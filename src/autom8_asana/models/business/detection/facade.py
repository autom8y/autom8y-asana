"""Detection facade - main orchestration functions.

Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: Central orchestration for tiered detection.

This module provides the main detection entry points that coordinate the tier chain:
- detect_entity_type(): Sync detection (Tiers 1-3, no API)
- detect_entity_type_async(): Async detection (Tiers 1-5, optional API)
- identify_holder_type(): Holder identification with fallback

The facade orchestrates tiers but contains no tier-specific logic.

Dependencies: types.py, config.py, tier1.py, tier2.py, tier3.py, tier4.py
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING

from autom8_asana.models.business.detection.config import (
    HOLDER_NAME_MAP,
    get_holder_attr,
)
from autom8_asana.models.business.detection.tier1 import (
    _detect_tier1_project_membership_async,
    detect_by_project_membership,
)
from autom8_asana.models.business.detection.tier2 import (
    _detect_by_name_pattern,
)
from autom8_asana.models.business.detection.tier3 import (
    detect_by_parent_inference,
)
from autom8_asana.models.business.detection.tier4 import (
    detect_by_structure_inspection,
)
from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_5,
    DetectionResult,
    EntityType,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

__all__ = [
    "detect_by_name",
    "detect_by_project",
    "detect_by_parent",
    "detect_by_structure_async",
    "detect_entity_type",
    "detect_entity_type_async",
    "identify_holder_type",
    "_matches_holder_pattern",
]

logger = logging.getLogger(__name__)


# --- Legacy Wrapper Functions ---


def detect_by_name(name: str | None) -> EntityType | None:
    """Detect entity type by task name (sync, no API call).

    .. deprecated::
        Use :func:`detect_entity_type` instead for full detection chain.

    Per ADR-0068: Legacy name-based detection using exact match.
    This function performs case-insensitive exact matching against known holder names.

    Business and Unit cannot be detected by name alone since they have
    variable names (e.g., "Acme Corp", "Premium Package").

    Args:
        name: Task name to check. May be None.

    Returns:
        EntityType if name matches a known holder pattern, None otherwise.

    Example:
        >>> detect_by_name("Contacts")
        EntityType.CONTACT_HOLDER
        >>> detect_by_name("My Business")
        None  # Business names are variable
        >>> detect_by_name(None)
        None
    """
    warnings.warn(
        "detect_by_name() is deprecated. Use detect_entity_type() instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if name is None:
        return None

    name_lower = name.lower().strip()

    if name_lower in HOLDER_NAME_MAP:
        return HOLDER_NAME_MAP[name_lower]

    return None


def detect_by_project(task: Task) -> DetectionResult | None:
    """Tier 1: Detect entity type by project membership.

    Per TDD-DETECTION/FR-DET-002: O(1) registry lookup, no API call.

    This is the primary detection method. It looks up the task's first project
    membership in the ProjectTypeRegistry for deterministic type detection.

    Args:
        task: Task to detect type for.

    Returns:
        DetectionResult if project GID is registered, None otherwise.

    Example:
        >>> result = detect_by_project(task)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name} via project membership")
    """
    return detect_by_project_membership(task)


def detect_by_parent(task: Task, parent_type: EntityType) -> DetectionResult | None:
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
        >>> result = detect_by_parent(task, EntityType.CONTACT_HOLDER)
        >>> result.entity_type  # EntityType.CONTACT
    """
    return detect_by_parent_inference(task, parent_type)


async def detect_by_structure_async(
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
    """
    return await detect_by_structure_inspection(task, client)


# --- Tier 5: Unknown Fallback ---


def _make_unknown_result(task: Task) -> DetectionResult:
    """Create Tier 5 UNKNOWN result.

    Per TDD-DETECTION: Fallback when all detection tiers fail.

    Args:
        task: Task that could not be detected (for logging).

    Returns:
        DetectionResult with UNKNOWN type and needs_healing=True.
    """
    logger.warning(
        "Unable to detect type for task %s (Tier 5 fallback)",
        task.gid,
        extra={"task_gid": task.gid, "task_name": task.name},
    )

    return DetectionResult(
        entity_type=EntityType.UNKNOWN,
        confidence=CONFIDENCE_TIER_5,
        tier_used=5,
        needs_healing=True,
        expected_project_gid=None,
    )


# --- Unified Detection Functions ---


def detect_entity_type(
    task: Task,
    parent_type: EntityType | None = None,
) -> DetectionResult:
    """Synchronous entity type detection (Tiers 1-3).

    Per TDD-DETECTION/FR-DET-007: Synchronous function for zero-API-call detection.

    Executes tiers in order, returning on first success:
    1. Project membership lookup (O(1), no API)
    2. Name pattern matching (string ops, no API)
    3. Parent type inference (logic only, no API)

    If all tiers fail, returns UNKNOWN with needs_healing=True.

    Args:
        task: Task to detect type for.
        parent_type: Known parent type for Tier 3 inference.

    Returns:
        DetectionResult with detected type and metadata.

    Example:
        >>> result = detect_entity_type(task)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name}")
        >>> if result.is_deterministic:
        ...     print("Detected via project membership (Tier 1)")
    """
    # Tier 1: Project membership
    result = detect_by_project_membership(task)
    if result:
        return result

    # Tier 2: Name patterns
    result = _detect_by_name_pattern(task)
    if result:
        return result

    # Tier 3: Parent inference
    if parent_type:
        result = detect_by_parent_inference(task, parent_type)
        if result:
            return result

    # Tier 5: Unknown (skip Tier 4 in sync path)
    return _make_unknown_result(task)


async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Asynchronous entity type detection (Tiers 1-5).

    Per TDD-DETECTION/FR-DET-008: Async function with optional Tier 4.
    Per TDD-WORKSPACE-PROJECT-REGISTRY: Async Tier 1 with lazy discovery FIRST.
    Per ADR-0109: Discovery triggered on first unregistered GID.

    Detection order:
    1. Async Tier 1: Project membership with lazy workspace discovery
    2-3. Sync tiers: Name patterns, parent inference (no API)
    4. Structure inspection (requires API call, disabled by default)
    5. UNKNOWN fallback

    Args:
        task: Task to detect type for.
        client: AsanaClient for Tier 1 discovery and Tier 4 API calls.
        parent_type: Known parent type for Tier 3 inference.
        allow_structure_inspection: Enable Tier 4 (default: False).

    Returns:
        DetectionResult with detected type and metadata.

    Example:
        >>> # Fast path: async Tier 1 with discovery, then sync tiers
        >>> result = await detect_entity_type_async(task, client)

        >>> # Full detection with structure inspection
        >>> result = await detect_entity_type_async(
        ...     task, client, allow_structure_inspection=True
        ... )
    """
    # NEW: Async Tier 1 with lazy workspace discovery (before sync tiers)
    # Per ADR-0109: Discovery triggers on first unregistered GID
    async_tier1_result = await _detect_tier1_project_membership_async(task, client)
    if async_tier1_result:
        return async_tier1_result

    # Tiers 2-3 (sync) - skip sync Tier 1 since async already handled it
    # Note: We call detect_entity_type which internally does Tier 1 again,
    # but it will hit the static registry (now possibly populated by discovery)
    result = detect_entity_type(task, parent_type)

    # If we found a type (not UNKNOWN), return it
    if result:
        return result

    # Tier 4 (if enabled)
    if allow_structure_inspection:
        tier4_result = await detect_by_structure_inspection(task, client)
        if tier4_result:
            return tier4_result

    # Tier 5: Unknown (already returned by detect_entity_type)
    return result


# --- Holder Identification ---


def identify_holder_type(
    task: Task,
    holder_key_map: dict[str, tuple[str, str]],
    *,
    filter_to_map: bool = False,
) -> str | None:
    """Identify which holder type a task is.

    Per TDD-SPRINT-1 Phase 2: Extracted utility for holder identification.
    Per ADR-0119: Consolidates Business._identify_holder and Unit._identify_holder.

    Uses detection system first (Tier 1: project membership, Tier 2: name patterns),
    falls back to legacy HOLDER_KEY_MAP matching with logged warning.

    Args:
        task: Task to identify.
        holder_key_map: Map of holder_key -> (name_pattern, emoji).
            Used for fallback matching when detection fails.
        filter_to_map: If True, only return holder keys present in holder_key_map.
            Used by Unit to filter to Unit-level holders (offer_holder, process_holder).
            If False, returns any detected holder type.

    Returns:
        Holder key name (e.g., "contact_holder") or None if not a holder.

    Example:
        >>> holder_key = identify_holder_type(
        ...     task,
        ...     Business.HOLDER_KEY_MAP,
        ...     filter_to_map=False,
        ... )
        >>> if holder_key:
        ...     print(f"Detected holder: {holder_key}")
    """
    # Try detection system first (Tier 1: project membership, Tier 2: name patterns)
    result = detect_entity_type(task)

    if result and result.entity_type.name.endswith("_HOLDER"):
        # Detection succeeded - map EntityType to holder key
        holder_attr = get_holder_attr(result.entity_type)
        if holder_attr:
            # Convert "_contact_holder" to "contact_holder"
            holder_key = holder_attr.lstrip("_")
            # Filter to map keys if requested (Unit-level holders only)
            if filter_to_map and holder_key not in holder_key_map:
                return None
            return holder_key

    # Fallback to legacy HOLDER_KEY_MAP matching
    for key, (name_pattern, emoji) in holder_key_map.items():
        if _matches_holder_pattern(task, name_pattern, emoji):
            logger.warning(
                "Detection fallback: identified %s via HOLDER_KEY_MAP for task '%s' (gid=%s)",
                key,
                task.name,
                task.gid,
                extra={
                    "holder_key": key,
                    "task_name": task.name,
                    "task_gid": task.gid,
                    "fallback": "HOLDER_KEY_MAP",
                },
            )
            return key
    return None


def _matches_holder_pattern(task: Task, name_pattern: str, emoji: str) -> bool:
    """Check if task matches a holder definition.

    Per TDD-SPRINT-1 Phase 2: Extracted from Business._matches_holder.

    Uses suffix/contains matching for flexibility:
    - Exact match: "Contacts" == "contacts"
    - Suffix match: "My Contacts" ends with "contacts"
    - Contains match: "All Contacts Here" contains "contacts"

    Args:
        task: Task to check.
        name_pattern: Expected task name or pattern.
        emoji: Expected custom emoji name (currently unused).

    Returns:
        True if task matches holder pattern.
    """
    if not task.name:
        return False

    task_name_lower = task.name.lower()
    pattern_lower = name_pattern.lower()

    # Check exact match first
    if task_name_lower == pattern_lower:
        return True

    # Check suffix match (e.g., "My Contacts" ends with "contacts")
    if task_name_lower.endswith(pattern_lower):
        return True

    # Check contains match (e.g., "All Contacts Here" contains "contacts")
    if pattern_lower in task_name_lower:
        return True

    # Fall back to emoji (not currently implemented in Task model)
    # Would check task.custom_emoji.name == emoji if available
    return False
