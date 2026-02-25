"""Field definition classes for Business Model layer.

Per ADR-0054: CascadingFieldDef and InheritedFieldDef for field flow patterns.
Per FR-CASCADE-001 through FR-CASCADE-008: Cascading field requirements.
Per FR-INHERIT-001 through FR-INHERIT-004: Inherited field requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.models.task import Task


@dataclass(frozen=True)
class CascadingFieldDef:
    """Definition of a field that cascades from owner to descendants.

    Per ADR-0054: Supports multi-level cascading where any entity can
    declare cascading fields that propagate to its descendants.

    CRITICAL DESIGN CONSTRAINT (per ADR-0054):
    - allow_override=False is the DEFAULT
    - This means parent value ALWAYS overwrites descendant value
    - Only set allow_override=True when descendants should keep non-null values

    Attributes:
        name: Custom field name in Asana (must match exactly).
        target_types: Set of entity type names to cascade to, or None for all.
                     Uses string names to avoid circular imports.
        allow_override: If False (DEFAULT), always overwrite descendant.
                       If True, only overwrite if descendant value is None.
        cascade_on_change: If True, change detection includes this field.
        source_field: Model attribute to use if not a custom field (e.g., "name").
        transform: Optional function to transform value before cascading.

    Example:
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={"Unit", "Offer", "Process"},
            # allow_override=False is DEFAULT - no local overrides
        )

        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={"Offer"},
            allow_override=True,  # EXPLICIT OPT-IN: Offers can keep their value
        )
    """

    name: str
    target_types: set[str] | None = None  # None = all descendants
    allow_override: bool = False  # DEFAULT: NO override - parent always wins
    cascade_on_change: bool = True
    source_field: str | None = None
    transform: Callable[[Any], Any] | None = None

    def applies_to(self, entity: Task) -> bool:
        """Check if cascade applies to given entity.

        Args:
            entity: Entity to check.

        Returns:
            True if cascade should apply to this entity type.
        """
        if self.target_types is None:
            return True  # None means all descendants
        return type(entity).__name__ in self.target_types

    def get_value(self, source: Task) -> Any:
        """Get the value to cascade from source entity.

        Args:
            source: Source entity owning the field.

        Returns:
            Value to cascade (transformed if transform is set).
        """
        if self.source_field:
            # Get from model attribute (e.g., Task.name)
            value = getattr(source, self.source_field, None)
        else:
            # Get from custom field
            value = source.custom_fields_editor().get(self.name)

        if self.transform and value is not None:
            value = self.transform(value)

        return value

    def should_update_descendant(self, descendant: Task) -> bool:
        """Determine if descendant should be updated during cascade.

        Per ADR-0054:
            - allow_override=False (DEFAULT): Always update
            - allow_override=True: Only update if descendant has null value

        Args:
            descendant: Descendant entity to check.

        Returns:
            True if descendant should receive the cascaded value.
        """
        if not self.allow_override:
            return True  # DEFAULT: Always overwrite

        # allow_override=True: Check if descendant has a value
        current_value = descendant.custom_fields_editor().get(self.name)
        return current_value is None


@dataclass(frozen=True)
class InheritedFieldDef:
    """Definition of a field inherited from parent entities.

    Per FR-INHERIT-001 through FR-INHERIT-004: Supports parent chain resolution
    at access time, with optional local override.

    Attributes:
        name: Custom field name in Asana.
        inherit_from: List of parent type names in resolution order.
                     Uses string names to avoid circular imports.
        allow_override: Whether child can set own value.
        override_flag_field: Custom field name tracking override status.
                            Defaults to "{name} Override".
        default: Default value if no ancestor has value.

    Example:
        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],  # Resolution order
            allow_override=True,
        )

        MANAGER = InheritedFieldDef(
            name="Manager",
            inherit_from=["Unit"],
            allow_override=False,  # Always use parent's value
        )
    """

    name: str
    inherit_from: list[str] = field(default_factory=list)
    allow_override: bool = True
    override_flag_field: str | None = None
    default: Any = None

    @property
    def override_field_name(self) -> str:
        """Name of the override flag field.

        Returns:
            Custom field name for tracking override status.
        """
        return self.override_flag_field or f"{self.name} Override"

    def applies_to(self, entity: Task) -> bool:
        """Check if this inherited field applies to given entity.

        Args:
            entity: Entity to check.

        Returns:
            True if entity type is in the inheritance chain.
        """
        return type(entity).__name__ in self.inherit_from

    def is_overridden(self, entity: Task) -> bool:
        """Check if entity has local override for this field.

        Args:
            entity: Entity to check.

        Returns:
            True if entity has override flag set.
        """
        if not self.allow_override:
            return False

        override_value = entity.custom_fields_editor().get(self.override_field_name)
        return override_value in ("Yes", "yes", True, "true", "1")

    def resolve(
        self,
        entity: Task,
        parent_chain: list[Task],
    ) -> Any:
        """Resolve field value by walking parent chain.

        Args:
            entity: Entity requesting the value.
            parent_chain: List of parent entities in order.

        Returns:
            Resolved value from first parent with non-null value,
            or default if none found.
        """
        # Check local override first
        if self.allow_override and self.is_overridden(entity):
            local_value = entity.custom_fields_editor().get(self.name)
            if local_value is not None:
                return local_value

        # Walk parent chain
        for parent in parent_chain:
            parent_type = type(parent).__name__
            if parent_type in self.inherit_from:
                value = parent.custom_fields_editor().get(self.name)
                if value is not None:
                    return value

        return self.default


# =============================================================================
# Task opt_fields Constants (per PRD-CACHE-PERF-HYDRATION)
# =============================================================================

# Standard field set that satisfies all detection, traversal, and cascading use cases.
# Per FR-FIELDS-001: Single source of truth for opt_fields across the SDK.
# Per FR-FIELDS-003: Includes parent.gid for upward traversal.
# Per FR-FIELDS-004: Includes custom_fields.people_value for Owner cascading.
STANDARD_TASK_OPT_FIELDS: tuple[str, ...] = (
    # Core identification
    "name",
    "parent.gid",
    # Detection (Tier 1)
    "memberships.project.gid",
    "memberships.project.name",
    # Custom fields (cascading)
    "custom_fields",
    "custom_fields.name",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.display_value",
    "custom_fields.number_value",
    "custom_fields.text_value",
    "custom_fields.resource_subtype",
    "custom_fields.people_value",
)

# Minimal field set for detection-only operations (subset of standard).
# Per FR-DETECT-003: Smaller set for performance when custom_fields not needed.
DETECTION_OPT_FIELDS: tuple[str, ...] = (
    "name",
    "parent.gid",
    "memberships.project.gid",
    "memberships.project.name",
)


# =============================================================================
# Cascading Field Registry (TDD-CASCADING-FIELD-RESOLUTION-001)
# =============================================================================

# Type alias for registry entries: (owner_entity_class, cascading_field_def)
# Using TYPE_CHECKING to avoid circular imports at runtime
CascadingFieldEntry = tuple[type, CascadingFieldDef]

# Registry mapping normalized field names to their (owner_class, field_def) tuples.
# Populated lazily on first access to avoid circular import issues.
# Per TDD: Static registry is simpler, faster, and explicit (Option A).
_CASCADING_FIELD_REGISTRY: dict[str, CascadingFieldEntry] | None = None


def _normalize_field_name(name: str) -> str:
    """Normalize field name for case-insensitive lookup.

    Args:
        name: Field name to normalize.

    Returns:
        Lowercase field name with whitespace trimmed.
    """
    return name.lower().strip()


def _build_cascading_field_registry() -> dict[str, CascadingFieldEntry]:
    """Build the cascading field registry from descriptor-driven discovery.

    Per ARCH-descriptor-driven-auto-wiring section 3.5: Loops over descriptors
    where cascading_field_provider=True, resolves the model class via
    desc.get_model_class(), and extracts CascadingFields.all() entries.

    Import of get_registry is deferred inside the function body to avoid
    circular imports (core.entity_registry must not be imported at module
    scope from models/business/fields.py).

    Returns:
        Dict mapping normalized field names to (owner_class, field_def) tuples.
    """
    from autom8_asana.core.entity_registry import get_registry

    registry: dict[str, CascadingFieldEntry] = {}

    for desc in get_registry().all_descriptors():
        if not desc.cascading_field_provider:
            continue
        model_class = desc.get_model_class()
        if model_class is None:
            continue
        cascading = getattr(model_class, "CascadingFields", None)
        if cascading is None:
            import logging

            logging.getLogger(__name__).warning(
                f"cascading_provider_missing_inner_class: entity={desc.name} model={desc.model_class_path}"
            )
            continue
        for field_def in cascading.all():
            key = _normalize_field_name(field_def.name)
            registry[key] = (model_class, field_def)

    return registry


def get_cascading_field_registry() -> dict[str, CascadingFieldEntry]:
    """Get the cascading field registry, building it on first access.

    Returns:
        Dict mapping normalized field names to (owner_class, field_def) tuples.

    Example:
        >>> registry = get_cascading_field_registry()
        >>> owner, field_def = registry["office phone"]
        >>> owner.__name__
        'Business'
        >>> field_def.name
        'Office Phone'
    """
    global _CASCADING_FIELD_REGISTRY
    if _CASCADING_FIELD_REGISTRY is None:
        _CASCADING_FIELD_REGISTRY = _build_cascading_field_registry()
    return _CASCADING_FIELD_REGISTRY


def get_cascading_field(field_name: str) -> CascadingFieldEntry | None:
    """Look up cascading field definition by name.

    Performs case-insensitive lookup using normalized field names.

    Args:
        field_name: Custom field name to look up (e.g., "Office Phone").

    Returns:
        Tuple of (owner_entity_class, CascadingFieldDef) if found, None otherwise.

    Example:
        >>> result = get_cascading_field("Office Phone")
        >>> if result:
        ...     owner_class, field_def = result
        ...     print(f"{field_def.name} owned by {owner_class.__name__}")
        Office Phone owned by Business

        >>> # Case-insensitive lookup
        >>> get_cascading_field("office phone") is not None
        True
        >>> get_cascading_field("OFFICE PHONE") is not None
        True

        >>> # Unknown field returns None
        >>> get_cascading_field("Unknown Field") is None
        True
    """
    registry = get_cascading_field_registry()
    key = _normalize_field_name(field_name)
    return registry.get(key)
