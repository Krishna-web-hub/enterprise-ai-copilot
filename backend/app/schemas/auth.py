"""
Authentication Schemas (Pydantic)

Define the shape of request/response bodies for auth endpoints.
Pydantic handles validation automatically — if a field is missing or wrong type,
FastAPI returns a 422 error with a clear message.
"""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(password: str) -> str:
    """
    Enforce password complexity rules:
    - At least 8 characters (enforced by Field min_length too)
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - No more than 128 characters
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


class RegisterRequest(BaseModel):
    """What the client sends to create an account."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        from app.core.sanitization import sanitize_text
        sanitized = sanitize_text(v)
        if not sanitized or len(sanitized) < 2:
            raise ValueError("Full name must be at least 2 characters after sanitization")
        return sanitized


class LoginRequest(BaseModel):
    """What the client sends to log in."""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """What the client sends to refresh their access token."""
    refresh_token: str


class TokenResponse(BaseModel):
    """What the server returns after successful login/refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User profile returned by the API (never includes password)."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
