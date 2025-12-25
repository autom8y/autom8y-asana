# TDD: Watermark Cache - Parallel Section Fetch

## Metadata

- **TDD ID**: TDD-WATERMARK-CACHE
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: [PRD-WATERMARK-CACHE](/docs/requirements/PRD-WATERMARK-CACHE.md)
- **Related TDDs**: TDD-0008 (Intelligent Caching), TDD-0009 (Structured DataFrame Layer)
- **Related ADRs**: ADR-0115, ADR-0116, ADR-0117, ADR-0118, ADR-0021 (DataFrame Caching Strategy)

---

## Overview

This TDD defines the technical architecture for reducing project-level DataFrame latency from 52-59 seconds to under 10 seconds through **parallel section fetch**. The core insight is that the existing per-task cache infrastructure is correctly designed; the performance problem is the serial paginated fetch strategy. This design introduces `build_async()` with parallel section fetching, automatic batch cache population, and SaveSession post-commit invalidation.

---

## Requirements Summary

From PRD-WATERMARK-CACHE:

- **FR-FETCH-001 to FR-FETCH-008**: Parallel section fetch implementation
- **FR-CACHE-001 to FR-CACHE-008**: Batch cache operations for 3,500+ entries
- **FR-INVALIDATE-001 to FR-INVALIDATE-006**: SaveSession post-commit invalidation
- **FR-CONFIG-001 to FR-CONFIG-006**: Configuration and opt-out mechanisms
- **FR-FALLBACK-001 to FR-FALLBACK-006**: Graceful degradation to serial fetch
- **NFR-PERF-001 to NFR-PERF-007**: Performance targets (cold <10s, warm <1s)
- **NFR-COMPAT-001 to NFR-COMPAT-004**: Backward compatibility guarantees

---

## System Context

The parallel fetch feature integrates with existing SDK infrastructure:

```
+-------------------------------------------------------------------+
|                        Consumer Application                        |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
|                     project.to_dataframe_async()                   |
|                           (NEW ENTRY POINT)                        |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
|                   ProjectDataFrameBuilder                          |
|  +------------------------------------------------------------+   |
|  |                    build_async() [NEW]                      |   |
|  |  1. Check batch cache (get_batch)                          |   |
|  |  2. Parallel section fetch (asyncio.gather)                |   |
|  |  3. Merge results, deduplicate                             |   |
|  |  4. Populate batch cache (set_batch)                       |   |
|  |  5. Build DataFrame                                        |   |
|  +------------------------------------------------------------+   |
+-------------------------------------------------------------------+
        |                       |                       |
        v                       v                       v
+----------------+    +-------------------+    +------------------+
| SectionsClient |    |   TasksClient     |    | CacheProvider    |
| list_for_      |    | list_async        |    | get_batch        |
| project_async  |    | (section=...)     |    | set_batch        |
+----------------+    +-------------------+    +------------------+
        |                       |                       |
        v                       v                       v
+-------------------------------------------------------------------+
|                         Asana REST API                             |
+-------------------------------------------------------------------+

Invalidation Flow:
+-------------------------------------------------------------------+
|                         SaveSession                                |
|  +------------------------------------------------------------+   |
|  |                  commit_async()                             |   |
|  |  ... existing commit logic ...                              |   |
|  |  --> _invalidate_cache_for_results() [UPDATED]              |   |
|  |      - EntryType.TASK, EntryType.SUBTASKS (existing)        |   |
|  |      - EntryType.DATAFRAME [NEW]                            |   |
|  |      - Query task.memberships for all project contexts      |   |
|  +------------------------------------------------------------+   |
+-------------------------------------------------------------------+
```

---

## Design

### Component Architecture

| Component | Responsibility | Changes |
|-----------|----------------|---------|
| `ProjectDataFrameBuilder` | Build DataFrames from project tasks | ADD: `build_async()` method with parallel fetch |
| `ParallelSectionFetcher` | Coordinate parallel section fetch with semaphore | NEW: Internal helper class |
| `DataFrameCacheIntegration` | Cache operations for DataFrame rows | UPDATE: Ensure `get_batch`/`set_batch` use provider batch ops |
| `SaveSession` | Unit of Work persistence | UPDATE: Add `EntryType.DATAFRAME` to invalidation |
| `DataFrameConfig` | Configuration for DataFrame operations | NEW: Add to `AsanaConfig` |
| `cache/dataframes.py` | DataFrame cache utilities | UPDATE: Add `invalidate_task_dataframes_async()` |

### Component Details

#### 1. ProjectDataFrameBuilder.build_async()

**Location**: `/src/autom8_asana/dataframes/builders/project.py`

```python
async def build_async(
    self,
    client: AsanaClient,
    *,
    use_parallel_fetch: bool = True,
    use_cache: bool = True,
    max_concurrent_sections: int | None = None,
) -> pl.DataFrame:
    """Build DataFrame with parallel section fetch and automatic caching.

    Per FR-FETCH-001: Async method for parallel section fetch.
    Per FR-CACHE-001: Automatic cache integration.
    Per FR-CONFIG-002, FR-CONFIG-004: Opt-out parameters.

    Args:
        client: AsanaClient for API calls and cache access.
        use_parallel_fetch: Enable parallel section fetch (default True).
            Set False to use serial project-level fetch.
        use_cache: Enable cache lookup and population (default True).
            Set False to bypass cache entirely.
        max_concurrent_sections: Override default concurrency limit.
            Defaults to DataFrameConfig.max_concurrent_sections (8).

    Returns:
        Polars DataFrame with extracted task data.

    Raises:
        No exceptions - falls back to serial on parallel fetch failure.

    Example:
        >>> builder = ProjectDataFrameBuilder(project, "Unit", schema)
        >>> df = await builder.build_async(client)  # Parallel + cache
        >>> df = await builder.build_async(client, use_cache=False)  # No cache
    """
```

**Algorithm**:

```
1. Determine project_gid from self._project
2. Get configuration:
   - max_concurrent = max_concurrent_sections or config.dataframe.max_concurrent_sections
   - cache_provider = client._cache_provider if use_cache else None

3. IF use_cache AND cache_provider:
   a. Get all task GIDs from project (lightweight call or cached)
   b. Build cache keys: [make_dataframe_key(task_gid, project_gid) for task_gid in task_gids]
   c. cached_entries = cache_provider.get_batch(keys, EntryType.DATAFRAME)
   d. Partition into: cache_hits, cache_misses
   e. IF all hits: Build DataFrame from cached data, RETURN

4. IF use_parallel_fetch:
   a. TRY parallel section fetch:
      i.   sections = await sections_client.list_for_project_async(project_gid).collect()
      ii.  IF no sections: fall through to serial fetch
      iii. Create semaphore(max_concurrent)
      iv.  tasks_by_section = await asyncio.gather(*[
               fetch_section_tasks(section.gid, semaphore)
               for section in sections
           ], return_exceptions=True)
      v.   IF any exception: log warning, GOTO serial fallback
      vi.  Flatten and deduplicate tasks by GID
   b. EXCEPT Exception: log warning, GOTO serial fallback

5. SERIAL FALLBACK:
   a. tasks = await tasks_client.list_async(project=project_gid).collect()

6. Apply section filtering (self._sections) if specified

7. IF use_cache AND cache_provider AND fetched_tasks:
   a. Build CacheEntry for each task (version=task.modified_at)
   b. cache_provider.set_batch(entries)

8. Build and return DataFrame using existing extraction logic
```

#### 2. ParallelSectionFetcher (Internal Helper)

**Location**: `/src/autom8_asana/dataframes/builders/parallel_fetch.py` (NEW FILE)

```python
@dataclass
class ParallelSectionFetcher:
    """Coordinates parallel task fetching across project sections.

    Per FR-FETCH-003: Concurrent section fetches.
    Per FR-FETCH-004: Configurable concurrency limit.
    Per FR-FETCH-006: Deduplication of multi-homed tasks.

    This is an internal implementation detail, not part of public API.
    """

    sections_client: SectionsClient
    tasks_client: TasksClient
    project_gid: str
    max_concurrent: int = 8
    opt_fields: list[str] | None = None
    logger: LogProvider | None = None

    async def fetch_all(self) -> FetchResult:
        """Fetch all tasks via parallel section fetch.

        Returns:
            FetchResult with tasks list and metadata.

        Raises:
            ParallelFetchError: If parallel fetch fails (caller should fallback).
        """
        ...

    async def _fetch_section(
        self,
        section_gid: str,
        semaphore: asyncio.Semaphore,
    ) -> list[Task]:
        """Fetch tasks from a single section with semaphore control."""
        async with semaphore:
            return await self.tasks_client.list_async(
                section=section_gid,
                opt_fields=self.opt_fields,
            ).collect()


@dataclass
class FetchResult:
    """Result of parallel section fetch."""
    tasks: list[Task]
    sections_fetched: int
    total_api_calls: int
    fetch_time_ms: float
```

#### 3. SaveSession Cache Invalidation Update

**Location**: `/src/autom8_asana/persistence/session.py`

Update `_invalidate_cache_for_results()`:

```python
async def _invalidate_cache_for_results(
    self,
    crud_result: SaveResult,
    action_results: list[ActionResult],
) -> None:
    """Invalidate cache entries for successfully mutated entities.

    Per FR-INVALIDATE-001: Invalidates DATAFRAME entries for mutated tasks.
    Per FR-INVALIDATE-002: Includes EntryType.DATAFRAME in invalidation.
    Per FR-INVALIDATE-003: Invalidates all project contexts via memberships.
    """
    cache = getattr(self._client, "_cache_provider", None)
    if cache is None:
        return

    from autom8_asana.cache.entry import EntryType
    from autom8_asana.cache.dataframes import invalidate_task_dataframes

    gids_to_invalidate: set[str] = set()
    # ... existing collection logic ...

    # Existing invalidation (TASK, SUBTASKS)
    for gid in gids_to_invalidate:
        try:
            cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
        except Exception as exc:
            # Log and continue
            ...

    # NEW: DataFrame invalidation with project context
    for gid in gids_to_invalidate:
        try:
            # Get entity to access memberships
            entity = self._tracker.get_entity(gid)
            if entity and hasattr(entity, "memberships") and entity.memberships:
                project_gids = [
                    m.get("project", {}).get("gid")
                    for m in entity.memberships
                    if m.get("project", {}).get("gid")
                ]
                if project_gids:
                    invalidate_task_dataframes(gid, project_gids, cache)
            # Fallback: invalidate with known project context if available
            elif self._current_project_gid:
                invalidate_task_dataframes(gid, [self._current_project_gid], cache)
        except Exception as exc:
            # FR-INVALIDATE-005: Don't fail commit on invalidation error
            if self._log:
                self._log.warning(
                    "dataframe_cache_invalidation_failed",
                    gid=gid,
                    error=str(exc),
                )
```

#### 4. DataFrameConfig

**Location**: `/src/autom8_asana/config.py`

```python
@dataclass(frozen=True)
class DataFrameConfig:
    """Configuration for DataFrame operations.

    Per FR-CONFIG-001: Parallel fetch enabled by default.
    Per FR-CONFIG-005: Configurable max_concurrent_sections.

    Attributes:
        parallel_fetch_enabled: Enable parallel section fetch (default True).
        max_concurrent_sections: Maximum concurrent section fetches (default 8).
            Must be between 1 and 20. Higher values may hit rate limits.
        cache_enabled: Enable automatic DataFrame caching (default True).
    """

    parallel_fetch_enabled: bool = True
    max_concurrent_sections: int = 8
    cache_enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 1 <= self.max_concurrent_sections <= 20:
            raise ConfigurationError(
                f"max_concurrent_sections must be 1-20, got {self.max_concurrent_sections}"
            )
```

Add to `AsanaConfig`:

```python
@dataclass
class AsanaConfig:
    # ... existing fields ...
    dataframe: DataFrameConfig = field(default_factory=DataFrameConfig)
```

#### 5. Convenience Method: project.to_dataframe_async()

**Decision**: Yes, implement `to_dataframe_async()` on Project model to call `build_async()` internally.

**Location**: Consumer-side model or SDK extension point

```python
async def to_dataframe_async(
    self,
    client: AsanaClient,
    task_type: str = "Task",
    schema: DataFrameSchema | None = None,
    sections: list[str] | None = None,
    **kwargs,
) -> pl.DataFrame:
    """Extract project tasks to DataFrame with parallel fetch.

    Zero-configuration entry point for DataFrame extraction with
    automatic performance optimization.

    Args:
        client: AsanaClient with configured cache.
        task_type: Task type filter (default "Task").
        schema: DataFrameSchema for extraction (default: auto-detect).
        sections: Optional section name filter.
        **kwargs: Passed to build_async (use_parallel_fetch, use_cache, etc.)

    Returns:
        Polars DataFrame with task data.

    Example:
        >>> df = await project.to_dataframe_async(client)
        >>> df = await project.to_dataframe_async(client, task_type="Unit")
    """
    from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder

    schema = schema or auto_detect_schema(task_type)
    builder = ProjectDataFrameBuilder(
        project=self,
        task_type=task_type,
        schema=schema,
        sections=sections,
    )
    return await builder.build_async(client, **kwargs)
```

---

### Data Model

#### Cache Entry Structure

Per existing `CacheEntry` dataclass (no changes needed):

```python
@dataclass(frozen=True)
class CacheEntry:
    key: str                    # "{task_gid}:{project_gid}"
    data: dict[str, Any]        # Extracted row data
    entry_type: EntryType       # EntryType.DATAFRAME
    version: datetime           # task.modified_at
    cached_at: datetime         # When cached
    ttl: int | None = 300       # 5 minutes default
    project_gid: str | None     # Project context
    metadata: dict[str, Any]    # {"schema_version": "1.0.0"}
```

#### Key Format

Per ADR-0021, key format is `{task_gid}:{project_gid}`:

```python
def make_dataframe_key(task_gid: str, project_gid: str) -> str:
    return f"{task_gid}:{project_gid}"
```

---

### API Contracts

#### ProjectDataFrameBuilder.build_async()

```python
async def build_async(
    self,
    client: AsanaClient,
    *,
    use_parallel_fetch: bool = True,
    use_cache: bool = True,
    max_concurrent_sections: int | None = None,
) -> pl.DataFrame
```

#### ParallelSectionFetcher.fetch_all()

```python
async def fetch_all(self) -> FetchResult

@dataclass
class FetchResult:
    tasks: list[Task]
    sections_fetched: int
    total_api_calls: int
    fetch_time_ms: float
```

#### CacheProvider Batch Operations (Existing)

```python
def get_batch(
    self,
    keys: list[str],
    entry_type: EntryType,
) -> dict[str, CacheEntry | None]

def set_batch(
    self,
    entries: dict[str, CacheEntry],
) -> None
```

---

### Data Flow

#### Sequence Diagram: Cold Fetch (No Cache)

```
Consumer                Builder              Fetcher           SectionsClient    TasksClient       Cache
   |                       |                    |                    |                |              |
   |--build_async()------->|                    |                    |                |              |
   |                       |--get_batch()-------|---------------------------------------------->|
   |                       |<--{} (all miss)----|----------------------------------------------<|
   |                       |                    |                    |                |              |
   |                       |--fetch_all()------>|                    |                |              |
   |                       |                    |--list_for_project->|                |              |
   |                       |                    |<--[sections]-------|                |              |
   |                       |                    |                    |                |              |
   |                       |                    |--gather([         |                |              |
   |                       |                    |    list_async(s1)-|--------------->|              |
   |                       |                    |    list_async(s2)-|--------------->|              |
   |                       |                    |    ...            |                |              |
   |                       |                    |  ])               |                |              |
   |                       |                    |<--[tasks_s1,s2...]|<---------------|              |
   |                       |<--FetchResult------|                    |                |              |
   |                       |                    |                    |                |              |
   |                       |--set_batch(entries)------------------------------------------------>|
   |                       |                    |                    |                |              |
   |<--DataFrame-----------|                    |                    |                |              |
```

#### Sequence Diagram: Warm Fetch (Full Cache Hit)

```
Consumer                Builder              Cache
   |                       |                    |
   |--build_async()------->|                    |
   |                       |--get_batch()------>|
   |                       |<--{all entries}----|
   |                       |                    |
   |                       | (skip fetch)       |
   |                       |                    |
   |<--DataFrame-----------|                    |
```

#### Sequence Diagram: Partial Cache (Mixed)

```
Consumer                Builder              Fetcher           Cache
   |                       |                    |                 |
   |--build_async()------->|                    |                 |
   |                       |--get_batch()------------------------->|
   |                       |<--{90% hits, 10% miss}----------------|
   |                       |                    |                 |
   |                       |--fetch_missing---->|                 |
   |                       |  (only 10% tasks)  |                 |
   |                       |<--FetchResult------|                 |
   |                       |                    |                 |
   |                       |--set_batch(new)------------------->|
   |                       |                    |                 |
   |                       | (merge cached + fetched)            |
   |<--DataFrame-----------|                    |                 |
```

#### Sequence Diagram: Invalidation Flow

```
Consumer              SaveSession            Cache           dataframes.py
   |                       |                    |                 |
   |--commit_async()------>|                    |                 |
   |                       | (execute ops)      |                 |
   |                       |                    |                 |
   |                       |--_invalidate_cache_for_results()    |
   |                       |  (for each mutated gid):            |
   |                       |    |                |                 |
   |                       |    |--invalidate(gid, [TASK, SUBTASKS])-->|
   |                       |    |                |                 |
   |                       |    |--get entity.memberships        |
   |                       |    |--invalidate_task_dataframes----|---------------->|
   |                       |    |                |<--invalidate(key, DATAFRAME)---|
   |                       |                    |                 |
   |<--SaveResult----------|                    |                 |
```

#### Sequence Diagram: Fallback Flow

```
Consumer                Builder              Fetcher           TasksClient
   |                       |                    |                 |
   |--build_async()------->|                    |                 |
   |                       |--fetch_all()------>|                 |
   |                       |                    |--list_for_project_async()
   |                       |                    |<--EXCEPTION-----|
   |                       |                    |                 |
   |                       |<--ParallelFetchError                |
   |                       |                    |                 |
   |                       | (log warning)      |                 |
   |                       |                    |                 |
   |                       |--list_async(project=gid)------------>|
   |                       |<--[tasks]---------------------------|
   |                       |                    |                 |
   |<--DataFrame-----------|                    |                 |
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Parallel fetch strategy | Section-parallel with semaphore | Sections are natural parallelization unit; semaphore prevents rate limit exhaustion | ADR-0115 |
| Batch cache pattern | Check-fetch-populate | Minimizes API calls; enables partial cache scenarios | ADR-0116 |
| Invalidation hook | Extend existing `_invalidate_cache_for_results` | Non-invasive; reuses proven pattern | ADR-0117 |
| Cache architecture | Single-level per-task (no hierarchy) | Multi-level rejected as over-engineering | ADR-0118 |
| Convenience API | `to_dataframe_async()` calls `build_async()` | Zero-config goal; improves discoverability | This TDD |
| Metrics exposure | Structured logging via LogProvider | Integrates with existing observability | This TDD |
| Redis batch optimization | Deferred (sequential acceptable) | In-memory sufficient for most cases; optimize later | This TDD |

---

## Complexity Assessment

**Level: Module**

This is a **Module-level** change:

- Clear API surface (`build_async()`, `to_dataframe_async()`)
- Contained boundaries (DataFrame builder, cache integration, invalidation hook)
- No new external dependencies
- No new deployment artifacts
- Builds on existing infrastructure

**Justification for Module (not Service)**:

- No new configuration services needed
- No new background processes
- No cross-service coordination
- Single-process operation

**Justification for Module (not Script)**:

- Multiple consumers of same logic (builder, convenience method)
- Non-trivial error handling (fallback, partial cache)
- Configuration surface (max_concurrent, opt-out)

---

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| **1** | Parallel section fetch in `build_async()` | None | 2 days |
| **2** | Batch cache integration | Phase 1 | 1 day |
| **3** | SaveSession invalidation, config, metrics | Phase 2 | 1 day |

### Phase 1: Parallel Section Fetch

1. Create `ParallelSectionFetcher` helper class
2. Add `build_async()` to `ProjectDataFrameBuilder`
3. Implement fallback to serial fetch
4. Add unit tests for parallel fetch logic
5. Add integration test with mocked clients

### Phase 2: Batch Cache Integration

1. Wire `get_batch()` into `build_async()` for cache lookup
2. Wire `set_batch()` for cache population after fetch
3. Implement partial cache scenario (fetch only misses)
4. Add tests for cache hit/miss scenarios

### Phase 3: Invalidation, Configuration, Metrics

1. Update `_invalidate_cache_for_results()` with `EntryType.DATAFRAME`
2. Add `DataFrameConfig` to `AsanaConfig`
3. Add metrics logging (fetch time, cache hit rate)
4. Add `to_dataframe_async()` convenience method
5. Integration tests for full flow

### Migration Strategy

**No migration required**. This is additive:

- Existing `build()` method unchanged (backward compatible)
- New `build_async()` method is opt-in
- Cache integration is automatic when `CacheProvider` configured
- Consumers can disable via `use_cache=False` or `use_parallel_fetch=False`

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Rate limit exhaustion | High - 429 errors | Low | Semaphore limits concurrent requests; token bucket rate limiter exists; default 8 concurrent is conservative |
| Partial section failure | Medium - incomplete data | Medium | Fail-all approach with automatic serial fallback; log warning |
| Cache memory pressure | Medium - OOM | Low | LRU eviction (max 10,000 entries); 5-min TTL; TieredCacheProvider for production |
| Multi-homed task invalidation miss | Low - stale data | Medium | Query `task.memberships`; TTL ensures eventual consistency |
| Performance target miss | High - initiative failure | Low | Benchmark tests in CI; fallback maintains functionality |

---

## Observability

### Metrics

Exposed via structured logging (`LogProvider`):

| Metric | Type | Description |
|--------|------|-------------|
| `dataframe_build_started` | Event | Build operation initiated |
| `dataframe_build_completed` | Event | Build operation completed |
| `dataframe_fetch_strategy` | Attribute | "parallel" or "serial" |
| `dataframe_fetch_time_ms` | Gauge | Total fetch time |
| `dataframe_cache_hits` | Counter | Number of cache hits |
| `dataframe_cache_misses` | Counter | Number of cache misses |
| `dataframe_cache_hit_rate` | Gauge | Computed hit rate |
| `dataframe_sections_fetched` | Counter | Sections fetched in parallel |
| `dataframe_fallback_triggered` | Event | Parallel fetch failed, using serial |

### Logging

```python
# Build started
self._log.info(
    "dataframe_build_started",
    project_gid=project_gid,
    use_parallel_fetch=use_parallel_fetch,
    use_cache=use_cache,
)

# Build completed
self._log.info(
    "dataframe_build_completed",
    project_gid=project_gid,
    task_count=len(tasks),
    fetch_strategy="parallel" if used_parallel else "serial",
    fetch_time_ms=fetch_time_ms,
    cache_hits=cache_hits,
    cache_misses=cache_misses,
    cache_hit_rate=cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0,
)

# Fallback triggered
self._log.warning(
    "dataframe_fallback_triggered",
    project_gid=project_gid,
    reason=str(error),
)
```

### Alerting

No new alerts for this feature. Existing rate limit monitoring sufficient.

---

## Testing Strategy

### Unit Tests

- `test_build_async_parallel_fetch`: Verify parallel fetch with mocked clients
- `test_build_async_serial_fallback`: Verify fallback on parallel failure
- `test_build_async_cache_hit`: Verify cache hit skips fetch
- `test_build_async_cache_miss`: Verify cache miss triggers fetch
- `test_build_async_partial_cache`: Verify partial cache fetches only misses
- `test_build_async_deduplication`: Verify multi-homed tasks deduplicated
- `test_build_async_empty_sections`: Verify empty sections handled
- `test_build_async_opt_out`: Verify `use_parallel_fetch=False` and `use_cache=False`

### Integration Tests

- `test_savesession_invalidates_dataframe_cache`: Verify invalidation on commit
- `test_full_flow_cold_warm`: Verify cold then warm fetch pattern
- `test_fallback_on_api_error`: Verify graceful degradation

### Performance Tests

- `benchmark_cold_start_3500_tasks`: Target <10 seconds
- `benchmark_warm_cache_3500_tasks`: Target <1 second
- `benchmark_partial_cache_10_percent_miss`: Target <2 seconds

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Should `project.to_dataframe_async()` call `build_async()` internally?~~ | Architect | Session 3 | **YES** - Zero-config goal, improves discoverability |
| ~~Should metrics use structured logging or callback interface?~~ | Architect | Session 3 | **Structured logging** - Integrates with existing LogProvider |
| ~~Is sequential `get_batch()` acceptable for Redis?~~ | Architect | Session 3 | **YES (deferred)** - In-memory sufficient; optimize later |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial draft |

---

## Appendix A: Requirement Traceability

| PRD Requirement | Design Element |
|-----------------|----------------|
| FR-FETCH-001 | `ProjectDataFrameBuilder.build_async()` |
| FR-FETCH-002 | `ParallelSectionFetcher.fetch_all()` calls `SectionsClient.list_for_project_async()` |
| FR-FETCH-003 | `asyncio.gather()` in `ParallelSectionFetcher` |
| FR-FETCH-004 | `asyncio.Semaphore(max_concurrent_sections)` |
| FR-FETCH-005 | Skip empty sections in `_fetch_section()` |
| FR-FETCH-006 | Deduplicate by task GID in `FetchResult` |
| FR-FETCH-007 | Pass `opt_fields` to `TasksClient.list_async()` |
| FR-FETCH-008 | Fall back to project-level fetch if no sections |
| FR-CACHE-001 | `get_batch()` call before fetch in `build_async()` |
| FR-CACHE-002 | `CacheProvider.get_batch()` (existing protocol) |
| FR-CACHE-003 | `make_dataframe_key()` (existing) |
| FR-CACHE-004 | Partial cache logic in `build_async()` |
| FR-CACHE-005 | `set_batch()` call after fetch in `build_async()` |
| FR-CACHE-006 | `CacheEntry.version = task.modified_at` |
| FR-CACHE-007 | `CacheEntry.ttl = 300` (default) |
| FR-CACHE-008 | try/except with logging in cache operations |
| FR-INVALIDATE-001 | Update to `_invalidate_cache_for_results()` |
| FR-INVALIDATE-002 | Add `EntryType.DATAFRAME` to invalidation |
| FR-INVALIDATE-003 | Query `entity.memberships` for project GIDs |
| FR-INVALIDATE-004 | Fallback to `self._current_project_gid` |
| FR-INVALIDATE-005 | try/except around invalidation, don't fail commit |
| FR-INVALIDATE-006 | All operation types included via `gids_to_invalidate` |
| FR-CONFIG-001 | `DataFrameConfig.parallel_fetch_enabled = True` |
| FR-CONFIG-002 | `build_async(use_parallel_fetch=False)` |
| FR-CONFIG-003 | `build_async()` checks `client._cache_provider` |
| FR-CONFIG-004 | `build_async(use_cache=False)` |
| FR-CONFIG-005 | `DataFrameConfig.max_concurrent_sections` |
| FR-CONFIG-006 | Uses existing `CacheConfig.ttl.default_ttl` |
| FR-FALLBACK-001 | try/except in parallel fetch, call serial fetch |
| FR-FALLBACK-002 | Transparent fallback, returns DataFrame |
| FR-FALLBACK-003 | `self._log.warning("dataframe_fallback_triggered", ...)` |
| FR-FALLBACK-004 | `return_exceptions=True` in `asyncio.gather()`, check for exceptions |
| FR-FALLBACK-005 | Token bucket rate limiter handles 429 retry |
| FR-FALLBACK-006 | Circuit breaker integration (existing) |

---

## Appendix B: File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/autom8_asana/dataframes/builders/project.py` | UPDATE | Add `build_async()` method |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | NEW | `ParallelSectionFetcher` helper |
| `src/autom8_asana/persistence/session.py` | UPDATE | Add `EntryType.DATAFRAME` to invalidation |
| `src/autom8_asana/config.py` | UPDATE | Add `DataFrameConfig` to `AsanaConfig` |
| `src/autom8_asana/cache/dataframes.py` | UPDATE | Add `invalidate_task_dataframes_async()` |
| `tests/dataframes/builders/test_project_async.py` | NEW | Unit tests for `build_async()` |
| `tests/dataframes/builders/test_parallel_fetch.py` | NEW | Unit tests for parallel fetcher |
| `tests/persistence/test_session_dataframe_invalidation.py` | NEW | Integration tests for invalidation |

---

## Quality Gate Checklist

- [x] Traces to approved PRD (PRD-WATERMARK-CACHE)
- [x] All significant decisions have ADRs (ADR-0115 through ADR-0118)
- [x] Component responsibilities are clear
- [x] Interfaces are defined
- [x] Complexity level is justified (Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable
