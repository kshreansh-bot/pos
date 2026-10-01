"""Authentication service with JWT and password handling."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from app.config import settings
from app.utils.errors import AuthenticationError

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> tuple[str, int]:
    """Create a JWT access token.

    Args:
        data: Dictionary with token claims (typically {"sub": user_id})
        expires_delta: Optional custom expiration time

    Returns:
        Tuple of (token, expires_in_seconds)

    Raises:
        AuthenticationError: If token creation fails
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.algorithm
        )
        expires_in = int((expire - datetime.utcnow()).total_seconds())
        return encoded_jwt, expires_in
    except Exception as e:
        raise AuthenticationError(f"Token creation failed: {str(e)}")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Dictionary with token claims

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid or expired token: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")


def extract_token_from_header(auth_header: Optional[str]) -> str:
    """Extract token from Authorization header.

    Args:
        auth_header: Authorization header value (format: "Bearer <token>")

    Returns:
        Token string

    Raises:
        AuthenticationError: If header is missing or malformed
    """
    if not auth_header:
        raise AuthenticationError("Authorization header missing")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format")

    return parts[1]
