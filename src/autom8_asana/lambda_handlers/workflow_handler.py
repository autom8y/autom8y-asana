"""Generic factory for workflow Lambda handlers.

Produces standardized Lambda handlers for any :class:`WorkflowAction`,
eliminating handler-level boilerplate (client init, validation, serialization,
error handling, metric emission).

Per ADR-DRY-WORKFLOW-001: Extracted from ``insights_export.py`` and
``conversation_audit.py`` which were 95% identical.

Usage::

    from autom8_asana.lambda_handlers.workflow_handler import (
        WorkflowHandlerConfig,
        create_workflow_handler,
    )

    config = WorkflowHandlerConfig(
        workflow_factory=_create_workflow,
        workflow_id="insights-export",
        log_prefix="lambda_insights_export",
        default_params={"max_concurrency": 5},
    )

    handler = create_workflow_handler(config)
"""

from __future__ import annotations

import asyncio
import json
import traceback
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger
from autom8y_telemetry.aws import (
    emit_business_metric,
    emit_success_timestamp,
    instrument_lambda,
)

from autom8_asana.core.scope import EntityScope
from autom8_asana.lambda_handlers.cloudwatch import emit_metric

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.automation.workflows.base import WorkflowAction, WorkflowResult

logger = get_logger(__name__)


@dataclass(frozen=True)
class WorkflowHandlerConfig:
    """Configuration for a workflow Lambda handler.

    Attributes:
        workflow_factory: Callable ``(asana_client, data_client) -> WorkflowAction``.
            Uses deferred import inside the callable for cold-start optimization.
        workflow_id: Identifier for logging and metrics dimensions.
        log_prefix: Structured-log event prefix (e.g. ``"lambda_insights_export"``).
        default_params: Default params merged with event overrides.
        response_metadata_keys: Extra keys from ``WorkflowResult.metadata``
            to include in the Lambda response body.
        requires_data_client: Whether to init ``DataServiceClient`` (default True).
        dms_namespace: CloudWatch namespace for dead-man's-switch metric emission.
            When set, ``emit_success_timestamp(dms_namespace)`` is called after
            successful workflow execution. When ``None``, no DMS metric is emitted.
        fleet_namespace: CloudWatch namespace for fleet-level observability.
            When set, ``BridgeFleetHealth`` metric and fleet DMS are emitted
            after workflow execution. Defaults to the bridge fleet namespace
            so all bridge handlers participate automatically. Non-bridge
            workflows should set ``fleet_namespace=None`` to opt out.
    """

    workflow_factory: Callable[..., WorkflowAction]
    workflow_id: str
    log_prefix: str
    default_params: dict[str, Any] = field(default_factory=dict)
    response_metadata_keys: tuple[str, ...] = ()
    requires_data_client: bool = True
    dms_namespace: str | None = None
    fleet_namespace: str | None = "Autom8y/AsanaBridgeFleet"


def create_workflow_handler(
    config: WorkflowHandlerConfig,
) -> Callable[[dict[str, Any], Any], dict[str, Any]]:
    """Create a Lambda handler for a WorkflowAction.

    Returns a ``handler(event, context)`` function suitable for
    AWS Lambda's handler entry point.
    """

    @instrument_lambda
    def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
        return asyncio.run(_handler_async(event, context))

    async def _handler_async(
        event: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        try:
            return await _execute(event)
        except (
            Exception  # noqa: BLE001
        ) as exc:  # BROAD-CATCH: boundary -- lambda top-level error handler returns 500
            logger.error(
                f"{config.log_prefix}_error",
                error=str(exc),
                error_type=type(exc).__name__,
                traceback=traceback.format_exc(),
            )
            emit_metric(
                "WorkflowExecutionError",
                1,
                dimensions={"workflow_id": config.workflow_id},
            )
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "status": "error",
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                ),
            }

    async def _execute(event: dict[str, Any]) -> dict[str, Any]:
        from autom8_asana.client import AsanaClient

        logger.info(f"{config.log_prefix}_started", lambda_event=event)
        emit_metric(
            "WorkflowExecutionCount",
            1,
            dimensions={"workflow_id": config.workflow_id},
        )

        # Construct EntityScope from event
        scope = EntityScope.from_event(event)

        # Merge event overrides onto defaults (existing whitelist)
        params: dict[str, Any] = {**config.default_params}
        for key in config.default_params:
            if key in event:
                params[key] = event[key]
        params["workflow_id"] = config.workflow_id

        # Inject scope-derived params (dry_run)
        params.update(scope.to_params())

        asana_client = AsanaClient()

        if config.requires_data_client:
            from autom8_asana.clients.data.client import DataServiceClient

            async with DataServiceClient() as data_client:
                workflow = config.workflow_factory(asana_client, data_client)
                _register_workflow(workflow)
                return await _validate_enumerate_and_run(workflow, scope, params)
        else:
            workflow = config.workflow_factory(asana_client, None)
            _register_workflow(workflow)
            return await _validate_enumerate_and_run(workflow, scope, params)

    def _register_workflow(workflow: WorkflowAction) -> None:
        """Register the workflow in the per-process registry.

        Handles warm-container re-registration gracefully via
        contextlib.suppress(ValueError). Per ADR-bridge-invocation-model.
        """
        import contextlib

        from autom8_asana.automation.workflows.registry import (
            get_workflow_registry,
        )

        registry = get_workflow_registry()
        with contextlib.suppress(ValueError):
            registry.register(workflow)

    def _publish_bridge_event(result: WorkflowResult) -> None:
        """Publish BridgeExecutionComplete domain event (fire-and-forget).

        Per ADR-bridge-dispatch-model Decision 3: Emit after successful
        workflow execution. Failure to publish must NEVER fail the handler.

        The autom8y-events import is guarded so the ``events`` extra is
        truly optional -- workflows still function without it installed.

        Per ADR sync concern: EventPublisher is sync boto3. Fine in Lambda
        (already sync top-level via asyncio.run()). Must wrap in
        asyncio.to_thread() if called from ECS async path.
        """
        try:
            from autom8y_events import (
                DomainEvent,
                EventPublisher,
            )

            publisher = EventPublisher()
            event = DomainEvent(
                source="asana",
                detail_type="BridgeExecutionComplete",
                detail={
                    "workflow_id": result.workflow_id,
                    "total": result.total,
                    "succeeded": result.succeeded,
                    "failed": result.failed,
                    "skipped": result.skipped,
                    "duration_seconds": round(result.duration_seconds, 2),
                    "dry_run": result.metadata.get("dry_run", False),
                },
                idempotency_key=(f"{result.workflow_id}-{result.completed_at.isoformat()}"),
            )
            publisher.publish(event)
            logger.info(
                f"{config.log_prefix}_event_published",
                detail_type="BridgeExecutionComplete",
                workflow_id=result.workflow_id,
            )
        except ImportError:
            logger.debug(
                f"{config.log_prefix}_event_skipped",
                reason="autom8y_events not installed",
            )
        except Exception:  # BROAD-CATCH: fire-and-forget per ADR  # noqa: BLE001
            logger.warning(
                f"{config.log_prefix}_event_publish_failed",
                workflow_id=result.workflow_id,
                exc_info=True,
            )

    async def _validate_enumerate_and_run(
        workflow: WorkflowAction,
        scope: EntityScope,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        # Pre-flight validation
        validation_errors = await workflow.validate_async()
        if validation_errors:
            logger.error(
                f"{config.log_prefix}_validation_failed",
                errors=validation_errors,
            )
            emit_metric(
                "WorkflowValidationSkipped",
                1,
                dimensions={"workflow_id": config.workflow_id},
            )
            # Fleet-level failure signal on validation skip.
            # Per ADR-bridge-observability-fleet: value=0.0 indicates the
            # bridge attempted to run but was skipped (kill-switch, circuit
            # breaker). No fleet DMS is emitted -- staleness IS the signal.
            if config.fleet_namespace:
                emit_metric(
                    "BridgeFleetHealth",
                    0.0,
                    unit="Count",
                    dimensions={"workflow_id": config.workflow_id},
                    namespace=config.fleet_namespace,
                )
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "status": "skipped",
                        "reason": "validation_failed",
                        "errors": validation_errors,
                    }
                ),
            }

        # Enumerate entities
        entities = await workflow.enumerate_async(scope)

        # Execute workflow with entity list
        result = await workflow.execute_async(entities, params)

        emit_metric(
            "WorkflowDuration",
            result.duration_seconds,
            unit="Seconds",
            dimensions={"workflow_id": config.workflow_id},
        )
        emit_metric(
            "WorkflowSuccessRate",
            round(100 * (1 - result.failure_rate), 2),
            unit="Percent",
            dimensions={"workflow_id": config.workflow_id},
        )

        # Per H-006: Emit business metrics via autom8y-telemetry for
        # standardized observability. Uses computation.* namespace
        # (bridge.* namespace requires platform team approval).
        emit_business_metric(
            namespace=config.dms_namespace or "BridgeWorkflows",
            metric_name="EntitiesProcessed",
            value=result.total,
            unit="Count",
            dimensions={"workflow_id": config.workflow_id},
        )
        emit_business_metric(
            namespace=config.dms_namespace or "BridgeWorkflows",
            metric_name="WorkflowDuration",
            value=round(result.duration_seconds, 2),
            unit="Seconds",
            dimensions={"workflow_id": config.workflow_id},
        )

        # Dead-man's-switch: record successful completion timestamp.
        # Emitted only when a dms_namespace is configured and the workflow
        # completed without total failure.
        if config.dms_namespace:
            emit_success_timestamp(config.dms_namespace)

        # Fleet-level observability (Tier 2 + 3).
        # Per ADR-bridge-observability-fleet: Emit BridgeFleetHealth metric
        # and fleet DMS timestamp after successful execution. Non-blocking:
        # emit_metric() already swallows CloudWatch errors internally.
        if config.fleet_namespace:
            emit_metric(
                "BridgeFleetHealth",
                1.0 if result.succeeded > 0 else 0.0,
                unit="Count",
                dimensions={"workflow_id": config.workflow_id},
                namespace=config.fleet_namespace,
            )
            emit_success_timestamp(config.fleet_namespace)

        # Per ADR-bridge-dispatch-model Decision 3: Publish domain event
        # after successful execution. Fire-and-forget semantics.
        _publish_bridge_event(result)

        return {
            "statusCode": 200,
            "body": json.dumps(
                result.to_response_dict(
                    extra_metadata_keys=list(config.response_metadata_keys),
                )
            ),
        }

    return handler
