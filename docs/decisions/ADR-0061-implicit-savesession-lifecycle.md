# ADR-0061: Implicit SaveSession Lifecycle

**Date:** 2025-12-12
**Status:** Approved
**Context:** SDK Usability Overhaul - Auto-tracking (P4, Session 3)
**References:** PRD-SDKUX, DISCOVERY-SDKUX-001 (lines 207-274)

---

## Context and Problem

P4 (Auto-tracking) adds `Task.save()` and `Task.save_async()` methods. These need to persist task changes without requiring explicit SaveSession.

**Problem:** How should `Task.save_async()` manage SaveSession lifecycle?

**Three Options:**

1. **Create & Destroy Within Method (chosen)**: SaveSession created at method start, destroyed at method end
2. **Reuse Ambient SaveSession**: Check if running inside SaveSession context, use it if available
3. **User-Managed Session**: Require user to pass session or manage separately

---

## Decision

**Create & Destroy Within Method** - Each `Task.save_async()` call creates a fresh SaveSession, scoped to that method invocation.

### Implementation

```python
async def save_async(self) -> Task:
    """Save changes to this task using implicit SaveSession (async)."""
    if self._client is None:
        raise ValueError("Cannot save task without client reference")

    from autom8_asana.persistence.session import SaveSession

    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()

        if not result.success:
            raise result.failed[0].error

        return self
```

---

## Rationale

### Why Create & Destroy Within Method?

1. **Clear Scope**: SaveSession lifetime = save_async() invocation
2. **No Nesting Issues**: Can't accidentally nest SaveSession contexts
3. **Simple Error Handling**: Failure is immediate and unambiguous
4. **Consistency**: Same pattern as P1 direct methods
5. **Backward Compatible**: SaveSession explicit context manager unchanged
6. **Type Safe**: Return Task (not SaveResult with status checking)

### Why Not Reuse Ambient SaveSession?

1. **Surprising Behavior**: Ambiguous whether changes are committed immediately or deferred
2. **Nesting Complexity**: Unclear how outer session interacts with implicit save
3. **Breaking Change Risk**: Refactoring to add SaveSession context changes behavior silently

### Why Not User-Managed Session?

1. **Defeats Purpose**: Requires passing session everywhere
2. **Optional Parameter Confusion**: Same call, different behavior
3. **Not What Users Expect**: Task.save() suggests "just save this object"

---

## Consequences

### Positive

1. **Simple Mental Model**: "call save(), task is saved immediately"
2. **No Nesting Issues**: Can't accidentally nest SaveSession contexts
3. **Clear Error Semantics**: Failure is immediate and unambiguous
4. **Consistency**: Same pattern as P1 direct methods
5. **Backward Compatible**: SaveSession explicit context manager unchanged

### Negative

1. **Per-Call Overhead**: SaveSession created/destroyed for each save_async() call
   - Mitigation: Overhead is minimal (container creation)

2. **No Batch Save**: Can't bundle multiple task.save() calls in one SaveSession
   - Mitigation: Document recommendation for batch operations

3. **Implicit Session Hidden from User**: Users can't observe session behavior
   - Mitigation: Documented in Task.save_async() docstring

---

## Implementation Notes

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

1. **Add _client attribute**
   - `_client: Any = PrivateAttr(default=None)`

2. **Add save_async() method** (~15 lines)
   - Check _client not None
   - Create SaveSession
   - Track, commit, return

3. **Add save() method** (~2 lines)
   - Use @sync_wrapper("save_async")

4. **Add refresh_async() method** (~15 lines)
   - Fetch latest via get_async()
   - Update all fields
   - Clear custom field modifications

5. **Add refresh() method** (~2 lines)
   - Use @sync_wrapper("refresh_async")

**Integration with TasksClient:**
- Update get_async(), create_async(), update_async() to assign task._client

---

## Verification

### Tests Required

1. **Task.save_async()** - persists changes, custom fields, error handling
2. **Task.save()** - sync wrapper works
3. **Task.refresh_async()** - fetches latest, updates fields
4. **Task.refresh()** - sync wrapper works
5. **Integration** - custom field changes persisted in save
6. **Backward Compat** - SaveSession unchanged, all existing tests pass

---

## Decision Record

**Decision:** Create & Destroy SaveSession Within Task.save_async()

**Decided by:** Architect (Session 3)

**Rationale:** Clear scope, no nesting issues, simple semantics, consistent with P1

**Implementation Timeline:** Session 6a (P4 Priority, after P2)

---

## Related ADRs

- ADR-0059: Direct Methods vs SaveSession Actions (P1 uses implicit sessions)
- ADR-0062: CustomFieldAccessor Enhancement vs Wrapper (P2 custom fields)
- ADR-0035: Unit of Work Pattern (SaveSession design)

---
