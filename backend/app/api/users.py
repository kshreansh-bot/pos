"""API routes for user management."""
from typing import Optional
from fastapi import APIRouter, Depends, Header, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db_session
from app.models import User, UserRole
from app.schemas import UserCreate, UserResponse, UserUpdate
from app.services.auth_service import decode_token, extract_token_from_header
from app.services.user_service import get_user_by_id, create_user, update_user
from app.utils.errors import AppException, AuthorizationError, NotFoundError

router = APIRouter(prefix="/users", tags=["users"])


async def require_role(
    required_roles: list[UserRole],
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """Dependency to check user role.

    Args:
        required_roles: List of allowed roles
        authorization: Authorization header
        session: Database session

    Returns:
        Current user if authorized

    Raises:
        AuthorizationError: If user role not in required_roles
    """
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)

    if user.role not in required_roles:
        raise AuthorizationError("Insufficient permissions")

    return user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(lambda auth=Header(None), session=Depends(get_db_session):
                                  require_role([UserRole.ADMIN], auth, session)),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """List all users (admin only).

    Args:
        session: Database session
        current_user: Current authenticated user (must be admin)
        skip: Number of users to skip
        limit: Maximum number of users to return

    Returns:
        List of users
    """
    result = await session.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None)
):
    """Get user by ID (admin only or own profile).

    Args:
        user_id: User ID
        session: Database session
        authorization: Authorization header

    Returns:
        User info
    """
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    current_user_id = int(payload.get("sub"))

    current_user = await get_user_by_id(session, current_user_id)
    if current_user.role != UserRole.ADMIN and current_user_id != user_id:
        raise AuthorizationError("Cannot access other users' profiles")

    user = await get_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("User not found")

    return UserResponse.model_validate(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(lambda auth=Header(None), session=Depends(get_db_session):
                                  require_role([UserRole.ADMIN], auth, session))
):
    """Create a new user (admin only).

    Args:
        user_create: User creation schema
        session: Database session
        current_user: Current authenticated user (must be admin)

    Returns:
        Created user
    """
    user = await create_user(session, user_create)
    await session.commit()
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
    authorization: str = Header(None)
):
    """Update user (admin only or own profile).

    Args:
        user_id: User ID to update
        user_update: User update schema
        session: Database session
        authorization: Authorization header

    Returns:
        Updated user
    """
    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    current_user_id = int(payload.get("sub"))

    current_user = await get_user_by_id(session, current_user_id)
    if current_user.role != UserRole.ADMIN and current_user_id != user_id:
        raise AuthorizationError("Cannot update other users")

    user = await update_user(session, user_id, user_update)
    await session.commit()
    return UserResponse.model_validate(user)
