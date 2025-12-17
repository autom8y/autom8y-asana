"""Entity type detection for business model hierarchy.

Per ADR-0068: Type Detection Strategy for Upward Traversal.

This module provides type detection capabilities for identifying entity types
during upward traversal through the business model hierarchy. It uses name-based
heuristics as the primary detection method with structure inspection as fallback.

Detection Algorithm:
1. Fast path: Name-based detection (zero API calls for holder types)
2. Slow path: Structure inspection via subtasks (1 API call for Business/Unit)

Example:
    # Sync detection by name (fast, no API call)
    entity_type = detect_by_name("Contacts")  # Returns EntityType.CONTACT_HOLDER

    # Async detection with fallback (may require API call)
    entity_type = await detect_entity_type_async(task, client)
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

__all__ = [
    "EntityType",
    "HOLDER_NAME_MAP",
    "detect_by_name",
    "detect_entity_type_async",
]

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Types of entities in the business model hierarchy.

    Per ADR-0068: Complete enumeration of all business model entity types.

    This enum covers:
    - Root entity: BUSINESS
    - Holder types: *_HOLDER variants for container tasks
    - Leaf entities: CONTACT, OFFER, PROCESS, LOCATION, HOURS
    - Composite: UNIT (has nested holders)
    - Fallback: UNKNOWN for unrecognized entities
    """

    # Root entity
    BUSINESS = "business"

    # Business-level holders
    CONTACT_HOLDER = "contact_holder"
    UNIT_HOLDER = "unit_holder"
    LOCATION_HOLDER = "location_holder"
    DNA_HOLDER = "dna_holder"
    RECONCILIATIONS_HOLDER = "reconciliations_holder"
    ASSET_EDIT_HOLDER = "asset_edit_holder"
    VIDEOGRAPHY_HOLDER = "videography_holder"

    # Unit-level holders
    OFFER_HOLDER = "offer_holder"
    PROCESS_HOLDER = "process_holder"

    # Composite entity (has nested holders)
    UNIT = "unit"

    # Leaf entities
    CONTACT = "contact"
    OFFER = "offer"
    PROCESS = "process"
    LOCATION = "location"
    HOURS = "hours"

    # Fallback
    UNKNOWN = "unknown"


# Per ADR-0068: Holder name detection map
# Maps lowercase task names to their EntityType
HOLDER_NAME_MAP: dict[str, EntityType] = {
    "contacts": EntityType.CONTACT_HOLDER,
    "units": EntityType.UNIT_HOLDER,
    "offers": EntityType.OFFER_HOLDER,
    "processes": EntityType.PROCESS_HOLDER,
    "location": EntityType.LOCATION_HOLDER,
    "dna": EntityType.DNA_HOLDER,
    "reconciliations": EntityType.RECONCILIATIONS_HOLDER,
    "asset edit": EntityType.ASSET_EDIT_HOLDER,
    "videography": EntityType.VIDEOGRAPHY_HOLDER,
}


def detect_by_name(name: str | None) -> EntityType | None:
    """Detect entity type by task name (sync, no API call).

    Per ADR-0068: Name-based detection is the fast path for holder types.
    This function performs case-insensitive matching against known holder names.

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
    if name is None:
        return None

    name_lower = name.lower().strip()

    if name_lower in HOLDER_NAME_MAP:
        return HOLDER_NAME_MAP[name_lower]

    return None


async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
) -> EntityType:
    """Detect entity type with structure fallback.

    Per ADR-0068: Uses name-based detection first (fast path), then falls back
    to structure inspection via subtasks (slow path) for Business/Unit detection.

    The structure fallback examines subtask names to determine entity type:
    - Business has holder subtasks: "contacts", "units", "location"
    - Unit has holder subtasks: "offers", "processes"

    Args:
        task: Task to detect type for.
        client: AsanaClient for API calls (used in fallback path).

    Returns:
        EntityType for the task. Returns UNKNOWN if type cannot be determined.

    Example:
        >>> task = await client.tasks.get_async(gid)
        >>> entity_type = await detect_entity_type_async(task, client)
        >>> if entity_type == EntityType.BUSINESS:
        ...     business = Business.model_validate(task.model_dump())
    """
    # Fast path: Name-based detection (works for holders)
    if detected := detect_by_name(task.name):
        return detected

    # Slow path: Structure inspection (needed for Business/Unit)
    # Fetch subtasks to examine structure
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Business has holder subtasks
    business_indicators = {"contacts", "units", "location"}
    if subtask_names & business_indicators:
        logger.debug(
            "Detected Business via structure",
            extra={"task_gid": task.gid, "subtask_names": subtask_names},
        )
        return EntityType.BUSINESS

    # Unit has offer/process holder subtasks
    unit_indicators = {"offers", "processes"}
    if subtask_names & unit_indicators:
        logger.debug(
            "Detected Unit via structure",
            extra={"task_gid": task.gid, "subtask_names": subtask_names},
        )
        return EntityType.UNIT

    # Log warning for ambiguous detection
    logger.warning(
        "Unable to determine entity type, returning UNKNOWN",
        extra={"task_gid": task.gid, "task_name": task.name},
    )

    return EntityType.UNKNOWN
