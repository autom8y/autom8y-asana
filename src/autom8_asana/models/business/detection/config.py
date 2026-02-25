"""Entity type configuration for business model hierarchy.

This module provides:
- ENTITY_TYPE_INFO: Master configuration dict mapping EntityType to EntityTypeInfo
- NAME_PATTERNS: Derived name pattern map for Tier 2 detection
- PARENT_CHILD_MAP: Derived parent-to-child type inference map
- get_holder_attr(): Lookup holder attribute from EntityTypeInfo
- entity_type_to_holder_attr(): Alias for get_holder_attr()

Dependencies: types.py only
"""

from __future__ import annotations

from autom8_asana.core.types import EntityType
from autom8_asana.models.business.detection.types import EntityTypeInfo

__all__ = [
    "ENTITY_TYPE_INFO",
    "NAME_PATTERNS",
    "PARENT_CHILD_MAP",
    "get_holder_attr",
    "entity_type_to_holder_attr",
]


# Master configuration dictionary - all holder types defined here
ENTITY_TYPE_INFO: dict[EntityType, EntityTypeInfo] = {
    # Root entity
    EntityType.BUSINESS: EntityTypeInfo(
        entity_type=EntityType.BUSINESS,
        display_name="Business",
        has_project=True,
    ),
    # Business-level holders
    EntityType.CONTACT_HOLDER: EntityTypeInfo(
        entity_type=EntityType.CONTACT_HOLDER,
        name_pattern="contacts",
        display_name="Contacts",
        emoji="busts_in_silhouette",
        holder_attr="_contact_holder",
        child_type=EntityType.CONTACT,
        has_project=True,
    ),
    EntityType.UNIT_HOLDER: EntityTypeInfo(
        entity_type=EntityType.UNIT_HOLDER,
        name_pattern="units",
        display_name="Business Units",
        emoji="package",
        holder_attr="_unit_holder",
        child_type=EntityType.UNIT,
        has_project=False,  # UnitHolder has no dedicated project
    ),
    EntityType.LOCATION_HOLDER: EntityTypeInfo(
        entity_type=EntityType.LOCATION_HOLDER,
        name_pattern="location",
        display_name="Location",
        emoji="round_pushpin",
        holder_attr="_location_holder",
        child_type=EntityType.LOCATION,
        has_project=False,  # LocationHolder has no dedicated project
    ),
    EntityType.DNA_HOLDER: EntityTypeInfo(
        entity_type=EntityType.DNA_HOLDER,
        name_pattern="dna",
        display_name="DNA",
        emoji="dna",
        holder_attr="_dna_holder",
        has_project=True,
    ),
    EntityType.RECONCILIATIONS_HOLDER: EntityTypeInfo(
        entity_type=EntityType.RECONCILIATIONS_HOLDER,
        name_pattern="reconciliations",
        display_name="Reconciliations",
        emoji="abacus",
        holder_attr="_reconciliation_holder",
        has_project=True,
    ),
    EntityType.ASSET_EDIT_HOLDER: EntityTypeInfo(
        entity_type=EntityType.ASSET_EDIT_HOLDER,
        name_pattern="asset edit",
        display_name="Asset Edits",
        emoji="art",
        holder_attr="_asset_edit_holder",
        has_project=True,
    ),
    EntityType.VIDEOGRAPHY_HOLDER: EntityTypeInfo(
        entity_type=EntityType.VIDEOGRAPHY_HOLDER,
        name_pattern="videography",
        display_name="Videography",
        emoji="video_camera",
        holder_attr="_videography_holder",
        has_project=True,
    ),
    # Unit-level holders
    EntityType.OFFER_HOLDER: EntityTypeInfo(
        entity_type=EntityType.OFFER_HOLDER,
        name_pattern="offers",
        display_name="Offers",
        emoji="gift",
        holder_attr="_offer_holder",
        child_type=EntityType.OFFER,
        has_project=True,
    ),
    EntityType.PROCESS_HOLDER: EntityTypeInfo(
        entity_type=EntityType.PROCESS_HOLDER,
        name_pattern="processes",
        display_name="Processes",
        emoji="gear",
        holder_attr="_process_holder",
        child_type=EntityType.PROCESS,
        has_project=False,  # ProcessHolder has no dedicated project
    ),
    # Composite entity
    EntityType.UNIT: EntityTypeInfo(
        entity_type=EntityType.UNIT,
        display_name="Unit",
        has_project=True,
    ),
    # Leaf entities
    EntityType.CONTACT: EntityTypeInfo(
        entity_type=EntityType.CONTACT,
        display_name="Contact",
        has_project=True,
    ),
    EntityType.OFFER: EntityTypeInfo(
        entity_type=EntityType.OFFER,
        display_name="Offer",
        has_project=True,
    ),
    EntityType.PROCESS: EntityTypeInfo(
        entity_type=EntityType.PROCESS,
        display_name="Process",
        has_project=True,
    ),
    EntityType.LOCATION: EntityTypeInfo(
        entity_type=EntityType.LOCATION,
        display_name="Location",
        has_project=True,
    ),
    EntityType.HOURS: EntityTypeInfo(
        entity_type=EntityType.HOURS,
        display_name="Hours",
        has_project=True,
    ),
    # Fallback
    EntityType.UNKNOWN: EntityTypeInfo(
        entity_type=EntityType.UNKNOWN,
        display_name="Unknown",
        has_project=False,
    ),
}


# --- Helper Functions ---


def get_holder_attr(entity_type: EntityType) -> str | None:
    """Get the holder attribute name for an entity type.

    Args:
        entity_type: The EntityType to look up.

    Returns:
        The holder attribute name (e.g., "_contact_holder") or None if not a holder.

    Example:
        >>> get_holder_attr(EntityType.CONTACT_HOLDER)
        '_contact_holder'
        >>> get_holder_attr(EntityType.BUSINESS)
        None
    """
    info = ENTITY_TYPE_INFO.get(entity_type)
    return info.holder_attr if info else None


def entity_type_to_holder_attr(entity_type: EntityType) -> str | None:
    """Map entity type to its holder attribute name.

    Alias for get_holder_attr() for semantic clarity.

    Args:
        entity_type: The EntityType to map.

    Returns:
        The holder attribute name or None if not a holder.
    """
    return get_holder_attr(entity_type)


# --- Derived Maps (from ENTITY_TYPE_INFO) ---


def _derive_name_patterns() -> dict[str, EntityType]:
    """Derive NAME_PATTERNS from ENTITY_TYPE_INFO at module load."""
    patterns: dict[str, EntityType] = {}
    for info in ENTITY_TYPE_INFO.values():
        if info.name_pattern:
            patterns[info.name_pattern] = info.entity_type
    return patterns


def _derive_parent_child_map() -> dict[EntityType, EntityType]:
    """Derive PARENT_CHILD_MAP from ENTITY_TYPE_INFO at module load."""
    mapping: dict[EntityType, EntityType] = {}
    for info in ENTITY_TYPE_INFO.values():
        if info.child_type:
            mapping[info.entity_type] = info.child_type
    return mapping


# --- Name Pattern Maps (Derived from ENTITY_TYPE_INFO) ---

# Per TDD-DETECTION/ADR-0094: Name pattern map for Tier 2 (contains matching)
# Maps substrings to their EntityType for case-insensitive contains matching
# DERIVED from ENTITY_TYPE_INFO at module load time
NAME_PATTERNS: dict[str, EntityType] = _derive_name_patterns()

# Per TDD-DETECTION: Parent-to-child type inference map for Tier 3
# Maps parent EntityType to inferred child EntityType
# DERIVED from ENTITY_TYPE_INFO at module load time
PARENT_CHILD_MAP: dict[EntityType, EntityType] = _derive_parent_child_map()
