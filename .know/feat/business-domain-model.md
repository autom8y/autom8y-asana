---
domain: feat/business-domain-model
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/business/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.96
format_version: "1.0"
---

# Business Domain Entity Model

## Purpose and Design Rationale

The Business Domain Entity Model maps Asana's project/task/subtask tree into a typed Python object
hierarchy representing real-world business client data. It transforms raw Asana task records into
domain-meaningful entities with bidirectional navigation, typed custom field access, cascading field
propagation, and full upward/downward hydration.

### Problem Solved

Asana stores business client data as nested tasks. Without a domain model, every consumer would
repeat the same structural interpretation: which task is the "Business" root, which subtask is the
"Contacts holder", how to reach a Business from an Offer four levels down. The domain model
encapsulates all of this interpretation, so callers work with typed entities (Business, Unit, Offer,
etc.) rather than generic Task dicts.

### Key Design Decisions

- **ADR-0050**: Holder lazy loading with prefetch support — holder subtasks are fetched on demand,
  not eagerly on Business construction.
- **ADR-0052**: Cached bidirectional references with explicit invalidation — PrivateAttr caches
  plus `_invalidate_refs()` prevent stale navigation.
- **ADR-0054**: `CascadingFieldDef` / `InheritedFieldDef` patterns — fields flow downward
  (`allow_override=False` default: parent always wins) or are resolved by walking the parent chain.
- **ADR-0075/0076**: `ParentRef[T]` + `HolderRef[T]` navigation descriptors — replace ~800 LOC of
  `@property` boilerplate with a two-class descriptor pattern. Auto-invalidation on write.
- **ADR-0077**: Descriptors declared WITHOUT type annotations to avoid Pydantic v2 treating them
  as model fields. `extra="allow"` on `BusinessEntity` is load-bearing for descriptor `__set__`.
- **ADR-0081/0082**: `CustomFieldDescriptor[T]` hierarchy with `__set_name__` auto-derivation of
  Asana field names. Inner `Fields` class auto-generated from registered descriptors at class
  definition time via `_pending_fields` two-phase registry.
- **ADR-0083**: `DateField` uses Arrow library for timezone-aware date handling.
- **ADR-0093/TDD-DETECTION**: `ProjectTypeRegistry` singleton for O(1) project GID → EntityType
  lookup. Backed by `_bootstrap.py` explicit startup registration.
- **ADR-0108/0109**: `WorkspaceProjectRegistry` wraps static registry with dynamic pipeline
  project discovery for `Process` entities whose `PRIMARY_PROJECT_GID` is None.
- **ADR-0116**: All pipeline fields on a single `Process` class (composition over subclassing) —
  accessing a field that does not exist on the underlying Asana task returns None.
- **ADR-0119**: Coarse-grained mixins (`SharedCascadingFieldsMixin`, `FinancialFieldsMixin`,
  `UpwardTraversalMixin`, `UnitNavigableEntityMixin`, `UnitNestedHolderMixin`) for DRY field
  consolidation across entities.
- **TDD-registry-consolidation**: Registration moved from `__init_subclass__` to explicit
  `_bootstrap.py:register_all_models()` to eliminate import-order-dependent behavior.
- **TDD-PATTERNS-C**: `HolderFactory` base class reduces ~70 LOC of boilerplate per holder to 3-5
  lines using Python `__init_subclass__` keyword argument pattern.

### Tradeoffs Accepted

- `extra="allow"` on `BusinessEntity` allows arbitrary attribute writes — required for descriptor
  `__set__` but bypasses Pydantic's strict field validation.
- Dynamic import in `HolderFactory._populate_children` (deferred via `importlib`) avoids circular
  imports at class definition time at the cost of a runtime import on first use.
- `Process.PRIMARY_PROJECT_GID = None` is intentional — pipeline projects are dynamic; static GIDs
  do not exist.

---

## Conceptual Model

### Entity Hierarchy

```
Business (root, PRIMARY_PROJECT_GID: "1200653012566782")
  +-- ContactHolder       → Contact (0..N)
  +-- UnitHolder          → Unit (0..N)
  |     +-- OfferHolder   → Offer (0..N)
  |     +-- ProcessHolder → Process (0..N)   [no PRIMARY_PROJECT_GID — dynamic discovery]
  +-- LocationHolder      → Location (0..N), Hours (0..1)
  +-- DNAHolder           → DNA (0..N)
  +-- ReconciliationHolder → Reconciliation (0..N)
  +-- AssetEditHolder     → AssetEdit (0..N)
  +-- VideographyHolder   → Videography (0..N)
```

### Entity vs Holder Distinction

- **Entities** (`Business`, `Unit`, `Contact`, `Offer`, `Process`, `Location`, `Hours`,
  `AssetEdit`, `DNA`, `Reconciliation`, `Videography`) extend `BusinessEntity(Task)`.
- **Holders** (`ContactHolder`, `UnitHolder`, `OfferHolder`, `ProcessHolder`, `LocationHolder`,
  `DNAHolder`, `ReconciliationHolder`, `AssetEditHolder`, `VideographyHolder`) extend
  `HolderFactory(Task, HolderMixin[Task])`. Holders are Asana subtasks that group children
  under a parent entity. They are NOT `BusinessEntity` subclasses.

### Custom Field Descriptor DSL (740 LOC — `descriptors.py`)

Eight typed `CustomFieldDescriptor[T]` subclasses provide declarative property access to Asana
custom fields:

| Class | Return Type | Notes |
|---|---|---|
| `TextField` | `str \| None` | Coerces non-strings to str |
| `PhoneTextField` | `str \| None` | E.164 normalization on read via `PhoneNormalizer` (SCAR-020/023 fix) |
| `EnumField` | `str \| None` | Extracts `name` from `{"gid": ..., "name": ...}` dict |
| `MultiEnumField` | `list[str]` | Extracts names from list-of-dicts; never None |
| `NumberField` | `Decimal \| None` | Precision-safe; writes float to API |
| `IntField` | `int \| None` | Truncates on read |
| `PeopleField` | `list[dict[str, Any]]` | Returns list of Asana user dicts |
| `DateField` | `Arrow \| None` | Parses ISO 8601; serializes YYYY-MM-DD on write |

Two navigation descriptor types:

| Class | Purpose |
|---|---|
| `ParentRef[T]` | Cached upward navigation with lazy resolution. `holder_attr` enables resolving Business via holder when direct cache is None. Auto-invalidates sibling refs on write (ADR-0076). |
| `HolderRef[T]` | Direct holder reference, no lazy resolution. Triggers invalidation on change. |

**Critical constraint**: Descriptors must be declared WITHOUT type annotations. The `BusinessEntity`
`model_config` sets `ignored_types=(ParentRef, HolderRef, CustomFieldDescriptor, ...)` and
`extra="allow"`. Violating either causes Pydantic to treat descriptors as model fields or silently
drop `__set__` calls.

Field name derivation: `company_id` → `"Company ID"`, `mrr` → `"MRR"` (ABBREVIATIONS
frozenset preserves known abbreviations as uppercase). Explicit `field_name=` overrides.

`Fields` inner class auto-generated per entity via `_pending_fields` two-phase registry: populated
during `__set_name__` (class definition), consumed during `BusinessEntity.__init_subclass__`.
Mixin fields are collected by walking `__mro__` (not popped, since mixins serve multiple entities).

### Cascading Field System (`fields.py`)

`CascadingFieldDef` (frozen dataclass) declares fields that flow downward from parent to
descendants:
- `allow_override=False` (DEFAULT): parent always overwrites descendant — safe direction
- `allow_override=True`: only overwrites if descendant value is None (opt-in override)
- `target_types: set[str] | None` — None = all descendants; set = named entity types only
- `source_field` — maps from model attribute (e.g., `"name"`) instead of custom field

`InheritedFieldDef` (frozen dataclass) resolves fields by walking a parent chain at access time,
with optional local override checked first.

`get_cascading_field_registry()` — lazy singleton `dict[str, (owner_class, CascadingFieldDef)]`
built from EntityRegistry descriptors where `cascading_field_provider=True`. Case-insensitive
normalized keys.

`STANDARD_TASK_OPT_FIELDS` and `DETECTION_OPT_FIELDS` — tuple constants defining Asana API
opt_fields for hydration vs detection-only fetches respectively. Single source of truth per
FR-FIELDS-001.

### Hydration Modes

**Downward hydration** (`Business.from_gid_async(client, gid, hydrate=True)`): Fetches Business
task, identifies holder subtasks, concurrently fetches each holder's children. For Units,
recursively fetches nested OfferHolder and ProcessHolder children.

**Upward traversal + downward hydration** (`hydrate_from_gid_async(client, any_gid)`): Generic
entry point. Detects entity type, traverses parent chain to Business root (max depth 10, cycle
detection), then performs downward hydration. Returns `HydrationResult` with per-branch success/
failure tracking and `is_complete` property.

**Partial failure mode** (`partial_ok=True`): Continues on hydration errors, returns partially
populated Business. `HydrationResult.failed` lists `HydrationFailure` entries with
`recoverable` flag (True for rate limits, timeouts, 5xx; False for 404/403).

**`to_business_async(client)`** (UpwardTraversalMixin): Per-entity convenience method. After
hydration, calls `_update_refs_from_hydrated_business(business)` hook to update entity-local
cached refs.

### Registry and Bootstrap

`ProjectTypeRegistry` (singleton): O(1) GID → EntityType dict lookup. Populated by
`_bootstrap.py:register_all_models()` called once at startup (`entrypoint.py` → `bootstrap()` and
`api/lifespan.py` step 1). Lazy bootstrap guard via `_ensure_bootstrapped()` for paths that reach
detection without explicit bootstrap. `reset()` available for test isolation.

`WorkspaceProjectRegistry` (singleton): Composes with `ProjectTypeRegistry`. Adds dynamic pipeline
discovery (`discover_async(client)`). Two-pass matching for `ProcessType`: exact match first, then
contains. Registers discovered pipeline GIDs as `EntityType.PROCESS` in static registry.

`ProcessType` (StrEnum): SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION,
MONTH1, ACCOUNT_ERROR, EXPANSION, UNKNOWN.

`ProcessSection` (StrEnum): OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT,
OTHER.

`AccountActivity` (StrEnum): ACTIVE, ACTIVATING, INACTIVE, IGNORED. Priority ordering:
ACTIVE > ACTIVATING > INACTIVE > IGNORED. Aggregated via `Business.max_unit_activity`.

### Resolution (AssetEdit → Unit/Offer)

`ResolutionStrategy` (StrEnum): DEPENDENT_TASKS, CUSTOM_FIELD_MAPPING, EXPLICIT_OFFER_ID, AUTO.
AUTO tries in priority order until success. `ResolutionResult[T]` returns `entity`, `strategy_used`,
`strategies_tried`, `ambiguous`, `candidates`. Batch variants `resolve_units_async` /
`resolve_offers_async` optimize shared Business hydration (once per unique Business, not per
AssetEdit). No internal caching (ADR-0072). Sync wrappers via `asyncio.run()`.

### Cross-Service Contract

`models/contracts/phone_vertical.py:pvp_from_business(business)` — factory that extracts
`office_phone` + `vertical` from a Business entity and returns `PhoneVerticalPair` (from
`autom8y_core`). Raises `InsightsValidationError` if either field is absent. Used to scope data
service requests to a specific business identity.

---

## Implementation Map

### Files in Scope (this feature — excluding matching/, detection/, seeder.py, section_timeline.py)

| File | Purpose |
|---|---|
| `base.py` | `HolderMixin[T]`, `BusinessEntity(Task)` — base classes; `_invalidate_refs()`, `get_cascading_fields()`, `Fields` auto-generation, `from_gid_async()` |
| `descriptors.py` | 740 LOC DSL: `ParentRef[T]`, `HolderRef[T]`, `CustomFieldDescriptor[T]` hierarchy (8 typed subclasses), `_pending_fields` registry |
| `holder_factory.py` | `HolderFactory(Task, HolderMixin[Task])` — `__init_subclass__` keyword pattern; eliminates ~70 LOC per holder |
| `business.py` | `Business` root entity (19 custom fields, 7 holder subtypes, `from_gid_async`, `_fetch_holders_async`, `get_insights_async`); stub holders `DNAHolder`, `ReconciliationHolder`, `AssetEditHolder`, `VideographyHolder` |
| `fields.py` | `CascadingFieldDef`, `InheritedFieldDef`, `get_cascading_field_registry()`, `STANDARD_TASK_OPT_FIELDS`, `DETECTION_OPT_FIELDS` |
| `hydration.py` | `hydrate_from_gid_async()`, `_traverse_upward_async()`, `HydrationResult`, `HydrationBranch`, `HydrationFailure`, `_convert_to_typed_entity()` |
| `registry.py` | `ProjectTypeRegistry`, `WorkspaceProjectRegistry`, `get_registry()`, `get_workspace_registry()`, `_register_entity_with_registry()` |
| `_bootstrap.py` | `register_all_models()`, `bootstrap()`, `is_bootstrap_complete()`, `reset_bootstrap()` — explicit startup registration |
| `mixins.py` | `SharedCascadingFieldsMixin` (vertical, rep), `FinancialFieldsMixin` (booking_type, mrr, weekly_ad_spend), `UpwardTraversalMixin` (to_business_async), `UnitNavigableEntityMixin`, `UnitNestedHolderMixin` |
| `resolution.py` | `ResolutionStrategy`, `ResolutionResult[T]`, `resolve_units_async()`, `resolve_offers_async()` |
| `activity.py` | `AccountActivity` (StrEnum), `ACTIVITY_PRIORITY`, `SectionClassifier` |
| `contact.py` | `Contact`, `ContactHolder` entity + typed holder |
| `unit.py` | `Unit`, `UnitHolder` entity + typed holder; `UnitHolder.units`, `OfferHolder`, `ProcessHolder` nested |
| `offer.py` | `Offer`, `OfferHolder` entity + typed holder |
| `process.py` | `Process`, `ProcessHolder`, `ProcessType`, `ProcessSection` |
| `location.py` | `Location`, `LocationHolder` — multi-location support |
| `hours.py` | `Hours` — business hours entity |
| `dna.py` | `DNA` — brand DNA entity |
| `reconciliation.py` | `Reconciliation` — reconciliation entity |
| `asset_edit.py` | `AssetEdit` — asset editing entity (has `resolve_unit_async`, `resolve_offer_async`) |
| `videography.py` | `Videography` — videography entity |
| `sections.py` | Section name constants and helpers |
| `patterns.py` | Shared pattern utilities |
| `__init__.py` | Public API surface re-exports |
| `models/contracts/phone_vertical.py` | `pvp_from_business(business)` — cross-service factory |

**Excluded from this entry** (separate features):
- `matching/` → `fuzzy-entity-matching`
- `detection/` → `entity-detection`
- `seeder.py` → `business-seeder`
- `section_timeline.py` → `section-timeline`

### Key Entry Points

```python
# Load fully hydrated Business from GID
business = await Business.from_gid_async(client, gid)

# Load from any entity GID in the hierarchy
result = await hydrate_from_gid_async(client, any_gid)
business = result.business

# Navigate upward from leaf entity
business = await contact.to_business_async(client)

# Batch resolve AssetEdits to Units
results = await resolve_units_async(asset_edits, client)
```

### Public API Surface (consumed by other packages)

- `Business`, `Unit`, `Contact`, `Offer`, `Process`, `Location`, `Hours`, `AssetEdit`, `DNA`,
  `Reconciliation`, `Videography` — consumed by `dataframes/`, `services/`, `persistence/`,
  `lifecycle/`, `api/routes/`
- `HolderFactory`, `HolderMixin` — consumed by `persistence/`, `dataframes/`
- `hydrate_from_gid_async` — consumed by `services/entity_service.py`
- `get_registry()`, `get_workspace_registry()` — consumed by `detection/`, `core/entity_registry`,
  `api/lifespan.py`
- `bootstrap()` — consumed by `entrypoint.py`, `api/lifespan.py`
- `CascadingFieldDef`, `get_cascading_field_registry()` — consumed by `dataframes/resolver/`,
  `persistence/cascade.py`
- `STANDARD_TASK_OPT_FIELDS` — consumed by `hydration.py`, `dataframes/`
- `pvp_from_business` — consumed by `services/matching_service.py`, `clients/data/`
- `AccountActivity`, `ACTIVITY_PRIORITY` — consumed by `services/universal_strategy.py`
- `ResolutionStrategy`, `resolve_units_async`, `resolve_offers_async` — consumed by
  `services/resolution_result.py`

### Test Coverage

Located in `tests/unit/models/business/`:
- `test_descriptors.py` — CustomFieldDescriptor, ParentRef, HolderRef behavior
- `test_custom_field_descriptors.py` — field type coverage (TextField, EnumField, etc.)
- `test_base.py` — HolderMixin, BusinessEntity, _invalidate_refs, Fields auto-generation
- `test_holder_factory.py` — HolderFactory __init_subclass__, _populate_children
- `test_business.py` — Business entity, holder properties, cascade fields
- `test_hydration.py`, `test_upward_traversal.py`, `test_hydration_combined.py` — hydration paths
- `test_registry.py`, `test_registry_consolidation.py`, `test_bootstrap.py`,
  `test_workspace_registry.py` — registry and bootstrap
- `test_fields.py`, `test_cascading_registry.py` — CascadingFieldDef, registry
- `test_activity.py`, `test_activity_properties.py` — AccountActivity, SectionClassifier
- `test_resolution.py` — ResolutionStrategy, batch resolution
- `test_contact.py`, `test_unit.py`, `test_offer.py`, `test_process.py`, `test_location.py`,
  `test_hours.py` — per-entity tests
- `test_patterns.py`, `test_sections.py` — shared utilities
- `tests/unit/persistence/test_session_business.py` — persistence integration

---

## Boundaries and Failure Modes

### What This Feature Does NOT Cover

- **matching/** — fuzzy entity matching (Fellegi-Sunter) is a separate feature
- **detection/** — 4-tier entity type detection is a separate feature
- **seeder.py** — business seeding is a separate feature
- **section_timeline.py** — section timeline tracking is a separate feature
- Custom field schema validation (field existence, allowed enum values) is not enforced by the
  descriptor layer — descriptors return None for missing fields, not errors

### Critical Constraints (Load-Bearing Invariants)

1. **SCAR-001**: Every holder class MUST define `PRIMARY_PROJECT_GID` or entity type detection
   silently collides. Exception: `Process` and its holder (`PRIMARY_PROJECT_GID = None` is
   intentional — dynamic discovery via `WorkspaceProjectRegistry`).

2. **SCAR-020 / SCAR-023** (phone E.164 on read path): `office_phone` and `twilio_phone_num` on
   `Business` MUST use `PhoneTextField` not `TextField`. `PhoneTextField` normalizes to E.164 on
   read via `PhoneNormalizer`. Applied at `business.py:267`. Regression test:
   `tests/unit/models/business/matching/test_normalizers.py:64-70` (`@pytest.mark.scar`).

3. **ADR-0077**: Descriptors declared WITHOUT type annotations. The `model_config` lists all
   descriptor types in `ignored_types` so Pydantic skips them as model fields.
   `extra="allow"` is load-bearing for `__set__` to be called.

4. **TDD-registry-consolidation**: Registration ONLY in `_bootstrap.py:register_all_models()`.
   NEVER in `__init_subclass__`. Adding registration to `__init_subclass__` re-introduces
   import-order-dependent behavior.

5. **ADR-0054**: `allow_override=False` is the DEFAULT for `CascadingFieldDef` — parent ALWAYS
   wins. Only set `allow_override=True` when descendants should keep non-null local values.

6. **HolderFactory MRO rule**: When a subclass inherits from both `UnitNestedHolderMixin` and
   `HolderFactory`, the mixin MUST come FIRST:
   `class OfferHolder(UnitNestedHolderMixin, HolderFactory, ...)`. The mixin's `business`
   property must override `HolderFactory.business`.

7. **ProcessType enum gaps**: As of source_hash `8980bcd7`, `CONSULTATION` is NOT a registered
   `ProcessType`. Workspace discovery will not match it as a pipeline type.

### Error Paths

- `Business.from_gid_async(partial_ok=False)` → `HydrationError` on any hydration failure.
  Wraps upstream exceptions with `entity_gid`, `entity_type`, `phase` context.
- `hydrate_from_gid_async` → `NotFoundError` if GID does not exist; `HydrationError` if traversal
  or hydration fails.
- `_traverse_upward_async` → `HydrationError` on root reached without finding Business, cycle
  detected, or max depth (10) exceeded.
- `_is_recoverable(error)` classifies: `RateLimitError`, `TimeoutError`, `ServerError` →
  True (retry-worthy); `NotFoundError`, `ForbiddenError` → False (permanent).
- `DateField._get_value` → logs `WARNING invalid_date_value` and returns None on parse failure
  (never raises).
- `PhoneTextField._get_value` → imports `PhoneNormalizer` lazily from `matching.normalizers`
  on every call. None passthrough if raw value is None.
- `ProjectTypeRegistry.register` → raises `ValueError` on duplicate GID with different type
  (duplicate same-type is idempotent).
- BROAD-CATCH annotations in hydration code mark intentional catch-all-and-degrade boundaries.

### Interaction Points

- **`dataframes/resolver/cascading.py`** — reads `get_cascading_field_registry()` and
  `CascadingFieldDef.applies_to()` / `should_update_descendant()` during DataFrame cascade
  resolution.
- **`persistence/cascade.py`** — reads `CascadingFieldDef` during entity save pipeline.
- **`core/entity_registry.py`** — `EntityDescriptor` has `cascading_field_provider` flag used
  by `_build_cascading_field_registry()`.
- **`api/lifespan.py` step 1** — calls `bootstrap()` before any detection can occur.
- **`matching/normalizers.py`** — `PhoneNormalizer` is imported lazily inside
  `PhoneTextField._get_value` to avoid circular imports. This means matching package is
  transitively required at runtime for any read of a phone field.
- **`autom8y_core.models.data_service.PhoneVerticalPair`** — cross-SDK type; requires
  `autom8y-core>=4.2.0` (Path γ dep bump, `8980bcd7`).

```metadata
source_files_read: [
  "src/autom8_asana/models/business/descriptors.py",
  "src/autom8_asana/models/business/base.py",
  "src/autom8_asana/models/business/holder_factory.py",
  "src/autom8_asana/models/business/fields.py",
  "src/autom8_asana/models/business/business.py",
  "src/autom8_asana/models/business/hydration.py",
  "src/autom8_asana/models/business/registry.py",
  "src/autom8_asana/models/business/_bootstrap.py",
  "src/autom8_asana/models/business/mixins.py",
  "src/autom8_asana/models/business/resolution.py",
  "src/autom8_asana/models/business/activity.py",
  "src/autom8_asana/models/business/process.py",
  "src/autom8_asana/models/contracts/phone_vertical.py",
  ".know/architecture.md",
  ".know/scar-tissue.md"
]
scar_refs: ["SCAR-001", "SCAR-020", "SCAR-023", "SCAR-024", "SCAR-005"]
adr_refs: [
  "ADR-0050", "ADR-0052", "ADR-0054", "ADR-0068", "ADR-0069", "ADR-0070",
  "ADR-0071", "ADR-0072", "ADR-0073", "ADR-0075", "ADR-0076", "ADR-0077",
  "ADR-0081", "ADR-0082", "ADR-0083", "ADR-0093", "ADR-0094", "ADR-0096",
  "ADR-0097", "ADR-0108", "ADR-0109", "ADR-0116", "ADR-0119"
]
gaps_resolved_from_prior: [
  "Secondary entity files (dna, reconciliation, videography, location, hours) field inventories",
  "seeder.py / patterns.py purpose",
  "AssetEdit resolution.py",
  "HolderFactory pattern",
  "Cascading field registry",
  "CONSULTATION ProcessType gap confirmed",
  "contracts/phone_vertical.py pvp_from_business"
]
```
