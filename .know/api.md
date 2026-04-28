---
domain: api
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
confidence: 0.92
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase API

**Framework**: FastAPI (Python) with `autom8y_api_middleware` fleet app factory
**Application entry**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/main.py` — `create_app()` returns the `FastAPI` instance
**Router aggregation**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/api/routes/__init__.py`
**Base URLs**: `https://asana.api.autom8y.io` (production), `https://asana.staging.api.autom8y.io` (staging)

## Route Inventory

Two namespaces with distinct auth models:
- `/api/v1/*` — public-facing (PAT Bearer or URL-token for webhooks)
- `/v1/*` — internal S2S only (ServiceJWT)

**Versioning pattern**: single version (v1) embedded in path prefix. No `/v2/` or header versioning.

### Health Routes — public, no auth

| Path | Method | Handler | File |
|------|--------|---------|------|
| `/health` | GET | `health_check` | `routes/health.py:114` |
| `/ready` | GET | `readiness_check` | `routes/health.py:143` |
| `/health/deps` | GET | `deps_check` | `routes/health.py:297` |

### Tasks — PAT Bearer, `/api/v1/tasks`

| Path | Method | Handler | Response model |
|------|--------|---------|----------------|
| `/api/v1/tasks` | GET | `list_tasks` | `SuccessResponse[list[AsanaResource]]` — paginated |
| `/api/v1/tasks` | POST | `create_task` | `SuccessResponse[AsanaResource]` 201 |
| `/api/v1/tasks/{gid}` | GET | `get_task` | `SuccessResponse[AsanaResource]` |
| `/api/v1/tasks/{gid}` | PUT | `update_task` | `SuccessResponse[AsanaResource]` |
| `/api/v1/tasks/{gid}` | DELETE | `delete_task` | 204 No Content |
| `/api/v1/tasks/{gid}/subtasks` | GET | `list_subtasks` | `SuccessResponse[list[AsanaResource]]` — paginated |
| `/api/v1/tasks/{gid}/dependents` | GET | `list_dependents` | `SuccessResponse[list[AsanaResource]]` — paginated |
| `/api/v1/tasks/{gid}/duplicate` | POST | `duplicate_task` | `SuccessResponse[AsanaResource]` 201 |
| `/api/v1/tasks/{gid}/tags` | POST | `add_tag` | `SuccessResponse[AsanaResource]` |
| `/api/v1/tasks/{gid}/tags/{tag_gid}` | DELETE | `remove_tag` | `SuccessResponse[AsanaResource]` |
| `/api/v1/tasks/{gid}/section` | POST | `move_to_section` | `SuccessResponse[AsanaResource]` |
| `/api/v1/tasks/{gid}/assignee` | PUT | `set_assignee` | `SuccessResponse[AsanaResource]` |
| `/api/v1/tasks/{gid}/projects` | POST | `add_to_project` | `SuccessResponse[AsanaResource]` |
| `/api/v1/tasks/{gid}/projects/{project_gid}` | DELETE | `remove_from_project` | `SuccessResponse[AsanaResource]` |

### Projects — PAT Bearer, `/api/v1/projects`

| Path | Method | Handler | Response model |
|------|--------|---------|----------------|
| `/api/v1/projects` | GET | `list_projects` | `SuccessResponse[list[AsanaResource]]` — paginated |
| `/api/v1/projects` | POST | `create_project` | `SuccessResponse[AsanaResource]` 201 |
| `/api/v1/projects/{gid}` | GET | `get_project` | `SuccessResponse[AsanaResource]` |
| `/api/v1/projects/{gid}` | PUT | `update_project` | `SuccessResponse[AsanaResource]` |
| `/api/v1/projects/{gid}` | DELETE | `delete_project` | 204 No Content |
| `/api/v1/projects/{gid}/sections` | GET | `list_sections` | `SuccessResponse[list[AsanaResource]]` — paginated |
| `/api/v1/projects/{gid}/members` | POST | `add_members` | `SuccessResponse[AsanaResource]` |
| `/api/v1/projects/{gid}/members` | DELETE | `remove_members` | `SuccessResponse[AsanaResource]` |

### Sections — PAT Bearer, `/api/v1/sections`

| Path | Method | Handler |
|------|--------|---------|
| `/api/v1/sections` | POST | `create_section` |
| `/api/v1/sections/{gid}` | GET | `get_section` |
| `/api/v1/sections/{gid}` | PUT | `update_section` |
| `/api/v1/sections/{gid}` | DELETE | `delete_section` |
| `/api/v1/sections/{gid}/tasks` | POST | `add_task_to_section` — 204 No Content |
| `/api/v1/sections/{gid}/reorder` | POST | `reorder_section` — 204 No Content |

### Users — PAT Bearer, `/api/v1/users`

| Path | Method | Handler |
|------|--------|---------|
| `/api/v1/users/me` | GET | `get_current_user` |
| `/api/v1/users/{gid}` | GET | `get_user` |
| `/api/v1/users` | GET | `list_users` — paginated |

### Workspaces — PAT Bearer, `/api/v1/workspaces`

| Path | Method | Handler |
|------|--------|---------|
| `/api/v1/workspaces` | GET | `list_workspaces` — paginated |
| `/api/v1/workspaces/{gid}` | GET | `get_workspace` |

### DataFrames — PAT Bearer, `/api/v1/dataframes`

| Path | Method | Handler |
|------|--------|---------|
| `/api/v1/dataframes/schemas` | GET | `list_dataframes` |
| `/api/v1/dataframes/schemas/{name}` | GET | `get_dataframe_schema` |
| `/api/v1/dataframes/project/{gid}` | GET | `list_project_dataframe` |
| `/api/v1/dataframes/section/{gid}` | GET | `list_section_dataframe` |

Schema names: `base`, `unit`, `contact`, `business`, `offer`, `asset_edit`, `asset_edit_holder`, `process`.

### Webhooks — URL-token auth, `/api/v1/webhooks`

| Path | Method | Handler |
|------|--------|---------|
| `/api/v1/webhooks/inbound` | POST | `receive_inbound_webhook` |

### Workflows — PAT Bearer, `/api/v1/workflows`

| Path | Method | Handler |
|------|--------|---------|
| `/api/v1/workflows/` | GET | `list_workflows` |
| `/api/v1/workflows/{workflow_id}/invoke` | POST | `invoke_workflow` |

### Offers — PAT Bearer, `/api/v1/offers`

| Path | Method | Handler | File |
|------|--------|---------|------|
| `/api/v1/offers/section-timelines` | GET | (section_timelines router) | `routes/section_timelines.py` |

### Resolver — S2S JWT only, `/v1/resolve`

| Path | Method | Handler |
|------|--------|---------|
| `/v1/resolve/{entity_type}` | POST | `resolve_entities` |
| `/v1/resolve/{entity_type}/schema` | GET | `get_entity_schema` |
| `/v1/resolve/{entity_type}/schema/enums/{field_name}` | GET | `get_enum_values` |

### Query (Introspection) — S2S JWT, `/v1/query`

| Path | Method | Handler |
|------|--------|---------|
| `/v1/query/entities` | GET | entity types list |
| `/v1/query/{entity_type}/fields` | GET | field list |
| `/v1/query/{entity_type}/relations` | GET | joinable entities |
| `/v1/query/{entity_type}/sections` | GET | section index |
| `/v1/query/data-sources` | GET | factory list |
| `/v1/query/data-sources/{factory}/fields` | GET | factory fields |

### Hidden S2S Routes (not in OpenAPI spec)

| Prefix | Routes | File |
|--------|--------|------|
| `/v1/query/{entity_type}` POST | legacy query | `routes/query.py:396` |
| `/v1/query/{entity_type}/rows` POST | composable row retrieval | `routes/query.py:468` |
| `/v1/query/{entity_type}/aggregate` POST | aggregate query | `routes/query.py:545` |
| `/v1/query/entities` POST (dual-mount) | fleet FleetQuery | `routes/fleet_query.py:224,255` |
| `/api/v1/query/entities` POST | fleet FleetQuery (fleet namespace) | `routes/fleet_query.py:255` |
| `/v1/admin/cache/refresh` POST | cache refresh | `routes/admin.py:394` |
| `/api/v1/internal/*` | internal S2S | `routes/internal.py` |
| `/v1/resolve/business` POST | intake resolve business | `routes/intake_resolve.py` |
| `/v1/resolve/contact` POST | intake resolve contact | `routes/intake_resolve.py` |
| `/v1/intake/business` POST | intake create business | `routes/intake_create.py` |
| `/v1/intake/route` POST | intake route unit | `routes/intake_create.py` |
| `/api/v1/entity/{entity_type}/{gid}` PATCH | entity write | `routes/entity_write.py` |
| `/v1/matching/query` POST | matching query | `routes/matching.py` |
| `/v1/tasks/{gid}/custom-fields` POST | custom field write | `routes/intake_custom_fields.py` |

**Route count**: 56 handler decorators in code; 44 paths in OpenAPI spec. The 12-path delta is fully explained by `include_in_schema=False` routers (admin, internal, query-exec, fleet_query, intake_resolve, intake_create, entity_write, matching, intake_custom_fields). No routes unintentionally hidden — hidden set is deliberate S2S-only surface.

**[KNOW-CANDIDATE]** The dual-mounted fleet query route (`/v1/query/entities` + `/api/v1/query/entities` both POST) represents a sovereignty pattern not documented elsewhere in `.know/`.

## Authentication & Authorization Model

### Three authentication schemes

**1. PersonalAccessToken (PAT) — Bearer scheme**

Used by `/api/v1/tasks`, `/api/v1/projects`, `/api/v1/sections`, `/api/v1/users`, `/api/v1/workspaces`, `/api/v1/dataframes`, `/api/v1/offers`, `/api/v1/workflows`.

Flow:
- Client sends `Authorization: Bearer <asana-pat>`
- `JWTAuthMiddleware` (from `autom8y_api_middleware`) configured to EXCLUDE these path prefixes
- `get_auth_context` dependency (`routes/dependencies.py:108`) calls `detect_token_type(token)` from `autom8_asana.auth.dual_mode`
- For `AuthMode.PAT`: token passed through directly to Asana API

**2. ServiceJWT (S2S) — Bearer JWT scheme**

Used by `/v1/resolve/*`, `/v1/query/*`, `/v1/admin/*`, `/v1/intake/*`, `/v1/matching/*`, `/api/v1/entity/*`, `/api/v1/internal/*`.

Flow:
- Client sends `Authorization: Bearer <jwt>`
- `JWTAuthMiddleware` validates JWT against JWKS endpoint (`AUTH_JWKS_URL`, default `https://auth.api.autom8y.io/.well-known/jwks.json`)
- `get_auth_context` detects JWT mode, calls `validate_service_token(token)` from `autom8_asana.auth.jwt_validator`
- On success: retrieves bot PAT from `ASANA_PAT` env var via `get_bot_pat()`, uses it for downstream Asana calls
- Claims include `service_name`, `scope`, `permissions` (used for `admin:access` super-admin gating)
- `require_business_scope=True` on `JWTAuthConfig`: service JWTs must include `business_id` scope claim (ADR-07 §7.1)

**3. WebhookToken — API key (query param)**

Used exclusively by `/api/v1/webhooks/inbound`.

Flow:
- Client sends `?token=<secret>` query parameter
- `verify_webhook_token` dependency (`routes/webhooks.py:209`) does timing-safe `hmac.compare_digest` against `ASANA_WEBHOOK_INBOUND_TOKEN` env var
- `JWTAuthMiddleware` excludes `/api/v1/webhooks/*` entirely
- Missing/invalid token raises `AsanaWebhookSignatureInvalidError` (wire code `ASANA-AUTH-002`)

### Route auth classification summary

| Auth Requirement | Path Prefixes |
|-----------------|---------------|
| None (public) | `/health`, `/ready`, `/health/deps` |
| PAT Bearer | `/api/v1/tasks`, `/api/v1/projects`, `/api/v1/sections`, `/api/v1/users`, `/api/v1/workspaces`, `/api/v1/dataframes`, `/api/v1/offers`, `/api/v1/workflows` |
| URL token (`?token=`) | `/api/v1/webhooks/*` |
| S2S JWT | `/v1/resolve`, `/v1/query`, `/v1/admin`, `/v1/intake`, `/v1/matching`, `/api/v1/entity`, `/api/v1/internal` |

### Dual-mode dependency

`get_auth_context` (`dependencies.py:108`) supports BOTH PAT and JWT modes for `/api/v1/*` PAT routes. An S2S caller may send a JWT to these routes and the service will use the bot PAT for Asana calls (ADR-ASANA-007).

### Super-admin gate

`POST /v1/admin/cache/refresh` requires `admin:access` in `claims.permissions` (Bedrock W4C-P3 / SEC-DT-10). Other S2S endpoints only require a valid JWT.

### OAuth2 scope taxonomy (documentation-only)

Scope definitions exist in `main.py:137-153`. Injected into the spec as `OAuth2Asana` security scheme but NOT runtime-enforced. Scope rules mapped in `_SCOPE_RULES` list at `main.py:158-174`.

**[KNOW-CANDIDATE]** The dual-mode auth architecture (PAT routes also accept S2S JWT, substituting bot PAT) is a non-obvious pattern any agent modifying endpoints must understand.

## Request/Response Contracts

### Success response envelope

All non-204 success responses use the fleet-standard envelope from `autom8y-api-schemas`:

```json
{
  "data": <payload>,
  "meta": {
    "request_id": "<16-char hex>",
    "timestamp": "<ISO 8601>",
    "pagination": {
      "limit": 100,
      "has_more": false,
      "next_offset": null
    }
  }
}
```

`SuccessResponse`, `ResponseMeta`, `PaginationMeta` imported from `autom8y_api_schemas`, re-exported at `api/models.py`. `build_success_response()` helper constructs the envelope.

### Error response envelope

```json
{
  "error": {
    "code": "<SERVICE-CATEGORY-NNN>",
    "message": "<human-readable>",
    "details": {}
  },
  "meta": {
    "request_id": "<16-char hex>",
    "timestamp": "<ISO 8601>"
  }
}
```

Error code prefix is `ASANA-` (e.g., `ASANA-VAL-001`, `ASANA-AUTH-002`, `ASANA-DEP-002`). 422 validation errors use `ASANA-VAL-001` (registered via `register_validation_handler(app, service_code_prefix="ASANA")`).

Alternate middleware-layer error shape (`AuthTebError`) can appear on 401/403 when `JWTAuthMiddleware` intercepts before the route handler. Both shapes documented in the spec via `_AuthEnvelope = ErrorResponse | AuthTebError` (`error_responses.py:32`).

### Pagination

Cursor-based pagination on all list endpoints:
- Request: `?limit=<int>&offset=<cursor_string>`
- Response meta: `pagination.has_more: bool`, `pagination.next_offset: str | null`
- `limit` range: 1–100, default 100
- `offset` is an opaque Asana-returned cursor (not numeric)

### Field naming

Snake_case throughout. GIDs are numeric strings validated by `GidStr` type alias (`models.py:47`): regex `^\d{1,64}$` in production, relaxed in test/local.

### Content types

- Default: `application/json`
- DataFrame endpoints support content negotiation: `Accept: application/x-polars-json` returns Polars-serialized JSON format (ADR-ASANA-005)
- Webhook inbound: accepts any `application/json` body

### Typed field constraints

- GIDs: `^\d{1,64}$` (numeric string, Pydantic `StringConstraints`)
- `entity_ids` in workflow invoke: list of 1–100 numeric strings
- `limit` parameters: `ge=1, le=100`
- DataFrame schema values: `Literal["base", "unit", "contact", "business", "offer", "asset_edit", "asset_edit_holder", "process"]`

### HTTP status codes used

- 200: Success
- 201: Created (task/project/section/duplicate)
- 202: Accepted (cache refresh)
- 204: No Content (DELETE, section/task operations)
- 400: Business logic / validation error
- 401: Auth failure
- 403: Forbidden (insufficient scope)
- 404: Entity not found
- 422: Pydantic validation error
- 429: Rate limit exceeded
- 503: Dependency unavailable
- 504: Workflow timeout

### Idempotency middleware

All mutating requests support `Idempotency-Key` header (via `IdempotencyMiddleware`). Backend: DynamoDB (table `autom8-idempotency-keys`, region `us-east-1`); fallbacks: in-memory or noop, controlled by `IDEMPOTENCY_STORE_BACKEND` env var.

## Cross-Service Dependencies

### Outbound: Asana API

- **Purpose**: Primary data store. All task/project/section/user/workspace CRUD delegates to Asana REST API.
- **Base URL**: `https://app.asana.com/api/1.0` (configured via `ASANA_BASE_URL` env var)
- **Auth**: PAT Bearer token (user's PAT in PAT-mode or bot PAT from `ASANA_PAT` env var in S2S mode)
- **Client**: `AsanaClient` instantiated per-request via `ClientPool` (token-keyed, 1hr TTL for S2S, 5min for PAT — `IMP-19`)

### Outbound: autom8y-data service (DataServiceClient)

- **Purpose**: Cross-service analytics enrichment for query engine joins. Provides insights (account, ads, campaigns, spend, etc.) keyed by phone/vertical pairs.
- **Base URL**: `AUTOM8Y_DATA_URL` env var (default `http://localhost:8000`; production: `https://data.autom8.io`)
- **Auth**: `AUTOM8Y_DATA_API_KEY` env var (bearer) or `ServiceTokenAuthProvider` (ServiceAccount JWT → token)
- **Client**: `DataServiceClient` from `autom8_asana.clients.data.client` — singleton on `app.state`, lazy-initialized
- **Contract spec**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/docs/contracts/openapi-data-service-client.yaml`
- **Endpoint consumed**: `POST /api/v1/factory/{factory_name}` — batch insights fetch
- **Circuit breaker**: enabled by default (5 failures in 60s opens circuit, 30s recovery)

### Outbound: autom8y-auth JWKS endpoint

- **Purpose**: JWT signature validation for S2S routes.
- **URL**: `AUTH_JWKS_URL` env var (default `https://auth.api.autom8y.io/.well-known/jwks.json`)
- **Pattern**: HTTP GET on every S2S request hitting `JWTAuthMiddleware` (cached by auth SDK)

### Outbound: AWS Lambda (cache warmer)

- **Purpose**: Trigger cache rebuild for entity types after full cache purge.
- **Invocation**: Fire-and-forget (`InvocationType=Event`) via boto3 `lambda.invoke()`
- **ARN**: `CACHE_WARMER_LAMBDA_ARN` env var (optional)
- **Location**: `routes/admin.py:_invoke_cache_warmer_lambda`

### Outbound: AWS DynamoDB (idempotency store)

- **Purpose**: Idempotency key storage for mutating requests.
- **Table**: `IDEMPOTENCY_TABLE_NAME` env var (default `autom8-idempotency-keys`)
- **Region**: `IDEMPOTENCY_TABLE_REGION` env var (default `us-east-1`)

### Inbound consumers

- **Asana Rules actions**: POST to `/api/v1/webhooks/inbound?token=<secret>` when an Asana rule fires on task mutation. Payload is full Asana Task JSON.
- **autom8y fleet services** (internal callers): POST to S2S routes under `/v1/resolve/*`, `/v1/query/*`, `/v1/intake/*`, `/api/v1/entity/*`.

## Spec Completeness & Freshness

- **Spec location**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/docs/api-reference/openapi.json`
- **OpenAPI version**: 3.2.0 (OAS 3.2.0 — `jsonSchemaDialect` set by fleet enrichment)
- **Generation mechanism**: Code-first (auto-generated by FastAPI from route decorators + Pydantic models, then post-processed by `custom_openapi()` in `main.py:484`). Recent commit `16abf564` confirms regeneration as of ADD-01+ADD-02 work.

**Route count delta**:
- Code routes: 56 handler decorators
- Spec paths: 44
- Hidden-from-spec routes (intentional): 14 paths across admin, internal, query-exec, fleet_query (hidden), intake_resolve, intake_create, entity_write, matching, intake_custom_fields

Delta fully accounted for by `include_in_schema=False`. Zero spec-only "ghost" routes. Spec is an accurate subset of the code surface.

- **Security schemes in spec**: `PersonalAccessToken`, `ServiceJWT`, `WebhookToken`, `OAuth2Asana` (doc-only)
- **Servers in spec**: production + staging — both present
- **Webhook OpenAPI object**: Present — `spec["webhooks"]["asanaTaskChanged"]` injected in `custom_openapi()` per OpenAPI 3.1+ webhook pattern
- **Spec authority**: The OpenAPI spec is a SECONDARY artifact (code is primary). Must be regenerated after route or schema changes.

**[KNOW-CANDIDATE]** The `custom_openapi()` post-processing pipeline is load-bearing — it injects security scheme annotations, OAuth2 scope taxonomy, Task model schema, fleet error responses, and the `x-query-method-candidates` extension. Any agent modifying routes must call this function path to keep the spec current.

## Knowledge Gaps

1. **`internal.py` route surface**: File has 0 `@router.*` decorators — the internal router is mounted but contains only auth helpers (`require_service_claims`, `ServiceClaims`). Actual internal endpoint surface appears replaced by resolver/entity-write routes. Confirm whether any live endpoints remain under `/api/v1/internal/`.
2. **`resolver_schema.py` full route detail**: Two routes found but request/response schema not fully inspected.
3. **`section_timelines.py` response schema**: Endpoint existence confirmed but response structure (`active_section_days`, `billable_section_days`) not fully read.
4. **Intake route request bodies**: `IntakeBusinessCreateRequest`, `BusinessResolveRequest`, `ContactResolveRequest`, etc. not read.
5. **OAuth2 runtime enforcement timeline**: Scope taxonomy is documentation-only as of this audit.
6. **DataServiceClient endpoint usage**: Data client consumes `POST /api/v1/factory/{factory_name}` but the full list of factory names used by the query engine join layer not enumerated.
