# QA Gate G2 Validation Report -- SSoT Convergence & Reliability Hardening

**Date**: 2026-02-17
**QA Agent**: qa-adversary
**Scope**: S0 (quick wins) + WS1-S1 + WS1-S2 + WS1-S3 (descriptor-driven auto-wiring)
**Branch**: feature/ssot-convergence
**Gate Type**: Mid-initiative gate (WS1 complete)

---

## 1. Test Suite Results

### Full Suite Execution

```
Command: .venv/bin/pytest tests/ -x -q --timeout=60
Duration: ~3:19 (198.93s)
```

| Metric | Count |
|--------|-------|
| **Passed** | 10,550 |
| **Failed** | 0 |
| **Skipped** | 45 |
| **xfailed** | 2 |
| **Pre-existing failures** | 0 encountered |

**Baseline comparison**: Target was 10,550 passed. Exact match.

### Targeted Test Suite Results

| Test File | Passed | Failed | Sprint |
|-----------|--------|--------|--------|
| `tests/unit/core/test_entity_registry.py` | 87 | 0 | S1 |
| `tests/unit/dataframes/test_auto_wire.py` | 13 | 0 | S2 |
| `tests/unit/query/test_hierarchy.py` | 17 | 0 | S3 |
| `tests/unit/models/business/test_fields.py` | 31 | 0 | S3 |
| `tests/unit/dataframes/test_schema_extractor.py` | 44 (combined) | 0 | S0 |

---

## 2. Axis-by-Axis Verification

### Axis 1: Behavioral Equivalence -- PASS

Every extractor factory resolution produces the expected extractor class:

| Task Type | Extractor Class | Verification |
|-----------|----------------|--------------|
| `Unit` | `UnitExtractor` | Descriptor-driven, path resolves |
| `Contact` | `ContactExtractor` | Descriptor-driven, path resolves |
| `Business` | `SchemaExtractor` | No extractor_class_path, schema has extra columns |
| `Offer` | `SchemaExtractor` | No extractor_class_path, schema has extra columns |
| `AssetEdit` | `SchemaExtractor` | No extractor_class_path, schema has extra columns |
| `AssetEditHolder` | `SchemaExtractor` | No extractor_class_path, schema has 1 extra column |
| `*` | `DefaultExtractor` | Hardcoded wildcard path, bypasses descriptors |
| Unknown type | `DefaultExtractor` | Base-only schema fallback |

All schema extractors produce correct row dicts matching schema column counts.

### Axis 2: Triad Completeness -- PASS

Entities with schema but no extractor emit structured validation warnings:

| Entity | Warning Event | Extra Columns |
|--------|--------------|---------------|
| `business` | `schema_without_extractor` | 5 |
| `offer` | `schema_without_extractor` | 11 |
| `asset_edit` | `schema_without_extractor` | 21 |
| `asset_edit_holder` | `schema_without_extractor` | 1 |

Entities with full triads (schema + extractor + row model): `unit`, `contact`.

Entities with schema but no row model also emit `schema_without_row_model` warnings for: `business`, `offer`, `asset_edit`, `asset_edit_holder`.

All dotted paths in descriptors (schema_module_path, extractor_class_path, row_model_class_path) resolve successfully at test time (test class `TestDataFramePathResolution`).

### Axis 3: Circular Import Safety -- PASS

Sequential import test verified with no circular dependency errors:

1. `autom8_asana.core.entity_registry` -- 17 entities loaded
2. `autom8_asana.dataframes.models.registry.SchemaRegistry` -- 6 task types discovered
3. `autom8_asana.query.hierarchy.ENTITY_RELATIONSHIPS` -- 8 relationships
4. `autom8_asana.models.business.fields.get_cascading_field_registry` -- 9 cascading fields
5. `autom8_asana.dataframes.builders.base.DataFrameBuilder` -- imported cleanly

Design mitigation: All consumers import `get_registry()` inside function bodies (deferred), not at module scope. Validation checks 6a-6c test path syntax only at import time; actual import resolution deferred to test time per ARCH doc section 6.4.

### Axis 4: Contract Preservation -- PASS

**SchemaRegistry.list_task_types():**
```
Actual:   ['AssetEdit', 'AssetEditHolder', 'Business', 'Contact', 'Offer', 'Unit']
Expected: ['AssetEdit', 'AssetEditHolder', 'Business', 'Contact', 'Offer', 'Unit']
```
Exact match. BASE_SCHEMA at `*` key excluded from list (by design).

**find_relationship() for all original pairs:**

| Source | Target | Join Key | Result |
|--------|--------|----------|--------|
| business | unit | office_phone | Found |
| business | contact | office_phone | Found |
| business | offer | office_phone | Found |
| unit | offer | office_phone | Found |

All 4 original pairs verified in both directions. No false positives for unrelated pairs (asset_edit-business, process-business, hours-unit all return None).

**ENTITY_RELATIONSHIPS superset:**
8 total relationships (was 4 hardcoded). The 4 additional entries come from bidirectional join_key declarations:

```
business -> unit via office_phone
business -> contact via office_phone
business -> offer via office_phone
unit -> business via office_phone     (NEW: from unit.join_keys)
unit -> offer via office_phone        (NEW: from unit.join_keys)
contact -> business via office_phone  (NEW: from contact.join_keys)
offer -> unit via office_phone        (NEW: from offer.join_keys)
offer -> business via office_phone    (NEW: from offer.join_keys)
```

No duplicate tuples detected.

### Axis 5: Validation Integrity -- PASS

All validation checks tested with deliberately broken descriptors:

| Check | Input | Expected | Actual |
|-------|-------|----------|--------|
| 6a | `schema_module_path="NoModulePart"` | ValueError | ValueError |
| 6b | `extractor_class_path="NoModulePart"` | ValueError | ValueError |
| 6c | `row_model_class_path="NoModulePart"` | ValueError | ValueError |
| 6d | Schema without extractor | Warning (no raise) | Warning (no raise) |
| 6e | Schema without row model | Warning (no raise) | Warning (no raise) |
| 6f | Extractor without schema | ValueError | ValueError |
| 7 | `cascading_field_provider=True` without `model_class_path` | ValueError | ValueError |

Additional adversarial inputs to `_resolve_dotted_path()`:

| Input | Result |
|-------|--------|
| Bad module name | ImportError |
| Bad attribute name | AttributeError |
| Empty string | ImportError ("Invalid dotted path") |
| `"..."` (dots only) | TypeError |
| String with spaces | ModuleNotFoundError |

The global registry passes all integrity checks at import time (confirmed by `test_global_registry_passes_all_new_checks`).

### Axis 6: Cascade Equivalence -- PASS

**Cascading field registry entries:**

| Provider | Fields | Count |
|----------|--------|-------|
| Business | office phone, company id, business name, primary contact phone | 4 |
| Unit | platforms, vertical, booking type, mrr, weekly ad spend | 5 |
| **Total** | | **9** |

Only `business` and `unit` have `cascading_field_provider=True`. All other descriptors correctly have `False`.

Registry rebuild is deterministic: two calls to `_build_cascading_field_registry()` produce identical key sets. Global singleton reset and re-initialization produces identical content (verified by object identity difference + key set equality).

All cascading_field_provider descriptors have model classes with `CascadingFields` inner class (verified by `hasattr` check).

### Axis 7: Regression -- PASS

Full suite: **10,550 passed, 0 failed, 45 skipped, 2 xfailed**.

Exact match to baseline. No regressions introduced.

---

## 3. S0 Quick Win Verification

| Fix | Before | After | Verified |
|-----|--------|-------|----------|
| BUSINESS_SCHEMA.task_type | `"business"` (lowercase) | `"Business"` (PascalCase) | PASS: `BUSINESS_SCHEMA.task_type == 'Business'` |
| Offer mrr dtype | `"Utf8"` | `"Decimal"` | PASS: `mrr_col.dtype == 'Decimal'` |
| Offer weekly_ad_spend dtype | `"Utf8"` | `"Decimal"` | PASS: `was_col.dtype == 'Decimal'` |
| MRR dedup documentation | N/A | Scope/description added | PASS: Metric definition has dedup docs |

---

## 4. Thread Safety Verification

**SchemaRegistry._ensure_initialized() under concurrency:**
10 threads simultaneously calling `SchemaRegistry.get_instance().list_task_types()` after `reset()`:
- All 10 threads returned identical sorted task type lists
- No deadlocks, no exceptions
- Double-checked locking pattern confirmed working

**_CASCADING_FIELD_REGISTRY global singleton:**
- Manual reset + re-init produces new object with identical content
- No thread safety issues (lazy init is called once per process lifecycle in production)

---

## 5. Adversarial Test Summary

| Test # | Description | Result |
|--------|-------------|--------|
| ADV-1 | _resolve_dotted_path with typo in module | ImportError raised |
| ADV-2 | _resolve_dotted_path with typo in attr | AttributeError raised |
| ADV-3 | _resolve_dotted_path with empty string | ImportError raised |
| ADV-4 | _resolve_dotted_path with dots only | TypeError raised |
| ADV-5 | _resolve_dotted_path with spaces | ModuleNotFoundError raised |
| ADV-6 | 10 concurrent SchemaRegistry initializations | All identical results |
| ADV-7 | SchemaRegistry reset + re-init cycle | Idempotent results |
| ADV-8 | S0 BUSINESS_SCHEMA task_type fix | Correct PascalCase |
| ADV-9 | S0 Offer dtype fixes | Decimal for mrr + weekly_ad_spend |
| ADV-10 | Partially-wired entity validation warnings | 4 entities emit warnings |
| ADV-11 | ENTITY_RELATIONSHIPS duplicate check | 0 duplicates in 8 entries |
| ADV-12 | Relationship derivation determinism | Two calls identical |
| ADV-13 | Cascading registry singleton reset | Clean rebuild |
| ADV-14 | CascadingFields inner class presence | Verified for all providers |
| ADV-15 | Extractor factory for all 8 task types | All correct class types |

**0 defects found.**

---

## 6. Known Risks and Accepted Trade-offs

### R1: Syntax-Only Validation at Import Time (LOW)

**Risk**: Validation checks 6a-6c only verify dotted path syntax (module.attr format) at module load time. A typo in the module name (e.g., `autom8_asana.dataframes.schemas.typo.SCHEMA`) would pass syntax validation but fail at runtime when `_resolve_dotted_path()` is called.

**Mitigation**: The `TestDataFramePathResolution` test class performs actual import resolution for every populated path. CI catches path typos at test time, not production time. Additionally, `_resolve_dotted_path()` raises clear `ImportError`/`AttributeError` with the exact path that failed, making debugging straightforward.

**Assessment**: Accepted. Full import resolution at module load would create circular import cycles (per ARCH doc section 6.4).

### R2: Relationship Superset (LOW)

**Risk**: ENTITY_RELATIONSHIPS now has 8 entries instead of the original 4. The 4 new entries are bidirectional mirrors (e.g., `unit -> business` in addition to `business -> unit`). Consumers using `find_relationship()` are unaffected (it checks both directions), but consumers iterating `ENTITY_RELATIONSHIPS` directly would see additional entries.

**Mitigation**: `find_relationship()` already searched both directions, so the superset is benign. Direct iteration is only used in `get_joinable_types()`, which deduplicates via `sorted(set(...))`. All existing test assertions pass.

**Assessment**: Accepted. The superset makes implicit bidirectional relationships explicit.

### R3: _CASCADING_FIELD_REGISTRY Global Mutable (LOW)

**Risk**: The `_CASCADING_FIELD_REGISTRY` global uses a None-check lazy init pattern without a lock. In theory, two threads could race to initialize it simultaneously.

**Mitigation**: In production, this is called once during Lambda cold start (single-threaded initialization). In tests, the conftest root fixture resets singleton registries. The registry is immutable after construction (dict is not mutated after `_build_cascading_field_registry()` returns).

**Assessment**: Accepted. No practical concurrency risk in Lambda runtime.

---

## 7. Security Assessment

No security-relevant changes in this scope:
- No new endpoints, authentication changes, or input validation changes
- No PII handling changes
- No new external integrations
- `_resolve_dotted_path()` only resolves paths defined in frozen descriptor tuples (not user-supplied input)
- No shell execution, subprocess calls, or file I/O changes

---

## 8. Documentation Impact Assessment

No user-facing behavior changes. All changes are internal refactoring (descriptor-driven auto-wiring replaces hardcoded logic with identical output). No API surface changes, no new commands, no deprecations. No documentation updates needed.

---

## 9. Backward Compatibility Assessment

| Area | Status | Notes |
|------|--------|-------|
| EntityDescriptor (4 new fields) | Compatible | All new fields have None/False defaults |
| SchemaRegistry.list_task_types() | Compatible | Same set returned |
| _create_extractor() | Compatible | Same extractor classes for all task types |
| ENTITY_RELATIONSHIPS | Compatible | Superset (8 vs 4), find_relationship() behavior unchanged |
| get_cascading_field_registry() | Compatible | Same 9 fields from same 2 providers |
| BUSINESS_SCHEMA.task_type | Fixed | "business" -> "Business" (corrects SM-003 bug) |
| Offer mrr/weekly_ad_spend dtype | Fixed | "Utf8" -> "Decimal" (corrects dtype mismatch) |

---

## 10. Release Recommendation

### GO

**Rationale:**

1. Full test suite passes with exact baseline match: 10,550 passed, 0 failed
2. All 7 QA axes verified with 0 defects found
3. 15 adversarial tests passed across all attack surfaces
4. Behavioral equivalence confirmed for all entity types
5. Thread safety verified under 10-thread concurrent access
6. No security vulnerabilities detected
7. All known risks are LOW severity with adequate mitigations
8. Backward compatibility preserved across all consumer interfaces

**Confidence level**: HIGH. The auto-wiring refactoring produces identical outputs to the hardcoded logic it replaces, validated through both existing tests (87 + 13 + 17 + 31 = 148 targeted tests) and 15 adversarial probes.

---

## Test Evidence

```
# Full suite
.venv/bin/pytest tests/ -x -q --timeout=60
10550 passed, 45 skipped, 2 xfailed in 198.93s

# Core tests
.venv/bin/pytest tests/unit/core/test_entity_registry.py -x -q --timeout=60
87 passed in 0.18s

# Auto-wire tests
.venv/bin/pytest tests/unit/dataframes/test_auto_wire.py -x -q --timeout=60
13 passed in 0.03s

# Hierarchy tests
.venv/bin/pytest tests/unit/query/test_hierarchy.py -x -q --timeout=60
17 passed in 0.11s

# Fields tests
.venv/bin/pytest tests/unit/models/business/test_fields.py -x -q --timeout=60
31 passed in 0.05s

# Schema extractor tests
.venv/bin/pytest tests/unit/dataframes/test_schema_extractor.py \
  tests/unit/dataframes/test_schema_extractor_completeness.py \
  tests/unit/dataframes/test_schema_extractor_adversarial.py -x -q --timeout=60
44 passed in 0.09s
```
