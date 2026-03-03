# SMELL-REPORT: COMPAT-PURGE

**Producer**: code-smeller
**Date**: 2026-02-25
**Session**: session-20260225-160455-f6944d8b

---

## Phase 0 Pre-Flight Results

### Test Baseline

```
11675 passed, 42 skipped, 2 xfailed, 547 warnings in 209.20s
```

All workstreams must maintain green-to-green against this baseline.

### Re-Export Consumer Census

**Result: CLEAR** — Zero sibling repos import from `autom8_asana`.

Sibling repos checked: `autom8y-data`, `autom8y-ads`, `autom8y-sms`.
None declare `autom8_asana` as a dependency. All re-exports are safe to remove.

### D-002 CloudWatch Gate

**Status: DEFERRED** — Cannot verify from local environment. Per PROMPT_0, D-002 is
in-scope only if zero traffic confirmed. Leaving out of scope for this initiative
(sunset date 2026-06-01 per HTTP headers already in place).

---

## Findings Summary

| Severity | Category | Count | Est. LOC Reduction |
|----------|----------|-------|--------------------|
| S1 | Backward-compat re-exports | 11 | -200 to -300 |
| S1 | Dead stubs/aliases | 3 | -50 to -80 |
| S2 | Deprecated functions/parameters | 3 | -60 to -100 |
| S2 | Dead migration scaffolding | 3 | -40 to -60 |
| S3 | Dual-path logic (legacy branch) | 6 | -150 to -250 |
| S3 | Hardcoded bespoke workarounds | 3 | -30 to -50 |
| S4 | Deferred (out of scope) | 7 | N/A |
| **Total** | | **29 in-scope + 7 deferred** | **-530 to -840** |

---

## S1: CRITICAL — High ROI, Low Risk

### RE-01: `core/schema.py` — Entire module is re-export shim
- **File**: `src/autom8_asana/core/schema.py`
- **What**: Module exists solely to re-export `get_schema_version()` from `dataframes.models.registry`
- **Evidence**: Docstring: "This module exists for backward compatibility"
- **Fix**: Update all importers to use `dataframes.models.registry`, delete file
- **Consumer verification required**: grep for `from autom8_asana.core.schema import`

### RE-02: `models/business/detection/types.py` — EntityType re-export
- **File**: `src/autom8_asana/models/business/detection/types.py:20-22`
- **What**: Re-exports `EntityType` from `core.types` with compat comment
- **Evidence**: "Re-exported from core.types for backward compatibility"
- **Fix**: Update importers to use `core.types.EntityType`, remove re-export
- **Risk**: EntityType is heavily used; import path updates will be numerous

### RE-03: `models/business/detection/__init__.py` — Package re-exports
- **File**: `src/autom8_asana/models/business/detection/__init__.py:72-124`
- **What**: 30+ re-exported items in `__all__` for backward compat
- **Fix**: Update importers to use canonical locations, trim `__all__`
- **Note**: Depends on RE-02 (EntityType re-export in types.py)

### RE-04: `clients/data/client.py` — PII + metrics re-exports
- **File**: `src/autom8_asana/clients/data/client.py:66-77`
- **What**: Re-exports `mask_phone_number`, `_mask_pii_in_string` from `_pii.py`
- **Evidence**: "Re-exported here for backward compatibility"
- **Fix**: Update importers to use `clients.data._pii`, remove re-exports

### RE-05: `automation/seeding.py` — field_utils re-exports
- **File**: `src/autom8_asana/automation/seeding.py:31-36`
- **What**: Re-exports `get_field_attr`, `normalize_custom_fields` from `core.field_utils`
- **Evidence**: "Re-exported from core.field_utils for backward compatibility"
- **Fix**: Update importers, remove re-exports

### RE-06: `cache/__init__.py` — `dataframe_cache` lazy re-export
- **File**: `src/autom8_asana/cache/__init__.py:295-299`
- **What**: `__getattr__` lazy-load provides moved module for backward compat
- **Evidence**: "Provide the moved module for backward compatibility"
- **Fix**: Update importers to use canonical module path, remove `__getattr__`

### RE-07: `api/routes/resolver.py` — Model re-exports for tests
- **File**: `src/autom8_asana/api/routes/resolver.py:76-85`
- **What**: Re-exports 5 resolver models (`ResolutionCriterion`, etc.) for test imports
- **Evidence**: "Re-export models for backward compatibility (tests import these)"
- **Fix**: Update test imports to use `resolver_models`, remove from `__all__`

### RE-08: `models/business/patterns.py` — Module-level constant aliases
- **File**: `src/autom8_asana/models/business/patterns.py:132-135`
- **What**: `PATTERN_CONFIG` and `PATTERN_PRIORITY` exposed as module-level constants
- **Evidence**: "For backward compatibility, expose as module-level constants"
- **Fix**: Update consumers to use function calls, remove aliases

### RE-09: `core/logging.py` — Module-level logger alias
- **File**: `src/autom8_asana/core/logging.py:104`
- **What**: `logger = get_logger("autom8_asana")` for backward compatibility
- **Evidence**: "Module-level logger for backward compatibility and convenience"
- **Fix**: Check if any module imports `from autom8_asana.core.logging import logger`
- **Risk**: Low — most modules call `get_logger(__name__)` directly

### RE-10: `cache/models/freshness_unified.py` — Old name type aliases
- **File**: `src/autom8_asana/cache/models/freshness_unified.py:10-13`
- **What**: Type aliases mapping old names to new names for backward compat
- **Fix**: Update importers, remove aliases

### RE-11: `cache/__init__.py` — Freshness + HierarchyTracker re-exports
- **File**: `src/autom8_asana/cache/__init__.py:142, 175-183`
- **What**: Re-exports `Freshness` model and `HierarchyTracker` with defensive ImportError fallback
- **Fix**: Part of freshness.py removal (ST-01) and cache __init__ cleanup

### ST-01: `cache/models/freshness.py` — Entire file is compat alias
- **File**: `src/autom8_asana/cache/models/freshness.py` (entire file)
- **What**: Deprecated module — `Freshness` is alias for `FreshnessIntent`
- **Evidence**: Docstring: "backward-compatible alias for FreshnessIntent"
- **Fix**: Update all `from cache.models.freshness import Freshness` → canonical path, delete file
- **Consumer**: 1 re-export in `cache/__init__.py:142`, 1 test in `test_reorg_imports.py`

### ST-02: `lifecycle/engine.py` — `_StubReopenService` dead stub
- **File**: `src/autom8_asana/lifecycle/engine.py:845-866`
- **What**: Stub for `ReopenService` "when module is not yet available"
- **Evidence**: `ReopenService` EXISTS at `lifecycle/reopen.py:47`. Import will succeed.
- **Fix**: Remove `_StubReopenService` class, remove try/except in `_import_reopen_service()`,
  replace with direct import
- **LOC**: ~25 lines removed

### ST-03: `dataframes/cache_integration.py` — `warm_struc_async` alias
- **File**: `src/autom8_asana/dataframes/cache_integration.py:451-456`
- **What**: Method alias: `warm_struc_async()` → `warm_dataframe_async()`
- **Evidence**: Docstring: "Alias for warm_dataframe_async (backward compatibility)"
- **Consumer**: 1 test at `tests/unit/dataframes/test_cache_integration.py:743`
- **Fix**: Update test to call `warm_dataframe_async()`, remove alias method

---

## S2: HIGH — High ROI, Medium Risk

### DEP-01: `DefaultResolver.extract_value()` — deprecated `expected_type` parameter
- **File**: `src/autom8_asana/dataframes/resolver/default.py:150-200`
- **Protocol**: `src/autom8_asana/dataframes/resolver/protocol.py:72-92`
- **What**: `expected_type: type | None = None` deprecated in favor of `column_def`
- **Evidence**: "The expected_type parameter is deprecated in favor of column_def"
- **Consumers**: 2 test uses (`test_resolver.py:837, 1287`), internal coercion logic
- **Fix**: Remove parameter from protocol + default resolver + mock resolver, update tests
- **Risk**: Medium — affects resolver protocol contract

### DEP-02: `ProcessType.GENERIC` — preserved backward compat enum value
- **File**: `src/autom8_asana/models/business/process.py:86`
- **What**: Enum member preserved solely for backward compatibility
- **Evidence**: "GENERIC is preserved for backward compatibility with existing code"
- **Consumers**: 2 fallback return statements in same file (lines 445, 454)
- **Fix**: Determine proper fallback behavior, remove GENERIC, update return statements
- **Risk**: Medium — changing fallback behavior for unmatchable pipeline types

### DEP-03: `CustomFieldAccessor strict=False` — legacy lenient mode
- **File**: `src/autom8_asana/models/custom_field_accessor.py:37-57, 324-386`
- **What**: `strict=False` allows returning name as-is on lookup failure (legacy behavior)
- **Evidence**: Docstring: "If False, return name as-is (legacy, deprecated)"
- **Consumers**: No explicit `strict=False` calls found in src/
- **Fix**: Remove `strict` parameter, always use strict behavior
- **Risk**: Medium — tests may construct with `strict=False`

### MIG-01: `BuildResult.to_legacy()` + `ProgressiveBuildResult`
- **File**: `src/autom8_asana/dataframes/builders/build_result.py:207-229`
- **File**: `src/autom8_asana/dataframes/builders/progressive.py:76-100`
- **File**: `src/autom8_asana/dataframes/builders/__init__.py:58, 79`
- **What**: Legacy result type + conversion method, superseded by `BuildResult`
- **Evidence**: "Replaces ProgressiveBuildResult with strictly more information"
- **Consumers**: `to_legacy()` called only in 1 test file (`test_build_result.py`)
- **Fix**: Remove `to_legacy()`, remove `ProgressiveBuildResult` class, update test + `__init__`

### MIG-02: `builders/__init__.py` — compatibility shim docstring
- **File**: `src/autom8_asana/dataframes/builders/__init__.py:9`
- **What**: Docstring references "compatibility shim" from completed migration
- **Fix**: Update docstring (trivial)

### MIG-03: `cache/integration/factory.py` — MIGRATION-PLAN comment
- **File**: `src/autom8_asana/cache/integration/factory.py:228-229`
- **What**: Comment references `MIGRATION-PLAN-legacy-cache-elimination RF-001` (completed)
- **Fix**: Update or remove comment (trivial)

---

## S3: MEDIUM — Medium ROI, Higher Risk

### DP-01: `automation/config.py` — `pipeline_templates` fallback
- **File**: `src/autom8_asana/automation/config.py:112-144, 175-183`
- **What**: Dual-path: check `pipeline_stages` first, fall back to `pipeline_templates`
- **Consumers**: 55 references across src/ and tests/
- **Fix**: Migrate all `pipeline_templates` → `pipeline_stages`, remove fallback
- **Risk**: High consumer count; requires systematic migration

### DP-02: `_defaults/cache.py` + `protocols/cache.py` — dual-method surface
- **File**: `src/autom8_asana/_defaults/cache.py:35-127`
- **File**: `src/autom8_asana/protocols/cache.py:44-191`
- **What**: "Original methods (backward compatible)" vs "New versioned methods"
- **Fix**: Check if any consumer calls old methods, collapse if unused
- **Risk**: Protocol change affects all implementations (NullCacheProvider, TieredCacheProvider, backends)

### DP-03: Cache backends — connection manager fallback
- **File**: `src/autom8_asana/cache/backends/s3.py:213-238`
- **File**: `src/autom8_asana/cache/backends/redis.py:189-214`
- **What**: New path delegates to connection_manager; legacy path uses internal client
- **Fix**: Verify all callers provide connection_manager, remove internal fallback
- **Risk**: Runtime initialization order; must verify DI wiring

### DP-04: `models/business/base.py` — `_children_cache` dual-write
- **File**: `src/autom8_asana/models/business/base.py:145-147, 175-177`
- **What**: Writes to subclass `CHILDREN_ATTR` AND legacy `_children_cache` simultaneously
- **Consumer**: `resolution/context.py:430` checks `_children_cache` as fallback
- **Fix**: Update context.py to use `CHILDREN_ATTR`, remove dual-write
- **Risk**: Medium — affects resolution context children discovery

### DP-05: `detection/facade.py` — `HOLDER_KEY_MAP` fallback detection
- **File**: `src/autom8_asana/models/business/detection/facade.py:541-588`
- **What**: Tier 1-4 detection with fallback to legacy HOLDER_KEY_MAP name/emoji matching
- **Fix**: Verify Tier 1-4 covers all cases, remove fallback (or log-only first)
- **Risk**: Holder detection is critical path; false negatives break entity classification

### DP-06: `automation/workflows/insights_export.py` — `LEGACY_ATTACHMENT_PATTERN`
- **File**: `src/autom8_asana/automation/workflows/insights_export.py:56-62, 574-582`
- **What**: Transitional dual-cleanup: `.html` (new) + `.md` (legacy) attachment formats
- **Evidence**: Comment: "transitional, one cycle"
- **Fix**: Remove `LEGACY_ATTACHMENT_PATTERN` constant and legacy cleanup branch
- **Risk**: Low — one-cycle transitional, should be safe now

### HW-01: `config.py` — "address" legacy alias + `_LEGACY_TTL_EXCLUDE`
- **File**: `src/autom8_asana/config.py:104-117`
- **What**: `DEFAULT_ENTITY_TTLS["address"]` hardcoded, `_LEGACY_TTL_EXCLUDE` filter
- **Evidence**: "address is a legacy alias for location preserved for backward compat"
- **Fix**: Remove address entry, remove `_LEGACY_TTL_EXCLUDE`, update config
- **Risk**: Low — purely internal configuration

### HW-02: `services/gid_lookup.py` — hardcoded key columns
- **File**: `src/autom8_asana/services/gid_lookup.py:252-253, 275-276`
- **What**: `key_columns = ["office_phone", "vertical"]` hardcoded default
- **Evidence**: "for backwards compatibility"
- **Fix**: Remove default, require explicit key_columns or derive from schema
- **Risk**: Medium — callers relying on default must be updated

### HW-03: `services/resolver.py` — `_apply_legacy_mapping`
- **File**: `src/autom8_asana/services/resolver.py:528-559`
- **What**: Legacy field name normalization wrapper
- **Evidence**: "Replaces static LEGACY_FIELD_MAPPING with dynamic algorithm"
- **Fix**: If the dynamic algorithm handles all cases, remove wrapper
- **Risk**: Medium — field resolution is query-critical

---

## S4: DEFERRED — Out of Scope

### D-QUERY: POST `/v1/query/{entity_type}` deprecated endpoint
- **File**: `src/autom8_asana/api/routes/query.py:424-552`
- **Reason**: CloudWatch gate (D-002) not verified. Sunset 2026-06-01. Per PROMPT_0 §2.1.
- **Gate**: Zero traffic on `deprecated_query_endpoint_used` metric (30 days)

### D-PRELOAD: `api/preload/legacy.py` (613 LOC)
- **Reason**: Active degraded-mode fallback per ADR-011. Per PROMPT_0 §4.2.

### D-GETCF: `Task.get_custom_fields()` (161 consumers)
- **File**: `src/autom8_asana/models/task.py:257-282`
- **Reason**: 6 src files, 161 total references. Migration is a feature-level effort, not
  hygiene cleanup. Would require migrating `descriptors.py` (28 calls), `asset_edit.py` (26 calls),
  `fields.py` (6 calls), `selection.py`, `cascade.py`. Too large for this initiative's scope.
- **Recommendation**: Separate initiative with deprecation->migration->removal phases.

### D-ADAPTER: `cache/integration/autom8_adapter.py` (479 LOC)
- **Reason**: Actively imported by `cache/__init__.py` and `cache/integration/factory.py`.
  `create_autom8_cache_provider()` is called at runtime by factory. Module is migration
  scaffolding whose documentation is stale, but functions provide ongoing runtime value.
- **Recommendation**: Update module docstring to remove migration references, but keep functions.

### D-ENTRY: Cache entry deserialization fallback
- **File**: `src/autom8_asana/cache/models/entry.py:240-246`
- **Reason**: Essential graceful degradation for serialized data without `_type` field.

### D-SCHEMA: Schema fallback patterns (entity-specific → base)
- **Reason**: Intentional resilience for unknown entity types, not backward compat.

### D-SECTION: Section resolution enum fallback
- **Reason**: Functional resilience (manifest-first, enum-fallback), not legacy compat.

---

## Risk Matrix

| Finding | Blast Radius | Reversibility | Test Coverage | Overall Risk |
|---------|-------------|---------------|---------------|--------------|
| RE-01..RE-11 | Import path changes | High (revert) | Existing tests | LOW |
| ST-01..ST-03 | Dead code removal | High | Direct tests | LOW |
| DEP-01 | Protocol contract | Medium | 2 test uses | MEDIUM |
| DEP-02 | Enum contract | Medium | Fallback paths | MEDIUM |
| DEP-03 | Accessor behavior | Low | No explicit use | LOW |
| MIG-01..MIG-03 | Builder module | Low | 1 test use | LOW |
| DP-01 | Config system | High (55 refs) | Extensive | MEDIUM-HIGH |
| DP-02..DP-03 | Cache protocol | High | Backend tests | HIGH |
| DP-04 | Model hierarchy | Medium | Context tests | MEDIUM |
| DP-05 | Entity detection | High | Detection tests | HIGH |
| DP-06 | Attachment cleanup | Low | Workflow tests | LOW |
| HW-01..HW-03 | Config/resolver | Medium | Existing tests | MEDIUM |

---

## Recommended Workstream Grouping (Advisory)

The architect-enforcer makes final grouping decisions. Advisory grouping by module boundary:

| Workstream | Findings | Files Touched | Risk |
|------------|----------|---------------|------|
| WS-REEXPORT | RE-01..RE-11 | ~15 src files + importers | LOW |
| WS-DEAD | ST-01..ST-03, MIG-01..MIG-03 | ~8 files | LOW |
| WS-DEPRECATED | DEP-01..DEP-03 | ~6 files | MEDIUM |
| WS-DUALPATH | DP-01..DP-06 | ~12 files | MEDIUM-HIGH |
| WS-BESPOKE | HW-01..HW-03 | ~4 files | MEDIUM |

**Estimated total**: 29 in-scope findings, ~45 files touched, -530 to -840 net LOC reduction.

---

## Handoff to Architect-Enforcer

This report provides the discovery surface. The architect-enforcer should:

1. Verify each finding's consumer count via exhaustive grep
2. Group into workstreams with strict file-scope contracts
3. Sequence workstreams by dependency (RE-02 before RE-03, ST-01 before RE-11)
4. Determine if DP-02/DP-03 (cache protocol) is feasible or should defer
5. Determine if DP-05 (holder detection fallback) is safe to remove
6. Produce REFACTORING-PLAN.md with before/after contracts per workstream
