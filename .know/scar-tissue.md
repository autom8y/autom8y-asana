---
domain: scar-tissue
generated_at: "2026-04-01T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "24d8e44"
confidence: 0.93
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

This catalog documents 31 confirmed production or near-production failures plus deployment/CI scars. SCAR-001 through SCAR-030 carry forward from the prior generation (source_hash 905fe4b, 2026-03-29). SCAR-S3-LOOP is surfaced as a distinct named entry. No new production scars identified in the 7 commits between 905fe4b and HEAD (24d8e44). All fix file paths verified present at HEAD.

### SCAR-001: Entity Collision -- UnitHolder vs Unit GID Resolver
**Category**: Entity Resolution / Collision
**What failed**: Both "Business Units" and "Units" project names normalized to `"unit"`. Last-write-wins caused wrong project GID mapping.
**Commit**: `edb8b6d`
**Fix location**: `src/autom8_asana/models/business/unit.py:479`, `src/autom8_asana/services/discovery.py:29`
**Defensive pattern**: Every holder class carries `PRIMARY_PROJECT_GID`. Tier 1 resolution uses project membership before name normalization.
**Regression test**: `tests/unit/core/test_project_registry.py:225-270`

### SCAR-002: Orphaned IN_PROGRESS Sections Deadlock Cache Rebuild
**Category**: Concurrency / Race Condition
**What failed**: Sections stuck in `IN_PROGRESS` after crash were never retried, blocking SWR refresh.
**Commit**: `05549b8`
**Fix location**: `src/autom8_asana/dataframes/section_persistence.py:139-158`
**Defensive pattern**: `in_progress_since` timestamp + 5-minute stale timeout.
**Regression test**: `tests/unit/dataframes/test_section_persistence_storage.py`

### SCAR-003: Force Rebuild Leaves Stale Merged Artifacts in S3
**Category**: Cache Coherence / Stale Data
**What failed**: `POST /admin/force-rebuild` left `dataframe.parquet` and `watermark.json` after deleting manifest + section parquets.
**Commit**: `05549b8`
**Fix location**: `src/autom8_asana/api/routes/admin.py:160` (ADR-HOTFIX-002)
**Defensive pattern**: Full artifact purge on force-rebuild.
**Regression test**: `tests/unit/api/routes/test_admin_force_rebuild.py`

### SCAR-004: Isolated Cache Providers -- Warm-up Data Invisible to Request Handlers (DEF-005)
**Category**: Cache Coherence / Stale Data
**What failed**: Each `AsanaClient` auto-detected its own `InMemoryCacheProvider`. Warm-up wrote to one; handlers read from another.
**Commit**: `557a44c`
**Fix location**: `src/autom8_asana/api/lifespan.py:108-130`, `src/autom8_asana/api/client_pool.py:201`
**Defensive pattern**: Single shared `CacheProvider` from `AsanaConfig`, attached to `app.state`.
**Regression test**: No dedicated isolated-provider regression test (known gap).

### SCAR-005: Cascade Field Null Rate -- 30% of Units with Null `office_phone`
**Category**: Data Model / Contract Violation
**What failed**: Tasks not re-registered in `HierarchyIndex` on S3 resume. ~30% null rate in cascade fields.
**Commit**: `9606712`
**Fix location**: `src/autom8_asana/dataframes/schemas/base.py` (parent_gid column), `src/autom8_asana/dataframes/builders/progressive.py:465,484`
**Defensive pattern**: `parent_gid` persisted to parquet. Post-build cascade null rate audit with WARN (5%) and ERROR (20%) thresholds.
**Regression test**: `tests/unit/dataframes/builders/test_cascade_validator.py:668`, `tests/unit/dataframes/test_warmup_ordering_guard.py`, `tests/unit/dataframes/test_cascade_ordering_assertion.py`

### SCAR-006: Cascade Hierarchy Warming Gaps -- Silent Null Fields
**Category**: Cache Coherence / Stale Data
**What failed**: Transient hierarchy warming failures caused null cascade fields. Units excluded from resolution.
**Commit**: `6cf457e`
**Fix location**: `src/autom8_asana/dataframes/views/cascade_view.py:356`, `src/autom8_asana/dataframes/builders/cascade_validator.py`, `src/autom8_asana/services/universal_strategy.py:458,504,515`
**Defensive pattern**: Chain traversal skips gaps. Grandparent fallback. Null section maps to `None` (UNKNOWN).
**Regression test**: `tests/unit/services/test_universal_strategy_status.py:183,276`, `tests/unit/dataframes/test_cascade_ordering_assertion.py:71-106`

### SCAR-007: SWR All-Sections-Skipped Produces Zero `total_rows`
**Category**: Cache Coherence / Stale Data
**What failed**: When all sections were `SKIPPED` during SWR, `total_rows` returned 0. Memory cache never promoted.
**Commit**: `9fbbb29`
**Fix location**: `src/autom8_asana/dataframes/builders/build_result.py`
**Defensive pattern**: `total_rows` uses `len(dataframe)` when DataFrame attached.
**Regression test**: `tests/unit/dataframes/builders/test_build_result.py`

### SCAR-008: Snapshot Captured Before Accessor Cleared (DEF-001)
**Category**: Data Model / Contract Violation
**What failed**: In `SaveSession._post_commit_cleanup`, snapshot captured before custom field accessor cleared.
**Fix location**: `src/autom8_asana/persistence/session.py:1005-1011`
**Defensive pattern**: Clear tracking state before snapshotting. Order documented in code comment.
**Regression test**: No isolated regression test (known gap).

### SCAR-009: `SyncInAsyncContextError` from `_auto_detect_workspace`
**Category**: Startup / Deployment Failure
**What failed**: Sync workspace detection in async context raises `SyncInAsyncContextError`.
**Commits**: `dffb644`, `8366df9`
**Fix location**: `src/autom8_asana/client.py`
**Defensive pattern**: CI sets `ASANA_WORKSPACE_GID` universally.
**Regression test**: Async client instantiation tests; CI env var guard.

### SCAR-010: SaveSession State Transitions Not Thread-Safe (DEBT-003/005)
**Category**: Concurrency / Race Condition
**What failed**: No lock protecting state transitions. Concurrent access caused lost state.
**Commit**: `3f19a51`
**Fix location**: `src/autom8_asana/persistence/session.py`
**Defensive pattern**: `threading.RLock()` + `_require_open()` context manager.
**Regression test**: `tests/unit/persistence/test_session_concurrency.py` (19+ tests)

### SCAR-010b: Session TOCTOU -- `_ensure_open()` Not Thread-Safe (REMEDY-003)
**Category**: Concurrency / Race Condition
**What failed**: `_ensure_open()` checked state without lock. TOCTOU on 4 methods.
**Commit**: `1a6f514`
**Fix location**: `src/autom8_asana/persistence/session.py`
**Defensive pattern**: All methods migrated to `_require_open()`. `_ensure_open()` deleted.
**Regression test**: `tests/unit/persistence/test_session_concurrency.py`

### SCAR-011: ECS Health Check Failure -- Liveness Blocked by Cache Warmup
**Category**: Startup / Deployment Failure
**What failed**: `/health` returned 503 during warming. ECS terminated task before ready.
**Commit**: `bb10cc7`
**Fix location**: `src/autom8_asana/api/lifespan.py`, `src/autom8_asana/api/routes/health.py`
**Defensive pattern**: Liveness/readiness separation: `/health` always 200; `/health/ready` gates on cache.
**Regression test**: Health endpoint tests.

### SCAR-011b: Workflow Config Import Failure Silently Swallowed (REMEDY-002)
**Category**: Startup / Deployment Failure
**What failed**: `lifespan.py` try/except silently swallowed Lambda handler import errors. Workflow invoke returned 404.
**Commit**: `24266f0`
**Fix location**: `src/autom8_asana/api/routes/health.py:79-106`, `src/autom8_asana/api/lifespan.py`
**Defensive pattern**: `_workflow_configs_registered` flag surfaced in `/ready`.
**Regression test**: `tests/unit/api/test_lifespan_workflow_import.py`

### SCAR-012: S2S Data-Service Auth Failure
**Category**: Authentication / Authorization
**What failed**: `DataServiceClient` created with no `auth_provider`. All cross-service joins returned zero matches.
**Commits**: `a51b173`, `df33fb8`
**Fix location**: `src/autom8_asana/auth/service_token.py`, `src/autom8_asana/api/dependencies.py`
**Defensive pattern**: `ServiceTokenAuthProvider` implements `AuthProvider` protocol.
**Regression test**: Auth integration tests.

### SCAR-013: Schema SDK Version Mismatch Causes ECS Exit Code 3
**Category**: Startup / Deployment Failure
**What failed**: `autom8y-cache` SDK import failure at module level caused ECS crash.
**Commit**: `869fddc`
**Fix location**: `src/autom8_asana/cache/integration/schema_providers.py`
**Defensive pattern**: `try/except ImportError` with `_SCHEMA_VERSIONING_AVAILABLE` flag.
**Regression test**: CI dependency matrix. No specific unit test (known gap).

### SCAR-014: Lifecycle Config `extra="forbid"` Breaks Forward-Compatibility (D-LC-002)
**Category**: Data Model / Contract Violation
**What failed**: `extra="forbid"` on 11 lifecycle models broke YAML configs with unknown fields.
**Commit**: `5a24194`
**Fix location**: `src/autom8_asana/lifecycle/config.py`
**Defensive pattern**: Lifecycle config models use `extra="ignore"`.
**Regression test**: `tests/integration/test_lifecycle_smoke.py:1720-1751`

### SCAR-015: Timeline Request Handler 504 Gateway Timeout (DEF-006/7/8)
**Category**: Performance Cliff / Timeout
**What failed**: Per-request story I/O exceeded ALB 60s timeout for ~3,800 offers.
**Commits**: `a347db6`, `8b5813e`
**Fix location**: `src/autom8_asana/api/lifespan.py` (DEF-006), `src/autom8_asana/services/section_timeline_service.py`
**Defensive pattern**: All I/O moved to warm-up. Request handlers do pure-CPU day counting.
**Regression test**: `tests/unit/services/test_section_timeline_service.py`, `tests/unit/api/test_routes_section_timelines.py`

### SCAR-016: Conversation Audit DEF-001 -- `date_range_days` Not Forwarded
**Category**: Workflow Logic Gap
**What failed**: `date_range_days` accepted but not forwarded to export. All audits used hardcoded default.
**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py`
**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py:642`

### SCAR-017: Conversation Audit DEF-002 -- `csv_row_count` Missing from Dry-Run
**Category**: Workflow Logic Gap
**What failed**: `metadata['csv_row_count']` absent in dry-run, causing KeyError.
**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py`
**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py:1362`

### SCAR-018: Polling Scheduler Zero Test Coverage (DEF-003)
**Category**: Workflow Logic Gap
**What failed**: `_evaluate_rules` dispatch path had zero coverage.
**Regression test**: `tests/unit/automation/polling/test_polling_scheduler.py:839,928,1036`

### SCAR-019: PollingScheduler ScheduleConfig Validator Zero Coverage (DEF-005)
**Category**: Workflow Logic Gap
**What failed**: `ScheduleConfig` validators had zero coverage.
**Regression test**: `tests/unit/automation/polling/test_config_schema.py:492,566`

### SCAR-020: Resolver Phone Trailing Newline Not Stripped (DEF-002)
**Category**: Workflow Logic Gap
**What failed**: Phone values with trailing newlines passed through without normalization.
**Fix location**: `src/autom8_asana/api/routes/resolver.py`
**Defensive pattern**: `PhoneTextField` descriptor normalizes to E.164 on read.
**Regression test**: `tests/unit/api/test_routes_resolver.py:565`, `tests/unit/models/business/matching/test_normalizers.py:65`

### SCAR-021: STANDARD_ERROR_RESPONSES Type Too Narrow
**Category**: Integration Failure / CI
**What failed**: `dict[int, ...]` rejected by mypy strict for FastAPI `responses=`.
**Fix location**: `src/autom8_asana/api/error_responses.py`
**Regression test**: mypy strict CI gate.

### SCAR-022: uv `--frozen` + `--no-sources` Mutually Exclusive (DEF-009)
**Category**: Startup / Deployment Failure
**What failed**: uv >=0.15.4 made flags mutually exclusive. Docker build failed.
**Commit**: `3e0790b`
**Fix location**: `Dockerfile`
**Defensive pattern**: `--no-sources` without `--frozen`. Comment documents constraint.
**Regression test**: CI Docker build step.

### SCAR-023: Offer Cascade Source Bypass -- 30-40% Null Rate
**Category**: Data Model / Contract Violation
**What failed**: `offer.office` had `source=None`, bypassing cascade pipeline. 30-40% null rate.
**Commit**: `bbba220`
**Fix location**: `src/autom8_asana/dataframes/schemas/offer.py`, `src/autom8_asana/dataframes/builders/cascade_validator.py`, `src/autom8_asana/dataframes/views/cascade_view.py`
**Defensive pattern**: All cascade-sourced columns require explicit `source="cascade:..."`. Schema version bumped.
**Regression test**: `tests/unit/dataframes/builders/test_cascade_validator.py` (580+ lines added)

### SCAR-024: PhoneNormalizer Wired Only in Matching Engine
**Category**: Data Model / Contract Violation
**What failed**: Read path served raw phone values. Reconciliation blindness on join key.
**Commit**: `bbba220`
**Fix location**: `src/autom8_asana/models/business/descriptors.py`
**Defensive pattern**: `PhoneTextField` descriptor normalizing to E.164 on read. Idempotent.
**Regression test**: `tests/unit/models/business/matching/test_normalizers.py:65`

### SCAR-025: asset_edit HTTP 500 -- DataFrame Construction + Missing Cascade Store
**Category**: Data Model / Contract Violation
**What failed**: `schema=asset_edit` returned 500. `DataFrameViewPlugin.materialize_async()` skipped coercion; empty `UnifiedTaskStore` had no parent data.
**Commit**: `26e36a4`
**Fix location**: `src/autom8_asana/dataframes/builders/fields.py`, `src/autom8_asana/dataframes/exceptions.py`, `src/autom8_asana/dataframes/builders/base.py`
**Defensive pattern**: `safe_dataframe_construct()` at all 6 construction sites. `DataFrameConstructionError` -> HTTP 422.
**Regression test**: 1760 dataframes+services tests, 702 API tests pass.

### SCAR-026: Workflow Calls Non-Existent Method -- Masked by MagicMock
**Category**: Integration Failure / CI
**What failed**: Three workflows called non-existent `tasks.list_for_project_async()`. MagicMock silently accepted.
**Commit**: `c52a521`
**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py`, `insights/`, `pipeline_transition.py`
**Regression test**: Updated workflow tests verify correct method.

### SCAR-027: `re.sub` Backreference Injection in Entity Name Generation
**Category**: Security / Input Validation
**What failed**: User-controlled `business_name` in `re.sub` replacement interpreted backreferences.
**Commit**: `e82d056`
**Fix location**: `src/autom8_asana/core/creation.py:82-97`
**Defensive pattern**: Lambda replacement prevents backreference interpretation.
**Regression test**: `tests/unit/core/test_creation.py` (12 cases)

### SCAR-028: PII Phone Number Leakage in gid_push Error Logs
**Category**: Security / Input Validation
**What failed**: `gid_push.py` logged `response.text[:500]` containing phone numbers.
**Commit**: `e82d056`
**Fix location**: `src/autom8_asana/services/gid_push.py:202,210,219`, `src/autom8_asana/clients/data/_endpoints/batch.py`, `src/autom8_asana/clients/data/_cache.py`
**Defensive pattern**: `mask_pii_in_string()` from `src/autom8_asana/clients/data/_pii.py`.
**Regression test**: `tests/unit/services/test_gid_push.py`

### SCAR-029: Whitespace-Only GID Bypass in Webhook Handler
**Category**: Security / Input Validation
**What failed**: `{"gid": "   "}` passed truthiness check; Pydantic stripped to empty string.
**Commit**: `7dd9aed`
**Fix location**: `src/autom8_asana/api/routes/webhooks.py:375-381`
**Defensive pattern**: Explicit `str.strip()` guard before validation.
**Regression test**: 45 adversarial tests, 78 total webhook tests.

### SCAR-030: Classifier Section Names Invented -- Not From Live Asana API
**Category**: Data Model / Contract Violation
**What failed**: Process section classifier used title-case names not present in any Asana project.
**Commits**: `7f35ea7`, `905fe4b`
**Fix location**: `src/autom8_asana/models/business/activity.py`, `src/autom8_asana/models/business/unit.py`
**Defensive pattern**: Section names standardized to ALL CAPS per Asana convention. Live API verification required.
**Regression test**: Updated test assertions.

### SCAR-S3-LOOP: S3 Degradation Loop Causing Production Data Loss
**Category**: Cache Coherence / Stale Data
**What failed**: `NoSuchKey` errors poisoned circuit breaker permanently. No recovery path.
**Commit**: `731a0f5`
**Fix location**: `src/autom8_asana/core/retry.py`, `src/autom8_asana/dataframes/storage.py`
**Defensive pattern**: `_PERMANENT_S3_ERROR_CODES` frozenset; `NoSuchKey` not fed to CB. HALF_OPEN recovery within 60s.
**Regression test**: `tests/unit/core/test_retry.py` (221 tests), `tests/unit/dataframes/test_storage.py` (301+ tests)

### Env Var Naming Scar: AUTOM8_DATA_API_KEY vs AUTOM8Y_DATA_API_KEY
**Category**: Authentication / Authorization
**What failed**: Missing "Y" in env var caused silent S2S auth failure.
**Commits**: `68c2561`, `c9273d8`
**Fix location**: `src/autom8_asana/settings.py`, `secretspec.toml`
**Defensive pattern**: ADR-ENV-NAMING-CONVENTION requires `AUTOM8Y_` prefix.

## Category Coverage Summary

| Category | Scars | Count |
|---|---|---|
| Cache Coherence / Stale Data | SCAR-003, SCAR-004, SCAR-005, SCAR-006, SCAR-007, SCAR-S3-LOOP | 6 |
| Data Model / Contract Violation | SCAR-008, SCAR-014, SCAR-023, SCAR-024, SCAR-025, SCAR-030 | 6 |
| Startup / Deployment Failure | SCAR-009, SCAR-011, SCAR-011b, SCAR-013, SCAR-022 | 5 |
| Workflow Logic Gap | SCAR-016, SCAR-017, SCAR-018, SCAR-019, SCAR-020 | 5 |
| Security / Input Validation | SCAR-027, SCAR-028, SCAR-029 | 3 |
| Concurrency / Race Condition | SCAR-002, SCAR-010, SCAR-010b | 3 |
| Integration Failure / CI | SCAR-021, SCAR-026 | 2 |
| Authentication / Authorization | SCAR-012, Env Var Naming | 2 |
| Entity Resolution / Collision | SCAR-001 | 1 |
| Performance Cliff / Timeout | SCAR-015 | 1 |

10 categories, 31+ named scars. Categories searched but not found: schema migration failure, distributed coordination failures.

## Defensive Pattern Documentation

Key defensive patterns by scar cluster:

**Cascade Defense-in-Depth (SCAR-005/006/023)**:
- `parent_gid` in BASE_SCHEMA for hierarchy reconstruction
- `WarmupOrderingError` (BROAD-CATCH immune) in `src/autom8_asana/dataframes/cascade_utils.py:22`
- Post-build null rate audit: WARN 5%, ERROR 20% in `src/autom8_asana/dataframes/builders/cascade_validator.py:30-31`
- Gap-skipping chain traversal in `src/autom8_asana/dataframes/views/cascade_view.py:356`
- All cascade columns require explicit `source="cascade:..."` annotation

**Session Thread Safety (SCAR-010/010b)**:
- `threading.RLock()` protecting all state transitions
- `_require_open()` context manager replaces all bare state checks
- `_ensure_open()` deleted (zero callers)

**Health Check Separation (SCAR-011/011b)**:
- `/health` always 200 (liveness); `/health/ready` gates on cache + workflow registration
- `_workflow_configs_registered` flag parallels `_cache_ready` pattern

**Security Hardening (SCAR-027/028/029)**:
- Lambda replacement in `re.sub` for user-controlled strings
- `mask_pii_in_string()` on all error log sites with user data
- `str.strip()` GID guard before Pydantic normalization

## Agent-Relevance Tags

| Scar | Relevant Roles | Why |
|---|---|---|
| SCAR-001 | principal-engineer, architect | New entity/holder classes must follow `PRIMARY_PROJECT_GID` pattern |
| SCAR-005/006 | principal-engineer | New cascade columns must be in BASE_SCHEMA and persisted to parquet |
| SCAR-009 | principal-engineer, qa-adversary | Tests must set `ASANA_WORKSPACE_GID`; never rely on sync auto-detect |
| SCAR-010/010b | principal-engineer | All SaveSession state access through lock; no unlocked state |
| SCAR-011 | platform-engineer | ECS health checks must target `/health`, not `/health/ready` |
| SCAR-012 | principal-engineer | New cross-service clients must use `ServiceTokenAuthProvider` |
| SCAR-013 | principal-engineer | Optional SDK imports must use `try/except ImportError` |
| SCAR-014 | principal-engineer | Lifecycle config models must remain forward-compatible |
| SCAR-015 | architect | I/O-heavy data must be pre-computed at warm-up |
| SCAR-023 | principal-engineer | `source=None` silently bypasses cascade pipeline |
| SCAR-026 | qa-adversary | MagicMock accepts any attribute; use `spec=` |
| SCAR-027 | principal-engineer | Never use user-controlled strings as `re.sub` replacement |
| SCAR-028 | principal-engineer | All error log sites must use `mask_pii_in_string()` |
| SCAR-S3-LOOP | platform-engineer | Permanent failure latches prevent self-healing; use CB HALF_OPEN |

## Knowledge Gaps

1. **SCAR-004 and SCAR-008 missing isolation tests**: Two impactful scars have no dedicated regression tests; rely on implicit coverage.
2. **SCAR-013 import-fallback unit test**: No test exercises the `_SCHEMA_VERSIONING_AVAILABLE = False` path.
3. **SCAR-026 mock-spec coverage**: No systematic audit confirms all workflow test mocks use `spec=`.
4. **BROAD-CATCH audit**: 30+ labeled exception handlers; no centralized audit confirms all degradation paths produce observable signals.
5. **PII masking completeness**: No systematic audit confirms ALL log sites that could emit user data are covered.
6. **Classifier drift risk**: SCAR-030 fixed by manual verification. No automated test validates section names against live Asana API.
7. **SM-001 through SM-008 refactoring scars**: Code hygiene fixes not expanded here -- not production failures.
