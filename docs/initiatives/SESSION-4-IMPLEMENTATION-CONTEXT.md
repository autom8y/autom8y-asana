# SESSION 4: P1 Implementation Context

**Document ID:** SESSION-4-IMPLEMENTATION-CONTEXT
**Status:** Ready for Engineer
**Date:** 2025-12-12
**Scope:** Phase 1 - Direct Methods (6 async + 6 sync)
**Quality Gate:** [Will be verified before engineer handoff]

---

## Quick Reference: What Am I Building?

**P1 is 12 new convenience methods on `TasksClient`** that wrap `SaveSession` internally, eliminating boilerplate:

```python
# Before (verbose, explicit SaveSession)
async with SaveSession(client) as session:
    session.add_tag(task_gid, tag_gid)
    await session.commit_async()

# After (concise, P1 method)
task = await client.tasks.add_tag_async(task_gid, tag_gid)
```

**Nothing else in P1.** No models, no new files, no name resolution. Just 12 methods that wrap SaveSession and return Task.

---

## The 12 P1 Methods (Exact Specs from TDD-SDKUX)

### Async Methods (6)

```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task without explicit SaveSession.

    Args:
        task_gid: Target task GID
        tag_gid: Tag GID to add

    Returns:
        Updated Task from API

    Raises:
        APIError: If task or tag not found

    Example:
        >>> task = await client.tasks.add_tag_async(task_gid, tag_gid)
    """

async def remove_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Remove tag from task.

    Args:
        task_gid: Target task GID
        tag_gid: Tag GID to remove

    Returns:
        Updated Task from API
    """

async def move_to_section_async(
    self, task_gid: str, section_gid: str, project_gid: str
) -> Task:
    """Move task to section within project.

    Args:
        task_gid: Task to move
        section_gid: Target section GID
        project_gid: Project context GID

    Returns:
        Updated Task from API
    """

async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task:
    """Set task assignee.

    Args:
        task_gid: Task to update
        assignee_gid: Assignee user GID (or "" to unassign)

    Returns:
        Updated Task from API
    """

async def add_to_project_async(
    self, task_gid: str, project_gid: str, section_gid: str | None = None
) -> Task:
    """Add task to project (optionally in section).

    Args:
        task_gid: Task to add
        project_gid: Target project GID
        section_gid: Optional section within project

    Returns:
        Updated Task from API
    """

async def remove_from_project_async(self, task_gid: str, project_gid: str) -> Task:
    """Remove task from project.

    Args:
        task_gid: Task to remove
        project_gid: Project to remove from

    Returns:
        Updated Task from API
    """
```

### Sync Methods (6 wrapper methods)

```python
def add_tag(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task (sync)."""
    return self._add_tag_sync(task_gid, tag_gid)

@sync_wrapper("add_tag_async")
async def _add_tag_sync(self, task_gid: str, tag_gid: str) -> Task:
    return await self.add_tag_async(task_gid, tag_gid)

# Similar pattern for:
# - remove_tag / _remove_tag_sync
# - move_to_section / _move_to_section_sync
# - set_assignee / _set_assignee_sync
# - add_to_project / _add_to_project_sync
# - remove_from_project / _remove_from_project_sync
```

---

## Implementation Pattern (From TDD-SDKUX §1)

**Each async method follows this exact pattern:**

```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task without explicit SaveSession."""
    # 1. Create SaveSession
    async with SaveSession(self._client) as session:
        # 2. Call SaveSession method
        session.add_tag(task_gid, tag_gid)
        # 3. Commit (automatic rollback on failure)
        await session.commit_async()

    # 4. Return fresh Task from API (updated with changes)
    return await self.get_async(task_gid)
```

**Why this pattern:**
- SaveSession handles all API calls, change tracking, error handling
- We just delegate to session methods and return the updated Task
- No error handling needed (SaveSession propagates as exceptions)
- Clean separation of concerns

---

## Integration Point: Where to Add Code

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

**Current State:**
- TasksClient class exists with `get_async()`, `create_async()`, `update_async()`, `delete_async()`
- `list_async()` returns `PageIterator[Task]`
- `subtasks_async()` exists
- Sync wrappers already follow `@sync_wrapper` pattern
- All methods use `self._http` for API calls
- All methods use `self._client` for client reference (in SaveSession calls)
- Error handling via `@error_handler` decorator

**Location to insert P1 methods:**
- **After `delete_async()` and `delete()` methods** (around line 419)
- **Before `list_async()` method** (around line 420)

This preserves the CRUD method grouping and maintains code organization.

---

## SaveSession Method Contracts

**SaveSession methods already exist** (don't implement—use them):

```python
# In SaveSession.__init__():
self._client: AsanaClient  # Available as reference

# Session methods that P1 uses:
async def add_tag(self, task_gid: str, tag_gid: str) -> None
async def remove_tag(self, task_gid: str, tag_gid: str) -> None
async def move_to_section(
    self, task_gid: str, section_gid: str, project_gid: str
) -> None
async def set_assignee(self, task_gid: str, assignee_gid: str) -> None
async def add_to_project(
    self, task_gid: str, project_gid: str, section_gid: str | None = None
) -> None
async def remove_from_project(self, task_gid: str, project_gid: str) -> None

# Commit method:
async def commit_async(self) -> SaveResult
```

**All these methods are already in `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`.**

You just call them. No implementation of SaveSession changes needed.

---

## Testing Requirements (From TDD-SDKUX §8)

### Test File Location
`/Users/tomtenuta/Code/autom8_asana/tests/unit/test_tasks_client.py` (already exists)

**Add these test cases to the existing test file:**

```python
# Test P1 async methods
@pytest.mark.asyncio
async def test_add_tag_async_returns_updated_task(client_with_mock_http):
    """add_tag_async returns Task with tag added."""
    # Setup
    client, mock_http = client_with_mock_http
    task_gid = "task_123"
    tag_gid = "tag_456"

    # Mock the return from get_async (fresh task after tag added)
    updated_task_data = {
        "gid": task_gid,
        "name": "Test Task",
        "tags": [{"gid": tag_gid, "name": "Urgent"}]
    }
    mock_http.get.return_value = updated_task_data

    # Execute
    result = await client.tasks.add_tag_async(task_gid, tag_gid)

    # Verify
    assert isinstance(result, Task)
    assert result.gid == task_gid

@pytest.mark.asyncio
async def test_add_tag_async_raises_on_invalid_gid(client_with_mock_http):
    """add_tag_async raises APIError for invalid task."""
    client, mock_http = client_with_mock_http
    mock_http.get.side_effect = APIError("404: Not Found")

    with pytest.raises(APIError):
        await client.tasks.add_tag_async("invalid_gid", "tag_456")

def test_add_tag_sync_delegates_to_async(client_with_mock_http):
    """Sync wrapper delegates to async."""
    client, mock_http = client_with_mock_http
    task_gid = "task_123"
    tag_gid = "tag_456"

    # Mock response
    updated_task_data = {
        "gid": task_gid,
        "name": "Test Task",
        "tags": [{"gid": tag_gid}]
    }
    mock_http.get.return_value = updated_task_data

    # Execute sync (should work)
    result = client.tasks.add_tag(task_gid, tag_gid)

    # Verify
    assert isinstance(result, Task)
    assert result.gid == task_gid

# Test P1 async methods (pattern repeats for all 6)
# - test_remove_tag_async_returns_updated_task
# - test_move_to_section_async_returns_updated_task
# - test_set_assignee_async_returns_updated_task
# - test_add_to_project_async_returns_updated_task
# - test_add_to_project_with_section_optional
# - test_remove_from_project_async_returns_updated_task

# Test sync wrappers
# - test_remove_tag_sync_delegates_to_async
# - test_move_to_section_sync_delegates_to_async
# - test_set_assignee_sync_delegates_to_async
# - test_add_to_project_sync_delegates_to_async
# - test_remove_from_project_sync_delegates_to_async

# Integration test
@pytest.mark.asyncio
async def test_add_tag_integration_with_savesession(client_with_mock_http):
    """P1 method correctly uses SaveSession internally."""
    client, mock_http = client_with_mock_http
    task_gid = "task_123"
    tag_gid = "tag_456"

    # Mock SaveSession.add_tag call (implicit in add_tag_async)
    # Mock the subsequent get_async call
    updated_task_data = {"gid": task_gid, "name": "Test", "tags": [{"gid": tag_gid}]}
    mock_http.get.return_value = updated_task_data

    # Execute
    result = await client.tasks.add_tag_async(task_gid, tag_gid)

    # Verify SaveSession was used (implicit: no exceptions)
    assert isinstance(result, Task)
```

**Acceptance Criteria (From TDD-SDKUX):**
- All P1 tests pass ✓
- Return types are Task objects ✓
- Sync wrappers work ✓
- No regressions in existing tests ✓

---

## Backward Compatibility Checklist

**Nothing breaks because:**
1. All 12 methods are **additive** (no existing methods modified)
2. Existing TasksClient methods unchanged (get, create, update, delete, list, subtasks)
3. SaveSession methods unchanged
4. No new imports required by consumers
5. All new methods follow existing `@error_handler` pattern
6. All sync wrappers follow existing `@sync_wrapper` pattern

**Verify before committing:**
- Run: `pytest tests/unit/test_tasks_client.py` (all existing tests pass)
- Run: `mypy src/autom8_asana/clients/tasks.py` (no type errors)
- Run: `ruff check src/autom8_asana/clients/tasks.py` (no lint errors)

---

## Success Criteria for Session 4

| Criterion | Check |
|-----------|-------|
| All 12 P1 methods implemented | Each method follows pattern, calls SaveSession, returns Task |
| All 6 sync wrappers work | Sync calls delegate to async, use @sync_wrapper |
| P1 tests pass | test_add_tag_async, test_remove_tag_async, etc. all pass |
| No type errors | mypy clean |
| No lint errors | ruff clean |
| No regressions | All existing tests still pass |
| Code quality | Follows existing patterns, clear docstrings |

**Session 4 is complete when:**
- [ ] All 12 methods added to TasksClient
- [ ] All P1 tests written and passing
- [ ] Full test suite passes (pytest)
- [ ] Type checking passes (mypy)
- [ ] Linting passes (ruff)
- [ ] Backward compatibility verified

---

## What NOT to Do in Session 4

This is P1 only. Do NOT do:

- **P2 (Custom Fields):** Don't add `__getitem__`, `__setitem__`, `__delitem__` to CustomFieldAccessor
- **P3 (Name Resolution):** Don't create NameResolver.py or add name→GID resolution
- **P4 (Auto-tracking):** Don't add `save()`, `refresh()` methods to Task
- **P5 (Client Constructor):** Don't enhance AsanaClient constructor for workspace detection

**Each phase is independent. P1 must complete first.**

---

## Imports You'll Need

Already available in TasksClient:

```python
# Already imported at top of tasks.py
from autom8_asana.models import Task
from autom8_asana.persistence.session import SaveSession
from autom8_asana.observability import error_handler

# SaveSession will be imported; just use self._client to pass to it
```

No new imports needed for P1.

---

## Quick Reference: SaveSession Usage in P1

```python
# Pattern for every P1 method:
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task."""
    async with SaveSession(self._client) as session:
        session.add_tag(task_gid, tag_gid)
        await session.commit_async()
    return await self.get_async(task_gid)

# Notes:
# - SaveSession(self._client) creates session with client reference
# - self._client is already available in TasksClient (from BaseClient)
# - session.add_tag() is already implemented in SaveSession
# - session.commit_async() returns SaveResult (we don't check it; let exceptions propagate)
# - await self.get_async(task_gid) fetches fresh Task with changes
# - Everything wrapped in @error_handler (decorator on method)
```

---

## Commit Message

When Session 4 is complete:

```
feat: P1 Direct Methods (12 convenience wrappers)

Add 6 async + 6 sync convenience methods to TasksClient:
- add_tag_async/add_tag
- remove_tag_async/remove_tag
- move_to_section_async/move_to_section
- set_assignee_async/set_assignee
- add_to_project_async/add_to_project
- remove_from_project_async/remove_from_project

Each method wraps SaveSession internally, eliminating boilerplate
for common task operations. Returns updated Task from API.

Per TDD-SDKUX Session 4 spec. All tests passing.
```

---

## Questions & Blockers

**Before you start:**

1. **Do I need to implement SaveSession methods?** No. They already exist.
2. **Do I modify the Task model?** No. P1 only touches TasksClient.
3. **Do I add name resolution?** No. That's P3 (later).
4. **Do I modify existing methods?** No. Only additive.
5. **What if a SaveSession method fails?** Exceptions propagate to caller (error_handler catches).

**If you find issues:**
- Blockers: Post them immediately
- Questions: Document them and continue (I'll address between sessions)
- Type errors: Fix locally using existing patterns

---

## Engineer Sign-Off Checklist

Before starting Session 4, verify:

- [ ] TDD-SDKUX is clear (this document filled gaps if any)
- [ ] SaveSession location confirmed: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
- [ ] TasksClient location confirmed: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
- [ ] Test file location confirmed: `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_tasks_client.py`
- [ ] @sync_wrapper pattern understood (existing methods show it)
- [ ] @error_handler pattern understood (existing methods show it)
- [ ] Ready to implement 12 methods following the pattern

**If all checked: Engineer ready for immediate Session 4 start.**

---

## References

- **Requirements:** `/Users/tomtenuta/Code/autom8_asana/docs/design/PRD-SDKUX.md` (41 FRs)
- **Architecture:** `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-SDKUX.md` (§1 P1 spec)
- **SaveSession Code:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
- **TasksClient Code:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
- **Tests:** `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_tasks_client.py`

---

## Engineer Invocation Recommendation

The engineer can start Session 4 immediately with:

```
@principal-engineer

**Session 4: P1 Direct Methods Implementation**

Context: See SESSION-4-IMPLEMENTATION-CONTEXT.md

Task: Implement 12 P1 convenience methods (6 async + 6 sync wrappers)
on TasksClient. Each wraps SaveSession internally, returns Task.

Success: All tests pass, type-safe, backward compatible.

Go.
```

---
