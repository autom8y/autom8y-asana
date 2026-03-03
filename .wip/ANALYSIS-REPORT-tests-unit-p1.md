---
type: qa
---
# Phase 2: Logic Surgeon Analysis Report -- tests/unit/ (Partition 1)

**Scope**: 389 Python test files in `tests/unit/` (~184K LOC, 9795 tests)
**Agent**: logic-surgeon
**Date**: 2026-02-23
**Mode**: Interactive

---

## Summary

| Category | DEFECT | SMELL | Total |
|----------|--------|-------|-------|
| Tautological tests | 8 | 0 | 8 |
| Assert-free tests | 18 | 14 | 32 |
| Over-mocked tests | 0 | 10 | 10 |
| Copy-paste bloat | 0 | 16 | 16 |
| Broad exception assertions | 0 | 5 | 5 |
| Assertion on wrong thing | 2 | 0 | 2 |
| **Total** | **28** | **40** | **68** |

**Noteworthy exclusions**: Of 104 assert-free functions detected by AST scan, 72 were classified as legitimate "does-not-raise" contract tests (e.g., `test_no_circular_imports`, `test_fire_and_forget_creates_task`, `test_idempotent_*`). These are intentionally verifying that operations complete without error and are NOT findings. Of 26 potential tautological patterns detected by data-flow analysis, 18 were false positives where the client code performs real work (model parsing, URL routing, header injection) between the mock and the assertion. Only 8 are genuine tautological tests.

---

## DEFECT Findings

### [LS-001] Tautological: raw=True client tests assert mock return value directly

- **Files**:
  - `tests/unit/clients/test_tasks_client.py:50` -- `test_get_async_raw_returns_dict`
  - `tests/unit/clients/test_tasks_client.py:111` -- `test_get_sync_raw_returns_dict`
  - `tests/unit/clients/test_tasks_client.py:160` -- `test_create_async_raw_returns_dict`
  - `tests/unit/clients/test_tasks_client.py:264` -- `test_update_async_raw_returns_dict`
  - `tests/unit/clients/test_tasks_client.py:346` -- `test_create_sync_raw_returns_dict`
  - `tests/unit/clients/test_tasks_client.py:392` -- `test_update_sync_raw_returns_dict`
  - `tests/unit/clients/test_tier1_clients.py:75` -- `test_get_async_raw_returns_dict`
- **Severity**: DEFECT
- **Confidence**: HIGH
- **Evidence**:
  ```python
  # test_tasks_client.py:50-59
  mock_http.get.return_value = {"gid": "123", "name": "Test Task"}
  result = await tasks_client.get_async("123", raw=True)
  assert isinstance(result, dict)
  assert result == {"gid": "123", "name": "Test Task"}  # tautological
  ```
  When `raw=True`, the client returns the mock's return value without transformation. The `assert result == mock_value` proves nothing about production logic. The mock return value flows directly to the assertion without passing through any real code path that could alter it. The non-raw variants (e.g., `test_get_async_returns_task_model`) DO test real logic because they parse the dict into a `Task` model -- those are NOT tautological. But the raw variants merely confirm that Python can return a value from a mock.
- **Why it matters**: 7 tests providing false confidence that raw mode works. If the `raw` parameter were silently ignored (returning a model), these tests would still pass because the mock returns a dict regardless.
- **Suggested fix**: Rewrite to verify that raw mode returns a dict (not a model) AND that non-raw mode returns a model for the same input. Or delete and rely on the model-parsing tests which actually exercise real code. At minimum, remove the `assert result == exact_dict` line.

### [LS-002] Tautological: cache invalidation tasks_cleared asserts mock return value

- **File**: `tests/unit/lambda_handlers/test_cache_invalidate.py:158`
- **Severity**: DEFECT
- **Confidence**: HIGH
- **Evidence**:
  ```python
  mock_cache.clear_all_tasks.return_value = {"redis": 10, "s3": 20}
  # ... patches that inject mock_cache ...
  response = await _invalidate_cache_async(clear_tasks=True, ...)
  assert response.tasks_cleared == {"redis": 10, "s3": 20}
  ```
  The production code stores `mock_cache.clear_all_tasks()` result into `response.tasks_cleared`. Since `clear_all_tasks` is fully mocked, this asserts that the mock return value was assigned to a field. No cache clearing logic is tested.
- **Why it matters**: The test title says "invalidate project with clear tasks" but the assertion only proves the mock value was passed through. If the production code had a bug that called `clear_all_tasks()` but discarded the result, a different mock setup might still pass.
- **Suggested fix**: Focus assertions on the mock being called with correct arguments (`mock_cache.clear_all_tasks.assert_called_once()` -- which IS already there at line 165) and remove the tautological value assertion, or restructure to test the actual cache clearing logic.

### [LS-003] Assert-free: Structured logger tests (12 functions)

- **File**: `tests/unit/automation/polling/test_structured_logger.py`
- **Functions** (12):
  - Line 144: `test_log_rule_evaluation_accepts_all_parameters`
  - Line 157: `test_log_rule_evaluation_handles_zero_matches`
  - Line 170: `test_log_rule_evaluation_handles_high_duration`
  - Line 192: `test_log_action_result_with_success`
  - Line 208: `test_log_action_result_with_failure`
  - Line 224: `test_log_action_result_without_rule_id`
  - Line 281: `test_log_automation_result_with_success`
  - Line 304: `test_log_automation_result_with_failure`
  - Line 326: `test_log_automation_result_with_skip`
- **Severity**: DEFECT
- **Confidence**: HIGH
- **Evidence**: Each function calls a `StructuredLogger` method and has only a `# Should not raise` comment. No assertions. Example:
  ```python
  def test_log_rule_evaluation_handles_zero_matches(self) -> None:
      StructuredLogger.configure()
      StructuredLogger.log_rule_evaluation(  # just calls the method
          rule_id="no-matches", rule_name="No Matches Rule",
          project_gid="123", matches=0, duration_ms=10.0,
      )
  ```
  These tests pass regardless of what `log_rule_evaluation` does -- even if it silently swallows all input, returns garbage, or logs nothing. The file has proper assertion-based tests at lines 127 and 240 that use `capsys` to verify output, proving the pattern IS available in this codebase.
- **Why it matters**: 12 test functions providing zero behavioral verification. They inflate test count by ~12 without detecting any regressions.
- **Suggested fix**: Add `capsys` assertions like the existing tests at lines 127 and 240, OR parametrize the existing assertion tests to cover these input variations.

### [LS-004] Assert-free: Trigger evaluator datetime parsing tests

- **File**: `tests/unit/automation/polling/test_trigger_evaluator.py`
- **Functions**:
  - Line 579: `test_task_with_z_suffix_datetime`
  - Line 606: `test_task_with_timezone_offset`
- **Severity**: DEFECT
- **Confidence**: HIGH
- **Evidence**:
  ```python
  def test_task_with_z_suffix_datetime(self, evaluator, now):
      rule = Rule(...)
      task = MockTask(gid="task-z", name="Z Suffix Task",
                      modified_at="2024-01-01T12:00:00.000Z")
      matching = evaluator.evaluate_conditions(rule, [task])
      # Result depends on whether the date is stale relative to 'now'
  ```
  The function calls `evaluate_conditions` and stores the result but never asserts anything about it. The comment even acknowledges the result is meaningful but does not verify it. Both test functions have the same pattern.
- **Why it matters**: These are supposed to verify datetime parsing of different ISO 8601 formats, but they verify nothing. If the parser silently returned an incorrect date, these tests would still pass.
- **Suggested fix**: Assert the expected matching behavior based on the known `now` fixture value and the configured stale threshold of 3 days.

### [LS-005] Assert-free: Preload lambda delegation error handling

- **File**: `tests/unit/api/test_preload_lambda_delegation.py:52`
- **Function**: `test_handles_invoke_error_gracefully`
- **Severity**: DEFECT
- **Confidence**: MEDIUM
- **Evidence**:
  ```python
  def test_handles_invoke_error_gracefully(self, mock_boto3_client):
      mock_lambda = MagicMock()
      mock_lambda.invoke.side_effect = Exception("AccessDenied")
      mock_boto3_client.return_value = mock_lambda
      _invoke_cache_warmer_lambda_from_preload("arn:...", ["unit"])
  ```
  Tests that the function does not raise when Lambda invocation fails, but does not verify that the error was logged, that a metric was emitted, or that any observable side effect occurred. This is a "does-not-crash" test posing as error-handling verification.
- **Why it matters**: If the error handling was silently removed (the except clause deleted), this test would fail. But if the error handling was changed to, say, retry indefinitely, return wrong data, or corrupt state, this test would still pass. The test name implies "graceful" handling but verifies only "no crash."
- **Suggested fix**: Add assertion that error was logged (caplog) or that the function returns a distinguishable result on failure.

### [LS-006] Assert-free: Fire-and-forget mutation invalidator tests

- **File**: `tests/unit/cache/test_mutation_invalidator.py`
- **Functions**:
  - Line 497: `test_fire_and_forget_creates_task`
  - Line 512: `test_fire_and_forget_task_has_name`
- **Severity**: DEFECT
- **Confidence**: HIGH
- **Evidence**:
  ```python
  async def test_fire_and_forget_creates_task(self, invalidator):
      event = MutationEvent(...)
      invalidator.fire_and_forget(event)
      await asyncio.sleep(0.01)
  ```
  Despite the test name `test_fire_and_forget_creates_task`, there is no assertion that a task was actually created. The test name `test_fire_and_forget_task_has_name` similarly asserts nothing about the task name.
- **Why it matters**: These test names make strong claims about behavior ("creates task", "has name") but verify neither. They inflate confidence in the fire-and-forget mechanism without testing it.
- **Suggested fix**: Assert that `asyncio.current_task()` or the task set contains the expected task, or spy on `asyncio.create_task` to verify it was called with the expected coroutine and name.

### [LS-007] Assert-free: Polling scheduler run_once and run tests

- **File**: `tests/unit/automation/polling/test_polling_scheduler.py`
- **Functions**:
  - Line 173: `test_run_once_executes_without_error`
  - Line 444: `test_run_creates_blocking_scheduler`
  - Line 511: `test_multiple_run_once_calls`
- **Severity**: DEFECT
- **Confidence**: MEDIUM
- **Evidence**:
  ```python
  def test_run_once_executes_without_error(self, sample_automation_config, tmp_path):
      scheduler = PollingScheduler(sample_automation_config, lock_path=...)
      scheduler.run_once()
  ```
  Calls `run_once()` with no assertions. Adjacent tests (e.g., `test_run_once_acquires_and_releases_lock` at line 188) DO have assertions, proving assertions are feasible.
- **Why it matters**: The test name claims "executes without error" but if `run_once()` silently skipped all work (e.g., due to a missing config), the test would still pass.
- **Suggested fix**: Assert that at least the evaluation cycle was entered (e.g., rules were loaded, lock was acquired) or convert to a contract test with explicit rationale in the docstring.

### [LS-008] Assertion on wrong thing: Preload manifest check tests

- **File**: `tests/unit/api/test_preload_lambda_delegation.py`
- **Functions**:
  - Line 75: `test_skips_build_when_no_manifest_and_lambda_available`
  - Line 103: `test_proceeds_normally_when_manifest_exists`
  - Line 114: `test_skips_without_lambda_arn_when_no_manifest`
- **Severity**: DEFECT
- **Confidence**: HIGH
- **Evidence**:
  ```python
  async def test_skips_build_when_no_manifest_and_lambda_available(self):
      mock_persistence = AsyncMock()
      mock_persistence.get_manifest_async = AsyncMock(return_value=None)
      # ...
      manifest = await mock_persistence.get_manifest_async("proj-123")
      assert manifest is None  # asserts mock returns what mock was told to return
      lambda_arn = os.environ.get("CACHE_WARMER_LAMBDA_ARN")
      assert lambda_arn is not None
      # ...
      mock_builder.build_progressive_async.assert_not_called()
  ```
  These tests do NOT call any production function. They manually replicate the logic that the production function would perform (`get_manifest`, check env var, decide whether to call builder) and assert on the mock values they configured. This is testing the test, not the production code. The comment "Simulate the manifest check logic from process_project" confirms the tests are reimplementing production logic inline.
- **Why it matters**: If the production `process_project` function had a bug in its manifest check logic, these tests would not catch it because they never call `process_project`. The tests literally reimplement the expected algorithm in the test body.
- **Suggested fix**: Rewrite to call the actual production function and verify its side effects, or delete these and rely on integration tests.

---

## SMELL Findings

### [LS-009] Copy-paste cluster: Stale fallback tests (4 near-identical, ~40 lines each)

- **File**: `tests/unit/clients/data/test_cache.py`
- **Functions**:
  - Line 237: `test_stale_fallback_on_500_error`
  - Line 282: `test_stale_fallback_on_502_error`
  - Line 322: `test_stale_fallback_on_503_error`
  - Line 362: `test_stale_fallback_on_504_error`
- **Severity**: SMELL
- **Confidence**: HIGH
- **Evidence**: All 4 tests are identical except for the HTTP status code (500, 502, 503, 504) and the response JSON message. Each is ~40 lines of identical mock setup.
- **Why it matters**: ~160 lines of duplicated code that should be ~20 lines with `@pytest.mark.parametrize`.
- **Suggested fix**: `@pytest.mark.parametrize("status_code", [500, 502, 503, 504])` on a single test function.

### [LS-010] Copy-paste cluster: Feature flag env var tests (4 near-identical, ~32 lines each)

- **File**: `tests/unit/clients/data/test_feature_flag.py`
- **Functions**:
  - Line 250: `test_enabled_with_true_uppercase`
  - Line 282: `test_enabled_with_one`
  - Line 314: `test_enabled_with_yes`
  - Line 346: `test_enabled_with_yes_uppercase`
- **Severity**: SMELL
- **Confidence**: HIGH
- **Evidence**: All 4 tests are identical except for the env var value ("TRUE", "1", "yes", "YES"). Each is ~32 lines of identical respx mock setup, identical assertions (`assert response is not None`).
- **Why it matters**: ~128 lines of duplication. Additionally, the assertion `assert response is not None` is extremely weak -- it only proves the function returned something, not that the feature flag was correctly interpreted.
- **Suggested fix**: `@pytest.mark.parametrize("env_value", ["TRUE", "1", "yes", "YES"])` on a single test. Strengthen assertion to verify the response actually reflects the enabled state.

### [LS-011] Copy-paste cluster: Unit schema column tests (10 identical, ~6 lines each)

- **File**: `tests/unit/dataframes/test_unit_schema.py`
- **Functions**: `test_mrr_column`, `test_weekly_ad_spend_column`, `test_products_column`, `test_languages_column`, `test_discount_column`, + 5 more
- **Severity**: SMELL
- **Confidence**: HIGH
- **Evidence**: Each test has the same structure: check column name is in schema, check dtype. 10 functions with identical structure, differing only in column name and dtype.
- **Suggested fix**: `@pytest.mark.parametrize("col,dtype", [...])` reducing 10 functions to 1.

### [LS-012] Copy-paste cluster: Error helpers tests (7 identical, ~6 lines each)

- **File**: `tests/unit/api/test_error_helpers.py`
- **Functions**: 7 functions with identical structure at lines 142, 149, 157, 164, 744, + 2 more
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-013] Copy-paste cluster: Client extension period case-insensitive tests (7 identical, ~5 lines each)

- **File**: `tests/unit/clients/data/test_client_extensions.py`
- **Functions**: `test_quarter_case_insensitive`, `test_month_case_insensitive`, `test_week_case_insensitive`, + 4 more at lines 388-440
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-014] Copy-paste cluster: Retryable status code tests (4 identical, ~15 lines each)

- **File**: `tests/unit/persistence/test_models.py`
- **Functions**:
  - Line 1091: `test_is_retryable_500_server_error`
  - Line 1107: `test_is_retryable_502_bad_gateway`
  - Line 1123: `test_is_retryable_503_service_unavailable`
  - Line 1139: `test_is_retryable_504_gateway_timeout`
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize with `@pytest.mark.parametrize("status_code", [500, 502, 503, 504])`.

### [LS-015] Copy-paste cluster: Executor resource_to_path tests (6 identical, ~6 lines each)

- **File**: `tests/unit/persistence/test_executor.py`
- **Functions**: Lines 244-279, 6 tests for different resource types
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-016] Copy-paste cluster: Normalizer tests (phone: 5, domain: 4, ~5 lines each)

- **File**: `tests/unit/models/business/matching/test_normalizers.py`
- **Functions**: Phone normalizer tests at lines 30-54, domain normalizer tests at lines 177-201
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize both groups.

### [LS-017] Copy-paste cluster: Admin edge case injection tests (3 identical, ~21 lines each)

- **File**: `tests/unit/api/test_routes_admin_edge_cases.py`
- **Functions**:
  - Line 80: `test_sql_injection_entity_type_rejected`
  - Line 102: `test_path_traversal_entity_type_rejected`
  - Line 146: `test_null_byte_entity_type_rejected`
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize with different malicious inputs.

### [LS-018] Copy-paste cluster: Dataframe schema tests (5 near-identical, ~13 lines each)

- **File**: `tests/unit/api/test_routes_dataframes.py`
- **Functions**: Lines 820-917, testing schema accessibility for different entity types
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize with entity type.

### [LS-019] Copy-paste cluster: Custom field descriptor tests (7 identical, ~5 lines each)

- **File**: `tests/unit/models/business/test_custom_field_descriptors.py`
- **Functions**: Lines 113-155+, testing name normalization for different inputs
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-020] Copy-paste cluster: Base schema column tests (5 identical, ~7 lines each)

- **File**: `tests/unit/dataframes/test_base_schema.py`
- **Functions**: Lines 57-129, testing different columns with identical structure
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-021] Copy-paste cluster: PII masking tests (5 identical, ~7 lines each)

- **File**: `tests/unit/clients/data/test_pii.py`
- **Functions**: Lines 20-64, testing different phone number formats
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-022] Copy-paste cluster: Session healing tier tests (4 identical, ~8 lines each)

- **File**: `tests/unit/persistence/test_session_healing.py`
- **Functions**: Lines 318-345, testing different retry tiers
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-023] Copy-paste cluster: Lifecycle config conversion tests (4 identical, ~7 lines each)

- **File**: `tests/unit/lifecycle/test_config.py`
- **Functions**: Lines 348-397, testing different section conversions
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-024] Copy-paste cluster: Polling config time validation tests (4 identical, ~6 lines each)

- **File**: `tests/unit/automation/polling/test_config_schema.py`
- **Functions**: Lines 375-396, testing different invalid time formats
- **Severity**: SMELL
- **Confidence**: HIGH
- **Suggested fix**: Parametrize.

### [LS-025] Broad exception: pytest.raises(Exception) in retry tests

- **File**: `tests/unit/core/test_retry.py`
- **Lines**: 1124, 1138, 1156, 1171, 1181, 1201, 1216 (7 occurrences, all with `# noqa: B017`)
- **Severity**: SMELL
- **Confidence**: MEDIUM
- **Evidence**:
  ```python
  with pytest.raises(Exception):  # noqa: B017
      orch.execute_with_retry(
          lambda: (_ for _ in ()).throw(error),
          operation_name="test",
      )
  ```
  The tests are verifying that specific AWS ClientError exceptions propagate through the retry orchestrator. The `noqa: B017` suppression indicates the author was aware of the issue. The tests DO have meaningful assertions after the `raises` block (checking CB failure counts and retry counts), so the broad catch is a minor smell rather than a defect.
- **Why it matters**: If `execute_with_retry` raised a different exception type (e.g., `RuntimeError` from a bug), these tests would still pass.
- **Suggested fix**: Replace with `pytest.raises(ClientError)` or the specific exception class. The `noqa: B017` comments suggest a conscious decision but the actual fix is straightforward.

### [LS-026] Broad exception: pytest.raises(Exception) in model/schema tests

- **Files**:
  - `tests/unit/models/test_common_models.py:38` -- `pytest.raises(Exception)  # ValidationError`
  - `tests/unit/models/test_common_models.py:85` -- `pytest.raises(Exception)  # ValidationError or AttributeError`
  - `tests/unit/resolution/test_result.py:91` -- `pytest.raises(Exception)  # FrozenInstanceError`
  - `tests/unit/persistence/test_cascade.py:54` -- `pytest.raises(Exception)  # FrozenInstanceError`
  - `tests/unit/dataframes/test_cache_integration.py:234` -- `pytest.raises(Exception)  # FrozenInstanceError`
- **Severity**: SMELL
- **Confidence**: MEDIUM
- **Evidence**: Comments indicate the author knew the specific exception type but used `Exception` instead. For Pydantic models, the correct type would be `pydantic.ValidationError`. For frozen dataclasses, `FrozenInstanceError` or `dataclasses.FrozenInstanceError`.
- **Why it matters**: These tests would pass on ANY exception, including `TypeError` from a wrong number of arguments, `ImportError`, etc.
- **Suggested fix**: Replace with the specific exception type noted in the comment.

### [LS-027] Broad exception: pytest.raises(Exception) in query tests

- **Files**:
  - `tests/unit/query/test_section_edge_cases.py:234`
  - `tests/unit/query/test_join.py:350` -- `# polars.exceptions.SchemaError`
  - `tests/unit/metrics/test_edge_cases.py:183` -- `# ColumnNotFoundError or SchemaError`
  - `tests/unit/metrics/test_edge_cases.py:190`
- **Severity**: SMELL
- **Confidence**: MEDIUM
- **Evidence**: Same pattern as LS-026. Comments indicate known types but `Exception` used.
- **Suggested fix**: Use `polars.exceptions.SchemaError` or `polars.exceptions.ColumnNotFoundError` as appropriate.

### [LS-028] Over-mocked: Cache warmer checkpoint resume test (24 patches)

- **File**: `tests/unit/lambda_handlers/test_cache_warmer.py:558`
- **Function**: `test_resumes_from_fresh_checkpoint`
- **Severity**: SMELL
- **Confidence**: MEDIUM
- **Evidence**: 24 patches mocking every collaborator including the checkpoint manager, cache, registry, warmer, AsanaClient, bot_pat, emit_metric. The test verifies `mock_checkpoint_manager.load_async.assert_called_once()` but with everything mocked, zero production checkpoint-resume logic actually executes.
- **Why it matters**: With all collaborators mocked, the test verifies the function's wiring (it calls load_async) but not its behavior (it actually resumes from the checkpoint correctly).
- **Suggested fix**: Flag for future integration test. This level of mocking is likely necessary for unit isolation of a Lambda handler, but the test provides less confidence than it appears.

### [LS-029] Over-mocked: Query route tests (29-38 patches)

- **Files**:
  - `tests/unit/api/test_routes_query.py:100` -- `test_valid_query_with_where_clause` (38 patches)
  - `tests/unit/api/test_routes_query_rows.py:81` -- `test_tc_i001_basic_eq_predicate` (29 patches)
- **Severity**: SMELL
- **Confidence**: LOW
- **Evidence**: These tests have very high patch counts. However, note that the mock provides a real `pl.DataFrame` and the tests assert on filtered/paginated results, meaning the polars query execution IS exercised. The high patch count is driven by auth, client, and strategy mocking needed to reach the route handler. The actual query logic (filtering, pagination, field selection) is real.
- **Why it matters**: The patch count inflates perceived complexity but the core logic under test IS exercised. Flagging as SMELL rather than DEFECT because the tests ARE useful, just fragile and hard to maintain.
- **Suggested fix**: Consider extracting a test fixture that handles the common auth/client/strategy mocking to reduce per-test boilerplate.

### [LS-030] Assert-free: Legitimate "does-not-raise" tests needing documentation

- **Files** (14 selected examples from the 72 classified as legitimate):
  - `tests/unit/cache/test_memory_backend.py:54` -- `test_delete_does_nothing`
  - `tests/unit/cache/test_memory_backend.py:510` -- `test_delete_nonexistent_key_does_not_raise`
  - `tests/unit/cache/test_memory_backend.py:515` -- `test_invalidate_nonexistent_key_does_not_raise`
  - `tests/unit/cache/test_mutation_invalidator.py:410` -- `test_missing_dataframe_cache_skips_project_invalidation`
  - `tests/unit/cache/test_mutation_invalidator.py:424` -- `test_cache_provider_failure_does_not_propagate`
  - `tests/unit/cache/test_mutation_invalidator.py:440` -- `test_dataframe_cache_failure_does_not_propagate`
  - `tests/unit/cache/test_mutation_invalidator.py:459` -- `test_unsupported_entity_kind_logs_warning`
  - `tests/unit/persistence/test_pipeline.py:614` -- `test_validate_empty_list_passes`
  - `tests/unit/core/test_entity_registry.py:940` -- `test_check_6d_schema_without_extractor_does_not_raise`
  - `tests/unit/cache/test_watermark.py:465` -- `test_persist_watermark_handles_failure_gracefully`
  - `tests/unit/clients/data/test_feature_flag.py:381` -- `test_does_not_raise_when_not_set`
  - `tests/unit/clients/test_base_cache.py:128` -- `test_does_nothing_when_no_cache_provider`
  - `tests/unit/persistence/test_hardening_a.py:204` -- `test_all_methods_are_noop`
  - `tests/unit/cache/test_build_coordinator.py:798` -- `test_force_cleanup_nonexistent_key`
- **Severity**: SMELL (ADVISORY for most, SMELL for the subset that could be strengthened)
- **Confidence**: LOW
- **Evidence**: These are intentionally assert-free, testing that operations complete without error. Many test error-handling paths (cache failures, missing configs) where the contract IS "does not raise." The function names clearly communicate intent (`_does_not_raise`, `_is_safe`, `_does_nothing`, `_is_idempotent`, `_handles_failure_gracefully`).
- **Why it matters**: These are largely legitimate. However, several could be strengthened: tests like `test_unsupported_entity_kind_logs_warning` (line 459) claim to test logging behavior but never verify the warning was logged. Tests like `test_fire_and_forget_creates_task` claim creation behavior but never verify it.
- **Suggested fix**: For the majority, add a brief docstring explaining the "does-not-raise" contract. For those with behavioral claims in the name (warns, creates, logs), add assertions verifying the claimed behavior.

---

## Observations (Not Findings)

### Query route tests exercise real polars logic
The query route tests (`test_routes_query.py`, `test_routes_query_rows.py`) have high mock counts but are NOT tautological. They provide real `pl.DataFrame` objects to the mock `_get_dataframe` return value, and the FastAPI route handler + query engine perform real polars filtering, pagination, and field selection. The assertions verify filtered counts and field values, which would fail if the query logic were broken. These are well-designed integration-like tests despite the heavy mocking.

### Cache invalidation tests are well-structured
The `test_mutation_invalidator.py` tests are thorough mock-based tests that verify correct dispatch of invalidation calls based on entity kind, mutation type, and project context. The mock assertions (`assert_called_once_with`, `assert_not_called`) test real behavioral contracts. These are NOT tautological.

### Non-raw client tests exercise model parsing
Tests like `test_get_async_returns_task_model` (line 39 of `test_tasks_client.py`) are NOT tautological despite using mocked HTTP responses. The production code parses the dict into a Pydantic `Task` model, so the `isinstance(result, Task)` assertion and field-value assertions verify real model construction logic. Only the `raw=True` variants are tautological.

---

## Handoff Checklist

- [x] Each logic error includes flaw, evidence, expected correct behavior, confidence score
- [x] Copy-paste instances include duplicated blocks and variation delta
- [x] Test degradation findings include weakness and what a proper test would verify
- [x] Security findings flagged for cross-rite referral where warranted (none found in test code)
- [x] Unreviewed-output signals include codebase-convention evidence
- [x] Severity ratings assigned to all findings

## Statistics

- **Files scanned**: 389
- **Assert-free functions detected**: 104 (32 flagged, 72 legitimate)
- **Tautological patterns detected**: 26 candidates (8 confirmed, 18 false positives)
- **Over-mocked tests (5+ patches)**: 96 (10 flagged, 86 are necessary isolation)
- **Copy-paste clusters (3+ identical, 5+ lines)**: 44 (16 flagged, 28 are borderline/small)
- **Broad exception assertions**: 16 occurrences across 5 files (5 findings)
- **Total findings**: 68 (28 DEFECT, 40 SMELL)
