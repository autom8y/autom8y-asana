# TDD: Sprint D -- Insights Export Backlog (Final)

## Overview

Two implementation items from the final insights export backlog sprint. F-11 pre-computes
a per-column alignment class outside the row loop. F-12 extracts 328 lines of inline CSS/JS
string literals to external `.css`/`.js` files loaded at module import time. F-17 is closed
(no code change).

## Context

- PRD: `.claude/wip/SPRINT-D-EXPORT/PRD.md`
- Source: `src/autom8_asana/automation/workflows/insights_formatter.py` (1,432 lines)
- Tests: `tests/unit/automation/workflows/test_insights_formatter.py` (3,599 lines, 445 tests)
- Build config: `pyproject.toml` (line 79-80)

All line references verified against current source on 2026-03-01.

---

## F-11: Pre-compute `_column_align_class` Per Column

### Problem

`_column_align_class(rows, col)` is called inside the inner loop of `_render_table_section`
(line 577 in header loop, line 596 in body loop). The function scans rows to find the first
non-None value per column. For a 100-row x 20-column table, this produces 2,000+ calls where
20 would suffice. The result is deterministic per column.

### Design

Insert a dict comprehension after the column guard (line 567-568) and before the header cell
loop (line 574). Replace both call sites with dict lookups.

### Exact Changes

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`

**Step 1 -- Insert alignment cache (after line 568, before line 570)**

After:
```python
        if not columns:
            return self._render_empty_section(section)
```

Before:
```python
        sid = _slugify(section.name)
```

Insert:
```python
        # Pre-compute alignment class per column (O(columns) instead of O(rows*columns))
        align_by_col = {col: _column_align_class(rows, col) for col in columns}
```

**Step 2 -- Replace header call site (line 577)**

Change:
```python
            align_cls = _column_align_class(rows, col)
```
To:
```python
            align_cls = align_by_col[col]
```

**Step 3 -- Replace body call site (line 596)**

Change:
```python
                align_cls = _column_align_class(rows, col)
```
To:
```python
                align_cls = align_by_col[col]
```

### Net diff

+2 lines, -0 lines (one new line for the dict comprehension, one blank line before `sid`
already exists). Two substitutions. No signature changes, no new imports.

---

## F-12: Extract CSS/JS to External Files

### Problem

`_CSS` (lines 1100-1271, 172 lines) and `_JS` (lines 1277-1432, 156 lines) are Python
triple-quoted string literals. They receive no editor syntax highlighting, no CSS/JS
linting, and typos are invisible until runtime.

### Design

Extract string content to co-located static files. Load at module import time via `pathlib`.
Assign to the same module-level `_CSS` and `_JS` names so all downstream references
(line 316: `f"<style>\n{_CSS}\n</style>\n"` and line 317: `f"<script>\n{_JS}\n</script>\n"`)
remain unchanged.

### New Files

**1. `src/autom8_asana/automation/workflows/static/insights_report.css`**

Content: the exact characters between `"""\` on line 1100 and `}"""` on line 1271.

The Python string `_CSS = """\...}"""` uses the backslash-continuation syntax: `"""\` means
the string starts immediately (no leading newline), and `}"""` means the string ends with `}`
(no trailing newline). The file content must therefore be:
- First line: `/* ===== CSS Custom Properties (Theme) ===== */`
- Last line: `}` (the closing brace of `@media print`)
- No trailing newline after the final `}`

Extraction procedure: copy lines 1101-1271 verbatim. The file content equals the Python
string value of `_CSS` exactly.

**2. `src/autom8_asana/automation/workflows/static/insights_report.js`**

Content: the exact characters between `"""\` on line 1277 and `})();"""` on line 1432.

Same pattern: lines 1278-1432 verbatim. No trailing newline.

Extraction procedure: copy lines 1278-1432 verbatim. The file content equals the Python
string value of `_JS` exactly.

**3. No `__init__.py` in `static/`**

The `static/` directory is a data directory, not a Python package. No `__init__.py` file.

### Changes to `insights_formatter.py`

**Step 1 -- Add `pathlib` import (after line 26, alongside existing stdlib imports)**

After:
```python
from typing import Any, Protocol
```

Insert:
```python
from pathlib import Path
```

**Step 2 -- Add static file loading block (replace lines 1096-1432)**

Replace the entire section from line 1096 (the CSS comment banner) through line 1432
(end of `_JS` string) with:

```python
# ---------------------------------------------------------------------------
# Static assets -- loaded once at import time, inlined into generated HTML
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / "static"
_CSS = (_STATIC_DIR / "insights_report.css").read_text(encoding="utf-8")
_JS = (_STATIC_DIR / "insights_report.js").read_text(encoding="utf-8")
```

This removes 337 lines and adds 6 lines (net -331 lines).

### String Boundary Verification

The `read_text()` call returns the file content. For byte-for-byte equivalence with the
original string values:

- `_CSS` original: starts with `/* ===== CSS Custom Properties (Theme) ===== */`, ends with
  `}` (no trailing newline in the Python string).
- `_JS` original: starts with `// ===== Sort =====`, ends with `})();` (no trailing newline
  in the Python string).
- `read_text()` behavior: returns file content including any trailing newline.

**Critical**: the extracted `.css` and `.js` files MUST NOT have a trailing newline. If the
editor or extraction tool adds one, `read_text()` will return a string with `\n` appended,
breaking byte-for-byte equivalence.

Verification command (run after extraction):
```bash
# Check no trailing newline
test "$(tail -c 1 src/autom8_asana/automation/workflows/static/insights_report.css | wc -l)" -eq 0
test "$(tail -c 1 src/autom8_asana/automation/workflows/static/insights_report.js | wc -l)" -eq 0
```

Alternative: if the extraction tool adds a trailing newline (which most editors do by
default), use `.read_text(encoding="utf-8").rstrip("\n")`. However, the cleaner approach
is to write the files without a trailing newline, keeping `read_text()` unmodified.

### `pyproject.toml` Changes

**No changes needed.**

The current build configuration:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/autom8_asana", "src/autom8_query_cli.py"]
```

Hatchling's default behavior includes all files within specified package directories in the
wheel build. Since `static/insights_report.css` and `static/insights_report.js` reside
under `src/autom8_asana/automation/workflows/static/`, they are included automatically.
The `only-packages` option (which would exclude non-Python files) is not set.

**Verification**: after implementation, confirm inclusion with:
```bash
pip wheel . --no-deps -w /tmp/whl && unzip -l /tmp/whl/*.whl | grep static
```

Expected output should show both `insights_report.css` and `insights_report.js` in the
wheel under `autom8_asana/automation/workflows/static/`.

### FR-07: Documentation Note

Add a brief comment at the top of `insights_report.css` (after the existing first comment
line) or as a standalone line. Similarly for `.js`. The PRD says "docstring note in the
static/ directory" -- since there is no `__init__.py`, this note goes in the files
themselves.

Suggested: a one-line comment at the top of each file:
```css
/* Loaded at import time by insights_formatter.py and inlined into generated HTML. */
```
```javascript
// Loaded at import time by insights_formatter.py and inlined into generated HTML.
```

These comments become part of the inlined HTML, which is acceptable (they are valid
CSS/JS comments and do not affect rendering). They must be inserted AFTER extraction,
as new content, which means `_CSS` and `_JS` will differ from the original values by
exactly this comment line.

**Decision**: skip FR-07. It is a "should have" and adding a comment changes the byte-for-byte
equivalence required by NFR-01. The loading mechanism (`_STATIC_DIR`, `read_text`) in the
Python source is self-documenting. If documentation is desired later, add it as a Python
comment in `insights_formatter.py` above the loading block (which is already done with the
`# Static assets -- loaded once at import time, inlined into generated HTML` comment).

---

## Commit Sequence

### Commit 1: F-11 -- Pre-compute column alignment class per column

**Files changed**: `insights_formatter.py` only (2-line diff)

This commit is independent of F-12 and should land first because it is trivially
reviewable and has zero risk.

### Commit 2: F-12 -- Extract inline CSS/JS to static files

**Files changed**:
- `insights_formatter.py` (add `pathlib` import, replace 337 lines with 6-line loading block)
- `static/insights_report.css` (new file, 171 lines)
- `static/insights_report.js` (new file, 155 lines)

**Files NOT changed**:
- `pyproject.toml` (no change needed)
- No `static/__init__.py` (data directory)

### No Commit for F-17

F-17 is closed as no-action. Rationale documented in PRD section "F-17 Triage Decision".

---

## Test Strategy

### Existing Test Coverage (No New Tests Needed)

Both F-11 and F-12 are behavior-preserving refactors. The existing 445-test suite validates
the unchanged output.

**F-11 alignment caching -- covered by**:
- `TestNumericAlignment::test_numeric_column_has_num_class` (line 1019): asserts `class="num"` in rendered output for numeric column
- `TestNumericAlignment::test_string_column_has_no_num_class` (line 1025): asserts no `num` class for string columns
- `TestPhase6QA::test_date_cells_have_date_class` (line 3404): asserts `date-cell` class on period columns
- Every test that renders a table section exercises `_render_table_section` which uses the alignment path

**F-12 CSS/JS extraction -- covered by**:
- `TestSelfContainedHtml::test_inline_css_present` (line 1055): asserts `<style>` and `</style>` in output
- `TestSelfContainedHtml::test_no_external_resources` (line 1041): asserts no `href="http"`, no `<link>` tags
- `TestComposeReport::test_compose_report_contains_inline_css` (line 820): asserts `<style>`, `font-family`, no `rel="stylesheet"`
- `TestPhase6QA::test_css_contains_light_and_dark_themes` (line 3367): asserts `:root {` and `[data-theme="dark"]`
- `TestPhase6QA::test_css_contains_print_styles` (line 3374): asserts `@media print`
- `TestPhase6QA::test_js_contains_all_functions` (line 3380): asserts all 11 JS function names present

**Build inclusion -- verified by**:
- The existing test suite imports `insights_formatter` at test time. If static files are
  missing, `read_text()` raises `FileNotFoundError` at import time, causing every formatter
  test to fail. This is the "fail fast" edge case from the PRD.

### Validation Steps

1. Run formatter tests: `pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q`
2. Run mypy: `mypy src/autom8_asana/automation/workflows/insights_formatter.py`
3. Verify no trailing newline in extracted files (see verification command above)
4. Verify wheel inclusion: `pip wheel . --no-deps -w /tmp/whl && unzip -l /tmp/whl/*.whl | grep static`

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Trailing newline in extracted files breaks string equivalence | Medium | Low (test suite catches immediately) | Verification command in commit checklist; `rstrip("\n")` fallback |
| Static files missing from wheel | Low | High (import-time crash in production) | Hatchling includes all files in package dir by default; wheel listing verification step |
| Editor reformats extracted CSS/JS | Low | Low (test suite catches) | Extract via scripted copy, not manual editing |

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/SPRINT-D-EXPORT/PRD.md` | Read |
| TDD (this) | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/SPRINT-D-EXPORT/TDD.md` | Written |
| Source | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/insights_formatter.py` | Read (1,432 lines) |
| Tests | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/automation/workflows/test_insights_formatter.py` | Read (3,599 lines) |
| Build config | `/Users/tomtenuta/Code/autom8y-asana/pyproject.toml` | Read (265 lines) |
