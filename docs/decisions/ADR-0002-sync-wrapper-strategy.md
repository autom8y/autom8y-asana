# ADR-0002: Fail-Fast Strategy for Sync Wrappers in Async Contexts

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-08
- **Deciders**: Architect, Principal Engineer
- **Related**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md), [TDD-0001](../design/TDD-0001-sdk-architecture.md), FR-SDK-003

## Context

The SDK is async-first (FR-SDK-002) but must provide sync wrappers for backward compatibility (FR-SDK-003). autom8's existing code is largely synchronous and calling `asyncio.run()` from sync code is straightforward.

However, a problem arises when sync wrappers are accidentally called from within an async context (e.g., inside an `async def` function). Consider:

```python
async def process_task(task_gid: str):
    # Developer mistakenly calls sync method instead of async
    task = client.tasks.get(task_gid)  # This is the sync wrapper
    return task
```

If the sync wrapper naively calls `asyncio.run()`, this raises:
```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

We need to decide how sync wrappers behave when called from an async context:

1. **Fail fast**: Detect the async context and raise an error immediately with guidance
2. **Nested event loop**: Use `nest_asyncio` or similar to allow nested `asyncio.run()`
3. **Thread delegation**: Run the async call in a separate thread with its own event loop
4. **Silent passthrough**: Just call the async method directly (but return a coroutine, breaking the contract)

## Decision

**Use fail-fast pattern: Detect async context and raise `RuntimeError` with clear guidance.**

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
```

Usage:

```python
class TasksClient:
    async def get_async(self, task_gid: str) -> Task:
        """Async method to get a task."""
        return await self._transport.get(f"/tasks/{task_gid}")

    @sync_wrapper
    async def _get_sync(self, task_gid: str) -> Task:
        return await self.get_async(task_gid)

    def get(self, task_gid: str) -> Task:
        """Sync wrapper for get_async."""
        return self._get_sync(task_gid)
```

What users see:

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

## Rationale

Fail-fast is the safest and most educational approach:

1. **Prevents hidden bugs**: Nested event loops or thread delegation might "work" but introduce subtle issues (deadlocks, resource leaks, performance problems).

2. **Clear error messages**: Developers immediately know what went wrong and how to fix it.

3. **Consistent behavior**: The sync method always behaves the same way based on context.

4. **No dependencies**: No need for `nest_asyncio` or complex thread management.

5. **Performance**: No overhead from thread creation or nested loops.

6. **Explicit > Implicit**: Following Python's philosophy, we make the async/sync boundary explicit rather than hiding it.

## Alternatives Considered

### Nested Event Loop (`nest_asyncio`)

- **Description**: Use `nest_asyncio.apply()` to patch asyncio and allow nested `asyncio.run()` calls.
- **Pros**:
  - Sync wrappers "just work" from anywhere
  - No code changes for callers
- **Cons**:
  - Monkey-patches asyncio globally (affects entire application)
  - Can hide architectural problems (sync code in async context)
  - Additional dependency
  - Known issues with some asyncio features
  - Performance overhead
- **Why not chosen**: Global monkey-patching is invasive and can cause subtle bugs. It papers over architectural issues rather than exposing them.

### Thread Delegation

- **Description**: Run async code in a new thread with its own event loop.
  ```python
  def sync_wrapper(async_func):
      def wrapper(*args, **kwargs):
          import concurrent.futures
          with concurrent.futures.ThreadPoolExecutor() as pool:
              future = pool.submit(asyncio.run, async_func(*args, **kwargs))
              return future.result()
      return wrapper
  ```
- **Pros**:
  - Works from any context
  - No global patching
- **Cons**:
  - Thread creation overhead for every call
  - Breaks connection pooling (connections aren't thread-safe)
  - Complicates resource cleanup
  - Rate limiter state not shared across threads
  - Much more complex implementation
- **Why not chosen**: Thread-per-call is expensive and breaks our connection/state sharing model.

### Silent Passthrough

- **Description**: In async context, just return the coroutine and let caller deal with it.
- **Pros**:
  - Simple implementation
- **Cons**:
  - Breaks the type contract (sync method returns coroutine)
  - Confusing behavior (sometimes returns result, sometimes coroutine)
  - Easy to miss the `await`, leading to unawaited coroutine warnings
- **Why not chosen**: Violates the principle of least surprise. The sync method should always return a result, not sometimes a coroutine.

### No Sync Wrappers

- **Description**: Only provide async API. Users handle sync themselves.
- **Pros**:
  - Simpler SDK code
  - No ambiguity
- **Cons**:
  - Breaks backward compatibility with autom8 (FR-SDK-003)
  - Forces all consumers to write their own sync wrappers
  - Poor developer experience for scripts and simple use cases
- **Why not chosen**: PRD requires sync wrappers for backward compatibility.

## Consequences

### Positive
- **Clear failure mode**: Developers know immediately when they've made a mistake
- **Actionable errors**: Error message tells them exactly what to do
- **No hidden complexity**: No threads, no monkey-patching, no magic
- **Type safety**: Sync methods always return the expected type
- **Performance**: Zero overhead in the happy path (sync from sync)

### Negative
- **Migration friction**: autom8 code transitioning to async will hit these errors
- **Can't mix sync/async freely**: Developers must be intentional about their context
- **Learning curve**: Developers new to async may be confused initially

### Neutral
- **Two method variants**: Each operation has both `method()` and `method_async()` (already planned)
- **Documentation burden**: Must clearly explain the async/sync boundary

## Compliance

To ensure this decision is followed:

1. **All sync wrappers use `sync_wrapper` decorator**: Code review checks for consistent pattern
2. **Error message includes method name**: Users know exactly which method to use
3. **Test coverage**: Unit tests verify behavior in both sync and async contexts
4. **Documentation**: README and docstrings explain async-first design and sync wrapper behavior
5. **Example code**: Show correct async and sync usage patterns
