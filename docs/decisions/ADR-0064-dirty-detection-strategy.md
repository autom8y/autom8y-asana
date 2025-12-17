# ADR-0064: Dirty Detection Strategy

**Date:** 2025-12-12
**Status:** Approved
**Context:** SDK Usability Overhaul - Auto-tracking (P4, Session 3)
**References:** PRD-SDKUX, DISCOVERY-SDKUX-001 (lines 207-274)

---

## Context and Problem

P4 (Auto-tracking) requires Task.save_async() to detect which fields have changed:

```python
task = await client.tasks.get(task_gid)
task.name = "Updated"
task.custom_fields["Priority"] = "High"
await task.save_async()  # Detects both changes
```

**Problem:** Should Task maintain its own dirty flag, or leverage SaveSession's change tracking?

**Three Options:**

1. **Leverage SaveSession ChangeTracker (chosen)**: SaveSession.track() snapshots state, detects diffs
2. **Task-Level Dirty Flag**: Task tracks `__setattr__()` to mark dirty
3. **Hybrid**: Task tracks fields, SaveSession validates

---

## Decision

**Leverage SaveSession ChangeTracker** - No new dirty tracking in Task. Use existing SaveSession snapshot-based mechanism.

### Implementation

```python
# In Task.save_async() (NO dirty flag in Task)
async def save_async(self) -> Task:
    """Save changes to this task."""
    if self._client is None:
        raise ValueError("Task has no client reference")

    from autom8_asana.persistence.session import SaveSession

    async with SaveSession(self._client) as session:
        # ChangeTracker automatically snapshots task state here
        session.track(self)

        # ChangeTracker compares snapshot to current state
        # Only modified fields included in API payload
        result = await session.commit_async()

        if not result.success:
            raise result.failed[0].error

        return self
```

**No changes needed to Task model** - SaveSession handles all dirty detection.

---

## Rationale

### Why Leverage SaveSession?

1. **Already Implemented**
   - SaveSession.ChangeTracker captures snapshot at track() time (DISCOVERY line 241)
   - At commit_async(), compares snapshot vs current state
   - Only differences included in API payload

2. **Proven Pattern**
   - Used throughout codebase for SaveSession batches
   - Thoroughly tested
   - No regressions

3. **Handles Complex Changes**
   - Field changes: `task.name = "Updated"`
   - Custom field changes: Detected via CustomFieldAccessor._modifications
   - Nested object changes: SaveSession handles

4. **No-op Optimization Built-In**
   - If nothing changed since track(), commit() succeeds with 0 API calls
   - SaveSession._pipeline.execute() skips unchanged entities

5. **Single Source of Truth**
   - One change detection mechanism (SaveSession)
   - Not duplicated across Task
   - Easier to maintain and test

6. **Custom Fields Automatic**
   - Task.save_async() doesn't need special logic for custom fields
   - CustomFieldAccessor.has_changes() already tracked
   - SaveSession includes modifications automatically

### Why Not Task-Level Dirty Flag?

1. **Duplication**
   - SaveSession already tracks changes
   - Task dirty flag would duplicate logic
   - Maintenance burden

2. **Custom Fields Complexity**
   ```python
   # How does Task know about custom field changes?
   task.custom_fields["Priority"] = "High"
   # CustomFieldAccessor changed, but Task didn't
   # Would need Task.__setattr__() to monitor _custom_fields_accessor
   # Fragile and complex
   ```

3. **Pydantic Interaction**
   - Task uses Pydantic BaseModel
   - Overriding __setattr__ has implications for Pydantic internals
   - Risk of breaking model_validate, model_dump, etc.

4. **Unnecessary Overhead**
   - Task tracks dirty (set flag in __setattr__)
   - SaveSession tracks dirty (snapshot comparison)
   - Double work

### Why Not Hybrid?

1. **Adds Complexity**
   - No benefit over pure SaveSession approach
   - Task would track fields, SaveSession would validate
   - Still need snapshot comparison for correctness

2. **Performance No Better**
   - Hybrid: Task.__setattr__ + SaveSession comparison
   - Pure SaveSession: Just comparison
   - Pure approach is faster

---

## Consequences

### Positive

1. **No New Code in Task**: Dirty detection entirely in SaveSession
2. **No Custom __setattr__**: Avoid Pydantic interaction issues
3. **Works for Custom Fields**: Changes detected automatically
4. **No-op Optimized**: Free optimization if nothing changed
5. **Proven Pattern**: SaveSession change tracking thoroughly tested
6. **Simpler Implementation**: ~15 lines in save_async(), no logic needed

### Negative

1. **Implicit Behavior**: Users don't see dirty tracking
   - Mitigation: Documented in save_async() docstring
   - Typical case: Users don't need to think about it

2. **Only Works in SaveSession**: Can't query task.is_dirty() outside SaveSession
   - Mitigation: No requirement for is_dirty() property
   - If needed: Can add in future

### Neutral

1. **SaveSession Required**: save_async() creates SaveSession internally
   - Expected; this is how implicit sessions work (ADR-0061)

---

## Implementation Details

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

**No changes to Task model** - Just implement save_async() to use SaveSession:

```python
async def save_async(self) -> Task:
    """Save changes to this task."""
    if self._client is None:
        raise ValueError("Task has no client reference")

    from autom8_asana.persistence.session import SaveSession

    async with SaveSession(self._client) as session:
        session.track(self)  # Snapshot current state
        # Changes detected automatically at commit time
        result = await session.commit_async()

        if not result.success:
            raise result.failed[0].error

        return self
```

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`

**No changes needed** - ChangeTracker already implements snapshot-based dirty detection.

---

## How It Works

1. **User modifies task**
   ```python
   task.name = "Updated"
   task.custom_fields["Priority"] = "High"
   ```

2. **User calls save_async()**
   ```python
   async with SaveSession(self._client) as session:
       session.track(self)  # Snapshot captured here
       # At this point: old_state = copy of task fields
   ```

3. **SaveSession tracks changes at commit time**
   ```python
   result = await session.commit_async()
   # Internally: ChangeTracker.get_changes(task) compares old_state vs new_state
   # Returns: {"name": ("Old", "Updated"), "custom_fields": {...}}
   ```

4. **Only changed fields sent to API**
   ```python
   # SavePipeline builds UPDATE payload with only changed fields
   # Custom field changes included via CustomFieldAccessor._modifications
   ```

5. **Task updated in-place**
   ```python
   # SaveSession.commit_async() updates task._state after API responds
   return self  # Task instance now reflects API state
   ```

---

## Testing Strategy

### Tests Required

1. **Field Change Detection**
   - Modify field: Verify included in API payload
   - Multiple fields: All included

2. **Custom Field Detection**
   - Modify custom field via __setitem__: Included in payload
   - Multiple custom fields: All included

3. **No-op Optimization**
   - Call save_async() with no changes
   - Verify commit succeeds with 0 API calls (mocked HTTP)

4. **Mixed Changes**
   - Modify field + custom field: Both included

5. **Refresh Clears Pending**
   - Modify field
   - Call refresh_async()
   - Verify pending changes discarded

---

## Alternatives Considered

### Alternative 1: Task-Level Dirty Flag

```python
# NOT CHOSEN
class Task(AsanaResource):
    _dirty: bool = PrivateAttr(default=False)

    def __setattr__(self, name, value):
        if not name.startswith("_") and value != getattr(self, name, None):
            self._dirty = True
        super().__setattr__(name, value)

    async def save_async(self) -> Task:
        if not self._dirty:
            return self  # No-op
        # Proceed with save
```

**Rejected because:**
- Duplicates SaveSession change tracking
- Custom field changes not detected (would need _custom_fields_accessor monitoring)
- Pydantic interaction risk
- More complex than leveraging SaveSession

### Alternative 2: Hybrid (Task tracks, SaveSession validates)

```python
# NOT CHOSEN
class Task:
    _dirty_fields: set[str] = PrivateAttr(default_factory=set)

    def __setattr__(self, name, value):
        if not name.startswith("_"):
            self._dirty_fields.add(name)
        super().__setattr__(name, value)

    async def save_async(self) -> Task:
        async with SaveSession(self._client) as session:
            session.track(self)
            # SaveSession still does comparison to verify
            result = await session.commit_async()
            self._dirty_fields.clear()
            return self
```

**Rejected because:**
- Adds Task complexity without benefit
- SaveSession still does comparison (redundant)
- Custom fields not tracked
- Harder to maintain (two tracking mechanisms)

---

## Decision Record

**Decision:** Leverage SaveSession ChangeTracker (no Task-level dirty flag)

**Decided by:** Architect (Session 3)

**Rationale:** SaveSession change tracking already proven, avoids duplication, handles custom fields

**Implementation Timeline:** Session 6a (P4 Priority, integrated into save_async)

**Future Extensions:** If is_dirty() property needed, can add in P4.1 by wrapping SaveSession.get_changes()

---

## Related ADRs

- ADR-0061: Implicit SaveSession Lifecycle (uses ChangeTracker for dirty detection)
- ADR-0035: Unit of Work Pattern (ChangeTracker snapshot implementation)

---
