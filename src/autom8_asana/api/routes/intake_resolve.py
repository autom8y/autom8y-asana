"""Intake resolve routes for business and contact resolution.

POST /v1/resolve/business          - Resolve business by phone/vertical
POST /v1/resolve/contact           - Resolve contact by email/phone within business scope
POST /v1/resolve/business-by-email - Resolve business INDIRECTLY, via contact email (OW-10a)

Per ADR-INT-001: Never return 404 for not-found; use found=False.
Per ADR-INT-002: Email-then-phone priority, NO name matching.

★ PATH SHADOWING (load-bearing): every path in this module is a LITERAL that
  sits inside the subtree claimed by ``resolver.py``'s wildcard
  ``POST /v1/resolve/{entity_type}``. This router is therefore mounted BEFORE
  ``resolver_router`` in ``api/main.py`` (Starlette matches in registration
  order), and that ordering is asserted by
  ``tests/unit/api/routes/test_business_by_email.py``. Adding a literal here
  without preserving that mount order routes the request into the wildcard
  instead. The failure is loud rather than silent -- the wildcard answers
  404 UNKNOWN_ENTITY_TYPE for a non-entity segment -- but it is still a
  regression, so the order is pinned by test rather than by comment alone.

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
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.intake_resolve_models import (
    BusinessByEmailResolveRequest,
    BusinessByEmailResolveResponse,
    BusinessResolveRequest,
    BusinessResolveResponse,
    ContactResolveRequest,
    ContactResolveResponse,
)
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.services.business_by_email_service import (
    ContactIndexUnavailableError,
    redact_email,
    resolve_business_by_email,
)
from autom8_asana.services.intake_resolve_service import (
    BusinessVerificationError,
    IntakeResolveService,
    SubtaskObservationError,
    is_valid_e164,
)

__all__ = ["router"]

logger = get_logger(__name__)

router = s2s_router(prefix="/v1", tags=["intake-resolve"], include_in_schema=False)


# ---------------------------------------------------------------------------
# POST /v1/resolve/business
# ---------------------------------------------------------------------------


@router.post(
    "/resolve/business",
    response_model=SuccessResponse[BusinessResolveResponse],
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-cross-service-refs": {
            "service": "autom8y-asana",
            "entity": "business",
        },
    },
)
async def resolve_business(
    body: BusinessResolveRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[BusinessResolveResponse]:
    """Resolve a business of record by office phone (O(1) index lookup).

    Authentication: S2S JWT only (require_service_claims dependency).

    Three-outcome contract (ADR-resolve-cure-design-2026-08-08 D-2a). ABSENT and
    UNAVAILABLE are DISTINCT answers: a 200 found=false asserts the index was
    consulted successfully and the office is genuinely absent, and downstream
    consumers may act on it (the calendly pipeline answers it with CREATE). An
    index that could not be consulted, or a GID that could not be verified as a
    business, fails CLOSED with a 503 -- never found=false.

    Request Body:
        BusinessResolveRequest with office_phone and optional vertical.

    Returns:
        BusinessResolveResponse with found=True (RESOLVED) or found=False
        (ABSENT). Never returns 404 for not-found (ADR-INT-001).

    Error Responses:
        - 400 INVALID_PHONE_FORMAT: Phone not in E.164 format
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 503 INDEX_NOT_READY: business index could not be consulted or built
        - 503 BUSINESS_VERIFY_FAILED: a GID resolved but is unverified
        - 503 SUBTASK_OBSERVATION_FAILED: sub-entity listing faulted (F-9:
          never rendered as has_unit/has_contact_holder=false)
        - 503 ASANA_UNAVAILABLE: Asana call failed
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
        async with AsanaClient(token=auth.asana_pat) as client:
            service = IntakeResolveService(client)
            result = await service.resolve_business(
                office_phone=body.office_phone,
                vertical=body.vertical,
            )
    except BusinessVerificationError as exc:
        # A GID resolved but could not be verified as a business of record.
        # Fail CLOSED: found=false here would drive a duplicate CREATE.
        logger.error(
            "intake_resolve_business_unverified",
            extra={
                "request_id": request_id,
                "gid": exc.gid,
                "reason": exc.reason,
            },
        )
        raise_api_error(
            request_id,
            503,
            "BUSINESS_VERIFY_FAILED",
            "A candidate business was found but could not be verified as a business "
            "of record. No result is returned rather than an unverified one.",
        )
    except SubtaskObservationError as exc:
        # F-9 durable cure (5xx-on-subtask-fault): the business resolved, but
        # the sub-entity listing faulted. Fail CLOSED: stamping
        # has_unit/has_contact_holder=false here hands the first-create
        # tripwire a fabricated positive contradiction.
        logger.error(
            "intake_resolve_business_subtask_unobserved",
            extra={
                "request_id": request_id,
                "gid": exc.gid,
                "reason": exc.reason,
            },
        )
        raise_api_error(
            request_id,
            503,
            "SUBTASK_OBSERVATION_FAILED",
            "The business resolved but its sub-entity observation faulted. "
            "Failing closed rather than asserting unobserved sub-entity state.",
        )
    except RuntimeError as exc:
        if "not initialized" in str(exc).lower() or "not ready" in str(exc).lower():
            raise_api_error(
                request_id,
                503,
                "INDEX_NOT_READY",
                "The business index could not be consulted for this request. "
                "This is a transient service condition -- retry shortly.",
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

    return build_success_response(data=result, request_id=request_id)


# ---------------------------------------------------------------------------
# POST /v1/resolve/contact
# ---------------------------------------------------------------------------


@router.post(
    "/resolve/contact",
    response_model=SuccessResponse[ContactResolveResponse],
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-cross-service-refs": {"service": "autom8y-asana", "entity": "contact"},
    },
)
async def resolve_contact(
    body: ContactResolveRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[ContactResolveResponse]:
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
        async with AsanaClient(token=auth.asana_pat) as client:
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

    return build_success_response(data=result, request_id=request_id)


# ---------------------------------------------------------------------------
# POST /v1/resolve/business-by-email  (OW-10a email fallback)
# ---------------------------------------------------------------------------


@router.post(
    "/resolve/business-by-email",
    response_model=SuccessResponse[BusinessByEmailResolveResponse],
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-cross-service-refs": {
            "service": "autom8y-asana",
            "entity": "business",
        },
    },
)
async def resolve_business_by_email_route(
    body: BusinessByEmailResolveRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[BusinessByEmailResolveResponse]:
    """Resolve a business's office phone from a contact email (OW-10a fallback).

    A DEDICATED surface, deliberately not an extra field on
    ``POST /v1/resolve/business``. That endpoint's contract is "office_phone is
    the primary key"; its criterion is built by a registry guard that refuses
    anything other than a phone lookup, on purpose. Widening it would have to
    weaken that guard for every caller. This endpoint is additive instead: it
    walks contact_email -> contact row -> cascaded office_phone, then hands the
    phone back so the caller can use the unchanged business path.

    Authentication: S2S JWT only (require_service_claims dependency).

    UNIQUE-MATCH-ONLY. ``found=True`` requires exactly ONE distinct business.
    Zero matches, an email spanning 2+ businesses, a missing cascade, or a
    non-E.164 cascade are all ``200 found=false`` with a discriminating
    ``reason``. No row is ever guessed: the phone returned here becomes a
    business-of-record downstream, where a wrong value succeeds against the
    wrong business instead of failing.

    Three-outcome contract, inherited from the business path
    (ADR-resolve-cure-design-2026-08-08 D-2b): ABSENT (200 found=false) and
    UNAVAILABLE (503) stay distinct. An index that could not be consulted is
    never rendered as ``found=false``.

    Request Body:
        BusinessByEmailResolveRequest with email.

    Returns:
        BusinessByEmailResolveResponse with found + office_phone + reason.
        Never returns 404 for not-found (ADR-INT-001).

    Error Responses:
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 422 VALIDATION_ERROR: Invalid request body
        - 503 INDEX_NOT_READY: contact index could not be consulted
        - 503 ASANA_UNAVAILABLE: Asana call failed
    """
    start_time = time.monotonic()

    # PII fence: the raw email never reaches a log line (redact_email keeps the
    # domain, masks the local part) -- mirroring the phone redaction above.
    redacted = redact_email(body.email)

    logger.info(
        "intake_resolve_business_by_email_request",
        extra={
            "request_id": request_id,
            "email": redacted,
            "caller_service": claims.service_name,
        },
    )

    try:
        async with AsanaClient(token=auth.asana_pat) as client:
            result = await resolve_business_by_email(email=body.email, client=client)
    except ContactIndexUnavailableError as exc:
        # UNAVAILABLE, never found=false. A downgrade here would tell the
        # caller "this email belongs to no business" on the strength of an
        # index we could not read -- which sends the calendly pipeline to
        # CREATE and mints a duplicate.
        logger.error(
            "intake_resolve_business_by_email_unavailable",
            extra={
                "request_id": request_id,
                "email": redacted,
                "reason": exc.reason,
            },
        )
        raise_api_error(
            request_id,
            503,
            "INDEX_NOT_READY",
            "The contact index could not be consulted for this request. "
            "This is a transient service condition -- retry shortly.",
        )
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "intake_resolve_business_by_email_error",
            extra={
                "request_id": request_id,
                "email": redacted,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            "Failed to resolve business by email. Asana service unavailable.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "intake_resolve_business_by_email_complete",
        extra={
            "request_id": request_id,
            "email": redacted,
            "found": result.found,
            "reason": result.reason,
            "match_count": result.match_count,
            "distinct_business_count": result.distinct_business_count,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return build_success_response(data=result, request_id=request_id)
