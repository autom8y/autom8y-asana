# Integration Fit Analysis: Adopt/Trial Verdicts Against Actual Codebase

**Date**: 2026-02-23
**Author**: Integration Researcher (rnd)
**Scope**: 7 Adopt/Trial verdicts from 5 technology scout assessments
**Input Documents**: SCOUT-shared-db-decoupling, SCOUT-cache-abstraction-simplification, SCOUT-jwt-auth-consolidation, SCOUT-pkg-distribution-resilience, SCOUT-import-side-effect-elimination
**Foundation**: ARCH-REVIEW-1 (10 documents), ECOSYSTEM-TOPOLOGY-INVENTORY

---

## Method

Each verdict was mapped against the actual codebase using file-level search (Glob, Grep, Read). Effort estimates include confidence levels with explicit assumptions. "What breaks" was determined by tracing import chains and consumer counts, not by guessing.

---

## Gap 1: Shared DB Decoupling

### 1A. ADOPT: Strangler Fig (API-Mediated)

**Verdict from Scout**: Route legacy monolith reads/writes through autom8y-data REST API instead of direct MySQL.

#### Codebase Touchpoints

**Legacy monolith (`/Users/tomtenuta/Code/autom8/`):**

| Component | Path | Lines | Description |
|-----------|------|-------|-------------|
| SQL session factory | `/Users/tomtenuta/Code/autom8/sql/session.py` | 1-176 | Creates `Session = scoped_session(...)` with `mysql+pymysql` engine. `DB_DATABASE` from Secrets Manager. This is THE shared MySQL connection. |
| SQL query modules | `/Users/tomtenuta/Code/autom8/sql/queries/` | 119 files with `from sql.` imports | Direct MySQL CRUD for 30+ entity domains (ads, leads, appointments, payments, campaigns, etc.) |
| SQL utilities | `/Users/tomtenuta/Code/autom8/sql/sql_utils/main.py` | L49-237 | Generic get/upsert/delete via `Session.commit()` / `Session.rollback()` |
| Auth (HS256) | `/Users/tomtenuta/Code/autom8/app/auth.py` | L30-31 | `SECRET_KEY = os.getenv("AUTOM8_SECRET_KEY", ...)`, `ALGORITHM = "HS256"` |
| Main app | `/Users/tomtenuta/Code/autom8/app/main.py` | 1921 lines | FastAPI app with embedded auth, health, employee endpoints |

**Key finding**: The legacy monolith has 119 Python files in `sql/queries/` that import from `sql.session`. These represent the full surface area of direct MySQL access. Entity domains include: ads, adsets, campaigns, leads, appointments, payments, offers, businesses, employees, assets, insights (with complex aggregation factories), addresses, verticals, configurations, hours, neighborhoods, categories, and more.

**autom8y-data REST API (already exists):**
- CRUD endpoints for: businesses, offers, leads, appointments, payments, campaigns, ads, adsets, ad-insights, verticals, addresses, business-offers, messages, GID mappings
- Insights/analytics engine with query, execute, batch endpoints
- gRPC for same entities on port 50051

**Gap between legacy SQL and autom8y-data API:**

| Legacy SQL Domain | autom8y-data API Equivalent | Status |
|---|---|---|
| businesses | `/api/v1/businesses` | Covered |
| offers | `/api/v1/offers` | Covered (read-only) |
| leads | `/api/v1/leads` | Covered |
| appointments | `/api/v1/appointments` | Covered |
| payments | `/api/v1/payments` | Covered |
| campaigns | `/api/v1/campaigns` | Covered |
| ads | `/api/v1/ads` | Covered |
| adsets | `/api/v1/adsets` | Covered |
| verticals | `/api/v1/verticals` | Covered |
| addresses | `/api/v1/addresses` | Covered |
| employees | **NONE** | Gap -- legacy has `sql_employees`, no autom8y-data endpoint |
| insights aggregations | `/api/v1/insights` | Partially covered -- legacy has 15+ factory files, data service has engine |
| ad_optimizations | **NONE** | Gap -- 5 files, no API equivalent |
| creative_templates | **NONE** | Gap -- no API equivalent |
| asset management | **NONE** | Gap -- `assets/`, `platform_assets/`, `assets_ad_creatives/` |
| configuration/settings | **NONE** | Gap -- `configurations/`, `config_messages/` |
| hours | **NONE** | Gap -- scheduling/hours data |
| neighborhoods | **NONE** | Gap -- location data |
| split_test_configs | **NONE** | Gap -- A/B test config |
| reviews | **NONE** | Gap |

**Critical hidden dependency**: `sql/session.py` line 11-15 establishes a DIRECT connection to MySQL at module import time using `SECRET_MANAGER.get_secret("DB_DATABASE")`. The database name comes from Secrets Manager -- we need to confirm whether this is the same database as autom8y-data or a different one. The connection string at line 54 (`mysql+pymysql://{username}:{password}@{host}/{database}`) uses the same variables.

#### Effort Estimate

| Phase | Effort | Confidence | Assumptions |
|-------|--------|------------|-------------|
| Auth bridge (S2S token in legacy) | 3-5 days | High | Legacy can import `autom8y-core` (already a dependency) |
| First entity migration (reads) | 5-8 days | Medium | autom8y-data API covers the entity shape; no transform needed |
| Per-entity migration (8-10 remaining) | 2-3 days each = 16-30 days | Medium | Each domain has consistent SQL patterns |
| Gap entities (employees, assets, etc.) | 10-15 days to add API endpoints in autom8y-data | Low | Scope of 8+ missing domains is uncertain |
| Write migration | 5-10 days | Low | Write paths may have business logic embedded in SQL procedures |
| **Total** | **39-68 days (8-14 developer-weeks)** | **Low-Medium** | Assumes 1 developer, serial execution |

**ESCALATION**: The 8+ entity domains with no autom8y-data API equivalent push total effort well beyond the scout's 24-week estimate if all entities must be migrated. The realistic scope for a 6-month runway is: migrate the 10 entities that already have API coverage, defer the rest.

#### What Breaks

- Legacy code that does `from sql.queries.businesses import get_business` and expects a SQLAlchemy result object. The replacement returns a Pydantic model or dict from HTTP response. Every consumer must handle the shape change.
- Transaction semantics: `session_scope()` provides atomic commit/rollback. HTTP calls are not transactional. Any multi-entity write in the legacy codebase that relies on database transactions will need redesign.
- Performance: direct MySQL query returns in <5ms. HTTP API call adds 10-30ms network overhead (same VPC). For hot paths called in loops, this matters.

#### What's Preserved

- autom8y-data's API contract is stable and versioned
- S2S JWT auth flow is already operational
- The `BaseClient` pattern in `autom8y-core` is used by 3+ services already
- No changes needed to autom8y-asana or any satellite service

#### Effort vs Leverage

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Effort** | 5 | 8-14 weeks for a single developer; 8+ API gaps to fill |
| **Leverage** | 4 | Eliminates shared-DB coupling, enables independent deployments |
| **Ratio** | 0.8 | High leverage but very high effort |

---

### 1B. ADOPT: Schema-per-Service (Phase 0 Tactical Step)

**Verdict from Scout**: Same MySQL instance, separate schemas as immediate step.

#### Codebase Touchpoints

| Component | Path | Change |
|-----------|------|--------|
| Legacy session | `/Users/tomtenuta/Code/autom8/sql/session.py:54` | Change database in connection string |
| autom8y-data config | `/Users/tomtenuta/Code/autom8y-data/` (Alembic config) | Update schema references |
| Terraform RDS | `/Users/tomtenuta/Code/autom8y/terraform/` | MySQL GRANT statements |
| auth-mysql-sync | `/Users/tomtenuta/Code/autom8y/services/auth-mysql-sync/` | Update source schema |

#### Effort Estimate

| Phase | Effort | Confidence | Assumptions |
|-------|--------|------------|-------------|
| Schema creation + GRANT | 0.5 days | High | DBA access available |
| Table ownership assignment | 1-2 days | Medium | Need to map which tables are owned by which service |
| Connection string updates | 0.5 days | High | Straightforward config change |
| Alembic migration updates | 1-2 days | Medium | Alembic supports schema targeting |
| Testing + validation | 2 days | Medium | Need staging environment |
| **Total** | **4-7 days (1-1.5 developer-weeks)** | **Medium** | Assumes DBA access and staging env |

#### What Breaks

- Cross-schema queries in legacy code that use unqualified table names. Every SQL query in the 119 `sql/queries/` files would need `schema.table` qualification OR the connection default database would need to remain the same (negating much of the benefit).
- Alembic migrations that assume a single schema.

#### What's Preserved

- All application code if connection string defaults to the correct schema
- All existing queries (if default database matches)
- Performance (same MySQL instance, negligible cross-schema overhead)

#### Effort vs Leverage

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Effort** | 2 | ~1 week, low risk |
| **Leverage** | 2 | Creates logical boundaries but does not enforce them; easy to bypass |
| **Ratio** | 1.0 | Low effort, low leverage -- a stepping stone, not a solution |

---

## Gap 2: Cache Simplification

### 2A. ADOPT: Concept Consolidation (Unified Freshness Vocabulary + Protocol + Observability)

**Verdict from Scout**: Unify freshness vocabulary, add DataFrameCacheProtocol, shared observability. Target: 31 concepts to ~25.

#### Codebase Touchpoints

**Freshness enum definitions (4 enums to collapse to 2):**

| Current Enum | File | Line | Values | Consumers (src) | Consumers (tests) |
|---|---|---|---|---|---|
| `Freshness` | `cache/models/freshness.py` | 19 | STRICT, EVENTUAL, IMMEDIATE | 9 files, ~15 refs | ~10 refs |
| `FreshnessMode` | `cache/integration/freshness_coordinator.py` | 30-41 | STRICT, EVENTUAL, IMMEDIATE | 5 files, ~33 refs | ~36 refs |
| `FreshnessClassification` | `cache/models/freshness_stamp.py` | 37-48 | FRESH, APPROACHING_STALE, STALE | 4 files, ~19 refs | ~15 refs |
| `FreshnessStatus` | `cache/integration/dataframe_cache.py` | 45-53 | FRESH, STALE_SERVABLE, EXPIRED_SERVABLE, SCHEMA_MISMATCH, WATERMARK_STALE, CIRCUIT_LKG | 5 files, ~25 refs | ~14 refs |

**Total source references**: 113 occurrences across 15 source files.
**Total test references**: 149 occurrences across 15 test files.

**Result types to merge (2 to 1):**

| Current Type | File | Line | Consumers |
|---|---|---|---|
| `FreshnessResult` | `cache/integration/freshness_coordinator.py` | 44-60 | freshness_coordinator.py, unified provider |
| `FreshnessInfo` | `cache/integration/dataframe_cache.py` | 56-72 | dataframe_cache.py, dataframe_view.py, query_service.py |

**DataFrameCacheProtocol (new, per ADR-0067):**

| Component | File | Change |
|-----------|------|--------|
| Protocol definition | `src/autom8_asana/protocols/cache.py` | Add `DataFrameCacheProtocol` |
| Factory injection | `src/autom8_asana/cache/integration/factory.py` | Replace singleton with factory |
| Existing protocol | `src/autom8_asana/protocols/cache.py` | Already has `CacheProvider` protocol (3 freshness refs) |

**Shared observability:**

| Component | File | Change |
|-----------|------|--------|
| Entity cache metrics | `src/autom8_asana/cache/providers/unified.py` | 9 freshness-related refs |
| DataFrame cache stats | `src/autom8_asana/cache/integration/dataframe_cache.py` | Internal `_stats` dict to delegate to CacheMetrics |

**Test `.reset()` sites**: 100 occurrences across 25 test files. These remain but become more predictable after protocol alignment.

#### Effort Estimate

| Phase | Effort | Confidence | Assumptions |
|-------|--------|------------|-------------|
| Freshness vocabulary collapse (FreshnessIntent + FreshnessState + FreshnessCheck) | 4-5 days | High | Mechanical refactoring with type alias bridge |
| DataFrameCacheProtocol + factory DI | 3-4 days | High | ADR-0067 already specifies design |
| Shared observability (CacheMetrics unification) | 2-3 days | Medium | DataFrame _stats dict delegation |
| EntryType consolidation | 1 day | High | Merge 2 enum values |
| Test updates (149 refs across 15 files) | 3-4 days | Medium | Type alias bridge reduces churn |
| Documentation + ADR-0067 update | 1 day | High | |
| **Total** | **14-18 days (3-4 developer-weeks)** | **Medium-High** | Assumes incremental delivery, type alias bridge for backward compat |

#### What Breaks

- **Direct enum imports**: 113 source refs + 149 test refs reference the old names. Type aliases (`FreshnessMode = FreshnessIntent`) at old locations mitigate this during migration.
- **FreshnessStatus.STALE_SERVABLE consumers**: The SWR behavior change from state-based to behavior-based (`if state == APPROACHING_STALE and swr_enabled`) affects `dataframe_cache.py` (main consumer) and `dataframe_view.py` (6 refs).
- **DataFrameCache singleton users**: `factory.py` (4 refs) and any module that calls `get_dataframe_cache()` must switch to DI.

#### What's Preserved

- All cache backend logic (Redis, S3, Memory tiers)
- All cache operational behavior (TTL, SWR, circuit breaker, coalescing)
- The 12/14 intentional divergences documented in ADR-0067
- CacheEntry and DataFrameCacheEntry internal structures

#### Effort vs Leverage

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Effort** | 3 | 3-4 weeks, mechanical but touches many files |
| **Leverage** | 3 | Reduces cognitive overhead from 31 to ~25 concepts, shared mental model |
| **Ratio** | 1.0 | Moderate both ways -- essential for maintainability, not transformational |

---

### 2B. TRIAL: Freshness State Machine Collapse (4 enums to 2)

**Verdict from Scout**: Collapse 4 freshness enums to 2 as a 2-day spike.

This is the first phase of 2A above. The spike validates the `FreshnessIntent`/`FreshnessState`/`FreshnessCheck` design before committing to the full consolidation.

#### Codebase Touchpoints

Same freshness enum files as 2A. The spike scope is:

1. Define `FreshnessIntent`, `FreshnessState`, `FreshnessCheck` in a new `cache/models/freshness_unified.py`
2. Add type aliases at old import locations
3. Validate with `pytest tests/unit/cache/ -v` (the 15 test files with 149 freshness refs)

#### Effort Estimate

| Phase | Effort | Confidence | Assumptions |
|-------|--------|------------|-------------|
| Spike: define new enums + aliases | 1 day | High | Pure refactoring |
| Spike: validate test suite passes | 1 day | High | Type aliases provide backward compat |
| **Total** | **2 days** | **High** | Time-boxed spike, not full migration |

#### What Breaks

Nothing -- the spike adds new types alongside old ones. The old types remain functional via aliases.

#### Effort vs Leverage

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Effort** | 1 | 2 days, zero risk |
| **Leverage** | 2 | Validates the design; does not complete the migration |
| **Ratio** | 2.0 | Excellent bang-for-buck as a validation step |

---

## Gap 3: JWT Auth Consolidation

### 3A. ADOPT: Dual-Validation Middleware

**Verdict from Scout**: Legacy monolith accepts both HS256 and RS256 during migration.

#### Codebase Touchpoints

**Legacy auth module:**

| Component | Path | Lines | Key Detail |
|-----------|------|-------|------------|
| Secret key | `/Users/tomtenuta/Code/autom8/app/auth.py:30` | `SECRET_KEY = os.getenv("AUTOM8_SECRET_KEY", ...)` | Hardcoded fallback in source |
| Algorithm | `/Users/tomtenuta/Code/autom8/app/auth.py:31` | `ALGORITHM = "HS256"` | Single algorithm, no RS256 path |
| JWT library | `/Users/tomtenuta/Code/autom8/app/auth.py:21` | `from jose import JWTError, jwt` | python-jose (unmaintained since 2021) |
| Token validation | `/Users/tomtenuta/Code/autom8/app/auth.py` | `jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])` (inferred from imports) | HS256 only |
| Auth consumers | `/Users/tomtenuta/Code/autom8/app/main.py:17-28` | Imports `get_current_user_required`, `verify_employee_by_email`, etc. | All routes use auth dependency |
| Health endpoint | `/Users/tomtenuta/Code/autom8/app/health.py` | Has auth imports | Even health checks may hit auth |

**Changes needed in legacy monolith (estimated ~200 LOC):**

1. Add JWKS client (~50 LOC): Fetch from `https://auth.api.autom8y.io/.well-known/jwks.json`, cache with TTL
2. Add RS256 validation path (~40 LOC): Inspect JWT `alg` header, route to HS256 or RS256 validation
3. Add feature flag (~10 LOC): `ACCEPT_RS256=true/false` env var
4. Add deprecation metric (~20 LOC): Counter for HS256 token usage
5. Update token decode (~30 LOC): `algorithms=["RS256", "HS256"]` with explicit key routing
6. Tests (~50 LOC): Algorithm confusion regression, dual-mode validation

**No changes needed in:**
- autom8y-asana (already validates RS256 via autom8y-auth SDK)
- autom8y-data (already validates RS256 via autom8y-auth SDK)
- auth service (already issues RS256 + serves JWKS)

**Hidden dependency**: The legacy `app/auth.py:48` creates `ssm_client = boto3.client("ssm")` at module level -- this suggests secret management is partially via SSM, partially via Secrets Manager (`SECRET_MANAGER = ENV.SecretManager()` in `sql/session.py`). The JWKS fetch would be a third mechanism. Need to ensure httpx or requests is available in the legacy monolith for JWKS fetch.

**Caller inventory** (services that send tokens TO the legacy monolith):
- Unknown. The ecosystem topology shows no modern service calling the legacy monolith directly. The legacy monolith appears to be called by: (a) the web app (`app.autom8y.io`), (b) Slack bots, (c) cron/EventBridge-triggered entry points. All of these would need to switch from HS256 to RS256 tokens during the migration window.

#### Effort Estimate

| Phase | Effort | Confidence | Assumptions |
|-------|--------|------------|-------------|
| Add RS256 validation to legacy auth | 3-4 days | High | python-jose supports dual-algo; httpx available for JWKS |
| Feature flag + deprecation metric | 1 day | High | |
| Testing (dual-mode + algorithm confusion) | 2-3 days | High | |
| Caller migration (60-90 day window) | 0 days (calendar time, not dev time) | Medium | Callers switch independently |
| HS256 removal + cleanup | 1-2 days | High | After 90-day window |
| **Total** | **7-10 days (1.5-2 developer-weeks)** | **High** | Assumes legacy monolith can be modified and deployed |

#### What Breaks

- Nothing breaks immediately -- dual-validation is additive. HS256 continues working.
- During caller migration: if a caller switches to RS256 before the legacy monolith is deployed with RS256 support, their requests fail with 401.
- After HS256 removal: any caller still using HS256 tokens gets 401.

#### What's Preserved

- All existing HS256 auth behavior during migration window
- All satellite service auth (RS256 via autom8y-auth SDK, unchanged)
- Auth service JWKS endpoint (unchanged)

#### Effort vs Leverage

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Effort** | 2 | ~2 weeks, well-understood pattern |
| **Leverage** | 4 | Eliminates split trust domain, enables cross-service audit, unblocks ALB JWT verification |
| **Ratio** | 2.0 | High leverage, moderate effort -- strong candidate |

---

## Gap 4: Package Distribution

### 4A. ADOPT: CI Cache Hardening

**Verdict from Scout**: Enable uv cache in GitHub Actions workflows.

#### Codebase Touchpoints

**autom8y-asana (this repo):**

| Workflow | Path | Current setup-uv | Cache Enabled? |
|----------|------|-------------------|----------------|
| Test (fast-tests) | `.github/workflows/test.yml:25-27` | `astral-sh/setup-uv@v2` | **NO** |
| Test (full-tests) | `.github/workflows/test.yml:89-91` | `astral-sh/setup-uv@v2` | **NO** |
| Test (integration-tests) | `.github/workflows/test.yml:141-143` | `astral-sh/setup-uv@v2` | **NO** |
| Satellite Dispatch | `.github/workflows/satellite-dispatch.yml` | N/A (no uv) | N/A |

**autom8y monorepo (platform CI):**

| Workflow | Path | Cache Enabled? |
|----------|------|----------------|
| `sdk-ci.yml` (lint job) | line 79-82 | **YES** (`enable-cache: true`) |
| `sdk-ci.yml` (audit job) | line 140 | **NO** |
| `sdk-ci.yml` (type-check job) | line 166-168 | **NO** |
| `service-ci.yml` | line 57-60 | **YES** (`enable-cache: true`) |
| `ecosystem-health.yml` | line 34-37 | **YES** (`enable-cache: true`) |
| `sdk-publish-v2.yml` (test job) | line 116-119 | **YES** (`enable-cache: true`) |
| `sdk-publish-v2.yml` (publish job) | line 235-237 | **NO** |
| `auth-mysql-sync-deploy.yml` | line 53 | **NO** |
| `build-api-docs.yml` | line 54-56 | **NO** |

**Summary of gaps:**

| Repo | Workflows Missing Cache | Total uv setup-uv Calls |
|------|------------------------|------------------------|
| autom8y-asana | 3 (all 3 test jobs) | 3 |
| autom8y (monorepo) | 4 (sdk-ci audit, sdk-ci type-check, sdk-publish publish, auth-mysql-sync-deploy, build-api-docs) | 9 |
| **Total** | **7 setup-uv calls missing cache** | 12 |

**Additional findings:**
- autom8y-asana uses `@v2` while monorepo uses `@v4`. Version upgrade recommended alongside cache enablement.
- No `uv cache prune --ci` anywhere. Adding this would optimize cache size.

#### Effort Estimate

| Phase | Effort | Confidence | Assumptions |
|-------|--------|------------|-------------|
| autom8y-asana: Add `enable-cache: true` to 3 jobs | 0.5 hours | High | YAML change only |
| autom8y-asana: Upgrade `@v2` to `@v4` | 0.5 hours | High | |
| autom8y monorepo: Add cache to 4-5 missing jobs | 1 hour | High | YAML change only |
| Add `uv cache prune --ci` step | 0.5 hours | High | |
| Verify cache hit rates (1 week observation) | 0 dev days (calendar time) | High | |
| **Total** | **2-3 hours (<0.5 developer-days)** | **High** | Trivial YAML changes |

#### What Breaks

Nothing. Cache is additive. Cache miss falls through to normal package resolution.

#### What's Preserved

Everything. This is a pure CI optimization with zero application code changes.

#### Effort vs Leverage

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Effort** | 1 | <0.5 days, trivial YAML changes |
| **Leverage** | 3 | Eliminates ~95% of CodeArtifact dependency for routine CI runs, speeds up every build |
| **Ratio** | 3.0 | Best ratio of any item -- immediate, risk-free improvement |

---

## Gap 5: Import Side Effects

### 5A. ADOPT: Explicit Bootstrap + Deferred Resolution

**Verdict from Scout**: Replace `register_all_models()` import-time call with explicit `app.bootstrap()`.

#### Codebase Touchpoints

**Registration trigger (the import-time side effect):**

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| Import-time call | `src/autom8_asana/models/business/__init__.py` | 64-66 | `from _bootstrap import register_all_models; register_all_models()` |
| Bootstrap function | `src/autom8_asana/models/business/_bootstrap.py` | 22-131 | Idempotent registration of 16 entity types into ProjectRegistry |
| Bootstrap state | `src/autom8_asana/models/business/_bootstrap.py` | 19, 134-150 | `_BOOTSTRAP_COMPLETE` flag, `is_bootstrap_complete()`, `reset_bootstrap()` |
| Defensive call | `src/autom8_asana/models/business/detection/tier1.py` | 93-105 | Calls `register_all_models()` if detection finds empty registry |

**Entry points that need explicit `bootstrap()` call:**

| Entry Point | File | Current Bootstrap? |
|-------------|------|--------------------|
| API lifespan | `src/autom8_asana/api/lifespan.py:35` | Implicit via `from models.business import ...` in startup.py |
| Cache warmer Lambda | `src/autom8_asana/lambda_handlers/cache_warmer.py` | Implicit via model imports |
| Cache invalidate Lambda | `src/autom8_asana/lambda_handlers/cache_invalidate.py` | Implicit via model imports |
| Workflow handler Lambda | `src/autom8_asana/lambda_handlers/workflow_handler.py` | Implicit via model imports |
| Conversation audit Lambda | `src/autom8_asana/lambda_handlers/conversation_audit.py` | Implicit via model imports |
| Insights export Lambda | `src/autom8_asana/lambda_handlers/insights_export.py` | Implicit via model imports |
| Entrypoint (CLI) | `src/autom8_asana/entrypoint.py:71` | Implicit via model imports |
| Test conftest | `tests/conftest.py` | Implicit via model imports |

**Registry singletons affected:**

| Registry | Current Access Pattern | `.reset()` Sites (tests) |
|----------|----------------------|-------------------------|
| `ProjectTypeRegistry` | `get_registry()` singleton | Multiple (tracked in test refs) |
| `SchemaRegistry` | `get_instance()` with `_ensure_initialized()` | Multiple |
| `MetricRegistry` | `get_instance()` singleton | Multiple |
| `WorkspaceProjectRegistry` | `get_workspace_registry()` singleton | Multiple |

**Total `.reset()` occurrences in tests**: 100 across 25 test files.

**Deferred resolution (Approach 6 from scout):**
- `SchemaRegistry._ensure_initialized()` already implements this pattern (file: `src/autom8_asana/cache/integration/schema_providers.py`)
- `ProjectTypeRegistry` needs the same `_ensure_bootstrapped()` guard

#### Effort Estimate

| Phase | Effort | Confidence | Assumptions |
|-------|--------|------------|-------------|
| Create `bootstrap()` function in `autom8_asana/__init__.py` or `core/bootstrap.py` | 1 day | High | Wraps `register_all_models()` |
| Add `_ensure_bootstrapped()` to ProjectTypeRegistry | 1 day | High | Follows existing SchemaRegistry pattern |
| Add explicit `bootstrap()` to 6 Lambda handlers | 1 day | High | One-line addition per handler |
| Add explicit `bootstrap()` to API lifespan | 0.5 days | High | Already has startup hook |
| Remove import-time `register_all_models()` from `__init__.py:66` | 0.5 days | High | Single line removal |
| Fix broken tests (~50-100 affected based on .reset() count) | 3-5 days | Medium | Need session-scoped bootstrap fixture |
| Add `bootstrap()` to test conftest.py | 0.5 days | High | |
| Verify all entry points + CI green | 1-2 days | Medium | Edge cases in import ordering |
| **Total** | **8-11 days (1.5-2.5 developer-weeks)** | **Medium-High** | The 3-5 days for test fixes is the uncertainty |

#### What Breaks

- **Any code that does `from autom8_asana.models.business import X` and immediately calls `detect_entity_type()`** without bootstrap will get `None` from registry lookups. The `_ensure_bootstrapped()` guard mitigates this.
- **Test files that import business models at module level** and expect registry to be populated. The session-scoped `conftest.py` fixture handles this.
- **Scripts or notebooks** that `import autom8_asana.models.business` without calling `bootstrap()`. The deferred resolution fallback handles this gracefully.

#### What's Preserved

- All 16 entity type registrations (same types, same order)
- `register_all_models()` function (still exists, just not called at import time)
- `reset_bootstrap()` for test isolation (still works)
- `__init_subclass__` and `__set_name__` descriptor hooks (fire at class definition time regardless)
- All 10,552 tests (after fixture update)

#### Effort vs Leverage

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Effort** | 2 | 1.5-2.5 weeks, well-understood Django pattern |
| **Leverage** | 3 | Eliminates import ordering fragility, improves test isolation, reduces Lambda cold starts |
| **Ratio** | 1.5 | Good leverage, moderate effort |

---

## Summary Table: All 7 Items

| # | Gap | Verdict | Effort (dev-days) | Effort Score | Leverage Score | Ratio | Confidence |
|---|-----|---------|-------------------|-------------|---------------|-------|------------|
| 1A | Shared DB: Strangler Fig | ADOPT | 39-68 | 5 | 4 | 0.8 | Low-Medium |
| 1B | Shared DB: Schema-per-Service | ADOPT | 4-7 | 2 | 2 | 1.0 | Medium |
| 2A | Cache: Concept Consolidation | ADOPT | 14-18 | 3 | 3 | 1.0 | Medium-High |
| 2B | Cache: Freshness Collapse Spike | TRIAL | 2 | 1 | 2 | 2.0 | High |
| 3A | JWT: Dual-Validation | ADOPT | 7-10 | 2 | 4 | 2.0 | High |
| 4A | Package: CI Cache Hardening | ADOPT | 0.25 | 1 | 3 | 3.0 | High |
| 5A | Import: Explicit Bootstrap | ADOPT | 8-11 | 2 | 3 | 1.5 | Medium-High |

**Total effort**: 74.25-116.25 developer-days = 15-23 developer-weeks

**Budget check**: At 40 developer-days budget, items 4A + 2B + 3A + 5A + 1B fit (~21.25-30.25 days). Items 2A (14-18 days) and 1A (39-68 days) exceed the remaining budget individually.

---

## Prioritized Execution Order

Sequenced by Leverage/Effort ratio (best bang-for-buck first), with dependency constraints.

### Priority 1: CI Cache Hardening (Gap 4A)
- **Ratio**: 3.0 (best)
- **Effort**: <0.5 days
- **Dependencies**: None
- **Rollback**: Remove `enable-cache: true` from YAML
- **Files to change**:
  - `/Users/tomtenuta/Code/autom8y-asana/.github/workflows/test.yml` -- lines 25-27, 89-91, 141-143 (add `enable-cache: true`, upgrade to `@v4`)
  - `/Users/tomtenuta/Code/autom8y/.github/workflows/sdk-ci.yml` -- lines 140, 166 (add `enable-cache: true`)
  - `/Users/tomtenuta/Code/autom8y/.github/workflows/sdk-publish-v2.yml` -- line 235 (add `enable-cache: true`)
  - `/Users/tomtenuta/Code/autom8y/.github/workflows/auth-mysql-sync-deploy.yml` -- line 53 (add `enable-cache: true`)
  - `/Users/tomtenuta/Code/autom8y/.github/workflows/build-api-docs.yml` -- line 54 (add `enable-cache: true`)

### Priority 2: Freshness State Machine Collapse Spike (Gap 2B)
- **Ratio**: 2.0 (tied with 3A)
- **Effort**: 2 days
- **Dependencies**: None
- **Rollback**: Delete the new file, remove aliases
- **Files to change**:
  - NEW: `src/autom8_asana/cache/models/freshness_unified.py`
  - `src/autom8_asana/cache/models/freshness.py` -- add alias
  - `src/autom8_asana/cache/integration/freshness_coordinator.py` -- add alias at line 30
  - `src/autom8_asana/cache/models/freshness_stamp.py` -- add alias at line 37
  - `src/autom8_asana/cache/integration/dataframe_cache.py` -- add alias at line 45

### Priority 3: JWT Dual-Validation Middleware (Gap 3A)
- **Ratio**: 2.0 (tied with 2B)
- **Effort**: 7-10 days
- **Dependencies**: None (this repo is not changed; changes are in legacy monolith)
- **Rollback**: Revert legacy monolith deployment (HS256 continues working)
- **Files to change** (in `/Users/tomtenuta/Code/autom8/`):
  - `app/auth.py` -- add RS256 validation path, JWKS fetch, dual-algorithm routing (~150 LOC)
  - `app/main.py` -- add `ACCEPT_RS256` env var to settings
  - NEW: `app/jwks.py` -- JWKS client with in-memory cache (~50 LOC)

### Priority 4: Explicit Bootstrap + Deferred Resolution (Gap 5A)
- **Ratio**: 1.5
- **Effort**: 8-11 days
- **Dependencies**: None
- **Rollback**: Re-add `register_all_models()` to `__init__.py:66`
- **Files to change**:
  - `src/autom8_asana/models/business/__init__.py` -- remove line 66
  - NEW or `src/autom8_asana/core/bootstrap.py` -- `bootstrap()` function
  - `src/autom8_asana/models/business/registry.py` -- add `_ensure_bootstrapped()` to `ProjectTypeRegistry.lookup()`
  - `src/autom8_asana/api/lifespan.py` -- add `bootstrap()` call in startup sequence
  - `src/autom8_asana/lambda_handlers/cache_warmer.py` -- add `bootstrap()` call
  - `src/autom8_asana/lambda_handlers/cache_invalidate.py` -- add `bootstrap()` call
  - `src/autom8_asana/lambda_handlers/workflow_handler.py` -- add `bootstrap()` call
  - `src/autom8_asana/lambda_handlers/conversation_audit.py` -- add `bootstrap()` call
  - `src/autom8_asana/lambda_handlers/insights_export.py` -- add `bootstrap()` call
  - `src/autom8_asana/entrypoint.py` -- add `bootstrap()` call
  - `tests/conftest.py` -- add session-scoped `bootstrap()` fixture
  - ~25 test files -- update `.reset()` patterns

### Priority 5: Schema-per-Service (Gap 1B)
- **Ratio**: 1.0
- **Effort**: 4-7 days
- **Dependencies**: Requires DBA access, staging environment confirmation
- **Rollback**: Revert schema names, restore GRANT permissions
- **Files to change** (cross-repo):
  - `/Users/tomtenuta/Code/autom8/sql/session.py:54` -- update database in connection string
  - `/Users/tomtenuta/Code/autom8y-data/` -- Alembic env.py and migration files
  - `/Users/tomtenuta/Code/autom8y/terraform/` -- MySQL GRANT statements (new)

### Priority 6: Cache Concept Consolidation (Gap 2A)
- **Ratio**: 1.0
- **Effort**: 14-18 days
- **Dependencies**: Priority 2 (freshness spike) should complete first as validation
- **Rollback**: Revert to old enum names (type aliases provide bridge)
- **Defer trigger**: Only execute after Priority 2 spike validates the design. If spike reveals problems, reassess.

### Priority 7: Strangler Fig Full Migration (Gap 1A)
- **Ratio**: 0.8
- **Effort**: 39-68 days
- **Dependencies**: Priority 5 (schema-per-service) as Phase 0; Priority 3 (JWT dual-validation) as prerequisite for S2S auth
- **Rollback**: Each entity migration is independently reversible (revert to direct MySQL)
- **ESCALATION**: This item exceeds the 40-day budget on its own. **Recommend scoping to only the entities that already have autom8y-data API coverage (10 entities, ~25-40 days) and deferring the 8+ gap entities.** The gap entities (employees, assets, ad_optimizations, creative_templates, configurations, hours, neighborhoods, split_test_configs, reviews) would need API endpoints built in autom8y-data first, adding another 10-15 days.

---

## Execution Plan: Fits Within 40 Developer-Days

| Priority | Item | Days | Cumulative | Phase |
|----------|------|------|------------|-------|
| P1 | CI Cache Hardening | 0.25 | 0.25 | Immediate (Week 1, Day 1) |
| P2 | Freshness Collapse Spike | 2 | 2.25 | Week 1 |
| P3 | JWT Dual-Validation | 7-10 | 9.25-12.25 | Weeks 2-3 |
| P4 | Explicit Bootstrap | 8-11 | 17.25-23.25 | Weeks 3-5 |
| P5 | Schema-per-Service | 4-7 | 21.25-30.25 | Week 5-6 |
| P6 | Cache Consolidation | 14-18 | 35.25-48.25 | Weeks 6-10 (may exceed budget) |

**Within 40-day budget**: P1 through P5 are guaranteed to fit (21.25-30.25 days). P6 fits if estimates land on the low end. P7 (Strangler Fig) is deferred.

**Rollback points between phases**:
- After P1: CI works faster, no other dependencies
- After P2: Freshness spike validated or rejected; informs P6 decision
- After P3: Legacy monolith accepts RS256; callers can migrate over 60-90 days
- After P4: Import ordering fragility eliminated; Lambda cold starts improved
- After P5: Logical schema boundaries established; strangler fig can begin later

---

## Hidden Dependencies Surfaced

1. **Legacy monolith has 119 SQL query files** -- far more than the scout's entity-level assessment suggests. The migration surface is wider than documented.

2. **8+ entity domains have NO autom8y-data API equivalent** -- employees, assets, ad_optimizations, creative_templates, configurations, hours, neighborhoods, split_test_configs. These gaps must be filled before full strangler fig migration.

3. **Legacy `sql/session.py` connects at module import time** (line 27-40: retry loop at import). This means any import of the SQL module triggers a MySQL connection. The strangler fig migration must replace this import-time behavior, not just the query layer.

4. **Legacy auth uses BOTH SSM and Secrets Manager** (`ssm_client` at auth.py:48, `SECRET_MANAGER` at session.py:11). The JWKS fetch for JWT dual-validation introduces a third secret/config mechanism.

5. **autom8y-asana test.yml uses `setup-uv@v2`** while the monorepo uses `@v4`. Version mismatch could cause subtle caching differences.

6. **The freshness enum consumer count is higher than expected**: 113 source refs + 149 test refs = 262 total references to collapse. Type alias bridge is essential.

7. **`register_all_models()` has a defensive re-call in `detection/tier1.py:93-105`** -- this is a fallback that fires if detection finds an empty registry. The deferred resolution pattern must account for this existing safety net (either replace it or ensure compatibility).

---

## Artifact Verification

| Artifact | Path | Verified |
|----------|------|----------|
| Integration Fit Analysis | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/INTEGRATION-FIT-ANALYSIS.md` | Written |
| SCOUT-shared-db-decoupling (input) | `/Users/tomtenuta/Code/autom8y-asana/docs/rnd/SCOUT-shared-db-decoupling.md` | Read |
| SCOUT-cache-abstraction-simplification (input) | `/Users/tomtenuta/Code/autom8y-asana/docs/rnd/SCOUT-cache-abstraction-simplification.md` | Read |
| SCOUT-jwt-auth-consolidation (input) | `/Users/tomtenuta/Code/autom8y-asana/docs/rnd/SCOUT-jwt-auth-consolidation.md` | Read |
| SCOUT-pkg-distribution-resilience (input) | `/Users/tomtenuta/Code/autom8y-asana/docs/rnd/SCOUT-pkg-distribution-resilience.md` | Read |
| SCOUT-import-side-effect-elimination (input) | `/Users/tomtenuta/Code/autom8y-asana/docs/rnd/SCOUT-import-side-effect-elimination.md` | Read |
| ECOSYSTEM-TOPOLOGY-INVENTORY (input) | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ECOSYSTEM-TOPOLOGY-INVENTORY.md` | Read |
| Legacy auth.py | `/Users/tomtenuta/Code/autom8/app/auth.py` | Read (lines 1-100) |
| Legacy session.py | `/Users/tomtenuta/Code/autom8/sql/session.py` | Read (full) |
| Legacy main.py | `/Users/tomtenuta/Code/autom8/app/main.py` | Read (lines 1-100) |
| autom8y-asana test.yml | `/Users/tomtenuta/Code/autom8y-asana/.github/workflows/test.yml` | Read (full) |
| autom8y-asana _bootstrap.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/_bootstrap.py` | Read (full) |
| autom8y-asana models/business/__init__.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/__init__.py` | Read (lines 1-70) |
| autom8y-asana freshness enums | Multiple cache/ files | Read + Grep (113 src refs, 149 test refs) |
| autom8y monorepo workflows | `/Users/tomtenuta/Code/autom8y/.github/workflows/` | Grep for setup-uv + enable-cache |
