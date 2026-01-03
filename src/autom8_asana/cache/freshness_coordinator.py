"""Freshness coordinator for batch staleness checks.

Per TDD-UNIFIED-CACHE-001: Replaces separate LightweightChecker +
StalenessCheckCoordinator with a unified approach that leverages
hierarchy relationships and Asana Batch API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from autom8y_log import get_logger

from autom8_asana.batch.models import BatchRequest

if TYPE_CHECKING:
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.cache.entry import CacheEntry

logger = get_logger(__name__)

# Asana batch API limit per request
ASANA_BATCH_LIMIT = 10


class FreshnessMode(Enum):
    """Freshness validation modes.

    Per TDD-UNIFIED-CACHE-001 Section 6.3:
    - STRICT: Always validate against API
    - EVENTUAL: TTL-based with lazy validation
    - IMMEDIATE: Return cached without validation
    """

    STRICT = "strict"
    EVENTUAL = "eventual"
    IMMEDIATE = "immediate"


@dataclass(frozen=True)
class FreshnessResult:
    """Result of freshness check.

    Attributes:
        gid: Task GID that was checked.
        is_fresh: Whether the cached data is fresh.
        cached_version: The cached modified_at timestamp.
        current_version: The current modified_at from API (if checked).
        action: Recommended action for the caller.
    """

    gid: str
    is_fresh: bool
    cached_version: datetime | None
    current_version: datetime | None
    action: Literal["use_cache", "fetch", "extend_ttl"]


@dataclass
class FreshnessCoordinator:
    """Coordinates batch freshness checks.

    Per TDD-UNIFIED-CACHE-001: Replaces separate LightweightChecker +
    StalenessCheckCoordinator with a unified approach.

    Uses Asana Batch API to check modified_at for multiple tasks
    in a single request (chunked by 10 per Asana limit).

    Attributes:
        batch_client: BatchClient for executing batch API requests.
        coalesce_window_ms: Window for request coalescing (milliseconds).
        max_batch_size: Maximum entries per batch check.

    Example:
        >>> coordinator = FreshnessCoordinator(
        ...     batch_client=batch_client,
        ...     coalesce_window_ms=50,
        ...     max_batch_size=100,
        ... )
        >>> results = await coordinator.check_batch_async(entries)
        >>> for result in results:
        ...     if result.action == "use_cache":
        ...         # Use cached data
        ...     elif result.action == "fetch":
        ...         # Fetch fresh data
    """

    batch_client: "BatchClient | None"
    coalesce_window_ms: int = 50
    max_batch_size: int = 100

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize statistics."""
        self._stats = {
            "total_checks": 0,
            "api_calls": 0,
            "fresh_count": 0,
            "stale_count": 0,
            "error_count": 0,
            "immediate_returns": 0,
        }

    async def check_batch_async(
        self,
        entries: list["CacheEntry"],
        mode: FreshnessMode = FreshnessMode.EVENTUAL,
    ) -> list[FreshnessResult]:
        """Check freshness for batch of cache entries.

        Per TDD-UNIFIED-CACHE-001 Section 5.3:

        For IMMEDIATE mode:
        - Returns is_fresh=True without API call

        For EVENTUAL mode:
        - If TTL not expired: return is_fresh=True without API call
        - If TTL expired: batch fetch modified_at via Asana Batch API
        - Compare versions and return results

        For STRICT mode:
        - Always batch fetch modified_at
        - Compare versions

        Args:
            entries: Cache entries to check.
            mode: Freshness validation mode.

        Returns:
            List of FreshnessResult with recommended actions.
        """
        if not entries:
            return []

        self._stats["total_checks"] += len(entries)

        # IMMEDIATE mode: return immediately without API call
        if mode == FreshnessMode.IMMEDIATE:
            self._stats["immediate_returns"] += len(entries)
            return [
                FreshnessResult(
                    gid=entry.key,
                    is_fresh=True,
                    cached_version=entry.version,
                    current_version=None,
                    action="use_cache",
                )
                for entry in entries
            ]

        # For EVENTUAL mode, filter to only expired entries
        if mode == FreshnessMode.EVENTUAL:
            now = datetime.now(timezone.utc)
            expired_entries = [e for e in entries if e.is_expired(now)]
            non_expired_entries = [e for e in entries if not e.is_expired(now)]

            # Non-expired entries are fresh
            results = [
                FreshnessResult(
                    gid=entry.key,
                    is_fresh=True,
                    cached_version=entry.version,
                    current_version=None,
                    action="use_cache",
                )
                for entry in non_expired_entries
            ]
            self._stats["fresh_count"] += len(non_expired_entries)

            # Check expired entries via API
            if expired_entries:
                api_results = await self._check_via_api(expired_entries)
                results.extend(api_results)

            return results

        # STRICT mode: always check via API
        return await self._check_via_api(entries)

    async def _check_via_api(
        self,
        entries: list["CacheEntry"],
    ) -> list[FreshnessResult]:
        """Check freshness via Asana Batch API.

        Chunks requests by ASANA_BATCH_LIMIT (10) per Asana API limit.

        Args:
            entries: Cache entries to check.

        Returns:
            List of FreshnessResult for each entry.
        """
        if not entries or self.batch_client is None:
            # No batch client - treat all as needing fetch
            self._stats["error_count"] += len(entries)
            return [
                FreshnessResult(
                    gid=entry.key,
                    is_fresh=False,
                    cached_version=entry.version,
                    current_version=None,
                    action="fetch",
                )
                for entry in entries
            ]

        # Build GID to entry mapping
        gid_to_entry: dict[str, "CacheEntry"] = {e.key: e for e in entries}
        gids = list(gid_to_entry.keys())

        # Chunk and execute
        results: list[FreshnessResult] = []
        for chunk_gids in _chunk(gids, ASANA_BATCH_LIMIT):
            chunk_results = await self._check_chunk(chunk_gids, gid_to_entry)
            results.extend(chunk_results)
            self._stats["api_calls"] += 1

        return results

    async def _check_chunk(
        self,
        gids: list[str],
        gid_to_entry: dict[str, "CacheEntry"],
    ) -> list[FreshnessResult]:
        """Execute a single chunk of modified_at checks.

        Args:
            gids: GIDs to check in this chunk (max ASANA_BATCH_LIMIT).
            gid_to_entry: Mapping of GID to cache entry.

        Returns:
            List of FreshnessResult for each GID.
        """
        if self.batch_client is None:
            return []

        requests = self._build_batch_requests(gids)

        try:
            batch_results = await self.batch_client.execute_async(requests)
            modified_at_map = self._parse_batch_response(batch_results, gids)
        except Exception as e:
            # Batch failed - mark all as needing fetch
            logger.warning(
                "freshness_check_batch_failure",
                extra={
                    "cache_operation": "freshness_check",
                    "chunk_size": len(gids),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            self._stats["error_count"] += len(gids)
            return [
                FreshnessResult(
                    gid=gid,
                    is_fresh=False,
                    cached_version=gid_to_entry[gid].version,
                    current_version=None,
                    action="fetch",
                )
                for gid in gids
            ]

        # Build results by comparing versions
        results: list[FreshnessResult] = []
        for gid in gids:
            entry = gid_to_entry[gid]
            modified_at = modified_at_map.get(gid)

            if modified_at is None:
                # Error or deleted - need to fetch
                self._stats["error_count"] += 1
                results.append(
                    FreshnessResult(
                        gid=gid,
                        is_fresh=False,
                        cached_version=entry.version,
                        current_version=None,
                        action="fetch",
                    )
                )
            else:
                current_version = _parse_datetime(modified_at)
                is_fresh = entry.is_current(current_version)

                if is_fresh:
                    self._stats["fresh_count"] += 1
                    results.append(
                        FreshnessResult(
                            gid=gid,
                            is_fresh=True,
                            cached_version=entry.version,
                            current_version=current_version,
                            action="extend_ttl",
                        )
                    )
                else:
                    self._stats["stale_count"] += 1
                    results.append(
                        FreshnessResult(
                            gid=gid,
                            is_fresh=False,
                            cached_version=entry.version,
                            current_version=current_version,
                            action="fetch",
                        )
                    )

        return results

    def _build_batch_requests(self, gids: list[str]) -> list[BatchRequest]:
        """Build batch GET requests for modified_at.

        Per TDD-UNIFIED-CACHE-001: Uses GET /tasks/{gid}?opt_fields=modified_at.

        Args:
            gids: Task GIDs to check.

        Returns:
            List of BatchRequest objects.
        """
        return [
            BatchRequest(
                relative_path=f"/tasks/{gid}",
                method="GET",
                options={"opt_fields": "modified_at"},
            )
            for gid in gids
        ]

    def _parse_batch_response(
        self,
        results: list[Any],
        gids: list[str],
    ) -> dict[str, str | None]:
        """Parse batch results to modified_at mapping.

        Args:
            results: BatchResult objects from batch execution.
            gids: Original GIDs in request order.

        Returns:
            Dict mapping GID to modified_at string or None.
        """
        from autom8_asana.batch.models import BatchResult

        parsed: dict[str, str | None] = {}

        for i, result in enumerate(results):
            gid = gids[i] if i < len(gids) else None
            if gid is None:
                continue

            if isinstance(result, BatchResult):
                if result.success and result.data:
                    modified_at = result.data.get("modified_at")
                    if modified_at and isinstance(modified_at, str):
                        parsed[gid] = modified_at
                    else:
                        parsed[gid] = None
                else:
                    # Failed or deleted
                    if result.status_code == 404:
                        logger.debug(
                            "freshness_check_entity_deleted",
                            extra={
                                "cache_operation": "freshness_check",
                                "gid": gid,
                                "status_code": 404,
                            },
                        )
                    parsed[gid] = None
            else:
                parsed[gid] = None

        return parsed

    async def check_hierarchy_async(
        self,
        root_gid: str,
        root_entry: "CacheEntry | None" = None,
        mode: FreshnessMode = FreshnessMode.EVENTUAL,
    ) -> FreshnessResult:
        """Check freshness using root entity's modified_at.

        Per TDD-UNIFIED-CACHE-001: Optimized path for hierarchy-aware caching.
        If the root Business hasn't changed, all descendants are fresh.

        Args:
            root_gid: Root Business GID.
            root_entry: Optional cache entry for the root (if available).
            mode: Freshness validation mode.

        Returns:
            Single FreshnessResult for the entire hierarchy.
        """
        self._stats["total_checks"] += 1

        # IMMEDIATE mode: return fresh without checking
        if mode == FreshnessMode.IMMEDIATE:
            self._stats["immediate_returns"] += 1
            return FreshnessResult(
                gid=root_gid,
                is_fresh=True,
                cached_version=root_entry.version if root_entry else None,
                current_version=None,
                action="use_cache",
            )

        # For EVENTUAL mode with non-expired entry, return fresh
        if mode == FreshnessMode.EVENTUAL and root_entry is not None:
            if not root_entry.is_expired():
                self._stats["fresh_count"] += 1
                return FreshnessResult(
                    gid=root_gid,
                    is_fresh=True,
                    cached_version=root_entry.version,
                    current_version=None,
                    action="use_cache",
                )

        # Check via API
        if self.batch_client is None:
            self._stats["error_count"] += 1
            return FreshnessResult(
                gid=root_gid,
                is_fresh=False,
                cached_version=root_entry.version if root_entry else None,
                current_version=None,
                action="fetch",
            )

        try:
            requests = self._build_batch_requests([root_gid])
            batch_results = await self.batch_client.execute_async(requests)
            self._stats["api_calls"] += 1

            modified_at_map = self._parse_batch_response(batch_results, [root_gid])
            modified_at = modified_at_map.get(root_gid)

            if modified_at is None:
                self._stats["error_count"] += 1
                return FreshnessResult(
                    gid=root_gid,
                    is_fresh=False,
                    cached_version=root_entry.version if root_entry else None,
                    current_version=None,
                    action="fetch",
                )

            current_version = _parse_datetime(modified_at)

            if root_entry is not None and root_entry.is_current(current_version):
                self._stats["fresh_count"] += 1
                return FreshnessResult(
                    gid=root_gid,
                    is_fresh=True,
                    cached_version=root_entry.version,
                    current_version=current_version,
                    action="extend_ttl",
                )
            else:
                self._stats["stale_count"] += 1
                return FreshnessResult(
                    gid=root_gid,
                    is_fresh=False,
                    cached_version=root_entry.version if root_entry else None,
                    current_version=current_version,
                    action="fetch",
                )

        except Exception as e:
            logger.warning(
                "freshness_check_hierarchy_failure",
                extra={
                    "cache_operation": "freshness_check",
                    "root_gid": root_gid,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            self._stats["error_count"] += 1
            return FreshnessResult(
                gid=root_gid,
                is_fresh=False,
                cached_version=root_entry.version if root_entry else None,
                current_version=None,
                action="fetch",
            )

    def get_stats(self) -> dict[str, int]:
        """Get coordinator statistics.

        Returns:
            Dict with total_checks, api_calls, fresh_count, stale_count, error_count.
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset statistics to zero."""
        for key in self._stats:
            self._stats[key] = 0


def _chunk(items: list[str], size: int) -> list[list[str]]:
    """Split list into chunks of specified size.

    Args:
        items: List to chunk.
        size: Maximum chunk size.

    Returns:
        List of chunks.
    """
    if not items or size <= 0:
        return []
    return [items[i : i + size] for i in range(0, len(items), size)]


def _parse_datetime(value: str) -> datetime:
    """Parse ISO format datetime string.

    Args:
        value: ISO format datetime string.

    Returns:
        Parsed datetime with UTC timezone.
    """
    # Handle Z suffix
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
