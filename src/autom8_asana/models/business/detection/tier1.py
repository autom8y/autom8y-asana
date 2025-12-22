"""Tier 1: Project membership detection.

Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: O(1) registry lookup, 100% accuracy.

This module provides deterministic entity type detection via project membership.
Tasks are identified by looking up their first project GID in the ProjectTypeRegistry.

Functions:
    detect_by_project_membership: Sync O(1) lookup, no API call
    detect_by_project_membership_async: Async variant with workspace discovery

Dependencies: types.py, config.py, registry.py
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_1,
    DetectionResult,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

__all__ = [
    "detect_by_project_membership",
    "detect_by_project_membership_async",
    "_detect_tier1_project_membership",
    "_detect_tier1_project_membership_async",
]

logger = logging.getLogger(__name__)


def _extract_project_gid(task: Task) -> str | None:
    """Extract project GID from task's first membership.

    Args:
        task: Task to extract project GID from.

    Returns:
        Project GID if found, None otherwise.
    """
    if not task.memberships:
        logger.debug(
            "No memberships on task for Tier 1 detection",
            extra={"task_gid": task.gid},
        )
        return None

    first_membership = task.memberships[0]
    project_data = first_membership.get("project")
    if not project_data:
        logger.debug(
            "No project in first membership for Tier 1 detection",
            extra={"task_gid": task.gid},
        )
        return None

    project_gid: str | None = project_data.get("gid")
    if not project_gid:
        logger.debug(
            "No project GID in membership for Tier 1 detection",
            extra={"task_gid": task.gid},
        )
        return None

    return project_gid


def _detect_tier1_project_membership(task: Task) -> DetectionResult | None:
    """Tier 1: Detect entity type by project membership.

    Per TDD-DETECTION/FR-DET-002: O(1) registry lookup, no API call.
    Per ADR-0101: Only ProjectTypeRegistry is used for entity type detection.

    This is the primary detection method. It looks up the task's first project
    membership in the ProjectTypeRegistry for deterministic type detection.

    Args:
        task: Task to detect type for.

    Returns:
        DetectionResult if project GID is registered, None otherwise.
    """
    from autom8_asana.models.business.registry import get_registry

    project_gid = _extract_project_gid(task)
    if not project_gid:
        return None

    # Registry lookup
    registry = get_registry()
    entity_type = registry.lookup(project_gid)

    if entity_type is None:
        logger.debug(
            "Project GID not in registry for Tier 1 detection",
            extra={"task_gid": task.gid, "project_gid": project_gid},
        )
        return None

    logger.debug(
        "Detected %s via project membership (Tier 1)",
        entity_type.name,
        extra={"task_gid": task.gid, "project_gid": project_gid, "tier": 1},
    )

    return DetectionResult(
        entity_type=entity_type,
        confidence=CONFIDENCE_TIER_1,
        tier_used=1,
        needs_healing=False,
        expected_project_gid=project_gid,
    )


def detect_by_project_membership(task: Task) -> DetectionResult | None:
    """Tier 1: Detect entity type by project membership.

    Per TDD-DETECTION/FR-DET-002: O(1) registry lookup, no API call.

    This is the primary detection method. It looks up the task's first project
    membership in the ProjectTypeRegistry for deterministic type detection.

    Args:
        task: Task to detect type for.

    Returns:
        DetectionResult if project GID is registered, None otherwise.

    Example:
        >>> result = detect_by_project_membership(task)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name} via project membership")
    """
    return _detect_tier1_project_membership(task)


async def _detect_tier1_project_membership_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Async Tier 1: Detect entity type with lazy workspace discovery.

    Per TDD-WORKSPACE-PROJECT-REGISTRY Phase 2: Async detection with lazy discovery.
    Per ADR-0109: Triggers discovery on first unregistered GID in async path.

    This function extends Tier 1 detection with dynamic pipeline project discovery.
    When a task's project is not in the static registry, it triggers workspace
    discovery to find and register pipeline projects (Sales, Onboarding, etc.).

    Flow:
    1. Extract project GID from task.memberships
    2. Use WorkspaceProjectRegistry.lookup_or_discover_async()
    3. If discovery finds a pipeline project, it registers with static registry
    4. Return DetectionResult if type found, None otherwise

    Args:
        task: Task to detect type for.
        client: AsanaClient for workspace discovery if needed.

    Returns:
        DetectionResult if project GID maps to an EntityType, None otherwise.

    Example:
        >>> result = await _detect_tier1_project_membership_async(task, client)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name} via async Tier 1")
    """
    from autom8_asana.models.business.registry import get_workspace_registry

    project_gid = _extract_project_gid(task)
    if not project_gid:
        return None

    # Use workspace registry for dynamic discovery
    workspace_registry = get_workspace_registry()
    entity_type = await workspace_registry.lookup_or_discover_async(
        project_gid,
        client,
    )

    if entity_type is None:
        logger.debug(
            "Project GID not found after async Tier 1 discovery",
            extra={"task_gid": task.gid, "project_gid": project_gid},
        )
        return None

    logger.debug(
        "Detected %s via async project membership with lazy discovery (Tier 1)",
        entity_type.name,
        extra={"task_gid": task.gid, "project_gid": project_gid, "tier": 1},
    )

    return DetectionResult(
        entity_type=entity_type,
        confidence=CONFIDENCE_TIER_1,
        tier_used=1,
        needs_healing=False,
        expected_project_gid=project_gid,
    )


async def detect_by_project_membership_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Async Tier 1: Detect entity type with lazy workspace discovery.

    Per TDD-WORKSPACE-PROJECT-REGISTRY Phase 2: Async detection with lazy discovery.

    Public wrapper for _detect_tier1_project_membership_async.

    Args:
        task: Task to detect type for.
        client: AsanaClient for workspace discovery if needed.

    Returns:
        DetectionResult if project GID maps to an EntityType, None otherwise.

    Example:
        >>> result = await detect_by_project_membership_async(task, client)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name} via async Tier 1")
    """
    return await _detect_tier1_project_membership_async(task, client)
