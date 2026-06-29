"""Entity Query routes for list/filter operations on DataFrame cache.

Routes:
- GET  /v1/query/entities - List queryable entity types (introspection)
- GET  /v1/query/{entity_type}/fields - List entity fields (introspection)
- GET  /v1/query/{entity_type}/relations - List joinable entities (introspection)
- POST /v1/query/{entity_type}/rows - Filtered row retrieval with composable predicates
- POST /v1/query/{entity_type}/aggregate - Aggregate entity data with grouping

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported
- GET introspection endpoints require service token
"""

from __future__ import annotations

from typing import Annotated, Any, Never

from autom8y_log import get_logger
from fastapi import Depends, Request

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    AuthContextDep,
    DataServiceClientDep,
    EntityServiceDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.api.exception_types import ApiDataFrameBuildError
from autom8_asana.api.metrics import (
    S7_CAUSE_CADENCE_503,
    S7_CAUSE_CAPACITY_502,
    S7_CAUSE_HONEST_REFUSAL,
    S7_OUTCOME_DATA_2XX,
    s7_cause_for_build_code,
)
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.rate_limit import (
    SA_NAMESPACE_LIMIT,
    _get_rate_limit_key,
    limiter,
)
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.client import AsanaClient
from autom8_asana.core.types import EntityType
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
    ClassificationError,
    JoinError,
    QueryEngineError,
    QueryTooComplexError,
)
from autom8_asana.query.guards import predicate_depth
from autom8_asana.query.models import (
    AggregateRequest,
    AggregateResponse,
    RowsRequest,
    RowsResponse,
)
from autom8_asana.services.errors import (
    CacheNotWarmError,
    InvalidParameterError,
    ServiceError,
)
from autom8_asana.services.query_service import (
    EntityQueryService,
    resolve_section_index,
)

__all__ = [
    "router",
    "query_introspection_router",
]

logger = get_logger(__name__)

# Two routers share the same prefix. The introspection router is visible in the
# OpenAPI spec (include_in_schema=True) while the query execution router stays
# hidden (include_in_schema=False) to avoid exposing POST endpoints.
query_introspection_router = s2s_router(prefix="/v1/query", tags=["query"], include_in_schema=True)
router = s2s_router(prefix="/v1/query", tags=["query"], include_in_schema=False)


# ---------------------------------------------------------------------------
# Error-to-status mapping (canonical pattern per D-004)
# ---------------------------------------------------------------------------

_ERROR_STATUS: dict[type[QueryEngineError], int] = {
    QueryTooComplexError: 400,
    AggregateGroupLimitError: 400,
    ClassificationError: 400,
    JoinError: 422,
}
_DEFAULT_ERROR_STATUS = 422


def _raise_query_error(request_id: str, error: QueryEngineError) -> Never:
    """Map QueryEngineError to HTTPException with request_id.

    Per ADR-I6-001: Preserves existing status mapping while adding
    request_id to every error response.
    """
    status = _ERROR_STATUS.get(type(error), _DEFAULT_ERROR_STATUS)
    d = error.to_dict()
    raise_api_error(request_id, status, d["error"], d["message"])


# ---------------------------------------------------------------------------
# Introspection endpoints (GET, no body)
# ---------------------------------------------------------------------------
# IMPORTANT: These static GET routes are defined BEFORE the /{entity_type}
# routes so FastAPI matches them before the path parameter catches "entities".


@query_introspection_router.get(
    "/entities",
    summary="List queryable entity types",
    description=(
        "Returns all registered entity types that can be queried through the "
        "composable query engine. Each entry includes the entity type name, "
        "display name, project GID, and category. Use this to discover which "
        "entity types are available before calling /fields, /relations, or "
        "/sections for a specific type."
    ),
    openapi_extra={"x-fleet-envelope-exempt": True},
)
async def list_query_entities(
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> dict[str, Any]:
    """List all queryable entity types.

    Returns entity metadata including type name, display name, project GID,
    and category. Shares logic with CLI 'entities' subcommand via
    introspection module.
    """
    from autom8_asana.query.introspection import list_entities

    return {"data": list_entities()}


@query_introspection_router.get(
    "/data-sources",
    summary="List data-service factories",
    description=(
        "Returns metadata for each registered data-service factory available "
        "for cross-service joins. Each entry includes the factory name, frame "
        "type, description, columns, and default period. Data-service "
        "factories provide virtual entities sourced from autom8y-data that "
        "can be joined with Asana-sourced entities in the query engine."
    ),
    openapi_extra={"x-fleet-envelope-exempt": True},
)
async def list_data_sources(
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> dict[str, Any]:
    """List available data-service factories for cross-service joins.

    Returns metadata for each registered data-service entity including
    factory name, frame type, description, columns, and default period.
    """
    from autom8_asana.query.data_service_entities import list_data_service_entities

    return {"data": list_data_service_entities()}


@query_introspection_router.get(
    "/data-sources/{factory}/fields",
    summary="List fields for a data-service factory",
    description=(
        "Returns column names from the virtual entity registry for a specific "
        "data-service factory. These columns are available for use in query "
        "predicates and select clauses when joining with this factory. Note "
        "that actual columns returned by autom8y-data may differ — this is an "
        "advisory list based on common factory configurations."
    ),
    openapi_extra={"x-fleet-envelope-exempt": True},
)
async def list_data_source_fields(
    factory: str,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> dict[str, Any]:
    """List known columns for a data-service factory.

    Returns column names from the virtual entity registry. Note that
    actual columns returned by autom8y-data may differ — this is an
    advisory list based on common factory configurations.
    """
    from autom8_asana.query.data_service_entities import get_data_service_entity

    info = get_data_service_entity(factory)
    if info is None:
        raise_api_error(
            request_id,
            404,
            "UNKNOWN_DATA_SOURCE",
            f"Unknown data-service factory: '{factory}'. "
            "Use GET /v1/query/data-sources to list available factories.",
        )
    return {
        "data": [{"name": col} for col in info.columns],
        "factory": factory,
        "description": info.description,
        "default_period": info.default_period,
        "join_key": info.join_key,
    }


@query_introspection_router.get(
    "/{entity_type}/fields",
    summary="List fields for an entity type",
    description=(
        "Returns column metadata for all fields available on the given entity "
        "type, including name, dtype, nullable flag, and description. Use this "
        "to discover which fields can be used in query predicates (where "
        "clauses) and select clauses when querying this entity type."
    ),
    openapi_extra={"x-fleet-envelope-exempt": True},
)
async def list_query_fields(
    entity_type: str,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> dict[str, Any]:
    """List available fields for an entity type.

    Returns column metadata including name, dtype, nullable, and description.
    Shares logic with CLI 'fields' subcommand via introspection module.
    """
    from autom8_asana.query.introspection import list_fields

    try:
        data = list_fields(entity_type)
    except ValueError as e:
        raise_api_error(request_id, 404, "UNKNOWN_ENTITY", str(e))
    return {"data": data}


@query_introspection_router.get(
    "/{entity_type}/relations",
    summary="List relations for an entity type",
    description=(
        "Returns relationship metadata for all joinable entity types from the "
        "given entity type. Each relation includes target entity, direction, "
        "default join key, cardinality, and description. Use this to discover "
        "how entity types can be joined in cross-entity queries."
    ),
    openapi_extra={"x-fleet-envelope-exempt": True},
)
async def list_query_relations(
    entity_type: str,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> dict[str, Any]:
    """List joinable entity types and their join keys.

    Returns relationship metadata including target entity, direction,
    default join key, cardinality, and description.
    Shares logic with CLI 'relations' subcommand via introspection module.
    """
    from autom8_asana.query.introspection import list_relations

    return {"data": list_relations(entity_type)}


@query_introspection_router.get(
    "/{entity_type}/sections",
    summary="List sections for an entity type",
    description=(
        "Returns section metadata for the given entity type, including section "
        "name and classification (active, activating, inactive, ignored). Only "
        "entity types with a registered SectionClassifier are supported. Use "
        "this to discover valid section values for filtering queries by "
        "section or classification."
    ),
    openapi_extra={"x-fleet-envelope-exempt": True},
)
async def list_query_sections(
    entity_type: str,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> dict[str, Any]:
    """List section names and classifications for an entity type.

    Returns section metadata including section_name and classification
    (active, activating, inactive, ignored). Only entity types with a
    registered SectionClassifier are supported.

    Shares logic with CLI 'sections' subcommand via introspection module.
    """
    from autom8_asana.query.introspection import list_sections

    try:
        data = list_sections(entity_type)
    except ValueError as e:
        raise_api_error(request_id, 404, "NO_SECTION_CLASSIFIER", str(e))
    return {"data": data, "entity_type": entity_type}


# NOTE (C-3/AC-9.2): A dedicated /schema endpoint is not needed.
# The existing /fields endpoint returns column definitions (name, dtype,
# nullable, description) which constitutes the entity schema.  Callers
# needing a full schema view can combine /fields + /relations + /sections
# from the introspection surface.  This avoids a redundant endpoint that
# would just wrap those three calls.


# ---------------------------------------------------------------------------
# Active endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{entity_type}/rows",
    response_model=SuccessResponse[RowsResponse],
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
@limiter.limit(
    SA_NAMESPACE_LIMIT,
    key_func=_get_rate_limit_key,
    override_defaults=True,
)
async def query_rows(
    request: Request,
    entity_type: str,
    request_body: RowsRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
    data_service_client: DataServiceClientDep = None,
) -> SuccessResponse[RowsResponse]:
    """Query entity rows with composable predicate filtering.

    See PRD-dynamic-query-service FR-004.

    Body-precedence rule (Sprint 2 receiver-surface — A1):
    When ``request_body.project_gid`` is present, it overrides the
    registry-derived ``project_gid``. Entity schema/descriptor validation
    still runs via ``validate_entity_type`` to confirm the entity is registered;
    only the GID lookup is overridden.  This enables arbitrary Asana fleet GIDs
    without static EntityProjectRegistry pre-registration.

    Rate-limit isolation (receiver-bulk-fanout-reliability Stage-1, qa-adversary
    FG-2 fix 2026-05-31 + FG-7 disclosure correction 2026-05-31):
    The ``@limiter.limit(SA_NAMESPACE_LIMIT, ...)`` decoration with
    ``override_defaults=True`` raises the ceiling to 600/min FOR THIS ROUTE
    ONLY (Phase-3 Knob 5: SA bulk-pass peak = 100 rpm baseline x 3 headroom
    x 2 burst). The ``request: Request`` parameter is REQUIRED by SlowAPI's
    ``_dynamic_route_limits`` path (slowapi/extension.py L586-L595 invokes
    ``with_request(request)`` to materialize per-key limits).

    POSTURE DISCLOSURE (FG-7): per SlowAPI ``__check_request_limit``
    (slowapi/extension.py L617-628), ``override_defaults=True`` EXCLUDES the
    global 100/min default from this route's limits chain entirely — so ALL
    callers (sa:/pat:/ip:) on ``query_rows`` get a 600/min PER-KEY bucket via
    their respective namespace key from ``_get_rate_limit_key``. Non-SA
    callers (PAT/IP) on this route are NO LONGER subject to the 100/min
    global default; they get 600/min per-key on this route only. The global
    100/min remains active on all other routes. Mitigation context: this is
    an s2s_router route (require_service_claims rejects unauthenticated
    callers, making the IP fallback effectively dead); the per-key bucket
    bounds the 6x ceiling raise. Per-namespace differentiation (sa:=600,
    pat:/ip:=100 on this route) is deferred to Sprint-2 if posture review
    deems it required.
    """
    # 1. Entity validation via EntityServiceDep
    # validate_entity_type checks schema registration + descriptor existence;
    # it does NOT inspect the request body — precedence altitude is here.
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except ServiceError as e:
        raise_service_error(request_id, e)

    # Sprint 2 A1 — body-precedence branch.
    # Body GID wins over registry-routed GID when present.
    resolved_project_gid: str | None
    if request_body.project_gid is not None:
        resolved_project_gid = request_body.project_gid
        logger.info(
            "query_rows_body_gid_precedence",
            extra={
                "entity_type": entity_type,
                "body_project_gid": request_body.project_gid,
                "registry_project_gid": ctx.project_gid,
            },
        )
    else:
        # Legacy path: registry-routed GID (Sprint 1 semantics preserved).
        resolved_project_gid = ctx.project_gid

    # risk-1 fail-fast guard: body-parameterized entities (project, section)
    # carry ctx.project_gid=None. If the body omitted project_gid, the resolved
    # GID is None — fail-fast with a clear 400 rather than passing None into the
    # query engine (which would 500 or silently misbehave). Locked by T5.
    if resolved_project_gid is None:
        raise_service_error(
            request_id,
            InvalidParameterError(
                f"project_gid is required in the request body for body-parameterized "
                f"entity type: {entity_type}"
            ),
        )

    # PQ-5 fail-closed guard: a section-entity request that omits its required
    # section selector must be REJECTED, not silently degenerated.
    #
    # The live section selector consumed by the engine is `request.section`
    # (the section NAME). `_resolve_section` (engine.py) returns None when
    # `request.section is None`, and the engine applies the section predicate
    # ONLY `if section_name_filter is not None` (engine.py "7.5 Apply section
    # filter"). So a section-entity request carrying project_gid but no
    # `section` selector skips section narrowing entirely and returns an
    # UNFILTERED project-wide frame as a 200 — a liveness-masquerade: the
    # response is "alive" but scopes the wrong rows (the S7-GATE-FIDELITY
    # false-negative class). `request.section_gid` is INERT on this path
    # (declared on RowsRequest but never read by the engine / resolve_section_index
    # post the S3-MAP fix), so supplying only section_gid does NOT scope either.
    # Fail-closed: require the live `section` selector for the section entity.
    if entity_type == EntityType.SECTION.value and request_body.section is None:
        raise_service_error(
            request_id,
            InvalidParameterError(
                "section is required in the request body for a section-entity query: "
                "a section query without a section selector would silently return the "
                "unfiltered project-wide frame. Supply the 'section' name selector "
                "(note: 'section_gid' is not consumed on this path). "
                "[MISSING_SECTION_SELECTOR]"
            ),
        )

    # 2. Build section index (manifest-first, enum fallback)
    section_index = await resolve_section_index(
        request_body.section, entity_type, resolved_project_gid
    )

    # 3. Execute query
    #
    # receiver-bulk-fanout-reliability Stage-1 Surface 5: instrument the
    # receiver-side mirror SLI per arm. Body-parameterized entities
    # (project, section) are the bulk-fan-out hot path; the mirror SLI
    # is success_count / (success_count + 5xx_count), tracked per arm.
    # 4xx are NOT counted (client error, not receiver health).
    #
    # Records ``success_for_metric`` based on the outcome of execute_rows:
    # success on 2xx return, server_error on 5xx-class raise (503 build errors,
    # cache-not-warm 503, generic exceptions). The receiver_query_success_rate
    # gauge derived from these counters drives Alert A8 (MIRROR-SLI-DEGRADATION)
    # and the deploy gate (>=99% sustained 10min on both arms).
    # S7-GATE-FIDELITY: alongside the binary success/server_error SLI, classify
    # this request into ONE of the three S7 causes the consumer GetDfFallback
    # collapses (cadence_503 / capacity_502 / honest_refusal) plus data_2xx for a
    # real-data serve. ``fallback_cause`` is set in each branch and emitted in the
    # finally so the S7 verdict reads CAUSE, not a collapsed total.
    success_for_metric = True
    fallback_cause: str | None = None
    query_service = EntityQueryService()
    engine = QueryEngine(provider=query_service, data_client=data_service_client)
    try:
        async with AsanaClient(token=ctx.bot_pat) as client:
            result = await engine.execute_rows(
                entity_type=entity_type,
                project_gid=resolved_project_gid,
                client=client,
                request=request_body,
                section_index=section_index,
                entity_project_registry=entity_service.project_registry,
            )
    except QueryEngineError as e:
        success_for_metric = False
        # A query-engine 5xx is a server-side serve failure, not a build-in-progress
        # warmth gap — classify it on the capacity side so it cannot mask as cadence.
        fallback_cause = S7_CAUSE_CAPACITY_502
        _raise_query_error(request_id, e)
    except ApiDataFrameBuildError as e:
        # ADR-G2RECV-002: request-time build-on-miss for body-parameterized entities
        # raises a typed 503 (DATAFRAME_BUILD_FAILED / _ERROR / _TIMEOUT, or
        # CACHE_BUILD_IN_PROGRESS). The error already carries status 503 +
        # retry_after; the registered api_dataframe_build_error_handler renders the
        # canonical envelope. Re-raise so it reaches that handler rather than being
        # swallowed here. NEVER a 500, NEVER a silent empty-200.
        success_for_metric = False
        # S7 split: CACHE_BUILD_IN_PROGRESS is the cadence/warmth gap (cadence_503);
        # every other build-error code is the build-semaphore-starvation path that
        # escalates to an ALB 502 (capacity_502). Derived from the error's .code.
        fallback_cause = s7_cause_for_build_code(e.code)
        raise
    except CacheNotWarmError as e:
        success_for_metric = False
        # Cache-not-warmed is a readiness/warmth gap (the frame is not yet built),
        # not a build-capacity failure — same cause family as CACHE_BUILD_IN_PROGRESS.
        fallback_cause = S7_CAUSE_CADENCE_503
        raise_api_error(
            request_id,
            503,
            "CACHE_NOT_WARMED",
            str(e),
            details={"retry_after_seconds": 30},
        )
    else:
        # 2xx path: distinguish an attested honest-empty serve (honest_refusal) from
        # a real-data serve (data_2xx). This is the liveness-masquerade defeat — an
        # empty 2xx is NOT counted as a healthy real-data serve at the S7 gate.
        fallback_cause = (
            S7_CAUSE_HONEST_REFUSAL
            if getattr(result.meta, "honest_empty", False)
            else S7_OUTCOME_DATA_2XX
        )
    finally:
        # Only emit for body-parameterized arms — the receiver mirror SLI
        # is specifically the bulk-fan-out hot path metric. Offer-domain
        # entities have a separate readiness model and are excluded.
        if ctx.project_gid is None:  # body_parameterized when registry GID is None
            try:
                from autom8_asana.api.metrics import (
                    _serving_stale_total_value,
                    emit_receiver_sli_emf,
                    record_query_fallback_cause,
                    record_receiver_query_outcome,
                )

                record_receiver_query_outcome(entity_type, success=success_for_metric)
                if fallback_cause is not None:
                    record_query_fallback_cause(entity_type, fallback_cause)
                # CR-3 GATE-2 P2-a: additive EMF export of the receiver SLI to a
                # durable backend (ship-dark; co-reads serving_stale_total in the
                # same document so the rate is never exported bare). Fire-and-forget.
                emit_receiver_sli_emf(
                    entity_type,
                    success=success_for_metric,
                    serving_stale_total=_serving_stale_total_value(),
                )
            except Exception:  # noqa: BLE001 -- metrics emission is fire-and-forget
                pass

    # 4. Log query completion
    logger.info(
        "query_rows_complete",
        extra={
            "entity_type": entity_type,
            "total_count": result.meta.total_count,
            "returned_count": result.meta.returned_count,
            "query_ms": result.meta.query_ms,
            "caller_service": claims.service_name,
            "predicate_depth": (predicate_depth(request_body.where) if request_body.where else 0),
            "section": request_body.section,
            "classification": request_body.classification,
        },
    )

    return build_success_response(data=result, request_id=request_id)


@router.post(
    "/{entity_type}/aggregate",
    response_model=SuccessResponse[AggregateResponse],
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
    },
)
async def query_aggregate(
    entity_type: str,
    request_body: AggregateRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
    data_service_client: DataServiceClientDep = None,
) -> SuccessResponse[AggregateResponse]:
    """Aggregate entity data with grouping and optional HAVING filter.

    See PRD-dynamic-query-service FR-005.
    """
    # 1. Entity validation via EntityServiceDep
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except ServiceError as e:
        raise_service_error(request_id, e)

    # risk-1 fail-fast guard: the aggregate endpoint has no body project_gid
    # field, so a body-parameterized entity (ctx.project_gid=None) cannot supply
    # a GID here. Fail-fast with a clear 400 rather than passing None downstream.
    if ctx.project_gid is None:
        raise_service_error(
            request_id,
            InvalidParameterError(
                f"Entity type {entity_type} is body-parameterized and is not "
                f"supported by the aggregate endpoint (no body project_gid field). "
                f"Use POST /v1/query/{entity_type}/rows with a body project_gid."
            ),
        )

    # 2. Build section index
    section_index = await resolve_section_index(request_body.section, entity_type, ctx.project_gid)

    # 3. Execute aggregate query
    query_service = EntityQueryService()
    engine = QueryEngine(provider=query_service, data_client=data_service_client)
    try:
        async with AsanaClient(token=ctx.bot_pat) as client:
            result = await engine.execute_aggregate(
                entity_type=entity_type,
                project_gid=ctx.project_gid,
                client=client,
                request=request_body,
                section_index=section_index,
            )
    except QueryEngineError as e:
        _raise_query_error(request_id, e)
    except CacheNotWarmError as e:
        raise_api_error(
            request_id,
            503,
            "CACHE_NOT_WARMED",
            str(e),
            details={"retry_after_seconds": 30},
        )

    # 4. Log query completion
    logger.info(
        "query_aggregate_complete",
        extra={
            "entity_type": entity_type,
            "group_count": result.meta.group_count,
            "aggregation_count": result.meta.aggregation_count,
            "group_by": result.meta.group_by,
            "query_ms": result.meta.query_ms,
            "caller_service": claims.service_name,
            "predicate_depth": (predicate_depth(request_body.where) if request_body.where else 0),
            "having_depth": (predicate_depth(request_body.having) if request_body.having else 0),
            "section": request_body.section,
        },
    )

    return build_success_response(data=result, request_id=request_id)
