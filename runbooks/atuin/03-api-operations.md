# API Operations

API usage guide for autom8_asana service: health checks, task operations, and endpoint examples.

**Time:** varies

---

## Prerequisites

- Complete [00-bootstrap.md](./00-bootstrap.md) first
- Complete [01-authentication.md](./01-authentication.md) (PAT configured)
- Development server running (see [02-local-development.md](./02-local-development.md))

---

## Service Health Check

Check if the autom8_asana API service is healthy.

```
---
type: http
name: service_health
---
GET http://localhost:8000/health
Accept: application/json
```

---

## Direct Asana API: Get User

Call Asana API directly to get current user info.

```
---
type: http
name: asana_get_user
---
GET https://app.asana.com/api/1.0/users/me
Authorization: Bearer {{env.ASANA_PAT}}
Accept: application/json
```

---

## Direct Asana API: List Workspaces

Get all accessible workspaces.

```
---
type: http
name: asana_list_workspaces
---
GET https://app.asana.com/api/1.0/workspaces
Authorization: Bearer {{env.ASANA_PAT}}
Accept: application/json
```

---

## Direct Asana API: List Projects

List projects in a workspace. Replace `WORKSPACE_GID` with actual workspace ID.

[var WORKSPACE_GID = "your_workspace_gid"]

```
---
type: http
name: asana_list_projects
---
GET https://app.asana.com/api/1.0/workspaces/{{var.WORKSPACE_GID}}/projects
Authorization: Bearer {{env.ASANA_PAT}}
Accept: application/json
```

---

## Direct Asana API: Get Task

Get details for a specific task. Replace with actual task GID.

[var TASK_GID = "your_task_gid"]

```
---
type: http
name: asana_get_task
---
GET https://app.asana.com/api/1.0/tasks/{{var.TASK_GID}}
Authorization: Bearer {{env.ASANA_PAT}}
Accept: application/json
```

---

## Direct Asana API: Create Task

Create a new task in a project. Replace project GID.

[var PROJECT_GID = "your_project_gid"]

```
---
type: http
name: asana_create_task
---
POST https://app.asana.com/api/1.0/tasks
Authorization: Bearer {{env.ASANA_PAT}}
Content-Type: application/json
Accept: application/json

{
  "data": {
    "name": "Test Task from Runbook",
    "notes": "Created via autom8_asana runbook",
    "projects": ["{{var.PROJECT_GID}}"]
  }
}
```

---

## Direct Asana API: Update Task

Update an existing task's name and notes.

```
---
type: http
name: asana_update_task
---
PUT https://app.asana.com/api/1.0/tasks/{{var.TASK_GID}}
Authorization: Bearer {{env.ASANA_PAT}}
Content-Type: application/json
Accept: application/json

{
  "data": {
    "name": "Updated Task Name",
    "notes": "Updated via autom8_asana runbook"
  }
}
```

---

## Direct Asana API: Complete Task

Mark a task as complete.

```
---
type: http
name: asana_complete_task
---
PUT https://app.asana.com/api/1.0/tasks/{{var.TASK_GID}}
Authorization: Bearer {{env.ASANA_PAT}}
Content-Type: application/json
Accept: application/json

{
  "data": {
    "completed": true
  }
}
```

---

## Quick Reference

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get User | GET | `/users/me` |
| List Workspaces | GET | `/workspaces` |
| List Projects | GET | `/workspaces/{gid}/projects` |
| Get Task | GET | `/tasks/{gid}` |
| Create Task | POST | `/tasks` |
| Update Task | PUT | `/tasks/{gid}` |
| Delete Task | DELETE | `/tasks/{gid}` |

---

## Rate Limits

| Limit Type | Value |
|------------|-------|
| Standard | 1500 requests/minute |
| Free tier | 150 requests/minute |
| Retry-After | Check header on 429 |

---

## Troubleshooting

### 401 Unauthorized

```
Cause: Invalid or expired PAT
ACTION: Regenerate PAT at https://app.asana.com/0/my-apps
```

### 403 Forbidden

```
Cause: No access to resource
ACTION: Check project/workspace membership in Asana
```

### 404 Not Found

```
Cause: Resource doesn't exist or no access
ACTION: Verify GID is correct and accessible
```

### 429 Rate Limited

```
Cause: Too many requests
ACTION: Wait for Retry-After header value, then retry
```

