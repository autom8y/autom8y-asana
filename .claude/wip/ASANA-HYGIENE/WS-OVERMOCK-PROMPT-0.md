# WS-OVERMOCK Session Prompt

## Rite & Workflow
- Rite: rnd
- Workflow: `/spike`
- Complexity: SPIKE

## Objective

Investigate 3 test files with 24-38 mock patches each (LS-028, LS-029) and produce a decision document recommending one of: accept as-is, refactor incrementally, or defer to a future test architecture initiative. No code changes.

## Context

Slop-chop Partition 1 flagged 2 findings for over-mocked tests. The analysis report noted that the core logic IS exercised despite high patch counts. This spike investigates whether the mock density is structural (necessary for isolation) or incidental (could be reduced with better test infrastructure).

Related debt item D-027 in `docs/debt/LEDGER-cleanup-modernization.md` notes 540 mock call sites across API tests. This spike informs whether D-027 is worth pursuing.

- Seed doc: `.claude/wip/ASANA-HYGIENE/WS-OVERMOCK.md`
- Finding details: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md` (LS-028, LS-029)

## Scope

### IN SCOPE

**Files to read and analyze (do NOT modify)**:

LS-028 -- Cache warmer Lambda handler:
- `tests/unit/lambda_handlers/test_cache_warmer.py` (focus: line 558 area, 24 patches)
- `src/autom8_asana/lambda_handlers/cache_warmer.py` (production dependencies)

LS-029 -- Query route handlers:
- `tests/unit/api/test_routes_query.py` (focus: line 100 area, 29+ patches)
- `tests/unit/api/test_routes_query_rows.py` (focus: line 81 area, 38 patches)
- `src/autom8_asana/api/routes/query.py` (production dependency chain)
- `src/autom8_asana/api/routes/query_v2.py` (compare: does v2 have better test patterns?)

**Deliverable**: Write `.claude/wip/ASANA-HYGIENE/WS-OVERMOCK-FINDINGS.md`

### OUT OF SCOPE

- Making any code changes
- Refactoring the tests
- Analyzing mock density in files NOT listed above
- Broader D-027 investigation (that is a separate initiative)

## Execution Plan

1. **Read** `test_cache_warmer.py` around line 558. Count and categorize each patch:
   - **Boundary mock**: AWS service, Asana API, external HTTP -- appropriate
   - **Internal mock**: patching an internal function/class in the same package -- brittle
   - **Configuration mock**: env vars, settings -- gray area
2. **Read** `cache_warmer.py` production code. Map the actual dependency tree. Determine which patches correspond to real external boundaries.
3. **Read** `test_routes_query.py` around line 100 and `test_routes_query_rows.py` around line 81. Same categorization.
4. **Read** `query.py` and `query_v2.py`. Compare: does v2 have fewer dependencies, and do its tests have fewer patches?
5. **Assess** for each file:
   - Could a fixture factory consolidate repeated mock setup?
   - Would dependency injection in the production code reduce the need for patching?
   - Is there a test harness pattern (e.g., a pre-wired app factory) that could help?
6. **Write** the findings document with recommendation.

### Questions to Answer

1. What percentage of patches mock external boundaries vs. internal implementation?
2. Would a `conftest.py` fixture factory reduce patch count without losing coverage?
3. Is there a structural production-code change (DI, factory) that would reduce patches?
4. Recommendation: `ACCEPT` / `REFACTOR-INCREMENTAL` / `DEFER-TO-D027`

## Verification

No code changes. Deliverable is `.claude/wip/ASANA-HYGIENE/WS-OVERMOCK-FINDINGS.md`.

Verify the document was written:
```bash
test -f .claude/wip/ASANA-HYGIENE/WS-OVERMOCK-FINDINGS.md && echo "Deliverable exists" || echo "MISSING"
```

## Time Budget

- **Hard stop: 1 hour**
- If the analysis is not conclusive by the 1-hour mark, write what you have and recommend `DEFER-TO-D027` as the default verdict
- Do NOT spend more than 20 minutes per file group (LS-028: 20 min, LS-029: 20 min, write-up: 20 min)
