# TDD: SDK Demonstration Suite

## Metadata
- **TDD ID**: TDD-SDKDEMO
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-12
- **Last Updated**: 2025-12-12
- **PRD Reference**: [PRD-SDKDEMO](/docs/requirements/PRD-SDKDEMO.md)
- **Discovery Document**: [DISCOVERY-SDKDEMO](/docs/validation/DISCOVERY-SDKDEMO.md)
- **Related TDDs**: None
- **Related ADRs**:
  - [ADR-DEMO-001](/docs/decisions/ADR-DEMO-001-state-capture-strategy.md) - State Capture Strategy
  - [ADR-DEMO-002](/docs/decisions/ADR-DEMO-002-name-resolution-approach.md) - Name Resolution Approach
  - [ADR-DEMO-003](/docs/decisions/ADR-DEMO-003-error-handling-strategy.md) - Error Handling Strategy

---

## Overview

Interactive demonstration suite that validates all 10 SDK operation categories against a real Asana workspace. The demo uses the SDK's SaveSession (Unit of Work pattern), action operations, and CustomFieldAccessor to perform CRUD and relationship operations, with full state capture for restoration after each demo category completes.

---

## Requirements Summary

From PRD-SDKDEMO:
- **FR-TAG**: Tag add/remove operations
- **FR-DEP**: Dependency and dependent operations
- **FR-DESC**: Description (notes) modifications
- **FR-CF-STR/PPL/ENM/NUM/MEN**: Custom field operations (string, people, enum, number, multi-enum)
- **FR-SUB**: Subtask parent and reorder operations
- **FR-MEM**: Project membership and section operations
- **FR-INT**: Interactive confirmation before every mutation
- **FR-REST**: State capture and restoration
- **FR-RES**: Name-to-GID resolution without hardcoding

---

## System Context

```
+-------------------+     +------------------+     +---------------+
|  Demo Scripts     |---->|  autom8_asana    |---->|  Asana API    |
|  (scripts/)       |     |  SDK             |     |  (REST)       |
+-------------------+     +------------------+     +---------------+
       |                         |
       |  Uses                   |  Provides
       v                         v
+-------------------+     +------------------+
|  Console I/O      |     |  SaveSession     |
|  (user prompts)   |     |  ActionExecutor  |
+-------------------+     |  CustomFieldAccessor
                          +------------------+
```

The demo scripts are consumers of the SDK, validating SDK functionality against the live Asana API. They do not modify SDK internals.

---

## Design

### Module Structure

```
scripts/
    demo_sdk_operations.py    # Main entry point - 10 demo categories
    demo_business_model.py    # Business model hierarchy traversal (secondary)
    _demo_utils.py            # Shared utilities (internal module)
```

**File Purposes**:

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `demo_sdk_operations.py` | Main demo orchestration, 10 category implementations | ~600 |
| `demo_business_model.py` | Business -> Unit -> Offer traversal demo | ~150 |
| `_demo_utils.py` | NameResolver, StateManager, DemoLogger, UserAction | ~300 |

---

### Component Architecture

```
demo_sdk_operations.py
        |
        +-- DemoRunner (orchestration)
        |       |
        |       +-- run_category(category_func)
        |       +-- display_summary()
        |       +-- restore_all()
        |
        +-- Category Functions (10 total)
                |
                +-- demo_tag_operations()
                +-- demo_dependency_operations()
                +-- demo_description_operations()
                +-- demo_string_cf_operations()
                +-- demo_people_cf_operations()
                +-- demo_enum_cf_operations()
                +-- demo_number_cf_operations()
                +-- demo_multienum_cf_operations()
                +-- demo_subtask_operations()
                +-- demo_membership_operations()

_demo_utils.py
        |
        +-- UserAction (enum)
        +-- confirm() -> UserAction
        +-- NameResolver
        +-- StateManager
        +-- DemoLogger
        +-- DemoError (dataclass)
        +-- EntityState (dataclass)
        +-- MembershipState (dataclass)
        +-- TaskSnapshot (dataclass)
        +-- RestoreResult (dataclass)
```

| Component | Responsibility | Owner |
|-----------|----------------|-------|
| `DemoRunner` | Orchestrate category execution, error collection, final restoration | Demo Scripts |
| `NameResolver` | Lazy-load name-to-GID mappings with caching | Demo Scripts |
| `StateManager` | Capture and restore entity state | Demo Scripts |
| `DemoLogger` | Structured logging with verbosity control | Demo Scripts |
| `confirm()` | Interactive user prompts with preview display | Demo Scripts |
| Category Functions | Implement each demo category's operations | Demo Scripts |

---

### Data Structures

#### EntityState (ADR-DEMO-001)

```python
@dataclass
class EntityState:
    """Captured scalar/custom field state of an entity."""
    gid: str
    notes: str | None = None
    html_notes: str | None = None
    name: str | None = None
    completed: bool | None = None
    due_on: str | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)  # {field_gid: value}
```

#### MembershipState

```python
@dataclass
class MembershipState:
    """Task's membership in a project/section."""
    project_gid: str
    section_gid: str | None = None
```

#### TaskSnapshot

```python
@dataclass
class TaskSnapshot:
    """Complete snapshot of a task for restoration."""
    entity_state: EntityState
    tag_gids: list[str] = field(default_factory=list)
    parent_gid: str | None = None
    memberships: list[MembershipState] = field(default_factory=list)
    dependency_gids: list[str] = field(default_factory=list)
    dependent_gids: list[str] = field(default_factory=list)
```

#### RestoreResult

```python
@dataclass
class RestoreResult:
    """Outcome of a restoration attempt."""
    entity_gid: str
    success: bool
    fields_restored: list[str] = field(default_factory=list)
    fields_failed: list[str] = field(default_factory=list)
    error: str | None = None
```

#### DemoError

```python
@dataclass
class DemoError:
    """Structured error with recovery guidance."""
    category: str       # e.g., "tag_operation", "custom_field"
    operation: str      # e.g., "add_tag", "set_field"
    entity_gid: str
    message: str
    recovery_hint: str | None = None
```

#### UserAction (Enum)

```python
class UserAction(Enum):
    """User response to confirmation prompt."""
    EXECUTE = "execute"   # Enter pressed
    SKIP = "skip"         # 's' pressed
    QUIT = "quit"         # 'q' pressed
```

---

### Component Specifications

#### UserAction Enum and confirm() Function

```python
class UserAction(Enum):
    """User response to confirmation prompt."""
    EXECUTE = "execute"
    SKIP = "skip"
    QUIT = "quit"

def confirm(
    operation_description: str,
    crud_ops: list[PlannedOperation],
    action_ops: list[ActionOperation],
) -> UserAction:
    """Display preview and prompt for user confirmation.

    Args:
        operation_description: Human-readable description of pending operation
        crud_ops: CRUD operations from session.preview()
        action_ops: Action operations from session.preview()

    Returns:
        UserAction indicating user's choice

    Display Format:
        --- {operation_description} ---

        CRUD Operations:
          CREATE Task(temp_1): {name: "...", notes: "..."}
          UPDATE Task(123456): {notes: "changed"}

        Action Operations:
          ADD_TAG on task 123456 -> tag 789012
          MOVE_TO_SECTION on task 123456 -> section 345678

        Press Enter to execute, 's' to skip, 'q' to quit:
    """
```

#### NameResolver Class (ADR-DEMO-002)

```python
class NameResolver:
    """Resolves human-readable names to Asana GIDs with lazy caching."""

    def __init__(self, client: AsanaClient, workspace_gid: str) -> None:
        """Initialize resolver.

        Args:
            client: SDK client for API calls
            workspace_gid: Workspace for tag/user lookups
        """

    async def resolve_tag(self, name: str) -> str | None:
        """Resolve tag name to GID. Case-insensitive.

        Returns None if tag not found.
        """

    async def resolve_user(self, display_name: str) -> str | None:
        """Resolve user display name to GID. Case-insensitive.

        Returns None if user not found.
        """

    async def resolve_section(self, project_gid: str, name: str) -> str | None:
        """Resolve section name within a project. Case-insensitive.

        Returns None if section not found.
        """

    async def resolve_project(self, name: str) -> str | None:
        """Resolve project name to GID. Case-insensitive.

        Returns None if project not found.
        """

    async def resolve_enum_option(
        self,
        custom_field_gid: str,
        option_name: str,
    ) -> str | None:
        """Resolve enum option name to GID within a custom field.

        Requires fetching custom field definition to get options.
        Returns None if option not found.
        """

    def clear_cache(self) -> None:
        """Clear all cached lookups. Useful for testing."""
```

#### StateManager Class (ADR-DEMO-001)

```python
class StateManager:
    """Manages entity state capture and restoration."""

    def __init__(self, client: AsanaClient) -> None:
        """Initialize with SDK client for restoration operations."""

    async def capture(self, task: Task) -> TaskSnapshot:
        """Capture current state of a task.

        Captures:
        - Scalar fields (notes, name, completed, due_on)
        - Custom field values (keyed by GID)
        - Tag GIDs
        - Parent GID
        - Membership (project/section) GIDs
        - Dependency/dependent GIDs
        """

    def store_initial(self, gid: str, snapshot: TaskSnapshot) -> None:
        """Store snapshot as initial state for later restoration."""

    def store_current(self, gid: str, snapshot: TaskSnapshot) -> None:
        """Update current state after successful operation."""

    def get_initial(self, gid: str) -> TaskSnapshot | None:
        """Get initial state snapshot."""

    def get_current(self, gid: str) -> TaskSnapshot | None:
        """Get current state snapshot."""

    def has_changes(self, gid: str) -> bool:
        """Check if entity has changed from initial state."""

    async def restore(self, gid: str, session: SaveSession) -> RestoreResult:
        """Restore entity to initial state using SaveSession.

        Restoration order:
        1. Restore scalar fields via track() and field assignment
        2. Restore custom fields via CustomFieldAccessor
        3. Restore tags via add_tag/remove_tag
        4. Restore parent via set_parent
        5. Restore memberships via move_to_section
        6. Restore dependencies via add_dependency/remove_dependency

        Returns RestoreResult with success status and details.
        """

    async def restore_all(self, session: SaveSession) -> list[RestoreResult]:
        """Restore all tracked entities to initial state."""
```

#### DemoLogger Class

```python
class DemoLogger:
    """Structured logging for demo operations."""

    def __init__(self, verbose: bool = False) -> None:
        """Initialize logger.

        Args:
            verbose: If True, log detailed operation info
        """

    def category_start(self, name: str) -> None:
        """Log start of demo category."""

    def category_end(self, name: str, success: bool) -> None:
        """Log end of demo category."""

    def operation(self, op_type: str, entity_gid: str, details: dict[str, Any]) -> None:
        """Log operation execution."""

    def resolution(self, resource_type: str, name: str, gid: str | None) -> None:
        """Log name resolution result."""

    def error(self, error: DemoError) -> None:
        """Log error with recovery hint."""

    def state_capture(self, gid: str, snapshot: TaskSnapshot) -> None:
        """Log state capture (verbose only)."""

    def state_restore(self, result: RestoreResult) -> None:
        """Log restoration result."""
```

#### DemoRunner Class

```python
class DemoRunner:
    """Orchestrates demo execution with error handling."""

    def __init__(
        self,
        client: AsanaClient,
        resolver: NameResolver,
        state_manager: StateManager,
        logger: DemoLogger,
    ) -> None:
        """Initialize runner with dependencies."""

    @property
    def errors(self) -> list[DemoError]:
        """All errors collected during demo."""

    async def run_category(
        self,
        name: str,
        category_func: Callable[[], Coroutine[Any, Any, None]],
    ) -> bool:
        """Execute a demo category with error handling.

        Returns True if category completed without errors.
        """

    async def run_operation(
        self,
        op_name: str,
        operation: Callable[[], Coroutine[Any, Any, Any]],
        entity_gid: str,
        recovery_hint: str | None = None,
    ) -> bool:
        """Execute single operation with error handling.

        Handles:
        - RateLimitError: Wait and retry
        - AsanaAPIError: Log and return False
        - Other exceptions: Log and return False

        Returns True if operation succeeded.
        """

    def display_summary(self) -> None:
        """Print demo summary with success/failure counts."""

    def generate_recovery_instructions(self) -> str:
        """Generate manual recovery instructions for failures."""
```

---

### Data Flow: Confirmation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Demo Category Function                       │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Set up operation (e.g., session.add_tag(task, tag_gid))      │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Call session.preview() -> (crud_ops, action_ops)             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Call confirm(description, crud_ops, action_ops)              │
│     - Display operation preview to user                          │
│     - Wait for user input                                        │
└─────────────────────────────────────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
      [EXECUTE]           [SKIP]             [QUIT]
            │                  │                  │
            ▼                  │                  ▼
┌───────────────────┐          │       ┌──────────────────┐
│ 4a. commit_async()│          │       │ 4c. Restore all, │
│ 5a. Update state  │          │       │     then exit    │
│ 6a. Log success   │          │       └──────────────────┘
└───────────────────┘          │
            │                  │
            └────────┬─────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Return to category function for next operation                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Data Flow: Restoration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    StateManager.restore(gid)                     │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Get initial_snapshot and current_snapshot                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Compute deltas:                                              │
│     - fields_to_restore = {f: initial[f] for f if f != current} │
│     - tags_to_add = initial.tags - current.tags                 │
│     - tags_to_remove = current.tags - initial.tags              │
│     - (similar for dependencies, memberships)                   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. Phase 1: CRUD Restoration                                    │
│     - session.track(task)                                        │
│     - task.notes = initial_snapshot.notes                        │
│     - task.custom_fields.set(gid, value) for each               │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Phase 2: Action Restoration                                  │
│     - session.remove_tag(task, gid) for tags_to_remove          │
│     - session.add_tag(task, gid) for tags_to_add                │
│     - session.set_parent(task, initial.parent_gid)              │
│     - session.move_to_section(task, initial.section_gid)        │
│     - session.add_dependency/remove_dependency                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. session.commit_async()                                       │
└─────────────────────────────────────────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
            ▼                                     ▼
      [SUCCESS]                             [FAILURE]
            │                                     │
            ▼                                     ▼
┌───────────────────┐                  ┌──────────────────┐
│ Return RestoreResult                 │ Return RestoreResult
│   success=True                       │   success=False
│   fields_restored=[...]              │   fields_failed=[...]
└───────────────────┘                  │   error=str(e)
                                       │   recovery_hint=...
                                       └──────────────────┘
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| State capture strategy | Shallow copy with GID references | Memory efficient, SDK-aligned | ADR-DEMO-001 |
| Name resolution | Lazy-loading with session cache | Minimizes startup latency | ADR-DEMO-002 |
| Error handling | Graceful degradation with recovery guidance | Demo continuity over fail-fast | ADR-DEMO-003 |
| Confirmation UI | Enter/s/q pattern | Simple, consistent, keyboard-friendly | N/A (obvious) |
| Module prefix | `_demo_utils.py` with underscore | Signals internal/non-public module | N/A (convention) |

---

## Complexity Assessment

**Level: Module**

This is a **Module-level** implementation:
- Clean API surface (demo functions, utility classes)
- Clear boundaries (demo scripts, utility module)
- Minimal structure (no layered architecture needed)
- Self-contained (no external services beyond Asana API)

**Why not Script?**
- Multiple files with shared utilities
- State management requires reusable classes
- Name resolution warrants dedicated component

**Why not Service?**
- No external API contract to expose
- No independent deployment
- No observability requirements beyond logging
- Single-user interactive tool

---

## Implementation Plan

### Phase 1: Foundation (Est. 2-3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `_demo_utils.py` with UserAction, confirm(), DemoError | None | 1 hour |
| `_demo_utils.py` with EntityState, TaskSnapshot, RestoreResult | None | 30 min |
| `_demo_utils.py` with NameResolver (tags, users) | SDK clients | 1 hour |

### Phase 2: State Management (Est. 2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| StateManager.capture() | TaskSnapshot dataclass | 45 min |
| StateManager.restore() for scalar/custom fields | SaveSession | 45 min |
| StateManager.restore() for relationships | Action operations | 30 min |

### Phase 3: Demo Infrastructure (Est. 1-2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| DemoLogger class | None | 30 min |
| DemoRunner class | All utility classes | 1 hour |
| Pre-flight checks in main() | SDK clients | 30 min |

### Phase 4: Demo Categories (Est. 3-4 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| demo_tag_operations() | NameResolver.resolve_tag | 20 min |
| demo_dependency_operations() | SaveSession action ops | 30 min |
| demo_description_operations() | SaveSession track/commit | 20 min |
| demo_string_cf_operations() | CustomFieldAccessor | 20 min |
| demo_people_cf_operations() | NameResolver.resolve_user | 30 min |
| demo_enum_cf_operations() | NameResolver.resolve_enum_option | 30 min |
| demo_number_cf_operations() | CustomFieldAccessor | 20 min |
| demo_multienum_cf_operations() | CustomFieldAccessor, multi-enum semantics | 40 min |
| demo_subtask_operations() | set_parent, reorder_subtask | 30 min |
| demo_membership_operations() | move_to_section, add/remove_from_project | 30 min |

### Phase 5: Polish (Est. 1 hour)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Final restoration and summary | All categories | 30 min |
| Verbose logging mode | DemoLogger | 20 min |
| Manual recovery instructions | DemoError collection | 10 min |

**Total Estimate**: 9-12 hours

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Test entity GIDs invalid | High | Medium | Pre-flight check verifies access; fail fast |
| Tag "optimize" doesn't exist | Low | High | Offer to create if missing |
| Rate limiting during demo | Medium | Medium | Auto-retry on 429 with backoff |
| State restoration fails | High | Medium | Provide manual recovery commands |
| Custom field schema changed | Medium | Low | Fetch current definition; handle missing fields |
| Multi-enum replace semantics surprise | Low | Medium | Log clear warning before multi-enum operations |
| User not found for people CF | Low | Medium | Graceful skip with message |

---

## Observability

### Logging

All operations logged via DemoLogger:
- **Category start/end**: `[DEMO] Starting: Tag Operations`
- **Operation execution**: `[OP] add_tag: task=123456, tag=789012`
- **Name resolution**: `[RESOLVE] tag "optimize" -> 789012`
- **Errors**: `[ERROR] add_tag failed: 403 Forbidden`
- **Verbose mode**: State snapshots, API response details

### Metrics (Not Applicable)

Demo scripts are interactive CLI tools, not services. No metrics collection required.

### Alerting (Not Applicable)

No production deployment, no alerting needed.

---

## Testing Strategy

### Unit Testing

| Test Area | Approach |
|-----------|----------|
| `confirm()` function | Mock stdin, verify UserAction return |
| `NameResolver` | Mock SDK clients, verify caching behavior |
| `StateManager.capture()` | Provide mock Task, verify snapshot fields |
| `StateManager.restore()` | Mock SaveSession, verify action operations called |
| `DemoError` / dataclasses | Test serialization, equality |

### Integration Testing

| Test Area | Approach |
|-----------|----------|
| Full demo run (happy path) | Live Asana workspace with test entities |
| Name resolution against live API | Verify tag/user/section lookup |
| Restoration correctness | Modify entity, restore, fetch and compare |

### Manual Testing

| Test Scenario | Steps |
|---------------|-------|
| Skip operation | Press 's' during confirmation |
| Quit demo | Press 'q' during confirmation, verify restoration |
| Rate limit handling | Trigger 429 (many rapid operations), verify retry |
| Missing tag | Run with non-existent tag name, verify prompt |

---

## PRD Traceability Matrix

| PRD Requirement | TDD Component | Verification |
|-----------------|---------------|--------------|
| FR-TAG-001..005 | `demo_tag_operations()`, NameResolver | Tags added/removed via session.add_tag/remove_tag |
| FR-DEP-001..006 | `demo_dependency_operations()` | Dependencies created via session.add_dependency |
| FR-DESC-001..005 | `demo_description_operations()` | Notes modified via session.track(), task.notes = |
| FR-CF-STR-001..005 | `demo_string_cf_operations()` | String CF via CustomFieldAccessor.set() |
| FR-CF-PPL-001..005 | `demo_people_cf_operations()` | People CF via CustomFieldAccessor.set() with user GID |
| FR-CF-ENM-001..005 | `demo_enum_cf_operations()` | Enum CF via CustomFieldAccessor.set() with option GID |
| FR-CF-NUM-001..004 | `demo_number_cf_operations()` | Number CF via CustomFieldAccessor.set() |
| FR-CF-MEN-001..006 | `demo_multienum_cf_operations()` | Multi-enum via CustomFieldAccessor.set() with list |
| FR-SUB-001..006 | `demo_subtask_operations()` | Subtask via session.set_parent(), session.reorder_subtask() |
| FR-MEM-001..006 | `demo_membership_operations()` | Membership via session.move_to_section(), add/remove_from_project() |
| FR-INT-001..006 | `confirm()` function | Preview via session.preview(), Enter/s/q prompts |
| FR-REST-001..006 | `StateManager` class | TaskSnapshot captures all fields, restore() applies |
| FR-RES-001..006 | `NameResolver` class | Lazy-load with case-insensitive matching |

---

## Implementation Notes for Engineer

### SDK Patterns to Follow

1. **Async-first**: All demo operations should be async. Use `asyncio.run()` only in `main()`.

2. **SaveSession lifecycle**:
   ```python
   async with SaveSession(client) as session:
       session.track(entity)
       # modify entity
       session.add_tag(entity, tag_gid)
       crud_ops, action_ops = session.preview()
       # confirm with user
       result = await session.commit_async()
   ```

3. **CustomFieldAccessor usage**:
   ```python
   # Get value
   current = task.custom_fields.get("Field Name")
   # Set value
   task.custom_fields.set("Field Name", new_value)
   # Clear value
   task.custom_fields.set("Field Name", None)
   ```

4. **Multi-enum replace semantics** (from Discovery):
   ```python
   # To "add" an option to multi-enum, read current + append + set
   current = task.custom_fields.get("Multi Field") or []
   current_gids = [opt["gid"] for opt in current]
   task.custom_fields.set("Multi Field", current_gids + [new_option_gid])
   ```

### Test Entity GIDs

From PRD-SDKDEMO Test Data Requirements:
- Business: `1203504488813198`
- Unit: `1203504489143268`
- Dependency Task: `1211596978294356`
- Subtask: `1203996810236966`
- Reconciliation Holder: `1203504488912317`

### Pre-flight Checks

Before any demo operations:
1. Verify all entity GIDs are accessible (404 = abort)
2. Get workspace GID from Business entity
3. Verify "optimize" tag exists (or offer to create)
4. Verify required custom fields exist on entities
5. Verify user has write permissions (try a harmless read)

### Restoration Order

When restoring an entity:
1. **CRUD first**: Track entity, set scalar fields and custom fields
2. **Commit CRUD**: Get entity in correct field state
3. **Actions second**: Tags, parent, section, dependencies
4. **Commit actions**: Relationships restored

This two-phase approach ensures custom fields are set before potentially conflicting relationship operations.

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Which string CF to demo? | Product | Before coding | Use "Office Phone" on Business |
| Which enum CF to demo? | Product | Before coding | Use "Status" or similar on Business |
| Which number CF to demo? | Product | Before coding | Use "MRR" or similar on Business |
| Which people CF to demo? | Product | Before coding | Use "Lead Owner" or "Assignee" |
| Create tag if missing, or error? | Product | Before coding | Offer to create with user confirmation |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Architect | Initial draft |

---

## Quality Gates Checklist

- [x] Traces to approved PRD (PRD-SDKDEMO)
- [x] All significant decisions have ADRs (3 ADRs created)
- [x] Component responsibilities are clear (DemoRunner, NameResolver, StateManager)
- [x] Interfaces defined (all public methods specified)
- [x] Complexity level justified (Module)
- [x] Risks identified with mitigations (7 risks documented)
- [x] Implementation plan is actionable (5 phases with estimates)

