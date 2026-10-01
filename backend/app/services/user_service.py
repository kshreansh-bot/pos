"""User service with business logic."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, UserRole
from app.schemas import UserCreate, UserUpdate, UserResponse
from app.services.auth_service import hash_password, verify_password
from app.utils.errors import NotFoundError, ValidationError, AuthenticationError


async def create_user(session: AsyncSession, user_create: UserCreate) -> User:
    """Create a new user.

    Args:
        session: Database session
        user_create: User creation schema

    Returns:
        Created user

    Raises:
        ValidationError: If username already exists
    """
    # Check if username exists
    result = await session.execute(select(User).where(User.username == user_create.username))
    if result.scalar_one_or_none():
        raise ValidationError(f"Username '{user_create.username}' already exists")

    # Check if email exists (if provided)
    if user_create.email:
        result = await session.execute(select(User).where(User.email == user_create.email))
        if result.scalar_one_or_none():
            raise ValidationError(f"Email '{user_create.email}' already exists")

    # Create user
    user = User(
        username=user_create.username,
        email=user_create.email,
        full_name=user_create.full_name,
        password_hash=hash_password(user_create.password),
        role=user_create.role,
        max_discount_percent=user_create.max_discount_percent
    )

    session.add(user)
    await session.flush()  # Get ID without committing
    return user


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """Get user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User:
    """Authenticate user with username and password.

    Args:
        session: Database session
        username: Username
        password: Plain password

    Returns:
        Authenticated user

    Raises:
        AuthenticationError: If credentials are invalid
    """
    user = await get_user_by_username(session, username)
    if not user:
        raise AuthenticationError("Invalid username or password")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid username or password")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


async def update_user(
    session: AsyncSession,
    user_id: int,
    user_update: UserUpdate
) -> User:
    """Update user information.

    Args:
        session: Database session
        user_id: User ID to update
        user_update: Update schema

    Returns:
        Updated user

    Raises:
        NotFoundError: If user not found
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("User not found")

    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await session.flush()
    return user
