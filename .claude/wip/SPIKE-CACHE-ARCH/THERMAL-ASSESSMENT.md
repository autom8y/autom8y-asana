# Thermal Assessment: autom8y-asana Cache Subsystem

**Date**: 2026-02-27
**Agent**: heat-mapper
**Session**: session-20260227-135243-55f4e4fa (CACHE-REMEDIATION)
**Complexity**: STANDARD (5 targeted findings, pre-seeded reconnaissance)

---

## System Context

- **Service(s) assessed**: `autom8_asana` — single-package Python service (FastAPI + Lambda handlers)
- **Current caching**: Extensive. Two independent tiered systems:
  - System A: Entity cache (Redis ElastiCache hot + S3 cold), serving `CacheEntry` objects (tasks, stories, timelines)
  - System B: DataFrame cache (in-process OrderedDict hot + S3 Parquet cold), serving Polars analytical DataFrames
- **Primary concern**: Remediation — five specific anti-pattern findings from architectural spike require 6-gate evaluation and verdict
- **Reconnaissance source**: Pre-seeded spike artifacts at `.claude/wip/SPIKE-CACHE-ARCH/` (TOPOLOGY, DEPENDENCY, ASSESSMENT, ARCHITECTURE-REPORT). Reconnaissance not repeated here.

---

## Unknown Resolution Results

These were resolved through code inspection before applying the gate framework, as they directly gate the verdicts.

### U-1: Was the SaveSession DataFrameCache gap intentional?

**Resolution**: GAP (not intentional design).

**Evidence**:
- `MutationInvalidator` was created in commit `c4c8b77` (2026-02-04) as part of the "Deep Hygiene Sprint" that reorganized the cache module into subpackages. It was designed with `DataFrameCache` project-level invalidation from day one (constructor accepts `dataframe_cache: DataFrameCache | None`).
- `CacheInvalidator` predates this commit. In `c4c8b77`, only its import paths were updated (refactored from `cache.entry` to `cache.models.entry`, and from `cache.dataframes` to `cache.integration.dataframes`). The `DataFrameCache.invalidate_project()` capability was never backported to `CacheInvalidator._invalidate_dataframe_caches()`.
- No ADR, TDD document, or code comment addresses this asymmetry as a deliberate design choice. The `CacheInvalidator` docstring references FR-INVALIDATE-001 through FR-INVALIDATE-006 and TDD-WATERMARK-CACHE, none of which mention project-level DataFrame cache exclusion.
- `CacheInvalidator.__init__` only accepts a `cache_provider` (System A provider). It has no `dataframe_cache` parameter, so it structurally cannot call `DataFrameCache.invalidate_project()` without a refactor.

**Conclusion**: The gap is an oversight. The `CacheInvalidator` was extracted before `MutationInvalidator` gained project-level DataFrame invalidation, and that capability was never backported. F-1 is a concrete staleness bug.

---

### U-2: Is 300s timeline staleness acceptable to section-timeline consumers?

**Resolution**: CANNOT CONFIRM FROM CODE — but evidence strongly suggests 300s is acceptable by design.

**Evidence**:
- The section-timelines API route (`api/routes/section_timelines.py`) is an on-demand analytical endpoint. Consumers pass `period_start`/`period_end` date range parameters, indicating a reporting/analytics use case (not a real-time operational feed).
- The comment in `derived.py` line 31 explicitly documents the trade-off: "Balances freshness (stories may update) vs. computation cost (~2-4s for 3,800 entities)." This is an engineer-authored intent statement.
- The SectionTimeline feature shipped 2026-02-19 with a `<1.5s` latency target (from project memory). That target is about warm-path performance, not freshness guarantees — consistent with reporting use.
- No consumer SLA is referenced in the code or ADRs. The API accepts historical date ranges where freshness within minutes is irrelevant.
- The service uses a `compute-on-read-then-cache` architecture (per `TDD-SECTION-TIMELINE-REMEDIATION` docstring), with a thundering-herd lock. This pattern is consistent with batch analytics, not real-time operations.

**Conclusion**: 300s is likely acceptable for the reporting use case. The finding is a known trade-off, not a concrete bug. This assessment escalates the staleness acceptability question but assigns a CACHE verdict with a note that the business owner should confirm.

---

### U-3: What are the actual runtime TTL values from EntityRegistry?

**Resolution**: CONFIRMED. Values match documented values.

**Evidence**: `ENTITY_DESCRIPTORS` in `core/entity_registry.py` defines `default_ttl_seconds` per entity:

| Entity | TTL (seconds) | SWR Grace (3.0x) | Max DataFrame Staleness |
|--------|--------------|------------------|------------------------|
| business | 3600 (60 min) | 10,800s (180 min) | 180 min |
| unit | 900 (15 min) | 2,700s (45 min) | 45 min |
| contact | 900 (15 min) | 2,700s (45 min) | 45 min |
| offer | 180 (3 min) | 540s (9 min) | 9 min |
| asset_edit | 300 (5 min) | 900s (15 min) | 15 min |
| process | 60 (1 min) | 180s (3 min) | 3 min |
| location | 3600 (60 min) | 10,800s (180 min) | 180 min |
| hours | 3600 (60 min) | 10,800s (180 min) | 180 min |
| asset_edit_holder | 300 (5 min) | 900s (15 min) | 15 min |

These match the values in TOPOLOGY-CACHE.md section 6. The "Max DataFrame Staleness" column is the worst-case window for F-1: how long a stale DataFrame persists after a SaveSession commit before natural TTL + SWR expiry.

---

### U-4: Do cross-entity DataFrames share derived columns?

**Resolution**: NO cross-entity DataFrame dependencies. Cascade columns are resolved at extraction time from the Asana task hierarchy — not from other entity DataFrames.

**Evidence**:
- `offer.py` schema shows `cascade:Office Phone`, `cascade:Vertical`, `cascade:MRR`, `cascade:Weekly Ad Spend`. The `cascade:` prefix indicates Asana parent-task field inheritance resolved at extraction time from the API response, not from querying another entity type's DataFrame.
- Same pattern in `unit.py` (`cascade:Business Name`, `cascade:Office Phone`), `contact.py` (`cascade:Office Phone`, `cascade:Vertical`), `asset_edit.py` (`cascade:Vertical`, `cascade:Office Phone`).
- Each entity type's DataFrame is built independently per project_gid from its own Asana project's tasks. The join keys in `EntityDescriptor` (e.g., `("unit", "office_phone")`) enable runtime query joins via the query CLI but do not create build-time dependencies between cached DataFrames.

**Conclusion**: R-4 (cross-entity coherence gap) can be closed. Entity DataFrames are cache-independent. When an Offer changes, the Unit or Business DataFrame does not need invalidation because those DataFrames do not contain columns derived from Offer data.

---

### U-6: What does the `connection_manager` parameter do?

**Resolution**: Forward scaffolding, not yet wired in production. Dead in current call path.

**Evidence**:
- `RedisCacheProvider.__init__` accepts `connection_manager: Any | None = None`. When provided, pool initialization is skipped (`if self._connection_manager is None: self._initialize_pool()`). `_get_connection()` delegates to `self._connection_manager.get_connection()` instead of the pool.
- No caller in `src/autom8_asana/` passes a `connection_manager` to `RedisCacheProvider`. The `CacheProviderFactory.create()` does not pass it. The parameter is fully dormant in all current production paths.
- Same pattern exists in `S3CacheProvider` (same forward scaffolding, same dead-in-production status).
- Per project memory, COMPAT-PURGE reclassified this as "intentional forward scaffolding" (connection lifecycle management TDD-CONNECTION-LIFECYCLE-001 Phase 1).

**Conclusion**: Low operational risk. The `connection_manager` parameter is dead code that enables a future connection lifecycle management feature. No action required now; this is a hygiene item for a future pass.

---

## Access Pattern Analysis

For the CACHE-verdicted findings, access patterns relevant to the invalidation paths.

### Hot Path: SaveSession Batch Commit (F-1)

- **Read/write ratio**: Write-heavy (batch mutations trigger this path)
- **Frequency**: SaveSession runs on every automation cycle. Estimated 10–100 commits per hour during active pipeline runs based on the system serving 3,771 offers with section-change driven automations.
- **Origin cost**: After a structural mutation (CREATE/DELETE), the DataFrame cache serves stale data for up to 9 min (offer) to 45 min (contact). The cost is incorrect API responses, not latency.
- **Staleness tolerance**: Zero tolerance for structural mutations. An offer that was deleted but still appears in API count responses, or a new offer that doesn't appear in listings, is a data correctness defect.
- **Data sensitivity**: Internal business data (not PII in cache keys). DataFrameCache entries are Polars DataFrames, not individual PII fields.
- **Growth trajectory**: Stable. The offer/unit/contact entity counts are bounded by business scale (~4k offers, ~20k contacts).

### Hot Path: Section-Timeline Request (F-2)

- **Read/write ratio**: Read-heavy. Computation is write-once-read-many per 300s window.
- **Frequency**: On-demand API endpoint. Frequency unknown without production metrics. Likely low (analytical query, not a hot real-time path).
- **Origin cost**: 2–4s computation for 3,800 entities on cache miss. Significant — justifies caching.
- **Staleness tolerance**: 300s (5 min) is the current behavior. Evidence suggests this is acceptable for the reporting use case. See U-2.
- **Data sensitivity**: Offer section history (not PII, not financial transaction data).
- **Growth trajectory**: Stable. Bounded by offer count (~4k).

### Hot Path: DataFrame LKG Fallback During Outage (F-3)

- **Read/write ratio**: Read-only (LKG path serves reads when SWR fails)
- **Frequency**: Only activates during SWR failure. Frequency unknown (U-5 — production metrics required).
- **Origin cost**: LKG data is already in MemoryTier; zero origin cost. The risk is staleness duration, not access cost.
- **Staleness tolerance**: Currently unlimited (0.0 multiplier). The appropriate bound is an operational decision.
- **Data sensitivity**: Same as general DataFrameCache — not PII in cache structure.
- **Growth trajectory**: Irrelevant to the finding (this is a failure-mode concern, not a growth concern).

---

## Alternatives Assessment

For each finding, non-cache alternatives are evaluated before applying the 6-gate framework.

### F-1: SaveSession DataFrameCache Gap

| Alternative | Feasibility | Expected Impact | Effort |
|-------------|-------------|-----------------|--------|
| Query optimization | LOW | Irrelevant. The problem is cache not being invalidated, not query performance. | N/A |
| Reduce TTL | LOW | Reduces the staleness window but does not eliminate it. Also increases cold-start cost. | Low |
| Disable DataFrameCache for SaveSession path | LOW | Forces every API request to rebuild from Asana API. Unacceptable latency. | N/A |
| Accept eventual consistency | LOW | Acceptable for pure field updates, but structural mutations (CREATE/DELETE) produce wrong row counts — a correctness defect, not just staleness. | N/A |
| Add `dataframe_cache` injection to `CacheInvalidator` + call `invalidate_project()` | HIGH | Eliminates the gap completely. Pattern already exists in `MutationInvalidator`. | ~3 hours |

**Verdict**: CACHE (invalidation fix). The fix is not "add a cache layer" but "fix the existing invalidation path." The cache is already in place; the invalidation path is incomplete.

---

### F-2: Derived Timeline Cache — No Upstream Invalidation

| Alternative | Feasibility | Expected Impact | Effort |
|-------------|-------------|-----------------|--------|
| Reduce TTL to 60s | MED | Reduces max staleness but increases computation frequency (2-4s per compute on cache miss). At 60s TTL under active request load, this could compute 60+ times per hour per project. | Low |
| On-demand compute, no cache | LOW | At 2–4s per compute for 3,800 entities, every request would take 2–4s. The cache's purpose is precisely to amortize this cost. | N/A |
| Story-level invalidation trigger | HIGH | When stories change, invalidate the derived cache entry. Pattern already exists in `MutationInvalidator._handle_section_mutation()`. Adding `DERIVED_TIMELINE` invalidation is a localized extension. | ~2 hours |
| Accept 300s staleness | HIGH | If the business use case is reporting/analytics (see U-2), 300s is acceptable. This is the cheapest resolution. | 0 |

**Verdict**: CACHE (existing cache is correct). The 300s TTL is a defensible trade-off for an analytical endpoint. Story-level invalidation can be added if the business owner requires sub-5-minute freshness, but is not required by the current evidence. Escalated to user for confirmation.

---

### F-3: Unlimited LKG Staleness

| Alternative | Feasibility | Expected Impact | Effort |
|-------------|-------------|-----------------|--------|
| Set LKG_MAX_STALENESS_MULTIPLIER to non-zero | HIGH | Bounds maximum staleness at N * entity_TTL. Requires calibration from operational data. | Config change only (~1 hour research + change) |
| Alerting on CIRCUIT_FALLBACK state | HIGH | Does not reduce staleness but makes the condition observable so operators can respond. Complementary, not alternative. | Low-medium |
| Accept unlimited LKG | HIGH | If SWR failures are rare and transient (U-5), the risk is low-probability and the availability benefit is high. | 0 |

**Verdict**: DEFER (needs operational data). The calibration of an LKG bound requires knowing actual SWR failure duration distributions. Without U-5 (production metrics), any non-zero value is a guess. This is a strategic investment, not a quick win.

---

### F-4: `clear_all_tasks()` Blast Radius Undocumented

| Alternative | Feasibility | Expected Impact | Effort |
|-------------|-------------|-----------------|--------|
| Documentation only | HIGH | Eliminates cognitive risk. No code change needed. | 30 min |
| Rename method | MEDIUM | `clear_entity_cache()` better describes behavior. Requires updating call sites. | ~1 hour |
| Split into targeted operations | LOW | Would require multiple SCAN operations. Adds complexity for marginal operational benefit. | N/A |

**Verdict**: OPTIMIZE-INSTEAD (documentation). The behavior is correct; the name is misleading. This is a hygiene concern, not a caching architecture concern.

---

### F-5: ApiSettings lru_cache Not in Test Reset

| Alternative | Feasibility | Expected Impact | Effort |
|-------------|-------------|-----------------|--------|
| Add to SystemContext.reset_all() | HIGH | Eliminates any test pollution risk. One-liner. | ~1 hour including verification |
| Add autouse fixture in conftest | HIGH | Targeted fix without touching SystemContext. | ~30 min |
| Accept as-is | HIGH | In production, containers restart on config changes — this is benign. In tests, pollution only occurs if tests modify ASANA_* env vars between cases without teardown. Verify before acting. | 0 |

**Verdict**: OPTIMIZE-INSTEAD (test hygiene). No cache architecture change needed. This is a test isolation concern.

---

## 6-Gate Framework

Applied to each finding. Gates: Frequency (Freq), Computation Cost (Cost), Staleness Tolerance (Stale), UX Impact (UX), Safety (Safety), Scalability (Scale).

### F-1: SaveSession DataFrameCache Gap

This finding is about a MISSING invalidation in an existing cache, not about adding a new cache layer. The 6-gate framework is applied to confirm the existing cache warrants the fix (not to evaluate whether to add a cache layer).

| Gate | Evaluation | Pass/Fail |
|------|-----------|-----------|
| **Frequency** | SaveSession runs on every automation cycle. At 10–100 commits/hr during active pipeline runs, stale DataFrames affect a meaningful fraction of API responses after each batch. | PASS |
| **Computation Cost** | Building a DataFrame from Asana API takes 2-4s per entity type per project. The cache exists precisely to avoid this. Serving stale data from a warm cache is not the problem — the problem is that stale data is served at all after a structural mutation. | PASS |
| **Staleness Tolerance** | Zero tolerance for structural mutations (CREATE/DELETE). An offer that is deleted must not appear in count responses. An offer that is created must appear. Business decisions are made from these counts (MRR, pipeline analysis). | FAIL → CACHE required |
| **UX Impact** | API consumers (internal analytics, metrics CLI, query engine) receive incorrect entity counts and listings. For MRR computation, an off-by-N entity count directly produces incorrect dollar figures. | PASS (significant impact) |
| **Safety** | DataFrameCache entries contain business data (offer/contact/unit rows). Not PII in cache keys. No multi-tenant isolation concern. | PASS |
| **Scalability** | Fix is localized to `CacheInvalidator._invalidate_dataframe_caches()`. No cardinality growth concern — project count is bounded (~5-10 active projects). | PASS |

**6-Gate Result**: 5 PASS, 1 FAIL (Staleness gate fails in the direction of requiring the fix). The existing cache is justified; the invalidation gap is a defect.

**Verdict**: CACHE (fix the invalidation path)

**Rationale**: The DataFrameCache is the correct solution for this access pattern (expensive to rebuild, frequently read). The staleness gap created by `CacheInvalidator` not calling `DataFrameCache.invalidate_project()` is a concrete correctness defect for structural mutations. The fix is to add `dataframe_cache` injection to `CacheInvalidator` and mirror the invalidation call that `MutationInvalidator._invalidate_project_dataframes()` already performs.

---

### F-2: Derived Timeline Cache — No Upstream Invalidation

| Gate | Evaluation | Pass/Fail |
|------|-----------|-----------|
| **Frequency** | Section-timelines is an on-demand analytical endpoint. Frequency is unknown without production metrics (U-5), but the 2–4s computation cost for 3,800 entities means caching is necessary for any non-trivial request rate. | PASS (caching is justified) |
| **Computation Cost** | HIGH. 2–4s to compute timelines for 3,800 entities from cached stories. Without caching, each request would be visibly slow. The 300s TTL is the correct mechanism to amortize this cost. | PASS |
| **Staleness Tolerance** | For the reporting use case (historical date ranges, periodic queries), 300s staleness is acceptable. Task section changes propagate through stories, which have their own cache refresh cycle. The timeline cache sits atop the story cache, adding at most 300s additional lag. | PASS (with caveat — business owner confirmation recommended) |
| **UX Impact** | Warm path: <2s (from cached derived entry). Cold path: 2–4s (rebuild from story cache). Users of an analytical endpoint expect some latency; 300s staleness for historical reporting is unlikely to be user-visible. | PASS |
| **Safety** | Timeline data: offer GID, section name, classification, date intervals. No PII. Not a financial transaction record. | PASS |
| **Scalability** | Cache key is `timeline:{project_gid}:{classifier_name}` — bounded key space (1 project * 1–2 classifiers = 2 keys). No cardinality growth concern. | PASS |

**6-Gate Result**: 6 PASS. The existing cache design (300s TTL, no upstream invalidation) passes all gates for the analytical reporting use case.

**Verdict**: CACHE (existing design is correct; story-level invalidation is optional enhancement)

**Rationale**: The 300s TTL is a deliberate, documented trade-off. For an analytical endpoint with historical date ranges, 5-minute staleness is within acceptable bounds. The "no upstream invalidation" is not a gap — it is the intended design for a compute-heavy derived cache where TTL-based expiry is sufficient. If the business owner requires sub-5-minute freshness, adding story-change invalidation to `MutationInvalidator._handle_section_mutation()` is the mechanism (existing invalidation infrastructure supports it); document this as a potential enhancement, not a defect.

**Escalation**: Recommend confirming with the product owner that 5-minute staleness is acceptable. If confirmed, close F-2 as accepted trade-off.

---

### F-3: Unlimited LKG Staleness

| Gate | Evaluation | Pass/Fail |
|------|-----------|-----------|
| **Frequency** | LKG path only activates when SWR refresh fails 3+ times per project (circuit breaker opens). Frequency is unknown without production metrics (U-5). If SWR failures are rare, this path activates infrequently. | DEFER (frequency unknown) |
| **Computation Cost** | N/A. LKG serves from MemoryTier at zero origin cost. The concern is not performance but correctness over time. | PASS |
| **Staleness Tolerance** | With `LKG_MAX_STALENESS_MULTIPLIER = 0.0`, staleness is unbounded. For process entities (TTL 60s), a 24-hour Asana API outage could serve data 24+ hours old. For offer entities (TTL 180s), same. Whether this is harmful depends on the business use case and outage history. | RISK (cannot pass without operational data) |
| **UX Impact** | When the circuit is open and LKG serves, users see data from before the outage. The system logs a warning (`CIRCUIT_FALLBACK` state) but does not surface this to API consumers. The API response appears normal but contains stale data. No visible degradation signal. | RISK |
| **Safety** | Same as general DataFrameCache — not PII in cache structure. The safety concern is data correctness (stale business decisions), not data security. | PASS |
| **Scalability** | Irrelevant to this finding. | PASS |

**6-Gate Result**: Staleness gate is an acknowledged risk. The gate does not auto-fail — it requires explicit risk acknowledgment per the framework (Gate 3: "A candidate that fails gates 3 or 5 requires explicit risk acknowledgment, not automatic rejection").

**Verdict**: DEFER (needs operational data — U-5)

**Rationale**: The LKG staleness bound cannot be calibrated without knowing actual SWR failure durations and frequencies (U-5). Setting `LKG_MAX_STALENESS_MULTIPLIER` to an arbitrary value (e.g., 10.0) without operational data could either: (a) bound staleness too aggressively, causing unnecessary cache misses during extended outages, or (b) bound too loosely, providing no meaningful protection. This decision requires CloudWatch data on `CIRCUIT_FALLBACK` event frequency and duration. Until that data is available, the current `0.0` (unlimited) remains the correct conservative availability choice.

**Risk acknowledgment**: The unlimited LKG staleness is a deliberate availability-first trade-off. It is acceptable as-is if SWR failures are rare and short. It becomes problematic during extended Asana API outages. The risk is acknowledged and deferred to when operational data is available.

---

### F-4: `clear_all_tasks()` Blast Radius Undocumented

| Gate | Evaluation | Pass/Fail |
|------|-----------|-----------|
| **Frequency** | Lambda cache invalidation is a rare, manual operational action. Does not justify a caching architecture change. | FAIL (no cache action warranted) |
| **Computation Cost** | Not a performance concern. The issue is documentation of operational consequences. | N/A |
| **Staleness Tolerance** | N/A — the behavior is correct, the naming is misleading. | N/A |
| **UX Impact** | Risk is operational: a developer running `clear_tasks` mode may not realize it destroys story incremental cursors, requiring full story re-fetches. No user-visible impact from correct operation. | N/A |
| **Safety** | N/A | N/A |
| **Scalability** | N/A | N/A |

**Verdict**: OPTIMIZE-INSTEAD (documentation only)

**Rationale**: No caching change is needed. The behavior of `clear_all_tasks()` is correct for its intended purpose. The naming (`clear_all_tasks` vs. the actual scope of all entity types) is a documentation/hygiene concern. The remedy is a docstring update to `lambda_handlers/cache_invalidate.py` documenting the blast radius: clears TASK, STORIES, DETECTION, SECTION, USER, DERIVED_TIMELINE, and PROJECT_SECTIONS entries under `asana:tasks:*`. Story incremental cursors are destroyed; next Lambda warm cycle will perform full story fetches instead of incremental (`since` cursor) fetches.

**Cross-rite referral**: hygiene — renaming or docstring addition in `cache/backends/redis.py` `clear_all_tasks()` and `lambda_handlers/cache_invalidate.py`.

---

### F-5: ApiSettings lru_cache Not in Test Reset

| Gate | Evaluation | Pass/Fail |
|------|-----------|-----------|
| **Frequency** | `get_settings()` is called per-process. In production, once. In tests, potentially many times across test cases. | N/A (not a user-facing frequency concern) |
| **Computation Cost** | `ApiSettings` construction is fast (env var reads). The `@lru_cache` is not a performance optimization for a hot path — it is a singleton pattern. | FAIL (negligible computation cost justification) |
| **Staleness Tolerance** | In production: irrelevant (containers restart on config change). In tests: staleness between test cases that modify env vars is the actual concern. | RISK (test isolation only) |
| **UX Impact** | No user-facing impact. Test-isolation concern only. | N/A |
| **Safety** | `ApiSettings` may contain API base URLs and feature flags. Not PII. Not a security concern in test context. | PASS |
| **Scalability** | N/A | N/A |

**Verdict**: OPTIMIZE-INSTEAD (test hygiene)

**Rationale**: The `@lru_cache` on `get_settings()` is a process-lifetime singleton pattern, which is correct for production (ECS containers restart on config change). The only risk is test pollution when tests modify ASANA_* env vars without resetting the cache. The remedy is to verify whether any test currently does this, then either: (a) add `get_settings.cache_clear` to `SystemContext.reset_all()` registration, or (b) add an autouse fixture in the relevant `conftest.py`. No caching architecture change is needed.

**Cross-rite referral**: hygiene — test infrastructure fix in `api/config.py` or `conftest.py`.

---

## 6-Gate Summary

| Candidate | Freq | Cost | Stale | UX | Safety | Scale | Verdict |
|-----------|------|------|-------|-----|--------|-------|---------|
| F-1: SaveSession DataFrameCache gap | P | P | FAIL→FIX | P | P | P | CACHE (fix invalidation) |
| F-2: Derived timeline 300s TTL | P | P | P* | P | P | P | CACHE (existing design correct) |
| F-3: Unlimited LKG staleness | DEFER | P | RISK | RISK | P | P | DEFER (needs U-5) |
| F-4: `clear_all_tasks()` naming | F | N/A | N/A | N/A | N/A | N/A | OPTIMIZE-INSTEAD (docs) |
| F-5: ApiSettings lru_cache | F | F | RISK | N/A | P | N/A | OPTIMIZE-INSTEAD (test hygiene) |

*F-2 Staleness gate passes conditionally — recommended escalation to business owner for confirmation.

---

## Anti-Pattern Audit (Existing Caches)

The spike artifacts (ASSESSMENT-CACHE.md) provide the complete anti-pattern catalog. This section summarizes severity and open status for the 5 targeted findings.

### AP-1: SaveSession / MutationInvalidator Invalidation Asymmetry (F-1)
- **Location**: `persistence/cache_invalidator.py` lines 160-195 vs. `cache/integration/mutation_invalidator.py` lines 347-363
- **Risk**: Stale DataFrames after SaveSession structural mutations. Up to 9 min (offer) to 45 min (contact) of incorrect API responses.
- **Severity**: HIGH
- **Status**: Active defect. Remediation path clear (see F-1 verdict).

### AP-2: Derived Timeline Fixed TTL (F-2)
- **Location**: `cache/integration/derived.py` line 32 (`_DERIVED_TIMELINE_TTL = 300`)
- **Risk**: Up to 5 min staleness for section-timeline API. Acceptable for analytical use case.
- **Severity**: MEDIUM (likely accepted trade-off)
- **Status**: Accepted trade-off pending business owner confirmation. No immediate action.

### AP-3: Unlimited LKG (F-3)
- **Location**: `config.py` line 102 (`LKG_MAX_STALENESS_MULTIPLIER: float = 0.0`)
- **Risk**: Unbounded staleness during extended outage if SWR consistently fails.
- **Severity**: MEDIUM (low probability, severity depends on outage duration)
- **Status**: Deferred — needs U-5 (production metrics on SWR failure rates).

### AP-5: `lru_cache` Without Test Invalidation (F-5)
- **Location**: `api/config.py` lines 90-97
- **Risk**: Test pollution in env-var-modifying tests.
- **Severity**: LOW
- **Status**: Verify then act. Hygiene fix, not architecture change.

### AP-6: `clear_all_tasks()` Misleading Name (F-4)
- **Location**: `cache/backends/redis.py` line 751
- **Risk**: Operator cognitive error — blast radius is wider than name implies (clears stories, timelines, detections, not just tasks).
- **Severity**: LOW (informational)
- **Status**: Documentation-only fix.

---

## Recommended Cache Layers

Only F-1 and F-2 carry CACHE verdicts. These are both about the existing cache architecture, not new layers.

### CACHE-1: DataFrameCache — Invalidation Completeness Fix (F-1)

**What**: Add project-level `DataFrameCache.invalidate_project(project_gid)` calls to `CacheInvalidator._invalidate_dataframe_caches()` for structural mutations (CREATE/DELETE/MOVE — mirror the guard that exists in `MutationInvalidator._handle_task_mutation()`).

**Current state**: `CacheInvalidator` only calls `invalidate_task_dataframes()` (per-task System A DataFrame entries). It never calls `DataFrameCache.invalidate_project()` (project-level System B DataFrame cache).

**Required change**: `CacheInvalidator` needs a `dataframe_cache: DataFrameCache | None` constructor parameter (same pattern as `MutationInvalidator`). The `_invalidate_dataframe_caches()` method should call `self._dataframe_cache.invalidate_project(project_gid)` for each project GID after identifying structural mutations.

**Reference implementation**: `mutation_invalidator.py` lines 347-363, `_invalidate_project_dataframes()`.

**Key files**:
- `src/autom8_asana/persistence/cache_invalidator.py` — add parameter + call
- `src/autom8_asana/cache/integration/mutation_invalidator.py` — reference implementation
- `src/autom8_asana/cache/dataframe/factory.py` — `get_dataframe_cache()` import

---

### CACHE-2: Derived Timeline Cache — Accepted Design (F-2)

**What**: The 300s TTL with no upstream invalidation is the correct design for the analytical reporting use case. No change recommended unless the business owner requires sub-5-minute freshness.

**Optional enhancement** (if business owner requires it): Add `DERIVED_TIMELINE` invalidation to `MutationInvalidator._handle_section_mutation()`. Call `cache.invalidate(make_derived_timeline_key(project_gid, "offer"), EntryType.DERIVED_TIMELINE)` when section changes occur. Infrastructure is already in place.

---

## Deferred Decisions

| ID | Decision | Blocked On | Owner |
|----|---------|------------|-------|
| D-1 | F-3: Should `LKG_MAX_STALENESS_MULTIPLIER` be set to a non-zero value? | U-5: Production metrics on SWR failure rates and durations (CloudWatch: `FreshnessState.CIRCUIT_FALLBACK` events, Lambda warmer build failure logs) | SRE/Operations |
| D-2 | F-2: Is 300s timeline staleness acceptable to business consumers? | Business owner confirmation for section-timelines API | Product owner |
| D-3 | R-4 (from spike): Cross-entity DataFrame coherence | CLOSED — cascade columns are resolved at Asana extraction time, not from cross-entity DataFrame joins. No cross-entity invalidation needed. | CLOSED |

---

## Recommended Specialist Routing

### To systems-thermodynamicist

**CACHE-1** (F-1 — DataFrameCache invalidation gap): This is a correctness defect in the invalidation path. The systems-thermodynamicist should design the exact change to `CacheInvalidator` — specifically:
- Whether `dataframe_cache` injection should be optional (defaulting to `None`, matching `MutationInvalidator`'s pattern) or required
- Whether the structural mutation guard from `MutationInvalidator` (only invalidate on CREATE/DELETE/MOVE/ADD_MEMBER/REMOVE_MEMBER, not pure field updates) should be replicated in `CacheInvalidator`, and how to detect structural mutations from `SaveResult` vs. `MutationEvent`
- Consistency model: should `CacheInvalidator` use sync `invalidate_project()` or schedule an async task? (Note: `CacheInvalidator._invalidate_dataframe_caches()` is currently sync; `MutationInvalidator._invalidate_project_dataframes()` is async. `DataFrameCache.invalidate_project()` appears to be sync based on `mutation_invalidator.py` line 358.)

**CACHE-2** (F-2 — if business owner confirms sub-5-minute freshness needed): Story-level timeline cache invalidation design. The systems-thermodynamicist should evaluate whether to invalidate on story creation events, section mutation events, or both, and what the key resolution looks like for classifier-name enumeration at invalidation time.

---

## Handoff Checklist

- [x] `thermal-assessment.md` produced at `.claude/wip/SPIKE-CACHE-ARCH/THERMAL-ASSESSMENT.md`
- [x] Every hot path has alternatives assessment documented
- [x] 6-gate framework applied to all 5 findings with per-gate reasoning
- [x] Each finding has a verdict: CACHE (F-1, F-2), OPTIMIZE-INSTEAD (F-4, F-5), DEFER (F-3)
- [x] At least one CACHE verdict exists (F-1 and F-2)
- [x] Anti-pattern audit completed (existing caching is present; AP-1 through AP-6 reviewed)
- [x] Deferred decisions section lists open questions (D-1: U-5 production metrics, D-2: business owner confirmation, D-3: closed)
- [x] Unknown resolution results documented for U-1 through U-4, U-6 (U-5 skipped per instruction)
