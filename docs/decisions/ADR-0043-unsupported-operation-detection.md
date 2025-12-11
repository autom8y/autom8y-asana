# ADR-0043: Validation-Phase Detection for Unsupported Direct Modifications

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer, QA
- **Related**: PRD-0006, TDD-0010, TDD-0011, ADR-0036 (Change Tracking), ADR-0042 (Action Operation Types)

## Context

PRD-0006 requires that the SDK detect and reject direct modifications to collection fields that require action endpoints (`tags`, `projects`, `memberships`, `dependencies`). Currently, these modifications are silently ignored during commit, leading to data loss and developer confusion.

**The Problem**:
```python
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)
    task.tags.append(NameGid(gid="tag_456", name="Priority"))  # Looks valid
    result = await session.commit()  # Tag change silently ignored!
```

The modification appears to succeed, but the tag is never added because `PUT /tasks/{gid}` ignores the `tags` field. Users must use `session.add_tag()` instead.

**Requirements** (from PRD-0006):
- FR-UNSUP-001 through FR-UNSUP-004: Detect modifications to `tags`, `projects`, `memberships`, `dependencies`
- FR-UNSUP-005: Detection must occur before API calls (fail-fast)
- FR-UNSUP-006, FR-UNSUP-007: Error message must identify field and suggest correct method
- FR-PREV-003: `preview()` must also detect unsupported modifications

### Design Question

Where in the save flow should we detect unsupported modifications?

Three candidates:
1. **In `ChangeTracker.get_changes()`**: Detect when computing field changes
2. **In `SavePipeline._validate()` (VALIDATE phase)**: Detect during pipeline validation
3. **In `SaveSession.commit()`**: Pre-flight check before invoking pipeline

## Decision

Detect unsupported modifications in **`SavePipeline.preview()` and `SavePipeline.execute()` during the VALIDATE phase**, using `ChangeTracker.get_changes()` to identify which fields have been modified, then checking if those fields are in the unsupported set.

**Implementation location**: New method `_validate_no_unsupported_changes()` called at the start of both `preview()` and `execute()`.

```python
# In SavePipeline

UNSUPPORTED_FIELDS = {
    "tags": ("add_tag", "remove_tag"),
    "projects": ("add_to_project", "remove_from_project"),
    "memberships": ("add_to_project", "remove_from_project", "move_to_section"),
    "dependencies": ("add_dependency", "remove_dependency"),
}

def _validate_no_unsupported_changes(
    self,
    entities: list[AsanaResource],
) -> None:
    """Validate that no entities have unsupported direct modifications.

    Per FR-UNSUP-005: Detection occurs before any API calls.

    Raises:
        UnsupportedOperationError: If any entity has direct modifications
            to fields that require action endpoints.
    """
    for entity in entities:
        changes = self._tracker.get_changes(entity)

        for field_name in changes.keys():
            if field_name in self.UNSUPPORTED_FIELDS:
                raise UnsupportedOperationError(field_name)
```

## Rationale

### Why VALIDATE Phase in SavePipeline?

1. **Single responsibility**: `ChangeTracker` tracks changes; `SavePipeline` validates them. Adding validation logic to the tracker conflates responsibilities.

2. **Consistent with existing architecture**: The VALIDATE phase already performs cycle detection. Adding unsupported field detection is a natural extension.

3. **Covers both paths**: Both `preview()` and `execute()` run through the pipeline, so a single validation point covers both (per FR-PREV-003).

4. **Fail-fast, but not too early**: Validation happens after all entities are tracked and changes computed, but before any API calls. This satisfies FR-UNSUP-005.

5. **Access to all context**: The pipeline has access to `ChangeTracker` for change detection and can aggregate errors across entities if needed.

### Why Not ChangeTracker?

`ChangeTracker.get_changes()` returns `{field: (old, new)}` for all changed fields. If we added validation there, it would:

1. **Couple change detection to validation**: Every call to `get_changes()` would perform validation, even when just inspecting state
2. **Duplicate responsibility**: ChangeTracker would both track changes AND enforce policies
3. **Complicate return type**: Would need to return changes + validation errors

### Why Not SaveSession.commit()?

Putting detection in `commit()` before `_pipeline.execute()` would:

1. **Duplicate logic**: `preview()` also needs this check (per FR-PREV-003), so we'd duplicate the validation
2. **Split responsibility**: Session handles registration; pipeline handles validation and execution
3. **Miss some cases**: Future code paths that directly call pipeline would bypass the check

### Error Message Design

Per FR-UNSUP-006 and FR-UNSUP-007, the error must be actionable:

```python
class UnsupportedOperationError(SaveOrchestrationError):
    """Raised when attempting unsupported direct modification."""

    FIELD_SUGGESTIONS = {
        "tags": ("add_tag", "remove_tag"),
        "projects": ("add_to_project", "remove_from_project"),
        "memberships": ("add_to_project", "remove_from_project", "move_to_section"),
        "dependencies": ("add_dependency", "remove_dependency"),
    }

    def __init__(self, field_name: str, entity: AsanaResource | None = None) -> None:
        self.field_name = field_name
        self.entity = entity
        suggestions = self.FIELD_SUGGESTIONS.get(field_name, ())
        self.suggested_methods = suggestions

        entity_desc = ""
        if entity:
            entity_desc = f" on {type(entity).__name__}(gid={entity.gid})"

        if suggestions:
            methods = " or ".join(f"session.{m}()" for m in suggestions)
            message = (
                f"Direct modification of '{field_name}'{entity_desc} is not supported. "
                f"Use {methods} instead."
            )
        else:
            message = f"Direct modification of '{field_name}'{entity_desc} is not supported."

        super().__init__(message)
```

Example error:
```
UnsupportedOperationError: Direct modification of 'tags' on Task(gid=123) is not supported.
Use session.add_tag() or session.remove_tag() instead.
```

## Alternatives Considered

### Alternative 1: Detect in ChangeTracker.get_changes()

**Description**: Add validation logic to `get_changes()` that raises if unsupported fields are modified.

**Pros**:
- Earliest possible detection
- Single point of change detection

**Cons**:
- Couples change detection to policy enforcement
- `get_changes()` is also used for non-validation purposes (e.g., debugging, payload building)
- Would need to add optional `validate` parameter to control behavior
- Violates single responsibility principle

**Why not chosen**: ChangeTracker should be a passive observer of state changes, not an enforcer of policies.

### Alternative 2: Detect in SaveSession.commit()

**Description**: Add a pre-flight validation step in `commit()` before calling `_pipeline.execute()`.

**Pros**:
- Explicit validation at the user-facing API
- Clear that commit() is the validation point

**Cons**:
- Duplicates logic needed for `preview()` (per FR-PREV-003)
- Splits validation between session and pipeline
- Future direct pipeline callers would bypass

**Why not chosen**: Validation should be in the pipeline where all operations flow through, not in the session API layer.

### Alternative 3: Frozen/Immutable Collection Fields

**Description**: Make `tags`, `projects`, etc. immutable (frozen lists) so modifications fail immediately.

**Pros**:
- Immediate feedback (AttributeError on append)
- No runtime validation needed

**Cons**:
- Breaking change to Pydantic model structure
- Confusing error message ("'tuple' has no attribute 'append'")
- Doesn't provide actionable guidance
- Complicates deserialization from API responses

**Why not chosen**: Error experience is poor, and it's a larger change to the model layer than warranted.

### Alternative 4: Detect Only on Modified Fields, Not Full Comparison

**Description**: Instead of using `get_changes()`, check specific fields directly.

**Pros**:
- Potentially faster (only checks 4 fields)

**Cons**:
- Requires knowing which entities have which fields
- Duplicate comparison logic (already done in `get_changes()`)
- Harder to extend for new unsupported fields

**Why not chosen**: `get_changes()` already computes exactly what we need; no benefit to duplicating the logic.

## Consequences

### Positive

1. **Fail-fast**: Errors raised before any API calls, preventing partial commits
2. **Actionable errors**: Messages tell users exactly what to do instead
3. **Consistent behavior**: Both `preview()` and `commit()` detect the same issues
4. **Minimal code change**: Single validation method in SavePipeline
5. **Testable**: Easy to unit test with mocked ChangeTracker

### Negative

1. **Breaking change for silent-failure code**: Code that relied on silent ignoring will now fail
2. **Additional validation overhead**: Extra iteration over entities and changes per commit
3. **Error aggregation question**: First error throws vs. collect all errors

### Neutral

1. **New exception type**: `UnsupportedOperationError` added to exception hierarchy
2. **Documentation needed**: Clear guidance that collection fields require action methods

## Compliance

### Enforcement

- **Type hints**: `UnsupportedOperationError.field_name` is strongly typed
- **Unit tests**: Tests for each unsupported field type
- **Integration tests**: End-to-end tests confirming `preview()` and `commit()` both detect

### Documentation

- TDD-0011 specifies the validation flow
- Docstrings on Task model warn about unsupported direct modifications
- Error messages themselves serve as documentation

## Performance Considerations

Per NFR-PERF-003, detection should be < 1ms per entity.

The implementation iterates over:
1. All entities (N)
2. Changed fields per entity (typically < 10)
3. Lookup in 4-element set (O(1))

Total: O(N * 10 * 1) = O(N), with very low constant factors. For 1000 entities with 10 changes each, this is ~10,000 set lookups, well under 1ms.
