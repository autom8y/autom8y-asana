"""Entity type detection for business model hierarchy.

This package provides tiered type detection capabilities for identifying entity types.
The detection chain prioritizes deterministic project-membership detection (Tier 1),
with fallback tiers for name patterns, parent inference, and structure inspection.

Detection Tiers:
1. Project membership lookup (O(1), no API, deterministic) - tier1.py
2. Name pattern matching (string ops, no API) - tier2.py
3. Parent type inference (logic only, no API) - tier3.py
4. Structure inspection via subtasks (async, requires API) - tier4.py
5. Unknown fallback (needs_healing=True) - facade.py

Example:
    # Sync detection (Tiers 1-3, no API calls)
    result = detect_entity_type(task)

    # Async detection with optional Tier 4
    result = await detect_entity_type_async(task, client, allow_structure_inspection=True)

Note: Private functions (_detect_by_name_pattern, _compile_word_boundary_pattern, etc.)
are re-exported for test compatibility. They are internal APIs subject to change.
"""

from __future__ import annotations

# Layer 0: Pure types (no dependencies)
from autom8_asana.core.types import EntityType

# Layer 1: Configuration (depends on types only)
from autom8_asana.models.business.detection.config import (
    ENTITY_TYPE_INFO,
    NAME_PATTERNS,
    PARENT_CHILD_MAP,
    entity_type_to_holder_attr,
    get_holder_attr,
)

# Layer 3: Facade - orchestration functions
from autom8_asana.models.business.detection.facade import (
    _matches_holder_pattern,
    detect_by_parent,
    detect_by_project,
    detect_by_structure_async,
    detect_entity_type,
    detect_entity_type_async,
    detect_entity_type_from_dict,
    identify_holder_type,
)

# Layer 2: Tier modules (depend on types and config)
from autom8_asana.models.business.detection.tier1 import (
    _detect_tier1_project_membership,
    _detect_tier1_project_membership_async,
    detect_by_project_membership,
    detect_by_project_membership_async,
)
from autom8_asana.models.business.detection.tier2 import (
    _compile_word_boundary_pattern,
    _detect_by_name_pattern,
    _matches_pattern_with_word_boundary,
    _strip_decorations,
    detect_by_name_pattern,
)
from autom8_asana.models.business.detection.tier3 import (
    detect_by_parent_inference,
)
from autom8_asana.models.business.detection.tier4 import (
    detect_by_structure_inspection,
)
from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_1,
    CONFIDENCE_TIER_2,
    CONFIDENCE_TIER_3,
    CONFIDENCE_TIER_4,
    CONFIDENCE_TIER_5,
    DetectionResult,
    EntityTypeInfo,
)

__all__ = [
    # Types
    "EntityType",
    "EntityTypeInfo",
    "DetectionResult",
    # Constants
    "ENTITY_TYPE_INFO",
    "NAME_PATTERNS",
    "PARENT_CHILD_MAP",
    "CONFIDENCE_TIER_1",
    "CONFIDENCE_TIER_2",
    "CONFIDENCE_TIER_3",
    "CONFIDENCE_TIER_4",
    "CONFIDENCE_TIER_5",
    # Config functions
    "get_holder_attr",
    "entity_type_to_holder_attr",
    # Tier 1: Project membership
    "detect_by_project_membership",
    "detect_by_project_membership_async",
    "_detect_tier1_project_membership",
    "_detect_tier1_project_membership_async",
    # Tier 2: Name patterns
    "detect_by_name_pattern",
    "_detect_by_name_pattern",
    "_compile_word_boundary_pattern",
    "_strip_decorations",
    "_matches_pattern_with_word_boundary",
    # Tier 3: Parent inference
    "detect_by_parent_inference",
    # Tier 4: Structure inspection
    "detect_by_structure_inspection",
    # Facade: Orchestration
    "detect_by_project",
    "detect_by_parent",
    "detect_by_structure_async",
    "detect_entity_type",
    "detect_entity_type_async",
    "detect_entity_type_from_dict",
    "identify_holder_type",
    "_matches_holder_pattern",
]
