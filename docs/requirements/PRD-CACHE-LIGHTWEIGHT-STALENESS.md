# PRD: Lightweight Staleness Detection with Progressive TTL Extension

## Metadata

- **PRD ID**: PRD-CACHE-LIGHTWEIGHT-STALENESS
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **Stakeholders**: SDK Team, DataFrame Consumers, API Quota Managers
- **Related PRDs**:
  - [PRD-CACHE-OPTIMIZATION-P3](/docs/requirements/PRD-CACHE-OPTIMIZATION-P3.md) - Phase 3 (GID enumeration caching)
  - [PRD-CACHE-OPTIMIZATION-P2](/docs/requirements/PRD-CACHE-OPTIMIZATION-P2.md) - Phase 2 (Task cache population)
- **Related Documents**:
  - [DISCOVERY-CACHE-LIGHTWEIGHT-STALENESS](/docs/analysis/DISCOVERY-CACHE-LIGHTWEIGHT-STALENESS.md) - Discovery findings
  - [PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS](/docs/requirements/PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS.md) - Initiative specification
  - [ADR-0019](/docs/decisions/ADR-0019-staleness-detection-algorithm.md) - Staleness detection algorithm

---

## Problem Statement

### The Problem

The autom8_asana SDK cache performs **full API fetches** when TTL expires, even when cached data is unchanged. For stable entities (tasks that haven't been modified), this wastes API quota and adds unnecessary latency. The existing staleness detection infrastructure (`check_entry_staleness()`, `CacheEntry.is_stale()`, `Freshness.STRICT` mode) is fully implemented but **not integrated** into the cache lookup flow.

### Current vs. Target Behavior

| Scenario | Current Behavior | Target Behavior |
|----------|------------------|-----------------|
| TTL expired, data unchanged | Full API fetch (~5KB, ~200ms) | Lightweight check (~100 bytes, <100ms), extend TTL |
| TTL expired, data changed | Full API fetch | Full API fetch (correct behavior) |
| Repeated access to stable entity | Full fetch every 5 min | Progressive TTL: 5min -> 10min -> ... -> 24h |

### Who Experiences This

All SDK consumers using cached operations, particularly:
- Long-running sessions accessing stable entities repeatedly
- Dashboard/reporting applications with periodic refresh
- Batch processing pipelines with entity-level caching
- Any consumer using `Freshness.STRICT` mode (or wanting to)

### Impact of Not Solving

- **Wasted API quota**: Full payload fetched for unchanged entities
- **Unnecessary latency**: ~200ms per entity instead of <100ms for lightweight check
- **No TTL progression**: Stable entities never extend TTL, always re-checked at base interval
- **Unused infrastructure**: Staleness detection machinery defined but not activated
- **Scaling limitation**: Cannot efficiently handle long-running sessions with stable entity sets

---

## Goals and Success Metrics

### Primary Goal

Achieve 90%+ API call reduction for stable entities by replacing full API fetches with lightweight `modified_at` checks and progressively extending TTL for unchanged entities.

### Success Metrics

| Metric | Current | Target | Measurement Method |
|--------|---------|--------|-------------------|
| API calls for stable entities (after 2h) | 24 (every 5 min) | 2-3 (progressive TTL) | Structured logging count |
| Latency for unchanged entity check | ~200ms (full fetch) | <100ms (lightweight check) | `time.perf_counter()` |
| TTL for stable entity after 2h | 300s (constant) | 3600s+ (progressive) | `CacheEntry.metadata.extension_count` |
| Bandwidth per staleness check | ~5KB (full payload) | ~100 bytes (modified_at only) | Response size logging |
| Batch efficiency | N/A | >10 entities per API call | `batch_size` metric |
| Changed entity detection | N/A | 100% accuracy | No stale reads in validation |

### Secondary Goals

- Maintain backward compatibility (no breaking API changes)
- Follow established patterns from P2/P3 (graceful degradation, structured logging)
- Enable future extension to other entity types (Projects, etc.)
- Integrate with existing `Freshness.STRICT` mode semantics

---

## Scope

### In Scope

| Area | Description |
|------|-------------|
| Batch request coalescing | Collect expired cache entries within 50ms window for batch checking |
| Lightweight API checks | Use `/batch` endpoint with `opt_fields=modified_at` only |
| Progressive TTL extension | Double TTL on unchanged (300s -> 600s -> ... -> 86400s max) |
| TTL reset on change | Return to base TTL when entity modification detected |
| Extension metadata storage | Track `extension_count` in `CacheEntry.metadata` |
| Graceful degradation | Fall back to full fetch on check failure |
| Observability | Structured logging for staleness check operations |
| Test coverage | Unit and integration tests for new behavior |

### Out of Scope

| Area | Rationale |
|------|-----------|
| Entity types other than TASK | Scope limited per PROMPT-0; Projects deferred to future phase |
| Nested attribute staleness | Subtasks, dependencies follow own TTL; not checked via parent |
| S3 tier staleness checks | Redis-only for this phase; S3 is cold tier |
| Configuration UI | Code/env config only; no UI changes |
| GID enumeration changes | Phase 3 complete and separate (ADR-0131) |
| Webhooks integration | Staleness checks are pull-based, not push-based |
| Per-entity-type TTL ceilings | Single 24h ceiling for Tasks; per-type deferred |

---

## Requirements

### Functional Requirements - Batch Coalescing (FR-BATCH-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-BATCH-001 | Collect expired cache entries within 50ms coalescing window before triggering batch API call | Must | Concurrent expired entries within 50ms appear in same batch; log shows `coalesce_window_ms: 50` |
| FR-BATCH-002 | Support maximum batch size of 100 entries per coalescing window | Must | Batches exceeding 100 entries are split; log shows `batch_count` when >1 |
| FR-BATCH-003 | Split batches exceeding Asana's 10-action limit into sequential chunks | Must | Batch of 25 entries becomes 3 API calls (10+10+5); log shows `chunk_count: 3` |
| FR-BATCH-004 | Handle concurrent callers waiting for same batch result | Must | Multiple callers for same GID receive same result; no duplicate API calls |
| FR-BATCH-005 | Flush batch immediately when max batch size (100) reached, without waiting for window | Must | Large burst of 100+ entries does not wait 50ms; immediate flush occurs |
| FR-BATCH-006 | Deduplicate GIDs within same batch (same entry requested multiple times) | Should | Batch with duplicate GIDs makes single API call per unique GID |

### Functional Requirements - Staleness Check Logic (FR-STALE-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-STALE-001 | Trigger lightweight staleness check when cached entry TTL expires | Must | Expired entry queued for batch check instead of immediate cache miss |
| FR-STALE-002 | Use Asana batch API with `opt_fields=modified_at` for lightweight checks | Must | API request contains only `opt_fields=modified_at`; response ~100 bytes per entity |
| FR-STALE-003 | Compare API `modified_at` against cached `CacheEntry.version` to determine staleness | Must | Entry with matching version returns cached data; entry with newer version triggers full fetch |
| FR-STALE-004 | Return cached data immediately for entries where `modified_at` matches cached version | Must | Unchanged entities return from cache after lightweight check; no full fetch |
| FR-STALE-005 | Signal caller to perform full fetch when `modified_at` indicates change | Must | Changed entities trigger full API fetch; cache updated with fresh data |
| FR-STALE-006 | Treat missing entity in API response as deleted; invalidate cache entry | Must | API returns 404 or omits GID; cache entry removed; caller receives None |
| FR-STALE-007 | Integrate with existing `Freshness.STRICT` mode semantics | Should | `Freshness.STRICT` triggers version validation (existing behavior preserved) |

### Functional Requirements - Progressive TTL Extension (FR-TTL-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-TTL-001 | Double TTL on each unchanged staleness check (base 300s -> 600s -> 1200s -> ...) | Must | Entry checked and unchanged doubles its TTL; log shows `new_ttl: 600` after first extension |
| FR-TTL-002 | Enforce maximum TTL ceiling of 86400 seconds (24 hours) | Must | Entry at 76800s TTL extends to 86400s, not 153600s; ceiling enforced |
| FR-TTL-003 | Reset TTL to base value (300s) when change detected | Must | Entry with detected change has TTL reset to 300s after full fetch |
| FR-TTL-004 | Track extension count in `CacheEntry.metadata["extension_count"]` | Must | Metadata contains integer count; 0 for new entries, increments on each extension |
| FR-TTL-005 | Reset `cached_at` timestamp when extending TTL (new expiration window) | Must | Extended entry has fresh `cached_at`; TTL countdown restarts |
| FR-TTL-006 | Replace `CacheEntry` on extension (immutable design preserved) | Must | New `CacheEntry` created with extended TTL; original entry not mutated |
| FR-TTL-007 | Preserve all original entry data during TTL extension (data, version, project_gid) | Must | Extended entry identical to original except `ttl`, `cached_at`, and `metadata.extension_count` |
| FR-TTL-008 | Support configurable base TTL via `CacheSettings.staleness_check_base_ttl` | Should | Base TTL configurable; default 300s; applies to progressive extension algorithm |
| FR-TTL-009 | Support configurable max TTL via `CacheSettings.staleness_check_max_ttl` | Should | Max TTL configurable; default 86400s; ceiling for progressive extension |

### Functional Requirements - Graceful Degradation (FR-DEGRADE-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DEGRADE-001 | Fall back to full API fetch when lightweight check fails (timeout, error) | Must | API error during batch check triggers full fetch; operation completes successfully |
| FR-DEGRADE-002 | Treat malformed `modified_at` response as changed (trigger full fetch) | Must | Invalid datetime or missing field triggers full fetch; no exception raised |
| FR-DEGRADE-003 | Process successful results from partial batch failure; retry/fallback failed entries | Must | Batch with 8 success + 2 failure: 8 processed normally, 2 fall back to full fetch |
| FR-DEGRADE-004 | Bypass staleness check entirely when cache provider unavailable | Must | `cache_provider=None` proceeds directly to API fetch; no errors |
| FR-DEGRADE-005 | Log all degradation events as warnings with context (error type, GID, fallback action) | Must | Warning log includes `degradation_reason`, `affected_gids`, `fallback_action` |
| FR-DEGRADE-006 | Do not propagate staleness check exceptions to caller (absorb and degrade) | Must | Caller receives either cached data or None (triggering fetch); no exceptions from check |
| FR-DEGRADE-007 | Respect existing retry and circuit breaker policies for batch API calls | Should | Batch staleness check honors `RetryHandler` and `CircuitBreaker` configuration |

### Functional Requirements - Observability (FR-OBS-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-OBS-001 | Log staleness check result per entry: `unchanged`, `changed`, `error`, `deleted` | Must | Structured log includes `staleness_result` field with enum value |
| FR-OBS-002 | Log batch metrics: `batch_size`, `chunk_count`, `api_calls_saved` | Must | Batch log entry includes all three metrics |
| FR-OBS-003 | Log TTL extension: `previous_ttl`, `new_ttl`, `extension_count` | Must | Extension log entry includes all three fields |
| FR-OBS-004 | Log coalescing metrics: `coalesce_window_ms`, `entries_coalesced`, `unique_gids` | Must | Coalesce log entry shows window utilization |
| FR-OBS-005 | Include `cache_operation: staleness_check` to distinguish from regular cache ops | Must | All staleness check logs have this field for filtering |
| FR-OBS-006 | Log cumulative session metrics: `total_checks`, `unchanged_count`, `changed_count`, `error_count` | Should | Session summary available for debugging |
| FR-OBS-007 | Log timing: `check_duration_ms` for lightweight check, `total_duration_ms` including coalesce wait | Should | Performance metrics for optimization |

---

## Non-Functional Requirements

### Performance (NFR-PERF-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Latency for lightweight check (unchanged entity) | <100ms including coalesce wait | `check_duration_ms` + `coalesce_wait_ms` in logs |
| NFR-PERF-002 | API calls for stable entity over 2 hours | 2-3 calls (vs 24 with fixed 5min TTL) | Structured logging count |
| NFR-PERF-003 | Batch efficiency (entries per API call) | >10 average | `batch_size` / `chunk_count` ratio in logs |
| NFR-PERF-004 | Bandwidth reduction per staleness check | 50x (5KB -> 100 bytes) | Response size comparison |
| NFR-PERF-005 | Coalescing overhead | <5ms for batch assembly | `coalesce_overhead_ms` in logs |
| NFR-PERF-006 | Memory overhead for coalescer | <1MB for 1000 pending entries | Memory profiling |

### Compatibility (NFR-COMPAT-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | Backward compatibility | No breaking changes to public APIs | All existing tests pass without modification |
| NFR-COMPAT-002 | `CacheEntry` structure | Metadata-only addition; no field changes | Type checker validation |
| NFR-COMPAT-003 | `Freshness` enum | No new values; extend `STRICT` behavior | Enum unchanged |
| NFR-COMPAT-004 | `CacheProvider` protocol | No method signature changes | Protocol compliance tests |
| NFR-COMPAT-005 | Default behavior | Enabled by default; opt-out via config | Config flag `enable_staleness_checks=True` |

### Reliability (NFR-REL-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-REL-001 | Changed entity detection accuracy | 100% (no stale reads) | Validation test suite |
| NFR-REL-002 | Graceful degradation rate | <0.1% of checks degrade to full fetch | `degradation_count` / `total_checks` ratio |
| NFR-REL-003 | Coalescer thread safety | Zero race conditions | Concurrent load testing |
| NFR-REL-004 | TTL extension correctness | Ceiling never exceeded | Property-based testing |

### Testing (NFR-TEST-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-TEST-001 | Unit test coverage on new code | >90% | pytest-cov report |
| NFR-TEST-002 | Integration test for full staleness flow | Complete path tested | Integration test exists and passes |
| NFR-TEST-003 | Graceful degradation tests | All FR-DEGRADE-* validated | Dedicated test cases |
| NFR-TEST-004 | Concurrent access tests | Race conditions tested | Stress test with 100 concurrent callers |
| NFR-TEST-005 | Progressive TTL tests | Full progression validated | Test verifies 300 -> 600 -> ... -> 86400 |

---

## User Stories / Use Cases

### UC-1: Long-Running Session with Stable Entities (Primary)

**As a** SDK consumer running a long session that repeatedly accesses the same tasks,
**I want** stable entities to progressively extend their TTL after each unchanged check,
**So that** API calls decrease over time and my session becomes more efficient.

**Scenario:**
1. User fetches task T1 (cold fetch, TTL = 300s)
2. After 5 minutes, user accesses T1 again
3. Lightweight check: T1 unchanged -> TTL extended to 600s, cached data returned
4. After 10 minutes, user accesses T1 again
5. Lightweight check: T1 unchanged -> TTL extended to 1200s, cached data returned
6. After 2 hours: T1 has TTL of 3600s+, total API calls = 3 (vs 24 with fixed TTL)

### UC-2: Batch Access to Multiple Entities

**As a** SDK consumer accessing multiple cached entities in rapid succession,
**I want** staleness checks to be batched together,
**So that** a single API call validates multiple entities efficiently.

**Scenario:**
1. User's session has 50 cached tasks, all expired within 50ms window
2. User triggers access to all 50 tasks (e.g., DataFrame refresh)
3. System coalesces all 50 into one batch check
4. Single batch API call (5 chunks of 10) validates all 50 entities
5. 45 unchanged (TTL extended), 5 changed (full fetch triggered)
6. API calls: 5 (batch) + 5 (full fetch) = 10, vs 50 without batching

### UC-3: Entity Modified Externally

**As a** SDK consumer where tasks are modified by other users or systems,
**I want** the staleness check to detect changes and trigger a full fetch,
**So that** I always see the latest data after a change.

**Scenario:**
1. User fetches task T1 (cached with `modified_at: 2025-12-23T10:00:00Z`)
2. External user modifies T1 in Asana (new `modified_at: 2025-12-23T11:30:00Z`)
3. After TTL expires, user accesses T1 again
4. Lightweight check: `modified_at` mismatch detected
5. System triggers full fetch, cache updated with fresh data
6. TTL reset to base (300s), extension_count reset to 0
7. User receives current task data

### UC-4: Graceful Degradation on API Error

**As a** SDK consumer in an environment with occasional API issues,
**I want** staleness check failures to fall back to full fetch,
**So that** my application continues working despite intermittent errors.

**Scenario:**
1. User accesses 10 expired cached tasks
2. Batch staleness check sent to Asana API
3. API returns timeout for 3 tasks, success for 7 tasks
4. 7 successful checks processed (5 extended, 2 changed -> full fetch)
5. 3 failed checks fall back to full fetch
6. User receives valid data for all 10 tasks
7. Warning logged: `degradation_reason: api_timeout, affected_gids: [...]`

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Tasks have stable `modified_at` timestamps | Asana API contract; `modified_at` changes only when task content changes |
| Batch API counts as single request for rate limiting | ADR-0018; Asana docs confirm batch = 1 quota unit |
| 50ms coalescing window is acceptable latency trade-off | P99 latency budget; parallel fetch patterns already add latency |
| `CacheEntry.metadata` field exists and supports arbitrary dict | Discovery document confirms `metadata: dict[str, Any]` field exists |
| Existing `CacheProvider.set_versioned()` supports entry replacement | Standard pattern already used for cache population |
| Asana API returns `modified_at` consistently in all task responses | API contract; field always present for existing tasks |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| `CacheEntry` with `metadata` field | SDK Team | Implemented |
| `BatchClient` for batch API calls | SDK Team | Implemented |
| `CacheProvider.get_versioned()` / `set_versioned()` | SDK Team | Implemented |
| `Freshness` enum with `STRICT` mode | SDK Team | Implemented |
| Version comparison utilities (`versioning.py`) | SDK Team | Implemented |
| Existing staleness functions (`staleness.py`) | SDK Team | Implemented (unused) |
| `asyncio.Lock` for coalescer thread safety | Python stdlib | Available |
| Phase 3 (GID enumeration caching) | SDK Team | Complete (ADR-0131) |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 50ms coalescing adds latency to P99 | Medium | Low | Make window configurable; monitor P99 |
| Progressive TTL causes stale reads | Low | High | Max ceiling 24h; reset on any change; 100% detection accuracy |
| Batch API rate limits reached | Low | Medium | Batch counts as 1 request; chunking handles large batches |
| Thread safety issues in coalescer | Medium | High | Use `asyncio.Lock`; comprehensive concurrent testing |
| `CacheEntry` replacement overhead | Low | Low | Already used pattern for cache population |
| Process restart loses extension state | Medium | Low | Acceptable; resets to base TTL; no correctness issue |
| Malformed API response handling | Low | Medium | Treat as changed; trigger full fetch; log warning |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All questions resolved in Session 2 scope decisions |

**Resolved Decisions:**
1. **Activation**: Enable by default with graceful degradation
2. **TTL Ceiling**: Single 24h maximum for Tasks
3. **Freshness Mode**: Extend existing `Freshness.STRICT` behavior; no new enum value

---

## Priority Summary (MoSCoW)

### Must Have (Blocking Release)

- **FR-BATCH-001 through FR-BATCH-005**: Core batch coalescing
- **FR-STALE-001 through FR-STALE-006**: Staleness check logic
- **FR-TTL-001 through FR-TTL-007**: Progressive TTL extension
- **FR-DEGRADE-001 through FR-DEGRADE-006**: Graceful degradation
- **FR-OBS-001 through FR-OBS-005**: Core observability
- **NFR-PERF-001 through NFR-PERF-004**: Performance targets
- **NFR-COMPAT-001 through NFR-COMPAT-005**: Backward compatibility
- **NFR-REL-001 through NFR-REL-004**: Reliability guarantees
- **NFR-TEST-001 through NFR-TEST-003**: Core test coverage

### Should Have (High Value)

- **FR-BATCH-006**: GID deduplication within batch
- **FR-STALE-007**: `Freshness.STRICT` integration
- **FR-TTL-008, FR-TTL-009**: Configurable TTL settings
- **FR-DEGRADE-007**: Retry/circuit breaker integration
- **FR-OBS-006, FR-OBS-007**: Enhanced observability
- **NFR-PERF-005, NFR-PERF-006**: Performance guardrails
- **NFR-TEST-004, NFR-TEST-005**: Advanced test coverage

### Could Have (Nice to Have)

- Pre-warming staleness coalescer during cache load
- Staleness check metrics in demo script output
- Per-entity-type progressive TTL configuration
- Admin API for forcing TTL reset

### Won't Have (This Phase)

- Project entity staleness checks (have `modified_at` but deferred)
- Nested attribute staleness (subtasks, dependencies)
- S3 tier staleness checks
- Webhook-based cache invalidation
- Configuration UI

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Requirements Analyst | Initial draft based on discovery findings and scope decisions |

---

## Appendix A: Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Discovery | `/docs/analysis/DISCOVERY-CACHE-LIGHTWEIGHT-STALENESS.md` | Infrastructure analysis |
| Prompt 0 | `/docs/requirements/PROMPT-0-CACHE-LIGHTWEIGHT-STALENESS.md` | Initiative specification |
| ADR-0018 | `/docs/decisions/ADR-0018-batch-modification-checking.md` | Batch modification pattern (25s TTL) |
| ADR-0019 | `/docs/decisions/ADR-0019-staleness-detection-algorithm.md` | Staleness detection algorithm |
| ADR-0131 | `/docs/decisions/ADR-0131-gid-enumeration-cache-strategy.md` | Phase 3 GID caching (complete) |

## Appendix B: Key Files for Implementation

| File | Purpose | Key Changes |
|------|---------|-------------|
| `src/autom8_asana/cache/coalescer.py` | NEW: Request coalescer | Batch collection with 50ms window |
| `src/autom8_asana/cache/lightweight_check.py` | NEW: Lightweight API check | Batch `modified_at` API calls |
| `src/autom8_asana/cache/staleness.py` | Extend staleness logic | Invert to trigger checks; add extension logic |
| `src/autom8_asana/cache/entry.py` | Metadata convention | Document `extension_count` in metadata |
| `src/autom8_asana/cache/settings.py` | Configuration | Add `enable_staleness_checks`, `staleness_check_base_ttl`, `staleness_check_max_ttl` |
| `src/autom8_asana/clients/base.py` | Client integration | Integrate staleness check in cache lookup |
| `tests/unit/cache/test_coalescer.py` | NEW: Coalescer tests | Window, batching, concurrency |
| `tests/unit/cache/test_lightweight_check.py` | NEW: Check tests | API format, result handling |
| `tests/unit/cache/test_progressive_ttl.py` | NEW: TTL tests | Extension, ceiling, reset |
| `tests/integration/test_staleness_flow.py` | NEW: Integration tests | Full E2E validation |

## Appendix C: TTL Progression Table

| Extension Count | TTL (seconds) | TTL (human readable) | Cumulative Time (approx) |
|-----------------|---------------|----------------------|--------------------------|
| 0 (base) | 300 | 5 minutes | 0 |
| 1 | 600 | 10 minutes | 5 min |
| 2 | 1200 | 20 minutes | 15 min |
| 3 | 2400 | 40 minutes | 35 min |
| 4 | 4800 | 80 minutes | 1h 15min |
| 5 | 9600 | 160 minutes (~2.7h) | 2h 35min |
| 6 | 19200 | 320 minutes (~5.3h) | 5h 15min |
| 7 | 38400 | 640 minutes (~10.7h) | 10h 35min |
| 8 | 76800 | 1280 minutes (~21h) | 21h 15min |
| 9+ | 86400 | 1440 minutes (24h) - CEILING | 42h 15min+ |

**API Call Comparison (2-hour stable entity):**
- Fixed 5min TTL: 24 API calls
- Progressive TTL: 5 API calls (extensions at 5min, 15min, 35min, 1h15min, 2h35min)
- Reduction: 79%

## Appendix D: Batch API Request Format

```http
POST /batch
Content-Type: application/json

{
  "data": {
    "actions": [
      {
        "method": "GET",
        "relative_path": "/tasks/1234567890",
        "options": { "opt_fields": "modified_at" }
      },
      {
        "method": "GET",
        "relative_path": "/tasks/2345678901",
        "options": { "opt_fields": "modified_at" }
      }
    ]
  }
}
```

**Response (per Asana Batch API):**
```json
[
  {
    "status_code": 200,
    "body": {
      "data": {
        "gid": "1234567890",
        "modified_at": "2025-12-23T10:30:00.000Z"
      }
    }
  },
  {
    "status_code": 200,
    "body": {
      "data": {
        "gid": "2345678901",
        "modified_at": "2025-12-23T09:15:00.000Z"
      }
    }
  }
]
```

**Constraints:**
- Max 10 actions per batch request
- Batch counts as 1 API request for rate limiting
- Response ~100 bytes per entity (vs ~5KB full payload)

## Appendix E: Test Cases Required

### Must Have Tests

| Test Case | Type | Validates |
|-----------|------|-----------|
| `test_coalescer_50ms_window` | Unit | FR-BATCH-001 |
| `test_coalescer_max_batch_size` | Unit | FR-BATCH-002 |
| `test_coalescer_chunk_splitting` | Unit | FR-BATCH-003 |
| `test_coalescer_concurrent_callers` | Unit | FR-BATCH-004 |
| `test_coalescer_immediate_flush_at_max` | Unit | FR-BATCH-005 |
| `test_staleness_check_triggers_on_expiry` | Unit | FR-STALE-001 |
| `test_lightweight_api_format` | Unit | FR-STALE-002 |
| `test_version_comparison_unchanged` | Unit | FR-STALE-003, FR-STALE-004 |
| `test_version_comparison_changed` | Unit | FR-STALE-005 |
| `test_deleted_entity_handling` | Unit | FR-STALE-006 |
| `test_ttl_doubles_on_unchanged` | Unit | FR-TTL-001 |
| `test_ttl_ceiling_enforced` | Unit | FR-TTL-002 |
| `test_ttl_reset_on_change` | Unit | FR-TTL-003 |
| `test_extension_count_tracking` | Unit | FR-TTL-004 |
| `test_cached_at_reset_on_extension` | Unit | FR-TTL-005 |
| `test_entry_immutability_preserved` | Unit | FR-TTL-006 |
| `test_fallback_on_api_error` | Unit | FR-DEGRADE-001 |
| `test_malformed_response_handling` | Unit | FR-DEGRADE-002 |
| `test_partial_batch_failure` | Unit | FR-DEGRADE-003 |
| `test_cache_unavailable_bypass` | Unit | FR-DEGRADE-004 |
| `test_full_staleness_flow_unchanged` | Integration | E2E unchanged path |
| `test_full_staleness_flow_changed` | Integration | E2E changed path |
| `test_progressive_ttl_over_time` | Integration | TTL progression |
| `test_batch_coalescing_under_load` | Integration | Batching efficiency |

### Should Have Tests

| Test Case | Type | Validates |
|-----------|------|-----------|
| `test_gid_deduplication` | Unit | FR-BATCH-006 |
| `test_freshness_strict_integration` | Unit | FR-STALE-007 |
| `test_configurable_base_ttl` | Unit | FR-TTL-008 |
| `test_configurable_max_ttl` | Unit | FR-TTL-009 |
| `test_retry_policy_honored` | Unit | FR-DEGRADE-007 |
| `test_observability_logging` | Unit | FR-OBS-* |
| `test_concurrent_staleness_checks` | Stress | NFR-REL-003 |
| `test_100_entity_batch` | Load | NFR-PERF-003 |
