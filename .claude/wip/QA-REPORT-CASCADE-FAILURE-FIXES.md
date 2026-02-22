# QA Report: Cascade Resolution Failure Fixes

```yaml
report_id: QA-CASCADE-FAILURE-FIXES-001
date: 2026-02-20
status: CONDITIONAL GO
spike: SPIKE-unit-resolution-cascade-failure
tdd: TDD-CASCADE-FAILURE-FIXES-001
fixes_tested: [Fix 1, Fix 2, Fix 3]
tests_run: 334 (30 new + 304 module-level regression)
tests_passed: 334
tests_failed: 0
defects_found: 1
coverage_gaps: 3
```

---

## 1. Release Recommendation

**CONDITIONAL GO** -- Ship Fix 1 + Fix 2 + Fix 3 after addressing the one MEDIUM-severity defect and acknowledging the test coverage gaps below. The defect is a missing try/except that could cause a build failure if the validation pass encounters unexpected data. The coverage gaps are missing tests specified in the TDD but not implemented.

---

## 2. Test Execution Summary

| Suite | Tests | Pass | Fail | Skip |
|-------|-------|------|------|------|
| Fix 1: test_cache_invalidate.py (new) | 10 | 10 | 0 | 0 |
| Fix 2: test_unified_parent_chain.py (new) | 6 | 6 | 0 | 0 |
| Fix 2: test_dataframe_view_grandparent_fallback.py (new) | 5 | 5 | 0 | 0 |
| Fix 3: test_cascade_validator.py (new) | 9 | 9 | 0 | 0 |
| Regression: tests/unit/cache/providers/ | all | all | 0 | 0 |
| Regression: tests/unit/dataframes/views/ | all | all | 0 | 0 |
| Regression: tests/unit/dataframes/builders/ | all | all | 0 | 0 |
| Regression: tests/unit/lambda_handlers/ | all | all | 0 | 0 |
| **Total module-level regression** | **304** | **304** | **0** | **0** |

---

## 3. Defects

### DEF-001: Missing try/except around cascade validation in progressive builder [MEDIUM]

**Severity:** MEDIUM
**Component:** `src/autom8_asana/dataframes/builders/progressive.py` lines 502-509

**Description:** The `validate_cascade_fields_async` call in Step 5.5 of `build_progressive_async` is not wrapped in a try/except. If the validation pass raises an exception (corrupted hierarchy index, unexpected polars column dtype, network error during `get_parent_chain_async`), the exception propagates up and kills the entire build. The already-merged DataFrame from Step 5 is lost, and the final artifact write in Step 6 never happens.

**Expected behavior:** Fix 3 is documented as additive validation that "should not break the build pipeline" (TDD section 5.3.4). The feature flag provides an escape hatch for anticipated issues, but a runtime exception would fail AFTER the flag check passes.

**Actual behavior:** An uncaught exception from `validate_cascade_fields_async` would propagate through `build_progressive_async` and produce a `BuildStatus.FAILURE` result, losing the merged data.

**Reproduction:**
1. Build a project where the hierarchy index contains a GID that maps to a non-string value in the DataFrame `gid` column
2. `str(gid)` could raise or produce unexpected results
3. `hierarchy.get_ancestor_chain(str(gid), max_depth=5)` could fail
4. The entire build is lost

**Recommended fix:** Wrap the validation call in a try/except that logs a warning and continues with the uncorrected `merged_df`:

```python
if cascade_plugin is not None:
    try:
        merged_df, _cascade_result = await validate_cascade_fields_async(...)
        total_rows = len(merged_df)
    except Exception:
        logger.warning(
            "cascade_validation_failed",
            extra={"project_gid": self._project_gid, ...},
        )
```

**Impact:** If the validation function throws, the build loses all data including data that was correct. This defeats the purpose of defense-in-depth.

**Blocking?:** Not blocking for release. The probability is low because the validation only processes null rows and the code paths it exercises (cache reads) are mature. However, this should be fixed before the next production build cycle.

---

## 4. Test Coverage Gaps

### GAP-001: Missing test for cascade_view gap-skipping [LOW]

**TDD spec:** Section 7.2 specifies `test_cascade_view_skips_gap_in_completeness_chain` in `tests/unit/dataframes/views/test_cascade_view_gaps.py`.

**Actual:** File does not exist. The gap-skipping behavior in `CascadeViewPlugin._get_parent_chain_with_completeness_async` (cascade_view.py lines 356-365) has no dedicated test.

**Risk:** The secondary fix point (cascade_view.py) is untested in isolation. It IS exercised indirectly through the cascade resolution path tests, but there is no test that specifically verifies the `continue` behavior when `get_with_upgrade_async` returns None for a middle ancestor.

### GAP-002: Missing feature flag disable test [LOW]

**TDD spec:** Section 7.3 specifies `test_validation_disabled_by_feature_flag` that sets `section_cascade_validation=0` and asserts the validation function is not called.

**Actual:** No test exercises the feature flag disable path. The feature flag IS tested in production code (progressive.py line 491: `if get_settings().runtime.section_cascade_validation != "0":`), but there is no test that verifies this guard works.

**Risk:** If the feature flag comparison is changed or broken in a refactor, there is no regression test to catch it. The flag is the primary escape hatch for Fix 3.

### GAP-003: Missing integration test [LOW]

**TDD spec:** Section 7.3 specifies `tests/integration/test_cascade_validation_progressive.py` with an end-to-end test `test_progressive_build_with_hierarchy_gap_corrected`.

**Actual:** File does not exist. There is no integration test verifying the full pipeline: hierarchy warming gap -> section build -> merge -> validation correction.

**Risk:** The individual unit tests verify each component in isolation. The interaction between Fix 2 (gap-tolerant chain) and Fix 3 (post-build validation) is not tested end-to-end.

---

## 5. Code Review Findings

### Fix 1: Targeted Project Invalidation

**File:** `src/autom8_asana/lambda_handlers/cache_invalidate.py`

| Aspect | Assessment |
|--------|-----------|
| Spec conformance | PASS. Implements TDD section 3.3 exactly. |
| Input validation | ACCEPTABLE. No sanitization on `invalidate_project` string, but S3 keys are opaque strings (no path traversal risk). Lambda is internal-only. |
| Error handling | PASS. Top-level try/except in `_invalidate_cache_async` catches and returns error response. |
| Idempotency | PASS. `delete_manifest_async` and `delete_section_files_async` succeed silently if already deleted. |
| Logging | PASS. Structured logs with project_gid and invocation_id. No sensitive data leaked. |
| Metrics | PASS. CloudWatch metric `ProjectManifestInvalidated` emitted with project_gid dimension. |
| Partial failure | ACCEPTABLE. Return value of `delete_section_files_async` is ignored. Orphaned section files are harmless; manifest deletion ensures full rebuild. |

### Fix 2: Gap-Tolerant Parent Chain

**File:** `src/autom8_asana/cache/providers/unified.py` (lines 741-770)

| Aspect | Assessment |
|--------|-----------|
| Spec conformance | PASS. Changes `break` to `continue` as specified in TDD section 4.3. |
| Ordering safety | PASS. TDD section 4.2 analysis of `allow_override` risk is correct. All `allow_override=True` fields cascade within a single parent-child level. |
| Stats tracking | PASS. `parent_chain_gaps` counter via `setdefault` is safe for concurrent access (single-threaded async). |
| Log level | PASS. Gaps logged at INFO level, appropriate for operational visibility. |
| Performance | PASS. No additional API calls introduced; same cache batch read. |

**File:** `src/autom8_asana/dataframes/views/cascade_view.py` (lines 356-365)

| Aspect | Assessment |
|--------|-----------|
| Spec conformance | PASS. `continue` instead of `break` as specified. |
| Test coverage | WEAK. No dedicated test (see GAP-001). |

**File:** `src/autom8_asana/dataframes/views/dataframe_view.py` (lines 470-508)

| Aspect | Assessment |
|--------|-----------|
| Spec conformance | PASS. Grandparent fallback exactly matches TDD section 4.3 "Tertiary improvement". |
| Infinite loop protection | PASS. Single-shot fetch with `chain_gids` dedup check. Cannot recurse. |
| Cache deduplication | PASS. `if grandparent_gid not in chain_gids` prevents redundant fetch. |
| Test coverage | GOOD. 5 tests cover happy path, already-in-chain, no-parent, empty-chain, and fetch-returns-none. |

### Fix 3: Post-Build Cascade Validation

**File:** `src/autom8_asana/dataframes/builders/cascade_validator.py`

| Aspect | Assessment |
|--------|-----------|
| Spec conformance | PASS. Implements TDD section 5.3.1 faithfully. |
| Performance | PASS. Only iterates null rows. Polars `is_null().arg_true()` is O(n) on column, negligible. |
| Column correction | PASS. Uses `to_list()` + index assignment + `with_columns()`. Immutable Polars pattern. |
| Type safety | PASS. `.cast(merged_df[col_name].dtype)` preserves original column dtype after replacement. |
| Private API usage | ACCEPTABLE. Calls `cascade_plugin._get_custom_field_value_from_dict()` (private method). Stable and used by other callers. |

**File:** `src/autom8_asana/dataframes/builders/progressive.py` (lines 485-509)

| Aspect | Assessment |
|--------|-----------|
| Feature flag | PASS. `section_cascade_validation != "0"` correctly enables by default. |
| Missing error handling | **DEFECT** (DEF-001). See section 3. |
| Import safety | PASS. Deferred import prevents circular dependency. |

**File:** `src/autom8_asana/settings.py`

| Aspect | Assessment |
|--------|-----------|
| New field | PASS. `section_cascade_validation: str = Field(default="1", ...)` in RuntimeSettings. |
| Naming consistency | PASS. Follows same pattern as `section_freshness_probe`. |
| Documentation | PASS. Env var `SECTION_CASCADE_VALIDATION` documented in docstring. |

---

## 6. Adversarial Analysis

### 6.1 What if `hierarchy.get_ancestor_chain` returns a GID never registered?

**Finding:** Safe. `cache.get_batch()` returns an empty dict for unknown GIDs. The gap-skipping logic adds the GID to `gaps` list and continues. No exception.

### 6.2 What if the grandparent fallback creates an infinite loop?

**Finding:** Impossible. The fallback fetches exactly one additional entity and checks `grandparent_gid not in chain_gids` before fetching. It does not recurse. The underlying `get_ancestor_chain` is bounded by `max_depth=5`.

### 6.3 What if `validate_cascade_fields_async` throws during correction?

**Finding:** **Defect DEF-001.** The build fails without writing the merged DataFrame. The uncorrected data is lost.

### 6.4 What if the merged DataFrame has millions of null rows?

**Finding:** The validation iterates all null rows synchronously with `await store.get_parent_chain_async()` per row. For millions of nulls, this would be:
- O(millions) cache reads (in-memory, ~1ms each = ~1000 seconds)
- The feature flag provides an escape hatch (`section_cascade_validation=0`)
- In practice, cascade-critical field nulls are rare (0-10 per project in normal operation)
- The 5-second performance budget from the TDD is realistic for typical workloads but would be violated at extreme scale

**Risk:** LOW. If this becomes a problem, the feature flag disables it.

### 6.5 What if `delete_manifest_async` fails partway through?

**Finding:** `delete_section_files_async` iterates all sections regardless of individual failures and returns False. `delete_manifest_async` is called after section file deletion. If manifest deletion fails, the handler's top-level try/except catches the error and returns `success=False` with the error message. On the next warm-up, the existing manifest would cause a resume (not a fresh rebuild), which is acceptable.

### 6.6 What happens when Fix 2 already resolves the gap before Fix 3 runs?

**Finding:** Correct interaction. If Fix 2's gap-tolerant chain successfully returns the Business ancestor, cascade resolution at build time populates `office_phone` correctly. Fix 3 then finds zero null rows and produces `rows_checked=0`. This is the expected "no-op when not needed" behavior. The fixes compose correctly.

---

## 7. Existing Test Impact

### Modified behavior in `test_parent_chain_stops_at_missing`

**File:** `tests/unit/cache/test_unified.py` line 505

The existing test `test_parent_chain_stops_at_missing` asserts `len(chain) == 1` with the comment "Should stop at parent since grandparent is missing." This test PASSES with the new code, but for a different reason:
- **Old behavior:** Chain broke at the gap (grandparent missing), returning `[parent]`
- **New behavior:** Chain skips the gap, but grandparent is the last ancestor, so result is still `[parent]`

The test assertion is accidentally correct. The comment is now misleading. This is a documentation issue, not a functional defect.

**No other existing tests were broken by the behavior change.** 304 module-level tests pass.

---

## 8. Risk Areas for Production Monitoring

| What to Monitor | Why | How |
|----------------|-----|-----|
| `parent_chain_gaps_skipped` log events | Fix 2 is working -- gaps are being skipped | Structured log search for event name |
| `parent_chain_gaps` stat in UnifiedTaskStore | Frequency of gaps indicates hierarchy warming reliability | Store stats at warm-up end |
| `cascade_validation_complete` log events | Fix 3 is running -- check `rows_stale` and `rows_corrected` | Structured log search |
| `cascade_grandparent_fallback_resolved` log events | Fix 2 grandparent fallback is firing | Structured log search, should be rare |
| `ProjectManifestInvalidated` CloudWatch metric | Fix 1 invocations are tracked | CloudWatch dashboard |
| Build duration increase | Fix 3 adds post-merge validation time | Compare build times before/after deployment |
| `cascade_validation_failed` (after DEF-001 fix) | Validation pass is failing gracefully | Should appear at WARNING level |

---

## 9. Conditions for GO

1. **DEF-001 must be fixed** before production deployment. Add try/except around the `validate_cascade_fields_async` call in progressive.py. This is a 3-line change.

2. **GAP-002 is recommended** before deployment. The feature flag test is the safety net for Fix 3 and should be verified.

3. **GAP-001 and GAP-003 can be deferred** to a follow-up. The cascade_view gap behavior is covered transitively, and the integration test adds confidence but is not blocking.

---

## 10. Documentation Impact

No user-facing documentation changes required. The fixes are internal cache and build pipeline changes. The `SECTION_CASCADE_VALIDATION` environment variable should be documented in operational runbooks for the Lambda deployment.
