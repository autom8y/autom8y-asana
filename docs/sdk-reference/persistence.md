# SaveSession and Persistence Reference

> Unit of Work pattern for batched Asana operations

## Overview

`SaveSession` provides a Django-ORM-style deferred save pattern where multiple model changes are collected and executed in optimized batches. It implements the Unit of Work pattern with automatic dependency ordering, partial failure handling, and event hooks.

Key features:
- Explicit entity registration via `track()`
- Snapshot-based dirty detection
- Dependency graph construction for parent-child relationships
- Automatic placeholder GID resolution for new entities
- Partial failure handling with commit-and-report semantics
- Event hooks for pre-save, post-save, and error handling
- Thread-safe operations with reentrant locking

## SaveSession

Main entry point for batched operations.

### Constructor

```python
def __init__(
    self,
    client: AsanaClient,
    batch_size: int = 10,
    max_concurrent: int = 15,
    auto_heal: bool = False,
    automation_enabled: bool | None = None,
    auto_create_holders: bool = True,
) -> None
```

**Parameters:**
- **client**: AsanaClient instance for API calls
- **batch_size**: Maximum operations per batch (default: 10, Asana limit)
- **max_concurrent**: Maximum concurrent batch requests (default: 15)
- **auto_heal**: If True, entities detected via fallback tiers will be added to their expected project during commit (default: False)
- **automation_enabled**: Override for automation execution. If None, uses `client._config.automation.enabled`
- **auto_create_holders**: If True (default), automatically create missing holder subtasks during commit. If False, ENSURE_HOLDERS phase is skipped.

### Context Manager Support

SaveSession supports both async and sync context managers.

```python
async def __aenter__(self) -> SaveSession
async def __aexit__(self, ...) -> None

def __enter__(self) -> SaveSession
def __exit__(self, ...) -> None
```

Note: Context manager exit closes the session. Uncommitted changes are discarded.

### Properties

#### state

```python
@property
def state(self) -> str
```

Current session state: `OPEN`, `COMMITTED`, or `CLOSED`.

#### pending_actions

```python
@property
def pending_actions(self) -> list[ActionOperation]
```

Copy of pending action operations for inspection.

#### healing_queue

```python
@property
def healing_queue(self) -> list[tuple[AsanaResource, str]]
```

Copy of the healing queue for inspection. Returns list of (entity, expected_project_gid) tuples.

#### auto_heal

```python
@property
def auto_heal(self) -> bool
```

Whether auto-healing is enabled for this session.

#### automation_enabled

```python
@property
def automation_enabled(self) -> bool
```

Whether automation is enabled for this session.

#### auto_create_holders

```python
@property
def auto_create_holders(self) -> bool
```

Whether holder auto-creation is enabled for this session.

#### name_resolver

```python
@property
def name_resolver(self) -> NameResolver
```

Get name resolver for this session (cached per-session).

### Core Methods

#### track()

```python
def track(
    self,
    entity: T,
    *,
    prefetch_holders: bool = False,
    recursive: bool = False,
    heal: bool | None = None,
) -> T
```

Register entity for change tracking. Captures snapshot of current state.

**Parameters:**
- **entity**: Entity to track
- **prefetch_holders**: For BusinessEntity types, prefetch holder properties during tracking
- **recursive**: Recursively track child entities in hierarchy
- **heal**: Override auto_heal setting for this entity. If None, uses session's auto_heal.

**Returns:** The tracked entity (same instance, or existing if GID already tracked)

**Raises:** `SessionClosedError` if session is closed

New entities (with gid starting with "temp_" or without gid) will be created via POST. Existing entities will be updated via PUT if they have changes.

#### commit_async()

```python
async def commit_async(self) -> SaveResult
```

Execute all pending operations asynchronously. Returns `SaveResult` with succeeded/failed lists.

Commit phases:
1. Validate all tracked entities
2. Build dependency graph
3. Execute CRUD operations in batches (topological order)
4. Execute action operations (tags, projects, sections)
5. Execute cascade operations (field propagation)
6. Execute healing operations (if auto_heal enabled)
7. Execute automation rules (if automation_enabled)
8. Invalidate cache entries

**Returns:** `SaveResult` with lists of succeeded/failed entities and operation results

**Raises:** `SessionClosedError` if session is closed

#### commit()

```python
def commit(self) -> SaveResult
```

Synchronous wrapper for `commit_async()`.

**Raises:** `SyncInAsyncContextError` if called from async context

#### preview()

```python
def preview(self) -> list[PlannedOperation]
```

Dry-run inspection of pending operations without executing them.

**Returns:** List of `PlannedOperation` objects showing what would be executed

#### mark_deleted()

```python
def mark_deleted(self, entity: AsanaResource) -> None
```

Mark entity for deletion. Will be deleted via DELETE at commit time.

**Raises:** `SessionClosedError` if session is closed

### Action Methods

SaveSession provides deferred action methods for operations that don't fit the standard CRUD pattern. All action methods return the session for chaining.

#### Tag Operations

```python
def add_tag(
    self,
    task: AsanaResource,
    tag: NameGid | str,
) -> SaveSession

def remove_tag(
    self,
    task: AsanaResource,
    tag: NameGid | str,
) -> SaveSession
```

Add or remove a tag from a task. Executed at commit time after CRUD operations.

#### Project Operations

```python
def add_to_project(
    self,
    task: AsanaResource,
    project: NameGid | str,
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession

def remove_from_project(
    self,
    task: AsanaResource,
    project: NameGid | str,
) -> SaveSession
```

Add or remove a task from a project. `add_to_project` supports positioning with `insert_before`/`insert_after`.

**Raises:** `PositioningConflictError` if both insert_before and insert_after are provided

#### Section Operations

```python
def move_to_section(
    self,
    task: AsanaResource,
    section: NameGid | str,
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession
```

Move task to a section. Supports positioning with `insert_before`/`insert_after`.

**Raises:** `PositioningConflictError` if both insert_before and insert_after are provided

#### Dependency Operations

```python
def add_dependency(
    self,
    task: AsanaResource,
    dependency: NameGid | str,
) -> SaveSession

def remove_dependency(
    self,
    task: AsanaResource,
    dependency: NameGid | str,
) -> SaveSession

def add_dependent(
    self,
    task: AsanaResource,
    dependent: NameGid | str,
) -> SaveSession

def remove_dependent(
    self,
    task: AsanaResource,
    dependent: NameGid | str,
) -> SaveSession
```

Manage task dependencies. Dependencies are tasks that must be completed before this task. Dependents are tasks that depend on this task.

#### Follower Operations

```python
def add_follower(
    self,
    task: AsanaResource,
    follower: NameGid | str,
) -> SaveSession

def remove_follower(
    self,
    task: AsanaResource,
    follower: NameGid | str,
) -> SaveSession
```

Add or remove followers from a task.

#### Subtask Operations

```python
def set_parent(
    self,
    task: AsanaResource,
    parent: NameGid | str | None,
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession
```

Set or clear parent task. Supports positioning with `insert_before`/`insert_after`.

**Raises:** `PositioningConflictError` if both insert_before and insert_after are provided

#### Like Operations

```python
def add_like(
    self,
    task: AsanaResource,
) -> SaveSession

def remove_like(
    self,
    task: AsanaResource,
) -> SaveSession
```

Add or remove a like from a task (as the authenticated user).

### Event Hooks

SaveSession supports event hooks for custom logic during the save lifecycle.

```python
def on_pre_save(
    self,
    handler: Callable[[AsanaResource, OperationType], None],
) -> None

def on_post_save(
    self,
    handler: Callable[[AsanaResource, OperationType, dict[str, Any]], Coroutine[Any, Any, None]],
) -> None

def on_error(
    self,
    handler: Callable[[SaveError], Coroutine[Any, Any, None]],
) -> None
```

Register callbacks for:
- **pre_save**: Before entity is saved (validation)
- **post_save**: After entity is saved successfully (notifications)
- **error**: When entity save fails (logging)

Handlers can be registered via decorator syntax:

```python
@session.on_pre_save
def validate(entity, op):
    if op == OperationType.CREATE and not entity.name:
        raise ValueError("Task must have a name")
```

## Data Models

### EntityState

Enum for entity lifecycle state.

```python
class EntityState(Enum):
    NEW = "new"           # No GID or temp GID, will be created via POST
    CLEAN = "clean"       # Unmodified since last save/track
    MODIFIED = "modified" # Has pending changes
    DELETED = "deleted"   # Marked for deletion
```

### OperationType

Enum for operation types.

```python
class OperationType(Enum):
    CREATE = "create"  # POST request
    UPDATE = "update"  # PUT request
    DELETE = "delete"  # DELETE request
```

### ActionType

Enum for action operation types.

```python
class ActionType(Enum):
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    MOVE_TO_SECTION = "move_to_section"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    ADD_DEPENDENT = "add_dependent"
    REMOVE_DEPENDENT = "remove_dependent"
    ADD_FOLLOWER = "add_follower"
    REMOVE_FOLLOWER = "remove_follower"
    SET_PARENT = "set_parent"
    ADD_LIKE = "add_like"
    REMOVE_LIKE = "remove_like"
```

### PlannedOperation

Result from preview() showing a planned operation.

```python
@dataclass(frozen=True)
class PlannedOperation:
    entity: AsanaResource          # Entity to operate on
    operation: OperationType        # CREATE, UPDATE, or DELETE
    payload: dict[str, Any]         # Data payload for request
    dependency_level: int           # Level in dependency graph (0 = no deps)
```

### SaveError

Error information for a failed operation.

```python
@dataclass
class SaveError:
    entity: AsanaResource           # Entity that failed
    operation: OperationType        # Operation that was attempted
    error: Exception                # Exception that occurred
    payload: dict[str, Any]         # Payload that was sent

    @property
    def is_retryable(self) -> bool  # Classification for retry logic
```

### SaveResult

Result of a commit operation.

```python
@dataclass
class SaveResult:
    succeeded: list[AsanaResource]      # Entities saved successfully (CRUD)
    failed: list[SaveError]              # Failed CRUD operations
    action_results: list[ActionResult]   # Action operation results
    cascade_results: list[CascadeResult] # Cascade operation results
    healing_report: HealingReport | None # Self-healing report (if auto_heal=True)
    automation_results: list[AutomationResult] # Automation results (if enabled)

    @property
    def success(self) -> bool            # True if no failures
    @property
    def total_operations(self) -> int    # Total CRUD operations attempted
```

### ActionOperation

Pending action operation.

```python
@dataclass
class ActionOperation:
    entity: AsanaResource       # Entity to operate on
    action_type: ActionType     # Type of action
    target: NameGid | str | None # Target resource (e.g., tag GID)
    params: dict[str, Any]      # Additional parameters (e.g., insert_before)
```

### ActionResult

Result of an action operation.

```python
@dataclass
class ActionResult:
    operation: ActionOperation  # The operation that was executed
    success: bool               # Whether it succeeded
    error: Exception | None     # Exception if failed
    response: dict[str, Any] | None # API response if succeeded
```

## Exceptions

### SessionClosedError

```python
class SessionClosedError(Exception)
```

Raised when attempting operations on a closed session.

### PositioningConflictError

```python
class PositioningConflictError(Exception)
```

Raised when both `insert_before` and `insert_after` are provided to a positioning operation.

## Examples

### Basic Usage

```python
async with client.save_session() as session:
    # Track existing entity
    session.track(task)
    task.name = "Updated Name"

    # Track new entity (with temp GID)
    new_task = Task(gid="temp_1", name="New Task")
    session.track(new_task)

    # Commit all changes
    result = await session.commit_async()

    if result.success:
        print("All saved!")
    else:
        print(f"Partial: {len(result.failed)} failed")
```

### Sync Usage

```python
with client.save_session() as session:
    session.track(task)
    task.name = "Updated"
    result = session.commit()
```

### Action Operations

```python
async with client.save_session() as session:
    session.track(task)

    # Queue action operations
    session.add_tag(task, "urgent_tag_gid")
    session.move_to_section(task, "in_progress_section_gid")
    session.add_follower(task, "user_gid")

    # Execute all at commit
    result = await session.commit_async()
```

### Positioning

```python
async with client.save_session() as session:
    session.add_to_project(
        task,
        "project_gid",
        insert_after="reference_task_gid"
    )
    await session.commit_async()
```

### Event Hooks

```python
async with client.save_session() as session:
    @session.on_pre_save
    def validate(entity, op):
        if op == OperationType.CREATE and not entity.name:
            raise ValueError("Task must have a name")

    @session.on_post_save
    async def notify(entity, op, data):
        await send_notification(entity.gid)

    @session.on_error
    async def log_error(error):
        logger.error(f"Save failed: {error.entity.gid}")

    session.track(task)
    await session.commit_async()
```

### Preview

```python
async with client.save_session() as session:
    session.track(task)
    task.name = "Updated"

    # Preview without executing
    operations = session.preview()
    for op in operations:
        print(f"{op.operation.value}: {op.entity.gid} at level {op.dependency_level}")

    # Execute
    result = await session.commit_async()
```

### Recursive Tracking

```python
async with client.save_session() as session:
    # Track business and all children recursively
    session.track(business, recursive=True)

    # Modify hierarchy
    business.units[0].name = "Updated Unit"
    business.units[0].offers[0].name = "Updated Offer"

    # Commit all changes
    result = await session.commit_async()
```

### Error Handling

```python
async with client.save_session() as session:
    session.track(task1)
    session.track(task2)
    session.track(task3)

    result = await session.commit_async()

    # Check results
    print(f"Succeeded: {len(result.succeeded)}")
    print(f"Failed: {len(result.failed)}")

    # Handle failures
    for error in result.failed:
        print(f"Failed to save {error.entity.gid}: {error.error}")
        if error.is_retryable:
            print("  (retryable)")
```

### Chaining Actions

```python
async with client.save_session() as session:
    (session.track(task)
           .add_tag(task, "urgent")
           .add_follower(task, "user_gid")
           .move_to_section(task, "in_progress"))

    await session.commit_async()
```

### Business Entity Tracking

```python
async with client.save_session() as session:
    # Prefetch holders during tracking
    session.track(business, prefetch_holders=True)

    # Holders are now loaded
    for unit in business.units:
        unit.mrr = 5000.0

    result = await session.commit_async()
```
