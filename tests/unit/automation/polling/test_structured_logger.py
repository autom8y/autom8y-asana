"""Tests for structured logging in polling automation.

Per TDD-PIPELINE-AUTOMATION-EXPANSION: Tests for JSON-structured logging
with structlog integration and stdlib fallback.

Covers:
- configure() sets up logging
- get_logger() returns usable logger
- log_rule_evaluation() outputs JSON
- log_automation_result() outputs JSON
- Fallback to stdlib works when structlog not available
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.automation.polling.structured_logger import (
    StructuredLogger,
    _StdlibLoggerAdapter,
    _STRUCTLOG_AVAILABLE,
)


class TestStructuredLoggerConfigure:
    """Tests for StructuredLogger.configure()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False

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

    @pytest.mark.skipif(not _STRUCTLOG_AVAILABLE, reason="structlog not installed")
    def test_configure_with_structlog(self) -> None:
        """configure() properly configures structlog when available."""
        StructuredLogger.configure(json_format=True, level="DEBUG")

        # Should not raise
        assert StructuredLogger._configured is True

    def test_configure_without_structlog(self) -> None:
        """configure() falls back to stdlib when structlog not available."""
        with patch(
            "autom8_asana.automation.polling.structured_logger._STRUCTLOG_AVAILABLE",
            False,
        ):
            # Force reconfiguration
            StructuredLogger._configured = False
            StructuredLogger.configure(level="INFO")

            assert StructuredLogger._configured is True


class TestStructuredLoggerGetLogger:
    """Tests for StructuredLogger.get_logger()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False

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

    @pytest.mark.skipif(not _STRUCTLOG_AVAILABLE, reason="structlog not installed")
    def test_get_logger_with_structlog_returns_bound_logger(self) -> None:
        """get_logger() returns structlog BoundLogger when available."""

        StructuredLogger.configure()
        logger = StructuredLogger.get_logger(test_key="test_value")

        # Should be a structlog bound logger
        assert hasattr(logger, "bind")

    def test_get_logger_without_structlog_returns_adapter(self) -> None:
        """get_logger() returns _StdlibLoggerAdapter when structlog unavailable."""
        with patch(
            "autom8_asana.automation.polling.structured_logger._STRUCTLOG_AVAILABLE",
            False,
        ):
            StructuredLogger._configured = False
            logger = StructuredLogger.get_logger(test_key="test_value")

            assert isinstance(logger, _StdlibLoggerAdapter)


class TestStructuredLoggerLogRuleEvaluation:
    """Tests for StructuredLogger.log_rule_evaluation()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False

    def test_log_rule_evaluation_outputs_correct_fields(self, caplog) -> None:
        """log_rule_evaluation() includes all expected fields."""
        StructuredLogger.configure(json_format=False, level="INFO")

        with caplog.at_level(logging.INFO):
            StructuredLogger.log_rule_evaluation(
                rule_id="test-rule",
                rule_name="Test Rule",
                project_gid="123456789",
                matches=5,
                duration_ms=150.5,
            )

        # Check log output contains expected fields
        log_output = caplog.text
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

    def test_log_action_result_outputs_correct_event(self, caplog) -> None:
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

        with caplog.at_level(logging.INFO):
            StructuredLogger.log_action_result(success_result)

        # Check log contains expected info
        log_output = caplog.text
        assert "action_executed" in log_output or "task-123" in log_output

        with caplog.at_level(logging.ERROR):
            StructuredLogger.log_action_result(failure_result)

        # Failure should be logged at error level
        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_records) >= 1


class TestStructuredLoggerLogAutomationResult:
    """Tests for StructuredLogger.log_automation_result()."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False

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


class TestStdlibLoggerAdapter:
    """Tests for _StdlibLoggerAdapter fallback."""

    def test_adapter_stores_bound_context(self) -> None:
        """Adapter stores initial bound context."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {"key1": "value1"})

        assert adapter._bound_context == {"key1": "value1"}

    def test_adapter_bind_creates_new_adapter(self) -> None:
        """bind() creates new adapter with merged context."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {"key1": "value1"})

        new_adapter = adapter.bind(key2="value2")

        # Original unchanged
        assert adapter._bound_context == {"key1": "value1"}
        # New adapter has merged context
        assert new_adapter._bound_context == {"key1": "value1", "key2": "value2"}

    def test_adapter_format_message_includes_context(self) -> None:
        """_format_message() includes bound context."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {"scheduler_id": "daily"})

        message = adapter._format_message("test_event", extra_key="extra_value")

        # Should be JSON-like
        assert '"event": "test_event"' in message
        assert '"scheduler_id": "daily"' in message
        assert '"extra_key": "extra_value"' in message

    def test_adapter_format_message_includes_timestamp(self) -> None:
        """_format_message() includes ISO timestamp."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        message = adapter._format_message("test_event")

        assert '"timestamp":' in message

    def test_adapter_info_logs_correctly(self, caplog) -> None:
        """info() method logs at INFO level."""
        stdlib_logger = logging.getLogger("test.adapter")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {"context": "test"})

        with caplog.at_level(logging.INFO, logger="test.adapter"):
            adapter.info("test_info_event", key="value")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"

    def test_adapter_debug_logs_correctly(self, caplog) -> None:
        """debug() method logs at DEBUG level."""
        stdlib_logger = logging.getLogger("test.adapter.debug")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        with caplog.at_level(logging.DEBUG, logger="test.adapter.debug"):
            adapter.debug("test_debug_event")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "DEBUG"

    def test_adapter_warning_logs_correctly(self, caplog) -> None:
        """warning() method logs at WARNING level."""
        stdlib_logger = logging.getLogger("test.adapter.warning")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        with caplog.at_level(logging.WARNING, logger="test.adapter.warning"):
            adapter.warning("test_warning_event")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"

    def test_adapter_warn_alias(self, caplog) -> None:
        """warn() is an alias for warning()."""
        stdlib_logger = logging.getLogger("test.adapter.warn")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        with caplog.at_level(logging.WARNING, logger="test.adapter.warn"):
            adapter.warn("test_warn_event")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"

    def test_adapter_error_logs_correctly(self, caplog) -> None:
        """error() method logs at ERROR level."""
        stdlib_logger = logging.getLogger("test.adapter.error")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        with caplog.at_level(logging.ERROR, logger="test.adapter.error"):
            adapter.error("test_error_event")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"

    def test_adapter_critical_logs_correctly(self, caplog) -> None:
        """critical() method logs at CRITICAL level."""
        stdlib_logger = logging.getLogger("test.adapter.critical")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        with caplog.at_level(logging.CRITICAL, logger="test.adapter.critical"):
            adapter.critical("test_critical_event")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "CRITICAL"

    def test_adapter_handles_list_values(self) -> None:
        """Adapter handles list values in context."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        message = adapter._format_message(
            "test_event",
            items=["a", "b", "c"],
        )

        assert '"items": ["a", "b", "c"]' in message

    def test_adapter_handles_dict_values(self) -> None:
        """Adapter handles dict values in context."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        message = adapter._format_message(
            "test_event",
            data={"nested": "value"},
        )

        assert '"data": {"nested": "value"}' in message

    def test_adapter_handles_numeric_values(self) -> None:
        """Adapter handles numeric values correctly."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        message = adapter._format_message(
            "test_event",
            count=42,
            ratio=3.14,
        )

        assert '"count": 42' in message
        assert '"ratio": 3.14' in message

    def test_adapter_handles_boolean_values(self) -> None:
        """Adapter handles boolean values correctly."""
        stdlib_logger = logging.getLogger("test")
        adapter = _StdlibLoggerAdapter(stdlib_logger, {})

        message = adapter._format_message(
            "test_event",
            enabled=True,
            disabled=False,
        )

        # Python bools are True/False, need to check actual output
        assert '"enabled":' in message
        assert '"disabled":' in message


class TestStructuredLoggerFallback:
    """Tests for structlog fallback behavior."""

    def setup_method(self) -> None:
        """Reset configured state before each test."""
        StructuredLogger._configured = False

    def test_fallback_produces_parseable_json(self) -> None:
        """Fallback logger produces valid JSON-like output."""
        with patch(
            "autom8_asana.automation.polling.structured_logger._STRUCTLOG_AVAILABLE",
            False,
        ):
            StructuredLogger._configured = False
            logger = StructuredLogger.get_logger(test_context="value")

            # Get the formatted message
            message = logger._format_message("test_event", key="data")

            # Should be valid JSON
            try:
                parsed = json.loads(message)
                assert parsed["event"] == "test_event"
                assert parsed["test_context"] == "value"
                assert parsed["key"] == "data"
                assert "timestamp" in parsed
            except json.JSONDecodeError:
                pytest.fail(f"Output is not valid JSON: {message}")

    def test_fallback_works_without_structlog(self) -> None:
        """Full logging workflow works without structlog installed."""
        with patch(
            "autom8_asana.automation.polling.structured_logger._STRUCTLOG_AVAILABLE",
            False,
        ):
            StructuredLogger._configured = False

            # Configure
            StructuredLogger.configure(json_format=True, level="DEBUG")

            # Get logger
            logger = StructuredLogger.get_logger(scheduler="test")

            # Use logger (should not raise)
            logger.info("test_info")
            logger.debug("test_debug")
            logger.warning("test_warning")
            logger.error("test_error")

            # Log rule evaluation (should not raise)
            StructuredLogger.log_rule_evaluation(
                rule_id="test",
                rule_name="Test",
                project_gid="123",
                matches=1,
                duration_ms=10.0,
            )
