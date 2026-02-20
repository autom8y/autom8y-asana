"""Incremental story loading with cache support.

Per ADR-0020, stories are loaded incrementally using the Asana 'since' parameter
to fetch only new stories since last fetch, reducing API calls and response sizes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.versioning import format_version, parse_version

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider


# Default story subtypes relevant for struc computation
# These track task state changes that affect dataframe rows
DEFAULT_STORY_TYPES = [
    "assignee_changed",
    "due_date_changed",
    "section_changed",
    "added_to_project",
    "removed_from_project",
    "marked_complete",
    "marked_incomplete",
    "enum_custom_field_changed",
    "number_custom_field_changed",
]


def read_cached_stories(
    task_gid: str,
    cache: CacheProvider,
) -> list[dict[str, Any]] | None:
    """Read stories from cache without any API call.

    Returns the cached story list if present and not expired,
    or None on cache miss. Does NOT modify the cache. Does NOT
    call the Asana API. This is a pure read-only operation.

    Per TDD-SECTION-TIMELINE-REMEDIATION: Gap 1 primitive. Enables
    derived timeline computations from existing cached data without
    warm-up infrastructure or network I/O.

    Args:
        task_gid: The task GID to read stories for.
        cache: Cache provider instance.

    Returns:
        List of story dicts if cached, None if cache miss or expired.
    """
    cached_entry = cache.get_versioned(task_gid, EntryType.STORIES)
    if cached_entry is None:
        return None
    return _extract_stories_list(cached_entry.data)


def read_stories_batch(
    task_gids: list[str],
    cache: CacheProvider,
    *,
    chunk_size: int = 500,
) -> dict[str, list[dict[str, Any]] | None]:
    """Read cached stories for multiple tasks in batched operations.

    Uses CacheProvider.get_batch() for efficient bulk reads.
    Chunks the request into groups of chunk_size to avoid
    oversized Redis MGET operations.

    Per TDD-SECTION-TIMELINE-REMEDIATION: Gap 4 primitive. Enables
    reading all ~3,800 story entries in chunked Redis pipeline batches
    for derived timeline computation.

    Args:
        task_gids: List of task GIDs to read stories for.
        cache: Cache provider instance.
        chunk_size: Maximum keys per batch operation (default 500).

    Returns:
        Dict mapping task_gid -> list of story dicts, or None for cache misses.
    """
    result: dict[str, list[dict[str, Any]] | None] = {}

    # Chunk to avoid oversized MGET (AMB-5 resolution)
    for i in range(0, len(task_gids), chunk_size):
        chunk = task_gids[i : i + chunk_size]
        batch_result = cache.get_batch(chunk, EntryType.STORIES)

        for gid, entry in batch_result.items():
            if entry is not None:
                result[gid] = _extract_stories_list(entry.data)
            else:
                result[gid] = None

    return result


async def load_stories_incremental(
    task_gid: str,
    cache: CacheProvider,
    fetcher: Callable[[str, str | None], Awaitable[list[dict[str, Any]]]],
    current_modified_at: str | None = None,
    max_cache_age_seconds: int | None = None,
) -> tuple[list[dict[str, Any]], CacheEntry | None, bool]:
    """Load stories with incremental fetching (since parameter).

    Per ADR-0020:
    - Get cached stories and their last_fetched timestamp
    - Fetch only stories since last_fetched (using Asana 'since' parameter)
    - Merge new stories with cached (dedupe by story GID)
    - Update cache with merged result

    When ``max_cache_age_seconds`` is set, the API call is skipped entirely
    if the cached entry is younger than the threshold.  This eliminates
    per-offer API round-trips on the request-time path when stories were
    recently warmed.

    Args:
        task_gid: The task GID.
        cache: Cache provider.
        fetcher: Async function(task_gid, since) -> list[story_dicts].
            since is ISO timestamp or None for full fetch.
        current_modified_at: Current task modified_at for cache versioning.
        max_cache_age_seconds: If set, return cached stories without an API
            call when the cache entry is fresher than this many seconds.
            ``None`` (default) preserves the existing always-fetch behavior.

    Returns:
        Tuple of (merged_stories, cache_entry, was_incremental_fetch).
        was_incremental_fetch is True if we fetched incrementally (had cache),
        False if we did a full fetch.
    """
    # Get existing cached stories
    cached_entry = cache.get_versioned(task_gid, EntryType.STORIES)

    if cached_entry is None:
        # No cache - full fetch
        stories = await fetcher(task_gid, None)
        entry = _create_stories_entry(task_gid, stories, current_modified_at)
        cache.set_versioned(task_gid, entry)
        return stories, entry, False

    # Get last fetched timestamp from cached entry metadata
    last_fetched = cached_entry.metadata.get("last_fetched")

    if last_fetched is None:
        # Corrupted cache (missing metadata) - full fetch
        stories = await fetcher(task_gid, None)
        entry = _create_stories_entry(task_gid, stories, current_modified_at)
        cache.set_versioned(task_gid, entry)
        return stories, entry, False

    # Short-circuit: if cache is fresh enough, skip the API call entirely.
    if max_cache_age_seconds is not None and cached_entry.cached_at is not None:
        cache_age = (datetime.now(UTC) - cached_entry.cached_at).total_seconds()
        if cache_age <= max_cache_age_seconds:
            cached_stories = _extract_stories_list(cached_entry.data)
            return cached_stories, cached_entry, True

    # Incremental fetch - get only stories since last_fetched
    new_stories = await fetcher(task_gid, last_fetched)

    # Merge with cached (dedupe by GID)
    # cached_entry.data is the cached stories list
    cached_stories = _extract_stories_list(cached_entry.data)
    merged = _merge_stories(cached_stories, new_stories)

    # Update cache
    entry = _create_stories_entry(task_gid, merged, current_modified_at)
    cache.set_versioned(task_gid, entry)

    return merged, entry, True


def _create_stories_entry(
    task_gid: str,
    stories: list[dict[str, Any]],
    version: str | None,
) -> CacheEntry:
    """Create a CacheEntry for stories with last_fetched metadata.

    Args:
        task_gid: The task GID used as cache key.
        stories: List of story dictionaries.
        version: The modified_at timestamp for versioning.

    Returns:
        CacheEntry containing the stories data.
    """
    now = datetime.now(UTC)
    version_dt = parse_version(version) if version else now

    return CacheEntry(
        key=task_gid,
        data={"stories": stories},
        entry_type=EntryType.STORIES,
        version=version_dt,
        cached_at=now,
        metadata={"last_fetched": format_version(now)},
    )


def _extract_stories_list(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract stories list from cache entry data.

    Handles the wrapper dict format used by CacheEntry.

    Args:
        data: Cache entry data dict.

    Returns:
        List of story dicts, empty list if not found.
    """
    if isinstance(data, dict):
        stories = data.get("stories")
        if isinstance(stories, list):
            return stories
    return []


def _merge_stories(
    existing: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge new stories into existing, deduping by GID.

    New stories take precedence (in case of updates).
    Result is sorted by created_at ascending.

    Args:
        existing: Existing cached stories.
        new: New stories fetched incrementally.

    Returns:
        Merged and sorted list of stories.
    """
    # Index existing by GID
    by_gid: dict[str, dict[str, Any]] = {}
    for s in existing:
        gid = s.get("gid")
        if gid is not None:
            by_gid[gid] = s

    # Overlay new stories (newer takes precedence)
    for story in new:
        gid = story.get("gid")
        if gid:
            by_gid[gid] = story

    # Sort by created_at (ascending)
    merged = list(by_gid.values())
    merged.sort(key=lambda s: s.get("created_at", ""))

    return merged


def filter_relevant_stories(
    stories: list[dict[str, Any]],
    include_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter stories to only include relevant types.

    Per ADR-0021, struc computation uses specific story subtypes that
    track task state changes (assignee_changed, due_date_changed, etc.).

    Args:
        stories: List of story dicts from Asana.
        include_types: Story resource_subtypes to include.
            If None, uses DEFAULT_STORY_TYPES for struc computation.

    Returns:
        Filtered list of stories matching the specified types.

    Example:
        >>> stories = [
        ...     {"gid": "1", "resource_subtype": "comment_added"},
        ...     {"gid": "2", "resource_subtype": "assignee_changed"},
        ... ]
        >>> filter_relevant_stories(stories)
        [{'gid': '2', 'resource_subtype': 'assignee_changed'}]
    """
    if include_types is None:
        include_types = DEFAULT_STORY_TYPES

    return [s for s in stories if s.get("resource_subtype") in include_types]


def get_latest_story_timestamp(stories: list[dict[str, Any]]) -> str | None:
    """Get the latest created_at timestamp from a list of stories.

    Useful for determining the 'since' parameter for the next fetch.

    Args:
        stories: List of story dicts.

    Returns:
        ISO timestamp of the latest story, or None if no stories.
    """
    if not stories:
        return None

    # Find the story with the latest created_at
    latest = max(
        (s for s in stories if s.get("created_at")),
        key=lambda s: s.get("created_at", ""),
        default=None,
    )

    return latest.get("created_at") if latest else None
