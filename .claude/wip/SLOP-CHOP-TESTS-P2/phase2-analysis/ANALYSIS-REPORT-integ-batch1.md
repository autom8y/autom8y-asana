---
type: qa
---

# Analysis Report: Integration Tests Batch 1

**Agent**: logic-surgeon
**Scope**: tests/integration/ (12 files, first batch)
**Date**: 2026-02-24

## Summary

Analyzed 12 integration test files for tautological assertions, assert-free test functions, broad exception handling, silent error catching, and copy-paste bloat. Found **15 findings** across the batch.

---

## Findings

### Finding P2B1-001: Assert-free test function with no behavioral verification
- Severity: DEFECT
- File: `tests/integration/test_custom_field_type_validation.py:14`
- Category: Assert-free test_ function
- Evidence: `test_text_field_accepts_string` has no assert statement. The comment `# Should not raise` documents intent but no assertion verifies the value was actually set or that the operation had any effect. The same pattern repeats in `test_text_field_accepts_none` (line 40), `test_number_field_accepts_int` (line 60), `test_number_field_accepts_float` (line 67), `test_number_field_accepts_decimal` (line 74), `test_number_field_accepts_none` (line 91), `test_date_field_accepts_iso_string` (line 210), `test_date_field_accepts_none` (line 227), `test_enum_field_accepts_string_gid` (line 111), `test_enum_field_accepts_dict_with_gid` (line 118), `test_enum_field_accepts_none` (line 155), `test_multi_enum_field_accepts_list` (line 166), `test_multi_enum_field_accepts_empty_list` (line 183), `test_multi_enum_field_accepts_none` (line 199), `test_people_field_accepts_list` (line 246), `test_people_field_accepts_empty_list` (line 263), `test_people_field_accepts_none` (line 269), `test_empty_string_accepted_for_text` (line 503), `test_unknown_field_type_no_validation` (line 510), `test_validation_with_missing_field` (line 519), `test_setitem_accepts_valid_value` (line 444), `test_setitem_with_gid` (line 451), `test_zero_decimal_accepted` (line 376), `test_negative_decimal_accepted` (line 383), `test_validation_by_gid_string` (line 394), `test_remove_is_allowed` (line 417).
- Confidence: HIGH -- 26 test functions contain zero assert statements, relying solely on "no exception raised" semantics. The test suite would pass even if `set()` were a no-op.

### Finding P2B1-002: Assert-free test function in traversal test
- Severity: DEFECT
- File: `tests/integration/test_hydration.py:366`
- Category: Assert-free test_ function
- Evidence: `test_traversal_stops_at_business` sets up mocks and mock data but contains zero assertions. The test body creates `business_task`, configures subtask mocks, and sets up `get_async` but never calls `_traverse_upward_async` or any function under test, and never asserts anything. The function ends after mock configuration with no act or assert phase.
- Confidence: HIGH -- the function has no assert statements and no invocation of the code under test. It is a dead test.

### Finding P2B1-003: Broad except Exception in cleanup code
- Severity: DEFECT
- File: `tests/integration/test_e2e_offer_write_proof.py:335`
- Category: Broad except Exception
- Evidence: `except Exception as e: print(f"\n--- Cleanup warning: {e} ---")` -- the cleanup block catches all exceptions and prints them, silently swallowing errors. If `delete_async` raises a non-network error (e.g., `TypeError`, `AttributeError` from a bug), the test still passes green. This is in a live API test where cleanup failure could leave orphaned resources.
- Confidence: MEDIUM -- cleanup exception swallowing is a common pattern, but this test is explicitly adversarial/e2e where cleanup failures should be visible. The test already uses `pytest.mark.integration` and skips without credentials, so this does not affect CI runs without `ASANA_PAT`.

### Finding P2B1-004: Copy-paste bloat in entity resolver E2E tests
- Severity: SMELL
- File: `tests/integration/test_entity_resolver_e2e.py:156-450`
- Category: Egregious copy-paste bloat
- Evidence: The three test methods in `TestEntityResolverE2E` (`test_resolve_unit_with_mocked_discovery`, `test_resolve_unit_not_found_returns_error`, `test_resolve_batch_preserves_order`) each contain an identical ~40-line block of mock setup code: the `mock_discovery` async function, the 5-way `with patch(...)` context manager, the `mock_client` setup, the `create_app()` call, the two auth dependency overrides, and the `try/finally` with `app.dependency_overrides.clear()`. The only variation between the three methods is the request payload and assertions. This block is duplicated 3 times (lines 171-261, 271-347, 354-450). Variation delta: only the JSON payload and the assertions differ (~10 lines each). A shared fixture or helper method could eliminate ~90 lines of duplication.
- Confidence: HIGH -- the three blocks are structurally identical with trivial differences.

### Finding P2B1-005: Copy-paste bloat in cascading field resolution production scenarios
- Severity: SMELL
- File: `tests/integration/test_cascading_field_resolution.py:524-656`
- Category: Egregious copy-paste bloat
- Evidence: `test_scenario_chiropractic_unit_with_known_phone` (lines 524-592) and `test_scenario_second_chiropractic_unit` (lines 594-656) are nearly identical. Both create the same mock hierarchy (Business -> UnitHolder -> Unit), configure the same `side_effect` for `get_async`, set up the same `detect_entity_type` patches, resolve `Office Phone`, build a DataFrame, create a `GidLookupIndex`, and assert a GID lookup. The only variation is the phone number, GID values, and business name. Variation delta: 6 string literals differ.
- Confidence: HIGH -- the two methods are structurally identical with parametric differences that could be expressed as `@pytest.mark.parametrize`.

### Finding P2B1-006: Copy-paste bloat in GID validation client tests
- Severity: SMELL
- File: `tests/integration/test_gid_validation_edge_cases.py:181-296`
- Category: Egregious copy-paste bloat
- Evidence: `TestClientGIDValidation` contains 7 test methods (`test_get_async_validates_task_gid`, `test_add_tag_async_validates_both_gids`, `test_remove_tag_async_validates_both_gids`, `test_move_to_section_async_validates_gids`, `test_set_assignee_async_validates_both_gids`, `test_add_to_project_async_validates_gids`, `test_remove_from_project_async_validates_gids`) that all follow an identical pattern: import `asyncio` and `pytest` (redundantly, since already imported at module level), define an inner `async def run_test()`, call `asyncio.run(run_test())`. The inner function in each case just does `pytest.raises(ValidationError)` around a client call with an invalid GID. The redundant `import pytest` inside each function is a strong signal of mechanical duplication.
- Confidence: HIGH -- identical structural pattern repeated 7 times with redundant imports inside each function body.

### Finding P2B1-007: Redundant import of pytest inside test functions
- Severity: SMELL
- File: `tests/integration/test_gid_validation_edge_cases.py:185,198,213,228,249,265,283`
- Category: Unreviewed-output signal
- Evidence: Seven test functions in `TestClientGIDValidation` each contain `import pytest` despite `pytest` already being imported at module level (line 7). This is a mechanical duplication signal -- each function was likely generated independently without awareness of module scope. The redundant import is harmless at runtime but is inconsistent with the codebase convention (no other test file in this batch re-imports pytest inside functions).
- Confidence: HIGH -- verifiable against the other 11 files in this batch, none of which re-import pytest inside functions.

### Finding P2B1-008: Copy-paste bloat in SaveSession GID validation tests
- Severity: SMELL
- File: `tests/integration/test_gid_validation_edge_cases.py:98-170`
- Category: Egregious copy-paste bloat
- Evidence: `TestSaveSessionGIDValidation` contains 7 test methods that follow an identical pattern: create `SaveSession(client_fixture)`, call `session.<method>(task_fixture, "invalid-...")` inside `pytest.raises(ValidationError)`. The only variation is the method name and the invalid string. These 7 methods could be a single parametrized test with `@pytest.mark.parametrize("method_name, invalid_arg", [...])`.
- Confidence: HIGH -- structurally identical with a single varying parameter (the method name).

### Finding P2B1-009: Duplicate subset assertion across two test classes
- Severity: SMELL
- File: `tests/integration/test_hydration_cache_integration.py:104,296`
- Category: Egregious copy-paste bloat
- Evidence: `TestTraversalUsesStandardFields.test_standard_fields_include_detection_fields` (line 104) and `TestStandardSupersetOfDetection.test_all_detection_fields_in_standard` (line 296) both assert that `DETECTION_OPT_FIELDS` is a subset of `STANDARD_TASK_OPT_FIELDS`. One uses `detection_set.issubset(standard_set)`, the other iterates with a for-loop. Same assertion, two locations. Additionally `test_detection_fields_count` hardcodes `== 4` and `test_standard_fields_count` hardcodes `== 15` -- these are brittle to any field additions.
- Confidence: LOW -- the duplication between the two classes is modest, and the hardcoded counts are arguably intentional contract tests.

### Finding P2B1-010: Test uses asyncio.run() inside sync test -- inconsistent with codebase convention
- Severity: SMELL
- File: `tests/integration/test_gid_validation_edge_cases.py:183-191`
- Category: Unreviewed-output signal
- Evidence: Tests in `TestClientGIDValidation` use `asyncio.run()` to run async code inside sync test functions, while the rest of the test suite uses `@pytest.mark.asyncio`. If these tests are ever collected in the same session as `pytest-asyncio` tests, `asyncio.run()` will fail with `RuntimeError: cannot be called from a running event loop` on some pytest configurations. The codebase convention (visible in `test_detection.py`, `test_hydration.py`, `test_cache_optimization_e2e.py`) is to use `@pytest.mark.asyncio` on test classes/methods. The `test_lifecycle_smoke.py` file uses a custom `_run_async()` helper with `asyncio.new_event_loop()` specifically to avoid this problem, further confirming `asyncio.run()` is not the project convention.
- Confidence: MEDIUM -- whether this causes actual failures depends on the test runner configuration, but the pattern is inconsistent with codebase convention.

### Finding P2B1-011: Test name contradicts test behavior (tautological)
- Severity: DEFECT
- File: `tests/integration/test_custom_field_type_validation.py:493-501`
- Category: Tautological test
- Evidence: `test_boolean_rejected_as_number` says in the docstring "Boolean should not be accepted as number" but the test body does the opposite -- it asserts `accessor.set("Budget", True)` does NOT raise and then asserts `accessor.get("Budget") is True`. The comment says "Note: bool is a subclass of int in Python, so this will be accepted. This is consistent with Python's type system." The test name claims rejection but the test asserts acceptance. The test would pass with any implementation that either accepts or silently ignores booleans. The name and docstring are misleading -- the actual test is "boolean accepted as number."
- Confidence: HIGH -- the test name says "rejected" but the body asserts "accepted". The test cannot fail regardless of behavior.

### Finding P2B1-012: Assert-free test functions in custom field validation (batch summary)
- Severity: DEFECT
- File: `tests/integration/test_custom_field_type_validation.py` (26 functions)
- Category: Assert-free test_ function (batch summary)
- Evidence: This is a summary finding for the 26 individual assert-free functions identified in P2B1-001. Each follows the pattern: create accessor, call `accessor.set(field, valid_value)` with only a `# Should not raise` comment. A proper test would call `accessor.get(field)` and assert the stored value matches, or assert on `accessor.to_api_dict()`. Since there is no behavioral assertion, these tests would pass if `set()` were defined as `def set(self, *args, **kwargs): pass`.
- Confidence: HIGH -- provably passes with a no-op implementation.

### Finding P2B1-013: Stale test for removed adapter class
- Severity: SMELL
- File: `tests/integration/test_lifecycle_smoke.py:1695-1711`
- Category: Unreviewed-output signal
- Evidence: `test_completion_adapter_returns_empty` is `@pytest.mark.skip` with reason `"_CompletionAdapter removed: CompletionService is now used directly without a shim adapter"`. This is a dead test that was left behind after the adapter was removed. The skip marker preserves the test function but it can never run and provides no value.
- Confidence: HIGH -- the skip reason explicitly states the tested class no longer exists.

### Finding P2B1-014: Process descriptor introspection uses bare except
- Severity: DEFECT
- File: `tests/integration/test_entity_write_smoke.py:993-998`
- Category: Broad except Exception
- Evidence: In `test_process_has_descriptors`, the loop `for attr_name in dir(Process)` contains `except Exception: continue` around `getattr(Process, attr_name)`. This silently swallows any exception from property descriptors, including `AttributeError` that might indicate a broken descriptor. If a descriptor raises an unexpected error, the test will simply skip it and potentially undercount descriptors, causing a false pass.
- Confidence: MEDIUM -- `getattr` on class attributes can raise for descriptors with side effects, so the except has some justification, but `except (AttributeError, TypeError)` would be more precise.

### Finding P2B1-015: Lifecycle smoke test helper creates fresh event loops (inconsistent with codebase)
- Severity: SMELL
- File: `tests/integration/test_lifecycle_smoke.py:25-35`
- Category: Unreviewed-output signal
- Evidence: `_run_async()` creates a new event loop per call via `asyncio.new_event_loop()`. While this avoids the `asyncio.run()` issue noted in P2B1-010, it is inconsistent with the codebase convention of using `@pytest.mark.asyncio`. The entire file uses `_run_async()` inside sync `def test_*` methods instead of `async def test_*` with `@pytest.mark.asyncio`. This means tests do not benefit from pytest-asyncio fixtures or scope management. 45+ test methods in this file use this pattern. However, the docstring explains the rationale ("Using asyncio.get_event_loop() fails when earlier async tests close the default loop"), suggesting this is a deliberate workaround.
- Confidence: LOW -- the helper has a documented rationale, but the pattern diverges from every other integration test file.

---

## Statistics

| Category | Count |
|---|---|
| Assert-free test_ functions (DEFECT) | 2 findings covering ~28 functions |
| Tautological tests (DEFECT) | 1 |
| Broad except Exception (DEFECT) | 2 |
| Copy-paste bloat (SMELL) | 6 |
| Unreviewed-output signals (SMELL) | 4 |
| **Total findings** | **15** |

## Files with No Findings

- `tests/integration/test_batch_api.py` -- clean, well-structured tests with proper assertions
- `tests/integration/test_cache_optimization_e2e.py` -- clean, all tests have behavioral assertions
- `tests/integration/test_detection.py` -- clean, thorough parametrized tests with assertions

## Handoff Notes

- P2B1-001 and P2B1-012 are the highest-impact findings: 26 test functions in `test_custom_field_type_validation.py` have no assertions at all. These tests provide minimal confidence in the validation system.
- P2B1-004 (entity resolver E2E bloat) is the most egregious copy-paste instance, with ~90 lines of identical setup duplicated 3 times.
- P2B1-011 is a misleading test where the name contradicts the assertion. Should be renamed or the behavior clarified.
