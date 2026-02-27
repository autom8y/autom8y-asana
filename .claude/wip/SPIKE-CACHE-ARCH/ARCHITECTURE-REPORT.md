# Architecture Report: Cache Subsystem

**Project**: autom8y-asana (`/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/`)
**Date**: 2026-02-27
**Scope**: Spike assessment -- caching architecture health, actionable findings, and prioritized recommendations
**Input Artifacts**: TOPOLOGY-CACHE.md, DEPENDENCY-CACHE.md, ASSESSMENT-CACHE.md

---

## 1. Executive Summary

The autom8y-asana cache subsystem is a deliberately engineered, availability-first system spanning 26 cataloged cache locations across two independent tiered systems: System A (entity cache: Redis hot + S3 cold, serving task/story/detection data) and System B (DataFrame cache: in-process OrderedDict hot + S3 Parquet cold, serving Polars analytical views). The design philosophy -- LKG (last-known-good) over errors, SWR (stale-while-revalidate) over synchronous blocking, fire-and-forget invalidation -- is consistently applied and appropriate for the workload. The architecture is sound. However, the philosophy breaks down at the boundary between the batch write path (SaveSession) and the DataFrame cache: when the automation pipeline creates or deletes tasks via SaveSession, it invalidates entity cache entries (System A) but never signals the project-level DataFrame cache (System B). Callers receive stale row counts and entity listings for up to 540 seconds (offers) or 2,700 seconds (contacts) after a batch commit. This is the most concrete, correctable defect in the system and has a localized, low-effort fix. The remaining findings are accepted trade-offs, documented design choices (ADR-0067, ADR-BC-002), or structural risks requiring business input before action.

---

## 2. Ranked Findings

Ranked by leverage (impact / effort). Confidence ratings propagated from upstream artifacts.

---

### F-1: SaveSession Does Not Invalidate Project-Level DataFrameCache After Structural Mutations

**Severity**: HIGH
**Confidence**: HIGH (corroborated across all three upstream artifacts)
**Leverage**: HIGH

**Impact**: When SaveSession commits a structural change (task CREATE, DELETE, or MOVE), `CacheInvalidator._invalidate_dataframe_caches()` invalidates per-task DataFrame entries in System A but never calls `DataFrameCache.invalidate_project()` on System B. The project-level DataFrame in MemoryTier continues to serve the pre-mutation state. For offer data (TTL 180s, SWR grace 3x = 540s total), stale data persists for up to 9 minutes. For contacts (TTL 900s, SWR grace 3x = 2,700s), stale data persists for up to 45 minutes. Row counts, aggregations, and entity listings returned by the API will be wrong during this window.

**Effort**: S -- The pattern already exists in `MutationInvalidator._handle_task_mutation()` (line 174-181). The fix is to call `DataFrameCache.invalidate_project(project_gid)` from `CacheInvalidator._invalidate_dataframe_caches()` for each affected project. No design decisions required; the invalidation interface already exists.

**Recommendation**: In `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py`, extend `_invalidate_dataframe_caches()` to call `DataFrameCache.invalidate_project(project_gid)` for each project GID associated with the committed entities. Import `get_dataframe_cache` from `cache/dataframe/factory.py` (already used elsewhere). Mirror the structural-mutation guard that exists in `MutationInvalidator` if the intent is to only invalidate on CREATE/DELETE/MOVE (not pure field updates). Confirm intent with the SaveSession author first -- see Unknown U-1.

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py` (lines 50-95, `_invalidate_dataframe_caches`)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py` (lines 174-181, reference implementation)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/dataframe/factory.py` (`get_dataframe_cache`, `DataFrameCache.invalidate_project`)

---

### F-2: Derived Timeline Cache Has No Upstream-Triggered Invalidation

**Severity**: MEDIUM
**Confidence**: HIGH (corroborated across dependency map and assessment)
**Leverage**: MEDIUM

**Impact**: The section-timelines API returns pre-computed `SectionTimeline` data cached with a fixed 300s TTL. When tasks change sections (stories), no invalidation signal propagates to the derived timeline cache. MutationInvalidator does not reference `EntryType.DERIVED_TIMELINE` at all. The maximum staleness is 300s -- all callers receive data that is up to 5 minutes behind actual task state. For operational dashboards used in real-time decision-making, this is a meaningful gap. For daily/weekly reporting, it is negligible (see Unknown U-2 before acting).

**Effort**: S -- `MutationInvalidator` already handles section mutations (lines 204-225). Adding derived timeline invalidation on section mutation is a localized addition: call `get_cached_timelines()` invalidation or simply delete the cache key for the affected `project_gid`. The `make_derived_timeline_key()` helper is already exported from `cache/integration/derived.py`.

**Recommendation**: Confirm staleness acceptability with the product owner (U-2). If near-real-time freshness is required: add a `_invalidate_derived_timelines(project_gid)` step to `MutationInvalidator._handle_section_mutation()`, calling `cache.invalidate(make_derived_timeline_key(project_gid, classifier_name), EntryType.DERIVED_TIMELINE)` for each active classifier. If 300s is acceptable, mark this as an accepted trade-off and close it.

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` (line 32, `_DERIVED_TIMELINE_TTL = 300`)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py` (lines 200-225, section mutation handler)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` (`make_derived_timeline_key`, `store_derived_timelines`)

---

### F-3: Unlimited LKG Staleness During Extended Outage

**Severity**: MEDIUM
**Confidence**: HIGH
**Leverage**: LOW (low likelihood, medium calibration effort)

**Impact**: `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (unlimited) in `config.py` means the system will serve any schema-valid DataFrame entry indefinitely if SWR consistently fails. If Asana API is down for hours and SWR refresh fails 3+ times per project (opening the circuit breaker), the system serves data from before the outage with no bound. For process entities (TTL 60s), this could mean serving data that is days old after a multi-hour outage.

**Effort**: M -- Setting `LKG_MAX_STALENESS_MULTIPLIER` to a non-zero value (e.g., `10.0` to allow 10x TTL staleness before rejecting) requires choosing a value based on operational data: how long do outages typically last, and at what staleness point does data become harmful rather than helpful? This requires operational input before implementation.

**Recommendation**: Review incident history for cache-build failure durations. If extended outages (> 30 minutes) have occurred, set `LKG_MAX_STALENESS_MULTIPLIER` to a value that bounds staleness at a business-acceptable level (e.g., `20.0` for offer data = 60 minutes maximum). Coordinate with the SRE/operations team to understand actual outage patterns before choosing a value. This is a configuration-only change once the value is agreed.

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/config.py` (line 100-102, `LKG_MAX_STALENESS_MULTIPLIER`)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframe_cache.py` (lines 444-465, `_check_freshness_and_serve`)

---

### F-4: `clear_all_tasks()` Naming Misleads -- Destroys Incremental Story Cursors

**Severity**: LOW (informational)
**Confidence**: HIGH
**Leverage**: LOW

**Impact**: The Lambda invalidation mode `clear_tasks` calls `TieredCacheProvider.clear_all_tasks()`, which SCAN-deletes ALL keys under `asana:tasks:*`. Per the key scheme in `_make_key()`, this prefix covers not just TASK entries but also STORIES, DETECTION, SECTION, USER, and DERIVED_TIMELINE entries. After a Lambda `clear_tasks` operation, all incremental story fetch cursors (the `since` parameter optimization from ADR-0020) are destroyed, forcing full story fetches on next access. This is a known consequence, not a bug, but the naming obscures the blast radius from operators.

**Effort**: S -- Document the blast radius in the Lambda handler's docstring and the operational runbook. No code change required unless renaming is desired.

**Recommendation**: Add a comment to `lambda_handlers/cache_invalidate.py` (the `clear_tasks` handler block) documenting that this operation also clears story, detection, timeline, and section entries, and that story incremental cursors will be lost. No code change required; this is documentation only.

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_invalidate.py` (lines 115-150)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/redis.py` (line 751, SCAN pattern; line 250, `_make_key` showing key structure)

---

### F-5: `ApiSettings` lru_cache Not Registered for Test Reset

**Severity**: LOW
**Confidence**: MEDIUM (grep-only; test pollution not confirmed)
**Leverage**: LOW

**Impact**: `get_settings()` in `api/config.py` uses an unbounded `@lru_cache` with no `cache_clear()` call and is not registered with `SystemContext.reset_all()`. In production (ECS), this is benign -- containers restart on config changes. In tests that modify environment variables between test cases, the cached `ApiSettings` could persist and cause test pollution. The risk is limited since `ApiSettings` is not a cache location but a configuration object.

**Effort**: S -- Register `get_settings.cache_clear()` with `SystemContext.reset_all()` or add a test-teardown fixture that clears it.

**Recommendation**: Before acting, verify whether any test currently modifies environment variables that affect `ApiSettings` without calling `cache_clear()`. If test pollution is confirmed, add `get_settings.cache_clear` to `SystemContext.reset_all()` registration in `settings.py` or add a `conftest.py` autouse fixture. If no pollution observed, accept as-is for production; note in test documentation that env-var-modifying tests should call `get_settings.cache_clear()`.

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/config.py` (lines 90-97)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/watermark.py` (reference: how singletons register with SystemContext)

---

## 3. Quick Wins

Items that are actionable in less than one day, require no architectural decisions, and have clear value.

**QW-1: Fix SaveSession DataFrameCache gap (F-1)** -- after confirming intent (U-1), the code change is adding ~5 lines to `persistence/cache_invalidator.py`. Reference implementation exists in `mutation_invalidator.py`. Estimated: 2-3 hours including tests.

**QW-2: Document `clear_all_tasks()` blast radius (F-4)** -- add a comment block to the Lambda handler and update the operational runbook. No code review required beyond a quick read. Estimated: 30 minutes.

**QW-3: Verify ApiSettings test isolation (F-5)** -- grep for test files that set `ASANA_*` env vars and check if `get_settings.cache_clear()` is called. If pollution is found, adding `SystemContext` registration is a one-liner. Estimated: 1 hour including investigation.

---

## 4. Deferred / Accepted Risks

### 4.1 Intentional Design Choices (do not remediate)

**ADR-0067: 12/14 Cache Dimension Divergence** -- System A and System B are deliberately different across 12 of 14 measured dimensions (freshness model, key scheme, data format, tier composition, invalidation mechanism, etc.). This is documented and intentional. No remediation required.

**LKG Philosophy (Unlimited Staleness, AP-3)** -- Serving stale data indefinitely rather than returning errors is an explicit availability trade-off. The `LKG_MAX_STALENESS_MULTIPLIER = 0.0` value is documented with intent. The risk (F-3) is real but low-probability. Address only if incident history shows harm.

**Fire-and-forget MutationInvalidator** -- Invalidation failures never block mutation responses. This is an explicit availability choice. If invalidation fails silently, the cache will serve stale data until TTL expires. The `_log_task_exception` callback ensures failures are observable. Accept as-is.

**ADR-BC-002: Dual Coalescing Systems (AP-4)** -- `DataFrameCacheCoalescer` and `BuildCoordinator` coexist during an incremental migration. Both are functional and serve the same thundering-herd purpose. No operational risk, only cognitive complexity. Defer migration completion to when the `@dataframe_cache` decorator path is the established standard path.

### 4.2 Real Risks, Not Worth Addressing Now

**R-4: Cross-Entity DataFrame Coherence** -- When an Offer changes, related BusinessEntity or Contact DataFrames are not signaled. This could serve incoherent views if entity types share derived columns. The fix requires cross-entity dependency metadata and new invalidation graph traversal. Trigger: confirm whether cross-entity data dependencies exist at the schema level (U-4). If they do not exist (each entity type's DataFrame is truly independent), close R-4 entirely.

**SPOF-4: Schema Version Mismatch on Deploy** -- A new schema version causes all MemoryTier entries to fail validation simultaneously, leading to a cold-start flood to S3. The `max_concurrent_builds=4` semaphore and per-key coalescer limit the impact. For the current entity count, this is manageable. Address only if entity count grows significantly or if a production deploy incident occurs.

**R-9: Redis failure degrades Insights cache** -- When Redis is down, `TieredCacheProvider` simple `get()`/`set()` (used by the Insights cache in `clients/data/_cache.py`) have no cold tier fallback. `get_stale_response()` provides application-level graceful degradation. Accept as-is.

---

## 5. Unknowns Registry

Consolidated from all three input artifacts, organized by impact on remediation decisions.

---

### Unknown U-1: Was the SaveSession DataFrameCache gap intentional or an oversight?

**Question**: Was the omission of `DataFrameCache.invalidate_project()` from `CacheInvalidator` (SaveSession path) an intentional design decision accepting eventual consistency for the automation pipeline, or an oversight that was never backported after MutationInvalidator gained this capability?
**Why it matters**: If intentional, F-1 should be accepted as a deliberate trade-off (automation pipeline is not latency-sensitive). If an oversight, F-1 is a concrete staleness bug that should be fixed before the next batch operation in production.
**Evidence**: `CacheInvalidator` was extracted per ADR-0059 before `MutationInvalidator` added DataFrameCache invalidation. No ADR or TDD document discusses this asymmetry as a design choice.
**Suggested source**: Author of ADR-0059 or the `MutationInvalidator` DataFrameCache addition. Git blame on `mutation_invalidator.py` lines 174-181 will identify the PR.

---

### Unknown U-2: Is 300s timeline staleness acceptable to section-timeline consumers?

**Question**: Do the consumers of the section-timelines API expect near-real-time freshness (< 60s), or is 5-minute eventual consistency acceptable for their reporting use cases?
**Why it matters**: Determines whether F-2 is a concrete problem requiring active invalidation or an accepted trade-off that can be closed.
**Evidence**: The 300s TTL is documented with a computation-cost rationale but no consumer SLA is referenced in the code or ADRs.
**Suggested source**: Product owner or the team consuming section-timelines API. The API is used by SectionTimeline-driven features shipped 2026-02-19.

---

### Unknown U-3: What are the actual runtime TTL values from EntityRegistry?

**Question**: The `DEFAULT_ENTITY_TTLS` dict is dynamically built from `EntityRegistry.all_descriptors()` at import time. The values documented in the `CacheConfig` docstring (business=3600, contact=900, offer=180, etc.) may be stale relative to the actual registry. What are the runtime values?
**Why it matters**: Affects staleness window calculations for F-1 (how long stale DataFrames are served) and F-3 (what a non-zero LKG multiplier should be set to).
**Evidence**: `config.py` line 108-112 builds `DEFAULT_ENTITY_TTLS` dynamically from registry. Docstring values documented in TOPOLOGY-CACHE.md section 6 may not match runtime values.
**Suggested source**: Read `core/entity_registry.py` EntityDescriptor definitions, or add a startup log line printing the resolved TTL dict.

---

### Unknown U-4: Do cross-entity DataFrames share derived columns that create read-time coherence dependencies?

**Question**: When an Offer's data changes, do the BusinessEntity or Contact DataFrames contain any columns derived from Offer data (or vice versa)? If so, are there business scenarios where incoherence across entity DataFrames would produce incorrect analytics?
**Why it matters**: If entity DataFrames are truly independent (no cross-entity derived columns), R-4 (cross-entity coherence gap) can be closed as a non-issue. If cross-entity derivation exists, R-4 is a real data correctness risk.
**Evidence**: Each entity type is cached independently by `{entity_type}:{project_gid}`. The dependency map confirms that "Freshness propagation is NOT automatic" between entity types but does not document whether schema-level cross-entity dependencies exist.
**Suggested source**: Entity schema definitions in `dataframes/models/registry.py` and resolution strategy implementations in `dataframes/resolver/`.

---

### Unknown U-5: What is the observed failure rate of SWR background refreshes in production?

**Question**: How often do SWR refreshes fail in production, and do failures cluster (causing per-project circuit breakers to open)? Are there any entities currently serving LKG data indefinitely?
**Why it matters**: Determines the actual exposure of F-3 (unlimited LKG staleness). If SWR failures are rare and transient, F-3 is low-risk. If failures cluster (e.g., during Asana API rate limit events), F-3 could be causing undetected stale data windows.
**Evidence**: `SPOF-3` in ASSESSMENT-CACHE.md: SWR callback depends on 8+ components, any failure -> circuit breaker -> LKG. The `FreshnessState.CIRCUIT_FALLBACK` state exists for observability but it is unknown whether it is being monitored in CloudWatch.
**Suggested source**: CloudWatch metrics for `FreshnessState.CIRCUIT_FALLBACK` events. Lambda warmer logs for build failures per entity type.

---

### Unknown U-6: What does the `connection_manager` parameter in RedisCacheProvider do?

**Question**: The `connection_manager` parameter in `RedisCacheProvider.__init__()` was noted as "forward scaffolding" in COMPAT-PURGE. Is it active? Is it wired to anything?
**Why it matters**: Low impact on current assessment. If it is dead code, it should be removed in a future hygiene pass. If it is live, it affects understanding of Redis connection pooling.
**Evidence**: `cache/backends/redis.py` accepts optional `connection_manager` parameter. Referenced in COMPAT-PURGE as "intentional forward scaffolding."
**Suggested source**: Read `RedisCacheProvider.__init__` in `cache/backends/redis.py`.

---

## 6. Cross-Rite Referrals

### Cross-Rite Referral: CRR-1
- **Target Rite**: hygiene
- **Concern**: `clear_all_tasks()` method name does not match behavior (clears stories, timelines, detection entries, not just tasks). And `ApiSettings` lru_cache (F-5) has no reset registration. Both are code clarity/quality issues, not architectural risks.
- **Evidence**: `cache/backends/redis.py` line 751 (SCAN pattern `asana:tasks:*` covers all entry types); `api/config.py` lines 90-97 (unbounded `lru_cache`, no `cache_clear` or `SystemContext` registration)
- **Suggested Scope**: Rename `clear_all_tasks()` to `clear_entity_cache()` or add a docstring clarifying blast radius; add `get_settings.cache_clear` to test reset coordination if pollution is confirmed. Both are small hygiene items, not architectural changes.
- **Priority**: LOW -- no operational impact. Address opportunistically during next test or API maintenance pass.

### Cross-Rite Referral: CRR-2
- **Target Rite**: docs
- **Concern**: No operational runbook documents the blast radius of each Lambda invalidation mode (`clear_tasks`, `clear_dataframes`, `invalidate_project`). The story cursor loss consequence of `clear_tasks` is implicit in code comments but not surfaced for operators.
- **Evidence**: `lambda_handlers/cache_invalidate.py` -- three invalidation modes with different scopes. `cache/integration/stories.py` -- story cursor optimization that is silently destroyed by `clear_tasks`.
- **Suggested Scope**: One-page runbook: "Cache Invalidation Modes and Operational Consequences" documenting what each Lambda mode clears, which data is affected, and the recovery time for each mode (e.g., after `clear_tasks`, expect N minutes of story re-fetch latency).
- **Priority**: LOW -- no current incident. Useful before the next operational cache reset.

---

## 7. Scope and Limitations

This spike does NOT cover:

- **Runtime behavior**: No load testing, latency profiling, or throughput measurement was performed. TTL and SWR grace windows are analyzed from code, not from observed production cache hit rates or measured staleness distributions.
- **Data architecture**: The report identifies WHAT is cached and for how long but does not evaluate whether the cached data models are correct, normalized, or well-suited for the analytical queries that consume them.
- **Operational concerns**: CloudWatch alarm coverage for cache metrics (`FreshnessState.CIRCUIT_FALLBACK`, SWR failure rates, MemoryTier eviction rates) was not audited. No incident response playbook review was performed.
- **Organizational alignment**: The split between `CacheInvalidator` (persistence/ bounded context) and `MutationInvalidator` (cache/integration/ bounded context) reflects team ownership boundaries. Conway's Law effects on this split were not evaluated.
- **Cross-repo cache interactions**: `autom8y-data` service and its caching patterns were not analyzed. If `autom8y-data` has its own cache layer, coherence between the two services is out of scope.
- **Security**: Cache key construction using PII (phone numbers, canonical keys) is noted in `clients/data/_cache.py` (PII-masked in logs). A full PII-in-cache audit belongs in the security rite, not here.

---

## Summary Table

| ID | Finding | Severity | Leverage | Effort | Status |
|----|---------|----------|----------|--------|--------|
| F-1 | SaveSession does not invalidate project-level DataFrameCache | HIGH | HIGH | S | Recommend fix (confirm U-1 first) |
| F-2 | Derived timeline cache has no upstream invalidation | MEDIUM | MEDIUM | S | Confirm acceptability (U-2) then fix or close |
| F-3 | Unlimited LKG staleness during extended outage | MEDIUM | LOW | M | Strategic -- needs operational data |
| F-4 | `clear_all_tasks()` blast radius undocumented | LOW | LOW | S | Documentation only |
| F-5 | ApiSettings lru_cache not in test reset | LOW | LOW | S | Verify before acting |
| R-4 | Cross-entity DataFrame coherence gap | MEDIUM | LOW | XL | Deferred -- confirm U-4 first |
| AP-4 | Dual coalescing systems (migration in progress) | LOW | LOW | M | Accepted -- ADR-BC-002 in progress |
| SPOF-4 | Schema version mismatch on deploy | LOW | LOW | -- | Accepted -- mitigated by coalescer |
| R-9 | Redis failure degrades Insights cache | LOW | LOW | -- | Accepted -- app-level fallback present |
| R-5/F-4 | `clear_all_tasks()` destroys story cursors (see F-4) | LOW | LOW | S | Accepted -- consolidated into F-4 |
| R-7 | SWR callback wide dependency surface | LOW | LOW | -- | Accepted -- circuit breaker + LKG mitigate |
| SPOF-1 | DataFrameCache module-level singleton | MEDIUM | LOW | -- | Accepted -- graceful degradation present |
| SPOF-2 | Redis hot tier SPOF for entity cache | MEDIUM | LOW | -- | Accepted -- degraded mode + S3 fallback |
