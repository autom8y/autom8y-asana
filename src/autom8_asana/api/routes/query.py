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

from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.client import AsanaClient
from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS
from autom8_asana.dataframes.exceptions import SchemaNotFoundError
from autom8_asana.dataframes.models.registry import SchemaRegistry
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
from autom8_asana.services.query_service import CacheNotWarmError, EntityQueryService
from autom8_asana.services.resolver import (
    EntityProjectRegistry,
    get_resolvable_entities,
    to_pascal_case,
)

__all__ = [
    "router",
    "QueryRequest",
    "QueryMeta",
    "QueryResponse",
]

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/query", tags=["query"])


# Default fields when select is not specified
DEFAULT_SELECT_FIELDS = ["gid", "name", "section"]


# --- Request/Response Models ---


class QueryRequest(BaseModel):
    """Request body for entity query.

    Per PRD FR-002: Unified where clause with AND semantics.

    Attributes:
        where: Filter criteria (field -> value, AND semantics).
        select: Fields to include in response (default: gid, name, section).
        limit: Max results per page (1-1000, default 100).
        offset: Skip N results for pagination (default 0).
    """

    model_config = ConfigDict(extra="forbid")

    where: dict[str, Any] = {}
    select: list[str] | None = None
    limit: int = 100
    offset: int = 0

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Enforce limit bounds (1-1000), clamp if exceeded."""
        if v < 1:
            raise ValueError("limit must be >= 1")
        return min(v, 1000)  # Clamp to max

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        """Enforce non-negative offset."""
        if v < 0:
            raise ValueError("offset must be >= 0")
        return v


class QueryMeta(BaseModel):
    """Response metadata for pagination and context."""

    model_config = ConfigDict(extra="forbid")

    total_count: int  # Total matching records (before pagination)
    limit: int  # Limit used for this request
    offset: int  # Offset used for this request
    entity_type: str  # Entity type queried
    project_gid: str  # Project GID used


class QueryResponse(BaseModel):
    """Response body for entity query.

    Per PRD FR-003: Contains data array and metadata.
    """

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]  # Matching records with selected fields
    meta: QueryMeta


# --- Helper Functions ---


def _get_queryable_entities() -> set[str]:
    """Get entity types that support querying.

    Returns entity types that have both a schema and registered project.
    """
    return get_resolvable_entities()


def _validate_fields(
    fields: list[str],
    entity_type: str,
    field_type: str,  # "where" or "select"
) -> None:
    """Validate fields against entity schema.

    Args:
        fields: Field names to validate.
        entity_type: Entity type for schema lookup.
        field_type: "where" or "select" for error message.

    Raises:
        HTTPException: 422 if any field is invalid.
    """
    registry = SchemaRegistry.get_instance()
    schema_key = to_pascal_case(entity_type)

    try:
        schema = registry.get_schema(schema_key)
    except SchemaNotFoundError:
        schema = registry.get_schema("*")

    valid_fields = set(schema.column_names())
    invalid_fields = set(fields) - valid_fields

    if invalid_fields:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_FIELD",
                "message": f"Unknown field(s) in {field_type} clause: {sorted(invalid_fields)}",
                "available_fields": sorted(valid_fields),
            },
        )


def _get_query_service() -> EntityQueryService:
    """Get EntityQueryService instance.

    Factory function for dependency injection.
    """
    return EntityQueryService()


# --- Endpoints ---


@router.post("/{entity_type}", response_model=QueryResponse)
async def query_entities(
    entity_type: str,
    request_body: QueryRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> JSONResponse:
    """Query entities from DataFrame cache with full cache lifecycle.

    CRITICAL: This endpoint uses EntityQueryService which routes through
    UniversalResolutionStrategy._get_dataframe(). This ensures:
    - Cache hit: Returns immediately from Memory/S3 tier
    - Cache miss: Triggers self-refresh via legacy strategy
    - Concurrent misses: Coalesced (first builds, others wait)
    - Repeated failures: Circuit breaker protects system

    Authentication:
        Requires valid service token (S2S JWT).
        PAT tokens are NOT supported.

    Path Parameters:
        entity_type: Entity type to query (unit, business, offer, etc.)

    Request:
        POST /v1/query/offer
        {
            "where": {"section": "ACTIVE"},
            "select": ["gid", "name", "office_phone"],
            "limit": 100,
            "offset": 0
        }

    Response:
        {
            "data": [{"gid": "123", "name": "...", "office_phone": "..."}],
            "meta": {"total_count": 47, "limit": 100, "offset": 0, ...}
        }

    Error Responses:
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 401 JWT_INVALID: JWT validation failed
        - 404 UNKNOWN_ENTITY_TYPE: entity_type not in allowed values
        - 422 INVALID_FIELD: Field in where/select not in schema
        - 422 VALIDATION_ERROR: Invalid request body
        - 503 CACHE_NOT_WARMED: DataFrame cache not available
        - 503 PROJECT_NOT_CONFIGURED: No project configured for entity
    """
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

    # Validate entity type
    queryable_types = _get_queryable_entities()
    if entity_type not in queryable_types:
        logger.warning(
            "unknown_entity_type",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "available": sorted(queryable_types),
            },
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UNKNOWN_ENTITY_TYPE",
                "message": f"Unknown entity type: {entity_type}",
                "available_types": sorted(queryable_types),
            },
        )

    # Validate where fields
    if request_body.where:
        _validate_fields(
            list(request_body.where.keys()),
            entity_type,
            "where",
        )

    # Determine select fields
    select_fields = request_body.select or DEFAULT_SELECT_FIELDS

    # Validate select fields
    _validate_fields(select_fields, entity_type, "select")

    # Get project GID from EntityProjectRegistry
    entity_registry: EntityProjectRegistry | None = getattr(
        request.app.state, "entity_project_registry", None
    )

    if entity_registry is None or not entity_registry.is_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": "Entity project registry not initialized.",
            },
        )

    project_gid = entity_registry.get_project_gid(entity_type)

    if project_gid is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": f"No project configured for entity type: {entity_type}",
            },
        )

    # Get AsanaClient for potential cache build operations
    # Uses bot PAT from environment (same as resolve endpoint)
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.error(
            "bot_pat_unavailable",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "SERVICE_NOT_CONFIGURED",
                "message": "Bot PAT not configured for cache operations.",
            },
        )

    # Execute query via EntityQueryService
    # This routes through UniversalResolutionStrategy._get_dataframe()
    # which provides full cache lifecycle (self-refresh, coalescing, circuit breaker)
    query_service = _get_query_service()

    try:
        async with AsanaClient(token=bot_pat) as client:
            result = await query_service.query(
                entity_type=entity_type,
                project_gid=project_gid,
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
                "project_gid": project_gid,
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

    # Build response
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

    # Log completion
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


# --- Section Resolution Helper ---


async def _resolve_section(
    section_name: str,
    entity_type: str,
    project_gid: str,
) -> str:
    """Validate section name and return canonical name for filtering.

    Strategy:
    1. Try SectionIndex.from_manifest_async() using SectionPersistence
    2. Fall back to SectionIndex.from_enum_fallback(entity_type)
    3. If neither resolves, raise UNKNOWN_SECTION error

    Returns:
        The section name as provided (for direct DataFrame column match).

    Raises:
        HTTPException 422 UNKNOWN_SECTION
    """
    from autom8_asana.metrics.resolve import SectionIndex

    # Try manifest-based resolution first
    try:
        from autom8_asana.dataframes.section_persistence import SectionPersistence

        persistence = SectionPersistence()
        if persistence.is_available:
            async with persistence:
                index = await SectionIndex.from_manifest_async(persistence, project_gid)
                if index.resolve(section_name) is not None:
                    return section_name
    except S3_TRANSPORT_ERRORS:
        # Manifest unavailable; fall through to enum fallback
        logger.debug(
            "manifest_section_resolution_failed",
            exc_info=True,
            extra={
                "section_name": section_name,
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )

    # Enum fallback
    index = SectionIndex.from_enum_fallback(entity_type)
    if index.resolve(section_name) is not None:
        return section_name

    raise HTTPException(
        status_code=422,
        detail={
            "error": "UNKNOWN_SECTION",
            "message": f"Unknown section: '{section_name}'",
            "section": section_name,
        },
    )


# --- New /rows Endpoint ---


@router.post("/{entity_type}/rows", response_model=RowsResponse)
async def query_rows(
    entity_type: str,
    request_body: RowsRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> RowsResponse:
    """Query entity rows with composable predicate trees.

    Accepts a JSON predicate AST (AND/OR/NOT with leaf comparisons),
    compiles it to a Polars expression, and filters the cached DataFrame.

    Authentication:
        Requires valid service token (S2S JWT).
        PAT tokens are NOT supported.

    Path Parameters:
        entity_type: Entity type to query (unit, business, offer, etc.)

    Error Responses:
        - 400 QUERY_TOO_COMPLEX: Predicate depth exceeds MAX_PREDICATE_DEPTH
        - 401 MISSING_AUTH / SERVICE_TOKEN_REQUIRED / JWT_INVALID
        - 404 UNKNOWN_ENTITY_TYPE: entity_type not in allowed values
        - 422 UNKNOWN_FIELD: Predicate references non-existent column
        - 422 INVALID_OPERATOR: Operator incompatible with field dtype
        - 422 COERCION_FAILED: Value cannot be coerced to field dtype
        - 422 UNKNOWN_SECTION: Section name cannot be resolved
        - 503 CACHE_NOT_WARMED: DataFrame cache not available
    """
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

    # 2. Validate entity type
    queryable_types = _get_queryable_entities()
    if entity_type not in queryable_types:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UNKNOWN_ENTITY_TYPE",
                "message": f"Unknown entity type: {entity_type}",
                "available_types": sorted(queryable_types),
            },
        )

    # 3. Get project GID
    entity_registry: EntityProjectRegistry | None = getattr(
        request.app.state, "entity_project_registry", None
    )

    if entity_registry is None or not entity_registry.is_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": "Entity project registry not initialized.",
            },
        )

    project_gid = entity_registry.get_project_gid(entity_type)
    if project_gid is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": f"No project configured for entity type: {entity_type}",
            },
        )

    # 4. Get bot PAT
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.error(
            "bot_pat_unavailable",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "SERVICE_NOT_CONFIGURED",
                "message": "Bot PAT not configured for cache operations.",
            },
        )

    # 5. Build section index for section validation (if needed)
    section_index = None
    if request_body.section is not None:
        # Validate section name
        await _resolve_section(request_body.section, entity_type, project_gid)
        # Build section index for QueryEngine
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex.from_enum_fallback(entity_type)

    # 6. EC-006: If section param + section in predicate, strip conflicts
    if request_body.section is not None and request_body.where is not None:
        from autom8_asana.query.models import Comparison

        # Check if any section predicates exist
        def _has_section_pred(node: Any) -> bool:
            if isinstance(node, Comparison):
                return node.field == "section"
            if hasattr(node, "and_"):
                return any(_has_section_pred(c) for c in node.and_)
            if hasattr(node, "or_"):
                return any(_has_section_pred(c) for c in node.or_)
            if hasattr(node, "not_"):
                return _has_section_pred(node.not_)
            return False

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
            # Reconstruct the request with stripped predicates
            request_body = request_body.model_copy(update={"where": stripped})

    # 7. Execute via QueryEngine (handles compilation, depth check, etc.)
    engine = QueryEngine()

    try:
        async with AsanaClient(token=bot_pat) as client:
            response = await engine.execute_rows(
                entity_type=entity_type,
                project_gid=project_gid,
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

    # 8. Log completion
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
