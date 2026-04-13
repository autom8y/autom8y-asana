"""Entity Resolver routes for generalized GID resolution.

Per TDD-entity-resolver Phase 1:
This module provides the POST /v1/resolve/{entity_type} endpoint for resolving
entity identifiers to Asana task GIDs.

Phase 1 implements:
- POST /v1/resolve/unit - Unit resolution via phone/vertical

Routes:
- POST /v1/resolve/{entity_type} - Resolve criteria to task GIDs

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported

Request:
    {
        "criteria": [
            {"phone": "+15551234567", "vertical": "dental"},
            {"phone": "+15559876543", "vertical": "medical"}
        ],
        "fields": ["gid", "name"]  // Optional, Phase 2
    }

Response:
    {
        "results": [
            {"gid": "1234567890123456"},
            {"gid": null, "error": "NOT_FOUND"}
        ],
        "meta": {
            "resolved_count": 1,
            "unresolved_count": 1,
            "entity_type": "unit",
            "project_gid": "1201081073731555"
        }
    }
"""

from __future__ import annotations

import time
from typing import Annotated

from autom8y_log import get_logger
from autom8y_telemetry import get_tracer
from fastapi import Depends
from opentelemetry.trace import StatusCode

from autom8_asana import AsanaClient
from autom8_asana.api.dependencies import (  # noqa: TC001 — FastAPI resolves these at runtime
    AuthContextDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error, raise_service_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.api.routes.resolver_models import (
    ResolutionMeta,
    ResolutionRequest,
    ResolutionResponse,
    ResolutionResultModel,
)
from autom8_asana.api.routes.resolver_schema import schema_router
from autom8_asana.core.entity_types import ENTITY_TYPES
from autom8_asana.core.string_utils import to_pascal_case
from autom8_asana.errors import AsanaError
from autom8_asana.services.errors import ServiceError
from autom8_asana.services.resolver import (
    EntityProjectRegistry,
    filter_result_fields,
    get_resolvable_entities,
    get_strategy,
    is_entity_resolvable,
)

__all__ = [
    "router",
    "get_supported_entity_types",
]

logger = get_logger(__name__)
_tracer = get_tracer(__name__)

router = s2s_router(prefix="/v1/resolve", tags=["resolver"], include_in_schema=True)

# Include schema discovery sub-router
router.include_router(schema_router)


# --- Supported Entity Types ---

# Fallback entity types derived from the canonical source.
# Used only when dynamic discovery (get_resolvable_entities) fails.
SUPPORTED_ENTITY_TYPES: set[str] = set(ENTITY_TYPES)


def get_supported_entity_types() -> set[str]:
    """Get supported entity types via dynamic discovery with fallback.

    Per TDD-DYNAMIC-RESOLVER-001 / FR-001:
    Derives resolvable entities from SchemaRegistry + EntityProjectRegistry.

    The universal strategy supports any entity with a schema and registered project.

    Returns:
        Set of entity type strings that are resolvable.
    """
    supported: set[str] = set()

    # Primary: Schema-based discovery
    try:
        discovered = get_resolvable_entities()
        supported.update(discovered)
    except Exception as e:  # BROAD-CATCH: degrade
        logger.warning(
            "entity_discovery_error",
            extra={"error": str(e)},
        )

    # Secondary: Include all entities with registered projects
    # The universal strategy can handle any entity with a schema
    try:
        project_registry = EntityProjectRegistry.get_instance()
        if project_registry.is_ready():
            for entity_type in project_registry.get_all_entity_types():
                if is_entity_resolvable(entity_type):
                    supported.add(entity_type)
    except Exception as e:  # BROAD-CATCH: degrade
        logger.warning(
            "entity_registry_check_error",
            extra={"error": str(e)},
        )

    # Final fallback if nothing discovered
    if not supported:
        logger.warning(
            "entity_discovery_fallback",
            extra={"fallback": "SUPPORTED_ENTITY_TYPES"},
        )
        return SUPPORTED_ENTITY_TYPES

    return supported


# --- Endpoints ---


@router.post(
    "/{entity_type}",
    response_model=SuccessResponse[ResolutionResponse],
    summary="Resolve entity identifiers to task GIDs",
    description=(
        "Resolve business identifiers (phone/vertical, offer_id, etc.) to "
        "Asana task GIDs using entity-type-specific resolution strategies. "
        "Supports batch resolution of multiple criteria in a single request. "
        "Use GET /v1/resolve/{entity_type}/schema to discover valid criterion "
        "fields for each entity type."
    ),
    openapi_extra={
        "x-fleet-side-effects": [],
        "x-fleet-idempotency": {"idempotent": True, "key_source": None},
        "x-fleet-cross-service-refs": {"service": "autom8y-asana", "entity": "task"},
    },
)
async def resolve_entities(
    entity_type: str,
    request_body: ResolutionRequest,
    request_id: RequestId,
    auth: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[ResolutionResponse]:
    """Resolve entity identifiers to task GIDs.

    This endpoint resolves business identifiers (phone/vertical, offer_id, etc.)
    to Asana task GIDs using entity-type-specific resolution strategies.

    Authentication:
        Requires valid service token (S2S JWT).
        PAT tokens are NOT supported.

    Path Parameters:
        entity_type: Entity type to resolve (unit, business, offer, contact)

    Request:
        POST /v1/resolve/unit
        {
            "criteria": [
                {"phone": "+15551234567", "vertical": "dental"},
                {"phone": "+15559876543", "vertical": "medical"}
            ]
        }

    Response:
        {
            "results": [
                {"gid": "1234567890123456"},
                {"gid": null, "error": "NOT_FOUND"}
            ],
            "meta": {
                "resolved_count": 1,
                "unresolved_count": 1,
                "entity_type": "unit",
                "project_gid": "1201081073731555"
            }
        }

    Error Responses:
        - 401 MISSING_AUTH: No Authorization header
        - 401 SERVICE_TOKEN_REQUIRED: PAT token provided (S2S only)
        - 404 UNKNOWN_ENTITY_TYPE: entity_type not in allowed values
        - 422 VALIDATION_ERROR: Invalid request body
        - 503 DISCOVERY_INCOMPLETE: Startup discovery not finished

    Args:
        entity_type: Path parameter for entity type
        request_body: ResolutionRequest with criteria
        request_id: Request ID from RequestId dependency
        auth: Authentication context with Asana PAT
        claims: Validated service claims from JWT

    Returns:
        ResolutionResponse with results and metadata.
    """
    start_time = time.monotonic()

    logger.info(
        "entity_resolution_request",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "criteria_count": len(request_body.criteria),
            "caller_service": claims.service_name,
        },
    )

    # Validate entity type via dynamic discovery (TASK-004)
    supported_types = get_supported_entity_types()
    if entity_type not in supported_types:
        logger.warning(
            "unknown_entity_type",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "supported": sorted(supported_types),
            },
        )
        raise_api_error(
            request_id,
            404,
            "UNKNOWN_ENTITY_TYPE",
            f"Unknown entity type: {entity_type}. "
            f"Supported types: {', '.join(sorted(supported_types))}",
            details={"available_types": sorted(supported_types)},
        )

    # Get entity project registry from singleton
    entity_registry = EntityProjectRegistry.get_instance()

    if not entity_registry.is_ready():
        logger.error(
            "entity_discovery_incomplete",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
            },
        )
        raise_api_error(
            request_id,
            503,
            "DISCOVERY_INCOMPLETE",
            "Entity resolver startup discovery has not completed. "
            "Please retry after service is fully initialized.",
        )

    # Get project GID for entity type
    project_gid = entity_registry.get_project_gid(entity_type)

    if project_gid is None:
        logger.error(
            "entity_project_not_registered",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
            },
        )
        raise_api_error(
            request_id,
            503,
            "PROJECT_NOT_CONFIGURED",
            f"No project configured for entity type: {entity_type}. "
            f"Check startup discovery logs for configuration issues.",
        )

    # Get resolution strategy
    strategy = get_strategy(entity_type)

    if strategy is None:
        logger.error(
            "strategy_not_found",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
            },
        )
        raise_api_error(
            request_id,
            501,
            "STRATEGY_NOT_IMPLEMENTED",
            f"Resolution strategy not implemented for: {entity_type}",
        )

    # Convert criteria to dicts for universal strategy
    criteria_dicts = [
        criterion.model_dump(exclude_none=True) for criterion in request_body.criteria
    ]

    # Validate criteria for entity type
    for i, criterion_dict in enumerate(criteria_dicts):
        validation_errors = strategy.validate_criterion(criterion_dict)
        if validation_errors:
            raise_api_error(
                request_id,
                422,
                "MISSING_REQUIRED_FIELD",
                f"Criterion {i}: {'; '.join(validation_errors)}",
            )

    # Validate requested fields against schema (DEF-001)
    if request_body.fields:
        try:
            # Call filter_result_fields with empty result to validate field names
            filter_result_fields({}, request_body.fields, entity_type)
        except ValueError as e:
            raise_api_error(
                request_id,
                422,
                "INVALID_FIELD",
                str(e),
            )

    # Resolve using strategy
    # Per TDD-STATUS-AWARE-RESOLUTION / FR-1:
    # Pass active_only from request to strategy
    with _tracer.start_as_current_span(
        "resolver.entities.resolve",
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        span.set_attribute("resolver.entity_type", entity_type)
        span.set_attribute("resolver.criteria_count", len(request_body.criteria))
        span.set_attribute("resolver.project_gid", project_gid)
        span.set_attribute("resolver.caller_service", claims.service_name)

        try:
            async with AsanaClient(token=auth.asana_pat) as client:
                resolution_results = await strategy.resolve(
                    criteria=criteria_dicts,
                    project_gid=project_gid,
                    client=client,
                    requested_fields=request_body.fields,
                    active_only=request_body.active_only,
                )

        except ServiceError as e:
            # Per ADR-error-taxonomy-resolution: Tier 1 -- delegate to raise_service_error()
            # which preserves error.error_code and error.to_dict() per ADR-I6-001.
            logger.warning(
                "entity_resolution_service_error",
                extra={
                    "request_id": request_id,
                    "entity_type": entity_type,
                    "error_code": e.error_code,
                    "error": str(e),
                },
            )
            span.set_attribute("resolver.error_code", e.error_code)
            span.set_attribute("resolver.error_tier", "service_error")
            span.set_attribute("error.type", type(e).__name__)
            span.record_exception(e)
            span.set_status(StatusCode.ERROR, description=e.error_code)
            raise_service_error(request_id, e)

        except AsanaError as e:
            # Per ADR-error-taxonomy-resolution: Tier 2 -- re-raise to let FastAPI's
            # registered global handlers (api/errors.py) produce the correct response.
            # They already map NotFoundError->404, RateLimitError->429, etc.
            span.set_attribute("resolver.error_tier", "asana_error")
            span.set_attribute("error.type", type(e).__name__)
            span.set_status(StatusCode.ERROR, description=type(e).__name__)
            raise

        except Exception as e:  # BROAD-CATCH: boundary (preserved)
            # Per ADR-error-taxonomy-resolution: Tier 3 -- backward-compatible fallback
            # for truly unexpected failures.
            logger.exception(
                "entity_resolution_error",
                extra={
                    "request_id": request_id,
                    "entity_type": entity_type,
                    "error": str(e),
                },
            )
            span.record_exception(e)
            span.set_attribute("resolver.error_code", "RESOLUTION_ERROR")
            span.set_attribute("resolver.error_tier", "unexpected")
            span.set_attribute("error.type", type(e).__name__)
            span.set_status(StatusCode.ERROR, description="RESOLUTION_ERROR")
            raise_api_error(
                request_id,
                500,
                "RESOLUTION_ERROR",
                "An unexpected error occurred during resolution.",
            )

        # Convert ResolutionResult to ResolutionResultModel
        # Per TDD-STATUS-AWARE-RESOLUTION / FR-3, FR-11:
        # Map status_annotations and total_match_count to response model
        results = [
            ResolutionResultModel(
                gid=r.gid,  # Backwards compat: first match
                gids=list(r.gids) if r.gids else None,
                match_count=r.match_count,
                error=r.error,
                data=list(r.match_context) if r.match_context else None,
                status=list(r.status_annotations) if r.status_annotations else None,
                total_match_count=r.total_match_count,
            )
            for r in resolution_results
        ]

        # Calculate counts
        resolved_count = sum(1 for r in results if r.gid is not None)
        unresolved_count = len(results) - resolved_count

        span.set_attribute("resolver.resolved_count", resolved_count)
        span.set_attribute("resolver.unresolved_count", unresolved_count)

        # Get available fields from schema registry
        from autom8_asana.dataframes.models.registry import SchemaRegistry

        available_fields: list[str] = []
        try:
            registry = SchemaRegistry.get_instance()
            schema = registry.get_schema(to_pascal_case(entity_type))
            if schema is not None:
                # Include queryable fields (those with a source or core fields)
                available_fields = [
                    col.name
                    for col in schema.columns
                    if col.source is not None
                    or col.name in {"gid", "name", "parent_gid"}
                ]
        except (KeyError, AttributeError, RuntimeError):  # non-critical metadata
            # If schema lookup fails, leave available_fields empty
            # This is metadata, not critical to resolution success
            pass

        # Extract criteria_schema from request
        criteria_schema: list[str] = []
        if criteria_dicts:
            # Collect all unique keys used across all criteria
            all_keys: set[str] = set()
            for criterion in criteria_dicts:
                all_keys.update(criterion.keys())
            criteria_schema = sorted(all_keys)

        # Build response
        response = ResolutionResponse(
            results=results,
            meta=ResolutionMeta(
                resolved_count=resolved_count,
                unresolved_count=unresolved_count,
                entity_type=entity_type,
                project_gid=project_gid,
                available_fields=available_fields,
                criteria_schema=criteria_schema,
            ),
        )

        # Log completion
        elapsed_ms = (time.monotonic() - start_time) * 1000

        logger.info(
            "entity_resolution_complete",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "criteria_count": len(request_body.criteria),
                "resolved_count": resolved_count,
                "unresolved_count": unresolved_count,
                "duration_ms": round(elapsed_ms, 2),
                "caller_service": claims.service_name,
                "project_gid": project_gid,
            },
        )

        return build_success_response(data=response, request_id=request_id)
