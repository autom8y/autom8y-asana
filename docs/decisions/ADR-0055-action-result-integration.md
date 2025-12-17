# ADR-0055: Action Result Integration into SaveResult

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-SDKDEMO, TDD-0011, ADR-0042 (Action Operation Types), ADR-0040 (Partial Failure Handling)

## Context

BUG-1 identified that action operation results are executed but discarded in `session.py` at lines 526-553. The current implementation:

1. Executes CRUD operations via `execute_with_actions()` which returns `(SaveResult, list[ActionResult])`
2. Logs action success/failure counts (lines 542-550)
3. Returns **only** `crud_result`, discarding `action_results`

This causes:
- Silent action failures (e.g., `add_tag` fails but caller sees `succeeded=1, failed=0`)
- Misleading metrics (actions execute but aren't reflected in results)
- No way for callers to know which action operations failed

### Current Code (BUG)

```python
# session.py lines 526-553
crud_result, action_results = await self._pipeline.execute_with_actions(
    entities=dirty_entities,
    actions=pending_actions,
    action_executor=self._action_executor,
)

# ... action_results logged but never returned ...

return crud_result  # BUG: action_results discarded
```

### Forces at Play

1. **Backward compatibility**: Existing code expects `SaveResult` with `succeeded: list[AsanaResource]` and `failed: list[SaveError]`
2. **Semantic mismatch**: Actions don't operate on entities the same way CRUD does (actions modify relationships, not entities)
3. **Type consistency**: `SaveError.entity` assumes an `AsanaResource`, but action failures relate to task-target pairs
4. **API clarity**: Callers need to distinguish CRUD failures from action failures
5. **Existing patterns**: `ActionResult` already captures action outcomes with `success`, `error`, and `response_data`

## Decision

**Extend SaveResult to include action operation results as a separate list.** Add two new fields:

```python
@dataclass
class SaveResult:
    """Result of a commit operation."""

    # Existing CRUD results
    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)

    # NEW: Action results (ADR-0055)
    action_results: list[ActionResult] = field(default_factory=list)
```

And modify `commit_async()` to merge action results into `SaveResult`:

```python
# Modified session.py commit_async()
crud_result, action_results = await self._pipeline.execute_with_actions(...)

# NEW: Merge action results into SaveResult
crud_result.action_results = action_results

return crud_result
```

### New Properties on SaveResult

```python
@property
def action_succeeded(self) -> list[ActionResult]:
    """Action operations that succeeded."""
    return [r for r in self.action_results if r.success]

@property
def action_failed(self) -> list[ActionResult]:
    """Action operations that failed."""
    return [r for r in self.action_results if not r.success]

@property
def all_success(self) -> bool:
    """True if both CRUD and action operations succeeded."""
    return self.success and len(self.action_failed) == 0
```

## Rationale

### Why Not Merge Action Failures into `failed` List?

Option B from the session brief suggested merging action failures into the existing `failed: list[SaveError]` list. This was rejected because:

1. **Type mismatch**: `SaveError` has `entity: AsanaResource` and `operation: OperationType`, but actions don't have a single entity (they operate on task-target pairs) and use `ActionType` not `OperationType`
2. **Semantic confusion**: Mixing "task update failed" with "add_tag failed" in the same list makes filtering difficult
3. **Breaking change**: Code checking `len(result.failed)` would suddenly see different values

### Why Not Return a New `CommitResult` Type?

Option C suggested a new return type. Rejected because:

1. **Breaking change**: All existing callers would need updates
2. **Unnecessary complexity**: Extending `SaveResult` achieves the same goal with less disruption
3. **Dataclass flexibility**: Adding optional fields with default empty lists is backward compatible

### Why Expose ActionResult Directly?

Rather than creating a new `ActionError` type, we expose `ActionResult` directly because:

1. **Already exists**: `ActionResult` is well-defined in `persistence/models.py`
2. **Rich information**: Contains `action`, `success`, `error`, and `response_data`
3. **Consistent with pipeline**: `execute_with_actions()` already returns `list[ActionResult]`

## Implementation Specification

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py`

**Change 1**: Add `action_results` field to `SaveResult` class (around line 123)

```python
@dataclass
class SaveResult:
    """Result of a commit operation.

    Per FR-ERROR-002: Provides succeeded, failed, and aggregate info.
    Per ADR-0055: Includes action operation results.

    Attributes:
        succeeded: List of entities that were saved successfully
        failed: List of SaveError for entities that failed
        action_results: List of ActionResult for action operations (ADR-0055)
    """

    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    action_results: list[ActionResult] = field(default_factory=list)  # NEW
```

**Change 2**: Add new properties after `total_count` property (around line 152)

```python
    @property
    def action_succeeded(self) -> list[ActionResult]:
        """Action operations that succeeded (ADR-0055).

        Returns:
            List of successful ActionResult objects.
        """
        return [r for r in self.action_results if r.success]

    @property
    def action_failed(self) -> list[ActionResult]:
        """Action operations that failed (ADR-0055).

        Returns:
            List of failed ActionResult objects.
        """
        return [r for r in self.action_results if not r.success]

    @property
    def all_success(self) -> bool:
        """True if all operations (CRUD and actions) succeeded (ADR-0055).

        Returns:
            True if no CRUD failures and no action failures.
        """
        return self.success and len(self.action_failed) == 0
```

**Change 3**: Update `__repr__` to include action counts

```python
    def __repr__(self) -> str:
        """Return string representation for debugging."""
        action_ok = len(self.action_succeeded)
        action_err = len(self.action_failed)
        if self.action_results:
            return (
                f"SaveResult(succeeded={len(self.succeeded)}, failed={len(self.failed)}, "
                f"actions_ok={action_ok}, actions_failed={action_err})"
            )
        return f"SaveResult(succeeded={len(self.succeeded)}, failed={len(self.failed)})"
```

### File: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`

**Change 1**: Modify `commit_async()` return to include action results (line 553)

Replace:
```python
        return crud_result
```

With:
```python
        # ADR-0055: Merge action results into SaveResult
        crud_result.action_results = action_results

        return crud_result
```

This change is at line 553, after the logging block (lines 544-551).

### Method Signatures (No Changes)

The public API signature remains unchanged:
```python
async def commit_async(self) -> SaveResult:
```

## Alternatives Considered

### Alternative A: Add Counts Only

**Description**: Add `action_succeeded_count` and `action_failed_count` integer fields

**Pros**:
- Minimal API change
- Simple aggregation

**Cons**:
- No detail on which actions failed
- Cannot inspect failure reasons
- Insufficient for debugging

**Why not chosen**: Callers need to know WHICH actions failed and WHY

### Alternative B: Merge into Failed List

**Description**: Convert `ActionResult` failures to `SaveError` and merge into `failed` list

**Pros**:
- Single list for all failures
- Simpler mental model

**Cons**:
- Type mismatch (action != entity)
- Would require fake entity or None
- Breaks existing `SaveError` semantics
- Hard to filter action vs CRUD failures

**Why not chosen**: Semantic mismatch is too significant

### Alternative C: New CommitResult Type

**Description**: Return `CommitResult(crud_result: SaveResult, action_results: list[ActionResult])`

**Pros**:
- Clean separation
- Type-safe

**Cons**:
- Breaking change to return type
- All callers need updates
- Tuple unpacking everywhere

**Why not chosen**: Extension is less disruptive than replacement

## Consequences

### Positive

1. **Visibility**: Callers can now see action operation outcomes
2. **Debugging**: Failed actions include error details
3. **Backward compatible**: Existing code using `succeeded`/`failed` works unchanged
4. **Type safe**: `ActionResult` is already well-typed

### Negative

1. **Larger SaveResult**: Additional field may surprise callers who `print(result)`
2. **Two failure lists**: Callers must check both `failed` and `action_failed` for complete picture

### Neutral

1. **Import order**: `ActionResult` imported in models.py (already available in same module)
2. **Empty list default**: `action_results=[]` for commits without actions

## Test Verification

After implementation, verify:

1. **Action results captured**: Call `add_tag()` then `commit_async()`, check `result.action_results` is not empty
2. **Success classification**: Successful action appears in `result.action_succeeded`
3. **Failure classification**: Failed action (invalid GID) appears in `result.action_failed`
4. **all_success property**: Returns False when action fails even if CRUD succeeds
5. **Backward compatibility**: Code using only `result.succeeded` and `result.failed` still works
6. **Empty actions**: Commit without actions has `action_results == []`

## Compliance

### Enforcement

- **Unit tests**: Test `SaveResult` properties with mixed CRUD/action results
- **Integration test**: Demo script should show action results after commit
- **Type checking**: mypy validates `action_results: list[ActionResult]`

### Documentation

- Update `SaveResult` docstring with action_results field
- Add example in `SaveSession.commit_async()` docstring showing action result inspection
