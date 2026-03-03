# Export Flow Structural Review

## Executive Summary

The insights export pipeline is functionally correct and has solid error isolation, concurrency control, and upload-first safety guarantees. However, it has accumulated structural debt across three areas: (1) the `_fetch_table` method is a parameter-routing monolith that encodes 12 table configurations imperatively rather than declaratively, (2) the `compose_report` adapter layer in `insights_formatter.py` mixes display-column filtering, row-limit slicing, sort logic, and reconciliation-pending detection in a single 80-line function, and (3) the test suite has a pervasive ResolutionContext mock-setup boilerplate duplicated across 31+ methods that inflates test code by ~400 lines. There are two P1 findings (stale docstring, cache keying collision risk), six P2 findings, and nine P3 findings.

---

## Findings Table

| ID | Severity | Category | File | Summary |
|----|----------|----------|------|---------|
| F-01 | P1 | DEFECT | `insights_export.py:90-96` | Docstring says "10 tables" but implementation has 12 |
| F-02 | P1 | ROBUSTNESS | `insights_export.py:112-114` | Business cache keyed by offer_gid, not by business_gid |
| F-03 | P2 | STRUCTURAL | `insights_export.py:691-821` | `_fetch_all_tables` + `_fetch_table` is a routing monolith |
| F-04 | P2 | STRUCTURAL | `insights_formatter.py:798-859` | `compose_report` adapter mixes 5 concerns |
| F-05 | P2 | CONSISTENCY | `insights_export.py:569` | Double UTF-8 encode (redundant allocation) |
| F-06 | P2 | MAINTAINABILITY | `insights_export.py:52-53` | Hardcoded OFFER_PROJECT_GID instead of Offer.PRIMARY_PROJECT_GID |
| F-07 | P2 | TEST GAP | `test_insights_export.py` | ResolutionContext mock boilerplate (31x ~6 lines each) |
| F-08 | P2 | ROBUSTNESS | `insights_export.py:883-906` | Reconciliation phone filter mutates response.data in-place |
| F-09 | P3 | CONSISTENCY | `insights_export.py:1-6` | Module docstring says "10 tables", should say 12 |
| F-10 | P3 | ROBUSTNESS | `insights_export.py:959-972` | `_sanitize_business_name` produces empty string for all-special-char names |
| F-11 | P3 | PERFORMANCE | `insights_formatter.py:1109-1121` | `_column_align_class` scans all rows; called once per cell |
| F-12 | P3 | MAINTAINABILITY | `insights_formatter.py:1144-1477` | Inline CSS+JS is ~350 lines; hard to maintain/test |
| F-13 | P3 | CONSISTENCY | `insights_export.py:246-254` | Business cache hit math is wrong when cache stores None |
| F-14 | P3 | TEST GAP | `test_insights_formatter.py` | No test for `_mask_pii_rows` function |
| F-15 | P3 | TEST GAP | `test_insights_export.py` | No test for reconciliation phone filtering (lines 883-906) |
| F-16 | P3 | CONSISTENCY | `insights_export.py:826-837` | `_fetch_table` has `factory: str | None` but defaults to `"base"` |
| F-17 | P3 | MAINTAINABILITY | `insights_formatter.py:746` | Module-level singleton `_renderer` (no reset hook for tests) |

---

## Detailed Findings

### F-01: Stale Docstring -- "10 tables" in class/module docs (P1 DEFECT)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 1-6 (module docstring), 82-101 (class docstring)

The module docstring says "fetches 10 tables" and the class docstring says "Fetch 10 tables concurrently". The implementation actually dispatches 12 concurrent calls. This was not updated when LIFETIME RECONCILIATIONS, T14 RECONCILIATIONS, and UNUSED ASSETS were added. The discrepancy causes confusion for any engineer reading the module-level documentation first.

**Why P1**: Incorrect documentation at the entry-point level leads engineers to wrong assumptions about the call structure. The comment "Step 3b" referencing a 10-table model could mislead debugging.

**Fix**: Update all docstrings and comments referencing table counts to 12. This is a 5-minute edit across 3-4 locations.

---

### F-02: Business Cache Keyed by offer_gid, Not business_gid (P1 ROBUSTNESS)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 112-114, 646-688

The dedup cache (`_business_cache`) is keyed by `offer_gid`, not by the resolved `business_gid`. The stated purpose (per AT3-001) is to "eliminate redundant Business fetches across offers." But since each offer has a unique GID, the cache only helps if the same offer_gid is processed twice within a single workflow run -- which never happens (the enumeration deduplicates by GID).

If two offers share the same parent Business (e.g., offer A and offer B both under Business X), the cache misses on both because it is keyed by offer_gid, not by the Business resolution target. The cache provides zero dedup benefit in the primary use case of multiple offers under one business.

**Why P1**: The cache's stated purpose (AT3-001: eliminate redundant Business fetches) is not achieved. The observability log line `cache_hits` and `api_calls_saved` reports metrics that are always zero, creating false confidence in the observability data.

**Fix**: Key the cache by the Business GID (or by the offer's parent chain fingerprint, e.g., `offer_task.parent.gid`). After resolving a business, store it keyed by a stable identifier that is shared across sibling offers.

---

### F-03: `_fetch_all_tables` + `_fetch_table` Is a Routing Monolith (P2 STRUCTURAL)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 691-953

`_fetch_all_tables` manually constructs 12 `_fetch_table` calls with different parameter combinations. `_fetch_table` then has a 4-branch if/elif chain to route to the correct DataServiceClient method based on the `method` parameter. Adding a 13th table requires editing both functions.

This is a classic "data-driven problem solved with imperative code" smell. The 12 table definitions could be declared as a data structure (e.g., a list of `TableSpec` dataclasses), and a single loop could iterate them. This would:

1. Eliminate the 130-line `_fetch_all_tables` method entirely
2. Make `_fetch_table` a simple dispatcher over a known enum
3. Make table additions require only a new entry in the data structure

**Why P2**: Not a defect, but the current structure makes every table addition a 2-method edit with high risk of parameter misalignment. The 12-entry gather is hard to review for completeness.

**Fix**: Extract a `TableSpec` frozen dataclass with fields: `name`, `method`, `factory`, `period`, `days`, `limit`, `exclude_appointments`, `window_days`, `include_unused`. Define `TABLE_SPECS: list[TableSpec]` as a module constant. Replace `_fetch_all_tables` with a loop over `TABLE_SPECS`.

---

### F-04: `compose_report` Adapter Mixes Five Concerns (P2 STRUCTURAL)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: 749-882

The `compose_report` function handles:
1. Table result validation (missing/error/empty branching)
2. Reconciliation pending detection
3. ASSET TABLE sort + column exclusion
4. Row limit application + truncation detection
5. Period table column filtering

These five concerns are interleaved in a single 80-line loop body. Adding a new table-specific behavior (e.g., a new table type with its own column filter) requires modifying the same dense loop.

**Why P2**: Each concern is independently testable but is woven into the adapter loop, making it harder to add new table-specific behaviors without increasing the cyclomatic complexity.

**Fix**: Extract per-table preparation into a `_prepare_display_rows(table_name, rows, row_limits) -> (display_rows, full_rows, truncated, total_rows)` function. Move ASSET TABLE sort/filter and period column filter into this function. Keep `compose_report` as a clean iteration over TABLE_ORDER with delegation.

---

### F-05: Double UTF-8 Encode (P2 CONSISTENCY)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 562, 569

```python
file=report_content.encode("utf-8"),  # line 562
...
size_bytes=len(report_content.encode("utf-8")),  # line 569
```

The report content is encoded to UTF-8 twice: once for the upload call (line 562), then again for the log message (line 569). The same pattern appears in the dry-run path (line 588). This creates a redundant ~100KB+ allocation for the sole purpose of computing a log metric.

**Why P2**: Wastes memory proportional to report size. For 12 tables with 100+ rows each, the report can be 200KB+, and encoding it twice is wasteful.

**Fix**: Encode once, store in a local variable, use it for both the upload and the size metric:
```python
report_bytes = report_content.encode("utf-8")
await self._attachments_client.upload_async(..., file=report_bytes, ...)
logger.info(..., size_bytes=len(report_bytes), ...)
```

---

### F-06: Hardcoded OFFER_PROJECT_GID (P2 MAINTAINABILITY)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 52-53

```python
# Offer project GID (canonical source: Offer.PRIMARY_PROJECT_GID)
OFFER_PROJECT_GID = "1143843662099250"
```

The comment acknowledges that `Offer.PRIMARY_PROJECT_GID` is the canonical source, but the value is duplicated as a string literal. If the canonical source changes, this file will be out of sync. The `Offer` class is available at runtime (not just TYPE_CHECKING), so there is no circular import barrier to using it directly.

**Why P2**: Violates DRY with an acknowledged canonical source. A regression risk when the GID mapping changes.

**Fix**: Import `Offer` from `autom8_asana.models.business.offer` and use `Offer.PRIMARY_PROJECT_GID`. If the import introduces a startup-time concern, use a deferred import at the call site.

---

### F-07: ResolutionContext Mock Boilerplate Duplicated 31+ Times (P2 TEST GAP / MAINTAINABILITY)

**File**: `tests/unit/automation/workflows/test_insights_export.py`
**Lines**: Throughout (361-372 pattern repeated)

The following 6-line mock setup block is copy-pasted across 31+ test methods:

```python
with patch("...ResolutionContext") as mock_rc:
    mock_ctx = AsyncMock()
    mock_business = _make_mock_business()
    mock_ctx.business_async = AsyncMock(return_value=mock_business)
    mock_rc.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_rc.return_value.__aexit__ = AsyncMock(return_value=False)
```

This adds ~200 lines of pure boilerplate. The test file itself documents this as a known issue (SM-008) but defers resolution.

**Why P2**: The boilerplate makes tests harder to read and increases the chance of an inconsistent mock setup across test methods. Any change to the ResolutionContext interface requires updating 31 sites.

**Fix**: Extract a `@pytest.fixture` that provides a pre-configured `ResolutionContext` patch. The existing `_force_fallback` fixture shows the pattern. A `_mock_resolution` fixture could yield the mock_business for per-test customization.

---

### F-08: Reconciliation Phone Filter Mutates response.data In-Place (P2 ROBUSTNESS)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 883-906

```python
response.data = [
    r for r in response.data
    if r.get("office_phone") == office_phone
]
```

This mutates the `InsightsResponse.data` list in-place. `InsightsResponse` is a Pydantic model, and while Pydantic v2 allows attribute mutation by default (no `frozen=True`), this violates the general principle that API responses should be treated as immutable. If any upstream code retains a reference to the response object (e.g., for caching), the filtered data would propagate unexpectedly.

**Why P2**: The DataServiceClient has a cache layer (`_cache_response`). If a cached response is filtered here and then reused for a different offer with a different phone, the cached data would be silently wrong. The current call path creates a new response per request, so this is not an active bug, but it is a latent one that will bite if caching behavior changes.

**Fix**: Assign to a local variable instead of mutating `response.data`:
```python
filtered_data = [r for r in response.data if r.get("office_phone") == office_phone]
# Use filtered_data below, not response.data
```

---

### F-09: Module Docstring Says "10 tables" (P3 CONSISTENCY)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 1-6

Same as F-01 but for the module-level docstring specifically. Lower severity since the class docstring is the primary entry point.

**Fix**: Update "fetches 10 tables" to "fetches 12 tables".

---

### F-10: `_sanitize_business_name` Produces Empty String for All-Special-Char Names (P3 ROBUSTNESS)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 959-972

For a business name like `"!@#$%^&*()"`, the function returns `""`, which produces a filename like `insights_export__20260301.html` (double underscore, no business identifier). This is cosmetically wrong but unlikely in production since business names in Asana always have alphanumeric characters.

The test `TestAdversarialSanitizeBusinessName.test_all_special_chars` documents this behavior but does not flag it as unexpected.

**Fix**: Add a fallback: `return sanitized or "unknown"`.

---

### F-11: `_column_align_class` Called Per-Cell, Scans All Rows (P3 PERFORMANCE)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: 1109-1121, 637

`_column_align_class(rows, col)` is called inside the inner loop of `_render_table_section` (line 637), once per cell. For a table with 100 rows and 20 columns, this is 2000 calls, each scanning up to 100 rows to find the first non-None value. Total: up to 200,000 row lookups for a single table.

The result is deterministic per column (not per cell), so it should be computed once per column outside the row loop.

**Why P3**: In practice the first row usually has a value, so the scan terminates quickly. But it is still a quadratic pattern that is easy to fix.

**Fix**: Compute `align_by_col = {col: _column_align_class(rows, col) for col in columns}` before the row loop. Use `align_by_col[col]` inside the loop.

---

### F-12: Inline CSS+JS is 350 Lines of Unmaintainable String Literals (P3 MAINTAINABILITY)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Lines**: 1144-1477

The `_CSS` and `_JS` constants are 350+ lines of raw strings embedded in a Python module. They have no syntax highlighting, no linting, no minification, and no automated testing. Any typo in the CSS/JS is invisible until the report is opened in a browser.

**Why P3**: The design decision (self-contained HTML, no external deps) is sound. But the maintenance burden of editing CSS/JS inside a Python string is real. This is an acceptable tradeoff for now but should not grow further.

**Fix (future)**: Move CSS and JS to `.css` and `.js` files in a `templates/` directory. Read them at module import time via `importlib.resources` or `pathlib.Path`. This preserves the self-contained HTML output while giving maintainers proper syntax highlighting and linting.

---

### F-13: Business Cache Hit Math Is Wrong When Cache Stores None (P3 CONSISTENCY)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 246-254

```python
"cache_hits": len(offers) - len(self._business_cache),
"api_calls_saved": len(offers) - len(self._business_cache),
```

The formula `len(offers) - len(self._business_cache)` assumes every cache entry was a unique business lookup. But the cache also stores `None` for offers whose resolution failed (line 661: `self._business_cache[offer_gid] = None`). A None entry represents a failed lookup, not a successful cache-hit-for-a-different-offer. This inflates the "API calls saved" count.

Combined with F-02 (cache keyed by offer_gid), `len(self._business_cache)` always equals `len(offers)`, so `cache_hits` is always 0. The metric is doubly misleading.

**Why P3**: Observability metric is always wrong, but it is purely informational and does not affect behavior.

**Fix**: Track actual cache hits with a counter incremented at the `cache_hit` log line (line 650), rather than deriving from set sizes.

---

### F-14: No Test for `_mask_pii_rows` (P3 TEST GAP)

**File**: `tests/unit/automation/workflows/test_insights_formatter.py`

The `_mask_pii_rows` function (lines 1043-1059 in `insights_formatter.py`) handles PII masking for the Copy TSV JSON data embedded in each table section. It has a fast-path optimization (check first row only), a shallow-copy pattern, and specific column targeting. None of these behaviors are directly tested.

The function is exercised indirectly through `compose_report` integration tests, but edge cases (no PII columns present, mixed PII presence across rows, non-string values in PII columns) are not covered.

**Fix**: Add a `TestMaskPiiRows` class with 4-5 focused tests: no-op when no PII columns, masks phone columns, preserves non-PII columns, handles non-string values in PII columns, handles empty rows.

---

### F-15: No Test for Reconciliation Phone Filtering (P3 TEST GAP)

**File**: `tests/unit/automation/workflows/test_insights_export.py`

The defensive phone filter in `_fetch_table` (lines 883-906) that filters reconciliation data to only rows matching the queried phone is not tested. This is a production-critical path: the API may return all businesses for the vertical, and without filtering, the reconciliation table would show data for unrelated businesses.

**Fix**: Add a test that mocks `get_reconciliation_async` to return multi-phone data and verifies that only the queried phone's rows survive.

---

### F-16: `_fetch_table` Has `factory: str | None` but Always Defaults to `"base"` (P3 CONSISTENCY)

**File**: `src/autom8_asana/automation/workflows/insights_export.py`
**Lines**: 826-837

The `factory` parameter is typed as `str | None` but the call site always provides a value or defaults to `"base"` at usage (line 910). The `None` case never occurs in practice. The type annotation is misleading.

**Fix**: Change to `factory: str = "base"` and remove the `or "base"` fallback at line 910.

---

### F-17: Module-Level `_renderer` Singleton (P3 MAINTAINABILITY)

**File**: `src/autom8_asana/automation/workflows/insights_formatter.py`
**Line**: 746

```python
_renderer = HtmlRenderer()
```

This module-level singleton is created at import time. It has no state (HtmlRenderer is stateless), so it is functionally harmless. However, it does not follow the project's `SystemContext.register_reset()` pattern for singletons, and it cannot be swapped in tests.

**Why P3**: HtmlRenderer is stateless and pure, so this is a non-issue in practice. It only becomes relevant if HtmlRenderer gains state (e.g., template caching).

**Fix**: No immediate action needed. If HtmlRenderer gains state in the future, move to lazy initialization with a reset hook.

---

## Recommended Sprint Plan

### Sprint A: Quick Wins (1-2 hours)

| ID | Finding | Effort |
|----|---------|--------|
| F-01 | Update all "10 tables" docstrings to "12 tables" | 10 min |
| F-09 | Same as F-01 (module docstring) | Included above |
| F-05 | Fix double UTF-8 encode | 10 min |
| F-10 | Add `or "unknown"` fallback in `_sanitize_business_name` | 5 min |
| F-16 | Fix `factory` parameter type annotation | 5 min |
| F-13 | Fix cache hit math (add explicit counter) | 20 min |
| F-06 | Replace hardcoded GID with `Offer.PRIMARY_PROJECT_GID` | 15 min |

### Sprint B: Robustness Fixes (2-3 hours)

| ID | Finding | Effort |
|----|---------|--------|
| F-02 | Re-key business cache by business_gid (or parent chain) | 45 min |
| F-08 | Stop mutating response.data in reconciliation filter | 15 min |
| F-15 | Add reconciliation phone filtering test | 30 min |
| F-14 | Add `_mask_pii_rows` tests | 30 min |

### Sprint C: Structural Improvements (4-6 hours)

| ID | Finding | Effort |
|----|---------|--------|
| F-03 | Extract `TableSpec` data structure for declarative table definitions | 2-3 hours |
| F-04 | Extract `_prepare_display_rows` from `compose_report` | 1-2 hours |
| F-07 | Extract shared `_mock_resolution` fixture in export tests | 1 hour |

### Sprint D: Future Work (backlog, not urgent)

| ID | Finding | Effort |
|----|---------|--------|
| F-11 | Cache `_column_align_class` per column (not per cell) | 30 min |
| F-12 | Move CSS/JS to external files with `importlib.resources` | 2 hours |
| F-17 | Add reset hook for `_renderer` if it gains state | 15 min |

---

## Files Referenced

- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/insights_export.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/workflows/insights_formatter.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/insights.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/models.py`
- `/Users/tomtenuta/Code/autom8y-asana/tests/unit/automation/workflows/test_insights_export.py`
- `/Users/tomtenuta/Code/autom8y-asana/tests/unit/automation/workflows/test_insights_formatter.py`
- `/Users/tomtenuta/Code/autom8y-asana/tests/integration/test_schema_contract.py`
