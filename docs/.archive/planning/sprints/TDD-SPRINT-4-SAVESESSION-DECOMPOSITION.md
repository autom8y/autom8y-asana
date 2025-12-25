# TDD: Sprint 4 - SaveSession Decomposition

## Metadata
- **TDD ID**: TDD-SPRINT-4-SAVESESSION-DECOMPOSITION
- **Status**: Completed
- **Author**: Architect (Claude)
- **Created**: 2025-12-19
- **Last Updated**: 2025-12-25
- **Completed**: 2025-12-22
- **PRD Reference**: [PRD-SPRINT-4-SAVESESSION-DECOMPOSITION](/docs/planning/sprints/PRD-SPRINT-4-SAVESESSION-DECOMPOSITION.md)
- **Related TDDs**: TDD-0010, TDD-0011, TDD-SPRINT-3-DETECTION-DECOMPOSITION
- **Related ADRs**: [ADR-0121](/docs/decisions/ADR-0121-savesession-decomposition-strategy.md), [ADR-0122](/docs/decisions/ADR-0122-action-method-factory-pattern.md), ADR-0066, ADR-0074

## Overview

This TDD defines the technical approach for reducing SaveSession from 2193 lines to ~400 lines (82% reduction) through targeted extraction of four components: Action Method Factory, State Manager, Healing Manager, and Commit Orchestrator. The decomposition is an **in-place refactoring** that preserves all public API signatures while consolidating boilerplate into reusable infrastructure. The highest-value target is the 18 action methods (920 lines), which will be replaced by a descriptor-based ActionBuilder pattern generating methods from configuration.

## Requirements Summary

Per PRD-SPRINT-4-SAVESESSION-DECOMPOSITION:

| ID | Requirement | Design Response |
|----|-------------|-----------------|
| FR-ACTION-001 | Create ActionBuilder to consolidate 18 methods | Section 4.1 - Descriptor pattern |
| FR-ACTION-002 | Support three action variants | Section 4.1.2 - ActionVariant enum |
| FR-ACTION-003 | Preserve exact public signatures | Section 4.1.3 - Signature preservation |
| FR-STATE-001 | Extract SessionState enum | Section 4.2 - Keep in session.py |
| FR-STATE-004 | Add `state` property | Section 4.2 - Public inspection |
| FR-HEAL-001 | Extract healing logic | Section 4.3 - Merge with healing.py |
| FR-COMMIT-001 | Extract five-phase commit | Section 4.4 - Optional extraction |
| FR-INSP-001 through FR-INSP-005 | Add inspection properties | Section 4.5 - Properties for test access |

| ID | NFR | Validation |
|----|-----|------------|
| NFR-COMPAT-001 | 0 public API changes | Signature comparison |
| NFR-PERF-001 | <5% latency regression | Benchmark: 100 entities + 50 actions |
| NFR-TEST-001 | All existing tests pass | `pytest tests/unit/persistence/test_session*.py` |
| NFR-MAINT-001 | Each module <200 lines | `wc -l` per module |

## System Context

```
+---------------------------------------------+
|        autom8_asana SDK                     |
|  +---------------------------------------+  |
|  |     persistence/                       |  |
|  |  +----------+  +---------+  +-------+  |  |
|  |  | tracker  |  |pipeline |  |events |  |  |
|  |  +----+-----+  +----+----+  +---+---+  |  |
|  |       |             |           |      |  |
|  |       +------+------+------+----+      |  |
|  |              |             |           |  |
|  |              v             v           |  |
|  |  +------------------------------------+ |  |
|  |  |         session.py                  | |  |  <-- Decomposition Target
|  |  |  +----------+ +----------+          | |  |
|  |  |  |  State   | |  Healing |          | |  |
|  |  |  | Manager  | | Manager  |          | |  |
|  |  |  +----------+ +----------+          | |  |
|  |  |  +---------------------------+      | |  |
|  |  |  |    ActionBuilder          |      | |  |
|  |  |  | (descriptor + registry)   |      | |  |
|  |  |  +---------------------------+      | |  |
|  |  +------------------------------------+ |  |
|  |              |                          |  |
|  |              v                          |  |
|  |  +----------+  +---------------+        |  |
|  |  |action_   |  | healing.py    |        |  |
|  |  |executor  |  | (standalone)  |        |  |
|  |  +----------+  +---------------+        |  |
|  +---------------------------------------+  |
+---------------------------------------------+
```

SaveSession is imported by:
- `client.py` - Factory method `save_session()`
- `automation/engine.py` - Automation rule execution
- `automation/pipeline.py` - Pipeline automation
- `tests/**` - All test files

SaveSession imports from:
- `tracker.py` - ChangeTracker for entity tracking
- `graph.py` - DependencyGraph for ordering
- `pipeline.py` - SavePipeline for CRUD execution
- `events.py` - EventSystem for hooks
- `action_executor.py` - ActionExecutor for action operations
- `cascade.py` - CascadeExecutor for field propagation
- `healing.py` - Standalone healing utilities (potential merge target)

## Design

### Architecture Decision: In-Place Refactoring

Per ADR-0121, we chose **in-place refactoring** over package extraction:

- Action methods remain as methods on SaveSession (not moved to submodule)
- ActionBuilder generates method bodies, not method objects
- Healing logic merges into existing `healing.py` module
- State management stays in session.py with cleaner organization

This approach minimizes disruption while achieving the line reduction target.

### Component Architecture

| Component | Current Lines | Target Lines | Approach | Location |
|-----------|---------------|--------------|----------|----------|
| ActionBuilder | 920 | ~150 | Descriptor + registry | `persistence/actions.py` (new) |
| State Manager | ~100 | ~50 | Inline cleanup | `session.py` (existing) |
| Healing Manager | ~165 | ~50 | Merge to healing.py | `persistence/healing.py` (existing) |
| Commit Orchestrator | ~160 | ~60 | Optional extraction | `session.py` or `persistence/commit.py` |
| Inspection APIs | N/A | ~20 | Properties | `session.py` (existing) |

### 4.1 Action Method Factory (ActionBuilder)

Per ADR-0122, we use a **descriptor-based factory pattern** to consolidate the 18 action methods.

#### 4.1.1 Module: persistence/actions.py

**Purpose**: Define action method infrastructure and generate methods from configuration.

**Estimated Lines**: ~150

**Exports**:
```python
__all__ = [
    "ActionBuilder",
    "ActionVariant",
    "ActionConfig",
    "action_method",  # Decorator for custom validation
]
```

#### 4.1.2 ActionVariant Enum

```python
class ActionVariant(Enum):
    """Categories of action method behavior.

    Per FR-ACTION-002: Three variants with distinct behaviors.
    """
    NO_TARGET = "no_target"           # add_like, remove_like
    TARGET_REQUIRED = "target_req"    # add_tag, add_dependency, etc.
    POSITIONING = "positioning"        # add_to_project, move_to_section, set_parent
```

#### 4.1.3 ActionConfig Dataclass

```python
@dataclass(frozen=True)
class ActionConfig:
    """Configuration for a single action method.

    Defines everything needed to generate the method body.
    """
    action_type: ActionType           # Enum value for ActionOperation
    variant: ActionVariant            # Behavioral category
    target_param: str | None = None   # Parameter name ("tag", "project", etc.)
    target_type_hint: str = "AsanaResource | str"  # Type annotation
    requires_validation: bool = True   # Whether to call validate_gid()
    log_event: str | None = None      # Structured log event name
    docstring: str = ""               # Method docstring
```

#### 4.1.4 Action Registry

```python
# Registry of all action configurations
ACTION_REGISTRY: dict[str, ActionConfig] = {
    "add_tag": ActionConfig(
        action_type=ActionType.ADD_TAG,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="tag",
        target_type_hint="AsanaResource | str",
        log_event="session_add_tag",
        docstring="Add a tag to a task...",
    ),
    "remove_tag": ActionConfig(
        action_type=ActionType.REMOVE_TAG,
        variant=ActionVariant.TARGET_REQUIRED,
        target_param="tag",
        target_type_hint="AsanaResource | str",
        log_event="session_remove_tag",
        docstring="Remove a tag from a task...",
    ),
    # ... remaining 16 configurations
}
```

#### 4.1.5 ActionBuilder Descriptor

```python
class ActionBuilder:
    """Descriptor that generates action method implementations.

    Per ADR-0122: Uses Python descriptor protocol to generate
    method bodies at class definition time, not at call time.

    Usage in SaveSession:
        add_tag = ActionBuilder("add_tag")
        remove_tag = ActionBuilder("remove_tag")
        # ... generates 18 methods from ~20 lines of declarations
    """

    def __init__(self, action_name: str) -> None:
        self._action_name = action_name
        self._config = ACTION_REGISTRY[action_name]

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when descriptor is assigned to class attribute."""
        self._attr_name = name

    def __get__(self, obj: SaveSession | None, objtype: type | None = None):
        """Return bound method that implements the action."""
        if obj is None:
            return self
        return self._make_method(obj)

    def _make_method(self, session: SaveSession) -> Callable[..., SaveSession]:
        """Generate the action method for this configuration."""
        config = self._config

        if config.variant == ActionVariant.NO_TARGET:
            return self._make_no_target_method(session, config)
        elif config.variant == ActionVariant.TARGET_REQUIRED:
            return self._make_target_method(session, config)
        else:  # POSITIONING
            return self._make_positioning_method(session, config)
```

#### 4.1.6 Method Templates

The ActionBuilder implements three templates:

**No-Target Template** (add_like, remove_like):
```python
def _make_no_target_method(self, session: SaveSession, config: ActionConfig):
    def method(task: AsanaResource) -> SaveSession:
        session._ensure_open()
        action = ActionOperation(
            task=task,
            action=config.action_type,
            target=None,
        )
        session._pending_actions.append(action)
        if session._log:
            session._log.debug(config.log_event, task_gid=task.gid)
        return session
    method.__doc__ = config.docstring
    return method
```

**Target-Required Template** (add_tag, add_dependency, etc.):
```python
def _make_target_method(self, session: SaveSession, config: ActionConfig):
    def method(task: AsanaResource, target: AsanaResource | str) -> SaveSession:
        session._ensure_open()
        # Build NameGid per ADR-0107
        if isinstance(target, str):
            target_gid = NameGid(gid=target)
        else:
            target_gid = NameGid(gid=target.gid, name=getattr(target, "name", None))
        # Validation
        if config.requires_validation:
            validate_gid(target_gid.gid, f"{config.target_param}_gid")
        # Create operation
        action = ActionOperation(
            task=task,
            action=config.action_type,
            target=target_gid,
        )
        session._pending_actions.append(action)
        if session._log:
            session._log.debug(config.log_event, task_gid=task.gid, target_gid=target_gid.gid)
        return session
    method.__doc__ = config.docstring
    return method
```

**Positioning Template** (add_to_project, move_to_section, set_parent):
```python
def _make_positioning_method(self, session: SaveSession, config: ActionConfig):
    def method(
        task: AsanaResource,
        target: AsanaResource | str,
        *,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> SaveSession:
        session._ensure_open()
        # Per ADR-0047: Fail-fast validation
        if insert_before is not None and insert_after is not None:
            raise PositioningConflictError(insert_before, insert_after)
        # Build NameGid
        if isinstance(target, str):
            target_gid = NameGid(gid=target)
        else:
            target_gid = NameGid(gid=target.gid, name=getattr(target, "name", None))
        if config.requires_validation:
            validate_gid(target_gid.gid, f"{config.target_param}_gid")
        # Build extra_params
        extra_params: dict[str, str] = {}
        if insert_before is not None:
            extra_params["insert_before"] = insert_before
        if insert_after is not None:
            extra_params["insert_after"] = insert_after
        # Create operation
        action = ActionOperation(
            task=task,
            action=config.action_type,
            target=target_gid,
            extra_params=extra_params,
        )
        session._pending_actions.append(action)
        if session._log:
            session._log.debug(
                config.log_event,
                task_gid=task.gid,
                target_gid=target_gid.gid,
                insert_before=insert_before,
                insert_after=insert_after,
            )
        return session
    method.__doc__ = config.docstring
    return method
```

#### 4.1.7 SaveSession Integration

After ActionBuilder is implemented, SaveSession action methods become:

```python
class SaveSession:
    # ... existing code ...

    # Action methods via ActionBuilder (replaces 920 lines with ~20 lines)
    add_tag = ActionBuilder("add_tag")
    remove_tag = ActionBuilder("remove_tag")
    add_to_project = ActionBuilder("add_to_project")
    remove_from_project = ActionBuilder("remove_from_project")
    add_dependency = ActionBuilder("add_dependency")
    remove_dependency = ActionBuilder("remove_dependency")
    move_to_section = ActionBuilder("move_to_section")
    add_follower = ActionBuilder("add_follower")
    remove_follower = ActionBuilder("remove_follower")
    add_dependent = ActionBuilder("add_dependent")
    remove_dependent = ActionBuilder("remove_dependent")
    add_like = ActionBuilder("add_like")
    remove_like = ActionBuilder("remove_like")

    # Special cases with custom logic (kept as explicit methods)
    def add_comment(self, task: AsanaResource, text: str, *, html_text: str | None = None) -> SaveSession:
        """Add a comment to a task. Requires non-empty text validation."""
        # Custom validation: text or html_text must be non-empty
        ...

    def set_parent(self, task: AsanaResource, parent: AsanaResource | str | None, ...) -> SaveSession:
        """Set parent with None handling for promotion."""
        # Custom logic: parent=None means promote to top-level
        ...

    def reorder_subtask(self, task: AsanaResource, ...) -> SaveSession:
        """Reorder subtask. Requires parent validation."""
        # Custom validation: task must have parent
        ...

    # Batch methods (kept as explicit, delegate to individual methods)
    def add_followers(self, task: AsanaResource, users: list[...]) -> SaveSession:
        for user in users:
            self.add_follower(task, user)
        return self

    def remove_followers(self, task: AsanaResource, users: list[...]) -> SaveSession:
        for user in users:
            self.remove_follower(task, user)
        return self
```

#### 4.1.8 Signature Preservation

Per FR-ACTION-003, all generated methods preserve exact signatures:

| Method | Original Signature | Generated Signature | Match |
|--------|-------------------|---------------------|-------|
| `add_tag` | `(task, tag) -> SaveSession` | `(task, tag) -> SaveSession` | YES |
| `add_to_project` | `(task, project, *, insert_before=None, insert_after=None) -> SaveSession` | `(task, target, *, insert_before=None, insert_after=None) -> SaveSession` | YES* |
| `add_like` | `(task) -> SaveSession` | `(task) -> SaveSession` | YES |

*Note: Parameter name `target` is internal; external callers use positional.

### 4.2 State Manager

Per FR-STATE-001 through FR-STATE-005, state management is cleaned up but kept in session.py.

#### 4.2.1 SessionState (Unchanged)

The `SessionState` class remains as-is at the top of session.py:

```python
class SessionState:
    """Internal state machine for SaveSession."""
    OPEN = "open"
    COMMITTED = "committed"
    CLOSED = "closed"
```

**Decision**: Keep as class constants rather than Enum per existing pattern. Moving to models.py adds no value and would require updating imports across tests.

#### 4.2.2 Inspection Properties (New)

Add properties for test access per FR-INSP-001 through FR-INSP-005:

```python
@property
def state(self) -> str:
    """Current session state for inspection (FR-INSP-001).

    Returns:
        One of SessionState.OPEN, COMMITTED, or CLOSED.
    """
    return self._state

@property
def auto_heal(self) -> bool:
    """Whether auto-healing is enabled (FR-INSP-002).

    Returns:
        True if auto_heal was passed as True to __init__.
    """
    return self._auto_heal

@property
def automation_enabled(self) -> bool:
    """Whether automation is enabled for this session (FR-INSP-003).

    Returns:
        True if automation will run during commit.
    """
    return self._automation_enabled

@property
def pending_healing_count(self) -> int:
    """Number of entities queued for healing (FR-INSP-004).

    Returns:
        Length of the healing queue.
    """
    return len(self._healing_queue)

@property
def healing_queue(self) -> list[tuple[AsanaResource, str]]:
    """Copy of the healing queue for inspection (FR-INSP-004).

    Returns:
        List of (entity, expected_project_gid) tuples.
    """
    return list(self._healing_queue)
```

### 4.3 Healing Manager

Per FR-HEAL-001, healing logic is extracted and merged with existing `persistence/healing.py`.

#### 4.3.1 Current State

- `persistence/healing.py` (~80 lines): Standalone utilities `heal_entity_async()`, `heal_entities_async()`
- `session.py` (~165 lines): `_should_heal()`, `_queue_healing()`, `_execute_healing_async()`

#### 4.3.2 Target State

Merge session healing into `healing.py`:

```python
# persistence/healing.py (expanded from ~80 to ~200 lines)

class HealingManager:
    """Manages entity healing operations.

    Per TDD-DETECTION/ADR-0095: Self-healing adds missing project memberships.
    """

    def __init__(self, client: AsanaClient, log: Any = None) -> None:
        self._client = client
        self._log = log
        self._queue: list[tuple[AsanaResource, str]] = []
        self._entity_flags: dict[str, bool] = {}

    def should_heal(
        self,
        entity: AsanaResource,
        auto_heal: bool,
        heal_override: bool | None,
    ) -> bool:
        """Determine if entity should be healed (FR-HEAL-002).

        Per TDD-DETECTION/ADR-0095: Healing triggered when:
        1. Session auto_heal=True OR heal_override=True
        2. Entity has _detection_result
        3. detection_result.tier_used > 1
        4. detection_result.expected_project_gid is not None
        5. Per-entity heal=False not specified
        """
        ...

    def queue(self, entity: AsanaResource, project_gid: str) -> None:
        """Queue entity for healing (FR-HEAL-003).

        Deduplicates by entity GID.
        """
        ...

    async def execute_async(self) -> HealingReport:
        """Execute all queued healing operations (FR-HEAL-004).

        Non-blocking: failures are logged but don't raise.
        Queue is cleared after execution (FR-HEAL-005).
        """
        ...

    @property
    def pending_count(self) -> int:
        """Number of entities pending healing."""
        return len(self._queue)

    @property
    def queue_snapshot(self) -> list[tuple[AsanaResource, str]]:
        """Copy of the queue for inspection."""
        return list(self._queue)


# Keep standalone utilities for ad-hoc usage
async def heal_entity_async(client: AsanaClient, entity: AsanaResource, project_gid: str) -> HealingResult:
    """Standalone healing for single entity."""
    ...

async def heal_entities_async(client: AsanaClient, entities: list[tuple[AsanaResource, str]]) -> HealingReport:
    """Standalone healing for multiple entities."""
    ...
```

#### 4.3.3 SaveSession Integration

SaveSession uses HealingManager:

```python
class SaveSession:
    def __init__(self, ...):
        ...
        # Replace manual healing management with HealingManager
        self._healing_manager = HealingManager(client, self._log)
        self._auto_heal = auto_heal

    def track(self, entity: T, *, heal: bool | None = None, ...) -> T:
        ...
        # Delegate healing decision
        if self._healing_manager.should_heal(entity, self._auto_heal, heal):
            detection = getattr(entity, "_detection_result", None)
            if detection and detection.expected_project_gid:
                self._healing_manager.queue(entity, detection.expected_project_gid)
        ...

    async def commit_async(self) -> SaveResult:
        ...
        # Phase 4: Healing
        healing_report: HealingReport | None = None
        if self._healing_manager.pending_count > 0:
            healing_report = await self._healing_manager.execute_async()
        ...

    @property
    def pending_healing_count(self) -> int:
        return self._healing_manager.pending_count

    @property
    def healing_queue(self) -> list[tuple[AsanaResource, str]]:
        return self._healing_manager.queue_snapshot
```

### 4.4 Commit Orchestrator (Optional)

Per FR-COMMIT-001 through FR-COMMIT-008, commit orchestration is the lowest-priority extraction.

#### 4.4.1 Analysis

Current `commit_async()` is ~160 lines covering:
1. Dirty entity collection
2. CRUD + Action execution (Phase 1-2)
3. Cascade execution (Phase 3)
4. Healing execution (Phase 4)
5. Automation execution (Phase 5)
6. Custom field reset
7. Post-commit hooks
8. Logging

After ActionBuilder and HealingManager extraction, `commit_async()` will be ~100 lines.

#### 4.4.2 Decision: Defer

Per PRD Phase 5 (Optional): Only extract if >100 lines remain after other extractions. Expected remaining lines: ~100. **Extraction deferred** - cleanup inline instead.

#### 4.4.3 Inline Cleanup

Simplify commit_async with private helper methods:

```python
async def commit_async(self) -> SaveResult:
    self._ensure_open()

    # Gather pending work
    pending = self._gather_pending_work()
    if not pending.has_work:
        return self._handle_empty_commit()

    # Execute phases
    crud_result, action_results = await self._execute_crud_and_actions(pending)
    cascade_results = await self._execute_cascades(pending)
    healing_report = await self._execute_healing()
    automation_results = await self._execute_automation(crud_result)

    # Post-commit processing
    self._reset_successful_entities(crud_result)
    await self._events.emit_post_commit(crud_result)

    # Build and return result
    return self._build_save_result(
        crud_result, action_results, cascade_results,
        healing_report, automation_results
    )
```

### 4.5 Inspection APIs

Per FR-INSP-001 through FR-INSP-005, add properties to SaveSession:

| Property | Type | Returns | Test Usage |
|----------|------|---------|------------|
| `state` | `str` | `SessionState.OPEN/COMMITTED/CLOSED` | Replace `session._state` |
| `auto_heal` | `bool` | Config value | Replace `session._auto_heal` |
| `automation_enabled` | `bool` | Config value | Replace access to `_automation_enabled` |
| `pending_healing_count` | `int` | Queue length | Replace `len(session._healing_queue)` |
| `healing_queue` | `list[tuple[...]]` | Queue copy | Replace `session._healing_queue` |

### Dependency Graph

```
Layer 0 (existing modules):
  - models.py: ActionType, ActionOperation, ActionResult (unchanged)
  - validation.py: validate_gid (unchanged)
  - exceptions.py: SessionClosedError, PositioningConflictError (unchanged)

Layer 1 (new/modified):
  - actions.py (NEW): ActionBuilder, ActionConfig, ACTION_REGISTRY
    - Imports: models.ActionType, models.ActionOperation, validation.validate_gid

  - healing.py (EXPANDED): HealingManager
    - Imports: models.HealingResult, models.HealingReport
    - Imports: TYPE_CHECKING: AsanaClient, AsanaResource

Layer 2 (modified):
  - session.py (REDUCED): SaveSession
    - Imports: actions.ActionBuilder
    - Imports: healing.HealingManager
    - Uses ActionBuilder as class-level descriptors
    - Instantiates HealingManager in __init__
```

**No circular imports**: actions.py and healing.py don't import session.py.

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Decomposition approach | In-place refactoring | Minimal disruption, same import paths | [ADR-0121](/docs/decisions/ADR-0121-savesession-decomposition-strategy.md) |
| Action method pattern | Descriptor-based factory | Generates methods at class definition, not call time; preserves signatures | [ADR-0122](/docs/decisions/ADR-0122-action-method-factory-pattern.md) |
| Healing extraction | Merge into healing.py | Single location for all healing logic | ADR-0121 |
| SessionState location | Keep in session.py | No value in moving; tests import SaveSession | ADR-0121 |
| Commit extraction | Defer (inline cleanup only) | Expected ~100 lines after other extractions | ADR-0121 |

## Complexity Assessment

**Level**: Module

This is a **structural refactoring** with:
- No new functionality
- No API changes
- No behavioral changes
- Reduced cognitive load through consolidation

The complexity is appropriate because:
- Changes are scoped to internal organization
- ActionBuilder is a well-understood Python pattern (descriptors)
- HealingManager follows existing Manager patterns in SDK
- Rollback is straightforward

## Implementation Plan

### Migration Strategy

Extraction proceeds in phases to maintain green tests throughout:

```
Phase 1: Foundation       <- Add properties, baseline benchmarks
Phase 2: ActionBuilder    <- Highest value extraction (920 -> 150 lines)
Phase 3: HealingManager   <- Merge into healing.py
Phase 4: State cleanup    <- Inline organization
Phase 5: Commit cleanup   <- Optional extraction
Phase 6: Validation       <- Final benchmarks, line count verification
```

### Phases

| Phase | Deliverable | Dependencies | Estimate | Validation |
|-------|-------------|--------------|----------|------------|
| 1 | Inspection properties + benchmarks | None | 1 hour | All tests pass |
| 2 | ActionBuilder + registry | Phase 1 | 3 hours | All action tests pass |
| 3 | HealingManager integration | Phase 1 | 2 hours | All healing tests pass |
| 4 | State cleanup | Phase 1 | 30 min | All tests pass |
| 5 | Commit cleanup (optional) | Phases 2-4 | 1 hour | All tests pass |
| 6 | Final validation | All phases | 1 hour | All metrics met |
| **Total** | | | **~8.5 hours** | |

### Phase Execution Details

#### Phase 1: Foundation (Preparation)

1. Add inspection properties to SaveSession:
   - `state`, `auto_heal`, `automation_enabled`
   - `pending_healing_count`, `healing_queue`
2. Update tests to use properties instead of private attributes
3. Create baseline benchmark script:
   ```python
   # scripts/benchmark_session.py
   def benchmark_100_entities_50_actions():
       """Baseline for NFR-PERF-001."""
       ...
   ```
4. Document baseline metrics

**Exit Criteria**: All tests pass, benchmarks documented

#### Phase 2: Action Method Factory

1. Create `persistence/actions.py`:
   - `ActionVariant` enum
   - `ActionConfig` dataclass
   - `ACTION_REGISTRY` with 18 configurations
   - `ActionBuilder` descriptor class
2. Update `SaveSession`:
   - Import ActionBuilder
   - Replace 13 action methods with ActionBuilder declarations
   - Keep 5 methods with custom logic (add_comment, set_parent, reorder_subtask, add_followers, remove_followers)
3. Verify all action tests pass
4. Run benchmarks to verify <5% regression

**Exit Criteria**: 920 lines reduced to ~150, all tests pass, benchmarks acceptable

#### Phase 3: Healing Manager

1. Expand `persistence/healing.py`:
   - Add `HealingManager` class
   - Move `_should_heal()`, `_queue_healing()`, `_execute_healing_async()` logic
   - Keep standalone utilities
2. Update `SaveSession`:
   - Replace `_healing_queue` and `_entity_heal_flags` with `HealingManager`
   - Update `track()` to use `HealingManager.should_heal()` and `queue()`
   - Update `commit_async()` to use `HealingManager.execute_async()`
3. Verify all healing tests pass

**Exit Criteria**: Healing logic consolidated, all tests pass

#### Phase 4: State Cleanup

1. Organize state-related code at top of SaveSession:
   - SessionState class
   - `_ensure_open()` method
   - Context managers
2. Add docstring sections for clarity
3. Verify all tests pass

**Exit Criteria**: Cleaner organization, all tests pass

#### Phase 5: Commit Cleanup (Optional)

1. Evaluate remaining `commit_async()` line count
2. If >100 lines, extract to private helper methods
3. If <100 lines, skip extraction
4. Verify all tests pass

**Exit Criteria**: Commit logic organized, all tests pass

#### Phase 6: Final Validation

1. Run full benchmark suite
2. Compare before/after metrics:
   - Line count: 2193 -> ~400 (82% reduction)
   - Commit latency: <5% regression
   - Memory: No regression
3. Verify all success metrics met
4. Update INDEX.md with new module

**Exit Criteria**: All PRD success metrics achieved

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-1: Descriptor pattern breaks signature inspection | High | Low | Use `functools.wraps` or `__signature__`; verify with `inspect.signature()` |
| R-2: Performance regression from descriptor dispatch | Medium | Low | Benchmark after Phase 2; inline hot paths if needed |
| R-3: Test breakage from property vs attribute | Low | Medium | Phase 1 adds properties before Phase 2 changes |
| R-4: Import cycle from actions.py | High | Low | actions.py imports only from models.py, validation.py (no session.py) |
| R-5: Custom action logic missed in extraction | High | Medium | Preserve add_comment, set_parent, reorder_subtask as explicit methods |
| R-6: HealingManager state mismatch | Medium | Low | Direct tests for queue/should_heal behavior |

## Rollback Plan

If extraction fails at any phase:

1. **Phase 1-3 incomplete**: Revert added properties/modules; session.py unchanged
2. **Phase 4-5 incomplete**: Revert inline changes; ActionBuilder/HealingManager stable
3. **Full rollback**: `git checkout HEAD -- src/autom8_asana/persistence/`

Rollback command:
```bash
git checkout HEAD -- src/autom8_asana/persistence/session.py
git checkout HEAD -- src/autom8_asana/persistence/healing.py
rm -f src/autom8_asana/persistence/actions.py
pytest tests/unit/persistence/test_session*.py  # Verify restoration
```

## Observability

Not applicable - this is a structural refactoring with no runtime behavioral changes.

Existing observability (structured logging via `_log`) is preserved through ActionBuilder's log_event configuration.

## Testing Strategy

### Unit Testing

All existing tests must pass unchanged:

| Test File | Lines | Focus | Validation |
|-----------|-------|-------|------------|
| `test_session.py` | 2112 | Core session, all 18 action methods | `pytest tests/unit/persistence/test_session.py` |
| `test_session_cascade.py` | 394 | Cascade queuing | `pytest tests/unit/persistence/test_session_cascade.py` |
| `test_session_healing.py` | 760 | Auto-heal, HealingManager | `pytest tests/unit/persistence/test_session_healing.py` |
| `test_session_business.py` | 250 | Recursive tracking | `pytest tests/unit/persistence/test_session_business.py` |

**New Tests Required**:

| Test | Purpose | Location |
|------|---------|----------|
| `test_action_builder.py` | ActionBuilder descriptor behavior | `tests/unit/persistence/test_action_builder.py` |
| `test_action_config.py` | ActionConfig validation | `tests/unit/persistence/test_action_builder.py` |

### Integration Testing

| Test | Validation |
|------|------------|
| Signature preservation | `inspect.signature(SaveSession.add_tag)` matches original |
| Fluent chaining | `session.add_tag(t, "x").add_to_project(t, "y")` works |
| Error handling | `PositioningConflictError` raised correctly |

### Performance Testing

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| 100 entities + 50 actions commit | TBD (Phase 1) | <105% of baseline | `scripts/benchmark_session.py` |
| 100 action registrations | TBD (Phase 1) | <1ms each | `scripts/benchmark_session.py` |
| Memory: 1000 tracked entities | TBD (Phase 1) | No regression | `tracemalloc` |

### Validation Commands

Run after each phase:
```bash
# All session tests
pytest tests/unit/persistence/test_session*.py -v

# Type checking
mypy src/autom8_asana/persistence/session.py
mypy src/autom8_asana/persistence/actions.py
mypy src/autom8_asana/persistence/healing.py

# Line count verification
wc -l src/autom8_asana/persistence/session.py
wc -l src/autom8_asana/persistence/actions.py
wc -l src/autom8_asana/persistence/healing.py

# Benchmark (after Phase 6)
python scripts/benchmark_session.py
```

### Exit Criteria

- [ ] All public API signatures unchanged (0 differences)
- [ ] All 3516+ test lines pass
- [ ] Line count: session.py ~400 lines (82% reduction from 2193)
- [ ] actions.py ~150 lines
- [ ] healing.py ~200 lines (expanded from ~80)
- [ ] Commit latency <5% regression
- [ ] Memory usage: no regression
- [ ] mypy passes with no errors
- [ ] All inspection properties working

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| OQ-1: Should ActionBuilder preserve `__doc__` from config or generate? | Architect | Phase 2 | Preserve from config for IDE support |
| OQ-2: Should healing.py export HealingManager in `__init__.py`? | Architect | Phase 3 | Yes, for direct usage |
| OQ-3: Should benchmark script be checked in? | Engineer | Phase 1 | Yes, in `scripts/` |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Architect (Claude) | Initial draft |
