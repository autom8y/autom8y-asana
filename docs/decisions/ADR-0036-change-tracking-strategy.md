# ADR-0036: Change Tracking via Snapshot Comparison

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-CHANGE-001 through FR-CHANGE-009), TDD-0010, ADR-0035

## Context

The Save Orchestration Layer (PRD-0005) requires detecting which entities have been modified since they were registered for tracking. This "dirty detection" determines which entities need API calls at commit time.

**Forces at play:**

1. **Model Preservation**: Existing Pydantic models (AsanaResource) should not require modification
2. **Simplicity**: Solution should be easy to understand and maintain
3. **Correctness**: All field changes must be detected, including nested objects
4. **Performance**: Overhead should be minimal (< 10ms per entity per NFR-PERF-002)
5. **Field-Level Granularity**: Need to know which specific fields changed for minimal payloads
6. **Framework Compatibility**: Must work with Pydantic v2's ConfigDict and model_dump()

**Problem**: How should we detect changes to tracked entities?

## Decision

Use **snapshot comparison via `model_dump()`** for dirty detection.

When an entity is tracked:
1. Capture a snapshot: `snapshot = entity.model_dump()`
2. Store snapshot keyed by `id(entity)` (Python object identity)

At commit time:
1. Get current state: `current = entity.model_dump()`
2. Compare: `is_dirty = snapshot != current`
3. Compute changes: `{field: (old, new) for field in diff(snapshot, current)}`

```python
class ChangeTracker:
    def track(self, entity: AsanaResource) -> None:
        self._snapshots[id(entity)] = entity.model_dump()

    def is_dirty(self, entity: AsanaResource) -> bool:
        return self._snapshots[id(entity)] != entity.model_dump()

    def get_changes(self, entity: AsanaResource) -> dict[str, tuple[Any, Any]]:
        original = self._snapshots[id(entity)]
        current = entity.model_dump()
        return {k: (original[k], current[k])
                for k in original if original[k] != current[k]}
```

## Rationale

### Why Snapshot Comparison

1. **No Model Changes**: Works with existing Pydantic models as-is
2. **Simple Implementation**: Just dictionary comparison
3. **Reliable**: `model_dump()` is the canonical serialization in Pydantic v2
4. **Handles Nested Objects**: Dictionary comparison works recursively
5. **Field-Level Diff**: Easy to compute which fields changed

### Why Not Alternative Approaches

**`__setattr__` override** would:
- Require modifying AsanaResource base class
- Add complexity for handling all edge cases
- Risk breaking existing model behavior

**Pydantic validators** would:
- Only work at validation time, not field assignment
- Require model configuration changes
- Not capture all modification patterns

**Proxy/wrapper pattern** would:
- Add indirection complexity
- Require wrapping every tracked entity
- Complicate type hints and IDE support

### Performance Analysis

Snapshot comparison has O(n) cost where n = number of fields:
- Base Task model: ~15 fields
- With custom fields: ~25-50 fields
- `model_dump()` call: < 0.5ms typical
- Dictionary comparison: < 0.1ms typical
- **Total: < 1ms per entity**, well under 10ms NFR target

For 1000 entities, total overhead: < 1 second, acceptable.

### Object Identity via `id()`

We use `id(entity)` as the snapshot key because:
- Unique per object instance in Python
- Works for entities with or without GID
- Fast O(1) lookup
- No collision risk within a session lifetime

**Caveat**: If user creates new object with same data, it's a different entity. This is intentional - track() is per-object-instance.

## Alternatives Considered

### Alternative 1: `__setattr__` Override in AsanaResource

- **Description**: Override `__setattr__` to track modified fields immediately
- **Pros**: O(1) dirty check, immediate change tracking, no snapshot memory
- **Cons**:
  - Requires modifying base model
  - Complex edge cases (list append, nested object changes)
  - May interfere with Pydantic internals
  - Difficult to implement correctly
- **Why not chosen**: Too invasive; PRD specifies snapshot approach

### Alternative 2: Pydantic Model Validators

- **Description**: Use Pydantic's `model_validator` and `field_validator` to track changes
- **Pros**: Built into Pydantic, declarative
- **Cons**:
  - Validators run at construction/validation, not field assignment
  - Wouldn't catch `entity.name = "new"` without re-validation
  - Model modification required
- **Why not chosen**: Doesn't track post-construction modifications

### Alternative 3: Proxy Object Wrapper

- **Description**: Wrap each tracked entity in a proxy that intercepts attribute access
- **Pros**: Transparent change tracking, no model modification
- **Cons**:
  - Complex implementation
  - Type hint confusion (proxy vs real type)
  - Performance overhead on every access
  - Debugging difficulty
- **Why not chosen**: Over-engineering for the problem

### Alternative 4: Explicit Dirty Marking

- **Description**: Require `entity.mark_dirty()` or `session.mark_dirty(entity)` calls
- **Pros**: Maximum control, no overhead, simple implementation
- **Cons**:
  - Developer burden to remember
  - Error-prone (forget to mark)
  - Poor developer experience
- **Why not chosen**: Violates "automatic detection" requirement

### Alternative 5: Copy-on-Track (Deep Copy)

- **Description**: Make deep copy at track() time, compare objects later
- **Pros**: True object comparison, handles mutable nested objects
- **Cons**:
  - Higher memory (double storage)
  - Deep copy is expensive
  - Complex for circular references
- **Why not chosen**: model_dump() achieves same result more efficiently

## Consequences

### Positive
- Works with existing Pydantic models unchanged
- Simple, understandable implementation
- Reliable change detection for all field types
- Enables minimal update payloads (only changed fields)
- Low overhead (< 1ms per entity)

### Negative
- O(n) comparison cost (acceptable for typical entity sizes)
- Memory for snapshots (~1KB per entity typical)
- Cannot detect intermediate changes (only initial vs final)
- Object identity requirement documented but can confuse users

### Neutral
- Snapshot captured at track() time, not fetch time
- Changes to entities before track() are invisible
- Re-tracking same entity is idempotent (no re-snapshot)

## Compliance

How do we ensure this decision is followed?

1. **Implementation**: ChangeTracker uses model_dump() exclusively
2. **Unit Tests**: Verify all field types detected (string, int, list, nested)
3. **Documentation**: Explain snapshot timing in API docs
4. **Performance Tests**: Benchmark to confirm < 10ms overhead
5. **No Model Changes**: Code review rejects modifications to AsanaResource for tracking
