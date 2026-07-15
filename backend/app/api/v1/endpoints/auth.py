"""
Authentication Endpoints

Handles user registration, login, token refresh, and profile retrieval.
All password handling uses bcrypt. Tokens are JWT-based.

Routes:
- POST /register  → Create a new account
- POST /login     → Authenticate and receive tokens
- POST /refresh   → Get new access token using refresh token
- GET  /me        → Get current user profile
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.audit import log_auth_event
from app.core.token_blacklist import blacklist_token
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.

    Validates that email is unique, hashes the password, and stores the user.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user with hashed password
    user = User(
        email=request.email,
        full_name=request.full_name,
        password_hash=hash_password(request.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return access + refresh tokens.

    Security: Account is locked for 15 minutes after 5 failed attempts.
    """
    from app.core.account_lockout import lockout_service

    # Check lockout BEFORE any DB lookup (prevent timing attacks)
    if await lockout_service.is_locked(request.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to too many failed login attempts. Try again in 15 minutes.",
        )

    # Look up user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user:
        # Record attempt even for non-existent emails (prevent enumeration timing)
        await lockout_service.record_failed_attempt(request.email)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email. Please sign up first.",
        )

    if not verify_password(request.password, user.password_hash):
        is_now_locked = await lockout_service.record_failed_attempt(request.email)
        if is_now_locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked due to too many failed login attempts. Try again in 15 minutes.",
            )
        remaining = await lockout_service.get_remaining_attempts(request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Incorrect password. {remaining} attempt(s) remaining before lockout.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Successful login — reset failed attempt counter
    await lockout_service.reset_attempts(request.email)

    # Audit log
    client_ip = req.client.host if req.client else None
    log_auth_event("LOGIN", request.email, True, ip_address=client_ip, user_id=user.id)

    # Generate tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Get a new access token using a valid refresh token.

    This allows clients to maintain sessions without re-entering credentials.
    """
    payload = decode_token(request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    # Issue new tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Logout the current user by blacklisting their access token.

    The token is added to a blacklist (Redis-backed) so it can no longer
    be used even though it hasn't technically expired yet.
    """
    payload = decode_token(token)
    if payload and "exp" in payload:
        await blacklist_token(token, float(payload["exp"]))

    log_auth_event(
        event="LOGOUT",
        email=current_user.email,
        success=True,
        ip_address=request.client.host if request.client else None,
        user_id=current_user.id,
    )

    return {"message": "Logged out successfully"}
