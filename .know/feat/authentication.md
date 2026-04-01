---
domain: feat/authentication
generated_at: "2026-04-01T17:10:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/auth/**/*.py"
  - "./src/autom8_asana/api/dependencies.py"
  - "./src/autom8_asana/protocols/auth.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.88
format_version: "1.0"
---

# Authentication (JWT / BotPAT / DualMode / S2S)

## Purpose and Design Rationale

Dual-mode authentication for two caller types: **human/user** (Asana PAT passthrough) and **internal S2S** (JWT validated via JWKS, bot PAT substituted for Asana calls).

Core routing gate: token type detection is purely structural -- JWT has exactly 2 dots (header.payload.signature); Asana PAT has 0 dots. This O(n) string scan routes the entire auth pipeline.

## Conceptual Model

### S2S Path

```
Bearer <jwt> -> detect_token_type (2 dots = JWT)
  -> validate_service_token (autom8y-auth JWKS validation)
  -> get_bot_pat (lru_cache; ASANA_PAT env var)
  -> AuthContext(mode=JWT, asana_pat=bot_pat, caller_service=claims.service_name)
  -> ClientPool.get_or_create(bot_pat, is_s2s=True)  [1h TTL]
```

### PAT Path

```
Bearer <pat> -> detect_token_type (0 dots = PAT)
  -> AuthContext(mode=PAT, asana_pat=token)
  -> ClientPool.get_or_create(token, is_s2s=False)  [5m TTL]
```

### Cross-Service Auth

`ServiceTokenAuthProvider` wraps `autom8y_core.TokenManager` for `SERVICE_API_KEY` -> JWT exchange. Used by `DataServiceClient` for calls to `autom8_data` satellite service.

### Route-Level Scheme

PAT Bearer: tasks, projects, sections, users, workspaces, dataframes, workflows. S2S JWT: resolver, query, admin, internal, entity-write, intake, matching. URL token: webhooks. None: health.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/auth/dual_mode.py` | `AuthMode` enum, `detect_token_type()` (dot count), `get_auth_mode()` |
| `src/autom8_asana/auth/jwt_validator.py` | Lazy `AuthClient` singleton, `validate_service_token()` -> autom8y-auth SDK |
| `src/autom8_asana/auth/bot_pat.py` | `get_bot_pat()` -- `lru_cache(maxsize=1)`, length validation (>10 chars) |
| `src/autom8_asana/auth/service_token.py` | `ServiceTokenAuthProvider` for cross-service JWT exchange |
| `src/autom8_asana/auth/audit.py` | `S2SAuditLogger` -- structured JSON events, no-op for PAT, INFO/WARNING for JWT |
| `src/autom8_asana/protocols/auth.py` | `AuthProvider` structural protocol (`get_secret(key) -> str`) |
| `src/autom8_asana/api/dependencies.py` | `AuthContext`, `get_auth_context()` FastAPI dependency, client wiring |

### Error Classification (Load-Bearing)

| Exception | HTTP | Rationale |
|-----------|------|-----------|
| `PermanentAuthError` | 401 | Bad token |
| `TransientAuthError` | 503 | Retryable (JWKS flaky) |
| `CircuitOpenError` | 503 | JWKS circuit open |
| `BotPATError` | 503 | Bot PAT missing/invalid |

503 for transient failures allows upstream retry instead of treating flaky JWKS as invalid credentials.

## Boundaries and Failure Modes

### Scars

- **SCAR-012**: `DataServiceClient` created without `auth_provider` -- all cross-service joins returned zero matches. Fix: `ServiceTokenAuthProvider` now explicitly wired.
- **Env Var Naming Scar**: `AUTOM8_DATA_API_KEY` (missing "Y") caused silent auth failure. ADR-ENV-NAMING-CONVENTION mandates `AUTOM8Y_` prefix.

### Defensive Patterns

- Bot PAT length validation rejects <10 chars (catches empty env vars)
- `__init__.py` wraps FastAPI import in `try/except ImportError` for non-API SDK usage
- `autom8y-auth` is optional at package level but required for any deployed S2S instance
- Audit logger never emits credential material (frozen dataclass accepts only safe fields)

### SDK Dependency

`autom8y-auth[observability]>=2.0.0` -- optional but effectively required for S2S. JWKS cache TTL default 5 minutes (SDK-controlled).

## Knowledge Gaps

1. `autom8y-auth` SDK JWKS caching and stale-cache fallback semantics not observable.
2. `ServiceTokenAuthProvider` test coverage not confirmed.
3. `SecretsManagerAuthProvider` referenced in docs but not found in `src/` (may be in `_defaults/`).
4. `resolve_secret_from_env` Lambda extension resolution semantics not visible.
