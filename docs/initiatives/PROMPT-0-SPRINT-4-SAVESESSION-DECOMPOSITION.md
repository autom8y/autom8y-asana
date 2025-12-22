# Orchestrator Initialization: Sprint 4 - SaveSession Decomposition

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, SaveSession, Unit of Work, persistence layer
  - Activates when: Working with SaveSession, persistence patterns

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

**How Skills Work**: Skills load automatically based on your current task. When you need SaveSession patterns, the `autom8-asana` skill activates.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Decompose SaveSession God Class into Focused Modules

Sprint 4 addresses the session.py god class (2192 lines, 14+ responsibilities) by decomposing it into focused, cohesive modules. SaveSession is the heart of the persistence layer - it must be decomposed carefully to preserve the Unit of Work pattern while enabling maintainable development.

**This is HIGH RISK** because SaveSession is the core of the persistence layer and is used by all business entity operations.

### Why This Sprint?

- **God Class**: session.py at 2192 lines with 14+ responsibilities violates SRP severely
- **Change Fragility**: Any modification risks breaking unrelated functionality
- **Testing Complexity**: Hard to test individual responsibilities in isolation
- **Mental Model**: Developers must understand entire file to modify any part
- **Coupling**: High internal coupling makes refactoring difficult

### Current State

**SaveSession Responsibilities (14+ identified)**:
1. State management (SessionState enum, state transitions)
2. Entity tracking (dirty detection, identity map)
3. PlannedOperation management (CRUD, cascade, actions)
4. ActionOperation handling (add_tag, move_section, etc.)
5. Self-healing logic (detect misplaced entities, correct)
6. Commit orchestration (phase execution, error handling)
7. Transaction semantics (rollback, savepoints)
8. Batch operation building (group operations for API)
9. Result collection (SaveResult construction)
10. Hook/callback management (pre-commit, post-commit)
11. Entity registration (add, remove, attach)
12. Change detection (field-level dirty tracking)
13. Relationship management (parent-child, holder references)
14. Validation (entity validation before commit)

**Current Structure**:
```
src/autom8_asana/persistence/
    session.py          # 2192 lines - EVERYTHING
```

### Sprint Profile

| Attribute | Value |
|-----------|-------|
| Duration | 3 weeks |
| Phase | 5 (SaveSession Decomposition) |
| Risk Level | HIGH |
| Blast Radius | Core persistence + all callers |
| Prerequisites | Sprints 1-3 complete, Responsibility mapping spike |
| Key Pattern | Composition over inheritance |

### Target Architecture

**After Decomposition**:
```
src/autom8_asana/persistence/session/
    __init__.py           # Re-exports: SaveSession
    state.py              # SessionState, state machine, transitions
    tracking.py           # Entity tracking, identity map, dirty detection
    operations.py         # PlannedOperation management, queuing
    actions.py            # ActionOperation handling
    healing.py            # Self-healing logic
    commit.py             # Commit orchestration
    batch.py              # Batch operation building
    result.py             # SaveResult construction
```

**Line Distribution Target**:
| Module | Estimated Lines | Responsibility |
|--------|-----------------|----------------|
| state.py | ~200 | State machine, transitions |
| tracking.py | ~350 | Entity tracking, dirty detection |
| operations.py | ~300 | PlannedOperation management |
| actions.py | ~250 | ActionOperation handling |
| healing.py | ~200 | Self-healing logic |
| commit.py | ~400 | Commit orchestration |
| batch.py | ~200 | Batch building |
| result.py | ~150 | SaveResult construction |
| **Total** | ~2050 | Same behavior, better structure |

**Composition Pattern**:
```python
# session/__init__.py
class SaveSession:
    """Facade that composes focused modules."""

    def __init__(self, ...):
        self._state = StateMachine()
        self._tracker = EntityTracker()
        self._operations = OperationQueue()
        self._actions = ActionHandler()
        self._healer = SelfHealer()
        self._committer = CommitOrchestrator()

    async def commit(self):
        self._state.transition_to(SessionState.COMMITTING)
        await self._committer.execute(
            self._operations,
            self._actions,
            self._healer
        )
        self._state.transition_to(SessionState.COMMITTED)
```

### Key Constraints

- **Backward Compatibility**: SaveSession public API must not change
- **No Behavior Changes**: Every edge case must be preserved
- **Composition Pattern**: Modules composed, not inherited
- **Test Preservation**: All existing tests must pass unchanged
- **Transactionality**: Commit semantics must be preserved exactly
- **Performance**: No regression in commit latency

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Create session/ package structure | Must |
| Extract state management to state.py | Must |
| Extract entity tracking to tracking.py | Must |
| Extract operation management to operations.py | Must |
| Extract action handling to actions.py | Must |
| Extract self-healing to healing.py | Must |
| Extract commit logic to commit.py | Must |
| Extract batch building to batch.py | Must |
| Extract result construction to result.py | Should |
| Create SaveSession facade | Must |
| Maintain backward compatibility | Must |
| Preserve all existing tests | Must |
| Add module-specific tests | Should |
| Document module responsibilities | Should |

### Success Criteria

1. session.py deleted (replaced by session/ package)
2. `from autom8_asana.persistence.session import SaveSession` works
3. All existing tests pass without modification
4. Each module is <400 lines
5. Each module has single responsibility
6. Commit semantics unchanged
7. Performance within 5% of baseline

### Performance Targets

| Metric | Before | After |
|--------|--------|-------|
| Commit latency (small batch) | Baseline | <5% regression |
| Commit latency (large batch) | Baseline | <5% regression |
| Memory per session | Baseline | No regression |
| Import time | Baseline | <15% increase |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **0: Responsibility Spike** | Architect | Responsibility map, decomposition seams |
| **1: Discovery** | Requirements Analyst | Full responsibility inventory, dependency graph |
| **2: Requirements** | Requirements Analyst | PRD-SPRINT-4-SAVESESSION-DECOMPOSITION |
| **3: Architecture** | Architect | TDD-SPRINT-4 with module boundaries and interfaces |
| **4: Implementation P1** | Principal Engineer | Package structure, state.py, tracking.py |
| **5: Implementation P2** | Principal Engineer | operations.py, actions.py, healing.py |
| **6: Implementation P3** | Principal Engineer | commit.py, batch.py, result.py, facade |
| **7: Validation** | QA/Adversary | Transactionality, performance, regression |

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `session.py` | All class methods and their responsibilities |
| `session.py` | All instance variables and their purposes |
| `session.py` | State machine transitions and guards |
| `session.py` | Commit phase ordering and dependencies |
| `pipeline.py` | How does pipeline interact with session? |
| `action_executor.py` | How do actions integrate with session? |
| `models.py` | SaveResult, PlannedOperation structures |

### Responsibility Analysis

| Responsibility | Questions |
|----------------|-----------|
| State management | What states exist? What transitions? Guards? |
| Entity tracking | How is identity map managed? Dirty detection? |
| Operations | How are operations queued? Ordered? Deduplicated? |
| Actions | How do actions differ from operations? |
| Healing | When does healing trigger? What can be healed? |
| Commit | What's the phase order? Error handling? Rollback? |
| Batching | How are operations batched for API? |

### Dependency Analysis

| Dependency | Questions |
|------------|-----------|
| Internal | Which responsibilities depend on which? |
| External | What external modules does session use? |
| Circular | Any potential circular dependencies? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Architecture Questions (from Spike)

1. **Decomposition seams**: Where are the natural boundaries between responsibilities?
2. **Shared state**: How do modules share session state without tight coupling?
3. **Circular prevention**: How to avoid circular dependencies between modules?

### Behavior Questions

4. **Commit atomicity**: Can commit phases be in separate modules while maintaining atomicity?
5. **Error propagation**: How do errors flow between modules?
6. **Rollback scope**: What state must be rolled back on failure?

### Interface Questions

7. **Module interfaces**: What's the contract between modules?
8. **Event/hook pattern**: How do modules communicate without coupling?
9. **Testing seams**: How do we test modules in isolation?

---

## Scope Boundaries

### Explicitly In Scope

- Create session/ package
- Extract all 14+ responsibilities to modules
- Create SaveSession facade
- Maintain backward compatibility
- All existing tests pass
- Add module-specific tests
- Document module responsibilities

### Explicitly Out of Scope

- SaveSession API changes
- New SaveSession features
- Performance optimization (beyond no regression)
- Pipeline changes
- Action executor changes
- Model changes (SaveResult, PlannedOperation)
- Automation layer changes

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking commit semantics | Medium | Critical | Extensive test coverage, incremental extraction |
| Circular dependencies | High | High | Careful dependency analysis, interface pattern |
| Performance regression | Medium | Medium | Benchmark before/after each phase |
| Hidden dependencies | Medium | High | Thorough discovery, integration testing |
| State management complexity | High | High | Clear state machine module, explicit transitions |
| Test gaps for edge cases | Medium | High | Audit test coverage before starting |

---

## Dependencies

### Prerequisites

| Dependency | Status | Notes |
|------------|--------|-------|
| Sprint 3 complete | Required | Detection may use session |
| Responsibility mapping spike | Required | Needed for decomposition plan |
| Test suite passing | Required | Baseline for regression |
| Performance baseline | Required | Benchmark before starting |

### Blocks Future Work

| Dependent | Notes |
|-----------|-------|
| Sprint 5 (Cleanup) | May need session references |
| Future automation work | Hooks in commit.py |

---

## Responsibility Spike

**Goal**: Map SaveSession responsibilities and identify decomposition seams.

**Duration**: 3-4 hours (run before Sprint 4)

**Tasks**:
1. Catalog all SaveSession methods (expect 30+)
2. Group methods by responsibility (14+ groups)
3. Map dependencies between responsibility groups
4. Identify shared state requirements
5. Propose module boundaries
6. Identify circular dependency risks
7. Document decomposition order

**Output**: Decomposition map with:
- Responsibility -> Module mapping
- Dependency graph between modules
- Shared state protocol
- Extraction order (least dependent first)

---

## Module Design Sketches

### state.py
```python
class SessionState(Enum):
    ACTIVE = "active"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"

class StateMachine:
    def __init__(self):
        self._state = SessionState.ACTIVE

    def transition_to(self, state: SessionState) -> None:
        """Validate and execute state transition."""
        ...
```

### tracking.py
```python
class EntityTracker:
    def __init__(self):
        self._identity_map: dict[str, BusinessEntity] = {}
        self._dirty: set[str] = set()

    def track(self, entity: BusinessEntity) -> None:
        ...

    def is_dirty(self, entity: BusinessEntity) -> bool:
        ...
```

### operations.py
```python
class OperationQueue:
    def __init__(self):
        self._operations: list[PlannedOperation] = []

    def add(self, operation: PlannedOperation) -> None:
        ...

    def by_phase(self, phase: OperationPhase) -> list[PlannedOperation]:
        ...
```

### commit.py
```python
class CommitOrchestrator:
    async def execute(
        self,
        operations: OperationQueue,
        actions: ActionHandler,
        healer: SelfHealer,
    ) -> SaveResult:
        """Execute commit phases in order."""
        # Phase 1: CRUD
        # Phase 2: Cascade
        # Phase 3: Actions
        # Phase 4: Healing (if enabled)
        ...
```

---

## Your First Task

Confirm understanding by:

1. Summarizing the Sprint 4 goal (Decompose SaveSession into focused modules)
2. Listing the 8 sessions (including Session 0: Responsibility Spike)
3. Identifying this as HIGH RISK affecting core persistence
4. Confirming the composition pattern over inheritance
5. Noting the spike must complete before Session 1
6. Noting the key constraint: commit semantics must be preserved exactly

**Do NOT begin any session yet. Responsibility spike must complete first.**

---

# Session Trigger Prompts

## Session 0: Responsibility Spike

```markdown
Begin Session 0: SaveSession Responsibility Mapping Spike

Work with the @architect agent to map responsibilities and decomposition seams.

**Goals:**
1. Catalog all SaveSession methods (30+ expected)
2. Group methods by responsibility (14+ groups expected)
3. Map dependencies between groups
4. Identify shared state requirements
5. Propose module boundaries
6. Identify circular dependency risks
7. Document extraction order

**Files to Analyze:**
- `src/autom8_asana/persistence/session.py` (2192 lines)
- `src/autom8_asana/persistence/pipeline.py`
- `src/autom8_asana/persistence/action_executor.py`
- `src/autom8_asana/persistence/models.py`

**Deliverable:**
Decomposition map with:
- Method inventory with responsibility assignment
- Responsibility -> Module mapping
- Dependency graph (responsibility to responsibility)
- Shared state protocol
- Circular dependency mitigation
- Extraction order

Create the analysis plan first. I'll review before you execute.
```

## Session 1: Discovery

```markdown
Begin Session 1: SaveSession Discovery

Work with the @requirements-analyst agent for deep session.py analysis.

**Prerequisites:**
- Responsibility spike complete

**Goals:**
1. Verify responsibility mapping from spike
2. Document all state transitions and guards
3. Document commit phase ordering
4. Document error handling patterns
5. Map test coverage per responsibility
6. Identify hidden dependencies

**Files to Analyze:**
- `src/autom8_asana/persistence/session.py`
- `tests/unit/persistence/test_session.py`
- Integration tests using SaveSession

**Deliverable:**
A discovery document with:
- Verified responsibility inventory
- State transition diagram
- Commit phase documentation
- Error handling patterns
- Test coverage map
- Hidden dependency registry

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: SaveSession Decomposition Requirements

Work with the @requirements-analyst agent to create PRD-SPRINT-4-SAVESESSION-DECOMPOSITION.

**Prerequisites:**
- Session 1 discovery complete
- Responsibility spike complete

**Goals:**
1. Define module structure requirements
2. Define backward compatibility requirements
3. Define transactionality requirements
4. Define performance requirements
5. Define acceptance criteria per module
6. Define test requirements

**Key Questions:**
- What defines a module as "complete"?
- How do we verify transactionality is preserved?
- What's the performance tolerance?

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: SaveSession Decomposition Architecture

Work with the @architect agent to create TDD-SPRINT-4-SAVESESSION-DECOMPOSITION.

**Prerequisites:**
- PRD-SPRINT-4-SAVESESSION-DECOMPOSITION approved

**Goals:**
1. Design module interfaces
2. Design shared state protocol
3. Design composition pattern
4. Design error propagation
5. Document extraction order
6. Create ADR for decomposition strategy

**Required ADR:**
- ADR-0120: SaveSession Decomposition Strategy

**Design Questions:**
- How does facade compose modules?
- How do modules communicate?
- How is state shared safely?
- How are errors propagated?

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Foundation Modules

Work with the @principal-engineer agent to create core modules.

**Phase 1 Scope:**
1. Create session/ package directory
2. Create session/__init__.py
3. Extract SessionState to state.py
4. Extract state machine logic to state.py
5. Extract EntityTracker to tracking.py
6. Extract identity map logic
7. Extract dirty detection logic
8. Verify tests pass

**Extraction Order:**
1. state.py (no dependencies)
2. tracking.py (depends only on types)

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Operation Modules

Work with the @principal-engineer agent to extract operation modules.

**Phase 2 Scope:**
1. Extract OperationQueue to operations.py
2. Extract ActionHandler to actions.py
3. Extract SelfHealer to healing.py
4. Update SaveSession to use extracted modules
5. Verify tests pass

**Extraction Order:**
1. operations.py (depends on types)
2. actions.py (may depend on operations)
3. healing.py (depends on operations, actions)

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Commit and Facade

Work with the @principal-engineer agent to complete decomposition.

**Phase 3 Scope:**
1. Extract CommitOrchestrator to commit.py
2. Extract BatchBuilder to batch.py
3. Extract ResultBuilder to result.py
4. Create SaveSession facade in __init__.py
5. Delete original session.py
6. Verify all tests pass
7. Verify backward compatibility

**Final Structure:**
```
session/
    __init__.py      # SaveSession facade + re-exports
    state.py         # SessionState, StateMachine
    tracking.py      # EntityTracker
    operations.py    # OperationQueue
    actions.py       # ActionHandler
    healing.py       # SelfHealer
    commit.py        # CommitOrchestrator
    batch.py         # BatchBuilder
    result.py        # ResultBuilder
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: SaveSession Decomposition Validation

Work with the @qa-adversary agent to validate the decomposition.

**Goals:**

**Part 1: Backward Compatibility**
- All existing imports work
- SaveSession API unchanged
- Context manager works

**Part 2: Transactionality**
- Commit phases execute in order
- Rollback works correctly
- Error handling unchanged

**Part 3: Module Isolation**
- Each module can be tested independently
- No circular imports
- Clear dependency direction

**Part 4: Functional Correctness**
- All existing tests pass
- All edge cases preserved
- Self-healing works

**Part 5: Performance**
- Small batch commit: <5% regression
- Large batch commit: <5% regression
- Memory usage unchanged

**Part 6: Structural Verification**
- Each module <400 lines
- Single responsibility per module
- Clear module interfaces

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**SaveSession Structure:**
- [ ] `session.py` full content (2192 lines)
- [ ] All methods with line counts
- [ ] All instance variables
- [ ] State transitions

**Persistence Layer:**
- [ ] `pipeline.py` integration points
- [ ] `action_executor.py` integration
- [ ] `models.py` structures

**Dependencies:**
- [ ] Internal dependencies within session.py
- [ ] External module dependencies
- [ ] Callers of SaveSession

**Test Coverage:**
- [ ] test_session.py structure
- [ ] Integration test patterns
- [ ] Edge case coverage
- [ ] Performance benchmarks
