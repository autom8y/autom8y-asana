"""Unit tests for generic workflow handler factory.

Tests the create_workflow_handler factory, WorkflowHandlerConfig, and
CloudWatch metric emission.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.base import WorkflowResult
from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)


# --- Helpers ---


def _make_workflow_result(
    *,
    workflow_id: str = "test-workflow",
    total: int = 10,
    succeeded: int = 8,
    failed: int = 1,
    skipped: int = 1,
    metadata: dict | None = None,
) -> WorkflowResult:
    started = datetime(2026, 2, 12, 11, 0, 0, tzinfo=UTC)
    completed = started + timedelta(seconds=42.5)
    return WorkflowResult(
        workflow_id=workflow_id,
        started_at=started,
        completed_at=completed,
        total=total,
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        errors=[],
        metadata=metadata or {},
    )


def _make_config(**overrides) -> WorkflowHandlerConfig:
    defaults = dict(
        workflow_factory=MagicMock(),
        workflow_id="test-workflow",
        log_prefix="lambda_test",
        default_params={"max_concurrency": 5},
        response_metadata_keys=(),
    )
    defaults.update(overrides)
    return WorkflowHandlerConfig(**defaults)


def _mock_workflow(
    validation_errors: list[str] | None = None,
    result: WorkflowResult | None = None,
) -> MagicMock:
    wf = MagicMock()
    wf.validate_async = AsyncMock(return_value=validation_errors or [])
    wf.execute_async = AsyncMock(return_value=result or _make_workflow_result())
    return wf


# --- Tests ---


class TestCreateWorkflowHandler:
    """Tests for create_workflow_handler."""

    def test_factory_returns_callable(self) -> None:
        """create_workflow_handler returns a callable handler function."""
        config = _make_config()
        handler = create_workflow_handler(config)
        assert callable(handler)

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_execution_success_returns_result(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Successful execution returns statusCode 200 with result body."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result())
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        handler = create_workflow_handler(config)
        result = handler({}, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "completed"
        assert body["workflow_id"] == "test-workflow"
        assert body["total"] == 10
        assert body["succeeded"] == 8

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_params_merged_from_event_and_defaults(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Event overrides are merged with default_params."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            default_params={"max_concurrency": 5, "attachment_pattern": "*.csv"},
        )

        handler = create_workflow_handler(config)
        handler({"max_concurrency": 3}, MagicMock())

        call_params = wf.execute_async.call_args[0][0]
        assert call_params["max_concurrency"] == 3
        assert call_params["attachment_pattern"] == "*.csv"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_validation_failure_returns_skipped(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Validation errors produce status='skipped'."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(validation_errors=["Feature flag disabled"])
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        handler = create_workflow_handler(config)
        result = handler({}, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"
        assert body["reason"] == "validation_failed"
        assert "Feature flag disabled" in body["errors"]

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_response_includes_metadata_keys(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Extra metadata keys are included in the response body."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(
            result=_make_workflow_result(
                metadata={"total_tables_succeeded": 75, "total_tables_failed": 5},
            ),
        )
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            response_metadata_keys=("total_tables_succeeded", "total_tables_failed"),
        )

        handler = create_workflow_handler(config)
        result = handler({}, MagicMock())

        body = json.loads(result["body"])
        assert body["total_tables_succeeded"] == 75
        assert body["total_tables_failed"] == 5

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_unhandled_error_returns_500(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Unhandled exception returns 500 with error details."""
        mock_asana_class.side_effect = RuntimeError("cold start failure")

        config = _make_config()
        handler = create_workflow_handler(config)
        result = handler({}, MagicMock())

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"
        assert body["error_type"] == "RuntimeError"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_emits_execution_count_metric(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """WorkflowExecutionCount metric is emitted on each invocation."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory, workflow_id="my-wf")

        handler = create_workflow_handler(config)
        handler({}, MagicMock())

        # Find the WorkflowExecutionCount call
        calls = [
            c for c in mock_emit.call_args_list if c[0][0] == "WorkflowExecutionCount"
        ]
        assert len(calls) == 1
        assert calls[0][0] == ("WorkflowExecutionCount", 1)
        assert calls[0][1]["dimensions"] == {"workflow_id": "my-wf"}

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_emits_duration_metric(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """WorkflowDuration metric is emitted on success."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result())
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        handler = create_workflow_handler(config)
        handler({}, MagicMock())

        duration_calls = [
            c for c in mock_emit.call_args_list if c[0][0] == "WorkflowDuration"
        ]
        assert len(duration_calls) == 1
        assert duration_calls[0][0][1] == 42.5  # duration_seconds
        assert duration_calls[0][1]["unit"] == "Seconds"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    def test_emits_error_metric_on_failure(
        self,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """WorkflowExecutionError metric is emitted on unhandled error."""
        mock_asana_class.side_effect = RuntimeError("boom")

        config = _make_config(workflow_id="fail-wf")
        handler = create_workflow_handler(config)
        handler({}, MagicMock())

        error_calls = [
            c for c in mock_emit.call_args_list if c[0][0] == "WorkflowExecutionError"
        ]
        assert len(error_calls) == 1
        assert error_calls[0][1]["dimensions"] == {"workflow_id": "fail-wf"}

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    def test_emits_validation_skipped_metric(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """WorkflowValidationSkipped metric is emitted when validation fails."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(validation_errors=["disabled"])
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory, workflow_id="skip-wf")

        handler = create_workflow_handler(config)
        handler({}, MagicMock())

        skip_calls = [
            c
            for c in mock_emit.call_args_list
            if c[0][0] == "WorkflowValidationSkipped"
        ]
        assert len(skip_calls) == 1
        assert skip_calls[0][1]["dimensions"] == {"workflow_id": "skip-wf"}
