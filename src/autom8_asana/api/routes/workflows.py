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
from fastapi import (
    Request,  # noqa: TC002 — FastAPI resolves Request annotation via get_type_hints() at route registration; moving behind TYPE_CHECKING would raise NameError
)
from pydantic import BaseModel, ConfigDict, Field, field_validator

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    AuthContextDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.rate_limit import limiter
from autom8_asana.api.routes._security import pat_router
from autom8_asana.core.scope import EntityScope

if TYPE_CHECKING:
    from autom8_asana.lambda_handlers.workflow_handler import WorkflowHandlerConfig

logger = get_logger(__name__)

router = pat_router(prefix="/api/v1/workflows", tags=["workflows"])

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

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "entity_ids": ["1234567890123456", "1234567890123457"],
                    "dry_run": False,
                    "params": {},
                }
            ]
        },
    )

    entity_ids: list[str] = Field(
        ...,
        description=(
            "Asana GIDs of entities to process. Must be non-empty numeric strings (1–100 items)."
        ),
        examples=[["1234567890123456", "1234567890123457"]],
    )
    dry_run: bool = Field(
        default=False,
        description="If true, validate and enumerate entities but skip all write operations.",
        examples=[False],
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow-specific parameter overrides merged on top of registered defaults.",
        examples=[{}],
    )

    @field_validator("entity_ids")
    @classmethod
    def validate_entity_ids(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("entity_ids must be a non-empty list")
        if len(v) > 100:
            raise ValueError("entity_ids must contain at most 100 items")
        for gid in v:
            if not gid.isdigit():
                raise ValueError(f"Invalid entity_id '{gid}': must be numeric (Asana GID format)")
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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "request_id": "a1b2c3d4e5f67890",
                    "invocation_source": "api",
                    "workflow_id": "update-offer-status",
                    "dry_run": False,
                    "entity_count": 2,
                    "result": {
                        "succeeded": 2,
                        "failed": 0,
                        "duration_seconds": 1.42,
                    },
                }
            ]
        }
    )

    request_id: str = Field(
        ...,
        description="Request correlation ID for tracing this invocation.",
        examples=["a1b2c3d4e5f67890"],
    )
    invocation_source: str = Field(
        default="api",
        description="Origin of the invocation. Always 'api' for this endpoint.",
        examples=["api"],
    )
    workflow_id: str = Field(
        ...,
        description="Registered workflow identifier that was invoked.",
        examples=["update-offer-status"],
    )
    dry_run: bool = Field(
        ...,
        description="Whether this was a dry-run invocation (no writes performed).",
        examples=[False],
    )
    entity_count: int = Field(
        ...,
        ge=0,
        description="Number of entities that were processed.",
        examples=[2],
    )
    result: dict[str, Any] = Field(
        ...,
        description="Serialized WorkflowResult with counts and any workflow-specific metadata.",
        examples=[{"succeeded": 2, "failed": 0, "duration_seconds": 1.42}],
    )


class WorkflowEntry(BaseModel):
    """Metadata for a single registered workflow.

    Attributes:
        workflow_id: Registered workflow identifier.
        log_prefix: Structured-log event prefix for this workflow.
        requires_data_client: Whether the workflow requires a DataServiceClient.
        response_metadata_keys: Keys from WorkflowResult.metadata included in response.
    """

    workflow_id: str = Field(..., description="Registered workflow identifier.")
    log_prefix: str = Field(..., description="Structured-log event prefix.")
    requires_data_client: bool = Field(
        ..., description="Whether this workflow requires a DataServiceClient."
    )
    response_metadata_keys: list[str] = Field(
        ..., description="Metadata keys emitted by this workflow."
    )


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


# --- Route Handlers ---


@router.get(
    "/",
    summary="List registered workflows",
    description=(
        "Returns all registered workflow IDs with descriptions and configuration "
        "metadata. Use this to discover available workflows before invoking them "
        "via POST /api/v1/workflows/{workflow_id}/invoke. Each workflow entry "
        "includes its ID, log prefix, whether it requires a data-service client, "
        "and the set of response metadata keys it produces."
    ),
    response_model=SuccessResponse[list[WorkflowEntry]],
)
async def list_workflows(
    request_id: RequestId,
    auth: AuthContextDep,
) -> SuccessResponse[list[WorkflowEntry]]:
    """List all registered workflows available for invocation."""
    _ = auth  # Enforce authentication
    entries = [
        WorkflowEntry(
            workflow_id=workflow_id,
            log_prefix=config.log_prefix,
            requires_data_client=config.requires_data_client,
            response_metadata_keys=list(config.response_metadata_keys),
        )
        for workflow_id, config in _WORKFLOW_CONFIGS.items()
    ]
    return build_success_response(data=entries, request_id=request_id)


@router.post(
    "/{workflow_id}/invoke",
    summary="Invoke a workflow against specific entities",
    response_description="Workflow invocation result with counts and metadata",
    response_model=SuccessResponse[WorkflowInvokeResponse],
    responses={
        400: {"description": "Validation error (empty entity_ids, non-numeric GID)"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Unknown workflow_id"},
        422: {"description": "Workflow pre-flight validation failed"},
        429: {"description": "Rate limit exceeded (10 requests/minute)"},
        504: {"description": "Workflow execution timed out (120s limit)"},
    },
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "task"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
@limiter.limit("10/minute")
async def invoke_workflow(
    workflow_id: str,
    body: WorkflowInvokeRequest,
    request: Request,
    auth_context: AuthContextDep,
    request_id: RequestId,
) -> SuccessResponse[WorkflowInvokeResponse]:
    """Invoke a registered workflow against a list of Asana entity GIDs.

    Workflows are identified by ``workflow_id`` and must be registered
    at application startup. Use ``dry_run: true`` to validate and enumerate
    entities without performing any writes — useful for previewing impact.

    **Execution lifecycle** (per invocation):
    1. Pre-flight validation via ``workflow.validate_async()``
    2. Entity enumeration scoped to the provided ``entity_ids``
    3. Workflow execution with a 120-second timeout
    4. CloudWatch metric emission (``WorkflowInvokeCount``)

    **Rate limit**: 10 requests per minute per client.

    **Audit logging**: Every invocation is logged with workflow ID,
    entity IDs, caller service, and auth mode.

    Requires Bearer token authentication (JWT or PAT).

    **CAUTION**: Executes workflow writes against the specified entities.
    Use dry_run=true to validate without performing writes. Side effects
    are workflow-specific and may be irreversible. Rate limited to 10
    requests per minute. Hard timeout at 120 seconds.

    Args:
        workflow_id: Registered workflow identifier
            (e.g. ``"update-offer-status"``).
        body: ``entity_ids`` (1–100 numeric Asana GIDs), ``dry_run`` flag,
            and optional ``params`` overrides.

    Returns:
        Invocation result with ``succeeded``, ``failed``, ``entity_count``,
        and workflow-specific metadata.

    Raises:
        400: ``entity_ids`` is empty or contains non-numeric values.
        404: ``workflow_id`` is not registered.
        422: Workflow pre-flight validation failed.
        429: Rate limit exceeded.
        504: Execution timed out after 120 seconds.
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

    return build_success_response(
        data=WorkflowInvokeResponse(
            request_id=request_id,
            invocation_source="api",
            workflow_id=workflow_id,
            dry_run=body.dry_run,
            entity_count=result.total,
            result=result.to_response_dict(
                extra_metadata_keys=list(factory_config.response_metadata_keys),
            ),
        ),
        request_id=request_id,
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
