# SPIKE: Entity Extensibility Architecture

**Date:** 2026-02-17
**Status:** Complete
**Timebox:** 1 session
**Decision Informs:** OfferExtractor implementation, future entity onboarding, EntityDescriptor scope expansion
**Predecessor:** [SPIKE-offer-query-canary-bugs](./SPIKE-offer-query-canary-bugs.md)

## Question

Why does adding a new entity type (e.g., Offer) require touching 10+ files across disconnected subsystems, and what is the ideal extensibility model to eliminate this shotgun surgery?

## Context

The [offer query canary bugs spike](./SPIKE-offer-query-canary-bugs.md) documented B1: `to_dataframe(task_type="Offer")` crashes because `_create_extractor()` has no `case "Offer":` branch, despite `OFFER_SCHEMA` being registered in `SchemaRegistry`. This is a symptom of a deeper architectural issue: the codebase has a **declared** single source of truth (`EntityDescriptor` in `entity_registry.py`) that is **not actually consumed** by the subsystems it was built to unify.

The docstring at `entity_registry.py:307` says:
> "Adding a new entity type means adding one entry here."

This is aspirational, not actual. Today, adding a new entity type requires shotgun surgery across 5 disconnected subsystems with no enforcement mechanism.

## Findings

### F1: The Two Parallel Worlds

The codebase contains two independent entity metadata systems that share zero references:

| System | Location | Knows About | Consumed By |
|--------|----------|-------------|-------------|
| **EntityDescriptor** | `core/entity_registry.py` | pascal_name, schema_key, join_keys, model_class_path, parent_entity, key_columns | Cache warming, TTL config, entity detection, holder resolution, DynamicIndex, GID lookup |
| **DataFrame Layer** | `dataframes/` (schemas, extractors, row models, builder) | Schema columns, extraction logic, row validation, type-specific factories | DataFrame construction, query engine, API endpoints |

**Zero cross-references:** `dataframes/` and `query/` have zero imports of `EntityDescriptor`, `EntityRegistry`, or `get_registry()`. The DataFrame layer maintains its own parallel set of hardcoded registries.

### F2: Shotgun Surgery Map — What "Add Offer Support" Actually Requires

To fully wire a new entity type (using Offer as the concrete example), you must touch **at minimum** these registration points:

| # | Subsystem | File | Registration Point | Currently Wired for Offer? |
|---|-----------|------|-------------------|---------------------------|
| 1 | Entity Registry | `core/entity_registry.py:372-389` | `EntityDescriptor` in `ENTITY_DESCRIPTORS` tuple | Yes |
| 2 | Entity Type Enum | `core/entity_types.py` | `EntityType.OFFER` enum member | Yes |
| 3 | Schema Definition | `dataframes/schemas/offer.py` | `OFFER_SCHEMA` module constant | Yes |
| 4 | Schema Registration | `dataframes/models/registry.py:122-129` | `self._schemas["Offer"] = OFFER_SCHEMA` in `_ensure_initialized()` | Yes |
| 5 | Row Model | `dataframes/models/task_row.py` | `OfferRow(TaskRow)` subclass | **NO** |
| 6 | Extractor | `dataframes/extractors/offer.py` | `OfferExtractor(BaseExtractor)` class | **NO** |
| 7 | Extractor Factory | `dataframes/builders/base.py:526-542` | `case "Offer":` in `_create_extractor()` match | **NO** |
| 8 | Extractor __init__ | `dataframes/extractors/__init__.py` | Export `OfferExtractor` | **NO** |
| 9 | Query Hierarchy | `query/hierarchy.py:33-58` | `EntityRelationship` entries for unit→offer, business→offer | Yes |
| 10 | Cascading Fields | `models/business/fields.py:284-310` | `_build_cascading_field_registry()` hardcoded imports | **NO** (only Business, Unit) |
| 11 | Activity Classifier | `models/business/activity.py` | `OFFER_CLASSIFIER` with section→activity mappings | Yes |
| 12 | Asana Model | `models/business/offer.py` | `Offer(Task)` Pydantic model | Yes |
| 13 | Query Service | `services/query_service.py` | Entity name→DataFrame mapping | Implicit (via SchemaRegistry) |
| 14 | Cache Warming | Lambda/builder configuration | Entity warming list with priority | Yes (warm_priority=3) |

**The gap:** Points 5, 6, 7, 8, and 10 are missing for Offer. This is why `to_dataframe(task_type="Offer")` crashes — the schema exists (point 4) but the extraction layer (points 5-8) was never wired.

### F3: The Validation Gap

`_validate_registry_integrity()` (`entity_registry.py:616-672`) validates 5 things:
1. Warmable entities have key_columns (warning only)
2. Holder references point to valid leaf entities
3. No duplicate pascal_names
4. Join key targets exist as registered entities
5. Parent entity references exist

**What it does NOT validate:**
- Schema exists in SchemaRegistry for `descriptor.effective_schema_key`
- Row model exists for each schema (the Schema-Extractor-Row triad)
- Extractor is wired in `_create_extractor()` for the pascal_name
- Cascading fields registry includes entities that use `cascade:` source
- Activity classifier exists for warmable entities with sections

The validation catches hierarchy integrity issues but has zero awareness of the DataFrame subsystem.

### F4: EntityDescriptor Already Has the Right Fields

`EntityDescriptor` already declares metadata that the DataFrame layer independently hardcodes:

| EntityDescriptor Field | DataFrame Layer Hardcoding | Duplication |
|----------------------|---------------------------|-------------|
| `pascal_name` | `_create_extractor()` match arms | Exact duplicate |
| `schema_key` / `effective_schema_key` | `SchemaRegistry._ensure_initialized()` dict keys | Exact duplicate |
| `join_keys` | `ENTITY_RELATIONSHIPS` in `query/hierarchy.py` | Exact duplicate |
| `model_class_path` | `task_row.py` subclass definitions | Structural equivalent |
| `parent_entity` | `_build_cascading_field_registry()` hardcoded imports | Structural equivalent |

The descriptor has the data; the DataFrame layer just doesn't read it.

### F5: Existing Self-Describing Patterns (Underutilized)

Several subsystems already demonstrate the registry-driven pattern that could be generalized:

1. **`EntityDescriptor.get_model_class()`** — Lazy import via `model_class_path` dotted string. Already works for Asana Task models. Could be extended with `extractor_class_path` and `row_model_class_path`.

2. **`CascadingFieldDef`** — Self-describing field metadata (`name`, `cf_gid`, `expected_dtype`, `accessor_method`) declared as inner class constants on Business/Unit. This is a good pattern but locked inside model classes with no way for `_build_cascading_field_registry()` to discover new providers dynamically.

3. **`SchemaRegistry`** — Already a proper registry with `get_schema()`, `list_task_types()`, thread-safe initialization. But populated by hardcoded imports rather than by scanning EntityDescriptor entries.

4. **`SectionClassifier`** / `CLASSIFIERS` dict — Activity classification is data-driven (section name → AccountActivity mapping). Already keyed by entity type string. No hardcoding needed to add new classifiers.

---

## Architecture Evaluation

### Option A: Descriptor-Driven Auto-Wiring (Recommended)

**Principle:** `EntityDescriptor` becomes the actual (not aspirational) single source of truth. The DataFrame layer reads descriptor metadata to auto-wire schemas, extractors, and row models.

**Changes to EntityDescriptor:**
```python
@dataclass(frozen=True, slots=True)
class EntityDescriptor:
    # ... existing fields ...

    # --- DataFrame Layer (NEW) ---
    schema_module_path: str | None = None    # e.g., "autom8_asana.dataframes.schemas.offer.OFFER_SCHEMA"
    extractor_class_path: str | None = None  # e.g., "autom8_asana.dataframes.extractors.offer.OfferExtractor"
    row_model_class_path: str | None = None  # e.g., "autom8_asana.dataframes.models.task_row.OfferRow"
    cascading_field_provider: bool = False    # Whether model has CascadingFields inner class
```

**SchemaRegistry becomes auto-wired:**
```python
def _ensure_initialized(self) -> None:
    if self._initialized:
        return
    with self._lock:
        if self._initialized:
            return
        from autom8_asana.core.entity_registry import get_registry
        for desc in get_registry().all_descriptors():
            if desc.schema_module_path:
                schema = _lazy_import(desc.schema_module_path)
                self._schemas[desc.effective_schema_key] = schema
        self._schemas["*"] = BASE_SCHEMA
        self._initialized = True
```

**`_create_extractor()` becomes auto-wired:**
```python
def _create_extractor(self, task_type: str) -> BaseExtractor:
    from autom8_asana.core.entity_registry import get_registry
    registry = get_registry()
    # Try pascal_name lookup
    for desc in registry.all_descriptors():
        if desc.pascal_name == task_type and desc.extractor_class_path:
            cls = _lazy_import(desc.extractor_class_path)
            return cls(self._schema, self._resolver, client=self._client)
    return DefaultExtractor(self._schema, self._resolver, client=self._client)
```

**`ENTITY_RELATIONSHIPS` derived from descriptors:**
```python
def _build_relationships_from_registry() -> list[EntityRelationship]:
    from autom8_asana.core.entity_registry import get_registry
    rels = []
    for desc in get_registry().all_descriptors():
        for target, key in desc.join_keys:
            rels.append(EntityRelationship(
                parent_type=desc.name, child_type=target,
                default_join_key=key, description=f"Auto-derived from {desc.name}"
            ))
    return rels
```

| Criteria | Score |
|----------|-------|
| Eliminates shotgun surgery | Yes — add one EntityDescriptor entry + create the implementation files |
| Import-time validation | `_validate_registry_integrity()` can check schema/extractor/row existence |
| Backward compatible | 100% — existing code continues to work during migration |
| Incremental adoption | High — wire one subsystem at a time |
| Runtime cost | Minimal — lazy imports, one-time init |
| Complexity | Low — builds on existing patterns (`get_model_class()` is the template) |

**Risks:**
- Circular import management — `entity_registry.py` would gain indirect references to `dataframes/` via dotted paths. Mitigated by lazy import strings (already the pattern for `model_class_path`).
- Over-centralization — descriptor grows to ~25 fields. Mitigated by field grouping with clear comments (already done with 6 sections).

---

### Option B: Convention-Based Discovery (Entry-Point / Pluggable)

**Principle:** Use Python naming conventions + `importlib` discovery to find schemas, extractors, and row models automatically. No descriptor metadata needed.

**Convention:**
```
dataframes/schemas/{entity_name}.py  →  {ENTITY_NAME}_SCHEMA
dataframes/extractors/{entity_name}.py  →  {PascalName}Extractor
dataframes/models/task_row.py  →  {PascalName}Row
```

**Auto-discovery in SchemaRegistry:**
```python
def _ensure_initialized(self) -> None:
    for schema_file in Path("dataframes/schemas").glob("*.py"):
        entity_name = schema_file.stem
        constant_name = f"{entity_name.upper()}_SCHEMA"
        module = importlib.import_module(f"autom8_asana.dataframes.schemas.{entity_name}")
        schema = getattr(module, constant_name, None)
        if schema:
            self._schemas[schema.name] = schema
```

| Criteria | Score |
|----------|-------|
| Eliminates shotgun surgery | Partially — must still follow naming conventions exactly |
| Import-time validation | Weak — only detects what's importable, not what's wired correctly |
| Backward compatible | Medium — requires renaming some files to match conventions |
| Incremental adoption | Medium |
| Runtime cost | Higher — filesystem scanning at init time |
| Complexity | Medium — magic conventions are implicit contracts |

**Risks:**
- Convention violations silently fail (no extractor found → DefaultExtractor → crash on extra fields)
- Harder to reason about — "where does Offer get wired?" requires understanding conventions, not reading code
- Entity names that don't follow conventions (e.g., `asset_edit` → `AssetEditSchema` vs `AssetEdit` pascal_name) create fragility

---

### Option C: Metaclass / Class Decorator Self-Registration

**Principle:** Each entity class registers itself with a metaclass or decorator at definition time.

```python
@entity(schema=OFFER_SCHEMA, extractor=OfferExtractor, row_model=OfferRow)
class Offer(Task):
    ...
```

| Criteria | Score |
|----------|-------|
| Eliminates shotgun surgery | Partially — still need schema/extractor/row files, but wiring is co-located |
| Import-time validation | Strong — registration happens at class definition |
| Backward compatible | Low — requires modifying every entity model class |
| Incremental adoption | Low — all-or-nothing metaclass migration |
| Runtime cost | Minimal |
| Complexity | High — metaclass debugging is notoriously difficult |

**Risks:**
- Metaclass interactions with Pydantic's own metaclass (`ModelMetaclass`)
- Import order dependencies — if decorator triggers registry writes, circular imports multiply
- Over-engineering for a system with ~10 entity types that changes infrequently

---

## Comparison Matrix

| Criterion | A: Descriptor-Driven | B: Convention-Based | C: Metaclass |
|-----------|----------------------|--------------------|----|
| Shotgun surgery elimination | Full | Partial | Partial |
| Explicit vs. magic | Explicit (dotted paths in descriptor) | Magic (naming conventions) | Semi-explicit (decorator args) |
| Validation at import time | Strong (integrity checks) | Weak (import success only) | Strong (registration side-effects) |
| Backward compatibility | 100% incremental | Requires file renames | All-or-nothing |
| Circular import risk | Low (lazy strings) | Low (importlib) | High (metaclass + Pydantic) |
| Debugging experience | Excellent (one file to read) | Poor (implicit conventions) | Poor (metaclass stack traces) |
| Matches existing patterns | Yes (model_class_path) | No | No |
| Incremental adoption | Wire one subsystem at a time | Wire all or none for consistency | Wire all or none |
| Lines of code to add Offer | ~3 (descriptor fields) + implementation files | 0 (just follow conventions) + implementation files | ~1 (decorator) + implementation files |
| Entity count consideration | Fine for 10-20 entities | Overkill discovery for 10-20 | Overkill metaclass for 10-20 |

## Recommendation

**Option A: Descriptor-Driven Auto-Wiring.**

Rationale:
1. **Already 80% built.** `EntityDescriptor` already has `pascal_name`, `schema_key`, `join_keys`, `model_class_path`, and `get_model_class()`. Adding 3-4 more dotted path fields extends a proven pattern rather than introducing a new one.

2. **One file to understand.** A developer adding a new entity reads `ENTITY_DESCRIPTORS` and sees exactly what's needed. No convention guessing, no metaclass debugging.

3. **Validation becomes comprehensive.** `_validate_registry_integrity()` can be extended to check that every descriptor with a `schema_module_path` has a corresponding schema importable, extractor importable, and row model importable. **This is the missing enforcement mechanism** — the integrity check that would have prevented the OfferExtractor gap from shipping.

4. **Incremental migration.** Each subsystem can be wired to read from descriptors independently. Start with `SchemaRegistry`, then `_create_extractor()`, then `hierarchy.py`, then `_build_cascading_field_registry()`. Existing hardcoded paths remain as fallbacks during migration.

5. **No new abstractions.** Convention-based discovery and metaclasses both introduce new concepts. Descriptor-driven auto-wiring extends the existing EntityDescriptor concept that the team already maintains.

## Migration Path (Phased)

### Phase 1: Descriptor Extension + Offer Fix (Immediate)
1. Add `schema_module_path`, `extractor_class_path`, `row_model_class_path` fields to `EntityDescriptor`
2. Populate these fields for all existing entities that have schemas (Unit, Contact, Offer, Business, AssetEdit, AssetEditHolder)
3. Create `OfferRow` + `OfferExtractor` (fixes B1 from canary spike)
4. Add `case "Offer":` to `_create_extractor()` (direct fix, not yet auto-wired)
5. Add validation check #6 to `_validate_registry_integrity()`: schema/extractor/row triad consistency

### Phase 2: Auto-Wire SchemaRegistry (Near-term)
1. Change `SchemaRegistry._ensure_initialized()` to iterate `get_registry().all_descriptors()` and import schemas from `schema_module_path`
2. Keep hardcoded fallback for `"*"` (BASE_SCHEMA has no entity descriptor)
3. Remove 7 hardcoded import lines from `_ensure_initialized()`

### Phase 3: Auto-Wire Extractor Factory (Near-term)
1. Change `_create_extractor()` to look up `extractor_class_path` from descriptor by `pascal_name`
2. Remove hardcoded `match`/`case` branches
3. `DefaultExtractor` remains the fallback for entities without extractors

### Phase 4: Auto-Wire Query Hierarchy (Later)
1. Derive `ENTITY_RELATIONSHIPS` from `EntityDescriptor.join_keys` at module load
2. Deprecate the hardcoded list in `hierarchy.py`
3. `find_relationship()` reads from derived list

### Phase 5: Auto-Wire Cascading Fields (Later)
1. Add `cascading_field_provider: bool` to `EntityDescriptor`
2. `_build_cascading_field_registry()` iterates descriptors with `cascading_field_provider=True`, imports their model class via `model_class_path`, and reads `CascadingFields.all()`
3. Remove hardcoded Business/Unit imports

## The Enforcement Invariant

After Phase 1, add this validation check to `_validate_registry_integrity()`:

```python
# Check 6: Schema-Extractor-Row triad consistency
for desc in registry.all_descriptors():
    if desc.schema_module_path:
        # Verify schema is importable
        _verify_importable(desc.schema_module_path, f"{desc.name} schema")
    if desc.extractor_class_path:
        # Verify extractor is importable
        _verify_importable(desc.extractor_class_path, f"{desc.name} extractor")
    if desc.row_model_class_path:
        # Verify row model is importable
        _verify_importable(desc.row_model_class_path, f"{desc.name} row model")
    # If schema exists, extractor and row model should also exist
    if desc.schema_module_path and not desc.extractor_class_path:
        logger.warning("schema_without_extractor", extra={"entity": desc.name})
```

This is the missing guard that would have prevented B1 (OfferExtractor gap) from ever reaching production. If `OFFER_SCHEMA` is declared in the descriptor, the validator would warn (or error) that no `OfferExtractor` path is provided.

## Follow-up Actions

| # | Action | Priority | Depends On |
|---|--------|----------|------------|
| 1 | Create OfferRow + OfferExtractor (direct fix for B1) | P1 | Nothing |
| 2 | Add `schema_module_path`, `extractor_class_path`, `row_model_class_path` to EntityDescriptor | P1 | Nothing |
| 3 | Populate new descriptor fields for all 7 schema-having entities | P1 | #2 |
| 4 | Add validation check #6 (schema-extractor-row triad) | P1 | #2, #3 |
| 5 | Auto-wire SchemaRegistry from descriptors (Phase 2) | P2 | #3 |
| 6 | Auto-wire _create_extractor() from descriptors (Phase 3) | P2 | #3, #5 |
| 7 | Auto-wire ENTITY_RELATIONSHIPS from join_keys (Phase 4) | P3 | #3 |
| 8 | Auto-wire cascading field registry from descriptors (Phase 5) | P3 | #3 |
| 9 | Audit Business/AssetEdit/AssetEditHolder extractor existence | P2 | Nothing |
