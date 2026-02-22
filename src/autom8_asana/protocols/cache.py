"""Cache provider protocol with versioned operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.cache.integration.dataframe_cache import (
        DataFrameCacheEntry,
        FreshnessInfo,
    )
    from autom8_asana.cache.models.entry import CacheEntry, EntryType
    from autom8_asana.cache.models.freshness import Freshness
    from autom8_asana.cache.models.metrics import CacheMetrics


class CacheProvider(Protocol):
    """Protocol for caching Asana API responses with versioning support.

    This protocol defines both basic key-value caching operations and
    advanced versioned operations for intelligent cache invalidation.

    Basic operations (backward compatible):
        - get/set/delete: Simple key-value caching

    Versioned operations (new):
        - get_versioned/set_versioned: Version-aware caching
        - get_batch/set_batch: Batch operations for efficiency
        - warm: Pre-populate cache
        - check_freshness: Validate cache against source version
        - invalidate: Remove entries by key and type
        - is_healthy: Backend health check

    Cache keys are formatted as: "{resource_type}:{gid}" (e.g., "task:12345")

    Implementations:
        - NullCacheProvider: No-op (default when caching disabled)
        - InMemoryCacheProvider: Thread-safe in-memory (development/testing)
        - RedisCacheProvider: Production Redis backend
    """

    # === Original methods (backward compatible) ===

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve value from cache (simple key-value).

        Args:
            key: Cache key.

        Returns:
            Cached dict if found, None if miss.
        """
        ...

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in cache (simple key-value).

        Args:
            key: Cache key.
            value: Dict to cache.
            ttl: Time-to-live in seconds, None for no expiration.
        """
        ...

    def delete(self, key: str) -> None:
        """Remove value from cache.

        Args:
            key: Cache key to delete.
        """
        ...

    # === New versioned methods ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness | None = None,
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry with freshness control.

        Args:
            key: Cache key (e.g., task GID "1234567890").
            entry_type: Type of entry for version resolution.
            freshness: STRICT validates version, EVENTUAL returns without check.
                Defaults to EVENTUAL if None.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        ...

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
        ...

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries in single operation.

        Efficient batch retrieval for multiple keys of the same type.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries to retrieve.

        Returns:
            Dict mapping keys to CacheEntry or None if not found.
        """
        ...

    def set_batch(
        self,
        entries: dict[str, CacheEntry],
    ) -> None:
        """Store multiple entries in single operation.

        Efficient batch write for multiple entries.

        Args:
            entries: Dict mapping keys to CacheEntry objects.
        """
        ...

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Pre-populate cache for specified GIDs and entry types.

        Used to warm the cache before anticipated access patterns.

        Args:
            gids: List of task GIDs to warm.
            entry_types: Entry types to fetch and cache.
                If None, warms all applicable types.

        Returns:
            WarmResult with success/failure counts.
        """
        ...

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if cached version matches current version.

        Used for staleness detection without retrieving full entry.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            current_version: Known current modified_at timestamp.

        Returns:
            True if cache is fresh, False if stale or missing.
        """
        ...

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries for a key.

        Args:
            key: Cache key (task GID).
            entry_types: Specific types to invalidate.
                If None, invalidates all types for the key.
        """
        ...

    def is_healthy(self) -> bool:
        """Check if cache backend is operational.

        Returns:
            True if backend is healthy and responding.
        """
        ...

    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics aggregator.

        Returns:
            CacheMetrics instance with hit/miss statistics.
        """
        ...

    def reset_metrics(self) -> None:
        """Reset cache metrics to zero."""
        ...

    def clear_all_tasks(self) -> int:
        """Clear all task entries from cache.

        Used for cache invalidation when cached data becomes stale
        or corrupted (e.g., missing required fields like memberships).

        Returns:
            Number of entries deleted.
        """
        ...


class WarmResult:
    """Result of cache warm operation.

    Attributes:
        warmed: Number of entries successfully warmed.
        failed: Number of entries that failed to warm.
        skipped: Number of entries skipped (already cached).
    """

    __slots__ = ("warmed", "failed", "skipped")

    def __init__(self, warmed: int = 0, failed: int = 0, skipped: int = 0) -> None:
        """Initialize warm result.

        Args:
            warmed: Count of successfully warmed entries.
            failed: Count of failed warming attempts.
            skipped: Count of skipped entries (already cached).
        """
        self.warmed = warmed
        self.failed = failed
        self.skipped = skipped

    @property
    def total(self) -> int:
        """Total number of entries processed."""
        return self.warmed + self.failed + self.skipped

    def __repr__(self) -> str:
        """String representation."""
        return f"WarmResult(warmed={self.warmed}, failed={self.failed}, skipped={self.skipped})"


class DataFrameCacheProtocol(Protocol):
    """Protocol for the unified DataFrame cache with tiered storage.

    Captures the public interface of ``DataFrameCache`` for dependency
    injection boundaries.  Implementations must provide tiered get/put,
    project-scoped invalidation, and schema-change invalidation.

    Per ADR-0067 dimension 14: Mirrors the ``CacheProvider`` structural
    typing approach so that a ``NullDataFrameCache`` test double can be
    introduced without touching production code.

    Lookup order for GET:
        1. Memory tier (hot cache)
        2. Progressive tier (cold storage via SectionPersistence)
        3. Return None (caller should trigger build)

    Write order for PUT:
        1. Progressive tier (source of truth)
        2. Memory tier (hot cache)

    Implementations:
        - DataFrameCache: Production tiered cache (Memory + S3)
    """

    async def get_async(
        self,
        project_gid: str,
        entity_type: str,
        current_watermark: datetime | None = None,
    ) -> DataFrameCacheEntry | None:
        """Get cached DataFrame entry with entity-aware TTL and SWR.

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type (unit, business, offer, contact).
            current_watermark: Optional watermark for freshness check.

        Returns:
            DataFrameCacheEntry if found and fresh/stale-servable, None otherwise.
        """
        ...

    async def put_async(
        self,
        project_gid: str,
        entity_type: str,
        dataframe: Any,
        watermark: datetime,
        build_result: Any = None,
    ) -> None:
        """Store DataFrame in both tiers.

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type.
            dataframe: Polars DataFrame to cache.
            watermark: Freshness watermark (based on max modified_at).
            build_result: Optional BuildResult for quality metadata.
        """
        ...

    def invalidate(
        self,
        project_gid: str,
        entity_type: str | None = None,
    ) -> None:
        """Invalidate cache entries for a project and optional entity type.

        Args:
            project_gid: Project to invalidate.
            entity_type: Optional specific entity type. If None, all types.
        """
        ...

    def invalidate_project(self, project_gid: str) -> None:
        """Invalidate all cached DataFrames for a project across entity types.

        Args:
            project_gid: Project GID whose DataFrames should be invalidated.
        """
        ...

    def invalidate_on_schema_change(self, new_version: str) -> None:
        """Invalidate all entries when schema version changes.

        Args:
            new_version: New schema version string.
        """
        ...

    def get_freshness_info(
        self,
        project_gid: str,
        entity_type: str,
    ) -> FreshnessInfo | None:
        """Get freshness info from the most recent get_async() call.

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type.

        Returns:
            FreshnessInfo if available, None on cache miss or no prior call.
        """
        ...
