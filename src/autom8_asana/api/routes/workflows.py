"""Workflow invocation API endpoint.

Per TDD-ENTITY-SCOPE-001 Section 2.7: Production-grade endpoint for
invoking workflows against specific entities. Supports dual-mode auth,
rate limiting, audit logging, and timeout-aware execution.

POST /api/v1/workflows/{workflow_id}/invoke
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger
from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator

from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.rate_limit import limiter
from autom8_asana.core.scope import EntityScope

if TYPE_CHECKING:
    from autom8_asana.api.dependencies import (
        AuthContextDep,
        RequestId,
    )
    from autom8_asana.lambda_handlers.workflow_handler import WorkflowHandlerConfig

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

# Default timeout for workflow execution (seconds)
WORKFLOW_EXECUTION_TIMEOUT = 120

# Populated at startup from Lambda handler configs
_WORKFLOW_CONFIGS: dict[str, WorkflowHandlerConfig] = {}


# --- Request/Response Models ---


class WorkflowInvokeRequest(BaseModel):
    """Request body for workflow invocation.

    Attributes:
        entity_ids: List of Asana GIDs to target. Must be non-empty.
        dry_run: If True, skip write operations.
        params: Additional workflow-specific parameter overrides.
    """

    entity_ids: list[str]
    dry_run: bool = False
    params: dict[str, Any] = {}

    @field_validator("entity_ids")
    @classmethod
    def validate_entity_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("entity_ids must be a non-empty list")
        if len(v) > 100:
            raise ValueError("entity_ids must contain at most 100 items")
        for gid in v:
            if not gid.isdigit():
                raise ValueError(
                    f"Invalid entity_id '{gid}': must be numeric (Asana GID format)"
                )
        return v


class WorkflowInvokeResponse(BaseModel):
    """Response body wrapping WorkflowResult.

    Attributes:
        request_id: Correlation ID for this invocation.
        invocation_source: Always "api" for this endpoint.
        workflow_id: ID of the invoked workflow.
        dry_run: Whether this was a dry-run invocation.
        entity_count: Number of entities processed.
        result: Serialized WorkflowResult.
    """

    request_id: str
    invocation_source: str = "api"
    workflow_id: str
    dry_run: bool
    entity_count: int
    result: dict[str, Any]


# --- Registry Functions ---


def register_workflow_config(config: WorkflowHandlerConfig) -> None:
    """Register a workflow config for API invocation.

    Args:
        config: WorkflowHandlerConfig from Lambda handler module.
    """
    _WORKFLOW_CONFIGS[config.workflow_id] = config


def _get_workflow_factory(workflow_id: str) -> WorkflowHandlerConfig | None:
    """Look up workflow config by ID.

    Args:
        workflow_id: Registered workflow identifier.

    Returns:
        WorkflowHandlerConfig if found, else None.
    """
    return _WORKFLOW_CONFIGS.get(workflow_id)


# --- Route Handler ---


@router.post(
    "/{workflow_id}/invoke",
    response_model=WorkflowInvokeResponse,
    responses={
        400: {"description": "Validation error (empty entity_ids, non-numeric GID)"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Unknown workflow_id"},
        422: {"description": "Workflow pre-flight validation failed"},
        429: {"description": "Rate limit exceeded"},
        504: {"description": "Workflow execution timed out"},
    },
)
@limiter.limit("10/minute")
async def invoke_workflow(
    workflow_id: str,
    body: WorkflowInvokeRequest,
    request: Request,
    auth_context: AuthContextDep,
    request_id: RequestId,
) -> WorkflowInvokeResponse:
    """Invoke a workflow for specific entities.

    Production endpoint: rate limited, audit logged, timeout-aware.

    Constructs workflow with per-request clients, calls enumerate_async
    with targeted scope, then execute_async with the entity list.
    """
    # Audit log (full invocation context)
    logger.info(
        "workflow_invoke_api",
        workflow_id=workflow_id,
        entity_ids=body.entity_ids,
        dry_run=body.dry_run,
        request_id=request_id,
        caller_service=auth_context.caller_service,
        auth_mode=auth_context.mode.value,
    )

    # Look up workflow factory config
    factory_config = _get_workflow_factory(workflow_id)
    if factory_config is None:
        raise_api_error(
            request_id,
            404,
            "WORKFLOW_NOT_FOUND",
            f"Workflow '{workflow_id}' is not registered for API invocation",
        )

    # Construct EntityScope
    scope = EntityScope(
        entity_ids=tuple(body.entity_ids),
        dry_run=body.dry_run,
    )

    # Build params: factory defaults + request overrides + scope
    params: dict[str, Any] = {**factory_config.default_params}
    params.update(body.params)
    params["workflow_id"] = workflow_id
    params.update(scope.to_params())

    # Construct workflow with per-request clients
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient

    asana_client = AsanaClient(token=auth_context.asana_pat)

    try:
        if factory_config.requires_data_client:
            async with DataServiceClient() as data_client:
                workflow = factory_config.workflow_factory(asana_client, data_client)
                result = await _validate_enumerate_execute(
                    workflow, scope, params, request_id, WORKFLOW_EXECUTION_TIMEOUT
                )
        else:
            workflow = factory_config.workflow_factory(asana_client, None)
            result = await _validate_enumerate_execute(
                workflow, scope, params, request_id, WORKFLOW_EXECUTION_TIMEOUT
            )
    except TimeoutError:
        logger.error(
            "workflow_invoke_timeout",
            workflow_id=workflow_id,
            request_id=request_id,
            timeout_seconds=WORKFLOW_EXECUTION_TIMEOUT,
        )
        raise_api_error(
            request_id,
            504,
            "WORKFLOW_TIMEOUT",
            f"Workflow execution timed out after {WORKFLOW_EXECUTION_TIMEOUT}s",
        )

    # Emit metric
    from autom8_asana.lambda_handlers.cloudwatch import emit_metric

    emit_metric(
        "WorkflowInvokeCount",
        1,
        dimensions={
            "workflow_id": workflow_id,
            "source": "api",
            "dry_run": str(body.dry_run).lower(),
        },
    )

    # Audit log completion
    logger.info(
        "workflow_invoke_completed",
        workflow_id=workflow_id,
        request_id=request_id,
        succeeded=result.succeeded,
        failed=result.failed,
        duration_seconds=round(result.duration_seconds, 2),
    )

    return WorkflowInvokeResponse(
        request_id=request_id,
        invocation_source="api",
        workflow_id=workflow_id,
        dry_run=body.dry_run,
        entity_count=result.total,
        result=result.to_response_dict(
            extra_metadata_keys=list(factory_config.response_metadata_keys),
        ),
    )


async def _validate_enumerate_execute(
    workflow: Any,
    scope: EntityScope,
    params: dict[str, Any],
    request_id: str,
    timeout_seconds: int,
) -> Any:
    """Validate, enumerate, and execute with timeout.

    Args:
        workflow: WorkflowAction instance.
        scope: EntityScope for enumeration.
        params: Merged workflow params.
        request_id: Request correlation ID.
        timeout_seconds: Max execution time.

    Returns:
        WorkflowResult from execute_async.

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout.
    """
    # Pre-flight validation
    validation_errors = await workflow.validate_async()
    if validation_errors:
        raise_api_error(
            request_id,
            422,
            "WORKFLOW_VALIDATION_FAILED",
            "Workflow pre-flight validation failed",
            details={"validation_errors": validation_errors},
        )

    # Enumerate + execute with timeout
    async def _run() -> Any:
        entities = await workflow.enumerate_async(scope)
        return await workflow.execute_async(entities, params)

    return await asyncio.wait_for(_run(), timeout=timeout_seconds)
