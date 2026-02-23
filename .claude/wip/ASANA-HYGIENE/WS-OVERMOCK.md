# WS-OVERMOCK: Investigate High-Patch-Count Tests

**Finding IDs**: LS-028, LS-029
**Severity**: SMELL
**Estimated Effort**: 2 hours (spike/research)
**Dependencies**: None (independent)
**Lane**: D (any available slot)
**Type**: Investigation spike -- no code changes expected

---

## Scope

Two findings flagged tests with 24-38 mock patches. The analysis report noted that the core logic IS exercised despite the patch count. This workstream investigates whether the high mock counts are a structural problem worth addressing or an acceptable cost of testing complex integration points.

### LS-028: Cache warmer Lambda handler (24 patches)
- **File**: `tests/unit/lambda_handlers/test_cache_warmer.py` (line 558 area)
- **Context**: Lambda handler test that needs to isolate many external dependencies (AWS services, Asana API, cache backends, metrics)
- **Analysis note**: "Lambda handler isolation; flag for future"

### LS-029: Query route handlers (29-38 patches)
- **Files**:
  - `tests/unit/api/test_routes_query.py` (line 100 area) -- 29+ patches
  - `tests/unit/api/test_routes_query_rows.py` (line 81 area) -- 38 patches
- **Context**: Query route tests that mock the entire dependency chain
- **Analysis note**: "Core polars logic IS exercised despite patch count"

---

## Objective

**Done when** a written assessment answers these questions:
1. Are the patches mocking external boundaries (appropriate) or internal implementation (brittle)?
2. Would a test fixture factory reduce the patch count without losing coverage?
3. Is there a structural improvement (dependency injection, test harness) that would reduce patches?
4. What is the recommendation: accept as-is, refactor incrementally, or defer to test architecture initiative?

**Deliverable**: Write findings to `.claude/wip/ASANA-HYGIENE/WS-OVERMOCK-FINDINGS.md`

---

## Files to Read

- `tests/unit/lambda_handlers/test_cache_warmer.py` -- read the high-patch test(s) around line 558
- `tests/unit/api/test_routes_query.py` -- read test setup around line 100
- `tests/unit/api/test_routes_query_rows.py` -- read test setup around line 81
- `src/autom8_asana/lambda_handlers/cache_warmer.py` -- understand what dependencies the handler has
- `src/autom8_asana/api/routes/query.py` -- understand route dependency chain
- `src/autom8_asana/api/routes/query_v2.py` -- compare v2 route test patterns

---

## Constraints

- **No code changes**: This is investigation only
- **Time-boxed**: 2 hours maximum. If the answer is not clear by then, recommend "defer to test architecture initiative" (debt item D-027)
- **Do NOT refactor**: Produce recommendations, not patches. Refactoring high-mock-count tests is a larger initiative.

---

## Context References

- **Finding details**: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-028, LS-029)
- **Related debt item**: `docs/debt/LEDGER-cleanup-modernization.md` (D-027: Heavy mock usage, 540 sites)

---

## Verification

No code changes, so no pytest verification needed. Deliverable is the findings document.
