"""Canonical entity type constants.

Single source of truth for entity type lists across all subsystems.
Add new entity types HERE; all consumers import from this module.
"""

from __future__ import annotations

# Core entity types used by DataFrameCache, admin, and query subsystems
ENTITY_TYPES: list[str] = [
    "unit",
    "business",
    "offer",
    "contact",
    "asset_edit",
]

# Extended set including derivative types (used by schema providers)
ENTITY_TYPES_WITH_DERIVATIVES: list[str] = [
    *ENTITY_TYPES,
    "asset_edit_holder",
]
