---
domain: feat/fastapi-server
generated_at: "2026-04-01T17:00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/main.py"
  - "./src/autom8_asana/api/lifespan.py"
  - "./src/autom8_asana/api/dependencies.py"
  - "./src/autom8_asana/api/client_pool.py"
  - "./src/autom8_asana/api/middleware/**/*.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# FastAPI HTTP Server (ECS Mode)

## Purpose and Design Rationale

Primary HTTP surface for `autom8_asana` in ECS mode. Bridges two caller populations: **external/user** (PAT auth, Asana resource management) and **internal S2S** (JWT auth, entity resolution/query/intake/writes using bot PAT). Conceptual model: thin routing shell over deep SDK -- no business logic in route handlers.

**Dual-mode container**: Same Docker image runs ECS (uvicorn) or Lambda (awslambdaric). Detection pivot: `AWS_LAMBDA_RUNTIME_API` env var.

## Conceptual Model

### Middleware Stack (outer to inner)

1. MetricsMiddleware (Prometheus), 2. CORSMiddleware, 3. IdempotencyMiddleware (RFC 8791, 4 eligible endpoints, DynamoDB/memory/noop backends), 4. SlowAPIMiddleware (rate limiting), 5. RequestLoggingMiddleware, 6. RequestIDMiddleware (16-char hex X-Request-ID).

### Auth DI Chain

`_extract_bearer_token` -> `get_auth_context` -> `detect_token_type` (dot-count heuristic: 2 dots = JWT, 0 = PAT) -> PAT path (passthrough) or JWT path (JWKS validation + bot PAT) -> `ClientPool.get_or_create()`.

### 14-Step Startup Sequence

1. Bootstrap business models, 2. Structured logging, 3. httpx OTel instrumentation, 4. Create shared CacheProvider (SCAR-004 fix), 5. ClientPool, 6. Discover entity projects (fail-fast), 7. Cross-registry validation, 8. DataFrame cache, 9. Schema providers, 10. MutationInvalidator, 11. EntityWriteRegistry, 12. Workflow configs, 13. Cascade ordering validation (fail-fast), 14. Background cache warming task.

### Client Pool

LRU pool keyed by `SHA-256(token)[:16]`. Max 100 entries. S2S TTL: 1h, PAT TTL: 5m. `_PooledClientWrapper` makes `aclose()` a no-op to prevent FastAPI dependency teardown from closing pooled clients.

### Health Probes (SCAR-011)

`GET /health` -- always 200, zero I/O (liveness). `GET /ready` -- 503 while cache warms (readiness). `GET /health/deps` -- JWKS + bot PAT check.

### Idempotency (RFC 8791)

4 eligible endpoints. DynamoDB-backed (prod), in-memory (dev). Two-phase: claim -> execute -> finalize. Concurrent duplicate returns 409 + Retry-After:1. Finalized duplicate replays response. DynamoDB failure degrades to passthrough.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/api/main.py` | `create_app()` factory, middleware registration, router ordering, OpenAPI enrichment |
| `src/autom8_asana/api/lifespan.py` | 14-step startup, shutdown cleanup |
| `src/autom8_asana/api/dependencies.py` | Auth chain, service DI, type aliases |
| `src/autom8_asana/api/client_pool.py` | LRU `ClientPool`, `_PooledClientWrapper` |
| `src/autom8_asana/api/middleware/core.py` | RequestIDMiddleware, RequestLoggingMiddleware, PAT redaction |
| `src/autom8_asana/api/middleware/idempotency.py` | IdempotencyMiddleware, DynamoDB/Memory/Noop stores |
| `src/autom8_asana/api/rate_limit.py` | SlowAPI Limiter, keyed by PAT prefix or remote IP |
| `src/autom8_asana/api/routes/health.py` | Three-tier health probes |
| `src/autom8_asana/entrypoint.py` | ECS/Lambda mode detection |
| `Dockerfile` | Multi-stage build, non-root user, healthcheck |

## Boundaries and Failure Modes

### Critical Invariants

1. **Shared cache provider** -- single `create_cache_provider()` in lifespan, never per-client (SCAR-004)
2. **Liveness vs readiness separation** -- `/health` always 200; `/ready` gates on cache (SCAR-011)
3. **Router registration ordering** -- `intake_resolve_router` before `resolver_router` (LB-003, correctness constraint)
4. **`_PooledClientWrapper.aclose()` is no-op** -- prevents FastAPI teardown from closing pooled state
5. **Cascade ordering fail-fast** -- `validate_cascade_ordering()` raises on misconfiguration
6. **Idempotency finalize failure risk** -- key not persisted means retry re-executes (SCAR-IDEM-001)

### Active Scars

SCAR-004 (isolated cache providers), SCAR-011/011b (health probe separation + workflow config surfacing), SCAR-015 (I/O at warm-up only), SCAR-022 (Dockerfile --no-sources constraint).

### Design Tensions

TENSION-002 (dual preload strategy), TENSION-004 (frozen deprecated query route), TENSION-007 (JWT dot-count heuristic), TENSION-009 (dual env var names for data service key).

## Knowledge Gaps

1. `api/startup.py` internal behavior not read.
2. `api/preload/progressive.py` cache readiness propagation not confirmed.
3. `api/errors.py` complete exception mapping unknown.
4. Rate limit is single-instance only (in-memory SlowAPI); no Redis multi-instance config.
5. DynamoDB idempotency table provisioning not in codebase (assumed external CDK/Terraform).
