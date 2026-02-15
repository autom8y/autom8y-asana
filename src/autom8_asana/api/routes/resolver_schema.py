"""Schema discovery endpoint for entity resolution.

Per TDD-I10: Extracted from resolver.py to separate the schema discovery
endpoint from the main resolution logic. This module provides the
GET /v1/resolve/{entity_type}/schema endpoint.

Routes:
    GET /{entity_type}/schema - Discover queryable fields for an entity type

Models:
    SchemaFieldInfo: Metadata about a single queryable field
    EntitySchemaResponse: Full schema discovery response
"""

from __future__ import annotations

from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from autom8_asana.api.dependencies import RequestId
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)

__all__ = [
    "schema_router",
    "SchemaFieldInfo",
    "EntitySchemaResponse",
]

logger = get_logger(__name__)

schema_router = APIRouter()


class SchemaFieldInfo(BaseModel):
    """Information about a queryable schema field.

    Per SPIKE-dynamic-api-criteria: Enables API consumers to discover
    valid criterion fields dynamically.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    description: str | None = None


class EntitySchemaResponse(BaseModel):
    """Response for schema discovery endpoint.

    Returns metadata about queryable fields for an entity type.
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str
    version: str
    queryable_fields: list[SchemaFieldInfo]


@schema_router.get(
    "/{entity_type}/schema",
    response_model=EntitySchemaResponse,
    summary="Get queryable fields for entity type",
    description="Returns schema information including all fields that can be used in resolution criteria.",
)
async def get_entity_schema(
    entity_type: str,
    request_id: RequestId,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> EntitySchemaResponse:
    """Return queryable fields for entity type.

    Per SPIKE-dynamic-api-criteria: Enables API consumers to discover
    valid criterion fields dynamically instead of relying on hardcoded
    field lists.

    Args:
        entity_type: Entity type (unit, business, offer, contact)
        claims: Validated service claims from JWT

    Returns:
        Schema information including queryable fields.

    Raises:
        HTTPException: 404 if entity type unknown.
    """
    # Lazy import to avoid circular dependency (resolver_schema -> resolver)
    from autom8_asana.api.routes.resolver import get_supported_entity_types
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    # Validate entity type
    supported_types = get_supported_entity_types()
    if entity_type not in supported_types:
        raise_api_error(
            request_id,
            404,
            "UNKNOWN_ENTITY_TYPE",
            f"Unknown entity type: {entity_type}",
            details={"available_types": sorted(supported_types)},
        )

    # Get schema from registry
    registry = SchemaRegistry.get_instance()
    schema = registry.get_schema(entity_type.capitalize())

    if schema is None:
        raise_api_error(
            request_id,
            404,
            "SCHEMA_NOT_FOUND",
            f"No schema registered for entity type: {entity_type}",
        )

    # Build queryable fields list
    # Include fields that have a source (can be populated) or are core fields
    queryable_fields = [
        SchemaFieldInfo(
            name=col.name,
            type=str(col.dtype),
            description=col.description,
        )
        for col in schema.columns
        if col.source is not None or col.name in {"gid", "name", "parent_gid"}
    ]

    logger.info(
        "schema_discovery_request",
        extra={
            "entity_type": entity_type,
            "version": schema.version,
            "field_count": len(queryable_fields),
            "caller_service": claims.service_name,
        },
    )

    return EntitySchemaResponse(
        entity_type=entity_type,
        version=schema.version,
        queryable_fields=queryable_fields,
    )
