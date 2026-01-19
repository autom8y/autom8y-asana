"""Tier 2: Name pattern detection.

Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: Name convention detection, ~60% accuracy.

This module provides entity type detection via name pattern matching.
Uses word boundary matching to avoid false positives.

Functions:
    detect_by_name_pattern: Main Tier 2 detection function
    _strip_decorations: Remove task name decorations
    _compile_word_boundary_pattern: Cached regex compilation

Dependencies: types.py, config.py
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_2,
    DetectionResult,
)

if TYPE_CHECKING:
    from autom8_asana.models.task import Task

__all__ = [
    "detect_by_name_pattern",
    "_detect_by_name_pattern",
    "_strip_decorations",
    "_compile_word_boundary_pattern",
    "_matches_pattern_with_word_boundary",
]

logger = get_logger(__name__)


@lru_cache(maxsize=128)
def _compile_word_boundary_pattern(pattern: str) -> re.Pattern[str]:
    """Compile pattern with word boundary markers (cached).

    Per ADR-0117: Use word boundaries to avoid false positives.

    Args:
        pattern: Pattern string to compile (e.g., "contacts").

    Returns:
        Compiled regex pattern with word boundaries.
    """
    return re.compile(rf"\b{re.escape(pattern)}\b", re.IGNORECASE)


def _strip_decorations(name: str) -> str:
    """Remove common task name decorations.

    Per ADR-0117/FR-DET-005: Strip decorations before pattern matching.

    Handles common prefixes/suffixes:
    - [URGENT] prefix
    - >> prefix, << suffix
    - (Primary) suffix
    - "1. " numbered prefix
    - "- " or "* " bullet prefix

    Args:
        name: Task name to strip.

    Returns:
        Name with decorations removed.
    """
    from autom8_asana.models.business.patterns import STRIP_PATTERNS

    result = name
    for pattern in STRIP_PATTERNS:
        result = re.sub(pattern, "", result)
    return result.strip()


def _matches_pattern_with_word_boundary(
    name: str, patterns: tuple[str, ...], use_word_boundary: bool
) -> str | None:
    """Check if name matches any pattern.

    Args:
        name: Name to check.
        patterns: Patterns to match against.
        use_word_boundary: Whether to use word boundary matching.

    Returns:
        The matched pattern if found, None otherwise.
    """
    for pattern in patterns:
        if use_word_boundary:
            compiled = _compile_word_boundary_pattern(pattern)
            if compiled.search(name):
                return pattern
        else:
            if pattern in name.lower():
                return pattern
    return None


def _detect_by_name_pattern(task: Task) -> DetectionResult | None:
    """Tier 2: Detect entity type by name pattern matching.

    Per TDD-DETECTION/ADR-0094/ADR-0117: Word boundary-aware matching.

    This is the fallback when project membership detection fails.
    Uses word boundary matching to avoid false positives (e.g., "Community"
    should NOT match "unit").

    Args:
        task: Task to detect type for.

    Returns:
        DetectionResult if name contains a known pattern, None otherwise.
    """
    from autom8_asana.models.business.patterns import (
        get_pattern_config,
        get_pattern_priority,
    )
    from autom8_asana.models.business.registry import get_registry

    if not task.name:
        return None

    # Get original name and stripped version
    name_original = task.name
    name_stripped = _strip_decorations(name_original)

    # Get pattern configuration
    pattern_config = get_pattern_config()
    pattern_priority = get_pattern_priority()

    # Check patterns in priority order
    for entity_type in pattern_priority:
        spec = pattern_config.get(entity_type)
        if spec is None:
            continue

        # Check both original and stripped names
        for name in (name_original, name_stripped):
            matched_pattern = _matches_pattern_with_word_boundary(
                name, spec.patterns, spec.word_boundary
            )
            if matched_pattern:
                expected_gid = get_registry().get_primary_gid(entity_type)

                logger.debug(
                    "Detected %s via name pattern '%s' (Tier 2, word_boundary=%s)",
                    entity_type.name,
                    matched_pattern,
                    spec.word_boundary,
                    extra={
                        "task_gid": task.gid,
                        "pattern": matched_pattern,
                        "tier": 2,
                        "word_boundary": spec.word_boundary,
                    },
                )

                return DetectionResult(
                    entity_type=entity_type,
                    confidence=CONFIDENCE_TIER_2,
                    tier_used=2,
                    needs_healing=True,
                    expected_project_gid=expected_gid,
                )

    return None


def detect_by_name_pattern(task: Task) -> DetectionResult | None:
    """Tier 2: Detect entity type by name pattern matching.

    Per TDD-DETECTION/ADR-0094/ADR-0117: Word boundary-aware matching.

    Public wrapper for _detect_by_name_pattern.

    Args:
        task: Task to detect type for.

    Returns:
        DetectionResult if name contains a known pattern, None otherwise.

    Example:
        >>> result = detect_by_name_pattern(task)
        >>> if result:
        ...     print(f"Detected {result.entity_type.name} via name pattern")
    """
    return _detect_by_name_pattern(task)
