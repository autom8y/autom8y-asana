# ADR-0044: extra_params Field Design for ActionOperation

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0007, TDD-0012, ADR-0042 (ActionType Enum)

## Context

PRD-0007 (SDK Functional Parity) requires extending ActionOperation to support additional parameters beyond the basic `task` and `target_gid`:

1. **Positioning parameters**: `insert_before` and `insert_after` for `add_to_project()` and `move_to_section()`
2. **Comment text**: `text` and `html_text` for `add_comment()`
3. **Future extensibility**: Other action endpoints may require additional parameters (e.g., `is_milestone` for projects)

The current `ActionOperation` dataclass has fixed fields:
```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None
```

We need a way to pass additional parameters to action endpoints without creating action-specific dataclasses or breaking the frozen dataclass pattern.

### Forces at Play

1. **Simplicity**: Single dataclass for all action types
2. **Type safety**: Catch invalid parameters at compile time when possible
3. **Extensibility**: Support future action types without schema changes
4. **Immutability**: Preserve frozen dataclass pattern (hashable, safe for sets)
5. **API ergonomics**: Natural parameter passing in SaveSession methods

## Decision

Add an `extra_params: dict[str, Any]` field to `ActionOperation` with `field(default_factory=dict)`:

```python
@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation requiring a dedicated API endpoint.

    Per ADR-0042: Action operations are separate from CRUD operations.
    Per ADR-0044: extra_params provides extensible parameter storage.
    """
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)
```

### Usage Examples

```python
# Positioning in add_to_project
session.add_to_project(task, project, insert_after=other_task)
# Creates: ActionOperation(
#     task=task,
#     action=ActionType.ADD_TO_PROJECT,
#     target_gid=project.gid,
#     extra_params={"insert_after": other_task.gid}
# )

# Comment with text
session.add_comment(task, "Hello", html_text="<p>Hello</p>")
# Creates: ActionOperation(
#     task=task,
#     action=ActionType.ADD_COMMENT,
#     target_gid=task.gid,
#     extra_params={"text": "Hello", "html_text": "<p>Hello</p>"}
# )

# No extra params (backward compatible)
session.add_tag(task, tag)
# Creates: ActionOperation(
#     task=task,
#     action=ActionType.ADD_TAG,
#     target_gid=tag.gid,
#     extra_params={}  # Empty dict
# )
```

### API Call Construction

The `to_api_call()` method merges extra_params into the payload:

```python
def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
    """Convert to (method, path, payload) tuple."""
    base_payload = {"data": {}}

    # Add target_gid if present
    if self.target_gid:
        base_payload["data"]["tag"] = self.target_gid  # or project, etc.

    # Merge extra_params
    base_payload["data"].update(self.extra_params)

    return ("POST", f"/tasks/{self.task.gid}/addTag", base_payload)
```

## Rationale

### Why dict[str, Any]?

1. **Universal container**: Can hold any JSON-serializable value
2. **No schema changes**: Adding new action types doesn't require modifying ActionOperation
3. **JSON-compatible**: Directly maps to API request payloads
4. **Python idiom**: Dictionary for kwargs-style parameters is idiomatic

### Why default_factory=dict?

1. **Frozen dataclass compatibility**: Mutable default `{}` is illegal for frozen classes
2. **New instance each time**: Each ActionOperation gets its own dict (no shared state)
3. **Hashable**: ActionOperation remains hashable (dict field is not part of hash/equality)

Actually, wait - frozen dataclasses with mutable fields are problematic. Let me reconsider...

**Correction**: Since `ActionOperation` is frozen, we need to ensure hashability. The dict itself is not part of the hash, but it's included in the dataclass. Let's verify this works:

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ActionOperation:
    action: str
    extra_params: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)
```

With `hash=False` and `compare=False`, the dict doesn't affect equality or hashing, preserving hashability while allowing per-instance state.

### Why Not Action-Specific Fields?

```python
@dataclass(frozen=True)
class ActionOperation:
    insert_before: str | None = None
    insert_after: str | None = None
    text: str | None = None
    html_text: str | None = None
```

**Problems**:
- Every action type adds more fields
- Most fields None for most operations
- No clear boundary (when to stop adding fields?)
- Pollutes the ActionOperation API surface

### Why Not Subclassing?

```python
class PositioningActionOperation(ActionOperation):
    insert_before: str | None
    insert_after: str | None

class CommentActionOperation(ActionOperation):
    text: str
    html_text: str | None
```

**Problems**:
- SaveSession must hold `list[ActionOperation | PositioningActionOperation | ...]`
- Type narrowing required throughout the codebase
- Violates Liskov Substitution Principle (different constructors)
- Adds complexity for marginal type safety gains

### Why extra_params Is Better

1. **Single type**: All action operations use same dataclass
2. **Pay-as-you-go**: Empty dict when no extra params needed
3. **Self-documenting**: SaveSession method signatures show required params
4. **Flexible**: New action types don't require code changes

## Alternatives Considered

### Alternative 1: Typed Params Classes

**Description**: Define typed parameter classes per action type
```python
@dataclass
class PositioningParams:
    insert_before: str | None = None
    insert_after: str | None = None

@dataclass(frozen=True)
class ActionOperation:
    params: PositioningParams | CommentParams | None = None
```

**Pros**:
- Type safety for parameters
- IDE autocomplete for param fields
- Validation at construction time

**Cons**:
- Requires union type that grows with each action
- Type narrowing needed to access fields
- Over-engineering for simple key-value pairs
- Still needs isinstance() checks

**Why not chosen**: The added type safety doesn't justify the complexity. SaveSession methods already provide typed interfaces (e.g., `insert_before: str | None`).

### Alternative 2: **kwargs Pattern

**Description**: Use **kwargs in ActionOperation constructor
```python
@dataclass(frozen=True)
class ActionOperation:
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)

    def __init__(self, task, action, target_gid=None, **kwargs):
        ...
```

**Pros**:
- Natural Python idiom for variable params
- Clear in method signatures

**Cons**:
- Frozen dataclasses don't support custom __init__ easily
- Loses frozen semantics
- **kwargs in constructor can hide typos

**Why not chosen**: Frozen dataclasses and **kwargs don't mix well. Explicit `extra_params={}` is clearer.

### Alternative 3: JSON String Field

**Description**: Store params as JSON string
```python
extra_params_json: str = ""
```

**Pros**:
- Immutable string is frozen-friendly
- No dict mutability concerns

**Cons**:
- Requires serialization/deserialization
- Not Python-idiomatic
- Error-prone (invalid JSON)
- Terrible debugging experience

**Why not chosen**: dict[str, Any] is the correct type for this use case.

### Alternative 4: Tuple of Tuples

**Description**: Immutable params storage
```python
extra_params: tuple[tuple[str, Any], ...] = ()
```

**Pros**:
- Fully immutable
- Hashable

**Cons**:
- Awkward to work with
- Must convert to dict for API calls anyway
- Not JSON-compatible
- Terrible ergonomics

**Why not chosen**: dict is the right abstraction; hashability concerns addressed with `hash=False`.

## Consequences

### Positive

1. **Single dataclass**: No proliferation of action-specific types
2. **Extensible**: New action types add params without schema changes
3. **Clean SaveSession API**: Method signatures define typed params
4. **Simple implementation**: Merge extra_params into API payload
5. **Frozen semantics preserved**: With `hash=False, compare=False` on dict field

### Negative

1. **Runtime validation**: Invalid param keys not caught at compile time
2. **No autocomplete**: extra_params contents not discoverable in IDE
3. **Documentation burden**: Must document which params each action type uses

### Neutral

1. **Type hints in methods**: SaveSession methods have typed signatures (e.g., `insert_before: str | None`)
2. **API call construction**: `to_api_call()` responsible for merging params correctly
3. **Empty by default**: Most action operations have `extra_params={}`

## Compliance

### Enforcement

1. **Field definition**: `extra_params: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)`
2. **SaveSession methods**: Pass extra params explicitly (no **kwargs)
3. **to_api_call()**: Merge extra_params into payload with validation
4. **Tests**: Verify extra_params correctly sent in API calls

### Documentation

- TDD-0012 specifies extra_params usage for each ActionType
- Docstrings explain which extra_params each action type supports
- Type hints in SaveSession methods define parameter types
