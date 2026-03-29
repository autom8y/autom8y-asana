"""Intake creation and routing routes.

POST /v1/intake/business - Create full business hierarchy (7-phase SaveSession)
POST /v1/intake/route    - Route a unit to a process type

Per IMPL spec sections 3 and 4:
- SaveSession phases are strictly ordered (Phase 2 parallelizes holders).
- Social profiles written as custom fields (SOCIAL-PROFILES-ORPHANED fix).
- Address uses postal_code (ZIP-MISMATCH fix).
- Idempotent: existing process returns is_new=False, not 409.

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
from autom8_asana.api.routes.intake_create_models import (
    IntakeBusinessCreateRequest,
    IntakeBusinessCreateResponse,
    IntakeRouteRequest,
    IntakeRouteResponse,
)
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.services.intake_create_service import (
    VALID_PROCESS_TYPES,
    IntakeCreateService,
)
from autom8_asana.services.intake_resolve_service import is_valid_e164

__all__ = ["router"]

logger = get_logger(__name__)

router = s2s_router(prefix="/v1/intake", tags=["intake-create"], include_in_schema=False)


# ---------------------------------------------------------------------------
# POST /v1/intake/business
# ---------------------------------------------------------------------------


@router.post(
    "/business",
    response_model=IntakeBusinessCreateResponse,
    status_code=201,
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "business_task"},
        ],
        "x-fleet-idempotency": {"idempotent": False, "key_source": None},
        "x-fleet-references": {"service": "autom8y-data", "entity": "business"},
    },
)
async def create_intake_business(
    body: IntakeBusinessCreateRequest,
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> IntakeBusinessCreateResponse:
    """Create full Asana entity hierarchy for a new business.

    Executes 7-phase SaveSession creation chain:
    1. Create Business task
    2. Create 7 holder subtasks (parallel)
    3. Create Unit subtask
    4. Create Contact subtask
    5. Route Process (if config provided)
    6. Write social profiles as custom fields
    7. Write address to location_holder

    Authentication: S2S JWT only (require_service_claims dependency).

    Request Body:
        IntakeBusinessCreateRequest with business, contact, and optional process data.

    Returns:
        201: IntakeBusinessCreateResponse with all entity GIDs.

    Error Responses:
        - 400 INVALID_PHONE_FORMAT: Phone not in E.164 format
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 422 UNKNOWN_PROCESS_TYPE: Invalid process_type
        - 503 PROJECT_NOT_CONFIGURED: Business project not registered
        - 503 ASANA_UNAVAILABLE: Asana API failure
    """
    start_time = time.monotonic()

    logger.info(
        "intake_create_business_request",
        extra={
            "request_id": request_id,
            "business_name": body.name,
            "office_phone": body.office_phone[:6] + "****",  # Redact for logs
            "vertical": body.vertical,
            "has_process": body.process is not None,
            "social_profile_count": len(body.social_profiles),
            "has_address": body.address is not None,
            "caller_service": claims.service_name,
        },
    )

    # Validate phone format
    if not is_valid_e164(body.office_phone):
        raise_api_error(
            request_id,
            400,
            "INVALID_PHONE_FORMAT",
            f"Phone must be in E.164 format (e.g., +15551234567). Got: {body.office_phone}",
        )

    # Validate process_type if provided
    if (
        body.process is not None
        and body.process.process_type not in VALID_PROCESS_TYPES
    ):
        raise_api_error(
            request_id,
            422,
            "UNKNOWN_PROCESS_TYPE",
            f"Unknown process type: {body.process.process_type}. "
            f"Valid types: {', '.join(sorted(VALID_PROCESS_TYPES))}",
        )

    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = IntakeCreateService(client)
            result = await service.create_business_hierarchy(request=body)
    except LookupError as exc:
        if "project" in str(exc).lower() or "not configured" in str(exc).lower():
            raise_api_error(
                request_id,
                503,
                "PROJECT_NOT_CONFIGURED",
                "Business project not configured. Service initialization incomplete.",
            )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            f"Resource not found: {exc}",
        )
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "intake_create_business_error",
            extra={
                "request_id": request_id,
                "business_name": body.name,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            "Failed to create business hierarchy. Asana service unavailable.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "intake_create_business_complete",
        extra={
            "request_id": request_id,
            "business_gid": result.business_gid,
            "unit_gid": result.unit_gid,
            "contact_gid": result.contact_gid,
            "process_gid": result.process_gid,
            "holder_count": len(result.holders),
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return result


# ---------------------------------------------------------------------------
# POST /v1/intake/route
# ---------------------------------------------------------------------------


@router.post(
    "/route",
    response_model=IntakeRouteResponse,
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "process_task"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-references": {"service": "autom8y-asana", "entity": "unit"},
    },
)
async def route_intake_process(
    body: IntakeRouteRequest,
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> IntakeRouteResponse:
    """Route a unit to a specific process type.

    Idempotent: if an open process of the same type exists under the unit,
    returns it with is_new=False (200). Otherwise creates a new process (200).

    Authentication: S2S JWT only (require_service_claims dependency).

    Request Body:
        IntakeRouteRequest with unit_gid, process_type, optional due_at/assignee.

    Returns:
        IntakeRouteResponse with process GID and is_new flag.

    Error Responses:
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 404 UNIT_NOT_FOUND: unit_gid not found in Asana
        - 422 UNKNOWN_PROCESS_TYPE: Invalid process_type
        - 503 ASANA_UNAVAILABLE: Asana API failure
    """
    start_time = time.monotonic()

    logger.info(
        "intake_route_request",
        extra={
            "request_id": request_id,
            "unit_gid": body.unit_gid,
            "process_type": body.process_type,
            "has_assignee": body.assignee_name is not None,
            "has_due_at": body.due_at is not None,
            "triggered_by": body.triggered_by,
            "caller_service": claims.service_name,
        },
    )

    # Validate process_type
    if body.process_type not in VALID_PROCESS_TYPES:
        raise_api_error(
            request_id,
            422,
            "UNKNOWN_PROCESS_TYPE",
            f"Unknown process type: {body.process_type}. "
            f"Valid types: {', '.join(sorted(VALID_PROCESS_TYPES))}",
        )

    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = IntakeCreateService(client)
            result = await service.route_process(
                unit_gid=body.unit_gid,
                process_type=body.process_type,
                due_at=body.due_at,
                assignee_name=body.assignee_name,
                triggered_by=body.triggered_by,
            )
    except LookupError:
        raise_api_error(
            request_id,
            404,
            "UNIT_NOT_FOUND",
            f"Unit not found: {body.unit_gid}",
        )
    except ValueError as exc:
        raise_api_error(
            request_id,
            422,
            "UNKNOWN_PROCESS_TYPE",
            str(exc),
        )
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "intake_route_error",
            extra={
                "request_id": request_id,
                "unit_gid": body.unit_gid,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            "Failed to route process. Asana service unavailable.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "intake_route_complete",
        extra={
            "request_id": request_id,
            "unit_gid": body.unit_gid,
            "process_gid": result.process_gid,
            "process_type": result.process_type,
            "is_new": result.is_new,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return result
