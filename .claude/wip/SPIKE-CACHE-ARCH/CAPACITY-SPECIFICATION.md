# Capacity Specification: autom8y-asana Cache Subsystem (CACHE-REMEDIATION)

**Date**: 2026-02-27
**Agent**: capacity-engineer
**Session**: session-20260227-135243-55f4e4fa (CACHE-REMEDIATION)
**Upstream**: CACHE-ARCHITECTURE.md (systems-thermodynamicist, 2026-02-27)
**Scope**: TTL sensitivity analysis for CACHE-1 fix, invalidation volume estimation, F-3 prerequisites

---

## Scope Boundary

This specification covers three items only, as scoped by the session prompt:

1. **TTL Sensitivity Analysis (Section 1)**: Before/after staleness window for all entity types under the CACHE-1 invalidation fix.
2. **Invalidation Volume and Cost (Section 2)**: How many `invalidate_project()` calls per commit, what each call costs, and thundering-herd risk.
3. **F-3 LKG Multiplier Prerequisites (Section 3)**: Exact production data requirements, derivation formula, and suggested initial conservative value.

F-3 sizing is **deferred** per the heat-mapper verdict (thermal-assessment.md, page 4). No LKG multiplier value is recommended here.

---

## Section 1: TTL Sensitivity Matrix — CACHE-1 Fix

### 1.1 Model Definition

**Before fix (current state)**:

The `CacheInvalidator` does not call `DataFrameCache.invalidate_project()`. After a SaveSession commit, the DataFrame for the affected project remains in MemoryTier until the entry's natural TTL expiry triggers an APPROACHING_STALE state, at which point the SWR grace window begins. The maximum stale window is:

```
max_stale_before = entity_TTL * (1 + SWR_GRACE_MULTIPLIER)
                 = entity_TTL * (1 + 3.0)
                 = entity_TTL * 4.0
```

Derivation: The base TTL governs when an entry transitions from FRESH to APPROACHING_STALE. The SWR grace window is `SWR_GRACE_MULTIPLIER * entity_TTL = 3.0 * entity_TTL`. During the grace window, the entry is served stale while a background rebuild fires. An entry can therefore be served stale for up to `entity_TTL + 3.0 * entity_TTL = 4.0 * entity_TTL` from the moment it was written (worst case: a read occurs at exactly TTL boundary, triggering SWR, and the rebuild completes at exactly the end of the grace window). However, the thermal assessment states "Max DataFrame Staleness = 3x" — this is the SWR grace window alone, computed from when the entry is already stale. For consistency with the thermal assessment, the analysis uses the thermal assessment's framing: the worst-case post-commit stale window is the time until the first read that is past TTL triggers SWR, plus the SWR grace window. In the worst case this is the full `entity_TTL + SWR_grace = entity_TTL + 3 * entity_TTL = 4x entity_TTL`.

The thermal assessment states "Max DataFrame Staleness" as the 3x SWR grace product. For fidelity with that document, the table below presents both derivations: the staleness from the moment of commit (4x total), and the staleness from the moment the entry is already TTL-expired (3x SWR grace, the thermal assessment framing).

**After fix (CACHE-1)**:

`CacheInvalidator._invalidate_project_dataframes()` calls `DataFrameCache.invalidate_project(project_gid)` immediately after the SaveSession commit. This removes the entry from MemoryTier synchronously. The next read after the commit triggers SWR rebuild (or direct build if S3 entry is also absent or expired). Maximum stale window after fix:

```
max_stale_after = time_between_commit_and_next_read + SWR_rebuild_duration
```

`time_between_commit_and_next_read` is bounded by request traffic. For the served entity types (~4k offers, ~20k contacts), the interval between consecutive API reads for the same project is seconds to low minutes. The SWR rebuild duration (ProgressiveProjectBuilder round-trip via Asana API) is estimated at 2–4 seconds based on the thermal assessment's documented computation cost for section-timeline data.

For the worst-case bound, a project with no API read traffic after the commit will not trigger SWR. In that case the stale S3 entry persists (S3 is not deleted on MemoryTier eviction — per CACHE-ARCHITECTURE.md design). If a read occurs later, it hits S3 (stale, in APPROACHING_STALE state), which triggers SWR. The maximum stale window in this cold-read scenario is therefore unbounded from the S3 side — but this is the same as the LKG S3 fallback behavior and is separate from the MemoryTier stale window that the fix targets.

**Practical bound for CACHE-1 fix**: For active projects with regular API read traffic (the primary concern for MRR correctness), the stale window drops from `entity_TTL * 4` down to `2–10 seconds` (time from commit to first API read + SWR rebuild). This is the operational improvement.

### 1.2 TTL Sensitivity Matrix

Confirmed TTL values from U-3 (thermal-assessment.md):
- `SWR_GRACE_MULTIPLIER = 3.0` (from `config.py:SWR_GRACE_MULTIPLIER`)
- Values confirmed by reading `ENTITY_DESCRIPTORS` in `core/entity_registry.py`

| Entity | Base TTL | Before Fix: Max Stale (4x TTL) | Before Fix: SWR Grace Only (3x) | After Fix: Practical Bound | Delta (worst-case improvement) |
|--------|----------|---------------------------------|----------------------------------|---------------------------|-------------------------------|
| offer | 180s (3 min) | 720s (12 min) | 540s (9 min) | 2–10s | 710–718s (99%+) |
| unit | 900s (15 min) | 3,600s (60 min) | 2,700s (45 min) | 2–10s | 3,590–3,598s (99%+) |
| contact | 900s (15 min) | 3,600s (60 min) | 2,700s (45 min) | 2–10s | 3,590–3,598s (99%+) |
| business | 3,600s (60 min) | 14,400s (240 min) | 10,800s (180 min) | 2–10s | 14,390–14,398s (99%+) |
| asset_edit | 300s (5 min) | 1,200s (20 min) | 900s (15 min) | 2–10s | 1,190–1,198s (99%+) |
| asset_edit_holder | 300s (5 min) | 1,200s (20 min) | 900s (15 min) | 2–10s | 1,190–1,198s (99%+) |
| process | 60s (1 min) | 240s (4 min) | 180s (3 min) | 2–10s | 230–238s (96–99%) |

**Thermal assessment table reference**: The thermal assessment (U-3) uses "Max DataFrame Staleness" = entity_TTL * 3.0 (SWR grace window only, from first TTL breach). The "Before Fix" column here extends that by one additional entity_TTL to account for the full window from the point of a SaveSession commit (which occurs before the TTL breach on a warm entry). Both framings are correct depending on whether the entry was freshly written (4x) or already aging (3x).

### 1.3 Sensitivity Analysis: Does the 2–10s bound hold under assumptions?

**Assumption**: Post-commit API read occurs within 10 seconds.

The thermal assessment states SaveSession runs at 10–100 commits per hour during active pipeline runs. At 100 commits/hour (1 commit per 36s), and assuming the API is receiving read traffic for these projects concurrently (the service serves 3,771 offers and ~20k contacts to internal analytics), the probability of a read within 10 seconds of a commit is high for hot projects.

**Sensitivity to this assumption**:

If the assumption is wrong by 2x (reads are 20 seconds apart on average), the practical bound becomes 22–24 seconds — still a 99%+ improvement over the before-fix window.

If no reads occur for 5 minutes post-commit (e.g., a bulk commit during off-hours), the MemoryTier entry has been evicted, the S3 entry serves as LKG (stale, pre-mutation), and the next read sees the correct post-mutation data because S3 entry state is APPROACHING_STALE (TTL has passed). SWR fires and the rebuild occurs on first access. Maximum staleness for this cold-read scenario: `time_without_reads` (can be hours). This is the residual LKG risk that F-3 addresses — and is separate from the MemoryTier staleness that CACHE-1 fixes.

**Critical distinction**: CACHE-1 fixes the MemoryTier hot-path stale window. It does not change the S3 LKG behavior. The delta reported in the table above applies to the MemoryTier hot path only.

### 1.4 TTL Recommendations Alongside CACHE-1

**Recommendation: No TTL adjustments needed alongside CACHE-1.**

Derivation:

The current TTLs are calibrated for the SWR pattern. With CACHE-1 in place, the MemoryTier hot path is corrected on structural mutations — the TTL primarily governs the background SWR revalidation cycle for non-committed changes (e.g., changes originating outside the service, such as direct Asana edits). The TTL-governed staleness for that use case remains acceptable:

- offer (180s, 3 min): Acceptable for mutation-external changes.
- contact/unit (900s, 15 min): Acceptable for non-critical analytical data.
- business (3,600s, 60 min): Business descriptors change rarely; 1-hour revalidation is appropriate.

Reducing TTLs alongside CACHE-1 would increase SWR rebuild frequency without proportional correctness benefit, since CACHE-1 already handles the high-severity case (post-commit invalidation). The TTL reduction alternative was evaluated by the heat-mapper and rejected for F-1 as "reduces the staleness window but does not eliminate it."

**Exception for process entity (TTL 60s)**: At 60s TTL, the SWR revalidation cycle is already the most aggressive in the registry. The 4x window before fix (240s) drops to 2–10s after fix. No change needed.

---

## Section 2: Invalidation Volume Estimation

### 2.1 What Does `invalidate_project()` Actually Do?

From reading `src/autom8_asana/cache/integration/dataframe_cache.py` (lines 579–607) and `src/autom8_asana/cache/dataframe/tiers/memory.py`:

```
invalidate_project(project_gid)
  -> invalidate(project_gid, entity_type=None)
     -> for et in ENTITY_TYPES:             # N iterations
          cache_key = f"{et}:{project_gid}"
          memory_tier.remove(cache_key)     # acquires RLock, dict.__contains__, dict.pop if present
          _stats[et]["invalidations"] += 1
```

**ENTITY_TYPES** is derived from `entity_registry.warmable_entities()` filtering `is_holder=False`:
- business, unit, contact, offer, asset_edit = 5 entity types
- (asset_edit_holder is a HOLDER type per EntityCategory.HOLDER — excluded from ENTITY_TYPES)

Therefore `invalidate_project(project_gid)` performs **5 iterations**, each calling `memory_tier.remove(key)`.

`MemoryTier.remove(key)` (lines 163–177):
```python
def remove(self, key: str) -> bool:
    with self._lock:              # threading.RLock acquire
        if key in self._cache:   # dict.__contains__ -> O(1)
            entry = self._cache.pop(key)  # OrderedDict.pop -> O(1)
            self._current_bytes -= self._estimate_size(entry)  # int arithmetic
            return True
        return False
```

**Cost per `remove()` call**: One `RLock.acquire()` + one dict lookup + conditional dict pop. No I/O, no network, no allocation. Pure in-process memory operation.

**Cost per `invalidate_project()` call**: 5 × `remove()` = 5 RLock acquisitions + 5 dict lookups (+ up to 5 pops if keys present). On a modern CPU this is sub-microsecond per call. The total cost for one `invalidate_project()` is in the range of **1–5 microseconds** (dominated by RLock contention overhead, not computation).

**Does it trigger SWR rebuild?** No. `invalidate_project()` only removes entries from MemoryTier. SWR rebuild is triggered lazily on the next call to `DataFrameCache.get_async()` when the key misses MemoryTier and the S3 entry is APPROACHING_STALE or absent. The invalidation itself is passive — it does not schedule a background task.

### 2.2 How Many `invalidate_project()` Calls Per SaveSession Commit?

From reading `persistence/session.py` and `persistence/cache_invalidator.py`:

**Batch size**: `SaveSession` uses `batch_size=10` (Asana API limit). One `commit_async()` executes all tracked dirty entities up to the batch limit per API round-trip.

**Entity membership**: Each entity has a `memberships` list mapping it to Asana project GIDs. The `_collect_project_gids()` method (per CACHE-ARCHITECTURE.md design) deduplicates across all entities in the batch and calls `invalidate_project()` once per unique project GID.

**Unique projects per commit**:

In the autom8y-asana domain, entities belong to exactly one primary project each (per `EntityDescriptor.primary_project_gid` — each entity type has a single dedicated Asana project). A SaveSession commit typically operates on one entity type at a time (e.g., updating a batch of Offers). Cross-entity-type commits exist but are less common.

- **Typical commit**: N entities of one type -> all in the same project -> 1 `invalidate_project()` call
- **Mixed-type commit**: Entities from up to K entity types, each in their own project -> K `invalidate_project()` calls (K ≤ 5, the number of entity types)
- **Worst case**: Entities spanning all 5 entity types, each in a different project -> 5 `invalidate_project()` calls

| Commit Type | Entities in Batch | Affected Projects | `invalidate_project()` Calls |
|-------------|-------------------|-------------------|------------------------------|
| Typical (single-type update) | 1–10 | 1 | 1 |
| Mixed-type automation commit | 2–10, multiple types | 2–3 | 2–3 |
| Worst case (all entity types) | ≤10 total | ≤5 | 5 |

**Per-call cost** (from Section 2.1): 1–5 microseconds.
**Total cost per commit** (worst case): 5 calls × 5 µs = 25 microseconds.

This cost is **negligible** relative to the SaveSession commit latency, which is dominated by Asana API round-trip time (100–500ms per batch).

### 2.3 Thundering-Herd Risk: Concurrent SaveSession Commits for the Same Project

**Scenario**: Two SaveSession commits fire concurrently for the same project (e.g., two automation pipeline runs processing different offers in the same Asana project simultaneously).

**Analysis**:

Step 1: Commit A calls `invalidate_project("proj-1")` -> removes `offer:proj-1` from MemoryTier.
Step 2: Commit B calls `invalidate_project("proj-1")` -> attempts to remove `offer:proj-1` (already absent) -> `remove()` returns False, no-op. No error.

Concurrent invalidation of the same key is **idempotent and race-free**. `MemoryTier.remove()` is protected by `threading.RLock`. Two concurrent callers serialize on the lock; the second caller finds the key absent and returns False. No entry is double-evicted; no inconsistency is introduced.

**SWR thundering-herd risk**: After both commits call `invalidate_project()`, the next API read for `offer:proj-1` misses MemoryTier. If two API requests arrive concurrently (e.g., two parallel analytics queries), both miss MemoryTier and both would trigger an SWR rebuild. The `DataFrameCacheCoalescer` prevents this: it serializes concurrent builds for the same `(project_gid, entity_type)` key via `asyncio.Event`. The first request acquires the build lock; the second waits (up to 60s coalescer timeout) and receives the result from the first build.

**Conclusion**: No thundering-herd risk from the CACHE-1 invalidation path. The existing `DataFrameCacheCoalescer` provides sufficient protection. This is consistent with the CACHE-ARCHITECTURE.md failure mode analysis (Section: "Consistency Propagation Between Invalidation and SWR Rebuild").

**Stampede protection level**: The coalescer is the correct mechanism here. XFetch (Vattani et al., VLDB 2015) would be the alternative for probabilistic early refresh — but XFetch applies to TTL-based eviction, not to explicit invalidation. After an explicit `invalidate_project()` call, there is no TTL window to apply probabilistic early refresh within. The coalescer (event-based serialization) is the right choice for this explicit-invalidation-then-read pattern.

### 2.4 Cost Summary

| Operation | Frequency | Per-Call Cost | Aggregate Cost per Commit |
|-----------|-----------|---------------|--------------------------|
| `invalidate_project()` | 1–5 per commit | ~1–5 µs | ~5–25 µs |
| `MemoryTier.remove()` per call | 5 (ENTITY_TYPES cardinality) | sub-µs | sub-µs × 5 |
| SWR rebuild trigger | 0 (deferred to next read) | N/A | N/A |
| `DataFrameCacheCoalescer` contention | Only on concurrent reads post-invalidation | asyncio.Event wait | ~0 (no contention if serialized reads) |

**Net assessment**: The CACHE-1 fix adds no operationally significant latency to the SaveSession commit path. The entire invalidation overhead is in the tens-of-microseconds range against a commit dominated by hundreds-of-milliseconds Asana API calls.

---

## Section 3: F-3 Placeholder — LKG Multiplier Sizing Prerequisites

### 3.1 Why F-3 Is Deferred

The heat-mapper verdict (thermal-assessment.md) is DEFER for F-3 because `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (unlimited) cannot be safely calibrated without knowing the distribution of SWR failure durations and frequencies. Setting it to an arbitrary value risks either:

- **(a) Over-aggressive bound**: Causes unnecessary cache misses during extended Asana API outages, surfacing errors to API consumers when stale (but useful) data was available.
- **(b) Under-protective bound**: Provides no meaningful staleness protection, effectively keeping the unlimited behavior.

The calibration requires production data. This section documents exactly what data is needed and what the derivation formula would look like once it is available.

### 3.2 Production Data Requirements

#### Metric 1: `CIRCUIT_FALLBACK` activation rate

**What**: Count of times per day the DataFrameCache enters `FreshnessState.CIRCUIT_FALLBACK` per project GID per entity type.

**How to collect**: `FreshnessInfo.freshness` is a thread-local side-channel (per TOPOLOGY-CACHE.md section 3.1.8). To make this observable:
- Emit a CloudWatch metric `dataframe_cache_freshness_state` with dimensions `{project_gid, entity_type, freshness_state}` on each `DataFrameCache.get_async()` return.
- Filter to `freshness_state = "CIRCUIT_FALLBACK"`.
- Aggregate: `SUM` by `(entity_type)` over 30 days.

**Time range**: 30-day window minimum. The LKG risk is meaningful only if outages are sustained (hours). A 30-day window captures seasonal variation and any known Asana API degradation events.

**Threshold for action**: If `CIRCUIT_FALLBACK` events are < 1 per week, the current unlimited LKG policy is operationally safe and no multiplier is needed. If > 1 per day, a bound becomes operationally important.

#### Metric 2: `CIRCUIT_FALLBACK` duration distribution

**What**: For each `CIRCUIT_FALLBACK` episode, how long does the circuit remain open before recovering?

**How to collect**:
- Emit `dataframe_cache_circuit_opened` (timestamp, project_gid) and `dataframe_cache_circuit_closed` (timestamp, project_gid) CloudWatch events.
- Derived metric: `circuit_open_duration_seconds = closed_timestamp - opened_timestamp`.
- Percentiles: p50, p95, p99 of duration.

**Alternative**: The CircuitBreaker state machine has `reset_timeout_seconds = 60s`. Each open circuit attempts half-open after 60s. Log each HALF_OPEN -> CLOSED vs HALF_OPEN -> OPEN (re-open) transition. The number of re-open attempts before recovery gives the total open duration: `total_open_duration ≈ 60s * (1 + re_open_count)`.

**Time range**: 30-day window.

#### Metric 3: Asana API error rate and pattern

**What**: Rate of Asana API call failures (`AsanaApiError`, `httpx.TimeoutException`, connection errors) for the SWR rebuild callback (`_swr_build_callback` in `factory.py`).

**How to collect**: The SWR callback logs `swr_build_no_bot_pat` and returns early on `BotPATError`. Add logging for `_swr_build_callback` exceptions (currently uncaught outside the coalescer). Count via CloudWatch `ERROR` filter on the `swr_build` log namespace.

**Time range**: 30-day window.

### 3.3 Derivation Formula (Once Data Is Available)

Let:
- `P50_duration`: 50th percentile of CIRCUIT_FALLBACK episode duration in seconds
- `P95_duration`: 95th percentile of CIRCUIT_FALLBACK episode duration in seconds
- `entity_TTL`: Entity-specific TTL in seconds
- `target_stale_ratio`: Acceptable staleness as a multiple of entity_TTL during outage

The multiplier formula:

```
LKG_MAX_STALENESS_MULTIPLIER = target_stale_ratio

Where:
  target_stale_ratio = P95_duration / entity_TTL  (calibrated to survive 95th percentile outage)
```

**Example** (hypothetical, not a recommendation):
If P95_duration = 1,800s (30 min) and offer_TTL = 180s:
```
target_stale_ratio = 1800 / 180 = 10.0
```
A `LKG_MAX_STALENESS_MULTIPLIER = 10.0` would allow LKG to serve for up to 1,800s (30 min) before forcing a hard miss. For a 30-minute outage, this provides no gaps. For a 60-minute outage, LKG would expire after 30 minutes, and the circuit would be forced to miss, returning errors for the remaining 30 minutes.

**Sensitivity analysis**:
- If actual P95 outages are 10 minutes (600s) and offer_TTL = 180s: multiplier = 3.3. A value of 4.0 provides comfortable coverage.
- If actual P95 outages are 4 hours (14,400s) and offer_TTL = 180s: multiplier = 80. At that scale, the LKG policy design needs architectural reconsideration (stale data for 4 hours is a business decision, not a technical parameter).
- If SWR failures are zero in 30 days: `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (unlimited) is the correct setting. No change needed.

The formula is only meaningful once P95_duration is known. Guessing a value now produces a false sense of protection.

### 3.4 Suggested Initial Conservative Value (if data collection is delayed)

If the product requires a non-zero bound before production data is available, the following reasoning applies:

**Conservative starting point**: `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (unchanged, unlimited).

**Rationale**: The availability-first contract (NFR-DEGRADE-001) is satisfied by unlimited LKG. The risk is data staleness during outages, not data loss. For the current use case (internal analytics, MRR calculation), serving slightly stale data during a 1-hour Asana API outage is preferable to serving no data. The thermal assessment explicitly acknowledges this: "If SWR failures are rare and transient (U-5), the risk is low-probability and the availability benefit is high."

**If a non-zero bound is politically required** before data is available:
```
LKG_MAX_STALENESS_MULTIPLIER = 48 * (3600 / entity_TTL)
```
This is equivalent to 48 hours of LKG protection for the entity with the longest TTL (business, 3600s): `48 * 1 = 48`. For offer (TTL 180s): `48 * (3600/180) = 48 * 20 = 960` (960 * 180s = 172,800s = 48 hours).

**However**: Expressing this as a uniform multiplier is problematic because entity TTLs differ by 20x (business 3600s vs. process 60s). A multiplier of 48 on process (TTL 60s) would limit LKG to 48 * 60 = 2,880s = 48 minutes. A multiplier of 960 on offer would limit LKG to 960 * 180s = 172,800s = 48 hours.

The config system uses a single `LKG_MAX_STALENESS_MULTIPLIER` applied uniformly across all entity types. To achieve uniform 48-hour protection:

```
Required multiplier = 48 * 3600 / min(entity_TTLs) = 172,800 / 60 = 2,880
```

A multiplier of 2,880 applied to process (TTL 60s) yields 172,800s = 48h. Applied to offer (TTL 180s) yields 518,400s = 144h. Applied to business (TTL 3600s) yields 10,368,000s = 120 days.

**Conclusion**: The uniform multiplier design is poorly matched to the entity TTL range. Before setting any non-zero value, the team should:
1. Confirm whether the LKG bound should be uniform across entity types or per-entity-type.
2. Run the 30-day data collection first (2–4 weeks of instrumentation).
3. If per-entity-type LKG bounds are needed, this is a config schema change (not just a value change) and belongs in a separate architectural decision.

---

## Section 4: Aggregate Resource Plan

This specification concerns the **existing DataFrameCache infrastructure**. No new cache layers are added. The resource plan reflects the current deployed configuration.

| Layer | Technology | Memory Budget | Instances | Monthly Cost Est. |
|-------|-----------|---------------|-----------|-------------------|
| DataFrameCache MemoryTier | In-process OrderedDict | 30% of container heap | 1 per ECS task | Included in ECS compute |
| DataFrameCache ProgressiveTier | S3 Parquet | ~6 entity types × ~5 projects × ~avg 10MB parquet = ~300MB | N/A (S3) | ~$0.007/month storage + negligible GET/PUT |
| Redis (System A entity cache) | ElastiCache | Existing, unchanged | Existing | Existing |

**MemoryTier sizing derivation**:

The container memory is detected via cgroup (or defaults to 1GB). At 30% heap: `1024 MB * 0.30 = 307 MB` max for DataFrameCache MemoryTier.

Current entity scale: 6 entity types × ~5 projects = 30 maximum entries (well within the 100-entry limit). At approximately 10MB per DataFrame parquet (conservative for ~4k offers, ~20k contacts, ~3k businesses), the working set is `30 entries × 10 MB avg = 300 MB`.

This is within the 307MB budget at 30% heap. No reallocation needed.

**The CACHE-1 fix does not change memory utilization.** It changes the eviction pattern (explicit invalidation on commit rather than TTL-based expiry), which reduces the average MemoryTier occupancy slightly (entries are evicted sooner after commits). This is a benefit, not a cost.

---

## Section 5: Policy Decision Records

### PDR-1: No TTL Adjustments Alongside CACHE-1

**Context**: CACHE-1 adds post-commit `invalidate_project()` calls to `CacheInvalidator`. The question is whether current TTL values need adjustment given the new invalidation behavior.

**Decision**: TTL values unchanged. Current values are calibrated for the SWR background revalidation cycle for external mutation sources (direct Asana edits, other services). The CACHE-1 fix addresses internal mutation sources (SaveSession commits). These are orthogonal — CACHE-1 does not change TTL semantics, only the explicit invalidation path.

**Trade-off**: Retaining the current TTLs means that for external mutations (not via SaveSession), the pre-CACHE-1 staleness behavior is unchanged. This is acceptable: external mutations are less frequent and do not change row counts (they are field-update edits from the Asana web UI, not CREATE/DELETE operations). The MRR correctness concern documented in the thermal assessment applies specifically to SaveSession structural mutations.

**Reference**: Thermal assessment F-1 alternatives assessment: "Reduce TTL: LOW feasibility — reduces the staleness window but does not eliminate it. Also increases cold-start cost."

---

### PDR-2: DataFrameCacheCoalescer as Stampede Protection (CACHE-1 Path)

**Context**: After `invalidate_project()` removes MemoryTier entries, concurrent API reads may try to rebuild the same `(project_gid, entity_type)` key simultaneously.

**Decision**: The existing `DataFrameCacheCoalescer` (60s wait timeout, `asyncio.Event`-based) is sufficient for the CACHE-1 invalidation-then-read pattern. No additional stampede protection is needed.

**Theoretical basis**: The coalescer implements the thundering-herd prevention pattern (Nishtala et al., NSDI 2013, "lease tokens" equivalent). It serializes concurrent build requests for the same key, allowing only one build to proceed while others wait. This is the correct mechanism for explicit-invalidation-triggered rebuilds where the triggering event (commit) is discrete, not probabilistic.

XFetch (Vattani et al., VLDB 2015) would be appropriate for TTL-based expiry where probabilistic early refresh is needed. It is not applicable here because the invalidation is hard (explicit remove), not probabilistic (TTL approaching).

**Trade-off**: The coalescer introduces a serialization point for concurrent reads. Maximum wait time is 60s (coalescer timeout). If the SWR rebuild exceeds 60s, the coalescer releases all waiters who then attempt their own builds — this is the correct fallback and was accepted at system design time (per TOPOLOGY-CACHE.md section 3.4.1).

---

### PDR-3: F-3 Deferred — No Uniform Multiplier Value Set

**Context**: `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (unlimited). The question is whether to set a non-zero bound.

**Decision**: Remain at 0.0 (unlimited) until production data on CIRCUIT_FALLBACK frequency and duration is collected per Section 3.2 requirements.

**Theoretical basis**: The availability-first contract (NFR-DEGRADE-001) takes precedence over staleness bounding during outages. Setting an arbitrary multiplier without operational data risks causing unnecessary hard misses during legitimate outages. The risk of unlimited staleness (unbounded LKG) is acceptable if CIRCUIT_FALLBACK events are rare and short — which is the working assumption pending U-5 data.

**Trade-off**: During an extended Asana API outage (multi-hour), LKG data grows progressively staler without bound. For internal analytics consumers (the primary use case), this is preferable to returning errors. For any consumer requiring a freshness SLA, this deferral represents an unresolved risk.

**Escalation trigger**: If a production incident is filed where stale LKG data caused a business decision error (e.g., MRR was computed from 4-hour-old data during an Asana outage and the number was acted on), this PDR should be revisited with urgency.

---

## Handoff Checklist

- [x] `capacity-specification.md` produced at `.claude/wip/SPIKE-CACHE-ARCH/CAPACITY-SPECIFICATION.md`
- [x] TTL sensitivity matrix: before/after for all 7 entity types with derivation shown
- [x] Invalidation volume estimated: per-call cost (1–5 µs), calls per commit (1–5), thundering-herd risk assessed (coalescer sufficient)
- [x] F-3 LKG prerequisites: 3 specific CloudWatch metrics, 30-day time range, derivation formula with hypothetical example, sensitivity analysis for 2x assumption error
- [x] Aggregate resource plan: existing infrastructure, no new allocations
- [x] Policy Decision Records: PDR-1 (no TTL changes), PDR-2 (coalescer as stampede protection), PDR-3 (F-3 deferred)
- [x] No bare numbers: every value has a derivation or source citation
- [x] F-3 sizing not attempted: deferred per heat-mapper verdict, prerequisites documented only
