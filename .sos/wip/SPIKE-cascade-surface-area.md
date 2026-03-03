---
type: spike
---

# SPIKE: Cascade Surface Area — Manual Registries vs Dynamic Derivation

**Date:** 2026-03-03
**Context:** After WS-1/WS-2/WS-3/WS-6 from the n8n consumer bugfix, audit where we're pushing the same boulder (manual registries) instead of exploding it (dynamic derivation from existing metadata).

---

## The Core Problem

The codebase has **two authoritative sources** that fully describe cascade relationships:

1. **DataFrameSchema columns** — each `ColumnDef` with `source="cascade:Office Phone"` declares WHAT cascades and WHERE it comes from
2. **CascadingFieldDef registry** — each `Business.CascadingFields.OFFICE_PHONE` or `Unit.CascadingFields.MRR` declares WHO provides the cascade and to WHOM

These two sources are the truth. Everything else should be derived from them. Instead, we have **6 places** that manually re-state this information — and every one of them is already stale or incomplete.

---

## Authoritative Metadata APIs (already exist)

### DataFrameSchema.has_cascade_columns()
`dataframes/models/schema.py:135` — Returns bool. Already used in WS-1.

**Missing method:** No way to get the actual (column_name, asana_field_name) pairs. Only binary yes/no.

### ColumnDef.source
`dataframes/models/schema.py:38` — String field. Format: `"cascade:Office Phone"`. Parse to get Asana field name.

### get_cascading_field_registry()
`models/business/fields.py:324` — Returns `dict[str, (owner_class, CascadingFieldDef)]`. Maps normalized field names to their provider class and definition. Dynamically discovered from all entities with `cascading_field_provider=True`.

### EntityDescriptor.cascading_field_provider
`core/entity_registry.py:159` — Bool flag. Today: Business=True, Unit=True. All others=False.

### CascadingFieldDef.target_types
`models/business/fields.py:24` — Set of entity type names that receive this cascade. Carries the full dependency graph.

---

## 6 Hardcoding Violations

### V-1: CASCADE_CRITICAL_FIELDS — static list instead of schema introspection

**File:** `dataframes/builders/cascade_validator.py:25-27`

```python
CASCADE_CRITICAL_FIELDS: list[tuple[str, str]] = [
    ("office_phone", "Office Phone"),  # (column_name, cascade_field_name)
]
```

**Problem:** Manually lists 1 of 11 cascade column instances across all schemas. The schema already declares `source="cascade:Office Phone"` on the columns. Adding a new cascade column to any schema requires someone to remember to also update this list — and nobody will.

**Dynamic replacement:** Derive from schema at validation time:
```python
def _get_cascade_fields_for_schema(schema: DataFrameSchema) -> list[tuple[str, str]]:
    return [
        (col.name, col.source[8:])  # "cascade:X" -> "X"
        for col in schema.columns
        if col.source and col.source.startswith("cascade:")
    ]
```

**Impact:** Validates ALL cascade fields (office_phone, vertical, mrr, weekly_ad_spend, office) for ALL entity types, automatically. Zero maintenance.

---

### V-2: cascade_field_mapping hardcoded in progressive.py WS-2

**File:** `api/preload/progressive.py:445-447`

```python
cascade_field_mapping={"office_phone": "Office Phone"}
```

**Problem:** Manually declares which Business columns to extract for store population. Misses Company ID, Business Name, Primary Contact Phone. And if Unit also needs store population (it does — Offer cascades MRR/spend from Unit), a second hardcoded mapping would be needed.

**Dynamic replacement:** Derive from the entity's schema. For a cascade SOURCE entity, the fields it provides are declared in `CascadingFieldDef`:
```python
def _get_cascade_provider_mapping(entity_type: str) -> dict[str, str]:
    """For a cascade SOURCE entity, get {df_column: asana_field} for fields it provides."""
    registry = get_cascading_field_registry()
    schema = get_schema(to_pascal_case(entity_type))
    mapping = {}
    for col in schema.columns:
        src = col.source
        if src and src.startswith("cf:"):
            asana_name = src[3:]
            # Check if this field is declared as cascading
            entry = registry.get(asana_name.lower().strip())
            if entry and entry[0].__name__.lower() == entity_type:
                mapping[col.name] = asana_name
    return mapping
```

Or simpler: iterate the CascadingFieldDef registry for this owner, cross-reference against the schema's columns.

---

### V-3: `entity_type == "business"` — hardcoded cascade source check

**File:** `api/preload/progressive.py:439` and `progressive.py:475`

```python
if entity_type == "business" and shared_store is not None:   # line 439
if entity_type != "business" and shared_store is not None:   # line 475
```

**Problem:** Hardcodes "business" as the only cascade source. Unit is ALSO a cascade source (provides MRR, Weekly Ad Spend, Vertical, Platforms, Booking Type to Offer/Process). This is why GAP-2 exists — Unit's data never enters the store.

**Dynamic replacement:**
```python
def _is_cascade_source(entity_type: str) -> bool:
    """Check if entity type provides cascade fields to others."""
    desc = get_registry().get_by_name(entity_type)
    return desc is not None and desc.cascading_field_provider
```

Then:
```python
if _is_cascade_source(entity_type) and shared_store is not None:
    # Populate store (works for BOTH business AND unit)

if not _is_cascade_source(entity_type) and shared_store is not None and _has_cascade_fields(schema):
    # Run cascade validation
```

**Impact:** Unit data automatically enters the store. Offer cascade for MRR/spend/vertical just works. No GAP-2.

---

### V-4: Business-first split — hardcoded 2-phase ordering

**File:** `api/preload/progressive.py:459-466` (renumbered after WS-1/WS-2 edits)

```python
business_configs = [(gid, etype) for gid, etype in project_configs if etype == "business"]
other_configs = [(gid, etype) for gid, etype in project_configs if etype != "business"]
```

**Problem:** Hardcodes a 2-phase split (business first, everything else parallel). But the cascade dependency graph requires a 3-level topological ordering:
1. Business (provides to Unit, Contact, Offer, AssetEdit)
2. Unit (provides to Offer, Process)
3. Everything else (Contact, Offer, AssetEdit, AssetEditHolder)

If Unit and Offer run in parallel (as they do now in `other_configs`), Offer's cascade validation may execute before Unit's store population completes.

**Dynamic replacement:** Derive ordering from `CascadingFieldDef.target_types`:
```python
def _derive_cascade_ordering(entity_types: list[str]) -> list[list[str]]:
    """Topological sort of entity types by cascade dependency.

    Returns list of batches. Each batch can run in parallel.
    Batches must run sequentially.
    """
    registry = get_cascading_field_registry()
    # Build dependency edges: source -> targets
    deps: dict[str, set[str]] = defaultdict(set)
    for field_name, (owner_class, field_def) in registry.items():
        source = owner_class.__name__.lower()
        if field_def.target_types:
            for target in field_def.target_types:
                deps[target.lower()].add(source)

    # Topological sort into batches
    remaining = set(entity_types)
    batches = []
    while remaining:
        # Find entities with no unsatisfied dependencies
        ready = {e for e in remaining if not (deps.get(e, set()) & remaining)}
        if not ready:
            ready = remaining  # Break cycles
        batches.append(sorted(ready))
        remaining -= ready
    return batches
```

Result: `[["business"], ["unit"], ["contact", "offer", "asset_edit", "asset_edit_holder"]]`

---

### V-5: Lambda default_priority — hardcoded entity ordering

**File:** `lambda_handlers/cache_warmer.py:577-585`

```python
default_priority = [
    "business", "unit", "offer", "contact",
    "asset_edit", "asset_edit_holder", "unit_holder",
]
```

**Problem:** Same as V-4. Manually specified ordering instead of derived. We just patched this from "unit first" to "business first" (WS-6), but it's still manual. If a third cascade source entity were added, someone would need to remember to reorder this list.

**Dynamic replacement:** Same `_derive_cascade_ordering()` function from V-4, flattened:
```python
batches = _derive_cascade_ordering(warmable_entity_types)
default_priority = [e for batch in batches for e in batch]
```

---

### V-6: Missing DataFrameSchema.get_cascade_columns() method

**File:** `dataframes/models/schema.py`

**Problem:** The schema has `has_cascade_columns()` (bool) but no method to EXTRACT cascade column info. Every consumer must manually parse `col.source` strings. This forces V-1 and V-2 to exist.

**Fix:** Add a single method to `DataFrameSchema`:
```python
def get_cascade_columns(self) -> list[tuple[str, str]]:
    """Extract (column_name, asana_field_name) pairs for cascade columns."""
    result = []
    for col in self.columns:
        if col.source and col.source.startswith("cascade:"):
            result.append((col.name, col.source[8:]))
    return result
```

This is the primitive that eliminates V-1 and simplifies V-2.

---

## Entity x Cascade Field Matrix (Complete)

### 11 Cascade Column Instances Across 5 Entity Types

| Entity | Column | Source Declaration | Provider | In CASCADE_CRITICAL_FIELDS? |
|--------|--------|-------------------|----------|---------------------------|
| unit | office | cascade:Business Name | Business | NO |
| unit | office_phone | cascade:Office Phone | Business | YES (only one) |
| contact | office_phone | cascade:Office Phone | Business | YES |
| contact | vertical | cascade:Vertical | Unit | NO |
| offer | office_phone | cascade:Office Phone | Business | YES |
| offer | vertical | cascade:Vertical | Unit | NO |
| offer | mrr | cascade:MRR | Unit | NO |
| offer | weekly_ad_spend | cascade:Weekly Ad Spend | Unit | NO |
| asset_edit | office_phone | cascade:Office Phone | Business | YES |
| asset_edit | vertical | cascade:Vertical | Unit | NO |
| asset_edit_holder | office_phone | cascade:Office Phone | Business | YES |

**The validator checks 5 of 11 instances (the office_phone ones). 6 instances are unprotected.**

### 2 Cascade Source Entities

| Entity | CascadingFieldDef Declarations | Target Types |
|--------|-------------------------------|-------------|
| **Business** | Office Phone, Company ID, Business Name, Primary Contact Phone | Unit, Offer, Process, Contact |
| **Unit** | Platforms, Vertical, Booking Type, MRR, Weekly Ad Spend | Offer, Process |

### Cascade Dependency Graph (for topological ordering)

```
Level 0: business (no cascade dependencies)
Level 1: unit (depends on business)
Level 2: offer, contact, asset_edit, asset_edit_holder (depend on business + unit)
```

---

## Cache Population Path Coverage (Post WS-1/2/3/6)

| Path | Cascade Validation | Shared Store | Source-First Ordering | Gap |
|------|-------------------|-------------|----------------------|-----|
| **S3 fast-path** | YES (WS-1, but only office_phone) | YES (WS-2, Business only) | 2-phase (Business → rest) | V-1, V-2, V-3, V-4 |
| **Progressive builder** | YES (Step 5.5, but only office_phone) | YES (all entities) | YES | V-1 |
| **Legacy preload** | NO | NO | NO | Accepted (ADR-011) |
| **SWR refresh** | YES (via builder, per-client store) | Per-client only | NO | WS-8 |
| **Admin rebuild** | YES (via builder, per-client store) | Per-client only | NO | WS-8 |
| **Lambda warmer** | Depends on strategy | Per-entity only | Manual (V-5) | V-5, GAP-4 |

---

## Recommendation: Explode the Boulder

Instead of patching each gap individually (R-1 through R-7 from the previous analysis), fix the **root cause**: replace all 6 manual registries with dynamic derivation from schema + CascadingFieldDef metadata.

### Implementation: 3 Primitives That Eliminate All 6 Violations

**Primitive 1: `DataFrameSchema.get_cascade_columns()`** (V-6 fix, ~10 lines)
- Add method to schema.py
- Eliminates V-1 (CASCADE_CRITICAL_FIELDS becomes dynamic)
- Simplifies V-2 (cascade_field_mapping derived from schema)

**Primitive 2: `_is_cascade_source(entity_type)` + `_get_cascade_provider_fields(entity_type)`** (~20 lines)
- Queries EntityDescriptor.cascading_field_provider + CascadingFieldDef registry
- Eliminates V-3 (entity_type == "business" checks become generic)
- Eliminates V-2 (store population mapping derived for any source entity)

**Primitive 3: `_derive_cascade_ordering(entity_types)`** (~30 lines)
- Topological sort from CascadingFieldDef.target_types dependency graph
- Eliminates V-4 (progressive preload) and V-5 (Lambda warmer) hardcoded ordering
- Automatically handles future cascade source entities

### What Changes After These 3 Primitives

| Before | After |
|--------|-------|
| `CASCADE_CRITICAL_FIELDS = [("office_phone", "Office Phone")]` | `schema.get_cascade_columns()` — validates ALL cascade fields for ANY entity |
| `cascade_field_mapping={"office_phone": "Office Phone"}` | `_get_cascade_provider_fields("business")` — populates ALL fields Business provides |
| `entity_type == "business"` | `_is_cascade_source(entity_type)` — works for Business AND Unit |
| `business_configs` / `other_configs` 2-phase | `_derive_cascade_ordering(types)` → 3-phase: Business → Unit → rest |
| `default_priority = ["business", "unit", ...]` | `_derive_cascade_ordering(warmable_types)` — derived from registry |
| Store only has Business data | Store has Business AND Unit data (V-3 fix makes Unit a source too) |
| Offer cascade for MRR/spend fails | Offer cascade for MRR/spend resolves (Unit in store, correct ordering) |

### Effort Estimate

| Primitive | Lines | Files | Risk |
|-----------|-------|-------|------|
| P-1: `get_cascade_columns()` | ~10 | schema.py | None — additive method |
| P-2: Source detection + field mapping | ~20 | New helper or existing module | Low — reads existing registry |
| P-3: Topological ordering | ~30 | New helper or existing module | Low — pure function |
| Refactor callers (validator, progressive, warmer) | ~60 | 3 files | Moderate — replacing hardcodes |
| Tests | ~80 | 2-3 test files | — |

Total: ~200 lines changed, 3-4 files modified, ~3h work.

---

## Follow-Up Actions

- [ ] Implement P-1: `DataFrameSchema.get_cascade_columns()` method
- [ ] Implement P-2: `_is_cascade_source()` + `_get_cascade_provider_fields()` helpers
- [ ] Implement P-3: `_derive_cascade_ordering()` topological sort
- [ ] Refactor `cascade_validator.py` to use P-1 instead of static list
- [ ] Refactor `progressive.py` to use P-2 for store population + P-3 for ordering
- [ ] Refactor `cache_warmer.py` to use P-3 for default_priority
- [ ] Tests for all 3 primitives + integration tests for the refactored callers
- [ ] WS-8 (SWR + Admin) — still needed separately (different class of problem: per-client stores)
