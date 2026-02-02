"""Hierarchy warmer for transitive parent chain registration.

Per ADR-hierarchy-registration-architecture: Ensures complete parent chains
are registered in HierarchyIndex by recursively fetching missing ancestors.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.entry import EntryType

if TYPE_CHECKING:
    from autom8_asana.cache.hierarchy import HierarchyIndex
    from autom8_asana.cache.unified import UnifiedTaskStore
    from autom8_asana.clients.tasks import TasksClient

logger = get_logger(__name__)

# Fields needed for hierarchy registration AND cascade resolution
# Per ADR-hierarchy-registration-architecture: Include custom_fields for cascade resolution
# Per TDD-unit-cascade-resolution-fix: Must include all custom field types for complete
# cascade resolution (enum, number, multi_enum in addition to text)
_HIERARCHY_OPT_FIELDS: list[str] = [
    "gid",
    "name",
    "parent",
    "parent.gid",
    # Per TDD-DETECTION: Required for Tier 1 detection via ProjectTypeRegistry
    "memberships.project.gid",
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.resource_subtype",  # Required for type-aware extraction
    "custom_fields.display_value",
    "custom_fields.text_value",
    "custom_fields.enum_value",  # For enum fields like Vertical
    "custom_fields.enum_value.name",  # For enum name extraction
    "custom_fields.number_value",  # For numeric fields
    "custom_fields.multi_enum_values",  # For multi-enum fields
    "custom_fields.multi_enum_values.name",  # For multi-enum names
]

# Conservative concurrency for hierarchy warming to avoid overwhelming Asana's rate limits.
# Asana allows 1500 req/min (25/sec), but bursting 25 concurrent requests triggers 429s.
# The SDK's TokenBucketRateLimiter handles per-request throttling; we limit concurrency
# to prevent burst spikes that exceed instantaneous limits.
_DEFAULT_MAX_CONCURRENT: int = 5


async def _gather_with_limit(
    coros: list[Any],
    max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
    semaphore: asyncio.Semaphore | None = None,
) -> list[Any]:
    """Execute coroutines with bounded concurrency using semaphore.

    Args:
        coros: List of coroutines to execute
        max_concurrent: Maximum concurrent executions
        semaphore: Optional external semaphore (overrides max_concurrent).

    Returns:
        List of results in same order as input coroutines
    """
    sem = semaphore or asyncio.Semaphore(max_concurrent)

    async def bounded_coro(coro: Any) -> Any:
        async with sem:
            return await coro

    return await asyncio.gather(*[bounded_coro(c) for c in coros])


def _is_rate_limit_error(exc: Exception) -> bool:
    """Check if an exception indicates a 429 rate limit error."""
    # Check for httpx.HTTPStatusError or similar with status_code
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    if status_code == 429:
        return True
    # Check string representation as fallback
    return "429" in str(exc) or "rate limit" in str(exc).lower()


async def _fetch_parent(
    gid: str,
    tasks_client: TasksClient,
    backoff_event: asyncio.Event | None = None,
) -> dict[str, Any] | None:
    """Fetch a single task with fields needed for cascade resolution.

    Args:
        gid: Task GID to fetch.
        tasks_client: TasksClient for fetching.
        backoff_event: Optional event to signal when a 429 is encountered.

    Returns:
        Full task dict with parent info and custom_fields, or None if fetch failed.
    """
    try:
        task = await tasks_client.get_async(gid, opt_fields=_HIERARCHY_OPT_FIELDS)
        # Return full task dict for caching
        return task.model_dump(exclude_none=True)
    except Exception as e:
        if _is_rate_limit_error(e) and backoff_event is not None:
            backoff_event.set()
        logger.warning(
            "hierarchy_warm_fetch_failed",
            extra={"gid": gid, "error": str(e)},
        )
        return None


async def warm_ancestors_async(
    gids: list[str],
    hierarchy_index: HierarchyIndex,
    tasks_client: TasksClient,
    max_depth: int = 5,
    max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
    unified_store: UnifiedTaskStore | None = None,
    global_semaphore: asyncio.Semaphore | None = None,
) -> int:
    """Recursively fetch, cache, and register parent chains.

    Traverses the parent chain for each GID, fetching missing ancestors,
    caching them in the unified store (if provided), and registering them
    in the hierarchy index until max_depth or root.

    Args:
        gids: Starting task GIDs whose ancestors should be warmed.
        hierarchy_index: HierarchyIndex to register parents in.
        tasks_client: TasksClient for fetching missing parents.
        max_depth: Maximum depth to traverse (default 5 for Offer hierarchy).
        max_concurrent: Maximum concurrent fetch operations.
        unified_store: Optional UnifiedTaskStore to cache fetched parents.
            Per ADR-hierarchy-registration-architecture: Fetched parents are
            cached with custom_fields for cascade resolution.
        global_semaphore: Optional shared semaphore to bound all hierarchy
            fetches across concurrent sections. Overrides max_concurrent.

    Returns:
        Count of ancestors warmed (fetched and registered).

    Example:
        >>> warmed = await warm_ancestors_async(
        ...     gids=["unit-123"],
        ...     hierarchy_index=store.get_hierarchy_index(),
        ...     tasks_client=client.tasks,
        ...     unified_store=store,
        ... )
        >>> print(f"Warmed {warmed} ancestors")
    """
    total_warmed = 0
    visited: set[str] = set()
    backoff_event = asyncio.Event()

    # Start with the initial GIDs as already visited (we don't need to fetch them)
    visited.update(gids)

    # Per TDD-unit-cascade-resolution-fix: Extract parent GIDs from the initial tasks
    # to start traversal. The initial GIDs are the tasks we already have (e.g., Units),
    # but we need to fetch their PARENTS (e.g., Business tasks).
    current_gids: list[str] = []
    for gid in gids:
        parent_gid = hierarchy_index.get_parent_gid(gid)
        if parent_gid and parent_gid not in visited:
            current_gids.append(parent_gid)

    # INFO-level logging for warm_ancestors entry
    logger.info(
        "warm_ancestors_starting",
        extra={
            "initial_gids_count": len(gids),
            "parent_gids_to_fetch": len(current_gids),
            "max_depth": max_depth,
        },
    )

    depth = 0

    while depth < max_depth and current_gids:
        # At each level, current_gids contains GIDs that we need to fetch
        # (we know about them from the previous level, but haven't fetched their data yet)

        # Filter to GIDs we haven't already fetched
        # Per TDD-unit-cascade-resolution-fix Fix 2: Always check CACHE first.
        # hierarchy_index.contains() returns True when a GID exists in _children_map
        # (added during child registration), but this doesn't mean the task data
        # is actually cached. We need the full task data for cascade resolution.
        gids_to_fetch: list[str] = []
        for gid in current_gids:
            if gid not in visited:
                visited.add(gid)
                # Check if task data is actually cached (not just hierarchy relationship)
                if unified_store:
                    cached = unified_store.cache.get_versioned(gid, EntryType.TASK)
                    if cached is None:
                        gids_to_fetch.append(gid)
                else:
                    # No unified_store - fall back to hierarchy check
                    if not hierarchy_index.contains(gid):
                        gids_to_fetch.append(gid)

        if not gids_to_fetch:
            # No more GIDs to fetch at this level
            # Check if any current GIDs have parents we should explore
            next_level_gids: list[str] = []
            for gid in current_gids:
                parent_gid = hierarchy_index.get_parent_gid(gid)
                if parent_gid and parent_gid not in visited:
                    next_level_gids.append(parent_gid)
            current_gids = next_level_gids
            depth += 1
            continue

        parents_to_fetch = gids_to_fetch
        already_known: list[str] = []

        # Adaptive backoff: pause if previous batch hit 429s
        if backoff_event.is_set():
            backoff_event.clear()
            await asyncio.sleep(2.0)
            logger.info(
                "hierarchy_warm_429_backoff",
                extra={"depth": depth},
            )

        # Batch fetch missing parents with bounded concurrency
        fetched_results: list[dict[str, Any] | None] = []
        if parents_to_fetch:
            fetched_results = await _gather_with_limit(
                [
                    _fetch_parent(gid, tasks_client, backoff_event=backoff_event)
                    for gid in parents_to_fetch
                ],
                max_concurrent=max_concurrent,
                semaphore=global_semaphore,
            )

        # Register fetched parents and collect next level
        fetched_count = 0
        next_level_gids = []  # Reset from previous loop iteration
        tasks_to_cache: list[dict[str, Any]] = []

        for result in fetched_results:
            if result is not None:
                # Register in hierarchy index
                hierarchy_index.register(result)
                fetched_count += 1
                total_warmed += 1

                # Collect for caching
                tasks_to_cache.append(result)

                # Add to next level if has parent
                parent = result.get("parent")
                if parent:
                    parent_gid = (
                        parent.get("gid")
                        if isinstance(parent, dict)
                        else getattr(parent, "gid", None)
                    )
                    if parent_gid:
                        next_level_gids.append(parent_gid)

        # Cache fetched parents in unified store for cascade resolution
        # Per ADR-hierarchy-registration-architecture: Parents need custom_fields
        if unified_store and tasks_to_cache:
            # Use the store's internal cache directly (skip warming recursion)
            for task_dict in tasks_to_cache:
                await unified_store.put_async(
                    task_dict, opt_fields=_HIERARCHY_OPT_FIELDS
                )

        # Add already-known parents that might have grandparents we need
        for parent_gid in already_known:
            grandparent = hierarchy_index.get_parent_gid(parent_gid)
            if grandparent and grandparent not in visited:
                next_level_gids.append(grandparent)

        logger.debug(
            "hierarchy_warm_level",
            extra={
                "depth": depth,
                "gids_to_fetch": len(gids_to_fetch),
                "fetched_count": fetched_count,
                "next_level": len(next_level_gids),
            },
        )

        # Move to next level
        current_gids = next_level_gids
        depth += 1

    # INFO-level logging for warm_ancestors completion
    logger.info(
        "warm_ancestors_completed",
        extra={
            "total_warmed": total_warmed,
            "total_visited": len(visited),
            "final_depth": depth,
        },
    )

    return total_warmed
