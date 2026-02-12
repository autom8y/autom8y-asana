# Data Models Reference

> Pydantic models for Asana API resources

## Overview

All Asana resource models:
- Use Pydantic v2 with `extra="ignore"` for forward compatibility
- Use `NameGid` for typed resource references
- Support both dict and model serialization
- Include optional fields (most fields are `None` by default)
- Preserve unknown fields from API responses (silently ignored)

Models inherit from `AsanaResource`, which provides common functionality including GID-based equality and hashing.

## AsanaResource

Base class for all Asana resource models.

```python
class AsanaResource(BaseModel):
    gid: str | None = None
    resource_type: str | None = None
    name: str | None = None
```

Provides:
- `model_validate()` - Parse dict to model
- `model_dump()` - Serialize to dict
- Equality and hashing based on GID
- Unknown field tolerance

## NameGid

Typed resource reference with GID and name.

```python
class NameGid(BaseModel):
    gid: str
    name: str | None = None
    resource_type: str | None = None
```

Used for references to other resources (assignee, projects, parent, etc.) instead of plain dicts.

## Task

Asana Task resource model.

### Key Fields

```python
class Task(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "task"
    resource_subtype: str | None  # default_task, milestone, section, approval

    # Content
    notes: str | None
    html_notes: str | None

    # Status
    completed: bool | None
    completed_at: str | None  # ISO 8601
    completed_by: NameGid | None

    # Dates
    due_on: str | None  # YYYY-MM-DD
    due_at: str | None  # ISO 8601
    start_on: str | None  # YYYY-MM-DD
    start_at: str | None  # ISO 8601

    # Relationships (typed with NameGid)
    assignee: NameGid | None
    assignee_section: NameGid | None
    assignee_status: str | None  # inbox, today, upcoming, later
    projects: list[NameGid] | None
    parent: NameGid | None
    workspace: NameGid | None
    followers: list[NameGid] | None
    tags: list[NameGid] | None

    # Custom fields
    custom_fields: list[dict[str, Any]] | None

    # Hierarchy
    num_subtasks: int | None
    memberships: list[dict[str, Any]] | None

    # Metadata
    created_at: str | None  # ISO 8601
    modified_at: str | None  # ISO 8601
    created_by: NameGid | None

    # Permalink
    permalink_url: str | None

    # Approval
    approval_status: str | None  # pending, approved, rejected, changes_requested

    # External data
    external: dict[str, Any] | None

    # Time tracking
    actual_time_minutes: float | None
```

### Custom Field Accessor

```python
@property
def cf(self) -> CustomFieldAccessor
```

Access custom fields by name instead of GID.

```python
task.cf["Status"] = "In Progress"
value = task.cf.get("Priority", default="Medium")
```

### Snapshot Detection

Task captures a snapshot of `custom_fields` at initialization to detect direct modifications. Use `_has_direct_custom_field_changes()` to check if custom_fields was modified directly (not via accessor).

## Project

Asana Project resource model.

### Key Fields

```python
class Project(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "project"

    # Content
    notes: str | None
    html_notes: str | None

    # Status
    archived: bool | None
    public: bool | None
    completed: bool | None
    completed_at: str | None
    completed_by: NameGid | None
    color: str | None  # dark-pink, dark-green, etc.

    # Dates
    created_at: str | None  # ISO 8601
    modified_at: str | None  # ISO 8601
    due_on: str | None  # YYYY-MM-DD
    due_at: str | None  # ISO 8601
    start_on: str | None  # YYYY-MM-DD

    # Relationships (typed with NameGid)
    owner: NameGid | None
    team: NameGid | None
    workspace: NameGid | None
    current_status: NameGid | None
    current_status_update: NameGid | None
    members: list[NameGid] | None
    followers: list[NameGid] | None
    created_from_template: NameGid | None

    # Custom fields
    custom_fields: list[dict[str, Any]] | None
    custom_field_settings: list[dict[str, Any]] | None

    # Project properties
    default_view: str | None  # list, board, calendar, timeline
    default_access_level: str | None  # admin, editor, commenter, viewer
    minimum_access_level_for_customization: str | None
    minimum_access_level_for_sharing: str | None
    is_template: bool | None

    # Metadata
    icon: str | None
    permalink_url: str | None
```

## Section

Asana Section resource model (columns in board view).

### Key Fields

```python
class Section(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "section"

    # Relationships
    project: NameGid | None

    # Metadata
    created_at: str | None  # ISO 8601
```

## User

Asana User resource model.

### Key Fields

```python
class User(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "user"

    # Profile
    email: str | None
    photo: dict[str, Any] | None  # Photo URLs in various sizes

    # Relationships
    workspaces: list[NameGid] | None
```

## CustomField

Asana CustomField resource model.

### Key Fields

```python
class CustomField(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "custom_field"
    resource_subtype: str | None  # text, number, enum, multi_enum, date, people

    # Type-specific properties
    type: str | None  # Deprecated, use resource_subtype
    enum_options: list[dict[str, Any]] | None
    enum_value: dict[str, Any] | None
    multi_enum_values: list[dict[str, Any]] | None
    number_value: float | None
    text_value: str | None
    date_value: dict[str, Any] | None
    people_value: list[NameGid] | None

    # Display properties
    description: str | None
    precision: int | None  # For number fields
    format: str | None  # For number/date fields
    currency_code: str | None  # For number fields
    is_global_to_workspace: bool | None
    has_notifications_enabled: bool | None

    # Metadata
    created_by: NameGid | None
```

## Workspace

Asana Workspace resource model.

### Key Fields

```python
class Workspace(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "workspace"

    # Properties
    is_organization: bool | None
    email_domains: list[str] | None
```

## Team

Asana Team resource model.

### Key Fields

```python
class Team(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "team"

    # Relationships
    organization: NameGid | None

    # Properties
    description: str | None
    html_description: str | None
    permalink_url: str | None
```

## Tag

Asana Tag resource model.

### Key Fields

```python
class Tag(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "tag"

    # Relationships
    workspace: NameGid | None

    # Properties
    color: str | None
    notes: str | None
    permalink_url: str | None

    # Metadata
    created_at: str | None
    followers: list[NameGid] | None
```

## Attachment

Asana Attachment resource model.

### Key Fields

```python
class Attachment(AsanaResource):
    # Identification
    gid: str | None
    name: str | None
    resource_type: str | None = "attachment"
    resource_subtype: str | None  # asana, dropbox, gdrive, onedrive, box, vimeo, external

    # Relationships
    parent: NameGid | None

    # File properties
    download_url: str | None
    permanent_url: str | None
    view_url: str | None
    host: str | None  # asana, dropbox, gdrive, etc.
    size: int | None  # Bytes

    # Metadata
    created_at: str | None
```

## Story

Asana Story resource model (comments and system events).

### Key Fields

```python
class Story(AsanaResource):
    # Identification
    gid: str | None
    resource_type: str | None = "story"
    resource_subtype: str | None  # comment_added, comment_removed, etc.

    # Content
    text: str | None
    html_text: str | None

    # Relationships
    created_by: NameGid | None
    target: NameGid | None  # Task or other resource

    # Properties
    type: str | None  # comment, system
    is_pinned: bool | None
    is_edited: bool | None

    # Metadata
    created_at: str | None
    num_likes: int | None
    liked: bool | None
```

## PageIterator

Generic iterator for paginated API responses.

```python
class PageIterator[T]:
    async def __aiter__(self) -> AsyncIterator[T]
    def __iter__(self) -> Iterator[T]
```

Supports both async and sync iteration:

```python
# Async iteration
async for task in client.tasks.list_async(project="gid"):
    print(task.name)

# Sync iteration
for task in client.tasks.list(project="gid"):
    print(task.name)
```

## Examples

### Task Model

```python
from autom8_asana.models import Task

# Parse from API response
task = Task.model_validate(api_response)

# Access fields
print(task.name)
print(task.assignee.name if task.assignee else "Unassigned")

# Custom fields via accessor
task.cf["Status"] = "In Progress"
priority = task.cf.get("Priority", default="Medium")

# Serialize back to dict
data = task.model_dump(exclude_none=True)
```

### Project Model

```python
from autom8_asana.models import Project

project = Project.model_validate(api_response)

# Access relationships
print(f"Owner: {project.owner.name if project.owner else 'None'}")
print(f"Team: {project.team.name if project.team else 'None'}")

# Check status
if project.archived:
    print("Project is archived")
```

### NameGid Usage

```python
# Task assignee is NameGid
if task.assignee:
    print(f"Assigned to: {task.assignee.name} ({task.assignee.gid})")

# Projects list contains NameGid objects
for project in task.projects:
    print(f"In project: {project.name}")
```

### Model Validation

```python
from pydantic import ValidationError

try:
    task = Task.model_validate(data)
except ValidationError as e:
    print(f"Validation error: {e}")
```
