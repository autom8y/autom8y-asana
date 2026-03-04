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
from autom8y_telemetry.aws import emit_success_timestamp, instrument_lambda

from autom8_asana.core.scope import EntityScope
from autom8_asana.lambda_handlers.cloudwatch import emit_metric

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.automation.workflows.base import WorkflowAction

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
    """

    workflow_factory: Callable[..., WorkflowAction]
    workflow_id: str
    log_prefix: str
    default_params: dict[str, Any] = field(default_factory=dict)
    response_metadata_keys: tuple[str, ...] = ()
    requires_data_client: bool = True
    dms_namespace: str | None = None


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
            Exception
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
                return await _validate_enumerate_and_run(workflow, scope, params)
        else:
            workflow = config.workflow_factory(asana_client, None)
            return await _validate_enumerate_and_run(workflow, scope, params)

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

        # Dead-man's-switch: record successful completion timestamp.
        # Emitted only when a dms_namespace is configured and the workflow
        # completed without total failure.
        if config.dms_namespace:
            emit_success_timestamp(config.dms_namespace)

        return {
            "statusCode": 200,
            "body": json.dumps(
                result.to_response_dict(
                    extra_metadata_keys=list(config.response_metadata_keys),
                )
            ),
        }

    return handler
