# SESSION 6: P4 Auto-tracking + P5 Client Simplification

**Document ID:** SESSION-6-IMPLEMENTATION-CONTEXT
**Status:** Ready for Engineer
**Date:** 2025-12-12
**Scope:** Phase 4 (Task.save/refresh with implicit SaveSession) + Phase 5 (Simplified AsanaClient constructor)
**Dependencies:** Sessions 1-5 complete (Discovery, Requirements, Architecture, P1, P2+P3 all solid)
**Test Status:** 2,959 tests passing (as of Session 5 completion)
**Quality Gate:** Design fully specified in ADRs; no ambiguities remain

---

## Executive Summary

**Sessions 1-5 are complete and solid.** All discovery questions answered, requirements validated, architecture designed, P1 implemented (12 methods), P2+P3 implemented (16+31 tests).

**Session 6 contains TWO INDEPENDENT PHASES:**

1. **P4: Auto-tracking Models** - Add Task.save()/save_async() and Task.refresh()/refresh_async() methods
   - Task stores client reference via `_client: Any = PrivateAttr(default=None)`
   - save() creates implicit SaveSession internally
   - Dirty detection via SaveSession.ChangeTracker (no new Task-level logic)
   - Estimated: 3-4 hours

2. **P5: Simplified Client Constructor** - Make AsanaClient(token) work with auto-detection
   - Single-argument pattern with optional workspace_gid
   - Auto-detect workspace if exactly one exists
   - Estimated: 1.5-2 hours

**Recommendation:** Implement P4 first (depends on P2 custom field dirty tracking), then P5 (independent).

**Total Estimated Time:** 5-6 hours for both phases.

**Quality Guarantee:** All design decisions documented in approved ADRs (ADR-0061, ADR-0063, ADR-0064). No ambiguities remain.

---

## PHASE 4: Auto-tracking Models (P4)

### What P4 Delivers

Users can now call `.save()` directly on tasks without managing SaveSession:

```python
# Before (verbose)
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()

# After (intuitive)
task = await client.tasks.get(task_gid)
task.name = "Updated"
await task.save_async()  # Implicit SaveSession

# Also supports
await task.refresh_async()  # Reload from API
```

### P4 Scope (Clear Boundaries)

**Files Modified:**
1. `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` (4 methods + 1 attribute)
2. `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` (3 methods updated for client assignment)

**Out of Scope:**
- SaveSession internals (unchanged)
- CustomFieldAccessor (already done in P2)
- Client class (P5 is separate)
- Existing tests (will pass unchanged)

### P4 Implementation Details

#### 1. Task Model Changes

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

**Add at class level (around line 115, after existing PrivateAttrs):**

```python
from pydantic import PrivateAttr
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

class Task(AsanaResource):
    # ... existing fields ...

    # Add this attribute (around line 115)
    _client: Any = PrivateAttr(default=None)  # Stores AsanaClient reference for save/refresh
```

**Add save_async() method (~20 lines):**

Location: After the custom_fields property, before end of class

```python
async def save_async(self) -> "Task":
    """Save changes to this task using implicit SaveSession (async).

    This method creates a SaveSession internally to persist changes
    (field updates, custom field modifications) back to Asana.

    Returns:
        This task instance (updated in-place with API response)

    Raises:
        ValueError: If task has no client reference (created outside client.tasks)
        APIError: If Asana API returns error

    Example:
        >>> task = await client.tasks.get(task_gid)
        >>> task.name = "Updated Name"
        >>> await task.save_async()  # Changes persisted
    """
    if self._client is None:
        raise ValueError(
            "Cannot save task without client reference. "
            "Task must be obtained via client.tasks.get() or similar."
        )

    from autom8_asana.persistence.session import SaveSession

    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()

        if not result.success:
            raise result.failed[0].error

        return self
```

**Add save() method (~2 lines):**

Location: After save_async()

```python
def save(self) -> "Task":
    """Save changes to this task using implicit SaveSession (sync).

    Synchronous wrapper around save_async().
    See save_async() docstring for full documentation.
    """
    from autom8_asana.shared.sync_wrapper import sync_wrapper
    return sync_wrapper(self.save_async)()
```

**Add refresh_async() method (~20 lines):**

Location: After save() method

```python
async def refresh_async(self) -> "Task":
    """Reload this task from Asana API, discarding local changes (async).

    Fetches the latest task state from Asana and updates this instance
    in-place. All local changes are discarded (you can still access the
    original task.gid to identify it).

    Returns:
        This task instance (updated with fresh API data)

    Raises:
        ValueError: If task has no client reference
        APIError: If Asana API returns error

    Example:
        >>> task = await client.tasks.get(task_gid)
        >>> task.name = "Locally changed"
        >>> await task.refresh_async()  # Name reverted to API value
    """
    if self._client is None:
        raise ValueError(
            "Cannot refresh task without client reference. "
            "Task must be obtained via client.tasks.get() or similar."
        )

    # Fetch fresh copy from API
    updated = await self._client.tasks.get_async(self.gid)

    # Update all fields from fresh copy
    for field_name in self.__fields_set__:
        if hasattr(updated, field_name):
            setattr(self, field_name, getattr(updated, field_name))

    # Clear custom field modifications
    if self._custom_fields_accessor is not None:
        self._custom_fields_accessor._modifications.clear()

    return self
```

**Add refresh() method (~2 lines):**

Location: After refresh_async()

```python
def refresh(self) -> "Task":
    """Reload this task from Asana API (sync).

    Synchronous wrapper around refresh_async().
    See refresh_async() docstring for full documentation.
    """
    from autom8_asana.shared.sync_wrapper import sync_wrapper
    return sync_wrapper(self.refresh_async)()
```

**Type Hints Note:**
- Use `"Task"` (forward reference) in return types to avoid circular import
- At top of file: `from typing import TYPE_CHECKING, Any` + conditional import

#### 2. TasksClient Updates (Assign Client Reference)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

**Update get_async() method (around line X):**

Locate existing `async def get_async(self, task_gid: str, ...)` method. After `Task.model_validate(data)` line, add:

```python
async def get_async(self, task_gid: str, opt_fields: list[str] | None = None) -> Task:
    """Get a task by GID."""
    data = await self._http.get(f"/tasks/{task_gid}", params={"opt_fields": opt_fields})
    task = Task.model_validate(data)
    task._client = self._client  # NEW: Assign client reference
    return task
```

**Update create_async() method (similar pattern):**

After `Task.model_validate(result)` line, add:

```python
task._client = self._client  # Assign client reference
```

**Update update_async() method (similar pattern):**

After `Task.model_validate(result)` line, add:

```python
task._client = self._client  # Assign client reference
```

**Note:** Search for all places that call `Task.model_validate()` and add `task._client = self._client` after instantiation.

### P4 Design Decisions (Already Approved)

**ADR-0061: Implicit SaveSession Lifecycle**
- Decision: Each save_async() call creates a fresh SaveSession, destroyed at method end
- Why: Clear scope, no nesting issues, consistent with P1 pattern
- Status: APPROVED

**ADR-0063: Client Reference Storage**
- Decision: Strong reference (not WeakRef)
- Why: Simple, pattern matches _custom_fields_accessor, acceptable memory impact
- Status: APPROVED

**ADR-0064: Dirty Detection Strategy**
- Decision: Leverage SaveSession.ChangeTracker (no Task-level dirty flag)
- Why: SaveSession already tracks changes; no duplication needed; handles custom fields
- Status: APPROVED

### P4 Testing Requirements

**File:** `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/test_task.py`

Tests to add (all must pass):

```python
# 1. save_async() with field changes
def test_task_save_async_persists_field_changes():
    # Create mock task with _client reference
    # Modify task.name
    # Call save_async()
    # Verify SaveSession was created, track called, commit_async called
    # Verify task returned

# 2. save() sync wrapper
def test_task_save_sync_wrapper():
    # Verify save() delegates to sync_wrapper(save_async)
    # Verify returns Task

# 3. save_async() with custom field changes
def test_task_save_async_persists_custom_field_changes():
    # Create task with custom fields
    # Modify via task.custom_fields["Priority"] = "High"
    # Call save_async()
    # Verify SaveSession includes custom field modifications

# 4. save_async() without client reference
def test_task_save_async_raises_without_client():
    # Create task without setting _client
    # Call save_async()
    # Verify ValueError raised with clear message

# 5. refresh_async() reloads from API
def test_task_refresh_async_reloads():
    # Create task with modified name (locally)
    # Call refresh_async()
    # Verify fresh fetch via client.tasks.get_async()
    # Verify local changes discarded

# 6. refresh() sync wrapper
def test_task_refresh_sync_wrapper():
    # Verify refresh() delegates to sync_wrapper(refresh_async)

# 7. save_async() clears custom field modifications
def test_task_save_async_clears_modifications():
    # Set custom field via __setitem__
    # Call save_async()
    # Verify _modifications cleared after commit

# 8. Integration: Field + Custom Field changes
def test_task_save_async_mixed_changes():
    # Modify both task.name and custom field
    # Call save_async()
    # Verify both included in SaveSession

# 9. TasksClient assigns client reference
def test_tasks_client_get_assigns_client():
    # Call client.tasks.get_async()
    # Verify returned task._client == client

# 10. refresh_async() updates task in-place
def test_task_refresh_async_updates_inplace():
    # Modify task
    # Call refresh_async()
    # Verify same task instance returned
    # Verify fields updated
```

**Key Testing Patterns:**
- Mock `SaveSession` context manager to verify track() and commit_async() called
- Mock HTTP client for refresh_async() API call
- Verify task instance returned (not new instance)
- Test error cases (no client reference)
- Test both sync and async versions

### P4 Success Criteria

- [ ] Task has `_client: Any = PrivateAttr(default=None)` attribute
- [ ] Task.save_async() creates SaveSession, tracks, commits, returns Task
- [ ] Task.save() is sync wrapper (delegates to save_async)
- [ ] Task.refresh_async() fetches from API, updates fields, clears modifications
- [ ] Task.refresh() is sync wrapper
- [ ] TasksClient.get_async(), create_async(), update_async() assign _client
- [ ] All new methods have docstrings
- [ ] ValueError raised if save/refresh called without client reference
- [ ] Custom field modifications persisted in save
- [ ] All tests pass (add ~10 new test cases)
- [ ] Type safety: mypy passes
- [ ] Backward compat: SaveSession unchanged, all pre-existing tests pass

---

## PHASE 5: Simplified Client Constructor (P5)

### What P5 Delivers

Users can now initialize the client with just a token:

```python
# Before (verbose)
client = AsanaClient(
    token="...",
    workspace_gid="1234567890123456",
    cache=None,
    http_client=None,
)

# After (simple, for common case)
client = AsanaClient(token="...")  # Auto-detects workspace if only one exists

# Or explicit (advanced case)
client = AsanaClient(token="...", workspace_gid="...")  # Full control
```

### P5 Scope (Clear Boundaries)

**Files Modified:**
1. `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py` (Enhanced __init__)

**Out of Scope:**
- Client class internals (only __init__)
- Existing client methods (unchanged)
- Exceptions (ConfigurationError should already exist)

### P5 Implementation Details

#### 1. Enhanced AsanaClient Constructor

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py`

**Current signature:** (locate existing __init__)
```python
def __init__(
    self,
    token: str,
    workspace_gid: str | None = None,
    cache: CacheProtocol | None = None,
    http_client: httpx.AsyncClient | None = None,
):
```

**Add auto-detection logic (before super().__init__()):**

```python
def __init__(
    self,
    token: str,
    workspace_gid: str | None = None,
    cache: CacheProtocol | None = None,
    http_client: httpx.AsyncClient | None = None,
):
    """Initialize Asana client.

    Args:
        token: Personal Access Token for Asana API
        workspace_gid: Workspace GID (optional). If not provided and exactly
                       one workspace exists, auto-detects it.
        cache: Optional cache backend (for advanced use)
        http_client: Optional httpx client (for advanced use)

    Raises:
        ConfigurationError: If workspace_gid not provided and:
                           - 0 workspaces available (token invalid?)
                           - >1 workspaces available (ambiguous, must specify)

    Example:
        >>> # Simple: auto-detect if only one workspace
        >>> client = AsanaClient(token="...")

        >>> # Explicit: specify workspace
        >>> client = AsanaClient(token="...", workspace_gid="1234567890123456")
    """
    # If workspace_gid not provided, try auto-detection
    if workspace_gid is None:
        workspace_gid = self._auto_detect_workspace(token, http_client)

    # Original initialization
    self._token = token
    self._workspace_gid = workspace_gid
    self._cache = cache or NoOpCache()
    self._http = http_client or httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
    )

    # Initialize clients
    self.tasks = TasksClient(self._http, self)
    # ... other client initialization ...
```

**Add helper method (~30 lines):**

```python
@staticmethod
def _auto_detect_workspace(
    token: str,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    """Auto-detect workspace GID if exactly one exists.

    Args:
        token: Personal Access Token
        http_client: Optional httpx client for API call

    Returns:
        Workspace GID if exactly one found

    Raises:
        ConfigurationError: If 0 or >1 workspaces found
    """
    import httpx
    from autom8_asana.exceptions import ConfigurationError

    # Create temporary client if not provided
    client = http_client or httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
    )

    try:
        # Fetch workspaces
        response = client.get(
            "https://app.asana.com/api/1.0/users/me",
            params={"opt_fields": "workspaces"}
        )
        response.raise_for_status()
        data = response.json()["data"]
        workspaces = data.get("workspaces", [])

        if len(workspaces) == 0:
            raise ConfigurationError(
                "No workspaces found. Token may be invalid or have no workspace access."
            )
        elif len(workspaces) == 1:
            return workspaces[0]["gid"]
        else:
            workspace_names = [w["name"] for w in workspaces]
            raise ConfigurationError(
                f"Multiple workspaces found: {workspace_names}. "
                f"Please specify workspace_gid explicitly."
            )
    finally:
        # Close temporary client if we created it
        if http_client is None:
            client.close()
```

**Important Notes:**
- Use synchronous httpx for __init__ (not async)
- Fetch from `/users/me` endpoint (public, always available)
- Extract workspace GID from response
- Raise ConfigurationError (not ValueError) for clarity
- Add docstrings with examples

#### 2. Exception Class (If Needed)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py`

Check if `ConfigurationError` exists. If not, add:

```python
class ConfigurationError(Exception):
    """Raised when AsanaClient configuration is invalid or ambiguous."""
    pass
```

### P5 Design Approach

**Pattern:** Progressive disclosure
- Common case: Just token (auto-detect)
- Advanced case: Token + workspace_gid (explicit control)
- Maintains backward compatibility

**Validation:**
- 0 workspaces → error (invalid token)
- 1 workspace → auto-use it
- >1 workspaces → error (ambiguous, require explicit choice)

### P5 Testing Requirements

**File:** `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_client.py`

Tests to add:

```python
# 1. Auto-detect single workspace
def test_client_init_auto_detects_single_workspace(mock_http):
    # Mock /users/me to return 1 workspace
    # Create AsanaClient(token) without workspace_gid
    # Verify client._workspace_gid set to that workspace

# 2. Error on no workspaces
def test_client_init_error_no_workspaces(mock_http):
    # Mock /users/me to return empty workspaces list
    # Create AsanaClient(token) without workspace_gid
    # Verify ConfigurationError raised

# 3. Error on multiple workspaces
def test_client_init_error_multiple_workspaces(mock_http):
    # Mock /users/me to return >1 workspaces
    # Create AsanaClient(token) without workspace_gid
    # Verify ConfigurationError raised
    # Verify error message includes workspace names

# 4. Explicit workspace_gid skips auto-detect
def test_client_init_explicit_workspace_skips_auto_detect(mock_http):
    # Create AsanaClient(token, workspace_gid="...")
    # Verify /users/me NOT called
    # Verify client._workspace_gid set to provided value

# 5. Backward compatibility: all args still work
def test_client_init_backward_compat_all_args():
    # Create client with all args (token, workspace_gid, cache, http_client)
    # Verify all assigned correctly

# 6. Auto-detect closes temporary client
def test_client_init_auto_detect_closes_temp_client(mock_http):
    # Mock /users/me
    # Create AsanaClient(token) without http_client
    # Verify temporary httpx client created and closed

# 7. Reuse provided http_client
def test_client_init_auto_detect_reuses_http_client(mock_http):
    # Create client with provided http_client
    # Create AsanaClient(token) without workspace_gid
    # Verify /users/me called on provided client (not temporary)
```

### P5 Success Criteria

- [ ] AsanaClient(token) works (auto-detects workspace if only one)
- [ ] AsanaClient(token, workspace_gid) works (explicit control)
- [ ] ConfigurationError raised if no workspaces found
- [ ] ConfigurationError raised if multiple workspaces (with names in error)
- [ ] Backward compatibility: All existing tests pass
- [ ] All new methods have docstrings
- [ ] Type safety: mypy passes
- [ ] Error messages are clear and actionable

---

## Integration Points & Dependencies

### P4 Depends On

- **P2 (Custom Field Access)** - Custom field changes detected via _modifications
- **SaveSession** (Sessions 1-3) - Used by Task.save_async()
- **TasksClient** - Needs to assign _client reference

### P5 Depends On

- **httpx** - Already available
- **ConfigurationError** - Should already exist in exceptions.py
- **Nothing else** (independent feature)

### P4 ↔ P5 Interaction

**None.** They're independent. Both can proceed in parallel, or sequentially (recommend P4 first since it's more impactful).

---

## Testing Strategy Summary

**Total New Tests:** ~17 (10 for P4, 7 for P5)

**Test Coverage Goals:**
- Happy path: All main scenarios
- Error paths: ValueError (no client), ConfigurationError (workspace issues)
- Edge cases: Mixed field+custom field changes, refresh clears modifications
- Backward compat: Existing tests all pass

**Mocking Strategy:**
- P4: Mock SaveSession, HTTP client
- P5: Mock httpx responses for /users/me endpoint

---

## Quality Gates (Pre-Handoff Checklist)

### Design Quality
- [ ] All methods have full docstrings
- [ ] Method signatures match PRD exactly
- [ ] ADRs approved (ADR-0061, ADR-0063, ADR-0064)
- [ ] No ambiguities remain

### Implementation Quality
- [ ] Code follows project conventions (see .claude/CLAUDE.md)
- [ ] Type hints complete (mypy passes)
- [ ] Error messages clear and actionable
- [ ] Comments for non-obvious logic

### Testing Quality
- [ ] All new methods have tests
- [ ] Happy path covered
- [ ] Error paths covered
- [ ] Integration tests (P4 with SaveSession, P5 with httpx)
- [ ] All tests pass (unit + integration)
- [ ] Coverage >80% for new code

### Backward Compatibility
- [ ] SaveSession unchanged (save_async uses it, but doesn't modify)
- [ ] CustomFieldAccessor unchanged (P4 relies on P2, but doesn't modify)
- [ ] All pre-existing tests pass
- [ ] Exception hierarchy unchanged

### Documentation
- [ ] Docstrings updated (save_async, refresh_async, __init__)
- [ ] If needed: README updated with new patterns
- [ ] Examples in docstrings

---

## File Locations Reference

**Task Model:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

**TasksClient:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

**AsanaClient:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py`

**Exceptions:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py`

**SaveSession:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (not modified in P4)

**P4 Tests:**
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/test_task.py`

**P5 Tests:**
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/test_client.py`

---

## Open Questions

**None.** All design decisions are approved and documented in ADRs.

---

## Revision History

| Version | Date | Status | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Ready | Initial context for P4+P5 handoff |

---

## Next Steps

1. **Engineer reviews this document** - Confirm understanding
2. **Engineer implements P4** - ~3-4 hours
3. **P4 Quality Gate** - All tests pass, coverage >80%
4. **Engineer implements P5** - ~1.5-2 hours
5. **P5 Quality Gate** - All tests pass, coverage >80%
6. **Final Verification** - All 2,959+ tests pass, mypy clean
7. **Commit & Merge** - Session 6 complete

---
