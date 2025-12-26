# ADR-0043: SaveSession Action Operations Architecture

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-10, Updated 2025-12-12
- **Consolidated From**: ADR-0042 (action types), ADR-0044, ADR-0045, ADR-0055, ADR-0059
- **Related**: [reference/SAVESESSION.md](/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/SAVESESSION.md), PRD-0006, PRD-0007, TDD-0011, TDD-0012

## Context

Asana provides action endpoints for relationship operations that differ fundamentally from standard CRUD operations. The Save Orchestration Layer needed to support operations like `add_tag()`, `remove_tag()`, `add_to_project()`, `move_to_section()`, and `add_like()`.

Key architectural decisions required:
1. **Type System**: How to model action operations separately from CRUD?
2. **Flexible Parameters**: How to handle action-specific parameters (positioning, comment text)?
3. **Optional Targets**: How to handle operations without explicit targets (likes)?
4. **Result Integration**: How to report action operation outcomes alongside CRUD results?
5. **Convenience Methods**: Should we provide direct methods alongside session-based operations?

Forces at play:
- **Different API Pattern**: `POST /tasks/{gid}/addTag` vs `PUT /tasks/{gid}`
- **Not Batch-Eligible**: Asana Batch API only supports CRUD; actions execute individually
- **Execution Ordering**: Actions must execute AFTER entity CRUD (entity must exist)
- **Semantic Difference**: CRUD changes entity state; actions modify relationships
- **Parameter Diversity**: Different actions need different parameters (positioning, text, etc.)
- **Type Safety**: Want compile-time guarantees about operation handling
- **Developer Experience**: Simple operations should be simple (one-liners)

## Decision

### Separate ActionType Enum and ActionOperation

Create distinct type system for action operations:

```python
class ActionType(Enum):
    """Type of action operation requiring dedicated API endpoint.

    Separate from OperationType because action operations have different
    execution characteristics (not batch-eligible, execute after CRUD,
    relationship-focused).
    """
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

@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation requiring dedicated API endpoint.

    Action operations queue and execute on commit, after CRUD operations.

    Attributes:
        task: The task this action operates on
        action: The type of action (ADD_TAG, ADD_FOLLOWER, etc.)
        target: NameGid of target entity (tag, user, project, etc.)
                Optional for like operations (uses authenticated user)
        extra_params: Additional parameters for positioning or comments
    """
    task: AsanaResource
    action: ActionType
    target: NameGid | None = None  # Optional for likes
    extra_params: dict[str, Any] = field(default_factory=dict)
```

**Why Separate from OperationType:**
- CRUD operations (`CREATE`, `UPDATE`, `DELETE`) map to HTTP methods and batch API
- Action operations use dedicated endpoints and execute individually
- Clear semantic separation: entity state changes vs relationship modifications
- Independent execution paths: CRUD via BatchExecutor, actions via ActionExecutor
- Type-safe dispatch: pattern matching catches missing cases

### Flexible Parameters via extra_params

Use `dict[str, Any]` field with `field(default_factory=dict)` for frozen dataclass compatibility:

```python
# Positioning parameters
session.move_to_section(
    task,
    section_gid,
    insert_after=previous_task_gid
)
# Stored as: extra_params={"insert_after": "previous_task_gid"}

# Comment parameters
session.add_comment(
    task,
    text="Progress update",
    html_text="<strong>Progress</strong> update"
)
# Stored as: extra_params={"text": "...", "html_text": "..."}
```

**Why dict[str, Any]:**
- Single unified type (no class explosion for each action)
- Extensible (new action types need no structural changes)
- Frozen-safe (`default_factory=dict` provides correct immutability)
- Simple API (consumers pass dict, framework extracts known keys)

**Trade-offs:**
- No static type checking for parameter names (mitigated by tests)
- Documentation burden (must document valid keys per action type)
- Typo risk (invalid keys silently ignored)

### Optional Target with NameGid

Make `target` optional and use NameGid for identity preservation:

```python
# Like operations have no explicit target (uses authenticated user)
session.add_like(task)
# ActionOperation(task, ActionType.ADD_LIKE, target=None)

# Other operations have explicit targets
session.add_tag(task, tag)
# ActionOperation(task, ActionType.ADD_TAG, target=NameGid(tag.gid, tag.name))
```

**Why Optional:**
- Like operations genuinely have no target (Asana API design)
- `None` accurately represents "not applicable"
- No dummy values or sentinel patterns
- Type reflects reality

**Why NameGid:**
- Preserves name information without loss
- Consistent with SDK resource references (assignee, projects, sections)
- Enables automation matching on names (e.g., "Converted" section)
- Frozen/immutable like ActionOperation

### Action Result Integration

Extend SaveResult to include action outcomes:

```python
@dataclass
class SaveResult:
    succeeded: list[AsanaResource]      # CRUD successes
    failed: list[SaveError]             # CRUD failures
    action_results: list[ActionResult]  # Action outcomes

    @property
    def action_succeeded(self) -> list[ActionResult]:
        return [r for r in self.action_results if r.success]

    @property
    def action_failed(self) -> list[ActionResult]:
        return [r for r in self.action_results if not r.success]

    @property
    def all_success(self) -> bool:
        """True if both CRUD and actions succeeded."""
        return self.success and len(self.action_failed) == 0

@dataclass
class ActionResult:
    """Result of an action operation execution."""
    action: ActionOperation
    success: bool
    error: Exception | None = None
```

**Why Separate List:**
- Semantic mismatch: Actions operate on task-target pairs, not single entities
- Type consistency: SaveError assumes AsanaResource, actions relate to relationships
- Backward compatible: Adding optional field with default empty list
- Clear attribution: Know exactly which actions succeeded/failed

### Direct Convenience Methods

Provide P1 (single-operation) methods on TasksClient:

```python
# Session-based (batch multiple operations)
async with SaveSession(client) as session:
    session.add_tag(task, tag_gid)
    session.add_follower(task, user_gid)
    result = await session.commit_async()

# Direct methods (single operation, raises on failure)
task = await client.tasks.add_tag_async(task_gid, tag_gid)
task = await client.tasks.add_follower_async(task_gid, user_gid)

# Instance methods (convenience)
await task.save_async()
```

**Direct Method Behavior:**
- Create SaveSession internally (single-operation scope)
- Raise SaveSessionError on failure
- Return modified entity on success
- Simple one-liner for common operations

## Rationale

### Why Not Extend OperationType?

Extending `OperationType` with `ADD_TAG`, `REMOVE_TAG`, etc. would:
1. **Blur Semantic Boundaries**: CRUD and actions have fundamentally different behaviors
2. **Complicate Batch Logic**: Need to differentiate batch-eligible vs non-batch in same enum
3. **Violate Single Responsibility**: `OperationType` maps to HTTP methods; actions break this
4. **Risk Cascading Changes**: Adding values could break existing match/switch statements

### Why extra_params Over TypedDict Per ActionType?

**Considered TypedDict approach:**
```python
class PositioningParams(TypedDict, total=False):
    insert_before: str
    insert_after: str

class CommentParams(TypedDict):
    text: str
    html_text: NotRequired[str]

# Would require:
extra_params: PositioningParams | CommentParams | dict[str, Any]
```

**Rejected because:**
- Proliferation of types (7+ TypedDicts needed)
- Complex union types in annotations
- Runtime validation already required (positioning conflicts)
- Low value: keys are fixed per action type, `to_api_call()` knows schema
- Frozen dataclass constraint: TypedDict adds ceremony

### Why Not Separate Fields?

**Considered explicit fields:**
```python
@dataclass(frozen=True)
class ActionOperation:
    insert_before: str | None = None
    insert_after: str | None = None
    text: str | None = None
    html_text: str | None = None
```

**Rejected because:**
- Field explosion (each new action type adds fields)
- Confusing API (most fields None for most actions)
- Validation scattered (each field needs None-check)
- Backward incompatible (adding fields changes constructor)

### Why Not Subclass Per ActionType?

**Considered class hierarchy:**
```python
@dataclass(frozen=True)
class AddToProjectOperation:
    task: AsanaResource
    project_gid: str
    insert_before: str | None = None

@dataclass(frozen=True)
class AddCommentOperation:
    task: AsanaResource
    text: str
    html_text: str | None = None
```

**Rejected because:**
- 11+ dataclasses needed (one per ActionType)
- Complex union types for collections
- isinstance() chains in ActionExecutor
- Contradicts unified ActionOperation design
- Over-engineering for essentially additional key-value data

### Why Separate Action Results?

**Considered merging into SaveError:**
```python
# Would require:
@dataclass
class SaveError:
    entity: AsanaResource | tuple[AsanaResource, AsanaResource]  # ???
```

**Rejected because:**
- Actions operate on task-target pairs (different structure than CRUD)
- Type consistency: SaveError assumes single AsanaResource
- Complexity: Would need union types and instanceof checks
- Clarity: Separate lists makes success/failure attribution clear

## Alternatives Considered

### Alternative 1: Generic "ACTION" OperationType

**Description**: Single `ACTION` operation type with `sub_type: str` field.

**Pros**: No new enum needed

**Cons**:
- Lose type safety (typos not caught at type-check time)
- Runtime validation required everywhere
- Less discoverable API (strings vs enum values)

**Why not chosen**: Type safety valuable for catching errors early.

### Alternative 2: Action Methods Return SaveResult

**Description**: Direct methods return SaveResult instead of raising exceptions.

**Pros**: Consistent with batch operations

**Cons**:
- Unnatural for single operations ("did this one thing work?")
- More boilerplate for simple cases
- Inconsistent with standard Python error handling

**Why not chosen**: Exception better UX for single-operation methods.

### Alternative 3: No Direct Methods (Session Only)

**Description**: Require SaveSession for all action operations.

**Pros**: Single API, no duplication

**Cons**:
- Poor UX for simple one-off operations
- Forces batch pattern even for single operation
- More boilerplate for common cases

**Why not chosen**: Convenience methods significantly improve UX.

### Alternative 4: Actions Use Batch API

**Description**: Try to batch action operations via Asana Batch API.

**Pros**: Potential performance improvement

**Cons**:
- Asana Batch API doesn't support action endpoints
- Would require workaround or API changes
- Not under our control

**Why not chosen**: Asana limitation, not technically possible.

## Consequences

### Positive

- **Clear Architecture**: CRUD and action operations have distinct code paths
- **Type Safety**: All action types enumerated and type-checkable
- **Backward Compatible**: No changes to existing `OperationType` handling
- **Flexible Parameters**: Unified type handles diverse parameter needs
- **Extensible**: Adding new action types straightforward
- **Testable**: Action operations tested independently of CRUD
- **Convenient**: Direct methods provide simple UX for common operations
- **Complete Results**: action_results provides full outcome information

### Negative

- **Two Type Systems**: Developers must understand both `OperationType` and `ActionType`
- **More Code**: Separate `ActionOperation` class and `ActionExecutor`
- **Preview Complexity**: `preview()` returns both CRUD and action operations
- **No Static Typing**: extra_params keys checked at runtime
- **Documentation Burden**: Must document valid keys per action type
- **Typo Risk**: Invalid extra_params keys silently ignored

### Neutral

- **Session API Extended**: SaveSession gains action methods
- **Pipeline Extended**: SavePipeline has action execution phase
- **Result Structure**: SaveResult includes both CRUD and action outcomes
- **P1 Methods**: Raise exceptions consistent with SDK pattern
- **Execution Order**: Actions always execute after CRUD (enforced)

## Compliance

### Enforcement

1. **Type Hints**: All action methods use `ActionType` type hints
2. **Code Review**: New action support must use `ActionType`, not strings
3. **Tests**: Unit tests verify distinct handling of `OperationType` vs `ActionType`
4. **Documentation**: TDD-0011 specifies separation of CRUD and action phases
5. **Extra Params**: Each action type documents valid keys in docstring

### Testing

**Unit Tests Verify:**
- ActionType enum values match API endpoints
- ActionOperation frozen dataclass immutability
- extra_params default_factory provides empty dict
- Optional target handling (None for likes)
- NameGid preservation in action operations
- Action results integrated into SaveResult
- Direct methods raise SaveSessionError on failure
- Session methods queue actions correctly

**Integration Tests Verify:**
- Action operations execute after CRUD
- Action failures don't affect CRUD successes
- Direct methods work end-to-end
- extra_params passed correctly to API

## Implementation Guidance

### Session-Based Action Operations

**Batch Multiple Actions:**
```python
async with SaveSession(client) as session:
    # Queue multiple actions
    session.add_tag(task, tag_gid)
    session.add_follower(task, user_gid)
    session.move_to_section(task, section_gid, insert_after=prev_gid)

    # Execute all together
    result = await session.commit_async()

    # Check action results
    if not result.all_success:
        for action_result in result.action_failed:
            print(f"Failed: {action_result.action.action} - {action_result.error}")
```

**With Positioning:**
```python
session.move_to_section(
    task,
    section_gid,
    insert_before=reference_task_gid
)
# OR
session.move_to_section(
    task,
    section_gid,
    insert_after=reference_task_gid
)
```

### Direct Convenience Methods

**Simple One-Liners:**
```python
# Add tag (raises on failure)
try:
    task = await client.tasks.add_tag_async(task_gid, tag_gid)
except SaveSessionError as e:
    print(f"Failed: {e}")

# Add follower
task = await client.tasks.add_follower_async(task_gid, user_gid)

# Add like (no target parameter)
task = await client.tasks.add_like_async(task_gid)
```

**Instance Methods:**
```python
# Save modified task
task.name = "Updated"
await task.save_async()  # Creates session internally
```

### Action Result Inspection

**Check All Results:**
```python
result = await session.commit_async()

# CRUD results
print(f"CRUD: {len(result.succeeded)} succeeded, {len(result.failed)} failed")

# Action results
print(f"Actions: {len(result.action_succeeded)} succeeded, "
      f"{len(result.action_failed)} failed")

# Overall status
if result.all_success:
    print("Everything succeeded!")
elif result.success:
    print("CRUD succeeded, but some actions failed")
else:
    print("Some operations failed")
```

### NameGid Usage

**With Name Preservation:**
```python
# NameGid captures both GID and name
tag = NameGid(gid="tag_123", name="Priority")
session.add_tag(task, tag)

# Enables matching on names in automation
if action.target.name == "Converted":
    # Handle state transition
```

## Cross-References

**Related ADRs:**
- ADR-0040: Unit of Work Pattern (provides track/commit foundation)
- ADR-0041: Dependency Ordering (actions execute after CRUD phase)
- ADR-0042: Error Handling (SaveResult structure, SaveSessionError)
- ADR-0045: Decomposition (ActionBuilder pattern for method generation)

**Related Documents:**
- PRD-0006: Action Operations requirements
- PRD-0007: Extended Actions (followers, likes, comments)
- TDD-0011: Action Operations technical design
- TDD-0012: Extended Actions technical design
