---
domain: scar-tissue
generated_at: "2026-03-18T11:50:56Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "d234795"
confidence: 0.82
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Scar Tissue

## Failure Catalog

This catalog documents 14 confirmed production or near-production failures, each with commit evidence and current fix location.

---

### SCAR-001: Entity Collision -- UnitHolder vs Unit GID Resolver (HOTFIX-entity-collision)

**What failed**: Both "Business Units" and "Units" Asana project names normalized to entity_type `"unit"`. Last-write-wins in the entity registry caused the resolver to map `"unit"` to UnitHolder's project GID instead of Unit's project GID. The entity resolver returned UnitHolder GIDs when callers requested Unit GIDs.

**Commit**: `edb8b6d` hotfix(entity): add PRIMARY_PROJECT_GID to UnitHolder to fix entity collision

**Fix location**: `src/autom8_asana/models/business/unit.py` line 479 -- `PRIMARY_PROJECT_GID: ClassVar[str | None] = "1204433992667196"`. Routing guard in `src/autom8_asana/services/discovery.py` line 29 documents `ADR-HOTFIX-entity-collision`.

**Defensive pattern**: Every holder class now has a distinct `PRIMARY_PROJECT_GID` class variable. Tier 1 resolution uses project membership lookup before falling back to name normalization. Documented in `UnitHolder` docstring lines 455-473.

**Regression test**: `tests/unit/core/test_project_registry.py` lines 225-270 assert `PRIMARY_PROJECT_GID` values for all entity and holder classes.

---

### SCAR-002: Orphaned IN_PROGRESS Sections Deadlock Cache Rebuild (ADR-HOTFIX-001)

**What failed**: When a process died mid-build, sections left in `IN_PROGRESS` status were never retried. `SectionFreshnessProber` permanently excluded them, disabling SWR refresh -- cache rebuild would never complete.

**Commit**: `05549b8` fix(cache): resolve manifest deadlock + force rebuild stale data

**Fix location**: `src/autom8_asana/dataframes/section_persistence.py` lines 139-158 -- `get_incomplete_section_gids()` treats `IN_PROGRESS` sections stuck longer than 5 minutes (`stale_timeout_seconds=300`) as retryable by comparing `in_progress_since` timestamp.

**Defensive pattern**: `SectionInfo` carries `in_progress_since: datetime | None`. Any `IN_PROGRESS` entry without a recent timestamp is added to the retry list.

**Regression test**: `tests/unit/dataframes/test_section_persistence_storage.py` (covers `get_incomplete_section_gids` with stuck timeout logic).

---

### SCAR-003: Force Rebuild Leaves Stale Merged Artifacts in S3 (ADR-HOTFIX-002)

**What failed**: `POST /admin/force-rebuild` deleted the S3 manifest and section parquets but left `dataframe.parquet` and `watermark.json`. On next startup, `ProgressiveTier` re-hydrated stale merged data from S3 into the memory tier, silently serving stale data even after a force rebuild.

**Commit**: `05549b8` fix(cache): resolve manifest deadlock + force rebuild stale data (same commit as SCAR-002)

**Fix location**: `src/autom8_asana/api/routes/admin.py` line 160 -- calls `persistence.storage.delete_dataframe(project_gid)` after deleting section files.

**Defensive pattern**: The comment at line 160 explicitly names `ADR-HOTFIX-002` to prevent removal of this call.

**Regression test**: `tests/unit/api/routes/test_admin_force_rebuild.py`

---

### SCAR-004: Isolated Cache Providers -- Warm-up Data Invisible to Request Handlers (DEF-005)

**What failed**: In non-Redis environments, each `AsanaClient` auto-detected its own `InMemoryCacheProvider` instance. Warm-up tasks wrote to one instance; request handlers read from a different, empty instance. Cache hits from warm-up never materialized for request handlers.

**Commit**: Not a single commit -- defensive pattern wired incrementally. Evidence in `fix(cache): wire SaveSession DataFrameCache invalidation gap (F-1)` commit `c1ad76a` and DEF-005 comments in lifespan.

**Fix location**: `src/autom8_asana/api/lifespan.py` lines 108-130 -- creates one shared `CacheProvider` at startup (`app.state.cache_provider`) and passes it to `ClientPool`. `src/autom8_asana/api/client_pool.py` line 201 injects it into pooled clients.

**Defensive pattern**: Application startup constructs a single `CacheProvider` from `AsanaConfig` and attaches to `app.state`. No client creates its own provider independently.

**Regression test**: No dedicated regression test found for the isolated-provider scenario. This is a known gap (see Knowledge Gaps).

---

### SCAR-005: Cascade Field Null Rate -- 30% of Units with Null `office_phone` (TDD-CASCADE-RESUME-FIX)

**What failed**: When `ProgressiveProjectBuilder` resumed sections from S3 parquet, tasks were not re-registered in `HierarchyIndex`. Step 5.5 cascade validator skipped all resumed tasks (empty ancestor chain). Result: ~30% null rate in `office_phone` and other cascade fields for unit tasks.

**Commit**: `9606712` fix(cascade): persist parent_gid to repair hierarchy on S3 resume

**Fix location**:
- `src/autom8_asana/dataframes/schemas/base.py` -- `parent_gid` added as 13th base column
- `src/autom8_asana/dataframes/models/task_row.py` line 39 -- `parent_gid` in base TaskRow
- `src/autom8_asana/dataframes/builders/progressive.py` lines 465, 484, 1196, 1252 -- hierarchy reconstruction and gap warming after S3 resume

**Defensive pattern**: `parent_gid` persisted to parquet so hierarchy can be reconstructed without re-fetching from Asana. Schema versions bumped to force one-time full rebuild on deploy.

**Regression test**: Referenced in `tests/unit/dataframes/` -- cascade validator post-build pass tests.

---

### SCAR-006: Cascade Hierarchy Warming Gaps -- Silent Null Fields from Transient Failures (TDD-CASCADE-FAILURE-FIXES-001)

**What failed**: Transient hierarchy warming failures caused `get_parent_chain_async` to break on missing ancestors, producing null cascade fields (e.g., `office_phone=None`). Units excluded from resolution index appeared as "Paying, No Ads" anomalies in reconcile-spend reports.

**Commit**: `6cf457e` fix(cache): harden cascade resolution against hierarchy warming gaps

**Fix location**:
- `src/autom8_asana/dataframes/views/cascade_view.py` line 356 -- gap-skipping in parent chain traversal
- `src/autom8_asana/dataframes/builders/cascade_validator.py` -- post-build cascade validation pass (Fix 3 from TDD-CASCADE-FAILURE-FIXES-001)

**Defensive pattern**: Chain traversal skips gaps rather than breaking. Grandparent fallback added for 3-level hierarchies. Post-build cascade validation detects and corrects stale fields. Documented in `docs/spikes/SPIKE-unit-resolution-cascade-failure.md`.

**Regression test**: `tests/unit/dataframes/builders/` -- cascade validator tests.

---

### SCAR-007: SWR All-Sections-Skipped Produces Zero `total_rows` -- Memory Cache Never Promoted

**What failed**: `BuildResult.total_rows` summed `row_count` from `SUCCESS` sections only. During SWR refresh when all sections were `SKIPPED` (fresh cache), `total_rows` returned 0. The factory guard `result.total_rows > 0` always failed, skipping the memory put. All 6 entity types served stale data indefinitely despite SWR firing.

**Commit**: `9fbbb29` fix(swr): fix memory cache promotion when all sections resume from S3

**Fix location**: `src/autom8_asana/dataframes/builders/build_result.py` -- `total_rows` now uses `len(dataframe)` when a merged DataFrame is available.

**Defensive pattern**: `total_rows` property checks for attached DataFrame before falling back to summing section row counts. `fetched_rows` property preserves the old API-work semantics.

**Regression test**: `tests/unit/dataframes/builders/test_build_result.py` lines 350-373 -- `test_build_result_total_rows_all_skipped_with_dataframe`.

---

### SCAR-008: DEF-001 -- Snapshot Captured Before Accessor Cleared, Persisting Stale Custom Fields

**What failed**: In `SaveSession._post_commit_cleanup`, the order was: (1) capture snapshot, (2) clear custom field accessor. When the snapshot was captured, the accessor still held stale modifications. These stale values persisted in the entity state.

**Commit**: Defensive comment added; exact fix commit not isolated -- evidence in session.py line 1005.

**Fix location**: `src/autom8_asana/persistence/session.py` lines 1005-1011 -- comment "DEF-001 FIX: Order matters - clear accessor BEFORE capturing snapshot"; `_reset_custom_field_tracking(entity)` called before `_tracker.mark_clean(entity)`. Also referenced in `src/autom8_asana/api/routes/resolver.py` line 310 for field validation.

**Defensive pattern**: Post-commit cleanup always clears tracking state before snapshotting. Order is documented in code comment.

**Regression test**: Not isolated -- covered implicitly by session healing tests.

---

### SCAR-009: `SyncInAsyncContextError` from `_auto_detect_workspace` in Async Contexts

**What failed**: `AsanaClient._auto_detect_workspace()` calls `SyncHttpClient` synchronously. When instantiated inside an async context (tests or async handlers), this raises `SyncInAsyncContextError`. Required CI to set `ASANA_WORKSPACE_GID` as a dummy env var to bypass auto-detection.

**Commits**:
- `dffb644` fix(client): guard _auto_detect_workspace against async context
- `8366df9` fix(ci): set ASANA_WORKSPACE_GID to prevent SyncHttpClient in async tests

**Fix location**: `src/autom8_asana/client.py` -- guard checks for running event loop before invoking synchronous detection.

**Defensive pattern**: CI sets `ASANA_WORKSPACE_GID` env var universally; production passes `workspace_gid` via config. Auto-detection is only attempted in pure sync contexts.

**Regression test**: Covered by async client instantiation tests; CI env var guard prevents recurrence.

---

### SCAR-010: SaveSession State Transitions Not Thread-Safe (DEBT-003, DEBT-005)

**What failed**: `SaveSession` had no lock protecting state transitions (`__aexit__`, `commit_async`). Concurrent access from multiple threads could cause lost state updates or operations executing against inconsistent state. Sprint 3 concurrency audit identified this as DEBT-003 (state atomicity) and DEBT-005 (concurrent track race).

**Commit**: `3f19a51` fix(persistence): add thread-safety to SaveSession state transitions

**Fix location**: `src/autom8_asana/persistence/session.py` -- `_lock = threading.RLock()` added; state transitions and track/untrack/delete wrapped in `_require_open()` context manager.

**Defensive pattern**: All state-mutating methods acquire `_lock` via `_state_lock()`. Lock is `RLock` to allow re-entrant acquisition within the same thread. Performance overhead documented as `<50us`.

**Regression test**: `tests/unit/persistence/test_session_concurrency.py` -- 19+ tests covering concurrent commits, rapid track/untrack, and state transitions.

---

### SCAR-011: ECS Health Check Failure -- Liveness Blocked by Cache Warmup (Health/Readiness)

**What failed**: `/health` returned 503 during cache warming. Cache warming ran in the lifespan context manager (blocking startup). Rate limiting or errors during warmup prevented the app from responding to ECS health checks, causing ECS to terminate the task before it could become healthy.

**Commit**: `bb10cc7` fix(health): decouple liveness from cache warmup for ECS health checks

**Fix location**: `src/autom8_asana/api/lifespan.py` -- cache warming moved to background task, not blocking startup. `src/autom8_asana/api/routes/health.py` -- `/health` returns 200 (liveness); `/health/ready` returns 503 during warmup (readiness).

**Defensive pattern**: Liveness/readiness separation follows Kubernetes pattern: liveness always 200 if process started; readiness gate on cache warmth.

**Regression test**: Health endpoint tests in `tests/unit/api/routes/`.

---

### SCAR-012: S2S Data-Service Auth Failure -- All Cross-Service Joins Return Zero Matches

**What failed** (two related failures):

**12a**: `DataServiceClient` DI factory created the client with no `auth_provider`. Data-service returned `MISSING_AUTH_HEADER`, causing all reconciliation and cross-service joins to return `join_matched=0`. Root cause: fallback to `AUTOM8_DATA_API_KEY` env var (unset in production).

**Commit**: `a51b173` fix(auth): wire SERVICE_API_KEY -> TokenManager JWT for data-service

**12b**: CLI `--live` mode passed `ASANA_SERVICE_KEY` directly as a Bearer token instead of exchanging it for a JWT via the auth service.

**Commit**: `df33fb8` fix(auth): replace --live raw-key-as-bearer with platform TokenManager

**Fix location**:
- `src/autom8_asana/auth/service_token.py` -- `ServiceTokenAuthProvider` wraps `autom8y_core.TokenManager`
- `src/autom8_asana/api/dependencies.py` -- DI factory creates auth provider from `SERVICE_API_KEY`
- `src/autom8_asana/clients/data/client.py` -- accepts auth provider

**Defensive pattern**: `ServiceTokenAuthProvider` implements the `AuthProvider` protocol. No client creates a raw-key Bearer header. Fallback to env var for backward compatibility is explicit and documented.

**Regression test**: Auth integration tests in `tests/unit/` -- auth provider tests.

---

### SCAR-013: Schema SDK Version Mismatch Causes ECS Exit Code 3 Crash

**What failed**: `autom8y-cache` SDK features (schema versioning) were added locally but not yet published to the package registry. Import failure at module level caused ECS container crash on startup (exit code 3).

**Commit**: `869fddc` hotfix(cache): graceful degradation when SDK lacks schema versioning

**Fix location**: `src/autom8_asana/cache/schema_providers.py` -- imports wrapped in `try/except` with `_SCHEMA_VERSIONING_AVAILABLE` flag; `register_asana_schemas()` returns early with a warning if unavailable. Also: `src/autom8_asana/cache/__init__.py` lines 142-149 -- Lambda-compatibility HOTFIX for `autom8y_cache` module mismatches (Freshness import fallback).

**Defensive pattern**: Optional SDK capabilities are guarded with `try/except ImportError`. Service starts normally; features enable when SDK is published. Lambda imports have the same defensive guard.

**Regression test**: CI dependency matrix tests. Specific import-fallback unit test not found (gap).

---

### SCAR-014: Lifecycle Config `extra="forbid"` Breaks Forward-Compatibility Contract D-LC-002

**What failed**: Adding `extra="forbid"` to all 16 Pydantic models (including 11 lifecycle config models) broke `test_yaml_config_with_extra_fields_ignored`. Design contract D-LC-002 requires that YAML configs with unknown fields not raise `ValidationError` -- lifecycle YAML files may evolve ahead of deployed code.

**Commit**: `5a24194` fix(lifecycle): revert extra="forbid" on config models to preserve D-LC-002 forward-compat contract

**Fix location**: `src/autom8_asana/lifecycle/` -- all 11 lifecycle config models (`SelfLoopConfig`, `InitActionConfig`, etc.) removed `model_config = ConfigDict(extra="forbid")`. Non-lifecycle models keep the restriction.

**Defensive pattern**: Lifecycle config models intentionally omit `extra="forbid"`. The 5 non-lifecycle models (webhook, seeder) retain it. The distinction is not enforced programmatically -- it relies on the contract being documented.

**Regression test**: `tests/integration/test_lifecycle_smoke.py` lines 1720-1751 -- `test_yaml_config_with_extra_fields_ignored` validates D-LC-002.

---

## Category Coverage

| Category | Scars | Count |
|---|---|---|
| **Cache Coherence / Stale Data** | SCAR-003, SCAR-004, SCAR-005, SCAR-006, SCAR-007 | 5 |
| **Entity Resolution / Collision** | SCAR-001 | 1 |
| **Concurrency / Race Condition** | SCAR-002, SCAR-010 | 2 |
| **Authentication / Authorization** | SCAR-012 | 1 |
| **Startup / Deployment Failure** | SCAR-009, SCAR-011, SCAR-013 | 3 |
| **Data Model / Contract Violation** | SCAR-008, SCAR-014 | 2 |

Total: 6 categories, 14 scars. All categories have at least 1 representative.

## Fix-Location Mapping

| Scar | Primary Fix File(s) | Function/Area |
|---|---|---|
| SCAR-001 | `src/autom8_asana/models/business/unit.py:479` | `UnitHolder.PRIMARY_PROJECT_GID` class var |
| SCAR-001 | `src/autom8_asana/services/discovery.py:29` | `ADR-HOTFIX-entity-collision` routing guard |
| SCAR-002 | `src/autom8_asana/dataframes/section_persistence.py:132-158` | `get_incomplete_section_gids()` |
| SCAR-003 | `src/autom8_asana/api/routes/admin.py:160-163` | `_perform_force_rebuild()` |
| SCAR-004 | `src/autom8_asana/api/lifespan.py:108-130` | `lifespan()` startup |
| SCAR-004 | `src/autom8_asana/api/client_pool.py:201` | `ClientPool.__init__` |
| SCAR-005 | `src/autom8_asana/dataframes/builders/progressive.py:465,484,1196,1252` | `_resume_sections_async`, `_warm_hierarchy_gaps_async` |
| SCAR-005 | `src/autom8_asana/dataframes/schemas/base.py` | BASE_SCHEMA (13th column) |
| SCAR-006 | `src/autom8_asana/dataframes/views/cascade_view.py:356` | parent chain traversal |
| SCAR-006 | `src/autom8_asana/dataframes/builders/cascade_validator.py` | post-build validation pass |
| SCAR-007 | `src/autom8_asana/dataframes/builders/build_result.py` | `BuildResult.total_rows` property |
| SCAR-008 | `src/autom8_asana/persistence/session.py:1005-1011` | `_post_commit_cleanup()` |
| SCAR-009 | `src/autom8_asana/client.py` | `_auto_detect_workspace()` guard |
| SCAR-010 | `src/autom8_asana/persistence/session.py` | `_lock`, `_state_lock()`, `_require_open()` |
| SCAR-011 | `src/autom8_asana/api/lifespan.py`, `src/autom8_asana/api/routes/health.py` | background warmup, `/health` vs `/health/ready` |
| SCAR-012 | `src/autom8_asana/auth/service_token.py`, `src/autom8_asana/api/dependencies.py` | `ServiceTokenAuthProvider`, DI factory |
| SCAR-013 | `src/autom8_asana/cache/schema_providers.py`, `src/autom8_asana/cache/__init__.py:142-149` | optional import guard |
| SCAR-014 | `src/autom8_asana/lifecycle/config.py` | all 11 lifecycle config models |

## Defensive Pattern Documentation

| Pattern | Where | Scar(s) |
|---|---|---|
| `PRIMARY_PROJECT_GID` per entity class; Tier 1 project-membership resolution | `models/business/*.py`, `services/discovery.py` | SCAR-001 |
| `in_progress_since` timestamp + 5-minute stale timeout on `IN_PROGRESS` sections | `dataframes/section_persistence.py` | SCAR-002 |
| Full artifact purge on force-rebuild (`delete_dataframe` + `delete_section_files` + `delete_manifest`) | `api/routes/admin.py` | SCAR-003 |
| Single shared `CacheProvider` at `app.state`; no per-client auto-detection | `api/lifespan.py`, `api/client_pool.py` | SCAR-004 |
| `parent_gid` column in BASE_SCHEMA; hierarchy reconstruction from parquet on S3 resume | `dataframes/schemas/base.py`, `dataframes/builders/progressive.py` | SCAR-005 |
| Gap-skipping chain traversal; grandparent fallback; post-build cascade validator | `dataframes/views/cascade_view.py`, `dataframes/builders/cascade_validator.py` | SCAR-006 |
| `total_rows` uses `len(dataframe)` when DataFrame available, falls back to section sum | `dataframes/builders/build_result.py` | SCAR-007 |
| Clear tracking state BEFORE snapshot in post-commit cleanup (DEF-001) | `persistence/session.py` | SCAR-008 |
| `ASANA_WORKSPACE_GID` env var bypasses sync workspace auto-detection | `client.py`, CI env | SCAR-009 |
| `threading.RLock` protecting all session state transitions | `persistence/session.py` | SCAR-010 |
| Liveness (`/health`) always 200; readiness (`/health/ready`) gates on cache warmth | `api/routes/health.py` | SCAR-011 |
| `ServiceTokenAuthProvider` wraps `TokenManager`; no raw-key Bearer | `auth/service_token.py` | SCAR-012 |
| `try/except ImportError` with `_SCHEMA_VERSIONING_AVAILABLE` flag for optional SDK features | `cache/schema_providers.py`, `cache/__init__.py` | SCAR-013 |
| Lifecycle config models omit `extra="forbid"`; non-lifecycle models retain it | `lifecycle/config.py` | SCAR-014 |

## Agent-Relevance Tagging

| Scar | Relevant Roles | Why |
|---|---|---|
| SCAR-001 | principal-engineer, architect | Any new entity/holder class must follow `PRIMARY_PROJECT_GID` pattern or risk collision |
| SCAR-002 | principal-engineer, platform-engineer | Section persistence changes must preserve `in_progress_since` stamping |
| SCAR-003 | principal-engineer, platform-engineer | Cache purge operations must include merged artifacts, not just manifests |
| SCAR-004 | principal-engineer, architect | New service entry points must receive `app.state.cache_provider`, not auto-create |
| SCAR-005 | principal-engineer | Any new DataFrame column needed for cascade must be added to BASE_SCHEMA and persisted to parquet |
| SCAR-006 | principal-engineer | Cascade chain traversal must skip gaps, never break; hierarchy always treated as potentially incomplete |
| SCAR-007 | principal-engineer | `BuildResult` metrics must account for SKIPPED sections; don't derive work count from section sum alone |
| SCAR-008 | principal-engineer | In `SaveSession` cleanup, reset state before snapshotting -- order is safety-critical |
| SCAR-009 | principal-engineer, qa-adversary | Tests and async contexts must set `ASANA_WORKSPACE_GID` or mock workspace; never rely on sync auto-detect |
| SCAR-010 | principal-engineer | `SaveSession` is used concurrently; all state access goes through lock -- don't add unlocked state |
| SCAR-011 | platform-engineer, architect | ECS/ALB health checks must target `/health` (liveness), not `/health/ready` (readiness) |
| SCAR-012 | principal-engineer, platform-engineer | New cross-service clients must use `ServiceTokenAuthProvider`; never pass raw API keys as Bearer tokens |
| SCAR-013 | principal-engineer, platform-engineer | Optional SDK imports must be guarded; platform features not yet published crash ECS |
| SCAR-014 | principal-engineer, architect | Lifecycle config models must remain forward-compatible (no `extra="forbid"`); document on any new lifecycle model |

## Knowledge Gaps

1. **DEF-005 isolated-cache regression test**: No dedicated test confirms that warm-up data is visible to request handlers when `InMemoryCacheProvider` is auto-detected. Coverage relies on integration behavior.
2. **SCAR-013 import-fallback unit test**: No unit test exercises the `_SCHEMA_VERSIONING_AVAILABLE = False` path in `cache/schema_providers.py`. Graceful degradation is only tested implicitly by CI dependency installs.
3. **SCAR-008 DEF-001 regression test**: No isolated regression test for the snapshot-ordering bug. Coverage is implicit through session lifecycle tests.
4. **git history depth**: `git log` reviewed through 292 scar-relevant commits. Commits older than the current log window (project genesis) are not cataloged.
5. **SM-002, SM-007, SM-008** (referenced in `cache/backends/base.py`) are refactoring scars (boundary violation, freshness stamp duplication, init boilerplate duplication) -- cataloged as code-quality scars but not expanded here as they did not cause production failures.
