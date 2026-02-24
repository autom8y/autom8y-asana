# WS-SSEDGE Session Prompt

## Rite & Workflow
- Rite: 10x-dev
- Workflow: `/task`
- Complexity: MODULE

## Objective

Implement behavioral assertions for 10 SaveSession tests across two files: 5 shallow edge-case tests (RS-015), 1 cleanup verification test (RS-016), and 4 self-raising exception tests (RS-017).

## Context

- Seed doc: `.claude/wip/REM-HYGIENE/WS-SSEDGE.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md` (RS-015, RS-016, RS-017)
- Analysis: `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-integ-batch2.md` (P2B2-010 to P2B2-016)

## Scope

### IN SCOPE

- **File 1**: `tests/integration/test_savesession_edge_cases.py` (RS-015, RS-016)
- **File 2**: `tests/integration/test_savesession_partial_failures.py` (RS-017)
- **Production source (read only)**:
  - `src/autom8_asana/persistence/session.py` (SaveSession: preview(), commit_async(), __aexit__, track())
  - `src/autom8_asana/persistence/exceptions.py` (SaveSessionError, SessionClosedError)
  - `src/autom8_asana/persistence/models.py` (SaveResult, SaveError)

### OUT OF SCOPE

- Modifying production source files
- Other test files
- Adding new test scenarios (only fix existing tests)

## Execution Plan

### Step 1: Read Production Source

Read these files to understand:
1. `SaveSession.preview()` -- What does it return? What structure? How to assert on it?
2. `SaveSession.commit_async()` -- How does it propagate failures into SaveSessionError?
3. `SaveSession.__aexit__` -- What cleanup does it perform on exception? Does it set `is_closed`?
4. `SaveSessionError` -- What attributes does it expose? How is it constructed from commit failures?

### Step 2: Fix RS-015 (5 tests in test_savesession_edge_cases.py)

For each test, replace `assert X is not None` with meaningful assertions:

**test_same_entity_in_different_sessions (line 78)**:
- Assert preview contains specific task GID from each session's perspective
- Example: `assert any(op.gid == "task1_gid" for op in preview1.operations)`

**test_session_isolation_prevents_cross_contamination (line 108)**:
- Assert session1 preview shows only session1's changes
- Assert session2 preview shows only session2's changes

**test_session_transitions_from_empty_to_tracked (line 199)**:
- Assert preview is empty/None before tracking
- Assert preview contains task after tracking

**test_session_retracking_same_entity_is_idempotent (line 225)**:
- Assert preview after triple-track shows exactly 1 entity (not 3)

**test_session_tracks_creates_and_modifications (line 291)**:
- Assert preview distinguishes between create and modify operation types

### Step 3: Fix RS-016 (1 test in test_savesession_edge_cases.py)

**test_session_context_manager_cleanup_on_error (line 257)**:
After the `except ValueError: pass` block, add:
```python
# Verify session is closed/faulted after error exit
assert session.is_closed  # or:
with pytest.raises(SessionClosedError):
    await session.commit_async()
```

### Step 4: Fix RS-017 (4 tests in test_savesession_partial_failures.py)

Replace manual `raise SaveSessionError(result)` with actual production code path:

```python
# Before (broken):
with pytest.raises(SaveSessionError) as exc_info:
    raise SaveSessionError(result)

# After (correct):
mock_client.tasks.update_async.return_value = failure_response
async with SaveSession(mock_client) as session:
    session.track(task)
    task.name = "modified"
    with pytest.raises(SaveSessionError) as exc_info:
        await session.commit_async()
# Now inspect exc_info.value
```

For each of the 4 tests:
1. Configure mock_client with failure return values
2. Call commit_async() instead of manually raising
3. Keep all existing exception attribute assertions (they verify the right thing, just from the wrong source)

### Step 5: Verify

After each file:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_savesession_edge_cases.py -v --tb=short

source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/test_savesession_partial_failures.py -v --tb=short
```

Final combined:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/integration/test_savesession_edge_cases.py \
  tests/integration/test_savesession_partial_failures.py \
  -v --tb=short
```

## Escalation Triggers

- If `SaveSession.preview()` return type is opaque (no documented structure), read the source and work from the actual return type. Document what you find in a code comment.
- If `commit_async()` does not raise `SaveSessionError` when the mock client returns failure, trace the error path through session.py. The mock may need to be configured at a different level (e.g., httpx response mock vs. client method mock).
- If `SaveSession.__aexit__` does not set `is_closed` or raise on reuse, check for alternative cleanup signals (faulted state, rollback flag, etc.).

## Time Budget

- Estimated: 4 hours
- ~1.5 hours reading production source (session.py, exceptions.py, models.py)
- ~1.5 hours implementing RS-015 + RS-016 (6 tests)
- ~1 hour implementing RS-017 (4 tests, mock setup is the challenge)

Commit with message prefix `test(10x):`.
