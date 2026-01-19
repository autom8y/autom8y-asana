"""Staleness check coordinator for lightweight staleness detection.

Per TDD-CACHE-LIGHTWEIGHT-STALENESS: Orchestrates the staleness check flow,
coordinating between coalescer, checker, and cache provider.

Per ADR-0133: Implements progressive TTL extension with immutable entry replacement.
Per ADR-0134: Integrates with BaseClient as optional coordinator pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.protocols.cache import CacheProvider

from autom8_asana.cache.coalescer import RequestCoalescer
from autom8_asana.cache.entry import CacheEntry
from autom8_asana.cache.lightweight_checker import LightweightChecker
from autom8_asana.cache.staleness_settings import StalenessCheckSettings

logger = get_logger(__name__)


@dataclass
class StalenessCheckCoordinator:
    """Coordinates lightweight staleness checks with progressive TTL extension.

    Per ADR-0134: This coordinator sits between cache lookup and API fetch,
    providing transparent staleness checking for expired entries.

    Flow:
    1. Receives expired cache entry from BaseClient
    2. Queues entry for batch modified_at check via coalescer
    3. If unchanged: extends TTL and returns updated entry
    4. If changed: returns None (caller performs full fetch)
    5. If error: returns None with graceful degradation

    Attributes:
        cache_provider: Cache provider for storing extended entries.
        batch_client: BatchClient for executing batch API requests.
        settings: Configuration for staleness checking behavior.

    Example:
        >>> coordinator = StalenessCheckCoordinator(
        ...     cache_provider=cache,
        ...     batch_client=batch_client,
        ...     settings=StalenessCheckSettings(),
        ... )
        >>> # Entry is expired but may be unchanged
        >>> result = await coordinator.check_and_get_async(expired_entry)
        >>> if result is not None:
        ...     # Entry was unchanged, result has extended TTL
        ...     pass
        ... else:
        ...     # Entry was changed or error, caller should fetch fresh
        ...     pass
    """

    cache_provider: CacheProvider
    batch_client: BatchClient
    settings: StalenessCheckSettings = field(default_factory=StalenessCheckSettings)

    # Internal components (created in __post_init__)
    _coalescer: RequestCoalescer = field(init=False, repr=False)
    _checker: LightweightChecker = field(init=False, repr=False)

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize coalescer and checker components."""
        self._checker = LightweightChecker(
            batch_client=self.batch_client,
            chunk_size=10,  # Asana batch limit
        )
        self._coalescer = RequestCoalescer(
            window_ms=self.settings.coalesce_window_ms,
            max_batch=self.settings.max_batch_size,
            checker=self._checker,
        )
        self._stats = {
            "total_checks": 0,
            "unchanged_count": 0,
            "changed_count": 0,
            "error_count": 0,
            "api_calls_saved": 0,
        }

    async def check_and_get_async(
        self,
        entry: CacheEntry,
    ) -> CacheEntry | None:
        """Check staleness and return updated entry or None.

        Per FR-STALE-001 through FR-STALE-006:
        - Queues entry for batch modified_at check
        - Returns extended-TTL entry if unchanged
        - Returns None if changed (caller should full-fetch)
        - Returns None if error/deleted (caller handles)

        Args:
            entry: Expired cache entry to check.

        Returns:
            CacheEntry with extended TTL if unchanged, None otherwise.
        """
        if not self.settings.enabled:
            return None

        self._stats["total_checks"] += 1
        start_time = datetime.now(UTC)

        try:
            # Queue for batch check
            modified_at = await self._coalescer.request_check_async(entry)

            # Process result
            result = self._process_staleness_result(entry, modified_at)

            # Log result
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self._log_staleness_check(entry, result, modified_at, duration_ms)

            return result

        except Exception as exc:
            # Per FR-DEGRADE-006: Graceful degradation - never propagate exceptions
            self._stats["error_count"] += 1
            logger.warning(
                "staleness_check_exception",
                extra={
                    "cache_operation": "staleness_check",
                    "gid": entry.key,
                    "entry_type": entry.entry_type.value,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
            return None

    def _process_staleness_result(
        self,
        entry: CacheEntry,
        modified_at: str | None,
    ) -> CacheEntry | None:
        """Process staleness check result.

        Per FR-STALE-003/004/005:
        - UNCHANGED: modified_at matches version -> extend TTL
        - CHANGED: modified_at differs -> return None
        - ERROR/DELETED: modified_at is None -> invalidate and return None

        Args:
            entry: Original cache entry.
            modified_at: Retrieved modified_at string, or None if error/deleted.

        Returns:
            Extended entry if unchanged, None otherwise.
        """
        if modified_at is None:
            # CASE C: Error or deleted
            self._stats["error_count"] += 1
            # Invalidate cache for this entry
            try:
                self.cache_provider.invalidate(entry.key, [entry.entry_type])
            except Exception as exc:
                logger.debug(
                    "staleness_invalidate_failed",
                    extra={
                        "cache_operation": "staleness_check",
                        "gid": entry.key,
                        "error": str(exc),
                    },
                )
            return None

        # Compare versions
        if entry.is_current(modified_at):
            # CASE A: Unchanged - extend TTL
            self._stats["unchanged_count"] += 1
            self._stats["api_calls_saved"] += 1

            extended_entry = self._extend_ttl(entry)

            # Update cache with extended entry
            try:
                self.cache_provider.set_versioned(entry.key, extended_entry)
            except Exception as exc:
                logger.debug(
                    "staleness_cache_update_failed",
                    extra={
                        "cache_operation": "staleness_check",
                        "gid": entry.key,
                        "error": str(exc),
                    },
                )
                # Still return extended entry even if cache update fails
                # Caller can use it, just won't be cached

            return extended_entry
        else:
            # CASE B: Changed - return None for full fetch
            self._stats["changed_count"] += 1
            return None

    def _extend_ttl(self, entry: CacheEntry) -> CacheEntry:
        """Extend TTL using exponential doubling.

        Per ADR-0133: min(base * 2^count, max).
        Per FR-TTL-006: Immutable - creates new entry, doesn't mutate.

        Args:
            entry: Original cache entry.

        Returns:
            New CacheEntry with extended TTL and updated metadata.
        """
        current_count = entry.metadata.get("extension_count", 0)
        new_count = current_count + 1

        # Calculate new TTL using settings
        new_ttl = self.settings.calculate_extended_ttl(new_count)
        previous_ttl = entry.ttl or self.settings.base_ttl

        logger.debug(
            "ttl_extended",
            extra={
                "cache_operation": "staleness_check",
                "gid": entry.key,
                "previous_ttl": previous_ttl,
                "new_ttl": new_ttl,
                "extension_count": new_count,
                "at_ceiling": new_ttl == self.settings.max_ttl,
            },
        )

        # Create new entry with extended TTL (immutable replacement)
        return CacheEntry(
            key=entry.key,
            data=entry.data,
            entry_type=entry.entry_type,
            version=entry.version,  # Preserved: actual version unchanged
            cached_at=datetime.now(UTC),  # Reset: new expiration window
            ttl=new_ttl,
            project_gid=entry.project_gid,
            metadata={**entry.metadata, "extension_count": new_count},
        )

    def _log_staleness_check(
        self,
        entry: CacheEntry,
        result: CacheEntry | None,
        modified_at: str | None,
        duration_ms: float,
    ) -> None:
        """Log staleness check result.

        Per FR-OBS-001 through FR-OBS-005: Structured logging for all operations.

        Args:
            entry: Original cache entry.
            result: Result entry (None if changed/error).
            modified_at: Retrieved modified_at or None.
            duration_ms: Check duration in milliseconds.
        """
        if result is not None:
            staleness_result = "unchanged"
        elif modified_at is None:
            staleness_result = "error_or_deleted"
        else:
            staleness_result = "changed"

        logger.info(
            "staleness_check_result",
            extra={
                "cache_operation": "staleness_check",
                "gid": entry.key,
                "entry_type": entry.entry_type.value,
                "staleness_result": staleness_result,
                "previous_ttl": entry.ttl,
                "new_ttl": result.ttl if result else None,
                "extension_count": (
                    result.metadata.get("extension_count", 0) if result else None
                ),
                "check_duration_ms": round(duration_ms, 2),
            },
        )

    def get_extension_stats(self) -> dict[str, int]:
        """Return session statistics for observability.

        Per FR-OBS-006: Cumulative session metrics.

        Returns:
            Dict with total_checks, unchanged_count, changed_count,
            error_count, api_calls_saved.
        """
        return self._stats.copy()

    async def flush_pending(self) -> None:
        """Force flush any pending coalesced requests.

        Useful for cleanup or testing.
        """
        await self._coalescer.flush_pending()
