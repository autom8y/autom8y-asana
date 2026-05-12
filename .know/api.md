---
domain: api
generated_at: "2026-05-08T00:00Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/api/**/*.py"
  - "./docs/api-reference/openapi.json"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
update_mode: "time-only"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase API Surface

## Route Inventory

**Framework**: Python / FastAPI (OAS 3.2.0). Entrypoint: `src/autom8_asana/api/main.py` → `create_app()`. Routes aggregated via `src/autom8_asana/api/routes/__init__.py`.

**Version prefix model**: Two namespaces coexist:
- `/api/v1/` — PAT-authenticated, user-facing resources (tasks, projects, sections, users, workspaces, dataframes, exports, webhooks, workflows, offers)
- `/v1/` — S2S JWT-authenticated, internal service surface (resolver, query, fleet-query, exports mirror, admin, intake, entity-write, matching)

**Published spec paths** — `docs/api-reference/openapi.json` OAS 3.2.0 (46 paths, 55 operations):

| Resource Group | Path | Method(s) | Handler | Auth |
|---|---|---|---|---|
| **Health** | `/health` | GET | `routes/health.py` | None |
| **Health** | `/ready` | GET | `routes/health.py` | None |
| **Health** | `/health/deps` | GET | `routes/health.py` | None |
| **Tasks** | `/api/v1/tasks` | GET, POST | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}` | GET, PUT, DELETE | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/subtasks` | GET | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/dependents` | GET | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/duplicate` | POST | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/tags` | POST | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/tags/{tag_gid}` | DELETE | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/section` | POST | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/assignee` | PUT | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/projects` | POST | `routes/tasks.py` | PAT |
| **Tasks** | `/api/v1/tasks/{gid}/projects/{project_gid}` | DELETE | `routes/tasks.py` | PAT |
| **Projects** | `/api/v1/projects` | GET, POST | `routes/projects.py` | PAT |
| **Projects** | `/api/v1/projects/{gid}` | GET, PUT, DELETE | `routes/projects.py` | PAT |
| **Projects** | `/api/v1/projects/{gid}/sections` | GET | `routes/projects.py` | PAT |
| **Projects** | `/api/v1/projects/{gid}/members` | POST, DELETE | `routes/projects.py` | PAT |
| **Sections** | `/api/v1/sections` | POST | `routes/sections.py` | PAT |
| **Sections** | `/api/v1/sections/{gid}` | GET, PUT, DELETE | `routes/sections.py` | PAT |
| **Sections** | `/api/v1/sections/{gid}/tasks` | POST | `routes/sections.py` | PAT |
| **Sections** | `/api/v1/sections/{gid}/reorder` | POST | `routes/sections.py` | PAT |
| **Users** | `/api/v1/users` | GET | `routes/users.py` | PAT |
| **Users** | `/api/v1/users/me` | GET | `routes/users.py` | PAT |
| **Users** | `/api/v1/users/{gid}` | GET | `routes/users.py` | PAT |
| **Workspaces** | `/api/v1/workspaces` | GET | `routes/workspaces.py` | PAT |
| **Workspaces** | `/api/v1/workspaces/{gid}` | GET | `routes/workspaces.py` | PAT |
| **DataFrames** | `/api/v1/dataframes/schemas` | GET | `routes/dataframes.py` | PAT |
| **DataFrames** | `/api/v1/dataframes/schemas/{name}` | GET | `routes/dataframes.py` | PAT |
| **DataFrames** | `/api/v1/dataframes/project/{gid}` | GET | `routes/dataframes.py` | PAT |
| **DataFrames** | `/api/v1/dataframes/section/{gid}` | GET | `routes/dataframes.py` | PAT |
| **Exports** | `/api/v1/exports` | POST | `routes/exports.py:post_export_api_v1` | PAT |
| **Exports (S2S)** | `/v1/exports` | POST | `routes/exports.py:post_export_v1` | S2S JWT |
| **Offers** | `/api/v1/offers/section-timelines` | GET | `routes/section_timelines.py` | PAT |
| **Workflows** | `/api/v1/workflows/` | GET | `routes/workflows.py` | PAT |
| **Workflows** | `/api/v1/workflows/{workflow_id}/invoke` | POST | `routes/workflows.py` | PAT |
| **Webhooks** | `/api/v1/webhooks/inbound` | POST | `routes/webhooks.py` | URL token |
| **Resolver** | `/v1/resolve/{entity_type}` | POST | `routes/resolver.py` | S2S JWT |
| **Resolver** | `/v1/resolve/{entity_type}/schema` | GET | `routes/resolver_schema.py` | S2S JWT |
| **Resolver** | `/v1/resolve/{entity_type}/schema/enums/{field_name}` | GET | `routes/resolver_schema.py` | S2S JWT |
| **Query** | `/v1/query/entities` | GET | `routes/query.py:query_introspection_router` | S2S JWT |
| **Query** | `/v1/query/{entity_type}/fields` | GET | `routes/query.py:query_introspection_router` | S2S JWT |
| **Query** | `/v1/query/{entity_type}/relations` | GET | `routes/query.py:query_introspection_router` | S2S JWT |
| **Query** | `/v1/query/{entity_type}/sections` | GET | `routes/query.py:query_introspection_router` | S2S JWT |
| **Query** | `/v1/query/data-sources` | GET | `routes/query.py:query_introspection_router` | S2S JWT |
| **Query** | `/v1/query/data-sources/{factory}/fields` | GET | `routes/query.py:query_introspection_router` | S2S JWT |

**Hidden routes (`include_in_schema=False`)** — live in code, not in published spec:

| Path | Method(s) | Handler | Auth |
|---|---|---|---|
| `/v1/admin/cache/refresh` | POST | `routes/admin.py` | S2S JWT |
| `/api/v1/internal/*` | varies | `routes/internal.py` | S2S JWT |
| `/v1/matching/query` | POST | `routes/matching.py` | S2S JWT |
| `/api/v1/entity/{entity_type}` | PATCH | `routes/entity_write.py` | S2S JWT |
| `/v1/resolve/business` | POST | `routes/intake_resolve.py` | S2S JWT |
| `/v1/resolve/contact` | POST | `routes/intake_resolve.py` | S2S JWT |
| `/v1/tasks/{gid}/custom-fields` | POST | `routes/intake_custom_fields.py` | S2S JWT |
| `/v1/intake/business` | POST | `routes/intake_create.py` | S2S JWT |
| `/v1/intake/route` | POST | `routes/intake_create.py` | S2S JWT |
| `/v1/query/{entity_type}/rows` | POST | `routes/query.py:router` | S2S JWT |
| `/v1/query/{entity_type}/aggregate` | POST | `routes/query.py:router` | S2S JWT |
| `/v1/query/{entity_type}` | POST | `routes/query.py:router` | S2S JWT (deprecated, sunset 2026-06-01) |
| `/v1/query/entities` (POST) | POST | `routes/fleet_query.py:fleet_query_router_v1` | S2S JWT |
| `/api/v1/query/entities` (POST) | POST | `routes/fleet_query.py:fleet_query_router_api_v1` | S2S JWT |

**Spec-vs-code delta**: Spec: 46 paths, 55 operations. Code: ~56 route decorators + 14 hidden-route groups. All hidden routes are intentionally `include_in_schema=False` — this is by design, not spec drift. Exports routes `/api/v1/exports` and `/v1/exports` are committed to the spec (present in `docs/api-reference/openapi.json`).

**Route registration order constraint** (CRITICAL — LBC-011/TENSION-009): Fleet-query routers and exports routers MUST mount BEFORE `query_router` in `main.py:431-441`. FastAPI matches routes in registration order. If `fleet_query_router_v1`/`exports_router_v1` mount after `query_router`, the path `/v1/query/entities` and `/v1/exports` would be consumed by the legacy `POST /v1/query/{entity_type}` wildcard handler (treating `entities`/`exports` as a path parameter), triggering a 422 extra_forbidden error. Annotated explicitly at `main.py:419-441`.

## Authentication & Authorization Model

**Three auth schemes** (defined in `main.py:create_app → custom_openapi`):

| Scheme | Type | Usage Namespace | Runtime Enforcement |
|---|---|---|---|
| `PersonalAccessToken` | HTTP Bearer | `/api/v1/*` user-facing | `get_auth_context()` DI; `detect_token_type()` returns PAT mode; token passed directly to Asana API |
| `ServiceJWT` | HTTP Bearer (JWT) | `/v1/*` internal S2S | `JWTAuthMiddleware` validates JWT; `validate_service_token()` checks JWKS; resolved to `ASANA_PAT` bot PAT for downstream calls |
| `WebhookToken` | API key (`?token=`) | `/api/v1/webhooks/inbound` | `verify_webhook_token()` timing-safe comparison vs `ASANA_WEBHOOK_INBOUND_TOKEN`; wire code `ASANA-AUTH-002` on failure |
| `OAuth2Asana` | OAuth2 client credentials | All tagged operations | Documentation-only in Phase 1; no runtime enforcement |

**Auth middleware chain** (`main.py:create_app`):
1. `FleetAppConfig.create_fleet_app` — fleet-standard middleware stack (request ID, logging, CORS)
2. `JWTAuthMiddleware` (`jwt_auth_config`, `main.py:374-396`): validates JWTs on S2S routes; excludes via `DEFAULT_EXCLUDE_PATHS` + service-specific exclusions: `/redoc`, `/api/v1/webhooks/*`, `/api/v1/tasks/*`, `/api/v1/projects/*`, `/api/v1/sections/*`, `/api/v1/users/*`, `/api/v1/workspaces/*`, `/api/v1/dataframes/*`, `/api/v1/offers/*`, `/api/v1/exports/*`. `require_business_scope=True` enforces scope post-signature (ADR-07 §7.1 precedence).
3. `IdempotencyMiddleware` — DynamoDB-backed by default (`IDEMPOTENCY_STORE_BACKEND=dynamodb`, table `IDEMPOTENCY_TABLE_NAME` default `autom8-idempotency-keys`, region `IDEMPOTENCY_TABLE_REGION` default `us-east-1`). Falls back to `InMemoryIdempotencyStore` or `NoopIdempotencyStore`.
4. `SecurityHeadersMiddleware` — HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Cache-Control: no-store on non-docs paths.

**Route-level auth DI** (`api/dependencies.py`): `get_auth_context()` → `AuthContext` — dual-mode via `detect_token_type()` in `auth/dual_mode.py`:
- PAT mode: user token passed directly through as `asana_pat`
- JWT mode: `validate_service_token(token)` → JWT claims; `get_bot_pat()` → `ASANA_PAT` env → bot PAT used for downstream Asana calls
- Error paths: `CircuitOpenError`/`TransientAuthError` → 503 `ApiServiceUnavailableError`; `PermanentAuthError` → 401 `ApiAuthError`

**Auth classification** (fail-closed, tag-based in `main.py:93-128`):
```
_PAT_TAGS = {"tasks", "projects", "sections", "users", "workspaces", "dataframes", "offers", "workflows", "exports"}
_TOKEN_TAGS = {"webhooks"}
_S2S_TAGS = {"resolver", "query", "admin", "internal", "entity-write", "intake-resolve", "intake-custom-fields", "intake-create", "matching"}
_NO_AUTH_TAGS = {"health"}
```

**Exports PAT exclusion from JWTAuthMiddleware** (SCAR-WS8): `/api/v1/exports/*` is explicitly in `JWTAuthMiddleware.exclude_paths` (`main.py:389`). The PAT auth surface for exports is handled by the dual-mode `get_auth_context()` DI in handler space, not by the JWT middleware. This is intentional and diverges from fleet `DEFAULT_EXCLUDE_PATHS`.

**OAuth2 scope taxonomy** (documentation-only, `main.py:_OAUTH2_SCOPE_DEFINITIONS`): `tasks:read`, `tasks:write`, `projects:read`, `projects:write`, `sections:read`, `sections:write`, `users:read`, `workspaces:read`, `dataframes:read`, `exports:read`, `workflows:execute`, `resolver:read`, `query:read`, `intake:write`, `admin:manage`, `webhooks:receive`.

**Scope rules** (`main.py:_SCOPE_RULES`): path-prefix + HTTP method → required scopes. Write methods (POST/PUT/PATCH/DELETE) get write scopes; GET/HEAD get read scopes. First matching prefix wins.

**Client pool** (`api/client_pool.py`): Token-keyed `ClientPool` manages `AsanaClient` instances. S2S callers share bot PAT (1hr TTL); PAT callers get per-PAT pool entry (5min TTL). Rate limiters, circuit breakers, and AIMD semaphores accumulate state per token.

## Request/Response Contracts

**Response envelope pattern** (fleet-standard from `autom8y_api_schemas`):

Success:
```json
{
  "data": <T>,
  "meta": {
    "request_id": "<16-char hex>",
    "timestamp": "<ISO-8601>",
    "pagination": { "limit": 100, "has_more": false, "next_offset": null }
  }
}
```

Error:
```json
{
  "error": {
    "code": "<MACHINE_CODE>",
    "message": "<human readable>",
    "details": { ... }
  },
  "meta": { "request_id": "<16-char hex>" }
}
```

Core types: `SuccessResponse[T]`, `ErrorResponse`, `ErrorDetail`, `ResponseMeta`, `PaginationMeta` — imported from `autom8y_api_schemas`, re-exported at `api/models.py` for backward compatibility. Auth-layer errors also emit `AuthTebError` (JWTAuthMiddleware `AUTH-TEB-NNN` codes); documented as `oneOf[ErrorResponse, AuthTebError]` on 401/403 in `error_responses.py`.

**Pagination**: Cursor-based. `PaginationMeta.next_offset` carries opaque next-page token. List endpoints: `limit` (int, 1-100, default 100), `offset` (str | None). Pattern consistent across tasks, subtasks, dependents, projects, sections, users, workspaces.

**Field naming convention**: `snake_case` throughout. GIDs typed as `GidStr` (`api/models.py:51-53`): regex `r"^\d{1,64}$"` in production; pattern relaxed (`None`) in `test`/`local`/`LOCAL` environments (detected via `AUTOM8Y_ENV` env var at module load time).

**Content types**:
- `application/json` — default for all endpoints
- `text/csv` — exports format=csv
- `application/octet-stream` — exports format=parquet (binary Polars)
- `application/x-polars-json` — Accept-header content negotiation on dataframes and exports

**Standard error response catalog** (`api/error_responses.py`):

| HTTP | Model | Description |
|---|---|---|
| 401 | `ErrorResponse \| AuthTebError` | AUTH-TEB (JWTAuthMiddleware) or application-layer |
| 403 | `ErrorResponse \| AuthTebError` | AUTH-TEB-004 or application-layer |
| 404 | `ErrorResponse` | Resource not found |
| 422 | (description only) | Validation error — ASANA-VAL-001 |
| 429 | `ErrorResponse` | Rate limited, Retry-After header |
| 500 | `ErrorResponse` | Internal server error |

**SDK exception → HTTP mapping** (ADR-ASANA-004, `api/errors.py`):

| SDK Exception | HTTP | Code |
|---|---|---|
| `NotFoundError` | 404 | `RESOURCE_NOT_FOUND` |
| `AuthenticationError` | 401 | `INVALID_CREDENTIALS` |
| `ForbiddenError` | 403 | `FORBIDDEN` |
| `RateLimitError` | 429 | `RATE_LIMITED` |
| `GidValidationError` | 400 | `VALIDATION_ERROR` |
| `ServerError` | 502 | `UPSTREAM_ERROR` |
| `TimeoutError` | 504 | `UPSTREAM_TIMEOUT` |
| `FleetError` subclasses | varies | `ASANA-<CATEGORY>-NNN` |
| Generic `Exception` | 500 | `INTERNAL_ERROR` |

**Validation errors**: `register_validation_handler(app, service_code_prefix="ASANA")` emits `ASANA-VAL-001` codes (matches `ADS-VAL-001`, `SCHED-VAL-001` pattern).

**Idempotency**: `Idempotency-Key` request header via `IdempotencyMiddleware`. DynamoDB-backed (`IDEMPOTENCY_STORE_BACKEND=dynamodb`, table `IDEMPOTENCY_TABLE_NAME`, region `IDEMPOTENCY_TABLE_REGION`). Task create/update, project/section mutations annotated with `x-fleet-idempotency`. Exports declare `x-fleet-idempotency: {idempotent: true}`.

**Task request models** (`api/models.py`): `CreateTaskRequest` (name, notes, assignee, projects, due_on `^\d{4}-\d{2}-\d{2}$`, workspace), `UpdateTaskRequest` (name, notes, completed, due_on), `AddTagRequest`, `MoveSectionRequest`, `SetAssigneeRequest`, `AddToProjectRequest`, `DuplicateTaskRequest`.

**Project request models**: `CreateProjectRequest` (name, workspace, team), `UpdateProjectRequest` (name, notes, archived), `MembersRequest` (members list[GidStr]).

**Section request models**: `CreateSectionRequest` (name, project), `UpdateSectionRequest` (name), `AddTaskToSectionRequest` (task_gid), `ReorderSectionRequest` (project_gid, before_section | after_section).

**Exports contract** (`routes/exports.py`):

```python
class ExportRequest:
    entity_type: str            # canonical entity identifier (Phase 1: "process")
    project_gids: list[int]     # min_length=1, Asana project GIDs
    predicate: PredicateNode | None  # composable filter AST
    format: Literal["json", "csv", "parquet"]  # default "json"
    options: ExportOptions       # open/additive, extra="allow" (LBC-010 constraint)

class ExportOptions:
    include_incomplete_identity: bool  # default True — surface null-key rows with identity_complete=false
    dedupe_key: list[str]              # default ["office_phone", "vertical"]
    # predicate_join_semantics: reserved Phase 2 field, admitted via extra="allow"
```

Phase 1 default column projection (`PHASE_1_DEFAULT_COLUMNS`): `gid`, `name`, `section`, `office_phone`, `vertical`, `pipeline_type`, `modified_at`, plus `identity_complete` boolean appended on every row.

**ExportsSuccessResponse** (`api/models.py:98-123`): typed `SuccessResponse[list[dict[str, Any]]]` subclass with `data` field annotated with representative example row for M-02 schema scoring. Non-runtime, schema-generation-only enrichment.

**FleetQuery contract** (`routes/fleet_query.py`): `FleetQuery` body from `autom8y_api_schemas`; dispatched via `fleet_query_to_dispatch_kwargs()` adapter in `api/fleet_query_adapter.py`. Response: `SuccessResponse[FleetQueryEnvelope]` where `FleetQueryEnvelope = {entity_type, project_gid, rows: list[dict]}`. PaginationMeta round-trips request limit/offset.

## Cross-Service Dependencies

**Outbound dependencies**:

| Service | Client | Endpoint/Pattern | Purpose | Discovery |
|---|---|---|---|---|
| **Asana API** | `AsanaClient` SDK (`src/autom8_asana/client.py`) | `https://app.asana.com/api/1.0/*` (default, overridable via `ASANA_BASE_URL`) | All Asana resource CRUD (tasks, projects, sections, users, workspaces) | Per-request via `ClientPool`; PAT from user token or `ASANA_PAT` env (bot PAT) |
| **autom8y auth (JWKS)** | `auth/jwt_validator.py` | `AUTH_JWKS_URL` env (default `https://auth.api.autom8y.io/.well-known/jwks.json`) | JWT signature validation; 5-min JWKS cache (`AUTH_JWKS_CACHE_TTL`) | Env vars `AUTH_JWKS_URL`, `AUTH_ISSUER` (default `auth.api.autom8y.io`) |
| **autom8y auth (token)** | `auth/service_token.py:ServiceTokenAuthProvider` | `auth.api.autom8y.io` token endpoint | S2S JWT for authenticating `DataServiceClient` calls | `SERVICE_CLIENT_ID`, `SERVICE_CLIENT_SECRET` env; falls back to env var `AUTOM8Y_DATA_API_KEY` |
| **autom8y-data service** | `clients/data/client.py:DataServiceClient` | `AUTOM8Y_DATA_URL` env | Analytics joins in query engine; workflows `DataServiceClient` | Optional; engine raises `JoinError` with clear message if join requested without client; also used by workflow invocations at `routes/workflows.py:355-361` |
| **AWS DynamoDB** | `boto3` sync wrapped with `asyncio.to_thread()` | `IDEMPOTENCY_TABLE_NAME` (default `autom8-idempotency-keys`) | Idempotency key storage for `IdempotencyMiddleware` | `IDEMPOTENCY_TABLE_NAME`, `IDEMPOTENCY_TABLE_REGION` (default `us-east-1`) |
| **AWS S3** | `dataframes/storage.py:S3DataFrameStorage` | `S3LocationConfig` env | DataFrame cache persistence; preloaded at startup via `lifespan.py` | S3 bucket + prefix env config; graceful degradation on S3 unavailable |
| **AWS Lambda** | boto3 (admin route) | `CACHE_WARMER_LAMBDA_ARN` env | Force cache rebuild via `POST /v1/admin/cache/refresh` | ARN env var |

**Inbound callers**:
- **Asana Rules engine** → `POST /api/v1/webhooks/inbound?token=<TOKEN>` with full task JSON payload. Verifies via `ASANA_WEBHOOK_INBOUND_TOKEN`. Returns 200 immediately to prevent Asana retries.
- **Internal autom8y services** → `/v1/*` routes via S2S JWT (`ServiceJWT` scheme). Services authenticated against `auth.api.autom8y.io` JWKS.

**Contract files**: `docs/contracts/openapi-data-service-client.yaml` (v1.0.0) — DataServiceClient API contract exists but specific endpoint paths not enumerated in this knowledge document.

## Spec Completeness & Freshness

**Spec file**: `docs/api-reference/openapi.json`, OAS 3.2.0 (with `jsonSchemaDialect`).

**Generation mechanism**: Code-first. Auto-generated at runtime by FastAPI from route decorators and Pydantic models, post-processed by `custom_openapi()` in `main.py:509-816`. Committed spec is a snapshot. Not hand-authored.

**Spec authority**: Code is source of truth. Committed spec is secondary, regenerated on route/model changes.

**Custom OpenAPI enrichment pipeline** (`main.py:custom_openapi()`):
1. `enrich_openapi_schema()` — common fleet enrichment (OAS 3.2.0, jsonSchemaDialect, server URLs, security schemes)
2. Fail-closed tag classification (`SecurityAnnotationStrategy.FAIL_CLOSED`)
3. Health path exemption from security annotations
4. Authorization header stripping (`strip_authorization_header=True`)
5. Error response injection (400, 401, 403, 404)
6. Tag descriptions (`_TAG_DESCRIPTIONS`)
7. OAuth2 scope annotations (Sprint-6, documentation-only)
8. Query method candidate extension (`x-query-method-candidates`)
9. Task model schema injection (from `autom8_asana.models.task.Task`)
10. Fleet schema types injection (`SuccessResponse`, `ErrorResponse`, `ErrorDetail`)
11. Webhook definition via OAS 3.1+ `webhooks` object (`asanaTaskChanged`)

**Route count delta** (as of SHA `20ef7952`):
- Spec: 46 paths, 55 operations
- Code total: ~56 route decorators across public + hidden routers
- Hidden (intentional): 14 route groups — all `include_in_schema=False`, by design
- Exports routes: committed to spec — `/api/v1/exports` (POST) and `/v1/exports` (POST) both present in `docs/api-reference/openapi.json`

**Schemas in spec**: 55 total in `components.schemas`. Exports-specific: `AndGroup`, `OrGroup`, `NotGroup`, `Comparison`, `ExportRequest`, `ExportOptions`, `Op` (with date operators `BETWEEN`, `DATE_GTE`, `DATE_LTE`). `Task` model and base registry types (`SuccessResponse`, `ErrorResponse`, `ErrorDetail`) injected by `custom_openapi()`.

**Format version**: OAS 3.2.0 with `jsonSchemaDialect`. Uses `webhooks` object (OAS 3.1+ feature) for `asanaTaskChanged` definition.

**Spec freshness**: Zero spec drift for committed spec as of SHA `20ef7952`. Hidden routes are intentionally excluded. Fleet-query PAT mount (`/api/v1/query/entities` POST) is intentionally hidden. Server entries: Production (`https://asana.api.autom8y.io`), Staging (`https://asana.staging.api.autom8y.io`).

## Knowledge Gaps

- `routes/internal.py` specific endpoint paths not enumerated — router prefix is `/api/v1/internal` (`include_in_schema=False`); the file primarily exports `ServiceClaims` model and `require_service_claims` dependency used by other routers
- `DataServiceClient` internal endpoint paths not enumerated — contract exists at `docs/contracts/openapi-data-service-client.yaml` but was not read during this audit
- OAuth2 enforcement timeline: documented as "documentation-only" with no committed enforcement date
- Exports observability gap (OBS-EXPORTS-001): `POST /api/v1/exports` and `POST /v1/exports` have zero metric, trace, or SLO instrumentation beyond structured log correlation via OTel `trace_id`. Pre-GA deadline 2026-06-15. See `obs.md` for details.

```metadata
domain: api
source_hash: "20ef7952"
confidence: 0.93
grades:
  route_inventory: "A"
  auth_model: "A"
  request_response_contracts: "A"
  cross_service_dependencies: "B"
  spec_freshness: "A"
overall: "A"
weighted_score: 0.937
```
