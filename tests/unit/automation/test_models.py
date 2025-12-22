"""Unit tests for AutomationResult and SaveResult automation properties.

Per TDD-AUTOMATION-LAYER: Test AutomationResult and related SaveResult properties.
"""

from __future__ import annotations

from autom8_asana.persistence.models import AutomationResult, SaveResult


class TestAutomationResult:
    """Tests for AutomationResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values for AutomationResult."""
        result = AutomationResult(
            rule_id="test_rule",
            rule_name="Test Rule",
            triggered_by_gid="123",
            triggered_by_type="Task",
        )

        assert result.rule_id == "test_rule"
        assert result.rule_name == "Test Rule"
        assert result.triggered_by_gid == "123"
        assert result.triggered_by_type == "Task"
        assert result.actions_executed == []
        assert result.entities_created == []
        assert result.entities_updated == []
        assert result.success is True
        assert result.error is None
        assert result.execution_time_ms == 0.0
        assert result.skipped_reason is None

    def test_was_skipped_true(self) -> None:
        """Test was_skipped property when skipped."""
        result = AutomationResult(
            rule_id="test_rule",
            rule_name="Test Rule",
            triggered_by_gid="123",
            triggered_by_type="Task",
            skipped_reason="circular_reference_prevented",
        )

        assert result.was_skipped is True

    def test_was_skipped_false(self) -> None:
        """Test was_skipped property when not skipped."""
        result = AutomationResult(
            rule_id="test_rule",
            rule_name="Test Rule",
            triggered_by_gid="123",
            triggered_by_type="Task",
        )

        assert result.was_skipped is False

    def test_repr_success(self) -> None:
        """Test repr for successful result."""
        result = AutomationResult(
            rule_id="test_rule",
            rule_name="Test Rule",
            triggered_by_gid="123",
            triggered_by_type="Task",
            success=True,
        )

        assert "Test Rule" in repr(result)
        assert "success" in repr(result)

    def test_repr_failed(self) -> None:
        """Test repr for failed result."""
        result = AutomationResult(
            rule_id="test_rule",
            rule_name="Test Rule",
            triggered_by_gid="123",
            triggered_by_type="Task",
            success=False,
            error="Something went wrong",
        )

        assert "Test Rule" in repr(result)
        assert "failed" in repr(result)

    def test_repr_skipped(self) -> None:
        """Test repr for skipped result."""
        result = AutomationResult(
            rule_id="test_rule",
            rule_name="Test Rule",
            triggered_by_gid="123",
            triggered_by_type="Task",
            skipped_reason="circular_reference_prevented",
        )

        assert "Test Rule" in repr(result)
        assert "skipped" in repr(result)


class TestSaveResultAutomation:
    """Tests for SaveResult automation properties."""

    def test_automation_results_default_empty(self) -> None:
        """Test that automation_results defaults to empty list."""
        result = SaveResult()

        assert result.automation_results == []

    def test_automation_succeeded_empty(self) -> None:
        """Test automation_succeeded with no results."""
        result = SaveResult()

        assert result.automation_succeeded == 0

    def test_automation_succeeded_counts_success(self) -> None:
        """Test automation_succeeded counts successful executions."""
        result = SaveResult(
            automation_results=[
                AutomationResult(
                    rule_id="r1",
                    rule_name="R1",
                    triggered_by_gid="1",
                    triggered_by_type="T",
                    success=True,
                ),
                AutomationResult(
                    rule_id="r2",
                    rule_name="R2",
                    triggered_by_gid="2",
                    triggered_by_type="T",
                    success=True,
                ),
            ]
        )

        assert result.automation_succeeded == 2

    def test_automation_succeeded_excludes_skipped(self) -> None:
        """Test automation_succeeded excludes skipped rules."""
        result = SaveResult(
            automation_results=[
                AutomationResult(
                    rule_id="r1",
                    rule_name="R1",
                    triggered_by_gid="1",
                    triggered_by_type="T",
                    success=True,
                ),
                AutomationResult(
                    rule_id="r2",
                    rule_name="R2",
                    triggered_by_gid="2",
                    triggered_by_type="T",
                    success=True,
                    skipped_reason="circular_reference_prevented",
                ),
            ]
        )

        assert result.automation_succeeded == 1

    def test_automation_failed_empty(self) -> None:
        """Test automation_failed with no results."""
        result = SaveResult()

        assert result.automation_failed == 0

    def test_automation_failed_counts_failures(self) -> None:
        """Test automation_failed counts failed executions."""
        result = SaveResult(
            automation_results=[
                AutomationResult(
                    rule_id="r1",
                    rule_name="R1",
                    triggered_by_gid="1",
                    triggered_by_type="T",
                    success=False,
                    error="Error 1",
                ),
                AutomationResult(
                    rule_id="r2",
                    rule_name="R2",
                    triggered_by_gid="2",
                    triggered_by_type="T",
                    success=True,
                ),
                AutomationResult(
                    rule_id="r3",
                    rule_name="R3",
                    triggered_by_gid="3",
                    triggered_by_type="T",
                    success=False,
                    error="Error 3",
                ),
            ]
        )

        assert result.automation_failed == 2

    def test_automation_skipped_empty(self) -> None:
        """Test automation_skipped with no results."""
        result = SaveResult()

        assert result.automation_skipped == 0

    def test_automation_skipped_counts_skipped(self) -> None:
        """Test automation_skipped counts skipped rules."""
        result = SaveResult(
            automation_results=[
                AutomationResult(
                    rule_id="r1",
                    rule_name="R1",
                    triggered_by_gid="1",
                    triggered_by_type="T",
                    success=True,
                ),
                AutomationResult(
                    rule_id="r2",
                    rule_name="R2",
                    triggered_by_gid="2",
                    triggered_by_type="T",
                    success=True,
                    skipped_reason="circular_reference_prevented",
                ),
                AutomationResult(
                    rule_id="r3",
                    rule_name="R3",
                    triggered_by_gid="3",
                    triggered_by_type="T",
                    success=True,
                    skipped_reason="depth_limit_reached",
                ),
            ]
        )

        assert result.automation_skipped == 2

    def test_automation_metrics_combined(self) -> None:
        """Test all automation metrics together."""
        result = SaveResult(
            automation_results=[
                # Succeeded
                AutomationResult(
                    rule_id="r1",
                    rule_name="R1",
                    triggered_by_gid="1",
                    triggered_by_type="T",
                    success=True,
                ),
                # Failed
                AutomationResult(
                    rule_id="r2",
                    rule_name="R2",
                    triggered_by_gid="2",
                    triggered_by_type="T",
                    success=False,
                    error="Error",
                ),
                # Skipped
                AutomationResult(
                    rule_id="r3",
                    rule_name="R3",
                    triggered_by_gid="3",
                    triggered_by_type="T",
                    success=True,
                    skipped_reason="loop",
                ),
            ]
        )

        assert result.automation_succeeded == 1
        assert result.automation_failed == 1
        assert result.automation_skipped == 1
