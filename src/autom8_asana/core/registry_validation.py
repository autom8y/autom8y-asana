"""Cross-registry consistency validation.

Per QW-4 (ARCH-REVIEW-1 Section 3.1): Three registries (EntityRegistry,
ProjectTypeRegistry, EntityProjectRegistry) are populated independently
with no cross-validation. This module provides a startup validation step
callable from both api/lifespan.py and Lambda handler bootstrap.

Validates that every EntityDescriptor with a primary_project_gid has
corresponding entries in the other registries, preventing silent divergence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autom8y_log import get_logger

logger = get_logger(__name__)


@dataclass
class RegistryValidationResult:
    """Result of cross-registry consistency check.

    Attributes:
        errors: Critical mismatches that indicate broken configuration.
        warnings: Non-critical gaps (e.g., entity without project in a
            registry that may not yet be populated).
    """

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if no errors were found."""
        return len(self.errors) == 0


def validate_cross_registry_consistency(
    *,
    check_project_type_registry: bool = True,
    check_entity_project_registry: bool = True,
) -> RegistryValidationResult:
    """Validate consistency across EntityRegistry, ProjectTypeRegistry, and EntityProjectRegistry.

    Checks that every EntityDescriptor with a primary_project_gid has
    corresponding entries in the other registries. Defers imports to avoid
    circular dependency issues at module load time.

    Args:
        check_project_type_registry: Whether to validate against
            ProjectTypeRegistry. True for both API and Lambda paths.
        check_entity_project_registry: Whether to validate against
            EntityProjectRegistry. Set False for Lambda bootstrap where
            EntityProjectRegistry is not populated.

    Returns:
        RegistryValidationResult with any errors and warnings found.
    """
    from autom8_asana.core.entity_registry import get_registry

    result = RegistryValidationResult()
    entity_registry = get_registry()

    if check_project_type_registry:
        _check_project_type_registry(entity_registry, result)

    if check_entity_project_registry:
        _check_entity_project_registry(entity_registry, result)

    # Log summary
    if result.ok and not result.warnings:
        logger.info(
            "cross_registry_validation_passed",
            extra={
                "checked_project_type": check_project_type_registry,
                "checked_entity_project": check_entity_project_registry,
            },
        )
    else:
        logger.warning(
            "cross_registry_validation_issues",
            extra={
                "error_count": len(result.errors),
                "warning_count": len(result.warnings),
                "errors": result.errors,
                "warnings": result.warnings,
            },
        )

    return result


def _check_project_type_registry(
    entity_registry: object,
    result: RegistryValidationResult,
) -> None:
    """Check EntityRegistry descriptors against ProjectTypeRegistry.

    Every descriptor with both primary_project_gid and entity_type should
    have a matching entry in ProjectTypeRegistry.
    """
    from autom8_asana.models.business.registry import (
        get_registry as get_project_type_registry,
    )

    pt_registry = get_project_type_registry()

    for desc in entity_registry.all_descriptors():  # type: ignore[union-attr]
        if desc.primary_project_gid is None or desc.entity_type is None:
            continue

        looked_up = pt_registry.lookup(desc.primary_project_gid)

        if looked_up is None:
            result.errors.append(
                f"EntityDescriptor '{desc.name}' has primary_project_gid "
                f"'{desc.primary_project_gid}' but ProjectTypeRegistry has no "
                f"entry for this GID"
            )
        elif looked_up != desc.entity_type:
            result.errors.append(
                f"EntityDescriptor '{desc.name}' has entity_type "
                f"{desc.entity_type!r} but ProjectTypeRegistry maps GID "
                f"'{desc.primary_project_gid}' to {looked_up!r}"
            )


def _check_entity_project_registry(
    entity_registry: object,
    result: RegistryValidationResult,
) -> None:
    """Check EntityRegistry descriptors against EntityProjectRegistry.

    Every descriptor with a primary_project_gid should have a matching
    entry in EntityProjectRegistry (populated during API startup discovery).
    """
    from autom8_asana.services.resolver import EntityProjectRegistry

    ep_registry = EntityProjectRegistry.get_instance()

    if not ep_registry.is_ready():
        result.warnings.append(
            "EntityProjectRegistry is not yet initialized; skipping cross-validation"
        )
        return

    for desc in entity_registry.all_descriptors():  # type: ignore[union-attr]
        if desc.primary_project_gid is None:
            continue

        config = ep_registry.get_config(desc.name)

        if config is None:
            # Not all entities are registered in EntityProjectRegistry
            # (only those discovered via workspace). This is a warning,
            # not an error, since EntityProjectRegistry is populated
            # dynamically from workspace discovery.
            result.warnings.append(
                f"EntityDescriptor '{desc.name}' has primary_project_gid "
                f"'{desc.primary_project_gid}' but EntityProjectRegistry "
                f"has no entry for entity type '{desc.name}'"
            )
        elif config.project_gid != desc.primary_project_gid:
            result.errors.append(
                f"EntityDescriptor '{desc.name}' has primary_project_gid "
                f"'{desc.primary_project_gid}' but EntityProjectRegistry "
                f"maps it to project_gid '{config.project_gid}'"
            )
