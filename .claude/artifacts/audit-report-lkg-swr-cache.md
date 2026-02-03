# Audit Report: LKG & SWR Cache Refactoring

**Date**: 2026-02-03
**Agent**: audit-lead
**Upstream**: `.claude/artifacts/refactoring-plan-lkg-swr-cache.md`
**Source file**: `src/autom8_asana/cache/dataframe_cache.py`

---

## Verdict: REVISION REQUIRED

One blocking issue must be resolved before merge: mypy --strict reports 3 type errors introduced by the refactoring. All other criteria pass.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Commits audited | 4 |
| Cache tests | 57/57 passed |
| Full suite | 7938 passed, 219 skipped, 1 xfailed |
| Ruff lint | All checks passed |
| mypy --strict | **3 errors (BLOCKING)** |
| Smells addressed | 4 of 4 targeted (SM-001, SM-002, SM-003, SM-010) |
| Lines changed | +113 / -80 (net +33) |

---

## 1. Test Results

### Cache Test Suite (57 tests)

All 57 tests in `tests/unit/cache/dataframe/test_dataframe_cache.py` pass, including the 6 circuit breaker LKG tests and 6 freshness info side-channel tests that specifically exercise the refactored code paths. Runtime: 0.76s.

Runtime warnings about unawaited `_swr_refresh_async` coroutines are pre-existing (from mocked `asyncio.create_task`) and not introduced by this refactoring.

### Full Suite (7938 tests)

No regressions detected. Pass/skip/xfail counts are consistent with pre-refactoring baseline.

### Lint (ruff)

All checks passed. No new violations.

### Type Check (mypy --strict) -- BLOCKING

```
src/autom8_asana/cache/dataframe_cache.py:425: error: Item "None" of "FreshnessInfo | None" has no attribute "data_age_seconds"  [union-attr]
src/autom8_asana/cache/dataframe_cache.py:435: error: Item "None" of "FreshnessInfo | None" has no attribute "data_age_seconds"  [union-attr]
src/autom8_asana/cache/dataframe_cache.py:447: error: Item "None" of "FreshnessInfo | None" has no attribute "staleness_ratio"  [union-attr]
```

**Root cause**: In `_check_freshness_and_serve()`, the variable `info` is assigned as `FreshnessInfo | None` (lines 394-401). The subsequent branches for `STALE_SERVABLE` (line 425) and `EXPIRED_SERVABLE` (lines 435, 447) access `info.data_age_seconds` and `info.staleness_ratio` without narrowing the type. Mypy cannot infer that `info` is non-None in these branches because the type narrowing happens via a separate `status` variable, not via direct None-checking of `info`.

**Pre-refactoring state**: Before RF-001, the age and staleness values were computed inline from local variables, so this mypy issue did not exist. The refactoring introduced a new type-narrowing requirement that was not satisfied.

**Fix**: Either (a) add an `assert info is not None` before the accesses in the `STALE_SERVABLE` and `EXPIRED_SERVABLE` branches, or (b) restructure so that `info` is built inside each branch that uses it (preserving the helper call). Option (a) is simplest and adds no behavioral change.

---

## 2. Contract Verification

### RF-004: Add CIRCUIT_LKG to FreshnessStatus enum

| Contract | Status |
|----------|--------|
| `FreshnessStatus` gains `CIRCUIT_LKG = "circuit_lkg"` | VERIFIED (line 36) |
| `FreshnessStatus` remains a `str` enum | VERIFIED (line 28: `class FreshnessStatus(str, Enum)`) |
| `"circuit_lkg"` string value unchanged | VERIFIED (`CIRCUIT_LKG.value == "circuit_lkg"`) |
| `FreshnessInfo.freshness` field type unchanged (`str`) | VERIFIED (line 47) |
| Existing tests pass without modification | VERIFIED (57/57) |

**Verdict**: PASS

### RF-001: Extract `_build_freshness_info()` helper

| Contract | Status |
|----------|--------|
| Same FreshnessInfo values for identical inputs | VERIFIED -- computation identical: age, entity_ttl lookup, rounding |
| Same `_last_freshness` dict mutation | VERIFIED (line 707: `self._last_freshness[cache_key] = info`) |
| Lazy import preserved | VERIFIED (line 698: import inside method body) |
| Public API `get_freshness_info()` unchanged | VERIFIED (lines 669-680) |

**Deviation from plan**: The plan specified `_build_freshness_info` would take `freshness_label: str` and return `tuple[FreshnessInfo, float]`. The implementation takes `status: FreshnessStatus` and returns `FreshnessInfo` (no age in return). This is a reasonable improvement -- passing the enum is more type-safe, and callers that need `age` extract it from `info.data_age_seconds`. The deviation does not affect behavior preservation.

**Verdict**: PASS (with note on mypy issue -- see Section 1)

### RF-002: Extract `_get_circuit_lkg()` from `get_async()`

| Contract | Status |
|----------|--------|
| Same return values for all inputs | VERIFIED -- memory then S3 lookup, schema check, return entry or None |
| Same stat increments | VERIFIED -- `circuit_breaks` in `get_async()`, `lkg_circuit_serves` + tier hits in `_get_circuit_lkg()` |
| Same logging (events, extra fields, levels) | VERIFIED -- event names and extra dicts match |
| Memory tier hydration on S3 hit | VERIFIED (line 345: `self.memory_tier.put(cache_key, entry)`) |
| `get_async()` return type unchanged | VERIFIED -- still `CacheEntry | None` |
| No change to normal path | VERIFIED -- lines 279-303 untouched in logic |

**Verdict**: PASS

### RF-003: Consolidate lazy config imports

| Contract | Status |
|----------|--------|
| Single import statement at top of method | VERIFIED (lines 385-389) |
| Same import resolution (lazy, not top-level) | VERIFIED |
| Same behavior in all freshness branches | VERIFIED |

**Verdict**: PASS

---

## 3. Smell Remediation

| Smell | Severity | Target | Status | Evidence |
|-------|----------|--------|--------|----------|
| SM-001 | HIGH | RF-001 | RESOLVED | FreshnessInfo construction in circuit LKG paths now delegates to `_build_freshness_info()` (lines 329, 348) |
| SM-002 | HIGH | RF-001 | RESOLVED | All 3 FreshnessInfo construction sites (2x circuit LKG, 1x normal) replaced by single helper |
| SM-003 | HIGH | RF-002 | RESOLVED | `get_async()` reduced from ~128 lines to ~40 lines; circuit breaker path in dedicated method |
| SM-010 | MEDIUM | RF-004 | RESOLVED | `CIRCUIT_LKG = "circuit_lkg"` added to enum (line 36); helper uses `status.value` |
| SM-004 | HIGH | Deferred | N/A | Out of scope per plan |
| SM-005 | MEDIUM | Deferred | N/A | Out of scope per plan |
| SM-006 | MEDIUM | RF-003 | PARTIALLY RESOLVED | `_check_freshness_and_serve` consolidated; `_build_freshness_info` has its own import; `_check_freshness` retains a separate import. Net reduction from 4 import sites to 3. |
| SM-007-013 | Various | Deferred/Dismissed | N/A | Per plan |

---

## 4. Commit Quality

| Commit | SHA | Files | Atomic | Reversible | Message Quality |
|--------|-----|-------|--------|------------|-----------------|
| RF-004 | `5c889bb` | 1 | Yes | Yes | Clear, references smell |
| RF-001 | `7db09ed` | 1 | Yes | Yes | Clear, explains what and why |
| RF-002 | `44f5cd2` | 1 | Yes | Yes | Clear, references complexity reduction |
| RF-003 | `1e535b5` | 1 | Yes | Yes | Clear, references dependency chain |

All commits follow the `refactor(cache):` convention specified in the plan. All include `Co-Authored-By` attribution. Sequencing matches the plan dependency graph: RF-004 -> RF-001 -> RF-002/RF-003.

**Verdict**: Excellent commit hygiene.

---

## 5. Behavior Preservation

| Aspect | Preserved | Evidence |
|--------|-----------|----------|
| Public API signatures | Yes | No method signatures changed on public methods |
| Return types | Yes | `get_async()`, `put_async()`, `get_freshness_info()` unchanged |
| Error semantics | Yes | Same exception handling, same circuit breaker behavior |
| Stat counter increments | Yes | All stat paths verified in `_get_circuit_lkg` and `_check_freshness_and_serve` |
| FreshnessInfo side-channel storage | Yes | `_last_freshness` dict populated identically |
| Circuit breaker LKG invariant | Yes | No refresh triggered, no staleness cap in circuit path |
| Memory hydration on S3 hit | Yes | Both normal path (line 299) and circuit LKG path (line 345) |

---

## 6. Blocking Issues

### BLOCK-001: mypy --strict type errors (3 errors)

**Severity**: Blocking
**Location**: `src/autom8_asana/cache/dataframe_cache.py` lines 425, 435, 447
**Description**: `info` variable typed as `FreshnessInfo | None` is accessed without narrowing in the `STALE_SERVABLE` and `EXPIRED_SERVABLE` branches.
**Required Fix**: Add `assert info is not None` before first access in each branch, or restructure the conditional assignment.
**Route to**: Janitor -- single commit fix, then re-run mypy to confirm.

---

## 7. Advisory Notes (Non-Blocking)

1. **SM-006 partially resolved**: The plan targeted consolidation of lazy config imports. Two of 4 original import sites were eliminated (one absorbed into `_build_freshness_info`, one consolidated in `_check_freshness_and_serve`). The remaining two (in `_build_freshness_info` and `_check_freshness`) are in separate methods and cannot be further consolidated without restructuring the import graph. This is acceptable.

2. **Plan deviation on `_build_freshness_info` signature**: The implementation uses `FreshnessStatus` enum parameter instead of `str`, and returns `FreshnessInfo` instead of `tuple[FreshnessInfo, float]`. This is an improvement over the plan -- more type-safe, simpler API. Callers access `info.data_age_seconds` directly instead of destructuring a tuple.

---

## 8. Improvement Assessment

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| `get_async()` line count | ~128 | ~40 | 69% reduction |
| FreshnessInfo construction sites | 3 | 1 | 67% reduction (DRY) |
| Hardcoded `"circuit_lkg"` strings | 2 | 0 | Eliminated |
| FreshnessStatus enum completeness | 5/6 values | 6/6 values | Complete |
| Lazy config import sites | 4 | 3 | 25% reduction |

The codebase is measurably improved in structure. The `get_async()` method is now symmetric (both circuit-breaker and normal paths delegate to helpers), the FreshnessInfo construction is DRY, and the enum models all valid freshness states.

---

## Handoff

**Status**: Route to Janitor for BLOCK-001 fix.

**Requirements**:
1. Add type narrowing (assert or conditional) for `info` variable at lines 425, 435, 447 in `_check_freshness_and_serve()`
2. Run `mypy src/autom8_asana/cache/dataframe_cache.py --strict` -- must produce 0 errors
3. Run `pytest tests/unit/cache/dataframe/test_dataframe_cache.py -v --timeout=60` -- all 57 must pass
4. Single commit: `refactor(cache): fix mypy --strict type narrowing in _check_freshness_and_serve`

**After fix**: Re-submit for audit. Only the new commit will be reviewed.

---

## Verification Attestation

| Artifact | Read | Lines Verified |
|----------|------|----------------|
| `src/autom8_asana/cache/dataframe_cache.py` | Yes | 1-898 (all) |
| `.claude/artifacts/smell-report-lkg-swr-cache.md` | Yes | 1-440 (all) |
| `.claude/artifacts/refactoring-plan-lkg-swr-cache.md` | Yes | 1-346 (all) |
| `tests/unit/cache/dataframe/test_dataframe_cache.py` | Via pytest | 57/57 tests executed |
| Full test suite | Via pytest | 7938 passed |
| mypy --strict output | Yes | 3 errors documented |
| ruff check output | Yes | All checks passed |
| Git log (4 commits) | Yes | SHA, stat, messages verified |
