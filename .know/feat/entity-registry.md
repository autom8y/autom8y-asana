---
domain: feat/entity-registry
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/core/entity_registry.py"
  - "./src/autom8_asana/core/project_registry.py"
  - "./src/autom8_asana/core/registry_validation.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# EntityRegistry (Descriptor-Driven Entity Metadata)

## Purpose and Design Rationale

The EntityRegistry is the **single source of truth** for all entity-type metadata in the autom8y-asana system. Before it existed, knowledge about each business entity was scattered across multiple files: hardcoded `match/case` branches in extractors, explicit imports in `SchemaRegistry`, scattered constants in `config.py`, and separate TTL dicts. The registry solves this by requiring that **adding a new entity type means adding exactly one entry** to `ENTITY_DESCRIPTORS`.

All downstream subsystems (SchemaRegistry auto-discovery, extractor resolution, cache TTL lookup, warm ordering, join key resolution) derive their behavior from that single declaration. This is enforced at module load time via an 8-check integrity validator.

The feature addresses three recurring failure modes: RF-L21 (entity gap not caught until runtime), SCAR-005/006 (cascade fields null due to warm ordering violation), and copy-paste bugs when adding entities to multiple independent registries.

## Conceptual Model

### Entity Category Hierarchy

| Category | Members | Description |
|---|---|---|
| ROOT | `business` | Top of hierarchy; cascade origin for `office_phone` |
| COMPOSITE | `unit` | Has nested holder children |
| LEAF | `contact`, `offer`, `asset_edit`, `process_*` (9 pipelines), `location`, `hours` | Terminal data entities |
| HOLDER | `contact_holder`, `unit_holder`, `offer_holder`, etc. (9 holders) | Asana project containers |
| OBSERVATION | `stage_transition` | Virtual/computed entities with no Asana project |

### The Descriptor

`EntityDescriptor` is a **frozen dataclass** (slots, immutable) capturing metadata across seven concerns: Identity, Asana Project, Hierarchy, Cache Behavior, Field Normalization, DataFrame Layer, and Discovery. Descriptors are frozen for thread safety and hashability. The one exception is `entity_type`, patched via `object.__setattr__` during `_bind_entity_types()` at module load.

### Registry Indexes

| Index | Key | Query Method | Complexity |
|---|---|---|---|
| `_by_name` | snake_case name | `get(name)`, `require(name)` | O(1) |
| `_by_gid` | Asana project GID | `get_by_gid(gid)` | O(1) |
| `_by_type` | `EntityType` enum | `get_by_type(entity_type)` | O(1) |

### Import-Time Validation (8 Checks)

`_validate_registry_integrity()` enforces structural invariants at module load: holder references registered, no duplicate pascal_names, join key targets registered, parent references registered, dotted path syntax valid, schema-extractor-row triad consistency.

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/core/entity_registry.py` | `EntityDescriptor`, `EntityRegistry`, `ENTITY_DESCRIPTORS` (28 entries), `_bind_entity_types()`, `_validate_registry_integrity()` |
| `src/autom8_asana/core/project_registry.py` | Flat constant store for project GIDs; `get_project_gid()`, `get_project_name()` |
| `src/autom8_asana/core/registry_validation.py` | Cross-registry consistency checks run at API startup and Lambda bootstrap |
| `src/autom8_asana/core/entity_types.py` | Facade: `ENTITY_TYPES` list derived from `registry.warmable_entities()` |

**28 registered entities**: 15 warmable (business, unit, offer, contact, asset_edit, asset_edit_holder, 9 process pipelines), 13 non-warmable (holders, location, hours, stage_transition).

**Test coverage**: `tests/unit/core/test_entity_registry.py`, `test_project_registry.py`, `test_registry_validation.py`.

## Boundaries and Failure Modes

### Consumers

The registry is imported by virtually every domain module: dataframes (schema auto-discovery), cache (TTL lookup, warm ordering), query (join keys), persistence (cascade fields), services (entity operations), API startup (cross-registry validation).

### Structural Constraints

- **Warm ordering is safety-critical**: `warm_priority` determines cascade field extraction order. Violating it reproduces SCAR-005/006.
- **Circular import barrier**: Descriptors store dotted paths (strings) instead of importing classes directly.
- **Three independent GID registries**: EntityRegistry, ProjectTypeRegistry, and `PIPELINE_TYPE_BY_PROJECT_GID` are cross-checked only by `registry_validation.py`.
- **`strict_triad_validation=True` in production**: Schema without extractor raises `ValueError` at module load.

## Knowledge Gaps

1. **Pipeline entity `entity_type` field**: The 9 `process_*` pipeline entities may not have `entity_type` bound.
2. **`process` entity dynamic GID mechanism**: `primary_project_gid=None` -- runtime resolution not traced.
3. **`ConsultationType` gap**: Missing from entity registry per design-constraints.md.
4. **`_discover_entity_projects` fail-fast scope**: Whether it applies to all entities or only those without static GIDs.
