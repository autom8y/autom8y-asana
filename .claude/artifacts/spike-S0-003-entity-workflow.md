# Spike S0-003: Entity Addition Workflow

**Status:** Complete
**Date:** 2026-02-04
**Traced Entity:** `asset_edit` (and derivative `asset_edit_holder`)
**Related:** Opportunity B1 (Entity Knowledge Registry) from architectural-opportunities.md

---

## 1. Summary

Adding `asset_edit` required changes across **16 files in 10 subsystems**. The touch points span model definition, detection/bootstrap, schema, registry, discovery, resolution, cache warming, API routes, and documentation strings. At least one location (`api/routes/resolver.py`) was missed during initial addition and only caught during Sprint 3 refactoring (RF-L21). The `query/hierarchy.py` relationship registry still has no `asset_edit` entries today.

---

## 2. Ordered Touch-Point Checklist

The following is the minimum set of changes required when adding a new entity type, ordered by dependency. Later steps depend on earlier ones being correct.

### Layer 0: Foundation (no dependencies)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 1 | `src/autom8_asana/core/entity_types.py` | Add to `ENTITY_TYPES` list (and `ENTITY_TYPES_WITH_DERIVATIVES` if derivative types exist) | `list[str]` -- plain snake_case strings |
| 2 | `src/autom8_asana/models/business/detection/types.py` | Add enum member to `EntityType` (e.g., `ASSET_EDIT_HOLDER = "asset_edit_holder"`) | `Enum` value = snake_case string |

### Layer 1: Model Definition (depends on Layer 0)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 3 | `src/autom8_asana/models/business/asset_edit.py` | New entity model file. Extends base class (e.g., `Process`). Must define `PRIMARY_PROJECT_GID: ClassVar[str \| None]`, `Fields` inner class, navigation descriptors | Pydantic model with `ClassVar` for GID, `PrivateAttr` for cached refs |
| 4 | `src/autom8_asana/models/business/business.py` | (a) Define holder class (e.g., `AssetEditHolder` via `HolderFactory`), (b) Add `_asset_edit_holder` `PrivateAttr` on `Business`, (c) Add entry to `HOLDER_KEY_MAP` dict, (d) Add `asset_edit_holder` property, (e) Wire into `_build_holder` dispatch, (f) Add to `_invalidate_refs` | `HolderFactory` metaclass kwargs, `PrivateAttr`, `ClassVar[dict]` entry |
| 5 | `src/autom8_asana/models/business/__init__.py` | Export new model classes in imports and `__all__` | Python import + `__all__` list |

### Layer 2: Detection & Bootstrap (depends on Layer 1)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 6 | `src/autom8_asana/models/business/detection/config.py` | Add `EntityTypeInfo` entry to `ENTITY_TYPE_INFO` dict for the holder type. Sets `name_pattern`, `display_name`, `emoji`, `holder_attr`, `child_type` | `dict[EntityType, EntityTypeInfo]` |
| 7 | `src/autom8_asana/models/business/_bootstrap.py` | Add `(EntityType.ASSET_EDIT_HOLDER, AssetEditHolder)` to `ENTITY_MODELS` list. Note: AssetEdit itself has no dedicated `EntityType` enum (detected via project GID, not enum) | `list[tuple[EntityType, type]]` |
| 8 | `src/autom8_asana/models/business/hydration.py` | Wire holder into `_estimate_hydration_calls` and `_collect_success_branches` | Hardcoded holder attribute checks |

### Layer 3: DataFrame Schema (depends on Layer 1)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 9 | `src/autom8_asana/dataframes/schemas/asset_edit.py` | New schema file. Define `ColumnDef` list and `DataFrameSchema` with `name`, `task_type` (PascalCase), `columns`, `version` | `DataFrameSchema` instance |
| 10 | `src/autom8_asana/dataframes/schemas/__init__.py` | Export new schema constants | Python imports + `__all__` |
| 11 | `src/autom8_asana/dataframes/models/registry.py` | Import schema and register in `_ensure_initialized` with PascalCase key (e.g., `"AssetEdit"`) | `self._schemas["AssetEdit"] = ASSET_EDIT_SCHEMA` |

### Layer 4: Resolution & Discovery (depends on Layers 1-3)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 12 | `src/autom8_asana/services/resolver.py` | Add entry to `ENTITY_ALIASES` dict | `dict[str, list[str]]` -- alias chain for field normalization |
| 13 | `src/autom8_asana/services/universal_strategy.py` | Add entry to `DEFAULT_KEY_COLUMNS` dict | `dict[str, list[str]]` -- columns for DynamicIndex |
| 14 | `src/autom8_asana/services/discovery.py` | Add to `ENTITY_MODEL_MAP` dict. If project name does not normalize automatically, add explicit mapping to `EXPLICIT_MAPPINGS` in `_normalize_project_name` | `dict[str, type]` model map; `dict[str, str]` name mapping |

### Layer 5: Cache & Lambda (depends on Layers 3-4)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 15 | `src/autom8_asana/cache/dataframe/warmer.py` | Add to `priority` default list in `CacheWarmer` dataclass | `list[str]` field default |
| 16 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | Add to `default_priority` list in `_warm_cache_async` (appears twice: docstring and code) | `list[str]` literal |

### Layer 6: API Routes (depends on Layers 0, 3-4)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 17 | `src/autom8_asana/api/routes/resolver.py` | **Implicitly covered** by `set(ENTITY_TYPES)` after RF-L21 fix. Before the fix, this was a hardcoded 4-item set that missed `asset_edit`. | `set[str]` from canonical import |
| 18 | `src/autom8_asana/api/routes/admin.py` | **Implicitly covered** by `set(ENTITY_TYPES)` import. | `set[str]` from canonical import |
| 19 | `src/autom8_asana/api/routes/dataframes.py` | Docstrings and error messages list entity types as prose. Must update manually. | Inline string literals |

### Layer 7: Query Joins (optional, depends on schema)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 20 | `src/autom8_asana/query/hierarchy.py` | Add `EntityRelationship` entries for the new entity type. **Currently missing for asset_edit.** | `list[EntityRelationship]` |

### Layer 8: SDK Bridge (auto-derived)

| # | File | What Changes | Format |
|---|------|-------------|--------|
| 21 | `src/autom8_asana/cache/schema_providers.py` | **Auto-derived** from `ENTITY_TYPES_WITH_DERIVATIVES`. No manual change needed if Layer 0 is correct. | Iterates canonical list |

---

## 3. Metadata Format Summary

| Location | Key Format | Value Format | Lookup Direction |
|----------|-----------|-------------|-----------------|
| `core/entity_types.py` | N/A (list position) | `"asset_edit"` snake_case string | Imported by consumers |
| `detection/types.py` EntityType | Enum member name `ASSET_EDIT_HOLDER` | Enum value `"asset_edit_holder"` | Enum access |
| `detection/config.py` ENTITY_TYPE_INFO | `EntityType` enum key | `EntityTypeInfo` dataclass | Dict lookup by EntityType |
| `_bootstrap.py` ENTITY_MODELS | Index position | `(EntityType, ModelClass)` tuple | Sequential iteration |
| `business.py` HOLDER_KEY_MAP | `"asset_edit_holder"` string | `("Asset Edits", "art")` tuple | Dict lookup by holder key |
| `SchemaRegistry` | `"AssetEdit"` PascalCase | `DataFrameSchema` instance | Dict lookup by task_type |
| `resolver.py` ENTITY_ALIASES | `"asset_edit"` snake_case | `["process"]` alias list | Dict lookup by entity_type |
| `universal_strategy.py` DEFAULT_KEY_COLUMNS | `"asset_edit"` snake_case | `["office_phone", ...]` column list | Dict lookup by entity_type |
| `discovery.py` ENTITY_MODEL_MAP | `"asset_edit"` snake_case | Model class reference | Dict lookup by entity_type |
| `discovery.py` EXPLICIT_MAPPINGS | `"paid content"` lowercase | `"asset_edit"` snake_case | Project name normalization |
| `warmer.py` priority | N/A (list position) | `"asset_edit"` snake_case | Sequential iteration |
| `query/hierarchy.py` | N/A (list items) | `EntityRelationship` dataclass | Linear scan |

---

## 4. Test Coverage Analysis

| Touch Point | Validated by Tests? | How Discovered if Wrong |
|------------|-------------------|----------------------|
| `core/entity_types.py` | Indirectly -- admin adversarial tests check `VALID_ENTITY_TYPES` includes `asset_edit` | Import-time if tests reference it |
| `detection/types.py` EntityType enum | Yes -- detection unit tests | Compile/import time |
| `detection/config.py` ENTITY_TYPE_INFO | Indirectly -- detection tests exercise name patterns | Runtime: holder detection fails silently |
| `_bootstrap.py` ENTITY_MODELS | Indirectly -- bootstrap test checks registered count | Runtime: Tier 1 detection fails, falls to lower tiers |
| `business.py` holder plumbing | Yes -- `test_asset_edit.py` checks inheritance, holder wiring | Runtime: hydration returns None for holder |
| `SchemaRegistry` registration | Yes -- `test_routes_dataframes.py` checks `asset_edit` schema accessible | Runtime: schema fallback to BASE_SCHEMA |
| `resolver.py` ENTITY_ALIASES | No explicit test for asset_edit alias chain | Runtime: field normalization silently fails |
| `universal_strategy.py` DEFAULT_KEY_COLUMNS | No explicit test for asset_edit key columns | Runtime: resolution returns empty results |
| `discovery.py` model/name mapping | No explicit test for asset_edit discovery | Runtime: entity project not found, logged as warning |
| `warmer.py` priority list | Indirectly -- cache warmer lambda tests | Runtime: entity skipped during warm |
| `lambda_handlers/cache_warmer.py` | Indirectly -- lambda handler tests check response shape | Runtime: entity not warmed |
| `api/routes/resolver.py` SUPPORTED_ENTITY_TYPES | Yes (after RF-L21) -- adversarial tests check `asset_edit` not in fallback would fail | **Was runtime-only before RF-L21 fix** |
| `api/routes/dataframes.py` docstrings | **No** -- prose strings are never validated | Never discovered (cosmetic) |
| `query/hierarchy.py` relationships | **No** -- test explicitly asserts `find_relationship("offer", "asset_edit") is None` | Runtime: cross-entity joins unavailable |

### Key Finding: 5 of 14 functional touch points have NO direct test coverage for asset_edit.

---

## 5. Pain Points and Failure Modes

### P1: Stale Hardcoded Lists (Severity: HIGH)

**Observed:** `api/routes/resolver.py` had a hardcoded 4-item `SUPPORTED_ENTITY_TYPES` set that did not include `asset_edit`. This was only discovered during Sprint 3 code smell audit (SM-S3-002) and fixed by RF-L21.

**Root Cause:** Multiple subsystems maintained independent entity type lists instead of importing from a canonical source.

**Current Mitigations:** RF-L21 changed the resolver route to `set(ENTITY_TYPES)`. The admin route already uses the canonical import. However, several locations still use hardcoded lists:
- `cache/dataframe/warmer.py` line 130-137 (hardcoded priority list)
- `lambda_handlers/cache_warmer.py` lines 319, 387-394 (hardcoded in two places)
- `services/universal_strategy.py` lines 38-45 (hardcoded DEFAULT_KEY_COLUMNS)
- `services/resolver.py` lines 252-259 (hardcoded ENTITY_ALIASES)
- `query/hierarchy.py` lines 33-58 (hardcoded ENTITY_RELATIONSHIPS)

### P2: Name Convention Mismatch (Severity: MEDIUM)

**Observed:** `asset_edit` requires snake_case-to-PascalCase conversion for SchemaRegistry lookups. Python's `.title()` produces `"Asset_Edit"` (wrong). The `to_pascal_case()` utility was created specifically to handle this. Any new multi-word entity type would hit the same issue.

**Impact:** Silent schema fallback to BASE_SCHEMA if PascalCase conversion is wrong.

### P3: Non-Standard Project Name Mapping (Severity: MEDIUM)

**Observed:** The Asana project for `asset_edit` is named "Paid Content", which does not normalize to `asset_edit` via the standard algorithm. Required an explicit `EXPLICIT_MAPPINGS` entry in `discovery.py`.

**Impact:** Discovery silently logs "entity_project_not_found" warning but continues. No hard failure -- the entity simply cannot be resolved at runtime.

### P4: Missing Query Hierarchy Registration (Severity: LOW-MEDIUM)

**Observed:** `query/hierarchy.py` has no `EntityRelationship` for `asset_edit`. Tests explicitly assert `find_relationship("offer", "asset_edit") is None`. This means cross-entity joins involving `asset_edit` are impossible via the query engine.

**Impact:** Feature gap rather than bug. Users cannot use the query join system with asset_edit entities.

### P5: Holder vs. Entity Asymmetry in EntityType Enum (Severity: LOW)

**Observed:** `AssetEditHolder` has an `EntityType.ASSET_EDIT_HOLDER` enum member, but `AssetEdit` itself does NOT have a dedicated `EntityType` member. It is detected via `PRIMARY_PROJECT_GID` (Tier 1 project membership) and conceptually uses `EntityType.PROCESS` as its base type.

**Impact:** Adds cognitive load. New developers may assume every entity type in `core/entity_types.py` has a corresponding `EntityType` enum member, but `asset_edit` does not.

### P6: Dual-Location Priority Lists (Severity: LOW)

**Observed:** Cache warming priority is defined in BOTH `cache/dataframe/warmer.py` (dataclass default) AND `lambda_handlers/cache_warmer.py` (function local). These must be kept in sync manually. The warmer module defines priority as `["offer", "unit", ...]` while the lambda handler uses `["unit", "business", ...]` -- different ordering.

---

## 6. Dependency Graph

```
core/entity_types.py ──────────────────────────┐
         |                                       |
         v                                       v
detection/types.py                    api/routes/admin.py
         |                            api/routes/resolver.py
         v                            cache/schema_providers.py
detection/config.py
         |
         v
models/business/asset_edit.py ──────> dataframes/schemas/asset_edit.py
models/business/business.py                |
         |                                  v
         v                          dataframes/schemas/__init__.py
models/business/__init__.py                |
         |                                  v
         v                          dataframes/models/registry.py
models/business/_bootstrap.py              |
models/business/hydration.py               v
         |                          services/resolver.py (ENTITY_ALIASES)
         |                          services/universal_strategy.py (KEY_COLUMNS)
         v                                 |
services/discovery.py <────────────────────┘
         |
         v
cache/dataframe/warmer.py
lambda_handlers/cache_warmer.py
query/hierarchy.py (OPTIONAL - currently missing)
```

---

## 7. Recommendations for B1 (Entity Knowledge Registry)

Based on this trace, an Entity Knowledge Registry should:

1. **Consolidate all per-entity metadata into one declaration** -- eliminating the need to touch 16+ files. A single registry entry should derive: schema columns, key columns, aliases, hierarchy relationships, detection config, cache priority, and API route inclusion.

2. **Validate completeness at import/startup time** -- a registry integrity check that cross-references `ENTITY_TYPES` against `SchemaRegistry`, `ENTITY_ALIASES`, `DEFAULT_KEY_COLUMNS`, `ENTITY_TYPE_INFO`, and `ENTITY_RELATIONSHIPS`. This would have caught the RF-L21 issue before runtime.

3. **Auto-derive PascalCase task_type keys** -- the registry should handle the `snake_case -> PascalCase` mapping internally, eliminating the manual `to_pascal_case()` calls scattered across modules.

4. **Unify cache warming priority** -- a single source for entity warming order, not two divergent hardcoded lists.

5. **Make query/hierarchy.py data-driven** -- entity relationships should be declarative metadata in the registry, not a separate hardcoded list.

Estimated reduction: A well-designed registry could reduce the entity addition workflow from **16 manual touch points** to **1 declaration + 2 files** (the model class file and the schema definition file, which contain genuinely unique logic).
