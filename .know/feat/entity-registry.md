---
domain: feat/entity-registry
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/core/entity_registry.py"
  - "./src/autom8_asana/core/project_registry.py"
  - "./src/autom8_asana/core/registry_validation.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# EntityRegistry (Descriptor-Driven Entity Metadata)

## Purpose and Design Rationale

The EntityRegistry is the **single source of truth** for all entity-type metadata in the
autom8y-asana system. Before it existed, knowledge about each business entity was scattered
across multiple files: hardcoded `match/case` branches in extractors, explicit imports in
`SchemaRegistry`, scattered constants in `config.py`, and separate TTL dicts. The registry
solves this by requiring that **adding a new entity type means adding exactly one entry**
to `ENTITY_DESCRIPTORS`.

All downstream subsystems — SchemaRegistry auto-discovery, extractor resolution, cache TTL
lookup, warm ordering, join key resolution, cascading field discovery — derive their behavior
from that single declaration. This is enforced at module load time via an 8-check integrity
validator (`_validate_registry_integrity`).

The feature addresses three recurring failure modes:
- **RF-L21** — entity gap not caught until runtime (import-time validation now closes this)
- **SCAR-005/006** — cascade fields null due to warm ordering violation
- Copy-paste bugs when adding entities to multiple independent registries

**Design reference**: `TDD-ENTITY-REGISTRY-001` (defines the three-class contract:
`EntityDescriptor`, `EntityRegistry`, `ENTITY_DESCRIPTORS`). `ADR-S4-001` explains why
DataFrame schemas remain separate files rather than being generated from descriptor metadata.
`ADR-001` authorizes `object.__setattr__()` for the deferred EntityType binding pattern.

## Conceptual Model

### Entity Category Hierarchy

| Category | Members (27 total) | Description |
|---|---|---|
| ROOT | `business` (1) | Top of hierarchy; cascade origin for `office_phone` |
| COMPOSITE | `unit` (1) | Has nested holder children; cascade origin for `vertical` |
| LEAF | `contact`, `offer`, `asset_edit`, `process`, `process_sales`, `process_outreach`, `process_onboarding`, `process_implementation`, `process_month1`, `process_retention`, `process_reactivation`, `process_account_error`, `process_expansion`, `location`, `hours` (15) | Terminal data entities |
| HOLDER | `contact_holder`, `unit_holder`, `location_holder`, `dna_holder`, `reconciliation_holder`, `asset_edit_holder`, `videography_holder`, `offer_holder`, `process_holder` (9) | Asana project containers anchored to a parent entity |
| OBSERVATION | `stage_transition` (1) | Virtual/computed; no Asana project; uses StageTransitionStore (parquet-based), not the standard DataFrame pipeline |

### The Descriptor

`EntityDescriptor` is a **frozen dataclass** (`@dataclass(frozen=True, slots=True)`) capturing
metadata across seven concern groups:

| Group | Fields |
|---|---|
| Identity | `name`, `pascal_name`, `display_name`, `entity_type`, `category` |
| Asana Project | `primary_project_gid`, `model_class_path` |
| Hierarchy | `parent_entity`, `holder_for`, `holder_attr` |
| Detection | `name_pattern`, `emoji`, `explicit_name_mappings` |
| Cache Behavior | `schema_key`, `default_ttl_seconds`, `warmable`, `warm_priority` |
| Field Normalization | `aliases`, `join_keys`, `key_columns` |
| DataFrame Layer | `schema_module_path`, `extractor_class_path`, `row_model_class_path`, `cascading_field_provider`, `custom_field_resolver_class_path` |

**GAP-006 (order dependency)**: Descriptors are frozen, but `entity_type` is set to `None` at
definition time and patched via `object.__setattr__(desc, "entity_type", et)` inside
`_bind_entity_types()`. This runs once at module load, before any consumer reads the
descriptors. The 9 pipeline process entities (`process_sales` through `process_expansion`)
intentionally omit `entity_type` entirely — they have no `EntityType` enum value and are
not in the `_TYPE_MAP`.

**GAP-007 (circular import workaround)**: `entity_type: Any = None` rather than
`entity_type: EntityType | None` because `EntityType` lives in `autom8_asana.core.types`
(which is reachable from the models layer). A direct import at module level would create a
`core → models` circular dependency. Deferred import inside `_bind_entity_types()` breaks
the cycle.

### Registry Indexes

| Index | Key Type | Build-Time Source | Query Method | Complexity |
|---|---|---|---|---|
| `_by_name` | snake_case `str` | `d.name` for all descriptors | `get(name)`, `require(name)` | O(1) |
| `_by_gid` | Asana project GID `str` | `d.primary_project_gid` (non-None only) | `get_by_gid(gid)` | O(1) |
| `_by_type` | `EntityType` enum | `d.entity_type` (non-None only) | `get_by_type(entity_type)` | O(1) |

`require(name)` raises `KeyError` with full available-names list. Duplicate names, GIDs, or
EntityTypes at build time raise `ValueError` immediately (constructor-level guard).

### Import-Time Validation (8 Checks)

`_validate_registry_integrity()` enforces structural invariants at module load. Fails with
`ValueError` (startup failure) on hard violations:

| Check | Type | Trigger |
|---|---|---|
| 1 | WARNING only | Warmable entity has no `key_columns` |
| 2 | ERROR | Holder `holder_for` references unknown entity name |
| 3 | ERROR | Duplicate `pascal_name` |
| 4 | ERROR | `join_keys` target not in registry |
| 5 | ERROR | `parent_entity` not in registry |
| 6a/6b/6c | ERROR | Schema/extractor/row_model path invalid dotted-path syntax |
| 6d | ERROR (strict) or WARNING | `schema_module_path` set but `extractor_class_path` absent |
| 6e | WARNING | `schema_module_path` set but `row_model_class_path` absent |
| 6f | ERROR | `extractor_class_path` set but `schema_module_path` absent |
| 7 | ERROR | `cascading_field_provider=True` but no `model_class_path` |
| 8 | ERROR | `custom_field_resolver_class_path` invalid dotted-path syntax |

**LBC-001**: The singleton is built with `strict_triad_validation=True` in production. Import
failure = startup failure for all entity-typed routes and all dataframe strategies.

Checks 6a–6c validate **path syntax only** at import time. Actual import resolution is
deferred to test time (`TestDataFramePathResolution` in `test_entity_registry.py`) because
importing `dataframes/` sub-packages triggers `dataframes/__init__.py` → builders → config →
`entity_registry` (circular).

### Warm Ordering Invariant

`warmable_entities()` returns warmable descriptors sorted by `warm_priority` (ascending). The
ordering is safety-critical: a cascade source entity must warm before any cascade consumer.

```
business (1) -> unit (2) -> offer (3) -> contact (4)
                                      -> asset_edit (5)
                                      -> asset_edit_holder (6)
                        pipeline entities (10-18)
```

Violating this ordering reproduces SCAR-005/006 conditions (CascadingFieldResolver null rate).

## Implementation Map

### Files

| File | Role |
|---|---|
| `src/autom8_asana/core/entity_registry.py` | `EntityDescriptor` frozen dataclass, `EntityRegistry` singleton, `ENTITY_DESCRIPTORS` tuple (27 entries), `_bind_entity_types()`, `_validate_registry_integrity()`, `get_registry()`, `_reset_entity_registry()` |
| `src/autom8_asana/core/project_registry.py` | Flat constant store for all Asana project GIDs. `get_project_gid(logical_name)`, `get_project_name(gid)`, `all_project_gids()`, `all_pipeline_project_gids()`, `all_entity_project_gids()`. Also has `_REGISTRY` dict and `_REVERSE_REGISTRY` for O(1) lookups in both directions. |
| `src/autom8_asana/core/registry_validation.py` | `validate_cross_registry_consistency()` — deferred cross-registry check run at API lifespan startup and Lambda bootstrap. Validates `EntityRegistry` against `ProjectTypeRegistry`, `EntityProjectRegistry`, and `PIPELINE_TYPE_BY_PROJECT_GID`. |

### Project Registry (project_registry.py)

Contains **23 constants** grouped in two sections:
- **Entity projects** (14): BUSINESS, UNIT, UNIT_HOLDER, OFFER, OFFER_HOLDER, CONTACT, CONTACT_HOLDER, ASSET_EDIT, ASSET_EDIT_HOLDER, LOCATION, HOURS, DNA_HOLDER, RECONCILIATION_HOLDER, VIDEOGRAPHY_HOLDER
- **Pipeline projects** (9): SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION, ACCOUNT_ERROR, EXPANSION, ACTIVATION_CONSULTATION

`ACTIVATION_CONSULTATION_PROJECT` = `"1209247943184021"` is the `process_month1` pipeline
("Activation Consultation" display name). The descriptor name `process_month1` diverges from
the display name; agents adding pipelines must use the constant, not hardcode GIDs.

**TENSION-005**: 15+ entity classes in `models/business/*.py` still carry their own
`PRIMARY_PROJECT_GID` class attributes that duplicate values from `project_registry.py`.
Parity is enforced by `tests/unit/core/test_project_registry.py:313`. No migration planned.

### Cross-Registry Validation (registry_validation.py)

`validate_cross_registry_consistency()` accepts three boolean flags (defaulting `True`) to
control which checks fire:

| Flag | Registry Checked | Lambda context |
|---|---|---|
| `check_project_type_registry` | `ProjectTypeRegistry` in `models/business/registry.py` | Both API + Lambda |
| `check_entity_project_registry` | `EntityProjectRegistry` in `services/resolver.py` | API only (set False for Lambda — not populated at bootstrap) |
| `check_pipeline_type_registry` | `PIPELINE_TYPE_BY_PROJECT_GID` in `services/gid_push.py` | Both |

Per **ADR-pipeline-stage-aggregation**: `PIPELINE_TYPE_BY_PROJECT_GID` uses bare names
(e.g., `"sales"`) while EntityRegistry uses `"process_{name}"` (e.g., `"process_sales"`).
The validation accepts both forms (`entity_name == pipeline_type` or
`entity_name == f"process_{pipeline_type}"`).

### Entry Point

```python
from autom8_asana.core.entity_registry import get_registry

registry = get_registry()
desc = registry.get("unit")                       # by name
desc = registry.get_by_gid("1201081073731555")    # by GID
desc = registry.get_by_type(EntityType.UNIT)      # by enum
warmable = registry.warmable_entities()           # ordered list
```

### Test Coverage

- `tests/unit/core/test_entity_registry.py` — `EntityDescriptor` unit tests, `EntityRegistry`
  construction + lookup, backward-compat facades, `_validate_registry_integrity` error cases,
  `TestDataFramePathResolution` (import resolution at test time)
- `tests/unit/core/test_project_registry.py` — constant values, `get_project_gid`,
  `get_project_name`, pipeline GID list, parity vs entity class `PRIMARY_PROJECT_GID` (line 313)
- `tests/unit/core/test_registry_validation.py` — cross-registry consistency checks

### Backward-Compatible Facades

The module docstring lists four facades that delegate to registry:
- `ENTITY_TYPES` (from `entity_types.py`) — derived from `registry.warmable_entities()`
- `DEFAULT_ENTITY_TTLS` — derived from `default_ttl_seconds` per descriptor
- `ENTITY_ALIASES` — derived from `aliases` per descriptor
- `DEFAULT_KEY_COLUMNS` — derived from `key_columns` per descriptor

**LBC-002**: `ENTITY_DESCRIPTORS` is the load-bearing tuple. Safe refactoring requires
replacing it with a registry factory and migrating all descriptor references.

## Boundaries and Failure Modes

### Scope: What EntityRegistry Does NOT Do

- Does **not** perform live Asana API validation of GIDs — GIDs are compile-time constants
- Does **not** manage entity model instances (lifecycle, hydration) — those live in `services/`
- Does **not** drive Asana project *discovery* — `EntityProjectRegistry` in `services/resolver.py`
  handles workspace-based dynamic discovery
- Does **not** store pipeline stage or section definitions — `lifecycle_stages.yaml` and
  `reconciliation/section_registry.py` own those
- Does **not** cover `ConsultationType` — per design-constraints GAP area, this type is absent
  from the entity registry

### SCAR-001: Missing PRIMARY_PROJECT_GID Silent Collision

Historical scar. An entity/holder class without `PRIMARY_PROJECT_GID` caused silent resolution
collision at runtime. The EntityRegistry design directly addresses this by requiring
`primary_project_gid` to be declared in `ENTITY_DESCRIPTORS` at import time. Regression test
ensures all entity classes that have `PRIMARY_PROJECT_GID` match the registry value
(`test_project_registry.py:313`).

Agent rule: new entity/holder classes must define `PRIMARY_PROJECT_GID` (per scar-tissue
`principal-engineer`/`architect` columns for SCAR-001).

### Three Independent GID Registries

The system has three independent GID registries cross-checked only by `registry_validation.py`:

1. `EntityRegistry` — entity metadata with GIDs from `project_registry.py`
2. `ProjectTypeRegistry` (`models/business/registry.py`) — GID → EntityType mapping used by
   detection/bootstrap
3. `PIPELINE_TYPE_BY_PROJECT_GID` (`services/gid_push.py`) — pipeline GID → type used by
   the GID-push service

Divergence between these is a **silent failure** path at startup. `validate_cross_registry_consistency()`
is the only cross-check, and it fires at lifespan/bootstrap time.

### Warm Ordering Violation Path

`warmable_entities()` sorts by `warm_priority`. Any entity that depends on cascade fields from
a parent entity **must** have a `warm_priority` number strictly greater than the parent's.
Violating this reproduces SCAR-005/006 (CascadingFieldResolver 30% null rate on units).
The current safe ordering is documented in `warmable_entities()` docstring (lines 306–333).

### `process` Entity Without GID

`process` (bare, non-pipeline) has `primary_project_gid=None` — dynamic workspace discovery
path. Its `default_ttl_seconds=60` is significantly shorter than other entities (300–3600s),
suggesting freshness concerns with dynamic discovery.

### Error Path Summary

| Condition | Error | Where Raised |
|---|---|---|
| Unknown entity name | `KeyError` with available-names list | `registry.require(name)` |
| Duplicate name at build | `ValueError` | `EntityRegistry.__init__` |
| Duplicate GID at build | `ValueError` | `EntityRegistry.__init__` |
| Duplicate EntityType at build | `ValueError` | `EntityRegistry.__init__` |
| Triad/structural violation | `ValueError` | `_validate_registry_integrity()` at module load |
| Invalid dotted path (syntax) | `ValueError` | `_validate_registry_integrity()` at module load |
| Invalid dotted path (import) | `ImportError` | `_resolve_dotted_path()` at first use |

### Test Reset Isolation

`_reset_entity_registry()` is registered with `SystemContext.reset_all()` to rebuild the
singleton between tests. Without this, EntityType bindings leak between test cases.

```metadata
source_files_read: 3
entity_count: 27
warmable_count: 15
pipeline_entity_count: 9
holder_count: 9
validation_checks: 8
test_files: 3
scars_referenced: SCAR-001, SCAR-005, SCAR-006
lbc_constraints: LBC-001, LBC-002
gap_constraints: GAP-006, GAP-007
tensions: TENSION-005
confidence_basis: full source read of all 3 implementation files + design-constraints + scar-tissue cross-reference
```
