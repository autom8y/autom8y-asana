# TDD-SDKUX: SDK Usability Overhaul - Technical Design Document

**Document ID:** TDD-SDKUX
**Status:** Ready for Implementation (Session 4)
**Author:** Architect
**Created:** 2025-12-12
**Approved PRD:** PRD-SDKUX (Session 2)
**Discovery Reference:** DISCOVERY-SDKUX-001

---

## Executive Summary

This technical design transforms the autom8_asana SDK from a functional but verbose library into an ergonomic, developer-friendly API. The solution adds **convenience methods, simplified syntax, and implicit session management** while preserving the powerful explicit `SaveSession` pattern for batch operations.

**Architecture Level:** Module - Clear API surface, minimal infrastructure, leverages existing patterns.

**Key Design Principles:**
- All new functionality is **additive** (zero breaking changes)
- **Async-first** with sync wrappers via existing `@sync_wrapper` decorator
- **Leverage existing patterns** (SaveSession, PrivateAttr, CustomFieldAccessor)
- **Type-safe** throughout (mypy compliance)
- **No new infrastructure** (use existing caching, change tracking, exception hierarchy)

---

## Component Architecture

### 1. TasksClient Extensions (P1: Direct Methods)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` (existing, enhance)

**Scope:** Add 12 new methods (6 async + 6 sync wrappers)

#### P1 Methods Specification

```python
# Async versions
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
    """Remove tag from task."""

async def move_to_section_async(
    self, task_gid: str, section_gid: str, project_gid: str
) -> Task:
    """Move task to section within project."""

async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task:
    """Set task assignee."""

async def add_to_project_async(
    self, task_gid: str, project_gid: str, section_gid: str | None = None
) -> Task:
    """Add task to project (optionally in section)."""

async def remove_from_project_async(self, task_gid: str, project_gid: str) -> Task:
    """Remove task from project."""

# Sync wrappers (all follow same pattern)
def add_tag(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task (sync)."""
    return self._add_tag_sync(task_gid, tag_gid)

@sync_wrapper("add_tag_async")
async def _add_tag_sync(self, task_gid: str, tag_gid: str) -> Task:
    return await self.add_tag_async(task_gid, tag_gid)

# Similar sync wrappers for all 6 async methods
```

**Pattern:**
- Each async method wraps `SaveSession` internally
- Returns updated `Task` object (not `SaveResult`)
- Sync wrappers use existing `@sync_wrapper` decorator pattern
- No breaking changes to existing methods

**Implementation Detail (Internal):**
```python
# Inside each async method:
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    async with SaveSession(self._client) as session:
        session.add_tag(task_gid, tag_gid)
        await session.commit_async()
    # Return fresh Task from API
    return await self.get_async(task_gid)
```

---

### 2. NameResolver (P3: Name Resolution)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/name_resolver.py` (NEW)

**Responsibilities:**
- Resolve human-readable names to GIDs
- Support polymorphic input (name_or_gid: str)
- Implement per-SaveSession caching
- Raise `NameNotFoundError` with helpful suggestions

#### NameResolver Class Design

```python
from typing import TYPE_CHECKING, Any
from difflib import get_close_matches

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.persistence.session import SaveSession

class NameResolver:
    """Resolve names to GIDs for tags, sections, projects, assignees.

    Caches results per SaveSession (zero staleness).
    Supports polymorphic input: accepts both names and GIDs.
    """

    def __init__(self, client: Any, session_cache: dict[str, Any] | None = None):
        """Initialize resolver with client and optional cache.

        Args:
            client: AsanaClient instance
            session_cache: Per-SaveSession cache dict (created per session)
        """
        self._client = client
        self._cache = session_cache or {}

    async def resolve_tag_async(
        self, name_or_gid: str, project_gid: str | None = None
    ) -> str:
        """Resolve tag name to GID.

        Args:
            name_or_gid: Tag name or GID
            project_gid: Unused (workspace-level tags)

        Returns:
            Tag GID

        Raises:
            NameNotFoundError: If name not found with suggestions

        Example:
            >>> gid = await resolver.resolve_tag_async("Urgent")
            >>> # Or passthrough GID
            >>> gid = await resolver.resolve_tag_async("1234567890abcdef")
        """
        # If looks like GID (alphanumeric, 20+ chars), return as-is
        if self._looks_like_gid(name_or_gid):
            return name_or_gid

        # Check cache
        cache_key = f"tag:{name_or_gid}"
        if cached := self._cache.get(cache_key):
            return cached

        # Fetch all tags in workspace
        workspace_gid = self._client.default_workspace_gid
        all_tags = []
        async for tag in self._client.tags.list_for_workspace_async(workspace_gid):
            all_tags.append(tag)

        # Find exact match (case-insensitive)
        for tag in all_tags:
            if tag.name.lower() == name_or_gid.lower():
                self._cache[cache_key] = tag.gid
                return tag.gid

        # Not found - raise with suggestions
        available_names = [tag.name for tag in all_tags]
        suggestions = get_close_matches(name_or_gid, available_names, n=3, cutoff=0.6)

        from autom8_asana.exceptions import NameNotFoundError

        raise NameNotFoundError(
            name=name_or_gid,
            resource_type="tag",
            scope=workspace_gid,
            suggestions=suggestions,
            available_names=available_names,
        )

    async def resolve_section_async(
        self, name_or_gid: str, project_gid: str
    ) -> str:
        """Resolve section name to GID (project-scoped)."""
        # Implementation similar to resolve_tag_async
        # but with project_gid scope

    async def resolve_project_async(
        self, name_or_gid: str, workspace_gid: str
    ) -> str:
        """Resolve project name to GID."""

    async def resolve_assignee_async(
        self, name_or_gid: str, workspace_gid: str
    ) -> str:
        """Resolve user name or email to GID."""

    # Sync wrappers for all methods
    def resolve_tag(self, name_or_gid: str, project_gid: str | None = None) -> str:
        """Resolve tag (sync)."""
        return self._resolve_tag_sync(name_or_gid, project_gid)

    @sync_wrapper("resolve_tag_async")
    async def _resolve_tag_sync(
        self, name_or_gid: str, project_gid: str | None = None
    ) -> str:
        return await self.resolve_tag_async(name_or_gid, project_gid)

    # Similar sync wrappers for all async methods

    @staticmethod
    def _looks_like_gid(value: str) -> bool:
        """Check if value looks like a Asana GID (alphanumeric, 20+ chars)."""
        return len(value) >= 20 and value.replace("_", "").isalnum()
```

**Per-SaveSession Cache Setup:**

In `SaveSession.__init__()`, add:
```python
self._name_cache: dict[str, str] = {}
self._name_resolver = NameResolver(self._client, self._name_cache)
```

Provide accessor:
```python
@property
def name_resolver(self) -> NameResolver:
    """Get name resolver for this session."""
    return self._name_resolver
```

---

### 3. CustomFieldAccessor Enhancement (P2)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py` (existing, enhance)

**Current Implementation (No Changes Needed):**
- Already has `get()`, `set()`, `remove()` methods
- Already tracks modifications in `_modifications` dict
- Already has `has_changes()` method

**New Methods to Add:**

```python
def __getitem__(self, name_or_gid: str) -> Any:
    """Get custom field value by name/GID (dict syntax).

    Args:
        name_or_gid: Field name or GID

    Returns:
        Field value (preserves type: enum dict, number, text, date, etc.)

    Raises:
        KeyError: If field doesn't exist

    Example:
        >>> value = accessor["Priority"]  # Returns enum dict or value
        >>> if value is None:
        ...     # Handle missing value
    """
    result = self.get(name_or_gid, default=_MISSING)
    if result is _MISSING:
        raise KeyError(name_or_gid)
    return result

def __setitem__(self, name_or_gid: str, value: Any) -> None:
    """Set custom field value by name/GID (dict syntax).

    Args:
        name_or_gid: Field name or GID
        value: New value (any type; accessor handles serialization)

    Example:
        >>> accessor["Priority"] = "High"  # Marks dirty automatically
    """
    self.set(name_or_gid, value)

def __delitem__(self, name_or_gid: str) -> None:
    """Delete custom field (dict syntax)."""
    self.remove(name_or_gid)
```

**Type Preservation (Already Implemented):**
- `_extract_value()` method already reads type-specific fields (text_value, number_value, enum_value, etc.)
- No changes needed; P2 just uses existing functionality

**Change Tracking (Already Implemented):**
- `_modifications` dict already tracks changes
- `has_changes()` already detects dirty state
- Task.model_dump() already includes modifications when present

---

### 4. Task Model Extensions (P2, P4)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` (existing, enhance)

**New Attribute:**
```python
from typing import TYPE_CHECKING, Any
from pydantic import PrivateAttr

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

class Task(AsanaResource):
    # ... existing fields ...

    # Private client reference (not serialized)
    _client: Any = PrivateAttr(default=None)
    _custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)
```

**New Property:**
```python
@property
def custom_fields(self) -> CustomFieldAccessor:
    """Dictionary-style access to custom fields.

    Returns:
        CustomFieldAccessor for this task's custom fields

    Example:
        >>> task.custom_fields["Priority"] = "High"
        >>> value = task.custom_fields["Status"]
    """
    if self._custom_fields_accessor is None:
        self._custom_fields_accessor = CustomFieldAccessor(self.custom_fields)
    return self._custom_fields_accessor
```

**New Methods (P4):**
```python
async def save_async(self) -> Task:
    """Save task changes using implicit SaveSession.

    Creates SaveSession automatically, tracks changes, commits.
    No-op if task is clean (no API call).

    Returns:
        Updated Task (same instance, refreshed from API)

    Raises:
        ValueError: If _client is not set
        PartialSaveError: If commit fails

    Example:
        >>> task = await client.tasks.get(task_gid)
        >>> task.name = "Updated"
        >>> task.custom_fields["Priority"] = "High"
        >>> await task.save()  # Commits both changes
    """
    if self._client is None:
        raise ValueError("Task has no client reference (not fetched from API?)")

    from autom8_asana.persistence.session import SaveSession

    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()

        if not result.success:
            # Raise first error
            raise result.failed[0].error

    # Return self (already updated by SaveSession)
    return self

def save(self) -> Task:
    """Save task changes (sync wrapper)."""
    return self._save_sync()

@sync_wrapper("save_async")
async def _save_sync(self) -> Task:
    return await self.save_async()

async def refresh_async(self) -> Task:
    """Re-fetch task from API, discarding local changes.

    Useful before saving to check for conflicts.

    Returns:
        Self (all fields updated from API)

    Raises:
        ValueError: If _client is not set
        APIError: If task not found

    Example:
        >>> task = await client.tasks.get(task_gid)
        >>> task.name = "Local"
        >>> await task.refresh()  # Resets to API state
    """
    if self._client is None:
        raise ValueError("Task has no client reference")

    # Fetch fresh copy
    fresh = await self._client.tasks.get_async(self.gid)

    # Copy all fields from fresh task
    for field_name in self.model_fields:
        setattr(self, field_name, getattr(fresh, field_name, None))

    # Clear custom field modifications
    if self._custom_fields_accessor is not None:
        self._custom_fields_accessor.clear_changes()

    return self

def refresh(self) -> Task:
    """Re-fetch task from API (sync wrapper)."""
    return self._refresh_sync()

@sync_wrapper("refresh_async")
async def _refresh_sync(self) -> Task:
    return await self.refresh_async()
```

**Client Reference Assignment (In TasksClient):**

After creating Task objects, assign client reference:
```python
# In TasksClient.get_async():
async def get_async(self, task_gid: str, ...) -> Task | dict[str, Any]:
    data = await self._http.get(f"/tasks/{task_gid}", params=params)
    if raw:
        return data
    task = Task.model_validate(data)
    task._client = self._client  # Store reference
    return task

# Similar for create_async(), update_async(), and list results
```

---

### 5. Exception Enhancement

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (existing, enhance)

**New Exception Class:**
```python
class NameNotFoundError(AsanaError):
    """Raised when a resource name cannot be resolved to a GID.

    Includes suggestions of similar names based on fuzzy matching.

    Attributes:
        name: The name that was searched for
        resource_type: Type of resource ("tag", "project", "user", "section")
        scope: Scope identifier (workspace GID or project GID)
        suggestions: List of similar names (fuzzy matches)
        available_names: All available names in the scope
    """

    def __init__(
        self,
        name: str,
        resource_type: str,
        scope: str,
        suggestions: list[str] | None = None,
        available_names: list[str] | None = None,
    ) -> None:
        """Initialize NameNotFoundError.

        Args:
            name: The name that was searched for
            resource_type: Type of resource ("tag", "project", "user", "section")
            scope: Scope identifier (workspace GID or project GID)
            suggestions: Optional fuzzy match suggestions
            available_names: Optional list of all available names in scope
        """
        self.name = name
        self.resource_type = resource_type
        self.scope = scope
        self.suggestions = suggestions or []
        self.available_names = available_names or []

        # Build helpful error message
        message = (
            f"Could not find {resource_type} named '{name}' "
            f"in scope {scope}."
        )

        if self.suggestions:
            message += f" Did you mean: {', '.join(repr(s) for s in self.suggestions)}?"

        if self.available_names:
            count = len(self.available_names)
            if count <= 10:
                message += f" Available: {', '.join(repr(n) for n in self.available_names)}"
            else:
                message += (
                    f" Available: {', '.join(repr(n) for n in self.available_names[:10])} "
                    f"(and {count - 10} more)"
                )

        super().__init__(message)
```

---

### 6. AsanaClient Constructor Enhancement (P5)

**File:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/client.py` (existing, enhance)

**Current Constructor:**
```python
def __init__(
    self,
    token: str,
    workspace_gid: str | None = None,
    batch_size: int = 10,
    max_concurrent: int = 15,
    # ... other params ...
):
```

**Enhanced Constructor (Backward Compatible):**
```python
def __init__(
    self,
    token: str,
    workspace_gid: str | None = None,
    batch_size: int = 10,
    max_concurrent: int = 15,
    # ... other params ...
):
    """Initialize Asana client.

    Simplified single-argument pattern: AsanaClient(token)
    Auto-detects workspace if user has exactly one.

    Args:
        token: Personal Access Token
        workspace_gid: Workspace GID (optional; auto-detected if exactly one)
        batch_size: Size of batch operations (default 10)
        max_concurrent: Max concurrent requests (default 15)

    Raises:
        ConfigurationError: If >1 workspace and no workspace_gid provided
        ConfigurationError: If 0 workspaces and no workspace_gid provided

    Example:
        >>> # Simplified (single workspace users)
        >>> client = AsanaClient("0/1234567890abcdef")

        >>> # Full (multi-workspace)
        >>> client = AsanaClient("0/1234567890abcdef", workspace_gid="5678...")
    """
    self._token = token
    self._http = HTTPClient(token)

    # Auto-detect workspace if not provided
    if workspace_gid is None:
        workspace_gid = self._detect_default_workspace()

    self.default_workspace_gid = workspace_gid

    # ... rest of initialization ...

async def _detect_default_workspace(self) -> str:
    """Auto-detect user's workspace (if exactly one).

    Returns:
        Workspace GID

    Raises:
        ConfigurationError: If >1 or 0 workspaces
    """
    user = await self.users.get_user_async()

    workspaces = []
    async for ws in self.workspaces.list_async():
        workspaces.append(ws)

    if len(workspaces) == 0:
        raise ConfigurationError(
            "User has no workspaces. This should not happen; check PAT validity."
        )
    elif len(workspaces) == 1:
        return workspaces[0].gid
    else:
        raise ConfigurationError(
            f"User has {len(workspaces)} workspaces. "
            f"Specify workspace_gid explicitly: "
            f"AsanaClient(token, workspace_gid='your_gid')"
        )
```

**Configuration Error (If Not Existing):**
```python
class ConfigurationError(AsanaError):
    """Raised for client configuration issues."""
    pass
```

---

## Data Flow Diagrams

### Flow 1: P1 Direct Method (add_tag_async)

```
User Code:
  await client.tasks.add_tag_async(task_gid, "Urgent")
    ↓
TasksClient.add_tag_async(task_gid, tag_gid)
    ↓ (wraps internally)
    async with SaveSession(self._client) as session:
        session.add_tag(task_gid, tag_gid)
        await session.commit_async()
    ↓ (SaveSession handles API calls, change tracking)
    return await self.get_async(task_gid)  ← Updated Task
    ↓
User receives: Task object with tag added
```

### Flow 2: P3 Name Resolution (When tag is name)

```
User Code:
  await client.tasks.add_tag_async(task_gid, "Urgent")
    ↓
TasksClient.add_tag_async checks if "Urgent" is GID or name
    ↓
If name (not GID pattern):
    ↓
    resolver = NameResolver(client, session._name_cache)
    gid = await resolver.resolve_tag_async("Urgent")
        ↓
        Check cache: "tag:Urgent" → miss
        ↓
        Fetch workspace tags: await client.tags.list_for_workspace_async()
        ↓
        Find exact match (case-insensitive)
        ↓
        Cache result
        ↓
        Return GID
    ↓
    Continue with SaveSession.add_tag(task_gid, resolved_gid)
```

### Flow 3: P2/P4 Auto-tracking (task.save())

```
User Code:
  task = await client.tasks.get(task_gid)
    ↓ (client stores reference in task._client)
  task.custom_fields["Priority"] = "High"
    ↓ (CustomFieldAccessor.set() called)
    ↓ (modification recorded in _modifications dict)
  await task.save()
    ↓
    Task.save_async() creates implicit SaveSession:
        async with SaveSession(self._client) as session:
            session.track(self)
                ↓ (ChangeTracker captures snapshot)
            await session.commit_async()
                ↓ (Detects changes between snapshot and current state)
                ↓ (Includes modified fields in API payload)
    ↓
    return self  ← Updated Task

User receives: Task with changes committed
```

---

## Integration Points & Dependencies

### Modified Files

| File | Changes | Impact | Backward Compat |
|------|---------|--------|---|
| `src/autom8_asana/clients/tasks.py` | Add 12 methods (P1) | New convenience API | ✓ Additive |
| `src/autom8_asana/models/task.py` | Add `_client`, `custom_fields`, `save()`, `refresh()` (P2, P4) | Auto-tracking & ergonomic fields | ✓ PrivateAttr not serialized |
| `src/autom8_asana/models/custom_field_accessor.py` | Add `__getitem__`, `__setitem__`, `__delitem__` (P2) | Dict-style access | ✓ Additive |
| `src/autom8_asana/exceptions.py` | Add `NameNotFoundError` (P3) | Better error messages | ✓ Extends hierarchy |
| `src/autom8_asana/client.py` | Enhance constructor for workspace detection (P5) | Simplified init | ✓ Backward compatible |
| `src/autom8_asana/persistence/session.py` | Add `_name_cache`, `_name_resolver` (P3 support) | Cache management | ✓ Internal only |

### New Files

| File | Purpose |
|------|---------|
| `src/autom8_asana/clients/name_resolver.py` | NameResolver class for name→GID resolution |

### Dependency Graph

```
SaveSession (existing, unchanged)
    ↑
    ├─ Used by P1 Direct Methods
    ├─ Used by P4 Task.save()
    ├─ Enhanced with P3 name cache

Task Model (existing, enhance)
    ↑
    ├─ Add _client reference (P4)
    ├─ Add custom_fields property (P2)
    ├─ Add save/refresh methods (P4)

CustomFieldAccessor (existing, enhance)
    ├─ Add __getitem__ (P2)
    ├─ Add __setitem__ (P2)
    ├─ Add __delitem__ (P2)

NameResolver (new)
    ├─ Used by P3 resolve_* methods
    ├─ Integrated into TasksClient.add_tag_async etc.
    ├─ Per-SaveSession cache lifecycle

AsanaClient (existing, enhance)
    ├─ Enhanced constructor for workspace detection (P5)
    ├─ Provides default_workspace_gid to NameResolver
```

**No Circular Dependencies:** Task doesn't import TasksClient at runtime (uses TYPE_CHECKING).

---

## Method Signatures & Contracts

### P1: Direct Methods (TasksClient)

```python
# Async
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task
async def remove_tag_async(self, task_gid: str, tag_gid: str) -> Task
async def move_to_section_async(self, task_gid: str, section_gid: str, project_gid: str) -> Task
async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task
async def add_to_project_async(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
async def remove_from_project_async(self, task_gid: str, project_gid: str) -> Task

# Sync wrappers
def add_tag(self, task_gid: str, tag_gid: str) -> Task
def remove_tag(self, task_gid: str, tag_gid: str) -> Task
def move_to_section(self, task_gid: str, section_gid: str, project_gid: str) -> Task
def set_assignee(self, task_gid: str, assignee_gid: str) -> Task
def add_to_project(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
def remove_from_project(self, task_gid: str, project_gid: str) -> Task
```

### P2: Custom Fields (Task)

```python
@property
def custom_fields(self) -> CustomFieldAccessor

# CustomFieldAccessor methods
def __getitem__(self, name_or_gid: str) -> Any  # Raises KeyError if missing
def __setitem__(self, name_or_gid: str, value: Any) -> None
def __delitem__(self, name_or_gid: str) -> None
```

### P3: Name Resolution (NameResolver)

```python
async def resolve_tag_async(self, name_or_gid: str, project_gid: str | None = None) -> str
async def resolve_section_async(self, name_or_gid: str, project_gid: str) -> str
async def resolve_project_async(self, name_or_gid: str, workspace_gid: str) -> str
async def resolve_assignee_async(self, name_or_gid: str, workspace_gid: str) -> str

# Sync wrappers
def resolve_tag(self, name_or_gid: str, project_gid: str | None = None) -> str
def resolve_section(self, name_or_gid: str, project_gid: str) -> str
def resolve_project(self, name_or_gid: str, workspace_gid: str) -> str
def resolve_assignee(self, name_or_gid: str, workspace_gid: str) -> str
```

### P4: Auto-tracking (Task)

```python
async def save_async(self) -> Task
def save(self) -> Task
async def refresh_async(self) -> Task
def refresh(self) -> Task
```

### P5: Client Constructor (AsanaClient)

```python
def __init__(
    self,
    token: str,
    workspace_gid: str | None = None,
    batch_size: int = 10,
    max_concurrent: int = 15,
    # ... other params (unchanged) ...
) -> None
```

---

## Complexity Level Justification

**Assessment: Module**

Rationale:
- **Clear API surface:** 12 direct methods, 4 Task methods, 1 client variant, 1 new resolver class
- **Minimal new infrastructure:** NameResolver is straightforward list + cache; no async primitives or complex patterns
- **Leverage existing patterns:** PrivateAttr already in Task; SaveSession handles sessions; CustomFieldAccessor exists
- **Team capability:** SDK team understands async/sync wrappers, SaveSession patterns, API design
- **Clear boundaries:** Each component has single responsibility
- **No external contracts:** All changes are additive; no API surface changes
- **Testability:** Each component can be tested independently
- **No distributed coordination:** Changes are local to SDK; no cross-service patterns

**Why Not Script?** Too many integration points (6 modified files, 1 new file).

**Why Not Service?** Doesn't require distributed coordination, no new infrastructure, no operational complexity.

**Appropriate: Module** - Clear boundaries, leverages existing patterns, team capability sufficient.

---

## Testing Strategy

### P1 Direct Methods Testing

**Test File:** `tests/unit/clients/test_tasks_direct_methods.py`

**Test Cases:**
- `test_add_tag_async_returns_updated_task` - Method returns Task
- `test_add_tag_async_raises_on_invalid_gid` - Raises APIError for invalid task
- `test_add_tag_sync_delegates_to_async` - Sync wrapper works
- `test_remove_tag_async` - Remove works
- `test_move_to_section_async` - Move works
- `test_set_assignee_async` - Assignee set works
- `test_add_to_project_async` - Add to project works
- `test_add_to_project_with_section` - Section optional works
- `test_remove_from_project_async` - Remove from project works
- Integration test: Full round-trip with mocked SaveSession

**Acceptance:** All P1 tests pass; return types are Task objects; sync wrappers work

### P2 Custom Field Tests

**Test File:** `tests/unit/models/test_custom_field_dict_access.py`

**Test Cases:**
- `test_getitem_returns_value` - `custom_fields["Priority"]` works
- `test_getitem_missing_raises_key_error` - Raises KeyError for missing field
- `test_setitem_records_modification` - Setting marks dirty
- `test_type_preservation_enum` - Enum values preserve dict structure
- `test_type_preservation_number` - Number values preserved
- `test_type_preservation_date` - Date strings preserved
- `test_backward_compat_get_custom_fields` - Old API still works
- `test_delitem_removes_field` - Delete works

**Acceptance:** Dict syntax works; types preserved; no regressions in existing tests

### P3 Name Resolution Tests

**Test File:** `tests/unit/clients/test_name_resolver.py`

**Test Cases:**
- `test_resolve_tag_name_returns_gid` - Name lookup succeeds
- `test_resolve_tag_gid_passthrough` - GID passthrough works
- `test_resolve_tag_missing_raises_error` - NameNotFoundError with suggestions
- `test_suggestions_fuzzy_match` - Similar names suggested
- `test_caching_per_session` - Cache hit within session
- `test_resolve_section_project_scoped` - Project-scoped resolution
- `test_resolve_project_workspace_scoped` - Workspace-scoped resolution
- `test_resolve_assignee_by_name_and_email` - User resolution works

**Acceptance:** Name resolution works; caching verified; error messages helpful

### P4 Auto-tracking Tests

**Test File:** `tests/unit/models/test_task_save.py`

**Test Cases:**
- `test_save_async_commits_changes` - Field changes persisted
- `test_save_async_dirty_detection` - No API call if clean
- `test_save_requires_client_reference` - Raises ValueError if no client
- `test_refresh_async_fetches_latest` - Latest state from API
- `test_refresh_clears_modifications` - Pending changes discarded
- `test_save_with_custom_fields` - Custom field changes included
- Integration test: Full save/refresh cycle

**Acceptance:** Save works; refresh works; client reference required

### P5 Client Constructor Tests

**Test File:** `tests/unit/client/test_constructor.py`

**Test Cases:**
- `test_single_arg_constructor` - `AsanaClient(token)` works
- `test_auto_detect_single_workspace` - Auto-detects if exactly one
- `test_error_multiple_workspaces` - Raises ConfigurationError
- `test_error_no_workspaces` - Raises ConfigurationError
- `test_full_constructor_unchanged` - Original signature still works

**Acceptance:** Single-arg pattern works; auto-detection works; backward compatible

### Backward Compatibility Testing

**Test Scope:** All existing tests must pass unchanged

- All existing SaveSession tests pass
- All existing custom field tests pass
- All existing TasksClient tests pass
- All existing exception tests pass
- No import path changes
- No breaking method signature changes

**Coverage Target:** >80% for all new code

---

## Risk Assessment & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Circular imports (Task ↔ TasksClient) | Low | High | Use TYPE_CHECKING for imports; ref set at runtime |
| Client reference memory leak | Low | Medium | Strong ref acceptable; can upgrade to WeakRef if needed |
| Name cache staleness | Low | Medium | Per-SaveSession cache (zero staleness within session) |
| Task.save() in SaveSession context | Low | Medium | Document: only saves field changes; don't nest SaveSession |
| Regression in existing tests | Low | High | Run full test suite in CI |
| Concurrent saves of same Task | Low | Medium | Document: SaveSession handles last-write-wins |
| Performance of name resolution (list all) | Low | Medium | Cache results; consider pagination for large workspaces |
| Exception class naming conflict | Very Low | Low | NameNotFoundError is new; unique name |

**Mitigation Examples:**

```python
# Circular import mitigation
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

class Task:
    _client: Any = PrivateAttr(default=None)  # Stores at runtime

# Memory leak mitigation (if needed in future)
from weakref import ref
_client_ref = PrivateAttr(default=None)

@property
def _client(self) -> AsanaClient | None:
    return self._client_ref() if self._client_ref else None
```

---

## Implementation Sequencing

**Recommended Order (Guides Engineer in Sessions 4-6):**

### Session 4: P1 Direct Methods (Independent)
1. Add 6 async methods to TasksClient (add_tag, remove_tag, move_to_section, set_assignee, add_to_project, remove_from_project)
2. Add 6 sync wrapper methods
3. Update TasksClient to set `task._client` reference after creating Task
4. Write P1 tests
5. Verify backward compatibility

**Why first:** P1 is independent, clear scope, no dependencies.

### Session 5a: P2 Custom Fields (Can run parallel)
1. Add `__getitem__`, `__setitem__`, `__delitem__` to CustomFieldAccessor
2. Add `custom_fields` property to Task
3. Write P2 tests
4. Verify type preservation

**Why parallel with P1:** Independent; no dependencies on P1.

### Session 5b: P3 Name Resolution (After P1)
1. Create NameResolver class in new file
2. Implement resolve_tag, resolve_section, resolve_project, resolve_assignee methods
3. Add sync wrappers for all
4. Add NameNotFoundError exception
5. Integrate NameResolver into SaveSession (add cache, accessor)
6. Update P1 methods to use name resolution (polymorphic input)
7. Write P3 tests

**Why after P1:** Name resolution enhances P1; P1 must complete first.

### Session 6a: P4 Auto-tracking (After P2)
1. Add `_client` PrivateAttr to Task
2. Add `save_async`, `save`, `refresh_async`, `refresh` methods
3. Write P4 tests

**Why after P2:** P4 depends on P2 dirty tracking already working.

### Session 6b: P5 Client Constructor (Anytime)
1. Enhance AsanaClient constructor for workspace auto-detection
2. Add ConfigurationError if needed
3. Write P5 tests
4. Backward compatibility verified

**Why independent:** Can run anytime; no dependencies.

### Final: Full Integration Tests
1. End-to-end test: Direct method → SaveSession → API
2. End-to-end test: Name resolution → Task update → save
3. End-to-end test: Custom fields → save → refresh

**Critical Path:** P2 → P4 (must complete P2 before P4)

---

## Success Criteria for Handoff to Engineer

This TDD is ready for Engineer handoff when:

- [x] Every FR from PRD-SDKUX has a design response
- [x] Component boundaries are explicit
- [x] Method signatures are fully defined
- [x] All ADRs explain significant decisions
- [x] Implementation sequence clear (5 sessions)
- [x] Testing strategy detailed for each priority
- [x] Risk mitigations documented
- [x] No ambiguity remains

---

## Sign-Off

**Architect:** ✓ Design complete, ready for implementation
**Discovery Validation:** ✓ All 6 questions answered, all evidence cited
**PRD Alignment:** ✓ All 41 FRs addressed, all acceptance criteria traceable
**Module Assessment:** ✓ Complexity justified, team capable, patterns leveraged

---
