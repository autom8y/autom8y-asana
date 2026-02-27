# Observability Plan: autom8y-asana Cache Subsystem (CACHE-REMEDIATION)

**Date**: 2026-02-27
**Agent**: thermal-monitor
**Session**: session-20260227-135243-55f4e4fa (CACHE-REMEDIATION)
**Upstream**: THERMAL-ASSESSMENT.md, CACHE-ARCHITECTURE.md, CAPACITY-SPECIFICATION.md, TOPOLOGY-CACHE.md, ARCHITECTURE-REPORT.md

---

## Section 1: Cross-Architecture Validation

### 1.1 Does `invalidate_project()` in `CacheInvalidator` Create Unintended Interactions With Other Cache Locations?

The CACHE-1 design adds a call to `DataFrameCache.invalidate_project(project_gid)` from `CacheInvalidator._invalidate_project_dataframes()`. The 26-location topology was reviewed for interaction risk.

**Verdict: No unintended cascade effects. The invalidation is localized and idempotent.**

Evidence per cache location:

| Location | Dependency on DataFrameCache MemoryTier? | Affected by CACHE-1? | Notes |
|----------|------------------------------------------|----------------------|-------|
| 3.1.1 EnhancedInMemoryCacheProvider | No | No | System A -- independent |
| 3.1.2 RedisCacheProvider | No | No | System A -- independent |
| 3.1.3 S3CacheProvider | No | No | System A -- independent |
| 3.1.4 TieredCacheProvider | No | No | System A composite -- independent |
| 3.1.5 UnifiedTaskStore | No | No | Wraps System A CacheProvider only |
| 3.1.8 DataFrameCache | YES -- writes to MemoryTier | DIRECTLY -- this is the target | `invalidate_project()` removes MemoryTier entries |
| 3.1.9 MemoryTier | YES -- stores DataFrameCacheEntry | DIRECTLY | Receives the `remove()` calls |
| 3.1.10 ProgressiveTier (S3) | No | No | NOT touched by `invalidate_project()`. S3 entries persist as LKG. |
| 3.1.11 DataFrameCache Singleton | YES -- manages MemoryTier | Indirectly | Singleton instance is what `CacheInvalidator` receives |
| 3.1.22 Story Cache | No | No | Separate entry type (STORIES) in System A. No dependency on DataFrameCache. |
| 3.1.23 Derived Timeline Cache | No | No | EntryType.DERIVED_TIMELINE in System A (Redis/S3 via TieredCacheProvider). Separate from System B DataFrameCache. |
| 3.1.24 Per-Task DataFrame Cache | No | No | System A (CacheProvider-backed, key: task_gid:project_gid). Separate from System B. |
| 3.1.25 ModificationCheckCache | No | No | In-process dict with 25s TTL. Completely independent. |
| 3.1.26 MutationInvalidator | No | No | Also calls `invalidate_project()` on the same DataFrameCache singleton. CACHE-1 mirrors this. |
| 3.4.1 DataFrameCacheCoalescer | Downstream | Indirectly | Post-invalidation reads may trigger coalescer wait. This is correct behavior -- coalescer prevents thundering herd. |
| 3.4.3 CircuitBreaker | Downstream | No | Circuit breaker state is per-project. Not affected by invalidation itself. |
| 3.5.1 OfflineDataFrameProvider | No | No | CLI-only in-process dict. Not a production runtime cache. |
| 3.6.1 Lambda Cache Warmer | Downstream | No | Warming reads from ProgressiveTier (S3). Invalidation of MemoryTier does not affect next warm cycle. |
| 3.6.2 Lambda Cache Invalidation | Orthogonal | No | Lambda `clear_tasks` mode clears System A (Redis/S3). Lambda `clear_dataframes` mode calls `invalidate_on_schema_change()` -- a separate code path. No overlap. |
| 3.7.1 DataServiceClient Insights Cache | No | No | Separate domain (insights responses, not entity DataFrames). |

**Critical finding confirmed**: DERIVED_TIMELINE (location 3.1.23) is in System A (TieredCacheProvider / Redis + S3), NOT in System B (DataFrameCache). Calling `DataFrameCache.invalidate_project()` does NOT touch DERIVED_TIMELINE entries. This confirms CACHE-ARCHITECTURE.md: "DERIVED_TIMELINE entries are in System A (Redis/S3 via TieredCacheProvider), not in System B (DataFrameCache). Invalidating System B does not affect derived timeline entries."

### 1.2 Are There Cache Locations That Depend on DataFrameCache State That Would Be Affected?

Reviewed all dependency edges in the topology for locations that READ FROM DataFrameCache:

- **Resolution strategies** (`dataframes/resolver/`) call `DataFrameCache.get_or_build_async()`. These are read consumers. After CACHE-1 invalidation, their next call will miss MemoryTier, hit ProgressiveTier (S3, stale), trigger SWR rebuild. This is the correct, intended behavior -- not an adverse interaction.
- **`@dataframe_cache` decorator** (`cache/dataframe/decorator.py`) wraps resolution strategies. Same read path. Same correct behavior on miss.
- **GidLookupIndex** references DataFrameCache via the legacy preload (`api/preload/legacy.py`). The preload populates GidLookupIndex from S3 DataFrames on cold start, not from MemoryTier on each request. Post-invalidation reads that hit GidLookupIndex use its own in-process state, not DataFrameCache. No adverse interaction.
- **DataFrameCacheCoalescer** (`cache/dataframe/coalescer.py`) serializes concurrent reads. After invalidation causes a miss, two concurrent readers will coalesce into a single build. This is correct behavior -- no adverse interaction.
- **CacheWarmer** (`cache/dataframe/warmer.py`) calls `warm_all_async()` which calls `get_or_build_async()`. If an invalidation fires during a warm cycle, the warmer's next `get_or_build_async()` call will trigger a fresh build. The warmer is designed for this -- it assumes potentially cold cache. No adverse interaction.

**Conclusion**: No cache location suffers an unintended adverse interaction from CACHE-1. The MemoryTier invalidation affects only direct MemoryTier readers, all of which correctly fall through to SWR rebuild or S3 LKG.

### 1.3 Does Conservative Invalidation (All Entities, Not Just Structural Mutations) Cause Cascade Effects?

The CACHE-1 design calls `invalidate_project()` for all succeeded entities in a commit batch, regardless of whether the operation is CREATE, UPDATE, or DELETE. `invalidate_project()` removes ALL entity type keys for the project from MemoryTier (offer, unit, contact, business, asset_edit -- 5 entity types per `invalidate_project()` implementation).

**Potential cascade from blanket invalidation**: A commit that updates a single custom field on one offer triggers invalidation of `{offer, unit, contact, business, asset_edit}:proj-1` from MemoryTier. All five entity types are evicted simultaneously, not just `offer:proj-1`. On the next read:
- `offer:proj-1`: SWR rebuild fires (correct -- the offer changed)
- `unit:proj-1`, `contact:proj-1`, `business:proj-1`, `asset_edit:proj-1`: MemoryTier miss, S3 hit (entries still in S3 as LKG), APPROACHING_STALE check passes if S3 entry is within TTL, served fresh from S3. SWR fires in background.

**Is this a harmful cascade?** No. The S3 entries for entity types not involved in the commit are within their natural TTL and are served from S3 at zero origin cost. The only cost is a MemoryTier promotion on the next read for each entity type (S3 hit -> MemoryTier put). This is a minor throughput cost, not a correctness or latency concern.

**Conclusion**: The conservative invalidation strategy causes a benign increase in MemoryTier miss rate immediately following each commit. The miss rate returns to baseline within one S3 round-trip per entity type per project. The DataFrameCacheCoalescer prevents concurrent rebuild amplification.

### 1.4 Validation Summary

| Design Decision | Topology Risk | Verdict |
|----------------|--------------|---------|
| CACHE-1 `invalidate_project()` added to `CacheInvalidator` | Reviewed all 26 locations | NO adverse interactions |
| DERIVED_TIMELINE isolation from System B | Confirmed DERIVED_TIMELINE is in System A only | Architecture assumption holds |
| Conservative blanket invalidation | Benign MemoryTier miss rate increase | Acceptable trade-off (ADR-CA-001) |
| Concurrent SaveSession commits | Idempotent `remove()`, coalescer prevents herd | No stampede risk |
| ProgressiveTier (S3) not deleted on invalidation | S3 LKG persists for other entity types | Correct LKG behavior |

---

## Section 2: CACHE-1 Observability Design

### 2.1 How Operators Know the Fix Is Working

The CACHE-1 fix must be observable at three levels:
1. **The invalidation fired**: Did `CacheInvalidator` successfully call `invalidate_project()`?
2. **The staleness was resolved**: Is the system no longer serving stale DataFrames post-commit?
3. **Degradation is detected early**: If the invalidation path fails silently, is there an alert?

### 2.2 Primary Metric: Miss Rate (Not Hit Rate)

The key metric for CACHE-1 validation is **miss rate by entity type by project**, not hit rate. The CACHE-1 fix changes the miss rate pattern:

**Before fix**: Miss rate is low and steady (cache always serves, even stale data). Stale data is invisible from miss rate alone -- the cache is "hitting" on stale entries.

**After fix**: Miss rate spikes briefly after each SaveSession commit (invalidation fires, then SWR rebuild fills MemoryTier). Miss rate returns to low baseline within seconds.

**The miss rate spike pattern is the operational confirmation that CACHE-1 is working correctly.** A flat miss rate after a SaveSession commit indicates the invalidation path is NOT firing.

### 2.3 Metrics Specification

#### Layer: DataFrameCache (System B -- Primary Target of CACHE-1)

| Metric | Source | Collection Method | Granularity | Retention | Derivation |
|--------|--------|-------------------|-------------|-----------|------------|
| `dataframe_cache_miss_rate` | `DataFrameCache.get_async()` return value (freshness_state != FRESH) | Structured log emission per `get_async()` call, aggregated via CloudWatch Logs Insights | 1-minute | 30 days | Misses / (Misses + Hits) per entity_type, project_gid |
| `dataframe_cache_hit_rate` | `DataFrameCache.get_async()` FRESH returns | Structured log (secondary metric only) | 1-minute | 30 days | Reference only -- miss rate is the actionable signal |
| `dataframe_cache_invalidation_count` | `CacheInvalidator._invalidate_project_dataframes()` success log | `project_dataframe_cache_invalidated` log event per `invalidate_project()` call | Per-event | 30 days | Count of invalidations per project_gid per hour |
| `dataframe_cache_invalidation_failed_count` | `CacheInvalidator._invalidate_project_dataframes()` warning log | `project_dataframe_invalidation_failed` log event | Per-event | 30 days | Any non-zero value requires investigation |
| `dataframe_cache_freshness_state` | `FreshnessState` enum value returned by `DataFrameCache.get_async()` | Log emission with `{project_gid, entity_type, freshness_state}` dimensions | Per-event | 30 days | Distribution across FRESH, APPROACHING_STALE, STALE, CIRCUIT_FALLBACK |
| `dataframe_cache_circuit_fallback_count` | `FreshnessState.CIRCUIT_FALLBACK` state | Filtered from `dataframe_cache_freshness_state` | 1-minute | 30 days | Non-zero = circuit open, serving LKG (F-3 risk indicator) |
| `dataframe_cache_swr_rebuild_count` | `_swr_build_callback` invocation | Structured log in `_swr_build_callback`: `swr_build_started`, `swr_build_complete`, `swr_build_failed` | Per-event | 30 days | Rebuild rate should track invalidation count with ~seconds lag |
| `dataframe_cache_invalidation_latency_ms` | Time between `invalidate_for_commit()` entry and `invalidate_project()` return | Derived from log timestamps | Per-commit | 14 days | Should be sub-1ms (in-process RLock + dict ops) |

**How to add miss rate emission**: `DataFrameCache.get_async()` currently returns `FreshnessInfo` via thread-local side-channel. To make this observable at CloudWatch scale, emit a structured log event at the return of `get_async()`:

```python
# In DataFrameCache.get_async() (cache/integration/dataframe_cache.py):
logger.debug(
    "dataframe_cache_access",
    extra={
        "project_gid": project_gid,
        "entity_type": entity_type,
        "freshness_state": freshness_info.freshness.value if freshness_info else "unknown",
        "is_hit": freshness_info.freshness == FreshnessState.FRESH if freshness_info else False,
    },
)
```

This mirrors the existing pattern in `MutationInvalidator` where every significant action is logged with structured fields.

#### Layer: System A Entity Cache (SaveSession Path -- Existing, Context for CACHE-1)

| Metric | Source | Collection Method | Granularity | Retention |
|--------|--------|-------------------|-------------|-----------|
| `cache_invalidation_complete` | `CacheInvalidator.invalidate_for_commit()` log | Existing `cache_invalidation_complete` log event | Per-commit | 14 days |
| `cache_invalidation_failed` | `CacheInvalidator._invalidate_entity_caches()` warning | Existing `cache_invalidation_failed` log event | Per-event | 14 days |
| `dataframe_cache_invalidation_failed` | `CacheInvalidator._invalidate_dataframe_caches()` warning | Existing `dataframe_cache_invalidation_failed` log event | Per-event | 14 days |

#### Layer: CACHE-1 New Instrumentation (Gap-Filling)

The CACHE-ARCHITECTURE.md design specifies two new log events for the new `_invalidate_project_dataframes()` method:

| Log Event | Severity | Fields | Meaning |
|-----------|----------|--------|---------|
| `project_dataframe_cache_invalidated` | DEBUG | `project_gid` | Successful `invalidate_project()` call. Primary confirmation signal. |
| `project_dataframe_invalidation_failed` | WARNING | `project_gid`, `error` | Failed `invalidate_project()` call. Alert if > 0 in 5-minute window. |

**Mirror pattern from `MutationInvalidator._invalidate_project_dataframes()`** (lines 347-363):
- `MutationInvalidator` uses `logger.warning("project_dataframe_invalidation_failed", ...)` -- identical event name should be used in `CacheInvalidator` to allow a single CloudWatch Logs Insights query to catch failures from both invalidators.

### 2.4 Staleness Improvement Measurement (Before/After CACHE-1)

The capacity-specification established a 99%+ staleness window reduction for hot projects. To measure this before and after deployment:

**Before deployment baseline**: Query CloudWatch Logs for `dataframe_cache_freshness_state` with `freshness_state = "STALE"` or `"APPROACHING_STALE"` during known SaveSession commit windows. The baseline will show these states persisting for minutes after commits.

**After deployment confirmation**: Query for the same signals. Within 10-30 seconds after a SaveSession commit:
1. `project_dataframe_cache_invalidated` log event fires (confirms invalidation ran)
2. `dataframe_cache_access` with `freshness_state = "STALE"` or `"APPROACHING_STALE"` fires briefly (first read after invalidation hits S3 LKG)
3. `swr_build_complete` fires (SWR rebuild completes)
4. `dataframe_cache_access` with `freshness_state = "FRESH"` resumes (MemoryTier repopulated)

The time from event 1 to event 4 is the operational staleness window post-fix. Capacity-specification estimates 2-10 seconds.

**CloudWatch Logs Insights query for validation**:
```
fields @timestamp, project_gid, entity_type, freshness_state
| filter @message like /dataframe_cache_access|project_dataframe_cache_invalidated|swr_build/
| sort @timestamp asc
| stats count(*) by bin(30s), freshness_state
```

### 2.5 Alert Design: CACHE-1 Path

#### Alert: DataFrameCache Invalidation Failure

- **Condition**: `count(project_dataframe_invalidation_failed) > 0` over 5-minute window
- **Severity**: WARNING
- **Derivation**: Any invalidation failure means the next read will serve stale data for up to entity_TTL * 4 (the before-fix window). Even a single failure re-introduces the pre-CACHE-1 staleness bug for that project. The threshold is zero tolerance -- one failure is one alert.
- **Response**: Check `project_gid` and `error` fields in the log event. Likely causes: DataFrameCache not initialized (check if `get_dataframe_cache()` returned None at `CacheInvalidator` construction), threading exception in `MemoryTier.remove()`. If `error` contains "NoneType", `dataframe_cache` was not injected -- check `SaveSession.__init__()` wiring.
- **Escalation**: If failures persist for > 15 minutes, the effective behavior is pre-fix. Page SRE to investigate `CacheInvalidator` construction site.

#### Alert: DataFrameCache Miss Rate Elevation (Post-Commit)

- **Condition**: `dataframe_cache_miss_rate > 20%` sustained for > 5 minutes (not following a known commit batch)
- **Severity**: WARNING
- **Derivation**: Brief miss rate elevation (30-60 seconds) after a commit is expected and correct (CACHE-1 intentionally evicts). Sustained elevation indicates either: (a) cache is not repopulating (SWR rebuild failing), or (b) invalidation is firing too aggressively. The 20% threshold is derived from the topology: 5 entity types per project, 5 projects maximum = 25 maximum simultaneous evictions. A 20% miss rate sustained for 5 minutes means multiple rebuilds are failing.
- **Response**: Check `swr_build_failed` log events. Check circuit breaker state (`dataframe_cache_circuit_fallback_count`). If SWR is failing, likely cause is Asana API unreachable -- check origin health.
- **Escalation**: If circuit breaker is open for > 10 minutes, F-3 (unlimited LKG staleness) risk activates -- page SRE.

#### Alert: Circuit Breaker Open (F-3 Risk Indicator)

- **Condition**: `dataframe_cache_circuit_fallback_count > 0` for any `project_gid` sustained for > 10 minutes
- **Severity**: WARNING
- **Derivation**: Circuit opens after 3 SWR rebuild failures (failure_threshold=3, per TOPOLOGY-CACHE section 3.4.3). Reset timeout is 60s. A circuit open for > 10 minutes means 10+ consecutive reset attempts have failed. At this point, the system is serving LKG data with no bound (F-3 -- deferred, unlimited `LKG_MAX_STALENESS_MULTIPLIER = 0.0`). This is the F-3 operational risk materializing.
- **Response**: See Runbook: Origin Failure With Fail-Open (Section 5.4). Identify which project and entity type is circuit-open. Check Asana API status. Check `swr_build_no_bot_pat` or `swr_build_no_workspace` for auth failures.
- **Escalation**: If Asana API is confirmed down, alert is expected -- notify product team of stale data state. If Asana API is up, investigate SWR callback for auth or config failure.

---

## Section 3: F-4 Lambda Blast Radius Documentation

### 3.1 What `clear_all_tasks()` Actually Does

The Lambda invalidation mode `clear_tasks=True` calls `TieredCacheProvider.clear_all_tasks()`, which delegates to `RedisCacheProvider.clear_all_tasks()`. This method SCAN-deletes all keys matching the pattern `asana:tasks:*`.

**What the name suggests**: "Clear task cache entries."

**What it actually clears**: Every key under the `asana:tasks:*` prefix covers ALL entry types registered under task GIDs:

| Entry Type | Key Pattern Affected | What Is Lost |
|------------|---------------------|--------------|
| TASK | `asana:tasks:{gid}:task` | Task entity data |
| SUBTASKS | `asana:tasks:{gid}:subtasks` | Subtask GID lists |
| DETECTION | `asana:tasks:{gid}:detection` | Tier 1/2 detection results |
| STORIES | `asana:tasks:{gid}:stories` | Story lists including incremental cursors |
| SECTION | `asana:tasks:{gid}:section` | Section membership data |
| USER | `asana:tasks:{gid}:user` | User/assignee data |
| DERIVED_TIMELINE | `asana:tasks:{gid}:derived_timeline` | Pre-computed section timeline data |
| _meta | `asana:tasks:{gid}:_meta` | Version metadata (freshness stamps) |
| DataFrames (per-task) | `asana:struc:{task_gid}:{project}` -- separate prefix, NOT cleared | NOT cleared by `clear_all_tasks()` |

**S3 counterpart**: `TieredCacheProvider.clear_all_tasks()` also calls `S3CacheProvider`-equivalent cleanup for the `{prefix}/tasks/` path in S3. This mirrors the Redis scope -- all entry types per task GID.

### 3.2 Story Incremental Cursor Destruction

The most operationally significant consequence is the destruction of story incremental cursors.

`cache/integration/stories.py` implements `load_stories_incremental()` which uses an Asana `since` cursor: the `created_at` timestamp of the most recent cached story. On subsequent fetches, only stories newer than the cursor are fetched (`GET /tasks/{gid}/stories?since={cursor}`). This is the ADR-0020 optimization that reduces Asana API call cost.

After `clear_tasks`:
- All `STORIES` entries under `asana:tasks:*` are deleted from Redis AND S3.
- The next call to `load_stories_incremental()` for any task finds no cached stories.
- Without a cursor, the Asana API is called with no `since` parameter: full story history fetch.
- For tasks with hundreds of stories (active contacts, long-running offers), this can mean fetching 100-500 stories per task in paginated calls.
- Story cache re-warm occurs naturally via the Lambda warmer on the next scheduled warm cycle.

### 3.3 Recovery Time Estimates Per Lambda Invalidation Mode

| Mode | What Is Cleared | Recovery Path | Estimated Recovery Time |
|------|-----------------|---------------|------------------------|
| `clear_tasks=True` (default) | ALL Redis `asana:tasks:*` entries + S3 `{prefix}/tasks/` objects | Lambda warmer re-warms story + entity cache | 5-30 minutes (proportional to offer count * story history depth). During recovery, each cold task access fetches full story history from Asana API. |
| `clear_dataframes=True` | DataFrameCache MemoryTier via `invalidate_on_schema_change()` | Next API read triggers SWR rebuild per entity type per project | 2-10 seconds per entity type per project (SWR background). 5 entity types * ~5 projects = 25 rebuilds, serialized by coalescer. Full recovery ~30-120 seconds. |
| `invalidate_project={gid}` | S3 section parquets + manifest for one project | Lambda warmer on next scheduled cycle rebuilds parquets for that project | 5-15 minutes (next warmer invocation + build time). In-flight API requests may hit cold ProgressiveTier and trigger SWR builds -- adds 2-4s per request until warmer completes. |

### 3.4 Recommended Documentation Content for `cache_invalidate.py`

The following docstring block should be added to the `_invalidate_cache_async()` function's `clear_tasks` handling section (after line 133 in the current implementation):

```python
# BLAST RADIUS: clear_all_tasks() clears ALL entry types under asana:tasks:*
# This includes: TASK, SUBTASKS, DETECTION, STORIES, SECTION, USER,
# DERIVED_TIMELINE, and _meta (version metadata) for every cached task GID.
# It also clears S3 objects under {prefix}/tasks/.
#
# CRITICAL CONSEQUENCE: Story incremental cursors (ADR-0020) are destroyed.
# The 'since' cursor for load_stories_incremental() is the latest story's
# created_at in the STORIES cache entry. After this operation, all subsequent
# story fetches will be full-history fetches (no 'since' parameter) until
# the Lambda warmer re-populates the story cache.
#
# RECOVERY: Schedule cache_warmer Lambda after this operation.
# Estimated recovery: 5-30 minutes depending on offer/contact count.
# During recovery, Asana API call volume increases proportionally to
# the number of tasks with story history.
#
# NOTE: This operation does NOT clear DataFrameCache (System B / MemoryTier).
# Use clear_dataframes=True for DataFrameCache invalidation.
# NOTE: per-task DataFrame entries (asana:struc:*) are NOT cleared by this operation.
```

---

## Section 4: F-5 ApiSettings Test Isolation Verdict

### 4.1 Investigation Results

**Claim under investigation**: `get_settings()` in `api/config.py` uses `@lru_cache` with no `cache_clear()` registration in `SystemContext.reset_all()`. If tests modify `ASANA_API_*` env vars between test cases, the cached `ApiSettings` could persist and cause test pollution.

**Methodology**: Searched all test files for:
1. Tests that reference `ASANA_API_*` env vars (the prefix for `ApiSettings`)
2. Tests that reference `get_settings` from `api/config.py`
3. Any call to `get_settings.cache_clear()`

**Findings**:

1. No test file sets `ASANA_API_CORS_ALLOWED_ORIGINS`, `ASANA_API_RATE_LIMIT_RPM`, `ASANA_API_LOG_LEVEL`, or `ASANA_API_DEBUG` env vars. Zero matches.

2. References to `get_settings` in tests are consistently `autom8_asana.settings.get_settings` (the main `Settings` class) or `autom8_asana.api.config.ApiSettings` mocked via `unittest.mock.patch`. No test directly calls the `api/config.get_settings()` function and relies on env var state leaking between test cases.

3. The `ASANA_API_` env vars are for CORS, rate limiting, log level, and debug mode -- none of which are modified by test cases in the suite. `AUTH_JWKS_URL` and `AUTH_*` settings that tests DO modify (`test_settings_url_guard.py`) are fields on the main `autom8_asana.settings.Settings` object, not `ApiSettings`.

4. No call to `get_settings.cache_clear()` exists anywhere in the codebase (verified via grep of `cache_clear` across all `.py` files).

### 4.2 Verdict: NOT A REAL PROBLEM (THEORETICAL ONLY)

**F-5 is theoretical in the current test suite.** Test pollution from `ApiSettings` lru_cache is not occurring because:
- No test modifies `ASANA_API_*` env vars
- The fields in `ApiSettings` (CORS origins, rate limit, log level, debug) are not modified by any test

**Risk boundary**: The risk activates only if a future test is written that:
1. Sets an `ASANA_API_*` env var
2. Does NOT call `from autom8_asana.api.config import get_settings; get_settings.cache_clear()`
3. Runs in the same process as another test that expects a different `ASANA_API_*` value

**Recommendation**: Accept as-is for current test suite. Document the risk in a comment near `get_settings()` in `api/config.py`:

```python
@lru_cache
def get_settings() -> ApiSettings:
    """Get cached API settings singleton.

    Note: Not registered with SystemContext.reset_all() because ApiSettings
    only contains ASANA_API_* prefixed vars (CORS, rate limit, log level, debug)
    which no test suite modifies. If future tests modify ASANA_API_* env vars,
    add get_settings.cache_clear to SystemContext registration or use
    monkeypatch.delenv("ASANA_API_CORS_ALLOWED_ORIGINS") + get_settings.cache_clear()
    in the test fixture.

    Returns:
        ApiSettings instance loaded from environment.
    """
    return ApiSettings()
```

This closes F-5 as a documentation-only hygiene item with no code change required.

---

## Section 5: Operational Runbooks

### 5.1 Scenario: CACHE-1 Invalidation Path Not Firing (Silent Regression)

**Detection**: `project_dataframe_cache_invalidated` log event absent after `cache_invalidation_complete` log events during known pipeline runs. Alternatively: manual test shows stale entity counts persist > 60 seconds after a SaveSession commit.

**Impact**: Pre-fix behavior restored. Stale DataFrames served for up to entity_TTL * 4 (up to 12 min for offers, 60 min for contacts). MRR calculations from this window are incorrect.

**Immediate Response**:
1. Verify `CacheInvalidator` construction site in `SaveSession.__init__()`. Check that `dataframe_cache=get_dataframe_cache()` is being passed.
2. Check if `get_dataframe_cache()` returns `None` (DataFrameCache not initialized). If `None`, `_invalidate_project_dataframes()` silently exits early -- this is the design, but means S3 is not configured.
3. Check ECS task environment for `ASANA_CACHE_S3_BUCKET`. If not set, `initialize_dataframe_cache()` returns `None` and the fix is not active.
4. If `get_dataframe_cache()` returns a non-None cache but invalidation log is absent, check if `SaveSession` was updated to pass `dataframe_cache` (construction site change is part of the implementation).

**Recovery Verification**: After investigating construction site, trigger a test SaveSession commit and verify `project_dataframe_cache_invalidated` appears in CloudWatch Logs.

---

### 5.2 Scenario: Cache Node Failure (MemoryTier/Redis Unavailable)

**Detection**: `cache_invalidation_failed` or `project_dataframe_invalidation_failed` log events with Redis connection errors. API latency increases (cold path fallback to S3 or Asana API).

**Impact Assessment**:
- System A (Redis): `TieredCacheProvider` falls back to S3 tier for reads. Write invalidations fail (logged as `cache_invalidation_failed`). Entity data served from S3 until Redis recovers.
- System B (DataFrameCache MemoryTier): In-process, cannot fail due to Redis outage. ProgressiveTier (S3) serves as fallback.

**Immediate Response**:
1. Check ElastiCache health in AWS console.
2. Verify `RedisCacheProvider` degraded state (`redis_degraded` log events) -- reconnect attempts fire every 30s.
3. System continues operating via S3 fallback -- no immediate action required unless S3 is also degraded.
4. Monitor API latency (P99 should stay under 2s on S3 cold path; > 2s indicates S3 also degraded).

**Recovery Verification**: `redis_reconnect_success` log event. Validate `cache_invalidation_complete` logs resume after Redis reconnects.

---

### 5.3 Scenario: Stampede Event (Post-Invalidation)

**Detection**: Multiple concurrent requests for the same `(project_gid, entity_type)` shortly after a SaveSession commit. Observable via `DataFrameCacheCoalescer` wait events in logs (if instrumented), or via elevated `swr_build_started` counts for the same key.

**Impact Assessment**: `DataFrameCacheCoalescer` should prevent multiple concurrent builds. Maximum 1 active build per `(project_gid, entity_type)` key. Concurrent readers wait up to 60 seconds (coalescer timeout). A stampede is only harmful if coalescer wait timeout (60s) is exceeded and waiters fall through to individual builds.

**Immediate Response**:
1. Check `BuildCoordinator` concurrency: `max_concurrent_builds=4` global semaphore. If 4 builds are already in progress, new build attempts queue behind semaphore.
2. Check if coalescer timeout (60s) is being exceeded for any key -- this indicates Asana API is slow, not a stampede problem per se.
3. Monitor `swr_build_started` count. If > 4 concurrent for different projects, normal operation. If > 1 concurrent for the same `(project_gid, entity_type)`, coalescer may not be engaged (check if using old non-coalesced path).

**Recovery Verification**: `swr_build_complete` events for affected keys within 60 seconds of stampede onset.

---

### 5.4 Scenario: Origin Failure With Fail-Open (Circuit Breaker Open)

**Detection**: `dataframe_cache_circuit_fallback_count > 0` for any project (from `FreshnessState.CIRCUIT_FALLBACK` log events). `swr_build_failed` events accumulating. Circuit opens after 3 consecutive build failures per project (per TOPOLOGY-CACHE section 3.4.3).

**Impact Assessment**: System serves LKG (last-known-good) data from MemoryTier or S3. Staleness grows unbounded (F-3 -- `LKG_MAX_STALENESS_MULTIPLIER = 0.0`). For short outages (< circuit_reset_timeout * failure_count = 60s * 3 = 3 minutes), LKG is likely acceptable. For extended outages, MRR calculations become progressively less accurate.

**Staleness tracking during circuit open**: Check `FreshnessInfo.age_seconds` if surfaced in logs. Current implementation exposes `FreshnessState` via thread-local but `age_seconds` may not be logged. This is an observability blind spot (see Section 6.1).

**Immediate Response**:
1. Check `swr_build_failed` log events for root cause: `swr_build_no_bot_pat` (PAT expired/missing), `swr_build_no_workspace` (workspace GID missing), or connection error (Asana API down).
2. If `swr_build_no_bot_pat`: check ASANA_PAT secret in Secrets Manager. PAT expiry is the most common cause.
3. If Asana API confirmed down: alert is expected -- circuit open is correct behavior. Notify product team that data is stale from (circuit open timestamp). Do not attempt to clear the DataFrameCache (that removes LKG and causes hard misses).
4. Do NOT invoke Lambda `clear_dataframes=True` during an Asana outage -- this destroys LKG data and the system will start returning 503s.

**Recovery Verification**: Circuit enters HALF_OPEN after 60s reset timeout. SWR rebuild attempt succeeds. `FreshnessState` transitions to FRESH. `dataframe_cache_circuit_fallback_count` drops to 0.

---

### 5.5 Scenario: Capacity Exhaustion (MemoryTier Full)

**Detection**: MemoryTier eviction rate increasing. Memory pressure log events from `MemoryTier` (if instrumented). LRU eviction at max entry count (100 entries) or max heap (30% of container heap, ~307MB at 1GB container).

**Impact Assessment**: LRU eviction at 100 entries: with 5 entity types * 5 projects = 25 entries, capacity exhaustion would require > 100 active project-entity combinations -- well above current scale (~4k offers, ~5 projects). Memory exhaustion is the more likely trigger: if average DataFrame size increases significantly (e.g., contacts table grows from ~20k to ~200k rows).

**Immediate Response**:
1. Check container memory utilization in ECS.
2. Check MemoryTier current entry count (if exposed via stats).
3. If entry count at max (100): working set has grown. Check entity count growth (new projects onboarded?).
4. If heap limit reached: DataFrame sizes have grown. Check row counts per entity type.

**Recovery Verification**: LRU eviction automatically frees memory by removing oldest entries. No manual intervention needed unless entity count growth is systemic -- in which case, increase `dataframe_max_entries` and `dataframe_heap_percent` config.

---

### 5.6 Scenario: Lambda Cache Invalidation (Operational Blast Radius)

**Detection**: Lambda `cache_invalidate_handler_invoked` log event. `tasks_cleared.redis` > 0.

**Impact Assessment** (per Section 3, F-4 blast radius):
- All story incremental cursors destroyed
- All entity data (TASK, SUBTASKS, DETECTION) cleared from Redis + S3
- Recovery time: 5-30 minutes (Lambda warmer)
- During recovery: Asana API call volume spikes (full story re-fetches)

**Immediate Response**:
1. Immediately trigger `cache_warmer` Lambda after `cache_invalidate` Lambda completes.
2. Monitor `swr_build_count` for story cache re-warm progress.
3. Expect elevated Asana API call rate for 5-30 minutes. Check Asana rate limit metrics.
4. Monitor API response latency during recovery (P99 may increase to 2-4s on cold story fetch paths).

**Recovery Verification**: `cache_warmer_complete` log event from Lambda warmer. Story cache repopulated: `load_stories_incremental()` should show non-zero cache hits within 30 minutes.

---

## Section 6: Design Validation Checklist

### 6.1 Blind Spots and Gaps

The following observability blind spots exist in the current system. These cannot be fully closed with existing logging infrastructure alone -- they require instrumentation additions:

**BLIND SPOT 1: LKG Data Age Is Not Logged**

When `FreshnessState.CIRCUIT_FALLBACK` is active, the LKG entry is served from MemoryTier or S3. The age of the LKG data (how old it is relative to the current time) is not emitted to CloudWatch. An operator during a circuit-open event cannot determine whether the LKG data is 5 minutes old or 5 hours old from logs alone.

- **Impact**: F-3 (unlimited LKG staleness) is a known risk. Without LKG age visibility, the operator cannot make a data-informed decision about whether to surface a "data may be stale" signal to API consumers.
- **Remediation**: Add `lkg_age_seconds` to the `dataframe_cache_access` log event when `freshness_state = "CIRCUIT_FALLBACK"`. Derive from `DataFrameCacheEntry.written_at` timestamp.
- **Priority**: HIGH -- this is the observable manifestation of F-3.
- **Route**: Implementation work for 10x-dev or SRE.

**BLIND SPOT 2: SWR Rebuild Success/Failure Is Not Structured-Logged**

`_swr_build_callback` in `factory.py` logs `swr_build_no_bot_pat` and `swr_build_no_workspace` (early exits) but does not log a structured success or failure event for the actual rebuild call (`builder.build_progressive_async()`). If the build fails silently (e.g., `ProgressiveProjectBuilder` returns `result.total_rows = 0` due to empty Asana project), no log event surfaces this.

- **Impact**: Circuit breaker opens silently if the coalescer's error handling swallows the exception. An operator cannot distinguish between "SWR rebuild succeeded but took long" and "SWR rebuild failed and circuit is counting failures."
- **Remediation**: Add structured log events to `_swr_build_callback`: `swr_build_started` (with `project_gid`, `entity_type`), `swr_build_complete` (with `total_rows`, `duration_ms`), `swr_build_failed` (with `error`, `error_type`).
- **Priority**: HIGH -- without this, circuit breaker open is the only signal of SWR failure.
- **Route**: Implementation work for 10x-dev.

**BLIND SPOT 3: Conservative Invalidation Blast Radius Is Not Instrumented**

`_invalidate_project_dataframes()` in the new `CacheInvalidator` method logs one event per `invalidate_project()` call but does not log which entity types were evicted from MemoryTier. When a single-entity-type commit triggers a 5-entity-type eviction (conservative blanket invalidation per ADR-CA-001), the operator cannot see the collateral evictions.

- **Impact**: Minor. The miss rate spike from collateral evictions is detectable via `dataframe_cache_access` miss events, but correlating them to the originating commit is difficult.
- **Remediation**: Log eviction count per `invalidate_project()` call: `project_dataframe_cache_invalidated` event should include `entity_types_evicted: int` (the count of non-absent keys that were actually removed from MemoryTier).
- **Priority**: LOW -- operational curiosity, not a blocker.
- **Route**: Implementation work for 10x-dev, opportunistically.

### 6.2 Validation Checklist (Full)

- [x] Every designed failure mode has observability coverage
  - CACHE-1 invalidation failure: `project_dataframe_invalidation_failed` warning log
  - CACHE-1 silent regression: `project_dataframe_cache_invalidated` absence detection
  - Circuit breaker open: `FreshnessState.CIRCUIT_FALLBACK` log event
  - SWR rebuild failure: `swr_build_no_bot_pat`, `swr_build_no_workspace` (partial -- see BLIND SPOT 2)
- [x] Alerting thresholds are consistent with capacity limits
  - Miss rate alert (20% sustained) derived from: 5 entity types * 5 projects / total keys in MemoryTier
  - Invalidation failure alert (0 tolerance) derived from: single failure = pre-fix staleness reintroduced
  - Circuit fallback alert (10 minutes) derived from: circuit reset timeout (60s) * 10 attempts = reasonable re-try window before declaring extended outage
- [x] Stampede protection has activation monitoring
  - `DataFrameCacheCoalescer` wait events (partially -- not yet instrumented, see Section 2.3)
  - `BuildCoordinator` concurrency limit (4) via `swr_build_started` count
- [x] Replication lag alerts: Not applicable (DataFrameCache is not distributed -- no replication)
- [x] Dashboard covers full thermal landscape (see Section 7)
- [x] Runbook covers every failure mode in architecture (Sections 5.1-5.6)
- [ ] LKG age visibility during circuit-open (BLIND SPOT 1 -- implementation work required)
- [ ] SWR rebuild structured logging (BLIND SPOT 2 -- implementation work required)
- [ ] Collateral eviction instrumentation (BLIND SPOT 3 -- low priority)

---

## Section 7: Dashboard Specification

### Overview Panel: Cache Health at a Glance

**Metrics to display**:
- `dataframe_cache_miss_rate` (all entity types, 5-minute rolling) -- primary health signal
- `dataframe_cache_circuit_fallback_count` (per project_gid) -- F-3 risk indicator
- `project_dataframe_invalidation_failed` event count (5-minute window) -- CACHE-1 path health
- `cache_invalidation_failed` event count (5-minute window) -- System A path health

**Layout**: 4-metric row. Any non-zero value in the bottom two metrics requires investigation. Miss rate above 5% for > 5 minutes without a known commit batch requires investigation.

### Per-Layer Detail Panel: DataFrameCache (System B)

**Metrics to display**:
- `dataframe_cache_access` breakdown by `freshness_state` (FRESH / APPROACHING_STALE / STALE / CIRCUIT_FALLBACK) per entity type
- `swr_build_started` and `swr_build_complete` counts per entity type per project
- `project_dataframe_cache_invalidated` count per project (correlates with SaveSession commit rate)
- MemoryTier entry count (if exposed via stats endpoint)

**Correlation view**: Overlay `cache_invalidation_complete` events (SaveSession commits) with `dataframe_cache_miss_rate` spikes. After CACHE-1 deployment, each commit should produce a detectable but brief miss rate spike followed by SWR rebuild completion within 10 seconds.

### Per-Layer Detail Panel: System A (Entity Cache)

**Metrics to display**:
- `cache_invalidation_complete` count (SaveSession commit rate proxy)
- `cache_invalidation_failed` count (Redis health proxy)
- `dataframe_cache_invalidation_failed` count (per-task DataFrame System A path)
- `KeysCleared` CloudWatch metric from Lambda invalidation (existing -- Lambda already emits this)

### Correlation View: Cache vs. Origin

**Metrics to overlay**:
- `dataframe_cache_miss_rate` (left axis)
- Asana API call rate from `_swr_build_callback` (right axis, derived from `swr_build_started`)
- SaveSession commit events (event overlay)

**Purpose**: Validate that miss rate spikes correlate with commits (healthy CACHE-1 behavior) rather than Asana API failures (circuit breaker risk).

---

## Section 8: Sprint Manifest

### WS-INVALIDATION: F-1 DataFrameCache Invalidation Fix

**Scope**: F-1 finding. The core correctness defect.

**Findings covered**: F-1 (CACHE-1 design)

**Files to modify**:
- `src/autom8_asana/persistence/cache_invalidator.py` -- add `dataframe_cache` parameter + `_collect_project_gids()` + `_invalidate_project_dataframes()` methods
- `src/autom8_asana/persistence/session.py` (or wherever `CacheInvalidator` is constructed) -- pass `get_dataframe_cache()` as `dataframe_cache` parameter
- `src/autom8_asana/cache/integration/dataframe_cache.py` -- if `DataFrameCache.invalidate_project()` needs `TYPE_CHECKING` import guard in `cache_invalidator.py`

**Files to create**:
- `tests/unit/persistence/test_cache_invalidator.py` -- 7 test cases per CACHE-ARCHITECTURE.md test strategy section

**Estimated effort**: ~3-4 hours including tests. Construction site verification (finding the exact `CacheInvalidator` instantiation) is the highest-risk step -- budget 30 minutes for investigation.

**Dependencies**: None. CacheInvalidator is standalone; `MutationInvalidator` is the reference but is not being modified.

**Test strategy**:
1. Unit tests for `CacheInvalidator` (7 cases): constructor injection, no-op when `None`, project-level invalidation, project GID deduplication, failure isolation, entity without memberships, empty commit.
2. Confirm existing test suite still passes: `CacheInvalidator` tests that exist elsewhere must not break (no `dataframe_cache` parameter was required before).
3. Integration check: confirm `MutationInvalidator` tests in `tests/unit/cache/test_mutation_invalidator.py` still pass (no changes to that file).

**Implementation priority**: FIRST. This is the correctness defect. All other workstreams are documentation or hygiene.

---

### WS-OBSERVABILITY: CACHE-1 Observability + F-4 Blast Radius Documentation

**Scope**: Add structured logging for CACHE-1 path. Document F-4 blast radius.

**Findings covered**: F-4 (blast radius documentation), CACHE-1 observability (new instrumentation per Section 2.3)

**Files to modify**:
- `src/autom8_asana/cache/dataframe/factory.py` -- add `swr_build_started`, `swr_build_complete`, `swr_build_failed` structured log events to `_swr_build_callback` (closes BLIND SPOT 2)
- `src/autom8_asana/cache/integration/dataframe_cache.py` -- add `dataframe_cache_access` log event at `get_async()` return with `freshness_state`, `project_gid`, `entity_type` fields (enables miss rate CloudWatch query)
- `src/autom8_asana/lambda_handlers/cache_invalidate.py` -- add blast radius comment block per Section 3.4

**Files to create**: None (documentation goes in code comments, not new files)

**Estimated effort**: ~2-3 hours. `dataframe_cache_access` emission is the most effort (requires identifying the return point in `get_async()`).

**Dependencies**: Can run in parallel with WS-INVALIDATION if different engineers. No file overlap.

**Test strategy**: Verify existing tests still pass (log events are additive). Spot-check log output in local dev for correct field names.

---

### WS-HYGIENE: F-5 Verdict Documentation

**Scope**: F-5 test isolation verdict. No code change required.

**Findings covered**: F-5 (ApiSettings lru_cache test isolation -- CONFIRMED NOT A PROBLEM)

**Files to modify**:
- `src/autom8_asana/api/config.py` -- add docstring note per Section 4.2 (conditional: only if team wants explicit documentation of the "not registered" decision)

**Estimated effort**: ~15 minutes. This is a one-sentence docstring addition. Optionally skip entirely if the finding is simply closed as "verified not a problem."

**Dependencies**: None.

**Test strategy**: N/A -- no code change.

---

### WS-DEFERRED: F-3 LKG Multiplier + Production Data Collection

**Scope**: F-3 deferred pending operational data. No implementation yet. Work product is a monitoring setup to collect the required data.

**Findings covered**: F-3 (DEFER verdict confirmed)

**Action required before implementation**:
1. Deploy WS-OBSERVABILITY first (specifically `dataframe_cache_access` with `freshness_state` emission).
2. Run for 30 days collecting `FreshnessState.CIRCUIT_FALLBACK` events and `swr_build_failed` events.
3. Compute P95 circuit-open duration using the derivation formula from CAPACITY-SPECIFICATION.md Section 3.3.
4. Only then set `LKG_MAX_STALENESS_MULTIPLIER` to a data-derived value.

**Files to modify (when triggered)**:
- `src/autom8_asana/config.py` -- `LKG_MAX_STALENESS_MULTIPLIER` value (currently `0.0`)
- Possibly config schema change if per-entity-type bounds are required (see CAPACITY-SPECIFICATION.md Section 3.4)

**Estimated effort (when triggered)**: 30 days data collection + 1 hour analysis + config change + 30 minutes verification.

**Dependencies**: WS-OBSERVABILITY must ship first (to collect the CIRCUIT_FALLBACK data).

---

### Implementation Priority Order

| Priority | Workstream | Rationale |
|----------|-----------|-----------|
| 1 | WS-INVALIDATION | Correctness defect. Every SaveSession commit currently produces incorrect API results for up to 60 minutes. This is the primary fix. |
| 2 | WS-OBSERVABILITY | Required for: (a) operational confirmation that WS-INVALIDATION is working, (b) collecting F-3 prerequisite data, (c) closing BLIND SPOT 2. Ship within same sprint as WS-INVALIDATION. |
| 3 | WS-HYGIENE | Optional documentation. Low value -- the verdict is that F-5 is not a real problem. Deferred until a natural maintenance pass. |
| 4 | WS-DEFERRED | Cannot act until WS-OBSERVABILITY has collected 30 days of CIRCUIT_FALLBACK data. |

---

## Section 9: Cross-Rite Routing Recommendations

### To 10x-dev (Implementation)

**WS-INVALIDATION**: The exact change specification in CACHE-ARCHITECTURE.md (Section: "CACHE-1 Design: Exact Change Specification") is implementation-ready. The architect has provided constructor signature, method bodies, calling convention analysis, and construction site guidance. The 10x-dev should verify the construction site (`SaveSession.__init__()`) before coding and confirm no circular import is introduced by adding `get_dataframe_cache()` to the persistence layer.

**WS-OBSERVABILITY**: Three specific instrumentation additions:
1. `dataframe_cache_access` log event in `DataFrameCache.get_async()`
2. `swr_build_started/complete/failed` log events in `_swr_build_callback`
3. Blast radius comment block in `cache_invalidate.py`

All are additive logging additions with no behavioral change. Appropriate for 10x-dev routing.

**BLIND SPOT 1 (LKG age logging)**: Add `lkg_age_seconds` to `dataframe_cache_access` event when `freshness_state = CIRCUIT_FALLBACK`. Requires exposing `DataFrameCacheEntry.written_at` or `computed_at` at the `get_async()` return site. Medium effort.

### To SRE

**CloudWatch Alarms**: Create the three alerts from Section 2.5:
1. `project_dataframe_invalidation_failed` count > 0 over 5 minutes (WARNING)
2. `dataframe_cache_miss_rate` > 20% sustained 5 minutes (WARNING)
3. `dataframe_cache_circuit_fallback_count` > 0 sustained 10 minutes (WARNING)

**F-3 Data Collection**: After WS-OBSERVABILITY ships, create a CloudWatch Dashboard with `dataframe_cache_freshness_state` filtered to `CIRCUIT_FALLBACK`. Run 30-day collection window. Report P50/P95 circuit-open duration to SRE/product decision-maker for F-3 calibration.

**Runbook Distribution**: Runbooks in Section 5 should be published to the team's incident response wiki before the next production deploy that includes WS-INVALIDATION.

### To Product Owner

**F-2 Deferred Decision**: Confirm whether 300-second staleness for the section-timelines API (`GET /section-timelines/{project_gid}`) is acceptable. Evidence in THERMAL-ASSESSMENT.md (U-2) suggests it is acceptable for analytical reporting. If confirmed acceptable, close F-2. If near-real-time freshness is required, implementation spec for CACHE-2 optional enhancement is complete in CACHE-ARCHITECTURE.md (Section: "CACHE-2 Design: Optional Timeline Invalidation Enhancement").

---

## Handoff Checklist

- [x] `observability-plan.md` produced at `.claude/wip/SPIKE-CACHE-ARCH/OBSERVABILITY-PLAN.md`
- [x] Miss rate is the primary metric for DataFrameCache (not hit rate)
- [x] Every alerting threshold has a derivation traced to architecture or capacity specs
- [x] Runbook covers every failure mode in the architecture (5.1-5.6: invalidation failure, cache node failure, stampede, origin failure, capacity exhaustion, Lambda blast radius)
- [x] Design validation checklist completed with blind spots identified (BLIND SPOTS 1-3 documented)
- [x] Cross-rite routing recommendations noted (WS-INVALIDATION to 10x-dev, alerting to SRE, F-2 decision to product owner)
- [x] F-4 Lambda blast radius content produced for `cache_invalidate.py`
- [x] F-5 test isolation verdict: NOT A REAL PROBLEM (no test modifies ASANA_API_* env vars)
- [x] Cross-architecture validation: 26 locations reviewed, no unintended interactions from CACHE-1
- [x] Sprint manifest: 4 workstreams with files, effort, dependencies, and priority order
