# Projects API

> Manage Asana projects with full CRUD operations, sections, and team membership.

## Authentication

Dual-mode Bearer token authentication via `Authorization: Bearer <token>` header.

**JWT Mode:** Service-to-service JWT token. Validates service token, uses bot PAT for Asana calls.

**PAT Mode:** User's Personal Access Token. Uses PAT directly for Asana calls.

**Requirements:**
- Header: `Authorization: Bearer <token>`
- Token minimum length: 10 characters
- Scheme: `Bearer` (required)

## Endpoints Summary

8 endpoints in 3 categories:

| Method | Path | Description |
|--------|------|-------------|
| **CRUD** | | |
| GET | `/api/v1/projects` | List projects by workspace (paginated) |
| GET | `/api/v1/projects/{gid}` | Get project by GID with optional field filtering |
| POST | `/api/v1/projects` | Create a new project |
| PUT | `/api/v1/projects/{gid}` | Update existing project fields |
| DELETE | `/api/v1/projects/{gid}` | Delete project (204 No Content) |
| **Related** | | |
| GET | `/api/v1/projects/{gid}/sections` | List sections in project (paginated) |
| **Membership** | | |
| POST | `/api/v1/projects/{gid}/members` | Add members to project |
| DELETE | `/api/v1/projects/{gid}/members` | Remove members from project |

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

**Pagination** appears only on list endpoints (projects, sections). Omitted on single-resource endpoints.

## CRUD Endpoints

### `GET /api/v1/projects`

List projects by workspace with cursor-based pagination.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `workspace` | string | Yes | - | Workspace GID to list projects from |
| `limit` | integer | No | 100 | Items per page (1-100) |
| `offset` | string | No | - | Pagination cursor from previous response |

**Response Body:**

```json
{
  "data": [
    {
      "gid": "1111111111111111",
      "name": "Marketing Campaign Q1",
      "notes": "Campaign planning and execution",
      "archived": false,
      "owner": {
        "gid": "9876543210987654",
        "name": "Jane Doe"
      },
      "team": {
        "gid": "8888888888888888",
        "name": "Marketing"
      },
      "workspace": {
        "gid": "7777777777777777",
        "name": "Acme Corp"
      }
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

**Example: List projects by workspace (cURL)**

```bash
curl -X GET "https://api.example.com/api/v1/projects?workspace=7777777777777777&limit=50" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: List projects with pagination (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/api/v1/projects",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "workspace": "7777777777777777",
            "limit": 100
        }
    )
    result = response.json()

    projects = result["data"]
    pagination = result["meta"]["pagination"]

    print(f"Found {len(projects)} projects")
    if pagination["has_more"]:
        print(f"Next offset: {pagination['next_offset']}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_PARAMETER` | Workspace parameter missing |
| 404 | `NOT_FOUND` | Workspace GID does not exist |

---

### `GET /api/v1/projects/{gid}`

Get a project by its GID with optional field filtering.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana project GID |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `opt_fields` | string | No | Comma-separated list of fields to include (e.g., `name,notes,owner,team`) |

**Response Body:**

```json
{
  "data": {
    "gid": "1111111111111111",
    "name": "Marketing Campaign Q1",
    "notes": "Campaign planning and execution",
    "archived": false,
    "owner": {
      "gid": "9876543210987654",
      "name": "Jane Doe"
    },
    "team": {
      "gid": "8888888888888888",
      "name": "Marketing"
    }
  },
  "meta": {
    "request_id": "abc123def4567890",
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

**Example: Get project with all fields (cURL)**

```bash
curl -X GET "https://api.example.com/api/v1/projects/1111111111111111" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: Get project with specific fields (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "https://api.example.com/api/v1/projects/1111111111111111",
        headers={"Authorization": f"Bearer {token}"},
        params={"opt_fields": "name,notes,owner,team,archived"}
    )
    result = response.json()
    project = result["data"]
    print(f"Project: {project['name']} - Archived: {project['archived']}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `NOT_FOUND` | Project GID does not exist |

---

### `POST /api/v1/projects`

Create a new project.

**Request Body:**

```json
{
  "name": "Marketing Campaign Q2",
  "workspace": "7777777777777777",
  "team": "8888888888888888"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Project name (min length: 1) |
| `workspace` | string | Yes | Workspace GID to create project in |
| `team` | string | No | Team GID to associate project with |

**Response Body:**

Returns created project data (same structure as GET response). HTTP status: `201 Created`.

**Example: Create project (cURL)**

```bash
curl -X POST https://api.example.com/api/v1/projects \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Marketing Campaign Q2",
    "workspace": "7777777777777777",
    "team": "8888888888888888"
  }'
```

**Example: Create project without team (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.example.com/api/v1/projects",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "name": "New Project",
            "workspace": "7777777777777777"
        }
    )
    result = response.json()
    project_gid = result["data"]["gid"]
    print(f"Created project: {project_gid}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 422 | `VALIDATION_ERROR` | Name or workspace missing or invalid |
| 404 | `NOT_FOUND` | Workspace or team GID does not exist |

---

### `PUT /api/v1/projects/{gid}`

Update an existing project. Only provided fields are updated; omitted fields retain their current values.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana project GID |

**Request Body:**

```json
{
  "name": "Marketing Campaign Q1 (Updated)",
  "notes": "Updated campaign notes",
  "archived": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | New project name (min length: 1) |
| `notes` | string | New project description |
| `archived` | boolean | Archive status |

All fields optional. Omit any field to leave it unchanged. At least one field must be provided.

**Response Body:**

Returns updated project data (same structure as GET response).

**Example: Update project name and notes (cURL)**

```bash
curl -X PUT https://api.example.com/api/v1/projects/1111111111111111 \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Marketing Campaign Q1 (Updated)",
    "notes": "Updated campaign notes"
  }'
```

**Example: Archive project (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.put(
        f"https://api.example.com/api/v1/projects/{project_gid}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"archived": True}
    )
    result = response.json()
    print(f"Project archived: {result['data']['archived']}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_PARAMETER` | No fields provided for update |
| 404 | `NOT_FOUND` | Project GID does not exist |
| 422 | `VALIDATION_ERROR` | Invalid field values |

---

### `DELETE /api/v1/projects/{gid}`

Delete a project permanently.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Asana project GID |

**Response:** `204 No Content` on success (no response body).

**Example: Delete project (cURL)**

```bash
curl -X DELETE https://api.example.com/api/v1/projects/1111111111111111 \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: Delete project (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.delete(
        f"https://api.example.com/api/v1/projects/{project_gid}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 204:
        print("Project deleted successfully")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `NOT_FOUND` | Project GID does not exist |

## Related Operations

### `GET /api/v1/projects/{gid}/sections`

List all sections in a project with cursor-based pagination.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Project GID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 100 | Items per page (1-100) |
| `offset` | string | No | - | Pagination cursor from previous response |

**Response Body:**

```json
{
  "data": [
    {
      "gid": "3333333333333333",
      "name": "To Do",
      "project": {
        "gid": "1111111111111111",
        "name": "Marketing Campaign Q1"
      }
    },
    {
      "gid": "4444444444444444",
      "name": "In Progress",
      "project": {
        "gid": "1111111111111111",
        "name": "Marketing Campaign Q1"
      }
    }
  ],
  "meta": {
    "request_id": "abc123def4567890",
    "timestamp": "2026-02-12T10:30:00Z",
    "pagination": {
      "limit": 100,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

**Example: List sections (cURL)**

```bash
curl -X GET "https://api.example.com/api/v1/projects/1111111111111111/sections?limit=50" \
  -H "Authorization: Bearer <TOKEN>"
```

**Example: List sections (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        f"https://api.example.com/api/v1/projects/{project_gid}/sections",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 100}
    )
    result = response.json()

    sections = result["data"]
    print(f"Project has {len(sections)} sections")
    for section in sections:
        print(f"  - {section['name']}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `NOT_FOUND` | Project GID does not exist |

## Membership Operations

### `POST /api/v1/projects/{gid}/members`

Add members to a project. Members gain access to the project and its tasks.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Project GID |

**Request Body:**

```json
{
  "members": ["9876543210987654", "9876543210987655"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `members` | array[string] | Yes | List of user GIDs to add (min length: 1) |

**Response Body:**

Returns updated project data (same structure as GET response).

**Example: Add members (cURL)**

```bash
curl -X POST https://api.example.com/api/v1/projects/1111111111111111/members \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "members": ["9876543210987654", "9876543210987655"]
  }'
```

**Example: Add single member (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        f"https://api.example.com/api/v1/projects/{project_gid}/members",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"members": [user_gid]}
    )
    result = response.json()
    print(f"Added member to project: {project_gid}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `NOT_FOUND` | Project or user GID does not exist |
| 422 | `VALIDATION_ERROR` | Members list empty or invalid |

---

### `DELETE /api/v1/projects/{gid}/members`

Remove members from a project. Removed members lose access to the project.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `gid` | string | Project GID |

**Request Body:**

```json
{
  "members": ["9876543210987654"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `members` | array[string] | Yes | List of user GIDs to remove (min length: 1) |

**Response Body:**

Returns updated project data (same structure as GET response).

**Example: Remove members (cURL)**

```bash
curl -X DELETE https://api.example.com/api/v1/projects/1111111111111111/members \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "members": ["9876543210987654"]
  }'
```

**Example: Remove member (Python httpx)**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.delete(
        f"https://api.example.com/api/v1/projects/{project_gid}/members",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"members": [user_gid]}
    )
    result = response.json()
    print(f"Removed member from project: {project_gid}")
```

**Errors:**

| Status | Error Code | Description |
|--------|------------|-------------|
| 404 | `NOT_FOUND` | Project or user GID does not exist |
| 422 | `VALIDATION_ERROR` | Members list empty or invalid |

## Common Error Responses

All endpoints return errors in a consistent format:

```json
{
  "detail": {
    "error": "NOT_FOUND",
    "message": "Project not found: 1111111111111111"
  }
}
```

### Error Codes by Status

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `INVALID_PARAMETER` | Invalid request parameter (missing required field, conflicting parameters) |
| 404 | `NOT_FOUND` | Project, workspace, team, or user GID does not exist |
| 422 | `VALIDATION_ERROR` | Request body validation failed (invalid format, missing required fields) |

### Error Response Examples

**Project Not Found:**

```json
{
  "detail": {
    "error": "NOT_FOUND",
    "message": "Project not found: 1111111111111111"
  }
}
```

**Invalid Parameter:**

```json
{
  "detail": {
    "error": "INVALID_PARAMETER",
    "message": "At least one field must be provided for update"
  }
}
```

**Validation Error:**

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "input": "",
      "ctx": {"min_length": 1}
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
- Comma-separated list (no spaces): `name,notes,owner,team`
- Invalid field names are silently ignored by Asana API

**Team Association:**
- Projects can optionally belong to a team
- Team membership affects project visibility and permissions
- Team parameter is optional during creation

**Archive Behavior:**
- Archived projects are hidden from most views in Asana
- Archived projects can be restored by setting `archived: false`
- Deleting a project is permanent and cannot be undone

**Project Membership:**
- Members must be workspace members to be added to projects
- Project owner is automatically a member
- Removing all members does not delete the project

## See Also

- [Tasks API](./tasks.md) - Manage tasks within projects
- Sections API - Manage project sections
