# TDD-10: Operations & SDK Usability

> Consolidated TDD for action endpoints, subtask operations, SDK ergonomics, and async method patterns.

## Metadata

| Field | Value |
|-------|-------|
| **TDD ID** | TDD-10 |
| **Status** | Accepted |
| **Date** | 2025-12-25 |
| **Consolidated From** | TDD-0011, TDD-0013, TDD-0015 (TDD-SDKUX), TDD-0025 (TDD-DESIGN-PATTERNS-D) |
| **Related ADRs** | ADR-0025, ADR-0039, ADR-0043 |
| **Related TDDs** | TDD-04 (Batch Save Operations), TDD-03 (Resource Clients) |

---

## Overview

This document consolidates SDK operations and usability features into a unified technical design. The design addresses three core concerns:

1. **Action Endpoint Support** - Specialized API endpoints for relationship operations (tags, projects, dependencies, sections)
2. **Parent-Subtask Operations** - Hierarchical task management via `SET_PARENT` action
3. **SDK Usability** - Ergonomic API patterns including direct methods, name resolution, and auto-tracking
4. **Async Method Generator** - Code reduction through `@async_method` decorator

### Design Principles

- **Additive changes only** - Zero breaking changes to existing API
- **Async-first with sync wrappers** - Single implementation generates both variants
- **Leverage existing patterns** - SaveSession, ChangeTracker, error hierarchy
- **Type-safe throughout** - Full mypy compliance and IDE support

---

## Action Endpoint Support

Action endpoints handle relationship operations that cannot be performed via standard CRUD. These operations are not batch-eligible and execute after CRUD operations during SaveSession commit.

### Supported Action Types

```python
class ActionType(str, Enum):
    """Action operations requiring dedicated API endpoints."""

    # Tag operations
    ADD_TAG = "add_tag"              # POST /tasks/{gid}/addTag
    REMOVE_TAG = "remove_tag"        # POST /tasks/{gid}/removeTag

    # Project operations
    ADD_TO_PROJECT = "add_to_project"          # POST /tasks/{gid}/addProject
    REMOVE_FROM_PROJECT = "remove_from_project" # POST /tasks/{gid}/removeProject

    # Dependency operations
    ADD_DEPENDENCY = "add_dependency"      # POST /tasks/{gid}/addDependencies
    REMOVE_DEPENDENCY = "remove_dependency" # POST /tasks/{gid}/removeDependencies

    # Section operations
    MOVE_TO_SECTION = "move_to_section"    # POST /sections/{gid}/addTask

    # Parent operations
    SET_PARENT = "set_parent"              # POST /tasks/{gid}/setParent
```

### Action Operation Data Model

```python
@dataclass(frozen=True)
class ActionOperation:
    """A planned action requiring a dedicated API endpoint.

    Attributes:
        action_type: The type of action to perform
        target_entity: The primary entity (typically a task)
        related_entity_gid: GID of the related entity (tag, project, etc.)
        extra_params: Additional parameters (section, positioning)
    """
    action_type: ActionType
    target_entity: AsanaResource
    related_entity_gid: str | None
    extra_params: dict[str, Any] = field(default_factory=dict)
```

### SaveSession Action Methods

All action methods return `self` for fluent chaining and queue operations for commit-time execution.

```python
class SaveSession:
    """Extended with action endpoint methods."""

    def add_tag(self, task: Task | str, tag: Tag | str) -> SaveSession:
        """Add tag to task. Executes POST /tasks/{gid}/addTag on commit."""

    def remove_tag(self, task: Task | str, tag: Tag | str) -> SaveSession:
        """Remove tag from task."""

    def add_to_project(
        self,
        task: Task | str,
        project: Project | str,
        *,
        section: Section | str | None = None,
    ) -> SaveSession:
        """Add task to project, optionally in specific section."""

    def remove_from_project(
        self,
        task: Task | str,
        project: Project | str,
    ) -> SaveSession:
        """Remove task from project."""

    def add_dependency(
        self,
        task: Task | str,
        depends_on: Task | str,
    ) -> SaveSession:
        """Add dependency (task depends on another task)."""

    def remove_dependency(
        self,
        task: Task | str,
        depends_on: Task | str,
    ) -> SaveSession:
        """Remove dependency."""

    def move_to_section(
        self,
        task: Task | str,
        section: Section | str,
    ) -> SaveSession:
        """Move task to section. Uses POST /sections/{gid}/addTask."""
```

### Unsupported Operation Detection

Direct modifications to relationship fields are detected and rejected with actionable error messages.

```python
class UnsupportedOperationError(SaveOrchestrationError):
    """Raised when attempting unsupported direct modification.

    Attributes:
        field_name: The field that was modified directly
        suggested_methods: Correct session method names to use
    """

    FIELD_SUGGESTIONS: ClassVar[dict[str, tuple[str, ...]]] = {
        "tags": ("add_tag", "remove_tag"),
        "projects": ("add_to_project", "remove_from_project"),
        "memberships": ("add_to_project", "remove_from_project", "move_to_section"),
        "dependencies": ("add_dependency", "remove_dependency"),
    }
```

**Detection timing**: Validation occurs in SavePipeline before any API calls, ensuring fail-fast behavior for both `preview()` and `commit()`.

### Action Execution Flow

```
SaveSession.commit_async()
    |
    v
Phase 0: VALIDATE
    - Check for unsupported direct modifications
    - Raise UnsupportedOperationError if found
    |
    v
Phases 1-3: CRUD EXECUTION
    - Create/update/delete entities via BatchClient
    - Build GID map (temp_xxx -> real GID)
    |
    v
Phase 4: ACTION EXECUTION
    - Resolve temp GIDs using map from CRUD phase
    - Execute action operations sequentially
    - Each action = individual POST call
    |
    v
Phase 5: CONFIRM
    - Combine CRUD and action results
    - Return SaveResult
```

---

## Parent-Subtask Operations

Parent/subtask management extends the action system with a single `SET_PARENT` ActionType.

### SaveSession Methods

```python
def set_parent(
    self,
    task: AsanaResource,
    parent: AsanaResource | str | None,
    *,
    insert_before: AsanaResource | str | None = None,
    insert_after: AsanaResource | str | None = None,
) -> SaveSession:
    """Set or change the parent of a task.

    Use this to:
    - Convert task to subtask: set_parent(task, parent_task)
    - Promote subtask to top-level: set_parent(task, None)
    - Move subtask to different parent: set_parent(task, new_parent)
    - Position within siblings: set_parent(task, parent, insert_after=sibling)

    Args:
        task: The task to reparent
        parent: New parent task, or None to promote to top-level
        insert_before: Position before this sibling (mutually exclusive)
        insert_after: Position after this sibling (mutually exclusive)

    Raises:
        PositioningConflictError: If both insert_before and insert_after specified
    """

def reorder_subtask(
    self,
    task: AsanaResource,
    *,
    insert_before: AsanaResource | str | None = None,
    insert_after: AsanaResource | str | None = None,
) -> SaveSession:
    """Reorder a subtask within its current parent.

    Convenience method that calls set_parent() with the task's current parent.

    Raises:
        ValueError: If task has no parent (is not a subtask)
    """
```

### API Payload Generation

```python
case ActionType.SET_PARENT:
    parent_gid = self.extra_params.get("parent")  # None or GID string
    data: dict[str, Any] = {"parent": parent_gid}
    if "insert_before" in self.extra_params:
        data["insert_before"] = self.extra_params["insert_before"]
    if "insert_after" in self.extra_params:
        data["insert_after"] = self.extra_params["insert_after"]
    return (
        "POST",
        f"/tasks/{task_gid}/setParent",
        {"data": data},
    )
```

---

## SDK Usability Patterns

### Direct Methods (TasksClient)

Direct methods wrap SaveSession internally, returning updated Task objects for single-operation scenarios.

```python
class TasksClient:
    """Extended with convenience methods."""

    # Async versions
    async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
        """Add tag to task without explicit SaveSession."""
        async with SaveSession(self._client) as session:
            session.add_tag(task_gid, tag_gid)
            await session.commit_async()
        return await self.get_async(task_gid)

    async def remove_tag_async(self, task_gid: str, tag_gid: str) -> Task
    async def move_to_section_async(self, task_gid: str, section_gid: str, project_gid: str) -> Task
    async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task
    async def add_to_project_async(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
    async def remove_from_project_async(self, task_gid: str, project_gid: str) -> Task

    # Sync wrappers (generated via @sync_wrapper decorator)
    def add_tag(self, task_gid: str, tag_gid: str) -> Task
    def remove_tag(self, task_gid: str, tag_gid: str) -> Task
    def move_to_section(self, task_gid: str, section_gid: str, project_gid: str) -> Task
    def set_assignee(self, task_gid: str, assignee_gid: str) -> Task
    def add_to_project(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
    def remove_from_project(self, task_gid: str, project_gid: str) -> Task
```

### Name Resolution

The NameResolver class provides name-to-GID resolution with per-SaveSession caching.

```python
class NameResolver:
    """Resolve names to GIDs for tags, sections, projects, assignees.

    Features:
    - Polymorphic input: accepts both names and GIDs
    - Per-SaveSession caching (zero staleness within session)
    - Fuzzy matching suggestions on not-found errors
    """

    async def resolve_tag_async(self, name_or_gid: str, project_gid: str | None = None) -> str
    async def resolve_section_async(self, name_or_gid: str, project_gid: str) -> str
    async def resolve_project_async(self, name_or_gid: str, workspace_gid: str) -> str
    async def resolve_assignee_async(self, name_or_gid: str, workspace_gid: str) -> str

    @staticmethod
    def _looks_like_gid(value: str) -> bool:
        """Check if value looks like Asana GID (alphanumeric, 20+ chars)."""
        return len(value) >= 20 and value.replace("_", "").isalnum()
```

**Error handling**:

```python
class NameNotFoundError(AsanaError):
    """Raised when resource name cannot be resolved to GID.

    Attributes:
        name: The name that was searched for
        resource_type: Type of resource ("tag", "project", "user", "section")
        scope: Scope identifier (workspace or project GID)
        suggestions: Fuzzy match suggestions
    """
```

### Task Auto-Tracking

Tasks fetched from the API maintain a client reference enabling implicit SaveSession management.

```python
class Task(AsanaResource):
    """Extended with auto-tracking capabilities."""

    _client: Any = PrivateAttr(default=None)
    _custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)

    @property
    def custom_fields(self) -> CustomFieldAccessor:
        """Dictionary-style access to custom fields."""
        if self._custom_fields_accessor is None:
            self._custom_fields_accessor = CustomFieldAccessor(self.custom_fields)
        return self._custom_fields_accessor

    async def save_async(self) -> Task:
        """Save task changes using implicit SaveSession.

        Creates SaveSession automatically, tracks changes, commits.
        No-op if task is clean (no API call).
        """
        if self._client is None:
            raise ValueError("Task has no client reference")

        async with SaveSession(self._client) as session:
            session.track(self)
            result = await session.commit_async()
            if not result.success:
                raise result.failed[0].error
        return self

    async def refresh_async(self) -> Task:
        """Re-fetch task from API, discarding local changes."""
```

### CustomFieldAccessor Dict Syntax

```python
class CustomFieldAccessor:
    """Extended with dict-style access."""

    def __getitem__(self, name_or_gid: str) -> Any:
        """Get value: accessor["Priority"]"""
        result = self.get(name_or_gid, default=_MISSING)
        if result is _MISSING:
            raise KeyError(name_or_gid)
        return result

    def __setitem__(self, name_or_gid: str, value: Any) -> None:
        """Set value: accessor["Priority"] = "High" """
        self.set(name_or_gid, value)

    def __delitem__(self, name_or_gid: str) -> None:
        """Delete field: del accessor["Priority"]"""
        self.remove(name_or_gid)
```

### Client Constructor Enhancement

```python
class AsanaClient:
    """Enhanced constructor with workspace auto-detection."""

    def __init__(
        self,
        token: str,
        workspace_gid: str | None = None,
        batch_size: int = 10,
        max_concurrent: int = 15,
    ) -> None:
        """Initialize Asana client.

        Simplified single-argument pattern: AsanaClient(token)
        Auto-detects workspace if user has exactly one.

        Raises:
            ConfigurationError: If >1 workspace and no workspace_gid provided
            ConfigurationError: If 0 workspaces
        """
```

---

## Async Method Decorator

The `@async_method` decorator reduces code duplication by generating both async and sync variants from a single implementation.

### Decorator Design

```python
def async_method(fn: Callable[..., Coroutine[Any, Any, R]]) -> AsyncMethodPair[R]:
    """Decorator that creates async/sync method pair.

    Usage:
        @async_method
        async def get(self, section_gid: str, *, raw: bool = False) -> Section | dict:
            '''Get a section by GID.'''
            ...

    Generates:
        - get_async() - the async version
        - get() - the sync wrapper
    """
    return AsyncMethodPair(fn)


class AsyncMethodPair(Generic[R]):
    """Descriptor that exposes both async and sync variants."""

    def __set_name__(self, owner: type, name: str) -> None:
        """Inject both method variants into the class."""
        async_name = f"{name}_async"
        sync_name = name

        # Create sync wrapper with async context detection
        @wraps(self._async_impl)
        def sync_method(self_: Any, *args: Any, **kwargs: Any) -> R:
            try:
                asyncio.get_running_loop()
                raise SyncInAsyncContextError(
                    method_name=sync_name,
                    async_method_name=async_name,
                )
            except RuntimeError:
                pass
            return asyncio.run(self._async_impl(self_, *args, **kwargs))

        setattr(owner, async_name, self._async_impl)
        setattr(owner, sync_name, sync_method)
```

### Migration Pattern

**Before** (~18 lines for simple method):
```python
@error_handler
async def delete_async(self, section_gid: str) -> None:
    await self._http.delete(f"/sections/{section_gid}")

@sync_wrapper("delete_async")
async def _delete_sync(self, section_gid: str) -> None:
    await self.delete_async(section_gid)

def delete(self, section_gid: str) -> None:
    self._delete_sync(section_gid)
```

**After** (~6 lines):
```python
@async_method
@error_handler
async def delete(self, section_gid: str) -> None:
    '''Delete a section.'''
    await self._http.delete(f"/sections/{section_gid}")
```

**Code reduction**: ~65% per method.

### Overload Handling

For methods with `raw` parameter, explicit `@overload` declarations are still required for type safety:

```python
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@overload
def get(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@async_method
@error_handler
async def get(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    '''Get a section by GID.'''
    ...
```

This reduces from 6 overloads + 3 methods to 4 overloads + 1 method (~60% reduction).

---

## Testing Strategy

### Action Endpoint Tests

| Test Category | Coverage |
|---------------|----------|
| ActionType enum | All 8 values present and correct |
| ActionOperation | Dataclass creation, repr, equality |
| UnsupportedOperationError | Message formatting for all 4 fields |
| ActionExecutor | Correct endpoint paths for all actions |
| SavePipeline validation | Detection for each unsupported field |
| SavePipeline execution | GID resolution, error handling |
| SaveSession methods | Fluent chaining, entity/GID resolution |

### Parent-Subtask Tests

| Test | Description |
|------|-------------|
| `test_set_parent_action_type_exists` | SET_PARENT in ActionType enum |
| `test_to_api_call_set_parent_basic` | Generates correct POST /tasks/{gid}/setParent |
| `test_to_api_call_set_parent_with_positioning` | Includes insert_before/insert_after |
| `test_to_api_call_set_parent_promote` | parent: null when promoting |
| `test_set_parent_positioning_conflict` | Raises PositioningConflictError |
| `test_reorder_subtask_no_parent_error` | ValueError on top-level task |

### SDK Usability Tests

| Test File | Coverage |
|-----------|----------|
| `test_tasks_direct_methods.py` | All 12 direct methods (6 async + 6 sync) |
| `test_custom_field_dict_access.py` | Dict syntax, type preservation |
| `test_name_resolver.py` | Name resolution, caching, error messages |
| `test_task_save.py` | Auto-tracking, save/refresh cycle |
| `test_constructor.py` | Workspace auto-detection, backward compat |

### Async Method Decorator Tests

```python
class TestAsyncMethod:
    def test_creates_async_variant(self): ...
    def test_creates_sync_variant(self): ...
    def test_async_behavior_correct(self): ...
    def test_sync_behavior_correct(self): ...
    def test_sync_in_async_context_raises(self): ...
    def test_preserves_docstring(self): ...
    def test_preserves_signature(self): ...
    def test_works_with_error_handler(self): ...
```

### Backward Compatibility

All existing tests must pass unchanged:
- SaveSession tests
- Custom field tests
- TasksClient tests
- Exception hierarchy tests

---

## Cross-References

### Related TDDs

| TDD | Relationship |
|-----|--------------|
| [TDD-04: Batch Save Operations](TDD-04-batch-save-operations.md) | Foundation for action execution pipeline |
| [TDD-03: Resource Clients](TDD-03-resource-clients.md) | Direct methods extend TasksClient |
| [TDD-06: Custom Fields](TDD-06-custom-fields.md) | CustomFieldAccessor dict syntax |

### Related ADRs

| ADR | Decision |
|-----|----------|
| ADR-0025 | Async-first concurrency pattern |
| ADR-0039 | API design and surface control |
| ADR-0043 | SaveSession action operations (action type separation, validation timing) |

### Source Documents

This consolidated TDD synthesizes:
- **TDD-0011**: Action Endpoint Support for Save Orchestration
- **TDD-0013**: Parent & Subtask Operations
- **TDD-0015** (TDD-SDKUX): SDK Usability Overhaul
- **TDD-0025** (TDD-DESIGN-PATTERNS-D): Async/Sync Method Generator

### File Locations

| Component | Path |
|-----------|------|
| ActionType, ActionOperation | `src/autom8_asana/persistence/models.py` |
| UnsupportedOperationError | `src/autom8_asana/persistence/exceptions.py` |
| SaveSession extensions | `src/autom8_asana/persistence/session.py` |
| ActionExecutor | `src/autom8_asana/persistence/action_executor.py` |
| SavePipeline extensions | `src/autom8_asana/persistence/pipeline.py` |
| NameResolver | `src/autom8_asana/clients/name_resolver.py` |
| Task extensions | `src/autom8_asana/models/task.py` |
| CustomFieldAccessor extensions | `src/autom8_asana/models/custom_field_accessor.py` |
| async_method decorator | `src/autom8_asana/utils/async_method.py` |
