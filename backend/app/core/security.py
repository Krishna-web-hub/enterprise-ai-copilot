"""
Security Utilities - Password Hashing and JWT Token Management

Password Hashing:
- Uses bcrypt via passlib for secure password storage
- Passwords are never stored in plaintext
- bcrypt automatically handles salt generation

JWT Tokens:
- Access tokens: Short-lived (30 min default), used for API authentication
- Refresh tokens: Long-lived (7 days default), used to get new access tokens
- Both are signed with HS256 using a secret key

Why JWT over sessions?
- Stateless: No server-side session storage needed
- Scalable: Works across multiple backend instances
- Standard: Widely supported across platforms
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
# bcrypt is the gold standard for password hashing:
# - Intentionally slow (prevents brute force)
# - Built-in salt (prevents rainbow table attacks)
# - Configurable work factor (can increase over time)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The user's plaintext password

    Returns:
        Hashed password string (includes salt and algorithm info)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Args:
        plain_password: The password the user provided at login
        hashed_password: The stored hash from the database

    Returns:
        True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload to encode (typically {"sub": user_id})
        expires_delta: Custom expiration time (defaults to config value)

    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token (longer-lived than access token).

    Args:
        data: Payload to encode (typically {"sub": user_id})

    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string to decode

    Returns:
        Decoded payload dict if valid, None if invalid/expired
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None
