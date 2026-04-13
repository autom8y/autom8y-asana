"""Hierarchy warming for the progressive project builder.

Extracted from ProgressiveProjectBuilder to separate hierarchy warming
concern from the build pipeline. Handles:
- Reconstructing hierarchy from resumed parquet data
- Fetching and caching gap tasks missing from the store
- Populating the store with freshly-fetched section tasks
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.errors import S3_TRANSPORT_ERRORS
from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS

if TYPE_CHECKING:
    from collections.abc import Callable

    import polars as pl

    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

__all__ = ["HierarchyWarmer"]

logger = get_logger(__name__)


class HierarchyWarmer:
    """Warms hierarchy index and populates store with parent chain data.

    Extracted from ProgressiveProjectBuilder to separate hierarchy
    warming concern from the build pipeline.
    """

    def __init__(
        self,
        store: Any,
        client: AsanaClient,
        project_gid: str,
        entity_type: str,
        max_concurrent: int,
        task_to_dict: Callable[[Task], dict[str, Any]],
    ) -> None:
        """Initialize HierarchyWarmer.

        Args:
            store: UnifiedStore for cache operations.
            client: AsanaClient for API calls.
            project_gid: Asana project GID.
            entity_type: Entity type string.
            max_concurrent: Max concurrent API fetches.
            task_to_dict: Callback to convert Task model to dict.
        """
        self._store = store
        self._client = client
        self._project_gid = project_gid
        self._entity_type = entity_type
        self._max_concurrent = max_concurrent
        self._task_to_dict = task_to_dict

    def reconstruct_hierarchy_from_dataframe(self, df: pl.DataFrame) -> int:
        """Reconstruct HierarchyIndex from resumed parquet parent_gid column.

        Per TDD-CASCADE-RESUME-FIX: When sections are loaded from S3,
        tasks are not registered in the UnifiedStore's HierarchyIndex.
        This method iterates the merged DataFrame and registers each
        (gid, parent_gid) pair so cascade validation (Step 5.5) can
        resolve parent chains for resumed sections.

        Args:
            df: Merged DataFrame with 'gid' and 'parent_gid' columns.

        Returns:
            Count of hierarchy entries registered.
        """
        if self._store is None:
            return 0

        if "gid" not in df.columns or "parent_gid" not in df.columns:
            return 0

        hierarchy = self._store.get_hierarchy_index()
        registered = 0

        gids = df["gid"].to_list()
        parent_gids = df["parent_gid"].to_list()

        for gid, parent_gid in zip(gids, parent_gids):
            if gid is None:
                continue

            # Skip if already registered (from freshly-fetched sections)
            if hierarchy.contains(str(gid)):
                continue

            # Build minimal task dict for hierarchy registration
            task_dict: dict[str, Any] = {"gid": str(gid)}
            if parent_gid is not None:
                task_dict["parent"] = {"gid": str(parent_gid)}

            hierarchy.register(task_dict)
            registered += 1

        if registered > 0:
            logger.info(
                "hierarchy_reconstructed_from_parquet",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "entries_registered": registered,
                    "total_rows": len(df),
                },
            )

        return registered

    async def warm_hierarchy_gaps_async(self, df: pl.DataFrame) -> int:
        """Warm hierarchy gaps by fetching uncached parent tasks from API.

        Per TDD-CASCADE-RESUME-FIX: After reconstructing unit → unit_holder
        links from parquet parent_gid, the unit_holder → business links are
        still missing because unit_holders were registered only as parents
        (not as tasks with their own parent). This method directly fetches
        uncached parent GIDs from the API — the API response reveals their
        parent (business), which gets registered in the hierarchy, completing
        the chain for cascade resolution.

        Per WS-1-cascade-null-fix: Fetches full task data from the API
        instead of storing GID-only stubs. Stubs lack the ``parent`` field
        needed by ``put_batch_async``'s hierarchy warming to discover the
        next level (e.g., unit_holder → business). Without the parent field,
        ``_fetch_immediate_parents`` finds no parents to fetch, leaving the
        chain incomplete and cascade fields unresolvable.

        Args:
            df: Merged DataFrame with 'parent_gid' column.

        Returns:
            Count of gap tasks fetched and cached.
        """
        if self._store is None or "parent_gid" not in df.columns:
            return 0

        parent_gids = [str(g) for g in df["parent_gid"].drop_nulls().unique().to_list()]
        if not parent_gids:
            return 0

        # Filter to parent GIDs not already cached as full task data
        from autom8_asana.cache.models.entry import EntryType

        uncached = []
        for gid in parent_gids:
            cached = self._store.cache.get_versioned(gid, EntryType.TASK)
            if cached is None:
                uncached.append(gid)

        if not uncached:
            return 0

        logger.info(
            "hierarchy_gap_fetch_starting",
            extra={
                "project_gid": self._project_gid,
                "entity_type": self._entity_type,
                "total_parent_gids": len(parent_gids),
                "uncached_count": len(uncached),
            },
        )

        # Fetch full task data from the API for each uncached parent.
        # Per WS-1-cascade-null-fix: GID-only stubs lack the ``parent``
        # field, so put_batch_async's _fetch_immediate_parents cannot
        # discover the next ancestor level. Fetching full task data
        # ensures the parent link is present, allowing hierarchy warming
        # to traverse the complete chain (e.g., unit_holder → business).
        try:
            fetched_task_dicts: list[dict[str, Any]] = []

            async def _fetch_gap_parent(gid: str) -> dict[str, Any] | None:
                try:
                    task = await self._client.tasks.get_async(gid, opt_fields=BASE_OPT_FIELDS)
                    if task is not None:
                        return self._task_to_dict(task)
                    return None
                except S3_TRANSPORT_ERRORS as e:
                    logger.warning(
                        "hierarchy_gap_fetch_failed",
                        extra={
                            "parent_gid": gid,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    return None

            results = await gather_with_limit(
                [_fetch_gap_parent(gid) for gid in uncached],
                max_concurrent=self._max_concurrent,
            )

            for result in results:
                if result is not None:
                    fetched_task_dicts.append(result)

            if not fetched_task_dicts:
                logger.warning(
                    "hierarchy_gap_no_tasks_fetched",
                    extra={
                        "project_gid": self._project_gid,
                        "entity_type": self._entity_type,
                        "attempted": len(uncached),
                    },
                )
                return 0

            # Store fetched tasks with hierarchy warming enabled.
            # Now that task_dicts contain full parent info,
            # _fetch_immediate_parents will discover and fetch the
            # next ancestor level (e.g., business from unit_holder.parent).
            await self._store.put_batch_async(
                fetched_task_dicts,
                opt_fields=BASE_OPT_FIELDS,
                tasks_client=self._client.tasks,
                warm_hierarchy=True,
            )

            logger.info(
                "hierarchy_gap_warming_complete",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "attempted": len(uncached),
                    "fetched": len(fetched_task_dicts),
                },
            )

            return len(fetched_task_dicts)
        except Exception as e:  # BROAD-CATCH: enrichment
            logger.warning(
                "hierarchy_gap_warming_failed",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "parent_gids_count": len(uncached),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 0

    async def populate_store_with_tasks(self, tasks: list[Task]) -> None:
        """Populate UnifiedStore with fetched tasks for cascade resolution.

        Per ADR-cascade-field-resolution: Uses put_batch_async with warm_hierarchy=True
        to recursively fetch and cache parent tasks. This ensures fields like
        office_phone and vertical that cascade from Business are properly resolved.

        The hierarchy warming:
        - Fetches immediate parents not already in cache
        - Recursively warms ancestors up to max_depth=5
        - Includes custom_fields for cascade field extraction
        """
        if not tasks or self._store is None:
            return

        try:
            # Convert Task models to dicts for batch storage
            task_dicts = [self._task_to_dict(task) for task in tasks]

            logger.info(
                "store_populate_batch_starting",
                extra={
                    "task_count": len(task_dicts),
                    "entity_type": self._entity_type,
                    "project_gid": self._project_gid,
                    "warm_hierarchy": True,
                },
            )

            # Use put_batch_async with hierarchy warming - same pattern as project.py
            # This recursively fetches and caches parent chains for cascade resolution
            await self._store.put_batch_async(
                task_dicts,
                opt_fields=BASE_OPT_FIELDS,
                tasks_client=self._client.tasks,
                warm_hierarchy=True,
            )

        except Exception as e:  # BROAD-CATCH: enrichment
            # Don't fail build if store population fails
            logger.warning(
                "store_populate_batch_failed",
                extra={
                    "task_count": len(tasks),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "entity_type": self._entity_type,
                },
            )
