"""Structured JSON logging for polling automation.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Provides structured logging with JSON
output format for rule evaluation, automation results, and scheduler events.

Features:
- JSON-formatted log output for machine parsing
- Graceful fallback to stdlib logging if structlog not installed
- Context binding for correlation across log entries
- Specialized methods for rule evaluation and automation results

Example - Configure and Use:
    from autom8_asana.automation.polling import StructuredLogger

    # Configure once at application startup
    StructuredLogger.configure(json_format=True, level="INFO")

    # Get logger with bound context
    logger = StructuredLogger.get_logger(scheduler_id="daily-poll")
    logger.info("Scheduler started")

    # Log rule evaluation
    StructuredLogger.log_rule_evaluation(
        rule_id="stale-task-escalation",
        rule_name="Escalate Stale Triage Tasks",
        project_gid="1234567890123",
        matches=5,
        duration_ms=150.0,
    )

Example - JSON Output:
    {
        "timestamp": "2024-01-15T02:00:00.000000Z",
        "level": "info",
        "event": "rule_evaluation_complete",
        "rule_id": "stale-task-escalation",
        "rule_name": "Escalate Stale Triage Tasks",
        "project_gid": "1234567890123",
        "matches": 5,
        "duration_ms": 150.0
    }
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.automation.polling.action_executor import ActionResult
    from autom8_asana.persistence.models import AutomationResult

__all__ = ["StructuredLogger"]

# Attempt to import structlog, set flag for fallback behavior
_STRUCTLOG_AVAILABLE = False
try:
    import structlog

    _STRUCTLOG_AVAILABLE = True
except ImportError:
    structlog = None  # type: ignore[assignment]


class StructuredLogger:
    """JSON-structured logger for polling automation.

    Provides structured logging with JSON output format. Uses structlog when
    available, falling back gracefully to stdlib logging with JSON-like
    formatting when structlog is not installed.

    All methods are class methods to provide a singleton-like interface
    without requiring instance management.

    Example:
        StructuredLogger.configure(json_format=True)
        logger = StructuredLogger.get_logger(component="scheduler")
        logger.info("evaluation_started", rule_count=5)
    """

    _configured: bool = False
    _json_format: bool = True
    _level: str = "INFO"

    @classmethod
    def configure(
        cls,
        *,
        json_format: bool = True,
        level: str = "INFO",
    ) -> None:
        """Configure structlog for the application.

        Configures either structlog (preferred) or stdlib logging (fallback)
        based on package availability. Should be called once at application
        startup before any logging occurs.

        Args:
            json_format: If True, output logs as JSON. If False, use human-
                readable format. Only affects structlog; stdlib fallback
                always uses a JSON-like string format.
            level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                Defaults to INFO.

        Example:
            StructuredLogger.configure(json_format=True, level="DEBUG")
        """
        cls._json_format = json_format
        cls._level = level.upper()

        if _STRUCTLOG_AVAILABLE:
            cls._configure_structlog(json_format, cls._level)
        else:
            cls._configure_stdlib(cls._level)

        cls._configured = True

    @classmethod
    def _configure_structlog(cls, json_format: bool, level: str) -> None:
        """Configure structlog with processors and renderers.

        Args:
            json_format: Whether to use JSON output format.
            level: Log level string.
        """
        # Build processor chain
        shared_processors: list[Any] = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
        ]

        if json_format:
            # JSON output for machine parsing
            shared_processors.append(structlog.processors.JSONRenderer())
        else:
            # Human-readable console output
            shared_processors.append(structlog.dev.ConsoleRenderer())

        # Configure structlog
        structlog.configure(
            processors=shared_processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure stdlib logging for structlog integration
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, level, logging.INFO),
        )

    @classmethod
    def _configure_stdlib(cls, level: str) -> None:
        """Configure stdlib logging as fallback.

        Uses a simple format since the _StdlibLoggerAdapter handles
        JSON formatting. We only pass through the message content.

        Args:
            level: Log level string.
        """
        # Simple format - _StdlibLoggerAdapter handles JSON structure
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, level, logging.INFO),
        )

    @classmethod
    def get_logger(cls, **bound_context: Any) -> Any:
        """Get a logger with bound context.

        Returns a structlog logger (if available) or stdlib logger with
        bound context values that will be included in all subsequent log
        entries from this logger instance.

        Args:
            **bound_context: Key-value pairs to bind to all log entries.
                Common context: scheduler_id, rule_id, project_gid.

        Returns:
            A logger instance (structlog.BoundLogger or _StdlibLoggerAdapter).
            The logger supports standard methods: debug, info, warning, error.

        Example:
            logger = StructuredLogger.get_logger(
                scheduler_id="daily-poll",
                timezone="America/New_York",
            )
            logger.info("Starting evaluation cycle")
            # Output includes scheduler_id and timezone in context
        """
        if not cls._configured:
            # Auto-configure with defaults on first use
            cls.configure()

        if _STRUCTLOG_AVAILABLE:
            return structlog.get_logger().bind(**bound_context)
        else:
            # Return adapted stdlib logger
            return _StdlibLoggerAdapter(
                logging.getLogger("autom8_asana.automation.polling"),
                bound_context,
            )

    @classmethod
    def log_rule_evaluation(
        cls,
        rule_id: str,
        rule_name: str,
        project_gid: str,
        matches: int,
        duration_ms: float,
    ) -> None:
        """Log rule evaluation result.

        Logs a structured event when a rule has been evaluated against
        a project's tasks. Includes timing information for performance
        monitoring.

        Args:
            rule_id: Unique identifier of the evaluated rule.
            rule_name: Human-readable name of the rule.
            project_gid: GID of the project containing evaluated tasks.
            matches: Number of tasks that matched the rule conditions.
            duration_ms: Time taken to evaluate the rule in milliseconds.

        Example:
            StructuredLogger.log_rule_evaluation(
                rule_id="escalate-stale",
                rule_name="Escalate Stale Triage",
                project_gid="1234567890123",
                matches=5,
                duration_ms=125.5,
            )

        Output (JSON):
            {
                "timestamp": "2024-01-15T02:00:00.000000Z",
                "level": "info",
                "event": "rule_evaluation_complete",
                "rule_id": "escalate-stale",
                "rule_name": "Escalate Stale Triage",
                "project_gid": "1234567890123",
                "matches": 5,
                "duration_ms": 125.5
            }
        """
        logger = cls.get_logger()

        if _STRUCTLOG_AVAILABLE:
            logger.info(
                "rule_evaluation_complete",
                rule_id=rule_id,
                rule_name=rule_name,
                project_gid=project_gid,
                matches=matches,
                duration_ms=duration_ms,
            )
        else:
            # Stdlib fallback: format as JSON-like string
            logger.info(
                "rule_evaluation_complete",
                rule_id=rule_id,
                rule_name=rule_name,
                project_gid=project_gid,
                matches=matches,
                duration_ms=duration_ms,
            )

    @classmethod
    def log_action_result(
        cls,
        result: "ActionResult",
        *,
        rule_id: str | None = None,
    ) -> None:
        """Log ActionResult from action execution.

        Logs the outcome of an action execution on a single task,
        including success/failure status and any error messages.

        Args:
            result: ActionResult from ActionExecutor.execute_async().
            rule_id: Optional rule identifier for context.

        Example:
            from autom8_asana.automation.polling import ActionResult

            result = ActionResult(
                success=True,
                action_type="add_tag",
                task_gid="task-123",
                details={"tag_gid": "tag-456"},
            )
            StructuredLogger.log_action_result(result, rule_id="escalate-stale")

        Output (JSON):
            {
                "timestamp": "2024-01-15T02:00:05.000000Z",
                "level": "info",
                "event": "action_executed",
                "task_gid": "task-123",
                "action_type": "add_tag",
                "success": true,
                "rule_id": "escalate-stale",
                "details": {"tag_gid": "tag-456"}
            }
        """
        logger = cls.get_logger()

        # Determine event name and log level based on outcome
        if result.success:
            event = "action_executed"
            level = "info"
        else:
            event = "action_failed"
            level = "error"

        # Build context dict
        context: dict[str, Any] = {
            "task_gid": result.task_gid,
            "action_type": result.action_type,
            "success": result.success,
        }

        # Add optional fields
        if rule_id:
            context["rule_id"] = rule_id
        if result.details:
            context["details"] = result.details
        if result.error:
            context["error"] = result.error

        # Log at appropriate level
        log_method = getattr(logger, level)
        log_method(event, **context)

    @classmethod
    def log_automation_result(
        cls,
        result: AutomationResult,
    ) -> None:
        """Log AutomationResult with full structured context.

        Logs the complete outcome of an automation rule execution,
        including success/failure status, actions executed, entities
        affected, and timing information.

        Args:
            result: AutomationResult from rule execution containing:
                - rule_id, rule_name: Rule identification
                - triggered_by_gid, triggered_by_type: Triggering entity
                - actions_executed: List of action types run
                - entities_created, entities_updated: Affected entities
                - success, error: Execution outcome
                - execution_time_ms: Performance timing
                - skipped_reason: If rule was skipped (loop prevention)

        Example:
            from autom8_asana.persistence.models import AutomationResult

            result = AutomationResult(
                rule_id="escalate-stale",
                rule_name="Escalate Stale Triage",
                triggered_by_gid="task-123",
                triggered_by_type="Task",
                actions_executed=["add_tag"],
                success=True,
                execution_time_ms=50.0,
            )
            StructuredLogger.log_automation_result(result)

        Output (JSON):
            {
                "timestamp": "2024-01-15T02:00:05.000000Z",
                "level": "info",
                "event": "automation_result",
                "rule_id": "escalate-stale",
                "rule_name": "Escalate Stale Triage",
                "triggered_by_gid": "task-123",
                "triggered_by_type": "Task",
                "actions_executed": ["add_tag"],
                "entities_created": [],
                "entities_updated": [],
                "success": true,
                "execution_time_ms": 50.0
            }
        """
        logger = cls.get_logger()

        # Determine log level based on outcome
        if result.was_skipped:
            level = "info"
            event = "automation_skipped"
        elif result.success:
            level = "info"
            event = "automation_succeeded"
        else:
            level = "error"
            event = "automation_failed"

        # Build context dict
        context: dict[str, Any] = {
            "rule_id": result.rule_id,
            "rule_name": result.rule_name,
            "triggered_by_gid": result.triggered_by_gid,
            "triggered_by_type": result.triggered_by_type,
            "actions_executed": result.actions_executed,
            "entities_created": result.entities_created,
            "entities_updated": result.entities_updated,
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
        }

        # Add optional fields if present
        if result.error:
            context["error"] = result.error
        if result.skipped_reason:
            context["skipped_reason"] = result.skipped_reason
        if result.enhancement_results:
            context["enhancement_results"] = result.enhancement_results

        # Log at appropriate level
        if _STRUCTLOG_AVAILABLE:
            log_method = getattr(logger, level)
            log_method(event, **context)
        else:
            # Stdlib fallback
            log_method = getattr(logger, level)
            log_method(event, **context)


class _StdlibLoggerAdapter:
    """Adapter to make stdlib logger behave like structlog.

    Provides structlog-like interface for stdlib logging when structlog
    is not installed. Handles bound context and keyword argument logging.
    """

    def __init__(
        self,
        logger: logging.Logger,
        bound_context: dict[str, Any],
    ) -> None:
        """Initialize adapter with logger and bound context.

        Args:
            logger: Stdlib Logger instance.
            bound_context: Initial bound context dict.
        """
        self._logger = logger
        self._bound_context = bound_context.copy()

    def bind(self, **new_context: Any) -> "_StdlibLoggerAdapter":
        """Return new adapter with additional bound context.

        Args:
            **new_context: Additional context to bind.

        Returns:
            New adapter with merged context.
        """
        merged = {**self._bound_context, **new_context}
        return _StdlibLoggerAdapter(self._logger, merged)

    def _format_message(self, event: str, **context: Any) -> str:
        """Format message with context as JSON-like string.

        Args:
            event: Event name/message.
            **context: Additional context for this log entry.

        Returns:
            Formatted message string.
        """
        # Merge bound context with call-time context
        full_context = {**self._bound_context, **context}

        # Build JSON-like parts
        parts = [f'"event": "{event}"']
        for key, value in full_context.items():
            if isinstance(value, str):
                parts.append(f'"{key}": "{value}"')
            elif isinstance(value, (list, dict)):
                # Simple JSON representation
                import json

                parts.append(f'"{key}": {json.dumps(value)}')
            else:
                parts.append(f'"{key}": {value}')

        # Add timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        parts.insert(0, f'"timestamp": "{timestamp}"')

        return "{" + ", ".join(parts) + "}"

    def debug(self, event: str, **context: Any) -> None:
        """Log at DEBUG level."""
        self._logger.debug(self._format_message(event, **context))

    def info(self, event: str, **context: Any) -> None:
        """Log at INFO level."""
        self._logger.info(self._format_message(event, **context))

    def warning(self, event: str, **context: Any) -> None:
        """Log at WARNING level."""
        self._logger.warning(self._format_message(event, **context))

    def warn(self, event: str, **context: Any) -> None:
        """Log at WARNING level (alias)."""
        self.warning(event, **context)

    def error(self, event: str, **context: Any) -> None:
        """Log at ERROR level."""
        self._logger.error(self._format_message(event, **context))

    def critical(self, event: str, **context: Any) -> None:
        """Log at CRITICAL level."""
        self._logger.critical(self._format_message(event, **context))

    def exception(self, event: str, **context: Any) -> None:
        """Log at ERROR level with exception info."""
        self._logger.exception(self._format_message(event, **context))
