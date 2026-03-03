# Triage + Remediation: Windowed Aggregation 500 on Insight Execute

**Origin**: autom8y-asana deploy QA (2026-02-25)
**Repo**: autom8y-data (this session operates here)
**Rite**: 10x-dev
**Complexity**: MODULE (triage unknown, fix likely PATCH-MODULE)

---

## Problem

`POST /api/v1/insights/{name}/execute` returns HTTP 500 when `window_days` is specified.
The non-windowed path (same insight, same parameters, no `window_days`) returns 200 OK.
The 500 response is the generic catch-all -- no structured error detail is surfaced to the caller.

This is a regression or latent bug, not a missing feature. Windowed aggregation is a shipped
primitive used across multiple insights.

---

## Reproduction

**Working (no windowing)**:
```bash
curl -s -X POST https://data.api.autom8y.io/api/v1/insights/reconciliation/execute \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"business": "+17175558734", "vertical": "chiropractic"}' \
  | jq '.data | length'
# Returns: 2 (200 OK, ~57s)
```

**Failing (with windowing)**:
```bash
curl -s -X POST https://data.api.autom8y.io/api/v1/insights/reconciliation/execute \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"business": "+17175558734", "vertical": "chiropractic", "window_days": 14}' \
  | jq '.'
# Returns: {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}} (500, ~24s)
```

Local reproduction (if `just dev-up data` is available):
```bash
# Replace host with http://localhost:5200, no JWT needed for local
```

---

## Triage Starting Points

The windowing code path, in execution order:

1. **`api/routes/insights.py`** -- endpoint handler, passes `window_days` from `InsightExecuteRequest` to engine
2. **`api/models.py`** -- `InsightExecuteRequest.window_days: Optional[int]` (1-365)
3. **`analytics/insight_executor.py`** -- `InsightExecutor.execute()`, windowing at step 8 (when `window_days is not None and result.df.height > 0`)
4. **`analytics/core/aggregation.py`** -- `aggregate_by_window()`, `find_date_column()`, `recompute_rate_metrics()`
5. **`analytics/core/registry/composite.py`** -- `Formula`, `pre_recomputation_formulas`
6. **`analytics/insights/library.py`** -- `reconciliation` insight definition (includes post-processors: `reconciliation_coverage`, `active_section_days_enrichment`, `column_coverage_metadata`)

The triage should determine:
- The exact exception/traceback (check application logs, or add temporary logging)
- Whether the failure is in `aggregate_by_window()` itself, or upstream (e.g., the DataFrame reaching step 8 lacks an expected date column, or has an incompatible schema)
- Whether this is specific to reconciliation or affects ALL insights with `window_days`
- Whether the `require_date_grain` flag interacts with windowing
- Whether the reconciliation post-processors modify the DataFrame in a way that breaks windowing assumptions (e.g., removing/renaming the date column)

### Recent Changes That May Be Relevant

Two recent hotfixes touched adjacent code paths:
- `b700128` -- Chunked seed materialization: per-table `seed_lookback_days`/`seed_chunk_days`
- `65f187e` -- Rolling window date filter: removed unnecessary date filter skip in TimeResolver, canonical "date" dimension for split queries

The second commit explicitly changed date handling in the query path. It may have altered
the shape of the DataFrame that reaches the windowing step.

---

## Scope

Do NOT limit triage to the reconciliation insight. The windowing primitive is shared.

1. Identify the root cause in the windowing path
2. Determine which insights are affected (reconciliation confirmed; test others)
3. Fix the root cause (not a per-insight workaround)
4. Add or update tests covering the windowed aggregation path

---

## Success Criteria

1. `POST /api/v1/insights/reconciliation/execute` with `window_days: 14` returns 200 with correct aggregated data
2. All other insights that support `window_days` also return 200
3. Non-windowed queries are unaffected (no regression)
4. Response time within the existing SLA envelope (reconciliation LIFETIME is ~57s; windowed should be comparable or faster)
5. Existing tests pass (green-to-green)

---

## Verification

After the fix, run the reproduction commands above against local (or deployed) and confirm:
- 200 response with `window_days: 14`
- Response contains aggregated rows (fewer rows than LIFETIME, grouped by window period)
- 200 response WITHOUT `window_days` still works (regression check)
- If unit/integration tests exist for `aggregate_by_window`, they pass
- If no tests exist, add at minimum: (a) happy path with a date column present, (b) edge case where DataFrame has zero rows, (c) edge case where date column is missing or misnamed

---

## Out of Scope

- Performance optimization of the windowing path (unless the fix naturally improves it)
- Changes to the autom8y-asana consumer code
- New windowing features or API surface changes
- Refactoring aggregation.py beyond what the fix requires

---

## Session Notes

- This repo has its own `.claude/CLAUDE.md` and MEMORY.md -- follow those conventions
- The caller (autom8y-asana) smoke test expects T14 RECONCILIATIONS (window_days=14) to succeed; that is the end-to-end validation target
- Emit a checkpoint with root cause, fix description, and test results before wrapping
