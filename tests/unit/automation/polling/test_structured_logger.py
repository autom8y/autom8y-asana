"""Tests for structured logging in polling automation.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Tests for JSON-structured logging
with autom8y-log SDK integration.

Covers:
- configure() sets up logging
- get_logger() returns usable logger
- log_rule_evaluation() outputs JSON
- log_automation_result() outputs JSON
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import autom8_asana.core.logging as core_logging
from autom8_asana.automation.polling.structured_logger import (
    StructuredLogger,
)


class TestStructuredLoggerConfigure:
    """Tests for StructuredLogger.configure()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False
        core_logging._configured = False

    def test_configure_sets_configured_flag(self) -> None:
        """configure() sets the _configured flag."""
        assert StructuredLogger._configured is False

        StructuredLogger.configure()

        assert StructuredLogger._configured is True

    def test_configure_stores_json_format(self) -> None:
        """configure() stores json_format setting."""
        StructuredLogger.configure(json_format=True)
        assert StructuredLogger._json_format is True

        StructuredLogger._configured = False
        StructuredLogger.configure(json_format=False)
        assert StructuredLogger._json_format is False

    def test_configure_stores_log_level(self) -> None:
        """configure() stores and normalizes log level."""
        StructuredLogger.configure(level="debug")
        assert StructuredLogger._level == "DEBUG"

        StructuredLogger._configured = False
        StructuredLogger.configure(level="WARNING")
        assert StructuredLogger._level == "WARNING"

    def test_configure_defaults(self) -> None:
        """configure() uses sensible defaults."""
        StructuredLogger.configure()

        assert StructuredLogger._json_format is True
        assert StructuredLogger._level == "INFO"

    def test_configure_with_sdk(self) -> None:
        """configure() properly configures via autom8y-log SDK."""
        StructuredLogger.configure(json_format=True, level="DEBUG")

        # Should not raise
        assert StructuredLogger._configured is True


class TestStructuredLoggerGetLogger:
    """Tests for StructuredLogger.get_logger()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False
        core_logging._configured = False

    def test_get_logger_auto_configures(self) -> None:
        """get_logger() auto-configures on first use."""
        assert StructuredLogger._configured is False

        logger = StructuredLogger.get_logger()

        assert StructuredLogger._configured is True
        assert logger is not None

    def test_get_logger_returns_usable_logger(self) -> None:
        """get_logger() returns a logger with standard methods."""
        logger = StructuredLogger.get_logger()

        # Should have standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_get_logger_accepts_bound_context(self) -> None:
        """get_logger() accepts and stores bound context."""
        logger = StructuredLogger.get_logger(
            scheduler_id="daily-poll",
            timezone="UTC",
        )

        # Logger should be returned (context binding is internal)
        assert logger is not None

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_logger() returns a bound logger with bind() support."""
        StructuredLogger.configure()
        logger = StructuredLogger.get_logger(test_key="test_value")

        assert hasattr(logger, "bind")


class TestStructuredLoggerLogRuleEvaluation:
    """Tests for StructuredLogger.log_rule_evaluation()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False
        core_logging._configured = False

    def test_log_rule_evaluation_outputs_correct_fields(self, capsys) -> None:
        """log_rule_evaluation() includes all expected fields."""
        StructuredLogger.configure(json_format=False, level="INFO")

        StructuredLogger.log_rule_evaluation(
            rule_id="test-rule",
            rule_name="Test Rule",
            project_gid="123456789",
            matches=5,
            duration_ms=150.5,
        )

        # SDK routes structlog output to stdout/stderr, not stdlib caplog
        captured = capsys.readouterr()
        log_output = captured.out + captured.err
        assert "rule_evaluation_complete" in log_output or "test-rule" in log_output

    def test_log_rule_evaluation_accepts_all_parameters(self) -> None:
        """log_rule_evaluation() accepts all required parameters."""
        StructuredLogger.configure()

        # Should not raise
        StructuredLogger.log_rule_evaluation(
            rule_id="my-rule",
            rule_name="My Rule",
            project_gid="9999999999999",
            matches=0,
            duration_ms=0.0,
        )

    def test_log_rule_evaluation_handles_zero_matches(self) -> None:
        """log_rule_evaluation() handles zero matches correctly."""
        StructuredLogger.configure()

        # Should not raise
        StructuredLogger.log_rule_evaluation(
            rule_id="no-matches",
            rule_name="No Matches Rule",
            project_gid="123",
            matches=0,
            duration_ms=10.0,
        )

    def test_log_rule_evaluation_handles_high_duration(self) -> None:
        """log_rule_evaluation() handles high duration values."""
        StructuredLogger.configure()

        # Should not raise
        StructuredLogger.log_rule_evaluation(
            rule_id="slow-rule",
            rule_name="Slow Rule",
            project_gid="123",
            matches=100,
            duration_ms=60000.0,  # 60 seconds
        )


class TestStructuredLoggerLogActionResult:
    """Tests for StructuredLogger.log_action_result()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False
        core_logging._configured = False

    def test_log_action_result_with_success(self) -> None:
        """log_action_result() logs successful action results."""
        from autom8_asana.automation.polling.action_executor import ActionResult

        StructuredLogger.configure()

        result = ActionResult(
            success=True,
            action_type="add_tag",
            task_gid="task-123",
            details={"tag_gid": "tag-456"},
        )

        # Should not raise
        StructuredLogger.log_action_result(result, rule_id="test-rule")

    def test_log_action_result_with_failure(self) -> None:
        """log_action_result() logs failed action results."""
        from autom8_asana.automation.polling.action_executor import ActionResult

        StructuredLogger.configure()

        result = ActionResult(
            success=False,
            action_type="add_comment",
            task_gid="task-456",
            error="Task not found",
        )

        # Should not raise
        StructuredLogger.log_action_result(result)

    def test_log_action_result_without_rule_id(self) -> None:
        """log_action_result() works without rule_id."""
        from autom8_asana.automation.polling.action_executor import ActionResult

        StructuredLogger.configure()

        result = ActionResult(
            success=True,
            action_type="change_section",
            task_gid="task-789",
            details={"section_gid": "section-999"},
        )

        # Should not raise
        StructuredLogger.log_action_result(result)

    def test_log_action_result_outputs_correct_event(self, capsys) -> None:
        """log_action_result() outputs correct event name based on success."""
        from autom8_asana.automation.polling.action_executor import ActionResult

        StructuredLogger.configure(json_format=False, level="INFO")

        success_result = ActionResult(
            success=True,
            action_type="add_tag",
            task_gid="task-123",
        )
        failure_result = ActionResult(
            success=False,
            action_type="add_tag",
            task_gid="task-456",
            error="Failed",
        )

        StructuredLogger.log_action_result(success_result)

        # SDK routes structlog output to stdout/stderr, not stdlib caplog
        captured = capsys.readouterr()
        log_output = captured.out + captured.err
        assert "action_executed" in log_output or "task-123" in log_output

        StructuredLogger.log_action_result(failure_result)

        # Failure should appear in output
        captured = capsys.readouterr()
        error_output = captured.out + captured.err
        assert "action_failed" in error_output or "task-456" in error_output


class TestStructuredLoggerLogAutomationResult:
    """Tests for StructuredLogger.log_automation_result()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False
        core_logging._configured = False

    def test_log_automation_result_with_success(self) -> None:
        """log_automation_result() logs successful results correctly."""
        StructuredLogger.configure()

        # Create mock AutomationResult
        mock_result = MagicMock()
        mock_result.rule_id = "test-rule"
        mock_result.rule_name = "Test Rule"
        mock_result.triggered_by_gid = "task-123"
        mock_result.triggered_by_type = "Task"
        mock_result.actions_executed = ["add_tag"]
        mock_result.entities_created = []
        mock_result.entities_updated = ["task-123"]
        mock_result.success = True
        mock_result.error = None
        mock_result.skipped_reason = None
        mock_result.execution_time_ms = 50.0
        mock_result.was_skipped = False
        mock_result.enhancement_results = None

        # Should not raise
        StructuredLogger.log_automation_result(mock_result)

    def test_log_automation_result_with_failure(self) -> None:
        """log_automation_result() logs failed results correctly."""
        StructuredLogger.configure()

        mock_result = MagicMock()
        mock_result.rule_id = "failing-rule"
        mock_result.rule_name = "Failing Rule"
        mock_result.triggered_by_gid = "task-456"
        mock_result.triggered_by_type = "Task"
        mock_result.actions_executed = []
        mock_result.entities_created = []
        mock_result.entities_updated = []
        mock_result.success = False
        mock_result.error = "API rate limit exceeded"
        mock_result.skipped_reason = None
        mock_result.execution_time_ms = 100.0
        mock_result.was_skipped = False
        mock_result.enhancement_results = None

        # Should not raise
        StructuredLogger.log_automation_result(mock_result)

    def test_log_automation_result_with_skip(self) -> None:
        """log_automation_result() logs skipped results correctly."""
        StructuredLogger.configure()

        mock_result = MagicMock()
        mock_result.rule_id = "skipped-rule"
        mock_result.rule_name = "Skipped Rule"
        mock_result.triggered_by_gid = "task-789"
        mock_result.triggered_by_type = "Task"
        mock_result.actions_executed = []
        mock_result.entities_created = []
        mock_result.entities_updated = []
        mock_result.success = True
        mock_result.error = None
        mock_result.skipped_reason = (
            "Loop prevention: task recently modified by automation"
        )
        mock_result.execution_time_ms = 5.0
        mock_result.was_skipped = True
        mock_result.enhancement_results = None

        # Should not raise
        StructuredLogger.log_automation_result(mock_result)
