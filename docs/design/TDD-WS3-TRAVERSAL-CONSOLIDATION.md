# TDD-WS3: Traversal Consolidation

**Author**: Architect (WS3-Arch)
**Date**: 2026-02-17
**Initiative**: SSoT Convergence & Reliability Hardening
**Workstream**: WS3 (Traversal Consolidation)
**Status**: DRAFT
**Predecessor**: WS2 Cache Reliability (COMPLETE, commit 2977717)
**Test Baseline**: 10,582 passed, 0 failed

---

## 1. Problem Statement

The DataFrame layer has two cascade resolution systems that evolved independently:

- **System B** (`CascadingFieldResolver` in `dataframes/resolver/cascading.py`, 676 lines): Legacy per-API-call resolver. Traverses parent chains by fetching Task objects via Asana API or pre-warmed local cache.
- **System C** (`CascadeViewPlugin` in `dataframes/views/cascade_view.py`, 541 lines): Cache-backed resolver using `UnifiedTaskStore`. Traverses parent chains via hierarchy index and cached dict data.

Additionally, `UnitExtractor._extract_office_async()` (111 lines in `dataframes/extractors/unit.py`) contains a bespoke traversal loop that duplicates System B's pattern and reaches into B's private methods (`_get_parent_gid`, `_fetch_parent_async`).

B already delegates to C when `cascade_plugin` is provided (line 224-229 in cascading.py). C already delegates `_extract_field_value` to the shared `cf_utils.extract_cf_value` (IMP-18). B still has its own inlined 58-line `_extract_field_value`.

### 1.1 Duplication Inventory

| Method | System B (cascading.py) | System C (cascade_view.py) | Identical? |
|--------|------------------------|---------------------------|------------|
| `_class_to_entity_type` | Lines 650-675 (12-entry map) | Lines 503-527 (12-entry map) | YES - identical maps |
| `_get_custom_field_value` | Lines 566-589 (24 lines) | Lines 417-440 (24 lines) | YES - identical logic |
| `_extract_field_value` | Lines 591-648 (58-line match/case) | Lines 470-481 (delegates to `cf_utils`) | DUPLICATE - same intent, B inlined |
| `_traverse_parent_chain` | Lines 272-398 (Task objects + API) | Lines 182-307 (dicts + cache) | SIMILAR - different data sources |

Additionally:
- `UnitExtractor._extract_office_async` (lines 89-199, 111 lines) duplicates B's traversal loop with cycle detection, entity type checking, and root fallback -- but resolves `task.name` instead of a custom field.

### 1.2 The Office Problem

`_extract_office_async` resolves the Business ancestor's `task.name` (the office name). This is fundamentally different from cascade resolution, which resolves custom field values via `_get_custom_field_value()`. The office field CANNOT simply become `cascade:Office` because the cascade mechanism searches `task.custom_fields`, not `task.name`.

However, `CascadingFieldDef` already has a `source_field` attribute (see `models/business/fields.py` line 58), and `Business.CascadingFields.BUSINESS_NAME` already declares `source_field="name"` (see `models/business/business.py` line 331). The model-layer `CascadingFieldDef.get_value()` method (fields.py lines 74-93) checks `source_field` and calls `getattr(source, self.source_field)` when set.

**The gap**: Neither System B nor System C checks `field_def.source_field` during traversal. Both call `_get_custom_field_value()` unconditionally, which only searches `task.custom_fields`. The `source_field` pathway exists in the data model but is not wired into the DataFrame-layer resolvers.

### 1.3 Scope

- **IN SCOPE**: Eliminate method duplication between B and C. Eliminate `_extract_office_async`. Make CascadeViewPlugin the primary resolution path.
- **OUT OF SCOPE**: System A (model-layer `UpwardTraversalMixin`). Query hierarchy. Entity detection improvements. New cascade fields or entity types. CascadeViewPlugin cache interaction changes (WS2 territory). Generalized parent-chain walker (future WS).

---

## 2. Design: DRY Extraction (Shared Utility Functions)

### 2.1 Decision: Extract to `cf_utils.py`

**Options Evaluated**:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A. B delegates to C | Make B call C's methods | Minimal new code | Couples B to C; B needs C instance even in fallback path |
| B. Extract to `cf_utils.py` | Move shared utilities to existing shared module | Clean dependency graph; both B and C consume same functions; `cf_utils.py` already exists as DRY target | Slightly more files touched |
| C. New shared module | Create `dataframes/resolver/cascade_utils.py` | Separation from view-layer utils | Unnecessary new file; `cf_utils.py` already serves this role |

**Selected: Option B** -- Extract to `cf_utils.py`.

Rationale: `cf_utils.py` (116 lines) already exists as the DRY target for custom field extraction per IMP-18. System C already delegates `_extract_field_value` to it. Adding the 2 other shared functions (`_class_to_entity_type` and `_get_custom_field_value`) to this module creates a single utility surface for all cascade field operations. No new abstractions needed.

### 2.2 Functions to Extract

Three functions move to `cf_utils.py`:

**1. `class_to_entity_type(cls: type) -> EntityType`** (new public function)

Extracted from the identical 12-entry class name maps in both B and C. Becomes a module-level function rather than a method.

```python
# In cf_utils.py
def class_to_entity_type(cls: type) -> EntityType:
    """Map business model class to EntityType enum."""
    class_name_map: dict[str, EntityType] = {
        "Business": EntityType.BUSINESS,
        "Unit": EntityType.UNIT,
        "Contact": EntityType.CONTACT,
        "ContactHolder": EntityType.CONTACT_HOLDER,
        "UnitHolder": EntityType.UNIT_HOLDER,
        "LocationHolder": EntityType.LOCATION_HOLDER,
        "OfferHolder": EntityType.OFFER_HOLDER,
        "ProcessHolder": EntityType.PROCESS_HOLDER,
        "Offer": EntityType.OFFER,
        "Process": EntityType.PROCESS,
        "Location": EntityType.LOCATION,
        "Hours": EntityType.HOURS,
    }
    return class_name_map.get(cls.__name__, EntityType.UNKNOWN)
```

**2. `get_custom_field_value(task_or_dict, field_name: str) -> Any`** (new public function)

Extracted from the identical implementations in B (lines 566-589) and C (lines 417-440). Accepts either a Task object or a dict (unifying `_get_custom_field_value` and `_get_custom_field_value_from_dict`).

```python
# In cf_utils.py
def get_custom_field_value(
    task_or_dict: Any,
    field_name: str,
) -> Any:
    """Extract custom field value by name from Task or dict.

    Handles both Task objects (with .custom_fields attribute) and
    dict data (with "custom_fields" key) transparently.
    """
    normalized_name = field_name.lower().strip()

    if isinstance(task_or_dict, dict):
        custom_fields = task_or_dict.get("custom_fields")
    else:
        custom_fields = getattr(task_or_dict, "custom_fields", None)

    if not custom_fields:
        return None

    for cf in custom_fields:
        if isinstance(cf, dict):
            cf_name = cf.get("name")
        else:
            cf_name = getattr(cf, "name", None)
        if cf_name and cf_name.lower().strip() == normalized_name:
            return extract_cf_value(cf) if isinstance(cf, dict) else extract_cf_value(cf)

    return None
```

**3. `extract_cf_value`** -- already in `cf_utils.py`, no change needed.

After extraction, both B and C replace their private methods with calls to these shared functions. B's `_extract_field_value` (58 lines) is deleted entirely and replaced with `extract_cf_value` from `cf_utils`.

### 2.3 Impact on B and C

**System B (`CascadingFieldResolver`)** changes:
- Delete `_class_to_entity_type` (lines 650-675)
- Delete `_get_custom_field_value` (lines 566-589)
- Delete `_extract_field_value` (lines 591-648)
- Import and call `class_to_entity_type`, `get_custom_field_value`, `extract_cf_value` from `cf_utils`
- Net reduction: ~105 lines

**System C (`CascadeViewPlugin`)** changes:
- Delete `_class_to_entity_type` (lines 503-527)
- Delete `_get_custom_field_value` (lines 417-440)
- Delete `_get_custom_field_value_from_dict` (lines 442-467)
- Import and call `class_to_entity_type`, `get_custom_field_value` from `cf_utils`
- `_extract_field_value` already delegates to `cf_utils.extract_cf_value`; can be inlined or kept as thin wrapper
- Net reduction: ~70 lines

---

## 3. Design: Office Resolution Mechanism

### 3.1 The Key Architectural Question

How to eliminate `UnitExtractor._extract_office_async` (111 lines) given that:
- Office resolves `task.name` (a model attribute), not a custom field
- The cascade mechanism's `_get_custom_field_value()` only searches `task.custom_fields`
- `CascadingFieldDef` already has `source_field: str | None` (fields.py line 58)
- `Business.CascadingFields.BUSINESS_NAME` already declares `source_field="name"` (business.py line 331)
- `CascadingFieldDef.get_value()` already handles `source_field` at the model layer (fields.py lines 83-85)
- Neither B nor C's `_traverse_parent_chain` checks `field_def.source_field`

### 3.2 Options Evaluated

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A. Wire `source_field` into resolvers | Teach `_traverse_parent_chain` to check `field_def.source_field` and use `getattr(task, source_field)` when set | Completes the existing design intent; zero new abstractions; `BUSINESS_NAME` CascadingFieldDef already exists; office becomes `cascade:Business Name` in schema | Requires changes to value extraction in both B and C's traversal loops |
| B. Keep `_extract_office_async`, refactor to use shared traversal | Extract traversal loop to shared function, keep office as derived field | No cascade mechanism changes | Doesn't eliminate the duplication -- just moves it; still a bespoke method |
| C. Create "name cascade" special case | New CascadingFieldDef subclass or flag | Explicit about the difference | Unnecessary new abstraction; `source_field` already exists for this |

**Selected: Option A** -- Wire `source_field` into DataFrame-layer resolvers.

### 3.3 Rationale

`source_field` was designed for exactly this use case. The model layer already has:
- `CascadingFieldDef.source_field` attribute (fields.py line 58)
- `CascadingFieldDef.get_value()` that dispatches on `source_field` (fields.py lines 83-85)
- `Business.CascadingFields.BUSINESS_NAME` with `source_field="name"` (business.py line 331)

The DataFrame-layer resolvers simply never wired this path. Completing the wiring is the minimal, correct fix. Zero new abstractions.

### 3.4 Implementation Details

**Step 1**: Create `get_field_value(task_or_dict, field_def: CascadingFieldDef) -> Any` in `cf_utils.py`:

```python
def get_field_value(
    task_or_dict: Any,
    field_def: CascadingFieldDef,
) -> Any:
    """Extract field value using CascadingFieldDef rules.

    If field_def.source_field is set, uses getattr/dict-get on that attribute.
    Otherwise, searches custom_fields by field_def.name.
    """
    if field_def.source_field:
        if isinstance(task_or_dict, dict):
            return task_or_dict.get(field_def.source_field)
        return getattr(task_or_dict, field_def.source_field, None)
    return get_custom_field_value(task_or_dict, field_def.name)
```

**Step 2**: Both B and C's `_traverse_parent_chain` replace `_get_custom_field_value(current, field_def.name)` with `get_field_value(current, field_def)`.

**Step 3**: In `UNIT_SCHEMA` (`dataframes/schemas/unit.py`), change the `office` column:

```python
# Before:
ColumnDef(
    name="office",
    dtype="Utf8",
    nullable=True,
    source=None,  # Derived from business.office_phone lookup
    description="Office name (derived)",
)

# After:
ColumnDef(
    name="office",
    dtype="Utf8",
    nullable=True,
    source="cascade:Business Name",  # Resolves Business ancestor's task.name
    description="Office name (cascades from Business via source_field)",
)
```

**Step 4**: Delete `UnitExtractor._extract_office_async` and `_extract_office` methods entirely.

**Step 5**: The existing `BaseExtractor._extract_column_async` cascade handling (base.py lines 325-329) will resolve `cascade:Business Name` through `CascadingFieldResolver.resolve_async()`, which looks up `BUSINESS_NAME` in the registry, finds `source_field="name"`, and calls `get_field_value()` which returns `task.name` from the Business ancestor. No changes to `BaseExtractor` needed.

### 3.5 Verification

The `BUSINESS_NAME` CascadingFieldDef is already registered in the cascading field registry via `Business.CascadingFields.BUSINESS_NAME`. The registry key is `"business name"` (normalized). The `cascade:Business Name` source in the schema strips the `cascade:` prefix, yielding `"Business Name"`, which matches the registry entry.

Test verification:
- Existing `test_unit_cascade_resolution.py` tests Business -> Unit cascade resolution
- New test needed: verify `cascade:Business Name` resolves to `task.name` of Business ancestor (not a custom field)

---

## 4. B/C Consolidation Pattern (Primary/Fallback Contract)

### 4.1 Current State

B (`CascadingFieldResolver`) is the entry point. When `cascade_plugin` (C) is injected via `BaseExtractor._get_cascading_resolver()` (base.py lines 109-129), B delegates `resolve_async` to C entirely (cascading.py lines 224-229). When no `cascade_plugin` is present, B uses its own `_traverse_parent_chain` with API calls.

### 4.2 Design: C Primary, B Fallback (No Change to Entry Point)

The current delegation pattern is already correct:
- `BaseExtractor` creates `CascadingFieldResolver` (B) as the entry point
- `BaseExtractor._get_cascading_resolver()` injects `CascadeViewPlugin` (C) when `unified_store` is available
- B's `resolve_async` delegates to C when `cascade_plugin` is present
- B's own `_traverse_parent_chain` activates only when no `cascade_plugin` is available (API fallback)

**No architectural change needed for the primary/fallback contract.** The consolidation work is purely DRY:
1. Both B and C call shared functions from `cf_utils` instead of maintaining private copies
2. Both B and C use `get_field_value(task_or_dict, field_def)` for `source_field`-aware extraction
3. B's `_traverse_parent_chain` remains as the no-cache fallback path

### 4.3 What B Retains After DRY Extraction

After removing duplicated utility methods, B retains:
- `__init__` and configuration (cascade_plugin, hierarchy_resolver)
- `resolve_async` with delegation to C or fallback to own traversal
- `_traverse_parent_chain` (API-based traversal -- different from C's cache-based traversal)
- `warm_parents` and batch fetching infrastructure
- `_fetch_parent_async` (API call with local cache)
- `_get_parent_gid` (simple parent extraction)
- `_get_hierarchy_resolver` (lazy init)
- `TaskParentFetcher` class (unchanged)

Estimated B size after consolidation: ~400 lines (down from 676, ~40% reduction).
Estimated C size after consolidation: ~370 lines (down from 541, ~30% reduction).

---

## 5. Sprint Decomposition

### 5.1 Sprint 1: DRY Extraction + `source_field` Wiring

**Objective**: Extract shared functions to `cf_utils.py`, wire `source_field` into both resolvers, eliminate `_extract_office_async`.

**File Manifest**:

| File | Action | Changes |
|------|--------|---------|
| `src/autom8_asana/dataframes/views/cf_utils.py` | MODIFY | Add `class_to_entity_type()`, `get_custom_field_value()`, `get_field_value()`. Add `EntityType` import. (~50 lines added) |
| `src/autom8_asana/dataframes/resolver/cascading.py` | MODIFY | Delete `_class_to_entity_type`, `_get_custom_field_value`, `_extract_field_value`. Replace with `cf_utils` imports. Update `_traverse_parent_chain` to use `get_field_value()`. (~105 lines removed, ~10 lines added) |
| `src/autom8_asana/dataframes/views/cascade_view.py` | MODIFY | Delete `_class_to_entity_type`, `_get_custom_field_value`, `_get_custom_field_value_from_dict`. Replace with `cf_utils` imports. Update `_traverse_parent_chain` to use `get_field_value()`. (~70 lines removed, ~10 lines added) |
| `src/autom8_asana/dataframes/schemas/unit.py` | MODIFY | Change `office` column source from `None` to `"cascade:Business Name"`. Update description. (~2 lines changed) |
| `src/autom8_asana/dataframes/extractors/unit.py` | MODIFY | Delete `_extract_office`, `_extract_office_async` methods. (~115 lines removed) |
| `tests/unit/dataframes/views/test_cf_utils.py` | MODIFY or CREATE | Add tests for `class_to_entity_type()`, `get_custom_field_value()`, `get_field_value()` |
| `tests/unit/dataframes/test_cascading_resolver.py` | MODIFY | Update tests that mock `_get_custom_field_value`, `_extract_field_value`, `_class_to_entity_type` to use new `cf_utils` paths. Add `source_field` test cases. |
| `tests/unit/dataframes/views/test_cascade_view.py` | MODIFY | Update tests for method removal, add `source_field` test cases |
| `tests/integration/test_unit_cascade_resolution.py` | MODIFY | Add test for `cascade:Business Name` resolving `task.name` |
| `tests/integration/test_cascading_field_resolution.py` | MODIFY | Add `source_field` integration test |

**Net line change estimate**: ~290 lines removed, ~100 lines added = ~190 net reduction in production code.

### 5.2 Sprint 2: Verification + QA Adversary

**Objective**: QA pass to verify green-to-green, edge case testing, regression check.

**File Manifest**:

| File | Action | Changes |
|------|--------|---------|
| Tests from Sprint 1 | VERIFY | Full test suite pass |
| Edge case tests | ADD | `source_field=None` (default path unchanged), missing `name` attribute, dict-based `source_field` extraction, root fallback with `source_field` |

### 5.3 Why Single Sprint (S1) Is Sufficient for Implementation

The 4 duplicated methods and office extraction all touch the same 5 production files. The coupling is tight -- extracting shared functions to `cf_utils.py` and updating callers in B, C, and UnitExtractor is one atomic change. Splitting into two implementation sprints would create an intermediate state where some duplication is resolved and some is not, making the code harder to reason about.

**Recommendation: 1 implementation sprint (S1) + 1 QA sprint (S2).**

---

## 6. ADR: UnitExtractor Dedicated vs SchemaExtractor Migration

### ADR-WS3-001: UnitExtractor Should Remain a Dedicated Extractor

**Status**: PROPOSED

**Context**: After removing `_extract_office_async` and `_extract_office`, UnitExtractor's remaining bespoke methods are:
- `_extract_vertical_id` (stub, returns None)
- `_extract_max_pipeline_stage` (stub, returns None)
- `_extract_type` (returns `"Unit"` always)
- `_create_row` (returns `UnitRow`)

Of these, `_extract_type` and `_create_row` are standard overrides that `SchemaExtractor` also provides via `DataFrameSchema.task_type`. The two stub methods return `None`, which is the default behavior when `source=None` and no `_extract_{name}` method exists on `BaseExtractor`.

**Decision**: Keep `UnitExtractor` as a dedicated extractor.

**Rationale**:
1. **`_extract_vertical_id` and `_extract_max_pipeline_stage` are not permanently None.** Both have explicit `TODO` comments noting they require model lookups (`Vertical` model and `UnitHolder` model respectively). When implemented, they will contain non-trivial logic that `SchemaExtractor` cannot provide.
2. **`UnitRow` is a distinct model.** `UnitExtractor._create_row` produces `UnitRow.model_validate(data)`. Migrating to `SchemaExtractor` would require making `SchemaExtractor` aware of `UnitRow`, which adds complexity without simplification.
3. **Unit has the most derived fields of any entity.** Even post-WS3, Unit will have 2 derived fields awaiting implementation. Premature migration to `SchemaExtractor` would need reversal when those stubs are implemented.
4. **Precedent**: `ContactExtractor` remains dedicated for similar reasons (bespoke derived fields).

**Consequences**:
- UnitExtractor goes from 264 lines to ~150 lines (post-office removal)
- Future work to implement `vertical_id` and `max_pipeline_stage` will happen in UnitExtractor
- If both stubs remain `None` indefinitely (>6 months), reconsider migration

**Alternatives Rejected**:
- Migrate to SchemaExtractor now: Would require reversal when stubs are implemented. Premature optimization.
- Hybrid approach (SchemaExtractor with hooks): Adds complexity. The current `BaseExtractor` convention-based dispatch (`_extract_{name}`) already provides this cleanly.

---

## 7. Risk Matrix

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | `source_field` wiring breaks custom field resolution | Low | High | `get_field_value` checks `source_field` first, falls through to `get_custom_field_value` when `source_field is None`. All existing CascadingFieldDefs have `source_field=None` except `BUSINESS_NAME`. Default behavior is unchanged. |
| R2 | Test mocks reference deleted private methods | Medium | Medium | Grep all test files for `_get_custom_field_value`, `_extract_field_value`, `_class_to_entity_type`. Update mock targets to `cf_utils` module functions. Per MEMORY.md: always check test mocks when changing method signatures. |
| R3 | `cascade:Business Name` resolution fails in cache-backed path (C) | Medium | High | C's `_traverse_parent_chain` works with dict data. `get_field_value` handles dicts via `task_or_dict.get(source_field)`. Cache entries include `"name"` field (per `STANDARD_TASK_OPT_FIELDS` which includes `"name"`). Verified: `"name"` is in the standard opt_fields. |
| R4 | `_get_custom_field_value_from_dict` removal breaks C's dict-based lookups | Low | High | Replaced by `get_custom_field_value(task_or_dict, field_name)` which handles both Task objects and dicts. Tests must cover dict path. |
| R5 | UnitExtractor tests assume `_extract_office_async` exists | Medium | Low | `office` column changes from `source=None` (derived) to `source="cascade:Business Name"`. Tests calling `_extract_office_async` directly need update. Tests going through `extract_async` will use cascade path automatically. |
| R6 | `EntityType` import in `cf_utils.py` creates circular import | Low | Medium | `EntityType` is an enum in `models.business`. `cf_utils` is in `dataframes.views`. Import chain: `dataframes.views.cf_utils` -> `models.business.EntityType`. This does NOT create a cycle (dataframes depends on models, not vice versa). |

---

## 8. Test Strategy

### 8.1 Existing Test Coverage

| Test File | Lines | Focus |
|-----------|-------|-------|
| `tests/unit/dataframes/test_cascading_resolver.py` | 832 | System B unit tests |
| `tests/unit/dataframes/views/test_cascade_view.py` | 695 | System C unit tests |
| `tests/integration/test_cascading_field_resolution.py` | 656 | End-to-end cascade resolution |
| `tests/integration/test_unit_cascade_resolution.py` | 343 | Unit-specific cascade integration |
| `tests/unit/test_cascade_registry_audit.py` | 87 | Registry completeness |
| `tests/unit/models/business/test_cascading_registry.py` | 247 | Registry unit tests |
| `tests/unit/dataframes/test_unit_schema.py` | 203 | Unit schema validation |
| **Total** | **3,063** | |

### 8.2 Tests to Add

1. **`cf_utils` unit tests**: `class_to_entity_type`, `get_custom_field_value` (Task and dict inputs), `get_field_value` with `source_field` set and `source_field=None`
2. **`source_field` integration test**: `cascade:Business Name` resolving `task.name` from Business ancestor through full stack (BaseExtractor -> CascadingFieldResolver -> CascadeViewPlugin -> cf_utils)
3. **`source_field` with dict data**: Verify cache-backed path (C) correctly extracts `task_data["name"]` when `source_field="name"`
4. **Root fallback with `source_field`**: Business at root of chain (no parent), `source_field="name"` still resolves
5. **Regression**: Existing `cascade:Office Phone` resolution unchanged (verifies `source_field=None` path)

### 8.3 Tests to Modify

1. Tests that mock `CascadingFieldResolver._get_custom_field_value` -- update mock target
2. Tests that mock `CascadingFieldResolver._extract_field_value` -- update mock target
3. Tests that mock `CascadingFieldResolver._class_to_entity_type` -- update mock target
4. Tests that call `UnitExtractor._extract_office_async` directly -- remove or replace with cascade resolution test
5. Tests that assert `UNIT_SCHEMA` office column `source=None` -- update to `source="cascade:Business Name"`

### 8.4 Green-to-Green Gate

- Baseline: 10,582 passed, 0 failed
- Expectation: 10,582 + new tests, 0 failed
- Pre-existing failures excluded: `test_adversarial_pacing`, `test_paced_fetch`, `test_cache_errors_logged_as_warnings`
- Full suite command: `.venv/bin/pytest tests/ -x -q --timeout=60`

---

## 9. Summary of Changes by File

| File | Sprint | Lines Removed | Lines Added | Net |
|------|--------|--------------|-------------|-----|
| `dataframes/views/cf_utils.py` | S1 | 0 | ~50 | +50 |
| `dataframes/resolver/cascading.py` | S1 | ~105 | ~10 | -95 |
| `dataframes/views/cascade_view.py` | S1 | ~70 | ~10 | -60 |
| `dataframes/extractors/unit.py` | S1 | ~115 | 0 | -115 |
| `dataframes/schemas/unit.py` | S1 | ~2 | ~2 | 0 |
| Test files (various) | S1+S2 | ~30 | ~80 | +50 |
| **Total** | | **~322** | **~152** | **-170** |

---

## Appendix A: File Reference

| File | Path | Role |
|------|------|------|
| System B | `src/autom8_asana/dataframes/resolver/cascading.py` | Legacy resolver (entry point, fallback) |
| System C | `src/autom8_asana/dataframes/views/cascade_view.py` | Cache-backed resolver (primary) |
| Shared utils | `src/autom8_asana/dataframes/views/cf_utils.py` | DRY target for extraction functions |
| UnitExtractor | `src/autom8_asana/dataframes/extractors/unit.py` | Unit-specific extractor |
| BaseExtractor | `src/autom8_asana/dataframes/extractors/base.py` | Extraction framework + cascade wiring |
| CascadingFieldDef | `src/autom8_asana/models/business/fields.py` | Field definition with `source_field` |
| Business model | `src/autom8_asana/models/business/business.py` | `BUSINESS_NAME` CascadingFieldDef |
| Unit schema | `src/autom8_asana/dataframes/schemas/unit.py` | Column definitions |

## Appendix B: Dependency Graph (Post-WS3)

```
BaseExtractor (base.py)
  |
  +-- creates CascadingFieldResolver (cascading.py)
  |     |
  |     +-- delegates to CascadeViewPlugin (cascade_view.py) when available
  |     |     |
  |     |     +-- calls cf_utils.get_field_value()
  |     |     +-- calls cf_utils.get_custom_field_value()
  |     |     +-- calls cf_utils.extract_cf_value()
  |     |     +-- calls cf_utils.class_to_entity_type()
  |     |
  |     +-- fallback: own _traverse_parent_chain (uses API)
  |           |
  |           +-- calls cf_utils.get_field_value()
  |           +-- calls cf_utils.get_custom_field_value()
  |           +-- calls cf_utils.class_to_entity_type()
  |
  +-- UnitExtractor (unit.py)
        |
        +-- office column: source="cascade:Business Name"
        |   (resolved via CascadingFieldResolver -> source_field="name" -> task.name)
        |
        +-- _extract_vertical_id (stub)
        +-- _extract_max_pipeline_stage (stub)
```
