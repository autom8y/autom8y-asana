# Asana Domain Model

> Asana resource hierarchy and API patterns

---

## Resource Hierarchy

Asana organizes data in a strict hierarchy. Understanding this is essential for working with the SDK.

```
Workspace (organization-level container)
    |
    +-- Team (group of users)
    |       |
    |       +-- Project (collection of tasks)
    |               |
    |               +-- Section (vertical grouping within project)
    |                       |
    |                       +-- Task (work item)
    |                               |
    |                               +-- Subtask (child task)
    |                               +-- Story (comment/activity)
    |                               +-- Attachment
    |
    +-- Portfolio (collection of projects)
    |
    +-- Goal (OKR-style objective)
    |
    +-- Tag (cross-project label)
    |
    +-- Custom Field (user-defined metadata)
    |
    +-- User (team member)
```

---

## Core Resource Types

### Task

The fundamental work item. Tasks can:
- Belong to multiple projects (multi-homing)
- Have subtasks (parent-child relationship)
- Have custom field values
- Be tagged
- Have dependencies on other tasks

**Key fields**: `gid`, `name`, `completed`, `due_on`, `assignee`, `projects`, `memberships`

### Project

Container for tasks, organized by sections.

**Key fields**: `gid`, `name`, `team`, `workspace`, `default_view`, `sections`

### Section

Vertical grouping within a project (like columns in a board view).

**Key fields**: `gid`, `name`, `project`

**Important**: Tasks in a project MUST belong to a section. Asana auto-creates an "Untitled section" if none specified.

### Custom Field

User-defined metadata attached to tasks. Types:
- `text` - Free-form string
- `number` - Numeric value
- `enum` - Single-select from options
- `multi_enum` - Multi-select from options
- `date` - Date value
- `people` - User reference

**Key fields**: `gid`, `name`, `resource_subtype` (the type), `enum_options`

---

## GID (Global ID)

Every Asana resource has a **GID** - a globally unique identifier.

- Format: Numeric string (e.g., `"1234567890123456"`)
- Immutable: Never changes for a resource
- Cross-workspace: GIDs are unique across all of Asana

### Temporary GIDs

For new entities not yet created in Asana, SDK uses temporary GIDs:
- Pattern: `temp_{uuid}` or `temp_1`, `temp_2`, etc.
- SaveSession resolves these to real GIDs after creation

---

## API Patterns

### Pagination

Asana uses cursor-based pagination, not page numbers:

```python
# SDK handles this internally
async for task in client.tasks.list(project_gid):
    process(task)

# Under the hood:
# GET /tasks?project={gid}&limit=100
# GET /tasks?project={gid}&limit=100&offset={cursor}
```

### Field Expansion (opt_fields)

By default, Asana returns minimal fields. Use `opt_fields` to request more:

```python
# Minimal (default)
task = await client.tasks.get(gid)  # Only gid, name

# Expanded
task = await client.tasks.get(gid, opt_fields=[
    "name", "completed", "due_on", "assignee.name", "custom_fields"
])
```

**Common opt_fields**:
- `name`, `completed`, `due_on`, `due_at`
- `assignee`, `assignee.name`, `assignee.email`
- `projects`, `memberships`, `memberships.section`
- `custom_fields`, `custom_fields.name`
- `parent`, `num_subtasks`

### Batch API

Asana's batch endpoint executes multiple requests in one HTTP call:

- Endpoint: `POST /batch`
- Limit: **10 actions per request**
- SDK chunks automatically for larger batches

---

## Action Endpoints

Some operations use dedicated "action" endpoints rather than standard CRUD:

| Operation | Endpoint | SDK Method |
|-----------|----------|------------|
| Add tag | `POST /tasks/{gid}/addTag` | `session.add_tag()` |
| Remove tag | `POST /tasks/{gid}/removeTag` | `session.remove_tag()` |
| Add to project | `POST /tasks/{gid}/addProject` | `session.add_to_project()` |
| Remove from project | `POST /tasks/{gid}/removeProject` | `session.remove_from_project()` |
| Add dependency | `POST /tasks/{gid}/addDependencies` | `session.add_dependency()` |
| Set parent | `POST /tasks/{gid}/setParent` | `session.set_parent()` |

---

## Memberships

A task's relationship to a project is called a **membership**. Memberships include:
- Which project the task belongs to
- Which section within that project

```python
# Task can be in multiple projects
task.memberships = [
    {"project": {"gid": "123"}, "section": {"gid": "456"}},
    {"project": {"gid": "789"}, "section": {"gid": "012"}},
]
```

---

## Rate Limits

| Limit Type | Value | Notes |
|------------|-------|-------|
| Requests per minute | 1,500 | Per Personal Access Token |
| Batch actions | 10 | Per batch request |
| Concurrent connections | 50 | Recommended max |

SDK transport layer handles retry with exponential backoff on 429 responses.
