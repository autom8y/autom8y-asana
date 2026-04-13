"""Sync wrapper utilities for async methods."""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from autom8_asana.errors import SyncInAsyncContextError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

T = TypeVar("T")


def sync_wrapper(
    async_method_name: str,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., T]]:
    """Decorator factory to create sync wrappers for async methods.

    Per ADR-0002, this wrapper fails fast if called from an async context,
    directing users to the async variant instead.

    Args:
        async_method_name: Name of the async method (for error message)

    Returns:
        Decorator that wraps async function for sync usage

    Example:
        class TasksClient:
            async def get_async(self, task_gid: str) -> Task:
                ...

            @sync_wrapper("get_async")
            async def _get_impl(self, task_gid: str) -> Task:
                return await self.get_async(task_gid)

            def get(self, task_gid: str) -> Task:
                return self._get_impl(task_gid)
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
        """Decorator that wraps an async function for synchronous execution."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            """Execute the async function synchronously using asyncio.run()."""
            # Check if we're in an async context using get_running_loop()
            # This returns the loop if called from a coroutine/callback, or raises RuntimeError
            running_loop: asyncio.AbstractEventLoop | None = None
            try:  # noqa: SIM105 — must capture loop assignment; suppress() cannot assign
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running event loop - this is the expected case for sync usage
                pass

            if running_loop is not None:
                # There's a running loop - fail fast per ADR-0002
                raise SyncInAsyncContextError(
                    method_name=func.__name__.lstrip("_"),
                    async_method_name=async_method_name,
                )

            # No event loop running - safe to use asyncio.run()
            return asyncio.run(func(*args, **kwargs))

        return wrapper

    return decorator
