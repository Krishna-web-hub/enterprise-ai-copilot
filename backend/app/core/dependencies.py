"""
FastAPI Dependency Injection

Dependencies are reusable components that FastAPI injects into route handlers.
They handle cross-cutting concerns like:
- Authentication (who is the current user?)
- Authorization (does this user have permission?)
- Database sessions
- Rate limiting

Why dependency injection?
- DRY: Write auth logic once, use everywhere
- Testable: Easily mock dependencies in tests
- Composable: Dependencies can depend on other dependencies
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.core.token_blacklist import is_token_blacklisted
from app.models.user import User

# OAuth2 scheme tells FastAPI where to find the token (Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency: Extract and validate the current user from the JWT token.

    Flow:
    1. Extract token from Authorization header
    2. Decode and validate the JWT
    3. Look up the user in the database
    4. Return the user object (or raise 401)

    Usage:
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode the token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # Check if token has been blacklisted (user logged out)
    if await is_token_blacklisted(token):
        raise credentials_exception

    # Extract user ID from token payload
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Verify token type
    if payload.get("type") != "access":
        raise credentials_exception

    # Look up user in database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency: Ensures the current user has admin role.

    Builds on get_current_user - first authenticates, then checks role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
