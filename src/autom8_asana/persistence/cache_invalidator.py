"""Cache invalidation coordinator for SaveSession commits.

Per ADR-0059: Extracted from session.py for Single Responsibility Principle.
Per FR-INVALIDATE-001 through FR-INVALIDATE-006.
Per TDD-WATERMARK-CACHE Phase 3: DataFrame cache invalidation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8_asana.core.exceptions import CACHE_TRANSIENT_ERRORS

if TYPE_CHECKING:
    from autom8_asana.persistence.models import ActionResult, SaveResult


class CacheInvalidator:
    """Coordinates cache invalidation after SaveSession commits.

    Per FR-INVALIDATE-001 through FR-INVALIDATE-006.
    Handles TASK, SUBTASKS, DETECTION, and DataFrame cache entries.

    Thread Safety: Stateless - safe for concurrent use.
    No internal state modified after __init__.

    Responsibility: Single - Cache entry invalidation for committed entities.

    Usage:
        >>> invalidator = CacheInvalidator(cache_provider, log)
        >>> gid_lookup = build_gid_to_entity_map(crud_result, action_results, tracker)
        >>> await invalidator.invalidate_for_commit(crud_result, action_results, gid_lookup)
    """

    def __init__(
        self,
        cache_provider: Any,
        log: Any | None = None,
    ) -> None:
        """Initialize invalidator with cache provider.

        Args:
            cache_provider: Cache implementation with invalidate() method.
                           Can be None (invalidation becomes no-op).
            log: Optional structured logger for debug/warning messages.
        """
        self._cache = cache_provider
        self._log = log

    async def invalidate_for_commit(
        self,
        crud_result: SaveResult,
        action_results: list[ActionResult],
        gid_to_entity_lookup: dict[str, Any],
    ) -> None:
        """Invalidate all cache entries affected by commit.

        Per FR-INVALIDATE-001: Invalidates after successful mutations.
        Per FR-INVALIDATE-002: UPDATE operations invalidate, including DATAFRAME.
        Per FR-INVALIDATE-003: DELETE operations invalidate.
        Per FR-INVALIDATE-004: CREATE operations warm cache.
        Per FR-INVALIDATE-005: Batch invalidation efficiency (O(n)).
        Per FR-INVALIDATE-006: Action operations invalidate.
        Per TDD-WATERMARK-CACHE/FR-INVALIDATE-001-006: DataFrame cache invalidation.

        Implementation:
        1. Collect GIDs from succeeded CRUD operations
        2. Collect GIDs from successful action operations
        3. Invalidate TASK, SUBTASKS, DETECTION entries
        4. Invalidate DataFrame caches via membership lookup

        Failure Handling:
        - Individual invalidation failures logged but don't fail commit
        - Per NFR-DEGRADE-001: Graceful degradation

        Args:
            crud_result: Result of CRUD operations with succeeded entities.
            action_results: Results of action operations.
            gid_to_entity_lookup: Map of GID -> entity for membership lookup.
        """
        if self._cache is None:
            return

        gids = self._collect_affected_gids(crud_result, action_results)
        if not gids:
            return

        self._invalidate_entity_caches(gids)
        self._invalidate_dataframe_caches(gids, gid_to_entity_lookup)

        if self._log:
            self._log.debug(
                "cache_invalidation_complete",
                invalidated_count=len(gids),
            )

    def _collect_affected_gids(
        self,
        crud_result: SaveResult,
        action_results: list[ActionResult],
    ) -> set[str]:
        """Collect GIDs of entities requiring cache invalidation.

        Per FR-INVALIDATE-005: Batch efficiency via set collection.

        Sources:
        1. CRUD succeeded entities (CREATE/UPDATE/DELETE)
        2. Action operation task GIDs (where action.success)

        Args:
            crud_result: Result containing succeeded entities.
            action_results: Results from action operations.

        Returns:
            Set of GIDs needing cache invalidation.
        """
        gids: set[str] = set()

        # FR-INVALIDATE-002, FR-INVALIDATE-003: CRUD succeeded entities
        for entity in crud_result.succeeded:
            if hasattr(entity, "gid") and entity.gid:
                gids.add(entity.gid)

        # FR-INVALIDATE-006: Action operations
        for action_result in action_results:
            if action_result.success and action_result.action.task:
                task = action_result.action.task
                if hasattr(task, "gid") and task.gid:
                    gids.add(task.gid)

        return gids

    def _invalidate_entity_caches(self, gids: set[str]) -> None:
        """Invalidate TASK, SUBTASKS, DETECTION cache entries.

        Per FR-INVALIDATE-001: Detection cache invalidated alongside TASK and SUBTASKS.

        Args:
            gids: Set of GIDs to invalidate.
        """
        from autom8_asana.cache.models.entry import EntryType

        for gid in gids:
            try:
                self._cache.invalidate(
                    gid,
                    [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION],
                )
            except (
                CACHE_TRANSIENT_ERRORS
            ) as exc:  # isolation -- per-gid loop, single failure must not abort batch
                # NFR-DEGRADE-001: Log and continue - invalidation failure is not fatal
                if self._log:
                    self._log.warning(
                        "cache_invalidation_failed",
                        gid=gid,
                        error=str(exc),
                    )

    def _invalidate_dataframe_caches(
        self,
        gids: set[str],
        gid_to_entity: dict[str, Any],
    ) -> None:
        """Invalidate DataFrame caches for project contexts.

        Per TDD-WATERMARK-CACHE Phase 3: DataFrame cache invalidation.
        Per FR-INVALIDATE-003: Invalidate all project contexts via memberships.

        Args:
            gids: Set of GIDs to invalidate.
            gid_to_entity: Map of GID -> entity for membership lookup.
        """
        from autom8_asana.cache.integration.dataframes import invalidate_task_dataframes

        for gid in gids:
            entity = gid_to_entity.get(gid)
            if entity and hasattr(entity, "memberships") and entity.memberships:
                try:
                    # FR-INVALIDATE-003: Invalidate all project contexts via memberships
                    project_gids = [
                        m.get("project", {}).get("gid")
                        for m in entity.memberships
                        if isinstance(m, dict) and m.get("project", {}).get("gid")
                    ]
                    if project_gids:
                        invalidate_task_dataframes(gid, project_gids, self._cache)
                except CACHE_TRANSIENT_ERRORS as exc:  # isolation -- per-gid loop, single failure must not abort batch
                    # FR-INVALIDATE-005: Don't fail commit on invalidation error
                    if self._log:
                        self._log.warning(
                            "dataframe_cache_invalidation_failed",
                            gid=gid,
                            error=str(exc),
                        )
