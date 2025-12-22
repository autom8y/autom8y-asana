"""Tier 3: Parent inference detection.

Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: Parent-based detection, ~80% accuracy.

This module provides entity type detection via parent type inference.
When the parent's type is known, child type can be inferred from PARENT_CHILD_MAP.

Functions:
    detect_by_parent_inference: Infer child type from parent type

Dependencies: types.py, config.py
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from autom8_asana.models.business.detection.config import PARENT_CHILD_MAP
from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_3,
    DetectionResult,
    EntityType,
)

if TYPE_CHECKING:
    from autom8_asana.models.task import Task

__all__ = [
    "detect_by_parent_inference",
]

logger = logging.getLogger(__name__)


def detect_by_parent_inference(
    task: Task, parent_type: EntityType
) -> DetectionResult | None:
    """Tier 3: Detect entity type by parent type inference.

    Per TDD-DETECTION: Infer child type from known parent type.

    This is used when we know the parent's type and can infer the child's type.
    For example, children of a CONTACT_HOLDER are CONTACT entities.

    Args:
        task: Task to detect type for (used for expected_project_gid lookup).
        parent_type: Known parent EntityType.

    Returns:
        DetectionResult if parent type has a known child mapping, None otherwise.

    Example:
        >>> result = detect_by_parent_inference(task, EntityType.CONTACT_HOLDER)
        >>> result.entity_type  # EntityType.CONTACT
    """
    from autom8_asana.models.business.registry import get_registry

    inferred_type = PARENT_CHILD_MAP.get(parent_type)
    if inferred_type is None:
        logger.debug(
            "No child type inference rule for parent type",
            extra={"task_gid": task.gid, "parent_type": parent_type.name},
        )
        return None

    expected_gid = get_registry().get_primary_gid(inferred_type)

    logger.debug(
        "Detected %s via parent inference from %s (Tier 3)",
        inferred_type.name,
        parent_type.name,
        extra={"task_gid": task.gid, "parent_type": parent_type.name, "tier": 3},
    )

    return DetectionResult(
        entity_type=inferred_type,
        confidence=CONFIDENCE_TIER_3,
        tier_used=3,
        needs_healing=True,
        expected_project_gid=expected_gid,
    )
