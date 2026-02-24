"""Entity Resolver service for generalized GID resolution.

Provides schema-driven entity resolution using DynamicIndex for O(1) lookups.
Supports any entity type with a registered schema and project.

Components:
- EntityProjectConfig: Configuration for a single entity type's project mapping
- EntityProjectRegistry: Singleton registry populated at startup
- ResolutionResult: Multi-match result imported from resolution_result module
- get_strategy: Factory function returning UniversalResolutionStrategy

Per ADR-0060: Project GIDs discovered at startup via WorkspaceProjectRegistry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from autom8y_log import get_logger

from autom8_asana.dataframes.exceptions import SchemaNotFoundError
from autom8_asana.services.resolution_result import ResolutionResult

if TYPE_CHECKING:
    from autom8_asana.services.universal_strategy import UniversalResolutionStrategy

__all__ = [
    "EntityProjectConfig",
    "EntityProjectRegistry",
    "ResolutionResult",
    "get_strategy",
    "filter_result_fields",
    "get_resolvable_entities",
    "validate_criterion_for_entity",
    "CriterionValidationResult",
    "ENTITY_ALIASES",
    "to_pascal_case",
    "_clear_resolvable_cache",
]

logger = get_logger(__name__)


# --- Utility Functions ---


from autom8_asana.core.string_utils import (
    to_pascal_case as to_pascal_case,  # noqa: E501 — re-export for backward compat
)

# --- Data Models ---


@dataclass(frozen=True, slots=True)
class EntityProjectConfig:
    """Configuration for a single entity type's project mapping.

    Per TDD: Immutable dataclass for thread-safe access.

    Attributes:
        entity_type: Entity type identifier (e.g., "unit", "business")
        project_gid: Asana project GID
        project_name: Human-readable name (for logging)
        schema_task_type: SchemaRegistry key (e.g., "Unit", "Contact")
    """

    entity_type: str
    project_gid: str
    project_name: str
    schema_task_type: str | None = None


# --- EntityProjectRegistry ---


class EntityProjectRegistry:
    """Singleton registry mapping entity_type -> project configuration.

    Per TDD: Populated at startup via WorkspaceProjectRegistry discovery.
    Thread-safe via immutable design (populated once, read-only after).

    Per ADR-0060: Startup discovery with fail-fast on missing projects.

    Usage:
        # Get singleton instance
        registry = EntityProjectRegistry.get_instance()

        # Check readiness
        if not registry.is_ready():
            raise RuntimeError("Discovery not complete")

        # Get project GID for entity type
        gid = registry.get_project_gid("unit")

    Testing:
        # Reset for test isolation
        EntityProjectRegistry.reset()
    """

    _instance: ClassVar[EntityProjectRegistry | None] = None

    # Instance attributes
    _configs: dict[str, EntityProjectConfig]
    _initialized: bool

    def __new__(cls) -> EntityProjectRegistry:
        """Get or create singleton instance.

        Returns:
            The singleton EntityProjectRegistry instance.
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._configs = {}
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize instance attributes (only runs once due to singleton)."""
        # Attributes are set in __new__ to avoid re-initialization
        pass

    @classmethod
    def get_instance(cls) -> EntityProjectRegistry:
        """Get the singleton instance.

        Returns:
            The singleton EntityProjectRegistry instance.
        """
        return cls()

    def register(
        self,
        entity_type: str,
        project_gid: str,
        project_name: str,
        schema_task_type: str | None = None,
    ) -> None:
        """Register an entity type to project mapping.

        Args:
            entity_type: Entity type identifier (e.g., "unit")
            project_gid: Asana project GID
            project_name: Human-readable project name
            schema_task_type: SchemaRegistry key (optional)
        """
        # Derive schema_task_type from entity_type if not provided
        if schema_task_type is None:
            schema_task_type = to_pascal_case(entity_type)  # "unit" -> "Unit"

        config = EntityProjectConfig(
            entity_type=entity_type,
            project_gid=project_gid,
            project_name=project_name,
            schema_task_type=schema_task_type,
        )

        self._configs[entity_type] = config
        self._initialized = True

        logger.debug(
            "entity_type_registered",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
                "project_name": project_name,
            },
        )

    def get_project_gid(self, entity_type: str) -> str | None:
        """Get project GID for entity type. O(1).

        Args:
            entity_type: Entity type identifier

        Returns:
            Project GID if registered, None otherwise.
        """
        config = self._configs.get(entity_type)
        return config.project_gid if config else None

    def get_config(self, entity_type: str) -> EntityProjectConfig | None:
        """Get full config for entity type. O(1).

        Args:
            entity_type: Entity type identifier

        Returns:
            EntityProjectConfig if registered, None otherwise.
        """
        return self._configs.get(entity_type)

    def is_ready(self) -> bool:
        """True if startup discovery completed successfully.

        Returns:
            True if at least one entity type is registered.
        """
        return self._initialized and len(self._configs) > 0

    def get_all_entity_types(self) -> list[str]:
        """Get all registered entity types.

        Returns:
            List of registered entity type identifiers.
        """
        return list(self._configs.keys())

    @classmethod
    def reset(cls) -> None:
        """Reset for testing.

        Clears the singleton instance so next access creates a fresh registry.
        Also clears the resolvable entities cache.
        """
        cls._instance = None
        _clear_resolvable_cache()
        logger.debug("EntityProjectRegistry reset")


# --- Dynamic Field Normalization (FR-006) ---

# FACADE: Delegates to EntityRegistry. Preserves existing import path.
# See: src/autom8_asana/core/entity_registry.py for the single source of truth.
#
# Per TDD-dynamic-field-normalization:
# Hierarchical alias resolution replaces static field mappings.
# Resolution chain examples:
#   - unit + "phone" -> office_phone (via unit->business_unit->business->office)
#   - offer + "phone" -> office_phone (via offer->business_offer->business->office)
#   - contact + "email" -> contact_email (via prefix expansion)
from autom8_asana.core.entity_registry import get_registry as _get_entity_registry

ENTITY_ALIASES: dict[str, list[str]] = {
    d.name: list(d.aliases)
    for d in _get_entity_registry().all_descriptors()
    if d.warmable  # Only warmable entities had aliases in the original dict
}


# --- Schema-Driven Entity Discovery (FR-001, FR-002) ---

# Module-level cache for resolvable entities
# Cleared on registry reset (see EntityProjectRegistry.reset())
_cached_entities: set[str] | None = None


def _clear_resolvable_cache() -> None:
    """Clear the cached resolvable entities set.

    Called by registry reset methods to invalidate the cache.
    Thread-safe: cache reads/writes are atomic for set objects in Python.
    """
    global _cached_entities
    _cached_entities = None


@dataclass
class CriterionValidationResult:
    """Result of criterion validation against schema.

    Per TDD-DYNAMIC-RESOLVER-001 / FR-002:
    Provides detailed validation results with helpful error messages.

    Attributes:
        is_valid: True if all criterion fields are valid schema columns.
        errors: List of validation error messages.
        unknown_fields: Fields in criterion not in schema.
        available_fields: All valid fields from schema.
        normalized_criterion: Criterion with legacy fields mapped to schema names.
    """

    is_valid: bool
    errors: list[str]
    unknown_fields: list[str]
    available_fields: list[str]
    normalized_criterion: dict[str, Any]


def get_resolvable_entities(
    schema_registry: Any | None = None,
    project_registry: EntityProjectRegistry | None = None,
) -> set[str]:
    """Derive resolvable entities from existing registries.

    Per TDD-DYNAMIC-RESOLVER-001 / FR-001:
    An entity is resolvable if and only if:
    1. It has a schema registered in SchemaRegistry
    2. It has a project registered in EntityProjectRegistry

    Caching:
        Results are cached after first computation when using singleton registries.
        Cache is cleared on registry reset via _clear_resolvable_cache().

    Args:
        schema_registry: SchemaRegistry instance (uses singleton if None).
        project_registry: EntityProjectRegistry instance (uses singleton if None).

    Returns:
        Set of entity type strings that are resolvable.

    Example:
        >>> entities = get_resolvable_entities()
        >>> "unit" in entities
        True
        >>> "unknown" in entities
        False
    """
    global _cached_entities

    # Use cache only when called with singletons (no custom registries)
    using_singletons = schema_registry is None and project_registry is None

    if using_singletons and _cached_entities is not None:
        logger.debug(
            "resolvable_entities_cache_hit",
            extra={"count": len(_cached_entities)},
        )
        return _cached_entities

    from autom8_asana.dataframes.models.registry import SchemaRegistry

    if schema_registry is None:
        schema_registry = SchemaRegistry.get_instance()
    if project_registry is None:
        project_registry = EntityProjectRegistry.get_instance()

    resolvable: set[str] = set()

    # Get all task types with schemas (excludes "*" base schema)
    for task_type in schema_registry.list_task_types():
        # Use schema.name for entity_type (handles snake_case like "asset_edit")
        schema = schema_registry.get_schema(task_type)
        entity_type = schema.name  # "asset_edit", "unit", etc.

        # Check if entity has a registered project
        if project_registry.get_project_gid(entity_type) is not None:
            resolvable.add(entity_type)
            logger.debug(
                "entity_discovered_resolvable",
                extra={
                    "entity_type": entity_type,
                    "task_type": task_type,
                },
            )

    logger.info(
        "resolvable_entities_discovered",
        extra={
            "count": len(resolvable),
            "entities": sorted(resolvable),
        },
    )

    # Cache result when using singletons
    if using_singletons:
        _cached_entities = resolvable

    return resolvable


def is_entity_resolvable(entity_type: str) -> bool:
    """Check if a single entity type is resolvable.

    Args:
        entity_type: Entity type to check (e.g., "unit").

    Returns:
        True if entity has both schema and project registered.
    """
    return entity_type.lower() in get_resolvable_entities()


def validate_criterion_for_entity(
    entity_type: str,
    criterion: dict[str, Any],
) -> CriterionValidationResult:
    """Validate criterion fields against entity schema.

    Per TDD-DYNAMIC-RESOLVER-001 / FR-002:
    Schema-Aware Criterion Validation

    Validation rules:
    - Unknown field: Return error with available_fields list
    - Type mismatch: Coerce string to target type or error
    - Empty criteria: Valid (returns empty results)

    Also applies legacy field mapping (FR-006) before validation.

    Args:
        entity_type: Entity type identifier (e.g., "unit").
        criterion: Dictionary of field -> value lookup criteria.

    Returns:
        CriterionValidationResult with validation status and details.

    Example:
        >>> result = validate_criterion_for_entity(
        ...     "unit",
        ...     {"phone": "+15551234567", "vertical": "dental"}
        ... )
        >>> result.is_valid
        True
        >>> result.normalized_criterion
        {"office_phone": "+15551234567", "vertical": "dental"}
    """
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    # Apply legacy field mapping first
    normalized = _apply_legacy_mapping(entity_type, criterion)

    # Get schema for entity type
    schema_registry = SchemaRegistry.get_instance()
    schema_key = to_pascal_case(entity_type)  # "unit" -> "Unit"

    try:
        schema = schema_registry.get_schema(schema_key)
    except SchemaNotFoundError:
        # Fall back to base schema if entity-specific not found
        schema = schema_registry.get_schema("*")

    # Get valid column names
    available_fields = schema.column_names()
    available_set = set(available_fields)

    # Check for unknown fields
    criterion_fields = set(normalized.keys())
    unknown_fields = list(criterion_fields - available_set)

    errors: list[str] = []

    if unknown_fields:
        errors.append(
            f"Unknown field(s) for {entity_type}: {sorted(unknown_fields)}. "
            f"Valid fields: {sorted(available_fields)}"
        )

    # Type coercion validation
    for field_name, value in normalized.items():
        if field_name in available_set:
            column_def = schema.get_column(field_name)
            if column_def is not None:
                coercion_error = _validate_field_type(
                    field_name, value, column_def.dtype
                )
                if coercion_error:
                    errors.append(coercion_error)

    return CriterionValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        unknown_fields=unknown_fields,
        available_fields=available_fields,
        normalized_criterion=normalized,
    )


def _normalize_field(
    field_name: str,
    entity_type: str,
    available_fields: set[str],
    _visited: set[str] | None = None,
) -> str:
    """Normalize a single field name using hierarchical alias resolution.

    Per TDD-dynamic-field-normalization:
    Implements 5-step resolution algorithm with recursion guard.

    Resolution order:
    1. Exact match: field_name in available_fields
    2. Prefix expansion: {entity_type}_{field_name}
    3. Prefix removal: strip {entity_type}_ from field_name
    4. Alias expansion: {alias}_{field_name} for each alias
    5. Alias decomposition: strip suffix, recurse to parent entity

    Args:
        field_name: The field name from the criterion (e.g., "phone", "email").
        entity_type: The entity type context (e.g., "contact", "unit").
        available_fields: Set of valid schema column names from SchemaRegistry.
        _visited: Internal set tracking visited entities to prevent infinite recursion.

    Returns:
        Normalized field name. Returns unchanged if no resolution found
        (validation will catch invalid fields downstream).

    Raises:
        No exceptions raised. Invalid fields pass through unchanged.
    """
    # 1. Recursion guard
    if _visited is None:
        _visited = set()
    if entity_type in _visited:
        return field_name
    _visited = _visited | {entity_type}

    # 2. Exact match
    if field_name in available_fields:
        return field_name

    # 3. Prefix expansion: {entity}_{field}
    prefixed = f"{entity_type}_{field_name}"
    if prefixed in available_fields:
        return prefixed

    # 4. Prefix removal: strip {entity}_
    prefix = f"{entity_type}_"
    if field_name.startswith(prefix):
        stripped = field_name[len(prefix) :]
        if stripped in available_fields:
            return stripped

    # 5. Alias resolution
    for alias in ENTITY_ALIASES.get(entity_type, []):
        # 5a. Direct alias expansion: {alias}_{field}
        alias_prefixed = f"{alias}_{field_name}"
        if alias_prefixed in available_fields:
            return alias_prefixed

        # 5b. Alias decomposition: recurse to parent
        if "_" in alias:
            parent = alias.rsplit("_", 1)[0]  # "business_unit" -> "business"
            result = _normalize_field(field_name, parent, available_fields, _visited)
            if result in available_fields:
                return result

    # 6. Fallback: return unchanged
    return field_name


def _apply_legacy_mapping(
    entity_type: str,
    criterion: dict[str, Any],
) -> dict[str, Any]:
    """Apply field normalization with hierarchical alias resolution.

    Per TDD-dynamic-field-normalization:
    Replaces static LEGACY_FIELD_MAPPING with dynamic algorithm.

    Args:
        entity_type: Entity type for context (e.g., "unit", "contact").
        criterion: Original criterion dict with field -> value pairs.

    Returns:
        New dict with fields normalized to schema column names.
    """
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    # Get available fields from schema
    schema_registry = SchemaRegistry.get_instance()
    schema_key = to_pascal_case(entity_type)
    try:
        schema = schema_registry.get_schema(schema_key)
        available_fields = set(schema.column_names())
    except SchemaNotFoundError:
        available_fields = set()

    # Normalize each field
    return {
        _normalize_field(field_name, entity_type, available_fields): value
        for field_name, value in criterion.items()
    }


def _validate_field_type(field_name: str, value: Any, dtype: str) -> str | None:
    """Validate and coerce value to target dtype.

    Args:
        field_name: Field name for error messages.
        value: Value to validate.
        dtype: Target Polars dtype string.

    Returns:
        Error message if invalid, None if valid.
    """
    # String types accept anything (coerce to string)
    if dtype in ("Utf8", "String"):
        return None

    # Integer types
    if dtype in ("Int64", "Int32"):
        try:
            int(value)
            return None
        except (ValueError, TypeError):
            return f"Field '{field_name}' expects integer, got: {type(value).__name__}"

    # Float types
    if dtype in ("Float64", "Decimal"):
        try:
            float(value)
            return None
        except (ValueError, TypeError):
            return f"Field '{field_name}' expects number, got: {type(value).__name__}"

    # Boolean
    if dtype == "Boolean":
        if isinstance(value, bool):
            return None
        if isinstance(value, str) and value.lower() in ("true", "false", "1", "0"):
            return None
        return f"Field '{field_name}' expects boolean, got: {value}"

    # Default: accept (be permissive for unknown types)
    return None


# --- Field Filtering ---


def filter_result_fields(
    result: dict[str, Any],
    requested_fields: list[str] | None,
    entity_type: str,
) -> dict[str, Any]:
    """Filter result to requested fields only with SchemaRegistry validation.

    Per TDD: Validates requested fields against SchemaRegistry schema.
    Always includes 'gid' field regardless of request.

    Args:
        result: Full result dict with all available fields
        requested_fields: List of field names to include (None = gid only)
        entity_type: Entity type for schema lookup (e.g., "unit")

    Returns:
        Filtered dict with only requested fields + gid.

    Raises:
        ValueError: If requested field not in schema (INVALID_FIELD error).
    """
    if not requested_fields:
        # Default: gid only
        return {"gid": result.get("gid")}

    # Validate fields against schema
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    registry = SchemaRegistry.get_instance()

    # Convert entity_type to schema key (e.g., "unit" -> "Unit")
    schema_key = to_pascal_case(entity_type)

    try:
        schema = registry.get_schema(schema_key)
        valid_fields = {col.name for col in schema.columns}
    except SchemaNotFoundError:
        # Fall back to base schema if entity-specific not found
        schema = registry.get_schema("*")
        valid_fields = {col.name for col in schema.columns}

    # Check for invalid fields
    invalid = set(requested_fields) - valid_fields - {"gid"}
    if invalid:
        raise ValueError(
            f"Invalid fields: {sorted(invalid)}. Available: {sorted(valid_fields)}"
        )

    # Always include gid
    fields_to_include = set(requested_fields) | {"gid"}

    return {k: v for k, v in result.items() if k in fields_to_include}


# --- Strategy Factory ---


def get_strategy(entity_type: str) -> UniversalResolutionStrategy | None:
    """Get resolution strategy for entity type.

    Returns a UniversalResolutionStrategy for any resolvable entity type.
    The strategy uses schema-driven resolution with DynamicIndex for O(1) lookups.

    Args:
        entity_type: Entity type identifier (e.g., "unit", "business", "offer")

    Returns:
        UniversalResolutionStrategy if entity is resolvable, None otherwise.

    Example:
        >>> strategy = get_strategy("unit")
        >>> if strategy:
        ...     results = await strategy.resolve(
        ...         criteria=[{"phone": "+15551234567", "vertical": "dental"}],
        ...         project_gid="1234567890",
        ...         client=client,
        ...     )
    """
    # Import here to avoid circular imports
    from autom8_asana.services.universal_strategy import get_universal_strategy

    # Check if entity is resolvable
    if not is_entity_resolvable(entity_type):
        return None

    return get_universal_strategy(entity_type)


# Self-register for SystemContext.reset_all()
from autom8_asana.core.system_context import register_reset  # noqa: E402

register_reset(EntityProjectRegistry.reset)

# Subscribe to SchemaRegistry reset to clear resolvable entities cache.
# This replaces the previous cross-boundary private API call where
# SchemaRegistry.reset() directly imported _clear_resolvable_cache.
from autom8_asana.dataframes.models.registry import SchemaRegistry  # noqa: E402

SchemaRegistry.on_reset(_clear_resolvable_cache)
