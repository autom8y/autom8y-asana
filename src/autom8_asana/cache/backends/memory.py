"""Enhanced in-memory cache provider with versioning support."""

from __future__ import annotations

import time
from datetime import datetime
from threading import Lock
from typing import Any, NamedTuple

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.metrics import CacheMetrics
from autom8_asana.cache.settings import CacheSettings
from autom8_asana.cache.versioning import is_current
from autom8_asana.protocols.cache import WarmResult


class _SimpleCacheEntry(NamedTuple):
    """Internal cache entry for simple key-value storage."""

    value: dict[str, Any]
    expires_at: float | None


class _VersionedCacheEntry(NamedTuple):
    """Internal cache entry for versioned storage."""

    entry: CacheEntry
    expires_at: float | None


class EnhancedInMemoryCacheProvider:
    """Thread-safe in-memory cache with versioning support.

    Implements the CacheProvider protocol using in-memory storage.
    Suitable for development, testing, and single-process deployments.

    Thread Safety:
        All operations are protected by a threading.Lock for
        safe concurrent access (ADR-0024).

    Features:
        - TTL-based expiration
        - LRU eviction when max_size reached
        - Full versioned operations support
        - Metrics tracking

    Limitations:
        - Not shared across processes
        - Lost on process restart
        - Memory-bound (no persistence)

    Example:
        >>> cache = EnhancedInMemoryCacheProvider(default_ttl=300, max_size=10000)
        >>> cache.set("key", {"data": "value"})
        >>> cache.get("key")
        {'data': 'value'}
    """

    def __init__(
        self,
        default_ttl: int | None = 300,
        max_size: int = 10000,
        settings: CacheSettings | None = None,
    ) -> None:
        """Initialize in-memory cache.

        Args:
            default_ttl: Default TTL in seconds (None = no expiration).
            max_size: Maximum number of entries before eviction.
            settings: Optional cache settings for advanced configuration.
        """
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._settings = settings or CacheSettings()

        # Separate storage for simple and versioned entries
        self._simple_cache: dict[str, _SimpleCacheEntry] = {}
        self._versioned_cache: dict[str, _VersionedCacheEntry] = {}
        self._version_metadata: dict[str, dict[str, datetime]] = {}

        self._lock = Lock()
        self._metrics = CacheMetrics()

    def _make_versioned_key(self, key: str, entry_type: EntryType) -> str:
        """Generate internal key for versioned entries.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry.

        Returns:
            Combined key string.
        """
        return f"{key}:{entry_type.value}"

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if at capacity.

        Called with lock held.
        """
        total_size = len(self._simple_cache) + len(self._versioned_cache)
        if total_size < self._max_size:
            return

        # Remove first 10% of simple entries
        to_remove = list(self._simple_cache.keys())[: self._max_size // 10]
        for k in to_remove:
            del self._simple_cache[k]
            self._metrics.record_eviction(key=k)

        # Remove first 10% of versioned entries
        to_remove = list(self._versioned_cache.keys())[: self._max_size // 10]
        for k in to_remove:
            del self._versioned_cache[k]
            self._metrics.record_eviction(key=k)

    def _cleanup_expired(self) -> None:
        """Remove expired entries.

        Called periodically or when convenient. Lock must be held.
        """
        now = time.time()

        # Clean simple cache
        expired_simple = [
            k
            for k, v in self._simple_cache.items()
            if v.expires_at is not None and now > v.expires_at
        ]
        for k in expired_simple:
            del self._simple_cache[k]

        # Clean versioned cache
        expired_versioned = [
            k
            for k, v in self._versioned_cache.items()
            if v.expires_at is not None and now > v.expires_at
        ]
        for k in expired_versioned:
            del self._versioned_cache[k]

    # === Original methods (backward compatible) ===

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve value from cache (simple key-value).

        Args:
            key: Cache key.

        Returns:
            Cached dict if found and not expired, None otherwise.
        """
        start = time.perf_counter()
        with self._lock:
            entry = self._simple_cache.get(key)
            if entry is None:
                latency = (time.perf_counter() - start) * 1000
                self._metrics.record_miss(latency, key=key)
                return None

            if entry.expires_at is not None and time.time() > entry.expires_at:
                del self._simple_cache[key]
                latency = (time.perf_counter() - start) * 1000
                self._metrics.record_miss(latency, key=key)
                return None

            latency = (time.perf_counter() - start) * 1000
            self._metrics.record_hit(latency, key=key)
            return entry.value

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in cache (simple key-value).

        Args:
            key: Cache key.
            value: Dict to cache.
            ttl: Time-to-live in seconds, None uses default.
        """
        start = time.perf_counter()
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        with self._lock:
            self._evict_if_needed()
            self._simple_cache[key] = _SimpleCacheEntry(
                value=value, expires_at=expires_at
            )

        latency = (time.perf_counter() - start) * 1000
        self._metrics.record_write(latency, key=key)

    def delete(self, key: str) -> None:
        """Remove value from cache.

        Args:
            key: Cache key to delete.
        """
        with self._lock:
            if key in self._simple_cache:
                del self._simple_cache[key]
                self._metrics.record_eviction(key=key)

    # === New versioned methods ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness | None = None,
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry with freshness control.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry.
            freshness: Freshness mode (STRICT/EVENTUAL).

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        if freshness is None:
            freshness = Freshness.EVENTUAL

        start = time.perf_counter()
        internal_key = self._make_versioned_key(key, entry_type)
        entry_type_str = entry_type.value

        with self._lock:
            cached = self._versioned_cache.get(internal_key)
            if cached is None:
                latency = (time.perf_counter() - start) * 1000
                self._metrics.record_miss(latency, key=key, entry_type=entry_type_str)
                return None

            # Check time-based expiration
            if cached.expires_at is not None and time.time() > cached.expires_at:
                del self._versioned_cache[internal_key]
                latency = (time.perf_counter() - start) * 1000
                self._metrics.record_miss(latency, key=key, entry_type=entry_type_str)
                return None

            # Check CacheEntry's own expiration
            if cached.entry.is_expired():
                del self._versioned_cache[internal_key]
                latency = (time.perf_counter() - start) * 1000
                self._metrics.record_miss(latency, key=key, entry_type=entry_type_str)
                return None

            latency = (time.perf_counter() - start) * 1000
            self._metrics.record_hit(latency, key=key, entry_type=entry_type_str)
            return cached.entry

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
        start = time.perf_counter()
        internal_key = self._make_versioned_key(key, entry.entry_type)
        entry_type_str = entry.entry_type.value

        expires_at = None
        if entry.ttl is not None:
            expires_at = time.time() + entry.ttl

        with self._lock:
            self._evict_if_needed()
            self._versioned_cache[internal_key] = _VersionedCacheEntry(
                entry=entry, expires_at=expires_at
            )

            # Update version metadata
            if key not in self._version_metadata:
                self._version_metadata[key] = {}
            self._version_metadata[key][entry_type_str] = entry.version

        latency = (time.perf_counter() - start) * 1000
        self._metrics.record_write(latency, key=key, entry_type=entry_type_str)

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries in single operation.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries to retrieve.

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
        """Store multiple entries in single operation.

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
        """Pre-populate cache for specified GIDs.

        Note: Actual warming requires API calls which are out of scope
        for Phase 1. Returns placeholder result.

        Args:
            gids: List of task GIDs to warm.
            entry_types: Entry types to warm.

        Returns:
            WarmResult with counts.
        """
        # Warming requires integration with TasksClient
        return WarmResult(warmed=0, failed=0, skipped=len(gids))

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if cached version matches current version.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            current_version: Known current modified_at.

        Returns:
            True if cache is fresh, False if stale or missing.
        """
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
        """Invalidate cache entries for a key.

        Args:
            key: Cache key (task GID).
            entry_types: Specific types to invalidate. If None, all types.
        """
        if entry_types is None:
            entry_types = list(EntryType)

        with self._lock:
            for entry_type in entry_types:
                internal_key = self._make_versioned_key(key, entry_type)
                if internal_key in self._versioned_cache:
                    del self._versioned_cache[internal_key]
                    self._metrics.record_eviction(key=key, entry_type=entry_type.value)

            # Clean up metadata
            if key in self._version_metadata:
                for entry_type in entry_types:
                    self._version_metadata[key].pop(entry_type.value, None)
                if not self._version_metadata[key]:
                    del self._version_metadata[key]

    def is_healthy(self) -> bool:
        """Check if cache backend is operational.

        In-memory cache is always healthy.

        Returns:
            True (always).
        """
        return True

    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics aggregator.

        Returns:
            CacheMetrics instance.
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset cache metrics to zero."""
        self._metrics.reset()

    def clear(self) -> None:
        """Clear all cache entries.

        Useful for testing.
        """
        with self._lock:
            self._simple_cache.clear()
            self._versioned_cache.clear()
            self._version_metadata.clear()

    def size(self) -> int:
        """Get total number of cached entries.

        Returns:
            Total count of simple and versioned entries.
        """
        with self._lock:
            return len(self._simple_cache) + len(self._versioned_cache)
