"""Entity resolution service backed by B1 EntityRegistry.

Per TDD-SERVICE-LAYER-001: Consolidates the entity validation + project
lookup + bot PAT acquisition pattern currently duplicated across route
handlers into a single service method.

Usage:
    from autom8_asana.services.entity_service import EntityService

    service = EntityService(
        entity_registry=get_registry(),
        project_registry=EntityProjectRegistry.get_instance(),
    )
    ctx = service.validate_entity_type("unit")
    # ctx.entity_type == "unit"
    # ctx.project_gid == "1201081073731555"
    # ctx.descriptor == EntityDescriptor(...)
    # ctx.bot_pat == "<bot_pat>"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.services.entity_context import EntityContext
from autom8_asana.services.errors import (
    ServiceNotConfiguredError,
    UnknownEntityError,
)

if TYPE_CHECKING:
    from autom8_asana.core.entity_registry import EntityRegistry
    from autom8_asana.services.resolver import EntityProjectRegistry

logger = get_logger(__name__)


class EntityService:
    """Entity resolution service backed by B1 EntityRegistry.

    Consolidates the entity validation + project lookup + bot PAT
    acquisition pattern currently duplicated across route handlers.

    Thread Safety: Wraps singleton registries. Safe for concurrent use
    after construction.

    Attributes:
        _entity_registry: B1 EntityRegistry for entity metadata lookup.
        _project_registry: EntityProjectRegistry for project GID resolution.
    """

    def __init__(
        self,
        entity_registry: EntityRegistry,
        project_registry: EntityProjectRegistry,
    ) -> None:
        """Initialize with registry dependencies.

        Args:
            entity_registry: B1 EntityRegistry for entity metadata.
            project_registry: EntityProjectRegistry for project GID lookup.
        """
        self._entity_registry = entity_registry
        self._project_registry = project_registry

    @property
    def project_registry(self) -> EntityProjectRegistry:
        """Expose project registry for callers that need it directly.

        Used by query.py to pass entity_project_registry to
        QueryEngine.execute_rows() without accessing app.state.

        Returns:
            The EntityProjectRegistry instance held by this service.
        """
        return self._project_registry

    def validate_entity_type(self, entity_type: str) -> EntityContext:
        """Validate entity type and return full context.

        Performs the complete entity resolution sequence:
        1. Check entity is in the set of queryable/resolvable entities
        2. Require descriptor from B1 EntityRegistry
        3. Resolve project GID from EntityProjectRegistry
        4. Acquire bot PAT

        Args:
            entity_type: Entity type string (e.g., "unit", "offer").

        Returns:
            EntityContext with validated entity metadata.

        Raises:
            UnknownEntityError: Entity type not in resolvable set.
            ServiceNotConfiguredError: Project not configured or bot PAT missing.
        """
        queryable = self.get_queryable_entities()
        if entity_type not in queryable:
            raise UnknownEntityError(entity_type, sorted(queryable))

        descriptor = self._entity_registry.require(entity_type)
        project_gid = self._project_registry.get_project_gid(entity_type)

        if project_gid is None:
            raise ServiceNotConfiguredError(
                f"No project configured for entity type: {entity_type}"
            )

        bot_pat = self._acquire_bot_pat()

        logger.debug(
            "entity_context_resolved",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )

        return EntityContext(
            entity_type=entity_type,
            project_gid=project_gid,
            descriptor=descriptor,
            bot_pat=bot_pat,
        )

    def get_queryable_entities(self) -> set[str]:
        """Get entity types that support querying.

        An entity is queryable if it has both a schema registered
        in SchemaRegistry and a project registered in EntityProjectRegistry.

        Returns:
            Set of resolvable entity type strings.
        """
        from autom8_asana.services.resolver import get_resolvable_entities

        return get_resolvable_entities(
            project_registry=self._project_registry,
        )

    def _acquire_bot_pat(self) -> str:
        """Acquire bot PAT for Asana API calls.

        Returns:
            Bot PAT string.

        Raises:
            ServiceNotConfiguredError: Bot PAT not configured.
        """
        from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

        try:
            return get_bot_pat()
        except BotPATError as e:
            raise ServiceNotConfiguredError(f"Bot PAT not configured: {e}") from e


__all__ = ["EntityService"]
