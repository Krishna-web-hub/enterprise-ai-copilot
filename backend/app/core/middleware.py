"""
Security & Performance Middleware

Production-grade middleware for:
1. Security headers (OWASP recommended)
2. Rate limiting (in-memory for demo, Redis-backed in production)
3. Request size limiting (prevent oversized payloads from exhausting memory)

Why middleware instead of per-endpoint logic?
- Cross-cutting concerns: every request needs security headers, not just some
- DRY: rate limiting logic written once, applied everywhere
- Ordering control: middleware runs before route handlers, so malicious
  requests are rejected before touching business logic
"""

import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

# ─── Security Headers Middleware ────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds OWASP-recommended security headers to every response.

    These prevent common web attacks:
    - X-Content-Type-Options: prevents MIME-type sniffing
    - X-Frame-Options: prevents clickjacking
    - X-XSS-Protection: legacy XSS filter (modern browsers use CSP)
    - Strict-Transport-Security: enforces HTTPS (when behind TLS proxy)
    - Referrer-Policy: limits information leakage
    - Permissions-Policy: disables unnecessary browser features
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self' http: https:; "
            "frame-ancestors 'none'"
        )

        # Only add HSTS in production (assumes HTTPS is terminated upstream)
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


# ─── Rate Limiting Middleware ───────────────────────────────────

# Tiered rate limits: different limits for different endpoint groups
# Format: (path_prefix, max_requests_per_window)
RATE_LIMIT_TIERS = [
    ("/api/v1/auth", 20),        # Auth: strict (prevent brute force)
    ("/api/v1/ml/train", 10),    # Training: expensive, limit heavily
    ("/api/v1/reports/generate", 10),  # Report gen: expensive
    ("/api/v1/rag/ingest", 10),  # RAG ingest: expensive
    ("/api/v1/chat", 30),        # Chat: moderate
    ("/api/v1/", 100),           # General API: standard
]

EXCLUDED_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-grade rate limiter with Redis backend and in-memory fallback.

    Features:
    - Redis-backed: Shared state across all workers/instances (production)
    - In-memory fallback: Works when Redis is unavailable (development)
    - Tiered limits: Different limits per endpoint group (auth=strict, general=relaxed)
    - Per-IP tracking: Identifies clients by IP address
    - Sliding window: Uses Redis INCR + EXPIRE for efficient counting

    Redis key format: ratelimit:{ip}:{tier_prefix}
    TTL: window_seconds (auto-expires, no cleanup needed)
    """

    def __init__(self, app, window_seconds: int = 60):
        super().__init__(app)
        self.window_seconds = window_seconds
        # In-memory fallback (used when Redis unavailable)
        self._fallback: dict[str, list[float]] = defaultdict(list)
        self._redis_available: bool | None = None  # None = not checked yet

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip excluded paths
        if path in EXCLUDED_PATHS:
            return await call_next(request)

        # Skip rate limiting in test environment (ASGI transport has no real client)
        client_ip = request.client.host if request.client else None
        if not client_ip or client_ip == "testclient" or (settings.DEBUG and client_ip == "127.0.0.1"):
            return await call_next(request)

        max_requests = self._get_tier_limit(path)

        # Try Redis first, fall back to in-memory
        is_limited = await self._check_rate_limit_redis(client_ip, path, max_requests)
        if is_limited is None:
            # Redis unavailable — use in-memory fallback
            is_limited = self._check_rate_limit_memory(client_ip, max_requests)

        if is_limited:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after_seconds": self.window_seconds,
                },
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(max_requests),
                },
            )

        return await call_next(request)

    def _get_tier_limit(self, path: str) -> int:
        """Find the most specific rate limit tier for this path."""
        for prefix, limit in RATE_LIMIT_TIERS:
            if path.startswith(prefix):
                return limit
        return 100  # Default fallback

    async def _check_rate_limit_redis(self, client_ip: str, path: str, max_requests: int) -> bool | None:
        """
        Check rate limit via Redis. Returns:
        - True: rate limited
        - False: allowed
        - None: Redis unavailable (caller should use fallback)
        """
        try:
            import redis.asyncio as aioredis

            # Lazy connection (reuse across requests)
            if not hasattr(self, "_redis") or self._redis is None:
                self._redis = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )

            # Determine tier key
            tier = "general"
            for prefix, _ in RATE_LIMIT_TIERS:
                if path.startswith(prefix):
                    tier = prefix.replace("/api/v1/", "").replace("/", "_")
                    break

            key = f"ratelimit:{client_ip}:{tier}"

            # Atomic increment + expire
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()

            current_count = results[0]
            return current_count > max_requests

        except Exception:
            # Redis unavailable
            self._redis = None
            return None

    def _check_rate_limit_memory(self, client_ip: str, max_requests: int) -> bool:
        """In-memory fallback rate limit check (single-worker only)."""
        now = time.time()
        window_start = now - self.window_seconds

        self._fallback[client_ip] = [
            ts for ts in self._fallback[client_ip] if ts > window_start
        ]

        if len(self._fallback[client_ip]) >= max_requests:
            return True

        self._fallback[client_ip].append(now)
        return False


# ─── Request Size Limit Middleware ──────────────────────────────

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Rejects requests with Content-Length exceeding the configured maximum.

    Prevents memory exhaustion from oversized uploads bypassing the
    UploadFile size check (which only triggers after reading the body).

    Default: MAX_UPLOAD_SIZE_MB from settings (100MB).
    """

    def __init__(self, app, max_size_bytes: int | None = None):
        super().__init__(app)
        self.max_size_bytes = max_size_bytes or (settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_size_bytes:
            max_mb = self.max_size_bytes // (1024 * 1024)
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size is {max_mb}MB."},
            )

        return await call_next(request)
