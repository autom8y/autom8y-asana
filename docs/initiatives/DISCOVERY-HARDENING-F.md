# DISCOVERY-HARDENING-F: SaveSession Reliability

**Initiative**: Architecture Hardening - Initiative F (SaveSession Reliability)
**Phase**: Discovery
**Date**: 2025-12-16
**Status**: COMPLETE
**Prerequisite**: SPIKE-HARDENING-F (GO recommendation, HIGH confidence)

---

## Executive Summary

This discovery document catalogs the current behavior of SaveSession's entity tracking and failure handling, identifies all failure modes, and maps user visibility gaps. The analysis reveals two core issues:

1. **Issue #8: `id()` Identity Bug** - The `ChangeTracker` uses Python object identity (`id(entity)`) for tracking, which breaks when the same Asana resource is fetched multiple times (each fetch creates a new Python object with the same GID but different `id()`).

2. **Issue #1: No Transaction Semantics** - Partial failures occur mid-commit with no rollback capability. Users must manually inspect `SaveResult.failed` to understand what succeeded and what failed.

The spike validated that both issues are addressable with reasonable effort. This discovery provides the requirements foundation for the PRD.

---

## 1. Commit Flow Analysis

### 1.1 High-Level Flow

The commit flow spans four files and five phases:

```
SaveSession.commit_async()
    |
    v
[Phase 1: VALIDATE] --> Check cycles, unsupported modifications
    |
    v
[Phase 2: PREPARE] --> Build operations, assign temp GIDs
    |
    v
[Phase 3: EXECUTE] --> Execute CRUD via BatchExecutor (level by level)
    |
    v
[Phase 4: ACTIONS] --> Execute action operations sequentially
    |
    v
[Phase 5: CONFIRM] --> Update GIDs, reset tracking state
```

### 1.2 Step-by-Step Execution

**Step 1: Entry Point** (`session.py:499-610`)
```python
async def commit_async(self) -> SaveResult:
    self._ensure_open()  # Raises SessionClosedError if closed

    dirty_entities = self._tracker.get_dirty_entities()  # Line 537
    pending_actions = list(self._pending_actions)        # Line 538
    pending_cascades = list(self._cascade_operations)    # Line 539
```
- Gets dirty entities from tracker
- Captures pending actions and cascades
- Returns empty `SaveResult` if nothing to do

**Step 2: Execute CRUD + Actions Together** (`session.py:558-566`)
```python
crud_result, action_results = await self._pipeline.execute_with_actions(
    entities=dirty_entities,
    actions=pending_actions,
    action_executor=self._action_executor,
)
```
- Delegates to `SavePipeline.execute_with_actions()`

**Step 3: Pipeline Validation** (`pipeline.py:573-575`)
```python
if entities:
    self.validate_no_unsupported_modifications(entities)
```
- Checks for direct modifications to `tags`, `projects`, `memberships`, `dependencies`, `followers`
- Raises `UnsupportedOperationError` if found (guides users to action methods)

**Step 4: Build Dependency Graph** (`pipeline.py:187-188`)
```python
self._graph.build(entities)
levels = self._graph.get_levels()
```
- Uses Kahn's algorithm for topological sort
- Groups entities by dependency level (level 0 = no dependencies)
- Raises `CyclicDependencyError` if cycle detected

**Step 5: Level-by-Level Execution** (`pipeline.py:202-262`)
```python
for level_entities in levels:
    # Filter out entities whose dependencies failed
    executable, cascaded_failures = self._filter_executable(
        level_entities, failed_gids, entities
    )

    # Execute this level via BatchExecutor
    level_results = await self._executor.execute_level(operations)

    # Process results - success updates GID map, failure tracks failed_gids
```

**Key Observation**: Operations are executed sequentially by level. If level 0 fails, level 1 entities that depend on level 0 are marked as `DependencyResolutionError` (cascading failure).

**Step 6: Action Execution** (`action_executor.py:53-77`)
```python
for action in actions:
    result = await self._execute_single_action(action, gid_map)
    results.append(result)
```
- Actions execute sequentially (not batched)
- Each action resolves temp GIDs using `gid_map` from CRUD phase
- Failures are captured in `ActionResult` objects

**Step 7: Post-Commit Cleanup** (`session.py:580-608`)
```python
for entity in crud_result.succeeded:
    self._reset_custom_field_tracking(entity)
    self._tracker.mark_clean(entity)
```
- Successful entities marked clean (snapshot updated)
- Session state set to `SessionState.COMMITTED`
- Failed entities remain dirty (can be retried)

### 1.3 What Happens Mid-Commit When Operation Fails

Consider tracking 3 entities: Parent (level 0), Child1 (level 1), Child2 (level 1)

**Scenario**: Parent CREATE fails with 400 error

1. Level 0 executes: Parent fails
2. `failed_gids.add(parent_temp_gid)`
3. Level 1 executes: `_filter_executable()` detects Child1 and Child2 depend on failed Parent
4. Both children added to `cascaded_failures` with `DependencyResolutionError`
5. Neither child is sent to API

**Result**:
- `SaveResult.succeeded = []`
- `SaveResult.failed = [SaveError(Parent, CREATE, ...), SaveError(Child1, ...), SaveError(Child2, ...)]`
- Child1 and Child2 errors show `DependencyResolutionError` with reference to Parent

---

## 2. Entity Identity Analysis (THE CORE BUG - Issue #8)

### 2.1 Current Implementation

The `ChangeTracker` uses Python's `id()` function for entity identity:

**File**: `tracker.py:32-39`
```python
def __init__(self) -> None:
    """Initialize empty tracker state."""
    # id(entity) -> snapshot dict
    self._snapshots: dict[int, dict[str, Any]] = {}
    # id(entity) -> EntityState
    self._states: dict[int, EntityState] = {}
    # id(entity) -> entity (for retrieval)
    self._entities: dict[int, AsanaResource] = {}
```

**Rationale documented in code** (`tracker.py:27-30`):
```python
"""Uses id(entity) for identity to handle entities that may not
have GIDs yet (new entities) or may have duplicate GIDs in
different sessions."""
```

### 2.2 The Bug: Same GID, Different Python Objects

**Reproduction Scenario**:
```python
async with SaveSession(client) as session:
    # Fetch task twice - creates two Python objects with same GID
    task1 = await client.tasks.get_async("12345")
    task2 = await client.tasks.get_async("12345")

    # id(task1) != id(task2) even though both represent same Asana task

    session.track(task1)  # Tracked as id(task1)
    task1.name = "Modified"

    session.track(task2)  # Tracked separately as id(task2)
    task2.notes = "Different change"

    result = await session.commit_async()
    # PROBLEM: Both entities sent as separate UPDATE operations
    # Last write wins, potentially losing task1.name change
```

### 2.3 Why `id()` Was Chosen

The original implementation considered:

1. **New entities have no GID**: Before creation, entities use `temp_xxx` GIDs
2. **Cross-session isolation**: Different sessions shouldn't share entity tracking
3. **Simplicity**: `id()` is always available and unique per Python object

### 2.4 Problems with `id()` Approach

| Problem | Description | Severity |
|---------|-------------|----------|
| Duplicate tracking | Same logical entity tracked multiple times | HIGH |
| Lost changes | Concurrent modifications to same GID overwrite each other | HIGH |
| Memory inefficiency | Multiple snapshots for same logical entity | MEDIUM |
| Confusing errors | User doesn't know which "copy" failed | HIGH |

### 2.5 Entity Refresh Behavior

**Current**: When an entity is re-fetched, it becomes a completely new tracked entity.

**Expected**: Re-fetching should update the existing tracked entity or at minimum warn about duplicate tracking.

### 2.6 Temp GID Lifecycle

**File**: `tracker.py:64-69`
```python
# Determine initial state based on GID
# New entities have no GID or a temp_* GID
gid = entity.gid
if not gid or gid.startswith("temp_"):
    self._states[entity_id] = EntityState.NEW
else:
    self._states[entity_id] = EntityState.CLEAN
```

**File**: `pipeline.py:234-240`
```python
# Update GID map for new entities
if op_type == OperationType.CREATE and batch_result.data:
    temp_gid = f"temp_{id(entity)}"  # Uses id() here too
    real_gid = batch_result.data.get("gid")
    if real_gid:
        gid_map[temp_gid] = real_gid
        object.__setattr__(entity, "gid", real_gid)  # Updates entity's GID
```

**Observation**: The temp GID is derived from `id(entity)`, creating a dependency on Python object identity throughout the system.

---

## 3. Failure Mode Catalog

### 3.1 CRUD Failure Modes

| # | Failure Mode | Trigger | Current Behavior | User Visibility | Recovery Path |
|---|--------------|---------|------------------|-----------------|---------------|
| FM-1 | **Single operation failure** | Invalid payload, permission denied | Operation fails, added to `SaveResult.failed` | `SaveError` with entity, operation type, error | Fix entity and retry commit |
| FM-2 | **Cascading dependency failure** | Parent create fails | Dependents skip execution, added to `failed` with `DependencyResolutionError` | Error shows dependency chain | Fix parent first, then retry |
| FM-3 | **Batch partial failure** | 2 of 5 operations in batch fail | Successful ops committed, failed ops in `SaveResult.failed` | Per-operation errors in `SaveError.error` | Inspect failed, fix, retry |
| FM-4 | **Network failure mid-batch** | Connection drops during batch chunk | Entire chunk fails, state indeterminate | Generic network error | Unknown which ops succeeded - DANGEROUS |
| FM-5 | **Rate limit exhaustion** | Too many operations | 429 response for chunk | `AsanaError` with rate limit info | Wait and retry |
| FM-6 | **Cycle detection** | Parent/child circular reference | Fails before execution | `CyclicDependencyError` with participants | Restructure dependencies |
| FM-7 | **Unsupported field modification** | Direct modification to `tags` field | Fails at validation | `UnsupportedOperationError` with guidance | Use action methods instead |

### 3.2 Action Failure Modes

| # | Failure Mode | Trigger | Current Behavior | User Visibility | Recovery Path |
|---|--------------|---------|------------------|-----------------|---------------|
| FM-8 | **Action target not found** | Tag/project GID doesn't exist | Action fails, `ActionResult.success=False` | `ActionResult.error` | Verify GID, retry |
| FM-9 | **Action permission denied** | No access to target resource | Action fails with 403 | `ActionResult.error` | Request permissions |
| FM-10 | **Temp GID resolution failure** | Action references entity that failed to create | Action uses invalid temp GID | Action fails with 404 | Retry after fixing CRUD |
| FM-11 | **Positioning conflict** | Both `insert_before` and `insert_after` specified | Fails at queue time | `PositioningConflictError` | Remove one parameter |

### 3.3 Session Lifecycle Failure Modes

| # | Failure Mode | Trigger | Current Behavior | User Visibility | Recovery Path |
|---|--------------|---------|------------------|-----------------|---------------|
| FM-12 | **Closed session operation** | track/commit after context exit | Raises `SessionClosedError` | Exception message | Create new session |
| FM-13 | **Double tracking conflict** | Track same Python object twice | Idempotent (ignored) | None - silent | N/A (non-issue) |
| FM-14 | **GID collision (duplicate tracking)** | Track two objects with same GID | Both tracked separately | Confusing - last write wins | **THIS IS THE BUG** |

### 3.4 Pre-commit Validation Failures

| # | Failure Mode | Trigger | Current Behavior | User Visibility | Recovery Path |
|---|--------------|---------|------------------|-----------------|---------------|
| FM-15 | **Invalid GID format** | Entity with malformed GID | `GidValidationError` at track time | Exception with guidance | Fix GID format |
| FM-16 | **Pre-save hook rejection** | Custom hook raises exception | Operation aborts for that entity | Hook's exception | Fix entity per hook logic |

---

## 4. User Visibility Gap Analysis

### 4.1 Partial Failure Visibility

**Gap 1: No Progress Indication**
- **Current**: User waits for entire commit, gets results at end
- **Missing**: No streaming progress during commit
- **Impact**: Long-running commits feel unresponsive

**Gap 2: Cascading Failure Attribution**
- **Current**: `DependencyResolutionError` shows immediate parent
- **Missing**: Full dependency chain to root cause
- **Impact**: User must trace chain manually

**Gap 3: Network Failure State Uncertainty**
- **Current**: Network failure aborts chunk, unclear what succeeded
- **Missing**: Idempotency keys or transaction log
- **Impact**: User may have partial state in Asana with no local record

### 4.2 Recovery Guidance Gaps

**Gap 4: No Retry Guidance**
- **Current**: `SaveError` contains error, no retry advice
- **Missing**: `is_retryable`, `retry_after`, `suggested_action`
- **Impact**: User must interpret Asana errors themselves

**Gap 5: No Entity State After Failure**
- **Current**: Failed entities remain "dirty" in tracker
- **Missing**: API to get "what failed" entities for retry
- **Impact**: User must remember/track what failed

**Gap 6: Action Failure Independence**
- **Current**: Action failures don't affect CRUD success reporting
- **Missing**: Clear correlation between CRUD and dependent actions
- **Impact**: User may not realize action failed because CRUD succeeded

### 4.3 Documentation Gaps

**Gap 7: Partial Success Handling Not Documented**
- **Current**: No guide on handling `SaveResult.partial == True`
- **Missing**: Best practices for partial failure recovery

**Gap 8: Entity Identity Behavior Not Documented**
- **Current**: `id()` tracking is implementation detail
- **Missing**: Warning about duplicate tracking of same GID

**Gap 9: Failure Mode Catalog Not Exposed**
- **Current**: Users discover failure modes through trial and error
- **Missing**: Comprehensive error handling guide

### 4.4 Visibility Matrix

| What User Needs to Know | Currently Visible | Where |
|-------------------------|-------------------|-------|
| Which operations succeeded | Yes | `SaveResult.succeeded` |
| Which operations failed | Yes | `SaveResult.failed` |
| Why each operation failed | Partial | `SaveError.error` (may be generic) |
| What payload was attempted | Yes | `SaveError.payload` |
| Dependency failure chain | Partial | Only immediate parent shown |
| Whether error is retryable | No | - |
| What to do next | No | - |
| Action results | Yes | `SaveResult.action_results` |
| Cascade results | Yes | `SaveResult.cascade_results` |

---

## 5. Spike Findings Integration

### 5.1 GID-Based Entity Identity (POC Validated)

The spike (`SPIKE-HARDENING-F.md`) demonstrated a `GidBasedTracker` prototype:

**Key Design Points**:
```python
class GidBasedTracker:
    # Primary storage: GID/temp_GID -> entity reference
    self._entities: dict[str, AsanaResource] = {}
    # Maps temp_gid -> real_gid after creation
    self._gid_transitions: dict[str, str] = {}

    def _get_key(self, entity: AsanaResource) -> str:
        """GID when available, __id_{id} for GID-less entities"""
        gid = getattr(entity, 'gid', None)
        if gid:
            return gid  # Works for real and temp_ GIDs
        return f"__id_{id(entity)}"  # Fallback only
```

**Benefits Validated**:
1. Deduplicates re-fetched entities automatically
2. `find_by_gid()` enables lookup by business identity
3. Same public API (track, untrack, get_state)
4. Performance: O(1) lookup preserved

**Implementation Complexity**: LOW - straightforward replacement

### 5.2 Partial Failure Breakdown (Already Implemented)

The spike confirmed the current implementation **already provides** complete partial failure information:

**Per-Operation Tracking** (`pipeline.py:229-261`):
```python
for entity, op_type, batch_result in level_results:
    if batch_result.success:
        all_succeeded.append(entity)
        # ... update GID map, emit post-save
    else:
        all_failed.append(SaveError(
            entity=entity,
            operation=op_type,
            error=batch_result.error or Exception("Unknown batch error"),
            payload=payload,
        ))
        failed_gids.add(self._get_entity_gid(entity))
```

**What's Already Available**:
- `SaveResult.succeeded`: List of entities that saved
- `SaveResult.failed`: List of `SaveError` with full details
- `SaveResult.partial`: Boolean indicating mixed results
- `SaveResult.action_results`: Per-action success/failure
- `SaveError.payload`: Exact data that was sent

**What's Missing**: Helper methods for common queries (retryable errors, grouped by error type, etc.)

### 5.3 Spike Recommendations

| Recommendation | Status | PRD Impact |
|----------------|--------|------------|
| Implement `GidBasedTracker` | Ready | Core requirement |
| Expose partial failure details | Already done | Document existing API |
| Add `find_by_gid()` capability | New feature | Nice-to-have requirement |
| Consider retry mechanism | Future | Out of scope for F |
| Consider idempotency keys | Future | Out of scope for F |

---

## 6. Requirements Themes for PRD

Based on this discovery, the PRD should address the following themes:

### Theme 1: Entity Identity Migration (MUST HAVE)

**Problem**: `id()` tracking causes duplicate entity handling, lost changes, and confusing errors.

**Requirements**:
- R-ID-001: Replace `ChangeTracker` with GID-based tracking
- R-ID-002: Handle temp GID to real GID transitions
- R-ID-003: Detect and prevent duplicate GID tracking
- R-ID-004: Maintain backward-compatible public API

### Theme 2: Failure Visibility Enhancement (SHOULD HAVE)

**Problem**: Users have raw data but lack actionable guidance.

**Requirements**:
- R-VIS-001: Add `is_retryable` property to `SaveError`
- R-VIS-002: Add `get_failed_entities()` convenience method
- R-VIS-003: Enhance `DependencyResolutionError` with full chain
- R-VIS-004: Document partial failure handling patterns

### Theme 3: Entity Lookup Capability (COULD HAVE)

**Problem**: No way to look up tracked entity by GID.

**Requirements**:
- R-LOOK-001: Add `session.get_by_gid(gid)` method
- R-LOOK-002: Add `session.is_tracked(gid)` method

### Theme 4: Documentation (MUST HAVE)

**Problem**: Failure modes and best practices undocumented.

**Requirements**:
- R-DOC-001: Document entity identity behavior
- R-DOC-002: Document partial failure handling
- R-DOC-003: Create error handling guide with failure mode catalog

---

## 7. Open Questions for PRD

| # | Question | Context | Suggested Answer |
|---|----------|---------|------------------|
| OQ-1 | Should duplicate GID tracking raise an error or silently update? | UX decision | Silently update (merge) - matches ORM behavior |
| OQ-2 | Should `find_by_gid()` return None or raise for missing? | API style | Return None - consistent with dict.get() |
| OQ-3 | Should failed actions affect `SaveResult.success` property? | Current: Yes (line 146) | Keep current - total success requires all phases |
| OQ-4 | Should we add retry helper methods in this initiative? | Scope control | Defer - separate enhancement |
| OQ-5 | What happens to cascades when CRUD fails? | Current: Cascades execute anyway | Fix - skip cascades if CRUD failed |
| OQ-6 | Should temp GID format change from `temp_{id}` to `temp_{uuid}`? | GID-based tracking makes `id()` less central | Keep `temp_{id}` for now - simpler |

---

## 8. Files Examined

| File | Location | Key Insights |
|------|----------|--------------|
| `tracker.py` | `persistence/tracker.py` | Core `id()` tracking implementation (lines 32-39) |
| `session.py` | `persistence/session.py` | Full commit flow, action/cascade coordination |
| `pipeline.py` | `persistence/pipeline.py` | Level-by-level execution, cascading failures |
| `executor.py` | `persistence/executor.py` | BatchExecutor correlation logic |
| `action_executor.py` | `persistence/action_executor.py` | Sequential action execution |
| `graph.py` | `persistence/graph.py` | Dependency ordering, cycle detection |
| `models.py` | `persistence/models.py` | SaveResult, SaveError, ActionResult |
| `exceptions.py` | `persistence/exceptions.py` | Exception hierarchy |
| `events.py` | `persistence/events.py` | Hook system |
| `batch/client.py` | `batch/client.py` | Chunking, per-operation results |
| `SPIKE-HARDENING-F.md` | `docs/initiatives/` | Feasibility validation, POC code |

---

## 9. Session Metadata

- **Analyst**: Requirements Analyst (Claude)
- **Duration**: 1 session
- **Spike Reference**: SPIKE-HARDENING-F (GO, HIGH confidence)
- **Next Step**: Create PRD-HARDENING-F based on requirements themes

---

## Appendix A: Code Examples Demonstrating the Bug

### A.1 Duplicate Tracking Bug

```python
# CURRENT BUGGY BEHAVIOR
async with SaveSession(client) as session:
    task_a = await client.tasks.get_async("12345")
    task_b = await client.tasks.get_async("12345")  # Same GID!

    session.track(task_a)
    session.track(task_b)  # Tracked separately - BUG

    task_a.name = "Name from A"
    task_b.notes = "Notes from B"

    result = await session.commit_async()
    # Two UPDATE operations sent for same task
    # Race condition: which wins?
    # User loses either name OR notes change
```

### A.2 Expected Behavior After Fix

```python
# DESIRED BEHAVIOR (after GID-based tracking)
async with SaveSession(client) as session:
    task_a = await client.tasks.get_async("12345")
    task_b = await client.tasks.get_async("12345")

    session.track(task_a)
    session.track(task_b)  # Detects same GID, updates reference

    task_a.name = "Name from A"
    task_b.notes = "Notes from B"  # Modifies same tracked entity

    result = await session.commit_async()
    # Single UPDATE with both changes
    # No data loss
```

### A.3 Cascading Failure Example

```python
async with SaveSession(client) as session:
    parent = Task(gid="temp_1", name="Parent")
    child = Task(gid="temp_2", name="Child", parent=parent)

    session.track(parent)
    session.track(child)

    # Simulate: parent creation fails (invalid project)
    result = await session.commit_async()

    # Current result:
    assert len(result.failed) == 2

    parent_error = result.failed[0]
    assert parent_error.operation == OperationType.CREATE
    assert "project" in str(parent_error.error)  # Root cause

    child_error = result.failed[1]
    assert isinstance(child_error.error, DependencyResolutionError)
    assert child_error.error.dependency is parent  # Shows immediate parent only
```
