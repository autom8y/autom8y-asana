# Smell Report: LKG & SWR Cache Implementation

**Scope**: 7 files covering DataFrameCache LKG/SWR freshness pattern
**Date**: 2026-02-03
**Agent**: code-smeller

---

## Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| DRY Violation | 0 | 2 | 1 | 0 | 3 |
| Complexity | 0 | 1 | 1 | 0 | 2 |
| Coupling | 0 | 1 | 1 | 0 | 2 |
| Import Hygiene | 0 | 0 | 1 | 0 | 1 |
| Naming | 0 | 0 | 1 | 1 | 2 |
| Dead Code | 0 | 0 | 0 | 1 | 1 |
| Test Smell | 0 | 0 | 1 | 0 | 1 |
| **Total** | **0** | **4** | **6** | **2** | **12** |

---

## Findings (ROI-ranked)

---

### SM-001: Duplicated FreshnessInfo construction in circuit breaker LKG path (HIGH)

**Category**: DRY Violation
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:279-301` (memory circuit LKG)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:305-329` (S3 circuit LKG)

**Evidence**: Lines 279-301 and 305-329 are near-identical blocks. Both perform:
1. `entry = <tier>.get(cache_key)` / `await <tier>.get_async(cache_key)`
2. `self._schema_is_valid(entry)` check
3. Stat increment: `lkg_circuit_serves` + tier hit counter
4. Age calculation: `(datetime.now(UTC) - entry.created_at).total_seconds()`
5. TTL lookup: `DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)`
6. FreshnessInfo construction with `freshness="circuit_lkg"`
7. Logging with identical structure (only `tier` value differs)

```python
# Lines 283-291 (memory path)
age = (datetime.now(UTC) - entry.created_at).total_seconds()
cb_entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
self._last_freshness[cache_key] = FreshnessInfo(
    freshness="circuit_lkg",
    data_age_seconds=round(age, 1),
    staleness_ratio=round(age / cb_entity_ttl, 2)
    if cb_entity_ttl > 0
    else 0.0,
)

# Lines 310-318 (S3 path) -- identical logic
age = (datetime.now(UTC) - entry.created_at).total_seconds()
cb_entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
self._last_freshness[cache_key] = FreshnessInfo(
    freshness="circuit_lkg",
    data_age_seconds=round(age, 1),
    staleness_ratio=round(age / cb_entity_ttl, 2)
    if cb_entity_ttl > 0
    else 0.0,
)
```

**Blast Radius**: 1 file, ~50 duplicated lines
**Fix Complexity**: Low -- extract helper method `_serve_circuit_lkg(entry, cache_key, tier)`
**ROI Score**: 9.0/10

**Note**: The circuit breaker LKG path duplicates FreshnessInfo construction that `_check_freshness_and_serve()` already handles for the normal path. Suggests the circuit breaker LKG block should be refactored to share the FreshnessInfo construction with the normal path. Flag for Architect Enforcer -- may want a unified `_build_freshness_info()` helper.

---

### SM-002: FreshnessInfo construction also duplicated between circuit LKG and normal path (HIGH)

**Category**: DRY Violation
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:283-291` (circuit LKG memory)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:310-318` (circuit LKG S3)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:385-397` (`_check_freshness_and_serve`)

**Evidence**: The age/entity_ttl/staleness_ratio calculation pattern appears 3 times with slight variations:

Circuit path uses `cb_entity_ttl` and hardcoded `"circuit_lkg"` string:
```python
cb_entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
FreshnessInfo(freshness="circuit_lkg", data_age_seconds=round(age, 1),
              staleness_ratio=round(age / cb_entity_ttl, 2) if cb_entity_ttl > 0 else 0.0)
```

Normal path uses `entity_ttl` and `status.value`:
```python
entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
FreshnessInfo(freshness=status.value, data_age_seconds=round(age, 1),
              staleness_ratio=round(age / entity_ttl, 2) if entity_ttl > 0 else 0.0)
```

The only meaningful difference is the `freshness` string value. The calculation is identical.

**Blast Radius**: 1 file, 3 locations
**Fix Complexity**: Low -- extract `_build_freshness_info(entry, freshness_label) -> FreshnessInfo`
**ROI Score**: 8.5/10

---

### SM-003: `get_async()` high cyclomatic complexity (HIGH)

**Category**: Complexity
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:236-364`

**Evidence**: `get_async()` spans 128 lines (236-364) with the following branching structure:

1. Circuit breaker check (line 267) -- enters a 70-line block
   - Memory tier get (line 279)
     - Schema valid check (line 280)
       - Stats, age calc, FreshnessInfo, logging, return (lines 281-302)
   - S3 tier get (line 305)
     - Schema valid check (line 306)
       - Memory hydration, stats, FreshnessInfo, logging, return (lines 307-329)
   - No LKG fallback, return None (lines 331-338)
2. Normal path -- memory tier (line 341)
   - `_check_freshness_and_serve()` delegation (line 343)
   - Result check (line 346)
3. S3 tier fallback (line 352)
   - `_check_freshness_and_serve()` delegation (line 354)
   - Memory hydration on hit (lines 358-360)

Estimated cyclomatic complexity: **11-13** (conditional branches + early returns).

The circuit breaker block (lines 267-338) is a self-contained 70-line inline block that could be extracted. The normal path (lines 340-364) is clean thanks to `_check_freshness_and_serve()` delegation, but the circuit breaker path has no equivalent decomposition.

**Blast Radius**: 1 file, core cache retrieval path
**Fix Complexity**: Medium -- extract `_get_circuit_lkg(project_gid, entity_type, cache_key) -> CacheEntry | None`
**ROI Score**: 8.0/10

**Note**: Flag for Architect Enforcer -- the asymmetry between the circuit-breaker path (inline) and normal path (delegated to helper) suggests an incomplete refactor.

---

### SM-004: FreshnessInfo side-channel propagated via `getattr` with defensive fallback (HIGH)

**Category**: Coupling (fragile side-channel threading)
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py:414-416` (getattr with lambda fallback)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py:405` (getattr with None default)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:259` (getattr with None default)

**Evidence**: FreshnessInfo propagates through 4 layers via mutable instance state and `getattr` defensive access:

Layer 1 -- DataFrameCache stores to `_last_freshness` dict (line 285, 312, 393):
```python
self._last_freshness[cache_key] = FreshnessInfo(...)
```

Layer 2 -- UniversalResolutionStrategy reads via `getattr` with lambda fallback (line 414-416):
```python
self._last_freshness_info = getattr(
    cache, "get_freshness_info", lambda *a: None
)(project_gid, self.entity_type)
```
This lambda fallback suggests the code is unsure if the cache object will have this method.

Layer 3 -- EntityQueryService reads from strategy (line 405):
```python
self._last_freshness_info = getattr(strategy, "_last_freshness_info", None)
```

Layer 4 -- QueryEngine reads from query_service (line 259):
```python
freshness_info = getattr(self.query_service, "_last_freshness_info", None)
```

Problems:
1. **No type safety**: All access is via `getattr` with None defaults, meaning any breakage is silent.
2. **Temporal coupling**: Info is only valid immediately after the prior call -- if another call intervenes (e.g., in `execute_rows` which calls `get_dataframe` twice for joins at lines 120-124 and 193-197), the second call overwrites the first's freshness info.
3. **Lambda fallback on known API** (line 414-416): `get_freshness_info` is a documented public method on DataFrameCache -- the lambda fallback is unnecessary defensive code.

**Blast Radius**: 4 files, entire freshness propagation chain
**Fix Complexity**: Medium -- introduce a typed return value or context object from `get_dataframe` that carries freshness info alongside the DataFrame, rather than mutable side-channels.
**ROI Score**: 7.5/10

**Note**: Flag for Architect Enforcer -- this is a boundary concern. The cache layer's internal freshness metadata is threaded through 3 service layers via fragile side-channels. A structured return type (e.g., `CacheResult[T]` carrying both data and metadata) would be more robust.

---

### SM-005: `_check_freshness_and_serve()` multi-branch complexity (MEDIUM)

**Category**: Complexity
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:366-468`

**Evidence**: The method handles 5 status branches with nested logic for the EXPIRED_SERVABLE branch (lines 428-463):

```python
if status == FreshnessStatus.FRESH:          # line 399 -- return entry
if status == FreshnessStatus.STALE_SERVABLE: # line 412 -- SWR + return
if status == FreshnessStatus.EXPIRED_SERVABLE: # line 428
    if LKG_MAX_STALENESS_MULTIPLIER > 0:       # line 432
        max_age = LKG_MAX_STALENESS_MULTIPLIER * entity_ttl  # line 433
        if age > max_age:                       # line 434
            if tier == "memory":               # line 445
            return None
    # else: serve as LKG
# implicit else: SCHEMA_MISMATCH or WATERMARK_STALE
```

The EXPIRED_SERVABLE branch has 3 levels of nesting. While the method is well-documented, the nesting depth (4 levels including the method body) makes it harder to trace the control flow.

**Blast Radius**: 1 file, 1 method
**Fix Complexity**: Low -- early-return for max staleness check, or extract `_enforce_max_staleness()` guard
**ROI Score**: 6.5/10

---

### SM-006: Repeated lazy import of config constants inside methods (MEDIUM)

**Category**: Import Hygiene
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:277` (`get_async` circuit path)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:383` (`_check_freshness_and_serve`)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:430` (`_check_freshness_and_serve` again)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:754` (`_check_freshness`)

**Evidence**: Four separate `from autom8_asana.config import ...` statements inside methods:

```python
# Line 277 (circuit path)
from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL

# Line 383 (_check_freshness_and_serve)
from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL

# Line 430 (_check_freshness_and_serve, nested in EXPIRED_SERVABLE branch)
from autom8_asana.config import LKG_MAX_STALENESS_MULTIPLIER

# Line 754 (_check_freshness)
from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL, SWR_GRACE_MULTIPLIER
```

These are all module-level constants (not classes with heavy init), so the circular import concern may be resolvable by restructuring the import graph. Even if lazy imports are needed, consolidating to a single method-level import location would reduce duplication.

**Blast Radius**: 1 file, 4 locations
**Fix Complexity**: Low (consolidate) to Medium (restructure imports to allow top-level)
**ROI Score**: 6.0/10

---

### SM-007: `query()` and `query_with_expr()` near-identical structure (MEDIUM)

**Category**: DRY Violation
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py:126-227` (`query`)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py:292-372` (`query_with_expr`)

**Evidence**: Both methods follow the identical pattern:
1. Assert strategy_factory not None
2. Create strategy from factory
3. Call `strategy._get_dataframe(project_gid, client)`
4. Raise `CacheNotWarmError` if None
5. Apply filter (dict-based vs expr-based -- the only difference)
6. Get total_count
7. Apply pagination
8. Apply select
9. Convert to dicts
10. Log and return QueryResult

The only meaningful difference is step 5: `_apply_filters(df, where)` vs `df.filter(expr)`.

**Blast Radius**: 1 file, ~80 duplicated lines
**Fix Complexity**: Low -- extract shared DataFrame acquisition + pagination into private helper
**ROI Score**: 5.5/10

---

### SM-008: Freshness metadata propagated via `**kwargs` dict unpacking (MEDIUM)

**Category**: Coupling (type erasure)
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:260-266` (rows path)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:409-416` (aggregate path)

**Evidence**: Freshness metadata is unpacked into response Meta models via `**freshness_meta` with `type: ignore` comments:

```python
# Line 260-266
freshness_info = getattr(self.query_service, "_last_freshness_info", None)
freshness_meta: dict[str, object] = {}
if freshness_info is not None:
    freshness_meta = {
        "freshness": freshness_info.freshness,
        "data_age_seconds": freshness_info.data_age_seconds,
        "staleness_ratio": freshness_info.staleness_ratio,
    }
```

Then used as:
```python
**freshness_meta,  # type: ignore[arg-type]
```

This pattern:
1. Erases type information (dict[str, object] -> kwargs)
2. Requires `type: ignore` suppression (line 279, 427)
3. Is duplicated identically for both `execute_rows` and `execute_aggregate`
4. Manually extracts fields that are already on a typed dataclass (`FreshnessInfo`)

**Blast Radius**: 1 file, 2 locations; also affects type checking coverage
**Fix Complexity**: Low -- pass FreshnessInfo directly to Meta model constructors with typed fields
**ROI Score**: 5.5/10

---

### SM-009: Naming inconsistency in freshness info field naming across layers (MEDIUM)

**Category**: Naming
**Locations**:
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:197` -- `_last_freshness: dict[str, FreshnessInfo]`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:664` -- `get_freshness_info()`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py:85` -- `_last_freshness_info: Any`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py:117` -- `_last_freshness_info: Any`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py:259` -- `_last_freshness_info` via getattr
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py:178,238` -- `freshness`, `data_age_seconds`, `staleness_ratio` (flat fields on Meta models)

**Evidence**: The naming drifts across layers:

| Layer | Field Name | Type |
|-------|-----------|------|
| DataFrameCache | `_last_freshness` | `dict[str, FreshnessInfo]` |
| DataFrameCache | `get_freshness_info()` | returns `FreshnessInfo \| None` |
| UniversalResolutionStrategy | `_last_freshness_info` | `Any` |
| EntityQueryService | `_last_freshness_info` | `Any` |
| QueryEngine | `_last_freshness_info` | accessed via getattr |
| RowsMeta/AggregateMeta | `freshness`, `data_age_seconds`, `staleness_ratio` | flat `str \| None`, `float \| None` |

Two specific issues:
1. `_last_freshness` (cache) vs `_last_freshness_info` (service/strategy) -- inconsistent suffix
2. The field is typed as `Any` in both UniversalResolutionStrategy (line 85) and EntityQueryService (line 117), losing all type information despite `FreshnessInfo` being a well-defined dataclass

**Blast Radius**: 4 files
**Fix Complexity**: Low -- standardize naming and use `FreshnessInfo | None` type annotation
**ROI Score**: 5.0/10

---

### SM-010: FreshnessInfo.freshness field uses `str` instead of `FreshnessStatus` enum (MEDIUM)

**Category**: Naming / Type Safety
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:46`

**Evidence**:
```python
@dataclass
class FreshnessInfo:
    freshness: str  # "fresh" | "stale_servable" | "expired_servable" | "circuit_lkg"
```

`FreshnessStatus` is defined at line 28 as an enum with values `FRESH`, `STALE_SERVABLE`, `EXPIRED_SERVABLE`, `SCHEMA_MISMATCH`, `WATERMARK_STALE`. The `FreshnessInfo.freshness` field uses raw strings, including `"circuit_lkg"` which is NOT a member of `FreshnessStatus` at all.

In `_check_freshness_and_serve` (line 394), the enum value is converted: `freshness=status.value`. But in the circuit breaker path (lines 286, 313), a raw string `"circuit_lkg"` is used directly.

This means the freshness field in FreshnessInfo has 4 valid values (3 from FreshnessStatus.value + 1 ad-hoc string), making it impossible to validate without knowing all call sites.

**Blast Radius**: 4 files (propagates through entire chain)
**Fix Complexity**: Low -- add `CIRCUIT_LKG = "circuit_lkg"` to `FreshnessStatus` enum, type `FreshnessInfo.freshness` as `FreshnessStatus`
**ROI Score**: 5.0/10

---

### SM-011: Test helper duplication and missing freshness propagation tests (MEDIUM)

**Category**: Test Smell
**Location**: `/Users/tomtenuta/Code/autom8_asana/tests/unit/cache/dataframe/test_dataframe_cache.py`

**Evidence**:

1. **Missing integration test for `_last_freshness_info` overwrite on join path**: `execute_rows` in engine.py calls `get_dataframe` twice when a join is present (lines 120-124 and 193-197). The second call overwrites `_last_freshness_info` on the query_service. No test covers whether the freshness info returned in the response corresponds to the primary entity or the join target. This is a gap in the SM-004 side-channel concern.

2. **No test for `LKG_MAX_STALENESS_MULTIPLIER` on S3 tier**: All max staleness tests use memory tier entries. The S3 path in `_check_freshness_and_serve` (line 445-447) has a conditional `if tier == "memory": self.memory_tier.remove(cache_key)` -- this means the S3 path does NOT evict. No test verifies this asymmetry.

3. **No negative test for `FreshnessInfo` on watermark-stale reject**: There is `test_freshness_info_not_stored_on_schema_reject` but no equivalent for `WATERMARK_STALE` status.

**Blast Radius**: Test coverage gap
**Fix Complexity**: Low -- add 3 targeted test cases
**ROI Score**: 4.5/10

---

### SM-012: `_get_schema_version_for_entity` module-level function could be static method (LOW)

**Category**: Dead Code / Organization
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:51-78`

**Evidence**: `_get_schema_version_for_entity` is a module-level function that is only called from within `DataFrameCache` methods (`_schema_is_valid` at line 697, `_check_freshness` at line 726) and `put_async` (line 492). It is also imported in tests (line 22 of test file). While not strictly dead code, it pollutes the module namespace and its leading underscore suggests it should be private to the class.

**Blast Radius**: 1 file + test file
**Fix Complexity**: Low
**ROI Score**: 2.5/10

---

### SM-013: `invalidate_on_schema_change` uses instance `schema_version` fallback (LOW)

**Category**: Naming
**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:194`

**Evidence**: `DataFrameCache.schema_version` (line 194) is an instance attribute defaulting to `"1.0.0"` that serves as a fallback in `put_async` (line 495) when registry lookup fails. However, `_check_freshness` (line 726) and `_schema_is_valid` (line 697) both use the registry directly and do NOT reference `self.schema_version`. This means the instance `schema_version` is only relevant for:
1. `put_async` fallback (line 495)
2. `invalidate_on_schema_change` comparison (line 573)

The field name `schema_version` suggests it is the authoritative schema version, but it is actually just a write-path fallback. This is misleading.

**Blast Radius**: 1 file, low risk
**Fix Complexity**: Low -- rename to `_fallback_schema_version`
**ROI Score**: 2.0/10

---

## Boundary Concerns for Architect Enforcer

1. **SM-004**: The FreshnessInfo side-channel threading pattern (cache -> strategy -> service -> engine) is fragile and untyped. The cache layer's internal metadata leaks through 3 service boundaries via mutable state and `getattr`. An explicit return type or context object at the `get_dataframe` boundary would be more robust.

2. **SM-001 + SM-003**: The circuit breaker LKG path in `get_async()` is a 70-line inline block that duplicates logic already present in `_check_freshness_and_serve()`. This asymmetry suggests the circuit breaker path was added later without refactoring to share the existing freshness infrastructure. The Architect Enforcer should evaluate whether the circuit breaker LKG path should delegate to the same helper.

3. **SM-010**: The `"circuit_lkg"` freshness status is an ad-hoc string not represented in the `FreshnessStatus` enum, creating an implicit contract that all consumers must know about. This is a modeling gap at the cache layer boundary.

---

## Verification Attestation

| File | Read | Lines Analyzed |
|------|------|----------------|
| `src/autom8_asana/cache/dataframe_cache.py` | Yes | 1-865 (all) |
| `src/autom8_asana/services/universal_strategy.py` | Yes | 1-630 (all) |
| `src/autom8_asana/services/query_service.py` | Yes | 1-407 (all) |
| `src/autom8_asana/query/engine.py` | Yes | 1-430 (all) |
| `src/autom8_asana/query/models.py` | Yes | 1-249 (all) |
| `src/autom8_asana/config.py` | Yes | 1-627 (all) |
| `tests/unit/cache/dataframe/test_dataframe_cache.py` | Yes | 1-1125 (all) |
