"""Unit tests for insights_export Lambda handler.

Per TDD-EXPORT-001 Section 9.2: Tests for Lambda handler entry point,
registration, validation handling, execution result mapping, and error handling.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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

    def test_handler_async_exists(self) -> None:
        """The module exposes '_handler_async' coroutine."""
        from autom8_asana.lambda_handlers.insights_export import _handler_async

        assert callable(_handler_async)

    def test_execute_exists(self) -> None:
        """The module exposes '_execute' coroutine."""
        from autom8_asana.lambda_handlers.insights_export import _execute

        assert callable(_execute)


# ---------------------------------------------------------------------------
# TestHandlerPattern -- AC-W05.2
# ---------------------------------------------------------------------------

class TestHandlerPattern:
    """Handler follows the asyncio.run -> _handler_async -> _execute pattern."""

    @patch("autom8_asana.lambda_handlers.insights_export._handler_async")
    @patch("autom8_asana.lambda_handlers.insights_export.asyncio")
    def test_handler_calls_asyncio_run(
        self,
        mock_asyncio: MagicMock,
        mock_handler_async: MagicMock,
    ) -> None:
        """handler() delegates to asyncio.run(_handler_async(...))."""
        from autom8_asana.lambda_handlers.insights_export import handler

        expected_result = {"statusCode": 200, "body": "{}"}
        mock_asyncio.run.return_value = expected_result

        event = {"test": True}
        context = MagicMock()
        result = handler(event, context)

        mock_asyncio.run.assert_called_once()
        assert result == expected_result


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

    @pytest.mark.asyncio
    async def test_validation_failure_returns_skipped(self) -> None:
        """Validation errors produce status='skipped' with errors list."""
        from autom8_asana.lambda_handlers.insights_export import _execute

        mock_workflow = MagicMock()
        mock_workflow.validate_async = AsyncMock(
            return_value=["Workflow disabled via AUTOM8_EXPORT_ENABLED=false"]
        )

        mock_asana_client = MagicMock()
        mock_asana_client.attachments = MagicMock()

        mock_data_client = AsyncMock()
        mock_data_client.__aenter__ = AsyncMock(return_value=mock_data_client)
        mock_data_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "autom8_asana.lambda_handlers.insights_export.InsightsExportWorkflow",
                return_value=mock_workflow,
            ) if False else patch.dict("sys.modules", {}),
        ):
            pass

        # Patch the deferred imports inside _execute
        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
            ) as mock_wf_class,
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            mock_wf_class.return_value = mock_workflow

            result = await _execute({})

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"
        assert body["reason"] == "validation_failed"
        assert len(body["errors"]) == 1
        assert "AUTOM8_EXPORT_ENABLED" in body["errors"][0]

    @pytest.mark.asyncio
    async def test_validation_success_proceeds_to_execute(self) -> None:
        """Empty validation errors proceed to workflow execution."""
        from autom8_asana.lambda_handlers.insights_export import _execute

        mock_workflow = MagicMock()
        mock_workflow.validate_async = AsyncMock(return_value=[])
        mock_workflow.execute_async = AsyncMock(
            return_value=_make_workflow_result()
        )

        mock_asana_client = MagicMock()
        mock_asana_client.attachments = MagicMock()

        mock_data_client = AsyncMock()
        mock_data_client.__aenter__ = AsyncMock(return_value=mock_data_client)
        mock_data_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
            ) as mock_wf_class,
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            mock_wf_class.return_value = mock_workflow

            result = await _execute({})

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "completed"
        mock_workflow.execute_async.assert_called_once()


# ---------------------------------------------------------------------------
# TestHandlerExecution -- AC-W05.9
# ---------------------------------------------------------------------------

class TestHandlerExecution:
    """Handler returns structured JSON with all required fields from WorkflowResult."""

    @pytest.mark.asyncio
    async def test_success_response_fields(self) -> None:
        """Completed execution returns all required fields in response body."""
        from autom8_asana.lambda_handlers.insights_export import _execute

        workflow_result = _make_workflow_result(
            total=10,
            succeeded=8,
            failed=1,
            skipped=1,
            total_tables_succeeded=75,
            total_tables_failed=5,
        )

        mock_workflow = MagicMock()
        mock_workflow.validate_async = AsyncMock(return_value=[])
        mock_workflow.execute_async = AsyncMock(return_value=workflow_result)

        mock_asana_client = MagicMock()
        mock_asana_client.attachments = MagicMock()

        mock_data_client = AsyncMock()
        mock_data_client.__aenter__ = AsyncMock(return_value=mock_data_client)
        mock_data_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
            ) as mock_wf_class,
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            mock_wf_class.return_value = mock_workflow

            result = await _execute({})

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

    @pytest.mark.asyncio
    async def test_params_built_from_event_overrides(self) -> None:
        """Event overrides are passed through to workflow params."""
        from autom8_asana.lambda_handlers.insights_export import _execute

        mock_workflow = MagicMock()
        mock_workflow.validate_async = AsyncMock(return_value=[])
        mock_workflow.execute_async = AsyncMock(
            return_value=_make_workflow_result()
        )

        mock_asana_client = MagicMock()
        mock_asana_client.attachments = MagicMock()

        mock_data_client = AsyncMock()
        mock_data_client.__aenter__ = AsyncMock(return_value=mock_data_client)
        mock_data_client.__aexit__ = AsyncMock(return_value=False)

        event = {
            "max_concurrency": 3,
            "attachment_pattern": "custom_*.md",
            "row_limits": {"APPOINTMENTS": 50},
        }

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
            ) as mock_wf_class,
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            mock_wf_class.return_value = mock_workflow

            await _execute(event)

        call_params = mock_workflow.execute_async.call_args[0][0]
        assert call_params["max_concurrency"] == 3
        assert call_params["attachment_pattern"] == "custom_*.md"
        assert call_params["row_limits"] == {"APPOINTMENTS": 50}

    @pytest.mark.asyncio
    async def test_params_use_defaults_when_event_empty(self) -> None:
        """Empty event uses defaults from workflow constants."""
        from autom8_asana.automation.workflows.insights_export import (
            DEFAULT_ATTACHMENT_PATTERN,
            DEFAULT_MAX_CONCURRENCY,
            DEFAULT_ROW_LIMITS,
        )
        from autom8_asana.lambda_handlers.insights_export import _execute

        mock_workflow = MagicMock()
        mock_workflow.validate_async = AsyncMock(return_value=[])
        mock_workflow.execute_async = AsyncMock(
            return_value=_make_workflow_result()
        )

        mock_asana_client = MagicMock()
        mock_asana_client.attachments = MagicMock()

        mock_data_client = AsyncMock()
        mock_data_client.__aenter__ = AsyncMock(return_value=mock_data_client)
        mock_data_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "autom8_asana.automation.workflows.insights_export.InsightsExportWorkflow",
            ) as mock_wf_class,
            patch(
                "autom8_asana.client.AsanaClient",
                return_value=mock_asana_client,
            ),
            patch(
                "autom8_asana.clients.data.client.DataServiceClient",
                return_value=mock_data_client,
            ),
        ):
            mock_wf_class.return_value = mock_workflow

            await _execute({})

        call_params = mock_workflow.execute_async.call_args[0][0]
        assert call_params["max_concurrency"] == DEFAULT_MAX_CONCURRENCY
        assert call_params["attachment_pattern"] == DEFAULT_ATTACHMENT_PATTERN
        assert call_params["row_limits"] == DEFAULT_ROW_LIMITS
        assert call_params["workflow_id"] == "insights-export"


# ---------------------------------------------------------------------------
# TestHandlerError -- AC-W05.2
# ---------------------------------------------------------------------------

class TestHandlerError:
    """When _execute raises, handler returns statusCode 500 with error details."""

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_500(self) -> None:
        """Unhandled exception in _execute produces a 500 response."""
        from autom8_asana.lambda_handlers.insights_export import _handler_async

        with patch(
            "autom8_asana.lambda_handlers.insights_export._execute",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected failure"),
        ):
            result = await _handler_async({}, MagicMock())

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"
        assert body["error"] == "Unexpected failure"
        assert body["error_type"] == "RuntimeError"

    @pytest.mark.asyncio
    async def test_error_response_includes_error_type(self) -> None:
        """Error response includes the exception class name."""
        from autom8_asana.lambda_handlers.insights_export import _handler_async

        with patch(
            "autom8_asana.lambda_handlers.insights_export._execute",
            new_callable=AsyncMock,
            side_effect=ValueError("Bad input"),
        ):
            result = await _handler_async({}, MagicMock())

        body = json.loads(result["body"])
        assert body["error_type"] == "ValueError"
        assert body["error"] == "Bad input"

    @pytest.mark.asyncio
    async def test_error_does_not_propagate(self) -> None:
        """Exception is caught and does not escape the handler."""
        from autom8_asana.lambda_handlers.insights_export import _handler_async

        with patch(
            "autom8_asana.lambda_handlers.insights_export._execute",
            new_callable=AsyncMock,
            side_effect=Exception("kaboom"),
        ):
            # Should NOT raise
            result = await _handler_async({}, MagicMock())

        assert result["statusCode"] == 500
