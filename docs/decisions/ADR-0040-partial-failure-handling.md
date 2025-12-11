# ADR-0040: Commit and Report on Partial Failure

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-ERROR-001 through FR-ERROR-010), TDD-0010

## Context

The Save Orchestration Layer must handle scenarios where some operations in a commit succeed and others fail. The Asana Batch API returns per-action results, and different actions can have different outcomes.

**Forces at play:**

1. **Asana Semantics**: Once an action succeeds, it's committed permanently - no rollback
2. **Batch Atomicity**: Asana batches are NOT atomic - individual actions independent
3. **Developer Experience**: Clear understanding of what succeeded vs failed
4. **Error Recovery**: Enable developers to handle failures appropriately
5. **Dependency Cascading**: If parent fails, dependent children cannot proceed

**Problem**: When some operations fail in a commit, what should happen to successful operations?

## Decision

Use **Commit and Report** strategy: commit all successful operations, report all failures in SaveResult.

On partial failure:
1. **Commit**: Successful operations are preserved (already committed to Asana)
2. **Report**: Failed operations returned in `SaveResult.failed` with full context
3. **Cascade**: Dependent entities marked as failed with `DependencyResolutionError`
4. **No Exception by Default**: Return SaveResult, let caller decide

```python
result = await session.commit_async()

if result.success:
    print(f"All {len(result.succeeded)} entities saved")
elif result.partial:
    print(f"Partial: {len(result.succeeded)} succeeded, {len(result.failed)} failed")
    for error in result.failed:
        print(f"  {error.entity}: {error.error}")
else:
    print(f"All {len(result.failed)} entities failed")

# Optional: raise if any failures
result.raise_on_failure()  # Raises PartialSaveError if failed
```

## Rationale

### Why Commit and Report

1. **Asana Reality**: Asana doesn't support rollback - successful actions stay committed
2. **No Wasted Work**: Successful saves aren't thrown away because something else failed
3. **Maximum Information**: Developer knows exactly what succeeded and what failed
4. **Flexibility**: Developer chooses how to handle (retry, log, escalate)
5. **Partial Progress**: Better than all-or-nothing for large batches

### Why Not Rollback (Fail All)

Rollback is **impossible** with Asana:
- No transaction support
- No DELETE to undo CREATE (creates new delete event, doesn't restore state)
- No UNDO for UPDATE (would need to track previous values)

Even if we attempted cleanup:
- Cleanup could fail too
- Leaves system in worse state
- Wastes the successful work

### Why Return SaveResult (Not Exception)

1. **Expected Outcome**: Partial failure is a valid outcome, not exceptional
2. **Information Preservation**: Exception would need to carry same data
3. **Caller Control**: Caller decides severity (`raise_on_failure()` optional)
4. **Consistent API**: Always returns SaveResult, always check result

### Dependency Cascade

When a parent fails, dependent children cannot save:

```
Level 0: parent_task FAILS
         -> Cannot get parent's GID

Level 1: subtask CANNOT EXECUTE
         -> Marked as DependencyResolutionError
         -> Added to SaveResult.failed
         -> Cause points to parent's error
```

This is the correct behavior because:
- Subtask literally cannot be created without parent GID
- Developer needs to know subtask didn't save AND why
- Error chain enables proper debugging

### SaveError Structure

Each failure includes full context:

```python
@dataclass
class SaveError:
    entity: AsanaResource      # What failed
    operation: OperationType   # CREATE/UPDATE/DELETE
    error: Exception           # Original error (or DependencyResolutionError)
    payload: dict[str, Any]    # What we tried to send
```

This enables:
- Identifying the entity
- Understanding what we tried to do
- Debugging with the payload
- Accessing original error details

## Alternatives Considered

### Alternative 1: Fail All (Rollback)

- **Description**: If any operation fails, treat entire commit as failed
- **Pros**: Atomic semantics, simpler mental model
- **Cons**:
  - Cannot actually rollback in Asana
  - Wastes successful work
  - Misleading (suggests rollback happened)
  - Large batches become very fragile
- **Why not chosen**: Impossible to implement correctly; wastes work

### Alternative 2: Retry Failed (Automatic)

- **Description**: Automatically retry failed operations up to N times
- **Pros**: Higher success rate, transient errors handled
- **Cons**:
  - Infinite retry risk
  - Delays overall commit
  - Some failures aren't retriable (validation errors)
  - Complexity
- **Why not chosen**: Should be user's choice; can add to future version

### Alternative 3: Stop on First Failure

- **Description**: Stop processing as soon as any operation fails
- **Pros**: Fast failure, clear point of failure
- **Cons**:
  - Operations before failure already committed
  - Remaining operations unknown status
  - Worse than commit-and-report
- **Why not chosen**: Leaves batch in undefined state

### Alternative 4: Exception Always

- **Description**: Raise PartialSaveError whenever any failure occurs
- **Pros**: Forces caller to handle failures
- **Cons**:
  - Treats expected outcome as exceptional
  - Harder to access successful results
  - Inconsistent with "report" philosophy
- **Why not chosen**: Exception available via raise_on_failure(); shouldn't be default

### Alternative 5: Two-Phase Commit Simulation

- **Description**: Validate all operations first, then execute all
- **Pros**: Some errors caught before any execution
- **Cons**:
  - Many errors only detectable at execution time
  - Adds latency for validation pass
  - Still partial failure possible in execute phase
  - Over-engineering
- **Why not chosen**: Doesn't solve the fundamental problem; adds complexity

## Consequences

### Positive
- Preserves all successful work
- Full information about what succeeded and failed
- Developer controls error handling strategy
- Works correctly with Asana's non-transactional model
- Dependency failures clearly attributed

### Negative
- Partial state may need cleanup (developer responsibility)
- More complex result handling than simple success/fail
- Developers must check result.success (not just catch exception)

### Neutral
- SaveResult always returned (even on full success or full failure)
- raise_on_failure() available for exception-based handling
- Cascade failures counted as failures (not skipped)

## Compliance

How do we ensure this decision is followed?

1. **API Design**: commit_async() returns SaveResult, not raises
2. **SaveResult Structure**: Always has succeeded and failed lists
3. **Documentation**: Clear examples of checking result
4. **Tests**: Test partial failure scenarios explicitly
5. **raise_on_failure()**: Provide opt-in exception raising
