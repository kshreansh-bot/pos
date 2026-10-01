"""Tests for authentication API endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models import Base, User, UserRole
from app.database import get_db_session
from app.schemas import UserCreate
from app.services.user_service import create_user
from app.services.auth_service import hash_password


@pytest.fixture
async def test_db():
    """Create in-memory test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(test_db):
    """Create test client with test database."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(test_db):
    """Create a test user."""
    user_create = UserCreate(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password="password123",
        role=UserRole.CASHIER
    )

    user = await create_user(test_db, user_create)
    await test_db.commit()
    return user


@pytest.mark.asyncio
class TestAuthLogin:
    """Test login endpoint."""

    async def test_login_success(self, client, test_db, test_user):
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "testuser"
        assert data["user"]["role"] == "cashier"
        assert "expires_in" in data

    async def test_login_invalid_username(self, client):
        response = await client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "password123"}
        )

        assert response.status_code == 401

    async def test_login_invalid_password(self, client, test_db, test_user):
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrongpassword"}
        )

        assert response.status_code == 401

    async def test_login_inactive_user(self, client, test_db):
        user_create = UserCreate(
            username="inactiveuser",
            email="inactive@example.com",
            full_name="Inactive User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        user.is_active = False
        await test_db.commit()

        response = await client.post(
            "/auth/login",
            json={"username": "inactiveuser", "password": "password123"}
        )

        assert response.status_code == 401

    async def test_login_returns_user_info(self, client, test_db, test_user):
        response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )

        data = response.json()
        user = data["user"]

        assert user["id"] == test_user.id
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        assert user["full_name"] == "Test User"
        assert user["is_active"] is True
        assert "created_at" in user


@pytest.mark.asyncio
class TestAuthLogout:
    """Test logout endpoint."""

    async def test_logout_success(self, client):
        response = await client.post("/auth/logout")

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
class TestGetCurrentUser:
    """Test get current user endpoint."""

    async def test_get_current_user_success(self, client, test_db, test_user):
        # First login to get token
        login_response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )

        token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["id"] == test_user.id

    async def test_get_current_user_missing_header(self, client):
        response = await client.get("/auth/me")

        assert response.status_code == 403

    async def test_get_current_user_invalid_token(self, client):
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 403

    async def test_get_current_user_malformed_header(self, client):
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "InvalidFormat"}
        )

        assert response.status_code == 403

    async def test_get_current_user_deleted_user(self, client, test_db, test_user):
        # Login to get token
        login_response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )

        token = login_response.json()["access_token"]

        # Delete the user
        await test_db.delete(test_user)
        await test_db.commit()

        # Try to get current user
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    async def test_get_current_user_different_roles(self, client, test_db):
        roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.INVENTORY_MANAGER]

        for role in roles:
            user_create = UserCreate(
                username=f"user_{role.value}",
                email=f"{role.value}@example.com",
                full_name=f"User {role.value}",
                password="password123",
                role=role
            )

            user = await create_user(test_db, user_create)
            await test_db.commit()

            login_response = await client.post(
                "/auth/login",
                json={"username": f"user_{role.value}", "password": "password123"}
            )

            token = login_response.json()["access_token"]

            response = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            assert response.json()["role"] == role.value


@pytest.mark.asyncio
class TestAuthenticationFlow:
    """Test complete authentication flow."""

    async def test_login_and_get_user_flow(self, client, test_db):
        # Create user
        user_create = UserCreate(
            username="flowtest",
            email="flow@example.com",
            full_name="Flow Test",
            password="password123",
            role=UserRole.MANAGER
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        # Login
        login_response = await client.post(
            "/auth/login",
            json={"username": "flowtest", "password": "password123"}
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        token = login_data["access_token"]

        # Verify token can be used to get user
        user_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert user_response.status_code == 200
        user_data = user_response.json()
        assert user_data["username"] == "flowtest"
        assert user_data["role"] == "manager"

    async def test_logout_and_token_still_valid(self, client, test_db, test_user):
        # Login
        login_response = await client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password123"}
        )

        token = login_response.json()["access_token"]

        # Logout (should not invalidate token in stateless JWT)
        logout_response = await client.post("/auth/logout")
        assert logout_response.status_code == 200

        # Token should still be valid (JWT is stateless)
        user_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert user_response.status_code == 200
