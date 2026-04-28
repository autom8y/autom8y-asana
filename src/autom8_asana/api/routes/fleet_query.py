"""Fleet-canonical query routes (S3 D4).

Exposes the fleet-canonical FleetQuery DSL as a POST endpoint at
``/v1/query/entities`` AND ``/api/v1/query/entities`` (dual-namespace
mount per S3 TDD section 7.4.3). Both routes share the same handler;
the dual-mount satisfies the sovereignty criterion that the FleetQuery
surface is reachable from both the legacy ``/v1`` namespace and the
fleet-standard ``/api/v1`` namespace.

Design notes:
- Adapter only — does NOT redesign the asana query engine. The
  fleet_query_adapter module translates FleetQuery into the kwargs
  accepted by EntityQueryService.query, which is the same surface
  consumed by the legacy POST /v1/query/{entity_type} handler.
- Backward compatibility: legacy routes (POST /v1/query/{entity_type},
  POST /v1/query/{entity_type}/rows, POST /v1/query/{entity_type}/aggregate)
  remain mounted alongside this fleet route. Existing callers are
  untouched.
- The fleet route requires an authenticated S2S JWT (same auth as the
  legacy /v1 query routes — applied via SecureRouter+s2s_router).
- Pagination round-trip: FleetQuery.limit/offset round-trip into the
  response envelope's PaginationMeta — verified by integration test.

Routes:
- POST /v1/query/entities      - fleet-canonical query (legacy namespace)
- POST /api/v1/query/entities  - fleet-canonical query (fleet namespace)
"""

from __future__ import annotations

from typing import Annotated

from autom8y_api_schemas import (
    FleetQuery,
    ResponseMeta,
    SuccessResponse,
)
from autom8y_log import get_logger
from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves at runtime
    AuthContextDep,
    EntityServiceDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.api.fleet_query_adapter import (
    AdapterValidationError,
    build_pagination_meta,
    fleet_query_to_dispatch_kwargs,
)
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.client import AsanaClient
from autom8_asana.services.errors import ServiceError
from autom8_asana.services.errors import CacheNotWarmError
from autom8_asana.services.query_service import EntityQueryService

__all__ = [
    "FleetQueryEnvelope",
    "fleet_query_router_v1",
    "fleet_query_router_api_v1",
    "handle_fleet_query",
]

logger = get_logger(__name__)


# Two routers, same handler. Mounting at different prefixes lets the
# fleet query surface appear at both /v1/query/entities and
# /api/v1/query/entities — the dual-namespace requirement from S3 TDD
# section 7.4.3.
fleet_query_router_v1 = s2s_router(
    prefix="/v1/query",
    tags=["query"],
    include_in_schema=False,
)
fleet_query_router_api_v1 = s2s_router(
    prefix="/api/v1/query",
    tags=["query"],
    include_in_schema=False,
)


# ---------------------------------------------------------------------------
# Response envelope (fleet SuccessResponse + FleetQuery-shaped payload)
# ---------------------------------------------------------------------------


class FleetQueryEnvelope(BaseModel):
    """Response payload for a FleetQuery dispatch.

    Wrapped in the canonical fleet ``SuccessResponse[T]`` envelope so the
    response shape mirrors the rest of the asana API surface.
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(description="Entity type queried")
    project_gid: str = Field(description="Asana project GID backing the entity type")
    rows: list[dict] = Field(description="Result rows in select-projection order")  # type: ignore[type-arg]


# ---------------------------------------------------------------------------
# Shared handler
# ---------------------------------------------------------------------------


async def handle_fleet_query(
    *,
    request_body: FleetQuery,
    request_id: str,
    auth: object,  # AuthContextDep — opaque here, validated by FastAPI
    claims: ServiceClaims,
    entity_service: object,  # EntityServiceDep — same opacity
) -> SuccessResponse[FleetQueryEnvelope]:
    """Dispatch a FleetQuery to the asana EntityQueryService.

    Pipeline:
    1. Translate FleetQuery -> EntityQueryService kwargs via the adapter.
    2. Validate the entity_type via EntityServiceDep.
    3. Execute via EntityQueryService.query().
    4. Build the response envelope with SuccessResponse + PaginationMeta
       round-trip — satisfying the section 7.3 invariant.

    Args:
        request_body: The fleet-canonical FleetQuery payload.
        request_id: Request correlation ID injected by RequestId dep.
        auth: AuthContext (opaque to type-checker; resolved at runtime).
        claims: Service claims for caller observability.
        entity_service: EntityService dep (opaque to type-checker).

    Returns:
        SuccessResponse[FleetQueryEnvelope] with PaginationMeta on
        ResponseMeta.

    Raises:
        HTTPException: Translated from AdapterValidationError,
            ServiceError, or CacheNotWarmError per the canonical
            asana error mapping.
    """
    # 1. Translate
    try:
        dispatch = fleet_query_to_dispatch_kwargs(request_body)
    except AdapterValidationError as e:
        raise_api_error(
            request_id,
            400,
            "FLEET_QUERY_VALIDATION",
            str(e),
        )

    # 2. Entity validation (same path the legacy POST endpoint uses)
    try:
        ctx = entity_service.validate_entity_type(dispatch.entity_type)  # type: ignore[attr-defined]
    except ServiceError as e:
        raise_service_error(request_id, e)

    # 3. Execute via EntityQueryService — identical surface to the
    # legacy POST /v1/query/{entity_type} handler so the engine sees
    # the same call shape it always has.
    query_service = EntityQueryService()
    try:
        async with AsanaClient(token=ctx.bot_pat) as client:
            result = await query_service.query(
                entity_type=dispatch.entity_type,
                project_gid=ctx.project_gid,
                client=client,
                where=dispatch.where,
                select=dispatch.select,
                limit=dispatch.limit,
                offset=dispatch.offset,
            )
    except CacheNotWarmError as e:
        raise_api_error(
            request_id,
            503,
            "CACHE_NOT_WARMED",
            str(e),
            details={
                "entity_type": dispatch.entity_type,
                "retry_after_seconds": 30,
            },
        )

    # 4. Build response with PaginationMeta round-trip
    pagination = build_pagination_meta(request_body, total_count=result.total_count)
    payload = FleetQueryEnvelope(
        entity_type=dispatch.entity_type,
        project_gid=result.project_gid,
        rows=result.data,
    )

    logger.info(
        "fleet_query_dispatch_complete",
        extra={
            "request_id": request_id,
            "entity_type": dispatch.entity_type,
            "result_count": len(result.data),
            "total_count": result.total_count,
            "limit": request_body.limit,
            "offset": request_body.offset,
            "caller_service": claims.service_name,
        },
    )

    return SuccessResponse[FleetQueryEnvelope](
        data=payload,
        meta=ResponseMeta(
            request_id=request_id,
            pagination=pagination,
        ),
    )


# ---------------------------------------------------------------------------
# Route registrations (dual-namespace)
# ---------------------------------------------------------------------------


@fleet_query_router_v1.post(
    "/entities",
    response_model=SuccessResponse[FleetQueryEnvelope],
    summary="Dispatch a FleetQuery (legacy /v1 namespace)",
    description=(
        "Accepts a fleet-canonical FleetQuery body and dispatches to the "
        "asana entity query service. PaginationMeta in the response "
        "envelope round-trips the request limit/offset."
    ),
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
async def fleet_query_v1(
    request_body: FleetQuery,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
) -> SuccessResponse[FleetQueryEnvelope]:
    """POST /v1/query/entities — fleet-canonical query in the legacy namespace."""
    return await handle_fleet_query(
        request_body=request_body,
        request_id=request_id,
        auth=auth,
        claims=claims,
        entity_service=entity_service,
    )


@fleet_query_router_api_v1.post(
    "/entities",
    response_model=SuccessResponse[FleetQueryEnvelope],
    summary="Dispatch a FleetQuery (fleet /api/v1 namespace)",
    description=(
        "Identical handler to /v1/query/entities mounted at the fleet "
        "/api/v1 namespace per S3 TDD section 7.4.3 dual-namespace "
        "requirement."
    ),
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
async def fleet_query_api_v1(
    request_body: FleetQuery,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
) -> SuccessResponse[FleetQueryEnvelope]:
    """POST /api/v1/query/entities — fleet-canonical query in the fleet namespace."""
    return await handle_fleet_query(
        request_body=request_body,
        request_id=request_id,
        auth=auth,
        claims=claims,
        entity_service=entity_service,
    )
