# Sprint D: Insights Export Backlog (Final)

**Initiative**: Final backlog sprint -- 3 P3 findings from the insights export pipeline review
**Rite**: 10x-dev (requirements-analyst -> architect -> principal-engineer -> qa-adversary)
**Codebase**: ~120K LOC async Python, FastAPI, ~11,100+ tests
**Entry**: requirements-analyst (brief interview to verify findings, surface F-12 design choices, and triage F-17)
**Prior work**: Sprints A+B (commit `5092d2d`, 10 findings), Sprint C (commits `eb85f3a`..`e721bbf`, 3 structural findings). 445 workflow tests passing, mypy clean.

---

## 1. Background

The insights export pipeline generates HTML reports by fetching 12 tables of business data
from the autom8y-data service, formatting them with inline CSS/JS, and uploading to Asana as
attachments. An architectural review produced 17 findings. Sprints A-C addressed 14 of them.

Sprint C shipped significant structural changes to `insights_formatter.py`:
- **F-03**: Extracted `TableSpec` declarative table configuration into `insights_tables.py`
- **F-04**: Spec-driven `compose_report` pipeline (eliminated table-name branching)
- **F-07**: Shared `ResolutionContext` fixture (eliminated 31x boilerplate)

These changes reduced the formatter by ~312 net LOC and shifted line numbers. **The review's
original line references for F-11, F-12, F-17 are stale.** Updated references are provided
below (verified against current source).

### Source Review

The full review with all 17 findings:
```
Read(".claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md")
```

### Codebase Knowledge

Load before making any code modifications:
```
Read(".know/architecture.md")    -- package structure, layers, entry points
Read(".know/conventions.md")     -- error handling, file organization, naming
```

---

## 2. The Three Findings

### F-11: `_column_align_class` Called Per-Cell, Scans All Rows (P3 PERFORMANCE)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Current lines**: 1065-1077 (definition), 577 + 596 (call sites in `_render_table_section`)

`_column_align_class(rows, col)` is called inside the inner loop of `_render_table_section`,
once per cell. For a table with 100 rows x 20 columns = 2,000 calls, each scanning up to
100 rows to find the first non-None value. Worst case: 200,000 row lookups for a single table.

The result is deterministic per column (not per cell). It should be computed once per column
before the row loop.

**Fix**: Compute `align_by_col = {col: _column_align_class(rows, col) for col in columns}`
before the row loop (after line 565). Use `align_by_col[col]` at lines 577 and 596.

**Effort**: ~30 minutes. Clear before/after. Minimal interview time needed.

### F-12: Inline CSS+JS is 333 Lines of Unmaintainable String Literals (P3 MAINTAINABILITY)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Current lines**: 1100-1271 (`_CSS`, 172 lines), 1277-1432 (`_JS`, 156 lines)

The `_CSS` and `_JS` constants are 333 lines of raw Python string literals. They have no
syntax highlighting, no CSS/JS linting, and no editor support. Any typo is invisible until
the report is opened in a browser.

The design decision (self-contained HTML output with no external resources) is sound and must
be preserved. The question is whether the *source representation* should be Python string
literals or external `.css`/`.js` files loaded at module import time.

**Design tension**: This project has no existing `importlib.resources` usage and no
package-data configuration in `pyproject.toml`. Introducing external static files requires:
1. Choosing a loading mechanism (`pathlib.Path(__file__).parent` vs `importlib.resources`)
2. Creating a templates/static directory (e.g., `automation/workflows/static/`)
3. Potentially registering package data in `pyproject.toml` (for `importlib.resources`)
4. Ensuring the files are included in wheel builds

**Effort**: ~2 hours. This is the highest-effort item and has genuine design choices.

### F-17: Module-Level `_renderer` Singleton (P3 MAINTAINABILITY)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Current line**: 705

```python
_renderer = HtmlRenderer()
```

This module-level singleton is created at import time. The project convention is to register
singletons with `SystemContext.register_reset()` so tests can reset state.

**However**: `HtmlRenderer` has no `__init__` method and no instance state. It is a pure
stateless class whose methods could equally be module-level functions. The `_renderer`
singleton is functionally equivalent to a namespace -- it holds no mutable state and cannot
accumulate cross-test contamination.

Adding a `SystemContext.register_reset()` hook would:
- Add complexity for zero behavioral benefit
- Create a false signal that HtmlRenderer has resettable state
- Introduce a dependency on `SystemContext` in a module that currently has none

**Recommendation**: CLOSE as no-action. If HtmlRenderer gains state in the future, add the
reset hook at that time. The interview should confirm this disposition.

---

## 3. Scope Boundaries

### IN SCOPE

- F-11: Cache `_column_align_class` result per column in `_render_table_section`
- F-12: Extract `_CSS` and `_JS` to external files (if interview confirms)
- F-17: Triage decision (close vs. minimal fix)
- Tests for any changes introduced
- mypy clean pass

### OUT OF SCOPE (Do NOT Touch)

| Item | Reason |
|------|--------|
| `compose_report` logic | Just refactored in Sprint C, do not re-touch |
| `TableSpec` / `insights_tables.py` | Sprint C deliverable, stable |
| `insights_export.py` | No Sprint D findings in this file |
| Test fixture infrastructure (conftest) | Sprint C deliverable, stable |
| HtmlRenderer API surface | Internal rendering contract, do not change signatures |
| CSS/JS content changes | Only moving files, not redesigning the report styling |

### Guardrails

1. **Behavior preservation**: Reports must produce identical HTML output. The CSS/JS extraction (F-12) must produce byte-for-byte identical inline content in the generated HTML.
2. **Green-to-green**: 445 workflow tests passing before and after. Full test suite baseline maintained.
3. **No new dependencies**: Use stdlib only. If `importlib.resources` is chosen for F-12, it is stdlib (Python 3.9+).
4. **Atomic commits**: One finding per commit. F-11, F-12, F-17 are independent.
5. **Small sprint**: This is ~2.5 hours of implementation work, not a multi-day initiative. Keep interview and design phases proportionally brief.

---

## 4. Key Files

| File | Role | Findings |
|------|------|----------|
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Report composition + rendering (1,432 lines) | F-11, F-12, F-17 |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Formatter tests | (may need updates for F-11, F-12) |
| `src/autom8_asana/automation/workflows/insights_tables.py` | TableSpec definitions (Sprint C) | (reference only, do not modify) |
| `pyproject.toml` | Build config (line 80: packages list) | (may need package-data for F-12) |

---

## 5. Interview Phase Guidance

This is a small backlog sprint. The interview should be proportionally brief -- 2-3 rounds
maximum, focused on the genuine decision points.

### Required interview topics

**F-12 design choices** (the only finding with real design surface area):
1. Loading mechanism: `pathlib.Path(__file__).parent / "static"` (simple, no config) vs `importlib.resources` (packaging-correct, needs `pyproject.toml` change). The project has zero `importlib.resources` usage today.
2. Directory placement: `automation/workflows/static/` (co-located) vs a top-level `templates/` directory.
3. File naming: `insights_report.css` + `insights_report.js`, or something else.

**F-17 triage**:
- Present the evidence that HtmlRenderer is stateless (no `__init__`, no instance attributes).
- Ask: close as no-action, or add a minimal reset hook as defensive practice?
- The architect should have the interview's decision before designing.

### Interview can skip

- F-11 implementation details (the fix is mechanical and unambiguous)
- CSS/JS content review (only the file extraction mechanism is in scope)
- Rendering pipeline internals (Sprint C just stabilized these)

---

## 6. Prior Work References

| Artifact | Location | Relevance |
|----------|----------|-----------|
| Export flow review | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/EXPORT-FLOW-REVIEW.md` | Full findings table, all 17 items |
| Sprint C PRD | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/PRD-SPRINT-C.md` | Design decisions from Sprint C |
| Sprint C TDD | `.claude/wip/SPIKE-INSIGHTS-CONSUMER/TDD-SPRINT-C.md` | Technical design from Sprint C |
| Sprint C frame | `.claude/wip/frames/sprint-c-export-structural.md` | Prior framing pattern |
| Sprint A+B commit | `5092d2d` | 10 findings resolved |
| Sprint C commits | `eb85f3a`, `57f865b`, `38e2467`, `e721bbf` | 3 structural findings resolved |
| Codebase architecture | `.know/architecture.md` | Package structure, layer boundaries |
| Conventions | `.know/conventions.md` | Error handling, naming, file organization |

---

## 7. Anti-Patterns for This Initiative

- **Over-engineering F-11**: This is a 10-line diff. Do not introduce a caching abstraction, a Column metadata class, or any new types. A dict comprehension before the loop is the entire fix.
- **Yak-shaving F-12 into a template system**: The goal is to move two string constants to two files. Not to build a Jinja2 template pipeline, a CSS minification step, or a build-time asset compilation system.
- **Adding complexity for F-17 when there is no problem**: If HtmlRenderer is confirmed stateless, closing the finding is the correct action. Adding a reset hook to satisfy a pattern checklist is negative value.
- **Scope creep into Sprint C territory**: Do not re-open `compose_report`, `TableSpec`, or the `ResolutionContext` fixture. They are stable.
- **Treating this as a major initiative**: Three P3 findings, ~2.5 hours of work. Keep the process proportional.

---

## 8. Next Commands

### Start the initiative (fresh session)

```
/go
```

When prompted for work description, provide:

```
@.claude/wip/frames/sprint-d-export-backlog.md

Sprint D (final) of the insights export improvements. Three P3 backlog findings: F-11
(column align caching), F-12 (CSS/JS file extraction), F-17 (renderer singleton triage).
Start with a brief interview to confirm F-12 design choices and F-17 disposition.
```

### Alternative: Direct interview start (if session is already active)

```
/task Start the Sprint D interview phase for insights export backlog.
Read the framing document at .claude/wip/frames/sprint-d-export-backlog.md for full context.
Route to requirements-analyst. Focus interview on F-12 design choices (loading mechanism,
directory placement) and F-17 triage (close vs. fix). F-11 needs no interview time.
```

### After interview: route to architect

```
/task Route the Sprint D PRD to architect for technical design. Brief TDD expected --
this is a small sprint with one mechanical fix (F-11), one file extraction (F-12), and
one triage decision (F-17).
```
