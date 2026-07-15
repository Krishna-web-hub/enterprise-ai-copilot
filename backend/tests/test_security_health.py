"""
Phase 12 Tests - Security, Health Check, and Auth Edge Cases

Coverage:
1. Health endpoint: returns correct shape, no auth required
2. Security headers: present on every response
3. Auth edge cases: expired token, invalid token format, wrong password format
4. Register edge cases: duplicate email, weak password

Database/client/auth fixtures from conftest.py.
"""

import time

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings

# ─── Health Check ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health check returns 200 with service info, no auth required."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "service" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_no_auth_required(client: AsyncClient):
    """Health endpoint must work without any authentication."""
    response = await client.get("/health")
    assert response.status_code == 200


# ─── Security Headers ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Every response should include OWASP security headers."""
    response = await client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_security_headers_on_api_routes(client: AsyncClient, auth_headers: dict):
    """Security headers should be present on authenticated API routes too."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


# ─── Auth Edge Cases ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_expired_token_rejected(client: AsyncClient):
    """An expired JWT should be rejected with 401."""
    # Create a token that expired 1 hour ago
    expired_payload = {
        "sub": "1",
        "type": "access",
        "exp": int(time.time()) - 3600,
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_malformed_token_rejected(client: AsyncClient):
    """A completely invalid token string should be rejected."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-at-all"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_used_as_access(client: AsyncClient, auth_headers: dict):
    """A refresh token should not work as an access token (wrong type field)."""
    # Register and login to get a refresh token
    await client.post("/api/v1/auth/register", json={
        "email": "refresh_test@example.com", "full_name": "Test", "password": "TestPass123",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "refresh_test@example.com", "password": "TestPass123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    # Try to use refresh token as access token
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_for_nonexistent_user_rejected(client: AsyncClient):
    """A valid-format token for a user that doesn't exist should be rejected."""
    payload = {
        "sub": "99999",
        "type": "access",
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# ─── Registration Edge Cases ──────────────────────────────────

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering with an existing email should return 409."""
    user_data = {"email": "dup@example.com", "full_name": "Test", "password": "TestPass123"}
    await client.post("/api/v1/auth/register", json=user_data)

    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Passwords shorter than 8 chars should be rejected by Pydantic validation."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "short@example.com", "full_name": "Test", "password": "123",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Invalid email format should be rejected."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email", "full_name": "Test", "password": "TestPass123",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Wrong password should return 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpw@example.com", "full_name": "Test", "password": "CorrectPass1",
    })

    response = await client.post("/api/v1/auth/login", json={
        "email": "wrongpw@example.com", "password": "wrongpassword",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    """Login with an email that doesn't exist should return 404."""
    response = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com", "password": "TestPass123",
    })
    assert response.status_code == 404
