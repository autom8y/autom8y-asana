# PRD: Cache Optimization Phase 3 - GID Enumeration Caching

## Metadata

- **PRD ID**: PRD-CACHE-OPT-P3
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **Stakeholders**: SDK Team, DataFrame Consumers
- **Related PRDs**:
  - [PRD-CACHE-OPTIMIZATION-P2](/docs/requirements/PRD-CACHE-OPTIMIZATION-P2.md) - Phase 2 (Task cache population)
  - [PRD-CACHE-PERF-FETCH-PATH](/docs/requirements/PRD-CACHE-PERF-FETCH-PATH.md) - Phase 1 foundation

---

## Problem Statement

### The Problem

The autom8_asana SDK warm DataFrame fetch operations take **9.67 seconds** instead of the target **<1 second**, despite Phase 2 task cache working correctly. A three-agent triage audit with unanimous consensus identified the root cause: **GID enumeration is NOT cached**.

### Root Cause Analysis (Three-Agent Triage Findings)

| Finding | Evidence |
|---------|----------|
| Task cache IS working | Log shows `cache_hit_skip_api_fetch` at 9.6s mark |
| GID enumeration NOT cached | 35+ API calls per fetch regardless of cache state |
| Time waste location | 9.5s spent on GID enumeration before cache is even consulted |

### Bottleneck Location

File: `src/autom8_asana/dataframes/builders/parallel_fetch.py` (lines 195-281)

| Function | Line | API Calls | Issue |
|----------|------|-----------|-------|
| `_list_sections()` | 195-198 | 1 per fetch | Not cached |
| `fetch_section_task_gids_async()` | 200-257 | Orchestrator | Calls uncached functions |
| `_fetch_section_gids()` | 259-281 | 1 per section | Not cached (N calls for N sections) |

**Total uncached API calls per warm fetch**: 1 (sections) + N (section GIDs) = 35+ calls

### Who Experiences This

All SDK consumers using DataFrame extraction via:
- `project.to_dataframe_parallel_async()`
- `ProjectDataFrameBuilder.build_with_parallel_fetch_async()`
- Any repeated extraction from the same project

### Impact of Not Solving

- **Wasted API quota**: 35+ unnecessary API calls per warm fetch
- **Poor user experience**: 9.67s latency for "cached" operations (target: <1s)
- **Phase 2 benefits unrealized**: Task cache works but is consulted too late
- **10x speedup blocked**: Cannot achieve target performance without GID caching

---

## Goals and Success Metrics

### Primary Goal

Achieve <1s warm fetch latency by caching GID enumeration results, eliminating 35+ API calls on warm fetches.

### Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Warm fetch latency | 9.67s | <1.0s | `scripts/demo_parallel_fetch.py` |
| API calls on warm fetch | 35+ | 0 | Structured logging count |
| GID enumeration cache hit rate | 0% | 100% | Cache metrics |
| Cold fetch latency | ~20s | No regression (+/- 5%) | Benchmark comparison |
| Cache speedup factor | 10x+ | 10x+ maintained | Warm vs cold ratio |

### Secondary Goals

- Maintain backward compatibility (no breaking API changes)
- Follow established patterns from Phase 1/Phase 2 (graceful degradation, structured logging)
- Minimal code changes (surgical scope)

---

## Scope

### In Scope

| Area | Description |
|------|-------------|
| Section list caching | Cache `_list_sections()` result per project |
| GID enumeration caching | Cache `fetch_section_task_gids_async()` result (section-to-GID mapping) |
| New EntryType values | Add entry types for section list and GID enumeration |
| Cache key format | Define consistent key format for new cache entries |
| TTL requirements | Define appropriate TTL values for enumeration data |
| Invalidation requirements | Define when cached enumeration becomes invalid |
| Graceful degradation | Cache failures must not break operations |
| Observability | Structured logging for GID cache operations |
| Test coverage | Unit and integration tests for new behavior |

### Out of Scope

| Area | Rationale |
|------|-----------|
| Task object caching | Already implemented in Phase 2 and working correctly |
| Changes to EntryType enum structure | Reuse existing infrastructure, only add new values |
| Changes to CacheProvider interface | Use existing `get`/`set` methods |
| Changes to other modules | Surgical scope to parallel_fetch.py only |
| Cache eviction policies | Existing TTL-based eviction sufficient |
| New cache backends | Use existing CacheProvider implementations |
| Multi-project caching coordination | Single project focus for this phase |

---

## Requirements

### Functional Requirements - Section List Caching (FR-SECTION-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SECTION-001 | Before calling Asana API in `_list_sections()`, check cache for existing section list | Must | Cache lookup occurs before API call; log shows `section_list_cache_check` |
| FR-SECTION-002 | On cache hit, return cached section list without API call | Must | No API call logged when cache hit; returns valid section list |
| FR-SECTION-003 | On cache miss, fetch from API and populate cache before returning | Must | API call logged; subsequent call shows cache hit |
| FR-SECTION-004 | Cache key format: `project:{project_gid}:sections` | Must | Cache entries use this exact key format |
| FR-SECTION-005 | Store section list as list of section GIDs with names | Must | Cached data includes `gid` and `name` for each section |

### Functional Requirements - GID Enumeration Caching (FR-GID-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-GID-001 | Before calling Asana API in `fetch_section_task_gids_async()`, check cache for existing GID mapping | Must | Cache lookup occurs before any section GID API calls |
| FR-GID-002 | On cache hit, return cached section-to-GID mapping without API calls | Must | Zero API calls for GID enumeration on cache hit; log shows `gid_enumeration_cache_hit` |
| FR-GID-003 | On cache miss, fetch from API and populate cache before returning | Must | API calls logged on miss; subsequent call shows cache hit |
| FR-GID-004 | Cache key format: `project:{project_gid}:gid_enumeration` | Must | Cache entries use this exact key format |
| FR-GID-005 | Store complete section-to-GID mapping as single cache entry | Must | Cached data is `dict[str, list[str]]` mapping section_gid to task_gids |
| FR-GID-006 | Include section count and total GID count in cached metadata | Should | Metadata includes `section_count` and `total_gid_count` for observability |

### Functional Requirements - Cache Behavior (FR-CACHE-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-001 | Add `EntryType.PROJECT_SECTIONS` for section list cache entries | Must | New entry type exists in `entry.py`; used by section list caching |
| FR-CACHE-002 | Add `EntryType.GID_ENUMERATION` for GID mapping cache entries | Must | New entry type exists in `entry.py`; used by GID enumeration caching |
| FR-CACHE-003 | TTL for `PROJECT_SECTIONS`: 1800 seconds (30 minutes) | Must | Cached section list expires after 30 minutes |
| FR-CACHE-004 | TTL for `GID_ENUMERATION`: 300 seconds (5 minutes) | Must | Cached GID mapping expires after 5 minutes |
| FR-CACHE-005 | Use project's `modified_at` as version for staleness detection when available | Should | Cache entry version set from project metadata if available |
| FR-CACHE-006 | Invalidate GID enumeration cache when task cache is explicitly cleared | Should | `clear_project_cache()` also clears GID enumeration for that project |

### Functional Requirements - Graceful Degradation (FR-DEGRADE-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DEGRADE-001 | Cache lookup failure does not prevent GID enumeration | Must | API fetch proceeds if cache read fails; operation completes successfully |
| FR-DEGRADE-002 | Cache population failure does not prevent returning results | Must | Results returned even if cache write fails; warning logged |
| FR-DEGRADE-003 | When cache_provider is None, bypass caching entirely | Must | No cache operations attempted; direct API fetch; no errors |
| FR-DEGRADE-004 | Cache errors logged as warnings, not raised as exceptions | Must | Cache failures produce warning logs, not exceptions |

### Functional Requirements - Observability (FR-OBS-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-OBS-001 | Log cache hit/miss for section list lookup | Must | Structured log includes `section_list_cache_hit: bool` |
| FR-OBS-002 | Log cache hit/miss for GID enumeration lookup | Must | Structured log includes `gid_enumeration_cache_hit: bool` |
| FR-OBS-003 | Log API calls saved by cache hit | Must | Log includes `api_calls_saved: int` on cache hit |
| FR-OBS-004 | Log cache population timing | Should | Log includes `cache_population_ms: float` after cache write |
| FR-OBS-005 | Log includes `cache_source` field distinguishing entry types | Should | Log field `cache_source` is `"section_list"` or `"gid_enumeration"` |
| FR-OBS-006 | Log GID count and section count on enumeration | Should | Log includes `section_count: int` and `gid_count: int` |

### Non-Functional Requirements - Performance (NFR-PERF-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Warm fetch latency | <1.0s for 3,530 tasks | `time.perf_counter()` in demo script |
| NFR-PERF-002 | API calls on warm fetch | 0 | Structured logging count |
| NFR-PERF-003 | Cold fetch latency | No regression (+/- 5% of ~20s baseline) | Before/after benchmark comparison |
| NFR-PERF-004 | Cache lookup overhead | <10ms per lookup | Measured via structured logging |
| NFR-PERF-005 | Cache population overhead | <50ms for GID enumeration | Measured via `cache_population_ms` log |
| NFR-PERF-006 | Cache speedup factor | 10x+ (maintained from Phase 2) | Warm vs cold latency ratio |

### Non-Functional Requirements - Compatibility (NFR-COMPAT-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | Backward compatibility | No breaking changes to public APIs | All existing tests pass without modification |
| NFR-COMPAT-002 | API signature preservation | `fetch_section_task_gids_async()` signature unchanged | Method signature comparison |
| NFR-COMPAT-003 | Return type preservation | Return types unchanged for all modified functions | Type annotation comparison |
| NFR-COMPAT-004 | Existing behavior preservation | Operations work identically when cache disabled | Test with `cache_provider=None` |

### Non-Functional Requirements - Graceful Degradation (NFR-DEGRADE-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-DEGRADE-001 | Cache failure isolation | Primary operation succeeds despite cache failure | Test with failing cache provider |
| NFR-DEGRADE-002 | Cache unavailable handling | Falls back to API fetch seamlessly | Test with `cache_provider=None` |
| NFR-DEGRADE-003 | Partial cache failure | Individual cache operation failure does not cascade | Test with intermittent cache failures |

### Non-Functional Requirements - Testing (NFR-TEST-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-TEST-001 | Unit test coverage | >90% on new code | pytest-cov report |
| NFR-TEST-002 | Integration test coverage | Warm fetch scenario tested | Integration test exists and passes |
| NFR-TEST-003 | Graceful degradation tests | All FR-DEGRADE-* validated | Dedicated test cases exist |

---

## User Stories / Use Cases

### UC-1: Repeated DataFrame Extraction (Primary)

**As a** SDK consumer extracting project data repeatedly,
**I want** the GID enumeration to be cached after the first fetch,
**So that** subsequent fetches complete in <1s instead of 9.67s.

**Scenario:**
1. User calls `project.to_dataframe_parallel_async(client)` - takes ~20s (cold)
2. GID enumeration completes, section list and GID mapping cached
3. Task cache populated (Phase 2)
4. User calls `project.to_dataframe_parallel_async(client)` again
5. GID enumeration cache hit - no API calls for sections or GID mapping
6. Task cache hit (Phase 2) - no API calls for tasks
7. Total warm fetch time: <1s
8. API calls on warm fetch: 0

### UC-2: Cache Expiration and Refresh

**As a** SDK consumer with a long-running session,
**I want** the GID enumeration cache to expire and refresh periodically,
**So that** I see newly added sections and tasks within a reasonable time.

**Scenario:**
1. User extracts project (caches GID enumeration with 5-minute TTL)
2. After 5 minutes, cache entry expires
3. Next extraction triggers fresh GID enumeration
4. New sections and tasks are discovered
5. Fresh data cached for next 5 minutes

### UC-3: Graceful Degradation

**As a** SDK consumer in an environment with unreliable cache,
**I want** GID enumeration to complete even if the cache fails,
**So that** my application remains functional.

**Scenario:**
1. User initiates DataFrame extraction
2. Cache lookup fails (connection error, timeout, etc.)
3. System logs warning but continues
4. GID enumeration proceeds via API calls
5. Results returned successfully
6. Cache population fails - warning logged, results still returned

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Phase 2 task cache is working correctly | Three-agent triage confirmed `cache_hit_skip_api_fetch` at 9.6s mark |
| GID enumeration results are stable within TTL | Asana API returns consistent section-task mappings |
| Section list changes infrequently | 30-minute TTL appropriate for section structure |
| Task additions/removals more frequent than section changes | 5-minute TTL for GID enumeration balances freshness vs. performance |
| Existing CacheProvider interface sufficient | `get`/`set` methods handle new entry types |
| ParallelSectionFetcher has access to cache_provider | Passed through from builder or globally available |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `CacheProvider` interface | SDK Team | Implemented |
| `CacheEntry` dataclass | SDK Team | Implemented |
| `EntryType` enum | SDK Team | Implemented (needs new values) |
| `ParallelSectionFetcher` | SDK Team | Implemented |
| Phase 2 task cache | SDK Team | Implemented and verified working |
| Structured logging infrastructure | SDK Team | Implemented |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GID enumeration cache stale after task moves between sections | Medium | Low | 5-minute TTL limits staleness; task cache handles actual data |
| Section list cache stale after section add/delete | Low | Low | 30-minute TTL; explicit cache clear available |
| Cache key collision with existing entries | Low | High | Distinct key format with `project:` prefix and type suffix |
| Increased memory usage from caching GID mappings | Low | Low | GID mappings are small (list of strings); TTL-based eviction |
| Breaking existing tests | Low | High | Run full test suite before merge |
| Cache provider not available in ParallelSectionFetcher | Medium | Medium | Add cache_provider parameter; graceful degradation if None |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All questions resolved via three-agent triage |

**Note**: The three-agent triage audit resolved all technical questions. The root cause is verified, the bottleneck code is identified, and the solution approach (caching GID enumeration) is validated.

---

## Priority Summary (MoSCoW)

### Must Have (Blocking Release)

- FR-SECTION-001 through FR-SECTION-005: Section list caching
- FR-GID-001 through FR-GID-005: GID enumeration caching
- FR-CACHE-001 through FR-CACHE-004: Entry types and TTLs
- FR-DEGRADE-001 through FR-DEGRADE-004: Graceful degradation
- FR-OBS-001 through FR-OBS-003: Core observability
- NFR-PERF-001, NFR-PERF-002: Performance targets
- NFR-COMPAT-001 through NFR-COMPAT-004: Backward compatibility
- NFR-DEGRADE-001 through NFR-DEGRADE-003: Graceful degradation
- NFR-TEST-001, NFR-TEST-002: Test coverage

### Should Have (High Value)

- FR-GID-006: Metadata for observability
- FR-CACHE-005, FR-CACHE-006: Version tracking and invalidation
- FR-OBS-004 through FR-OBS-006: Enhanced observability
- NFR-PERF-003 through NFR-PERF-006: Performance guardrails
- NFR-TEST-003: Graceful degradation tests

### Could Have (Nice to Have)

- Pre-warming GID enumeration cache during project load
- Cache statistics in demo script output
- Configurable TTL values via settings

### Won't Have (This Phase)

- Task object caching changes (Phase 2 scope)
- Cache infrastructure changes (EntryType enum structure, CacheProvider interface)
- Multi-project cache coordination
- Cache eviction policy changes

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Requirements Analyst | Initial draft based on three-agent triage findings |

---

## Appendix A: Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Phase 2 PRD | `/docs/requirements/PRD-CACHE-OPTIMIZATION-P2.md` | Prior phase requirements |
| Phase 1 PRD | `/docs/requirements/PRD-CACHE-PERF-FETCH-PATH.md` | Foundation work |
| Cache Entry Types | `src/autom8_asana/cache/entry.py` | Existing infrastructure |
| Parallel Fetcher | `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Bottleneck code |

## Appendix B: Key Files for Implementation

| File | Purpose | Key Changes |
|------|---------|-------------|
| `src/autom8_asana/cache/entry.py` | Entry type definitions | Add `PROJECT_SECTIONS` and `GID_ENUMERATION` entry types |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Parallel fetcher | Add cache lookup/population to `_list_sections()` and `fetch_section_task_gids_async()` |
| `tests/unit/dataframes/test_parallel_fetch.py` | Unit tests | Add GID enumeration cache tests |
| `tests/integration/test_gid_cache_warm_fetch.py` | Integration tests | New file for E2E validation |

## Appendix C: Test Cases Required

### Must Have Tests

| Test Case | Type | Validates |
|-----------|------|-----------|
| `test_section_list_cache_hit` | Unit | FR-SECTION-001, FR-SECTION-002 |
| `test_section_list_cache_miss_populates` | Unit | FR-SECTION-003 |
| `test_gid_enumeration_cache_hit` | Unit | FR-GID-001, FR-GID-002 |
| `test_gid_enumeration_cache_miss_populates` | Unit | FR-GID-003 |
| `test_warm_fetch_zero_api_calls` | Integration | NFR-PERF-002 |
| `test_warm_fetch_under_one_second` | Integration | NFR-PERF-001 |
| `test_cache_failure_graceful_degradation` | Unit | FR-DEGRADE-001, FR-DEGRADE-002 |
| `test_cache_provider_none_bypasses_cache` | Unit | FR-DEGRADE-003 |
| `test_cold_fetch_no_regression` | Integration | NFR-PERF-003 |

### Should Have Tests

| Test Case | Type | Validates |
|-----------|------|-----------|
| `test_section_list_ttl_expiration` | Unit | FR-CACHE-003 |
| `test_gid_enumeration_ttl_expiration` | Unit | FR-CACHE-004 |
| `test_cache_key_format_section_list` | Unit | FR-SECTION-004 |
| `test_cache_key_format_gid_enumeration` | Unit | FR-GID-004 |
| `test_observability_logs_cache_hit` | Unit | FR-OBS-001, FR-OBS-002 |
| `test_observability_logs_api_calls_saved` | Unit | FR-OBS-003 |

## Appendix D: Cache Key Format Specification

| Entry Type | Key Format | Example |
|------------|------------|---------|
| `PROJECT_SECTIONS` | `project:{project_gid}:sections` | `project:1234567890:sections` |
| `GID_ENUMERATION` | `project:{project_gid}:gid_enumeration` | `project:1234567890:gid_enumeration` |

## Appendix E: TTL Rationale

| Entry Type | TTL | Rationale |
|------------|-----|-----------|
| `PROJECT_SECTIONS` | 1800s (30 min) | Section structure changes infrequently; matches existing `SECTION` TTL |
| `GID_ENUMERATION` | 300s (5 min) | Task additions/removals more frequent; balances freshness vs. performance |

**Note**: TTL for `GID_ENUMERATION` is shorter than section list because task membership changes more frequently than section structure. A 5-minute TTL ensures reasonable freshness while still providing significant performance benefit (eliminates 35+ API calls for 5 minutes after each enumeration).
