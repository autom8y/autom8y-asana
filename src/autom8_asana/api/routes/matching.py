"""Matching query route.

POST /v1/matching/query -- accepts business identity, returns scored match candidates.

Authentication:
    S2S JWT only (require_service_claims dependency).
    Hidden router: include_in_schema=False (HD-01).

Data source:
    Uses cached Business DataFrame (no direct Asana API calls during matching).
"""

from __future__ import annotations

import time
from typing import Annotated

from autom8y_log import get_logger
from fastapi import Depends

from autom8_asana.api.dependencies import (
    AuthContextDep,  # noqa: TC001 -- FastAPI resolves at runtime
    RequestId,  # noqa: TC001 -- FastAPI resolves at runtime
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.api.routes.matching_models import (
    MatchingQueryRequest,
    MatchingQueryResponse,
)
from autom8_asana.cache.dataframe.factory import get_dataframe_cache_provider
from autom8_asana.services.matching_service import MatchingService
from autom8_asana.services.resolver import EntityProjectRegistry

__all__ = ["router"]

logger = get_logger(__name__)

router = s2s_router(
    prefix="/v1/matching",
    tags=["matching"],
    include_in_schema=False,
)


# ---------------------------------------------------------------------------
# POST /v1/matching/query
# ---------------------------------------------------------------------------


@router.post(
    "/query",
    response_model=SuccessResponse[MatchingQueryResponse],
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
async def matching_query(
    body: MatchingQueryRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[MatchingQueryResponse]:
    """Query for matching business candidates.

    Accepts business identity fields (name, phone, email, domain) and
    returns scored match candidates from the cached Business DataFrame.

    Authentication: S2S JWT only (require_service_claims dependency).

    Request Body:
        MatchingQueryRequest with identity fields, optional limit/threshold.

    Returns:
        MatchingQueryResponse with scored candidates.

    Error Responses:
        - 400 INVALID_QUERY: No identity fields provided
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 503 CACHE_UNAVAILABLE: Business DataFrame not available
    """
    start_time = time.monotonic()

    logger.info(
        "matching_query_request",
        extra={
            "request_id": request_id,
            "has_name": body.name is not None,
            "has_phone": body.phone is not None,
            "has_email": body.email is not None,
            "has_domain": body.domain is not None,
            "limit": body.limit,
            "has_threshold": body.threshold is not None,
            "caller_service": claims.service_name,
        },
    )

    # Validate: at least one identity field must be provided
    if not any([body.name, body.phone, body.email, body.domain]):
        raise_api_error(
            request_id,
            400,
            "INVALID_QUERY",
            "At least one identity field (name, phone, email, domain) must be provided.",
        )

    # Get Business DataFrame from cache
    try:
        cache = get_dataframe_cache_provider()
    except Exception:  # BROAD-CATCH: boundary  # noqa: BLE001
        cache = None

    if cache is None:
        raise_api_error(
            request_id,
            503,
            "CACHE_UNAVAILABLE",
            "Business DataFrame cache is not available. Service may still be warming up.",
        )

    # Resolve the business project GID from the entity project registry
    try:
        registry = EntityProjectRegistry.get_instance()
        project_gid = registry.get_project_gid("business")
    except Exception:  # BROAD-CATCH: boundary  # noqa: BLE001
        project_gid = None

    if project_gid is None:
        raise_api_error(
            request_id,
            503,
            "PROJECT_NOT_CONFIGURED",
            "Business project is not registered. Service initialization may be incomplete.",
        )

    # Fetch the cached DataFrame
    try:
        entry = await cache.get_async(project_gid, "business")
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "matching_cache_fetch_error",
            extra={
                "request_id": request_id,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            503,
            "CACHE_UNAVAILABLE",
            "Failed to fetch Business DataFrame from cache.",
        )

    if entry is None:
        raise_api_error(
            request_id,
            503,
            "CACHE_UNAVAILABLE",
            "Business DataFrame is not cached. Cache may still be warming up.",
        )

    # Execute matching via service layer
    try:
        service = MatchingService()
        response = service.query(
            name=body.name,
            phone=body.phone,
            email=body.email,
            domain=body.domain,
            dataframe=entry.dataframe,
            limit=body.limit,
            threshold=body.threshold,
        )
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "matching_query_error",
            extra={
                "request_id": request_id,
                "error": str(exc),
            },
        )
        raise_api_error(
            request_id,
            500,
            "MATCHING_ERROR",
            "An error occurred during matching. Please try again.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "matching_query_complete",
        extra={
            "request_id": request_id,
            "candidates_returned": len(response.candidates),
            "total_evaluated": response.total_candidates_evaluated,
            "matches_found": sum(1 for c in response.candidates if c.is_match),
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return build_success_response(data=response, request_id=request_id)
