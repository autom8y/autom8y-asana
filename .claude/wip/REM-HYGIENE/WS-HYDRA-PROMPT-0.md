# WS-HYDRA Session Prompt

## Rite & Workflow
- Rite: 10x-dev
- Workflow: `/task`
- Complexity: SPOT

## Objective

Fix the dead traversal test `test_traversal_stops_at_business` in `test_hydration.py` by adding the missing function call (act phase) and assertion (assert phase).

## Context

- Seed doc: `.claude/wip/REM-HYGIENE/WS-HYDRA.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md` (RS-002)
- Analysis: `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-integ-batch1.md` (P2B1-002)

## Scope

### IN SCOPE

- **Test file**: `tests/integration/test_hydration.py` (line 366, `test_traversal_stops_at_business`)
- **Production source (read only)**: `src/autom8_asana/models/business/hydration.py` (`_traverse_upward_async`)

### OUT OF SCOPE

- Modifying production source files
- Other test functions in test_hydration.py
- Other test files

## Execution Plan

### Step 1: Read Production Source

Read `_traverse_upward_async` in `src/autom8_asana/models/business/hydration.py`:
1. What is the function signature? (parameters, return type)
2. How does it determine the "business entity boundary" (stopping condition)?
3. What does it return? (HydrationResult, list of branches, etc.)

### Step 2: Read Existing Test Setup

Read `test_traversal_stops_at_business` at line 366 in `test_hydration.py`:
1. What mocks are already configured?
2. What mock data is already set up?
3. What start_gid would be passed to `_traverse_upward_async`?

### Step 3: Add Act Phase

Call the function with the configured mocks:
```python
result = await _traverse_upward_async(start_gid, mock_client, ...)
```

If `_traverse_upward_async` is not imported in the test, add the import at the top of the test file (it is already imported in other tests in this file -- check the existing imports).

### Step 4: Add Assert Phase

Assert that traversal stopped at the business entity boundary:
- The result should NOT include ancestors beyond the business node
- Example assertions (adjust based on actual return type):
  ```python
  assert result is not None
  assert result.branches[-1].entity_type == EntityType.BUSINESS
  # OR: assert traversal did not fetch beyond business GID
  mock_client.tasks.get_async.assert_not_called_with(parent_of_business_gid)
  ```

### Step 5: Verify

```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_hydration.py::test_traversal_stops_at_business -v --tb=short

# Run full hydration test suite to verify no regressions:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_hydration.py -v --tb=short
```

## Time Budget

- Estimated: 1 hour
- ~30 min reading production source and understanding stopping condition
- ~20 min implementing act + assert
- ~10 min verification

Commit with message prefix `test(10x):`.
