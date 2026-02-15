"""Query v2 routes: /rows (Sprint 1), /aggregate (Sprint 2), /metric (Sprint 3).

POST /v1/query/{entity_type}/rows -- Filtered row retrieval with composable predicates.
"""

from __future__ import annotations

from typing import Annotated, Never

from autom8y_log import get_logger
from fastapi import APIRouter, Depends

from autom8_asana.api.dependencies import EntityServiceDep, RequestId
from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.client import AsanaClient
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import (
    AggregateGroupLimitError,
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
from autom8_asana.services.errors import ServiceError
from autom8_asana.services.query_service import CacheNotWarmError, resolve_section_index

__all__ = [
    "router",
]

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/query", tags=["query-v2"], include_in_schema=False)


# Error-to-status mapping
_ERROR_STATUS: dict[type[QueryEngineError], int] = {
    QueryTooComplexError: 400,
    AggregateGroupLimitError: 400,
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
        "query_v2_rows_complete",
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

    # 4. Log query completion (TDD Section 16: Observability)
    logger.info(
        "query_v2_aggregate_complete",
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
