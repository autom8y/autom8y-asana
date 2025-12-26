# ADR-0047: Positioning Validation Timing

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0007 (FR-POS-003), TDD-0012, ADR-0044 (extra_params Field)

## Context

PRD-0007 FR-POS-003 requires:

> SDK shall raise `PositioningConflictError` when both `insert_before` and `insert_after` are specified.

The `add_to_project()` and `move_to_section()` methods accept optional positioning parameters:

```python
def add_to_project(
    self,
    task: Task | str,
    project: Project | NameGid | str,
    *,
    insert_before: Task | NameGid | str | None = None,
    insert_after: Task | NameGid | str | None = None,
) -> SaveSession:
    ...
```

Asana's API treats these parameters as mutually exclusive - specifying both results in an error. The question is: when should the SDK validate this constraint?

### Timing Options

1. **Queue time**: When `add_to_project()` is called
2. **Commit time**: When `commit()` is called
3. **API call time**: When `to_api_call()` generates the payload
4. **Let API reject**: Don't validate; let Asana API return error

### Forces at Play

1. **Developer experience**: Earlier errors are easier to debug
2. **Fail-fast principle**: Invalid operations should fail immediately
3. **Separation of concerns**: Where should validation logic live?
4. **Error attribution**: Stack trace should point to the mistake
5. **Consistency**: All positioning methods should validate the same way
6. **Performance**: Validation adds minimal overhead; timing doesn't affect performance meaningfully

## Decision

Validate positioning conflicts at queue time (when `add_to_project()` or `move_to_section()` is called). Raise `PositioningConflictError` immediately if both `insert_before` and `insert_after` are specified.

```python
class PositioningConflictError(SaveOrchestrationError):
    """Raised when both insert_before and insert_after are specified.

    Per ADR-0047: Validation happens at queue time for immediate feedback.

    Attributes:
        insert_before: The insert_before value that was provided.
        insert_after: The insert_after value that was provided.
    """

    def __init__(
        self,
        insert_before: str,
        insert_after: str,
    ) -> None:
        self.insert_before = insert_before
        self.insert_after = insert_after
        super().__init__(
            "Cannot specify both insert_before and insert_after. "
            f"Got insert_before={insert_before}, insert_after={insert_after}"
        )
```

### Implementation in SaveSession

```python
def add_to_project(
    self,
    task: Task | str,
    project: Project | NameGid | str,
    *,
    insert_before: Task | NameGid | str | None = None,
    insert_after: Task | NameGid | str | None = None,
) -> SaveSession:
    """Add a task to a project with optional positioning."""
    self._ensure_open()

    # Fail-fast: Validate positioning conflict immediately
    if insert_before is not None and insert_after is not None:
        before_gid = insert_before if isinstance(insert_before, str) else insert_before.gid
        after_gid = insert_after if isinstance(insert_after, str) else insert_after.gid
        raise PositioningConflictError(before_gid, after_gid)

    # ... rest of method creates ActionOperation with extra_params
```

### Error Message Design

The error message includes both values for debugging:

```
PositioningConflictError: Cannot specify both insert_before and insert_after.
Got insert_before=12345, insert_after=67890
```

This tells the developer:
1. What's wrong (mutually exclusive parameters)
2. What values were provided (for debugging)
3. Where the error occurred (queue time, stack trace points to add_to_project call)

## Rationale

### Why Queue Time Over Commit Time?

Commit time validation:

```python
def commit(self):
    # Validate all pending actions
    for action in self._pending_actions:
        if action.action == ActionType.ADD_TO_PROJECT:
            if action.extra_params.get("insert_before") and action.extra_params.get("insert_after"):
                raise PositioningConflictError(...)
    # ... execute
```

Problems:

1. **Delayed feedback**: Developer doesn't see error until commit(), possibly much later
2. **Lost context**: Stack trace shows commit(), not the add_to_project() call that had the error
3. **Wasted work**: Other operations may have been queued between the bad call and commit
4. **Debugging difficulty**: Which add_to_project() call had the conflict?

### Why Queue Time Over to_api_call() Time?

Validation in to_api_call():

```python
def to_api_call(self) -> tuple[str, str, dict[str, Any]]:
    if self.extra_params.get("insert_before") and self.extra_params.get("insert_after"):
        raise PositioningConflictError(...)
    # ... generate payload
```

Problems:

1. **Even later feedback**: Happens during commit execution phase
2. **Wrong responsibility**: to_api_call() generates payloads, not validates input
3. **Same issues as commit time**: Lost context, delayed feedback

### Why Not Let API Reject?

Letting Asana API return the error:

```
400 Bad Request: Cannot specify both insert_before and insert_after
```

Problems:

1. **Network round-trip wasted**: Made an API call we knew would fail
2. **Generic error**: Asana's error message may be less helpful than ours
3. **Rate limit impact**: Failed call still counts against rate limits
4. **Inconsistent UX**: Some errors from SDK, some from API

### Benefits of Queue Time Validation

1. **Immediate feedback**: Error raised exactly where the mistake was made
2. **Clear stack trace**: Points directly to the problematic add_to_project() call
3. **No wasted operations**: Invalid action never enters the queue
4. **Consistent pattern**: Matches comment validation (ADR-0046 validates empty comments at queue time)
5. **Better developer experience**: "Fix your code now" vs. "fix it and re-run commit"

### Consistency with Other Validations

| Validation | When | Rationale |
|------------|------|-----------|
| Session closed | Queue time | Can't queue to closed session |
| Empty comment | Queue time | Invalid data should fail immediately |
| Positioning conflict | Queue time | Invalid parameters should fail immediately |
| Invalid GID format | API call time | May not know format is invalid until API rejects |

Queue time is appropriate for validations we can perform with local information.

## Alternatives Considered

### Alternative 1: Validate at Commit Time

**Description**: Check all pending actions for positioning conflicts when commit() is called.

**Pros**:
- Centralized validation in one place
- Can validate all operations together
- Consistent timing for all validations

**Cons**:
- Delayed feedback
- Lost call site context
- Debugging harder
- Wasted queuing of invalid operations

**Why not chosen**: Violates fail-fast principle. Developers get better feedback when errors are raised at the source.

### Alternative 2: Validate in to_api_call()

**Description**: Check for positioning conflicts when generating the API payload.

**Pros**:
- Validation close to usage
- Single point of validation

**Cons**:
- Even later than commit time
- Wrong responsibility for to_api_call()
- Poorest developer experience

**Why not chosen**: to_api_call() should generate payloads, not validate business rules. The error would surface at the worst possible time.

### Alternative 3: Let Asana API Reject

**Description**: Don't validate; send both parameters and let Asana return an error.

**Pros**:
- No SDK validation code needed
- Asana's error message is authoritative
- Always matches API behavior

**Cons**:
- Wasted network round-trip
- Rate limit impact
- Less helpful error message
- Inconsistent error experience

**Why not chosen**: This is a preventable error. The SDK should catch it before wasting API resources.

### Alternative 4: Override with Priority

**Description**: If both specified, use one (e.g., insert_before takes priority).

```python
if insert_before and insert_after:
    insert_after = None  # insert_before wins
```

**Pros**:
- No error, operation proceeds
- Deterministic behavior

**Cons**:
- Silent data loss (insert_after ignored)
- Confusing: developer passed both, only one used
- Hides developer mistake
- No indication anything was wrong

**Why not chosen**: Silent override is worse than explicit error. Developers should know their code has a logic error.

### Alternative 5: Validate at ActionOperation Construction

**Description**: Validate in ActionOperation.__post_init__():

```python
@dataclass(frozen=True)
class ActionOperation:
    def __post_init__(self):
        if self.extra_params.get("insert_before") and self.extra_params.get("insert_after"):
            raise PositioningConflictError(...)
```

**Pros**:
- Validation in the data class itself
- Can't create invalid ActionOperation

**Cons**:
- ActionOperation is generic; doesn't know all validation rules for all action types
- Would need to validate other action-specific rules too
- Couples ActionOperation to business logic

**Why not chosen**: Validation belongs in SaveSession methods which have the semantic knowledge of each operation. ActionOperation is a data carrier.

## Consequences

### Positive

1. **Fail-fast**: Invalid operations rejected immediately
2. **Clear error attribution**: Stack trace points to add_to_project()/move_to_section() call
3. **No wasted work**: Invalid action never enters queue or triggers API call
4. **Consistent with other validations**: Session closed, empty comment also validate at queue time
5. **Better DX**: Developers see and fix errors during development, not at runtime

### Negative

1. **Validation logic in SaveSession**: Methods have validation code, not just queuing
2. **Duplicate validation**: Both add_to_project() and move_to_section() validate (acceptable DRY violation for clarity)

### Neutral

1. **New exception class**: PositioningConflictError added to persistence/exceptions.py
2. **Error includes both values**: Debugging information in exception attributes
3. **GID extraction at validation time**: Must convert Task/NameGid to GID for error message

## Compliance

### Enforcement

- **SaveSession methods**: add_to_project() and move_to_section() validate immediately
- **Unit tests**: Verify PositioningConflictError raised when both params specified
- **Unit tests**: Verify correct error message content
- **Unit tests**: Verify no ActionOperation created when validation fails

### Documentation

- SaveSession method docstrings document the PositioningConflictError raise condition
- Exception class docstring explains when it's raised
- TDD-0012 specifies fail-fast validation behavior
