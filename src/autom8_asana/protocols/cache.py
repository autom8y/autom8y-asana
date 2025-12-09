"""Cache provider protocol."""

from typing import Any, Protocol


class CacheProvider(Protocol):
    """Protocol for caching Asana API responses.

    Implementations can range from no-op (NullCacheProvider) to
    distributed caches (Redis, S3-backed).

    Cache keys are formatted as: "{resource_type}:{gid}" (e.g., "task:12345")
    """

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached dict if found, None if miss
        """
        ...

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Dict to cache
            ttl: Time-to-live in seconds, None for no expiration
        """
        ...

    def delete(self, key: str) -> None:
        """Remove value from cache.

        Args:
            key: Cache key to delete
        """
        ...
