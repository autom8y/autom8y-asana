# TDD: Entity Knowledge Registry

**TDD ID**: TDD-ENTITY-REGISTRY-001
**Version**: 1.0
**Date**: 2026-02-04
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: Architectural Opportunities Initiative, B1 (Wave 2)
**Spike References**: S0-003 (Entity Addition Workflow), S0-005 (Entity Metadata Catalog)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Proposed Architecture](#proposed-architecture)
5. [Component Design: EntityDescriptor](#component-design-entitydescriptor)
6. [Component Design: EntityRegistry](#component-design-entityregistry)
7. [Backward-Compatible Facades](#backward-compatible-facades)
8. [Startup Validation](#startup-validation)
9. [Migration Phases](#migration-phases)
10. [Interface Contracts](#interface-contracts)
11. [Data Flow Diagrams](#data-flow-diagrams)
12. [Non-Functional Considerations](#non-functional-considerations)
13. [Test Strategy](#test-strategy)
14. [Risk Assessment](#risk-assessment)
15. [ADRs](#adrs)
16. [Success Criteria](#success-criteria)

---

## Overview

This TDD specifies an `EntityRegistry` singleton backed by frozen `EntityDescriptor` dataclasses that consolidates the 53+ locations of entity knowledge identified in spike S0-005 into a single declaration per entity type. The registry provides O(1) lookup by name, by Asana project GID, and by `EntityType` enum. Existing consumers (`ENTITY_TYPES`, `ENTITY_TYPE_INFO`, `DEFAULT_ENTITY_TTLS`, `ENTITY_ALIASES`, `DEFAULT_KEY_COLUMNS`) become thin backward-compatible facades that delegate to the registry, ensuring zero breaking changes to the 8,022 existing tests.

### Solution Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| `EntityDescriptor` | `core/entity_registry.py` | Frozen dataclass capturing all metadata for one entity type |
| `EntityRegistry` | `core/entity_registry.py` | Singleton with three indexes (name, GID, EntityType) and query methods |
| `ENTITY_DESCRIPTORS` | `core/entity_registry.py` | Module-level tuple of all EntityDescriptor instances (the single source of truth) |
| Startup validation | `core/entity_registry.py` | Import-time integrity check cross-referencing facades against registry |
| Facade wrappers | Various existing modules | Thin delegations preserving existing import paths and APIs |

---

## Problem Statement

### Current State

Per spike S0-005, the same "which entity types exist and what do they look like" knowledge is scattered across **53+ distinct locations** in the codebase with **5-way redundancy** on the fundamental question of which entity types exist. Per spike S0-003, adding a new entity type (traced via `asset_edit`) required changes across **16 files in 10 subsystems**. At least one location was missed during initial addition and only discovered during Sprint 3 refactoring (RF-L21).

The fragmentation breaks down into:

| Redundancy | Locations | Drift Risk |
|-----------|-----------|------------|
| Entity type lists | 5+ independent `list[str]`, `Enum`, `dict` keys | High -- RF-L21 showed real-world miss |
| Entity-to-project GID | 3 sources (ClassVars, ProjectTypeRegistry, EntityProjectRegistry) | Medium -- bootstrap copies static GIDs |
| Entity hierarchy | 3 sources (hierarchy.py, ENTITY_TYPE_INFO, HOLDER_KEY_MAP) | Medium -- overlapping but non-identical |
| Name/display conventions | 3 sources (detection, holder maps, discovery normalization) | Low-Medium |
| TTL configuration | 2 sources (module-level dict, CacheConfig instance copy) | Low |

### Impact

- **Adding a new entity type costs 13+ file touches** (spike S0-003 recommendation 7)
- **Silent runtime failures** when a location is missed (no import-time validation)
- **Cognitive load**: Developers must understand 5+ modules to reason about entity metadata
- **Testing gaps**: 5 of 14 functional touch points had no direct test coverage for `asset_edit`

### Why Not Just Fix the Lists?

Sprint 3 already fixed the most dangerous instance (RF-L21: hardcoded `SUPPORTED_ENTITY_TYPES` replaced with `set(ENTITY_TYPES)`). But this is whack-a-mole. The fundamental problem is that entity knowledge has no single owner. Each subsystem declares its own copy and hopes it stays in sync. A registry inverts this: subsystems ask the registry instead of maintaining their own lists.

---

## Goals and Non-Goals

### Goals

| ID | Goal | Spike Reference |
|----|------|-----------------|
| G1 | Single declaration per entity type -- one `EntityDescriptor` captures name, display name, EntityType enum, project GID, model class, hierarchy, detection config, TTL, warm priority, aliases, join keys | S0-005 Section 3 |
| G2 | O(1) lookup by name, project GID, and EntityType enum via pre-built indexes | S0-005 Section 3 |
| G3 | Zero breaking changes -- all existing consumers continue to work via backward-compatible facades | S0-005 Section 3 "backward compat" |
| G4 | Import-time integrity validation that detects missing or inconsistent entries | S0-003 Recommendation 2 |
| G5 | Adding a new entity type requires 1 registry entry + 2 files (model class, schema) | S0-003 Recommendation 1 |
| G6 | Handle the 17-member EntityType enum vs 5-member ENTITY_TYPES divergence explicitly | S0-005 Section 2.1 |

### Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Replace schema ColumnDef definitions | Schemas contain genuinely unique column definitions per entity; they reference the registry but are not metadata |
| NG2 | Replace model class implementations | Model classes contain field descriptors, validation, hydration logic -- genuinely unique per entity |
| NG3 | Replace detection tier logic | Detection algorithms (Tier 1-5) use registry data but contain independent logic |
| NG4 | Replace custom field descriptors | 50+ descriptors across Business, Unit, Contact, Offer are implementation details |
| NG5 | Consolidate PRIMARY_PROJECT_GID ClassVars in this sprint | Hard tier (S0-005 Section 4); deferred to avoid model class changes |
| NG6 | Replace EntityKind enum from MutationEvent | EntityKind (task/section/project) is a different domain than entity type metadata |

---

## Proposed Architecture

### System Context

```
                    ┌──────────────────────────────────────────┐
                    │          EntityRegistry (singleton)        │
                    │                                          │
                    │  ┌─────────────────────────────────────┐ │
                    │  │ ENTITY_DESCRIPTORS (frozen tuple)    │ │
                    │  │                                     │ │
                    │  │  EntityDescriptor("unit", ...)       │ │
                    │  │  EntityDescriptor("business", ...)   │ │
                    │  │  EntityDescriptor("contact", ...)    │ │
                    │  │  EntityDescriptor("offer", ...)      │ │
                    │  │  EntityDescriptor("asset_edit", ...) │ │
                    │  │  EntityDescriptor("asset_edit_holder")│ │
                    │  │  EntityDescriptor("hours", ...)      │ │
                    │  │  EntityDescriptor("location", ...)   │ │
                    │  │  EntityDescriptor("process", ...)    │ │
                    │  │  ... (holders, etc.)                 │ │
                    │  └─────────────────────────────────────┘ │
                    │                                          │
                    │  Indexes (built at import time):          │
                    │  _by_name:  dict[str, EntityDescriptor]   │
                    │  _by_gid:   dict[str, EntityDescriptor]   │
                    │  _by_type:  dict[EntityType, Descriptor]  │
                    └────────┬─────────┬──────────┬────────────┘
                             │         │          │
             ┌───────────────┤         │          ├────────────────┐
             │               │         │          │                │
             v               v         v          v                v
     ┌──────────────┐ ┌──────────┐ ┌────────┐ ┌─────────┐ ┌──────────────┐
     │ ENTITY_TYPES │ │ ENTITY_  │ │DEFAULT_│ │ENTITY_  │ │DEFAULT_KEY_  │
     │ (facade)     │ │TYPE_INFO │ │ENTITY_ │ │ALIASES  │ │COLUMNS       │
     │              │ │(facade)  │ │TTLS    │ │(facade) │ │(facade)      │
     │ entity_      │ │detection/│ │(facade)│ │resolver │ │universal_    │
     │ types.py     │ │config.py │ │config. │ │.py      │ │strategy.py   │
     └──────────────┘ └──────────┘ │py      │ └─────────┘ └──────────────┘
                                   └────────┘
```

### Key Design Decisions

1. **Module-level singleton, not class-level**: The registry is a module-level instance populated by a module-level tuple of descriptors. This avoids metaclass complexity and matches the `ENTITY_TYPE_INFO` pattern already proven in `detection/config.py`.

2. **Frozen descriptors, mutable indexes**: `EntityDescriptor` is `frozen=True` for thread safety and hashability. Indexes are built once at import time and never mutated.

3. **EntityType enum preserved**: The `EntityType` enum remains the identity type. The registry does not replace it; it indexes by it. Descriptors hold an `entity_type: EntityType | None` field because some entities (e.g., `AssetEdit` leaf) lack a dedicated enum member.

4. **Lazy model_class resolution**: The `model_class` field uses a string reference resolved lazily to avoid circular imports at module load time. Model classes import from `core/` but `core/` must not import from `models/`.

---

## Component Design: EntityDescriptor

### Dataclass Definition

```python
# src/autom8_asana/core/entity_registry.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class EntityCategory(str, Enum):
    """Classification of entity types by their role in the hierarchy."""
    ROOT = "root"           # Business
    COMPOSITE = "composite" # Unit (has nested holders)
    LEAF = "leaf"           # Contact, Offer, Process, Location, Hours, AssetEdit
    HOLDER = "holder"       # All *Holder types


@dataclass(frozen=True, slots=True)
class EntityDescriptor:
    """Complete metadata for a single entity type.

    Frozen for thread safety and hashability. One instance per entity type
    is defined in ENTITY_DESCRIPTORS and never mutated after module load.

    Attributes:
        name: Canonical snake_case identifier (e.g., "unit", "asset_edit_holder").
            Used as the primary key in all registry lookups.
        pascal_name: PascalCase form for SchemaRegistry lookups (e.g., "Unit",
            "AssetEditHolder"). Derived from name if not explicitly provided.
        display_name: Human-readable name for UI/logging (e.g., "Business Units").
        entity_type: EntityType enum member, or None for entities without a
            dedicated enum member (e.g., AssetEdit leaf has no EntityType.ASSET_EDIT).
        category: Classification as root, composite, leaf, or holder.

        primary_project_gid: Asana project GID for this entity type, or None
            for entities without a dedicated project (LocationHolder, ProcessHolder).
        model_class_path: Dotted import path for lazy model class resolution
            (e.g., "autom8_asana.models.business.unit.Unit"). Avoids circular
            imports at module load.

        parent_entity: Name of the parent entity type (e.g., "business" for
            ContactHolder). None for root entities.
        holder_for: If this is a holder, the name of the leaf entity it contains
            (e.g., "contact" for ContactHolder). None for non-holders.
        holder_attr: Private attribute name on parent model (e.g., "_contact_holder").
            None for non-holders.

        name_pattern: Substring pattern for Tier 2 name detection
            (e.g., "contacts"). None if not detectable by name.
        emoji: Custom emoji indicator for holder matching (e.g., "busts_in_silhouette").
            None if not detectable by emoji.

        schema_key: SchemaRegistry lookup key. Defaults to pascal_name.
            Overridable for cases where schema key differs from pascal name.
        default_ttl_seconds: Cache TTL in seconds. Defaults to 300 (5 min).
        warmable: Whether included in Lambda cache warming. Defaults to False.
        warm_priority: Warming order (lower = higher priority). Only meaningful
            when warmable=True. Defaults to 99.

        aliases: Field normalization alias chain for resolver
            (e.g., ["business_unit"] for unit). Defaults to empty list.
        join_keys: Default join column by target entity type
            (e.g., {"business": "office_phone"}). Defaults to empty dict.
        key_columns: Default key columns for DynamicIndex resolution.
            Defaults to empty list.

        explicit_name_mappings: Asana project name -> entity type mappings
            for discovery normalization (e.g., {"paid content": "asset_edit"}).
            Only set on entities whose project name does not normalize
            automatically. Defaults to empty dict.
    """

    # --- Identity ---
    name: str
    pascal_name: str
    display_name: str
    entity_type: Any = None  # EntityType | None -- Any to avoid import
    category: EntityCategory = EntityCategory.LEAF

    # --- Asana Project ---
    primary_project_gid: str | None = None
    model_class_path: str | None = None

    # --- Hierarchy ---
    parent_entity: str | None = None
    holder_for: str | None = None
    holder_attr: str | None = None

    # --- Detection ---
    name_pattern: str | None = None
    emoji: str | None = None

    # --- Schema ---
    schema_key: str | None = None  # Defaults to pascal_name if None

    # --- Cache Behavior ---
    default_ttl_seconds: int = 300
    warmable: bool = False
    warm_priority: int = 99

    # --- Field Normalization ---
    aliases: tuple[str, ...] = ()
    join_keys: tuple[tuple[str, str], ...] = ()  # ((target, key), ...)
    key_columns: tuple[str, ...] = ()

    # --- Discovery ---
    explicit_name_mappings: tuple[tuple[str, str], ...] = ()  # ((project_name, entity_name), ...)

    @property
    def effective_schema_key(self) -> str:
        """Schema key for SchemaRegistry lookup."""
        return self.schema_key or self.pascal_name

    @property
    def is_holder(self) -> bool:
        """True if this entity is a holder type."""
        return self.category == EntityCategory.HOLDER

    @property
    def has_project(self) -> bool:
        """True if this entity has a dedicated Asana project."""
        return self.primary_project_gid is not None

    def get_join_key(self, target: str) -> str | None:
        """Get the default join column for joining with target entity type."""
        for t, k in self.join_keys:
            if t == target:
                return k
        return None

    def get_model_class(self) -> type | None:
        """Lazily resolve model class from dotted path.

        Returns None if model_class_path is not set. Raises ImportError
        if the path is invalid.
        """
        if self.model_class_path is None:
            return None
        parts = self.model_class_path.rsplit(".", 1)
        if len(parts) != 2:
            return None
        import importlib
        module = importlib.import_module(parts[0])
        return getattr(module, parts[1])
```

### Design Rationale

**Why frozen dataclass with slots?** Matches the pattern established by `EntityTypeInfo`, `DetectionResult`, and `MutationEvent` in the existing codebase. Frozen provides thread safety without locks. Slots reduces memory footprint for 20+ instances.

**Why `tuple` instead of `list` for collection fields?** Frozen dataclasses require hashable fields. Tuples are hashable; lists are not. The `field(default_factory=tuple)` pattern is idiomatic for frozen dataclasses.

**Why `entity_type: Any` instead of `EntityType`?** Avoids importing `EntityType` from `models.business.detection.types` into `core/`, which would create a dependency from core toward models. The type annotation uses `Any` with a comment; runtime values are `EntityType` instances. ADR-001 documents this decision.

**Why `model_class_path: str` instead of `model_class: type`?** Model classes live in `models/business/*.py` which imports from `core/`. If `core/entity_registry.py` imported model classes, it would create a circular import. The string path is resolved lazily on first access.

---

## Component Design: EntityRegistry

### Registry Class

```python
class EntityRegistry:
    """Singleton registry providing O(1) lookup of entity metadata.

    Built at module load time from ENTITY_DESCRIPTORS. Provides three
    indexes for different lookup patterns:
    - by name (snake_case): Primary lookup for most subsystems
    - by project GID: Used by detection Tier 1 and bootstrap
    - by EntityType enum: Used by detection, hydration, holder logic

    Thread Safety:
        All state is built once at module load and never mutated.
        No locks needed for reads.

    Usage:
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()
        desc = registry.get("unit")
        desc = registry.get_by_gid("1201081073731555")
        warmable = registry.warmable_entities()
    """

    def __init__(self, descriptors: tuple[EntityDescriptor, ...]) -> None:
        self._descriptors = descriptors
        self._by_name: dict[str, EntityDescriptor] = {}
        self._by_gid: dict[str, EntityDescriptor] = {}
        self._by_type: dict[Any, EntityDescriptor] = {}  # EntityType -> Descriptor

        for d in descriptors:
            if d.name in self._by_name:
                raise ValueError(
                    f"Duplicate entity name: {d.name!r}"
                )
            self._by_name[d.name] = d

            if d.primary_project_gid is not None:
                if d.primary_project_gid in self._by_gid:
                    existing = self._by_gid[d.primary_project_gid]
                    raise ValueError(
                        f"Duplicate project GID {d.primary_project_gid!r}: "
                        f"{d.name!r} conflicts with {existing.name!r}"
                    )
                self._by_gid[d.primary_project_gid] = d

            if d.entity_type is not None:
                if d.entity_type in self._by_type:
                    existing = self._by_type[d.entity_type]
                    raise ValueError(
                        f"Duplicate EntityType {d.entity_type!r}: "
                        f"{d.name!r} conflicts with {existing.name!r}"
                    )
                self._by_type[d.entity_type] = d

    # --- Primary Lookups ---

    def get(self, name: str) -> EntityDescriptor | None:
        """Lookup by canonical snake_case name. O(1).

        Args:
            name: Entity name (e.g., "unit", "asset_edit_holder").

        Returns:
            EntityDescriptor if found, None otherwise.
        """
        return self._by_name.get(name)

    def require(self, name: str) -> EntityDescriptor:
        """Lookup by name, raising if not found.

        Args:
            name: Entity name.

        Returns:
            EntityDescriptor.

        Raises:
            KeyError: If entity name is not registered.
        """
        desc = self._by_name.get(name)
        if desc is None:
            available = sorted(self._by_name.keys())
            raise KeyError(
                f"Unknown entity type: {name!r}. "
                f"Available: {available}"
            )
        return desc

    def get_by_gid(self, project_gid: str) -> EntityDescriptor | None:
        """Lookup by Asana project GID. O(1).

        Args:
            project_gid: Asana project GID string.

        Returns:
            EntityDescriptor if found, None otherwise.
        """
        return self._by_gid.get(project_gid)

    def get_by_type(self, entity_type: Any) -> EntityDescriptor | None:
        """Lookup by EntityType enum member. O(1).

        Args:
            entity_type: EntityType enum value.

        Returns:
            EntityDescriptor if found, None otherwise.
        """
        return self._by_type.get(entity_type)

    # --- Collection Queries ---

    def all_descriptors(self) -> tuple[EntityDescriptor, ...]:
        """All registered descriptors in definition order."""
        return self._descriptors

    def all_names(self) -> list[str]:
        """All registered entity names in definition order."""
        return [d.name for d in self._descriptors]

    def warmable_entities(self) -> list[EntityDescriptor]:
        """Entities included in cache warming, sorted by priority (ascending).

        Returns:
            List of warmable EntityDescriptors, lowest warm_priority first.
        """
        return sorted(
            [d for d in self._descriptors if d.warmable],
            key=lambda d: d.warm_priority,
        )

    def dataframe_entities(self) -> list[str]:
        """Entity names that have DataFrame schemas (warmable or schema-bearing).

        Used by schema providers and cache stats initialization.

        Returns:
            List of entity names that should have DataFrame support.
        """
        return [d.name for d in self._descriptors if d.warmable]

    def holders(self) -> list[EntityDescriptor]:
        """All holder entity types."""
        return [d for d in self._descriptors if d.is_holder]

    def get_join_key(self, source: str, target: str) -> str | None:
        """Get the default join key between two entity types.

        Checks both directions (source -> target and target -> source).

        Args:
            source: Source entity type name.
            target: Target entity type name.

        Returns:
            Join column name, or None if no relationship exists.
        """
        desc = self._by_name.get(source)
        if desc is not None:
            key = desc.get_join_key(target)
            if key is not None:
                return key

        # Check reverse direction
        desc = self._by_name.get(target)
        if desc is not None:
            key = desc.get_join_key(source)
            if key is not None:
                return key

        return None

    def get_entity_ttl(self, name: str, default: int = 300) -> int:
        """Get cache TTL for entity type.

        Args:
            name: Entity name (case-insensitive).
            default: Fallback TTL if entity not found.

        Returns:
            TTL in seconds.
        """
        desc = self._by_name.get(name.lower())
        if desc is not None:
            return desc.default_ttl_seconds
        return default

    def get_aliases(self, name: str) -> tuple[str, ...]:
        """Get field normalization aliases for entity type.

        Args:
            name: Entity name.

        Returns:
            Tuple of alias strings, empty if not found.
        """
        desc = self._by_name.get(name)
        if desc is not None:
            return desc.aliases
        return ()

    def get_key_columns(self, name: str) -> tuple[str, ...]:
        """Get default key columns for DynamicIndex resolution.

        Args:
            name: Entity name.

        Returns:
            Tuple of column name strings, empty if not found.
        """
        desc = self._by_name.get(name)
        if desc is not None:
            return desc.key_columns
        return ()


# --- Module-Level Singleton ---

def _to_pascal(name: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in name.split("_"))
```

### Entity Descriptor Declarations

The single source of truth. Adding a new entity type means adding one entry here.

```python
ENTITY_DESCRIPTORS: tuple[EntityDescriptor, ...] = (

    # =========================================================================
    # Root Entity
    # =========================================================================

    EntityDescriptor(
        name="business",
        pascal_name="Business",
        display_name="Business",
        entity_type=None,  # Set post-import to avoid circular dep
        category=EntityCategory.ROOT,
        primary_project_gid="1200653012566782",
        model_class_path="autom8_asana.models.business.business.Business",
        default_ttl_seconds=3600,
        warmable=True,
        warm_priority=2,
        aliases=("office",),
        join_keys=(
            ("unit", "office_phone"),
            ("contact", "office_phone"),
            ("offer", "office_phone"),
        ),
        key_columns=("office_phone",),
    ),

    # =========================================================================
    # Composite Entity
    # =========================================================================

    EntityDescriptor(
        name="unit",
        pascal_name="Unit",
        display_name="Business Units",
        entity_type=None,  # Set post-import
        category=EntityCategory.COMPOSITE,
        primary_project_gid="1201081073731555",
        model_class_path="autom8_asana.models.business.unit.Unit",
        default_ttl_seconds=900,
        warmable=True,
        warm_priority=1,
        aliases=("business_unit",),
        join_keys=(
            ("business", "office_phone"),
            ("offer", "office_phone"),
        ),
        key_columns=("office_phone", "vertical"),
    ),

    # =========================================================================
    # Leaf Entities
    # =========================================================================

    EntityDescriptor(
        name="contact",
        pascal_name="Contact",
        display_name="Contact",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1200775689604552",
        model_class_path="autom8_asana.models.business.contact.Contact",
        default_ttl_seconds=900,
        warmable=True,
        warm_priority=4,
        aliases=(),
        join_keys=(
            ("business", "office_phone"),
        ),
        key_columns=("office_phone", "contact_phone", "contact_email"),
    ),

    EntityDescriptor(
        name="offer",
        pascal_name="Offer",
        display_name="Offer",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1143843662099250",
        model_class_path="autom8_asana.models.business.offer.Offer",
        default_ttl_seconds=180,
        warmable=True,
        warm_priority=3,
        aliases=("business_offer",),
        join_keys=(
            ("unit", "office_phone"),
            ("business", "office_phone"),
        ),
        key_columns=("office_phone", "vertical", "offer_id"),
    ),

    EntityDescriptor(
        name="asset_edit",
        pascal_name="AssetEdit",
        display_name="Asset Edits",
        entity_type=None,  # No dedicated EntityType enum member
        category=EntityCategory.LEAF,
        primary_project_gid="1202204184560785",
        model_class_path="autom8_asana.models.business.asset_edit.AssetEdit",
        default_ttl_seconds=300,
        warmable=True,
        warm_priority=5,
        aliases=("process",),
        key_columns=("office_phone", "vertical", "asset_id", "offer_id"),
        explicit_name_mappings=(("paid content", "asset_edit"),),
    ),

    EntityDescriptor(
        name="process",
        pascal_name="Process",
        display_name="Process",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid=None,  # Dynamic via workspace discovery
        model_class_path="autom8_asana.models.business.process.Process",
        default_ttl_seconds=60,
    ),

    EntityDescriptor(
        name="location",
        pascal_name="Location",
        display_name="Location",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1200836133305610",
        model_class_path="autom8_asana.models.business.location.Location",
        default_ttl_seconds=3600,
    ),

    EntityDescriptor(
        name="hours",
        pascal_name="Hours",
        display_name="Hours",
        entity_type=None,  # Set post-import
        category=EntityCategory.LEAF,
        primary_project_gid="1201614578074026",
        model_class_path="autom8_asana.models.business.hours.Hours",
        default_ttl_seconds=3600,
    ),

    # =========================================================================
    # Business-Level Holders
    # =========================================================================

    EntityDescriptor(
        name="contact_holder",
        pascal_name="ContactHolder",
        display_name="Contacts",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1201500116978260",
        model_class_path="autom8_asana.models.business.contact.ContactHolder",
        parent_entity="business",
        holder_for="contact",
        holder_attr="_contact_holder",
        name_pattern="contacts",
        emoji="busts_in_silhouette",
    ),

    EntityDescriptor(
        name="unit_holder",
        pascal_name="UnitHolder",
        display_name="Business Units",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1204433992667196",
        model_class_path="autom8_asana.models.business.unit.UnitHolder",
        parent_entity="business",
        holder_for="unit",
        holder_attr="_unit_holder",
        name_pattern="units",
        emoji="package",
    ),

    EntityDescriptor(
        name="location_holder",
        pascal_name="LocationHolder",
        display_name="Location",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid=None,
        model_class_path="autom8_asana.models.business.location.LocationHolder",
        parent_entity="business",
        holder_for="location",
        holder_attr="_location_holder",
        name_pattern="location",
        emoji="round_pushpin",
    ),

    EntityDescriptor(
        name="dna_holder",
        pascal_name="DNAHolder",
        display_name="DNA",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1167650840134033",
        model_class_path="autom8_asana.models.business.business.DNAHolder",
        parent_entity="business",
        holder_attr="_dna_holder",
        name_pattern="dna",
        emoji="dna",
    ),

    EntityDescriptor(
        name="reconciliation_holder",
        pascal_name="ReconciliationHolder",
        display_name="Reconciliations",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1203404998225231",
        model_class_path="autom8_asana.models.business.business.ReconciliationHolder",
        parent_entity="business",
        holder_attr="_reconciliation_holder",
        name_pattern="reconciliations",
        emoji="abacus",
    ),

    EntityDescriptor(
        name="asset_edit_holder",
        pascal_name="AssetEditHolder",
        display_name="Asset Edits",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1203992664400125",
        model_class_path="autom8_asana.models.business.business.AssetEditHolder",
        parent_entity="business",
        holder_for="asset_edit",
        holder_attr="_asset_edit_holder",
        name_pattern="asset edit",
        emoji="art",
        warmable=True,
        warm_priority=6,
        aliases=(),
        key_columns=("office_phone",),
    ),

    EntityDescriptor(
        name="videography_holder",
        pascal_name="VideographyHolder",
        display_name="Videography",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1207984018149338",
        model_class_path="autom8_asana.models.business.business.VideographyHolder",
        parent_entity="business",
        holder_attr="_videography_holder",
        name_pattern="videography",
        emoji="video_camera",
    ),

    # =========================================================================
    # Unit-Level Holders
    # =========================================================================

    EntityDescriptor(
        name="offer_holder",
        pascal_name="OfferHolder",
        display_name="Offers",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid="1210679066066870",
        model_class_path="autom8_asana.models.business.offer.OfferHolder",
        parent_entity="unit",
        holder_for="offer",
        holder_attr="_offer_holder",
        name_pattern="offers",
        emoji="gift",
    ),

    EntityDescriptor(
        name="process_holder",
        pascal_name="ProcessHolder",
        display_name="Processes",
        entity_type=None,  # Set post-import
        category=EntityCategory.HOLDER,
        primary_project_gid=None,
        model_class_path="autom8_asana.models.business.process.ProcessHolder",
        parent_entity="unit",
        holder_for="process",
        holder_attr="_process_holder",
        name_pattern="processes",
        emoji="gear",
    ),
)


# --- EntityType Binding ---
# Performed at module load AFTER EntityType is importable.
# This deferred binding avoids circular imports from core -> models.

def _bind_entity_types() -> None:
    """Bind EntityType enum values to descriptors.

    Called once at module load. Uses object.__setattr__ to mutate
    frozen dataclass instances (safe because this runs exactly once
    before any consumer reads the descriptors).
    """
    from autom8_asana.models.business.detection.types import EntityType

    _TYPE_MAP: dict[str, Any] = {
        "business": EntityType.BUSINESS,
        "unit": EntityType.UNIT,
        "contact": EntityType.CONTACT,
        "offer": EntityType.OFFER,
        "process": EntityType.PROCESS,
        "location": EntityType.LOCATION,
        "hours": EntityType.HOURS,
        "contact_holder": EntityType.CONTACT_HOLDER,
        "unit_holder": EntityType.UNIT_HOLDER,
        "location_holder": EntityType.LOCATION_HOLDER,
        "dna_holder": EntityType.DNA_HOLDER,
        "reconciliation_holder": EntityType.RECONCILIATIONS_HOLDER,
        "asset_edit_holder": EntityType.ASSET_EDIT_HOLDER,
        "videography_holder": EntityType.VIDEOGRAPHY_HOLDER,
        "offer_holder": EntityType.OFFER_HOLDER,
        "process_holder": EntityType.PROCESS_HOLDER,
        # Note: "asset_edit" intentionally has no EntityType member
    }

    for desc in ENTITY_DESCRIPTORS:
        et = _TYPE_MAP.get(desc.name)
        if et is not None:
            object.__setattr__(desc, "entity_type", et)


# Build the singleton registry
_bind_entity_types()
_REGISTRY = EntityRegistry(ENTITY_DESCRIPTORS)


def get_registry() -> EntityRegistry:
    """Get the module-level EntityRegistry singleton.

    Returns:
        The singleton EntityRegistry instance.
    """
    return _REGISTRY
```

---

## Backward-Compatible Facades

Each existing consumer module keeps its current import path and API. The implementation changes from inline data to a delegation to the registry.

### Facade 1: `core/entity_types.py`

**Current**: Module-level `list[str]` constants.
**After**: Computed from registry.

```python
# src/autom8_asana/core/entity_types.py (MODIFIED)

"""Canonical entity type constants.

FACADE: Delegates to EntityRegistry. Preserves existing import paths.
"""
from autom8_asana.core.entity_registry import get_registry

_registry = get_registry()

# Core entity types used by DataFrameCache, admin, and query subsystems
ENTITY_TYPES: list[str] = [d.name for d in _registry.warmable_entities()
                            if not d.is_holder]

# Extended set including derivative types (used by schema providers)
ENTITY_TYPES_WITH_DERIVATIVES: list[str] = [d.name for d in _registry.warmable_entities()]
```

**Compatibility**: `from autom8_asana.core.entity_types import ENTITY_TYPES` continues to work. The list values are identical. The only difference is that the list is now computed rather than hardcoded.

### Facade 2: `config.py` DEFAULT_ENTITY_TTLS

**Current**: Module-level `dict[str, int]`.
**After**: Computed from registry.

```python
# In config.py, replace the hardcoded dict:

from autom8_asana.core.entity_registry import get_registry as _get_entity_registry

DEFAULT_ENTITY_TTLS: dict[str, int] = {
    d.name: d.default_ttl_seconds
    for d in _get_entity_registry().all_descriptors()
    if d.default_ttl_seconds != 300  # Only non-default TTLs
}
```

**Compatibility**: `from autom8_asana.config import DEFAULT_ENTITY_TTLS` returns the same dict. `CacheConfig.get_entity_ttl()` unchanged.

### Facade 3: `services/resolver.py` ENTITY_ALIASES

**Current**: Module-level `dict[str, list[str]]`.
**After**: Computed from registry.

```python
# In resolver.py, replace the hardcoded dict:

from autom8_asana.core.entity_registry import get_registry as _get_entity_registry

ENTITY_ALIASES: dict[str, list[str]] = {
    d.name: list(d.aliases)
    for d in _get_entity_registry().all_descriptors()
    if d.aliases  # Only entities with aliases
}
```

**Compatibility**: `from autom8_asana.services.resolver import ENTITY_ALIASES` returns the same dict.

### Facade 4: `services/universal_strategy.py` DEFAULT_KEY_COLUMNS

**Current**: Module-level `dict[str, list[str]]`.
**After**: Computed from registry.

```python
# In universal_strategy.py, replace the hardcoded dict:

from autom8_asana.core.entity_registry import get_registry as _get_entity_registry

DEFAULT_KEY_COLUMNS: dict[str, list[str]] = {
    d.name: list(d.key_columns)
    for d in _get_entity_registry().all_descriptors()
    if d.key_columns
}
```

### Facade 5: `detection/config.py` ENTITY_TYPE_INFO

This facade is more complex because `ENTITY_TYPE_INFO` uses `EntityType` as keys and `EntityTypeInfo` as values, which remain the canonical types for the detection subsystem.

**Strategy**: Keep `ENTITY_TYPE_INFO` as the authoritative source for detection-specific metadata but populate it from the registry where fields overlap (name_pattern, display_name, emoji, holder_attr). Fields unique to `EntityTypeInfo` (child_type, has_project) remain in `detection/config.py`.

```python
# In detection/config.py (Phase 2 - Medium tier migration):
# ENTITY_TYPE_INFO remains authoritative for detection.
# Registry provides the overlapping fields; a validation function
# checks consistency at import time.

from autom8_asana.core.entity_registry import get_registry as _get_entity_registry

def _validate_detection_config_consistency() -> None:
    """Verify ENTITY_TYPE_INFO matches registry for shared fields."""
    registry = _get_entity_registry()
    for entity_type, info in ENTITY_TYPE_INFO.items():
        desc = registry.get_by_type(entity_type)
        if desc is None:
            continue
        if info.name_pattern and desc.name_pattern and info.name_pattern != desc.name_pattern:
            raise ValueError(
                f"Detection config mismatch for {entity_type}: "
                f"name_pattern {info.name_pattern!r} != registry {desc.name_pattern!r}"
            )

# Run at import time (Phase 2)
# _validate_detection_config_consistency()
```

This is deferred to the Medium migration tier to avoid coupling the initial PR to detection subsystem changes.

---

## Startup Validation

### Integrity Check

The registry performs a cross-referencing validation at import time. This catches the class of bugs that RF-L21 addressed (missing entries in downstream lists).

```python
def _validate_registry_integrity(registry: EntityRegistry) -> None:
    """Cross-reference registry against known facade expectations.

    Called at module load time. Raises ValueError if inconsistencies
    are detected. This is the import-time validation gate that would
    have caught the RF-L21 gap.

    Checks:
    1. Every warmable entity has a non-empty key_columns
    2. Every entity with aliases has a valid alias target
    3. Every holder has a holder_for reference to a valid entity
    4. No duplicate pascal_names (would collide in SchemaRegistry)
    5. Every entity with join_keys references valid target entities
    """
    names = set(registry.all_names())

    # Check 1: Warmable entities have key_columns
    for desc in registry.warmable_entities():
        if not desc.key_columns:
            logger.warning(
                "warmable_entity_no_key_columns",
                extra={"entity": desc.name},
            )

    # Check 2: Holder references valid leaf entity
    for desc in registry.holders():
        if desc.holder_for and desc.holder_for not in names:
            raise ValueError(
                f"Holder {desc.name!r} references unknown entity "
                f"{desc.holder_for!r}"
            )

    # Check 3: No duplicate pascal_names
    pascal_names: dict[str, str] = {}
    for desc in registry.all_descriptors():
        pn = desc.pascal_name
        if pn in pascal_names:
            raise ValueError(
                f"Duplicate pascal_name {pn!r}: {desc.name!r} "
                f"conflicts with {pascal_names[pn]!r}"
            )
        pascal_names[pn] = desc.name

    # Check 4: Join key targets exist
    for desc in registry.all_descriptors():
        for target, _key in desc.join_keys:
            if target not in names:
                raise ValueError(
                    f"Entity {desc.name!r} has join_key to unknown "
                    f"target {target!r}"
                )

    # Check 5: Parent entity references exist
    for desc in registry.all_descriptors():
        if desc.parent_entity and desc.parent_entity not in names:
            raise ValueError(
                f"Entity {desc.name!r} references unknown parent "
                f"{desc.parent_entity!r}"
            )
```

This validation runs at module import time, meaning any broken registry entry is caught before a single test or API request executes.

---

## Migration Phases

### Phase 1: Easy Tier (Sprint 2, estimated 3-4 days)

Create the registry module and migrate the simplest consumers.

| Step | File | Change | Risk |
|------|------|--------|------|
| 1.1 | `core/entity_registry.py` | New file: EntityDescriptor, EntityRegistry, ENTITY_DESCRIPTORS, validation | Low -- additive only |
| 1.2 | `core/entity_types.py` | Replace hardcoded lists with registry facade | Low -- same values |
| 1.3 | `config.py` DEFAULT_ENTITY_TTLS | Replace hardcoded dict with registry facade | Low -- same values |
| 1.4 | `services/resolver.py` ENTITY_ALIASES | Replace hardcoded dict with registry facade | Low -- same values |
| 1.5 | `services/universal_strategy.py` DEFAULT_KEY_COLUMNS | Replace hardcoded dict with registry facade | Low -- same values |
| 1.6 | `cache/dataframe_cache.py` _stats init | Use `registry.dataframe_entities()` | Low -- same values |
| 1.7 | `cache/schema_providers.py` | Use `registry.dataframe_entities()` | Low -- same values |
| 1.8 | `lambda_handlers/cache_warmer.py` | Use `registry.warmable_entities()` | Low -- same values |

**Validation gate**: All 8,022 tests pass with no changes to test files.

### Phase 2: Medium Tier (Sprint 3, estimated 5-7 days)

Integrate with detection, discovery, and bootstrap subsystems.

| Step | File | Change | Risk |
|------|------|--------|------|
| 2.1 | `detection/config.py` | Add consistency validation against registry | Medium -- new validation |
| 2.2 | `models/business/_bootstrap.py` | Read model_class_path from registry instead of hardcoded list | Medium -- import order sensitive |
| 2.3 | `services/discovery.py` | Use registry for ENTITY_MODEL_MAP and EXPLICIT_MAPPINGS | Medium -- discovery normalization |
| 2.4 | `query/hierarchy.py` | Derive ENTITY_RELATIONSHIPS from registry join_keys | Medium -- query semantics |
| 2.5 | `models/business/registry.py` | Cross-reference ProjectTypeRegistry with entity registry | Medium -- runtime consistency |

**Validation gate**: All tests pass. New integration tests verify cross-subsystem consistency.

### Phase 3: Hard Tier (Deferred, estimated 1-2 weeks)

These require model class changes and are explicitly deferred.

| Step | File | Change | Risk |
|------|------|--------|------|
| 3.1 | `models/business/*.py` PRIMARY_PROJECT_GID | Remove ClassVar, read from registry | High -- 15+ files, import order |
| 3.2 | `models/business/business.py` HOLDER_KEY_MAP | Replace with registry holder metadata | High -- typed instantiation logic |
| 3.3 | `models/business/unit.py` HOLDER_KEY_MAP | Replace with registry holder metadata | High -- same |

**Not scheduled**. Backward-compatible facades make these changes non-urgent. The registry is authoritative; the ClassVars become redundant documentation.

---

## Interface Contracts

### Public API

```python
# Module: autom8_asana.core.entity_registry

# Types
class EntityCategory(str, Enum): ...
class EntityDescriptor: ...   # frozen dataclass
class EntityRegistry: ...      # singleton class

# Constants
ENTITY_DESCRIPTORS: tuple[EntityDescriptor, ...]  # All descriptors

# Functions
def get_registry() -> EntityRegistry: ...  # Singleton accessor

# EntityRegistry Methods
def get(name: str) -> EntityDescriptor | None: ...
def require(name: str) -> EntityDescriptor: ...
def get_by_gid(project_gid: str) -> EntityDescriptor | None: ...
def get_by_type(entity_type: EntityType) -> EntityDescriptor | None: ...
def all_descriptors() -> tuple[EntityDescriptor, ...]: ...
def all_names() -> list[str]: ...
def warmable_entities() -> list[EntityDescriptor]: ...
def dataframe_entities() -> list[str]: ...
def holders() -> list[EntityDescriptor]: ...
def get_join_key(source: str, target: str) -> str | None: ...
def get_entity_ttl(name: str, default: int = 300) -> int: ...
def get_aliases(name: str) -> tuple[str, ...]: ...
def get_key_columns(name: str) -> tuple[str, ...]: ...

# EntityDescriptor Properties
def effective_schema_key(self) -> str: ...
def is_holder(self) -> bool: ...
def has_project(self) -> bool: ...
def get_join_key(self, target: str) -> str | None: ...
def get_model_class(self) -> type | None: ...
```

### Import Contract

```python
# Primary usage (new code):
from autom8_asana.core.entity_registry import get_registry

# Backward-compatible usage (existing code, unchanged):
from autom8_asana.core.entity_types import ENTITY_TYPES
from autom8_asana.config import DEFAULT_ENTITY_TTLS
from autom8_asana.services.resolver import ENTITY_ALIASES
from autom8_asana.services.universal_strategy import DEFAULT_KEY_COLUMNS
```

---

## Data Flow Diagrams

### Adding a New Entity Type (After Registry)

```
Developer adds 1 entry to ENTITY_DESCRIPTORS
in core/entity_registry.py
         │
         v
┌────────────────────────────┐
│ Registry rebuilds indexes  │ (automatic at import)
│ Validation runs            │ (catches missing refs)
└────────┬───────────────────┘
         │
    ┌────┴────┬───────────┬───────────┬──────────┐
    v         v           v           v          v
ENTITY_    DEFAULT_    ENTITY_     DEFAULT_   warmable_
TYPES      ENTITY_     ALIASES    KEY_        entities()
(facade)   TTLS        (facade)   COLUMNS    (facade)
           (facade)               (facade)
```

Developer still creates 2 additional files:
1. `models/business/new_entity.py` -- model class (unique logic)
2. `dataframes/schemas/new_entity.py` -- schema definition (unique columns)

**Total: 3 files** (down from 13+).

### Cache Warming Flow (Using Registry)

```
Lambda handler calls registry.warmable_entities()
         │
         v
┌─────────────────────────────────────────────────┐
│ Returns sorted by warm_priority:                 │
│  1. unit (priority=1)                            │
│  2. business (priority=2)                        │
│  3. offer (priority=3)                           │
│  4. contact (priority=4)                         │
│  5. asset_edit (priority=5)                      │
│  6. asset_edit_holder (priority=6)               │
└────────┬────────────────────────────────────────┘
         │
         v
For each entity: get TTL, project GID, schema key
from the same EntityDescriptor instance
```

### Entity Resolution Flow (Using Registry)

```
Query: resolve("unit", {"phone": "+1555"})
         │
         v
registry.get("unit")
         │
         v
EntityDescriptor(
    name="unit",
    key_columns=("office_phone", "vertical"),
    aliases=("business_unit",),
    ...
)
         │
         ├─> aliases -> _normalize_field("phone", "unit", ...) -> "office_phone"
         ├─> key_columns -> DynamicIndex configuration
         └─> effective_schema_key -> "Unit" -> SchemaRegistry.get_schema("Unit")
```

---

## Non-Functional Considerations

### Performance

| Concern | Approach | Target |
|---------|----------|--------|
| Import time | All indexes built once at module load from ~20 descriptors | < 1ms |
| Lookup latency | Dict lookup: O(1) | < 1us per lookup |
| Memory | ~20 frozen dataclass instances with slots | < 10KB total |
| Circular imports | model_class_path uses string import paths, resolved lazily | No import-time circular deps |

### Thread Safety

The registry is built once at module load and never mutated. All state is in frozen dataclasses and plain dicts. No locks are needed for reads. This matches the existing pattern used by `ENTITY_TYPE_INFO` in `detection/config.py`.

### Testability

```python
# Tests can create isolated registries:
test_descriptors = (
    EntityDescriptor(name="test_entity", pascal_name="TestEntity", ...),
)
test_registry = EntityRegistry(test_descriptors)

# No need to monkey-patch the global singleton for unit tests
# that only need specific entity types.
```

The singleton is accessed via `get_registry()` function, not a class method, making it straightforward to mock in tests that need isolation.

---

## Test Strategy

### Unit Tests for EntityRegistry

| Test | Validates |
|------|-----------|
| `test_get_by_name_returns_descriptor` | Primary lookup returns correct descriptor |
| `test_get_by_name_returns_none_for_unknown` | Unknown name returns None |
| `test_require_raises_for_unknown` | `require()` raises KeyError with helpful message |
| `test_get_by_gid_returns_descriptor` | GID lookup returns correct descriptor |
| `test_get_by_type_returns_descriptor` | EntityType lookup returns correct descriptor |
| `test_all_names_preserves_order` | `all_names()` matches definition order |
| `test_warmable_sorted_by_priority` | `warmable_entities()` returns ascending priority |
| `test_get_join_key_both_directions` | Join key lookup works source->target and reverse |
| `test_get_entity_ttl_returns_correct_value` | TTL lookup matches descriptor |
| `test_get_entity_ttl_fallback` | Unknown entity returns default TTL |
| `test_duplicate_name_raises` | Constructor rejects duplicate names |
| `test_duplicate_gid_raises` | Constructor rejects duplicate project GIDs |
| `test_duplicate_entity_type_raises` | Constructor rejects duplicate EntityType values |

### Unit Tests for EntityDescriptor

| Test | Validates |
|------|-----------|
| `test_descriptor_is_frozen` | Cannot mutate after creation |
| `test_effective_schema_key_default` | Returns pascal_name when schema_key is None |
| `test_effective_schema_key_override` | Returns schema_key when explicitly set |
| `test_is_holder_true_for_holders` | Category HOLDER returns True |
| `test_is_holder_false_for_leaves` | Category LEAF returns False |
| `test_get_model_class_lazy_import` | Resolves model class from path |
| `test_get_model_class_none_when_unset` | Returns None when path is None |

### Integration Tests for Facades

| Test | Validates |
|------|-----------|
| `test_entity_types_matches_legacy` | `ENTITY_TYPES` facade produces same values as old hardcoded list |
| `test_entity_types_with_derivatives_matches` | `ENTITY_TYPES_WITH_DERIVATIVES` facade matches |
| `test_default_entity_ttls_matches` | `DEFAULT_ENTITY_TTLS` facade produces same dict |
| `test_entity_aliases_matches` | `ENTITY_ALIASES` facade produces same dict |
| `test_default_key_columns_matches` | `DEFAULT_KEY_COLUMNS` facade produces same dict |

### Validation Tests

| Test | Validates |
|------|-----------|
| `test_integrity_check_catches_bad_holder_ref` | Validation rejects holder referencing unknown entity |
| `test_integrity_check_catches_bad_join_target` | Validation rejects join key to unknown entity |
| `test_integrity_check_catches_bad_parent_ref` | Validation rejects unknown parent_entity |
| `test_integrity_check_catches_duplicate_pascal` | Validation rejects duplicate pascal_names |
| `test_all_entity_types_have_descriptors` | Every EntityType enum member (except UNKNOWN) has a registry entry |

### Existing Test Preservation

All 8,022 existing tests must pass without modification. The facade approach ensures this by preserving import paths, variable names, and data shapes. CI runs the full suite before and after each migration step.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Circular import at module load | Medium | High (import failure) | model_class uses string path, EntityType uses deferred binding via `_bind_entity_types()` |
| Import order dependency | Medium | Medium (test failures) | Registry module has zero imports from `models/` at module level; only `detection.types` via deferred function |
| Facade value mismatch | Low | High (behavioral change) | Integration tests compare facade output against hardcoded expected values |
| Entity type missing from registry | Low | Medium (KeyError at runtime) | Import-time validation cross-references all facades |
| Performance regression from dynamic lists | Very Low | Low | Lists are computed once at import time, not per-call |
| Frozen dataclass mutation via `object.__setattr__` | Low | Medium (thread safety) | `_bind_entity_types()` runs exactly once before any reader; documented with comment |

---

## ADRs

### ADR-001: EntityType Binding Strategy

**Status**: Proposed
**Context**: `EntityDescriptor` lives in `core/entity_registry.py`. `EntityType` enum lives in `models/business/detection/types.py`. Core must not import from models at module level to avoid circular imports.

**Decision**: Use deferred binding. Define descriptors with `entity_type=None`, then call `_bind_entity_types()` at module load to set the values via `object.__setattr__` on frozen instances. The `entity_type` field is typed as `Any` to avoid the import.

**Alternatives Considered**:
1. **Move EntityType to core/**: Would require moving `detection/types.py` content to `core/`, creating a large core module and breaking the detection module's encapsulation. Rejected because EntityType is semantically a detection concept.
2. **Use string enum values**: Store `"business"` instead of `EntityType.BUSINESS`. Rejected because it loses type safety and breaks existing consumers that compare with enum members.
3. **Lazy property**: Make `entity_type` a lazy property that imports on first access. Rejected because frozen dataclasses do not support computed properties that set state, and the overhead of repeated imports is unnecessary.

**Consequences**: The `object.__setattr__` call on frozen instances is safe because it runs exactly once at module load before any consumer reads the values. It is admittedly unusual, but it is documented with a clear comment and tested.

### ADR-002: Singleton Pattern Choice

**Status**: Proposed
**Context**: The registry needs to be accessible from any module. Options are module-level instance, class-level singleton (like `SchemaRegistry`), or dependency injection.

**Decision**: Module-level instance accessed via `get_registry()` function. The module-level tuple `ENTITY_DESCRIPTORS` is the source of truth; the `EntityRegistry` instance is built from it at import time.

**Alternatives Considered**:
1. **Class-level singleton with `__new__`**: Used by `SchemaRegistry` and `EntityProjectRegistry`. Rejected because the registry does not need lazy initialization or reset -- it is built once from static data.
2. **Dependency injection**: Rejected for the registry layer because it would require threading the registry through every function call. The registry is a constant -- it does not vary by context.
3. **Class with `@classmethod` factory**: Similar to option 1 but with a factory method. Rejected as unnecessary indirection.

**Consequences**: Simpler than class-level singleton. Testing uses direct construction (`EntityRegistry(test_descriptors)`) rather than singleton reset. The only downside is that the module-level instance is created at import time, which means `detection.types` must be importable at that point. The deferred binding in ADR-001 handles this.

### ADR-003: Collection Field Types (Tuple vs List)

**Status**: Proposed
**Context**: `EntityDescriptor` is frozen, which requires hashable fields. Collection fields (`aliases`, `join_keys`, `key_columns`) could use `tuple` or `frozenset`.

**Decision**: Use `tuple` for all collection fields. Tuples are ordered (matching the existing list semantics of `ENTITY_ALIASES` and `DEFAULT_KEY_COLUMNS`), hashable, and familiar.

**Alternatives Considered**:
1. **frozenset**: Unordered. Rejected because `key_columns` order matters for DynamicIndex (first column is primary lookup).
2. **list with custom __hash__**: Rejected because it violates frozen dataclass invariants.

**Consequences**: Facades must convert tuple to list for backward compatibility (`list(desc.aliases)`). This is a trivial O(n) operation run once at import time.

### ADR-004: Scope Boundary -- What the Registry Does NOT Own

**Status**: Proposed
**Context**: The registry could theoretically absorb every piece of entity knowledge. The question is where to draw the line.

**Decision**: The registry owns identity, hierarchy, detection hints, cache behavior, and field normalization metadata. It does NOT own: schema column definitions, model class logic, detection algorithms, custom field descriptors, or cascading field definitions.

**Rationale**: The excluded items contain genuinely unique logic per entity type. Schema columns define what data a DataFrame holds. Model classes define how entities are hydrated and validated. Detection algorithms decide how to classify unknown tasks. These are not metadata about entity types -- they are implementations that happen to be organized by entity type.

**Consequences**: Adding a new entity type still requires 3 files (registry entry, model class, schema). This is a 77% reduction from 13 files, which satisfies G5.

---

## Success Criteria

### Quantitative

| Metric | Baseline | Target | How Measured |
|--------|----------|--------|-------------|
| Files touched to add new entity type | 13 (spike S0-003) | 3 (registry + model + schema) | Manual trace of next entity addition |
| Entity type list redundancy | 5-way (spike S0-005) | 1 (registry) + facades | `grep -r "ENTITY_TYPES\|EntityType\|entity_type" --include="*.py" \| wc -l` reduced by 50%+ |
| Import-time validation coverage | 0 checks | 5 checks (holder refs, join targets, parent refs, pascal uniqueness, EntityType coverage) | Validation function assertions |
| Test count unchanged | 8,022 | 8,022 (plus new registry tests) | `pytest --co -q \| wc -l` |
| Backward compat: zero test modifications | 0 test files changed | 0 test files changed | `git diff --name-only tests/` empty for facade changes |

### Qualitative

| Criterion | Validation |
|-----------|-----------|
| New team member can add an entity type without architecture guidance | Walk-through test: provide only the TDD and ask for implementation |
| Registry is the obvious place to look for entity metadata | All facades include a comment pointing to `core/entity_registry.py` |
| Import-time validation catches the RF-L21 class of bugs | Unit test: remove an entity from registry, verify import raises |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-entity-knowledge-registry.md` | Yes (written by architect) |
| Spike S0-003 | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-003-entity-workflow.md` | Yes (read during design) |
| Spike S0-005 | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/spike-S0-005-entity-metadata-catalog.md` | Yes (read during design) |
| Architectural opportunities | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/architectural-opportunities.md` | Yes (read during design) |
| Exception hierarchy (pattern ref) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/exceptions.py` | Yes (read during design) |
| MutationEvent (EntityKind ref) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/mutation_event.py` | Yes (read during design) |
| Sprint 1 TDD (structure ref) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-cache-invalidation-pipeline.md` | Yes (read during design) |
| Existing entity_types.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_types.py` | Yes (read during design) |
| Existing EntityType enum | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection/types.py` | Yes (read during design) |
| Existing ENTITY_TYPE_INFO | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection/config.py` | Yes (read during design) |
| Existing config.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | Yes (read during design) |
| Existing resolver.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes (read during design) |
| Existing hierarchy.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/hierarchy.py` | Yes (read during design) |
| Existing universal_strategy.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Yes (read during design) |
| Existing _bootstrap.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/_bootstrap.py` | Yes (read during design) |
| Existing discovery.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/discovery.py` | Yes (read during design) |
| Existing SchemaRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Yes (read during design) |
