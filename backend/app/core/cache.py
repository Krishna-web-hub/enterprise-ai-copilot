"""
Redis Cache Utility

Provides an async Redis client with helpers for caching API responses.

Design principles:
- Graceful degradation: If Redis is unavailable, the app continues to work
  (just slower, hitting the DB every time). Cache misses are NOT errors.
- Tenant isolation: Keys are prefixed with user_id to prevent data leakage
  between users (user A's cached dashboard should never be shown to user B).
- Automatic serialization: Values are JSON-serialized on set and deserialized
  on get, so callers pass dicts/lists directly.
- TTL-based expiration: Every cached value has a time-to-live. No manual
  cleanup required. Stale data expires automatically.

Usage:
    from app.core.cache import cache

    # Set with 60-second TTL
    await cache.set("dashboard", user_id=1, value={"total_datasets": 5}, ttl=60)

    # Get (returns None on miss or Redis error)
    data = await cache.get("dashboard", user_id=1)

    # Invalidate
    await cache.delete("dashboard", user_id=1)
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("app.cache")


class CacheService:
    """
    Async Redis cache with graceful fallback.

    All methods catch Redis exceptions and return None/False instead
    of propagating errors — the app should never crash because Redis
    is temporarily unreachable.
    """

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    @property
    def client(self) -> aioredis.Redis:
        """Lazily create the Redis connection (reused across requests)."""
        if self._client is None:
            self._client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
        return self._client

    def _key(self, namespace: str, user_id: int) -> str:
        """Build a namespaced, user-isolated cache key."""
        return f"copilot:{user_id}:{namespace}"

    async def get(self, namespace: str, user_id: int) -> Optional[Any]:
        """
        Get a cached value. Returns None on miss or Redis error.
        """
        try:
            raw = await self.client.get(self._key(namespace, user_id))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.debug("Cache get failed (non-critical): %s", e)
            return None

    async def set(self, namespace: str, user_id: int, value: Any, ttl: int = 60) -> bool:
        """
        Cache a value with TTL (seconds). Returns True on success.
        """
        try:
            serialized = json.dumps(value, default=str)
            await self.client.setex(
                self._key(namespace, user_id),
                ttl,
                serialized,
            )
            return True
        except Exception as e:
            logger.debug("Cache set failed (non-critical): %s", e)
            return False

    async def delete(self, namespace: str, user_id: int) -> bool:
        """
        Invalidate a cached value. Returns True on success.
        """
        try:
            await self.client.delete(self._key(namespace, user_id))
            return True
        except Exception as e:
            logger.debug("Cache delete failed (non-critical): %s", e)
            return False

    async def invalidate_user(self, user_id: int) -> bool:
        """
        Invalidate ALL cached data for a user.
        Used after significant changes (e.g., bulk upload, model training).
        """
        try:
            pattern = f"copilot:{user_id}:*"
            keys = []
            async for key in self.client.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await self.client.delete(*keys)
            return True
        except Exception as e:
            logger.debug("Cache invalidate_user failed (non-critical): %s", e)
            return False

    async def close(self):
        """Close the Redis connection (call on app shutdown)."""
        if self._client:
            await self._client.close()
            self._client = None


# Singleton instance used throughout the app
cache = CacheService()
