"""Section name-to-GID resolution for workflow section-targeted fetch.

Shared helper used by workflow enumeration methods to resolve section names
to GIDs via the SectionsClient (30-min cached).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.clients.sections import SectionsClient

logger = get_logger(__name__)


async def resolve_section_gids(
    sections_client: SectionsClient,
    project_gid: str,
    target_names: frozenset[str] | set[str],
) -> dict[str, str]:
    """Resolve section names to GIDs for a project.

    Fetches the project's section list via SectionsClient (cached, 30-min TTL),
    matches target names case-insensitively, and returns a mapping of
    lowercase section name -> section GID.

    Missing sections are logged at WARNING level but do not raise.

    Args:
        sections_client: Sections API client (with cache).
        project_gid: Asana project GID to enumerate sections for.
        target_names: Set of section names to resolve (matched case-insensitively).

    Returns:
        Dict mapping lowercase section name -> section GID.
        Empty dict if no target names matched.

    Raises:
        Exception: Propagates any SectionsClient error (network, 5xx, timeout).
            Callers must handle this for fallback.
    """
    sections = await sections_client.list_for_project_async(project_gid).collect()

    lookup: dict[str, str] = {}
    for section in sections:
        if section.name:
            lookup[section.name.lower()] = section.gid

    resolved: dict[str, str] = {}
    for name in target_names:
        key = name.lower()
        if key in lookup:
            resolved[key] = lookup[key]
        else:
            logger.warning(
                "section_resolution_miss",
                project_gid=project_gid,
                missing_name=name,
            )

    return resolved
