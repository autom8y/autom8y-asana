---
domain: scar-tissue
generated_at: "2026-04-04T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "55aaab5"
confidence: 0.94
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/scar-tissue.md"
land_hash: "0a21b8d2148d7837d02525e91044995b417a2a2f282f4439282f157d9c27b46b"
---

# Codebase Scar Tissue

## Failure Catalog

This catalog documents 33 confirmed production or near-production failures. SCAR-001 through SCAR-030 plus SCAR-S3-LOOP carry forward from prior generation (source_hash 905fe4b, verified present at HEAD 55aaab5). Two new scars surfaced in commits 944a0e7 and e89875f (2026-04-01), post-dating the prior document's source_hash of 24d8e44. All fix file paths verified present at HEAD.

### SCAR-001: Entity Collision -- UnitHolder vs Unit GID Resolver
**Category**: Entity Resolution / Collision
**What failed**: Both "Business Units" and "Units" project names normalized to `"unit"`. Last-write-wins caused wrong project GID mapping.
**Commit**: `edb8b6d`
**Fix locations**:
- `src/autom8_asana/models/business/unit.py:479`
- `src/autom8_asana/services/discovery.py:29`
**Defensive pattern**: Every holder class carries `PRIMARY_PROJECT_GID`. Tier 1 resolution uses project membership before name normalization.
**Regression test**: `tests/unit/core/test_project_registry.py:225-270`

### SCAR-002: Orphaned IN_PROGRESS Sections Deadlock Cache Rebuild
**Category**: Concurrency / Race Condition
**What failed**: Sections stuck in `IN_PROGRESS` after crash were never retried, blocking SWR refresh.
**Commit**: `05549b8`
**Fix location**: `src/autom8_asana/dataframes/section_persistence.py:139-158` (`in_progress_since` timestamp + 5-minute stale timeout)
**Defensive pattern**: `in_progress_since: datetime | None` field on `SectionInfo`. `stale_timeout_seconds=300` default passed to `get_stale_sections()`.
**Regression test**: `tests/unit/dataframes/test_section_persistence_storage.py`

### SCAR-003: Force Rebuild Leaves Stale Merged Artifacts in S3
**Category**: Cache Coherence / Stale Data
**What failed**: `POST /admin/force-rebuild` deleted manifest and section parquets but left `dataframe.parquet` and `watermark.json`.
**Commit**: `05549b8`
**Fix location**: `src/autom8_asana/api/routes/admin.py:160` (ADR-HOTFIX-002)
**Defensive pattern**: Full artifact purge on force-rebuild.
**Regression test**: `tests/unit/api/routes/test_admin_force_rebuild.py`

### SCAR-004: Isolated Cache Providers -- Warm-up Data Invisible to Request Handlers (DEF-005)
**Category**: Cache Coherence / Stale Data
**What failed**: Each `AsanaClient` auto-detected its own `InMemoryCacheProvider`. Warm-up wrote to one; request handlers read from another.
**Commit**: `557a44c`
**Fix locations**:
- `src/autom8_asana/api/lifespan.py:108-130` — single shared `CacheProvider` from `AsanaConfig`, attached to `app.state`
- `src/autom8_asana/api/client_pool.py:201` — `DEF-005: inject shared cache_provider so pooled clients share`
**Defensive pattern**: Single shared `CacheProvider` at `app.state`.
**Known gap**: No dedicated isolated-provider regression test.

### SCAR-005: Cascade Field Null Rate -- 30% of Units with Null `office_phone`
**Category**: Data Model / Contract Violation
**What failed**: Tasks not re-registered in `HierarchyIndex` on S3 resume. ~30% null rate in cascade fields.
**Commit**: `9606712`
**Fix locations**:
- `src/autom8_asana/dataframes/builders/progressive.py:162,465,471,484`
- `src/autom8_asana/dataframes/cascade_utils.py:27,289`
- `src/autom8_asana/core/entity_registry.py:324`
**Defensive pattern**:
- `parent_gid` persisted to parquet; `WarmupOrderingError` (BROAD-CATCH immune) in `cascade_utils.py:22`
- Post-build cascade null rate audit: `CASCADE_NULL_WARN_THRESHOLD = 0.05`, `CASCADE_NULL_ERROR_THRESHOLD = 0.20`
- All cascade columns require explicit `source="cascade:..."` annotation
**Regression tests**:
- `tests/unit/dataframes/builders/test_cascade_validator.py:668`
- `tests/unit/dataframes/test_warmup_ordering_guard.py`
- `tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106`

### SCAR-006: Cascade Hierarchy Warming Gaps -- Silent Null Fields
**Category**: Cache Coherence / Stale Data
**What failed**: Transient hierarchy warming failures caused null cascade fields. Units excluded from resolution.
**Commit**: `6cf457e`
**Fix locations**:
- `src/autom8_asana/dataframes/views/cascade_view.py:356` — gap-skipping chain traversal
- `src/autom8_asana/dataframes/builders/cascade_validator.py:30-31`
- `src/autom8_asana/services/universal_strategy.py:458,504,515`
**Defensive pattern**: Chain traversal skips gaps. Grandparent fallback. `Null section maps to None (UNKNOWN) per SCAR-005/006`.
**Regression tests**: `tests/unit/services/test_universal_strategy_status.py:183,276`

### SCAR-007: SWR All-Sections-Skipped Produces Zero `total_rows`
**Category**: Cache Coherence / Stale Data
**What failed**: When all sections were `SKIPPED` during SWR, `total_rows` returned 0. Memory cache never promoted.
**Commit**: `9fbbb29`
**Fix location**: `src/autom8_asana/dataframes/builders/build_result.py` — `total_rows` uses `len(dataframe)` when DataFrame attached
**Regression test**: `tests/unit/dataframes/builders/test_build_result.py`

### SCAR-008: Snapshot Captured Before Accessor Cleared (DEF-001)
**Category**: Data Model / Contract Violation
**What failed**: In `SaveSession._post_commit_cleanup`, snapshot captured before custom field accessor cleared. Stale accessor state leaked into snapshot.
**Fix location**: `src/autom8_asana/persistence/session.py:1005-1011` — `DEF-001 FIX: Order matters - clear accessor BEFORE capturing snapshot`
**Defensive pattern**: Clear tracking state before snapshotting. Order documented in code comment.
**Known gap**: No isolated regression test.

### SCAR-009: `SyncInAsyncContextError` from `_auto_detect_workspace`
**Category**: Startup / Deployment Failure
**What failed**: Sync workspace detection called from async context raises `SyncInAsyncContextError`.
**Commits**: `dffb644`, `8366df9`
**Fix location**: `src/autom8_asana/client.py`
**Defensive pattern**: CI sets `ASANA_WORKSPACE_GID` universally. `sync_wrapper` raises immediately when called from event loop.

### SCAR-010: SaveSession State Transitions Not Thread-Safe (DEBT-003/005)
**Category**: Concurrency / Race Condition
**What failed**: No lock protecting state transitions. Concurrent access caused lost state.
**Commit**: `3f19a51`
**Fix location**: `src/autom8_asana/persistence/session.py` — `threading.RLock()` on all state mutations
**Regression test**: `tests/unit/persistence/test_session_concurrency.py` (19+ tests)

### SCAR-010b: Session TOCTOU -- `_ensure_open()` Not Thread-Safe (REMEDY-003)
**Category**: Concurrency / Race Condition
**What failed**: `_ensure_open()` checked state without lock. TOCTOU on 4 methods.
**Commit**: `1a6f514`
**Fix location**: `src/autom8_asana/persistence/session.py` — all 4 methods migrated to `_require_open()` context manager; `_ensure_open()` deleted
**Regression test**: `tests/unit/persistence/test_session_concurrency.py`

### SCAR-011: ECS Health Check Failure -- Liveness Blocked by Cache Warmup
**Category**: Startup / Deployment Failure
**What failed**: `/health` returned 503 during warming. ECS terminated task before it was ready.
**Commit**: `bb10cc7`
**Fix locations**:
- `src/autom8_asana/api/lifespan.py`
- `src/autom8_asana/api/routes/health.py`
**Defensive pattern**: Liveness/readiness separation: `/health` always 200; `/health/ready` gates on cache.

### SCAR-011b: Workflow Config Import Failure Silently Swallowed (REMEDY-002)
**Category**: Startup / Deployment Failure
**What failed**: `lifespan.py` try/except silently swallowed Lambda handler import errors. Workflow invoke returned 404.
**Commit**: `24266f0`
**Fix locations**:
- `src/autom8_asana/api/routes/health.py:79-106`
- `src/autom8_asana/api/lifespan.py`
**Defensive pattern**: `_workflow_configs_registered` flag surfaced in `/ready` response.
**Regression test**: `tests/unit/api/test_lifespan_workflow_import.py`

### SCAR-012: S2S Data-Service Auth Failure
**Category**: Authentication / Authorization
**What failed**: `DataServiceClient` created with no `auth_provider`. All cross-service joins returned zero matches.
**Commits**: `a51b173`, `df33fb8`
**Fix locations**:
- `src/autom8_asana/auth/service_token.py` — `ServiceTokenAuthProvider` implements `AuthProvider` protocol; migrated to `client_credentials` grant in commit `527c6ac` (REM-005)
- `src/autom8_asana/api/dependencies.py`
**Defensive pattern**: `ServiceTokenAuthProvider` now uses `SERVICE_CLIENT_ID` + `SERVICE_CLIENT_SECRET` (OAuth2 client_credentials grant, replacing legacy `SERVICE_API_KEY`).
**Note**: Auth migration REM-005 (commit `527c6ac`, 2026-04-03) supersedes the original `SERVICE_API_KEY` pattern.

### SCAR-013: Schema SDK Version Mismatch Causes ECS Exit Code 3
**Category**: Startup / Deployment Failure
**What failed**: `autom8y-cache` SDK import failure at module level caused ECS crash with exit code 3.
**Commit**: `869fddc`
**Fix location**: `src/autom8_asana/cache/integration/schema_providers.py` — `_SCHEMA_VERSIONING_AVAILABLE = False` guard
**Defensive pattern**: `try/except ImportError` with `_SCHEMA_VERSIONING_AVAILABLE` flag.
**Known gap**: No unit test exercises the `_SCHEMA_VERSIONING_AVAILABLE = False` path.

### SCAR-014: Lifecycle Config `extra="forbid"` Breaks Forward-Compatibility (D-LC-002)
**Category**: Data Model / Contract Violation
**What failed**: `extra="forbid"` on 11 lifecycle config models broke YAML configs with unknown fields.
**Commit**: `5a24194` (revert; original was `b493ff3`)
**Fix location**: `src/autom8_asana/lifecycle/config.py` — all 11 lifecycle config models have `extra="ignore"`
**Defensive pattern**: Non-lifecycle models (2 webhook, 3 seeder) keep `extra="forbid"`. Lifecycle models must remain forward-compatible (D-LC-002).
**Regression test**: `tests/integration/test_lifecycle_smoke.py:1720-1751`

### SCAR-015: Timeline Request Handler 504 Gateway Timeout (DEF-006/7/8)
**Category**: Performance Cliff / Timeout
**What failed**: Per-request story I/O exceeded ALB 60-second timeout for ~3,800 offers.
**Commits**: `a347db6`, `8b5813e`
**Fix locations**:
- `src/autom8_asana/api/lifespan.py` (DEF-006 pre-compute at warm-up)
- `src/autom8_asana/services/section_timeline_service.py`
**Defensive pattern**: All I/O moved to warm-up. Request handlers do pure-CPU day counting from pre-computed data.
**Regression tests**:
- `tests/unit/services/test_section_timeline_service.py`
- `tests/unit/api/test_routes_section_timelines.py`

### SCAR-016: Conversation Audit DEF-001 -- `date_range_days` Not Forwarded
**Category**: Workflow Logic Gap
**What failed**: `date_range_days` accepted by workflow but not forwarded to export. All audits used hardcoded default.
**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py`
**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py:642`

### SCAR-017: Conversation Audit DEF-002 -- `csv_row_count` Missing from Dry-Run
**Category**: Workflow Logic Gap
**What failed**: `metadata['csv_row_count']` absent in dry-run path, causing `KeyError`.
**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py`
**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py:1362`

### SCAR-018: Polling Scheduler Zero Test Coverage (DEF-003)
**Category**: Workflow Logic Gap
**What failed**: `_evaluate_rules` dispatch path had zero coverage. Silent failure risk.
**Regression test**: `tests/unit/automation/polling/test_polling_scheduler.py:839,928,1036`

### SCAR-019: PollingScheduler ScheduleConfig Validator Zero Coverage (DEF-005)
**Category**: Workflow Logic Gap
**What failed**: `ScheduleConfig` validators had zero coverage.
**Regression test**: `tests/unit/automation/polling/test_config_schema.py:492,566`

### SCAR-020: Resolver Phone Trailing Newline Not Stripped (DEF-002)
**Category**: Workflow Logic Gap
**What failed**: Phone values with trailing newlines passed through without normalization. Reconciliation join key mismatch.
**Fix location**: `src/autom8_asana/api/routes/resolver.py` — validation applied on input
**Defensive pattern**: `PhoneTextField` descriptor in `src/autom8_asana/models/business/descriptors.py:478-497` normalizes to E.164 on read. Idempotent.
**Regression tests**:
- `tests/unit/api/test_routes_resolver.py:565`
- `tests/unit/models/business/matching/test_normalizers.py:65-67`

### SCAR-021: STANDARD_ERROR_RESPONSES Type Too Narrow
**Category**: Integration Failure / CI
**What failed**: `dict[int, ...]` type on `STANDARD_ERROR_RESPONSES` rejected by mypy strict for FastAPI `responses=` parameter.
**Fix location**: `src/autom8_asana/api/error_responses.py`
**Regression test**: mypy strict CI gate.

### SCAR-022: uv `--frozen` + `--no-sources` Mutually Exclusive (DEF-009)
**Category**: Startup / Deployment Failure
**What failed**: uv >=0.15.4 made `--frozen` and `--no-sources` flags mutually exclusive. Docker build failed silently in some CI environments.
**Commit**: `3e0790b`
**Fix location**: `Dockerfile:11,51` — `--no-sources` without `--frozen`. Comment documents constraint `DEF-009/SCAR-022`.
**Defensive pattern**: Comment at both Dockerfile `pip install` sites.

### SCAR-023: Offer Cascade Source Bypass -- 30-40% Null Rate
**Category**: Data Model / Contract Violation
**What failed**: `offer.office` field had `source=None`, bypassing cascade pipeline. 30-40% null rate in office data.
**Commit**: `bbba220`
**Fix locations**:
- `src/autom8_asana/dataframes/schemas/offer.py`
- `src/autom8_asana/dataframes/builders/cascade_validator.py`
- `src/autom8_asana/dataframes/views/cascade_view.py`
**Defensive pattern**: All cascade-sourced columns require explicit `source="cascade:..."`. Schema version bumped.
**Regression test**: `tests/unit/dataframes/builders/test_cascade_validator.py` (580+ lines added)

### SCAR-024: PhoneNormalizer Wired Only in Matching Engine
**Category**: Data Model / Contract Violation
**What failed**: Read path served raw phone values. Reconciliation blindness on join key — mismatched `+1XXXXXXXXXX` vs `XXXXXXXXXX`.
**Commit**: `bbba220`
**Fix location**: `src/autom8_asana/models/business/descriptors.py` — `PhoneTextField` descriptor normalizing to E.164 on read. Idempotent.
**Regression test**: `tests/unit/models/business/matching/test_normalizers.py:65`

### SCAR-025: asset_edit HTTP 500 -- DataFrame Construction + Missing Cascade Store
**Category**: Data Model / Contract Violation
**What failed**: `schema=asset_edit` returned HTTP 500. `DataFrameViewPlugin.materialize_async()` skipped row-type coercion; empty `UnifiedTaskStore` had no parent data.
**Commit**: `26e36a4`
**Fix locations**:
- `src/autom8_asana/dataframes/builders/fields.py`
- `src/autom8_asana/dataframes/exceptions.py`
- `src/autom8_asana/dataframes/builders/base.py`
**Defensive pattern**: `safe_dataframe_construct()` at all 6 construction sites. `DataFrameConstructionError` maps to HTTP 422.

### SCAR-026: Workflow Calls Non-Existent Method -- Masked by MagicMock
**Category**: Integration Failure / CI
**What failed**: Three workflows called non-existent `tasks.list_for_project_async()`. MagicMock silently accepted any attribute.
**Commit**: `c52a521`
**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` (and `insights/`, `pipeline_transition.py`)
**Defensive pattern**: Test mocks must use `spec=` to catch attribute access on non-existent methods.
**Known gap**: No systematic audit confirms all workflow test mocks use `spec=`.

### SCAR-027: `re.sub` Backreference Injection in Entity Name Generation
**Category**: Security / Input Validation
**What failed**: User-controlled `business_name` string passed directly as `re.sub` replacement; backreferences like `\1` were interpreted.
**Commit**: `e82d056`
**Fix location**: `src/autom8_asana/core/creation.py:82-97` — lambda replacement prevents backreference interpretation
**Regression test**: `tests/unit/core/test_creation.py` (12 cases)

### SCAR-028: PII Phone Number Leakage in gid_push Error Logs
**Category**: Security / Input Validation
**What failed**: `gid_push.py` logged `response.text[:500]` containing phone numbers in error paths.
**Commit**: `e82d056`
**Fix locations**:
- `src/autom8_asana/services/gid_push.py:198,206,217`
- `src/autom8_asana/clients/data/_endpoints/batch.py:80,120,154,196`
- `src/autom8_asana/clients/data/_cache.py:82,83,97,169,171,192`
**Defensive pattern**: `mask_pii_in_string()` from `src/autom8_asana/clients/data/_pii.py:61`
**Regression test**: `tests/unit/services/test_gid_push.py`

### SCAR-029: Whitespace-Only GID Bypass in Webhook Handler
**Category**: Security / Input Validation
**What failed**: `{"gid": "   "}` passed truthiness check; Pydantic stripped to empty string post-validation.
**Commit**: `7dd9aed`
**Fix location**: `src/autom8_asana/api/routes/webhooks.py:375-381` — explicit `str.strip()` guard before Pydantic normalization
**Regression test**: 45 adversarial tests, 78+ total webhook tests.

### SCAR-030: Classifier Section Names Invented -- Not From Live Asana API
**Category**: Data Model / Contract Violation
**What failed**: Process section classifier used title-case names not present in any Asana project.
**Commits**: `7f35ea7`, `905fe4b`
**Fix locations**:
- `src/autom8_asana/models/business/activity.py`
- `src/autom8_asana/models/business/unit.py`
**Defensive pattern**: Section names standardized to ALL CAPS per Asana convention. Live API verification required before adding new names.
**Known gap**: No automated test validates section names against live Asana API.

### SCAR-S3-LOOP: S3 Degradation Loop Causing Production Data Loss
**Category**: Cache Coherence / Stale Data
**What failed**: `NoSuchKey` errors fed to circuit breaker, poisoning it permanently. No recovery path.
**Commit**: `731a0f5`
**Fix locations**:
- `src/autom8_asana/core/retry.py:198-267` — `_PERMANENT_S3_ERROR_CODES` frozenset; `NoSuchKey` not fed to CB
- `src/autom8_asana/dataframes/storage.py`
**Defensive pattern**: `_PERMANENT_S3_ERROR_CODES = frozenset({"NoSuchKey", ...})` at line 198. HALF_OPEN recovery within 60s.
**Regression tests**:
- `tests/unit/core/test_retry.py` (86 tests)
- `tests/unit/dataframes/test_storage.py` (63 tests)

### Env Var Naming Scar: AUTOM8_DATA_API_KEY vs AUTOM8Y_DATA_API_KEY
**Category**: Authentication / Authorization
**What failed**: Missing "Y" in env var caused silent S2S auth failure in production.
**Commits**: `68c2561`, `c9273d8`
**Fix locations**:
- `src/autom8_asana/settings.py`
- `secretspec.toml`
- `src/autom8_asana/clients/data/config.py:242`
**Defensive pattern**: ADR-ENV-NAMING-CONVENTION requires `AUTOM8Y_` prefix for all ecosystem env vars.

### SCAR-IDEM-001: Idempotency Key Finalize Failure -- Double-Execution Risk (NEW)
**Category**: Data Model / Contract Violation
**What failed**: `dispatch()` handler `try/except` around `store.finalize()` swallows all exceptions. If finalize fails, idempotency key is not persisted and retry will re-execute the mutation.
**Commit**: `944a0e7` (VERIFY-BEFORE-PROD annotation, 2026-04-01)
**Fix location**: `src/autom8_asana/api/middleware/idempotency.py:730` — exception promoted to `logger.exception` with `impact` field
**Defensive pattern**: Observability-only fix. VERIFY-BEFORE-PROD comment documents that S2S callers with strict-once semantics require an error metric.
**Known gap**: Double-execution risk not yet fully mitigated.

### SCAR-REG-001: Section Registry GIDs Are Fabricated Placeholders (NEW)
**Category**: Data Model / Contract Violation
**What failed**: `EXCLUDED_SECTION_GIDS` and `UNIT_SECTION_GIDS` contain sequential placeholder values not verified against the live Asana API.
**Commit**: `e89875f` (2026-04-01)
**Fix location**: `src/autom8_asana/reconciliation/section_registry.py:57,79,94,128` — `_validate_gid_set()` at module import
**Defensive pattern**:
- `_ASANA_GID_PATTERN` validates 10-20 digit numeric GIDs at import time
- `_looks_sequential()` heuristic warns if 4+ consecutive integer GIDs detected
- `VERIFY-BEFORE-PROD` annotations on both GID sets
**Known gap**: Must verify via `GET /projects/1201081073731555/sections` before production.

---

## Category Coverage

| Category | Scars | Count |
|---|---|---|
| Cache Coherence / Stale Data | SCAR-003, SCAR-004, SCAR-005, SCAR-006, SCAR-007, SCAR-S3-LOOP | 6 |
| Data Model / Contract Violation | SCAR-008, SCAR-014, SCAR-023, SCAR-024, SCAR-025, SCAR-030, SCAR-IDEM-001, SCAR-REG-001 | 8 |
| Startup / Deployment Failure | SCAR-009, SCAR-011, SCAR-011b, SCAR-013, SCAR-022 | 5 |
| Workflow Logic Gap | SCAR-016, SCAR-017, SCAR-018, SCAR-019, SCAR-020 | 5 |
| Security / Input Validation | SCAR-027, SCAR-028, SCAR-029 | 3 |
| Concurrency / Race Condition | SCAR-002, SCAR-010, SCAR-010b | 3 |
| Authentication / Authorization | SCAR-012, Env Var Naming | 2 |
| Integration Failure / CI | SCAR-021, SCAR-026 | 2 |
| Entity Resolution / Collision | SCAR-001 | 1 |
| Performance Cliff / Timeout | SCAR-015 | 1 |

10 categories. 33 named scars total. Categories searched but not found: schema migration failures, distributed coordination failures, network partition handling.

---

## Fix-Location Mapping

All 33 scars mapped. All primary fix-file paths verified present at HEAD (55aaab5). See individual scar entries above for exact file:line references.

---

## Defensive Pattern Documentation

### Cascade Defense-in-Depth (SCAR-005/006/023)

Four-layer defense:

1. **Schema enforcement**: All cascade-sourced columns require `source="cascade:..."` in `DataFrameSchema`. Absence is a schema validation error.
2. **Warm-up ordering guard**: `WarmupOrderingError` class at `src/autom8_asana/dataframes/cascade_utils.py:22` — explicitly documented as BROAD-CATCH immune.
3. **Post-build null rate audit**: `CASCADE_NULL_WARN_THRESHOLD = 0.05` (5%) and `CASCADE_NULL_ERROR_THRESHOLD = 0.20` (20%) at `src/autom8_asana/dataframes/builders/cascade_validator.py:31-32`.
4. **Chain traversal gap-skipping**: `src/autom8_asana/dataframes/views/cascade_view.py:356` skips missing hierarchy links; grandparent fallback path.

### Session Thread Safety (SCAR-010/010b)

- `threading.RLock()` on all state mutations in `src/autom8_asana/persistence/session.py`
- `_require_open()` context manager replaces all bare state checks
- `_ensure_open()` deleted (zero callers)

### Health Check Separation (SCAR-011/011b)

- `/health` returns 200 unconditionally (liveness probe)
- `/health/ready` gates on `_cache_ready` AND `_workflow_configs_registered` flags
- Pattern: any new startup dependency must be gated through `/health/ready`, not `/health`

### Security Hardening (SCAR-027/028/029)

- Lambda replacement in `re.sub` at `src/autom8_asana/core/creation.py:82-97`
- `mask_pii_in_string()` at `src/autom8_asana/clients/data/_pii.py:61` — applied at 10+ error log sites
- `str.strip()` GID guard at `src/autom8_asana/api/routes/webhooks.py:375-381`

### BROAD-CATCH Classification

20+ `except Exception` blocks annotated with classification:
- `ADVISORY`: optional enrichment; service degrades gracefully
- `SCAR-IDEM-001: VERIFY-BEFORE-PROD`: critical path where swallowing has correctness impact

### S3 Circuit Breaker (SCAR-S3-LOOP)

`_PERMANENT_S3_ERROR_CODES: frozenset[str]` at `src/autom8_asana/core/retry.py:198-200`. These error codes are never fed to circuit breaker state. HALF_OPEN recovery within 60s.

---

## Agent-Relevance Tagging

| Scar | Relevant Roles | Constraint |
|---|---|---|
| SCAR-001 | principal-engineer, architect | New entity/holder classes must define `PRIMARY_PROJECT_GID` |
| SCAR-002 | principal-engineer | Section persistence must use `in_progress_since` + stale timeout |
| SCAR-005/006 | principal-engineer | New cascade columns must use `source="cascade:..."` and appear in BASE_SCHEMA |
| SCAR-008 | principal-engineer | In `SaveSession`, always clear accessor state BEFORE capturing snapshot |
| SCAR-009 | principal-engineer, qa-adversary | Tests must set `ASANA_WORKSPACE_GID`; never rely on sync auto-detect |
| SCAR-010/010b | principal-engineer | All `SaveSession` state access through `_require_open()` context manager |
| SCAR-011 | platform-engineer | ECS health checks must target `/health` (liveness), never `/health/ready` |
| SCAR-011b | principal-engineer | Any new startup dependency must gate through `/health/ready`, not `/health` |
| SCAR-012 | principal-engineer | New cross-service clients must use `ServiceTokenAuthProvider` with `client_credentials` grant |
| SCAR-013 | principal-engineer | Optional SDK imports must use `try/except ImportError` with feature flag |
| SCAR-014 | principal-engineer | Lifecycle config models must NOT set `extra="forbid"` (D-LC-002) |
| SCAR-015 | architect | I/O-heavy data for request handlers must be pre-computed at warm-up |
| SCAR-023 | principal-engineer | `source=None` silently bypasses cascade pipeline; always use `source="cascade:..."` |
| SCAR-026 | qa-adversary | Test mocks for SDK clients must use `spec=` |
| SCAR-027 | principal-engineer | Never pass user-controlled strings as `re.sub` replacement; use `lambda m: value` |
| SCAR-028 | principal-engineer | All error log sites with user data must call `mask_pii_in_string()` |
| SCAR-029 | principal-engineer | Validate GIDs with `str.strip()` before Pydantic normalization |
| SCAR-030 | principal-engineer | Section names must come from live Asana API verification (ALL CAPS) |
| SCAR-S3-LOOP | platform-engineer | Permanent S3 errors must not be fed to circuit breaker |
| SCAR-IDEM-001 | principal-engineer | S2S callers with strict-once semantics need an error metric on finalize failure |
| SCAR-REG-001 | platform-engineer | Section GIDs require live API verification before production |
| Env Var | principal-engineer | All ecosystem env vars use `AUTOM8Y_` prefix |

---

## Knowledge Gaps

1. **SCAR-004 and SCAR-008 isolation tests absent**: No dedicated regression tests for either scar.
2. **SCAR-013 import-fallback path untested**: No unit test exercises the `_SCHEMA_VERSIONING_AVAILABLE = False` path.
3. **SCAR-026 mock-spec audit missing**: No systematic review confirms all workflow test mocks use `spec=`.
4. **BROAD-CATCH completeness**: No centralized audit confirms all degradation paths produce observable signals.
5. **PII masking completeness**: No systematic audit confirms all log sites that could emit user data call `mask_pii_in_string()`.
6. **SCAR-030 classifier drift**: No automated test validates section names against live Asana API.
7. **SCAR-IDEM-001 mitigation incomplete**: Observability-only fix. Double-execution risk for strict-once callers not fully mitigated.
8. **SCAR-REG-001 production blocker**: Sequential placeholder GIDs must be replaced with verified GIDs before production.
9. **Auth migration (REM-005) documentation**: SCAR-012 auth description updated to reflect `client_credentials` grant (commit `527c6ac`).
