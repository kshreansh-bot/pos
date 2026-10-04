"""Tests for user service."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, UserRole
from app.schemas import UserCreate, UserUpdate
from app.services.user_service import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    authenticate_user,
    update_user,
)
from app.utils.errors import ValidationError, AuthenticationError, NotFoundError

pytestmark = pytest.mark.asyncio


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


class TestCreateUser:
    """Test user creation."""

    async def test_create_user_success(self, test_db):
        user_create = UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="password123",
            role=UserRole.CASHIER,
            max_discount_percent=5
        )

        user = await create_user(test_db, user_create)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == UserRole.CASHIER
        assert user.max_discount_percent == 5
        assert user.is_active is True

    async def test_create_user_default_role(self, test_db):
        user_create = UserCreate(
            username="cashier",
            email="cashier@example.com",
            full_name="Cashier User",
            password="password123"
        )

        user = await create_user(test_db, user_create)

        assert user.role == UserRole.CASHIER

    async def test_create_user_duplicate_username(self, test_db):
        user_create = UserCreate(
            username="duplicate",
            email="first@example.com",
            full_name="First User",
            password="password123"
        )

        await create_user(test_db, user_create)

        # Try to create with same username
        with pytest.raises(ValidationError) as exc_info:
            await create_user(test_db, user_create)

        assert "already exists" in str(exc_info.value)

    async def test_create_user_duplicate_email(self, test_db):
        user_create1 = UserCreate(
            username="user1",
            email="same@example.com",
            full_name="User 1",
            password="password123"
        )

        user_create2 = UserCreate(
            username="user2",
            email="same@example.com",
            full_name="User 2",
            password="password123"
        )

        await create_user(test_db, user_create1)

        with pytest.raises(ValidationError) as exc_info:
            await create_user(test_db, user_create2)

        assert "already exists" in str(exc_info.value)

    async def test_create_user_without_email(self, test_db):
        user_create = UserCreate(
            username="noemail",
            full_name="No Email User",
            password="password123"
        )

        user = await create_user(test_db, user_create)

        assert user.email is None

    async def test_create_user_all_roles(self, test_db):
        roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.CASHIER, UserRole.INVENTORY_MANAGER]

        for i, role in enumerate(roles):
            user_create = UserCreate(
                username=f"user_{role.value}",
                email=f"{role.value}@example.com",
                full_name=f"User {role.value}",
                password="password123",
                role=role
            )

            user = await create_user(test_db, user_create)
            assert user.role == role


class TestGetUser:
    """Test user retrieval."""

    async def test_get_user_by_username(self, test_db):
        user_create = UserCreate(
            username="findme",
            email="findme@example.com",
            full_name="Find Me",
            password="password123"
        )

        created_user = await create_user(test_db, user_create)
        await test_db.commit()

        found_user = await get_user_by_username(test_db, "findme")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "findme"

    async def test_get_user_by_username_not_found(self, test_db):
        user = await get_user_by_username(test_db, "nonexistent")
        assert user is None

    async def test_get_user_by_id(self, test_db):
        user_create = UserCreate(
            username="byid",
            email="byid@example.com",
            full_name="By ID",
            password="password123"
        )

        created_user = await create_user(test_db, user_create)
        await test_db.commit()

        found_user = await get_user_by_id(test_db, created_user.id)

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.username == "byid"

    async def test_get_user_by_id_not_found(self, test_db):
        user = await get_user_by_id(test_db, 99999)
        assert user is None


class TestAuthenticateUser:
    """Test user authentication."""

    async def test_authenticate_user_success(self, test_db):
        user_create = UserCreate(
            username="authuser",
            email="auth@example.com",
            full_name="Auth User",
            password="correctpassword"
        )

        await create_user(test_db, user_create)
        await test_db.commit()

        authenticated_user = await authenticate_user(test_db, "authuser", "correctpassword")

        assert authenticated_user.username == "authuser"

    async def test_authenticate_user_wrong_password(self, test_db):
        user_create = UserCreate(
            username="authuser",
            email="auth@example.com",
            full_name="Auth User",
            password="correctpassword"
        )

        await create_user(test_db, user_create)
        await test_db.commit()

        with pytest.raises(AuthenticationError):
            await authenticate_user(test_db, "authuser", "wrongpassword")

    async def test_authenticate_user_not_found(self, test_db):
        with pytest.raises(AuthenticationError):
            await authenticate_user(test_db, "nonexistent", "password")

    async def test_authenticate_inactive_user(self, test_db):
        user_create = UserCreate(
            username="inactiveuser",
            email="inactive@example.com",
            full_name="Inactive User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        user.is_active = False
        await test_db.commit()

        with pytest.raises(AuthenticationError) as exc_info:
            await authenticate_user(test_db, "inactiveuser", "password123")

        assert "inactive" in str(exc_info.value)


class TestUpdateUser:
    """Test user updates."""

    async def test_update_user_full_name(self, test_db):
        user_create = UserCreate(
            username="updateme",
            email="update@example.com",
            full_name="Original Name",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        update_data = UserUpdate(full_name="Updated Name")
        updated_user = await update_user(test_db, user.id, update_data)

        assert updated_user.full_name == "Updated Name"
        assert updated_user.username == "updateme"

    async def test_update_user_email(self, test_db):
        user_create = UserCreate(
            username="user",
            email="old@example.com",
            full_name="User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        update_data = UserUpdate(email="new@example.com")
        updated_user = await update_user(test_db, user.id, update_data)

        assert updated_user.email == "new@example.com"

    async def test_update_user_role(self, test_db):
        user_create = UserCreate(
            username="user",
            email="user@example.com",
            full_name="User",
            password="password123",
            role=UserRole.CASHIER
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        update_data = UserUpdate(role=UserRole.MANAGER)
        updated_user = await update_user(test_db, user.id, update_data)

        assert updated_user.role == UserRole.MANAGER

    async def test_update_user_is_active(self, test_db):
        user_create = UserCreate(
            username="user",
            email="user@example.com",
            full_name="User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        update_data = UserUpdate(is_active=False)
        updated_user = await update_user(test_db, user.id, update_data)

        assert updated_user.is_active is False

    async def test_update_user_max_discount(self, test_db):
        user_create = UserCreate(
            username="user",
            email="user@example.com",
            full_name="User",
            password="password123",
            max_discount_percent=5
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        update_data = UserUpdate(max_discount_percent=20)
        updated_user = await update_user(test_db, user.id, update_data)

        assert updated_user.max_discount_percent == 20

    async def test_update_user_multiple_fields(self, test_db):
        user_create = UserCreate(
            username="user",
            email="user@example.com",
            full_name="User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        update_data = UserUpdate(
            full_name="New Name",
            email="new@example.com",
            role=UserRole.MANAGER,
            max_discount_percent=15
        )
        updated_user = await update_user(test_db, user.id, update_data)

        assert updated_user.full_name == "New Name"
        assert updated_user.email == "new@example.com"
        assert updated_user.role == UserRole.MANAGER
        assert updated_user.max_discount_percent == 15

    async def test_update_nonexistent_user(self, test_db):
        update_data = UserUpdate(full_name="New Name")

        with pytest.raises(NotFoundError):
            await update_user(test_db, 99999, update_data)

    async def test_update_user_partial_fields(self, test_db):
        user_create = UserCreate(
            username="user",
            email="user@example.com",
            full_name="Original Name",
            password="password123",
            max_discount_percent=10
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        # Update only one field
        update_data = UserUpdate(full_name="New Name")
        updated_user = await update_user(test_db, user.id, update_data)

        # Other fields should remain unchanged
        assert updated_user.full_name == "New Name"
        assert updated_user.email == "user@example.com"
        assert updated_user.max_discount_percent == 10
