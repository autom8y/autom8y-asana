# ADR: Hierarchy Registration Architecture for Cascade Resolution

## Status
Proposed

## Context

The cascade resolution system correctly resolves cascading fields (like `office_phone`) by traversing the parent chain from Unit to UnitHolder to Business. However, in production DataFrame extraction, **all 2616 Units return `None` for `office_phone`** despite:

1. SDK layer correctly fetching `parent.gid` in API responses (confirmed via `_BASE_OPT_FIELDS`)
2. `UnifiedTaskStore.put_async()` and `put_batch_async()` correctly calling `self._hierarchy.register(task)` (lines 432, 497)
3. `CascadeViewPlugin` correctly calling `hierarchy.get_ancestor_chain(gid, max_depth=5)`
4. Manual registration working: `hierarchy.register({"gid": task.gid, "parent": {"gid": parent_gid}})` produces correct chains

### Root Cause Analysis

The data flow during DataFrame extraction is:

```
SDK (list_async)
    |
    v
ProjectDataFrameBuilder._build_with_unified_store_async()
    |
    +--> Fetches tasks from API with _BASE_OPT_FIELDS (includes parent.gid)
    |
    +--> Checks UnifiedTaskStore.get_batch_async() for cached tasks
    |
    +--> On miss: fetches from API, calls put_batch_async() with task_dicts
    |
    v
DataFrameViewPlugin.materialize_async()
    |
    +--> Fetches from UnifiedTaskStore.get_batch_async()
    |
    +--> For cascade: fields, calls store.get_parent_chain_async()
    |
    v
HierarchyIndex.get_ancestor_chain()
    |
    +--> Returns [] because parent relationships not registered
```

**The gap**: When `put_batch_async()` is called at line 539 in `project.py`:

```python
task_dicts = [t.model_dump(exclude_none=True) for t in fetched_tasks]
await self._unified_store.put_batch_async(task_dicts, opt_fields=_BASE_OPT_FIELDS)
```

The `put_batch_async()` calls `self._hierarchy.register(task)` for each task. However, **the hierarchy only stores immediate parent relationships, not the full ancestor chain**. When a Unit task is registered with `{"gid": "unit-123", "parent": {"gid": "unit-holder-456"}}`:

- The hierarchy knows: Unit -> UnitHolder
- But **UnitHolder and Business are never fetched or registered**
- Therefore `get_ancestor_chain("unit-123")` returns `["unit-holder-456"]` and stops because UnitHolder isn't in the hierarchy

The architecture requires **all ancestors to be registered in the hierarchy** before cascade resolution can work.

### Constraints

1. **Asana API does not return full ancestor chains** - Only immediate `parent.gid` is returned
2. **Multiple entity types share hierarchy** - Units, Offers, Contacts all use parent chain resolution
3. **Hierarchy depths vary by entity type**:
   - Unit -> UnitHolder -> Business (3 levels)
   - Offer -> OfferHolder -> Unit -> UnitHolder -> Business (5 levels)
   - Contact -> ContactHolder -> Unit -> UnitHolder -> Business (5 levels)
4. **Performance-critical path** - DataFrame extraction needs <10s latency for 2600 tasks
5. **Existing infrastructure** - `HierarchyIndex`, `UnifiedTaskStore`, `CascadeViewPlugin` are battle-tested

## Decision

Implement **Eager Hierarchy Warming** at the storage layer with recursive parent fetching.

### Approach: Storage-Layer Recursive Registration

Augment `UnifiedTaskStore.put_batch_async()` to recursively fetch and register missing parent tasks up to a configurable depth. The key insight is that **hierarchy registration must be transitive** - when we store a task, we must also ensure its entire ancestor chain is in the hierarchy.

### New Component: HierarchyWarmer

```python
@dataclass
class HierarchyWarmer:
    """Ensures complete ancestor chains for hierarchy-dependent operations.

    When a task is stored, this component:
    1. Extracts parent.gid from the task
    2. Checks if parent exists in hierarchy
    3. If not, fetches parent from API and recursively warms its ancestors
    4. Registers all tasks in hierarchy
    """
    store: "UnifiedTaskStore"
    tasks_client: "TasksClient"
    max_depth: int = 5
    _warming_in_progress: set[str] = field(default_factory=set)  # Cycle detection
```

### Integration Point

Modify `UnifiedTaskStore.put_batch_async()` to optionally accept a `TasksClient` and warm hierarchy:

```python
async def put_batch_async(
    self,
    tasks: list[dict[str, Any]],
    ttl: int | None = None,
    opt_fields: list[str] | None = None,
    tasks_client: "TasksClient | None" = None,  # NEW
    warm_hierarchy: bool = False,               # NEW
) -> int:
    # ... existing code ...

    if warm_hierarchy and tasks_client:
        await self._warm_hierarchy_batch_async(tasks, tasks_client)
```

### Warming Strategy

```python
async def _warm_hierarchy_batch_async(
    self,
    tasks: list[dict[str, Any]],
    tasks_client: "TasksClient",
) -> None:
    """Warm hierarchy by fetching missing ancestors.

    Strategy:
    1. Collect all parent GIDs that aren't in hierarchy
    2. Batch fetch missing parents from API
    3. Recursively warm their ancestors
    4. Register all in hierarchy
    """
    missing_parent_gids: set[str] = set()

    for task in tasks:
        parent = task.get("parent")
        if parent and isinstance(parent, dict):
            parent_gid = parent.get("gid")
            if parent_gid and not self._hierarchy.contains(parent_gid):
                missing_parent_gids.add(parent_gid)

    if not missing_parent_gids:
        return

    # Batch fetch missing parents with parent.gid included
    parent_tasks = await self._fetch_parents_async(
        list(missing_parent_gids),
        tasks_client
    )

    # Store fetched parents (which registers them in hierarchy)
    if parent_tasks:
        await self.put_batch_async(
            parent_tasks,
            opt_fields=_PARENT_OPT_FIELDS,
            tasks_client=tasks_client,
            warm_hierarchy=True,  # Recursive!
        )
```

### Call Site Change

In `ProjectDataFrameBuilder._build_with_unified_store_async()`:

```python
# Current (line 539):
await self._unified_store.put_batch_async(
    task_dicts, opt_fields=_BASE_OPT_FIELDS
)

# New:
await self._unified_store.put_batch_async(
    task_dicts,
    opt_fields=_BASE_OPT_FIELDS,
    tasks_client=client.tasks,  # Pass client
    warm_hierarchy=True,        # Enable warming
)
```

## Alternatives Considered

### Option A: Builder-Layer Warming (Rejected)

Add hierarchy warming in `ProjectDataFrameBuilder` before DataFrame materialization.

**Pros:**
- Localized change
- Clear call site

**Cons:**
- Scattered hierarchy logic across builders (violates SRP)
- Every builder type would need this logic
- Doesn't centralize the invariant "stored tasks have complete hierarchy"

### Option B: SDK-Layer Warming (Rejected)

Augment `TasksClient.list_async()` to automatically fetch parent chains.

**Pros:**
- Single integration point
- Works for all downstream consumers

**Cons:**
- SDK should be thin wrapper around Asana API
- Adds implicit behavior that surprises callers
- Performance overhead for callers who don't need hierarchy
- Violates separation of concerns

### Option C: Lazy Warming in CascadeViewPlugin (Rejected)

Fetch missing parents on-demand during cascade resolution.

**Pros:**
- Only fetches what's needed
- No upfront cost

**Cons:**
- Adds latency during extraction (N+1 query pattern)
- Poor UX: First cascade resolution is slow
- Race conditions in concurrent resolutions
- Complex caching invalidation

### Option D: Pre-Warming Hook (Rejected)

Add a lifecycle hook that warms hierarchy before any cascade-using operation.

**Pros:**
- Flexible integration points
- Opt-in behavior

**Cons:**
- Caller must remember to call hook
- Easy to forget, leading to subtle bugs
- Doesn't guarantee invariant

## Rationale

**Storage-layer warming** is the correct location because:

1. **Centralized invariant enforcement**: The invariant "stored tasks have complete hierarchy" is enforced at the single point of storage
2. **Implicit correctness**: Any caller storing tasks gets hierarchy warming automatically (opt-in via flag, but easy to enable)
3. **Batch-optimized**: Parent fetching can be batched across all tasks being stored
4. **Recursive termination**: Recursion naturally terminates when ancestors are already in hierarchy or max_depth reached
5. **Cache-aware**: Already-cached parents don't trigger API calls
6. **Ecosystem alignment**: Builds on existing `UnifiedTaskStore` + `HierarchyIndex` infrastructure

### Why not lazy?

Lazy warming seems appealing but creates **unpredictable performance**:
- First resolution pays the full warming cost
- Subsequent resolutions are fast
- Users experience inconsistent latency
- Hard to diagnose why some extractions are slow

Eager warming **front-loads the cost** during the fetch phase where users already expect latency.

### Performance Considerations

**Worst case (cold cache, 2600 Units):**
- Each Unit has parent -> UnitHolder -> Business (2 levels up)
- Assume 50 unique UnitHolders, 5 unique Businesses
- Additional API calls: 50 (UnitHolders) + 5 (Businesses) = 55 calls
- At 200ms/call: 11 seconds overhead
- **Mitigation**: Batch parent fetching (10 parents per call with Batch API) = ~5 seconds

**Warm cache:**
- All ancestors already in cache/hierarchy
- Zero additional API calls
- **Expected case after first full extraction**

## Consequences

### Positive
- Cascade resolution works correctly for all entity types
- Single source of truth for hierarchy completeness
- Predictable performance (front-loaded cost)
- Backward compatible (opt-in flag)
- Natural integration with existing ecosystem

### Negative
- Increased complexity in `UnifiedTaskStore`
- Requires passing `TasksClient` to storage layer (mild coupling)
- First extraction incurs hierarchy warming cost
- Requires API quota for parent fetching

### Neutral
- `HierarchyIndex` API unchanged
- `CascadeViewPlugin` logic unchanged
- `ProjectDataFrameBuilder` only passes new parameters

## Implementation Plan

### Phase 1: Core Infrastructure (Estimated: 4 hours)

1. Add `HierarchyWarmer` dataclass to `autom8_asana/cache/hierarchy_warmer.py`
2. Add `_warm_hierarchy_batch_async()` method to `UnifiedTaskStore`
3. Add `tasks_client` and `warm_hierarchy` parameters to `put_batch_async()`
4. Add unit tests for hierarchy warming logic

### Phase 2: Integration (Estimated: 2 hours)

5. Update `ProjectDataFrameBuilder._build_with_unified_store_async()` to pass `tasks_client` and enable warming
6. Update `DataFrameViewPlugin` to pass client through cascade plugin
7. Integration tests verifying cascade resolution works with warming

### Phase 3: Optimization (Estimated: 2 hours)

8. Implement batch parent fetching using Asana Batch API
9. Add metrics/logging for warming operations
10. Performance testing with 2600-task dataset

## Migration Strategy

1. **Phase 1 deployment**: Add infrastructure with `warm_hierarchy=False` default (no behavior change)
2. **Validation**: Enable for single test project, verify cascade resolution
3. **Gradual rollout**: Enable `warm_hierarchy=True` in production
4. **Monitoring**: Track hierarchy warming metrics (API calls, time, depth)
5. **Optimization**: Tune batch sizes based on observed patterns

## Files to Modify

| File | Change |
|------|--------|
| `src/autom8_asana/cache/hierarchy_warmer.py` | NEW: HierarchyWarmer component |
| `src/autom8_asana/cache/unified.py` | Add warming parameters and method |
| `src/autom8_asana/dataframes/builders/project.py` | Pass tasks_client, enable warming |
| `tests/unit/cache/test_hierarchy_warmer.py` | NEW: Unit tests |
| `tests/integration/test_cascade_warming.py` | NEW: Integration tests |

## Related ADRs

- ADR-0054: Cascading Custom Fields (establishes cascade resolution pattern)
- ADR-0116: Batch Cache Population Pattern (batch storage)
- ADR-0130: Cache Population Location (storage layer responsibility)

## Open Items

1. **Batch API quota**: Verify sufficient API quota for warming operations
2. **Cycle detection**: Handle pathological circular parent references (if possible in Asana)
3. **Partial failure**: What happens if some parent fetches fail?
4. **TTL alignment**: Should warmed parents have same TTL as child tasks?
