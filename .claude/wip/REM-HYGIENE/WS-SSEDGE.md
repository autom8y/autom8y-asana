# WS-SSEDGE: SaveSession Edge Cases + Partial Failures

**Objective**: Implement behavioral assertions for 5 shallow/assert-free SaveSession edge case tests, 1 cleanup verification test, and 4 self-raising exception tests across two files.

---

## Source Findings

| RS-ID | Finding | File | Severity | Tests |
|-------|---------|------|----------|-------|
| RS-015 | 5 tests have no assertions or only `assert preview is not None` | `test_savesession_edge_cases.py` | DEFECT HIGH | lines 78-135, 199-248, 291-313 |
| RS-016 | Cleanup test verifies nothing after error exit | `test_savesession_edge_cases.py` | DEFECT MED | lines 257-281 |
| RS-017 | 4 tests raise their own exceptions instead of calling production code | `test_savesession_partial_failures.py` | DEFECT HIGH | lines 50-80, 83-123, 126-156, 207-251 |

---

## File Targets

- **Test file 1**: `tests/integration/test_savesession_edge_cases.py` (RS-015, RS-016)
- **Test file 2**: `tests/integration/test_savesession_partial_failures.py` (RS-017)
- **Production source (read only)**:
  - `src/autom8_asana/persistence/session.py` (SaveSession, preview(), commit_async(), __aexit__)
  - `src/autom8_asana/persistence/exceptions.py` (SaveSessionError, SessionClosedError)

### RS-015 Tests to Fix (5 total)

| Test | Line | Current State | Required Assertion |
|------|------|--------------|-------------------|
| `test_same_entity_in_different_sessions` | 78 | `assert changes is not None` | Assert preview contains specific task GID |
| `test_session_isolation_prevents_cross_contamination` | 108 | Zero assertions | Assert session1 preview has task1 only, session2 has task2 only |
| `test_session_transitions_from_empty_to_tracked` | 199 | `assert preview is not None` | Assert preview contains tracked task GID |
| `test_session_retracking_same_entity_is_idempotent` | 225 | Zero assertions | Assert preview has exactly 1 entity after triple-track |
| `test_session_tracks_creates_and_modifications` | 291 | `assert preview is not None` | Assert preview distinguishes create vs. modify operations |

### RS-016 Test to Fix (1 total)

| Test | Line | Current State | Required Assertion |
|------|------|--------------|-------------------|
| `test_session_context_manager_cleanup_on_error` | 257 | Catches ValueError, asserts nothing about cleanup | Assert session is closed or subsequent op raises SessionClosedError |

### RS-017 Tests to Fix (4 total)

| Test | Line | Current State | Required Fix |
|------|------|--------------|-------------|
| `test_save_async_raises_savesession_error_on_failure` | 50 | Manually raises SaveSessionError | Call commit_async() with mock failure client |
| `test_save_async_error_contains_full_result` | 83 | Manually raises SaveSessionError | Call commit_async() with mock failure client |
| `test_save_async_error_message_shows_all_failures` | 126 | Manually raises SaveSessionError | Call commit_async() with mock failure client |
| `test_save_async_error_includes_docstring_example` | 207 | Manually raises SaveSessionError | Call commit_async() with mock failure client |

---

## Implementation Strategy

### RS-015 + RS-016 (test_savesession_edge_cases.py)

1. Read `SaveSession.preview()` return type in `session.py`
2. For each test, replace `assert X is not None` with assertions against the preview structure
3. For RS-016, add post-error assertion: `session.is_closed` or `pytest.raises(SessionClosedError)`

### RS-017 (test_savesession_partial_failures.py)

1. Read how `commit_async()` propagates failures into `SaveSessionError`
2. Configure mock client to return failure results
3. Replace `raise SaveSessionError(result)` with:
   ```python
   with pytest.raises(SaveSessionError) as exc_info:
       await session.commit_async()
   ```
4. Inspect `exc_info.value` for the same attributes previously checked

---

## Effort Estimate

- **Total**: ~4 hours
- **Breakdown**: ~1.5h reading production source, ~2h implementing assertions, ~0.5h verification
- **Risk**: MEDIUM -- SaveSession.preview() return type may be complex; commit_async() mock setup requires understanding error propagation

---

## Dependencies

- None. Files have zero overlap with other workstreams.

---

## Rite / Complexity

- **Rite**: 10x-dev (recommended, confirm at dispatch)
- **Complexity**: MODULE
