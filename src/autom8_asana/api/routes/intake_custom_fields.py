"""Intake custom field write route.

POST /v1/tasks/{task_gid}/custom-fields - Write custom fields by name.

Resolves field descriptor names to Asana custom field GIDs internally,
then writes all resolved fields in a single Asana API update call.

Authentication:
    All routes require service token (S2S JWT) authentication.
    PAT tokens are NOT supported.
"""

from __future__ import annotations

import time
from typing import Annotated

from autom8y_log import get_logger
from fastapi import Depends

from autom8_asana import AsanaClient
from autom8_asana.api.dependencies import (  # noqa: TC001 -- FastAPI resolves these at runtime
    AuthContextDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.intake_custom_fields_models import (
    CustomFieldWriteRequest,
    CustomFieldWriteResponse,
)
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.errors import NotFoundError, RateLimitError
from autom8_asana.services.intake_custom_field_service import IntakeCustomFieldService

__all__ = ["router"]

logger = get_logger(__name__)

router = s2s_router(
    prefix="/v1/tasks", tags=["intake-custom-fields"], include_in_schema=False
)


@router.post(
    "/{task_gid}/custom-fields",
    response_model=CustomFieldWriteResponse,
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "task_custom_fields"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-rate-limit": {"tier": "external"},
    },
)
async def write_custom_fields(
    task_gid: str,
    body: CustomFieldWriteRequest,
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> CustomFieldWriteResponse:
    """Write custom field values to an Asana task.

    Resolves field names to Asana custom field GIDs internally.
    Supports partial success: some fields may succeed while others fail.

    Authentication: S2S JWT only (require_service_claims dependency).

    Path Parameters:
        task_gid: Asana task GID.

    Request Body:
        CustomFieldWriteRequest with fields dict.

    Returns:
        CustomFieldWriteResponse with write count and error list.

    Error Responses:
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 404 TASK_NOT_FOUND: task_gid not found in Asana
        - 422 EMPTY_FIELDS: Empty fields dict
        - 429 RATE_LIMITED: Asana rate limit exceeded
        - 503 ASANA_UNAVAILABLE: Asana API failure
    """
    start_time = time.monotonic()

    logger.info(
        "intake_custom_fields_request",
        extra={
            "request_id": request_id,
            "task_gid": task_gid,
            "field_count": len(body.fields),
            "caller_service": claims.service_name,
        },
    )

    # Validate non-empty fields
    if not body.fields:
        raise_api_error(
            request_id,
            422,
            "EMPTY_FIELDS",
            "At least one field is required",
        )

    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = IntakeCustomFieldService(client)
            result = await service.write_fields(
                task_gid=task_gid,
                fields=body.fields,
            )
    except NotFoundError:
        raise_api_error(
            request_id,
            404,
            "TASK_NOT_FOUND",
            f"Task not found: {task_gid}",
        )
    except RateLimitError as exc:
        retry_after = getattr(exc, "retry_after", None) or 60
        raise_api_error(
            request_id,
            429,
            "RATE_LIMITED",
            "Rate limit exceeded. Please retry after backoff.",
            headers={"Retry-After": str(retry_after)},
        )
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "intake_custom_fields_error",
            extra={
                "request_id": request_id,
                "task_gid": task_gid,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            "Failed to write custom fields. Asana service unavailable.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "intake_custom_fields_complete",
        extra={
            "request_id": request_id,
            "task_gid": task_gid,
            "fields_written": result.fields_written,
            "error_count": len(result.errors),
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return result
