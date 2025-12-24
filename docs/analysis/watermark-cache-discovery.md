# Watermark Cache Discovery Analysis

**Session**: 1 - Discovery
**Date**: 2025-12-23
**Author**: Requirements Analyst
**Status**: Complete

---

## Executive Summary

This discovery analysis maps the current implementation and identifies integration points for parallel section fetch and batch cache operations. The core insight from Prompt 0 is confirmed: **"The cache is already right. The fetch is wrong."**

**Key Findings**:

1. **Parallel fetch is achievable** - `TasksClient.list_async(section=...)` supports section-scoped fetching; `SectionsClient.list_for_project_async()` provides section enumeration
2. **Batch cache operations exist** - `get_batch()` / `set_batch()` are defined in `CacheProvider` protocol and implemented in `EnhancedInMemoryCacheProvider`
3. **Post-commit hook infrastructure exists** - `EventSystem.emit_post_commit()` provides the insertion point for cache invalidation
4. **Concurrency is configurable** - SDK supports 50 concurrent reads, rate limit of 1500 requests/60s with token bucket limiter

**Prompt 0 Assumption Corrections**:

- The cache key format is `{task_gid}:{project_gid}` for DataFrame entries (confirmed)
- Batch cache operations exist but are sequential loops in `EnhancedInMemoryCacheProvider` (not atomic batches)
- SaveSession already has cache invalidation (lines 1452-1508), but it invalidates TASK and SUBTASKS entry types, not DATAFRAME entries

---

## 1. Current Fetch Flow Analysis

### 1.1 ProjectDataFrameBuilder Current Implementation

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py`

The `ProjectDataFrameBuilder` currently:

1. Accepts a `project` object that is expected to have a `tasks` attribute/method (lines 116-131)
2. Does NOT fetch tasks itself - it expects pre-fetched tasks from the project
3. Applies section filtering client-side via `_task_in_sections()` (lines 152-175)

**Critical Finding**: The DataFrame builder does NOT call `TasksClient.list_async()` directly. The latency problem is upstream - wherever `project.tasks` is populated.

```python
# Current flow in ProjectDataFrameBuilder.get_tasks():
def get_tasks(self) -> list[Task]:
    tasks = self._project.tasks  # Already fetched externally
    if callable(tasks):
        tasks = tasks()
    if self._sections:
        tasks = [t for t in tasks if self._task_in_sections(t, self._sections)]
    return tasks
```

### 1.2 Where Tasks Are Actually Fetched

The 52-second latency occurs when populating `project.tasks`. This is likely in:

1. A Project model that lazily fetches tasks
2. Consumer code that calls `TasksClient.list_async(project=project_gid).collect()`

**Implication**: Parallel fetch must be implemented either:
- **Option A**: In `ProjectDataFrameBuilder` by accepting a client and fetching internally
- **Option B**: In a new helper function that returns tasks grouped by section
- **Option C**: In the Project model's task population logic

### 1.3 TasksClient List Capabilities

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py`

The `list_async()` method (lines 574-639) supports:

```python
def list_async(
    self,
    *,
    project: str | None = None,      # Filter by project GID
    section: str | None = None,       # Filter by section GID  <-- KEY CAPABILITY
    assignee: str | None = None,
    workspace: str | None = None,
    completed_since: str | None = None,
    modified_since: str | None = None,
    opt_fields: list[str] | None = None,
    limit: int = 100,                 # Max 100 per page
) -> PageIterator[Task]:
```

**Confirmed**: `section` parameter enables section-scoped task fetching for parallel fetch strategy.

### 1.4 SectionsClient Capabilities

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`

```python
def list_for_project_async(
    self,
    project_gid: str,
    *,
    opt_fields: list[str] | None = None,
    limit: int = 100,
) -> PageIterator[Section]:
```

**Confirmed**: Section enumeration is available via `SectionsClient.list_for_project_async()`.

---

## 2. Proposed Parallel Fetch Flow

### 2.1 Target Architecture

```
project.to_dataframe_async()
    |
    v
+------------------------------------------+
|   PARALLEL SECTION FETCH                 |
|   1. sections = sections_client          |
|      .list_for_project_async(project_gid)|
|      .collect()                          |
|   2. semaphore = Semaphore(8)            |
|   3. async for section in sections:      |
|      async with semaphore:               |
|        tasks_client.list_async(          |
|          section=section.gid             |
|        ).collect()                       |
|   4. tasks = await gather(*fetch_tasks)  |
+------------------------------------------+
    |
    v
+------------------------------------------+
|   BATCH CACHE OPERATIONS                 |
|   1. keys = [make_dataframe_key(t.gid,   |
|              project_gid) for t in tasks]|
|   2. cached = cache.get_batch(keys,      |
|              EntryType.DATAFRAME)        |
|   3. For misses: extract rows            |
|   4. cache.set_batch(new_entries)        |
+------------------------------------------+
    |
    v
    DataFrame
```

### 2.2 Integration Point Options

**Option A: Modify ProjectDataFrameBuilder** (Recommended)

Add a new async method that fetches via parallel sections:

```python
async def build_async(
    self,
    client: AsanaClient,  # New parameter
    use_parallel_fetch: bool = True,
    use_cache: bool = True,
) -> pl.DataFrame:
```

Pros:
- Centralized logic
- Backward compatible (existing `build()` still works with pre-fetched tasks)
- Natural place for cache integration

Cons:
- Requires AsanaClient reference

**Option B: New ParallelFetchBuilder** (Alternative)

Create a new builder that wraps ProjectDataFrameBuilder:

```python
class ParallelFetchDataFrameBuilder:
    def __init__(self, client: AsanaClient, project_gid: str):
        ...
    async def build(self) -> pl.DataFrame:
        tasks = await self._fetch_parallel()
        return ProjectDataFrameBuilder(...).build(tasks=tasks)
```

Pros:
- Separation of concerns
- Easier to test in isolation

Cons:
- Additional abstraction layer

---

## 3. Cache Infrastructure Audit

### 3.1 CacheProvider Protocol

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py`

The protocol defines batch operations (lines 104-133):

```python
def get_batch(
    self,
    keys: list[str],
    entry_type: EntryType,
) -> dict[str, CacheEntry | None]:
    """Retrieve multiple entries in single operation."""
    ...

def set_batch(
    self,
    entries: dict[str, CacheEntry],
) -> None:
    """Store multiple entries in single operation."""
    ...
```

**Confirmed**: Batch operations are part of the protocol.

### 3.2 EnhancedInMemoryCacheProvider Implementation

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py`

```python
def get_batch(
    self,
    keys: list[str],
    entry_type: EntryType,
) -> dict[str, CacheEntry | None]:
    result: dict[str, CacheEntry | None] = {}
    for key in keys:
        result[key] = self.get_versioned(key, entry_type)
    return result

def set_batch(
    self,
    entries: dict[str, CacheEntry],
) -> None:
    for key, entry in entries.items():
        self.set_versioned(key, entry)
```

**Finding**: Batch operations are sequential loops, not atomic. This is acceptable for in-memory but may need optimization for Redis.

### 3.3 DataFrame Cache Key Format

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframes.py`

```python
def make_dataframe_key(task_gid: str, project_gid: str) -> str:
    """Create cache key for dataframe entry.

    Per ADR-0021, dataframe entries vary by project due to custom fields,
    so key includes both task and project GID.
    """
    return f"{task_gid}:{project_gid}"
```

**Confirmed**: Key format is `{task_gid}:{project_gid}` as stated in Prompt 0.

### 3.4 CacheEntry Structure

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py`

```python
@dataclass(frozen=True)
class CacheEntry:
    key: str
    data: dict[str, Any]
    entry_type: EntryType  # DATAFRAME for this use case
    version: datetime      # task.modified_at for staleness detection
    cached_at: datetime
    ttl: int | None = 300  # 5 min default
    project_gid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Confirmed**: Versioning via `modified_at` timestamp for staleness detection.

### 3.5 DataFrameCacheIntegration

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py`

Existing integration provides:

- `get_cached_row_async()` - Single row lookup with schema version validation
- `get_cached_batch_async()` - Batch lookup (but loops internally, not truly batched)
- `cache_row_async()` - Single row write
- `cache_batch_async()` - Batch write
- `invalidate_async()` - Single key invalidation

**Gap Identified**: `get_cached_batch_async()` loops through individual lookups (lines 260-294). For 3,500 tasks, this is 3,500 individual `get_versioned()` calls. True batch should use `get_batch()` at cache provider level.

---

## 4. Invalidation Hook Points

### 4.1 SaveSession Cache Invalidation (Already Exists)

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py`

Lines 1452-1508 show existing cache invalidation:

```python
async def _invalidate_cache_for_results(
    self,
    crud_result: SaveResult,
    action_results: list[ActionResult],
) -> None:
    """Invalidate cache entries for successfully mutated entities."""
    cache = getattr(self._client, "_cache_provider", None)
    if cache is None:
        return

    from autom8_asana.cache.entry import EntryType

    gids_to_invalidate: set[str] = set()

    for entity in crud_result.succeeded:
        if hasattr(entity, "gid") and entity.gid:
            gids_to_invalidate.add(entity.gid)

    for action_result in action_results:
        if action_result.success and action_result.action.task:
            if hasattr(action_result.action.task, "gid"):
                gids_to_invalidate.add(action_result.action.task.gid)

    for gid in gids_to_invalidate:
        try:
            cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
        except Exception as exc:
            # Log and continue
            ...
```

**Gap Identified**: Invalidation covers `EntryType.TASK` and `EntryType.SUBTASKS`, but NOT `EntryType.DATAFRAME`.

**Required Change**: Add `EntryType.DATAFRAME` to invalidation, but this requires knowing the project_gid(s) for the task since the DataFrame cache key is `{task_gid}:{project_gid}`.

### 4.2 Post-Commit Hook System

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/events.py`

```python
async def emit_post_commit(self, result: SaveResult) -> None:
    """Emit post-commit event with full SaveResult."""
    for hook in self._post_commit_hooks:
        try:
            hook_result = hook(result)
            if asyncio.iscoroutine(hook_result):
                await hook_result
        except Exception:
            pass  # Post-commit hooks should not fail the operation
```

**Confirmed**: Post-commit hooks receive full `SaveResult` and can trigger invalidation.

### 4.3 Invalidation Strategy for DataFrame Entries

**Challenge**: DataFrame cache keys include project context (`{task_gid}:{project_gid}`). When a task is modified, we need to invalidate all project-specific cache entries.

**Options**:

1. **Query task memberships**: Get all project GIDs from `task.memberships` and invalidate each
2. **Wildcard invalidation**: Invalidate all keys matching `{task_gid}:*` (requires cache provider support)
3. **Track task-project mappings**: Maintain reverse index of task -> projects

**Recommendation**: Option 1 (query memberships) is simplest and aligns with existing patterns. Task entities typically have `memberships` populated from API responses.

---

## 5. Concurrency Assessment

### 5.1 SDK Concurrency Configuration

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py`

```python
@dataclass(frozen=True)
class ConcurrencyConfig:
    read_limit: int = 50   # Concurrent GET requests
    write_limit: int = 15  # Concurrent mutation requests
```

### 5.2 HTTP Transport Semaphores

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/http.py`

```python
# Concurrency semaphores (lines 65-67)
self._read_semaphore = asyncio.Semaphore(config.concurrency.read_limit)
self._write_semaphore = asyncio.Semaphore(config.concurrency.write_limit)
```

**Confirmed**: Read operations (GET) use a semaphore with default limit of 50.

### 5.3 Token Bucket Rate Limiter

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/rate_limiter.py`

```python
class TokenBucketRateLimiter:
    def __init__(
        self,
        max_tokens: int = 1500,      # Asana's limit
        refill_period: float = 60.0,  # 60 seconds
    ):
```

**Confirmed**: Token bucket respects Asana's 1500 requests/60s limit.

### 5.4 Safe Concurrency for Parallel Section Fetch

**Analysis**:

- Asana rate limit: 1500 requests / 60 seconds = 25 requests/second
- Typical project: 8-12 sections
- Parallel section fetch: 8 concurrent requests (one per section)
- Each section fetch: paginated, ~100 tasks per page

**Calculation for 3,500 tasks in 8 sections**:

- Section listing: 1 request
- Per section: ~4 pages (350 tasks per section average) = 4 requests
- Total: 1 + (8 * 4) = 33 requests
- At 8 concurrent: ~4 batches = ~2 seconds API time

**Recommendation**: Default `max_concurrent_sections=8` is safe. Could increase to 10-12 for aggressive optimization, but 8 provides margin.

### 5.5 Circuit Breaker

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/circuit_breaker.py`

Circuit breaker protection exists with configurable thresholds. Parallel fetch should integrate with this for automatic fallback.

---

## 6. Open Questions Resolution

### 6.1 Parallel Fetch Questions

| Question | Answer |
|----------|--------|
| **Concurrency limit** | 8 concurrent section fetches (safe within rate limits) |
| **Error handling** | Fail all and fall back to serial; partial success is complex |
| **Empty sections** | Skip - no tasks to fetch |
| **Section ordering** | Not critical - tasks are aggregated then sorted by DataFrame |

### 6.2 Cache Integration Questions

| Question | Answer |
|----------|--------|
| **Batch population** | Yes - parallel fetch should populate DataFrame cache |
| **Partial cache** | Check cache first, fetch only misses, merge results |
| **Cache key format** | `{task_gid}:{project_gid}` - confirmed |
| **TTL strategy** | Same 5-min TTL for all fetch paths |

### 6.3 Invalidation Questions

| Question | Answer |
|----------|--------|
| **Invalidation scope** | Invalidate DataFrame entries for all projects in task memberships |
| **Batch invalidation** | Loop through affected GIDs; cache.invalidate() is O(1) per key |
| **External changes** | TTL expiration (5 min) - no active detection needed |

### 6.4 Configuration Questions

| Question | Answer |
|----------|--------|
| **Default parallelism** | 8 concurrent sections |
| **Opt-out mechanism** | `use_parallel_fetch=False` parameter |
| **Metrics exposure** | Use existing CacheMetrics (hit/miss/latency already tracked) |

---

## 7. Risks and Mitigations

### 7.1 Risk: API Rate Limit Exhaustion

**Risk**: Parallel fetch consumes too many tokens, causing 429 errors.

**Mitigation**:
- Token bucket rate limiter already in place
- Semaphore limits concurrent in-flight requests
- Default 8 concurrent sections is conservative

### 7.2 Risk: Partial Section Failure

**Risk**: One section fetch fails, invalidating entire result.

**Mitigation**:
- Fail-all approach with automatic fallback to serial fetch
- Circuit breaker trips if failures cascade
- Log warning but complete with available data (Phase 2 enhancement)

### 7.3 Risk: Cache Memory Pressure

**Risk**: 3,500 cached DataFrame entries consume excessive memory.

**Mitigation**:
- Existing LRU eviction in `EnhancedInMemoryCacheProvider` (max_size=10000)
- 5-min TTL ensures stale entries expire
- For production, TieredCacheProvider offloads to Redis/S3

### 7.4 Risk: DataFrame Cache Invalidation Complexity

**Risk**: Task memberships not populated, preventing multi-project invalidation.

**Mitigation**:
- Check `task.memberships` existence before invalidation
- Fall back to invalidating only known project context
- Document that full invalidation requires populated memberships

---

## 8. Summary of Required Changes

### 8.1 New Components

| Component | Purpose |
|-----------|---------|
| `parallel_fetch.py` | Parallel section fetch logic with semaphore control |

### 8.2 Modified Components

| Component | Changes |
|-----------|---------|
| `ProjectDataFrameBuilder` | Add `build_async()` with parallel fetch support |
| `DataFrameCacheIntegration` | Use `get_batch()` for true batch lookups |
| `SaveSession._invalidate_cache_for_results()` | Add `EntryType.DATAFRAME` with project context |
| `config.py` | Add `DataFrameConfig` with `max_concurrent_sections` |

### 8.3 No Changes Required

| Component | Reason |
|-----------|--------|
| `SectionsClient` | Already supports `list_for_project_async()` |
| `TasksClient` | Already supports `list_async(section=...)` |
| `CacheProvider` | Already has `get_batch()` / `set_batch()` |
| `CacheEntry` | Already has project_gid field |
| Rate limiter | Already protects against API exhaustion |

---

## 9. Handoff to Session 2

### 9.1 What Session 2 (Requirements) Needs

1. This discovery document as input
2. Confirmation of integration approach (Option A recommended)
3. Decision on fail-all vs. partial-success for section fetch errors

### 9.2 Remaining Questions for Requirements

1. Should `project.to_dataframe_async()` convenience method be updated, or is builder-level API sufficient?
2. Should parallel fetch be the default or opt-in?
3. Should cache be enabled by default (current: must pass `cache_integration` explicitly)?

### 9.3 Documents to Create in Session 2

- `PRD-WATERMARK-CACHE.md` with:
  - FR-FETCH-*: Parallel section fetch requirements
  - FR-CACHE-*: Batch cache population and lookup
  - FR-INVALIDATE-*: SaveSession post-commit invalidation
  - FR-CONFIG-*: Configuration and opt-out mechanisms
  - FR-FALLBACK-*: Graceful degradation requirements
  - NFR-*: Performance targets

---

## Appendix A: File Reference

| File | Purpose | Lines Analyzed |
|------|---------|----------------|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py` | ProjectDataFrameBuilder | 1-176 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/base.py` | DataFrameBuilder base | 1-608 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | SectionsClient | 1-342 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` | TasksClient | 1-1390 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/batch.py` | ModificationCheckCache | 1-372 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py` | CacheEntry | 1-171 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframes.py` | DataFrame caching | 1-209 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/memory.py` | InMemory provider | 1-433 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py` | DataFrameCacheIntegration | 1-677 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/protocols/cache.py` | CacheProvider protocol | 1-240 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` | SaveSession | 1-1514 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/events.py` | EventSystem | 1-281 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/rate_limiter.py` | TokenBucketRateLimiter | 1-116 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/transport/http.py` | AsyncHTTPClient semaphores | 65-67, 159-167 |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/config.py` | ConcurrencyConfig | 105-125 |

---

## Appendix B: Prompt 0 Assumption Validation

| Assumption | Status | Notes |
|------------|--------|-------|
| Cache infrastructure is correct | **Confirmed** | Per-task granularity with project context exists |
| Multi-level caching rejected | **Confirmed** | No section/project-level cache exists |
| Parallel fetch is the missing piece | **Confirmed** | TasksClient supports section-scoped fetch |
| `get_batch` / `set_batch` exist | **Confirmed** | Defined in protocol, implemented in providers |
| Cache key format `{task_gid}:{project_gid}` | **Confirmed** | In `make_dataframe_key()` |
| SaveSession can trigger invalidation | **Partial** | Exists but only for TASK/SUBTASKS, not DATAFRAME |
| TTL is 5 min | **Confirmed** | Default 300 seconds in CacheEntry |
| Rate limit 1500/60s | **Confirmed** | TokenBucketRateLimiter default |
| Read concurrency 50 | **Confirmed** | ConcurrencyConfig.read_limit default |
