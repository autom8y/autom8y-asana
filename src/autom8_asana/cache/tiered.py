"""Two-tier cache provider coordinating Redis (hot) and S3 (cold) tiers.

Implements the architecture defined in ADR-0026:
- Write-through: Writes go to both tiers for durability
- Cache-aside with promotion: Reads check hot first, promote from cold on miss
- Graceful degradation: S3 failures don't break Redis operations

Example:
    >>> from autom8_asana.cache.tiered import TieredCacheProvider, TieredConfig
    >>> from autom8_asana.cache.backends.redis import RedisCacheProvider
    >>> from autom8_asana.cache.backends.s3 import S3CacheProvider
    >>>
    >>> config = TieredConfig(s3_enabled=True)
    >>> tiered = TieredCacheProvider(
    ...     hot_tier=RedisCacheProvider(),
    ...     cold_tier=S3CacheProvider(),
    ...     config=config,
    ... )
    >>> tiered.is_healthy()
    True
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from autom8y_log import get_logger

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.metrics import CacheMetrics
from autom8_asana.protocols.cache import CacheProvider, WarmResult

logger = get_logger(__name__)


@dataclass
class TieredConfig:
    """Configuration for two-tier cache behavior.

    Attributes:
        s3_enabled: Feature flag to enable S3 cold tier.
            When False, TieredCacheProvider behaves as Redis-only.
            Environment variable: ASANA_CACHE_S3_ENABLED
        promotion_ttl: TTL in seconds when promoting entries from S3 to Redis.
            Default is 3600 (1 hour) per ADR-0026.
        write_through: Whether to write to both tiers on set operations.
            When True, writes go to both Redis and S3.
            When False, only Redis receives writes.
    """

    s3_enabled: bool = False
    promotion_ttl: int = 3600
    write_through: bool = True


class TieredCacheProvider:
    """Two-tier cache provider coordinating Redis and S3 backends.

    Implements the CacheProvider protocol by coordinating a hot tier (Redis)
    and optional cold tier (S3). When S3 is disabled via the feature flag,
    behaves exactly like the Redis provider alone.

    Read Strategy (cache-aside with promotion):
        1. Check hot tier (Redis) first
        2. On hit: return immediately (fast path)
        3. On miss: check cold tier (S3) if enabled
        4. On cold hit: promote to hot tier with promotion_ttl, return
        5. On cold miss: return None (caller fetches from API)

    Write Strategy (write-through):
        1. Write to hot tier (Redis) - always
        2. Write to cold tier (S3) if enabled - fire-and-forget

    Graceful Degradation:
        - S3 failures are logged but don't fail operations
        - Health check only requires hot tier to be healthy
        - Read/write operations succeed if Redis works

    Thread Safety:
        Thread safety is delegated to the underlying providers.
        Both RedisCacheProvider and S3CacheProvider are thread-safe.

    Example:
        >>> config = TieredConfig(s3_enabled=True)
        >>> provider = TieredCacheProvider(
        ...     hot_tier=redis_provider,
        ...     cold_tier=s3_provider,
        ...     config=config,
        ... )
        >>> entry = provider.get_versioned("12345", EntryType.TASK)
    """

    def __init__(
        self,
        hot_tier: CacheProvider,
        cold_tier: CacheProvider | None = None,
        config: TieredConfig | None = None,
    ) -> None:
        """Initialize tiered cache provider.

        Args:
            hot_tier: Redis cache provider for fast access.
            cold_tier: S3 cache provider for durability.
                Can be None if S3 is not configured.
            config: Tiered cache configuration.
                Defaults to TieredConfig() with S3 disabled.
        """
        self._hot = hot_tier
        self._cold = cold_tier
        self._config = config or TieredConfig()
        self._metrics = CacheMetrics()

    @property
    def s3_enabled(self) -> bool:
        """Check if S3 cold tier is enabled.

        Returns True only if both the feature flag is enabled AND
        a cold tier provider is configured.
        """
        return self._config.s3_enabled and self._cold is not None

    # === Original methods (backward compatible) ===

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve value from cache (simple key-value).

        Checks hot tier only for simple get operations.
        Versioned operations should use get_versioned for
        full two-tier support.

        Args:
            key: Cache key.

        Returns:
            Cached dict if found, None if miss.
        """
        return self._hot.get(key)

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store value in cache (simple key-value).

        Writes to hot tier only for simple set operations.
        Versioned operations should use set_versioned for
        write-through support.

        Args:
            key: Cache key.
            value: Dict to cache.
            ttl: Time-to-live in seconds.
        """
        self._hot.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """Remove value from cache.

        Deletes from both tiers to maintain consistency.

        Args:
            key: Cache key to delete.
        """
        self._hot.delete(key)
        if self.s3_enabled and self._cold is not None:
            try:
                self._cold.delete(key)
            except Exception as e:
                logger.warning(
                    "s3_delete_failed",
                    extra={"key": key, "error": str(e)},
                )

    # === Versioned methods with two-tier support ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: Freshness | None = None,
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry with two-tier lookup.

        Implements cache-aside with promotion:
        1. Check hot tier (Redis)
        2. On hit: return entry (fast path)
        3. On miss + S3 enabled: check cold tier
        4. On cold hit: promote to hot tier with promotion_ttl
        5. On miss: return None

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry for version resolution.
            freshness: STRICT validates version, EVENTUAL returns without check.

        Returns:
            CacheEntry if found in either tier, None otherwise.
        """
        if freshness is None:
            freshness = Freshness.EVENTUAL

        # Check hot tier first
        entry = self._hot.get_versioned(key, entry_type, freshness)
        if entry is not None:
            return entry

        # S3 disabled - return miss
        if not self.s3_enabled or self._cold is None:
            return None

        # Check cold tier
        try:
            entry = self._cold.get_versioned(key, entry_type, freshness)
        except Exception as e:
            logger.warning(
                "s3_get_versioned_failed",
                extra={"key": key, "entry_type": entry_type.value, "error": str(e)},
            )
            return None

        if entry is None:
            return None

        # Promote to hot tier with configured promotion TTL
        promoted_entry = self._promote_entry(entry)
        try:
            self._hot.set_versioned(key, promoted_entry)
            self._metrics.record_promotion(
                key=key,
                entry_type=entry_type.value,
            )
        except Exception as e:
            # Promotion failure shouldn't fail the read
            logger.warning(
                "redis_promotion_failed",
                extra={"key": key, "error": str(e)},
            )

        return entry

    def set_versioned(
        self,
        key: str,
        entry: CacheEntry,
    ) -> None:
        """Store versioned cache entry with write-through.

        Always writes to hot tier. When S3 is enabled and
        write_through is True, also writes to cold tier.

        S3 write failures are logged but don't fail the operation.

        Args:
            key: Cache key.
            entry: CacheEntry with data and metadata.
        """
        # Always write to hot tier
        self._hot.set_versioned(key, entry)

        # Write-through to cold tier if enabled
        if self.s3_enabled and self._config.write_through and self._cold is not None:
            try:
                self._cold.set_versioned(key, entry)
            except Exception as e:
                # S3 write failure - log but don't fail operation
                logger.warning(
                    "s3_write_through_failed",
                    extra={"key": key, "entry_type": entry.entry_type.value, "error": str(e)},
                )

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries with two-tier lookup.

        First checks hot tier for all keys. For keys with misses,
        checks cold tier if S3 is enabled and promotes hits.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries to retrieve.

        Returns:
            Dict mapping keys to CacheEntry or None if not found.
        """
        if not keys:
            return {}

        # Check hot tier first
        result = self._hot.get_batch(keys, entry_type)

        # If S3 disabled, return hot tier results
        if not self.s3_enabled or self._cold is None:
            return result

        # Find keys that missed in hot tier
        missed_keys = [k for k, v in result.items() if v is None]
        if not missed_keys:
            return result

        # Check cold tier for missed keys
        try:
            cold_results = self._cold.get_batch(missed_keys, entry_type)
        except Exception as e:
            logger.warning(
                "s3_get_batch_failed",
                extra={"key_count": len(missed_keys), "error": str(e)},
            )
            return result

        # Promote cold hits to hot tier
        promotions: dict[str, CacheEntry] = {}
        for key, entry in cold_results.items():
            if entry is not None:
                result[key] = entry
                promoted = self._promote_entry(entry)
                promotions[key] = promoted

        # Batch promote to hot tier
        if promotions:
            try:
                self._hot.set_batch(promotions)
                for key in promotions:
                    self._metrics.record_promotion(
                        key=key,
                        entry_type=entry_type.value,
                    )
            except Exception as e:
                logger.warning(
                    "batch_promotion_to_redis_failed",
                    extra={"error": str(e)},
                )

        return result

    def set_batch(
        self,
        entries: dict[str, CacheEntry],
    ) -> None:
        """Store multiple entries with write-through.

        Always writes to hot tier. When S3 is enabled and
        write_through is True, also writes to cold tier.

        Args:
            entries: Dict mapping keys to CacheEntry objects.
        """
        if not entries:
            return

        # Always write to hot tier
        self._hot.set_batch(entries)

        # Write-through to cold tier if enabled
        if self.s3_enabled and self._config.write_through and self._cold is not None:
            try:
                self._cold.set_batch(entries)
            except Exception as e:
                logger.warning(
                    "s3_batch_write_through_failed",
                    extra={"error": str(e)},
                )

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Pre-populate cache for specified GIDs.

        Delegates to hot tier warming. Cold tier warming is not
        supported as S3 is for durability, not warming.

        Args:
            gids: List of task GIDs to warm.
            entry_types: Entry types to fetch and cache.

        Returns:
            WarmResult with success/failure counts.
        """
        return self._hot.warm(gids, entry_types)

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if cached version matches current version.

        Checks hot tier only. If entry is in cold tier but not
        hot tier, returns False (stale) to trigger refresh.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            current_version: Known current modified_at timestamp.

        Returns:
            True if hot tier cache is fresh, False if stale or missing.
        """
        return self._hot.check_freshness(key, entry_type, current_version)

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries from both tiers.

        Always invalidates from hot tier. When S3 is enabled,
        also invalidates from cold tier.

        Args:
            key: Cache key (task GID).
            entry_types: Specific types to invalidate.
                If None, invalidates all types for the key.
        """
        self._hot.invalidate(key, entry_types)

        if self.s3_enabled and self._cold is not None:
            try:
                self._cold.invalidate(key, entry_types)
            except Exception as e:
                logger.warning(
                    "s3_invalidate_failed",
                    extra={"key": key, "error": str(e)},
                )

    def is_healthy(self) -> bool:
        """Check if cache is operational.

        Returns True if hot tier (Redis) is healthy.
        S3 health is not required - it's for durability, not availability.

        Returns:
            True if Redis is healthy and responding.
        """
        return self._hot.is_healthy()

    def get_metrics(self) -> CacheMetrics:
        """Get tiered cache metrics.

        Returns the tiered provider's own metrics which track
        promotions. For tier-specific metrics, access the
        individual providers.

        Returns:
            CacheMetrics instance with promotion statistics.
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset tiered cache metrics.

        Resets the tiered provider's metrics. Does not reset
        individual tier metrics - call those separately if needed.
        """
        self._metrics.reset()

    def clear_all_tasks(self) -> dict[str, int]:
        """Clear all task entries from both tiers.

        Clears task cache from both Redis (hot) and S3 (cold) tiers.
        Used for cache invalidation when cached data becomes stale
        or corrupted (e.g., missing required fields like memberships).

        Returns:
            Dict with counts: {"redis": N, "s3": M}
        """
        result = {"redis": 0, "s3": 0}

        # Clear hot tier (Redis)
        try:
            result["redis"] = self._hot.clear_all_tasks()
        except Exception as e:
            logger.warning(
                "redis_clear_all_tasks_failed",
                extra={"error": str(e)},
            )

        # Clear cold tier (S3) if enabled
        if self.s3_enabled and self._cold is not None:
            try:
                result["s3"] = self._cold.clear_all_tasks()
            except Exception as e:
                logger.warning(
                    "s3_clear_all_tasks_failed",
                    extra={"error": str(e)},
                )

        logger.info(
            "tiered_clear_all_tasks_complete",
            extra={
                "redis_deleted": result["redis"],
                "s3_deleted": result["s3"],
            },
        )

        return result

    def get_hot_metrics(self) -> CacheMetrics:
        """Get hot tier (Redis) metrics.

        Returns:
            CacheMetrics from the Redis provider.
        """
        return self._hot.get_metrics()

    def get_cold_metrics(self) -> CacheMetrics | None:
        """Get cold tier (S3) metrics if available.

        Returns:
            CacheMetrics from S3 provider, or None if S3 disabled.
        """
        if self._cold is not None:
            return self._cold.get_metrics()
        return None

    # === Helper methods ===

    def _promote_entry(self, entry: CacheEntry) -> CacheEntry:
        """Create a new entry with promotion TTL for hot tier.

        Uses dataclasses.replace to create a new immutable CacheEntry
        with the configured promotion TTL.

        Args:
            entry: Original entry from cold tier.

        Returns:
            New CacheEntry with promotion_ttl and updated cached_at.
        """
        return replace(
            entry,
            ttl=self._config.promotion_ttl,
            cached_at=datetime.now(UTC),
        )
