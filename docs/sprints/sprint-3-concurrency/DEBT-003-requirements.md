# DEBT-003: Session State Atomicity Requirements

**Sprint**: Sprint 3 - Concurrency & Refactoring
**Session**: session-20251228-121556-d4def705
**Location**: `src/autom8_asana/persistence/session.py`
**Priority**: High (concurrency bug in production path)

---

## Executive Summary

The `SaveSession._state` attribute transitions (OPEN -> COMMITTED -> CLOSED) are not atomic. Concurrent operations can observe or modify session state in an inconsistent window, leading to race conditions where operations may execute against a session in an unexpected state or state transitions may be lost.

---

## Current Behavior

### State Machine Definition (Lines 47-58)

```python
class SessionState:
    """Internal state machine for SaveSession."""
    OPEN = "open"
    COMMITTED = "committed"
    CLOSED = "closed"
```

### State Transition Points

1. **`__init__`**: `self._state = SessionState.OPEN` (line 194)
2. **`__aexit__`**: `self._state = SessionState.CLOSED` (line 214)
3. **`__exit__`**: `self._state = SessionState.CLOSED` (line 231)
4. **`commit_async`**: `self._state = SessionState.COMMITTED` (line 786)

### State Read Points

1. **`state` property**: `return self._state` (line 244)
2. **`_ensure_open`**: `if self._state == SessionState.CLOSED` (line 1404)

### Why This Is Problematic

The current implementation has two distinct issues:

**Issue 1: Non-Atomic Read-Modify-Write**

The `_ensure_open()` check (line 1404) performs a check-then-act pattern:
```python
def _ensure_open(self) -> None:
    if self._state == SessionState.CLOSED:  # READ
        raise SessionClosedError()           # CONDITIONAL ACT
    # ... operation proceeds                 # IMPLICIT ACT
```

Between the read of `_state` and the subsequent operation, another thread can:
- Close the session via `__exit__`
- Complete a commit, changing state to COMMITTED

**Issue 2: Non-Atomic State Transitions**

The state assignment `self._state = SessionState.COMMITTED` (line 786) occurs AFTER all the commit work but BEFORE the method returns. If concurrent operations check state during commit, they see OPEN when commit is partially complete.

**Issue 3: State Inspection Under Concurrency**

The `state` property (line 244) returns the raw `_state` without synchronization. Concurrent readers can see:
- Stale values (CPU cache coherency)
- Partially updated values (torn reads on some architectures)
- Values inconsistent with the session's actual operational state

---

## Failure Scenarios

### FS-001: Track During Exit (Race Condition)

**Conditions**:
- Thread A: Exiting context manager (`__exit__`)
- Thread B: Calling `track()` on same session

**Sequence**:
```
T1 [Thread B]: _ensure_open() reads _state == OPEN
T2 [Thread A]: __exit__ sets _state = CLOSED
T3 [Thread B]: track() executes tracker operations on CLOSED session
T4 [Thread B]: Entity tracked but never committed (silently lost)
```

**Impact**: Data loss - tracked entities are never persisted.

### FS-002: Concurrent Commit State (Lost Update)

**Conditions**:
- Thread A: Executing `commit_async()`
- Thread B: Executing `track()` during commit

**Sequence**:
```
T1 [Thread A]: commit_async begins, _state == OPEN
T2 [Thread A]: get_dirty_entities() captures snapshot
T3 [Thread B]: track() adds new entity (state still OPEN)
T4 [Thread A]: execute pipeline with original snapshot
T5 [Thread A]: _state = COMMITTED
T6 [Thread B]: New entity not in committed batch (silently lost)
```

**Impact**: Data loss - entities tracked during commit window are silently not persisted.

### FS-003: State Inspection Inconsistency

**Conditions**:
- Thread A: Inspecting `session.state` for conditional logic
- Thread B: Committing or closing

**Sequence**:
```
T1 [Thread A]: if session.state == SessionState.OPEN
T2 [Thread B]: commit_async completes, _state = COMMITTED
T3 [Thread A]: assumes OPEN, makes decisions based on stale state
```

**Impact**: Logic errors - caller acts on incorrect state information.

### FS-004: Double Commit Race

**Conditions**:
- Thread A: Calling `commit_async()`
- Thread B: Also calling `commit_async()`

**Sequence**:
```
T1 [Thread A]: _ensure_open() passes
T2 [Thread B]: _ensure_open() passes (both see OPEN)
T3 [Thread A]: get_dirty_entities()
T4 [Thread B]: get_dirty_entities() (same entities!)
T5 [Thread A]: execute pipeline, entities succeed
T6 [Thread A]: mark_clean() for entities
T7 [Thread B]: execute pipeline, entities already clean or with stale snapshot
T8 [Thread B]: Unpredictable results (duplicate API calls, state corruption)
```

**Impact**: API abuse, potential duplicate operations in Asana, state corruption.

---

## Required Behavior

### RB-001: Atomic State Transitions

State transitions MUST be atomic operations. A state change must be immediately visible to all threads, and no intermediate states may be observed.

### RB-002: Atomic Check-Then-Act

The `_ensure_open()` pattern MUST be atomic. The check and subsequent operation authorization must occur as an indivisible unit.

### RB-003: Consistent State Reads

Reading `state` property MUST return a value consistent with the session's actual operational state at that moment.

### RB-004: Commit Exclusion

At most one `commit_async()` operation MAY execute at a time per session. Concurrent commits must be serialized or the second must fail fast.

### RB-005: Track-During-Commit Safety

If `track()` is called during `commit_async()`:
- EITHER the entity is included in the current commit batch
- OR `track()` returns successfully but entity is queued for next commit
- NOT silently lost

**Design Decision Required**: The architect must decide which semantic is appropriate.

---

## Acceptance Criteria

### AC-001: State Transitions Are Atomic

**Test**: Concurrent threads calling `__exit__` and `track()` on same session
**Expected**: Either `track()` raises `SessionClosedError` OR `track()` completes and entity is tracked. No silent failures.
**Verification**: Unit test with `threading.Barrier` to synchronize race window.

### AC-002: No Lost Tracks

**Test**: Thread A commits while Thread B tracks new entities
**Expected**: Tracked entities are either in current commit OR pending for next commit. None silently lost.
**Verification**: After concurrent commit/track, verify `get_dirty_entities()` or commit results account for all tracked entities.

### AC-003: No Double Commits

**Test**: Two threads call `commit_async()` simultaneously
**Expected**: One completes successfully, other either waits and succeeds (if new dirty entities) OR raises/returns indicating concurrent commit in progress.
**Verification**: Unit test with `threading.Barrier`, verify batch API called exactly once per entity.

### AC-004: State Inspection Accuracy

**Test**: Thread A reads `session.state` while Thread B commits
**Expected**: State accurately reflects session status at read time (not stale).
**Verification**: Memory ordering test with read barriers.

### AC-005: Backward Compatible API

**Test**: Existing single-threaded usage patterns
**Expected**: No behavioral changes for single-threaded use. All existing tests pass.
**Verification**: Full test suite regression.

### AC-006: Performance Within Tolerance

**Test**: Benchmark session operations with locking
**Expected**: Lock contention adds < 1ms latency per operation in typical use (single-threaded).
**Verification**: Timing comparison before/after.

---

## Constraints

### C-001: Backward Compatibility

The public API (`track()`, `commit()`, `commit_async()`, `state` property) MUST NOT change signatures. Internal implementation changes only.

### C-002: Python GIL Considerations

While CPython's GIL provides some protection for simple operations, it does NOT guarantee atomicity of:
- Check-then-act patterns
- Multi-statement sequences
- Async operations (where GIL is released during I/O)

The fix must work correctly regardless of GIL behavior.

### C-003: Async/Sync Dual Support

Both sync (`commit()`) and async (`commit_async()`) paths must be protected. Lock mechanism must work with both `threading` and `asyncio`.

### C-004: Performance Budget

Lock acquisition must not significantly impact single-threaded performance:
- Target: < 1ms additional latency per operation
- Lock should be uncontended in typical single-threaded use

### C-005: No External Dependencies

Solution should use Python standard library (`threading.Lock`, `threading.RLock`, `asyncio.Lock`) without introducing new dependencies.

### C-006: ChangeTracker Scope

The `ChangeTracker` class has its own internal dictionaries that are also subject to concurrent access. The atomicity fix should consider whether `ChangeTracker` needs its own synchronization or if session-level locking is sufficient.

---

## Implementation Notes

### Lock Granularity Options

**Option A: Coarse-Grained Session Lock**
- Single lock protects all session state
- Simple, prevents all races
- May have higher contention in pathological concurrent use

**Option B: Fine-Grained Locks**
- Separate locks for state, tracker, actions
- More complex, allows more parallelism
- Overkill if concurrent session use is rare

**Recommendation**: Start with coarse-grained (Option A). SaveSession is typically not shared across threads. Fine-grained locking adds complexity without proven benefit.

### Async Lock Consideration

`commit_async()` is async and releases the GIL during I/O. If we use `threading.Lock`, we must ensure it's held across the async operations OR use `asyncio.Lock` for async paths.

**Consideration**: May need dual locking strategy:
- `threading.RLock` for sync operations
- `asyncio.Lock` for async commit serialization

### State Machine Formalization

Consider formalizing state transitions to prevent invalid transitions:
```
OPEN -> COMMITTED (via commit)
OPEN -> CLOSED (via exit without commit)
COMMITTED -> COMMITTED (via subsequent commit)
COMMITTED -> CLOSED (via exit)
```

Invalid transitions (should raise):
- CLOSED -> anything
- Any state -> OPEN

### Existing Test Coverage

The `test_concurrency.py` file has tests for:
- Session isolation (different sessions)
- Thread safety of `ChangeTracker`
- Concurrent commits (different sessions)

Missing test coverage:
- Same session concurrent operations (the actual bug)
- Track during commit window
- State inspection under concurrency

---

## Out of Scope

### OS-001: Distributed Locking

This fix addresses single-process thread safety. Distributed locking (across processes/machines) is out of scope.

### OS-002: ChangeTracker Refactoring

While `ChangeTracker` may have its own concurrency concerns, a full refactor of its internals is out of scope. Session-level locking should provide sufficient protection for typical use.

### OS-003: API Changes

No changes to the public SaveSession API. This is a behavior fix, not an interface change.

### OS-004: Async Context Manager Concurrency

The async context manager (`__aenter__`/`__aexit__`) concurrent entry/exit is technically possible but is a programming error. We do not attempt to protect against misuse patterns.

---

## Traceability

| Requirement | Source | Rationale |
|-------------|--------|-----------|
| RB-001 | Code analysis (lines 214, 231, 786) | Direct state mutations without sync |
| RB-002 | Code analysis (line 1404) | Check-then-act pattern |
| RB-003 | Code analysis (line 244) | Unsynchronized read |
| RB-004 | FS-004 | Double commit causes undefined behavior |
| RB-005 | FS-002 | Track during commit is valid but currently lossy |
| C-002 | Python semantics | GIL does not prevent all races |
| C-003 | Existing API | Session supports both sync and async |

---

## Stakeholder Confirmation

- [ ] Architect confirms lock granularity decision
- [ ] Architect confirms track-during-commit semantic (RB-005)
- [ ] Principal Engineer confirms performance budget is achievable
- [ ] QA Adversary confirms acceptance criteria are testable

---

## Revision History

| Date | Author | Change |
|------|--------|--------|
| 2025-12-28 | Requirements Analyst | Initial requirements document |
