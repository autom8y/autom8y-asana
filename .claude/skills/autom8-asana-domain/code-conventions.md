# SDK Code Conventions

> Python patterns and conventions specific to autom8_asana

---

## Async-First Pattern

All primary interfaces are async. Sync wrappers are provided via decorator.

### Async Method (Primary)

```python
async def commit_async(self) -> SaveResult:
    """Execute all pending operations asynchronously.

    Returns:
        SaveResult with success status and details.
    """
    # Implementation
    ...
```

### Sync Wrapper (Secondary)

```python
from autom8_asana.transport.sync import sync_wrapper

def commit(self) -> SaveResult:
    """Sync wrapper for commit_async()."""
    return sync_wrapper(self.commit_async)()
```

**Convention**:
- Async methods end with `_async` suffix
- Sync wrappers have the same name without suffix
- Document async method fully; sync wrapper just references it

---

## Pydantic v2 Models

All Asana resources use Pydantic v2 models.

### Base Model Pattern

```python
from pydantic import BaseModel, Field, ConfigDict

class AsanaResource(BaseModel):
    """Base class for all Asana resource models."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",  # Ignore unknown fields from API
    )

    gid: str = Field(..., description="Asana global ID")
    resource_type: str | None = Field(None, description="Resource type name")
```

### Resource Model Pattern

```python
class Task(AsanaResource):
    """Asana task resource."""

    name: str = Field(..., description="Task name")
    completed: bool = Field(False, description="Completion status")
    due_on: date | None = Field(None, description="Due date (no time)")
    due_at: datetime | None = Field(None, description="Due datetime")
    assignee: NameGid | None = Field(None, description="Assigned user")
    projects: list[NameGid] = Field(default_factory=list)
    custom_fields: list[CustomFieldValue] = Field(default_factory=list)
```

### Serialization

```python
# To dict (for API requests)
task.model_dump(exclude_none=True, by_alias=True)

# From API response
Task.model_validate(response_data)
```

---

## Protocol-Based Interfaces

SDK defines protocols; consumers implement.

### Defining a Protocol

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class CacheProtocol(Protocol):
    """Protocol for cache backends."""

    async def get(self, key: str) -> bytes | None:
        """Get value by key."""
        ...

    async def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
        """Set value with optional TTL."""
        ...

    async def delete(self, key: str) -> None:
        """Delete key."""
        ...
```

### Using Protocols in Type Hints

```python
class AsanaClient:
    def __init__(
        self,
        auth: AuthProtocol,
        cache: CacheProtocol | None = None,
    ):
        self._auth = auth
        self._cache = cache or InMemoryCache()
```

---

## Error Handling

### SDK Exception Hierarchy

```python
class AsanaSDKError(Exception):
    """Base exception for all SDK errors."""

class AsanaAPIError(AsanaSDKError):
    """Error from Asana API response."""
    def __init__(self, status_code: int, message: str, errors: list[dict] | None = None):
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(message)

class RateLimitError(AsanaAPIError):
    """Rate limit exceeded (429)."""
    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(429, "Rate limit exceeded")

class SessionClosedError(AsanaSDKError):
    """Operation attempted on closed SaveSession."""
```

### Handling Errors

```python
try:
    result = await session.commit_async()
except RateLimitError as e:
    await asyncio.sleep(e.retry_after or 60)
    # Retry...
except AsanaAPIError as e:
    logger.error(f"API error {e.status_code}: {e.errors}")
    raise
```

---

## SaveSession Usage Patterns

### Basic Usage

```python
async with SaveSession(client) as session:
    # Track existing entity
    session.track(task)
    task.name = "Updated Name"

    # Track new entity
    new_task = Task(gid="temp_1", name="New Task", project=project_gid)
    session.track(new_task)

    # Commit all changes
    result = await session.commit_async()
```

### Action Operations

```python
async with SaveSession(client) as session:
    # Tag operations
    session.add_tag(task_gid, tag_gid)
    session.remove_tag(task_gid, other_tag_gid)

    # Project operations
    session.add_to_project(task_gid, project_gid, section_gid=section_gid)
    session.remove_from_project(task_gid, old_project_gid)

    # Section operations (within same project)
    session.move_to_section(task_gid, new_section_gid)

    # Dependencies
    session.add_dependency(task_gid, blocking_task_gid)

    result = await session.commit_async()
```

### Preview Before Commit

```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Changed"

    # See what will happen
    operations = session.preview()
    for op in operations:
        print(f"{op.operation}: {op.entity.gid} at level {op.dependency_level}")

    # Commit if looks good
    if user_confirms():
        await session.commit_async()
```

---

## Resource Client Pattern

All resource clients follow consistent patterns:

```python
class TasksClient:
    """Client for Asana Tasks API."""

    async def list(
        self,
        project: str | None = None,
        assignee: str | None = None,
        opt_fields: list[str] | None = None,
    ) -> AsyncIterator[Task]:
        """List tasks with optional filters."""
        ...

    async def get(
        self,
        task_gid: str,
        opt_fields: list[str] | None = None,
    ) -> Task:
        """Get single task by GID."""
        ...

    async def create(
        self,
        data: dict[str, Any],
        opt_fields: list[str] | None = None,
    ) -> Task:
        """Create new task."""
        ...

    async def update(
        self,
        task_gid: str,
        data: dict[str, Any],
        opt_fields: list[str] | None = None,
    ) -> Task:
        """Update existing task."""
        ...

    async def delete(self, task_gid: str) -> None:
        """Delete task."""
        ...
```

---

## Testing Patterns

### Async Test Functions

```python
import pytest

@pytest.mark.asyncio
async def test_save_session_commit():
    client = create_mock_client()
    async with SaveSession(client) as session:
        task = Task(gid="temp_1", name="Test")
        session.track(task)
        result = await session.commit_async()
        assert result.success
```

### Mocking HTTP with respx

```python
import respx

@pytest.mark.asyncio
@respx.mock
async def test_api_call():
    respx.get("https://app.asana.com/api/1.0/tasks/123").respond(
        json={"data": {"gid": "123", "name": "Test Task"}}
    )

    task = await client.tasks.get("123")
    assert task.name == "Test Task"
```

---

## Import Organization

```python
# Standard library
from __future__ import annotations
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass

# Third-party
import httpx
from pydantic import BaseModel, Field

# SDK (absolute imports)
from autom8_asana.models.task import Task
from autom8_asana.persistence.session import SaveSession

# TYPE_CHECKING imports (avoid circular deps)
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
```
