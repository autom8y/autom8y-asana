---
domain: api
generated_at: "2026-10-05T03:08:24Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/__init__.py"
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/config.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./src/autom8_asana/errors.py"
  - "./src/autom8_asana/settings.py"
  - "./src/autom8_asana/storage_namespace.py"
  - "./mcp/asana_mcp/__init__.py"
  - "./mcp/asana_mcp/assembly.py"
  - "./mcp/asana_mcp/bridge.py"
  - "./mcp/asana_mcp/context.py"
  - "./mcp/asana_mcp/envelopes.py"
  - "./mcp/asana_mcp/errors.py"
  - "./mcp/asana_mcp/observability.py"
  - "./mcp/asana_mcp/schemas.py"
  - "./mcp/asana_mcp/server.py"
  - "./mcp/asana_mcp/settings.py"
  - "./mcp/asana_mcp/timeouts.py"
  - "./mcp/canary/test_broken_fixture_canary.py"
  - "./mcp/probes/c2_sandbox_reput_probe.py"
  - "./mcp/tests/conftest.py"
  - "./mcp/tests/test_assembly_floor.py"
  - "./mcp/tests/test_bridge_401_fail_clean.py"
  - "./mcp/tests/test_budget_partition_and_rate_cap.py"
  - "./mcp/tests/test_cold_frame_mapping.py"
  - "./mcp/tests/test_composite_write_s3.py"
  - "./mcp/tests/test_confirm_gate_rb1.py"
  - "./mcp/tests/test_discovery_tools.py"
  - "./mcp/tests/test_errors_c3.py"
  - "./mcp/tests/test_errors_passthrough.py"
  - "./mcp/tests/test_errors_substrate_424.py"
  - "./mcp/tests/test_fences.py"
  - "./mcp/tests/test_honesty_passthrough.py"
  - "./mcp/tests/test_import_safety_obs.py"
  - "./mcp/tests/test_import_safety.py"
  - "./mcp/tests/test_instrument_seam.py"
  - "./mcp/tests/test_postures.py"
  - "./mcp/tests/test_query_tools.py"
  - "./mcp/tests/test_readiness_gate.py"
  - "./mcp/tests/test_resolve_tool.py"
  - "./mcp/tests/test_schema_canary.py"
  - "./mcp/tests/test_seam_conformance.py"
  - "./mcp/tests/test_span_and_traceparent.py"
  - "./mcp/tests/test_tag_dual_key_wsb2.py"
  - "./mcp/tests/test_timeout_cascade_invariant.py"
  - "./mcp/tests/test_workflows_disclosure.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "6a8debe2b2650bf405b8e8a3a03e3c969e935410abcd9c5b1c21410fbd76784d"
confidence: 0.85
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@c29f58f4"
---

# Codebase API Surface

> Fresh full-observation pass at `origin/main` `c29f58f4` (2026-10-04), read from the detached worktree only. Surface = (1) the FastAPI satellite REST API (`src/autom8_asana/api/`, built by `create_app()` at `src/autom8_asana/api/main.py:378`, which calls `create_fleet_app(` at `main.py:481`) and (2) the `mcp/asana_mcp/` FastMCP sidecar tool surface. Framework: Python / FastAPI via the fleet `create_fleet_app()` factory. **Reconciled counts (own AST pass over `api/routes/*.py`): 28 `RouterMount`s (`main.py:490-531`), 72 route decorators (= 72 operations), 49 spec paths / 58 spec operations; 72 - 14 hidden (`include_in_schema=False`) = 58, so spec-vs-code drift = 0.**

## Route Inventory

**Mount mechanics.** All routers are mounted in one list passed to `create_fleet_app(routers=[RouterMount(...)])` (`main.py:489-531`; 28 mounts). Registration order is load-bearing in two places: `intake_resolve_router` (`main.py:503`) before `resolver_router` (`main.py:504`) ( comment: explicit paths before the `/v1/resolve/{entity_type}` wildcard) and fleet `/v1/query/entities` before the legacy `/v1/query/{entity_type}` wildcard, enforced at startup by `_assert_fleet_query_mount_order` (`main.py:350`, invoked `main.py:556`; TENSION-009). Two routers are created with a raw `APIRouter` (health `routes/health.py:46`, webhooks `routes/webhooks.py:126`); every other router is a `SecureRouter` from `pat_router()` / `s2s_router()` (`routes/_security.py:37-50`). `internal_router` is mounted (`main.py:500`) but **`routes/internal.py` declares zero route decorators** — it only hosts `ServiceClaims` and `require_service_claims` (`internal.py:33,118`); prior note "internal ops" was wrong.

**Versioning.** Two coexisting namespaces: `/api/v1/*` (resource-facing, PAT-tag routers that are really dual-mode PAT+JWT at the DI layer) and `/v1/*` (S2S-JWT, fleet-facing). `exports` and fleet-query are deliberately dual-mounted under both prefixes (`exports.py:230-236`, `fleet_query.py:73-82`). A few S2S hidden routes live under `/api/v1/` (`/api/v1/entity`, `/api/v1/query/entities`, `/api/v1/internal`). No `/v2`.

Auth column legend: **PAT*** = `pat_router` + `AsanaClientDualMode`/`AuthContextDep` (accepts PAT *or* S2S JWT in `get_auth_context`, `dependencies.py:134`); **S2S** = `s2s_router` + `require_service_claims` (PAT rejected with `SERVICE_TOKEN_REQUIRED`, `internal.py:141-152`); **WG** = also carries `require_write_authz(WriteClass.X)` (see Auth section). `Spec` = appears in `docs/api-reference/openapi.json`.

| Router (file) | Method path | Decorator | Auth | Spec | Notes |
|---|---|---|---|---|---|
| health (`health.py`) | GET `/health` | :188 | none | yes | liveness, no I/O |
| | GET `/ready` | :217 | none | yes | cache/workflow_configs/jwks/bot_pat; 503 while warming |
| | GET `/health/deps` | :406 | none | yes | jwks + bot PAT probe |
| users | GET `/api/v1/users/me`, `/{gid}`, `/` | :42,:69,:98 | PAT* | yes | 3 ops |
| workspaces | GET `/api/v1/workspaces`, `/{gid}` | :41,:101 | PAT* | yes | 2 |
| dataframes | GET `/api/v1/dataframes/schemas`, `/schemas/{name}`, `/project/{gid}`, `/section/{gid}` | :373,:431,:502,:623 | PAT* | yes | JSON / Polars via `Accept` |
| tasks | GET `/api/v1/tasks`, `/{gid}`, `/{gid}/subtasks`, `/{gid}/dependents` | :75,:133,:361,:418 | PAT* | yes | reads |
| | POST `/`, PUT `/{gid}`, DELETE `/{gid}`, POST `/{gid}/duplicate`, POST `/{gid}/tags`, DELETE `/{gid}/tags/{tag_gid}`, POST `/{gid}/section`, PUT `/{gid}/assignee`, POST `/{gid}/projects`, DELETE `/{gid}/projects/{project_gid}` | :183,:246,:311,:476,:532,:583,:636,:690,:739,:789 | PAT* + WG(TASKS) | yes | 10 writes; 14 ops total (largest) |
| tags | GET `/api/v1/tags` | :48 | PAT* | yes | list or `?name=` resolve |
| projects | GET `/`, `/{gid}`, `/{gid}/sections`; POST `/`, `/{gid}/members`; PUT `/{gid}`; DELETE `/{gid}`, `/{gid}/members` | :107,:168,:374,:213,:458,:264,:328,:505 | PAT* ; writes WG(PROJECTS) at :227,:277,:341,:471,:518 | yes | 8 ops |
| sections | GET `/{gid}`; POST `/`, `/{gid}/tasks`, `/{gid}/reorder`; PUT `/{gid}`; DELETE `/{gid}` | :51,:89,:242,:295,:140,:191 | PAT* ; writes WG(SECTIONS) :103,:153,:204,:255,:308 | yes | 6 ops |
| section_timelines | GET `/api/v1/offers/section-timelines` | :124 | PAT* | yes | no scope rule in `_SCOPE_RULES` |
| workflows | GET `/api/v1/workflows/` | :230 | PAT* (see gap G-1) | yes | disclosure oracle |
| | POST `/api/v1/workflows/{workflow_id}/invoke` | :260 | PAT* + WG(WORKFLOWS) + `@limiter.limit("10/minute")` (:282) | yes | 120 s timeout, audit-logged |
| exports | POST `/v1/exports` | :604 | S2S | yes | `exports_router_v1` |
| | POST `/api/v1/exports` | :636 | PAT* | yes | `exports_router_api_v1`; `ExportRequest` json/csv/parquet |
| query (introspection) | GET `/v1/query/entities`, `/data-sources`, `/data-sources/{factory}/fields`, `/{entity_type}/fields`, `/{entity_type}/relations`, `/{entity_type}/sections` | :118,:145,:171,:215,:246,:273 | S2S | yes | `query_introspection_router` (`query.py:83`) |
| query (exec) | POST `/v1/query/{entity_type}/rows`, `/{entity_type}/aggregate` | :321,:565 | S2S | **hidden** | `router` (`query.py:84`); rows carries `@limiter.limit(SA_NAMESPACE_LIMIT)` (:329) |
| fleet_query | POST `/v1/query/entities`, POST `/api/v1/query/entities` | :221,:252 | S2S | **hidden** | FleetQuery DSL adapter |
| resolver | POST `/v1/resolve/{entity_type}` | :154 | S2S | yes | max 1000 criteria (`resolver_models.py:157`) |
| resolver_schema | GET `/v1/resolve/{entity_type}/schema`, `/schema/enums/{field_name}` | :146,:375 | S2S | yes | included under resolver router (`resolver.py:93`) |
| intake_resolve | POST `/v1/resolve/business`, `/contact`, `/business-by-email` | :79,:237,:347 | S2S | **hidden** | mounted before resolver wildcard |
| intake_create | POST `/v1/intake/business` (201), `/v1/intake/route` | :62,:200 | S2S + WG(INTAKE) (:73,:210) | **hidden** | idempotency-eligible |
| intake_custom_fields | POST `/v1/tasks/{task_gid}/custom-fields` | :47 | S2S + WG(INTAKE) :57 | **hidden** | idempotency-eligible |
| entity_write | PATCH `/api/v1/entity/{entity_type}/{gid}` | :185 | S2S + WG(INTAKE) :195 | **hidden** | idempotency-eligible |
| receipts | POST `/v1/receipts` | :86 | S2S + WG(RECEIPTS) :99 | **hidden** | comment-thread receipt |
| matching | POST `/v1/matching/query` | :56 | S2S | **hidden** | read-only scoring |
| forwarding_stage_census | GET `/v1/forwarding-stage/census` | :94 | S2S | yes | read; typed 502 refusals |
| identity_supply | GET `/v1/identity-supply/{offer_gid}` | :128 | S2S | yes | read; `x-fleet-read-only` |
| admin | POST `/v1/admin/cache/refresh` (202) | :414 | S2S + inline `admin:access` permission check (`admin.py:39,456`) | **hidden** | background Lambda/cache refresh |
| webhooks | POST `/api/v1/webhooks/inbound` | :392 | `?token=` URL token, timing-safe `hmac.compare_digest` (`webhooks.py:209,257`) | yes | documented in spec `webhooks.asanaTaskChanged` (`main.py:895`) |

**Classification totals (72 ops):** none/public 3; URL-token 1; PAT* 42 (tasks 14, projects 8, sections 6, dataframes 4, users 3, workspaces 2, workflows 2, exports-api 1, tags 1, offers 1); S2S 26 (12 in spec + 14 hidden). **Hidden 14** = admin 1, entity_write 1, fleet_query 2, intake_create 2, intake_custom_fields 1, intake_resolve 3, matching 1, query-exec 2, receipts 1. Everything hidden is S2S. Prior pass counted 69 decorators / 47 paths / 56 ops. Spec delta +2 ops / +2 paths is exactly `forwarding_stage_census` (`/v1/forwarding-stage/census`, commit 140f9bfc #401) and `identity_supply` (`/v1/identity-supply/{offer_gid}`, commit d75bfe1a); the extra +1 in the decorator count is not attributable to a named commit (likely a prior undercount of hidden routers).

**Dead-letter router:** `internal_router` has no operations; `internal` is in `_S2S_TAGS` (`main.py:122-137`) and `_SCOPE_RULES` but classifies nothing.

## MCP tool surface (`mcp/asana_mcp/`)

FastMCP process; "routes" are tool registrations. `create_server()` (`server.py:33`) registers **6 read tools**: `list_entity_types`, `describe_entity` (`tools/discovery.py:55-74`, over `GET /v1/query/entities` and `/v1/query/{et}/fields|relations|sections`, `discovery.py:21-41`), `query_rows`, `query_aggregate` (`tools/query.py:42-64`, over `POST /v1/query/{et}/rows|aggregate`, `query.py:25,35`), `resolve_entity` (`tools/resolve.py:39-47`, `POST /v1/resolve/{et}`, `resolve.py:24`), `list_report_workflows` (`tools/workflows.py:104-117`, `GET /api/v1/workflows/` — trailing slash load-bearing, `workflows.py:46`; never invokes). `assembly.py:build_instrumented_server` then calls `composite_write.register`, which attaches the 7th tool `asana_complete_tagged_task` **only if** `ASANA_MCP_ENABLE_WRITE_SURFACE` is truthy (default OFF; `composite_write.py:98-112,458`). `match_business` is a deliberately inert stub (`tools/_match_business_stub.py:23`). Correction vs prior: the surface is 6 always-on + 1 gated = 7 registrable tools (not 8); `assembly.py` docstring still says "exactly the five READ tools" (stale).

**RB-1 confirm gate** (`tools/confirm_gate.py`): `DEFAULT_CONFIRMATION_TTL_S = 600.0` (:49); a call without `confirmation_token` returns a `confirmation_required` envelope with zero backend calls (`composite_write.py:485-500`); token is issued by `ConfirmationGate.issue` (:128), redeemed with an intent fingerprint (`redeem` :138; `intent_fingerprint` :78).

**Composite write route chain** (`composite_write.py:208-221`): `POST /api/v1/tasks/{gid}/tags`, `PUT /api/v1/tasks/{gid}` (save), `PUT /api/v1/tasks/{gid}` (`completed:true`). These are the PAT-tag, JWT-accepting task routes and therefore hit `require_write_authz(WriteClass.TASKS)` (`tasks.py:545,:259`) with the sidecar's S2S principal — they succeed only if that principal is allowlisted (or the deployed mode is observe). Name->GID resolution uses `GET /api/v1/tags` (`tag_resolve.py:52`).

MCP-side contracts: `envelopes.py:unwrap_outer` strips the satellite `{data}` envelope; `errors.py` `McpToolError(kind,status,retryable,code)`; `bridge.py:_classify_mint_failure` maps `InvalidServiceKeyError` -> 401 non-retryable `S2S_MINT_CREDENTIALS_INVALID`, `TokenAcquisitionError` -> 503 retryable `S2S_MINT_UNAVAILABLE` (`bridge.py:27,48,61`). Readiness probe proxies satellite `/ready`, fail-closed by default (`bridge.py:129` `make_readiness_probe`; `settings.py` `readiness_fail_open=False`). Base URL default `https://asana.api.autom8y.io` (`settings.py`), env `ASANA_MCP_BASE_URL` / `AUTOM8Y_ASANA_URL`.

## Authentication & Authorization Model

**Layered chain (entry -> handler).** Outermost-first app middleware order is set in `create_app`: fleet stack from `create_fleet_app` (CORS, `JWTAuthMiddleware`, rate-limit, `IdempotencyMiddleware` via `extra_middleware`, `main.py:481-541`), then `SecurityHeadersMiddleware` (`main.py:579`), then `RequestIDMiddleware` (`main.py:592`, sole writer of `request.state.request_id`; `middleware/core.py:93`), then `instrument_app` (`main.py:941`). Request-ID is trusted from `x-request-id` header or minted (16 hex chars).

1. **Layer 1 — `JWTAuthMiddleware`** (`autom8y_auth` package, `middleware.py:116,182-250`; configured at `main.py:453-478`). Non-excluded paths REQUIRE a valid JWT (`validate_from_header`) else AUTH-TEB error envelope; `require_business_scope=True` (`main.py:478`) adds ADR-07 precedence (bypass claim -> `business_id` -> 400 AUTH-TEB-004). **Excluded** (optional token, failures ignored): `DEFAULT_EXCLUDE_PATHS` + `/redoc`, `/api/v1/webhooks/*`, `/api/v1/tasks|projects|sections|users|workspaces|dataframes|offers|exports|tags/*` (`main.py:453-478`). So the PAT-tag trees skip middleware JWT enforcement and rely on layer 2; every `/v1/*` route and the hidden `/api/v1/{entity,query,internal}` routes are JWT-enforced by BOTH layers.
2. **Layer 2 — DI.** `get_auth_context` (`dependencies.py:134`) calls `detect_token_type`: PAT -> `AuthContext(mode=PAT, asana_pat=token)` pass-through (`dependencies.py:174`); JWT -> `validate_service_token` (`auth/jwt_validator.py`) with typed failures: `CircuitOpenError`/`TransientAuthError` -> 503, `PermanentAuthError`/`AuthError`/pydantic `ValidationError` -> 401 `INVALID_TOKEN`; then bot PAT from `get_bot_pat()` (`BotPATError` -> 503 `S2S_NOT_CONFIGURED`) and `AuthContext(mode=JWT, asana_pat=bot_pat, caller_service, claims)` (`dependencies.py:291`). `_extract_bearer_token` requires `Bearer ` and length >= 10 (`dependencies.py:103-131`). Token -> Asana client via token-keyed `ClientPool` (`client_pool.py:74`; max 100, S2S TTL 3600 s, PAT TTL 300 s).
3. **S2S-only routes** add `require_service_claims` (`internal.py:118`): rejects PAT (`SERVICE_TOKEN_REQUIRED`), validates JWT, returns local `ServiceClaims{sub, service_name, scope, permissions, client_id}` (`internal.py:33-82`; `scope` is logging-only).

**OpenAPI security schemes** (`main.py:633-675`, `OAuth2Asana` added in `custom_openapi`, `main.py:609+`): `PersonalAccessToken` (http bearer), `ServiceJWT` (http bearer JWT), `WebhookToken` (apiKey in query `token`), plus documentation-only `OAuth2Asana` clientCredentials (tokenUrl `https://auth.api.autom8y.io/oauth/token`, 18 scopes `_OAUTH2_SCOPE_DEFINITIONS` `main.py:154`; per-op mapping `_SCOPE_RULES` `main.py:182`; **not enforced at runtime**). Tag->scheme classification is FAIL_CLOSED with `fail_on_unknown=True` over `_PAT_TAGS` (`main.py:99`), `_S2S_TAGS` (`main.py:122`), `_TOKEN_TAGS` (`main.py:119`), `_NO_AUTH_TAGS` (`main.py:140`). Verified against the committed spec: PAT ops list `[{PersonalAccessToken},{OAuth2Asana:[scope]}]`, S2S ops `[{ServiceJWT},{OAuth2Asana}]`, webhook `[{WebhookToken},...]`, health `[]`; `/api/v1/offers/section-timelines` has PAT only (no `_SCOPE_RULES` prefix for `/api/v1/offers`). Stale scope rules: `("/v1/entity-write", ...)` and `("/v1/internal", ...)` (`main.py:223-224`) match no real path (actual prefixes `/api/v1/entity`, `/api/v1/internal`) — harmless because the routes are hidden and the table is documentation-only.

**Public / webhook.** `/health`, `/ready`, `/health/deps` — no auth (`health.py:188,217,406`). Webhook: `verify_webhook_token` (`webhooks.py:209`) compares `?token=` to `settings.webhook.inbound_token` with `hmac.compare_digest` (:257); unset token -> 503 `AsanaWebhookNotConfiguredError`; missing/wrong -> 401 `ASANA-AUTH-002`-family with `WWW-Authenticate: URLToken`. SC-02 exemption comment at `webhooks.py:124`. **Dispatcher is a no-op:** `NoOpDispatcher` (`webhooks.py:165`) is the module default `_dispatcher` (:184); `set_dispatcher` (:187) is defined but has **zero callers in `src/`** (grep over `src` finds only the definition), so `autom8_asana/lifecycle/webhook_dispatcher.py:85` (the real lifecycle dispatcher "replacing NoOpDispatcher") is never installed; background work is cache invalidation only (`_process_inbound_task`, `webhooks.py:356`, scheduled at `:509`). Empty body -> 200 ignored; non-JSON -> 400 `ASANA-VAL-*`; no `gid` -> 400.

**Write-class authorization (SEC-001, RE-2) — `api/write_authz.py`.**
- Six `WriteClass` values: `tasks:write`, `projects:write`, `sections:write`, `intake:write`, `receipts:write`, `workflows:execute` (`write_authz.py:100-108`), each with allowlist env `ASANA_WRITERS_{TASKS,PROJECTS,SECTIONS,INTAKE,RECEIPTS}_WRITE` / `ASANA_WRITERS_WORKFLOWS_EXECUTE` (`ALLOWLIST_ENV`, `write_authz.py:135-142`). Mode env `ASANA_WRITE_AUTHZ_MODE` (`MODE_ENV` :128).
- **Code default is ENFORCE and fails closed**: unset/empty/malformed mode -> ENFORCE; only the literal `observe` selects OBSERVE (`resolve_mode`); an unset/empty/malformed allowlist -> empty set -> deny-all (`load_writer_allowlist`, `is_authorized`). There is no wildcard; `*` is just a principal name. Authorization is deliberately NOT keyed on `scope` (the `has_scope` `scope=="*"` fail-open); principal precedence is `service_account_id` (from `request.state.claims_dict`) > `client_id` > `service_name`/`sub` (`resolve_principal`).
- In OBSERVE the decision is logged as `write_authz_would_deny` and the request proceeds; in ENFORCE a denied principal gets 403 `INSUFFICIENT_PRIVILEGE` (`authorize_write`; `DENIED_ERROR_CODE`).
- **PAT callers are exempt by design**: `_write_authz_gate` returns early when `auth_context.mode == AuthMode.PAT` (`write_authz.py:414-418`); only the JWT branch (lent the shared bot PAT) is gated.
- **Gated routes: 26 of 72 ops** (decorator `dependencies=[Depends(require_write_authz(...))]`): tasks 10 (`tasks.py:197,259,324,490,545,595,648,702,751,801`), projects 5 (`projects.py:227,277,341,471,518`), sections 5 (`sections.py:103,153,204,255,308`), intake_create 2 (`:73,:210`), intake_custom_fields 1 (`:57`), entity_write 1 (`:195`), receipts 1 (`:99`), workflows invoke 1 (`workflows.py:280`). Not gated by this module: `POST /v1/admin/cache/refresh` (separate inline `admin:access` permission check, `admin.py:39`), webhooks (token), all reads.
- **The deployed mode and allowlists are NOT declared anywhere in this repo.** `grep` for `ASANA_WRITE_AUTHZ_MODE` / `ASANA_WRITERS_*` over the main worktree finds only `write_authz.py`, `tests/conftest.py:235-253` (tests run ENFORCE with `_TEST_WRITE_PRINCIPALS="autom8_data,email_booking_intake,dev-bypass-service"`), and `.ledge/reviews/RECEIPT-re2-devs-1-4-2026-08-23.md:291-300` (operator paths: shadow-first via `observe`, or configure-first). Therefore: with the allowlists unset, a deploy in the code-default ENFORCE denies every S2S write; a deploy in `observe` lets them through while logging `would_deny`. The live setting is environment state (ECS task definition), not recoverable from code. [UV-P: live mode; METHOD: read ECS task-def env / CloudWatch `write_authz_would_deny` count; REASON: not in the repo.] Operator memory (2026-09 "300 would_deny in 7d, mode:observe, empty allowlists") is consistent with observe being set outside the repo but is not code evidence.
- Test guards: `tests/unit/api/test_write_authz.py`, `tests/unit/api/test_write_authz_coverage.py` (GUARD-2 coverage/axis drift guard).

**Other cross-cutting controls.**
- **Rate limiting** (`rate_limit.py`): slowapi `limiter` (`:225`, in-memory storage per instance, `:217-219`), global `settings.rate_limit_rpm` per minute as default limit (`:202-214`; field `config.py:56`), key func `_get_rate_limit_key` (`:161`) keys SA tokens by namespace; `SA_RATE_LIMIT_NAMESPACE = "sa:asana-dataframe-resolver"`, `SA_RATE_LIMIT_RPM = 600` (`:65-66`) applied by decorator only at `query.py:329` (rows) and an explicit `10/minute` on workflow invoke (`workflows.py:282`). 429 handler wrapped to emit per-namespace metric (`errors.py:723`).
- **Idempotency** (`middleware/idempotency.py:64-67`): `IDEMPOTENT_ENDPOINTS` = exactly 4 `(method, path-template)` pairs — `POST /v1/intake/business`, `POST /v1/intake/route`, `POST /v1/tasks/{task_gid}/custom-fields`, `PATCH /api/v1/entity/{entity_type}/{gid}`. Additive: requests without `Idempotency-Key` pass through; header allowed chars `[a-zA-Z0-9-_.]`, min/max length enforced (`:453-459`); backend chosen in `create_app` by `IDEMPOTENCY_STORE_BACKEND` (`dynamodb` default / `memory` / `noop`; DynamoDB failure degrades to Noop with a warning, `main.py:400-436`). Note `POST /v1/receipts` is idempotent by content marker, not by this middleware (`receipts.py:94`).
- **CORS**: `ASANA_API_CORS_ALLOWED_ORIGINS` (`api/config.py:7,49`); allowed headers `Authorization, Content-Type, X-Request-ID, Idempotency-Key` (`main.py:440-448`); CORS only enabled when origins non-empty.
- **Security headers**: `SecurityHeadersMiddleware` from `autom8y_api_schemas.middleware` (HSTS, X-Frame-Options, nosniff, Referrer-Policy, `Cache-Control: no-store`; `main.py:579`).

**Gaps in the auth model.**
- **G-1 (code-derived, runtime unverified): `/api/v1/workflows*` is PAT-tagged but NOT in the JWT exclude list.** `_PAT_TAGS` contains `workflows` (`main.py:99-112`) and the tag description says "Requires PAT Bearer authentication" (`main.py:324`), but the `exclude_paths` list (`main.py:453-478`) omits `/api/v1/workflows/*` (it lists tasks, projects, sections, users, workspaces, dataframes, offers, exports, tags, webhooks). Per `JWTAuthMiddleware.dispatch`, a non-excluded path with a non-JWT bearer returns an AUTH-TEB error before DI. Net effect from code: workflows is reachable by S2S JWT (what the MCP sidecar uses, `tools/workflows.py:46`) but a raw Asana PAT would be rejected at the middleware despite documentation. `tests/unit/api/routes/test_workflows.py:190-222` sends a fake bearer with `get_auth_context` overridden, so it does not exercise this. [UV-P: live PAT-to-workflows behaviour; METHOD: curl with a real PAT; REASON: requires a deployed instance.]
- Dual-mode routes admit any valid fleet JWT, which borrows the single shared bot PAT; write-class gating (above) is the only per-service control, and PAT-mode requests bypass it.

## Request/Response Contracts

- **Envelope.** Success: `SuccessResponse[T]` = `{data, meta}`; error: `ErrorResponse` = `{error:{code,message,details}, meta}`; both types are re-exported from the shared `autom8y_api_schemas` package at `api/models.py:28-36` (backward-compat path). `meta` is `ResponseMeta{request_id, timestamp, pagination}`. Hidden/handwritten routes still build the same envelope (`errors.py:64-89` `_build_error_response`; `raise_api_error` `errors.py:92`). `http_exception_handler` (`errors.py:448`) unwraps dict `detail` so `HTTPException(detail=<ErrorResponse dict>)` is returned flat; non-dict detail yields the non-canonical `{"detail": ...}`.
- **Error vocabulary.** Handlers registered in `register_exception_handlers` (`errors.py:771`): `NotFoundError`->404, `AuthenticationError`->401, `ForbiddenError`->403, `RateLimitError`->429 (Retry-After), `GidValidationError`->400, `ServerError`->502, `TimeoutError`->504, `RequestError`->502, `AsanaError`->500, `ApiAuthError`/`ApiServiceUnavailableError`/`ApiDataFrameBuildError`/`ApiError` (typed API-layer exceptions, `api/exception_types.py`), `HTTPException`, catch-all `Exception`->500 (detail hidden), plus `FleetError` catch-all (`fleet_error_handler` `errors.py:677`, registered `main.py:605`) emitting canonical `ASANA-<CATEGORY>-NNN` codes with `retryable`/`retry_after_seconds`. RFC-422 validation uses `register_validation_handler(app, service_code_prefix="ASANA")` -> `ASANA-VAL-001` (`main.py:569`). Webhook-specific codes `ASANA-VAL-002/003/004` (invalid JSON / missing gid / non-Task), `ASANA-AUTH-002` (bad token), `ASANA-DEP-002` (token unconfigured) (`webhooks.py:52-104`). Documented error responses are composed by `error_responses.py` (`authenticated_responses` 401/403, `entity_responses` +404, `mutation_responses` +422, `rate_limited_responses` +429); 401/403 are declared `ErrorResponse | AuthTebError` because the JWT middleware emits a different AUTH-TEB-NNN envelope (`error_responses.py:17-32`) — a genuine dual-envelope: two 401 shapes exist depending on which layer rejects.
- **Domain-specific refusals** (typed, intentionally NOT collapsed to zero/200): census `502 STAGE_CENSUS_{TRUNCATED,EMPTY_CORPUS,FIELD_ABSENT,GID_DRIFT}` (`forwarding_stage_census.py:114-128`); identity supply `502 IDENTITY_SUPPLY_BASIS_CONFLICT` / `503 IDENTITY_SUPPLY_UNAVAILABLE` and a typed absence as 200 (`identity_supply.py:141-156`); receipts `404 COMPANY_NOT_RESOLVED` / `409 COMPANY_AMBIGUOUS` (`receipts.py:121-122`); admin `403 INSUFFICIENT_PRIVILEGE`, `400 INVALID_ENTITY_TYPE`, `503 CACHE_NOT_INITIALIZED` (`admin.py:456-500`); entity write `404 TASK_NOT_FOUND`, `422 NO_VALID_FIELDS`, `504 ASANA_TIMEOUT`, `502 ASANA_UPSTREAM_ERROR` (`entity_write.py:129-169`).
- **Pagination — three models.** (1) REST resources (tasks, projects, sections, tags, ...): cursor — `limit` 1-100 (default 100: `DEFAULT_LIMIT=MAX_LIMIT=100`, `tasks.py:68-69`, `tags.py:44-45`) and `offset: str|None` (opaque cursor from `meta.pagination.next_offset`); `ListTasksParams` (`models.py:126-148`) additionally requires exactly one of `project`/`section`. (2) Query engine rows (`/v1/query/{et}/rows`): numeric `limit` 1-10000 (default 100, clamped by server `max_result_rows`) and integer `offset` (`query/models.py:381-391`), `RowsMeta` echoes `limit`/`offset` (`query/models.py:454-462`). (3) FleetQuery: `limit`/`offset` round-trip via `build_pagination_meta` (`fleet_query_adapter.py`, `fleet_query.py` docstring :1-33). Resolver batch: max 1000 criteria (`resolver_models.py:157`).
- **Field naming**: snake_case everywhere in satellite models; GID typing `GidStr` regex `^\d{1,64}$` in production, **relaxed (no pattern) when `AUTOM8Y_ENV` is `test|local|LOCAL`**, evaluated at module import (`models.py:41-54`) — so the spec generated with `AUTOM8Y_ENV=local` (`scripts/generate_openapi.py:20-21`) is the relaxed variant for every `GidStr` field. `identity_supply` uses an unconditional `^[0-9]{1,64}$` Path pattern instead (`identity_supply.py:111`). Extra-field policy: `extra="forbid"` on `EntityWriteRequest` (`entity_write.py:76`) and `ResolutionRequest` (`resolver_models.py:122`).
- **Content types.** JSON default. Dataframes content-negotiate by `Accept`: `application/x-polars-json`, `text/csv`, `application/vnd.apache.parquet` (`dataframes.py:95-98`, ADR-ASANA-005). Exports select via body `format: json|csv|parquet` (`exports.py:116`). Webhook body JSON (full Task). Receipts body bounded: `company_id` <=256, `body` <=16384 chars (`receipts_models.py:35-57`). No multipart/protobuf/gRPC; no WebSocket/SSE routes in `src/` (verified: no `add_api_route`/`WebSocket`/`mount()` registrations outside the listed routers).
- **Machine-readable contract layer.** `openapi_extra` keys `x-fleet-side-effects`, `x-fleet-idempotency`, `x-fleet-rate-limit`, `x-fleet-cross-service-refs`, `x-fleet-read-only` appear 131 times in `src/` (42 `x-fleet-side-effects` in `api/routes`) and 107 times in the committed spec; `/v1/query*` operations get a blanket `x-fleet-idempotency{idempotent:true}` / `x-fleet-side-effects:[]` injected in `custom_openapi` (`main.py:846-851`). `x-query-method-candidates` / `-blocked-by` / `-ready-when` document the HTTP QUERY-method deferral (`main.py:824-831`).
- **MCP contracts**: tool inputs are pydantic (`mcp/asana_mcp/schemas.py` `RowsArgs`, `AggregateArgs`, `ResolveArgs`); outputs are plain dicts with honesty fields (`honest_empty`, `contract_complete`) re-attached after `unwrap_outer` (`envelopes.py`); errors always surface as `McpToolError{kind,status,retryable,code,retry_after}` (`errors.py`).

## Cross-Service Dependencies

**Inbound (who calls this service).**
- Fleet S2S callers on `/v1/*` (JWT via the fleet auth service) — identifiable from code only by comment: EBI forwarding service for `/v1/receipts` and `/v1/forwarding-stage/census` (`main.py:203-221` scope-rule comments), the id-walk identity-ledger consumer for `/v1/identity-supply` (`identity_supply.py` `x-fleet-cross-service-refs{service:autom8y, entity:identity_observation_ledger}`), `asana-dataframe-resolver` SA on query rows (`rate_limit.py:65-66`), `autom8_data`, `email_booking_intake` and `dev-bypass-service` appear in the test write-principal list (`tests/conftest.py:253`). Intake pipelines call `/v1/intake/*`, `/v1/resolve/*`, `/v1/tasks/{gid}/custom-fields` (idempotency-eligible set).
- Asana Rules actions -> `POST /api/v1/webhooks/inbound?token=` with full task JSON (`webhooks.py:392`); effect today = cache invalidation only (NoOp dispatcher, above).
- The MCP sidecar -> `/v1/query/*`, `/v1/resolve/{et}`, `GET /api/v1/workflows/`, `GET /api/v1/tags`, `GET/POST/PUT /api/v1/tasks/*` (see MCP section) with a minted S2S JWT.
- External PAT users -> `/api/v1/*` resource routes (documented in the spec; ECS ALB, `scripts/entrypoint.sh:50-53` runs `python -m uvicorn autom8_asana.api.main:create_app --factory`; Dockerfile `ENTRYPOINT ["/app/entrypoint.sh"]` :183; `src/autom8_asana/entrypoint.py` is a separate dual-mode launcher bypassed in production).

**Outbound (what this service calls).**
| Target | Purpose | Where |
|---|---|---|
| Asana REST `https://app.asana.com/api/1.0` | all resource operations (SDK `AsanaClient`) | `settings.py:114`, `client.py:813`, `config.py:937` (`ASANA_BASE_URL`) |
| autom8y-auth `https://auth.api.autom8y.io` — JWKS `/.well-known/jwks.json` | inbound JWT validation (cache 5 min, circuit breaker), `/ready` + `/health/deps` probes | `api/config.py:13`, `health.py:315,442`, `auth/jwt_validator.py:6,36,55` |
| autom8y-auth token exchange | S2S token mint for outbound service calls (`ServiceTokenAuthProvider`, `auth_url` default) | `auth/service_token.py:38`, `auth/business_token.py:142`, `services/gid_push.py:275-338,464-555` |
| autom8y-auth `POST /operator/token` via STS SigV4 | machine-operator mint (`sts:GetCallerIdentity` components) | `clients/data/_operator_mint.py:1-16,70` |
| autom8y-data (`AUTOM8Y_DATA_URL`, default `http://localhost:8000`) | `DataServiceClient` lazy singleton on `app.state.data_service_client` (`dependencies.py:545-585`): `POST /api/v1/data-service/insights` (`_endpoints/insights.py:182`, `batch.py:267`), `/api/v1/insights/operator/execute-batch` (`operator.py:47`), `/api/v1/insights/reconciliation/execute` (`reconciliation.py:156`), `/api/v1/messages/export` (`export.py:207`), `/api/v1/appointments` (`simple.py:143`), `/api/v1/leads` (`simple.py:248`); kill switch `AUTOM8Y_DATA_INSIGHTS_ENABLED` (`client.py:118`) | `clients/data/` |
| autom8y-data push receivers | `POST /api/v1/gid-mappings/sync` (`gid_push.py:789`) and `POST /api/v1/account-status/sync` (`gid_push.py:1156`); ECS periodic loop `AccountStatusPushLoop` started in lifespan (`lifespan.py:386-390`, `status_push.py`), lever `STATUS_PUSH_ENABLED` (`gid_push.py:821`) | `services/gid_push.py`, `api/status_push.py` |
| autom8y-scheduling `https://scheduling.api.autom8y.io` | `PATCH /api/v1/businesses/{phone}/config` governed enrollment write — **called from the `enrollment_intent_bridge` Lambda, not the HTTP API** | `enrollment/scheduling_client.py:55-60`, `lambda_handlers/enrollment_intent_bridge.py:127` |
| AWS Lambda `CACHE_WARMER_LAMBDA_ARN` | `POST /v1/admin/cache/refresh` background invoke | `admin.py:218-220,368` |
| AWS DynamoDB (`autom8-idempotency-keys`, us-east-1) | idempotency store | `main.py:400-436` |
| Redis / S3 | cache backends via `create_cache_provider` | `lifespan.py:167` |

**Service discovery** is environment-variable driven (`AUTOM8Y_DATA_URL`, `AUTH_JWKS_URL`, `ASANA_BASE_URL`, `CACHE_WARMER_LAMBDA_ARN`, `IDEMPOTENCY_*`) with hard-coded production defaults for auth and scheduling; settings validation does the inverse guard — in `local`/`test` envs it raises on a URL containing `autom8y.io` for `AUTOM8Y_DATA_URL` and `AUTH_JWKS_URL` (`settings.py:1062-1090`); the data URL defaults to `http://localhost:8000` (`settings.py:737`). Outbound HTTP is policy-constrained to `autom8y_http.Autom8yHttpClient` (ruff `TID251` bans raw `httpx`, `pyproject.toml:360-362`), with documented exceptions (MCP sidecar, CLI `--live`).

## Spec Completeness & Freshness

- **Artifact**: `docs/api-reference/openapi.json`, OpenAPI **3.2.0**, 49 paths / 58 operations, info version `0.1.0`, server list prod/staging (`main.py:629-630`), security schemes `OAuth2Asana`, `PersonalAccessToken`, `ServiceJWT`, `WebhookToken`, and a top-level `webhooks.asanaTaskChanged` entry (`main.py:895`). Last touched by commit `d75bfe1a` (2026-09-06, identity-supply), which is the most recent route addition, so the committed spec includes both newest routes.
- **Code vs spec reconciliation (own count)**: 72 route decorators - 14 `include_in_schema=False` operations = 58 = spec ops; zero undocumented-in-code-but-missing-in-spec among in-schema routes, zero spec-only paths (every spec path listed above has a handler). Hidden operations are by design: admin, entity-write, fleet-query (x2), intake-create/resolve/custom-fields, matching, query execution rows/aggregate, receipts. `x-query-method-candidates` (`main.py:824`) re-documents three hidden POSTs as QUERY candidates inside the spec.
- **Authority and generation**: code-first. `scripts/generate_openapi.py` imports `create_app()` with `AUTOM8Y_ENV=local`, `AUTH_DEV_MODE=true`, serialises `app.openapi()` with sorted keys; `--check` mode byte-compares to the committed file (`generate_openapi.py:44-70`), wired to `just` targets (`justfile:172,177`). CI: `.github/workflows/test.yml:124-128` enables Spectral lint (`spectral_enabled: true`) and `spec_check_enabled: true` with `scripts/validate_openapi.py` against the committed spec; schemathesis fuzz job `tests/test_openapi_fuzz.py` (5 examples on PRs / 25 on main, `test.yml:282-290`). Whether the shared reusable workflow invokes `generate_openapi.py --check` as the drift gate is not visible in this repo (the `spec_check_validate_script` is `validate_openapi.py`) [UV-P: drift-gate semantics inside `satellite-ci-reusable.yml`; METHOD: read the pinned reusable workflow; REASON: external repo].
- **Gaps**: `docs/api-reference/endpoints/` has 8 hand-written pages (`dataframes, entity-write, health, projects, query, resolver, sections, tasks`) — no pages for users, workspaces, tags, exports, workflows, offers/section-timelines, webhooks, census, identity-supply, receipts. The MCP tool surface has no committed machine-readable spec (docstrings and `description=` only). `_OAUTH2_SCOPE_DEFINITIONS` scopes are documentation-only (`main.py:146` comment) and two `_SCOPE_RULES` prefixes match no live path.

## Knowledge Gaps

- Per-field request/response schema for each of the 72 operations was not individually enumerated; the inventory documents path/method/handler/auth/spec-visibility and the shared contract patterns (envelope, errors, pagination), with schemas read in depth only for tasks `ListTasksParams`, query rows/aggregate, resolver, receipts, entity-write, exports, census, identity-supply.
- `GET /api/v1/workflows` PAT behaviour (G-1) and the live `ASANA_WRITE_AUTHZ_MODE` / allowlist values are code-derived only; both need a live probe (UV-P labels above).
- JWT middleware behaviour was read from the session venv's `autom8y_auth 4.1.0` (`site-packages/autom8y_auth/middleware.py`), not from a lockfile-pinned copy in the main worktree; `uv.lock` pin not cross-checked.
- Not read in depth: `tools/tag_resolve.py` body (429 lines), `mcp/asana_mcp/observability.py` (815 lines), `mcp/probes/`, `api/preload/`, `fleet_query_adapter.py` internals, `services/*` handler bodies behind routes.
- `.github/workflows/*` reusable-workflow internals (drift gate) live in another repo.

**Changes since prior version (`.know/api.md`, 2026-07-23, HEAD `d0c8b662`):**
1. Counts moved 69 decorators / 47 paths / 56 ops -> **72 / 49 / 58** (28 mounts reconciled). New in-spec routes: `GET /v1/forwarding-stage/census` (commit 140f9bfc #401) and `GET /v1/identity-supply/{offer_gid}` (commit d75bfe1a). Hidden routers: 14 ops (prior implied 13).
2. **Correction:** `routes/internal.py` has no routes; prior table listed it as "internal ops".
3. **New material area — write-class authorization** (`api/write_authz.py`, RE-2 #391): 26 of 72 operations gated by `require_write_authz`; code default ENFORCE/fail-closed; PAT exempt; the deployed mode/allowlists are environment state not declared in the repo. Prior note only mentioned the idempotency middleware.
4. **MCP surface**: 6 read tools always registered + 1 write tool gated by `ASANA_MCP_ENABLE_WRITE_SURFACE` (default OFF) = 7, not 8; `match_business` stays an unregistered stub; `assembly.py` docstring ("five READ tools") is stale.
5. **New finding G-1**: `/api/v1/workflows*` PAT-tagged but absent from the JWT exclude list.
6. Prior "inbound webhook V1 stub" refined: `set_dispatcher` has no callers in `src/`, so the real `lifecycle/webhook_dispatcher.py` is never installed.
7. Prior statement "CI drift gate relies on regenerate-and-commit" refined: `generate_openapi.py --check` exists (`generate_openapi.py` / `justfile:177`) but the CI wiring into the reusable workflow is not visible here.
8. Source/line anchors in prior text (`main.py:455-495`, `main.py:328-336`) are stale (now `main.py:489-531`, `main.py:350`).
