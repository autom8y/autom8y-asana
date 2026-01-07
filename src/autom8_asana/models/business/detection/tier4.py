"""Tier 4: Structure inspection detection.

Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: Async structure inspection, ~90% accuracy.

This module provides entity type detection via subtask structure inspection.
When sync detection tiers fail, we can examine subtask names to infer parent type.

Functions:
    detect_by_structure_inspection: Async detection via subtask examination

Dependencies: types.py, config.py
"""

from __future__ import annotations

from autom8y_log import get_logger
from typing import TYPE_CHECKING

from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_4,
    DetectionResult,
    EntityType,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

__all__ = [
    "detect_by_structure_inspection",
]

logger = get_logger(__name__)

# Structure indicators for entity type detection
BUSINESS_INDICATORS: frozenset[str] = frozenset({"contacts", "units", "location"})
UNIT_INDICATORS: frozenset[str] = frozenset({"offers", "processes"})


async def detect_by_structure_inspection(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Tier 4: Detect entity type by subtask structure inspection.

    Per TDD-DETECTION/ADR-0094: Async detection via API call.

    This is the fallback when sync detection tiers fail. It fetches subtasks
    and examines their names to infer the parent entity type.

    - Business has holder subtasks: "contacts", "units", "location"
    - Unit has holder subtasks: "offers", "processes"

    Args:
        task: Task to detect type for.
        client: AsanaClient for API calls.

    Returns:
        DetectionResult if structure matches a known pattern, None otherwise.

    Example:
        >>> result = await detect_by_structure_inspection(task, client)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name} via structure")
    """
    from autom8_asana.models.business.registry import get_registry

    # Fetch subtasks to examine structure
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Business has holder subtasks
    if subtask_names & BUSINESS_INDICATORS:
        expected_gid = get_registry().get_primary_gid(EntityType.BUSINESS)

        logger.debug(
            "Detected Business via structure (Tier 4)",
            extra={
                "task_gid": task.gid,
                "subtask_names": list(subtask_names),
                "tier": 4,
            },
        )

        return DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=CONFIDENCE_TIER_4,
            tier_used=4,
            needs_healing=True,
            expected_project_gid=expected_gid,
        )

    # Unit has offer/process holder subtasks
    if subtask_names & UNIT_INDICATORS:
        expected_gid = get_registry().get_primary_gid(EntityType.UNIT)

        logger.debug(
            "Detected Unit via structure (Tier 4)",
            extra={
                "task_gid": task.gid,
                "subtask_names": list(subtask_names),
                "tier": 4,
            },
        )

        return DetectionResult(
            entity_type=EntityType.UNIT,
            confidence=CONFIDENCE_TIER_4,
            tier_used=4,
            needs_healing=True,
            expected_project_gid=expected_gid,
        )

    logger.debug(
        "No structure pattern match for Tier 4 detection",
        extra={"task_gid": task.gid, "subtask_names": list(subtask_names)},
    )

    return None
