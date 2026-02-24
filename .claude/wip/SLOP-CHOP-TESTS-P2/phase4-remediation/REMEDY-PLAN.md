---
type: triage
phase: 4
agent: remedy-smith
produced: 2026-02-24
scope: tests/integration/, tests/validation/, tests/benchmarks/, tests/_shared/
source-reports:
  - phase1-detection/DETECTION-REPORT.md
  - phase2-analysis/ANALYSIS-REPORT-integ-batch1.md
  - phase2-analysis/ANALYSIS-REPORT-integ-batch2.md
  - phase2-analysis/ANALYSIS-REPORT-val-bench.md
  - phase3-decay/DECAY-REPORT.md
---

# REMEDY-PLAN: Slop-Chop Quality Gate — Test Suite Phase 2

**Findings inventory**: Phase 1: 0 findings. Phase 2: 51 findings (29 DEFECT, 22 SMELL). Phase 3: 17 findings (all SMELL/TEMPORAL).
**Total remediation items**: 68 findings — all accounted for below.

---

## Coverage Map

| Finding ID(s) | Remedy Item | Classification |
|---|---|---|
| P2B1-001, P2B1-012 | RS-001 | MANUAL |
| P2B1-002 | RS-002 | MANUAL |
| P2B1-003 | RS-003 | MANUAL |
| P2B1-004 | RS-004 | MANUAL |
| P2B1-005 | RS-005 | MANUAL |
| P2B1-006, P2B1-007, P2B1-008, P2B1-010 | RS-006 | MANUAL |
| P2B1-009 | RS-007 | MANUAL |
| P2B1-011 | RS-008 | AUTO |
| P2B1-013 | RS-009 | MANUAL |
| P2B1-014 | RS-010 | AUTO |
| P2B1-015 | RS-011 | MANUAL |
| P2B2-001 through P2B2-004 | RS-012 | MANUAL |
| P2B2-005 through P2B2-008 | RS-013 | MANUAL |
| P2B2-009 | RS-014 | MANUAL |
| P2B2-010 through P2B2-014 | RS-015 | MANUAL |
| P2B2-015 | RS-016 | MANUAL |
| P2B2-016 | RS-017 | MANUAL |
| P2B2-017 | RS-018 | MANUAL |
| P2B2-018 | RS-019 | AUTO |
| P2B2-019 | RS-020 | MANUAL |
| P2B2-020 | RS-021 | AUTO |
| P2B2-021, P2B2-022, P2B2-026 | RS-022 | MANUAL |
| P2B2-023, P2B2-024, P2B2-025 | RS-023 | No fix needed |
| P2-001 | RS-024 | AUTO |
| P2-002 | RS-025 | MANUAL |
| P2-003 | RS-026 | MANUAL |
| P2-004 | RS-027 | MANUAL |
| P2-005, P2-006 | RS-028 | MANUAL |
| P2-007 | RS-029 | MANUAL |
| P2-008 | RS-030 | No fix needed |
| P2-009 | RS-031 | MANUAL |
| P2-010 | RS-032 | MANUAL |
| P3-001, P3-002 | RS-033 | MANUAL |
| P3-003 | RS-034 | MANUAL |
| P3-004 | RS-035 | MANUAL |
| P3-005 | RS-036 | MANUAL |
| P3-006 | RS-037 | MANUAL |
| P3-007 | RS-038 | MANUAL |
| P3-008 | RS-039 | MANUAL |
| P3-009 | RS-040 | MANUAL |
| P3-010 | RS-041 | MANUAL |
| P3-011 | RS-042 | MANUAL |
| P3-012 | RS-043 | MANUAL |
| P3-013 | RS-044 | MANUAL |
| P3-014 | RS-045 | MANUAL |
| P3-015 | RS-046 | MANUAL |
| P3-016 | RS-047 | MANUAL |
| P3-017 | RS-048 | MANUAL |

---

## Section 1: AUTO Patches

AUTO patches are mechanically safe fixes requiring no behavioral judgment. Apply with the commands shown; run tests after each patch.

---

### RS-008: Rename misleading test to match actual behavior (AUTO)

**Source**: P2B1-011 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_custom_field_type_validation.py`
**Lines**: 493-501
**Classification**: AUTO -- the name contradicts observable behavior provably. The fix is a rename plus docstring update; no behavioral change is introduced.

**Patch**:

```diff
-    def test_boolean_rejected_as_number(self):
-        """Boolean should not be accepted as number (bool is int subclass)."""
+    def test_boolean_accepted_as_number(self):
+        """Boolean is accepted as number because bool is a subclass of int in Python."""
         accessor = CustomFieldAccessor(
             data=[{"gid": "1", "name": "Budget", "resource_subtype": "number"}]
         )
-        # Note: bool is a subclass of int in Python, so this will be accepted
-        # This is consistent with Python's type system
-        accessor.set("Budget", True)  # Allowed because bool is int subclass
+        accessor.set("Budget", True)  # bool is int subclass; accepted by Python type system
         assert accessor.get("Budget") is True
```

**Application**: Edit lines 493-501 in `tests/integration/test_custom_field_type_validation.py`. No test logic changes. Run `pytest tests/integration/test_custom_field_type_validation.py::TestValidationEdgeCases::test_boolean_accepted_as_number -v` to confirm collection and pass.

**Effort**: trivial

---

### RS-010: Narrow bare except to specific exception types (AUTO)

**Source**: P2B1-014 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_entity_write_smoke.py`
**Lines**: 995-996
**Classification**: AUTO -- the correct exception types for `getattr` failures on class attributes are `AttributeError` and `TypeError`. This is an unambiguous narrowing with no behavioral ambiguity.

**Patch**:

```diff
         for attr_name in dir(Process):
             try:
                 attr = getattr(Process, attr_name)
-            except Exception:
+            except (AttributeError, TypeError):
                 continue
```

**Application**: Edit line 995 in `tests/integration/test_entity_write_smoke.py`. Run `pytest tests/integration/test_entity_write_smoke.py::test_process_has_descriptors -v` to confirm pass.

**Effort**: trivial

---

### RS-019: Add timing assertions to performance tests (AUTO)

**Source**: P2B2-018 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_unified_cache_integration.py`
**Lines**: 593-594 and 622-624
**Classification**: AUTO -- adding a reasonable upper-bound assertion (1000ms for 100 iterations) converts assertion-free tests to meaningful regression gates. The bound is intentionally loose to avoid flakiness on CI runners.

**Patch for `test_unified_store_lookup_timing` (after line 594)**:

```diff
         # Log timing (informational, no assertion)
         print(f"\n100 unified store lookups: {elapsed_ms:.2f}ms")
+        assert elapsed_ms < 1000.0, (
+            f"100 unified store lookups took {elapsed_ms:.2f}ms, expected < 1000ms"
+        )
```

**Patch for `test_legacy_coordinator_lookup_timing` (after line 624)**:

```diff
         # Log timing (informational, no assertion)
         print(f"\n100 legacy coordinator lookups: {elapsed_ms:.2f}ms")
+        assert elapsed_ms < 1000.0, (
+            f"100 legacy coordinator lookups took {elapsed_ms:.2f}ms, expected < 1000ms"
+        )
```

**Application**: Edit `tests/integration/test_unified_cache_integration.py` at lines 594 and 624. Run `pytest tests/integration/test_unified_cache_integration.py::TestPerformanceTiming -v` to confirm pass. If the bound is too tight on CI, raise to `2000.0`.

**Effort**: trivial

---

### RS-021: Add missing cache-hit assertion after second batch resolve (AUTO)

**Source**: P2B2-020 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_platform_performance.py`
**Lines**: 233-237
**Classification**: AUTO -- the missing assertion is explicitly documented in the test comment. The correct value (`fetch_count == 2`, unchanged after the cached second call) is stated in the comment on lines 235-236. This is not a judgment call.

**Patch**:

```diff
         # Second fetch should hit cache
         results2 = await resolver.resolve_batch(keys=keys)
         assert len(results2) == 2
         # Note: HierarchyAwareResolver cache is within the resolver instance
         # so second call should still hit cache (fetch_count unchanged)
+        assert fetch_count == 2, (
+            f"Cache miss on second resolve_batch: fetch_count advanced to {fetch_count}, expected 2"
+        )
```

**Application**: Insert after line 236 in `tests/integration/test_platform_performance.py`. Run `pytest tests/integration/test_platform_performance.py::TestHierarchyAwareResolver::test_resolve_batch_caches_results -v` to confirm pass.

**Effort**: trivial

---

### RS-024: Replace tautological length assertion with meaningful bound (AUTO)

**Source**: P2-001 (ANALYSIS-REPORT-val-bench.md)
**File**: `tests/validation/persistence/test_concurrency.py`
**Lines**: 212
**Classification**: AUTO -- `len(levels) >= 0` is a mathematical tautology for any list. The minimally correct fix is `len(levels) >= 1` (levels must be non-empty after a valid concurrent build). This does not require knowledge of expected entity counts.

**Patch**:

```diff
         # Graph should be in consistent state (last build wins)
         levels = graph.get_levels()
-        assert len(levels) >= 0  # Just verify it doesn't crash
+        assert len(levels) >= 1, (
+            f"get_levels() returned empty result after concurrent graph build: {levels!r}"
+        )
```

**Application**: Edit line 212 in `tests/validation/persistence/test_concurrency.py`. Run `pytest tests/validation/persistence/test_concurrency.py -k "test_concurrent_graph" -v` to confirm pass. If the exact entity count is known from test setup (appears to be 10 from the analysis report), a stricter assertion `assert sum(len(level) for level in levels) == 10` is preferred but requires confirming the setup count.

**Effort**: trivial

---

## Section 2: MANUAL Instructions

MANUAL fixes require behavioral judgment, architectural understanding, or verification against production code paths before implementation. Every item includes the flaw, expected correct behavior, recommended approach, effort estimate, and priority.

Priority definitions: P1 = blocking (gate-relevant DEFECT), P2 = significant improvement, P3 = advisory (SMELL or TEMPORAL).

---

### RS-001: Write behavioral assertions for 26 assert-free custom field validation tests (MANUAL)

**Source**: P2B1-001, P2B1-012 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_custom_field_type_validation.py`
**Lines**: 14, 40, 60, 67, 74, 91, 111, 118, 155, 166, 183, 199, 210, 227, 246, 263, 269, 376, 383, 394, 417, 444, 451, 503, 510, 519
**Severity**: DEFECT (HIGH confidence)
**Priority**: P1

**Flaw**: 26 test functions call `accessor.set(field, value)` with only a `# Should not raise` comment and no subsequent assertion. These tests pass with a no-op `set()` implementation. They provide no coverage of the stored value, the accessor state after the operation, or any observable effect.

**Expected correct behavior**: After `accessor.set(field, value)`:
- `accessor.get(field)` must return `value` (or the coerced equivalent)
- OR `accessor.to_api_dict()` must contain the correct API representation

**Recommended fix approach**:
1. For each test that calls `accessor.set(field, value)`, add a get-back assertion:
   ```python
   accessor.set("Budget", 42)
   assert accessor.get("Budget") == 42
   ```
2. For tests where the stored form differs from the input (e.g., enum by GID, multi-enum lists), assert the stored representation:
   ```python
   accessor.set("Priority", {"gid": "enum_gid_1"})
   assert accessor.get("Priority") == {"gid": "enum_gid_1"}
   ```
3. For None-acceptance tests, assert the stored value is None:
   ```python
   accessor.set("Budget", None)
   assert accessor.get("Budget") is None
   ```
4. For `test_validation_with_missing_field` (line 519): if the test expects no-raise behavior for unknown fields, verify the accessor state is unchanged. If it should raise, convert to `pytest.raises`.

Do NOT add `assert True` or trivial non-vacuous assertions. Each assertion must exercise a real behavioral contract.

**Effort**: medium (a few hours for 26 functions; some require reading `CustomFieldAccessor` source to determine correct stored representation)

---

### RS-002: Implement assert-free traversal test (MANUAL)

**Source**: P2B1-002 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_hydration.py`
**Lines**: 366
**Severity**: DEFECT (HIGH confidence)
**Priority**: P1

**Flaw**: `test_traversal_stops_at_business` configures mocks and mock data but never calls `_traverse_upward_async` and never asserts anything. It is a dead test with zero behavioral coverage.

**Expected correct behavior**: The test should call `_traverse_upward_async(start_gid, ...)` and verify that traversal halts at the business-entity boundary (e.g., that it does not fetch further ancestors beyond the business node, or that it returns the expected partial traversal result).

**Recommended fix approach**:
1. Read `_traverse_upward_async` in `src/autom8_asana/models/business/hydration.py` to understand its signature and stopping conditions.
2. Call the function with the configured mocks.
3. Assert on the returned `HydrationResult` or branch structure to confirm traversal terminated at the business level and did not recurse further.
4. If the function is intentionally not imported by name at test scope, add the import and call it directly.

**Effort**: small (1-2 hours; requires reading hydration source to understand expected traversal stop behavior)

---

### RS-003: Narrow broad except in E2E cleanup (MANUAL)

**Source**: P2B1-003 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_e2e_offer_write_proof.py`
**Lines**: 335
**Severity**: DEFECT (MEDIUM confidence)
**Priority**: P2

**Flaw**: `except Exception as e: print(...)` in the cleanup block of a live-API E2E test swallows all exception types including `TypeError` and `AttributeError` from code bugs. Cleanup failures are only visible in stdout, not as test failures.

**Recommended fix approach**:
1. Narrow to network/API exceptions that are expected during cleanup (e.g., `httpx.HTTPStatusError`, the project's `AsanaError` or equivalent). These are the only exception types legitimately expected when `delete_async` fails after a test.
2. Let unexpected exceptions (TypeError, AttributeError) propagate so they surface as test errors.
3. Example:
   ```python
   except (httpx.HTTPStatusError, AsanaError) as e:
       print(f"\n--- Cleanup warning: {e} ---")
   ```
4. Verify which exception hierarchy `delete_async` raises on API failures by reading `src/autom8_asana/clients/tasks.py`.

**Effort**: small

---

### RS-004: Extract shared fixture/helper from copy-paste E2E setup (MANUAL)

**Source**: P2B1-004 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_entity_resolver_e2e.py`
**Lines**: 156-450
**Severity**: SMELL (HIGH confidence)
**Priority**: P2

**Flaw**: ~90 lines of mock setup code (async `mock_discovery`, 5-way `with patch(...)`, `create_app()`, auth dependency overrides, `try/finally` cleanup) are duplicated verbatim across three test methods.

**Recommended fix approach**:
1. Extract the repeated setup block into a pytest `@pytest.fixture` or an `asynccontextmanager` helper in the test class.
2. Each test method then receives the configured app + client from the fixture and only contains its unique payload and assertions.
3. If the five patch targets vary between tests, pass them as parameters; if they are identical, they belong in the fixture.
4. Example structure:
   ```python
   @pytest_asyncio.fixture
   async def resolver_app(mock_discovery):
       with patch(...), patch(...), ...:
           app = create_app()
           app.dependency_overrides[...] = ...
           try:
               yield AsyncClient(app=app, base_url="http://test")
           finally:
               app.dependency_overrides.clear()
   ```

**Effort**: small

---

### RS-005: Parametrize duplicate scenario tests in cascading field resolution (MANUAL)

**Source**: P2B1-005 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_cascading_field_resolution.py`
**Lines**: 524-656
**Severity**: SMELL (HIGH confidence)
**Priority**: P3

**Flaw**: `test_scenario_chiropractic_unit_with_known_phone` and `test_scenario_second_chiropractic_unit` are structurally identical; only 6 string literals (phone, GID values, business name) differ.

**Recommended fix approach**:
1. Merge into a single parametrized test:
   ```python
   @pytest.mark.parametrize("phone,unit_gid,business_name", [
       ("555-1234", "unit-gid-1", "Business A"),
       ("555-5678", "unit-gid-2", "Business B"),
   ])
   def test_scenario_chiropractic_unit(self, phone, unit_gid, business_name, ...):
       ...
   ```
2. Preserve both scenario names as `pytest.mark.parametrize` IDs for traceability.

**Effort**: small

---

### RS-006: Refactor redundant import and asyncio.run() pattern in GID validation tests (MANUAL)

**Source**: P2B1-006, P2B1-007, P2B1-008, P2B1-010 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_gid_validation_edge_cases.py`
**Lines**: 98-296
**Severity**: SMELL (HIGH confidence)
**Priority**: P2

**Flaw**: `TestClientGIDValidation` contains 7 methods with redundant `import pytest` inside each function body and use of `asyncio.run()` instead of the project-standard `@pytest.mark.asyncio`. `TestSaveSessionGIDValidation` has 7 methods with identical structure varying only by method name. Both classes could be collapsed.

**Recommended fix approach**:
1. Remove all `import pytest` statements inside test function bodies (pytest is already imported at module level).
2. Convert `TestClientGIDValidation` methods from sync + `asyncio.run()` to `async def` + `@pytest.mark.asyncio`, matching the project convention.
3. Parametrize `TestSaveSessionGIDValidation` on `(method_name, invalid_arg)`:
   ```python
   @pytest.mark.parametrize("method_name,invalid_arg", [
       ("get_async", "invalid-gid"),
       ("add_tag_async", "invalid-gid"),
       ...
   ])
   def test_invalid_gid_raises_validation_error(self, method_name, invalid_arg, ...):
       ...
   ```
4. Parametrize `TestClientGIDValidation` similarly.

**Effort**: small

---

### RS-007: Resolve low-confidence duplicate subset assertion (MANUAL)

**Source**: P2B1-009 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_hydration_cache_integration.py`
**Lines**: 104, 296
**Severity**: SMELL (LOW confidence)
**Priority**: P3

**Flaw**: Two test classes each assert that `DETECTION_OPT_FIELDS` is a subset of `STANDARD_TASK_OPT_FIELDS`. Hardcoded counts `== 4` and `== 15` are brittle to field additions.

**Recommended fix approach**:
1. Remove one of the two duplicate subset assertions (keep the one that is more clearly part of its class's declared purpose).
2. For hardcoded counts: decide whether these are intentional contract tests (if so, document that intent with a comment) or brittle assertions (if so, remove the count and keep only the subset relationship). Do not change without confirming the field counts against the source.

**Effort**: trivial

---

### RS-009: Delete permanently skipped dead test for removed adapter (MANUAL)

**Source**: P2B1-013 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_lifecycle_smoke.py`
**Lines**: 1695-1711
**Severity**: SMELL (HIGH confidence)
**Priority**: P2

**Flaw**: `test_completion_adapter_returns_empty` is permanently skipped with the explicit reason that `_CompletionAdapter` was removed. The test body attempts to import and instantiate a class that no longer exists. It provides zero coverage and false assurance.

**Recommended fix approach**:
1. Verify `_CompletionAdapter` does not exist in `src/autom8_asana/lifecycle/engine.py`.
2. If confirmed absent: delete lines 1695-1711 entirely.
3. If `_CompletionAdapter` still exists: remove the skip marker and investigate why it was incorrectly marked as removed.

**Verification step**: `grep -n "_CompletionAdapter" src/autom8_asana/lifecycle/engine.py` -- expect no output.

**Effort**: trivial

---

### RS-011: Evaluate event-loop strategy for lifecycle smoke tests (MANUAL)

**Source**: P2B1-015 (ANALYSIS-REPORT-integ-batch1.md)
**File**: `tests/integration/test_lifecycle_smoke.py`
**Lines**: 25-35
**Severity**: SMELL (LOW confidence)
**Priority**: P3

**Flaw**: `_run_async()` creates a new event loop per call. The docstring provides a rationale ("asyncio.get_event_loop() fails when earlier async tests close the default loop"). This is a deliberate workaround, not an oversight, but it diverges from the project's `@pytest.mark.asyncio` convention used everywhere else.

**Recommended fix approach**:
1. Do not change unless pytest-asyncio issues arise in CI.
2. If migration is desired: convert the 45+ test methods to `async def` with `@pytest.mark.asyncio(scope="class")` and remove `_run_async`. Requires verifying pytest-asyncio version supports class scope.
3. If keeping: add a comment explaining the deliberate deviation from convention at the top of the file to prevent future "cleanup" that reintroduces the problem.

**Effort**: large (if migrating 45+ methods); trivial (if only adding clarifying comment)

---

### RS-012: Implement pass-only stubs in workspace switching tests (MANUAL)

**Source**: P2B2-001, P2B2-002, P2B2-003, P2B2-004 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_workspace_switching.py`
**Lines**: 166, 193, 227, 255
**Severity**: DEFECT (HIGH confidence)
**Priority**: P1

**Flaw**: Four test functions with only `pass` as their body. Pytest collects and passes them unconditionally. No workspace behavior is tested.

**Recommended fix approach**:
1. For each stub, determine the intended behavioral contract from the test name and docstring:
   - `test_recommended_pattern_separate_clients` (line 166): Verify that two separate `AsanaClient` instances for two workspaces do not share state (workspace GID, registry, field cache).
   - `test_anti_pattern_switching_workspace_context` (line 193): Verify that reconfiguring a single client mid-flight produces observable isolation failures or that the pattern is correctly rejected.
   - `test_field_name_resolution_workspace_specific` (line 227): Verify that `FieldResolver` resolves field names against the correct workspace registry.
   - `test_field_resolver_requires_workspace_context` (line 255): Verify that `FieldResolver` raises or returns an error when no workspace context is provided.
2. If the intended behavior cannot be determined, convert to `pytest.mark.skip(reason="not yet implemented: <specific description>")`. A named skip is better than a silent pass.
3. Do not accept `pass` as a permanent state for named test functions.

**Effort**: medium (requires understanding of workspace isolation contract)

---

### RS-013: Replace tautological constructor-GID assertions in workspace tests (MANUAL)

**Source**: P2B2-005, P2B2-006, P2B2-007, P2B2-008 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_workspace_switching.py`
**Lines**: 75, 104, 129, 156-157
**Severity**: DEFECT (HIGH confidence)
**Priority**: P1

**Flaw**: Four tests construct model objects with hardcoded GIDs/attributes and then assert those same values back. `assert task.gid == "3000000001"` after `Task(gid="3000000001")` is always true and tests nothing about workspace behavior.

**Recommended fix approach**:
1. Each test should exercise workspace isolation through the actual system under test, not through direct model construction.
2. Example fix for `test_task_belongs_to_single_workspace`:
   - Create two workspaces and two clients.
   - Fetch or register a task under workspace A's client.
   - Verify the task is not accessible/visible from workspace B's client without explicit cross-workspace access.
3. If actual workspace isolation logic does not exist yet, convert these to documented placeholders (named skip) rather than silently-passing tautologies.
4. Remove the `mock_client = create_mock_client_for_workspace()` lines (see RS-014) since those variables are also unused.

**Effort**: medium

---

### RS-014: Remove unused mock_client assignments in documentation tests (MANUAL)

**Source**: P2B2-009 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_workspace_switching.py`
**Lines**: 64, 87
**Severity**: DEFECT (HIGH confidence)
**Priority**: P2

**Flaw**: `mock_client = create_mock_client_for_workspace()` is called but the variable is never referenced. Dead code inside test functions is a strong signal that the test was not finished.

**Recommended fix approach**:
1. If RS-013 is implemented (replacing the tautological tests with real behavioral tests), `mock_client` will be used in those implementations. Address RS-013 first.
2. If RS-013 is deferred, remove the `mock_client = ...` lines to eliminate dead code. A test that doesn't use a mock client shouldn't construct one.

**Effort**: trivial (if just removing dead lines); addressed as part of RS-013 (if implementing real tests)

---

### RS-015: Implement behavioral assertions in SaveSession edge case tests (MANUAL)

**Source**: P2B2-010, P2B2-011, P2B2-012, P2B2-013, P2B2-014 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_savesession_edge_cases.py`
**Lines**: 78-135 (P2B2-010, P2B2-011), 199-248 (P2B2-012, P2B2-013), 291-313 (P2B2-014)
**Severity**: DEFECT (HIGH confidence)
**Priority**: P1

**Flaw**: Five tests either have no assertions at all or only assert `preview is not None`. The comments within the tests explicitly acknowledge that "actual test would verify the preview output" -- meaning the real assertions were known but never written.

**Expected correct behavior**:
- `test_session_isolation_prevents_cross_contamination` (line 108): Two independent sessions tracking different tasks should each only see their own changes in `session.preview()`. Assert that session1's preview contains task1 only, and session2's preview contains task2 only.
- `test_same_entity_in_different_sessions` (line 78): The preview for session1 should reflect session1's tracked state, independent of session2. Assert specific key presence, not just `is not None`.
- `test_session_transitions_from_empty_to_tracked` (line 199): After tracking a task, `preview()` should return a non-empty result containing that task's GID. Assert `len(preview) > 0` at minimum; assert the specific task GID is present in the preview result.
- `test_session_retracking_same_entity_is_idempotent` (line 225): After triple-tracking the same entity, the session should behave identically to single-tracking. Assert `len(session.preview())` equals 1 entity.
- `test_session_tracks_creates_and_modifications` (line 291): Assert the preview distinguishes between creates and modifications (different `OperationType` values in the result).

**Recommended fix approach**:
1. Read `SaveSession.preview()` in `src/autom8_asana/persistence/session.py` to understand its return type.
2. Implement assertions against the actual return structure, not just `is not None`.
3. If `preview()` does not expose the granularity needed for these assertions, check `SaveSession.get_planned_operations()` or similar.

**Effort**: medium

---

### RS-016: Implement cleanup verification in context manager error test (MANUAL)

**Source**: P2B2-015 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_savesession_edge_cases.py`
**Lines**: 257-281
**Severity**: DEFECT (MEDIUM confidence)
**Priority**: P1

**Flaw**: `test_session_context_manager_cleanup_on_error` raises a `ValueError` inside the context manager and catches it, but never verifies any cleanup occurred. The test name claims to test cleanup-on-error behavior, but the only post-exception assertion is `assert result is not None` on a subsequent session -- not on the first session's cleanup state.

**Expected correct behavior**: After an error exits the context manager, the session should be closed, uncommitted changes should be rolled back (or the session marked as faulted), and a subsequent operation on the same session should raise `SessionClosedError` or equivalent.

**Recommended fix approach**:
1. After the `except ValueError: pass` block, assert on the first session's state:
   ```python
   # Verify session is closed/faulted after error exit
   with pytest.raises(SessionClosedError):
       await session.commit_async()
   ```
   OR verify via a state attribute if one exists:
   ```python
   assert session.is_closed
   ```
2. Read `src/autom8_asana/persistence/session.py` to determine what cleanup guarantee `SaveSession.__aexit__` provides on exception.

**Effort**: small

---

### RS-017: Redirect partial failure tests to exercise production code path (MANUAL)

**Source**: P2B2-016 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_savesession_partial_failures.py`
**Lines**: 50-80, 83-123, 126-156, 207-251
**Severity**: DEFECT (HIGH confidence)
**Priority**: P1

**Flaw**: Four tests construct a `SaveSessionError` and raise it themselves (`raise SaveSessionError(result)`), then inspect the exception they just created. This tests the exception class constructor, not the production code path that raises it. The test names imply that `save_async()` or `commit_async()` is called and fails -- but neither is called.

**Expected correct behavior**: The tests should call `session.commit_async()` (or the equivalent production path) with a mock that returns failure results, and verify that the resulting `SaveSessionError` is raised and contains the correct data.

**Recommended fix approach**:
1. For each of the four tests, replace the manual `raise SaveSessionError(result)` with:
   ```python
   mock_client.tasks.update_async.return_value = ...  # failure response
   async with SaveSession(mock_client) as session:
       session.track(task)
       task.name = "modified"
       with pytest.raises(SaveSessionError) as exc_info:
           await session.commit_async()
   # Now inspect exc_info.value
   ```
2. The `create_mock_client()` helper already exists in this file's test setup -- use it with configured failure return values.
3. Verify the exception's attributes against the mock-configured failure results.

**Effort**: medium (requires understanding how `commit_async` propagates failures into `SaveSessionError`)

---

### RS-018: Resolve MIGRATION_REQUIRED pass-only stubs (MANUAL)

**Source**: P2B2-017 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/test_unified_cache_integration.py`
**Lines**: 191-230
**Severity**: DEFECT (MEDIUM confidence)
**Priority**: P2

**Flaw**: Three `pass`-only stubs inside the `@MIGRATION_REQUIRED`-skipped class `TestProjectDataFrameBuilderUnifiedIntegration`. The migration (to `ProgressiveProjectBuilder`) is complete per the `unified-cache-phase-4-complete` git tag.

**Recommended fix approach**:
1. Since the migration is complete, the `MIGRATION_REQUIRED` skip is stale (addressed in RS-038).
2. Either implement the three stub bodies using `ProgressiveProjectBuilder` constructors (now available), or delete the stubs and the class.
3. Do not un-skip the class while the bodies are `pass` -- that would convert skipped dead tests into silently-passing dead tests.

**Effort**: medium (requires reading `ProgressiveProjectBuilder` constructor signatures and writing meaningful assertions)

---

### RS-020: Promote or delete dead test suite in test_live_api.py (MANUAL)

**Source**: P2B2-019 (ANALYSIS-REPORT-integ-batch2.md)
**File**: `tests/integration/persistence/test_live_api.py`
**Lines**: 42-306
**Severity**: DEFECT (HIGH confidence)
**Priority**: P1

**Flaw**: The entire test suite (`TestLiveAPICreate`, `TestLiveAPIUpdate`, `TestLiveAPIBatch`, `TestLiveAPIDelete`, `TestLiveAPIErrors`, lines 42-306) is stored as a triple-quoted string -- dead Python. The blocking condition stated in the comment (`"Once implemented, uncomment and adapt as needed"`) has been met: `AsanaClient.save_session()` is fully implemented. The file currently provides zero persistence coverage.

**Recommended fix approach** (choose one):

**Option A (promote)**: Extract the string literal into active code. Adapt method signatures, imports, and fixture references to match the current `SaveSession` API. Guard all tests with `@pytest.mark.skipif(not os.getenv("ASANA_ACCESS_TOKEN"), reason="requires live Asana credentials")` so they are skipped in unit/mock CI contexts but executable with credentials.

**Option B (delete)**: If live-API persistence coverage already exists elsewhere (check `tests/integration/persistence/test_action_batch_integration.py`), remove the entire string literal block (lines 42-306) and the stub `TestIntegrationInfrastructure` class. Remove the now-unneeded env-var check fixtures from `conftest.py` (see RS-044).

Verify coverage gap first before deleting. If `test_action_batch_integration.py` provides equivalent create/update/batch/delete/error coverage, Option B is preferred.

**Effort**: medium (promote) or small (delete after coverage verification)

---

### RS-022: Consolidate copy-paste bloat in multiple test files (MANUAL)

**Source**: P2B2-021, P2B2-022, P2B2-026 (ANALYSIS-REPORT-integ-batch2.md)
**Files**:
- `tests/integration/test_savesession_partial_failures.py:49-251` (P2B2-021)
- `tests/integration/test_workspace_switching.py:47-157` (P2B2-022)
- `tests/integration/test_savesession_edge_cases.py:58-300` (P2B2-026)
**Severity**: SMELL
**Priority**: P3

**Flaw**: Three separate instances of structural duplication:
- P2B2-021: Four tests with near-identical raise+inspect pattern (addressed in RS-017; consolidation follows naturally from that fix).
- P2B2-022: Four workspace tests with identical model-construct-then-assert pattern (addressed in RS-013; consolidation follows from that fix).
- P2B2-026: `create_mock_client()` called 12 times across tests; a pytest fixture would eliminate the repetition.

**Recommended fix approach**:
- P2B2-021 and P2B2-022: Address as part of RS-017 and RS-013 respectively. Once the tests are rewritten with real behavior, parametrization will emerge naturally.
- P2B2-026: Add a `@pytest.fixture` for `mock_client` in `test_savesession_edge_cases.py` that calls `create_mock_client()` and yields the result. Replace the 12 inline calls with fixture injection.

**Effort**: trivial to small (P2B2-026 only; P2B2-021 and P2B2-022 are covered by other remedy items)

---

### RS-023: No fix needed -- broad except in fixture teardown (accepted pattern)

**Source**: P2B2-023, P2B2-024, P2B2-025 (ANALYSIS-REPORT-integ-batch2.md)
**Files**: `tests/integration/automation/polling/conftest.py:158,196,227`, `tests/integration/automation/polling/test_end_to_end.py:83,119`, `tests/integration/events/test_sqs_integration.py:74`
**Classification**: No fix needed

**Rationale**: All three findings are `except Exception: pass` in yield-fixture teardown blocks for live-API cleanup (task deletion, queue deletion). The analysis report assigned LOW confidence and explicitly noted "legitimate cleanup pattern for infrastructure teardown." Swallowing exceptions in cleanup teardown is the correct pattern: a cleanup failure must not propagate as a test failure when the test itself passed.

---

### RS-025: Improve thread error messages in concurrency tests (MANUAL)

**Source**: P2-002 (ANALYSIS-REPORT-val-bench.md)
**File**: `tests/validation/persistence/test_concurrency.py`
**Lines**: 147, 176, 200, 230, 255, 428
**Severity**: DEFECT (MEDIUM confidence)
**Priority**: P3

**Flaw**: Six thread workers use `except Exception as e: errors.append(e)`. The broad catch is intentional for thread safety testing (any exception indicates a race condition). However, failures produce unhelpful error messages with no thread identity.

**Recommended fix approach**:
1. Enhance error capture to include thread identity:
   ```python
   except Exception as e:
       import threading
       errors.append(f"Thread {threading.current_thread().name}: {type(e).__name__}: {e}")
   ```
2. This does not change the test logic but dramatically improves failure diagnosis.
3. The analysis report notes this is a codebase-wide convention (30+ sites). If enhanced messages are desired, apply consistently across all thread worker patterns.

**Effort**: small (if applied to all 30+ sites), trivial (if limited to these 6 lines)

---

### RS-026: Remove or-hedge from snapshot isolation assertion (MANUAL)

**Source**: P2-003 (ANALYSIS-REPORT-val-bench.md)
**File**: `tests/validation/persistence/test_concurrency.py`
**Lines**: 479
**Severity**: SMELL (MEDIUM confidence)
**Priority**: P2

**Flaw**: `assert "name" not in snapshot_before or snapshot_before.get("name") == ("Original", "Original")` is an or-hedge. The test comment says "Snapshot before should show no changes" but the assertion also accepts a change where old and new are the same value -- contradictory second condition.

**Recommended fix approach**:
1. Read `ChangeTracker.get_changes()` in `src/autom8_asana/persistence/tracker.py` to determine its exact return value for an unmodified entity.
2. If "no changes" is represented as an empty dict (key absent): assert `"name" not in snapshot_before` only, remove the `or` clause.
3. If "no changes" is represented as same-value tuple: assert `snapshot_before.get("name") == ("Original", "Original")` only, remove the `or` clause.
4. Do not leave both conditions in an `or` -- pick the semantically correct one.

**Effort**: trivial

---

### RS-027: Add modification-count assertion after concurrent tracker test (MANUAL)

**Source**: P2-004 (ANALYSIS-REPORT-val-bench.md)
**File**: `tests/validation/persistence/test_concurrency.py`
**Lines**: 161-186
**Severity**: SMELL (MEDIUM confidence)
**Priority**: P2

**Flaw**: `test_tracker_concurrent_modifications` only asserts `len(errors) == 0` (no crash). It never verifies that all 50 modifications were recorded.

**Recommended fix approach**:
1. After `t.join()` for all threads, assert that the tracker recorded all modifications:
   ```python
   assert len(tracker.get_dirty_entities()) == 50, (
       f"Expected 50 dirty entities after concurrent modifications, got {len(tracker.get_dirty_entities())}"
   )
   ```
2. This verifies correctness of concurrent modification recording, not just absence of exceptions.
3. Verify that `get_dirty_entities()` is the correct public API by reading the tracker source.

**Effort**: trivial

---

### RS-028: Address copy-paste in HTTP status code and async hook tests (MANUAL)

**Source**: P2-005, P2-006 (ANALYSIS-REPORT-val-bench.md)
**Files**:
- `tests/validation/persistence/test_error_handling.py:517-574` (P2-005)
- `tests/validation/persistence/test_functional.py:296-485` (P2-006)
**Severity**: SMELL (LOW confidence)
**Priority**: P3

**Flaw**: Three HTTP status code tests share ~90% identical structure with only status code and message varying. Sync/async hook test pairs are near-identical.

**Recommended fix approach**:
- P2-005: Parametrize on `(status_code, expected_message)`:
  ```python
  @pytest.mark.parametrize("status_code,message", [
      (500, "Internal Server Error"),
      (429, "Rate limited"),
      (401, "Unauthorized"),
  ])
  ```
- P2-006: Assess whether sync and async hook registration use different code paths in production. If they share the same registration mechanism, parametrize on `hook_type`. If they exercise distinct paths, keep separate and document that intent.

**Effort**: small

---

### RS-029: Fix incorrect type annotation in benchmark (MANUAL)

**Source**: P2-007 (ANALYSIS-REPORT-val-bench.md)
**File**: `tests/benchmarks/test_insights_benchmark.py`
**Lines**: 148
**Severity**: SMELL (MEDIUM confidence)
**Priority**: P3

**Flaw**: Return type annotation `-> callable:` uses the builtin function `callable` instead of `Callable` from `typing` or `collections.abc`. Inconsistent with the rest of the codebase.

**Recommended fix approach**:
1. Add `from collections.abc import Callable` to the imports if not already present.
2. Change `-> callable:` to `-> Callable:` at line 148.
3. Or, if the return type is more specific (e.g., `Callable[[str, int], Awaitable[MockResponse]]`), use the full annotation.

**Effort**: trivial

---

### RS-030: No fix needed -- standalone benchmark scripts (advisory only)

**Source**: P2-008 (ANALYSIS-REPORT-val-bench.md)
**Files**: `tests/benchmarks/bench_batch_operations.py`, `tests/benchmarks/bench_cache_operations.py`
**Classification**: No fix needed

**Rationale**: The analysis report notes that benchmark tests are intentionally standalone scripts (per instructions). The `if __name__ == "__main__"` pattern confirms this. If CI gating on these scripts is desired in the future, add `assert` statements to `check_targets()`. No action required now.

---

### RS-031: Rename or rewrite misnamed "concurrent" test that runs sequentially (MANUAL)

**Source**: P2-009 (ANALYSIS-REPORT-val-bench.md)
**File**: `tests/validation/persistence/test_concurrency.py`
**Lines**: 331-356
**Severity**: DEFECT (MEDIUM confidence)
**Priority**: P2

**Flaw**: `test_concurrent_commits_with_shared_entities` uses a `for` loop (sequential) rather than `asyncio.gather` (concurrent), per the inline comment. The name and docstring imply concurrent access but the implementation is sequential.

**Recommended fix approach** (choose one):

**Option A (rename)**: Rename to `test_sequential_sessions_with_shared_entity` and update the docstring to accurately describe sequential independent-session behavior. No logic change needed.

**Option B (implement concurrency)**: Replace the `for` loop with `asyncio.gather` and verify that concurrent `commit_async` calls on independent sessions with a shared task object produce correct and consistent results. More thorough but riskier -- requires understanding SaveSession's thread/async safety guarantees.

Option A is recommended unless concurrent behavior is a known requirement.

**Effort**: trivial (Option A) or medium (Option B)

---

### RS-032: Accept private-attribute access in memory overhead test (MANUAL)

**Source**: P2-010 (ANALYSIS-REPORT-val-bench.md)
**File**: `tests/validation/persistence/test_performance.py`
**Lines**: 319-330
**Severity**: SMELL (LOW confidence)
**Priority**: P3

**Flaw**: `test_memory_overhead_estimation` accesses `tracker._entities`, `tracker._snapshots`, `tracker._states` directly. This is implementation-coupled but common in Python white-box validation tests.

**Recommended fix approach**:
1. This is a deliberate white-box validation test. Accept the private-attribute coupling as-is.
2. Add a comment explaining the coupling:
   ```python
   # White-box validation: verify internal storage structure.
   # If ChangeTracker internal layout changes, update these assertions.
   ```
3. If `tracemalloc`-based measurement is desired in the future, this can be revisited. No action required now.

**Effort**: trivial (comment only)

---

## Section 3: Temporal Debt Cleanup Plans

All Phase 3 findings are SMELL severity. Temporal debt is ALWAYS advisory and never blocking. Items below are pruning plans with explicit verification steps.

---

### RS-033: Remove unused async fixtures stale_task and task_with_due_date (MANUAL, TEMPORAL)

**Source**: P3-001, P3-002 (DECAY-REPORT.md)
**File**: `tests/integration/automation/polling/conftest.py`
**Lines**: 163-228
**Category**: dead-helper
**Priority**: P3

**What to change**: Remove `stale_task` fixture (lines 163-196) and `task_with_due_date` fixture (lines 200-228).

**Verification steps**:
1. `grep -rn "stale_task" tests/` -- confirm zero results (no callers).
2. `grep -rn "task_with_due_date" tests/` -- confirm zero results.
3. Run `pytest tests/integration/automation/polling/ -v` after deletion to confirm no test breakage.

**Effort**: trivial

---

### RS-034: Remove unused helper triad from validation conftest (MANUAL, TEMPORAL)

**Source**: P3-003 (DECAY-REPORT.md)
**File**: `tests/validation/persistence/conftest.py`
**Lines**: 116, 177, 218, 236
**Category**: dead-helper
**Priority**: P3

**What to change**: Remove `create_multi_result()` (line 116), `create_task_hierarchy()` (line 177), `CallTracker` class (line 218), and `call_tracker` fixture (line 236).

**Verification steps**:
1. `grep -rn "create_multi_result\|create_task_hierarchy\|CallTracker\|call_tracker" tests/` -- confirm no uses outside conftest.
2. Run `pytest tests/validation/persistence/ -v` after deletion to confirm no test breakage.

**Effort**: trivial

---

### RS-035: Promote or delete dead test suite in test_live_api.py (MANUAL, TEMPORAL)

**Source**: P3-004 (DECAY-REPORT.md)
**File**: `tests/integration/persistence/test_live_api.py`
**Lines**: 42-306
**Category**: orphaned-infra
**Priority**: P2 (also covered by RS-020)

**Shared with RS-020** (logic-surgeon DEFECT finding). The temporal debt angle: this was a migration stub from 2025-12-22, now 63 days stale, with the blocking condition already met.

**Verification steps**:
1. `grep -n "save_session" src/autom8_asana/client.py` -- confirm implementation exists.
2. Assess coverage in `tests/integration/persistence/test_action_batch_integration.py`.
3. If coverage is sufficient: delete lines 42-306 and the `TestIntegrationInfrastructure` class.
4. Run `pytest tests/integration/persistence/ -v` to confirm no collection errors.

**Effort**: small

---

### RS-036: Remove stale "uncomment when available" scaffold in persistence conftest (MANUAL, TEMPORAL)

**Source**: P3-005 (DECAY-REPORT.md)
**File**: `tests/integration/persistence/conftest.py`
**Lines**: 18, 58-80
**Category**: orphaned-infra
**Priority**: P3

**What to change**: Remove the stale comment at line 18 and the commented-out fixture block (lines 58-80, `live_client` and `cleanup_tasks`).

**Verification steps**:
1. Confirm `AsanaClient` is importable: `grep -n "class AsanaClient" src/autom8_asana/client.py`.
2. Confirm no test file imports `live_client` or `cleanup_tasks` from this conftest: `grep -rn "live_client\|cleanup_tasks" tests/integration/persistence/`.
3. Run `pytest tests/integration/persistence/ -v` after deletion.

**Effort**: trivial

---

### RS-037: Delete or un-skip permanently dead completion adapter test (MANUAL, TEMPORAL)

**Source**: P3-006 (DECAY-REPORT.md)
**File**: `tests/integration/test_lifecycle_smoke.py`
**Lines**: 1695-1711
**Category**: stale-skip
**Priority**: P2 (also covered by RS-009)

**Shared with RS-009**. The temporal decay angle: the skip has been in place since at least 2026-02-18 and the reason is definitively stale.

**Verification steps**:
1. `grep -n "_CompletionAdapter" src/autom8_asana/lifecycle/engine.py` -- if no output, class is gone; delete the test.
2. If class exists, remove the skip marker and run the test to see whether it passes or reveals a genuine defect.

**Effort**: trivial

---

### RS-038: Remove MIGRATION_REQUIRED skip and implement or delete stubs (MANUAL, TEMPORAL)

**Source**: P3-007 (DECAY-REPORT.md)
**File**: `tests/integration/test_unified_cache_integration.py`
**Lines**: 37, 182, 507
**Category**: stale-skip
**Priority**: P2 (also addressed in RS-018)

**What to change**: Remove the `MIGRATION_REQUIRED` sentinel definition (line 37) and its two use-site decorators. For the two skipped classes, either implement the test bodies using `ProgressiveProjectBuilder` or delete the classes.

**Verification steps**:
1. `grep -n "ProgressiveProjectBuilder" src/autom8_asana/cache/dataframe/factory.py` -- confirm constructor is available.
2. After removing the skip decorator, run `pytest tests/integration/test_unified_cache_integration.py::TestProjectDataFrameBuilderUnifiedIntegration -v` -- tests will either pass (if implemented) or fail with `pass` body (if not yet filled in).
3. If tests fail due to `pass` bodies: implement the bodies before removing the skip.
4. Run the full file after cleanup: `pytest tests/integration/test_unified_cache_integration.py -v`.

**Effort**: medium

---

### RS-039: Remove LEGACY_CASCADE_PATH skip from tests that would pass (MANUAL, TEMPORAL)

**Source**: P3-008 (DECAY-REPORT.md)
**File**: `tests/integration/test_unified_cache_integration.py`
**Lines**: 49, 280, 299
**Category**: stale-skip
**Priority**: P2

**What to change**: Remove `LEGACY_CASCADE_PATH` skip markers from `test_resolver_without_plugin_uses_existing_path` (line 280) and `test_both_paths_return_same_value_for_unregistered_field` (line 299). Remove the `LEGACY_CASCADE_PATH` sentinel definition (line 49) if no other use-sites remain.

**Verification steps** (ordered):
1. `grep -n "cascade_plugin" src/autom8_asana/dataframes/resolver/cascading.py` -- confirm `cascade_plugin: CascadeViewPlugin | None = None` (optional parameter).
2. `grep -n "_parent_cache" src/autom8_asana/dataframes/resolver/cascading.py` -- confirm attribute still exists.
3. Remove the `LEGACY_CASCADE_PATH` skip decorators from lines 280 and 299.
4. Run `pytest tests/integration/test_unified_cache_integration.py -k "test_resolver_without_plugin_uses_existing_path or test_both_paths_return_same_value_for_unregistered_field" -v` -- expect PASS.
5. If tests pass, remove the sentinel definition at line 49.
6. Run `pytest tests/integration/test_unified_cache_integration.py -v` for full-file confirmation.

**Effort**: small

---

### RS-040: Delete diagnostic spike script from tests/ (MANUAL, TEMPORAL)

**Source**: P3-009 (DECAY-REPORT.md)
**File**: `tests/integration/spike_write_diagnosis.py`
**Category**: ephemeral-comment (with hardcoded production GID)
**Priority**: P3

**What to change**: Delete `tests/integration/spike_write_diagnosis.py` entirely. The spike is complete (line 222 states "All field types verified by spike_write_diagnosis.py"). The hardcoded `TARGET_GID = "1213235375126350"` is a production task GID with no place in the test suite.

**Verification steps**:
1. Confirm the file is not imported by any other file: `grep -rn "spike_write_diagnosis" tests/`.
2. Confirm it is not referenced in any pytest configuration: `grep -rn "spike_write_diagnosis" pyproject.toml`.
3. Delete the file.
4. Run `pytest tests/integration/ --collect-only 2>&1 | grep -i spike` -- confirm no collection error.

**Effort**: trivial

---

### RS-041: Remove initiative tag from mock_client fixture docstring (MANUAL, TEMPORAL)

**Source**: P3-010 (DECAY-REPORT.md)
**File**: `tests/integration/test_cascading_field_resolution.py`
**Lines**: 108
**Category**: ephemeral-comment
**Priority**: P3

**What to change**: Replace `Per MIGRATION-PLAN-legacy-cache-elimination RF-008: Sets unified_store=None to ensure tests use legacy cascade resolution path (not unified cache).` with `Sets unified_store=None to exercise the legacy cascade resolution path without unified cache.`

**Verification steps**:
1. Confirm the change does not alter test behavior (docstring only).
2. Run `pytest tests/integration/test_cascading_field_resolution.py -v` to confirm no regression.

**Effort**: trivial

---

### RS-042: Remove IMP-23 ticket prefix from test docstring (MANUAL, TEMPORAL)

**Source**: P3-011 (DECAY-REPORT.md)
**File**: `tests/integration/test_hydration_cache_integration.py`
**Lines**: 91
**Category**: ephemeral-comment
**Priority**: P3

**What to change**: Remove `Per IMP-23:` from the docstring prefix at line 91. Preserve the behavioral description that follows it.

**Effort**: trivial

---

### RS-043: Remove Story 3.2 and IMP-20 initiative tags from benchmark module (MANUAL, TEMPORAL)

**Source**: P3-012 (DECAY-REPORT.md)
**File**: `tests/benchmarks/test_insights_benchmark.py`
**Lines**: 4, 151, 423, 484, 546
**Category**: ephemeral-comment
**Priority**: P3

**What to change**:
1. Line 4: Replace `Per Story 3.2:` prefix in module docstring with a plain description of the benchmark's purpose.
2. Lines 151, 423, 484, 546: Remove `Per IMP-20:` prefixes from inline docstrings and comments. Preserve the factual behavioral descriptions that follow each prefix.

**Effort**: trivial

---

### RS-044: Remove dead env-var shim fixtures from persistence conftest (MANUAL, TEMPORAL)

**Source**: P3-013 (DECAY-REPORT.md)
**File**: `tests/integration/persistence/conftest.py`
**Lines**: 40, 47, 53
**Category**: dead-shim
**Priority**: P3

**What to change**: Remove `asana_token` (line 40), `workspace_gid` (line 47), and `project_gid` (line 53) fixtures. These were scaffolded for the live API tests that exist only as a string literal stub.

**Verification steps**:
1. `grep -rn "asana_token\|workspace_gid\|project_gid" tests/integration/persistence/` -- confirm zero usage in test files (only defined in conftest).
2. Remove the three fixtures.
3. Re-introduce if and when RS-035 / RS-020 is resolved by promoting live API tests.
4. Run `pytest tests/integration/persistence/ -v` to confirm no breakage.

**Effort**: trivial

---

### RS-045: Delete double-skipped empty test stub (MANUAL, TEMPORAL)

**Source**: P3-014 (DECAY-REPORT.md)
**File**: `tests/integration/test_unified_cache_integration.py`
**Lines**: 200
**Category**: dead-shim
**Priority**: P2

**What to change**: Delete `test_builder_without_unified_store_uses_existing_path` (approximately lines 200-214). This test is double-skipped (`@MIGRATION_REQUIRED` class + inner `@LEGACY_PATH_REMOVED`) and has a `pass` body. Also remove `LEGACY_PATH_REMOVED` sentinel definition (line 43) after verifying no other use-sites.

**Verification steps**:
1. `grep -n "LEGACY_PATH_REMOVED" tests/integration/test_unified_cache_integration.py` -- identify all use-sites.
2. After RS-039 (removing LEGACY_CASCADE_PATH uses at lines 280 and 299), confirm LEGACY_PATH_REMOVED use-sites are limited to line 200 and the definition at line 43.
3. Delete the test at line 200 and sentinel at line 43.
4. Run `pytest tests/integration/test_unified_cache_integration.py -v` to confirm.

**Note**: Apply RS-039 before RS-045 to avoid confusion between the two sentinel names.

**Effort**: trivial (after RS-039 is applied first)

---

### RS-046: Migrate single-consumer conftest to test file or MockClientBuilder (MANUAL, TEMPORAL)

**Source**: P3-015 (DECAY-REPORT.md)
**File**: `tests/integration/conftest.py`
**Lines**: 15, 45
**Category**: orphaned-infra
**Priority**: P3

**What to change**: Move `client_fixture` and `task_fixture` from `tests/integration/conftest.py` into `tests/integration/test_gid_validation_edge_cases.py` as local fixtures (or migrate to `MockClientBuilder`). Delete `tests/integration/conftest.py` afterward.

**Verification steps**:
1. `grep -rn "client_fixture\|task_fixture" tests/integration/` -- confirm only `test_gid_validation_edge_cases.py` uses these fixtures.
2. Move the fixtures into the test file.
3. Delete `tests/integration/conftest.py`.
4. Run `pytest tests/integration/test_gid_validation_edge_cases.py -v` to confirm fixtures resolve.

**Effort**: small

---

### RS-047: Remove TDD-CONV-AUDIT-001 ticket prefix from inline test docstring (MANUAL, TEMPORAL)

**Source**: P3-016 (DECAY-REPORT.md)
**File**: `tests/integration/automation/polling/test_trigger_evaluator_integration.py`
**Lines**: 467
**Category**: ephemeral-comment
**Priority**: P3

**What to change**: Remove `Per TDD-CONV-AUDIT-001:` from the inline docstring prefix at line 467. Preserve the behavioral description. If linking the TDD is valuable, reference it in the module-level docstring instead.

**Effort**: trivial

---

### RS-048: Remove Phase 3 qualifier from Phase 4+ module docstring (MANUAL, TEMPORAL)

**Source**: P3-017 (DECAY-REPORT.md)
**File**: `tests/integration/test_unified_cache_integration.py`
**Lines**: 1
**Category**: ephemeral-comment
**Priority**: P3

**What to change**: Change `Integration tests for unified cache wiring (Phase 3: TDD-UNIFIED-CACHE-001).` to `Integration tests for unified cache wiring (TDD-UNIFIED-CACHE-001).`

**Note**: This is the lowest-priority item in the plan and is naturally addressed if the larger cleanup in RS-038 and RS-039 proceeds. Handle together with that work.

**Effort**: trivial

---

## Section 4: Remediation Roadmap

Priority-ordered with dependency notes. Gate-keeper uses P1 findings to determine verdict.

### P1 Items (gate-relevant DEFECT, HIGH confidence)

These findings represent test suite integrity failures -- tests that pass unconditionally regardless of production code correctness.

| Remedy | Finding(s) | File(s) | Effort | Depends on |
|---|---|---|---|---|
| RS-001 | P2B1-001, P2B1-012 | test_custom_field_type_validation.py | medium | -- |
| RS-002 | P2B1-002 | test_hydration.py | small | -- |
| RS-012 | P2B2-001 to 004 | test_workspace_switching.py | medium | -- |
| RS-013 | P2B2-005 to 008 | test_workspace_switching.py | medium | RS-012 (implement together) |
| RS-015 | P2B2-010 to 014 | test_savesession_edge_cases.py | medium | -- |
| RS-016 | P2B2-015 | test_savesession_edge_cases.py | small | -- |
| RS-017 | P2B2-016 | test_savesession_partial_failures.py | medium | -- |
| RS-020 | P2B2-019 | test_live_api.py | medium | RS-035, RS-044 inform decision |
| AUTO: RS-008 | P2B1-011 | test_custom_field_type_validation.py | trivial | -- |
| AUTO: RS-010 | P2B1-014 | test_entity_write_smoke.py | trivial | -- |
| AUTO: RS-019 | P2B2-018 | test_unified_cache_integration.py | trivial | -- |
| AUTO: RS-021 | P2B2-020 | test_platform_performance.py | trivial | -- |
| AUTO: RS-024 | P2-001 | test_concurrency.py | trivial | -- |

### P2 Items (significant improvement, MEDIUM confidence DEFECT or HIGH SMELL)

| Remedy | Finding(s) | File(s) | Effort | Notes |
|---|---|---|---|---|
| RS-003 | P2B1-003 | test_e2e_offer_write_proof.py | small | Narrow exception type |
| RS-004 | P2B1-004 | test_entity_resolver_e2e.py | small | Extract shared fixture |
| RS-009 | P2B1-013 | test_lifecycle_smoke.py | trivial | Delete after verification |
| RS-014 | P2B2-009 | test_workspace_switching.py | trivial | After RS-013 |
| RS-018 | P2B2-017 | test_unified_cache_integration.py | medium | After RS-038 |
| RS-026 | P2-003 | test_concurrency.py | trivial | Read tracker source first |
| RS-027 | P2-004 | test_concurrency.py | trivial | -- |
| RS-031 | P2-009 | test_concurrency.py | trivial (rename) | -- |
| RS-037 | P3-006 | test_lifecycle_smoke.py | trivial | Shared with RS-009 |
| RS-038 | P3-007 | test_unified_cache_integration.py | medium | Before RS-045 |
| RS-039 | P3-008 | test_unified_cache_integration.py | small | Before RS-045 |
| RS-045 | P3-014 | test_unified_cache_integration.py | trivial | After RS-039 |

### P3 Items (advisory, SMELL or TEMPORAL)

All Phase 3 findings and low-confidence SMELL findings. Address in background; no gate impact.

| Remedy | Finding(s) | File(s) | Effort |
|---|---|---|---|
| RS-005 | P2B1-005 | test_cascading_field_resolution.py | small |
| RS-006 | P2B1-006 to 010 | test_gid_validation_edge_cases.py | small |
| RS-007 | P2B1-009 | test_hydration_cache_integration.py | trivial |
| RS-011 | P2B1-015 | test_lifecycle_smoke.py | large or trivial |
| RS-022 | P2B2-021, 022, 026 | multiple | trivial to small |
| RS-025 | P2-002 | test_concurrency.py | small |
| RS-028 | P2-005, 006 | test_error_handling.py, test_functional.py | small |
| RS-029 | P2-007 | test_insights_benchmark.py | trivial |
| RS-032 | P2-010 | test_performance.py | trivial |
| RS-033 | P3-001, 002 | polling/conftest.py | trivial |
| RS-034 | P3-003 | validation/conftest.py | trivial |
| RS-035 | P3-004 | test_live_api.py | small |
| RS-036 | P3-005 | persistence/conftest.py | trivial |
| RS-040 | P3-009 | spike_write_diagnosis.py | trivial |
| RS-041 | P3-010 | test_cascading_field_resolution.py | trivial |
| RS-042 | P3-011 | test_hydration_cache_integration.py | trivial |
| RS-043 | P3-012 | test_insights_benchmark.py | trivial |
| RS-044 | P3-013 | persistence/conftest.py | trivial |
| RS-046 | P3-015 | integration/conftest.py | small |
| RS-047 | P3-016 | test_trigger_evaluator_integration.py | trivial |
| RS-048 | P3-017 | test_unified_cache_integration.py | trivial |

---

## Handoff Criteria Verification

- [x] Every finding from all prior reports has a remedy or explicit "no fix needed" with rationale (RS-023 for P2B2-023/024/025; RS-030 for P2-008)
- [x] AUTO patches are syntactically valid and labeled AUTO (RS-008, RS-010, RS-019, RS-021, RS-024)
- [x] MANUAL fixes include rationale and expected correct behavior for each finding
- [x] Temporal debt cleanup plans include explicit verification steps for all MANUAL items (RS-033 through RS-048)
- [x] Effort estimates assigned to all remediation items
- [x] Safe/unsafe classification justified for each fix
- [x] No finding from Phase 1 (0 findings), Phase 2 (51 findings), or Phase 3 (17 findings) is silently absent

**Acid test**: Gate-keeper can issue a verdict knowing that 5 findings have AUTO patches ready to apply, 41 findings have MANUAL instructions with explicit expected behaviors, 2 findings are accepted with no-fix rationale, and all 68 findings are accounted for. Effort ranges from trivial (minutes) to medium (days). P1 items with AUTO patches can be applied immediately; P1 MANUAL items require behavioral judgment and are ordered in the roadmap above.
