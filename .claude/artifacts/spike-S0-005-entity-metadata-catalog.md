# Spike S0-005: Entity Metadata Surface Catalog

**Date**: 2026-02-04
**Spike Owner**: Architect
**Context**: Pre-design research for Opportunity B1 (Entity Knowledge Registry)
**Objective**: Complete inventory of where entity knowledge is encoded across the codebase

---

## 1. Complete Inventory Table

### 1.1 Canonical / Registry Locations

| # | File | Metadata Type | Format | What It Encodes | Update Frequency |
|---|------|---------------|--------|----------------|------------------|
| 1 | `core/entity_types.py` | Entity type list | `list[str]` (`ENTITY_TYPES`, `ENTITY_TYPES_WITH_DERIVATIVES`) | Which entity types exist; derivative types for schema providers | Rarely (new entity type) |
| 2 | `query/hierarchy.py` | Entity relationships | `list[EntityRelationship]` dataclass with parent/child/join_key | Parent-child hierarchy, default join keys for cross-entity joins | Rarely (new relationship) |
| 3 | `dataframes/models/registry.py` | Schema-to-task-type mapping | `SchemaRegistry` singleton, `dict[str, DataFrameSchema]` | PascalCase task type -> DataFrame column schema (Unit, Business, Contact, Offer, AssetEdit, AssetEditHolder) | On schema change (version bump) |
| 4 | `cache/entry.py` | Cache entry types | `EntryType(str, Enum)` with 14 members | What can be cached: task, subtasks, dependencies, dependents, stories, attachments, dataframe, project, section, user, custom_field, detection, project_sections, gid_enumeration, insights | When new cacheable resource added |
| 5 | `services/resolver.py` | Entity project config | `EntityProjectRegistry` singleton, `ENTITY_ALIASES` dict, `to_pascal_case()` conversion | Entity -> project GID mapping, field alias chains for normalization, snake_case -> PascalCase conversion | At startup (discovery) |

### 1.2 Domain Model Locations

| # | File | Metadata Type | Format | What It Encodes | Update Frequency |
|---|------|---------------|--------|----------------|------------------|
| 6 | `models/business/detection/types.py` | Entity type enum | `EntityType(Enum)` with 17 members | Complete enumeration: BUSINESS, CONTACT_HOLDER, UNIT_HOLDER, LOCATION_HOLDER, DNA_HOLDER, RECONCILIATIONS_HOLDER, ASSET_EDIT_HOLDER, VIDEOGRAPHY_HOLDER, OFFER_HOLDER, PROCESS_HOLDER, UNIT, CONTACT, OFFER, PROCESS, LOCATION, HOURS, UNKNOWN | New entity type |
| 7 | `models/business/detection/config.py` | Master entity metadata | `dict[EntityType, EntityTypeInfo]` (ENTITY_TYPE_INFO) | Per-type: name_pattern, display_name, emoji, holder_attr, child_type, has_project. Derives NAME_PATTERNS and PARENT_CHILD_MAP | New entity type or detection change |
| 8 | `models/business/detection/types.py` | Detection confidence | Float constants (CONFIDENCE_TIER_1..5) | Confidence levels per detection tier | Rarely |
| 9 | `models/business/base.py` | Base entity ClassVars | `PRIMARY_PROJECT_GID`, `NAME_CONVENTION`, `HOLDER_KEY_MAP` on BusinessEntity | Which Asana project each entity type belongs to, naming conventions, holder identification | New entity type |
| 10 | `models/business/business.py` | Business holder map | `HOLDER_KEY_MAP: dict[str, tuple[str, str]]` (7 entries) | Holder name -> (task_name, emoji) for all 7 Business-level holders | New holder type |
| 11 | `models/business/unit.py` | Unit holder map | `HOLDER_KEY_MAP: dict[str, tuple[str, str]]` (2 entries) | Offer and Process holder detection patterns | Rarely |
| 12 | `models/business/business.py` | Cascading field defs | Inner class `CascadingFields` with 4 defs | Which fields cascade from Business to descendants (OFFICE_PHONE, COMPANY_ID, BUSINESS_NAME, PRIMARY_CONTACT_PHONE) and target types | Field behavior change |
| 13 | `models/business/unit.py` | Cascading + inherited field defs | Inner classes `CascadingFields` (3), `InheritedFields` (1) | PLATFORMS, VERTICAL, BOOKING_TYPE cascade targets; DEFAULT_VERTICAL inheritance chain | Field behavior change |

### 1.3 PRIMARY_PROJECT_GID Locations (Hardcoded Asana Project GIDs)

| # | File | Entity | GID |
|---|------|--------|-----|
| 14 | `models/business/business.py` | Business | `1200653012566782` |
| 15 | `models/business/business.py` | DNAHolder | `1167650840134033` |
| 16 | `models/business/business.py` | ReconciliationHolder | `1203404998225231` |
| 17 | `models/business/business.py` | AssetEditHolder | `1203992664400125` |
| 18 | `models/business/business.py` | VideographyHolder | `1207984018149338` |
| 19 | `models/business/unit.py` | Unit | `1201081073731555` |
| 20 | `models/business/unit.py` | UnitHolder | `1204433992667196` |
| 21 | `models/business/contact.py` | Contact | `1200775689604552` |
| 22 | `models/business/contact.py` | ContactHolder | `1201500116978260` |
| 23 | `models/business/offer.py` | Offer | `1143843662099250` |
| 24 | `models/business/offer.py` | OfferHolder | `1210679066066870` |
| 25 | `models/business/location.py` | Location | `1200836133305610` |
| 26 | `models/business/location.py` | LocationHolder | `None` (no project) |
| 27 | `models/business/hours.py` | Hours | `1201614578074026` |
| 28 | `models/business/process.py` | Process | `None` (dynamic via workspace discovery) |
| 29 | `models/business/process.py` | ProcessHolder | `None` (no project) |
| 30 | `models/business/asset_edit.py` | AssetEdit | `1202204184560785` |

### 1.4 Configuration / TTL / Behavioral Locations

| # | File | Metadata Type | Format | What It Encodes | Update Frequency |
|---|------|---------------|--------|----------------|------------------|
| 31 | `config.py` | Entity TTLs | `DEFAULT_ENTITY_TTLS: dict[str, int]` | TTL per entity type: business=3600, contact=900, unit=900, offer=180, process=60, address=3600, hours=3600 | Tuning |
| 32 | `config.py` | SWR/LKG multipliers | Module-level floats | `SWR_GRACE_MULTIPLIER=3.0`, `LKG_MAX_STALENESS_MULTIPLIER=0.0` | Tuning |
| 33 | `services/resolver.py` | Entity aliases | `ENTITY_ALIASES: dict[str, list[str]]` | Field normalization chains: unit->business_unit, offer->business_offer, business->office, asset_edit->process | New alias pattern |

### 1.5 Discovery / Bootstrap / Registration Locations

| # | File | Metadata Type | Format | What It Encodes | Update Frequency |
|---|------|---------------|--------|----------------|------------------|
| 34 | `models/business/_bootstrap.py` | Bootstrap registry | `ENTITY_MODELS: list[tuple[EntityType, type]]` (16 entries) | Ordered list of (EntityType, model_class) for ProjectTypeRegistry population | New entity type |
| 35 | `models/business/registry.py` | Project-to-EntityType registry | `ProjectTypeRegistry` singleton `dict[str, EntityType]` | GID -> EntityType mapping, populated from PRIMARY_PROJECT_GID at import time | At import |
| 36 | `models/business/registry.py` | Workspace project registry | `WorkspaceProjectRegistry` singleton | Dynamic name -> GID discovery, ProcessType matching, lazy or eager discovery | At startup |
| 37 | `services/discovery.py` | Entity discovery service | `ENTITY_MODEL_MAP: dict[str, type]` (7 entries) + `_normalize_project_name()` + `EXPLICIT_MAPPINGS` | Model-select then name-normalization discovery. Contains "paid content" -> "asset_edit" mapping and pluralization rules | New entity type or naming exception |

### 1.6 Schema Definition Locations

| # | File | Metadata Type | Format | What It Encodes | Update Frequency |
|---|------|---------------|--------|----------------|------------------|
| 38 | `dataframes/schemas/base.py` | Base columns | `BASE_COLUMNS: list[ColumnDef]` | Common columns all entities share (gid, name, section, etc.) | Schema evolution |
| 39 | `dataframes/schemas/unit.py` | Unit columns | `UNIT_COLUMNS + BASE_COLUMNS -> UNIT_SCHEMA` | Unit-specific fields: mrr, weekly_ad_spend, products, etc. | Schema evolution |
| 40 | `dataframes/schemas/business.py` | Business columns | `BUSINESS_COLUMNS -> BUSINESS_SCHEMA` | Business-specific fields | Schema evolution |
| 41 | `dataframes/schemas/contact.py` | Contact columns | `CONTACT_COLUMNS -> CONTACT_SCHEMA` | Contact-specific fields | Schema evolution |
| 42 | `dataframes/schemas/offer.py` | Offer columns | `OFFER_COLUMNS -> OFFER_SCHEMA` | Offer-specific fields | Schema evolution |
| 43 | `dataframes/schemas/asset_edit.py` | AssetEdit columns | `ASSET_EDIT_COLUMNS -> ASSET_EDIT_SCHEMA` | AssetEdit-specific fields | Schema evolution |
| 44 | `dataframes/schemas/asset_edit_holder.py` | AssetEditHolder columns | `ASSET_EDIT_HOLDER_SCHEMA` | AssetEditHolder-specific fields | Schema evolution |

### 1.7 Operational / Integration Locations

| # | File | Metadata Type | Format | What It Encodes | Update Frequency |
|---|------|---------------|--------|----------------|------------------|
| 45 | `lambda_handlers/cache_warmer.py` | Warm priority list | Hardcoded `list[str]` | Default warming order: ["unit", "business", "offer", "contact", "asset_edit", "asset_edit_holder"] | New warmable entity |
| 46 | `cache/schema_providers.py` | Schema version bridge | Iterates `ENTITY_TYPES_WITH_DERIVATIVES` | Registers "asana:{entity_type}" schema providers with SDK | New entity type |
| 47 | `cache/dataframe_cache.py` | Per-entity stats | `_stats: dict[str, dict[str, int]]` initialized from `ENTITY_TYPES` | Hit/miss/build/SWR/LKG counters per entity type | New entity type |
| 48 | `models/business/sections.py` | Section GIDs | `OfferSection(str, Enum)` | Hardcoded section GID: ACTIVE="1143843662099256" for Offer project | New section |
| 49 | `metrics/definitions/offer.py` | Metric scopes | `Scope(entity_type="offer", ...)` | Entity-type-specific metric definitions with section and dedup config | New metric |
| 50 | `metrics/resolve.py` | Section resolution | `if entity_type == "offer":` branch | Entity-type-specific section resolution fallback | New entity with sections |
| 51 | `core/schema.py` | Schema version lookup | `get_schema_version()` utility | Bridges entity_type -> SchemaRegistry -> version string | N/A (utility) |
| 52 | `models/business/business.py` (descriptors) | Custom field definitions | `TextField()`, `EnumField()`, `IntField()` descriptors | Entity-specific Asana custom field mappings (13 text, 1 int, 2 enum for Business) | Field addition |
| 53 | `models/business/unit.py` (descriptors) | Custom field definitions | `TextField()`, `EnumField()`, `MultiEnumField()`, etc. | Unit-specific fields (~31 descriptors) | Field addition |

---

## 2. Overlap/Redundancy Analysis

### 2.1 Entity Type Lists (5-way redundancy)

The same "which entity types exist" knowledge is encoded in at least **5 independent locations**:

| Location | Format | Entity Types Listed |
|----------|--------|--------------------|
| `core/entity_types.ENTITY_TYPES` | `list[str]` | unit, business, offer, contact, asset_edit |
| `core/entity_types.ENTITY_TYPES_WITH_DERIVATIVES` | `list[str]` | Above + asset_edit_holder |
| `detection/types.EntityType` | `Enum` | 17 members including holders, location, hours, process, unknown |
| `_bootstrap.ENTITY_MODELS` | `list[tuple]` | 16 entries (EntityType + model class) |
| `discovery.ENTITY_MODEL_MAP` | `dict[str, type]` | 7 entries (unit, unit_holder, business, offer, contact, asset_edit, asset_edit_holder) |
| `cache_warmer.default_priority` | `list[str]` | unit, business, offer, contact, asset_edit, asset_edit_holder |
| `config.DEFAULT_ENTITY_TTLS` | `dict[str, int]` | business, contact, unit, offer, process, address, hours |

**Key observation**: Each list serves a different purpose (what to cache, what to warm, what to detect, what to resolve) but the "master list" concept is fragmented. `ENTITY_TYPES` claims to be the "single source of truth" but has only 5 entries while `EntityType` enum has 17.

### 2.2 Entity-to-Project GID Mapping (3-way redundancy)

| Location | When Populated | Scope |
|----------|---------------|-------|
| `PRIMARY_PROJECT_GID` ClassVars on 15+ model classes | Module definition time (static) | Hardcoded in source code |
| `ProjectTypeRegistry` singleton | Import time (from PRIMARY_PROJECT_GID via _bootstrap) | Runtime copy of static GIDs |
| `EntityProjectRegistry` singleton | Startup discovery (from API + model GIDs) | Runtime with discovery fallback |

All three encode the same fundamental mapping: entity type -> Asana project GID. The `ProjectTypeRegistry` is literally populated by reading `PRIMARY_PROJECT_GID` from the model classes.

### 2.3 Entity Relationship / Hierarchy (3-way redundancy)

| Location | Encodes |
|----------|---------|
| `query/hierarchy.ENTITY_RELATIONSHIPS` | Parent/child pairs with join keys (4 relationships) |
| `detection/config.ENTITY_TYPE_INFO` | `child_type` field on EntityTypeInfo (holder -> leaf entity) |
| `detection/config.PARENT_CHILD_MAP` | Derived from ENTITY_TYPE_INFO at module load |
| `Business.HOLDER_KEY_MAP` / `Unit.HOLDER_KEY_MAP` | Holder names and emojis for parent -> holder navigation |

These encode overlapping but not identical knowledge. `ENTITY_RELATIONSHIPS` captures join semantics (join key = office_phone), while detection captures containment semantics (ContactHolder contains Contact). Neither is derivable from the other.

### 2.4 Entity Name/Display Conventions (3-way redundancy)

| Location | Encodes |
|----------|---------|
| `detection/config.ENTITY_TYPE_INFO[].display_name` | "Contacts", "Business Units", "Location", etc. |
| `Business.HOLDER_KEY_MAP` / `Unit.HOLDER_KEY_MAP` | ("Contacts", "busts_in_silhouette"), ("Business Units", "package"), etc. |
| `discovery._normalize_project_name()` | "Business Units" -> "unit", "Contacts" -> "contact", pluralization rules |

### 2.5 snake_case <-> PascalCase Conversion (implicit everywhere)

The `to_pascal_case()` function in `services/resolver.py` is the only explicit converter, but the SchemaRegistry uses PascalCase keys ("Unit") while everything else uses snake_case ("unit"). This convention is implicitly assumed in at least 8 files.

### 2.6 TTL Configuration (2-way redundancy)

| Location | Encodes |
|----------|---------|
| `config.DEFAULT_ENTITY_TTLS` | Module-level dict with 7 entries |
| `config.CacheConfig.entity_ttls` | Instance-level copy (defaults to `DEFAULT_ENTITY_TTLS.copy()`) |

The `CacheConfig` docstring additionally lists entity types and their TTLs in prose form, creating a third documentation-level copy.

---

## 3. Proposed Unified Schema Sketch (Conceptual)

The goal is a single `EntityDescriptor` that captures all metadata about an entity type, so that adding a new entity type requires exactly one change.

```python
@dataclass(frozen=True)
class EntityDescriptor:
    """Complete metadata for a single entity type."""

    # Identity
    name: str                          # "unit" (snake_case canonical)
    pascal_name: str                   # "Unit" (derived or explicit)
    display_name: str                  # "Business Units" (human-readable)
    entity_type: EntityType            # EntityType.UNIT (enum)

    # Asana Project Mapping
    primary_project_gid: str | None    # "1201081073731555"
    model_class: type | None           # Unit (for hydration)

    # Hierarchy
    parent_types: list[str]            # ["business"]
    child_types: list[str]             # ["offer", "process"] (via holders)
    is_holder: bool                    # False
    holder_for: str | None             # None (or "unit" for UnitHolder)
    holder_attr: str | None            # None (or "_unit_holder")

    # Detection
    name_pattern: str | None           # "units" (Tier 2 substring match)
    emoji: str | None                  # "package" (fallback detection)

    # Schema
    schema_key: str                    # "Unit" (SchemaRegistry lookup key)
    schema: DataFrameSchema | None     # Lazy-loaded schema object

    # Cache Behavior
    default_ttl_seconds: int           # 900
    warmable: bool                     # True (included in Lambda warming)
    warm_priority: int                 # 1 (lower = higher priority)

    # Field Normalization
    aliases: list[str]                 # ["business_unit"]

    # Relationships (for query joins)
    join_keys: dict[str, str]          # {"business": "office_phone", "offer": "office_phone"}


class EntityRegistry:
    """Singleton registry: the one place to look up entity metadata."""

    _descriptors: dict[str, EntityDescriptor]  # name -> descriptor
    _gid_index: dict[str, EntityDescriptor]    # project_gid -> descriptor
    _type_index: dict[EntityType, EntityDescriptor]  # enum -> descriptor

    def get(self, name: str) -> EntityDescriptor | None: ...
    def get_by_gid(self, project_gid: str) -> EntityDescriptor | None: ...
    def get_by_type(self, entity_type: EntityType) -> EntityDescriptor | None: ...
    def all_names(self) -> list[str]: ...
    def warmable_entities(self) -> list[EntityDescriptor]: ...
    def get_join_key(self, source: str, target: str) -> str | None: ...
```

**Key design decisions in this sketch**:

1. **Static definition, runtime indexes**: Descriptors are frozen dataclasses defined in one module. Multiple indexes (by name, by GID, by EntityType) are built at import time.

2. **Replaces 5+ sources**: `ENTITY_TYPES`, `EntityType` enum, `ENTITY_TYPE_INFO`, `DEFAULT_ENTITY_TTLS`, `ENTITY_RELATIONSHIPS`, `ENTITY_ALIASES` would all be derived from or replaced by the registry.

3. **Does NOT replace**: Schema definitions themselves (ColumnDef lists), model class implementations, or detection tier logic. Those reference the registry but are not metadata about entity types.

4. **Backward compatibility**: Existing consumers (`ENTITY_TYPES`, `EntityType`, etc.) would become thin facades over the registry, not immediate deletions.

---

## 4. Estimated Effort to Consolidate

### Easy (1-2 days each)

| Location | Why Easy | Migration Path |
|----------|----------|----------------|
| `core/entity_types.ENTITY_TYPES` | Simple list, 3 consumers | Replace with `registry.all_names()` |
| `config.DEFAULT_ENTITY_TTLS` | Dict of ints, used via `CacheConfig.get_entity_ttl()` | Move TTL into EntityDescriptor, keep `get_entity_ttl()` as facade |
| `services/resolver.ENTITY_ALIASES` | Dict, 1 consumer (_apply_legacy_mapping) | Move aliases into EntityDescriptor |
| `cache_warmer.default_priority` | Hardcoded list, 1 consumer | `registry.warmable_entities()` sorted by priority |
| `cache/dataframe_cache._stats` init | Iterates ENTITY_TYPES | `registry.all_names()` |
| `cache/schema_providers.register_asana_schemas` | Iterates ENTITY_TYPES_WITH_DERIVATIVES | `registry.all_names()` (filter warmable or schema-bearing) |

### Medium (3-5 days each)

| Location | Why Medium | Migration Path |
|----------|-----------|----------------|
| `query/hierarchy.ENTITY_RELATIONSHIPS` | Used by join engine, has semantic content (join keys) beyond simple listing | Move join_keys into EntityDescriptor, keep `find_relationship()` as facade |
| `detection/config.ENTITY_TYPE_INFO` | 17-entry master config, drives NAME_PATTERNS and PARENT_CHILD_MAP derivation | Replace with EntityDescriptor fields; derive the same maps |
| `detection/types.EntityType` enum | Referenced in ~30 files | Keep enum (it is the identity type), but populate from registry rather than being authoritative |
| `_bootstrap.ENTITY_MODELS` + `ProjectTypeRegistry` | Import-order-sensitive bootstrap with 16 entries | Registry replaces both; model classes reference registry descriptors |
| `services/discovery.ENTITY_MODEL_MAP` | Startup discovery with normalization logic | Use registry descriptors for model class lookup; normalization rules move into descriptor |

### Hard (1-2 weeks each)

| Location | Why Hard | Migration Path |
|----------|----------|----------------|
| `PRIMARY_PROJECT_GID` ClassVars on 15+ model classes | Deeply integrated into model class definitions, used by detection, bootstrap, and discovery | Keep ClassVar on models for backward compat, but registry becomes authoritative. Migration: remove ClassVar references one subsystem at a time |
| `Business.HOLDER_KEY_MAP` / `Unit.HOLDER_KEY_MAP` | Used in `_identify_holder()` and `_create_typed_holder()` with if/elif chains | Registry provides holder detection data, but the typed instantiation logic in `_create_typed_holder()` is entity-specific. Would need a factory pattern or class reference in descriptor |
| `dataframes/schemas/*.py` (6 files) | Each schema is a detailed ColumnDef list tightly coupled to its entity | Schemas remain separate files but registry provides the lookup path. SchemaRegistry becomes a thin index over registry |
| `models/business/*.py` custom field descriptors | 50+ descriptors across Business, Unit, Contact, Offer define Asana custom field mappings | These are implementation details, not entity metadata. Do NOT consolidate. Registry only needs to know schema_key for lookup |

---

## 5. Summary Findings

### Scale of the Problem

- **53+ distinct locations** encode entity-type-specific knowledge
- **5-way redundancy** on the basic "which entity types exist" question
- **3-way redundancy** on entity-to-project-GID mapping
- **15+ hardcoded Asana GIDs** scattered across model class definitions
- **7+ independent lists** that must all be updated when adding a new entity type

### Risk Assessment

Adding a new entity type today requires touching:
1. `core/entity_types.py` (2 lists)
2. `dataframes/schemas/new_entity.py` (new file)
3. `dataframes/models/registry.py` (import + registration)
4. `models/business/new_entity.py` (new model class with PRIMARY_PROJECT_GID)
5. `models/business/_bootstrap.py` (add to ENTITY_MODELS)
6. `models/business/__init__.py` (export)
7. `detection/config.py` (ENTITY_TYPE_INFO entry)
8. `detection/types.py` (EntityType enum member)
9. `config.py` (DEFAULT_ENTITY_TTLS entry)
10. `services/discovery.py` (ENTITY_MODEL_MAP entry, possibly normalization rule)
11. `query/hierarchy.py` (if it has relationships)
12. `lambda_handlers/cache_warmer.py` (if warmable)
13. `services/resolver.py` (ENTITY_ALIASES if it has aliases)

That is **13 files minimum** for a new entity type. A unified registry would reduce this to **3 files**: the registry definition, the schema file, and the model class.

### Recommendation

Proceed with B1 (Entity Knowledge Registry) design. The spike confirms the problem is real, quantifiable, and the consolidation path is clear. The "easy" tier alone (6 locations, ~8 days total) would eliminate the most dangerous redundancy -- the entity type lists that must stay in sync. The "medium" tier brings in the detection and discovery subsystems. The "hard" tier (model ClassVars and holder maps) can be deferred or done incrementally since backward-compatible facades make the migration non-breaking.
