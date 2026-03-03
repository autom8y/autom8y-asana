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

**Noteworthy exclusions**: Of 104 assert-free functions detected by AST scan, 72 were classified as legitimate "does-not-raise" contract tests. Of 26 potential tautological patterns detected by data-flow analysis, 18 were false positives where client code performs real work between mock and assertion.

---

## DEFECT Findings

### [LS-001] Tautological: raw=True client tests assert mock return value directly
- **Files**: `tests/unit/clients/test_tasks_client.py` (lines 50, 111, 160, 264, 346, 392), `tests/unit/clients/test_tier1_clients.py:75`
- **Severity**: DEFECT | **Confidence**: HIGH
- **Evidence**: When `raw=True`, client returns mock's return value without transformation. `assert result == mock_value` proves nothing.
- **Fix**: Delete tautological value assertions or rewrite to verify raw vs non-raw behavior contrast.

### [LS-002] Tautological: cache invalidation tasks_cleared asserts mock return value
- **File**: `tests/unit/lambda_handlers/test_cache_invalidate.py:158`
- **Severity**: DEFECT | **Confidence**: HIGH
- **Evidence**: `assert response.tasks_cleared == {"redis": 10, "s3": 20}` where that dict came directly from `mock_cache.clear_all_tasks.return_value`.
- **Fix**: Remove tautological value assertion; the `assert_called_once()` at line 165 is the real assertion.

### [LS-003] Assert-free: Structured logger tests (12 functions)
- **File**: `tests/unit/automation/polling/test_structured_logger.py` (lines 144, 157, 170, 192, 208, 224, 281, 304, 326 + 3 more)
- **Severity**: DEFECT | **Confidence**: HIGH
- **Evidence**: Each calls a logger method with no assertions. Adjacent tests at lines 127, 240 DO use `capsys` properly.
- **Fix**: Add `capsys` assertions or parametrize existing assertion tests.

### [LS-004] Assert-free: Trigger evaluator datetime parsing (2 functions)
- **File**: `tests/unit/automation/polling/test_trigger_evaluator.py` (lines 579, 606)
- **Severity**: DEFECT | **Confidence**: HIGH
- **Fix**: Assert matching behavior based on known `now` fixture value.

### [LS-005] Assert-free: Preload lambda delegation error handling
- **File**: `tests/unit/api/test_preload_lambda_delegation.py:52`
- **Severity**: DEFECT | **Confidence**: MEDIUM
- **Fix**: Add caplog assertion for error logging.

### [LS-006] Assert-free: Fire-and-forget mutation invalidator (2 functions)
- **File**: `tests/unit/cache/test_mutation_invalidator.py` (lines 497, 512)
- **Severity**: DEFECT | **Confidence**: HIGH
- **Evidence**: Test names claim "creates task" and "has name" but assert neither.
- **Fix**: Spy on `asyncio.create_task` to verify call.

### [LS-007] Assert-free: Polling scheduler run_once (3 functions)
- **File**: `tests/unit/automation/polling/test_polling_scheduler.py` (lines 173, 444, 511)
- **Severity**: DEFECT | **Confidence**: MEDIUM
- **Fix**: Assert evaluation cycle was entered.

### [LS-008] Assertion on wrong thing: Preload manifest check tests
- **File**: `tests/unit/api/test_preload_lambda_delegation.py` (lines 75, 103, 114)
- **Severity**: DEFECT | **Confidence**: HIGH
- **Evidence**: Tests replicate production logic inline rather than calling production code. Comments confirm: "Simulate the manifest check logic from process_project".
- **Fix**: Rewrite to call actual production function or delete.

---

## SMELL Findings

### Copy-paste clusters (16 findings, LS-009 through LS-024)

| ID | File | Count | Lines Each | Fix |
|----|------|-------|-----------|-----|
| LS-009 | `test_cache.py` stale fallback | 4 | ~40 | Parametrize status codes |
| LS-010 | `test_feature_flag.py` env vars | 4 | ~32 | Parametrize env values |
| LS-011 | `test_unit_schema.py` columns | 10 | ~6 | Parametrize col/dtype |
| LS-012 | `test_error_helpers.py` | 7 | ~6 | Parametrize |
| LS-013 | `test_client_extensions.py` case | 7 | ~5 | Parametrize |
| LS-014 | `test_models.py` retryable status | 4 | ~15 | Parametrize |
| LS-015 | `test_executor.py` resource paths | 6 | ~6 | Parametrize |
| LS-016 | `test_normalizers.py` phone+domain | 9 | ~5 | Parametrize both groups |
| LS-017 | `test_routes_admin_edge_cases.py` | 3 | ~21 | Parametrize inputs |
| LS-018 | `test_routes_dataframes.py` schema | 5 | ~13 | Parametrize entity type |
| LS-019 | `test_custom_field_descriptors.py` | 7 | ~5 | Parametrize |
| LS-020 | `test_base_schema.py` columns | 5 | ~7 | Parametrize |
| LS-021 | `test_pii.py` phone formats | 5 | ~7 | Parametrize |
| LS-022 | `test_session_healing.py` tiers | 4 | ~8 | Parametrize |
| LS-023 | `test_config.py` sections | 4 | ~7 | Parametrize |
| LS-024 | `test_config_schema.py` times | 4 | ~6 | Parametrize |

**Estimated LOC reduction from parametrization**: ~600-800 lines

### Broad exception assertions (3 findings, LS-025 through LS-027)

| ID | Files | Occurrences | Correct Type |
|----|-------|-------------|--------------|
| LS-025 | `test_retry.py` | 7 | `ClientError` |
| LS-026 | `test_common_models.py`, `test_result.py`, `test_cascade.py`, `test_cache_integration.py` | 5 | `ValidationError` / `FrozenInstanceError` |
| LS-027 | `test_section_edge_cases.py`, `test_join.py`, `test_edge_cases.py` | 4 | `SchemaError` / `ColumnNotFoundError` |

### Over-mocked tests (2 findings, LS-028 through LS-029)

| ID | File | Patches | Notes |
|----|------|---------|-------|
| LS-028 | `test_cache_warmer.py:558` | 24 | Lambda handler isolation; flag for future |
| LS-029 | `test_routes_query.py:100`, `test_routes_query_rows.py:81` | 29-38 | Core polars logic IS exercised despite patch count |

### Assert-free "does-not-raise" needing documentation (LS-030)
- 14 selected examples from 72 legitimate assert-free tests
- Most have clear naming (`_does_not_raise`, `_is_safe`)
- Several claim behavior in name but don't verify it

---

## Statistics

- Files scanned: 389
- Assert-free detected: 104 (32 flagged, 72 legitimate)
- Tautological candidates: 26 (8 confirmed, 18 false positives)
- Over-mocked (5+ patches): 96 (10 flagged, 86 necessary)
- Copy-paste clusters: 44 (16 flagged, 28 borderline)
- Broad exceptions: 16 occurrences (5 findings)
- **Total findings: 68 (28 DEFECT, 40 SMELL)**
