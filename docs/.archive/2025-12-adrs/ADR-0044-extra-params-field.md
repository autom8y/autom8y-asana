# ADR-0044: extra_params Field Design for ActionOperation

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0007, TDD-0012, ADR-0042 (ActionType Enum), ADR-0046 (Comment Text Storage), ADR-0047 (Positioning Validation)

## Context

TDD-0012 extends the ActionOperation dataclass to support positioning parameters (`insert_before`, `insert_after`) and comment text storage. The existing ActionOperation structure from ADR-0042 has:

```python
@dataclass(frozen=True)
class ActionOperation:
    action_type: ActionType
    target_entity: AsanaResource
    related_entity_gid: str
    # No mechanism for additional parameters
```

Different action types require different additional parameters:

| ActionType | Additional Parameters Needed |
|------------|------------------------------|
| ADD_TO_PROJECT | `insert_before`, `insert_after` (mutually exclusive) |
| MOVE_TO_SECTION | `insert_before`, `insert_after` (mutually exclusive) |
| ADD_COMMENT | `text`, `html_text` |
| ADD_TAG, REMOVE_TAG | None |
| ADD_FOLLOWER, REMOVE_FOLLOWER | None |
| ADD_LIKE, REMOVE_LIKE | None |

### Forces at Play

1. **Flexibility**: Different action types need different parameters without proliferating types
2. **Type safety**: Would prefer compile-time safety, but runtime flexibility may be necessary
3. **Frozen dataclass**: ActionOperation is immutable; mutable defaults are forbidden
4. **API payload generation**: `to_api_call()` must access these parameters to build requests
5. **Simplicity**: Avoid creating separate dataclass per ActionType
6. **Consistency**: Same pattern should work for positioning and comment storage

## Decision

Add an `extra_params: dict[str, Any]` field to ActionOperation using `field(default_factory=dict)` for frozen dataclass compatibility.

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation requiring a dedicated API endpoint.

    Per ADR-0042: Separate from PlannedOperation (CRUD) because action
    operations have different execution characteristics.
    Per ADR-0044: extra_params stores action-specific parameters.

    Attributes:
        task: The task entity this action operates on.
        action: The type of action (ADD_FOLLOWER, ADD_LIKE, etc.).
        target_gid: The GID of the target entity (user, task, project, etc.).
                   Optional for like operations per ADR-0045.
        extra_params: Additional parameters for the API call. Used for:
                     - Positioning: {"insert_before": "gid"} or {"insert_after": "gid"}
                     - Comments: {"text": "...", "html_text": "..."}
    """
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)
```

### Usage in to_api_call()

```python
def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
    match self.action:
        case ActionType.ADD_TO_PROJECT:
            payload: dict[str, Any] = {"data": {"project": self.target_gid}}
            if self.extra_params.get("insert_before"):
                payload["data"]["insert_before"] = self.extra_params["insert_before"]
            if self.extra_params.get("insert_after"):
                payload["data"]["insert_after"] = self.extra_params["insert_after"]
            return ("POST", f"/tasks/{task_gid}/addProject", payload)

        case ActionType.ADD_COMMENT:
            comment_data: dict[str, Any] = {"text": self.extra_params.get("text", "")}
            if self.extra_params.get("html_text"):
                comment_data["html_text"] = self.extra_params["html_text"]
            return ("POST", f"/tasks/{task_gid}/stories", {"data": comment_data})
```

## Rationale

### Why dict[str, Any] Over TypedDict Per ActionType?

TypedDicts would provide static type checking:

```python
class PositioningParams(TypedDict, total=False):
    insert_before: str
    insert_after: str

class CommentParams(TypedDict):
    text: str
    html_text: NotRequired[str]
```

However:

1. **Proliferation of types**: Each ActionType with extra params needs its own TypedDict
2. **Union complexity**: `extra_params: PositioningParams | CommentParams | dict[str, Any]`
3. **Runtime validation already required**: We validate positioning conflicts at queue time per ADR-0047
4. **Low value**: The keys are fixed per action type; `to_api_call()` knows which keys to expect
5. **Frozen dataclass constraint**: Default factory must be simple; TypedDict adds ceremony

### Why field(default_factory=dict)?

Frozen dataclasses cannot have mutable default values:

```python
# WRONG - raises ValueError: mutable default for field extra_params
@dataclass(frozen=True)
class ActionOperation:
    extra_params: dict[str, Any] = {}

# CORRECT - new dict created per instance
@dataclass(frozen=True)
class ActionOperation:
    extra_params: dict[str, Any] = field(default_factory=dict)
```

### Why Not Separate Fields?

Adding `insert_before`, `insert_after`, `text`, `html_text` as optional fields:

```python
@dataclass(frozen=True)
class ActionOperation:
    insert_before: str | None = None
    insert_after: str | None = None
    text: str | None = None
    html_text: str | None = None
```

Problems:
1. **Field explosion**: Each new action type with params adds fields
2. **Confusing API**: Most fields are None for most action types
3. **Validation scattered**: Each field needs None-check in `to_api_call()`
4. **Backwards incompatible**: Adding fields changes constructor signature

### Why Not Separate Dataclass Per ActionType?

```python
@dataclass(frozen=True)
class AddToProjectOperation:
    task: AsanaResource
    project_gid: str
    insert_before: str | None = None
    insert_after: str | None = None

@dataclass(frozen=True)
class AddCommentOperation:
    task: AsanaResource
    text: str
    html_text: str | None = None
```

Problems:
1. **14 dataclasses**: One per ActionType (and growing)
2. **Collection complexity**: `_pending_actions: list[ActionOperation | AddToProjectOperation | ...]`
3. **Dispatch complexity**: `isinstance()` chains in ActionExecutor
4. **Inconsistent with ADR-0042**: ActionOperation was designed as unified type

## Alternatives Considered

### Alternative 1: TypedDict Per ActionType

**Description**: Define TypedDict for each action type's extra parameters.

**Pros**:
- Static type checking for parameter names
- IDE autocomplete for known keys
- Self-documenting parameter structure

**Cons**:
- Type proliferation (7+ TypedDicts needed)
- Complex union types in extra_params annotation
- Still needs runtime validation for mutual exclusion
- Ceremony outweighs benefit for simple key-value pairs

**Why not chosen**: The type safety benefit is marginal. We already validate at queue time, and `to_api_call()` has explicit knowledge of which keys each action type uses.

### Alternative 2: Separate Optional Fields

**Description**: Add `insert_before`, `insert_after`, `text`, `html_text` as optional fields on ActionOperation.

**Pros**:
- Explicit field names visible in type hints
- IDE shows all possible fields
- No runtime key lookups

**Cons**:
- Most fields are None for most operations
- Constructor grows with each new action type
- Breaking change when adding fields
- Cluttered dataclass definition

**Why not chosen**: Creates a "god object" where most fields are irrelevant to most instances. The extra_params pattern keeps action-specific concerns isolated.

### Alternative 3: Subclass Per ActionType

**Description**: Create ActionOperation subclasses with specific fields.

**Pros**:
- Strong typing per action type
- No irrelevant fields per class
- Clean separation of concerns

**Cons**:
- 14+ classes to maintain
- Complex union types for collections
- `isinstance()` dispatch throughout
- Contradicts ADR-0042's unified ActionOperation design

**Why not chosen**: Over-engineering for what is essentially additional key-value data. The execution path is the same regardless of action type; only the payload differs.

### Alternative 4: JSON String Field

**Description**: `extra_params: str` storing JSON.

**Pros**:
- Truly immutable (strings are immutable)
- No default_factory needed

**Cons**:
- Serialization/deserialization overhead
- No type hints for contents
- Error-prone string manipulation
- Unusual pattern for dataclasses

**Why not chosen**: Unnecessary complexity. `field(default_factory=dict)` solves the mutability concern cleanly.

## Consequences

### Positive

1. **Single unified type**: ActionOperation handles all action types without subclassing
2. **Extensible**: New action types with new parameters need no structural changes
3. **Frozen-safe**: `default_factory=dict` provides correct immutability semantics
4. **Simple API**: Consumers pass a dict; framework extracts known keys
5. **Consistent pattern**: Same approach for positioning and comments (see ADR-0046)

### Negative

1. **No static type checking**: Parameter names are strings checked at runtime
2. **Documentation burden**: Must document valid keys per action type
3. **Typo risk**: `{"insert_befroe": "gid"}` silently ignored (mitigated by tests)
4. **IDE limitations**: No autocomplete for extra_params keys

### Neutral

1. **to_api_call() knows the schema**: Each case in the match statement documents expected keys
2. **Validation at queue time**: Per ADR-0047, positioning conflicts detected immediately
3. **Empty dict is valid**: Actions without extra params work with default

## Compliance

### Enforcement

- **Code review**: New action types must document their extra_params keys in docstring
- **Unit tests**: Each action type has tests verifying correct extra_params handling
- **Type hints**: `dict[str, Any]` annotation required; no bare `dict`

### Documentation

- TDD-0012 specifies which keys each action type uses
- ActionOperation docstring lists known extra_params patterns
- Each SaveSession method documents what it stores in extra_params
