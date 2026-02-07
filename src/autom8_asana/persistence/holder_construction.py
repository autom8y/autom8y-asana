"""Holder entity construction and detection for write-path auto-creation.

Per TDD-GAP-01 Section 3.3, 3.4, 5: Pure construction function and async
detection function for the ENSURE_HOLDERS pipeline phase.

This module provides:
- HOLDER_CLASS_MAP: Registry mapping holder_key to holder class (9 entries).
- construct_holder(): Pure function building typed holder entities.
- detect_existing_holders(): Async function checking Asana API for existing holders.

The detection function reuses identify_holder_type from the detection facade
to guarantee consistency between read and write paths (FR-001).

The construction function uses HOLDER_KEY_MAP metadata to determine:
- Holder class (ContactHolder, UnitHolder, etc.)
- Name (conventional name from the tuple, no emoji in name)
- Parent reference (NameGid with real or temp GID)
- Project assignment (PRIMARY_PROJECT_GID where available)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.models.common import NameGid

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource

logger = get_logger(__name__)


def _get_holder_class_map() -> dict[str, type]:
    """Build the holder class map with deferred imports to avoid circular deps.

    Returns:
        Dict mapping holder_key to holder class for all 9 holder types.
    """
    from autom8_asana.models.business.business import (
        AssetEditHolder,
        DNAHolder,
        ReconciliationHolder,
        VideographyHolder,
    )
    from autom8_asana.models.business.contact import ContactHolder
    from autom8_asana.models.business.location import LocationHolder
    from autom8_asana.models.business.offer import OfferHolder
    from autom8_asana.models.business.process import ProcessHolder
    from autom8_asana.models.business.unit import UnitHolder

    return {
        # Business-level holders (7)
        "contact_holder": ContactHolder,
        "unit_holder": UnitHolder,
        "location_holder": LocationHolder,
        "dna_holder": DNAHolder,
        "reconciliation_holder": ReconciliationHolder,
        "asset_edit_holder": AssetEditHolder,
        "videography_holder": VideographyHolder,
        # Unit-level holders (2)
        "offer_holder": OfferHolder,
        "process_holder": ProcessHolder,
    }


# Module-level cache; populated on first access
_HOLDER_CLASS_MAP: dict[str, type] | None = None


def get_holder_class_map() -> dict[str, type]:
    """Get the holder class map, building it on first access.

    Returns:
        Dict mapping holder_key to holder class for all 9 holder types.
    """
    global _HOLDER_CLASS_MAP
    if _HOLDER_CLASS_MAP is None:
        _HOLDER_CLASS_MAP = _get_holder_class_map()
    return _HOLDER_CLASS_MAP


def construct_holder(
    holder_key: str,
    holder_key_map: dict[str, tuple[str, str]],
    parent_entity: AsanaResource,
) -> AsanaResource:
    """Construct a typed holder entity for a given holder_key.

    Per TDD-GAP-01 Section 5.1: Build a typed holder entity programmatically.

    Uses HOLDER_KEY_MAP metadata to determine:
    - Holder class (ContactHolder, UnitHolder, etc.)
    - Name (from the tuple: e.g., "Contacts", "Business Units")
    - Parent reference (set to parent_entity via NameGid)

    The holder is created with a temp GID (Option A from TDD Section 4.4) so
    that the pipeline's GID resolution chain works correctly.

    Per TDD Section 5.3: Project assignment uses PRIMARY_PROJECT_GID where
    available. Holders with PRIMARY_PROJECT_GID = None get no projects.

    Args:
        holder_key: Key from HOLDER_KEY_MAP (e.g., "contact_holder").
        holder_key_map: The HOLDER_KEY_MAP dict from the parent entity.
        parent_entity: The Business or Unit that owns this holder.

    Returns:
        A typed holder entity with:
        - gid = temp_{id(holder)} (explicit temp GID for pipeline resolution)
        - name = conventional name from HOLDER_KEY_MAP
        - parent = NameGid with parent's real or temp GID
        - resource_type = "task"
        - projects = [NameGid(gid=PRIMARY_PROJECT_GID)] if available

    Raises:
        KeyError: If holder_key is not in holder_key_map or HOLDER_CLASS_MAP.
    """
    class_map = get_holder_class_map()

    if holder_key not in class_map:
        raise KeyError(f"Unknown holder type: {holder_key}")

    holder_class = class_map[holder_key]
    conventional_name, _emoji = holder_key_map[holder_key]

    # Construct holder with empty GID (Pydantic requires gid field)
    holder = holder_class(
        gid="",
        name=conventional_name,
        resource_type="task",
    )

    # Assign explicit temp GID for pipeline resolution (Option A)
    object.__setattr__(holder, "gid", f"temp_{id(holder)}")

    # Set parent reference for dependency graph
    parent_gid = parent_entity.gid
    if parent_gid and not parent_gid.startswith("temp_"):
        # Parent has real GID
        holder.parent = NameGid(gid=parent_gid)
    else:
        # Parent also new -- use temp_{id(parent)} for payload serialization
        holder.parent = NameGid(gid=f"temp_{id(parent_entity)}")

    # Wire holder -> parent business reference
    from autom8_asana.models.business.business import Business

    if isinstance(parent_entity, Business):
        holder._business = parent_entity
    else:
        # For Unit-level holders, propagate _business from parent
        holder._business = getattr(parent_entity, "_business", None)

    # Project assignment (FR-008, TDD Section 5.3)
    primary_project_gid = getattr(holder_class, "PRIMARY_PROJECT_GID", None)
    if primary_project_gid is not None:
        holder.projects = [NameGid(gid=primary_project_gid)]

    logger.info(
        "holder_construction_complete",
        parent_gid=parent_gid,
        holder_type=holder_key,
        temp_gid=holder.gid,
        holder_name=conventional_name,
        has_project=primary_project_gid is not None,
    )

    return holder


async def detect_existing_holders(
    client: AsanaClient,
    parent_gid: str,
    holder_key_map: dict[str, tuple[str, str]],
) -> dict[str, AsanaResource]:
    """Detect which holders already exist as subtasks of parent.

    Per TDD-GAP-01 Section 3.4: Calls the subtasks API once per parent,
    then uses identify_holder_type() (same logic as the read path) to
    match each subtask.

    Args:
        client: AsanaClient for subtasks_async call.
        parent_gid: GID of the parent entity (Business or Unit).
        holder_key_map: The HOLDER_KEY_MAP to match against.

    Returns:
        Dict of holder_key -> typed holder entity for existing holders.
        Missing holder types are absent from the dict.
    """
    from autom8_asana.models.business.detection import identify_holder_type

    logger.info(
        "holder_detection_start",
        parent_gid=parent_gid,
    )

    # Fetch subtasks once per parent
    subtasks = await client.tasks.subtasks_async(
        parent_gid, include_detection_fields=True
    ).collect()

    existing: dict[str, Any] = {}

    for subtask in subtasks:
        holder_key = identify_holder_type(subtask, holder_key_map, filter_to_map=True)
        if holder_key:
            existing[holder_key] = subtask
            logger.info(
                "holder_detected_existing",
                parent_gid=parent_gid,
                holder_type=holder_key,
                holder_gid=subtask.gid,
            )

    existing_count = len(existing)
    missing_count = len(holder_key_map) - existing_count

    logger.info(
        "holder_detection_complete",
        parent_gid=parent_gid,
        existing=existing_count,
        missing=missing_count,
    )

    return existing
