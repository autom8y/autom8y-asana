"""Entity Query routes for list/filter operations on DataFrame cache.

Routes:
- POST /v1/query/{entity_type} - Legacy query with flat equality filtering (deprecated, sunset 2026-06-01)
- POST /v1/query/{entity_type}/rows - Filtered row retrieval with composable predicates
- POST /v1/query/{entity_type}/aggregate - Aggregate entity data with grouping

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Never

from autom8y_log import get_logger
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from autom8_asana.api.dependencies import EntityServiceDep, RequestId
from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.client import AsanaClient
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
    ClassificationError,
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
    # Legacy models (backward compatibility for imports)
    "QueryRequest",
    "QueryMeta",
    "QueryResponse",
]

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/query", tags=["query"], include_in_schema=False)


# ---------------------------------------------------------------------------
# Error-to-status mapping (canonical pattern per D-004)
# ---------------------------------------------------------------------------

_ERROR_STATUS: dict[type[QueryEngineError], int] = {
    QueryTooComplexError: 400,
    AggregateGroupLimitError: 400,
    ClassificationError: 400,
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

    where: dict[str, Any] = {}
    select: list[str] | None = None
    limit: int = 100
    offset: int = 0

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
    total_count: int
    limit: int
    offset: int
    entity_type: str
    project_gid: str


class QueryResponse(BaseModel):
    """Response body for entity query."""

    model_config = ConfigDict(extra="forbid")
    data: list[dict[str, Any]]
    meta: QueryMeta


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
    engine = QueryEngine()
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
    engine = QueryEngine()
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
