# Insights Export -- Workstream Decomposition

**Date**: 2026-02-20
**Context**: `INSIGHTS_EXPORT-CANONICAL-2026-02-20.md`
**Smoke test**: `INSIGHTS_EXPORT-SMOKETEST-2026-02-20.md`

---

## Dependency Graph

```
WS-A (reconciliation UX)  ----\
WS-B (row limits)          -----+--> WS-F (smoke test)
WS-C (display polish)     -----/         |
WS-D (ASSET TABLE caps)  -----/          v
WS-E (unit test gaps)                  DONE
```

WS-A through WS-D are independent of each other. WS-E is independent. WS-F depends on WS-A through WS-D being merged.

---

## WS-A: Reconciliation Table UX (H-01)

**Priority**: P0
**Est**: 0.5d
**Blocker for**: WS-F (smoke test must see clean reconciliation display)

### Scope

Tables 4-5 (LIFETIME RECONCILIATIONS, T14 RECONCILIATIONS) currently render rows with null values for payment-related columns (`collected`, `num_invoices`, `variance`) because Stripe REC-8 has not shipped. A user seeing a table full of dashes gets no signal about whether data is missing or the feature is pending.

### Approach

Add a conditional check in `compose_report()`: if ALL payment-indicator columns are null/None across all rows of a reconciliation table, replace the table with a styled info message: "Payment reconciliation data is pending Stripe integration. Spend and budget data is available below."

This is display-layer only. Do not change the API call or data fetch. The reconciliation endpoint should still be called (it returns spend/budget data that IS valid).

### Files to Touch

| File | Change |
|------|--------|
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Add `_is_payment_data_pending()` helper; modify section building in `compose_report()` to emit info-message DataSection when pending |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Add tests: recon table with all-null payment cols -> info message; recon table with some data -> normal render |

### Acceptance Criteria

1. When reconciliation table rows have ALL payment columns (`collected`, `num_invoices`, `variance`, `expected_collection`, `expected_variance`) as None: render as info-styled section with pending message instead of data table
2. When reconciliation table rows have ANY non-null payment column: render normally as data table
3. Spend and budget columns in reconciliation data still display when present
4. Both LIFETIME and T14 RECONCILIATIONS affected independently
5. Tests pass: `pytest tests/unit/automation/workflows/test_insights_formatter.py -x`

### Implementation Notes

- The info message should use a new `_render_info_section()` method on HtmlRenderer (or reuse `_render_empty_section()` with a distinct CSS class)
- Payment indicator columns: `collected`, `num_invoices`, `variance`, `expected_collection`, `expected_variance`
- Check must be on the actual data rows, not on column presence in schema

---

## WS-B: Raise APPOINTMENTS/LEADS Row Limits (H-06)

**Priority**: P1
**Est**: 0.25d
**Blocker for**: WS-F

### Scope

`DEFAULT_ROW_LIMITS` and `_config.default_params["row_limits"]` hard-code APPOINTMENTS at 100 and LEADS at 100. The server supports up to 500. High-volume accounts get silently truncated.

### Files to Touch

| File | Line(s) | Change |
|------|---------|--------|
| `src/autom8_asana/automation/workflows/insights_export.py` | 63-66 | Change `DEFAULT_ROW_LIMITS` values: APPOINTMENTS -> 250, LEADS -> 250 |
| `src/autom8_asana/lambda_handlers/insights_export.py` | 43 | Update `row_limits` in `default_params` to match: `{"APPOINTMENTS": 250, "LEADS": 250}` |
| `tests/unit/automation/workflows/test_insights_export.py` | grep for `100` in row_limit assertions | Update expected values to 250 |
| `tests/unit/lambda_handlers/test_insights_export.py` | grep for `100` in default_params assertions | Update expected values to 250 |

### Acceptance Criteria

1. `DEFAULT_ROW_LIMITS` = `{"APPOINTMENTS": 250, "LEADS": 250}`
2. Lambda handler `default_params["row_limits"]` matches
3. All existing tests pass with updated values
4. `pytest tests/unit/automation/workflows/test_insights_export.py tests/unit/lambda_handlers/test_insights_export.py -x`

---

## WS-C: Display Label Overrides (H-10)

**Priority**: P2
**Est**: 0.1d
**Independent**: no cross-dependencies

### Scope

`_to_title_case()` converts `n_distinct_ads` to "N Distinct Ads". Should be "Distinct Ads" or a custom label. Add a display label override dict so known fields render with human-chosen names.

### Files to Touch

| File | Change |
|------|--------|
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Add `_DISPLAY_LABELS: dict[str, str]` near `_FIELD_FORMAT`; modify `_to_title_case()` to check override dict first |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Add test: `n_distinct_ads` -> override label; other fields -> unchanged |

### Suggested Override Dict

```python
_DISPLAY_LABELS: dict[str, str] = {
    "n_distinct_ads": "Distinct Ads",
    "cpl": "Cost Per Lead",
    "cps": "Cost Per Show",
    "ecps": "Expected Cost Per Show",
    "cpc": "Cost Per Click",
    "ltv": "Lifetime Value",
    "ctr": "Click-Through Rate",
    "lctr": "Lead Click-Through Rate",
    "nsr_ncr": "NSR/NCR Ratio",
    "lp20m": "Leads Per 20K",
    "sp20m": "Shows Per 20K",
    "esp20m": "Expected Shows Per 20K",
    "ltv20m": "LTV Per 20K",
    "roas": "ROAS",
    "ns_rate": "No-Show Rate",
    "nc_rate": "No-Close Rate",
    "variance_pct": "Variance %",
    "imp": "Impressions",
}
```

### Acceptance Criteria

1. `_to_title_case("n_distinct_ads")` returns the override label
2. `_to_title_case("spend")` still returns "Spend" (no override needed)
3. Override dict is easy to extend for future fields
4. Tests pass

---

## WS-D: ASSET TABLE Row Cap + Transcript Overflow (H-09 + H-07)

**Priority**: P2
**Est**: 0.5d
**Independent**: no cross-dependencies

### Scope

Two related ASSET TABLE issues bundled because they both affect the same table rendering:

1. **H-09**: ASSET TABLE can return 300+ rows (T30 unbounded). Add a row limit of 150, sorted by spend descending.
2. **H-07**: `transcript` column contains full video transcripts that overflow table cells. Add CSS max-height + overflow clipping for long text cells.

### Files to Touch

| File | Change |
|------|--------|
| `src/autom8_asana/automation/workflows/insights_export.py` | Add `"ASSET TABLE": 150` to `DEFAULT_ROW_LIMITS` |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Add `"ASSET TABLE": 150` to `default_params["row_limits"]` |
| `src/autom8_asana/automation/workflows/insights_export.py` | In `_fetch_all_tables()`: sort ASSET TABLE result by spend desc before passing to table_map (or: sort in compose_report) |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Add CSS rule: `.table-section td { max-height: 6em; overflow: hidden; text-overflow: ellipsis; }` or column-specific `.col-transcript` class |
| `tests/unit/automation/workflows/test_insights_export.py` | Test: ASSET TABLE with 200 rows -> truncated to 150, sorted by spend desc |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Test: long transcript cell renders with truncation CSS class |

### Design Decision: Where to Sort

Sort in `compose_report()` (formatter layer), not in `_fetch_all_tables()` (workflow layer). Rationale: the formatter already handles row_limits truncation. Sorting before truncation ensures the most-spend assets survive the cut.

Add a `sort_key` concept to `DataSection` or handle it in the compose_report section-building loop specifically for ASSET TABLE. Simplest: sort `result.data` by `spend` (desc, nulls last) inline in the `compose_report()` section-building loop when `table_name == "ASSET TABLE"`.

### Acceptance Criteria

1. ASSET TABLE limited to 150 rows in output
2. Rows sorted by `spend` descending (highest spend assets shown)
3. Truncation note displayed: "Showing 150 of N rows"
4. Transcript column content clipped at ~6em height with CSS overflow hidden
5. UNUSED ASSETS derivation still runs on FULL asset data (not truncated)
6. Tests pass

### Critical Note on UNUSED ASSETS

`row_limits` truncation happens in `compose_report()` (display layer). UNUSED ASSETS derivation happens in `_fetch_all_tables()` (data layer). The sort+cap must NOT affect the UNUSED ASSETS filter input. Verify that the `row_limits` config only applies at render time via `compose_report()`, not at fetch time.

---

## WS-E: Unit Test Coverage Gaps

**Priority**: P1
**Est**: 0.5d
**Independent**: can be done in parallel with WS-A through WS-D

### Scope

Three specific test gaps identified in the existing test suite.

### Gap 1: 12-Table Count Assertion

**File**: `tests/unit/automation/workflows/test_insights_export.py`
**Test**: Verify that `_fetch_all_tables()` returns exactly 12 entries (matching `TOTAL_TABLE_COUNT`).

```python
async def test_fetch_all_tables_returns_twelve_tables(self):
    """All 12 TABLE_NAMES present in _fetch_all_tables() result."""
    table_map = await workflow._fetch_all_tables(phone, vertical, row_limits, offer_gid)
    assert len(table_map) == TOTAL_TABLE_COUNT
    assert set(table_map.keys()) == set(TABLE_NAMES)
```

### Gap 2: Reconciliation Fetch Path

**File**: `tests/unit/automation/workflows/test_insights_export.py`
**Test**: Verify that `_fetch_table()` with `method="reconciliation"` calls `get_reconciliation_async()` with correct args.

```python
async def test_fetch_table_reconciliation_calls_correct_method(self):
    """method='reconciliation' dispatches to get_reconciliation_async."""
    result = await workflow._fetch_table(
        "LIFETIME RECONCILIATIONS", offer_gid, phone, vertical,
        method="reconciliation",
    )
    mock_data_client.get_reconciliation_async.assert_called_once_with(
        phone, vertical, period=None, window_days=None,
    )
```

### Gap 3: window_days Threading

**File**: `tests/unit/automation/workflows/test_insights_export.py`
**Test**: Verify that `window_days=14` is passed through to `get_reconciliation_async()`.

```python
async def test_fetch_table_reconciliation_window_days(self):
    """window_days parameter threads to get_reconciliation_async."""
    result = await workflow._fetch_table(
        "T14 RECONCILIATIONS", offer_gid, phone, vertical,
        method="reconciliation", window_days=14,
    )
    mock_data_client.get_reconciliation_async.assert_called_once_with(
        phone, vertical, period=None, window_days=14,
    )
```

### Acceptance Criteria

1. Three new tests added and passing
2. Existing tests unbroken: `pytest tests/unit/automation/workflows/test_insights_export.py -x`
3. Test names follow existing file conventions (check existing test class structure first)

---

## WS-F: Production Smoke Test

**Priority**: P0 (gate)
**Est**: 0.5d
**Depends on**: WS-A, WS-B, WS-D merged
**Playbook**: `INSIGHTS_EXPORT-SMOKETEST-2026-02-20.md`

### Scope

Run the full pipeline against offer `1211872268838349` using the Lambda handler entry point. Verify all 12 tables render correctly in the output HTML. Upload to Asana and visually inspect.

### Pre-conditions

- All WS-A through WS-D changes committed
- All unit tests green: `pytest tests/unit/ -x`
- Environment configured per smoke test playbook

### Acceptance Criteria

1. Handler returns `statusCode: 200` with `status: "completed"`
2. `total_tables_succeeded >= 10` (reconciliation tables may show pending indicator)
3. HTML output contains all 12 section IDs
4. SUMMARY section has exactly 1 row
5. AD QUESTIONS section shows question-level columns (question_key, priority), NOT offer-level
6. Currency fields display as `$X,XXX.XX`
7. Rate fields display as `X.XX%`
8. Period tables have period columns ordered left
9. Reconciliation tables show either data or clean pending-data indicator
10. ASSET TABLE limited to 150 rows with truncation note if applicable
11. APPOINTMENTS limited to 250 rows
12. HTML uploaded to Asana offer task successfully

---

## Execution Order Recommendation

**Parallel batch 1** (independent, can run simultaneously):
- WS-B (row limits, 0.25d, smallest)
- WS-C (display labels, 0.1d, smallest)
- WS-E (unit tests, 0.5d)

**Parallel batch 2** (after batch 1 or independently):
- WS-A (reconciliation UX, 0.5d)
- WS-D (ASSET TABLE caps + transcript, 0.5d)

**Sequential gate**:
- WS-F (smoke test, 0.5d) -- after all of WS-A through WS-D

**Total estimated**: ~1.5d of work, compressible to ~1d with parallelism.
