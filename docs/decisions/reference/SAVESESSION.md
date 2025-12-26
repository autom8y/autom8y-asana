# ADR Summary: SaveSession & Persistence

> Consolidated decision record for save orchestration, change tracking, action management, and persistence lifecycle. Individual ADRs archived.

## Overview

SaveSession implements the Unit of Work pattern for deferred persistence in the autom8_asana SDK. Inspired by Django ORM and SQLAlchemy, it provides a context manager that batches entity modifications into optimized API calls, handling dependency ordering, change tracking, action operations, and error recovery.

The system evolved from simple batch saves to a sophisticated orchestration layer supporting complex operations: dependency graphs for correct save order, snapshot-based dirty detection, async-first concurrency, selective failure handling, action endpoint operations separate from CRUD, and composite entity hierarchies. This summary consolidates 22 individual ADRs spanning three years of design decisions into a coherent narrative of how SaveSession became the SDK's persistence engine.

## Key Decisions

### 1. Core Pattern: Unit of Work
**Context**: Need Django-ORM-style deferred saves where multiple model changes are collected and executed in optimized batches.

**Decision**: Implement Unit of Work pattern via SaveSession class as context manager with explicit `track()` and `commit()` lifecycle (ADR-0035).

**Rationale**:
- Familiar pattern (SQLAlchemy, Django ORM, Entity Framework)
- Explicit scope via context manager provides clear "batch operation boundary"
- State isolation per session prevents cross-session confusion
- Resource cleanup guaranteed even on exceptions
- Composable (multiple sessions possible, though discouraged for same entities)

**Key APIs**:
```python
# Async usage (primary)
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = await session.commit_async()

# Sync usage (wrapper)
with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = session.commit()
```

**Source ADRs**: ADR-0035

### 2. Change Tracking: Snapshot Comparison
**Context**: Must detect which entities have been modified since registration without modifying Pydantic models.

**Decision**: Use snapshot comparison via `model_dump()` for dirty detection (ADR-0036, ADR-0064).

**Rationale**:
- No model changes required (works with existing Pydantic models)
- Simple implementation (dictionary comparison)
- Handles nested objects reliably
- Field-level diff enables minimal update payloads
- Low overhead (<1ms per entity)

**Implementation**:
```python
# At track() time
snapshot = entity.model_dump()
self._snapshots[id(entity)] = snapshot

# At commit() time
current = entity.model_dump()
is_dirty = snapshot != current
changes = {k: (original[k], current[k]) for k in diff}
```

**Trade-offs**: O(n) comparison cost (acceptable for typical entity sizes), cannot detect intermediate changes (only initial vs final), requires object identity via `id()`.

**Source ADRs**: ADR-0036, ADR-0064

### 3. Dependency Ordering: Kahn's Algorithm
**Context**: Parent tasks must be saved before subtasks (children need parent GID reference).

**Decision**: Use Kahn's algorithm for topological sorting of dependency graph (ADR-0037).

**Rationale**:
- O(V+E) optimal complexity
- Natural cycle detection (if not all nodes processed, cycle exists)
- Level grouping enables parallel batching (nodes at same level are independent)
- BFS-based (iterative, no recursion stack limits)
- Deterministic output with consistent queue ordering

**Algorithm**:
1. Calculate in-degree for each node
2. Queue all nodes with in-degree 0
3. Process queue, decrementing in-degrees
4. If result contains all nodes, order valid; else cycle detected

**Source ADRs**: ADR-0037

### 4. Concurrency Model: Async-First
**Context**: Batch operations involve HTTP requests; need consistent concurrency pattern with SDK.

**Decision**: Async-first with sync wrappers, consistent with ADR-0002 (ADR-0038).

**Rationale**:
- Consistency with established SDK pattern
- Non-blocking I/O for batch operations
- Works for both async and sync callers
- Integrates naturally with async BatchClient
- Modern Python asyncio standard for I/O-bound operations

**Implementation**:
- `commit_async()` is primary implementation
- `commit()` uses `@sync_wrapper` decorator
- Context manager supports both `async with` and `with`
- All internal batch operations use async BatchClient

**Thread safety**: SaveSession is NOT thread-safe; single thread/coroutine use documented.

**Source ADRs**: ADR-0038

### 5. Error Handling: Commit and Report
**Context**: Asana Batch API returns per-action results; different actions can have different outcomes.

**Decision**: Commit all successful operations, report all failures in SaveResult; no rollback (ADR-0040, ADR-0065).

**Rationale**:
- Asana reality: No transaction support, no rollback capability
- Maximum information: Developer knows exactly what succeeded and failed
- Flexibility: Developer chooses how to handle (retry, log, escalate)
- Partial progress better than all-or-nothing for large batches

**SaveResult Structure**:
```python
@dataclass
class SaveResult:
    succeeded: list[AsanaResource]
    failed: list[SaveError]
    action_results: list[ActionResult]  # ADR-0055
```

**Dependency cascading**: When parent fails, dependent children marked as `DependencyResolutionError` with cause chain.

**P1 method exception**: Direct methods (e.g., `add_tag_async`) raise `SaveSessionError` on failure (ADR-0065), wrapping SaveResult for inspection.

**Source ADRs**: ADR-0040, ADR-0055, ADR-0065

### 6. Action Operations: Separate Type System
**Context**: Asana action endpoints (`/tasks/{gid}/addTag`) differ from CRUD (not batch-eligible, execute after CRUD, relationship-focused).

**Decision**: Create separate `ActionType` enum and `ActionOperation` dataclass; keep `OperationType` for CRUD (ADR-0042).

**Rationale**:
- Clear semantic separation (entity state changes vs relationship modifications)
- Independent execution paths (CRUD via BatchExecutor, actions via ActionExecutor)
- Type-safe dispatch (pattern matching catches missing cases)
- Clean extension (adding action types only affects action-related code)

**ActionType Values**:
```python
class ActionType(Enum):
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MOVE_TO_SECTION = "move_to_section"
    ADD_FOLLOWER = "add_follower"
    REMOVE_FOLLOWER = "remove_follower"
    ADD_LIKE = "add_like"
    REMOVE_LIKE = "remove_like"
```

**Source ADRs**: ADR-0042

### 7. Action Parameters: extra_params Design
**Context**: Different action types need different parameters (positioning, comment text, etc.).

**Decision**: Add `extra_params: dict[str, Any]` field to ActionOperation using `field(default_factory=dict)` for frozen dataclass compatibility (ADR-0044).

**Rationale**:
- Single unified type (no class explosion)
- Extensible (new action types need no structural changes)
- Frozen-safe (`default_factory=dict` provides correct immutability)
- Simple API (consumers pass dict, framework extracts known keys)

**Usage**:
```python
# Positioning parameters
extra_params={"insert_before": section_gid}

# Comment parameters
extra_params={"text": "...", "html_text": "..."}
```

**Trade-offs**: No static type checking (parameter names are strings), documentation burden, typo risk mitigated by tests.

**Source ADRs**: ADR-0044

### 8. Action Targets: NameGid and Optionality
**Context**: Like operations use authenticated user implicitly (no target parameter).

**Decision**: Make `target` optional with `NameGid | None = None`; use NameGid for identity preservation (ADR-0045, ADR-0107).

**Rationale** (Optionality):
- Like operations genuinely have no target (Asana API design)
- `None` accurately represents "not applicable"
- No dummy values or sentinel patterns
- Type reflects reality

**Rationale** (NameGid):
- Preserves name information without loss
- Consistent with SDK resource references (assignee, projects, sections)
- Enables automation matching on names (e.g., "Converted" section)
- Frozen/immutable like ActionOperation

**ActionOperation Structure**:
```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target: NameGid | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)
```

**Source ADRs**: ADR-0045, ADR-0107

### 9. Action Result Integration
**Context**: Action operation results were executed but discarded; failed actions silently lost.

**Decision**: Extend SaveResult to include `action_results: list[ActionResult]` as separate list (ADR-0055).

**Rationale**:
- Semantic mismatch: Actions operate on task-target pairs, not single entities like CRUD
- Type consistency: SaveError assumes AsanaResource, but actions relate to relationships
- Backward compatible: Adding optional field with default empty list

**New Properties**:
```python
@property
def action_succeeded(self) -> list[ActionResult]:
    return [r for r in self.action_results if r.success]

@property
def action_failed(self) -> list[ActionResult]:
    return [r for r in self.action_results if not r.success]

@property
def all_success(self) -> bool:
    return self.success and len(self.action_failed) == 0
```

**Source ADRs**: ADR-0055

### 10. Session Lifecycle: Implicit vs Explicit
**Context**: Task.save() and direct methods (add_tag_async) need persistence without explicit SaveSession.

**Decision**: Create and destroy SaveSession within method scope; no ambient session reuse (ADR-0061).

**Rationale**:
- Clear scope (session lifetime = method invocation)
- No nesting issues (can't accidentally nest contexts)
- Simple error handling (failure immediate and unambiguous)
- Consistency with P1 direct methods pattern

**Implementation**:
```python
async def save_async(self) -> Task:
    async with SaveSession(self._client) as session:
        session.track(self)
        result = await session.commit_async()
        if not result.success:
            raise result.failed[0].error
        return self
```

**Source ADRs**: ADR-0061, ADR-0059

### 11. Action Clearing: Selective on Success
**Context**: `_pending_actions.clear()` ran unconditionally; failed actions discarded, preventing retry.

**Decision**: Implement selective clearing based on action identity matching `(task.gid, action_type, target_gid)` (ADR-0066).

**Rationale**:
- Retry capability (failed actions remain in pending list)
- Inspection (get_pending_actions() shows exactly what failed)
- Semantic correctness (success clears, failure preserves)
- Efficient (O(n) matching with set membership)

**Algorithm**:
```python
def _clear_successful_actions(self, action_results: list[ActionResult]) -> None:
    successful_identities: set[tuple[str, ActionType, str | None]] = set()
    for result in action_results:
        if result.success:
            identity = (result.action.task.gid, result.action.action, result.action.target_gid)
            successful_identities.add(identity)

    self._pending_actions = [
        action for action in self._pending_actions
        if (action.task.gid, action.action, action.target_gid) not in successful_identities
    ]
```

**Source ADRs**: ADR-0066

### 12. Composite Entities: Optional Recursive Tracking
**Context**: Should tracking a Business entity automatically track its children (ContactHolder, UnitHolder, contacts, units)?

**Decision**: Provide optional recursive tracking via `track(entity, recursive=True)` flag, defaulting to `recursive=False` (ADR-0053).

**Rationale**:
- Explicit is better than implicit (Python Zen)
- Memory control (developer opts into large footprint)
- Debug-ability (preview shows exactly what's tracked)
- DependencyGraph handles ordering once entities are tracked
- Flexibility for common patterns (minimal, comprehensive, specific branches)

**Usage Patterns**:
```python
# Save entire hierarchy
session.track(business, recursive=True)

# Save only specific entities
session.track(business)
session.track(contact)

# Save business + contacts, not units
session.track(business)
session.track(business.contact_holder, recursive=True)
```

**Source ADRs**: ADR-0053

### 13. State Transitions: Composition over Extension
**Context**: Process entities need to move between pipeline states (Opportunity -> Active -> Converted).

**Decision**: Compose state transitions via `Process.move_to_state()` helper that wraps `SaveSession.move_to_section()`; do NOT add methods to SaveSession (ADR-0100).

**Rationale**:
- SaveSession remains entity-agnostic (no Process-specific logic)
- Process.move_to_state() is domain-appropriate
- Reuses existing move_to_section() implementation
- Fast section lookup via configuration (ProcessProjectRegistry)

**Implementation**:
```python
def move_to_state(self, session: SaveSession, target_state: ProcessSection) -> SaveSession:
    section_gid = registry.get_section_gid(process_type, target_state)
    return session.move_to_section(self, section_gid)
```

**Source ADRs**: ADR-0100

### 14. Automation Integration: Loop Prevention
**Context**: Automation rules can trigger other rules (cascade); need safeguards for circular references.

**Decision**: Use dual protection: depth limit AND visited set tracking `(entity_gid, rule_id)` pairs (ADR-0104).

**Rationale**:
- Defense in depth (two independent safeguards)
- Depth prevents unbounded chains
- Visited prevents true cycles
- Clear skip reasons for debugging

**AutomationContext**:
```python
@dataclass
class AutomationContext:
    depth: int = 0
    visited: set[tuple[str, str]] = field(default_factory=set)

    def can_continue(self, entity_gid: str, rule_id: str) -> bool:
        if self.depth >= self.config.max_cascade_depth:
            return False
        if (entity_gid, rule_id) in self.visited:
            return False
        return True
```

**Source ADRs**: ADR-0104

### 15. Task Duplication: Subtask Strategy
**Context**: Pipeline conversion creates new Process from template; template has subtasks.

**Decision**: Use `duplicate_async()` (wrapping Asana's `POST /tasks/{gid}/duplicate`) instead of manual creation (ADR-0110, ADR-0111).

**Rationale**:
- Atomic operation (parent + all subtasks in one request)
- Hierarchy preservation (nested subtasks copied automatically)
- Template evolution (changes automatically apply)
- Single API call vs N+1

**Subtask wait strategy**: Poll until subtask count matches expected (ADR-0111).
```python
async def wait_for_subtasks_async(
    task_gid: str,
    expected_count: int,
    timeout: float = 2.0,
    poll_interval: float = 0.2,
) -> bool:
    # Poll until count matches or timeout
```

**Source ADRs**: ADR-0110, ADR-0111

### 16. Architecture: Decomposition Strategy
**Context**: SaveSession grew to 2193 lines with 50 methods; "god class" symptoms.

**Decision**: Use in-place refactoring with sibling module extraction: keep SaveSession in `session.py`, create `actions.py` for ActionBuilder, expand `healing.py` (ADR-0121).

**Rationale**:
- Import path stability (no package, no re-exports needed)
- Test stability (no import updates)
- Code review simplicity (fewer files)
- SaveSession components tightly integrated (unlike detection tiers)

**Line reduction**: 2193 -> ~400 lines (82%) via:
- ActionBuilder (770 lines)
- HealingManager (115 lines)
- Inline cleanup (~900 lines)

**Source ADRs**: ADR-0121

### 17. Code Generation: ActionBuilder Pattern
**Context**: 18 action methods (920 lines) follow identical boilerplate patterns.

**Decision**: Use descriptor-based factory pattern with configuration registry (ADR-0122).

**Implementation**:
```python
# In SaveSession class:
add_tag = ActionBuilder("add_tag")
remove_tag = ActionBuilder("remove_tag")
# ... 13 total declarations

# Configuration registry
ACTION_REGISTRY["add_tag"] = ActionConfig(
    action_type=ActionType.ADD_TAG,
    variant=ActionVariant.TARGET_REQUIRED,
    target_param="tag",
    log_event="session_add_tag",
    docstring="Add a tag to a task...",
)
```

**Rationale**:
- Signature preservation (descriptors return bound methods)
- IDE support (`help()` and type hints work)
- Single source of truth (ACTION_REGISTRY)
- 920 -> ~150 lines (83% reduction)

**ActionVariants**: NO_TARGET (likes), TARGET_REQUIRED (tags, followers), POSITIONING (projects, sections).

**Source ADRs**: ADR-0122

### 18. Cache Integration: Invalidation Hook
**Context**: Modified entities must be invalidated in cache after successful commit.

**Decision**: Use post-commit callback (Phase 1.5) with GID collection and batch invalidation (ADR-0125).

**Implementation**:
```python
async def commit_async(self) -> SaveResult:
    # Phase 1: Execute CRUD and actions
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # Phase 1.5: Cache invalidation
    await self._invalidate_cache_for_results(crud_result, action_results)

    # Phase 2-5: Continue...
```

**Rationale**:
- Clean separation (invalidation logic isolated)
- Batch efficiency (O(n) invalidations via set deduplication)
- Comprehensive (covers CRUD and action operations)
- Resilient (failures logged, not propagated)

**Source ADRs**: ADR-0125

## Evolution Timeline

| Date | Decision | Impact |
|------|----------|--------|
| 2025-12-10 | ADR-0035: Unit of Work Pattern | Core SaveSession API established |
| 2025-12-10 | ADR-0036: Snapshot Comparison | Change tracking via model_dump() |
| 2025-12-10 | ADR-0037: Kahn's Algorithm | Dependency ordering for correct save order |
| 2025-12-10 | ADR-0038: Async-First Concurrency | Consistent with SDK patterns |
| 2025-12-10 | ADR-0040: Partial Failure Handling | Commit and report, no rollback |
| 2025-12-10 | ADR-0042: ActionType Enum | Separate type system for action operations |
| 2025-12-10 | ADR-0044: extra_params Field | Flexible action parameters |
| 2025-12-10 | ADR-0045: Like Operations | Optional target for implicit user |
| 2025-12-11 | ADR-0053: Composite SaveSession | Optional recursive tracking |
| 2025-12-12 | ADR-0055: Action Result Integration | action_results in SaveResult |
| 2025-12-12 | ADR-0059: Direct Methods | Convenience methods on TasksClient |
| 2025-12-12 | ADR-0061: Implicit Lifecycle | SaveSession created within methods |
| 2025-12-12 | ADR-0064: Dirty Detection | Leverage SaveSession ChangeTracker |
| 2025-12-12 | ADR-0065: SaveSessionError | Exception for P1 method failures |
| 2025-12-12 | ADR-0066: Selective Clearing | Only clear successful actions |
| 2025-12-17 | ADR-0100: State Transitions | Composition pattern for Process states |
| 2025-12-17 | ADR-0104: Loop Prevention | Dual protection (depth + visited set) |
| 2025-12-18 | ADR-0107: NameGid Targets | Preserve name information in actions |
| 2025-12-18 | ADR-0110: Task Duplication | duplicate_async() for template copying |
| 2025-12-18 | ADR-0111: Subtask Wait | Poll until subtasks created |
| 2025-12-19 | ADR-0121: Decomposition Strategy | In-place refactoring, 82% line reduction |
| 2025-12-19 | ADR-0122: ActionBuilder Pattern | Descriptor-based factory for methods |
| 2025-12-22 | ADR-0125: Cache Invalidation | Post-commit hook for cache freshness |

## Cross-References

### Related PRDs
- [PRD-0005: Save Orchestration](/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-0005-save-orchestration.md)
- [PRD-0006: Action Operations](/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-0006-action-operations.md)
- [PRD-0007: Extended Actions](/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-0007-extended-actions.md)
- [PRD-SDKUX: SDK Usability Overhaul](/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-SDKUX.md)
- [PRD-CACHE-INTEGRATION](/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-CACHE-INTEGRATION.md)

### Related TDDs
- [TDD-0010: Save Orchestration](/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-0010-save-orchestration.md)
- [TDD-0011: Action Operations](/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-0011-action-operations.md)
- [TDD-0012: Extended Actions](/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-0012-extended-actions.md)
- [TDD-CACHE-INTEGRATION](/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-CACHE-INTEGRATION.md)

### Related Summaries
- [ADR-SUMMARY-CACHE](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-SUMMARY-CACHE.md) - Cache invalidation hooks integrate with SaveSession
- [ADR-SUMMARY-DETECTION](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-SUMMARY-DETECTION.md) - Self-healing detection triggers SaveSession operations
- [ADR-SUMMARY-AUTOMATION](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-SUMMARY-AUTOMATION.md) - Automation rules use SaveSession for cascading changes

### Key Reference Documents
- [REF-savesession-lifecycle](/Users/tomtenuta/Code/autom8_asana/docs/reference/REF-savesession-lifecycle.md) - Session state machine and phase execution
- [REF-entity-lifecycle](/Users/tomtenuta/Code/autom8_asana/docs/reference/REF-entity-lifecycle.md) - Entity state from creation through persistence
- [REF-batch-operations](/Users/tomtenuta/Code/autom8_asana/docs/reference/REF-batch-operations.md) - Batch API integration details

## Archived Individual ADRs

The following individual ADRs have been consolidated into this summary and are considered archived for historical reference:

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| [ADR-0035](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0035-unit-of-work-pattern.md) | Unit of Work Pattern for Save Orchestration | 2025-12-10 | Context manager with explicit track/commit |
| [ADR-0036](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0036-change-tracking-strategy.md) | Change Tracking via Snapshot Comparison | 2025-12-10 | model_dump() snapshot comparison |
| [ADR-0037](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0037-dependency-graph-algorithm.md) | Kahn's Algorithm for Dependency Ordering | 2025-12-10 | Topological sort with cycle detection |
| [ADR-0038](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0038-save-concurrency-model.md) | Async-First Concurrency for Save Operations | 2025-12-10 | Async primary with sync wrappers |
| [ADR-0040](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0040-partial-failure-handling.md) | Commit and Report on Partial Failure | 2025-12-10 | No rollback; report all results |
| [ADR-0042](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0042-action-operation-types.md) | Separate ActionType Enum | 2025-12-10 | ActionType separate from OperationType |
| [ADR-0044](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0044-extra-params-field.md) | extra_params Field Design | 2025-12-10 | dict[str, Any] for action parameters |
| [ADR-0045](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0045-like-operations-without-target.md) | Like Operations Without Target GID | 2025-12-10 | Optional target: NameGid \| None |
| [ADR-0053](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0053-composite-savesession-support.md) | Composite SaveSession Support | 2025-12-11 | Optional recursive tracking |
| [ADR-0055](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0055-action-result-integration.md) | Action Result Integration | 2025-12-12 | action_results field in SaveResult |
| [ADR-0059](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0059-direct-methods-vs-session-actions.md) | Direct Methods vs SaveSession Actions | 2025-12-12 | Convenience methods on TasksClient |
| [ADR-0061](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0061-implicit-savesession-lifecycle.md) | Implicit SaveSession Lifecycle | 2025-12-12 | Create/destroy within method |
| [ADR-0064](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0064-dirty-detection-strategy.md) | Dirty Detection Strategy | 2025-12-12 | Leverage existing ChangeTracker |
| [ADR-0065](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0065-savesession-error-exception.md) | SaveSessionError Exception | 2025-12-12 | Exception wrapper for P1 failures |
| [ADR-0066](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0066-selective-action-clearing.md) | Selective Action Clearing Strategy | 2025-12-12 | Identity-based success clearing |
| [ADR-0100](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0100-state-transition-composition.md) | State Transition Composition | 2025-12-17 | Composition over extension |
| [ADR-0104](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0104-loop-prevention-strategy.md) | Loop Prevention Strategy | 2025-12-17 | Dual protection mechanism |
| [ADR-0107](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0107-namegid-action-targets.md) | NameGid for ActionOperation Targets | 2025-12-18 | NameGid preserves name information |
| [ADR-0110](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0110-task-duplication-strategy.md) | Task Duplication vs Creation | 2025-12-18 | duplicate_async() for templates |
| [ADR-0111](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0111-subtask-wait-strategy.md) | Subtask Wait Strategy | 2025-12-18 | Poll until count matches expected |
| [ADR-0121](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0121-savesession-decomposition-strategy.md) | SaveSession Decomposition Strategy | 2025-12-19 | In-place refactoring approach |
| [ADR-0122](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0122-action-method-factory-pattern.md) | Action Method Factory Pattern | 2025-12-19 | Descriptor-based generation |
| [ADR-0125](/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-0125-savesession-invalidation.md) | SaveSession Cache Invalidation Hook | 2025-12-22 | Post-commit callback pattern |

## Implementation Guidance

### When to Use SaveSession Explicitly

Use explicit SaveSession context for:
- Batch operations (multiple entities)
- Complex workflows requiring preview
- Operations needing transaction-like boundaries
- Custom error handling requirements

```python
async with SaveSession(client) as session:
    for task in tasks:
        session.track(task)
        task.name = f"Updated {task.name}"

    # Preview before committing
    ops, actions = session.preview()
    print(f"Will execute {len(ops)} operations")

    result = await session.commit_async()
    if not result.all_success:
        # Handle partial failures
        for err in result.failed:
            print(f"Failed: {err.entity.gid} - {err.error}")
```

### When to Use Direct Methods

Use direct methods for:
- Single-entity operations
- Simple workflows
- Quick scripts and CLI tools

```python
# Simple one-liner
task = await client.tasks.add_tag_async(task_gid, tag_gid)

# Or Task instance method
task.name = "Updated"
await task.save_async()
```

### Common Patterns

**Hierarchical saves with dependencies**:
```python
async with SaveSession(client) as session:
    session.track(parent_task, recursive=True)  # Tracks parent + all children
    parent_task.name = "Parent Updated"
    parent_task.subtasks[0].name = "Child Updated"

    result = await session.commit_async()
    # Parent saved first, then children (automatic ordering)
```

**Batch actions with positioning**:
```python
async with SaveSession(client) as session:
    for task in tasks:
        session.move_to_section(task, section_gid, insert_after=previous_task_gid)

    result = await session.commit_async()
```

**Retry on partial failure**:
```python
async with SaveSession(client) as session:
    session.track_many(tasks)
    result = await session.commit_async()

    if not result.all_success:
        # Failed actions remain in pending queue
        pending = session.get_pending_actions()
        # Fix issues, then retry
        result2 = await session.commit_async()
```

## Future Considerations

### Potential Enhancements
- Optimistic locking (version-based conflict detection)
- Batch size limits with automatic chunking
- Transaction log for replay/audit
- Dry-run mode for validation without commit
- Metrics collection (operation counts, timing)

### Extension Points
- Custom validation hooks (pre-commit)
- Custom transformation hooks (pre-save)
- Custom conflict resolution strategies
- Alternative change tracking strategies for performance

### Limitations
- No true atomicity (Asana has no rollback)
- No cross-session transactions
- Dependency cycles rejected (no circular references)
- Thread-unsafe (single thread/coroutine per session)
- Memory bounded by tracked entity count
