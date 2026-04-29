---
domain: api
generated_at: "2026-04-29T00:00Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/api/**/*.py"
  - "./docs/api-reference/openapi.json"
generator: theoros
source_hash: "6b303485"
confidence: 0.93
format_version: "1.0"
update_mode: "incremental"
incremental_cycle: 1
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
| **Health** | `/health`, `/ready`, `/health/deps` | GET | `routes/health.py` | None |
| **Tasks** | `/api/v1/tasks` and 11 sub-paths | GET/POST/PUT/DELETE | `routes/tasks.py` | PAT |
| **Projects** | `/api/v1/projects` and 4 sub-paths | varied | `routes/projects.py` | PAT |
| **Sections** | `/api/v1/sections` and 3 sub-paths | varied | `routes/sections.py` | PAT |
| **Users** | `/api/v1/users`, `/me`, `/{gid}` | GET | `routes/users.py` | PAT |
| **Workspaces** | `/api/v1/workspaces` and `/{gid}` | GET | `routes/workspaces.py` | PAT |
| **DataFrames** | `/api/v1/dataframes/{schemas,project,section}` | GET | `routes/dataframes.py` | PAT |
| **Exports** | `/api/v1/exports`, `/v1/exports` | POST | `routes/exports.py` | PAT (api), S2S (v1) |
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

**Spec-vs-code delta**: Spec has 46 paths (55 operations). Code exposes ~14 additional route prefixes/paths beyond the spec, all intentionally hidden via `include_in_schema=False`. Exports routes are NOW COMMITTED and tracked in spec post-PR #38 (merge commit `80256049`).

**Route registration order note** (critical — TENSION-009/LBC-011): Fleet query and exports routers MUST mount BEFORE `query_router` in `main.py:431-441` to prevent FastAPI's first-match routing from treating `entities`/`exports` as `{entity_type}` path parameter values. Exports router mount explicitly annotated at `main.py:433-440`. See also `design-constraints.md` TENSION-009.

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

**Exports auth exclusion** (SCAR-WS8 regression test): `JWTAuthMiddleware.exclude_paths` includes `/api/v1/exports/*` at `main.py:389`. This diverges from fleet `DEFAULT_EXCLUDE_PATHS` — the PAT-auth surface for exports is deliberately excluded from JWT middleware so the dual-mode `get_auth_context()` DI handles auth in handler space. Verified by `tests/unit/api/test_exports_auth_exclusion.py`.

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

**Exports contract — LIVE post-PR #38** (`routes/exports.py`): `ExportRequest` body: `entity_type` (str), `project_gids` (list[int], min 1), `predicate` (PredicateNode AST | None), `format` (json|csv|parquet, default json), `options` (`ExportOptions` — open/additive, `extra="allow"`, LBC-010). `ExportOptions`: `include_incomplete_identity` (bool, default true), `dedupe_key` (list[str], default `["office_phone", "vertical"]`). Returns DataFrame rows with `identity_complete` boolean column.

**Exports schemas added post-PR #38** (now in `docs/api-reference/openapi.json` components.schemas): `AndGroup`, `OrGroup`, `NotGroup`, `Comparison`, `ExportRequest`, `ExportOptions`, `Op` (with operators including `BETWEEN`, `DATE_GTE`, `DATE_LTE`).

**Telos linkage**: Exports Phase 1 of `project-asana-pipeline-extraction` — DELIVERED (PR #38, commit `80256049`). Phase 1 deadline 2026-05-11. See also `design-constraints.md` LBC-010 for `ExportOptions extra="allow"` constraint.

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
- Spec: 46 paths, 55 operations (verified from `docs/api-reference/openapi.json` post-PR #38)
- Code (total): ~58 paths/route prefixes including hidden routes
- Hidden (intentional): 11 route groups
- Exports routes: COMMITTED and tracked in spec — `/api/v1/exports` and `/v1/exports` both present post-PR #38 (merge commit `80256049`)

**Schemas** (post-PR #38): 55 total in `components.schemas`. New schemas added by exports: `AndGroup`, `OrGroup`, `NotGroup`, `Comparison`, `ExportRequest`, `ExportOptions`, `Op`.

**Field examples** (CSI-001 DISCHARGED): 136 `"examples":` plural entries in spec. 2 residual `"example":` singular entries at `dataframes.py:511,632` — pre-CSI-001 raw dict inline OpenAPI annotation, not a regression. `just spec-check` passes. M-02 score: 136 (tracked in `.ci/semantic-baseline.json:12`).

**Format version**: OAS 3.2.0 (with `jsonSchemaDialect`). Uses `webhooks` object (OAS 3.1+) for `asanaTaskChanged` webhook definition.

**Spec drift assessment**: NONE — spec is fully derivable from Pydantic source post-T-08 CSI-001 discharge. Exports routes committed to spec at PR #38. The `/api/v1/query/entities` fleet-query PAT mount intentionally hidden.

## Knowledge Gaps

- `routes/admin.py` hidden endpoints: only `POST /v1/admin/cache/refresh` confirmed; full inventory not cataloged
- `routes/internal.py` hidden endpoints: prefix `/api/v1/internal` confirmed, specific endpoint paths not enumerated
- `routes/fleet_query.py`: dual-mount confirmed; handler accepts `FleetQueryRequest` body (not further inspected)
- DataServiceClient endpoint inventory: contract file exists but specific endpoint paths not enumerated
- Intake resolver response models not fully cataloged
- OAuth2 enforcement timeline: documented as "documentation-only" with no committed enforcement date
- Exports observability gap (OBS-EXPORTS-001): `POST /api/v1/exports` and `POST /v1/exports` have zero metric, trace, or SLO instrumentation beyond structured log correlation via OTel `trace_id`. Pre-GA deadline 2026-06-15. See `obs.md` for details.
