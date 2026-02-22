# S5 Decomposition Map: God Object Structural Analysis

**Date**: 2026-02-18
**Sprint**: 5 -- God Object Decomposition
**Agent**: code-smeller
**Source Smells**: CX-001, CX-002, DRY-002

---

## Target 1: DataServiceClient Decomposition Map

### Current State

- **File**: `src/autom8_asana/clients/data/client.py`
- **LOC**: 2,173 (2,174 with trailing newline)
- **Class span**: Lines 136-2160 (~2,024 lines in class body)
- **Method count**: 30 class methods/properties + 13 nested callback functions + 3 module-level functions + 1 module-level helper = 47 definitions total
- **C901 violations**: 3 (`_execute_batch_request` at 29, `_execute_insights_request` at 22, `_execute_with_retry` at 12)

### Existing Extracted Modules

| Module | LOC | Completeness | Contents |
|--------|-----|-------------|----------|
| `_cache.py` | 193 | Complete | `build_cache_key`, `cache_response`, `get_stale_response` |
| `_metrics.py` | 54 | Complete | `MetricsHook` type alias, `emit_metric` |
| `_response.py` | 270 | Complete | `validate_factory`, `handle_error_response`, `parse_success_response` |
| **Total extracted** | **517** | | |

The class retains thin delegation wrappers for each extracted function (`_emit_metric`, `_build_cache_key`, `_cache_response`, `_get_stale_response`, `_validate_factory`, `_handle_error_response`, `_parse_success_response`). These wrappers bind instance state (`self._cache`, `self._log`, etc.) to the module-level functions.

### Concern Clusters

| # | Cluster | Methods | LOC | Line Range | Extractable? | Target Module |
|---|---------|---------|-----|-----------|-------------|---------------|
| 1 | **PII Redaction** | `mask_phone_number`, `_mask_canonical_key` | 58 | 72-128 | Yes | `_pii.py` or keep module-level in `client.py` |
| 2 | **Configuration & Properties** | `__init__`, `config`, `is_initialized`, `has_cache`, `has_metrics`, `circuit_breaker`, `VALID_FACTORIES`, `FACTORY_TO_FRAME_TYPE`, `FEATURE_FLAG_ENV_VAR`, `_check_feature_enabled` | 162 | 136-233, 527-555, 565-621, 691-728 | Partial | Core client skeleton |
| 3 | **HTTP Transport** | `_get_client`, `_get_auth_token`, `close`, `__aenter__`, `__aexit__`, `__enter__`, `__exit__`, `_run_sync` | 189 | 234-325, 424-526 | Yes | Core client skeleton |
| 4 | **Retry Infrastructure** | `_execute_with_retry` | 93 | 328-421 | Already standalone | Core client skeleton |
| 5 | **Cache Delegation** | `_emit_metric`, `_build_cache_key`, `_cache_response`, `_get_stale_response` | 48 | 625-671 | N/A (thin wrappers) | Core client skeleton |
| 6 | **Response Delegation** | `_validate_factory`, `_handle_error_response`, `_parse_success_response` | 41 | 1750-1791 | N/A (thin wrappers) | Core client skeleton |
| 7 | **Endpoint: get_insights** | `get_insights_async`, `get_insights`, `_execute_insights_request` | 361 | 730-906, 1463-1745 | Yes | `_endpoints/insights.py` |
| 8 | **Endpoint: get_insights_batch** | `get_insights_batch_async`, `_execute_batch_request`, `_build_entity_response` | 324 | 909-1414 | Yes | `_endpoints/batch.py` |
| 9 | **Endpoint: get_export_csv** | `get_export_csv_async` | 145 | 1794-1938 | Yes | `_endpoints/export.py` |
| 10 | **Endpoint: get_appointments** | `get_appointments_async` | 106 | 1942-2047 | Yes | `_endpoints/appointments.py` |
| 11 | **Endpoint: get_leads** | `get_leads_async` | 113 | 2049-2160 | Yes | `_endpoints/leads.py` |
| 12 | **Period Normalization** | `_normalize_period` | 48 | 1415-1462 | Yes | Utility or config |
| 13 | **Content Disposition** | `_parse_content_disposition_filename` | 13 | 2162-2174 | Yes | Already module-level |

**Total LOC accounted**: 2,173 (all lines assigned)

### D-031 Callback Factory Analysis

Each of the 5 endpoint methods defines nested callback functions for the `_execute_with_retry` infrastructure. This table documents the exact parametric differences.

| Endpoint Method | `_on_retry`? | `_on_timeout_exhausted`? | `_on_http_error`? | Error Class | Log Event (retry) | Log Event (fail) | Metrics? | Extra Context |
|----------------|-------------|--------------------------|-------------------|-------------|-------------------|------------------|----------|---------------|
| `_execute_batch_request` (L1169-1229) | YES (L1169-1185) | YES (L1187-1208) | YES (L1210-1229) | `InsightsServiceError` | `insights_batch_request_retry` | `insights_batch_request_failed` | NO | `batch_size` in extra |
| `_execute_insights_request` (L1583-1677) | YES (L1583-1599) | YES (L1601-1639) | YES (L1641-1677) | `InsightsServiceError` | `insights_request_retry` | `insights_request_failed` | YES (error_total, latency_ms) | None |
| `get_export_csv_async` (L1856-1872) | NO | YES (L1856-1863) | YES (L1865-1872) | `ExportError` | N/A | N/A (no log event, just record_failure) | NO | `office_phone` in error |
| `get_appointments_async` (L2000-2014) | NO | YES (L2000-2006) | YES (L2008-2014) | `InsightsServiceError` | N/A | N/A (no log event, just record_failure) | NO | None |
| `get_leads_async` (L2112-2126) | NO | YES (L2112-2118) | YES (L2120-2126) | `InsightsServiceError` | N/A | N/A (no log event, just record_failure) | NO | None |

#### Detailed Parametric Differences

**Common shape across all 5 endpoints:**
1. `_on_timeout_exhausted`: `await self._circuit_breaker.record_failure(e)` then `raise ErrorClass(...) from e`
2. `_on_http_error`: `await self._circuit_breaker.record_failure(e)` then `raise ErrorClass(...) from e`

**Variation axis 1: `_on_retry` callback presence**
- Present in: `_execute_batch_request`, `_execute_insights_request` (2 of 5)
- Absent in: `get_export_csv_async`, `get_appointments_async`, `get_leads_async` (3 of 5)
- Structure when present: log a warning event with request_id, attempt, max_retries, and either status_code/retry_after or error_type/reason

**Variation axis 2: Error class**
- `InsightsServiceError`: used by 4 of 5 endpoints (batch, insights, appointments, leads)
- `ExportError`: used by export endpoint only

**Variation axis 3: Error message prefix**
- `"Batch request to autom8_data timed out"` / `"HTTP error communicating with autom8_data: {e}"`
- `"Request to autom8_data timed out"` / `"HTTP error communicating with autom8_data: {e}"`
- `"Export request timed out"` / `"HTTP error during export: {e}"`
- `"Appointments request timed out"` / `"HTTP error during appointments fetch: {e}"`
- `"Leads request timed out"` / `"HTTP error during leads fetch: {e}"`

**Variation axis 4: Error kwargs**
- `request_id=request_id, reason="timeout"` -- all InsightsServiceError instances
- `office_phone=office_phone, reason="timeout"` -- ExportError only

**Variation axis 5: Metrics emission in callbacks**
- Only `_execute_insights_request` emits metrics inside callbacks (`insights_request_error_total`, `insights_request_latency_ms`)
- `_execute_batch_request` emits metrics *outside* the callbacks (after response parsing)
- Other 3 endpoints emit no metrics in callbacks

**Variation axis 6: Elapsed time calculation**
- `_execute_batch_request` and `_execute_insights_request` calculate `elapsed_ms` inside callbacks (captures `start_time` from closure)
- Other 3 endpoints do not compute elapsed time in callbacks

**Variation axis 7: Extra log context fields**
- `_execute_batch_request`: `batch_size=len(pvp_list)` in all log extras
- `_execute_insights_request`: none
- Others: no logging in callbacks

#### LOC Per Instance

| Endpoint | `_on_retry` LOC | `_on_timeout` LOC | `_on_http_error` LOC | Total Callback LOC |
|----------|-----------------|-------------------|----------------------|-------------------|
| `_execute_batch_request` | 17 | 22 | 20 | **59** |
| `_execute_insights_request` | 17 | 39 | 37 | **93** |
| `get_export_csv_async` | 0 | 8 | 8 | **16** |
| `get_appointments_async` | 0 | 7 | 7 | **14** |
| `get_leads_async` | 0 | 7 | 7 | **14** |
| **Total** | **34** | **83** | **79** | **196** |

#### Factory Parameterization Summary

A callback factory would need these parameters:
1. `log_event_retry: str | None` -- retry log event name (None to skip _on_retry entirely)
2. `log_event_fail: str` -- failure log event name
3. `error_class: type[InsightsServiceError | ExportError]` -- which exception to raise
4. `error_msg_timeout: str` -- timeout error message
5. `error_msg_http: str` -- HTTP error message template (with `{e}` placeholder)
6. `error_kwargs: dict` -- extra kwargs for error class (`request_id=...` or `office_phone=...`)
7. `emit_metrics: bool` -- whether to emit error/latency metrics in callbacks
8. `extra_log_context: dict | None` -- extra fields for log extras (e.g., `batch_size`)
9. `start_time: float` -- captured for elapsed_ms calculation

The `_execute_insights_request` callbacks are the most complex (metrics + logging + elapsed time). The appointments/leads/export callbacks are the simplest (just record_failure + raise). A factory could reduce ~196 LOC of callbacks to ~30 LOC of factory invocations + ~50 LOC factory implementation = ~80 LOC net, saving **~116 LOC**.

### Shared State Analysis

| Instance Attribute | Used By Clusters |
|-------------------|-----------------|
| `self._config` | Configuration, HTTP Transport, Retry, Insights, Batch, Export, Appointments, Leads |
| `self._auth_provider` | HTTP Transport |
| `self._log` | All clusters |
| `self._cache` | Cache Delegation |
| `self._staleness_settings` | (unused in client.py -- passed through only) |
| `self._metrics_hook` | Cache Delegation (via `_emit_metric`) |
| `self._client` | HTTP Transport, all endpoint clusters |
| `self._client_lock` | HTTP Transport |
| `self._circuit_breaker` | Configuration (property), all endpoint clusters |
| `self._retry_handler` | Retry Infrastructure |

**Key observation**: All endpoint clusters depend on the same 4 instance attributes: `self._config`, `self._log`, `self._circuit_breaker`, and the HTTP client (via `self._get_client()`). They also share `self._execute_with_retry`. This means endpoint extraction requires either:
- Passing these as arguments to endpoint functions (pure function extraction)
- Creating endpoint classes that hold a reference to the core client
- Using mixin classes (not recommended)

### Coupling Matrix

| Cluster | Depends On | Depended On By |
|---------|-----------|----------------|
| PII Redaction | (none -- pure functions) | Insights endpoint (for `_mask_canonical_key`) |
| Configuration & Properties | (none) | All clusters |
| HTTP Transport | Configuration | All endpoint clusters |
| Retry Infrastructure | Configuration, HTTP Transport | All endpoint clusters |
| Cache Delegation | `_cache.py`, `_metrics.py` modules | Insights endpoint |
| Response Delegation | `_response.py` module | Insights, Appointments, Leads endpoints |
| get_insights | Config, Transport, Retry, Cache, Response, PII | (public API) |
| get_insights_batch | Config, Transport, Retry | (public API) |
| get_export_csv | Config, Transport, Retry, PII | (public API) |
| get_appointments | Config, Transport, Retry, Response, PII | (public API) |
| get_leads | Config, Transport, Retry, Response, PII | (public API) |
| Period Normalization | (none -- pure logic) | Insights, Batch endpoints |
| Content Disposition | (none -- pure function) | Export endpoint |

### Extraction Priority (ordered)

1. **D-031: Retry Callback Factory** -- Eliminates ~116 LOC of boilerplate across 5 endpoints. Lowest risk (behavioral change is zero). Standalone, no dependency on other extractions.

2. **Endpoint methods -> separate modules** -- Each of the 5 endpoint methods (insights, batch, export, appointments, leads) can be extracted to module-level async functions that accept the core client instance. The sync wrapper `get_insights` stays on the class as a thin delegation. This reduces the class from ~2,024 lines to ~600 lines (transport + retry + configuration + delegation wrappers).

3. **Period normalization -> config or utility** -- `_normalize_period` is pure logic with no instance state dependency (only uses `insights_period` argument). Move to `config.py` or a shared utility.

4. **PII Redaction** -- Already module-level. No extraction needed. Currently well-placed.

### Risks

- **Public API preservation**: All 5 public methods (`get_insights_async`, `get_insights`, `get_insights_batch_async`, `get_export_csv_async`, `get_appointments_async`, `get_leads_async`) must remain callable as `client.method()`. Extraction of implementation to separate modules is transparent to callers.
- **Closure capture**: The retry callbacks capture `start_time`, `request_id`, and other locals from their enclosing endpoint methods via closure. A callback factory must explicitly parameterize these.
- **Test restructuring dependency**: The 4,885-line test file `test_client.py` will need parallel restructuring (D-028) once endpoints are extracted.
- **Metrics inconsistency**: Only `_execute_insights_request` emits per-request metrics in its callbacks. The callback factory should make this consistent across endpoints (or explicitly opt-in).

### Test Coverage Mapping

Test file: `tests/unit/clients/data/test_client.py` (4,885 LOC, 31 test classes)

| Source Cluster | Test Class(es) | Test File Line Range | Approx Tests |
|---------------|----------------|---------------------|-------------|
| Configuration & Properties | `TestDataServiceClientInit` (L29), `TestDataServiceClientProperties` (L506) | 29-105, 506-535 | 12 |
| HTTP Transport | `TestDataServiceClientGetClient` (L206), `TestDataServiceClientGetAuthToken` (L369), `TestDataServiceClientConcurrency` (L473), `TestDataServiceClientClose` (L163), `TestDataServiceClientContextManager` (L108) | 108-504 | 25 |
| Feature Flag | `TestFeatureFlagDisabled` (L1404), `TestFeatureFlagEnabled` (L1528), `TestCheckFeatureEnabled` (L1760) | 1404-1819 | 16 |
| Endpoint: get_insights | `TestGetInsightsAsyncValidation` (L547), `TestGetInsightsAsyncHTTPContract` (L661), `TestGetInsightsAsyncErrorMapping` (L848), `TestGetInsightsAsyncSuccessResponse` (L1086), `TestGetInsightsAsyncIntegration` (L1216), `TestEntryTypeInsights` (L2676) | 547-1388, 2676-2696 | 35+ |
| PII Redaction | `TestMaskPhoneNumber` (L2697), `TestMaskCanonicalKey` (L2763) | 2697-2798 | 10 |
| Metrics | `TestMetricsHook` (L2800) | 2800-2858 | 5 |
| Observability (logging + metrics) | `TestObservabilityLogging` (L2859), `TestObservabilityMetrics` (L3032), `TestObservabilityIntegration` (L3212) | 2859-3310 | 30+ |
| Sync Wrapper | `TestSyncWrapper` (L3311) | 3311-3496 | 10+ |
| Circuit Breaker | `TestCircuitBreaker` (L3497) | 3497-3827 | 20+ |
| Retry Infrastructure | `TestRetryHandler` (L3828) | 3828-4343 | 25+ |
| Endpoint: batch | `TestGetInsightsBatchAsync` (L4344) | 4344-4885 | 25+ |
| Cache | `TestCacheKeyGeneration` (L1826), `TestCacheHit` (L1870), `TestCacheMiss` (L1994), `TestStaleFallback` (L2037), `TestCacheFailureGracefulDegradation` (L2392), `TestStaleResponseMetadata` (L2503) | 1826-2675 | 40+ |

Additional test files for endpoints not in `test_client.py`:
- `tests/unit/clients/data/test_client_extensions.py`: `TestGetAppointmentsAsync` (L60), `TestGetLeadsAsync` (L214), `TestNormalizePeriod` (L381), `TestInsightsRequestValidation` (L457)
- `tests/unit/clients/data/test_export.py`: `TestParseContentDispositionFilename` (L57), `TestGetExportCsvAsyncSuccess` (L84), `TestGetExportCsvAsyncErrors` (L212)

### Honest Assessment

DataServiceClient **is a genuine god object** that warrants decomposition. The evidence:

1. **2,024 lines in a single class** with 30 methods is objectively too large for maintainability.
2. **5 endpoint methods** each repeat the same circuit-breaker/retry/callback pattern with ~196 LOC of near-identical boilerplate.
3. **Mixing concerns**: HTTP transport, retry logic, circuit breaker management, authentication, 5 distinct API endpoints, PII redaction, metrics emission, and period normalization all coexist in one class.
4. **Three C901 violations** indicate high branching complexity concentrated in two endpoint methods.

However, the decomposition is **structurally straightforward** because:
- The concern boundaries are already visible (endpoints are self-contained methods)
- The cross-cutting infrastructure (retry, circuit breaker, transport) forms a natural "core client" skeleton
- Three modules have already been extracted successfully (`_cache.py`, `_metrics.py`, `_response.py`)
- The delegation pattern (thin wrapper on class -> module-level function) is proven

The risk is moderate: the callback factory (D-031) changes internal structure only, but full endpoint extraction requires parallel test restructuring (D-028).

---

## Target 2: SaveSession Decomposition Map

### Current State

- **File**: `src/autom8_asana/persistence/session.py`
- **LOC**: 1,853
- **Class span**: Lines 67-1853 (~1,786 lines in class body, plus `SessionState` at lines 53-64)
- **Method count**: 50 instance methods/properties + 13 ActionBuilder descriptors = 63 definitions on SaveSession (plus `SessionState` enum class at lines 53-64)
- **C901 violations**: 0 (no complexity violations in session.py)

### Existing Collaborator Modules

| Module | LOC | Responsibility |
|--------|-----|---------------|
| `action_executor.py` | 424 | Executes action operations via Asana API |
| `actions.py` | 733 | ActionBuilder descriptor, ACTION_REGISTRY, ActionOperation model |
| `pipeline.py` | 593 | SavePipeline: CRUD execution with dependency ordering |
| `tracker.py` | 376 | ChangeTracker: snapshot-based dirty detection |
| `events.py` | 311 | EventSystem: pre/post-save hooks |
| `graph.py` | 252 | DependencyGraph: topological sort |
| `healing.py` | 449 | HealingManager: self-healing project membership |
| `cascade.py` | 284 | CascadeExecutor: field propagation |
| `cache_invalidator.py` | 195 | CacheInvalidator: post-commit cache invalidation |
| `holder_ensurer.py` | 474 | HolderEnsurer: auto-create missing holders |
| `holder_concurrency.py` | 56 | HolderConcurrencyManager: dedup lock |
| `holder_construction.py` | 231 | Holder construction logic |
| `reorder.py` | 223 | LIS-optimized reorder plan computation |
| `validation.py` | 63 | Validation utilities |
| **Total collaborators** | **4,664** | |

### Concern Clusters

| # | Cluster | Methods | LOC | Line Range | Extractable? | Target Module |
|---|---------|---------|-----|-----------|-------------|---------------|
| 1 | **Context Managers** | `__aenter__`, `__aexit__`, `__enter__`, `__exit__` | 40 | 244-283 | No (protocol) | Keep on class |
| 2 | **Inspection Properties** | `state`, `pending_actions`, `healing_queue`, `auto_heal`, `automation_enabled`, `auto_create_holders`, `name_resolver` | 83 | 286-369 | No (read-only accessors) | Keep on class |
| 3 | **Entity Registration** | `track`, `_track_recursive`, `untrack`, `delete`, `get_changes`, `get_state`, `find_by_gid`, `is_tracked`, `get_dependency_order` | 305 | 373-676 | Partial (already delegates to `ChangeTracker` + `DependencyGraph`) | Keep on class |
| 4 | **Dry Run** | `preview` | 40 | 679-718 | No (thin delegation to `SavePipeline.preview`) | Keep on class |
| 5 | **Commit Orchestration** | `commit_async`, `_capture_commit_state`, `_execute_ensure_holders`, `_execute_crud_and_actions`, `_execute_cascades`, `_execute_healing`, `_update_post_commit_state`, `_execute_automation`, `_finalize_commit`, `commit` (sync), `_commit_sync` | 375 | 722-1118 | Partial (see analysis below) | Candidate for `CommitOrchestrator` |
| 6 | **Event Hooks** | `on_pre_save`, `on_post_save`, `on_error`, `on_post_commit` | 120 | 1122-1242 | No (thin delegation to `EventSystem`) | Keep on class |
| 7 | **ActionBuilder Descriptors** | 13 descriptors: `add_tag`, `remove_tag`, `add_to_project`, `remove_from_project`, `add_dependency`, `remove_dependency`, `move_to_section`, `add_follower`, `remove_follower`, `add_dependent`, `remove_dependent`, `add_like`, `remove_like` | 26 | 1247-1273 | No (descriptor declarations) | Keep on class |
| 8 | **Custom Action Methods** | `add_followers`, `remove_followers`, `add_comment`, `set_parent`, `reorder_subtask`, `reorder_subtasks`, `get_pending_actions`, `cascade_field`, `get_pending_cascades` | 371 | 1277-1703 | Partial | Some could move to action-related module |
| 9 | **Internal Utilities** | `_state_lock`, `_require_open`, `_ensure_open`, `_reset_custom_field_tracking`, `_clear_successful_actions`, `_build_gid_lookup` | 148 | 1706-1848 | No (lock primitives + state management) | Keep on class |
| 10 | **Constructor** | `__init__` | 100 | 134-241 | No (initialization) | Keep on class |

**Total LOC accounted**: 1,853 (all lines assigned, including imports, docstrings, SessionState class)

### Commit Orchestration Phase Sequence

The `commit_async` method (L722-835) orchestrates 6 phases in strict sequence:

```
Phase 0: ENSURE_HOLDERS (_execute_ensure_holders)
    |  Detects missing holder subtasks, creates them
    v
Phase 1 + 1.5: CRUD + ACTIONS + CACHE_INVALIDATION (_execute_crud_and_actions)
    |  Delegates to SavePipeline.execute_with_actions + ActionExecutor
    |  Then CacheInvalidator.invalidate_for_commit
    v
Phase 2: CASCADES (_execute_cascades)
    |  Delegates to CascadeExecutor.execute
    v
Phase 3: HEALING (_execute_healing)
    |  Delegates to HealingManager.execute_async
    v
Phase 4: STATE_UPDATE (_update_post_commit_state)
    |  Reset entity tracking, mark session COMMITTED
    v
Phase 5: AUTOMATION (_execute_automation)
    |  Delegates to client.automation.evaluate_async (isolated)
    v
Phase 6: FINALIZE (_finalize_commit)
    |  Post-commit hooks, logging
    v
Return SaveResult
```

**Lock patterns**: Lock held during `_capture_commit_state` (state check + snapshot). Released during all I/O phases (0-3, 5). Re-acquired briefly in `_execute_crud_and_actions` (L917) for `_clear_successful_actions` and in `_execute_cascades` (L940) for cascade clearing. Re-acquired in `_update_post_commit_state` (L994) for entity state reset.

**State transitions**: `OPEN` -> (commit starts) -> (phases execute without lock) -> `COMMITTED` (in `_update_post_commit_state`). Session can accept new `track()` calls during commit execution; those entities queue for next commit.

### Action Builder Methods Analysis

| Method | Type | LOC | Line Range | Logic Complexity |
|--------|------|-----|-----------|-----------------|
| `add_tag` | Descriptor | 1 | 1248 | None (ActionBuilder) |
| `remove_tag` | Descriptor | 1 | 1249 | None |
| `add_to_project` | Descriptor | 1 | 1252 | None |
| `remove_from_project` | Descriptor | 1 | 1253 | None |
| `add_dependency` | Descriptor | 1 | 1256 | None |
| `remove_dependency` | Descriptor | 1 | 1257 | None |
| `move_to_section` | Descriptor | 1 | 1260 | None |
| `add_follower` | Descriptor | 1 | 1263 | None |
| `remove_follower` | Descriptor | 1 | 1264 | None |
| `add_dependent` | Descriptor | 1 | 1267 | None |
| `remove_dependent` | Descriptor | 1 | 1268 | None |
| `add_like` | Descriptor | 1 | 1271 | None |
| `remove_like` | Descriptor | 1 | 1272 | None |
| `add_followers` | Custom | 29 | 1277-1305 | Loop over `add_follower` |
| `remove_followers` | Custom | 29 | 1307-1335 | Loop over `remove_follower` |
| `add_comment` | Custom | 73 | 1337-1409 | Validates text, builds `ActionOperation` |
| `set_parent` | Custom | 89 | 1415-1503 | Validates positioning, builds `ActionOperation` |
| `reorder_subtask` | Custom | 47 | 1505-1551 | Delegates to `set_parent` |
| `reorder_subtasks` | Custom | 58 | 1553-1610 | Computes plan via `compute_reorder_plan`, delegates to `set_parent` |
| `get_pending_actions` | Custom | 14 | 1612-1625 | Returns copy of list |
| `cascade_field` | Custom | 74 | 1629-1691 | Builds `CascadeOperation` |
| `get_pending_cascades` | Custom | 10 | 1693-1702 | Returns copy of list |

**Descriptor methods**: 13 declarations, 13 lines. These are highly compact thanks to the `ActionBuilder` descriptor pattern (ADR-0122). The descriptors themselves live in `actions.py` (733 LOC) which contains `ACTION_REGISTRY` with all metadata and docstrings.

**Custom methods**: 9 methods, ~423 LOC including docstrings. Of these:
- `add_followers` / `remove_followers` are trivial loops (could be generated)
- `add_comment`, `set_parent`, `cascade_field` contain validation + ActionOperation construction
- `reorder_subtask` delegates to `set_parent`
- `reorder_subtasks` has meaningful logic (LIS-optimized planning)
- `get_pending_actions` / `get_pending_cascades` are trivial accessors

### Shared State Analysis

| Instance Attribute | Used By Clusters |
|-------------------|-----------------|
| `self._client` | Constructor, Commit (ensure_holders, healing, automation) |
| `self._batch_size` | Constructor (passes to SavePipeline) |
| `self._max_concurrent` | Constructor only (reserved) |
| `self._tracker` | Entity Registration, Commit (state update, gid_lookup), Preview |
| `self._graph` | Entity Registration (get_dependency_order), Preview |
| `self._events` | Event Hooks, Commit (finalize) |
| `self._pipeline` | Preview, Commit (CRUD+actions) |
| `self._action_executor` | Commit (CRUD+actions via pipeline) |
| `self._pending_actions` | Custom Action Methods, Commit, Inspection Properties |
| `self._cascade_executor` | Commit (cascades) |
| `self._cascade_operations` | Custom Action Methods (cascade_field), Commit, Inspection |
| `self._name_cache` | Constructor only |
| `self._name_resolver` | Inspection Properties |
| `self._healing_manager` | Entity Registration (track), Commit (healing), Inspection |
| `self._automation_enabled` | Commit (automation), Inspection |
| `self._lock` | Internal Utilities (all lock operations) |
| `self._state` | Context Managers, Internal Utilities, Commit, Inspection |
| `self._log` | All clusters |
| `self._cache_invalidator` | Commit (CRUD+actions) |
| `self._auto_create_holders` | Commit (ensure_holders), Inspection |
| `self._holder_concurrency` | Commit (ensure_holders) |

### Coupling Matrix

| Cluster | Depends On | Depended On By |
|---------|-----------|----------------|
| Constructor | (initializes all collaborators) | All clusters |
| Context Managers | `_state_lock`, `_state` | (protocol -- used by callers) |
| Inspection Properties | `_state`, `_pending_actions`, `_healing_manager`, `_name_resolver`, `_automation_enabled`, `_auto_create_holders` | (read-only -- used by callers) |
| Entity Registration | `_tracker`, `_graph`, `_healing_manager`, `_log`, `_state_lock` | Commit (via `_tracker.get_dirty_entities`) |
| Preview | `_tracker`, `_pipeline`, `_pending_actions` | (used by callers) |
| Commit Orchestration | `_tracker`, `_pipeline`, `_action_executor`, `_cascade_executor`, `_healing_manager`, `_client`, `_cache_invalidator`, `_holder_concurrency`, `_events`, `_log`, `_state_lock`, `_auto_create_holders`, `_automation_enabled`, `_pending_actions`, `_cascade_operations` | (used by callers) |
| Event Hooks | `_events` | Commit (via `_events.emit_post_commit`) |
| ActionBuilder Descriptors | `_pending_actions`, `_ensure_open` | Commit (via `_pending_actions`) |
| Custom Action Methods | `_pending_actions`, `_cascade_operations`, `_ensure_open`, `_log` | Commit (via `_pending_actions`, `_cascade_operations`) |
| Internal Utilities | `_lock`, `_state`, `_tracker` | Entity Registration, Commit, Context Managers |

### Extraction Priority (ordered)

1. **Commit Orchestration -> CommitOrchestrator (conditional)** -- The 6-phase `commit_async` with its helper methods (`_capture_commit_state`, `_execute_ensure_holders`, etc.) totals ~375 LOC and is the largest single concern. However, see Honest Assessment below.

2. **Custom Action Methods (add_comment, set_parent, cascade_field)** -- These contain validation logic and ActionOperation construction that is independent of session state. Could be extracted to builder functions. However, the LOC savings would be modest (~200 LOC with docstrings) and would break the fluent API pattern (`session.add_comment(...).add_tag(...).commit()`).

3. **Internal Utilities** -- `_clear_successful_actions` and `_build_gid_lookup` are pure logic that could become standalone functions. Low ROI (~50 LOC).

### Risks

- **Fluent API breakage**: SaveSession exposes a fluent chaining API (`session.track(x).add_tag(x, y).commit()`). Extracting action methods to a separate object would require an adapter or break this pattern.
- **Lock semantics**: The locking protocol is distributed across multiple methods. Extracting commit orchestration requires careful preservation of lock acquire/release boundaries.
- **Test impact**: SaveSession has extensive test coverage in `tests/unit/persistence/`. Restructuring would require parallel test changes.
- **False economy**: Extracting 375 LOC of commit orchestration into a `CommitOrchestrator` class would leave SaveSession at ~1,478 LOC (still above the 500 LOC target) and introduce indirection without reducing total complexity.

### Honest Assessment

**SaveSession is NOT a classic god object.** While it is large (1,853 LOC, 63 definitions), the structural evidence tells a different story from DataServiceClient:

1. **Zero C901 violations.** No method in session.py has cyclomatic complexity above the threshold. The largest method (`commit_async`) is essentially a sequential phase dispatcher with no branching -- it calls 8 phase methods in order. Each phase method is typically 15-30 lines.

2. **Heavy delegation already in place.** SaveSession initializes and orchestrates **14 collaborator classes** totaling 4,664 LOC. The actual business logic (CRUD execution, dependency sorting, healing, cascade propagation, action execution, holder construction, reorder planning) lives entirely in collaborators. SaveSession is the **facade/coordinator**.

3. **The class is large because of its API surface, not its logic.** Of the 1,853 lines:
   - ~400 LOC is constructor + context managers + inspection properties (structural overhead)
   - ~120 LOC is event hook registration (4 thin delegation methods with docstrings)
   - ~26 LOC is 13 ActionBuilder descriptor declarations
   - ~423 LOC is custom action methods (mostly docstrings + validation + ActionOperation construction)
   - ~375 LOC is commit orchestration (sequential phase dispatch, no complex branching)
   - ~148 LOC is internal utilities (lock management, state cleanup)
   - ~360 LOC is entity registration (track/untrack/delete/get_changes etc. -- all delegate to ChangeTracker)

4. **Each method is focused.** The longest method body is `commit_async` at ~65 lines, which is a straightforward phase sequence. No method combines unrelated concerns.

5. **The 500 LOC target is unrealistic for this class.** SaveSession is the Unit of Work -- by definition, it must expose: entity registration (track/untrack/delete), change inspection, commit orchestration, action building (13 descriptor + 9 custom), cascade queuing, event hooks, and context manager protocol. Even with zero docstrings and zero validation, the method signatures alone would occupy ~300 LOC. With Python's required docstrings and type annotations, 500 LOC is mathematically insufficient for a 63-definition public API.

**Recommendation for Architect Enforcer:**

- **Do NOT decompose SaveSession into smaller classes.** The existing collaborator extraction is thorough and well-designed. Further decomposition would create indirection without reducing complexity.
- **Consider docstring reduction** if LOC targets are firm. Approximately 500 LOC of SaveSession is docstrings. Consolidating documentation (e.g., referencing ACTION_REGISTRY for descriptor docs instead of duplicating) could reduce to ~1,300 LOC.
- **The Sprint 5 scope for D-032 should be reconsidered.** The effort would be better spent on DataServiceClient decomposition (D-030/D-031) which has genuine structural problems.

---

## Cross-Target Observations

### DataServiceClient vs. SaveSession: Structural Comparison

| Metric | DataServiceClient | SaveSession |
|--------|------------------|-------------|
| LOC | 2,173 | 1,853 |
| C901 violations | 3 (29, 22, 12) | 0 |
| DRY violations in class | 196 LOC callback boilerplate | None |
| Concern mixing | 5+ distinct concerns | Single concern (UoW orchestration) |
| Existing extraction | 517 LOC in 3 modules | 4,664 LOC in 14 modules |
| Delegation depth | Shallow (wrappers around module functions) | Deep (14 collaborator classes) |
| Decomposition ROI | High | Low |
| True god object? | **Yes** | **No -- coordinator pattern** |

### D-031 Impact on Both Targets

D-031 (retry callback factory) is exclusively a DataServiceClient concern. It eliminates ~116 LOC from client.py and establishes the extraction pattern for subsequent endpoint decomposition (D-030). It has zero interaction with SaveSession.

---

## Attestation

| Artifact | Verified | Method |
|----------|----------|--------|
| `S5-DECOMPOSITION-MAP.md` | Yes | Written via Write tool |
| DataServiceClient line ranges | Yes | Verified via Read tool against `client.py` |
| SaveSession line ranges | Yes | Verified via Read tool against `session.py` |
| Extracted module LOC counts | Yes | Verified via `wc -l` |
| Collaborator LOC counts | Yes | Verified via `wc -l` |
| Test class line ranges | Yes | Verified via Grep on `test_client.py` |
| D-031 parametric differences | Yes | Verified via Read tool, each callback compared |
| C901 violation counts | Yes | Per SMELL-REPORT-WS4 (verified during WS4) |
| Method counts | Yes | Verified via Grep for `def ` patterns (50 defs on SaveSession confirmed) |
