---
type: audit
---

# Smell Report: Insights Pipeline (2026-02-20)

**Scope**: 10 focus files across insights formatter, export workflow, health endpoints, lambda handler, and contract tests
**Scanner**: Code Smeller (hygiene rite)
**Status**: Complete -- ready for Architect Enforcer

---

## Summary

| Category | Count | P1 | P2 | P3 | P4 |
|----------|-------|----|----|----|----|
| Type Safety | 1 | - | 1 | - | - |
| Contract Drift | 1 | - | 1 | - | - |
| Test Fragility | 1 | - | - | 1 | - |
| DRY Violations | 4 | - | 1 | 2 | 1 |
| Complexity | 2 | - | - | 2 | - |
| Dead Code / Naming | 2 | - | - | - | 2 |
| Import Hygiene | 1 | - | - | 1 | - |
| **Total** | **12** | **0** | **3** | **4** | **3** |

---

## Confirmed Findings (from pre-identified items)

### SM-001 (HYG-001): `type: ignore` suppressions in insights_formatter.py [P2]

**Category**: Type Safety
**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: 456, 495, 499, 525, 526

**Evidence**: Five `# type: ignore` comments suppress mypy errors in the KPI card rendering logic:

```python
# Line 456 -- list comprehension produces list[Any | None], not list[float]
sparkline_svg = self._render_sparkline(br_values)  # type: ignore[arg-type]

# Line 495 -- max() on tuple[Any, Any] produces unprovable return type
best_val, best_label = max(br_pairs, key=lambda p: p[0])  # type: ignore[arg-type,return-value]

# Line 499 -- best_val might not support multiplication
f"{best_val * 100:.2f}%",  # type: ignore[operator]

# Lines 525-526 -- sum() on list[Any | None] has unresolvable type
recent_sum = sum(recent)  # type: ignore[arg-type]
prior_sum = sum(prior) if prior else 0  # type: ignore[arg-type]
```

**Root Cause**: The list comprehension filters produce `list[int | float | None]` because `r.get("booking_rate")` returns `Any | None`. The `isinstance` guard narrows at runtime but mypy cannot prove it through the list comprehension.

**Blast Radius**: 5 lines, 1 file, no downstream impact (rendering only)
**Fix Complexity**: Low -- type-narrow via a helper function like `_extract_numeric_values(rows, key) -> list[float]` that handles the isinstance check internally
**ROI Score**: 7.0/10 -- low effort, removes 5 suppressions, improves maintainability

---

### SM-002 (HYG-002): Contract test VALID_FRAME_TYPES loosened without upstream API change [P2]

**Category**: Contract Drift
**File**: `tests/unit/clients/data/test_contract_alignment.py`
**Line**: 33

**Evidence**:

```python
VALID_FRAME_TYPES = {"offer", "unit", "business", "asset", "question"}
```

The test set includes `"question"` which was added when the `ad_questions` factory mapping was introduced. However, the upstream `autom8_data` API enum (`InsightsRequest.frame_type`) does not yet include `"question"` -- the data service returns a validation error for this value. This is documented in project memory:

> AD QUESTIONS: `frame_type: 'question'` not in API enum yet -- pre-existing, needs data service update

The contract test is supposed to enforce alignment with the upstream schema, but it now encodes an aspirational state rather than the actual contract. If `autom8_data` adds `"question"` the test would silently pass, but currently it masks a real contract mismatch.

**Blast Radius**: 1 file, masks a real integration issue (AD QUESTIONS table may fail in production when autom8_data validates frame_type)
**Fix Complexity**: Low -- add a comment documenting the drift, or split VALID_FRAME_TYPES into `VALID_FRAME_TYPES_CURRENT` and `VALID_FRAME_TYPES_PENDING` with explicit annotations
**ROI Score**: 6.5/10 -- low effort, prevents false confidence in contract alignment

---

### SM-003 (HYG-003): Asset sort tests use `str.find()` with prefix collision risk [P3]

**Category**: Test Fragility
**File**: `tests/unit/automation/workflows/test_insights_formatter.py`
**Lines**: 2031-2033, 2750-2752

**Evidence**:

```python
# Line 2031-2034 (test_compose_report_asset_table_sorted_by_spend_desc)
high_pos = asset_tbody.find("High")
mid_pos = asset_tbody.find("Mid")
low_pos = asset_tbody.find("Low")
assert high_pos < mid_pos < low_pos
```

`str.find("High")` would match "HighSpend", "Highway", or any CSS class containing "high". The test currently works because test data uses "High", "Mid", "Low" as names, but these are fragile anchors. The 10-row version at line 2672 is better, using NATO phonetic names ("Alpha", "Bravo"...) that are unlikely to collide with HTML content.

However, the test at line 2750 still uses `tbody.find("HighSpend")`, `tbody.find("LowSpend")`, `tbody.find("NoSpend")` which could match if these strings appear in currency-formatted values like "$500.00HighSpend" (unlikely but not impossible in edge cases).

**Blast Radius**: 2 test methods, no production impact
**Fix Complexity**: Low -- wrap names in `>name<` markers (as other tests do, e.g., `result.find(">Period<")`) or extract into a structural assertion helper
**ROI Score**: 5.0/10 -- test-only, low blast radius, but easy to fix

---

## New Findings

### SM-004: Duplicated TABLE_ORDER / TABLE_NAMES constant [P2]

**Category**: DRY Violation
**Files**:
- `src/autom8_asana/automation/workflows/insights_formatter.py` lines 34-47 (`TABLE_ORDER`)
- `src/autom8_asana/automation/workflows/insights_export.py` lines 73-86 (`TABLE_NAMES`)

**Evidence**: Two identical 12-element string lists with different names:

```python
# insights_formatter.py:34
TABLE_ORDER: list[str] = [
    "SUMMARY", "APPOINTMENTS", "LEADS",
    "LIFETIME RECONCILIATIONS", "T14 RECONCILIATIONS",
    "BY QUARTER", "BY MONTH", "BY WEEK",
    "AD QUESTIONS", "ASSET TABLE", "OFFER TABLE", "UNUSED ASSETS",
]

# insights_export.py:73
TABLE_NAMES: list[str] = [
    "SUMMARY", "APPOINTMENTS", "LEADS",
    "LIFETIME RECONCILIATIONS", "T14 RECONCILIATIONS",
    "BY QUARTER", "BY MONTH", "BY WEEK",
    "AD QUESTIONS", "ASSET TABLE", "OFFER TABLE", "UNUSED ASSETS",
]
```

Same values, different names (`TABLE_ORDER` vs `TABLE_NAMES`). If a table is added or renamed, both must be updated in sync -- a classic copy-paste maintenance trap.

**Blast Radius**: 2 files, ~28 lines, plus downstream `TOTAL_TABLE_COUNT = len(TABLE_NAMES)` in export
**Fix Complexity**: Low -- `insights_export.py` should import `TABLE_ORDER` from `insights_formatter.py` and alias as `TABLE_NAMES = TABLE_ORDER` (or just use one name)
**ROI Score**: 8.5/10 -- high impact (prevents silent drift), trivial fix

**Note**: Suggests missing shared constants surface -- flag for Architect Enforcer.

---

### SM-005: Repeated `import json` inside test functions [P3]

**Category**: Import Hygiene
**File**: `tests/unit/clients/data/test_contract_alignment.py`
**Lines**: 163, 240, 328, 391, 460, 532, 591

**Evidence**: `import json` appears 7 times inside individual test method bodies rather than once at module top:

```python
# Line 163 (inside test_request_body_structure)
import json
body_json = json.loads(body)

# ... repeated 6 more times in other test methods
```

`json` is a stdlib module with zero cost at module-level import. Burying it inside methods suggests copy-paste from a template without cleanup.

**Blast Radius**: 1 file, 7 occurrences, no runtime impact
**Fix Complexity**: Trivial -- move `import json` to module top (line 22 area), delete 7 inline imports
**ROI Score**: 5.5/10 -- trivial effort, improves readability

---

### SM-006: `_render_empty_section` and `_render_error_section` near-duplicate structure [P3]

**Category**: DRY Violation
**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: 691-741

**Evidence**: Both methods share ~80% identical structure (section shell with id, header, toggle, collapsed state, subtitle). The only difference is the inner content: one renders `<p class="empty">` and the other renders `<div class="error-box">`:

```python
def _render_empty_section(self, section: DataSection) -> str:  # line 691
    sid = _slugify(section.name)
    message = section.empty_message or "No data available"
    is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
    collapsed_class = "" if is_expanded else " collapsed"
    subtitle = _SECTION_SUBTITLES.get(section.name, "")
    subtitle_html = (...)
    return (
        f'<section id="{sid}" ...'   # identical shell
        f'<p class="empty">...'       # <-- only difference
        "</section>"
    )

def _render_error_section(self, section: DataSection) -> str:  # line 717
    sid = _slugify(section.name)
    error_text = section.error or "Unknown error"
    is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
    collapsed_class = "" if is_expanded else " collapsed"
    subtitle = _SECTION_SUBTITLES.get(section.name, "")
    subtitle_html = (...)
    return (
        f'<section id="{sid}" ...'    # identical shell
        f'<div class="error-box">...' # <-- only difference
        "</section>"
    )
```

**Blast Radius**: 2 methods (~50 lines), same file
**Fix Complexity**: Low -- extract a `_render_status_section(section, content_html)` helper
**ROI Score**: 5.0/10 -- moderate readability gain, low urgency

---

### SM-007: `_render_kpi_cards` complexity hotspot (140 lines, deep nesting) [P3]

**Category**: Complexity
**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: 413-553

**Evidence**: The `_render_kpi_cards` method is 140 lines with 6 sequential card-building blocks, each following an identical pattern:

1. Extract value from summary_row
2. isinstance check
3. Format value
4. Append card or "n/a"

The "Spend Trend" card (lines 508-551) has 4 levels of nesting. The "Best Week" card (lines 487-506) has 3 levels. Each card duplicates the `_kpi_card("...", "n/a", "Awaiting data")` fallback.

**Blast Radius**: 1 method, ~140 lines
**Fix Complexity**: Medium -- extract card builders into data-driven config or individual `_build_*_card()` methods
**ROI Score**: 4.5/10 -- no bugs, but challenging to extend (adding card 7 requires understanding all 6 patterns)

---

### SM-008: ResolutionContext mock boilerplate repeated 31 times [P4]

**Category**: DRY Violation
**File**: `tests/unit/automation/workflows/test_insights_export.py`
**Lines**: Throughout (31 occurrences of patching ResolutionContext)

**Evidence**: The same 5-line mock setup block appears in nearly every test:

```python
with patch(
    "autom8_asana.automation.workflows.insights_export.ResolutionContext"
) as mock_rc:
    mock_ctx = AsyncMock()
    mock_business = _make_mock_business()
    mock_ctx.business_async = AsyncMock(return_value=mock_business)
    mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)
```

This block is copy-pasted 31 times. A fixture or contextmanager helper would reduce it to a single reference.

**Blast Radius**: 1 file, ~155 lines of repeated boilerplate
**Fix Complexity**: Low -- extract a `@pytest.fixture` or `@contextmanager` helper
**ROI Score**: 4.0/10 -- test-only, no production impact, but would significantly reduce test file size

---

### SM-009: `compose_report` function complexity (134 lines) [P3]

**Category**: Complexity
**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: 758-891

**Evidence**: The `compose_report` function is 134 lines, handling 5 distinct responsibilities:
1. Build metadata dict (lines 760-769)
2. Build sections from table results with 4 branches per table (lines 771-868)
3. Special ASSET TABLE sort + column filter (lines 826-845)
4. Special period table column filter (lines 848-857)
5. Build footer (lines 870-891)

The section-building loop has a `continue` (line 820) inside a conditional, nested 3 levels deep.

**Blast Radius**: 1 function, 134 lines
**Fix Complexity**: Medium -- could extract `_build_section_from_result()` and `_build_footer()` helpers
**ROI Score**: 4.5/10 -- stable code, but difficult to extend (adding a new table-specific treatment requires understanding the full 134-line function)

---

### SM-010: `deps_response` is an undocumented alias [P4]

**Category**: Naming
**File**: `src/autom8_asana/api/health_models.py`
**Line**: 102

**Evidence**:

```python
# /health/deps (dependency probe) -- same signature as readiness_response
# with more granular checks.
deps_response = readiness_response
```

This creates a function alias without any behavioral difference. The comment explains the intent, but the alias adds a layer of indirection. Callers (health.py line 235) use `deps_response(...)` which is actually `readiness_response(...)`. This is not a bug, but it could confuse readers tracing the call chain.

**Blast Radius**: 2 files, 1 line
**Fix Complexity**: Trivial -- either inline `readiness_response` at the call site, or keep the alias with a more prominent comment
**ROI Score**: 2.0/10 -- cosmetic, intentional design

---

### SM-011: Duplicate default_params in handler config and workflow constants [P3]

**Category**: DRY Violation
**File**: `src/autom8_asana/lambda_handlers/insights_export.py`
**Lines**: 40-44

**Evidence**: The handler config duplicates values already defined as constants in the workflow module:

```python
# lambda_handlers/insights_export.py:40-44
_config = WorkflowHandlerConfig(
    ...
    default_params={
        "max_concurrency": 5,                    # == DEFAULT_MAX_CONCURRENCY
        "attachment_pattern": "insights_export_*.html",  # == DEFAULT_ATTACHMENT_PATTERN
        "row_limits": {"APPOINTMENTS": 100, "LEADS": 100, "ASSET TABLE": 150},  # == DEFAULT_ROW_LIMITS
    },
    ...
)
```

These are literal copies of `DEFAULT_MAX_CONCURRENCY`, `DEFAULT_ATTACHMENT_PATTERN`, and `DEFAULT_ROW_LIMITS` from `insights_export.py`. If the workflow constants change, the handler defaults would silently diverge.

**Blast Radius**: 1 file, 3 values
**Fix Complexity**: Trivial -- import and reference the constants
**ROI Score**: 6.0/10 -- prevents silent divergence, trivial fix

---

### SM-012: Docstring says "markdown" but workflow produces HTML [P4]

**Category**: Naming / Documentation Drift
**Files**:
- `src/autom8_asana/automation/workflows/insights_export.py` line 92
- `tests/unit/automation/workflows/test_insights_export.py` line 853

**Evidence**:

```python
# insights_export.py:92
class InsightsExportWorkflow(AttachmentReplacementMixin, WorkflowAction):
    """Daily insights export markdown report for Offer tasks.

# test_insights_export.py:853
    async def test_upload_called_with_correct_params(self) -> None:
        """Upload creates .md file with correct content type."""
```

The docstring says "markdown report" but the workflow produces HTML reports (`.html` extension, `text/html` content type). This is a leftover from the pre-WS-G migration when the formatter produced markdown.

**Blast Radius**: 2 files, cosmetic only
**Fix Complexity**: Trivial -- update docstrings
**ROI Score**: 2.5/10 -- cosmetic, but could mislead new developers

---

## Priority Queue (by ROI)

| Rank | ID | ROI | Category | Effort | Summary |
|------|----|-----|----------|--------|---------|
| 1 | SM-004 | 8.5 | DRY | Low | Duplicate TABLE_ORDER / TABLE_NAMES constant |
| 2 | SM-001 | 7.0 | Type Safety | Low | 5 type:ignore in KPI card rendering |
| 3 | SM-002 | 6.5 | Contract | Low | VALID_FRAME_TYPES includes pending "question" |
| 4 | SM-011 | 6.0 | DRY | Trivial | Duplicate default_params in handler config |
| 5 | SM-005 | 5.5 | Imports | Trivial | Repeated `import json` in test methods |
| 6 | SM-006 | 5.0 | DRY | Low | Near-duplicate empty/error section renderers |
| 7 | SM-003 | 5.0 | Tests | Low | Fragile str.find() in asset sort tests |
| 8 | SM-009 | 4.5 | Complexity | Medium | compose_report 134 lines, 5 responsibilities |
| 9 | SM-007 | 4.5 | Complexity | Medium | _render_kpi_cards 140 lines, deep nesting |
| 10 | SM-008 | 4.0 | DRY (Tests) | Low | ResolutionContext mock boilerplate x31 |
| 11 | SM-012 | 2.5 | Naming | Trivial | Docstring says "markdown", produces HTML |
| 12 | SM-010 | 2.0 | Naming | Trivial | deps_response undocumented alias |

---

## Boundary Concerns for Architect Enforcer

1. **SM-004 (TABLE_ORDER duplication)**: Suggests missing shared constants module. The formatter and export workflow share the same domain vocabulary but define it independently. Architect Enforcer should evaluate whether a `insights_constants.py` or similar shared surface is warranted.

2. **SM-001 (type:ignore pattern)**: The underlying issue is a type-narrowing gap in list comprehensions with `isinstance` guards. A reusable `_extract_numeric(rows, key)` helper could establish a pattern for similar KPI extraction across the codebase.

3. **SM-007 + SM-009 (complexity hotspots)**: Both `_render_kpi_cards` and `compose_report` are stable and well-tested, but they resist extension. If new KPI cards or table-specific treatments are planned, Architect Enforcer should consider decomposition.

---

## Items Not Flagged (Intentional Patterns)

- **`_CSS` and `_JS` inline strings** (~300 lines of CSS, ~150 lines of JS): Intentional design per "self-contained HTML" requirement. No external resources allowed.
- **Module-level `_renderer = HtmlRenderer()` singleton** (line 755): Intentional for performance -- stateless renderer, no side effects. Not a god object.
- **`# BROAD-CATCH: boundary` comments** on except blocks: Documented intentional pattern for error isolation at boundary points. Each has a comment explaining the reason.
- **`global _cache_ready`** in health.py: Intentional module-level state for ECS health check signaling. Well-documented, tested with state transitions.
- **`health_models.deps_response = readiness_response`** alias: Flagged as SM-010 at P4 but is arguably intentional -- kept as low-priority cosmetic note.

---

## Attestation

| File | Read | Analyzed |
|------|------|----------|
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Yes | Yes |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Yes (chunked) | Yes |
| `tests/unit/clients/data/test_contract_alignment.py` | Yes | Yes |
| `src/autom8_asana/api/routes/health.py` | Yes | Yes |
| `tests/api/test_health.py` | Yes | Yes |
| `src/autom8_asana/api/health_models.py` | Yes | Yes |
| `src/autom8_asana/automation/workflows/insights_export.py` | Yes | Yes |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Yes | Yes |
| `tests/unit/automation/workflows/test_insights_export.py` | Yes | Yes |
| `tests/unit/lambda_handlers/test_insights_export.py` | Yes | Yes |
