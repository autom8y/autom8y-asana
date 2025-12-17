# TDD-DESIGN-PATTERNS-D: Async/Sync Method Generator

| Field | Value |
|-------|-------|
| **ID** | TDD-DESIGN-PATTERNS-D |
| **Title** | Async/Sync Method Generator |
| **Status** | Active |
| **PRD** | PRD-DESIGN-PATTERNS-D |
| **Created** | 2025-12-16 |

---

## 1. Overview

This document specifies the technical design for the `@async_method` decorator that generates async/sync method pairs from a single async implementation.

### 1.1 Design Goals

1. **Single source of truth** - One async implementation generates both variants
2. **Full type safety** - IDE autocomplete and mypy compliance
3. **Zero behavior change** - Identical to hand-written methods
4. **Minimal API surface** - Simple decorator usage

---

## 2. Architecture

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     @async_method Decorator                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Developer writes:                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  @async_method                                             │  │
│  │  async def get(self, gid: str, *, raw: bool = False)       │  │
│  │      -> Section | dict[str, Any]:                          │  │
│  │      ...                                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  Decorator produces:                                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  get_async() -> Coroutine[..., Section | dict]            │  │
│  │  get() -> Section | dict  (sync wrapper)                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Design Approach: Descriptor Pattern

The decorator returns a **descriptor** that provides both `method_async` and `method` access:

```python
class AsyncMethodDescriptor(Generic[P, R]):
    """Descriptor providing async and sync access to a method."""

    def __init__(self, async_fn: Callable[P, Coroutine[Any, Any, R]]):
        self._async_fn = async_fn
        self._name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when descriptor is assigned to class attribute."""
        self._name = name

    def __get__(self, obj: Any, objtype: type | None = None) -> "BoundAsyncMethod[P, R]":
        """Return bound method wrapper when accessed on instance."""
        if obj is None:
            return self  # Class-level access
        return BoundAsyncMethod(obj, self._async_fn, self._name)
```

### 2.3 BoundAsyncMethod Class

```python
class BoundAsyncMethod(Generic[P, R]):
    """Bound method that provides both async and sync access."""

    def __init__(self, instance: Any, async_fn: Callable[P, Coroutine[Any, Any, R]], name: str):
        self._instance = instance
        self._async_fn = async_fn
        self._name = name

    async def async_(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Async execution - call the underlying coroutine."""
        return await self._async_fn(self._instance, *args, **kwargs)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Sync execution - wraps async in asyncio.run()."""
        # Check for async context
        try:
            asyncio.get_running_loop()
            raise SyncInAsyncContextError(
                method_name=self._name,
                async_method_name=f"{self._name}_async",
            )
        except RuntimeError:
            pass

        return asyncio.run(self._async_fn(self._instance, *args, **kwargs))
```

### 2.4 Alternative: Simpler Two-Method Approach

After analysis, a simpler approach that doesn't require descriptors:

```python
def async_method(fn: Callable[P, Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Mark an async method and generate sync wrapper.

    The decorated method becomes `method_async()`.
    A sync `method()` wrapper is generated automatically.
    """
    # Store metadata for class-level processing
    fn._is_async_method = True
    fn._sync_name = fn.__name__  # e.g., "get" -> sync name is "get"
    fn._async_name = f"{fn.__name__}_async"  # async name is "get_async"
    return fn


class AsyncMethodMeta(type):
    """Metaclass that processes @async_method decorators."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        for attr_name, attr_value in list(namespace.items()):
            if callable(attr_value) and getattr(attr_value, '_is_async_method', False):
                # Rename to _async
                async_name = attr_value._async_name
                sync_name = attr_value._sync_name

                # Create sync wrapper
                namespace[async_name] = attr_value
                namespace[sync_name] = _create_sync_wrapper(attr_value, async_name)

                # Remove original
                del namespace[attr_name]

        return super().__new__(mcs, name, bases, namespace)
```

**Decision**: Use the **Descriptor Pattern** (2.2/2.3) for maximum flexibility and no metaclass requirement.

---

## 3. Detailed Design

### 3.1 Core Types

```python
# src/autom8_asana/utils/async_method.py

from __future__ import annotations

import asyncio
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Generic,
    ParamSpec,
    TypeVar,
    overload,
)

from autom8_asana.exceptions import SyncInAsyncContextError

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


class AsyncSyncMethod(Generic[R]):
    """Descriptor that provides both async and sync access to a method.

    Usage:
        class MyClient:
            @AsyncSyncMethod.create
            async def get(self, gid: str) -> Model:
                return await self._http.get(f"/resource/{gid}")

        # Generates:
        # client.get_async(gid)  -> async
        # client.get(gid)        -> sync
    """

    def __init__(
        self,
        async_impl: Callable[..., Coroutine[Any, Any, R]],
    ) -> None:
        self._async_impl = async_impl
        self._name: str = ""
        self.__doc__ = async_impl.__doc__

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when descriptor assigned to class."""
        self._name = name

    @overload
    def __get__(self, obj: None, objtype: type) -> "AsyncSyncMethod[R]": ...

    @overload
    def __get__(self, obj: object, objtype: type | None) -> "BoundAsyncSyncMethod[R]": ...

    def __get__(
        self, obj: object | None, objtype: type | None = None
    ) -> "AsyncSyncMethod[R] | BoundAsyncSyncMethod[R]":
        if obj is None:
            return self
        return BoundAsyncSyncMethod(obj, self._async_impl, self._name)

    @staticmethod
    def create(fn: Callable[..., Coroutine[Any, Any, R]]) -> "AsyncSyncMethod[R]":
        """Decorator to create async/sync method pair."""
        return AsyncSyncMethod(fn)


class BoundAsyncSyncMethod(Generic[R]):
    """Bound method providing both async and sync execution."""

    __slots__ = ("_instance", "_async_impl", "_name")

    def __init__(
        self,
        instance: object,
        async_impl: Callable[..., Coroutine[Any, Any, R]],
        name: str,
    ) -> None:
        self._instance = instance
        self._async_impl = async_impl
        self._name = name

    async def __call__(self, *args: Any, **kwargs: Any) -> R:
        """Async execution (default when awaited)."""
        return await self._async_impl(self._instance, *args, **kwargs)

    def sync(self, *args: Any, **kwargs: Any) -> R:
        """Sync execution."""
        try:
            asyncio.get_running_loop()
            raise SyncInAsyncContextError(
                method_name=self._name,
                async_method_name=f"{self._name}_async",
            )
        except RuntimeError:
            pass
        return asyncio.run(self._async_impl(self._instance, *args, **kwargs))
```

### 3.2 Revised Design: Preserving Current API

The current API uses `method_async()` for async and `method()` for sync. The descriptor approach would change this to `method()` being awaitable. To preserve backward compatibility, we need a different approach.

**Final Design: Function-based decorator with class attribute injection**

```python
def async_method(fn: Callable[..., Coroutine[Any, Any, R]]) -> AsyncMethodPair[R]:
    """Decorator that creates async/sync method pair.

    The decorated method defines the async implementation.
    Two methods are exposed on the class:
    - `method_async()` - the async version
    - `method()` - the sync wrapper

    Usage:
        class SectionsClient(BaseClient):
            @async_method
            async def get(self, section_gid: str, *, raw: bool = False) -> Section | dict:
                '''Get a section by GID.'''
                params = self._build_opt_fields(opt_fields)
                data = await self._http.get(f"/sections/{section_gid}", params=params)
                if raw:
                    return data
                return Section.model_validate(data)

        # This creates:
        # - client.get_async(section_gid) -> async
        # - client.get(section_gid) -> sync
    """
    return AsyncMethodPair(fn)


class AsyncMethodPair(Generic[R]):
    """Descriptor that exposes both async and sync variants."""

    def __init__(self, async_impl: Callable[..., Coroutine[Any, Any, R]]) -> None:
        self._async_impl = async_impl
        self._name = async_impl.__name__
        self.__doc__ = async_impl.__doc__

    def __set_name__(self, owner: type, name: str) -> None:
        """Inject both method variants into the class."""
        self._name = name
        async_name = f"{name}_async"
        sync_name = name

        # Create the async method
        async_method = self._async_impl

        # Create the sync wrapper
        @wraps(self._async_impl)
        def sync_method(self_: Any, *args: Any, **kwargs: Any) -> R:
            try:
                asyncio.get_running_loop()
                raise SyncInAsyncContextError(
                    method_name=sync_name,
                    async_method_name=async_name,
                )
            except RuntimeError:
                pass
            return asyncio.run(async_method(self_, *args, **kwargs))

        sync_method.__doc__ = f"{self._async_impl.__doc__}\n\nSync wrapper."

        # Inject both into the class
        setattr(owner, async_name, async_method)
        setattr(owner, sync_name, sync_method)

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        """This should not be called - methods are injected in __set_name__."""
        raise AttributeError(
            f"AsyncMethodPair descriptor was not properly processed. "
            f"Method '{self._name}' should be accessed as '{self._name}_async' or '{self._name}'."
        )
```

### 3.3 Handling @overload for Raw Parameter

The challenge is that `@overload` must be written explicitly for type checkers - they cannot be generated at runtime. The solution is a **type stub pattern**:

**Option A: Explicit Overloads in Source (Recommended)**

```python
class SectionsClient(BaseClient):
    # Type overloads for IDE/mypy
    @overload
    async def get_async(
        self, section_gid: str, *, raw: Literal[False] = ...
    ) -> Section: ...

    @overload
    async def get_async(
        self, section_gid: str, *, raw: Literal[True]
    ) -> dict[str, Any]: ...

    # Implementation via decorator
    @async_method
    @error_handler
    async def get(
        self, section_gid: str, *, raw: bool = False
    ) -> Section | dict[str, Any]:
        '''Get a section by GID.'''
        ...
```

This reduces from 6 overloads to 2, and the implementation is defined once.

**Option B: Protocol-based typing (Complex)**

Define a Protocol that describes the overloaded behavior. This is complex and not recommended.

**Decision**: Use **Option A** - explicit overloads for async, auto-generate sync wrapper. This reduces code by ~60% while preserving full type safety.

---

## 4. Implementation Plan

### 4.1 File Structure

```
src/autom8_asana/
├── utils/
│   └── async_method.py      # New: @async_method decorator
├── clients/
│   ├── sections.py          # Migrate as proof of concept
│   └── ...
```

### 4.2 Migration Pattern

**Before** (current - ~71 lines per method with raw):
```python
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@error_handler
async def get_async(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    ...

@overload
def get(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

def get(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    return self._get_sync(gid, raw=raw)

@sync_wrapper("get_async")
async def _get_sync(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    if raw:
        return await self.get_async(gid, raw=True)
    return await self.get_async(gid, raw=False)
```

**After** (with @async_method - ~25 lines):
```python
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@overload
def get(self, gid: str, *, raw: Literal[False] = ...) -> Section: ...

@overload
def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

@async_method
@error_handler
async def get(self, gid: str, *, raw: bool = False) -> Section | dict[str, Any]:
    '''Get a section by GID.'''
    params = self._build_opt_fields(opt_fields)
    data = await self._http.get(f"/sections/{gid}", params=params)
    if raw:
        return data
    return Section.model_validate(data)
```

**Reduction**: From ~71 lines to ~25 lines (~65% reduction)

### 4.3 Methods Without Raw Parameter

For methods like `delete` that don't have overloads:

**Before** (~18 lines):
```python
@error_handler
async def delete_async(self, section_gid: str) -> None:
    await self._http.delete(f"/sections/{section_gid}")

@sync_wrapper("delete_async")
async def _delete_sync(self, section_gid: str) -> None:
    await self.delete_async(section_gid)

def delete(self, section_gid: str) -> None:
    self._delete_sync(section_gid)
```

**After** (~6 lines):
```python
@async_method
@error_handler
async def delete(self, section_gid: str) -> None:
    '''Delete a section.'''
    await self._http.delete(f"/sections/{section_gid}")
```

**Reduction**: From ~18 lines to ~6 lines (~67% reduction)

---

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# tests/unit/utils/test_async_method.py

class TestAsyncMethod:
    """Tests for @async_method decorator."""

    def test_creates_async_variant(self):
        """Verify method_async is created."""

    def test_creates_sync_variant(self):
        """Verify method (sync) is created."""

    def test_async_behavior_correct(self):
        """Verify async method executes as coroutine."""

    def test_sync_behavior_correct(self):
        """Verify sync method blocks and returns result."""

    def test_sync_in_async_context_raises(self):
        """Verify SyncInAsyncContextError raised when appropriate."""

    def test_preserves_docstring(self):
        """Verify docstring propagated to both variants."""

    def test_preserves_signature(self):
        """Verify parameter signatures preserved."""

    def test_works_with_error_handler(self):
        """Verify @error_handler integration."""

    def test_overload_typing(self):
        """Verify type overloads work correctly."""
```

### 5.2 Integration Tests

- Migrate SectionsClient and verify all existing tests pass
- No behavior changes observable to callers

---

## 6. ADR: Async Method Generation Strategy

### Decision

Use a **descriptor-based decorator** (`@async_method`) that:
1. Takes the base method name (e.g., `get`)
2. Generates `get_async()` and `get()` from single implementation
3. Requires explicit `@overload` declarations for `raw` parameter support
4. Integrates with `@error_handler` via decorator stacking

### Rationale

- **Descriptor pattern** allows clean injection of both methods
- **Explicit overloads** required because type checkers cannot see runtime-generated signatures
- **Decorator stacking** (`@async_method` + `@error_handler`) is familiar Python pattern
- **Backward compatible** - existing method signatures preserved

### Consequences

- **Positive**: ~65% code reduction per method
- **Positive**: Single source of truth for implementation
- **Positive**: Full type safety preserved
- **Negative**: Still requires overload declarations (but ~60% fewer)
- **Negative**: Decorator order matters (`@async_method` must be outermost)

---

## 7. References

- PRD-DESIGN-PATTERNS-D
- ADR-0002: Fail-fast async context detection
- Current @sync_wrapper implementation
- Current @error_handler implementation
