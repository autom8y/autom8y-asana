---
domain: api
generated_at: "2026-07-23T14:56:44Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./mcp/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "70d45434e1e79ce7bc380936e47a4e265447ffd4db88dc37cd8b37edc70b862f"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase API Surface

> Fresh full-observation pass at synced HEAD `d0c8b662` (2026-07-23). Covers the FastAPI satellite REST API (`src/autom8_asana/api/`) AND the NEW `mcp/asana_mcp/` sidecar tool surface (asana-mcp-v1). Framework: Python / FastAPI via a shared `create_fleet_app()` factory. **69 route decorators / 47 spec paths / 56 operations** (13-op delta = `include_in_schema=False` internal S2S routers, documented-by-design).

## Route Inventory

**Satellite REST API** (`src/autom8_asana/api/routes/`, mounted via `RouterMount` at `api/main.py:455-495`, `create_app()`). Router registration order is load-bearing (`_assert_fleet_query_mount_order`, `main.py:328-336`).

| Router | Prefix | Auth factory | in_schema | Routes |
|---|---|---|---|---|
| health.py | (none) | plain, no auth | true | 3 (`/health`, `/ready`, `/health/deps`) |
| users.py | /api/v1/users | pat_router | true | 3 |
| workspaces.py | /api/v1/workspaces | pat_router | true | 2 |
| dataframes.py | /api/v1/dataframes | pat_router | true | 4 |
| tasks.py | /api/v1/tasks | pat_router | true | 14 (largest) |
| tags.py | /api/v1/tags | pat_router | true | 1 (list-or-resolve-by-name, #246) |
| projects.py | /api/v1/projects | pat_router | true | 8 |
| sections.py | /api/v1/sections | pat_router | true | 6 |
| internal.py | /api/v1/internal | s2s_router | **false** | internal ops |
| intake_resolve.py | /v1 | s2s_router | **false** | 2 |
| resolver.py | /v1/resolve | s2s_router | true | 1 |
| resolver_schema.py | (s2s) | s2s_router | default | 2 |
| query.py | /v1/query | s2s_router | mixed | 8 |
| fleet_query.py | /v1/query & /api/v1/query (dual) | s2s | true | re-export |
| exports.py | /v1/exports & /api/v1/exports (dual) | s2s/pat | true | `POST` |
| admin.py | /v1/admin | s2s_router | **false** | 1 |
| webhooks.py | /api/v1/webhooks | plain (HMAC/token, SC-02 exempt) | true | 1 (`POST /inbound`) |
| workflows.py | /api/v1/workflows | pat_router | true | 2 (`GET /`, `POST /{id}/invoke` — the disclosure oracle) |
| entity_write.py | /api/v1/entity | s2s_router | **false** | 1 (`PATCH`, idempotency-eligible) |
| section_timelines.py | /api/v1/offers | pat_router | true | 1 |
| intake_create.py | /v1/intake | s2s_router | **false** | 2 |
| intake_custom_fields.py | /v1/tasks | s2s_router | **false** | 1 |
| matching.py | (s2s) | s2s_router | hidden | 1 |
| receipts.py | /v1 | s2s_router | **false** | 1 (EBI OI-2 forwarding-receipt) |

**Versioning**: `/api/v1/*` (PAT, external/resource-facing) and `/v1/*` (S2S-JWT, internal fleet-facing) coexist by design; `exports.py`/`fleet_query.py` deliberately dual-mount the same surface under both prefixes (legacy compat).

**MCP Sidecar** (`mcp/asana_mcp/`, `asana-mcp-v1`) — a FastMCP process; its "routes" are MCP tool registrations via `server.py:create_server()` (`discovery`, `query`, `resolve`, `workflows` registered; `composite_write` conditional on the write flag):

| Tool | Module | Verb | Notes |
|---|---|---|---|
| list_entity_types / describe_entity | tools/discovery.py | read | thin tier |
| query_rows / query_aggregate | tools/query.py | read | rich native; proxies `/v1/query` |
| resolve_entity | tools/resolve.py | read | proxies `/v1/resolve/{entity_type}` |
| list_report_workflows | tools/workflows.py (#268) | read/disclosure | reads `GET /api/v1/workflows`; **never invokes** (invocation is a separate write-verb) |
| asana_complete_tagged_task | tools/composite_write.py | write (gated) | needs `ASANA_MCP_ENABLE_WRITE_SURFACE` (default OFF) AND RB-1 confirm-token for `add_tag` |
| match_business | tools/_match_business_stub.py | — | deliberately NOT registered |

**RB-1 confirm-before-firing gate** (`tools/confirm_gate.py`, #263): a trigger-capable write WITHOUT `confirmation_token` performs zero backend calls and returns a `confirmation_required` envelope carrying a single-use, TTL-bounded (600s), fingerprint-bound token; a second call with the token + byte-identical intent executes; mismatch refuses again (zero writes) and burns the token.

## Authentication & Authorization Model

**Satellite** — dual-mode PAT + S2S-JWT unified through `AuthContext` (`api/dependencies.py:46-72`).
- Schemes (`routes/_security.py`): `PAT_BEARER_SCHEME` (PersonalAccessToken) via `pat_router()`; `SERVICE_JWT_SCHEME` (ServiceJWT) via `s2s_router()`; both `auto_error=False` (schemes inject OpenAPI metadata only; runtime enforcement is in the dependency chain).
- Chain: `_extract_bearer_token` → `get_auth_context` (`dependencies.py:109-268`; `detect_token_type`/`AuthMode`; PAT direct or bot-PAT via `auth/bot_pat.py` for JWT S2S) → `get_asana_client_from_context`.
- Classification: public (`/health*`), PAT (external `/api/v1/*`), S2S-JWT (internal `/v1/*` + several hidden `/api/v1/*`). `webhooks.py` uses HMAC/token-in-querystring (SC-02 exemption).
- `ClientPool` (`api/client_pool.py`): token-hash-keyed, LRU 100, TTL 1h S2S / 5min user-PAT — preserves rate-limiter/circuit-breaker/AIMD state (IMP-19).
- Rate limiting (`api/rate_limit.py`): slowapi; `sa:asana-dataframe-resolver` at 600 rpm for SA-JWT callers.
- Idempotency (`api/middleware/idempotency.py`): RFC 8791 `Idempotency-Key` scoped to 4 named mutating endpoints.
- Dual error envelope: 401/403 declare `oneOf[ErrorResponse, AuthTebError]` (`error_responses.py`) so both app-layer and middleware-layer shapes are fuzzer-visible.
- Every endpoint declares `x-fleet-side-effects` / `x-fleet-idempotency` / `x-fleet-rate-limit` `openapi_extra` (102 occurrences) — the authoritative machine-readable contract layer.

**MCP** — auth is bridged, never independently minted. `bridge.py` speaks HTTP only to the satellite's S2S surface (never imports the domain SDK); mints via fleet `autom8y_core.TokenManager` (lazy). #264 fail-clean: `InvalidServiceKeyError` → `McpToolError(kind=auth, 401, non-retryable, S2S_MINT_CREDENTIALS_INVALID)` vs auth-infra-down → `kind=server, 503, retryable`. Readiness gate is fail-closed (proxies `/ready`). Write-surface gate: `ASANA_MCP_ENABLE_WRITE_SURFACE` (default OFF) — the write tool attaches to nothing while off. RB-1 confirm-gate is a human-in-the-loop authorization layer on top of that flag.

## Request/Response Contracts

- Envelope: `{data, meta}` / `{error: {code, message, details}, meta}` from `autom8y_api_schemas` (re-exported `api/models.py`). `meta.request_id` + `meta.timestamp` on both.
- Error catalog (`api/errors.py`, ADR-ASANA-004): `NotFoundError`→404, `AuthenticationError`→401, `ForbiddenError`→403, `RateLimitError`→429, `GidValidationError`→400, `ServerError`→502, `TimeoutError`→504, catch-all→500 (detail-hidden). `raise_api_error()` / `raise_service_error()`.
- Pagination: cursor-based (`limit` + `offset: str|None`); `DEFAULT_LIMIT=MAX_LIMIT=100`.
- Field naming snake_case throughout (no camelCase alias). GID typing: `GidStr` regex `^\d{1,64}$` in prod, relaxed in test/local (env checked at module-import time).
- Content types: JSON only in most routes; dataframes/exports negotiate via `Accept` (JSON/CSV/Parquet/Polars-native).
- **MCP contracts**: `envelopes.py:unwrap_outer` strips the satellite `{data}` envelope; tools re-add honesty-attestation fields (`honest_empty`, `contract_complete`). `errors.py` `McpToolError`/`map_http_error` carries `kind`/`status`/`retryable`/`code`.

## Cross-Service Dependencies

**Outbound**: Asana public API (via `AsanaClient`); autom8y-auth/JWKS (JWT validation, circuit breaker); autom8y-data (`DataServiceClient`, optional lazy singleton on `app.state`); DynamoDB (idempotency store); Redis (optional cache backend); `autom8y_core.TokenManager` (MCP S2S mint, lazy). **Inbound**: Asana webhooks (`POST /api/v1/webhooks/inbound?token=` — V1 stub, full HMAC handshake is a marked V2 extension point); the MCP sidecar is itself an inbound HTTP consumer of the satellite's `/v1/query`, `/v1/resolve`, `GET /api/v1/workflows`, and composite write. Service discovery is environment-variable based throughout.

## Spec Completeness & Freshness

`docs/api-reference/openapi.json` (OAS 3.2.0, 47 paths / 56 ops), code-first generated via `scripts/generate_openapi.py`/`validate_openapi.py` (`create_app().openapi()`). CI drift gate: `.github/workflows/test.yml:76-83` runs `spec_check_enabled: true` + Spectral lint + schemathesis fuzz (`tests/test_openapi_fuzz.py`, `continue-on-error`). NOTE: the gate validates structural schema-conformance + registry-type presence, NOT an explicit route-count-delta against a frozen baseline — freshness relies on regenerate-and-commit discipline. The 69-vs-56 code-to-spec delta is fully attributable to 7 `include_in_schema=False` internal routers (documented-by-design, not drift). **The MCP tool surface has no committed OpenAPI/proto equivalent** — documented only in-code via docstrings + `description=` kwargs. A genuine gap for the newer sidecar relative to the mature REST spec discipline.

## Grades

Route Inventory A (96%) · Auth Model A (93%) · Request/Response Contracts A (92%) · Cross-Service Dependencies B (87%) · Spec Completeness & Freshness B. **Overall A (92%).**

## Knowledge Gaps

- Per-decorator-to-spec-path mapping reconciled at router/module level, not per-individual-route (69 vs 47).
- `mcp/probes/c2_sandbox_reput_probe.py` not read (inferred reputation/sandbox probe).
- Asana Webhooks V2 handshake/HMAC protocol not investigated (marked not-yet-implemented).
- `tag_resolve.py` (429 lines) scanned for registration but not read line-by-line.
- `docs/api-reference/endpoints/` subdirectory contents not enumerated.
- [KNOW-CANDIDATE] The MCP surface may warrant a sibling `.know/mcp.md` covering the 8 tools, RB-1, the #264 bridge fix, and #268 disclosure tool as a first-class domain.
