# WS-WSISO Session Prompt

## Rite & Workflow
- Rite: 10x-dev
- Workflow: `/task`
- Complexity: MODULE

## Objective

Replace 4 pass-only stubs (RS-012) and 4 tautological constructor-assertion tests (RS-013) in `test_workspace_switching.py` with behavioral workspace isolation tests, or convert to named `pytest.mark.skip` with explicit reasons if the isolation logic does not exist yet.

## Context

- Seed doc: `.claude/wip/REM-HYGIENE/WS-WSISO.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md` (RS-012, RS-013)
- Analysis: `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-integ-batch2.md` (P2B2-001 to P2B2-008)

## Scope

### IN SCOPE

- **Test file**: `tests/integration/test_workspace_switching.py`
- **Production source (read only)**:
  - `src/autom8_asana/client.py` (AsanaClient, workspace context)
  - `src/autom8_asana/resolution/field_resolver.py` (FieldResolver)
  - `src/autom8_asana/models/business/registry.py` (WorkspaceProjectRegistry)

8 tests to fix:

**RS-012 (pass-only stubs)**: lines 166, 193, 227, 255
**RS-013 (tautological assertions)**: lines 75, 104, 129, 156-157
**RS-014 (unused mock_client, advisory)**: lines 64, 87 -- address as part of cleanup

### OUT OF SCOPE

- Modifying production source files
- Other test files
- Adding workspace isolation features to production code

## Execution Plan

### Step 1: Read Production Source

Understand what workspace isolation guarantees exist:
1. Read `AsanaClient.__init__` -- does it bind to a specific workspace?
2. Read `FieldResolver` -- does it require workspace context?
3. Read `WorkspaceProjectRegistry` -- does `get_workspace_registry()` isolate by workspace?

### Step 2: Decide Implementation Approach

**If workspace isolation logic EXISTS in production code**:
- Implement behavioral tests exercising the actual isolation contract
- Example for RS-013 tautological tests:
  ```python
  def test_task_belongs_to_single_workspace(self):
      client_ws1 = create_mock_client_for_workspace(gid="ws1")
      client_ws2 = create_mock_client_for_workspace(gid="ws2")
      # Exercise actual isolation through the system under test
      # Assert workspace independence
  ```

**If workspace isolation logic does NOT exist**:
- Convert to named skips with specific contract descriptions:
  ```python
  @pytest.mark.skip(reason="Not yet implemented: workspace isolation requires separate AsanaClient instances per workspace")
  def test_recommended_pattern_separate_clients(self):
      pass
  ```
- Named skips are better than silent passes. They document intent and show up in test reports.

### Step 3: Clean Up Unused Variables

Remove the unused `mock_client = create_mock_client_for_workspace()` assignments at lines 64, 87 (RS-014). If the variable is needed for the new test implementation, keep it; otherwise delete.

### Step 4: Verify

```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_workspace_switching.py -v --tb=short

# Verify no more pass-only stubs:
grep -c "^        pass$" tests/integration/test_workspace_switching.py
# Expected: 0

# Verify no more tautological GID assertions:
grep -n 'assert.*gid == "' tests/integration/test_workspace_switching.py
# Expected: only assertions against actual workspace behavior, not constructor args
```

## Escalation Triggers

- If workspace isolation is not implemented in production code, convert ALL 8 tests to named skips rather than leaving as pass-only or tautological. Document the specific behavioral contract each test should cover.
- If `create_mock_client_for_workspace` does provide real workspace separation, implement tests using it.

## Time Budget

- Estimated: 3 hours
- ~45 min reading production source (client, field resolver, registry)
- ~1.5 hours implementing 8 tests (or converting to named skips)
- ~45 min cleanup (RS-014) and verification

Commit with message prefix `test(10x):`.
