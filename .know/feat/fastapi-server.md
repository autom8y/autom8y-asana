---
domain: feat/fastapi-server
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/"
  - "./src/autom8_asana/entrypoint.py"
  - "./Dockerfile"
  - "./docker-compose.yml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.96
format_version: "1.0"
---

# FastAPI HTTP Server

## Purpose and Design Rationale

Primary HTTP surface for `autom8_asana` in ECS mode. Bridges two caller populations: **external/user** (PAT auth, Asana resource management via `/api/v1/*`) and **internal S2S** (JWT auth, entity resolution/query/intake/writes using bot PAT via `/v1/*`). Core design principle: thin routing shell over the deep SDK — route handlers contain no business logic.

**Decision records**: TDD-I5 (API Main Decomposition) decomposed `main.py` into `lifespan.py`, `startup.py`, and `preload/`. ADR-ASANA-007 mandates per-request SDK client lifecycle for user isolation. TDD-SPRINT1-CUSTOM-OPENAPI drives the custom OpenAPI enrichment pipeline. ADR-0060 governs fail-fast entity discovery at startup.

**Dual-mode container**: Same Docker image runs ECS (uvicorn) or Lambda (awslambdaric). Detection pivot: `AWS_LAMBDA_RUNTIME_API` env var absent = ECS, present = Lambda. Lambda mode requires handler path as `sys.argv[1]` (e.g., `autom8_asana.lambda_handlers.cache_warmer.handler`).

**Sprint history**: S2S JWT baseline (PKG-009/AUDIT-010), idempotency middleware (ADR-omniscience-idempotency), FleetQuery dual-mount (S3 D4, TDD §7.4.3), exports dual-mount (Sprint 3, project-asana-pipeline-extraction Phase 1), OAuth2 scope pilot (Sprint 6 Track D), security headers + fleet error handler (WS-B1+B2 P1-D), `/ready` deep probe promotion (SP-L3-1 D4).

## Conceptual Model

### App Factory (`create_app()`)

`create_app()` in `api/main.py` is the FastAPI application factory. Execution sequence:
1. Build `IdempotencyMiddleware` with configured store (env-selected: dynamodb / memory / noop)
2. Build `CORSConfig` from `settings.cors_origins_list`
3. Build `JWTAuthConfig` with PAT route tree exclusions + `require_business_scope=True`
4. Call `create_fleet_app(config, routers, lifespan, cors, jwt_auth, rate_limit, extra_middleware)` — registers 22 routers in order, wires middleware stack
5. Register domain Prometheus metrics (`api/metrics.py`)
6. Call `register_exception_handlers(app)` — 14 specific + catch-all handlers
7. Call `register_validation_handler(app, service_code_prefix="ASANA")` — emits `ASANA-VAL-001` codes
8. Add `SecurityHeadersMiddleware` (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Cache-Control: no-store)
9. Register `fleet_error_handler` for `FleetError` catch-all
10. Attach `custom_openapi()` function (runs once, cached on `app.openapi_schema`)

### Middleware Stack (outer → inner execution order)

Per `api/middleware/idempotency.py` header comment and `create_fleet_app` contract:

1. **SecurityHeadersMiddleware** — HSTS, X-Frame-Options, X-Content-Type-Options; WS-B1+B2 P1-D
2. **CORSMiddleware** — configurable origins (`cors_origins_list` env)
3. **JWTAuthMiddleware** — validates S2S JWT, excludes PAT routes + webhooks + health + docs; `require_business_scope=True`
4. **IdempotencyMiddleware** — RFC 8791, 4 eligible endpoints, DynamoDB/InMemory/Noop backends
5. **SlowAPIMiddleware** — rate limiting (`rate_limit_rpm` from settings), keyed by PAT prefix or remote IP
6. **RequestLoggingMiddleware** — structured access logs, PAT redaction via `_filter_sensitive_data`
7. **RequestIDMiddleware** — generates/propagates 16-char hex `X-Request-ID`

### 13-Step Startup Sequence (`api/lifespan.py`)

1. `bootstrap()` — registers business entity types in `EntityRegistry`
2. `configure_logging()` — structured logging with `add_otel_trace_ids` + `_filter_sensitive_data` processors
3. `HTTPXClientInstrumentor().instrument()` — global httpx OTel W3C traceparent propagation (optional; degrades gracefully on `ImportError`)
4. `create_cache_provider(AsanaConfig().cache)` → `app.state.cache_provider` — shared SDK CacheProvider (DEF-005 fix: single instance shared by warm-up and request handlers)
5. `ClientPool(cache_provider=app.state.cache_provider)` → `app.state.client_pool` — LRU S2S resilience pool (IMP-19)
6. `_discover_entity_projects(app)` → `app.state.entity_project_registry` — workspace entity discovery; **fail-fast** (raises `RuntimeError` on failure per ADR-0060)
7. `validate_cross_registry_consistency(check_entity_project_registry=True)` — EntityRegistry vs EntityProjectRegistry divergence check; logs errors but does not block startup
8. `_initialize_dataframe_cache(app)` → `app.state.dataframe_cache` — Memory+S3 tiered cache; graceful degrade if S3 not configured
9. `_register_schema_providers()` — bridges satellite `SchemaRegistry` to SDK `SchemaVersionProvider` for cache compatibility checks (SC-004)
10. `_initialize_mutation_invalidator(app)` → `app.state.mutation_invalidator` — wires REST cache invalidation; graceful degrade on failure
11. `EntityWriteRegistry(entity_registry)` → `app.state.entity_write_registry` — built once after entity discovery; graceful degrade (503) on failure
12. `register_workflow_config(insights_config)` + `register_workflow_config(audit_config)` — registers `insights-export` and `conversation-audit` workflow configs; graceful degrade (404 for all workflows) on failure; sets `_workflow_configs_registered` flag in `health.py`
13. `validate_cascade_ordering()` — validates `warm_priority` cascade dependency graph; **hard fail** (`ValueError`) on conflict (L1 guard per WS-4a)

After step 13: `asyncio.create_task(_preload_dataframe_cache_progressive(app))` — **background** cache warm (non-blocking; allows `/health` to return 200 immediately while `/ready` gates on warmth).

### 22 Registered Routers (4 dual-mounted)

| Router | Auth | Primary Path | Notes |
|--------|------|-------------|-------|
| `health_router` | none | `/health`, `/ready`, `/health/deps` | SCAR-011/011b |
| `users_router` | PAT | `/api/v1/users` | |
| `workspaces_router` | PAT | `/api/v1/workspaces` | |
| `dataframes_router` | PAT | `/api/v1/dataframes` | |
| `tasks_router` | PAT | `/api/v1/tasks` | |
| `projects_router` | PAT | `/api/v1/projects` | |
| `sections_router` | PAT | `/api/v1/sections` | |
| `section_timelines_router` | PAT | `/api/v1/offers` | |
| `webhooks_router` | URL token | `/api/v1/webhooks` | `?token=` query param |
| `workflows_router` | PAT | `/api/v1/workflows` | |
| `exports_router_v1` | PAT | `/v1/exports` | dual-mount (Sprint 3) |
| `exports_router_api_v1` | PAT | `/api/v1/exports` | dual-mount (Sprint 3) |
| `fleet_query_router_v1` | S2S | `/v1/query/entities` | dual-mount (S3 D4) |
| `fleet_query_router_api_v1` | S2S | `/api/v1/query/entities` | dual-mount (S3 D4) |
| `intake_resolve_router` | S2S | `/v1/intake/resolve/*` | MUST mount BEFORE resolver_router |
| `resolver_router` | S2S | `/v1/resolve/{entity_type}` | wildcard |
| `query_introspection_router` | S2S | `/v1/query` | GET introspection only |
| `query_router` | S2S | `/v1/query/{entity_type}` | wildcard; MUST mount AFTER fleet+exports |
| `admin_router` | S2S | `/v1/admin` | |
| `internal_router` | S2S | `/v1/internal` | |
| `entity_write_router` | S2S | `/v1/entity-write` | |
| `intake_custom_fields_router` | S2S | `/v1/intake/custom-fields` | |
| `intake_create_router` | S2S | `/v1/intake/create` | |
| `matching_router` | S2S | `/v1/matching` | |

(Count: 22 logical routers, 2 dual-mounts = 24 total `RouterMount` registrations)

### Auth DI Chain (`api/dependencies.py`)

`_extract_bearer_token` → `get_auth_context` → `detect_token_type` (dot-count heuristic: 2 dots = JWT, 0 = PAT) → PAT path (passthrough, user's own PAT) or JWT path (JWKS validation + bot PAT) → `ClientPool.get_or_create(token, is_s2s=True/False)` → `AuthContext(mode, asana_pat, caller_service)`.

`AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]`. S2S routes use `EntityServiceDep` / `DataServiceClient`; PAT routes use `AuthContextDep` directly.

### Client Pool (`api/client_pool.py`)

LRU pool keyed by `SHA-256(token)[:16]`. Max 100 entries. S2S TTL: 1h, PAT TTL: 5m. `_PooledClientWrapper` proxies all attribute access to the underlying `AsanaClient` but overrides `aclose()` / `close()` as no-ops to prevent FastAPI dependency teardown from closing pooled clients. Pool metrics: hits/misses/evictions via structlog. CB tuning: `failure_threshold=10, recovery_timeout=30s`. `close_all()` called during shutdown.

### Health Probes (`api/routes/health.py`)

**Three-tier contract** (SCAR-011/011b):
- `GET /health` — pure liveness, no I/O, always 200. Zero dependencies checked. ALB liveness target.
- `GET /ready` — readiness probe with 4 concurrent checks (SP-L3-1 D4):
  1. `cache` — `_cache_ready` flag (set by `_preload_dataframe_cache_progressive` in `finally` block)
  2. `workflow_configs` — `_workflow_configs_registered` flag (set by lifespan step 12)
  3. `jwks` — HTTP GET to `AUTH_JWKS_URL` with 2s timeout, validates `keys` array presence
  4. `bot_pat` — presence check for `ASANA_PAT` env var (≥10 chars); never logs value
  Returns 200 only when all 4 pass; 503 if any fail. JWKS/PAT are DEGRADED (not UNAVAILABLE) on failure, so they reduce aggregate status but do not individually cause 503.
- `GET /health/deps` — dependency probe (sequential, 5s JWKS timeout, returns JWKS + bot_pat checks).

Module-level flags `_cache_ready` and `_workflow_configs_registered` are the readiness state. `set_cache_ready(True)` is always called in the `finally` block of `_preload_dataframe_cache_progressive`, even on preload failure.

### Idempotency Middleware (`api/middleware/idempotency.py`)

RFC 8791 implementation. **4 eligible endpoints**:
- `POST /v1/intake/business`
- `POST /v1/intake/route`
- `POST /v1/tasks/{task_gid}/custom-fields`
- `PATCH /api/v1/entity/{entity_type}/{gid}`

**Two-phase protocol** (claim → execute → finalize):
1. Missing `Idempotency-Key` header: passthrough (R-006 additive contract), log derived fallback key
2. Invalid key format (< 8 chars, > 256 chars, invalid chars `[a-zA-Z0-9-_.]`): 400 `INVALID_IDEMPOTENCY_KEY`
3. Key claimed by another in-flight request: 409 + `Retry-After: 1`
4. Key finalized with different body fingerprint: 422 `IDEMPOTENCY_KEY_MISMATCH`
5. Key finalized with same fingerprint: replay stored response with `X-Idempotent-Replayed: true`
6. New key: claim → execute → finalize → echo `Idempotency-Key` header

**DynamoDB key schema**: `pk = {service}#{key}`, `sk = {METHOD}#{path_template}`, `ttl = epoch + 86400s`. Body: `asyncio.to_thread()` wraps synchronous boto3 client. Finalize failure risk: SCAR-IDEM-001 — if `finalize()` fails, key is not persisted; client retry re-executes mutation.

**Graceful degradation**: DynamoDB unavailable at construction → `NoopIdempotencyStore` (passthrough). Store failure at claim/get time → execute with `X-Idempotent-Degraded: true` header.

**Backends**: `DynamoDBIdempotencyStore` (prod, `IDEMPOTENCY_STORE_BACKEND=dynamodb`), `InMemoryIdempotencyStore` (dev, `=memory`), `NoopIdempotencyStore` (`=noop` or unknown).

### Progressive Preload (`api/preload/progressive.py`)

Cache warm-up runs as `asyncio.create_task("cache_warming")` — non-blocking. Processes projects in **cascade-safe phase order** (providers before consumers per `cascade_warm_phases()`). Concurrency: `PROJECT_CONCURRENCY = 3` semaphore. Three warm paths per project:
1. S3 parquet exists: load directly, populate shared `UnifiedTaskStore` (cascade providers), run `validate_cascade_fields_async`, self-heal corrected rows back to S3
2. No manifest or parquet: delegate to `CACHE_WARMER_LAMBDA_ARN` (fire-and-forget `boto3.client("lambda").invoke`); production only
3. Cold start (dev/non-prod, no Lambda ARN): full progressive build via `ProgressiveProjectBuilder`

**L2 pre-phase gate**: Before each phase, verifies all cascade providers for entities in that phase have already completed. Raises `WarmupOrderingError` (never caught by `BROAD-CATCH` handlers) if violated. **30-second heartbeat** (`HEARTBEAT_INTERVAL_SECONDS`) during long operations. `set_cache_ready(True)` is always called in `finally`, regardless of outcome.

### OpenAPI Enrichment (`custom_openapi()`)

8 common steps via `enrich_openapi_schema()` (OAS 3.2.0, security schemes, server URLs, fail-closed tag classification, health exemption, authorization header stripping, error response injection). 4 service-specific steps:
- OAuth2 scope annotations (Sprint 6 pilot, DOCUMENTATION-ONLY, `OAuth2Asana` scheme with `clientCredentials` flow)
- QUERY method candidates extension (`x-query-method-candidates` — RQ-1 verdict: HOLD)
- Task model schema injection (webhook definition via `Task.model_json_schema()`)
- Fleet registry type injection (`SuccessResponse`, `ErrorResponse`, `ErrorDetail`)

**Security scheme tags**: `_PAT_TAGS` (tasks/projects/sections/users/workspaces/dataframes/offers/workflows/exports), `_S2S_TAGS` (resolver/query/admin/internal/entity-write/intake-resolve/intake-custom-fields/intake-create/matching), `_TOKEN_TAGS` (webhooks), `_NO_AUTH_TAGS` (health). Strategy: `FAIL_CLOSED` with `fail_on_unknown=True`.

### FleetQuery Adapter (`api/fleet_query_adapter.py`)

Translates `autom8y_api_schemas.FleetQuery` → `EntityQueryService.query()` kwargs. `FleetQuery.filters` is permissive `dict[str, Any]`; `entity_type` and optional `select` are expected inside filters. `FleetQuery.limit/offset` maps 1:1. Returns `PaginationMeta` built from request limit/offset + post-execution `total_count` (§7.3 pagination round-trip invariant). Adapter-only — does NOT touch `QueryEngine`, `EntityQueryService`, or legacy routes.

### Exception Handling (`api/errors.py`)

14 specific handlers registered before the catch-all (most-specific-first via `register_exception_handlers`):
- SDK errors: `NotFoundError` (404), `AuthenticationError` (401 + `WWW-Authenticate`), `ForbiddenError` (403), `RateLimitError` (429 + `Retry-After`), `GidValidationError` (400), `ServerError` (502), `TimeoutError` (504)
- Network: `RequestError` (502)
- Generic SDK: `AsanaError` (500)
- API-layer typed: `ApiAuthError` (401), `ApiServiceUnavailableError` (503), `ApiDataFrameBuildError` (503), `ApiError` (catch-all)
- Core: `HTTPException` (prevents double-wrapping of `detail` dict), `Exception` (500 catch-all)
- Fleet: `FleetError` → `fleet_error_to_response()` (WS-B1+B2 P1-D, canonical `ASANA-<CATEGORY>-NNN` codes)

All error responses include `request_id` from `request.state.request_id`. `raise_api_error()` and `raise_service_error()` are the canonical helpers for route-layer errors (ADR-I6-001).

## Implementation Map

| File | Role |
|------|------|
| `api/main.py` | `create_app()` factory; 22 routers; OpenAPI enrichment; security tag sets; OAuth2 scope pilot; middleware wiring |
| `api/lifespan.py` | 13-step startup + shutdown; cache warm background task; connection registry teardown |
| `api/startup.py` | `_discover_entity_projects`, `_initialize_dataframe_cache`, `_register_schema_providers`, `_initialize_mutation_invalidator` |
| `api/preload/progressive.py` | Progressive cache warm: cascade-phased, parallel, S3/Lambda/cold-start paths, L2 gate, heartbeat |
| `api/preload/legacy.py` | Legacy in-memory preload (degraded-mode fallback when S3 unavailable per ADR-011) |
| `api/preload/constants.py` | `PROJECT_CONCURRENCY`, `HEARTBEAT_INTERVAL_SECONDS`, `PRELOAD_EXCLUDE_PROJECT_GIDS` |
| `api/dependencies.py` | `get_auth_context()` (dual-mode DI), `AuthContext`, `EntityServiceDep`, `DataServiceClient` injection |
| `api/client_pool.py` | `ClientPool` (LRU, SHA-256 keyed); `_PooledClientWrapper` (no-op aclose) |
| `api/fleet_query_adapter.py` | FleetQuery → EntityQueryService translation; `PaginationMeta` round-trip |
| `api/middleware/core.py` | `RequestIDMiddleware`, `RequestLoggingMiddleware`, `_filter_sensitive_data` |
| `api/middleware/idempotency.py` | `IdempotencyMiddleware`; `DynamoDBIdempotencyStore`, `InMemoryIdempotencyStore`, `NoopIdempotencyStore`; `StoredResponse` |
| `api/routes/health.py` | `/health` (liveness), `/ready` (4-check readiness), `/health/deps` (JWKS+PAT); `set_cache_ready()`, `set_workflow_configs_registered()` |
| `api/routes/_security.py` | `pat_router`, `s2s_router` factory helpers |
| `api/errors.py` | `register_exception_handlers()`; 14 specific handlers; `raise_api_error()`, `raise_service_error()`, `fleet_error_handler` |
| `api/exception_types.py` | `ApiError`, `ApiAuthError`, `ApiServiceUnavailableError`, `ApiDataFrameBuildError` typed exception hierarchy |
| `api/models.py` | Re-exports `SuccessResponse`, `ErrorResponse`, `ErrorDetail`, `PaginationMeta`; adds `ExportsSuccessResponse` |
| `api/health_models.py` | `CheckResult`, `HealthStatus`, `liveness_response()`, `readiness_response()`, `deps_response()` |
| `api/rate_limit.py` | SlowAPI `Limiter` singleton; keyed by PAT prefix or remote IP |
| `api/metrics.py` | `PrometheusMetricsEmitter`; domain-specific Prometheus metric registrations |
| `api/config.py` | `get_settings()` (API-layer settings alias) |
| `api/routes/*.py` | 20 route handler files; co-located `*_models.py` contain Pydantic request/response models |
| `entrypoint.py` | ECS/Lambda mode detection; `run_ecs_mode()` → uvicorn; `run_lambda_mode(handler)` → awslambdaric |

**Test locations**: `tests/unit/api/` (unit tests for route handlers, middleware, dependencies), `tests/integration/api/` (integration tests), `tests/test_openapi_fuzz.py` (OpenAPI spec fuzz, `xdist_group` marker per SCAR-W1E-LOADGROUP-001).

## Boundaries and Failure Modes

### Critical Invariants

1. **Shared cache provider** — single `create_cache_provider()` in lifespan step 4, injected into `ClientPool` and all request-handler clients (DEF-005; SCAR-004 origin: isolated instances made warm-up data invisible to request handlers)
2. **Liveness vs readiness separation** — `/health` always 200, zero I/O; `/ready` checks 4 dependencies; never mix (SCAR-011/011b)
3. **Router registration order** — `intake_resolve_router` BEFORE `resolver_router`; `fleet_query_router_*` and `exports_router_*` BEFORE `query_router` (LBC-011, TENSION-009; FastAPI matches first registration)
4. **`_PooledClientWrapper.aclose()` is no-op** — prevents FastAPI dependency teardown from closing pooled client state
5. **Cascade ordering fail-fast** — `validate_cascade_ordering()` at step 13 raises `ValueError` on `warm_priority` graph conflict; `WarmupOrderingError` in preload is NEVER caught by `BROAD-CATCH` handlers
6. **Idempotency finalize failure risk** — SCAR-IDEM-001: if `finalize()` throws, key is NOT persisted; client retry will re-execute mutation (acceptable for idempotent callers; risk for strict-once S2S)
7. **PAT route exclusions** — PAT route tree paths MUST be in `jwt_auth_config.exclude_paths` (SCAR-WS8); omission causes JWT middleware to reject valid PAT requests
8. **`ExportOptions.extra="allow"`** — P1-C-02 BINDING; must NOT change to `"forbid"` (TENSION-010; Phase 2 `predicate_join_semantics` escape valve)

### Active Scars

| SCAR | Location | Risk |
|------|----------|------|
| SCAR-004 | `api/lifespan.py` step 4 (resolved) | Cache split between warm-up and handlers if `create_cache_provider()` called per-client |
| SCAR-011/011b | `api/routes/health.py` | `/health` vs `/ready` confusion causes ECS health check misconfiguration |
| SCAR-015 | `api/routes/section_timelines.py` (resolved) | Per-request Asana I/O exceeded ALB 60s at ~3,800 offers |
| SCAR-022 | `Dockerfile` | `uv sync --frozen --no-sources` incompatible with uv >=0.15.4; resolved by constraint |
| SCAR-IDEM-001 | `api/middleware/idempotency.py:719` | `finalize()` exception silently swallowed; retry re-executes mutation |
| SCAR-WS8 | `api/main.py:389` (active) | PAT route trees require explicit `jwt_auth_config.exclude_paths` entries |

### Design Tensions

| Tension | Location | Impact |
|---------|----------|--------|
| TENSION-002 | `services/intake_*_service.py` importing `api/routes/*_models.py` | Layer boundary violation; services depend on API models |
| TENSION-008 | `auth/dual_mode.py:24`, `cache/dataframe/decorator.py:147` | Auth + cache layers have runtime dependency on `api/exception_types.py` |
| TENSION-009 | `api/main.py:431-441` | Exports + FleetQuery routers MUST mount before `query_router`; not structurally enforced |
| TENSION-010 | `api/routes/exports.py:141` | `ExportOptions.extra="allow"` binding constraint for Phase 2 |

### Scope Boundaries (What This Feature Does NOT Do)

- Does NOT implement business logic — all in service/client layers below
- Does NOT manage DynamoDB table provisioning — external CDK/Terraform
- Does NOT run the Lambda handlers — separate `entrypoint.py` Lambda path dispatches those
- Rate limiting is **single-instance only** (in-memory SlowAPI) — no Redis multi-instance config
- IdempotencyMiddleware does NOT check request fingerprint for `PATCH` vs `POST` method mismatch — only body fingerprint
- OAuth2 scopes are DOCUMENTATION-ONLY — no runtime enforcement in Sprint 6

### Configuration Boundaries

Key environment variables affecting this feature:
- `AWS_LAMBDA_RUNTIME_API` — mode detection (absent = ECS, present = Lambda)
- `IDEMPOTENCY_STORE_BACKEND` — `dynamodb` (default) / `memory` / `noop`
- `IDEMPOTENCY_TABLE_NAME` — DynamoDB table (default: `autom8-idempotency-keys`)
- `IDEMPOTENCY_TABLE_REGION` — AWS region (default: `us-east-1`)
- `AUTH_JWKS_URL` — JWKS endpoint for `/ready` deep probe (default: `https://auth.api.autom8y.io/.well-known/jwks.json`)
- `ASANA_PAT` — bot PAT; checked in `/ready` (≥10 chars), used in progressive preload
- `CACHE_WARMER_LAMBDA_ARN` — if set, cold-start projects delegate warm to Lambda; in production, absence means skip
- `PRELOAD_EXCLUDE_PROJECT_GIDS` (constant, not env) — set of project GIDs to skip during warm-up
- `CORS_ORIGINS` (via `settings.cors_origins_list`) — comma-separated; CORS disabled if empty

```metadata
observation_method: direct_source_read
files_read: 12 (main.py, lifespan.py, startup.py, preload/progressive.py, routes/health.py, middleware/idempotency.py, client_pool.py, dependencies.py, errors.py, fleet_query_adapter.py, middleware/core.py, entrypoint.py)
supporting_files_read: .know/architecture.md, .know/scar-tissue.md, .know/design-constraints.md (partial)
architecture_seed_hash: 8980bcd7
prior_knowledge_hash: c213958
gaps_closed: startup.py behavior (fully read), preload/progressive.py cascade-phased warm (fully read), errors.py complete exception mapping (fully read), /ready 4-check expansion (SP-L3-1 D4), OAuth2 scope pilot (Sprint 6 Track D), SecurityHeadersMiddleware addition (WS-B1+B2 P1-D)
remaining_gaps:
  - rate_limit.py: key derivation detail (PAT prefix vs remote IP) not traced to exact line
  - DynamoDB table schema provisioning not in codebase (external CDK/Terraform, confirmed)
  - api/metrics.py: full Prometheus metric names not inventoried
```
