# TDD: Cache Entry Completeness Tracking

**TDD ID**: TDD-CACHE-COMPLETENESS-001
**Version**: 1.0
**Date**: 2026-01-02
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: N/A (Technical initiative from exploratory debugging)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Current State Analysis](#current-state-analysis)
4. [Goals and Non-Goals](#goals-and-non-goals)
5. [Design Decision: Tiers vs Field-Level Tracking](#design-decision-tiers-vs-field-level-tracking)
6. [Proposed Architecture](#proposed-architecture)
7. [Component Designs](#component-designs)
8. [Integration Points](#integration-points)
9. [Cache Upgrade Strategy](#cache-upgrade-strategy)
10. [Auto-Prefix Resolution](#auto-prefix-resolution)
11. [Implementation Phases](#implementation-phases)
12. [Test Scenarios](#test-scenarios)
13. [Risk Assessment](#risk-assessment)
14. [ADRs](#adrs)
15. [Success Criteria](#success-criteria)

---

## Overview

This TDD defines the completeness tracking system for cache entries in the autom8_asana SDK. The design addresses a critical bug where `ParallelSectionFetcher._fetch_section_gids()` caches tasks with only `["gid"]` fields, but downstream consumers (DataFrameViewPlugin, CascadeViewPlugin) require `custom_fields`, `parent`, and other fields for extraction.

### Solution Summary

**Tiered Completeness Model**: Cache entries are tagged with a `CompletenessLevel` (MINIMAL, STANDARD, FULL) in their metadata. Consumers declare their required level, and the cache coordinator transparently upgrades entries that are insufficient by re-fetching with expanded opt_fields.

**Key Insight**: The problem is not that data is cached incorrectly, but that consumers cannot distinguish "I have GID-only data" from "I have complete data". Adding completeness metadata solves this without changing how data is fetched or stored.

---

## Problem Statement

### Observed Behavior

During DataFrame extraction for Unit tasks:
- `source="cf:Vertical"` returns 0 matches (extraction fails silently)
- `source="cascade:Office Phone"` returns 2280 matches (works correctly)

### Root Causes

**Root Cause 1: `cf:` prefix scope limitation**

`DefaultCustomFieldResolver.get_value()` only checks the current task's `custom_fields` array. If the task was cached via `_fetch_section_gids()` with `opt_fields=["gid"]`, the `custom_fields` array is missing entirely. The resolver returns `None` (field not found).

```python
# DefaultCustomFieldResolver.get_value()
for cf_data in task.custom_fields or []:  # custom_fields is None or []
    cf_gid = cf_data.get("gid")
    if cf_gid == gid:
        return self._extract_raw_value(cf_data)  # Never reached
return None  # Always returns None
```

**Root Cause 2: GID enumeration caching with minimal fields**

`ParallelSectionFetcher._fetch_section_gids()` caches tasks with only `["gid"]`:

```python
# parallel_fetch.py line 545-549
async def _fetch_section_gids(self, section_gid, semaphore):
    async with semaphore:
        tasks = await self.tasks_client.list_async(
            section=section_gid,
            opt_fields=["gid"],  # MINIMAL - no custom_fields, parent, etc.
        ).collect()
        return [task.gid for task in tasks if task.gid]
```

When `UnifiedTaskStore.get_async()` later retrieves these entries for cascade resolution, it returns incomplete data without warning.

**Root Cause 3: No cache entry completeness tracking**

`CacheEntry` has no mechanism to record which fields were present when cached. Consumers cannot distinguish:
- Entry cached with `["gid"]` (MINIMAL)
- Entry cached with `["gid", "name", "custom_fields", "parent"]` (STANDARD)
- Entry cached with all available fields (FULL)

### Impact

| Scenario | Expected | Actual |
|----------|----------|--------|
| `cf:Vertical` on Unit task | Vertical value from custom_fields | `None` (custom_fields missing) |
| `cascade:Vertical` on Unit task | Vertical from ancestor | Works (fetches parent with full fields) |
| Batch extraction of 2000+ Units | All fields populated | `cf:` fields fail, `cascade:` works |

---

## Current State Analysis

### Existing Completeness Module

A `completeness.py` module has been started at `/src/autom8_asana/cache/completeness.py`:

```python
class CompletenessLevel(IntEnum):
    UNKNOWN = 0   # Legacy entries without tracking
    MINIMAL = 10  # gid only (enumeration)
    STANDARD = 20 # gid + core fields (name, custom_fields, parent)
    FULL = 30     # All available fields
```

**Field Sets Defined**:
- `MINIMAL_FIELDS`: `frozenset(["gid"])`
- `STANDARD_FIELDS`: 27 fields including custom_fields.*, parent.*, memberships.*
- `FULL_FIELDS`: 37+ fields including notes, assignee, projects, tags

**Helper Functions Implemented**:
- `infer_completeness_level(opt_fields)` - Infers tier from opt_fields list
- `get_entry_completeness(entry)` - Reads tier from CacheEntry.metadata
- `is_entry_sufficient(entry, required_level)` - Checks if entry meets requirements
- `create_completeness_metadata(opt_fields)` - Creates metadata dict for caching
- `get_fields_for_level(level)` - Returns opt_fields list for a tier

**Status**: Module is complete but NOT INTEGRATED with cache coordinators.

### Cache Entry Model

`CacheEntry` (in `cache/entry.py`) already supports metadata:

```python
@dataclass(frozen=True)
class CacheEntry:
    key: str
    data: dict[str, Any]
    entry_type: EntryType
    version: datetime
    cached_at: datetime
    ttl: int | None = 300
    project_gid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # <-- Use this
```

**Decision**: Store completeness in `CacheEntry.metadata["completeness_level"]` (already designed in completeness.py).

### Current Cache Population Points

| Component | Method | opt_fields | Current Tier |
|-----------|--------|------------|--------------|
| `ParallelSectionFetcher` | `_fetch_section_gids()` | `["gid"]` | MINIMAL |
| `ParallelSectionFetcher` | `_fetch_section()` | Configurable | STANDARD/FULL |
| `UnifiedTaskStore` | `put_async()` | From caller | UNKNOWN |
| `ProjectDataFrameBuilder` | `build_with_parallel_fetch_async()` | STANDARD_FIELDS | STANDARD |

---

## Goals and Non-Goals

### Goals

| ID | Goal | Success Metric |
|----|------|----------------|
| G1 | Track completeness level for all cached tasks | 100% of new entries have `completeness_level` in metadata |
| G2 | Automatic upgrade when consumer requires more fields | Cache miss triggers re-fetch with expanded opt_fields |
| G3 | `cf:` prefix works correctly after cache upgrade | 100% parity with `cascade:` prefix success rate |
| G4 | Backward compatibility with legacy entries | UNKNOWN entries treated conservatively |
| G5 | No API call increase for sufficient entries | API calls only for genuinely insufficient data |

### Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Field-level tracking | Complexity vs benefit tradeoff (see ADR-COMPLETENESS-001) |
| NG2 | Automatic proactive upgrade | Fetch-on-miss is simpler and respects usage patterns |
| NG3 | `auto:` prefix implementation | `cascade:` is sufficient; `cf:` works after upgrade |
| NG4 | Schema migration for existing cached data | TTL expiry handles legacy entries naturally |

---

## Design Decision: Tiers vs Field-Level Tracking

### Option A: Tiered Completeness (SELECTED)

Track 3-4 predefined tiers with known field sets.

**Pros**:
- Simple to implement (just store an integer)
- Fast comparison (integer inequality)
- Predictable upgrade paths
- Aligns with common use patterns (enumeration vs extraction)

**Cons**:
- Coarse-grained (may fetch more than strictly needed)
- Adding new tiers requires code changes

### Option B: Field-Level Tracking

Store exact set of fields present in each entry.

**Pros**:
- Precise (fetch only what's missing)
- No predefined tiers to maintain

**Cons**:
- Larger metadata overhead (set of field names per entry)
- Complex comparison logic (set intersection)
- Must track nested fields (custom_fields.name vs custom_fields)
- Diminishing returns (most queries want STANDARD or FULL)

### Decision: Tier-Based Tracking

Per ADR-COMPLETENESS-001, we select tiered completeness for simplicity and performance. The three tiers (MINIMAL, STANDARD, FULL) cover 95%+ of use cases with minimal overhead.

---

## Proposed Architecture

### Component Diagram

```
                                  ┌─────────────────────────────┐
                                  │    DataFrame Extractors     │
                                  │  (UnitExtractor, etc.)      │
                                  └──────────────┬──────────────┘
                                                 │
                      ┌──────────────────────────┼──────────────────────────┐
                      │                          │                          │
                      ▼                          ▼                          ▼
         ┌────────────────────┐    ┌─────────────────────────┐  ┌────────────────────┐
         │  DefaultResolver   │    │  CascadingFieldResolver │  │  CascadeViewPlugin │
         │  (cf: prefix)      │    │  (cascade: prefix)      │  │  (unified cache)   │
         └────────┬───────────┘    └───────────┬─────────────┘  └──────────┬─────────┘
                  │                            │                           │
                  └────────────────────────────┼───────────────────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────────────┐
                              │         UnifiedTaskStore           │
                              │  (with Completeness Awareness)     │
                              ├─────────────────────────────────────┤
                              │  get_async(gid, required_level)    │
                              │  get_batch_async(gids, level)      │
                              │  put_async(task, opt_fields)       │
                              │  upgrade_if_needed(gid, level)     │
                              └─────────────────────────────────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          │                    │                    │
                          ▼                    ▼                    ▼
                 ┌─────────────┐      ┌──────────────┐     ┌──────────────┐
                 │ HierarchyIdx│      │  CacheEntry  │     │Completeness  │
                 │ (parent map)│      │  (metadata)  │     │  Module      │
                 └─────────────┘      └──────────────┘     └──────────────┘
```

### Data Flow: Cache Miss with Upgrade

```
1. DataFrameExtractor.extract_async(task)
   │
2. CascadeViewPlugin.resolve_async(task, "Office Phone")
   │
3. UnifiedTaskStore.get_parent_chain_async(task.gid)
   │
4. UnifiedTaskStore.get_batch_async([parent_gid], required_level=STANDARD)
   │
5. Cache lookup returns entry with completeness_level=MINIMAL
   │
6. is_entry_sufficient(entry, STANDARD) → False
   │
7. UnifiedTaskStore.upgrade_async(parent_gid, STANDARD)
   │  - Fetches via API with STANDARD_FIELDS opt_fields
   │  - Stores new entry with completeness_level=STANDARD
   │
8. Return upgraded parent data
   │
9. CascadeViewPlugin extracts "Office Phone" from custom_fields
   │
10. Field value returned to extractor
```

---

## Component Designs

### 7.1 UnifiedTaskStore Enhancements

```python
# Enhanced signatures in unified.py

async def get_async(
    self,
    gid: str,
    freshness: FreshnessMode | None = None,
    required_level: CompletenessLevel = CompletenessLevel.STANDARD,  # NEW
) -> dict[str, Any] | None:
    """Get single task, respecting freshness and completeness.

    If cached entry exists but is insufficient for required_level,
    returns None (caller should upgrade or re-fetch).

    Args:
        gid: Task GID to retrieve.
        freshness: Override default freshness mode.
        required_level: Minimum completeness required.

    Returns:
        Task dict if found, fresh, AND sufficient; None otherwise.
    """

async def get_with_upgrade_async(
    self,
    gid: str,
    required_level: CompletenessLevel = CompletenessLevel.STANDARD,
    freshness: FreshnessMode | None = None,
) -> dict[str, Any] | None:
    """Get task with automatic upgrade if insufficient.

    If cached entry is insufficient, fetches fresh with expanded fields.

    Args:
        gid: Task GID to retrieve.
        required_level: Minimum completeness required.
        freshness: Override default freshness mode.

    Returns:
        Task dict at required completeness, or None if fetch failed.
    """

async def put_async(
    self,
    task: dict[str, Any],
    ttl: int | None = None,
    opt_fields: list[str] | None = None,  # NEW - for completeness inference
) -> None:
    """Store task in cache with completeness tracking.

    Args:
        task: Task dict with at least "gid" key.
        ttl: Optional TTL override.
        opt_fields: Fields used in fetch (for completeness inference).
    """
```

### 7.2 Completeness-Aware Cache Entry Creation

```python
# In UnifiedTaskStore.put_async() or put_batch_async()

from autom8_asana.cache.completeness import (
    CompletenessLevel,
    create_completeness_metadata,
    infer_completeness_level,
)

async def put_async(
    self,
    task: dict[str, Any],
    ttl: int | None = None,
    opt_fields: list[str] | None = None,
) -> None:
    gid = task.get("gid")
    if not gid:
        raise ValueError("Task must have 'gid' field")

    modified_at = task.get("modified_at")
    version = self._parse_version(modified_at)

    # NEW: Include completeness in metadata
    base_metadata = self._extract_metadata(task)
    completeness_metadata = create_completeness_metadata(opt_fields)

    entry = CacheEntry(
        key=gid,
        data=task,
        entry_type=EntryType.TASK,
        version=version,
        cached_at=datetime.now(timezone.utc),
        ttl=ttl,
        metadata={**base_metadata, **completeness_metadata},  # Merged
    )

    self.cache.set_versioned(gid, entry)
    self._hierarchy.register(task)
```

### 7.3 Completeness Check in get_async

```python
from autom8_asana.cache.completeness import (
    CompletenessLevel,
    is_entry_sufficient,
)

async def get_async(
    self,
    gid: str,
    freshness: FreshnessMode | None = None,
    required_level: CompletenessLevel = CompletenessLevel.STANDARD,
) -> dict[str, Any] | None:
    mode = freshness or self.freshness_mode
    entry = self.cache.get_versioned(gid, EntryType.TASK)

    if entry is None:
        self._stats["get_misses"] += 1
        return None

    # NEW: Check completeness
    if not is_entry_sufficient(entry, required_level):
        self._stats["get_misses"] += 1
        self._stats["completeness_misses"] += 1
        logger.debug(
            "cache_completeness_insufficient",
            extra={
                "gid": gid,
                "cached_level": get_entry_completeness(entry).name,
                "required_level": required_level.name,
            },
        )
        return None

    # Existing freshness checks...
    if mode == FreshnessMode.IMMEDIATE:
        self._stats["get_hits"] += 1
        return entry.data

    # ... rest of freshness validation
```

### 7.4 Upgrade Method

```python
async def upgrade_async(
    self,
    gid: str,
    target_level: CompletenessLevel,
    batch_client: BatchClient | None = None,
) -> dict[str, Any] | None:
    """Upgrade cache entry to target completeness level.

    Fetches task from API with expanded opt_fields corresponding
    to target_level, then updates cache.

    Args:
        gid: Task GID to upgrade.
        target_level: Desired completeness level.
        batch_client: Optional BatchClient for fetch.

    Returns:
        Upgraded task data, or None if fetch failed.
    """
    from autom8_asana.cache.completeness import get_fields_for_level

    opt_fields = get_fields_for_level(target_level)

    # Fetch via client
    try:
        # This would use the batch_client or tasks_client
        # Implementation depends on how UnifiedTaskStore accesses API
        task = await self._fetch_task_async(gid, opt_fields)
        if task is None:
            return None

        # Store with new completeness
        await self.put_async(task, opt_fields=opt_fields)

        self._stats["upgrade_count"] += 1
        logger.info(
            "cache_entry_upgraded",
            extra={
                "gid": gid,
                "target_level": target_level.name,
            },
        )
        return task.model_dump() if hasattr(task, "model_dump") else task

    except Exception as e:
        logger.warning(
            "cache_upgrade_failed",
            extra={
                "gid": gid,
                "target_level": target_level.name,
                "error": str(e),
            },
        )
        return None
```

---

## Integration Points

### 8.1 ParallelSectionFetcher Integration

When `_fetch_section_gids()` stores entries, it must tag them as MINIMAL:

```python
# parallel_fetch.py - _fetch_section_gids

async def _fetch_section_gids(self, section_gid, semaphore):
    async with semaphore:
        self._api_call_count += 1
        tasks = await self.tasks_client.list_async(
            section=section_gid,
            opt_fields=["gid"],
        ).collect()

        # NEW: If using unified store, tag completeness
        if self._unified_store:
            for task in tasks:
                await self._unified_store.put_async(
                    {"gid": task.gid},
                    opt_fields=["gid"],  # Explicit for MINIMAL inference
                )

        return [task.gid for task in tasks if task.gid]
```

**Alternative**: Don't cache from `_fetch_section_gids()` at all - it's just enumeration.

### 8.2 ProjectDataFrameBuilder Integration

When building DataFrames, request STANDARD level:

```python
# In build_with_parallel_fetch_async()

# Phase 2: Get cached tasks with STANDARD completeness required
cached_result = await self._cache_coordinator.get_batch_async(
    task_gids,
    required_level=CompletenessLevel.STANDARD,  # NEW
)

# Entries with insufficient completeness are returned as None
# They'll be included in the "miss" list for re-fetch
```

### 8.3 CascadeViewPlugin Integration

When resolving cascading fields, require STANDARD for parent chain:

```python
# cascade_view.py - _traverse_parent_chain

async def _traverse_parent_chain(self, task, field_def, owner_class, max_depth):
    # Get parent chain with STANDARD completeness
    parent_chain = await self._store.get_parent_chain_async(
        task.gid,
        max_depth=max_depth,
        required_level=CompletenessLevel.STANDARD,  # NEW
    )
```

Or use `get_with_upgrade_async()` for transparent upgrade:

```python
parent_chain = await self._store.get_parent_chain_with_upgrade_async(
    task.gid,
    max_depth=max_depth,
    required_level=CompletenessLevel.STANDARD,
)
```

---

## Cache Upgrade Strategy

### 9.1 Upgrade Path Options

| Strategy | Description | Pros | Cons |
|----------|-------------|------|------|
| **Fetch-on-Miss** | Re-fetch when insufficient | Simple, respects usage patterns | Latency on first access |
| **Proactive Upgrade** | Upgrade entries when detected | Lower latency | Wasted API calls for unused entries |
| **Batch Upgrade** | Collect insufficient, upgrade in batch | Efficient for bulk operations | Complexity |

### Decision: Fetch-on-Miss with Batch Support

**Primary**: Use fetch-on-miss - when `get_async()` detects insufficient completeness, it returns `None` and caller handles re-fetch.

**Enhancement**: Provide `get_batch_with_upgrade_async()` for batch operations that need transparent upgrade:

```python
async def get_batch_with_upgrade_async(
    self,
    gids: list[str],
    required_level: CompletenessLevel = CompletenessLevel.STANDARD,
) -> dict[str, dict[str, Any] | None]:
    """Get batch with automatic upgrade for insufficient entries.

    1. Check cache for all GIDs
    2. Partition into sufficient/insufficient
    3. Batch fetch insufficient via API
    4. Update cache with fetched entries
    5. Return combined results
    """
```

### 9.2 Legacy Entry Handling

Entries without `completeness_level` in metadata are treated as `UNKNOWN`:

```python
def get_entry_completeness(entry: CacheEntry) -> CompletenessLevel:
    if not entry.metadata:
        return CompletenessLevel.UNKNOWN

    level_value = entry.metadata.get("completeness_level")
    if level_value is None:
        return CompletenessLevel.UNKNOWN

    try:
        return CompletenessLevel(level_value)
    except ValueError:
        return CompletenessLevel.UNKNOWN
```

For `UNKNOWN` entries, `is_entry_sufficient()` is conservative:

```python
def is_entry_sufficient(entry, required_level):
    entry_level = get_entry_completeness(entry)

    if entry_level == CompletenessLevel.UNKNOWN:
        # Conservative: only accept for MINIMAL requirements
        return required_level <= CompletenessLevel.MINIMAL

    return entry_level >= required_level
```

This ensures legacy entries naturally expire and are replaced with completeness-tracked entries.

---

## Auto-Prefix Resolution

### 10.1 Design Question: Is `auto:` Prefix Needed?

**Context**: User asked whether an `auto:` prefix should auto-infer `cf:` vs `cascade:`.

**Analysis**:

| Prefix | Behavior | When to Use |
|--------|----------|-------------|
| `cf:` | Resolve on current task only | Field always exists on this task type |
| `cascade:` | Traverse parent chain | Field inherited from ancestor |
| `auto:` (proposed) | Try cf: first, then cascade: | Unknown inheritance pattern |

**Arguments Against `auto:`**:

1. **Semantic Ambiguity**: The schema author should know whether a field is local or inherited. Auto-inference hides this.

2. **Performance**: `auto:` would require trying `cf:` first, then falling back to `cascade:`. This doubles work for cascade fields.

3. **Cache Completeness Solves the Real Problem**: The bug (cf:Vertical returning 0) is not about prefix choice, but about incomplete cache entries. With completeness tracking:
   - `cf:Vertical` on a task with STANDARD completeness works correctly
   - `cascade:Vertical` already works (fetches with full fields)

4. **Registry Already Knows**: `CASCADING_FIELD_REGISTRY` defines which fields cascade. If we wanted auto-inference, we'd consult the registry, which effectively duplicates `cascade:` behavior.

### 10.2 Decision: No `auto:` Prefix

**Rationale**: The real fix is completeness tracking, not prefix inference.

After completeness tracking is integrated:
- `cf:Vertical` works when the cached entry has STANDARD completeness
- `cascade:Vertical` works by traversing (with automatic upgrade if needed)

The schema author explicitly chooses the appropriate prefix based on domain knowledge.

**Future Consideration**: If a use case emerges where the caller genuinely doesn't know whether a field is local or inherited, we can revisit. For now, YAGNI.

---

## Implementation Phases

### Phase 1: Core Integration (1-2 days)

**Tasks**:
1. Add `completeness_level` to all `put_async()` calls in UnifiedTaskStore
2. Add `required_level` parameter to `get_async()` and `get_batch_async()`
3. Implement `is_entry_sufficient()` checks in get methods
4. Add `completeness_misses` to stats

**Validation**:
- Unit test: Entry with MINIMAL fails STANDARD requirement
- Unit test: Entry with STANDARD passes STANDARD requirement
- Unit test: UNKNOWN entries treated conservatively

### Phase 2: Upgrade Mechanism (1 day)

**Tasks**:
1. Implement `upgrade_async()` in UnifiedTaskStore
2. Implement `get_with_upgrade_async()` for single entries
3. Implement `get_batch_with_upgrade_async()` for batch operations
4. Wire `upgrade_async()` to tasks client

**Validation**:
- Integration test: MINIMAL entry upgraded to STANDARD on demand
- Integration test: Batch upgrade for 10+ entries

### Phase 3: Consumer Integration (1 day)

**Tasks**:
1. Update `CascadeViewPlugin` to request STANDARD completeness
2. Update `ProjectDataFrameBuilder` to request STANDARD completeness
3. Update `ParallelSectionFetcher._fetch_section` to tag entries

**Validation**:
- End-to-end test: `cf:Vertical` extraction succeeds after cache upgrade
- Performance test: No API increase for warm cache with STANDARD entries

### Phase 4: Observability (0.5 days)

**Tasks**:
1. Add `completeness_misses` and `upgrade_count` to stats
2. Add structured logging for completeness decisions
3. Document completeness levels in cache README

**Validation**:
- Stats correctly reflect completeness-related cache behavior
- Logs traceable for debugging

---

## Test Scenarios

### 12.1 Unit Tests

| ID | Scenario | Input | Expected Output |
|----|----------|-------|-----------------|
| TC-001 | MINIMAL entry, STANDARD required | Entry with level=10, required=20 | `is_entry_sufficient()` returns False |
| TC-002 | STANDARD entry, STANDARD required | Entry with level=20, required=20 | `is_entry_sufficient()` returns True |
| TC-003 | FULL entry, STANDARD required | Entry with level=30, required=20 | `is_entry_sufficient()` returns True |
| TC-004 | UNKNOWN entry, MINIMAL required | Entry without metadata, required=10 | `is_entry_sufficient()` returns True |
| TC-005 | UNKNOWN entry, STANDARD required | Entry without metadata, required=20 | `is_entry_sufficient()` returns False |
| TC-006 | Infer from ["gid"] | opt_fields=["gid"] | MINIMAL |
| TC-007 | Infer from STANDARD_FIELDS | opt_fields with custom_fields | STANDARD |

### 12.2 Integration Tests

| ID | Scenario | Setup | Expected |
|----|----------|-------|----------|
| IT-001 | Cascade with MINIMAL cache | Cache task with gid only, resolve cascade:OfficePhone | Fetches parent with STANDARD, returns value |
| IT-002 | cf: with STANDARD cache | Cache task with custom_fields, extract cf:Vertical | Returns value from custom_fields |
| IT-003 | Batch extraction with mixed completeness | 50 tasks: 25 MINIMAL, 25 STANDARD | 25 upgrades, 0 API calls for STANDARD entries |
| IT-004 | Legacy entry upgrade | Entry without metadata, require STANDARD | Treated as UNKNOWN, triggers re-fetch |

### 12.3 Performance Tests

| ID | Metric | Baseline | Target |
|----|--------|----------|--------|
| PT-001 | API calls per DataFrame build (warm cache, STANDARD) | N/A | 0 (all cache hits) |
| PT-002 | API calls per DataFrame build (warm cache, MINIMAL) | N/A | 1-2 batch upgrades |
| PT-003 | Cache entry metadata size overhead | 0 bytes | < 50 bytes per entry |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking change in get_async signature | Medium | High | Default `required_level=STANDARD` preserves behavior |
| Performance regression from completeness checks | Low | Medium | Integer comparison is O(1), negligible overhead |
| API quota impact from upgrades | Low | Medium | Batch upgrades minimize calls; only on genuine miss |
| Legacy entries cause widespread misses | Medium | Low | TTL expiry naturally replaces; conservative handling |

---

## ADRs

### ADR-COMPLETENESS-001: Tiered vs Field-Level Tracking

**Status**: Accepted

**Context**: Need to track which fields are present in cached task entries.

**Decision**: Use tiered completeness (MINIMAL, STANDARD, FULL) rather than field-level tracking.

**Rationale**:
1. Simpler implementation (single integer vs set of strings)
2. Fast comparison (integer inequality vs set operations)
3. Predictable upgrade paths (MINIMAL -> STANDARD -> FULL)
4. Covers 95%+ of use cases with 3 tiers

**Consequences**:
- May fetch more fields than strictly needed during upgrade
- Adding new tiers requires code changes
- Accepted tradeoff for simplicity

### ADR-COMPLETENESS-002: Fetch-on-Miss Upgrade Strategy

**Status**: Accepted

**Context**: How should insufficient entries be upgraded?

**Decision**: Use fetch-on-miss strategy - return `None` for insufficient entries, let caller handle re-fetch.

**Rationale**:
1. Simpler control flow (no hidden API calls)
2. Respects usage patterns (only upgrade what's actually needed)
3. Caller can batch upgrades for efficiency

**Consequences**:
- First access to upgraded entry has latency
- Callers must handle `None` and re-fetch pattern
- Provide `get_with_upgrade_async()` for convenience

### ADR-COMPLETENESS-003: No auto: Prefix

**Status**: Accepted

**Context**: Should an `auto:` prefix auto-infer `cf:` vs `cascade:`?

**Decision**: No `auto:` prefix - schema authors explicitly choose prefix.

**Rationale**:
1. Schema author knows domain semantics
2. Auto-inference doubles work for cascade fields
3. Completeness tracking solves the underlying bug
4. YAGNI

**Consequences**:
- Schemas must explicitly use correct prefix
- Less magic, more predictable behavior

---

## Success Criteria

| ID | Criterion | Measurement | Target |
|----|-----------|-------------|--------|
| SC-001 | cf:Vertical extraction succeeds | Extraction success rate | 100% (matches cascade:OfficePhone) |
| SC-002 | New entries have completeness metadata | Metadata presence check | 100% of new entries |
| SC-003 | API calls for warm STANDARD cache | API call count | 0 per DataFrame build |
| SC-004 | Legacy entry natural expiry | Entries with UNKNOWN after 1 week | < 5% |
| SC-005 | No breaking changes | Existing test suite | All tests pass |

---

## Appendices

### A. Field Sets by Tier

```python
MINIMAL_FIELDS = frozenset(["gid"])

STANDARD_FIELDS = frozenset([
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
])

FULL_FIELDS = frozenset([
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
])
```

### B. Existing Completeness Module Location

`/src/autom8_asana/cache/completeness.py` - Complete, needs integration wiring.

### C. Related Documentation

- TDD-UNIFIED-CACHE-001: Unified cache architecture
- TDD-CASCADING-FIELD-RESOLUTION-001: Cascade prefix design
- ADR-0131: GID enumeration caching
