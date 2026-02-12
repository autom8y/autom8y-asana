# Resource Clients Reference

> Typed clients for Asana API resources

## Overview

Resource clients provide typed access to Asana API resources. All clients:
- Return Pydantic models by default (use `raw=True` for dicts)
- Support both async (`_async` suffix) and sync operations
- Include automatic cache integration where enabled
- Use `@async_method` decorator for dual async/sync method generation
- Provide `opt_fields` parameters to control API response fields

All resource clients are accessed via properties on `AsanaClient` and are lazy-initialized on first access.

## BaseClient

All resource clients inherit from `BaseClient`, which provides common functionality:
- HTTP client access
- Cache integration helpers (`_cache_get`, `_cache_set`)
- Config and provider management
- `opt_fields` parameter building

## TasksClient

Operations for Asana tasks.

### get()

```python
def get(
    self,
    task_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Task | dict[str, Any]

async def get_async(
    self,
    task_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Task | dict[str, Any]
```

Get a task by GID with cache support. Returns `Task` model by default, or dict if `raw=True`.

**Raises:** `ValidationError` if task_gid is invalid

### create()

```python
def create(
    self,
    *,
    name: str,
    workspace: str | None = None,
    projects: list[str] | None = None,
    parent: str | None = None,
    raw: bool = False,
    **kwargs: Any,
) -> Task | dict[str, Any]

async def create_async(...) -> Task | dict[str, Any]
```

Create a new task. Returns created `Task` model.

### update()

```python
def update(
    self,
    task_gid: str,
    *,
    raw: bool = False,
    **updates: Any,
) -> Task | dict[str, Any]

async def update_async(...) -> Task | dict[str, Any]
```

Update a task with specified fields.

### delete()

```python
def delete(self, task_gid: str) -> dict[str, Any]
async def delete_async(self, task_gid: str) -> dict[str, Any]
```

Delete a task by GID.

### list()

```python
def list(
    self,
    *,
    project: str | None = None,
    section: str | None = None,
    assignee: str | None = None,
    workspace: str | None = None,
    completed_since: str | None = None,
    modified_since: str | None = None,
    opt_fields: list[str] | None = None,
) -> PageIterator[Task]

async def list_async(...) -> PageIterator[Task]
```

List tasks with automatic pagination. Returns `PageIterator[Task]` for efficient iteration over large result sets.

### P1 Operations

Delegated to `TaskOperations` helper (accessed via `tasks.operations`):

```python
# Tag operations
async def add_tag_async(task_gid: str, tag_gid: str) -> dict[str, Any]
async def remove_tag_async(task_gid: str, tag_gid: str) -> dict[str, Any]

# Section operations
async def move_to_section_async(task_gid: str, section_gid: str) -> dict[str, Any]

# Assignee operations
async def set_assignee_async(task_gid: str, assignee_gid: str | None) -> dict[str, Any]

# Project operations
async def add_to_project_async(task_gid: str, project_gid: str) -> dict[str, Any]
async def remove_from_project_async(task_gid: str, project_gid: str) -> dict[str, Any]
```

## ProjectsClient

Operations for Asana projects.

### get()

```python
def get(
    self,
    project_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Project | dict[str, Any]

async def get_async(...) -> Project | dict[str, Any]
```

Get a project by GID with cache support (15-minute TTL).

**Raises:** `GidValidationError` if project_gid is invalid

### create()

```python
def create(
    self,
    *,
    name: str,
    workspace: str,
    team: str | None = None,
    public: bool | None = None,
    color: str | None = None,
    default_view: str | None = None,
    raw: bool = False,
    **kwargs: Any,
) -> Project | dict[str, Any]

async def create_async(...) -> Project | dict[str, Any]
```

Create a new project.

### update()

```python
def update(
    self,
    project_gid: str,
    *,
    raw: bool = False,
    **updates: Any,
) -> Project | dict[str, Any]

async def update_async(...) -> Project | dict[str, Any]
```

Update a project.

### delete()

```python
def delete(self, project_gid: str) -> dict[str, Any]
async def delete_async(self, project_gid: str) -> dict[str, Any]
```

Delete a project.

### list_sections()

```python
def list_sections(
    self,
    project_gid: str,
    *,
    opt_fields: list[str] | None = None,
) -> PageIterator[Section]

async def list_sections_async(...) -> PageIterator[Section]
```

List sections within a project.

## SectionsClient

Operations for Asana sections (columns in board view).

### get()

```python
def get(
    self,
    section_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Section | dict[str, Any]

async def get_async(...) -> Section | dict[str, Any]
```

Get a section by GID.

### create()

```python
def create(
    self,
    *,
    project: str,
    name: str,
    raw: bool = False,
    **kwargs: Any,
) -> Section | dict[str, Any]

async def create_async(...) -> Section | dict[str, Any]
```

Create a new section in a project.

### update()

```python
def update(
    self,
    section_gid: str,
    *,
    raw: bool = False,
    **updates: Any,
) -> Section | dict[str, Any]

async def update_async(...) -> Section | dict[str, Any]
```

Update a section.

### delete()

```python
def delete(self, section_gid: str) -> dict[str, Any]
async def delete_async(self, section_gid: str) -> dict[str, Any]
```

Delete a section.

## CustomFieldsClient

Operations for custom fields.

### get()

```python
def get(
    self,
    custom_field_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> CustomField | dict[str, Any]

async def get_async(...) -> CustomField | dict[str, Any]
```

Get a custom field by GID.

### create()

```python
def create(
    self,
    *,
    workspace: str,
    name: str,
    resource_subtype: str,
    raw: bool = False,
    **kwargs: Any,
) -> CustomField | dict[str, Any]

async def create_async(...) -> CustomField | dict[str, Any]
```

Create a new custom field. `resource_subtype` must be one of: text, number, enum, multi_enum, date, people.

## UsersClient

Operations for users.

### get()

```python
def get(
    self,
    user_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> User | dict[str, Any]

async def get_async(...) -> User | dict[str, Any]
```

Get a user by GID.

### list()

```python
def list(
    self,
    *,
    workspace: str | None = None,
    team: str | None = None,
    opt_fields: list[str] | None = None,
) -> PageIterator[User]

async def list_async(...) -> PageIterator[User]
```

List users in a workspace or team.

## WorkspacesClient

Operations for workspaces.

### get()

```python
def get(
    self,
    workspace_gid: str,
    *,
    raw: bool = False,
    opt_fields: list[str] | None = None,
) -> Workspace | dict[str, Any]

async def get_async(...) -> Workspace | dict[str, Any]
```

Get a workspace by GID.

### list()

```python
def list(
    self,
    *,
    opt_fields: list[str] | None = None,
) -> PageIterator[Workspace]

async def list_async(...) -> PageIterator[Workspace]
```

List all workspaces the authenticated user has access to.

## BatchClient

Bulk operations via Asana's batch API.

### execute()

```python
def execute(
    self,
    requests: list[BatchRequest],
) -> list[BatchResult]

async def execute_async(
    self,
    requests: list[BatchRequest],
) -> list[BatchResult]
```

Execute multiple requests in batches. Automatically chunks into groups of 10 (Asana's limit) and handles partial failures.

### create_tasks()

```python
def create_tasks(
    self,
    task_data_list: list[dict[str, Any]],
) -> list[BatchResult]

async def create_tasks_async(
    self,
    task_data_list: list[dict[str, Any]],
) -> list[BatchResult]
```

Convenience method for creating multiple tasks in batches.

## SearchService

Field-based GID lookup from cached Polars DataFrames.

### find()

```python
def find(
    self,
    target_field: str,
    filters: dict[str, Any],
) -> SearchResult

async def find_async(
    self,
    target_field: str,
    filters: dict[str, Any],
) -> SearchResult
```

Find GIDs by matching custom field values in cached project DataFrames.

**Parameters:**
- **target_field**: Field name containing GIDs to return (e.g., "project_gid")
- **filters**: Dict of field_name -> value pairs to match

**Returns:** `SearchResult` with hits (matching rows)

## Examples

### TasksClient

```python
# Get task
task = await client.tasks.get_async("task_gid")

# Create task
task = await client.tasks.create_async(
    name="New Task",
    projects=["project_gid"],
)

# List tasks in project
async for task in client.tasks.list_async(project="project_gid"):
    print(task.name)

# P1 operations
await client.tasks.operations.add_tag_async("task_gid", "tag_gid")
await client.tasks.operations.move_to_section_async("task_gid", "section_gid")
```

### ProjectsClient

```python
# Get project
project = await client.projects.get_async("project_gid")

# Create project
project = await client.projects.create_async(
    name="New Project",
    workspace="workspace_gid",
    team="team_gid",
)

# List sections
async for section in client.projects.list_sections_async("project_gid"):
    print(section.name)
```

### BatchClient

```python
from autom8_asana.batch import BatchRequest

requests = [
    BatchRequest("/tasks", "POST", data={"name": "Task 1", "projects": ["123"]}),
    BatchRequest("/tasks", "POST", data={"name": "Task 2", "projects": ["123"]}),
]
results = await client.batch.execute_async(requests)

# Or use convenience method
results = await client.batch.create_tasks_async([
    {"name": "Task 1", "projects": ["123"]},
    {"name": "Task 2", "projects": ["123"]},
])
```

### SearchService

```python
# Find project GID by custom field values
result = await client.search.find_async(
    "project_gid",
    {"Office Phone": "555-1234", "Vertical": "Medical"}
)
for hit in result.hits:
    print(hit.gid)
```
