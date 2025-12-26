# ADR-0037: Partial Failure Handling & Result Patterns

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-25
- **Deciders**: Architect, Principal Engineer
- **Consolidated From**: ADR-0040 (Commit and Report), ADR-0070 (Hydration Partial Failure), ADR-0046 (Comment Storage), ADR-0047 (Positioning Validation)
- **Related**: reference/API-INTEGRATION.md, ADR-SUMMARY-SAVESESSION.md

## Context

The Asana Batch API returns per-action results where some operations may succeed while others fail. Additionally, hydration operations may partially succeed when loading hierarchies. The SDK must handle these scenarios without losing successful work or hiding failures.

Forces at play:
1. **Asana Semantics**: No transaction support - successful operations are committed permanently
2. **Batch Atomicity**: Asana batches are NOT atomic - individual actions are independent
3. **Developer Experience**: Clear understanding of what succeeded vs. failed
4. **Error Recovery**: Enable appropriate failure handling strategies
5. **Dependency Cascading**: If parent fails, dependent children cannot proceed

The fundamental question: **When some operations fail, what happens to successful operations?**

## Decision

### Commit-and-Report Strategy

**Commit all successful operations, report all failures in structured result types.**

On partial failure:
1. **Commit**: Successful operations preserved (already committed to Asana)
2. **Report**: Failed operations returned with full context
3. **Cascade**: Dependent entities marked as failed with clear attribution
4. **No Exception by Default**: Return result type, let caller decide

### SaveResult Structure

```python
@dataclass
class SaveResult:
    """Result of SaveSession.commit_async operation."""
    succeeded: list[EntityResult]
    failed: list[SaveError]
    action_results: list[ActionResult]

    @property
    def success(self) -> bool:
        """True if all operations succeeded."""
        return len(self.failed) == 0

    @property
    def partial(self) -> bool:
        """True if some succeeded, some failed."""
        return len(self.succeeded) > 0 and len(self.failed) > 0

    def raise_on_failure(self) -> None:
        """Raise PartialSaveError if any failures occurred."""
        if self.failed:
            raise PartialSaveError(f"{len(self.failed)} operations failed", self)
```

### Usage Pattern

```python
result = await session.commit_async()

if result.success:
    print(f"All {len(result.succeeded)} entities saved")
elif result.partial:
    print(f"Partial: {len(result.succeeded)} succeeded, {len(result.failed)} failed")
    for error in result.failed:
        print(f"  {error.entity}: {error.error}")
    # Decide: retry, log, escalate
else:
    print(f"All {len(result.failed)} entities failed")

# Optional: raise if any failures
result.raise_on_failure()  # Raises PartialSaveError
```

### SaveError Structure

Each failure includes full context:

```python
@dataclass
class SaveError:
    entity: AsanaResource      # What failed
    operation: OperationType   # CREATE/UPDATE/DELETE
    error: Exception           # Original error (or DependencyResolutionError)
    payload: dict[str, Any]    # What we tried to send

    @property
    def is_retryable(self) -> bool:
        """Advisory: suggests retry eligibility."""
```

Enables:
- Identifying the entity that failed
- Understanding what operation was attempted
- Debugging with the actual payload sent
- Accessing original error details
- Checking retry eligibility

### Dependency Cascade

When a parent fails, dependent children cannot save:

```
Level 0: parent_task FAILS (API error)
         -> Cannot get parent's GID

Level 1: subtask CANNOT EXECUTE
         -> Marked as DependencyResolutionError
         -> Added to SaveResult.failed
         -> Cause points to parent's error
```

```python
class DependencyResolutionError(SaveOrchestrationError):
    """Raised when dependency cannot be resolved."""
    def __init__(self, entity: AsanaResource, cause: Exception):
        super().__init__(f"Cannot resolve dependency for {entity}")
        self.entity = entity
        self.cause = cause  # Points to parent's error
```

### HydrationResult Structure

Follows same commit-and-report pattern for loading hierarchies:

```python
@dataclass
class HydrationResult:
    """Result of hydration operation."""
    business: Business              # Root entity (always populated if found)
    entry_entity: BusinessEntity    # Entity at entry GID
    succeeded: list[BusinessEntity] # Successfully loaded entities
    failed: list[HydrationError]    # Failed fetches

    @property
    def is_complete(self) -> bool:
        """True if full hierarchy loaded without failures."""
        return len(self.failed) == 0

    def raise_on_failure(self) -> None:
        """Raise PartialHydrationError if any failures."""
        if self.failed:
            raise PartialHydrationError(
                f"{len(self.failed)} hydration operations failed", self
            )
```

### Queue-Time Validation

**Validate parameters at queue time (when method called), not commit time.**

```python
class SaveSession:
    def create_task(
        self,
        name: str,
        *,
        parent: str | Task | None = None,
        insert_before: str | Task | None = None,
        insert_after: str | Task | None = None,
    ) -> Task:
        """Queue task creation with validation."""
        # Validate positioning conflicts immediately
        if insert_before is not None and insert_after is not None:
            raise PositioningConflictError(
                f"Cannot specify both insert_before and insert_after"
            )

        # Store comment in extra_params if provided
        # Validation at queue time provides immediate feedback
```

**Benefits**:
- Immediate feedback with stack trace pointing to mistake
- No wasted operations for invalid input
- Error attribution clear (call site vs. commit time)
- Consistent with fail-fast philosophy

## Rationale

### Why Commit and Report?

1. **Asana Reality**: Asana doesn't support rollback - successful actions stay committed
2. **No Wasted Work**: Successful saves aren't thrown away because something else failed
3. **Maximum Information**: Developer knows exactly what succeeded and what failed
4. **Flexibility**: Developer chooses how to handle (retry, log, escalate)
5. **Partial Progress**: Better than all-or-nothing for large batches

### Why Not Rollback (Fail All)?

Rollback is **impossible** with Asana:
- No transaction support
- No DELETE to undo CREATE (creates new delete event, doesn't restore state)
- No UNDO for UPDATE (would need to track previous values)

Even if we attempted cleanup:
- Cleanup could fail too
- Leaves system in worse state
- Wastes the successful work

### Why Return Result (Not Exception)?

1. **Expected Outcome**: Partial failure is valid outcome, not exceptional
2. **Information Preservation**: Exception would need to carry same data anyway
3. **Caller Control**: Caller decides severity (`raise_on_failure()` optional)
4. **Consistent API**: Always returns result, always check result

### Why Dependency Cascade?

When a parent fails, dependent children **literally cannot be created**:
- Subtask requires parent GID
- API rejects subtask creation without valid parent
- Developer needs to know subtask didn't save AND why
- Error chain enables proper debugging

Marking dependents as failed (not skipped) is correct:
- They were queued for save
- Save was attempted
- Failure cause is clear (dependency resolution)

### Why Queue-Time Validation?

**Alternative**: Validate at commit time
- **Cons**: Errors discovered late, poor stack traces, unclear call site
- **Cons**: Wasted work building batches that will fail validation

**Queue-time validation**:
- **Pros**: Immediate feedback with clear stack trace
- **Pros**: No wasted work for invalid input
- **Pros**: Consistent with fail-fast error handling

## Alternatives Considered

### Alternative 1: Fail All (Rollback)

- **Description**: If any operation fails, treat entire commit as failed
- **Pros**: Atomic semantics, simpler mental model
- **Cons**: Cannot actually rollback in Asana, wastes successful work, misleading
- **Why not chosen**: Impossible to implement correctly; wastes work

### Alternative 2: Retry Failed (Automatic)

- **Description**: Automatically retry failed operations up to N times
- **Pros**: Higher success rate, transient errors handled
- **Cons**: Infinite retry risk, delays commit, some failures not retriable, complexity
- **Why not chosen**: Should be user's choice; can add in future version

### Alternative 3: Stop on First Failure

- **Description**: Stop processing as soon as any operation fails
- **Pros**: Fast failure, clear point of failure
- **Cons**: Operations before failure already committed, remaining operations unknown, worse than commit-and-report
- **Why not chosen**: Leaves batch in undefined state

### Alternative 4: Exception Always

- **Description**: Raise PartialSaveError whenever any failure occurs
- **Pros**: Forces caller to handle failures
- **Cons**: Treats expected outcome as exceptional, harder to access successful results, inconsistent with "report" philosophy
- **Why not chosen**: Exception available via `raise_on_failure()`; shouldn't be default

### Alternative 5: Two-Phase Commit Simulation

- **Description**: Validate all operations first, then execute all
- **Pros**: Some errors caught before any execution
- **Cons**: Many errors only detectable at execution, adds latency, still partial failure possible, over-engineering
- **Why not chosen**: Doesn't solve fundamental problem; adds complexity

### Alternative 6: Commit-Time Validation

- **Description**: Validate positioning/comments when batch is submitted
- **Pros**: All validation in one place
- **Cons**: Late error discovery, poor stack traces, unclear call site, wasted work
- **Why not chosen**: Queue-time validation provides better developer experience

## Consequences

### Positive

- **Preserves successful work**: No wasted API calls or lost data
- **Full information**: Complete picture of successes and failures
- **Developer control**: Caller decides error handling strategy
- **Correct with Asana**: Works with non-transactional model
- **Clear attribution**: Dependency failures point to root cause
- **Immediate feedback**: Queue-time validation catches errors at call site
- **Consistent pattern**: Same approach for SaveSession and Hydration

### Negative

- **Partial state**: May need cleanup (developer responsibility)
- **Complex result handling**: More than simple success/fail boolean
- **Must check result**: Developers must check `result.success` (not just catch exception)
- **No automatic retry**: User must implement if desired

### Neutral

- **Result always returned**: Even on full success or full failure
- **`raise_on_failure()` available**: Opt-in exception-based handling
- **Cascade failures counted**: Counted as failures, not skipped
- **Comment/positioning storage**: Stored in `extra_params` (established pattern)

## Compliance

### Enforcement

1. **API Design**: `commit_async()` returns `SaveResult`, not raises
2. **Result Structure**: Always has `succeeded` and `failed` lists
3. **Documentation**: Clear examples of checking result
4. **Tests**: Test partial failure scenarios explicitly
5. **`raise_on_failure()`**: Provide opt-in exception raising
6. **Queue-time validation**: Positioning and comment validation at method call

### Validation

- [ ] `commit_async()` returns `SaveResult` on partial failure
- [ ] `SaveResult.succeeded` contains successful entities
- [ ] `SaveResult.failed` contains failed entities with full context
- [ ] Dependency failures include cause chain
- [ ] `HydrationResult` follows same pattern
- [ ] Positioning conflicts raise immediately at queue time
- [ ] Comment text validated at queue time
- [ ] `raise_on_failure()` raises appropriate exception with result attached
