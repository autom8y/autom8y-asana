# Tasks API

> Manage Asana tasks with full CRUD operations, relationships, tags, and project membership.

## Authentication

Dual-mode Bearer token authentication via `Authorization: Bearer <token>` header.

**JWT Mode:** Service-to-service JWT token. Validates service token, uses bot PAT for Asana calls.

**PAT Mode:** User's Personal Access Token. Uses PAT directly for Asana calls.

**Requirements:**
- Header: `Authorization: Bearer <token>`
- Token minimum length: 10 characters
- Scheme: `Bearer` (required)

## Endpoints Summary

14 endpoints in 4 categories:

| Method | Path | Description |
|--------|------|-------------|
| **CRUD** | | |
| GET | `/api/v1/tasks` | List tasks by project or section (paginated) |
| GET | `/api/v1/tasks/{gid}` | Get task by GID with optional field filtering |
| POST | `/api/v1/tasks` | Create a new task |
| PUT | `/api/v1/tasks/{gid}` | Update existing task fields |
| DELETE | `/api/v1/tasks/{gid}` | Delete task (204 No Content) |
| **Related** | | |
| GET | `/api/v1/tasks/{gid}/subtasks` | List task's subtasks (paginated) |
| GET | `/api/v1/tasks/{gid}/dependents` | List dependent tasks (paginated) |
| POST | `/api/v1/tasks/{gid}/duplicate` | Duplicate task with new name |
| **Tags** | | |
| POST | `/api/v1/tasks/{gid}/tags` | Add tag to task |
| DELETE | `/api/v1/tasks/{gid}/tags/{tag_gid}` | Remove tag from task |
| **Membership** | | |
| POST | `/api/v1/tasks/{gid}/section` | Move task to section within project |
| PUT | `/api/v1/tasks/{gid}/assignee` | Set or clear task assignee |
| POST | `/api/v1/tasks/{gid}/projects` | Add task to project |
| DELETE | `/api/v1/tasks/{gid}/projects/{project_gid}` | Remove task from project |

## Response Envelope

All successful responses use `SuccessResponse`:

```json
{
  "data": <response_data>,
  "meta": {
    "request_id": "16-char hex",
    "timestamp": "ISO 8601 UTC",
    "pagination": {
      "limit": 100,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

**Pagination** appears only on list endpoints (tasks, subtasks, dependents). Omitted on single-resource endpoints.

## CRUD Endpoints

### `GET /api/v1/tasks`

List tasks by project or section with cursor-based pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project` | string | * | - | Project GID to list tasks from |
| `section` | string | * | - | Section GID to list tasks from |
| `limit` | integer | No | 100 | Items per page (1-100) |
| `offset` | string | No | - | Pagination cursor from previous response |

\* **Note:** Exactly one of `project` or `section` required. Providing both or neither returns `400 INVALID_PARAMETER`.

**Response Body:**

```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Review Q1 Budget",
      "notes": "Annual budget review",
      "completed": false,
      "assignee": {
        "gid": "9876543210987654",
        "name": "Jane Doe"
      },
      "due_on": "2026-03-15",
      "projects": [
        {
          "gid": "1111111111111111",
          "name": "Finance"
        }
      ]
    }
  ],
  "meta": {
    "request_id": "abc123def4567890",
    "timestamp": "2026-02-12T10:30:00Z",
    "pagination": {
      "limit": 100,
      "has_more": true,
      "next_offset": "eyJvZmZzZXQiOiIxMDAifQ=="
    }
  }
}
```

**Example: List tasks by project (cURL)**

```bash
curl -X GET "https://api.example.com/api/v1/tasks?project=1111111111111111&limit=50" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: List tasks by section (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "section": "2222222222222222",
            "limit": 100
        }
    )
    result = response.json()

    tasks = result["data"]
    pagination = result["meta"]["pagination"]

    print(f"Found {len(tasks)} tasks")
    if pagination["has_more"]:
        print(f"Next offset: {pagination['next_offset']}")
```

**Example: Paginate through all tasks**

```python
import httpx

async def fetch_all_tasks(project_gid: str, token: str) -> list[dict]:
    """Fetch all tasks in a project with cursor pagination."""
    all_tasks = []
    offset = None

    async with httpx.AsyncClient() as client:
        while True:
            params = {"project": project_gid, "limit": 100}
            if offset:
                params["offset"] = offset

            response = await client.get(
                "https://api.example.com/api/v1/tasks",
                headers={"Authorization": f"Bearer {token}"},
                params=params
            )
            response.raise_for_status()
            result = response.json()

            all_tasks.extend(result["data"])

            pagination = result["meta"]["pagination"]
            if not pagination["has_more"]:
                break

            offset = pagination["next_offset"]

    return all_tasks
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_PARAMETER` | Neither project nor section provided, or both provided |
| 404 | `TASK_NOT_FOUND` | Project or section GID does not exist |
| 503 | `CACHE_NOT_READY` | Service cache not warmed for entity type |

---

### `GET /api/v1/tasks/{gid}`

Get a task by its GID with optional field filtering.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana task GID |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `opt_fields` | string | No | Comma-separated list of fields to include (e.g., `name,notes,due_on,assignee`) |

**Response Body:**

```json
{
  "data": {
    "gid": "1234567890123456",
    "name": "Review Q1 Budget",
    "notes": "Annual budget review",
    "completed": false,
    "assignee": {
      "gid": "9876543210987654",
      "name": "Jane Doe"
    },
    "due_on": "2026-03-15"
  },
  "meta": {
    "request_id": "abc123def4567890",
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

**Example: Get task with all fields (cURL)**

```bash
curl -X GET "https://api.example.com/api/v1/tasks/1234567890123456" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: Get task with specific fields (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/api/v1/tasks/1234567890123456",
        headers={"Authorization": f"Bearer {token}"},
        params={"opt_fields": "name,notes,due_on,completed,assignee"}
    )
    result = response.json()
    task = result["data"]
    print(f"Task: {task['name']} - Due: {task['due_on']}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task GID does not exist |

---

### `POST /api/v1/tasks`

Create a new task.

**Request Body:**

```json
{
  "name": "Review Q1 Budget",
  "notes": "Annual budget review",
  "assignee": "9876543210987654",
  "projects": ["1111111111111111"],
  "due_on": "2026-03-15",
  "workspace": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Task name (min length: 1) |
| `notes` | string | No | Task description |
| `assignee` | string | No | Assignee user GID |
| `projects` | array[string] | * | Project GIDs to add task to |
| `due_on` | string | No | Due date in `YYYY-MM-DD` format |
| `workspace` | string | * | Workspace GID (required if no projects) |

\* **Note:** Either `projects` or `workspace` required. Providing `projects` adds task to those projects. Providing only `workspace` creates unattached task in workspace.

**Response Body:**

Returns created task data (same structure as GET response). HTTP status: `201 Created`.

**Example: Create task in project (cURL)**

```bash
curl -X POST https://api.example.com/api/v1/tasks \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Review Q1 Budget",
    "notes": "Annual budget review",
    "assignee": "9876543210987654",
    "projects": ["1111111111111111"],
    "due_on": "2026-03-15"
  }'
```

**Example: Create task in workspace (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.example.com/api/v1/tasks",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "name": "New Task",
            "notes": "Task description",
            "workspace": "8888888888888888"
        }
    )
    result = response.json()
    task_gid = result["data"]["gid"]
    print(f"Created task: {task_gid}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_PARAMETER` | Neither projects nor workspace provided |
| 422 | `VALIDATION_ERROR` | Invalid due_on format (must be YYYY-MM-DD) |
| 404 | `TASK_NOT_FOUND` | Project or workspace GID does not exist |

---

### `PUT /api/v1/tasks/{gid}`

Update an existing task. Only provided fields are updated; omitted fields retain their current values.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana task GID |

**Request Body:**

```json
{
  "name": "Review Q1 and Q2 Budget",
  "notes": "Extended budget review",
  "completed": true,
  "due_on": "2026-03-20"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | New task name (min length: 1) |
| `notes` | string | New task description |
| `completed` | boolean | Task completion status |
| `due_on` | string \| null | Due date in `YYYY-MM-DD` format (null to clear) |

All fields optional. Omit any field to leave it unchanged.

**Response Body:**

Returns updated task data (same structure as GET response).

**Example: Update task name and due date (cURL)**

```bash
curl -X PUT https://api.example.com/api/v1/tasks/1234567890123456 \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Review Q1 and Q2 Budget",
    "due_on": "2026-03-20"
  }'
```

**Example: Mark task complete (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.put(
        f"https://api.example.com/api/v1/tasks/{task_gid}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"completed": True}
    )
    result = response.json()
    print(f"Task completed: {result['data']['completed']}")
```

**Example: Clear due date**

```python
# Set due_on to null to clear the due date
response = await client.put(
    f"https://api.example.com/api/v1/tasks/{task_gid}",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json={"due_on": None}
)
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task GID does not exist |
| 422 | `VALIDATION_ERROR` | Invalid due_on format (must be YYYY-MM-DD or null) |

---

### `DELETE /api/v1/tasks/{gid}`

Delete a task permanently.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana task GID |

**Response:** `204 No Content` on success (no response body).

**Example: Delete task (cURL)**

```bash
curl -X DELETE https://api.example.com/api/v1/tasks/1234567890123456 \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: Delete task (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.delete(
        f"https://api.example.com/api/v1/tasks/{task_gid}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 204:
        print("Task deleted successfully")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task GID does not exist |

## Related Operations

### `GET /api/v1/tasks/{gid}/subtasks`

List all subtasks of a task with cursor-based pagination.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Parent task GID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 100 | Items per page (1-100) |
| `offset` | string | No | - | Pagination cursor from previous response |

**Response Body:**

Same structure as `GET /api/v1/tasks` (array of tasks with pagination).

**Example: List subtasks (cURL)**

```bash
curl -X GET "https://api.example.com/api/v1/tasks/1234567890123456/subtasks?limit=50" \
  -H "Authorization: Bearer <TOKEN>"
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Parent task GID does not exist |

---

### `GET /api/v1/tasks/{gid}/dependents`

List all tasks that depend on this task (tasks blocked by this task) with cursor-based pagination.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Task GID to get dependents for |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 100 | Items per page (1-100) |
| `offset` | string | No | - | Pagination cursor from previous response |

**Response Body:**

Same structure as `GET /api/v1/tasks` (array of tasks with pagination).

**Example: List dependent tasks (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        f"https://api.example.com/api/v1/tasks/{task_gid}/dependents",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 100}
    )
    result = response.json()

    dependents = result["data"]
    print(f"{len(dependents)} tasks depend on this task")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task GID does not exist |

---

### `POST /api/v1/tasks/{gid}/duplicate`

Duplicate a task with a new name. Copies task properties but creates a new GID.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | GID of task to duplicate |

**Request Body:**

```json
{
  "name": "Review Q2 Budget (Copy)"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Name for the duplicated task (min length: 1) |

**Response Body:**

Returns new duplicated task data (same structure as GET response). HTTP status: `201 Created`.

**Example: Duplicate task (cURL)**

```bash
curl -X POST https://api.example.com/api/v1/tasks/1234567890123456/duplicate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Review Q2 Budget (Copy)"
  }'
```

**Example: Duplicate task (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        f"https://api.example.com/api/v1/tasks/{task_gid}/duplicate",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"name": f"{original_name} (Copy)"}
    )
    result = response.json()
    new_gid = result["data"]["gid"]
    print(f"Duplicated task GID: {new_gid}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Source task GID does not exist |
| 422 | `VALIDATION_ERROR` | Name field missing or empty |

## Tags

### `POST /api/v1/tasks/{gid}/tags`

Add a tag to a task.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Task GID |

**Request Body:**

```json
{
  "tag_gid": "5555555555555555"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tag_gid` | string | Yes | Tag GID to add (min length: 1) |

**Response Body:**

Returns updated task data (same structure as GET response).

**Example: Add tag (cURL)**

```bash
curl -X POST https://api.example.com/api/v1/tasks/1234567890123456/tags \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "tag_gid": "5555555555555555"
  }'
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task or tag GID does not exist |

---

### `DELETE /api/v1/tasks/{gid}/tags/{tag_gid}`

Remove a tag from a task.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Task GID |
| `tag_gid` | string | Tag GID to remove |

**Response Body:**

Returns updated task data (same structure as GET response).

**Example: Remove tag (cURL)**

```bash
curl -X DELETE https://api.example.com/api/v1/tasks/1234567890123456/tags/5555555555555555 \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: Remove tag (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.delete(
        f"https://api.example.com/api/v1/tasks/{task_gid}/tags/{tag_gid}",
        headers={"Authorization": f"Bearer {token}"}
    )
    result = response.json()
    print("Tag removed successfully")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task or tag GID does not exist |

## Membership

### `POST /api/v1/tasks/{gid}/section`

Move a task to a section within a project.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Task GID |

**Request Body:**

```json
{
  "section_gid": "3333333333333333",
  "project_gid": "1111111111111111"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `section_gid` | string | Yes | Target section GID (min length: 1) |
| `project_gid` | string | Yes | Project GID containing the section (min length: 1) |

**Response Body:**

Returns updated task data (same structure as GET response).

**Example: Move task to section (cURL)**

```bash
curl -X POST https://api.example.com/api/v1/tasks/1234567890123456/section \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "section_gid": "3333333333333333",
    "project_gid": "1111111111111111"
  }'
```

**Example: Move task to section (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        f"https://api.example.com/api/v1/tasks/{task_gid}/section",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "section_gid": section_gid,
            "project_gid": project_gid
        }
    )
    result = response.json()
    print("Task moved to section successfully")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task, section, or project GID does not exist |
| 404 | `UNKNOWN_SECTION` | Section not found in specified project |

---

### `PUT /api/v1/tasks/{gid}/assignee`

Set or clear the task assignee.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Task GID |

**Request Body:**

```json
{
  "assignee_gid": "9876543210987654"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `assignee_gid` | string \| null | User GID to assign (null to unassign) |

**Response Body:**

Returns updated task data (same structure as GET response).

**Example: Set assignee (cURL)**

```bash
curl -X PUT https://api.example.com/api/v1/tasks/1234567890123456/assignee \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "assignee_gid": "9876543210987654"
  }'
```

**Example: Unassign task (Python httpx)**

```python
import httpx

# Set assignee_gid to null to unassign
async with httpx.AsyncClient() as client:
    response = await client.put(
        f"https://api.example.com/api/v1/tasks/{task_gid}/assignee",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"assignee_gid": None}
    )
    result = response.json()
    print("Task unassigned successfully")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task or user GID does not exist |

---

### `POST /api/v1/tasks/{gid}/projects`

Add a task to a project.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Task GID |

**Request Body:**

```json
{
  "project_gid": "1111111111111111"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_gid` | string | Yes | Project GID to add task to (min length: 1) |

**Response Body:**

Returns updated task data (same structure as GET response).

**Example: Add task to project (cURL)**

```bash
curl -X POST https://api.example.com/api/v1/tasks/1234567890123456/projects \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_gid": "1111111111111111"
  }'
```

**Example: Add task to multiple projects**

```python
import httpx

async def add_to_projects(task_gid: str, project_gids: list[str], token: str):
    """Add a task to multiple projects."""
    async with httpx.AsyncClient() as client:
        for project_gid in project_gids:
            response = await client.post(
                f"https://api.example.com/api/v1/tasks/{task_gid}/projects",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"project_gid": project_gid}
            )
            response.raise_for_status()

    print(f"Added task to {len(project_gids)} projects")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task or project GID does not exist |

---

### `DELETE /api/v1/tasks/{gid}/projects/{project_gid}`

Remove a task from a project.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Task GID |
| `project_gid` | string | Project GID to remove task from |

**Response Body:**

Returns updated task data (same structure as GET response).

**Example: Remove task from project (cURL)**

```bash
curl -X DELETE https://api.example.com/api/v1/tasks/1234567890123456/projects/1111111111111111 \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: Remove task from project (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.delete(
        f"https://api.example.com/api/v1/tasks/{task_gid}/projects/{project_gid}",
        headers={"Authorization": f"Bearer {token}"}
    )
    result = response.json()
    print("Task removed from project successfully")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `TASK_NOT_FOUND` | Task or project GID does not exist |

## Common Error Responses

All endpoints return errors in a consistent format:

```json
{
  "detail": {
    "error": "TASK_NOT_FOUND",
    "message": "Task not found: 1234567890123456"
  }
}
```

### Error Codes by Status

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_PARAMETER` | Invalid request parameter (missing required field, conflicting parameters) |
| 404 | `TASK_NOT_FOUND` | Task GID does not exist in Asana |
| 404 | `UNKNOWN_SECTION` | Section not found in specified project |
| 422 | `VALIDATION_ERROR` | Request body validation failed (invalid format, missing required fields) |
| 503 | `CACHE_NOT_READY` | Service cache not warmed for entity type |

### Error Response Examples

**Task Not Found:**

```json
{
  "detail": {
    "error": "TASK_NOT_FOUND",
    "message": "Task not found: 1234567890123456"
  }
}
```

**Invalid Parameter:**

```json
{
  "detail": {
    "error": "INVALID_PARAMETER",
    "message": "Must provide exactly one of: project, section"
  }
}
```

**Validation Error:**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "due_on"],
      "msg": "String should match pattern '^\\d{4}-\\d{2}-\\d{2}$'",
      "input": "2026-13-45",
      "ctx": {"pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
    }
  ]
}
```

## Notes

**Pagination:**
- Cursor-based pagination using opaque `offset` tokens
- Default limit: 100 items per page
- Maximum limit: 100 items per page
- `has_more` indicates if additional pages exist
- `next_offset` is null when `has_more` is false

**Field Filtering:**
- `opt_fields` reduces payload size by requesting only needed fields
- Comma-separated list (no spaces): `name,notes,due_on,assignee`
- Invalid field names are silently ignored by Asana API

**Date Format:**
- All dates use ISO 8601 format: `YYYY-MM-DD`
- Due dates validated with regex: `^\d{4}-\d{2}-\d{2}$`
- Set `due_on` to null to clear existing due date

**Assignee Handling:**
- `assignee_gid` accepts user GID or null
- Setting to null unassigns the task
- Assignee must be a workspace member

**Project Membership:**
- Tasks can belong to multiple projects
- Removing from last project makes task unattached (remains in workspace)
- Moving to section requires task already be in that project

## See Also

- [Entity Write API](./entity-write.md) - Write custom fields to tasks
- [Entity Resolver API](./resolver.md) - Resolve business identifiers to task GIDs
- Projects API - Manage Asana projects
- Sections API - Manage project sections
