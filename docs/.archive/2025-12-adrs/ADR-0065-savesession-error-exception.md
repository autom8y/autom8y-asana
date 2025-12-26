# ADR-0065: SaveSessionError Exception for P1 Methods

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: Architect, Principal Engineer
- **Related**: TDD-TRIAGE-FIXES, ADR-0040 (Partial Failure Handling), ADR-0055 (Action Result Integration)

## Context

Issue 5 from the QA Adversarial Review identified that P1 convenience methods (`add_tag_async`, `remove_tag_async`, etc.) don't check `SaveResult.success` after calling `commit_async()`. Failed actions are silently lost, and the method returns a task as if the operation succeeded.

### Current Behavior (BUG)

```python
@error_handler
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        await session.commit_async()  # Result IGNORED

    return await self.get_async(task_gid)  # Returns task as if success
```

If `tag_gid` doesn't exist (422 error), the action fails but the caller receives a task with no indication of failure.

### Forces at Play

1. **User expectation**: Callers expect an exception if the operation fails
2. **Existing exception hierarchy**: `PartialSaveError` exists but is designed for batch CRUD failures
3. **Action failures are different**: Actions fail for different reasons than CRUD (invalid GID, permission denied, etc.)
4. **SaveResult accessibility**: Callers may want to inspect what failed, not just know it failed
5. **P1 simplicity**: These are "convenience" methods - should be simple to use

## Decision

**Create a new `SaveSessionError` exception** that wraps `SaveResult` and provides a descriptive error message. P1 methods will raise this exception when `result.success` is `False`.

```python
class SaveSessionError(SaveOrchestrationError):
    """Raised when a SaveSession commit fails in a convenience method.

    Per TDD-TRIAGE-FIXES: P1 methods must propagate failures to callers.

    Attributes:
        result: The SaveResult containing success/failure details.
    """

    def __init__(self, result: SaveResult) -> None:
        self.result = result

        # Build descriptive message
        failures: list[str] = []

        for err in result.failed:
            failures.append(f"CRUD {err.operation.value}: {err.error}")

        for action_result in result.action_results:
            if not action_result.success:
                failures.append(f"Action {action_result.action.action.value}: {action_result.error}")

        message = f"SaveSession commit failed. {len(failures)} failure(s): " + "; ".join(failures[:3])
        if len(failures) > 3:
            message += f" ... and {len(failures) - 3} more"

        super().__init__(message)
```

### Usage Pattern

```python
@error_handler
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    from autom8_asana.persistence.exceptions import SaveSessionError

    async with SaveSession(self._client) as session:
        task = await self.get_async(task_gid)
        session.add_tag(task, tag_gid)
        result = await session.commit_async()

        if not result.success:
            raise SaveSessionError(result)

    return task
```

### Caller Experience

```python
try:
    task = await client.tasks.add_tag_async(task_gid, invalid_tag_gid)
except SaveSessionError as e:
    print(f"Failed: {e}")  # Human-readable message
    print(f"Details: {e.result.action_results}")  # Inspect failures
```

## Rationale

### Why Not Reuse PartialSaveError?

`PartialSaveError` is designed for batch CRUD scenarios where "partial success" is meaningful (some entities saved, others failed). For P1 methods that perform a single operation:

1. **Semantics don't match**: "Partial save" implies some things succeeded - but P1 methods do one thing
2. **Different failure modes**: Action failures (422s) are different from CRUD failures
3. **Message clarity**: A dedicated exception can provide clearer, more specific messages

### Why Not Just Re-raise the Original Exception?

The original exception from the Asana API is captured in `ActionResult.error`, but:

1. It's wrapped inside `SaveResult`, not directly accessible
2. The context is lost (which operation failed, on which task)
3. Callers would need to know about `SaveResult` internals to debug

### Why Expose SaveResult on the Exception?

1. **Debugging**: Callers may want to inspect exactly what failed
2. **Retry logic**: Callers can see which actions failed and decide to retry
3. **Consistency**: Matches `PartialSaveError.result` pattern

## Alternatives Considered

### Alternative A: Use PartialSaveError for All Failures

**Description**: Reuse `PartialSaveError` for P1 method failures

**Pros**:
- No new exception class
- Existing handling code works

**Cons**:
- Semantic mismatch ("partial" for single operation)
- Message may confuse users

**Why not chosen**: Semantics are wrong for single-operation methods

### Alternative B: Raise APIError Directly

**Description**: Extract and re-raise the original `APIError` from action result

**Pros**:
- Users familiar with `APIError`
- No new exception type

**Cons**:
- Loses context (which P1 method, which action)
- Can't inspect full `SaveResult`
- Inconsistent with batch scenarios

**Why not chosen**: Loses valuable context information

### Alternative C: Return Tuple (Task, SaveResult)

**Description**: Return `(task, result)` tuple instead of raising

**Pros**:
- No exception for flow control
- Always returns result details

**Cons**:
- Breaking API change (return type)
- Every caller must unpack and check
- Easy to ignore result

**Why not chosen**: Breaks "convenience" purpose of P1 methods

### Alternative D: Add `raise_on_failure` Parameter

**Description**: `add_tag_async(task_gid, tag_gid, raise_on_failure=True)`

**Pros**:
- Backward compatible (default False)
- User controls behavior

**Cons**:
- Default silent failure is the bug we're fixing
- Extra parameter complexity

**Why not chosen**: Silent failure should not be default behavior

## Consequences

### Positive

1. **Failures surface**: Users will know when operations fail
2. **Debuggable**: Error message includes failure details
3. **Inspectable**: `SaveResult` accessible for programmatic handling
4. **Type-safe**: New exception class, clear in type hints
5. **Consistent**: Follows existing `SaveOrchestrationError` hierarchy

### Negative

1. **Breaking change**: Previously silent failures now raise
2. **New exception to learn**: Users must know about `SaveSessionError`
3. **Try/except required**: Users who want to ignore failures must explicitly catch

### Neutral

1. **Import location**: Available from `autom8_asana.persistence.exceptions`
2. **Sync wrapper behavior**: Exception propagates naturally through sync wrappers

## Implementation Notes

1. **Import inside methods**: To avoid circular imports, import `SaveSessionError` inside each P1 method body
2. **Export in __all__**: Add to `exceptions.py` `__all__` list
3. **Documentation**: Update P1 method docstrings to list `SaveSessionError` in Raises section

## Test Verification

1. `test_save_session_error_message_includes_failures`: Error message contains failure details
2. `test_save_session_error_result_accessible`: Can access `error.result`
3. `test_add_tag_invalid_gid_raises_save_session_error`: P1 method raises on failure
4. `test_sync_wrapper_propagates_exception`: Sync version also raises

## Compliance

### Enforcement

- **Unit tests**: Test exception message format and result accessibility
- **Type checking**: mypy validates exception hierarchy
- **Code review**: P1 methods must check `result.success`

### Documentation

- Add `SaveSessionError` to exceptions reference
- Update P1 method docstrings
- Add example in usage guide showing exception handling
