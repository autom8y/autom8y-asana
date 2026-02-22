# Test Suite Performance Profile

**Generated**: 2026-02-16
**Runner**: pytest 9.0.2 (pytest-asyncio, pytest-timeout, pytest-json-report, pytest-mock, pytest-cov)
**Python**: 3.12 | **asyncio_mode**: auto | **timeout**: 60s (thread method)
**Total tests collected**: 10,452 | **Profiled**: 10,407 (45 skipped)

---

## Summary

| Metric | Value |
|--------|-------|
| Total tests | 10,452 |
| Total wall-clock (sequential batches) | 295.9s |
| Sum of individual test durations | 284.3s |
| Mean duration | 27.3ms |
| Median duration | 0.6ms |
| P90 duration | 4.3ms |
| P95 duration | 25.1ms |
| P99 duration | 413.7ms |
| Max duration | 15,286ms |

### Tier Distribution

| Tier | Count | Percentage | Criteria |
|------|-------|------------|----------|
| Fast | 10,340 | 99.4% | <500ms |
| Medium | 42 | 0.4% | 500ms-2s |
| Slow | 25 | 0.2% | >2s |

**Assessment**: The vast majority of tests (99.4%) are healthy. However, 67 tests exceed 500ms, and 25 exceed 2s. The top 2 tests alone account for 30s (10% of total execution time). The suite is dominated by fixture overhead in the API tests (101s wall-clock for 334 tests) rather than test logic.

---

## Top 20 Slowest Tests

| # | Duration | File | Test | Root Cause |
|---|----------|------|------|------------|
| 1 | 15,286ms | `tests/unit/clients/data/test_client.py` | `TestCircuitBreaker::test_circuit_opens_after_threshold` | Real retry backoff (max_retries=2 not disabled) |
| 2 | 14,561ms | `tests/unit/clients/data/test_client.py` | `TestCircuitBreaker::test_circuit_open_raises_immediately` | Real retry backoff (max_retries=2 not disabled) |
| 3 | 12,336ms | `tests/integration/test_e2e_offer_write_proof.py` | `test_e2e_offer_write_proof` | Live Asana API round-trips |
| 4 | 5,144ms | `tests/integration/test_entity_write_smoke.py` | `TestEnumResolution::test_enum_write_by_name` | Live Asana API + field resolution |
| 5 | 4,633ms | `tests/integration/test_entity_write_smoke.py` | `TestLiveWrites::test_null_clear_text_field` | Live Asana API |
| 6 | 4,594ms | `tests/unit/dataframes/builders/test_paced_fetch.py` | `TestFinalWriteReplacesCheckpoint::*` | Real asyncio.sleep in pacing |
| 7 | 4,348ms | `tests/integration/test_entity_write_smoke.py` | `TestEnumResolution::test_multi_enum_write` | Live Asana API |
| 8 | 4,306ms | `tests/integration/test_entity_write_smoke.py` | `TestPartialSuccess::test_mixed_valid_and_invalid` | Live Asana API |
| 9 | 3,795ms | `tests/integration/test_entity_write_smoke.py` | `TestDiscoveredDefects::test_d_ew_001_invalid` | Live Asana API |
| 10 | 3,658ms | `tests/integration/test_entity_write_smoke.py` | `TestLiveWrites::test_text_field_write` | Live Asana API |
| 11 | 3,622ms | `tests/integration/test_entity_write_smoke.py` | `TestLiveWrites::test_number_field_write` | Live Asana API |
| 12 | 3,411ms | `tests/integration/test_entity_write_smoke.py` | `TestLiveWrites::test_core_field_write_name` | Live Asana API |
| 13 | 3,397ms | `tests/integration/test_entity_write_smoke.py` | `TestResultStructure::test_resolved_fields` | Live Asana API |
| 14 | 3,379ms | `tests/integration/test_entity_write_smoke.py` | `TestPartialSuccess::test_partial_with_type` | Live Asana API |
| 15 | 3,292ms | `tests/unit/clients/data/test_client.py` | `TestStaleFallback::test_stale_fallback_on_503` | Real retry backoff |
| 16 | 3,162ms | `tests/unit/clients/data/test_client.py` | `TestStaleFallback::test_stale_fallback_on_502` | Real retry backoff |
| 17 | 3,110ms | `tests/integration/test_entity_write_smoke.py` | `TestLiveWrites::test_mixed_write_multiple` | Live Asana API |
| 18 | 2,851ms | `tests/unit/clients/data/test_client.py` | `TestStaleFallback::test_stale_fallback_on_504` | Real retry backoff |
| 19 | 2,774ms | `tests/integration/test_entity_write_smoke.py` | `TestResultStructure::test_result_has_correct` | Live Asana API |
| 20 | 2,647ms | `tests/unit/clients/data/test_client.py` | `TestGetInsightsAsyncErrorMapping::test_503_maps` | Real retry backoff |

### Root Cause Summary for >500ms Tests (67 total)

| Root Cause | Count | Aggregate Time |
|------------|-------|----------------|
| Circuit breaker / retry with real backoff sleep | 11 | ~54s |
| Integration tests (live Asana API or complex orchestration) | 15 | ~50s |
| Pacing/checkpoint tests with real asyncio.sleep | 11 | ~17s |
| API TestClient fixture overhead (setup+teardown per test) | 2 | ~2s |
| S2S health endpoint (TestClient + async startup) | 4 | ~4s |
| TTL expiry (time.sleep for cache expiration) | 3 | ~3s |
| Other (moto S3, admin refresh, startup preload) | 21 | ~12s |

---

## Batch Timing Breakdown

| Batch | Directory | Tests | Wall-clock | Avg/test | Notes |
|-------|-----------|-------|------------|----------|-------|
| 10 | `tests/api/` | 334 | 101.4s | 303.5ms | TestClient setup/teardown dominates |
| 11 | `tests/integration/` | 534 | 69.7s | 130.6ms | Live API + complex mocks |
| 7 | `tests/unit/clients+transport+core` | 1,002 | 56.8s | 56.7ms | Circuit breaker retries |
| 1 | `tests/unit/cache/` | 1,181 | 21.5s | 18.2ms | S3 moto fixtures, build coordinator |
| 5 | `tests/unit/dataframes/` | 918 | 19.9s | 21.6ms | Pacing tests with sleep |
| 8 | `tests/unit/misc` | 966 | 17.3s | 17.9ms | Lambda handlers, lifecycle, metrics |
| 4 | `tests/unit/automation/` | 819 | 1.8s | 2.1ms | Healthy |
| 3 | `tests/unit/persistence/` | 914 | 1.8s | 1.9ms | Healthy |
| 9 | `tests/unit/test_*.py` (top-level) | 1,021 | 1.7s | 1.6ms | Healthy |
| 12 | `tests/remaining` | 367 | 1.5s | 4.1ms | Healthy |
| 2 | `tests/unit/models/` | 1,434 | 1.5s | 1.0ms | Exemplary |
| 6 | `tests/unit/services+query` | 917 | 1.2s | 1.3ms | Exemplary |
| **TOTAL** | | **10,407** | **295.9s** | **28.4ms** | |

### Top 30 Slowest Test Files

| # | Total Time | Tests | Avg/test | Max | Setup% | TD% | File |
|---|-----------|-------|----------|-----|--------|-----|------|
| 1 | 54.6s | 181 | 302ms | 15,286ms | 0.1% | 0.1% | `test_client.py` (data) |
| 2 | 49.5s | 43 | 1,150ms | 5,144ms | 0.9% | 0.0% | `test_entity_write_smoke.py` |
| 3 | 16.4s | 46 | 357ms | 431ms | 15.8% | 82.7% | `test_routes_dataframes.py` |
| 4 | 14.8s | 41 | 360ms | 438ms | 16.9% | 82.2% | `test_routes_projects.py` |
| 5 | 12.3s | 1 | 12,336ms | 12,336ms | 0.0% | 0.0% | `test_e2e_offer_write_proof.py` |
| 6 | 10.5s | 25 | 421ms | 1,000ms | 12.4% | 53.7% | `test_health.py` |
| 7 | 8.9s | 8 | 1,110ms | 4,594ms | 0.0% | 0.0% | `test_paced_fetch.py` |
| 8 | 8.6s | 24 | 360ms | 430ms | 16.8% | 82.3% | `test_tasks.py` |
| 9 | 8.5s | 22 | 388ms | 1,661ms | 0.1% | 0.1% | `test_adversarial_pacing.py` |
| 10 | 8.1s | 21 | 387ms | 772ms | 14.0% | 75.3% | `test_routes_query_rows.py` |
| 11 | 6.9s | 29 | 237ms | 416ms | 15.9% | 81.7% | `test_routes_query.py` |
| 12 | 6.6s | 32 | 208ms | 479ms | 15.5% | 82.9% | `test_routes_resolver.py` |
| 13 | 5.6s | 16 | 349ms | 436ms | 17.3% | 79.9% | `test_resolver_gid_contract.py` |
| 14 | 5.2s | 59 | 88ms | 707ms | 96.8% | 0.4% | `test_s3_backend.py` |
| 15 | 5.1s | 33 | 154ms | 2,002ms | 0.3% | 0.2% | `test_build_coordinator.py` |

---

## Infrastructure Findings

### Current Configuration

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
timeout = 60
timeout_method = "thread"
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests requiring live API access",
    "benchmark: marks tests as performance benchmarks",
]
```

### Issue 1: No Test Parallelism (HIGH IMPACT)

**Current**: Tests run serially. No `pytest-xdist` installed.
**Impact**: Full suite takes ~296s serially. With 4-8 workers, could be ~50-80s.
**Recommended**:
```bash
pip install pytest-xdist
# Add to pyproject.toml [project.optional-dependencies] dev:
#   "pytest-xdist>=3.5.0",
# Run with:
.venv/bin/pytest tests/ -n auto --timeout=60
```
**Caveat**: Requires verifying all tests are properly isolated (no shared state). The `autouse=True` registry reset fixtures in `conftest.py` suggest awareness of isolation, but xdist runs tests in separate processes which requires all fixtures to be process-safe.

### Issue 2: API TestClient Created Per-Test (HIGH IMPACT)

**Current**: `tests/api/conftest.py` creates a new `TestClient(app)` for each test via `authed_client` and `client` fixtures. Each TestClient instantiation triggers FastAPI lifespan (startup/shutdown), adding ~120ms setup + ~220ms teardown = **340ms overhead per test**.
**Impact**: 334 API tests x 340ms = **113s of pure fixture overhead** (38% of total suite time).
**Recommended**: Use `session`-scoped or `module`-scoped `app` fixture, and `session`-scoped `TestClient` where possible:
```python
@pytest.fixture(scope="module")
def app():
    """Create app once per module."""
    ...

@pytest.fixture(scope="module")
def base_client(app):
    """Shared TestClient -- tests use dependency_overrides for isolation."""
    with TestClient(app) as c:
        yield c
```
This alone would reduce API test time from ~101s to ~15-20s.

### Issue 3: Circuit Breaker Tests Use Real Retry Backoff (HIGH IMPACT)

**Current**: `test_circuit_opens_after_threshold` and `test_circuit_open_raises_immediately` in `tests/unit/clients/data/test_client.py` create `DataServiceClient` with default `RetryConfig(max_retries=2)` but do NOT mock the retry sleep. Each 503 request triggers 2 retries with exponential backoff (likely 0.5s, 1.0s), and 5-6 requests are made.
**Impact**: Top 2 tests alone cost 30s.
**Recommended**: Add `retry=RetryConfig(max_retries=0)` to these tests (same pattern already used by the half-open/probe tests in the same class):
```python
config = DataServiceConfig(
    circuit_breaker=CircuitBreakerConfig(
        enabled=True, failure_threshold=5,
        recovery_timeout=30.0, half_open_max_calls=1,
    ),
    retry=RetryConfig(max_retries=0),  # Isolate circuit breaker from retry
)
```

### Issue 4: Pacing Tests Use Real asyncio.sleep (MEDIUM IMPACT)

**Current**: Several tests in `test_paced_fetch.py` and `test_adversarial_pacing.py` use real `asyncio.sleep` for checkpoint/pacing tests instead of mocking it.
**Impact**: ~17s across 11 tests.
**Recommended**: Mock `asyncio.sleep` consistently (many tests in the same files already do this). The pattern exists at line 118 of `test_paced_fetch.py`:
```python
with patch("autom8_asana.dataframes.builders.progressive.asyncio.sleep") as mock_sleep:
```

### Issue 5: TTL Expiry Tests Use Real time.sleep (LOW IMPACT)

**Current**: `test_memory_backend.py` uses `time.sleep(1.1)` (3 occurrences) to test TTL expiration.
**Impact**: ~3.3s across 3 tests.
**Recommended**: Use `freezegun` or mock `time.monotonic`/`time.time` to advance time without sleeping.

### Issue 6: No Fast-Feedback Subset Defined (MEDIUM IMPACT)

**Current**: No smoke test marker, no critical-path subset. Developers must run full suite (296s) or guess which tests matter.
**Recommended**: Define a `@pytest.mark.smoke` marker and tag ~50 critical-path tests. See proposal below.

### Issue 7: S3 Backend Tests Use Per-Test moto Fixture (LOW IMPACT)

**Current**: `test_s3_backend.py` (59 tests, 5.2s) creates `mock_aws()` context per test. The `setup` phase accounts for 96.8% of test time.
**Impact**: 5.2s.
**Recommended**: Use `session`-scoped moto mock with per-test bucket cleanup instead of full mock recreation.

### Issue 8: No Test Sharding for CI (INFO)

**Current**: No `pytest-split`, `pytest-xdist` remote, or CI matrix sharding configured.
**Recommended**: For CI pipelines, configure test splitting:
```yaml
# GitHub Actions example
strategy:
  matrix:
    shard: [1, 2, 3, 4]
steps:
  - run: pytest tests/ --splits 4 --group ${{ matrix.shard }}
```

### Issue 9: Markers Underutilized

**Current**: 69 marker usages across 17 files (mostly `@pytest.mark.slow` and `@pytest.mark.integration`).
**Impact**: Most slow/integration tests are not marked, so `-m "not slow"` is ineffective.
**Recommended**: Mark all tests in `test_entity_write_smoke.py`, `test_e2e_offer_write_proof.py`, and circuit breaker tests as `@pytest.mark.slow` or `@pytest.mark.integration`.

---

## Recommended Actions (Ordered by Estimated Time Savings)

| Priority | Action | Est. Savings | Effort |
|----------|--------|-------------|--------|
| **P0** | Module-scope TestClient for API tests | **~85s** (-29%) | Medium (fixture refactor, verify isolation) |
| **P0** | Disable retries in circuit breaker tests | **~30s** (-10%) | Trivial (add `retry=RetryConfig(max_retries=0)`) |
| **P1** | Install pytest-xdist, run `-n auto` | **~220s** (-74%) | Low (install + verify isolation) |
| **P1** | Mock asyncio.sleep in remaining pacing tests | **~14s** (-5%) | Low (pattern already exists in same files) |
| **P2** | Mock time.sleep in TTL expiry tests | **~3s** (-1%) | Low |
| **P2** | Session-scope moto for S3 tests | **~4s** (-1%) | Medium |
| **P2** | Add `@pytest.mark.slow` to all >2s tests | 0s (enables `-m "not slow"`) | Trivial |
| **P3** | Define `@pytest.mark.smoke` fast-feedback subset | 0s (enables `pytest -m smoke`) | Low |
| **P3** | Configure CI test sharding | 0s (CI-only improvement) | Medium |

**Projected improvement** (P0+P1 combined): Full suite from **296s -> ~25-40s** (with xdist 8-workers on serial ~80s base after fixture fixes).

---

## Fast-Feedback Subset Proposal

50 tests covering all 25+ modules, estimated execution time **<3s** (32ms test time + ~2s collection overhead). Suitable for agentic dev loops and pre-commit validation.

### Selection Criteria
- One test per source module, covering critical paths
- All under 50ms individually
- No TestClient, no live API, no real sleep
- Spread across: models, persistence, cache, automation, dataframes, services, query, resolution, auth, clients, transport, core, lifecycle, lambda, metrics, search, detection, patterns

### Proposed Tests

```bash
# Save as tests/smoke_tests.txt or use with: pytest $(cat tests/smoke_tests.txt)

# Auth
tests/test_auth/test_audit.py::TestS2SAuditEntry::test_entry_to_dict
tests/test_auth/test_bot_pat.py::TestGetBotPat::test_get_bot_pat_cached
tests/test_auth/test_dependencies.py::TestAuthContext::test_auth_context_jwt_mode
tests/test_auth/test_dual_mode.py::TestAuthMode::test_jwt_value
tests/test_auth/test_jwt_validator.py::TestResetAuthClient::test_reset_is_idempotent

# API layer (model-only, no TestClient)
tests/unit/api/test_error_helpers.py::TestFormatConsistencyAcrossRoutes::test_tasks_pattern_via_raise_service_error
tests/unit/api/test_client_pool.py::TestTokenHashing::test_hash_is_16_chars

# Automation
tests/unit/automation/test_validation.py::TestValidationResultEdgeCases::test_defaults_are_empty_lists
tests/unit/automation/events/test_types.py::TestEventTypeStrCompatibility::test_construct_from_string

# Cache
tests/unit/cache/test_adversarial.py::TestStalenessEdgeCases::test_partition_empty_dict
tests/unit/cache/dataframe/test_schema_version_validation.py::TestSchemaVersionLookup::test_lookup_offer_schema_version

# Clients
tests/unit/clients/test_name_resolver.py::TestNameResolverLooksLikeGid::test_looks_like_gid_false_for_names
tests/unit/clients/data/test_client.py::TestMaskCanonicalKey::test_returns_malformed_key_unchanged

# Core
tests/unit/core/test_project_registry.py::TestParityWithLifecycleYaml::test_sales_yaml_parity
tests/unit/core/test_exceptions.py::TestHierarchy::test_transport_error_is_autom8_error

# Dataframes
tests/unit/dataframes/test_unit_schema.py::TestUnitSchemaStructure::test_task_type_is_unit
tests/unit/dataframes/test_freshness.py::TestComputeGidHash::test_stable_across_calls

# Detection
tests/unit/detection/test_detection_cache.py::TestEntryTypeDetection::test_entry_type_detection_is_string_enum

# Lambda handlers
tests/unit/lambda_handlers/test_insights_export.py::TestHandlerRegistration::test_importable_from_package
tests/unit/lambda_handlers/test_cache_warmer.py::TestShouldExitEarly::test_returns_true_when_remaining_time_is_zero

# Lifecycle
tests/unit/lifecycle/test_config.py::TestPydanticModels::test_seeding_config_defaults
tests/unit/lifecycle/test_reopen.py::TestReopenResultStructure::test_default_field_values

# Metrics
tests/unit/metrics/test_adversarial.py::TestMetricExprAdversarial::test_sql_injection_agg
tests/unit/metrics/test_resolve.py::TestResolveMetricScope::test_already_resolved

# Models
tests/unit/models/business/test_activity.py::TestActivityPriority::test_is_tuple
tests/unit/models/business/test_cascading_registry.py::TestModuleExports::test_exports_from_fields_module

# Patterns
tests/unit/patterns/test_error_classification.py::TestRecoveryHint::test_404_hint_mentions_gid
tests/unit/patterns/test_async_method.py::TestAsyncMethodDecorator::test_descriptor_class_access

# Persistence
tests/unit/persistence/test_exceptions.py::TestSessionClosedError::test_default_message
tests/unit/persistence/test_models.py::TestSaveResultRetryableHelpers::test_has_retryable_failures_false_when_empty

# Query
tests/unit/query/test_models.py::TestRowsRequestSugar::test_dict_passthrough
tests/unit/query/test_hierarchy.py::TestGetJoinKey::test_tc_h006_no_relationship

# Resolution
tests/unit/resolution/test_result.py::TestResolutionResult::test_success_property_partial
tests/unit/resolution/test_budget.py::TestApiBudget::test_consume_default_count

# Search
tests/unit/search/test_models.py::TestFieldCondition::test_in_operator_with_list
tests/unit/search/test_service.py::TestSearchServiceInit::test_init_with_null_cache

# Services
tests/unit/services/test_entity_discovery.py::TestValidateFieldType::test_boolean_type_rejects_invalid
tests/unit/services/test_service_errors.py::TestInvalidFieldError::test_error_code

# Transport
tests/unit/transport/test_response_handler.py::TestResponseHandler::test_handles_429_rate_limit

# Top-level unit
tests/unit/test_auth_providers.py::TestSecretsManagerAuthProvider::test_build_secret_path_custom_pattern
tests/unit/test_batch.py::TestBatchResult::test_batch_result_failure_404
tests/unit/test_batch_adversarial.py::TestBatchResultPropertyEdgeCases::test_status_204_is_success
tests/unit/test_cascade_registry_audit.py::test_registry_is_not_empty
tests/unit/test_client.py::TestTokenAuthProvider::test_whitespace_token_rejected
tests/unit/test_common_models.py::TestNameGidEquality::test_equality_with_name_vs_none
tests/unit/test_config_validation.py::TestConnectionPoolConfig::test_default_values_are_valid
tests/unit/test_exceptions.py::TestErrorClassHierarchy::test_autom8_error_is_base

# Cross-cutting
tests/services/test_gid_lookup.py::TestGidLookupIndexStaleDetection::test_exactly_at_ttl_not_stale
tests/qa/test_poc_query_evaluation.py::TestCategory14PredicateDepthCalculation::test_single_comparison_depth_1
tests/benchmarks/test_insights_benchmark.py::TestBatchRequestBenchmark::test_batch_10_pvps_latency
```

### Run Command
```bash
# Full smoke suite (~3s)
.venv/bin/pytest -m smoke --timeout=10 -q

# Or direct execution from file:
.venv/bin/pytest $(cat tests/smoke_tests.txt) --timeout=10 -q
```

---

## Appendix: Key Architectural Observations

1. **Two autouse fixtures in root conftest** (`reset_settings_singleton`, `reset_registries`) run for every test. Combined they import 4 registry modules and call 8 reset methods. At 10,452 tests, this adds ~5-10s of cumulative overhead. Consider lazy imports or conditional reset.

2. **TestClient is the single largest bottleneck**. FastAPI's `TestClient.__enter__` triggers the ASGI lifespan (startup handlers), and `__exit__` triggers shutdown. The `create_app()` factory builds middleware stacks, dependency graphs, etc. Module-scoping this would be transformative.

3. **Integration tests against live Asana API** (`test_entity_write_smoke.py`) are correctly marked `@pytest.mark.integration` but contribute 49.5s. These should run only in CI or on explicit opt-in (`-m integration`).

4. **No coverage during profiling** -- `pytest-cov` was not active during these runs. Coverage instrumentation typically adds 10-20% overhead. Budget ~350s for full suite with coverage.
