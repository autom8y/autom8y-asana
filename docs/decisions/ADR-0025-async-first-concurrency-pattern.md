# ADR-0025: Async-First Concurrency Pattern

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0002, ADR-0038
- **Related**: PRD-0001 (FR-SDK-002, FR-SDK-003), PRD-0005 (FR-UOW-004, NFR-COMPAT-002), TDD-0001, TDD-0010

## Context

The autom8_asana SDK must support both async and sync codebases while optimizing for I/O-bound operations against the Asana API. The SDK needs a consistent concurrency pattern that:

1. Maximizes performance for async-aware code through non-blocking I/O
2. Maintains backward compatibility with synchronous autom8 codebase
3. Prevents subtle bugs from nested event loops
4. Provides clear error messages when misused
5. Follows a single, maintainable implementation path

**The central problem**: How should the SDK handle sync wrappers when accidentally called from within an async context? If the sync wrapper naively calls `asyncio.run()`, it raises `RuntimeError: asyncio.run() cannot be called from a running event loop`.

**Forces at play**:
- I/O-bound HTTP operations benefit dramatically from async/await patterns
- Legacy autom8 code is largely synchronous
- Nested event loops can cause deadlocks, resource leaks, and performance problems
- Developers new to async may accidentally mix sync and async calls
- Thread-based solutions break connection pooling and rate limiter state
- Global monkey-patching (like `nest_asyncio`) can hide architectural issues

## Decision

**Implement async-first architecture with fail-fast sync wrappers across all I/O operations.**

All I/O-bound operations are implemented as async methods with thin sync wrappers that detect async context and fail fast with helpful error messages:

```python
from functools import wraps
import asyncio

def sync_wrapper(async_func):
    """Wrap an async function to be callable synchronously.

    Raises RuntimeError if called from within an async context,
    directing the user to use the async variant instead.
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
            # If we get here, there's an active event loop
            raise RuntimeError(
                f"Cannot call sync method '{async_func.__name__}' from async context. "
                f"Use 'await {async_func.__name__}_async(...)' instead."
            )
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                # No event loop running, safe to use asyncio.run()
                return asyncio.run(async_func(*args, **kwargs))
            # Re-raise our custom error or other RuntimeErrors
            raise
    return wrapper

class TasksClient:
    async def get_async(self, task_gid: str) -> Task:
        """Primary async implementation."""
        return await self._http.get(f"/tasks/{task_gid}")

    @sync_wrapper
    async def _get_sync(self, task_gid: str) -> Task:
        return await self.get_async(task_gid)

    def get(self, task_gid: str) -> Task:
        """Sync wrapper with fail-fast detection."""
        return self._get_sync(task_gid)
```

**Applied consistently across**:
- All HTTP client methods (GET, POST, PUT, DELETE)
- All resource clients (TasksClient, ProjectsClient, etc.)
- SaveSession commit operations
- All paginated list operations

## Rationale

### Why Async-First Over Sync-First

1. **Optimal for I/O**: Asana SDK is I/O-bound; async/await provides non-blocking HTTP operations
2. **Single implementation path**: Async logic written once, wrapped for sync compatibility
3. **Integration with async ecosystem**: BatchClient, rate limiter, connection pooling all benefit from async
4. **Scalability**: Multiple operations in different coroutines work efficiently
5. **Modern Python standard**: asyncio is the established pattern for I/O-bound operations

### Why Fail-Fast Over Nested Event Loops

**Fail-fast prevents hidden bugs**:
- Nested event loops might "work" but introduce deadlocks and resource leaks
- Clear error messages immediately guide developers to correct usage
- No global monkey-patching (`nest_asyncio`) that affects entire application
- No thread-per-call overhead that breaks connection pooling

**Clear failure mode**:
```python
# Sync context - works fine
def main():
    task = client.tasks.get("123")  # OK

# Async context - clear error
async def main():
    task = client.tasks.get("123")  # RuntimeError with helpful message
    # Error: Cannot call sync method 'get' from async context.
    #        Use 'await get_async(...)' instead.
```

### Why Not Thread Delegation

Thread-per-call would work from any context but:
- Thread creation overhead for every call
- Breaks connection pooling (connections aren't thread-safe)
- Rate limiter state not shared across threads
- Complicates resource cleanup
- Much more complex implementation

## Alternatives Considered

### Alternative 1: Nested Event Loop (`nest_asyncio`)

**Description**: Use `nest_asyncio.apply()` to patch asyncio globally and allow nested `asyncio.run()` calls.

**Pros**:
- Sync wrappers "just work" from anywhere
- No code changes for callers

**Cons**:
- Monkey-patches asyncio globally (affects entire application)
- Can hide architectural problems (sync code in async context)
- Additional dependency
- Known issues with some asyncio features
- Performance overhead

**Why not chosen**: Global monkey-patching is invasive and can cause subtle bugs. It papers over architectural issues rather than exposing them.

### Alternative 2: Thread Delegation

**Description**: Run async code in a new thread with its own event loop.

**Pros**:
- Works from any context
- No global patching

**Cons**:
- Thread creation overhead for every call
- Breaks connection pooling (connections aren't thread-safe)
- Complicates resource cleanup
- Rate limiter state not shared across threads
- Much more complex implementation

**Why not chosen**: Thread-per-call is expensive and breaks connection/state sharing model.

### Alternative 3: Sync-First with Async Wrapper

**Description**: Primary implementation is synchronous, with async wrappers.

**Pros**:
- Simpler mental model for sync-only developers

**Cons**:
- Violates I/O optimization principles
- Would require blocking HTTP calls
- Poor integration with async BatchClient
- Inconsistent with async ecosystem

**Why not chosen**: Async is optimal for I/O-bound operations; sync-first contradicts performance requirements.

### Alternative 4: Async-Only (No Sync Wrapper)

**Description**: Only provide async API, require all callers to use async.

**Pros**:
- Simpler implementation
- No wrapper complexity

**Cons**:
- Breaks compatibility with sync codebases
- Forces async adoption on all users
- Not meeting backward compatibility requirements

**Why not chosen**: PRD requires sync wrappers for backward compatibility with autom8.

## Consequences

### Positive

- **Clear failure mode**: Developers know immediately when they've made a mistake
- **Actionable errors**: Error message tells them exactly what to do
- **No hidden complexity**: No threads, no monkey-patching, no magic
- **Type safety**: Sync methods always return the expected type
- **Performance**: Zero overhead in the happy path (sync from sync, async from async)
- **Consistent pattern**: All I/O operations follow same pattern
- **Efficient non-blocking I/O**: Async enables concurrent operations

### Negative

- **Migration friction**: autom8 code transitioning to async will hit these errors
- **Can't mix sync/async freely**: Developers must be intentional about their context
- **Learning curve**: Developers new to async may be confused initially
- **Sync callers install event loop**: Handled transparently by `@sync_wrapper`

### Neutral

- **Two method variants**: Each operation has both `method()` and `method_async()`
- **Documentation burden**: Must clearly explain the async/sync boundary
- **Context manager dual support**: SaveSession supports both `async with` and `with`

## Implementation Patterns

### Standard Async-First Pattern

```python
class TasksClient:
    async def get_async(self, task_gid: str) -> Task:
        """Primary async implementation."""
        return await self._http.get(f"/tasks/{task_gid}")

    @sync_wrapper
    async def _get_sync(self, task_gid: str) -> Task:
        return await self.get_async(task_gid)

    def get(self, task_gid: str) -> Task:
        """Sync wrapper with fail-fast detection."""
        return self._get_sync(task_gid)
```

### SaveSession Dual Context Manager

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

    async def commit_async(self) -> SaveResult:
        """Primary async implementation."""
        # ... batch execution logic ...

    @sync_wrapper
    async def _commit_sync(self) -> SaveResult:
        return await self.commit_async()

    def commit(self) -> SaveResult:
        """Sync wrapper."""
        return self._commit_sync()
```

## Compliance

To ensure this decision is followed:

1. **Code Review**:
   - All sync wrappers use `@sync_wrapper` decorator
   - Error messages include method name and async alternative
   - No direct `asyncio.run()` calls in method implementations

2. **Test Coverage**:
   - Unit tests verify behavior in both sync and async contexts
   - Tests verify fail-fast error raised when sync called from async
   - Tests verify sync wrapper works in sync context

3. **Documentation**:
   - README explains async-first design
   - API docs show async examples first, sync as alternative
   - Docstrings document both `method()` and `method_async()`

4. **CI Enforcement**:
   - Test suite runs in both async and sync contexts
   - Code review rejects new sync implementations of I/O operations

## Cross-References

- **ADR-0010**: Sequential chunk execution uses async patterns
- **ADR-0039**: Save orchestration uses async-first per this decision
- **ADR-0115**: Parallel section fetch leverages async concurrency
- **ADR-SUMMARY-SAVESESSION**: Save operations follow this pattern
