"""Multi-entry loading helpers for cache operations.

This module provides utilities for loading cache entries efficiently,
handling cache misses by fetching from the API, and managing multiple
entry types and batch operations.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.staleness import check_entry_staleness

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider


async def load_task_entry(
    task_gid: str,
    entry_type: EntryType,
    cache: CacheProvider,
    fetcher: Callable[[str], Awaitable[dict[str, Any]]],
    current_modified_at: str | None = None,
    freshness: Freshness = Freshness.EVENTUAL,
    project_gid: str | None = None,
    ttl: int | None = 300,
) -> tuple[CacheEntry | None, bool]:
    """Load a cache entry for a task, fetching if needed.

    Attempts to retrieve the entry from cache first. If the entry is
    missing or stale (based on freshness mode), fetches fresh data
    from the API and caches it.

    Args:
        task_gid: The task GID to load.
        entry_type: Type of entry (TASK, SUBTASKS, etc.).
        cache: Cache provider to use.
        fetcher: Async function to fetch data from API if cache miss/stale.
            Takes task_gid as argument, returns dict of data.
        current_modified_at: Current version from Asana (for staleness check).
            Required for STRICT freshness mode.
        freshness: STRICT (always verify) or EVENTUAL (trust TTL).
            Defaults to EVENTUAL.
        project_gid: Project GID (required for STRUC entry type).
        ttl: Time-to-live in seconds for cached entry. Defaults to 300.

    Returns:
        Tuple of (CacheEntry or None, was_cache_hit: bool).
        - If fetcher succeeds: (entry, cache_hit_flag)
        - If fetcher returns empty/None: (None, False)

    Example:
        >>> async def fetch_task(gid: str) -> dict:
        ...     return {"gid": gid, "name": "My Task"}
        >>> import asyncio
        >>> from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
        >>> cache = EnhancedInMemoryCacheProvider()
        >>> entry, hit = asyncio.run(load_task_entry(
        ...     "123",
        ...     EntryType.TASK,
        ...     cache,
        ...     fetch_task,
        ... ))
        >>> hit
        False
        >>> entry.data["name"] if entry else None
        'My Task'
    """
    # Try cache first
    cached_entry = cache.get_versioned(task_gid, entry_type, freshness)

    if cached_entry is not None:
        # Check staleness based on freshness mode
        is_stale = check_entry_staleness(cached_entry, current_modified_at, freshness)
        if not is_stale:
            return cached_entry, True

    # Cache miss or stale - fetch from API
    data = await fetcher(task_gid)

    if not data:
        return None, False

    # Extract version from data if available, otherwise use current time
    version_str = data.get("modified_at")
    if version_str:
        version = _parse_version(version_str)
    else:
        version = datetime.now(UTC)

    # Create new cache entry
    entry = CacheEntry(
        key=task_gid,
        data=data,
        entry_type=entry_type,
        version=version,
        cached_at=datetime.now(UTC),
        ttl=ttl,
        project_gid=project_gid,
    )

    # Store in cache
    cache.set_versioned(task_gid, entry)

    return entry, False


async def load_task_entries(
    task_gid: str,
    entry_types: list[EntryType],
    cache: CacheProvider,
    fetchers: dict[EntryType, Callable[[str], Awaitable[dict[str, Any]]]],
    current_modified_at: str | None = None,
    freshness: Freshness = Freshness.EVENTUAL,
    project_gid: str | None = None,
    ttl: int | None = 300,
) -> dict[EntryType, tuple[CacheEntry | None, bool]]:
    """Load multiple cache entries for a task concurrently.

    Loads different entry types (TASK, SUBTASKS, etc.) for the same
    task in parallel. Each entry type uses its own fetcher function.

    Args:
        task_gid: The task GID to load entries for.
        entry_types: List of entry types to load.
        cache: Cache provider to use.
        fetchers: Dict mapping EntryType to async fetcher function.
            Each fetcher takes task_gid and returns dict of data.
        current_modified_at: Current version from Asana (for staleness check).
        freshness: STRICT or EVENTUAL freshness mode.
        project_gid: Project GID (required for STRUC entry type).
        ttl: Time-to-live in seconds. Defaults to 300.

    Returns:
        Dict mapping EntryType to tuple of (CacheEntry or None, was_cache_hit).

    Example:
        >>> async def fetch_task(gid: str) -> dict:
        ...     return {"gid": gid, "name": "Task"}
        >>> async def fetch_subtasks(gid: str) -> dict:
        ...     return {"subtasks": []}
        >>> import asyncio
        >>> from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
        >>> cache = EnhancedInMemoryCacheProvider()
        >>> results = asyncio.run(load_task_entries(
        ...     "123",
        ...     [EntryType.TASK, EntryType.SUBTASKS],
        ...     cache,
        ...     {EntryType.TASK: fetch_task, EntryType.SUBTASKS: fetch_subtasks},
        ... ))
        >>> len(results)
        2
    """
    results: dict[EntryType, tuple[CacheEntry | None, bool]] = {}

    # Create tasks for concurrent loading
    async def load_single(
        entry_type: EntryType,
    ) -> tuple[EntryType, CacheEntry | None, bool]:
        fetcher = fetchers.get(entry_type)
        if fetcher is None:
            return entry_type, None, False

        entry, hit = await load_task_entry(
            task_gid=task_gid,
            entry_type=entry_type,
            cache=cache,
            fetcher=fetcher,
            current_modified_at=current_modified_at,
            freshness=freshness,
            project_gid=project_gid,
            ttl=ttl,
        )
        return entry_type, entry, hit

    # Run all loads concurrently
    tasks = [load_single(et) for et in entry_types]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, BaseException):
            # Log error but continue with other results
            # In production, this would use LogProvider
            continue
        # result is now guaranteed to be the tuple
        entry_type, entry, hit = result
        results[entry_type] = (entry, hit)

    return results


async def load_batch_entries(
    task_gids: list[str],
    entry_type: EntryType,
    cache: CacheProvider,
    batch_fetcher: Callable[[list[str]], Awaitable[dict[str, dict[str, Any]]]],
    current_versions: dict[str, str] | None = None,
    freshness: Freshness = Freshness.EVENTUAL,
    ttl: int | None = 300,
) -> dict[str, tuple[CacheEntry | None, bool]]:
    """Load cache entries for multiple tasks, using batch API for misses.

    Efficiently loads entries for many tasks by:
    1. Checking cache for all GIDs
    2. Identifying cache misses or stale entries
    3. Fetching all misses in a single batch API call
    4. Caching the fetched results

    Args:
        task_gids: List of task GIDs to load.
        entry_type: Type of entry to load (same type for all tasks).
        cache: Cache provider to use.
        batch_fetcher: Async function to fetch data for multiple tasks.
            Takes list of GIDs, returns dict mapping GID to data dict.
        current_versions: Dict mapping GID to current modified_at timestamp.
            Required for STRICT freshness mode.
        freshness: STRICT or EVENTUAL freshness mode.
        ttl: Time-to-live in seconds. Defaults to 300.

    Returns:
        Dict mapping GID to tuple of (CacheEntry or None, was_cache_hit).

    Example:
        >>> async def fetch_tasks(gids: list[str]) -> dict[str, dict]:
        ...     return {gid: {"gid": gid, "name": f"Task {gid}"} for gid in gids}
        >>> import asyncio
        >>> from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
        >>> cache = EnhancedInMemoryCacheProvider()
        >>> results = asyncio.run(load_batch_entries(
        ...     ["123", "456", "789"],
        ...     EntryType.TASK,
        ...     cache,
        ...     fetch_tasks,
        ... ))
        >>> len(results)
        3
    """
    if not task_gids:
        return {}

    results: dict[str, tuple[CacheEntry | None, bool]] = {}
    current_versions = current_versions or {}

    # Check cache for all GIDs
    cached_entries = cache.get_batch(task_gids, entry_type)

    # Determine which GIDs need fetching
    gids_to_fetch: list[str] = []

    for gid in task_gids:
        entry = cached_entries.get(gid)
        if entry is None:
            # Cache miss
            gids_to_fetch.append(gid)
        else:
            # Check staleness
            current = current_versions.get(gid)
            is_stale = check_entry_staleness(entry, current, freshness)
            if is_stale:
                gids_to_fetch.append(gid)
            else:
                # Cache hit
                results[gid] = (entry, True)

    # Fetch missing/stale entries
    if gids_to_fetch:
        fetched_data = await batch_fetcher(gids_to_fetch)

        # Create entries and store in cache
        entries_to_cache: dict[str, CacheEntry] = {}

        for gid in gids_to_fetch:
            data = fetched_data.get(gid)
            if not data:
                results[gid] = (None, False)
                continue

            # Extract version from data
            version_str = data.get("modified_at")
            if version_str:
                version = _parse_version(version_str)
            else:
                version = datetime.now(UTC)

            entry = CacheEntry(
                key=gid,
                data=data,
                entry_type=entry_type,
                version=version,
                cached_at=datetime.now(UTC),
                ttl=ttl,
            )

            entries_to_cache[gid] = entry
            results[gid] = (entry, False)

        # Batch cache the fetched entries
        if entries_to_cache:
            cache.set_batch(entries_to_cache)

    return results


def _parse_version(version_str: str) -> datetime:
    """Parse version string to datetime.

    Handles ISO format strings including Z suffix.

    Args:
        version_str: ISO format datetime string.

    Returns:
        Parsed datetime with UTC timezone.
    """
    # Handle Z suffix
    if version_str.endswith("Z"):
        version_str = version_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(version_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError:
        # Fallback to current time if parsing fails
        return datetime.now(UTC)
