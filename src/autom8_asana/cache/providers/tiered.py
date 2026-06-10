"""Redis-backed cache provider (the historical "tiered" provider, S3 cold tier RETIRED).

Originally specced (ADR-0026) as a two-tier Redis-hot + S3-cold provider. The S3
cold tier was NEVER wired in production: ``factory.py`` maps the ``tiered``
provider to Redis ("S3 cold tier is Phase 3"), and the ``ASANA_CACHE_S3_ENABLED``
env flag that gated the cold path was set NOWHERE (not in Terraform, not in
``.env/defaults``, not in secretspec). It was the storage-topology census's
**mask #1 — phantom S3 cold tier**: a config field advertising a read tier wired
nowhere.

That phantom is now RETIRED. The ``s3_enabled`` flag, the ``ASANA_CACHE_S3_ENABLED``
env claim, the optional ``cold_tier`` argument, the promotion path, and every
``if self.s3_enabled`` cold-path gate are gone. ``TieredCacheProvider`` is now an
honest Redis-only passthrough. The durable per-task copies at
``asana-cache/tasks/`` are read via the EXPLICIT ``DurableTaskCacheReader`` (a
WRITE-durable / explicit-read namespace, NOT a cache provider tier) —
see ``StorageNamespaceContract.TASK_CACHE`` in ``storage_namespace.py``.

The class is retained (not deleted) because ``factory.py`` still selects it as the
``tiered`` provider value and it implements the full ``CacheProvider`` protocol by
delegating to the hot tier. Wiring a real S3 read tier in the future is a
separately-gated decision that must register its namespace in the storage registry
(it would otherwise fail ``tests/arch/test_namespace_contract.py`` t4).

Example:
    >>> from autom8_asana.cache.providers.tiered import TieredCacheProvider
    >>> from autom8_asana.cache.backends.redis import RedisCacheProvider
    >>>
    >>> tiered = TieredCacheProvider(hot_tier=RedisCacheProvider())
    >>> tiered.is_healthy()
    True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.models.metrics import CacheMetrics

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.cache.models.entry import CacheEntry, EntryType
    from autom8_asana.cache.models.freshness_unified import FreshnessIntent
    from autom8_asana.protocols.cache import CacheProvider, WarmResult

logger = get_logger(__name__)


class TieredCacheProvider:
    """Redis-only cache provider (S3 cold tier retired — see module docstring).

    Implements the ``CacheProvider`` protocol by delegating every operation to a
    single hot tier (Redis). There is no cold tier: the durable task cache is read
    explicitly via ``DurableTaskCacheReader``, not promoted through this provider.

    Thread Safety:
        Delegated to the underlying hot-tier provider (RedisCacheProvider is
        thread-safe).

    Example:
        >>> provider = TieredCacheProvider(hot_tier=redis_provider)
        >>> entry = provider.get_versioned("12345", EntryType.TASK)
    """

    def __init__(self, hot_tier: CacheProvider) -> None:
        """Initialize the provider over a single hot tier.

        Args:
            hot_tier: Redis cache provider for all operations.
        """
        self._hot = hot_tier
        self._metrics = CacheMetrics()

    # === Simple key-value operations ===

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a value from the hot tier (simple key-value)."""
        return self._hot.get(key)

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store a value in the hot tier (simple key-value)."""
        self._hot.set(key, value, ttl)

    def delete(self, key: str) -> None:
        """Remove a value from the hot tier."""
        self._hot.delete(key)

    # === Versioned operations ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: FreshnessIntent | None = None,
    ) -> CacheEntry | None:
        """Retrieve a versioned entry from the hot tier.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry for version resolution.
            freshness: STRICT validates version, EVENTUAL returns without check.

        Returns:
            CacheEntry if found in the hot tier, None otherwise.
        """
        return self._hot.get_versioned(key, entry_type, freshness)

    def set_versioned(self, key: str, entry: CacheEntry) -> None:
        """Store a versioned entry in the hot tier."""
        self._hot.set_versioned(key, entry)

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries from the hot tier.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries to retrieve.

        Returns:
            Dict mapping keys to CacheEntry or None if not found.
        """
        if not keys:
            return {}
        return self._hot.get_batch(keys, entry_type)

    def set_batch(self, entries: dict[str, CacheEntry]) -> None:
        """Store multiple entries in the hot tier."""
        if not entries:
            return
        self._hot.set_batch(entries)

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Pre-populate the hot tier for the specified GIDs."""
        return self._hot.warm(gids, entry_types)

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if the hot-tier cached version matches the current version."""
        return self._hot.check_freshness(key, entry_type, current_version)

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries in the hot tier."""
        self._hot.invalidate(key, entry_types)

    def is_healthy(self) -> bool:
        """Return True if the hot tier (Redis) is healthy."""
        return self._hot.is_healthy()

    def get_metrics(self) -> CacheMetrics:
        """Return this provider's own metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset this provider's own metrics."""
        self._metrics.reset()

    def clear_all_tasks(self) -> dict[str, int]:
        """Clear all task entries from the hot tier.

        Returns:
            Dict with counts: ``{"redis": N, "s3": 0}``. The ``"s3"`` count is
            retained for back-compat with consumers (e.g. ``cache_invalidate``)
            but is ALWAYS 0 now that the S3 cold tier is retired — there is no
            cold tier to clear. It honestly reflects "no S3 cold tier present".
        """
        result = {"redis": 0, "s3": 0}
        from autom8_asana.core.errors import CACHE_TRANSIENT_ERRORS

        try:
            result["redis"] = self._hot.clear_all_tasks()
        except CACHE_TRANSIENT_ERRORS as e:
            logger.warning(
                "redis_clear_all_tasks_failed",
                extra={"error": str(e)},
            )

        logger.info(
            "tiered_clear_all_tasks_complete",
            extra={"redis_deleted": result["redis"], "s3_deleted": result["s3"]},
        )
        return result

    def get_hot_metrics(self) -> CacheMetrics:
        """Return the hot tier (Redis) metrics."""
        return self._hot.get_metrics()
