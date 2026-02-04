"""EntityContext: validated entity context for service operations.

Per TDD-SERVICE-LAYER-001: EntityContext is a frozen dataclass that
replaces the 15-line entity resolution pattern duplicated across route
handlers. It carries the validated entity type, project GID, B1
EntityDescriptor, and bot PAT needed for Asana API calls.

Services that need entity context accept it as a parameter rather
than resolving it themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.core.entity_registry import EntityDescriptor


@dataclass(frozen=True, slots=True)
class EntityContext:
    """Validated entity context for service operations.

    Created by EntityService.validate_entity_type(). Immutable
    for thread safety and to prevent accidental mutation.

    Attributes:
        entity_type: Canonical snake_case entity identifier (e.g., "unit").
        project_gid: Asana project GID for this entity type.
        descriptor: B1 EntityDescriptor with full entity metadata.
        bot_pat: Bot PAT for Asana API calls.
    """

    entity_type: str
    project_gid: str
    descriptor: EntityDescriptor
    bot_pat: str


__all__ = ["EntityContext"]
