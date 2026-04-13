"""EntityWriteRegistry -- auto-discovers writable entity types at startup.

Per TDD-ENTITY-WRITE-API Section 3.1:
    Introspects entity model classes for CustomFieldDescriptor properties to build
    a descriptor-name-to-display-name index used for dual field resolution.

Per ADR-EW-002:
    Separate registry overlaying EntityRegistry. Does not modify EntityRegistry or
    EntityProjectRegistry. Additive only.

Thread Safety:
    Immutable after construction. Built once at startup, read-many at runtime.

Usage:
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.resolution.write_registry import EntityWriteRegistry

    write_registry = EntityWriteRegistry(get_registry())
    info = write_registry.get("offer")
    if info:
        print(info.descriptor_index)  # {"weekly_ad_spend": "Weekly Ad Spend", ...}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.core.entity_registry import EntityRegistry

logger = get_logger(__name__)


# Known Asana core fields accepted in the `fields` dict.
# These map directly to top-level keys in the Asana PUT /tasks/{gid} body.
CORE_FIELD_NAMES: frozenset[str] = frozenset({"name", "assignee", "due_on", "completed", "notes"})


@dataclass(frozen=True, slots=True)
class WritableEntityInfo:
    """Write-specific metadata for an entity type.

    Attributes:
        entity_type: Canonical snake_case name.
        model_class: The entity model class (e.g., Offer).
        project_gid: Asana project GID from EntityRegistry.
        descriptor_index: Maps snake_case descriptor name -> Asana display name.
            Example: {"weekly_ad_spend": "Weekly Ad Spend", "mrr": "MRR"}
        core_fields: Set of Asana core field names writable on this type.
    """

    entity_type: str
    model_class: type
    project_gid: str
    descriptor_index: dict[str, str]  # snake_case -> "Display Name"
    core_fields: frozenset[str]


class EntityWriteRegistry:
    """Auto-discovers writable entities from model descriptors.

    Built once at startup. Provides O(1) lookup by entity type.

    Thread Safety: Immutable after construction.
    """

    def __init__(self, entity_registry: EntityRegistry) -> None:
        self._by_type: dict[str, WritableEntityInfo] = {}
        self._discover(entity_registry)

    def _discover(self, entity_registry: EntityRegistry) -> None:
        """Introspect entity models for CustomFieldDescriptor properties.

        For each EntityDescriptor with a model_class_path, lazily resolve the
        class and scan its MRO for CustomFieldDescriptor instances. Any model
        with at least one CustomFieldDescriptor is registered as writable.

        Lazy import of CustomFieldDescriptor avoids circular imports.
        """
        from autom8_asana.models.business.descriptors import CustomFieldDescriptor

        for desc in entity_registry.all_descriptors():
            if desc.category.value == "holder":
                continue  # Holders are not writable targets

            model_class = desc.get_model_class()
            if model_class is None:
                continue

            # Scan all attributes on the class for descriptors
            descriptor_index: dict[str, str] = {}
            for attr_name in dir(model_class):
                try:
                    attr = getattr(model_class, attr_name)
                except (AttributeError, TypeError):
                    continue
                if isinstance(attr, CustomFieldDescriptor) and attr.field_name:
                    descriptor_index[attr.public_name] = attr.field_name

            if not descriptor_index:
                continue  # No custom fields = not writable

            project_gid = desc.primary_project_gid
            if project_gid is None:
                continue  # No project = can't validate membership

            self._by_type[desc.name] = WritableEntityInfo(
                entity_type=desc.name,
                model_class=model_class,
                project_gid=project_gid,
                descriptor_index=descriptor_index,
                core_fields=CORE_FIELD_NAMES,
            )

            logger.debug(
                "write_registry_discovered",
                entity_type=desc.name,
                descriptor_count=len(descriptor_index),
            )

    def get(self, entity_type: str) -> WritableEntityInfo | None:
        """O(1) lookup by entity type name."""
        return self._by_type.get(entity_type)

    def is_writable(self, entity_type: str) -> bool:
        """Check if an entity type is registered as writable."""
        return entity_type in self._by_type

    def writable_types(self) -> list[str]:
        """Sorted list of all writable entity type names."""
        return sorted(self._by_type.keys())
