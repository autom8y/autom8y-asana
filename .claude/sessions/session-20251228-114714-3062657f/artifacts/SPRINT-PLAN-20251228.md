# Sprint Debt Packages

**Plan Date**: 2025-12-28
**Planner**: Sprint Planner (debt-triage-pack)
**Input**: RISK-REPORT-20251228.md, DEBT-LEDGER-20251228.md
**Planning Horizon**: 3 Sprints (5-7 weeks total)

---

## Executive Summary

### Sprint Roadmap Overview

| Sprint | Focus | Duration | Items | Total Effort |
|--------|-------|----------|-------|--------------|
| **Sprint 1** | Critical Data Integrity | 1-2 weeks | 4 items | 8-14 days |
| **Sprint 2** | Test Infrastructure & Coverage | 1-2 weeks | 5 items | 7-12 days |
| **Sprint 3** | Concurrency & Refactoring | 2-3 weeks | 6 items | 10-16 days |

**Total Estimated Effort**: 25-42 days (with buffer)

### Risk Score Reduction Target

| Metric | Before | After Sprint 3 | Reduction |
|--------|--------|----------------|-----------|
| CRITICAL items | 3 | 0 | 100% |
| Total risk score (Top 10) | 287 | ~120 | 58% |
| Test collection errors | 151 | 0 | 100% |
| API route coverage | 0% | >60% | N/A |

### Key Dependencies

1. **DEBT-001 before DEBT-009**: Cache write-through fix enables simple API deprecation
2. **DEBT-020 before API tests**: Collection errors must clear to run new tests
3. **DEBT-003 + DEBT-005 together**: Session concurrency items share context
4. **Quick wins independent**: DEBT-007, DEBT-010 can start immediately

---

## Sprint 1: Critical Data Integrity

**Duration**: 1-2 weeks
**Theme**: Eliminate data loss risks
**Capacity Required**: 8-14 days engineering effort

### Sprint 1 Backlog

| Priority | ID | Title | Size | Effort | Confidence | Dependencies |
|----------|-----|-------|------|--------|------------|--------------|
| P0 | DEBT-001 | Two-tier cache write-through inconsistency | L | 3-5 days | Medium | None |
| P0 | DEBT-002 | Pending actions cleared on partial commit failure | L | 3-5 days | Medium | None |
| P1 | DEBT-007 | Circuit breaker hooks swallow exceptions | XS | 2-4 hours | High | None |
| P1 | DEBT-010 | Lock file UnboundLocalError risk | XS | 1-2 hours | High | None |

**Sprint 1 Buffer**: 20% (~2 days) for medium confidence items

### Package Details

---

#### DEBT-001: Two-tier cache write-through inconsistency

**Risk Score**: 40 (CRITICAL)
**Module**: `cache/tiered.py:75-86`
**Size**: L (3-5 days)
**Confidence**: Medium

**Problem Statement**:
Write-through to S3 (L2) is fire-and-forget. When L2 write fails, L1 and L2 become inconsistent. After L1 eviction, stale data is served from L2.

**Implementation Approach**:
1. Add "pending sync" flag to L1 entries
2. Implement write confirmation from L2
3. Rollback L1 on L2 failure, or mark for reconciliation
4. Add reconciliation job for unsynced entries

**Acceptance Criteria**:
- [ ] L2 write failures do not leave L1/L2 inconsistent
- [ ] Failed L2 writes are logged with sufficient context for debugging
- [ ] Entries pending sync are identifiable for reconciliation
- [ ] Unit tests cover: successful sync, failed sync, reconciliation path
- [ ] Integration test confirms no stale reads after simulated L2 failure

**Risk Mitigations**:
- If full transactional semantics too complex, implement "mark dirty" pattern first
- Can phase: (1) add logging/visibility, (2) add rollback, (3) add reconciliation

**Verification Approach**:
```bash
# Run cache-specific tests
pytest tests/unit/test_tiered*.py -v

# Simulate L2 failure scenario
pytest tests/integration/test_cache_consistency.py -v
```

---

#### DEBT-002: Pending actions cleared on partial commit failure

**Risk Score**: 40 (CRITICAL)
**Module**: `persistence/session.py:737-738`
**Size**: L (3-5 days)
**Confidence**: Medium

**Problem Statement**:
On partial commit failure, all pending actions are cleared regardless of which succeeded. Data loss occurs when some actions were intended but never executed.

**Implementation Approach**:
1. Add per-action success/failure tracking
2. Modify commit to only clear successfully executed actions
3. Return failed actions to caller for handling/retry
4. Add recovery mechanism for failed actions

**Acceptance Criteria**:
- [ ] Partial failure does not clear unexecuted actions
- [ ] Failed actions returned in commit result
- [ ] Successful actions correctly cleared
- [ ] Unit tests cover: all success, all failure, partial failure
- [ ] Documentation updated for new commit semantics

**Risk Mitigations**:
- Maintain backward compatibility: existing callers that ignore return value still work
- Add deprecation warning for callers not handling failed actions

**Verification Approach**:
```bash
# Run session-specific tests
pytest tests/unit/test_session*.py -v

# Run persistence integration tests
pytest tests/integration/test_persistence*.py -v
```

---

#### DEBT-007: Circuit breaker hooks swallow exceptions

**Risk Score**: 24 (HIGH)
**Module**: `transport/circuit_breaker.py:196-219`
**Size**: XS (2-4 hours)
**Confidence**: High

**Problem Statement**:
Bare `pass` statements in exception handlers silently swallow exceptions, making debugging extremely difficult.

**Implementation Approach**:
1. Replace `pass` with `logging.exception()`
2. Optionally collect exceptions for batch inspection

**Acceptance Criteria**:
- [ ] All except blocks in circuit_breaker.py log exceptions
- [ ] Log messages include context (hook name, circuit state)
- [ ] No change to circuit breaker behavior (still catches and continues)
- [ ] Unit test verifies logging occurs on exception

**Risk Mitigations**:
- Minimal risk - adding logging only, not changing control flow

**Verification Approach**:
```bash
pytest tests/unit/test_circuit_breaker*.py -v
```

---

#### DEBT-010: Lock file UnboundLocalError risk

**Risk Score**: 7 (LOW, but trivial fix)
**Module**: `automation/polling/polling_scheduler.py:445-462`
**Size**: XS (1-2 hours)
**Confidence**: High

**Problem Statement**:
`lock_file` variable may be undefined when OSError caught during lock acquisition, causing UnboundLocalError in cleanup.

**Implementation Approach**:
1. Initialize `lock_file = None` before try block
2. Check `if lock_file is not None` before cleanup operations

**Acceptance Criteria**:
- [ ] No UnboundLocalError possible in lock file error handling
- [ ] Lock file properly cleaned up on success path
- [ ] Unit test for error path with early OSError

**Risk Mitigations**:
- One-line fix with obvious correctness

**Verification Approach**:
```bash
pytest tests/unit/test_polling_scheduler*.py -v
```

---

### Sprint 1 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CRITICAL items remaining | 0 | Ledger update |
| Risk score reduction | -80 points | DEBT-001 + DEBT-002 resolved |
| Data loss vectors | 0 | Code review attestation |
| Circuit breaker visibility | 100% | All hooks log exceptions |

---

## Sprint 2: Test Infrastructure & Coverage

**Duration**: 1-2 weeks
**Theme**: Unblock CI, establish test patterns
**Capacity Required**: 7-12 days engineering effort
**Prerequisite**: Sprint 1 completion recommended (DEBT-020 technically independent)

### Sprint 2 Backlog

| Priority | ID | Title | Size | Effort | Confidence | Dependencies |
|----------|-----|-------|------|--------|------------|--------------|
| P0 | DEBT-020 | Test collection errors blocking coverage | M | 3-5 days | Medium | None |
| P1 | DEBT-015 | API sections routes untested | S | 1 day | High | DEBT-020 (soft) |
| P1 | DEBT-013 | API dataframes routes untested | M | 2-3 days | Medium | DEBT-015 (pattern) |
| P1 | DEBT-014 | API projects routes untested | M | 2-3 days | Medium | DEBT-015 (pattern) |
| P2 | DEBT-008 | Half-open state max calls not enforced | S | 4-8 hours | High | None |

**Sprint 2 Buffer**: 15% (~1.5 days) for triage uncertainty

### Package Details

---

#### DEBT-020: Test collection errors blocking coverage

**Risk Score**: 36 (CRITICAL)
**Module**: `tests/` (pytest infrastructure)
**Size**: M (3-5 days)
**Confidence**: Medium

**Problem Statement**:
151 test collection errors prevent full test suite execution. Coverage metrics unreliable. CI cannot be trusted.

**Implementation Approach**:
1. Run `pytest --collect-only` with verbose output
2. Categorize errors: import errors, fixture issues, syntax errors, other
3. Fix import/fixture errors first (bulk win)
4. Quarantine persistently failing tests with skip markers
5. Document quarantined tests with owner and investigation plan

**Acceptance Criteria**:
- [ ] `pytest --collect-only` reports 0 errors
- [ ] All quarantined tests marked with reason and owner
- [ ] Coverage report runs successfully
- [ ] CI pipeline passes collection phase

**Risk Mitigations**:
- If full triage takes too long, implement quarantine first to unblock CI
- Create DEBT items for quarantined tests to track cleanup

**Verification Approach**:
```bash
# Verify collection passes
pytest --collect-only 2>&1 | grep -c "error"
# Should output: 0

# Run full test suite
pytest --tb=short
```

---

#### DEBT-015: API sections routes untested

**Risk Score**: 16 (MEDIUM)
**Module**: `api/routes/sections.py` (220 lines)
**Size**: S (1 day)
**Confidence**: High

**Problem Statement**:
0% test coverage on user-facing API route. Regressions go undetected.

**Implementation Approach**:
1. Create test fixtures for section routes (reusable pattern)
2. Write happy path tests for CRUD operations
3. Add error case tests (not found, validation errors)
4. Document test pattern for other route coverage work

**Acceptance Criteria**:
- [ ] Test file created: `tests/api/test_routes_sections.py`
- [ ] Coverage >= 60% for `api/routes/sections.py`
- [ ] All CRUD operations have at least one test
- [ ] Test pattern documented for reuse

**Risk Mitigations**:
- Start with smallest route to establish pattern before larger routes

**Verification Approach**:
```bash
pytest tests/api/test_routes_sections.py -v --cov=api/routes/sections --cov-report=term-missing
```

---

#### DEBT-013: API dataframes routes untested

**Risk Score**: 22 (HIGH)
**Module**: `api/routes/dataframes.py` (455 lines)
**Size**: M (2-3 days)
**Confidence**: Medium

**Problem Statement**:
Critical user-facing API with 0% coverage. Largest untested route.

**Implementation Approach**:
1. Apply test pattern from DEBT-015
2. Prioritize most-used endpoints first
3. Add integration tests for dataframe operations
4. Consider contract testing for API stability

**Acceptance Criteria**:
- [ ] Test file created: `tests/api/test_routes_dataframes.py`
- [ ] Coverage >= 60% for `api/routes/dataframes.py`
- [ ] Critical paths (list, get, create) covered
- [ ] Error handling tested

**Risk Mitigations**:
- Depends on test pattern from DEBT-015; schedule after

**Verification Approach**:
```bash
pytest tests/api/test_routes_dataframes.py -v --cov=api/routes/dataframes --cov-report=term-missing
```

---

#### DEBT-014: API projects routes untested

**Risk Score**: 22 (HIGH)
**Module**: `api/routes/projects.py` (351 lines)
**Size**: M (2-3 days)
**Confidence**: Medium

**Problem Statement**:
Critical user-facing API with 0% coverage.

**Implementation Approach**:
1. Apply test pattern from DEBT-015
2. Cover project CRUD operations
3. Test project-specific operations (membership, custom fields)

**Acceptance Criteria**:
- [ ] Test file created: `tests/api/test_routes_projects.py`
- [ ] Coverage >= 60% for `api/routes/projects.py`
- [ ] Critical paths covered
- [ ] Integration with project-related services tested

**Risk Mitigations**:
- Schedule after DEBT-015 for pattern reuse

**Verification Approach**:
```bash
pytest tests/api/test_routes_projects.py -v --cov=api/routes/projects --cov-report=term-missing
```

---

#### DEBT-008: Half-open state max calls not enforced

**Risk Score**: 13 (MEDIUM)
**Module**: `transport/circuit_breaker.py:124-127`
**Size**: S (4-8 hours)
**Confidence**: High

**Problem Statement**:
In half-open state, the counter can exceed the intended limit, allowing more traffic than desired through a potentially failing service.

**Implementation Approach**:
1. Add atomic check-and-increment (threading.Lock or atomic counter)
2. Enforce strict limit on probing calls
3. Add tests for concurrent half-open access

**Acceptance Criteria**:
- [ ] Max calls in half-open state strictly enforced
- [ ] Concurrent access does not exceed limit
- [ ] Unit tests verify enforcement under concurrent load
- [ ] No change to circuit breaker state machine semantics

**Risk Mitigations**:
- Isolated change to circuit breaker module
- Can be included in Sprint 1 if capacity allows

**Verification Approach**:
```bash
pytest tests/unit/test_circuit_breaker*.py -v
```

---

### Sprint 2 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test collection errors | 0 | `pytest --collect-only` |
| API route coverage | >= 60% | Coverage report |
| CI reliability | Green builds | Pipeline status |
| Test pattern established | Yes | Documentation exists |

---

## Sprint 3: Concurrency & Refactoring

**Duration**: 2-3 weeks
**Theme**: Session safety, reduce maintenance burden
**Capacity Required**: 10-16 days engineering effort
**Prerequisites**: Sprint 1 & 2 complete (test infrastructure reliable)

### Sprint 3 Backlog

| Priority | ID | Title | Size | Effort | Confidence | Dependencies |
|----------|-----|-------|------|--------|------------|--------------|
| P0 | DEBT-003 | Session state transitions not atomic | M | 2-3 days | Medium | Investigation |
| P0 | DEBT-005 | Concurrent track() calls race condition | S | 1-2 days | Medium | DEBT-003 |
| P1 | DEBT-009 | Simple get/set bypass two-tier logic | M | 2-3 days | Medium | DEBT-001 |
| P1 | DEBT-006 | Batch executor assumes sequential results | S | 1-2 days | High | None |
| P2 | DEBT-004 | Cascade operations remain after partial failures | M | 2-3 days | Medium | None |
| P2 | DEBT-012 | Code duplication in field comparisons | M | 2-3 days | High | None |

**Sprint 3 Buffer**: 25% (~3 days) for concurrency complexity

### Package Details

---

#### DEBT-003: Session state transitions not atomic

**Risk Score**: 28 (HIGH)
**Module**: `persistence/session.py:47-58`
**Size**: M (2-3 days)
**Confidence**: Medium

**Problem Statement**:
`_state` attribute modified without lock protection. Race conditions possible in concurrent usage.

**Implementation Approach**:
1. **Investigation spike first**: Determine if multi-threaded usage actually occurs
2. If yes: Add threading.Lock for state transitions
3. If no: Document single-threaded requirement clearly
4. Either way: Add tests for state transition correctness

**Acceptance Criteria**:
- [ ] Thread-safety decision documented in code and API docs
- [ ] If thread-safe: Lock protects all state transitions
- [ ] If single-threaded: RuntimeError on concurrent access (defensive)
- [ ] Unit tests verify state machine correctness
- [ ] Integration test for documented usage pattern

**Risk Mitigations**:
- Investigation spike reduces uncertainty before implementation
- Can defer full thread-safety if usage doesn't require it

**Verification Approach**:
```bash
pytest tests/unit/test_session*.py -v

# If thread-safe implementation:
pytest tests/integration/test_session_concurrency.py -v
```

---

#### DEBT-005: Concurrent track() calls race condition

**Risk Score**: 21 (HIGH)
**Module**: `persistence/session.py:367`
**Size**: S (1-2 days)
**Confidence**: Medium

**Problem Statement**:
`track()` method modifies entity snapshots without synchronization.

**Implementation Approach**:
1. Add per-entity locking or document single-threaded requirement
2. Align with decision from DEBT-003

**Acceptance Criteria**:
- [ ] Consistent with DEBT-003 thread-safety decision
- [ ] If thread-safe: Per-entity lock prevents race
- [ ] Unit tests for concurrent tracking scenarios

**Risk Mitigations**:
- Bundle with DEBT-003 for consistent approach

**Verification Approach**:
```bash
pytest tests/unit/test_session_tracking*.py -v
```

---

#### DEBT-009: Simple get/set bypass two-tier logic

**Risk Score**: 21 (HIGH)
**Module**: `cache/tiered.py:129-156`
**Size**: M (2-3 days)
**Confidence**: Medium

**Problem Statement**:
Simple `get()` and `set()` methods bypass full two-tier logic (promotion, staleness, write-through).

**Implementation Approach**:
1. **After DEBT-001 fix**: Two-tier logic is reliable
2. Deprecate simple methods with warning
3. Route simple methods through full logic, or
4. Remove simple methods if not widely used

**Acceptance Criteria**:
- [ ] Simple methods deprecated or removed
- [ ] All cache access uses consistent behavior
- [ ] Migration guide if API breaking
- [ ] Tests verify consistent behavior regardless of method used

**Risk Mitigations**:
- Requires DEBT-001 completion first
- Audit callers before deprecation

**Verification Approach**:
```bash
pytest tests/unit/test_tiered*.py -v
pytest tests/integration/test_cache*.py -v
```

---

#### DEBT-006: Batch executor assumes sequential results

**Risk Score**: 18 (MEDIUM)
**Module**: `persistence/executor.py:106-108`
**Size**: S (1-2 days)
**Confidence**: High

**Problem Statement**:
No validation that result count matches input count. Results assumed sequential.

**Implementation Approach**:
1. Add validation: result count == request count
2. Consider request IDs for correlation (if API supports)
3. Fail fast on mismatch with clear error

**Acceptance Criteria**:
- [ ] Validation added for result count
- [ ] Clear error message on mismatch
- [ ] Unit tests for matched and mismatched scenarios
- [ ] No silent misattribution possible

**Risk Mitigations**:
- Straightforward validation; low risk

**Verification Approach**:
```bash
pytest tests/unit/test_executor*.py -v
```

---

#### DEBT-004: Cascade operations remain after partial failures

**Risk Score**: 15 (MEDIUM)
**Module**: `persistence/session.py:749-751`
**Size**: M (2-3 days)
**Confidence**: Medium

**Problem Statement**:
Failed cascade operations remain in queue without max retry counter. Infinite retry loops possible.

**Implementation Approach**:
1. Add max retry counter (configurable, default 3)
2. Implement exponential backoff
3. Move to dead-letter queue after max attempts
4. Log dead-letter entries for investigation

**Acceptance Criteria**:
- [ ] Max retry counter enforced
- [ ] Dead-letter mechanism for failed cascades
- [ ] Logging for dead-letter entries
- [ ] Unit tests for retry exhaustion

**Risk Mitigations**:
- Config allows tuning in production

**Verification Approach**:
```bash
pytest tests/unit/test_session_cascade*.py -v
```

---

#### DEBT-012: Code duplication in field comparisons

**Risk Score**: 16 (MEDIUM)
**Module**: `models/business/matching/engine.py:222-459`
**Size**: M (2-3 days)
**Confidence**: High

**Problem Statement**:
Four `_compare_*` methods (~150 lines each) follow identical pattern.

**Implementation Approach**:
1. Extract common comparison logic into base method
2. Use strategy pattern for field-specific behavior
3. Each field type provides config/strategy, not duplicate code

**Acceptance Criteria**:
- [ ] Single comparison method with field strategies
- [ ] Code reduction >= 50%
- [ ] All existing tests pass
- [ ] No change to comparison results

**Risk Mitigations**:
- Thorough existing test coverage protects refactor
- Can be done incrementally (one field at a time)

**Verification Approach**:
```bash
pytest tests/unit/test_matching*.py -v
pytest tests/integration/test_business_matching*.py -v
```

---

### Sprint 3 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Concurrency bugs resolved | 2 | DEBT-003, DEBT-005 |
| Cache API consistent | Yes | DEBT-009 resolved |
| Code duplication reduced | -50% | engine.py line count |
| Risk score reduction | -60 points | Ledger update |

---

## Deferred Items

Items not scheduled in the 3-sprint horizon with rationale and acceleration conditions.

### Deferred: Design Debt (Major Refactoring)

| ID | Title | Score | Rationale | Accelerate If |
|----|-------|-------|-----------|---------------|
| DEBT-018 | SaveSession bloat and complexity | 35 | Major refactor requiring dedicated sprint. Risk: introducing bugs during decomposition. | Critical bugs in session layer accumulate; new feature requires clean architecture |
| DEBT-019 | Tasks client overcrowded | 22 | Maintenance burden, not user risk. | Feature work requires extensive task client changes |
| DEBT-061 | Pipeline automation complexity | N/A | Similar to DEBT-018; implicit state machine | New pipeline features needed |

**Recommendation**: Schedule DEBT-018 as a dedicated decomposition sprint (Sprint 4) after stabilizing with Sprints 1-3. Decomposition plan:
1. Extract StateManager
2. Extract ActionQueue
3. Extract CascadeHandler
4. Extract CommitExecutor

### Deferred: Coverage Gaps (Lower Priority)

| ID | Title | Score | Rationale | Accelerate If |
|----|-------|-------|-----------|---------------|
| DEBT-016 | Goals client low coverage | 17 | Large client (1,124 lines) but lower usage risk | Goals feature work planned |
| DEBT-017 | Portfolios client low coverage | 15 | Same as above | Portfolios feature work planned |
| DEBT-052 | Attachments client limited coverage | N/A | Limited usage | Attachments bugs reported |
| DEBT-053-055 | Tags/Teams/Webhooks partial coverage | N/A | Lower priority clients | Feature work in those areas |

**Recommendation**: Address during feature work in those modules, not dedicated coverage sprints.

### Deferred: Config & Low Severity

| ID | Title | Score | Rationale | Accelerate If |
|----|-------|-------|-----------|---------------|
| DEBT-011 | SearchCriteria OR combinator unsupported | 6 | Low impact; remove field or implement on demand | Users request OR queries |
| DEBT-030-031 | Hardcoded TTL/rate limits | N/A | Config debt, low risk | Deployment to different environment needs tuning |
| DEBT-056-059 | Unit extraction TODOs | N/A | Feature incomplete, not debt | Unit DataFrame feature prioritized |

### Deferred: Medium Severity (Capacity Dependent)

| ID | Title | Score | Rationale | Accelerate If |
|----|-------|-------|-----------|---------------|
| DEBT-021 | Healing queue operations not fail-safe | N/A | Rare path | Healing failures observed |
| DEBT-024 | Snapshot comparison non-determinism | N/A | Edge case | Intermittent test failures |
| DEBT-036 | Repeated sync/async wrapper pattern | N/A | Duplication, not risk | Async refactor planned |

---

## Dependencies & Sequencing

### Critical Path

```
Sprint 1:
  DEBT-007, DEBT-010 (parallel, quick wins)
      |
  DEBT-001, DEBT-002 (parallel, critical fixes)
      |
      v
Sprint 2:
  DEBT-020 (unblocks test infrastructure)
      |
  DEBT-015 (establishes test pattern)
      |
  DEBT-013, DEBT-014 (parallel, apply pattern)
      |
  DEBT-008 (independent, fills capacity)
      |
      v
Sprint 3:
  Investigation spike (DEBT-003 usage patterns)
      |
  DEBT-003 -> DEBT-005 (sequential, shared context)
      |
  DEBT-009 (depends on DEBT-001 completion)
      |
  DEBT-006, DEBT-004, DEBT-012 (parallel, independent)
```

### Dependency Matrix

| Item | Depends On | Blocks |
|------|------------|--------|
| DEBT-001 | None | DEBT-009 |
| DEBT-002 | None | None |
| DEBT-003 | Investigation spike | DEBT-005 |
| DEBT-005 | DEBT-003 decision | None |
| DEBT-007 | None | None |
| DEBT-008 | None | None |
| DEBT-009 | DEBT-001 | None |
| DEBT-010 | None | None |
| DEBT-013 | DEBT-015 pattern | None |
| DEBT-014 | DEBT-015 pattern | None |
| DEBT-015 | DEBT-020 (soft) | DEBT-013, DEBT-014 |
| DEBT-020 | None | DEBT-015 (soft) |

### Items That Must Be Done Together

1. **Session Concurrency** (DEBT-003 + DEBT-005): Same module, same decision (thread-safe vs documented single-threaded)
2. **API Route Tests** (DEBT-013 + DEBT-014 + DEBT-015): Share test infrastructure, apply consistent pattern
3. **Circuit Breaker** (DEBT-007 + DEBT-008): Same module, can be one PR

### Recommended Order Within Sprints

**Sprint 1**:
1. DEBT-007, DEBT-010 (quick wins, build momentum)
2. DEBT-001 (higher complexity, start early)
3. DEBT-002 (parallel with DEBT-001 if separate engineers)

**Sprint 2**:
1. DEBT-020 (unblock everything)
2. DEBT-015 (establish pattern)
3. DEBT-008 (independent, fills gaps)
4. DEBT-013, DEBT-014 (parallel, apply pattern)

**Sprint 3**:
1. Investigation spike for DEBT-003
2. DEBT-003 + DEBT-005 (together)
3. DEBT-009 (after DEBT-001 verified in production)
4. DEBT-006, DEBT-004, DEBT-012 (parallel, fill capacity)

---

## Success Metrics

### Overall Program Metrics

| Metric | Baseline | Sprint 1 | Sprint 2 | Sprint 3 |
|--------|----------|----------|----------|----------|
| CRITICAL items | 3 | 1 | 0 | 0 |
| HIGH items | 8 | 6 | 2 | 0 |
| Test collection errors | 151 | 151 | 0 | 0 |
| API route coverage | 0% | 0% | 60%+ | 60%+ |
| Risk score (Top 10) | 287 | 207 | 171 | ~120 |

### Sprint 1 Verification

| What to Verify | How | Acceptance |
|----------------|-----|------------|
| Cache consistency | Integration test simulating L2 failure | No stale reads |
| Action preservation | Unit test with partial commit failure | Failed actions returned |
| Exception logging | Log inspection | All circuit breaker exceptions logged |
| Lock file safety | Unit test with early OSError | No UnboundLocalError |

### Sprint 2 Verification

| What to Verify | How | Acceptance |
|----------------|-----|------------|
| Test collection | `pytest --collect-only` | 0 errors |
| Route coverage | Coverage report | >= 60% each route |
| CI stability | 5 consecutive green builds | No collection failures |

### Sprint 3 Verification

| What to Verify | How | Acceptance |
|----------------|-----|------------|
| Concurrency safety | Concurrent access tests | No race conditions |
| Cache API consistency | All paths use same logic | Deprecated methods removed |
| Batch validation | Mismatched result test | Clear error on mismatch |

### Risk Score Reduction Goals

**Target**: Reduce total risk score of Top 10 items by 58% (287 -> ~120)

| Sprint | Items Resolved | Score Reduction |
|--------|----------------|-----------------|
| Sprint 1 | DEBT-001, DEBT-002, DEBT-007, DEBT-010 | -111 points |
| Sprint 2 | DEBT-020, DEBT-013, DEBT-014, DEBT-015, DEBT-008 | -109 points |
| Sprint 3 | DEBT-003, DEBT-005, DEBT-009, DEBT-006, DEBT-004, DEBT-012 | -125 points |

---

## Capacity Planning Notes

### Assumptions

- 1 engineer = 5-8 productive days per 2-week sprint
- Buffer accounts for meetings, reviews, and unexpected issues
- Estimates assume familiarity with codebase; add 20% for new team members

### Recommended Team Allocation

| Sprint | Minimum | Recommended | Notes |
|--------|---------|-------------|-------|
| Sprint 1 | 1 engineer | 2 engineers | Critical items can parallel |
| Sprint 2 | 1 engineer | 2 engineers | Test work can parallel |
| Sprint 3 | 2 engineers | 3 engineers | More items, complexity |

### If Capacity Constrained

**Sprint 1 Must-Haves**: DEBT-001, DEBT-002 (data integrity non-negotiable)
**Sprint 1 Nice-to-Haves**: DEBT-007, DEBT-010 (quick wins, can slip)

**Sprint 2 Must-Haves**: DEBT-020 (unblocks CI)
**Sprint 2 Nice-to-Haves**: API route tests (can extend to Sprint 3)

**Sprint 3 Must-Haves**: DEBT-003, DEBT-005 (if concurrency used)
**Sprint 3 Nice-to-Haves**: DEBT-012 (refactoring, can defer further)

---

## Feedback Loop

### During Sprint

- Track actual vs estimated effort for calibration
- Document new debt discovered during remediation
- Report blockers immediately for re-sequencing

### After Each Sprint

| Feedback Item | Action |
|---------------|--------|
| Actual effort data | Update T-shirt size calibration |
| New debt items | Route to Debt Collector |
| Changed risk assessment | Route to Risk Assessor |
| Deferred item conditions met | Re-prioritize for next sprint |

### Calibration Data Template

| Item | Estimated | Actual | Variance | Notes |
|------|-----------|--------|----------|-------|
| DEBT-001 | 3-5 days | TBD | | |
| DEBT-002 | 3-5 days | TBD | | |
| ... | | | | |

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| Debt Ledger (Input) | /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-114714-3062657f/artifacts/DEBT-LEDGER-20251228.md | YES |
| Risk Report (Input) | /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-114714-3062657f/artifacts/RISK-REPORT-20251228.md | YES |
| Sprint Plan (Output) | /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20251228-114714-3062657f/artifacts/SPRINT-PLAN-20251228.md | YES |

---

*Generated by Sprint Planner - debt-triage-pack*
*Ready for engineering sprint planning*
