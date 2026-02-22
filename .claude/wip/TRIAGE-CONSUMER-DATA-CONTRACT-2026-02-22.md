# Consumer Data Contract Triage Audit

**Date**: 2026-02-22
**Scope**: autom8y-asana insights export consumer alignment with autom8y-data upstream
**Trigger**: 3 upstream sessions shipped (Consumer Contract Remediation, Cross-Fact Dimension Scoping Fix, include_unused param hotfix)

---

## Summary

The autom8y-data insights service underwent significant remediation across three sessions.
This audit tracks all consumer-side alignment actions: applied, deferred, and design-review items.

## Applied Fixes (This Session)

### FIX-1: Rate Field Reclassification (CRITICAL)

**File**: `insights_formatter.py` `_FIELD_FORMAT` dict

Upstream `_PRECISION_RULES` was updated to properly categorize fields by output scale.
Consumer `_FIELD_FORMAT` now aligns:

| Field | Old Consumer | Upstream Truth | New Consumer | Source |
|-------|-------------|----------------|-------------|--------|
| `ctr` | "rate" (x100) | PERCENTAGE (PercentageFormula, 0-100) | **"percentage"** | BUG-3 remediation |
| `lctr` | "rate" (x100) | PERCENTAGE (PercentageFormula, 0-100) | **"percentage"** | BUG-3 remediation |
| `sched_rate` | "percentage" | RATE (SchedRateFormula, 0-1) | **"rate"** | Contract Remediation |
| `pacing_ratio` | "percentage" | RATIO (PacingRatioFormula, unbounded) | **"ratio"** | Contract Remediation |
| `booking_rate` | "rate" | RATE (0-1) | "rate" (unchanged) | BUG-1 fix |
| `conversion_rate` | "percentage" | PERCENTAGE | "percentage" (unchanged) | Correct |
| `ns_rate` | "percentage" | PERCENTAGE | "percentage" (unchanged) | Correct |
| `nc_rate` | "percentage" | PERCENTAGE | "percentage" (unchanged) | Correct |
| `conv_rate` | "percentage" | PERCENTAGE | "percentage" (unchanged) | Correct |
| `nsr_ncr` | "percentage" | PERCENTAGE | "percentage" (unchanged) | Correct |
| `roas` | "ratio" | RATIO (unbounded) | "ratio" (unchanged) | Correct |

**Risk if missed**: ctr/lctr would display as x100 of already-percentage values (e.g., 342% instead of 3.42%). sched_rate would display as-is (e.g., 0.03% instead of 3.42%). pacing_ratio would show "85.00%" instead of "1.05x" multiplier notation.

**Tests**: 268 formatter tests pass. Parametrized data updated for all 4 fields.

### FIX-2: Phone PII Masking (HIGH)

**File**: `insights_formatter.py`

Applied in prior session (2026-02-22 AM):
- `_PII_PHONE_COLUMNS` constant: `{office_phone, phone, patient_phone, contact_phone}`
- Masking in `_format_cell_html` before any other formatting
- `_mask_pii_rows` helper for JSON embed (Copy TSV) masking
- 9 regression tests in `TestPiiPhoneMasking`

**Status**: COMPLETE. Upstream also added `pii_annotations` metadata on the data service side.

### FIX-3: Stale Row Limit Comment (LOW)

**File**: `insights_export.py:65`

Updated from "API max is 100 (autom8y-data validation constraint)" to
"upstream API supports up to 500; self-limited to 100 for report readability".

Upstream validation constraint was raised to 500 in an earlier remediation.

---

## Deferred Items (Require Deeper Evaluation)

### D-1: Reconciliation Multi-Tenant Filter (MEDIUM)

**File**: `insights_export.py` lines 914-937

**Current state**: Consumer has a defensive post-hoc phone filter that strips rows
not matching the offer's `office_phone`. This was originally needed because the
reconciliation insight could return data for other businesses sharing the same
underlying data structure.

**Upstream change**: `required_filters=["business"]` now enforced server-side on the
reconciliation insight, which should prevent multi-tenant data leak at source.

**Recommendation**: KEEP the consumer filter as belt-and-suspenders. The cost is negligible
(one list comprehension) and protects against any regression in server-side enforcement.
Add a comment documenting that upstream now has `required_filters` but consumer retains
as defense-in-depth.

**Action**: No code change. Add comment annotation in next cleanup pass.

### D-2: include_unused Parameter for UNUSED ASSETS (MEDIUM)

**File**: `insights_export.py` lines 818-852

**Current state**: Consumer derives "UNUSED ASSETS" client-side by scanning the ASSET TABLE
for rows where spend and leads are both zero/null. This works but duplicates logic that
the upstream API now supports natively via `include_unused=True` parameter.

**Upstream change**: `include_unused` parameter added to the asset frame_type query. When
`include_unused=True`, the API includes zero-activity assets; when `False` (default),
they are excluded.

**Recommendation**: EVALUATE in next sprint. Migration would:
1. Add `include_unused=True` to the ASSET TABLE fetch call
2. Split response into ASSET TABLE (active) and UNUSED ASSETS (inactive)
3. Remove client-side derivation logic

**Risk**: The upstream definition of "unused" (spend=0 AND leads=0) must exactly match
the consumer's current filter. Need to verify BUG-6 (`_apply_activity_filter` for
`frame_type='asset'`) covers the same zero-check semantics.

**Complexity**: ~0.5 day. Not urgent — current approach works correctly.

### D-3: AD QUESTIONS Frame Type Enum (LOW)

**File**: Not applicable (blocked by upstream)

**Current state**: The `frame_type: 'question'` is not yet in the API's enum validation.
AD QUESTIONS table always returns an error. The table appears in the report as an error
section with a message.

**Upstream status**: Known gap. Requires data service update to add 'question' to the
frame_type enum. No consumer action until upstream ships.

### D-4: Period Aggregation Split (LOW-MEDIUM)

**Current state**: Consumer fetches BY WEEK, BY MONTH, and BY DAY as separate API calls
to the `offer_period_stats` insight with different `period_type` parameters.

**Upstream change**: Session 1 (Contract Remediation) added a unified `/periods` endpoint
concept that could return all period types in a single call.

**Recommendation**: EVALUATE. A unified fetch could reduce 3 API calls to 1, improving
latency. However, the current approach works and the latency impact is masked by
concurrent fetching. Low priority.

### D-5: Conditional Format Type Knowledge (LOW)

**File**: `insights_formatter.py` `_CONDITIONAL_FORMAT_THRESHOLDS`

**Current state**: Thresholds encode implicit type knowledge:
- `booking_rate: (0.40, 0.20)` — ratio scale (0-1)
- `conv_rate: (40.0, 20.0)` — percentage scale (0-100)

This means threshold values must change if upstream ever changes the field's output scale.
There's no compile-time check linking `_FIELD_FORMAT` categories to threshold scales.

**Recommendation**: Acceptable technical debt. The coupling is small (2 entries),
well-documented via comments, and caught by tests. A format-aware threshold system
would be over-engineering.

---

## Alignment Status Matrix

| Upstream Contract Element | Consumer Status | Notes |
|--------------------------|----------------|-------|
| `_PRECISION_RULES` RATE fields | ALIGNED | booking_rate, sched_rate |
| `_PRECISION_RULES` PERCENTAGE fields | ALIGNED | ctr, lctr, conversion_rate, ns_rate, nc_rate, conv_rate, nsr_ncr |
| `_PRECISION_RULES` RATIO fields | ALIGNED | roas, pacing_ratio |
| `_PRECISION_RULES` CURRENCY fields | ALIGNED | All 16 fields correct |
| `required_filters` (recon) | ALIGNED (belt+suspenders) | Consumer retains defensive filter |
| `pii_annotations` metadata | N/A | Consumer masks at display boundary regardless |
| `include_unused` param | NOT LEVERAGED | Consumer uses client-side derivation (D-2) |
| `frame_type: 'question'` enum | BLOCKED upstream | AD QUESTIONS table errors gracefully |
| Row limit (500 max) | ALIGNED | Comment updated; self-limited to 100 |
| BUG-1 booking_rate (ratio 0-1) | ALIGNED | Consumer "rate" type applies x100 correctly |
| BUG-2 booking_rate denominator | N/A | Upstream-only fix (formula change) |
| BUG-4 appointment type filter | N/A | Upstream-only fix (materializer) |
| BUG-5 grouping dimensions | N/A | Upstream-only fix (prevents join fan-out) |
| BUG-6 activity filter for assets | N/A | Upstream-only fix (affects D-2 evaluation) |

## Cross-Fact Dimension Scoping (Session 2)

Upstream fixed a critical bug where reconciliation spend was inflated 1000-10000x due to
join fan-out on the cross-fact path (ads -> adsets -> campaigns -> offers). This was a
server-side computation error — no consumer action required. Consumer will now receive
correct reconciliation values.

## Test Coverage

| Test Suite | Count | Status |
|-----------|-------|--------|
| Formatter unit tests | 268 | PASS |
| Export/handler unit tests | ~88 | PASS |
| Full automation suite | 1062 | PASS |

## Next Actions

1. **Smoke test** — Re-run live smoke on offer 1211872268838349 to validate ctr/lctr/sched_rate/pacing_ratio rendering with real API data
2. **D-2 evaluation** — When convenient, evaluate `include_unused` param migration
3. **D-3 monitor** — Watch for upstream `frame_type: 'question'` enum addition
4. **D-1 comment** — Add `required_filters` documentation comment to recon filter
