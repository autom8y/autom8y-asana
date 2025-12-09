"""Staleness detection helpers for cache entries.

This module provides utilities for determining whether cached data
is stale compared to the current version from the source (Asana API).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.cache.freshness import Freshness
from autom8_asana.cache.versioning import is_stale

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider


def check_entry_staleness(
    entry: CacheEntry,
    current_modified_at: str | None,
    freshness: Freshness = Freshness.EVENTUAL,
) -> bool:
    """Check if a cache entry is stale.

    Determines whether a cache entry should be refetched based on
    TTL expiration and version comparison (for STRICT freshness mode).

    Args:
        entry: The cache entry to check.
        current_modified_at: Current version from Asana (ISO timestamp).
            Required for STRICT freshness mode.
        freshness: STRICT (always verify version) or EVENTUAL (trust TTL).
            Defaults to EVENTUAL.

    Returns:
        True if entry is stale and should be refetched.
        False if entry is fresh and can be used.

    Example:
        >>> from autom8_asana.cache import CacheEntry, EntryType, Freshness
        >>> from datetime import datetime, timezone
        >>> entry = CacheEntry(
        ...     key="123",
        ...     data={},
        ...     entry_type=EntryType.TASK,
        ...     version=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     ttl=300,
        ... )
        >>> check_entry_staleness(entry, "2025-01-02T00:00:00Z", Freshness.STRICT)
        True
    """
    # If entry is TTL-expired, it's always stale
    if entry.is_expired():
        return True

    # For EVENTUAL freshness, TTL expiration is the only staleness check
    if freshness == Freshness.EVENTUAL:
        return False

    # For STRICT freshness, we must verify against current version
    if current_modified_at is None:
        # Cannot verify without current version - treat as stale for STRICT
        return True

    return is_stale(entry.version, current_modified_at)


def check_batch_staleness(
    cache: CacheProvider,
    task_gids: list[str],
    entry_type: EntryType,
    current_versions: dict[str, str],
    freshness: Freshness = Freshness.EVENTUAL,
) -> dict[str, bool]:
    """Check staleness for multiple tasks.

    Efficiently checks staleness for a batch of tasks, retrieving
    entries from cache and comparing versions.

    Args:
        cache: Cache provider to retrieve entries from.
        task_gids: List of task GIDs to check.
        entry_type: Type of entry to check (TASK, SUBTASKS, etc.).
        current_versions: Dict mapping GID to current modified_at timestamp.
        freshness: STRICT or EVENTUAL freshness mode. Defaults to EVENTUAL.

    Returns:
        Dict mapping GID to is_stale boolean.
        True means the entry is stale or missing.
        False means the entry is fresh.

    Example:
        >>> from autom8_asana.cache.backends.memory import EnhancedInMemoryCacheProvider
        >>> cache = EnhancedInMemoryCacheProvider()
        >>> # After populating cache...
        >>> staleness = check_batch_staleness(
        ...     cache,
        ...     ["123", "456"],
        ...     EntryType.TASK,
        ...     {"123": "2025-01-01T00:00:00Z", "456": "2025-01-01T00:00:00Z"},
        ... )
        >>> staleness
        {'123': True, '456': True}  # Both stale because not cached
    """
    results: dict[str, bool] = {}

    # Get all entries from cache in batch
    entries = cache.get_batch(task_gids, entry_type)

    for gid in task_gids:
        entry = entries.get(gid)
        if entry is None:
            # Not in cache = needs fetch (treated as stale)
            results[gid] = True
        else:
            current = current_versions.get(gid)
            results[gid] = check_entry_staleness(entry, current, freshness)

    return results


def partition_by_staleness(
    staleness: dict[str, bool],
) -> tuple[list[str], list[str]]:
    """Partition GIDs into stale and current lists.

    Utility function to split staleness results into two lists
    for easy processing of stale entries vs current entries.

    Args:
        staleness: Dict mapping GID to is_stale boolean.

    Returns:
        Tuple of (stale_gids, current_gids).

    Example:
        >>> staleness = {"123": True, "456": False, "789": True}
        >>> stale, current = partition_by_staleness(staleness)
        >>> stale
        ['123', '789']
        >>> current
        ['456']
    """
    stale = [gid for gid, is_stale_flag in staleness.items() if is_stale_flag]
    current = [gid for gid, is_stale_flag in staleness.items() if not is_stale_flag]
    return stale, current
