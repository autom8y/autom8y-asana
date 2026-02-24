# WS-LIVEAPI Session Prompt

## Rite & Workflow
- Rite: 10x-dev
- Workflow: `/task`
- Complexity: MODULE

## Objective

Resolve the dead string-literal test suite in `test_live_api.py` (lines 42-306) by either promoting to active code or deleting after coverage verification. Also clean up related dead infrastructure in `conftest.py`.

## Context

- Seed doc: `.claude/wip/REM-HYGIENE/WS-LIVEAPI.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md` (RS-020, RS-035, RS-036, RS-044)
- Analysis: `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-integ-batch2.md` (P2B2-019)
- Decay: `.claude/wip/SLOP-CHOP-TESTS-P2/phase3-decay/DECAY-REPORT.md` (P3-004, P3-005, P3-013)

## Scope

### IN SCOPE

- **Test file**: `tests/integration/persistence/test_live_api.py` (RS-020)
- **Conftest**: `tests/integration/persistence/conftest.py` (RS-036, RS-044)
- **Coverage reference (read only)**: `tests/integration/persistence/test_action_batch_integration.py`
- **Production source (read only)**: `src/autom8_asana/persistence/session.py`

### OUT OF SCOPE

- Modifying production source files
- Other test directories
- test_action_batch_integration.py (read only for coverage assessment)

## Execution Plan

### Step 1: Coverage Verification

Read `tests/integration/persistence/test_action_batch_integration.py` to determine if it covers:
- [ ] Create operations (TestLiveAPICreate equivalent)
- [ ] Update operations (TestLiveAPIUpdate equivalent)
- [ ] Batch operations (TestLiveAPIBatch equivalent)
- [ ] Delete operations (TestLiveAPIDelete equivalent)
- [ ] Error handling (TestLiveAPIErrors equivalent)

### Step 2: Decision

**If test_action_batch_integration.py covers all 5 categories** -> Option B (Delete):

1. Delete lines 42-306 in `test_live_api.py` (entire string literal block)
2. Delete `TestIntegrationInfrastructure` class if it only checks env vars
3. If the file is now empty or trivial, consider deleting it entirely
4. Delete dead env-var shim fixtures from conftest.py:
   - `asana_token` (line 40)
   - `workspace_gid` (line 47)
   - `project_gid` (line 53)
5. Remove stale scaffold comments from conftest.py:
   - Line 18 ("Note: These imports assume the client module exists")
   - Lines 58-80 (commented-out fixture block)

**If coverage gaps exist** -> Option A (Promote):

1. Extract string literal into active Python code
2. Update imports to current module paths
3. Adapt method signatures to current SaveSession API
4. Guard all live-API tests with:
   ```python
   @pytest.mark.skipif(
       not os.getenv("ASANA_ACCESS_TOKEN"),
       reason="requires live Asana credentials"
   )
   ```
5. Verify tests are collected by pytest (even if skipped)
6. Keep conftest fixtures for the promoted tests

### Step 3: Verify

```bash
# Verify no collection errors:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/persistence/ --collect-only -q

# Verify no test regressions:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/persistence/ -v --tb=short
```

## Escalation Triggers

- If coverage verification is ambiguous (partial overlap), prefer Option B (delete) with a code comment noting which scenarios would need coverage if live-API testing is added in the future.
- If conftest.py has other active fixtures beyond the dead shims, preserve the file but remove only the dead fixtures.

## Time Budget

- Estimated: 2 hours
- ~30 min reading test_action_batch_integration.py for coverage assessment
- ~1 hour implementation (delete path: 30 min; promote path: 1.5 hours)
- ~30 min verification and conftest cleanup

Commit with message prefix `test(10x):`.
