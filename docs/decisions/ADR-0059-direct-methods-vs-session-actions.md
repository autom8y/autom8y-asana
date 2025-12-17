# ADR-0059: Direct Methods vs. SaveSession Actions

**Date:** 2025-12-12
**Status:** Approved
**Context:** SDK Usability Overhaul (Session 3)
**References:** PRD-SDKUX, DISCOVERY-SDKUX-001 (lines 28-36)

---

## Context and Problem

The SDK currently requires explicit `SaveSession` context for all operations:

```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    session.add_tag(task.gid, tag_gid)
    await session.commit_async()
```

This creates friction for simple single-task operations. We need to decide: should we add convenience methods to **TasksClient** (direct methods that wrap SaveSession internally), or should we enhance **SaveSession** with new action methods?

**Two Options:**

1. **Direct Methods (chosen)**: Add `add_tag_async()`, `remove_tag_async()`, etc. to TasksClient
   - Pros: Clear API surface, users think "TasksClient", short-lived sessions
   - Cons: Code duplication between method wrappers and SaveSession methods

2. **SaveSession Enhancement**: Add new action methods directly to SaveSession
   - Pros: Single source of truth for all operations
   - Cons: Obscures implicit session lifecycle, unclear when to use SaveSession vs standalone method

---

## Decision

**Implement Direct Methods on TasksClient** - add convenience methods that internally create and manage `SaveSession` instances.

### Implementation

```python
# In TasksClient
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task (convenience method)."""
    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)
        session.track(task)
        session.add_tag(task.gid, tag_gid)
        result = await session.commit_async()

        if not result.success:
            raise result.failed[0].error

        return task

@sync_wrapper("add_tag_async")
def add_tag(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task (sync wrapper)."""
    ...
```

**Pattern applied to all P1 methods:**
- `add_tag_async()`, `add_tag()`
- `remove_tag_async()`, `remove_tag()`
- `move_to_section_async()`, `move_to_section()`
- `set_assignee_async()`, `set_assignee()`
- `add_to_project_async()`, `add_to_project()`
- `remove_from_project_async()`, `remove_from_project()`

### SaveSession Remains Unchanged

SaveSession continues to support:
- Explicit batch operations: `async with SaveSession(client) as session:`
- Multiple operations: `session.add_tag()`, `session.move_to_section()`, etc.
- Full control over commit lifecycle

This coexistence supports both use cases:
- **Simple case**: `await client.tasks.add_tag_async(task_gid, tag_gid)` (1 line)
- **Batch case**: SaveSession context manager (5+ lines, full control)

---

## Rationale

### Why Direct Methods (not SaveSession enhancement)?

1. **Clear API Hierarchy**
   - Users naturally think "I want to add a tag, so I use TasksClient.add_tag_async()"
   - Not "I need to create a SaveSession first, then use SaveSession.add_tag()"

2. **Scope Management**
   - Direct methods create short-lived sessions (scoped to single operation)
   - SaveSession explicit context manager manages long-lived sessions (batch ops)
   - Clear visual distinction in code

3. **Backward Compatibility**
   - SaveSession methods unchanged
   - Existing code using `async with SaveSession()` continues working
   - New convenience methods are pure additions

4. **Implementation Evidence** (DISCOVERY lines 28-36)
   - TasksClient already returns Task objects from all methods (get_async, create_async, update_async)
   - Pattern is established: async method + @sync_wrapper
   - Can reuse existing infrastructure

5. **Type Safety**
   - Return type is Task (not SaveResult)
   - Simpler than returning SaveResult and requiring users to check .success
   - Matches user expectation: "I called add_tag, I get a task back"

### Why Not SaveSession Enhancement?

1. **Session Lifecycle Confusion**
   - Direct method: Session auto-created/destroyed, user doesn't think about it
   - SaveSession enhancement: Would obscure when/why to use it

2. **Batch vs Single Operation**
   - SaveSession is designed for batch (multiple operations in one transaction)
   - Single operations via SaveSession feel awkward (create session → 1 operation → commit)
   - Direct methods align intent with action

3. **Future Flexibility**
   - If SaveSession is enhanced, how do users choose between:
     - SaveSession.add_tag() (for batch)
     - New SaveSession.add_tag_single() (for single)
   - Direct methods avoid this confusion

---

## Consequences

### Positive

1. **Reduced Ceremony**: Single-operation code drops from 5+ lines to 1 line
2. **Lower Learning Curve**: New users can use TasksClient methods without understanding SaveSession
3. **Clear Intent**: Code reads naturally ("add this tag to this task")
4. **Backward Compatible**: All existing SaveSession code continues working
5. **Type Safe**: Return Task objects, not SaveResult

### Negative

1. **Code Duplication**: Direct methods wrap SaveSession methods (small amount of boilerplate)
   - Mitigation: Each method is 4-5 lines; reusable pattern template

2. **Two Patterns**: Users must learn both TasksClient direct methods AND SaveSession for batch ops
   - Mitigation: Documentation clarifies when to use each pattern

3. **Short-lived Sessions**: Direct methods create/destroy SaveSession per operation
   - Mitigation: Negligible overhead; session is lightweight container
   - For batch: Use SaveSession explicitly

### Neutral

1. **No Change to SaveSession API**: Existing methods unchanged, behavior identical
2. **No New Infrastructure**: Uses existing SaveSession, sync_wrapper, change tracking

---

## Alternatives Considered

### Alternative 1: SaveSession Enhancement Only

```python
# Hypothetical - NOT CHOSEN
async with SaveSession(client) as session:
    task = await session.add_tag_single(task_gid, tag_gid)
```

**Rejected because:**
- Obscures implicit vs explicit session lifecycle
- Users must create SaveSession even for single operations
- Batch and single operations feel like different APIs

### Alternative 2: Hybrid Approach (Both SaveSession and Direct Methods)

**Chosen hybrid:**
- Direct methods on TasksClient (convenience)
- SaveSession methods unchanged (power)
- Both coexist, no conflict

This is what we're implementing. Users choose:
- 1-line for simple ops: `await client.tasks.add_tag_async(...)`
- Batch for complex ops: `async with SaveSession(client) as session:`

---

## Implementation Notes

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

1. **Add async methods** (6 methods, ~30 lines total)
   - Each follows pattern: create SaveSession → fetch task → track → queue op → commit

2. **Add sync wrappers** (6 methods via @sync_wrapper decorator)
   - Each uses `@sync_wrapper("async_method_name")`

3. **Error handling**
   - APIError propagated if task/tag doesn't exist
   - PartialSaveError raised if commit fails

4. **Return type**
   - All return Task (not SaveResult)
   - Task instance modified in-place by SaveSession.commit_async()

### No Changes Required

- SaveSession.py (unchanged)
- Task model (unchanged for P1; enhanced in P4)
- CustomFieldAccessor (unchanged for P1; enhanced in P2)
- Exception hierarchy (unchanged for P1; enhanced in P3)

---

## Verification

### Tests Required

1. **Test add_tag_async**
   - Returns Task object
   - Task has updated state (tag added)
   - SaveSession created/destroyed internally

2. **Test add_tag (sync wrapper)**
   - Delegates to add_tag_async
   - Returns Task object

3. **Test error propagation**
   - APIError raised if task doesn't exist
   - APIError raised if tag doesn't exist
   - PartialSaveError raised if commit fails

4. **Test sync/async consistency**
   - Both versions produce identical results
   - Both versions handle errors identically

### Backward Compatibility

- All existing SaveSession tests pass (unchanged SaveSession)
- All existing TasksClient methods work (not modified)
- New methods are pure additions (no breaking changes)

---

## Decision Record

**Decision:** Implement Direct Methods on TasksClient (not SaveSession enhancement)

**Decided by:** Architect (Session 3)

**Approval:** PRD-SDKUX approved (Session 2)

**Implementation Timeline:** Session 4 (P1 Priority)

---

## Related ADRs

- ADR-0061: Implicit SaveSession Lifecycle (how Task.save() uses SaveSession)
- ADR-0035: Unit of Work Pattern (SaveSession design)

---
