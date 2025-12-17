# ADR-0066: Selective Action Clearing Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: Architect, Principal Engineer
- **Related**: TDD-TRIAGE-FIXES, ADR-0055 (Action Result Integration), ADR-0042 (Action Operation Types)

## Context

Issue 10 from the QA Adversarial Review identified that `_pending_actions.clear()` in `commit_async()` runs unconditionally at line 555, regardless of whether any actions failed. This means:

1. Failed actions are discarded and cannot be retried
2. Users cannot inspect which actions failed after commit
3. `get_pending_actions()` returns empty list even after failures

### Current Behavior (BUG)

```python
async def commit_async(self) -> SaveResult:
    # ...
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # BUG: Clears ALL actions, even failed ones
    self._pending_actions.clear()

    return crud_result
```

### Desired Behavior

After commit:
- **All succeeded**: `_pending_actions` is empty (no retry needed)
- **All failed**: `_pending_actions` unchanged (all can be retried)
- **Partial success**: Only failed actions remain (selective retry)

### Forces at Play

1. **Retry capability**: Users should be able to fix issues and retry failed actions
2. **Memory management**: Don't accumulate unbounded operations
3. **Identity matching**: Need to match `ActionResult` back to `ActionOperation`
4. **Edge cases**: Duplicate operations, operations on same task

## Decision

**Implement selective clearing based on action identity matching.** An action is uniquely identified by the tuple `(task.gid, action_type, target_gid)`. After execution, only actions whose identity appears in a successful `ActionResult` are removed from `_pending_actions`.

### Action Identity Model

```python
# Unique identity of an action
ActionIdentity = tuple[str, ActionType, str | None]
# (task.gid, action_type, target_gid)

# Examples:
# Add tag to task: ("task_123", ActionType.ADD_TAG, "tag_456")
# Remove tag:      ("task_123", ActionType.REMOVE_TAG, "tag_456")
# Like task:       ("task_123", ActionType.ADD_LIKE, None)
# Add to project:  ("task_123", ActionType.ADD_TO_PROJECT, "proj_789")
```

### Implementation

```python
def _clear_successful_actions(self, action_results: list[ActionResult]) -> None:
    """Remove only successful actions from pending list.

    Args:
        action_results: Results from action execution.
    """
    if not action_results:
        self._pending_actions.clear()
        return

    # Build set of successful action identities
    successful_identities: set[tuple[str, ActionType, str | None]] = set()
    for result in action_results:
        if result.success:
            action = result.action
            identity = (action.task.gid, action.action, action.target_gid)
            successful_identities.add(identity)

    # Keep only failed actions
    self._pending_actions = [
        action for action in self._pending_actions
        if (action.task.gid, action.action, action.target_gid) not in successful_identities
    ]
```

### Usage in commit_async()

```python
async def commit_async(self) -> SaveResult:
    # ...
    crud_result, action_results = await self._pipeline.execute_with_actions(...)

    # Selective clearing - only remove successful actions
    self._clear_successful_actions(action_results)

    return crud_result
```

### Retry Workflow

```python
async with SaveSession(client) as session:
    session.add_tag(task, "tag_1")  # Valid
    session.add_tag(task, "tag_2")  # Invalid GID

    result = await session.commit_async()
    # tag_1 succeeds, tag_2 fails

    # Inspect failures
    pending = session.get_pending_actions()
    # [ActionOperation(add_tag, task, "tag_2")]

    # Fix and retry
    # (User fixes tag_2 or removes it)
    result2 = await session.commit_async()
```

## Rationale

### Why Identity Tuple (Not Object Reference)?

Option A was to match by object identity (`action is result.action`). Rejected because:

1. **ActionResult may contain a copy**: Pipeline execution might not preserve object references
2. **Serialization breaks identity**: If actions are serialized/deserialized
3. **Tuple is stable**: GID + type + target uniquely identifies the operation

### Why Include target_gid in Identity?

Consider two operations on the same task:
```python
session.add_tag(task, "tag_1")
session.add_tag(task, "tag_2")
```

Without `target_gid`, identity would be `(task.gid, ADD_TAG)` - both actions match the same identity. One success would clear both.

With `target_gid`:
- `("task_123", ADD_TAG, "tag_1")` - distinct identity
- `("task_123", ADD_TAG, "tag_2")` - distinct identity

### Why Set Membership (Not Linear Search)?

```python
# O(1) lookup
successful_identities: set[tuple[...]] = {...}
action_identity in successful_identities

# vs O(n) linear search
any(r.action.task.gid == action.task.gid and ... for r in results)
```

For sessions with many actions, set membership is more efficient.

### Why Keep Failed Actions (Not Return Them)?

Alternative: Clear all actions, return failed ones in `SaveResult.failed_actions`.

Keeping them in `_pending_actions` is simpler:
- User already knows `get_pending_actions()` API
- Retry is just another `commit_async()` call
- No new field needed on SaveResult

## Alternatives Considered

### Alternative A: Match by Object Reference

**Description**: `action is result.action`

**Pros**:
- Simple comparison
- No tuple construction

**Cons**:
- Relies on reference preservation
- Breaks if objects are copied

**Why not chosen**: Reference identity not guaranteed through execution

### Alternative B: Return Failed Actions in SaveResult

**Description**: Add `SaveResult.failed_actions: list[ActionOperation]`

**Pros**:
- Result is self-contained
- Can clear pending unconditionally

**Cons**:
- New field on SaveResult
- Duplicates information (already in action_results)
- User must extract and re-queue

**Why not chosen**: Adds complexity; keeping in pending is simpler

### Alternative C: Never Clear Pending Actions

**Description**: Actions remain until user explicitly clears them

**Pros**:
- Simple implementation
- User has full control

**Cons**:
- Success case: user must manually clear
- Memory accumulation risk
- Breaks expected "commit clears" semantics

**Why not chosen**: Violates principle of least surprise

### Alternative D: Add explicit_clear Parameter

**Description**: `commit_async(clear_on_success=True, clear_on_failure=False)`

**Pros**:
- User controls behavior
- Backward compatible

**Cons**:
- Complex API
- Easy to misconfigure
- Defaults still need to be right

**Why not chosen**: Over-engineering; selective clearing is the right default

## Consequences

### Positive

1. **Retry capability**: Failed actions can be retried without re-queuing
2. **Inspection**: `get_pending_actions()` shows exactly what failed
3. **Semantic correctness**: Success clears, failure preserves
4. **Efficient**: O(n) matching with set membership

### Negative

1. **Memory accumulation**: If user ignores failures, pending grows
2. **Behavioral change**: Previously all cleared, now selective
3. **Duplicate handling**: Identical operations treated as one

### Mitigation

| Risk | Mitigation |
|------|------------|
| Memory accumulation | Pending actions bounded by user's queue size; log warning if pending grows large |
| Behavioral change | This is the fix - correct behavior |
| Duplicate operations | Duplicates are redundant; clearing both is correct |

## Edge Cases

### Duplicate Operations

```python
session.add_tag(task, "tag_1")
session.add_tag(task, "tag_1")  # Duplicate
```

Both have identity `("task_gid", ADD_TAG, "tag_1")`. If first succeeds:
- Identity added to successful set
- Both operations cleared (same identity)

This is correct: the duplicate was redundant anyway.

### Operations on Different Tasks

```python
session.add_tag(task_a, "tag_1")
session.add_tag(task_b, "tag_1")  # Same tag, different task
```

Identities:
- `("task_a_gid", ADD_TAG, "tag_1")`
- `("task_b_gid", ADD_TAG, "tag_1")`

These are distinct. Success/failure of one doesn't affect the other.

### Operations with None target_gid

```python
session.add_like(task)  # target_gid = None
session.add_like(task)  # Duplicate
```

Identity: `("task_gid", ADD_LIKE, None)` - same for both.

Both cleared on success, which is correct.

## Test Verification

1. `test_all_success_clears_all_actions`: Queue 3 actions, all succeed, pending empty
2. `test_all_failure_keeps_all_actions`: Queue 3 actions, all fail, pending has 3
3. `test_partial_keeps_only_failed`: Queue 3 actions, 2 succeed, pending has 1
4. `test_duplicate_operations_both_cleared`: Same action twice, success clears both
5. `test_different_tasks_handled_independently`: Operations on different tasks tracked separately
6. `test_retry_workflow_succeeds`: Re-commit after fixing issue works

## Compliance

### Enforcement

- **Unit tests**: Cover all edge cases above
- **Code review**: Ensure identity tuple includes all relevant fields
- **Type checking**: mypy validates tuple structure

### Documentation

- Update `commit_async()` docstring to explain clearing behavior
- Document retry workflow in usage guide
