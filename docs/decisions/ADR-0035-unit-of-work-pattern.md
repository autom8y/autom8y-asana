# ADR-0035: Unit of Work Pattern for Save Orchestration

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-UOW-001 through FR-UOW-008), TDD-0010

## Context

The autom8_asana SDK currently uses immediate persistence where every API call executes immediately. PRD-0005 requires a Save Orchestration Layer that enables Django-ORM-style deferred saves where multiple model changes are collected and executed in optimized batches.

**Forces at play:**

1. **Developer Familiarity**: Django ORM's `session.add()` / `session.commit()` pattern is well-known
2. **Explicit Scope**: Developers need clear boundaries for which entities participate in a batch
3. **Resource Management**: HTTP connections, state tracking, and cleanup need proper lifecycle
4. **Error Handling**: Partial failures need to be captured and reported within a defined scope
5. **Async/Sync Duality**: SDK uses async-first with sync wrappers per ADR-0002

**Problem**: How should we structure the API for collecting and committing multiple entity changes?

## Decision

Implement the Unit of Work pattern via a **SaveSession class that acts as a context manager**.

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

The SaveSession:
- Enters via `__aenter__` / `__enter__` (returns session for use)
- Tracks entities explicitly via `session.track(entity)`
- Commits changes via `session.commit_async()` / `session.commit()`
- Exits via `__aexit__` / `__exit__` (marks session closed)

## Rationale

### Why Unit of Work Pattern

1. **Familiar Pattern**: Mirrors SQLAlchemy, Django ORM, and Entity Framework - developers understand the semantics immediately
2. **Explicit Scope**: Context manager provides clear "this is where batched operations happen" boundary
3. **State Isolation**: Each session tracks its own entities, preventing cross-session confusion
4. **Resource Cleanup**: Context manager guarantees cleanup even on exceptions
5. **Composable**: Multiple sessions can exist (though we don't encourage concurrent access to same entities)

### Why Context Manager Over Other APIs

**Context manager** provides:
- Automatic cleanup via `__exit__`
- Clear visual scope in code
- Exception handling boundary
- Pythonic idiom

**Alternative APIs considered and rejected:**
- Factory function (`create_session()`) - no automatic cleanup
- Global session (`client.session`) - stateful, confusing
- Decorator (`@batch_save`) - doesn't fit modification pattern

### Why Explicit `track()` Over Automatic Tracking

Per PRD-0005 Decision 1, tracking is opt-in. This requires explicit `session.track(entity)`:

1. **Predictable**: Only entities you explicitly add participate
2. **No Surprises**: Accidentally modified objects don't get saved
3. **Performance Control**: Developer decides what gets snapshotted
4. **Pythonic**: "Explicit is better than implicit"

## Alternatives Considered

### Alternative 1: Repository Pattern with Automatic Tracking

- **Description**: All entities fetched through repository are automatically tracked
- **Pros**: More "magical", less boilerplate
- **Cons**: Hidden behavior, performance surprises, requires model modification
- **Why not chosen**: Violates explicit tracking decision in PRD; would require model changes

### Alternative 2: Fluent Builder Pattern

- **Description**: `SaveBatch.add(task1).add(task2).execute()`
- **Pros**: Clean chaining syntax
- **Cons**: No context manager cleanup, less familiar, doesn't support modification-then-save pattern
- **Why not chosen**: Doesn't support the "modify entity, then commit changes" workflow

### Alternative 3: Transaction-Style API

- **Description**: `client.begin_transaction()` / `client.commit()` / `client.rollback()`
- **Pros**: Familiar from database transactions
- **Cons**: Asana doesn't support rollback, misleading semantics
- **Why not chosen**: Would imply atomicity/rollback that Asana cannot provide

### Alternative 4: Decorator-Based Batching

- **Description**: `@batch_operations def my_function(): ...`
- **Pros**: Clean syntax for function-scoped batching
- **Cons**: Doesn't work well with async, harder to return results, less flexible
- **Why not chosen**: Poor fit for async-first pattern, limited control flow

## Consequences

### Positive
- Familiar pattern for Python developers (SQLAlchemy, Django)
- Clear scope boundaries for batched operations
- Automatic resource cleanup via context manager
- Works naturally with both async and sync code
- Enables multiple sessions (e.g., for different operation groups)

### Negative
- Additional API surface (SaveSession class) to learn
- Requires explicit `track()` calls (more boilerplate than automatic)
- Session state machine adds complexity to implementation
- Cannot be used as a simple function call (requires context manager)

### Neutral
- Session is not thread-safe (document as single-thread use)
- Entity modifications between track() and commit() are detected via snapshots
- Session cannot be reused after context exit (prevents confusion)

## Compliance

How do we ensure this decision is followed?

1. **API Design**: SaveSession is the only public entry point for batched saves
2. **Documentation**: Examples show context manager usage exclusively
3. **Type Hints**: Methods return `SaveSession` enabling IDE guidance
4. **Linting**: Could add custom lint rule for SaveSession usage outside context manager
5. **Tests**: All tests use context manager pattern
