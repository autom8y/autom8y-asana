"""Entity Query routes for list/filter operations on DataFrame cache.

Routes:
- POST /v1/query/{entity_type} - Legacy query with flat equality filtering (deprecated)
- POST /v1/query/{entity_type}/rows - New query with composable predicate trees

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported
"""

from __future__ import annotations

import time
from typing import Annotated, Any

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from autom8_asana.api.dependencies import EntityServiceDep
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.client import AsanaClient
from autom8_asana.query.compiler import strip_section_predicates
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    CoercionError,
    InvalidOperatorError,
    QueryTooComplexError,
    UnknownFieldError,
    UnknownSectionError,
)
from autom8_asana.query.models import RowsRequest, RowsResponse
from autom8_asana.services.errors import (
    InvalidFieldError,
    ServiceError,
    UnknownSectionError as SvcUnknownSectionError,
    get_status_for_error,
)
from autom8_asana.services.query_service import (
    CacheNotWarmError,
    EntityQueryService,
    resolve_section,
    validate_fields,
)

__all__ = [
    "router",
    "QueryRequest",
    "QueryMeta",
    "QueryResponse",
]

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/query", tags=["query"])


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


def _get_query_service() -> EntityQueryService:
    """Get EntityQueryService instance."""
    return EntityQueryService()


def _has_section_pred(node: Any) -> bool:
    """Check if a predicate tree contains any section comparisons."""
    from autom8_asana.query.models import Comparison

    if isinstance(node, Comparison):
        return node.field == "section"
    if hasattr(node, "and_"):
        return any(_has_section_pred(c) for c in node.and_)
    if hasattr(node, "or_"):
        return any(_has_section_pred(c) for c in node.or_)
    if hasattr(node, "not_"):
        return _has_section_pred(node.not_)
    return False


@router.post("/{entity_type}", response_model=QueryResponse)
async def query_entities(
    entity_type: str,
    request_body: QueryRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
) -> JSONResponse:
    """Query entities from DataFrame cache (deprecated -- use /rows)."""
    start_time = time.monotonic()
    request_id = getattr(request.state, "request_id", "unknown")

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

    # 1. Entity validation (replaces inline entity type + project + bot PAT logic)
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except ServiceError as e:
        raise HTTPException(
            status_code=get_status_for_error(e), detail=e.to_dict()
        )

    # 2. Field validation via QueryService
    if request_body.where:
        try:
            validate_fields(
                list(request_body.where.keys()), entity_type, "where"
            )
        except InvalidFieldError as e:
            raise HTTPException(status_code=422, detail=e.to_dict())

    select_fields = request_body.select or DEFAULT_SELECT_FIELDS

    try:
        validate_fields(select_fields, entity_type, "select")
    except InvalidFieldError as e:
        raise HTTPException(status_code=422, detail=e.to_dict())

    # 3. Execute query via EntityQueryService
    query_service = _get_query_service()

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
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CACHE_NOT_WARMED",
                "message": str(e),
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


@router.post("/{entity_type}/rows", response_model=RowsResponse)
async def query_rows(
    entity_type: str,
    request_body: RowsRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
    entity_service: EntityServiceDep,
) -> RowsResponse:
    """Query entity rows with composable predicate trees."""
    start_time = time.monotonic()
    request_id = getattr(request.state, "request_id", "unknown")

    # 1. Log request
    logger.info(
        "query_rows_request",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "caller_service": claims.service_name,
            "section": request_body.section,
            "select_fields": request_body.select,
            "limit": request_body.limit,
            "offset": request_body.offset,
            "has_predicate": request_body.where is not None,
        },
    )

    # 2. Entity validation (replaces inline entity type + project + bot PAT logic)
    try:
        ctx = entity_service.validate_entity_type(entity_type)
    except ServiceError as e:
        raise HTTPException(
            status_code=get_status_for_error(e), detail=e.to_dict()
        )

    # 3. Section resolution (if needed)
    section_index = None
    if request_body.section is not None:
        try:
            await resolve_section(
                request_body.section, entity_type, ctx.project_gid
            )
        except SvcUnknownSectionError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "UNKNOWN_SECTION",
                    "message": f"Unknown section: '{e.section_name}'",
                    "section": e.section_name,
                },
            )
        # Build section index for QueryEngine
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex.from_enum_fallback(entity_type)

    # 4. EC-006: If section param + section in predicate, strip conflicts
    if request_body.section is not None and request_body.where is not None:
        if _has_section_pred(request_body.where):
            logger.warning(
                "section_parameter_conflicts_with_predicate",
                extra={
                    "request_id": request_id,
                    "entity_type": entity_type,
                    "section": request_body.section,
                },
            )
            stripped = strip_section_predicates(request_body.where)
            request_body = request_body.model_copy(update={"where": stripped})

    # 5. Execute via QueryEngine
    engine = QueryEngine()

    try:
        async with AsanaClient(token=ctx.bot_pat) as client:
            response = await engine.execute_rows(
                entity_type=entity_type,
                project_gid=ctx.project_gid,
                client=client,
                request=request_body,
                section_index=section_index,
            )
    except QueryTooComplexError as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except UnknownFieldError as e:
        raise HTTPException(status_code=422, detail=e.to_dict())
    except InvalidOperatorError as e:
        raise HTTPException(status_code=422, detail=e.to_dict())
    except CoercionError as e:
        raise HTTPException(status_code=422, detail=e.to_dict())
    except UnknownSectionError as e:
        raise HTTPException(status_code=422, detail=e.to_dict())
    except CacheNotWarmError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CACHE_NOT_WARMED",
                "message": str(e),
                "entity_type": entity_type,
                "retry_after_seconds": 30,
            },
        )

    # 6. Log completion
    elapsed_ms = (time.monotonic() - start_time) * 1000

    logger.info(
        "query_rows_complete",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "total_count": response.meta.total_count,
            "returned_count": response.meta.returned_count,
            "query_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return response
