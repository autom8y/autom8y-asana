"""Unit tests for insights_export Lambda handler.

Per TDD-EXPORT-001 Section 9.2: Tests for Lambda handler entry point,
registration, validation handling, execution result mapping, and error handling.

Tests exercise the handler via the generic workflow_handler factory,
mocking at the client/workflow level.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from autom8_asana.automation.workflows.base import WorkflowResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workflow_result(
    *,
    total: int = 10,
    succeeded: int = 8,
    failed: int = 1,
    skipped: int = 1,
    total_tables_succeeded: int = 75,
    total_tables_failed: int = 5,
) -> WorkflowResult:
    """Build a WorkflowResult with sensible defaults for handler tests."""
    started = datetime(2026, 2, 12, 11, 0, 0, tzinfo=UTC)
    completed = started + timedelta(seconds=42.5)
    return WorkflowResult(
        workflow_id="insights-export",
        started_at=started,
        completed_at=completed,
        total=total,
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        errors=[],
        metadata={
            "total_tables_succeeded": total_tables_succeeded,
            "total_tables_failed": total_tables_failed,
        },
    )


def _setup_mocks():
    """Create standard mock objects for handler tests."""
    mock_workflow = MagicMock()
    mock_workflow.validate_async = AsyncMock(return_value=[])
    mock_workflow.enumerate_async = AsyncMock(
        return_value=[{"gid": "o1", "name": "Offer 1"}]
    )
    mock_workflow.execute_async = AsyncMock(return_value=_make_workflow_result())

    mock_asana_client = MagicMock()
    mock_asana_client.attachments = MagicMock()

    mock_data_client = AsyncMock()
    mock_data_client.__aenter__ = AsyncMock(return_value=mock_data_client)
    mock_data_client.__aexit__ = AsyncMock(return_value=False)

    return mock_workflow, mock_asana_client, mock_data_client


# ---------------------------------------------------------------------------
# TestHandlerModule -- AC-W05.1
# ---------------------------------------------------------------------------


class TestHandlerModule:
    """Module is importable and exposes the expected handler function."""

    def test_module_importable(self) -> None:
        """The insights_export handler module can be imported."""
        import autom8_asana.lambda_handlers.insights_export as mod

        assert mod is not None

    def test_handler_function_exists(self) -> None:
        """The module exposes a top-level 'handler' callable."""
        from autom8_asana.lambda_handlers.insights_export import handler

        assert callable(handler)

    def test_config_has_correct_workflow_id(self) -> None:
        """The handler config uses 'insights-export' as workflow_id."""
        from autom8_asana.lambda_handlers.insights_export import _config

        assert _config.workflow_id == "insights-export"

    def test_config_has_correct_defaults(self) -> None:
        """The handler config default_params match workflow constants."""
        from autom8_asana.lambda_handlers.insights_export import _config

        assert _config.default_params["max_concurrency"] == 5
        assert _config.default_params["attachment_pattern"] == "insights_export_*.md"
        assert _config.default_params["row_limits"] == {
            "APPOINTMENTS": 100,
            "LEADS": 100,
        }

    def test_config_has_response_metadata_keys(self) -> None:
        """The handler config includes table tracking metadata keys."""
        from autom8_asana.lambda_handlers.insights_export import _config

        assert "total_tables_succeeded" in _config.response_metadata_keys
        assert "total_tables_failed" in _config.response_metadata_keys


# ---------------------------------------------------------------------------
# TestHandlerRegistration -- AC-W05.3
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    """Handler is registered in lambda_handlers.__init__."""

    def test_registered_in_all(self) -> None:
        """'insights_export_handler' appears in __all__."""
        import autom8_asana.lambda_handlers as lh

        assert "insights_export_handler" in lh.__all__

    def test_importable_from_package(self) -> None:
        """insights_export_handler is importable from autom8_asana.lambda_handlers."""
        from autom8_asana.lambda_handlers import insights_export_handler

        assert callable(insights_export_handler)

    def test_handler_identity(self) -> None:
        """The registered handler is the same function as the module-level handler."""
        from autom8_asana.lambda_handlers import insights_export_handler
        from autom8_asana.lambda_handlers.insights_export import handler

        assert insights_export_handler is handler


# ---------------------------------------------------------------------------
# TestHandlerValidation -- AC-W05.5
# ---------------------------------------------------------------------------


class TestHandlerValidation:
    """When workflow.validate_async() returns errors, handler returns skipped."""

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_validation_failure_returns_skipped(
        self,
        mock_emit: MagicMock,
    ) -> None:
        """Validation errors produce status='skipped' with errors list."""
        from autom8_asana.lambda_handlers.insights_export import handler

        mock_workflow, mock_asana_client, mock_data_client = _setup_mocks()
        mock_workflow.validate_async = AsyncMock(
            return_value=["Workflow disabled via AUTOM8_EXPORT_ENABLED=false"]
        )

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
                return_value=mock_workflow,
            ),
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            result = handler({}, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"
        assert body["reason"] == "validation_failed"
        assert len(body["errors"]) == 1
        assert "AUTOM8_EXPORT_ENABLED" in body["errors"][0]

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_validation_success_proceeds_to_execute(
        self,
        mock_emit: MagicMock,
    ) -> None:
        """Empty validation errors proceed to workflow execution."""
        from autom8_asana.lambda_handlers.insights_export import handler

        mock_workflow, mock_asana_client, mock_data_client = _setup_mocks()

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
                return_value=mock_workflow,
            ),
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            result = handler({}, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "completed"
        mock_workflow.execute_async.assert_called_once()


# ---------------------------------------------------------------------------
# TestHandlerExecution -- AC-W05.9
# ---------------------------------------------------------------------------


class TestHandlerExecution:
    """Handler returns structured JSON with all required fields from WorkflowResult."""

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_success_response_fields(self, mock_emit: MagicMock) -> None:
        """Completed execution returns all required fields in response body."""
        from autom8_asana.lambda_handlers.insights_export import handler

        workflow_result = _make_workflow_result(
            total=10,
            succeeded=8,
            failed=1,
            skipped=1,
            total_tables_succeeded=75,
            total_tables_failed=5,
        )

        mock_workflow, mock_asana_client, mock_data_client = _setup_mocks()
        mock_workflow.execute_async = AsyncMock(return_value=workflow_result)

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
                return_value=mock_workflow,
            ),
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            result = handler({}, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])

        # All required fields per TDD Section 3.4
        assert body["status"] == "completed"
        assert body["workflow_id"] == "insights-export"
        assert body["total"] == 10
        assert body["succeeded"] == 8
        assert body["failed"] == 1
        assert body["skipped"] == 1
        assert body["duration_seconds"] == 42.5
        assert body["failure_rate"] == 0.1
        assert body["total_tables_succeeded"] == 75
        assert body["total_tables_failed"] == 5

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_params_built_from_event_overrides(
        self,
        mock_emit: MagicMock,
    ) -> None:
        """Event overrides are passed through to workflow params."""
        from autom8_asana.lambda_handlers.insights_export import handler

        mock_workflow, mock_asana_client, mock_data_client = _setup_mocks()

        event = {
            "max_concurrency": 3,
            "attachment_pattern": "custom_*.md",
            "row_limits": {"APPOINTMENTS": 50},
        }

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
                return_value=mock_workflow,
            ),
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            handler(event, MagicMock())

        call_params = mock_workflow.execute_async.call_args[0][1]
        assert call_params["max_concurrency"] == 3
        assert call_params["attachment_pattern"] == "custom_*.md"
        assert call_params["row_limits"] == {"APPOINTMENTS": 50}

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_params_use_defaults_when_event_empty(
        self,
        mock_emit: MagicMock,
    ) -> None:
        """Empty event uses defaults from handler config."""
        from autom8_asana.lambda_handlers.insights_export import handler

        mock_workflow, mock_asana_client, mock_data_client = _setup_mocks()

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
                return_value=mock_workflow,
            ),
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            handler({}, MagicMock())

        call_params = mock_workflow.execute_async.call_args[0][1]
        assert call_params["max_concurrency"] == 5
        assert call_params["attachment_pattern"] == "insights_export_*.md"
        assert call_params["row_limits"] == {"APPOINTMENTS": 100, "LEADS": 100}
        assert call_params["workflow_id"] == "insights-export"


# ---------------------------------------------------------------------------
# TestHandlerError -- AC-W05.2
# ---------------------------------------------------------------------------


class TestHandlerError:
    """When execution raises, handler returns statusCode 500 with error details."""

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_unexpected_error_returns_500(self, mock_emit: MagicMock) -> None:
        """Unhandled exception produces a 500 response."""
        from autom8_asana.lambda_handlers.insights_export import handler

        with patch(
            "autom8_asana.client.AsanaClient",
            side_effect=RuntimeError("Unexpected failure"),
        ):
            result = handler({}, MagicMock())

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"
        assert body["error"] == "Unexpected failure"
        assert body["error_type"] == "RuntimeError"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_error_response_includes_error_type(
        self,
        mock_emit: MagicMock,
    ) -> None:
        """Error response includes the exception class name."""
        from autom8_asana.lambda_handlers.insights_export import handler

        with patch(
            "autom8_asana.client.AsanaClient",
            side_effect=ValueError("Bad input"),
        ):
            result = handler({}, MagicMock())

        body = json.loads(result["body"])
        assert body["error_type"] == "ValueError"
        assert body["error"] == "Bad input"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    def test_error_does_not_propagate(self, mock_emit: MagicMock) -> None:
        """Exception is caught and does not escape the handler."""
        from autom8_asana.lambda_handlers.insights_export import handler

        with patch(
            "autom8_asana.client.AsanaClient",
            side_effect=Exception("kaboom"),
        ):
            # Should NOT raise
            result = handler({}, MagicMock())

        assert result["statusCode"] == 500
