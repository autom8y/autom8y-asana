"""Async/sync method generator decorator.

Per TDD-DESIGN-PATTERNS-D: Provides @async_method decorator that generates
both async and sync variants from a single async implementation.

This eliminates massive code duplication in client methods (~65% reduction)
while preserving full type safety and IDE autocomplete.

Usage:
    class SectionsClient(BaseClient):
        # Type overloads (required for IDE support with raw parameter)
        @overload
        async def get_async(
            self, section_gid: str, *, raw: Literal[False] = ...
        ) -> Section: ...

        @overload
        async def get_async(
            self, section_gid: str, *, raw: Literal[True]
        ) -> dict[str, Any]: ...

        @overload
        def get(self, section_gid: str, *, raw: Literal[False] = ...) -> Section: ...

        @overload
        def get(self, section_gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

        # Single implementation generates both variants
        @async_method
        @error_handler
        async def get(
            self, section_gid: str, *, raw: bool = False
        ) -> Section | dict[str, Any]:
            '''Get a section by GID.'''
            params = self._build_opt_fields(opt_fields)
            data = await self._http.get(f"/sections/{section_gid}", params=params)
            if raw:
                return data
            return Section.model_validate(data)
"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    overload,
)

from autom8_asana.exceptions import SyncInAsyncContextError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

R = TypeVar("R")


class AsyncMethodPair(Generic[R]):
    """Descriptor that generates async and sync method variants.

    When assigned to a class, this descriptor injects two methods:
    - `{name}_async()` - the async variant
    - `{name}()` - the sync wrapper

    The sync wrapper detects async contexts and raises SyncInAsyncContextError
    per ADR-0002 (fail-fast behavior).

    Example:
        class MyClient:
            @async_method
            async def get(self, gid: str) -> Model:
                return await self._fetch(gid)

        # Creates:
        # - client.get_async(gid)  -> coroutine
        # - client.get(gid)        -> blocking result
    """

    __slots__ = ("_async_impl", "_name", "_doc")

    def __init__(self, async_impl: Callable[..., Coroutine[Any, Any, R]]) -> None:
        """Initialize with the async implementation function.

        Args:
            async_impl: The async function that implements the method logic.
        """
        self._async_impl = async_impl
        self._name = async_impl.__name__
        self._doc = async_impl.__doc__

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        """Return the docstring from the wrapped function."""
        return self._doc

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when descriptor is assigned to a class attribute.

        This is where we inject both the async and sync variants into the class.

        Args:
            owner: The class this descriptor is being assigned to.
            name: The attribute name being assigned.
        """
        self._name = name
        async_name = f"{name}_async"
        sync_name = name

        # Get the async implementation
        async_impl = self._async_impl

        # Create the sync wrapper
        @wraps(async_impl)
        def sync_wrapper(self_: Any, *args: Any, **kwargs: Any) -> R:
            """Sync execution of the async method.

            Raises:
                SyncInAsyncContextError: If called from within an async context.
            """
            # Check for async context per ADR-0002
            running_loop: asyncio.AbstractEventLoop | None = None
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running event loop - this is the expected case for sync usage
                pass

            if running_loop is not None:
                # There's a running loop - fail fast per ADR-0002
                raise SyncInAsyncContextError(
                    method_name=sync_name,
                    async_method_name=async_name,
                )

            # No event loop running - safe to use asyncio.run()
            return asyncio.run(async_impl(self_, *args, **kwargs))

        # Update sync wrapper metadata
        sync_wrapper.__doc__ = f"{async_impl.__doc__ or ''}\n\n(Sync wrapper - see {async_name} for async variant)"
        sync_wrapper.__name__ = sync_name

        # Inject both methods into the class
        setattr(owner, async_name, async_impl)
        setattr(owner, sync_name, sync_wrapper)

    @overload
    def __get__(self, obj: None, objtype: type) -> AsyncMethodPair[R]: ...

    @overload
    def __get__(self, obj: object, objtype: type | None) -> Any: ...

    def __get__(self, obj: object | None, objtype: type | None = None) -> Any:
        """Descriptor get - should not be called after __set_name__ processes.

        If this is called, it means the methods weren't properly injected.
        This can happen if the descriptor is accessed at the class level
        before __set_name__ completes.

        Args:
            obj: The instance (None for class access).
            objtype: The class type.

        Returns:
            Self for class-level access.

        Raises:
            AttributeError: If accessed on an instance (methods should exist).
        """
        if obj is None:
            # Class-level access - return self for introspection
            return self

        # Instance access - this shouldn't happen after __set_name__
        # The methods should be directly on the class
        raise AttributeError(
            f"AsyncMethodPair descriptor accessed incorrectly. "
            f"Method '{self._name}' should be accessed as "
            f"'{self._name}_async()' or '{self._name}()'."
        )


def async_method(fn: Callable[..., Coroutine[Any, Any, R]]) -> AsyncMethodPair[R]:
    """Decorator that creates async/sync method pair from single implementation.

    The decorated async function becomes the implementation for both:
    - `{name}_async()` - the async variant (original coroutine)
    - `{name}()` - the sync wrapper (blocks via asyncio.run)

    Type overloads must be declared separately for methods with `raw` parameter
    that changes return type. The decorator preserves docstrings and signatures.

    Args:
        fn: The async function to wrap.

    Returns:
        AsyncMethodPair descriptor that generates both variants.

    Example:
        # Without raw parameter (simple case)
        @async_method
        async def delete(self, gid: str) -> None:
            await self._http.delete(f"/resource/{gid}")

        # With raw parameter (requires explicit overloads)
        @overload
        async def get_async(self, gid: str, *, raw: Literal[False] = ...) -> Model: ...
        @overload
        async def get_async(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...
        @overload
        def get(self, gid: str, *, raw: Literal[False] = ...) -> Model: ...
        @overload
        def get(self, gid: str, *, raw: Literal[True]) -> dict[str, Any]: ...

        @async_method
        async def get(self, gid: str, *, raw: bool = False) -> Model | dict[str, Any]:
            data = await self._http.get(f"/resource/{gid}")
            return data if raw else Model.model_validate(data)

    Note:
        When stacking with @error_handler, @async_method must be outermost:

            @async_method  # Must be first (outermost)
            @error_handler
            async def get(self, gid: str) -> Model:
                ...
    """
    return AsyncMethodPair(fn)


__all__ = ["async_method", "AsyncMethodPair"]
