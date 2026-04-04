---
domain: api
generated_at: "2026-04-04T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./docs/api-reference/openapi.json"
  - "./pyproject.toml"
generator: theoros
source_hash: "55aaab5"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase API Surface

## Route Inventory

**Framework**: FastAPI (Python 3.12), optional extra `[api]` activates the service. Application factory at `src/autom8_asana/api/main.py`, routes aggregated in `src/autom8_asana/api/routes/__init__.py`.

**Base URLs** (injected in custom OpenAPI):
- Production: `https://asana.api.autom8y.io`
- Staging: `https://asana.staging.api.autom8y.io`

The API uses two URL namespace prefixes:
- `/api/v1/*` — PAT-authenticated resource endpoints (public-facing)
- `/v1/*` — S2S JWT-only endpoints (internal service-to-service)

### Health Routes (`src/autom8_asana/api/routes/health.py`)

Auth tag: `health` (no auth required)

| Method | Path | Summary |
|--------|------|---------|
| GET | `/health` | Liveness probe — always 200, no I/O |
| GET | `/ready` | Readiness probe — 200 when cache warm, 503 while preloading |
| GET | `/health/deps` | Dependency probe — checks JWKS reachability and bot PAT config |

### Tasks Routes (`src/autom8_asana/api/routes/tasks.py`)

Router prefix: `/api/v1/tasks`, auth: PAT Bearer

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/tasks` | List tasks by project or section (cursor pagination) |
| GET | `/api/v1/tasks/{gid}` | Get task by GID |
| POST | `/api/v1/tasks` | Create task (201) |
| PUT | `/api/v1/tasks/{gid}` | Update task (partial) |
| DELETE | `/api/v1/tasks/{gid}` | Delete task (204) |
| GET | `/api/v1/tasks/{gid}/subtasks` | List direct subtasks (cursor pagination) |
| GET | `/api/v1/tasks/{gid}/dependents` | List dependent tasks (cursor pagination) |
| POST | `/api/v1/tasks/{gid}/duplicate` | Duplicate task (201) |
| POST | `/api/v1/tasks/{gid}/tags` | Add tag to task |
| DELETE | `/api/v1/tasks/{gid}/tags/{tag_gid}` | Remove tag from task |
| POST | `/api/v1/tasks/{gid}/section` | Move task to section |
| PUT | `/api/v1/tasks/{gid}/assignee` | Set or clear task assignee |
| POST | `/api/v1/tasks/{gid}/projects` | Add task to project |
| DELETE | `/api/v1/tasks/{gid}/projects/{project_gid}` | Remove task from project |

### Projects Routes (`src/autom8_asana/api/routes/projects.py`)

Router prefix: `/api/v1/projects`, auth: PAT Bearer

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/projects` | List projects in workspace (cursor pagination) |
| GET | `/api/v1/projects/{gid}` | Get project by GID |
| POST | `/api/v1/projects` | Create project (201) |
| PUT | `/api/v1/projects/{gid}` | Update project |
| DELETE | `/api/v1/projects/{gid}` | Delete project (204) |
| GET | `/api/v1/projects/{gid}/sections` | List project sections |
| POST | `/api/v1/projects/{gid}/members` | Add members to project |
| DELETE | `/api/v1/projects/{gid}/members` | Remove members from project |

### Sections Routes (`src/autom8_asana/api/routes/sections.py`)

Router prefix: `/api/v1/sections`, auth: PAT Bearer

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/sections/{gid}` | Get section by GID |
| POST | `/api/v1/sections` | Create section |
| PUT | `/api/v1/sections/{gid}` | Update section |
| DELETE | `/api/v1/sections/{gid}` | Delete section (204) |
| POST | `/api/v1/sections/{gid}/addTask` | Add task to section |
| POST | `/api/v1/sections/{gid}/reorder` | Reorder section within project |

### Users Routes (`src/autom8_asana/api/routes/users.py`)

Router prefix: `/api/v1/users`, auth: PAT Bearer

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/users/me` | Get current authenticated user |
| GET | `/api/v1/users/{gid}` | Get user by GID |
| GET | `/api/v1/users` | List users in workspace |

### Workspaces Routes (`src/autom8_asana/api/routes/workspaces.py`)

Router prefix: `/api/v1/workspaces`, auth: PAT Bearer

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/workspaces` | List accessible workspaces |
| GET | `/api/v1/workspaces/{gid}` | Get workspace by GID |

### DataFrames Routes (`src/autom8_asana/api/routes/dataframes.py`)

Router prefix: `/api/v1/dataframes`, auth: PAT Bearer

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/dataframes/schemas` | List all dataframe schemas |
| GET | `/api/v1/dataframes/schemas/{name}` | Get single schema details |
| GET | `/api/v1/dataframes/project/{gid}` | Project tasks as dataframe |
| GET | `/api/v1/dataframes/section/{gid}` | Section tasks as dataframe |

Content negotiation via `Accept` header: `application/json` (default) or `application/x-polars-json`.

### Offers / Section Timelines (`src/autom8_asana/api/routes/section_timelines.py`)

Router prefix: `/api/v1/offers`, auth: PAT Bearer

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/offers/section-timelines` | Get section timelines for all offers (query params: period_start, period_end, classification) |

### Workflows Routes (`src/autom8_asana/api/routes/workflows.py`)

Router prefix: `/api/v1/workflows`, auth: PAT Bearer. Rate limited: 10 requests/minute.

| Method | Path | Summary |
|--------|------|---------|
| GET | `/api/v1/workflows` | List available workflow IDs |
| POST | `/api/v1/workflows/{workflow_id}/invoke` | Invoke workflow against entities (120s timeout) |

### Webhooks Routes (`src/autom8_asana/api/routes/webhooks.py`)

Router prefix: `/api/v1/webhooks`, auth: URL token (`?token=<secret>`)

| Method | Path | Summary |
|--------|------|---------|
| POST | `/api/v1/webhooks/inbound` | Receive Asana Rules task notification (returns 200 immediately, background processing) |

### Resolver Routes (`src/autom8_asana/api/routes/resolver.py`)

Router prefix: `/v1/resolve`, auth: S2S JWT. Visible in schema.

| Method | Path | Summary |
|--------|------|---------|
| POST | `/v1/resolve/{entity_type}` | Batch resolve business identifiers to Asana GIDs |
| GET | `/v1/resolve/{entity_type}/schema` | Schema discovery (via `resolver_schema.py` sub-router) |

### Query Introspection Routes (`src/autom8_asana/api/routes/query.py`)

Router: `query_introspection_router`, prefix `/v1/query`, auth: S2S JWT. Visible in schema.

| Method | Path | Summary |
|--------|------|---------|
| GET | `/v1/query/entities` | List queryable entity types |
| GET | `/v1/query/data-sources` | List data-service factories |
| GET | `/v1/query/data-sources/{factory}/fields` | List fields for a data-service factory |
| GET | `/v1/query/{entity_type}/fields` | List fields for an entity type |
| GET | `/v1/query/{entity_type}/relations` | List joinable entity types |
| GET | `/v1/query/{entity_type}/sections` | List sections and classifications |

### Query Execution Routes (`src/autom8_asana/api/routes/query.py`)

Router: `query_router`, prefix `/v1/query`, auth: S2S JWT. Hidden from schema (`include_in_schema=False`).

| Method | Path | Summary |
|--------|------|---------|
| POST | `/v1/query/{entity_type}/rows` | Filtered row retrieval with composable predicates |
| POST | `/v1/query/{entity_type}/aggregate` | Aggregate entity data with grouping |
| POST | `/v1/query/{entity_type}` | **DEPRECATED** (sunset 2026-06-01) — flat equality query. Returns `Deprecation: true`, `Sunset: 2026-06-01`, `Link: </v1/query/{entity_type}/rows>; rel="successor-version"` headers. |

### Admin Routes (`src/autom8_asana/api/routes/admin.py`)

Router prefix: `/v1/admin`, auth: S2S JWT. Hidden from schema.

| Method | Path | Summary |
|--------|------|---------|
| POST | `/v1/admin/cache/refresh` | Trigger cache refresh (202 Accepted, background task) |

### Internal Routes (`src/autom8_asana/api/routes/internal.py`)

Router prefix: `/api/v1/internal`, auth: S2S JWT. Hidden from schema. No route handlers defined here — the file provides shared `require_service_claims` dependency and `ServiceClaims` model used by other S2S routers.

### Entity Write Routes (`src/autom8_asana/api/routes/entity_write.py`)

Router prefix: `/api/v1/entity`, auth: S2S JWT. Hidden from schema.

| Method | Path | Summary |
|--------|------|---------|
| PATCH | `/api/v1/entity/{entity_type}/{gid}` | Write custom fields to an entity task |

### Intake Resolve Routes (`src/autom8_asana/api/routes/intake_resolve.py`)

Router prefix: `/v1`, auth: S2S JWT. Hidden from schema. **Route ordering matters**: these explicit paths are registered before the wildcard `/v1/resolve/{entity_type}`.

| Method | Path | Summary |
|--------|------|---------|
| POST | `/v1/resolve/business` | Resolve business by phone/vertical (GidLookupIndex O(1)) |
| POST | `/v1/resolve/contact` | Resolve contact by email/phone within business scope |

### Intake Create Routes (`src/autom8_asana/api/routes/intake_create.py`)

Router prefix: `/v1/intake`, auth: S2S JWT. Hidden from schema.

| Method | Path | Summary |
|--------|------|---------|
| POST | `/v1/intake/business` | Create full business hierarchy (7-phase SaveSession) |
| POST | `/v1/intake/route` | Route a unit to a process type |

### Intake Custom Fields Routes (`src/autom8_asana/api/routes/intake_custom_fields.py`)

Router prefix: `/v1/tasks`, auth: S2S JWT. Hidden from schema.

| Method | Path | Summary |
|--------|------|---------|
| POST | `/v1/tasks/{gid}/custom-fields` | Write custom fields to a task |

### Matching Routes (`src/autom8_asana/api/routes/matching.py`)

Router prefix: `/v1/matching`, auth: S2S JWT. Hidden from schema.

| Method | Path | Summary |
|--------|------|---------|
| POST | `/v1/matching/query` | Matching query for scored business candidates (reads cached DataFrame) |

**Total routes**: approximately 60 endpoints across 18 routers.

---

## Authentication & Authorization Model

The service implements a **dual-mode auth** system with three authentication schemes, classified by tag in the OpenAPI spec.

### Authentication Schemes

**1. PersonalAccessToken (PAT Bearer)**

Used by: `tasks`, `projects`, `sections`, `users`, `workspaces`, `dataframes`, `offers`, `workflows` tags.

- Token: Asana Personal Access Token (user-issued)
- Transport: `Authorization: Bearer <token>`
- Detection: `autom8_asana.auth.dual_mode.detect_token_type()` — distinguishes PAT from JWT by token structure
- Behavior: PAT is passed through directly to the Asana API. No platform auth validation.
- Client lifecycle: Per-request via token-keyed `ClientPool` (`src/autom8_asana/api/client_pool.py`). PAT-mode TTL in pool: 5 minutes.
- Code path: `src/autom8_asana/api/dependencies.py` -> `get_auth_context()` -> PAT branch returns `AuthContext(mode=PAT, asana_pat=token)`

**2. ServiceJWT (S2S JWT)**

Used by: `resolver`, `query`, `admin`, `internal`, `entity-write`, `intake-resolve`, `intake-custom-fields`, `intake-create`, `matching` tags.

- Token: JWT issued by `autom8y-auth` service
- Transport: `Authorization: Bearer <JWT>`
- Detection: `detect_token_type()` — JWT-mode path
- Validation: `autom8_asana.auth.jwt_validator.validate_service_token()` -> delegates entirely to `autom8y-auth` SDK `AuthClient.validate_service_token()`
- JWKS: Auto-fetched and cached (5-minute TTL, configurable via `AUTH__CACHE__TTL_SECONDS`) from `AUTH_JWKS_URL` env var (default: `https://auth.api.autom8y.io/.well-known/jwks.json`)
- Bot PAT injection: After JWT validation, the bot PAT (`ASANA_PAT` env var) replaces the JWT for downstream Asana API calls
- Client lifecycle: S2S mode TTL in pool: 1 hour
- Code path: `src/autom8_asana/api/dependencies.py` -> `get_auth_context()` -> JWT branch -> `validate_service_token()` -> `get_bot_pat()` -> `AuthContext(mode=JWT, asana_pat=bot_pat, caller_service=...)`
- Claims model: `src/autom8_asana/api/routes/internal.py:ServiceClaims` — `{sub, service_name, scope}`
- S2S-only enforcement: `require_service_claims()` dependency rejects PAT tokens with `401 SERVICE_TOKEN_REQUIRED`

**3. WebhookToken (URL query parameter)**

Used by: `webhooks` tag.

- Token: Secret string
- Transport: `?token=<secret>` query parameter
- Verification: `src/autom8_asana/api/routes/webhooks.py:verify_webhook_token()` — timing-safe `hmac.compare_digest()` against `ASANA_WEBHOOK_INBOUND_TOKEN` env var
- No JWT validation involved

**4. Health endpoints** — No authentication (tag: `health`)

### Security Primitives

- `src/autom8_asana/api/routes/_security.py` — `pat_router()` and `s2s_router()` factory functions using `autom8y_api_schemas.SecureRouter`. The `auto_error=False` setting means `SecureRouter` injects OpenAPI metadata only — runtime auth is handled by dependency injection (`get_auth_context`, `require_service_claims`).
- `src/autom8_asana/api/dependencies.py` — `_extract_bearer_token()` extracts and minimally validates Bearer token format; `get_auth_context()` is the primary auth dependency wiring dual-mode detection, JWT validation, and PAT injection.

### Error Handling for Auth

Handled by typed exceptions registered in `src/autom8_asana/api/errors.py`:
- `ApiAuthError` -> 401 with `WWW-Authenticate: Bearer` header
- `ApiServiceUnavailableError` -> 503 (JWKS unreachable, bot PAT missing, circuit breaker open)
- `AuthenticationError` (SDK) -> 401 INVALID_CREDENTIALS
- `ForbiddenError` (SDK) -> 403 FORBIDDEN

### Auth Dependencies Chain

```
Route handler
  -> AsanaClientDualMode (Depends(get_asana_client_from_context))
       -> AuthContextDep (Depends(get_auth_context))
            -> _extract_bearer_token (Depends)
                 -> Authorization header
```

For S2S routes, additionally:
```
claims: ServiceClaims (Depends(require_service_claims))
  -> validate_service_token(token)
       -> autom8y_auth.AuthClient
            -> JWKS endpoint
```

---

## Request/Response Contracts

### Envelope Format

All API responses use a **fleet-standard envelope** from `autom8y-api-schemas` package, imported/re-exported at `src/autom8_asana/api/models.py`:

**Success response:**
```json
{
  "data": "<response_payload>",
  "meta": {
    "request_id": "<16-char hex>",
    "timestamp": "<ISO-8601>"
  }
}
```

**Paginated success response** (list endpoints):
```json
{
  "data": ["..."],
  "meta": {
    "request_id": "...",
    "timestamp": "...",
    "pagination": {
      "limit": 100,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

**Error response:**
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "...",
    "details": {}
  },
  "meta": {
    "request_id": "..."
  }
}
```

Models: `SuccessResponse[T]` (generic), `ErrorResponse`, `ErrorDetail`, `ResponseMeta`, `PaginationMeta`.

### Core Shared Models

Located in `src/autom8_asana/api/models.py`:

- `AsanaResource` — Base resource: `{gid: str, resource_type: str|None, name: str|None}` with `extra="allow"` (accepts any additional Asana fields)

**Request models:**
- `CreateTaskRequest` — `{name, notes?, assignee?, projects?, due_on?, workspace?}`. At least `projects` or `workspace` required.
- `UpdateTaskRequest` — `{name?, notes?, completed?, due_on?}` (partial update)
- `AddTagRequest` — `{tag_gid}`
- `MoveSectionRequest` — `{section_gid, project_gid}`
- `SetAssigneeRequest` — `{assignee_gid?}` (null to unassign)
- `AddToProjectRequest` — `{project_gid}`
- `DuplicateTaskRequest` — `{name}`
- `CreateProjectRequest` — `{name, workspace, team?}`
- `UpdateProjectRequest` — `{name?, notes?, archived?}`
- `MembersRequest` — `{members: list[str]}`
- `CreateSectionRequest` — `{name, project}`
- `UpdateSectionRequest` — `{name}`
- `AddTaskToSectionRequest` — `{task_gid}`
- `ReorderSectionRequest` — `{project_gid, before_section?, after_section?}` (exactly one of before/after)

### Resolver Contract (`src/autom8_asana/api/routes/resolver_models.py`)

`ResolutionRequest`:
```json
{
  "criteria": [{"phone": "+15551234567", "vertical": "dental"}],
  "fields": ["gid", "name"],
  "active_only": false
}
```

`ResolutionResponse`:
```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["..."],
      "match_count": 1,
      "error": null,
      "data": ["..."],
      "status": ["..."],
      "total_match_count": 1
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 0,
    "entity_type": "unit",
    "project_gid": "...",
    "available_fields": ["gid", "name"],
    "criteria_schema": ["phone", "vertical"]
  }
}
```

### Query Contracts (`src/autom8_asana/query/models.py`)

`RowsRequest` — composable predicate filtering (where, select, section, classification, limit, offset, join). Used by `POST /v1/query/{entity_type}/rows`.

`AggregateRequest` — group_by, metrics, where (predicate), having (predicate), section, join. Used by `POST /v1/query/{entity_type}/aggregate`.

Legacy `QueryRequest` (deprecated) — flat `where: dict`, `select: list`, `limit`, `offset`.

### Intake Contracts

`BusinessResolveRequest` (`src/autom8_asana/api/routes/intake_resolve_models.py`):
- `{office_phone: str (E.164), vertical: str?}`

`BusinessResolveResponse`:
- `{found: bool, task_gid: str|None, ...}`

`ContactResolveRequest`:
- `{business_gid: str, email: str?, phone: str?}` (at least one of email/phone required)

`ContactResolveResponse`:
- `{found: bool, match_field: str|None, ...}`

`IntakeBusinessCreateRequest` / `IntakeBusinessCreateResponse` (from `src/autom8_asana/api/routes/intake_create_models.py`):
- Full business hierarchy creation (7-phase SaveSession). `is_new: bool` in response — idempotent.

### Matching Contract (`src/autom8_asana/api/routes/matching_models.py`)

`MatchingQueryRequest` — business identity fields for scored candidate matching. `MatchingQueryResponse` — list of scored candidate records.

### Entity Write Contract (`src/autom8_asana/api/routes/entity_write.py`)

`PATCH /api/v1/entity/{entity_type}/{gid}` — body contains fields to write as custom field GID-to-value map.

### Pagination

All list endpoints use cursor-based pagination: `limit` (1-100, default 100, max 100), `offset` (opaque cursor string from `meta.pagination.next_offset`). `meta.pagination.has_more` signals more pages.

### Error Codes (Standard)

Defined in `src/autom8_asana/api/errors.py`:

| SDK Exception | HTTP Status | Error Code |
|---|---|---|
| NotFoundError | 404 | RESOURCE_NOT_FOUND |
| AuthenticationError | 401 | INVALID_CREDENTIALS |
| ForbiddenError | 403 | FORBIDDEN |
| RateLimitError | 429 | RATE_LIMITED (+ Retry-After header) |
| GidValidationError | 400 | VALIDATION_ERROR |
| ServerError | 502 | UPSTREAM_ERROR |
| TimeoutError | 504 | UPSTREAM_TIMEOUT |
| RequestError | 502 | UPSTREAM_ERROR |
| AsanaError (generic) | 500 | INTERNAL_ERROR |

Domain-specific: `MISSING_AUTH`, `INVALID_SCHEME`, `SERVICE_TOKEN_REQUIRED`, `S2S_NOT_CONFIGURED`, `CACHE_NOT_WARMED`, `DISCOVERY_INCOMPLETE`, `UNKNOWN_ENTITY_TYPE`, `INVALID_PHONE_FORMAT`, `INDEX_NOT_READY`, `MISSING_CRITERIA`.

### OpenAPI Extension Annotations

Several routes carry fleet extension fields:
- `x-fleet-side-effects` — list of side effects (type: `asana_api`)
- `x-fleet-idempotency` — `{idempotent: bool, key_source: str|null}`
- `x-fleet-references` — `{service, entity}`
- `x-idempotent`, `x-safe` — annotated on query engine GET endpoints

### Idempotency Middleware

`IdempotencyMiddleware` (`src/autom8_asana/api/middleware/idempotency.py`) implements RFC 8791 store-and-replay. Stores: DynamoDB (default, table `autom8-idempotency-keys`, region `us-east-1`), in-memory, or noop. Configured via `IDEMPOTENCY_STORE_BACKEND` env var.

---

## Cross-Service Dependencies

### 1. Asana API (External)

All routes ultimately call the Asana REST API via `AsanaClient`. Client pool managed at `src/autom8_asana/api/client_pool.py`. Bot PAT from `ASANA_PAT` env var.

### 2. autom8y-auth (Platform Auth Service)

- **Dependency**: `autom8y-auth[observability]>=2.2.0` (optional extra `[auth]`)
- **What**: JWKS-backed JWT validation for all S2S JWT requests
- **Endpoint**: `AUTH_JWKS_URL` (default: `https://auth.api.autom8y.io/.well-known/jwks.json`)
- **Code**: `src/autom8_asana/auth/jwt_validator.py` — lazy-init `AuthClient` singleton
- **Failure mode**: `CircuitOpenError` -> 503; `TransientAuthError` -> 503; `PermanentAuthError` -> 401
- **Health probe**: `/health/deps` checks JWKS reachability

### 3. autom8y-data / DataServiceClient (Internal Service)

- **Dependency**: No pip package — calls `autom8_data` via HTTP
- **What**: Analytics insights API for cross-service query joins (workflow insights, payment reconciliation)
- **Contract**: `docs/contracts/openapi-data-service-client.yaml` — client-side spec
- **Endpoint**: `POST /api/v1/factory/{factory_name}` on `autom8_data`
- **Code**: `src/autom8_asana/clients/data/client.py` — `DataServiceClient` with circuit breaker, retry, cache fallback
- **Auth**: Bearer token (service JWT via `ServiceTokenAuthProvider` or API key `AUTOM8Y_DATA_API_KEY`)
- **Factories**: account, ads, adsets, campaigns, spend, leads, appts, assets, targeting, payments, business_offers, ad_questions, ad_tests, base
- **Used by**: Query engine joins (`src/autom8_asana/query/engine.py`, `join.py`), automation workflows (`insights/workflow.py`, `payment_reconciliation/workflow.py`)
- **Initialization**: Lazy singleton on `app.state` via `get_data_service_client()` in `dependencies.py`
- **Graceful degradation**: Returns `None` when unconfigured; query engine raises `JoinError` with clear message when join attempted without client

### 4. AWS S3 (Cache Storage)

- **Dependency**: `boto3>=1.42.19`
- **What**: Progressive DataFrame cache storage (parquet files, manifests, watermarks)
- **Code**: `src/autom8_asana/cache/backends/s3.py`
- **Used by**: `ProgressiveProjectBuilder`, `SectionPersistence`

### 5. AWS DynamoDB (Idempotency Store)

- **What**: RFC 8791 idempotency key store
- **Table**: `autom8-idempotency-keys` (configurable via `IDEMPOTENCY_TABLE_NAME`)
- **Region**: `us-east-1` (configurable via `IDEMPOTENCY_TABLE_REGION`)
- **Code**: `src/autom8_asana/api/middleware/idempotency.py`
- **Failure mode**: Falls back to `NoopIdempotencyStore` on connection error

### 6. AWS Lambda (Cache Warmer)

- **What**: Fire-and-forget Lambda invocation to rebuild DataFrame cache after force-refresh
- **Trigger**: `POST /v1/admin/cache/refresh` with `force_full_rebuild=true`
- **ARN**: `CACHE_WARMER_LAMBDA_ARN` env var (optional — degrades to "rebuild on restart" if unset)
- **Code**: `src/autom8_asana/api/routes/admin.py:_invoke_cache_warmer_lambda()`

### 7. autom8y-events / EventBridge (Lambda handlers only)

- **Dependency**: `autom8y-events>=0.1.0` (optional extra `[events]`)
- **What**: Domain event publishing for bridge dispatch
- **Used by**: Lambda handlers (`workflow_handler.py`, `insights_export.py`, `payment_reconciliation.py`, `conversation_audit.py`) — NOT the FastAPI routes themselves
- **Code**: `src/autom8_asana/lambda_handlers/`

### 8. Redis (Optional Cache Backend)

- **Dependency**: `redis>=5.0.0` (optional extra `[redis]`)
- **What**: Alternative cache backend for task/section data
- **Code**: `src/autom8_asana/cache/backends/redis.py`

---

## Spec Completeness & Freshness

### Available Spec Files

1. **`docs/api-reference/openapi.json`** — 229KB, 6597 lines. OpenAPI 3.2.0. Last committed 2026-04-02 (commit `322eb00`). This is the primary machine-readable spec.

2. **`docs/contracts/openapi-data-service-client.yaml`** — OpenAPI 3.1.0 client-side contract documenting what `autom8_asana` expects from `autom8_data`. Not an authoritative server spec (the server spec lives in `autom8_data`).

### What the Spec Covers

The `openapi.json` is auto-generated by FastAPI from the live route definitions and post-processed by `custom_openapi()` in `src/autom8_asana/api/main.py`:

- **Included** (tag has `include_in_schema=True` or no override): health, tasks, projects, sections, users, workspaces, dataframes, offers, workflows, resolver, query introspection endpoints
- **Excluded** (`include_in_schema=False`): admin, internal, entity-write, intake-resolve, intake-create, intake-custom-fields, matching, query execution (rows/aggregate)

The spec has been enriched with:
- `components.securitySchemes`: `PersonalAccessToken`, `ServiceJWT`, `WebhookToken`
- Per-operation security annotations from tag classification sets (`_PAT_TAGS`, `_S2S_TAGS`, `_TOKEN_TAGS`, `_NO_AUTH_TAGS`)
- `servers` block with production and staging URLs
- `tags` descriptions (14 tags documented)
- `webhooks.asanaTaskChanged` definition (OpenAPI 3.1+ webhook object)
- `x-query-method-candidates` extension documenting POST-as-QUERY endpoints
- Fleet registry types (`SuccessResponse`, `ErrorResponse`, `ErrorDetail`) injected into `components.schemas`
- `Task` model schema injected for webhook payload documentation

### Spec Freshness Assessment

The spec was last regenerated on 2026-04-02, two days before the audit date (2026-04-04). The most recent commits include route additions and type fixes — the spec appears to track source code changes actively. A `openapi-spec-validator>=0.7.1` dev dependency suggests automated validation in CI.

### Notable Gaps in Spec Coverage

- **~30 S2S endpoints are absent**: All `include_in_schema=False` routes (admin, entity-write, intake-*, matching, query execution) have no OpenAPI documentation. These are intentionally hidden but create a documentation gap for internal service consumers.
- **`x-query-method-candidates` extension** documents the hidden query execution endpoints at the spec level via a top-level extension, partially mitigating the gap.
- **Lambda handler endpoints**: The Lambda execution entry points (`src/autom8_asana/lambda_handlers/`) are not covered by the spec — they are invoked directly by AWS, not via HTTP.

---

## Knowledge Gaps

1. **Exact path strings for sections router** — The `sections.py` grep shows 6 route decorators but the file was not read in full. Path strings were inferred from standard FastAPI patterns.
2. **`resolver_schema.py` sub-router** — The schema discovery sub-router included into the resolver router via `router.include_router(schema_router)` was not read.
3. **`intake_create_models.py` and `intake_resolve_models.py` full field schemas** — Partial: request/response field names were inferred from docstrings and handler code but not fully enumerated from the Pydantic model definitions.
4. **`entity_write.py` full PATCH request body schema** — The route path and HTTP method are confirmed but the request body model definition was not fully observed.
5. **DynamoDB idempotency store full schema** — Behavior is documented from `main.py` references only.
6. **Rate limit specifics beyond workflows** — SlowAPI is configured (`src/autom8_asana/api/rate_limit.py`). The workflows router has an explicit 10 req/min limit. Other per-route limits were not investigated.
