# ADR-0042: SaveSession Error Handling & Partial Failures

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-10, Updated 2025-12-12
- **Consolidated From**: ADR-0040 (original), ADR-0065, ADR-0066
- **Related**: [reference/SAVESESSION.md](/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/SAVESESSION.md), PRD-0005, TDD-0010

## Context

The Save Orchestration Layer must handle scenarios where some operations in a commit succeed while others fail. Three critical error handling concerns emerged:

1. **Partial Failure Strategy**: What happens when some operations succeed and others fail?
2. **P1 Method Exceptions**: Should direct convenience methods (`task.save()`, `add_tag_async()`) raise exceptions or return results?
3. **Action Clearing**: After commit, should successful actions be cleared while failed actions remain for retry?

Forces at play:
- Asana reality: No transaction support, no rollback capability
- Batch API returns per-action results independently
- Partial success is valuable (better than losing successful work)
- Developer experience: Clear understanding of outcomes
- Retry capability: Failed operations should be retryable
- P1 methods: Single-operation methods have different UX expectations
- Memory management: Don't accumulate unbounded failed operations

## Decision

### Commit and Report on Partial Failure

On partial failure:
1. **Commit**: Successful operations are preserved (already committed to Asana)
2. **Report**: Failed operations returned in `SaveResult.failed` with full context
3. **Cascade**: Dependent entities marked as failed with `DependencyResolutionError`
4. **No Exception by Default**: Return SaveResult, let caller decide

```python
result = await session.commit_async()

if result.success:
    # All operations succeeded
    print(f"Saved {len(result.succeeded)} entities")
elif result.partial:
    # Some succeeded, some failed
    print(f"{len(result.succeeded)} succeeded, {len(result.failed)} failed")
    for error in result.failed:
        print(f"  {error.entity.gid}: {error.error}")
else:
    # All failed
    print(f"All {len(result.failed)} operations failed")

# Optional: raise if any failures
result.raise_on_failure()  # Raises PartialSaveError
```

**SaveResult Structure:**
```python
@dataclass
class SaveResult:
    succeeded: list[AsanaResource]  # Successfully saved entities
    failed: list[SaveError]         # Failed operations with context
    action_results: list[ActionResult]  # Action operation outcomes

    @property
    def success(self) -> bool:
        """True if all operations succeeded."""
        return len(self.failed) == 0 and len(self.action_failed) == 0

    @property
    def partial(self) -> bool:
        """True if some succeeded and some failed."""
        return len(self.succeeded) > 0 and (
            len(self.failed) > 0 or len(self.action_failed) > 0
        )

@dataclass
class SaveError:
    entity: AsanaResource      # What failed
    operation: OperationType   # CREATE/UPDATE/DELETE
    error: Exception           # Original error (or DependencyResolutionError)
    payload: dict[str, Any]    # What we tried to send
```

### P1 Methods Raise SaveSessionError

Direct convenience methods raise exceptions on failure:

```python
# P1 method (raises on failure)
try:
    task = await client.tasks.add_tag_async(task_gid, tag_gid)
except SaveSessionError as e:
    # Access underlying SaveResult
    result = e.save_result
    print(f"Failed: {result.failed[0].error}")

# Instance method (raises on failure)
try:
    await task.save_async()
except SaveSessionError as e:
    print(f"Save failed: {e}")
```

**SaveSessionError Structure:**
```python
class SaveSessionError(Exception):
    """Exception raised when a P1 operation fails.

    P1 operations (add_tag_async, task.save_async) raise this
    exception on failure, wrapping the SaveResult for inspection.
    """
    def __init__(self, message: str, save_result: SaveResult):
        super().__init__(message)
        self.save_result = save_result
```

**Rationale for Exception in P1:**
- Single-operation methods have clear success/failure expectation
- Exception natural for "this one thing didn't work"
- Consistent with standard Python error handling
- SaveResult still accessible via exception attribute
- Batch operations (session.commit) still return SaveResult

### Selective Action Clearing

After commit, only successful actions are cleared from `_pending_actions`:

```python
def _clear_successful_actions(self, action_results: list[ActionResult]) -> None:
    """Remove only successful actions from pending list.

    Args:
        action_results: Results from action execution
    """
    if not action_results:
        self._pending_actions.clear()
        return

    # Build set of successful action identities
    successful_identities: set[tuple[str, ActionType, str | None]] = set()
    for result in action_results:
        if result.success:
            identity = (result.action.task.gid,
                       result.action.action,
                       result.action.target_gid)
            successful_identities.add(identity)

    # Keep only failed actions (enable retry)
    self._pending_actions = [
        action for action in self._pending_actions
        if (action.task.gid, action.action, action.target_gid)
        not in successful_identities
    ]
```

**Action Identity Model:**
```python
# Unique identity: (task.gid, action_type, target_gid)
ActionIdentity = tuple[str, ActionType, str | None]

# Examples:
# ("task_123", ActionType.ADD_TAG, "tag_456")
# ("task_123", ActionType.REMOVE_TAG, "tag_456")  # Different from above
# ("task_123", ActionType.ADD_LIKE, None)         # No target
```

**Retry Workflow:**
```python
async with SaveSession(client) as session:
    session.add_tag(task, "tag_1")  # Valid
    session.add_tag(task, "tag_2")  # Invalid GID

    result = await session.commit_async()
    # tag_1 succeeds, tag_2 fails

    # Failed action remains in pending
    pending = session.get_pending_actions()
    # [ActionOperation(ADD_TAG, task, "tag_2")]

    # Fix issue and retry
    # (user corrects tag_2 GID or removes it)
    result2 = await session.commit_async()
```

## Rationale

### Why Commit and Report (Not Rollback)

**Asana Reality:**
- No transaction support in Asana API
- No rollback capability for successful operations
- DELETE doesn't undo CREATE (creates new event, doesn't restore state)
- UPDATE can't be reversed without tracking previous values

**Even if we attempted cleanup:**
- Cleanup operations could fail too
- Would leave system in worse state
- Wastes the successful work already done

**Benefits:**
- Maximum information: Developer knows exactly what succeeded/failed
- Flexibility: Developer chooses handling strategy (retry, log, escalate)
- Partial progress: Better than all-or-nothing for large batches
- No wasted work: Successful saves aren't discarded

### Why Return SaveResult (Not Exception) for Batches

1. **Expected Outcome**: Partial failure is valid outcome in batch operations, not exceptional
2. **Information Preservation**: Exception would need to carry same data anyway
3. **Caller Control**: Caller decides severity (`raise_on_failure()` available)
4. **Consistent API**: Always returns SaveResult, always check result
5. **Detailed Context**: SaveError includes entity, operation, error, payload

**Dependency Cascade:**
```
Level 0: parent_task FAILS (validation error)
         → Cannot get parent's GID

Level 1: subtask CANNOT EXECUTE
         → Marked as DependencyResolutionError
         → Added to SaveResult.failed
         → Cause chain points to parent's error
```

This is correct behavior:
- Subtask literally cannot be created without parent GID
- Developer needs to know subtask didn't save AND why
- Error chain enables proper debugging

### Why Raise Exception in P1 Methods

**P1 = Priority 1 = Single-Operation Convenience Methods**

Examples:
- `await task.save_async()`
- `await client.tasks.add_tag_async(task_gid, tag_gid)`
- `await client.tasks.delete_async(task_gid)`

**Rationale for Exception:**
1. **Single Operation**: Clear success/failure expectation
2. **Pythonic**: Exception natural for "this one thing failed"
3. **Backward Compatible**: Existing error-raising patterns
4. **Consistent**: Standard try/except error handling
5. **SaveResult Available**: Exception wraps SaveResult for inspection

**Different from Batch:**
- Batch operations: Multiple items, partial success expected → return SaveResult
- P1 operations: One item, failure is exceptional → raise exception

### Why Selective Action Clearing

**Previous Bug:**
```python
# WRONG: Cleared all actions unconditionally
self._pending_actions.clear()
```

**Problems:**
- Failed actions discarded (cannot retry)
- `get_pending_actions()` returns empty even after failures
- No inspection of what failed

**Solution:**
1. **Retry Capability**: Failed actions remain in `_pending_actions`
2. **Inspection**: `get_pending_actions()` shows exactly what failed
3. **Semantic Correctness**: Success clears, failure preserves
4. **Efficient**: O(n) matching with set membership

**Why Identity Tuple (Not Object Reference):**
- ActionResult may contain copy (not same object reference)
- Serialization could break object identity
- Tuple `(gid, type, target)` is stable and unique

**Why Include target_gid:**
```python
session.add_tag(task, "tag_1")
session.add_tag(task, "tag_2")
```
Without `target_gid`, both have same identity → one success clears both (wrong).
With `target_gid`, distinct identities → cleared independently (correct).

## Alternatives Considered

### Alternative 1: Rollback All on Any Failure

**Description**: If any operation fails, treat entire commit as failed.

**Pros**: Atomic semantics, simpler mental model

**Cons**:
- Cannot actually rollback in Asana (no transaction support)
- Wastes successful work
- Misleading (suggests rollback happened when it didn't)
- Large batches become very fragile

**Why not chosen**: Impossible to implement correctly; wastes work.

### Alternative 2: Automatic Retry on Failure

**Description**: Automatically retry failed operations up to N times.

**Pros**: Higher success rate, transient errors handled

**Cons**:
- Infinite retry risk (needs careful backoff)
- Delays overall commit
- Some failures aren't retriable (validation errors)
- Complexity in distinguishing transient vs permanent failures

**Why not chosen**: Should be user's choice; can add to future version if needed.

### Alternative 3: Exception Always on Any Failure

**Description**: Raise PartialSaveError whenever any failure occurs (batch or P1).

**Pros**: Forces caller to handle failures

**Cons**:
- Treats expected outcome as exceptional (batches)
- Harder to access successful results
- Inconsistent with "report" philosophy
- Breaking try/except for every commit

**Why not chosen**: Exception available via `raise_on_failure()`; shouldn't be default for batches.

### Alternative 4: Never Clear Pending Actions

**Description**: Actions remain until user explicitly clears them.

**Pros**: Simple implementation, user has full control

**Cons**:
- Success case: user must manually clear (poor UX)
- Memory accumulation risk
- Breaks expected "commit clears" semantics

**Why not chosen**: Violates principle of least surprise.

### Alternative 5: Return Failed Actions in SaveResult

**Description**: Add `SaveResult.failed_actions: list[ActionOperation]`, clear pending unconditionally.

**Pros**: Result is self-contained, can clear pending

**Cons**:
- New field on SaveResult (duplicates information already in action_results)
- User must extract and re-queue
- More complex than keeping in pending

**Why not chosen**: Keeping in pending is simpler; `get_pending_actions()` already exists.

## Consequences

### Positive

- **Preserves Work**: All successful operations committed, not discarded
- **Full Context**: SaveResult provides complete information about outcomes
- **Flexible Handling**: Developer chooses error handling strategy
- **Retry Capability**: Failed actions remain for retry without re-queuing
- **Inspection**: `get_pending_actions()` shows exactly what failed
- **Dependency Attribution**: Cascade failures clearly attributed to root cause
- **Pythonic P1**: Exception-based error handling for single operations
- **Semantic Correctness**: Success clears, failure preserves

### Negative

- **Partial State**: May need cleanup (developer responsibility)
- **Complex Result Handling**: More than simple success/fail for batches
- **Must Check Result**: Developers must check `result.success` (not just catch exception)
- **Memory Accumulation**: If user ignores failures, pending actions grow
- **Behavioral Change**: Previously all cleared, now selective (this is the fix)

### Neutral

- **SaveResult Always Returned**: Even on full success or full failure
- **`raise_on_failure()` Available**: Opt-in exception for batch operations
- **Cascade Failures Counted**: Dependency failures included in `failed` list
- **Duplicate Actions Handled**: Same identity → cleared together (correct)

## Compliance

### Enforcement

1. **API Design**: `commit_async()` returns SaveResult (doesn't raise by default)
2. **P1 Methods**: All direct methods raise SaveSessionError on failure
3. **SaveResult Structure**: Always has `succeeded` and `failed` lists
4. **Type Checking**: mypy validates SaveResult usage
5. **Selective Clearing**: `_clear_successful_actions()` called in `commit_async()`

### Testing

**Unit Tests Verify:**
- All success: succeeded populated, failed empty, pending cleared
- All failure: succeeded empty, failed populated, pending unchanged
- Partial failure: both lists populated, selective clearing
- Dependency cascade: failures attributed correctly
- P1 methods: raise SaveSessionError on failure
- `raise_on_failure()`: raises when failures exist
- Action clearing: duplicate operations both cleared on success
- Action clearing: different tasks handled independently
- Retry workflow: re-commit after fixing issue succeeds

**Integration Tests Verify:**
- Partial save results propagate to caller
- Failed operations can be retried
- P1 exceptions caught correctly

## Implementation Guidance

### Batch Operation Error Handling

**Check Result Status:**
```python
result = await session.commit_async()

if result.success:
    # All operations succeeded
    log.info(f"Saved {len(result.succeeded)} entities")

elif result.partial:
    # Some succeeded, some failed
    log.warning(f"{len(result.succeeded)} succeeded, {len(result.failed)} failed")
    for error in result.failed:
        log.error(f"Failed {error.entity.gid}: {error.error}")

else:
    # All failed
    log.error(f"All operations failed")
    for error in result.failed:
        log.error(f"  {error.entity.gid}: {error.error}")
```

**Optional Exception Raising:**
```python
result = await session.commit_async()
result.raise_on_failure()  # Raises if any failures exist
```

**Retry on Partial Failure:**
```python
result = await session.commit_async()
if not result.all_success:
    # Failed actions remain in pending queue
    pending = session.get_pending_actions()
    log.info(f"{len(pending)} actions failed, will retry")

    # Fix issues, then retry
    result2 = await session.commit_async()
```

### P1 Method Error Handling

**Standard Try/Except:**
```python
try:
    task = await task.save_async()
except SaveSessionError as e:
    log.error(f"Save failed: {e}")
    # Access SaveResult for details
    for error in e.save_result.failed:
        log.error(f"  {error.entity.gid}: {error.error}")
```

**With Context Manager:**
```python
try:
    await client.tasks.add_tag_async(task_gid, tag_gid)
except SaveSessionError as e:
    # SaveSession created and destroyed within method
    # Exception contains full SaveResult
    print(f"Add tag failed: {e}")
```

## Cross-References

**Related ADRs:**
- ADR-0040: Unit of Work Pattern (provides SaveSession foundation)
- ADR-0041: Dependency Ordering (provides cascade failure mechanism)
- ADR-0043: Action Operations (uses SaveResult structure)

**Related Documents:**
- PRD-0005: Save Orchestration error handling requirements
- TDD-0010: Error handling technical design
- REF-savesession-lifecycle: Error state transitions
