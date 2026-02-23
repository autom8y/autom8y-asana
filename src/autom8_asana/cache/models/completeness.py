"""Cache completeness tracking for partial vs full task data.

Per TDD-CACHE-COMPLETENESS-001: Tracks which fields were requested when
caching tasks, enabling detection of partial cache entries and automatic
upgrade when more fields are needed.

Problem
-------
ParallelSectionFetcher._fetch_section_gids() caches tasks with only ["gid"],
but DataFrameViewPlugin and CascadeViewPlugin need custom_fields, parent, etc.
The old code couldn't distinguish partial from complete entries, causing
silent failures where cf:FieldName returned None despite data being available.

Solution: Tiered Completeness Model
-----------------------------------
Cache entries are tagged with a CompletenessLevel in their metadata. Consumers
declare their required level, and the cache returns None (or triggers upgrade)
for insufficient entries.

Completeness Levels
-------------------
- UNKNOWN (0): Legacy entries without tracking. Treated conservatively.
- MINIMAL (10): GID only. Used for enumeration (listing task GIDs in a section).
- STANDARD (20): GID + core fields (name, custom_fields, parent, memberships).
  Used for DataFrame extraction and cascade resolution.
- FULL (30): All available fields including notes, assignee, projects, tags.
  Used when complete task details are needed.

When to Use Each Level
----------------------
MINIMAL:
    - Listing task GIDs in a section/project
    - Building task inventories without data extraction
    - ParallelSectionFetcher._fetch_section_gids()

STANDARD (recommended default):
    - DataFrame extraction (cf: and cascade: prefixes)
    - Custom field value resolution
    - Parent chain traversal for cascading fields
    - ProgressiveProjectBuilder.build_progressive_async()

FULL:
    - Complete task details for display
    - Operations requiring notes, assignee, or project memberships
    - Task export or backup operations

Upgrade Mechanism
-----------------
When a cached entry has insufficient completeness:

1. get_async() returns None and increments completeness_misses stat
2. Caller can use get_with_upgrade_async() for transparent upgrade
3. upgrade_async() fetches task with expanded opt_fields
4. New entry replaces old with higher completeness level

Observability
-------------
Stats tracked (via UnifiedTaskStore.get_stats()):
    - completeness_misses: Count of cache lookups where entry was found
      but had insufficient completeness level
    - upgrade_count: Count of successful cache entry upgrades

Structured log events:
    - cache_completeness_insufficient: Entry found but level too low
      (extra: gid, cached_level, required_level)
    - cache_entry_upgraded: Entry successfully upgraded
      (extra: gid, target_level)
    - cache_upgrade_failed: Upgrade failed
      (extra: gid, target_level, error)

Example
-------
>>> from autom8_asana.cache import (
...     UnifiedTaskStore, CompletenessLevel, FreshnessIntent
... )
>>> # Get task requiring STANDARD fields
>>> task = await store.get_async(
...     "task-gid",
...     required_level=CompletenessLevel.STANDARD
... )
>>> # Or with automatic upgrade
>>> task = await store.get_with_upgrade_async(
...     "task-gid",
...     required_level=CompletenessLevel.STANDARD,
...     tasks_client=client
... )

ADRs
----
- ADR-COMPLETENESS-001: Tiered vs Field-Level Tracking (chose tiered)
- ADR-COMPLETENESS-002: Fetch-on-Miss Upgrade Strategy (chose fetch-on-miss)
- ADR-COMPLETENESS-003: No auto: Prefix (schema authors choose prefix)

See Also
--------
- TDD-CACHE-COMPLETENESS-001: Full design specification
- TDD-UNIFIED-CACHE-001: Unified cache architecture
- TDD-CASCADING-FIELD-RESOLUTION-001: Cascade prefix design
"""

from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.cache.models.entry import CacheEntry


class CompletenessLevel(IntEnum):
    """Cache entry completeness levels.

    Higher levels include all fields from lower levels.
    Use IntEnum so levels can be compared: FULL > STANDARD > MINIMAL.

    Example:
        >>> if cached_level < required_level:
        ...     # Need to re-fetch with more fields
    """

    UNKNOWN = 0  # Legacy entries without tracking
    MINIMAL = 10  # gid only (enumeration)
    STANDARD = 20  # gid + core fields (name, custom_fields, parent)
    FULL = 30  # All available fields


# Fields included at each completeness level
# These sets are cumulative: STANDARD includes MINIMAL, FULL includes all
MINIMAL_FIELDS: frozenset[str] = frozenset(["gid"])

STANDARD_FIELDS: frozenset[str] = frozenset(
    [
        "gid",
        "name",
        "resource_subtype",
        "parent",
        "parent.gid",
        "parent.name",
        "custom_fields",
        "custom_fields.gid",
        "custom_fields.name",
        "custom_fields.resource_subtype",
        "custom_fields.display_value",
        "custom_fields.text_value",
        "custom_fields.number_value",
        "custom_fields.enum_value",
        "custom_fields.enum_value.gid",
        "custom_fields.enum_value.name",
        "custom_fields.multi_enum_values",
        "custom_fields.multi_enum_values.gid",
        "custom_fields.multi_enum_values.name",
        "memberships",
        "memberships.section",
        "memberships.section.gid",
        "memberships.section.name",
        "modified_at",
        "completed",
        "completed_at",
    ]
)

FULL_FIELDS: frozenset[str] = frozenset(
    [
        *STANDARD_FIELDS,
        "created_at",
        "due_on",
        "due_at",
        "start_on",
        "start_at",
        "notes",
        "html_notes",
        "assignee",
        "assignee.gid",
        "assignee.name",
        "projects",
        "projects.gid",
        "projects.name",
        "tags",
        "tags.gid",
        "tags.name",
        "followers",
        "permalink_url",
        "workspace",
        "approval_status",
        "resource_type",
    ]
)


def infer_completeness_level(opt_fields: list[str] | None) -> CompletenessLevel:
    """Infer completeness level from opt_fields list.

    Args:
        opt_fields: List of fields requested from Asana API.

    Returns:
        Inferred completeness level based on fields present.

    Example:
        >>> infer_completeness_level(["gid"])
        CompletenessLevel.MINIMAL
        >>> infer_completeness_level(["gid", "name", "custom_fields"])
        CompletenessLevel.STANDARD
    """
    if opt_fields is None:
        return CompletenessLevel.UNKNOWN

    fields_set = frozenset(opt_fields)

    # Check if it's just GID (enumeration case)
    if fields_set == MINIMAL_FIELDS or fields_set == frozenset(["gid"]):
        return CompletenessLevel.MINIMAL

    # Check if it has the core standard fields
    has_custom_fields = any(f.startswith("custom_fields") for f in fields_set)
    has_parent = "parent" in fields_set or "parent.gid" in fields_set

    if has_custom_fields and has_parent:
        # Check if it has full fields
        if fields_set >= FULL_FIELDS:
            return CompletenessLevel.FULL
        return CompletenessLevel.STANDARD

    # Has more than gid but not standard fields
    if len(fields_set) > 1:
        return CompletenessLevel.STANDARD

    return CompletenessLevel.MINIMAL


def get_entry_completeness(entry: CacheEntry) -> CompletenessLevel:
    """Get completeness level from cache entry metadata.

    Args:
        entry: Cache entry to check.

    Returns:
        Completeness level from metadata, or UNKNOWN for legacy entries.
    """
    if not entry.metadata:
        return CompletenessLevel.UNKNOWN

    level_value = entry.metadata.get("completeness_level")
    if level_value is None:
        return CompletenessLevel.UNKNOWN

    try:
        return CompletenessLevel(level_value)
    except ValueError:
        return CompletenessLevel.UNKNOWN


def is_entry_sufficient(
    entry: CacheEntry,
    required_level: CompletenessLevel,
) -> bool:
    """Check if cache entry has sufficient completeness.

    Args:
        entry: Cache entry to check.
        required_level: Minimum required completeness level.

    Returns:
        True if entry is sufficient, False if re-fetch needed.

    Example:
        >>> if not is_entry_sufficient(entry, CompletenessLevel.STANDARD):
        ...     # Re-fetch with standard fields
    """
    entry_level = get_entry_completeness(entry)

    # UNKNOWN entries from legacy code need re-fetch for STANDARD/FULL
    if entry_level == CompletenessLevel.UNKNOWN:
        # Be conservative - only accept if requiring MINIMAL or UNKNOWN
        return required_level <= CompletenessLevel.MINIMAL

    return entry_level >= required_level


def create_completeness_metadata(
    opt_fields: list[str] | None,
    *,
    explicit_level: CompletenessLevel | None = None,
) -> dict[str, Any]:
    """Create metadata dict with completeness tracking.

    Args:
        opt_fields: Fields that were requested.
        explicit_level: Override inferred level (optional).

    Returns:
        Metadata dict suitable for CacheEntry.metadata.

    Example:
        >>> metadata = create_completeness_metadata(["gid", "name", "custom_fields"])
        >>> entry = CacheEntry(..., metadata=metadata)
    """
    level = explicit_level or infer_completeness_level(opt_fields)

    return {
        "completeness_level": level.value,
        "opt_fields_used": opt_fields or [],
    }


def get_fields_for_level(level: CompletenessLevel) -> list[str]:
    """Get the opt_fields list for a completeness level.

    Args:
        level: Desired completeness level.

    Returns:
        List of opt_fields to request from Asana API.

    Example:
        >>> fields = get_fields_for_level(CompletenessLevel.STANDARD)
        >>> tasks = await client.tasks.list_async(opt_fields=fields)
    """
    match level:
        case CompletenessLevel.MINIMAL:
            return list(MINIMAL_FIELDS)
        case CompletenessLevel.STANDARD:
            return list(STANDARD_FIELDS)
        case CompletenessLevel.FULL:
            return list(FULL_FIELDS)
        case _:
            return list(MINIMAL_FIELDS)
