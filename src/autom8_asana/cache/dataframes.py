"""Dataframe (struc) caching with project-aware keys.

Per ADR-0021, struc (computed dataframe rows) are cached per task+project
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


def make_struc_key(task_gid: str, project_gid: str) -> str:
    """Create cache key for struc entry.

    Per ADR-0021, struc varies by project due to custom fields,
    so key includes both task and project GID.

    Args:
        task_gid: The task GID.
        project_gid: The project GID.

    Returns:
        Composite key in format "task_gid:project_gid".

    Example:
        >>> make_struc_key("12345", "67890")
        '12345:67890'
    """
    return f"{task_gid}:{project_gid}"


async def load_struc_cached(
    task_gid: str,
    project_gid: str,
    cache: CacheProvider,
    compute_fn: Callable[[str, str], Awaitable[dict[str, Any]]],
    current_modified_at: str | None = None,
    force_refresh: bool = False,
) -> tuple[dict[str, Any], CacheEntry | None, bool]:
    """Load struc (computed dataframe row) with caching.

    Per ADR-0021:
    - Cache key is struc:{task_gid}:{project_gid}
    - Invalidate when task's modified_at changes
    - Struc varies by project due to custom fields

    Args:
        task_gid: The task GID.
        project_gid: The project GID (for custom fields context).
        cache: Cache provider.
        compute_fn: Async function(task_gid, project_gid) -> struc_dict.
        current_modified_at: Current task modified_at for staleness check.
        force_refresh: Force recompute even if cached.

    Returns:
        Tuple of (struc_dict, cache_entry, was_cache_hit).
        was_cache_hit is True if struc was served from cache.
    """
    key = make_struc_key(task_gid, project_gid)

    if not force_refresh:
        # Try cache
        cached = cache.get_versioned(key, EntryType.STRUC)

        if cached is not None:
            # Check if still current
            if current_modified_at is None or cached.is_current(current_modified_at):
                return cached.data, cached, True

    # Compute fresh struc
    struc = await compute_fn(task_gid, project_gid)

    # Determine version
    now = datetime.now(timezone.utc)
    version_dt = parse_version(current_modified_at) if current_modified_at else now

    # Cache it
    entry = CacheEntry(
        key=key,
        data=struc,
        entry_type=EntryType.STRUC,
        version=version_dt,
        cached_at=now,
        project_gid=project_gid,
    )
    cache.set_versioned(key, entry)

    return struc, entry, False


def invalidate_struc(
    task_gid: str,
    project_gid: str,
    cache: CacheProvider,
) -> None:
    """Invalidate struc cache for a task+project.

    Args:
        task_gid: The task GID.
        project_gid: The project GID.
        cache: Cache provider.
    """
    key = make_struc_key(task_gid, project_gid)
    cache.invalidate(key, [EntryType.STRUC])


def invalidate_task_strucs(
    task_gid: str,
    project_gids: list[str],
    cache: CacheProvider,
) -> None:
    """Invalidate struc cache for a task across multiple projects.

    Use when a task is modified and all project views need refresh.

    Args:
        task_gid: The task GID.
        project_gids: List of project GIDs to invalidate.
        cache: Cache provider.
    """
    for project_gid in project_gids:
        invalidate_struc(task_gid, project_gid, cache)


def parse_struc_key(key: str) -> tuple[str, str] | None:
    """Parse a struc cache key into its components.

    Args:
        key: Cache key in format "task_gid:project_gid".

    Returns:
        Tuple of (task_gid, project_gid) or None if invalid format.

    Example:
        >>> parse_struc_key("12345:67890")
        ('12345', '67890')
        >>> parse_struc_key("invalid")
        None
    """
    parts = key.split(":", 1)
    if len(parts) != 2:
        return None
    return (parts[0], parts[1])


async def load_batch_strucs_cached(
    task_project_pairs: list[tuple[str, str]],
    cache: CacheProvider,
    compute_fn: Callable[[str, str], Awaitable[dict[str, Any]]],
    modifications: dict[str, str] | None = None,
    force_refresh: bool = False,
) -> dict[str, tuple[dict[str, Any], bool]]:
    """Load multiple strucs with caching.

    Batch loading for efficiency when processing multiple tasks.

    Args:
        task_project_pairs: List of (task_gid, project_gid) tuples.
        cache: Cache provider.
        compute_fn: Async function(task_gid, project_gid) -> struc_dict.
        modifications: Dict of task_gid -> modified_at for staleness check.
        force_refresh: Force recompute even if cached.

    Returns:
        Dict mapping struc_key -> (struc_dict, was_cache_hit).
    """
    modifications = modifications or {}

    # Inner function for concurrent loading
    async def load_single(
        task_gid: str, project_gid: str
    ) -> tuple[str, dict[str, Any], bool]:
        key = make_struc_key(task_gid, project_gid)
        current_modified_at = modifications.get(task_gid)

        struc, _, was_hit = await load_struc_cached(
            task_gid=task_gid,
            project_gid=project_gid,
            cache=cache,
            compute_fn=compute_fn,
            current_modified_at=current_modified_at,
            force_refresh=force_refresh,
        )
        return key, struc, was_hit

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
        key, struc, was_hit = result
        results[key] = (struc, was_hit)

    return results
