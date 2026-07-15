"""
Authentication Service

Business logic for user registration, login, and token management.
This keeps the route handler thin — it only handles HTTP, this handles logic.

Why separate services from routes?
- Reusable: Agents can call auth_service without going through HTTP
- Testable: Unit test business logic without spinning up FastAPI
- Clean: Routes stay focused on request/response handling
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User


class AuthService:
    """Handles user authentication and registration logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, email: str, full_name: str, password: str) -> User:
        """
        Create a new user account.

        Raises ValueError if email is already taken.
        """
        # Check uniqueness
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """
        Verify credentials and return the user if valid.

        Returns None if email not found or password doesn't match.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None

        return user

    @staticmethod
    def create_tokens(user_id: int) -> dict:
        """Generate access and refresh tokens for a user."""
        token_data = {"sub": str(user_id)}
        return {
            "access_token": create_access_token(token_data),
            "refresh_token": create_refresh_token(token_data),
            "token_type": "bearer",
        }
