---
domain: api
generated_at: "2026-04-28T21:55:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "8c58f930"
confidence: 0.92
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase API Surface

## Route Inventory

**Framework**: Python / FastAPI (OAS 3.2.0). Entrypoint: `src/autom8_asana/api/main.py` → `create_app()`. Routes aggregated via `src/autom8_asana/api/routes/__init__.py`.

**Version prefix model**: Two namespaces coexist:
- `/api/v1/` — PAT-authenticated, user-facing resources (tasks, projects, sections, users, workspaces, dataframes, exports, webhooks, workflows, offers)
- `/v1/` — S2S JWT-authenticated, internal service surface (resolver, query, fleet-query, exports mirror, admin, intake, entity-write, matching)

**Published spec paths** — `docs/api-reference/openapi.json` OAS 3.2.0 (44 paths, 53 operations):

| Resource Group | Path | Method(s) | Handler | Auth |
|---|---|---|---|---|
| **Health** | `/health`, `/ready`, `/health/deps` | GET | `routes/health.py` | None |
| **Tasks** | `/api/v1/tasks` and 11 sub-paths | GET/POST/PUT/DELETE | `routes/tasks.py` | PAT |
| **Projects** | `/api/v1/projects` and 4 sub-paths | varied | `routes/projects.py` | PAT |
| **Sections** | `/api/v1/sections` and 3 sub-paths | varied | `routes/sections.py` | PAT |
| **Users** | `/api/v1/users`, `/me`, `/{gid}` | GET | `routes/users.py` | PAT |
| **Workspaces** | `/api/v1/workspaces` and `/{gid}` | GET | `routes/workspaces.py` | PAT |
| **DataFrames** | `/api/v1/dataframes/{schemas,project,section}` | GET | `routes/dataframes.py` | PAT |
| **Exports** (WIP) | `/api/v1/exports`, `/v1/exports` | POST | `routes/exports.py` | PAT (api), S2S (v1) |
| **Offers** | `/api/v1/offers/section-timelines` | GET | `routes/section_timelines.py` | PAT |
| **Workflows** | `/api/v1/workflows/`, `/{id}/invoke` | GET/POST | `routes/workflows.py` | PAT |
| **Webhooks** | `/api/v1/webhooks/inbound` | POST | `routes/webhooks.py` | URL token |
| **Resolver** | `/v1/resolve/{entity_type}` + schema/enums | POST/GET | `routes/resolver.py` | S2S JWT |
| **Query** | `/v1/query/*` introspection routes | GET | `routes/query.py` | S2S JWT |
| **Fleet Query** | `/v1/query/entities`, `/api/v1/query/entities` | POST | `routes/fleet_query.py` | S2S JWT / PAT |

**Hidden routes (`include_in_schema=False`)** — live in code, not in published spec:

| Path | Methods | Handler | Auth |
|---|---|---|---|
| `/v1/admin/*` | POST | `routes/admin.py` | S2S JWT |
| `/api/v1/internal/*` | varied | `routes/internal.py` | S2S JWT |
| `/v1/matching/query` | POST | `routes/matching.py` | S2S JWT |
| `/api/v1/entity/{entity_type}` | PATCH | `routes/entity_write.py` | S2S JWT |
| `/v1/resolve/business`, `/v1/resolve/contact` | POST | `routes/intake_resolve.py` | S2S JWT |
| `/v1/tasks/{gid}/custom-fields` | POST | `routes/intake_custom_fields.py` | S2S JWT |
| `/v1/intake/business`, `/v1/intake/route` | POST | `routes/intake_create.py` | S2S JWT |
| `/v1/query/{entity_type}/rows`, `/aggregate` | POST | `routes/query.py` | S2S JWT |

**Spec-vs-code delta**: Spec has 44 paths (53 operations). Code exposes ~14 additional route prefixes/paths beyond the spec, all intentionally hidden or WIP (exports untracked on this branch).

**Route registration order note** (critical): Fleet query and exports routers MUST mount BEFORE `query_router` in `main.py:426-441` to prevent FastAPI's first-match routing from treating `entities`/`exports` as `{entity_type}` path parameter values. Documented inline at registration site.

## Authentication & Authorization Model

| Scheme | Type | Usage Namespace | Env / Secret |
|---|---|---|---|
| `PersonalAccessToken` | HTTP Bearer | `/api/v1/*` user-facing | User-supplied PAT in `Authorization: Bearer`; passed to Asana API |
| `ServiceJWT` | HTTP Bearer (JWT) | `/v1/*` internal S2S | Short-lived JWT issued by `auth.api.autom8y.io`, validated against JWKS |
| `WebhookToken` | API key (query param) | `/api/v1/webhooks/inbound` | `ASANA_WEBHOOK_INBOUND_TOKEN`; timing-safe comparison |
| `OAuth2Asana` | OAuth2 client credentials | All tagged operations | Documentation-only; no runtime enforcement yet |

**Auth middleware chain** (`main.py:create_app`):
1. `FleetAppConfig` from `autom8y_api_middleware.create_fleet_app` — fleet middleware stack
2. `JWTAuthMiddleware` (`main.py:374-396`): validates JWTs on S2S routes; excludes PAT routes, webhooks, health, `/redoc`, export PAT routes via `exclude_paths`. `require_business_scope=True` enforces scope validation post-signature
3. `IdempotencyMiddleware` — DynamoDB-backed by default (`IDEMPOTENCY_STORE_BACKEND`), in-memory or noop fallback
4. `SecurityHeadersMiddleware` — HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Cache-Control: no-store

**Route-level auth DI** (`routes/dependencies.py`): `get_auth_context()` → `AuthContext` — dual-mode (PAT vs JWT) via `detect_token_type()` in `auth/dual_mode.py`. JWT validated, then resolved to bot PAT (`ASANA_PAT` env).

**Auth classification** (fail-closed):
- Public: health tag only
- PAT Bearer: all `/api/v1/` resource routes except webhooks
- S2S JWT: all `/v1/` routes
- URL token: webhooks only

**OAuth2 scopes** (`main.py:_OAUTH2_SCOPE_DEFINITIONS`) — documentation-only in Phase 1: `tasks:read/write`, `projects:read/write`, `sections:read/write`, `users:read`, `workspaces:read`, `dataframes:read`, `exports:read`, `workflows:execute`, `resolver:read`, `query:read`, `intake:write`, `admin:manage`, `webhooks:receive`.

## Request/Response Contracts

**Response envelope pattern** (fleet-standard from `autom8y_api_schemas`):

Success:
```json
{
  "data": <payload>,
  "meta": { "request_id": "<16-char hex>", "timestamp": "<ISO-8601>",
            "pagination": { "limit": 100, "has_more": false, "next_offset": null } }
}
```

Error:
```json
{
  "error": { "code": "<MACHINE_CODE>", "message": "<human text>", "details": { ... } },
  "meta": { "request_id": "<16-char hex>" }
}
```

Models: `SuccessResponse[T]`, `ErrorResponse`, `ErrorDetail`, `ResponseMeta`, `PaginationMeta` (`api/models.py`). All errors include `request_id`.

**Pagination**: Cursor-based via `offset` string. `PaginationMeta.next_offset` carries next page token. List endpoints accept `limit` (1-100, default 100) and `offset` query params.

**Field naming**: `snake_case`. GIDs typed as `GidStr` — `r"^\d{1,64}$"` in production, relaxed in `test`/`local` (`api/models.py:46`).

**Content types**: `application/json` (default), `application/x-polars-json` (Accept negotiation on dataframes/exports), `text/csv` and `format: "parquet"` on exports.

**Error code mapping** (ADR-ASANA-004):

| SDK Exception | HTTP | Code |
|---|---|---|
| `NotFoundError` | 404 | `RESOURCE_NOT_FOUND` |
| `AuthenticationError` | 401 | `INVALID_CREDENTIALS` |
| `ForbiddenError` | 403 | `FORBIDDEN` |
| `RateLimitError` | 429 | `RATE_LIMITED` (+ `Retry-After`) |
| `GidValidationError` | 400 | `VALIDATION_ERROR` |
| `ServerError` | 502 | `UPSTREAM_ERROR` |
| `TimeoutError` | 504 | `UPSTREAM_TIMEOUT` |
| `FleetError` subclasses | varies | `ASANA-<CATEGORY>-NNN` |
| Generic `Exception` | 500 | `INTERNAL_ERROR` |

**Idempotency**: `Idempotency-Key` request header via `IdempotencyMiddleware`. DynamoDB-backed (`IDEMPOTENCY_TABLE_NAME`, default `autom8-idempotency-keys`). Exports declare `x-fleet-idempotency: {idempotent: true}` in `openapi_extra`.

**Exports contract (WIP — `routes/exports.py`)**: `ExportRequest` body: `entity_type` (str), `project_gids` (list[int], min 1), `predicate` (PredicateNode AST | None), `format` (json|csv|parquet, default json), `options` (`ExportOptions` — open/additive, `extra="allow"`). `ExportOptions`: `include_incomplete_identity` (bool, default true), `dedupe_key` (list[str], default `["office_phone", "vertical"]`). Returns DataFrame rows with `identity_complete` boolean column.

## Cross-Service Dependencies

**Outbound dependencies**:

| Service | Client | Endpoint Pattern | Purpose | Discovery |
|---|---|---|---|---|
| **Asana API** | `AsanaClient` SDK | `https://app.asana.com/api/1.0/*` | Asana resource CRUD | Per-request via `ClientPool`; PAT from user or `ASANA_PAT` env |
| **autom8y auth (JWKS)** | `auth/jwt_validator.py` | `AUTH_JWKS_URL` (default `auth.api.autom8y.io`) | JWT validation; 5-min JWKS cache | Env vars `AUTH_JWKS_URL`, `AUTH_ISSUER` |
| **autom8y auth (token)** | `auth/service_token.py:ServiceTokenAuthProvider` | `auth.api.autom8y.io` | S2S JWT for `DataServiceClient` | `SERVICE_CLIENT_ID`/`SECRET` env |
| **autom8_data service** | `clients/data/client.py:DataServiceClient` | `AUTOM8Y_DATA_URL` | Analytics/PVP for engine joins | Optional; engine raises `JoinError` if join requested without client |

Contract file: `docs/contracts/openapi-data-service-client.yaml` (v1.0.0).

**Inbound callers**:
- Asana Rules engine → `POST /api/v1/webhooks/inbound?token=<TOKEN>` with full task JSON
- Internal autom8y services → `/v1/*` routes via S2S JWT

**Lambda invocation**: `routes/admin.py` can invoke `CACHE_WARMER_LAMBDA_ARN` for force-rebuild operations.

## Spec Completeness & Freshness

**Spec file**: `docs/api-reference/openapi.json`, OAS 3.2.0.

**Generation mechanism**: Code-first. Auto-generated at runtime by FastAPI from route decorators and Pydantic models, post-processed by `custom_openapi()` in `main.py:509-816`. Committed spec is a snapshot. Not hand-authored.

**Spec authority**: Code is source of truth. Committed spec is secondary, regenerated on route/model changes. `openapitools.json` in root indicates generator toolchain in use.

**Route count delta**:
- Spec: 44 paths, 53 operations
- Code (total): ~58 paths/route prefixes including hidden routes
- Hidden (intentional): 11 route groups
- WIP on current branch: `/v1/exports`, `/api/v1/exports` (untracked) — **not yet in committed spec**

**Format version**: OAS 3.2.0 (with `jsonSchemaDialect`). Uses `webhooks` object (OAS 3.1+) for `asanaTaskChanged` webhook definition.

**Spec drift assessment**: Low on committed routes; exports routes are current gap (will need spec regeneration once branch merges). The `/api/v1/query/entities` fleet-query PAT mount intentionally hidden.

## Knowledge Gaps

- `routes/admin.py` hidden endpoints: only `POST /v1/admin/cache/refresh` confirmed; full inventory not cataloged
- `routes/internal.py` hidden endpoints: prefix `/api/v1/internal` confirmed, specific endpoint paths not enumerated
- `routes/fleet_query.py`: dual-mount confirmed; handler accepts `FleetQueryRequest` body (not further inspected)
- DataServiceClient endpoint inventory: contract file exists but specific endpoint paths not enumerated
- Intake resolver response models not fully cataloged
- OAuth2 enforcement timeline: documented as "documentation-only" with no committed enforcement date
