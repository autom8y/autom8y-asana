---
status: superseded
superseded_by: /docs/reference/REF-cache-architecture.md
superseded_date: 2025-12-24
---

# PRD: Watermark Cache - Parallel Section Fetch

## Metadata

- **PRD ID**: PRD-WATERMARK-CACHE
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **Stakeholders**: SDK consumers, Platform team
- **Related PRDs**: None
- **Discovery Document**: `/docs/analysis/watermark-cache-discovery.md`
- **Prompt 0**: `/docs/initiatives/PROMPT-0-WATERMARK-CACHE.md`

---

## Problem Statement

Project-level DataFrame operations take **52-59 seconds** for a typical project (3,500+ tasks), making the SDK impractical for interactive use cases and operational workflows. Users run this operation frequently as it is a primitive for business operational logic. Back-to-back runs show no cache benefit despite having cache infrastructure in place.

The root cause is **serial paginated API fetching**, not cache architecture. The existing per-task cache with project context is correctly designed. The missing piece is **parallel section fetch** - fetching tasks from all sections concurrently rather than sequentially paginating through the entire project.

**Impact of not solving**: SDK remains unusable for interactive workflows. Users resort to workarounds (raw API calls, external caching) that fragment the codebase and bypass SDK guarantees.

---

## Goals & Success Metrics

### Primary Goal

Reduce project-level DataFrame cold-start latency from 52-59 seconds to under 10 seconds via parallel section fetch, while automatically leveraging the existing cache infrastructure.

### Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Cold start latency (3,500 tasks) | 52-59s | <10s | Benchmark test with production-sized project |
| Warm cache latency | ~1s (explicit wiring) | <1s (automatic) | Benchmark test with pre-populated cache |
| Partial cache latency (10% miss) | N/A | <2s | Benchmark test with 90% cache pre-populated |
| Single task cache hit | ~200ms (HTTP) | <5ms | Unit test with mocked cache |
| Cache hit rate (steady state) | 0% (not wired) | >95% | Metrics collection over 5-minute window |

### Secondary Goals

1. **Zero Configuration**: Default behavior provides performance improvement without consumer code changes
2. **Backward Compatibility**: Existing consumer code works without modification
3. **Graceful Degradation**: Failures fall back to current serial behavior transparently

---

## Scope

### In Scope

1. **Parallel Section Fetch**: Concurrent task fetching across project sections
2. **Automatic Cache Population**: Bulk fetch results populate the DataFrame cache without explicit wiring
3. **Batch Cache Operations**: Efficient batch lookup/store for 3,500+ entries
4. **SaveSession Invalidation**: Post-commit hook invalidates affected DataFrame cache entries
5. **Configuration Options**: Parallelism limits, opt-out mechanisms
6. **Metrics Exposure**: Cache hit/miss rates via existing metrics infrastructure

### Out of Scope (Explicitly Rejected per Exploration)

| Feature | Rationale |
|---------|-----------|
| Section-level cache | Sections have no `modified_at` field; staleness detection impossible |
| Project-level cache | Cache thrashing under write patterns (10 writes/hour = never warm) |
| Multi-level cache hierarchy | Over-engineering; "ghost reference problem" with moved tasks |
| Search API integration | Premium-only; 100-item limit; cannot detect removals |
| Manual cache warming API | Parallel fetch warms automatically; explicit API unnecessary |
| Background refresh | TTL expiration sufficient; adds complexity without clear benefit |
| Async batch operations in cache providers | Current sequential loops acceptable; Redis optimization deferred |

---

## Requirements

### Functional Requirements: Parallel Section Fetch (FR-FETCH)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-FETCH-001 | `ProjectDataFrameBuilder` SHALL support an async `build_async()` method that fetches tasks via parallel section fetch | Must | Unit test: `build_async()` returns identical DataFrame to `build()` with pre-fetched tasks |
| FR-FETCH-002 | Parallel fetch SHALL enumerate sections via `SectionsClient.list_for_project_async()` before fetching tasks | Must | Unit test: Section listing called once per `build_async()` invocation |
| FR-FETCH-003 | Parallel fetch SHALL fetch tasks from each section concurrently using `TasksClient.list_async(section=section_gid)` | Must | Unit test: All section fetches initiated before any completes; `asyncio.gather()` used |
| FR-FETCH-004 | Parallel fetch SHALL limit concurrent section fetches to a configurable maximum (default: 8) | Must | Unit test: With 12 sections and max_concurrent=8, no more than 8 requests in-flight simultaneously |
| FR-FETCH-005 | Parallel fetch SHALL skip empty sections (0 tasks) without error | Should | Unit test: Empty section does not produce error or empty result merge |
| FR-FETCH-006 | Parallel fetch SHALL aggregate tasks from all sections and deduplicate by task GID | Must | Unit test: Task appearing in multiple sections (multi-homed) appears once in result |
| FR-FETCH-007 | Parallel fetch SHALL preserve existing `opt_fields` configuration for task fetching | Must | Unit test: Custom `opt_fields` passed to builder are applied to all section fetches |
| FR-FETCH-008 | Parallel fetch SHALL work with projects that have no sections (unsectioned tasks) | Must | Unit test: Project with only "(no section)" tasks returns all tasks via project-level fetch |

### Functional Requirements: Batch Cache Operations (FR-CACHE)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-001 | `build_async()` SHALL check cache for existing DataFrame entries before fetching from API | Must | Unit test: Cache hit for all tasks results in zero API calls |
| FR-CACHE-002 | Cache lookup SHALL use `get_batch()` for efficient bulk retrieval | Must | Unit test: Single `get_batch()` call for N tasks, not N individual calls |
| FR-CACHE-003 | Cache lookup SHALL use key format `{task_gid}:{project_gid}` per existing `make_dataframe_key()` | Must | Unit test: Keys match format from `cache/dataframes.py` |
| FR-CACHE-004 | For partial cache hits, `build_async()` SHALL fetch only missing tasks via parallel section fetch | Must | Unit test: 90% cache hit results in fetching only 10% of tasks |
| FR-CACHE-005 | After API fetch, `build_async()` SHALL populate cache via `set_batch()` for all fetched tasks | Must | Unit test: After cold fetch, subsequent `build_async()` hits cache for all tasks |
| FR-CACHE-006 | Cache entries SHALL use `task.modified_at` as version for staleness detection | Must | Unit test: Task with newer `modified_at` than cached version triggers re-fetch |
| FR-CACHE-007 | Cache entries SHALL use default TTL of 300 seconds (5 minutes) | Must | Unit test: Entry created with `ttl=300`; entry expired after 300s returns miss |
| FR-CACHE-008 | Cache operations SHALL degrade gracefully on failure (log warning, continue without cache) | Must | Unit test: Cache provider raises exception; `build_async()` completes successfully |

### Functional Requirements: Cache Invalidation (FR-INVALIDATE)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-INVALIDATE-001 | `SaveSession.commit_async()` SHALL invalidate DataFrame cache entries for all mutated tasks | Must | Integration test: Task update via SaveSession invalidates its DataFrame cache entry |
| FR-INVALIDATE-002 | Invalidation SHALL include `EntryType.DATAFRAME` in addition to existing `TASK` and `SUBTASKS` | Must | Unit test: `cache.invalidate()` called with `EntryType.DATAFRAME` for each mutated task |
| FR-INVALIDATE-003 | Invalidation SHALL invalidate all project contexts for a task using `task.memberships` | Must | Unit test: Multi-homed task invalidates cache entries for all projects in memberships |
| FR-INVALIDATE-004 | Invalidation SHALL fall back to invalidating only known project context if `memberships` unavailable | Should | Unit test: Task without `memberships` attribute invalidates based on operation context |
| FR-INVALIDATE-005 | Invalidation SHALL NOT fail the commit if cache invalidation fails | Must | Unit test: Cache provider raises during invalidation; `commit_async()` succeeds |
| FR-INVALIDATE-006 | Invalidation SHALL be triggered for CREATE, UPDATE, and DELETE operations | Must | Unit test: All three operation types trigger cache invalidation |

### Functional Requirements: Configuration (FR-CONFIG)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CONFIG-001 | Parallel fetch SHALL be enabled by default (zero configuration goal) | Must | Unit test: Default `AsanaConfig` enables parallel fetch |
| FR-CONFIG-002 | Parallel fetch SHALL be disableable via `use_parallel_fetch=False` parameter on `build_async()` | Must | Unit test: `build_async(use_parallel_fetch=False)` uses serial project-level fetch |
| FR-CONFIG-003 | Cache integration SHALL be enabled by default when `CacheProvider` is configured | Must | Unit test: Client with `CacheProvider` auto-enables cache in `build_async()` |
| FR-CONFIG-004 | Cache integration SHALL be disableable via `use_cache=False` parameter on `build_async()` | Must | Unit test: `build_async(use_cache=False)` skips cache lookup and population |
| FR-CONFIG-005 | Maximum concurrent sections SHALL be configurable via `DataFrameConfig.max_concurrent_sections` | Should | Unit test: Custom `max_concurrent_sections=4` limits parallelism to 4 |
| FR-CONFIG-006 | Cache TTL SHALL be configurable via existing `CacheConfig.ttl.default_ttl` | Should | Unit test: Custom TTL applied to DataFrame cache entries |

### Functional Requirements: Graceful Degradation (FR-FALLBACK)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-FALLBACK-001 | If parallel section fetch fails, `build_async()` SHALL fall back to serial project-level fetch | Must | Unit test: Section listing fails; fallback to `list_async(project=project_gid)` succeeds |
| FR-FALLBACK-002 | Fallback to serial fetch SHALL be automatic and transparent to caller | Must | Unit test: Caller receives DataFrame without knowledge of fallback |
| FR-FALLBACK-003 | Fallback SHALL log a warning indicating degraded performance | Must | Unit test: Warning log emitted on fallback |
| FR-FALLBACK-004 | If individual section fetch fails, entire parallel fetch SHALL fail and trigger fallback | Must | Unit test: One section returns 500; all sections cancelled; serial fallback triggered |
| FR-FALLBACK-005 | Rate limit errors (429) SHALL NOT trigger fallback; retry with backoff instead | Must | Unit test: 429 response retried via existing retry handler; no fallback |
| FR-FALLBACK-006 | Circuit breaker trip SHALL trigger immediate fallback without retry | Should | Unit test: Circuit open; fallback triggered immediately |

### Non-Functional Requirements: Performance (NFR-PERF)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Cold start latency for 3,500-task project | <10 seconds | Benchmark: `build_async()` on project with 3,500 tasks, empty cache |
| NFR-PERF-002 | Warm cache latency for 3,500-task project | <1 second | Benchmark: `build_async()` on project with 3,500 tasks, fully populated cache |
| NFR-PERF-003 | Partial cache latency (10% miss) for 3,500-task project | <2 seconds | Benchmark: `build_async()` with 90% cache hits, 10% API fetches |
| NFR-PERF-004 | Single task cache hit latency | <5 milliseconds | Unit test: Cache lookup for single entry |
| NFR-PERF-005 | Batch cache lookup latency for 3,500 entries | <100 milliseconds | Benchmark: `get_batch()` for 3,500 keys (in-memory provider) |
| NFR-PERF-006 | Memory overhead per cached task | <2 KB | Measurement: Memory profiling of 3,500-entry cache |
| NFR-PERF-007 | API request count for parallel fetch (8 sections, 3,500 tasks) | <40 requests | Measurement: Request count for typical project |

### Non-Functional Requirements: Compatibility (NFR-COMPAT)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | Existing `ProjectDataFrameBuilder.build()` API unchanged | 100% compatible | All existing tests pass without modification |
| NFR-COMPAT-002 | Existing consumer code works without changes | Zero breaking changes | Integration tests with sample consumer code |
| NFR-COMPAT-003 | New `build_async()` returns identical DataFrame structure | Byte-identical schema | Unit test: Schema comparison between `build()` and `build_async()` results |
| NFR-COMPAT-004 | Python 3.10+ compatibility | Full support | CI matrix includes Python 3.10, 3.11, 3.12 |

### Non-Functional Requirements: Reliability (NFR-RELIABLE)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-RELIABLE-001 | Parallel fetch respects Asana rate limits | Zero 429 errors under normal load | Integration test: 10 concurrent `build_async()` calls |
| NFR-RELIABLE-002 | Cache failures do not fail DataFrame operations | 100% graceful degradation | Chaos test: Cache provider throws randomly |
| NFR-RELIABLE-003 | Partial API failures handled gracefully | Automatic fallback | Chaos test: Random section fetches fail |

---

## User Stories / Use Cases

### UC-1: Interactive Dashboard Refresh

**As a** business operator using the SDK for dashboard automation,
**I want** project DataFrame extraction to complete in under 10 seconds,
**So that** I can refresh operational dashboards without waiting a minute per project.

**Acceptance**: Cold start `project.to_dataframe_async()` completes in <10s for 3,500-task project.

### UC-2: Repeated Analysis Runs

**As a** data analyst running multiple analysis passes,
**I want** subsequent DataFrame extractions to be nearly instant,
**So that** I can iterate on analysis without re-fetching data.

**Acceptance**: Second `project.to_dataframe_async()` call completes in <1s due to cache.

### UC-3: Automated Workflow Execution

**As an** automation pipeline using SaveSession to update tasks,
**I want** my updates to automatically invalidate stale cache entries,
**So that** subsequent DataFrame extractions reflect my changes without waiting for TTL.

**Acceptance**: Task updated via SaveSession; immediate `build_async()` returns updated data.

### UC-4: Graceful Handling of API Issues

**As a** developer building on the SDK,
**I want** the SDK to handle API issues gracefully,
**So that** my application remains functional even when Asana has degraded performance.

**Acceptance**: Parallel fetch failure falls back to serial; user receives DataFrame with warning logged.

---

## Assumptions

| Assumption | Basis | Risk if Invalid |
|------------|-------|-----------------|
| Asana API allows 8 concurrent requests without rate limiting | Rate limit is 1500 req/60s = 25 req/s; 8 concurrent is well under | Fallback to serial; performance target missed |
| Typical projects have 8-12 sections | User feedback; production data analysis | More sections increases parallelism benefit; fewer reduces it |
| Task `modified_at` is reliable for staleness detection | Asana API contract; used elsewhere in SDK | False positives (unnecessary fetches) or negatives (stale data) |
| `task.memberships` is populated for multi-project invalidation | Requires explicit `opt_fields` in fetch | Partial invalidation; some stale entries may persist |
| In-memory cache is sufficient for typical use | Production workloads are single-process | Need Redis/S3 tier for multi-process; TieredCacheProvider exists |

---

## Dependencies

| Dependency | Owner | Status | Risk |
|------------|-------|--------|------|
| `SectionsClient.list_for_project_async()` | SDK (existing) | Available | None |
| `TasksClient.list_async(section=...)` | SDK (existing) | Available | None |
| `CacheProvider.get_batch()` / `set_batch()` | SDK (existing) | Available | Sequential implementation may need optimization for Redis |
| `SaveSession._invalidate_cache_for_results()` | SDK (existing) | Available; needs extension | Low - straightforward addition |
| `EventSystem.emit_post_commit()` | SDK (existing) | Available | None |
| Asana API rate limits | Asana | Stable (1500/60s) | External dependency; mitigated by token bucket |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Parallel fetch exhausts rate limit | Low | High - 429 errors | Token bucket rate limiter; semaphore limits concurrent requests; conservative default (8) |
| Section fetch fails partially | Medium | Medium - incomplete data | Fail-all with automatic serial fallback; log warning |
| Cache memory pressure | Low | Medium - OOM | LRU eviction (max 10,000 entries); 5-min TTL; TieredCacheProvider for production |
| DataFrame cache invalidation misses multi-homed tasks | Medium | Low - stale data | Query `task.memberships`; document requirement; TTL ensures eventual consistency |
| Performance target not met | Low | High - initiative failure | Benchmark tests in CI; fallback to serial maintains functionality |
| Breaking change to existing API | Low | High - consumer breakage | Additive-only changes; new `build_async()` method; existing `build()` unchanged |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should `project.to_dataframe_async()` convenience method call `build_async()` internally? | Architect | Session 3 | Determines API surface for zero-config goal |
| Should metrics be exposed via structured logging or callback interface? | Architect | Session 3 | Impacts observability integration |
| Is sequential `get_batch()` acceptable for Redis, or do we need pipeline support? | Architect | Session 3 | May defer to future optimization |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Requirements Analyst | Initial draft based on Discovery Analysis |

---

## Appendix A: Requirement Traceability

### Prompt 0 Requirements Mapping

| Prompt 0 Requirement | PRD Requirement(s) |
|---------------------|-------------------|
| Implement parallel section fetch in ProjectDataFrameBuilder | FR-FETCH-001 through FR-FETCH-008 |
| Wire batch cache operations into DataFrame build | FR-CACHE-001 through FR-CACHE-008 |
| Auto-populate task cache on bulk fetch | FR-CACHE-005 |
| Connect SaveSession post-commit to cache invalidation | FR-INVALIDATE-001 through FR-INVALIDATE-006 |
| Provide configuration for parallelism limits | FR-CONFIG-005 |
| Expose cache metrics | Deferred to existing CacheMetrics infrastructure |
| Support partial cache scenarios | FR-CACHE-004 |
| Fall back gracefully if parallel fetch fails | FR-FALLBACK-001 through FR-FALLBACK-006 |

### Performance Targets Mapping

| Prompt 0 Target | PRD Requirement |
|-----------------|-----------------|
| Cold start <10s | NFR-PERF-001 |
| Warm cache <1s | NFR-PERF-002 |
| Partial cache <2s | NFR-PERF-003 |
| Single task hit <5ms | NFR-PERF-004 |

---

## Appendix B: Discovery Findings Summary

Key findings from `/docs/analysis/watermark-cache-discovery.md`:

1. **Current State**: `ProjectDataFrameBuilder` expects pre-fetched tasks; latency is upstream
2. **API Capability**: `TasksClient.list_async(section=...)` enables section-scoped fetch
3. **Cache Infrastructure**: `get_batch()` / `set_batch()` exist; key format confirmed
4. **Invalidation Gap**: SaveSession invalidates TASK/SUBTASKS but not DATAFRAME entries
5. **Concurrency Safe**: 8 concurrent sections within rate limits (1500 req/60s)

---

## Quality Gate Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] Dependencies identified with owners
- [x] Risks documented with mitigations
- [x] No blocking open questions (all have owners assigned)
