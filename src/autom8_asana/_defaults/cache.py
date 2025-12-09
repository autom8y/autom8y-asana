"""Default cache providers."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, NamedTuple


class _CacheEntry(NamedTuple):
    value: dict[str, Any]
    expires_at: float | None


class NullCacheProvider:
    """Cache provider that does nothing (no-op).

    This is the default when no caching is desired.
    All operations succeed silently but don't store anything.
    """

    def get(self, key: str) -> dict[str, Any] | None:
        """Always returns None (cache miss)."""
        return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Does nothing."""
        pass

    def delete(self, key: str) -> None:
        """Does nothing."""
        pass


class InMemoryCacheProvider:
    """Simple in-memory cache with TTL support.

    Thread-safe for basic usage. Not recommended for production
    multi-process deployments.

    Example:
        cache = InMemoryCacheProvider(default_ttl=300)  # 5 minute default
        client = AsanaClient(cache_provider=cache)
    """

    def __init__(self, default_ttl: int | None = None, max_size: int = 10000) -> None:
        """Initialize cache.

        Args:
            default_ttl: Default TTL in seconds (None = no expiration)
            max_size: Maximum number of entries before eviction
        """
        self._cache: dict[str, _CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        """Get value from cache if not expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at is not None and time.time() > entry.expires_at:
                del self._cache[key]
                return None
            return entry.value

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in cache with optional TTL."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        with self._lock:
            # Simple eviction: remove oldest entries if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                # Remove first 10% of entries
                to_remove = list(self._cache.keys())[:self._max_size // 10]
                for k in to_remove:
                    del self._cache[k]

            self._cache[key] = _CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        """Remove value from cache."""
        with self._lock:
            self._cache.pop(key, None)
