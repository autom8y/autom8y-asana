"""Entity type detection patterns.

Per ADR-0117/FR-DET-005: Word boundary-aware pattern matching configuration.

This module provides configurable pattern specifications for Tier 2 name-based
entity type detection. Patterns use word boundary matching to avoid false
positives (e.g., "Community" should NOT match "unit").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.business.detection import EntityType

__all__ = [
    "PatternSpec",
    "STRIP_PATTERNS",
    "get_pattern_config",
    "get_pattern_priority",
]


@dataclass(frozen=True, slots=True)
class PatternSpec:
    """Configuration for entity type pattern matching.

    Attributes:
        patterns: Tuple of patterns to match (singular and plural forms).
        word_boundary: Whether to use word boundary matching (default: True).
        strip_decorations: Whether to strip decorations before matching (default: True).
    """

    patterns: tuple[str, ...]
    word_boundary: bool = True
    strip_decorations: bool = True


def _get_pattern_config() -> dict[EntityType, PatternSpec]:
    """Build pattern configuration dictionary.

    Deferred import to avoid circular dependency with detection module.
    """
    from autom8_asana.models.business.detection import EntityType

    return {
        EntityType.CONTACT_HOLDER: PatternSpec(
            patterns=("contacts", "contact"),
        ),
        EntityType.UNIT_HOLDER: PatternSpec(
            patterns=("units", "unit", "business units"),
        ),
        EntityType.OFFER_HOLDER: PatternSpec(
            patterns=("offers", "offer"),
        ),
        EntityType.PROCESS_HOLDER: PatternSpec(
            patterns=("processes", "process"),
        ),
        EntityType.LOCATION_HOLDER: PatternSpec(
            patterns=("location", "address"),
        ),
        EntityType.DNA_HOLDER: PatternSpec(
            patterns=("dna",),
        ),
        EntityType.RECONCILIATIONS_HOLDER: PatternSpec(
            patterns=("reconciliations", "reconciliation"),
        ),
        EntityType.ASSET_EDIT_HOLDER: PatternSpec(
            patterns=("asset edit", "asset edits"),
        ),
        EntityType.VIDEOGRAPHY_HOLDER: PatternSpec(
            patterns=("videography",),
        ),
    }


def _get_pattern_priority() -> list[EntityType]:
    """Build pattern priority list (most specific first).

    Deferred import to avoid circular dependency with detection module.
    """
    from autom8_asana.models.business.detection import EntityType

    return [
        EntityType.ASSET_EDIT_HOLDER,  # "asset edit" before others
        EntityType.RECONCILIATIONS_HOLDER,  # Multi-word before single
        EntityType.CONTACT_HOLDER,
        EntityType.UNIT_HOLDER,
        EntityType.OFFER_HOLDER,
        EntityType.PROCESS_HOLDER,
        EntityType.LOCATION_HOLDER,
        EntityType.DNA_HOLDER,
        EntityType.VIDEOGRAPHY_HOLDER,
    ]


# Decoration stripping patterns (applied before pattern matching)
# These handle common task name prefixes/suffixes that don't affect entity type
STRIP_PATTERNS: list[str] = [
    r"^\[.*?\]\s*",  # [URGENT] prefix
    r"^>+\s*",  # >> prefix
    r"\s*<+$",  # << suffix
    r"\s*\(.*?\)$",  # (Primary) suffix
    r"^\d+\.\s*",  # "1. " numbered prefix
    r"^[-*]\s*",  # "- " or "* " bullet prefix
]


# Lazy-initialized at first access
_PATTERN_CONFIG: dict[EntityType, PatternSpec] | None = None
_PATTERN_PRIORITY: list[EntityType] | None = None


def get_pattern_config() -> dict[EntityType, PatternSpec]:
    """Get pattern configuration (lazy initialization)."""
    global _PATTERN_CONFIG
    if _PATTERN_CONFIG is None:
        _PATTERN_CONFIG = _get_pattern_config()
    return _PATTERN_CONFIG


def get_pattern_priority() -> list[EntityType]:
    """Get pattern priority list (lazy initialization)."""
    global _PATTERN_PRIORITY
    if _PATTERN_PRIORITY is None:
        _PATTERN_PRIORITY = _get_pattern_priority()
    return _PATTERN_PRIORITY
