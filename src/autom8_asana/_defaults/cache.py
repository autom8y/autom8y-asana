"""Default cache providers with versioning support."""

from __future__ import annotations

import time
from threading import Lock
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.cache.models.entry import CacheEntry, EntryType
    from autom8_asana.cache.models.freshness_unified import FreshnessIntent
    from autom8_asana.cache.models.metrics import CacheMetrics
    from autom8_asana.protocols.cache import WarmResult


class _CacheEntry(NamedTuple):
    """Internal cache entry for simple key-value storage."""

    value: dict[str, Any]
    expires_at: float | None


class NullCacheProvider:
    """Cache provider that does nothing (no-op).

    This is the default when no caching is desired.
    All operations succeed silently but don't store anything.

    Implements the full CacheProvider protocol including versioned
    operations, all of which are no-ops.
    """

    # === Original methods (backward compatible) ===

    def get(self, key: str) -> dict[str, Any] | None:
        """Always returns None (cache miss)."""
        return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Does nothing."""
        pass

    def delete(self, key: str) -> None:
        """Does nothing."""
        pass

    # === New versioned methods (all no-op) ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: FreshnessIntent | None = None,
    ) -> CacheEntry | None:
        """Always returns None (cache miss)."""
        return None

    def set_versioned(
        self,
        key: str,
        entry: CacheEntry,
    ) -> None:
        """Does nothing."""
        pass

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Returns all misses."""
        return {key: None for key in keys}

    def set_batch(
        self,
        entries: dict[str, CacheEntry],
    ) -> None:
        """Does nothing."""
        pass

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Returns empty result."""
        from autom8_asana.protocols.cache import WarmResult

        return WarmResult(warmed=0, failed=0, skipped=len(gids))

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Always returns False (not fresh)."""
        return False

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Does nothing."""
        pass

    def is_healthy(self) -> bool:
        """Always returns True (null cache is always healthy)."""
        return True

    def get_metrics(self) -> CacheMetrics:
        """Returns a new empty CacheMetrics instance."""
        from autom8_asana.cache.models.metrics import CacheMetrics

        return CacheMetrics()

    def reset_metrics(self) -> None:
        """Does nothing (no metrics to reset)."""
        pass

    def clear_all_tasks(self) -> int:
        """Does nothing (no cache to clear)."""
        return 0


class _VersionedEntry(NamedTuple):
    """Internal versioned cache entry."""

    entry: Any  # CacheEntry
    expires_at: float | None


class InMemoryCacheProvider:
    """Simple in-memory cache with TTL and versioning support.

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
        self._versioned_cache: dict[str, _VersionedEntry] = {}
        self._version_metadata: dict[str, dict[str, datetime]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = Lock()
        self._metrics: CacheMetrics | None = None

    def _get_metrics(self) -> CacheMetrics:
        """Lazily initialize metrics."""
        if self._metrics is None:
            from autom8_asana.cache.models.metrics import CacheMetrics

            self._metrics = CacheMetrics()
        return self._metrics

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if at capacity. Called with lock held."""
        total = len(self._cache) + len(self._versioned_cache)
        if total < self._max_size:
            return

        # Remove first 10% of simple entries
        to_remove = list(self._cache.keys())[: self._max_size // 10]
        for k in to_remove:
            del self._cache[k]

        # Remove first 10% of versioned entries
        to_remove = list(self._versioned_cache.keys())[: self._max_size // 10]
        for k in to_remove:
            del self._versioned_cache[k]

    # === Original methods (backward compatible) ===

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
            self._evict_if_needed()
            self._cache[key] = _CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> None:
        """Remove value from cache."""
        with self._lock:
            self._cache.pop(key, None)

    # === New versioned methods ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: FreshnessIntent | None = None,
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            freshness: FreshnessIntent mode (ignored for in-memory).

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        internal_key = f"{key}:{entry_type.value}"

        with self._lock:
            cached = self._versioned_cache.get(internal_key)
            if cached is None:
                return None

            if cached.expires_at is not None and time.time() > cached.expires_at:
                del self._versioned_cache[internal_key]
                return None

            # Check CacheEntry's own expiration
            if cached.entry.is_expired():
                del self._versioned_cache[internal_key]
                return None

            entry: CacheEntry = cached.entry
            return entry

    def set_versioned(
        self,
        key: str,
        entry: CacheEntry,
    ) -> None:
        """Store versioned cache entry.

        Args:
            key: Cache key.
            entry: CacheEntry with data and metadata.
        """
        internal_key = f"{key}:{entry.entry_type.value}"
        expires_at = None
        if entry.ttl is not None:
            expires_at = time.time() + entry.ttl

        with self._lock:
            self._evict_if_needed()
            self._versioned_cache[internal_key] = _VersionedEntry(
                entry=entry, expires_at=expires_at
            )

            # Update version metadata
            if key not in self._version_metadata:
                self._version_metadata[key] = {}
            self._version_metadata[key][entry.entry_type.value] = entry.version

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries.

        Returns:
            Dict mapping keys to CacheEntry or None.
        """
        result: dict[str, CacheEntry | None] = {}
        for key in keys:
            result[key] = self.get_versioned(key, entry_type)
        return result

    def set_batch(
        self,
        entries: dict[str, CacheEntry],
    ) -> None:
        """Store multiple entries.

        Args:
            entries: Dict mapping keys to CacheEntry objects.
        """
        for key, entry in entries.items():
            self.set_versioned(key, entry)

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Pre-populate cache (not implemented).

        Args:
            gids: List of task GIDs.
            entry_types: Entry types to warm.

        Returns:
            WarmResult indicating all skipped.
        """
        from autom8_asana.protocols.cache import WarmResult

        return WarmResult(warmed=0, failed=0, skipped=len(gids))

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if cached version matches current.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            current_version: Known current modified_at.

        Returns:
            True if fresh, False if stale or missing.
        """
        from autom8_asana.cache.models.versioning import is_current

        with self._lock:
            metadata = self._version_metadata.get(key)
            if metadata is None:
                return False

            cached_version = metadata.get(entry_type.value)
            if cached_version is None:
                return False

            return is_current(cached_version, current_version)

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries.

        Args:
            key: Cache key.
            entry_types: Specific types to invalidate. If None, all.
        """
        from autom8_asana.cache.models.entry import EntryType

        if entry_types is None:
            entry_types = list(EntryType)

        with self._lock:
            for entry_type in entry_types:
                internal_key = f"{key}:{entry_type.value}"
                self._versioned_cache.pop(internal_key, None)

            # Clean up metadata
            if key in self._version_metadata:
                for entry_type in entry_types:
                    self._version_metadata[key].pop(entry_type.value, None)
                if not self._version_metadata[key]:
                    del self._version_metadata[key]

    def is_healthy(self) -> bool:
        """Check if cache is healthy (always True for in-memory)."""
        return True

    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics aggregator."""
        return self._get_metrics()

    def reset_metrics(self) -> None:
        """Reset cache metrics."""
        if self._metrics is not None:
            self._metrics.reset()

    def clear_all_tasks(self) -> int:
        """Clear all task entries from cache.

        Returns:
            Number of entries deleted.
        """
        deleted = 0
        with self._lock:
            task_keys = [k for k in self._versioned_cache if k.endswith(":task")]
            for k in task_keys:
                del self._versioned_cache[k]
                deleted += 1
        return deleted
