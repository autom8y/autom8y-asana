# PRD: Sprint D -- Insights Export Backlog (Final)

## Overview

Resolve the three remaining P3 findings from the insights export pipeline review. F-11 caches
a per-column alignment computation that is currently recomputed per-cell. F-12 extracts 333
lines of inline CSS/JS string literals to external `.css`/`.js` files for editor support and
maintainability. F-17 is closed as no-action after confirming HtmlRenderer is stateless.

## Impact Assessment

impact: low
impact_categories: []

Rationale: All changes are internal to `insights_formatter.py`. No API contract, schema,
security, or cross-service changes. F-11 is a mechanical performance fix. F-12 moves string
constants to files without changing generated output. F-17 requires no code change.

## Background

An architectural review of the insights export pipeline produced 17 findings. Sprints A-C
addressed 14 of them across commits `5092d2d` (10 findings) and `eb85f3a`..`e721bbf` (3
structural findings). Three P3 findings remain. This sprint closes the backlog.

Sprint C shipped significant structural changes to `insights_formatter.py` (TableSpec
extraction, spec-driven compose_report, shared ResolutionContext fixture), which shifted line
numbers. All references below are verified against the current source.

### Prior Work

| Sprint | Findings | Commits |
|--------|----------|---------|
| A+B | 10 findings (F-01, F-02, F-05, F-06, F-08, F-09, F-10, F-13, F-14, F-15) | `5092d2d` |
| C | 3 structural findings (F-03, F-04, F-07) | `eb85f3a`..`e721bbf` |
| D (this) | 3 P3 findings (F-11, F-12, F-17) | -- |

### Source References

- Full review: `.claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md`
- Sprint C PRD: `.claude/wip/SPIKE-INSIGHTS-CONSUMER/PRD-SPRINT-C.md`
- Sprint C TDD: `.claude/wip/SPIKE-INSIGHTS-CONSUMER/TDD-SPRINT-C.md`
- Framing document: `.claude/wip/frames/sprint-d-export-backlog.md`

## Findings Table

| Finding | Title | Priority | Disposition | Effort |
|---------|-------|----------|-------------|--------|
| F-11 | `_column_align_class` called per-cell, scans all rows | P3 PERFORMANCE | **Implement** | ~30 min |
| F-12 | Inline CSS+JS is 333 lines of unmaintainable string literals | P3 MAINTAINABILITY | **Implement** | ~2 hours |
| F-17 | Module-level `_renderer` singleton | P3 MAINTAINABILITY | **Close (no-action)** | 0 |

## Stakeholder Interview Record

Interview conducted 2026-03-01, 1 round (Round 2 waived -- all decisions unambiguous).

### F-12 Design Decisions

| Decision | Options Considered | Selected | Rationale |
|----------|--------------------|----------|-----------|
| Loading mechanism | (A) `pathlib.Path(__file__).parent / "static/"` vs (B) `importlib.resources` | **A: pathlib** | Simpler, matches current project style (zero importlib.resources usage). Both require pyproject.toml touch for wheel inclusion. |
| Directory placement | (A) `automation/workflows/static/` (co-located) vs (B) top-level `templates/` | **A: co-located** | Files are used only by `insights_formatter.py`. Co-location signals ownership. |
| File naming | `insights_report.css` + `insights_report.js` vs alternatives | **`insights_report.css` + `insights_report.js`** | Clear provenance, consistent naming. |

### F-17 Triage Decision

**Decision: Close as no-action.**

Evidence reviewed and confirmed by stakeholder:
- `HtmlRenderer` has no `__init__` method and no instance attributes.
- The class is functionally a namespace -- all methods operate purely on arguments.
- `_renderer = HtmlRenderer()` (line 705) holds no mutable state and cannot accumulate
  cross-test contamination.
- Adding `SystemContext.register_reset()` would: introduce a dependency on `SystemContext`
  where none exists, create a false signal that resettable state exists, and add complexity
  for zero behavioral benefit.
- If `HtmlRenderer` gains state in the future, the reset hook should be added at that time.

## User Stories

- As a **developer maintaining the insights export**, I want CSS and JS assets in proper
  `.css`/`.js` files, so that I get syntax highlighting, linting, and editor support when
  editing report styles and interactivity.

- As a **developer reading `insights_formatter.py`**, I want the 333 lines of string
  literals removed from the Python module, so that the module is focused on rendering logic
  rather than raw asset content.

- As a **report consumer**, I want the column alignment computation to be efficient, so that
  large tables render without unnecessary repeated work.

## Functional Requirements

### Must Have

- **FR-01 (F-11):** Pre-compute `_column_align_class(rows, col)` once per column before the
  row loop in `_render_table_section`. Store results in a dict keyed by column name. Use the
  cached value at both call sites (header cells, line 577; body cells, line 596). Remove
  per-cell invocations.

- **FR-02 (F-12):** Extract the `_CSS` string constant (lines 1100-1271, 172 lines) to
  `src/autom8_asana/automation/workflows/static/insights_report.css`.

- **FR-03 (F-12):** Extract the `_JS` string constant (lines 1277-1432, 156 lines) to
  `src/autom8_asana/automation/workflows/static/insights_report.js`.

- **FR-04 (F-12):** Load both files at module import time using
  `pathlib.Path(__file__).parent / "static" / "insights_report.css"` (and `.js`). Assign
  to module-level `_CSS` and `_JS` variables so all downstream references remain unchanged.

- **FR-05 (F-12):** Ensure `.css` and `.js` files are included in wheel builds. Update
  `pyproject.toml` build configuration as needed (e.g., `[tool.hatch.build]` force-include
  or package-data glob).

- **FR-06 (F-17):** No code change. Document closure rationale in this PRD (see Triage
  Decision above).

### Should Have

- **FR-07:** Add a module-level `__all__` or docstring note in the `static/` directory
  indicating these files are loaded at import time and inlined into generated HTML (not
  served as external resources).

## Non-Functional Requirements

- **NFR-01: Behavior preservation** -- Generated HTML reports must produce byte-for-byte
  identical inline CSS and JS content before and after F-12 extraction. The `_CSS` and `_JS`
  values seen by downstream code must be identical strings.

- **NFR-02: Performance** -- F-11 reduces `_column_align_class` calls from O(rows x columns)
  to O(columns). For a 100-row, 20-column table: from 2,000 calls to 20 calls.

- **NFR-03: No new dependencies** -- stdlib only. `pathlib` is already used throughout the
  codebase. No third-party packages added.

- **NFR-04: Build correctness** -- `pip install .` and `pip wheel .` must include the
  `static/` directory contents in the installed package.

## Edge Cases

| Case | Expected Behavior |
|------|------------------|
| CSS/JS files missing at import time | `FileNotFoundError` at module import -- fail fast, do not silently degrade to empty styles |
| Empty rows list passed to `_render_table_section` | `align_by_col` dict is empty; existing `if not columns: return empty_section` guard handles this before the alignment code runs |
| Column with all None values | `_column_align_class` returns `""` (left-aligned). Behavior unchanged by caching. |
| CSS/JS file contains BOM or non-UTF-8 | Load with explicit `encoding="utf-8"`. Files are authored in this project, so encoding is controlled. |
| Wheel build without static files | Build-time validation: `hatch build` must succeed and include the files. CI catches this via existing test suite (tests import the module). |

## Success Criteria

- [ ] F-11: `_column_align_class` is called exactly once per column per table (not per cell)
- [ ] F-12: `_CSS` content in `insights_report.css` matches the original string literal byte-for-byte
- [ ] F-12: `_JS` content in `insights_report.js` matches the original string literal byte-for-byte
- [ ] F-12: `insights_formatter.py` loads CSS/JS via `pathlib` at module level
- [ ] F-12: `pyproject.toml` updated to include `static/` in wheel builds
- [ ] F-17: No code change; finding closed with documented rationale
- [ ] All 445 workflow tests pass (green-to-green)
- [ ] Full test suite baseline maintained (no regressions in touched files)
- [ ] `mypy` passes clean on touched files
- [ ] Atomic commits: one commit per finding (F-11 and F-12 independent; F-17 no commit needed)

## Out of Scope

| Item | Reason |
|------|--------|
| `compose_report` logic | Sprint C deliverable, stable -- do not re-touch |
| `TableSpec` / `insights_tables.py` | Sprint C deliverable, stable |
| `insights_export.py` | No Sprint D findings in this file |
| Test fixture infrastructure (conftest) | Sprint C deliverable, stable |
| HtmlRenderer API surface | Internal rendering contract, do not change method signatures |
| CSS/JS content changes | Only moving files, not redesigning report styling |
| Jinja2 or template engine integration | The goal is file extraction, not a template system |
| CSS minification or build-time asset compilation | Out of scope; assets are inlined as-is |
| `importlib.resources` pattern introduction | Decided against in interview (pathlib selected) |
| Other files in `automation/workflows/` | No findings apply to them |

## Open Questions

None. All design decisions resolved in stakeholder interview.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/SPRINT-D-EXPORT/PRD.md` | Read |
| Framing Doc | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/frames/sprint-d-export-backlog.md` | Read |
| Source (formatter) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/insights_formatter.py` | Read |
| Build config | `/Users/tomtenuta/Code/autom8y-asana/pyproject.toml` | Read |
