# SPIKE: INSIGHTS_DATA Consumer Sprint — Feasibility Assessment

```yaml
status: COMPLETE
date: 2026-02-27
session: session-20260227-175851-a3aa2c27
time_box: 15 min
origin: autom8y-data/.claude/wip/PROMPT_0_CONSUMER_SPRINT_ASANA.md
```

---

## Summary

All 3 consumer-side items from INSIGHTS_DATA closure are now **CLOSED**.

| Item | Status | Effort | Action |
|------|--------|--------|--------|
| CG-4 | **CLOSED** (pre-existing) | 0 | No work needed |
| OPP-4 | **CLOSED** (implemented) | ~0.5 day | `tests/integration/test_schema_contract.py` |
| COMP-5 | **CLOSED** (implemented) | ~0.5 day | Migrated to data-service `include_unused=true` |

**All items closed.** Original 2-day estimate → ~1 day actual (CG-4 was pre-existing).

---

## CG-4: T14 Reconciliation Consumer Wiring — CLOSED

All acceptance criteria from PROMPT_0 are met. Evidence:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `get_reconciliation_async()` exists | DONE | `client.py:1195` → delegates to `_endpoints/reconciliation.py` |
| Full resilience (CB, retry, auth, feature guard) | DONE | `_endpoints/reconciliation.py:122-183` uses DefaultEndpointPolicy |
| TABLE_NAMES has 12 entries | DONE | `insights_export.py:76-78`, `TABLE_ORDER` has 12 items |
| `_fetch_all_tables()` fetches both | DONE | `insights_export.py:746-759` — LIFETIME + T14 in asyncio.gather |
| `_fetch_table()` has reconciliation branch | DONE | `insights_export.py:903-933` with defensive phone filtering |
| Formatter TABLE_ORDER + COLUMN_ORDER | DONE | `insights_formatter.py:34-75` — both tables positioned after LEADS |
| Error isolation | DONE | `_fetch_table()` wraps in try/except → `TableResult(success=False)` |
| `_normalize.normalize_period()` NOT modified | DONE | Not touched |

**Git evidence**: `8d16ef5 feat(export): add LIFETIME and T14 reconciliation tables to insights report`

**Test coverage**:
- `test_insights_export.py`: reconciliation mock wiring (lines 208-217), TABLE_NAMES assertions (lines 1226-1227)
- `test_insights_formatter.py`: 40+ reconciliation assertions covering TABLE_ORDER, COLUMN_ORDER, section rendering, pending message, slugified IDs

---

## OPP-4: Cross-Repo Schema Contract Test — OPEN, READY

### Feasibility: HIGH

**What exists**:
- `_FIELD_FORMAT` dict at `insights_formatter.py:950` — 40 entries mapping metric names to formatter types (currency, rate, percentage, ratio, per20k)
- Integration test infrastructure: `tests/integration/` with `pytest.mark.integration` marker (8 existing test files use it)
- Smoke test auth infrastructure: `scripts/smoke_test_api.py` demonstrates S2S JWT authentication flow

**What's needed**:
1. `tests/integration/test_schema_contract.py` — NEW file
2. HTTP GET to data service `GET /api/v1/metrics?limit=1000` (paginated)
3. Compatibility validation: metric_type ↔ _FIELD_FORMAT formatter
4. Coverage validation: every metric has a _FIELD_FORMAT entry
5. Orphan detection: warn on consumer entries not in API

**Implementation risks**:
- Needs data service available in CI (skipable via `pytest.mark.integration`)
- Auth: reuse existing `AUTOM8_DATA_URL` + JWT exchange pattern from smoke tests
- Pagination: API response shape needs discovery (PROMPT_0 says `limit=1000` per page)

**MetricType → formatter compatibility map** (from PROMPT_0):

| metric_type | Expected _FIELD_FORMAT value |
|-------------|------------------------------|
| CURRENCY | "currency" |
| PERCENTAGE | "percentage" |
| RATIO | "ratio" |
| COUNT | (none — integer formatting, no entry needed) |
| PER_20K | "per20k" |
| DURATION | (not in _FIELD_FORMAT yet — may need adding) |
| DATE | (not in _FIELD_FORMAT — passthrough) |
| STATUS | (not in _FIELD_FORMAT — passthrough) |

**Gap identified**: DURATION, DATE, STATUS metric_types have no `_FIELD_FORMAT` entries. Contract test should either:
- Allow missing entries for passthrough types (COUNT, DATE, STATUS, DURATION)
- Or require explicit "passthrough" entries

**Recommendation**: Allow-list passthrough types. Only fail on CURRENCY/PERCENTAGE/RATIO/PER_20K missing entries.

---

## COMP-5: include_unused Consumer Deduplication — OPEN, EVALUATE FIRST

### Current client-side derivation (`insights_export.py:817-830`):

```python
unused_rows = [
    row
    for row in (asset_result.data or [])
    if row.get("spend", -1) == 0
    and row.get("imp", -1) == 0
    and not row.get("disabled")
    and not row.get("is_generic")
]
```

Four-condition filter:
1. `spend == 0`
2. `imp == 0` (impressions)
3. `disabled == False` (not disabled)
4. `is_generic == False` (not generic)

### What needs evaluation:

The data-side `include_unused=true` parameter (on the assets insight) returns unused assets
server-side. But **we don't know if the server-side definition matches these 4 conditions exactly**.

**Before implementing COMP-5**:
1. Call `POST /api/v1/insights/assets/execute` with `include_unused=true` on a real business
2. Compare the server-side "unused" rows against the client-side 4-condition filter
3. If shapes differ → DEFER (per PROMPT_0 risk note)
4. If shapes match → safe to switch

**Approach**: Add this as a smoke-test-level evaluation (not a code change). Can be done alongside OPP-4 if data service is available.

### Risk assessment: LOW
- Current code works correctly
- No urgency to deduplicate
- If API shape differs, deferral is the right call

---

## Recommended Sprint Plan

### Phase 1: OPP-4 (0.5 day)
1. Create `tests/integration/test_schema_contract.py`
2. Fetch metrics from discovery API
3. Validate `_FIELD_FORMAT` coverage and compatibility
4. Mark with `pytest.mark.integration`, skip when data service unavailable

### Phase 2: COMP-5 Evaluation (0.5 day)
1. Run smoke test with `include_unused=true` against data service
2. Compare output shapes
3. If match → implement switch (remove client-side derivation)
4. If mismatch → document and DEFER

### Skipped: CG-4
Already shipped. No work needed.

---

## Cross-Repo References Consulted

| File | Path | Used For |
|------|------|----------|
| Consumer sprint prompt | `autom8y-data/.claude/wip/PROMPT_0_CONSUMER_SPRINT_ASANA.md` | Source spec |
| DataServiceClient | `src/autom8_asana/clients/data/client.py` | CG-4 verification |
| Reconciliation endpoint | `src/autom8_asana/clients/data/_endpoints/reconciliation.py` | CG-4 verification |
| Insights export | `src/autom8_asana/automation/workflows/insights_export.py` | CG-4 + COMP-5 |
| Insights formatter | `src/autom8_asana/automation/workflows/insights_formatter.py` | CG-4 + OPP-4 |
| Export tests | `tests/unit/automation/workflows/test_insights_export.py` | CG-4 test coverage |
| Formatter tests | `tests/unit/automation/workflows/test_insights_formatter.py` | CG-4 test coverage |
