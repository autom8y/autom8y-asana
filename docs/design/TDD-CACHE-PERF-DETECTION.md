---
status: superseded
superseded_by: /docs/reference/REF-cache-patterns.md
superseded_date: 2025-12-24
---

# TDD: Detection Result Caching

## Metadata

- **TDD ID**: TDD-CACHE-PERF-DETECTION
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-23
- **Last Updated**: 2025-12-23
- **PRD Reference**: [PRD-CACHE-PERF-DETECTION](/docs/requirements/PRD-CACHE-PERF-DETECTION.md)
- **Related TDDs**: TDD-DETECTION, TDD-CACHE-INTEGRATION, TDD-WATERMARK-CACHE
- **Related ADRs**: [ADR-0143](/docs/decisions/ADR-0143-detection-result-caching.md), ADR-0094, ADR-0125

---

## Overview

This TDD defines the technical architecture for caching `DetectionResult` after Tier 4 execution to eliminate redundant subtask API calls. The design integrates with existing cache infrastructure, placing the cache check AFTER Tiers 1-3 (the fast path) and BEFORE Tier 4 (the expensive path). This achieves 40x speedup on repeat detections (<5ms vs ~200ms) without regressing performance for tasks detected via the fast path.

---

## Requirements Summary

From PRD-CACHE-PERF-DETECTION:

- **FR-ENTRY-001 to FR-ENTRY-003**: Add `EntryType.DETECTION` to cache entry types
- **FR-CACHE-001 to FR-CACHE-006**: Cache integration around Tier 4
- **FR-VERSION-001 to FR-VERSION-004**: Versioning with `task.modified_at`
- **FR-INVALIDATE-001 to FR-INVALIDATE-004**: SaveSession invalidation
- **FR-DEGRADE-001 to FR-DEGRADE-004**: Graceful degradation
- **FR-OBSERVE-001 to FR-OBSERVE-003**: Structured logging
- **NFR-LATENCY-001 to NFR-LATENCY-004**: Performance targets
- **NFR-COMPAT-001 to NFR-COMPAT-004**: Backward compatibility
- **NFR-ACCURACY-001 to NFR-ACCURACY-003**: Detection correctness

---

## System Context

The detection caching feature integrates with existing SDK infrastructure:

```
+-------------------------------------------------------------------+
|                        Consumer Application                        |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
|                     hydrate_from_gid_async()                       |
|                   _traverse_upward_async()                         |
+-------------------------------------------------------------------+
                                |
                                v
+-------------------------------------------------------------------+
|                    detect_entity_type_async()                      |
|  +------------------------------------------------------------+   |
|  | Tier 1: Project membership (O(1), async discovery)         |   |
|  | Tier 2-3: Name patterns, parent inference (O(1), sync)     |   |
|  | ---------------------------------------------------------- |   |
|  | [CACHE CHECK HERE - only if allow_structure_inspection]    |   |
|  |   |-> HIT: Return cached DetectionResult (<5ms)            |   |
|  |   |-> MISS: Continue to Tier 4                             |   |
|  | ---------------------------------------------------------- |   |
|  | Tier 4: Structure inspection (~200ms API call)             |   |
|  |   |-> Success: Cache result, return                        |   |
|  |   |-> None: Fall through to Tier 5                         |   |
|  | Tier 5: UNKNOWN fallback (not cached)                      |   |
|  +------------------------------------------------------------+   |
+-------------------------------------------------------------------+
        |                       |
        v                       v
+------------------+    +------------------+
|   TasksClient    |    | CacheProvider    |
| subtasks_async() |    | get() / set()    |
+------------------+    +------------------+
        |                       |
        v                       v
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
|  |      - EntryType.DETECTION [NEW]                            |   |
|  +------------------------------------------------------------+   |
+-------------------------------------------------------------------+
```

---

## Design

### Component Architecture

| Component | Responsibility | Changes |
|-----------|----------------|---------|
| `cache/entry.py` | Cache entry type definitions | ADD: `EntryType.DETECTION` |
| `detection/facade.py` | Detection orchestration | UPDATE: Add cache check/store around Tier 4 |
| `persistence/session.py` | Unit of Work with invalidation | UPDATE: Add `EntryType.DETECTION` to invalidation |

### Component Details

#### 1. EntryType.DETECTION

**Location**: `/src/autom8_asana/cache/entry.py`

```python
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
    DETECTION = "detection"  # NEW: Per PRD-CACHE-PERF-DETECTION
```

Per FR-ENTRY-001: New enum member for detection result caching.

#### 2. Detection Cache Helpers

**Location**: `/src/autom8_asana/models/business/detection/facade.py`

```python
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from autom8_asana.cache.entry import CacheEntry, EntryType
from autom8_asana.models.business.detection.types import DetectionResult, EntityType

if TYPE_CHECKING:
    from autom8_asana.cache.provider import CacheProvider
    from autom8_asana.models.task import Task

# Default TTL for detection cache (matches task cache per FR-VERSION-003)
DETECTION_CACHE_TTL = 300


def _get_cached_detection(
    task_gid: str,
    cache: CacheProvider,
) -> DetectionResult | None:
    """Retrieve cached detection result for task GID.

    Per FR-CACHE-001: Check cache before Tier 4 execution.
    Per FR-DEGRADE-001: Returns None on any cache error.

    Args:
        task_gid: The task GID to look up.
        cache: Cache provider instance.

    Returns:
        DetectionResult if cache hit and valid, None otherwise.
    """
    try:
        entry = cache.get(task_gid, EntryType.DETECTION)
        if entry is None:
            return None

        # Check TTL expiration
        if entry.is_expired():
            return None

        # Deserialize DetectionResult from cached dict
        data = entry.data
        return DetectionResult(
            entity_type=EntityType(data["entity_type"]),
            confidence=data["confidence"],
            tier_used=data["tier_used"],
            needs_healing=data["needs_healing"],
            expected_project_gid=data["expected_project_gid"],
        )
    except Exception:
        # Per FR-DEGRADE-001: Cache lookup failures don't prevent detection
        return None


def _cache_detection_result(
    task: Task,
    result: DetectionResult,
    cache: CacheProvider,
) -> None:
    """Cache a detection result for future lookups.

    Per FR-CACHE-002: Store result after Tier 4 success.
    Per FR-CACHE-005: Only cache non-None Tier 4 results.
    Per FR-CACHE-006: Do not cache UNKNOWN (Tier 5).
    Per FR-DEGRADE-002: Cache storage failures don't prevent detection.

    Args:
        task: The task that was detected.
        result: The DetectionResult to cache.
        cache: Cache provider instance.
    """
    # FR-CACHE-006: Don't cache UNKNOWN results
    if result.entity_type == EntityType.UNKNOWN:
        return

    # Serialize DetectionResult to dict
    data = {
        "entity_type": result.entity_type.value,
        "confidence": result.confidence,
        "tier_used": result.tier_used,
        "needs_healing": result.needs_healing,
        "expected_project_gid": result.expected_project_gid,
    }

    # Per FR-VERSION-001: Use task.modified_at as version when available
    # Per FR-VERSION-002: Fall back to current time if modified_at is None
    version = task.modified_at if task.modified_at else datetime.now(timezone.utc)

    entry = CacheEntry(
        key=task.gid,
        data=data,
        entry_type=EntryType.DETECTION,
        version=version,
        ttl=DETECTION_CACHE_TTL,
    )

    try:
        cache.set(task.gid, entry)
    except Exception:
        # Per FR-DEGRADE-002: Cache storage failures don't prevent detection
        pass
```

#### 3. Updated detect_entity_type_async()

**Location**: `/src/autom8_asana/models/business/detection/facade.py`

```python
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Asynchronous entity type detection (Tiers 1-5).

    Per TDD-DETECTION/FR-DET-008: Async function with optional Tier 4.
    Per TDD-CACHE-PERF-DETECTION: Cache integration around Tier 4.

    Detection order:
    1. Async Tier 1: Project membership with lazy workspace discovery
    2-3. Sync tiers: Name patterns, parent inference (no API)
    4. [CACHE CHECK] - only when allow_structure_inspection=True
    4. Structure inspection (requires API call, disabled by default)
    5. UNKNOWN fallback

    Cache Behavior (per PRD-CACHE-PERF-DETECTION):
    - Cache check occurs ONLY before Tier 4, not at function entry
    - Successful Tier 4 results are cached with task.modified_at version
    - UNKNOWN results are NOT cached (should retry on next call)
    - Cache failures degrade gracefully (detection proceeds normally)

    Args:
        task: Task to detect type for.
        client: AsanaClient for Tier 1 discovery and Tier 4 API calls.
        parent_type: Known parent type for Tier 3 inference.
        allow_structure_inspection: Enable Tier 4 (default: False).

    Returns:
        DetectionResult with detected type and metadata.

    Example:
        >>> # Fast path: async Tier 1 with discovery, then sync tiers
        >>> result = await detect_entity_type_async(task, client)

        >>> # Full detection with structure inspection (uses cache)
        >>> result = await detect_entity_type_async(
        ...     task, client, allow_structure_inspection=True
        ... )
    """
    # Async Tier 1: Project membership with lazy workspace discovery
    # Per ADR-0109: Discovery triggers on first unregistered GID
    async_tier1_result = await _detect_tier1_project_membership_async(task, client)
    if async_tier1_result:
        return async_tier1_result

    # Tiers 2-3 (sync) - Name patterns, parent inference
    result = detect_entity_type(task, parent_type)

    # If we found a type (not UNKNOWN), return it
    if result:
        return result

    # Tier 4: Structure inspection (with cache integration)
    if allow_structure_inspection:
        # Per FR-CACHE-001: Check cache BEFORE Tier 4 API call
        # Per FR-CACHE-003: Cache check occurs AFTER Tiers 1-3
        cache = getattr(client, "_cache_provider", None)

        if cache is not None:
            try:
                cached_result = _get_cached_detection(task.gid, cache)
                if cached_result is not None:
                    # Per FR-OBSERVE-001: Log cache hit
                    logger.info(
                        "detection_cache_hit",
                        extra={
                            "event": "detection_cache_hit",
                            "task_gid": task.gid,
                            "entity_type": cached_result.entity_type.value,
                            "tier_used": cached_result.tier_used,
                        },
                    )
                    return cached_result
                else:
                    # Per FR-OBSERVE-002: Log cache miss
                    logger.debug(
                        "detection_cache_miss",
                        extra={
                            "event": "detection_cache_miss",
                            "task_gid": task.gid,
                        },
                    )
            except Exception as exc:
                # Per FR-DEGRADE-003: Log warning on cache failure
                logger.warning(
                    "detection_cache_check_failed",
                    extra={
                        "event": "detection_cache_check_failed",
                        "task_gid": task.gid,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )

        # Execute Tier 4 API call
        tier4_result = await detect_by_structure_inspection(task, client)

        if tier4_result is not None:
            # Per FR-CACHE-002: Cache successful Tier 4 result
            if cache is not None:
                try:
                    _cache_detection_result(task, tier4_result, cache)
                    # Per FR-OBSERVE-003: Log cache store
                    logger.info(
                        "detection_cache_store",
                        extra={
                            "event": "detection_cache_store",
                            "task_gid": task.gid,
                            "entity_type": tier4_result.entity_type.value,
                        },
                    )
                except Exception as exc:
                    # Per FR-DEGRADE-003: Log warning on cache failure
                    logger.warning(
                        "detection_cache_store_failed",
                        extra={
                            "event": "detection_cache_store_failed",
                            "task_gid": task.gid,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
            return tier4_result

    # Tier 5: Unknown (already returned by detect_entity_type)
    return result
```

#### 4. SaveSession Invalidation Update

**Location**: `/src/autom8_asana/persistence/session.py`

Update `_invalidate_cache_for_results()` to include `EntryType.DETECTION`:

```python
async def _invalidate_cache_for_results(
    self,
    crud_result: SaveResult,
    action_results: list[ActionResult],
) -> None:
    """Invalidate cache entries for successfully mutated entities.

    Per FR-INVALIDATE-001: Invalidates EntryType.DETECTION alongside TASK and SUBTASKS.
    Per FR-INVALIDATE-002: All mutation types (CREATE, UPDATE, DELETE).
    Per FR-INVALIDATE-003: Action operations invalidate detection cache.
    Per FR-INVALIDATE-004: Invalidation failures don't prevent commit.
    """
    cache = getattr(self._client, "_cache_provider", None)
    if cache is None:
        return

    from autom8_asana.cache.entry import EntryType
    from autom8_asana.cache.dataframes import invalidate_task_dataframes

    gids_to_invalidate: set[str] = set()

    # Collect GIDs from CRUD operations
    for entity in crud_result.succeeded:
        if hasattr(entity, "gid") and entity.gid:
            gids_to_invalidate.add(entity.gid)

    # Collect GIDs from action operations
    for action_result in action_results:
        if action_result.success and action_result.action.task:
            if hasattr(action_result.action.task, "gid"):
                gids_to_invalidate.add(action_result.action.task.gid)

    # Per FR-INVALIDATE-001: Invalidate TASK, SUBTASKS, and DETECTION
    for gid in gids_to_invalidate:
        try:
            cache.invalidate(gid, [
                EntryType.TASK,
                EntryType.SUBTASKS,
                EntryType.DETECTION,  # NEW: Per PRD-CACHE-PERF-DETECTION
            ])
        except Exception as exc:
            # Per FR-INVALIDATE-004: Log and continue
            if self._log:
                self._log.warning(
                    "cache_invalidation_failed",
                    gid=gid,
                    error=str(exc),
                )

    # ... existing DataFrame invalidation logic ...
```

---

### Data Model

#### CacheEntry Structure for Detection

Per existing `CacheEntry` dataclass (no changes to structure):

```python
@dataclass(frozen=True)
class CacheEntry:
    key: str                    # task_gid
    data: dict[str, Any]        # Serialized DetectionResult
    entry_type: EntryType       # EntryType.DETECTION
    version: datetime           # task.modified_at or current time
    cached_at: datetime         # When cached
    ttl: int | None = 300       # 5 minutes default (FR-VERSION-003)
    project_gid: str | None     # None for detection (not project-scoped)
    metadata: dict[str, Any]    # Optional metadata
```

#### Serialized DetectionResult Format

```json
{
  "entity_type": "business",
  "confidence": 0.9,
  "tier_used": 4,
  "needs_healing": true,
  "expected_project_gid": "1234567890"
}
```

Per FR-ENTRY-003: All 5 DetectionResult fields are preserved.

---

### API Contracts

#### Existing API (Unchanged)

```python
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult
```

Per NFR-COMPAT-001: Function signature unchanged.

#### Internal Helpers (New)

```python
def _get_cached_detection(
    task_gid: str,
    cache: CacheProvider,
) -> DetectionResult | None

def _cache_detection_result(
    task: Task,
    result: DetectionResult,
    cache: CacheProvider,
) -> None
```

---

### Data Flow

#### Sequence Diagram: Cache Miss (Cold Detection)

```
Consumer                   facade.py              TasksClient        Cache
   |                          |                       |                |
   |--detect_entity_type_async(task, client, allow_structure_inspection=True)
   |                          |                       |                |
   |                          |--Tier 1 (async)------>|                |
   |                          |<--None----------------|                |
   |                          |                       |                |
   |                          |--Tiers 2-3 (sync)--->|                |
   |                          |<--None (UNKNOWN)-----|                |
   |                          |                       |                |
   |                          |--_get_cached_detection(gid)---------->|
   |                          |<--None (cache miss)-------------------|
   |                          |                       |                |
   |                          |--detect_by_structure_inspection()     |
   |                          |   |--subtasks_async()-->              |
   |                          |   |<--[subtasks]--------|              |
   |                          |<--DetectionResult-----|                |
   |                          |                       |                |
   |                          |--_cache_detection_result()----------->|
   |                          |                       |                |
   |<--DetectionResult--------|                       |                |
```

#### Sequence Diagram: Cache Hit (Warm Detection)

```
Consumer                   facade.py              Cache
   |                          |                     |
   |--detect_entity_type_async(task, client, allow_structure_inspection=True)
   |                          |                     |
   |                          |--Tier 1 (async)---->|
   |                          |<--None--------------|
   |                          |                     |
   |                          |--Tiers 2-3 (sync)-->|
   |                          |<--None (UNKNOWN)----|
   |                          |                     |
   |                          |--_get_cached_detection(gid)-->|
   |                          |<--DetectionResult (hit)-------|
   |                          |                     |
   |                          | (skip Tier 4 API)   |
   |                          |                     |
   |<--DetectionResult--------|                     |
```

#### Sequence Diagram: Fast Path (Tier 1 Success, No Cache Check)

```
Consumer                   facade.py
   |                          |
   |--detect_entity_type_async(task, client, allow_structure_inspection=True)
   |                          |
   |                          |--Tier 1 (async)---->
   |                          |<--DetectionResult---|
   |                          |
   |                          | (skip cache check)
   |                          | (skip Tier 4)
   |                          |
   |<--DetectionResult--------|
```

Per NFR-LATENCY-004: Zero cache overhead when Tiers 1-3 succeed.

#### Sequence Diagram: Invalidation Flow

```
Consumer              SaveSession              Cache
   |                       |                     |
   |--commit_async()------>|                     |
   |                       | (execute ops)       |
   |                       |                     |
   |                       |--_invalidate_cache_for_results()
   |                       |  for each gid:      |
   |                       |    |--invalidate(gid, [TASK, SUBTASKS, DETECTION])-->|
   |                       |                     |
   |<--SaveResult----------|                     |
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Cache access method | Extract from `client._cache_provider` | No API change; client already passed | ADR-0120 |
| Cache check placement | AFTER Tiers 1-3, BEFORE Tier 4 | Zero overhead on fast path | ADR-0120 |
| Serialization format | `asdict()` with EntityType.value | Simple; all fields JSON-compatible | ADR-0120 |
| Architecture pattern | Inline logic (no coordinator) | Simple case; ~25 lines total | ADR-0120 |
| TTL | 300 seconds | Match task cache TTL | This TDD |
| UNKNOWN caching | Not cached | Should retry on next call | This TDD |

---

## Complexity Assessment

**Level: Script/Module (Low End)**

This is a **Script-level** change that borders on Module:

- Single file modification (facade.py) + enum addition (entry.py)
- ~50 lines of new code
- No new public API
- No new configuration surface
- Follows existing cache patterns exactly

**Justification for Script (not Module)**:

- No multiple consumers of detection cache logic
- No configuration options (TTL is fixed, matches task cache)
- Minimal error handling (graceful degradation only)
- Implementation is contained in existing module

**Why Not Less?**:

- SaveSession invalidation update makes it slightly more than script
- Pattern must be followed for correctness (invalidation required)

---

## Implementation Plan

### Phases

| Phase | Deliverable | Dependencies | Estimate |
|-------|-------------|--------------|----------|
| **1** | `EntryType.DETECTION` + cache helpers | None | 0.5 day |
| **2** | `detect_entity_type_async()` cache integration | Phase 1 | 0.5 day |
| **3** | SaveSession invalidation update | Phase 1 | 0.25 day |
| **4** | Tests and validation | Phase 2, 3 | 0.5 day |

### Phase 1: Cache Infrastructure

1. Add `EntryType.DETECTION = "detection"` to `cache/entry.py`
2. Add `_get_cached_detection()` helper to facade
3. Add `_cache_detection_result()` helper to facade
4. Add `DETECTION_CACHE_TTL = 300` constant

### Phase 2: Detection Integration

1. Update `detect_entity_type_async()` with cache check before Tier 4
2. Add cache store after successful Tier 4
3. Add structured logging for hit/miss/store events
4. Ensure graceful degradation on cache errors

### Phase 3: Invalidation

1. Update `_invalidate_cache_for_results()` to include `EntryType.DETECTION`
2. Verify invalidation covers all mutation paths (CRUD + actions)

### Phase 4: Testing

1. Unit tests for `_get_cached_detection()` and `_cache_detection_result()`
2. Integration test for cache hit scenario
3. Integration test for cache miss scenario
4. Integration test for graceful degradation
5. Integration test for invalidation flow
6. Benchmark test for performance targets

### Migration Strategy

**No migration required**. This is fully backward compatible:

- Function signature unchanged (NFR-COMPAT-001)
- Sync `detect_entity_type()` unchanged (NFR-COMPAT-002)
- Cache integration is automatic when `CacheProvider` configured
- Cache unavailable degrades gracefully to existing behavior

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Stale detection type returned | Medium | Medium | TTL (300s) + explicit invalidation on mutation |
| Cache check overhead on fast path | High | Low | Cache check ONLY before Tier 4, not at entry |
| Serialization failure | Low | Low | DetectionResult uses primitives; tested serialization |
| Versioning without `modified_at` | Medium | Medium | TTL-only fallback; 300s is acceptable |
| SaveSession misses invalidation | Medium | Low | Add to existing invalidation list; tested |

---

## Observability

### Metrics

Exposed via structured logging:

| Metric | Type | Description |
|--------|------|-------------|
| `detection_cache_hit` | Event | Cache hit, Tier 4 skipped |
| `detection_cache_miss` | Event | Cache miss, proceeding to Tier 4 |
| `detection_cache_store` | Event | Result cached after Tier 4 |
| `detection_cache_check_failed` | Warning | Cache lookup error (degraded) |
| `detection_cache_store_failed` | Warning | Cache storage error (degraded) |

### Logging Format

```python
# Cache hit
logger.info(
    "detection_cache_hit",
    extra={
        "event": "detection_cache_hit",
        "task_gid": "12345",
        "entity_type": "business",
        "tier_used": 4,
    },
)

# Cache miss
logger.debug(
    "detection_cache_miss",
    extra={
        "event": "detection_cache_miss",
        "task_gid": "12345",
    },
)

# Cache store
logger.info(
    "detection_cache_store",
    extra={
        "event": "detection_cache_store",
        "task_gid": "12345",
        "entity_type": "business",
    },
)
```

### Alerting

No new alerts for this feature. Existing cache health monitoring sufficient.

---

## Testing Strategy

### Unit Tests

| Test | Description | Requirement |
|------|-------------|-------------|
| `test_entry_type_detection_exists` | EntryType.DETECTION in enum | FR-ENTRY-001 |
| `test_get_cached_detection_hit` | Returns result on cache hit | FR-CACHE-001 |
| `test_get_cached_detection_miss` | Returns None on cache miss | FR-CACHE-001 |
| `test_get_cached_detection_expired` | Returns None on expired entry | FR-VERSION-003 |
| `test_cache_detection_result_stores` | Stores entry with correct key/type | FR-CACHE-002 |
| `test_cache_detection_result_version` | Uses task.modified_at | FR-VERSION-001 |
| `test_cache_detection_result_version_fallback` | Uses current time if no modified_at | FR-VERSION-002 |
| `test_cache_detection_result_skips_unknown` | Does not cache UNKNOWN | FR-CACHE-006 |
| `test_detect_async_cache_check_after_tier3` | Cache check only when Tier 1-3 fail | FR-CACHE-003 |
| `test_detect_async_no_cache_overhead_tier1` | No cache interaction on Tier 1 success | NFR-LATENCY-004 |
| `test_detect_async_cache_error_degrades` | Detection proceeds on cache error | FR-DEGRADE-001 |
| `test_serialization_roundtrip` | All 5 fields preserved | FR-ENTRY-003, NFR-ACCURACY-003 |

### Integration Tests

| Test | Description | Requirement |
|------|-------------|-------------|
| `test_hydration_benefits_from_cache` | Second hydration faster | UC-1 |
| `test_savesession_invalidates_detection` | Commit invalidates detection cache | FR-INVALIDATE-001 |
| `test_action_invalidates_detection` | add_project invalidates detection | FR-INVALIDATE-003 |
| `test_detection_accuracy_preserved` | Cached matches fresh detection | NFR-ACCURACY-001 |

### Performance Tests

| Test | Target | Requirement |
|------|--------|-------------|
| `benchmark_cached_detection` | <5ms | NFR-LATENCY-001 |
| `benchmark_first_detection` | <=210ms | NFR-LATENCY-002 |
| `benchmark_hydration_5_levels_cached` | <50ms | NFR-LATENCY-003 |
| `benchmark_tier1_no_cache_overhead` | 0ms overhead | NFR-LATENCY-004 |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Should detection cache use separate TTL?~~ | Architect | Session 3 | **300s (same as task)** - Consistency |
| ~~Should we add detection metrics to CacheMetrics?~~ | Architect | Session 3 | **Structured logging** - Follows existing pattern |
| ~~How to access cache from facade?~~ | Architect | Session 3 | **Extract from client** - Per ADR-0120 |
| ~~Should we create DetectionCacheCoordinator?~~ | Architect | Session 3 | **No (inline)** - Per ADR-0120 |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Architect | Initial draft |

---

## Appendix A: Requirement Traceability

| PRD Requirement | Design Element |
|-----------------|----------------|
| FR-ENTRY-001 | `EntryType.DETECTION = "detection"` in entry.py |
| FR-ENTRY-002 | Uses existing `CacheProvider.get()`/`set()` |
| FR-ENTRY-003 | Serialization preserves all 5 DetectionResult fields |
| FR-CACHE-001 | `_get_cached_detection()` called before Tier 4 |
| FR-CACHE-002 | `_cache_detection_result()` called after Tier 4 success |
| FR-CACHE-003 | Cache check in `detect_entity_type_async()` after Tiers 1-3 |
| FR-CACHE-004 | Uses `task.gid` as cache key |
| FR-CACHE-005 | Only caches non-None Tier 4 results |
| FR-CACHE-006 | Check for `EntityType.UNKNOWN` before caching |
| FR-VERSION-001 | `CacheEntry.version = task.modified_at` |
| FR-VERSION-002 | Fallback to `datetime.now(timezone.utc)` |
| FR-VERSION-003 | `DETECTION_CACHE_TTL = 300` |
| FR-VERSION-004 | Configurable via `TTLSettings.entry_type_ttls` (future) |
| FR-INVALIDATE-001 | `EntryType.DETECTION` in SaveSession invalidation |
| FR-INVALIDATE-002 | Invalidation for CREATE, UPDATE, DELETE |
| FR-INVALIDATE-003 | Action results included in invalidation collection |
| FR-INVALIDATE-004 | try/except around invalidation, log warning |
| FR-DEGRADE-001 | try/except in `_get_cached_detection()` |
| FR-DEGRADE-002 | try/except in `_cache_detection_result()` |
| FR-DEGRADE-003 | `logger.warning()` on cache failures |
| FR-DEGRADE-004 | `getattr(client, "_cache_provider", None)` handles None |
| FR-OBSERVE-001 | `detection_cache_hit` log event |
| FR-OBSERVE-002 | `detection_cache_miss` log event |
| FR-OBSERVE-003 | `detection_cache_store` log event |

---

## Appendix B: File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `src/autom8_asana/cache/entry.py` | UPDATE | Add `EntryType.DETECTION` |
| `src/autom8_asana/models/business/detection/facade.py` | UPDATE | Add cache helpers, update `detect_entity_type_async()` |
| `src/autom8_asana/persistence/session.py` | UPDATE | Add `EntryType.DETECTION` to invalidation |
| `tests/unit/detection/test_detection_cache.py` | NEW | Unit tests for cache behavior |
| `tests/integration/test_detection_cache_integration.py` | NEW | Integration tests |

---

## Quality Gate Checklist

- [x] Traces to approved PRD (PRD-CACHE-PERF-DETECTION)
- [x] All significant decisions have ADRs (ADR-0120)
- [x] Component responsibilities are clear
- [x] Interfaces are defined
- [x] Complexity level is justified (Script/Module)
- [x] Risks identified with mitigations
- [x] Implementation plan is actionable
