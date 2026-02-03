"""Query v2 routes: /rows (Sprint 1), /aggregate (Sprint 2), /metric (Sprint 3).

POST /v1/query/{entity_type}/rows -- Filtered row retrieval with composable predicates.
"""

from __future__ import annotations

from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request

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
from autom8_asana.services.query_service import CacheNotWarmError
from autom8_asana.services.resolver import (
    EntityProjectRegistry,
    get_resolvable_entities,
)

__all__ = [
    "router",
]

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/query", tags=["query-v2"])


# Error-to-status mapping
_ERROR_STATUS: dict[type[QueryEngineError], int] = {
    QueryTooComplexError: 400,
    AggregateGroupLimitError: 400,
}
_DEFAULT_ERROR_STATUS = 422


def _error_to_response(error: QueryEngineError) -> HTTPException:
    """Map QueryEngineError to HTTPException."""
    status = _ERROR_STATUS.get(type(error), _DEFAULT_ERROR_STATUS)
    return HTTPException(status_code=status, detail=error.to_dict())


@router.post("/{entity_type}/rows", response_model=RowsResponse)
async def query_rows(
    entity_type: str,
    request_body: RowsRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> RowsResponse:
    """Query entity rows with composable predicate filtering.

    See PRD-dynamic-query-service FR-004.
    """
    # Validate entity type
    queryable = get_resolvable_entities()
    if entity_type not in queryable:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UNKNOWN_ENTITY_TYPE",
                "message": f"Unknown entity type: {entity_type}",
                "available_types": sorted(queryable),
            },
        )

    # Get project GID
    registry: EntityProjectRegistry | None = getattr(
        request.app.state,
        "entity_project_registry",
        None,
    )
    if registry is None or not registry.is_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": "Entity project registry not initialized.",
            },
        )

    project_gid = registry.get_project_gid(entity_type)
    if project_gid is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": f"No project configured for entity type: {entity_type}",
            },
        )

    # Get bot PAT for cache operations
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

    try:
        bot_pat = get_bot_pat()
    except BotPATError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "SERVICE_NOT_CONFIGURED",
                "message": "Bot PAT not configured for cache operations.",
            },
        )

    # Build section index (manifest-first, enum fallback)
    section_index = None
    if request_body.section is not None:
        from autom8_asana.dataframes.section_persistence import SectionPersistence
        from autom8_asana.metrics.resolve import SectionIndex

        persistence = SectionPersistence()
        section_index = await SectionIndex.from_manifest_async(persistence, project_gid)
        # Check if manifest had results; if not, fall back to enum
        if section_index.resolve(request_body.section) is None:
            section_index = SectionIndex.from_enum_fallback(entity_type)

    # Execute query
    engine = QueryEngine()
    try:
        async with AsanaClient(token=bot_pat) as client:
            result = await engine.execute_rows(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
                request=request_body,
                section_index=section_index,
                entity_project_registry=registry,
            )
    except QueryEngineError as e:
        raise _error_to_response(e)
    except CacheNotWarmError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CACHE_NOT_WARMED",
                "message": str(e),
                "retry_after_seconds": 30,
            },
        )

    # Log query completion
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
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> AggregateResponse:
    """Aggregate entity data with grouping and optional HAVING filter.

    See PRD-dynamic-query-service FR-005.
    """
    # Validate entity type (same as /rows)
    queryable = get_resolvable_entities()
    if entity_type not in queryable:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UNKNOWN_ENTITY_TYPE",
                "message": f"Unknown entity type: {entity_type}",
                "available_types": sorted(queryable),
            },
        )

    # Get project GID (same pattern as /rows)
    registry: EntityProjectRegistry | None = getattr(
        request.app.state,
        "entity_project_registry",
        None,
    )
    if registry is None or not registry.is_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": "Entity project registry not initialized.",
            },
        )

    project_gid = registry.get_project_gid(entity_type)
    if project_gid is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": f"No project configured for entity type: {entity_type}",
            },
        )

    # Get bot PAT
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

    try:
        bot_pat = get_bot_pat()
    except BotPATError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "SERVICE_NOT_CONFIGURED",
                "message": "Bot PAT not configured for cache operations.",
            },
        )

    # Build section index
    section_index = None
    if request_body.section is not None:
        from autom8_asana.dataframes.section_persistence import SectionPersistence
        from autom8_asana.metrics.resolve import SectionIndex

        persistence = SectionPersistence()
        section_index = await SectionIndex.from_manifest_async(persistence, project_gid)
        if section_index.resolve(request_body.section) is None:
            section_index = SectionIndex.from_enum_fallback(entity_type)

    # Execute aggregate query
    engine = QueryEngine()
    try:
        async with AsanaClient(token=bot_pat) as client:
            result = await engine.execute_aggregate(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
                request=request_body,
                section_index=section_index,
            )
    except QueryEngineError as e:
        raise _error_to_response(e)
    except CacheNotWarmError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CACHE_NOT_WARMED",
                "message": str(e),
                "retry_after_seconds": 30,
            },
        )

    # Log query completion (TDD Section 16: Observability)
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
