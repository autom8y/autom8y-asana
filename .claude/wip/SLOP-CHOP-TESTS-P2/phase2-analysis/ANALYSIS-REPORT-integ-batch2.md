---
type: qa
---

# Analysis Report: Integration Tests Batch 2

**Agent**: logic-surgeon
**Scope**: tests/integration/ (second batch) -- 21 files analyzed
**Date**: 2026-02-24

---

## Summary

| Category | DEFECT | SMELL | Total |
|----------|--------|-------|-------|
| Assert-free test_ functions | 13 | -- | 13 |
| Tautological / shallow assertions | 7 | -- | 7 |
| Broad except Exception | -- | 3 | 3 |
| Catch-and-pass-silently | 1 | -- | 1 |
| Copy-paste bloat | -- | 3 | 3 |
| **Total** | **21** | **6** | **27** |

---

## Findings

### Finding P2B2-001: Assert-free test_recommended_pattern_separate_clients

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:166
- Category: Assert-free test_ function
- Evidence: `test_recommended_pattern_separate_clients` body is only `pass`. No assertions, no pytest.raises, no side-effect verification. This function is named `test_*` so pytest collects and runs it, and it always passes regardless of implementation correctness.
- Confidence: HIGH

### Finding P2B2-002: Assert-free test_anti_pattern_switching_workspace_context

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:193
- Category: Assert-free test_ function
- Evidence: `test_anti_pattern_switching_workspace_context` body is only `pass`. Always passes. Named `test_*` so collected by pytest.
- Confidence: HIGH

### Finding P2B2-003: Assert-free test_field_name_resolution_workspace_specific

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:227
- Category: Assert-free test_ function
- Evidence: `test_field_name_resolution_workspace_specific` body is only `pass`. Always passes. Named `test_*` so collected by pytest.
- Confidence: HIGH

### Finding P2B2-004: Assert-free test_field_resolver_requires_workspace_context

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:255
- Category: Assert-free test_ function
- Evidence: `test_field_resolver_requires_workspace_context` body is only `pass`. Always passes. Named `test_*` so collected by pytest.
- Confidence: HIGH

### Finding P2B2-005: Tautological assertion in test_task_belongs_to_single_workspace

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:75
- Category: Tautological test
- Evidence: `assert task.gid == "3000000001"` -- the test creates `Task(gid="3000000001", ...)` on line 68 and then asserts the GID equals the value it was just constructed with. This always passes. The test claims to document workspace isolation behavior but exercises none of that behavior.
- Confidence: HIGH

### Finding P2B2-006: Tautological assertion in test_custom_fields_vary_by_workspace

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:104
- Category: Tautological test
- Evidence: `assert task.custom_fields is not None` -- the test assigns `task.custom_fields = {...}` on line 93 and then asserts it is not None. This always passes. No workspace-varying behavior is tested.
- Confidence: HIGH

### Finding P2B2-007: Tautological assertion in test_team_membership_workspace_specific

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:129
- Category: Tautological test
- Evidence: `assert task.gid == "5000000001"` -- constructs Task with that GID and asserts same GID back. No workspace membership behavior tested.
- Confidence: HIGH

### Finding P2B2-008: Tautological assertions in test_project_scope_is_workspace_scoped

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:156-157
- Category: Tautological test
- Evidence: `assert project.gid == "6000000001"` and `assert task.gid == "7000000001"` -- both values are the constructor arguments. No workspace scoping behavior is exercised.
- Confidence: HIGH

### Finding P2B2-009: Unreferenced mock_client in documentation tests

- Severity: DEFECT
- File: tests/integration/test_workspace_switching.py:64,87
- Category: Dead code in test
- Evidence: In `test_task_belongs_to_single_workspace` (line 64) and `test_custom_fields_vary_by_workspace` (line 87), `mock_client = create_mock_client_for_workspace()` is called but `mock_client` is never used in either test. The variable is assigned and then abandoned, suggesting the tests were intended to exercise the mock client but the actual test logic was never implemented.
- Confidence: HIGH

### Finding P2B2-010: Assert-free test_session_isolation_prevents_cross_contamination

- Severity: DEFECT
- File: tests/integration/test_savesession_edge_cases.py:108-135
- Category: Assert-free test_ function
- Evidence: `test_session_isolation_prevents_cross_contamination` has NO assertions at all. The test creates sessions, tracks tasks, and modifies them, but never asserts any isolation property. The comments say "This doesn't change what session would have committed" but no commit is performed and no verification occurs. The test always passes regardless of session behavior.
- Confidence: HIGH

### Finding P2B2-011: Shallow assertion in test_same_entity_in_different_sessions

- Severity: DEFECT
- File: tests/integration/test_savesession_edge_cases.py:78-105
- Category: Tautological test
- Evidence: The assertions `assert changes1 is not None` and `assert changes2 is not None` on lines 104-105 only verify that `session.preview()` returns a non-None value. The comment says "Both sessions should see their own independent changes" and "(Note: Actual test would verify the preview output)" -- indicating the meaningful assertions were never implemented. The test passes as long as `preview()` returns anything, even if session isolation is broken.
- Confidence: HIGH

### Finding P2B2-012: Shallow assertion in test_session_transitions_from_empty_to_tracked

- Severity: DEFECT
- File: tests/integration/test_savesession_edge_cases.py:199-222
- Category: Tautological test
- Evidence: `assert preview2 is not None` is the only assertion. The test is supposed to verify state transitions (empty -> tracked), but only checks that preview returns non-None. The comments `# (Would verify empty state)` and `# (Would verify task appears in preview)` confirm the real assertions were never written.
- Confidence: HIGH

### Finding P2B2-013: Assert-free test_session_retracking_same_entity_is_idempotent

- Severity: DEFECT
- File: tests/integration/test_savesession_edge_cases.py:225-248
- Category: Assert-free test_ function
- Evidence: `test_session_retracking_same_entity_is_idempotent` has NO assertions. It calls `track()` three times and modifies the task, but never verifies idempotent behavior. Comment says "Should only see one change (from Track snapshot to current state) not multiple snapshots" but this is never asserted.
- Confidence: HIGH

### Finding P2B2-014: Assert-free test_session_tracks_creates_and_modifications

- Severity: DEFECT
- File: tests/integration/test_savesession_edge_cases.py:291-313
- Category: Assert-free / shallow test
- Evidence: The only assertion is `assert preview is not None`. The test is supposed to verify that SaveSession "correctly distinguishes between creates and modifications" but only checks preview is not None. Comment: `# (Would verify different operation types)` confirms the real assertion was never written.
- Confidence: HIGH

### Finding P2B2-015: Catch exception and pass silently in test_session_context_manager_cleanup_on_error

- Severity: DEFECT
- File: tests/integration/test_savesession_edge_cases.py:257-281
- Category: Catches errors and passes silently
- Evidence: Lines 267-274 contain:
  ```python
  try:
      async with SaveSession(mock_client) as session:
          ...
          raise ValueError("Simulated error during session")
  except ValueError:
      pass  # Expected
  ```
  While this specific pattern is testing error recovery (intentionally raising and catching), the subsequent session2 assertions only verify `result is not None`, never verifying any cleanup property. The test name says "cleanup_on_error" but no cleanup is actually verified. The catch+pass pattern here masks the lack of meaningful assertions rather than being a deliberate error-handling test.
- Confidence: MEDIUM

### Finding P2B2-016: Tests manually raise the exception they claim to test

- Severity: DEFECT
- File: tests/integration/test_savesession_partial_failures.py:50-80, 83-123, 126-156, 207-251
- Category: Tautological test (testing self-raised exception, not production code path)
- Evidence: Four tests (`test_save_async_raises_savesession_error_on_failure`, `test_save_async_error_contains_full_result`, `test_save_async_error_message_shows_all_failures`, `test_save_async_error_includes_docstring_example`) all construct a `SaveSessionError` and then `raise` it themselves:
  ```python
  with pytest.raises(SaveSessionError) as exc_info:
      raise SaveSessionError(result)
  ```
  or:
  ```python
  try:
      raise SaveSessionError(result)
  except SaveSessionError as e:
      ...
  ```
  These tests verify that a manually constructed exception contains the data that was manually put into it. They do NOT test that `Task.save_async()` actually raises `SaveSessionError` when the API fails. The test names imply they test `save_async()` behavior (e.g., "SaveSessionError from save_async() contains full SaveResult") but `save_async()` is never called. Only `test_save_async_without_client_raises_value_error` (line 159) and `test_save_async_success_returns_updated_task` (line 171) actually exercise production code.
- Confidence: HIGH

### Finding P2B2-017: Assert-free skipped test stubs in unified cache integration

- Severity: DEFECT
- File: tests/integration/test_unified_cache_integration.py:191-230
- Category: Assert-free test_ function
- Evidence: Three test methods inside `TestProjectDataFrameBuilderUnifiedIntegration` have bodies that are only `pass`: `test_builder_with_unified_store_branches_correctly` (line 191), `test_builder_without_unified_store_uses_existing_path` (line 201), and `test_unified_path_fetches_from_store` (line 213). The class is decorated with `@MIGRATION_REQUIRED` (a `pytest.mark.skip`), so these tests are skipped at runtime. However, they remain as dead code indicating incomplete migration.
- Confidence: MEDIUM -- these are explicitly skipped with rationale, but three `pass`-only stubs remain indefinitely.

### Finding P2B2-018: Performance tests with no behavioral assertion

- Severity: DEFECT
- File: tests/integration/test_unified_cache_integration.py:562-624
- Category: Assert-free test_ function (performance timing)
- Evidence: Both `test_unified_store_lookup_timing` (line 563) and `test_legacy_coordinator_lookup_timing` (line 597) have NO assertions. They run 100 lookups and print timing to stdout, but never assert anything. These tests always pass, providing no regression protection. A proper performance test would assert timing bounds.
- Confidence: HIGH

### Finding P2B2-019: Entire test suite is commented out as triple-quoted string

- Severity: DEFECT
- File: tests/integration/persistence/test_live_api.py:42-306
- Category: Assert-free test_ function / dead test code
- Evidence: The actual test classes (TestLiveAPICreate, TestLiveAPIUpdate, TestLiveAPIBatch, TestLiveAPIDelete, TestLiveAPIErrors) are wrapped in a triple-quoted string (lines 42-306), making them commented-out dead code. The only live tests are in `TestIntegrationInfrastructure` (lines 314-334), which consist of environment-variable checks -- not persistence behavior tests. The file's stated purpose ("Part 6: Live API Integration Tests") is misleading since no live API integration testing is performed.
- Confidence: HIGH

### Finding P2B2-020: No assertion on fetch_count unchanged in test_resolve_batch_caches_results

- Severity: DEFECT
- File: tests/integration/test_platform_performance.py:207-236
- Category: Missing assertion (incomplete test)
- Evidence: `test_resolve_batch_caches_results` tracks `fetch_count` and asserts it equals 2 after the first batch. Then it performs a second `resolve_batch` with the same keys (line 233) and comments "Note: HierarchyAwareResolver cache is within the resolver instance so second call should still hit cache (fetch_count unchanged)". However, it NEVER asserts `fetch_count == 2` after the second call. The caching behavior the test claims to verify is never actually asserted.
- Confidence: HIGH

### Finding P2B2-021: Copy-paste bloat in test_savesession_partial_failures.py

- Severity: SMELL
- File: tests/integration/test_savesession_partial_failures.py:49-251
- Category: Copy-paste bloat
- Evidence: Four tests (`test_save_async_raises_savesession_error_on_failure`, `test_save_async_error_contains_full_result`, `test_save_async_error_message_shows_all_failures`, `test_save_async_error_includes_docstring_example`) share a nearly identical pattern: construct SaveError/SaveResult, `raise SaveSessionError(result)`, then catch and inspect. The variation between them is minimal -- they test slightly different attributes of the same self-raised error. Combined with Finding P2B2-016, these four tests could be collapsed into one or two parameterized tests.
- Confidence: MEDIUM

### Finding P2B2-022: Copy-paste bloat across workspace switching documentation tests

- Severity: SMELL
- File: tests/integration/test_workspace_switching.py:47-157
- Category: Copy-paste bloat
- Evidence: `TestWorkspaceSwitching` contains four `test_*` methods that all follow the exact same pattern: create mock client (unused), create a model instance with a hardcoded GID, assert the GID equals the hardcoded value. The variation delta between `test_task_belongs_to_single_workspace`, `test_custom_fields_vary_by_workspace`, `test_team_membership_workspace_specific`, and `test_project_scope_is_workspace_scoped` is limited to which model class is instantiated and which attribute is trivially checked. None exercise any actual workspace behavior.
- Confidence: HIGH

### Finding P2B2-023: Broad except Exception in fixture cleanup (conftest)

- Severity: SMELL
- File: tests/integration/automation/polling/conftest.py:158,196,227
- Category: Broad except Exception
- Evidence: Three fixture teardown blocks catch `except Exception: pass` after `await asana_client.tasks.delete_async(task.gid)`. This is in cleanup code within yield-fixtures, which is a legitimate pattern for test cleanup that should not fail the test suite if cleanup fails. The comments indicate this is intentional ("Task may already be deleted or inaccessible - that's fine").
- Confidence: LOW -- fixture cleanup is the one context where broad except + pass is reasonable.

### Finding P2B2-024: Broad except Exception in e2e fixture cleanup

- Severity: SMELL
- File: tests/integration/automation/polling/test_end_to_end.py:83,119
- Category: Broad except Exception
- Evidence: Same pattern as P2B2-023, in yield-fixture teardown. `except Exception: pass` after task deletion. Legitimate cleanup pattern.
- Confidence: LOW

### Finding P2B2-025: Broad except Exception in SQS fixture cleanup

- Severity: SMELL
- File: tests/integration/events/test_sqs_integration.py:74
- Category: Broad except Exception
- Evidence: `except Exception: pass` in the `sqs_queue` fixture teardown after `client.delete_queue()`. Legitimate cleanup pattern for infrastructure teardown.
- Confidence: LOW

### Finding P2B2-026: Copy-paste bloat in test_savesession_edge_cases.py session creation

- Severity: SMELL
- File: tests/integration/test_savesession_edge_cases.py:58-300 (12 occurrences)
- Category: Copy-paste bloat
- Evidence: `create_mock_client()` is called at the start of nearly every test method (12 times). Each test creates independent `SaveSession(mock_client)` instances with the same mock setup. Every test method repeats the pattern:
  ```python
  mock_client = create_mock_client()
  async with SaveSession(mock_client) as session:
      task = Task(gid="...", name="...")
      session.track(task)
  ```
  A pytest fixture would eliminate the repeated `create_mock_client()` call and provide cleaner teardown semantics.
- Confidence: LOW -- this is idiomatic pytest usage, just slightly verbose.

---

## Files with No Findings

The following files had no defects or smells detected:

- `tests/integration/test_name_resolution_failures.py` -- well-structured tests with meaningful assertions for every test case.
- `tests/integration/test_staleness_flow.py` -- thorough assertions on TTL values, counts, and batch behavior.
- `tests/integration/test_stories_cache_integration.py` -- good integration tests with specific assertions on cache behavior, sort order, and metrics.
- `tests/integration/test_unified_cache_success_criteria.py` -- well-organized success criteria tests with specific assertions.
- `tests/integration/test_unit_cascade_resolution.py` -- real integration tests with meaningful hierarchy and cache assertions.
- `tests/integration/test_workspace_registry.py` -- thorough registry tests with parametrized cases and proper edge case coverage.
- `tests/integration/automation/polling/test_action_executor_integration.py` -- real API integration tests with proper assertions.
- `tests/integration/automation/polling/test_end_to_end.py` -- comprehensive E2E tests with real API verification.
- `tests/integration/automation/polling/test_trigger_evaluator_integration.py` -- thorough trigger evaluation tests with boundary cases.
- `tests/integration/automation/workflows/test_conversation_audit_e2e.py` -- well-structured lifecycle test with specific count assertions.
- `tests/integration/events/test_sqs_integration.py` -- proper integration tests with real SQS verification.
- `tests/integration/persistence/test_action_batch_integration.py` -- good batch integration tests with proper assertions.
- `tests/integration/api/test_preload_manifest_check.py` -- well-structured branch coverage tests with observable assertions.

---

## Severity Distribution

| Severity | Count |
|----------|-------|
| HIGH confidence DEFECT | 18 |
| MEDIUM confidence DEFECT | 3 |
| LOW confidence SMELL | 4 |
| MEDIUM confidence SMELL | 2 |

## Hotspot Files

| File | Finding Count | Notes |
|------|--------------|-------|
| test_workspace_switching.py | 9 | Dominated by assert-free and tautological documentation tests |
| test_savesession_edge_cases.py | 6 | Multiple assert-free or shallow-assertion tests |
| test_savesession_partial_failures.py | 2 | Tests raise exceptions themselves rather than testing production paths |
| test_unified_cache_integration.py | 2 | Performance tests without assertions, pass-only stubs |
| test_live_api.py | 1 | Entire test suite is commented out as triple-quoted string |
| test_platform_performance.py | 1 | Missing cache verification assertion |
