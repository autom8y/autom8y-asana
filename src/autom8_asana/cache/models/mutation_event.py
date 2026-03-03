"""Mutation event types for REST cache invalidation.

Per TDD-CACHE-INVALIDATION-001: Dataclass describing what was mutated
(entity type, GID, operation, project context) for cache invalidation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MutationType(StrEnum):
    """Type of mutation operation."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"  # Section move (affects two sections)
    ADD_MEMBER = "add"  # Add to project/section
    REMOVE_MEMBER = "remove"  # Remove from project/section


class EntityKind(StrEnum):
    """Kind of entity being mutated."""

    TASK = "task"
    SECTION = "section"
    PROJECT = "project"  # Phase 2


@dataclass(frozen=True)
class MutationEvent:
    """Describes a mutation that requires cache invalidation.

    Per TDD-CACHE-INVALIDATION-001: Frozen dataclass carrying the
    entity kind, GID, operation type, and project context needed
    to determine which cache tiers to invalidate.

    Attributes:
        entity_kind: What was mutated (task, section, project).
        entity_gid: GID of the mutated entity.
        mutation_type: What operation was performed.
        project_gids: Project contexts affected (if known from request).
        section_gid: Section context (for section moves, add-to-section).
        source_section_gid: Source section (for section moves only).
    """

    entity_kind: EntityKind
    entity_gid: str
    mutation_type: MutationType
    project_gids: list[str] = field(default_factory=list)
    section_gid: str | None = None
    source_section_gid: str | None = None


def extract_project_gids(task_data: dict[str, Any] | None) -> list[str]:
    """Extract project GIDs from an Asana task response.

    Per ADR-002: Extracts from API response, not a reverse index.
    Looks for project membership in standard Asana response fields:
    - task.projects[].gid (common in full task responses)
    - task.memberships[].project.gid (SaveSession entity format)

    Args:
        task_data: Task dict from Asana API response, or None.

    Returns:
        List of project GIDs (may be empty if not available).
    """
    if not task_data:
        return []

    gids: list[str] = []

    # Try projects array (Asana REST response format)
    projects = task_data.get("projects")
    if projects and isinstance(projects, list):
        for p in projects:
            if isinstance(p, dict) and p.get("gid"):
                gids.append(p["gid"])

    # Try memberships array (entity/SaveSession format)
    if not gids:
        memberships = task_data.get("memberships")
        if memberships and isinstance(memberships, list):
            for m in memberships:
                if isinstance(m, dict):
                    project = m.get("project", {})
                    if isinstance(project, dict) and project.get("gid"):
                        gids.append(project["gid"])

    return gids
