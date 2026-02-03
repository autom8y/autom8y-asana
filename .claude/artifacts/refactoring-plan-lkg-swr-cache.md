# Refactoring Plan: LKG & SWR Cache Implementation

**Date**: 2026-02-03
**Agent**: architect-enforcer
**Upstream**: `.claude/artifacts/smell-report-lkg-swr-cache.md`
**Downstream**: Janitor

---

## Architectural Assessment

The LKG cache implementation is **sound in design** but exhibits symptoms of incremental feature addition: the circuit breaker LKG path was bolted onto `get_async()` without decomposing it to share the freshness infrastructure already built for the normal path. This created duplication (SM-001/SM-002) and asymmetric complexity (SM-003).

The FreshnessInfo side-channel (SM-004) is a **pragmatic boundary compromise** that I am deferring from this plan. Replacing it with a structured return type (e.g., `CacheResult[T]`) would change the public API contract of `get_async()`, `_get_dataframe()`, and the query service -- touching 4 files and all downstream consumers. That is a feature change, not a refactoring. The side-channel works correctly today; its fragility is documented; the risk of the refactoring exceeds the smell severity.

### Root Cause Clusters

| Cluster | Smells | Root Cause |
|---------|--------|------------|
| **FreshnessInfo duplication** | SM-001, SM-002 | No shared helper for FreshnessInfo construction |
| **Circuit breaker inline block** | SM-003 | Circuit breaker path added without delegation pattern matching normal path |
| **Type safety gap** | SM-010 | `"circuit_lkg"` not modeled in FreshnessStatus enum |

### Boundary Health

- **Cache module boundary** (`dataframe_cache.py`): Internal organization issue. All three HIGH-severity smells are local to this file. No boundary leaks.
- **Cache-to-service boundary** (`get_freshness_info()` API): Stable. Public method signature unchanged by this plan.
- **Service-to-engine boundary** (SM-004 side-channel): Known fragile. Deferred -- not addressable without API changes.

---

## Smell Disposition

| Smell | Severity | Disposition | Reason |
|-------|----------|-------------|--------|
| SM-001 | HIGH | **Address** (RF-001) | Pure duplication, mechanical fix |
| SM-002 | HIGH | **Address** (RF-001) | Same root cause as SM-001, single fix |
| SM-003 | HIGH | **Address** (RF-002) | Extract method, reduces `get_async()` to ~60 lines |
| SM-004 | HIGH | **Defer** | Requires public API change; not a refactoring |
| SM-005 | MEDIUM | **Defer** | Nesting depth is acceptable given the 5-state freshness model; early-return would obscure the EXPIRED_SERVABLE policy logic |
| SM-006 | MEDIUM | **Address** (RF-003) | Lazy imports can be consolidated within methods that share them |
| SM-007 | MEDIUM | **Defer** | Out of scope (query_service.py, not cache layer) |
| SM-008 | MEDIUM | **Defer** | Coupled to SM-004; same API-change concern |
| SM-009 | MEDIUM | **Defer** | Naming standardization across 4 files is high-churn for low value; defer until SM-004 is addressed |
| SM-010 | MEDIUM | **Address** (RF-004) | Enum gap is a type safety issue local to cache module |
| SM-011 | MEDIUM | **Defer** | Test additions are additive work, not refactoring |
| SM-012 | LOW | **Dismiss** | Module-level function is fine; moving to static method would break test imports for no behavioral gain |
| SM-013 | LOW | **Dismiss** | Rename of internal field has negligible value |

---

## Refactoring Items

### Phase 1: Foundation (Low Risk)

#### RF-004: Add `CIRCUIT_LKG` to `FreshnessStatus` enum

**Rationale**: Must land first because RF-001 will use the enum value instead of the raw string.

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:28-35`: `FreshnessStatus` enum with 5 members
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:46`: `FreshnessInfo.freshness` typed as `str`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:286,313`: Hardcoded `freshness="circuit_lkg"` strings

**After State:**
- `FreshnessStatus` enum gains `CIRCUIT_LKG = "circuit_lkg"` member
- `FreshnessInfo.freshness` type annotation remains `str` (since `FreshnessStatus` is a `str` enum, `.value` produces `str`; changing the field type would affect the downstream Meta models which expect `str | None` -- that is SM-004 territory)
- Lines 286 and 313 use `freshness=FreshnessStatus.CIRCUIT_LKG.value` (will be collapsed in RF-001)

**Invariants:**
- `FreshnessStatus` remains a `str` enum (subclasses `str`)
- `"circuit_lkg"` string value unchanged
- `FreshnessInfo.freshness` field type unchanged (`str`)
- All existing tests pass without modification (the enum addition is additive)

**Verification:**
1. Run: `python -m pytest tests/unit/cache/dataframe/test_dataframe_cache.py -x -q`
2. Confirm all 57 tests pass
3. Confirm `FreshnessStatus.CIRCUIT_LKG.value == "circuit_lkg"`

**Rollback**: Revert single commit.

---

#### RF-001: Extract `_build_freshness_info()` helper method

**Rationale**: Eliminates the 3x-duplicated age/TTL/ratio calculation (SM-001 + SM-002). Must land after RF-004 so the helper can use the enum value.

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:283-291`: FreshnessInfo construction (circuit LKG memory path)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:310-318`: FreshnessInfo construction (circuit LKG S3 path)
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:385-397`: FreshnessInfo construction (normal path in `_check_freshness_and_serve`)

All three perform identical logic:
```python
age = (datetime.now(UTC) - entry.created_at).total_seconds()
entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
FreshnessInfo(
    freshness=<label>,
    data_age_seconds=round(age, 1),
    staleness_ratio=round(age / entity_ttl, 2) if entity_ttl > 0 else 0.0,
)
```

**After State:**
New private method on `DataFrameCache`:
```python
def _build_freshness_info(
    self,
    entry: CacheEntry,
    freshness_label: str,
    cache_key: str,
) -> tuple[FreshnessInfo, float]:
    """Build FreshnessInfo and store in side-channel.

    Returns (freshness_info, age_seconds) for caller logging use.
    """
    from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL

    age = (datetime.now(UTC) - entry.created_at).total_seconds()
    entity_ttl = DEFAULT_ENTITY_TTLS.get(entry.entity_type, DEFAULT_TTL)
    info = FreshnessInfo(
        freshness=freshness_label,
        data_age_seconds=round(age, 1),
        staleness_ratio=round(age / entity_ttl, 2) if entity_ttl > 0 else 0.0,
    )
    self._last_freshness[cache_key] = info
    return info, age
```

All three call sites replaced with:
```python
info, age = self._build_freshness_info(entry, <label>, cache_key)
```

The circuit LKG paths pass `FreshnessStatus.CIRCUIT_LKG.value` as the label. The normal path passes `status.value`.

**Invariants:**
- Same FreshnessInfo values produced for identical inputs
- Same `_last_freshness` dict mutation behavior
- `age` variable still available to callers for logging
- Lazy import of config constants preserved (inside helper)
- Public API unchanged: `get_freshness_info()` returns same values

**Verification:**
1. Run: `python -m pytest tests/unit/cache/dataframe/test_dataframe_cache.py -x -q`
2. Confirm all 57 tests pass
3. Specifically verify: `test_freshness_info_stored_on_fresh_hit`, `test_freshness_info_stored_on_stale_serve`, `test_freshness_info_stored_on_lkg_serve`, `test_freshness_info_stored_on_circuit_lkg`

**Rollback**: Revert single commit.

---

### Phase 2: Structural Cleanup (Medium Risk)

#### RF-002: Extract `_get_circuit_lkg()` from `get_async()`

**Rationale**: Reduces `get_async()` from 128 lines / CC~12 to ~60 lines / CC~6 by extracting the 70-line circuit breaker inline block into a dedicated method. This makes `get_async()` symmetric: both circuit-breaker and normal paths delegate to helpers. Depends on RF-001 (uses `_build_freshness_info`).

**Before State:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py:267-338`: 70-line inline block inside `get_async()` handling circuit breaker LKG fallback across memory and S3 tiers

**After State:**
New private async method on `DataFrameCache`:
```python
async def _get_circuit_lkg(
    self,
    project_gid: str,
    entity_type: str,
    cache_key: str,
) -> CacheEntry | None:
    """Attempt LKG serve when circuit breaker is open.

    Tries memory tier, then progressive tier. Skips freshness checks
    (any schema-valid entry is acceptable). Does not trigger refresh.

    Returns CacheEntry if a valid LKG entry is found, None otherwise.
    """
```

The method encapsulates:
1. Memory tier lookup + schema validation + stats + freshness info + logging
2. Progressive tier lookup + memory hydration + schema validation + stats + freshness info + logging
3. No-LKG warning + return None

`get_async()` circuit breaker block becomes:
```python
if self.circuit_breaker.is_open(project_gid):
    self._stats[entity_type]["circuit_breaks"] += 1
    logger.warning(
        "dataframe_cache_circuit_open",
        extra={"project_gid": project_gid, "entity_type": entity_type},
    )
    return await self._get_circuit_lkg(project_gid, entity_type, cache_key)
```

**Invariants:**
- Same return values for all inputs
- Same stat increments (`circuit_breaks`, `lkg_circuit_serves`, `memory_hits`, `s3_hits`)
- Same logging (event names, extra fields, log levels)
- Same memory tier hydration on S3 hit
- `get_async()` return type unchanged: `CacheEntry | None`
- No change to normal (non-circuit-breaker) path

**Verification:**
1. Run: `python -m pytest tests/unit/cache/dataframe/test_dataframe_cache.py -x -q`
2. Confirm all 57 tests pass
3. Specifically verify circuit breaker tests: `test_circuit_open_serves_valid_memory_entry`, `test_circuit_open_serves_valid_s3_entry`, `test_circuit_open_rejects_schema_mismatch`, `test_circuit_open_no_data_returns_none`, `test_circuit_open_no_refresh_triggered`, `test_circuit_open_tracks_lkg_circuit_serves_stat`

**Rollback**: Revert single commit. No other refactoring depends on this.

---

#### RF-003: Consolidate lazy config imports in `_check_freshness_and_serve()`

**Rationale**: Two separate `from autom8_asana.config import ...` statements in the same method (lines 383 and 430) can be merged into one at the top of the method. The `_build_freshness_info` helper (from RF-001) absorbs the first import, so this task only needs to hoist `LKG_MAX_STALENESS_MULTIPLIER` to the remaining import. Depends on RF-001.

**Before State:**
- Line 383: `from autom8_asana.config import DEFAULT_ENTITY_TTLS, DEFAULT_TTL` (inside `_check_freshness_and_serve`)
- Line 430: `from autom8_asana.config import LKG_MAX_STALENESS_MULTIPLIER` (nested inside `if status == EXPIRED_SERVABLE`)

After RF-001 lands, line 383 is removed (moved into `_build_freshness_info`). Line 430 remains.

**After State:**
- The `LKG_MAX_STALENESS_MULTIPLIER` import moves to the top of `_check_freshness_and_serve()`, alongside any remaining config import needed for the `entity_ttl` variable used in the max staleness calculation.
- `_check_freshness_and_serve` has at most one lazy import statement.

**Invariants:**
- Same import resolution (lazy, not top-level -- circular import concern preserved)
- Same behavior in all freshness branches

**Verification:**
1. Run: `python -m pytest tests/unit/cache/dataframe/test_dataframe_cache.py -x -q`
2. Confirm all 57 tests pass

**Rollback**: Revert single commit.

---

## Sequencing & Dependencies

```
RF-004 (enum) ──> RF-001 (helper) ──> RF-002 (extract method)
                                  ──> RF-003 (consolidate imports)
```

| Order | Task | Depends On | Risk | Blast Radius |
|-------|------|------------|------|--------------|
| 1 | RF-004 | None | Low | 1 file, additive enum member |
| 2 | RF-001 | RF-004 | Low | 1 file, 3 call sites |
| 3 | RF-002 | RF-001 | Medium | 1 file, core retrieval path |
| 4 | RF-003 | RF-001 | Low | 1 file, 1 method |

RF-002 and RF-003 are independent of each other and can be done in either order after RF-001.

### Rollback Points

- **After RF-004**: Enum addition is fully backward-compatible. Safe checkpoint.
- **After RF-001**: FreshnessInfo construction is centralized. If RF-002 or RF-003 cause issues, revert only those commits.
- **After RF-002**: Circuit breaker extraction is self-contained. Revert does not affect RF-001 or RF-003.
- **After RF-003**: Import consolidation is trivial. Revert is single commit.

---

## Risk Matrix

| Task | What Could Break | Detection | Recovery |
|------|-----------------|-----------|----------|
| RF-004 | Nothing (additive) | Tests pass | Revert 1 commit |
| RF-001 | FreshnessInfo values differ (rounding, age calc) | `test_freshness_info_stored_on_*` tests (4 tests) | Revert 1 commit |
| RF-002 | Circuit breaker LKG behavior changes (stats, return values, logging) | 6 circuit breaker tests | Revert 1 commit |
| RF-003 | Import timing changes cause circular import | Any test import failure | Revert 1 commit |

---

## What Is NOT In Scope

These items are explicitly excluded from this plan:

1. **SM-004 (side-channel refactoring)**: Would require changing `get_async()` return type to carry freshness alongside data. This is a feature change affecting 4 files and all consumers. Should be a separate initiative with its own PRD.

2. **SM-007 (query_service DRY)**: Different module, different concern. Not part of cache layer cleanup.

3. **SM-008 (kwargs type erasure in engine.py)**: Coupled to SM-004. Fix properly when the side-channel is replaced with structured types.

4. **SM-009 (naming consistency)**: 4-file rename for field names. Do this when SM-004 is addressed.

5. **SM-011 (test gaps)**: Adding tests is additive work. Can be done independently, outside this refactoring plan.

6. **SM-012, SM-013**: Dismissed. Negligible value.

---

## Janitor Notes

### Commit Conventions
- One commit per RF-* task
- Commit message format: `refactor(cache): <description>`
- Example: `refactor(cache): add CIRCUIT_LKG to FreshnessStatus enum`

### Test Requirements
- Run full cache test suite after each commit: `python -m pytest tests/unit/cache/dataframe/test_dataframe_cache.py -x -q`
- All 57 tests must pass at each commit boundary
- No new tests required (this is structure-only refactoring)

### Critical Ordering
- RF-004 MUST land before RF-001 (RF-001 references the new enum member)
- RF-001 MUST land before RF-002 and RF-003 (both depend on the extracted helper)
- RF-002 and RF-003 are independent of each other

### Implementation Details

**RF-004**: Add enum member after `WATERMARK_STALE`. Replace the two `freshness="circuit_lkg"` string literals with `freshness=FreshnessStatus.CIRCUIT_LKG.value`.

**RF-001**: Place `_build_freshness_info` method after `get_freshness_info` (around line 676). The method handles its own lazy import. Callers destructure the returned tuple: `info, age = self._build_freshness_info(...)`. The `age` value is needed by callers for logging `age_seconds` in their `extra` dicts. In `_check_freshness_and_serve`, also use `age` for the max staleness comparison (line 434) -- ensure this variable remains available after the refactoring.

**RF-002**: The extracted `_get_circuit_lkg` method should be placed immediately after `get_async`. It is `async` because it calls `self.progressive_tier.get_async()`. The `_ensure_stats` call and circuit break stat increment stay in `get_async` (they are pre-delegation bookkeeping).

**RF-003**: After RF-001 absorbs the `DEFAULT_ENTITY_TTLS`/`DEFAULT_TTL` import from `_check_freshness_and_serve`, the only remaining lazy import in that method is `LKG_MAX_STALENESS_MULTIPLIER`. However, `_check_freshness_and_serve` still needs `entity_ttl` for the max staleness calculation (`max_age = LKG_MAX_STALENESS_MULTIPLIER * entity_ttl`). The `_build_freshness_info` helper does not return `entity_ttl`. Two options: (a) have `_build_freshness_info` also return `entity_ttl`, or (b) keep a single consolidated import at the top of `_check_freshness_and_serve` for both `DEFAULT_ENTITY_TTLS, DEFAULT_TTL, LKG_MAX_STALENESS_MULTIPLIER`. Option (b) is simpler and preferred.

---

## Verification Attestation

| File | Read | Lines Analyzed |
|------|------|----------------|
| `.claude/artifacts/smell-report-lkg-swr-cache.md` | Yes | 1-440 (all) |
| `src/autom8_asana/cache/dataframe_cache.py` | Yes | 1-100, 185-199, 230-480, 650-770 |
| `src/autom8_asana/services/universal_strategy.py` | Yes | 1-100, 400-430 |
| `src/autom8_asana/services/query_service.py` | Yes | 100-140, 390-407 |
| `src/autom8_asana/query/engine.py` | Yes | 1-50, 245-295, 395-430 |
| `src/autom8_asana/query/models.py` | Yes | 160-249 |

---

## Handoff Checklist

- [x] Every HIGH smell classified (3 addressed, 1 deferred with reason)
- [x] Every MEDIUM/LOW smell dispositioned
- [x] Each refactoring has before/after contract documented
- [x] Invariants and verification criteria specified
- [x] Refactorings sequenced with explicit dependencies
- [x] Rollback points identified between phases
- [x] Risk assessment complete for each task
- [x] Artifacts verified via Read tool with attestation table
