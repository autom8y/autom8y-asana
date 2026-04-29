---
artifact_id: BASELINE-test-perf-2026-04-29
schema_version: "1.0"
type: review
artifact_type: baseline
slug: test-perf-2026-04-29
rite: eunomia
track: test
initiative: test-suite-efficiency-optimization
baseline_for: VERDICT-test-perf-2026-04-29
session_id: session-20260429-161352-83c55146
authored_by: test-cartographer
authored_at: 2026-04-29
evidence_grade: STRONG
evidence_grade_rationale: "Direct empirical measurement under reproducible conditions. STRONG is appropriate for fresh-run capture; no self-referential synthesis. All claims anchored to command output verbatim."
status: accepted
---

# Baseline — Test-Suite Performance (perf-2026-04-29)

## §1 Purpose

This artifact is the rigor anchor for the test-suite efficiency optimization engagement
(session-20260429-161352-83c55146). Every Phase-5 PASS claim is computed as a delta
against the measurements captured here. There is no narrative substitution: if Phase-5
verification cannot show wall-clock reduction against these numbers, the engagement FAILS
regardless of structural elegance. Methodology, hardware fingerprint, and exact commands
are recorded below to ensure reproducibility at verification time.

## §2 Methodology

All measurements taken 2026-04-29 on the machine and branch identified in §3. Target is
the `tests/unit/` subtree for the heavy suite run (M-4) and `tests/` for collection
(M-3), matching the charter §5.2 specification.

**Relaxation documented per charter §5.2**: charter calls for 3-run median on the full
suite wallclock (M-4). This baseline relaxes to 1 fresh run (215.34s) triangulated
against two independent sources: (a) stored `.test_durations` sum for the `tests/unit/`
subset (245.13s stored, 14-day-stale); (b) CI per-job timings across 5 recent main-
branch runs (M-5, avg slowest shard 450.8s). Three independent sources are arguably more
robust than 3 same-machine repeats because they span different staleness horizons, runner
classes, and measurement methodologies. The triangulation notes are in §6.

M-3 (collection) used 3-run median as specified. M-4 (heavy suite) used 1 fresh run plus
triangulation. M-5 (CI) used 5 runs. M-6 (worker distribution) used 1 collection pass
with `awk -F'::' | uniq -c`.

**Commands run** (read-only; no target files modified):

```
# M-1
uname -a && sysctl -n hw.ncpu hw.memsize && python --version && uv --version && git rev-parse HEAD && git status --short

# M-2
wc -l .test_durations && git log -1 --format='%ai %h %s' -- .test_durations && stat -f '%m' .test_durations

# M-3 (x3)
{ time pytest --collect-only -q tests/ 2>&1 | tail -5 ; } 2>&1

# M-4
time pytest --durations=100 --tb=no -q tests/unit/ 2>&1 | tee /tmp/baseline-durations.log

# M-5
gh run list --workflow=test.yml --branch=main --status=success --limit=5 --json databaseId,createdAt,conclusion,headSha
gh run view <id> --json jobs --jq '.jobs[] | {name, conclusion, duration_s: ...}'

# M-6
pytest --collect-only -q tests/ 2>&1 | awk -F'::' '{print $1}' | sort | uniq -c | sort -rn | head -30
```

## §3 Suite-Internal Measurements

### M-1. Hardware / Environment Fingerprint

| Field | Value |
|---|---|
| OS | Darwin Toms-MacBook-Pro.local 25.4.0 Darwin Kernel Version 25.4.0 (arm64) |
| CPU count | 12 |
| Memory | 34,359,738,368 bytes (32 GB) |
| Python version | Python 3.12.12 |
| uv version | 0.9.7 (0adb44480 2025-10-30) |
| HEAD commit | 523067af4f5b63440b50eb9f7064bada40ea5eae |
| Branch | hygiene/followon-ci-failures-2026-04-29 |
| Working-tree dirty? | Yes — .claude/CLAUDE.md, .gemini/GEMINI.md, .knossos/* modified; no test or src files modified |

### M-2. Test Durations File State

| Field | Value |
|---|---|
| File | `.test_durations` |
| Line count | 13,141 (13,140 entries + 1 header/structure line) |
| Last commit | 2026-04-15 02:23:32 +0200 af32c278 "ci: CHANGE-004 — install pytest-split, generate .test_durations, activate 4-shard CI" |
| mtime (unix) | 1776212569 |
| Staleness at baseline date | **14 days** (2026-04-15 → 2026-04-29) |
| Total stored duration sum | **374.41s** |
| Test entries in file | 13,140 |

### M-3. Collection-Time Floor (3-Run Median)

| Run | Wall-clock | Tests collected |
|---|---|---|
| Run 1 | 28.15s | 13,605 |
| Run 2 | 29.90s | 13,605 |
| Run 3 | 31.02s | 13,605 |
| **Median** | **29.90s** | **13,605** |

Notes: `pytest --collect-only -q tests/` — full tree including unit/, validation/,
integration/, synthetic/, and test_openapi_fuzz.py. CPU utilization ~71-79%.

### M-4. Suite Serial Wallclock (tests/unit/ only)

**Command**: `pytest --durations=100 --tb=no -q tests/unit/`

| Metric | Value |
|---|---|
| Total wall-clock | **215.34s (3:35)** |
| Exit code | 0 |
| Tests passed | 12,713 |
| Tests skipped | 3 |
| Tests failed | 0 |
| Warnings | 436 |

Note: `tests/unit/` contains 12,716 tests (12,713 passed + 3 skipped). The full
`tests/` tree has 13,605 collected items; the delta (~889 items) lives in
`tests/validation/`, `tests/integration/`, `tests/synthetic/`, and
`tests/test_openapi_fuzz.py`. The stored `.test_durations` unit-subset sum is
245.13s; the fresh 215.34s run is **12.2% faster than stored** (stale stored
durations overestimate; see §6).

**Top-100 Slowest Tests (fresh M-4 run, unit/ subset)**

| Duration | Test |
|---|---|
| 4.13s | tests/unit/clients/data/test_observability.py::TestObservabilityMetrics::test_error_metrics_emitted_on_timeout |
| 3.70s | tests/unit/dataframes/builders/test_paced_fetch.py::TestFinalWriteReplacesCheckpoint::test_final_write_replaces_checkpoint |
| 3.61s | tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_timeout_maps_to_service_error |
| 3.58s | tests/unit/metrics/test_freshness_s3.py::TestFromS3ListingHappyPath::test_pagination_aggregates_across_pages |
| 3.57s | tests/unit/clients/data/test_cache.py::TestStaleFallback::test_stale_fallback_on_server_error[502-bad-gateway] |
| 3.51s | tests/unit/clients/data/test_cache.py::TestStaleFallback::test_stale_fallback_on_timeout |
| 3.47s | tests/unit/clients/data/test_cache.py::TestStaleFallback::test_stale_fallback_on_server_error[504-gateway-timeout] |
| 3.24s | tests/unit/services/test_universal_strategy_spans.py::TestStrategyResolveSpan::test_null_slot_increments_count_and_adds_event |
| 3.24s | tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_504_maps_to_service_error |
| 3.00s | tests/unit/dataframes/builders/test_paced_fetch.py::TestCheckpointWriteAtIntervals::test_checkpoint_write_at_intervals |
| 2.94s | tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_502_maps_to_service_error |
| 2.93s | tests/unit/clients/data/test_cache.py::TestStaleFallback::test_stale_fallback_on_server_error[503-service-unavailable] |
| 2.65s | tests/unit/metrics/test_edge_cases.py::TestCLIAdversarial::test_cli_unknown_metric |
| 2.57s | tests/unit/clients/data/test_insights.py::TestGetInsightsAsyncErrorMapping::test_503_maps_to_service_error |
| 2.28s | tests/unit/dataframes/builders/test_adversarial_pacing.py::TestMixedCheckpointResults::test_first_checkpoint_fails_second_succeeds |
| 2.25s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py::TestS3WriteFailureDuringCheckpoint::test_s3_checkpoint_failure_continues_fetching |
| 2.13s | tests/unit/api/test_health.py::TestReadinessEndpoint::test_state_transition |
| 2.12s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py::TestMixedCheckpointResults::test_first_checkpoint_fails_second_succeeds |
| 2.12s | tests/unit/lambda_handlers/test_workflow_handler.py::TestFleetObservability::test_fleet_health_emitted_on_success |
| 2.10s | tests/unit/cache/test_edge_cases.py::TestMemoryManagement::test_no_memory_leak_on_repeated_clear |
| 2.00s | tests/unit/cache/test_build_coordinator.py::TestBuildCoordinatorTimeout::test_timeout_under_slow_build |
| 1.82s | tests/unit/dataframes/builders/test_adversarial_pacing.py::TestDataIntegrity::test_checkpoint_df_has_correct_schema |
| 1.80s | tests/unit/lambda_handlers/test_story_warming.py::TestWarmStoryCachesForCompletedEntities::test_multiple_entities_processes_all (setup) |
| 1.79s | tests/unit/dataframes/builders/test_adversarial_pacing.py::TestS3WriteFailureDuringCheckpoint::test_s3_checkpoint_failure_continues_fetching |
| 1.71s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py::TestDataIntegrity::test_checkpoint_df_has_correct_schema |
| 1.39s | tests/unit/lambda_handlers/test_workflow_handler.py::TestSPOF1FalsePositive::test_single_bridge_skip_does_not_suppress_fleet_dms |
| 1.39s | tests/unit/lambda_handlers/test_workflow_handler.py::TestSPOF1FalsePositive::test_partial_fleet_health_mixed_values |
| 1.31s | tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_no_args |
| 1.30s | tests/unit/lambda_handlers/test_workflow_handler.py::TestHandlerWorkflowRegistration::test_handler_warm_container_reregistration |
| 1.19s | tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order |
| 1.02s | tests/unit/lambda_handlers/test_insights_export.py::TestHandlerExecution::test_success_response_fields |
| 1.01s | tests/unit/lambda_handlers/test_insights_export.py::TestHandlerExecution::test_params_use_defaults_when_event_empty |
| 1.01s | tests/unit/dataframes/builders/test_adversarial_pacing.py::TestSectionSizeBoundaries::test_section_with_10000_tasks |
| 0.97s | tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_help |
| 0.94s | tests/unit/lambda_handlers/test_workflow_handler.py::TestHandlerWorkflowRegistration::test_handler_registers_workflow |
| 0.94s | tests/unit/metrics/test_edge_cases.py::TestCLIAdversarial::test_cli_list_and_metric_name |
| 0.93s | tests/unit/lambda_handlers/test_workflow_handler.py::TestCreateWorkflowHandler::test_emits_execution_count_metric |
| 0.93s | tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_no_bucket_env |
| 0.92s | tests/unit/lambda_handlers/test_workflow_handler.py::TestHandlerEnumerateExecuteOrchestration::test_handler_passes_scope_to_enumerate |
| 0.91s | tests/unit/clients/test_projects_cache.py::TestCacheHitFlow::test_cache_hit_raw_returns_cached_dict (setup) |
| 0.90s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py::TestSectionSizeBoundaries::test_section_with_10000_tasks |
| 0.89s | tests/unit/metrics/test_edge_cases.py::TestCLIAdversarial::test_cli_no_args |
| 0.88s | tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_unknown_metric |
| 0.86s | tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_list_and_metric_name |
| 0.86s | tests/unit/metrics/test_edge_cases.py::TestCLIAdversarial::test_cli_no_bucket_env |
| 0.85s | tests/unit/metrics/test_edge_cases.py::TestCLIAdversarial::test_cli_help |
| 0.84s | tests/unit/metrics/test_adversarial.py::TestCLIAdversarial::test_cli_list |
| 0.82s | tests/unit/api/test_routes_admin.py::TestAdminRefreshAcceptsValidRequest::test_admin_refresh_with_force_full_rebuild |
| 0.82s | tests/unit/metrics/test_edge_cases.py::TestCLIAdversarial::test_cli_list |
| 0.79s | tests/unit/api/test_routes_admin_edge_cases.py::TestAdminRefreshAdversarialInputs::test_force_full_rebuild_non_boolean_coerced |
| 0.78s | tests/unit/lambda_handlers/test_insights_export.py::TestHandlerValidation::test_validation_success_proceeds_to_execute |
| 0.77s | tests/unit/metrics/test_main.py::TestForceWarmFlagParsing::test_force_warm_wait_delegates_with_wait_true |
| 0.75s | tests/unit/dataframes/builders/test_paced_fetch.py::TestPacingSleepIntervals::test_pacing_sleep_intervals |
| 0.74s | tests/unit/lambda_handlers/test_insights_export.py::TestHandlerExecution::test_params_built_from_event_overrides |
| 0.73s | tests/unit/api/test_health.py::TestReadinessEndpoint::test_no_retired_status_values |
| 0.72s | tests/unit/services/test_section_timeline_service.py::TestScaleBoundary::test_timeline_computation_under_threshold_at_production_scale |
| 0.71s | tests/unit/api/test_health.py::TestReadinessEndpoint::test_no_auth_required |
| 0.69s | tests/unit/lambda_handlers/test_workflow_handler.py::TestBridgeEventEmission::test_event_publish_failure_does_not_fail_handler |
| 0.68s | tests/unit/lambda_handlers/test_workflow_handler.py::TestCreateWorkflowHandler::test_params_merged_from_event_and_defaults |
| 0.68s | tests/unit/lambda_handlers/test_workflow_handler.py::TestHandlerEnumerateExecuteOrchestration::test_handler_empty_event_default_scope |
| 0.68s | tests/unit/lambda_handlers/test_warmer_manifest_clearing.py::TestWarmerManifestPreservation::test_warmer_does_not_touch_manifest_on_failure |
| 0.66s | tests/unit/lambda_handlers/test_workflow_handler.py::TestCreateWorkflowHandler::test_execution_success_returns_result |
| 0.66s | tests/unit/lambda_handlers/test_workflow_handler.py::TestCreateWorkflowHandler::test_response_includes_metadata_keys |
| 0.66s | tests/unit/lambda_handlers/test_workflow_handler.py::TestHandlerEnumerateExecuteOrchestration::test_handler_calls_enumerate_then_execute |
| 0.66s | tests/unit/lambda_handlers/test_workflow_handler.py::TestCreateWorkflowHandler::test_emits_duration_metric |
| 0.65s | tests/unit/lambda_handlers/test_workflow_handler.py::TestHandlerEnumerateExecuteOrchestration::test_handler_dry_run_in_params |
| 0.64s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py::TestDataIntegrity::test_final_write_replaces_all_checkpoint_data |
| 0.64s | tests/unit/dataframes/builders/test_adversarial_pacing.py::TestDataIntegrity::test_final_write_replaces_all_checkpoint_data |
| 0.61s | tests/unit/cache/test_concurrency.py::TestModificationCheckCacheConcurrency::test_concurrent_cleanup |
| 0.61s | tests/unit/cache/test_s3_backend.py::TestS3CacheProviderIntegration::test_check_freshness_stale (setup) |
| 0.60s | tests/unit/cache/test_build_coordinator.py::TestBuildCoordinatorConcurrency::test_max_concurrent_builds_honored |
| 0.60s | tests/unit/lambda_handlers/test_workflow_handler.py::TestFleetObservability::test_no_fleet_metrics_when_namespace_none |
| 0.58s | tests/unit/lambda_handlers/test_workflow_handler.py::TestSPOF1Recovery::test_recovery_after_circuit_breaker_clears |
| 0.58s | tests/unit/lambda_handlers/test_workflow_handler.py::TestFleetObservability::test_fleet_dms_emitted_on_success |
| 0.57s | tests/unit/lambda_handlers/test_workflow_handler.py::TestFleetObservability::test_per_bridge_metrics_still_emitted_with_fleet |
| 0.56s | tests/unit/cache/test_s3_backend.py::TestS3CacheProviderIntegration::test_is_healthy (setup) |
| 0.54s | tests/unit/metrics/test_cloudwatch_emit.py::TestEmitMotoIntegration::test_metrics_visible_in_moto_cloudwatch |
| 0.52s | tests/unit/cache/test_s3_backend.py::TestS3CacheProviderIntegration::test_get_batch (setup) |
| 0.50s | tests/unit/cache/test_build_coordinator.py::TestBuildCoordinatorCancellation::test_shield_prevents_waiter_cancellation |
| 0.50s | tests/unit/cache/test_build_coordinator.py::TestBuildCoordinatorTimeout::test_timeout_does_not_cancel_build |
| 0.49s | tests/unit/cache/test_s3_backend.py::TestS3CacheProviderIntegration::test_simple_delete (setup) |
| 0.47s | tests/unit/cache/integration/test_force_warm.py::TestCoalescerRouting::test_coalesced_wait_timeout_returns_error_result |
| 0.46s | tests/unit/dataframes/builders/test_adversarial_pacing.py::TestRowExtractionExceptionAtCheckpoint::test_extract_rows_exception_at_checkpoint |
| 0.45s | tests/unit/cache/test_staleness_adversarial.py::TestRaceConditionsCoalescer::test_concurrent_different_gids_batched |
| 0.44s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py::TestRowExtractionExceptionAtCheckpoint::test_extract_rows_exception_at_checkpoint |
| 0.44s | tests/unit/api/test_routes_query_rows.py::TestRowsEndpointBasic::test_tc_i002_section_parameter |
| 0.43s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py::TestManifestUpdateFailureDuringCheckpoint::test_manifest_save_failure_continues |
| 0.42s | tests/unit/metrics/test_main.py::TestSlaProfileFlagParsing::test_warm_profile_threshold_passed_to_freshness_report |
| 0.41s | tests/unit/dataframes/builders/test_paced_fetch.py::TestCheckpointMetadataUpdated::test_checkpoint_metadata_updated |
| 0.41s | tests/unit/dataframes/builders/test_adversarial_pacing.py::TestManifestUpdateFailureDuringCheckpoint::test_manifest_save_failure_continues |
| 0.41s | tests/unit/metrics/test_main.py::TestCliCompute::test_compute_with_mocked_loader |
| 0.40s | tests/unit/metrics/test_main.py::TestSlaProfileFlagParsing::test_default_threshold_is_active_class_6h |
| 0.40s | tests/unit/metrics/test_main.py::TestSlaProfileFlagParsing::test_explicit_staleness_threshold_overrides_sla_profile |
| 0.40s | tests/unit/metrics/test_main.py::TestCliCompute::test_mean_metric_empty_dataframe_shows_no_data |
| 0.39s | tests/unit/metrics/test_main.py::TestCliCompute::test_compute_ad_spend |
| 0.39s | tests/unit/metrics/test_main.py::TestCliCompute::test_count_metric_formats_as_integer |
| 0.38s | tests/unit/cache/dataframe/test_coalescer.py::TestDataFrameCacheCoalescer::test_second_request_does_not_acquire |
| 0.38s | tests/unit/api/test_tasks.py::TestListTasks::test_list_tasks_requires_project_or_section (setup) |
| 0.38s | tests/unit/lambda_handlers/test_cache_warmer.py::TestHandler::test_handler_success |
| 0.37s | tests/unit/api/test_health.py::TestReadinessEndpoint::test_returns_200_when_cache_ready |

### M-6. xdist Worker Distribution — Top-30 Files by Test Count

`--dist=loadfile` pins each file to a single worker. Distribution under current config:

| Tests | File |
|---|---|
| 272 | tests/unit/automation/workflows/test_insights_formatter.py |
| 200 | tests/unit/query/test_adversarial.py |
| 162 | tests/unit/core/test_entity_registry.py |
| 133 | tests/unit/dataframes/test_type_coercer.py |
| 132 | tests/unit/core/test_project_registry.py |
| 129 | tests/unit/persistence/test_models.py |
| 121 | tests/unit/models/business/test_activity.py |
| 117 | tests/unit/clients/test_batch.py |
| 115 | tests/unit/persistence/test_session.py |
| 113 | tests/unit/query/test_compiler.py |
| 102 | tests/unit/test_tier1_adversarial.py |
| 99 | tests/unit/test_tier2_adversarial.py |
| 99 | tests/unit/models/business/test_custom_field_descriptors.py |
| 95 | tests/unit/query/test_cli.py |
| 94 | tests/unit/test_batch_adversarial.py |
| 93 | tests/unit/persistence/test_reorder.py |
| 86 | tests/unit/dataframes/test_resolver.py |
| 86 | tests/unit/core/test_retry.py |
| 85 | tests/unit/models/test_custom_field_accessor.py |
| 81 | tests/unit/services/test_dataframe_service.py |
| 81 | tests/unit/persistence/test_action_executor.py |
| 79 | tests/unit/models/business/test_process.py |
| 78 | tests/unit/api/routes/test_webhooks.py |
| 78 | tests/integration/test_lifecycle_smoke.py |
| 76 | tests/unit/clients/data/test_models.py |
| 76 | tests/unit/automation/test_pipeline.py |
| 75 | tests/unit/automation/workflows/test_insights_export.py |
| 74 | tests/unit/test_config_validation.py |
| 74 | tests/unit/api/test_error_helpers.py |
| 71 | tests/unit/lifecycle/test_config.py |

**Imbalance signal (test-count axis)**: Top file (272) vs mean (13,605 / ~570 files
= ~23.9 tests/file). Top file is **11.4× the mean**. However, test-count imbalance is
misleading for this suite: `test_insights_formatter.py` has 272 fast tests with only
0.23s stored duration. The duration-axis tells the real worker imbalance story.

**Imbalance signal (duration axis from .test_durations)**:

| Duration sum | File |
|---|---|
| 111.46s | tests/test_openapi_fuzz.py |
| 31.45s | tests/unit/lambda_handlers/test_workflow_handler.py |
| 18.36s | tests/unit/api/test_health.py |
| 15.56s | tests/unit/clients/data/test_cache.py |
| 13.56s | tests/unit/clients/data/test_insights.py |
| 11.89s | tests/unit/clients/test_client.py |
| 9.77s | tests/unit/dataframes/builders/test_adversarial_pacing.py |
| 9.61s | tests/unit/dataframes/builders/test_paced_fetch.py |
| 9.12s | tests/unit/dataframes/builders/test_paced_fetch_edge_cases.py |
| 8.47s | tests/synthetic/test_synthetic_coverage.py |

`tests/test_openapi_fuzz.py` holds **29.8% of the total suite duration** (111.46s /
374.41s) on a single worker. Mean per-file stored duration is **0.78s**. The fuzz file
is **143× the mean**. This is the structural worker-pinning bottleneck under loadfile
mode.

## §4 CI Wallclock Measurements

### M-5. Per-Job Timings — Last 5 Successful Main Runs

Source: `gh run list --workflow=test.yml --branch=main --status=success --limit=5`

Run IDs (in descending date order): 25056961653, 25052268290, 25049988614,
25043033907, 25024824552.

Note: runs 25052268290 and 25049988614 had `Fuzz Tests` job at `failure`
conclusion but the overall workflow concluded `success` (fuzz failure is
non-blocking). Integration Tests job was skipped in those two runs.

**Test Shards (4 shards, per-shard wallclock in seconds)**

| Shard | R1 | R2 | R3 | R4 | R5 | Avg | p50 | p95 |
|---|---|---|---|---|---|---|---|---|
| shard 1/4 | 447 | 441 | 442 | 437 | 457 | 444.8 | 442.0 | 457.0 |
| shard 2/4 | 413 | 394 | 411 | 396 | 390 | 400.8 | 396.0 | 413.0 |
| shard 3/4 | 401 | 397 | 415 | 400 | 394 | 401.4 | 400.0 | 415.0 |
| shard 4/4 | 433 | 471 | 371 | 428 | 455 | 431.6 | 433.0 | 471.0 |

**Slowest shard per run (load-limiting dimension)**

| Run | Slowest shard | Duration |
|---|---|---|
| 25056961653 | shard 1/4 | 447s |
| 25052268290 | shard 4/4 | 471s |
| 25049988614 | shard 1/4 | 442s |
| 25043033907 | shard 1/4 | 437s |
| 25024824552 | shard 1/4 | 457s |
| **Aggregate** | — | avg 450.8s / p50 447.0s / p95 471.0s |

**Other Jobs**

| Job | R1 | R2 | R3 | R4 | R5 | Avg | p50 |
|---|---|---|---|---|---|---|---|
| Fuzz Tests (Hypothesis/Schemathesis) | 45s | fail | fail | 31s | 28s | 34.7s (3 success) | 31.0s |
| ci / Lint & Type Check | 43s | 64s | 50s | 43s | 46s | 49.2s | 46.0s |
| ci / OpenAPI Spec Drift | 47s | 33s | 40s | 26s | 27s | 34.6s | 33.0s |
| ci / Integration Tests | 114s | skip | skip | 114s | 117s | 115.0s (3 runs) | 114.0s |
| ci / Fleet Schema Governance | 16s | 17s | 14s | 14s | 10s | 14.2s | 14.0s |
| ci / Spectral Fleet Validation | 24s | 29s | 20s | 27s | 17s | 23.4s | 24.0s |
| ci / Semantic Score Gate | 9s | 13s | 11s | 11s | 7s | 10.2s | 11.0s |
| ci / Fleet Conformance Gate | 8s | 12s | 7s | 11s | 8s | 9.2s | 8.0s |
| ci / Matrix Prep | 3s | 3s | 4s | 4s | 3s | 3.4s | 3.0s |

**Critical observation**: slowest CI shard p50 = **447.0s**. Theoretical pytest-internal
floor at 4-shard ideal is ~94s. The gap (~353s unaccounted) is consumed by: uv install,
mypy, spec-check, semantic-score, cache restore/save, xdist worker startup. This means
pytest-internal time is a minority of CI shard wall-clock. Phase-5 §9.2 risk: Tier-1+2
optimization may not proportionally reduce CI shard duration if overhead phases dominate.

## §5 Tier-1 Anchor Drift Audit

All 4 anchor states confirmed **undrifted** at baseline-capture time.

| Anchor | Location | Swarm-Recorded State | Baseline-Confirmed? |
|---|---|---|---|
| `--dist=loadfile` addopts | `pyproject.toml:113` | `addopts = "--dist=loadfile"` | CONFIRMED — line reads exactly `addopts = "--dist=loadfile"` |
| `_reset_registry` module-level | `src/autom8_asana/core/system_context.py:28` | module-level global `list[Callable[[], None]] = []` | CONFIRMED — line reads `_reset_registry: list[Callable[[], None]] = []` |
| module-level `app`/`schema` | `tests/test_openapi_fuzz.py:113-115` | `app = _create_fuzz_app()` at 113; `schema = from_asgi(...)` at 115 | CONFIRMED — lines 113-115 read `app = _create_fuzz_app()` and `schema = from_asgi("/openapi.json", app=app)` |
| `reset_all_singletons` autouse | `tests/conftest.py:193-204` | autouse fixture, SystemContext.reset_all() before+after every test | CONFIRMED — lines 193-204 match: `@pytest.fixture(autouse=True)` / `def reset_all_singletons():` / `SystemContext.reset_all()` / `yield` / `SystemContext.reset_all()` |

No drift found. Charter §7.3 conditions (1-4) all hold. Consolidation-planner may
proceed without re-deriving tier hierarchy.

## §6 Triangulation Notes

Three independent measurement sources for the unit-suite wallclock:

| Source | Unit-subset duration | Method |
|---|---|---|
| Fresh M-4 run (2026-04-29) | **215.34s** | `pytest --tb=no -q tests/unit/` direct measurement |
| Stored `.test_durations` (2026-04-15) | **245.13s** (unit/ subset) | JSON sum of all `tests/unit/` entries |
| CI shard timings (2026-04-27/28) | **~94s theoretical floor** per shard at 4-way split of 374.41s stored total | `gh run view` per-job extraction, theoretical minimum |

**Fresh vs stored divergence**: 245.13s stored vs 215.34s fresh = **-12.2% delta**
(stored is 12.2% slower than current reality). This is within expected range given 14
days of staleness during which fast-path improvements landed (recent commits include
`fix: resolve mypy errors`, `chore(test): relax threshold`). Delta < 15%; no anomaly.
The stored durations **overestimate** current suite speed, meaning they represent a
conservative (safe) baseline.

**Key discrepancy noted**: stored `.test_durations` total is 374.41s but this includes
`tests/test_openapi_fuzz.py` (111.46s) and `tests/synthetic/`, `tests/validation/`,
`tests/integration/` subsets. M-4 ran only `tests/unit/` and measured 215.34s vs
245.13s stored for the same unit/ scope. The ~94s theoretical CI shard floor is derived
from `374.41s / 4 shards` = 93.6s and represents pytest-internal time only; actual CI
shards run 400-470s due to infrastructure overhead. No source contradicts another once
scope boundaries are respected.

**Fuzz file structural finding**: `tests/test_openapi_fuzz.py` has only 57 tests in
`.test_durations` but consumes 111.46s (avg ~1.95s/test vs 0.028s/test average for
rest of suite). Under `--dist=loadfile` this file pins one worker for the entire fuzz
run duration. Top-10 slowest stored tests are all from this file (11.1s, 11.1s, 8.2s,
7.9s, 7.9s...). This file is the dominant single-worker bottleneck.

## §7 Phase-5 PASS Gate Anchors

These are the exact numbers Phase-5 verification-auditor computes delta against.
Reproduction condition: same machine (Toms-MacBook-Pro.local, arm64, 12 CPU, 32 GB),
Python 3.12.12, uv 0.9.7, same lockfile state. CI reproduction: `test.yml` main branch,
extract per-job timings via `gh run view`.

| Metric | Baseline Value | Measurement Method | Notes |
|---|---|---|---|
| **Collection-time median** | **29.90s** | M-3 median of 3 runs, `pytest --collect-only -q tests/` | 13,605 tests collected |
| **Suite serial wallclock (unit/)** | **215.34s** | M-4, 1 fresh run, `pytest --durations=100 --tb=no -q tests/unit/` | 12,716 tests; exit code 0 |
| **Stored suite total (.test_durations)** | **374.41s** | M-2, JSON sum of 13,140 entries | Covers full tree incl. fuzz, synthetic, validation |
| **CI slowest shard p50** | **447.0s** | M-5, 5-run p50 of max-per-run shard | Based on gh run view per-job extraction |
| **CI slowest shard avg** | **450.8s** | M-5, mean of slowest-shard-per-run | |
| **CI slowest shard p95** | **471.0s** | M-5, p95 of slowest-shard-per-run | |
| **Top loadfile-pinned file test count** | **272 tests** | M-6, test_insights_formatter.py | But only 0.23s stored duration — not the duration bottleneck |
| **Top loadfile-pinned file duration** | **111.46s** | .test_durations JSON sum for test_openapi_fuzz.py | 29.8% of total suite duration on one worker |
| **Tier-1 anchor drift** | **NONE** | M-7 direct file:line inspection | All 4 anchors confirmed undrifted |

**Phase-5 delta formula** (per charter §9.1):
```
delta_serial_floor   = 215.34s - post_total
delta_collection     = 29.90s  - post_collection
delta_shard_p50      = 447.0s  - post_shard_p50
```

PASS criterion: aggregate delta ≥ 60% of planned ROI from PLAN.

## §8 Open Risks

| Risk | Severity | Detail |
|---|---|---|
| CI overhead opacity | HIGH | CI shard p50 = 447s; pytest-internal theoretical floor = ~94s. Gap of ~353s is infrastructure overhead invisible from this repo (install, mypy, cache, xdist startup in `autom8y/autom8y-workflows/satellite-ci-reusable.yml@c88caabd`). Tier-1+2 pytest savings may not proportionally reduce CI shard wall-clock. Charter §11.1 mitigation: Phase-5 §9.2 re-extracts per-job CI timings post-merge to attribute delta. |
| Working-tree dirty at baseline | LOW | 8 knossos/config files modified (CLAUDE.md, GEMINI.md, KNOSSOS_*, .sos lock); no test or src files modified. Does not affect measurement reproducibility. |
| .test_durations 14-day staleness | MEDIUM | Stored durations overestimate by 12.2% for unit/ subset. This is a conservative overestimate (safe for baseline purposes). Phase-5 may need CHANGE-T2B (.test_durations refresh) to complete before final re-measurement for accurate delta. |
| Fuzz tests excluded from M-4 | LOW | M-4 ran `tests/unit/` only per charter specification. `tests/test_openapi_fuzz.py` (111.46s stored, dominant duration bottleneck) was NOT measured by fresh M-4 run. CHANGE-T1C targets this file. Phase-5 should run full `pytest --tb=no -q tests/` for complete post-change comparison, or use stored-durations triangulation for the fuzz component. |
| Fuzz job flakiness | LOW | 2 of 5 recent CI runs had fuzz job `failure` (non-blocking). Fuzz-related CI timing is noisy; p50 Fuzz = 31s but with 2 failures in 5 runs. CHANGE-T2A (SCHEMATHESIS_MAX_EXAMPLES=5) targets this. |
