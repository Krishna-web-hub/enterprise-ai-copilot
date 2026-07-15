"""
Shared test fixtures for the backend test suite.

Provides:
- An in-memory SQLite database (fast, isolated, no external dependencies)
- An async HTTP client wired to the FastAPI app with the DB dependency overridden
- An `auth_headers` fixture that registers+logs in a user for authenticated tests

All test files should import fixtures from here rather than redefining their
own database setup — a single dependency_overrides assignment on the shared
`app` object is what makes tests deterministic; duplicating it per-file is a
common source of "works alone, fails in the full suite" bugs.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# ─── Test database setup ───────────────────────────────────────
# SQLite + aiosqlite in-memory: fast, no external Postgres needed for CI
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Override the database dependency for tests."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


# ─── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test, drop them after (full isolation)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Reset in-memory security state between tests
    from app.core.account_lockout import lockout_service
    from app.core.token_blacklist import _memory_blacklist
    lockout_service._attempts.clear()
    lockout_service._lockouts.clear()
    _memory_blacklist.clear()


@pytest.fixture
async def client():
    """Async HTTP test client for FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a user and return Authorization headers with a valid access token."""
    # Reset lockout state to ensure tests are isolated
    from app.core.account_lockout import lockout_service
    lockout_service._attempts.clear()
    lockout_service._lockouts.clear()

    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "TestPass123",
    })

    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
