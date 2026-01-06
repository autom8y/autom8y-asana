---
artifact_id: TDD-unit-cascade-resolution-fix
title: "Technical Design Document: Unit Cascade Resolution Fix"
created_at: "2026-01-06T14:00:00Z"
author: architect
status: draft
complexity: MODULE
prd_ref: PRD-unit-cascade-resolution-fix
related_adrs:
  - ADR-hierarchy-registration-architecture
  - ADR-0054 (Cascading Field Design)
schema_version: "1.0"
---

# TDD: Unit Cascade Resolution Fix

## Overview

This TDD addresses the failure of cascade field resolution for Unit tasks where `office_phone` and `vertical` columns end up null because the parent hierarchy (Business task) is not being properly traversed. The fix ensures cascade fields defined as `source="cascade:Office Phone"` and `source="cascade:Vertical"` correctly resolve values from Business ancestor tasks.

## Root Cause Analysis

### Investigation Summary

The cascade resolution flow was traced through four key components:

1. **DataFrameViewPlugin._resolve_cascade_from_dict()** - Entry point for cascade resolution
2. **UnifiedTaskStore.get_parent_chain_async()** - Retrieves ancestor chain from hierarchy
3. **HierarchyIndex.get_ancestor_chain()** - Returns ancestor GIDs from internal tracker
4. **CascadeViewPlugin._get_custom_field_value_from_dict()** - Extracts field value from task dict

### Root Cause: Missing Parent Chain Registration

**Primary Issue**: `HierarchyIndex.get_ancestor_chain(unit_gid)` returns an empty list because parent relationships are not transitively registered.

When a Unit task is cached:
1. `put_batch_async()` registers the Unit with its immediate parent GID
2. BUT the parent (Business) task is NOT in the HierarchyIndex unless also fetched
3. `get_ancestor_chain()` cannot traverse past the Unit's registered parent because the Business isn't registered

**Evidence from Code**:

```python
# hierarchy.py line 174
# get_ancestor_chain returns empty if parent not registered:
# "Empty list if task has no parent or is not registered."

# unified.py line 566-569
ancestor_gids = self._hierarchy.get_ancestor_chain(gid, max_depth=max_depth)
if not ancestor_gids:
    return []  # <-- Returns empty, cascade fails silently
```

### Secondary Issue: Incomplete opt_fields in Hierarchy Warmer

When `warm_hierarchy=True` triggers `warm_ancestors_async()`, it fetches parent tasks with `_HIERARCHY_OPT_FIELDS`:

```python
# hierarchy_warmer.py line 23-33
_HIERARCHY_OPT_FIELDS: list[str] = [
    "gid",
    "name",
    "parent",
    "parent.gid",
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.display_value",
    "custom_fields.text_value",  # Only text_value!
]
```

**Missing fields for cascade resolution**:
- `custom_fields.resource_subtype` - Required to identify field type for extraction
- `custom_fields.enum_value` - Required for Vertical (enum type)
- `custom_fields.enum_value.name` - Required to extract enum name
- `custom_fields.number_value` - Required for numeric fields

Without `resource_subtype`, `_extract_field_value()` falls through to `display_value` which may be empty for structured fields.

### Tertiary Issue: Warm Hierarchy Not Effective

The `warm_ancestors_async()` function has a logic issue in its loop:

```python
# hierarchy_warmer.py line 143-163
gids_to_fetch: list[str] = []
for gid in current_gids:
    if gid not in visited:
        visited.add(gid)
        # Check if we need to fetch this GID
        if not hierarchy_index.contains(gid):
            gids_to_fetch.append(gid)
        elif unified_store:
            # Check if in cache
            cached = unified_store.cache.get(gid)  # <-- Sync call on async cache!
            if not cached:
                gids_to_fetch.append(gid)
```

This loop checks `hierarchy_index.contains(gid)` BEFORE adding to `visited`, but the initial GIDs are already added to visited at line 129. The loop then immediately checks parents of already-visited GIDs without fetching their data first.

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Unit DataFrame Build Flow                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ProjectDataFrameBuilder.build_with_parallel_fetch_async()              │
│  ├── Fetch Unit tasks from API                                          │
│  └── put_batch_async(tasks, warm_hierarchy=True)  ◄─┐                   │
└────────────────────────────────────────────────────│────────────────────┘
                                    │                │
                                    ▼                │ FIX POINT 1
┌─────────────────────────────────────────────────────────────────────────┐
│  UnifiedTaskStore.put_batch_async()                                     │
│  ├── For each task: _hierarchy.register(task)                           │
│  │   └── Registers Unit GID -> parent Business GID                      │
│  └── IF warm_hierarchy: warm_ancestors_async()    ◄─┐                   │
└────────────────────────────────────────────────────│────────────────────┘
                                    │                │ FIX POINT 2
                                    ▼                │
┌─────────────────────────────────────────────────────────────────────────┐
│  warm_ancestors_async()                                                 │
│  ├── Collect parent GIDs from Unit tasks                                │
│  ├── Fetch Business tasks (missing: enum fields)  ◄──── FIX POINT 3    │
│  ├── hierarchy_index.register(business)                                 │
│  └── unified_store.put_async(business)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DataFrameViewPlugin.materialize_async()                                │
│  └── For each cascade: column                                           │
│      └── _resolve_cascade_from_dict(task_data, "Office Phone")          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  DataFrameViewPlugin._resolve_cascade_from_dict()                       │
│  ├── Check local value (Unit has none for cascade fields)               │
│  └── get_parent_chain_async(unit_gid)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  UnifiedTaskStore.get_parent_chain_async()                              │
│  ├── _hierarchy.get_ancestor_chain(unit_gid)                            │
│  │   └── PROBLEM: Returns [] if Business not registered                 │
│  └── Fetch ancestors from cache (none to fetch)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  RESULT: parent_chain = []                                              │
│  cascade field value = None                                             │
│  office_phone = null, vertical = null                                   │
│  GidLookupIndex cannot build lookup dict                                │
│  Unit resolution returns NOT_FOUND                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Proposed Fix

### Fix 1: Expand _HIERARCHY_OPT_FIELDS

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py`

Add missing custom field types to ensure parent tasks have complete field data:

```python
# Current (incomplete):
_HIERARCHY_OPT_FIELDS: list[str] = [
    "gid",
    "name",
    "parent",
    "parent.gid",
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.display_value",
    "custom_fields.text_value",
]

# Fixed (complete for cascade resolution):
_HIERARCHY_OPT_FIELDS: list[str] = [
    "gid",
    "name",
    "parent",
    "parent.gid",
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.resource_subtype",  # ADD: Required for type-aware extraction
    "custom_fields.display_value",
    "custom_fields.text_value",
    "custom_fields.enum_value",         # ADD: For enum fields like Vertical
    "custom_fields.enum_value.name",    # ADD: For enum name extraction
    "custom_fields.number_value",       # ADD: For numeric fields
    "custom_fields.multi_enum_values",  # ADD: For multi-enum fields
    "custom_fields.multi_enum_values.name",  # ADD: For multi-enum names
]
```

### Fix 2: Ensure Warm Hierarchy Processes Initial Task Parents

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py`

The current logic adds initial GIDs to `visited` before the loop, then tries to find their parents. But the initial GIDs are the Unit tasks we already have - we need to fetch their PARENTS.

```python
# Current (line 125-132):
total_warmed = 0
visited: set[str] = set()

# Start with the initial GIDs as already visited (we don't need to fetch them)
visited.update(gids)

current_gids = gids  # <-- These are Units, we already have them
depth = 0

# Fixed approach:
total_warmed = 0
visited: set[str] = set()
visited.update(gids)  # Mark Unit GIDs as visited

# Extract parent GIDs to start traversal
current_gids: list[str] = []
for gid in gids:
    parent_gid = hierarchy_index.get_parent_gid(gid)
    if parent_gid and parent_gid not in visited:
        current_gids.append(parent_gid)

depth = 0
```

### Fix 3: Add Direct Parent Fetch in put_batch_async When warm_hierarchy=True

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py`

As a belt-and-suspenders approach, ensure that `put_batch_async` directly fetches immediate parents before calling `warm_ancestors_async`:

```python
# In put_batch_async, after line 510 (after batch store):
if warm_hierarchy and tasks_client is not None:
    # First, ensure we have immediate parents
    parent_gids_needed: set[str] = set()
    for task in tasks:
        parent = task.get("parent")
        if parent and isinstance(parent, dict):
            parent_gid = parent.get("gid")
            if parent_gid and not self._hierarchy.contains(parent_gid):
                parent_gids_needed.add(parent_gid)

    if parent_gids_needed:
        # Fetch and register immediate parents first
        from autom8_asana.cache.hierarchy_warmer import _HIERARCHY_OPT_FIELDS
        for parent_gid in parent_gids_needed:
            try:
                parent_task = await tasks_client.get_async(
                    parent_gid, opt_fields=_HIERARCHY_OPT_FIELDS
                )
                if parent_task:
                    parent_dict = parent_task.model_dump(exclude_none=True)
                    self._hierarchy.register(parent_dict)
                    await self.put_async(parent_dict, opt_fields=_HIERARCHY_OPT_FIELDS)
            except Exception as e:
                logger.warning(
                    "warm_immediate_parent_failed",
                    extra={"parent_gid": parent_gid, "error": str(e)},
                )

    # Then warm deeper ancestors
    from autom8_asana.cache.hierarchy_warmer import warm_ancestors_async
    # ... existing warm_ancestors_async call
```

### Fix 4: Fallback in _resolve_cascade_from_dict

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/views/dataframe_view.py`

Add a fallback to directly use parent.gid from task_data when parent chain is empty:

```python
async def _resolve_cascade_from_dict(
    self,
    task_data: dict[str, Any],
    field_name: str,
) -> Any:
    # First try local extraction
    local_value = self._cascade_plugin._get_custom_field_value_from_dict(
        task_data, field_name
    )
    if local_value is not None:
        return local_value

    # Get parent chain from unified store
    task_gid = task_data.get("gid")
    if not task_gid:
        return None

    parent_chain = await self._store.get_parent_chain_async(task_gid)

    # FALLBACK: If parent_chain is empty but task has parent, try direct fetch
    if not parent_chain:
        parent = task_data.get("parent")
        if parent and isinstance(parent, dict):
            parent_gid = parent.get("gid")
            if parent_gid:
                # Try to get parent directly from cache
                from autom8_asana.cache.completeness import CompletenessLevel
                from autom8_asana.cache.freshness_coordinator import FreshnessMode
                parent_data = await self._store.get_with_upgrade_async(
                    parent_gid,
                    required_level=CompletenessLevel.STANDARD,
                    freshness=FreshnessMode.IMMEDIATE,
                )
                if parent_data:
                    parent_chain = [parent_data]

    if not parent_chain:
        return None

    # Search parent chain for field value
    for parent_data in parent_chain:
        value = self._cascade_plugin._get_custom_field_value_from_dict(
            parent_data, field_name
        )
        if value is not None:
            return value

    return None
```

## Implementation Order

Fixes should be applied in this order to minimize risk:

| Priority | Fix | Risk | Impact |
|----------|-----|------|--------|
| 1 | Fix 1: Expand _HIERARCHY_OPT_FIELDS | Low | Ensures fetched parents have complete custom fields |
| 2 | Fix 2: Initial parent GID extraction | Medium | Changes warm_ancestors_async loop logic |
| 3 | Fix 4: Fallback in _resolve_cascade | Low | Defensive fallback, no regression risk |
| 4 | Fix 3: Direct parent fetch in put_batch | Medium | Belt-and-suspenders, more API calls |

## Test Strategy

### Unit Tests

**Test 1**: HierarchyIndex ancestor chain traversal
```python
def test_get_ancestor_chain_with_registered_parent():
    """Verify ancestor chain works when parent is registered."""
    index = HierarchyIndex()

    # Register both tasks
    business = {"gid": "business-1", "parent": None}
    unit = {"gid": "unit-1", "parent": {"gid": "business-1"}}

    index.register(business)
    index.register(unit)

    chain = index.get_ancestor_chain("unit-1")
    assert chain == ["business-1"]
```

**Test 2**: Cascade resolution with populated parent chain
```python
@pytest.mark.asyncio
async def test_resolve_cascade_from_populated_chain():
    """Verify cascade field extracted from parent in chain."""
    # Set up store with Business and Unit
    business_data = {
        "gid": "business-1",
        "parent": None,
        "custom_fields": [{
            "name": "Office Phone",
            "resource_subtype": "text",
            "text_value": "+15551234567",
        }],
    }
    unit_data = {
        "gid": "unit-1",
        "parent": {"gid": "business-1"},
        "custom_fields": [],
    }

    # Store should return business in parent chain
    mock_store.get_parent_chain_async.return_value = [business_data]

    plugin = DataFrameViewPlugin(store=mock_store, schema=UNIT_SCHEMA)
    result = await plugin._resolve_cascade_from_dict(unit_data, "Office Phone")

    assert result == "+15551234567"
```

**Test 3**: _HIERARCHY_OPT_FIELDS completeness
```python
def test_hierarchy_opt_fields_includes_all_types():
    """Verify _HIERARCHY_OPT_FIELDS has all required custom field types."""
    from autom8_asana.cache.hierarchy_warmer import _HIERARCHY_OPT_FIELDS

    required_fields = {
        "custom_fields.resource_subtype",
        "custom_fields.enum_value",
        "custom_fields.enum_value.name",
        "custom_fields.number_value",
    }

    for field in required_fields:
        assert field in _HIERARCHY_OPT_FIELDS, f"Missing: {field}"
```

### Integration Tests

**Test 4**: End-to-end cascade resolution
```python
@pytest.mark.asyncio
async def test_unit_cascade_resolution_e2e():
    """Integration test: Unit DataFrame has cascade fields populated."""
    # Use real Asana client with test project
    client = await AsanaClient.create()

    project = await client.projects.get_async(UNIT_PROJECT_GID)
    builder = ProjectDataFrameBuilder(
        project=project,
        task_type="Unit",
        schema=UNIT_SCHEMA,
        unified_store=client.unified_store,
    )

    df = await builder.build_with_parallel_fetch_async(client)

    # Verify cascade fields populated
    office_phone_nulls = df["office_phone"].null_count()
    vertical_nulls = df["vertical"].null_count()
    total = len(df)

    # Allow 10% null for incomplete data
    assert office_phone_nulls / total < 0.1, f"Too many null office_phone: {office_phone_nulls}/{total}"
    assert vertical_nulls / total < 0.1, f"Too many null vertical: {vertical_nulls}/{total}"
```

**Test 5**: Warm hierarchy effectiveness
```python
@pytest.mark.asyncio
async def test_warm_hierarchy_populates_business_parents():
    """Verify warm_hierarchy=True fetches Business parent tasks."""
    store = UnifiedTaskStore(cache=InMemoryCacheProvider())

    # Store Unit tasks
    units = [
        {"gid": "unit-1", "parent": {"gid": "business-1"}},
        {"gid": "unit-2", "parent": {"gid": "business-1"}},
    ]

    await store.put_batch_async(
        units,
        warm_hierarchy=True,
        tasks_client=mock_tasks_client,
    )

    # Verify Business was fetched and registered
    assert store._hierarchy.contains("business-1")

    # Verify parent chain works
    chain = await store.get_parent_chain_async("unit-1")
    assert len(chain) == 1
    assert chain[0]["gid"] == "business-1"
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API rate limiting from additional parent fetches | Medium | Medium | Bounded concurrency in hierarchy_warmer (max 5) |
| Regression in other entity types | Low | High | Unit tests cover Business, Unit, Contact schemas |
| Performance degradation from hierarchy warming | Low | Medium | Only fetches missing parents, caches results |
| Custom field type handling edge cases | Low | Medium | Fallback to display_value for unknown types |

## Success Criteria Traceability

| SC-ID | Requirement | Addressed By |
|-------|-------------|--------------|
| SC-001 | Unit resolution returns 2/3 matches | Fixes 1-4 enable cascade field population |
| SC-002 | Unit DataFrame has populated office_phone | Fix 1 (enum fields) + Fix 2/3 (hierarchy) |
| SC-003 | Unit DataFrame has populated vertical | Fix 1 (enum fields) + Fix 2/3 (hierarchy) |
| SC-004 | Integration test validates cascade | Test 4 (e2e cascade resolution) |

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-unit-cascade-resolution-fix.md` | Yes |
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unit-cascade-resolution-fix.md` | Pending |
| hierarchy_warmer.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py` | Yes |
| unified.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` | Yes |
| dataframe_view.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/views/dataframe_view.py` | Yes |
| UNIT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/unit.py` | Yes |

## Open Questions

1. **Q**: Should we add `custom_fields.people_value` to `_HIERARCHY_OPT_FIELDS` for Owner cascading?
   **A**: Not required for SC-001 through SC-004, but consider for future expansion.

2. **Q**: Should the fallback in Fix 4 trigger `tasks_client` upgrade if parent not in cache?
   **A**: Not in this fix - would require passing `tasks_client` through DataFrameViewPlugin. Hierarchy warming should handle this.

---

**Handoff to Principal Engineer**: This TDD is ready for implementation. Start with Fix 1 (lowest risk), verify with Test 3, then proceed through Fix 2/3/4 with corresponding tests. The integration test (Test 4) should pass after all fixes are applied.
