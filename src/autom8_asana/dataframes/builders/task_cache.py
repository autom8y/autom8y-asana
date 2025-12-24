"""Task-level cache coordinator for DataFrame fetch path.

Per TDD-CACHE-PERF-FETCH-PATH Phase 1: Provides Task-level cache
integration for the DataFrame building pipeline. Enables second fetch
latency of <1s (down from 11.56s) by caching Task objects.

This module provides:
- TaskCacheResult: Result of cache lookup/population operations
- TaskCacheCoordinator: Coordinates cache operations for Task objects

Design per ADR-0119:
- Uses existing CacheProvider.get_batch()/set_batch() for efficiency
- Cache key is task GID (consistent with TasksClient.get_async())
- Entry type is EntryType.TASK
- Graceful degradation: cache failures log warnings but never propagate
- TTL resolution mirrors TasksClient._resolve_entity_ttl() pattern
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from autom8_asana.cache.entry import CacheEntry, EntryType

if TYPE_CHECKING:
    from autom8_asana.models import Task
    from autom8_asana.protocols.cache import CacheProvider

logger = logging.getLogger(__name__)


@dataclass
class TaskCacheResult:
    """Result of task cache lookup/population operations.

    Per TDD-CACHE-PERF-FETCH-PATH: Captures cache hit/miss statistics
    and merged task lists for observability and downstream processing.

    Attributes:
        cached_tasks: Tasks retrieved from cache.
        fetched_tasks: Tasks fetched from API (cache misses).
        cache_hits: Count of cache hits.
        cache_misses: Count of cache misses.
        all_tasks: Merged list preserving original order.

    Example:
        >>> result = coordinator.merge_results(gids, cached, fetched)
        >>> print(f"Hit rate: {result.hit_rate:.1%}")
    """

    cached_tasks: list["Task"] = field(default_factory=list)
    fetched_tasks: list["Task"] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    all_tasks: list["Task"] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate as float between 0.0 and 1.0, or 0.0 if no lookups.
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def total_tasks(self) -> int:
        """Total number of tasks (cached + fetched)."""
        return len(self.all_tasks)


class TaskCacheCoordinator:
    """Coordinates Task-level cache operations for DataFrame building.

    Per TDD-CACHE-PERF-FETCH-PATH and ADR-0119: Encapsulates cache logic
    for the DataFrame fetch path, using existing cache infrastructure.

    The coordinator handles:
    - Batch cache lookup before API fetch (FR-LOOKUP)
    - Batch cache population after API fetch (FR-POPULATE)
    - Merging cached and fetched tasks preserving order (FR-PARTIAL)
    - Graceful degradation on cache failures (FR-DEGRADE)

    Attributes:
        cache_provider: The underlying cache provider (may be None).
        default_ttl: Default TTL for cached entries (300s).

    Example:
        >>> coordinator = TaskCacheCoordinator(cache_provider)
        >>> cached = await coordinator.lookup_tasks_async(task_gids)
        >>> # Fetch missing from API...
        >>> await coordinator.populate_tasks_async(fetched_tasks)
        >>> result = coordinator.merge_results(gids, cached, fetched)
    """

    # TTLs imported from canonical source in config.py
    # DO NOT define TTL values here - use the canonical constants

    def __init__(
        self,
        cache_provider: "CacheProvider | None",
        default_ttl: int = 300,
    ) -> None:
        """Initialize TaskCacheCoordinator.

        Args:
            cache_provider: Cache provider for storage. None disables caching.
            default_ttl: Default TTL in seconds for cached entries.
        """
        self._cache = cache_provider
        self._default_ttl = default_ttl

    @property
    def cache_provider(self) -> "CacheProvider | None":
        """Get the underlying cache provider."""
        return self._cache

    async def lookup_tasks_async(
        self,
        task_gids: list[str],
    ) -> dict[str, "Task | None"]:
        """Batch lookup tasks from cache.

        Per FR-LOOKUP-001/002: Uses CacheProvider.get_batch() for efficiency.
        Per FR-LOOKUP-004: Uses EntryType.TASK for consistency.
        Per FR-DEGRADE-001: Graceful degradation on cache failures.

        Args:
            task_gids: List of task GIDs to look up.

        Returns:
            Dict mapping task_gid to Task if found, None if miss.
            On cache failure, returns empty dict (all misses).
        """
        if self._cache is None:
            logger.debug(
                "task_cache_lookup_skipped",
                extra={"reason": "no_cache_provider", "task_count": len(task_gids)},
            )
            return {gid: None for gid in task_gids}

        if not task_gids:
            return {}

        try:
            logger.debug(
                "task_cache_lookup_started",
                extra={"task_count": len(task_gids)},
            )

            # Use batch lookup for efficiency
            entries = self._cache.get_batch(task_gids, EntryType.TASK)

            # Convert cache entries to Task objects
            result: dict[str, "Task | None"] = {}
            hits = 0
            misses = 0

            for gid in task_gids:
                entry = entries.get(gid)
                if entry is not None and not entry.is_expired():
                    # Cache hit - convert to Task model
                    task = self._entry_to_task(entry)
                    result[gid] = task
                    hits += 1
                else:
                    result[gid] = None
                    misses += 1

            logger.debug(
                "task_cache_lookup_completed",
                extra={
                    "hits": hits,
                    "misses": misses,
                    "hit_rate": hits / len(task_gids) if task_gids else 0.0,
                },
            )

            return result

        except Exception as exc:
            # FR-DEGRADE-001: Log and continue without cache
            logger.warning(
                "task_cache_lookup_failed",
                extra={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "task_count": len(task_gids),
                },
            )
            return {gid: None for gid in task_gids}

    async def populate_tasks_async(
        self,
        tasks: list["Task"],
        ttl_resolver: Callable[["Task"], int] | None = None,
    ) -> int:
        """Batch populate cache with fetched tasks.

        Per FR-POPULATE-001/002: Uses CacheProvider.set_batch() for efficiency.
        Per FR-POPULATE-003: Uses task.modified_at as version.
        Per FR-POPULATE-004: Uses entity-type based TTL.
        Per FR-DEGRADE-002: Graceful degradation on cache failures.

        Args:
            tasks: List of Task objects to cache.
            ttl_resolver: Optional function to resolve TTL per task.
                If None, uses entity-type based TTL resolution.

        Returns:
            Count of tasks successfully cached.
            Returns 0 on cache failure.
        """
        if self._cache is None:
            logger.debug(
                "task_cache_population_skipped",
                extra={"reason": "no_cache_provider", "task_count": len(tasks)},
            )
            return 0

        if not tasks:
            return 0

        try:
            logger.debug(
                "task_cache_population_started",
                extra={"task_count": len(tasks)},
            )

            entries: dict[str, CacheEntry] = {}

            for task in tasks:
                if task.gid is None:
                    continue

                # Build cache entry
                data = self._task_to_data(task)
                version = self._parse_modified_at(task.modified_at)
                ttl = (
                    ttl_resolver(task)
                    if ttl_resolver
                    else self._resolve_entity_ttl(data)
                )

                entry = CacheEntry(
                    key=task.gid,
                    data=data,
                    entry_type=EntryType.TASK,
                    version=version,
                    cached_at=datetime.now(timezone.utc),
                    ttl=ttl,
                )
                entries[task.gid] = entry

            # Batch write
            self._cache.set_batch(entries)

            logger.debug(
                "task_cache_population_completed",
                extra={"populated_count": len(entries)},
            )

            return len(entries)

        except Exception as exc:
            # FR-DEGRADE-002: Log and continue
            logger.warning(
                "task_cache_population_failed",
                extra={
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "task_count": len(tasks),
                },
            )
            return 0

    def merge_results(
        self,
        task_gids_ordered: list[str],
        cached: dict[str, "Task"],
        fetched: list["Task"],
    ) -> TaskCacheResult:
        """Merge cached and fetched tasks preserving original order.

        Per FR-PARTIAL-002/003: Combines cached and fetched tasks,
        preserving the order defined by task_gids_ordered.

        Args:
            task_gids_ordered: List of task GIDs in desired order.
            cached: Dict mapping gid to Task from cache hits.
            fetched: List of Task objects fetched from API.

        Returns:
            TaskCacheResult with merged list and statistics.
        """
        # Build lookup for fetched tasks
        fetched_by_gid: dict[str, "Task"] = {
            t.gid: t for t in fetched if t.gid is not None
        }

        # Merge in order
        all_tasks: list["Task"] = []
        cached_tasks: list["Task"] = []
        fetched_tasks_list: list["Task"] = []

        for gid in task_gids_ordered:
            if gid in cached:
                task = cached[gid]
                all_tasks.append(task)
                cached_tasks.append(task)
            elif gid in fetched_by_gid:
                task = fetched_by_gid[gid]
                all_tasks.append(task)
                fetched_tasks_list.append(task)
            # Tasks not in either are skipped (removed from section)

        return TaskCacheResult(
            cached_tasks=cached_tasks,
            fetched_tasks=fetched_tasks_list,
            cache_hits=len(cached_tasks),
            cache_misses=len(fetched_tasks_list),
            all_tasks=all_tasks,
        )

    def _entry_to_task(self, entry: CacheEntry) -> "Task":
        """Convert CacheEntry to Task model.

        Args:
            entry: Cache entry with task data.

        Returns:
            Task model instance.
        """
        from autom8_asana.models import Task

        return Task.model_validate(entry.data)

    def _task_to_data(self, task: "Task") -> dict[str, Any]:
        """Convert Task model to cacheable dict.

        Args:
            task: Task model instance.

        Returns:
            Dict representation suitable for caching.
        """
        # Use model_dump with exclude_none to match API response format
        return task.model_dump(exclude_none=True)

    def _parse_modified_at(self, value: str | None) -> datetime:
        """Parse modified_at to datetime.

        Args:
            value: ISO format string or None.

        Returns:
            Timezone-aware datetime (UTC). Now if value is None.
        """
        if value is None:
            return datetime.now(timezone.utc)

        # Handle ISO format with Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _resolve_entity_ttl(self, data: dict[str, Any]) -> int:
        """Resolve TTL based on entity type detection.

        Uses canonical DEFAULT_ENTITY_TTLS from config.py for consistency.

        Args:
            data: Task data dict.

        Returns:
            TTL in seconds.
        """
        from autom8_asana.config import DEFAULT_ENTITY_TTLS

        entity_type = self._detect_entity_type(data)

        if entity_type and entity_type.lower() in DEFAULT_ENTITY_TTLS:
            return DEFAULT_ENTITY_TTLS[entity_type.lower()]

        return self._default_ttl

    def _detect_entity_type(self, data: dict[str, Any]) -> str | None:
        """Detect entity type from task data.

        Uses existing detection infrastructure if available.

        Args:
            data: Task data dict.

        Returns:
            Entity type name or None if not detectable.
        """
        try:
            from autom8_asana.models import Task as TaskModel
            from autom8_asana.models.business.detection import detect_entity_type

            # Create temporary Task to use detection
            temp_task = TaskModel.model_validate(data)
            result = detect_entity_type(temp_task)
            if result and result.entity_type:
                return result.entity_type.value
            return None
        except ImportError:
            # Detection module not available
            return None
        except Exception:
            # Detection failed, use default
            return None
