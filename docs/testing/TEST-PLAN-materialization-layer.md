# Test Plan: DataFrame Materialization Layer

## Overview

This test plan validates the complete DataFrame Materialization Layer implementation from Sprint 2 and Sprint 3. The layer eliminates cold-start latency and implements efficient incremental sync via `modified_since` API parameter.

**Artifact ID**: TEST-PLAN-materialization-layer
**Sprint**: sprint-materialization-003 (Validation and QA)
**PRD Reference**: `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-materialization-layer.md`
**Test Period**: 2026-01-02
**Tester**: QA Adversary

---

## Test Scope

### Components Under Test

| Component | Location | Sprint |
|-----------|----------|--------|
| WatermarkRepository | `src/autom8_asana/dataframes/watermark.py` | Sprint 2 |
| refresh_incremental() | `src/autom8_asana/dataframes/builders/project.py` | Sprint 2 |
| DataFramePersistence | `src/autom8_asana/dataframes/persistence.py` | Sprint 2 |
| GidLookupIndex serialize/deserialize | `src/autom8_asana/services/gid_lookup.py` | Sprint 3 |
| Index persistence (save_index, load_index) | `src/autom8_asana/dataframes/persistence.py` | Sprint 3 |
| Watermark persistence (save_watermark, load_all_watermarks) | `src/autom8_asana/dataframes/persistence.py` | Sprint 3 |
| Startup preload (_preload_dataframe_cache) | `src/autom8_asana/api/main.py` | Sprint 2/3 |
| Incremental catch-up (_do_incremental_catchup) | `src/autom8_asana/api/main.py` | Sprint 3 |
| Health check cache status | `src/autom8_asana/api/routes/health.py` | Sprint 2 |

---

## PRD Success Criteria Mapping

| Criterion | Test Case IDs | Status |
|-----------|---------------|--------|
| First request after healthy status <500ms | TC-INT-001, TC-PERF-001 | Pending |
| Incremental refresh completes in <5 seconds | TC-INT-002, TC-PERF-002 | Pending |
| 90%+ reduction in Asana API calls after initial sync | TC-PERF-003 | Pending |
| Graceful degradation when S3 unavailable | TC-EDGE-001, TC-EDGE-002 | Pending |
| Container startup within ECS timeout (60s) | TC-PERF-004 | Pending |
| Health check returns 503 until cache ready | TC-UNIT-HEALTH-001, TC-UNIT-HEALTH-002 | Passed |

---

## Unit Tests (Existing Coverage)

### WatermarkRepository (`tests/unit/test_watermark.py`)

| Test Case | Description | Status |
|-----------|-------------|--------|
| test_get_instance_returns_singleton | Singleton pattern enforcement | PASS |
| test_direct_instantiation_returns_singleton | Direct instantiation returns singleton | PASS |
| test_get_watermark_repo_returns_singleton | Module function returns singleton | PASS |
| test_reset_clears_singleton | reset() clears singleton state | PASS |
| test_get_watermark_returns_none_for_unknown | Returns None for unknown project | PASS |
| test_set_and_get_watermark | Basic set/get operation | PASS |
| test_set_watermark_updates_existing | Updates existing watermark | PASS |
| test_set_watermark_rejects_naive_datetime | Rejects non-timezone-aware datetime | PASS |
| test_multiple_projects_independent | Per-project isolation | PASS |
| test_get_all_watermarks_returns_copy | Returns copy to prevent modification | PASS |
| test_clear_watermark_removes_existing | Clear operation works | PASS |
| test_concurrent_singleton_access | Thread-safe singleton | PASS |
| test_concurrent_set_watermark | Thread-safe set operations | PASS |
| test_concurrent_get_and_set | Thread-safe mixed operations | PASS |
| test_set_persistence_configures_repository | Persistence configuration | PASS |
| test_load_from_persistence_hydrates_watermarks | Loads watermarks from S3 | PASS |
| test_persist_watermark_handles_failure_gracefully | Graceful S3 failure handling | PASS |

**Coverage**: Comprehensive - thread safety, singleton pattern, timezone validation, persistence integration.

---

### DataFramePersistence (`tests/unit/test_persistence.py`)

| Test Case | Description | Status |
|-----------|-------------|--------|
| test_config_with_defaults | Default configuration values | PASS |
| test_config_with_all_params | All configuration parameters | PASS |
| test_make_dataframe_key | DataFrame S3 key format | PASS |
| test_make_watermark_key | Watermark S3 key format | PASS |
| test_make_index_key | Index S3 key format | PASS |
| test_save_dataframe_rejects_naive_datetime | Timezone validation | PASS |
| test_save_dataframe_returns_false_when_degraded | Degraded mode behavior | PASS |
| test_load_dataframe_returns_none_when_degraded | Degraded mode behavior | PASS |
| test_delete_dataframe_returns_false_when_degraded | Degraded mode behavior | PASS |
| test_is_available_false_when_degraded | Availability check | PASS |
| test_save_index_success | Index save to S3 | PASS |
| test_save_index_handles_s3_error | S3 error handling | PASS |
| test_load_index_success | Index load from S3 | PASS |
| test_load_index_returns_none_when_not_found | 404 handling | PASS |
| test_load_index_handles_invalid_json | Corrupted data handling | PASS |
| test_delete_index_success | Index deletion | PASS |
| test_save_and_load_preserves_data | Round-trip data integrity | PASS |
| test_save_watermark_success | Watermark save to S3 | PASS |
| test_load_all_watermarks_loads_multiple_projects | Bulk watermark load | PASS |
| test_load_all_watermarks_handles_missing_watermark | Partial data handling | PASS |
| test_handle_s3_error_enters_degraded_for_connection_errors | Degraded mode trigger | PASS |
| test_reconnect_interval_respected | Reconnection rate limiting | PASS |

**Coverage**: Comprehensive - all S3 operations, degraded mode, error handling, round-trip integrity.

---

### GidLookupIndex Serialization (`tests/unit/test_gid_lookup.py`)

| Test Case | Description | Status |
|-----------|-------------|--------|
| test_serialize_returns_dict_with_required_keys | Required keys present | PASS |
| test_serialize_version_is_1_0 | Version format | PASS |
| test_serialize_created_at_is_iso_format | ISO 8601 datetime | PASS |
| test_serialize_entry_count_matches_lookup_length | Entry count validation | PASS |
| test_serialize_is_json_compatible | JSON serialization | PASS |
| test_deserialize_reconstructs_index | Reconstruction from data | PASS |
| test_deserialize_preserves_lookup_entries | Lookup data integrity | PASS |
| test_deserialize_parses_created_at | Datetime parsing | PASS |
| test_deserialize_raises_key_error_missing_version | Missing key validation | PASS |
| test_deserialize_raises_value_error_invalid_version | Version validation | PASS |
| test_deserialize_raises_value_error_invalid_datetime | Datetime validation | PASS |
| test_deserialize_raises_value_error_entry_count_mismatch | Corruption detection | PASS |
| test_round_trip_preserves_equality | Round-trip integrity | PASS |
| test_round_trip_through_json | JSON round-trip | PASS |
| test_round_trip_large_index | 1000-entry index | PASS |

**Coverage**: Comprehensive - serialization, deserialization, validation, corruption detection.

---

### Incremental Refresh (`tests/unit/test_incremental_refresh.py`)

| Test Case | Description | Status |
|-----------|-------------|--------|
| test_no_watermark_triggers_full_fetch | First sync behavior | PASS |
| test_existing_df_none_with_watermark_triggers_full_fetch | Edge case handling | PASS |
| test_with_watermark_fetches_modified_only | Incremental fetch behavior | PASS |
| test_no_changes_returns_existing_df | No-op optimization | PASS |
| test_merge_deltas_replaces_existing_rows | Update handling | PASS |
| test_merge_deltas_adds_new_tasks | New task handling | PASS |
| test_merge_deltas_empty_changes_returns_existing | Empty delta optimization | PASS |
| test_merge_deltas_multiple_updates_and_new | Mixed updates | PASS |
| test_error_during_incremental_triggers_full_fetch | Fallback behavior | PASS |
| test_future_watermark_triggers_full_rebuild | Clock skew handling | PASS |
| test_new_watermark_is_sync_start_time | Watermark calculation | PASS |
| test_watermark_is_timezone_aware | UTC timezone requirement | PASS |
| test_no_project_gid_returns_empty_df | Missing project GID | PASS |

**Coverage**: Comprehensive - full fetch, incremental fetch, delta merge, fallback scenarios.

---

### Health Check (`tests/api/test_health.py`)

| Test Case | Description | Status |
|-----------|-------------|--------|
| test_health_returns_200 | Basic health check | PASS |
| test_health_response_structure | Response format | PASS |
| test_health_no_auth_required | No authentication | PASS |
| test_health_returns_503_when_cache_not_ready | Warming state | PASS |
| test_health_returns_200_when_cache_ready | Ready state | PASS |
| test_set_cache_ready_changes_state | State transition | PASS |
| test_cache_state_transition | Full lifecycle | PASS |
| test_health_warming_no_auth_required | No auth during warming | PASS |
| test_s2s_health_status_healthy_when_all_dependencies_ok | S2S healthy | PASS |
| test_s2s_health_status_degraded_when_jwks_unreachable | S2S degraded | PASS |

**Coverage**: Comprehensive - cache readiness states, S2S health, authentication bypass.

---

## Integration Tests (New Tests Needed)

### TC-INT-001: Full Refresh Cycle

**Requirement**: US-001 (Fast First Request), FR-003 (Startup Preloading)
**Priority**: High
**Type**: Integration

#### Preconditions
- S3 bucket accessible with valid credentials
- Asana API accessible with valid bot PAT
- Test workspace with at least one project containing 100+ tasks

#### Steps
1. Clear all persisted state (DataFrames, watermarks, indices) from S3
2. Reset WatermarkRepository singleton
3. Clear _gid_index_cache module cache
4. Start application (invoke lifespan startup)
5. Wait for health check to return 200 ("healthy")
6. Measure time from application start to healthy state
7. Invoke Entity Resolver for first request
8. Measure first request latency

#### Expected Result
- Health check returns 503 during startup preload
- Health check transitions to 200 when preload completes
- Startup completes in <60 seconds
- First request completes in <500ms
- S3 contains persisted DataFrame, watermark, and index

#### Actual Result
Pending execution

---

### TC-INT-002: Incremental Catch-up on Restart

**Requirement**: US-002 (Efficient Hourly Refresh), FR-002 (Incremental Refresh)
**Priority**: High
**Type**: Integration

#### Preconditions
- Persisted state exists in S3 (DataFrame, watermark, index)
- Some tasks modified since watermark timestamp

#### Steps
1. Note current persisted watermark timestamp
2. Modify 5 tasks in Asana (update names)
3. Create 2 new tasks in Asana
4. Restart application (simulate container restart)
5. Wait for health check to return 200
6. Verify incremental catch-up used modified_since
7. Measure catch-up duration
8. Verify index contains new task GIDs

#### Expected Result
- Startup logs show "incremental_catchup" strategy
- Catch-up completes in <5 seconds
- Only modified/new tasks fetched (7 tasks, not all)
- Updated watermark persisted to S3
- Index contains new task entries

#### Actual Result
Pending execution

---

### TC-INT-003: Resolver Uses Cached Index

**Requirement**: US-003 (Centralized Cache Benefit), FR-005 (Resolver Integration)
**Priority**: High
**Type**: Integration

#### Preconditions
- Cache preload complete (health check returns 200)
- GidLookupIndex populated in _gid_index_cache

#### Steps
1. Start application and wait for healthy state
2. Call Entity Resolver 10 times with valid phone/vertical pairs
3. Monitor Asana API call logs
4. Measure response latency for each request

#### Expected Result
- All 10 requests use cached index (no API calls)
- Response latency <500ms for each request
- Logs show cache hit pattern

#### Actual Result
Pending execution

---

### TC-INT-004: Resolver Refreshes on Cache Miss

**Requirement**: FR-005 (Resolver Integration)
**Priority**: Medium
**Type**: Integration

#### Preconditions
- Cache preload complete
- Index TTL configured (e.g., 3600 seconds)

#### Steps
1. Start application and wait for healthy state
2. Manually clear _gid_index_cache (simulate TTL expiry)
3. Call Entity Resolver with valid phone/vertical
4. Verify rebuild occurs
5. Call Entity Resolver again
6. Verify cache hit

#### Expected Result
- First call triggers incremental refresh
- Subsequent calls use cached index
- Rebuild uses modified_since parameter

#### Actual Result
Pending execution

---

## Load Benchmarks (Performance Validation)

### TC-PERF-001: Cold Start Timing with Persisted State

**Requirement**: NFR-001 (Latency), US-005 (ECS Timeout)
**Priority**: High
**Type**: Performance

#### Preconditions
- S3 contains persisted state for 3 projects
- Total task count across projects: 10,000+

#### Steps
1. Stop application
2. Start application with timer
3. Measure time to healthy state
4. Record breakdown: S3 load time, incremental sync time

#### Expected Result
- Total startup time <60 seconds
- S3 load: <2 seconds per project
- Incremental sync: <5 seconds per project
- First request after healthy: <500ms

#### Actual Result
Pending execution

---

### TC-PERF-002: Incremental Refresh Latency

**Requirement**: NFR-001 (Latency), US-002 (Efficient Refresh)
**Priority**: High
**Type**: Performance

#### Preconditions
- Warm cache with 10,000 tasks
- 1% of tasks modified since last watermark (100 tasks)

#### Steps
1. Trigger manual cache refresh via TTL expiry
2. Measure refresh duration
3. Record API call count

#### Expected Result
- Refresh completes in <5 seconds
- API calls: ~100 tasks (1% of total)
- Log shows "incremental" strategy

#### Actual Result
Pending execution

---

### TC-PERF-003: API Call Reduction Verification

**Requirement**: 90%+ reduction in Asana API calls
**Priority**: High
**Type**: Performance

#### Preconditions
- Project with 1,000 tasks
- Baseline: Full rebuild API call count recorded

#### Steps
1. Perform full rebuild, count API calls (baseline)
2. Wait for TTL expiry
3. Modify 10 tasks (1%)
4. Trigger incremental refresh, count API calls
5. Calculate reduction percentage

#### Expected Result
- Baseline: ~100 API calls (task pagination)
- Incremental: ~5 API calls (modified tasks only)
- Reduction: 95%+

#### Actual Result
Pending execution

---

### TC-PERF-004: Container Startup Under Load

**Requirement**: US-005 (ECS Timeout)
**Priority**: Medium
**Type**: Performance

#### Preconditions
- 5 projects with total 50,000 tasks
- Persisted state in S3

#### Steps
1. Start container with resource limits (1 vCPU, 2GB RAM)
2. Measure startup time to healthy state
3. Monitor memory usage during preload
4. Monitor CPU usage during preload

#### Expected Result
- Startup completes in <60 seconds
- Peak memory <2GB
- No OOM errors
- Health check returns 200

#### Actual Result
Pending execution

---

## Edge Case Tests

### TC-EDGE-001: S3 Unavailable at Startup

**Requirement**: Graceful degradation when S3 unavailable
**Priority**: High
**Type**: Edge Case

#### Preconditions
- S3 endpoint unreachable (network isolation or invalid credentials)

#### Steps
1. Configure invalid S3 endpoint
2. Start application
3. Observe startup behavior
4. Verify health check eventually returns 200
5. Test Entity Resolver functionality

#### Expected Result
- Startup logs warning about S3 unavailability
- Application continues startup (graceful degradation)
- Health check returns 200 (cache built on first request)
- Entity Resolver performs full fetch on first request
- Subsequent requests use in-memory cache

#### Actual Result
Pending execution

---

### TC-EDGE-002: S3 Unavailable During Persistence

**Requirement**: Graceful degradation when S3 unavailable
**Priority**: High
**Type**: Edge Case

#### Preconditions
- Application running with healthy cache
- S3 becomes unavailable mid-operation

#### Steps
1. Start application with healthy S3
2. Trigger watermark update
3. Disconnect S3 mid-persistence
4. Verify in-memory watermark is updated
5. Verify no exception propagates to caller

#### Expected Result
- Watermark updated in memory
- Persistence failure logged (warning)
- No exception thrown
- Application continues operating
- Persistence auto-recovers when S3 available

#### Actual Result
Pending execution

---

### TC-EDGE-003: Corrupted Persisted Index

**Requirement**: Data integrity, graceful recovery
**Priority**: Medium
**Type**: Edge Case

#### Preconditions
- Persisted index in S3

#### Steps
1. Manually corrupt index JSON in S3 (invalid JSON or wrong entry_count)
2. Start application
3. Observe error handling
4. Verify recovery behavior

#### Expected Result
- Load failure logged with corruption details
- Application falls back to full rebuild
- New valid index persisted to S3
- No crash or service outage

#### Actual Result
Pending execution

---

### TC-EDGE-004: Corrupted Persisted DataFrame

**Requirement**: Data integrity, graceful recovery
**Priority**: Medium
**Type**: Edge Case

#### Preconditions
- Persisted DataFrame in S3

#### Steps
1. Manually corrupt Parquet file in S3
2. Start application
3. Observe error handling
4. Verify recovery behavior

#### Expected Result
- Load failure logged
- Application falls back to full rebuild
- New valid DataFrame persisted to S3
- No crash or service outage

#### Actual Result
Pending execution

---

### TC-EDGE-005: Clock Skew (Future Watermark)

**Requirement**: FR-006 (Delta Merge), Edge case handling
**Priority**: Medium
**Type**: Edge Case

#### Preconditions
- Persisted watermark set to future timestamp (1 year ahead)

#### Steps
1. Manually set watermark in S3 to future date
2. Start application
3. Observe handling of future watermark
4. Verify full rebuild triggered

#### Expected Result
- Log warning about clock skew detected
- Full rebuild triggered (not incremental)
- New valid watermark set to current time
- No exception or crash

#### Actual Result
Pending execution

---

### TC-EDGE-006: Concurrent Access to WatermarkRepository

**Requirement**: Thread safety
**Priority**: Medium
**Type**: Edge Case

#### Preconditions
- Application running

#### Steps
1. Spawn 50 concurrent threads
2. Each thread performs 100 set/get operations on different projects
3. Verify no race conditions or data corruption

#### Expected Result
- All operations complete without deadlock
- No data corruption (each project has correct watermark)
- No exceptions

#### Actual Result
Pending execution (covered by unit tests)

---

### TC-EDGE-007: Zero Tasks in Project

**Requirement**: Empty project handling
**Priority**: Low
**Type**: Edge Case

#### Preconditions
- Empty project registered in EntityProjectRegistry

#### Steps
1. Create empty project in Asana
2. Register project for entity resolution
3. Start application
4. Observe preload behavior for empty project

#### Expected Result
- Empty DataFrame created and persisted
- Empty index created and persisted
- Watermark set
- Health check returns 200
- Entity Resolver returns empty results

#### Actual Result
Pending execution

---

### TC-EDGE-008: Entity Type Not Registered

**Requirement**: Edge case handling
**Priority**: Low
**Type**: Edge Case

#### Preconditions
- EntityProjectRegistry has no registered entity types

#### Steps
1. Clear EntityProjectRegistry
2. Start application
3. Observe preload behavior

#### Expected Result
- Preload logs "no_registered_projects"
- Health check returns 200 (no preload needed)
- Application starts successfully

#### Actual Result
Pending execution

---

## Security Tests

### TC-SEC-001: S3 Credentials Not Logged

**Requirement**: Security best practices
**Priority**: High
**Type**: Security

#### Preconditions
- S3 credentials configured via environment

#### Steps
1. Enable DEBUG logging
2. Trigger S3 operations (save, load, error scenarios)
3. Search logs for credential patterns

#### Expected Result
- No AWS access key IDs in logs
- No AWS secret keys in logs
- Connection errors show endpoint, not credentials

#### Actual Result
Pending execution

---

### TC-SEC-002: Persisted Data Encrypted at Rest

**Requirement**: Data protection
**Priority**: Medium
**Type**: Security

#### Preconditions
- S3 bucket with SSE-S3 or SSE-KMS enabled

#### Steps
1. Save DataFrame to S3
2. Verify S3 object metadata shows encryption
3. Attempt to read object without proper credentials

#### Expected Result
- S3 objects encrypted (ServerSideEncryption header present)
- Unauthorized read returns 403

#### Actual Result
Pending execution

---

## Execution Instructions

### Unit Test Execution

```bash
# Run all materialization-related unit tests
pytest tests/unit/test_watermark.py tests/unit/test_persistence.py tests/unit/test_gid_lookup.py tests/unit/test_incremental_refresh.py -v

# Run with coverage
pytest tests/unit/test_watermark.py tests/unit/test_persistence.py tests/unit/test_gid_lookup.py tests/unit/test_incremental_refresh.py --cov=autom8_asana.dataframes --cov=autom8_asana.services.gid_lookup --cov-report=term-missing
```

### API Test Execution

```bash
# Run health check tests
pytest tests/api/test_health.py -v
```

### Integration Test Setup

1. Configure test environment variables:
   ```bash
   export ASANA_PAT="0/your_test_pat"
   export ASANA_WORKSPACE_GID="your_workspace_gid"
   export ASANA_CACHE_S3_BUCKET="test-cache-bucket"
   export ASANA_CACHE_S3_REGION="us-east-1"
   ```

2. Create test projects in Asana with known task counts

3. Run integration tests:
   ```bash
   pytest tests/integration/test_materialization.py -v --run-integration
   ```

### Performance Test Setup

1. Prepare large test dataset (10K+ tasks)
2. Run performance tests with timing:
   ```bash
   pytest tests/performance/test_startup.py -v --durations=0
   ```

---

## Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Task deletions not detected | Stale data until full rebuild | Acceptable staleness per PRD |
| No multi-container cache sharing | Each container warms independently | Acceptable for 1-2 container deployment |
| Parallel entity preloading not implemented | Serial preload per entity type | Future enhancement (FR-008) |

---

## Defect Tracking

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| None identified | - | - | - |

---

## Release Recommendation

**Status**: PENDING

**Criteria for GO**:
- [ ] All unit tests pass
- [ ] Integration tests TC-INT-001 through TC-INT-004 pass
- [ ] Performance tests TC-PERF-001 and TC-PERF-002 meet targets
- [ ] Edge case tests TC-EDGE-001 and TC-EDGE-002 pass
- [ ] No critical or high severity defects

**Criteria for CONDITIONAL GO**:
- All critical tests pass
- Medium severity defects documented with workarounds
- Performance within 120% of target (degraded but acceptable)

**Criteria for NO-GO**:
- Any critical test fails
- Performance >200% of target
- Security vulnerabilities identified

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-02 | 1.0 | QA Adversary | Initial test plan |
