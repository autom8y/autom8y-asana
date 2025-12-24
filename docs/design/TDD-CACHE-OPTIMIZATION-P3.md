# TDD: Cache Optimization Phase 3 - GID Enumeration Caching

## Metadata
- **TDD ID**: TDD-CACHE-OPT-P3
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: [PRD-CACHE-OPTIMIZATION-P3](/docs/requirements/PRD-CACHE-OPTIMIZATION-P3.md)
- **Related TDDs**:
  - [TDD-CACHE-OPTIMIZATION-P2](/docs/design/TDD-CACHE-OPTIMIZATION-P2.md) - Phase 2 (Task cache population)
  - [TDD-CACHE-PERF-FETCH-PATH](/docs/design/TDD-CACHE-PERF-FETCH-PATH.md) - Phase 1 foundation
- **Related ADRs**:
  - [ADR-0131](/docs/decisions/ADR-0131-gid-enumeration-cache-strategy.md) - GID enumeration cache strategy (NEW)
  - [ADR-0130](/docs/decisions/ADR-0130-cache-population-location.md) - Cache population location (Phase 2)

---

## Overview

This TDD defines the technical approach to achieve **10x speedup** (9.67s -> <1s) by caching GID enumeration results. The design adds two-tier caching to `ParallelSectionFetcher`: section list caching (TTL 1800s) and GID enumeration caching (TTL 300s). With this change, warm DataFrame fetches require zero API calls for enumeration, consulting only the already-working task cache from Phase 2.

---

## Requirements Summary

Per [PRD-CACHE-OPTIMIZATION-P3](/docs/requirements/PRD-CACHE-OPTIMIZATION-P3.md):

| Category | Key Requirements | Priority |
|----------|-----------------|----------|
| FR-SECTION-* | Cache section list with 1800s TTL | Must |
| FR-GID-* | Cache GID enumeration with 300s TTL | Must |
| FR-CACHE-* | Add `PROJECT_SECTIONS` and `GID_ENUMERATION` entry types | Must |
| FR-DEGRADE-* | Graceful degradation on cache failure | Must |
| FR-OBS-* | Structured logging for cache operations | Must/Should |
| NFR-PERF-001 | <1s warm fetch latency | Must |
| NFR-PERF-002 | 0 API calls on warm fetch | Must |
| NFR-COMPAT-* | No breaking changes | Must |

---

## System Context

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   DataFrame Build Path                   │
                    └─────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────┐    ┌──────────────────────────────────────────────────────┐
│  SDK Consumer   │───▶│          ProjectDataFrameBuilder                     │
│                 │    │  build_with_parallel_fetch_async()                   │
└─────────────────┘    └──────────────────────────────────────────────────────┘
                                              │
                          ┌───────────────────┴───────────────────┐
                          ▼                                       ▼
        ┌──────────────────────────────┐        ┌──────────────────────────────┐
        │    TaskCacheCoordinator      │        │   ParallelSectionFetcher     │
        │  - lookup_tasks_async()      │        │  - fetch_section_task_gids() │
        │  - populate_tasks_async()    │        │  - _list_sections() [CACHED] │
        │  (Phase 2 - working)         │        │  + cache_provider [NEW]      │
        └──────────────────────────────┘        └──────────────────────────────┘
                          │                                       │
                          ▼                                       ▼
        ┌──────────────────────────────┐        ┌──────────────────────────────┐
        │      CacheProvider           │◀───────│    GID Enumeration Cache     │
        │  - get() / set()             │        │  - PROJECT_SECTIONS [NEW]    │
        │  - get_batch() / set_batch() │        │  - GID_ENUMERATION [NEW]     │
        └──────────────────────────────┘        └──────────────────────────────┘
```

**Key Changes:**
- `ParallelSectionFetcher` gains `cache_provider` constructor parameter
- Two new `EntryType` values for GID-related caching
- Cache lookup/populate integrated into fetcher methods

---

## Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ParallelSectionFetcher (Enhanced)                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Constructor Changes                                                     ││
│  │  + cache_provider: CacheProvider | None = None                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  _list_sections() [ENHANCED] │  │  fetch_section_task_gids_async()     │ │
│  │  + Cache lookup first        │  │  [ENHANCED]                          │ │
│  │  + Cache populate on miss    │  │  + Cache lookup first                │ │
│  │  + Graceful degradation      │  │  + Cache populate on miss            │ │
│  │  + Structured logging        │  │  + Graceful degradation              │ │
│  └──────────────────────────────┘  └──────────────────────────────────────┘ │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Private Cache Helpers [NEW]                                          │   │
│  │  - _get_cached_sections() -> list[Section] | None                     │   │
│  │  - _cache_sections(sections: list[Section]) -> None                   │   │
│  │  - _get_cached_gid_enumeration() -> dict[str, list[str]] | None       │   │
│  │  - _cache_gid_enumeration(mapping: dict[str, list[str]]) -> None      │   │
│  │  - _make_cache_key(suffix: str) -> str                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         EntryType Enum (Enhanced)                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  + PROJECT_SECTIONS = "project_sections"   # TTL: 1800s                 ││
│  │  + GID_ENUMERATION = "gid_enumeration"     # TTL: 300s                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                  ProjectDataFrameBuilder (Minor Change)                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  build_with_parallel_fetch_async():                                      ││
│  │    fetcher = ParallelSectionFetcher(                                    ││
│  │        sections_client=client.sections,                                 ││
│  │        tasks_client=client.tasks,                                       ││
│  │        project_gid=project_gid,                                         ││
│  │        max_concurrent=max_concurrent,                                   ││
│  │        opt_fields=_BASE_OPT_FIELDS,                                     ││
│  │        cache_provider=task_cache_provider,  # [NEW - pass through]      ││
│  │    )                                                                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

| Component | Responsibility | Changes |
|-----------|---------------|---------|
| `ParallelSectionFetcher` | Section enumeration, task fetch, GID caching | ADD cache_provider param, cache helpers, cache integration |
| `EntryType` | Cache entry type enum | ADD `PROJECT_SECTIONS`, `GID_ENUMERATION` |
| `ProjectDataFrameBuilder` | DataFrame build orchestration | MINOR: Pass cache_provider to fetcher |

---

### Data Model

#### EntryType Additions

```python
# src/autom8_asana/cache/entry.py

class EntryType(str, Enum):
    """Types of cache entries with distinct versioning strategies."""

    TASK = "task"
    SUBTASKS = "subtasks"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"
    DATAFRAME = "dataframe"
    PROJECT = "project"
    SECTION = "section"
    USER = "user"
    CUSTOM_FIELD = "custom_field"
    DETECTION = "detection"

    # Per PRD-CACHE-OPT-P3 / ADR-0131: GID enumeration caching
    PROJECT_SECTIONS = "project_sections"  # TTL: 1800s (30 min)
    GID_ENUMERATION = "gid_enumeration"    # TTL: 300s (5 min)
```

#### Cache Entry Structures

| Entry Type | Key Format | Data Structure | TTL |
|------------|------------|----------------|-----|
| `PROJECT_SECTIONS` | `project:{project_gid}:sections` | `list[dict[str, str]]` | 1800s |
| `GID_ENUMERATION` | `project:{project_gid}:gid_enumeration` | `dict[str, list[str]]` | 300s |

**Section List Entry:**
```python
{
    "key": "project:1234567890:sections",
    "data": {
        "sections": [
            {"gid": "111", "name": "To Do"},
            {"gid": "222", "name": "In Progress"},
            {"gid": "333", "name": "Done"},
        ]
    },
    "entry_type": EntryType.PROJECT_SECTIONS,
    "version": datetime(2025, 1, 1, tzinfo=timezone.utc),
    "cached_at": datetime.now(timezone.utc),
    "ttl": 1800,
    "project_gid": "1234567890",
    "metadata": {
        "section_count": 3,
    },
}
```

**GID Enumeration Entry:**
```python
{
    "key": "project:1234567890:gid_enumeration",
    "data": {
        "section_gids": {
            "111": ["task1", "task2", "task3"],
            "222": ["task4", "task5"],
            "333": ["task6", "task7", "task8", "task9"],
        }
    },
    "entry_type": EntryType.GID_ENUMERATION,
    "version": datetime(2025, 1, 1, tzinfo=timezone.utc),
    "cached_at": datetime.now(timezone.utc),
    "ttl": 300,
    "project_gid": "1234567890",
    "metadata": {
        "section_count": 3,
        "total_gid_count": 9,
    },
}
```

---

### Data Flow

#### Cold Fetch Flow (First Call)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ProjectDataFrameBuilder.build_with_parallel_fetch_async()                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. Create Fetcher with Cache Provider                                       │
│     fetcher = ParallelSectionFetcher(..., cache_provider=task_cache_provider)│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. Enumerate GIDs                                                           │
│     section_gids_map = await fetcher.fetch_section_task_gids_async()        │
│                                                                              │
│     INSIDE fetch_section_task_gids_async():                                 │
│     ┌────────────────────────────────────────────────────────────────────┐  │
│     │  a. Check GID enumeration cache -> MISS                            │  │
│     │  b. Call _list_sections()                                          │  │
│     │     ┌──────────────────────────────────────────────────────────┐   │  │
│     │     │  Check sections cache -> MISS                             │   │  │
│     │     │  API call: list_for_project_async()                       │   │  │
│     │     │  Populate sections cache                                  │   │  │
│     │     │  Return sections                                          │   │  │
│     │     └──────────────────────────────────────────────────────────┘   │  │
│     │  c. Call _fetch_section_gids() x N [API calls]                     │  │
│     │  d. Populate GID enumeration cache                                 │  │
│     │  e. Return section_gids_map                                        │  │
│     └────────────────────────────────────────────────────────────────────┘  │
│     API Calls: 1 (sections) + N (section GIDs) = 35+                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. Task Cache Lookup -> All MISS (cold cache)                               │
│  4. Fetch Tasks via API                                                      │
│  5. Populate Task Cache                                                      │
│  6. Build DataFrame                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Cold Fetch Total Time:** ~20s (no regression from baseline)

---

#### Warm Fetch Flow (Second Call) - TARGET STATE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ProjectDataFrameBuilder.build_with_parallel_fetch_async()                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. Create Fetcher with Cache Provider                                       │
│     fetcher = ParallelSectionFetcher(..., cache_provider=task_cache_provider)│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. Enumerate GIDs                                                           │
│     section_gids_map = await fetcher.fetch_section_task_gids_async()        │
│                                                                              │
│     INSIDE fetch_section_task_gids_async():                                 │
│     ┌────────────────────────────────────────────────────────────────────┐  │
│     │  a. Check GID enumeration cache -> HIT!                            │  │
│     │  b. Return cached section_gids_map immediately                     │  │
│     │  API Calls: 0                                                       │  │
│     │  Time: <10ms                                                        │  │
│     └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. Task Cache Lookup -> All HIT! (Phase 2 working)                          │
│     API Calls: 0                                                             │
│     Time: <50ms                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. Build DataFrame from Cached Tasks                                        │
│     API Calls: 0                                                             │
│     Time: ~500ms (DataFrame construction)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Warm Fetch Target Time:** <1s (10x speedup achieved)
**API Calls on Warm Fetch:** 0

---

#### Partial Cache Flow (GID Cache Miss, Section Cache Hit)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  fetch_section_task_gids_async()                                             │
│                                                                              │
│  a. Check GID enumeration cache -> MISS (expired after 5 min)               │
│  b. Call _list_sections()                                                   │
│     ┌──────────────────────────────────────────────────────────────────┐    │
│     │  Check sections cache -> HIT (still valid, 30 min TTL)           │    │
│     │  Return cached sections immediately                               │    │
│     │  API Calls: 0                                                     │    │
│     └──────────────────────────────────────────────────────────────────┘    │
│  c. Call _fetch_section_gids() x N [API calls needed]                       │
│  d. Populate GID enumeration cache                                          │
│  e. Return section_gids_map                                                 │
│                                                                              │
│  API Calls: N (section GIDs only, not section list)                         │
│  Time: ~5-8s (GID enumeration only)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

This partial cache scenario demonstrates the benefit of two-tier caching: the section list (which changes rarely) can remain cached even when the GID enumeration (which changes more often) needs refresh.

---

### API Contracts

#### ParallelSectionFetcher Constructor (Enhanced)

```python
@dataclass
class ParallelSectionFetcher:
    """Coordinates parallel task fetching across project sections.

    Per ADR-0131: Now supports GID enumeration caching via optional
    cache_provider parameter.
    """

    sections_client: SectionsClient
    tasks_client: TasksClient
    project_gid: str
    max_concurrent: int = 8
    opt_fields: list[str] | None = None
    cache_provider: CacheProvider | None = None  # NEW: Per ADR-0131
    _api_call_count: int = field(default=0, init=False, repr=False)

    # TTL constants per PRD-CACHE-OPT-P3
    _SECTIONS_TTL: ClassVar[int] = 1800  # 30 minutes
    _GID_ENUM_TTL: ClassVar[int] = 300   # 5 minutes
```

#### Enhanced Methods

```python
async def _list_sections(self) -> list[Section]:
    """List all sections in the project with caching.

    Per FR-SECTION-001/002/003: Checks cache before API call,
    populates cache on miss.

    Returns:
        List of Section objects.
    """

async def fetch_section_task_gids_async(self) -> dict[str, list[str]]:
    """Enumerate task GIDs per section with caching.

    Per FR-GID-001/002/003: Checks cache before API calls,
    populates cache on miss.

    Returns:
        Dict mapping section_gid -> list of task_gids.
        Empty dict if project has no sections.
    """
```

#### Private Cache Helpers (New)

```python
def _make_cache_key(self, suffix: str) -> str:
    """Generate cache key for this project.

    Args:
        suffix: Key suffix ("sections" or "gid_enumeration")

    Returns:
        Formatted cache key, e.g., "project:1234567890:sections"
    """
    return f"project:{self.project_gid}:{suffix}"

def _get_cached_sections(self) -> list[Section] | None:
    """Attempt to retrieve sections from cache.

    Per FR-DEGRADE-001: Graceful degradation on cache failure.

    Returns:
        Cached sections if hit and not expired, None on miss or error.
    """

def _cache_sections(self, sections: list[Section]) -> None:
    """Populate cache with section list.

    Per FR-DEGRADE-002: Cache failure does not prevent operation.

    Args:
        sections: List of Section objects to cache.
    """

def _get_cached_gid_enumeration(self) -> dict[str, list[str]] | None:
    """Attempt to retrieve GID enumeration from cache.

    Per FR-DEGRADE-001: Graceful degradation on cache failure.

    Returns:
        Cached mapping if hit and not expired, None on miss or error.
    """

def _cache_gid_enumeration(
    self,
    section_gids: dict[str, list[str]],
) -> None:
    """Populate cache with GID enumeration.

    Per FR-DEGRADE-002: Cache failure does not prevent operation.

    Args:
        section_gids: Dict mapping section_gid -> task_gids.
    """
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Cache location | Fetcher level (inside `ParallelSectionFetcher`) | Encapsulation; fetcher owns enumeration | [ADR-0131](/docs/decisions/ADR-0131-gid-enumeration-cache-strategy.md) |
| Cache provider access | Constructor injection | Testability; explicit dependency; matches existing patterns | [ADR-0131](/docs/decisions/ADR-0131-gid-enumeration-cache-strategy.md) |
| Cache granularity | Per-project (not per-section) | Single cache lookup; simpler; same benefit | [ADR-0131](/docs/decisions/ADR-0131-gid-enumeration-cache-strategy.md) |
| Two-tier caching | Separate section list and GID enum | Different TTLs; PRD compliance; partial refresh | [ADR-0131](/docs/decisions/ADR-0131-gid-enumeration-cache-strategy.md) |
| Section list TTL | 1800s (30 min) | Section structure rarely changes | PRD FR-CACHE-003 |
| GID enumeration TTL | 300s (5 min) | Task membership changes more often | PRD FR-CACHE-004 |

---

## Complexity Assessment

**Level: Module**

This is an enhancement to an existing subsystem, not a new service:

| Factor | Assessment |
|--------|-----------|
| Scope | Single subsystem (DataFrame building / parallel fetcher) |
| Components | Extends 1 component, adds 2 enum values |
| External Dependencies | Uses existing cache infrastructure |
| Data Model Changes | Two new EntryType values |
| Breaking Changes | None (optional constructor param) |
| Test Complexity | Unit tests sufficient; reuse existing integration patterns |

**Escalation Check:**
- No new service boundaries
- No new external integrations
- No infrastructure changes
- Stays within Module complexity

---

## Implementation Plan

### Phase 1: EntryType Additions

**Goal:** Add new cache entry types per PRD specification.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 1.1 Add `PROJECT_SECTIONS` EntryType | `cache/entry.py` | New enum value | 5 min |
| 1.2 Add `GID_ENUMERATION` EntryType | `cache/entry.py` | New enum value | 5 min |

**Acceptance Criteria:**
- Both entry types exist and can be used
- No breaking changes to existing code

---

### Phase 2: Fetcher Cache Integration

**Goal:** Add cache lookup/populate to `ParallelSectionFetcher`.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 2.1 Add `cache_provider` constructor param | `parallel_fetch.py` | Optional param with None default | 15 min |
| 2.2 Add `_make_cache_key()` helper | `parallel_fetch.py` | Key generation method | 10 min |
| 2.3 Add section cache helpers | `parallel_fetch.py` | `_get_cached_sections`, `_cache_sections` | 30 min |
| 2.4 Add GID enum cache helpers | `parallel_fetch.py` | `_get_cached_gid_enumeration`, `_cache_gid_enumeration` | 30 min |
| 2.5 Integrate caching into `_list_sections()` | `parallel_fetch.py` | Cache lookup before API, populate after | 30 min |
| 2.6 Integrate caching into `fetch_section_task_gids_async()` | `parallel_fetch.py` | Cache lookup before API, populate after | 30 min |
| 2.7 Add structured logging | `parallel_fetch.py` | Log cache hit/miss, timing, API calls saved | 20 min |

**Acceptance Criteria:**
- Cache lookup occurs before API calls
- Cache populated after successful API fetch
- Graceful degradation on cache errors
- Structured logging for observability

---

### Phase 3: Builder Integration

**Goal:** Wire cache provider from builder to fetcher.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 3.1 Pass `cache_provider` to fetcher | `project.py` | Add param to `ParallelSectionFetcher()` constructor | 10 min |

**Acceptance Criteria:**
- Fetcher receives same cache provider as task cache coordinator
- No changes to public API signatures

---

### Phase 4: Testing

**Goal:** Comprehensive test coverage for new behavior.

| Task | File | Changes | Estimate |
|------|------|---------|----------|
| 4.1 Unit tests for section cache | `test_parallel_fetch.py` | `test_section_list_cache_hit`, `test_section_list_cache_miss_populates` | 1h |
| 4.2 Unit tests for GID enum cache | `test_parallel_fetch.py` | `test_gid_enumeration_cache_hit`, `test_gid_enumeration_cache_miss_populates` | 1h |
| 4.3 Unit tests for graceful degradation | `test_parallel_fetch.py` | `test_cache_failure_graceful_degradation`, `test_cache_provider_none_bypasses_cache` | 45 min |
| 4.4 Integration test for warm fetch | `test_gid_cache_warm_fetch.py` | `test_warm_fetch_zero_api_calls`, `test_warm_fetch_under_one_second` | 1.5h |
| 4.5 Test cache key formats | `test_parallel_fetch.py` | `test_cache_key_format_section_list`, `test_cache_key_format_gid_enumeration` | 30 min |

**Acceptance Criteria:**
- >90% coverage on new code
- All FR-DEGRADE requirements validated
- Integration test confirms <1s warm fetch

---

### Dependency Graph

```
Phase 1 (EntryTypes) ─────────────────────┐
                                          │
                                          ▼
Phase 2 (Fetcher Cache) ─────────────────▶ Phase 4 (Testing)
                                          ▲
Phase 3 (Builder Integration) ────────────┘
```

Phase 1 is a prerequisite; Phases 2 and 3 can be done in parallel; Phase 4 depends on all.

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Cache entry size for large projects | Low | Medium | GID list is compact (~20 bytes/GID); 3,530 GIDs = ~70KB |
| Staleness after task moves | Low | Medium | 5-minute TTL limits staleness; task cache has actual data |
| Breaking existing fetcher tests | Medium | Low | Optional param with None default; existing tests unchanged |
| Cache key collision | High | Low | Distinct prefix `project:` and suffix `:sections`/`:gid_enumeration` |
| Constructor param ordering | Low | Low | Use keyword-only for new param |

---

## Observability

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `section_list_cache_hit` | Bool | Whether section list was found in cache |
| `gid_enumeration_cache_hit` | Bool | Whether GID enumeration was found in cache |
| `api_calls_saved` | Counter | API calls avoided by cache hit |
| `section_count` | Gauge | Number of sections in project |
| `gid_count` | Gauge | Total number of task GIDs enumerated |
| `cache_lookup_time_ms` | Histogram | Time to check cache |
| `cache_population_time_ms` | Histogram | Time to populate cache |

### Logging

```python
# Section list cache hit
logger.debug(
    "section_list_cache_hit",
    extra={
        "project_gid": self.project_gid,
        "section_count": len(cached_sections),
        "cache_source": "section_list",
        "api_calls_saved": 1,
    },
)

# GID enumeration cache hit
logger.info(
    "gid_enumeration_cache_hit",
    extra={
        "project_gid": self.project_gid,
        "section_count": len(cached_result),
        "gid_count": sum(len(gids) for gids in cached_result.values()),
        "cache_source": "gid_enumeration",
        "api_calls_saved": len(cached_result) + 1,  # N sections + 1 list call
    },
)

# GID enumeration cache miss (API fetch required)
logger.debug(
    "gid_enumeration_cache_miss",
    extra={
        "project_gid": self.project_gid,
        "reason": "not_found",  # or "expired"
    },
)

# Cache population completed
logger.debug(
    "gid_enumeration_cache_populated",
    extra={
        "project_gid": self.project_gid,
        "section_count": len(section_gids),
        "gid_count": total_gid_count,
        "cache_population_ms": round(populate_time_ms, 2),
    },
)
```

### Alerting

| Alert | Condition | Action |
|-------|-----------|--------|
| Cache lookup overhead | lookup_time_ms > 50ms | Investigate cache provider performance |
| Cache population failure | `cache_population_failed` logged | Check cache provider health |

---

## Testing Strategy

### Unit Tests

| Test Case | File | Validates |
|-----------|------|-----------|
| `test_section_list_cache_hit` | `test_parallel_fetch.py` | FR-SECTION-001, FR-SECTION-002 |
| `test_section_list_cache_miss_populates` | `test_parallel_fetch.py` | FR-SECTION-003 |
| `test_section_list_cache_key_format` | `test_parallel_fetch.py` | FR-SECTION-004 |
| `test_gid_enumeration_cache_hit` | `test_parallel_fetch.py` | FR-GID-001, FR-GID-002 |
| `test_gid_enumeration_cache_miss_populates` | `test_parallel_fetch.py` | FR-GID-003 |
| `test_gid_enumeration_cache_key_format` | `test_parallel_fetch.py` | FR-GID-004 |
| `test_cache_failure_graceful_degradation` | `test_parallel_fetch.py` | FR-DEGRADE-001, FR-DEGRADE-002 |
| `test_cache_provider_none_bypasses_cache` | `test_parallel_fetch.py` | FR-DEGRADE-003 |
| `test_cache_errors_logged_as_warnings` | `test_parallel_fetch.py` | FR-DEGRADE-004 |
| `test_entry_type_project_sections_exists` | `test_entry.py` | FR-CACHE-001 |
| `test_entry_type_gid_enumeration_exists` | `test_entry.py` | FR-CACHE-002 |

### Integration Tests

| Test Case | File | Validates |
|-----------|------|-----------|
| `test_warm_fetch_under_one_second` | `test_gid_cache_warm_fetch.py` | NFR-PERF-001 |
| `test_warm_fetch_zero_api_calls` | `test_gid_cache_warm_fetch.py` | NFR-PERF-002 |
| `test_cold_fetch_no_regression` | `test_gid_cache_warm_fetch.py` | NFR-PERF-003 |
| `test_cache_lookup_overhead` | `test_gid_cache_warm_fetch.py` | NFR-PERF-004 |
| `test_backward_compatibility` | `test_gid_cache_warm_fetch.py` | NFR-COMPAT-001 |

### Performance Validation

```bash
# Run benchmark script
python scripts/demo_parallel_fetch.py --name "Business Offers"

# Expected output (warm fetch):
# First fetch: ~20s (cold)
# Second fetch: <1.0s (warm) - TARGET ACHIEVED
# API calls on warm: 0
# Cache hit: gid_enumeration=True, task_cache=100%
```

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All questions resolved in design |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial draft based on PRD-CACHE-OPTIMIZATION-P3 |

---

## Appendix A: Current vs Target Fetch Flow

### Current State (Problem)

```
First Fetch:
  fetch_section_task_gids_async() [35+ API calls] -> task_cache_lookup() [miss]
    -> fetch_all() [API] -> populate_task_cache() -> build_df()
  Time: ~20s

Second Fetch:
  fetch_section_task_gids_async() [35+ API calls!] -> task_cache_lookup() [HIT]
    -> skip_fetch -> build_df()
  Time: ~9.67s  <-- PROBLEM: 35+ API calls for GID enumeration
```

### Target State (Solution)

```
First Fetch:
  fetch_section_task_gids_async() [35+ API calls] -> populate_gid_cache()
    -> task_cache_lookup() [miss] -> fetch_all() [API] -> populate_task_cache()
    -> build_df()
  Time: ~20s (no regression)

Second Fetch:
  fetch_section_task_gids_async() [0 API calls - CACHE HIT!]
    -> task_cache_lookup() [HIT] -> skip_fetch -> build_df()
  Time: <1.0s  <-- TARGET ACHIEVED
```

---

## Appendix B: Key File Locations

| File | Purpose | Key Lines |
|------|---------|-----------|
| `src/autom8_asana/cache/entry.py` | Entry type definitions | Lines 11-34 (EntryType enum) |
| `src/autom8_asana/dataframes/builders/parallel_fetch.py` | Parallel fetcher | Lines 189-281 (enumeration methods) |
| `src/autom8_asana/dataframes/builders/project.py` | DataFrame builder | Lines 317-329 (fetcher construction) |
| `tests/unit/dataframes/test_parallel_fetch.py` | Fetcher unit tests | Existing |
| `tests/unit/cache/test_entry.py` | Entry type tests | Existing |

---

## Appendix C: Backward Compatibility Checklist

- [x] `ParallelSectionFetcher` constructor accepts new `cache_provider` param as optional
- [x] Default value `None` means no caching (existing behavior preserved)
- [x] No changes to method return types
- [x] No changes to public method signatures
- [x] Existing tests pass without modification
- [x] Graceful degradation when `cache_provider=None`

---

## Appendix D: Implementation Reference

### Section Cache Helper Implementation

```python
def _get_cached_sections(self) -> list[Section] | None:
    """Attempt to retrieve sections from cache."""
    if self.cache_provider is None:
        return None

    try:
        key = self._make_cache_key("sections")
        entry = self.cache_provider.get(key, EntryType.PROJECT_SECTIONS)

        if entry is None:
            logger.debug(
                "section_list_cache_miss",
                extra={"project_gid": self.project_gid, "reason": "not_found"},
            )
            return None

        if entry.is_expired():
            logger.debug(
                "section_list_cache_miss",
                extra={"project_gid": self.project_gid, "reason": "expired"},
            )
            return None

        # Convert cached data back to Section objects
        from autom8_asana.models.section import Section

        sections = [
            Section(gid=s["gid"], name=s["name"])
            for s in entry.data.get("sections", [])
        ]

        logger.debug(
            "section_list_cache_hit",
            extra={
                "project_gid": self.project_gid,
                "section_count": len(sections),
                "api_calls_saved": 1,
            },
        )
        return sections

    except Exception as e:
        # FR-DEGRADE-001: Graceful degradation
        logger.warning(
            "section_list_cache_lookup_failed",
            extra={
                "project_gid": self.project_gid,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        return None


def _cache_sections(self, sections: list[Section]) -> None:
    """Populate cache with section list."""
    if self.cache_provider is None:
        return

    try:
        key = self._make_cache_key("sections")
        entry = CacheEntry(
            key=key,
            data={
                "sections": [
                    {"gid": s.gid, "name": s.name}
                    for s in sections
                ]
            },
            entry_type=EntryType.PROJECT_SECTIONS,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=self._SECTIONS_TTL,
            project_gid=self.project_gid,
            metadata={"section_count": len(sections)},
        )
        self.cache_provider.set(key, entry)

        logger.debug(
            "section_list_cache_populated",
            extra={
                "project_gid": self.project_gid,
                "section_count": len(sections),
            },
        )

    except Exception as e:
        # FR-DEGRADE-002: Cache failure does not prevent operation
        logger.warning(
            "section_list_cache_population_failed",
            extra={
                "project_gid": self.project_gid,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
```

### GID Enumeration Cache Helper Implementation

```python
def _get_cached_gid_enumeration(self) -> dict[str, list[str]] | None:
    """Attempt to retrieve GID enumeration from cache."""
    if self.cache_provider is None:
        return None

    try:
        key = self._make_cache_key("gid_enumeration")
        entry = self.cache_provider.get(key, EntryType.GID_ENUMERATION)

        if entry is None:
            logger.debug(
                "gid_enumeration_cache_miss",
                extra={"project_gid": self.project_gid, "reason": "not_found"},
            )
            return None

        if entry.is_expired():
            logger.debug(
                "gid_enumeration_cache_miss",
                extra={"project_gid": self.project_gid, "reason": "expired"},
            )
            return None

        section_gids = entry.data.get("section_gids", {})
        total_gids = sum(len(gids) for gids in section_gids.values())

        logger.info(
            "gid_enumeration_cache_hit",
            extra={
                "project_gid": self.project_gid,
                "section_count": len(section_gids),
                "gid_count": total_gids,
                "api_calls_saved": len(section_gids) + 1,
            },
        )
        return section_gids

    except Exception as e:
        # FR-DEGRADE-001: Graceful degradation
        logger.warning(
            "gid_enumeration_cache_lookup_failed",
            extra={
                "project_gid": self.project_gid,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        return None


def _cache_gid_enumeration(
    self,
    section_gids: dict[str, list[str]],
) -> None:
    """Populate cache with GID enumeration."""
    if self.cache_provider is None:
        return

    try:
        key = self._make_cache_key("gid_enumeration")
        total_gids = sum(len(gids) for gids in section_gids.values())

        entry = CacheEntry(
            key=key,
            data={"section_gids": section_gids},
            entry_type=EntryType.GID_ENUMERATION,
            version=datetime.now(timezone.utc),
            cached_at=datetime.now(timezone.utc),
            ttl=self._GID_ENUM_TTL,
            project_gid=self.project_gid,
            metadata={
                "section_count": len(section_gids),
                "total_gid_count": total_gids,
            },
        )
        self.cache_provider.set(key, entry)

        logger.debug(
            "gid_enumeration_cache_populated",
            extra={
                "project_gid": self.project_gid,
                "section_count": len(section_gids),
                "gid_count": total_gids,
            },
        )

    except Exception as e:
        # FR-DEGRADE-002: Cache failure does not prevent operation
        logger.warning(
            "gid_enumeration_cache_population_failed",
            extra={
                "project_gid": self.project_gid,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
```
