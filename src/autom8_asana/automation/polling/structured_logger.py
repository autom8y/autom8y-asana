"""Structured JSON logging for polling automation.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Provides structured logging with JSON
output format for rule evaluation, automation results, and scheduler events.

Features:
- JSON-formatted log output for machine parsing via autom8y-log SDK
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

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.automation.polling.action_executor import ActionResult
    from autom8_asana.persistence.models import AutomationResult

__all__ = ["StructuredLogger"]


class StructuredLogger:
    """JSON-structured logger for polling automation.

    Provides structured logging with JSON output format via autom8y-log SDK.

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
        """Configure logging via autom8y-log SDK.

        Should be called once at application startup before any logging occurs.

        Args:
            json_format: If True, output logs as JSON. If False, use human-
                readable format.
            level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                Defaults to INFO.

        Example:
            StructuredLogger.configure(json_format=True, level="DEBUG")
        """
        cls._json_format = json_format
        cls._level = level.upper()

        from autom8_asana.core.logging import configure as sdk_configure

        fmt = "json" if json_format else "console"
        sdk_configure(level=cls._level, format=fmt)

        cls._configured = True

    @classmethod
    def get_logger(cls, **bound_context: Any) -> Any:
        """Get a logger with bound context.

        Returns a logger with bound context values that will be included
        in all subsequent log entries from this logger instance.

        Args:
            **bound_context: Key-value pairs to bind to all log entries.
                Common context: scheduler_id, rule_id, project_gid.

        Returns:
            A bound logger instance supporting debug, info, warning, error.

        Example:
            logger = StructuredLogger.get_logger(
                scheduler_id="daily-poll",
                timezone="America/New_York",
            )
            logger.info("Starting evaluation cycle")
            # Output includes scheduler_id and timezone in context
        """
        if not cls._configured:
            cls.configure()

        from autom8_asana.core.logging import get_logger as sdk_get_logger

        return sdk_get_logger("autom8_asana.automation.polling").bind(
            **bound_context
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
        result: ActionResult,
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
        log_method = getattr(logger, level)
        log_method(event, **context)


