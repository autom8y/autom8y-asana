---
status: superseded
superseded_by: /docs/reference/REF-cache-invalidation.md
superseded_date: 2025-12-24
---

# PRD: Cache Optimization Phase 2 - Fetch Path Cache Integration

## Metadata

- **PRD ID**: PRD-CACHE-OPT-P2
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **Stakeholders**: SDK Team, DataFrame Consumers
- **Related PRDs**:
  - [PRD-CACHE-PERF-FETCH-PATH](/docs/requirements/PRD-CACHE-PERF-FETCH-PATH.md) - P1 foundation
  - [PROMPT-MINUS-1-CACHE-PERFORMANCE-META](/docs/initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md) - Initiative scope

---

## Problem Statement

### The Problem

The autom8_asana SDK has a **10x cache performance gap** where warm DataFrame fetch operations take 8.84s instead of the expected <1s. Despite implementing cache infrastructure (TaskCacheCoordinator, batch operations, EntryType.TASK), the cache is **never populated** from the primary fetch path.

### Root Causes (per [DISCOVERY-CACHE-OPTIMIZATION-P2](/docs/analysis/DISCOVERY-CACHE-OPTIMIZATION-P2.md))

| # | Root Cause | Severity | Impact |
|---|------------|----------|--------|
| 1 | `list_async()` does not populate cache | **CRITICAL** | Cache never populated from primary fetch path |
| 2 | Miss handling fetches ALL tasks, not just misses | **HIGH** | Partial cache provides no benefit; full re-fetch on any miss |
| 3 | GID enumeration not cached | **MEDIUM** | Repeated API calls for section-task mappings |

### Who Experiences This

All SDK consumers using DataFrame extraction via:
- `project.to_dataframe_parallel_async()`
- `ProjectDataFrameBuilder.build_with_parallel_fetch_async()`
- Any repeated extraction from the same project

### Impact of Not Solving

- **Wasted API quota**: ~35+ unnecessary API calls per warm fetch
- **Poor user experience**: Unacceptable 8.84s latency for "cached" operations
- **Infrastructure underutilization**: TaskCacheCoordinator, batch operations unused
- **Scalability concerns**: Cannot efficiently extract data from large projects repeatedly

---

## Goals and Success Metrics

### Primary Goal

Achieve <1s warm fetch latency for DataFrame extraction by ensuring tasks fetched via `list_async()` are cached and subsequent fetches use the cache.

### Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Warm fetch latency (3,530 tasks) | 8.84s | <1.0s | `scripts/demo_parallel_fetch.py` |
| Cache hit rate (warm) | ~0% | >90% | `CacheMetrics.hit_rate` |
| API calls on warm fetch | >35 | 0 | Structured logging count |
| Cold fetch latency | ~13.55s | No regression (+/- 5%) | Benchmark comparison |

### Secondary Goals

- Maintain backward compatibility (no breaking API changes)
- Follow established patterns from P1 (graceful degradation, batch operations, structured logging)
- Enable incremental improvements (GID enumeration caching as SHOULD)

---

## Scope

### In Scope

| Area | Description |
|------|-------------|
| Cache population from `list_async()` | Populate Task cache after parallel fetch completes |
| Miss handling optimization | Fetch only missing GIDs, not all tasks |
| GID enumeration caching | Cache section-to-task-GID mappings (SHOULD priority) |
| Observability enhancements | Structured logging for cache operations |
| Test coverage | Unit and integration tests for new behavior |

### Out of Scope

| Area | Rationale |
|------|-----------|
| `list_async()` cache lookup | Complex due to pagination; population-only approach |
| Multi-project caching | Single project focus for this phase |
| Cache eviction policies | Existing TTL-based eviction sufficient |
| New cache backends | Use existing CacheProvider implementations |
| Detection caching in DataFrame path | Covered by separate P2-Detection initiative |
| Stories caching | Covered by separate P4-Stories initiative |
| Hydration caching | Covered by separate P3-Hydration initiative |

---

## Requirements

### Functional Requirements - Cache Population (FR-POP-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-POP-001 | After `fetch_all()` completes, batch-populate Task cache with all fetched tasks | Must | Tasks from first fetch appear in cache; second fetch shows >90% hit rate |
| FR-POP-002 | Use existing `TaskCacheCoordinator.populate_tasks_async()` for population | Must | No new cache population code; reuse existing coordinator |
| FR-POP-003 | Population uses entity-type TTL resolution (Business=3600s, Contact/Unit=900s, etc.) | Must | Cached entries have correct TTL per entity type |
| FR-POP-004 | Population includes all opt_fields from fetch (not just minimal fields) | Must | Cached tasks have complete field set matching `_BASE_OPT_FIELDS` |
| FR-POP-005 | Cache population occurs in builder, not in TasksClient.list_async() | Should | list_async() remains unchanged; builder owns population decision |

### Functional Requirements - Miss Handling (FR-MISS-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-MISS-001 | When cache has partial hits, fetch only missing GIDs (not all tasks) | Must | API calls proportional to miss count, not total task count |
| FR-MISS-002 | Add `fetch_by_gids(gids: list[str])` method to ParallelSectionFetcher | Must | Method exists and fetches only specified GIDs efficiently |
| FR-MISS-003 | Merge fetched tasks with cached tasks preserving original order | Must | DataFrame row order matches section/task ordering |
| FR-MISS-004 | Handle edge case: 100% cache hit (no API calls) | Must | Zero API calls when cache is fully warm |
| FR-MISS-005 | Handle edge case: 0% cache hit (full fetch) | Must | Behavior identical to current cold fetch |

### Functional Requirements - GID Enumeration (FR-ENUM-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ENUM-001 | Cache section-to-task-GID mappings after enumeration | Should | Second enumeration returns from cache, no API calls |
| FR-ENUM-002 | Use new `EntryType.SECTION_TASKS` for enumeration cache | Should | Distinct entry type prevents key collision with TASK entries |
| FR-ENUM-003 | TTL for enumeration cache matches section cache (1800s) | Should | Enumeration cache expires after 30 minutes |
| FR-ENUM-004 | Cache key format: `section:{section_gid}` | Should | Consistent with other section-scoped cache keys |
| FR-ENUM-005 | Graceful degradation: enumeration works if cache unavailable | Should | Cache failures do not prevent enumeration |

### Functional Requirements - Observability (FR-OBS-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-OBS-001 | Log cache population count and timing after batch populate | Must | Structured log includes `populated_count`, `population_time_ms` |
| FR-OBS-002 | Log cache hit/miss statistics per build operation | Must | Existing logging enhanced with hit rate per operation |
| FR-OBS-003 | Log API calls saved by cache (warm fetch path) | Should | Log includes `api_calls_saved` metric |
| FR-OBS-004 | Include `cache_source` field in logs ("task_cache", "enumeration_cache") | Should | Distinguish between task and enumeration cache hits |

### Non-Functional Requirements (NFR-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Warm fetch latency | <1.0s for 3,530 tasks | `time.perf_counter()` in demo script |
| NFR-PERF-002 | Cache hit rate on warm | >90% | `CacheMetrics.hit_rate` |
| NFR-PERF-003 | Cold fetch latency | No regression (+/- 5%) | Before/after benchmark comparison |
| NFR-PERF-004 | Cache population overhead | <100ms for 3,530 tasks | Measured via `population_time_ms` log |
| NFR-COMPAT-001 | Backward compatibility | No breaking changes | All existing tests pass without modification |
| NFR-COMPAT-002 | API signature preservation | No changes to public APIs | `to_dataframe_parallel_async()` signature unchanged |
| NFR-DEGRADE-001 | Cache failure isolation | Primary operation succeeds | Test with failing cache provider |
| NFR-DEGRADE-002 | Cache unavailable handling | Falls back to API fetch | Test with `cache_provider=None` |
| NFR-TEST-001 | Unit test coverage | >90% on new code | pytest-cov report |
| NFR-TEST-002 | Integration test coverage | Warm fetch scenario tested | Integration test in test suite |

---

## User Stories / Use Cases

### UC-1: Repeated DataFrame Extraction (Primary)

**As a** SDK consumer extracting project data,
**I want** the second extraction from the same project to be fast (<1s),
**So that** I can efficiently refresh dashboards, reports, or data pipelines without waiting for full API fetches.

**Scenario:**
1. User calls `project.to_dataframe_parallel_async(client)` - takes ~13s (cold)
2. User calls `project.to_dataframe_parallel_async(client)` again - takes <1s (warm)
3. Cache hit rate is >90%, API calls are 0

### UC-2: Partial Cache Invalidation

**As a** SDK consumer with modified tasks,
**I want** only the modified tasks to be re-fetched,
**So that** updates are efficient without re-fetching unchanged data.

**Scenario:**
1. User extracts project (populates cache)
2. Some tasks are modified externally (cache entries become stale)
3. User extracts again - only stale/missing tasks fetched via API
4. Unchanged tasks served from cache

### UC-3: Large Project Handling

**As a** SDK consumer working with large projects (5,000+ tasks),
**I want** cache operations to be efficient,
**So that** performance scales with project size.

**Scenario:**
1. User extracts 5,000-task project (cold fetch)
2. Cache population completes in <200ms
3. Second extraction completes in <2s with >90% hit rate

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Task cache infrastructure is functional | P1 implementation validated with 91 passing tests |
| InMemoryCacheProvider is default backend | SDK configuration defaults |
| Entity-type TTL resolution works correctly | Existing `_resolve_entity_ttl()` implementation |
| Batch operations (`get_batch`, `set_batch`) are efficient | P1 validation with 500-entry batches |
| Tasks fetched via `list_async()` have stable GIDs | Asana API contract |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `TaskCacheCoordinator` | SDK Team | Implemented (P1) |
| `CacheProvider.get_batch()` | SDK Team | Implemented |
| `CacheProvider.set_batch()` | SDK Team | Implemented |
| `EntryType.TASK` | SDK Team | Implemented |
| `ParallelSectionFetcher` | SDK Team | Implemented |
| `ProjectDataFrameBuilder` | SDK Team | Implemented |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache population adds latency to cold fetch | Medium | Low | Async population; target <100ms overhead |
| Memory pressure from caching 3,530+ tasks | Low | Medium | TTL-based eviction; memory-bounded cache |
| Opt_fields mismatch between fetch and cache | Medium | High | Use `_BASE_OPT_FIELDS` consistently |
| GID enumeration cache stale after task moves | Low | Low | Shorter TTL (1800s); section-level invalidation |
| Breaking existing tests | Low | High | Run full test suite before merge |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should `fetch_by_gids()` use individual `get_async()` calls or batch endpoint? | Architect | TDD Phase | Batch via section-scoped queries recommended |
| Should enumeration cache be project-scoped or section-scoped? | Architect | TDD Phase | Section-scoped for granularity |

---

## Priority Summary (MoSCoW)

### Must Have (Blocking Release)
- FR-POP-001 through FR-POP-004: Cache population
- FR-MISS-001 through FR-MISS-005: Miss handling
- FR-OBS-001, FR-OBS-002: Core observability
- NFR-PERF-001, NFR-PERF-002: Performance targets
- NFR-COMPAT-001, NFR-COMPAT-002: Backward compatibility
- NFR-DEGRADE-001, NFR-DEGRADE-002: Graceful degradation

### Should Have (High Value)
- FR-POP-005: Builder-owned population
- FR-ENUM-001 through FR-ENUM-005: GID enumeration caching
- FR-OBS-003, FR-OBS-004: Enhanced observability
- NFR-PERF-003, NFR-PERF-004: Performance guardrails

### Could Have (Nice to Have)
- Pre-warming cache during project load
- Cache hit/miss metrics in demo script output

### Won't Have (This Phase)
- `list_async()` cache lookup (only population)
- Multi-project cache coordination
- Cache eviction policy changes

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Requirements Analyst | Initial draft based on discovery findings |

---

## Appendix A: Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Discovery | `/docs/analysis/DISCOVERY-CACHE-OPTIMIZATION-P2.md` | Root cause analysis |
| P1 Learnings | `/docs/analysis/INTEGRATION-CACHE-PERF-P1-LEARNINGS.md` | Patterns to follow |
| Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md` | Initiative scope |
| P1 PRD | `/docs/requirements/PRD-CACHE-PERF-FETCH-PATH.md` | Foundation work |

## Appendix B: Key Files for Implementation

| File | Purpose | Key Changes |
|------|---------|-------------|
| `src/autom8_asana/dataframes/builders/project.py` | DataFrame builder | Add cache population after fetch; fix miss handling |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Parallel fetcher | Add `fetch_by_gids()` method |
| `src/autom8_asana/dataframes/builders/task_cache.py` | Cache coordinator | Existing - reuse |
| `src/autom8_asana/cache/entry.py` | Entry types | Add `SECTION_TASKS` (if SHOULD items implemented) |
| `tests/unit/dataframes/test_project_async.py` | Builder tests | Add warm fetch tests |
| `tests/integration/test_cache_warm_fetch.py` | Integration tests | New file for E2E validation |

## Appendix C: Test Cases Required

### Must Have Tests

| Test Case | Type | Validates |
|-----------|------|-----------|
| `test_warm_fetch_uses_cache` | Integration | FR-MISS-004, NFR-PERF-001 |
| `test_cache_populated_after_fetch` | Unit | FR-POP-001 |
| `test_partial_cache_hit_fetches_only_misses` | Unit | FR-MISS-001 |
| `test_fetch_by_gids_returns_only_requested` | Unit | FR-MISS-002 |
| `test_cache_population_graceful_degradation` | Unit | NFR-DEGRADE-001 |
| `test_cold_fetch_no_regression` | Integration | NFR-PERF-003 |

### Should Have Tests

| Test Case | Type | Validates |
|-----------|------|-----------|
| `test_enumeration_cache_hit` | Unit | FR-ENUM-001 |
| `test_enumeration_cache_ttl` | Unit | FR-ENUM-003 |
| `test_large_batch_population` | Unit | NFR-PERF-004 |
