"""Bridge Asana SchemaRegistry to autom8y-cache SDK SchemaVersionProvider.

This module provides the integration between the satellite's internal
SchemaRegistry (which tracks DataFrame schemas for Unit, Contact, etc.)
and the SDK's schema versioning system for cache compatibility checks.

Per SDK Phase 1:
- SchemaVersion and CompatibilityMode types are in the SDK
- SchemaVersionProvider protocol defines the interface
- register_schema_provider() registers providers with the SDK registry

Example:
    >>> from autom8_asana.cache.integration.schema_providers import register_asana_schemas
    >>> register_asana_schemas()  # Call during app startup

Note:
    Schema versioning requires autom8y-cache >= 0.5.0 with schema_version module.
    If unavailable, register_asana_schemas() logs a warning and returns gracefully.
"""

from __future__ import annotations

from autom8y_cache import CompatibilityMode, SchemaVersion
from autom8y_log import get_logger

from autom8_asana.core.string_utils import to_pascal_case
from autom8_asana.dataframes.models.registry import get_schema

logger = get_logger(__name__)

# Schema versioning is optional - requires SDK >= 0.5.0
# Fail gracefully if not available (SDK not yet published with these features)
_SCHEMA_VERSIONING_AVAILABLE = False
try:
    from autom8y_cache import (
        CompatibilityMode,
        SchemaVersion,
        register_schema_provider,
    )

    _SCHEMA_VERSIONING_AVAILABLE = True
except ImportError:
    # SDK version doesn't have schema versioning yet
    CompatibilityMode = None  # type: ignore[misc, assignment]
    SchemaVersion = None  # type: ignore[misc, assignment]
    register_schema_provider = None  # type: ignore[assignment]


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
        # SchemaRegistry expects PascalCase: "unit" -> "Unit", "asset_edit" -> "AssetEdit"
        task_type = to_pascal_case(self._entity_type)
        schema = get_schema(task_type)
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

    Note:
        If autom8y-cache doesn't have schema versioning support (< 0.5.0),
        this function logs a warning and returns without error. Schema
        registration will be enabled once the SDK is updated.
    """
    if not _SCHEMA_VERSIONING_AVAILABLE:
        logger.warning(
            "schema_versioning_unavailable",
            extra={
                "reason": "autom8y-cache missing schema versioning exports",
                "impact": "Schema compatibility checks disabled",
                "remediation": "Update autom8y-cache to >= 0.5.0 when available",
            },
        )
        return

    from autom8_asana.core.entity_types import ENTITY_TYPES_WITH_DERIVATIVES

    for entity_type in ENTITY_TYPES_WITH_DERIVATIVES:
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
            "entity_types": ENTITY_TYPES_WITH_DERIVATIVES,
            "count": len(ENTITY_TYPES_WITH_DERIVATIVES),
        },
    )
