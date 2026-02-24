"""Section CRUD operations with integrated cache invalidation.

Per TDD-SERVICE-LAYER-001 Phase 2: Encapsulates section business logic
extracted from api/routes/sections.py. The service owns MutationEvent
construction and fire-and-forget invalidation.

Usage:
    service = SectionService(invalidator=mutation_invalidator)
    section = await service.create_section(client, name="New", project="gid")
    section = await service.update_section(client, gid="123", name="Renamed")

Note: This service does NOT modify route handlers. Route wiring
is Phase 3/4 work per the migration plan.
"""

from __future__ import annotations

from typing import Any

from autom8y_log import get_logger

from autom8_asana import AsanaClient
from autom8_asana.cache.integration.mutation_invalidator import MutationInvalidator
from autom8_asana.cache.models.mutation_event import (
    EntityKind,
    MutationEvent,
    MutationType,
)
from autom8_asana.services.errors import InvalidParameterError

logger = get_logger(__name__)


class SectionService:
    """Section CRUD operations with integrated cache invalidation.

    Encapsulates:
    - Asana SDK section client calls
    - MutationEvent construction from response data
    - Fire-and-forget invalidation via MutationInvalidator

    Dependencies are received via constructor injection per ADR-SLE-002.
    """

    def __init__(self, invalidator: MutationInvalidator) -> None:
        """Initialize with invalidation dependency.

        Args:
            invalidator: MutationInvalidator for cache invalidation.
        """
        self._invalidator = invalidator

    # --- Get ---

    async def get_section(
        self,
        client: AsanaClient,
        gid: str,
    ) -> dict[str, Any]:
        """Get section by GID.

        Args:
            client: Asana SDK client.
            gid: Asana section GID.

        Returns:
            Section data dict from Asana API.
        """
        return await client.sections.get_async(gid, raw=True)

    # --- Create (S1) ---

    async def create_section(
        self,
        client: AsanaClient,
        name: str,
        project: str,
    ) -> dict[str, Any]:
        """Create section in project and fire invalidation event.

        Args:
            client: Asana SDK client.
            name: Section name.
            project: Project GID to create section in.

        Returns:
            Created section data dict.
        """
        section = await client.sections.create_async(
            name=name,
            project=project,
            raw=True,
        )

        section_gid = section.get("gid", "") if isinstance(section, dict) else ""
        self._fire_invalidation(
            entity_gid=section_gid,
            mutation_type=MutationType.CREATE,
            project_gids=[project],
        )

        return section

    # --- Update (S2) ---

    async def update_section(
        self,
        client: AsanaClient,
        gid: str,
        name: str,
    ) -> dict[str, Any]:
        """Update section (rename) and fire invalidation event.

        Args:
            client: Asana SDK client.
            gid: Asana section GID.
            name: New section name.

        Returns:
            Updated section data dict.
        """
        section = await client.sections.update_async(gid, raw=True, name=name)

        # Extract project GID from response if available
        project_gids = self._extract_section_project_gids(section)

        self._fire_invalidation(
            entity_gid=gid,
            mutation_type=MutationType.UPDATE,
            project_gids=project_gids,
        )

        return section

    # --- Delete (S3) ---

    async def delete_section(
        self,
        client: AsanaClient,
        gid: str,
    ) -> None:
        """Delete section and fire invalidation event.

        Args:
            client: Asana SDK client.
            gid: Asana section GID.
        """
        await client.sections.delete_async(gid)  # type: ignore[attr-defined]

        # 204 No Content: no project GID available from response
        self._fire_invalidation(
            entity_gid=gid,
            mutation_type=MutationType.DELETE,
            project_gids=[],
        )

    # --- Add Task (S4) ---

    async def add_task(
        self,
        client: AsanaClient,
        section_gid: str,
        task_gid: str,
    ) -> None:
        """Add a task to a section.

        Args:
            client: Asana SDK client.
            section_gid: Section GID.
            task_gid: Task GID to add.
        """
        await client.sections.add_task_async(  # type: ignore[attr-defined]
            section_gid, task=task_gid
        )

        # section_gid field carries the task_gid per TDD convention
        self._invalidator.fire_and_forget(
            MutationEvent(
                entity_kind=EntityKind.SECTION,
                entity_gid=section_gid,
                mutation_type=MutationType.ADD_MEMBER,
                project_gids=[],
                section_gid=task_gid,
            )
        )

    # --- Reorder ---

    async def reorder(
        self,
        client: AsanaClient,
        gid: str,
        project_gid: str,
        *,
        before_section: str | None = None,
        after_section: str | None = None,
    ) -> None:
        """Reorder section within a project.

        Args:
            client: Asana SDK client.
            gid: Section GID to reorder.
            project_gid: Project GID containing the section.
            before_section: Section GID to insert before (optional).
            after_section: Section GID to insert after (optional).

        Raises:
            InvalidParameterError: Neither or both of before/after provided.
        """
        if before_section is None and after_section is None:
            raise InvalidParameterError(
                "Either 'before_section' or 'after_section' must be provided"
            )
        if before_section is not None and after_section is not None:
            raise InvalidParameterError(
                "Only one of 'before_section' or 'after_section' may be specified"
            )

        await client.sections.insert_section_async(  # type: ignore[attr-defined]
            project_gid,
            section=gid,
            before_section=before_section,
            after_section=after_section,
        )
        # Reorder does not affect cache (order is not cached)

    # --- Private Helpers ---

    @staticmethod
    def _extract_section_project_gids(
        section: dict[str, Any] | Any,
    ) -> list[str]:
        """Extract project GIDs from a section API response.

        Args:
            section: Section data from Asana API.

        Returns:
            List of project GIDs (may be empty).
        """
        if not isinstance(section, dict):
            return []
        project = section.get("project")
        if isinstance(project, dict) and project.get("gid"):
            return [project["gid"]]
        return []

    def _fire_invalidation(
        self,
        *,
        entity_gid: str,
        mutation_type: MutationType,
        project_gids: list[str],
    ) -> None:
        """Construct MutationEvent and fire invalidation.

        Args:
            entity_gid: GID of the mutated section.
            mutation_type: What operation was performed.
            project_gids: Affected project GIDs.
        """
        self._invalidator.fire_and_forget(
            MutationEvent(
                entity_kind=EntityKind.SECTION,
                entity_gid=entity_gid,
                mutation_type=mutation_type,
                project_gids=project_gids,
            )
        )


__all__ = ["SectionService"]
