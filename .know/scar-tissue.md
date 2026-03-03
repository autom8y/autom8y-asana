---
domain: scar-tissue
generated_at: "2026-02-27T11:21:29Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "73b6e61"
confidence: 0.75
format_version: "1.0"
---

# Codebase Scar Tissue

## Failure Catalog Completeness

### SCAR-001: SaveSession Custom Field Snapshot Ordering (DEF-001)

**What failed**: Custom field accessor was not cleared before capturing entity snapshot after CRUD success. This caused stale custom field modifications to persist across SaveSession commit cycles, leading to repeated writes of already-saved values.

**Fix commit**: Identified in `persistence/session.py` line 997
**Fix location**: `src/autom8_asana/persistence/session.py`, `_post_commit_cleanup()` method
**Marker**: `# DEF-001 FIX: Order matters - clear accessor BEFORE capturing snapshot`

**Defensive pattern**: Order enforcement -- custom field tracking reset via `_reset_custom_field_tracking(entity)` MUST happen before `_tracker.mark_clean(entity)`. Per ADR-0074.

**Agent relevance**: Any agent modifying SaveSession commit flow or custom field tracking. Critical to preserve operation ordering.

---

### SCAR-002: Schema Field Validation on Resolver Routes (DEF-001)

**What failed**: Resolver endpoint accepted arbitrary field names without validation, allowing invalid field requests to propagate to the DataFrame layer.

**Fix location**: `src/autom8_asana/api/routes/resolver.py`, line 310
**Marker**: `# Validate requested fields against schema (DEF-001)`

**Defensive pattern**: Schema validation guard at API boundary using `validate_fields()` before any DataFrame access.

**Agent relevance**: Any agent adding new resolver or query endpoints must add field validation.

---

### SCAR-003: Shared CacheProvider Across Client Pool (DEF-005)

**What failed**: Each pooled client created its own CacheProvider, causing cache fragmentation -- warm data in one client was invisible to others. SWR writes to S3 succeeded but memory promotion was isolated.

**Fix locations**:
- `src/autom8_asana/api/lifespan.py`, lines 103, 121 -- shared CacheProvider creation
- `src/autom8_asana/api/client_pool.py`, line 201 -- injection into pooled clients
**Marker**: `# DEF-005: Create a shared SDK CacheProvider once so warm-up tasks and` / `# DEF-005: inject shared cache_provider so pooled clients share`

**Defensive pattern**: Single CacheProvider instance created in lifespan, injected into all pooled clients. Do not create per-client cache providers.

**Agent relevance**: Any agent modifying client pool creation, lifespan initialization, or cache provider DI.

---

### SCAR-004: SWR Memory Cache Promotion Bug

**What failed**: `BuildResult.total_rows` returned 0 on SWR resume because it counted only SUCCESS sections, not SKIPPED ones. SWR wrote fresh data to S3 but never promoted to memory. All 6 entity types served stale data indefinitely.

**Fix commit**: `9fbbb29` -- `fix(swr): fix memory cache promotion when all sections resume from S3`
**Fix location**: `src/autom8_asana/dataframes/` (build_result.py -- `total_rows` now uses `len(self.dataframe)` when available)

**Defensive pattern**: `total_rows` property computes from actual DataFrame when available; `fetched_rows` added for API-work metric (counts only fresh fetches). Tests verify both code paths.

**Agent relevance**: Any agent modifying build result tracking, SWR logic, or cache warming pipeline.

---

### SCAR-005: NameGid Forward Reference Resolution

**What failed**: Pydantic v2 models using `from __future__ import annotations` with `NameGid` imported only under `TYPE_CHECKING` could not resolve the forward reference at runtime. This caused `ValidationError` on model construction.

**Fix commit**: `7b82a92` -- `fix(tests): resolve NameGid forward references via explicit model_rebuild`
**Fix location**: `tests/conftest.py`, `_bootstrap_session()` fixture

**Defensive pattern**: Session-scoped autouse fixture calls `Task.model_rebuild(_types_namespace={"NameGid": NameGid})` first (propagates to BusinessEntity subclasses), then rebuilds all other resource models. This runs once per test session.

**Agent relevance**: Any agent adding new Pydantic models with NameGid references. Must add the model to the rebuild list in `tests/conftest.py`.

---

### SCAR-006: Health Endpoint JWKS Mock Targets

**What failed**: Health check tests mocked JWKS verification at the wrong import path, causing tests to hit real JWKS endpoints during CI. This produced flaky failures when the auth service was unreachable.

**Fix commit**: `d4db4a9` -- `fix(tests): rework health JWKS mock targets to patch Autom8yHttpClient`
**Fix location**: `tests/unit/api/routes/` (health test files)

**Defensive pattern**: Mock targets must patch at the point of use (`Autom8yHttpClient` in the auth module), not at the point of definition.

**Agent relevance**: Any agent modifying auth-related tests. Always verify mock targets are patching at the correct import path.

---

### SCAR-007: Metrics Count Aggregation Format + None Guard

**What failed**: Count aggregation returned incorrect format and crashed on empty DataFrames with `None` value.

**Fix commit**: `92b474f` -- `fix(metrics): correct format for count aggregation and guard None on empty DataFrame`
**Fix location**: Metrics compute module

**Defensive pattern**: Guard against `None` on empty DataFrame results. Ensure aggregation output format matches consumer expectations.

**Agent relevance**: Any agent modifying metrics aggregation or query engine aggregate responses.

---

### SCAR-008: Cascade Hierarchy Warming Gaps

**What failed**: Cascade resolution could fail when hierarchy warming was incomplete, leaving business entities without their parent chain.

**Fix commit**: `6cf457e` -- `fix(cache): harden cascade resolution against hierarchy warming gaps`
**Fix location**: Cache hierarchy warming code

**Defensive pattern**: Cascade resolution now handles missing hierarchy entries gracefully instead of raising.

**Agent relevance**: Any agent modifying cascading field logic or hierarchy warming.

---

### SCAR-009: Data Client Entity Type Mapping

**What failed**: `ad_questions` entity type was not mapped to `question` in the DataServiceClient, causing 404s for ad question data.

**Fix commit**: `79ee103` -- `fix(data-client): map ad_questions entity type to question`
**Fix location**: `src/autom8_asana/clients/data/`

**Defensive pattern**: Entity type mapping in DataServiceClient must cover all entity aliases.

**Agent relevance**: Any agent adding new entity types that require DataServiceClient integration.

---

### SCAR-010: Section Timeline Pre-Computation

**What failed**: Section timeline queries were slow (computing on-the-fly from stories), causing timeout issues for large workspaces.

**Fix commit**: `8b5813e` -- `fix(timeline): pre-compute timelines at warm-up, serve from memory (DEF-006/7/8)`
**Fix location**: `src/autom8_asana/services/section_timeline_service.py`, cache warm-up

**Defensive pattern**: Timelines are now pre-computed during cache warming and served from memory. 3,771 offers, sub-second response.

**Agent relevance**: Any agent modifying timeline queries or cache warming. Timelines must be pre-computed, not computed on-the-fly.

---

### SCAR-011: Auth Token Wiring for Data Service

**What failed**: `--live` CLI mode sent raw service key as bearer token, but the data service expected JWT. Auth flow broke silently.

**Fix commits**: `a51b173`, `df33fb8` -- `fix(auth): wire SERVICE_API_KEY -> TokenManager JWT for data-service` and `fix(auth): replace --live raw-key-as-bearer with platform TokenManager`
**Fix location**: Auth module, query CLI

**Defensive pattern**: Always use `TokenManager` for JWT exchange. Never send raw service keys as bearer tokens.

**Agent relevance**: Any agent modifying data service auth flow or CLI `--live` mode.

---

### SCAR-012: Docker COPY Permissions

**What failed**: `COPY --link --chown` used string user:group which failed in some Docker build contexts.

**Fix commit**: `7794ac5` -- `fix(docker): use numeric UID:GID in COPY --link --chown`
**Fix location**: `Dockerfile`

**Defensive pattern**: Always use numeric UID:GID in Docker COPY directives for portability.

**Agent relevance**: Any agent modifying Dockerfile.

---

## Category Coverage

| Category | Scar Count | Examples |
|----------|-----------|----------|
| **Data Corruption/Staleness** | 3 | SCAR-001 (stale custom fields), SCAR-004 (SWR stale memory), SCAR-008 (cascade gaps) |
| **Integration Failure** | 3 | SCAR-003 (cache fragmentation), SCAR-009 (entity type mapping), SCAR-011 (auth token wiring) |
| **Test Infrastructure** | 2 | SCAR-005 (NameGid forward refs), SCAR-006 (JWKS mock targets) |
| **API Contract** | 2 | SCAR-002 (field validation), SCAR-007 (aggregation format) |
| **Performance** | 1 | SCAR-010 (timeline pre-computation) |
| **Build/Deploy** | 1 | SCAR-012 (Docker permissions) |
| **Race Conditions** | 0 | Not observed (RLock used in SaveSession per TDD-DEBT-003) |
| **Security** | 0 | Not observed directly; PII redaction contract in `clients/data/_pii.py` is defensive |

## Fix-Location Mapping

| Scar | File Path | Function/Section |
|------|-----------|-----------------|
| SCAR-001 | `src/autom8_asana/persistence/session.py:997` | `_post_commit_cleanup()` |
| SCAR-002 | `src/autom8_asana/api/routes/resolver.py:310` | Resolver route handler |
| SCAR-003 | `src/autom8_asana/api/lifespan.py:103,121` + `api/client_pool.py:201` | `lifespan()`, `ClientPool._create_client()` |
| SCAR-004 | `src/autom8_asana/dataframes/` (build_result.py) | `BuildResult.total_rows` property |
| SCAR-005 | `tests/conftest.py` | `_bootstrap_session()` |
| SCAR-006 | `tests/unit/api/routes/` (health tests) | Mock target setup |
| SCAR-007 | Metrics compute module | Aggregation output formatting |
| SCAR-008 | Cache hierarchy warming | Cascade resolution |
| SCAR-009 | `src/autom8_asana/clients/data/` | Entity type mapping |
| SCAR-010 | `src/autom8_asana/services/section_timeline_service.py` | Timeline pre-computation |
| SCAR-011 | Auth module + query CLI | Token exchange flow |
| SCAR-012 | `Dockerfile` | COPY directive |

## Defensive Pattern Documentation

| Scar | Defensive Pattern | Regression Test |
|------|------------------|-----------------|
| SCAR-001 | Clear accessor before snapshot capture | SaveSession commit cycle tests |
| SCAR-002 | `validate_fields()` guard at API boundary | Resolver route tests |
| SCAR-003 | Shared CacheProvider injection in lifespan | Client pool integration tests |
| SCAR-004 | `total_rows` from DataFrame.len(); separate `fetched_rows` | Build result tests (40 tests) |
| SCAR-005 | Session-scoped `model_rebuild()` in conftest | All tests (autouse fixture) |
| SCAR-006 | Mock at import-use point, not definition | Health endpoint tests |
| SCAR-007 | None guard on empty DataFrame | Metrics aggregation tests |
| SCAR-008 | Graceful handling of missing hierarchy entries | Cascade validation tests |
| SCAR-009 | Entity type alias mapping | DataServiceClient tests |
| SCAR-010 | Pre-computed timelines at warm-up | Section timeline tests |
| SCAR-011 | TokenManager for JWT exchange | Auth integration tests |
| SCAR-012 | Numeric UID:GID | CI Docker build |

## Agent-Relevance Tagging

| Scar | Relevant Areas | Why |
|------|----------------|-----|
| SCAR-001 | SaveSession, custom fields, persistence | Must preserve accessor-clear-before-snapshot ordering |
| SCAR-002 | Query routes, resolver endpoints | Must add field validation at API boundary for new endpoints |
| SCAR-003 | Client pool, lifespan, cache DI | Must inject shared CacheProvider; do not create per-client |
| SCAR-004 | SWR, cache warming, build results | Must use DataFrame.len() for total_rows, not section counting |
| SCAR-005 | Pydantic models, test infrastructure | Must add new models to rebuild list in conftest |
| SCAR-006 | Auth tests, JWKS mocking | Must mock at import-use point |
| SCAR-007 | Metrics, aggregation | Must guard against None on empty DataFrames |
| SCAR-008 | Cascading fields, hierarchy, cache | Must handle missing hierarchy entries gracefully |
| SCAR-009 | Entity types, DataServiceClient | Must update entity type mapping for new entity types |
| SCAR-010 | Timelines, performance | Must pre-compute, not compute on-the-fly |
| SCAR-011 | Auth, CLI, data service | Must use TokenManager for JWT, never raw keys |
| SCAR-012 | Docker, deployment | Must use numeric UID:GID |

## Knowledge Gaps

- SCAR-NNN numbered entries in the traditional format were not present in the source code; the DEF-NNN marker system is used instead. The catalog above synthesizes from DEF markers and git history.
- Some older scars from before the current git history window may not be captured.
- The exact regression test names for each scar were not individually verified (test coverage is documented at module level).
- Defensive patterns in the `automation/` and `lifecycle/` packages were not deeply audited for scar-born code.
