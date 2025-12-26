# ADR-0040: SaveSession Unit of Work Pattern & Change Tracking

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-10
- **Consolidated From**: ADR-0035, ADR-0036
- **Related**: [reference/SAVESESSION.md](/Users/tomtenuta/Code/autom8_asana/docs/decisions/reference/SAVESESSION.md), PRD-0005, TDD-0010

## Context

The autom8_asana SDK required a deferred persistence layer enabling Django-ORM-style batch operations where multiple model changes are collected and executed in optimized batches. Two foundational questions needed resolution:

1. **How should we structure the API** for collecting and committing multiple entity changes?
2. **How should we detect changes** to tracked entities without modifying existing Pydantic models?

Forces at play:
- Developer familiarity with ORM patterns (SQLAlchemy, Django)
- Explicit scope boundaries for batch operations
- Resource management and cleanup guarantees
- No modification of existing Pydantic models permitted
- Performance overhead must remain under 10ms per entity
- Field-level change granularity needed for minimal update payloads
- Async-first consistency with ADR-0002

## Decision

### Unit of Work Pattern via Context Manager

Implement SaveSession as a context manager with explicit `track()` and `commit()` lifecycle:

```python
# Async usage (primary)
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = await session.commit_async()

# Sync usage (wrapper)
with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = session.commit()
```

**API Characteristics:**
- Context manager provides automatic cleanup via `__exit__`
- Explicit `track()` registration for predictable entity participation
- State isolation per session prevents cross-session confusion
- Not thread-safe; documented for single-thread/coroutine use

### Snapshot-Based Change Tracking

Use `model_dump()` comparison for dirty detection:

```python
class ChangeTracker:
    def track(self, entity: AsanaResource) -> None:
        # Capture snapshot at track() time
        self._snapshots[id(entity)] = entity.model_dump()

    def is_dirty(self, entity: AsanaResource) -> bool:
        # Compare current state to snapshot
        return self._snapshots[id(entity)] != entity.model_dump()

    def get_changes(self, entity: AsanaResource) -> dict[str, tuple[Any, Any]]:
        # Field-level diff for minimal payloads
        original = self._snapshots[id(entity)]
        current = entity.model_dump()
        return {k: (original[k], current[k])
                for k in original if original[k] != current[k]}
```

**Implementation Details:**
- Snapshot captured using Pydantic v2's `model_dump()`
- Object identity via `id(entity)` as snapshot key
- O(n) comparison cost where n = number of fields (< 1ms typical)
- Enables field-level diff for minimal update payloads

## Rationale

### Why Unit of Work Pattern

1. **Familiar Pattern**: Mirrors SQLAlchemy and Django ORM - developers understand semantics immediately
2. **Explicit Scope**: Context manager provides clear "batch operation boundary"
3. **State Isolation**: Each session tracks its own entities independently
4. **Resource Cleanup**: Context manager guarantees cleanup even on exceptions
5. **Composable**: Multiple sessions possible (though same-entity access discouraged)
6. **Pythonic**: "Explicit is better than implicit" - no automatic tracking surprises

**Rejected Alternatives:**
- **Repository Pattern with Automatic Tracking**: Too magical, performance surprises, requires model modification
- **Fluent Builder Pattern**: Doesn't support modify-then-save workflow
- **Transaction-Style API**: Misleading - Asana doesn't support rollback
- **Decorator-Based Batching**: Poor fit for async-first pattern

### Why Snapshot Comparison

1. **No Model Changes**: Works with existing Pydantic models unchanged
2. **Simple Implementation**: Just dictionary comparison
3. **Reliable**: `model_dump()` is canonical serialization in Pydantic v2
4. **Handles Nested Objects**: Dictionary comparison works recursively
5. **Field-Level Diff**: Easy to compute exactly what changed

**Performance Analysis:**
- Base Task model: ~15 fields → < 0.5ms
- With custom fields: ~50 fields → < 1ms
- 1000 entities: < 1 second total overhead (acceptable)

**Rejected Alternatives:**
- **`__setattr__` Override**: Too invasive, complex edge cases, risks breaking Pydantic internals
- **Pydantic Validators**: Only run at validation time, not field assignment
- **Proxy/Wrapper Pattern**: Over-engineering, type hint confusion
- **Explicit Dirty Marking**: Poor developer experience, error-prone

## Alternatives Considered

### Alternative 1: Global Session with Automatic Tracking

**Description**: All entities fetched through client automatically tracked in global session.

**Pros**: Magical, minimal boilerplate, familiar from some ORMs

**Cons**:
- Hidden behavior leads to unexpected saves
- Performance surprises from large automatic snapshots
- Requires model modifications
- Violates explicit tracking requirement in PRD
- Complex state management across application

**Why not chosen**: "Explicit is better than implicit" - automatic tracking creates more problems than it solves.

### Alternative 2: Deep Copy for Change Detection

**Description**: Make deep copy at `track()` time, compare objects later.

**Pros**: True object comparison, handles mutable nested objects

**Cons**:
- Double memory footprint
- Deep copy is expensive for complex object graphs
- Complex handling for circular references
- `model_dump()` achieves same result more efficiently

**Why not chosen**: Snapshot via `model_dump()` provides same functionality with better performance and simpler implementation.

### Alternative 3: Dirty Flag on Models

**Description**: Add `_is_dirty` flag to AsanaResource base class, set on field changes.

**Pros**: O(1) dirty check, immediate change detection, minimal memory

**Cons**:
- Requires modifying base model (violates constraint)
- Complex to implement correctly for all field types
- Doesn't capture which fields changed
- May interfere with Pydantic internals

**Why not chosen**: Modifying Pydantic models creates maintenance burden and risks breaking changes.

## Consequences

### Positive

- **Familiar API**: Django/SQLAlchemy developers immediately productive
- **Explicit Control**: Developers know exactly what participates in batch
- **Automatic Cleanup**: Context manager handles resource management
- **No Model Changes**: Works with existing Pydantic models unchanged
- **Field-Level Diffs**: Enables minimal update payloads
- **Low Overhead**: < 1ms per entity meets performance requirements
- **Reliable Detection**: All field changes captured including nested objects

### Negative

- **Additional Boilerplate**: Requires explicit `track()` calls
- **Learning Curve**: New API surface to learn
- **O(n) Comparison**: Acceptable for typical sizes but grows with fields
- **Object Identity Dependency**: Users must understand `id()` semantics
- **Cannot Detect Intermediate Changes**: Only initial vs final state

### Neutral

- **Session Not Thread-Safe**: Documented as single-thread use
- **Snapshot Timing**: Captured at `track()` time, not fetch time
- **Re-tracking Idempotent**: Multiple `track()` calls on same entity safe
- **Session Not Reusable**: Cannot use after context exit (prevents confusion)

## Compliance

### Enforcement

1. **API Design**: SaveSession is only public entry point for batched saves
2. **Type Hints**: All methods properly annotated for IDE support
3. **Documentation**: Examples show context manager usage exclusively
4. **Tests**: All tests use context manager pattern and verify change detection
5. **Performance Benchmarks**: Automated tests verify < 10ms overhead per entity

### Validation

**Unit Tests Verify:**
- Context manager lifecycle (`__enter__`, `__exit__`, `__aenter__`, `__aexit__`)
- Explicit tracking behavior (only tracked entities participate)
- Snapshot comparison accuracy (all field types detected)
- Field-level diff computation
- Performance targets met

**Integration Tests Verify:**
- Batch operations execute correctly
- Multiple sessions can coexist
- Resource cleanup on exceptions
- Works with real Pydantic models

## Implementation Guidance

### When to Use Explicit SaveSession

**Use explicit context for:**
- Batch operations (multiple entities)
- Complex workflows requiring preview
- Operations needing transaction-like boundaries
- Custom error handling requirements

```python
async with SaveSession(client) as session:
    for task in tasks:
        session.track(task)
        task.name = f"Updated {task.name}"

    # Preview before committing
    ops, actions = session.preview()
    print(f"Will execute {len(ops)} operations")

    result = await session.commit_async()
```

### Change Detection Patterns

**Detecting Modifications:**
```python
# Track baseline state
session.track(task)

# Modify entity
task.name = "New Name"
task.due_on = "2025-01-15"

# Check if dirty
if session.is_dirty(task):
    changes = session.get_changes(task)
    # {'name': ('Old Name', 'New Name'),
    #  'due_on': (None, '2025-01-15')}
```

**Object Identity Considerations:**
```python
# Same entity tracked - idempotent
task = await client.tasks.get_async("123")
session.track(task)
session.track(task)  # Safe, no duplicate

# Different object instance - separate tracking
task1 = await client.tasks.get_async("123")
task2 = await client.tasks.get_async("123")
session.track(task1)
session.track(task2)  # Both tracked independently
```

## Cross-References

**Related ADRs:**
- ADR-0041: Dependency Ordering & Concurrency (builds on this foundation)
- ADR-0042: Error Handling & Partial Failures (uses SaveResult from commits)
- ADR-0043: Action Operations Architecture (extends track/commit pattern)

**Related Documents:**
- PRD-0005: Save Orchestration Layer requirements
- TDD-0010: Save Orchestration technical design
- REF-savesession-lifecycle: Session state machine details
- REF-entity-lifecycle: Entity state from creation through persistence
