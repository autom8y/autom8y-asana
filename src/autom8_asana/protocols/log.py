"""Logging provider protocol."""

from __future__ import annotations

from typing import Any, Literal, Protocol

# Valid cache event types for log_cache_event
CacheEventType = Literal[
    "hit", "miss", "write", "evict", "expire", "error", "overflow_skip"
]


class LogProvider(Protocol):
    """Protocol for logging, compatible with Python's logging.Logger.

    Any logging.Logger instance satisfies this protocol automatically.
    Custom implementations can add structured logging, correlation IDs, etc.

    The log_cache_event method is optional for backward compatibility.
    Standard logging.Logger instances will not have this method, but the
    SDK's DefaultLogProvider and custom implementations can provide it.
    """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        ...

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        ...


class CacheLoggingProvider(Protocol):
    """Extended logging protocol with cache event support.

    Per ADR-0023, this protocol adds cache observability through a
    dedicated log_cache_event method that consumers can implement
    to route cache metrics to their preferred destination.

    This is a separate protocol to maintain backward compatibility
    with standard logging.Logger instances.
    """

    def log_cache_event(
        self,
        event_type: CacheEventType,
        key: str,
        entry_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a cache event for observability.

        Per ADR-0023, this is a callback that consumers can implement
        to route cache metrics to their preferred destination
        (CloudWatch, DataDog, Prometheus, etc.).

        Args:
            event_type: Type of cache event (hit, miss, write, etc.).
            key: Cache key involved in the operation.
            entry_type: Entry type (task, subtasks, etc.) if applicable.
            metadata: Additional event metadata (latency_ms, version, etc.).

        Example:
            >>> log_provider.log_cache_event(
            ...     event_type="hit",
            ...     key="task:12345",
            ...     entry_type="task",
            ...     metadata={"latency_ms": 2.5},
            ... )
        """
        ...
