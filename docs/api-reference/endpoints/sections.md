# Sections API Endpoints

Manage Asana sections within projects.

## Overview

Sections organize tasks within an Asana project. These endpoints provide CRUD operations for sections, plus operations to add tasks and reorder sections within projects.

**Authentication**: All endpoints require a Bearer token (JWT or PAT) in the `Authorization` header.

**Base Path**: `/api/v1/sections`

## Endpoints Summary

| Method | Endpoint | Description | Status Code |
|--------|----------|-------------|-------------|
| GET | `/api/v1/sections/{gid}` | Get section by GID | 200 |
| POST | `/api/v1/sections` | Create section in project | 201 |
| PUT | `/api/v1/sections/{gid}` | Update section (rename) | 200 |
| DELETE | `/api/v1/sections/{gid}` | Delete section | 204 |
| POST | `/api/v1/sections/{gid}/tasks` | Add task to section | 204 |
| POST | `/api/v1/sections/{gid}/reorder` | Reorder section in project | 204 |

## Endpoint Details

### Get Section

**GET** `/api/v1/sections/{gid}`

Retrieve a section by its GID.

**Path Parameters:**
- `gid` (string, required): Asana section GID

**Response:** `200 OK`
```json
{
  "data": {
    "gid": "1206783719540123",
    "name": "Phase 1",
    "resource_type": "section",
    "project": {
      "gid": "1206783719540120",
      "name": "Q1 Roadmap"
    }
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

### Create Section

**POST** `/api/v1/sections`

Create a new section in a project.

**Request Body:**
```json
{
  "name": "Phase 2",
  "project": "1206783719540120"
}
```

**Fields:**
- `name` (string, required): Section name (min length: 1)
- `project` (string, required): Project GID (min length: 1)

**Response:** `201 Created`
```json
{
  "data": {
    "gid": "1206783719540125",
    "name": "Phase 2",
    "resource_type": "section",
    "project": {
      "gid": "1206783719540120",
      "name": "Q1 Roadmap"
    }
  },
  "meta": {
    "request_id": "req_def456",
    "timestamp": "2026-02-12T10:35:00Z"
  }
}
```

**Example cURL:**
```bash
curl -X POST "https://api.example.com/api/v1/sections" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Phase 2",
    "project": "1206783719540120"
  }'
```

### Update Section

**PUT** `/api/v1/sections/{gid}`

Update a section (currently supports renaming only).

**Path Parameters:**
- `gid` (string, required): Asana section GID

**Request Body:**
```json
{
  "name": "Phase 2 - Updated"
}
```

**Fields:**
- `name` (string, required): New section name (min length: 1)

**Response:** `200 OK`
```json
{
  "data": {
    "gid": "1206783719540125",
    "name": "Phase 2 - Updated",
    "resource_type": "section",
    "project": {
      "gid": "1206783719540120",
      "name": "Q1 Roadmap"
    }
  },
  "meta": {
    "request_id": "req_ghi789",
    "timestamp": "2026-02-12T10:40:00Z"
  }
}
```

### Delete Section

**DELETE** `/api/v1/sections/{gid}`

Delete a section from a project.

**Path Parameters:**
- `gid` (string, required): Asana section GID

**Response:** `204 No Content`

No response body on success.

### Add Task to Section

**POST** `/api/v1/sections/{gid}/tasks`

Add a task to a section.

**Path Parameters:**
- `gid` (string, required): Section GID

**Request Body:**
```json
{
  "task_gid": "1206783719540130"
}
```

**Fields:**
- `task_gid` (string, required): GID of the task to add (min length: 1)

**Response:** `204 No Content`

No response body on success.

**Example cURL:**
```bash
curl -X POST "https://api.example.com/api/v1/sections/1206783719540125/tasks" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_gid": "1206783719540130"
  }'
```

### Reorder Section

**POST** `/api/v1/sections/{gid}/reorder`

Reorder a section within a project. Specify position by providing exactly one of `before_section` or `after_section`.

**Path Parameters:**
- `gid` (string, required): Section GID to reorder

**Request Body:**
```json
{
  "project_gid": "1206783719540120",
  "before_section": "1206783719540123"
}
```

**Fields:**
- `project_gid` (string, required): Project GID containing the section
- `before_section` (string, optional): Section GID to insert before
- `after_section` (string, optional): Section GID to insert after

**Constraints:**
- Exactly one of `before_section` or `after_section` must be provided
- Providing neither or both will result in a `400 Bad Request` error

**Response:** `204 No Content`

No response body on success.

## Error Responses

All endpoints use standard error response format:

```json
{
  "detail": {
    "error": "RESOURCE_NOT_FOUND",
    "message": "Section not found"
  }
}
```

**Common Error Codes:**
- `400 Bad Request`: Invalid input (missing required fields, constraint violations)
- `401 Unauthorized`: Missing or invalid Bearer token
- `404 Not Found`: Section, project, or task not found
- `500 Internal Server Error`: Unexpected server error

## Response Envelope

Success responses (200/201) use the standard envelope:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_unique_id",
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

Empty responses (204) have no body.

## See Also

- [Tasks API](./tasks.md) - Task operations including creation and updates
- [Projects API](./projects.md) - Project management operations
