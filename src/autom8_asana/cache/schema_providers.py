"""Bridge Asana SchemaRegistry to autom8y-cache SDK SchemaVersionProvider.

This module provides the integration between the satellite's internal
SchemaRegistry (which tracks DataFrame schemas for Unit, Contact, etc.)
and the SDK's schema versioning system for cache compatibility checks.

Per SDK Phase 1:
- SchemaVersion and CompatibilityMode types are in the SDK
- SchemaVersionProvider protocol defines the interface
- register_schema_provider() registers providers with the SDK registry

Example:
    >>> from autom8_asana.cache.schema_providers import register_asana_schemas
    >>> register_asana_schemas()  # Call during app startup
"""

from __future__ import annotations

import logging

from autom8y_cache import (
    CompatibilityMode,
    SchemaVersion,
    register_schema_provider,
)

from autom8_asana.dataframes.models.registry import SchemaRegistry

logger = logging.getLogger(__name__)


class AsanaSchemaProvider:
    """Bridges Asana SchemaRegistry to SDK SchemaVersionProvider protocol.

    Implements the SDK's SchemaVersionProvider protocol by wrapping the
    satellite's SchemaRegistry. Each instance is bound to a specific
    entity type (e.g., "unit", "contact", "offer").

    Attributes:
        _entity_type: The entity type this provider represents.
    """

    def __init__(self, entity_type: str) -> None:
        """Initialize provider for a specific entity type.

        Args:
            entity_type: Entity type identifier (e.g., "unit", "contact").
        """
        self._entity_type = entity_type

    @property
    def schema_version(self) -> SchemaVersion:
        """Get current schema version from SchemaRegistry.

        Returns:
            SchemaVersion parsed from the schema's version string.
        """
        # SchemaRegistry expects title case: "unit" -> "Unit"
        task_type = self._entity_type.title()
        schema = SchemaRegistry.get_instance().get_schema(task_type)
        return SchemaVersion.from_string(schema.version)

    @property
    def compatibility_mode(self) -> CompatibilityMode:
        """Get compatibility mode for this entity type.

        For now, we use EXACT mode which requires version strings to match
        exactly. This is the safest approach for initial implementation.

        Returns:
            CompatibilityMode.EXACT for strict version matching.
        """
        return CompatibilityMode.EXACT


def register_asana_schemas() -> None:
    """Register all Asana entity schemas with SDK registry.

    Should be called during application startup to make schema versions
    available to the SDK's cache compatibility checking system.

    Registers providers for: unit, contact, offer, business
    Each is prefixed with "asana:" namespace (e.g., "asana:unit").
    """
    entity_types = ["unit", "contact", "offer", "business"]

    for entity_type in entity_types:
        entry_type = f"asana:{entity_type}"
        provider = AsanaSchemaProvider(entity_type)
        register_schema_provider(entry_type, provider)

        logger.info(
            "schema_provider_registered",
            extra={
                "entry_type": entry_type,
                "schema_version": str(provider.schema_version),
                "compatibility_mode": provider.compatibility_mode.value,
            },
        )

    logger.info(
        "asana_schemas_registered",
        extra={
            "entity_types": entity_types,
            "count": len(entity_types),
        },
    )
