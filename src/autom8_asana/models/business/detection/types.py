"""Entity type definitions for business model hierarchy.

This module provides:
- DetectionResult: Immutable result container with type, confidence, tier, and healing info
- EntityTypeInfo: Master configuration dataclass for entity type metadata
- CONFIDENCE_TIER_*: Float constants for detection tier confidence levels

EntityType lives in ``core.types``. Import it from there or from the
``detection`` package __init__.
"""

from __future__ import annotations

from dataclasses import dataclass

from autom8_asana.core.types import EntityType

__all__ = [
    "DetectionResult",
    "EntityTypeInfo",
    "CONFIDENCE_TIER_1",
    "CONFIDENCE_TIER_2",
    "CONFIDENCE_TIER_3",
    "CONFIDENCE_TIER_4",
    "CONFIDENCE_TIER_5",
]


# --- Confidence Constants ---
# Per TDD-DETECTION: Confidence levels for each detection tier

CONFIDENCE_TIER_1: float = 1.0  # Project membership (deterministic)
CONFIDENCE_TIER_2: float = 0.6  # Name patterns (unreliable)
CONFIDENCE_TIER_3: float = 0.8  # Parent inference (reliable)
CONFIDENCE_TIER_4: float = 0.9  # Structure inspection
CONFIDENCE_TIER_5: float = 0.0  # Unknown fallback


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Result of entity type detection.

    Per TDD-DETECTION/ADR-0094: Structured result with type, tier, and healing info.

    This frozen dataclass provides an immutable detection result that includes:
    - The detected entity type
    - Confidence level (0.0 - 1.0)
    - Which tier succeeded
    - Whether the entity needs healing (project membership repair)
    - Expected project GID for healing

    Attributes:
        entity_type: Detected type or EntityType.UNKNOWN.
        confidence: Detection confidence (0.0 - 1.0).
        tier_used: Which detection tier succeeded (1-5).
        needs_healing: True if entity lacks expected project membership.
        expected_project_gid: GID entity should have for Tier 1 detection.

    Example:
        >>> result = detect_entity_type(task)
        >>> if result:  # False for UNKNOWN
        ...     print(f"Detected {result.entity_type.name} via tier {result.tier_used}")
        >>> if result.needs_healing:
        ...     print(f"Entity should be in project {result.expected_project_gid}")
    """

    entity_type: EntityType
    confidence: float
    tier_used: int
    needs_healing: bool
    expected_project_gid: str | None

    def __bool__(self) -> bool:
        """Return False for UNKNOWN, True otherwise.

        Enables natural `if result:` checks.
        """
        return self.entity_type != EntityType.UNKNOWN

    @property
    def is_deterministic(self) -> bool:
        """True if detected via project membership (Tier 1)."""
        return self.tier_used == 1


@dataclass(frozen=True, slots=True)
class EntityTypeInfo:
    """Master configuration for an entity type - single source of truth.

    Per Architect Decision: EntityTypeInfo consolidates entity type metadata
    to derive NAME_PATTERNS, PARENT_CHILD_MAP, and provide holder attribute
    lookups for detection-based holder identification.

    Attributes:
        entity_type: The EntityType enum value this info describes.
        name_pattern: Substring pattern for Tier 2 name detection (e.g., "contacts").
        display_name: Human-readable name for HOLDER_KEY_MAP fallback (e.g., "Contacts").
        emoji: Custom emoji indicator for holder matching (e.g., "busts_in_silhouette").
        holder_attr: Private attribute name on parent (e.g., "_contact_holder").
        child_type: EntityType of children for PARENT_CHILD_MAP derivation.
        has_project: Whether this entity type has a dedicated Asana project.
    """

    entity_type: EntityType
    name_pattern: str | None = None
    display_name: str | None = None
    emoji: str | None = None
    holder_attr: str | None = None
    child_type: EntityType | None = None
    has_project: bool = True
