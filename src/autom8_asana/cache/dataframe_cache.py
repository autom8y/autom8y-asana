"""DataFrame caching with tiered storage for entity resolution.

Per TDD-DATAFRAME-CACHE-001: Provides unified caching for all entity types
with Memory + S3 tiering, request coalescing, and circuit breaker patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
    from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
    from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
    from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier

logger = get_logger(__name__)


def _get_schema_version_for_entity(entity_type: str) -> str | None:
    """Look up schema version from SchemaRegistry for an entity type.

    Args:
        entity_type: Entity type in lowercase (e.g., "unit", "contact").

    Returns:
        Schema version string if found, None if lookup fails.
    """
    try:
        from autom8_asana.dataframes.models.registry import SchemaRegistry
        from autom8_asana.services.resolver import to_pascal_case

        registry = SchemaRegistry.get_instance()
        # Convert entity_type to PascalCase for registry lookup
        # e.g., "unit" -> "Unit", "asset_edit" -> "AssetEdit"
        registry_key = to_pascal_case(entity_type)
        schema = registry.get_schema(registry_key)
        return schema.version
    except Exception as e:
        logger.warning(
            "schema_version_lookup_failed",
            extra={
                "entity_type": entity_type,
                "error": str(e),
            },
        )
        return None


@dataclass
class CacheEntry:
    """Single DataFrame cache entry with metadata.

    Per TDD-DATAFRAME-CACHE-001: Immutable entry containing a cached DataFrame
    with freshness tracking via watermarks and schema versioning.

    Attributes:
        project_gid: Asana project GID this DataFrame belongs to.
        entity_type: Entity type (unit, business, offer, contact).
        dataframe: Polars DataFrame containing entity data.
        watermark: Freshness watermark based on max(modified_at).
        created_at: When this cache entry was created.
        schema_version: Schema version for invalidation on version bumps.
        row_count: Number of rows in the DataFrame (computed).

    Example:
        >>> entry = CacheEntry(
        ...     project_gid="1234567890",
        ...     entity_type="unit",
        ...     dataframe=df,
        ...     watermark=datetime.now(timezone.utc),
        ...     created_at=datetime.now(timezone.utc),
        ...     schema_version="1.0.0",
        ... )
        >>> entry.is_stale(ttl_seconds=3600)
        False
    """

    project_gid: str
    entity_type: str
    dataframe: pl.DataFrame
    watermark: datetime
    created_at: datetime
    schema_version: str
    row_count: int = field(init=False)

    def __post_init__(self) -> None:
        """Compute row_count from DataFrame."""
        self.row_count = len(self.dataframe)

    def is_stale(self, ttl_seconds: int) -> bool:
        """Check if entry has exceeded TTL.

        Args:
            ttl_seconds: Maximum age in seconds before entry is stale.

        Returns:
            True if entry age exceeds ttl_seconds.
        """
        age = datetime.now(timezone.utc) - self.created_at
        return age.total_seconds() > ttl_seconds

    def is_fresh_by_watermark(self, current_watermark: datetime) -> bool:
        """Check if entry is fresh based on watermark comparison.

        The entry is fresh if its watermark is >= the current watermark,
        meaning no newer data exists in the source.

        Args:
            current_watermark: Current max(modified_at) from source.

        Returns:
            True if entry watermark >= current_watermark.
        """
        return self.watermark >= current_watermark


@dataclass
class DataFrameCache:
    """Unified DataFrame cache with tiered storage.

    Per TDD-DATAFRAME-CACHE-001 and TDD-UNIFIED-PROGRESSIVE-CACHE-001:
    - Memory tier for hot cache (sub-millisecond access)
    - Progressive tier for cold storage (uses SectionPersistence location)
    - Request coalescing to prevent thundering herd
    - Circuit breaker for failure isolation

    Lookup order for GET:
    1. Memory tier (hot cache)
    2. Progressive tier (cold storage via SectionPersistence)
    3. Return None (caller should trigger build)

    Write order for PUT:
    1. Progressive tier (source of truth)
    2. Memory tier (hot cache)

    Attributes:
        memory_tier: Hot cache with dynamic heap-based limits.
        progressive_tier: Cold storage using SectionPersistence location.
        coalescer: Request coalescing for build deduplication.
        circuit_breaker: Per-project failure isolation.
        ttl_hours: Default TTL in hours (12-24 configurable).
        schema_version: Current schema version for invalidation.

    Example:
        >>> cache = DataFrameCache(
        ...     memory_tier=MemoryTier(max_heap_percent=0.3),
        ...     progressive_tier=ProgressiveTier(persistence=persistence),
        ...     coalescer=DataFrameCacheCoalescer(),
        ...     circuit_breaker=CircuitBreaker(),
        ...     ttl_hours=12,
        ... )
        >>>
        >>> # Get DataFrame (tries memory, then progressive tier, then returns None)
        >>> entry = await cache.get_async("project-123", "unit")
        >>>
        >>> # Store after build
        >>> await cache.put_async("project-123", "unit", df, watermark)
    """

    memory_tier: "MemoryTier"
    progressive_tier: "ProgressiveTier"
    coalescer: "DataFrameCacheCoalescer"
    circuit_breaker: "CircuitBreaker"
    ttl_hours: int = 12
    schema_version: str = "1.0.0"

    # Statistics per entity type
    _stats: dict[str, dict[str, int]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize per-entity-type statistics."""
        for entity_type in ["unit", "business", "offer", "contact"]:
            self._stats[entity_type] = {
                "memory_hits": 0,
                "memory_misses": 0,
                "s3_hits": 0,
                "s3_misses": 0,
                "builds_triggered": 0,
                "builds_coalesced": 0,
                "circuit_breaks": 0,
                "invalidations": 0,
            }

    async def get_async(
        self,
        project_gid: str,
        entity_type: str,
        current_watermark: datetime | None = None,
    ) -> CacheEntry | None:
        """Get cached DataFrame entry.

        Lookup order:
        1. Memory tier (hot cache)
        2. Progressive tier (cold storage via SectionPersistence)
        3. Return None (caller should trigger build)

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type (unit, business, offer, contact).
            current_watermark: Optional watermark for freshness check.

        Returns:
            CacheEntry if found and fresh, None otherwise.
        """
        cache_key = self._build_key(project_gid, entity_type)

        # Check circuit breaker
        if self.circuit_breaker.is_open(project_gid):
            self._stats[entity_type]["circuit_breaks"] += 1
            logger.warning(
                "dataframe_cache_circuit_open",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                },
            )
            return None

        # Try memory tier first
        entry = self.memory_tier.get(cache_key)
        if entry is not None:
            # Validate freshness
            if self._is_valid(entry, current_watermark):
                self._stats[entity_type]["memory_hits"] += 1
                logger.debug(
                    "dataframe_cache_memory_hit",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                        "row_count": entry.row_count,
                    },
                )
                return entry
            else:
                # Stale - remove from memory
                self.memory_tier.remove(cache_key)

        self._stats[entity_type]["memory_misses"] += 1

        # Try progressive tier (S3 via SectionPersistence)
        entry = await self.progressive_tier.get_async(cache_key)
        if entry is not None:
            if self._is_valid(entry, current_watermark):
                self._stats[entity_type]["s3_hits"] += 1
                # Hydrate memory tier
                self.memory_tier.put(cache_key, entry)
                logger.info(
                    "dataframe_cache_s3_hit",
                    extra={
                        "project_gid": project_gid,
                        "entity_type": entity_type,
                        "row_count": entry.row_count,
                    },
                )
                return entry

        self._stats[entity_type]["s3_misses"] += 1
        return None

    async def put_async(
        self,
        project_gid: str,
        entity_type: str,
        dataframe: pl.DataFrame,
        watermark: datetime,
    ) -> None:
        """Store DataFrame in both tiers.

        Write order:
        1. S3 tier (source of truth)
        2. Memory tier (hot cache)

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type.
            dataframe: Polars DataFrame to cache.
            watermark: Freshness watermark (based on max modified_at).
        """
        cache_key = self._build_key(project_gid, entity_type)

        # Look up schema version from registry for this entity type
        schema_version = _get_schema_version_for_entity(entity_type)
        if schema_version is None:
            # Fallback to instance default if registry lookup fails
            schema_version = self.schema_version
            logger.warning(
                "put_async_schema_version_fallback",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "fallback_version": schema_version,
                },
            )

        entry = CacheEntry(
            project_gid=project_gid,
            entity_type=entity_type,
            dataframe=dataframe,
            watermark=watermark,
            created_at=datetime.now(timezone.utc),
            schema_version=schema_version,
        )

        # Write to progressive tier first (source of truth)
        await self.progressive_tier.put_async(cache_key, entry)

        # Then memory tier
        self.memory_tier.put(cache_key, entry)

        # Clear circuit breaker on successful write
        self.circuit_breaker.close(project_gid)

        logger.info(
            "dataframe_cache_put",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "row_count": entry.row_count,
                "watermark": watermark.isoformat(),
            },
        )

    def invalidate(
        self,
        project_gid: str,
        entity_type: str | None = None,
    ) -> None:
        """Invalidate cache entries.

        Args:
            project_gid: Project to invalidate.
            entity_type: Optional specific entity type. If None, all types.
        """
        entity_types = (
            [entity_type] if entity_type else ["unit", "business", "offer", "contact"]
        )

        for et in entity_types:
            cache_key = self._build_key(project_gid, et)
            self.memory_tier.remove(cache_key)
            # Note: S3 entries not deleted, just superseded on next write
            self._stats[et]["invalidations"] += 1

        logger.info(
            "dataframe_cache_invalidate",
            extra={
                "project_gid": project_gid,
                "entity_types": entity_types,
            },
        )

    def invalidate_on_schema_change(self, new_version: str) -> None:
        """Invalidate all entries when schema version changes.

        Per TDD: Auto-invalidate on version bump.

        Args:
            new_version: New schema version string.
        """
        if new_version != self.schema_version:
            logger.info(
                "dataframe_cache_schema_invalidation",
                extra={
                    "old_version": self.schema_version,
                    "new_version": new_version,
                },
            )
            self.memory_tier.clear()
            self.schema_version = new_version

    async def acquire_build_lock_async(
        self,
        project_gid: str,
        entity_type: str,
    ) -> bool:
        """Attempt to acquire build lock via coalescer.

        Returns True if this request should perform the build.
        Returns False if another request is building (wait for it).

        Args:
            project_gid: Project to build.
            entity_type: Entity type to build.

        Returns:
            True if caller should build, False if should wait.
        """
        cache_key = self._build_key(project_gid, entity_type)
        acquired = await self.coalescer.try_acquire_async(cache_key)

        if acquired:
            self._stats[entity_type]["builds_triggered"] += 1
        else:
            self._stats[entity_type]["builds_coalesced"] += 1

        return acquired

    async def release_build_lock_async(
        self,
        project_gid: str,
        entity_type: str,
        success: bool,
    ) -> None:
        """Release build lock and notify waiters.

        Args:
            project_gid: Project that was built.
            entity_type: Entity type that was built.
            success: Whether build succeeded.
        """
        cache_key = self._build_key(project_gid, entity_type)
        await self.coalescer.release_async(cache_key, success)

        if not success:
            self.circuit_breaker.record_failure(project_gid)

    async def wait_for_build_async(
        self,
        project_gid: str,
        entity_type: str,
        timeout_seconds: float = 30.0,
    ) -> CacheEntry | None:
        """Wait for in-progress build to complete.

        Args:
            project_gid: Project being built.
            entity_type: Entity type being built.
            timeout_seconds: Maximum wait time.

        Returns:
            CacheEntry if build succeeded, None on timeout/failure.
        """
        cache_key = self._build_key(project_gid, entity_type)
        success = await self.coalescer.wait_async(cache_key, timeout_seconds)

        if success:
            return await self.get_async(project_gid, entity_type)
        return None

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Get per-entity-type cache statistics."""
        return {k: dict(v) for k, v in self._stats.items()}

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        for stats in self._stats.values():
            for key in stats:
                stats[key] = 0

    def _build_key(self, project_gid: str, entity_type: str) -> str:
        """Build cache key from project and entity type."""
        return f"{entity_type}:{project_gid}"

    def _is_valid(
        self,
        entry: CacheEntry,
        current_watermark: datetime | None,
    ) -> bool:
        """Check if entry is valid (not stale, correct schema).

        Schema version validation uses the SchemaRegistry to look up the
        expected version for the entry's entity type, rather than comparing
        against a hardcoded cache-level version. This ensures cache entries
        are invalidated when individual entity schemas are bumped.
        """
        # Schema version check using registry lookup
        expected_version = _get_schema_version_for_entity(entry.entity_type)
        if expected_version is None:
            # Registry lookup failed - treat as invalid to force rebuild
            logger.warning(
                "cache_entry_invalid_no_schema",
                extra={
                    "entity_type": entry.entity_type,
                    "entry_version": entry.schema_version,
                },
            )
            return False

        if entry.schema_version != expected_version:
            logger.debug(
                "cache_entry_version_mismatch",
                extra={
                    "entity_type": entry.entity_type,
                    "entry_version": entry.schema_version,
                    "expected_version": expected_version,
                },
            )
            return False

        # TTL check
        ttl_seconds = self.ttl_hours * 3600
        if entry.is_stale(ttl_seconds):
            return False

        # Watermark check (if provided)
        if current_watermark is not None:
            if not entry.is_fresh_by_watermark(current_watermark):
                return False

        return True


# Module-level singleton for easy access
_dataframe_cache: DataFrameCache | None = None


def get_dataframe_cache() -> DataFrameCache | None:
    """Get the singleton DataFrameCache instance.

    Returns:
        DataFrameCache if initialized, None otherwise.
    """
    return _dataframe_cache


def set_dataframe_cache(cache: DataFrameCache) -> None:
    """Set the singleton DataFrameCache instance.

    Args:
        cache: DataFrameCache instance to set as singleton.
    """
    global _dataframe_cache
    _dataframe_cache = cache


def reset_dataframe_cache() -> None:
    """Reset the singleton DataFrameCache (for testing)."""
    global _dataframe_cache
    _dataframe_cache = None
