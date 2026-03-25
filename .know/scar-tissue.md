---
domain: scar-tissue
generated_at: "2026-03-25T01:56:07Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "c6bcef6"
confidence: 0.87
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Scar Tissue

## Failure Catalog

This catalog documents 16 confirmed production or near-production failures plus 4 deployment/CI scars, each with commit evidence and current fix location. Scars SCAR-001 through SCAR-014 were cataloged in the prior generation (2026-03-18). SCAR-015 through SCAR-022 and the DEF-006/7/8 cluster represent incremental additions observed post-generation or identified as gaps in the prior catalog.

---

### SCAR-001: Entity Collision -- UnitHolder vs Unit GID Resolver

**What failed**: Both "Business Units" and "Units" Asana project names normalized to entity_type `"unit"`. Last-write-wins in the entity registry caused the resolver to map `"unit"` to UnitHolder's project GID instead of Unit's project GID.

**Commit**: `edb8b6d` hotfix(entity): add PRIMARY_PROJECT_GID to UnitHolder to fix entity collision

**Fix location**: `src/autom8_asana/models/business/unit.py` line 479 (`PRIMARY_PROJECT_GID: ClassVar[str | None]`). Routing guard at `src/autom8_asana/services/discovery.py` line 29 (`ADR-HOTFIX-entity-collision`).

**Defensive pattern**: Every holder class carries a distinct `PRIMARY_PROJECT_GID`. Tier 1 resolution uses project membership before name normalization.

**Regression test**: `tests/unit/core/test_project_registry.py` lines 225-270 assert `PRIMARY_PROJECT_GID` values for all entity and holder classes.

---

### SCAR-002: Orphaned IN_PROGRESS Sections Deadlock Cache Rebuild

**What failed**: Sections stuck in `IN_PROGRESS` after process crash were never retried. `SectionFreshnessProber` permanently excluded them, preventing SWR refresh from completing.

**Commit**: `05549b8` fix(cache): resolve manifest deadlock + force rebuild stale data

**Fix location**: `src/autom8_asana/dataframes/section_persistence.py` lines 139-158 -- `get_incomplete_section_gids()` treats `IN_PROGRESS` sections with `in_progress_since` older than 5 minutes as retryable.

**Defensive pattern**: `SectionInfo` carries `in_progress_since: datetime | None`; any stale `IN_PROGRESS` entry enters the retry list.

**Regression test**: `tests/unit/dataframes/test_section_persistence_storage.py` (covers stuck timeout logic).

---

### SCAR-003: Force Rebuild Leaves Stale Merged Artifacts in S3

**What failed**: `POST /admin/force-rebuild` deleted manifest + section parquets but left `dataframe.parquet` and `watermark.json`. On next startup, stale merged data was re-hydrated, silently serving stale data post-rebuild.

**Commit**: `05549b8` fix(cache): resolve manifest deadlock + force rebuild stale data (same commit as SCAR-002)

**Fix location**: `src/autom8_asana/api/routes/admin.py` line 160 -- calls `delete_dataframe()` after deleting section files. Comment names `ADR-HOTFIX-002` to prevent removal.

**Defensive pattern**: Full artifact purge on force-rebuild: `delete_dataframe` + `delete_section_files` + `delete_manifest`.

**Regression test**: `tests/unit/api/routes/test_admin_force_rebuild.py`

---

### SCAR-004: Isolated Cache Providers -- Warm-up Data Invisible to Request Handlers (DEF-005)

**What failed**: Each `AsanaClient` auto-detected its own `InMemoryCacheProvider`. Warm-up wrote to one instance; request handlers read from a different empty instance. Cache hits never materialized at request time.

**Commit**: Incremental -- evidence in commit `c1ad76a` `fix(cache): wire SaveSession DataFrameCache invalidation gap (F-1)` and commit `557a44c` `fix(lifespan): pass shared cache provider to warm_client and ClientPool (DEF-005)`.

**Fix location**: `src/autom8_asana/api/lifespan.py` lines 108-130 (DEF-005 marker, single shared `CacheProvider` at `app.state`). `src/autom8_asana/api/client_pool.py` line 201 (DEF-005 marker, injects shared provider into pooled clients).

**Defensive pattern**: Application startup constructs one `CacheProvider` from `AsanaConfig`, attaches to `app.state`. No client auto-creates its own provider.

**Regression test**: No dedicated isolated-provider regression test (known gap).

---

### SCAR-005: Cascade Field Null Rate -- 30% of Units with Null `office_phone`

**What failed**: When `ProgressiveProjectBuilder` resumed sections from S3 parquet, tasks were not re-registered in `HierarchyIndex`. Step 5.5 cascade validator skipped all resumed tasks (empty ancestor chain). ~30% null rate in cascade fields.

**Commit**: `9606712` fix(cascade): persist parent_gid to repair hierarchy on S3 resume

**Fix location**:
- `src/autom8_asana/dataframes/schemas/base.py` -- `parent_gid` added as 13th base column
- `src/autom8_asana/dataframes/builders/progressive.py` lines 465, 484, 1196, 1252 -- hierarchy reconstruction after S3 resume

**Defensive pattern**: `parent_gid` persisted to parquet so hierarchy can be reconstructed without re-fetching. Post-build cascade null rate audit added (logged via structured logging; comment references SCAR-005/006). Thresholds: WARN at 5%, ERROR at 20% (calibrated against the 30% production incident).

**Regression test**: `tests/unit/dataframes/builders/test_cascade_validator.py` line 664 documents "30 nulls out of 100 = 30% (SCAR-005 scenario)".

---

### SCAR-006: Cascade Hierarchy Warming Gaps -- Silent Null Fields from Transient Failures

**What failed**: Transient hierarchy warming failures caused `get_parent_chain_async` to break on missing ancestors, producing null cascade fields. Units excluded from resolution index appeared as "Paying, No Ads" anomalies in reconcile-spend reports.

**Commit**: `6cf457e` fix(cache): harden cascade resolution against hierarchy warming gaps

**Fix location**:
- `src/autom8_asana/dataframes/views/cascade_view.py` line 356 -- gap-skipping in parent chain traversal
- `src/autom8_asana/dataframes/builders/cascade_validator.py` -- post-build cascade validation pass
- `src/autom8_asana/core/entity_registry.py` line 304 -- comment: "Violating this invariant would cause cascade fields to be null at extraction time, reproducing SCAR-005/006 conditions."

**Defensive pattern**: Chain traversal skips gaps rather than breaking. Grandparent fallback for 3-level hierarchies. Null section maps to `None` (UNKNOWN) per SCAR-005/006 -- universal_strategy.py lines 454, 500, 511.

**Regression test**: `tests/unit/services/test_universal_strategy_status.py` lines 183, 276 explicitly reference SCAR-005/006.

---

### SCAR-007: SWR All-Sections-Skipped Produces Zero `total_rows` -- Memory Cache Never Promoted

**What failed**: `BuildResult.total_rows` summed `row_count` from `SUCCESS` sections only. When all sections were `SKIPPED` during SWR, `total_rows` returned 0. Factory guard `result.total_rows > 0` always failed, silently skipping memory cache promotion -- all 6 entity types served stale data indefinitely.

**Commit**: `9fbbb29` fix(swr): fix memory cache promotion when all sections resume from S3

**Fix location**: `src/autom8_asana/dataframes/builders/build_result.py` -- `total_rows` now uses `len(dataframe)` when a merged DataFrame is available. `fetched_rows` preserves the old API-work semantics.

**Defensive pattern**: `total_rows` property checks for attached DataFrame before falling back to section count sum.

**Regression test**: `tests/unit/dataframes/builders/test_build_result.py` lines 350-373 -- `test_build_result_total_rows_all_skipped_with_dataframe`.

---

### SCAR-008: Snapshot Captured Before Accessor Cleared, Persisting Stale Custom Fields (DEF-001)

**What failed**: In `SaveSession._post_commit_cleanup`, snapshot was captured before custom field accessor was cleared. Stale modifications persisted in the entity state.

**Commit**: Not isolated -- defensive comment added. Evidence in `src/autom8_asana/persistence/session.py` line 1005.

**Fix location**: `src/autom8_asana/persistence/session.py` lines 1005-1011 -- comment "DEF-001 FIX: Order matters - clear accessor BEFORE capturing snapshot". Also enforced at `src/autom8_asana/api/routes/resolver.py` line 316 (field validation via DEF-001 marker).

**Defensive pattern**: Post-commit cleanup always clears tracking state before snapshotting. Order documented in code comment.

**Regression test**: No isolated regression test (known gap). Covered implicitly by session lifecycle tests.

---

### SCAR-009: `SyncInAsyncContextError` from `_auto_detect_workspace` in Async Contexts

**What failed**: `AsanaClient._auto_detect_workspace()` calls `SyncHttpClient` synchronously. When instantiated in async context (tests or async handlers), raises `SyncInAsyncContextError`.

**Commits**:
- `dffb644` fix(client): guard _auto_detect_workspace against async context
- `8366df9` fix(ci): set ASANA_WORKSPACE_GID to prevent SyncHttpClient in async tests

**Fix location**: `src/autom8_asana/client.py` -- guard checks for running event loop before invoking synchronous detection.

**Defensive pattern**: CI sets `ASANA_WORKSPACE_GID` env var universally. Production passes `workspace_gid` via config. Auto-detection only attempted in pure sync contexts.

**Regression test**: Async client instantiation tests; CI env var guard prevents recurrence.

---

### SCAR-010: SaveSession State Transitions Not Thread-Safe (DEBT-003, DEBT-005)

**What failed**: `SaveSession` had no lock protecting state transitions. Concurrent access could cause lost state updates or operations against inconsistent state.

**Commit**: `3f19a51` fix(persistence): add thread-safety to SaveSession state transitions

**Fix location**: `src/autom8_asana/persistence/session.py` -- `_lock = threading.RLock()` added; all state transitions wrapped in `_require_open()`. `RLock` used for re-entrant acquisition. Performance overhead documented as `<50us`.

**Defensive pattern**: All state-mutating methods acquire `_lock` via `_state_lock()`.

**Regression test**: `tests/unit/persistence/test_session_concurrency.py` -- 19+ tests covering concurrent commits, rapid track/untrack, state transitions.

---

### SCAR-011: ECS Health Check Failure -- Liveness Blocked by Cache Warmup

**What failed**: `/health` returned 503 during cache warming. ECS health checks failed, causing ECS to terminate the task before it became healthy.

**Commit**: `bb10cc7` fix(health): decouple liveness from cache warmup for ECS health checks

**Fix location**: `src/autom8_asana/api/lifespan.py` -- cache warming moved to background task. `src/autom8_asana/api/routes/health.py` -- `/health` returns 200 always (liveness); `/health/ready` returns 503 during warmup (readiness).

**Defensive pattern**: Liveness/readiness separation: liveness always 200 if process started; readiness gates on cache warmth.

**Regression test**: Health endpoint tests in `tests/unit/api/routes/`.

---

### SCAR-012: S2S Data-Service Auth Failure -- All Cross-Service Joins Return Zero Matches

**What failed**:
- **12a**: `DataServiceClient` DI factory created the client with no `auth_provider`. Data-service returned `MISSING_AUTH_HEADER`. Fallback to `AUTOM8_DATA_API_KEY` env var was unset in production.
- **12b**: CLI `--live` mode passed `ASANA_SERVICE_KEY` directly as a raw Bearer token instead of exchanging it for a JWT via the auth service.

**Commits**:
- `a51b173` fix(auth): wire SERVICE_API_KEY -> TokenManager JWT for data-service
- `df33fb8` fix(auth): replace --live raw-key-as-bearer with platform TokenManager

**Fix location**:
- `src/autom8_asana/auth/service_token.py` -- `ServiceTokenAuthProvider` wraps `autom8y_core.TokenManager`
- `src/autom8_asana/api/dependencies.py` -- DI factory creates auth provider from `SERVICE_API_KEY`

**Defensive pattern**: `ServiceTokenAuthProvider` implements `AuthProvider` protocol. No client creates raw-key Bearer headers. Fallback to env var is explicit and documented.

**Regression test**: Auth integration tests in `tests/unit/`.

---

### SCAR-013: Schema SDK Version Mismatch Causes ECS Exit Code 3 Crash

**What failed**: `autom8y-cache` SDK schema versioning features added locally but not yet published to registry. Import failure at module level caused ECS container crash on startup (exit code 3).

**Commit**: `869fddc` hotfix(cache): graceful degradation when SDK lacks schema versioning

**Fix location**: `src/autom8_asana/cache/integration/schema_providers.py` -- imports wrapped in `try/except ImportError` with `_SCHEMA_VERSIONING_AVAILABLE` flag at line 33; guard at line 41; `register_asana_schemas()` returns early with warning if unavailable (line 107). Also: `src/autom8_asana/cache/__init__.py` lines 142-149 -- Lambda-compatibility HOTFIX for `autom8y_cache` module mismatches.

**Defensive pattern**: Optional SDK capabilities guarded with `try/except ImportError`. Service starts normally; features enable when SDK is published.

**Regression test**: CI dependency matrix tests. Specific import-fallback unit test not found (known gap).

---

### SCAR-014: Lifecycle Config `extra="forbid"` Breaks Forward-Compatibility Contract D-LC-002

**What failed**: Adding `extra="forbid"` to 11 lifecycle Pydantic models broke `test_yaml_config_with_extra_fields_ignored`. Contract D-LC-002 requires that YAML configs with unknown fields not raise `ValidationError`.

**Commit**: `5a24194` fix(lifecycle): revert extra="forbid" on config models to preserve D-LC-002 forward-compat contract

**Fix location**: `src/autom8_asana/lifecycle/config.py` -- all 11 lifecycle config models omit `model_config = ConfigDict(extra="forbid")`. 5 non-lifecycle models retain it.

**Defensive pattern**: Lifecycle config models intentionally use `extra="ignore"`. Distinction not enforced programmatically -- relies on D-LC-002 being documented. Surfaced in `.know/design-constraints.md` line 133.

**Regression test**: `tests/integration/test_lifecycle_smoke.py` lines 1720-1751 -- `test_yaml_config_with_extra_fields_ignored`.

---

### SCAR-015: Timeline Request Handler 504 Gateway Timeout (DEF-006/7/8)

**What failed**: Section timeline endpoint performed per-request I/O -- fetching stories from Asana API at request time. ALB 60-second timeout exceeded for ~3,800 offers. Production 504 Gateway Timeout on all timeline requests.

**Commits**:
- `a347db6` fix(timeline): parallelize per-request offer processing to prevent 504 Gateway Timeout (partial fix)
- `8b5813e` fix(timeline): pre-compute timelines at warm-up, serve from memory (DEF-006/7/8) (architectural fix)

**Fix location**: `src/autom8_asana/api/lifespan.py` -- DEF-006 fix: `build_all_timelines()` runs after story warm-up, builds `SectionTimeline` objects, stores on `app.state.offer_timelines`. DEF-008 fix: `warm_story_caches()` tracks progress incrementally per-offer, enabling 50% readiness gate (AC-7.4) mid-warm-up. `src/autom8_asana/services/section_timeline_service.py` -- `build_all_timelines()`, `warm_story_caches()`.

**Defensive pattern**: All I/O moved to warm-up time. Request handlers do pure-CPU day counting from pre-computed `app.state.offer_timelines` -- no API calls, no I/O, `<100ms` for ~3,800 offers. DEF-007: pre-computation eliminates timeout risk entirely.

**Regression test**: Timeline endpoint tests (specific file not verified).

---

### SCAR-016: Conversation Audit DEF-001 -- `date_range_days` Accepted but Not Forwarded

**What failed**: `ConversationAuditWorkflow` accepted `date_range_days` from YAML params but did not forward it to `get_export_csv_async`. All conversation audits silently used the hardcoded default date range.

**Commit**: `a9cae0f` feat(automation): conversation audit workflow + scheduler dispatch + QA hotfixes (DEF-001 through DEF-005 hotfixes included)

**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit.py` -- `date_range_days` consumed from params and forwarded to `get_export_csv_async`.

**Defensive pattern**: `date_range_days` is now explicitly passed; test verifies start_date/end_date forwarding.

**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py` lines 642-643 -- "Per DEF-001 regression: date_range_days was accepted in YAML but not passed to get_export_csv_async."

---

### SCAR-017: Conversation Audit DEF-002 -- `csv_row_count` Missing from Dry-Run Metadata

**What failed**: `metadata['csv_row_count']` was absent in dry-run results, causing KeyError in callers that assumed it was always present.

**Commit**: `a9cae0f` (same QA hotfix batch)

**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit.py` -- dry-run path now sets `csv_row_count` in metadata.

**Defensive pattern**: Metadata contract is uniform across live and dry-run paths.

**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py` line 1362 -- `test_dry_run_metadata_csv_row_count`.

---

### SCAR-018: Polling Scheduler Zero Test Coverage for Schedule-Driven Dispatch (DEF-003)

**What failed**: `_evaluate_rules` dispatch path had zero test coverage. Rule evaluation bugs would be undetected.

**Commit**: `a9cae0f` (same QA hotfix batch -- "Scheduler dispatch + ScheduleConfig validator test coverage")

**Fix location**: `tests/unit/automation/polling/test_polling_scheduler.py` -- new tests added at lines 838, 927, 1035.

**Defensive pattern**: Three test classes cover schedule-driven dispatch. Marked with "Per DEF-003" docstrings.

**Regression test**: `tests/unit/automation/polling/test_polling_scheduler.py` lines 838, 927, 1035.

---

### SCAR-019: PollingScheduler ScheduleConfig Validator Zero Test Coverage (DEF-005)

**What failed**: `ScheduleConfig` validators had zero test coverage. Invalid configs would pass validation silently.

**Commit**: `a9cae0f` (same QA hotfix batch)

**Fix location**: `tests/unit/automation/polling/test_config_schema.py` -- `ScheduleConfig` validator tests added at lines 492, 566.

**Defensive pattern**: Tests validate schedule vs conditions mutual requirements.

**Regression test**: `tests/unit/automation/polling/test_config_schema.py` lines 492, 566.

---

### SCAR-020: Resolver Phone Trailing Newline Not Stripped (DEF-002)

**What failed**: Phone values with trailing newlines passed through the resolver without normalization. Downstream validation and display exhibited inconsistent behavior.

**Commit**: Included in resolver QA fixes. Evidence in test at line 565.

**Fix location**: `src/autom8_asana/api/routes/resolver.py` -- phone normalization in validation pipeline.

**Defensive pattern**: Phone normalization strips trailing whitespace before validation.

**Regression test**: `tests/unit/api/test_routes_resolver.py` line 565 -- "Phone with trailing newline is stripped and validated (DEF-002)."

---

### SCAR-021: STANDARD_ERROR_RESPONSES Type Too Narrow -- mypy Strict Rejects `dict[int, ...]`

**What failed**: `STANDARD_ERROR_RESPONSES: dict[int, dict[str, Any]]` was rejected by mypy strict when passed to FastAPI's `responses=` parameter, which expects `dict[int | str, dict[str, Any]] | None`. 39 mypy errors across 7 route files in CI.

**Commit**: `58896d1` fix(ci): resolve mypy type error and resolver mock signature mismatch (Round 10 pipeline fix)

**Fix location**: `src/autom8_asana/api/error_responses.py` -- annotation changed to `dict[int | str, dict[str, Any]]`.

**Defensive pattern**: FastAPI `responses=` parameter requires the broader union type. Not a runtime bug -- pure type contract.

**Regression test**: mypy strict CI gate.

---

### SCAR-022: uv `--frozen` + `--no-sources` Mutually Exclusive (DEF-009)

**What failed**: `uv >=0.15.4` made `--frozen` and `--no-sources` flags mutually exclusive. The `Dockerfile` used both. Docker build failed in CI (Stage 3, Round 11 of Satellite Receiver pipeline).

**Commit**: `3e0790b` fix(ci): replace --frozen with --no-sources in uv sync (DEF-009/SCAR-022)

**Fix location**: `Dockerfile` -- `uv sync --frozen --no-dev --no-sources` replaced with `uv sync --no-sources --no-dev`. Comment at line documenting "DEF-009/SCAR-022: --no-sources ensures registry resolution instead of monorepo path deps."

**Defensive pattern**: `--no-sources` is required to resolve SDKs from CodeArtifact registry rather than local monorepo editable path deps. `--frozen` omitted as mutually exclusive. Dockerfile comment documents the constraint permanently.

**Regression test**: CI Docker build step (Stage 3, Satellite Receiver).

---

## Category Coverage

| Category | Scars | Count |
|---|---|---|
| **Cache Coherence / Stale Data** | SCAR-003, SCAR-004, SCAR-005, SCAR-006, SCAR-007 | 5 |
| **Entity Resolution / Collision** | SCAR-001 | 1 |
| **Concurrency / Race Condition** | SCAR-002, SCAR-010 | 2 |
| **Authentication / Authorization** | SCAR-012 | 1 |
| **Startup / Deployment Failure** | SCAR-009, SCAR-011, SCAR-013, SCAR-022 | 4 |
| **Data Model / Contract Violation** | SCAR-008, SCAR-014 | 2 |
| **Performance Cliff / Timeout** | SCAR-015 | 1 |
| **Integration Failure / CI** | SCAR-021, SCAR-022 | 2 |
| **Workflow Logic Gap** | SCAR-016, SCAR-017, SCAR-018, SCAR-019, SCAR-020 | 5 |

Total: 9 categories, 22 scars. All categories have at least 1 representative. SCAR-022 spans both "Startup / Deployment Failure" and "Integration Failure / CI" -- counted once in each.

**Categories searched but not found**: Security (injection/XSS/CSRF), schema evolution (migration failure), data corruption (persisted incorrect values -- closest is SCAR-005 which was null not corrupt).

---

## Fix-Location Mapping

| Scar | Primary Fix File(s) | Function/Area |
|---|---|---|
| SCAR-001 | `src/autom8_asana/models/business/unit.py:479` | `UnitHolder.PRIMARY_PROJECT_GID` class var |
| SCAR-001 | `src/autom8_asana/services/discovery.py:29` | `ADR-HOTFIX-entity-collision` routing guard |
| SCAR-002 | `src/autom8_asana/dataframes/section_persistence.py:139-158` | `get_incomplete_section_gids()` |
| SCAR-003 | `src/autom8_asana/api/routes/admin.py:160` | `_perform_force_rebuild()` |
| SCAR-004 | `src/autom8_asana/api/lifespan.py:108-130` | `lifespan()` startup |
| SCAR-004 | `src/autom8_asana/api/client_pool.py:201` | `ClientPool.__init__` |
| SCAR-005 | `src/autom8_asana/dataframes/builders/progressive.py:465,484,1196,1252` | `_resume_sections_async`, `_warm_hierarchy_gaps_async` |
| SCAR-005 | `src/autom8_asana/dataframes/schemas/base.py` | BASE_SCHEMA (13th column: `parent_gid`) |
| SCAR-006 | `src/autom8_asana/dataframes/views/cascade_view.py:356` | parent chain traversal |
| SCAR-006 | `src/autom8_asana/dataframes/builders/cascade_validator.py` | post-build cascade validation pass |
| SCAR-007 | `src/autom8_asana/dataframes/builders/build_result.py` | `BuildResult.total_rows` property |
| SCAR-008 | `src/autom8_asana/persistence/session.py:1005-1011` | `_post_commit_cleanup()` |
| SCAR-009 | `src/autom8_asana/client.py` | `_auto_detect_workspace()` guard |
| SCAR-010 | `src/autom8_asana/persistence/session.py` | `_lock`, `_state_lock()`, `_require_open()` |
| SCAR-011 | `src/autom8_asana/api/lifespan.py` | background warmup |
| SCAR-011 | `src/autom8_asana/api/routes/health.py` | `/health` vs `/health/ready` |
| SCAR-012 | `src/autom8_asana/auth/service_token.py` | `ServiceTokenAuthProvider` |
| SCAR-012 | `src/autom8_asana/api/dependencies.py` | DI factory |
| SCAR-013 | `src/autom8_asana/cache/integration/schema_providers.py` | optional import guard (`_SCHEMA_VERSIONING_AVAILABLE`) |
| SCAR-013 | `src/autom8_asana/cache/__init__.py:142-149` | Lambda-compat Freshness import fallback |
| SCAR-014 | `src/autom8_asana/lifecycle/config.py` | all 11 lifecycle config models |
| SCAR-015 | `src/autom8_asana/api/lifespan.py` | `build_all_timelines()` call post-story-warm-up |
| SCAR-015 | `src/autom8_asana/services/section_timeline_service.py` | `build_all_timelines()`, `warm_story_caches()` |
| SCAR-016 | `src/autom8_asana/automation/workflows/conversation_audit.py` | date_range_days forwarding |
| SCAR-017 | `src/autom8_asana/automation/workflows/conversation_audit.py` | dry-run metadata contract |
| SCAR-018 | `tests/unit/automation/polling/test_polling_scheduler.py:838,927,1035` | dispatch tests added |
| SCAR-019 | `tests/unit/automation/polling/test_config_schema.py:492,566` | ScheduleConfig validator tests |
| SCAR-020 | `src/autom8_asana/api/routes/resolver.py` | phone normalization |
| SCAR-021 | `src/autom8_asana/api/error_responses.py` | `STANDARD_ERROR_RESPONSES` annotation |
| SCAR-022 | `Dockerfile` | uv sync flags |

---

## Defensive Pattern Documentation

| Pattern | Where | Scar(s) |
|---|---|---|
| `PRIMARY_PROJECT_GID` per entity class; Tier 1 project-membership resolution | `models/business/*.py`, `services/discovery.py` | SCAR-001 |
| `in_progress_since` timestamp + 5-minute stale timeout on `IN_PROGRESS` sections | `dataframes/section_persistence.py` | SCAR-002 |
| Full artifact purge on force-rebuild (`delete_dataframe` + `delete_section_files` + `delete_manifest`) | `api/routes/admin.py` | SCAR-003 |
| Single shared `CacheProvider` at `app.state`; no per-client auto-detection | `api/lifespan.py`, `api/client_pool.py` | SCAR-004 |
| `parent_gid` column in BASE_SCHEMA; hierarchy reconstruction from parquet on S3 resume | `dataframes/schemas/base.py`, `dataframes/builders/progressive.py` | SCAR-005 |
| Cascade null rate thresholds (WARN 5%, ERROR 20%); post-build audit pass | `dataframes/builders/cascade_validator.py`, `dataframes/builders/progressive.py` | SCAR-005/006 |
| Gap-skipping chain traversal; grandparent fallback; null section -> UNKNOWN | `dataframes/views/cascade_view.py`, `services/universal_strategy.py` | SCAR-006 |
| `total_rows` uses `len(dataframe)` when DataFrame available, falls back to section sum | `dataframes/builders/build_result.py` | SCAR-007 |
| Clear tracking state BEFORE snapshot in post-commit cleanup (DEF-001) | `persistence/session.py:1005-1011` | SCAR-008 |
| `ASANA_WORKSPACE_GID` env var bypasses sync workspace auto-detection | `client.py`, CI env | SCAR-009 |
| `threading.RLock` protecting all session state transitions | `persistence/session.py` | SCAR-010 |
| Liveness (`/health`) always 200; readiness (`/health/ready`) gates on cache warmth | `api/routes/health.py` | SCAR-011 |
| `ServiceTokenAuthProvider` wraps `TokenManager`; no raw-key Bearer | `auth/service_token.py` | SCAR-012 |
| `try/except ImportError` with `_SCHEMA_VERSIONING_AVAILABLE` flag for optional SDK features | `cache/integration/schema_providers.py`, `cache/__init__.py` | SCAR-013 |
| Lifecycle config models omit `extra="forbid"`; non-lifecycle models retain it | `lifecycle/config.py` | SCAR-014 |
| All timeline I/O pre-computed at warm-up time; `app.state.offer_timelines` served at request time | `api/lifespan.py`, `services/section_timeline_service.py` | SCAR-015 |
| `date_range_days` explicitly forwarded from params to `get_export_csv_async` | `automation/workflows/conversation_audit.py` | SCAR-016 |
| `metadata['csv_row_count']` populated on both live and dry-run paths | `automation/workflows/conversation_audit.py` | SCAR-017 |
| `STANDARD_ERROR_RESPONSES` typed as `dict[int | str, ...]` for FastAPI compatibility | `api/error_responses.py` | SCAR-021 |
| `--no-sources` without `--frozen` in `uv sync`; Dockerfile comment documents constraint | `Dockerfile` | SCAR-022 |

---

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
| SCAR-015 | architect, platform-engineer | Timeline or I/O-heavy data served at request time must be pre-computed at warm-up; ALB 60s timeout is not negotiable |
| SCAR-016 | principal-engineer | Workflow params must be explicitly threaded through to all call sites -- implicit defaults silently mask configuration |
| SCAR-017 | principal-engineer, qa-adversary | Metadata contracts must be uniform between live and dry-run paths; callers must not KeyError on dry-run |
| SCAR-018 | principal-engineer, qa-adversary | Scheduler dispatch paths require explicit test coverage -- they are invisible to unit tests that only mock the trigger |
| SCAR-019 | principal-engineer | ScheduleConfig and similar config models need validator tests; invalid configs would otherwise fail silently at runtime |
| SCAR-020 | principal-engineer | API input normalization (strip/trim) must happen before validation; user-supplied data contains whitespace/newlines |
| SCAR-021 | principal-engineer, platform-engineer | When introducing global error response catalogs, verify type compatibility with framework-expected signatures |
| SCAR-022 | platform-engineer, release-executor | uv `--no-sources` is required for registry-resolved builds; `--frozen` must be dropped -- incompatible in uv >=0.15.4 |

---

## Knowledge Gaps

1. **SCAR-004 (DEF-005) isolated-cache regression test**: No dedicated test confirms warm-up data is visible to request handlers when `InMemoryCacheProvider` is auto-detected. Carried forward from prior document.
2. **SCAR-008 (DEF-001) regression test**: No isolated regression test for the snapshot-ordering bug. Coverage implicit through session lifecycle tests.
3. **SCAR-013 import-fallback unit test**: No unit test exercises the `_SCHEMA_VERSIONING_AVAILABLE = False` path. Graceful degradation tested only implicitly by CI dependency installs.
4. **SCAR-015 regression test**: The section timeline pre-computation test file was not verified at line level.
5. **SCAR-015 through SCAR-021 numbering gap**: Commit history references SCAR-022 directly after SCAR-014 (in the prior document's scope). SCAR-015 through SCAR-021 were inferred from DEF/QA commit bodies and test markers. There may be additional SCAR entries in cross-repo history not visible in this repo's git log.
6. **SM-001, SM-002, SM-007, SM-008 (refactoring scars)**: Referenced in `src/autom8_asana/cache/backends/base.py` and commits `932dfc0` / `1a33859`. Not expanded here as they did not cause production failures.
7. **Round 13 open regression**: ECS rollout=FAILED at Poll 2 with failedTasks=0 and running=1/1. This pattern has not been classified as a SCAR yet.
8. **git history scope**: This audit reviewed 901 commits. Commits before the project's git history are not cataloged.
