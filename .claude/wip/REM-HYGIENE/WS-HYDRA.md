# WS-HYDRA: Dead Traversal Test

**Objective**: Fix `test_traversal_stops_at_business` in `test_hydration.py` by adding the missing act and assert phases.

---

## Source Findings

| RS-ID | Finding | Severity | Confidence |
|-------|---------|----------|------------|
| RS-002 | `test_traversal_stops_at_business` configures mocks but never calls `_traverse_upward_async` and never asserts. Dead test with zero behavioral coverage. | DEFECT HIGH | HIGH |

---

## File Targets

- **Test file**: `tests/integration/test_hydration.py` (line 366)
- **Production source (read only)**: `src/autom8_asana/models/business/hydration.py` (`_traverse_upward_async`)

---

## Implementation Strategy

1. Read `_traverse_upward_async` in `hydration.py` to understand:
   - Function signature (parameters)
   - What it returns (HydrationResult or equivalent)
   - How it determines "business entity boundary" (stopping condition)
2. In the test, call `_traverse_upward_async` with the already-configured mocks
3. Assert that traversal stopped at the business entity (e.g., result does not include ancestors beyond the business node)
4. If the function is not imported at test scope, add the import

---

## Effort Estimate

- **Total**: ~1 hour
- **Breakdown**: ~30 min reading production source, ~30 min implementing act+assert
- **Risk**: LOW -- mocks are already configured; only the call and assertion are missing

---

## Dependencies

- None. File has zero overlap with other workstreams.

---

## Rite / Complexity

- **Rite**: 10x-dev (recommended, confirm at dispatch)
- **Complexity**: SPOT
