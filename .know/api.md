---
domain: api
generated_at: "2026-04-01T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "24d8e44"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase API Surface

## Route Inventory

This service exposes **57 route handler functions** across 19 routers, grouped into two URL namespaces:

- `/api/v1/*` — PAT-authenticated public endpoints (user-facing)
- `/v1/*` — S2S JWT-authenticated internal endpoints (service-to-service)

Route router definitions are in `src/autom8_asana/api/routes/`.

### Health (no auth)

Router: plain `APIRouter`, no prefix, tag `health`
Handler file: `src/autom8_asana/api/routes/health.py`

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/health` | `health_check` | Liveness -- always 200, no I/O |
| GET | `/ready` | `readiness_check` | Readiness -- 503 while cache warms |
| GET | `/health/deps` | `deps_check` | Checks JWKS reachability + ASANA_PAT presence |

### Tasks -- PAT Bearer

Router: `pat_router(prefix="/api/v1/tasks", tags=["tasks"])`
Handler file: `src/autom8_asana/api/routes/tasks.py`

| Method | Path | Response Model |
|--------|------|----------------|
| GET | `/api/v1/tasks` | `SuccessResponse[list[AsanaResource]]` |
| GET | `/api/v1/tasks/{gid}` | `SuccessResponse[AsanaResource]` |
| POST | `/api/v1/tasks` | `SuccessResponse[AsanaResource]` (201) |
| PUT | `/api/v1/tasks/{gid}` | `SuccessResponse[AsanaResource]` |
| DELETE | `/api/v1/tasks/{gid}` | 204 No Content |
| GET | `/api/v1/tasks/{gid}/subtasks` | `SuccessResponse[list[AsanaResource]]` |
| GET | `/api/v1/tasks/{gid}/dependents` | `SuccessResponse[list[AsanaResource]]` |
| POST | `/api/v1/tasks/{gid}/duplicate` | `SuccessResponse[AsanaResource]` (201) |
| POST | `/api/v1/tasks/{gid}/tags` | `SuccessResponse[AsanaResource]` |
| DELETE | `/api/v1/tasks/{gid}/tags/{tag_gid}` | `SuccessResponse[AsanaResource]` |
| POST | `/api/v1/tasks/{gid}/section` | `SuccessResponse[AsanaResource]` |
| PUT | `/api/v1/tasks/{gid}/assignee` | `SuccessResponse[AsanaResource]` |
| POST | `/api/v1/tasks/{gid}/projects` | `SuccessResponse[AsanaResource]` |
| DELETE | `/api/v1/tasks/{gid}/projects/{project_gid}` | `SuccessResponse[AsanaResource]` |

### Projects -- PAT Bearer

Router: `pat_router(prefix="/api/v1/projects", tags=["projects"])`
Handler file: `src/autom8_asana/api/routes/projects.py`

| Method | Path | Response Model |
|--------|------|----------------|
| GET | `/api/v1/projects` | `SuccessResponse[list[AsanaResource]]` |
| GET | `/api/v1/projects/{gid}` | `SuccessResponse[AsanaResource]` |
| POST | `/api/v1/projects` | `SuccessResponse[AsanaResource]` (201) |
| PUT | `/api/v1/projects/{gid}` | `SuccessResponse[AsanaResource]` |
| DELETE | `/api/v1/projects/{gid}` | 204 No Content |
| GET | `/api/v1/projects/{gid}/sections` | `SuccessResponse[list[AsanaResource]]` |
| POST | `/api/v1/projects/{gid}/members` | `SuccessResponse[AsanaResource]` |
| DELETE | `/api/v1/projects/{gid}/members` | `SuccessResponse[AsanaResource]` |

### Sections -- PAT Bearer

Router: `pat_router(prefix="/api/v1/sections", tags=["sections"])`
Handler file: `src/autom8_asana/api/routes/sections.py`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/sections/{gid}` | Get section by GID |
| POST | `/api/v1/sections` | Create section |
| PUT | `/api/v1/sections/{gid}` | Update section |
| DELETE | `/api/v1/sections/{gid}` | Delete section |
| POST | `/api/v1/sections/{gid}/tasks` | Add task to section |
| POST | `/api/v1/sections/{gid}/reorder` | Reorder section within project |

### Users -- PAT Bearer

Router: `pat_router(prefix="/api/v1/users", tags=["users"])`
Handler file: `src/autom8_asana/api/routes/users.py`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/users/me` | Get authenticated user |
| GET | `/api/v1/users/{gid}` | Get user by GID |
| GET | `/api/v1/users` | List users in workspace |

### Workspaces -- PAT Bearer

Router: `pat_router(prefix="/api/v1/workspaces", tags=["workspaces"])`
Handler file: `src/autom8_asana/api/routes/workspaces.py`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/workspaces` | List all workspaces |
| GET | `/api/v1/workspaces/{gid}` | Get workspace by GID |

### DataFrames -- PAT Bearer

Router: `pat_router(prefix="/api/v1/dataframes", tags=["dataframes"])`
Handler file: `src/autom8_asana/api/routes/dataframes.py`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/dataframes/schemas` | List available schemas |
| GET | `/api/v1/dataframes/{schema}/columns` | Get schema column definitions |
| GET | `/api/v1/dataframes/{schema}` | Fetch DataFrame for schema |
| GET | `/api/v1/dataframes/{schema}/export` | Export DataFrame (Polars-serialized) |

### Section Timelines / Offers -- PAT Bearer

Router: `pat_router(prefix="/api/v1/offers", tags=["offers"])`
Handler file: `src/autom8_asana/api/routes/section_timelines.py`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/offers` | Offer activity timeline reporting |

### Workflows -- PAT Bearer

Router: `pat_router(prefix="/api/v1/workflows", tags=["workflows"])`
Handler file: `src/autom8_asana/api/routes/workflows.py`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/workflows` | List registered workflows |
| POST | `/api/v1/workflows/{workflow_id}/invoke` | Invoke a workflow (rate-limited: 10/min) |

### Webhooks -- URL Token

Router: `APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])`
Handler file: `src/autom8_asana/api/routes/webhooks.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/webhooks/inbound?token=<secret>` | Inbound Asana task notification |

### Resolver -- S2S JWT (in spec)

Router: `s2s_router(prefix="/v1/resolve", tags=["resolver"], include_in_schema=True)`
Handler file: `src/autom8_asana/api/routes/resolver.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/resolve/{entity_type}` | Batch GID resolution by business identifiers |

### Query -- S2S JWT (mixed spec visibility)

Introspection router: `s2s_router(prefix="/v1/query", tags=["query"], include_in_schema=True)`
Execution router: `s2s_router(prefix="/v1/query", tags=["query"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/query.py`

| Method | Path | In Spec | Notes |
|--------|------|---------|-------|
| GET | `/v1/query/entities` | Yes | List queryable entity types |
| GET | `/v1/query/{entity_type}/fields` | Yes | List entity fields |
| GET | `/v1/query/{entity_type}/relations` | Yes | List joinable entities |
| POST | `/v1/query/{entity_type}/rows` | No | Filtered row retrieval |
| POST | `/v1/query/{entity_type}/aggregate` | No | Aggregate with grouping |
| POST | `/v1/query/{entity_type}` | No | Legacy query (deprecated, sunset 2026-06-01) |

### Intake Resolve -- S2S JWT (hidden from spec)

Router: `s2s_router(prefix="/v1", tags=["intake-resolve"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/intake_resolve.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/resolve/business` | Resolve business by phone/vertical |
| POST | `/v1/resolve/contact` | Resolve contact by email/phone within business scope |

**Note**: These two paths must be registered before `/v1/resolve/{entity_type}` (the resolver wildcard) to avoid path conflicts.

### Intake Create -- S2S JWT (hidden from spec)

Router: `s2s_router(prefix="/v1/intake", tags=["intake-create"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/intake_create.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/intake/business` | Create full business hierarchy (7-phase SaveSession) |
| POST | `/v1/intake/route` | Route unit to process type |

### Intake Custom Fields -- S2S JWT (hidden from spec)

Router: `s2s_router(prefix="/v1/tasks", tags=["intake-custom-fields"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/intake_custom_fields.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/tasks/{gid}/custom-fields` | Write custom fields on task |

### Entity Write -- S2S JWT (hidden from spec)

Router: `s2s_router(prefix="/api/v1/entity", tags=["entity-write"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/entity_write.py`

| Method | Path | Notes |
|--------|------|-------|
| PATCH | `/api/v1/entity/{entity_type}/{gid}` | Write typed fields to entity |

### Admin -- S2S JWT (hidden from spec)

Router: `s2s_router(prefix="/v1/admin", tags=["admin"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/admin.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/admin/cache/refresh` | Manual cache invalidation and rebuild (202 Accepted) |

### Matching -- S2S JWT (hidden from spec)

Router: `s2s_router(prefix="/v1/matching", tags=["matching"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/matching.py`

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/matching/query` | Matching query for scored business candidates |

### Internal -- S2S JWT (hidden from spec)

Router: `s2s_router(prefix="/api/v1/internal", tags=["internal"], include_in_schema=False)`
Handler file: `src/autom8_asana/api/routes/internal.py`

Acts primarily as a dependency provider (`ServiceClaims`, `require_service_claims`) used by other S2S routers.

### Route Versioning Pattern

Two parallel namespaces exist:
- `/api/v1/` -- public user-facing (PAT auth)
- `/v1/` -- internal service-facing (S2S JWT auth)

There is no v2 yet. No version negotiation via headers.

## Authentication & Authorization Model

### Auth Scheme Overview

Three security schemes are defined and injected into the OpenAPI spec by `custom_openapi()` in `src/autom8_asana/api/main.py`:

| Scheme | OAS Name | Type | Routes |
|--------|----------|------|--------|
| Asana PAT | `PersonalAccessToken` | HTTP Bearer | `/api/v1/*` (PAT tags) |
| Service JWT | `ServiceJWT` | HTTP Bearer (JWT) | `/v1/*` and some `/api/v1/entity`, `/api/v1/internal` |
| Webhook Token | `WebhookToken` | API Key (query param `?token=`) | `/api/v1/webhooks/*` |

### Dual-Mode Detection

Every authenticated request passes through `get_auth_context()` in `src/autom8_asana/api/dependencies.py`. The dispatcher in `src/autom8_asana/auth/dual_mode.py` detects token type by dot-counting:

- Token with exactly 2 dots -> `AuthMode.JWT` (S2S)
- Token with 0 dots -> `AuthMode.PAT` (user pass-through)

### PAT Pass-Through (AuthMode.PAT)

The user's Asana PAT is passed **directly** to the Asana SDK. The token is never logged (structlog filter in `src/autom8_asana/api/middleware/core.py` redacts fields matching `authorization`, `token`, `pat`, `password`, `secret`).

### S2S JWT Validation (AuthMode.JWT)

For JWT tokens:
1. `validate_service_token()` in `src/autom8_asana/auth/jwt_validator.py` delegates to `autom8y_auth.AuthClient`
2. JWKS endpoint: `https://auth.api.autom8y.io/.well-known/jwks.json` (configurable via `AUTH_JWKS_URL`)
3. JWKS caching: 5-minute TTL, managed by SDK (stale cache fallback enabled)
4. On success: `ServiceClaims` returned with `service_name` and `scope`
5. Bot PAT is then fetched from `ASANA_PAT` env var via `src/autom8_asana/auth/bot_pat.py`

### Auth Error Propagation

| Error | HTTP Status |
|-------|-------------|
| Missing Authorization header | 401 MISSING_AUTH |
| Non-Bearer scheme | 401 INVALID_SCHEME |
| JWT signature/expiry failure | 401 (from `PermanentAuthError`) |
| JWKS unreachable | 503 (from `TransientAuthError` or `CircuitOpenError`) |
| Bot PAT not configured | 503 S2S_NOT_CONFIGURED |

### Route-Level Auth Classification

The `custom_openapi()` function defines four tag sets for OpenAPI annotation:

- `_PAT_TAGS`: `tasks`, `projects`, `sections`, `users`, `workspaces`, `dataframes`, `offers`, `workflows`
- `_TOKEN_TAGS`: `webhooks`
- `_S2S_TAGS`: `resolver`, `query`, `admin`, `internal`, `entity-write`, `intake-resolve`, `intake-custom-fields`, `intake-create`, `matching`
- `_NO_AUTH_TAGS`: `health`

### Webhook Auth

`POST /api/v1/webhooks/inbound` uses URL query token auth (`?token=<secret>`). Timing-safe comparison via `hmac.compare_digest` against `ASANA_WEBHOOK_INBOUND_TOKEN` env var.

## Request/Response Contracts

### Response Envelope

All success responses use the fleet-standard envelope from `autom8y_api_schemas`:

```json
{
  "data": "<payload>",
  "meta": {
    "request_id": "abc123def456789a",
    "timestamp": "2026-04-01T00:00:00Z"
  }
}
```

Paginated list responses include `pagination` key in `meta` with `limit`, `has_more`, `next_offset`.

The `SuccessResponse[T]` and `build_success_response()` types are imported from `autom8y_api_schemas` and re-exported from `src/autom8_asana/api/models.py`.

### Error Response Envelope

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "..."
  },
  "meta": {
    "request_id": "..."
  }
}
```

### Standard HTTP Error Status Codes

| Status | Code | Trigger |
|--------|------|---------|
| 400 | `VALIDATION_ERROR` | GidValidationError |
| 401 | `INVALID_CREDENTIALS` / `MISSING_AUTH` | AuthenticationError |
| 403 | `FORBIDDEN` | ForbiddenError |
| 404 | `RESOURCE_NOT_FOUND` | NotFoundError |
| 422 | (FastAPI default) | Pydantic validation failure |
| 429 | `RATE_LIMITED` | RateLimitError; includes `Retry-After` header |
| 500 | `INTERNAL_ERROR` | Catch-all |
| 502 | `UPSTREAM_ERROR` | Asana ServerError or httpx RequestError |
| 503 | `S2S_NOT_CONFIGURED` | Bot PAT missing, auth circuit open |
| 504 | `UPSTREAM_TIMEOUT` | TimeoutError |

### Pagination Model

Cursor-based pagination: `?limit=<int>&offset=<cursor_string>`. Default limit: 100, max limit: 100.

### Content Types

Default: `application/json`. DataFrames export: Polars-serialized binary when requested via `Accept` header.

### Idempotency

RFC 8791 idempotency via `IdempotencyMiddleware` in `src/autom8_asana/api/middleware/idempotency.py`. Backend: `dynamodb` (default), `memory`, or `noop`.

## Cross-Service Dependencies

### Outbound: Asana API

All routes (except health and webhooks) make outbound calls to the Asana REST API via `AsanaClient`. Client lifecycle is per-request, pooled via `ClientPool` on `app.state`.

### Outbound: autom8y-data Service

`src/autom8_asana/clients/data/client.py` -- `DataServiceClient` for cross-service joins and DataFrame enrichment.

- Base URL: `AUTOM8Y_DATA_URL` env var (default `http://localhost:8000`)
- Auth: `AUTOM8Y_DATA_API_KEY` or `ServiceTokenAuthProvider`
- Retry: 2 retries with exponential backoff, retries 429/502/503/504
- Circuit breaker: 5 failures in 60s opens circuit, 30s recovery timeout

### Outbound: autom8y-auth JWKS

`src/autom8_asana/auth/jwt_validator.py` uses `autom8y_auth.AuthClient` which fetches JWKS from `https://auth.api.autom8y.io/.well-known/jwks.json`.

### Inbound: Asana Rules Webhooks

`POST /api/v1/webhooks/inbound` receives full task JSON payloads from Asana Rules actions.

### Service Dependency Map

```
External Caller (PAT)  -> autom8y-asana API
Internal Service (S2S JWT) -> autom8y-asana API
Asana Rules -> POST /api/v1/webhooks/inbound

autom8y-asana API -> Asana REST API (per-request, SDK)
autom8y-asana API -> autom8y-data satellite (DataServiceClient)
autom8y-asana API -> autom8y-auth JWKS endpoint (JWT validation)
```

## Spec Completeness & Freshness

### No Committed OpenAPI Spec in Main Branch

There is no `docs/api-reference/openapi.yaml` in the main working tree. The spec is generated at runtime by `custom_openapi()` in `src/autom8_asana/api/main.py`.

### Spec Generation Mechanism

Runtime-generated via FastAPI's `get_openapi()` with post-processing to inject security schemes, tag descriptions, and OAS 3.2.0 metadata. Cached on `app.openapi_schema` after first call.

### Spec Authority

The runtime-generated spec is the **source of truth**. Routes with `include_in_schema=False` are hidden from the generated spec but present in the live router.

### Spec vs. Code Route Count

Routes in spec: ~35-38 (PAT endpoints + resolver + query introspection + webhooks)
Routes in code: 57 handler functions across 19 routers
Delta: ~19-22 routes intentionally hidden (S2S internal routes)

## Knowledge Gaps

1. **Route handler bodies for sections, users, workspaces, workflows, dataframes** -- exact request/response schema models not individually read.
2. **`internal.py` endpoint listing** -- identified as dependency provider; actual handler definitions not read.
3. **`resolver_schema.py`** -- a separate `schema_router` is defined but not imported in `__init__.py`. Mount status unclear.
4. **`DataServiceClient` endpoint URL paths** -- target URL paths inside `_endpoints/` not extracted.
5. **Idempotency middleware covered operations** -- which HTTP methods/paths it applies to not verified.
