"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=80)
    email: Optional[EmailStr] = None
    full_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.CASHIER
    max_discount_percent: int = Field(default=10, ge=0, le=100)


class UserUpdate(BaseModel):
    """Schema for updating user."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    max_discount_percent: Optional[int] = Field(None, ge=0, le=100)


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    role: UserRole
    is_active: bool
    max_discount_percent: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_in: int  # seconds


class TokenResponse(BaseModel):
    """Schema for token refresh response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
    error_code: Optional[str] = None
    status_code: int
