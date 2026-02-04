"""Cache invalidation service for REST mutation endpoints.

Per TDD-CACHE-INVALIDATION-001: MutationInvalidator is a sibling service
to CacheInvalidator (ADR-001). Both call the same underlying primitives
(CacheProvider.invalidate, invalidate_task_dataframes) but have different
interfaces suited to their callers.

MutationInvalidator accepts MutationEvents from REST route handlers and
triggers invalidation across all affected cache tiers using a fire-and-forget
pattern (ADR-003).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.cache.models.entry import EntryType
from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
)
from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

if TYPE_CHECKING:
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)

# Entry types invalidated for task mutations
_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]


@dataclass
class SoftInvalidationConfig:
    """Controls when MutationInvalidator uses soft vs. hard invalidation.

    Per TDD-CROSS-TIER-FRESHNESS-001 / ADR-003: Soft invalidation marks
    entries stale without evicting. Disabled by default to preserve
    existing hard-eviction behavior.

    Attributes:
        enabled: Master switch for soft invalidation.
        soft_entity_kinds: Entity kinds that use soft invalidation.
            Defaults to empty (all use hard invalidation).
        soft_mutation_types: Mutation types that use soft invalidation.
            Defaults to UPDATE only (creates/deletes should hard-evict).
    """

    enabled: bool = False
    soft_entity_kinds: frozenset[str] = frozenset()
    soft_mutation_types: frozenset[str] = frozenset({"update"})


class MutationInvalidator:
    """Cache invalidation service for REST mutation endpoints.

    Stateless service that accepts MutationEvents and triggers
    invalidation across the appropriate cache tiers. Designed
    for fire-and-forget usage from route handlers.

    Thread Safety: Stateless after init. Safe for concurrent use.

    Attributes:
        _cache: TieredCacheProvider for entity-level invalidation.
        _dataframe_cache: DataFrameCache for project-level DataFrame invalidation.
    """

    def __init__(
        self,
        cache_provider: CacheProvider,
        dataframe_cache: DataFrameCache | None = None,
        soft_config: SoftInvalidationConfig | None = None,
    ) -> None:
        """Initialize with cache backends.

        Args:
            cache_provider: Cache implementation for entity-level invalidation.
            dataframe_cache: Optional DataFrameCache for project-level DataFrame
                invalidation. If None, project DataFrame invalidation is skipped.
            soft_config: Configuration for soft invalidation behavior.
                Defaults to SoftInvalidationConfig() (disabled).
        """
        self._cache = cache_provider
        self._dataframe_cache = dataframe_cache
        self._soft_config = soft_config or SoftInvalidationConfig()

    async def invalidate_async(self, event: MutationEvent) -> None:
        """Invalidate all cache tiers affected by a mutation.

        This is the primary entry point. Route handlers call this
        via fire_and_forget() to avoid blocking the response.

        Args:
            event: Description of the mutation that occurred.
        """
        try:
            if event.entity_kind == EntityKind.TASK:
                await self._handle_task_mutation(event)
            elif event.entity_kind == EntityKind.SECTION:
                await self._handle_section_mutation(event)
            else:
                logger.warning(
                    "mutation_invalidator_unsupported_kind",
                    extra={"entity_kind": event.entity_kind.value},
                )
        except Exception as exc:  # BROAD-CATCH: isolation -- background task boundary, must never propagate
            logger.error(
                "mutation_invalidation_failed",
                extra={
                    "entity_kind": event.entity_kind.value,
                    "entity_gid": event.entity_gid,
                    "mutation_type": event.mutation_type.value,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

    def fire_and_forget(self, event: MutationEvent) -> None:
        """Schedule invalidation as a background task.

        Per ADR-003: Uses asyncio.create_task for zero-latency dispatch.
        Does not block. Errors are logged, never propagated.
        Safe to call from within a route handler.

        Args:
            event: Description of the mutation that occurred.
        """
        task = asyncio.create_task(
            self.invalidate_async(event),
            name=f"invalidate:{event.entity_kind.value}:{event.entity_gid}",
        )
        task.add_done_callback(_log_task_exception)

    # --- Private: Task Mutations ---

    async def _handle_task_mutation(self, event: MutationEvent) -> None:
        """Handle task-level cache invalidation.

        Steps:
        1. Invalidate entity cache (TASK, SUBTASKS, DETECTION)
        2. Invalidate per-task DataFrame entries (if project context known)
        3. For structural changes: invalidate DataFrameCache for affected projects
        """
        gid = event.entity_gid

        # Step 1: Entity cache invalidation
        self._invalidate_entity_entries(gid, event)

        # Step 2: Per-task DataFrame invalidation (task_gid:project_gid keys)
        if event.project_gids:
            self._invalidate_per_task_dataframes(gid, event.project_gids)

        # Step 3: Project-level DataFrameCache invalidation
        # For creates, moves, and membership changes, the project's full
        # DataFrame is affected (row count changes, not just row content)
        if event.mutation_type in (
            MutationType.CREATE,
            MutationType.DELETE,
            MutationType.MOVE,
            MutationType.ADD_MEMBER,
            MutationType.REMOVE_MEMBER,
        ):
            await self._invalidate_project_dataframes(event.project_gids)

        logger.debug(
            "mutation_invalidation_complete",
            extra={
                "entity_gid": gid,
                "mutation_type": event.mutation_type.value,
                "project_count": len(event.project_gids),
            },
        )

    # --- Private: Section Mutations ---

    async def _handle_section_mutation(self, event: MutationEvent) -> None:
        """Handle section-level cache invalidation.

        Section mutations affect:
        1. SECTION entry type in entity cache
        2. DataFrameCache for the section's parent project
        3. For add-task-to-section: also invalidate the task's entity cache
        """
        gid = event.entity_gid

        # Step 1: Section entity cache
        try:
            self._cache.invalidate(gid, [EntryType.SECTION])
        except CACHE_TRANSIENT_ERRORS as exc:
            logger.warning(
                "section_cache_invalidation_failed",
                extra={"gid": gid, "error": str(exc)},
            )

        # Step 2: Project-level DataFrame invalidation
        if event.project_gids:
            await self._invalidate_project_dataframes(event.project_gids)

        # Step 3: If a task was added to this section, invalidate the task too
        # section_gid is reused to carry the task_gid that was added
        if (
            event.mutation_type == MutationType.ADD_MEMBER
            and event.section_gid
        ):
            self._invalidate_entity_entries(event.section_gid)

        logger.debug(
            "section_invalidation_complete",
            extra={
                "section_gid": gid,
                "mutation_type": event.mutation_type.value,
                "project_count": len(event.project_gids),
            },
        )

    # --- Private: Invalidation Primitives ---

    def _invalidate_entity_entries(
        self, gid: str, event: MutationEvent | None = None
    ) -> None:
        """Invalidate or soft-mark TASK, SUBTASKS, DETECTION entries for a GID.

        If soft invalidation is enabled and the event qualifies, entries
        are marked with a staleness hint instead of being evicted.
        """
        if event is not None and self._should_soft_invalidate(event):
            self._soft_invalidate_entity_entries(gid, event)
        else:
            self._hard_invalidate_entity_entries(gid)

    def _hard_invalidate_entity_entries(self, gid: str) -> None:
        """Hard invalidate (evict) entity entries."""
        try:
            self._cache.invalidate(gid, _TASK_ENTRY_TYPES)
        except CACHE_TRANSIENT_ERRORS as exc:
            logger.warning(
                "entity_cache_invalidation_failed",
                extra={"gid": gid, "error": str(exc)},
            )

    def _should_soft_invalidate(self, event: MutationEvent) -> bool:
        """Check if this event should use soft invalidation."""
        if not self._soft_config.enabled:
            return False
        if (
            self._soft_config.soft_entity_kinds
            and event.entity_kind.value not in self._soft_config.soft_entity_kinds
        ):
            return False
        if event.mutation_type.value not in self._soft_config.soft_mutation_types:
            return False
        return True

    def _soft_invalidate_entity_entries(
        self, gid: str, event: MutationEvent
    ) -> None:
        """Mark entries stale without evicting.

        Reads each entry, applies a staleness hint to its stamp,
        and writes back. If the entry does not exist or has no stamp,
        falls back to hard invalidation.
        """
        hint = (
            f"mutation:{event.entity_kind.value}:"
            f"{event.mutation_type.value}:{event.entity_gid}"
        )

        for entry_type in _TASK_ENTRY_TYPES:
            try:
                entry = self._cache.get_versioned(gid, entry_type)
                if entry is None or entry.freshness_stamp is None:
                    # No entry or legacy entry -- hard invalidate
                    self._cache.invalidate(gid, [entry_type])
                    continue

                # Apply staleness hint
                marked_stamp = entry.freshness_stamp.with_staleness_hint(hint)
                marked_entry = replace(entry, freshness_stamp=marked_stamp)
                self._cache.set_versioned(gid, marked_entry)

                logger.info(
                    "freshness_soft_invalidation",
                    extra={
                        "gid": gid,
                        "entry_type": entry_type.value,
                        "hint": hint,
                        "previous_source": entry.freshness_stamp.source.value,
                    },
                )

            except Exception as exc:  # BROAD-CATCH: isolation -- per-entry loop with fallback to hard invalidation
                logger.warning(
                    "soft_invalidation_failed_falling_back",
                    extra={
                        "gid": gid,
                        "entry_type": entry_type.value,
                        "error": str(exc),
                    },
                )
                # Fallback: hard invalidate on any error
                try:
                    self._cache.invalidate(gid, [entry_type])
                except Exception:  # BROAD-CATCH: isolation -- last-resort fallback, must not fail
                    logger.warning(
                        "hard_invalidation_fallback_failed",
                        extra={
                            "gid": gid,
                            "entry_type": entry_type.value,
                        },
                        exc_info=True,
                    )
                    pass

    def _invalidate_per_task_dataframes(
        self, task_gid: str, project_gids: list[str]
    ) -> None:
        """Invalidate per-task DataFrame entries (task_gid:project_gid keys)."""
        from autom8_asana.cache.integration.dataframes import invalidate_task_dataframes

        try:
            invalidate_task_dataframes(task_gid, project_gids, self._cache)
        except CACHE_TRANSIENT_ERRORS as exc:
            logger.warning(
                "per_task_dataframe_invalidation_failed",
                extra={
                    "task_gid": task_gid,
                    "project_count": len(project_gids),
                    "error": str(exc),
                },
            )

    async def _invalidate_project_dataframes(
        self, project_gids: list[str]
    ) -> None:
        """Invalidate DataFrameCache for entire projects.

        When a task is created, moved, or removed from a project,
        the project's full DataFrame is affected and must be invalidated.
        """
        if not self._dataframe_cache:
            return

        for project_gid in project_gids:
            try:
                self._dataframe_cache.invalidate_project(project_gid)
            except Exception as exc:  # BROAD-CATCH: isolation -- per-project loop, single failure must not abort batch
                logger.warning(
                    "project_dataframe_invalidation_failed",
                    extra={"project_gid": project_gid, "error": str(exc)},
                )


def _log_task_exception(task: asyncio.Task) -> None:  # type: ignore[type-arg]
    """Callback for fire-and-forget tasks. Logs unhandled exceptions.

    Attached via task.add_done_callback() to ensure background task
    failures are always visible in logs.
    """
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error(
            "background_invalidation_exception",
            extra={
                "task_name": task.get_name(),
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
