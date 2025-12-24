# PRD-CACHE-PERF-STORIES: Stories Client Incremental Cache Integration

| Field | Value |
|-------|-------|
| **Document ID** | PRD-CACHE-PERF-STORIES |
| **Title** | Stories Client Incremental Cache Integration |
| **Status** | Draft |
| **Created** | 2025-12-23 |
| **Last Updated** | 2025-12-23 |
| **Author** | Requirements Analyst (AI-assisted) |
| **Initiative** | PROMPT-0-CACHE-PERF-STORIES |
| **Discovery** | [stories-cache-wiring-discovery.md](../analysis/stories-cache-wiring-discovery.md) |
| **Related PRDs** | PRD-WATERMARK-CACHE, PRD-CACHE-INTEGRATION |

---

## 1. Problem Statement

### Current State

The `StoriesClient.list_for_task_async()` method fetches stories directly from the Asana API without cache integration. Each call results in a full fetch of all stories for a task, regardless of whether stories were recently fetched.

### Problems

1. **No Cache Utilization**: Stories are fetched fresh every time, ignoring existing cache infrastructure
2. **Unused Incremental Infrastructure**: `load_stories_incremental()` in `cache/stories.py` is fully implemented but not wired to any client
3. **Wasted API Bandwidth**: Asana's `since` parameter (for incremental fetching) is not utilized
4. **Performance Opportunity Missed**: Repeat story fetches take ~500ms when they could take <100ms with incremental caching

### Desired Outcome

Wire `StoriesClient` to use the existing `load_stories_incremental()` infrastructure, enabling:
- Incremental fetching via Asana's `since` parameter
- Story caching with merge/deduplication
- >90% cache hit rate on repeat fetches
- <100ms latency for incremental fetches

---

## 2. Scope

### In Scope

| Item | Description |
|------|-------------|
| New client method | `list_for_task_cached_async()` with cache integration |
| Sync wrapper | `list_for_task_cached()` following existing pattern |
| Fetcher adapter | Internal method to create loader-compatible fetcher |
| Cache integration | Wire to `load_stories_incremental()` |
| Graceful degradation | Fallback to full fetch when cache unavailable |
| Observability | Structured logging for cache hit/miss |

### Out of Scope

| Item | Rationale |
|------|-----------|
| Modifying `list_for_task_async()` | Preserve backward compatibility (Discovery Q1) |
| Story filtering in client | Caller responsibility per separation of concerns (Discovery Q5) |
| Struc computation integration | Separate initiative |
| Custom TTL configuration | Use defaults initially; can add later |
| Rich return type with metadata | Simple `list[Story]` first; can enhance later (Discovery Q4) |

---

## 3. Functional Requirements

### FR-CLIENT: Client Method Integration

#### FR-CLIENT-001: New Async Method [Must]

**Requirement:** StoriesClient SHALL provide a new `list_for_task_cached_async()` method for cache-aware story fetching.

**Signature:**
```python
async def list_for_task_cached_async(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
```

**Acceptance Criteria:**
- [ ] Method exists on `StoriesClient` class
- [ ] Returns `list[Story]` (not `PageIterator`)
- [ ] Accepts required `task_gid` parameter
- [ ] Accepts optional `task_modified_at` parameter for cache versioning
- [ ] Accepts optional `opt_fields` parameter for field selection
- [ ] Method is async (uses `await`)

**Traces to:** Discovery Q1 (Option B - New Method)

---

#### FR-CLIENT-002: Sync Wrapper [Must]

**Requirement:** StoriesClient SHALL provide a synchronous `list_for_task_cached()` wrapper method.

**Signature:**
```python
def list_for_task_cached(
    self,
    task_gid: str,
    *,
    task_modified_at: str | None = None,
    opt_fields: list[str] | None = None,
) -> list[Story]:
```

**Acceptance Criteria:**
- [ ] Sync method exists on `StoriesClient` class
- [ ] Uses `@sync_wrapper` decorator pattern (per existing convention)
- [ ] Returns same type as async version (`list[Story]`)
- [ ] Parameters match async version exactly

**Traces to:** Discovery Open Question 1 (Sync wrapper recommendation)

---

#### FR-CLIENT-003: opt_fields Support [Must]

**Requirement:** The new method SHALL support the `opt_fields` parameter for specifying which story fields to return.

**Acceptance Criteria:**
- [ ] `opt_fields` parameter is passed to Asana API request
- [ ] When `opt_fields` is None, default fields are returned
- [ ] When `opt_fields` is provided, only specified fields are returned
- [ ] Field format follows Asana API conventions (comma-separated in request)

**Traces to:** Existing `list_for_task_async()` pattern

---

#### FR-CLIENT-004: BaseClient Cache Integration [Must]

**Requirement:** The new method SHALL use `self._cache` from `BaseClient` for cache operations.

**Acceptance Criteria:**
- [ ] Uses `self._cache` attribute inherited from `BaseClient`
- [ ] Does not create new cache provider instance
- [ ] Respects cache provider configuration from client initialization

**Traces to:** Discovery Current State Analysis (BaseClient with `self._cache` available)

---

#### FR-CLIENT-005: Preserve Existing Method [Must]

**Requirement:** Existing `list_for_task_async()` SHALL remain unchanged (backward compatibility).

**Acceptance Criteria:**
- [ ] Method signature unchanged
- [ ] Return type remains `PageIterator[Story]`
- [ ] Behavior unchanged (no cache, lazy pagination)
- [ ] All existing tests pass without modification

**Traces to:** Discovery Q1 (Option B - New Method preserves existing)

---

### FR-FETCH: Fetcher Adapter

#### FR-FETCH-001: Loader-Compatible Fetcher [Must]

**Requirement:** StoriesClient SHALL create an internal fetcher function compatible with `load_stories_incremental()` signature.

**Required Signature:**
```python
Callable[[str, str | None], Awaitable[list[dict[str, Any]]]]
# (task_gid, since_timestamp) -> list of story dicts
```

**Acceptance Criteria:**
- [ ] Fetcher accepts `task_gid` as first parameter
- [ ] Fetcher accepts `since` (ISO timestamp or None) as second parameter
- [ ] Fetcher returns `list[dict[str, Any]]` (raw dicts, not Story models)
- [ ] Fetcher is async (returns Awaitable)

**Traces to:** Discovery Q2 (Fetcher Adapter Design)

---

#### FR-FETCH-002: Since Parameter Support [Must]

**Requirement:** The fetcher SHALL pass the `since` parameter to the Asana API when provided.

**Acceptance Criteria:**
- [ ] When `since` is None, no `since` parameter in API request
- [ ] When `since` is provided, `since={value}` included in API request
- [ ] `since` value is ISO 8601 timestamp format
- [ ] API returns only stories created/modified after `since` timestamp

**Traces to:** Discovery Q2 (since parameter: Passes to Asana API when provided)

---

#### FR-FETCH-003: Eager Pagination [Must]

**Requirement:** The fetcher SHALL collect all pages of stories before returning (eager evaluation).

**Acceptance Criteria:**
- [ ] Fetcher loops through all pagination offsets
- [ ] All stories across all pages are collected into single list
- [ ] Fetcher does not return until all pages are fetched
- [ ] Works correctly for tasks with 0, 1, or multiple pages of stories

**Traces to:** Discovery Q2 (Eager fetching: Collects all pages before returning)

---

#### FR-FETCH-004: Raw Dict Response [Must]

**Requirement:** The fetcher SHALL return raw API response dicts, not Story model instances.

**Acceptance Criteria:**
- [ ] Returns `list[dict[str, Any]]` type
- [ ] Does not call `Story.model_validate()` on results
- [ ] Preserves all fields from API response
- [ ] Model validation happens after cache merge, not during fetch

**Traces to:** Discovery Q2 (Raw dicts: Returns dict, not Story models)

---

#### FR-FETCH-005: Since Parameter Omission [Must]

**Requirement:** The fetcher SHALL NOT pass `since` parameter when None (full fetch).

**Acceptance Criteria:**
- [ ] HTTP request omits `since` parameter when `since` argument is None
- [ ] Results in full fetch of all stories
- [ ] No empty string or null value sent to API

**Traces to:** Discovery Q2 (Fetcher behavior on first fetch)

---

#### FR-FETCH-006: opt_fields Propagation [Must]

**Requirement:** The fetcher SHALL use same `opt_fields` configuration as caller specified.

**Acceptance Criteria:**
- [ ] Custom `opt_fields` from caller reflected in HTTP request params
- [ ] Fetcher does not override or drop caller's field selections
- [ ] Default behavior when `opt_fields=None` matches existing pattern

**Traces to:** Discovery (Fetcher respects existing `_build_opt_fields()` pattern)

---

### FR-CACHE: Cache Integration

#### FR-CACHE-001: Use Incremental Loader [Must]

**Requirement:** The new method SHALL use `load_stories_incremental()` from `cache/stories.py`.

**Acceptance Criteria:**
- [ ] Imports `load_stories_incremental` from `autom8_asana.cache.stories`
- [ ] Calls `load_stories_incremental()` with required parameters
- [ ] Handles return tuple: `(stories, cache_entry, was_incremental_fetch)`
- [ ] Converts returned dicts to Story models before returning

**Traces to:** Discovery Integration Strategy (Use existing loader)

---

#### FR-CACHE-002: EntryType.STORIES Usage [Must]

**Requirement:** Cache operations SHALL use `EntryType.STORIES` for story cache entries.

**Acceptance Criteria:**
- [ ] Story cache entries use `EntryType.STORIES` enum value
- [ ] Cache keys are task GIDs
- [ ] Entry type is consistent with existing loader implementation

**Traces to:** Discovery (EntryType.STORIES already defined)

---

#### FR-CACHE-003: Last Fetched Metadata [Must]

**Requirement:** Cache entries SHALL include `last_fetched` timestamp in metadata.

**Acceptance Criteria:**
- [ ] Cache entry metadata contains `last_fetched` key
- [ ] `last_fetched` value is ISO 8601 timestamp
- [ ] Timestamp represents when stories were last fetched from API
- [ ] Used as `since` parameter for subsequent incremental fetches

**Traces to:** Discovery (Cache entry with `last_fetched` metadata - handled by existing loader)

---

#### FR-CACHE-004: Task GID as Cache Key [Must]

**Requirement:** Cache key SHALL be `task_gid` (stories are per-task, not per-project).

**Acceptance Criteria:**
- [ ] Cache lookup uses `task_gid` as key
- [ ] Key format is plain task GID (not composite with project)
- [ ] Consistent with existing `load_stories_incremental()` key usage

**Traces to:** Discovery (Stories are per-task entity; cache/stories.py uses task_gid as key)

---

#### FR-CACHE-005: Task Modified At Versioning [Should]

**Requirement:** The method SHOULD accept `task_modified_at` for cache versioning.

**Acceptance Criteria:**
- [ ] `task_modified_at` parameter passed to `load_stories_incremental()` as `current_modified_at`
- [ ] When provided, used for cache entry versioning
- [ ] When None, loader uses current time for version
- [ ] Does not require extra API call to fetch task

**Traces to:** Discovery Q3 (Option A - Accept as Optional Parameter)

---

### FR-MERGE: Story Merging

*Note: These requirements are satisfied by the existing `load_stories_incremental()` implementation. Listed for traceability.*

#### FR-MERGE-001: Deduplicate by GID [Must]

**Requirement:** Story merging SHALL deduplicate stories by GID.

**Acceptance Criteria:**
- [ ] No duplicate story GIDs in merged result
- [ ] Existing `_merge_stories()` function handles deduplication
- [ ] Test coverage exists in `test_stories.py`

**Traces to:** Discovery (Story merging with deduplication by GID)

---

#### FR-MERGE-002: New Stories Precedence [Must]

**Requirement:** When merging, new stories SHALL take precedence over cached stories with same GID.

**Acceptance Criteria:**
- [ ] If story GID exists in both cached and new, new version is kept
- [ ] Handles story updates correctly
- [ ] Test coverage exists in `test_stories.py`

**Traces to:** Discovery (`_merge_stories()` - New stories take precedence)

---

#### FR-MERGE-003: Sort by Created At [Must]

**Requirement:** Merged stories SHALL be sorted by `created_at` timestamp ascending.

**Acceptance Criteria:**
- [ ] Result list is sorted by `created_at` field
- [ ] Oldest stories first, newest last
- [ ] Stories without `created_at` handled gracefully
- [ ] Test coverage exists in `test_stories.py`

**Traces to:** Discovery (`_merge_stories()` - sorts by created_at)

---

### FR-DEGRADE: Graceful Degradation

#### FR-DEGRADE-001: Fallback Without Cache [Must]

**Requirement:** When cache provider is unavailable, the method SHALL fallback to full fetch.

**Acceptance Criteria:**
- [ ] When `self._cache` is None, performs full fetch
- [ ] Full fetch returns all stories (no `since` parameter)
- [ ] Returns valid `list[Story]` even without cache
- [ ] No exception raised due to missing cache

**Traces to:** Discovery Risk (Cache provider unavailable - Graceful degradation)

---

#### FR-DEGRADE-002: Log Cache Failures [Must]

**Requirement:** Cache operation failures SHALL be logged but not raised.

**Acceptance Criteria:**
- [ ] Cache read failures logged at WARNING level
- [ ] Cache write failures logged at WARNING level
- [ ] Method continues execution after cache failure
- [ ] Log includes error details for debugging

**Traces to:** Discovery Risk Mitigation (Log cache failures, don't raise)

---

#### FR-DEGRADE-003: Valid Response on Failure [Must]

**Requirement:** The method SHALL return a valid `list[Story]` even when cache operations fail.

**Acceptance Criteria:**
- [ ] Cache failure does not prevent story fetch
- [ ] Returns stories from direct API fetch on cache failure
- [ ] Return type is always `list[Story]`
- [ ] Caller cannot distinguish cache failure from cache miss

**Traces to:** Discovery FR-DEGRADE (Return valid list[Story] even on cache failure)

---

## 4. Non-Functional Requirements

### NFR-PERF: Performance

#### NFR-PERF-001: First Fetch Latency [Must]

**Requirement:** First fetch latency SHALL remain unchanged (~500ms baseline).

**Target:** ~500ms (same as current `list_for_task_async()`)

**Acceptance Criteria:**
- [ ] First fetch (cache miss) takes approximately same time as current implementation
- [ ] No significant overhead from cache integration on first fetch
- [ ] Measured under normal network conditions

**Traces to:** PROMPT-0 Performance Targets

---

#### NFR-PERF-002: Incremental Fetch Latency [Must]

**Requirement:** Incremental fetch latency SHALL be less than 100ms.

**Target:** <100ms

**Acceptance Criteria:**
- [ ] Second fetch (cache hit, incremental) completes in <100ms
- [ ] Latency reduction due to fewer stories returned by API
- [ ] Measured with typical task (10-50 stories, 0-5 new since last fetch)

**Traces to:** PROMPT-0 Performance Targets

---

#### NFR-PERF-003: Merge Operation Latency [Must]

**Requirement:** Story merge operation SHALL complete in less than 10ms.

**Target:** <10ms

**Acceptance Criteria:**
- [ ] `_merge_stories()` completes in <10ms for typical story counts
- [ ] Tested with up to 500 stories
- [ ] CPU-bound operation, no I/O

**Traces to:** PROMPT-0 Performance Targets

---

#### NFR-PERF-004: Cache Hit Rate [Should]

**Requirement:** Cache hit rate SHOULD exceed 90% for repeat fetches.

**Target:** >90%

**Acceptance Criteria:**
- [ ] After initial fetch, subsequent fetches use incremental path
- [ ] Cache entries not prematurely evicted (default TTL appropriate)
- [ ] Measured across typical usage patterns

**Traces to:** PROMPT-0 Success Criteria

---

#### NFR-PERF-005: Model Validation Latency [Should]

**Requirement:** Story model validation SHOULD complete in less than 50ms for typical story counts.

**Target:** <50ms for 100 Story objects

**Acceptance Criteria:**
- [ ] `Story.model_validate()` across 100 items completes in <50ms
- [ ] No blocking I/O during validation
- [ ] Measured with representative story data

**Traces to:** Performance budget for model conversion step

---

### NFR-COMPAT: Compatibility

#### NFR-COMPAT-001: No Breaking Changes [Must]

**Requirement:** Implementation SHALL NOT introduce breaking changes to existing API.

**Acceptance Criteria:**
- [ ] `list_for_task_async()` signature unchanged
- [ ] `list_for_task_async()` behavior unchanged
- [ ] No changes to `Story` model
- [ ] No changes to `PageIterator` behavior

**Traces to:** Discovery Q1 (No breaking changes to existing consumers)

---

#### NFR-COMPAT-002: Preserve PageIterator [Must]

**Requirement:** Existing `list_for_task_async()` SHALL continue to return `PageIterator[Story]`.

**Acceptance Criteria:**
- [ ] `list_for_task_async()` return type is `PageIterator[Story]`
- [ ] Lazy pagination behavior preserved
- [ ] Existing tests continue to pass

**Traces to:** Discovery Q1 (Preserves list_for_task_async() for PageIterator consumers)

---

#### NFR-COMPAT-003: Python Version Compatibility [Must]

**Requirement:** Implementation SHALL support Python 3.10+.

**Target:** Full support for Python 3.10, 3.11, 3.12

**Acceptance Criteria:**
- [ ] CI matrix passes for all supported Python versions
- [ ] No Python 3.10+ incompatible syntax or imports
- [ ] Type hints use compatible union syntax (`X | Y` or `Union[X, Y]`)

**Traces to:** SDK compatibility requirements

---

#### NFR-COMPAT-004: Type Safety [Must]

**Requirement:** Type hints SHALL pass mypy strict mode.

**Target:** Zero mypy errors

**Acceptance Criteria:**
- [ ] `mypy --strict` passes for new code
- [ ] All parameters and return types annotated
- [ ] No `# type: ignore` comments without justification

**Traces to:** SDK type safety standards

---

### NFR-OBS: Observability

#### NFR-OBS-001: Log Fetch Type [Should]

**Requirement:** The method SHOULD log whether fetch was incremental or full.

**Acceptance Criteria:**
- [ ] Log entry indicates `was_incremental_fetch` boolean
- [ ] Log level is DEBUG
- [ ] Structured logging format used

**Traces to:** Discovery Q4 (Log was_incremental_fetch for observability)

---

#### NFR-OBS-002: Log Cache Hit/Miss [Should]

**Requirement:** The method SHOULD log cache hit/miss status.

**Acceptance Criteria:**
- [ ] Cache hit logged at DEBUG level
- [ ] Cache miss logged at DEBUG level
- [ ] Includes task_gid for correlation

**Traces to:** Discovery (Observability via logging)

---

#### NFR-OBS-003: Structured Logging [Should]

**Requirement:** Log entries SHOULD use structured logging format.

**Acceptance Criteria:**
- [ ] Uses `extra={}` dict for structured fields
- [ ] Consistent with existing SDK logging patterns
- [ ] Machine-parseable format

**Traces to:** SDK logging conventions

---

## 5. Dependencies

### Existing Infrastructure (No Changes Required)

| Component | Location | Status |
|-----------|----------|--------|
| `load_stories_incremental()` | `cache/stories.py` | Implemented, tested |
| `EntryType.STORIES` | `cache/entry.py` | Defined |
| `_merge_stories()` | `cache/stories.py` | Implemented, tested |
| `_create_stories_entry()` | `cache/stories.py` | Implemented |
| `BaseClient._cache` | `clients/base.py` | Available |
| `Story` model | `models/story.py` | Defined |
| `@sync_wrapper` | `transport/sync.py` | Available |

### Test Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| Loader unit tests | `tests/unit/cache/test_stories.py` | 17 tests passing |
| StoriesClient tests | `tests/unit/test_coverage_gap.py` | Existing coverage |

---

## 6. Risks

| ID | Risk | Impact | Likelihood | Mitigation |
|----|------|--------|------------|------------|
| R1 | Eager fetch memory pressure | High memory for tasks with many stories | Low | Most tasks have <100 stories; monitor memory usage |
| R2 | Cache provider unavailable | Degraded performance | Medium | FR-DEGRADE-001: Fallback to full fetch |
| R3 | Merge correctness edge cases | Data corruption | Low | Existing test coverage; add integration tests |
| R4 | Asana `since` parameter behavior | Unexpected API behavior | Low | Well-documented in Asana API; verified in existing tests |
| R5 | Performance regression on first fetch | Slower than current | Very Low | First fetch uses same code path |
| R6 | Story model validation failures | Runtime errors | Low | Story model uses `extra="ignore"` |

---

## 7. Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Incremental fetch rate | >90% after warmup | Logging/metrics |
| Second fetch latency | <100ms | Performance testing |
| Cache hit rate | >90% for repeat fetches | Cache metrics |
| Regression rate | 0 failures in existing tests | CI/CD |
| API call reduction | >50% on repeat fetches | API call logging |

---

## 8. Acceptance Test Scenarios

### Scenario 1: First Fetch (Cache Miss)

```gherkin
Given a task with 50 stories
And the cache is empty for this task
When I call list_for_task_cached_async(task_gid)
Then all 50 stories are returned
And the cache is populated with 50 stories
And last_fetched metadata is set
```

### Scenario 2: Second Fetch (Incremental)

```gherkin
Given a task with 50 stories cached
And 2 new stories created since last fetch
When I call list_for_task_cached_async(task_gid)
Then 52 stories are returned (50 cached + 2 new)
And the API was called with since={last_fetched}
And the cache is updated with 52 stories
```

### Scenario 3: No Cache Provider

```gherkin
Given StoriesClient initialized without cache provider
When I call list_for_task_cached_async(task_gid)
Then all stories are fetched directly from API
And no exception is raised
And list[Story] is returned
```

### Scenario 4: Cache Failure During Read

```gherkin
Given cache provider raises exception on read
When I call list_for_task_cached_async(task_gid)
Then warning is logged
And full fetch is performed
And list[Story] is returned
```

### Scenario 5: Duplicate Story GIDs

```gherkin
Given cached stories include story with GID "s1"
And incremental fetch returns updated story with GID "s1"
When stories are merged
Then only one story with GID "s1" exists
And it contains the updated content
```

---

## 9. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-12-23 | Requirements Analyst | Initial draft |
| 0.2 | 2025-12-23 | Requirements Analyst | Added FR-CLIENT-005, FR-FETCH-005/006, FR-CACHE-004, NFR-PERF-005, NFR-COMPAT-003/004; Enhanced requirement IDs for traceability |

---

## 10. Approvals

| Role | Name | Date | Status |
|------|------|------|--------|
| Product Owner | | | Pending |
| Tech Lead | | | Pending |
| Architect | | | Pending |

---

*Next: Session 3 - Architecture Design (TDD-CACHE-PERF-STORIES)*

---

## Appendix A: Requirements Summary Table

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CLIENT-001 | New `list_for_task_cached_async()` method | Must |
| FR-CLIENT-002 | Sync wrapper `list_for_task_cached()` | Must |
| FR-CLIENT-003 | opt_fields parameter support | Must |
| FR-CLIENT-004 | Use BaseClient `self._cache` | Must |
| FR-CLIENT-005 | Preserve existing `list_for_task_async()` | Must |
| FR-FETCH-001 | Loader-compatible fetcher signature | Must |
| FR-FETCH-002 | Since parameter support | Must |
| FR-FETCH-003 | Eager pagination (all pages) | Must |
| FR-FETCH-004 | Raw dict response (not models) | Must |
| FR-FETCH-005 | Omit since when None | Must |
| FR-FETCH-006 | Propagate opt_fields to fetcher | Must |
| FR-CACHE-001 | Use `load_stories_incremental()` | Must |
| FR-CACHE-002 | Use `EntryType.STORIES` | Must |
| FR-CACHE-003 | Include `last_fetched` metadata | Must |
| FR-CACHE-004 | Use task_gid as cache key | Must |
| FR-CACHE-005 | Accept `task_modified_at` for versioning | Should |
| FR-MERGE-001 | Deduplicate by GID | Must |
| FR-MERGE-002 | New stories take precedence | Must |
| FR-MERGE-003 | Sort by created_at ascending | Must |
| FR-DEGRADE-001 | Fallback without cache | Must |
| FR-DEGRADE-002 | Log cache failures | Must |
| FR-DEGRADE-003 | Valid response on failure | Must |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-PERF-001 | First fetch latency | ~500ms (unchanged) |
| NFR-PERF-002 | Incremental fetch latency | <100ms |
| NFR-PERF-003 | Merge operation latency | <10ms |
| NFR-PERF-004 | Cache hit rate | >90% |
| NFR-PERF-005 | Model validation latency | <50ms (100 objects) |
| NFR-COMPAT-001 | No breaking changes | 100% compatible |
| NFR-COMPAT-002 | Preserve PageIterator return | Unchanged |
| NFR-COMPAT-003 | Python version support | 3.10, 3.11, 3.12 |
| NFR-COMPAT-004 | Type safety | mypy --strict passes |
| NFR-OBS-001 | Log fetch type | DEBUG level |
| NFR-OBS-002 | Log cache hit/miss | DEBUG level |
| NFR-OBS-003 | Structured logging | extra={} format |

---

## Appendix B: Quality Gate Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] Dependencies identified with owners
- [x] Risks documented with mitigations
- [x] No blocking open questions
