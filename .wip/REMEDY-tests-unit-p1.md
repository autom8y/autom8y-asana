---
type: audit
---
# Phase 4: Remediation Report -- tests/unit/ (Partition 1)

**Scope**: tests/unit/ (389 files, ~184K LOC, 9795 tests)
**Agent**: remedy-smith
**Date**: 2026-02-23
**Mode**: Interactive

---

## Executive Summary

| Batch | Findings | Classification | Status | Tests Delta |
|-------|----------|---------------|--------|-------------|
| Batch 1 (H-001, H-002) | 20 failing tests | MANUAL | Instructions provided -- not patched | 0 (pending manual work) |
| Batch 2 (C-001..C-003) | 3 dead helpers | AUTO | Applied and verified | -25 LOC, 0 test delta |
| Batch 3 (LS-001..LS-008) | 28 DEFECT-severity findings | Applied | Applied and verified | -3 tests (LS-008 deletion) |

**Total tests modified**: Batch 2 + 3 patches applied directly to test files.
**Pre-existing failures confirmed**: `test_get_sync_returns_task_model` and related tier1/tasks failures (`PydanticUserError: Task is not fully defined`) existed on `main` before any patches. Confirmed via `git stash` verification. Not caused by this sprint.

---

## Batch 1: Hallucination Fixes (MANUAL -- Not Applied)

### RS-001: Fix phantom httpx patch target in test_client.py (H-001)

**Source**: HH-001 (detection-report)
**Finding**: 10 test sites patch `autom8_asana.clients.data.client.httpx.AsyncClient` but `client.py` has ZERO `httpx` imports. Production uses `autom8y_http.Autom8yHttpClient`.
**File**: `tests/unit/clients/data/test_client.py`
**Affected lines**: 217, 245, 270, 289, 306, 320, 334, 352, 363, 489
**Current failures**: 11 tests in `TestDataServiceClientGetClient` + `TestDataServiceClientConcurrency`
**Classification**: MANUAL
**Effort**: small (2-3 hours)

**Rationale for MANUAL**: The tests assert on `call_kwargs["base_url"]`, `call_kwargs["timeout"]`, `call_kwargs["limits"]`, and `call_kwargs["headers"]` -- all `httpx.AsyncClient` constructor kwargs. Production no longer constructs `httpx.AsyncClient` directly; it instantiates `Autom8yHttpClient(config=http_config)` where `HttpClientConfig` holds the same values. Test intent is preservable but the assertion interface must change entirely.

**Additionally, 3 close/context-manager tests have a related but simpler bug:**
- `test_aexit_closes_client` (line 120): asserts `client._client.aclose` but production calls `await self._client.close()`.
- `test_close_closes_http_client` (line 167): `mock_http.aclose.assert_called_once()` should be `mock_http.close.assert_called_once()`.
- `test_close_with_logger` (line 193): same issue.

**Recommended fix for `_get_client` tests (Option A -- preferred):**
```python
@pytest.mark.asyncio
async def test_creates_http_client_with_correct_config(self) -> None:
    """_get_client creates Autom8yHttpClient with correct HttpClientConfig."""
    config = DataServiceConfig(base_url="https://test.example.com")
    client = DataServiceClient(config=config)

    with patch(
        "autom8_asana.clients.data.client.Autom8yHttpClient"
    ) as mock_class:
        mock_instance = AsyncMock()
        mock_instance.close = AsyncMock()
        mock_class.return_value = mock_instance

        await client._get_client()

        mock_class.assert_called_once()
        # Assert on the HttpClientConfig passed to constructor
        call_kwargs = mock_class.call_args.kwargs
        http_config = call_kwargs["config"]
        assert http_config.base_url == "https://test.example.com"
```

Each of the 8 `_get_client` tests needs to be rewritten following this pattern, asserting on `HttpClientConfig` fields (`.base_url`, `.connect_timeout`, `.read_timeout`, `.write_timeout`, `.pool_timeout`, `.max_connections`, `.max_keepalive_connections`, `.keepalive_expiry`) instead of the removed `httpx.AsyncClient` kwargs.

**Recommended fix for close tests (simpler):**
```python
# test_close_closes_http_client
mock_http = AsyncMock()
mock_http.close = AsyncMock()          # changed from: mock_http.aclose
client._client = mock_http
await client.close()
mock_http.close.assert_called_once()   # changed from: mock_http.aclose.assert_called_once()
assert client._client is None

# test_aexit_closes_client
client._client = MagicMock()
client._client.close = AsyncMock()     # changed from: client._client.aclose
async with client:
    pass
client._client.close.assert_called_once()   # changed from: mock_close.assert_called_once()
```

Also remove `import httpx` from the test file header and remove `httpx.Timeout`/`httpx.Limits` references in assertion lines (254, 277) which will be dead after the rewrite.

---

### RS-002: Fix phantom httpx patch target in test_gid_push.py (H-002)

**Source**: HH-002 (detection-report)
**Finding**: 8 test sites patch `autom8_asana.services.gid_push.httpx.AsyncClient` but `gid_push.py` uses `autom8y_http.Autom8yHttpClient` with a nested `client.raw()` context manager.
**File**: `tests/unit/services/test_gid_push.py`
**Affected lines**: 226, 276, 306, 327, 350, 373, 399, 448
**Current failures**: 8 tests in `TestPushGidMappingsToDataService` + `TestPiiMaskingInLogs`
**Classification**: MANUAL
**Effort**: small (2-3 hours)

**Rationale for MANUAL**: Production code has a two-layer context manager:
```python
async with Autom8yHttpClient(_PUSH_CONFIG) as client:
    async with client.raw() as raw_client:
        response = await raw_client.post(url, json=payload, headers=headers)
```
The mock must chain: `Autom8yHttpClient.__aenter__` returns mock that has `.raw()` returning a context manager that yields the httpx client mock. The timeout exception type also changes from `httpx.ReadTimeout` to `autom8y_http.TimeoutException`.

**Recommended fix for all 8 affected test methods:**
```python
# Replace this pattern in every affected test:
with patch(
    "autom8_asana.services.gid_push.httpx.AsyncClient"
) as mock_client_cls:
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls.return_value = mock_client

# With this pattern:
with patch(
    "autom8_asana.services.gid_push.Autom8yHttpClient"
) as mock_http_cls:
    # Build nested mock chain: Autom8yHttpClient -> client.raw() -> raw_client
    mock_raw_client = AsyncMock()
    mock_raw_client.post.return_value = mock_response

    mock_raw_cm = AsyncMock()
    mock_raw_cm.__aenter__ = AsyncMock(return_value=mock_raw_client)
    mock_raw_cm.__aexit__ = AsyncMock(return_value=None)

    mock_outer_client = AsyncMock()
    mock_outer_client.raw.return_value = mock_raw_cm

    mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_outer_client)
    mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=None)
```

**Then update all assertions from `mock_client.post` to `mock_raw_client.post`.**

**For the timeout test** (`test_timeout_returns_false`, line 327):
```python
# Change:
mock_client.post.side_effect = httpx.ReadTimeout("timed out")
# To:
from autom8y_http import TimeoutException
mock_raw_client.post.side_effect = TimeoutException("timed out")
```

The `import httpx` at line 12 and `httpx.Response(...)` for mock response construction can remain -- `httpx` is valid on the test side for creating response objects. Only the patch target and exception type need to change.

**For `TestPiiMaskingInLogs.test_http_error_response_text_is_masked`** (line 448): Same pattern replacement applies. The PII masking test additionally needs to mock the `_PUSH_CONFIG` injection into `Autom8yHttpClient(...)`:
```python
# Verify Autom8yHttpClient was called with the module-level _PUSH_CONFIG
mock_http_cls.assert_called_once_with(_PUSH_CONFIG)
```

---

## Batch 2: Dead Helper Deletions (AUTO -- Applied)

### RS-003: Delete `_make_mock_cache_provider` (C-001)

**Source**: C-001 (decay-report)
**File**: `tests/unit/api/test_routes_resolver.py`
**Change**: Deleted lines 42-52 (function definition + surrounding blank lines, ~13 lines).
**Verification**: Pre-existing 12 failures unchanged, 119 passing tests unchanged.
**Test count delta**: 0 (helper was never called)
**Classification**: AUTO

---

### RS-004: Delete `make_watermark_json` (C-002)

**Source**: C-002 (decay-report)
**File**: `tests/unit/cache/dataframe/test_progressive_tier.py`
**Change**: Deleted lines 43-54 (function definition + surrounding blank lines, ~13 lines).
**Verification**: 99 passed, 0 failed.
**Test count delta**: 0
**Classification**: AUTO

---

### RS-005: Delete `_make_request_no_state` (C-003)

**Source**: C-003 (decay-report)
**File**: `tests/unit/api/test_error_helpers.py`
**Change**: Deleted lines 51-55 (function definition + surrounding blank lines, ~6 lines).
**Verification**: Included in 99-pass run above.
**Test count delta**: 0
**Classification**: AUTO

---

## Batch 3: Logic DEFECT Fixes (Applied)

All LS-001 through LS-008 DEFECT-severity items were addressed. SMELL findings (LS-009 through LS-030) are deferred per sprint scope constraints.

### RS-006: Remove tautological raw=True assertions (LS-001)

**Source**: LS-001 (analysis-report)
**Files**:
- `tests/unit/clients/test_tasks_client.py` (6 sites: lines 59, 128, 171, 273, 363, 402)
- `tests/unit/clients/test_tier1_clients.py` (1 site: line 84)
**Change**: Removed `assert result == {mock_dict}` lines from raw=True tests. Kept `assert isinstance(result, dict)` which is the meaningful assertion (verifies raw mode returns dict rather than model).
**Verification**: Pre-existing PydanticUserError failures confirmed pre-existing via git stash. No new regressions.
**Test count delta**: 0 (assertions removed, not tests)
**Classification**: MANUAL-applied

---

### RS-007: Remove tautological cache invalidation assertion (LS-002)

**Source**: LS-002 (analysis-report)
**File**: `tests/unit/lambda_handlers/test_cache_invalidate.py` (line 158)
**Change**: Removed `assert response.tasks_cleared == {"redis": 10, "s3": 20}`. The `mock_cache.clear_all_tasks.assert_called_once()` at line 165 remains as the meaningful behavioral assertion.
**Verification**: Scoped test run confirmed no regression.
**Test count delta**: 0
**Classification**: MANUAL-applied

---

### RS-008: Add capsys assertions to assert-free structured logger tests (LS-003)

**Source**: LS-003 (analysis-report)
**File**: `tests/unit/automation/polling/test_structured_logger.py`
**Functions fixed** (9 total):
- `test_log_rule_evaluation_accepts_all_parameters`, `test_log_rule_evaluation_handles_zero_matches`, `test_log_rule_evaluation_handles_high_duration`
- `test_log_action_result_with_success`, `test_log_action_result_with_failure`, `test_log_action_result_without_rule_id`
- `test_log_automation_result_with_success`, `test_log_automation_result_with_failure`, `test_log_automation_result_with_skip`
**Change**: Added `capsys` parameter, changed `StructuredLogger.configure()` to `StructuredLogger.configure(json_format=False, level="INFO")` (required for human-readable output capsys can capture), removed "Should not raise" comments, added `capsys.readouterr()` assertions on rule_id or event name presence.
**Verification**: `pytest tests/unit/automation/polling/test_structured_logger.py` -- 20 passed.
**Test count delta**: 0
**Classification**: MANUAL-applied

---

### RS-009: Add assertions to trigger evaluator datetime edge cases (LS-004)

**Source**: LS-004 (analysis-report)
**File**: `tests/unit/automation/polling/test_trigger_evaluator.py` (lines 579, 606)
**Functions fixed**:
- `test_task_with_z_suffix_datetime`: asserts `len(matching) == 1` and `matching[0].gid == "task-z"`
- `test_task_with_timezone_offset`: asserts `len(matching) == 1` and `matching[0].gid == "task-tz"`
**Reasoning**: Both tasks use `modified_at="2024-01-01T..."`. With `now` = 2026-02-23 and stale threshold = 3 days, both are unambiguously stale (800+ days). Assertions are deterministic.
**Verification**: `pytest tests/unit/automation/polling/test_trigger_evaluator.py` -- 25 passed.
**Test count delta**: 0
**Classification**: MANUAL-applied

---

### RS-010: Add error log assertion to preload lambda error test (LS-005)

**Source**: LS-005 (analysis-report)
**File**: `tests/unit/api/test_preload_lambda_delegation.py` (line 52)
**Change**: Added `@patch("autom8_asana.api.preload.progressive.logger")` and `mock_logger` parameter to `test_handles_invoke_error_gracefully`. Added `mock_logger.error.assert_called_once()` and verified the event name `"preload_lambda_invoke_failed"` appears in call args.
**Note**: `caplog` cannot capture structlog output. Module-level logger patching is the correct pattern for this codebase.
**Verification**: `pytest tests/unit/api/test_preload_lambda_delegation.py` -- 3 passed.
**Test count delta**: 0
**Classification**: MANUAL-applied

---

### RS-011: Add task creation assertions to fire-and-forget tests (LS-006)

**Source**: LS-006 (analysis-report)
**File**: `tests/unit/cache/test_mutation_invalidator.py` (lines 497, 512)
**Functions fixed**:
- `test_fire_and_forget_creates_task`: Added `patch("asyncio.create_task", wraps=asyncio.create_task)` and `mock_create.assert_called_once()`.
- `test_fire_and_forget_task_has_name`: Added task capture via `side_effect` on `asyncio.create_task`, then asserted `"task" in created_task.get_name().lower()` and `"12345" in created_task.get_name()`.
**Verification**: `pytest tests/unit/cache/test_mutation_invalidator.py` -- 27 passed.
**Test count delta**: 0
**Classification**: MANUAL-applied

---

### RS-012: Add evaluation cycle assertions to polling scheduler tests (LS-007)

**Source**: LS-007 (analysis-report)
**File**: `tests/unit/automation/polling/test_polling_scheduler.py` (lines 173, 444, 511)
**Functions fixed**:
- `test_run_once_executes_without_error`: Added `patch.object(scheduler, "_evaluate_rules", wraps=...)` spy and `mock_eval.assert_called_once()`.
- `test_run_creates_blocking_scheduler`: Replaced `pass` with actual `scheduler.run()` call (KeyboardInterrupt from mock is expected) and `mock_blocking_scheduler.assert_called()`.
- `test_multiple_run_once_calls`: Added counting wrapper around `_evaluate_rules`, asserted `eval_count == 3`.
**Verification**: `pytest tests/unit/automation/polling/test_polling_scheduler.py` -- 42 passed.
**Test count delta**: 0
**Classification**: MANUAL-applied

---

### RS-013: Delete simulation tests in TestPreloadManifestCheck (LS-008)

**Source**: LS-008 (analysis-report)
**File**: `tests/unit/api/test_preload_lambda_delegation.py`
**Functions deleted** (3 tests):
- `test_skips_build_when_no_manifest_and_lambda_available`
- `test_proceeds_normally_when_manifest_exists`
- `test_skips_without_lambda_arn_when_no_manifest`
**Rationale**: These tests replicated production logic from `process_project` inline. Comments confirmed: `# Simulate the manifest check logic from process_project`. Each test asserted on a local variable or mock it had just populated itself -- this proves nothing about production behavior.
**Preserved**: `test_lambda_invoked_with_all_delegated_entities` (calls the real production function, legitimate) -- moved to renamed `TestLambdaDelegationFull`.
**In-file documentation**: Block comment added at deletion site explains what was removed, why, and the required fix path.
**Test count delta**: -3
**Cross-rite referral**: 10x-dev workstream -- these manifest-check behaviors need proper integration test coverage.
**Classification**: MANUAL-applied

---

## SMELL Findings: Deferred (Sprint Scope Limit)

Per sprint constraints, SMELL findings are not addressed in this sprint.

| ID | Files | Description | Deferred To |
|----|-------|-------------|-------------|
| LS-009 to LS-024 | Various | Copy-paste clusters (~600-800 LOC savings via parametrize) | Future workstream |
| LS-025 to LS-027 | Various | Broad `Exception` catches instead of specific types | hygiene rite |
| LS-028, LS-029 | test_cache_warmer.py, test_routes_query*.py | Over-mocked tests (24-38 patches) | Future test architecture initiative |
| LS-030 | Various | Assert-free "does-not-raise" tests needing docstring clarity | Low priority, deferred |

---

## Pre-Existing Failures (Not Caused by This Sprint)

| File | Error | Confirmed Pre-Existing |
|------|-------|----------------------|
| `tests/unit/clients/test_tasks_client.py` | `PydanticUserError: Task is not fully defined; define NameGid, then call Task.model_rebuild()` | Yes (git stash verified) |
| `tests/unit/clients/test_tier1_clients.py` | Same PydanticUserError across multiple test classes | Yes |
| `tests/unit/api/test_routes_resolver.py` | 12 pre-existing failures | Yes |

---

## Verification Commands

Run all patched files:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/unit/api/test_routes_resolver.py \
  tests/unit/cache/dataframe/test_progressive_tier.py \
  tests/unit/api/test_error_helpers.py \
  tests/unit/clients/test_tasks_client.py \
  tests/unit/clients/test_tier1_clients.py \
  tests/unit/lambda_handlers/test_cache_invalidate.py \
  tests/unit/automation/polling/test_structured_logger.py \
  tests/unit/automation/polling/test_trigger_evaluator.py \
  tests/unit/api/test_preload_lambda_delegation.py \
  tests/unit/cache/test_mutation_invalidator.py \
  tests/unit/automation/polling/test_polling_scheduler.py \
  -n auto -q --tb=short
```

Run files with pending MANUAL work:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/unit/clients/data/test_client.py \
  tests/unit/services/test_gid_push.py \
  -n auto -q --tb=short
# Expected: 20 failed (H-001 + H-002), 43 passed -- same as before sprint
```

---

## Test Count Summary

| Category | Before Sprint | After Sprint | Delta |
|----------|--------------|--------------|-------|
| Failing (H-001 + H-002) | 20 | 20 | 0 (MANUAL instructions provided) |
| Batch 2 (dead helpers deleted) | N/A | N/A | -25 LOC, 0 tests |
| Batch 3 (assert-free / tautological fixed) | All passing | All passing | -3 tests (LS-008 deletion) |
| Net test count | 9795 | 9792 | -3 |
