"""
Account Lockout — Brute Force Protection

Tracks failed login attempts per email address and temporarily locks
accounts after too many consecutive failures.

Why account lockout?
- Without it, an attacker can try unlimited passwords against a known email.
- Even with bcrypt's intentional slowness (~100ms/attempt), 1000 attempts/min
  is feasible without lockout — a weak 6-char password falls in hours.
- The lockout period (15 min) balances security with user convenience.

Implementation:
- Uses Redis when available (shared across workers), falls back to in-memory.
- Tracks attempts by email (not IP), because attackers can rotate IPs easily
  but the target email stays the same.
- Lockout resets on successful login (so legitimate users aren't stuck after
  a lock period ends and they know the right password).

Privacy: failed attempt data auto-expires after the lockout window — no
long-term tracking of login behavior.
"""

import logging
import time
from collections import defaultdict
from typing import Optional

logger = logging.getLogger("app.security")

# Configuration
MAX_FAILED_ATTEMPTS = 5  # Lock after this many failures
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes
ATTEMPT_WINDOW_SECONDS = 900  # Track attempts within this window


class AccountLockoutService:
    """
    Manages login attempt tracking and account lockout state.

    Thread-safe for single-worker use. For multi-worker production,
    uses Redis (shared state).
    """

    def __init__(self):
        # In-memory storage (fallback when Redis unavailable)
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._lockouts: dict[str, float] = {}
        self._redis = None

    async def _get_redis(self):
        """Lazily connect to Redis."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                from app.core.config import settings

                self._redis = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def is_locked(self, email: str) -> bool:
        """Check if an account is currently locked out."""
        email_lower = email.lower()

        redis = await self._get_redis()
        if redis:
            try:
                lock_key = f"lockout:{email_lower}"
                return await redis.exists(lock_key) > 0
            except Exception:
                pass

        # In-memory fallback
        lock_until = self._lockouts.get(email_lower, 0)
        if lock_until > time.time():
            return True
        elif email_lower in self._lockouts:
            del self._lockouts[email_lower]
        return False

    async def record_failed_attempt(self, email: str) -> bool:
        """
        Record a failed login attempt. Returns True if the account is now locked.
        """
        email_lower = email.lower()

        redis = await self._get_redis()
        if redis:
            try:
                attempt_key = f"login_attempts:{email_lower}"
                count = await redis.incr(attempt_key)
                if count == 1:
                    await redis.expire(attempt_key, ATTEMPT_WINDOW_SECONDS)

                if count >= MAX_FAILED_ATTEMPTS:
                    lock_key = f"lockout:{email_lower}"
                    await redis.setex(lock_key, LOCKOUT_DURATION_SECONDS, "locked")
                    logger.warning("Account locked: %s after %d failed attempts", email_lower, count)
                    return True
                return False
            except Exception:
                pass

        # In-memory fallback
        now = time.time()
        window_start = now - ATTEMPT_WINDOW_SECONDS
        self._attempts[email_lower] = [
            t for t in self._attempts[email_lower] if t > window_start
        ]
        self._attempts[email_lower].append(now)

        if len(self._attempts[email_lower]) >= MAX_FAILED_ATTEMPTS:
            self._lockouts[email_lower] = now + LOCKOUT_DURATION_SECONDS
            logger.warning("Account locked (memory): %s after %d failed attempts",
                          email_lower, len(self._attempts[email_lower]))
            return True
        return False

    async def reset_attempts(self, email: str) -> None:
        """Clear failed attempts after a successful login."""
        email_lower = email.lower()

        redis = await self._get_redis()
        if redis:
            try:
                await redis.delete(f"login_attempts:{email_lower}", f"lockout:{email_lower}")
            except Exception:
                pass

        # Also clear in-memory
        self._attempts.pop(email_lower, None)
        self._lockouts.pop(email_lower, None)

    async def get_remaining_attempts(self, email: str) -> int:
        """Get how many login attempts remain before lockout."""
        email_lower = email.lower()

        redis = await self._get_redis()
        if redis:
            try:
                count = await redis.get(f"login_attempts:{email_lower}")
                return max(0, MAX_FAILED_ATTEMPTS - int(count or 0))
            except Exception:
                pass

        # In-memory fallback
        now = time.time()
        window_start = now - ATTEMPT_WINDOW_SECONDS
        recent = [t for t in self._attempts.get(email_lower, []) if t > window_start]
        return max(0, MAX_FAILED_ATTEMPTS - len(recent))


# Singleton instance
lockout_service = AccountLockoutService()
