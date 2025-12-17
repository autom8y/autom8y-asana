"""Field definition classes for Business Model layer.

Per ADR-0054: CascadingFieldDef and InheritedFieldDef for field flow patterns.
Per FR-CASCADE-001 through FR-CASCADE-008: Cascading field requirements.
Per FR-INHERIT-001 through FR-INHERIT-004: Inherited field requirements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
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
            value = source.get_custom_fields().get(self.name)

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
        current_value = descendant.get_custom_fields().get(self.name)
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

        override_value = entity.get_custom_fields().get(self.override_field_name)
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
            local_value = entity.get_custom_fields().get(self.name)
            if local_value is not None:
                return local_value

        # Walk parent chain
        for parent in parent_chain:
            parent_type = type(parent).__name__
            if parent_type in self.inherit_from:
                value = parent.get_custom_fields().get(self.name)
                if value is not None:
                    return value

        return self.default
