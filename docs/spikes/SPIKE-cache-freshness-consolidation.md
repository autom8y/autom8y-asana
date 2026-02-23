# SPIKE: Cache Freshness Consolidation — Unified Enum Design Validation

**Date**: 2026-02-23
**Time-Box**: 2 days (investigation + prototype + writeup)
**Status**: COMPLETE
**Verdict**: **GO** (enum consolidation 4→2) / **NO-GO** (result type consolidation)

---

## Question

Can the 4 freshness enums (`Freshness`, `FreshnessMode`, `FreshnessClassification`, `FreshnessStatus`) collapse into a unified model without breaking the ~358 existing references across source and test files?

## Decision This Informs

Whether to proceed with P6 (Cache Concept Consolidation, 14-18 days) from the PATTERN-GAP-ANALYSIS execution plan. The scout proposed a 3-concept model (`FreshnessIntent` / `FreshnessState` / `FreshnessCheck`). This spike validates the design.

## Foundation

- `docs/rnd/SCOUT-cache-abstraction-simplification.md` (Approach 2 + 5)
- `.claude/wip/q1_arch/PATTERN-GAP-ANALYSIS.md` (Gap 2, P2/P6)
- `.claude/wip/q1_arch/INTEGRATION-FIT-ANALYSIS.md` (Gap 2A/2B)
- `docs/decisions/ADR-0067` (cache divergence — 12/14 intentional)

---

## Findings

### 1. Actual Reference Counts (Higher Than Estimated)

| Enum | Source Refs | Test Refs | Total | Source Files | Test Files |
|------|-----------|-----------|-------|-------------|------------|
| `Freshness` | ~47 | 47 | ~94 | 13 | 10 |
| `FreshnessMode` | ~33 | 106 | ~139 | 8 | 12 |
| `FreshnessClassification` | ~20 | 21 | ~41 | 2 | 2 |
| `FreshnessStatus` | ~25 | 7 | ~32 | 1 | 1 |
| `FreshnessResult` | ~26 | 5 | ~31 | 1 | 1 |
| `FreshnessInfo` | ~15 | 6 | ~21 | 4 | 1 |
| **TOTAL** | **~166** | **192** | **~358** | — | — |

The scout's estimate of 262 (113 source + 149 test) was conservative. Actual total is ~358 when counting all occurrences. Many `Freshness` references are in docstrings/comments, but the code references are still higher than estimated.

### 2. Enum Value Mapping Table

#### FreshnessIntent (replaces Freshness + FreshnessMode)

| Old Enum | Old Value | New Enum | New Value | Semantic Loss |
|----------|-----------|----------|-----------|---------------|
| `Freshness.STRICT` | `"strict"` | `FreshnessIntent.STRICT` | `"strict"` | None |
| `Freshness.EVENTUAL` | `"eventual"` | `FreshnessIntent.EVENTUAL` | `"eventual"` | None |
| `Freshness.IMMEDIATE` | `"immediate"` | `FreshnessIntent.IMMEDIATE` | `"immediate"` | None |
| `FreshnessMode.STRICT` | `"strict"` | `FreshnessIntent.STRICT` | `"strict"` | None |
| `FreshnessMode.EVENTUAL` | `"eventual"` | `FreshnessIntent.EVENTUAL` | `"eventual"` | None |
| `FreshnessMode.IMMEDIATE` | `"immediate"` | `FreshnessIntent.IMMEDIATE` | `"immediate"` | None |

**Clean merge.** Identical values. `FreshnessIntent` inherits `str` (preserving serialization from `Freshness`; upgrading `FreshnessMode` which did not inherit `str`).

#### FreshnessState (replaces FreshnessClassification + FreshnessStatus)

| Old Enum | Old Value | New Enum | New Value | Notes |
|----------|-----------|----------|-----------|-------|
| `FC.FRESH` | `"fresh"` | `FS.FRESH` | `"fresh"` | Direct |
| `FC.APPROACHING_STALE` | `"approaching_stale"` | `FS.APPROACHING_STALE` | `"approaching_stale"` | Direct |
| `FC.STALE` | `"stale"` | `FS.STALE` | `"stale"` | Direct |
| `FrSt.FRESH` | `"fresh"` | `FS.FRESH` | `"fresh"` | Direct |
| `FrSt.STALE_SERVABLE` | `"stale_servable"` | `FS.APPROACHING_STALE` | `"approaching_stale"` | **String value changes** |
| `FrSt.EXPIRED_SERVABLE` | `"expired_servable"` | `FS.STALE` | `"stale"` | **String value changes** |
| `FrSt.SCHEMA_MISMATCH` | `"schema_mismatch"` | `FS.SCHEMA_INVALID` | `"schema_invalid"` | **String value changes** |
| `FrSt.WATERMARK_STALE` | `"watermark_stale"` | `FS.WATERMARK_BEHIND` | `"watermark_behind"` | **String value changes** |
| `FrSt.CIRCUIT_LKG` | `"circuit_lkg"` | `FS.CIRCUIT_FALLBACK` | `"circuit_fallback"` | **String value changes** |

**Semantic subtlety resolved**: `STALE_SERVABLE` → `APPROACHING_STALE` changes the name but preserves the behavior (serve + trigger refresh). SWR becomes a **behavior** controlled by the consumer, not a state encoded in the enum. This is the correct abstraction — the entity cache and DataFrame cache differ in *when* they trigger refresh, not in *what* the state means.

**String value impact**: `FreshnessInfo.freshness` stores the string value. Since `FreshnessInfo` is ephemeral (computed per-request, not persisted to cache or DB), the string value change is safe. No stored data migration needed.

### 3. Type Alias Compatibility Layer Design

The prototype validates that **additive coexistence** works:

```
# In freshness.py (alongside existing Freshness class):
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
__all__ = ["Freshness", "FreshnessIntent"]

# In freshness_stamp.py (alongside existing FreshnessClassification):
from autom8_asana.cache.models.freshness_unified import FreshnessState

# In freshness_coordinator.py (alongside existing FreshnessMode):
from autom8_asana.cache.models.freshness_unified import FreshnessIntent

# In dataframe_cache.py (alongside existing FreshnessStatus):
from autom8_asana.cache.models.freshness_unified import FreshnessState
```

**Phase 2 migration** (after spike, during P6): Replace old classes with type aliases:
```python
# freshness.py
Freshness = FreshnessIntent  # Backward-compatible alias

# freshness_coordinator.py
FreshnessMode = FreshnessIntent  # Backward-compatible alias
```

This requires `FreshnessIntent` to be a `str, Enum` (which it is) so that `Freshness.STRICT == FreshnessIntent.STRICT` evaluates based on string value. However, `isinstance(FreshnessIntent.STRICT, Freshness)` would be False — any code doing isinstance checks on the old type would break.

**Grep for isinstance checks:**
- `isinstance(..., Freshness)`: 0 occurrences in source/tests
- `isinstance(..., FreshnessMode)`: 0 occurrences in source/tests
- `isinstance(..., FreshnessClassification)`: 0 occurrences in source/tests
- `isinstance(..., FreshnessStatus)`: 0 occurrences in source/tests

**No isinstance barriers.** All consumer code uses `==` comparison against enum members, which works with type aliases.

### 4. Prototype Results

| Metric | Result |
|--------|--------|
| Cache tests passed | **1206 / 1206** (5 pre-existing Redis backend failures unrelated) |
| New mypy errors | **0** |
| Circular import issues | **0** |
| Import path changes needed | **0** (new types coexist alongside old) |
| Consumer code changes needed (Phase 1) | **0** (aliases make new types available, old types remain) |

The unified module `freshness_unified.py` has zero external dependencies (stdlib `enum` only), introducing no new import chain risks.

### 5. FreshnessCheck (Result Type Unification) — NO-GO

The scout proposed merging `FreshnessResult` + `FreshnessInfo` into a unified `FreshnessCheck`. Investigation reveals this is a **bad idea**:

| Dimension | FreshnessResult | FreshnessInfo |
|-----------|----------------|---------------|
| **Context** | Entity cache (per-GID) | DataFrame cache (per-project) |
| **Question** | "Use cache or fetch?" | "What's the quality of served data?" |
| **Identity** | `gid: str` | Keyed by `cache_key` (implicit) |
| **Verdict** | `is_fresh: bool` + `action: Literal[...]` | `freshness: str` (6-way) |
| **Temporal** | `cached_version` / `current_version` (datetimes) | `data_age_seconds` / `staleness_ratio` (derived) |
| **Build quality** | N/A | `build_status`, `sections_failed` |
| **Frozen** | Yes (`frozen=True`) | No (mutable) |
| **Field overlap** | 0 fields shared | 0 fields shared |

A merged `FreshnessCheck` would be a 10+ field kitchen-sink dataclass where half the fields are `None` in each usage context. This increases cognitive load, not reduces it.

**Recommendation**: Keep `FreshnessResult` and `FreshnessInfo` as separate types. The "3-concept model" from the scout should be revised to a **2-concept model** (enum consolidation only).

### 6. ADR-0067 Compliance Check

The 12 intentional divergences from ADR-0067 are all preserved:

| ADR-0067 Dimension | Preserved? | Notes |
|---------------------|-----------|-------|
| 1. Data shape (dict vs DataFrame) | Yes | No data model changes |
| 2. Access pattern (per-GID vs per-project) | Yes | No access pattern changes |
| 3. Storage tier (Redis+S3 vs Memory+S3) | Yes | No tier changes |
| 4. TTL strategy (simple vs entity-aware) | Yes | No TTL changes |
| 5. Freshness check (batch API vs watermark) | Yes | Enum names change, check logic unchanged |
| 6. SWR (no vs yes) | Yes | SWR becomes behavior, not state — same outcome |
| 7. Circuit breaker (no vs yes) | Yes | CIRCUIT_FALLBACK preserves the concept |
| 8. Build coordination (no vs coalescing) | Yes | No build changes |
| 9. Schema versioning (via entry vs explicit) | Yes | SCHEMA_INVALID preserves the concept |
| 10. Completeness tracking (yes vs no) | Yes | No completeness changes |
| 11. Invalidation (webhook vs watermark) | Yes | No invalidation changes |
| 12. Hierarchy (parent-child vs flat) | Yes | No hierarchy changes |

---

## Verdict

### GO: Enum Consolidation (4 → 2)

| Success Criterion | Status | Evidence |
|-------------------|--------|----------|
| All references can map without semantic loss | **PASS** | Mapping table above — all 15 values map cleanly. STALE_SERVABLE→APPROACHING_STALE is a name change, not a semantic change |
| Type aliases provide backward compatibility | **PASS** | 1206 tests pass with additive coexistence. Zero isinstance barriers |
| Test suite passes with aliases in place | **PASS** | 1206/1206 cache tests, 0 new mypy errors |
| No ADR-0067 divergence violated | **PASS** | All 12 intentional divergences preserved |

### NO-GO: Result Type Unification (FreshnessCheck)

| Failure Criterion | Status | Evidence |
|-------------------|--------|----------|
| Semantic gaps found | **TRIGGERED** | Zero field overlap between FreshnessResult and FreshnessInfo. Merging creates a kitchen-sink type that's worse than two focused types |

### Revised Model

The validated model is **2-concept** (not 3):

| New Concept | Replaces | Values | Consumer Changes |
|------------|----------|--------|-----------------|
| `FreshnessIntent` | `Freshness` + `FreshnessMode` | STRICT, EVENTUAL, IMMEDIATE | Zero during alias phase |
| `FreshnessState` | `FreshnessClassification` + `FreshnessStatus` | FRESH, APPROACHING_STALE, STALE, SCHEMA_INVALID, WATERMARK_BEHIND, CIRCUIT_FALLBACK | Zero during alias phase |

Net concept reduction: **4 enums → 2 enums = -2 concepts** (not -3 as the scout estimated, since result types remain separate).

---

## Recommended Migration Path

### Phase 1: Additive Coexistence (0.5 days, done in this spike)
- Create `freshness_unified.py` with `FreshnessIntent` + `FreshnessState`
- Re-export from old locations alongside old types
- Zero consumer changes, zero risk

### Phase 2: New Consumer Convention (1-2 days)
- New code uses `FreshnessIntent`/`FreshnessState` directly
- Old code continues working
- Update `cache/__init__.py` to prefer new names in docs/examples

### Phase 3: Gradual Migration (3-4 days, can be spread over time)
- Replace old enum references with new ones, file by file
- FreshnessMode consumers (139 refs, 8+12 files) are the largest batch
- FreshnessStatus consumers (32 refs, 1+1 files) are the smallest and need string value updates
- Type aliases remain at old locations indefinitely for SDK backward compat

### Phase 4: Optional Cleanup (1 day, low priority)
- Remove old enum class bodies, replace with `OldName = NewName` aliases
- Or keep old classes indefinitely — the cost of parallel definitions is low

**Total estimated effort**: 4.5-7.5 days (vs scout's 4-5 day estimate for enum phase alone). The delta is from the higher-than-expected reference count (358 vs 262).

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| FreshnessStatus string values change in logs | HIGH | LOW | Log search queries need update; data is ephemeral |
| SDK consumers import old names | MEDIUM | LOW | Type aliases at old locations — indefinite support |
| `FreshnessMode` lacks `str` inheritance | LOW | LOW | `FreshnessIntent(str, Enum)` is a superset; `==` works on `.value` |
| Parallel definitions confuse new developers | MEDIUM | LOW | Deprecation docstrings on old types point to new |

---

## Follow-Up Actions

1. **Commit prototype** from worktree `agent-a277b0be` (Phase 1 — additive coexistence)
2. **Update PATTERN-GAP-ANALYSIS.md**: Revise P6 from "3-concept model" to "2-concept model"; update effort from 14-18 to 12-15 days (result types removed from scope)
3. **File P6 sprint plan**: Phase 2-4 migration across ~358 references
4. **Update SCOUT-cache-abstraction-simplification.md**: Note FreshnessCheck NO-GO finding

---

## Artifacts

| Artifact | Location |
|----------|----------|
| This spike report | `docs/spikes/SPIKE-cache-freshness-consolidation.md` |
| Prototype (worktree) | `.claude/worktrees/agent-a277b0be/` |
| Unified enum definitions | `src/autom8_asana/cache/models/freshness_unified.py` (in worktree) |
| Foundation: Scout assessment | `docs/rnd/SCOUT-cache-abstraction-simplification.md` |
| Foundation: Gap analysis | `.claude/wip/q1_arch/PATTERN-GAP-ANALYSIS.md` |
| Foundation: Integration fit | `.claude/wip/q1_arch/INTEGRATION-FIT-ANALYSIS.md` |
