# PRD: SaveSession Decomposition

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-SPRINT-4-SAVESESSION-DECOMPOSITION |
| **Status** | Completed |
| **Author** | Requirements Analyst |
| **Created** | 2025-12-19 |
| **Last Updated** | 2025-12-25 |
| **Completed** | 2025-12-22 |
| **Stakeholders** | SDK Maintainers, Integration Developers |
| **Related PRDs** | None |
| **Discovery Doc** | [DISCOVERY-SAVESESSION-DECOMPOSITION.md](/docs/analysis/DISCOVERY-SAVESESSION-DECOMPOSITION.md) |

---

## Problem Statement

### What problem are we solving?

SaveSession (`persistence/session.py`) has grown to 2193 lines with 50 methods, exhibiting classic "god class" symptoms. Despite architectural discipline (delegation to ChangeTracker, SavePipeline, ActionExecutor, etc.), the file remains a maintenance burden:

1. **Cognitive Overhead**: 18 action methods (920 lines, 42%) follow identical boilerplate patterns, obscuring the core logic.
2. **Mixed Responsibilities**: Session lifecycle, action registration, healing coordination, and commit orchestration interleave.
3. **Testing Friction**: Large file means slower iteration; tests access private attributes due to missing getters.
4. **Onboarding Cost**: New contributors must understand 2000+ lines to make changes safely.

### For whom?

- **SDK Maintainers**: Currently navigate 50 methods to find relevant code.
- **Integration Developers**: Docstrings and examples buried in massive file.
- **QA**: Test isolation difficult with monolithic class.

### What is the impact of not solving it?

- Continued velocity loss on SaveSession-related features.
- Higher bug introduction risk during maintenance.
- Technical debt compounds as new features (automation, healing) add more code.

### Validation

The discovery analysis confirmed:
- **82% reduction target validated**: Heavy lifting already delegated to extracted components.
- **Highest-value target identified**: 18 action methods can consolidate from 920 lines to ~150 lines.
- **Backward compatibility achievable**: All public API signatures can remain unchanged.

---

## Goals & Success Metrics

### Primary Goal

Reduce SaveSession from 2193 lines to ~400 lines (82% reduction) through targeted extraction while preserving 100% backward compatibility.

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Line count reduction | 82% (2193 -> ~400) | `wc -l session.py` |
| Public API changes | 0 | Signature comparison |
| Test pass rate | 100% | `pytest tests/unit/persistence/test_session*.py` |
| Commit latency regression | <5% | Benchmark: 100 entities + 50 actions |
| Memory regression | None | Benchmark: 1000 tracked entities |

### Secondary Goals

1. Improve code discoverability (action logic in one place, healing in one place).
2. Enable independent testing of extracted components.
3. Reduce test file reliance on private attribute access.

---

## Scope

### In Scope

| Component | Current Lines | Target Lines | Action |
|-----------|---------------|--------------|--------|
| Action Method Factory | 920 | ~150 | Extract to `ActionBuilder` or decorator pattern |
| State Manager | ~100 | ~50 in new module | Extract `SessionState`, lifecycle, context managers |
| Healing Manager | ~165 | ~50 in new module | Unify with existing `persistence/healing.py` |
| Commit Orchestrator | ~160 | ~60 in new module | Extract five-phase coordination |
| Inspection Getters | N/A | ~20 new lines | Add properties for `state`, `healing_queue`, etc. |

**Total Extraction Target**: ~1345 lines moved, ~400 lines remaining in SaveSession.

### Out of Scope

| Item | Rationale |
|------|-----------|
| `_track_recursive()` refactoring | HIGH coupling to BusinessEntity internals; defer to entity refactoring |
| ChangeTracker modifications | Already well-factored; no value in moving |
| SavePipeline modifications | Already well-factored; no value in moving |
| EventSystem modifications | Already well-factored; no value in moving |
| ActionExecutor modifications | Already well-factored; no value in moving |
| CascadeExecutor modifications | Already well-factored; no value in moving |
| Thread-safety additions | Design decision: asyncio context only |
| `max_concurrent` implementation | Reserved parameter; not functional |

---

## Requirements

### Functional Requirements - Action Method Factory

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ACTION-001 | Create `ActionBuilder` class or decorator pattern to consolidate 18 action methods into reusable infrastructure | Must | All 18 methods generated from shared infrastructure |
| FR-ACTION-002 | `ActionBuilder` must support three action variants: no-target (like, comment), target-required (tag, project, dependency), and positioning-enabled (add_to_project, move_to_section, set_parent) | Must | Each variant has single implementation, methods differ only in configuration |
| FR-ACTION-003 | All generated methods must preserve exact public signatures per Discovery Section 7.1 | Must | Signature comparison shows 0 differences |
| FR-ACTION-004 | All generated methods must return `self` for fluent chaining | Must | `session.add_tag(t, "x").add_to_project(t, "y")` works |
| FR-ACTION-005 | All generated methods must call `_ensure_open()` as first operation | Must | SessionClosedError raised on closed session |
| FR-ACTION-006 | All generated methods must append `ActionOperation` to `_pending_actions` | Must | `get_pending_actions()` returns correct operations |
| FR-ACTION-007 | All generated methods must log if `_log` is present | Should | Debug log entries match current format |
| FR-ACTION-008 | Positioning-enabled methods must validate `insert_before`/`insert_after` exclusivity and raise `PositioningConflictError` | Must | `test_*_with_both_raises_positioning_conflict_error` passes |
| FR-ACTION-009 | `add_comment` must validate non-empty text and raise `ValueError` | Must | `test_add_comment_empty_raises_value_error` passes |
| FR-ACTION-010 | `reorder_subtask` must validate entity has parent and raise `ValueError` | Must | `test_reorder_subtask_raises_for_task_without_parent` passes |
| FR-ACTION-011 | Batch methods (`add_followers`, `remove_followers`) must loop over inputs and create individual operations | Must | Equivalent to multiple single calls |

### Functional Requirements - State Manager

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-STATE-001 | Extract `SessionState` enum to separate module or keep in session.py | Could | Enum accessible via same import path |
| FR-STATE-002 | Centralize `_ensure_open()` logic with clear state validation | Must | Single implementation, called from all operations |
| FR-STATE-003 | Extract context manager logic (`__aenter__`, `__aexit__`, `__enter__`, `__exit__`) to use shared state transitions | Should | Context managers work identically |
| FR-STATE-004 | Add `state` property for public read access to session state | Must | Tests can use `session.state` instead of `session._state` |
| FR-STATE-005 | Preserve state transition invariants: OPEN -> COMMITTED -> CLOSED | Must | State diagram from Discovery Section 2 holds |

### Functional Requirements - Healing Manager

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-HEAL-001 | Extract healing logic to dedicated `HealingManager` class or merge with `persistence/healing.py` | Should | Healing logic in one location |
| FR-HEAL-002 | `HealingManager` must implement `should_heal(entity, override)` with tier-based logic | Must | All `TestShouldHeal` tests pass |
| FR-HEAL-003 | `HealingManager` must implement `queue_healing(entity, project_gid)` with deduplication | Must | Same entity not queued twice |
| FR-HEAL-004 | `HealingManager` must implement `execute_healing_async()` with non-blocking failures | Must | Healing failures do not raise; logged and reported |
| FR-HEAL-005 | Healing queue cleared after execution (success or failure) | Must | `test_healing_queue_cleared_*` tests pass |
| FR-HEAL-006 | Add `healing_queue` property for test inspection | Should | Tests use property instead of `_healing_queue` |

### Functional Requirements - Commit Orchestrator

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-COMMIT-001 | Extract five-phase commit logic to `CommitOrchestrator` or internal method grouping | Should | Clear phase separation in code |
| FR-COMMIT-002 | Preserve exact phase ordering: CRUD+Actions -> Cascades -> Healing -> Automation | Must | Discovery Section 1.5 ordering maintained |
| FR-COMMIT-003 | Preserve custom field tracking reset BEFORE snapshot capture (DEF-001 fix) | Must | `TestCustomFieldTrackingReset` passes |
| FR-COMMIT-004 | Preserve selective action clearing on partial failure (ADR-0066) | Must | `TestSelectiveActionClearing` passes |
| FR-COMMIT-005 | Preserve cascade preservation on failure | Must | `test_cascades_preserved_on_failure` passes |
| FR-COMMIT-006 | Preserve automation failure isolation (exception swallowed, logged) | Must | Automation failure does not raise from commit |
| FR-COMMIT-007 | Preserve post-commit hook emission after all phases | Must | `on_post_commit` called with complete `SaveResult` |
| FR-COMMIT-008 | Empty session commit logs warning and returns empty `SaveResult` | Must | `test_commit_async_empty_session` passes |

### Functional Requirements - Inspection APIs

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-INSP-001 | Add `state` property returning `SessionState` | Must | `session.state == SessionState.OPEN` works |
| FR-INSP-002 | Add `auto_heal` property returning bool | Should | `session.auto_heal` returns config value |
| FR-INSP-003 | Add `automation_enabled` property returning bool | Should | `session.automation_enabled` returns config value |
| FR-INSP-004 | Add `pending_healing_count` property returning int | Should | `session.pending_healing_count == 3` works |
| FR-INSP-005 | Deprecate test access to `_pending_actions` in favor of `get_pending_actions()` | Should | Tests updated, no direct access |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | All public API signatures unchanged | 100% | Signature diff tool |
| NFR-COMPAT-002 | All public imports from `persistence/__init__.py` unchanged | 100% | Import test |
| NFR-COMPAT-003 | All exception types unchanged | 100% | Exception type comparison |
| NFR-COMPAT-004 | Fluent chaining preserved for all action methods | 100% | Return type is SaveSession |
| NFR-PERF-001 | Commit latency regression | <5% | Benchmark: 100 entities + 50 actions |
| NFR-PERF-002 | Memory usage regression | None | Benchmark: 1000 tracked entities |
| NFR-PERF-003 | Action registration overhead | <1ms per action | Benchmark: 100 action registrations |
| NFR-TEST-001 | All existing tests pass without modification (green bar) | 100% | `pytest tests/unit/persistence/test_session*.py` |
| NFR-TEST-002 | Test coverage for extracted components | >95% | Coverage report |
| NFR-MAINT-001 | Each extracted module <200 lines | All | `wc -l` per module |
| NFR-MAINT-002 | Cyclomatic complexity per function <10 | All | Static analysis |

---

## User Stories / Use Cases

### UC-1: SDK Developer Adds New Action Type

**Before Decomposition**:
1. Developer opens 2193-line session.py
2. Scrolls to find action methods (~line 900)
3. Copies existing action method (~50 lines)
4. Modifies for new action type
5. Tests entire session to verify

**After Decomposition**:
1. Developer opens ~150-line action_builder.py
2. Adds new action configuration (3-5 lines)
3. Action method auto-generated
4. Tests action module in isolation

### UC-2: SDK Developer Debugs Healing Issue

**Before Decomposition**:
1. Developer searches session.py for healing-related code
2. Finds `_should_heal`, `_queue_healing`, `_execute_healing_async` scattered
3. Also finds `persistence/healing.py` with standalone utilities
4. Confusion about which path is active

**After Decomposition**:
1. Developer opens healing.py (single source)
2. All healing logic in one module
3. Clear separation of session-integrated vs. standalone utilities

### UC-3: Integration Developer Inspects Session State

**Before Decomposition**:
```python
# Accessing private attribute (fragile)
if session._state == SessionState.OPEN:
    ...
if session._auto_heal:
    ...
```

**After Decomposition**:
```python
# Using public properties (stable)
if session.state == SessionState.OPEN:
    ...
if session.auto_heal:
    ...
```

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| BusinessEntity private attribute access in `_track_recursive()` is acceptable for now | Documented as out-of-scope coupling; deferred to entity refactoring |
| asyncio single-threaded context is sufficient | Documented thread-safety limitation; no current multi-threaded use cases |
| Existing test suite provides sufficient coverage for refactoring | 3516 test lines, 1.6x coverage ratio |
| Decorator/factory pattern for actions is technically feasible | Common Python pattern; prototyping recommended in TDD |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `persistence/healing.py` exists | SDK Team | Complete |
| `ActionExecutor` interface stable | SDK Team | Complete |
| `SavePipeline.execute_with_actions()` interface stable | SDK Team | Complete |
| All test_session*.py tests passing | QA | Complete |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should `ActionBuilder` use decorators, metaclass, or factory pattern? | Architect | Pre-TDD | Architect recommends in TDD |
| Should `HealingManager` be merged into existing `healing.py` or stay separate? | Architect | Pre-TDD | Architect decides based on import cycle analysis |
| Should `SessionState` enum move to `models.py` or stay in session? | Architect | Pre-TDD | Low impact; Architect decides |
| Should we add `get_healing_queue()` or property? | Requirements | Resolved | Property preferred for consistency |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Subtle behavior regression in action methods | Medium | High | Comprehensive test suite; characterization tests before refactoring |
| Performance regression from delegation overhead | Low | Medium | Benchmark before/after; inline if necessary |
| Import cycle from new module structure | Medium | Medium | Architect to analyze in TDD; use TYPE_CHECKING imports |
| Test breakage from private attribute access | High | Low | Add getters/properties before refactoring |
| Missing edge case in action factory pattern | Medium | High | Port all existing tests; review Discovery Section 5 edge cases |

---

## Implementation Phases

### Phase 1: Foundation (Preparation)

1. Add inspection properties (`state`, `auto_heal`, `automation_enabled`, `pending_healing_count`)
2. Update tests to use properties instead of private attributes
3. Create baseline benchmarks

**Exit Criteria**: All tests green, benchmarks documented

### Phase 2: Action Method Factory

1. Design and implement `ActionBuilder` pattern (TDD to specify)
2. Replace 18 action methods with generated equivalents
3. Verify all action tests pass

**Exit Criteria**: 920 lines reduced to ~150 lines, all tests green

### Phase 3: State Manager

1. Extract state management to internal organization or new module
2. Centralize `_ensure_open()` and context managers
3. Verify lifecycle tests pass

**Exit Criteria**: Clear state boundary, all tests green

### Phase 4: Healing Manager

1. Extract healing logic to dedicated module or merge with `healing.py`
2. Add healing inspection APIs
3. Verify healing tests pass

**Exit Criteria**: Single healing location, all tests green

### Phase 5: Commit Orchestrator (Optional)

1. Evaluate commit logic organization
2. Extract if >100 lines remain after other extractions
3. Verify commit tests pass

**Exit Criteria**: Commit logic organized, all tests green

### Phase 6: Validation

1. Run full benchmark suite
2. Compare before/after metrics
3. Verify 82% reduction achieved

**Exit Criteria**: All success metrics met

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Requirements Analyst | Initial draft from discovery analysis |

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] No open questions blocking design (owners assigned, low-impact)
- [x] Risk register with mitigations
- [x] Success metrics defined

**PRD Status**: Ready for Architect Review
