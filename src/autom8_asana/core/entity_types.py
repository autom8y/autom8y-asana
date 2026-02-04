"""Canonical entity type constants.

FACADE: Delegates to EntityRegistry. Preserves existing import paths.
All consumers continue to use: from autom8_asana.core.entity_types import ENTITY_TYPES

See: src/autom8_asana/core/entity_registry.py for the single source of truth.
"""

from __future__ import annotations

from autom8_asana.core.entity_registry import get_registry

_registry = get_registry()

# Core entity types used by DataFrameCache, admin, and query subsystems
ENTITY_TYPES: list[str] = [
    d.name for d in _registry.warmable_entities() if not d.is_holder
]

# Extended set including derivative types (used by schema providers)
ENTITY_TYPES_WITH_DERIVATIVES: list[str] = [
    d.name for d in _registry.warmable_entities()
]
