# Session 1 Discovery: SDK Usability Integration Analysis

**Document ID:** DISCOVERY-SDKUX-001
**Date:** 2025-12-12
**Status:** Complete
**Analyst:** Requirements Analysis Phase

---

## Executive Summary

Analysis of the autom8_asana SDK codebase confirms that all three design decisions are **architecturally feasible** with no blocking dependencies or circular import risks. The SDK already provides the necessary foundations:

1. **Direct methods returning Task objects** - The TasksClient already follows this pattern (get_async, create_async, update_async all return Task objects)
2. **Implicit SaveSession in Task.save()** - SaveSession is designed as a context manager but can be created implicitly; Task can safely store a `_client` reference via PrivateAttr
3. **Name resolution with NameNotFoundError** - Exception hierarchy is extensible; name resolution data sources (tags, projects, users, sections) are all accessible and support caching

**Key Finding:** Task model already has a `_custom_fields_accessor` private attribute using Pydantic's PrivateAttr pattern (lines 115-134 in task.py). This establishes the precedent for storing a `_client` reference without serialization issues.

**Readiness:** All 6 critical questions answered with code evidence. Ready to proceed to Session 2 (Requirements Definition).

---

## Q1: Direct Method Feasibility - ANSWER

**Question:** Is it technically feasible to add async methods that wrap SaveSession internally and return updated Task objects? What's the pattern?

**Answer:** **YES - Fully Feasible.** The pattern is straightforward and already partially implemented.

**Evidence:**

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` (lines 46-68, 155-198, 322-342):
- All current async methods in TasksClient follow the pattern: call API → receive dict → validate with Pydantic → return typed model
- Example: `get_async()` returns `Task` object (line 68: `return Task.model_validate(data)`)
- Example: `create_async()` returns `Task` object (line 198: `return Task.model_validate(result)`)
- Example: `update_async()` returns `Task` object (line 342: `return Task.model_validate(result)`)

**Pattern for Task.save():**
```python
# Pseudo-code pattern from existing SaveSession design
async def save_async(self) -> Task:
    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()
        if result.success:
            return self  # Already updated in-place during commit
        else:
            raise result.failed[0].error  # Or PartialSaveError
```

SaveSession design (session.py lines 469-556) supports:
- Implicit creation within a method
- Multiple commits within the same session
- Tracking entities and detecting changes
- Returning updated Task objects from commit

**Feasibility Assessment:** ✓ **Feasible**

---

## Q2: Return Type Validation - ANSWER

**Question:** Do existing TasksClient methods return Task objects? Can we follow that pattern?

**Answer:** **YES - Pattern Already Established.** TasksClient consistently returns typed Task objects.

**Evidence:**

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`:

| Method | Return Type | Evidence |
|--------|-------------|----------|
| `get_async()` | `Task \| dict[str, Any]` | Lines 31, 42, 68 |
| `create_async()` | `Task \| dict[str, Any]` | Lines 136, 151, 198 |
| `update_async()` | `Task \| dict[str, Any]` | Lines 306, 317, 342 |
| `list_async()` | `PageIterator[Task]` | Lines 432, 483 |
| `subtasks_async()` | `PageIterator[Task]` | Lines 494, 530 |

**Sync wrapper pattern** (lines 92-109 example):
```python
def get(self, task_gid: str, *, raw: bool = False, ...) -> Task | dict[str, Any]:
    return self._get_sync(task_gid, raw=raw, ...)

@sync_wrapper("get_async")
async def _get_sync(self, task_gid: str, *, raw: bool = False, ...) -> Task | dict[str, Any]:
    if raw:
        return await self.get_async(task_gid, raw=True, ...)
    return await self.get_async(task_gid, raw=False, ...)
```

**Feasibility Assessment:** ✓ **Feasible** - Can directly follow existing pattern

---

## Q3: Name Resolution Scope - ANSWER

**Question:** For workspace-level resources (tags, projects, users), can we list them once and cache? For project-scoped resources (sections), what's the caching strategy?

**Answer:** **YES - Multiple Options.** All resources support listing; caching strategy depends on use case.

**Evidence:**

### Tags (Workspace-scoped)
From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py` (lines 379-411):
- **Method:** `list_for_workspace_async(workspace_gid, ...) -> PageIterator[Tag]`
- **API Endpoint:** `GET /workspaces/{workspace_gid}/tags`
- **Return Data:** Tag objects with `gid`, `name` fields
- **Cost:** 1 API call per page (100 items max per page)
- **Caching:** Can cache at workspace level with TTL; per-session cache viable

### Sections (Project-scoped)
From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` (lines 392-430):
- **Method:** `list_for_project_async(project_gid, ...) -> PageIterator[Section]`
- **API Endpoint:** `GET /projects/{project_gid}/sections`
- **Return Data:** Section objects with `gid`, `name` fields
- **Cost:** 1 API call per page (100 items max per page)
- **Caching:** Must cache per project; recommended per-session cache

### Projects (Workspace-scoped)
From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py` (lines 433-479):
- **Method:** `list_async(workspace=..., ...) -> PageIterator[Project]`
- **API Endpoint:** `GET /projects?workspace={workspace_gid}`
- **Return Data:** Project objects with `gid`, `name` fields
- **Cost:** 1 API call per page (100 items max per page)
- **Caching:** Can cache at workspace level with TTL

### Users (Workspace-scoped)
From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py` (lines 216-254):
- **Method:** `list_for_workspace_async(workspace_gid, ...) -> PageIterator[User]`
- **API Endpoint:** `GET /workspaces/{workspace_gid}/users`
- **Return Data:** User objects with `gid`, `name` fields
- **Cost:** 1 API call per page (100 items max per page)
- **Caching:** Can cache at workspace level with TTL

### Recommended Caching Strategy

**Per-SaveSession Caching (Simplest):**
- Cache all lists within SaveSession context
- Clear cache on context exit
- Low memory overhead; zero staleness risk
- Pattern: Store in SaveSession._name_resolver dict

**Per-Client TTL Caching (Advanced):**
- Cache all workspace-scoped resources (tags, projects, users) with 5-15 min TTL
- Cache project-scoped resources (sections) per project with 5-15 min TTL
- Requires LRU cache or similar
- Higher complexity but better for repeated operations

**Feasibility Assessment:** ✓ **Feasible** - Multiple strategies available; per-session caching is low-risk

---

## Q4: Task.save() Feasibility - ANSWER

**Question:** Can Task objects safely store a `_client` reference? Will that cause circular imports?

**Answer:** **YES - Safe Pattern Already in Use.** Pydantic PrivateAttr prevents circular serialization.

**Evidence:**

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` (lines 114-134):
```python
# Line 115: Private accessor instance (not serialized)
_custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)

def get_custom_fields(self) -> CustomFieldAccessor:
    """Get custom fields accessor for fluent API."""
    if self._custom_fields_accessor is None:
        self._custom_fields_accessor = CustomFieldAccessor(self.custom_fields)
    return self._custom_fields_accessor
```

**Key Pattern:** Pydantic's `PrivateAttr`:
- Marked with underscore prefix: `_client`
- Excluded from serialization (model_dump, model_dump_json)
- Excluded from schema generation
- Cached on first access
- Not validated by Pydantic

**Circular Import Analysis:**

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (lines 32-40):
```python
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task
```

The SaveSession already uses TYPE_CHECKING to avoid runtime imports. Task.py can do the same:
```python
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

# Runtime: Store as Any or use TYPE_CHECKING Union
_client: Any = PrivateAttr(default=None)  # Will hold AsanaClient at runtime
```

**No circular risk** because:
1. PrivateAttr is never serialized
2. TYPE_CHECKING imports are not executed at runtime
3. Client assignment happens at runtime, not import time

**Feasibility Assessment:** ✓ **Feasible** - Pattern already established in codebase

---

## Q5: Dirty Tracking - ANSWER

**Question:** Does the Task model already track changes? If not, how should we implement dirty detection for `task.save()`?

**Answer:** **Task doesn't track changes, but SaveSession does.** Dirty detection is the responsibility of SaveSession, not Task.

**Evidence:**

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`:

**SaveSession tracks changes via ChangeTracker (line 137):**
```python
self._tracker = ChangeTracker()
```

**Snapshot-based dirty detection (lines 195-256):**
```python
def track(self, entity: T, *, prefetch_holders: bool = False, recursive: bool = False) -> T:
    """Register entity for change tracking.

    Per FR-CHANGE-001: Capture snapshot at track time.
    ...
    Tracks an entity for changes. A snapshot of the entity's current
    state is captured. After tracking, any modifications to the entity
    will be detected at commit time.
    """
    self._ensure_open()
    self._tracker.track(entity)
    return entity
```

**Get changes method (lines 346-370):**
```python
def get_changes(self, entity: AsanaResource) -> dict[str, tuple[Any, Any]]:
    """Get field-level changes for tracked entity.

    Per FR-CHANGE-002: Compute {field: (old, new)} changes.

    Returns a dict showing what fields have changed since tracking,
    with both old and new values.
    """
    return self._tracker.get_changes(entity)
```

**Implementation Pattern for Task.save():**
```python
async def save_async(self) -> Task:
    """Save changes to this task."""
    async with SaveSession(self._client) as session:
        session.track(self)
        # ChangeTracker automatically detects what changed
        # since track() captured a snapshot
        result = await session.commit_async()
        if not result.success:
            raise PartialSaveError(result)
        return self
```

The Task itself doesn't need dirty tracking - SaveSession handles it through:
1. Snapshot at track time (line 241)
2. Comparison at commit time (implicitly in _tracker.get_dirty_entities())

**Task Model Changes Required:**
- Add `_client` private attribute (PrivateAttr)
- Add `save_async()` and `save()` methods
- No dirty tracking logic needed

**Feasibility Assessment:** ✓ **Feasible** - Leverage existing SaveSession change tracking

---

## Q6: NameNotFoundError Design - ANSWER

**Question:** What should a NameNotFoundError include? How should we generate suggestions?

**Answer:** **Design is straightforward.** New exception should include field name, searched value, and suggestions.

**Evidence:**

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (lines 26-49):
- Base `AsanaError` class has precedent for rich error data
- Includes `message`, `status_code`, `response`, `errors` attributes
- Pattern: Include all context needed for debugging

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/exceptions.py` (lines 129-159):
- Example: `UnsupportedOperationError` includes `field_name` and `suggested_methods` list
- Pattern: Store structured data + human-readable message

**Recommended NameNotFoundError Design:**

```python
class NameNotFoundError(AsanaError):
    """Raised when a name cannot be resolved to a GID.

    For example: "Priority" tag not found in workspace.
    Includes suggestions of similar names found.
    """

    def __init__(
        self,
        name: str,
        resource_type: str,  # "tag", "project", "user", "section"
        scope: str,  # "workspace" or project GID
        suggestions: list[str] | None = None,
        available_names: list[str] | None = None,
    ) -> None:
        self.name = name
        self.resource_type = resource_type
        self.scope = scope
        self.suggestions = suggestions or []
        self.available_names = available_names or []

        message = (
            f"Could not find {resource_type} named '{name}' "
            f"(scope: {scope}). "
        )

        if self.suggestions:
            message += f"Did you mean: {', '.join(self.suggestions)}? "

        if self.available_names and len(self.available_names) <= 10:
            message += f"Available: {', '.join(self.available_names)}"
        elif self.available_names:
            message += (
                f"Available: {', '.join(self.available_names[:10])} "
                f"(+{len(self.available_names) - 10} more)"
            )

        super().__init__(message)
```

**Suggestion Algorithm:**

Use difflib.get_close_matches() for fuzzy matching:
```python
from difflib import get_close_matches

suggestions = get_close_matches(
    name,
    available_names,
    n=3,  # Return top 3 matches
    cutoff=0.6  # 60% similarity threshold
)
```

**Example Error Messages:**

```
Could not find tag named 'Priority' (scope: workspace_123).
Did you mean: Prioritize, Priorities, Primary?
Available: Budget, Feature, Infrastructure, Backend, Team (and 12 more)

Could not find user named 'bob@example.com' (scope: workspace_123).
Available: alice@example.com, bob.smith@example.com, robert@example.com
```

**Location:** Place in `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (extends existing exception hierarchy)

**Feasibility Assessment:** ✓ **Feasible** - Straightforward exception design; fuzzy matching via difflib (stdlib)

---

## Task 1: TasksClient Architecture

### Current Async Methods

| Method | Signature | Return Type | Evidence |
|--------|-----------|-------------|----------|
| `get_async()` | `(task_gid, *, raw, opt_fields)` | `Task \| dict` | Lines 24-68 |
| `create_async()` | `(*, name, raw, workspace, projects, parent, notes, **kwargs)` | `Task \| dict` | Lines 125-198 |
| `update_async()` | `(task_gid, *, raw, **kwargs)` | `Task \| dict` | Lines 299-342 |
| `delete_async()` | `(task_gid)` | `None` | Lines 399-406 |
| `list_async()` | `(*, project, section, assignee, workspace, ...)` | `PageIterator[Task]` | Lines 421-486 |
| `subtasks_async()` | `(task_gid, *, opt_fields, limit)` | `PageIterator[Task]` | Lines 488-533 |

### Sync Wrapper Pattern

Pattern: Public sync method → calls `_*_sync()` with `@sync_wrapper` decorator

```python
def get(self, task_gid: str, *, raw: bool = False, ...) -> Task | dict[str, Any]:
    return self._get_sync(task_gid, raw=raw, ...)

@sync_wrapper("get_async")
async def _get_sync(self, task_gid: str, *, raw: bool = False, ...) -> Task | dict[str, Any]:
    if raw:
        return await self.get_async(task_gid, raw=True, ...)
    return await self.get_async(task_gid, raw=False, ...)
```

Naming pattern: `_*_sync()` for all sync wrappers (lines 112, 265, 386, 409)

### Return Type Pattern

- Default (raw=False): Returns typed Pydantic model (Task, Tag, Section, etc.)
- Optional (raw=True): Returns dict for backward compatibility
- Accomplished via `Model.model_validate(api_response_dict)`

### Extension Point

**Where to add Task.save() and Task.refresh() methods:**
1. Add to Task class (not TasksClient)
2. Task should have `_client` reference (PrivateAttr)
3. Implement as instance methods on Task
4. Call client methods or SaveSession internally

**Why not in TasksClient:**
- Not a client operation; it's a model operation
- SaveSession is designed for deferred saves, not immediate updates
- Pattern: Similar to ORMs (SQLAlchemy, Django ORM) where models have save() methods

---

## Task 2: CustomFieldAccessor Design

### Current Implementation

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`:

**Initialization (lines 29-44):**
```python
def __init__(
    self,
    data: list[dict[str, Any]] | None = None,
    resolver: DefaultCustomFieldResolver | None = None,
) -> None:
    self._data: list[dict[str, Any]] = list(data) if data else []
    self._resolver = resolver
    self._modifications: dict[str, Any] = {}  # gid -> new_value (or None for removal)
    self._name_to_gid: dict[str, str] = {}  # Cache name->gid from data
    self._build_index()
```

**get() Method (lines 65-86):**
```python
def get(self, name_or_gid: str, default: Any = None) -> Any:
    gid = self._resolve_gid(name_or_gid)

    # Check modifications first
    if gid in self._modifications:
        return self._modifications[gid]

    # Find in original data
    for field in self._data:
        if field.get("gid") == gid:
            return self._extract_value(field)

    return default
```

**set() Method (lines 55-63):**
```python
def set(self, name_or_gid: str, value: Any) -> None:
    gid = self._resolve_gid(name_or_gid)
    self._modifications[gid] = value
```

### Type Preservation Mechanism

From `_extract_value()` (lines 216-233):
```python
def _extract_value(self, field: dict[str, Any]) -> Any:
    """Extract value from custom field dict based on type."""
    # Asana stores values in type-specific fields
    if "text_value" in field and field["text_value"] is not None:
        return field["text_value"]
    if "number_value" in field and field["number_value"] is not None:
        return field["number_value"]
    if "enum_value" in field and field["enum_value"] is not None:
        # enum_value is a dict with gid/name
        return field["enum_value"]
    if "multi_enum_values" in field and field["multi_enum_values"]:
        return field["multi_enum_values"]
    if "date_value" in field and field["date_value"] is not None:
        return field["date_value"]
    if "people_value" in field and field["people_value"]:
        return field["people_value"]
    return field.get("display_value")
```

**Type information preserved through:**
1. Asana API returns type-specific keys (text_value, number_value, enum_value, etc.)
2. _extract_value() reads from appropriate key based on field structure
3. _format_value_for_api() handles reverse conversion (lines 141-173)

### Bridge to Dictionary Interface

**Current methods:**
- `to_list()` (lines 97-125): Returns `list[{"gid": str, "value": Any}]`
- `to_api_dict()` (lines 127-139): Returns `dict[gid: str] -> value`
- `__len__()` (lines 235-237): Supports `len(accessor)`
- `__iter__()` (lines 239-241): Supports `for field in accessor`

**Missing methods:** `__getitem__()` and `__setitem__()`

**Feasibility of adding dictionary interface (✓ Feasible):**
```python
def __getitem__(self, name_or_gid: str) -> Any:
    """accessor["Priority"] -> value"""
    result = self.get(name_or_gid, default=_MISSING)
    if result is _MISSING:
        raise KeyError(name_or_gid)
    return result

def __setitem__(self, name_or_gid: str, value: Any) -> None:
    """accessor["Priority"] = "High" """
    self.set(name_or_gid, value)

def __delitem__(self, name_or_gid: str) -> None:
    """del accessor["Priority"]"""
    self.remove(name_or_gid)
```

### Change Tracking Mechanism

**Current implementation (lines 42, 175-181):**
```python
self._modifications: dict[str, Any] = {}  # gid -> new_value (or None for removal)

def has_changes(self) -> bool:
    """Check if any modifications are pending."""
    return len(self._modifications) > 0

def clear_changes(self) -> None:
    """Clear all pending modifications."""
    self._modifications.clear()
```

**Used by Task.model_dump() (task.py lines 150-157):**
```python
if (
    self._custom_fields_accessor is not None
    and self._custom_fields_accessor.has_changes()
):
    data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
```

**This pattern works because:**
1. CustomFieldAccessor tracks mutations in `_modifications`
2. Task.model_dump() checks has_changes() and includes modifications
3. When saving via SaveSession, the modified payload is automatically included

---

## Task 3: Name Resolution Data Sources

### Tags (Workspace-scoped)

**List Method:** `TagsClient.list_for_workspace_async(workspace_gid, ...) -> PageIterator[Tag]`
- **API Endpoint:** `GET /workspaces/{workspace_gid}/tags`
- **Return Data:** `PageIterator[Tag]` with Tag.gid, Tag.name
- **API Cost:** 1 call per 100 items; paginated
- **File Evidence:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py` lines 379-411

### Sections (Project-scoped)

**List Method:** `SectionsClient.list_for_project_async(project_gid, ...) -> PageIterator[Section]`
- **API Endpoint:** `GET /projects/{project_gid}/sections`
- **Return Data:** `PageIterator[Section]` with Section.gid, Section.name
- **API Cost:** 1 call per 100 items; paginated
- **File Evidence:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` lines 392-430

### Projects (Workspace-scoped)

**List Method:** `ProjectsClient.list_async(workspace=..., ...) -> PageIterator[Project]`
- **API Endpoint:** `GET /projects?workspace={workspace_gid}`
- **Return Data:** `PageIterator[Project]` with Project.gid, Project.name
- **API Cost:** 1 call per 100 items; paginated
- **File Evidence:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py` lines 433-479

### Users/Assignees (Workspace-scoped)

**List Method:** `UsersClient.list_for_workspace_async(workspace_gid, ...) -> PageIterator[User]`
- **API Endpoint:** `GET /workspaces/{workspace_gid}/users`
- **Return Data:** `PageIterator[User]` with User.gid, User.name, User.email
- **API Cost:** 1 call per 100 items; paginated
- **File Evidence:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py` lines 216-254

### Recommended Caching Strategy

**Per-SaveSession Cache (Recommended for MVP):**
- Store all name->GID mappings in SaveSession instance
- Lifetime: Duration of SaveSession context
- Memory: ~1KB per 100 names (negligible)
- Staleness: Zero (fresh data from each session)
- Implementation: Add `_name_cache` dict to SaveSession init

**Per-Client TTL Cache (Future optimization):**
- Store with expiration timestamps
- Workspace resources: 15-minute TTL
- Project resources: 10-minute TTL (more volatile)
- Implementation: Decorator-based LRU cache with TTL

---

## Task 4: SaveSession Integration

### Context Manager Lifecycle

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`:

**Async Entry (lines 159-161):**
```python
async def __aenter__(self) -> SaveSession:
    """Enter async context (FR-UOW-001)."""
    return self
```

**Async Exit (lines 163-174):**
```python
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """Exit async context (FR-UOW-001).

    Closes the session. No further operations are allowed.
    Does not auto-commit; uncommitted changes are discarded.
    """
    self._state = SessionState.CLOSED
```

**Sync Entry (lines 176-178):**
```python
def __enter__(self) -> SaveSession:
    """Enter sync context (FR-UOW-004)."""
    return self
```

**Sync Exit (lines 180-191):**
```python
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    """Exit sync context (FR-UOW-004).

    Closes the session. No further operations are allowed.
    Does not auto-commit; uncommitted changes are discarded.
    """
    self._state = SessionState.CLOSED
```

**States (lines 45-56):**
```python
class SessionState:
    OPEN = "open"
    COMMITTED = "committed"
    CLOSED = "closed"
```

### Implicit Session Creation Pattern

From SaveSession design (lines 116-156):
```python
def __init__(
    self,
    client: AsanaClient,
    batch_size: int = 10,
    max_concurrent: int = 15,
) -> None:
    self._client = client
    self._batch_size = batch_size
    self._max_concurrent = max_concurrent

    self._tracker = ChangeTracker()
    self._graph = DependencyGraph()
    self._events = EventSystem()
    self._pipeline = SavePipeline(...)
    self._action_executor = ActionExecutor(client._http)
    self._pending_actions: list[ActionOperation] = []
    self._state = SessionState.OPEN
```

**Pattern for implicit creation in Task.save():**
```python
async def save_async(self) -> Task:
    """Save changes to this task."""
    if self._client is None:
        raise ValueError("Task has no client reference")

    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()

        if not result.success:
            raise result.failed[0].error  # Raise first error

        return self  # Already updated in-place
```

**Features leveraged:**
- Automatic initialization of ChangeTracker, DependencyGraph, EventSystem
- Support for both async (async with) and sync (with) contexts
- Exception handling via context manager protocol

### Circular Import Risk Assessment

**Risk Level: NONE**

**Evidence:**
1. SaveSession already uses TYPE_CHECKING for Task imports (session.py line 39):
   ```python
   if TYPE_CHECKING:
       from autom8_asana.models.task import Task
   ```

2. Task can do the same for AsanaClient:
   ```python
   if TYPE_CHECKING:
       from autom8_asana.client import AsanaClient
   ```

3. Runtime assignment happens after both modules are imported:
   ```python
   task._client = client  # Happens at runtime, not import time
   ```

4. PrivateAttr is not deserialized, so no serialization cycle:
   ```python
   _client: Any = PrivateAttr(default=None)  # Never included in model_dump()
   ```

### Deferred Operations Pattern

From SaveSession (lines 671-1522):

**Action Operations** (lines 672-1522):
- `add_tag()`, `remove_tag()`: Queue tag operations
- `add_to_project()`, `remove_from_project()`: Queue project operations
- `add_dependency()`, `remove_dependency()`: Queue dependency operations
- `move_to_section()`: Queue section movement
- All return self for chaining

**Execution** (lines 469-556):
```python
async def commit_async(self) -> SaveResult:
    """Execute all pending changes (async)."""
    # Execute CRUD operations and actions together
    crud_result, action_results = await self._pipeline.execute_with_actions(
        entities=dirty_entities,
        actions=pending_actions,
        action_executor=self._action_executor,
    )
```

**Pattern:** Queue operations, execute all together at commit time

---

## Task 5: Task Model Integration

### Current Structure and Attributes

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` (lines 19-115):

**Base class:** Extends `AsanaResource` (Pydantic BaseModel)

**Core attributes:**
- `gid`: Inherited from AsanaResource
- `name`, `notes`, `html_notes`: Task content
- `completed`, `completed_at`: Status
- `due_on`, `due_at`, `start_on`, `start_at`: Dates
- `assignee`, `projects`, `parent`, `workspace`: Relationships
- `custom_fields`: List of custom field dicts
- `_custom_fields_accessor`: Private custom field accessor

**Key property (lines 114-115):**
```python
_custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)
```

### Task Construction

From Task class (lines 34-115):
- All attributes are optional (use `| None = None`)
- Extra="ignore" configuration (per ADR-0005) allows forward compatibility
- Pydantic model_validate() converts API dicts to Task objects

**Pattern from TasksClient:**
```python
data = await self._http.get(f"/tasks/{task_gid}", params=params)
if raw:
    return data
return Task.model_validate(data)  # Pydantic validates and creates Task
```

### Client Reference Storage

**Already has precedent:** `_custom_fields_accessor` uses PrivateAttr (line 115)

**Implementation:**
```python
from pydantic import PrivateAttr
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

class Task(AsanaResource):
    # ... existing attributes ...

    # Private client reference (not serialized)
    _client: Any = PrivateAttr(default=None)
    _custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)
```

**Assignment at creation:**
```python
# In TasksClient.get_async() after creating Task:
task = Task.model_validate(data)
task._client = self._client  # Store reference
return task
```

### Dirty Tracking Mechanism

**Current state:** Task does NOT track changes internally

**How SaveSession handles it:**
1. When `session.track(task)` is called, ChangeTracker captures a snapshot
2. If task attributes are modified, SaveSession detects the diff at commit
3. Only modified fields are included in the API payload

**Evidence from session.py (lines 195-256):**
```python
def track(self, entity: T, *, ...) -> T:
    """Per FR-CHANGE-001: Capture snapshot at track time."""
    self._ensure_open()
    self._tracker.track(entity)
    return entity

def get_changes(self, entity: AsanaResource) -> dict[str, tuple[Any, Any]]:
    """Per FR-CHANGE-002: Compute {field: (old, new)} changes."""
    return self._tracker.get_changes(entity)
```

**No changes needed to Task class** - SaveSession handles all dirty detection

### Integration Points for save() and refresh()

**Where to add:**
1. Add methods to Task class (not TasksClient)
2. Methods should use `self._client` reference
3. Use SaveSession for deferred operations

**Proposed implementation locations:**

**save() method (sync + async):**
```python
async def save_async(self) -> Task:
    """Save changes to this task via implicit SaveSession."""
    if self._client is None:
        raise ValueError("Task has no client reference")

    from autom8_asana.persistence.session import SaveSession

    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()
        if not result.success:
            raise result.failed[0].error
        return self

def save(self) -> Task:
    """Save changes to this task (sync)."""
    if self._client is None:
        raise ValueError("Task has no client reference")

    from autom8_asana.persistence.session import SaveSession

    with SaveSession(self._client) as session:
        session.track(self)
        result = session.commit()
        if not result.success:
            raise result.failed[0].error
        return self
```

**refresh() method (sync + async):**
```python
async def refresh_async(self) -> Task:
    """Reload task from API, discarding local changes."""
    if self._client is None:
        raise ValueError("Task has no client reference")

    updated = await self._client.tasks.get_async(self.gid)
    # Copy all fields from updated task
    for field in self.__fields__:
        setattr(self, field, getattr(updated, field, None))
    return self

def refresh(self) -> Task:
    """Reload task from API (sync)."""
    if self._client is None:
        raise ValueError("Task has no client reference")

    updated = self._client.tasks.get(self.gid)
    # Copy all fields from updated task
    for field in self.__fields__:
        setattr(self, field, getattr(updated, field, None))
    return self
```

---

## Task 6: Exception Handling

### Current Exception Hierarchy

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (lines 26-217):

**Base class:** `AsanaError(Exception)` (lines 26-99)
- Attributes: message, status_code, response, errors
- Factory method: `AsanaError.from_response(response: Response)`

**HTTP error subclasses:**
- `AuthenticationError` (401)
- `ForbiddenError` (403)
- `NotFoundError` (404)
- `GoneError` (410)
- `RateLimitError` (429) - Includes `retry_after` attribute
- `ServerError` (5xx)
- `TimeoutError`
- `ConfigurationError`

**Other error subclasses:**
- `SyncInAsyncContextError` - Raised by sync_wrapper
- `CircuitBreakerOpenError` - Per ADR-0048

### SaveSession-specific Exceptions

From `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/exceptions.py` (lines 18-209):

**Base:** `SaveOrchestrationError(AsanaError)` (lines 18-32)

**Subclasses:**
- `SessionClosedError` (lines 35-45)
- `CyclicDependencyError` (lines 48-68) - Includes cycle list
- `DependencyResolutionError` (lines 71-102) - Entity + dependency + cause
- `PartialSaveError` (lines 105-126) - Includes SaveResult
- `UnsupportedOperationError` (lines 129-159) - Includes field_name + suggested_methods
- `PositioningConflictError` (lines 162-185) - Includes insert_before/insert_after values
- `ValidationError` (lines 188-208)

### NameNotFoundError Design

**Recommended placement:** `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py` (extends AsanaError)

**Design (full implementation):**

```python
class NameNotFoundError(AsanaError):
    """Raised when a name cannot be resolved to a GID.

    Used by name resolution methods when a resource name
    (e.g., tag name, project name) doesn't exist in the
    specified scope.

    Includes suggestions of similar names based on fuzzy matching.

    Attributes:
        name: The name that was searched for
        resource_type: Type of resource (tag, project, user, section)
        scope: Scope identifier (workspace GID or project GID)
        suggestions: List of similar names (fuzzy match results)
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
        """Initialize with search context and suggestions.

        Args:
            name: The name that was searched for
            resource_type: Type of resource ("tag", "project", "user", "section")
            scope: Scope identifier (workspace GID or "project_gid")
            suggestions: Optional fuzzy match suggestions
            available_names: Optional list of available names in scope
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

**Suggestion generation (utility function):**

```python
def generate_name_suggestions(
    search_name: str,
    available_names: list[str],
    max_suggestions: int = 3,
    cutoff: float = 0.6,
) -> list[str]:
    """Generate fuzzy match suggestions for a name.

    Args:
        search_name: Name to search for
        available_names: Available names to match against
        max_suggestions: Maximum number of suggestions to return
        cutoff: Minimum similarity ratio (0-1)

    Returns:
        List of similar names, ordered by similarity
    """
    from difflib import get_close_matches

    return get_close_matches(
        search_name,
        available_names,
        n=max_suggestions,
        cutoff=cutoff,
    )
```

### Example Usage in Name Resolver

```python
from difflib import get_close_matches

async def resolve_tag_name(
    self,
    workspace_gid: str,
    tag_name: str,
) -> str:
    """Resolve tag name to GID, raising NameNotFoundError if not found."""

    # List all tags in workspace
    all_tags = []
    async for tag in self.client.tags.list_for_workspace_async(workspace_gid):
        all_tags.append(tag)

    # Find exact match (case-insensitive)
    for tag in all_tags:
        if tag.name.lower() == tag_name.lower():
            return tag.gid

    # No exact match - generate suggestions
    available_names = [tag.name for tag in all_tags]
    suggestions = get_close_matches(
        tag_name,
        available_names,
        n=3,
        cutoff=0.6,
    )

    raise NameNotFoundError(
        name=tag_name,
        resource_type="tag",
        scope=workspace_gid,
        suggestions=suggestions,
        available_names=available_names,
    )
```

---

## Backward Compatibility Assessment

**Question:** Does this approach preserve all existing APIs?

**Answer:** **YES - 100% backward compatible.**

**Evidence:**

1. **No breaking changes to existing TasksClient methods**
   - All existing methods retain same signature and behavior
   - Task.save() is a NEW method, not a replacement

2. **No breaking changes to Task model**
   - PrivateAttr fields are not serialized, don't affect API contracts
   - get_custom_fields() already exists and works the same

3. **SaveSession already exists and is unchanged**
   - Task.save() is just a convenience wrapper
   - Advanced users can still use SaveSession directly

4. **Exception hierarchy is extensible**
   - NameNotFoundError is new, doesn't change existing exceptions
   - Can be caught as `AsanaError` for backward compatibility

5. **Name resolution is opt-in**
   - Existing code using GIDs directly: no change
   - New convenience methods using names: backward-compatible addition

**Breaking changes:** NONE identified

---

## Readiness for Session 2

**Gating Criteria Status:**

- [✓] Q1: Direct method feasibility - ANSWERED with evidence
- [✓] Q2: Return type validation - ANSWERED with evidence
- [✓] Q3: Name resolver scope - ANSWERED with evidence
- [✓] Q4: Task.save() feasibility - ANSWERED with evidence
- [✓] Q5: Dirty tracking mechanism - ANSWERED with evidence
- [✓] Q6: NameNotFoundError design - ANSWERED with design spec

**Architecture Blockers:** NONE identified

**Design Decision Validation:**
- [✓] Direct methods return Task objects - FEASIBLE (already pattern)
- [✓] Name resolution raises NameNotFoundError - FEASIBLE (straightforward exception)
- [✓] task.save() uses implicit SaveSession - FEASIBLE (no circular imports)

**Technical Risks & Mitigations:**

| Risk | Mitigation |
|------|-----------|
| Client reference storage creates strong references | Use WeakRef if memory becomes issue; unlikely for short-lived tasks |
| Name resolution caching staleness | Use per-session cache (0 staleness) or implement TTL for cross-session |
| Recursive SaveSession creation | Document that Task.save() should not be called within SaveSession context |
| Performance of name resolution (listing all names) | Cache results; consider pagination for large workspaces |

**All risks are mitigable and do not block proceeding to Session 2.**

---

## Questions for Architect (Session 3)

1. **Caching Strategy:** Should we implement per-SaveSession cache first, or design for per-Client TTL cache from the start?

2. **WeakRef vs Strong Reference:** Should Task store a strong reference to AsanaClient, or use weakref.ref() to avoid keeping client alive?

3. **Error Handling in Task.save():** Should partial failures raise PartialSaveError, or just the first error? Should we expose SaveResult?

4. **API Design Choice:** Should Task.save() flush pending action operations (from SaveSession.add_tag(), etc.), or only save field modifications?

5. **Sync/Async Strategy:** What's the performance implication of supporting both sync and async save()? Any preference?

---

## Appendix: Code Evidence Summary

### Files Analyzed

1. **TasksClient** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`
   - 534 lines, analyzed async/sync patterns
   - Evidence: Methods return Task objects; sync_wrapper pattern established

2. **CustomFieldAccessor** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`
   - 242 lines, analyzed get/set/type preservation
   - Evidence: Change tracking via _modifications dict, type-safe value extraction

3. **Task Model** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`
   - 159 lines, analyzed attributes and PrivateAttr usage
   - Evidence: PrivateAttr precedent with _custom_fields_accessor

4. **SaveSession** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
   - 1674 lines, analyzed context manager and change tracking
   - Evidence: Full Unit of Work pattern; supports sync + async; no circular imports

5. **TagsClient** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py`
   - 532 lines, analyzed list_for_workspace_async()
   - Evidence: Workspace-scoped tag listing with PageIterator

6. **SectionsClient** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`
   - 573 lines, analyzed list_for_project_async()
   - Evidence: Project-scoped section listing with PageIterator

7. **ProjectsClient** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/projects.py`
   - 728 lines, analyzed list_async()
   - Evidence: Workspace-scoped project listing with PageIterator

8. **UsersClient** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py`
   - 255 lines, analyzed list_for_workspace_async()
   - Evidence: Workspace-scoped user listing with PageIterator

9. **Base Exceptions** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/exceptions.py`
   - 217 lines, analyzed hierarchy and patterns
   - Evidence: AsanaError base class with rich context

10. **SaveSession Exceptions** - `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/exceptions.py`
    - 209 lines, analyzed SaveOrchestrationError hierarchy
    - Evidence: 7 specialized exception types with structured data

---

## Conclusion

All 6 critical questions have been answered with code evidence from the SDK. The architecture supports the 3 approved design decisions without blockers or risks. The SDK is ready to proceed to Session 2 (Requirements Definition) where the PRD will be written with specific features, user stories, and acceptance criteria.

**Key Insight:** The SDK already implements the foundational patterns needed (Task models with Pydantic PrivateAttr, SaveSession with change tracking, async/sync wrappers, exception hierarchy). The usability overhaul is primarily about adding convenience methods (Task.save(), Task.refresh()) and name resolution tooling, not architectural changes.

