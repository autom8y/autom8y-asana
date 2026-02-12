# API Reference

Reference documentation for the autom8_asana REST API.

## Audience

This documentation is for service integrators and developers who need to call the autom8_asana API endpoints. It covers authentication, pagination, error handling, and all available route groups.

## Base URLs

The API uses different base paths for different authentication modes:

- **Standard routes**: `https://{host}/api/v1/`
  - Supports PAT Bearer authentication
  - Used for Asana resource operations (tasks, projects, sections, users, workspaces)

- **Service-to-service (S2S) routes**: `https://{host}/v1/`
  - Requires S2S JWT authentication
  - Used for entity resolution, query operations, and internal APIs

- **Health checks**: `https://{host}/health`
  - No version prefix
  - No authentication required

## Authentication

The API supports two authentication modes depending on the endpoint.

### PAT Bearer Authentication

Direct Asana Personal Access Token authentication for standard resource routes.

```bash
curl -H "Authorization: Bearer xoxp-..." \
  https://api.example.com/api/v1/tasks/1234567890123456
```

**When to use**: Tasks, projects, sections, users, workspaces, dataframes, and webhook endpoints.

**How it works**: Your PAT is passed directly to the Asana API. The service acts as a proxy with caching and enhanced querying.

### S2S JWT Authentication

Service-to-service authentication using JWTs issued by the autom8y auth service.

```bash
curl -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  https://api.example.com/v1/resolve/unit
```

**When to use**: Entity resolution (`/v1/resolve/*`), entity query (`/v1/query/*`), entity write (`/api/v1/entity/*`), internal routes (`/api/v1/internal/*`), and admin routes (`/v1/admin/*`).

**How it works**: The JWT is validated against the JWKS endpoint. The service uses its configured bot PAT to make Asana API calls on behalf of the requesting service.

### No Authentication

Health check endpoints require no authentication.

```bash
curl https://api.example.com/health
```

## Pagination

List endpoints use cursor-based pagination following Asana's pagination model.

### Request Parameters

```bash
# First page (default limit: 100)
GET /api/v1/tasks?project=1234567890123456

# Custom page size
GET /api/v1/tasks?project=1234567890123456&limit=50

# Subsequent pages
GET /api/v1/tasks?project=1234567890123456&offset=eyJvZmZzZXQiOjUwfQ
```

**Query parameters**:
- `limit`: Number of items per page (1-100, default 100)
- `offset`: Opaque cursor from previous response (omit for first page)

### Response Format

```json
{
  "data": [
    {"gid": "1234567890123456", "name": "Task 1"},
    {"gid": "1234567890123457", "name": "Task 2"}
  ],
  "meta": {
    "request_id": "a1b2c3d4e5f67890",
    "timestamp": "2026-02-12T10:30:00Z",
    "pagination": {
      "limit": 100,
      "has_more": true,
      "next_offset": "eyJvZmZzZXQiOjEwMH0"
    }
  }
}
```

**Pagination fields**:
- `has_more`: `true` if more results exist
- `next_offset`: Cursor to use for next request (null when `has_more` is false)

**Example pagination loop**:

```bash
offset=""
while true; do
  response=$(curl "https://api.example.com/api/v1/tasks?project=123&limit=50&offset=$offset")
  # Process response...

  has_more=$(echo "$response" | jq -r '.meta.pagination.has_more')
  if [ "$has_more" != "true" ]; then
    break
  fi

  offset=$(echo "$response" | jq -r '.meta.pagination.next_offset')
done
```

## Error Responses

All errors return a JSON response with standard structure.

### Error Format

```json
{
  "detail": {
    "error": "RESOURCE_NOT_FOUND",
    "message": "Task with GID 1234567890123456 not found"
  }
}
```

Some errors include additional context:

```json
{
  "detail": {
    "error": "INVALID_SCHEMA",
    "message": "Unknown schema 'invalid'. Valid schemas: base, unit, contact, business, offer",
    "valid_schemas": ["base", "unit", "contact", "business", "offer"]
  }
}
```

### Common Status Codes

| Status | Error Code | Description |
|--------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Request parameters failed validation |
| 400 | `INVALID_SCHEMA` | Unknown schema name in dataframe request |
| 401 | `MISSING_AUTH` | No Authorization header provided |
| 401 | `INVALID_TOKEN` | Token format is invalid |
| 401 | `SERVICE_TOKEN_REQUIRED` | PAT provided for S2S-only endpoint |
| 403 | `FORBIDDEN` | Insufficient permissions for requested resource |
| 404 | `RESOURCE_NOT_FOUND` | Requested resource does not exist |
| 404 | `UNKNOWN_ENTITY_TYPE` | Entity type not supported for resolution |
| 422 | `UNPROCESSABLE_ENTITY` | Request body validation failed |
| 429 | `RATE_LIMITED` | Too many requests, retry after delay |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `SERVICE_UNAVAILABLE` | Service dependency unavailable (cache warming, bot PAT not configured) |

### Error Response Examples

**Missing authentication**:
```bash
$ curl https://api.example.com/api/v1/tasks/123
{
  "detail": {
    "error": "MISSING_AUTH",
    "message": "Authorization header required"
  }
}
```

**Resource not found**:
```bash
$ curl -H "Authorization: Bearer xoxp-..." \
  https://api.example.com/api/v1/tasks/999999999999999
{
  "detail": {
    "error": "RESOURCE_NOT_FOUND",
    "message": "Task with GID 999999999999999 not found"
  }
}
```

**Validation error**:
```bash
$ curl -X POST \
  -H "Authorization: Bearer xoxp-..." \
  -H "Content-Type: application/json" \
  -d '{"name": ""}' \
  https://api.example.com/api/v1/tasks
{
  "detail": {
    "error": "VALIDATION_ERROR",
    "message": "Task name cannot be empty"
  }
}
```

## Content Negotiation

DataFrame endpoints support multiple response formats via the `Accept` header.

### Supported Formats

- `application/json` (default): JSON array of records
- `application/x-polars-json`: Polars-serialized wire format

### JSON Format (Default)

```bash
curl -H "Authorization: Bearer xoxp-..." \
  -H "Accept: application/json" \
  https://api.example.com/api/v1/dataframes/project/1234567890123456?schema=unit
```

Response:
```json
{
  "data": [
    {"gid": "123", "name": "Unit 1", "phone": "+15551234567"},
    {"gid": "456", "name": "Unit 2", "phone": "+15559876543"}
  ],
  "meta": {
    "request_id": "a1b2c3d4e5f67890",
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

### Polars Format

```bash
curl -H "Authorization: Bearer xoxp-..." \
  -H "Accept: application/x-polars-json" \
  https://api.example.com/api/v1/dataframes/project/1234567890123456?schema=unit
```

Returns Polars JSON-serialized DataFrame for efficient deserialization by Polars clients.

## Route Groups

### Health

**Base path**: `/health`
**Authentication**: None

Health and readiness probes for container orchestration.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness probe (always 200 if app is running) |
| `/health/ready` | GET | Readiness probe (503 during cache warming) |
| `/health/s2s` | GET | S2S connectivity check (JWKS + bot PAT) |

**Example**:
```bash
$ curl https://api.example.com/health
{
  "status": "healthy",
  "version": "0.1.0",
  "cache_ready": true
}
```

### Tasks

**Base path**: `/api/v1/tasks`
**Authentication**: PAT Bearer

Task CRUD operations and task membership management.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tasks` | GET | List tasks by project or section (paginated) |
| `/api/v1/tasks` | POST | Create a new task |
| `/api/v1/tasks/{gid}` | GET | Get task by GID |
| `/api/v1/tasks/{gid}` | PUT | Update task |
| `/api/v1/tasks/{gid}` | DELETE | Delete task |
| `/api/v1/tasks/{gid}/subtasks` | GET | List subtasks (paginated) |
| `/api/v1/tasks/{gid}/dependents` | GET | List dependent tasks (paginated) |
| `/api/v1/tasks/{gid}/duplicate` | POST | Duplicate task |
| `/api/v1/tasks/{gid}/tags` | POST | Add tag to task |
| `/api/v1/tasks/{gid}/tags/{tag_gid}` | DELETE | Remove tag from task |
| `/api/v1/tasks/{gid}/section` | POST | Move task to section |
| `/api/v1/tasks/{gid}/assignee` | PUT | Set task assignee |
| `/api/v1/tasks/{gid}/projects` | POST | Add task to project |
| `/api/v1/tasks/{gid}/projects/{project_gid}` | DELETE | Remove task from project |

**Example: Get task**:
```bash
$ curl -H "Authorization: Bearer xoxp-..." \
  "https://api.example.com/api/v1/tasks/1234567890123456?opt_fields=name,notes,due_on,assignee"
{
  "data": {
    "gid": "1234567890123456",
    "name": "Fix authentication bug",
    "notes": "Users report 401 errors on login",
    "due_on": "2026-02-15",
    "assignee": {
      "gid": "9876543210987654",
      "name": "Jane Developer"
    }
  },
  "meta": {
    "request_id": "a1b2c3d4e5f67890",
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

**Example: Create task**:
```bash
$ curl -X POST \
  -H "Authorization: Bearer xoxp-..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Review API documentation",
    "notes": "Check for accuracy and completeness",
    "projects": ["1234567890123456"],
    "due_on": "2026-02-20"
  }' \
  https://api.example.com/api/v1/tasks
{
  "data": {
    "gid": "1111111111111111",
    "name": "Review API documentation",
    "notes": "Check for accuracy and completeness",
    "due_on": "2026-02-20"
  },
  "meta": {
    "request_id": "b2c3d4e5f6a78901",
    "timestamp": "2026-02-12T10:35:00Z"
  }
}
```

### Projects

**Base path**: `/api/v1/projects`
**Authentication**: PAT Bearer

Project management operations.

### Sections

**Base path**: `/api/v1/sections`
**Authentication**: PAT Bearer

Section management within projects.

### Users

**Base path**: `/api/v1/users`
**Authentication**: PAT Bearer

User information and workspace membership.

### Workspaces

**Base path**: `/api/v1/workspaces`
**Authentication**: PAT Bearer

Workspace information and project listings.

### DataFrames

**Base path**: `/api/v1/dataframes`
**Authentication**: PAT Bearer

Tabular data access for tasks with schema-based transformations.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/dataframes/project/{gid}` | GET | Project tasks as DataFrame |
| `/api/v1/dataframes/section/{gid}` | GET | Section tasks as DataFrame |

**Query parameters**:
- `schema`: Schema name (base, unit, contact, business, offer, asset_edit, asset_edit_holder)
- `limit`: Page size (1-100, default 100)
- `offset`: Pagination cursor

**Example**:
```bash
$ curl -H "Authorization: Bearer xoxp-..." \
  -H "Accept: application/json" \
  "https://api.example.com/api/v1/dataframes/project/1234567890123456?schema=unit&limit=50"
{
  "data": [
    {
      "gid": "123",
      "name": "Dental Office - Main St",
      "phone": "+15551234567",
      "vertical": "dental"
    },
    {
      "gid": "456",
      "name": "Medical Clinic - Oak Ave",
      "phone": "+15559876543",
      "vertical": "medical"
    }
  ],
  "meta": {
    "request_id": "c3d4e5f6a7b89012",
    "timestamp": "2026-02-12T10:40:00Z"
  }
}
```

### Entity Write

**Base path**: `/api/v1/entity`
**Authentication**: S2S JWT

Field write operations for entity custom fields.

### Resolver

**Base path**: `/v1/resolve`
**Authentication**: S2S JWT

Entity resolution from business identifiers to task GIDs.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/resolve/{entity_type}` | POST | Resolve criteria to task GIDs |
| `/v1/resolve/{entity_type}/schema` | GET | Get resolution schema for entity type |

**Supported entity types**: unit, business, offer, contact

**Example: Resolve units**:
```bash
$ curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"phone": "+15551234567", "vertical": "dental"},
      {"phone": "+15559876543", "vertical": "medical"}
    ]
  }' \
  https://api.example.com/v1/resolve/unit
{
  "results": [
    {"gid": "1234567890123456", "match_count": 1},
    {"gid": "1234567890123457", "match_count": 1}
  ],
  "meta": {
    "resolved_count": 2,
    "unresolved_count": 0,
    "entity_type": "unit",
    "project_gid": "1201081073731555",
    "available_fields": ["gid", "name", "phone", "vertical"],
    "criteria_schema": ["phone", "vertical"]
  }
}
```

**Example: Get resolution schema**:
```bash
$ curl -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  https://api.example.com/v1/resolve/unit/schema
{
  "entity_type": "unit",
  "required_fields": ["phone", "vertical"],
  "optional_fields": [],
  "available_output_fields": ["gid", "name", "phone", "vertical", "parent_gid"]
}
```

### Query

**Base path**: `/v1/query`
**Authentication**: S2S JWT

Entity querying operations.

### Admin

**Base path**: `/v1/admin`
**Authentication**: S2S JWT

Cache management and administrative operations.

### Webhooks

**Base path**: `/api/v1/webhooks`
**Authentication**: Token-based

Inbound webhook event handling from Asana.

## Request Tracing

All requests receive a unique request ID for distributed tracing.

### Request ID Header

Send `X-Request-ID` header to correlate requests across services:

```bash
curl -H "Authorization: Bearer xoxp-..." \
  -H "X-Request-ID: my-trace-id-12345" \
  https://api.example.com/api/v1/tasks/1234567890123456
```

If not provided, the service generates a 16-character hex ID automatically.

### Response Metadata

Every response includes the request ID in the `meta` field:

```json
{
  "data": {...},
  "meta": {
    "request_id": "my-trace-id-12345",
    "timestamp": "2026-02-12T10:30:00Z"
  }
}
```

Use this ID when reporting errors or investigating issues.

## OpenAPI Specification

The complete OpenAPI specification is auto-generated from FastAPI route decorators and available at:

- `GET /docs` (Swagger UI, debug mode only)
- `GET /redoc` (ReDoc UI, debug mode only)
- `docs/api-reference/openapi.yaml` (static export)

The OpenAPI spec includes:
- All endpoint paths and HTTP methods
- Request/response schemas
- Authentication requirements
- Query parameters and path variables
- Example requests and responses

## Rate Limiting

The API applies service-level rate limiting to protect service availability.

Rate limits are applied per client IP address. When exceeded, the service returns HTTP 429 with a `Retry-After` header indicating seconds to wait.

**Example**:
```bash
$ curl -H "Authorization: Bearer xoxp-..." \
  https://api.example.com/api/v1/tasks/1234567890123456
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "detail": "Rate limit exceeded"
}
```

Wait for the `Retry-After` duration before retrying.

## Debugging

### Enable Verbose Logging

Set `DEBUG=true` environment variable to enable:
- Interactive API documentation at `/docs` and `/redoc`
- Verbose request/response logging
- Stack traces in error responses (development only)

### Common Issues

**401 MISSING_AUTH**: Missing Authorization header. Add `-H "Authorization: Bearer <token>"`.

**401 SERVICE_TOKEN_REQUIRED**: PAT provided for S2S endpoint. Use JWT for `/v1/*` routes.

**503 during startup**: Cache warming in progress. Check `/health/ready` for readiness status.

**404 UNKNOWN_ENTITY_TYPE**: Entity type not supported. Check `/v1/resolve/{entity_type}/schema` for supported types.

**422 VALIDATION_ERROR**: Request body validation failed. Check error details for specific field errors.
