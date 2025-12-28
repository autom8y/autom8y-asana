# DEBT-003: Session State Atomicity - Technical Design

## Metadata

- **TDD ID**: TDD-DEBT-003
- **Status**: Draft
- **Author**: Architect Agent
- **Created**: 2025-12-28
- **PRD Reference**: DEBT-003-requirements.md
- **Related ADRs**: ADR-DEBT-003-001 (Lock Granularity), ADR-DEBT-003-002 (Track-During-Commit)

---

## Overview

This document specifies the thread-safety solution for `SaveSession._state` transitions to resolve the atomicity bugs identified in DEBT-003. The design uses a coarse-grained reentrant lock (`threading.RLock`) protecting all session state operations, with a "queue for next commit" semantic for entities tracked during an active commit.

---

## Design Decisions

### Lock Granularity

**Decision**: Coarse-grained session lock (single `threading.RLock` for all session state)

#### Analysis

| Approach | Complexity | Contention Risk | Safety Guarantee | Maintenance |
|----------|------------|-----------------|------------------|-------------|
| **Coarse (single RLock)** | Low | Low* | Complete | Simple |
| Fine (per-concern locks) | High | Very Low | Partial** | Complex |

*Contention is low because SaveSession instances are typically not shared across threads in practice.

**Fine-grained locking cannot prevent FS-002 (track-during-commit) without a commit-level lock anyway.

#### Rationale

1. **Usage Pattern**: `SaveSession` is designed as a unit-of-work per request/operation. Sharing sessions across threads is an edge case, not the primary use pattern.

2. **Simplicity**: A single lock eliminates deadlock potential and reduces cognitive load for maintainers.

3. **Performance**: Uncontended `RLock` acquisition is ~50-100ns on modern CPUs. The <1ms budget allows ~10,000-20,000 lock operations per millisecond - far more than any realistic usage.

4. **Correctness over Concurrency**: For a data persistence layer, correctness is paramount. The marginal parallelism gain from fine-grained locking does not justify the complexity and risk.

5. **ChangeTracker Scope (C-006)**: Session-level locking inherently protects `ChangeTracker` operations, avoiding the need for tracker-level synchronization.

**Decision**: Use `threading.RLock` (not `threading.Lock`)

#### Why RLock over Lock

1. **Nested Calls**: Methods like `commit_async` call `_ensure_open()`, and `track()` also calls `_ensure_open()`. If a hook registered via `on_pre_save` calls `track()` during commit, a non-reentrant lock would deadlock.

2. **Defensive Design**: RLock has negligible additional overhead but prevents an entire class of bugs.

3. **Sync Wrapper Support**: The `commit()` sync wrapper calls `commit_async()` internally. Reentrant locks prevent issues if synchronization is added at multiple levels.

---

### Track-During-Commit Semantic

**Decision**: Option B - Queue entity for next commit (not included in current batch)

#### Edge Case Analysis

| Scenario | Option A (Include) | Option B (Queue) |
|----------|-------------------|------------------|
| Track during batch execution | Must pause batch, modify, resume (complex) | Entity waits for next commit (simple) |
| Track during API calls | GID resolution incomplete, may fail | Clean separation of concerns |
| User expectation | "My track() worked" | "My track() worked, will save on next commit" |
| Implementation complexity | High (pipeline modification) | Low (existing dirty detection) |
| Predictability | Low (race determines inclusion) | High (deterministic behavior) |

#### Rationale

1. **Deterministic Behavior**: With Option B, the semantic is clear: "Entities tracked during a commit are dirty for the next commit." This is predictable and documentable.

2. **Existing Infrastructure**: The `ChangeTracker` already supports multiple commits per session (FR-UOW-007). Entities tracked during commit naturally become dirty for the next `commit_async()` call.

3. **No Pipeline Changes**: Option A would require modifying `SavePipeline.execute_with_actions()` to accept additions mid-flight, a significant complexity increase.

4. **Safety**: Option B prevents partial inclusion where some entities from a track() make it into the batch and others don't, depending on timing.

5. **Explicit Retry Path**: If a user wants entities in the same commit, they should track before calling commit. If they need a retry pattern, they call commit again.

#### Documented Behavior

```python
async with SaveSession(client) as session:
    session.track(task1)  # Will be in commit batch

    # Background thread or callback tracks task2 during commit
    commit_task = asyncio.create_task(session.commit_async())
    session.track(task2)  # May or may not be in first commit (race)
    await commit_task

    # task2 is now dirty - call commit again if needed
    await session.commit_async()  # Saves task2 if tracked during first commit
```

---

## Technical Design

### Lock Mechanism

#### Implementation

```python
import threading
from contextlib import contextmanager

class SaveSession:
    def __init__(self, client: AsanaClient, ...) -> None:
        # ... existing initialization ...
        self._state = SessionState.OPEN
        self._lock = threading.RLock()  # Protects all state operations

    @contextmanager
    def _state_lock(self) -> Generator[None, None, None]:
        """Context manager for thread-safe state operations."""
        self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()
```

#### Async Compatibility

The `threading.RLock` works correctly with async code because:

1. **GIL Release During I/O**: When `await` suspends during I/O, the lock is NOT automatically released. This is correct behavior - we WANT the lock held across the entire commit operation.

2. **No asyncio.Lock Needed**: We do not need `asyncio.Lock` because:
   - `asyncio.Lock` prevents concurrent coroutines in the same thread
   - `threading.RLock` prevents concurrent threads
   - Our requirement is thread safety, not coroutine serialization
   - Multiple coroutines in the same thread cannot truly run in parallel (no GIL release for pure Python)

3. **Lock Scope**: The lock is acquired at operation entry (`track()`, `commit_async()`) and released at exit. The entire operation is atomic from the caller's perspective.

#### Performance Characteristics

| Operation | Lock Overhead | Notes |
|-----------|---------------|-------|
| Uncontended acquire | ~50-100ns | Typical case |
| Contended acquire | ~1-10us | Waiting for release |
| Nested acquire (RLock) | ~50ns | Increment counter only |
| Release | ~30-50ns | Decrement counter |

**Total budget impact**: <1us per operation, well within <1ms requirement.

---

### Protected Operations

#### 1. `__init__` (Line 194)

No lock needed during construction - the session is not yet shared.

```python
def __init__(self, ...) -> None:
    # ... setup ...
    self._lock = threading.RLock()
    self._state = SessionState.OPEN  # Safe: no concurrent access yet
```

#### 2. `__aexit__` (Line 214)

**Protection Pattern**: Acquire lock, transition state, release lock.

```python
async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    with self._state_lock():
        self._state = SessionState.CLOSED
```

#### 3. `__exit__` (Line 231)

**Protection Pattern**: Same as `__aexit__`.

```python
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    with self._state_lock():
        self._state = SessionState.CLOSED
```

#### 4. `commit_async` (Line 786)

**Protection Pattern**: Acquire lock at entry, hold through state transition, release at exit.

```python
async def commit_async(self) -> SaveResult:
    with self._state_lock():
        self._ensure_open_locked()  # Check while holding lock

        dirty_entities = self._tracker.get_dirty_entities()
        pending_actions = list(self._pending_actions)
        # ... capture all state needed for commit ...

    # Execute pipeline (lock released - allows track() during execution)
    # This is intentional per track-during-commit semantic

    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    with self._state_lock():
        # Reset state for successful entities
        for entity in crud_result.succeeded:
            self._reset_custom_field_tracking(entity)
            self._tracker.mark_clean(entity)

        self._state = SessionState.COMMITTED

    return crud_result
```

**Note**: The lock is released during pipeline execution. This is intentional:
- Allows `track()` calls during commit (queued for next commit per RB-005)
- Prevents blocking I/O from holding the lock
- State capture is atomic, execution is not

#### 5. `track` (Line 309)

**Protection Pattern**: Full operation under lock.

```python
def track(self, entity: T, ...) -> T:
    with self._state_lock():
        self._ensure_open_locked()
        tracked = self._tracker.track(entity)
        # ... healing logic ...
        return tracked
```

#### 6. `state` property (Line 236)

**Protection Pattern**: Read under lock for memory visibility.

```python
@property
def state(self) -> str:
    with self._state_lock():
        return self._state
```

---

### `_ensure_open()` Redesign

**Current Anti-Pattern** (check-then-act):

```python
def _ensure_open(self) -> None:
    if self._state == SessionState.CLOSED:  # READ
        raise SessionClosedError()           # ACT
    # ... gap where state can change ...
```

**Redesigned Pattern** (atomic check):

```python
def _ensure_open_locked(self) -> None:
    """Check session is open. MUST be called while holding _lock.

    This method assumes the caller holds self._lock. It does not
    acquire the lock itself to allow callers to perform additional
    operations atomically.

    Raises:
        SessionClosedError: If session state is CLOSED.
    """
    if self._state == SessionState.CLOSED:
        raise SessionClosedError()
```

**Usage Pattern**:

```python
def track(self, entity: T, ...) -> T:
    with self._state_lock():
        self._ensure_open_locked()  # Check under lock
        # ... track operations also under lock ...
```

**Alternative: Atomic Check-And-Execute Context Manager**:

```python
@contextmanager
def _require_open(self) -> Generator[None, None, None]:
    """Context manager ensuring session stays open during operation.

    Acquires lock, verifies session is open, yields, then releases lock.
    The entire block is atomic with respect to state changes.

    Raises:
        SessionClosedError: If session is closed at entry.
    """
    with self._state_lock():
        if self._state == SessionState.CLOSED:
            raise SessionClosedError()
        yield
```

**Usage**:

```python
def track(self, entity: T, ...) -> T:
    with self._require_open():
        tracked = self._tracker.track(entity)
        # ... all operations atomic with state check ...
        return tracked
```

**Recommendation**: Use `_require_open()` context manager for cleaner call sites.

---

## Code Structure

### Class Modifications Outline

```python
class SaveSession:
    # New instance variable
    _lock: threading.RLock

    # Modified __init__
    def __init__(self, ...):
        # Add after other initialization
        self._lock = threading.RLock()
        self._state = SessionState.OPEN

    # New private methods
    @contextmanager
    def _state_lock(self) -> Generator[None, None, None]: ...

    @contextmanager
    def _require_open(self) -> Generator[None, None, None]: ...

    # Renamed/modified internal method
    def _ensure_open_locked(self) -> None: ...  # Replaces _ensure_open

    # Modified methods (add lock acquisition):
    # - __aexit__
    # - __exit__
    # - state property
    # - track
    # - untrack
    # - delete
    # - commit_async
    # - commit (through commit_async)
    # - All action methods (add_tag, etc.) through _require_open
```

### Files Modified

| File | Changes |
|------|---------|
| `src/autom8_asana/persistence/session.py` | Add lock, modify state access patterns |

### Files NOT Modified

| File | Reason |
|------|--------|
| `src/autom8_asana/persistence/tracker.py` | Protected by session lock |
| `src/autom8_asana/persistence/pipeline.py` | No state, receives immutable inputs |
| `src/autom8_asana/persistence/exceptions.py` | No changes needed |
| Public API | No signature changes |

---

## Performance Analysis

### Lock Overhead Budget

| Operation | Frequency | Lock Overhead | Total Impact |
|-----------|-----------|---------------|--------------|
| track() | 10-100/session | ~100ns | ~1-10us |
| commit_async() | 1-5/session | ~200ns (2 acquires) | ~1us |
| state property | 1-10/session | ~100ns | ~1us |
| __exit__ | 1/session | ~100ns | ~100ns |

**Total per session**: <20us typical, <100us worst case

**Verdict**: Well within <1ms budget (AC-006)

### Contention Analysis

| Scenario | Contention Level | Impact |
|----------|------------------|--------|
| Single-threaded (typical) | None | Uncontended lock ~100ns |
| Track from callback during commit | Low | One waiter, ~1us |
| Multi-threaded track() | Low | Short critical sections |
| Pathological: many threads | Medium | Lock serializes, but operations complete |

**Note**: High contention indicates misuse (sharing sessions across threads). The lock ensures correctness; users should create separate sessions for parallelism.

---

## Acceptance Criteria Validation

### AC-001: State Transitions Are Atomic

**Solution**: All state transitions (`_state = ...`) occur within `_state_lock()` context.

**Test Strategy**:
```python
def test_track_during_exit():
    """Concurrent track/exit: either track raises or completes atomically."""
    session = SaveSession(client)
    barrier = threading.Barrier(2)
    results = []

    def track_thread():
        barrier.wait()
        try:
            session.track(task)
            results.append("tracked")
        except SessionClosedError:
            results.append("closed")

    def exit_thread():
        barrier.wait()
        session.__exit__(None, None, None)
        results.append("exited")

    # Run threads, verify one of:
    # - ["closed", "exited"] - track saw closed state
    # - ["tracked", "exited"] - track completed before close
```

### AC-002: No Lost Tracks

**Solution**: Track-during-commit queues for next commit. Lock ensures tracker.track() completes atomically.

**Test Strategy**:
```python
async def test_no_lost_tracks():
    """Entities tracked during commit appear in get_dirty_entities after."""
    session = SaveSession(mock_client)
    session.track(task1)

    # Start commit, track during execution
    commit_future = asyncio.create_task(session.commit_async())
    await asyncio.sleep(0.001)  # Let commit start
    session.track(task2)
    await commit_future

    # task2 should be dirty for next commit
    dirty = session._tracker.get_dirty_entities()
    assert task2 in dirty or task2.gid in [e.gid for e in dirty]
```

### AC-003: No Double Commits

**Solution**: Lock is held during dirty entity capture. Second commit waits for first to release.

**Test Strategy**:
```python
async def test_no_double_commits():
    """Concurrent commits serialize correctly."""
    session = SaveSession(mock_client)
    session.track(task)

    barrier = threading.Barrier(2)
    api_calls = []

    async def commit_thread():
        barrier.wait()
        result = await session.commit_async()
        api_calls.append(result)

    # Run two commits - they should serialize
    # First gets entities, second sees clean state
```

### AC-004: State Inspection Accuracy

**Solution**: `state` property acquires lock before reading.

**Test Strategy**:
```python
def test_state_inspection_accuracy():
    """State reads reflect current state."""
    session = SaveSession(client)

    states_seen = []
    def reader():
        for _ in range(1000):
            states_seen.append(session.state)

    def writer():
        session.commit()  # Changes to COMMITTED
        session.__exit__(None, None, None)  # Changes to CLOSED

    # Verify no impossible states (e.g., CLOSED then OPEN)
```

### AC-005: Backward Compatible API

**Solution**: No public API changes. All modifications are internal.

**Test Strategy**: Full test suite regression. No new parameters, no signature changes.

### AC-006: Performance Within Tolerance

**Solution**: Lock overhead is ~100ns uncontended, <1us typical total.

**Test Strategy**:
```python
def test_performance_budget():
    """Lock overhead is within 1ms budget."""
    session = SaveSession(mock_client)

    start = time.perf_counter_ns()
    for _ in range(1000):
        session.track(Task(gid=f"temp_{_}", name="test"))
    elapsed_ns = time.perf_counter_ns() - start

    # 1000 operations should complete in <100ms (100us each)
    # This leaves massive headroom for the 1ms budget
    assert elapsed_ns < 100_000_000  # 100ms
```

---

## Test Strategy

### Unit Tests

| Test | Validates |
|------|-----------|
| `test_state_lock_prevents_concurrent_mutation` | AC-001 |
| `test_track_during_commit_queues_for_next` | AC-002, RB-005 |
| `test_concurrent_commits_serialize` | AC-003, RB-004 |
| `test_state_property_reads_current_value` | AC-004, RB-003 |
| `test_existing_api_unchanged` | AC-005 |
| `test_lock_overhead_within_budget` | AC-006 |

### Concurrency Tests (threading.Barrier synchronized)

| Test | Failure Scenario |
|------|------------------|
| `test_track_during_exit_race` | FS-001 |
| `test_track_during_commit_race` | FS-002 |
| `test_state_inspection_during_commit` | FS-003 |
| `test_double_commit_race` | FS-004 |

### Integration Tests

| Test | Validates |
|------|-----------|
| `test_sync_async_interop` | C-003 |
| `test_reentrant_lock_with_hooks` | RLock decision |
| `test_thread_pool_executor_usage` | Real-world pattern |

---

## Migration Notes

### Backward Compatibility

| Aspect | Status | Notes |
|--------|--------|-------|
| Public method signatures | Unchanged | No API changes |
| Return types | Unchanged | SaveResult, etc. |
| Exception types | Unchanged | SessionClosedError timing may change |
| Behavior: single-threaded | Unchanged | Lock is transparent |
| Behavior: multi-threaded | Improved | Now thread-safe |

### Deprecation Path

None required. This is a bugfix, not a feature change.

### Documentation Updates

Update docstrings to note thread-safety:

```python
class SaveSession:
    """Unit of Work pattern for batched Asana operations.

    Thread Safety:
        SaveSession is thread-safe. Multiple threads may call track(),
        commit_async(), and other methods concurrently on the same
        instance. However, for optimal performance, prefer one session
        per thread/task.

        Entities tracked during an active commit will be included in
        the next commit, not the current one.
    """
```

---

## ADRs

### ADR-DEBT-003-001: Lock Granularity

**Status**: Accepted

**Context**: DEBT-003 requires thread-safe state transitions. Options: coarse-grained (single lock) vs fine-grained (per-concern locks).

**Decision**: Use coarse-grained `threading.RLock` protecting all session state.

**Rationale**: Sessions are rarely shared across threads. Simplicity and correctness outweigh parallelism gains.

**Consequences**:
- Positive: Simple implementation, complete safety, easy maintenance
- Negative: Theoretical serialization under high contention (unlikely in practice)

### ADR-DEBT-003-002: Track-During-Commit Semantic

**Status**: Accepted

**Context**: Per RB-005, track() during commit must not silently lose entities. Options: include in current batch vs queue for next.

**Decision**: Queue entity for next commit.

**Rationale**: Deterministic behavior, no pipeline changes, leverages existing multi-commit support.

**Consequences**:
- Positive: Predictable, simple implementation, no silent failures
- Negative: Users must call commit() again if they want immediate persistence
- Neutral: Requires documentation update

---

## Open Items

None. All design decisions are resolved.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-28 | Architect Agent | Initial design |
