"""
Token Blacklist — Logout Support

When a user logs out, their access token is added to a blacklist so it
can no longer be used even though it hasn't expired yet.

Without blacklisting:
- A stolen token remains valid until it expires (30 min by default).
- A user who "logs out" can still have their old token used by an attacker.

Implementation:
- Blacklisted tokens are stored in Redis with a TTL matching the token's
  remaining lifetime (so they auto-expire and don't accumulate forever).
- Falls back to in-memory set when Redis unavailable (cleared on restart,
  but better than nothing for single-worker dev).
- The get_current_user dependency checks the blacklist on every request.

Performance: A Redis GET per authenticated request adds ~0.1ms latency.
This is negligible compared to the DB query that already runs in that dependency.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("app.security")

# In-memory fallback (tokens with their expiry time)
_memory_blacklist: dict[str, float] = {}


async def blacklist_token(token: str, expires_at: float) -> None:
    """
    Add a token to the blacklist.

    Args:
        token: The JWT token string to blacklist
        expires_at: Unix timestamp when this token expires (from the JWT 'exp' claim).
                    The blacklist entry auto-expires at this time.
    """
    ttl = int(expires_at - time.time())
    if ttl <= 0:
        return  # Already expired, no need to blacklist

    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        client = aioredis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True,
            socket_connect_timeout=1, socket_timeout=1,
        )
        await client.setex(f"blacklist:{token[:64]}", ttl, "1")
        await client.close()
        return
    except Exception:
        pass

    # In-memory fallback
    _memory_blacklist[token[:64]] = expires_at
    # Cleanup expired entries periodically (every 100 additions)
    if len(_memory_blacklist) % 100 == 0:
        now = time.time()
        expired = [k for k, v in _memory_blacklist.items() if v < now]
        for k in expired:
            del _memory_blacklist[k]


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been blacklisted (user logged out).

    Returns True if the token should be rejected.
    """
    token_key = token[:64]

    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        client = aioredis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True,
            socket_connect_timeout=1, socket_timeout=1,
        )
        result = await client.exists(f"blacklist:{token_key}")
        await client.close()
        return result > 0
    except Exception:
        pass

    # In-memory fallback
    expiry = _memory_blacklist.get(token_key)
    if expiry is None:
        return False
    if expiry < time.time():
        del _memory_blacklist[token_key]
        return False
    return True
