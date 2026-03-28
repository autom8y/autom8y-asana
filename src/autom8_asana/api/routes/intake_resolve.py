"""Intake resolve routes for business and contact resolution.

POST /v1/resolve/business - Resolve business by phone/vertical
POST /v1/resolve/contact  - Resolve contact by email/phone within business scope

Per ADR-INT-001: Never return 404 for not-found; use found=False.
Per ADR-INT-002: Email-then-phone priority, NO name matching.

Authentication:
    All routes require service token (S2S JWT) authentication.
    PAT tokens are NOT supported.
"""

from __future__ import annotations

import time
from typing import Annotated

from autom8y_log import get_logger
from fastapi import Depends
from autom8_asana.api.routes._security import s2s_router

from autom8_asana import AsanaClient
from autom8_asana.api.dependencies import (  # noqa: TC001 -- FastAPI resolves these at runtime
    AuthContextDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.routes.intake_resolve_models import (
    BusinessResolveRequest,
    BusinessResolveResponse,
    ContactResolveRequest,
    ContactResolveResponse,
)
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.services.intake_resolve_service import (
    IntakeResolveService,
    is_valid_e164,
)

__all__ = ["router"]

logger = get_logger(__name__)

router = s2s_router(prefix="/v1", tags=["intake-resolve"], include_in_schema=False)


# ---------------------------------------------------------------------------
# POST /v1/resolve/business
# ---------------------------------------------------------------------------


@router.post("/resolve/business", response_model=BusinessResolveResponse)
async def resolve_business(
    body: BusinessResolveRequest,
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> BusinessResolveResponse:
    """Resolve business by phone via GidLookupIndex O(1).

    Authentication: S2S JWT only (require_service_claims dependency).

    Request Body:
        BusinessResolveRequest with office_phone and optional vertical.

    Returns:
        BusinessResolveResponse with found=True/False.
        Never returns 404 for not-found (ADR-INT-001).

    Error Responses:
        - 400 INVALID_PHONE_FORMAT: Phone not in E.164 format
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 503 INDEX_NOT_READY: GidLookupIndex not initialized
    """
    start_time = time.monotonic()

    logger.info(
        "intake_resolve_business_request",
        extra={
            "request_id": request_id,
            "office_phone": body.office_phone[:6] + "****",  # Redact for logs
            "vertical": body.vertical,
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

    # Resolve via service layer
    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = IntakeResolveService(client)
            result = await service.resolve_business(
                office_phone=body.office_phone,
                vertical=body.vertical,
            )
    except RuntimeError as exc:
        if "not initialized" in str(exc).lower() or "not ready" in str(exc).lower():
            raise_api_error(
                request_id,
                503,
                "INDEX_NOT_READY",
                "GidLookupIndex is not yet populated. Retry after service initialization.",
            )
        raise
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "intake_resolve_business_error",
            extra={
                "request_id": request_id,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            "Failed to resolve business. Asana service unavailable.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "intake_resolve_business_complete",
        extra={
            "request_id": request_id,
            "found": result.found,
            "task_gid": result.task_gid,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return result


# ---------------------------------------------------------------------------
# POST /v1/resolve/contact
# ---------------------------------------------------------------------------


@router.post("/resolve/contact", response_model=ContactResolveResponse)
async def resolve_contact(
    body: ContactResolveRequest,
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> ContactResolveResponse:
    """Resolve contact within a business scope.

    Single algorithm: email (exact) -> phone (exact) -> no match.
    Name matching is deliberately excluded (ADR-INT-002).

    Authentication: S2S JWT only (require_service_claims dependency).

    Request Body:
        ContactResolveRequest with business_gid, optional email, optional phone.

    Returns:
        ContactResolveResponse with found=True/False and match_field.
        Never returns 404 for not-found contact.

    Error Responses:
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 404 BUSINESS_NOT_FOUND: business_gid not found in Asana
        - 422 MISSING_CRITERIA: Neither email nor phone provided
    """
    start_time = time.monotonic()

    logger.info(
        "intake_resolve_contact_request",
        extra={
            "request_id": request_id,
            "business_gid": body.business_gid,
            "has_email": body.email is not None,
            "has_phone": body.phone is not None,
            "caller_service": claims.service_name,
        },
    )

    # Validate at least one criterion
    if body.email is None and body.phone is None:
        raise_api_error(
            request_id,
            422,
            "MISSING_CRITERIA",
            "At least one of email or phone is required",
        )

    # Resolve via service layer
    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = IntakeResolveService(client)
            result = await service.resolve_contact(
                business_gid=body.business_gid,
                email=body.email,
                phone=body.phone,
            )
    except LookupError:
        raise_api_error(
            request_id,
            404,
            "BUSINESS_NOT_FOUND",
            f"Business task not found: {body.business_gid}",
        )
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "intake_resolve_contact_error",
            extra={
                "request_id": request_id,
                "business_gid": body.business_gid,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            "Failed to resolve contact. Asana service unavailable.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "intake_resolve_contact_complete",
        extra={
            "request_id": request_id,
            "business_gid": body.business_gid,
            "found": result.found,
            "match_field": result.match_field,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return result
