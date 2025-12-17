# PRD: SaveSession Reliability (Initiative F)

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-HARDENING-F |
| **Status** | Draft |
| **Author** | Requirements Analyst |
| **Created** | 2025-12-16 |
| **Last Updated** | 2025-12-16 |
| **Initiative** | Architecture Hardening - Initiative F |
| **Issues Addressed** | Issue #8 (High), Issue #1 (High) |
| **Spike Reference** | SPIKE-HARDENING-F (GO, HIGH confidence) |
| **Discovery Reference** | DISCOVERY-HARDENING-F |

---

## 1. Problem Statement

### 1.1 Issue #8: Entity Identity Uses Python `id()` (HIGH Severity)

The `ChangeTracker` class uses Python's `id()` function for entity identity (`tracker.py:32-39`). This creates a critical bug when the same Asana resource is fetched multiple times within a session:

```python
# BUG DEMONSTRATION
async with SaveSession(client) as session:
    task_a = await client.tasks.get_async("12345")
    task_b = await client.tasks.get_async("12345")  # Same GID, different Python object

    session.track(task_a)
    session.track(task_b)  # Tracked SEPARATELY due to id(task_a) != id(task_b)

    task_a.name = "Change A"
    task_b.notes = "Change B"

    await session.commit_async()
    # PROBLEM: Two UPDATE operations sent for same task
    # Race condition: one change is lost
```

**Impact**:
- Data loss through silent overwrite
- Duplicate API operations (wasted quota)
- Confusing error attribution (which "copy" failed?)
- Memory inefficiency (multiple snapshots for same entity)

### 1.2 Issue #1: No Transaction Semantics (HIGH Severity)

SaveSession commits operations without transaction guarantees. When partial failures occur:

- Successful operations are committed to Asana (cannot rollback)
- Failed operations remain in local tracker (can retry)
- Users must manually inspect `SaveResult.failed` to understand state
- No built-in guidance on which errors are retryable

**Impact**:
- Partial state between local and remote
- Manual error handling required
- No rollback capability
- Recovery guidance missing

### 1.3 Who Is Affected

- **SDK Users**: Any developer using SaveSession for bulk operations
- **Automation Scripts**: Workflows that fetch and modify multiple tasks
- **Business Logic**: Code that may re-fetch entities for validation

### 1.4 Cost of Not Solving

- Silent data loss undermines trust in the SDK
- Users implement workarounds (tracking GIDs manually)
- Support burden for "lost changes" investigations
- Blocks adoption for critical automation use cases

---

## 2. Goals and Success Metrics

### 2.1 Goals

| ID | Goal | Measurable Outcome |
|----|------|-------------------|
| G-1 | Eliminate duplicate entity tracking | Same GID tracked once, regardless of Python object count |
| G-2 | Preserve all changes to tracked entities | Changes from all references merged into single update |
| G-3 | Enhance failure visibility | Users can programmatically determine error recoverability |
| G-4 | Document partial failure handling | Clear guidance in SDK documentation |

### 2.2 Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG-1 | True transaction semantics (rollback) | Asana API doesn't support transactions; would require compensating actions |
| NG-2 | Automatic retry mechanism | Deferred to future initiative (changes scope significantly) |
| NG-3 | Idempotency keys | Requires API-level support; out of scope |
| NG-4 | Cross-session entity sharing | Per-session isolation is intentional |

### 2.3 Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Duplicate tracking eliminated | 100% | Unit test: same GID tracked once |
| No breaking API changes | 0 breaking changes | Existing tests pass without modification |
| Documentation coverage | 100% of new features | All new methods have docstrings and guides |
| Test coverage | >= 90% for new code | pytest-cov report |

---

## 3. Scope

### 3.1 In Scope

| ID | Item | Description |
|----|------|-------------|
| IS-1 | GID-based entity tracking | Replace `id()` with GID as primary key |
| IS-2 | Temp GID handling | Support `temp_*` GIDs for new entities |
| IS-3 | GID transition on CREATE | Re-key when temp GID becomes real GID |
| IS-4 | Duplicate detection | Detect and merge when same GID tracked twice |
| IS-5 | Entity lookup by GID | New `find_by_gid()` and `is_tracked()` methods |
| IS-6 | Failure visibility enhancement | Add `is_retryable` property to `SaveError` |
| IS-7 | Failed entity retrieval | Add `get_failed_entities()` to SaveResult |
| IS-8 | Documentation | Error handling guide, entity identity docs |

### 3.2 Out of Scope

| ID | Item | Rationale |
|----|------|-----------|
| OS-1 | Automatic retry | Separate initiative; changes commit semantics |
| OS-2 | Transaction rollback | Asana API limitation |
| OS-3 | Idempotency keys | Requires Asana API support |
| OS-4 | Progress callbacks | Nice-to-have; defer to future |
| OS-5 | Cross-session registry | Conflicts with session isolation principle |
| OS-6 | Entity merge conflict resolution UI | Too complex for this initiative |

---

## 4. Open Questions Resolved

| ID | Question | Decision | Rationale |
|----|----------|----------|-----------|
| OQ-1 | Registry scope: global or per-session? | **Per-session** | Maintains session isolation; avoids cross-session side effects; matches ORM patterns |
| OQ-2 | How to handle truly GID-less entities? | **Fallback to id()** | Edge case for entities that somehow have no GID; use `__id_{id(entity)}` as key |
| OQ-3 | Add `is_retryable` property? | **Yes, SHOULD HAVE** | Common need; can classify based on HTTP status (429, 5xx = retryable) |
| OQ-4 | Add automatic retry? | **No, defer** | Scope creep; requires backoff strategy, max attempts, etc. |
| OQ-5 | How to handle entity refresh (re-track same GID)? | **Silent update with warning log** | Update entity reference, preserve snapshot from first track, log at DEBUG level |
| OQ-6 | Transaction semantics? | **Best-effort with documentation** | Document partial failure handling patterns; provide `get_failed_entities()` helper |

---

## 5. Requirements

### 5.1 Functional Requirements: Entity Identity (MUST HAVE)

| ID | Requirement | Priority | Acceptance Criteria | Traces To |
|----|-------------|----------|---------------------|-----------|
| FR-EID-001 | Tracker SHALL use GID as primary key for entities with GID | MUST | Unit test: `tracker._entities` keyed by GID string, not int | Discovery 2.1, Spike POC-1 |
| FR-EID-002 | Tracker SHALL use `__id_{id(entity)}` for entities without GID | MUST | Unit test: GID-less entity tracked with fallback key | Spike POC-1 |
| FR-EID-003 | Tracker SHALL support `temp_*` prefixed GIDs as valid keys | MUST | Unit test: entity with `temp_123` GID tracked correctly | Discovery 2.6 |
| FR-EID-004 | Tracker SHALL re-key entity when temp GID becomes real GID | MUST | Unit test: after CREATE, entity accessible via real GID | Spike POC-1, Discovery 2.6 |
| FR-EID-005 | Tracker SHALL maintain `_gid_transitions` map for temp-to-real lookup | MUST | Unit test: `find_by_gid("temp_123")` returns entity after transition | Spike POC-1 |
| FR-EID-006 | When same GID tracked twice, Tracker SHALL update entity reference | MUST | Unit test: second track() updates reference, keeps original snapshot | OQ-5, Discovery FM-14 |
| FR-EID-007 | When same GID tracked twice, Tracker SHALL log warning at DEBUG level | SHOULD | Integration test: log message contains GID | OQ-5 |
| FR-EID-008 | Tracker SHALL preserve backward-compatible public API | MUST | Existing unit tests pass without modification | Discovery Theme 1 |

### 5.2 Functional Requirements: Entity Lookup (COULD HAVE)

| ID | Requirement | Priority | Acceptance Criteria | Traces To |
|----|-------------|----------|---------------------|-----------|
| FR-EL-001 | SaveSession SHALL provide `find_by_gid(gid)` method | COULD | Method returns entity or None; unit test coverage | Spike POC-1 |
| FR-EL-002 | `find_by_gid()` SHALL return entity for real GID | COULD | Unit test: tracked entity returned by GID | Spike POC-1 |
| FR-EL-003 | `find_by_gid()` SHALL return entity for transitioned temp GID | COULD | Unit test: `find_by_gid("temp_x")` works after CREATE | Spike POC-1 |
| FR-EL-004 | `find_by_gid()` SHALL return None for unknown GID | COULD | Unit test: unknown GID returns None (not raises) | OQ-2 |
| FR-EL-005 | SaveSession SHALL provide `is_tracked(gid)` method | COULD | Method returns bool; unit test coverage | Discovery Theme 3 |

### 5.3 Functional Requirements: Failure Handling (SHOULD HAVE)

| ID | Requirement | Priority | Acceptance Criteria | Traces To |
|----|-------------|----------|---------------------|-----------|
| FR-FH-001 | SaveError SHALL provide `is_retryable` property | SHOULD | Property returns bool based on error classification | OQ-3, Discovery Gap 4 |
| FR-FH-002 | `is_retryable` SHALL return True for 429 (rate limit) errors | SHOULD | Unit test: 429 status -> is_retryable=True | Discovery FM-5 |
| FR-FH-003 | `is_retryable` SHALL return True for 5xx (server) errors | SHOULD | Unit test: 500/502/503/504 -> is_retryable=True | Discovery Gap 4 |
| FR-FH-004 | `is_retryable` SHALL return False for 4xx (client) errors except 429 | SHOULD | Unit test: 400/401/403/404 -> is_retryable=False | Discovery Gap 4 |
| FR-FH-005 | SaveResult SHALL provide `get_failed_entities()` method | SHOULD | Method returns list of entities from failed list | Discovery Gap 5 |
| FR-FH-006 | SaveResult SHALL provide `get_retryable_errors()` method | SHOULD | Method returns SaveErrors where is_retryable=True | Discovery Gap 4 |
| FR-FH-007 | SaveResult SHALL provide `failed_count` property | SHOULD | Property returns len(failed); convenience accessor | Discovery 4.4 |

### 5.4 Functional Requirements: Documentation (MUST HAVE)

| ID | Requirement | Priority | Acceptance Criteria | Traces To |
|----|-------------|----------|---------------------|-----------|
| FR-DOC-001 | SDK docs SHALL document entity identity behavior | MUST | Markdown file in docs/ explains GID-based tracking | Discovery Gap 8 |
| FR-DOC-002 | SDK docs SHALL document partial failure handling | MUST | Guide with code examples for SaveResult inspection | Discovery Gap 7 |
| FR-DOC-003 | SDK docs SHALL include failure mode reference | MUST | Table of error types with recovery guidance | Discovery Section 3 |
| FR-DOC-004 | All new public methods SHALL have docstrings | MUST | pylint/ruff passes; all public methods documented | Standard |
| FR-DOC-005 | CHANGELOG SHALL document breaking behavior changes | MUST | Entry describes entity identity change | Standard |

### 5.5 Non-Functional Requirements

| ID | Requirement | Target | Measurement | Priority |
|----|-------------|--------|-------------|----------|
| NFR-001 | Performance: track() latency | < 1ms p99 | Benchmark test | MUST |
| NFR-002 | Performance: GID lookup | O(1) | Code review (dict access) | MUST |
| NFR-003 | Memory: no leaks in _gid_transitions | Bounded by session lifetime | Session close clears map | MUST |
| NFR-004 | Compatibility: Python 3.10+ | All supported versions | CI matrix | MUST |
| NFR-005 | Test coverage for new code | >= 90% | pytest-cov | SHOULD |

---

## 6. User Stories / Use Cases

### 6.1 UC-1: Duplicate Fetch Handling

**As a** developer using SaveSession
**I want** changes from multiple fetches of the same task to be merged
**So that** I don't lose data when the same task is accessed from different code paths

**Scenario**:
```python
async with SaveSession(client) as session:
    # Fetched in function A
    task_a = await client.tasks.get_async("12345")
    session.track(task_a)
    task_a.name = "Updated Name"

    # Later, fetched again in function B (doesn't know about task_a)
    task_b = await client.tasks.get_async("12345")
    session.track(task_b)
    task_b.notes = "Updated Notes"

    result = await session.commit_async()
    # EXPECTED: Single UPDATE with both name and notes changes
    assert len(result.succeeded) == 1
    assert result.succeeded[0].name == "Updated Name"
    assert result.succeeded[0].notes == "Updated Notes"
```

### 6.2 UC-2: Partial Failure Recovery

**As a** developer handling bulk operations
**I want** to easily identify which failures are retryable
**So that** I can implement appropriate retry logic

**Scenario**:
```python
result = await session.commit_async()

if not result.success:
    # Get retryable errors
    retryable = result.get_retryable_errors()

    if retryable:
        # Some errors can be retried (rate limit, server errors)
        for error in retryable:
            print(f"Will retry: {error.entity.gid} - {error.error}")
        # Implement retry logic...

    # Non-retryable errors need different handling
    permanent = [e for e in result.failed if not e.is_retryable]
    for error in permanent:
        print(f"Cannot retry: {error.entity.gid} - {error.error}")
```

### 6.3 UC-3: Entity Lookup Before Commit

**As a** developer building complex workflows
**I want** to check if an entity is already tracked by GID
**So that** I can avoid redundant fetches and track calls

**Scenario**:
```python
async with SaveSession(client) as session:
    # Check if already tracked
    if not session.is_tracked("12345"):
        task = await client.tasks.get_async("12345")
        session.track(task)
    else:
        task = session.find_by_gid("12345")

    task.completed = True
    await session.commit_async()
```

---

## 7. Assumptions

| ID | Assumption | Basis | Risk if Wrong |
|----|------------|-------|---------------|
| A-1 | GID is globally unique within Asana | Asana API documentation | LOW - Asana guarantees this |
| A-2 | temp_* prefix is never used by real Asana GIDs | Implementation convention | LOW - We control temp GID format |
| A-3 | Users will read migration documentation | Standard SDK practice | MEDIUM - Silent behavior change could confuse |
| A-4 | 429 and 5xx errors are generally retryable | HTTP semantics | LOW - Standard classification |
| A-5 | Session-scoped registry is sufficient | ORM pattern precedent | LOW - Can revisit if users need cross-session |

---

## 8. Dependencies

| ID | Dependency | Type | Owner | Status |
|----|------------|------|-------|--------|
| D-1 | Spike POC validation | Internal | Principal Engineer | COMPLETE |
| D-2 | Discovery analysis | Internal | Requirements Analyst | COMPLETE |
| D-3 | Existing ChangeTracker tests | Internal | QA | Available |
| D-4 | Asana Batch API behavior | External | Asana | Stable |

---

## 9. Risks and Mitigations

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|------------|--------|------------|
| R-1 | Silent behavior change surprises users | Medium | Medium | Document in CHANGELOG; add DEBUG log on duplicate track |
| R-2 | Edge cases with GID-less entities | Low | Low | Fallback to id(); comprehensive unit tests |
| R-3 | Re-keying complexity causes bugs | Low | High | Port spike POC code; extensive testing |
| R-4 | Performance regression | Low | Medium | Benchmark tests; O(1) operations only |
| R-5 | Snapshot state confusion on duplicate track | Medium | Medium | Keep first snapshot, update reference; document behavior |

---

## 10. Acceptance Test Scenarios

### 10.1 ATS-1: Duplicate GID Deduplication

**Preconditions**:
- SaveSession initialized
- Task with GID "12345" exists in Asana

**Steps**:
1. Fetch task twice: `task_a = get("12345")`, `task_b = get("12345")`
2. Track both: `session.track(task_a)`, `session.track(task_b)`
3. Modify both: `task_a.name = "A"`, `task_b.notes = "B"`
4. Commit: `result = await session.commit_async()`

**Expected Results**:
- `len(result.succeeded) == 1`
- Single UPDATE operation sent to Asana
- Task in Asana has both name="A" and notes="B"
- `session.find_by_gid("12345")` returns the tracked entity

**Verification**: Unit test + integration test

---

### 10.2 ATS-2: Temp GID Transition

**Preconditions**:
- SaveSession initialized

**Steps**:
1. Create new task: `task = Task(gid="temp_1", name="New Task")`
2. Track: `session.track(task)`
3. Commit: `result = await session.commit_async()`
4. Look up by temp GID: `found = session.find_by_gid("temp_1")`
5. Look up by real GID: `found2 = session.find_by_gid(task.gid)`

**Expected Results**:
- `result.succeeded[0].gid` starts with numeric (real GID)
- `found is task` (temp GID lookup works via transition map)
- `found2 is task` (real GID lookup works)
- `tracker._gid_transitions["temp_1"] == task.gid`

**Verification**: Unit test

---

### 10.3 ATS-3: Retryable Error Classification

**Preconditions**:
- SaveSession with mocked HTTP client
- Mock returns 429 for first entity, 400 for second

**Steps**:
1. Track two entities
2. Commit (partial failure)
3. Inspect `result.failed`

**Expected Results**:
- `result.failed[0].is_retryable == True` (429)
- `result.failed[1].is_retryable == False` (400)
- `result.get_retryable_errors()` returns only first error
- `result.get_failed_entities()` returns both entities

**Verification**: Unit test with mocked responses

---

### 10.4 ATS-4: Backward Compatibility

**Preconditions**:
- Existing test suite for ChangeTracker/SaveSession

**Steps**:
1. Run existing test suite without modification

**Expected Results**:
- All existing tests pass
- No deprecation warnings (unless intentionally added)

**Verification**: CI test run

---

## 11. Traceability Matrix

| Requirement | Discovery Finding | Spike Finding | Failure Mode |
|-------------|------------------|---------------|--------------|
| FR-EID-001 | Section 2.1 | POC-1 | FM-14 |
| FR-EID-002 | Section 2.1 | POC-1 (fallback) | - |
| FR-EID-003 | Section 2.6 | POC-1 | - |
| FR-EID-004 | Section 2.6 | POC-1 | - |
| FR-EID-005 | - | POC-1 | - |
| FR-EID-006 | Section 2.5 | POC-1 | FM-14 |
| FR-FH-001 | Gap 4 | - | FM-5 |
| FR-FH-005 | Gap 5 | - | - |
| FR-DOC-001 | Gap 8 | - | - |
| FR-DOC-002 | Gap 7 | POC-2 | - |

---

## 12. Implementation Phases

| Phase | Requirements | Description |
|-------|--------------|-------------|
| Phase 1 | FR-EID-001 to FR-EID-008, NFR-001 to NFR-003 | Core GID-based tracking |
| Phase 2 | FR-FH-001 to FR-FH-007 | Failure visibility enhancements |
| Phase 3 | FR-EL-001 to FR-EL-005 | Entity lookup methods |
| Phase 4 | FR-DOC-001 to FR-DOC-005 | Documentation |

---

## 13. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-16 | Requirements Analyst | Initial draft from discovery |

---

## Appendix A: Current vs. Proposed Tracking Keys

### Current Implementation (id()-based)

```python
# tracker.py:32-39
self._snapshots: dict[int, dict[str, Any]] = {}  # id(entity) -> snapshot
self._states: dict[int, EntityState] = {}        # id(entity) -> state
self._entities: dict[int, AsanaResource] = {}    # id(entity) -> entity
```

### Proposed Implementation (GID-based)

```python
# Per Spike POC-1
self._snapshots: dict[str, dict[str, Any]] = {}  # GID -> snapshot
self._states: dict[str, EntityState] = {}        # GID -> state
self._entities: dict[str, AsanaResource] = {}    # GID -> entity
self._gid_transitions: dict[str, str] = {}       # temp_GID -> real_GID
self._entity_to_key: dict[int, str] = {}         # id(entity) -> key (reverse lookup)
```

---

## Appendix B: Error Classification Reference

| HTTP Status | `is_retryable` | Reason |
|-------------|---------------|--------|
| 400 Bad Request | False | Client error - payload invalid |
| 401 Unauthorized | False | Auth error - needs credential fix |
| 403 Forbidden | False | Permission error - needs access grant |
| 404 Not Found | False | Resource doesn't exist |
| 409 Conflict | False | Conflict - needs manual resolution |
| 429 Too Many Requests | **True** | Rate limit - can retry after delay |
| 500 Internal Server Error | **True** | Server error - transient |
| 502 Bad Gateway | **True** | Server error - transient |
| 503 Service Unavailable | **True** | Server error - transient |
| 504 Gateway Timeout | **True** | Server error - transient |

---

## Appendix C: Quality Gate Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] All 6 open questions resolved with decisions
- [x] Success criteria defined
- [x] At least 3 acceptance test scenarios
- [x] Traceability to discovery findings
- [x] Backward compatibility addressed
