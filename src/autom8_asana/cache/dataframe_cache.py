"""DataFrame caching with tiered storage for entity resolution.

Per TDD-DATAFRAME-CACHE-001: Provides unified caching for all entity types
with Memory + S3 tiering, request coalescing, and circuit breaker patterns.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
    from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
    from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
    from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier

logger = get_logger(__name__)


class FreshnessStatus(str, Enum):
    """Result of entity-aware freshness check."""

    FRESH = "fresh"
    STALE_SERVABLE = "stale_servable"  # Within SWR grace window
    EXPIRED_SERVABLE = "expired_servable"  # Beyond grace, data structurally valid (LKG)
    SCHEMA_MISMATCH = "schema_mismatch"  # Hard reject
    WATERMARK_STALE = "watermark_stale"  # Hard reject
    CIRCUIT_LKG = "circuit_lkg"  # Circuit breaker open, serving LKG


@dataclass
class FreshnessInfo:
    """Freshness metadata for a cache serve operation.

    Carried as a side-channel from DataFrameCache to API response.
    Not stored in CacheEntry (freshness changes over time as data ages).
    """

    freshness: str  # FreshnessStatus value (see FreshnessStatus enum)
    data_age_seconds: float
    staleness_ratio: float  # age / entity_ttl (>1.0 means past TTL)


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
        age = datetime.now(UTC) - self.created_at
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
        schema_version: Current schema version for invalidation (fallback).

    Example:
        >>> cache = DataFrameCache(
        ...     memory_tier=MemoryTier(max_heap_percent=0.3),
        ...     progressive_tier=ProgressiveTier(persistence=persistence),
        ...     coalescer=DataFrameCacheCoalescer(),
        ...     circuit_breaker=CircuitBreaker(),
        ... )
        >>>
        >>> # Get DataFrame (tries memory, then progressive tier, then returns None)
        >>> entry = await cache.get_async("project-123", "unit")
        >>>
        >>> # Store after build
        >>> await cache.put_async("project-123", "unit", df, watermark)
    """

    memory_tier: MemoryTier
    progressive_tier: ProgressiveTier
    coalescer: DataFrameCacheCoalescer
    circuit_breaker: CircuitBreaker
    schema_version: str = "1.0.0"

    # Last freshness info per cache key (side-channel for API layer)
    _last_freshness: dict[str, FreshnessInfo] = field(
        default_factory=dict, init=False, repr=False
    )

    # Optional callback for SWR background rebuilds.
    # Signature: async def callback(project_gid: str, entity_type: str) -> None
    # The callback should build the DataFrame and call put_async() on this cache.
    _build_callback: Callable[[str, str], Awaitable[None]] | None = field(
        default=None, init=False, repr=False
    )

    # Statistics per entity type
    _stats: dict[str, dict[str, int]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize per-entity-type statistics."""
        for entity_type in ["unit", "business", "offer", "contact", "asset_edit"]:
            self._ensure_stats(entity_type)

    def _ensure_stats(self, entity_type: str) -> None:
        """Lazily initialize stats for an entity type if not present."""
        if entity_type not in self._stats:
            self._stats[entity_type] = {
                "memory_hits": 0,
                "memory_misses": 0,
                "s3_hits": 0,
                "s3_misses": 0,
                "builds_triggered": 0,
                "builds_coalesced": 0,
                "circuit_breaks": 0,
                "invalidations": 0,
                "swr_serves": 0,
                "swr_refreshes_triggered": 0,
                "lkg_serves": 0,
                "lkg_circuit_serves": 0,
            }

    async def get_async(
        self,
        project_gid: str,
        entity_type: str,
        current_watermark: datetime | None = None,
    ) -> CacheEntry | None:
        """Get cached DataFrame entry with entity-aware TTL and SWR.

        Lookup order:
        1. Memory tier (hot cache)
        2. Progressive tier (cold storage via SectionPersistence)
        3. Return None (caller should trigger build)

        Freshness states:
        - FRESH: Entry within entity TTL — serve immediately.
        - STALE_SERVABLE: Entry past TTL but within SWR grace window —
          serve stale data and trigger background refresh.
        - EXPIRED: Entry beyond grace window — treat as cache miss.

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type (unit, business, offer, contact).
            current_watermark: Optional watermark for freshness check.

        Returns:
            CacheEntry if found and fresh/stale-servable, None otherwise.
        """
        cache_key = self._build_key(project_gid, entity_type)

        # Check circuit breaker
        self._ensure_stats(entity_type)
        if self.circuit_breaker.is_open(project_gid):
            self._stats[entity_type]["circuit_breaks"] += 1
            logger.warning(
                "dataframe_cache_circuit_open",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                },
            )
            return await self._get_circuit_lkg(cache_key, project_gid, entity_type)

        # Try memory tier first
        entry = self.memory_tier.get(cache_key)
        if entry is not None:
            result = self._check_freshness_and_serve(
                entry, current_watermark, project_gid, entity_type, cache_key, "memory"
            )
            if result is not None:
                return result

        self._stats[entity_type]["memory_misses"] += 1

        # Try progressive tier (S3 via SectionPersistence)
        entry = await self.progressive_tier.get_async(cache_key)
        if entry is not None:
            result = self._check_freshness_and_serve(
                entry, current_watermark, project_gid, entity_type, cache_key, "s3"
            )
            if result is not None:
                if result is entry:
                    # Hydrate memory tier on S3 hit
                    self.memory_tier.put(cache_key, entry)
                return result

        self._stats[entity_type]["s3_misses"] += 1
        return None

    async def _get_circuit_lkg(
        self,
        cache_key: str,
        project_gid: str,
        entity_type: str,
    ) -> CacheEntry | None:
        """Serve LKG from cache when circuit breaker is open.

        Checks memory then S3. Returns entry if schema-valid.
        No refresh triggered. No staleness cap applied.

        Args:
            cache_key: Cache key for lookups.
            project_gid: Project GID for logging.
            entity_type: Entity type for stats and logging.

        Returns:
            CacheEntry if found and schema-valid, None otherwise.
        """
        # Try memory tier first
        entry = self.memory_tier.get(cache_key)
        if entry is not None and self._schema_is_valid(entry):
            self._stats[entity_type]["lkg_circuit_serves"] += 1
            self._stats[entity_type]["memory_hits"] += 1
            info = self._build_freshness_info(entry, FreshnessStatus.CIRCUIT_LKG, cache_key)
            logger.info(
                "dataframe_cache_circuit_lkg_serve",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "tier": "memory",
                    "row_count": entry.row_count,
                    "age_seconds": info.data_age_seconds,
                },
            )
            return entry

        # Try progressive tier (read-only, no refresh)
        entry = await self.progressive_tier.get_async(cache_key)
        if entry is not None and self._schema_is_valid(entry):
            self.memory_tier.put(cache_key, entry)
            self._stats[entity_type]["lkg_circuit_serves"] += 1
            self._stats[entity_type]["s3_hits"] += 1
            info = self._build_freshness_info(entry, FreshnessStatus.CIRCUIT_LKG, cache_key)
            logger.info(
                "dataframe_cache_circuit_lkg_serve",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "tier": "s3",
                    "row_count": entry.row_count,
                    "age_seconds": info.data_age_seconds,
                },
            )
            return entry

        # No LKG entry available
        logger.warning(
            "dataframe_cache_circuit_open_no_lkg",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
            },
        )
        return None

    def _check_freshness_and_serve(
        self,
        entry: CacheEntry,
        current_watermark: datetime | None,
        project_gid: str,
        entity_type: str,
        cache_key: str,
        tier: str,
    ) -> CacheEntry | None:
        """Check entry freshness and handle SWR/LKG logic for a tier.

        Returns the entry if servable (fresh, stale-within-grace, or LKG),
        None if hard-rejected (schema mismatch or watermark stale).
        """
        status = self._check_freshness(entry, current_watermark)

        # Build freshness info for servable states
        if status in (
            FreshnessStatus.FRESH,
            FreshnessStatus.STALE_SERVABLE,
            FreshnessStatus.EXPIRED_SERVABLE,
        ):
            info = self._build_freshness_info(entry, status, cache_key)
        else:
            info = None

        if status == FreshnessStatus.FRESH:
            self._stats[entity_type][f"{tier}_hits"] += 1
            logger.debug(
                f"dataframe_cache_{tier}_hit",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "row_count": entry.row_count,
                    "freshness": "fresh",
                },
            )
            return entry

        if status == FreshnessStatus.STALE_SERVABLE:
            self._stats[entity_type][f"{tier}_hits"] += 1
            self._stats[entity_type]["swr_serves"] += 1
            logger.info(
                f"dataframe_cache_{tier}_swr_serve",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "row_count": entry.row_count,
                    "age_seconds": info.data_age_seconds,
                    "freshness": "stale_servable",
                },
            )
            self._trigger_swr_refresh(project_gid, entity_type, cache_key)
            return entry

        if status == FreshnessStatus.EXPIRED_SERVABLE:
            # Check max staleness policy before serving
            from autom8_asana.config import (
                DEFAULT_ENTITY_TTLS,
                DEFAULT_TTL,
                LKG_MAX_STALENESS_MULTIPLIER,
            )

            entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
            age = info.data_age_seconds

            if LKG_MAX_STALENESS_MULTIPLIER > 0:
                max_age = LKG_MAX_STALENESS_MULTIPLIER * entity_ttl
                if age > max_age:
                    logger.warning(
                        f"dataframe_cache_{tier}_lkg_max_staleness_exceeded",
                        extra={
                            "project_gid": project_gid,
                            "entity_type": entity_type,
                            "age_seconds": age,
                            "max_age_seconds": round(max_age, 1),
                            "staleness_ratio": info.staleness_ratio,
                        },
                    )
                    if tier == "memory":
                        self.memory_tier.remove(cache_key)
                    return None

            # LKG: Serve expired entry with warning, trigger refresh
            self._stats[entity_type][f"{tier}_hits"] += 1
            self._stats[entity_type]["lkg_serves"] += 1
            logger.warning(
                f"dataframe_cache_{tier}_lkg_serve",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type,
                    "row_count": entry.row_count,
                    "age_seconds": age,
                    "freshness": "expired_servable",
                },
            )
            self._trigger_swr_refresh(project_gid, entity_type, cache_key)
            return entry

        # SCHEMA_MISMATCH or WATERMARK_STALE — hard reject, remove from memory
        if tier == "memory":
            self.memory_tier.remove(cache_key)
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
            created_at=datetime.now(UTC),
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
            [entity_type]
            if entity_type
            else ["unit", "business", "offer", "contact", "asset_edit"]
        )

        for et in entity_types:
            cache_key = self._build_key(project_gid, et)
            self.memory_tier.remove(cache_key)
            # Note: S3 entries not deleted, just superseded on next write
            self._ensure_stats(et)
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

        self._ensure_stats(entity_type)
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

    def get_freshness_info(
        self,
        project_gid: str,
        entity_type: str,
    ) -> FreshnessInfo | None:
        """Get freshness info from the most recent get_async() call.

        Returns None if no freshness info is available (cache miss or
        no prior get_async() call for this key).
        """
        cache_key = self._build_key(project_gid, entity_type)
        return self._last_freshness.get(cache_key)

    def _build_freshness_info(
        self,
        entry: CacheEntry,
        status: FreshnessStatus,
        cache_key: str,
    ) -> FreshnessInfo:
        """Build FreshnessInfo and store in side-channel.

        Args:
            entry: Cache entry to compute freshness for.
            status: Freshness status (from enum).
            cache_key: Cache key for side-channel storage.

        Returns:
            FreshnessInfo with computed age and staleness metrics.
        """
        from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL

        entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
        age = (datetime.now(UTC) - entry.created_at).total_seconds()
        info = FreshnessInfo(
            freshness=status.value,
            data_age_seconds=round(age, 1),
            staleness_ratio=round(age / entity_ttl, 2) if entity_ttl > 0 else 0.0,
        )
        self._last_freshness[cache_key] = info
        return info

    def set_build_callback(
        self,
        callback: Callable[[str, str], Awaitable[None]],
    ) -> None:
        """Register async callback for SWR background rebuilds.

        The callback is invoked as ``await callback(project_gid, entity_type)``
        and should build the DataFrame then call ``put_async`` on this cache.

        Args:
            callback: Async callable ``(project_gid, entity_type) -> None``.
        """
        self._build_callback = callback

    def _schema_is_valid(self, entry: CacheEntry) -> bool:
        """Check if entry schema version matches current registry.

        Returns True if schema is valid, False on mismatch or lookup failure.
        Used by circuit breaker LKG path where full freshness check is not needed.
        """
        expected_version = _get_schema_version_for_entity(entry.entity_type)
        if expected_version is None:
            return False
        return entry.schema_version == expected_version

    def _build_key(self, project_gid: str, entity_type: str) -> str:
        """Build cache key from project and entity type."""
        return f"{entity_type}:{project_gid}"

    def _check_freshness(
        self,
        entry: CacheEntry,
        current_watermark: datetime | None,
    ) -> FreshnessStatus:
        """Check entry freshness using entity-aware TTL with SWR grace.

        Returns a five-state result:
        - FRESH: Within entity TTL, serve immediately.
        - STALE_SERVABLE: Past entity TTL but within SWR grace window.
          Caller should serve stale data and trigger background refresh.
        - EXPIRED_SERVABLE: Beyond grace window but schema/watermark valid (LKG).
          Serve with warning, trigger refresh.
        - SCHEMA_MISMATCH: Schema version mismatch. Hard reject.
        - WATERMARK_STALE: Source has newer data. Hard reject.

        Schema version validation uses the SchemaRegistry to look up the
        expected version for the entry's entity type.
        """
        # Schema version check — always hard-reject on mismatch
        expected_version = _get_schema_version_for_entity(entry.entity_type)
        if expected_version is None:
            logger.warning(
                "cache_entry_invalid_no_schema",
                extra={
                    "entity_type": entry.entity_type,
                    "entry_version": entry.schema_version,
                },
            )
            return FreshnessStatus.SCHEMA_MISMATCH

        if entry.schema_version != expected_version:
            logger.debug(
                "cache_entry_version_mismatch",
                extra={
                    "entity_type": entry.entity_type,
                    "entry_version": entry.schema_version,
                    "expected_version": expected_version,
                },
            )
            return FreshnessStatus.SCHEMA_MISMATCH

        # Watermark check — hard-reject if source has newer data
        if current_watermark is not None:
            if not entry.is_fresh_by_watermark(current_watermark):
                return FreshnessStatus.WATERMARK_STALE

        # Entity-aware TTL with SWR grace window
        from autom8_asana.config import (
            DEFAULT_ENTITY_TTLS,
            DEFAULT_TTL,
            SWR_GRACE_MULTIPLIER,
        )

        entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
        grace_ttl = entity_ttl * SWR_GRACE_MULTIPLIER
        age = (datetime.now(UTC) - entry.created_at).total_seconds()

        if age <= entity_ttl:
            return FreshnessStatus.FRESH

        if age <= grace_ttl:
            return FreshnessStatus.STALE_SERVABLE

        # Beyond grace window but schema/watermark valid — serve as LKG
        return FreshnessStatus.EXPIRED_SERVABLE

    def _trigger_swr_refresh(
        self,
        project_gid: str,
        entity_type: str,
        cache_key: str,
    ) -> None:
        """Schedule non-blocking background refresh, deduped by coalescer.

        If a build is already in progress for this key, this is a no-op.
        Otherwise fires an asyncio task to rebuild and re-cache the entry.
        """
        if self.coalescer.is_building(cache_key):
            logger.debug(
                "swr_refresh_already_building",
                extra={"project_gid": project_gid, "entity_type": entity_type},
            )
            return

        self._ensure_stats(entity_type)
        self._stats[entity_type]["swr_refreshes_triggered"] += 1

        logger.info(
            "swr_refresh_triggered",
            extra={"project_gid": project_gid, "entity_type": entity_type},
        )

        asyncio.create_task(
            self._swr_refresh_async(project_gid, entity_type),
            name=f"swr:{entity_type}:{project_gid}",
        )

    async def _swr_refresh_async(
        self,
        project_gid: str,
        entity_type: str,
    ) -> None:
        """Background SWR refresh via coalescer-guarded build lock.

        Acquires the build lock, then delegates the actual DataFrame rebuild
        to the registered build callback.  If no callback is registered the
        refresh is skipped (the Lambda warmer will pick it up instead).
        """
        acquired = await self.acquire_build_lock_async(project_gid, entity_type)
        if not acquired:
            # Another task already building — coalesced
            return

        try:
            if self._build_callback is not None:
                await self._build_callback(project_gid, entity_type)
            else:
                logger.debug(
                    "swr_refresh_no_callback",
                    extra={"project_gid": project_gid, "entity_type": entity_type},
                )
        except Exception:
            logger.exception(
                "swr_refresh_failed",
                extra={"project_gid": project_gid, "entity_type": entity_type},
            )
            await self.release_build_lock_async(project_gid, entity_type, success=False)
        else:
            await self.release_build_lock_async(project_gid, entity_type, success=True)


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
