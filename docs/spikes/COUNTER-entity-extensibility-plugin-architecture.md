# Counter-Proposal: Entity DataFrame Plugin Architecture

**Date:** 2026-02-17
**Status:** Analysis (Adversarial)
**In Response To:** [SPIKE-entity-extensibility-architecture.md](./SPIKE-entity-extensibility-architecture.md) (Option A: Descriptor-Driven Auto-Wiring)
**Purpose:** Steel-man the case AGAINST expanding EntityDescriptor with DataFrame metadata

---

## Executive Summary

The spike recommends adding 4 fields (`schema_module_path`, `extractor_class_path`, `row_model_class_path`, `cascading_field_provider`) to `EntityDescriptor`, growing it from 21 to 25 fields and creating a unidirectional coupling from the entity identity layer into the DataFrame extraction layer. This counter-proposal argues that this direction conflates two distinct architectural concerns and proposes a **co-located triad pattern** where each entity's DataFrame components (schema, extractor, row model) declare themselves as a cohesive unit that the registry discovers -- rather than the registry declaring them.

The core question is not "should we have a single source of truth?" but rather "what should that source of truth contain?" The descriptor should own entity *identity and hierarchy*. The DataFrame layer should own entity *extraction and serialization*. The wiring between them should be discoverable, not declarative.

---

## Part 1: The God-Object Critique

### 1.1 Current EntityDescriptor Field Census

EntityDescriptor today has 21 fields spanning 6 distinct concerns:

| Concern | Fields | Count |
|---------|--------|-------|
| Identity | `name`, `pascal_name`, `display_name`, `entity_type`, `category` | 5 |
| Asana Project | `primary_project_gid`, `model_class_path` | 2 |
| Hierarchy | `parent_entity`, `holder_for`, `holder_attr` | 3 |
| Detection | `name_pattern`, `emoji` | 2 |
| Schema/Cache | `schema_key`, `default_ttl_seconds`, `warmable`, `warm_priority` | 4 |
| Resolution | `aliases`, `join_keys`, `key_columns`, `explicit_name_mappings` | 4 |
| **Total** | | **21** |

Option A proposes adding a 7th concern:

| Concern | Fields | Count |
|---------|--------|-------|
| DataFrame Layer | `schema_module_path`, `extractor_class_path`, `row_model_class_path`, `cascading_field_provider` | 4 |
| **New Total** | | **25** |

### 1.2 When Does "Single Source of Truth" Become "Single Point of Coupling"?

The spike argues that EntityDescriptor is "already 80% built" for this purpose, citing `model_class_path` as precedent. But `model_class_path` serves the *identity* concern -- it tells you what Pydantic model represents this entity in the Asana domain. Adding `extractor_class_path` and `row_model_class_path` serves a fundamentally different concern: how to *serialize* this entity into tabular data.

Consider the trajectory. After Option A's 4 fields, the next natural additions are:
- `activity_classifier_path` (wiring the activity classification subsystem)
- `query_engine_config` (entity-specific query settings)
- `cache_storage_path` (entity-specific S3 paths)
- `api_route_prefix` (entity-specific API routing)

Each of these eliminates another hardcoded wiring point. Each is justified by the same "single source of truth" argument. At 30+ fields, EntityDescriptor becomes the kind of god-object where every subsystem change requires reading and potentially modifying a single 400-line tuple of frozen dataclass instances.

The precedent `model_class_path` sets is instructive: it is a string that gets lazily imported. It works because Asana Task models are genuinely part of the entity's *identity* -- you cannot meaningfully describe "what is a Unit?" without referencing the Unit model. But you CAN meaningfully describe "what is a Unit?" without knowing that its DataFrame extraction uses `UnitExtractor` from `dataframes/extractors/unit.py`. The extractor is an *implementation detail of one subsystem's consumption* of the entity concept.

### 1.3 The Import String Staleness Problem

Option A's approach relies on dotted import strings:

```python
schema_module_path="autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA"
extractor_class_path="autom8_asana.dataframes.extractors.offer.OfferExtractor"
row_model_class_path="autom8_asana.dataframes.models.task_row.OfferRow"
```

These strings have no IDE support for:
- Rename refactoring (move `OfferExtractor` to a new module -- no breakage detected)
- Find-all-references (searching for `OfferExtractor` usage misses the string in `entity_registry.py`)
- Import validation (typo in path compiles fine, fails at runtime)

The spike acknowledges this and proposes import-time validation via `_validate_registry_integrity()`. But this means you are writing meta-validation code to compensate for the fact that you chose strings over real imports. This is a code smell: when you need validation to verify that your configuration is correct, the configuration model may be wrong.

The existing `model_class_path` string is tolerable precisely because it is one field on one concern. Tripling the number of lazily-imported strings (to 4 per descriptor, times ~17 descriptors = 68 import strings) changes the economics. The validation burden grows quadratically with the number of triad members to verify.

---

## Part 2: The Co-Location Principle

### 2.1 Where Should DataFrame Metadata Live?

Option A says: "in the entity registry, which the DataFrame layer reads."
This counter-proposal says: "in the DataFrame layer, which declares itself to the entity registry."

The distinction matters because of the **direction of dependency**:

```
Option A (Descriptor-Driven):
  entity_registry.py
       |
       | (lazy import strings pointing to)
       v
  dataframes/schemas/offer.py
  dataframes/extractors/offer.py
  dataframes/models/task_row.py

Option B (Co-Located Plugin):
  dataframes/plugins/offer.py  (declares triad)
       |
       | (imports from)
       v
  dataframes/schemas/offer.py
  dataframes/extractors/offer.py
  dataframes/models/task_row.py
       |
       | (auto-discovered by)
       v
  entity_registry.py  (or a separate DataFrame registry)
```

In Option A, the core identity layer (entity_registry.py) acquires knowledge of the DataFrame layer's internal module structure. If you reorganize `dataframes/extractors/` into subdirectories, you must update `entity_registry.py`. If you rename a schema constant, you must update `entity_registry.py`. The entity registry becomes a coordination point that couples to every downstream subsystem's internal layout.

In the co-located approach, the DataFrame layer owns its own wiring. The entity registry remains focused on identity and hierarchy. Each subsystem that consumes entity metadata declares how it maps to entities, rather than having a central registry declare how entities map to each subsystem.

### 2.2 The Existing Evidence: SchemaRegistry Already Self-Describes

Look at `DataFrameSchema`:

```python
@dataclass
class DataFrameSchema:
    name: str         # e.g., "offer"
    task_type: str    # e.g., "Offer"
    columns: list[ColumnDef]
    version: str = "1.0.0"
```

The schema already knows its `task_type`. The schema already knows its `name`. The schema carries enough metadata to register itself. `OFFER_SCHEMA.task_type == "Offer"` is the same key that `EntityDescriptor.pascal_name == "Offer"` uses.

Similarly, `UnitExtractor._create_row()` returns `UnitRow`, and `UnitExtractor._extract_type()` returns `"Unit"`. The extractor already knows what entity type it serves and what row model it produces.

The triad (schema, extractor, row model) is *already* self-describing in terms of what entity type it belongs to. What is missing is not *metadata* but *discovery* -- a mechanism for the builder/registry to find these components without hardcoded imports.

---

## Part 3: The Proposed Alternative -- Entity DataFrame Triad

### 3.1 Design

Each entity type that supports DataFrame extraction declares a `DataFrameTriad` -- a frozen dataclass that binds a schema, extractor class, and row model class into a single cohesive unit.

```python
# dataframes/triad.py

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.dataframes.extractors.base import BaseExtractor
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.models.task_row import TaskRow


@dataclass(frozen=True, slots=True)
class DataFrameTriad:
    """Binding of schema + extractor + row model for one entity type.

    The triad is the unit of DataFrame extensibility. To add DataFrame
    support for a new entity type, create a triad module that declares
    all three components together.
    """
    task_type: str                          # "Offer", "Unit", etc.
    schema: DataFrameSchema                 # OFFER_SCHEMA
    extractor_class: type[BaseExtractor]    # OfferExtractor
    row_model_class: type[TaskRow]          # OfferRow
    has_cascading_fields: bool = False      # Whether model has CascadingFields
```

### 3.2 Triad Declarations Live With Their Components

Each entity type that has DataFrame support declares its triad in a module alongside its existing components:

```python
# dataframes/triads/offer.py

from autom8_asana.dataframes.triad import DataFrameTriad
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from autom8_asana.dataframes.extractors.offer import OfferExtractor
from autom8_asana.dataframes.models.task_row import OfferRow

OFFER_TRIAD = DataFrameTriad(
    task_type="Offer",
    schema=OFFER_SCHEMA,
    extractor_class=OfferExtractor,
    row_model_class=OfferRow,
)
```

```python
# dataframes/triads/unit.py

from autom8_asana.dataframes.triad import DataFrameTriad
from autom8_asana.dataframes.schemas.unit import UNIT_SCHEMA
from autom8_asana.dataframes.extractors.unit import UnitExtractor
from autom8_asana.dataframes.models.task_row import UnitRow

UNIT_TRIAD = DataFrameTriad(
    task_type="Unit",
    schema=UNIT_SCHEMA,
    extractor_class=UnitExtractor,
    row_model_class=UnitRow,
    has_cascading_fields=True,
)
```

### 3.3 TriadRegistry Replaces Hardcoded Wiring

A `TriadRegistry` collects all triads at init time. It replaces both the hardcoded `SchemaRegistry._ensure_initialized()` imports AND the `_create_extractor()` match statement:

```python
# dataframes/triad_registry.py

from autom8_asana.dataframes.triad import DataFrameTriad


class TriadRegistry:
    """Registry of all DataFrame triads, discoverable by task_type."""

    def __init__(self) -> None:
        self._triads: dict[str, DataFrameTriad] = {}

    def register(self, triad: DataFrameTriad) -> None:
        if triad.task_type in self._triads:
            raise ValueError(f"Duplicate triad for {triad.task_type!r}")
        self._triads[triad.task_type] = triad

    def get(self, task_type: str) -> DataFrameTriad | None:
        return self._triads.get(task_type)

    def all_task_types(self) -> list[str]:
        return list(self._triads.keys())

    def has(self, task_type: str) -> bool:
        return task_type in self._triads
```

### 3.4 Discovery Mechanism: Explicit Registration in `__init__`

Rather than filesystem scanning (which the original spike correctly criticizes as fragile), triads register themselves via an explicit init module:

```python
# dataframes/triads/__init__.py

from autom8_asana.dataframes.triad_registry import TriadRegistry

_REGISTRY = TriadRegistry()


def _register_all() -> None:
    from autom8_asana.dataframes.triads.unit import UNIT_TRIAD
    from autom8_asana.dataframes.triads.contact import CONTACT_TRIAD
    from autom8_asana.dataframes.triads.offer import OFFER_TRIAD
    # ... additional triads as they are created

    _REGISTRY.register(UNIT_TRIAD)
    _REGISTRY.register(CONTACT_TRIAD)
    _REGISTRY.register(OFFER_TRIAD)


_register_all()


def get_triad_registry() -> TriadRegistry:
    return _REGISTRY
```

This is ONE file with ONE list of imports. It replaces THREE separate hardcoded registrations (SchemaRegistry imports, `_create_extractor()` match arms, `extractors/__init__.py` exports). More critically, it uses **real imports** -- not strings -- so IDE rename refactoring, find-all-references, and import validation all work.

### 3.5 Consumers Become Trivial

**SchemaRegistry becomes a thin facade:**

```python
def _ensure_initialized(self) -> None:
    if self._initialized:
        return
    with self._lock:
        if self._initialized:
            return
        from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
        from autom8_asana.dataframes.triads import get_triad_registry

        self._schemas["*"] = BASE_SCHEMA
        for task_type in get_triad_registry().all_task_types():
            triad = get_triad_registry().get(task_type)
            self._schemas[task_type] = triad.schema
        self._initialized = True
```

**`_create_extractor()` becomes generic:**

```python
def _create_extractor(self, task_type: str) -> BaseExtractor:
    from autom8_asana.dataframes.triads import get_triad_registry

    triad = get_triad_registry().get(task_type)
    if triad is not None:
        return triad.extractor_class(
            self._schema, self._resolver, client=self._client
        )
    return DefaultExtractor(self._schema, self._resolver, client=self._client)
```

**`_build_cascading_field_registry()` becomes discoverable:**

```python
def _build_cascading_field_registry() -> dict[str, CascadingFieldEntry]:
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.dataframes.triads import get_triad_registry

    registry: dict[str, CascadingFieldEntry] = {}
    triad_reg = get_triad_registry()

    for triad in triad_reg._triads.values():
        if triad.has_cascading_fields:
            entity_desc = get_registry().get(triad.task_type.lower())
            if entity_desc:
                model_class = entity_desc.get_model_class()
                if model_class and hasattr(model_class, 'CascadingFields'):
                    for field_def in model_class.CascadingFields.all():
                        key = _normalize_field_name(field_def.name)
                        registry[key] = (model_class, field_def)
    return registry
```

---

## Part 4: Developer Experience Comparison

### 4.1 Option A: "Add Offer DataFrame Support"

Step 1. Open `core/entity_registry.py` (687 lines). Find the Offer descriptor (line 372). Add 3-4 new fields:

```python
EntityDescriptor(
    name="offer",
    pascal_name="Offer",
    # ... 15 existing fields ...
    schema_module_path="autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA",
    extractor_class_path="autom8_asana.dataframes.extractors.offer.OfferExtractor",
    row_model_class_path="autom8_asana.dataframes.models.task_row.OfferRow",
    cascading_field_provider=False,
)
```

Step 2. Create `dataframes/extractors/offer.py` with `OfferExtractor`.

Step 3. Add `OfferRow` to `dataframes/models/task_row.py`.

Step 4. The schema already exists (`dataframes/schemas/offer.py`).

**Files touched:** 3 (entity_registry.py, offer.py extractor, task_row.py).

**Cognitive load:** Developer must understand the EntityDescriptor data model (21+ fields across 6+ concerns) to add 3 strings. Must ensure the dotted path strings are exactly correct -- no IDE assistance. Must understand that `entity_registry.py` is the coordination point for a subsystem 3 directories away.

### 4.2 Triad Approach: "Add Offer DataFrame Support"

Step 1. Create `dataframes/extractors/offer.py` with `OfferExtractor`.

Step 2. Add `OfferRow` to `dataframes/models/task_row.py`.

Step 3. The schema already exists (`dataframes/schemas/offer.py`).

Step 4. Create `dataframes/triads/offer.py` (5 lines):

```python
from autom8_asana.dataframes.triad import DataFrameTriad
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from autom8_asana.dataframes.extractors.offer import OfferExtractor
from autom8_asana.dataframes.models.task_row import OfferRow

OFFER_TRIAD = DataFrameTriad(
    task_type="Offer",
    schema=OFFER_SCHEMA,
    extractor_class=OfferExtractor,
    row_model_class=OfferRow,
)
```

Step 5. Add one import + one `.register()` call in `dataframes/triads/__init__.py`.

**Files touched:** 4 (offer.py extractor, task_row.py, triads/offer.py, triads/__init__.py).

**Cognitive load:** Developer works entirely within the `dataframes/` package. The triad module is 5 lines of real Python imports -- no strings, no dotted paths, no understanding of the 21-field EntityDescriptor required. IDE validates all imports immediately. "Where is Offer wired?" is answered by `dataframes/triads/offer.py` -- a file that exists solely for this purpose and contains nothing else.

### 4.3 Comparison Table

| Factor | Option A (Descriptor) | Triad Approach |
|--------|----------------------|----------------|
| Files touched to add entity | 3 | 4 |
| Lines added to existing files | ~3 strings in entity_registry.py | ~2 lines in triads/__init__.py |
| New files | 1 (extractor) | 2 (extractor + triad) |
| IDE refactoring support | None (strings) | Full (imports) |
| "Where is Offer wired?" | entity_registry.py:372 (buried in 25-field descriptor) | dataframes/triads/offer.py (dedicated 5-line file) |
| Validation approach | Runtime import string verification | Compile-time import resolution |
| Knowledge required | EntityDescriptor internals + dotted path conventions | DataFrameTriad (5 fields) |
| Can forget a field? | Yes (string typo compiles) | No (import fails immediately) |
| Cross-concern coupling | entity_registry knows dataframes layout | dataframes knows entity_registry (already true) |

---

## Part 5: Honest Critique of Option A's Failure Modes

### 5.1 Lazy Import Strings That Become Stale

The spike proposes `schema_module_path="autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA"`. This string will become stale if:

- The schema module is moved (e.g., reorganizing schemas into subdirectories by domain)
- The schema constant is renamed (e.g., `OFFER_SCHEMA` -> `OFFER_V2_SCHEMA` during a schema evolution)
- The entire `dataframes/schemas/` package is restructured

The import-time validation catches these -- but only at startup, not at development time. The developer sees no IDE warning. `mypy` sees no error. `ruff` sees no violation. The feedback loop is: make change -> start application -> see ImportError -> fix string -> repeat.

With real imports in a triad file, the feedback loop is: make change -> IDE immediately underlines the broken import in red.

### 5.2 A 25-Field (and Growing) Descriptor

Read the `ENTITY_DESCRIPTORS` tuple today. Each descriptor is already 10-20 lines of field assignments. Adding 4 more fields means each descriptor becomes 14-24 lines. The full tuple (17 descriptors * ~20 lines) is 340+ lines of dense configuration. With `schema_module_path` strings averaging 60+ characters, line-wrapping makes each descriptor even harder to scan.

More importantly, this sets the precedent. The activity classifier (`OFFER_CLASSIFIER`) is another hardcoded wiring point documented in the spike (point 11 in the shotgun surgery map). After Option A ships, the logical next step is `activity_classifier_path: str | None`. Then the query hierarchy derivation (spike Phase 4) needs to be validated, so perhaps `query_hierarchy_enabled: bool`. The descriptor becomes the project's `settings.py` -- a file that every subsystem depends on and every feature touches.

### 5.3 Import-Time Validation That Slows Startup

The spike proposes extending `_validate_registry_integrity()` to verify that every `schema_module_path`, `extractor_class_path`, and `row_model_class_path` is importable. This means at application startup:

1. Iterate 17 descriptors
2. For each, attempt to import up to 3 modules
3. Validate that the imported object is the correct type

That is up to 51 lazy imports at startup, triggered by entity_registry.py loading. Today, `_validate_registry_integrity()` does no imports -- it only checks internal consistency of the descriptor tuple. Option A transforms it into an import-heavy validation pass that triggers the entire DataFrame subsystem's module loading.

For the Lambda deployment (cache warming), this startup cost matters. Every cold start pays the validation tax.

The triad approach has the same import cost, but it is *deferred* to first use of the triad registry -- which is when the DataFrame system actually needs the components. The entity registry itself loads with zero DataFrame imports, preserving today's fast startup for code paths that never touch DataFrames.

### 5.4 The "One File to Understand" Claim Is Misleading

The spike argues: "A developer adding a new entity reads ENTITY_DESCRIPTORS and sees exactly what's needed."

But what they actually see is:

```python
EntityDescriptor(
    name="offer",
    pascal_name="Offer",
    display_name="Offer",
    entity_type=None,
    category=EntityCategory.LEAF,
    primary_project_gid="1143843662099250",
    model_class_path="autom8_asana.models.business.offer.Offer",
    default_ttl_seconds=180,
    warmable=True,
    warm_priority=3,
    aliases=("business_offer",),
    join_keys=(("unit", "office_phone"), ("business", "office_phone")),
    key_columns=("office_phone", "vertical", "offer_id"),
    schema_module_path="autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA",
    extractor_class_path="autom8_asana.dataframes.extractors.offer.OfferExtractor",
    row_model_class_path="autom8_asana.dataframes.models.task_row.OfferRow",
    cascading_field_provider=False,
)
```

This is 18 lines. The developer must parse all 18 to understand which ones they need to fill in for their new entity. They must understand the distinction between `model_class_path` (Asana model), `extractor_class_path` (DataFrame extractor), and `row_model_class_path` (Pydantic row validator). They must know the dotted path convention. They must know that `schema_key` defaults to `pascal_name` but `schema_module_path` does not.

By contrast, the triad approach separates concerns: the entity's *identity* is in entity_registry.py (which the developer already understands), and the entity's *DataFrame components* are in a dedicated 5-line triad file that imports real Python objects.

---

## Part 6: Testing Implications

### 6.1 Option A: Testing Requires Entity Registry Setup

With Option A, any test that exercises `_create_extractor()` or `SchemaRegistry._ensure_initialized()` must have a valid `EntityRegistry` with populated descriptor fields. The existing test fixtures reset the registry singleton (`conftest.py` resets `EntityProjectRegistry`, `SchemaRegistry`, etc.). Adding DataFrame paths to descriptors means these reset fixtures must also ensure the descriptor strings are valid -- or the import-time validation will fail during test setup.

Consider a test that only needs the Unit extractor. Today, it imports `UnitExtractor` directly. With Option A's auto-wiring, it might go through `_create_extractor("Unit")`, which queries the entity registry, which requires that the descriptor's `extractor_class_path` is populated and importable. The test has gained a transitive dependency on entity_registry initialization.

### 6.2 Triad Approach: Testing Is Component-Local

With the triad approach, testing each component remains independent:

- **Test a schema:** Import `OFFER_SCHEMA` directly, validate columns. No registry needed.
- **Test an extractor:** Import `OfferExtractor` directly, pass it a schema and resolver. No registry needed.
- **Test a row model:** Import `OfferRow` directly, call `model_validate()`. No registry needed.
- **Test the wiring:** Import `OFFER_TRIAD`, verify `.schema`, `.extractor_class`, `.row_model_class` are the expected types. Simple attribute assertions.
- **Test the registry:** Import `get_triad_registry()`, verify `has("Offer")`, `get("Offer").schema == OFFER_SCHEMA`. No entity_registry dependency.

The triad approach preserves the existing test isolation pattern where DataFrame tests live in `tests/unit/dataframes/` and do not require entity registry fixtures. Option A would blur this boundary.

### 6.3 Invariant Testing

Both approaches support the critical invariant test ("every schema has an extractor and row model"). The implementations differ:

**Option A:** Iterate `entity_registry.all_descriptors()`, check that `schema_module_path` implies `extractor_class_path` and `row_model_class_path` are set.

**Triad Approach:** Iterate `get_triad_registry().all_task_types()`, check that each triad's `.schema`, `.extractor_class`, and `.row_model_class` are non-None and self-consistent. Additionally, cross-reference `SchemaRegistry.list_task_types()` against `TriadRegistry.all_task_types()` to catch orphaned schemas.

The triad approach gives you a *stronger* invariant: not just "the strings exist" but "the imports resolve and the types are correct" -- because the triad uses real imports, not strings.

---

## Part 7: Migration Path

### Phase 1: Create Triad Infrastructure (Immediate)

1. Create `dataframes/triad.py` with the `DataFrameTriad` dataclass
2. Create `dataframes/triad_registry.py` with `TriadRegistry`
3. Create `dataframes/triads/__init__.py` with registration for existing triads (Unit, Contact)
4. Create `dataframes/triads/unit.py` and `dataframes/triads/contact.py`

### Phase 2: Add Offer (Immediate, fixes B1)

1. Create `OfferRow` in `task_row.py`
2. Create `OfferExtractor` in `extractors/offer.py`
3. Create `dataframes/triads/offer.py`
4. Register in `dataframes/triads/__init__.py`

### Phase 3: Wire Consumers to TriadRegistry (Near-term)

1. Modify `SchemaRegistry._ensure_initialized()` to read from `TriadRegistry`
2. Modify `_create_extractor()` to read from `TriadRegistry`
3. Remove hardcoded imports from both locations
4. Add invariant test: `SchemaRegistry.list_task_types()` subset of `TriadRegistry.all_task_types()`

### Phase 4: Wire Cascading Fields (Later)

1. Add `has_cascading_fields: bool` to `DataFrameTriad`
2. Modify `_build_cascading_field_registry()` to discover providers via `TriadRegistry`
3. Remove hardcoded Business/Unit imports

### Phase 5: Wire Query Hierarchy (Later, same as spike Phase 4)

This phase is identical under either approach -- `ENTITY_RELATIONSHIPS` derivation from `EntityDescriptor.join_keys` does not depend on whether DataFrame metadata lives in the descriptor or in triads. This is hierarchy metadata, which correctly belongs in `EntityDescriptor`.

---

## Part 8: What EntityDescriptor SHOULD Own (And What It Should Not)

| Metadata | Belongs In EntityDescriptor? | Reason |
|----------|------------------------------|--------|
| `pascal_name`, `name`, `display_name` | Yes | Entity identity |
| `entity_type`, `category` | Yes | Entity classification |
| `primary_project_gid` | Yes | Asana project binding |
| `model_class_path` | Yes | Domain model identity |
| `parent_entity`, `holder_for`, `holder_attr` | Yes | Hierarchy structure |
| `name_pattern`, `emoji` | Yes | Entity detection |
| `schema_key` | Yes | Registry key (identity-level) |
| `default_ttl_seconds`, `warmable`, `warm_priority` | Yes | Cache behavior |
| `aliases`, `join_keys`, `key_columns` | Yes | Resolution identity |
| `schema_module_path` | **No** | DataFrame subsystem internal |
| `extractor_class_path` | **No** | DataFrame subsystem internal |
| `row_model_class_path` | **No** | DataFrame subsystem internal |
| `cascading_field_provider` | **No** | DataFrame subsystem internal |

The bright line: if the metadata describes *what this entity IS* (identity, hierarchy, relationships, behavior policies), it belongs in the descriptor. If the metadata describes *how a specific subsystem processes this entity* (DataFrame extraction, query routing, activity classification), it belongs with that subsystem.

---

## Part 9: Comparison Matrix

| Criterion | Option A (Descriptor) | Triad Approach |
|-----------|----------------------|----------------|
| Shotgun surgery elimination | Full | Full (same reduction) |
| EntityDescriptor field count | 25 (and growing) | 21 (stable) |
| Import validation | Runtime (lazy strings) | Compile-time (real imports) |
| IDE refactoring support | None (strings) | Full (imports) |
| Subsystem coupling direction | Core -> DataFrame (wrong) | DataFrame -> Core (correct) |
| Test isolation | Blurred (DataFrame tests need entity registry) | Preserved (tests remain local) |
| Startup cost | Higher (validation imports all triads) | Deferred (lazy on first DataFrame use) |
| "Where is X wired?" | Search 687-line entity_registry.py | Open dataframes/triads/x.py |
| Incremental adoption | Wire one subsystem at a time | Wire one subsystem at a time |
| New files per entity | 0 (add to existing) | 1 (triad module) |
| Backward compatible | 100% | 100% |
| Matches existing patterns | `model_class_path` precedent | `SchemaRegistry` + `TriadRegistry` pattern |
| God-object trajectory | Accelerating (precedent for more fields) | Arrested (descriptor stays focused) |
| Future subsystem wiring | Each adds fields to descriptor | Each gets its own registry |

---

## Part 10: What I Concede

This is a steel-man argument, so I must be honest about where Option A genuinely wins:

1. **Fewer files.** Option A requires zero new infrastructure modules. The triad approach adds `triad.py`, `triad_registry.py`, and `triads/__init__.py` as new abstractions. For a codebase with ~10 entity types that changes infrequently, this is real overhead.

2. **One canonical location.** Option A makes EntityDescriptor THE place to look for everything about an entity. The triad approach splits entity knowledge between `entity_registry.py` (identity) and `dataframes/triads/x.py` (DataFrame components). A new developer must learn two locations.

3. **Simpler mental model.** "Everything about an entity is in its descriptor" is simpler than "identity is in the descriptor, DataFrame components are in triads, and they cross-reference via task_type string."

4. **The spike's `model_class_path` precedent is real.** The descriptor already has one lazily-imported string. Adding three more is a quantitative change, not a qualitative one. The "god-object" alarm may be premature at 25 fields.

5. **Entity count is small.** With ~10 entity types that gain DataFrame support rarely (maybe 1-2 per quarter), the practical impact of either choice is modest. The architectural purity of the triad approach may not justify the new abstraction layer for a team of this size.

---

## Recommendation

The triad approach is architecturally superior for the following reasons, listed in order of importance:

1. **Dependency direction.** The entity registry is a core module. The DataFrame layer is a domain-specific subsystem. Core should not depend on (or know about) subsystem internals. The triad approach inverts the dependency correctly.

2. **Real imports over strings.** The compile-time safety of real imports versus the runtime-only validation of dotted path strings is a meaningful quality difference that compounds over time.

3. **God-object arrest.** The triad approach establishes a precedent where each subsystem owns its own entity wiring. Future subsystems (activity classification, query configuration) follow the same pattern rather than adding more fields to EntityDescriptor.

4. **Test isolation preservation.** DataFrame tests remain independent of entity registry initialization, which is the current (correct) state of affairs.

However, the choice is closer than it might appear. For a small team working on a codebase with ~10 entity types, either approach solves the immediate problem (B1: missing OfferExtractor). The spike's Option A is a pragmatic, minimal-diff solution. The triad approach is a more principled solution that pays dividends if the entity count grows or if additional subsystems need similar wiring.

The strongest argument for the triad approach is not what it does today, but what it *prevents* tomorrow: the slow accretion of unrelated metadata into EntityDescriptor until it becomes a 35-field god-object that every subsystem in the project depends on.

---

## Follow-up Actions (If Triad Approach Is Selected)

| # | Action | Priority | Depends On |
|---|--------|----------|------------|
| 1 | Create `DataFrameTriad` dataclass | P1 | Nothing |
| 2 | Create `TriadRegistry` | P1 | #1 |
| 3 | Create triad modules for Unit, Contact | P1 | #1 |
| 4 | Create `OfferRow` + `OfferExtractor` (fixes B1) | P1 | Nothing |
| 5 | Create Offer triad module | P1 | #1, #4 |
| 6 | Wire `SchemaRegistry._ensure_initialized()` to TriadRegistry | P2 | #2, #3 |
| 7 | Wire `_create_extractor()` to TriadRegistry | P2 | #2, #3 |
| 8 | Add invariant test (schema-extractor-row triad consistency) | P2 | #2, #3 |
| 9 | Wire `_build_cascading_field_registry()` to TriadRegistry | P3 | #2 |
| 10 | Audit Business/AssetEdit/AssetEditHolder for triad creation | P2 | #2 |
