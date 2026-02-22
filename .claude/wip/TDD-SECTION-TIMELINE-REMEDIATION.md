# TDD: Section Timeline Architecture Remediation

```yaml
id: TDD-SECTION-TIMELINE-REMEDIATION-001
status: DRAFT
date: 2026-02-20
author: architect
prd: PRD-SECTION-TIMELINE-REMEDIATION-001
parent-tdd: TDD-SECTION-TIMELINE-001
impact: high
impact_categories: [data_model, api_contract, service_layer]
```

---

## 1. System Context

### 1.1 Purpose

This design specifies the remediation of the SectionTimeline architecture from a warm-up pipeline model (in-memory `app.state`, startup I/O storms, readiness gates) to a cache-layer-native model using three generic cache primitives: pure-read story access, derived cache entries, and batch cache reads. The result is a compute-on-read-then-cache architecture where timeline data is computed on first request and served from cache on subsequent requests, with no warm-up pipeline, no `app.state`, and no startup-time API calls.

### 1.2 Scope Boundary

This TDD covers Gaps 1, 3, and 4 from the seed document. Gap 2 (project membership caching) is explicitly deferred. Lambda warmer integration (FR-8) is COULD priority and not designed here -- the compute-on-read model must work standalone.

### 1.3 Design Constraints

- Conform to existing `CacheProvider` protocol (`src/autom8_asana/protocols/cache.py`)
- Use `__init_subclass__` registration for new entry types (`src/autom8_asana/cache/models/entry.py:110-124`)
- Preserve `load_stories_incremental()` contract for existing callers (`src/autom8_asana/cache/integration/stories.py:35-109`)
- No `app.state` for timeline data
- No warm-up pipeline for timelines at ECS startup
- Generic parameterization via `(project_gid, classifier_name)` -- not hardcoded to offers
- Compute-on-read-then-cache: first request computes, subsequent requests serve cached result
- JSON serialization for derived cache entries (consistent with existing patterns)

---

## 2. Architecture Overview

### 2.1 Current Architecture (To Be Replaced)

```
ECS Startup
    |
    v
_warm_section_timeline_stories()       [lifespan.py:267-375]
    |
    +-- warm_story_caches()            [section_timeline_service.py:425-504]
    |       3,800 x list_for_task_cached_async()
    |       ~12-15 min, rate-limited
    |
    +-- build_all_timelines()          [section_timeline_service.py:340-422]
    |       3,800 x build_timeline_for_offer()
    |       Stores result on app.state.offer_timelines
    |
    v
Request Time
    |
    +-- _check_readiness(request)      [section_timelines.py:61-87]
    |       Reads app.state.timeline_warm_count/total
    |
    +-- compute_timeline_entries()     [section_timeline_service.py:305-337]
            Reads from app.state.offer_timelines
            Pure CPU day counting
```

### 2.2 Remediated Architecture

```
Request: GET /api/v1/offers/section-timelines?period_start=...&period_end=...
    |
    v
Endpoint Handler                        [section_timelines.py - MODIFIED]
    |
    +-- 1. Check derived cache: get_cached_timelines()
    |       key: "timeline:{project_gid}:{classifier_name}"
    |       type: EntryType.DERIVED_TIMELINE
    |       |
    |       +-- HIT: Deserialize list[SectionTimeline], compute day counts, return
    |       +-- MISS: Continue to step 2
    |
    +-- 2. Acquire computation lock (asyncio.Lock per project+classifier)
    |       |
    |       +-- Lock already held: Wait for lock, then re-check cache (step 1)
    |       +-- Lock acquired: Continue to step 3
    |
    +-- 3. Enumerate tasks: tasks.list_async(project=..., opt_fields=...)
    |       One paginated API call (~3,800 tasks)
    |
    +-- 4. Batch-read cached stories: read_stories_batch()
    |       get_batch(task_gids, EntryType.STORIES) via Redis pipeline
    |       Chunk into batches of 500 to avoid oversized MGET
    |
    +-- 5. Build timelines from cached stories (pure-read, no API calls)
    |       For each task with cached stories:
    |           filter -> sort -> build_intervals -> SectionTimeline
    |       For tasks with no cached stories:
    |           Impute if current_section available, else exclude
    |
    +-- 6. Store derived entry: set_versioned()
    |       key: "timeline:{project_gid}:{classifier_name}"
    |       TTL: 300s (5 min)
    |       data: JSON-serialized list of SectionTimeline
    |
    +-- 7. Compute day counts and return response
    |
    v
Release computation lock
```

### 2.3 How the Three Primitives Compose

| Primitive | Gap | Role in Flow | Step |
|-----------|-----|-------------|------|
| **Pure-read story cache** | Gap 1 | Read cached stories without API calls (step 4 fallback for individual reads) | 4 |
| **Batch cache reads** | Gap 4 | Read all 3,800 story entries in chunked Redis pipeline batches | 4 |
| **Derived cache entries** | Gap 3 | Store computed timelines as a single cache entry for subsequent requests | 1, 6 |

---

## 3. Component Design

### 3.1 Gap 1: Pure-Read Story Cache

**File**: `src/autom8_asana/cache/integration/stories.py`

#### Interface

```python
def read_cached_stories(
    task_gid: str,
    cache: CacheProvider,
) -> list[dict[str, Any]] | None:
    """Read stories from cache without any API call.

    Returns the cached story list if present and not expired,
    or None on cache miss. Does NOT modify the cache. Does NOT
    call the Asana API. This is a pure read-only operation.

    Args:
        task_gid: The task GID to read stories for.
        cache: Cache provider instance.

    Returns:
        List of story dicts if cached, None if cache miss or expired.
    """
```

#### Implementation

```python
def read_cached_stories(
    task_gid: str,
    cache: CacheProvider,
) -> list[dict[str, Any]] | None:
    cached_entry = cache.get_versioned(task_gid, EntryType.STORIES)
    if cached_entry is None:
        return None
    return _extract_stories_list(cached_entry.data)
```

#### Data Flow

```
read_cached_stories(task_gid, cache)
    |
    v
cache.get_versioned(task_gid, EntryType.STORIES)
    |
    +-- Redis HIT: Return stories list
    +-- Redis MISS, S3 HIT: Promote to Redis, return stories list
    +-- Both MISS: Return None
    |
    v
_extract_stories_list(entry.data) -> list[dict] | None
```

#### Integration Points

- Reuses existing `_extract_stories_list()` helper at `stories.py:140-155`
- Reuses existing `CacheProvider.get_versioned()` which handles tiered lookup (Redis then S3)
- `load_stories_incremental()` is unchanged -- this is a new additive function
- Called by the batch reader (Gap 4) as a fallback for individual misses

#### AMB-2 Resolution (Batch Read Granularity)

**Decision**: Per-entity MGET via `get_batch()`, NOT per-project composite.

**Rationale**: The existing cache model stores stories keyed by `task_gid` with `EntryType.STORIES`. Introducing a per-project composite entry would require a new storage format, new invalidation logic, and would duplicate data already stored per-entity. The `get_batch()` protocol method is designed exactly for this: reading N keys of the same type in one operation. Redis pipelined HGETALL is efficient for this pattern.

---

### 3.2 Gap 3: Derived Cache Entries

**Files**: `src/autom8_asana/cache/models/entry.py` (new EntryType + subclass), `src/autom8_asana/cache/integration/derived.py` (new file)

#### 3.2.1 New EntryType Member

Add to `EntryType` enum in `src/autom8_asana/cache/models/entry.py`:

```python
# Per TDD-SECTION-TIMELINE-REMEDIATION: Derived/computed cache entries
# materialized from other cached data (e.g., timelines derived from stories)
DERIVED_TIMELINE = "derived_timeline"  # TTL: 300s (5 min)
```

#### 3.2.2 New CacheEntry Subclass

```python
@dataclass(frozen=True)
class DerivedTimelineCacheEntry(
    CacheEntry,
    entry_types=(EntryType.DERIVED_TIMELINE,),
):
    """Cache entry for derived timeline computations.

    Stores pre-computed SectionTimeline data for a (project, classifier)
    pair. The data field contains JSON-serialized timeline data.

    Attributes:
        classifier_name: Name of the SectionClassifier used (e.g., "offer", "unit").
        source_entity_count: Number of entities included in this computation.
        source_cache_hits: Number of entities whose stories were found in cache.
        source_cache_misses: Number of entities with no cached stories (excluded).
        computation_duration_ms: Time to compute the derived entry.
    """

    classifier_name: str = ""
    source_entity_count: int = 0
    source_cache_hits: int = 0
    source_cache_misses: int = 0
    computation_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize with subclass-specific fields."""
        result = super().to_dict()
        result["classifier_name"] = self.classifier_name
        result["source_entity_count"] = self.source_entity_count
        result["source_cache_hits"] = self.source_cache_hits
        result["source_cache_misses"] = self.source_cache_misses
        result["computation_duration_ms"] = self.computation_duration_ms
        return result

    @classmethod
    def _from_dict_impl(cls, data: dict[str, Any]) -> DerivedTimelineCacheEntry:
        """Construct DerivedTimelineCacheEntry from dict."""
        base = _deserialize_base(data)
        return cls(
            key=base.key,
            data=base.data,
            entry_type=base.entry_type,
            version=base.version,
            cached_at=base.cached_at,
            ttl=base.ttl,
            project_gid=base.project_gid,
            metadata=base.metadata,
            freshness_stamp=base.freshness_stamp,
            classifier_name=data.get("classifier_name", ""),
            source_entity_count=data.get("source_entity_count", 0),
            source_cache_hits=data.get("source_cache_hits", 0),
            source_cache_misses=data.get("source_cache_misses", 0),
            computation_duration_ms=data.get("computation_duration_ms", 0.0),
        )
```

#### 3.2.3 Derived Timeline Integration Module

**New file**: `src/autom8_asana/cache/integration/derived.py`

```python
"""Derived cache entry operations for computed timeline data.

Per TDD-SECTION-TIMELINE-REMEDIATION: Provides read/write operations
for DerivedTimelineCacheEntry, which stores pre-computed SectionTimeline
data keyed by (project_gid, classifier_name).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8_asana.cache.models.entry import (
    CacheEntry,
    DerivedTimelineCacheEntry,
    EntryType,
)

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider


# Default TTL for derived timeline entries: 5 minutes
# Balances freshness (stories may update) vs. computation cost (~2-4s for 3,800 entities)
_DERIVED_TIMELINE_TTL = 300


def make_derived_timeline_key(project_gid: str, classifier_name: str) -> str:
    """Build the cache key for a derived timeline entry.

    Args:
        project_gid: Asana project GID.
        classifier_name: Classifier name ("offer", "unit").

    Returns:
        Composite cache key string.
    """
    return f"timeline:{project_gid}:{classifier_name}"


def get_cached_timelines(
    project_gid: str,
    classifier_name: str,
    cache: CacheProvider,
) -> DerivedTimelineCacheEntry | None:
    """Read a derived timeline entry from cache.

    Args:
        project_gid: Asana project GID.
        classifier_name: Classifier name.
        cache: Cache provider.

    Returns:
        DerivedTimelineCacheEntry if found and not expired, None otherwise.
    """
    key = make_derived_timeline_key(project_gid, classifier_name)
    entry = cache.get_versioned(key, EntryType.DERIVED_TIMELINE)
    if entry is None:
        return None
    # Ensure we return the typed subclass
    if isinstance(entry, DerivedTimelineCacheEntry):
        return entry
    # Fallback: base CacheEntry returned (legacy deserialization)
    return None


def store_derived_timelines(
    project_gid: str,
    classifier_name: str,
    timeline_data: list[dict[str, Any]],
    cache: CacheProvider,
    *,
    entity_count: int = 0,
    cache_hits: int = 0,
    cache_misses: int = 0,
    computation_duration_ms: float = 0.0,
) -> None:
    """Store a derived timeline computation in the cache.

    Args:
        project_gid: Asana project GID.
        classifier_name: Classifier name.
        timeline_data: JSON-serializable list of timeline dicts.
        cache: Cache provider.
        entity_count: Total entities processed.
        cache_hits: Entities with cached stories.
        cache_misses: Entities without cached stories.
        computation_duration_ms: Computation time for observability.
    """
    key = make_derived_timeline_key(project_gid, classifier_name)
    now = datetime.now(UTC)

    entry = DerivedTimelineCacheEntry(
        key=key,
        data={"timelines": timeline_data},
        entry_type=EntryType.DERIVED_TIMELINE,
        version=now,
        cached_at=now,
        ttl=_DERIVED_TIMELINE_TTL,
        project_gid=project_gid,
        metadata={"computed_at": now.isoformat()},
        classifier_name=classifier_name,
        source_entity_count=entity_count,
        source_cache_hits=cache_hits,
        source_cache_misses=cache_misses,
        computation_duration_ms=computation_duration_ms,
    )
    cache.set_versioned(key, entry)
```

#### AMB-1 Resolution (Derived Cache Invalidation Strategy)

**Decision**: TTL-only invalidation. No story-write-triggered recomputation.

**Rationale**: See ADR-0146 for full analysis. The derived entry has a 5-minute TTL. When the underlying story data changes (via `load_stories_incremental` writes), the derived entry is NOT immediately invalidated. Instead, the next request after TTL expiry recomputes. The maximum staleness window is 5 minutes, which is acceptable for day-count aggregation where the data changes slowly (section moves happen at most a few times per day).

The alternative (story-write-triggered invalidation) would require coupling `load_stories_incremental` to the derived entry lifecycle -- adding invalidation calls to every story cache write path. This coupling would violate the layering (raw cache operations should not know about derived computations) and add latency to every story write for a benefit (sub-minute freshness) that the use case does not require.

#### AMB-3 Resolution (Concurrent Computation Guard)

**Decision**: In-process `asyncio.Lock` keyed by `(project_gid, classifier_name)`.

**Rationale**: Each ECS task is independent; there is no benefit to a distributed lock since each container serves its own requests. The `asyncio.Lock` prevents the thundering herd problem where multiple concurrent requests to the same endpoint all attempt to compute the same derived entry simultaneously. The first request acquires the lock and computes; subsequent requests wait for the lock, then find the result in cache.

Implementation:

```python
# In the service layer
import asyncio
from collections import defaultdict

_computation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

def _get_computation_lock(project_gid: str, classifier_name: str) -> asyncio.Lock:
    """Get or create a computation lock for a (project, classifier) pair."""
    key = f"{project_gid}:{classifier_name}"
    return _computation_locks[key]
```

#### AMB-6 Resolution (Derived Entry Serialization Format)

**Decision**: JSON dict serialization.

**Rationale**: Consistent with all other cache entries in the system. `SectionTimeline` is a frozen dataclass; its serialization to JSON dict is straightforward:

```python
def _serialize_timeline(timeline: SectionTimeline) -> dict[str, Any]:
    """Serialize a SectionTimeline to a JSON-compatible dict."""
    return {
        "offer_gid": timeline.offer_gid,
        "office_phone": timeline.office_phone,
        "intervals": [
            {
                "section_name": iv.section_name,
                "classification": iv.classification.value if iv.classification else None,
                "entered_at": iv.entered_at.isoformat(),
                "exited_at": iv.exited_at.isoformat() if iv.exited_at else None,
            }
            for iv in timeline.intervals
        ],
        "task_created_at": timeline.task_created_at.isoformat() if timeline.task_created_at else None,
        "story_count": timeline.story_count,
    }

def _deserialize_timeline(data: dict[str, Any]) -> SectionTimeline:
    """Deserialize a SectionTimeline from a JSON dict."""
    from autom8_asana.models.business.activity import AccountActivity

    intervals = []
    for iv_data in data.get("intervals", []):
        cls_value = iv_data.get("classification")
        classification = AccountActivity(cls_value) if cls_value else None
        intervals.append(SectionInterval(
            section_name=iv_data["section_name"],
            classification=classification,
            entered_at=datetime.fromisoformat(iv_data["entered_at"]),
            exited_at=datetime.fromisoformat(iv_data["exited_at"]) if iv_data.get("exited_at") else None,
        ))

    task_created_at = data.get("task_created_at")
    return SectionTimeline(
        offer_gid=data["offer_gid"],
        office_phone=data.get("office_phone"),
        intervals=tuple(intervals),
        task_created_at=datetime.fromisoformat(task_created_at) if task_created_at else None,
        story_count=data.get("story_count", 0),
    )
```

---

### 3.3 Gap 4: Batch Cache Reads

**File**: `src/autom8_asana/cache/integration/stories.py` (add to existing file)

#### Interface

```python
def read_stories_batch(
    task_gids: list[str],
    cache: CacheProvider,
    *,
    chunk_size: int = 500,
) -> dict[str, list[dict[str, Any]] | None]:
    """Read cached stories for multiple tasks in batched operations.

    Uses CacheProvider.get_batch() for efficient bulk reads.
    Chunks the request into groups of chunk_size to avoid
    oversized Redis MGET operations.

    Args:
        task_gids: List of task GIDs to read stories for.
        cache: Cache provider instance.
        chunk_size: Maximum keys per batch operation (default 500).

    Returns:
        Dict mapping task_gid -> list of story dicts, or None for cache misses.
    """
```

#### Implementation

```python
def read_stories_batch(
    task_gids: list[str],
    cache: CacheProvider,
    *,
    chunk_size: int = 500,
) -> dict[str, list[dict[str, Any]] | None]:
    result: dict[str, list[dict[str, Any]] | None] = {}

    # Chunk to avoid oversized MGET (AMB-5)
    for i in range(0, len(task_gids), chunk_size):
        chunk = task_gids[i : i + chunk_size]
        batch_result = cache.get_batch(chunk, EntryType.STORIES)

        for gid, entry in batch_result.items():
            if entry is not None:
                result[gid] = _extract_stories_list(entry.data)
            else:
                result[gid] = None

    return result
```

#### Data Flow

```
read_stories_batch(task_gids=[gid_1, ..., gid_3800], cache)
    |
    v
Chunk into groups of 500:
    [gid_1..gid_500], [gid_501..gid_1000], ..., [gid_3501..gid_3800]
    |
    v (for each chunk)
cache.get_batch(chunk, EntryType.STORIES)
    |
    +-- TieredCacheProvider.get_batch()     [tiered.py:276-315]
    |       +-- Redis pipeline HGETALL      [redis.py:471-520]
    |       +-- S3 fallback for misses      [s3.py:541-570]
    |       +-- Promote cold hits to hot
    |
    v
Merge chunk results into final dict
    {gid: list[dict] | None, ...}
```

#### AMB-5 Resolution (Batch Size Limits)

**Decision**: Chunk into batches of 500 keys.

**Rationale**: Redis MGET has no hard protocol limit, but practical limits exist:
- Each HGETALL in the pipeline returns the full story list for one task. With ~50 stories per task at ~500 bytes each, that is ~25KB per task.
- 500 tasks x 25KB = ~12.5MB per pipeline response. This is well within Redis's 512MB output buffer default.
- 500 is a conservative chunk size that keeps individual pipeline round-trips under 100ms on production Redis (observed latency: 50-100ms for ~100 keys in existing batch operations).
- S3 fallback is sequential per key (`s3.py:567-568`), so smaller chunks limit the worst-case S3 sequential read time per chunk.

The `chunk_size` parameter is configurable for tuning.

---

## 4. Data Model

### 4.1 New EntryType Member

```
EntryType Enum (entry.py)
    ...existing 16 members...
    DERIVED_TIMELINE = "derived_timeline"   # NEW
```

### 4.2 DerivedTimelineCacheEntry Schema

```
DerivedTimelineCacheEntry (frozen dataclass)
    inherits: CacheEntry
    entry_types: (EntryType.DERIVED_TIMELINE,)

    Fields:
        key: str                        # "timeline:{project_gid}:{classifier_name}"
        data: dict                      # {"timelines": [serialized SectionTimeline, ...]}
        entry_type: EntryType           # DERIVED_TIMELINE
        version: datetime               # Computation timestamp
        cached_at: datetime             # When stored
        ttl: int                        # 300 (5 min)
        project_gid: str                # Asana project GID
        metadata: dict                  # {"computed_at": ISO timestamp}
        classifier_name: str            # "offer" | "unit"
        source_entity_count: int        # Total entities processed
        source_cache_hits: int          # Entities with cached stories
        source_cache_misses: int        # Entities without cached stories
        computation_duration_ms: float  # Computation time

    data.timelines schema (per element):
        {
            "offer_gid": str,
            "office_phone": str | null,
            "intervals": [
                {
                    "section_name": str,
                    "classification": str | null,  # AccountActivity.value
                    "entered_at": str,             # ISO 8601
                    "exited_at": str | null        # ISO 8601
                }
            ],
            "task_created_at": str | null,  # ISO 8601
            "story_count": int
        }
```

### 4.3 Cache Key Format

```
Derived timeline:  timeline:{project_gid}:{classifier_name}
    Example:       timeline:1143843662099250:offer
    Example:       timeline:1234567890000000:unit

Stories (existing): {prefix}:{workspace_gid}:stories:{task_gid}
    No changes to existing key format.
```

---

## 5. Endpoint Migration

### 5.1 Changes to `section_timelines.py`

**Before** (current, reading from `app.state`):

```python
# Imports:
from autom8_asana.services.section_timeline_service import compute_timeline_entries

# Handler reads app.state:
offer_timelines = getattr(request.app.state, "offer_timelines", [])
entries = compute_timeline_entries(offer_timelines, period_start, period_end)
```

**After** (remediated, reading from cache layer):

```python
# Imports:
from autom8_asana.api.dependencies import AsanaClientDualMode
from autom8_asana.services.section_timeline_service import get_or_compute_timelines

# Handler calls service layer:
entries = await get_or_compute_timelines(
    client=client,
    project_gid=BUSINESS_OFFERS_PROJECT_GID,
    classifier_name="offer",
    period_start=period_start,
    period_end=period_end,
)
```

Key changes:
1. **Remove** readiness gate (`_check_readiness`, `_READINESS_THRESHOLD`, `_RETRY_AFTER_SECONDS`, `_READY`/`_NOT_READY`/`_WARM_FAILED` constants)
2. **Remove** `request: Request` parameter dependency (no longer needs `app.state`)
3. **Add** `client: AsanaClientDualMode` dependency (for task enumeration if cache miss)
4. **Replace** `compute_timeline_entries(app.state.offer_timelines, ...)` with `await get_or_compute_timelines(client, ...)`
5. **Add** error handling for cold-cache scenario (returns partial results, not 503)

### 5.2 New Service Function

**File**: `src/autom8_asana/services/section_timeline_service.py`

```python
async def get_or_compute_timelines(
    client: AsanaClient,
    project_gid: str,
    classifier_name: str,
    period_start: date,
    period_end: date,
) -> list[OfferTimelineEntry]:
    """Get timeline entries, computing from cache if needed.

    Implements compute-on-read-then-cache:
    1. Check derived cache for pre-computed timelines
    2. If cache miss, compute from cached stories + task enumeration
    3. Store computed result in derived cache
    4. Compute day counts for the requested period

    Uses asyncio.Lock to prevent thundering herd on cold cache.

    Args:
        client: AsanaClient (for task enumeration on cache miss).
        project_gid: Asana project GID.
        classifier_name: Classifier name ("offer", "unit").
        period_start: Query period start (inclusive).
        period_end: Query period end (inclusive).

    Returns:
        List of OfferTimelineEntry with day counts.
    """
```

### 5.3 Endpoint Error Handling Changes

| Scenario | Before | After |
|----------|--------|-------|
| Warm-up not complete | 503 TIMELINE_NOT_READY | N/A (no warm-up) |
| Warm-up failed | 503 TIMELINE_WARM_FAILED | N/A (no warm-up) |
| Derived cache cold, stories warm | N/A | 200 (compute on demand, <5s) |
| Derived cache cold, stories cold | N/A | 200 with partial results (entities with cached stories only) |
| Both caches empty | N/A | 200 with empty timelines list + WARNING log |
| Asana API failure during task enum | 502 UPSTREAM_ERROR | 502 UPSTREAM_ERROR (preserved) |

The 503 error codes are removed entirely. The endpoint always returns 200 with whatever data is available. An empty result is a valid response when caches are cold -- the Lambda warmer will populate story caches on its next run, and subsequent requests will return full results.

---

## 6. Cleanup Plan

### 6.1 Files to Modify

| File | Changes |
|------|---------|
| `src/autom8_asana/cache/models/entry.py` | Add `DERIVED_TIMELINE` to EntryType, add `DerivedTimelineCacheEntry` subclass |
| `src/autom8_asana/cache/integration/stories.py` | Add `read_cached_stories()`, `read_stories_batch()` functions |
| `src/autom8_asana/api/routes/section_timelines.py` | Remove readiness gate, remove `app.state` reads, add `AsanaClientDualMode` dep, call `get_or_compute_timelines()` |
| `src/autom8_asana/services/section_timeline_service.py` | Add `get_or_compute_timelines()`, keep domain logic functions, remove `warm_story_caches()`, `build_all_timelines()`, `compute_timeline_entries()` |
| `src/autom8_asana/api/lifespan.py` | Remove lines 251-386 (`_warm_section_timeline_stories` and associated setup) |
| `src/autom8_asana/cache/__init__.py` | Export new functions |

### 6.2 New Files

| File | Purpose |
|------|---------|
| `src/autom8_asana/cache/integration/derived.py` | Derived timeline cache read/write operations |

### 6.3 Code to Remove

**From `section_timeline_service.py`**:
- `warm_story_caches()` function (lines 425-504)
- `build_all_timelines()` function (lines 340-422)
- `compute_timeline_entries()` function (lines 305-337)
- `_WARM_CONCURRENCY` constant (line 43)
- `_BUILD_CONCURRENCY` constant (line 47)
- `_WARM_TIMEOUT_SECONDS` constant (line 53)

**From `lifespan.py`** (lines 251-386):
- `app.state.timeline_warm_count` initialization
- `app.state.timeline_total` initialization
- `app.state.timeline_warm_failed` initialization
- `_warm_section_timeline_stories()` async function
- `timeline_warm_task` creation and `app.state` assignment
- Log message for warm task start

**From `section_timelines.py`** (lines 34-87):
- `_READINESS_THRESHOLD` constant
- `_RETRY_AFTER_SECONDS` constant
- `_READY`, `_NOT_READY`, `_WARM_FAILED` constants
- `_check_readiness()` function
- Readiness gate check in handler

**From `section_timelines.py`** (handler body):
- `request: Request` parameter
- `app.state.offer_timelines` read
- `compute_timeline_entries()` call
- 503 TIMELINE_NOT_READY error handling
- 503 TIMELINE_WARM_FAILED error handling

### 6.4 `max_cache_age_seconds` Removal (FR-7)

**Step 1**: Audit callers of `load_stories_incremental()`.

Callers identified (from grep):
- `src/autom8_asana/clients/stories.py:414` -- `StoriesClient.list_for_task_cached()` which accepts `max_cache_age_seconds` and passes through

Callers of `StoriesClient.list_for_task_cached_async()`:
- `section_timeline_service.py:267` -- `build_timeline_for_offer()` passes `max_cache_age_seconds=7200`

After remediation, `build_timeline_for_offer()` will no longer be called in the warm-up path. In the compute-on-read path, stories are read via `read_stories_batch()` (pure-read, no API call). `build_timeline_for_offer()` itself is refactored to accept pre-read stories rather than calling `list_for_task_cached_async()`.

**Step 2**: Once `build_timeline_for_offer()` no longer passes `max_cache_age_seconds`, verify no other caller passes it. If confirmed, remove the parameter from both `load_stories_incremental()` and `StoriesClient.list_for_task_cached()`.

**Risk**: If any other caller is discovered during implementation, defer removal and add a TODO comment. The parameter is harmless when unused -- it defaults to `None` (no-op).

---

## 7. Generic Entity Parameterization

### 7.1 Classifier-Based Architecture

The `CLASSIFIERS` dict (`src/autom8_asana/models/business/activity.py:264-267`) already maps entity type names to `SectionClassifier` instances:

```python
CLASSIFIERS: dict[str, SectionClassifier] = {
    "offer": OFFER_CLASSIFIER,
    "unit": UNIT_CLASSIFIER,
}
```

The remediated architecture parameterizes all timeline operations by `(project_gid, classifier_name)`:

| Function | Parameters | Hardcoded Before | Generic After |
|----------|-----------|-----------------|---------------|
| `get_or_compute_timelines()` | `project_gid, classifier_name` | Business Offers project, OFFER_CLASSIFIER | Any project, any registered classifier |
| `make_derived_timeline_key()` | `project_gid, classifier_name` | N/A (new) | Generic key format |
| `_is_cross_project_noise()` | `classifier: SectionClassifier` | `OFFER_CLASSIFIER` hardcoded | Passed as parameter |
| `_build_intervals_from_stories()` | `classifier: SectionClassifier` | `OFFER_CLASSIFIER` hardcoded | Passed as parameter |

### 7.2 Adding a New Entity Type

To produce Unit timelines:

```python
entries = await get_or_compute_timelines(
    client=client,
    project_gid=BUSINESS_UNITS_PROJECT_GID,
    classifier_name="unit",
    period_start=period_start,
    period_end=period_end,
)
```

Zero new code required beyond passing the correct project GID and classifier name. The `UNIT_CLASSIFIER` is resolved from `CLASSIFIERS["unit"]` inside the service layer.

### 7.3 Refactored Internal Functions

The existing `_is_cross_project_noise()` and `_build_intervals_from_stories()` currently hardcode `OFFER_CLASSIFIER.classify()`. These are refactored to accept `classifier: SectionClassifier` as a parameter:

```python
def _is_cross_project_noise(story: Story, classifier: SectionClassifier) -> bool:
    new_cls = classifier.classify(new_name) if new_name else None
    old_cls = classifier.classify(old_name) if old_name else None
    return new_cls is None and old_cls is None

def _build_intervals_from_stories(
    stories: list[Story],
    classifier: SectionClassifier,
    entity_gid: str | None = None,
) -> tuple[list[SectionInterval], int]:
    # Uses classifier.classify(section_name) instead of OFFER_CLASSIFIER
```

---

## 8. Error Handling and Degradation

### 8.1 Cold Cache Scenarios

| Scenario | Behavior | Response Time |
|----------|----------|---------------|
| **EC-1**: Derived cache cold, story cache warm | Compute on demand. Enumerate tasks (~2s), batch-read stories (~500ms), build timelines (~100ms), store derived entry. | <5s |
| **EC-2**: Both caches cold | Enumerate tasks (~2s). Batch-read returns all misses. Return empty/partial results. Log WARNING. | <3s |
| **EC-3**: Concurrent first-request computation | First request acquires lock, computes. Subsequent requests wait for lock, then read from cache. | <5s (first), <2s (subsequent) |
| **EC-4**: Story cache updated after derived entry cached | Derived entry serves stale data until 5-min TTL expires. Acceptable staleness. | <2s |
| **EC-5**: Partial cache hit in batch read | Process entities with cached stories, exclude those without. Return partial results. | <5s |

### 8.2 Failure Modes

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Redis unavailable | `get_batch()` falls back to S3 (TieredCacheProvider handles this) | Existing circuit breaker + degraded mode |
| S3 unavailable | `get_batch()` returns None for all keys | Return empty results, log ERROR |
| Task enumeration API failure | Cannot compute timelines | Return 502 UPSTREAM_ERROR |
| Lock acquisition timeout | Should not happen (asyncio.Lock has no timeout by default) | Add optional timeout with asyncio.wait_for if needed |
| Serialization error | Cannot store derived entry | Log ERROR, return computed results (just not cached) |

### 8.3 Edge Case Responses

| Edge Case | Design Response |
|-----------|----------------|
| **EC-6**: Entity with zero stories (never warmed) | Pure-read returns None. If task_created_at and current_section available from enumeration, impute interval per existing AC-3.1 logic. |
| **EC-7**: New entity added after derived cache built | Not in derived cache. Next computation (after TTL expiry) includes it. |
| **EC-8**: Very large project (>5,000 entities) | Batch reads chunked at 500 keys. Task enumeration is a single paginated API call (no chunking needed). Total computation time scales linearly but stays under 60s ALB timeout. |

---

## 9. Implementation Sequence

### Phase 1: Gap 1 -- Pure-Read Story Cache (~0.5 day)

**Deliverables**: `read_cached_stories()` function in `stories.py`

1. Add `read_cached_stories()` to `src/autom8_asana/cache/integration/stories.py`
2. Add export to `src/autom8_asana/cache/__init__.py`
3. Write unit tests verifying: cache hit returns stories, cache miss returns None, expired entry returns None
4. Verify no impact on existing `load_stories_incremental()` callers

**Dependency**: None (standalone additive change)

### Phase 2: Gap 4 -- Batch Cache Reads (~0.5 day)

**Deliverables**: `read_stories_batch()` function in `stories.py`

1. Add `read_stories_batch()` to `src/autom8_asana/cache/integration/stories.py`
2. Write unit tests verifying: chunking at 500, mix of hits/misses, empty input
3. Integration test with InMemoryCacheProvider: populate N entries, batch-read, verify round-trip

**Dependency**: Phase 1 (reuses `_extract_stories_list`)

### Phase 3: Gap 3 -- Derived Cache Entries (~1 day)

**Deliverables**: `EntryType.DERIVED_TIMELINE`, `DerivedTimelineCacheEntry`, `derived.py` module

1. Add `DERIVED_TIMELINE` to `EntryType` enum
2. Add `DerivedTimelineCacheEntry` subclass to `entry.py`
3. Create `src/autom8_asana/cache/integration/derived.py` with `get_cached_timelines()`, `store_derived_timelines()`
4. Add serialization/deserialization functions for `SectionTimeline`
5. Write unit tests for `__init_subclass__` registration, `to_dict()`/`from_dict()` round-trip, TTL behavior
6. Write integration test: store derived entry, retrieve, verify content

**Dependency**: None (standalone, but benefits from Phase 2 for the integration test)

### Phase 4: Service Layer + Endpoint Migration (~1 day)

**Deliverables**: `get_or_compute_timelines()`, updated endpoint handler

1. Add `get_or_compute_timelines()` to `section_timeline_service.py`
2. Refactor `_is_cross_project_noise()` and `_build_intervals_from_stories()` to accept `SectionClassifier` parameter
3. Add `_computation_locks` and lock acquisition logic
4. Update `section_timelines.py` endpoint handler:
   - Remove readiness gate
   - Add `AsanaClientDualMode` dependency
   - Call `get_or_compute_timelines()`
   - Update error handling
5. Write tests for: warm cache path (<2s), cold computation path, concurrent request locking, partial results on cache miss, generic parameterization (offer + unit)

**Dependency**: Phases 1, 2, 3

### Phase 5: Cleanup (~0.5 day)

**Deliverables**: Removed warm-up pipeline, removed app.state keys, removed max_cache_age_seconds

1. Remove warm-up code from `lifespan.py` (lines 251-386)
2. Remove `warm_story_caches()`, `build_all_timelines()`, `compute_timeline_entries()` from `section_timeline_service.py`
3. Remove `_WARM_CONCURRENCY`, `_BUILD_CONCURRENCY`, `_WARM_TIMEOUT_SECONDS` constants
4. Audit and remove `max_cache_age_seconds` if no remaining callers
5. Run full test suite, verify no regressions
6. Verify no remaining references to `app.state.offer_timelines`, `timeline_warm_count`, `timeline_total`, `timeline_warm_failed`

**Dependency**: Phase 4

### Total Estimated Effort: ~3.5 days

---

## 10. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R-1 | Cold-start latency exceeds 5s target for first request | Medium | Medium | Task enumeration is the bottleneck (~2s). If it exceeds 5s, consider caching the enumeration result (Gap 2, deferred). Monitor p95 latency after deployment. |
| R-2 | S3 `get_batch` is sequential, not true batch | Known | Low | Redis is the hot tier; S3 fallback is rare after Lambda warmer runs. Chunk size limits worst-case S3 sequential reads to 500 keys. |
| R-3 | `max_cache_age_seconds` removal breaks unknown caller | Low | Medium | Step-by-step audit. If any caller found, defer removal (FR-7 is SHOULD priority). Parameter defaults to None (no-op). |
| R-4 | Derived entry TTL (5 min) too stale for some use cases | Low | Low | TTL is configurable. Can be tuned down to 60s if freshness demands increase. 5 min is conservative starting point. |
| R-5 | Lock contention under high concurrent load | Low | Medium | Lock is per (project, classifier) pair. In practice, timeline endpoints are called infrequently (reconciliation batch, not user-facing). |
| R-6 | JSON serialization of 3,800 timelines exceeds Redis value size | Low | Medium | Estimated: 3,800 x ~200 bytes = ~760KB. Redis max value is 512MB. S3 has no practical limit. |
| R-7 | Warm-up removal causes production regression | Medium | High | Deploy behind feature flag (optional). Verify Lambda warmer populates story caches on schedule. Monitor first request latency after deployment. Rollback plan: revert to previous commit. |

---

## 11. ADRs

| ADR | Title | Resolves |
|-----|-------|----------|
| [ADR-0146](/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0146-pure-read-story-cache-and-batch-reads.md) | Pure-read mode for story cache and batch reads | AMB-1 (partial), AMB-2, AMB-5 |
| [ADR-0147](/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0147-derived-timeline-cache-entries.md) | Derived timeline cache entries | AMB-1, AMB-3, AMB-6 |
| [ADR-0148](/Users/tomtenuta/Code/autom8y-asana/docs/decisions/ADR-0148-warm-up-pipeline-removal.md) | Warm-up pipeline removal and compute-on-read model | AMB-4 |

---

## 12. PRD Traceability

| PRD Requirement | TDD Section | Status |
|----------------|-------------|--------|
| FR-1: Pure-read story cache | 3.1 | Designed |
| FR-2: Derived cache entry type | 3.2, 4.1, 4.2 | Designed |
| FR-3: Batch story cache reads | 3.3 | Designed |
| FR-4: Endpoint migration off app.state | 5.1, 5.2, 5.3 | Designed |
| FR-5: Generic entity parameterization | 7.1, 7.2, 7.3 | Designed |
| FR-6: Warm-up pipeline removal | 6.1-6.3 | Designed |
| FR-7: max_cache_age_seconds removal | 6.4 | Designed |
| NFR-1: <2s warm / <5s cold | 8.1, 9 (Phase 4 tests) | Designed |
| NFR-2: No startup I/O storm | 6.1-6.3 (removal) | Designed |
| NFR-3: Graceful degradation | 5.3, 8.1, 8.2 | Designed |
| NFR-4: Cache coherence (TTL-based) | 3.2.3 (AMB-1 resolution) | Designed |
| SC-1 through SC-8 | Various | All addressed |

### Ambiguity Resolutions

| AMB | Resolution | ADR |
|-----|-----------|-----|
| AMB-1: Derived cache invalidation | TTL-only (5 min), no story-write triggers | ADR-0147 |
| AMB-2: Batch read granularity | Per-entity MGET via `get_batch()` | ADR-0146 |
| AMB-3: Concurrent computation guard | In-process `asyncio.Lock` per (project, classifier) | ADR-0147 |
| AMB-4: Response time targets | <2s warm, <5s cold (confirmed) | ADR-0148 |
| AMB-5: Batch size limits | Chunk at 500 keys | ADR-0146 |
| AMB-6: Serialization format | JSON dict | ADR-0147 |

### Edge Case Coverage

| EC | Design Response | TDD Section |
|----|----------------|-------------|
| EC-1: Cold derived, warm stories | Compute on demand | 8.1 |
| EC-2: Cold derived, cold stories | Partial results or empty | 8.1 |
| EC-3: Concurrent first computation | asyncio.Lock | 3.2.3 (AMB-3) |
| EC-4: Story updated after derived cached | Stale until TTL | 3.2.3 (AMB-1) |
| EC-5: Partial batch hit | Process hits, exclude misses | 8.1 |
| EC-6: Zero stories (never warmed) | Impute from enumeration data | 8.3 |
| EC-7: New entity after derived built | Next TTL cycle includes it | 8.3 |
| EC-8: >5,000 entities | Chunked batch reads | 8.3 |

---

## 13. Handoff Checklist

- [x] TDD covers all PRD requirements (FR-1 through FR-7)
- [x] Component boundaries and responsibilities are clear (stories.py / derived.py / service / route)
- [x] Data model defined with storage approach (EntryType.DERIVED_TIMELINE, DerivedTimelineCacheEntry)
- [x] API contracts specified (endpoint changes, new function signatures)
- [x] ADRs document all significant decisions (3 ADRs)
- [x] All 6 ambiguities explicitly resolved
- [x] All 8 edge cases have design responses
- [x] Risks identified with mitigations (7 risks)
- [x] Implementation sequence is realistic and dependency-ordered
- [x] Generic entity parameterization proven for both Offer and Unit
- [x] Cleanup plan specifies exact lines/functions to remove
- [x] Principal Engineer can implement without architectural questions

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD (this document) | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-SECTION-TIMELINE-REMEDIATION.md` | Written |
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-SECTION-TIMELINE-REMEDIATION.md` | Read-verified |
| Seed document | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/SECTION-TIMELINE-ARCH-REMEDIATION.md` | Read-verified |
| Cache architecture review | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/q1_arch/ARCH-REVIEW-1-CACHE.md` | Read-verified |
| Original TDD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-SECTION-TIMELINE.md` | Read-verified |
| Story cache integration | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/stories.py` | Read-verified (lines 35-109, 140-155) |
| CacheEntry hierarchy | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/entry.py` | Read-verified (EntryType: lines 20-51, __init_subclass__: lines 110-124, subclasses: lines 354-580) |
| CacheProvider protocol | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/protocols/cache.py` | Read-verified (get_batch: lines 108-124) |
| TieredCacheProvider.get_batch | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/providers/tiered.py` | Read-verified (lines 276-315, confirmed two-tier lookup with promotion) |
| RedisCacheProvider.get_batch | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/redis.py` | Read-verified (lines 471-520, confirmed pipelined HGETALL) |
| S3CacheProvider.get_batch | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/backends/s3.py` | Read-verified (lines 541-570, confirmed sequential per-key) |
| Section timeline service | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` | Read-verified (full file) |
| Section timeline endpoint | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py` | Read-verified (full file) |
| Lifespan warm-up | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py` | Read-verified (lines 251-386) |
| Domain models | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py` | Read-verified (full file) |
| CLASSIFIERS dict | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` | Read-verified (lines 264-267) |
| StoriesClient caller | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/stories.py` | Read-verified (lines 395-456, confirmed max_cache_age_seconds passthrough) |
