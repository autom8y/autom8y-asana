# TDD: SaveSession Reliability (Initiative F)

## Metadata

| Field | Value |
|-------|-------|
| **TDD ID** | TDD-HARDENING-F |
| **Status** | Draft |
| **Author** | Architect |
| **Created** | 2025-12-16 |
| **Last Updated** | 2025-12-16 |
| **PRD Reference** | [PRD-HARDENING-F](/docs/requirements/PRD-HARDENING-F.md) |
| **Spike Reference** | [SPIKE-HARDENING-F](/docs/initiatives/SPIKE-HARDENING-F.md) |
| **Related ADRs** | ADR-0078, ADR-0079, ADR-0080 |

---

## 1. Overview

This TDD specifies the technical design for improving SaveSession reliability by:

1. **Replacing `id(entity)` tracking with GID-based entity identity** - Ensures the same Asana resource is tracked once regardless of how many Python objects reference it, eliminating duplicate operations and data loss from race conditions.

2. **Adding retryable error classification** - Enhances `SaveError` with an `is_retryable` property to help users implement appropriate error recovery strategies.

3. **Providing entity lookup by GID** - New `find_by_gid()` and `is_tracked()` methods enable efficient entity lookup within a session.

The design prioritizes surgical modifications with full backward compatibility.

---

## 2. Requirements Summary

### 2.1 Entity Identity (MUST HAVE)

| ID | Requirement | Design Response |
|----|-------------|-----------------|
| FR-EID-001 | Use GID as primary key for entities with GID | Section 2.1: `_get_key()` method |
| FR-EID-002 | Use `__id_{id(entity)}` for entities without GID | Section 2.1: Fallback key pattern |
| FR-EID-003 | Support `temp_*` prefixed GIDs as valid keys | Section 2.2: Temp GID handling |
| FR-EID-004 | Re-key entity when temp GID becomes real GID | Section 2.2: `update_gid()` method |
| FR-EID-005 | Maintain `_gid_transitions` map for temp-to-real lookup | Section 2.2: Transition tracking |
| FR-EID-006 | Update entity reference when same GID tracked twice | Section 2.1: Duplicate detection |
| FR-EID-007 | Log warning at DEBUG level on duplicate track | Section 2.1: Observability |
| FR-EID-008 | Preserve backward-compatible public API | Section 2.5: Compatibility matrix |

### 2.2 Entity Lookup (COULD HAVE)

| ID | Requirement | Design Response |
|----|-------------|-----------------|
| FR-EL-001 | Provide `find_by_gid(gid)` method | Section 2.4: Entity lookup API |
| FR-EL-002 | Return entity for real GID | Section 2.4: Direct lookup |
| FR-EL-003 | Return entity for transitioned temp GID | Section 2.4: Transition map lookup |
| FR-EL-004 | Return None for unknown GID | Section 2.4: None fallback |
| FR-EL-005 | Provide `is_tracked(gid)` method | Section 2.4: Boolean helper |

### 2.3 Failure Handling (SHOULD HAVE)

| ID | Requirement | Design Response |
|----|-------------|-----------------|
| FR-FH-001 | SaveError provides `is_retryable` property | Section 2.3: Property implementation |
| FR-FH-002 | 429 errors classified as retryable | Section 2.3: Classification table |
| FR-FH-003 | 5xx errors classified as retryable | Section 2.3: Classification table |
| FR-FH-004 | 4xx errors (except 429) not retryable | Section 2.3: Classification table |
| FR-FH-005 | SaveResult provides `get_failed_entities()` | Section 2.3: Convenience method |
| FR-FH-006 | SaveResult provides `get_retryable_errors()` | Section 2.3: Filter method |
| FR-FH-007 | SaveResult provides `failed_count` property | Section 2.3: Property |

### 2.4 Non-Functional Requirements

| ID | Requirement | Design Response |
|----|-------------|-----------------|
| NFR-001 | track() latency < 1ms p99 | O(1) dict operations only |
| NFR-002 | GID lookup O(1) | Direct dict access |
| NFR-003 | No memory leaks in _gid_transitions | Bounded by session lifetime |
| NFR-004 | Python 3.10+ compatibility | Standard library only |
| NFR-005 | Test coverage >= 90% | Section 5: Testing strategy |

---

## 3. System Context

### 3.1 Component Interaction

```
                    +----------------+
                    |   User Code    |
                    +-------+--------+
                            |
                            v
                    +-------+--------+
                    |  SaveSession   |
                    +-------+--------+
                            |
            +---------------+---------------+
            |               |               |
            v               v               v
    +-------+-------+  +----+----+  +-------+-------+
    | ChangeTracker |  |  Graph  |  |    Pipeline   |
    | (GID-based)   |  |         |  |               |
    +---------------+  +---------+  +-------+-------+
                                            |
                                            v
                                    +-------+-------+
                                    |  BatchClient  |
                                    +---------------+
```

### 3.2 Affected Components

| Component | File | Change Type |
|-----------|------|-------------|
| ChangeTracker | `persistence/tracker.py` | **Major** - Replace identity strategy |
| SaveError | `persistence/models.py` | **Minor** - Add `is_retryable` property |
| SaveResult | `persistence/models.py` | **Minor** - Add convenience methods |
| SaveSession | `persistence/session.py` | **Minor** - Expose new tracker methods |
| SavePipeline | `persistence/pipeline.py` | **Minor** - Call `update_gid()` on CREATE |

---

## 4. Design

### 4.1 GID-Based Entity Registry (ADR-0078)

The core change replaces the `id(entity)` keying strategy with GID-based keying.

#### 4.1.1 Key Generation Strategy

```python
def _get_key(self, entity: AsanaResource) -> str:
    """Generate tracking key for entity.

    Priority:
    1. Use entity's GID if it exists (works for real and temp_ GIDs)
    2. Fall back to f"__id_{id(entity)}" for truly GID-less entities
    """
    gid = getattr(entity, 'gid', None)
    if gid:
        return gid  # Works for both real GIDs and temp_ GIDs
    # Edge case: entity has no GID at all
    return f"__id_{id(entity)}"
```

**Decision**: Use `__id_` prefix (not bare `id()`) to avoid collision with numeric-looking GIDs.

#### 4.1.2 Data Structures

```python
class ChangeTracker:
    def __init__(self) -> None:
        # Primary storage: key -> entity reference
        self._entities: dict[str, AsanaResource] = {}
        # key -> snapshot at track time
        self._snapshots: dict[str, dict[str, Any]] = {}
        # key -> lifecycle state
        self._states: dict[str, EntityState] = {}
        # Maps temp_gid -> real_gid after creation
        self._gid_transitions: dict[str, str] = {}
        # Reverse lookup: id(entity) -> key (for entity-to-key lookup)
        self._entity_to_key: dict[int, str] = {}
```

**Type change**: Keys change from `int` (Python id) to `str` (GID or fallback).

#### 4.1.3 Duplicate Detection on Track

```python
def track(self, entity: AsanaResource) -> None:
    key = self._get_key(entity)

    # Check for existing entity with same GID
    if key in self._entities:
        existing = self._entities[key]
        if existing is not entity:
            # Same GID, different object - this is a re-fetch
            if self._log:
                self._log.debug(
                    "tracker_duplicate_gid",
                    gid=key,
                    message="Entity re-tracked with same GID; updating reference",
                )
            # Update to use new entity reference, keep original snapshot
            old_id = id(existing)
            if old_id in self._entity_to_key:
                del self._entity_to_key[old_id]
        else:
            # Same entity object, already tracked - idempotent
            return

    self._entities[key] = entity
    self._entity_to_key[id(entity)] = key

    # Only capture snapshot on first track (preserve original state)
    if key not in self._snapshots:
        self._snapshots[key] = entity.model_dump()

    # Determine initial state based on GID
    gid = entity.gid
    if not gid or gid.startswith("temp_"):
        self._states[key] = EntityState.NEW
    else:
        self._states[key] = EntityState.CLEAN
```

**Behavior change**: When the same GID is tracked twice:
- Entity reference is updated to the new object
- Original snapshot is preserved (tracks changes from first track)
- DEBUG log emitted (FR-EID-007)

#### 4.1.4 Sequence Diagram: Duplicate GID Tracking

```
User                  SaveSession          ChangeTracker
 |                        |                     |
 |-- track(task_a) ------>|                     |
 |                        |-- track(task_a) --->|
 |                        |                     |-- _get_key() -> "12345"
 |                        |                     |-- store in _entities["12345"]
 |                        |                     |-- capture snapshot
 |                        |                     |-- set state = CLEAN
 |                        |<----- ok -----------|
 |<----- ok --------------|                     |
 |                        |                     |
 |-- task_a.name = "A" -->|                     |
 |                        |                     |
 |-- track(task_b) ------>| (same GID "12345")  |
 |                        |-- track(task_b) --->|
 |                        |                     |-- _get_key() -> "12345"
 |                        |                     |-- found existing, different object
 |                        |                     |-- log DEBUG "duplicate_gid"
 |                        |                     |-- update _entities["12345"] = task_b
 |                        |                     |-- preserve original snapshot
 |                        |<----- ok -----------|
 |<----- ok --------------|                     |
 |                        |                     |
 |-- task_b.notes = "B" ->|                     |
 |                        |                     |
 |-- commit_async() ----->|                     |
 |                        |-- get_dirty_entities() ->|
 |                        |                     |-- compare task_b to original snapshot
 |                        |                     |-- detect name AND notes changes
 |                        |<--- [task_b] -------|
 |                        |                     |
 |                        |-- execute UPDATE "12345" with both changes
```

**Key insight**: Because the snapshot was captured from `task_a` when it was first tracked, and `task_b` is now the reference, the diff detects both `task_a.name` and `task_b.notes` changes.

### 4.2 Temp GID Handling

#### 4.2.1 Temp GID Recognition

Temp GIDs follow the pattern `temp_{id}` and are used for entities that haven't been created yet.

```python
def track(self, entity: AsanaResource) -> None:
    # ... key generation ...

    gid = entity.gid
    if not gid or gid.startswith("temp_"):
        self._states[key] = EntityState.NEW
    else:
        self._states[key] = EntityState.CLEAN
```

#### 4.2.2 GID Transition on CREATE Success

After successful CREATE, the pipeline calls `update_gid()` to re-key:

```python
def update_gid(self, entity: AsanaResource, old_key: str, new_gid: str) -> None:
    """Re-key entity after temp GID becomes real GID.

    Called by pipeline after successful CREATE operation.
    Maintains transition map for temp GID lookups.
    """
    if old_key not in self._entities:
        return

    # Transfer all state to new key
    self._entities[new_gid] = self._entities.pop(old_key)
    self._snapshots[new_gid] = self._snapshots.pop(old_key)
    self._states[new_gid] = self._states.pop(old_key)

    # Record transition for lookup
    self._gid_transitions[old_key] = new_gid

    # Update reverse lookup
    self._entity_to_key[id(entity)] = new_gid
```

#### 4.2.3 Sequence Diagram: Temp GID Transition

```
User                  SaveSession          ChangeTracker          Pipeline
 |                        |                     |                     |
 |-- task = Task(temp_1) -|                     |                     |
 |-- track(task) -------->|                     |                     |
 |                        |-- track(task) ----->|                     |
 |                        |                     |-- key = "temp_1"    |
 |                        |                     |-- state = NEW       |
 |                        |<----- ok -----------|                     |
 |<----- ok --------------|                     |                     |
 |                        |                     |                     |
 |-- commit_async() ----->|                     |                     |
 |                        |-------- execute ----------------------->  |
 |                        |                     |                     |
 |                        |                     |   CREATE succeeds   |
 |                        |                     |   real_gid = "99999"|
 |                        |                     |                     |
 |                        |                     |<- update_gid -------|
 |                        |                     |   ("temp_1","99999")|
 |                        |                     |                     |
 |                        |                     |-- re-key to "99999" |
 |                        |                     |-- record transition |
 |                        |                     |   temp_1 -> 99999   |
 |                        |<----- result -------|                     |
 |<----- result ----------|                     |                     |
 |                        |                     |                     |
 |-- find_by_gid("temp_1")|                     |                     |
 |                        |-- find_by_gid ----->|                     |
 |                        |                     |-- lookup "temp_1"   |
 |                        |                     |-- not in _entities  |
 |                        |                     |-- check transitions |
 |                        |                     |-- "temp_1" -> "99999"|
 |                        |                     |-- return _entities["99999"]
 |                        |<----- task ---------|                     |
 |<----- task ------------|                     |                     |
```

### 4.3 Failure Handling Enhancement (ADR-0079)

#### 4.3.1 SaveError.is_retryable Property

```python
@dataclass
class SaveError:
    entity: AsanaResource
    operation: OperationType
    error: Exception
    payload: dict[str, Any]

    @property
    def is_retryable(self) -> bool:
        """Determine if this error is potentially retryable.

        Classification based on HTTP status code semantics:
        - 429 (Rate Limit): Retryable after delay
        - 5xx (Server Error): Retryable (transient)
        - 4xx (Client Error): Not retryable (bad request)

        Returns:
            True if error type suggests retry may succeed.
        """
        status_code = self._extract_status_code()
        if status_code is None:
            return False  # Unknown errors are not retryable

        # Rate limit is retryable
        if status_code == 429:
            return True

        # Server errors are retryable
        if 500 <= status_code < 600:
            return True

        # Client errors are not retryable
        return False

    def _extract_status_code(self) -> int | None:
        """Extract HTTP status code from error.

        Handles AsanaError and BatchResult error types.
        """
        from autom8_asana.exceptions import AsanaError

        if isinstance(self.error, AsanaError):
            return self.error.status_code

        # Check for status_code attribute on generic exceptions
        if hasattr(self.error, 'status_code'):
            return getattr(self.error, 'status_code')

        return None
```

#### 4.3.2 Error Classification Table

| HTTP Status | `is_retryable` | Reason |
|-------------|----------------|--------|
| 400 Bad Request | False | Client error - payload invalid |
| 401 Unauthorized | False | Auth error - needs credential fix |
| 403 Forbidden | False | Permission error - needs access grant |
| 404 Not Found | False | Resource doesn't exist |
| 409 Conflict | False | Conflict - needs manual resolution |
| **429 Too Many Requests** | **True** | Rate limit - can retry after delay |
| **500 Internal Server Error** | **True** | Server error - transient |
| **502 Bad Gateway** | **True** | Server error - transient |
| **503 Service Unavailable** | **True** | Server error - transient |
| **504 Gateway Timeout** | **True** | Server error - transient |

#### 4.3.3 SaveResult Convenience Methods

```python
@dataclass
class SaveResult:
    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    # ... existing fields ...

    @property
    def failed_count(self) -> int:
        """Number of failed operations (FR-FH-007)."""
        return len(self.failed)

    def get_failed_entities(self) -> list[AsanaResource]:
        """Get entities that failed to save (FR-FH-005).

        Returns:
            List of entities from failed operations.
        """
        return [error.entity for error in self.failed]

    def get_retryable_errors(self) -> list[SaveError]:
        """Get errors that may be retried (FR-FH-006).

        Returns:
            List of SaveErrors where is_retryable is True.
        """
        return [error for error in self.failed if error.is_retryable]
```

### 4.4 Entity Lookup API

New methods exposed on SaveSession for entity lookup by GID.

#### 4.4.1 ChangeTracker Methods

```python
class ChangeTracker:
    def find_by_gid(self, gid: str) -> AsanaResource | None:
        """Look up entity by GID (FR-EL-001).

        Searches direct entities first, then checks transition map
        for temp GIDs that have been resolved to real GIDs.

        Args:
            gid: The GID to look up (real or temp).

        Returns:
            Tracked entity or None if not found.
        """
        # Direct lookup
        if gid in self._entities:
            return self._entities[gid]

        # Check if it's a transitioned temp GID
        if gid in self._gid_transitions:
            real_gid = self._gid_transitions[gid]
            return self._entities.get(real_gid)

        return None

    def is_tracked(self, gid: str) -> bool:
        """Check if GID is currently tracked (FR-EL-005).

        Args:
            gid: The GID to check.

        Returns:
            True if entity with this GID is tracked.
        """
        return self.find_by_gid(gid) is not None
```

#### 4.4.2 SaveSession Delegation

```python
class SaveSession:
    def find_by_gid(self, gid: str) -> AsanaResource | None:
        """Look up entity by GID.

        Per FR-EL-001: New capability enabled by GID-based tracking.

        Args:
            gid: The GID to look up.

        Returns:
            Tracked entity or None if not found.

        Example:
            task = session.find_by_gid("12345")
            if task:
                task.completed = True
        """
        return self._tracker.find_by_gid(gid)

    def is_tracked(self, gid: str) -> bool:
        """Check if GID is currently tracked.

        Per FR-EL-005: Boolean helper for tracking state.

        Args:
            gid: The GID to check.

        Returns:
            True if entity with this GID is tracked.

        Example:
            if not session.is_tracked("12345"):
                task = await client.tasks.get_async("12345")
                session.track(task)
        """
        return self._tracker.is_tracked(gid)
```

### 4.5 Backward Compatibility (ADR-0080)

#### 4.5.1 Public API Compatibility Matrix

| Method | Signature Change | Behavior Change | Breaking |
|--------|-----------------|-----------------|----------|
| `track(entity)` | None | Deduplicates by GID | No* |
| `untrack(entity)` | None | Uses GID-based key | No |
| `get_state(entity)` | None | None | No |
| `get_changes(entity)` | None | None | No |
| `mark_deleted(entity)` | None | None | No |
| `mark_clean(entity)` | None | None | No |
| `get_dirty_entities()` | None | None | No |
| `get_changed_fields(entity)` | None | None | No |
| **NEW** `find_by_gid(gid)` | New method | N/A | No |
| **NEW** `is_tracked(gid)` | New method | N/A | No |

*Behavior change note: Tracking the same GID twice now updates the reference instead of creating duplicate entries. This is a bug fix, not a breaking change.

#### 4.5.2 Internal Type Changes

| Data Structure | Old Type | New Type | Impact |
|---------------|----------|----------|--------|
| `_entities` | `dict[int, AsanaResource]` | `dict[str, AsanaResource]` | Internal |
| `_snapshots` | `dict[int, dict]` | `dict[str, dict]` | Internal |
| `_states` | `dict[int, EntityState]` | `dict[str, EntityState]` | Internal |
| **NEW** `_gid_transitions` | N/A | `dict[str, str]` | Internal |
| **NEW** `_entity_to_key` | N/A | `dict[int, str]` | Internal |

---

## 5. Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Entity identity strategy | GID-based with `__id_` fallback | Ensures deduplication, handles edge cases | ADR-0078 |
| Retryable error classification | HTTP status code based | Standard HTTP semantics, simple implementation | ADR-0079 |
| Registry scope | Per-SaveSession | Maintains session isolation, matches ORM patterns | ADR-0080 |

---

## 6. Complexity Assessment

**Level**: Module

**Justification**:
- Single module modification (tracker.py) with minor updates to models.py and session.py
- No new external dependencies
- No new architectural patterns
- Surgical replacement of keying strategy
- Clear boundaries and responsibilities

**Escalation triggers NOT present**:
- No multiple consumers of same logic (internal to SaveSession)
- No external API contract changes
- No independent deployment needed

---

## 7. Implementation Plan

### Phase 1: Core GID-Based Tracking (MUST HAVE)

| Task | File | Estimate |
|------|------|----------|
| P1.1 Update ChangeTracker data structures | `tracker.py` | 0.5h |
| P1.2 Implement `_get_key()` method | `tracker.py` | 0.25h |
| P1.3 Update `track()` with duplicate detection | `tracker.py` | 0.5h |
| P1.4 Implement `update_gid()` method | `tracker.py` | 0.25h |
| P1.5 Update pipeline to call `update_gid()` | `pipeline.py` | 0.25h |
| P1.6 Update all internal methods to use string keys | `tracker.py` | 0.5h |
| P1.7 Add unit tests for GID-based tracking | `test_tracker.py` | 1h |
| P1.8 Add integration tests for duplicate scenario | `test_*.py` | 1h |

**Phase 1 Total**: ~4.25h

### Phase 2: Failure Handling & Lookup (SHOULD/COULD HAVE)

| Task | File | Estimate |
|------|------|----------|
| P2.1 Add `is_retryable` to SaveError | `models.py` | 0.5h |
| P2.2 Add `_extract_status_code()` helper | `models.py` | 0.25h |
| P2.3 Add SaveResult convenience methods | `models.py` | 0.25h |
| P2.4 Implement `find_by_gid()` | `tracker.py`, `session.py` | 0.25h |
| P2.5 Implement `is_tracked()` | `tracker.py`, `session.py` | 0.15h |
| P2.6 Add unit tests for failure handling | `test_models.py` | 0.5h |
| P2.7 Add unit tests for lookup methods | `test_tracker.py` | 0.5h |

**Phase 2 Total**: ~2.4h

### Phase 3: Documentation (MUST HAVE)

| Task | File | Estimate |
|------|------|----------|
| P3.1 Document entity identity behavior | `docs/guides/` | 0.5h |
| P3.2 Document partial failure handling | `docs/guides/` | 0.5h |
| P3.3 Add CHANGELOG entry | `CHANGELOG.md` | 0.15h |
| P3.4 Update docstrings | Various | 0.5h |

**Phase 3 Total**: ~1.65h

**Total Estimate**: ~8.3h

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Silent behavior change surprises users | Medium | Medium | DEBUG log on duplicate track; CHANGELOG entry |
| Edge cases with GID-less entities | Low | Low | Fallback to `__id_{id}`; comprehensive tests |
| Re-keying complexity causes bugs | High | Low | Port spike POC code; extensive testing |
| Performance regression | Medium | Low | Benchmark tests; O(1) operations only |
| Snapshot state confusion on duplicate | Medium | Medium | Keep first snapshot, update reference; document |

---

## 9. Observability

### 9.1 Logging

| Event | Level | Fields | Trigger |
|-------|-------|--------|---------|
| `tracker_duplicate_gid` | DEBUG | `gid`, `message` | Same GID tracked twice |
| `tracker_gid_transition` | DEBUG | `old_gid`, `new_gid` | Temp GID resolved |
| `tracker_track` | DEBUG | `key`, `state` | Entity tracked |
| `tracker_untrack` | DEBUG | `key` | Entity untracked |

### 9.2 Metrics (Future)

- `tracker.entities_count`: Number of tracked entities
- `tracker.transitions_count`: Number of temp GID transitions
- `tracker.duplicate_tracks`: Count of duplicate GID track events

---

## 10. Testing Strategy

### 10.1 Unit Tests

| Test Case | Requirement | Priority |
|-----------|-------------|----------|
| Track entity by GID | FR-EID-001 | MUST |
| Track entity without GID (fallback) | FR-EID-002 | MUST |
| Track temp GID entity | FR-EID-003 | MUST |
| Re-key on GID transition | FR-EID-004 | MUST |
| Temp GID lookup via transition map | FR-EID-005 | MUST |
| Duplicate GID updates reference | FR-EID-006 | MUST |
| `is_retryable` for 429 | FR-FH-002 | SHOULD |
| `is_retryable` for 5xx | FR-FH-003 | SHOULD |
| `is_retryable` for 4xx | FR-FH-004 | SHOULD |
| `find_by_gid()` returns entity | FR-EL-002 | COULD |
| `find_by_gid()` returns None | FR-EL-004 | COULD |
| `is_tracked()` returns bool | FR-EL-005 | COULD |

### 10.2 Integration Tests

| Test Case | Scenario |
|-----------|----------|
| Duplicate fetch deduplication | UC-1: Fetch same task twice, modify both, single UPDATE |
| Temp GID end-to-end | UC-2: Create new entity, verify GID transition |
| Partial failure with retryable | UC-3: Mock 429, verify is_retryable=True |

### 10.3 Backward Compatibility Tests

| Test Case | Verification |
|-----------|--------------|
| Existing test suite passes | No signature changes break callers |
| Legacy tracking patterns work | id()-tracked entities still function |

---

## 11. Requirement Traceability Matrix

| Requirement | Design Section | Test Case | ADR |
|-------------|----------------|-----------|-----|
| FR-EID-001 | 4.1.1 | `test_track_by_gid` | ADR-0078 |
| FR-EID-002 | 4.1.1 | `test_track_without_gid` | ADR-0078 |
| FR-EID-003 | 4.2.1 | `test_track_temp_gid` | ADR-0078 |
| FR-EID-004 | 4.2.2 | `test_gid_transition` | ADR-0078 |
| FR-EID-005 | 4.2.2 | `test_transition_lookup` | ADR-0078 |
| FR-EID-006 | 4.1.3 | `test_duplicate_gid_update` | ADR-0078 |
| FR-EID-007 | 4.1.3 | `test_duplicate_gid_log` | - |
| FR-EID-008 | 4.5.1 | Existing tests | ADR-0080 |
| FR-EL-001 | 4.4.1 | `test_find_by_gid` | - |
| FR-EL-002 | 4.4.1 | `test_find_by_real_gid` | - |
| FR-EL-003 | 4.4.1 | `test_find_by_temp_gid` | - |
| FR-EL-004 | 4.4.1 | `test_find_unknown_gid` | - |
| FR-EL-005 | 4.4.2 | `test_is_tracked` | - |
| FR-FH-001 | 4.3.1 | `test_is_retryable_property` | ADR-0079 |
| FR-FH-002 | 4.3.2 | `test_is_retryable_429` | ADR-0079 |
| FR-FH-003 | 4.3.2 | `test_is_retryable_5xx` | ADR-0079 |
| FR-FH-004 | 4.3.2 | `test_is_retryable_4xx` | ADR-0079 |
| FR-FH-005 | 4.3.3 | `test_get_failed_entities` | - |
| FR-FH-006 | 4.3.3 | `test_get_retryable_errors` | - |
| FR-FH-007 | 4.3.3 | `test_failed_count` | - |

---

## 12. Open Questions

| Question | Owner | Status | Resolution |
|----------|-------|--------|------------|
| None | - | - | All questions resolved in PRD |

---

## 13. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Architect | Initial draft |

---

## Appendix A: Complete ChangeTracker Class Design

```python
class ChangeTracker:
    """Tracks entity changes via snapshot comparison.

    Per ADR-0078: GID-based entity identity for deduplication.
    Per ADR-0036: Snapshot-based dirty detection using model_dump().

    Responsibilities:
    - Store snapshots at track() time
    - Detect dirty entities by comparing current state to snapshot
    - Compute field-level change sets
    - Track entity lifecycle states
    - Deduplicate entities by GID

    Uses GID as primary key for identity, with fallback to __id_{id()}
    for entities without GIDs.
    """

    def __init__(self) -> None:
        """Initialize empty tracker state."""
        # key -> entity reference
        self._entities: dict[str, AsanaResource] = {}
        # key -> snapshot dict
        self._snapshots: dict[str, dict[str, Any]] = {}
        # key -> EntityState
        self._states: dict[str, EntityState] = {}
        # temp_gid -> real_gid (transition map)
        self._gid_transitions: dict[str, str] = {}
        # id(entity) -> key (reverse lookup)
        self._entity_to_key: dict[int, str] = {}
        # Optional logger
        self._log: Any = None

    def _get_key(self, entity: AsanaResource) -> str:
        """Generate tracking key for entity."""
        gid = getattr(entity, 'gid', None)
        if gid:
            return gid
        return f"__id_{id(entity)}"

    def track(self, entity: AsanaResource) -> None:
        """Register entity for change tracking."""
        key = self._get_key(entity)

        if key in self._entities:
            existing = self._entities[key]
            if existing is not entity:
                if self._log:
                    self._log.debug(
                        "tracker_duplicate_gid",
                        gid=key,
                    )
                old_id = id(existing)
                if old_id in self._entity_to_key:
                    del self._entity_to_key[old_id]
            else:
                return  # Already tracked, idempotent

        self._entities[key] = entity
        self._entity_to_key[id(entity)] = key

        if key not in self._snapshots:
            self._snapshots[key] = entity.model_dump()

        gid = entity.gid
        if not gid or gid.startswith("temp_"):
            self._states[key] = EntityState.NEW
        else:
            self._states[key] = EntityState.CLEAN

    def untrack(self, entity: AsanaResource) -> None:
        """Remove entity from tracking."""
        key = self._get_key(entity)
        self._snapshots.pop(key, None)
        self._states.pop(key, None)
        self._entities.pop(key, None)
        self._entity_to_key.pop(id(entity), None)

    def update_gid(self, entity: AsanaResource, old_key: str, new_gid: str) -> None:
        """Re-key entity after temp GID becomes real GID."""
        if old_key not in self._entities:
            return

        self._entities[new_gid] = self._entities.pop(old_key)
        self._snapshots[new_gid] = self._snapshots.pop(old_key)
        self._states[new_gid] = self._states.pop(old_key)
        self._gid_transitions[old_key] = new_gid
        self._entity_to_key[id(entity)] = new_gid

    def find_by_gid(self, gid: str) -> AsanaResource | None:
        """Look up entity by GID."""
        if gid in self._entities:
            return self._entities[gid]
        if gid in self._gid_transitions:
            return self._entities.get(self._gid_transitions[gid])
        return None

    def is_tracked(self, gid: str) -> bool:
        """Check if GID is currently tracked."""
        return self.find_by_gid(gid) is not None

    # ... remaining methods unchanged except for int->str key type ...
```

---

## Appendix B: Quality Gate Checklist

- [x] Traces to approved PRD (PRD-HARDENING-F)
- [x] All significant decisions have ADRs (ADR-0078, ADR-0079, ADR-0080)
- [x] Component responsibilities are clear
- [x] Interfaces are defined (public API unchanged + new methods)
- [x] Complexity level is justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable
- [x] Engineer could implement without clarifying questions
