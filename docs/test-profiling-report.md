# Test Suite Profiling Report

## Summary

- **Total tests**: 7357
- **Total duration (sum of means)**: 141.4s
- **Mean per test**: 19.2ms
- **Median per test**: 0.8ms
- **P90**: 7.5ms
- **P95**: 20.4ms
- **P99**: 158.3ms
- **Std dev**: 325.5ms
- **Slow threshold**: 500.0ms

## By Category

| Category | Count | Sum (s) | Mean (ms) | Median (ms) | P95 (ms) | Max (ms) |
|----------|-------|---------|-----------|-------------|----------|----------|
| api | 305 | 21.6 | 70.8 | 22.9 | 335.8 | 1390.4 |
| benchmarks | 8 | 1.3 | 158.6 | 92.5 | 370.3 | 370.3 |
| other | 491 | 4.3 | 8.8 | 0.5 | 9.5 | 695.3 |
| unit | 6427 | 106.4 | 16.6 | 0.8 | 11.4 | 16980.7 |
| validation | 126 | 7.8 | 62.0 | 2.1 | 23.0 | 7108.6 |

## Top 30 Slowest Tests

| # | Mean (ms) | Std (ms) | Root Causes | Test |
|---|-----------|----------|-------------|------|
| 1 | 16981 | 204 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestCircuitBreaker::test_circuit_open_raises_immediately` |
| 2 | 16656 | 1632 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestCircuitBreaker::test_circuit_opens_after_threshold` |
| 3 | 7109 | 5686 | - | `tests/validation/persistence/test_performance.py::TestMemoryOverhead::test_memory_overhead_estimation` |
| 4 | 4271 | 1415 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_timeout` |
| 5 | 4070 | 634 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestObservabilityMetrics::test_error_metrics_emitted_on_timeout` |
| 6 | 3788 | 1640 | sleep, concurrency | `tests/unit/cache/test_adversarial.py::TestMemoryManagement::test_no_memory_leak_on_repeated_clear` |
| 7 | 3709 | 586 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_504_error` |
| 8 | 3606 | 519 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_timeout_maps_to_service_error` |
| 9 | 3282 | 834 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_503_error` |
| 10 | 3012 | 1625 | dataframe-ops, subprocess | `tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_no_args` |
| 11 | 2950 | 625 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_502_maps_to_service_error` |
| 12 | 2778 | 689 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_504_maps_to_service_error` |
| 13 | 2616 | 416 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_502_error` |
| 14 | 2312 | 350 | sleep, http-client | `tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_503_maps_to_service_error` |
| 15 | 2302 | 76 | dataframe-ops, subprocess | `tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_list` |
| 16 | 2141 | 632 | dataframe-ops, subprocess | `tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_no_bucket_env` |
| 17 | 1961 | 356 | dataframe-ops, subprocess | `tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_help` |
| 18 | 1840 | 739 | dataframe-ops, subprocess | `tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_unknown_metric` |
| 19 | 1839 | 504 | dataframe-ops, subprocess | `tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_list_and_metric_name` |
| 20 | 1390 | 208 | - | `tests/api/test_routes_admin.py::TestAdminRefreshAllTypes::test_admin_refresh_all_types` |
| 21 | 1296 | 510 | http-client | `tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_returns_expected_fields` |
| 22 | 1202 | 287 | http-client | `tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_no_auth_required` |
| 23 | 1191 | 85 | sleep | `tests/unit/cache/test_memory_backend.py::TestInMemoryCacheProvider::test_ttl_expiration` |
| 24 | 1177 | 97 | sleep | `tests/unit/cache/test_memory_backend.py::TestEnhancedInMemoryCacheProvider::test_versioned_ttl_expiration` |
| 25 | 1148 | 278 | http-client | `tests/api/test_routes_admin_adversarial.py::TestAdminRefreshConcurrency::test_multiple_rapid_requests_all_accepted` |
| 26 | 1140 | 61 | sleep | `tests/unit/cache/test_memory_backend.py::TestInMemoryCacheProvider::test_explicit_ttl_override` |
| 27 | 1132 | 43 | - | `tests/api/test_routes_admin.py::TestAdminRefreshValidatesEntityType::test_admin_refresh_accepts_all_valid_entity_types` |
| 28 | 1051 | 100 | http-client | `tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_reports_bot_pat_configured` |
| 29 | 921 | 66 | http-client | `tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_reports_bot_pat_not_configured` |
| 30 | 695 | 444 | dataframe-ops, http-client | `tests/integration/test_entity_resolver_e2e.py::TestHealthEndpoint::test_health_endpoint_returns_ok` |

## Root Cause Breakdown (slow tests)

Tests above 500.0ms threshold: **35**

| Root Cause | Count | Total Duration (s) |
|------------|-------|-------------------|
| http-client | 20 | 71.3 |
| sleep | 16 | 71.2 |
| dataframe-ops | 10 | 15.6 |
| subprocess | 6 | 13.1 |
| concurrency | 2 | 4.5 |

## Marker Recommendations

Tests to mark `@pytest.mark.slow` (>500.0ms mean):

```
    16981ms  tests/unit/clients/data/test_client.py::TestCircuitBreaker::test_circuit_open_raises_immediately
    16656ms  tests/unit/clients/data/test_client.py::TestCircuitBreaker::test_circuit_opens_after_threshold
     7109ms  tests/validation/persistence/test_performance.py::TestMemoryOverhead::test_memory_overhead_estimation
     4271ms  tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_timeout
     4070ms  tests/unit/clients/data/test_client.py::TestObservabilityMetrics::test_error_metrics_emitted_on_timeout
     3788ms  tests/unit/cache/test_adversarial.py::TestMemoryManagement::test_no_memory_leak_on_repeated_clear
     3709ms  tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_504_error
     3606ms  tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_timeout_maps_to_service_error
     3282ms  tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_503_error
     3012ms  tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_no_args
     2950ms  tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_502_maps_to_service_error
     2778ms  tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_504_maps_to_service_error
     2616ms  tests/unit/clients/data/test_client.py::TestStaleFallback::test_stale_fallback_on_502_error
     2312ms  tests/unit/clients/data/test_client.py::TestGetInsightsAsyncErrorMapping::test_503_maps_to_service_error
     2302ms  tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_list
     2141ms  tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_no_bucket_env
     1961ms  tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_help
     1840ms  tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_unknown_metric
     1839ms  tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_list_and_metric_name
     1390ms  tests/api/test_routes_admin.py::TestAdminRefreshAllTypes::test_admin_refresh_all_types
     1296ms  tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_returns_expected_fields
     1202ms  tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_no_auth_required
     1191ms  tests/unit/cache/test_memory_backend.py::TestInMemoryCacheProvider::test_ttl_expiration
     1177ms  tests/unit/cache/test_memory_backend.py::TestEnhancedInMemoryCacheProvider::test_versioned_ttl_expiration
     1148ms  tests/api/test_routes_admin_adversarial.py::TestAdminRefreshConcurrency::test_multiple_rapid_requests_all_accepted
     1140ms  tests/unit/cache/test_memory_backend.py::TestInMemoryCacheProvider::test_explicit_ttl_override
     1132ms  tests/api/test_routes_admin.py::TestAdminRefreshValidatesEntityType::test_admin_refresh_accepts_all_valid_entity_types
     1051ms  tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_reports_bot_pat_configured
      921ms  tests/api/test_health.py::TestS2SHealthEndpoint::test_s2s_health_reports_bot_pat_not_configured
      695ms  tests/integration/test_entity_resolver_e2e.py::TestHealthEndpoint::test_health_endpoint_returns_ok
      684ms  tests/unit/cache/test_concurrency.py::TestModificationCheckCacheConcurrency::test_concurrent_cleanup
      668ms  tests/integration/test_entity_resolver_e2e.py::TestEntityResolverE2E::test_resolve_batch_preserves_order
      659ms  tests/api/test_startup_preload.py::TestPreloadDataframeCacheFunction::test_preload_loads_index_from_s3_and_does_incremental_catchup
      586ms  tests/api/test_routes_admin_adversarial.py::TestAdminRefreshAdversarialInputs::test_force_full_rebuild_non_boolean_coerced
      509ms  tests/integration/test_entity_resolver_e2e.py::TestEntityResolverE2E::test_resolve_unit_not_found_returns_error
```

### By File (for applying markers)

**tests/api/test_health.py** (4 slow tests, 4.5s total)
  - `test_s2s_health_returns_expected_fields` (1296ms)
  - `test_s2s_health_no_auth_required` (1202ms)
  - `test_s2s_health_reports_bot_pat_configured` (1051ms)
  - `test_s2s_health_reports_bot_pat_not_configured` (921ms)

**tests/api/test_routes_admin.py** (2 slow tests, 2.5s total)
  - `test_admin_refresh_all_types` (1390ms)
  - `test_admin_refresh_accepts_all_valid_entity_types` (1132ms)

**tests/api/test_routes_admin_adversarial.py** (2 slow tests, 1.7s total)
  - `test_multiple_rapid_requests_all_accepted` (1148ms)
  - `test_force_full_rebuild_non_boolean_coerced` (586ms)

**tests/api/test_startup_preload.py** (1 slow tests, 0.7s total)
  - `test_preload_loads_index_from_s3_and_does_incremental_catchup` (659ms)

**tests/integration/test_entity_resolver_e2e.py** (3 slow tests, 1.9s total)
  - `test_health_endpoint_returns_ok` (695ms)
  - `test_resolve_batch_preserves_order` (668ms)
  - `test_resolve_unit_not_found_returns_error` (509ms)

**tests/unit/cache/test_adversarial.py** (1 slow tests, 3.8s total)
  - `test_no_memory_leak_on_repeated_clear` (3788ms)

**tests/unit/cache/test_concurrency.py** (1 slow tests, 0.7s total)
  - `test_concurrent_cleanup` (684ms)

**tests/unit/cache/test_memory_backend.py** (3 slow tests, 3.5s total)
  - `test_ttl_expiration` (1191ms)
  - `test_versioned_ttl_expiration` (1177ms)
  - `test_explicit_ttl_override` (1140ms)

**tests/unit/clients/data/test_client.py** (11 slow tests, 63.2s total)
  - `test_circuit_open_raises_immediately` (16981ms)
  - `test_circuit_opens_after_threshold` (16656ms)
  - `test_stale_fallback_on_timeout` (4271ms)
  - `test_error_metrics_emitted_on_timeout` (4070ms)
  - `test_stale_fallback_on_504_error` (3709ms)
  - `test_timeout_maps_to_service_error` (3606ms)
  - `test_stale_fallback_on_503_error` (3282ms)
  - `test_502_maps_to_service_error` (2950ms)
  - `test_504_maps_to_service_error` (2778ms)
  - `test_stale_fallback_on_502_error` (2616ms)
  - `test_503_maps_to_service_error` (2312ms)

**tests/unit/metrics/test_adversarial.py** (6 slow tests, 13.1s total)
  - `test_cli_no_args` (3012ms)
  - `test_cli_list` (2302ms)
  - `test_cli_no_bucket_env` (2141ms)
  - `test_cli_help` (1961ms)
  - `test_cli_unknown_metric` (1840ms)
  - `test_cli_list_and_metric_name` (1839ms)

**tests/validation/persistence/test_performance.py** (1 slow tests, 7.1s total)
  - `test_memory_overhead_estimation` (7109ms)

## Estimated Fast Suite Impact

- **Fast tests**: 7322 (99.5%)
- **Slow tests**: 35 (0.5%)
- **Fast suite duration (sum of means)**: 38.7s
- **Slow tests duration (sum of means)**: 102.7s
- **Duration reduction**: 72.6%
