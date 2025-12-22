# SPIKE: SaveSession Decomposition Map

> **Author**: @architect
> **Date**: 2025-12-19
> **Status**: Analysis Complete
> **Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`
> **Lines Analyzed**: 2193 lines

---

## Executive Summary

SaveSession is a 2193-line god class implementing the Unit of Work pattern for batched Asana operations. Analysis reveals **14 distinct responsibility groups** with significant intertwining. The persistence layer has already extracted key concerns (tracker.py, pipeline.py, events.py, action_executor.py, graph.py, executor.py, cascade.py, healing.py), but session.py retains substantial logic that could be further decomposed.

**Key Finding**: Session.py mixes orchestration (its core job) with implementation details. The decomposition should preserve SaveSession as a facade while extracting implementation to specialized modules.

---

## Part 1: Method Inventory

### Complete Method Catalog (34 Methods)

| # | Method | Lines | Start | End | Responsibility Group |
|---|--------|-------|-------|-----|---------------------|
| 1 | `__init__` | 82 | 121 | 202 | Initialization |
| 2 | `__aenter__` | 3 | 205 | 207 | Context Management |
| 3 | `__aexit__` | 12 | 209 | 220 | Context Management |
| 4 | `__enter__` | 3 | 222 | 224 | Context Management |
| 5 | `__exit__` | 12 | 226 | 237 | Context Management |
| 6 | `name_resolver` (property) | 14 | 241 | 254 | Name Resolution |
| 7 | `track` | 85 | 258 | 340 | Entity Tracking |
| 8 | `_track_recursive` | 26 | 342 | 367 | Entity Tracking |
| 9 | `untrack` | 23 | 368 | 391 | Entity Tracking |
| 10 | `delete` | 34 | 393 | 426 | Entity Tracking |
| 11 | `get_changes` | 25 | 430 | 454 | Change Inspection |
| 12 | `get_state` | 24 | 456 | 479 | Change Inspection |
| 13 | `find_by_gid` | 21 | 481 | 501 | Entity Lookup |
| 14 | `is_tracked` | 17 | 503 | 520 | Entity Lookup |
| 15 | `get_dependency_order` | 25 | 522 | 547 | Dependency Analysis |
| 16 | `preview` | 43 | 551 | 590 | Preview/Dry Run |
| 17 | `commit_async` | 160 | 594 | 753 | Commit Orchestration |
| 18 | `commit` | 17 | 755 | 771 | Commit Orchestration |
| 19 | `_commit_sync` | 4 | 773 | 776 | Commit Orchestration |
| 20 | `on_pre_save` | 28 | 780 | 808 | Event Hooks |
| 21 | `on_post_save` | 28 | 810 | 837 | Event Hooks |
| 22 | `on_error` | 28 | 839 | 865 | Event Hooks |
| 23 | `on_post_commit` | 32 | 867 | 897 | Event Hooks |
| 24 | `add_tag` | 49 | 901 | 949 | Action Operations |
| 25 | `remove_tag` | 49 | 951 | 999 | Action Operations |
| 26 | `add_to_project` | 78 | 1001 | 1078 | Action Operations |
| 27 | `remove_from_project` | 51 | 1080 | 1129 | Action Operations |
| 28 | `add_dependency` | 52 | 1131 | 1182 | Action Operations |
| 29 | `remove_dependency` | 51 | 1184 | 1233 | Action Operations |
| 30 | `move_to_section` | 80 | 1235 | 1313 | Action Operations |
| 31 | `add_follower` | 49 | 1315 | 1363 | Action Operations |
| 32 | `remove_follower` | 49 | 1365 | 1413 | Action Operations |
| 33 | `add_followers` | 24 | 1415 | 1443 | Action Operations |
| 34 | `remove_followers` | 24 | 1445 | 1473 | Action Operations |
| 35 | `add_dependent` | 56 | 1477 | 1532 | Action Operations |
| 36 | `remove_dependent` | 55 | 1534 | 1587 | Action Operations |
| 37 | `add_like` | 39 | 1589 | 1627 | Action Operations |
| 38 | `remove_like` | 39 | 1629 | 1667 | Action Operations |
| 39 | `add_comment` | 73 | 1669 | 1741 | Action Operations |
| 40 | `set_parent` | 89 | 1747 | 1835 | Action Operations |
| 41 | `reorder_subtask` | 48 | 1837 | 1883 | Action Operations |
| 42 | `get_pending_actions` | 14 | 1885 | 1898 | Action Inspection |
| 43 | `cascade_field` | 64 | 1902 | 1962 | Cascade Operations |
| 44 | `get_pending_cascades` | 10 | 1964 | 1973 | Cascade Inspection |
| 45 | `_ensure_open` | 8 | 1977 | 1984 | State Guards |
| 46 | `_reset_custom_field_tracking` | 12 | 1986 | 1996 | Post-Commit Cleanup |
| 47 | `_clear_successful_actions` | 29 | 1998 | 2026 | Post-Commit Cleanup |
| 48 | `_should_heal` | 45 | 2030 | 2074 | Self-Healing |
| 49 | `_queue_healing` | 19 | 2076 | 2093 | Self-Healing |
| 50 | `_execute_healing_async` | 89 | 2104 | 2192 | Self-Healing |

**Total Unique Methods**: 50 (including properties)

---

## Part 2: Responsibility Groups

### Group Analysis (14 Categories)

| # | Responsibility | Methods | Lines | % of Total |
|---|----------------|---------|-------|------------|
| 1 | **Initialization** | 1 | 82 | 3.7% |
| 2 | **Context Management** | 4 | 30 | 1.4% |
| 3 | **Entity Tracking** | 4 | 168 | 7.7% |
| 4 | **Change Inspection** | 2 | 49 | 2.2% |
| 5 | **Entity Lookup** | 2 | 38 | 1.7% |
| 6 | **Dependency Analysis** | 1 | 25 | 1.1% |
| 7 | **Preview/Dry Run** | 1 | 43 | 2.0% |
| 8 | **Commit Orchestration** | 3 | 181 | 8.3% |
| 9 | **Event Hooks** | 4 | 116 | 5.3% |
| 10 | **Action Operations** | 18 | 920 | 42.0% |
| 11 | **Action/Cascade Inspection** | 2 | 24 | 1.1% |
| 12 | **Cascade Operations** | 1 | 64 | 2.9% |
| 13 | **Self-Healing** | 3 | 153 | 7.0% |
| 14 | **Internal Utilities** | 3 | 49 | 2.2% |
| | **Docstrings/Imports** | - | ~251 | 11.5% |

### Detailed Breakdown

#### 1. Initialization (82 lines)
```
__init__
```
- Initializes all dependencies (tracker, graph, events, pipeline)
- Configures executors (action, cascade)
- Sets up healing and automation state
- **Coupling**: High - touches all subsystems

#### 2. Context Management (30 lines)
```
__aenter__, __aexit__, __enter__, __exit__
```
- Manages session lifecycle
- Sets session state to CLOSED on exit
- **Coupling**: Low - only modifies `_state`

#### 3. Entity Tracking (168 lines)
```
track, _track_recursive, untrack, delete
```
- Delegates to ChangeTracker
- Handles recursive tracking for holders
- Manages healing flag per entity
- **Coupling**: Medium - interacts with tracker, healing queue

#### 4. Change Inspection (49 lines)
```
get_changes, get_state
```
- Pure delegation to ChangeTracker
- **Coupling**: Low - read-only delegation

#### 5. Entity Lookup (38 lines)
```
find_by_gid, is_tracked
```
- Pure delegation to ChangeTracker
- **Coupling**: Low - read-only delegation

#### 6. Dependency Analysis (25 lines)
```
get_dependency_order
```
- Delegates to DependencyGraph
- **Coupling**: Low - read-only

#### 7. Preview/Dry Run (43 lines)
```
preview
```
- Combines pipeline preview with pending actions
- **Coupling**: Medium - reads from tracker, pipeline, pending_actions

#### 8. Commit Orchestration (181 lines)
```
commit_async, commit, _commit_sync
```
- **Core complexity center**
- Orchestrates 5 phases: CRUD, Actions, Cascades, Healing, Automation
- Manages result aggregation
- Post-commit cleanup and hooks
- **Coupling**: Very High - touches ALL subsystems

#### 9. Event Hooks (116 lines)
```
on_pre_save, on_post_save, on_error, on_post_commit
```
- Decorator-style registration
- Delegates to EventSystem
- **Coupling**: Low - pure delegation

#### 10. Action Operations (920 lines - 42% of class!)
```
add_tag, remove_tag, add_to_project, remove_from_project,
add_dependency, remove_dependency, move_to_section,
add_follower, remove_follower, add_followers, remove_followers,
add_dependent, remove_dependent, add_like, remove_like,
add_comment, set_parent, reorder_subtask
```
- All follow same pattern: validate -> build ActionOperation -> append to queue
- High code duplication
- **Coupling**: Low - only appends to `_pending_actions`

#### 11. Action/Cascade Inspection (24 lines)
```
get_pending_actions, get_pending_cascades
```
- Returns copies of pending lists
- **Coupling**: None - read-only

#### 12. Cascade Operations (64 lines)
```
cascade_field
```
- Builds CascadeOperation and appends to queue
- **Coupling**: Low - only appends to `_cascade_operations`

#### 13. Self-Healing (153 lines)
```
_should_heal, _queue_healing, _execute_healing_async
```
- Healing eligibility logic
- Direct API calls for healing
- **Coupling**: High - accesses detection state, makes API calls

#### 14. Internal Utilities (49 lines)
```
_ensure_open, _reset_custom_field_tracking, _clear_successful_actions
```
- Session state guards
- Post-commit cleanup helpers
- **Coupling**: Low-Medium

---

## Part 3: Instance Variable Inventory

### All Instance Variables (19 Total)

| Variable | Type | Set In | Used In | Ownership Candidate |
|----------|------|--------|---------|---------------------|
| `_client` | AsanaClient | __init__ | commit, healing | Session (facade access) |
| `_batch_size` | int | __init__ | __init__ | Session |
| `_max_concurrent` | int | __init__ | unused | Session (remove?) |
| `_tracker` | ChangeTracker | __init__ | track, get_*, preview | Tracking Module |
| `_graph` | DependencyGraph | __init__ | preview, get_dependency_order | Session (via pipeline) |
| `_events` | EventSystem | __init__ | on_*, commit | Session (via pipeline) |
| `_pipeline` | SavePipeline | __init__ | preview, commit | Session |
| `_action_executor` | ActionExecutor | __init__ | commit | Session (via pipeline) |
| `_pending_actions` | list[ActionOperation] | __init__ | action methods, preview, commit | Actions Module |
| `_cascade_executor` | CascadeExecutor | __init__ | commit | Session |
| `_cascade_operations` | list[CascadeOperation] | __init__ | cascade_field, commit | Session |
| `_name_cache` | dict[str, str] | __init__ | name_resolver | Session |
| `_name_resolver` | NameResolver | __init__ | name_resolver property | Session |
| `_auto_heal` | bool | __init__ | _should_heal | Healing Module |
| `_entity_heal_flags` | dict[str, bool] | __init__ | track, _should_heal | Healing Module |
| `_healing_queue` | list[tuple] | __init__ | track, commit, healing methods | Healing Module |
| `_automation_enabled` | bool | __init__ | commit | Session |
| `_state` | SessionState | __init__, __exit__ | _ensure_open | State Module |
| `_log` | Logger | __init__ | throughout | Session (passed to modules) |

### Variable Groupings

**Core Session State**:
- `_client`, `_batch_size`, `_max_concurrent`, `_state`, `_log`
- `_automation_enabled`

**Delegated Components**:
- `_tracker`, `_graph`, `_events`, `_pipeline`
- `_action_executor`, `_cascade_executor`
- `_name_resolver`, `_name_cache`

**Pending Operations Queues**:
- `_pending_actions`
- `_cascade_operations`

**Healing State**:
- `_auto_heal`, `_entity_heal_flags`, `_healing_queue`

---

## Part 4: Dependency Graph (Responsibility-to-Responsibility)

```
                         ┌─────────────────┐
                         │  Initialization │
                         └────────┬────────┘
                                  │ creates
                                  ▼
    ┌───────────────────────────────────────────────────────┐
    │                    All Components                      │
    │  (tracker, graph, events, pipeline, executors, etc.)   │
    └───────────────────────────────────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
            ▼                     ▼                     ▼
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │Entity Tracking│     │Action Methods │     │Cascade Method│
    │   (track)     │     │  (add_tag)   │     │(cascade_field)│
    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
           │                    │                    │
           │ populates          │ populates          │ populates
           ▼                    ▼                    ▼
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │   Tracker    │     │pending_actions│     │cascade_ops   │
    │  (entities)  │     │   (queue)    │     │   (queue)    │
    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
           │                    │                    │
           │                    │                    │
           └─────────┬──────────┴──────────┬─────────┘
                     │                     │
                     ▼                     │
              ┌──────────────┐             │
              │    Preview   │◄────────────┘
              │  (read-only) │
              └──────────────┘
                     │
                     │ same data
                     ▼
              ┌──────────────────────────────────────────┐
              │              COMMIT                       │
              │  ┌────────────────────────────────────┐  │
              │  │ Phase 1: CRUD (via pipeline)       │  │
              │  └────────────────┬───────────────────┘  │
              │                   ▼                      │
              │  ┌────────────────────────────────────┐  │
              │  │ Phase 2: Actions (via executor)    │  │
              │  └────────────────┬───────────────────┘  │
              │                   ▼                      │
              │  ┌────────────────────────────────────┐  │
              │  │ Phase 3: Cascades (via executor)   │  │
              │  └────────────────┬───────────────────┘  │
              │                   ▼                      │
              │  ┌────────────────────────────────────┐  │
              │  │ Phase 4: Healing (inline)          │  │
              │  └────────────────┬───────────────────┘  │
              │                   ▼                      │
              │  ┌────────────────────────────────────┐  │
              │  │ Phase 5: Automation (via client)   │  │
              │  └────────────────────────────────────┘  │
              └──────────────────────────────────────────┘
                     │
                     ▼
              ┌──────────────┐
              │ Post-Commit  │
              │   Cleanup    │
              └──────────────┘
```

### Critical Path Dependencies

1. **Entity Tracking** must happen before **Preview** and **Commit**
2. **Action Methods** can be called in any order, only affect pending queue
3. **Commit** must execute phases in strict order
4. **Post-Commit Cleanup** depends on **Commit** results

---

## Part 5: Module Boundaries (Target Decomposition)

### Proposed Module Structure

Based on analysis, here are the recommended extraction modules with line estimates:

#### 5.1 state.py (~80 lines)
**Responsibility**: Session lifecycle and state machine

```python
# Contents:
class SessionState:     # Already in session.py, extract
    OPEN = "open"
    COMMITTED = "committed"
    CLOSED = "closed"

class SessionLifecycle:
    """Manages session state transitions."""
    _state: SessionState

    def ensure_open(self) -> None
    def transition_to_committed(self) -> None
    def transition_to_closed(self) -> None

    @contextmanager
    def sync_context(self) -> ...

    @asynccontextmanager
    def async_context(self) -> ...
```

**Extracts From session.py**:
- `SessionState` class (lines 50-61)
- `_ensure_open()` method (lines 1977-1984)
- `__aenter__`, `__aexit__`, `__enter__`, `__exit__` logic

#### 5.2 actions.py (~450 lines)
**Responsibility**: Action operation builders

```python
# Contents:
class ActionBuilder:
    """Fluent interface for building action operations."""
    _pending: list[ActionOperation]
    _log: Logger | None

    def add_tag(task, tag) -> Self
    def remove_tag(task, tag) -> Self
    def add_to_project(task, project, ...) -> Self
    def remove_from_project(task, project) -> Self
    def add_dependency(task, depends_on) -> Self
    def remove_dependency(task, depends_on) -> Self
    def move_to_section(task, section, ...) -> Self
    def add_follower(task, user) -> Self
    def remove_follower(task, user) -> Self
    def add_followers(task, users) -> Self
    def remove_followers(task, users) -> Self
    def add_dependent(task, dependent) -> Self
    def remove_dependent(task, dependent) -> Self
    def add_like(task) -> Self
    def remove_like(task) -> Self
    def add_comment(task, text, ...) -> Self
    def set_parent(task, parent, ...) -> Self
    def reorder_subtask(task, ...) -> Self

    def get_pending() -> list[ActionOperation]
    def clear_successful(results) -> None
```

**Extracts From session.py**:
- All action methods (lines 901-1898) - 18 methods, ~920 lines
- `_clear_successful_actions()` (lines 1998-2026)

**Pattern Opportunity**: All action methods follow identical pattern:
1. `self._ensure_open()`
2. Build `NameGid` from target
3. Validate GID
4. Create `ActionOperation`
5. Append to `_pending_actions`
6. Log if enabled
7. Return `self`

Could reduce to ~200 lines with generic builder + dispatch table.

#### 5.3 healing.py (EXISTS - Enhance to ~250 lines)
**Responsibility**: Self-healing execution

The standalone `healing.py` already exists but session.py duplicates logic. Consolidate:

```python
# Enhance existing healing.py with:
class HealingManager:
    """Manages healing queue and execution for SaveSession."""
    _auto_heal: bool
    _entity_flags: dict[str, bool]
    _queue: list[tuple[AsanaResource, str]]

    def should_heal(entity, override) -> bool      # From _should_heal
    def queue_if_needed(entity, override) -> None  # From _queue_healing + track logic
    async def execute_async(client, log) -> HealingReport  # From _execute_healing_async
```

**Extracts From session.py**:
- `_should_heal()` (lines 2030-2074)
- `_queue_healing()` (lines 2076-2093)
- `_execute_healing_async()` (lines 2104-2192)
- Healing-related instance variables

#### 5.4 commit.py (~300 lines)
**Responsibility**: Commit orchestration

```python
# Contents:
class CommitOrchestrator:
    """Orchestrates 5-phase commit execution."""

    async def execute_async(
        tracker: ChangeTracker,
        pipeline: SavePipeline,
        action_executor: ActionExecutor,
        pending_actions: list[ActionOperation],
        cascade_executor: CascadeExecutor,
        pending_cascades: list[CascadeOperation],
        healing_manager: HealingManager,
        automation_client: AutomationClient | None,
        events: EventSystem,
        log: Logger | None,
    ) -> SaveResult:
        """
        Phase 1: CRUD operations (pipeline.execute_with_actions)
        Phase 2: Cascade operations (cascade_executor.execute)
        Phase 3: Healing operations (healing_manager.execute_async)
        Phase 4: Automation (automation_client.evaluate_async)
        Phase 5: Post-commit hooks (events.emit_post_commit)
        """
```

**Extracts From session.py**:
- Core logic of `commit_async()` (lines 594-753)
- Result aggregation logic
- Phase coordination

#### 5.5 tracking.py (EXISTS as tracker.py - No Changes Needed)
**Status**: Already extracted. Session.py correctly delegates to ChangeTracker.

#### 5.6 result.py (EXISTS as models.py - No Changes Needed)
**Status**: SaveResult, ActionResult, HealingReport already in models.py.

---

## Part 6: Extraction Order (Least Dependent First)

### Recommended Extraction Sequence

```
Phase 1: Low-Risk Extractions (No Behavioral Change)
├── 1.1 state.py       - Extract SessionState + lifecycle methods
│                        Zero risk, pure state machine
│
└── 1.2 actions.py     - Extract all action builder methods
                         High line count, low coupling

Phase 2: Healing Consolidation
└── 2.1 healing.py     - Consolidate session healing into existing module
                         Some risk: healing logic tightly coupled to track()

Phase 3: Commit Refactor (Highest Risk)
└── 3.1 commit.py      - Extract commit orchestration
                         High risk: touches all subsystems
                         Requires careful interface design
```

### Extraction Risk Analysis

| Module | Risk Level | Reason | Mitigation |
|--------|------------|--------|------------|
| state.py | **Low** | Pure state machine, no side effects | Unit test state transitions |
| actions.py | **Low** | All methods follow same pattern, no shared state | Integration tests for each action |
| healing.py | **Medium** | Coupled to track() and detection | Feature flag for old vs new path |
| commit.py | **High** | Central orchestration point | Extensive integration testing, phased rollout |

---

## Part 7: Circular Dependency Risks

### Identified Risks

#### Risk 1: actions.py <-> session.py
**Symptom**: ActionBuilder needs to call `_ensure_open()` from session
**Mitigation**: Pass lifecycle check as callback or inject state checker

```python
# Option A: Callback injection
class ActionBuilder:
    def __init__(self, ensure_open: Callable[[], None]):
        self._ensure_open = ensure_open

# Option B: Protocol injection
class StateChecker(Protocol):
    def ensure_open(self) -> None: ...

class ActionBuilder:
    def __init__(self, state: StateChecker): ...
```

#### Risk 2: healing.py <-> session.py
**Symptom**: HealingManager needs access to `_client` for API calls
**Mitigation**: Pass client at execution time, not construction

```python
class HealingManager:
    async def execute_async(self, client: AsanaClient) -> HealingReport:
        # Client passed in, not stored
```

#### Risk 3: commit.py <-> all modules
**Symptom**: CommitOrchestrator needs many dependencies
**Mitigation**: Dependency injection via dataclass or named parameters

```python
@dataclass
class CommitContext:
    tracker: ChangeTracker
    pipeline: SavePipeline
    action_executor: ActionExecutor
    cascade_executor: CascadeExecutor
    healing_manager: HealingManager
    events: EventSystem
    client: AsanaClient
    log: Logger | None

class CommitOrchestrator:
    async def execute(self, ctx: CommitContext) -> SaveResult: ...
```

### Import Dependency Graph (Post-Extraction)

```
session.py
    ├── state.py (no back-import)
    ├── actions.py (no back-import)
    ├── healing.py (no back-import)
    ├── commit.py (no back-import)
    ├── tracker.py (existing, no changes)
    ├── pipeline.py (existing, no changes)
    └── events.py (existing, no changes)
```

**Rule**: Extracted modules MUST NOT import from session.py. All dependencies flow downward.

---

## Part 8: Shared State Protocol

### State Access Patterns

#### Pattern 1: Immutable Configuration (Pass at Construction)
```python
# For: _batch_size, _auto_heal, _automation_enabled
class ActionBuilder:
    def __init__(self, log: Logger | None = None):
        self._log = log  # Immutable after construction
```

#### Pattern 2: Mutable Queues (Owned by Module)
```python
# For: _pending_actions, _cascade_operations, _healing_queue
class ActionBuilder:
    def __init__(self):
        self._pending: list[ActionOperation] = []

    def get_pending(self) -> list[ActionOperation]:
        return list(self._pending)  # Return copy

    def drain(self) -> list[ActionOperation]:
        pending = self._pending
        self._pending = []
        return pending
```

#### Pattern 3: External Dependencies (Pass at Execution)
```python
# For: _client, _tracker, _pipeline
class CommitOrchestrator:
    async def execute(
        self,
        tracker: ChangeTracker,  # Passed, not stored
        pipeline: SavePipeline,
        ...
    ) -> SaveResult:
```

#### Pattern 4: Callback Injection (For State Checks)
```python
# For: _ensure_open checks
class ActionBuilder:
    def __init__(self, state_guard: Callable[[], None]):
        self._guard = state_guard

    def add_tag(self, task, tag):
        self._guard()  # Checks session state via callback
        ...
```

### Session as Facade (Final Structure)

```python
class SaveSession:
    """Facade coordinating extracted modules."""

    def __init__(self, client: AsanaClient, ...):
        # Core state (not extracted)
        self._client = client
        self._state = SessionState.OPEN
        self._log = ...

        # Existing extracted modules
        self._tracker = ChangeTracker()
        self._graph = DependencyGraph()
        self._events = EventSystem()
        self._pipeline = SavePipeline(...)
        self._action_executor = ActionExecutor(...)
        self._cascade_executor = CascadeExecutor(...)

        # NEW extracted modules
        self._actions = ActionBuilder(state_guard=self._ensure_open)
        self._healing = HealingManager(auto_heal=auto_heal)

    # Delegation to actions module
    def add_tag(self, task, tag) -> Self:
        self._actions.add_tag(task, tag)
        return self

    # Delegation to commit module
    async def commit_async(self) -> SaveResult:
        return await CommitOrchestrator.execute(
            CommitContext(
                tracker=self._tracker,
                pipeline=self._pipeline,
                pending_actions=self._actions.drain(),
                ...
            )
        )
```

---

## Appendix A: Line Count Summary

### Current State (session.py)
| Section | Lines |
|---------|-------|
| Imports/Docstring | 47 |
| SessionState | 12 |
| SaveSession Class | 2134 |
| **Total** | **2193** |

### Post-Extraction Estimate
| Module | Lines | Source |
|--------|-------|--------|
| state.py | ~80 | New extraction |
| actions.py | ~200-450 | New extraction (with/without refactor) |
| healing.py | ~250 | Existing + consolidation |
| commit.py | ~300 | New extraction |
| **session.py (facade)** | **~300-400** | Remaining facade |

**Reduction**: 2193 -> ~400 lines (82% reduction in session.py)

---

## Appendix B: Already Extracted Modules

These modules already exist and perform well. No changes recommended:

| Module | Lines | Responsibility |
|--------|-------|----------------|
| tracker.py | 377 | Change tracking via snapshots |
| pipeline.py | 594 | 4-phase save orchestration |
| events.py | 282 | Hook registration and emission |
| action_executor.py | 203 | Action API execution |
| executor.py | 190 | Batch execution |
| graph.py | 245 | Dependency graph + Kahn's algorithm |
| cascade.py | 285 | Cascade field propagation |
| models.py | 754 | Data models (EntityState, SaveResult, etc.) |
| exceptions.py | 360 | Exception hierarchy |
| validation.py | 64 | GID validation |
| healing.py | 226 | Standalone healing utilities |

---

## Appendix C: Decision Factors

### Why Extract actions.py?
1. **42% of class** - Single largest responsibility group
2. **High code duplication** - All 18 methods follow identical pattern
3. **Low coupling** - Only appends to a queue, no shared state mutations
4. **Easy to test** - Pure data structure building

### Why Extract commit.py?
1. **Core complexity** - 181 lines of orchestration logic
2. **5 distinct phases** - Each phase is conceptually separate
3. **Result aggregation** - Complex logic that could be unit tested
4. **Clear interface** - Takes inputs, produces SaveResult

### Why Consolidate healing.py?
1. **Duplicate logic** - session.py has inline healing, standalone healing.py exists
2. **Self-contained** - Healing is conceptually independent
3. **Testability** - Healing logic can be unit tested in isolation

### Why NOT Extract tracking.py?
1. **Already exists** - ChangeTracker is already a separate module
2. **Clean delegation** - session.py correctly delegates
3. **Stable interface** - No changes needed

---

## Next Steps

1. **Review with stakeholder** - Validate extraction priorities
2. **Write tests first** - Ensure coverage before refactoring
3. **Extract state.py** - Lowest risk starting point
4. **Extract actions.py** - Highest impact with pattern refactoring
5. **Consolidate healing.py** - Medium risk, good payoff
6. **Extract commit.py** - Last due to highest risk

---

*Generated by @architect spike session*
