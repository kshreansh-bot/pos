"""API routes for authentication."""
from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db_session
from app.schemas import LoginRequest, LoginResponse, UserResponse
from app.services.auth_service import create_access_token, decode_token, extract_token_from_header
from app.services.user_service import authenticate_user
from app.utils.errors import AppException

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Authenticate user and return JWT token.

    Args:
        credentials: Login credentials (username, password)
        session: Database session

    Returns:
        LoginResponse with access token and user info
    """
    user = await authenticate_user(session, credentials.username, credentials.password)

    token, expires_in = create_access_token({"sub": str(user.id)})

    return LoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
        expires_in=expires_in
    )


@router.post("/logout")
async def logout():
    """Logout user (client-side token deletion).

    Note: JWT tokens are stateless. This endpoint is provided for API consistency.
    Clients should delete the token from their storage.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_db_session)
):
    """Get current authenticated user.

    Args:
        authorization: Authorization header with bearer token
        session: Database session

    Returns:
        Current user info
    """
    from app.services.user_service import get_user_by_id

    token = extract_token_from_header(authorization)
    payload = decode_token(token)
    user_id = int(payload.get("sub"))

    user = await get_user_by_id(session, user_id)
    if not user:
        raise AppException("User not found", status_code=404)

    return UserResponse.model_validate(user)
