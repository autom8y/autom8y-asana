"""Unit tests for generic workflow handler factory.

Tests the create_workflow_handler factory, WorkflowHandlerConfig, and
CloudWatch metric emission.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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
    entities: list[dict] | None = None,
) -> MagicMock:
    wf = MagicMock()
    wf.validate_async = AsyncMock(return_value=validation_errors or [])
    wf.enumerate_async = AsyncMock(
        return_value=entities if entities is not None else [{"gid": "123"}]
    )
    wf.execute_async = AsyncMock(return_value=result or _make_workflow_result())
    return wf


# --- Tests ---


class TestCreateWorkflowHandler:
    """Tests for create_workflow_handler."""

    async def test_factory_returns_callable(self) -> None:
        """create_workflow_handler returns a callable handler function."""
        config = _make_config()
        handler = create_workflow_handler(config)
        assert callable(handler)

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_execution_success_returns_result(
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
        result = await asyncio.to_thread(handler, {}, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "completed"
        assert body["workflow_id"] == "test-workflow"
        assert body["total"] == 10
        assert body["succeeded"] == 8

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_params_merged_from_event_and_defaults(
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
        await asyncio.to_thread(handler, {"max_concurrency": 3}, MagicMock())

        # execute_async receives (entities, params) -- params is second positional arg
        call_params = wf.execute_async.call_args[0][1]
        assert call_params["max_concurrency"] == 3
        assert call_params["attachment_pattern"] == "*.csv"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_validation_failure_returns_skipped(
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
        result = await asyncio.to_thread(handler, {}, MagicMock())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "skipped"
        assert body["reason"] == "validation_failed"
        assert "Feature flag disabled" in body["errors"]

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_response_includes_metadata_keys(
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
        result = await asyncio.to_thread(handler, {}, MagicMock())

        body = json.loads(result["body"])
        assert body["total_tables_succeeded"] == 75
        assert body["total_tables_failed"] == 5

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_unhandled_error_returns_500(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Unhandled exception returns 500 with error details."""
        mock_asana_class.side_effect = RuntimeError("cold start failure")

        config = _make_config()
        handler = create_workflow_handler(config)
        result = await asyncio.to_thread(handler, {}, MagicMock())

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["status"] == "error"
        assert body["error_type"] == "RuntimeError"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_emits_execution_count_metric(
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
        await asyncio.to_thread(handler, {}, MagicMock())

        # Find the WorkflowExecutionCount call
        calls = [c for c in mock_emit.call_args_list if c[0][0] == "WorkflowExecutionCount"]
        assert len(calls) == 1
        assert calls[0][0] == ("WorkflowExecutionCount", 1)
        assert calls[0][1]["dimensions"] == {"workflow_id": "my-wf"}

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_emits_duration_metric(
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
        await asyncio.to_thread(handler, {}, MagicMock())

        duration_calls = [c for c in mock_emit.call_args_list if c[0][0] == "WorkflowDuration"]
        assert len(duration_calls) == 1
        assert duration_calls[0][0][1] == 42.5  # duration_seconds
        assert duration_calls[0][1]["unit"] == "Seconds"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    async def test_emits_error_metric_on_failure(
        self,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """WorkflowExecutionError metric is emitted on unhandled error."""
        mock_asana_class.side_effect = RuntimeError("boom")

        config = _make_config(workflow_id="fail-wf")
        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        error_calls = [c for c in mock_emit.call_args_list if c[0][0] == "WorkflowExecutionError"]
        assert len(error_calls) == 1
        assert error_calls[0][1]["dimensions"] == {"workflow_id": "fail-wf"}

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_emits_validation_skipped_metric(
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
        await asyncio.to_thread(handler, {}, MagicMock())

        skip_calls = [c for c in mock_emit.call_args_list if c[0][0] == "WorkflowValidationSkipped"]
        assert len(skip_calls) == 1
        assert skip_calls[0][1]["dimensions"] == {"workflow_id": "skip-wf"}


class TestHandlerEnumerateExecuteOrchestration:
    """Tests for the enumerate -> execute orchestration pattern.

    Per TDD-ENTITY-SCOPE-001 Section 8.4: Verify that the handler factory
    calls enumerate_async with EntityScope, then passes entities to execute_async.
    """

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_handler_calls_enumerate_then_execute(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """enumerate_async is called before execute_async."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        entities = [{"gid": "111"}, {"gid": "222"}]
        wf = _mock_workflow(entities=entities)
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        # enumerate_async was called
        wf.enumerate_async.assert_called_once()
        # execute_async was called with the entities from enumerate_async
        wf.execute_async.assert_called_once()
        call_entities = wf.execute_async.call_args[0][0]
        assert call_entities == entities

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_handler_passes_scope_to_enumerate(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """EntityScope fields match event."""
        from autom8_asana.core.scope import EntityScope

        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {"entity_ids": ["999"], "dry_run": True}, MagicMock())

        scope_arg = wf.enumerate_async.call_args[0][0]
        assert isinstance(scope_arg, EntityScope)
        assert scope_arg.entity_ids == ("999",)
        assert scope_arg.dry_run is True

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_handler_dry_run_in_params(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """dry_run=True in event propagates to params."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {"dry_run": True}, MagicMock())

        call_params = wf.execute_async.call_args[0][1]
        assert call_params["dry_run"] is True

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_handler_empty_event_default_scope(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Empty event produces default EntityScope (full enumeration)."""
        from autom8_asana.core.scope import EntityScope

        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        scope_arg = wf.enumerate_async.call_args[0][0]
        assert isinstance(scope_arg, EntityScope)
        assert scope_arg.entity_ids == ()
        assert scope_arg.dry_run is False
        assert scope_arg.limit is None


class TestHandlerWorkflowRegistration:
    """Tests for workflow registration in the handler factory.

    Per TDD sprint-2 Item 3: Verify that create_workflow_handler
    registers the workflow in get_workflow_registry().
    """

    def setup_method(self) -> None:
        """Reset registry before each test."""
        from autom8_asana.automation.workflows.registry import (
            reset_workflow_registry,
        )

        reset_workflow_registry()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        from autom8_asana.automation.workflows.registry import (
            reset_workflow_registry,
        )

        reset_workflow_registry()

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_handler_registers_workflow(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Invoking the handler registers the workflow in get_workflow_registry()."""
        from autom8_asana.automation.workflows.registry import (
            get_workflow_registry,
        )

        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        wf.workflow_id = "reg-test-wf"
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory, workflow_id="reg-test-wf")

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        registry = get_workflow_registry()
        assert registry.get("reg-test-wf") is wf

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_handler_warm_container_reregistration(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Second invocation in warm container does not raise on re-registration."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        wf.workflow_id = "warm-wf"
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory, workflow_id="warm-wf")

        handler = create_workflow_handler(config)
        # First invocation -- registers
        result1 = await asyncio.to_thread(handler, {}, MagicMock())
        assert result1["statusCode"] == 200

        # Second invocation -- warm container, should not raise
        result2 = await asyncio.to_thread(handler, {}, MagicMock())
        assert result2["statusCode"] == 200


class TestBridgeEventEmission:
    """Tests for BridgeExecutionComplete domain event emission.

    Per ADR-bridge-dispatch-model Decision 3: Verify that the handler
    publishes a BridgeExecutionComplete event after successful execution,
    and that publish failures are swallowed (fire-and-forget semantics).
    """

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_event_published_on_success(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """BridgeExecutionComplete event is published after successful execution."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result(workflow_id="emit-test"))
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory, workflow_id="emit-test")

        with patch("autom8y_events.EventPublisher") as mock_publisher_cls:
            mock_publisher = MagicMock()
            mock_publisher_cls.return_value = mock_publisher

            handler = create_workflow_handler(config)
            result = await asyncio.to_thread(handler, {}, MagicMock())

            assert result["statusCode"] == 200
            mock_publisher.publish.assert_called_once()

            # Verify event shape
            event = mock_publisher.publish.call_args[0][0]
            assert event.source == "asana"
            assert event.detail_type == "BridgeExecutionComplete"
            assert event.detail["workflow_id"] == "emit-test"
            assert event.detail["total"] == 10
            assert event.detail["succeeded"] == 8
            assert event.detail["failed"] == 1
            assert event.detail["skipped"] == 1
            assert event.detail["duration_seconds"] == 42.5
            assert event.idempotency_key is not None
            assert event.idempotency_key.startswith("emit-test-")

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_event_publish_failure_does_not_fail_handler(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """Event publish failure is swallowed -- handler returns 200."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        with patch("autom8y_events.EventPublisher") as mock_publisher_cls:
            mock_publisher = MagicMock()
            mock_publisher.publish.side_effect = RuntimeError("EventBridge down")
            mock_publisher_cls.return_value = mock_publisher

            handler = create_workflow_handler(config)
            result = await asyncio.to_thread(handler, {}, MagicMock())

            # Handler still returns 200 despite event publish failure
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["status"] == "completed"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_event_not_published_on_validation_failure(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """No event is published when validation fails (skipped status)."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(validation_errors=["Feature flag disabled"])
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        with patch("autom8y_events.EventPublisher") as mock_publisher_cls:
            mock_publisher = MagicMock()
            mock_publisher_cls.return_value = mock_publisher

            handler = create_workflow_handler(config)
            result = await asyncio.to_thread(handler, {}, MagicMock())

            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["status"] == "skipped"
            # EventPublisher should NOT have been instantiated
            mock_publisher_cls.assert_not_called()

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_event_skipped_when_events_not_installed(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """When autom8y-events is not installed, emission is silently skipped."""
        import sys

        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow()
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        # Simulate autom8y_events not being installed by hiding it
        original = sys.modules.get("autom8y_events")
        sys.modules["autom8y_events"] = None  # type: ignore[assignment]
        try:
            handler = create_workflow_handler(config)
            result = await asyncio.to_thread(handler, {}, MagicMock())

            # Handler succeeds despite missing events package
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["status"] == "completed"
        finally:
            if original is not None:
                sys.modules["autom8y_events"] = original
            else:
                sys.modules.pop("autom8y_events", None)

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_event_includes_dry_run_from_params(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
    ) -> None:
        """dry_run flag from WorkflowResult metadata is included in event detail."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result(metadata={"dry_run": True}))
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory)

        with patch("autom8y_events.EventPublisher") as mock_publisher_cls:
            mock_publisher = MagicMock()
            mock_publisher_cls.return_value = mock_publisher

            handler = create_workflow_handler(config)
            await asyncio.to_thread(handler, {"dry_run": True}, MagicMock())

            event = mock_publisher.publish.call_args[0][0]
            assert event.detail["dry_run"] is True


class TestFleetObservability:
    """Tests for fleet-level observability (Tier 2 + 3).

    Per ADR-bridge-observability-fleet: Verify BridgeFleetHealth metric
    emission, fleet DMS timestamps, and correct opt-out behavior when
    fleet_namespace is None.
    """

    async def test_fleet_namespace_field_exists_with_correct_default(self) -> None:
        """WorkflowHandlerConfig has fleet_namespace defaulting to fleet namespace."""
        config = _make_config()
        assert config.fleet_namespace == "Autom8y/AsanaBridgeFleet"

    async def test_fleet_namespace_opt_out(self) -> None:
        """fleet_namespace=None opts a handler out of fleet observability."""
        config = _make_config(fleet_namespace=None)
        assert config.fleet_namespace is None

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_fleet_health_emitted_on_success(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """BridgeFleetHealth=1.0 emitted to fleet namespace on success."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result(succeeded=8))
        factory = MagicMock(return_value=wf)
        config = _make_config(workflow_factory=factory, workflow_id="fleet-test")

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        fleet_calls = [c for c in mock_emit.call_args_list if c[0][0] == "BridgeFleetHealth"]
        assert len(fleet_calls) == 1
        assert fleet_calls[0][0] == ("BridgeFleetHealth", 1.0)
        assert fleet_calls[0][1]["unit"] == "Count"
        assert fleet_calls[0][1]["dimensions"] == {"workflow_id": "fleet-test"}
        assert fleet_calls[0][1]["namespace"] == "Autom8y/AsanaBridgeFleet"

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_fleet_dms_emitted_on_success(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """Fleet DMS timestamp emitted to fleet namespace on success."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result(succeeded=8))
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            dms_namespace="Autom8y/AsanaInsights",
        )

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        # emit_success_timestamp should be called for both per-bridge and fleet
        ts_calls = [c[0][0] for c in mock_emit_ts.call_args_list]
        assert "Autom8y/AsanaInsights" in ts_calls
        assert "Autom8y/AsanaBridgeFleet" in ts_calls

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_fleet_failure_metric_on_validation_skip(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """BridgeFleetHealth=0.0 emitted on validation skip (kill-switch/circuit breaker)."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(validation_errors=["Circuit breaker open"])
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            workflow_id="skip-fleet-test",
        )

        handler = create_workflow_handler(config)
        result = await asyncio.to_thread(handler, {}, MagicMock())

        body = json.loads(result["body"])
        assert body["status"] == "skipped"

        fleet_calls = [c for c in mock_emit.call_args_list if c[0][0] == "BridgeFleetHealth"]
        assert len(fleet_calls) == 1
        assert fleet_calls[0][0] == ("BridgeFleetHealth", 0.0)
        assert fleet_calls[0][1]["unit"] == "Count"
        assert fleet_calls[0][1]["dimensions"] == {
            "workflow_id": "skip-fleet-test",
        }
        assert fleet_calls[0][1]["namespace"] == "Autom8y/AsanaBridgeFleet"

        # No fleet DMS should be emitted on validation skip
        ts_calls = [c[0][0] for c in mock_emit_ts.call_args_list]
        assert "Autom8y/AsanaBridgeFleet" not in ts_calls

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_no_fleet_metrics_when_namespace_none(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """No fleet metrics or DMS emitted when fleet_namespace=None."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result(succeeded=8))
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            fleet_namespace=None,
        )

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        # No BridgeFleetHealth metric should be emitted
        fleet_calls = [c for c in mock_emit.call_args_list if c[0][0] == "BridgeFleetHealth"]
        assert len(fleet_calls) == 0

        # No fleet DMS should be emitted
        ts_calls = [c[0][0] for c in mock_emit_ts.call_args_list]
        assert "Autom8y/AsanaBridgeFleet" not in ts_calls

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_no_fleet_metrics_on_validation_skip_when_namespace_none(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """No fleet failure metric on validation skip when fleet_namespace=None."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(validation_errors=["Feature flag disabled"])
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            fleet_namespace=None,
        )

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        fleet_calls = [c for c in mock_emit.call_args_list if c[0][0] == "BridgeFleetHealth"]
        assert len(fleet_calls) == 0

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    @patch("autom8_asana.client.AsanaClient")
    @patch("autom8_asana.clients.data.client.DataServiceClient")
    async def test_per_bridge_metrics_still_emitted_with_fleet(
        self,
        mock_ds_class: MagicMock,
        mock_asana_class: MagicMock,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """Existing per-bridge metrics (Tier 1) still emitted alongside fleet metrics."""
        mock_asana = MagicMock()
        mock_asana_class.return_value = mock_asana

        mock_ds = AsyncMock()
        mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
        mock_ds.__aexit__ = AsyncMock(return_value=False)
        mock_ds_class.return_value = mock_ds

        wf = _mock_workflow(result=_make_workflow_result(succeeded=8))
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            workflow_id="regression-test",
            dms_namespace="Autom8y/AsanaInsights",
        )

        handler = create_workflow_handler(config)
        await asyncio.to_thread(handler, {}, MagicMock())

        emitted_metrics = [c[0][0] for c in mock_emit.call_args_list]
        # Tier 1 per-bridge metrics must still be present
        assert "WorkflowExecutionCount" in emitted_metrics
        assert "WorkflowDuration" in emitted_metrics
        assert "WorkflowSuccessRate" in emitted_metrics
        # Tier 2 fleet metric also present
        assert "BridgeFleetHealth" in emitted_metrics

        # Per-bridge DMS still emitted alongside fleet DMS
        ts_calls = [c[0][0] for c in mock_emit_ts.call_args_list]
        assert "Autom8y/AsanaInsights" in ts_calls
        assert "Autom8y/AsanaBridgeFleet" in ts_calls


# --- SPOF-1 Chaos Experiment Tests ---
#
# Per CHAOS-spof1-bridge-fleet.md: Verify that fleet-level observability
# detects the SPOF-1 scenario (circuit breaker opens -> all bridges skip ->
# fleet alarm preconditions met).
#
# These tests simulate the N=3 fleet (insights-export, conversation-audit,
# payment-reconciliation) using the handler factory with mocked workflows.
# The injection point is validate_async() returning circuit-breaker errors,
# which is the observable contract the handler factory depends on.

# Fleet bridge configurations matching production fleet
_FLEET_BRIDGES = [
    {
        "workflow_id": "insights-export",
        "log_prefix": "lambda_insights_export",
        "dms_namespace": "Autom8y/AsanaInsights",
    },
    {
        "workflow_id": "conversation-audit",
        "log_prefix": "lambda_conversation_audit",
        "dms_namespace": "Autom8y/AsanaAudit",
    },
    {
        "workflow_id": "payment-reconciliation",
        "log_prefix": "lambda_payment_reconciliation",
        "dms_namespace": "Autom8y/AsanaReconciliation",
    },
]

_CIRCUIT_BREAKER_ERROR = "DataServiceClient circuit breaker is open. autom8_data may be degraded."


async def _invoke_fleet(
    mock_emit: MagicMock,
    mock_emit_ts: MagicMock,
    bridge_configs: list[dict],
    *,
    skip_workflow_ids: set[str] | None = None,
    validation_error: str = _CIRCUIT_BREAKER_ERROR,
) -> list[dict]:
    """Invoke all fleet bridges and return handler responses.

    Args:
        mock_emit: Patched emit_metric.
        mock_emit_ts: Patched emit_success_timestamp.
        bridge_configs: List of per-bridge config dicts.
        skip_workflow_ids: Set of workflow_ids that should return
            validation errors. If None, ALL bridges skip.
        validation_error: Error message for skipped bridges.

    Returns:
        List of handler response dicts.
    """
    if skip_workflow_ids is None:
        skip_workflow_ids = {b["workflow_id"] for b in bridge_configs}

    results = []
    for bridge in bridge_configs:
        wf_id = bridge["workflow_id"]
        should_skip = wf_id in skip_workflow_ids

        if should_skip:
            wf = _mock_workflow(validation_errors=[validation_error])
        else:
            wf = _mock_workflow(
                result=_make_workflow_result(workflow_id=wf_id, succeeded=8, total=10)
            )

        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            workflow_id=wf_id,
            log_prefix=bridge["log_prefix"],
            dms_namespace=bridge["dms_namespace"],
        )

        handler = create_workflow_handler(config)

        # Patch AsanaClient and DataServiceClient for each handler invocation
        with (
            patch("autom8_asana.client.AsanaClient") as mock_asana_class,
            patch("autom8_asana.clients.data.client.DataServiceClient") as mock_ds_class,
        ):
            mock_asana_class.return_value = MagicMock()
            mock_ds = AsyncMock()
            mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
            mock_ds.__aexit__ = AsyncMock(return_value=False)
            mock_ds_class.return_value = mock_ds

            result = await asyncio.to_thread(handler, {}, MagicMock())
            results.append(result)

    return results


class TestSPOF1Detection:
    """SPOF-1 chaos experiment: circuit breaker opens, all 3 bridges skip.

    Per CHAOS-spof1-bridge-fleet.md Section 4.1.

    Hypothesis: When the DataServiceClient circuit breaker is open,
    fleet-level alarms detect the failure because:
    - BridgeFleetHealth=0.0 emitted for all 3 bridges
    - Fleet DMS not refreshed (staleness signal)
    - Per-bridge DMS not refreshed
    """

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_all_bridges_skip_when_circuit_breaker_open(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """All 3 bridges return skipped status when circuit breaker is open."""
        results = await _invoke_fleet(mock_emit, mock_emit_ts, _FLEET_BRIDGES)

        for i, result in enumerate(results):
            body = json.loads(result["body"])
            assert body["status"] == "skipped", (
                f"Bridge {_FLEET_BRIDGES[i]['workflow_id']} "
                f"should be skipped but got {body['status']}"
            )
            assert body["reason"] == "validation_failed"
            assert _CIRCUIT_BREAKER_ERROR in body["errors"]

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_fleet_health_zero_for_all_bridges(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """BridgeFleetHealth=0.0 emitted for all 3 bridges on SPOF-1."""
        await _invoke_fleet(mock_emit, mock_emit_ts, _FLEET_BRIDGES)

        fleet_health_calls = [c for c in mock_emit.call_args_list if c[0][0] == "BridgeFleetHealth"]

        # Exactly 3 fleet health emissions (one per bridge)
        assert len(fleet_health_calls) == 3

        # All values are 0.0
        for call in fleet_health_calls:
            assert call[0][1] == 0.0, f"BridgeFleetHealth should be 0.0 but got {call[0][1]}"
            assert call[1]["namespace"] == "Autom8y/AsanaBridgeFleet"

        # Each bridge's workflow_id is represented
        emitted_workflow_ids = {call[1]["dimensions"]["workflow_id"] for call in fleet_health_calls}
        expected_workflow_ids = {b["workflow_id"] for b in _FLEET_BRIDGES}
        assert emitted_workflow_ids == expected_workflow_ids

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_fleet_dms_not_emitted_on_fleet_skip(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """Fleet DMS timestamp NOT emitted when all bridges skip (staleness signal)."""
        await _invoke_fleet(mock_emit, mock_emit_ts, _FLEET_BRIDGES)

        ts_namespaces = [c[0][0] for c in mock_emit_ts.call_args_list]
        assert "Autom8y/AsanaBridgeFleet" not in ts_namespaces, (
            "Fleet DMS should NOT be refreshed during SPOF-1 -- staleness is the detection signal"
        )

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_per_bridge_dms_not_emitted_on_skip(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """Per-bridge DMS timestamps NOT emitted when all bridges skip."""
        await _invoke_fleet(mock_emit, mock_emit_ts, _FLEET_BRIDGES)

        ts_namespaces = [c[0][0] for c in mock_emit_ts.call_args_list]

        for bridge in _FLEET_BRIDGES:
            assert bridge["dms_namespace"] not in ts_namespaces, (
                f"Per-bridge DMS for {bridge['workflow_id']} should NOT be refreshed during SPOF-1"
            )

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_validation_skipped_emitted_for_all_bridges(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """WorkflowValidationSkipped=1 emitted for all 3 bridges."""
        await _invoke_fleet(mock_emit, mock_emit_ts, _FLEET_BRIDGES)

        skip_calls = [c for c in mock_emit.call_args_list if c[0][0] == "WorkflowValidationSkipped"]

        assert len(skip_calls) == 3

        skipped_workflow_ids = {call[1]["dimensions"]["workflow_id"] for call in skip_calls}
        expected_workflow_ids = {b["workflow_id"] for b in _FLEET_BRIDGES}
        assert skipped_workflow_ids == expected_workflow_ids

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_no_success_metrics_emitted_on_fleet_skip(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """No WorkflowDuration or WorkflowSuccessRate emitted during SPOF-1."""
        await _invoke_fleet(mock_emit, mock_emit_ts, _FLEET_BRIDGES)

        emitted_metrics = [c[0][0] for c in mock_emit.call_args_list]

        assert "WorkflowDuration" not in emitted_metrics, (
            "WorkflowDuration should NOT be emitted when all bridges skip"
        )
        assert "WorkflowSuccessRate" not in emitted_metrics, (
            "WorkflowSuccessRate should NOT be emitted when all bridges skip"
        )


class TestSPOF1FalsePositive:
    """False positive check: single bridge disabled should NOT trigger fleet alarm.

    Per CHAOS-spof1-bridge-fleet.md Section 5.

    Scenario: 1 of 3 bridges has its kill-switch tripped (validation skip).
    The other 2 bridges succeed normally. The fleet DMS should be refreshed
    by the successful bridges, so the fleet alarm stays in OK state.
    """

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_single_bridge_skip_does_not_suppress_fleet_dms(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """Fleet DMS IS refreshed when only 1 of 3 bridges skips."""
        await _invoke_fleet(
            mock_emit,
            mock_emit_ts,
            _FLEET_BRIDGES,
            skip_workflow_ids={"insights-export"},
            validation_error="Workflow disabled via AUTOM8_EXPORT_ENABLED=false",
        )

        ts_namespaces = [c[0][0] for c in mock_emit_ts.call_args_list]

        # Fleet DMS should be refreshed by the 2 successful bridges
        assert ts_namespaces.count("Autom8y/AsanaBridgeFleet") == 2, (
            "Fleet DMS should be refreshed by the 2 successful bridges"
        )

        # Per-bridge DMS should be refreshed for the 2 successful bridges
        assert "Autom8y/AsanaAudit" in ts_namespaces
        assert "Autom8y/AsanaReconciliation" in ts_namespaces

        # Per-bridge DMS should NOT be refreshed for the skipped bridge
        assert "Autom8y/AsanaInsights" not in ts_namespaces

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_partial_fleet_health_mixed_values(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """BridgeFleetHealth=0.0 for skipped bridge, 1.0 for succeeded bridges."""
        await _invoke_fleet(
            mock_emit,
            mock_emit_ts,
            _FLEET_BRIDGES,
            skip_workflow_ids={"insights-export"},
            validation_error="Workflow disabled via AUTOM8_EXPORT_ENABLED=false",
        )

        fleet_health_calls = [c for c in mock_emit.call_args_list if c[0][0] == "BridgeFleetHealth"]

        # 3 fleet health emissions (one per bridge)
        assert len(fleet_health_calls) == 3

        health_by_wf = {
            call[1]["dimensions"]["workflow_id"]: call[0][1] for call in fleet_health_calls
        }

        # Skipped bridge emits 0.0
        assert health_by_wf["insights-export"] == 0.0, (
            "Skipped bridge should emit BridgeFleetHealth=0.0"
        )

        # Succeeded bridges emit 1.0
        assert health_by_wf["conversation-audit"] == 1.0, (
            "Succeeded bridge should emit BridgeFleetHealth=1.0"
        )
        assert health_by_wf["payment-reconciliation"] == 1.0, (
            "Succeeded bridge should emit BridgeFleetHealth=1.0"
        )


class TestSPOF1Recovery:
    """Recovery verification: after circuit breaker clears, fleet DMS refreshes.

    Per CHAOS-spof1-bridge-fleet.md Section 6.

    Scenario: All 3 bridges previously skipped (SPOF-1 active). Circuit
    breaker recovers. The next invocation of a single bridge succeeds,
    which refreshes the fleet DMS and BridgeFleetHealth for that bridge.
    """

    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_success_timestamp")
    @patch("autom8_asana.lambda_handlers.workflow_handler.emit_metric")
    async def test_recovery_after_circuit_breaker_clears(
        self,
        mock_emit: MagicMock,
        mock_emit_ts: MagicMock,
    ) -> None:
        """After recovery: fleet DMS refreshed, BridgeFleetHealth=1.0, per-bridge DMS refreshed."""
        # Phase 1: SPOF-1 active -- all bridges skip
        await _invoke_fleet(mock_emit, mock_emit_ts, _FLEET_BRIDGES)

        # Verify SPOF-1 state: no fleet DMS
        ts_namespaces_phase1 = [c[0][0] for c in mock_emit_ts.call_args_list]
        assert "Autom8y/AsanaBridgeFleet" not in ts_namespaces_phase1

        # Phase 2: Circuit breaker recovers. Reset mocks.
        mock_emit.reset_mock()
        mock_emit_ts.reset_mock()

        # Only insights-export runs (it is the daily bridge, first to recover).
        # The other two bridges have not been invoked yet.
        recovered_bridge = _FLEET_BRIDGES[0]  # insights-export
        wf = _mock_workflow(
            result=_make_workflow_result(
                workflow_id=recovered_bridge["workflow_id"],
                succeeded=8,
                total=10,
            )
        )
        factory = MagicMock(return_value=wf)
        config = _make_config(
            workflow_factory=factory,
            workflow_id=recovered_bridge["workflow_id"],
            log_prefix=recovered_bridge["log_prefix"],
            dms_namespace=recovered_bridge["dms_namespace"],
        )

        handler = create_workflow_handler(config)

        with (
            patch("autom8_asana.client.AsanaClient") as mock_asana_class,
            patch("autom8_asana.clients.data.client.DataServiceClient") as mock_ds_class,
        ):
            mock_asana_class.return_value = MagicMock()
            mock_ds = AsyncMock()
            mock_ds.__aenter__ = AsyncMock(return_value=mock_ds)
            mock_ds.__aexit__ = AsyncMock(return_value=False)
            mock_ds_class.return_value = mock_ds

            result = await asyncio.to_thread(handler, {}, MagicMock())

        # Verify recovery
        body = json.loads(result["body"])
        assert body["status"] == "completed", "Recovered bridge should complete successfully"

        # Fleet DMS should be refreshed
        ts_namespaces_phase2 = [c[0][0] for c in mock_emit_ts.call_args_list]
        assert "Autom8y/AsanaBridgeFleet" in ts_namespaces_phase2, (
            "Fleet DMS should be refreshed after recovery"
        )

        # Per-bridge DMS for recovered bridge should be refreshed
        assert recovered_bridge["dms_namespace"] in ts_namespaces_phase2, (
            f"Per-bridge DMS for {recovered_bridge['workflow_id']} "
            f"should be refreshed after recovery"
        )

        # BridgeFleetHealth=1.0 for recovered bridge
        fleet_health_calls = [c for c in mock_emit.call_args_list if c[0][0] == "BridgeFleetHealth"]
        assert len(fleet_health_calls) == 1
        assert fleet_health_calls[0][0][1] == 1.0, (
            "Recovered bridge should emit BridgeFleetHealth=1.0"
        )
        assert (
            fleet_health_calls[0][1]["dimensions"]["workflow_id"]
            == (recovered_bridge["workflow_id"])
        )
