# ADR-0042: Separate ActionType Enum for Action Endpoint Operations

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0006, TDD-0010, TDD-0011, ADR-0035 (Unit of Work), ADR-0036 (Change Tracking)

## Context

PRD-0006 requires adding support for Asana action endpoints: `add_tag()`, `remove_tag()`, `add_to_project()`, `remove_from_project()`, `add_dependency()`, `remove_dependency()`, and `move_to_section()`. These operations differ fundamentally from standard CRUD operations in several ways:

1. **Different API pattern**: Action endpoints use `POST /tasks/{gid}/addTag` vs CRUD's `PUT /tasks/{gid}`
2. **Not batch-eligible**: Asana's Batch API only supports standard CRUD operations; action endpoints must execute individually
3. **Execution ordering**: Action operations must execute AFTER entity CRUD (entity must exist before actions can be applied)
4. **Semantic difference**: CRUD operations change entity state; action operations modify relationships between entities

The existing `OperationType` enum contains `CREATE`, `UPDATE`, `DELETE`. We need to decide how to model action operations in the system.

### Forces at Play

1. **Type safety**: We want compile-time/type-check-time guarantees about operation handling
2. **Separation of concerns**: CRUD and action operations have different execution paths
3. **Code clarity**: Engineers should understand that action operations behave differently
4. **Extension path**: Future action operations (followers, attachments) should integrate cleanly
5. **Backward compatibility**: Existing code using `OperationType` must continue working

## Decision

Create a separate `ActionType` enum and `ActionOperation` dataclass for action endpoint operations. Keep `OperationType` unchanged for CRUD operations.

```python
# New types in persistence/models.py

class ActionType(Enum):
    """Type of action operation requiring dedicated API endpoint.

    Per ADR-0042: Separate from OperationType because action operations
    have different execution characteristics (not batch-eligible,
    execute after CRUD, relationship-focused).
    """
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MOVE_TO_SECTION = "move_to_section"


@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation requiring a dedicated API endpoint.

    Per FR-ACTION-010: Action operations queued and executed on commit.
    Per FR-ACTION-011: Action operations execute after CRUD operations.

    Attributes:
        action_type: The type of action to perform
        target_entity: The primary entity (e.g., task for add_tag)
        related_entity_gid: The GID of the related entity (e.g., tag GID)
        extra_params: Additional parameters (e.g., section for add_to_project)
    """
    action_type: ActionType
    target_entity: AsanaResource
    related_entity_gid: str
    extra_params: dict[str, Any] = field(default_factory=dict)
```

## Rationale

### Why Not Extend OperationType?

Extending `OperationType` with `ADD_TAG`, `REMOVE_TAG`, etc. would:

1. **Blur semantic boundaries**: CRUD operations and action operations have fundamentally different behaviors. Mixing them in one enum suggests they can be handled uniformly, which is false.

2. **Complicate batch execution logic**: The `BatchExecutor` would need to differentiate between batch-eligible and non-batch operations within the same enum. This adds conditional logic throughout.

3. **Violate single responsibility**: `OperationType` currently maps cleanly to HTTP methods (CREATE->POST, UPDATE->PUT, DELETE->DELETE). Action types break this pattern.

4. **Risk cascading changes**: Adding values to `OperationType` could break existing match/switch statements that assume only 3 values.

### Why Not a Generic "ACTION" Type with Sub-type Field?

A single `ACTION` operation type with a `sub_type` field would:

1. **Lose type safety**: Typos in string sub-types wouldn't be caught at type-check time
2. **Require runtime validation**: Every handler would need to validate sub-type values
3. **Obscure the API surface**: Less discoverable than explicit enum values

### Benefits of Separate ActionType

1. **Clear semantic separation**: CRUD operations vs action operations are distinct concepts with distinct types
2. **Independent execution paths**: `SavePipeline` can handle CRUD via `BatchExecutor` and actions via a new `ActionExecutor`
3. **Type-safe dispatch**: Pattern matching on `ActionType` catches missing cases at type-check time
4. **Clean extension**: Adding new action types only affects action-related code
5. **Backward compatible**: No changes to existing `OperationType` handling

## Alternatives Considered

### Alternative 1: Extend OperationType Enum

**Description**: Add `ADD_TAG`, `REMOVE_TAG`, etc. directly to `OperationType`

**Pros**:
- Single enum for all operations
- Simpler `PlannedOperation` type

**Cons**:
- Semantic confusion (mixes entity state changes with relationship changes)
- Complicates batch vs non-batch logic
- Breaks the clean HTTP method mapping
- Risk of breaking existing code

**Why not chosen**: The semantic difference between CRUD and action operations is significant enough to warrant separate types. Mixing them creates confusion and technical debt.

### Alternative 2: Subclass PlannedOperation

**Description**: Create `ActionPlannedOperation(PlannedOperation)` subclass

**Pros**:
- Leverages inheritance for shared behavior
- Single collection can hold both types

**Cons**:
- Inheritance hierarchy for what is essentially different data
- Requires isinstance() checks throughout
- Less explicit about the difference

**Why not chosen**: Composition (separate types) is clearer than inheritance here. The types share no meaningful behavior.

### Alternative 3: Use String Action Names

**Description**: `ActionOperation(action_name: str, ...)`

**Pros**:
- Flexible, no enum updates needed
- Simple data structure

**Cons**:
- No type safety
- Typo-prone
- No IDE autocomplete
- Runtime validation required

**Why not chosen**: Type safety is valuable for catching errors early. The action set is well-defined and stable.

## Consequences

### Positive

1. **Clear architecture**: CRUD and action operations have distinct code paths
2. **Type safety**: All action types are enumerated and type-checkable
3. **Backward compatible**: No changes to existing `OperationType` handling
4. **Testable**: Action operations can be tested independently of CRUD operations
5. **Extensible**: Adding new action types (followers, attachments) is straightforward

### Negative

1. **Two type systems**: Developers must understand both `OperationType` and `ActionType`
2. **More code**: Separate `ActionOperation` class and `ActionExecutor`
3. **Preview complexity**: `preview()` must return both `PlannedOperation` and `ActionOperation` items

### Neutral

1. **SaveSession API adds methods**: `add_tag()`, `remove_tag()`, etc. on session (per PRD-0006)
2. **Pipeline extended**: `SavePipeline` gains action execution phase
3. **SaveResult unchanged**: Both CRUD successes and action successes go in `succeeded`

## Compliance

### Enforcement

- **Type hints**: All action methods use `ActionType` type hints
- **Code review**: New action support must use `ActionType`, not string identifiers
- **Tests**: Unit tests verify distinct handling of `OperationType` vs `ActionType`

### Documentation

- TDD-0011 specifies the separation of CRUD and action execution phases
- Docstrings explain when to use `OperationType` vs `ActionType`
