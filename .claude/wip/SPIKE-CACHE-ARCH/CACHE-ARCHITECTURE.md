# Cache Architecture: autom8y-asana — CACHE-REMEDIATION

**Date**: 2026-02-27
**Agent**: systems-thermodynamicist
**Session**: session-20260227-135243-55f4e4fa (CACHE-REMEDIATION)
**Upstream**: THERMAL-ASSESSMENT.md (heat-mapper, 2026-02-27)
**Scope**: F-1 (SaveSession DataFrameCache Gap) and F-2 (Derived Timeline Cache — Optional Enhancement)

---

## Architecture Overview

```
WRITE PATH (SaveSession)
========================

  SaveSession.commit()
       |
       v
  CacheInvalidator.invalidate_for_commit()
       |
       +---> _invalidate_entity_caches()          [System A: Redis/S3]
       |     TASK, SUBTASKS, DETECTION per GID
       |
       +---> _invalidate_dataframe_caches()       [System A: per-task DataFrame keys]
       |     invalidate_task_dataframes() per GID
       |
       +---> _invalidate_project_dataframes()     [System B: project-level DataFrameCache]  ← GAP (F-1)
             DataFrameCache.invalidate_project() per structural mutation

WRITE PATH (REST mutations — existing, unchanged)
=================================================

  MutationInvalidator.invalidate_async()
       |
       +---> _handle_task_mutation()
             |
             +---> System A entity entries (TASK, SUBTASKS, DETECTION)
             +---> System A per-task DataFrame entries (if project_gids known)
             +---> System B DataFrameCache.invalidate_project()
                   (only for CREATE, DELETE, MOVE, ADD_MEMBER, REMOVE_MEMBER)

READ PATH (section-timeline API)
=================================

  GET /section-timelines/{project_gid}
       |
       v
  SectionTimelineResolver
       |
       v
  get_cached_timelines()     ← DerivedTimelineCacheEntry from Redis/S3
       |-- HIT: return in <2s
       |-- MISS: compute (~2-4s), then store_derived_timelines() with 300s TTL
```

The two CACHE-verdicted findings involve distinct layers:

- **CACHE-1** (F-1): Adds the missing third invalidation call in `CacheInvalidator._invalidate_dataframe_caches()` to reach System B (DataFrameCache). The first two calls (entity cache + per-task DataFrame) already exist and are correct.
- **CACHE-2** (F-2): Optional enhancement to `MutationInvalidator._handle_section_mutation()` to push derived timeline invalidation on section mutations. Currently deferred pending business owner confirmation that 300s TTL is insufficient.

---

## Layer Designs

### Layer: DataFrameCache Project-Level Invalidation (CACHE-1 / F-1)

#### Pattern

- **Selected**: Write-through invalidation (extend existing cache-aside path with invalidation side effect)
- **Rationale**: The DataFrameCache already uses cache-aside for reads (resolution strategies call `get_or_build_async()`). The write path (SaveSession) must issue an invalidation signal after structural mutations to ensure subsequent reads rebuild from the Asana source. This is not a new cache pattern — it is completing an existing invalidation chain that was half-implemented.
- **Trade-off acknowledged**: The fix adds latency to `CacheInvalidator.invalidate_for_commit()` proportional to the number of structural mutations per commit. In practice, `DataFrameCache.invalidate_project()` is a synchronous memory eviction (removes entries from `MemoryTier` via `memory_tier.remove()`). S3 entries are not deleted — they are superseded on the next `put_async()`. The latency cost is negligible (O(n entities per project) dict removals).

#### Consistency Model

- **Selected**: Eventual consistency
- **CAP position**: AP (Availability + Partition Tolerance)
- **Staleness budget**: Zero tolerance for structural mutations (CREATE/DELETE/MOVE). The thermal assessment establishes that row-count errors in offer/contact DataFrames produce incorrect MRR figures. The consistency requirement is met by triggering immediate invalidation after commit — the next read triggers SWR rebuild from the Asana source.
- **Rationale**: AP is appropriate. The invalidation is fire-and-forget; if it fails, the existing TTL-based expiry provides a safety net (worst case: 9 min for offers, 45 min for contacts before natural staleness triggers rebuild). Choosing CP (fail the commit if invalidation fails) would violate the availability-first contract established across the codebase (NFR-DEGRADE-001, `MutationInvalidator` ADR-003, existing `CacheInvalidator` error handling).

#### Failure Mode Design

**Cache unavailable (DataFrameCache.invalidate_project() raises):**
- **Behavior**: Fail-open. Log warning with `project_dataframe_invalidation_failed`. Continue loop. Do not fail the commit.
- **Rationale**: The commit has already succeeded in Asana. Failing the commit response due to a cache invalidation failure would create a worse outcome: the Asana mutation is applied but the caller receives an error, leaving the system in an ambiguous state. The staleness window (up to entity TTL + SWR grace) is the accepted trade-off.
- **Recovery**: TTL-based expiry + SWR background rebuild provides automatic recovery within the entity's max staleness window.

**Origin unavailable (Asana API unreachable after invalidation):**
- **Behavior**: Invalidation succeeds (removes MemoryTier entries). Next read triggers SWR rebuild. SWR callback fails because Asana API is unreachable. Circuit breaker opens after 3 failures. LKG is served from MemoryTier or ProgressiveTier (S3) while circuit is open.
- **Rationale**: This is the correct degradation path. The LKG entry (pre-mutation data) is served during Asana downtime. This is preferable to serving no data at all. Note: LKG staleness is currently unbounded (F-3, deferred). The staleness risk during extended Asana outage is an acknowledged open item per the thermal assessment.

**Network partition (process cannot reach DataFrameCache tiers):**
- **Behavior**: MemoryTier is in-process; it is never unreachable due to network. ProgressiveTier (S3) may be unreachable. `DataFrameCache.invalidate_project()` only operates on MemoryTier synchronously — it does not touch S3. S3 entries are not deleted on invalidation; they are superseded on the next `put_async()`. Therefore a partition affecting S3 does not affect invalidation correctness. The partition only delays the SWR rebuild that would supersede the stale S3 entry.
- **Rationale**: Design is partition-tolerant by construction. S3 entries persist as cold fallback. MemoryTier invalidation is always local.

#### Structural Mutation Detection Strategy

`MutationInvalidator` receives a `MutationEvent` with an explicit `mutation_type` field. `CacheInvalidator` does not have this luxury — it receives a `SaveResult` that contains succeeded/failed entities without operation type classification per entity.

The decision is: **always invalidate project-level DataFrameCache on any succeeded entity in the commit batch**.

**Rationale for conservative approach over selective approach:**

1. `SaveResult.succeeded` contains entities that were committed to Asana. The operation type (CREATE/UPDATE/DELETE) is not surfaced in `SaveResult` — only the entity and its GID are in `succeeded`.
2. A pure field UPDATE (e.g., a custom field value change) does not change row count but does change row content. The DataFrameCache serves this data. Invalidating on field updates causes a rebuild that correctly reflects the update. The cost is one additional SWR rebuild per field-update commit cycle.
3. Attempting to infer operation type from entity state (checking if `entity.gid` is a "real" vs. "temp" GID to distinguish CREATE from UPDATE) is fragile and not the right layer to introduce that inference.
4. `MutationInvalidator` applies the structural-mutation filter because it has explicit `MutationType` context from the REST route handler. `CacheInvalidator` does not have that context.

**Alternative considered and rejected**: Extract operation type from `crud_result` by correlating entities to `PlannedOperation` list. Rejected because: (a) `CacheInvalidator.invalidate_for_commit()` does not receive the planned operations, only the results; (b) adding that parameter increases coupling to the SaveSession internals; (c) the cost of conservative invalidation (one extra SWR rebuild per commit) is negligible compared to the risk of missing a structural mutation invalidation.

**Conclusion**: Conservative blanket invalidation for all succeeded entities is correct for `CacheInvalidator`. This matches `MutationInvalidator`'s behavior for section mutations (which always invalidate project DataFrames regardless of mutation type).

#### Distributed Topology

Not applicable. `DataFrameCache` is a process-scoped composite cache (MemoryTier in-process, ProgressiveTier via S3). There is no distributed coordination layer. Invalidation is local to the process.

---

### Layer: Derived Timeline Cache (CACHE-2 / F-2)

#### Pattern

- **Selected**: TTL-based expiry (existing, accepted as correct design)
- **Optional enhancement**: Event-driven invalidation on section mutations via `MutationInvalidator._handle_section_mutation()`, if activated by business owner trigger
- **Rationale**: The 300s TTL is a deliberate, documented trade-off. For an analytical endpoint with historical date ranges, 5-minute staleness is within acceptable bounds. The `store_derived_timelines()` path already caches with `_DERIVED_TIMELINE_TTL = 300` and the comment in `derived.py` line 31 explicitly documents this as a freshness vs. computation cost balance.
- **Trade-off acknowledged**: Stale derived timelines (up to 5 minutes old) may be served to consumers of `GET /section-timelines`. For historical analytical queries this is immaterial. If near-real-time timeline freshness is required, the optional enhancement below provides the mechanism.

#### Consistency Model

- **Selected**: Eventual consistency (TTL-bounded)
- **CAP position**: AP
- **Staleness budget**: 300s (5 minutes) per `_DERIVED_TIMELINE_TTL`
- **Rationale**: Section timeline data is derived from story events (task section-change stories). Stories have their own cache freshness cycle. The derived timeline cache adds at most 300s of additional lag atop the story cache TTL. For the current analytical reporting use case, this is acceptable.

#### Failure Mode Design

**Cache unavailable (Redis/S3 unreachable for DERIVED_TIMELINE entries):**
- **Behavior**: Fail-open. `get_cached_timelines()` returns `None`. The section-timeline resolver recomputes (~2-4s) and attempts `store_derived_timelines()`. If the store also fails, the response is served from the fresh computation but the cache entry is not persisted. Next request recomputes again.
- **Rationale**: The cache is an optimization. Falling back to on-demand computation is the correct degradation path. The computation cost (~2-4s) is the accepted latency floor on cache miss.

**Origin unavailable (story cache empty or Asana unreachable):**
- **Behavior**: If the story cache is cold and Asana is unreachable, the timeline computation cannot proceed. The section-timeline API returns an error. There is no LKG fallback for derived timelines (unlike DataFrameCache which has LKG via MemoryTier). A stale DERIVED_TIMELINE entry in Redis/S3 would be served if TTL has not expired.
- **Rationale**: The 300s TTL provides a bounded staleness window during transient Asana outages. Extended outages beyond 300s will result in cache misses and computation failures. This is acceptable for an analytical endpoint.

**Network partition (cache unreachable during partition):**
- **Behavior**: Same as cache unavailable above. Computation path remains available if the story cache (Redis/S3) is reachable. The story cache is on the same Redis/S3 backend — a partition affecting derived timeline entries affects story entries equally.
- **Rationale**: Both caches share the same `CacheProvider` instance. A partition either takes both down or neither.

---

## Multi-Level Hierarchy

### System A / System B Relationship (Unchanged)

The two systems are intentionally independent per ADR-0067. This design does not change that relationship. The change adds a new call from `CacheInvalidator` into System B — this is a new coordination point, not a unification.

```
CacheInvalidator (SaveSession write path)
  |
  +---> System A invalidation (entity + per-task DataFrame)  [existing]
  +---> System B invalidation (project-level DataFrameCache) [NEW — CACHE-1]

MutationInvalidator (REST mutation write path)
  |
  +---> System A invalidation (entity + per-task DataFrame)  [existing]
  +---> System B invalidation (project-level DataFrameCache) [existing]
```

After CACHE-1 is implemented, both write paths have symmetric System B coverage. The divergence (ADR-0067) remains intentional at the read path (different data types, different TTL semantics, different tier compositions). Only the write path gains consistency.

---

## Invalidation Strategy

### Per-Layer

| Layer | Strategy | Trigger |
|-------|----------|---------|
| System A entity cache (TASK/SUBTASKS/DETECTION) | Event-driven hard eviction | SaveSession commit (existing) |
| System A per-task DataFrame (task_gid:project_gid) | Event-driven hard eviction | SaveSession commit (existing) |
| System B DataFrameCache (project-level, MemoryTier) | Event-driven hard eviction | SaveSession commit (NEW) |
| System B DataFrameCache (ProgressiveTier/S3) | Superseded on next put_async() | SWR rebuild after eviction |
| DERIVED_TIMELINE | TTL expiry (300s) | None (TTL only, unless F-2 enhancement activated) |

### Cross-Layer Consistency Propagation

**SaveSession commit triggers System B invalidation:**

1. `CacheInvalidator._invalidate_project_dataframes()` calls `DataFrameCache.invalidate_project(project_gid)` for each affected project GID.
2. `invalidate_project()` delegates to `invalidate(project_gid, entity_type=None)` which calls `memory_tier.remove(cache_key)` for all entity types.
3. S3 entries remain (they are superseded, not deleted). This is intentional — the S3 entry serves as LKG fallback if SWR rebuild fails.
4. Next read to `DataFrameCache.get_async()` for the affected project misses MemoryTier and either hits S3 (stale, triggers SWR) or misses S3 (triggers synchronous build).
5. SWR rebuild callback (`_swr_build_callback` in factory.py) rebuilds from Asana API and calls `put_async()`, which writes to S3 first then MemoryTier.

**Invisible invalidation chain assessment:**

There is no invisible cross-layer chain risk because:
- `DataFrameCache.invalidate_project()` clears all entity types for a project atomically within MemoryTier.
- The DERIVED_TIMELINE entries are in System A (Redis/S3 via `TieredCacheProvider`), not in System B (DataFrameCache). Invalidating System B does not affect derived timeline entries.
- The DERIVED_TIMELINE TTL (300s) is independent. If F-2 optional enhancement is activated, `MutationInvalidator._handle_section_mutation()` would need to also call derived timeline invalidation — see F-2 Enhancement Specification below.

---

## CACHE-1 Design: Exact Change Specification

### Summary

Add `dataframe_cache: DataFrameCache | None` parameter to `CacheInvalidator.__init__()` and add a new private method `_invalidate_project_dataframes()` called from `_invalidate_dataframe_caches()`.

### File to Modify

`src/autom8_asana/persistence/cache_invalidator.py`

### Constructor Change

```
# BEFORE
def __init__(
    self,
    cache_provider: Any,
    log: Any | None = None,
) -> None:
    self._cache = cache_provider
    self._log = log

# AFTER
def __init__(
    self,
    cache_provider: Any,
    log: Any | None = None,
    dataframe_cache: Any | None = None,
) -> None:
    self._cache = cache_provider
    self._log = log
    self._dataframe_cache = dataframe_cache  # Optional DataFrameCache for project-level invalidation
```

**Why Optional**: Matches the `MutationInvalidator` pattern. `CacheInvalidator` is constructed in multiple contexts (tests, Lambda handlers, production FastAPI startup). Making `dataframe_cache` required would break all existing construction sites. Optional with `None` default means: when `None`, project-level DataFrame invalidation is silently skipped — which is the current behavior.

**Type annotation**: Use `Any | None` at the parameter level (matching the existing `cache_provider: Any` pattern) to avoid import-time circular dependency. The TYPE_CHECKING guard is already used for `SaveResult` / `ActionResult` imports. Add `DataFrameCache` there:

```python
if TYPE_CHECKING:
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
    from autom8_asana.persistence.models import ActionResult, SaveResult
```

Then narrow the instance variable annotation:

```python
if TYPE_CHECKING:
    self._dataframe_cache: DataFrameCache | None
```

### Method Change: `_invalidate_dataframe_caches()`

```
# CURRENT implementation (end of _invalidate_dataframe_caches):
#   1. invalidate_task_dataframes() per GID  ← exists
#   (missing: project-level DataFrameCache invalidation)

# AFTER — add project-level invalidation after the per-GID loop:

def _invalidate_dataframe_caches(
    self,
    gids: set[str],
    gid_to_entity: dict[str, Any],
) -> None:
    """Invalidate DataFrame caches for project contexts.

    Per TDD-WATERMARK-CACHE Phase 3: DataFrame cache invalidation.
    Per FR-INVALIDATE-003: Invalidate all project contexts via memberships.
    Per TDD-CACHE-INVALIDATION-001: Mirror MutationInvalidator project-level
    invalidation for SaveSession structural mutations.
    """
    from autom8_asana.cache.integration.dataframes import invalidate_task_dataframes

    # Step 1: Per-task DataFrame invalidation (System A, unchanged)
    for gid in gids:
        entity = gid_to_entity.get(gid)
        if entity and hasattr(entity, "memberships") and entity.memberships:
            try:
                project_gids = [
                    m.get("project", {}).get("gid")
                    for m in entity.memberships
                    if isinstance(m, dict) and m.get("project", {}).get("gid")
                ]
                if project_gids:
                    invalidate_task_dataframes(gid, project_gids, self._cache)
            except CACHE_TRANSIENT_ERRORS as exc:
                if self._log:
                    self._log.warning(
                        "dataframe_cache_invalidation_failed",
                        gid=gid,
                        error=str(exc),
                    )

    # Step 2: Project-level DataFrameCache invalidation (System B, NEW)
    # Collect all project GIDs affected by this commit
    affected_project_gids = self._collect_project_gids(gids, gid_to_entity)
    if affected_project_gids:
        self._invalidate_project_dataframes(affected_project_gids)
```

### New Method: `_collect_project_gids()`

```python
def _collect_project_gids(
    self,
    gids: set[str],
    gid_to_entity: dict[str, Any],
) -> set[str]:
    """Collect all project GIDs affected by the committed entities.

    Per FR-INVALIDATE-003: Uses membership data to find affected projects.
    Deduplicates across all entities in the batch.

    Args:
        gids: Set of entity GIDs that were committed.
        gid_to_entity: Map of GID -> entity for membership lookup.

    Returns:
        Set of project GIDs whose DataFrameCache should be invalidated.
    """
    project_gids: set[str] = set()
    for gid in gids:
        entity = gid_to_entity.get(gid)
        if entity and hasattr(entity, "memberships") and entity.memberships:
            for m in entity.memberships:
                if isinstance(m, dict):
                    pgid = m.get("project", {}).get("gid")
                    if pgid:
                        project_gids.add(pgid)
    return project_gids
```

**Design note**: This deduplicates project GIDs across the entire batch. A commit that touches 10 tasks all in the same project triggers exactly one `invalidate_project()` call, not 10. This is the correct behavior — `DataFrameCache.invalidate_project()` clears all entity types for the project; calling it 10 times would be redundant.

### New Method: `_invalidate_project_dataframes()`

```python
def _invalidate_project_dataframes(
    self,
    project_gids: set[str],
) -> None:
    """Invalidate DataFrameCache for entire projects.

    Per TDD-CACHE-INVALIDATION-001: Mirrors MutationInvalidator._invalidate_project_dataframes().
    When a SaveSession commits entities, the project's full DataFrame
    may be affected (row count changes, row content changes) and must
    be invalidated so next read triggers SWR rebuild.

    Called for ALL succeeded entities (conservative approach):
    CacheInvalidator does not have per-entity operation type context
    (CREATE vs UPDATE vs DELETE) — only the committed entity list.
    Conservative blanket invalidation is correct here.

    Failure mode: Fire-and-forget with logging. A cache invalidation
    failure must not fail the commit response (NFR-DEGRADE-001).

    Args:
        project_gids: Set of project GIDs to invalidate.
    """
    if not self._dataframe_cache:
        return

    for project_gid in project_gids:
        try:
            self._dataframe_cache.invalidate_project(project_gid)
            if self._log:
                self._log.debug(
                    "project_dataframe_cache_invalidated",
                    project_gid=project_gid,
                )
        except Exception as exc:  # BROAD-CATCH: isolation -- per-project loop, single failure must not abort batch
            if self._log:
                self._log.warning(
                    "project_dataframe_invalidation_failed",
                    project_gid=project_gid,
                    error=str(exc),
                )
```

**Why BROAD-CATCH here**: Matches `MutationInvalidator._invalidate_project_dataframes()` line 359, which uses `except Exception`. The `DataFrameCache.invalidate_project()` method calls `MemoryTier.remove()`, which uses `threading.RLock`. Any threading or unexpected error should be caught and logged, not propagated.

### Calling Convention: Sync vs Async

`DataFrameCache.invalidate_project()` is synchronous (line 609 of `dataframe_cache.py`: calls `self.invalidate()` which calls `self.memory_tier.remove()` — all sync). `CacheInvalidator._invalidate_dataframe_caches()` is also sync. No calling convention mismatch. No `asyncio.create_task` needed for the invalidation itself.

`CacheInvalidator.invalidate_for_commit()` is `async` and calls `_invalidate_dataframe_caches()` synchronously. This is unchanged — the new `_invalidate_project_dataframes()` call is also synchronous.

**Contrast with MutationInvalidator**: `MutationInvalidator._invalidate_project_dataframes()` is `async` because it was designed to be called from an async handler. The method body is actually synchronous (the loop body calls `self._dataframe_cache.invalidate_project()` which is sync). The `async def` wrapper is an artifact of the fire-and-forget `asyncio.create_task` pattern. `CacheInvalidator` does not use fire-and-forget — it runs invalidation inline before returning. Both approaches are correct.

### Construction Site: Where to Wire `dataframe_cache`

`CacheInvalidator` is constructed in `SaveSession.__init__()`. That is where `dataframe_cache` must be passed.

The `DataFrameCache` singleton is accessed via `get_dataframe_cache()` from `cache/dataframe/factory.py`. The construction site should call `get_dataframe_cache()` and pass the result (which may be `None` if DataFrameCache is not initialized, e.g., in test environments or when S3 is not configured).

```
# In SaveSession.__init__() (or wherever CacheInvalidator is constructed):
from autom8_asana.cache.dataframe.factory import get_dataframe_cache

self._cache_invalidator = CacheInvalidator(
    cache_provider=cache_provider,
    log=log,
    dataframe_cache=get_dataframe_cache(),  # None if not initialized
)
```

**This must be verified**: Locate the exact construction site in `SaveSession` and confirm `get_dataframe_cache()` is importable there without introducing a circular dependency. The `factory.py` module imports are wrapped in `TYPE_CHECKING` guards elsewhere in the persistence layer — this pattern is established.

### Docstring Updates

The `CacheInvalidator` class docstring should be updated to reference the new System B invalidation:

```
Per FR-INVALIDATE-001 through FR-INVALIDATE-006.
Handles TASK, SUBTASKS, DETECTION, DataFrame (per-task), and
project-level DataFrameCache entries.
```

---

## CACHE-2 Design: Optional Timeline Invalidation Enhancement

### Decision Criteria for Activation

This enhancement should be implemented when **any** of the following conditions are met:

1. **Business owner confirms** that 5-minute staleness for section-timeline data is unacceptable for a specific consumer (e.g., a real-time dashboard, an operational workflow that reads timeline data immediately after a section move).
2. **Production incident** is filed where stale timeline data caused a business decision error.
3. **SLA is established** for the section-timelines API that requires freshness guarantees shorter than 300s.

The current evidence (analytical reporting use case, historical date range parameters, `<1.5s` latency target focused on warm-path performance) does not meet any of these criteria. The enhancement is designed here so it can be implemented quickly when triggered, not because it is required now.

### Implementation Specification

**File to modify**: `src/autom8_asana/cache/integration/mutation_invalidator.py`

**Location**: `MutationInvalidator._handle_section_mutation()`, after Step 2 (project-level DataFrame invalidation).

```
# Current _handle_section_mutation() steps:
# Step 1: Section entity cache (SECTION entry type)
# Step 2: Project-level DataFrame invalidation
# Step 3: Task entity cache for add-member operations

# ADDITIONAL Step 4 (new, conditional on activation):
# Step 4: Derived timeline cache invalidation

# In _handle_section_mutation(), add after Step 2:

# Step 4: Derived timeline cache invalidation
# Section mutations (add/remove task, create/delete section, section rename)
# may affect which interval a task currently occupies.
# Invalidate the derived timeline cache so next request recomputes.
if event.project_gids:
    self._invalidate_derived_timelines(event.project_gids)
```

### New Method: `_invalidate_derived_timelines()`

```python
def _invalidate_derived_timelines(
    self,
    project_gids: list[str],
) -> None:
    """Invalidate derived timeline entries for affected projects.

    Per F-2 optional enhancement: When a section mutation occurs, the
    pre-computed derived timeline cache for the project may be stale
    (the task's current section position has changed).

    Invalidates all known classifier names for each project.
    The classifier name set is enumerated from KNOWN_CLASSIFIER_NAMES.

    Args:
        project_gids: Projects whose derived timelines should be invalidated.
    """
    from autom8_asana.cache.integration.derived import (
        make_derived_timeline_key,
    )
    from autom8_asana.cache.models.entry import EntryType

    for project_gid in project_gids:
        for classifier_name in _DERIVED_TIMELINE_CLASSIFIER_NAMES:
            key = make_derived_timeline_key(project_gid, classifier_name)
            try:
                self._cache.invalidate(key, [EntryType.DERIVED_TIMELINE])
            except CACHE_TRANSIENT_ERRORS as exc:
                logger.warning(
                    "derived_timeline_invalidation_failed",
                    extra={
                        "project_gid": project_gid,
                        "classifier_name": classifier_name,
                        "error": str(exc),
                    },
                )
```

### Classifier Enumeration Strategy

The derived timeline cache key is `timeline:{project_gid}:{classifier_name}`. At invalidation time, the invalidator does not know which classifier names have been used for a given project. There are three strategies:

**Strategy A: Enumerate from a known constant (RECOMMENDED)**

Define a module-level constant listing all classifier names that may produce derived timeline entries:

```python
# In mutation_invalidator.py (or derived.py for shared access):
_DERIVED_TIMELINE_CLASSIFIER_NAMES: frozenset[str] = frozenset({
    "offer",
    "unit",
})
```

The current codebase uses `"offer"` and `"unit"` as classifier names (from `DerivedTimelineCacheEntry.classifier_name` usage in the section timeline feature). This set is small, bounded, and stable. Invalidating 2 keys per project per section mutation is negligible overhead.

**Why this is correct**: The invalidation is idempotent — invalidating a key that does not exist is a no-op in `CacheProvider.invalidate()`. Over-invalidating (invalidating a classifier that had no entry) causes only a harmless cache miss on the next request.

**Strategy B: SCAN-based enumeration**

Use Redis SCAN with pattern `asana:*:timeline:{project_gid}:*` to discover all active classifier names at invalidation time. Rejected: SCAN is expensive in production Redis, adds latency to the invalidation path, and is operationally fragile. The known constant approach is strictly better.

**Strategy C: Registry of active classifier names per project**

Maintain a per-project set of known classifier names populated on `store_derived_timelines()`. Rejected: Adds state to the invalidation path, creates a coordination requirement between write (storing) and invalidation paths, and the bounded classifier set makes this engineering overhead unjustified.

### Blast Radius Analysis

**Blast radius per section mutation event**: 2 cache invalidation calls (one per classifier name) per project GID in the event. For a typical section mutation affecting 1 project: 2 calls.

**Effect**: Forces recomputation on next section-timelines request. Recomputation cost: ~2-4s (from `_DERIVED_TIMELINE_TTL` comment). At current request frequency (on-demand analytical, low rate), this is acceptable.

**Risk**: If section mutations are very frequent (e.g., bulk moves), derived timeline cache hit rate drops significantly. The 300s TTL means the cache would naturally expire before most bulk operation windows complete anyway — so the additional invalidation calls primarily affect the first request after each mutation rather than continuous recomputation.

---

## Failure Mode Summary

| Scenario | System | Behavior | Justification |
|----------|--------|----------|---------------|
| `DataFrameCache.invalidate_project()` raises | CACHE-1 | Fail-open: log warning, continue loop, commit response succeeds | NFR-DEGRADE-001; commit already applied to Asana; staleness TTL provides recovery |
| `DataFrameCache` is `None` (not initialized) | CACHE-1 | Silent no-op (early return in `_invalidate_project_dataframes`) | Matches `MutationInvalidator` pattern; test/dev environments without S3 config |
| Asana API unreachable after MemoryTier eviction | CACHE-1 | SWR rebuild fails; circuit breaker opens; LKG served from MemoryTier/S3 | LKG availability-first contract; consistent with F-3 unlimited LKG policy |
| S3 write fails during SWR rebuild | CACHE-1 | MemoryTier populated, S3 not updated; next cold start misses S3 LKG for this project | Acceptable; S3 failure already logged by `put_async()` |
| `cache.invalidate(key, [DERIVED_TIMELINE])` raises | CACHE-2 (if activated) | Fail-open: log warning, continue | Fire-and-forget pattern; 300s TTL provides automatic recovery |
| Redis unreachable for DERIVED_TIMELINE reads | CACHE-2 | `get_cached_timelines()` returns None; compute path executes; response served fresh | Cache is an optimization; computation path is the fallback |

---

## Cross-Layer Consistency

### System A / System B After CACHE-1

Before CACHE-1, the two systems had asymmetric consistency guarantees from the SaveSession write path:
- System A: Correctly invalidated per-task entries after every commit.
- System B: Not invalidated at all. Stale DataFrames persisted for up to 9-45 min (entity TTL + SWR grace).

After CACHE-1, both systems are invalidated within the same `CacheInvalidator.invalidate_for_commit()` call. The consistency model for both is eventual (fire-and-forget, AP). The staleness window for System B drops from "entity TTL + SWR grace (up to 45 min)" to "time between commit and SWR rebuild (typically 1-10s for the background task to execute)".

### Consistency Propagation Between Invalidation and SWR Rebuild

The invalidation (CACHE-1) and the SWR rebuild are not atomic. There is a window between:
1. `invalidate_project()` removes MemoryTier entry
2. SWR rebuild completes and `put_async()` populates MemoryTier with fresh data

During this window, requests to `DataFrameCache.get_async()` will:
- Miss MemoryTier (just evicted)
- Hit ProgressiveTier (S3 — stale, pre-mutation data)
- The S3 hit will check TTL/schema and enter APPROACHING_STALE or STALE state
- STALE state triggers a second SWR refresh (or waits for the first to complete via coalescer)

This is correct behavior. The `DataFrameCacheCoalescer` prevents multiple concurrent builds for the same `(project_gid, entity_type)` key. All concurrent readers during the rebuild window get the LKG (pre-mutation) data and the rebuild completes exactly once.

**Guaranteed delivery**: The SWR rebuild is not triggered by the invalidation — it is triggered by the next read after invalidation. If no reads occur after the invalidation, the stale S3 entry persists until natural TTL expiry drives the next SWR trigger. This is the accepted behavior for AP + eventual consistency.

---

## Architecture Decision Records

### ADR-CA-001: Conservative vs. Selective Structural Mutation Guard in CacheInvalidator

**Context**: `MutationInvalidator` applies a structural mutation guard before calling `DataFrameCache.invalidate_project()` — only CREATE, DELETE, MOVE, ADD_MEMBER, REMOVE_MEMBER trigger project-level invalidation. UPDATE-only mutations do not. This is because `MutationInvalidator` receives explicit `MutationType` context from REST route handlers. `CacheInvalidator` receives only `SaveResult` (committed entities, no operation type per entity).

**Decision**: `CacheInvalidator` applies conservative blanket invalidation — all succeeded entities trigger `DataFrameCache.invalidate_project()` for their affected projects, regardless of whether the operation was a CREATE, UPDATE, or DELETE.

**Consequences**:
- Positive: No structural mutations are missed. No code required to infer operation type from `SaveResult`.
- Negative: Field-update commits (UPDATE-only, no row count change) trigger a project-level DataFrame rebuild. This is an unnecessary rebuild for pure field updates.
- Mitigation: The SWR rebuild is background and deduped by the coalescer. For a commit that updates multiple fields on one offer, exactly one rebuild fires once. The rebuilding cost (~2-4s Asana API round trip) is paid in the background, not on the critical path.

**Alternatives considered**:
1. Add `operation_type` to `SaveResult.succeeded` entries: Would require plumbing operation type through `Session.commit()` -> `EntityProcessor` -> `SaveResult`. Significant refactor to `persistence/` internals. Rejected as disproportionate for this fix.
2. Infer CREATE by checking for temp GID resolution (temp GID before commit, real GID after): Fragile — relies on GID format conventions rather than explicit type. Rejected.
3. Accept false-negative misses (only invalidate on detected structural mutations): Risk of serving incorrect row counts after CREATE/DELETE is too high. Rejected per F-1 severity assessment (HIGH).

**Verdict**: Conservative blanket invalidation is the correct choice for `CacheInvalidator`.

---

### ADR-CA-002: Optional `dataframe_cache` Parameter vs. Required

**Context**: `MutationInvalidator` takes `dataframe_cache: DataFrameCache | None = None` (optional). The question is whether `CacheInvalidator` should use the same pattern or make it required.

**Decision**: Optional with default `None`. Same pattern as `MutationInvalidator`.

**Consequences**:
- Zero breaking changes to existing construction sites.
- Existing tests do not need `dataframe_cache` wiring to compile.
- When `dataframe_cache` is `None`, project-level DataFrame invalidation is silently skipped. This is the current behavior, so tests pass unchanged.
- Production construction site requires one change: pass `get_dataframe_cache()` to `CacheInvalidator.__init__()`.

**Alternatives considered**: Required parameter. Rejected because it breaks all existing test fixtures and Lambda handler construction sites that create `CacheInvalidator` without a `DataFrameCache`.

---

### ADR-CA-003: Classifier Name Enumeration for Derived Timeline Invalidation (F-2 Optional)

**Context**: `make_derived_timeline_key(project_gid, classifier_name)` produces the key `timeline:{project_gid}:{classifier_name}`. At invalidation time in `MutationInvalidator`, the classifier names that have been used for a given project are not tracked. The invalidator must either enumerate known names statically or discover them dynamically.

**Decision**: Static constant `_DERIVED_TIMELINE_CLASSIFIER_NAMES = frozenset({"offer", "unit"})`. Invalidate all entries in the set for each affected project.

**Consequences**:
- Positive: No SCAN operations, no state, no coordination between write and invalidation paths.
- Positive: Idempotent — invalidating a key that does not exist is a no-op.
- Negative: Adding a new classifier name requires updating the constant in two places (wherever `classifier_name` values are defined + this constant). Mitigation: the constant should be defined in `derived.py` alongside `_DERIVED_TIMELINE_TTL` and imported by `mutation_invalidator.py`.

**Alternatives considered**: See Classifier Enumeration Strategy section above. Both alternatives were rejected.

---

### ADR-CA-004: F-2 Enhancement Trigger Deferred to Business Owner

**Context**: The thermal assessment (F-2) assessed the 300s TTL as likely acceptable for the analytical reporting use case. The heat-mapper escalated the staleness acceptability question and assigned a DEFER-until-confirmation status to the enhancement.

**Decision**: The F-2 enhancement specification is documented here but not yet marked for implementation. Activation requires explicit business owner confirmation that 5-minute staleness is insufficient for at least one active consumer.

**Consequences**: If activated without business owner confirmation and the use case is purely analytical, the enhancement adds unnecessary Redis invalidation calls on every section mutation with no user-visible benefit. The 300s TTL would expire naturally before most analytical queries are re-executed anyway.

**Trigger conditions**: Documented in the CACHE-2 "Decision Criteria for Activation" section above.

---

## Test Strategy

### CACHE-1 Tests: New Invalidation Path

#### Unit Tests for `CacheInvalidator` (new file: `tests/unit/persistence/test_cache_invalidator.py`)

The test file does not currently exist. It should be created to cover:

**1. Constructor injection:**

```
test_init_without_dataframe_cache:
    Given: CacheInvalidator(cache_provider=mock_cache)
    Assert: self._dataframe_cache is None

test_init_with_dataframe_cache:
    Given: CacheInvalidator(cache_provider=mock_cache, dataframe_cache=mock_df_cache)
    Assert: self._dataframe_cache is mock_df_cache
```

**2. No-op when dataframe_cache is None:**

```
test_invalidate_for_commit_no_dataframe_cache_does_not_call_invalidate_project:
    Given: CacheInvalidator(mock_cache, dataframe_cache=None)
    When: invalidate_for_commit(crud_result_with_succeeded_entities, ...)
    Assert: No call to any invalidate_project() method
    Assert: No AttributeError raised
```

**3. Project-level invalidation on commit:**

```
test_invalidate_for_commit_calls_invalidate_project_for_each_affected_project:
    Given: Entity with memberships = [{"project": {"gid": "proj-1"}}, {"project": {"gid": "proj-2"}}]
    When: CacheInvalidator(mock_cache, dataframe_cache=mock_df_cache).invalidate_for_commit(crud_result, ...)
    Assert: mock_df_cache.invalidate_project.call_count == 2
    Assert: calls include "proj-1" and "proj-2"
```

**4. Project GID deduplication:**

```
test_invalidate_project_called_once_per_project_not_per_entity:
    Given: 5 entities, all with memberships = [{"project": {"gid": "proj-1"}}]
    When: invalidate_for_commit(crud_result with 5 succeeded, ...)
    Assert: mock_df_cache.invalidate_project.call_count == 1
    Assert: called with "proj-1"
```

**5. Failure isolation:**

```
test_invalidate_project_failure_does_not_fail_commit:
    Given: mock_df_cache.invalidate_project raises RuntimeError
    When: invalidate_for_commit(...)
    Assert: No exception propagates from invalidate_for_commit()
    Assert: (if log mock provided) warning logged with "project_dataframe_invalidation_failed"
```

**6. Entity without memberships is skipped:**

```
test_entity_without_memberships_does_not_contribute_project_gids:
    Given: Entity has no .memberships attribute
    When: invalidate_for_commit(...)
    Assert: mock_df_cache.invalidate_project not called
```

**7. Empty commit is a no-op:**

```
test_empty_crud_result_no_invalidation:
    Given: SaveResult with empty succeeded list
    When: invalidate_for_commit(...)
    Assert: mock_df_cache.invalidate_project not called
    Assert: mock_cache.invalidate not called
```

#### Integration-level check (existing test baseline)

`tests/unit/cache/test_mutation_invalidator.py` provides the fixture and pattern baseline. Mirror the `test_task_create_invalidates_project_dataframe` pattern from that test file for the `CacheInvalidator` tests.

---

### CACHE-2 Tests: Derived Timeline Invalidation (if activated)

#### Unit Tests for `MutationInvalidator` (add to existing `test_mutation_invalidator.py`)

```
test_section_mutation_invalidates_derived_timeline_when_activated:
    Given: MutationInvalidator with feature flag enabled
    When: invalidate_async(MutationEvent(EntityKind.SECTION, "section-1",
           MutationType.MOVE, project_gids=["proj-1"]))
    Assert: mock_cache.invalidate called with
            key=make_derived_timeline_key("proj-1", "offer"),
            entry_types=[EntryType.DERIVED_TIMELINE]
    Assert: mock_cache.invalidate called with
            key=make_derived_timeline_key("proj-1", "unit"),
            entry_types=[EntryType.DERIVED_TIMELINE]

test_section_mutation_derived_timeline_failure_does_not_propagate:
    Given: mock_cache.invalidate raises ConnectionError for DERIVED_TIMELINE calls
    When: invalidate_async(section mutation event)
    Assert: No exception propagates
    Assert: logger.warning called with "derived_timeline_invalidation_failed"

test_section_mutation_no_project_gids_does_not_invalidate_derived_timeline:
    Given: MutationEvent(EntityKind.SECTION, ..., project_gids=[])
    When: invalidate_async(event)
    Assert: No DERIVED_TIMELINE invalidation calls
```

#### Existing test: `test_derived_timeline_cache_serves_stale_on_section_move`

This is a new integration test that should be added when F-2 is activated. It would:
1. Seed a derived timeline cache entry with `store_derived_timelines()`
2. Fire a section mutation event through `MutationInvalidator`
3. Assert that `get_cached_timelines()` returns None (entry evicted)

---

## Handoff Checklist

- [x] `cache-architecture.md` produced at `.claude/wip/SPIKE-CACHE-ARCH/CACHE-ARCHITECTURE.md`
- [x] CACHE-1 layer has: pattern selected with rationale, consistency model justified (eventual/AP), failure mode designed for all three scenarios
- [x] CACHE-2 layer has: pattern confirmed (TTL), optional enhancement specified, failure mode designed, decision criteria documented
- [x] Invalidation strategy specified per layer and cross-layer
- [x] ADRs documented: ADR-CA-001 (conservative guard), ADR-CA-002 (optional param), ADR-CA-003 (classifier enumeration), ADR-CA-004 (F-2 deferral)
- [x] Exact change specification for CACHE-1 (constructor, methods, construction site, calling convention)
- [x] Test strategy: what to test, how to structure, which file to create
- [x] No architecture designed for F-3 (DEFER), F-4 (OPTIMIZE-INSTEAD), F-5 (OPTIMIZE-INSTEAD)
