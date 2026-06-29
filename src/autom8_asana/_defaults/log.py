"""Default logging provider.

Per TDD-HARDENING-A/FR-LOG-003: Enhanced with `extra` support for structured logging.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from autom8y_log import sanitize_log_extra

if TYPE_CHECKING:
    from autom8_asana.protocols.log import CacheEventType


_STDLIB_LOG_KWARGS = frozenset({"exc_info", "stack_info", "stacklevel"})
"""Keyword arguments accepted by ``logging.Logger._log()``."""


class DefaultLogProvider:
    """Default logging provider using Python's logging module.

    Per TDD-HARDENING-A/FR-LOG-003: Enhanced with `extra` support for structured logging.

    Creates a logger named 'autom8_asana' with standard configuration.
    Implements both LogProvider and CacheLoggingProvider protocols.

    Example:
        from autom8_asana.observability import LogContext

        log = DefaultLogProvider()
        ctx = LogContext(correlation_id="abc123", operation="track")
        log.info("Processing entity %s", entity.gid, extra=ctx.to_dict())
    """

    def __init__(
        self,
        level: int = logging.INFO,
        enable_cache_logging: bool = True,
        name: str = "autom8_asana",
    ) -> None:
        """Initialize logger.

        Per FR-LOG-001: Logger naming via standard `__name__` pattern.

        Args:
            level: Logging level (default INFO).
            enable_cache_logging: Whether to log cache events (default True).
                Set to False to silence cache event logging.
            name: Logger name (default "autom8_asana").
        """
        self._logger = logging.getLogger(name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            self._logger.addHandler(handler)
        self._logger.setLevel(level)
        self._enable_cache_logging = enable_cache_logging

    @staticmethod
    def _sanitize_kwargs(
        extra: dict[str, Any] | None, kwargs: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Fold stray kwargs into ``extra`` and sanitize reserved ``LogRecord`` keys.

        Two failure modes are handled here, at the single chokepoint where
        ``extra`` is forwarded to stdlib ``logging`` (which rejects any ``extra``
        key that shadows a reserved ``LogRecord`` attribute with
        ``KeyError: "Attempt to overwrite '<key>' in LogRecord"``, raised inside
        the logger before any handler runs):

        1. External callers (e.g. ``autom8y_http``) may pass arbitrary keyword
           arguments like ``message=`` that stdlib ``Logger._log()`` rejects.
           Those are folded into ``extra`` so they don't break the call.
        2. Callers idiomatically pass reserved keys directly in ``extra``
           (e.g. ``extra={"name": ...}`` from the entity seeder). These reach
           stdlib unchanged and crash the log call — and, on a hot path like the
           cache warmer, the surrounding operation.

        Both the merged ``extra`` and any reserved keys are routed through the
        fleet-canonical :func:`autom8y_log.sanitize_log_extra`, which renames
        reserved keys to a safe ``extra_``-prefixed form (``name`` ->
        ``extra_name``) while preserving the value. Non-reserved keys pass
        through unchanged. The sanitizer is the single source of truth for the
        reserved-attribute set, so this provider does not duplicate that logic.
        """
        non_stdlib = {k: v for k, v in kwargs.items() if k not in _STDLIB_LOG_KWARGS}
        clean_kwargs = (
            kwargs
            if not non_stdlib
            else {k: v for k, v in kwargs.items() if k in _STDLIB_LOG_KWARGS}
        )

        # Fold stray (non-stdlib) kwargs into extra before sanitizing, so reserved
        # stray keys are renamed by the same canonical sanitizer as reserved
        # extra keys (no second, divergent reserved-key set to maintain).
        merged_extra: dict[str, Any] | None
        if non_stdlib:
            merged_extra = dict(extra) if extra else {}
            merged_extra.update(non_stdlib)
        else:
            merged_extra = extra

        return sanitize_log_extra(merged_extra), clean_kwargs

    def debug(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log debug message with optional structured context.

        Per FR-LOG-003: Supports `extra` parameter for structured logging.
        Per FR-LOG-005: Uses lazy %s formatting for zero-cost when disabled.

        Args:
            msg: Message format string (use %s placeholders).
            *args: Values to substitute into message.
            extra: Structured context dict (e.g., from LogContext.to_dict()).
            **kwargs: Additional keyword arguments for logger.
        """
        extra, kwargs = self._sanitize_kwargs(extra, kwargs)
        self._logger.debug(msg, *args, extra=extra, **kwargs)

    def info(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log info message with optional structured context.

        Per FR-LOG-003: Supports `extra` parameter for structured logging.
        Per FR-LOG-005: Uses lazy %s formatting for zero-cost when disabled.

        Args:
            msg: Message format string (use %s placeholders).
            *args: Values to substitute into message.
            extra: Structured context dict (e.g., from LogContext.to_dict()).
            **kwargs: Additional keyword arguments for logger.
        """
        extra, kwargs = self._sanitize_kwargs(extra, kwargs)
        self._logger.info(msg, *args, extra=extra, **kwargs)

    def warning(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log warning message with optional structured context.

        Per FR-LOG-003: Supports `extra` parameter for structured logging.
        Per FR-LOG-005: Uses lazy %s formatting for zero-cost when disabled.

        Args:
            msg: Message format string (use %s placeholders).
            *args: Values to substitute into message.
            extra: Structured context dict (e.g., from LogContext.to_dict()).
            **kwargs: Additional keyword arguments for logger.
        """
        extra, kwargs = self._sanitize_kwargs(extra, kwargs)
        self._logger.warning(msg, *args, extra=extra, **kwargs)

    def error(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log error message with optional structured context.

        Per FR-LOG-003: Supports `extra` parameter for structured logging.
        Per FR-LOG-005: Uses lazy %s formatting for zero-cost when disabled.

        Args:
            msg: Message format string (use %s placeholders).
            *args: Values to substitute into message.
            extra: Structured context dict (e.g., from LogContext.to_dict()).
            **kwargs: Additional keyword arguments for logger.
        """
        extra, kwargs = self._sanitize_kwargs(extra, kwargs)
        self._logger.error(msg, *args, extra=extra, **kwargs)

    def exception(
        self, msg: str, *args: Any, extra: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Log exception with traceback and optional structured context.

        Per FR-LOG-003: Supports `extra` parameter for structured logging.

        Args:
            msg: Message format string (use %s placeholders).
            *args: Values to substitute into message.
            extra: Structured context dict (e.g., from LogContext.to_dict()).
            **kwargs: Additional keyword arguments for logger.
        """
        extra, kwargs = self._sanitize_kwargs(extra, kwargs)
        self._logger.exception(msg, *args, extra=extra, **kwargs)

    def isEnabledFor(self, level: int) -> bool:
        """Check if logger is enabled for given level.

        Per FR-LOG-005: Use for expensive debug operations.

        Args:
            level: Logging level to check (e.g., logging.DEBUG).

        Returns:
            True if logger would emit at this level.

        Example:
            if log.isEnabledFor(logging.DEBUG):
                expensive_info = compute_debug_info()
                log.debug("Info: %s", expensive_info)
        """
        return self._logger.isEnabledFor(level)

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
        self._logger.debug(f"cache_event: {json.dumps(event_data)}")
