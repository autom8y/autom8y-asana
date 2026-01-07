---
artifact_id: TDD-unit-cascade-resolution-fix
title: "Technical Design Document: Unit Cascade Resolution Fix"
created_at: "2026-01-06T18:50:00Z"
author: architect
status: draft
complexity: MODULE
prd_ref: PRD-unit-cascade-resolution-fix
components:
  - name: DiagnosticLogging
    type: module
    description: "INFO-level logging to trace cascade resolution flow in production"
    dependencies:
      - name: autom8y_log
        type: external
  - name: HierarchyWarmerFix
    type: module
    description: "Fixes for warm_ancestors_async to correctly traverse initial parent GIDs"
    dependencies:
      - name: HierarchyIndex
        type: internal
      - name: TasksClient
        type: internal
  - name: CascadeIntegrationTest
    type: module
    description: "Integration test that validates cascade resolution without mocking"
    dependencies:
      - name: pytest
        type: external
      - name: UnifiedTaskStore
        type: internal
related_adrs:
  - ADR-hierarchy-registration-architecture
  - ADR-0054
schema_version: "1.0"
---

# TDD: Unit Cascade Resolution Fix (Revised)

## Overview

This TDD addresses the production failure where Unit DataFrame `office_phone` and `vertical` columns are null because cascade field resolution through the parent Business task fails. Previous fixes were implemented but the issue persists, indicating a deeper root cause in the hierarchy registration flow.

## Executive Summary

**Problem**: Unit resolution returns NOT_FOUND for all lookups despite data existing in Asana.

**Root Cause**: HierarchyIndex is not being populated with parent relationships during `warm_hierarchy=True` execution. The cascade resolution system correctly traverses the hierarchy, but the hierarchy is empty.

**Solution**:
1. Add diagnostic INFO-level logging to verify warm_hierarchy execution in production
2. Fix the hierarchy registration gap where immediate parents aren't registered before `warm_ancestors_async` traversal
3. Add integration test that validates the full cascade flow without mocking

## Deep Exploration Findings

Three exploration agents analyzed the cascade resolution system and identified:

### What Works (Verified)
- `UNIT_SCHEMA` correctly defines `source="cascade:Office Phone"` and `source="cascade:Vertical"`
- `ProjectDataFrameBuilder.build_with_parallel_fetch_async()` passes `warm_hierarchy=True` (line 853)
- `DataFrameViewPlugin._resolve_cascade_from_dict()` handles cascade resolution (line 338)
- `_HIERARCHY_OPT_FIELDS` includes all required custom field types (enum_value, etc.)
- `GidLookupIndex.from_dataframe()` builds O(1) lookup from DataFrame

### Silent Failure Chain (Root Cause)

```
ProjectDataFrameBuilder
    |
    +--> put_batch_async(warm_hierarchy=True, tasks_client=client.tasks)
           |
           +--> For each task: _hierarchy.register(task)  # Units registered
           |      └── Registers Unit GID -> parent Business GID (in _parent_map)
           |
           +--> Immediate parent fetch (lines 526-555)
           |      └── BUT: _hierarchy.contains(parent_gid) returns True if parent
           |          GID was just registered as a parent reference, NOT as a full task
           |
           +--> warm_ancestors_async(task_gids, hierarchy_index, tasks_client, ...)
                  |
                  +--> parent_gid = hierarchy_index.get_parent_gid(gid)  # Line 144
                  |      └── Returns the parent GID from _parent_map
                  |
                  +--> if parent_gid and parent_gid not in visited:
                  |      └── Adds to current_gids
                  |
                  +--> Loop: for gid in current_gids:
                         |
                         +--> if not hierarchy_index.contains(gid):  # Line 169
                         |      └── PROBLEM: Business GID WAS registered as parent
                         |          reference during Unit registration, so contains()
                         |          returns True, skipping the fetch!
                         |
                         +--> gids_to_fetch stays empty
                         |
                         +--> No Business tasks fetched
                         |
                         +--> Business custom_fields never cached
```

### The Registration vs Contains Gap

When `HierarchyIndex.register(unit_task)` is called:

```python
# hierarchy.py _asana_parent_gid_extractor extracts parent.gid
# The SDK HierarchyTracker stores:
#   _parent_map[unit_gid] = business_gid
#   _children_map[business_gid].add(unit_gid)
```

The SDK's `HierarchyTracker.contains(gid)` likely checks if `gid` exists as either:
1. A key in `_parent_map` (registered entities), OR
2. A key in `_children_map` (entities with children)

When Unit registration adds `business_gid` to `_children_map`, `contains(business_gid)` returns `True` even though the Business task was never fully registered with its own parent relationship.

**Result**: `warm_ancestors_async` thinks Business is already registered, skips fetching it, and Business custom_fields are never cached.

## Component Interaction Diagram (Updated)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ACTUAL BEHAVIOR (Root Cause)                              │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: Unit tasks fetched from API
┌─────────────────────────────────────────────────────────────────────────────┐
│  Unit: { gid: "unit-1", parent: { gid: "business-1" }, custom_fields: [] }  │
│  Unit: { gid: "unit-2", parent: { gid: "business-1" }, custom_fields: [] }  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Step 2: put_batch_async(tasks, warm_hierarchy=True)
┌─────────────────────────────────────────────────────────────────────────────┐
│  _hierarchy.register(unit-1) creates:                                        │
│    _parent_map["unit-1"] = "business-1"                                      │
│    _children_map["business-1"] = {"unit-1"}  ◄── business-1 added as KEY    │
│                                                                              │
│  _hierarchy.register(unit-2) creates:                                        │
│    _parent_map["unit-2"] = "business-1"                                      │
│    _children_map["business-1"].add("unit-2")                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Step 3: Immediate parent fetch loop (lines 526-555)
┌─────────────────────────────────────────────────────────────────────────────┐
│  for task in tasks:                                                          │
│      parent_gid = "business-1"                                               │
│      if not self._hierarchy.contains(parent_gid):  ◄── FALSE! It's in       │
│          parent_gids_needed.add(parent_gid)              _children_map       │
│                                                                              │
│  parent_gids_needed = {} (empty!)                                            │
│  NO immediate parent fetch occurs                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Step 4: warm_ancestors_async()
┌─────────────────────────────────────────────────────────────────────────────┐
│  visited = {"unit-1", "unit-2"}                                              │
│  current_gids = ["business-1"]  (from get_parent_gid)                        │
│                                                                              │
│  Loop: for gid in ["business-1"]:                                            │
│      if gid not in visited: visited.add("business-1")                        │
│      if not hierarchy_index.contains("business-1"):  ◄── FALSE again!       │
│          gids_to_fetch.append(gid)                                           │
│                                                                              │
│  gids_to_fetch = [] (empty!)                                                 │
│  NO Business tasks fetched                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Step 5: Cascade resolution during DataFrame materialization
┌─────────────────────────────────────────────────────────────────────────────┐
│  _resolve_cascade_from_dict(unit_data, "Office Phone")                       │
│      │                                                                       │
│      +--> get_parent_chain_async("unit-1")                                   │
│             │                                                                │
│             +--> _hierarchy.get_ancestor_chain("unit-1")                     │
│                    │                                                         │
│                    +--> Returns ["business-1"] (from _parent_map)            │
│             │                                                                │
│             +--> cache.get_batch(["business-1"])                             │
│                    │                                                         │
│                    +--> Returns {} (Business never cached!)                  │
│             │                                                                │
│             +--> Returns [] (chain incomplete)                               │
│      │                                                                       │
│      +--> Fallback: get_with_upgrade_async("business-1")                     │
│             │                                                                │
│             +--> tasks_client is None in DataFrameViewPlugin                 │
│             │    (not passed through from builder)                           │
│             │                                                                │
│             +--> Returns None                                                │
│      │                                                                       │
│      +--> Returns None (cascade fails)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
Step 6: DataFrame Result
┌─────────────────────────────────────────────────────────────────────────────┐
│  office_phone = NULL, vertical = NULL for all Units                          │
│  GidLookupIndex filters out nulls → 0 matches                                │
│  Unit resolution returns NOT_FOUND                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Proposed Fixes

### Fix 1: Change `contains()` Check to Use Cache, Not HierarchyIndex

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py`

The immediate parent fetch loop (lines 526-555) should check if parent is **in cache** (has full task data), not just in hierarchy index (which only confirms parent relationship exists).

```python
# Current (lines 530-531):
if parent_gid and not self._hierarchy.contains(parent_gid):
    parent_gids_needed.add(parent_gid)

# Fixed:
# Check cache, not hierarchy - we need the parent's FULL TASK DATA
if parent_gid:
    cached_entry = self.cache.get_versioned(parent_gid, EntryType.TASK)
    if cached_entry is None:
        parent_gids_needed.add(parent_gid)
```

### Fix 2: Same Fix in warm_ancestors_async

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py`

The check at line 169 has the same issue - it checks `hierarchy_index.contains()` instead of whether the task data is actually cached.

```python
# Current (lines 168-175):
if not hierarchy_index.contains(gid):
    gids_to_fetch.append(gid)
elif unified_store:
    # Check if in cache
    cached = unified_store.cache.get(gid)
    if not cached:
        gids_to_fetch.append(gid)

# Fixed - always check cache first since hierarchy.contains() is misleading:
if unified_store:
    # Check if task data is actually cached (not just hierarchy relationship)
    cached = unified_store.cache.get_versioned(gid, EntryType.TASK)
    if cached is None:
        gids_to_fetch.append(gid)
else:
    # No unified_store - fall back to hierarchy check
    if not hierarchy_index.contains(gid):
        gids_to_fetch.append(gid)
```

### Fix 3: Add INFO-Level Diagnostic Logging

**Files**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/views/dataframe_view.py`

Critical paths need INFO-level logging to verify execution in production:

```python
# unified.py - after put_batch_async line 510 (batch store complete):
logger.info(
    "unified_store_hierarchy_warm_starting",
    extra={
        "task_count": len(tasks),
        "warm_hierarchy": warm_hierarchy,
        "has_tasks_client": tasks_client is not None,
    },
)

# unified.py - after immediate parent fetch (line 555):
logger.info(
    "unified_store_immediate_parents_fetched",
    extra={
        "parents_requested": len(parent_gids_needed),
        "parents_fetched": immediate_parents_fetched,
    },
)

# hierarchy_warmer.py - at warm_ancestors_async entry:
logger.info(
    "warm_ancestors_starting",
    extra={
        "initial_gids_count": len(gids),
        "parent_gids_to_fetch": len(current_gids),
        "max_depth": max_depth,
    },
)

# hierarchy_warmer.py - at warm_ancestors_async completion:
logger.info(
    "warm_ancestors_completed",
    extra={
        "total_warmed": total_warmed,
        "total_visited": len(visited),
        "final_depth": depth,
    },
)

# dataframe_view.py - in _resolve_cascade_from_dict when chain empty:
logger.info(
    "cascade_resolution_empty_chain",
    extra={
        "task_gid": task_gid,
        "field_name": field_name,
        "parent_gid": task_data.get("parent", {}).get("gid") if task_data.get("parent") else None,
    },
)
```

### Fix 4: Import EntryType in hierarchy_warmer.py

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py`

The fix requires importing EntryType for cache lookup:

```python
# Add to imports at top of file:
from autom8_asana.cache.entry import EntryType
```

## Implementation Order

| Priority | Fix | Risk | Impact | Effort |
|----------|-----|------|--------|--------|
| 1 | Fix 3: Diagnostic logging | Low | Enables production debugging | 30 min |
| 2 | Fix 1: Cache check in put_batch_async | Medium | Core fix for immediate parent | 1 hour |
| 3 | Fix 2: Cache check in warm_ancestors_async | Medium | Core fix for recursive warming | 1 hour |
| 4 | Fix 4: Import EntryType | Low | Required for Fix 2 | 5 min |

## Test Strategy

### Unit Tests

**Test 1**: Verify `contains()` vs cache distinction
```python
def test_hierarchy_contains_vs_cache():
    """Verify hierarchy.contains() doesn't mean data is cached."""
    store = UnifiedTaskStore(cache=InMemoryCacheProvider())

    # Register a Unit - its parent GID gets added to hierarchy
    unit = {"gid": "unit-1", "parent": {"gid": "business-1"}}
    store._hierarchy.register(unit)

    # Hierarchy contains business-1 (as parent reference)
    assert store._hierarchy.contains("business-1") == True

    # But business-1 is NOT cached (no task data)
    cached = store.cache.get_versioned("business-1", EntryType.TASK)
    assert cached is None
```

**Test 2**: Verify immediate parent fetch with cache check
```python
@pytest.mark.asyncio
async def test_put_batch_fetches_uncached_parents():
    """put_batch_async should fetch parents not in cache."""
    store = UnifiedTaskStore(cache=InMemoryCacheProvider())
    mock_client = AsyncMock()

    business_data = Task(
        gid="business-1",
        name="Test Business",
        custom_fields=[
            {"name": "Office Phone", "resource_subtype": "text", "text_value": "+15551234567"}
        ]
    )
    mock_client.get_async.return_value = business_data

    units = [
        {"gid": "unit-1", "parent": {"gid": "business-1"}},
        {"gid": "unit-2", "parent": {"gid": "business-1"}},
    ]

    await store.put_batch_async(
        units,
        tasks_client=mock_client,
        warm_hierarchy=True,
    )

    # Verify business-1 was fetched
    mock_client.get_async.assert_called()

    # Verify business-1 is now cached
    cached = store.cache.get_versioned("business-1", EntryType.TASK)
    assert cached is not None
    assert cached.data["custom_fields"][0]["text_value"] == "+15551234567"
```

### Integration Test (FR-004)

**File**: `/Users/tomtenuta/Code/autom8_asana/tests/integration/test_unit_cascade_resolution.py`

```python
"""Integration test for Unit cascade field resolution.

This test validates the complete cascade resolution flow WITHOUT mocking
the cascade field values. It uses actual parent hierarchy traversal.

Per PRD FR-004: "Create test that validates end-to-end cascade field resolution."
"""

import pytest
import polars as pl

from autom8_asana.cache.in_memory import InMemoryCacheProvider
from autom8_asana.cache.unified import UnifiedTaskStore
from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA


# Test data: Simulated Business -> Unit hierarchy
BUSINESS_TASK = {
    "gid": "business-001",
    "name": "Test Business",
    "parent": None,  # Business is root
    "custom_fields": [
        {
            "gid": "cf-phone",
            "name": "Office Phone",
            "resource_subtype": "text",
            "text_value": "+15551234567",
            "display_value": "+15551234567",
        },
        {
            "gid": "cf-vertical",
            "name": "Vertical",
            "resource_subtype": "enum",
            "enum_value": {"gid": "ev-chiro", "name": "Chiropractic"},
            "display_value": "Chiropractic",
        },
    ],
}

UNIT_TASKS = [
    {
        "gid": "unit-001",
        "name": "Unit Task 1",
        "parent": {"gid": "business-001"},
        "custom_fields": [],  # No local cascade fields - must resolve from parent
    },
    {
        "gid": "unit-002",
        "name": "Unit Task 2",
        "parent": {"gid": "business-001"},
        "custom_fields": [],
    },
]


class MockTasksClient:
    """Mock TasksClient that returns Business task when requested."""

    async def get_async(self, gid: str, opt_fields: list[str] | None = None, raw: bool = False):
        if gid == "business-001":
            # Return a mock Task-like object with model_dump
            class MockTask:
                def model_dump(self, exclude_none: bool = False) -> dict:
                    return BUSINESS_TASK
            return MockTask()
        return None


@pytest.mark.asyncio
async def test_cascade_resolution_populates_fields():
    """Test that cascade fields are populated from Business parent.

    This test validates:
    1. Unit tasks are stored with warm_hierarchy=True
    2. Business parent is fetched and cached
    3. Cascade resolution extracts office_phone from Business
    4. Cascade resolution extracts vertical from Business

    Per SC-002: "Unit DataFrame contains populated office_phone column"
    Per SC-003: "Unit DataFrame contains populated vertical column"
    """
    # Setup: Create store with in-memory cache
    cache = InMemoryCacheProvider()
    store = UnifiedTaskStore(cache=cache)
    mock_client = MockTasksClient()

    # Act: Store Unit tasks with hierarchy warming
    await store.put_batch_async(
        UNIT_TASKS,
        tasks_client=mock_client,
        warm_hierarchy=True,
    )

    # Verify: Business was fetched and cached
    hierarchy = store.get_hierarchy_index()
    assert hierarchy.contains("business-001"), "Business should be in hierarchy"

    # Verify: Parent chain works
    chain = await store.get_parent_chain_async("unit-001")
    assert len(chain) == 1, f"Expected 1 parent, got {len(chain)}"
    assert chain[0]["gid"] == "business-001"

    # Verify: Business has cascade fields
    assert chain[0]["custom_fields"][0]["name"] == "Office Phone"
    assert chain[0]["custom_fields"][0]["text_value"] == "+15551234567"


@pytest.mark.asyncio
async def test_dataframe_cascade_fields_populated():
    """Test that DataFrame extraction populates cascade columns.

    This validates the full extraction path:
    1. DataFrameViewPlugin._resolve_cascade_from_dict() is called
    2. It retrieves parent chain from store
    3. It extracts Office Phone and Vertical from Business parent
    4. DataFrame has non-null values in cascade columns

    Per SC-004: "Integration test validates cascade resolution with real hierarchy"
    """
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin

    # Setup
    cache = InMemoryCacheProvider()
    store = UnifiedTaskStore(cache=cache)
    mock_client = MockTasksClient()

    # Store Units with hierarchy warming
    await store.put_batch_async(
        UNIT_TASKS,
        tasks_client=mock_client,
        warm_hierarchy=True,
    )

    # Store Units again for the view to fetch
    for unit in UNIT_TASKS:
        await store.put_async(unit)

    # Create view plugin
    view = DataFrameViewPlugin(store=store, schema=UNIT_SCHEMA)

    # Materialize DataFrame
    df = await view.materialize_async(
        task_gids=["unit-001", "unit-002"],
        project_gid="test-project",
    )

    # Verify cascade fields populated
    assert "office_phone" in df.columns, "office_phone column missing"
    assert "vertical" in df.columns, "vertical column missing"

    # Check values are NOT null
    office_phone_nulls = df["office_phone"].null_count()
    vertical_nulls = df["vertical"].null_count()
    total_rows = len(df)

    assert office_phone_nulls == 0, f"office_phone has {office_phone_nulls}/{total_rows} nulls"
    assert vertical_nulls == 0, f"vertical has {vertical_nulls}/{total_rows} nulls"

    # Verify actual values
    assert df["office_phone"][0] == "+15551234567"
    assert df["vertical"][0].lower() == "chiropractic"
```

## Success Criteria Traceability

| SC-ID | Requirement | Addressed By |
|-------|-------------|--------------|
| SC-001 | Unit resolution returns 2/3 matches for demo pairs | Fixes 1-2 enable parent fetching, Fix 3 enables debugging |
| SC-002 | Unit DataFrame contains populated office_phone column | Fix 1 (cache check) ensures Business is fetched with custom_fields |
| SC-003 | Unit DataFrame contains populated vertical column | Fix 1 (cache check) ensures Business enum_value is cached |
| SC-004 | Integration test validates cascade with real hierarchy | Integration test uses real cascade resolution, no value mocking |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache check changes behavior for other callers | Low | Medium | Change is strictly more correct - fetches missing data |
| Additional API calls for parent fetching | Medium | Low | Only fetches parents once, then cached |
| Log verbosity increase | Low | Low | INFO level appropriate for production diagnosis |
| Circular import with EntryType | Low | Low | EntryType is in cache.entry, no circular dependency |

## Performance Considerations

**Before fix**: Hierarchy warming skips parent fetch, cascade fails, all Units return null.

**After fix**:
- First extraction: +N API calls for N unique Business parents (typically 1-50 calls)
- Subsequent extractions: 0 additional API calls (parents cached)
- Typical overhead: 1-5 seconds on cold cache

The performance impact is acceptable because:
1. Current behavior is **broken** (returns all nulls)
2. Parent tasks are cached after first fetch
3. Most projects have few unique Business parents (bounded by organizational structure)

## Files to Modify

| File | Change |
|------|--------|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` | Fix 1: Cache check instead of hierarchy.contains() |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py` | Fix 2: Cache check, Fix 4: Import EntryType |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/views/dataframe_view.py` | Fix 3: Diagnostic logging |
| `/Users/tomtenuta/Code/autom8_asana/tests/integration/test_unit_cascade_resolution.py` | NEW: Integration test (FR-004) |

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-unit-cascade-resolution-fix.md` | Yes |
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unit-cascade-resolution-fix.md` | Yes (this file) |
| ADR | `/Users/tomtenuta/Code/autom8_asana/docs/design/ADR-hierarchy-registration-architecture.md` | Yes |
| unified.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` | Yes |
| hierarchy_warmer.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py` | Yes |
| dataframe_view.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/views/dataframe_view.py` | Yes |
| hierarchy.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy.py` | Yes |

## Handoff to Principal Engineer

This TDD is ready for implementation. The root cause is a **semantic mismatch**: `hierarchy.contains(gid)` returns `True` when a GID exists as a parent reference in `_children_map`, but this does NOT mean the task data is cached.

**Implementation order**:
1. Fix 3 (logging) - Deploy first to verify hypothesis in production
2. Fixes 1, 2, 4 - Core fix after hypothesis confirmed
3. Integration test - Validates fix prevents regression

**Validation target**: After fix, the demo script at `/Users/tomtenuta/Code/autom8-s2s-demo/examples/05_gid_lookup.py` should return 2/3 matches:
- `+12604442080` / `chiropractic` -> GID (resolved)
- `+19127481506` / `chiropractic` -> GID (resolved)
- `+15555555555` / `dental` -> NOT_FOUND (expected - no matching Unit)

---

## Appendix: Code References

### HierarchyIndex.contains() Implementation (SDK)

The `HierarchyIndex` wraps `autom8y_cache.HierarchyTracker`. The SDK's `contains()` method likely checks:

```python
# Hypothesized SDK implementation:
def contains(self, entity_id: str) -> bool:
    return entity_id in self._parent_map or entity_id in self._children_map
```

When a Unit is registered with `parent: {"gid": "business-1"}`, the SDK adds `"business-1"` to `_children_map` even though Business was never registered as a full entity. This makes `contains("business-1")` return `True`.

### Current put_batch_async Flow (lines 526-555)

```python
if warm_hierarchy and tasks_client is not None:
    # ...
    parent_gids_needed: set[str] = set()
    for task in tasks:
        parent = task.get("parent")
        if parent and isinstance(parent, dict):
            parent_gid = parent.get("gid")
            if parent_gid and not self._hierarchy.contains(parent_gid):  # <-- BUG
                parent_gids_needed.add(parent_gid)
```

The fix changes `self._hierarchy.contains(parent_gid)` to `self.cache.get_versioned(parent_gid, EntryType.TASK) is None`.
