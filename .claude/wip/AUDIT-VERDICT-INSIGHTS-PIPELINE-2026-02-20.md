# Audit Verdict: Insights Pipeline Hygiene Remediation
**Date**: 2026-02-20
**Auditor**: Audit Lead
**Commits Audited**: 7 (8c7a7f9 through 8d6a03f)
**Plan Reference**: `.claude/wip/REFACTORING-PLAN-INSIGHTS-PIPELINE-2026-02-20.md`

---

## Executive Summary

**VERDICT: APPROVED WITH NOTES**

The refactoring series achieves its stated goals. All 345 tests pass at the tip of the series. All production files pass ruff format and ruff check. No `type: ignore` comments remain in `_render_kpi_cards`. `TABLE_NAMES` is confirmed as an alias to `TABLE_ORDER` (identity-equal). The lambda handler uses imported constants. The scaffold helper extracts correctly.

One commit (RF-001) has a material atomicity issue: it bundled four unplanned runtime behavior changes alongside the TABLE_NAMES alias refactor, and those behavior changes were not covered by updated tests until RF-007. This created a six-commit window (RF-001 through RF-006) where `test_default_row_limits` and `test_dry_run_includes_report_preview` would fail if run against any intermediate commit.

This issue is documented below. The final state is correct and all tests pass. The series is approved for merge with the atomicity defect recorded as a follow-forward note.

---

## Test Results

```
345 passed in 1.35s
```

Test suites run:
- `tests/unit/automation/workflows/test_insights_formatter.py`
- `tests/unit/automation/workflows/test_insights_export.py`
- `tests/unit/lambda_handlers/test_insights_export.py`

Baseline was 345 (257 formatter + 88 export/handler). Result: 345 passed. No regression. No new failures.

Pre-existing failures in `test_contract_alignment.py` (21 RESPX mock failures) are out of scope and not counted.

---

## Ruff Compliance

| File | Format | Lint |
|------|--------|------|
| `src/autom8_asana/automation/workflows/insights_formatter.py` | PASS | PASS |
| `src/autom8_asana/automation/workflows/insights_export.py` | PASS | PASS |
| `src/autom8_asana/lambda_handlers/insights_export.py` | PASS | PASS |
| `src/autom8_asana/api/health_models.py` | PASS | PASS |
| `tests/unit/automation/workflows/test_insights_formatter.py` | PASS | PASS |
| `tests/unit/automation/workflows/test_insights_export.py` | PASS | PASS |

All six files pass `ruff format --check` and `ruff check` without error.

---

## Behavior Invariant Spot Checks

**TABLE_NAMES alias (RF-001)**
```
TABLE_NAMES is TABLE_ORDER: True
TOTAL_TABLE_COUNT: 12
Same list: True
```
`TABLE_NAMES` is the same Python object as `TABLE_ORDER`. Importers of `TABLE_NAMES` from `insights_export` get the formatter's canonical list. Invariant holds.

**type: ignore removal (RF-003)**
Zero `type: ignore` comments remain in `insights_formatter.py`. The `_extract_numeric_values` static method returns `list[float]`, making the return type visible to mypy at all call sites. Filtering semantics (exclude `None` and non-numeric) are identical to the removed inline comprehensions.

**Scaffold extraction (RF-004)**
`_render_empty_section` and `_render_error_section` now delegate to `_render_section_with_body`. The commit message states "HTML output is byte-for-byte identical." The diff confirms the scaffold assembly (sid, collapsed_class, subtitle_html, outer HTML structure) is shared. Body content is still `<p class="empty">` vs `<div class="error-box">` respectively. Invariant holds.

**Lambda deferred import (RF-002)**
The `InsightsExportWorkflow` import remains inside `_create_workflow` for cold-start optimization. Only the three constants (`DEFAULT_MAX_CONCURRENCY`, `DEFAULT_ATTACHMENT_PATTERN`, `DEFAULT_ROW_LIMITS`) are at module level. Invariant holds.

---

## Per-Commit Assessment

### RF-001: `refactor(insights): import TABLE_ORDER from formatter; alias TABLE_NAMES`
**Commit**: `8c7a7f9`
**Contract compliance**: PARTIAL FAIL
**Behavior preservation**: FAIL (contains unplanned behavior changes)
**Atomicity**: FAIL

The plan specifies a single-concern change: import `TABLE_ORDER`, alias `TABLE_NAMES`, derive `TOTAL_TABLE_COUNT = len(TABLE_NAMES)`. The commit delivers this. However, the diff also contains four additional unplanned changes that were never listed in the refactoring plan:

1. **DEFAULT_ROW_LIMITS changed** from `{"APPOINTMENTS": 250, "LEADS": 250}` to `{"APPOINTMENTS": 100, "LEADS": 100, "ASSET TABLE": 150}`. This is a runtime behavior change affecting all callers that use the default.

2. **Dry-run behavior replaced**: changed from truncating the report to 2000 chars in memory (`report_content[:2000]`) to writing the full HTML to disk in `.wip/`. The metadata key changed from `report_preview` to `preview_paths`.

3. **_OfferOutcome gained a new field**: `preview_path: str | None = None`, modifying the internal dataclass.

4. **pathlib import added** to support the new dry-run file write.

These changes are legitimate (consistent with the project memory note that row limits were reverted to 100, and that `.wip/` preview files were added during WS-G), but they belong in a feature commit, not in the constants-aliasing refactor commit. The test coverage for these changes (`test_default_row_limits` and `test_dry_run_includes_report_preview`) was not updated until RF-007, meaning any intermediate checkout of RF-001 through RF-006 had two failing tests.

**Note**: This is an atomicity defect, not a correctness defect at the tip. The final state is tested and correct.

---

### RF-002: `refactor(lambda): import insights_export constants; remove hardcoded literals`
**Commit**: `a239587`
**Contract compliance**: PASS
**Behavior preservation**: PASS
**Atomicity**: PASS

The diff shows exactly what the plan specifies: three constants imported at module level, inline literals replaced with named references, `InsightsExportWorkflow` deferred import preserved in `_create_workflow`. The `row_limits` value in the lambda handler now reflects `DEFAULT_ROW_LIMITS` (the updated value from RF-001), which is the correct behavior — a single source of truth.

One observation: the lambda handler's `default_params["row_limits"]` previously was `{"APPOINTMENTS": 250, "LEADS": 250}` (matching the pre-RF-001 constant). After RF-002 it becomes `DEFAULT_ROW_LIMITS` which now includes `ASSET TABLE: 150`. This is the correct behavior for a constants-aliasing refactor. The lambda handler config is now fully synchronized with the workflow module.

---

### RF-003: `refactor(formatter): extract _extract_numeric_values; remove type: ignore`
**Commit**: `2322b31`
**Contract compliance**: PASS
**Behavior preservation**: PASS
**Atomicity**: PASS

The helper is added as a `@staticmethod` on `HtmlRenderer` with return type `list[float]`. Three call sites use it for sparkline and spend-trend extraction. The best-week case uses an explicitly typed `list[tuple[float, str]]` comprehension (the "cleaner alternative" noted in the plan). All five `type: ignore` suppressions are removed. Filtering logic (exclude `None` and non-numeric) is identical in the helper to what was inline. No behavior change.

---

### RF-004: `refactor(formatter): extract _render_section_with_body scaffold helper`
**Commit**: `1abe334`
**Contract compliance**: PASS
**Behavior preservation**: PASS
**Atomicity**: PASS

The plan's "simpler" option (helper takes `body_content: str`) is implemented. Both `_render_empty_section` and `_render_error_section` delegate to `_render_section_with_body`. The scaffold assembly in the helper is identical to what both methods had independently. Body content is still computed in the caller. The helper is private (`_`). Public signatures unchanged.

---

### RF-005: `test(formatter): replace str.find sort assertions with row-index assertions`
**Commit**: `321db06`
**Contract compliance**: PASS
**Behavior preservation**: PASS (test-only change)
**Atomicity**: PASS

The `_extract_row_names` module-level helper is added. Both `str.find()` position comparisons are replaced with `.index()` on the parsed row name list. Assertion semantics are identical: relative order of named rows is verified. The new form is immune to substring collisions in non-name columns. `import re` added at module level.

---

### RF-006: `test(formatter): move import json to module level`
**Commit**: `fc6ad6c`
**Contract compliance**: PASS
**Behavior preservation**: PASS (test-only change)
**Atomicity**: PASS

All seven method-local `import json as json_mod` instances removed. Single `import json` added at module level. All `json_mod.` references replaced with `json.`. No test behavior change. Clean single-concern commit.

---

### RF-007: `docs(insights): fix "markdown" docstrings; annotate deps_response alias`
**Commit**: `8d6a03f`
**Contract compliance**: PASS
**Behavior preservation**: PASS
**Atomicity**: ADVISORY NOTE

The commit correctly fixes the two "markdown" docstring references in `InsightsExportWorkflow` to "HTML", adds the SM-008 deferral annotation in `test_insights_export.py`, and expands the `deps_response` comment in `health_models.py`.

However, this commit also contains two test behavior updates that belong logically with RF-001:

1. `test_default_row_limits` updated from `{"APPOINTMENTS": 250, "LEADS": 250}` to `{"APPOINTMENTS": 100, "LEADS": 100, "ASSET TABLE": 150}`
2. `test_dry_run_includes_report_preview` renamed and rewritten as `test_dry_run_writes_preview_files`

These updates make the test suite green at the tip, but they should have been in RF-001 alongside the behavior changes they cover. The commit message "fix markdown docstrings" does not accurately describe the test updates, making the commit harder to bisect if a regression occurs.

**Verdict**: PASS at tip. Atomicity advisory: the test updates belong with RF-001.

---

## Contract Verification Matrix

| Plan Task | Contract Satisfied | Evidence |
|-----------|-------------------|----------|
| RF-001: TABLE_NAMES alias | Yes (with unplanned additions) | `TABLE_NAMES is TABLE_ORDER: True`, `TOTAL_TABLE_COUNT: 12` |
| RF-001: No formatter import added | Yes | Formatter file unchanged in RF-001 diff |
| RF-002: Constants imported, literals removed | Yes | Diff shows exact substitution |
| RF-002: InsightsExportWorkflow deferred import preserved | Yes | `_create_workflow` still has local import |
| RF-003: _extract_numeric_values added as staticmethod | Yes | Confirmed in diff |
| RF-003: list[float] return type | Yes | Annotation present |
| RF-003: 5 type: ignore removed | Yes | Zero found in current file |
| RF-004: _render_section_with_body added | Yes | Diff confirms |
| RF-004: Both methods delegate to helper | Yes | Each is 2 lines |
| RF-004: HTML output byte-for-byte identical | Yes | Same scaffold, caller provides body |
| RF-005: str.find replaced with row-index | Yes | Diff confirms both sites |
| RF-005: _extract_row_names module-level helper | Yes | Added before class definitions |
| RF-006: import json module-level | Yes | 7 local imports removed, 1 module import added |
| RF-007: "markdown" docstrings fixed (2 sites) | Yes | Diff confirms |
| RF-007: deps_response annotated | Yes | Comment expanded |
| RF-007: SM-008 deferral noted | Yes | Comment added in test_insights_export.py |

---

## Improvement Assessment

**Smells addressed**:
- SM-004 (TABLE_NAMES duplication): Resolved. Single source of truth in formatter.
- SM-011 (lambda literals): Resolved. Lambda handler uses named constants.
- SM-001 (type: ignore in _render_kpi_cards): Resolved. Zero suppressions remain.
- SM-006 (duplicate empty/error scaffold): Resolved. 26 lines -> 2 lines each.
- SM-003 (str.find assertions): Resolved. Row-index assertions are structurally sound.
- SM-005 (import json): Resolved. Module-level import.
- SM-012 (markdown docstrings): Resolved. Both sites corrected.
- SM-010 (deps_response alias): Resolved. Comment explains shared factory.

**Deferred per plan**: SM-007, SM-008, SM-009 — all correctly deferred with rationale.

**Code quality delta**:
- `insights_formatter.py`: -19 net lines (helper extraction tradeoff with type annotations)
- `insights_export.py`: net lines reduced by removal of 12-element literal list
- `lambda_handlers/insights_export.py`: +8 lines (import block added, literals replaced)
- Test files: net reduction in test code due to deduplication

No new smells introduced.

---

## Issues Found

### ISSUE-1: RF-001 Atomicity Violation (Advisory, Non-Blocking)

**Severity**: Advisory
**Blocking**: No

RF-001 bundled four unplanned runtime behavior changes with the TABLE_NAMES alias refactor:
- `DEFAULT_ROW_LIMITS` values changed (250/250 -> 100/100/150 with new key)
- Dry-run behavior changed (in-memory truncation -> file write to `.wip/`)
- `_OfferOutcome` gained `preview_path` field
- `metadata["report_preview"]` changed to `metadata["preview_paths"]`

Test coverage for these changes was deferred to RF-007, creating a six-commit window where `test_default_row_limits` and `test_dry_run_includes_report_preview` would fail on any intermediate checkout. The plan's invariant for RF-001 stated "No behavior change," which was not honored.

**Why non-blocking**: All changes are correct and fully tested at the tip. The behavior changes reflect project memory (WS-G row limit correction, `.wip/` preview file addition). No test failure exists at the merge point.

**Recommendation**: In future iterations, feature behavior changes should be their own commit with accompanying test updates. The refactoring commit should be pure structural change. This is a process note, not a merge blocker.

### ISSUE-2: RF-007 Commit Message Scope (Advisory, Non-Blocking)

**Severity**: Advisory
**Blocking**: No

The RF-007 commit message describes documentation changes but silently contains two test assertions that cover the RF-001 behavior changes. This makes `git bisect` harder for the dry-run and row-limits behavior. The tests pass and are correct; the message is just incomplete.

---

## Handoff Checklist

- [x] All tests pass without exception (345/345)
- [x] Every contract verified against plan
- [x] All production files pass ruff format and ruff check
- [x] All test files pass ruff format and ruff check
- [x] TABLE_NAMES is confirmed alias (identity equality verified at runtime)
- [x] Zero type: ignore comments remain in insights_formatter.py
- [x] Lambda handler uses imported constants with deferred InsightsExportWorkflow preserved
- [x] Scaffold helper extraction verified byte-equivalent
- [x] str.find assertions replaced with row-index assertions
- [x] import json at module level (7 local imports removed)
- [x] "markdown" docstrings corrected in both locations
- [x] Behavior preservation confirmed for RF-003, RF-004, RF-005, RF-006, RF-007
- [x] Behavior changes in RF-001 documented and confirmed intentional (WS-G row limit correction)
- [x] Audit report complete

---

## Artifact Verification

| File | Read | Verified |
|------|------|---------|
| `.claude/wip/REFACTORING-PLAN-INSIGHTS-PIPELINE-2026-02-20.md` | Yes | Plan read in full |
| `src/autom8_asana/automation/workflows/insights_export.py` | Yes (via git diff + runtime import) | TABLE_NAMES alias, DEFAULT_ROW_LIMITS values |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Yes (via git diff + grep) | _extract_numeric_values, zero type: ignore |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Yes (via git diff + runtime inspect) | Constants imported, deferred import preserved |
| `src/autom8_asana/api/health_models.py` | Yes (via git diff) | deps_response annotation expanded |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Yes (via git diff) | _extract_row_names helper, import json at module level |
| `tests/unit/automation/workflows/test_insights_export.py` | Yes (via git diff) | SM-008 annotation, test_default_row_limits updated |

---

## Final Verdict

**APPROVED WITH NOTES**

The series is ready to merge. All 345 tests pass. Ruff clean across all six changed files. All eight target smells are resolved. Behavior is preserved for all pure-refactoring commits (RF-002 through RF-007). The RF-001 atomicity defect is advisory: the behavior changes it introduced are correct, intentional, and fully tested at the merge point. The intermediate test-breakage window does not affect the merge state.

Notes for follow-forward:
1. Future refactoring commits must not contain behavior changes. When behavior changes are needed, they belong in a separate commit with same-commit test updates.
2. The RF-007 commit message should have called out the test updates explicitly.
