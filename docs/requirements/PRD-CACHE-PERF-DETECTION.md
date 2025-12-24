# PRD: Detection Result Caching

## Metadata
- **PRD ID**: PRD-CACHE-PERF-DETECTION
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **Stakeholders**: SDK consumers, autom8 platform team
- **Related PRDs**: PRD-CACHE-PERF-FETCH-PATH (P1), PRD-DETECTION
- **Discovery Document**: [DISCOVERY-CACHE-PERF-DETECTION.md](/docs/analysis/DISCOVERY-CACHE-PERF-DETECTION.md)
- **Parent Initiative**: [PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md](/docs/requirements/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md)

---

## Problem Statement

### What Problem Are We Solving?

`detect_entity_type_async()` with `allow_structure_inspection=True` makes a Tier 4 API call (subtask fetch) every time it is invoked for the same task. This adds ~200ms per detection and compounds during hydration operations that traverse multiple hierarchy levels.

### For Whom?

SDK consumers performing hydration operations (`hydrate_from_gid_async()`) and any code paths that require entity type detection with structure inspection enabled.

### Root Cause (from Discovery)

1. **Tier 4 fetches subtasks via API** - `client.tasks.subtasks_async(task.gid).collect()` (~200ms)
2. **DetectionResult is NOT cached** - Each invocation repeats the API call
3. **Hydration calls detection multiple times** - Once per hierarchy level during upward traversal
4. **Same task may be detected repeatedly** - During different operations or retry scenarios

### Impact of Not Solving

- **Performance**: Hydration from deep entities (Offer, Process) takes 1000ms+ due to repeated Tier 4 calls
- **API Usage**: Unnecessary subtask fetches consume rate limits
- **Scalability**: Large extraction operations (1000+ tasks) could take 200+ seconds in worst case
- **User Experience**: Business hierarchy operations are slower than necessary

---

## Goals & Success Metrics

### Primary Goal

Cache `DetectionResult` after Tier 4 execution so that repeat detections for the same task return immediately from cache (<5ms) instead of making API calls (~200ms).

### Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| Repeat Tier 4 detection (same GID) | ~200ms | <5ms | Benchmark script |
| Hydration traversal (5 levels, cached) | ~1000ms | <25ms | Benchmark script |
| First detection (cache miss) | ~200ms | No regression | Benchmark script |
| API calls on repeat detection | 1 per detection | 0 | API call counter |

---

## Scope

### In Scope

- Add `EntryType.DETECTION` to cache entry types
- Cache `DetectionResult` after Tier 4 execution in `detect_entity_type_async()`
- Check cache before executing Tier 4
- Use `task.modified_at` for versioning when available
- Add `EntryType.DETECTION` to SaveSession invalidation
- Graceful degradation when cache is unavailable
- Structured logging for detection cache hits/misses

### Out of Scope

- Caching Tiers 1-3 results (they are O(1), no benefit)
- Caching UNKNOWN (Tier 5) results (should retry)
- Cascade invalidation (not needed - detection is per-task)
- Changes to sync `detect_entity_type()` function
- Changes to detection tier logic or accuracy
- New detection tiers or patterns

---

## Requirements

### Functional Requirements

#### FR-ENTRY: Cache Entry Type

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ENTRY-001 | The system SHALL define `EntryType.DETECTION` in the cache entry type enum. | Must | GIVEN cache/entry.py WHEN inspected THEN `EntryType.DETECTION = "detection"` exists in the enum. |
| FR-ENTRY-002 | `EntryType.DETECTION` SHALL be usable with existing cache provider operations. | Must | GIVEN a CacheProvider instance WHEN `get(gid, EntryType.DETECTION)` is called THEN no error is raised. |
| FR-ENTRY-003 | Detection cache entries SHALL store the full `DetectionResult` dataclass fields. | Must | GIVEN a cached detection entry WHEN deserialized THEN all 5 fields (entity_type, confidence, tier_used, needs_healing, expected_project_gid) are present. |

#### FR-CACHE: Cache Integration

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CACHE-001 | When `allow_structure_inspection=True` and Tier 4 is about to execute, the system SHALL check the detection cache first. | Must | GIVEN a cached detection for task GID WHEN `detect_entity_type_async()` is called with `allow_structure_inspection=True` THEN no subtask API call is made. |
| FR-CACHE-002 | On cache miss, the system SHALL execute Tier 4 and cache the result before returning. | Must | GIVEN no cached detection for task GID WHEN Tier 4 executes and returns a result THEN the result is stored in cache with key `{task_gid}` and `EntryType.DETECTION`. |
| FR-CACHE-003 | Cache check SHALL occur AFTER Tiers 1-3, not at function entry. | Must | GIVEN a task detectable via Tier 1 WHEN `detect_entity_type_async()` is called THEN no cache check occurs (Tier 1 returns immediately). |
| FR-CACHE-004 | Cache lookup and storage SHALL use the task GID as the cache key. | Must | GIVEN task with GID "12345" WHEN detection is cached THEN cache key is "12345" with `EntryType.DETECTION`. |
| FR-CACHE-005 | Only successful Tier 4 results (non-None) SHALL be cached. | Must | GIVEN Tier 4 returns None (no structure match) WHEN caching is attempted THEN no cache entry is created. |
| FR-CACHE-006 | UNKNOWN results (Tier 5 fallback) SHALL NOT be cached. | Must | GIVEN detection falls through to Tier 5 UNKNOWN WHEN result is returned THEN no detection cache entry is created. |

#### FR-VERSION: Versioning Strategy

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-VERSION-001 | Detection cache entries SHALL use `task.modified_at` as the version when available. | Must | GIVEN task with `modified_at: "2025-01-01T00:00:00Z"` WHEN detection is cached THEN `CacheEntry.version` equals that timestamp. |
| FR-VERSION-002 | When `task.modified_at` is None, the system SHALL use current timestamp as version. | Should | GIVEN task with `modified_at: None` WHEN detection is cached THEN `CacheEntry.version` is approximately current time. |
| FR-VERSION-003 | Detection cache entries SHALL use TTL of 300 seconds (matching task cache). | Should | GIVEN a detection cache entry WHEN created THEN TTL is 300 seconds. |
| FR-VERSION-004 | TTL SHALL be configurable via `TTLSettings.entry_type_ttls["detection"]`. | Should | GIVEN `entry_type_ttls={"detection": 600}` WHEN detection is cached THEN TTL is 600 seconds. |

#### FR-INVALIDATE: Cache Invalidation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-INVALIDATE-001 | SaveSession SHALL invalidate `EntryType.DETECTION` alongside `EntryType.TASK` and `EntryType.SUBTASKS` on task mutation. | Must | GIVEN a task is updated via SaveSession WHEN commit completes THEN detection cache for that GID is invalidated. |
| FR-INVALIDATE-002 | Detection cache invalidation SHALL occur for all mutation types (CREATE, UPDATE, DELETE). | Must | GIVEN any CRUD operation on a task WHEN commit succeeds THEN detection cache is invalidated. |
| FR-INVALIDATE-003 | Action operations (add_project, remove_project, set_parent, etc.) SHALL invalidate detection cache. | Should | GIVEN an add_project action on a task WHEN action succeeds THEN detection cache for that GID is invalidated. |
| FR-INVALIDATE-004 | Invalidation failures SHALL NOT prevent commit from succeeding. | Must | GIVEN detection cache invalidation throws exception WHEN commit occurs THEN commit succeeds and warning is logged. |

#### FR-DEGRADE: Graceful Degradation

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DEGRADE-001 | Cache lookup failures SHALL NOT prevent detection from completing. | Must | GIVEN cache provider throws exception on get WHEN detection is called THEN Tier 4 executes normally and result is returned. |
| FR-DEGRADE-002 | Cache storage failures SHALL NOT prevent detection from completing. | Must | GIVEN cache provider throws exception on set WHEN detection completes THEN DetectionResult is returned successfully. |
| FR-DEGRADE-003 | Cache failures SHALL be logged at WARNING level with error details. | Must | GIVEN cache failure occurs WHEN operation completes THEN log contains warning with exception type and message. |
| FR-DEGRADE-004 | When cache provider is None, detection SHALL proceed without cache interaction. | Must | GIVEN `cache_provider=None` in client WHEN detection is called THEN Tier 4 executes and returns result with no cache-related errors. |

#### FR-OBSERVE: Observability

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-OBSERVE-001 | Detection cache hits SHALL be logged with structured fields. | Should | GIVEN cache hit occurs WHEN detection returns THEN log contains `{"event": "detection_cache_hit", "task_gid": "...", "entity_type": "..."}`. |
| FR-OBSERVE-002 | Detection cache misses SHALL be logged with structured fields. | Should | GIVEN cache miss occurs WHEN Tier 4 executes THEN log contains `{"event": "detection_cache_miss", "task_gid": "..."}`. |
| FR-OBSERVE-003 | Detection cache population SHALL be logged with structured fields. | Should | GIVEN detection is cached WHEN storage completes THEN log contains `{"event": "detection_cache_store", "task_gid": "...", "entity_type": "..."}`. |

### Non-Functional Requirements

#### NFR-LATENCY: Performance Targets

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-LATENCY-001 | Cached detection lookup SHALL complete in under 5 milliseconds. | <5ms | Benchmark: `time(cached_detection) < 5ms` |
| NFR-LATENCY-002 | First detection (cache miss) SHALL not regress from current ~200ms baseline. | <=210ms | Benchmark: `time(first_detection) <= 210ms` |
| NFR-LATENCY-003 | Full hydration traversal (5 levels, all cached) SHALL complete in under 50ms. | <50ms | Benchmark: hydration timing |
| NFR-LATENCY-004 | Cache check overhead (when Tier 1-3 succeeds) SHALL be zero. | 0ms | Code review: cache check only before Tier 4 |

#### NFR-COMPAT: Backward Compatibility

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-COMPAT-001 | `detect_entity_type_async()` function signature SHALL remain unchanged. | No changes | Code review: signature unchanged |
| NFR-COMPAT-002 | `detect_entity_type()` sync function SHALL remain unchanged. | No changes | Code review: no modifications |
| NFR-COMPAT-003 | Detection accuracy SHALL not regress from current behavior. | 100% match | Integration test: cached vs fresh detection |
| NFR-COMPAT-004 | Existing tests SHALL continue to pass without modification. | 100% pass | CI: all tests green |

#### NFR-ACCURACY: Detection Correctness

| ID | Requirement | Target | Measurement Method |
|----|-------------|--------|-------------------|
| NFR-ACCURACY-001 | Cached detection result SHALL match result that would be returned by fresh Tier 4 execution. | 100% match | Integration test: compare cached vs uncached |
| NFR-ACCURACY-002 | After task mutation, re-detection SHALL return fresh result (not stale cache). | Correct type | Integration test: mutate then detect |
| NFR-ACCURACY-003 | All DetectionResult fields SHALL be preserved through cache round-trip. | All 5 fields | Unit test: serialize/deserialize equality |

---

## User Stories / Use Cases

### UC-1: Repeat Hydration

**As a** SDK consumer,
**I want** repeat hydrations from the same GID to be fast,
**So that** I can refresh business hierarchy data without long waits.

**Scenario**:
1. First call: `await hydrate_from_gid_async(client, offer_gid)` - detects through 5 levels (~1000ms)
2. Cache warms with detection results for each traversed task
3. Second call: Same hydration - all detections hit cache (<50ms)
4. User sees near-instant hierarchy refresh

### UC-2: Batch Entity Processing

**As a** batch processor,
**I want** repeated detection of the same tasks to be fast,
**So that** processing pipelines can re-detect entities efficiently.

**Scenario**:
1. Pipeline processes 100 tasks, detecting type for each
2. For tasks requiring Tier 4, detection results are cached
3. Pipeline reruns (retry or scheduled)
4. Second run: All Tier 4 detections hit cache (<5ms each)

### UC-3: Dashboard with Multiple Hydrations

**As a** dashboard operator,
**I want** multiple simultaneous hydrations to benefit from shared cache,
**So that** dashboard load time is minimized.

**Scenario**:
1. Dashboard initiates 5 parallel hydrations for different entities
2. First hydration traverses hierarchy, caching detection results
3. Subsequent hydrations hit cache for shared ancestor tasks
4. Overall dashboard load is faster due to shared detection cache

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| `DetectionResult` is serializable via `dataclasses.asdict()` | Frozen dataclass with simple types |
| Task GID is globally unique (cache key won't collide) | Asana assigns unique GIDs |
| Detection result is stable for unchanged tasks | Tier 4 examines subtask names which are stable |
| 300s TTL is sufficient for typical use cases | Matches task cache TTL |
| Cache provider supports single-key get/set operations | Existing `CacheProvider` protocol |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `CacheProvider` protocol with `get`/`set` operations | SDK Team | Available |
| `EntryType` enum extensibility | SDK Team | Available (add new member) |
| SaveSession `_invalidate_cache_for_results()` | SDK Team | Available (add entry type) |
| `detect_entity_type_async()` in facade.py | SDK Team | Available (modify) |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should detection cache use separate TTL from task cache? | Architect | Session 3 | Recommend same (300s) for simplicity |
| Should we add detection metrics to CacheMetrics class? | Architect | Session 3 | Recommend reuse existing pattern |
| How to access cache provider from detection facade? | Architect | Session 3 | Pass client or extract cache_provider from client |

---

## Constraints

### Technical Constraints

1. **Must use existing cache infrastructure** - No new cache backends
2. **Must not slow down Tiers 1-3** - Cache check only before Tier 4
3. **Must be serializable** - DetectionResult through JSON-compatible format
4. **Cache key must be `{task_gid}`** - Consistency with existing patterns

### Business Constraints

1. **No breaking changes** - Existing detection callers must continue working
2. **Default enabled** - Cache should work automatically when cache provider exists
3. **Detection accuracy preserved** - Cached results must be correct

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Stale detection type returned | Medium | Medium | TTL (300s) + explicit invalidation on mutation |
| Cache adds overhead to Tiers 1-3 | Low | High | Cache check ONLY before Tier 4, not at entry |
| Serialization failure for DetectionResult | Low | Low | Use simple `asdict()` conversion; all fields are primitives |
| SaveSession doesn't invalidate detection | Medium | Medium | Add to invalidation list explicitly |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Requirements Analyst | Initial draft based on Discovery findings |

---

## Appendix A: Discovery Summary

### Tier 4 Call Sites

| Location | Function | API Call |
|----------|----------|----------|
| `hydration.py:318-319` | `hydrate_from_gid_async()` | Subtask fetch |
| `hydration.py:702-704` | `_traverse_upward_async()` | Subtask fetch per level |

### Current Flow (No Caching)

```
detect_entity_type_async(task, client, allow_structure_inspection=True)
  --> Tier 1: Project membership (async, no API if registered)
  --> Tier 2-3: Name patterns, parent inference (sync, no API)
  --> Tier 4: fetch subtasks (API call ~200ms) <-- CACHE HERE
  --> Return DetectionResult (not cached)

[Same task detected again]
  --> Same flow, Tier 4 API call repeated (~200ms)
```

### Proposed Flow (With Caching)

```
detect_entity_type_async(task, client, allow_structure_inspection=True)
  --> Tier 1-3: (unchanged)
  --> Check detection cache for task_gid
      --> HIT: Return cached DetectionResult (<5ms)
      --> MISS: Execute Tier 4, cache result, return
```

---

## Appendix B: DetectionResult Structure

```python
@dataclass(frozen=True, slots=True)
class DetectionResult:
    entity_type: EntityType      # Enum value (e.g., "business", "unit")
    confidence: float            # 0.0 - 1.0
    tier_used: int               # 1-5
    needs_healing: bool          # True if entity needs project membership repair
    expected_project_gid: str | None  # GID for healing
```

### Serialization Format

```json
{
  "entity_type": "business",
  "confidence": 0.9,
  "tier_used": 4,
  "needs_healing": true,
  "expected_project_gid": "1234567890"
}
```

---

## Appendix C: Acceptance Criteria Verification Matrix

| Requirement | Test Type | Automation |
|-------------|-----------|------------|
| FR-ENTRY-001 | Unit | Assert enum member exists |
| FR-CACHE-001 | Integration | Mock cache with entry, assert no API call |
| FR-CACHE-002 | Integration | Cold cache, assert cache populated after Tier 4 |
| FR-CACHE-003 | Unit | Tier 1 detectable task, assert no cache interaction |
| FR-VERSION-001 | Unit | Assert CacheEntry.version matches task.modified_at |
| FR-INVALIDATE-001 | Integration | SaveSession commit, assert detection invalidated |
| FR-DEGRADE-001 | Unit | Cache raises, assert detection still returns |
| NFR-LATENCY-001 | Benchmark | Timed detection with warm cache |
| NFR-ACCURACY-001 | Integration | Compare cached vs fresh detection |
