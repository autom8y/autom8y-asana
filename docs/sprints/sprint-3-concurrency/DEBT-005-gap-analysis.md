# DEBT-005: Concurrent track() Race Condition - Gap Analysis

**Sprint**: Sprint 3 - Concurrency & Refactoring
**Phase**: Diagnostic Verification
**Analyst**: QA Adversary
**Date**: 2025-12-28

---

## Executive Summary

**VERDICT: ALREADY FIXED (with caveats)**

DEBT-003's `threading.RLock` implementation in `SaveSession` **does protect** `ChangeTracker.track()` from concurrent corruption. The primary `track()` operation and all recursive tracking happen within the session lock. However, there are **read-only inspection methods** that access the tracker without lock protection, which could cause **torn reads** but not data corruption.

| Aspect | Status | Notes |
|--------|--------|-------|
| `track()` protected | YES | Lines 390-391, uses `_require_open()` |
| `_track_recursive()` protected | YES | Called only within `track()`, inherits lock |
| `ChangeTracker.track()` direct bypass | NO | Not exposed publicly, only via session methods |
| Read-only methods protected | NO | `get_changes()`, `get_state()`, etc. not locked |
| Data corruption possible | NO | Only mutation paths are protected |

**Recommendation**: Close DEBT-005. The race condition is resolved. Optionally track read-consistency as a separate low-priority item.

---

## Detailed Analysis

### Question 1: Is `track()` always called within the `_require_open()` context?

**Answer: YES**

The `SaveSession.track()` method wraps all operations in `_require_open()`:

```python
# session.py lines 390-426
def track(self, entity: T, ...) -> T:
    # TDD-DEBT-003: Full operation under lock
    with self._require_open():
        tracked = self._tracker.track(entity)
        # ... logging, healing, recursive tracking ...
        return tracked
```

The `_require_open()` context manager acquires the session lock and verifies the session is open:

```python
# session.py lines 1463-1484
@contextmanager
def _require_open(self) -> Generator[None, None, None]:
    with self._state_lock():
        if self._state == SessionState.CLOSED:
            raise SessionClosedError()
        yield
```

This means the entire `track()` operation, including the call to `self._tracker.track(entity)`, executes while holding `self._lock`.

---

### Question 2: Can external code call `ChangeTracker.track()` directly?

**Answer: NO (in production)**

The `ChangeTracker` class is:
1. **Not part of the public API** - It is an internal implementation detail
2. **Only instantiated by SaveSession** - Line 162: `self._tracker = ChangeTracker()`
3. **Not exposed publicly** - No `session.tracker` property exists
4. **Module-private by convention** - Located in `persistence/tracker.py`

External code cannot access `ChangeTracker` without:
- Importing the internal module directly (violation of API contract)
- Accessing `session._tracker` (underscore prefix signals private)

**Test code** does instantiate `ChangeTracker` directly for unit testing, but this is isolated and does not represent production usage.

---

### Question 3: Does `ChangeTracker` have internal mutable state that could be corrupted?

**Answer: YES, but protected by session lock**

`ChangeTracker` maintains five mutable dictionaries:

```python
# tracker.py lines 34-47
def __init__(self) -> None:
    self._snapshots: dict[str, dict[str, Any]] = {}
    self._states: dict[str, EntityState] = {}
    self._entities: dict[str, AsanaResource] = {}
    self._gid_transitions: dict[str, str] = {}
    self._entity_to_key: dict[int, str] = {}
```

The `track()` method modifies all of these:

```python
# tracker.py lines 114-126 (new entity tracking)
self._entities[key] = entity
self._entity_to_key[id(entity)] = key
self._snapshots[key] = entity.model_dump()
self._states[key] = EntityState.NEW  # or CLEAN
```

Without synchronization, concurrent calls could:
- Interleave dictionary updates
- Corrupt the reverse lookup mapping
- Create inconsistent snapshot/state/entity references

**However**, since all mutation paths go through `SaveSession.track()`, `untrack()`, or `delete()`, and these methods hold the session lock, concurrent corruption is **prevented**.

---

### Question 4: Are there any code paths to `track()` that are NOT protected by the lock?

**Answer: NO for mutation paths, YES for read paths**

#### Protected Mutation Paths

| Method | Protection | Evidence |
|--------|------------|----------|
| `session.track()` | `_require_open()` | Line 390 |
| `session.untrack()` | `_require_open()` | Line 470 |
| `session.delete()` | `_require_open()` | Line 500 |
| `_track_recursive()` | Inherits from `track()` | Called at line 424 |
| `commit_async()` state capture | `_state_lock()` | Line 729-737 |
| `commit_async()` mark_clean | `_state_lock()` | Line 822-830 |

#### Unprotected Read Paths

The following `SaveSession` methods call `ChangeTracker` methods **without** holding the lock:

| Session Method | Tracker Call | Line | Risk |
|----------------|--------------|------|------|
| `get_changes()` | `_tracker.get_changes(entity)` | 541 | Torn read |
| `get_state()` | `_tracker.get_state(entity)` | 566 | Torn read |
| `find_by_gid()` | `_tracker.find_by_gid(gid)` | 588 | Torn read |
| `is_tracked()` | `_tracker.is_tracked(gid)` | 607 | Torn read |
| `get_dependency_order()` | `_tracker.get_dirty_entities()` | 630 | Torn read |
| `preview()` | `_tracker.get_dirty_entities()` | 667 | Torn read |
| `_invalidate_cache_for_results()` | `_tracker.find_by_gid(gid)` | 1605 | Torn read |

**"Torn read" means**: The method may see partially updated state if another thread is modifying the tracker. For example, `find_by_gid()` might return `None` during a concurrent `track()` that is mid-way through adding the entity.

#### Why Torn Reads Are Not Critical

1. **Read methods do not modify state** - No corruption occurs
2. **Python's GIL provides basic atomicity** - Dictionary lookups are atomic
3. **Typical usage is single-threaded** - Sessions are unit-of-work per request
4. **DEBT-003 validation accepted similar issues** - See DEF-002, DEF-003

---

## Code Path Analysis

### `_track_recursive()` Deep Dive

The `_track_recursive()` method is called from two places:

1. **From `track()`** (line 424) - Inside `_require_open()` context, **PROTECTED**
2. **Self-recursion** (lines 443, 452) - Still inside original lock, **PROTECTED**

```python
# session.py lines 428-452
def _track_recursive(self, entity: AsanaResource) -> None:
    """Recursively track all children in entity's holders."""
    holder_key_map = getattr(entity, "HOLDER_KEY_MAP", None)
    if holder_key_map:
        for holder_name in holder_key_map:
            holder = getattr(entity, f"_{holder_name}", None)
            if holder is not None:
                self._tracker.track(holder)  # <-- Direct tracker call
                self._track_recursive(holder)

    for child_attr in ("_contacts", "_units", "_offers", "_processes"):
        children = getattr(entity, child_attr, None)
        if children and isinstance(children, list):
            for child in children:
                self._tracker.track(child)  # <-- Direct tracker call
                self._track_recursive(child)
```

**Important**: These calls to `self._tracker.track()` bypass `session.track()` but **do not bypass the lock** because they execute within the lock acquired by the original `session.track()` call.

### Pipeline Access to Tracker

The `SavePipeline` receives a `ChangeTracker` reference at construction:

```python
# pipeline.py line 108
self._tracker = tracker
```

It calls tracker methods during `preview()` and `execute()`:

```python
# pipeline.py lines 320, 363, 531, 537
state = self._tracker.get_state(entity)
changed_fields = self._tracker.get_changed_fields(entity)
```

These calls happen **outside the session lock** (the lock is released during I/O per TDD-DEBT-003 lines 763-764). However:

1. **State capture is atomic** - Dirty entities are captured under lock (line 734)
2. **Pipeline operates on captured list** - No new entities added mid-execution
3. **Read-only operations** - Pipeline only reads tracker state

---

## DEBT-005 Original Problem Statement

> "The `track()` method modifies entity snapshots without synchronization. Concurrent calls to track the same entity can corrupt the snapshot state."

### Was This Fixed?

**YES**. The specific race condition is resolved:

1. **`track()` is synchronized** - All calls go through `_require_open()` which holds `self._lock`
2. **Same entity tracking is idempotent** - Tracker returns existing entity if GID matches
3. **Snapshot capture is atomic** - `entity.model_dump()` happens under lock
4. **No concurrent modification** - Lock serializes all tracker mutations

---

## Remaining Considerations

### Low-Severity: Read Consistency

The unprotected read methods (`get_changes()`, `get_state()`, etc.) could return inconsistent data if called concurrently with `track()`. This is:

- **Low risk**: Typical usage is single-threaded
- **Low impact**: No data corruption, just stale/partial reads
- **Consistent with DEBT-003 validation**: Similar issues in DEF-002/DEF-003 were accepted

### Recommendation

If read consistency becomes a requirement, add lock protection:

```python
def get_state(self, entity: AsanaResource) -> EntityState:
    with self._state_lock():
        return self._tracker.get_state(entity)
```

This is **not blocking** for DEBT-005 closure.

---

## Conclusion

**ALREADY FIXED**: DEBT-003's RLock implementation protects `ChangeTracker.track()` from concurrent corruption.

| Question | Answer |
|----------|--------|
| Is `track()` protected? | YES |
| Can external code bypass? | NO |
| Is mutable state protected? | YES |
| Are there unprotected paths? | NO (for mutations) |

**Recommendation**: Close DEBT-005 as resolved by DEBT-003. Document the read-consistency limitations as a known caveat in thread-safety documentation.

---

## Attestation

| Artifact | Path |
|----------|------|
| Session Implementation | `/src/autom8_asana/persistence/session.py` |
| Tracker Implementation | `/src/autom8_asana/persistence/tracker.py` |
| Pipeline Implementation | `/src/autom8_asana/persistence/pipeline.py` |
| DEBT-003 TDD | `/docs/sprints/sprint-3-concurrency/DEBT-003-tdd.md` |
| DEBT-003 Validation | `/docs/sprints/sprint-3-concurrency/DEBT-003-validation.md` |
| This Analysis | `/docs/sprints/sprint-3-concurrency/DEBT-005-gap-analysis.md` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-28 | QA Adversary | Initial gap analysis |
