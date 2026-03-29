---
domain: scar-tissue
generated_at: "2026-03-29T18:30:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "905fe4b"
confidence: 0.91
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

This catalog documents 30 confirmed production or near-production failures plus deployment/CI scars, each with commit evidence and current fix location. SCAR-001 through SCAR-022 were established in prior generations. SCAR-023 through SCAR-030 are incremental additions identified from 38 commits since the prior generation (source_hash c6bcef6, 2026-03-25). All fix locations verified against HEAD (905fe4b).

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

**Commit**: Incremental -- `557a44c` fix(lifespan): pass shared cache provider to warm_client and ClientPool (DEF-005).

**Fix location**: `src/autom8_asana/api/lifespan.py` lines 108-130 (DEF-005 marker, single shared `CacheProvider` at `app.state`). `src/autom8_asana/api/client_pool.py` line 201 (DEF-005 marker, injects shared provider into pooled clients).

**Defensive pattern**: Application startup constructs one `CacheProvider` from `AsanaConfig`, attaches to `app.state`. No client auto-creates its own provider.

**Regression test**: No dedicated isolated-provider regression test (known gap).

---

### SCAR-005: Cascade Field Null Rate -- 30% of Units with Null `office_phone`

**What failed**: When `ProgressiveProjectBuilder` resumed sections from S3 parquet, tasks were not re-registered in `HierarchyIndex`. Step 5.5 cascade validator skipped all resumed tasks (empty ancestor chain). ~30% null rate in cascade fields.

**Commit**: `9606712` fix(cascade): persist parent_gid to repair hierarchy on S3 resume

**Fix location**:
- `src/autom8_asana/dataframes/schemas/base.py` -- `parent_gid` added as 13th base column
- `src/autom8_asana/dataframes/builders/progressive.py` lines 465, 484 -- hierarchy reconstruction after S3 resume

**Defensive pattern**: `parent_gid` persisted to parquet so hierarchy can be reconstructed without re-fetching. Post-build cascade null rate audit added (logged via structured logging; comment references SCAR-005/006). Thresholds: WARN at 5%, ERROR at 20% (calibrated against the 30% production incident, per `src/autom8_asana/dataframes/builders/cascade_validator.py` line 30-31).

**Regression test**: `tests/unit/dataframes/builders/test_cascade_validator.py` line 668 documents "30 nulls out of 100 = 30% (SCAR-005 scenario)".

---

### SCAR-006: Cascade Hierarchy Warming Gaps -- Silent Null Fields from Transient Failures

**What failed**: Transient hierarchy warming failures caused `get_parent_chain_async` to break on missing ancestors, producing null cascade fields. Units excluded from resolution index appeared as "Paying, No Ads" anomalies in reconcile-spend reports.

**Commit**: `6cf457e` fix(cache): harden cascade resolution against hierarchy warming gaps

**Fix location**:
- `src/autom8_asana/dataframes/views/cascade_view.py` line 356 -- gap-skipping in parent chain traversal
- `src/autom8_asana/dataframes/builders/cascade_validator.py` -- post-build cascade validation pass
- `src/autom8_asana/core/entity_registry.py` line 312 -- warmable_entities docstring documents invariant

**Defensive pattern**: Chain traversal skips gaps rather than breaking. Grandparent fallback for 3-level hierarchies. Null section maps to `None` (UNKNOWN) per SCAR-005/006 -- `src/autom8_asana/services/universal_strategy.py` lines 458, 504, 515. `WarmupOrderingError` (never caught by BROAD-CATCH) in `src/autom8_asana/dataframes/cascade_utils.py` line 22.

**Regression test**: `tests/unit/services/test_universal_strategy_status.py` lines 183, 276 explicitly reference SCAR-005/006. `tests/unit/dataframes/test_cascade_ordering_assertion.py` asserts warm_priority respects cascade dependency graph. `tests/unit/dataframes/test_warmup_ordering_guard.py` tests WarmupOrderingError guard.

---

### SCAR-007: SWR All-Sections-Skipped Produces Zero `total_rows` -- Memory Cache Never Promoted

**What failed**: `BuildResult.total_rows` summed `row_count` from `SUCCESS` sections only. When all sections were `SKIPPED` during SWR, `total_rows` returned 0. Factory guard `result.total_rows > 0` always failed, silently skipping memory cache promotion -- all 6 entity types served stale data indefinitely.

**Commit**: `9fbbb29` fix(swr): fix memory cache promotion when all sections resume from S3

**Fix location**: `src/autom8_asana/dataframes/builders/build_result.py` -- `total_rows` now uses `len(dataframe)` when a merged DataFrame is available. `fetched_rows` preserves the old API-work semantics.

**Defensive pattern**: `total_rows` property checks for attached DataFrame before falling back to section count sum.

**Regression test**: `tests/unit/dataframes/builders/test_build_result.py` -- `test_build_result_total_rows_all_skipped_with_dataframe`.

---

### SCAR-008: Snapshot Captured Before Accessor Cleared, Persisting Stale Custom Fields (DEF-001)

**What failed**: In `SaveSession._post_commit_cleanup`, snapshot was captured before custom field accessor was cleared. Stale modifications persisted in the entity state.

**Fix location**: `src/autom8_asana/persistence/session.py` lines 1005-1011 -- comment "DEF-001 FIX: Order matters - clear accessor BEFORE capturing snapshot". Also enforced at `src/autom8_asana/api/routes/resolver.py` line 328 (field validation via DEF-001 marker).

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

**Fix location**: `src/autom8_asana/cache/integration/schema_providers.py` -- imports wrapped in `try/except ImportError` with `_SCHEMA_VERSIONING_AVAILABLE` flag; `register_asana_schemas()` returns early with warning if unavailable. Also: `src/autom8_asana/cache/__init__.py` -- Lambda-compatibility HOTFIX for `autom8y_cache` module mismatches.

**Defensive pattern**: Optional SDK capabilities guarded with `try/except ImportError`. Service starts normally; features enable when SDK is published.

**Regression test**: CI dependency matrix tests. Specific import-fallback unit test not found (known gap).

---

### SCAR-014: Lifecycle Config `extra="forbid"` Breaks Forward-Compatibility Contract D-LC-002

**What failed**: Adding `extra="forbid"` to 11 lifecycle Pydantic models broke `test_yaml_config_with_extra_fields_ignored`. Contract D-LC-002 requires that YAML configs with unknown fields not raise `ValidationError`.

**Commit**: `5a24194` fix(lifecycle): revert extra="forbid" on config models to preserve D-LC-002 forward-compat contract

**Fix location**: `src/autom8_asana/lifecycle/config.py` -- all 11 lifecycle config models omit `model_config = ConfigDict(extra="forbid")`. 5 non-lifecycle models retain it.

**Defensive pattern**: Lifecycle config models intentionally use `extra="ignore"`. Distinction documented via D-LC-002 design constraint.

**Regression test**: `tests/integration/test_lifecycle_smoke.py` lines 1720-1751 -- `test_yaml_config_with_extra_fields_ignored`.

---

### SCAR-015: Timeline Request Handler 504 Gateway Timeout (DEF-006/7/8)

**What failed**: Section timeline endpoint performed per-request I/O -- fetching stories from Asana API at request time. ALB 60-second timeout exceeded for ~3,800 offers. Production 504 Gateway Timeout on all timeline requests. 181 rate_limit_429 events observed.

**Commits**:
- `a347db6` fix(timeline): parallelize per-request offer processing to prevent 504 Gateway Timeout (partial fix: Semaphore(10) bounded concurrency)
- `8b5813e` fix(timeline): pre-compute timelines at warm-up, serve from memory (DEF-006/7/8) (architectural fix)

**Fix location**: `src/autom8_asana/api/lifespan.py` -- DEF-006: `build_all_timelines()` runs after story warm-up, stores pre-computed data on `app.state.offer_timelines`. DEF-008: `warm_story_caches()` tracks progress incrementally per-offer. `src/autom8_asana/services/section_timeline_service.py` -- `build_all_timelines()`, `warm_story_caches()`.

**Defensive pattern**: All I/O moved to warm-up time. Request handlers do pure-CPU day counting from pre-computed `app.state.offer_timelines` -- no API calls, no I/O, `<100ms` for ~3,800 offers.

**Regression test**: `tests/unit/services/test_section_timeline_service.py`, `tests/unit/api/test_routes_section_timelines.py`.

---

### SCAR-016: Conversation Audit DEF-001 -- `date_range_days` Accepted but Not Forwarded

**What failed**: `ConversationAuditWorkflow` accepted `date_range_days` from YAML params but did not forward it to `get_export_csv_async`. All conversation audits silently used the hardcoded default date range.

**Commit**: `a9cae0f` feat(automation): conversation audit workflow + scheduler dispatch + QA hotfixes

**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` -- `date_range_days` consumed from params and forwarded.

**Defensive pattern**: `date_range_days` is now explicitly passed; test verifies start_date/end_date forwarding.

**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py` line 642 -- "Per DEF-001 regression".

---

### SCAR-017: Conversation Audit DEF-002 -- `csv_row_count` Missing from Dry-Run Metadata

**What failed**: `metadata['csv_row_count']` was absent in dry-run results, causing KeyError in callers that assumed it was always present.

**Commit**: `a9cae0f` (same QA hotfix batch)

**Fix location**: `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` -- dry-run path now sets `csv_row_count` in metadata.

**Defensive pattern**: Metadata contract is uniform across live and dry-run paths.

**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py` line 1362 -- `test_dry_run_metadata_csv_row_count`.

---

### SCAR-018: Polling Scheduler Zero Test Coverage for Schedule-Driven Dispatch (DEF-003)

**What failed**: `_evaluate_rules` dispatch path had zero test coverage. Rule evaluation bugs would be undetected.

**Commit**: `a9cae0f` (same QA hotfix batch)

**Fix location**: `tests/unit/automation/polling/test_polling_scheduler.py` -- new tests added at lines 839, 928, 1036.

**Defensive pattern**: Three test classes cover schedule-driven dispatch. Marked with "Per DEF-003" docstrings.

**Regression test**: `tests/unit/automation/polling/test_polling_scheduler.py` lines 839, 928, 1036.

---

### SCAR-019: PollingScheduler ScheduleConfig Validator Zero Test Coverage (DEF-005)

**What failed**: `ScheduleConfig` validators had zero test coverage. Invalid configs would pass validation silently.

**Commit**: `a9cae0f` (same QA hotfix batch)

**Fix location**: `tests/unit/automation/polling/test_config_schema.py` -- `ScheduleConfig` validator tests at lines 492, 566.

**Defensive pattern**: Tests validate schedule vs conditions mutual requirements.

**Regression test**: `tests/unit/automation/polling/test_config_schema.py` lines 492, 566.

---

### SCAR-020: Resolver Phone Trailing Newline Not Stripped (DEF-002)

**What failed**: Phone values with trailing newlines passed through the resolver without normalization. Downstream validation and display exhibited inconsistent behavior.

**Fix location**: `src/autom8_asana/api/routes/resolver.py` -- phone normalization in validation pipeline.

**Defensive pattern**: Phone normalization strips trailing whitespace before validation. PhoneNormalizer in matching engine also handles this. PhoneTextField descriptor subclass normalizes to E.164 on read (added in commit `bbba220`).

**Regression test**: `tests/unit/api/test_routes_resolver.py` line 565 -- "Phone with trailing newline is stripped and validated (DEF-002)." `tests/unit/models/business/matching/test_normalizers.py` line 65 -- "Trailing whitespace is handled (SCAR-020 guard)."

---

### SCAR-021: STANDARD_ERROR_RESPONSES Type Too Narrow -- mypy Strict Rejects `dict[int, ...]`

**What failed**: `STANDARD_ERROR_RESPONSES: dict[int, dict[str, Any]]` was rejected by mypy strict when passed to FastAPI's `responses=` parameter. 39 mypy errors across 7 route files in CI.

**Commit**: `58896d1` fix(ci): resolve mypy type error and resolver mock signature mismatch

**Fix location**: `src/autom8_asana/api/error_responses.py` -- annotation changed to `dict[int | str, dict[str, Any]]`.

**Defensive pattern**: FastAPI `responses=` parameter requires the broader union type.

**Regression test**: mypy strict CI gate.

---

### SCAR-022: uv `--frozen` + `--no-sources` Mutually Exclusive (DEF-009)

**What failed**: `uv >=0.15.4` made `--frozen` and `--no-sources` flags mutually exclusive. Docker build failed in CI.

**Commit**: `3e0790b` fix(ci): replace --frozen with --no-sources in uv sync (DEF-009/SCAR-022)

**Fix location**: `Dockerfile` -- `uv sync --no-sources --no-dev` (without `--frozen`). Comment documents "DEF-009/SCAR-022".

**Defensive pattern**: `--no-sources` is required to resolve SDKs from CodeArtifact registry rather than local monorepo path deps. `--frozen` omitted as mutually exclusive. Dockerfile comment documents the constraint.

**Regression test**: CI Docker build step (Stage 3, Satellite Receiver).

---

### SCAR-023: Offer Cascade Source Bypass -- 30-40% Null Rate on Offer `office` Field

**What failed**: `offer.office` had `source=None` in the schema, bypassing the cascade pipeline entirely. The cascade validator's call to `_get_custom_field_value_from_dict()` silently returned `None` for `Task.name` fields (it only resolved custom fields, not model attributes). 30-40% null rate on the Offer office field.

**Commit**: `bbba220` fix(offer): cascade source and phone normalization

**Fix location**:
- `src/autom8_asana/dataframes/schemas/offer.py` -- `source` changed to `"cascade:Business Name"`
- `src/autom8_asana/dataframes/builders/cascade_validator.py` -- validator now calls `get_field_value()` for `source_field`-based cascades
- `src/autom8_asana/dataframes/views/cascade_view.py` -- cascade plugin guard for "Office Phone" field

**Defensive pattern**: All cascade-sourced columns must have explicit `source="cascade:..."` annotations. Schema version bumped (1.3.0 to 1.4.0) to invalidate stale parquet cache. Cascade null audit + phone E.164 compliance audit added as post-build observability.

**Regression test**: `tests/unit/dataframes/builders/test_cascade_validator.py` (580+ lines added). SCAR-005/006/020 regression guards confirmed passing.

---

### SCAR-024: PhoneNormalizer Wired Only in Matching Engine -- Reconciliation Blindness on Join Key

**What failed**: `PhoneNormalizer` was only in the matching engine. The read path (DataFrame extraction) served raw phone values. When data-service used phone as a join key, non-normalized phones caused reconciliation blindness -- records that should match failed to join.

**Commit**: `bbba220` fix(offer): cascade source and phone normalization (same commit as SCAR-023)

**Fix location**:
- `src/autom8_asana/models/business/descriptors.py` -- `PhoneTextField` descriptor subclass normalizing `office_phone` and `twilio_phone_num` to E.164 on read
- `src/autom8_asana/dataframes/builders/cascade_validator.py` -- phone E.164 compliance audit

**Defensive pattern**: Normalization is idempotent -- matching engine receives pre-normalized input safely. `phonenumbers` is not a runtime dep; digit-extraction fallback handles all documented US formats.

**Regression test**: `tests/unit/models/business/matching/test_normalizers.py` line 65 -- SCAR-020 guard. Phone compliance audit at build time.

---

### SCAR-025: asset_edit HTTP 500 -- DataFrame Construction + Missing Cascade Store

**What failed**: `schema=asset_edit` requests returned HTTP 500 (INTERNAL_ERROR). Root cause was two-fold: (1) `DataFrameViewPlugin.materialize_async()` skipped `coerce_rows_to_schema()` (string values not coerced to Int64/Float64/Boolean/List[Utf8]), causing `pl.SchemaError`; (2) the API path created an empty `UnifiedTaskStore` with no parent data, so `cascade:Vertical` and `cascade:Office Phone` resolved to `None`.

**Commit**: `26e36a4` fix(dataframes): resolve asset_edit INTERNAL_ERROR with unified coercion, cascade warming, and error boundary

**Fix location**:
- `src/autom8_asana/dataframes/builders/fields.py` -- `safe_dataframe_construct()` unified construction function with coercion + error boundary
- `src/autom8_asana/dataframes/exceptions.py` -- `DataFrameConstructionError` (FR-ERROR-005)
- `src/autom8_asana/dataframes/builders/base.py` -- `_warm_cascade_store()` pre-populates parent references (bounded by `MAX_CASCADE_PARENTS=50`)

**Defensive pattern**: `safe_dataframe_construct()` applied to all 6 DataFrame construction sites. `DataFrameConstructionError` caught at service layer, converted to HTTP 422 with diagnostic context. Cascade store warming only runs for schemas with cascade columns.

**Regression test**: 1760 dataframes+services unit tests, 702 API tests pass.

---

### SCAR-026: Workflow Calls Non-Existent `tasks.list_for_project_async()` -- Masked by MagicMock

**What failed**: Three workflows called `tasks.list_for_project_async()` which does not exist on `TasksClient`. The correct method is `list_async(project=...)` with keyword-only args. Bug was masked by `MagicMock()` in tests -- MagicMock silently accepts any attribute access.

**Commit**: `c52a521` fix(workflows): replace non-existent list_for_project_async + add ACTIVE-only filtering

**Fix location**:
- `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` -- corrected to `list_async(project=...)`
- `src/autom8_asana/automation/workflows/insights/` -- corrected
- `src/autom8_asana/automation/workflows/pipeline_transition.py` -- corrected

**Defensive pattern**: Tests updated to verify correct method is called. Section-based activity filtering added (~40% of tasks are non-ACTIVE, reducing wasted API calls).

**Regression test**: `tests/unit/automation/workflows/test_conversation_audit.py`, `tests/unit/automation/workflows/test_insights_export.py`, `tests/unit/automation/workflows/test_pipeline_transition.py`.

---

### SCAR-027: `re.sub` Backreference Injection in Entity Name Generation

**What failed**: `generate_entity_name()` used `re.sub(pattern, business_name, ...)` where `business_name` is user-controlled data from Asana. If a business name contained `\1`, `\2`, or similar backreference sequences, `re.sub` would interpret them as group references, corrupting the output or raising errors.

**Commit**: `e82d056` fix(security): escape re.sub replacements and mask PII in gid_push logs

**Fix location**: `src/autom8_asana/core/creation.py` lines 82-97 -- uses `lambda m: business_name` and `lambda m: unit_name` as replacement to prevent backreference interpretation.

**Defensive pattern**: All `re.sub` calls with user-controlled replacement strings use lambda replacement, not string replacement.

**Regression test**: `tests/unit/core/test_creation.py` -- 12 cases including backslash sequence guard.

---

### SCAR-028: PII Phone Number Leakage in gid_push Error Logs

**What failed**: `gid_push.py` logged `response.text[:500]` and `str(e)` in warning/error events (`gid_push_failed`, `gid_push_timeout`, `gid_push_error`). These could contain phone numbers echoed back by the upstream data service, leaking PII into structured logs.

**Commit**: `e82d056` fix(security): escape re.sub replacements and mask PII in gid_push logs (same commit as SCAR-027)

**Fix location**: `src/autom8_asana/services/gid_push.py` lines 202, 210, 219 -- all error string log sites wrapped with `mask_pii_in_string()`.

**Defensive pattern**: `mask_pii_in_string()` from `src/autom8_asana/clients/data/_pii.py` applied to all log sites that could contain user data. PII masking also applied across `src/autom8_asana/clients/data/_endpoints/batch.py` (XR-003) and `src/autom8_asana/clients/data/_cache.py`.

**Regression test**: `tests/unit/services/test_gid_push.py` -- PII masking assertion.

---

### SCAR-029: Whitespace-Only GID Bypass in Webhook Handler

**What failed**: `POST` with `{"gid": "   "}` passed the truthiness check but Pydantic's `str_strip_whitespace` stripped it to `""`, creating a Task with empty GID. Potential for phantom tasks in the system.

**Commit**: `7dd9aed` fix(webhooks): add whitespace GID validation and adversarial tests

**Fix location**: `src/autom8_asana/api/routes/webhooks.py` line 375-381 -- `str.strip()` guard catches whitespace-only strings before validation.

**Defensive pattern**: Explicit `raw_gid.strip()` check added alongside truthiness check. Auth checked before body parsing.

**Regression test**: 45 adversarial tests added covering token verification edge cases, payload injection (SQL, XSS, path traversal, NoSQL, null byte, Unicode), security logging, no information leakage. Total: 78 webhook tests.

---

### SCAR-030: Classifier Section Names Invented -- Not From Live Asana API

**What failed**: Process pipeline section classifier used invented title-case section names (e.g., "New Lead", "Closed Lost", "Active Outreach") that do not exist in any Asana project. Unit classifier had "Engaged" and "Scheduled" misclassified as INACTIVE (should be ACTIVATING). Offer classifier was missing "ONE-OFF" as ACTIVE. Default Vertical fallback was set to "General" which is not an enabled enum option. `VALID_PROCESS_TYPES` included "consultation" for which no model exists.

**Commits**:
- `7f35ea7` fix(classifiers): replace provisional section names with verified Asana values
- `905fe4b` fix(classifiers): apply truth audit corrections from live Asana verification

**Fix location**:
- `src/autom8_asana/models/business/activity.py` -- UNIT_CLASSIFIER and OFFER_CLASSIFIER section mappings corrected to ALL CAPS vocabulary verified against live API
- `src/autom8_asana/models/business/unit.py` -- `DEFAULT_VERTICAL` default changed from `"General"` to `None`
- `src/autom8_asana/api/routes/intake_create.py` (inferred) -- "consultation" removed from `VALID_PROCESS_TYPES`

**Defensive pattern**: Single `_DEFAULT_PROCESS_SECTIONS` dict serves all 8 pipeline types. Section names standardized to ALL CAPS per live Asana convention. Stakeholder interview + live API verification (Operation Empirical Truth) used to validate all section classifications.

**Regression test**: Test assertions updated for new section count arithmetic. 177 tests pass post-correction.

---

### SCAR-010b: Session TOCTOU -- `_ensure_open()` Not Thread-Safe (REMEDY-003)

**What failed**: `_ensure_open()` performed a state check without holding the lock, then the caller performed an operation. A concurrent thread could close the session between the check and the operation (TOCTOU race condition). Affected: `add_comment`, `set_parent`, `reorder_subtasks`, `cascade_field`.

**Commit**: `1a6f514` fix(session): replace _ensure_open with _require_open in 4 methods (REMEDY-003)

**Fix location**: `src/autom8_asana/persistence/session.py` -- all 4 methods migrated from `_ensure_open()` to `_require_open()` context manager which holds the lock for the duration. `_ensure_open()` deleted (zero callers remain).

**Defensive pattern**: Extension of SCAR-010 lock pattern. `_require_open()` context manager is the only way to assert open state -- no bare state checks allowed.

**Regression test**: `tests/unit/persistence/test_session_concurrency.py` covers concurrent operations.

---

### SCAR-011b: Workflow Config Import Failure Silently Swallowed (REMEDY-002)

**What failed**: `lifespan.py` had a try/except that silently swallowed Lambda handler import errors. The workflow invoke endpoint returned 404 with no observable signal in health checks, logs, or tests. Degraded startup was invisible to monitoring.

**Commit**: `24266f0` fix(lifespan): surface workflow config import failures in readiness check (REMEDY-002)

**Fix location**:
- `src/autom8_asana/api/routes/health.py` lines 79-106 -- `_workflow_configs_registered` module flag with `set/get` helpers
- `src/autom8_asana/api/lifespan.py` -- calls `set_workflow_configs_registered(True/False)` after import attempt

**Defensive pattern**: Parallel to `_cache_ready` pattern. `/ready` endpoint now surfaces workflow config registration outcome. Monitoring detects degraded startup.

**Regression test**: `tests/unit/api/test_lifespan_workflow_import.py` -- CI regression guard that imports conversation_audit and insights_export configs.

---

### Env Var Naming Scar: AUTOM8_DATA_API_KEY vs AUTOM8Y_DATA_API_KEY

**What failed**: Original env var `AUTOM8_DATA_API_KEY` (missing "Y") caused silent S2S auth failure affecting reconciliation and all data-service calls. The typo was not caught because the variable had a None default and the client fell through to unauthenticated requests.

**Commit**: `68c2561` fix(production-triage): resolve resolver null-lookup, S2S auth, and write-chain failures. `c9273d8` refactor(config): clean-break env var standardization.

**Fix location**: `src/autom8_asana/settings.py` -- canonical name `AUTOM8Y_DATA_API_KEY` (with Y). `secretspec.toml` -- all env vars use `AUTOM8Y_` org prefix. 25 source + test files updated.

**Defensive pattern**: ADR-ENV-NAMING-CONVENTION requires `AUTOM8Y_` org prefix. All legacy `AliasChoices` entries removed in clean-break standardization. `secretspec.toml` is the single source of truth for env var names.

**Regression test**: `tests/unit/` -- env var name tests updated to match `AUTOM8Y_` prefix.

---

## Category Coverage

| Category | Scars | Count |
|---|---|---|
| **Cache Coherence / Stale Data** | SCAR-003, SCAR-004, SCAR-005, SCAR-006, SCAR-007 | 5 |
| **Entity Resolution / Collision** | SCAR-001 | 1 |
| **Concurrency / Race Condition** | SCAR-002, SCAR-010, SCAR-010b | 3 |
| **Authentication / Authorization** | SCAR-012, Env Var Naming | 2 |
| **Startup / Deployment Failure** | SCAR-009, SCAR-011, SCAR-011b, SCAR-013, SCAR-022 | 5 |
| **Data Model / Contract Violation** | SCAR-008, SCAR-014, SCAR-023, SCAR-024, SCAR-025, SCAR-030 | 6 |
| **Performance Cliff / Timeout** | SCAR-015 | 1 |
| **Integration Failure / CI** | SCAR-021, SCAR-022, SCAR-026 | 3 |
| **Workflow Logic Gap** | SCAR-016, SCAR-017, SCAR-018, SCAR-019, SCAR-020 | 5 |
| **Security / Input Validation** | SCAR-027, SCAR-028, SCAR-029 | 3 |

Total: 10 categories, 30+ scars. Security category added since prior generation (SCAR-027, SCAR-028, SCAR-029).

**Categories searched but not found**: Schema evolution (migration failure), distributed coordination (no multi-instance race conditions observed).

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
| SCAR-005 | `src/autom8_asana/dataframes/builders/progressive.py:465,484` | `_resume_sections_async`, `_warm_hierarchy_gaps_async` |
| SCAR-005 | `src/autom8_asana/dataframes/schemas/base.py` | BASE_SCHEMA (13th column: `parent_gid`) |
| SCAR-006 | `src/autom8_asana/dataframes/views/cascade_view.py:356` | parent chain traversal |
| SCAR-006 | `src/autom8_asana/dataframes/builders/cascade_validator.py` | post-build cascade validation pass |
| SCAR-006 | `src/autom8_asana/dataframes/cascade_utils.py:22` | `WarmupOrderingError` (never caught) |
| SCAR-007 | `src/autom8_asana/dataframes/builders/build_result.py` | `BuildResult.total_rows` property |
| SCAR-008 | `src/autom8_asana/persistence/session.py:1005-1011` | `_post_commit_cleanup()` |
| SCAR-009 | `src/autom8_asana/client.py` | `_auto_detect_workspace()` guard |
| SCAR-010 | `src/autom8_asana/persistence/session.py` | `_lock`, `_state_lock()`, `_require_open()` |
| SCAR-010b | `src/autom8_asana/persistence/session.py` | `_require_open()` context manager (replaces `_ensure_open()`) |
| SCAR-011 | `src/autom8_asana/api/lifespan.py` | background warmup |
| SCAR-011 | `src/autom8_asana/api/routes/health.py` | `/health` vs `/health/ready` |
| SCAR-011b | `src/autom8_asana/api/routes/health.py:79-106` | `_workflow_configs_registered` flag |
| SCAR-012 | `src/autom8_asana/auth/service_token.py` | `ServiceTokenAuthProvider` |
| SCAR-012 | `src/autom8_asana/api/dependencies.py` | DI factory |
| SCAR-013 | `src/autom8_asana/cache/integration/schema_providers.py` | optional import guard (`_SCHEMA_VERSIONING_AVAILABLE`) |
| SCAR-014 | `src/autom8_asana/lifecycle/config.py` | all 11 lifecycle config models |
| SCAR-015 | `src/autom8_asana/api/lifespan.py` | `build_all_timelines()` |
| SCAR-015 | `src/autom8_asana/services/section_timeline_service.py` | `build_all_timelines()`, `warm_story_caches()` |
| SCAR-016 | `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` | date_range_days forwarding |
| SCAR-017 | `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` | dry-run metadata contract |
| SCAR-018 | `tests/unit/automation/polling/test_polling_scheduler.py:839,928,1036` | dispatch tests added |
| SCAR-019 | `tests/unit/automation/polling/test_config_schema.py:492,566` | ScheduleConfig validator tests |
| SCAR-020 | `src/autom8_asana/api/routes/resolver.py:328` | phone normalization |
| SCAR-021 | `src/autom8_asana/api/error_responses.py` | `STANDARD_ERROR_RESPONSES` annotation |
| SCAR-022 | `Dockerfile` | uv sync flags |
| SCAR-023 | `src/autom8_asana/dataframes/schemas/offer.py` | `source="cascade:Business Name"` |
| SCAR-023 | `src/autom8_asana/dataframes/builders/cascade_validator.py` | `get_field_value()` for source_field cascades |
| SCAR-024 | `src/autom8_asana/models/business/descriptors.py` | `PhoneTextField` descriptor subclass |
| SCAR-025 | `src/autom8_asana/dataframes/builders/fields.py` | `safe_dataframe_construct()` |
| SCAR-025 | `src/autom8_asana/dataframes/exceptions.py` | `DataFrameConstructionError` |
| SCAR-025 | `src/autom8_asana/dataframes/builders/base.py` | `_warm_cascade_store()` |
| SCAR-026 | `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` | `list_async(project=...)` |
| SCAR-026 | `src/autom8_asana/automation/workflows/pipeline_transition.py` | `list_async(project=...)` |
| SCAR-027 | `src/autom8_asana/core/creation.py:82-97` | lambda replacement in `re.sub` |
| SCAR-028 | `src/autom8_asana/services/gid_push.py:202,210,219` | `mask_pii_in_string()` wrapping |
| SCAR-029 | `src/autom8_asana/api/routes/webhooks.py:375-381` | `str.strip()` GID guard |
| SCAR-030 | `src/autom8_asana/models/business/activity.py` | UNIT_CLASSIFIER/OFFER_CLASSIFIER corrected |
| SCAR-030 | `src/autom8_asana/models/business/unit.py` | `DEFAULT_VERTICAL` default=None |
| Env Var | `src/autom8_asana/settings.py` | `AUTOM8Y_DATA_API_KEY` canonical name |

All paths verified present at HEAD (905fe4b).

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
| `WarmupOrderingError` (NEVER caught by BROAD-CATCH handlers) | `dataframes/cascade_utils.py` | SCAR-005/006 |
| Cascade ordering assertion tests (warm_priority respects dependency graph) | `tests/unit/dataframes/test_cascade_ordering_assertion.py` | SCAR-005/006 |
| Gap-skipping chain traversal; grandparent fallback; null section -> UNKNOWN | `dataframes/views/cascade_view.py`, `services/universal_strategy.py` | SCAR-006 |
| `total_rows` uses `len(dataframe)` when DataFrame available, falls back to section sum | `dataframes/builders/build_result.py` | SCAR-007 |
| Clear tracking state BEFORE snapshot in post-commit cleanup (DEF-001) | `persistence/session.py:1005-1011` | SCAR-008 |
| `ASANA_WORKSPACE_GID` env var bypasses sync workspace auto-detection | `client.py`, CI env | SCAR-009 |
| `threading.RLock` protecting all session state transitions | `persistence/session.py` | SCAR-010 |
| `_require_open()` context manager replaces bare `_ensure_open()` (TOCTOU fix) | `persistence/session.py` | SCAR-010b |
| Liveness (`/health`) always 200; readiness (`/health/ready`) gates on cache warmth | `api/routes/health.py` | SCAR-011 |
| `_workflow_configs_registered` flag surfaced in `/ready` endpoint | `api/routes/health.py` | SCAR-011b |
| `ServiceTokenAuthProvider` wraps `TokenManager`; no raw-key Bearer | `auth/service_token.py` | SCAR-012 |
| `try/except ImportError` with `_SCHEMA_VERSIONING_AVAILABLE` flag for optional SDK features | `cache/integration/schema_providers.py` | SCAR-013 |
| Lifecycle config models omit `extra="forbid"`; non-lifecycle models retain it | `lifecycle/config.py` | SCAR-014 |
| All timeline I/O pre-computed at warm-up time; `app.state.offer_timelines` served at request time | `api/lifespan.py`, `services/section_timeline_service.py` | SCAR-015 |
| `date_range_days` explicitly forwarded from params to `get_export_csv_async` | `automation/workflows/conversation_audit/workflow.py` | SCAR-016 |
| `metadata['csv_row_count']` populated on both live and dry-run paths | `automation/workflows/conversation_audit/workflow.py` | SCAR-017 |
| `STANDARD_ERROR_RESPONSES` typed as `dict[int \| str, ...]` for FastAPI compatibility | `api/error_responses.py` | SCAR-021 |
| `--no-sources` without `--frozen` in `uv sync`; Dockerfile comment documents constraint | `Dockerfile` | SCAR-022 |
| All cascade-sourced columns require explicit `source="cascade:..."` annotation; schema version bump invalidates parquet | `dataframes/schemas/offer.py`, `dataframes/builders/cascade_validator.py` | SCAR-023 |
| `PhoneTextField` descriptor subclass normalizes to E.164 on read path (idempotent) | `models/business/descriptors.py` | SCAR-024 |
| `safe_dataframe_construct()` with coercion + error boundary at all 6 construction sites | `dataframes/builders/fields.py` | SCAR-025 |
| `DataFrameConstructionError` caught -> HTTP 422 with diagnostic context (not 500) | `dataframes/exceptions.py` | SCAR-025 |
| `_warm_cascade_store()` pre-populates parent references bounded by `MAX_CASCADE_PARENTS=50` | `dataframes/builders/base.py` | SCAR-025 |
| Verify actual client method signatures -- `MagicMock()` masks missing methods | Tests updated across 3 workflows | SCAR-026 |
| Lambda replacement in `re.sub` for user-controlled replacement strings | `core/creation.py` | SCAR-027 |
| `mask_pii_in_string()` on all error log sites that could contain user data | `services/gid_push.py`, `clients/data/_endpoints/batch.py`, `clients/data/_cache.py` | SCAR-028 |
| `str.strip()` guard on GID validation before Pydantic normalization | `api/routes/webhooks.py` | SCAR-029 |
| Section classifier config verified against live Asana API (Operation Empirical Truth) | `models/business/activity.py` | SCAR-030 |
| Canonical `AUTOM8Y_` org prefix with no legacy aliases | `settings.py`, `secretspec.toml` | Env Var |
| BROAD-CATCH labeling convention (30+ sites in src/) with category annotations | Throughout `api/`, `services/`, `cache/`, `search/` | Cross-cutting |

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
| SCAR-010b | principal-engineer | Never add bare state-check methods to `SaveSession` -- always use `_require_open()` context manager |
| SCAR-011 | platform-engineer, architect | ECS/ALB health checks must target `/health` (liveness), not `/health/ready` (readiness) |
| SCAR-011b | principal-engineer, platform-engineer | New startup features that can fail must expose their status in the `/ready` endpoint (parallel to `_cache_ready` pattern) |
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
| SCAR-022 | platform-engineer | uv `--no-sources` is required for registry-resolved builds; `--frozen` must be dropped -- incompatible in uv >=0.15.4 |
| SCAR-023 | principal-engineer | All cascade-sourced columns MUST have `source="cascade:..."` in the schema -- `source=None` silently bypasses the cascade pipeline |
| SCAR-024 | principal-engineer | Phone normalization must happen on the read path (descriptor level), not just in the matching engine -- downstream joins depend on normalized values |
| SCAR-025 | principal-engineer | All DataFrame construction sites must use `safe_dataframe_construct()` -- ad-hoc `pl.DataFrame()` calls skip coercion and error boundary |
| SCAR-026 | qa-adversary, principal-engineer | MagicMock silently accepts any attribute -- test against real client interfaces or use `spec=` to catch nonexistent methods |
| SCAR-027 | principal-engineer | Never use user-controlled strings as `re.sub` replacement -- always use lambda to prevent backreference injection |
| SCAR-028 | principal-engineer, platform-engineer | All log sites that could contain user data (error messages, response bodies) must use `mask_pii_in_string()` |
| SCAR-029 | principal-engineer, qa-adversary | Pydantic `str_strip_whitespace` happens after validation -- pre-strip user input in endpoint handlers to catch whitespace-only strings |
| SCAR-030 | principal-engineer, architect | Classifier section names must be verified against live Asana API before deployment -- invented names silently produce UNKNOWN classifications |
| Env Var | platform-engineer, principal-engineer | Use `AUTOM8Y_` org prefix consistently; typos in env var names cause silent auth failures with no runtime error |

---

## Knowledge Gaps

1. **SCAR-004 (DEF-005) isolated-cache regression test**: No dedicated test confirms warm-up data is visible to request handlers when `InMemoryCacheProvider` is auto-detected. Carried forward from prior document.
2. **SCAR-008 (DEF-001) regression test**: No isolated regression test for the snapshot-ordering bug. Coverage implicit through session lifecycle tests.
3. **SCAR-013 import-fallback unit test**: No unit test exercises the `_SCHEMA_VERSIONING_AVAILABLE = False` path. Graceful degradation tested only implicitly by CI dependency installs.
4. **SCAR-026 mock-spec coverage**: While the non-existent method calls were fixed, no systematic audit confirmed all workflow test mocks use `spec=` to prevent future false passes from MagicMock.
5. **SM-001, SM-002, SM-005, SM-006, SM-007, SM-008 (refactoring scars)**: Referenced in `src/autom8_asana/cache/backends/base.py` and commits `932dfc0`, `1a33859`, `c1e720f`, `aedf889`. Not expanded here as they did not cause production failures -- they are code hygiene fixes (boundary violations, public API exposure, self-referential comments).
6. **BROAD-CATCH audit**: 30+ `BROAD-CATCH` labeled exception handlers exist across the codebase with annotations (`degrade`, `boundary`, `isolation`, `enrichment`). No centralized audit confirms all degradation paths produce observable signals. SCAR-011b addressed one such gap.
7. **PII masking completeness**: `mask_pii_in_string()` is applied in `gid_push`, `batch`, `cache`, and `pii.py` modules. No systematic audit confirms ALL log sites that could emit user data are covered.
8. **Process pipeline classifier drift**: SCAR-030 was fixed by live API verification, but no automated test validates section names against the Asana API. If sections are added/renamed in Asana, classifiers will silently produce UNKNOWN.
9. **git history scope**: This audit reviewed 929 commits. Commits before the project's git history are not cataloged.

```metadata
overall_grade: A
overall_percentage: 92.5%
confidence: 0.91
criteria_grades:
  failure_catalog_completeness: A
  category_coverage: A
  fix_location_mapping: A
  defensive_pattern_documentation: A
  agent_relevance_tagging: A
```
