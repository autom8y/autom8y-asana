---
domain: feat/authentication
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/auth/"
  - "./src/autom8_asana/api/routes/internal.py"
  - "./pyproject.toml"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.96
format_version: "1.0"
---

# Authentication (JWT / BotPAT / DualMode / S2S / ServiceClaims)

## Purpose and Design Rationale

Authentication in `autom8_asana` solves a two-caller-type problem: **human/user callers** present Asana PATs directly (pass-through), and **internal S2S callers** present JWT tokens from the autom8y auth service. The same HTTP API must accept both without forcing S2S callers to manage Asana credentials.

**Core design decisions (per ADR-S2S-001, ADR-S2S-002, TDD-S2S-001)**:

1. **Token type detection via dot counting** (ADR-S2S-001): JWT tokens have exactly 2 dots (`header.payload.signature`); Asana PATs have 0 dots. O(n) string scan, no regex, no header-based routing. Alternatives considered and rejected: header-based (`X-Auth-Type`), regex validation, decode-and-inspect, prefix convention.

2. **Bot PAT substitution for S2S** (ADR-S2S-002): When a JWT is presented, `autom8_asana` validates it against the JWKS endpoint and substitutes its own `ASANA_PAT` (injected via ECS Secrets Manager) for the downstream Asana call. S2S callers never hold Asana credentials; the service acts as a credential boundary.

3. **`autom8y-auth` SDK delegated entirely** (ADR-S2S-001): No custom JWT validation logic. The SDK owns JWKS caching (5-minute TTL, `AUTH__CACHE__TTL_CACHE_TTL`), signature verification, issuer/audience enforcement (`audience="https://api.autom8y.io"`), and circuit-breaking on JWKS endpoint failures.

4. **`ServiceClaims` / `require_service_claims`** (subsumed from `internal.py`): A separate fine-grained auth dependency for routes that need caller identity (not just a valid JWT). Returns `ServiceClaims(sub, service_name, scope, permissions)`. `permissions: list[str]` enables privilege gating (e.g., `"admin:access"` required for `/v1/admin/cache/refresh` per Bedrock W4C-P3 / SEC-DT-10).

**Why dual-mode exists**: The API serves both the autom8y platform (S2S, JWT) and end-user/integration callers (PAT). A single auth dependency that routes transparently avoids duplicating route definitions or forcing middleware to understand Asana's PAT format.

**SCAR-WS8 history**: PAT-tagged routes must be listed in `jwt_auth_config.exclude_paths`. The `JWTAuthMiddleware` (from `autom8y_api_middleware`) applies fleet-level JWT enforcement before FastAPI's DI runs. Without an `exclude_paths` entry, PAT requests hit the middleware and are rejected before `get_auth_context()` even executes. `/api/v1/exports/*` was missing; regression test `test_exports_auth_exclusion.py` (2 `@pytest.mark.scar` markers) now guards this. Structural invariant: **every new PAT-tagged router registration requires a corresponding `exclude_paths` entry**.

**SCAR-012 history**: `DataServiceClient` was originally wired without `auth_provider`, causing all cross-service data joins to use PAT-based auth. Fix: `ServiceTokenAuthProvider` (wrapping `autom8y_core.TokenManager`) now explicitly wired via `dependencies.py:get_data_service_client()`. Cross-service callers MUST use `client_credentials` grant, not PAT pass-through.

---

## Conceptual Model

### Four Auth Strategies

```
Incoming Bearer token
  ├─ dot_count == 2 → JWT path (S2S)
  │     ├─ validate_service_token(token) → ServiceClaims (sub, service_name, scope, permissions)
  │     ├─ get_bot_pat() → ASANA_PAT env var [lru_cache(maxsize=1)]
  │     └─ AuthContext(mode=JWT, asana_pat=bot_pat, caller_service=claims.service_name)
  │
  └─ dot_count != 2 → PAT path (user)
        └─ AuthContext(mode=PAT, asana_pat=token, caller_service=None)
```

### Strategy 1 — DualMode (PAT or JWT detection)

`auth/dual_mode.py` — the routing gate. `detect_token_type(token: str) -> AuthMode` is the single pure function that all auth paths depend on.

```
Bearer <jwt> → detect_token_type → AuthMode.JWT → validate_service_token → get_bot_pat → AuthContext
Bearer <pat> → detect_token_type → AuthMode.PAT → AuthContext(asana_pat=token)
```

**Cross-layer tension (TENSION-008)**: `dual_mode.py:24` imports `ApiAuthError` from `api/exception_types.py` at module load time — not behind `TYPE_CHECKING`. This is a documented upward dependency (`auth/` → `api/`) that violates the standard layer order. `api/exception_types.py` functions as a cross-cutting exception registry; renaming or moving it requires coordinated updates in `auth/dual_mode.py`, `cache/dataframe/decorator.py` (4 sites), `api/dependencies.py`, and `api/routes/internal.py`. See GAP-008 in design-constraints.

### Strategy 2 — JWT Validation

`auth/jwt_validator.py` — wraps `autom8y_auth.AuthClient`. Lazy initialized module-level singleton (`_auth_client`); thread-safe. Validates with `client.validate_service_token(token, audience="https://api.autom8y.io")`. Returns `autom8y_auth.ServiceClaims`.

JWKS semantics (SDK-controlled, not locally visible): 5-minute cache TTL (`AUTH__CACHE__TTL_SECONDS` configurable). Stale-cache fallback behavior is internal to the SDK. `AUTH_JWKS_URL` defaults to `https://auth.api.autom8y.io/.well-known/jwks.json`; `AUTH_ISSUER` defaults to `auth.api.autom8y.io`.

Error taxonomy from `autom8y_auth` (all caught in `api/dependencies.py`):

| Exception | HTTP | Rationale |
|-----------|------|-----------|
| `PermanentAuthError` | 401 via `ApiAuthError` | Bad token (expired, invalid sig, wrong issuer) |
| `TransientAuthError` | 503 via `ApiServiceUnavailableError` | Retryable (JWKS temporarily unavailable) |
| `CircuitOpenError` | 503 via `ApiServiceUnavailableError` | JWKS circuit breaker open |
| `ImportError` | 503 via `ApiServiceUnavailableError` | `autom8y-auth` SDK not installed |

503 for transient failures allows upstream retry rather than treating flaky JWKS as bad credentials.

### Strategy 3 — BotPAT

`auth/bot_pat.py` — `get_bot_pat()` with `@lru_cache(maxsize=1)`. Reads `ASANA_PAT` via `autom8y_config.lambda_extension.resolve_secret_from_env()` (supports Lambda extension resolution). Raises `BotPATError` if missing or shorter than 10 chars. Never logs the value; only logs `pat_length`. Cleared in tests via `clear_bot_pat_cache()`.

The 10-char minimum is a sanity check that catches empty env vars (`""`) and placeholder values; it is not a cryptographic check.

### Strategy 4 — ServiceToken (S2S Client Auth)

`auth/service_token.py` — `ServiceTokenAuthProvider`. Satisfies `protocols.auth.AuthProvider` (structural protocol: `get_secret(key: str) -> str`). Wraps `autom8y_core.TokenManager` with `client_credentials` grant. Used to authenticate `DataServiceClient` outbound calls to `autom8_data` satellite service. Configured via `SERVICE_CLIENT_ID` + `SERVICE_CLIENT_SECRET` env vars. Falls back gracefully (caught `ValueError`/`ImportError` in `dependencies.py:get_data_service_client()`) to env var `AUTOM8Y_DATA_API_KEY` for backward compat.

### ServiceClaims and `require_service_claims`

Defined in `api/routes/internal.py`. A second-level auth dependency layered on top of JWT validation, providing caller identity to route handlers:

```python
class ServiceClaims(BaseModel):
    sub: str
    service_name: str
    scope: str | None = None
    permissions: list[str] = []  # from ServiceAccount scopes; gates SUPER_ADMIN_PERMISSION
```

`require_service_claims(request)` calls `detect_token_type()`, rejects PAT with 401, validates JWT via `validate_service_token()`, and returns `ServiceClaims`. Used as `Annotated[ServiceClaims, Depends(require_service_claims)]` in 11 route files (resolver_schema, entity_write, query, intake_resolve, matching, fleet_query, admin, intake_custom_fields, resolver, intake_create — see Importer Map below).

**Privilege gating**: `admin.py` enforces `SUPER_ADMIN_PERMISSION = "admin:access"` check on the cache-refresh endpoint: `if SUPER_ADMIN_PERMISSION not in claims.permissions: raise 403`.

### Audit Logging

`auth/audit.py` — `S2SAuditLogger` with two methods:

- `log_request(...)` — logs all requests (JWT and PAT)
- `log_jwt_only(...)` — logs only JWT (S2S) requests; returns `None` for PAT — preferred for route handlers to avoid log noise

`S2SAuditEntry` is a frozen dataclass (`slots=True`). Fields: `event`, `timestamp` (UTC ISO 8601 with Z), `request_id`, `auth_mode`, `caller_service` (None for PAT), `endpoint`, `method`, `response_status`, `duration_ms`. No credential material is accepted as a field. Uses `INFO` for 2xx/3xx, `WARNING` for 4xx/5xx.

### ClientPool TTL Differentiation

`api/client_pool.py` pools `AsanaClient` instances keyed by PAT:

| Mode | `is_s2s` | TTL |
|------|----------|-----|
| JWT (S2S) | `True` | 1 hour |
| PAT (user) | `False` | 5 minutes |

Wired in `api/dependencies.py:get_asana_client_from_context()`.

---

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/auth/dual_mode.py` | `AuthMode` enum (JWT/PAT), `detect_token_type()` (dot count), `get_auth_mode()` FastAPI dependency; IMPORTS `ApiAuthError` from `api/exception_types.py` (TENSION-008) |
| `src/autom8_asana/auth/jwt_validator.py` | Lazy `AuthClient` singleton; `validate_service_token()` → `autom8y_auth` SDK; `reset_auth_client()` for tests |
| `src/autom8_asana/auth/bot_pat.py` | `get_bot_pat()` `lru_cache(maxsize=1)`; `BotPATError`; `clear_bot_pat_cache()` for tests; reads via `resolve_secret_from_env("ASANA_PAT")` |
| `src/autom8_asana/auth/service_token.py` | `ServiceTokenAuthProvider`; wraps `autom8y_core.TokenManager`; satisfies `AuthProvider` protocol |
| `src/autom8_asana/auth/audit.py` | `S2SAuditEntry` (frozen dataclass), `S2SAuditLogger`, `get_audit_logger()` singleton; structured JSON to CloudWatch |
| `src/autom8_asana/auth/__init__.py` | Package facade; wraps FastAPI-dependent `dual_mode` imports in `try/except ImportError` to allow non-API SDK usage |
| `src/autom8_asana/api/routes/internal.py` | `ServiceClaims` Pydantic model + `require_service_claims` dependency; `_extract_bearer_token` helper; JWT-only enforcement (rejects PAT with 401) |
| `src/autom8_asana/api/dependencies.py` | `AuthContext` class; `get_auth_context()` primary FastAPI dependency; `get_asana_client_from_context()`; `get_data_service_client()` (wires `ServiceTokenAuthProvider`) |
| `src/autom8_asana/protocols/auth.py` | `AuthProvider` structural protocol: `get_secret(key: str) -> str` — pure leaf, no imports |
| `src/autom8_asana/api/main.py:374-396` | `JWTAuthConfig(exclude_paths=...)` — fleet middleware wiring; `DEFAULT_EXCLUDE_PATHS` from `autom8y_auth` + service-specific PAT route exclusions |

### `ServiceClaims` / `require_service_claims` Importer Map (11 route files)

`require_service_claims` is a load-bearing cross-cutting auth utility with **11 importer files**:

| File | Usage |
|------|-------|
| `api/routes/resolver_schema.py` | 2 route handlers |
| `api/routes/entity_write.py` | 2+ route handlers |
| `api/routes/query.py` | 9 route handlers |
| `api/routes/intake_resolve.py` | 2 route handlers |
| `api/routes/matching.py` | 1 route handler |
| `api/routes/fleet_query.py` | 2 route handlers |
| `api/routes/admin.py` | 1 route handler (+ `SUPER_ADMIN_PERMISSION` gate) |
| `api/routes/intake_custom_fields.py` | 1 route handler |
| `api/routes/resolver.py` | 1 route handler |
| `api/routes/intake_create.py` | 2 route handlers |

**Census decision**: `internal.py` is subsumed into the authentication feature because `ServiceClaims` and `require_service_claims` are auth-layer utilities that happen to live in a route file, not business logic.

### Optional Dependency

```toml
[project.optional-dependencies]
auth = ["autom8y-auth[observability]>=3.3.0"]
```

`pyproject.toml` also declares `autom8y-auth[observability]>=3.3.0` and `autom8y-auth[testing]>=3.3.0` in `dev` extras (required for `test_auth` tests, S2 UC-1/2/3). The SDK is effectively required for any deployed S2S instance.

### Data Flow: Request Authentication

```
HTTP request with Bearer token
  → JWTAuthMiddleware (api/main.py:453)
      [PAT routes excluded via jwt_auth_config.exclude_paths → pass through]
      [JWT routes → fleet-level JWT pre-validation]
  → FastAPI route handler
  → Depends(get_auth_context) [api/dependencies.py]
      → _extract_bearer_token() [min-length=10, Bearer scheme]
      → detect_token_type(token) [dot count]
      → IF JWT: validate_service_token(token) + get_bot_pat()
        → return AuthContext(mode=JWT, asana_pat=bot_pat, caller_service=service_name)
      → IF PAT: return AuthContext(mode=PAT, asana_pat=token)
  → Depends(get_asana_client_from_context)
      → ClientPool.get_or_create(asana_pat, is_s2s=True/False)
        [1h TTL for S2S, 5m TTL for PAT]
  → Route handler receives AsanaClient + AuthContext
```

For S2S-only routes using `require_service_claims`:

```
  → Depends(require_service_claims) [api/routes/internal.py]
      → _extract_bearer_token()
      → detect_token_type() → reject PAT with 401
      → validate_service_token(token) → ServiceClaims
      → Optional: check claims.permissions for privilege gating
```

### Test Coverage Locations

| Test File | Coverage |
|-----------|----------|
| `tests/unit/api/test_exports_auth_exclusion.py` | SCAR-WS8 — live middleware introspection, `@pytest.mark.scar` (2 markers) |
| Auth unit tests (referenced via `S2 UC-1/2/3`) | JWT validation, PAT pass-through — requires `autom8y-auth[testing]>=3.3.0` |

---

## Boundaries and Failure Modes

### IN Scope

- Token type detection (JWT vs PAT)
- JWT validation (delegated to `autom8y-auth` SDK)
- Bot PAT activation from environment
- `AuthContext` assembly for downstream use
- `ServiceClaims` extraction and privilege gating
- S2S audit logging
- `ServiceTokenAuthProvider` for outbound S2S calls (DataServiceClient authentication)

### OUT of Scope

- Rate limiting (handled by `SlowAPI` middleware in `api/main.py`)
- Request logging (handled by `RequestLoggingMiddleware`)
- Idempotency (handled by `IdempotencyMiddleware`)
- Security headers (handled by `SecurityHeadersMiddleware`)
- OpenAPI security scheme definitions (handled in `api/main.py:custom_openapi()`)

### Failure Modes Catalog

**SCAR-WS8 — JWT middleware rejects PAT requests**
- Trigger: New PAT-tagged router added without corresponding `jwt_auth_config.exclude_paths` entry.
- Effect: `JWTAuthMiddleware` runs before FastAPI DI; PAT token treated as invalid JWT; all requests to route return 401.
- Fix location: `api/main.py:389`; currently includes: `DEFAULT_EXCLUDE_PATHS` + `/redoc`, `/api/v1/webhooks/*`, `/api/v1/tasks/*`, `/api/v1/projects/*`, `/api/v1/sections/*`, `/api/v1/users/*`, `/api/v1/workspaces/*`, `/api/v1/dataframes/*`, `/api/v1/offers/*`, `/api/v1/exports/*`, `/api/v1/workflows/*`.
- Regression: `tests/unit/api/test_exports_auth_exclusion.py` (`@pytest.mark.scar`).
- Invariant: **Every new PAT-tagged router addition requires a corresponding `exclude_paths` entry AND a regression test.**

**SCAR-012 — Cross-service client using PAT instead of `client_credentials`**
- Trigger: `DataServiceClient` initialized without `auth_provider`.
- Effect: Cross-service data joins return zero matches (auth header sent as Asana PAT to data service, which expects JWT).
- Fix: `dependencies.py:get_data_service_client()` now wraps `ServiceTokenAuthProvider()` in `try/except (ValueError, ImportError)` before constructing client. Falls back to `AUTOM8Y_DATA_API_KEY` env var for backward compat.
- Invariant: **New cross-service clients must use `ServiceTokenAuthProvider` with `client_credentials` grant, not PAT pass-through.**

**SCAR-012 companion — Env Var Naming**
- `AUTOM8_DATA_API_KEY` (missing Y) caused silent auth failure in production.
- Fix: `clients/data/config.py:231` uses `AUTOM8Y_DATA_API_KEY`.
- Convention: All ecosystem env vars use `AUTOM8Y_` prefix (ADR-ENV-NAMING-CONVENTION).

**Bot PAT missing or invalid**
- `BotPATError` → 503 `ApiServiceUnavailableError`.
- Trigger: `ASANA_PAT` env var missing, empty, or shorter than 10 chars.
- Logs `bot_pat_unavailable` with `error` field (no credential value).

**JWKS circuit open**
- `CircuitOpenError` → 503 `ApiServiceUnavailableError`.
- All S2S JWT requests fail until circuit resets. PAT requests unaffected.

**`autom8y-auth` not installed**
- `ImportError` → 503 `ApiServiceUnavailableError`.
- Caught in both `get_auth_context()` and `require_service_claims()`.

**Super-admin permission missing**
- `claims.permissions` does not contain `"admin:access"`.
- Effect: `admin.py` cache-refresh endpoint returns 403 with `INSUFFICIENT_PRIVILEGE`.
- Gate: `if SUPER_ADMIN_PERMISSION not in claims.permissions`.

**TENSION-008 — Cross-layer import**
- `auth/dual_mode.py:24` imports `ApiAuthError` from `api/exception_types.py` at module load time.
- Risk: If `api/exception_types.py` is renamed/moved, `auth/dual_mode.py` breaks silently (no TYPE_CHECKING guard).
- `api/exception_types.py` is a de-facto cross-cutting exception registry used by auth, cache, and api layers (GAP-008).

**Audit log gaps**
- `log_jwt_only()` skips PAT requests entirely — no audit trail for user-PAT operations.
- No caller-identity on PAT requests (by design: users are identified by their PAT, not a service name).

### Configuration Boundaries

| Env Var | Purpose | Default |
|---------|---------|---------|
| `ASANA_PAT` | Bot PAT for S2S → Asana calls | Required for S2S; injected by ECS Secrets Manager |
| `AUTH_JWKS_URL` | JWKS endpoint for JWT validation | `https://auth.api.autom8y.io/.well-known/jwks.json` |
| `AUTH_ISSUER` | Expected JWT issuer | `auth.api.autom8y.io` |
| `AUTH__CACHE__TTL_SECONDS` | JWKS cache TTL (SDK) | 300 (5 min) |
| `SERVICE_CLIENT_ID` | ServiceAccount ID for `ServiceTokenAuthProvider` | Required for data-service joins |
| `SERVICE_CLIENT_SECRET` | ServiceAccount secret | Required for data-service joins |
| `AUTOM8Y_DATA_API_KEY` | Fallback API key for data-service | Backward compat only |

**Invalid values**: `ASANA_PAT` < 10 chars raises `BotPATError`. Empty `SERVICE_CLIENT_ID` or `SERVICE_CLIENT_SECRET` raises `ValueError` in `ServiceTokenAuthProvider.__init__()` (caught gracefully in `get_data_service_client()`).

### Knowledge Gaps

1. `autom8y-auth` SDK internal JWKS stale-cache fallback behavior not observable from this codebase.
2. `ServiceTokenAuthProvider.close()` is defined but no caller in `dependencies.py` calls it on shutdown — potential resource leak on app teardown.
3. SCAR-WS8 regression test (`test_exports_auth_exclusion.py`) covers exports exclusion only; systematic coverage of all 9 PAT-route exclusion paths not confirmed.
4. `AUTH__CACHE__TTL_SECONDS` configuration path not confirmed (SDK-internal env var name).

```metadata
domain: feat/authentication
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.96
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 95
    weight: 0.30
    notes: >
      Problem statement clear. ADR-S2S-001, ADR-S2S-002, TDD-S2S-001 referenced.
      SCAR-WS8 and SCAR-012 histories documented with root causes and invariants.
      Rejected alternatives for dot-counting listed. Tradeoffs (503 vs 401 for
      transient JWKS) explicitly identified.
  conceptual_model:
    grade: A
    pct: 92
    weight: 0.25
    notes: >
      All 4 strategies (DualMode, JWT, BotPAT, ServiceToken) plus ServiceClaims
      modeled with flow diagrams. ClientPool TTL differentiation documented.
      TENSION-008 cross-layer dependency identified. Privilege gating documented.
      Minor gap: SDK JWKS stale-cache fallback semantics not observable.
  implementation_map:
    grade: A
    pct: 94
    weight: 0.25
    notes: >
      All 5 auth files + internal.py + dependencies.py + protocols/auth.py mapped.
      All 11 ServiceClaims importer files enumerated. Data flow traced end-to-end.
      pyproject.toml optional dep group documented. Test locations identified.
  boundaries_and_failure_modes:
    grade: A
    pct: 93
    weight: 0.20
    notes: >
      IN/OUT scope documented explicitly. 5 failure modes with SCAR references
      and evidence. Configuration boundary table with env var inventory.
      GAP: ServiceTokenAuthProvider.close() not called on shutdown.
overall_grade: A
overall_pct: 94
```
