"""
Database Connection and Session Management

Uses SQLAlchemy 2.0 async engine with asyncpg driver.

Architecture:
- Engine: Manages the connection pool to PostgreSQL
- SessionLocal: Factory for creating database sessions
- Base: Declarative base class for all ORM models
- get_db: Dependency that provides a session per request and handles cleanup

Why async?
- FastAPI is async-first; blocking DB calls would defeat the purpose
- asyncpg is the fastest PostgreSQL driver for Python
- Allows handling thousands of concurrent requests efficiently
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,  # Log SQL queries in development
    pool_size=20,         # Max connections in the pool
    max_overflow=10,      # Extra connections allowed beyond pool_size
    pool_pre_ping=True,   # Verify connections before using them
)

# Session factory - each request gets its own session
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (avoids lazy-load issues)
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    All models inherit from this. It provides:
    - Metadata for table creation
    - Common configuration
    """
    pass


async def get_db() -> AsyncSession:
    """
    Dependency that yields a database session.

    Usage in FastAPI endpoints:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically closed after the request completes,
    even if an exception occurs (thanks to the finally block).
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
