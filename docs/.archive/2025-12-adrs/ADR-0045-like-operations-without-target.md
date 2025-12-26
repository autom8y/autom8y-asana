# ADR-0045: Like Operations Without Target GID

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0007 (FR-LIK-001 through FR-LIK-009), TDD-0012, ADR-0042 (ActionType Enum)

## Context

The ActionOperation dataclass from ADR-0042 was designed with a required `related_entity_gid: str` field:

```python
@dataclass(frozen=True)
class ActionOperation:
    action_type: ActionType
    target_entity: AsanaResource
    related_entity_gid: str  # Required - always a GID string
```

This works for operations like:
- ADD_TAG: `related_entity_gid` = tag GID
- ADD_FOLLOWER: `related_entity_gid` = user GID
- ADD_DEPENDENCY: `related_entity_gid` = dependent task GID

However, Asana's like/unlike API endpoints do not accept a user parameter:

```
POST /tasks/{task_gid}/addLike
Body: { "data": {} }  # Empty - uses authenticated user from OAuth token

POST /tasks/{task_gid}/removeLike
Body: { "data": {} }  # Empty - uses authenticated user from OAuth token
```

The like operation implicitly uses the authenticated user. There is no `related_entity_gid` to specify.

### Forces at Play

1. **API reality**: Asana's like endpoint takes no user parameter
2. **Type consistency**: ActionOperation should have consistent field semantics
3. **Backward compatibility**: Existing code expects `related_entity_gid` on ActionOperation
4. **Simplicity**: Avoid complex workarounds for a straightforward requirement
5. **Type safety**: Prefer types that express the actual domain accurately

## Decision

Make `target_gid` (renamed from `related_entity_gid` for clarity) optional with `str | None = None`:

```python
@dataclass(frozen=True)
class ActionOperation:
    """A planned action operation requiring a dedicated API endpoint.

    Attributes:
        task: The task entity this action operates on.
        action: The type of action to perform.
        target_gid: The GID of the target entity (user, task, project, etc.).
                   None for like operations which use the authenticated user
                   implicitly per ADR-0045.
        extra_params: Additional parameters for the API call per ADR-0044.
    """
    task: AsanaResource
    action: ActionType
    target_gid: str | None = None  # Optional for likes
    extra_params: dict[str, Any] = field(default_factory=dict)
```

### Usage

```python
# Like operation - no target_gid needed
like_action = ActionOperation(
    task=task,
    action=ActionType.ADD_LIKE,
    target_gid=None,  # Explicit or omit (defaults to None)
)

# Follower operation - target_gid is the user
follower_action = ActionOperation(
    task=task,
    action=ActionType.ADD_FOLLOWER,
    target_gid=user_gid,  # Required for this action type
)
```

### to_api_call() Handling

```python
def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
    task_gid = self.task.gid if hasattr(self.task, 'gid') else str(self.task)

    match self.action:
        case ActionType.ADD_LIKE:
            # No target_gid used - authenticated user implicit
            return ("POST", f"/tasks/{task_gid}/addLike", {"data": {}})

        case ActionType.REMOVE_LIKE:
            # No target_gid used - authenticated user implicit
            return ("POST", f"/tasks/{task_gid}/removeLike", {"data": {}})

        case ActionType.ADD_FOLLOWER:
            # target_gid required - would fail if None
            return ("POST", f"/tasks/{task_gid}/addFollowers",
                    {"data": {"followers": [self.target_gid]}})
```

## Rationale

### Why Optional Over Required?

Making `target_gid` optional accurately models the domain:

1. **Like operations genuinely have no target**: The Asana API design proves this - no user parameter exists
2. **Type reflects reality**: `None` means "not applicable" which is semantically correct
3. **No dummy values**: Avoids misleading GID values that are never used
4. **Clear intent**: Callers explicitly pass `None` or omit the parameter for likes

### Why Not a Sentinel Value Like "__SELF__"?

A sentinel pattern:

```python
# Alternative: Use sentinel for "use authenticated user"
CURRENT_USER = "__SELF__"

like_action = ActionOperation(
    task=task,
    action=ActionType.ADD_LIKE,
    target_gid=CURRENT_USER,  # Sentinel value
)
```

Problems:

1. **False information**: `target_gid="__SELF__"` suggests a GID will be used; it won't
2. **Magic string**: Requires documentation explaining the sentinel
3. **Validation complexity**: Must check for sentinel in `to_api_call()`
4. **Type system abuse**: `str` type allows any string, not just valid GIDs or sentinel
5. **Confusing semantics**: Does `"__SELF__"` mean the OAuth user? The task creator? Ambiguous.

### Why Not Separate LikeOperation Class?

```python
@dataclass(frozen=True)
class LikeOperation:
    task: AsanaResource
    action: ActionType  # Only ADD_LIKE or REMOVE_LIKE

# No target_gid field at all
```

Problems:

1. **Type proliferation**: Contradicts ADR-0042's unified ActionOperation design
2. **Collection complexity**: `_pending_actions: list[ActionOperation | LikeOperation]`
3. **Dispatch complexity**: Two code paths in ActionExecutor
4. **Over-engineering**: Adding one field optionality is simpler than a new class

### Why Rename to target_gid?

The original name `related_entity_gid` was accurate but verbose. `target_gid` is:

1. **Shorter**: Easier to read in code
2. **Semantically clear**: The "target" of the action
3. **Consistent with Asana terminology**: Asana docs use "target" in action contexts
4. **Still accurate**: For followers, the target is the user; for tags, the target is the tag

## Alternatives Considered

### Alternative 1: Sentinel Value "__SELF__"

**Description**: Use a special string constant to indicate "use authenticated user".

**Pros**:
- Field remains required (non-nullable)
- Explicit marker for "self" operations
- Could extend to other "self" operations

**Cons**:
- Magic string requires documentation
- Type system doesn't distinguish sentinel from real GIDs
- Misleading - suggests a value is used when it isn't
- Must be filtered out in `to_api_call()`

**Why not chosen**: Introduces complexity for a simple case. `None` is the standard way to express "not applicable" in Python.

### Alternative 2: Separate LikeOperation Dataclass

**Description**: Create a dedicated dataclass for like operations without target_gid.

**Pros**:
- No optional fields
- Type system enforces no target for likes
- Clean separation

**Cons**:
- Two operation types to manage
- Union types in collections
- Violates ADR-0042's unified approach
- Disproportionate complexity for 2 action types

**Why not chosen**: Over-engineering. The difference between likes and other actions is one optional field, not a fundamental structural difference.

### Alternative 3: Dummy GID Value

**Description**: Pass any valid-looking GID that gets ignored.

```python
like_action = ActionOperation(
    task=task,
    action=ActionType.ADD_LIKE,
    target_gid="0",  # Ignored by API
)
```

**Pros**:
- Field remains required
- Simple implementation

**Cons**:
- Misleading - looks like a real GID
- Could be accidentally used in payload
- No semantic meaning
- Fails code review ("why is this 0?")

**Why not chosen**: Technically dishonest. The field should reflect actual usage, not contain placeholder garbage.

### Alternative 4: Two Separate Fields

**Description**: Add `like_user_source: Literal["authenticated"]` field for likes.

```python
@dataclass(frozen=True)
class ActionOperation:
    target_gid: str | None = None
    like_user_source: Literal["authenticated"] | None = None
```

**Pros**:
- Explicit about like behavior
- Self-documenting

**Cons**:
- Unnecessary field for one action type
- Clutters dataclass
- Over-specific solution

**Why not chosen**: The authenticated user behavior is a property of the Asana API for likes, not something we need to model explicitly. `None` for target_gid sufficiently expresses "no target needed".

## Consequences

### Positive

1. **Accurate domain model**: `None` correctly represents "no target needed"
2. **Simple implementation**: One optional field vs. new classes or magic strings
3. **Backward compatible**: Existing action types still work; they just provide target_gid
4. **Clear intent**: Code reads naturally: "add like to task (no target)"
5. **Type-safe for likes**: `target_gid=None` is the correct value, not a workaround

### Negative

1. **Runtime validation needed**: Actions requiring target_gid must check for None
2. **Documentation burden**: Must document when target_gid is required vs. optional
3. **Potential misuse**: Could create ADD_FOLLOWER with target_gid=None (caught at API call)

### Neutral

1. **SaveSession methods enforce correctness**: `add_follower()` always provides target_gid; `add_like()` never does
2. **to_api_call() validates implicitly**: Using None where a GID is needed would fail at API call time
3. **Test coverage catches errors**: Integration tests verify correct payloads

## Compliance

### Enforcement

- **SaveSession methods**: Each method constructs ActionOperation with correct target_gid presence
- **Unit tests**: Verify ADD_LIKE operations have target_gid=None
- **Unit tests**: Verify ADD_FOLLOWER operations have target_gid set
- **Integration tests**: Verify API calls succeed with correct payloads

### Documentation

- ActionOperation docstring explains when target_gid is None
- Each SaveSession method documents whether it sets target_gid
- TDD-0012 lists which ActionTypes require target_gid
