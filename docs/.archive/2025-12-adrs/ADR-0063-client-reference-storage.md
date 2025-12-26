# ADR-0063: Client Reference Storage

**Date:** 2025-12-12
**Status:** Approved
**Context:** SDK Usability Overhaul - Auto-tracking (P4, Session 3)
**References:** PRD-SDKUX, DISCOVERY-SDKUX-001 (lines 153-204)

---

## Context and Problem

P4 (Auto-tracking) requires Task.save_async() to access the client:

```python
task = await client.tasks.get(task_gid)
await task.save_async()  # Needs to know which client to use
```

**Problem:** How should Task store the client reference? Two Options:

1. **Strong Reference (chosen)**: Store `_client: Any = PrivateAttr(default=None)`
2. **WeakReference**: Store `_client_ref = weakref.ref(client)`

---

## Decision

**Strong Reference** - Store client as regular PrivateAttr, not WeakReference.

### Implementation

```python
from typing import TYPE_CHECKING, Any
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

class Task(AsanaResource):
    _client: Any = PrivateAttr(default=None)

# In TasksClient methods
async def get_async(self, task_gid: str, ...) -> Task:
    data = await self._http.get(f"/tasks/{task_gid}", ...)
    task = Task.model_validate(data)
    task._client = self._client  # Store strong reference
    return task
```

---

## Rationale

### Why Strong Reference?

1. **Simple Implementation**
   - Standard Python object assignment
   - No weakref.ref() complexity
   - Pydantic PrivateAttr pattern already established (task.py line 115: _custom_fields_accessor)

2. **Acceptable Memory Impact**
   - Tasks are typically short-lived (created, used, discarded)
   - Client is lightweight container (1-2 KB)
   - Not a long-term memory accumulation

3. **No Circular Reference Issue**
   - Client has clients (TasksClient, etc.), not Task instances
   - Task → Client link is one-way, not circular
   - SaveSession already holds client reference without issues

4. **No Performance Impact**
   - Reference assignment is O(1)
   - No cleanup overhead (Python GC handles it)

5. **Simpler Error Handling**
   - Can directly access client: `self._client.tasks.get_async()`
   - No need to check if weakref is still alive

6. **Pattern Already in Codebase** (DISCOVERY lines 153-204)
   - Task has `_custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)`
   - SaveSession stores client reference: `self._client = client`
   - Established pattern in codebase

### Why Not WeakReference?

1. **Unnecessary Complexity**
   - Must check if reference still alive: `client = self._client_ref()`
   - Error handling: What if client was GC'd? (shouldn't happen in practice)

2. **Not Solving Real Problem**
   - Client is not GC'd while task is in use
   - Tasks are short-lived; client lives for app duration
   - Weak reference prevents nothing here

3. **Performance Overhead**
   - WeakRef creation: Extra object
   - WeakRef access: Function call instead of attribute access
   - Minimal but unnecessary overhead

4. **Debugging Difficulty**
   - Weak references are less visible in debuggers
   - String representation unhelpful: `<weakref at 0x...>`

---

## Consequences

### Positive

1. **Simple**: Standard Python assignment
2. **Fast**: O(1) access, no weakref dereferencing
3. **Familiar**: Pattern matches _custom_fields_accessor in Task
4. **Backward Compatible**: PrivateAttr not serialized, no API impact
5. **Type Safe**: Can use TYPE_CHECKING for imports

### Negative

1. **Keeps Client Alive**: Task holds strong reference to client
   - Mitigation: Tasks are short-lived; client lives for app duration anyway
   - Typical case: Task created, used, discarded in milliseconds

2. **Potential Memory Waste**: If tasks accumulate without being GC'd
   - Mitigation: Tasks are typically not accumulated
   - If user does: `tasks = [await client.tasks.get(gid) for gid in gids]`
   - Can add docs warning about this

### Neutral

1. **Upgrade Path**: Can switch to WeakRef in future if needed
   - Not a breaking change (internal implementation detail)

---

## Future Optimization Path

If memory becomes issue (unlikely):

1. **Add WeakRef Option**
   ```python
   task._client = weakref.ref(client)

   # In save_async()
   client = self._client_ref()
   if client is None:
       raise RuntimeError("Client was garbage collected")
   ```

2. **Add Pooling/Reuse**
   - Task cache with TTL
   - Task object reuse (advanced)

3. **Lazy Loading**
   - Fetch client on first save_async() call
   - Not before

**Current decision:** Go with strong reference (simplest, sufficient)

---

## Implementation Notes

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

1. **Add attribute**
   ```python
   _client: Any = PrivateAttr(default=None)
   ```

2. **Use in save_async()**
   ```python
   async def save_async(self) -> Task:
       if self._client is None:
           raise ValueError("Task has no client reference")

       async with SaveSession(self._client) as session:
           # ...
   ```

3. **Use in refresh_async()**
   ```python
   async def refresh_async(self) -> Task:
       if self._client is None:
           raise ValueError("Task has no client reference")

       updated = await self._client.tasks.get_async(self.gid)
       # ...
   ```

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

1. **Assign in get_async()**
   ```python
   task = Task.model_validate(data)
   task._client = self._client
   return task
   ```

2. **Assign in create_async()**
   ```python
   task = Task.model_validate(result)
   task._client = self._client
   return task
   ```

3. **Assign in update_async()**
   ```python
   task = Task.model_validate(result)
   task._client = self._client
   return task
   ```

---

## Verification

### Tests Required

1. **Reference Storage**
   - Task._client set after get_async()
   - Task._client set after create_async()
   - Task._client set after update_async()

2. **Reference Use**
   - save_async() can access client
   - refresh_async() can access client

3. **Error Handling**
   - ValueError raised if _client is None
   - Clear error message

4. **Memory Test**
   - No memory leak on task creation/destruction
   - Client not prematurely GC'd

---

## Alternatives Considered

### Alternative 1: WeakReference

```python
# NOT CHOSEN
import weakref

class Task:
    _client_ref: Any = PrivateAttr(default=None)

    async def save_async(self) -> Task:
        if self._client_ref is None:
            raise ValueError("No client reference")

        client = self._client_ref()
        if client is None:
            raise RuntimeError("Client was garbage collected")

        async with SaveSession(client) as session:
            # ...
```

**Rejected because:**
- Unnecessary complexity
- Extra function call on every access
- Not solving real problem (client outlives task)

### Alternative 2: No Client Storage

```python
# NOT CHOSEN - would require user to manage:
async def save_async(self, client: AsanaClient | None = None) -> Task:
    if client is None:
        raise ValueError("Must pass client to save()")
    # ...
```

**Rejected because:**
- Defeats convenience purpose
- Requires passing client everywhere
- Not ergonomic

---

## Decision Record

**Decision:** Strong Reference Storage (Task._client = PrivateAttr)

**Decided by:** Architect (Session 3)

**Rationale:** Simple, pattern established in codebase, acceptable memory impact

**Implementation Timeline:** Session 6a (P4 Priority, with save_async implementation)

**Future Review:** Monitor for memory issues; can upgrade to WeakRef if needed

---

## Related ADRs

- ADR-0061: Implicit SaveSession Lifecycle (uses client reference in save_async)
- ADR-0035: Unit of Work Pattern (SaveSession also stores client reference)

---
