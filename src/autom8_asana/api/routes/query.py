"""Entity Query routes for list/filter operations on DataFrame cache.

Routes:
- GET  /v1/query/entities - List queryable entity types (introspection)
- GET  /v1/query/{entity_type}/fields - List entity fields (introspection)
- GET  /v1/query/{entity_type}/relations - List joinable entities (introspection)
- POST /v1/query/{entity_type} - Legacy query with flat equality filtering (deprecated, sunset 2026-06-01)
- POST /v1/query/{entity_type}/rows - Filtered row retrieval with composable predicates
- POST /v1/query/{entity_type}/aggregate - Aggregate entity data with grouping

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported
- GET introspection endpoints require service token
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Never

from autom8y_log import get_logger
from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    DataServiceClientDep,
    EntityServiceDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.client import AsanaClient
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
from autom8_asana.services.errors import InvalidFieldError, ServiceError
from autom8_asana.services.query_service import (
    CacheNotWarmError,
    EntityQueryService,
    resolve_section_index,
    validate_fields,
)

__all__ = [
    "router",
    "query_introspection_router",
    # Legacy models (backward compatibility for imports)
    "QueryRequest",
    "QueryMeta",
    "QueryResponse",
]

logger = get_logger(__name__)

# Two routers share the same prefix. The introspection router is visible in the
# OpenAPI spec (include_in_schema=True) while the query execution router stays
# hidden (include_in_schema=False) to avoid exposing POST endpoints.
query_introspection_router = s2s_router(
    prefix="/v1/query", tags=["query"], include_in_schema=True
)
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
# Legacy models (for deprecated POST /{entity_type} endpoint)
# ---------------------------------------------------------------------------

DEFAULT_SELECT_FIELDS = ["gid", "name", "section"]


class QueryRequest(BaseModel):
    """Legacy query request with flat equality filtering (AND semantics)."""

    model_config = ConfigDict(extra="forbid")

    where: dict[str, Any] = Field(
        default_factory=dict,
        description="Flat equality predicates with AND semantics. Keys are column names, values are match targets.",
        examples=[{"vertical": "chiro", "status": "active"}],
    )
    select: list[str] | None = Field(
        default=None,
        description="Column names to include in results. Null returns default fields (gid, name, section).",
        examples=[["gid", "name", "office_phone"]],
    )
    limit: int = Field(
        default=100,
        description="Maximum number of rows to return. Values above 1000 are silently clamped.",
        examples=[100],
    )
    offset: int = Field(
        default=0,
        description="Number of rows to skip for pagination.",
        examples=[0],
    )

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1:
            raise ValueError("limit must be >= 1")
        return min(v, 1000)

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 0:
            raise ValueError("offset must be >= 0")
        return v


class QueryMeta(BaseModel):
    """Response metadata for pagination and context."""

    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(
        description="Total number of matching rows before pagination.",
    )
    limit: int = Field(
        description="Maximum rows per page as applied.",
    )
    offset: int = Field(
        description="Number of rows skipped.",
    )
    entity_type: str = Field(
        description="Entity type that was queried (e.g., 'unit', 'offer').",
    )
    project_gid: str = Field(
        description="Asana project GID backing this entity type.",
    )


class QueryResponse(BaseModel):
    """Response body for entity query."""

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]] = Field(
        description="Query result rows. Each dict contains the requested select fields.",
    )
    meta: QueryMeta = Field(
        description="Pagination metadata and query context.",
    )


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
)
async def list_query_entities(
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
)
async def list_data_sources(
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
)
async def list_data_source_fields(
    factory: str,
    request_id: RequestId,
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
)
async def list_query_fields(
    entity_type: str,
    request_id: RequestId,
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
)
async def list_query_relations(
    entity_type: str,
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
)
async def list_query_sections(
    entity_type: str,
    request_id: RequestId,
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


@router.post("/{entity_type}/rows", response_model=RowsResponse)
async def query_rows(
    entity_type: str,
    request_body: RowsRequest,
    request_id: RequestId,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
    data_service_client: DataServiceClientDep = None,
) -> RowsResponse:
    """Query entity rows with composable predicate filtering.

    See PRD-dynamic-query-service FR-004.
    """
    # 1. Entity validation via EntityServiceDep
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except ServiceError as e:
        raise_service_error(request_id, e)

    # 2. Build section index (manifest-first, enum fallback)
    section_index = await resolve_section_index(
        request_body.section, entity_type, ctx.project_gid
    )

    # 3. Execute query
    query_service = EntityQueryService()
    engine = QueryEngine(provider=query_service, data_client=data_service_client)
    try:
        async with AsanaClient(token=ctx.bot_pat) as client:
            result = await engine.execute_rows(
                entity_type=entity_type,
                project_gid=ctx.project_gid,
                client=client,
                request=request_body,
                section_index=section_index,
                entity_project_registry=entity_service.project_registry,
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
        "query_rows_complete",
        extra={
            "entity_type": entity_type,
            "total_count": result.meta.total_count,
            "returned_count": result.meta.returned_count,
            "query_ms": result.meta.query_ms,
            "caller_service": claims.service_name,
            "predicate_depth": (
                predicate_depth(request_body.where) if request_body.where else 0
            ),
            "section": request_body.section,
            "classification": request_body.classification,
        },
    )

    return result


@router.post("/{entity_type}/aggregate", response_model=AggregateResponse)
async def query_aggregate(
    entity_type: str,
    request_body: AggregateRequest,
    request_id: RequestId,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
    data_service_client: DataServiceClientDep = None,
) -> AggregateResponse:
    """Aggregate entity data with grouping and optional HAVING filter.

    See PRD-dynamic-query-service FR-005.
    """
    # 1. Entity validation via EntityServiceDep
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except ServiceError as e:
        raise_service_error(request_id, e)

    # 2. Build section index
    section_index = await resolve_section_index(
        request_body.section, entity_type, ctx.project_gid
    )

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
            "predicate_depth": (
                predicate_depth(request_body.where) if request_body.where else 0
            ),
            "having_depth": (
                predicate_depth(request_body.having) if request_body.having else 0
            ),
            "section": request_body.section,
        },
    )

    return result


# ---------------------------------------------------------------------------
# Deprecated endpoint (sunset 2026-06-01)
# ---------------------------------------------------------------------------


@router.post("/{entity_type}", response_model=QueryResponse)
async def query_entities(
    entity_type: str,
    request_body: QueryRequest,
    request_id: RequestId,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
) -> JSONResponse:
    """Query entities from DataFrame cache (deprecated -- use /rows)."""
    start_time = time.monotonic()

    logger.info(
        "entity_query_request",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "where_fields": list(request_body.where.keys()),
            "select_fields": request_body.select,
            "limit": request_body.limit,
            "offset": request_body.offset,
            "caller_service": claims.service_name,
        },
    )

    # 1. Entity validation
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except ServiceError as e:
        raise_service_error(request_id, e)

    # 2. Field validation via QueryService
    if request_body.where:
        try:
            validate_fields(list(request_body.where.keys()), entity_type, "where")
        except InvalidFieldError as e:
            raise_service_error(request_id, e)

    select_fields = request_body.select or DEFAULT_SELECT_FIELDS

    try:
        validate_fields(select_fields, entity_type, "select")
    except InvalidFieldError as e:
        raise_service_error(request_id, e)

    # 3. Execute query via EntityQueryService
    query_service = EntityQueryService()

    try:
        async with AsanaClient(token=ctx.bot_pat) as client:
            result = await query_service.query(
                entity_type=entity_type,
                project_gid=ctx.project_gid,
                client=client,
                where=request_body.where,
                select=select_fields,
                limit=request_body.limit,
                offset=request_body.offset,
            )
    except CacheNotWarmError as e:
        logger.warning(
            "cache_not_warm",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "project_gid": ctx.project_gid,
                "error": str(e),
            },
        )
        raise_api_error(
            request_id,
            503,
            "CACHE_NOT_WARMED",
            str(e),
            details={
                "entity_type": entity_type,
                "retry_after_seconds": 30,
            },
        )

    # 4. Build response
    response = QueryResponse(
        data=result.data,
        meta=QueryMeta(
            total_count=result.total_count,
            limit=request_body.limit,
            offset=request_body.offset,
            entity_type=entity_type,
            project_gid=result.project_gid,
        ),
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    logger.info(
        "entity_query_complete",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "result_count": len(result.data),
            "total_count": result.total_count,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
            "project_gid": result.project_gid,
            "cache_status": "hit_or_refreshed",
        },
    )

    # Add deprecation headers (per TDD Section 8.2)
    response_obj = JSONResponse(content=response.model_dump())
    response_obj.headers["Deprecation"] = "true"
    response_obj.headers["Sunset"] = "2026-06-01"
    response_obj.headers["Link"] = (
        f'</v1/query/{entity_type}/rows>; rel="successor-version"'
    )

    logger.info(
        "deprecated_query_endpoint_used",
        extra={
            "caller_service": claims.service_name,
            "entity_type": entity_type,
        },
    )

    return response_obj
