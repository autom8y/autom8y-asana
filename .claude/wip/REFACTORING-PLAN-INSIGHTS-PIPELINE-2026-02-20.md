# Refactoring Plan: Insights Pipeline Hygiene
**Date**: 2026-02-20
**Input**: Smell report from Code Smeller (12 findings, 0 P1, 3 P2, 4 P3, 3 P4)
**Author**: Architect Enforcer
**Status**: Ready for Janitor

---

## Architectural Assessment

### Boundary Health

The insights pipeline is a two-file system: `insights_formatter.py` (rendering)
and `insights_export.py` (workflow orchestration). The dependency direction is
correct: export imports from formatter, not the reverse. This boundary must be
preserved in all refactors.

**Boundary rule**: formatter is a pure rendering module. It must not import from
the workflow module (`insights_export.py`). All constant sharing must go through
the formatter-owns-vocabulary direction.

### Root Cause Clusters

Three clusters account for 9 of 12 findings:

1. **Constant duplication across boundary** (SM-004, SM-011): The export module
   re-declares constants the formatter already owns. Fix: import from source of
   truth.

2. **Mypy-invisible numeric narrowing** (SM-001): `dict.get()` returns
   `Any`, and mypy cannot narrow through list comprehensions with inline
   `isinstance` guards. Fix: extract helper with explicit return type.

3. **Speculative test authoring** (SM-002, SM-003, SM-005, SM-008): Tests
   written for future state or with fragile coupling to HTML structure. Fix:
   two sub-cases — SM-002 is a live contract assertion that should be annotated;
   SM-003/SM-005/SM-008 are internal test hygiene issues.

### Decisions Made

**SM-004 (TABLE_ORDER/TABLE_NAMES)**: Option A — formatter owns `TABLE_ORDER`,
export imports and aliases. Rationale: the formatter is the vocabulary owner
for rendering order; the export workflow is a consumer. Inverting the direction
would create a formatter dependency on the workflow (boundary violation).

**SM-011 (lambda handler constants)**: Import constants from
`insights_export.py` rather than duplicating literals. The lambda handler is
already a thin adapter; hard-coded literals are accidental duplication.

**SM-001 (type: ignore)**: Extract `_extract_numeric_values()` helper inside
`HtmlRenderer`. The helper encapsulates the `isinstance` narrowing and returns
`list[float]`, making the return type visible to mypy at all call sites.
Sparkline and best-week calculations simplify to list operations on the typed
return value.

**SM-002 (VALID_FRAME_TYPES)**: Accept with annotation. The `"question"` value
is already shipped to the API enum side (confirmed by D-022 closure). The test
is a forward-looking contract assertion, not a smell. Annotate in-test to
document the intent.

**SM-006 (_render_empty_section / _render_error_section)**: Extract shared
section scaffold into a private `_render_section_scaffold()` helper. The two
methods differ only in body content (empty `<p>` vs error `<div>`). The
scaffold assembly (header, toggle, body wrapper, subtitle) is identical.

**SM-009 (compose_report)**: Defer. At 134 lines, `compose_report` is a
readable orchestration function. Its 5 responsibilities are sequential
transformation stages, not mixed concerns — this is appropriate for a top-level
public function. Decomposition would add indirection without reducing
complexity. Annotate with a complexity note.

**SM-007 (_render_kpi_cards)**: Defer. At 140 lines, the function is long but
each card block is independently readable. Splitting into 6 `_card_*()` methods
would fragment the cohesive card computation pattern. The `_extract_numeric_values()`
helper from SM-001 removes the type: ignore noise, which is the real friction.

---

## Tier Classification

| ID | Tier | Rationale |
|----|------|-----------|
| SM-004 | 1 (Execute) | Constant duplication across module boundary; single-commit fix |
| SM-001 | 1 (Execute) | Type annotations suppress valid mypy checks; extract helper |
| SM-011 | 1 (Execute) | Lambda handler has hardcoded literals that diverge on change |
| SM-005 | 1 (Execute) | Module-level `import json` removes 7 repeated local imports |
| SM-006 | 1 (Execute) | Near-duplicate renderers with identical scaffolds; extract helper |
| SM-003 | 1 (Execute) | `str.find()` assertions are brittle; replace with row-order assertions |
| SM-012 | 1 (Execute) | Docstring says "markdown" in two places; produces HTML since WS-G |
| SM-010 | 1 (Execute) | `deps_response` alias is undocumented; trivial inline comment |
| SM-008 | 2 (Annotate) | 31 ResolutionContext patches; fixture refactor is medium effort and independent of pipeline logic; defer to test architecture initiative |
| SM-002 | 3 (Accept) | `"question"` is in the live API enum; VALID_FRAME_TYPES is correct; no action |
| SM-009 | 3 (Accept) | 134-line orchestration function with sequential stages; decomposition adds indirection without value |
| SM-007 | 3 (Accept) | 140-line KPI renderer; SM-001 fix removes the type: ignore noise; residual length is acceptable for card-per-block structure |

---

## Ordered Commit Sequence

Execute commits in this order. Each commit is atomic and independently
revertable. Run the verification command before moving to the next commit.

### Phase 1: Constants and Imports (Zero Risk)

#### Commit 1 — RF-001: Import TABLE_ORDER into insights_export.py; remove TABLE_NAMES duplication

**Risk**: Low. No behavior change. TABLE_ORDER and TABLE_NAMES are identical
12-element lists. `TOTAL_TABLE_COUNT` becomes `len(TABLE_ORDER)`, same value.
Tests import both names from `insights_export`; the alias preserves those
import paths.

**Before State**:
- `src/autom8_asana/automation/workflows/insights_export.py:73-88`
  ```python
  # Table names in section order (per PRD FR-W01.6, extended per TDD-WS5)
  TABLE_NAMES: list[str] = [
      "SUMMARY",
      "APPOINTMENTS",
      ...
      "UNUSED ASSETS",
  ]

  TOTAL_TABLE_COUNT = len(TABLE_NAMES)  # 12
  ```

**After State**:
- `src/autom8_asana/automation/workflows/insights_export.py:73-88`
  ```python
  from autom8_asana.automation.workflows.insights_formatter import TABLE_ORDER

  # Public alias — same list, formatter owns the vocabulary
  TABLE_NAMES = TABLE_ORDER
  TOTAL_TABLE_COUNT = len(TABLE_NAMES)  # 12
  ```

**Invariants**:
- `TABLE_NAMES` is still importable from `insights_export` (existing test imports preserved)
- `TOTAL_TABLE_COUNT` remains 12
- `TABLE_ORDER` in formatter is unchanged
- No new imports in formatter (dependency direction preserved)

**Verification**:
```bash
python -m pytest tests/unit/automation/workflows/test_insights_export.py -x -q
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q
```
Expected: all currently-passing tests pass with no new failures.

**Rollback**: Revert single commit; restore original TABLE_NAMES literal block.

---

#### Commit 2 — RF-002: Import constants into lambda handler; remove hardcoded literals

**Risk**: Low. Lambda handler is a thin adapter. The literals are identical to
the source constants confirmed above. Only `default_params` dict changes; the
`WorkflowHandlerConfig` constructor call is unchanged.

**Before State**:
- `src/autom8_asana/lambda_handlers/insights_export.py:40-44`
  ```python
  _config = WorkflowHandlerConfig(
      ...
      default_params={
          "max_concurrency": 5,
          "attachment_pattern": "insights_export_*.html",
          "row_limits": {"APPOINTMENTS": 100, "LEADS": 100, "ASSET TABLE": 150},
      },
      ...
  )
  ```

**After State**:
- Add to imports at top of `lambda_handlers/insights_export.py`:
  ```python
  from autom8_asana.automation.workflows.insights_export import (
      DEFAULT_ATTACHMENT_PATTERN,
      DEFAULT_MAX_CONCURRENCY,
      DEFAULT_ROW_LIMITS,
      InsightsExportWorkflow,
  )
  ```
- `_config` dict:
  ```python
  _config = WorkflowHandlerConfig(
      ...
      default_params={
          "max_concurrency": DEFAULT_MAX_CONCURRENCY,
          "attachment_pattern": DEFAULT_ATTACHMENT_PATTERN,
          "row_limits": DEFAULT_ROW_LIMITS,
      },
      ...
  )
  ```
- Remove `InsightsExportWorkflow` from the deferred `_create_workflow` import
  (it is now top-level); adjust `_create_workflow` accordingly.

**Note on deferred import**: The deferred import inside `_create_workflow` was
for cold-start optimization. Moving `InsightsExportWorkflow` to the top level
negates that optimization for one symbol. If cold-start is a concern, keep the
deferred import for `InsightsExportWorkflow` and add a separate top-level import
only for the constants. The constants are simple module-level values; importing
them at load time has negligible cost.

**Revised after state for cold-start safety**:
```python
# Top-level import for constants only
from autom8_asana.automation.workflows.insights_export import (
    DEFAULT_ATTACHMENT_PATTERN,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_ROW_LIMITS,
)

def _create_workflow(asana_client: Any, data_client: Any) -> Any:
    """Deferred workflow construction for cold-start optimization."""
    from autom8_asana.automation.workflows.insights_export import (
        InsightsExportWorkflow,
    )
    ...
```

**Invariants**:
- `_config.default_params` values are identical at runtime
- `WorkflowHandlerConfig` constructor call is structurally unchanged
- `_create_workflow` deferred import for `InsightsExportWorkflow` preserved

**Verification**:
```bash
python -m pytest tests/unit/lambda_handlers/test_insights_export.py -x -q
```
Expected: all currently-passing tests pass.

**Rollback**: Revert single commit; restore inline literals.

---

### Phase 2: Type Safety (Low Risk)

#### Commit 3 — RF-003: Extract _extract_numeric_values(); remove 5 type: ignore comments

**Risk**: Low. Pure extraction. The helper encapsulates existing logic that
already existed inline; no new logic is introduced. `type: ignore` comments are
removed because mypy can now infer the return type from the helper's annotation.

**Before State** (representative — `insights_formatter.py` lines 449-456):
```python
br_values = [
    r.get("booking_rate")
    for r in week_rows
    if r.get("booking_rate") is not None
    and isinstance(r.get("booking_rate"), (int, float))
]
if br_values:
    sparkline_svg = self._render_sparkline(br_values)  # type: ignore[arg-type]
```

And at lines 488-495 (best-week max):
```python
br_pairs = [
    (r.get("booking_rate"), r.get("period_label", ""))
    for r in week_rows
    if r.get("booking_rate") is not None
    and isinstance(r.get("booking_rate"), (int, float))
]
if br_pairs:
    best_val, best_label = max(br_pairs, key=lambda p: p[0])  # type: ignore[arg-type,return-value]
    cards.append(
        self._kpi_card(
            "Best Week",
            f"{best_val * 100:.2f}%",  # type: ignore[operator]
```

And at lines 510-526 (spend trend):
```python
spend_values = [
    r.get("spend")
    for r in week_rows
    if r.get("spend") is not None
    and isinstance(r.get("spend"), (int, float))
]
...
recent_sum = sum(recent)  # type: ignore[arg-type]
prior_sum = sum(prior) if prior else 0  # type: ignore[arg-type]
```

**After State**:

Add private helper to `HtmlRenderer` class (before `_render_kpi_cards`):
```python
@staticmethod
def _extract_numeric_values(
    rows: list[dict[str, Any]], key: str
) -> list[float]:
    """Return float values for `key` from rows, skipping None and non-numeric."""
    return [
        float(r[key])
        for r in rows
        if r.get(key) is not None and isinstance(r.get(key), (int, float))
    ]
```

Replace inline list comprehensions + type: ignore at all 5 sites:

- Line ~454: `br_values = self._extract_numeric_values(week_rows, "booking_rate")`
- Lines ~488-494: Replace the `br_pairs` comprehension with two extractions:
  ```python
  br_nums = self._extract_numeric_values(week_rows, "booking_rate")
  # pair each with its period_label for max()
  br_pairs: list[tuple[float, str]] = [
      (v, week_rows[i].get("period_label", ""))
      for i, v in enumerate(br_nums)
      # only rows where booking_rate was numeric (already filtered)
      # Note: index alignment requires building pairs from filtered rows instead
  ]
  ```
  **Cleaner alternative**: build pairs directly from filtered rows (avoids index drift):
  ```python
  br_pairs: list[tuple[float, str]] = [
      (float(r["booking_rate"]), str(r.get("period_label", "")))
      for r in week_rows
      if r.get("booking_rate") is not None
      and isinstance(r.get("booking_rate"), (int, float))
  ]
  if br_pairs:
      best_val, best_label = max(br_pairs, key=lambda p: p[0])
  ```
  Use this form — explicit types on the list annotation satisfy mypy without a helper.
- Lines ~510-515: `spend_values = self._extract_numeric_values(week_rows, "spend")`
- Line ~525: `recent_sum = sum(recent)` — `recent` is now `list[float]`, no ignore needed
- Line ~526: `prior_sum = sum(prior) if prior else 0` — same, `prior` is `list[float]`

**Contract refinement**: The helper `_extract_numeric_values` is used for
sparkline and spend trend. The best-week case uses an explicit typed list
comprehension instead (avoids index-alignment complexity). Both approaches
eliminate `type: ignore`.

**Invariants**:
- Filtering logic is unchanged: `None` and non-numeric values are excluded
- `_render_sparkline` receives `list[float]` (was `list[Any]`)
- `max()` on `br_pairs` is unchanged in semantics
- `sum()` calls operate on `list[float]` (was `list[Any]`)
- All KPI card values are identical for identical input data

**Verification**:
```bash
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q -k "kpi"
# Then full formatter suite
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q
# Then mypy check
python -m mypy src/autom8_asana/automation/workflows/insights_formatter.py --ignore-missing-imports
```
Expected: 0 `type: ignore` comments remain in `_render_kpi_cards`, mypy clean.

**Rollback**: Revert single commit; restore inline comprehensions with type: ignore.

---

### Phase 3: Rendering Structure (Low Risk)

#### Commit 4 — RF-004: Extract _render_section_scaffold() for empty/error renderers

**Risk**: Low. Pure extraction of identical HTML-building logic. The two
renderers differ only in the last element of their body content.

**Before State**:

`_render_empty_section` (`insights_formatter.py:691-715`) and
`_render_error_section` (`insights_formatter.py:717-741`) share identical:
- `sid = _slugify(section.name)`
- `is_expanded` + `collapsed_class` logic
- `subtitle` + `subtitle_html` computation
- Outer `<section>`, `<div class="section-header">`, `<h2>`, toggle icon, body wrapper

They differ only in the final body content element:
- Empty: `<p class="empty">{html.escape(message)}</p>`
- Error: `<div class="error-box">{html.escape(error_text)}</div>`

**After State**:

Add private helper returning the scaffold as a tuple of parts (prefix, body-open, suffix):
```python
def _section_scaffold(
    self, section: DataSection
) -> tuple[str, str, str]:
    """Return (prefix, body_open, suffix) for section rendering.

    prefix: everything up to and including the body div open tag
    body_open: the body div open tag (with collapsed class)
    suffix: closing tags for body and section
    Note: subtitle_html is included in prefix, callers append body content then suffix.
    """
```

Or simpler: extract a helper that takes the body content string as a parameter:
```python
def _render_section_with_body(
    self, section: DataSection, body_content: str
) -> str:
    """Render a section with the given body_content string."""
    sid = _slugify(section.name)
    is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
    collapsed_class = "" if is_expanded else " collapsed"
    subtitle = _SECTION_SUBTITLES.get(section.name, "")
    subtitle_html = (
        f'<div class="section-subtitle">{html.escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    return (
        f'<section id="{sid}" class="table-section">\n'
        f'<div class="section-header" onclick="toggleSection(\'{sid}\')">\n'
        f"<h2>{html.escape(section.name)}</h2>\n"
        f'<div class="section-controls">'
        f'<span class="toggle-icon{collapsed_class}" id="toggle-{sid}">\u25bc</span>'
        f"</div>\n"
        "</div>\n"
        f'<div class="section-body{collapsed_class}" id="body-{sid}">\n'
        f"{subtitle_html}\n"
        f"{body_content}\n"
        "</div>\n"
        "</section>"
    )
```

Then the two methods become:
```python
def _render_empty_section(self, section: DataSection) -> str:
    message = section.empty_message or "No data available"
    body = f'<p class="empty">{html.escape(message)}</p>'
    return self._render_section_with_body(section, body)

def _render_error_section(self, section: DataSection) -> str:
    error_text = section.error or "Unknown error"
    body = f'<div class="error-box">{html.escape(error_text)}</div>'
    return self._render_section_with_body(section, body)
```

**Invariants**:
- HTML output is byte-for-byte identical for identical input
- `_render_empty_section` and `_render_error_section` public signatures unchanged
- `_render_section_with_body` is private (prefixed `_`), not in public API
- `_DEFAULT_EXPANDED_SECTIONS` and `_SECTION_SUBTITLES` lookups are unchanged

**Verification**:
```bash
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q -k "empty or error"
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q
```
Expected: all tests pass; no new test changes required.

**Rollback**: Revert single commit.

---

### Phase 4: Test Quality (Low Risk)

#### Commit 5 — RF-005: Fix fragile str.find() sort assertions in test_insights_formatter.py

**Risk**: Low. Test-only change. Production code is unchanged.

**Before State**:

`tests/unit/automation/workflows/test_insights_formatter.py:2031-2034`:
```python
high_pos = asset_tbody.find("High")
mid_pos = asset_tbody.find("Mid")
low_pos = asset_tbody.find("Low")
assert high_pos < mid_pos < low_pos
```

`tests/unit/automation/workflows/test_insights_formatter.py:2750-2753`:
```python
high_pos = tbody.find("HighSpend")
low_pos = tbody.find("LowSpend")
no_pos = tbody.find("NoSpend")
assert high_pos < low_pos < no_pos, "Null spend should sort to bottom"
```

The `str.find()` approach breaks when any column value in a higher-ranked row
happens to contain the substring of a lower-ranked asset name, or when the HTML
structure changes. The data being searched is not isolated to the `name` column.

**After State**:

Extract row order from the rendered HTML by parsing the `<tbody>` into rows and
reading the first cell (name column):
```python
import re

def _extract_row_names(tbody_html: str) -> list[str]:
    """Extract first-column text from each <tr> in tbody HTML."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tbody_html, re.DOTALL)
    names = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if cells:
            names.append(cells[0].strip())
    return names
```

Replace both assertion blocks:
```python
# Test 1 (lines 2031-2034)
row_names = _extract_row_names(asset_tbody)
assert row_names.index("High") < row_names.index("Mid") < row_names.index("Low")

# Test 2 (lines 2750-2753)
row_names = _extract_row_names(tbody)
assert row_names.index("HighSpend") < row_names.index("LowSpend") < row_names.index("NoSpend"), \
    "Null spend should sort to bottom"
```

The helper `_extract_row_names` is a module-level private function in the test
file. It is not parameterizable or reusable outside this module.

**Invariants**:
- Assertion semantics are identical: relative order check
- Tests still fail if sort order is wrong
- Tests no longer fail due to substring collisions in other columns

**Verification**:
```bash
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q -k "asset" -v
```
Expected: the two asset sort tests pass. If either test fails after the change,
the sort regression is real and should be investigated before proceeding.

**Rollback**: Revert single commit.

---

#### Commit 6 — RF-006: Move `import json` to module level in test_insights_formatter.py

**Risk**: Trivial. Test-only change. Seven methods in `test_insights_formatter.py`
have `import json as json_mod` as the first line of the method body.

**Before State** (representative, 7 occurrences at lines 2219, 2335, 2800, 2951, 3021, 3040, 3061):
```python
def test_script_json_blocks_contain_valid_json(self):
    import json as json_mod
    ...
    parsed = json_mod.loads(json_str)
```

**After State**:

Add `import json` to the module-level imports block at the top of
`tests/unit/automation/workflows/test_insights_formatter.py`.

Replace all 7 occurrences of `import json as json_mod` and all references
`json_mod.loads(...)` / `json_mod.dumps(...)` etc. with the module-level `json`
name.

**Invariants**:
- Test behavior is unchanged
- `json` is a stdlib module; no version compatibility concern
- All test method signatures unchanged

**Verification**:
```bash
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q -k "json"
python -m pytest tests/unit/automation/workflows/test_insights_formatter.py -x -q
```
Expected: all tests pass. No new test count changes.

**Rollback**: Revert single commit.

---

### Phase 5: Documentation Fixes (Trivial Risk)

#### Commit 7 — RF-007: Fix "markdown" docstrings in insights_export.py; annotate SM-008 deferral; annotate deps_response

**Risk**: Trivial. Documentation-only changes in two files plus a comment
addition in the test suite. No behavior change.

**Files and changes**:

**File 1**: `src/autom8_asana/automation/workflows/insights_export.py`

- Line 92: Change `"""Daily insights export markdown report for Offer tasks.` to
  `"""Daily insights export HTML report for Offer tasks.`
- Line 102: Change `c. Compose markdown report via insights_formatter` to
  `c. Compose HTML report via insights_formatter`

**File 2**: `src/autom8_asana/api/health_models.py`

- Line 100-102: Add inline comment to `deps_response`:
  ```python
  # /health/deps (dependency probe) -- same signature as readiness_response
  # with more granular checks.
  # Alias: deps_response is identical to readiness_response. Both endpoints
  # share the same response factory. See api/routes/health.py for mount points.
  deps_response = readiness_response
  ```

**File 3**: `tests/unit/automation/workflows/test_insights_export.py`

- Locate the `ResolutionContext` patch boilerplate (SM-008 deferral). Add a
  comment block near the top of the `TestUploadAndCleanup` class or the first
  test that uses this pattern:
  ```python
  # NOTE: ResolutionContext patch boilerplate is repeated across ~31 test methods.
  # Consolidation via a shared fixture is deferred (SM-008) to a dedicated test
  # architecture initiative. The pattern is consistent and functional as-is.
  ```

**Invariants**:
- No production behavior changes
- No test behavior changes
- All docstring changes are purely descriptive (update "markdown" -> "HTML")

**Verification**:
```bash
python -m pytest tests/unit/automation/workflows/test_insights_export.py -x -q
python -m pytest tests/ -x -q --tb=no -q 2>&1 | tail -5
```
Expected: test counts unchanged. No new failures.

**Rollback**: Revert single commit.

---

## SM-002 Disposition: Accept with Attestation

`VALID_FRAME_TYPES` in `tests/unit/clients/data/test_contract_alignment.py:33`
includes `"question"`. The smell report flagged this as a pending enum value.

**Finding after verification**: The `"question"` frame type was added to the
autom8_data API enum as part of D-022 work (confirmed in project memory:
`"ad_questions entity type mapped to question"`). The `VALID_FRAME_TYPES` set
is a local copy of the autom8_data schema — it is correct. No action required.

---

## SM-008 Deferral: Annotate

31 `ResolutionContext` patch sites across `test_insights_export.py` represent
boilerplate that could be consolidated into a pytest fixture. This is deferred
because:

1. The refactor scope is medium (test architecture, not pipeline logic)
2. The pattern is functional and consistently applied
3. A pytest fixture refactor may touch fixture scoping rules and interfere with
   async test isolation

Trigger for execution: dedicated test architecture initiative or when the test
file exceeds 2000 lines and fixture debt becomes a maintenance cost.

---

## SM-009 / SM-007 Disposition: Accept

`compose_report` (134 lines): Sequential transformation orchestration. The
function's 5 responsibilities are ordered pipeline stages, not mixed concerns.
The function reads cleanly as a narrative of the report-building process.
Extracting sub-functions would introduce named stages that have no independent
callers and would require passing significant shared state as parameters.

`_render_kpi_cards` (140 lines): Each of 6 card blocks is independent. The
SM-001 fix (RF-003) eliminates the type: ignore noise. The remaining length is
repetitive-but-readable card computations. Splitting into `_card_cpl()`,
`_card_booking_rate()`, etc. would add 6 private methods that are never called
independently and would make the card-construction pattern harder to scan.

---

## Risk Matrix

| Commit | Blast Radius | Detection Speed | Rollback Cost | Net Risk |
|--------|-------------|-----------------|---------------|----------|
| RF-001 (TABLE_ORDER alias) | insights_export imports | Immediate (import error or test failure) | 1 min | Low |
| RF-002 (lambda constants) | lambda_handlers/insights_export.py | Test suite | 1 min | Low |
| RF-003 (type: ignore / helper) | _render_kpi_cards, sparkline, best-week | KPI card tests | 5 min | Low |
| RF-004 (scaffold extract) | _render_empty_section, _render_error_section | Section render tests | 3 min | Low |
| RF-005 (str.find repair) | 2 test methods | Test run | 2 min | Trivial |
| RF-006 (import json) | 7 test methods | Test run | 2 min | Trivial |
| RF-007 (docstrings + comments) | None | Visual review | 1 min | Trivial |

No commit has cross-file blast radius beyond what is listed. All changes are
detectable by the existing test suite within one test run.

---

## Janitor Notes

### Commit Conventions

Follow the project's existing commit message style (from git log):
```
fix(insights): <description>
refactor(insights): <description>
test(insights): <description>
docs(insights): <description>
```

Suggested prefixes per commit:
- RF-001: `refactor(insights): import TABLE_ORDER from formatter; alias TABLE_NAMES`
- RF-002: `refactor(lambda): import insights_export constants; remove hardcoded literals`
- RF-003: `refactor(formatter): extract _extract_numeric_values; remove type: ignore`
- RF-004: `refactor(formatter): extract _render_section_with_body scaffold helper`
- RF-005: `test(formatter): replace str.find sort assertions with row-index assertions`
- RF-006: `test(formatter): move import json to module level`
- RF-007: `docs(insights): fix "markdown" docstrings; annotate deps_response alias`

### Test Requirements

- Run `python -m pytest tests/unit/automation/workflows/ -x -q` after each commit
- Run `python -m pytest tests/unit/lambda_handlers/ -x -q` after RF-002
- Run `python -m pytest tests/unit/clients/data/test_contract_alignment.py -x -q` before starting (baseline)
- Run mypy after RF-003: `python -m mypy src/autom8_asana/automation/workflows/insights_formatter.py --ignore-missing-imports`

### Critical Ordering

**RF-001 must precede RF-002**: RF-002 imports from `insights_export.py` which
will itself import from `insights_formatter.py` after RF-001. Both must be in
place before lambda handler imports are added, to avoid a transient import error
if RF-002 is applied to a pre-RF-001 codebase.

RF-003, RF-004, RF-005, RF-006, RF-007 are independent of each other and can
be applied in any order after RF-001.

### Do Not Change

- The `_render_kpi_cards` decomposition is explicitly deferred (SM-007: Accept)
- The `compose_report` decomposition is explicitly deferred (SM-009: Accept)
- `VALID_FRAME_TYPES` in `test_contract_alignment.py` is correct as-is (SM-002: Accept)
- The deferred import of `InsightsExportWorkflow` in the lambda handler must be
  preserved for cold-start optimization (see RF-002 revised after state)

---

## Artifact Verification

| File | Read | State Confirmed |
|------|------|-----------------|
| `src/autom8_asana/automation/workflows/insights_formatter.py` lines 1-60 | Yes | `TABLE_ORDER` at line 34, 12 elements |
| `src/autom8_asana/automation/workflows/insights_formatter.py` lines 440-560 | Yes | 5 type: ignore at lines 456, 495, 499, 525, 526 |
| `src/autom8_asana/automation/workflows/insights_formatter.py` lines 691-741 | Yes | Duplicate scaffold confirmed in empty/error renderers |
| `src/autom8_asana/automation/workflows/insights_export.py` lines 50-102 | Yes | `TABLE_NAMES` duplicate at lines 73-86; `TOTAL_TABLE_COUNT` at 88; "markdown" docstrings at lines 92, 102 |
| `src/autom8_asana/lambda_handlers/insights_export.py` (full) | Yes | Hardcoded literals at lines 41-43 confirmed |
| `tests/unit/clients/data/test_contract_alignment.py` lines 1-40 | Yes | `VALID_FRAME_TYPES = {"offer", "unit", "business", "asset", "question"}` at line 33 |
| `tests/unit/automation/workflows/test_insights_formatter.py` lines 2025-2040 | Yes | `str.find("High")` etc. at lines 2031-2034 |
| `tests/unit/automation/workflows/test_insights_formatter.py` lines 2745-2760 | Yes | `str.find("HighSpend")` etc. at lines 2750-2753 |
| `tests/unit/automation/workflows/test_insights_formatter.py` (import json) | Yes | 7 inline imports at lines 2219, 2335, 2800, 2951, 3021, 3040, 3061 |
| `tests/unit/automation/workflows/test_insights_export.py` (ResolutionContext) | Yes | 31 patch sites confirmed |
| `src/autom8_asana/api/health_models.py` lines 100-103 | Yes | `deps_response = readiness_response` with comment but no alias explanation |

---

## Acid Test

Following this plan exactly produces 7 atomic commits that:
1. Eliminate both constant duplication sites (TABLE_ORDER, lambda literals)
2. Remove all 5 `type: ignore` suppression comments
3. Reduce `_render_empty_section` + `_render_error_section` to single-line delegators
4. Replace 2 fragile `str.find()` sort assertions with structural row-index checks
5. Consolidate 7 method-local `import json` statements to 1 module-level import
6. Fix 3 stale "markdown" references in docstrings and annotate 2 deferred items

No test changes behavior. No production logic changes behavior. All 7 commits
are independently revertable.
