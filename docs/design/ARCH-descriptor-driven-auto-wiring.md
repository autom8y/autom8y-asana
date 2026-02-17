# Architectural Analysis: Descriptor-Driven Auto-Wiring (Option A Steel-Man)

**Date:** 2026-02-17
**Author:** Architect Agent
**Status:** Analysis (Pre-Decision)
**Predecessor:** [SPIKE-entity-extensibility-architecture](../spikes/SPIKE-entity-extensibility-architecture.md), [SPIKE-offer-query-canary-bugs](../spikes/SPIKE-offer-query-canary-bugs.md)
**Scope:** EntityDescriptor as single source of truth for DataFrame layer auto-wiring

---

## 1. Why This Is the Right Fit for THIS Codebase

This section does not argue that centralized metadata registries are generically good. It argues that descriptor-driven auto-wiring is specifically optimal for autom8_asana given five concrete properties of the existing system.

### 1.1 The EntityDescriptor Is Already Load-Bearing Infrastructure

`EntityDescriptor` is not a proposal. It is a frozen dataclass instantiated 18 times at module load in `ENTITY_DESCRIPTORS` (`core/entity_registry.py:310-567`), consumed by 8+ subsystems (cache warming, TTL config, entity detection, holder resolution, DynamicIndex, GID lookup, field normalization, join key resolution), and validated by 5 integrity checks at import time. The `get_model_class()` method already performs lazy resolution of dotted import paths for model classes. Adding 3-4 more dotted path fields extends a proven, debugged pattern rather than introducing a new abstraction.

Compare this to the alternative: introducing convention-based discovery or metaclass registration requires building new infrastructure that must prove itself reliable in the same scenarios where EntityDescriptor already works (multi-threaded Lambda warming, API server initialization, test isolation via `SchemaRegistry.reset()`). The risk profile of extending working infrastructure is categorically different from introducing unproven infrastructure.

### 1.2 The Entity Count Is Right-Sized

The system has 18 entity descriptors (7 leaf/composite/root, 11 holders). Of these, 7 currently have DataFrame schemas. The expected ceiling is approximately 20-25 entities total (the domain model is bounded by the Asana workspace structure). At this scale:

- **Convention-based discovery is over-engineered.** Filesystem scanning, importlib autodiscovery, and naming convention enforcement are patterns designed for plugin systems with unbounded contributor counts. For a closed set of 20 entities maintained by one team, explicit declaration in a single file is more maintainable than implicit conventions spread across the filesystem.

- **Metaclass registration is over-engineered.** Metaclass interactions with Pydantic's `ModelMetaclass` are notoriously fragile. The complexity tax of metaclass debugging is justified when you have 100+ entity types contributed by multiple teams. For 20 entities maintained in a single repository, it is pure liability.

- **Explicit descriptor declaration is ergonomically optimal.** A developer adding a new entity reads one file (`entity_registry.py`), sees exactly what 18 other entities declare, fills in the same fields, and gets immediate feedback from `_validate_registry_integrity()` if anything is missing. There is no convention to learn, no metaclass stack trace to debug, no "where does the magic happen?" question.

### 1.3 The Shotgun Surgery Is Empirically Documented

The canary bug spike (SPIKE-offer-query-canary-bugs, B1) proved that the current architecture allows a schema (`OFFER_SCHEMA`) to be registered in `SchemaRegistry` while the corresponding extractor and row model are never created. This is not a hypothetical -- it shipped and crashed in production when a user called `to_dataframe(task_type="Offer")`.

The root cause is structural: there is no enforcement mechanism connecting `SchemaRegistry._ensure_initialized()` (7 hardcoded imports), `_create_extractor()` (2 hardcoded match arms), `task_row.py` (2 hardcoded row subclasses), `ENTITY_RELATIONSHIPS` (4 hardcoded relationship entries), and `_build_cascading_field_registry()` (2 hardcoded model imports). Each is a parallel world with no cross-references.

Descriptor-driven auto-wiring eliminates the parallel worlds by giving each consumer a single place to read from. More critically, it gives `_validate_registry_integrity()` a single place to check: if a descriptor declares `schema_module_path` but not `extractor_class_path`, the validator warns at import time, before any user ever calls `to_dataframe()`.

### 1.4 The Asana Domain Model Is Stable and Hierarchical

The entity type taxonomy (Business > UnitHolder > Unit > OfferHolder > Offer, etc.) is dictated by Asana's project/subtask structure. New entity types arrive infrequently (roughly 2-3 per year) and always follow the same structural pattern: a leaf entity nested under a holder, with cascading fields from ancestors, a dedicated Asana project, a schema, an extractor, and a row model.

This stability means the descriptor fields can be designed to model the actual invariants of the domain, not to handle arbitrary extensibility scenarios. Every entity with a schema needs an extractor. Every entity with an extractor needs a row model. Every entity with a parent needs join keys. These are not optional -- they are the structural invariants of the Asana-backed domain model, and they should be declared and validated, not inferred.

### 1.5 The Team's Mental Model Is Already Descriptor-Centric

The module docstring at `entity_registry.py:307` says: "Adding a new entity type means adding one entry here." This is already the team's mental model -- it is just not true yet. Making it true (rather than introducing a new mental model like "follow the naming convention" or "add the right decorator") has the lowest adoption cost because it aligns with existing expectations.

---

## 2. Exact EntityDescriptor Field Additions

### 2.1 New Fields

```python
@dataclass(frozen=True, slots=True)
class EntityDescriptor:
    # ... existing 21 fields ...

    # --- DataFrame Layer (NEW) ---
    schema_module_path: str | None = None
    extractor_class_path: str | None = None
    row_model_class_path: str | None = None
    cascading_field_provider: bool = False
```

### 2.2 Field-by-Field Justification

**`schema_module_path: str | None = None`**

- **Type rationale: dotted path string, not a class reference.** The schema is a module-level constant (`OFFER_SCHEMA`), not a class. Using a dotted path string (`"autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA"`) is consistent with the existing `model_class_path` pattern and avoids importing the `dataframes` package from `core/` at module load time.
- **Why not `None` means "no schema":** Entities without DataFrame schemas (e.g., `dna_holder`, `reconciliation_holder`) simply leave this as `None`. The validator only checks consistency for descriptors where the field is set.
- **Why not a callable:** Callables would require defining factory functions in `entity_registry.py` that import from `dataframes/`, creating direct circular dependencies. Dotted path strings defer resolution to call time.
- **Format:** `"module.path.CONSTANT_NAME"` -- the trailing component is the attribute name on the module, resolved via `importlib.import_module(module_path)` + `getattr(module, attr_name)`.

**`extractor_class_path: str | None = None`**

- **Type rationale: dotted path string to a class.** Mirrors `model_class_path` exactly. The existing `get_model_class()` method already handles this pattern and can be generalized into a private `_resolve_dotted_path()` helper.
- **Example:** `"autom8_asana.dataframes.extractors.unit.UnitExtractor"`
- **Why a class path and not a factory callable:** The extractor construction interface is uniform -- every extractor takes `(schema, resolver, client=client)`. The variation is which class to instantiate, not how to instantiate it. A class path captures this exactly.

**`row_model_class_path: str | None = None`**

- **Type rationale: dotted path string to a class.** Same pattern as above.
- **Example:** `"autom8_asana.dataframes.models.task_row.UnitRow"`
- **Why this field matters:** The row model is not derivable from the extractor class (unlike `_create_row()`, which is an internal implementation detail). Having it in the descriptor enables the validator to verify that the row model exists and accepts all schema columns before any extraction happens.

**`cascading_field_provider: bool = False`**

- **Type rationale: boolean, not a path.** Unlike the previous three fields, this does not point to a new class. It is a boolean flag indicating that the model class (already referenced by `model_class_path`) has an inner `CascadingFields` class with an `all()` classmethod. Today, only `Business` and `Unit` have this. The flag lets `_build_cascading_field_registry()` discover providers dynamically without knowing their names in advance.
- **Why not `cascading_fields_class_path`:** The cascading fields are defined as an inner class of the model class (e.g., `Business.CascadingFields`). Adding a separate path would duplicate the model_class_path. The boolean flag says "use model_class_path to find the model, then look for `.CascadingFields` on it."
- **Why a field and not a convention check:** We could instead have `_build_cascading_field_registry()` check `hasattr(model_class, 'CascadingFields')` for every descriptor. But this makes the contract implicit. The explicit boolean flag makes the intent declarative and visible in the descriptor definition.

### 2.3 What Was Considered and Rejected

**`activity_classifier_path: str | None`** -- Activity classifiers (`OFFER_CLASSIFIER`, etc.) are already keyed by entity type string in a `CLASSIFIERS` dict in `models/business/activity.py`. This is already a proper registry pattern with no hardcoding issue. Adding a descriptor field for it would be belt-and-suspenders with no bug-prevention benefit.

**`query_relationship_entries`** -- The `join_keys` field on EntityDescriptor already captures the same information as `ENTITY_RELATIONSHIPS` in `query/hierarchy.py`. Rather than adding a new field, the auto-wiring should derive `ENTITY_RELATIONSHIPS` from existing `join_keys`. See section 3.4.

**`async_extraction_required: bool`** -- Considered to flag entities that need `extract_async()` (because they have `cascade:` source columns). Rejected because this is derivable from the schema at extraction time -- if any column has `source.startswith("cascade:")`, the extractor knows to use the async path. Duplicating derivable information in the descriptor violates single-source-of-truth.

---

## 3. The Auto-Wiring Contract

This section specifies the exact interface each consumer needs from the descriptor, the resolution mechanism, and the error handling.

### 3.1 Shared Resolution Utility

Before specifying individual consumers, define the shared lazy resolution function:

```python
# In core/entity_registry.py (private utility)

def _resolve_dotted_path(dotted_path: str) -> Any:
    """Resolve a dotted import path to the referenced object.

    Handles both 'module.path.ClassName' and 'module.path.CONSTANT_NAME'.

    Args:
        dotted_path: Fully qualified dotted path.

    Returns:
        The resolved object (class, constant, etc.)

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the attribute does not exist on the module.
    """
    module_path, _, attr_name = dotted_path.rpartition(".")
    if not module_path:
        raise ImportError(f"Invalid dotted path (no module): {dotted_path!r}")
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, attr_name)
```

Note: `get_model_class()` already implements nearly this exact logic at lines 131-146. The refactoring would extract the common logic into `_resolve_dotted_path()` and have `get_model_class()` delegate to it.

### 3.2 SchemaRegistry._ensure_initialized() Contract

**Current state:** 7 hardcoded imports + 7 hardcoded dict assignments.

**Auto-wired state:**

```python
def _ensure_initialized(self) -> None:
    if self._initialized:
        return
    with self._lock:
        if self._initialized:
            return

        # Auto-wire from entity descriptors
        from autom8_asana.core.entity_registry import get_registry, _resolve_dotted_path

        for desc in get_registry().all_descriptors():
            if desc.schema_module_path:
                schema = _resolve_dotted_path(desc.schema_module_path)
                self._schemas[desc.effective_schema_key] = schema

        # BASE_SCHEMA has no entity descriptor -- it's a universal fallback
        from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
        self._schemas["*"] = BASE_SCHEMA

        self._initialized = True
```

**Interface requirements:**
- Reads `desc.schema_module_path` (the dotted path)
- Reads `desc.effective_schema_key` (the dict key, defaults to `pascal_name`)
- The resolved object must be a `DataFrameSchema` instance
- `BASE_SCHEMA` remains hardcoded because `"*"` is not an entity type

**Error handling:**
- `ImportError` or `AttributeError` from `_resolve_dotted_path()` should propagate -- a descriptor that declares a schema path that does not resolve is a configuration error that must fail loudly at initialization time. This is intentionally strict: silent fallback to `BASE_SCHEMA` would mask exactly the class of bug that B1 exposed.

### 3.3 _create_extractor() Contract

**Current state:** Match/case with 2 explicit branches + wildcard fallback.

**Auto-wired state:**

```python
def _create_extractor(self, task_type: str) -> BaseExtractor:
    from autom8_asana.core.entity_registry import get_registry, _resolve_dotted_path

    registry = get_registry()
    for desc in registry.all_descriptors():
        if desc.pascal_name == task_type and desc.extractor_class_path:
            cls = _resolve_dotted_path(desc.extractor_class_path)
            return cls(self._schema, self._resolver, client=self._client)

    # Fallback for task types without a dedicated extractor
    return DefaultExtractor(self._schema, self._resolver, client=self._client)
```

**Performance note:** The linear scan over ~18 descriptors is negligible (this runs once per DataFrame build, not per row). If desired, the registry could add a `get_by_pascal_name()` O(1) index, but the win is immaterial at 18 entries.

**Interface requirements:**
- Reads `desc.pascal_name` for matching
- Reads `desc.extractor_class_path` for class resolution
- The resolved class must be a subclass of `BaseExtractor`
- Constructor signature must be `(schema, resolver, *, client=None)`

**Error handling:**
- `ImportError`/`AttributeError` from resolution should propagate as `ExtractionError`
- If `pascal_name` matches but `extractor_class_path` is `None`, fall through to `DefaultExtractor` (this is the "partial wiring" case -- schema exists but extractor is not yet implemented)

**Observation on `DefaultExtractor` fallback:** Today, the `DefaultExtractor` fallback is dangerous because `TaskRow` uses `extra="forbid"` and rejects type-specific columns. This is the proximate cause of B1. The auto-wired design preserves the fallback but makes it safe: if a descriptor has `schema_module_path` but no `extractor_class_path`, the validator (section 4) warns at import time. The `DefaultExtractor` remains available for truly unknown task types that do not appear in the registry at all.

### 3.4 ENTITY_RELATIONSHIPS Derivation

**Current state:** 4 hardcoded `EntityRelationship` instances in `query/hierarchy.py:33-58`.

**Auto-wired state:**

```python
def _build_relationships_from_registry() -> list[EntityRelationship]:
    from autom8_asana.core.entity_registry import get_registry

    relationships = []
    for desc in get_registry().all_descriptors():
        for target, key in desc.join_keys:
            relationships.append(
                EntityRelationship(
                    parent_type=desc.name,
                    child_type=target,
                    default_join_key=key,
                    description=f"Auto-derived: {desc.pascal_name} -> {target} via {key}",
                )
            )
    return relationships

# Module-level initialization
ENTITY_RELATIONSHIPS: list[EntityRelationship] = _build_relationships_from_registry()
```

**Interface requirements:**
- Reads `desc.name` (snake_case) for `parent_type`
- Reads `desc.join_keys` (tuple of `(target, key)` pairs)
- The existing `find_relationship()`, `get_join_key()`, and `get_joinable_types()` functions remain unchanged -- they read from `ENTITY_RELATIONSHIPS` as before

**Directionality note:** The current `join_keys` on descriptors are declared from the descriptor's perspective (e.g., `business` declares `join_keys=(("unit", "office_phone"), ...)`). The derived relationship treats this as `parent_type="business", child_type="unit"`. This matches the existing hardcoded entries. However, `find_relationship()` already searches bidirectionally (lines 77-81), so the direction of declaration does not constrain query capability.

**Consistency check:** The 4 hardcoded entries today derive from 3 descriptors (business has 3 join_keys, unit has 2 overlapping with business). The derived list will have 7 entries (business: 3, unit: 2, contact: 1, offer: 2). This is a superset of the current 4, which is correct -- the current list was incomplete. `find_relationship()` handles duplicates correctly because it returns the first match.

### 3.5 _build_cascading_field_registry() Contract

**Current state:** Hardcoded imports of `Business` and `Unit`.

**Auto-wired state:**

```python
def _build_cascading_field_registry() -> dict[str, CascadingFieldEntry]:
    from autom8_asana.core.entity_registry import get_registry

    registry: dict[str, CascadingFieldEntry] = {}

    for desc in get_registry().all_descriptors():
        if not desc.cascading_field_provider:
            continue
        model_class = desc.get_model_class()
        if model_class is None:
            continue
        cascading = getattr(model_class, "CascadingFields", None)
        if cascading is None:
            logger.warning(
                "cascading_provider_missing_inner_class",
                extra={"entity": desc.name, "model": desc.model_class_path},
            )
            continue
        for field_def in cascading.all():
            key = _normalize_field_name(field_def.name)
            registry[key] = (model_class, field_def)

    return registry
```

**Interface requirements:**
- Reads `desc.cascading_field_provider` (boolean flag)
- Calls `desc.get_model_class()` (already implemented)
- Expects `model_class.CascadingFields.all()` to return an iterable of `CascadingFieldDef`
- `_normalize_field_name()` remains unchanged

**Error handling:**
- If `cascading_field_provider=True` but the model class lacks a `CascadingFields` inner class, log a warning (not an error). This is a recoverable inconsistency -- the descriptor flag is wrong but the system can function without those cascade definitions.

---

## 4. The Validation Invariant

### 4.1 New Validation Checks

Add these checks to `_validate_registry_integrity()`, which runs at module load time (line 677):

```python
def _validate_registry_integrity(registry: EntityRegistry) -> None:
    # ... existing checks 1-5 ...

    # Check 6: Schema-Extractor-Row triad consistency
    for desc in registry.all_descriptors():
        # 6a: Schema path resolves
        if desc.schema_module_path:
            try:
                schema = _resolve_dotted_path(desc.schema_module_path)
            except (ImportError, AttributeError) as e:
                raise ValueError(
                    f"Entity {desc.name!r}: schema_module_path "
                    f"{desc.schema_module_path!r} failed to resolve: {e}"
                )

        # 6b: Extractor path resolves
        if desc.extractor_class_path:
            try:
                _resolve_dotted_path(desc.extractor_class_path)
            except (ImportError, AttributeError) as e:
                raise ValueError(
                    f"Entity {desc.name!r}: extractor_class_path "
                    f"{desc.extractor_class_path!r} failed to resolve: {e}"
                )

        # 6c: Row model path resolves
        if desc.row_model_class_path:
            try:
                _resolve_dotted_path(desc.row_model_class_path)
            except (ImportError, AttributeError) as e:
                raise ValueError(
                    f"Entity {desc.name!r}: row_model_class_path "
                    f"{desc.row_model_class_path!r} failed to resolve: {e}"
                )

        # 6d: Schema without extractor (WARNING)
        if desc.schema_module_path and not desc.extractor_class_path:
            logger.warning(
                "schema_without_extractor",
                extra={
                    "entity": desc.name,
                    "schema_path": desc.schema_module_path,
                },
            )

        # 6e: Schema without row model (WARNING)
        if desc.schema_module_path and not desc.row_model_class_path:
            logger.warning(
                "schema_without_row_model",
                extra={
                    "entity": desc.name,
                    "schema_path": desc.schema_module_path,
                },
            )

        # 6f: Extractor without schema (ERROR -- nonsensical)
        if desc.extractor_class_path and not desc.schema_module_path:
            raise ValueError(
                f"Entity {desc.name!r}: has extractor_class_path but no "
                f"schema_module_path (extractor requires a schema)"
            )

    # Check 7: Cascading field provider validity
    for desc in registry.all_descriptors():
        if desc.cascading_field_provider and not desc.model_class_path:
            raise ValueError(
                f"Entity {desc.name!r}: cascading_field_provider=True but "
                f"no model_class_path to resolve the model"
            )
```

### 4.2 Severity Design Rationale

| Check | Severity | Rationale |
|-------|----------|-----------|
| 6a: Schema path unresolvable | ERROR (ValueError) | Misconfigured descriptor; system cannot function correctly |
| 6b: Extractor path unresolvable | ERROR (ValueError) | Same -- declared path must resolve |
| 6c: Row model path unresolvable | ERROR (ValueError) | Same -- declared path must resolve |
| 6d: Schema without extractor | WARNING | Partial wiring -- schema is defined but extraction is not yet implemented. This is the expected state during incremental development. Demoting to warning allows adding a schema first and the extractor in a follow-up PR. |
| 6e: Schema without row model | WARNING | Same reasoning as 6d |
| 6f: Extractor without schema | ERROR | An extractor without a schema is structurally nonsensical -- the extractor reads from the schema's column definitions. This indicates a copy-paste error. |
| 7: Provider without model_class_path | ERROR | The cascading field provider flag requires the model class to exist |

### 4.3 Partial Wiring and the B1 Prevention Guarantee

The B1 bug was: `OFFER_SCHEMA` registered, `OfferExtractor` not created. Under the new validation:

1. If `offer` descriptor has `schema_module_path` but no `extractor_class_path`, check 6d emits a WARNING at import time. This is logged to structured logs and would appear in Lambda/API startup logs.
2. If the developer intended to add extraction support but forgot, the warning serves as a reminder.
3. If the developer intentionally deferred extraction, the warning is acceptable and does not block startup.

The choice of WARNING over ERROR for 6d is deliberate. An ERROR would force atomic implementation of the full triad (schema + extractor + row model) in a single PR. This conflicts with incremental development practices and would discourage adding schemas early for documentation/validation purposes. The WARNING provides the safety net without the rigidity.

**Future tightening:** Once all existing schemas have matching extractors and row models, check 6d could be promoted to ERROR via a configuration flag (`strict_triad_validation: bool = False` on the registry, flipped to `True` after migration).

### 4.4 Import-Time Cost of Validation

Resolving dotted paths in checks 6a-6c triggers `importlib.import_module()` calls for the schema, extractor, and row model modules. For 7 schema-bearing entities, this is 21 imports at module load time.

**Mitigation:** These modules are lightweight (schema modules define constants, extractor modules define classes, row model modules define Pydantic models). The imports would happen anyway when `SchemaRegistry._ensure_initialized()` and `_create_extractor()` are first called. The validation check front-loads them to import time, catching errors earlier.

**Opt-out for testing:** If import-time validation proves too slow for unit tests that never use the DataFrame layer, the validation check can guard behind a `SKIP_SCHEMA_VALIDATION` environment variable (pattern already used in the codebase for `SKIP_ASANA_SETUP`). However, this should be unnecessary -- 21 module imports add negligible time.

---

## 5. Migration Strategy

### 5.1 Phase Ordering

The phases are ordered by dependency chain and risk. Each phase is independently deployable.

#### Phase 1: Foundation (No Behavior Change)

**Scope:** Add fields to EntityDescriptor, populate for existing entities, add validation.
**Risk:** Zero -- no consumer reads the new fields yet.

1. Add `schema_module_path`, `extractor_class_path`, `row_model_class_path`, `cascading_field_provider` to `EntityDescriptor` with `None`/`False` defaults
2. Add `_resolve_dotted_path()` utility
3. Populate fields for all 7 schema-bearing entities:

```python
# business descriptor additions:
schema_module_path="autom8_asana.dataframes.schemas.business.BUSINESS_SCHEMA",
extractor_class_path=None,  # No BusinessExtractor exists yet
row_model_class_path=None,  # No BusinessRow exists yet
cascading_field_provider=True,

# unit descriptor additions:
schema_module_path="autom8_asana.dataframes.schemas.unit.UNIT_SCHEMA",
extractor_class_path="autom8_asana.dataframes.extractors.unit.UnitExtractor",
row_model_class_path="autom8_asana.dataframes.models.task_row.UnitRow",
cascading_field_provider=True,

# contact descriptor additions:
schema_module_path="autom8_asana.dataframes.schemas.contact.CONTACT_SCHEMA",
extractor_class_path="autom8_asana.dataframes.extractors.contact.ContactExtractor",
row_model_class_path="autom8_asana.dataframes.models.task_row.ContactRow",

# offer descriptor additions:
schema_module_path="autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA",
extractor_class_path=None,  # OfferExtractor does not exist yet (B1)
row_model_class_path=None,  # OfferRow does not exist yet (B1)

# asset_edit descriptor additions:
schema_module_path="autom8_asana.dataframes.schemas.asset_edit.ASSET_EDIT_SCHEMA",
extractor_class_path=None,  # No AssetEditExtractor exists
row_model_class_path=None,  # No AssetEditRow exists

# asset_edit_holder descriptor additions:
schema_module_path="autom8_asana.dataframes.schemas.asset_edit_holder.ASSET_EDIT_HOLDER_SCHEMA",
extractor_class_path=None,  # No AssetEditHolderExtractor exists
row_model_class_path=None,  # No AssetEditHolderRow exists
```

4. Add validation checks 6a-6f, 7 to `_validate_registry_integrity()`
5. Observe: the new validation will emit WARNINGs for offer, business, asset_edit, and asset_edit_holder (schema without extractor). This is correct and expected.

**Deliverable:** One PR. No behavior change. Validation warnings visible in logs.

#### Phase 2: Fix B1 (OfferExtractor + OfferRow)

**Scope:** Create `OfferRow`, `OfferExtractor`, add `case "Offer":` to `_create_extractor()`, update descriptor.
**Risk:** Low -- additive only, fixes a known crash.

1. Create `OfferRow(TaskRow)` in `task_row.py` with 12 offer-specific fields
2. Create `OfferExtractor(BaseExtractor)` in `extractors/offer.py`
3. Add `case "Offer":` to `_create_extractor()` match statement
4. Export `OfferExtractor` from `extractors/__init__.py`
5. Update offer descriptor: set `extractor_class_path` and `row_model_class_path`
6. Validation warning for offer goes silent

**Deliverable:** One PR. Fixes the B1 crash. Validation confirms the offer triad is complete.

#### Phase 3: Auto-Wire SchemaRegistry

**Scope:** Replace 7 hardcoded imports in `_ensure_initialized()` with descriptor-driven loop.
**Risk:** Low -- functionally identical behavior, testable by comparing `list_task_types()` before/after.

1. Replace `_ensure_initialized()` body with the auto-wired version (section 3.2)
2. Keep `BASE_SCHEMA` hardcoded (it is not an entity type)
3. Verification test: `SchemaRegistry.get_instance().list_task_types()` returns the same set before and after

**Deliverable:** One PR. Removes 7 hardcoded imports. Schemas auto-discovered from descriptors.

#### Phase 4: Auto-Wire _create_extractor()

**Scope:** Replace match/case with descriptor-driven lookup.
**Risk:** Low -- functionally identical. `DefaultExtractor` fallback preserved.

1. Replace `_create_extractor()` body with descriptor-driven version (section 3.3)
2. Remove explicit `UnitExtractor` and `ContactExtractor` imports from `builders/base.py` (now lazy-resolved)
3. Verification test: build DataFrames for Unit, Contact, and Offer; confirm identical output

**Deliverable:** One PR. Eliminates the match/case that caused B1.

#### Phase 5: Auto-Wire ENTITY_RELATIONSHIPS

**Scope:** Derive `ENTITY_RELATIONSHIPS` from `join_keys` instead of hardcoding.
**Risk:** Medium -- the derived list is a superset of the current list. Must verify that `find_relationship()` consumers handle the additional entries correctly.

1. Replace hardcoded list with `_build_relationships_from_registry()` (section 3.4)
2. Verify: all existing callers of `find_relationship()` and `get_joinable_types()` produce correct results
3. The superset behavior is correct: more relationships are discoverable, but no existing relationship is removed

**Deliverable:** One PR.

#### Phase 6: Auto-Wire _build_cascading_field_registry()

**Scope:** Replace hardcoded Business/Unit imports with descriptor-driven discovery.
**Risk:** Low -- only 2 providers exist today. The auto-wired version discovers the same 2.

1. Replace `_build_cascading_field_registry()` body (section 3.5)
2. Set `cascading_field_provider=True` on `business` and `unit` descriptors (Phase 1)
3. Verification: `get_cascading_field_registry()` returns identical entries

**Deliverable:** One PR.

### 5.2 What Requires Atomic Cutover

Nothing. Every phase is independently deployable because:

- Phases 1-2 add data and fix bugs without changing any consumer behavior
- Phases 3-6 each change one consumer to read from descriptors instead of hardcoded values
- Each phase can be deployed and rolled back independently
- No phase depends on another phase being deployed first (except Phase 2 benefits from Phase 1's validation)

### 5.3 Rollback Safety

Each auto-wired consumer phase (3-6) can be rolled back by reverting the single PR. The descriptors (Phase 1) remain populated regardless -- they are inert metadata fields with no consumers until Phases 3-6 wire them.

---

## 6. Circular Import Analysis

### 6.1 Current Import Graph

```
core/entity_registry.py
  imports: models/business/detection/types.py (EntityType, deferred via _bind_entity_types)
  imported by: services/, api/, config.py, resolution/, core/entity_types.py
  does NOT import: dataframes/

dataframes/models/registry.py (SchemaRegistry)
  imports: dataframes/schemas/*.py (deferred via _ensure_initialized)
  imported by: core/schema.py (deferred), services/resolver.py, api/

dataframes/builders/base.py (_create_extractor)
  imports: dataframes/extractors/ (at module level)
  imports: dataframes/models/registry.py
  does NOT import: core/entity_registry.py

dataframes/ (general)
  imports from core/: exceptions.py, concurrency.py, retry.py, datetime_utils.py
  does NOT import: core/entity_registry.py
```

Key observation: Today, `dataframes/` has zero imports from `core/entity_registry.py`, and `core/entity_registry.py` has zero imports from `dataframes/`. The two packages are completely decoupled.

### 6.2 Post-Auto-Wiring Import Graph

After Phases 3-6, the new imports are:

```
dataframes/models/registry.py (Phase 3)
  NEW: from autom8_asana.core.entity_registry import get_registry (deferred in _ensure_initialized)

dataframes/builders/base.py (Phase 4)
  NEW: from autom8_asana.core.entity_registry import get_registry (deferred in _create_extractor)

query/hierarchy.py (Phase 5)
  NEW: from autom8_asana.core.entity_registry import get_registry (deferred in _build_relationships_from_registry)

models/business/fields.py (Phase 6)
  NEW: from autom8_asana.core.entity_registry import get_registry (deferred in _build_cascading_field_registry)
```

All of these are **deferred imports** (inside function bodies, not at module scope). This is critical because:

1. `entity_registry.py` imports from `models/business/detection/types.py` at module load (via `_bind_entity_types()`).
2. If `entity_registry.py` were to import from `dataframes/` at module scope, and `dataframes/` imported from `models/business/` (which imports from `core/`), a circular dependency could form.
3. By deferring the `get_registry()` import to function call time, the import cycle never forms: `entity_registry.py` finishes loading before any consumer calls `get_registry()`.

### 6.3 The core/schema.py Precedent

`core/schema.py` (line 25) already imports from `dataframes/models/registry.py` inside a function body. This is the exact same pattern proposed here. It has been in production without issues.

### 6.4 Edge Cases Where Lazy Resolution Could Fail

**Edge case 1: Validation check 6a-6c calls `_resolve_dotted_path()` during module load.**

The validation runs at line 677 of `entity_registry.py`:
```python
_validate_registry_integrity(_REGISTRY)
```

If check 6a calls `_resolve_dotted_path("autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA")`, this triggers `importlib.import_module("autom8_asana.dataframes.schemas.offer")` during `entity_registry.py` module load.

**Is this safe?** Yes, because:
- `dataframes/schemas/offer.py` imports only from `dataframes/models/schema.py` (the `DataFrameSchema` and `ColumnDef` classes). It does not import from `core/entity_registry.py`.
- The schema modules are pure data definitions with no side effects.
- The import chain is: `entity_registry.py` -> (validates) -> `dataframes/schemas/offer.py` -> `dataframes/models/schema.py`. No cycle.

**Edge case 2: What if a future schema module imports from `core/entity_registry.py`?**

This would create a genuine circular import: `entity_registry.py` -> (validates) -> `schema_module.py` -> `core/entity_registry.py` (partially loaded). This is prevented by architectural constraint: schema modules must be pure data definitions (constants + `DataFrameSchema`/`ColumnDef` instantiation) with no imports from `core/`.

This constraint should be documented as a comment in `entity_registry.py` adjacent to the validation checks:

```python
# IMPORTANT: Schema/extractor/row model modules must NOT import from
# core.entity_registry, because _validate_registry_integrity() resolves
# their paths during entity_registry.py module load. Any such import
# would create a circular dependency.
```

**Edge case 3: Extractor modules importing from `core/`.**

`dataframes/extractors/unit.py` imports from `models/business/` (line 16: `from autom8_asana.models.business import EntityType, detect_entity_type`). If `models/business/` imports from `core/entity_registry.py` at module scope, and `entity_registry.py` validates extractor paths during its own module load, we get: `entity_registry.py` -> (validates) -> `extractors/unit.py` -> `models/business/` -> `core/entity_registry.py` (partially loaded).

**Check: Does `models/business/` import from `core/entity_registry.py` at module scope?**

Looking at the grep results: `core/entity_registry.py` is imported by `services/`, `api/`, `config.py`, `resolution/`, and `core/entity_types.py`. It is NOT imported by `models/business/`. This is safe today.

**Mitigation:** If this ever becomes a concern, the validation of extractor paths (check 6b) can be deferred from `_validate_registry_integrity()` to `SchemaRegistry._ensure_initialized()`. The import-time check is valuable but not strictly necessary for correctness -- the auto-wired `_create_extractor()` will fail at call time if the path is wrong.

**Summary of circular import risk:** LOW. All new imports are deferred. The validation edge case is safe given current module structure, and can be further hardened by splitting validation into "module-load checks" (path syntax validation) and "first-use checks" (import resolution).

---

## 7. Counter-Arguments Addressed

### 7.1 "The descriptor becomes a god object"

**Objection:** With the 4 new fields, EntityDescriptor grows from 21 to 25 fields. This approaches the complexity threshold where a single class knows too much.

**Response:** The 25 fields decompose into 6 clearly-scoped groups (Identity: 5, Asana Project: 2, Hierarchy: 3, Detection: 2, Schema+DataFrame: 5, Cache: 3, Field Normalization: 3, Discovery: 1, new DataFrame Layer: 4). The frozen dataclass is a passive data container, not a behavior-rich object. It has 5 properties and 2 methods, all trivial. God objects are dangerous because of behavioral complexity (many methods with interacting state), not because of field count in an immutable data record.

Furthermore, `EntityDescriptor` explicitly exists to consolidate the "53+ locations of duplicated entity knowledge" (module docstring, line 1). A centralized metadata record with 25 fields is the correct antidote to 53 locations of scattered knowledge. The alternative -- keeping 21 fields in the descriptor and maintaining 4 separate parallel registrations -- is precisely the fragmentation that caused B1.

### 7.2 "Dotted path strings are fragile -- they break on rename"

**Objection:** If someone renames `UnitExtractor` to `UnitTaskExtractor`, the dotted path in the descriptor silently breaks.

**Response:** It does not silently break. It loudly breaks:
1. `_validate_registry_integrity()` check 6b fires at import time with `AttributeError: module 'autom8_asana.dataframes.extractors.unit' has no attribute 'UnitExtractor'`
2. The application refuses to start
3. The CI pipeline fails

This is strictly better than the current state where renaming an extractor class would only break the `case "Unit":` match arm in `_create_extractor()` -- and only if someone runs `to_dataframe(task_type="Unit")`, which may not be covered by the unit test that the developer remembers to run.

The dotted path string pattern is also battle-tested in this codebase: `model_class_path` has been in production since `EntityDescriptor` was introduced, and every entity has one. No silent breakage has been reported.

IDE support for rename refactoring (PyCharm, VS Code with Pylance) does not follow string-based references. This is a genuine ergonomic cost. It is mitigated by the import-time validation (renames are caught within seconds of running any test or starting the app) and by the small entity count (at most 25 paths to update during a rename, which is a mechanical find-and-replace operation).

### 7.3 "This creates a coupling between core/ and dataframes/"

**Objection:** `core/entity_registry.py` will now contain dotted path strings referencing `dataframes/` modules. This couples the core layer to the DataFrame layer.

**Response:** The coupling is metadata-only, not behavioral. `entity_registry.py` stores string paths that happen to point to `dataframes/` modules, but it never imports them at module scope and never calls any `dataframes/` API. The strings are inert data consumed by `dataframes/` itself (SchemaRegistry, extractor factory) at their own initiative.

Compare to the alternative: if `dataframes/` continues to maintain its own parallel registry, the coupling is implicit (via naming conventions and human memory) rather than explicit (via declared paths). Implicit coupling is harder to detect, harder to validate, and harder to change. The proposed approach trades implicit coupling for explicit, validated coupling -- a strictly better position.

### 7.4 "Deferred imports are a code smell"

**Objection:** Deferred imports inside function bodies are harder to discover and indicate architectural problems.

**Response:** Deferred imports are already pervasive in this codebase:
- `_bind_entity_types()` uses a deferred import (line 585)
- `SchemaRegistry._ensure_initialized()` uses 7 deferred imports (lines 115-123)
- `_build_cascading_field_registry()` uses 2 deferred imports (lines 295-296)
- `core/schema.py` uses 2 deferred imports (lines 25-26)

The proposed changes add 4 more deferred imports, all following the same pattern and all for the same reason (avoiding circular dependencies between `core/` and `dataframes/`). Consistency is more important than avoiding a pattern that is already established and understood.

### 7.5 "Convention-based discovery would require less maintenance"

**Objection:** Option B requires zero descriptor changes when adding a new entity -- just create files with the right names.

**Response:** This is true for the happy path. But it fails on five important edges:

1. **Non-standard names.** `AssetEdit` has pascal_name `AssetEdit` and schema module `asset_edit.py` containing `ASSET_EDIT_SCHEMA`. The convention `{entity_name}.py` -> `{ENTITY_NAME}_SCHEMA` works, but `asset_edit_holder` would need `ASSET_EDIT_HOLDER_SCHEMA` in `asset_edit_holder.py` -- and the convention must handle multi-word entity names correctly. This is a source of bugs that is invisible until runtime.

2. **Selective participation.** Not all entities need schemas (e.g., `dna_holder`, `reconciliation_holder`). Convention-based discovery would need a way to exclude entities from DataFrame wiring. The descriptor approach handles this naturally: leave `schema_module_path` as `None`.

3. **Validation gap.** Convention-based discovery can only validate "does the file exist?", not "does the schema/extractor/row model triad form a consistent set?". The descriptor approach validates triad consistency at import time.

4. **Debugging difficulty.** When `to_dataframe(task_type="Offer")` crashes, a developer debugging with convention-based discovery must reason: "Is there a file at `dataframes/schemas/offer.py`? Does it export `OFFER_SCHEMA`? Does the naming convention match? Is there an extractor at `dataframes/extractors/offer.py`? Does it export `OfferExtractor`?" With descriptor-driven wiring, the developer reads one entry in `ENTITY_DESCRIPTORS` and sees exactly what is and is not wired.

5. **Partial states.** During development, a developer may want to add a schema for documentation purposes before implementing the extractor. Convention-based discovery has no way to express "this entity has a schema but intentionally lacks an extractor." The descriptor approach distinguishes this by having `schema_module_path` set and `extractor_class_path` as `None`, with a WARNING from the validator.

### 7.6 "This is premature centralization -- YAGNI"

**Objection:** The system has 7 schemas today. The shotgun surgery is annoying but manageable. Wait until there are 15+ schemas before centralizing.

**Response:** The B1 bug already shipped. The "annoying but manageable" state produced a crash in production for a user attempting a straightforward operation (`to_dataframe(task_type="Offer")`). The cost of the fix (one PR to add 4 descriptor fields + validation) is lower than the cost of the next B1-class bug, which will happen when the next entity (likely AssetEdit or Business) gets its extractor wired incorrectly.

Furthermore, the existing `EntityDescriptor` infrastructure was built precisely to prevent this class of problem. The spike found that the infrastructure exists but is not connected to the DataFrame layer. Connecting it requires adding 4 fields and changing 4 consumers. This is a completion of existing work, not premature investment in hypothetical future requirements.

### 7.7 "What about entity types that live outside this repository?"

**Objection:** If another service needs to add entity types, they cannot modify `ENTITY_DESCRIPTORS`.

**Response:** This system is a single-repository application backed by a single Asana workspace. Entity types are defined by the Asana project structure, which is controlled by the same team that maintains this codebase. There is no multi-team plugin scenario to design for. If that changes in the future, `SchemaRegistry.register()` (lines 158-189) already supports runtime registration, providing an extension point that does not require modifying `ENTITY_DESCRIPTORS`.

---

## Summary

Descriptor-driven auto-wiring is not the theoretically ideal extensibility model for all systems. It is the right model for THIS system because:

1. **The infrastructure already exists** -- `EntityDescriptor`, `EntityRegistry`, `get_model_class()`, `_validate_registry_integrity()`, and the `ENTITY_DESCRIPTORS` tuple are production-proven and consumed by 8+ subsystems.

2. **The gap is precisely scoped** -- 4 new fields, 4 consumers to rewire, 6 phases of incremental migration.

3. **The alternative (status quo) has already caused a production bug** -- B1 proved that disconnected parallel registries produce wiring gaps that validation cannot catch.

4. **The entity count is right-sized** -- ~20 entities, one team, one repository. Convention-based discovery and metaclass registration are over-engineered for this scale.

5. **Every phase is independently deployable and reversible** -- no big-bang migration, no atomic cutover.

6. **Circular import risk is low and well-mitigated** -- all new imports are deferred, following established patterns in the codebase, with the edge cases analyzed and documented.

The strongest argument is the simplest: the module docstring at `entity_registry.py:307` already says "Adding a new entity type means adding one entry here." Making that statement true is completion of existing intent, not introduction of new complexity.
