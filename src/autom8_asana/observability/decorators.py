"""Error handler decorator for consistent error handling and correlation ID logging.

Per TDD-0007 and ADR-0013: Provides @error_handler decorator for client methods.
"""

from __future__ import annotations

import functools
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable, TypeVar, cast

from autom8_asana.observability.correlation import generate_correlation_id

if TYPE_CHECKING:
    from autom8_asana.protocols.log import LogProvider

T = TypeVar("T")


def error_handler(
    func: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[T]]:
    """Decorator for consistent error handling on client methods.

    Provides:
    1. Correlation ID generation and propagation
    2. Consistent error logging with context
    3. Exception enrichment with correlation data
    4. Operation timing (debug level)

    Expects the decorated method to be on a class with `_log` attribute
    (LogProvider | None) for logging.

    Per TDD-0007, this decorator is applied explicitly to async methods
    on client classes.

    Args:
        func: Async method to wrap.

    Returns:
        Wrapped async method with error handling.

    Example:
        class TasksClient(BaseClient):
            @error_handler
            async def get_async(self, task_gid: str) -> Task:
                ...
    """

    @functools.wraps(func)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
        """Execute the wrapped function with error handling and correlation tracking."""
        correlation_id = generate_correlation_id()
        operation = f"{self.__class__.__name__}.{func.__name__}"

        # Extract resource_gid from first positional arg if present
        resource_gid: str | None = None
        if args and isinstance(args[0], str):
            resource_gid = args[0]

        # Format operation string with optional resource GID
        if resource_gid:
            operation_str = f"{operation}({resource_gid})"
        else:
            operation_str = f"{operation}()"

        # Get log provider from instance
        log_provider: LogProvider | None = getattr(self, "_log", None)

        # Log start
        if log_provider:
            log_provider.debug(f"[{correlation_id}] {operation_str} starting")

        start_time = time.monotonic()

        try:
            result = await func(self, *args, **kwargs)
            elapsed = (time.monotonic() - start_time) * 1000

            if log_provider:
                log_provider.debug(
                    f"[{correlation_id}] {operation_str} completed in {elapsed:.0f}ms"
                )

            return result

        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000

            # Enrich exception with correlation context
            # Use object.__setattr__ to handle frozen exceptions
            try:
                e.correlation_id = correlation_id  # type: ignore[attr-defined]
            except AttributeError:
                # Exception may be immutable, try with object.__setattr__
                try:
                    object.__setattr__(e, "correlation_id", correlation_id)
                except (AttributeError, TypeError):
                    pass  # Some exceptions truly cannot be modified

            try:
                e.operation = operation  # type: ignore[attr-defined]
            except AttributeError:
                try:
                    object.__setattr__(e, "operation", operation)
                except (AttributeError, TypeError):
                    pass

            if log_provider:
                # Log error with correlation ID
                log_provider.error(
                    f"[{correlation_id}] {operation_str} failed: {e}"
                )

            raise

    return cast(Callable[..., Awaitable[T]], wrapper)
