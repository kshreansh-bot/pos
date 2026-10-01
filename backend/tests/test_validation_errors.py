"""Tests for error handling and edge cases."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, UserRole
from app.schemas import UserCreate, UserUpdate
from app.services.user_service import create_user, update_user
from app.services.auth_service import hash_password, verify_password
from app.utils.errors import ValidationError, AuthenticationError, NotFoundError


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


@pytest.mark.asyncio
class TestInputValidation:
    """Test input validation and schema constraints."""

    async def test_username_too_short(self, test_db):
        """Username must be at least 3 characters."""
        with pytest.raises(ValueError):
            UserCreate(
                username="ab",
                email="test@example.com",
                full_name="Test",
                password="password123"
            )

    async def test_username_too_long(self, test_db):
        """Username must be at most 80 characters."""
        with pytest.raises(ValueError):
            UserCreate(
                username="a" * 81,
                email="test@example.com",
                full_name="Test",
                password="password123"
            )

    async def test_password_too_short(self, test_db):
        """Password must be at least 8 characters."""
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                full_name="Test",
                password="short"
            )

    async def test_full_name_empty(self, test_db):
        """Full name cannot be empty."""
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                full_name="",
                password="password123"
            )

    async def test_invalid_email_format(self, test_db):
        """Email must be valid format."""
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser",
                email="notanemail",
                full_name="Test",
                password="password123"
            )

    async def test_max_discount_negative(self, test_db):
        """Max discount cannot be negative."""
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                full_name="Test",
                password="password123",
                max_discount_percent=-1
            )

    async def test_max_discount_over_100(self, test_db):
        """Max discount cannot exceed 100."""
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                full_name="Test",
                password="password123",
                max_discount_percent=101
            )


@pytest.mark.asyncio
class TestPasswordSecurity:
    """Test password security measures."""

    async def test_password_not_stored_plain(self, test_db):
        """Password should never be stored in plain text."""
        user_create = UserCreate(
            username="secureuser",
            email="secure@example.com",
            full_name="Secure User",
            password="mypassword123"
        )

        user = await create_user(test_db, user_create)

        # Password should be hashed
        assert user.password_hash != "mypassword123"
        assert len(user.password_hash) > 20

    async def test_password_hash_consistent_verification(self, test_db):
        """Password hash should verify correctly."""
        password = "testpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed)
        assert not verify_password("wrongpassword", hashed)

    async def test_different_users_different_hashes(self, test_db):
        """Same password for different users should result in different hashes."""
        password = "commonpassword123"

        user1 = UserCreate(
            username="user1",
            email="user1@example.com",
            full_name="User 1",
            password=password
        )

        user2 = UserCreate(
            username="user2",
            email="user2@example.com",
            full_name="User 2",
            password=password
        )

        created_user1 = await create_user(test_db, user1)
        created_user2 = await create_user(test_db, user2)

        # Hashes should be different
        assert created_user1.password_hash != created_user2.password_hash


@pytest.mark.asyncio
class TestUserConstraints:
    """Test database constraints and business rules."""

    async def test_username_unique_constraint(self, test_db):
        """Usernames must be unique."""
        user_create = UserCreate(
            username="unique",
            email="first@example.com",
            full_name="First User",
            password="password123"
        )

        await create_user(test_db, user_create)
        await test_db.commit()

        # Try to create another user with same username
        with pytest.raises(ValidationError):
            user_create2 = UserCreate(
                username="unique",
                email="second@example.com",
                full_name="Second User",
                password="password123"
            )
            await create_user(test_db, user_create2)

    async def test_email_unique_constraint(self, test_db):
        """Emails must be unique."""
        user_create = UserCreate(
            username="user1",
            email="same@example.com",
            full_name="User 1",
            password="password123"
        )

        await create_user(test_db, user_create)
        await test_db.commit()

        # Try to create another user with same email
        with pytest.raises(ValidationError):
            user_create2 = UserCreate(
                username="user2",
                email="same@example.com",
                full_name="User 2",
                password="password123"
            )
            await create_user(test_db, user_create2)

    async def test_multiple_users_without_email(self, test_db):
        """Multiple users can have null email."""
        user1 = UserCreate(
            username="noemail1",
            full_name="No Email 1",
            password="password123"
        )

        user2 = UserCreate(
            username="noemail2",
            full_name="No Email 2",
            password="password123"
        )

        created1 = await create_user(test_db, user1)
        created2 = await create_user(test_db, user2)

        assert created1.email is None
        assert created2.email is None


@pytest.mark.asyncio
class TestDefaultValues:
    """Test default values for user fields."""

    async def test_user_default_role(self, test_db):
        """New users should default to CASHIER role."""
        user_create = UserCreate(
            username="defaultuser",
            email="default@example.com",
            full_name="Default User",
            password="password123"
        )

        user = await create_user(test_db, user_create)

        assert user.role == UserRole.CASHIER

    async def test_user_default_is_active(self, test_db):
        """New users should be active by default."""
        user_create = UserCreate(
            username="activeuser",
            email="active@example.com",
            full_name="Active User",
            password="password123"
        )

        user = await create_user(test_db, user_create)

        assert user.is_active is True

    async def test_user_default_max_discount(self, test_db):
        """New users should have default max discount."""
        user_create = UserCreate(
            username="discountuser",
            email="discount@example.com",
            full_name="Discount User",
            password="password123"
        )

        user = await create_user(test_db, user_create)

        assert user.max_discount_percent == 10

    async def test_user_custom_max_discount(self, test_db):
        """Users can have custom max discount."""
        user_create = UserCreate(
            username="customuser",
            email="custom@example.com",
            full_name="Custom User",
            password="password123",
            max_discount_percent=25
        )

        user = await create_user(test_db, user_create)

        assert user.max_discount_percent == 25

    async def test_user_timestamps_created(self, test_db):
        """User should have created_at timestamp."""
        user_create = UserCreate(
            username="timeuser",
            email="time@example.com",
            full_name="Time User",
            password="password123"
        )

        user = await create_user(test_db, user_create)

        assert user.created_at is not None


@pytest.mark.asyncio
class TestUserUpdate:
    """Test user update validation."""

    async def test_update_with_invalid_email(self, test_db):
        """Email update should validate email format."""
        user_create = UserCreate(
            username="user",
            email="valid@example.com",
            full_name="User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        with pytest.raises(ValueError):
            update_data = UserUpdate(email="invalidemail")
            await update_user(test_db, user.id, update_data)

    async def test_update_email_uniqueness(self, test_db):
        """Email must remain unique across users."""
        user1_create = UserCreate(
            username="user1",
            email="user1@example.com",
            full_name="User 1",
            password="password123"
        )

        user2_create = UserCreate(
            username="user2",
            email="user2@example.com",
            full_name="User 2",
            password="password123"
        )

        user1 = await create_user(test_db, user1_create)
        user2 = await create_user(test_db, user2_create)
        await test_db.commit()

        # Try to update user2's email to user1's email
        update_data = UserUpdate(email="user1@example.com")

        # This might raise an integrity error or validation error
        # depending on implementation
        try:
            await update_user(test_db, user2.id, update_data)
            await test_db.commit()
            # If it doesn't raise, both users have the same email now
            # which is a problem
            pytest.fail("Should not allow duplicate emails")
        except Exception:
            # Expected to fail
            pass

    async def test_update_max_discount_validation(self, test_db):
        """Max discount must be between 0 and 100."""
        user_create = UserCreate(
            username="user",
            email="user@example.com",
            full_name="User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        with pytest.raises(ValueError):
            update_data = UserUpdate(max_discount_percent=101)

    async def test_update_role_to_all_roles(self, test_db):
        """User role should accept all valid roles."""
        user_create = UserCreate(
            username="user",
            email="user@example.com",
            full_name="User",
            password="password123"
        )

        user = await create_user(test_db, user_create)
        await test_db.commit()

        for role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.INVENTORY_MANAGER, UserRole.CASHIER]:
            update_data = UserUpdate(role=role)
            updated_user = await update_user(test_db, user.id, update_data)
            assert updated_user.role == role


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and error messages."""

    async def test_operation_on_nonexistent_user(self, test_db):
        """Operations on nonexistent users should raise NotFoundError."""
        update_data = UserUpdate(full_name="New Name")

        with pytest.raises(NotFoundError):
            await update_user(test_db, 99999, update_data)

    async def test_authentication_error_message(self, test_db):
        """Authentication error should not reveal which part failed."""
        # This is a security best practice - don't say "user not found" vs "wrong password"
        # The error message should be generic
        from app.services.user_service import authenticate_user

        try:
            await authenticate_user(test_db, "nonexistent", "password")
            pytest.fail("Should raise AuthenticationError")
        except AuthenticationError as e:
            # Error message should be generic, not revealing
            assert "Invalid username or password" in str(e)

    async def test_validation_error_for_duplicate_username(self, test_db):
        """Duplicate username should raise ValidationError."""
        user_create = UserCreate(
            username="duplicate",
            email="first@example.com",
            full_name="First",
            password="password123"
        )

        await create_user(test_db, user_create)

        with pytest.raises(ValidationError) as exc_info:
            await create_user(test_db, user_create)

        assert "already exists" in str(exc_info.value)
