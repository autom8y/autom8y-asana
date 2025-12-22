"""Dataframe caching with project-aware keys.

Per ADR-0021, dataframe (computed row) entries are cached per task+project
combination because custom field values vary by project context.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.versioning import parse_version

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider


def make_dataframe_key(task_gid: str, project_gid: str) -> str:
    """Create cache key for dataframe entry.

    Per ADR-0021, dataframe entries vary by project due to custom fields,
    so key includes both task and project GID.

    Args:
        task_gid: The task GID.
        project_gid: The project GID.

    Returns:
        Composite key in format "task_gid:project_gid".

    Example:
        >>> make_dataframe_key("12345", "67890")
        '12345:67890'
    """
    return f"{task_gid}:{project_gid}"


async def load_dataframe_cached(
    task_gid: str,
    project_gid: str,
    cache: CacheProvider,
    compute_fn: Callable[[str, str], Awaitable[dict[str, Any]]],
    current_modified_at: str | None = None,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], CacheEntry | None, bool]:
    """Load dataframe (computed row) with caching.

    Per ADR-0021:
    - Cache key is dataframe:{task_gid}:{project_gid}
    - Invalidate when task's modified_at changes
    - Dataframe entries vary by project due to custom fields

    Args:
        task_gid: The task GID.
        project_gid: The project GID (for custom fields context).
        cache: Cache provider.
        compute_fn: Async function(task_gid, project_gid) -> dataframe_dict.
        current_modified_at: Current task modified_at for staleness check.
        force_refresh: Force recompute even if cached.

    Returns:
        Tuple of (dataframe_dict, cache_entry, was_cache_hit).
        was_cache_hit is True if data was served from cache.
    """
    key = make_dataframe_key(task_gid, project_gid)

    if not force_refresh:
        # Try cache
        cached = cache.get_versioned(key, EntryType.DATAFRAME)

        if cached is not None:
            # Check if still current
            if current_modified_at is None or cached.is_current(current_modified_at):
                return cached.data, cached, True

    # Compute fresh dataframe entry
    dataframe_data = await compute_fn(task_gid, project_gid)

    # Determine version
    now = datetime.now(timezone.utc)
    version_dt = parse_version(current_modified_at) if current_modified_at else now

    # Cache it
    entry = CacheEntry(
        key=key,
        data=dataframe_data,
        entry_type=EntryType.DATAFRAME,
        version=version_dt,
        cached_at=now,
        project_gid=project_gid,
    )
    cache.set_versioned(key, entry)

    return dataframe_data, entry, False


def invalidate_dataframe(
    task_gid: str,
    project_gid: str,
    cache: CacheProvider,
) -> None:
    """Invalidate dataframe cache for a task+project.

    Args:
        task_gid: The task GID.
        project_gid: The project GID.
        cache: Cache provider.
    """
    key = make_dataframe_key(task_gid, project_gid)
    cache.invalidate(key, [EntryType.DATAFRAME])


def invalidate_task_dataframes(
    task_gid: str,
    project_gids: list[str],
    cache: CacheProvider,
) -> None:
    """Invalidate dataframe cache for a task across multiple projects.

    Use when a task is modified and all project views need refresh.

    Args:
        task_gid: The task GID.
        project_gids: List of project GIDs to invalidate.
        cache: Cache provider.
    """
    for project_gid in project_gids:
        invalidate_dataframe(task_gid, project_gid, cache)


def parse_dataframe_key(key: str) -> tuple[str, str] | None:
    """Parse a dataframe cache key into its components.

    Args:
        key: Cache key in format "task_gid:project_gid".

    Returns:
        Tuple of (task_gid, project_gid) or None if invalid format.

    Example:
        >>> parse_dataframe_key("12345:67890")
        ('12345', '67890')
        >>> parse_dataframe_key("invalid")
        None
    """
    parts = key.split(":", 1)
    if len(parts) != 2:
        return None
    return (parts[0], parts[1])


async def load_batch_dataframes_cached(
    task_project_pairs: list[tuple[str, str]],
    cache: CacheProvider,
    compute_fn: Callable[[str, str], Awaitable[dict[str, Any]]],
    modifications: dict[str, str] | None = None,
    force_refresh: bool = False,
) -> dict[str, tuple[dict[str, Any], bool]]:
    """Load multiple dataframe entries with caching.

    Batch loading for efficiency when processing multiple tasks.

    Args:
        task_project_pairs: List of (task_gid, project_gid) tuples.
        cache: Cache provider.
        compute_fn: Async function(task_gid, project_gid) -> dataframe_dict.
        modifications: Dict of task_gid -> modified_at for staleness check.
        force_refresh: Force recompute even if cached.

    Returns:
        Dict mapping dataframe_key -> (dataframe_dict, was_cache_hit).
    """
    modifications = modifications or {}

    # Inner function for concurrent loading
    async def load_single(
        task_gid: str, project_gid: str
    ) -> tuple[str, dict[str, Any], bool]:
        key = make_dataframe_key(task_gid, project_gid)
        current_modified_at = modifications.get(task_gid)

        dataframe_data, _, was_hit = await load_dataframe_cached(
            task_gid=task_gid,
            project_gid=project_gid,
            cache=cache,
            compute_fn=compute_fn,
            current_modified_at=current_modified_at,
            force_refresh=force_refresh,
        )
        return key, dataframe_data, was_hit

    # Run all loads concurrently - O(1) latency instead of O(N)
    tasks = [load_single(t, p) for t, p in task_project_pairs]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results, skipping failures (partial results on error)
    results: dict[str, tuple[dict[str, Any], bool]] = {}
    for result in completed:
        if isinstance(result, BaseException):
            # Skip failed loads, return partial results
            # In production, this would use LogProvider for error reporting
            continue
        key, dataframe_data, was_hit = result
        results[key] = (dataframe_data, was_hit)

    return results
