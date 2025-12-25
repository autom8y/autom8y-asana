# Discovery: Detection Result Caching

> **Initiative**: PROMPT-0-CACHE-PERF-DETECTION (P2 of Cache Performance Meta-Initiative)
> **Session**: 1 - Discovery
> **Agent**: Requirements Analyst (via Orchestrator)
> **Date**: 2025-12-23

---

## Executive Summary

This discovery analyzes the detection system's Tier 4 (structure inspection) API calls to identify caching opportunities. The investigation confirms that caching `DetectionResult` after Tier 4 execution will eliminate redundant subtask fetches during hydration operations, with estimated savings of 100-200ms per cached hit.

**Key Finding**: Tier 4 detection is called in exactly 2 code paths, both in `hydration.py`, both with `allow_structure_inspection=True`. These are the only paths that make API calls for detection.

---

## 1. Detection Call Site Analysis

### 1.1 Call Site Map

| Location | Function | Sync/Async | Tier 4 Enabled | API Calls |
|----------|----------|------------|----------------|-----------|
| `hydration.py:318-319` | `hydrate_from_gid_async()` | Async | **Yes** | Subtask fetch |
| `hydration.py:702-704` | `_traverse_upward_async()` | Async | **Yes** | Subtask fetch per level |
| `clients/tasks.py:203-208` | `_detect_entity_type()` | Sync | No | None |
| `dataframes/builders/task_cache.py:417-421` | `_detect_entity_type()` | Sync | No | None |
| `detection/facade.py:356` | `identify_holder_type()` | Sync | No | None |

### 1.2 Code Analysis: Tier 4 Invocations

**hydration.py:318-319** (Entry point detection):
```python
detection_result = await detect_entity_type_async(
    entry_task, client, allow_structure_inspection=True
)
```

**hydration.py:702-704** (Upward traversal detection):
```python
detection_result = await detect_entity_type_async(
    parent_task, client, allow_structure_inspection=True
)
```

### 1.3 Call Frequency Analysis

| Scenario | Detection Calls | Tier 4 Calls (Worst Case) |
|----------|-----------------|---------------------------|
| Hydrate from Business | 1 | 1 (if Tiers 1-3 fail) |
| Hydrate from Contact | 3 | 3 (entry + 2 parents) |
| Hydrate from Offer | 5 | 5 (entry + 4 parents) |
| Hydrate from Process | 5 | 5 (entry + 4 parents) |
| DataFrame extraction (1000 tasks) | 1000 | 0-1000 (depends on tier success) |

**Critical Insight**: Hydration calls `detect_entity_type_async()` for EVERY parent in the traversal path. If Tier 4 is needed, each parent requires a separate subtask fetch (~200ms each).

---

## 2. Tier 4 Implementation Analysis

### 2.1 Current Implementation

**File**: `src/autom8_asana/models/business/detection/tier4.py`

```python
async def detect_by_structure_inspection(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Tier 4: Detect entity type by subtask structure inspection."""
    # Fetch subtasks to examine structure - THIS IS THE API CALL
    subtasks = await client.tasks.subtasks_async(task.gid).collect()
    subtask_names = {s.name.lower() for s in subtasks if s.name}

    # Check for Business indicators: {"contacts", "units", "location"}
    if subtask_names & BUSINESS_INDICATORS:
        return DetectionResult(
            entity_type=EntityType.BUSINESS,
            confidence=CONFIDENCE_TIER_4,  # 0.9
            tier_used=4,
            needs_healing=True,
            expected_project_gid=expected_gid,
        )

    # Check for Unit indicators: {"offers", "processes"}
    if subtask_names & UNIT_INDICATORS:
        return DetectionResult(...)

    return None  # No match
```

### 2.2 What Tier 4 Returns

| Detection | entity_type | confidence | tier_used | needs_healing | expected_project_gid |
|-----------|-------------|------------|-----------|---------------|---------------------|
| Business found | BUSINESS | 0.9 | 4 | True | From registry |
| Unit found | UNIT | 0.9 | 4 | True | From registry |
| No match | None | - | - | - | - |

### 2.3 Tier 4 Cost

| Metric | Value |
|--------|-------|
| API Call | `GET /tasks/{gid}/subtasks` |
| Latency | ~200ms |
| Rate Limit Impact | 1 request per detection |

---

## 3. Cache Integration Design

### 3.1 What to Cache

**Decision**: Cache the full `DetectionResult` dataclass.

**Rationale**:
- `DetectionResult` is a frozen dataclass (immutable, hashable)
- All 5 fields are simple types (EntityType enum, float, int, bool, str|None)
- Full result preserves `tier_used`, `confidence`, and `needs_healing` for observability
- No serialization complexity - use `dataclasses.asdict()` and reconstruct

```python
@dataclass(frozen=True, slots=True)
class DetectionResult:
    entity_type: EntityType      # Enum -> string for cache
    confidence: float            # JSON-serializable
    tier_used: int               # JSON-serializable
    needs_healing: bool          # JSON-serializable
    expected_project_gid: str | None  # JSON-serializable
```

### 3.2 Cache Integration Point

**Location**: `detect_entity_type_async()` in `facade.py`, specifically around line 309-311.

**Current Flow**:
```python
async def detect_entity_type_async(..., allow_structure_inspection=False):
    # Tier 1: Async project membership
    result = await _detect_tier1_project_membership_async(task, client)
    if result: return result

    # Tiers 2-3: Sync (no API)
    result = detect_entity_type(task, parent_type)
    if result: return result

    # Tier 4: Structure inspection (THE API CALL)
    if allow_structure_inspection:
        tier4_result = await detect_by_structure_inspection(task, client)  # <-- Cache here
        if tier4_result:
            return tier4_result

    return result  # UNKNOWN
```

**Proposed Flow**:
```python
async def detect_entity_type_async(..., allow_structure_inspection=False):
    # Tiers 1-3 (unchanged - they're fast)
    ...

    # Tier 4: Check cache BEFORE API call
    if allow_structure_inspection:
        cached_result = await _check_detection_cache(task.gid, client)
        if cached_result:
            return cached_result

        tier4_result = await detect_by_structure_inspection(task, client)
        if tier4_result:
            await _store_detection_cache(task.gid, tier4_result, task.modified_at, client)
            return tier4_result

    return result
```

### 3.3 Why Cache Only Tier 4?

| Tier | Cost | Should Cache? | Rationale |
|------|------|---------------|-----------|
| 1 | O(1) registry lookup | No | Already fast, registry is in-memory |
| 2 | String pattern match | No | O(1), no benefit from caching |
| 3 | Parent type inference | No | O(1), logic only |
| 4 | API call (~200ms) | **Yes** | Expensive, deterministic, repeatable |
| 5 | UNKNOWN fallback | No | No computation, just a fallback value |

---

## 4. Cache Key and Versioning Strategy

### 4.1 Cache Key Structure

**Format**: `{task_gid}` with `EntryType.DETECTION`

**Rationale**:
- Matches existing pattern: `EntryType.TASK`, `EntryType.SUBTASKS` use task GID as key
- Detection result is per-task, not per-project context
- Simple, predictable key structure

**Entry Type Addition**:
```python
class EntryType(str, Enum):
    TASK = "task"
    SUBTASKS = "subtasks"
    ...
    DETECTION = "detection"  # NEW
```

### 4.2 Versioning Strategy

**Challenge**: When detection is called, we may not have `task.modified_at`.

**Solution**: Use Task object's `modified_at` if available, otherwise use TTL-only expiration.

```python
def _get_detection_version(task: Task) -> datetime:
    """Get version for detection cache entry."""
    if task.modified_at:
        return task.modified_at
    # Fallback: Use current time (TTL becomes primary expiration)
    return datetime.now(timezone.utc)
```

**TTL Configuration**:
- Default: 300s (matches task cache TTL)
- Configurable via `TTLSettings.entry_type_ttls["detection"]`

### 4.3 Versioning Edge Cases

| Scenario | Task.modified_at | Versioning Behavior |
|----------|------------------|---------------------|
| Full task fetched | Available | Use modified_at for staleness |
| Partial task (detection fields only) | May be None | TTL-only expiration |
| Task mutated | Updated | Stale cache, re-detect on miss |

---

## 5. Invalidation Analysis

### 5.1 Existing Invalidation Infrastructure

**Location**: `SaveSession._invalidate_cache_for_results()` (session.py:1452-1554)

**Current Behavior**:
```python
# Invalidate TASK and SUBTASKS for all mutated GIDs
for gid in gids_to_invalidate:
    cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS])
```

**Required Change**: Add `EntryType.DETECTION` to invalidation list:
```python
cache.invalidate(gid, [EntryType.TASK, EntryType.SUBTASKS, EntryType.DETECTION])
```

### 5.2 What Mutations Affect Detection?

| Mutation | Affects Tier | Impact on Detection |
|----------|--------------|---------------------|
| Task name change | Tier 2 | Holder name pattern match may change |
| Task project change | Tier 1 | Registry lookup result changes |
| Task parent change | Tier 3 | Parent inference changes |
| Subtask add/remove | Tier 4 | Structure inspection result changes |

**Decision**: Invalidate detection cache on ANY task mutation.

**Rationale**:
- Simple and safe - no missed invalidations
- Cost is low (detection happens infrequently relative to mutations)
- Matches P1 (Fetch Path) approach: "invalidate task, subtasks, detection"

### 5.3 Cascade Invalidation

**Question**: If parent changes, should children's detection be invalidated?

**Answer**: No cascade needed.

**Rationale**:
- Detection is per-task, based on that task's properties
- Parent type inference (Tier 3) is passed as a parameter, not cached
- If parent detection changes, the caller will pass new `parent_type`

---

## 6. Performance Impact Estimate

### 6.1 Current Cost (No Caching)

| Scenario | Tier 4 Calls | API Latency | Total |
|----------|--------------|-------------|-------|
| Hydrate from Business | 1 | 200ms | 200ms |
| Hydrate from Process | 5 | 200ms each | 1000ms |
| 1000 task extraction (worst case) | 1000 | 200ms each | 200s |

### 6.2 With Detection Caching

| Scenario | Cache Hits | Cache Misses | Total |
|----------|------------|--------------|-------|
| Hydrate from Business (first) | 0 | 1 | 200ms |
| Hydrate from Business (repeat) | 1 | 0 | <5ms |
| Hydrate from Process (first) | 0 | 5 | 1000ms |
| Hydrate from Process (repeat) | 5 | 0 | <25ms |
| 1000 task extraction (warm cache) | ~900 | ~100 | ~20s |

### 6.3 Expected Savings

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Repeat detection (same GID) | 200ms | <5ms | **40x faster** |
| Hydration traversal (cached) | 1000ms | <25ms | **40x faster** |
| 1000 task extraction (warm) | 200s | ~25s | **8x faster** |

---

## 7. Open Questions Resolved

| Question | Resolution | Confidence |
|----------|------------|------------|
| What to cache? | Full DetectionResult | High |
| Cache key structure? | `{task_gid}` + EntryType.DETECTION | High |
| Where to inject cache? | In facade, around Tier 4 call | High |
| Should Tiers 1-3 check cache? | No - they're O(1) | High |
| Cache UNKNOWN results? | No - let it retry | High |
| Versioning without modified_at? | TTL-only fallback | Medium |
| What mutations invalidate? | ALL task mutations | High |
| Cascade invalidation? | Not needed | High |
| TTL vs explicit invalidation? | Both - TTL primary, explicit on mutation | High |

---

## 8. Implementation Scope

### 8.1 Files to Modify

| File | Changes |
|------|---------|
| `cache/entry.py` | Add `EntryType.DETECTION` |
| `detection/facade.py` | Add cache check/store around Tier 4 |
| `persistence/session.py` | Add DETECTION to invalidation list |
| `cache/settings.py` | Optional: Add detection TTL config |

### 8.2 New Files

| File | Purpose |
|------|---------|
| `detection/cache.py` | Detection cache coordinator (optional - may inline) |

### 8.3 Test Files

| File | Purpose |
|------|---------|
| `tests/unit/detection/test_detection_cache.py` | Unit tests for cache behavior |
| `tests/integration/test_detection_cache_integration.py` | Integration with hydration |

---

## 9. Patterns from P1 (Fetch Path) to Apply

| Pattern | P1 Implementation | P2 Application |
|---------|-------------------|----------------|
| Two-phase cache | Enumerate -> lookup -> fetch -> populate | Check cache -> execute tier 4 -> store |
| Graceful degradation | try/except with WARNING log | Same - never block detection |
| Structured observability | Log hits, misses, hit_rate | Log detection cache hits/misses |
| Coordinator class | `BatchCacheCoordinator` | Optional: `DetectionCacheCoordinator` |

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Stale detection type | Medium | TTL (300s) + explicit invalidation |
| Cache unavailable | Low | Graceful degradation - proceed without cache |
| Serialization failure | Low | DetectionResult is simple dataclass |
| Versioning without modified_at | Medium | TTL-only expiration as fallback |

---

## 11. Recommendation

**Proceed to Session 2 (Requirements)** with the following confirmed decisions:

1. **Cache full DetectionResult** - immutable, serializable, preserves observability
2. **Cache only Tier 4** - Tiers 1-3 are O(1), no benefit
3. **Key: `{task_gid}` + EntryType.DETECTION** - matches existing patterns
4. **Invalidate on any mutation** - simple, safe, low cost
5. **TTL: 300s** - matches task cache for consistency
6. **Graceful degradation** - cache failure never blocks detection

---

## References

- [PROMPT-0-CACHE-PERF-DETECTION.md](/docs/initiatives/PROMPT-0-CACHE-PERF-DETECTION.md)
- [PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md](/docs/initiatives/PROMPT-MINUS-1-CACHE-PERFORMANCE-META.md)
- [DISCOVERY-CACHE-PERF-FETCH-PATH.md](/docs/analysis/DISCOVERY-CACHE-PERF-FETCH-PATH.md)
- [TDD-DETECTION.md](/docs/design/TDD-DETECTION.md)
- [ADR-0125-savesession-invalidation.md](/docs/decisions/ADR-0125-savesession-invalidation.md)
