# Analysis: Story Cache Freshness Opportunities

**Date**: 2026-02-20
**Author**: Architect
**Status**: RESEARCH (analysis only, no code changes)
**Context**: Post-ship review of story cache population mechanisms. User question: "Should SaveSession fire-and-forget story cache writes when pushing section changes?"

---

## Part 1: Current State Map -- When Do Story Cache Writes Happen?

### 1.1 Mechanism 1: Lambda Story Warming (Bulk, Scheduled)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py` (line 235)

The `_warm_story_caches_for_completed_entities()` function runs as the final phase of the Lambda cache warmer, after all DataFrame entity types have been warmed and GID mappings pushed.

**Trigger**: Lambda cron schedule. The exact cron is not defined in the application codebase -- it is configured in the deployment infrastructure (CloudFormation/Terraform/EventBridge, not checked in here). From the operational context, it runs periodically (likely hourly or similar).

**Flow**:
```
_warm_cache_async() completes all entity types
    -> _push_gid_mappings_for_completed_entities()
    -> _warm_story_caches_for_completed_entities()
        -> For each completed entity type:
            -> Retrieve warmed DataFrame, extract task GIDs from "gid" column
            -> For each task GID (Semaphore(3), chunks of 100):
                -> client.stories.list_for_task_cached_async(task_gid, max_cache_age_seconds=7200)
```

**Key details**:
- **Concurrency**: Semaphore(3), processed in chunks of 100
- **max_cache_age_seconds=7200**: Skips API calls for stories cached within the last 2 hours
- **Timeout detection**: Checks `_should_exit_early(context)` before each chunk
- **Failure isolation**: Per-task failures logged but do not abort the batch; per-entity-type failures logged but do not abort story warming; story warming failures NEVER affect overall warmer success
- **Scope**: All entity types that were successfully warmed (unit, business, offer, contact, asset_edit, asset_edit_holder, unit_holder)
- **Write path**: `list_for_task_cached_async()` -> `load_stories_incremental()` -> `cache.set_versioned(task_gid, entry)` with `EntryType.STORIES`

### 1.2 Mechanism 2: Bounded Self-Healing (Reactive, Request-Time)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` (line 444)

When `get_or_compute_timelines()` encounters cache misses during batch story reads, it fetches stories inline for a bounded number of misses.

**Trigger**: First request for a given (project_gid, classifier_name) pair after the derived timeline cache expires (5-minute TTL).

**Flow**:
```
get_or_compute_timelines()
    -> read_stories_batch(task_gids, cache)       # Pure read, no API
    -> misses = [gid for gid if stories_by_gid.get(gid) is None]
    -> if 0 < len(misses) <= 50:
        -> For each miss (Semaphore(5)):
            -> client.stories.list_for_task_cached_async(gid)    # API fetch + cache write
        -> Re-read batch after population
    -> elif len(misses) > 50:
        -> Log WARNING, return partial results (imputed only for misses)
```

**Key details**:
- **Threshold**: MAX_INLINE_STORY_FETCHES = 50
- **Concurrency**: Semaphore(5)
- **No max_cache_age_seconds**: Default behavior -- always attempts API fetch for misses
- **Bounded**: Protects against ALB timeout (60s) on full cold starts
- **Scope**: Only the specific (project_gid, classifier_name) pair being queried

### 1.3 Freshness Gaps

| Window | Stories Populated By | Staleness Risk |
|--------|---------------------|----------------|
| Lambda run completes | Lambda bulk warming | Fresh: all stories current as of Lambda run time |
| Lambda +0 to Lambda +2h | max_cache_age_seconds=7200 means next Lambda run skips recently-cached entries | Low: entries remain valid for 2h per the API skip threshold |
| Lambda +2h to next Lambda | No active population. Redis TTL for stories is 300s. S3 cold tier preserves stories without TTL | Medium: S3 entries are served via promotion, but new stories created after Lambda run are absent |
| Between Lambda runs (new offers added) | Self-healing catches up to 50 new offers per timeline request | Low for incremental changes; high if Lambda is down |
| Full cold start (no Lambda has run) | Self-healing cannot cover >50 misses; returns partial results | High: 3,800+ offers exceed threshold, timeline feature is non-functional |

**The critical gap**: When our system pushes section changes to Asana (via SaveSession `move_to_section` or lifecycle `CascadingSectionService`), a `section_changed` story is created on Asana's side. That story exists in Asana but is NOT reflected in our cache until the next Lambda run or a self-healing fetch. This creates a staleness window of up to 2 hours for timeline data.

---

## Part 2: SaveSession Integration Analysis

### 2.1 SaveSession Architecture Summary

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/session.py`

SaveSession is a unit-of-work coordinator with 14 collaborators, executing in a 6-phase commit pipeline:

```
Phase 0: ENSURE_HOLDERS       (auto-create missing holder subtasks)
Phase 1: CRUD + Actions        (entity creates/updates/deletes + action operations)
Phase 1.5: Cache Invalidation  (CacheInvalidator invalidates TASK, SUBTASKS, DETECTION, DATAFRAME)
Phase 2: Cascades              (field value propagation to descendants)
Phase 3: Healing               (add missing project memberships)
Phase 5: Automation            (evaluate automation rules)
```

**Relevant action**: `move_to_section` (ActionBuilder descriptor at line 1260) generates a `MOVE_TO_SECTION` ActionOperation. This ultimately calls the Asana API endpoint `POST /sections/{section_gid}/addTask` with `{"data": {"task": task_gid}}`.

When this API call succeeds, Asana creates a `section_changed` system story on the task. This is the EXACT moment the story exists in Asana but NOT in our cache.

### 2.2 SaveSession's Existing Cache Invalidation

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py`

`CacheInvalidator.invalidate_for_commit()` (line 50) runs at Phase 1.5 and invalidates:
- `EntryType.TASK` -- per-entity task cache
- `EntryType.SUBTASKS` -- per-entity subtask cache
- `EntryType.DETECTION` -- per-entity detection cache
- DataFrame caches via project membership lookup

**Critical finding: `EntryType.STORIES` is NOT in the invalidation list.** Neither `CacheInvalidator` (SaveSession's) nor `MutationInvalidator` (REST routes') touches story cache entries. Story invalidation is a blind spot across the entire mutation surface.

### 2.3 Feasibility: Fire-and-Forget Story Cache Write in SaveSession

**The concept**: After Phase 1 completes (actions executed, including `move_to_section`), identify task GIDs that had section-changing actions, and fire-and-forget a story cache write (or invalidation) for each affected task.

**What would be needed**:

```python
# Conceptual -- in _execute_crud_and_actions() or _finalize_commit()
section_changing_actions = [
    ActionType.MOVE_TO_SECTION,
    ActionType.ADD_TO_PROJECT,
    ActionType.REMOVE_FROM_PROJECT,
]
affected_task_gids = {
    ar.action.task.gid
    for ar in action_results
    if ar.success and ar.action.action in section_changing_actions
}
for gid in affected_task_gids:
    asyncio.create_task(
        self._client.stories.list_for_task_cached_async(gid),
        name=f"story_refresh:{gid}",
    )
```

### 2.4 Blast Radius Analysis

| Dimension | Assessment |
|-----------|-----------|
| **Coupling** | Medium. SaveSession currently has zero knowledge of story caches. Adding story awareness introduces a new concern into the unit-of-work pattern. However, `CacheInvalidator` already handles multiple cache tiers, so extending it to stories is a natural extension of existing responsibility. |
| **Latency impact** | Zero if fire-and-forget (asyncio.create_task). The commit returns immediately; story refresh happens in background. |
| **Error propagation** | Must be fully isolated. Story refresh failure must NEVER affect commit success. This is already the established pattern for cache invalidation in SaveSession (line 910: `CacheInvalidator` failures are logged but don't fail commit). |
| **Rate limit pressure** | Low per-commit. A typical commit has 1-5 section moves. Each fire-and-forget story fetch is one API call. This is negligible compared to the commit's CRUD batch operations. |
| **API call timing** | Tricky. The `section_changed` story is created asynchronously by Asana after the `addTask` API call returns. If we immediately fire a story fetch, the new story might not yet exist on Asana's side. There could be a race condition where we fetch stories and the `section_changed` story has not been recorded yet. |
| **Test surface** | Moderate. Would need to test: story refresh fires on section-changing actions, does not fire on non-section actions, failure isolation, no impact on commit result. |

### 2.5 Race Condition: The Fundamental Problem

**This is the critical issue.** When SaveSession calls `POST /sections/{section_gid}/addTask`, Asana returns `200 OK` immediately. The `section_changed` system story is created asynchronously by Asana's event system. There is no guarantee about when the story will be visible via `GET /tasks/{task_gid}/stories`.

If we fire-and-forget a story cache fetch immediately after the section move succeeds, we might:
1. Fetch stories and get the old list (without the new `section_changed` story)
2. Cache that stale list
3. Now the cache is actively wrong -- it has a fresh timestamp but is missing the most recent story

This is WORSE than having an expired cache entry, because the `max_cache_age_seconds` check will consider this entry fresh and skip re-fetching on the next read.

**Mitigation options**:
- **Option A**: Add a delay (e.g., 2-5 seconds) before fetching. Unreliable -- Asana's event lag is not guaranteed.
- **Option B**: Invalidate (delete) the story cache entry instead of refreshing it. This forces the next reader to fetch fresh. No race condition because we are deleting, not writing stale data.
- **Option C**: Use soft invalidation (mark entry as stale without deleting). The next reader sees the staleness hint and re-fetches.

**Option B is the winner.** Invalidation avoids the race condition entirely. The next `list_for_task_cached_async()` call (from Lambda warmer or self-healing) will do a full fetch and get the new story.

### 2.6 SaveSession Integration Verdict

| Integration Approach | Feasibility | Coupling Cost | Race Risk | Recommendation |
|---------------------|------------|---------------|-----------|----------------|
| Fire-and-forget story FETCH (write-through) | Medium | Medium | **HIGH** -- race with Asana async story creation | **REJECT** |
| Fire-and-forget story INVALIDATION (delete entry) | High | Low | None -- deleting is always safe | **RECOMMENDED** |
| Do nothing (status quo) | N/A | None | N/A | Acceptable but leaves freshness gap |

---

## Part 3: MutationInvalidator Integration Analysis

### 3.1 MutationInvalidator Architecture

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py`

`MutationInvalidator` is a stateless service that accepts `MutationEvent` objects and invalidates cache tiers. It is used by:
1. **REST route handlers**: Via `fire_and_forget()` (asyncio.create_task)
2. **FieldWriteService**: Via direct `invalidate_async()` call in fire-and-forget task

**Current invalidation scope for task mutations** (line 36):
```python
_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]
```

`EntryType.STORIES` is absent.

### 3.2 Should MutationInvalidator Handle Story Invalidation?

**The question**: When a mutation event includes a section move (or any action that creates a story on Asana's side), should `MutationInvalidator` also invalidate `EntryType.STORIES`?

**Analysis**:

| Mutation Type | Creates Stories on Asana? | Should Invalidate `STORIES`? |
|---------------|--------------------------|------------------------------|
| `UPDATE` (field change) | Yes (e.g., `assignee_changed`, `due_date_changed`, `enum_custom_field_changed`) | Yes -- but low urgency (these stories are less critical for timelines) |
| `MOVE` (section change) | Yes (`section_changed`) | **Yes -- high urgency** (directly affects timeline data) |
| `CREATE` | Yes (`added_to_project`) | Low urgency (new task has no history) |
| `DELETE` | No new stories (task is gone) | No -- deleting STORIES entry is harmless cleanup |
| `ADD_MEMBER` / `REMOVE_MEMBER` | Yes (`added_to_project`, `removed_from_project`) | Medium urgency |

**The simplest change**: Add `EntryType.STORIES` to `_TASK_ENTRY_TYPES`:

```python
_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION, EntryType.STORIES]
```

This is a 1-line change that invalidates story caches on ALL task mutations. It is safe because:
1. Story cache invalidation is deletion (no race condition)
2. The next reader of stories will fetch fresh from API
3. The blast radius is bounded -- only the specific task's story entry is invalidated
4. MutationInvalidator already handles `CACHE_TRANSIENT_ERRORS` gracefully

**Tradeoff**: Invalidating stories on every task UPDATE (not just section moves) is slightly aggressive. Most field changes (name, assignee, custom fields) do create Asana system stories, but those stories are not critical for timeline computation (which only uses `section_changed`). However, the cost of over-invalidation is low: one extra API fetch the next time stories are needed. The cost of under-invalidation is stale timeline data.

### 3.3 MutationInvalidator Verdict

| Approach | Change Size | Blast Radius | Freshness Gain |
|----------|------------|--------------|----------------|
| Add `EntryType.STORIES` to `_TASK_ENTRY_TYPES` | 1 line | Low -- only invalidates on mutation | Moderate -- REST-initiated mutations trigger story invalidation |
| Add STORIES only for MOVE mutations | ~5 lines | Lower | Lower -- only section moves |
| Do nothing | 0 | None | None |

**Recommendation**: Add `EntryType.STORIES` to `_TASK_ENTRY_TYPES`. The over-invalidation cost is negligible; the simplicity is high.

---

## Part 4: Other Existing Infrastructure Opportunities

### 4.1 CacheInvalidator (SaveSession's Coordinator)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py`

Same pattern as MutationInvalidator but for SaveSession commits. Add `EntryType.STORIES` to the invalidation list at line 148:

```python
self._cache.invalidate(
    gid,
    [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION, EntryType.STORIES],
)
```

This ensures that when SaveSession commits any change to a task (including section moves, tag additions, field updates), the story cache for that task is invalidated.

**Effort**: 1 line.
**Reuses existing infrastructure**: Yes -- CacheInvalidator already exists, already handles transient errors, already runs at Phase 1.5.

### 4.2 Webhook Handler (Inbound)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/webhooks.py`

The inbound webhook handler already invalidates TASK, SUBTASKS, and DETECTION entries when it receives a task payload with a newer `modified_at` timestamp (line 182-257, `invalidate_stale_task_cache()`).

```python
_TASK_ENTRY_TYPES = [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION]
```

Same pattern: add `EntryType.STORIES`. When Asana Rules fire and POST a task payload to our webhook, we also invalidate that task's story cache.

**Effort**: 1 line.
**Reuses existing infrastructure**: Yes -- `invalidate_stale_task_cache()` already does versioned comparison and conditional invalidation.

### 4.3 Derived Timeline Cache TTL

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py`

The derived timeline cache has a 5-minute TTL (`_DERIVED_TIMELINE_TTL = 300`). When underlying story caches are invalidated (via the changes proposed above), the derived timeline will still serve stale data for up to 5 minutes.

**Option**: Invalidate the derived timeline cache key when any task in that project has its story cache invalidated.

**Assessment**: This requires knowing which project a task belongs to at invalidation time, and which (project_gid, classifier_name) derived entries depend on that task. This is a reverse-index problem that does not exist today. The effort is moderate (need to build the reverse mapping) and the benefit is marginal (5 minutes of staleness is acceptable for day-counting analytics).

**Recommendation**: Do NOT add derived timeline invalidation. The 5-minute TTL is sufficient. The next request after TTL expiry will recompute from fresh story data.

### 4.4 `max_cache_age_seconds` Parameter Tuning

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py` (line 158)

The `max_cache_age_seconds` parameter on `load_stories_incremental()` controls whether a cached story entry is served without an API call. Currently used at:
- Lambda warmer: `max_cache_age_seconds=7200` (2 hours)
- `build_timeline_for_offer()`: `max_cache_age_seconds=7200` (2 hours)
- Self-healing in `get_or_compute_timelines()`: Not set (default = always fetch)

**Opportunity**: If we add story invalidation to the mutation paths (CacheInvalidator, MutationInvalidator, webhook handler), the story cache entries for recently-mutated tasks will be deleted. The next `list_for_task_cached_async()` call will see a cache miss and fetch fresh. The `max_cache_age_seconds` parameter becomes less critical because invalidation handles proactive freshness.

**Recommendation**: No tuning needed. The invalidation-based approach makes `max_cache_age_seconds` a secondary concern. Keep current values as-is.

### 4.5 EntityWriteRegistry / FieldWriteService

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/field_write_service.py`

`FieldWriteService.write_async()` already emits a `MutationEvent` with `MutationType.UPDATE` and fires cache invalidation via `MutationInvalidator`. If we add `EntryType.STORIES` to `MutationInvalidator._TASK_ENTRY_TYPES`, the entity write endpoint automatically gets story invalidation for free. No changes needed in `FieldWriteService`.

**Effort**: 0 (inherited from MutationInvalidator change).

### 4.6 Lifecycle Engine / CascadingSectionService

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/sections.py`

`CascadingSectionService._move_to_section_async()` calls `self._client.sections.add_task_async(section_gid, task=entity.gid)` directly -- it does NOT go through SaveSession. This is a direct API call that creates a `section_changed` story on Asana's side.

This path does NOT trigger any cache invalidation today. It is a blind spot.

**Options**:
1. Refactor to use SaveSession (would get invalidation for free, but is a larger change)
2. Add fire-and-forget story invalidation after the `add_task_async` call
3. Accept the gap (lifecycle transitions are infrequent and Lambda warmer covers them)

**Assessment**: Lifecycle transitions (Outreach -> Sales -> Onboarding -> Implementation) are relatively infrequent events (a handful per day). The Lambda warmer runs frequently enough that the 2-hour freshness window is acceptable. Adding invalidation here is low-value relative to the mutation-path changes above.

**Recommendation**: Accept the gap for now. If lifecycle-triggered section changes become more frequent, add story invalidation here. Tag as a known low-priority item.

---

## Part 5: Ranked Recommendations (Reuse-First, Anti-Overengineering)

### Tier 1: Trivial Changes (Reuse Existing Infrastructure, Minutes of Work)

| # | Change | File | Effort | Freshness Gain | Reuses |
|---|--------|------|--------|----------------|--------|
| R1 | Add `EntryType.STORIES` to `MutationInvalidator._TASK_ENTRY_TYPES` | `cache/integration/mutation_invalidator.py:36` | 1 line | REST mutations (entity write, task update) invalidate story cache | MutationInvalidator |
| R2 | Add `EntryType.STORIES` to `CacheInvalidator._invalidate_entity_caches()` | `persistence/cache_invalidator.py:148` | 1 line | SaveSession commits (including `move_to_section`) invalidate story cache | CacheInvalidator |
| R3 | Add `EntryType.STORIES` to webhook handler `_TASK_ENTRY_TYPES` | `api/routes/webhooks.py:39` | 1 line | Inbound webhook notifications invalidate story cache | Webhook handler |

**Combined effect of R1 + R2 + R3**: Every known mutation path in the system (SaveSession, REST routes, webhooks) invalidates story caches as a side effect. When a section move happens through any path, the affected task's story cache is deleted. The next time anyone reads stories for that task (Lambda warmer, self-healing, or direct client call), they get fresh data from the Asana API.

**Total effort**: 3 lines of code. Zero new infrastructure. Zero new abstractions.

### Tier 2: Already Shipped (Existing Mechanisms, No Changes Needed)

| # | Mechanism | Coverage |
|---|-----------|----------|
| Existing | Lambda story warming (bulk, scheduled) | Repopulates all story caches on each Lambda run. Covers the base case for ~3,800+ entities. |
| Existing | Bounded self-healing (reactive, request-time) | Catches up to 50 cache misses per timeline request. Covers new offers and small gaps. |

These two mechanisms are already in production and provide the bulk of story freshness. The Tier 1 changes above close the gap between "mutation happens" and "next Lambda run."

### Tier 3: Considered and Rejected

| # | Idea | Why Rejected |
|---|------|-------------|
| R4 | Fire-and-forget story FETCH in SaveSession after section move | Race condition with Asana's async story creation. Would cache stale data with a fresh timestamp. Worse than cache miss. |
| R5 | Derived timeline cache invalidation on story invalidation | Requires reverse-index mapping (task -> project -> derived key). 5-minute TTL is sufficient. Disproportionate complexity for marginal gain. |
| R6 | Story invalidation in CascadingSectionService | Lifecycle transitions are infrequent. Lambda warmer covers them within 2 hours. Low ROI. |
| R7 | New background task for story warming in ECS | Multi-replica API call amplification. Rate limit contention with request handling. |
| R8 | Webhook registration for Asana story creation events | Massive infrastructure investment (webhook management, HMAC verification, backfill). Correct long-term architecture but disproportionate to current problem. |
| R9 | Post-commit hook in SaveSession that schedules delayed story fetch | Requires timer/scheduler infrastructure, adds complexity to SaveSession, and still has race condition risk (delay must be long enough for Asana, but too-long delays have their own problems). |

---

## Part 6: What NOT to Do (Anti-Patterns and Bespoke Traps)

### Anti-Pattern 1: Write-Through Story Caching on Section Move

**Trap**: "When we move a task to a section, immediately fetch and cache the stories."

**Why it is wrong**: Asana creates the `section_changed` story asynchronously after the `addTask` API call returns. Immediately fetching stories returns the pre-move list. You cache stale data with a fresh timestamp. The `max_cache_age_seconds` check on subsequent reads sees the fresh entry and skips the API call, serving stale data for hours. This is ACTIVELY HARMFUL -- worse than no caching at all.

### Anti-Pattern 2: Building a Story Invalidation Pub/Sub System

**Trap**: "We should build an event bus where mutations publish events and a story cache subscriber consumes them."

**Why it is wrong**: We already have two invalidation services (`CacheInvalidator`, `MutationInvalidator`) that do exactly this. Adding a third indirection layer (pub/sub) is overengineering. The existing services are called from known call sites. A 1-line change to each achieves the same result without new abstractions.

### Anti-Pattern 3: Story Cache TTL Micromanagement

**Trap**: "We should tune story cache TTLs per entity type -- offers get 30 minutes, units get 2 hours, contacts get 1 hour."

**Why it is wrong**: The current TTL is the CacheEntry default (300 seconds / 5 minutes for Redis hot tier, no expiry for S3 cold tier). The Lambda warmer writes entries every run. The invalidation changes above force re-fetch on mutation. TTL micromanagement adds configuration complexity with no measurable freshness improvement.

### Anti-Pattern 4: Coupling Timeline Logic into SaveSession

**Trap**: "SaveSession should know that section moves affect timelines and proactively warm timeline data."

**Why it is wrong**: SaveSession is a persistence coordinator. It should not know about domain-specific consumers of its mutations. Cache invalidation (deleting stale entries) is a persistence concern. Timeline computation is a service concern. SaveSession already delegates invalidation to CacheInvalidator -- that is the correct boundary. Adding timeline-specific logic to SaveSession violates SRP and creates a coupling that will be regretted when the next consumer of section stories appears.

### Anti-Pattern 5: Creating a Dedicated "StoryCacheManager" Service

**Trap**: "We need a new service that coordinates story cache lifecycle: warming, invalidation, TTL management, and freshness monitoring."

**Why it is wrong**: The story cache lifecycle is already distributed across existing services that each own one phase:
- **Writing**: `StoriesClient.list_for_task_cached()` -> `load_stories_incremental()`
- **Bulk warming**: Lambda `_warm_story_caches_for_completed_entities()`
- **Request-time healing**: `get_or_compute_timelines()` bounded self-healing
- **Invalidation**: `CacheInvalidator` (SaveSession) + `MutationInvalidator` (REST) + webhook handler

A new coordinating service would duplicate these responsibilities without adding capability. The right fix is to ensure each existing service handles `EntryType.STORIES` consistently -- which is exactly what Tier 1 recommendations achieve with 3 lines of code.

---

## Summary

The user's question -- "Should SaveSession fire-and-forget story cache writes when pushing section changes?" -- has a nuanced answer:

**No to writes, yes to invalidation.**

Fire-and-forget story WRITES (fetching stories after a section move) are dangerous due to the race condition with Asana's asynchronous story creation. But fire-and-forget story INVALIDATION (deleting the stale cache entry) is safe, trivial, and effective. The next reader (Lambda warmer, self-healing, or direct client) fetches fresh data.

The recommended changes are 3 lines of code across 3 files, all reusing existing infrastructure:
1. `MutationInvalidator._TASK_ENTRY_TYPES` += `EntryType.STORIES`
2. `CacheInvalidator._invalidate_entity_caches()` entry types += `EntryType.STORIES`
3. Webhook handler `_TASK_ENTRY_TYPES` += `EntryType.STORIES`

Combined with the existing Lambda warming and bounded self-healing mechanisms, this closes the freshness gap without creating any new infrastructure, services, or abstractions.

---

## Part 7: Addendum -- Reassessing Invalidation Strategy for Incremental Fetch Preservation

**Context**: The original R1-R3 recommendations proposed adding `EntryType.STORIES` to the hard-deletion lists in MutationInvalidator, CacheInvalidator, and the webhook handler. Critical feedback identified that hard deletion destroys the incremental fetch capability of `load_stories_incremental()`, which uses the `since` parameter to fetch only new stories since `last_fetched`. This addendum reassesses the tradeoffs.

### 7.1 The Cost of Hard Deletion That Parts 1-6 Underestimated

`load_stories_incremental()` (`cache/integration/stories.py:102`) implements a cursor-based incremental fetch pattern per ADR-0020:

```
1. Read cached entry -> extract metadata["last_fetched"] timestamp
2. Pass last_fetched as "since" to Asana API -> receive only stories created AFTER that time
3. Merge new stories with cached (dedupe by GID)
4. Write merged result back to cache with updated last_fetched
```

For a typical offer with 50 stories accumulated over 6 months, the incremental path fetches 0-2 new stories per cycle. The full-fetch path fetches all 50. Across 3,800 offers, the difference is:

| Scenario | API Response Size | API Calls | Practical Impact |
|----------|-------------------|-----------|------------------|
| Incremental (cache hit) | ~0-2 stories per task | Same count, much smaller payloads | Lambda story warming completes faster, lower rate-limit pressure |
| Full fetch (cache miss) | ~50 stories per task | Same count, 25x larger payloads | Lambda story warming takes longer, heavier rate-limit consumption |
| Cached + fresh (max_cache_age_seconds skip) | 0 (no API call) | 0 | Best case: served from cache |

Hard-deleting the story cache entry (as R1-R3 proposed) converts every post-mutation fetch from the incremental path to the full-fetch path. This is not catastrophic -- the Lambda warmer and self-healing still function -- but it destroys a non-trivial optimization that ADR-0020 was specifically designed to provide.

The key insight: **the existing story data in the cache is not wrong after a mutation. It is merely incomplete.** A `section_changed` story was created on Asana's side, but the cached list of 50 stories is still valid -- it just needs 1 more appended. The incremental fetch does exactly this. Hard deletion discards the 50 good stories to force re-fetching all 51.

### 7.2 Three-Option Analysis: Hard Deletion vs. Soft Invalidation vs. No Invalidation

#### Option A: Hard Deletion (Original R1-R3)

Add `EntryType.STORIES` to `cache.invalidate()` calls in all three sites.

**Mechanism**: `TieredCacheProvider.invalidate()` (`cache/providers/tiered.py:411`) deletes the entry from both Redis and S3.

**Pros**:
- Simple (3 x 1-line changes)
- Guarantees next reader gets fresh data from API
- No new infrastructure

**Cons**:
- Destroys `metadata["last_fetched"]` cursor -- next fetch is full (no `since`)
- Destroys cached story list -- incremental merge cannot run
- For Lambda warmer with `max_cache_age_seconds=7200`, the deleted entry becomes a cache miss, triggering a full fetch
- Net API payload increase proportional to average story count per task

**Verdict**: Correct for freshness but wasteful. Appropriate ONLY for create/delete mutations where the cached data is structurally invalid (e.g., task deleted, task added to new project).

#### Option B: Soft Invalidation via FreshnessStamp

Mark the story entry stale without deleting it. The next reader sees the staleness hint and performs an incremental fetch (using the preserved `since` cursor).

**Mechanism**: `MutationInvalidator._soft_invalidate_entity_entries()` (`mutation_invalidator.py:257`) already implements this pattern: reads entry, calls `entry.freshness_stamp.with_staleness_hint(hint)`, writes back.

**Infrastructure gap -- two blockers**:

1. **Story entries have no FreshnessStamp**: `_create_stories_entry()` (`stories.py:179`) creates a `CacheEntry` without setting `freshness_stamp`. The soft invalidation code path in `_soft_invalidate_entity_entries()` checks `if entry.freshness_stamp is None` and falls back to hard invalidation (line 272-274). So enabling soft invalidation today would result in hard deletion for all story entries anyway.

2. **`load_stories_incremental()` does not check staleness_hint**: Even if story entries had a FreshnessStamp with a staleness_hint, nothing in the incremental fetch flow reads it. The function checks only:
   - `cached_entry is None` -> full fetch
   - `last_fetched is None` -> full fetch
   - `max_cache_age_seconds` vs `cached_at` -> skip API call if fresh enough

   There is no branch for "entry has staleness_hint, therefore bypass the `max_cache_age_seconds` short-circuit and do incremental fetch."

**What would need to change to make Option B work**:

```python
# Change 1: _create_stories_entry() must set freshness_stamp
# (stories.py:197)
from autom8_asana.cache.models.freshness_stamp import FreshnessStamp, VerificationSource

return CacheEntry(
    key=task_gid,
    data={"stories": stories},
    entry_type=EntryType.STORIES,
    version=version_dt,
    cached_at=now,
    metadata={"last_fetched": format_version(now)},
    freshness_stamp=FreshnessStamp.now(source=VerificationSource.API_FETCH),  # NEW
)

# Change 2: load_stories_incremental() must check staleness_hint
# (stories.py, between the max_cache_age_seconds check and the incremental fetch)
# If entry has staleness_hint, bypass the age check and proceed to incremental fetch
if cached_entry.freshness_stamp is not None and cached_entry.freshness_stamp.is_soft_invalidated():
    # Entry was soft-invalidated -- do incremental fetch regardless of age
    pass  # fall through to incremental fetch below
elif max_cache_age_seconds is not None and cached_entry.cached_at is not None:
    cache_age = (datetime.now(UTC) - cached_entry.cached_at).total_seconds()
    if cache_age <= max_cache_age_seconds:
        cached_stories = _extract_stories_list(cached_entry.data)
        return cached_stories, cached_entry, True

# Change 3: MutationInvalidator/CacheInvalidator/webhook must soft-invalidate
# EntryType.STORIES instead of hard-deleting
# This is the "add to list" change, but using soft_invalidate instead of invalidate
```

**Pros**:
- Preserves `metadata["last_fetched"]` and cached story list
- Next fetch is incremental (uses `since` cursor)
- Staleness is signaled explicitly -- no ambiguity about whether data might be stale
- Infrastructure (FreshnessStamp, staleness_hint, with_staleness_hint) already exists
- Pattern already proven for TASK/SUBTASKS/DETECTION in MutationInvalidator

**Cons**:
- Requires 3 changes (FreshnessStamp on stories, staleness check in incremental loader, soft-invalidate in mutation paths) vs. 1 line for hard deletion
- Introduces a new obligation: every code path that creates story cache entries must set FreshnessStamp
- The `load_stories_incremental()` change is a behavioral modification to a critical function -- needs careful testing
- Race condition from Part 2.5 still applies: if the Asana story has not been created yet, the incremental fetch returns 0 new stories and clears the staleness hint. This is equivalent to "I checked, nothing new" -- technically correct at that instant, but the story appears moments later

**Verdict**: Architecturally correct but requires more work than the original R1-R3 and introduces the same race condition risk (mitigated by the Lambda warmer covering the gap on its next cycle).

#### Option C: No Story Invalidation At All

Leave story invalidation lists untouched. Rely entirely on Lambda warming and self-healing.

**Mechanism**: Status quo. No changes.

**Pros**:
- Zero risk of regression
- Lambda warmer already handles bulk freshness
- Self-healing covers small gaps
- `max_cache_age_seconds=7200` means Lambda warmer skips recent entries, limiting redundant API calls

**Cons**:
- The freshness gap between "mutation happens" and "next Lambda run" remains (up to 2 hours)
- If Lambda is delayed or fails, staleness persists until self-healing triggers on request
- The blindspot documented in Part 2.2 remains

**Verdict**: Acceptable if the 2-hour staleness window is tolerable for the business. For section timelines (day-counting analytics), a 2-hour lag rarely changes the displayed value. The user would need to make a section move AND request the timeline for the same offer within 2 hours AND have the Lambda warmer not run in that window.

### 7.3 `modified_at` Probe Checks for Freshness Detection

The webhook handler (`webhooks.py:182-256`) demonstrates a probe pattern: read `EntryType.TASK` from cache, compare its `version` (which stores `modified_at`) against the inbound `modified_at`. If inbound is newer, invalidate.

Could this pattern be applied to stories? The question is: **can we detect, without fetching stories, that a task's stories are stale?**

**Analysis**:

The `modified_at` timestamp on a task updates when the task itself changes (field edits, section moves, completion). When `modified_at` is newer than the story cache entry's `version`, we know the task has been touched since the stories were last cached. This is a strong signal that new stories might exist.

However, there is a subtlety: `_create_stories_entry()` (`stories.py:195`) sets `version` from `current_modified_at` (which is the task's `modified_at` at fetch time). If the task was modified after the stories were cached but before the next probe, `cached_entry.version < current_modified_at` is true. This correctly identifies staleness.

**Where this could be used**:

1. **In `load_stories_incremental()` itself**: Before the `max_cache_age_seconds` short-circuit, if `current_modified_at` is provided and is newer than `cached_entry.version`, bypass the age check and proceed to incremental fetch. This already has the parameter (`current_modified_at`) but currently uses it only for the version field of the NEW cache entry -- not for comparison against the existing entry.

   ```python
   # Proposed check (conceptual, before the max_cache_age_seconds block):
   if current_modified_at is not None and cached_entry.is_stale(current_modified_at):
       # Task was modified since stories were cached -- do incremental fetch
       pass  # fall through to incremental fetch
   ```

   This is elegant because it requires no new infrastructure. The `current_modified_at` parameter already exists. `CacheEntry.is_stale()` already exists. The incremental fetch preserves the `since` cursor.

2. **In `read_cached_stories()` and `read_stories_batch()`**: These pure-read functions could accept an optional `modified_at` to compare against and return `None` (cache miss) when stale. But these functions are deliberately pure reads (no API calls), so signaling staleness would require the caller to handle the "stale but present" state -- adding complexity at the call site.

**Limitation**: The `modified_at` probe requires the caller to ALREADY HAVE the task's current `modified_at`. In the Lambda warmer, this is available (from the warmed DataFrame). In self-healing (`get_or_compute_timelines()`), it is NOT readily available -- the function works from task GIDs, not task objects. Adding a `modified_at` lookup step would require an additional cache read or API call per task, negating the probe's benefit.

**Verdict**: The `modified_at` probe in `load_stories_incremental()` is a valuable low-cost optimization for callers that already have `current_modified_at` (Lambda warmer, direct `list_for_task_cached_async` calls with task context). It is NOT useful for the batch read path (`read_stories_batch`) or self-healing path where `modified_at` is not readily available.

### 7.4 Revised Recommendation: Hybrid Strategy

The original R1-R3 was correct that the `EntryType.STORIES` blindspot should be addressed, but incorrect in prescribing hard deletion as the uniform mechanism. The revised recommendation uses a graduated approach that matches invalidation strategy to mutation type:

#### R1-revised: Differentiated Invalidation by Mutation Type

| Mutation Type | Story Impact | Recommended Action | Rationale |
|---------------|-------------|-------------------|-----------|
| `UPDATE` (field change) | New story created (e.g., assignee_changed) | Soft invalidation OR `modified_at` probe | Cached stories are still valid; incremental fetch appends 1 story |
| `MOVE` (section change) | New `section_changed` story | Soft invalidation OR `modified_at` probe | Same as UPDATE -- data is incomplete not invalid |
| `CREATE` (new task) | `added_to_project` story | No invalidation needed | New task has no prior story cache entry |
| `DELETE` (task removal) | No new stories | Hard deletion | Cache entry for a deleted task is structural garbage |
| `ADD_MEMBER` / `REMOVE_MEMBER` | Membership stories | Soft invalidation if entry exists, no-op if miss | Same incremental pattern |

#### R2-revised: `modified_at` Probe in `load_stories_incremental()`

Add a `current_modified_at` comparison check before the `max_cache_age_seconds` short-circuit in `load_stories_incremental()`. When the caller provides `current_modified_at` and the cached entry is stale relative to it, bypass the age check and proceed to incremental fetch.

This is the **highest-value, lowest-risk change** because:
- It requires no changes to any invalidation path (CacheInvalidator, MutationInvalidator, webhook)
- It preserves the `since` cursor and cached stories
- It uses existing infrastructure (`CacheEntry.is_stale()`, `current_modified_at` parameter)
- It automatically handles any mutation type that updates `modified_at` (which is all of them)
- The incremental fetch that follows handles the Asana race condition gracefully: if the new story is not yet visible, the fetch returns 0 new stories and the cache is updated with a fresh `last_fetched` timestamp. On the NEXT call, the `since` cursor picks up the story.

**Estimated effort**: ~5 lines in `load_stories_incremental()`. Zero infrastructure changes.

**Call-site compatibility**: All callers that already pass `current_modified_at` get the benefit automatically. Callers that pass `None` (the default) get no change in behavior. This is a fully backward-compatible enhancement.

#### R3-revised: FreshnessStamp on Story Entries (Deferred)

Adding `FreshnessStamp` to story cache entries and making `load_stories_incremental()` aware of `staleness_hint` is architecturally sound but should be DEFERRED until:
- The `modified_at` probe (R2-revised) has been shipped and observed in production
- There is a concrete use case where soft invalidation provides value BEYOND what the `modified_at` probe delivers
- The `SoftInvalidationConfig` on MutationInvalidator is enabled for other entry types, establishing the pattern

This avoids building infrastructure ahead of demonstrated need.

#### R4-revised: Hard Deletion for DELETE Mutations Only

Add `EntryType.STORIES` to the hard-invalidation path for `MutationType.DELETE` events only. When a task is deleted, its story cache entry is structural garbage. Hard deletion is correct here because there is no future incremental fetch -- the task no longer exists.

This is a targeted addition to `MutationInvalidator._handle_task_mutation()` (not to the global `_TASK_ENTRY_TYPES` list).

### 7.5 Generalizability to Other Entry Types

The tension between "invalidation for freshness" and "preservation for incremental optimization" is specific to `EntryType.STORIES`. Other entry types do not exhibit this tension:

| Entry Type | Has Incremental Fetch? | Hard Deletion Cost | Verdict |
|------------|----------------------|-------------------|---------|
| `TASK` | No (single entity, always full fetch) | Low (one API call to re-fetch) | Hard deletion is fine |
| `SUBTASKS` | No (always full list) | Low | Hard deletion is fine |
| `DETECTION` | No (computed from task data) | Low (recomputed on next access) | Hard deletion is fine |
| `STORIES` | **Yes** (`since` parameter, merge) | **Medium** (full re-fetch of all stories) | **Soft invalidation or probe preferred** |
| `DATAFRAME` | No (full recomputation) | Medium but necessary | Hard deletion is fine (different cache tier) |
| `PROJECT` | No (single entity) | Low | Hard deletion is fine |
| `SECTION` | No (single entity) | Low | Hard deletion is fine |
| `DERIVED_TIMELINE` | No (recomputed from stories) | Low (5-min TTL, recomputed on miss) | Hard deletion is fine |

The incremental fetch pattern is unique to stories because of the Asana `since` parameter on `GET /tasks/{task_gid}/stories`. No other Asana list endpoint supports a `since`-style cursor in our usage. Therefore, the soft invalidation concern is specific to `EntryType.STORIES` and does not need to be generalized to a system-wide pattern.

However, if future entry types adopt a similar incremental/cursor pattern, the `modified_at` probe approach (R2-revised) is the most generalizable: compare the resource's `modified_at` against the cached entry's `version`, and on staleness, proceed to the entry-type-specific refresh strategy (incremental for stories, full for others). This requires no entry-type-specific invalidation logic in the mutation paths.

### 7.6 Part 7 Summary

| # | Recommendation | Effort | Preserves `since`? | New Infra? |
|---|---------------|--------|-------------------|------------|
| R1-revised | Differentiate invalidation by mutation type (soft for updates, hard for deletes) | Moderate (~15 lines) | Yes for updates | No (uses existing FreshnessStamp -- but requires FreshnessStamp on story entries first) |
| **R2-revised** | **`modified_at` probe in `load_stories_incremental()`** | **Low (~5 lines)** | **Yes** | **No** |
| R3-revised | FreshnessStamp on story entries (deferred) | Moderate (~10 lines) | Yes | No (exists, not wired) |
| R4-revised | Hard deletion for DELETE mutations only | Low (~5 lines) | N/A (task is gone) | No |

**Priority order**: R2-revised first (highest value, lowest risk, no infrastructure dependencies), then R4-revised (cleanup correctness), then R1-revised + R3-revised together if observed need arises.

The key architectural insight is that **the `modified_at` timestamp, which the caller often already has, is a sufficient freshness signal that avoids the invalidation-vs-preservation dilemma entirely.** The mutation paths do not need to touch story cache entries at all if the read path can detect staleness from `modified_at` and respond with an incremental fetch. This is a read-side solution to a write-side problem, and it preserves the `since` cursor that ADR-0020 was designed to provide.

---

## File Reference

| File | Role | Line(s) |
|------|------|---------|
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/mutation_invalidator.py` | MutationInvalidator -- REST route cache invalidation | 36 (`_TASK_ENTRY_TYPES`) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py` | CacheInvalidator -- SaveSession commit invalidation | 148 (entry types list) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/webhooks.py` | Webhook inbound handler -- task cache invalidation | 39 (`_TASK_ENTRY_TYPES`) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/session.py` | SaveSession -- unit-of-work coordinator | 1260 (`move_to_section`), 886-921 (CRUD + actions + invalidation) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py` | Story cache read/write primitives | 102 (`load_stories_incremental`), 35 (`read_cached_stories`), 62 (`read_stories_batch`) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/stories.py` | StoriesClient -- `list_for_task_cached` | 342-455 |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Lambda cache warmer -- story warming phase | 235-395 (`_warm_story_caches_for_completed_entities`) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` | Timeline service -- bounded self-healing | 444-475 (inline story fetch for cache misses) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/sections.py` | CascadingSectionService -- direct section moves | 202 (`add_task_async` call) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/field_write_service.py` | FieldWriteService -- entity write pipeline | 207-218 (MutationEvent emission) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` | Derived timeline cache -- 5-minute TTL | 31 (`_DERIVED_TIMELINE_TTL = 300`) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/mutation_event.py` | MutationEvent -- mutation type taxonomy | 14-55 |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py` | ECS startup -- no story warming at startup | 252-255 (comment about removal) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/freshness_stamp.py` | FreshnessStamp -- staleness_hint, soft invalidation support | 52-118 (FreshnessStamp class, with_staleness_hint) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/entry.py` | CacheEntry hierarchy -- RelationshipCacheEntry handles STORIES | 423-484 (RelationshipCacheEntry), 100-108 (CacheEntry fields) |
| `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/providers/tiered.py` | TieredCacheProvider -- invalidate deletes from both tiers | 411-435 (invalidate method) |
