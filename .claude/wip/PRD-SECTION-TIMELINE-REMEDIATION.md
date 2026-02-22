# PRD: Section Timeline Architecture Remediation

```yaml
id: PRD-SECTION-TIMELINE-REMEDIATION-001
status: DRAFT
date: 2026-02-20
author: requirements-analyst
seed: .claude/wip/SECTION-TIMELINE-ARCH-REMEDIATION.md
parent-prd: PRD-SECTION-TIMELINE-001
impact: high
impact_categories: [data_model, api_contract]
```

---

## 1. Problem Statement

The SectionTimeline feature is operational (1.4s response, 3,769 offers, 0 invariant violations) but its architecture is a collection of workarounds for missing cache layer primitives. Four cache gaps forced a 12-15 minute warm-up pipeline at ECS startup, in-memory `app.state` that dies on every restart, a `max_cache_age_seconds` bolt-on to suppress per-entity API calls, and readiness gates for the warm-up window.

These workarounds have caused 13 iterative production deployments, including rate limit saturation (659 and 291 429-events), warm-up timeouts, invisible warm data, and 60s ALB timeout breaches.

The remediation closes three of the four identified cache primitive gaps so that any entity type with a `SectionClassifier` can derive timeline data from cached stories without a dedicated warm-up pipeline, in-memory state, or startup-time I/O storms.

**Reference**: Seed document, "Problem Statement" and "Production Incident History" sections.

---

## 2. Scope

### In Scope (3 Gaps)

| Gap | Description | Rationale |
|-----|-------------|-----------|
| **Gap 1**: Pure-read story cache | `load_stories_incremental()` always makes a live API call. Need a mode that returns cached data without network I/O. | Eliminates `max_cache_age_seconds` hack and enables derived computations from existing cached data. |
| **Gap 3**: Derived/computed cache entries | Cache layer only stores raw API responses. No concept of materialized views computed from cached data. | Eliminates warm-up pipeline and `app.state` by storing computed timelines alongside raw stories. |
| **Gap 4**: Batch cache reads | Reading 3,800 individual cache entries from S3 per-request is slow. `CacheProvider.get_batch()` exists in protocol but is unused by the story path. | Enables efficient bulk reads for the derived timeline computation without per-entity round-trips. |

### Deferred

| Gap | Description | Rationale for Deferral |
|-----|-------------|----------------------|
| **Gap 2**: Project membership caching | `tasks.list_async(project=...)` always hits Asana API. `EntryType.GID_ENUMERATION` exists but is unused here. | Independent concern; can be filed as follow-on work. Does not block the compute-on-read model since task enumeration occurs once per request, not once per entity. |

### Entity Scope

Both Offer and Unit timelines must be validated. The `CLASSIFIERS` dict (`activity.py:264-267`) already maps `"offer"` and `"unit"` to their respective `SectionClassifier` instances. The remediated architecture must prove the generic primitive works for both entity types without entity-specific code paths.

---

## 3. User Stories

### US-1: Cache-Only Story Reads

**As** a derived computation (timeline builder),
**I want** to read stories from cache without triggering an API call,
**so that** I can compute timelines from existing cached data at request time without warm-up infrastructure.

### US-2: Derived Timeline Caching

**As** a section timeline endpoint,
**I want** computed timeline data stored in the cache layer alongside raw stories,
**so that** subsequent requests for the same entity serve precomputed results instead of re-deriving from raw stories on every call.

### US-3: Efficient Bulk Story Access

**As** a timeline computation for an entire project,
**I want** to read all cached stories for a project's entities in a single batch operation,
**so that** I avoid 3,800 individual S3 round-trips and stay within the 60s ALB timeout.

### US-4: Generic Entity Timeline

**As** an operations team member,
**I want** the timeline primitive to work for both Offers and Units with only a classifier parameter,
**so that** adding new entity types does not require new warm-up pipelines or endpoint code.

---

## 4. Functional Requirements

### Must Have

- **FR-1**: Pure-read story cache function [Gap 1] [MUST]
  - A mechanism to read cached stories for a task GID without making any Asana API call.
  - Returns cached stories if present, or indicates cache miss (returns `None` or empty).
  - Does not modify the cache state (no writes, no incremental append).
  - The existing `load_stories_incremental()` contract is preserved unchanged for callers that need the incremental-with-API-call behavior.
  - **Source**: Seed doc, Gap 1; `stories.py:35-109`.

- **FR-2**: Derived cache entry type [Gap 3] [MUST]
  - A new `EntryType` (or extension of the existing enum) to represent computed/derived data.
  - A `CacheEntry` subclass registered via `__init_subclass__` auto-registration (`entry.py:110-124`).
  - Derived entries store pre-computed `SectionTimeline` data keyed to `(project_gid, entity_gid, classifier_name)`.
  - Derived entries carry a staleness marker linked to the freshness of their source stories.
  - **Source**: Seed doc, Gap 3; `entry.py:20-51`, `entry.py:354-580`.

- **FR-3**: Batch story cache reads [Gap 4] [MUST]
  - A function to read stories for multiple task GIDs in a single operation, using `CacheProvider.get_batch()` (`protocols/cache.py:108-124`).
  - Returns a mapping of `task_gid -> list[Story] | None` (None for cache misses).
  - Uses the same `EntryType.STORIES` as individual reads.
  - **Source**: Seed doc, Gap 4; `protocols/cache.py:108-124`.

- **FR-4**: Endpoint migration off `app.state` [MUST]
  - `GET /api/v1/offers/section-timelines` reads from the cache layer (derived entries or compute-on-read) instead of `app.state.offer_timelines`.
  - No `app.state` keys for timeline data (`offer_timelines`, `timeline_warm_count`, `timeline_total`, `timeline_warm_failed`).
  - **Source**: Seed doc, "Anti-Patterns" and "Success Criteria".

- **FR-5**: Generic entity parameterization [MUST]
  - The timeline builder accepts `(project_gid, classifier)` as parameters instead of hardcoding to offers.
  - `SectionClassifier` from `CLASSIFIERS` dict (`activity.py:264-267`) provides the entity type mapping.
  - Producing Unit timelines (using `UNIT_CLASSIFIER`) requires zero new code beyond passing a different classifier and project GID.
  - **Source**: Seed doc, Architectural Question 5; `activity.py:264-267`.

### Should Have

- **FR-6**: Warm-up pipeline removal [SHOULD]
  - Remove `warm_story_caches()` and `build_all_timelines()` from `section_timeline_service.py`.
  - Remove `_warm_section_timeline_stories()` from `lifespan.py` (lines 251-386).
  - Remove `_WARM_CONCURRENCY`, `_BUILD_CONCURRENCY`, `_WARM_TIMEOUT_SECONDS` constants.
  - Remove readiness gate logic from `section_timelines.py` (lines 55-87).
  - **Source**: Seed doc, Phase 4: Cleanup.

- **FR-7**: `max_cache_age_seconds` removal [SHOULD]
  - Remove the `max_cache_age_seconds` parameter from `load_stories_incremental()` if no callers depend on it after FR-1 is implemented.
  - Audit all callers of `load_stories_incremental()` to confirm no remaining usage.
  - **Source**: Seed doc, Gap 1 and Anti-Patterns.

### Could Have

- **FR-8**: Derived cache warming via Lambda [COULD]
  - The existing Lambda warmer (`lambda_handlers/cache_warmer.py`) could trigger derived timeline materialization after story cache warming, eliminating even the first-request computation cost.
  - This is an optimization; the compute-on-read model must work without it.
  - **Source**: Seed doc, Anti-Patterns ("Do NOT ignore the Lambda cache warmer").

---

## 5. Non-Functional Requirements

- **NFR-1: Response Time** -- `GET /api/v1/offers/section-timelines` responds in <2s with warm cache, <5s with cold derived cache (computed on demand), measured at p95. (Note: the original PRD specified <5s p95 for the warm-up-based model. The seed document targets <2s for the remediated architecture.)
- **NFR-2: No Startup I/O Storm** -- Zero Asana API calls during ECS startup for timeline purposes. Story cache warming happens via the existing Lambda warmer schedule, not at container boot.
- **NFR-3: Graceful Degradation** -- When the derived cache is empty (cold start), the endpoint computes timelines on demand from cached stories (FR-1 + FR-3). If stories are also uncached, the endpoint returns partial results for entities with cached stories and excludes entities without cached data.
- **NFR-4: Cache Coherence** -- Derived timeline entries are invalidated when their source story data changes. Invalidation must be eventual-consistent (TTL-based is acceptable; real-time is not required).

---

## 6. Edge Cases

| ID | Condition | Expected Behavior |
|----|-----------|-------------------|
| EC-1 | Cold derived cache, warm story cache | Compute timelines on demand from cached stories. Response may be slower (<5s) but succeeds. Cache the computed result for subsequent requests. |
| EC-2 | Cold derived cache, cold story cache | Return partial results (entities with cached stories only) or empty array. Do NOT trigger Asana API calls at request time. Log at WARNING. |
| EC-3 | Concurrent requests during first computation | Only one computation runs; subsequent requests either wait or receive the result once available. No thundering herd of parallel computations. |
| EC-4 | Story cache updated after derived entry cached | Derived entry serves stale data until its TTL expires or invalidation fires. Staleness is bounded by derived entry TTL. |
| EC-5 | `get_batch()` partial cache hit | Batch read returns a mix of hits and misses. Misses are either computed on demand or excluded from results, per NFR-3 graceful degradation. |
| EC-6 | Entity with zero stories in cache (never warmed) | Pure-read returns None/empty. If imputation data (task_created_at, current section) is available from task enumeration, imputation still works per original PRD AC-3.1. |
| EC-7 | New entity added to project after derived cache built | Not in derived cache; computed on demand from story data (if cached) or excluded. Next full computation includes it. |
| EC-8 | Very large project (>5,000 entities) | Batch reads must handle pagination or chunking. `get_batch()` should not attempt 5,000 keys in a single Redis MGET or S3 multi-get. |

---

## 7. Success Criteria

- [ ] **SC-1**: `GET /api/v1/offers/section-timelines` responds in <2s without any warm-up pipeline running at startup.
- [ ] **SC-2**: No `app.state` keys exist for timeline data (offer_timelines, timeline_warm_count, timeline_total, timeline_warm_failed).
- [ ] **SC-3**: Unit timelines can be produced using `UNIT_CLASSIFIER` with zero new code beyond passing the classifier and project GID as parameters.
- [ ] **SC-4**: Zero additional Asana API calls at request time for entities with cached stories.
- [ ] **SC-5**: When derived cache is cold but story cache is warm, the endpoint returns a valid response (computed on demand) within 5 seconds.
- [ ] **SC-6**: When both caches are cold, the endpoint degrades gracefully (partial results or empty, no 500/503 error).
- [ ] **SC-7**: Existing callers of `load_stories_incremental()` (DataFrame computation path) are unaffected by the changes.
- [ ] **SC-8**: The `max_cache_age_seconds` parameter is removed from the codebase (or confirmed unused if deferring removal).

---

## 8. Constraints

- **Compute model**: Compute-on-read-then-cache. No Lambda warmer integration in this iteration. Derived entries are computed on first request and cached for subsequent reads.
- **Preserve story cache contract**: `load_stories_incremental()` must continue to work for all existing callers. The pure-read mode is additive (new function or new parameter), not a modification of existing behavior.
- **No `app.state` for timeline data**: Derived data belongs in the cache layer, not in process memory.
- **No warm-up pipeline**: The architecture must function without any startup-time background tasks for timeline computation.
- **No hardcoding to offers**: The solution must be parameterized by `(project_gid, classifier)`.
- **Existing `CacheProvider` protocol**: Implementation must conform to the existing protocol. New entry types use `__init_subclass__` registration.
- **No external consumer impact**: The only consumer of `app.state.offer_timelines` is the section-timeline endpoint. No downstream systems depend on the warm-up state keys.

---

## 9. Out of Scope

- **Gap 2 (project membership caching)**: `tasks.list_async(project=...)` caching is a separate concern. Filed as follow-on.
- **Lambda warmer integration**: FR-8 is COULD priority; the compute-on-read model must work standalone.
- **Webhook-based invalidation**: No real-time invalidation from Asana events. TTL-based staleness is sufficient.
- **Unit timeline endpoint**: The generic primitive must support Units, but exposing a `GET /api/v1/units/section-timelines` endpoint is not in scope. Validation is at the service/test level.
- **reconcile-spend integration**: No changes to the reconciliation pipeline's consumption of timeline data.
- **Shadow mode / feature flags**: The remediated endpoint replaces the current implementation directly.

---

## 10. Dependencies

| Dependency | Location | Status |
|------------|----------|--------|
| `CacheProvider.get_batch()` protocol method | `protocols/cache.py:108-124` | Exists, untested on story path |
| `CacheEntry.__init_subclass__` auto-registration | `entry.py:110-124` | Exists, working for other types |
| `CLASSIFIERS` dict with Offer and Unit classifiers | `activity.py:264-267` | Exists, both classifiers registered |
| `EntryType` enum extensibility | `entry.py:20-51` | Exists, 16 types currently defined |
| `SectionTimeline` domain model (frozen dataclass) | `models/business/section_timeline.py` | Exists, no changes needed |
| `load_stories_incremental()` story cache function | `cache/integration/stories.py:35-109` | Exists, must be preserved |

---

## 11. Gaps and Ambiguities in Seed Document

The following items surfaced during validation and should be resolved during architecture design:

| ID | Item | Seed Doc Reference | Resolution Needed |
|----|------|-------------------|-------------------|
| AMB-1 | **Derived cache invalidation strategy**: When underlying stories change, how is the derived timeline entry invalidated? TTL-only, or story-cache-write triggers recomputation? | Gap 3 description | Architect should specify in ADR. TTL-only is simplest; trigger-on-write gives fresher data but adds coupling. |
| AMB-2 | **Batch read granularity**: Is the batch key per-entity (MGET of N individual story entries) or per-project (one composite entry for all stories in a project)? | Gap 4, Architectural Question 4 | Architect should decide. Per-entity batch via `get_batch()` is more natural given the existing protocol; per-project composite is a new pattern. |
| AMB-3 | **Concurrent computation guard**: EC-3 (concurrent first-request computation) needs a locking mechanism. Is this an in-process lock, or a distributed lock via Redis? | Not addressed in seed doc | Architect should specify. In-process `asyncio.Lock` keyed by `(project_gid, classifier)` is likely sufficient since ECS tasks are independent. |
| AMB-4 | **Response time target discrepancy**: Seed doc says "<2s", original PRD says "<5s p95". Which applies post-remediation? | Seed doc Success Criteria vs. PRD NFR-1 | Stakeholder confirmed <2s is the target for warm cache; <5s for cold derived cache (on-demand computation). Both documented in NFR-1 above. |
| AMB-5 | **Batch size limits for `get_batch()`**: With ~3,800 entities, does the Redis MGET or S3 multi-get have practical size limits? | Not addressed | Architect should specify chunking strategy if needed (e.g., batches of 500). |
| AMB-6 | **Derived entry serialization format**: SectionTimeline is a frozen dataclass. What serialization format for the cache entry? JSON dict? Pickle? Custom? | Not addressed | Architect should specify in TDD. JSON dict is consistent with other cache entries. |

---

## 12. Impact Assessment

```yaml
impact: high
impact_categories: [data_model, api_contract]
```

**Rationale**:
- **data_model**: New `EntryType` member and `CacheEntry` subclass added to the cache model hierarchy.
- **api_contract**: Internal API changes (removing `app.state`, removing `max_cache_age_seconds`, changing endpoint's data source). No external breaking changes -- the HTTP endpoint contract remains identical.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD (this document) | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-SECTION-TIMELINE-REMEDIATION.md` | Written |
| Seed document | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/SECTION-TIMELINE-ARCH-REMEDIATION.md` | Read-verified |
| Original PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-SECTION-TIMELINE.md` | Read-verified |
| Original TDD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-SECTION-TIMELINE.md` | Read-verified |
| Cache architecture review | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ARCH-REVIEW-1-CACHE.md` | Read-verified |
| CacheProvider protocol | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/protocols/cache.py` | Read-verified (lines 108-124) |
| EntryType enum | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/entry.py` | Read-verified (lines 20-124) |
| Story cache integration | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py` | Read-verified (lines 85-109) |
| CLASSIFIERS dict | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` | Read-verified (lines 264-267) |
