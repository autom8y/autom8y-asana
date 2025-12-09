"""Default logging provider."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.protocols.log import CacheEventType


class DefaultLogProvider:
    """Default logging provider using Python's logging module.

    Creates a logger named 'autom8_asana' with standard configuration.
    Implements both LogProvider and CacheLoggingProvider protocols.
    """

    def __init__(
        self,
        level: int = logging.INFO,
        enable_cache_logging: bool = True,
    ) -> None:
        """Initialize logger.

        Args:
            level: Logging level (default INFO).
            enable_cache_logging: Whether to log cache events (default True).
                Set to False to silence cache event logging.
        """
        self._logger = logging.getLogger("autom8_asana")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self._logger.addHandler(handler)
        self._logger.setLevel(level)
        self._enable_cache_logging = enable_cache_logging

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._logger.exception(msg, *args, **kwargs)

    def log_cache_event(
        self,
        event_type: CacheEventType,
        key: str,
        entry_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a cache event for observability.

        Per ADR-0023, this method logs cache events for monitoring.
        Events are logged at DEBUG level to avoid noise in production.

        Args:
            event_type: Type of cache event (hit, miss, write, etc.).
            key: Cache key involved in the operation.
            entry_type: Entry type (task, subtasks, etc.) if applicable.
            metadata: Additional event metadata (latency_ms, version, etc.).
        """
        if not self._enable_cache_logging:
            return

        # Build structured log message
        event_data: dict[str, Any] = {
            "event": event_type,
            "key": key,
        }
        if entry_type:
            event_data["entry_type"] = entry_type
        if metadata:
            event_data.update(metadata)

        # Log at DEBUG level to avoid noise
        self._logger.debug("cache_event: %s", json.dumps(event_data))
