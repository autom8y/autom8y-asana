# ADR-0038: Async-First Concurrency for Save Operations

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-UOW-004, NFR-COMPAT-002), TDD-0010, ADR-0002

## Context

The Save Orchestration Layer needs to make HTTP requests to the Asana Batch API. The SDK already has an established concurrency pattern per ADR-0002: async-first with sync wrappers that fail fast when called from async contexts.

**Forces at play:**

1. **Consistency**: New features should follow established SDK patterns
2. **Performance**: Async enables non-blocking I/O for batch operations
3. **Compatibility**: Must work for both async and sync callers
4. **Simplicity**: Avoid complex threading or multiprocessing
5. **Integration**: Must work with existing BatchClient (which is async-first)

**Problem**: What concurrency model should SaveSession use?

## Decision

Use **async-first concurrency with sync wrappers**, consistent with ADR-0002.

Primary API is async:
```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = await session.commit_async()
```

Sync wrapper for non-async callers:
```python
with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = session.commit()  # Uses @sync_wrapper internally
```

Implementation details:
- `commit_async()` is the primary implementation
- `commit()` is a sync wrapper using `@sync_wrapper` decorator
- Context manager supports both `async with` and `with`
- All internal batch operations use async BatchClient

## Rationale

### Why Async-First

1. **Established Pattern**: ADR-0002 defined this pattern; consistency is critical
2. **BatchClient Integration**: BatchClient.execute_async() is the primary API
3. **Non-Blocking I/O**: Batch operations involve HTTP requests; async is natural fit
4. **Scalability**: Multiple SaveSessions in different coroutines work efficiently
5. **Modern Python**: asyncio is the standard for I/O-bound operations

### Why Sync Wrapper (Not Sync-First)

1. **ADR-0002 Compliance**: Sync wrappers use `@sync_wrapper` decorator
2. **Fail-Fast**: Sync wrappers detect async context and fail with helpful message
3. **Simple Implementation**: Single async implementation, thin sync wrapper
4. **No Code Duplication**: Async logic written once, wrapped for sync

### Context Manager Dual Support

SaveSession supports both `async with` and `with`:

```python
class SaveSession:
    async def __aenter__(self) -> "SaveSession":
        return self

    async def __aexit__(self, ...):
        self._state = SessionState.CLOSED

    def __enter__(self) -> "SaveSession":
        return self

    def __exit__(self, ...):
        self._state = SessionState.CLOSED
```

This is safe because:
- Entry/exit don't perform I/O (just state management)
- No async work needed in context manager protocol
- Both protocols just set state flags

### Thread Safety

SaveSession is **not thread-safe**. A single session should be used from a single thread/coroutine. This is acceptable because:
- Typical use: one session per operation/request
- Entity tracking via id() assumes stable object identity
- No documented use case for concurrent session access
- Thread-safety would add significant complexity

Document as: "SaveSession should be used from a single thread or coroutine."

## Alternatives Considered

### Alternative 1: Sync-First with Async Wrapper

- **Description**: Primary implementation is synchronous, with async wrappers
- **Pros**: Simpler mental model for sync-only developers
- **Cons**:
  - Violates ADR-0002 established pattern
  - Would require blocking HTTP calls
  - Poor integration with async BatchClient
  - Inconsistent with rest of SDK
- **Why not chosen**: Contradicts established pattern; BatchClient is async-first

### Alternative 2: Threading-Based Concurrency

- **Description**: Use ThreadPoolExecutor for batch operations
- **Pros**: Works in sync contexts without event loop
- **Cons**:
  - Complex thread safety requirements
  - GIL limits actual parallelism for CPU-bound work
  - Doesn't integrate well with async BatchClient
  - Different model from rest of SDK
- **Why not chosen**: Over-complicated; async is better for I/O

### Alternative 3: Multiprocessing

- **Description**: Use ProcessPoolExecutor for true parallelism
- **Pros**: True parallelism, bypasses GIL
- **Cons**:
  - Massive overhead for I/O-bound work
  - Serialization required for entities
  - Complex error handling
  - Overkill for HTTP requests
- **Why not chosen**: Entirely inappropriate for I/O-bound batch requests

### Alternative 4: Async-Only (No Sync Wrapper)

- **Description**: Only provide async API, require all callers to use async
- **Pros**: Simpler implementation, no wrapper complexity
- **Cons**:
  - Breaks compatibility with sync codebases
  - Forces async adoption on all users
  - Inconsistent with SDK's dual-mode pattern
- **Why not chosen**: SDK explicitly supports both modes per ADR-0002

## Consequences

### Positive
- Consistent with established SDK pattern (ADR-0002)
- Efficient non-blocking I/O for batch operations
- Works for both async and sync callers
- Simple implementation (async primary, sync wrapper)
- Integrates naturally with async BatchClient

### Negative
- Sync callers must install event loop machinery (handled by @sync_wrapper)
- Not thread-safe (documented limitation)
- Sync wrapper adds small overhead vs direct async

### Neutral
- Context manager works identically for async/sync (just state flags)
- Internal pipeline is fully async
- Performance characteristics same as existing SDK patterns

## Compliance

How do we ensure this decision is followed?

1. **Implementation**: Use @sync_wrapper decorator for all sync methods
2. **Tests**: Test both async and sync usage patterns
3. **Documentation**: Show async examples first, sync as alternative
4. **Code Review**: Reject new sync implementations of I/O operations
5. **CI**: Test in both async and sync contexts
