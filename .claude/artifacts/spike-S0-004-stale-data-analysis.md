# Spike S0-004: Stale-Data Window Measurement

**Date**: 2026-02-04
**Author**: Principal Engineer (spike)
**Status**: Complete
**Scope**: Trace all mutation endpoints and determine which trigger cache invalidation and which do not.

---

## 1. Complete Mutation Endpoint Inventory

### 1.1 Task Mutations (`/api/v1/tasks`)

| # | Method | Endpoint | Handler | Cache Invalidation | Notes |
|---|--------|----------|---------|-------------------|-------|
| T1 | POST | `/api/v1/tasks` | `create_task` | **NO** | Creates via `client.tasks.create_async()` directly. No cache touch. |
| T2 | PUT | `/api/v1/tasks/{gid}` | `update_task` | **NO** | Updates via `client.tasks.update_async()` directly. No cache invalidation. |
| T3 | DELETE | `/api/v1/tasks/{gid}` | `delete_task` | **NO** | Deletes via `client.tasks.delete_async()` directly. Stale entry remains in cache. |
| T4 | POST | `/api/v1/tasks/{gid}/duplicate` | `duplicate_task` | **NO** | Duplicates via SDK. New task never enters cache; original stays untouched. |
| T5 | POST | `/api/v1/tasks/{gid}/tags` | `add_tag` | **NO** | Adds tag via SDK. Task cache entry not invalidated. |
| T6 | DELETE | `/api/v1/tasks/{gid}/tags/{tag_gid}` | `remove_tag` | **NO** | Removes tag via SDK. Task cache entry not invalidated. |
| T7 | POST | `/api/v1/tasks/{gid}/section` | `move_to_section` | **NO** | Moves task to section. Neither task cache nor section DataFrame invalidated. |
| T8 | PUT | `/api/v1/tasks/{gid}/assignee` | `set_assignee` | **NO** | Sets assignee via SDK. No cache invalidation. |
| T9 | POST | `/api/v1/tasks/{gid}/projects` | `add_to_project` | **NO** | Adds task to project. No cache or DataFrame invalidation. |
| T10 | DELETE | `/api/v1/tasks/{gid}/projects/{project_gid}` | `remove_from_project` | **NO** | Removes task from project. No cache invalidation. |

### 1.2 Project Mutations (`/api/v1/projects`)

| # | Method | Endpoint | Handler | Cache Invalidation | Notes |
|---|--------|----------|---------|-------------------|-------|
| P1 | POST | `/api/v1/projects` | `create_project` | **NO** | Creates project via SDK. No cache involved. |
| P2 | PUT | `/api/v1/projects/{gid}` | `update_project` | **NO** | Updates project via SDK. No cache invalidation. |
| P3 | DELETE | `/api/v1/projects/{gid}` | `delete_project` | **NO** | Deletes project. Cached DataFrames keyed by project_gid become orphaned. |
| P4 | POST | `/api/v1/projects/{gid}/members` | `add_members` | **NO** | Adds members via SDK. No cache impact. |
| P5 | DELETE | `/api/v1/projects/{gid}/members` | `remove_members` | **NO** | Removes members. No cache impact. |

### 1.3 Section Mutations (`/api/v1/sections`)

| # | Method | Endpoint | Handler | Cache Invalidation | Notes |
|---|--------|----------|---------|-------------------|-------|
| S1 | POST | `/api/v1/sections` | `create_section` | **NO** | Creates section. Section DataFrames not aware. |
| S2 | PUT | `/api/v1/sections/{gid}` | `update_section` | **NO** | Renames section. Cached DataFrames have stale section name. |
| S3 | DELETE | `/api/v1/sections/{gid}` | `delete_section` | **NO** | Deletes section. Section parquet in S3 becomes orphaned. |
| S4 | POST | `/api/v1/sections/{gid}/tasks` | `add_task_to_section` | **NO** | Adds task to section. Section DataFrame not updated. |
| S5 | POST | `/api/v1/sections/{gid}/reorder` | `reorder_section` | **NO** | Reorders section. No cache impact (order not cached). |

### 1.4 Admin/Internal Mutations

| # | Method | Endpoint | Handler | Cache Invalidation | Notes |
|---|--------|----------|---------|-------------------|-------|
| A1 | POST | `/v1/admin/cache/refresh` | `refresh_cache` | **YES** | Explicit admin-initiated invalidation + rebuild. Full or incremental. |

### 1.5 SaveSession Commit Flow (SDK path, not REST API)

| # | Trigger | Handler | Cache Invalidation | Notes |
|---|---------|---------|-------------------|-------|
| SS1 | `session.commit_async()` | `CacheInvalidator.invalidate_for_commit()` | **YES** | Invalidates TASK, SUBTASKS, DETECTION entries for all succeeded entities. Also invalidates DataFrame caches via project membership lookup. |

---

## 2. Cache Invalidation Flow Diagram

```
                    ┌──────────────────────────────────────────────────────┐
                    │                  MUTATION SOURCES                     │
                    ├──────────────────────────────────────────────────────┤
                    │                                                      │
                    │  REST API Routes                  SDK SaveSession    │
                    │  (tasks.py, projects.py,          (session.py)       │
                    │   sections.py)                                       │
                    │       │                                │             │
                    │       │ NO invalidation               │ YES         │
                    │       │ (fire-and-forget              │ invalidation│
                    │       │  to Asana API)                │             │
                    │       ▼                                ▼             │
                    └──────────────────────────────────────────────────────┘
                                                            │
                                                            ▼
                                              ┌─────────────────────────┐
                                              │    CacheInvalidator     │
                                              │  (cache_invalidator.py) │
                                              └─────────────────────────┘
                                                      │           │
                                        ┌─────────────┘           └────────────┐
                                        ▼                                      ▼
                              ┌───────────────────┐              ┌──────────────────────┐
                              │ _invalidate_      │              │ _invalidate_         │
                              │ entity_caches()   │              │ dataframe_caches()   │
                              │                   │              │                      │
                              │ Invalidates:      │              │ Invalidates:         │
                              │ - EntryType.TASK  │              │ - EntryType.DATAFRAME│
                              │ - EntryType.      │              │   per project via    │
                              │   SUBTASKS        │              │   membership lookup  │
                              │ - EntryType.      │              │                      │
                              │   DETECTION       │              │                      │
                              └───────────────────┘              └──────────────────────┘
                                        │                                      │
                                        ▼                                      ▼
                              ┌───────────────────┐              ┌──────────────────────┐
                              │  TieredCache      │              │  cache/dataframes.py │
                              │  Provider          │              │  invalidate_task_    │
                              │  (Redis + S3)     │              │  dataframes()        │
                              └───────────────────┘              └──────────────────────┘


    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                          CACHE TIERS (NEVER TOUCHED BY REST)                    │
    │                                                                                 │
    │  Tier 1: UnifiedTaskStore (in-memory via CacheProvider)                         │
    │    - Task data, freshness, hierarchy                                            │
    │    - Invalidated: ONLY by SaveSession commit                                    │
    │                                                                                 │
    │  Tier 2: TieredCacheProvider (Redis hot + S3 cold)                              │
    │    - Task entries, subtask entries, detection entries                            │
    │    - Invalidated: ONLY by SaveSession commit                                    │
    │                                                                                 │
    │  Tier 3: DataFrameCache (in-memory + S3)                                        │
    │    - Full project DataFrames (Polars), keyed by project_gid+entity_type         │
    │    - Invalidated: ONLY by SaveSession commit OR admin/cache/refresh             │
    │                                                                                 │
    │  Tier 4: SectionPersistence (S3 parquet files)                                  │
    │    - Per-section parquet files, manifest.json                                   │
    │    - Invalidated: ONLY by admin/cache/refresh (force_full_rebuild)              │
    │    - NEVER invalidated by any mutation (task, section, or project)              │
    │                                                                                 │
    │  Tier 5: cache/dataframes.py (per-task-per-project computed rows)               │
    │    - Individual task DataFrame rows (task_gid:project_gid key)                  │
    │    - Invalidated: ONLY by SaveSession commit (via membership lookup)            │
    │                                                                                 │
    └─────────────────────────────────────────────────────────────────────────────────┘
```

### Lambda Handlers (Out-of-Band)

```
    cache_warmer Lambda              cache_invalidate Lambda
    ─────────────────────            ──────────────────────
    Populates DataFrameCache         Clears Redis + S3 task keys
    via ProgressiveProjectBuilder    Optionally clears DataFrameCache
    (periodic/on-demand)             (nuclear: all entries)
    Does NOT invalidate first        Does NOT invalidate DataFrames
    (relies on watermark freshness)  unless clear_dataframes=true
```

---

## 3. Gap Analysis

### Gap G1: REST Task Mutations Leave ALL Cache Tiers Stale
**Affected Endpoints**: T1-T10 (all 10 task mutation endpoints)
**Affected Cache Tiers**: All 5 tiers

When a user calls `PUT /api/v1/tasks/{gid}` to update a task name, the Asana API is updated but:
- The `UnifiedTaskStore` still holds the old task data
- The `TieredCacheProvider` (Redis/S3) still holds the old entry
- The `DataFrameCache` still holds the old DataFrame row
- The `SectionPersistence` S3 parquet still has the old data
- The per-task `cache/dataframes.py` entry still has the old computed row

**Stale window**: Until the next `SaveSession` commit touches the same task, OR the next Lambda cache warmer run, OR the cache TTL expires (TTL-dependent, could be hours).

### Gap G2: REST Section Mutations Leave Section DataFrames Stale
**Affected Endpoints**: S1-S4
**Affected Cache Tiers**: Tier 3 (DataFrameCache), Tier 4 (SectionPersistence)

When a section is renamed (`PUT /sections/{gid}`), created, or deleted:
- DataFrameCache rows referencing the section have stale section names
- SectionPersistence parquet files keyed by section_gid become orphaned (delete) or missing (create)
- Task-to-section membership changes (S4) leave the section DataFrame incomplete

**Stale window**: Until the next cache warmer run or admin cache refresh.

### Gap G3: REST Project Mutations Leave DataFrameCache Orphaned
**Affected Endpoints**: P2, P3
**Affected Cache Tiers**: Tier 3 (DataFrameCache), Tier 4 (SectionPersistence)

When a project is deleted:
- DataFrameCache entries keyed by project_gid become orphaned (never cleaned up)
- SectionPersistence parquet files under that project_gid prefix remain in S3

**Stale window**: Permanent (orphaned entries) until admin cache refresh or S3 lifecycle policy.

### Gap G4: Task Creation via REST Never Warms Cache
**Affected Endpoint**: T1 (POST /tasks)
**Affected Cache Tiers**: All tiers

When a task is created via the REST API, the new task is never written into any cache tier. This means:
- Immediately reading the task via a cached path will miss
- The DataFrameCache for the task's project is unaware of the new task
- The resolver service cannot find the new task until the next cache warm

**Stale window**: Until the next cache warmer run covers the task's project.

### Gap G5: Section Move (T7) Creates Cross-Section Inconsistency
**Affected Endpoint**: T7 (POST /tasks/{gid}/section)
**Affected Cache Tiers**: Tier 3 (DataFrameCache), Tier 4 (SectionPersistence)

Moving a task between sections affects TWO section DataFrames:
- The source section DataFrame still includes the moved task
- The destination section DataFrame does not include the moved task

**Stale window**: Until the next cache warmer run rebuilds both sections.

### Gap G6: SaveSession Invalidation Requires Membership Data
**Affected**: `CacheInvalidator._invalidate_dataframe_caches()`

The SaveSession invalidator depends on `entity.memberships` being populated to find project_gids for DataFrame invalidation. If the entity was loaded without `memberships` in `opt_fields`, DataFrame invalidation is silently skipped. This is a partial gap in the SaveSession path itself.

---

## 4. Severity Ranking

| Gap | Severity | User Impact | Frequency | Stale Window |
|-----|----------|------------|-----------|--------------|
| **G1** | **CRITICAL** | Users see outdated task data after REST mutations. Task name/status/assignee changes appear lost until TTL expiry or next warm. External API consumers (other services) get stale data from resolver and query endpoints. | Every REST mutation (highest-traffic path) | Minutes to hours (TTL-dependent) |
| **G5** | **HIGH** | Tasks appear in wrong sections after move operations. Dashboard views show inconsistent section membership. | Every section move via REST | Hours (until next cache warm) |
| **G4** | **HIGH** | Newly created tasks are invisible to query/resolver until next cache warm. API consumers cannot find tasks they just created. | Every task creation via REST | Hours (until next cache warm) |
| **G2** | **MEDIUM** | Section renames show stale names in DataFrames. Deleted sections leave ghost entries. New sections have no cached data. | Section management operations | Hours (until next cache warm) |
| **G6** | **MEDIUM** | SaveSession commits that lack membership data silently skip DataFrame invalidation. Partially defeats the one path that DOES invalidate. | When entities loaded with minimal opt_fields | Variable (depends on entity load pattern) |
| **G3** | **LOW** | Orphaned cache entries for deleted projects consume storage. No direct user impact unless storage limits hit. | Project deletion (rare) | Permanent until manual cleanup |

---

## 5. Recommendations for A1 Implementation Priority

### Phase 1: REST Route Invalidation Middleware (Addresses G1, G4, G5)

**Priority**: Immediate -- this is the highest-impact gap.

**Approach**: Add a post-mutation hook or middleware to REST API routes that triggers cache invalidation after successful write-through to Asana.

Recommended design:
1. Create `MutationInvalidator` service that accepts (entity_type, gid, operation, project_context)
2. Wire it into task/section/project routes as a FastAPI dependency or response hook
3. For task mutations: invalidate `TASK`, `SUBTASKS`, `DETECTION` entries in `UnifiedTaskStore` and `TieredCacheProvider`
4. For task mutations with known project context: invalidate `DataFrameCache` per-task entry
5. For section moves: invalidate both source and destination section DataFrames
6. For task creation: optionally warm the new task into cache

**Complexity**: Medium. The `CacheInvalidator` already has the right logic -- it just needs to be callable from outside `SaveSession`.

### Phase 2: Section & Project Invalidation (Addresses G2, G3)

**Priority**: Medium-term.

- Section rename/delete: Invalidate `DataFrameCache` for the section's parent project
- Section create: Mark `SectionPersistence` manifest as incomplete
- Project delete: Purge `DataFrameCache` entries and `SectionPersistence` files for that project

### Phase 3: Cross-Tier Freshness Unification (Addresses G6, relates to A2)

**Priority**: Later -- this is more architectural.

- Ensure all entity loads that feed into `SaveSession` include `memberships` in opt_fields
- Alternatively, make DataFrame invalidation look up memberships from the cache/API rather than relying on the entity object

### Sequencing

```
Phase 1 (G1, G4, G5)  ──>  Phase 2 (G2, G3)  ──>  Phase 3 (G6 + A2)
   [HIGH IMPACT]              [MEDIUM IMPACT]         [ARCHITECTURAL]
   ~2-3 days                  ~1-2 days                ~3-5 days
```

### Key Design Decision

The REST routes currently use `AsanaClientDualMode` which wraps the SDK client. The cache provider is accessible via `client._cache_provider` on the SDK client. The main question is whether to:

**(A)** Extract `CacheInvalidator` from `SaveSession` into a shared service that both `SaveSession.commit_async()` and REST routes can use, or

**(B)** Create a new `RESTMutationInvalidator` that uses `UnifiedTaskStore.invalidate()` directly (simpler, narrower scope).

Recommendation: Option (A). The existing `CacheInvalidator` already handles entity caches + DataFrame caches correctly. Extracting it as a shared service avoids duplicating that logic and ensures both paths stay in sync as new cache tiers are added.

---

## Summary

The A1 opportunity claim is **confirmed and understated**. Not only do REST task mutations never invalidate cache, but **zero** REST mutation endpoints across tasks, projects, and sections trigger any form of cache invalidation. The only paths that invalidate are:

1. `SaveSession.commit_async()` (SDK path, not REST)
2. `POST /v1/admin/cache/refresh` (admin manual trigger)
3. Lambda `cache_invalidate` handler (nuclear option)
4. Cache TTL expiry (passive, time-based)

This means any external consumer using the REST API (other microservices, the Satellite API) operates in a permanently stale-data window for all mutations until the next scheduled cache warm or TTL expiry.
