# ADR-0120: Detection Result Caching Strategy

## Metadata
- **Status**: Proposed
- **Author**: Architect
- **Date**: 2025-12-23
- **Deciders**: SDK Team
- **Related**: [PRD-CACHE-PERF-DETECTION](/docs/requirements/PRD-CACHE-PERF-DETECTION.md), [TDD-CACHE-PERF-DETECTION](/docs/design/TDD-CACHE-PERF-DETECTION.md), ADR-0094, ADR-0125

## Context

`detect_entity_type_async()` with `allow_structure_inspection=True` makes a Tier 4 API call (subtask fetch via `client.tasks.subtasks_async(task.gid).collect()`) every time it is invoked for the same task. This adds approximately 200ms per detection and compounds during hydration operations that traverse multiple hierarchy levels.

Key observations from discovery:
- Tier 4 is called in exactly 2 code paths, both in `hydration.py`, both with `allow_structure_inspection=True`
- Hydration calls `detect_entity_type_async()` for EVERY parent in the traversal path
- Detection result is deterministic for unchanged tasks (subtask structure is stable)
- Tiers 1-3 are O(1) operations that do not benefit from caching

The SDK already has cache infrastructure (`CacheProvider`, `CacheEntry`, `EntryType`) used by P1 (Fetch Path Caching) and DataFrame caching. We need to integrate detection result caching without slowing down the fast path (Tiers 1-3).

**Key design questions**:
1. How should the detection facade access the cache provider?
2. Where exactly in `detect_entity_type_async()` should cache check/store be injected?
3. How should `DetectionResult` be serialized for caching?
4. Should we create a `DetectionCacheCoordinator` class or inline the logic?

## Decision

We will implement **inline cache integration** within `detect_entity_type_async()` with the following characteristics:

1. **Cache access via client parameter**: Extract `cache_provider` from the `client` parameter already passed to `detect_entity_type_async()`. No new parameters needed.

2. **Cache check placement**: AFTER Tiers 1-3, BEFORE Tier 4 execution. This ensures no overhead for the fast path.

3. **Serialization approach**: Use `dataclasses.asdict()` for serialization and reconstruct `DetectionResult` from dict on cache hit.

4. **Inline logic (no coordinator)**: The cache integration is simple enough (check/store) that a separate coordinator class would be over-engineering.

```python
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    # Tiers 1-3 (unchanged - fast path)
    async_tier1_result = await _detect_tier1_project_membership_async(task, client)
    if async_tier1_result:
        return async_tier1_result

    result = detect_entity_type(task, parent_type)
    if result:
        return result

    # Tier 4 (with cache integration)
    if allow_structure_inspection:
        # Cache check ONLY here - not at function entry
        cache = getattr(client, "_cache_provider", None)
        if cache:
            try:
                cached = _get_cached_detection(task.gid, cache)
                if cached:
                    logger.debug("detection_cache_hit", task_gid=task.gid, entity_type=cached.entity_type.value)
                    return cached
            except Exception as exc:
                logger.warning("detection_cache_check_failed", task_gid=task.gid, error=str(exc))

        tier4_result = await detect_by_structure_inspection(task, client)
        if tier4_result:
            # Cache successful Tier 4 result
            if cache:
                try:
                    _cache_detection_result(task, tier4_result, cache)
                    logger.debug("detection_cache_store", task_gid=task.gid, entity_type=tier4_result.entity_type.value)
                except Exception as exc:
                    logger.warning("detection_cache_store_failed", task_gid=task.gid, error=str(exc))
            return tier4_result

    # Tier 5: Unknown fallback
    return result
```

## Rationale

### Why Extract Cache from Client (vs. New Parameter)?

| Approach | Pros | Cons |
|----------|------|------|
| New `cache_provider` parameter | Explicit dependency | Breaks API; forces all callers to pass cache |
| **Extract from client** | No API change; client already has cache | Implicit coupling |
| Global/singleton cache | Simple access | Hard to test; poor DI |

**Extract from client** wins because:
- `client` is already a required parameter (for Tier 4 API calls)
- Client owns `_cache_provider` (per ADR-0124)
- Zero breaking changes to function signature
- Testing: pass mock client with mock cache

### Why Cache Check AFTER Tiers 1-3?

```
Current Flow (No Cache):
  detect_entity_type_async()
    --> Tier 1: Project membership (O(1))
    --> Tier 2-3: Name patterns, parent inference (O(1))
    --> Tier 4: Subtask fetch (~200ms)
    --> Tier 5: UNKNOWN

With Cache Check at Entry:
  detect_entity_type_async()
    --> Cache check (~1ms) <-- ADDED OVERHEAD
    --> Tier 1-3: (O(1))
    --> Tier 4: (only if cache miss)

With Cache Check Before Tier 4:
  detect_entity_type_async()
    --> Tier 1-3: (O(1)) <-- NO OVERHEAD
    --> Cache check (~1ms) <-- Only when Tier 4 needed
    --> Tier 4: (only if cache miss)
```

**Cache check before Tier 4** is optimal because:
- Tiers 1-3 succeed for most tasks (registered projects, holder names)
- Adding cache overhead to fast path would regress performance (NFR-LATENCY-004)
- Cache is only valuable for Tier 4 (the expensive operation)

### Why `asdict()` for Serialization?

| Approach | Pros | Cons |
|----------|------|------|
| **`asdict()`** | Built-in; handles all fields; reversible | Enum becomes string |
| `__dict__` | Simple | Frozen dataclass has no `__dict__` |
| Custom `to_dict()` | Full control | More code to maintain |
| pickle | Preserves types | Binary; security concerns |

**`asdict()`** wins because:
- `DetectionResult` is a frozen dataclass with 5 simple fields
- All field types are JSON-compatible (EntityType enum -> string, float, int, bool, str|None)
- Reconstruction is straightforward: `DetectionResult(**data)` with enum lookup

```python
def _serialize_detection_result(result: DetectionResult) -> dict:
    data = asdict(result)
    data["entity_type"] = result.entity_type.value  # Ensure string
    return data

def _deserialize_detection_result(data: dict) -> DetectionResult:
    return DetectionResult(
        entity_type=EntityType(data["entity_type"]),
        confidence=data["confidence"],
        tier_used=data["tier_used"],
        needs_healing=data["needs_healing"],
        expected_project_gid=data["expected_project_gid"],
    )
```

### Why Inline Logic (No Coordinator)?

| Approach | Pros | Cons |
|----------|------|------|
| **Inline in facade** | Simple; contained; few lines | Logic mixed with detection |
| `DetectionCacheCoordinator` | Separation of concerns | Over-engineering for ~20 lines |
| Decorator pattern | Clean separation | Adds indirection; harder to debug |

**Inline logic** wins because:
- Total code is ~20-25 lines (check + store + try/except)
- P1 BatchCacheCoordinator justified by complex two-phase enumerate/fetch
- Detection caching is simple: single key lookup, single key store
- Coordinator would add boilerplate without meaningful abstraction

## Alternatives Considered

### Alternative 1: Cache at Function Entry

- **Description**: Check detection cache before any tier:
  ```python
  async def detect_entity_type_async(...):
      cached = _get_cached_detection(task.gid, client._cache_provider)
      if cached:
          return cached
      # Then run tiers...
  ```
- **Pros**:
  - Simple placement
  - Maximum cache utilization
- **Cons**:
  - Adds ~1ms overhead to every detection call
  - Most calls succeed at Tier 1-3 (cache check is wasted)
  - Violates NFR-LATENCY-004 (zero overhead for Tiers 1-3)
- **Why not chosen**: Performance regression on fast path

### Alternative 2: DetectionCacheCoordinator Class

- **Description**: Create dedicated class mirroring P1's BatchCacheCoordinator:
  ```python
  class DetectionCacheCoordinator:
      def __init__(self, cache_provider: CacheProvider | None):
          self._cache = cache_provider

      async def get_or_detect(
          self,
          task: Task,
          client: AsanaClient,
          detect_func: Callable,
      ) -> DetectionResult:
          if self._cache:
              cached = self._lookup(task.gid)
              if cached:
                  return cached
          result = await detect_func(task, client)
          if self._cache and result:
              self._store(task, result)
          return result
  ```
- **Pros**:
  - Follows P1 pattern
  - Testable in isolation
  - Clear separation of caching concern
- **Cons**:
  - Adds ~50 lines for ~20 lines of logic
  - P1 coordinator justified by complex batch operations
  - Detection is single-key, no batching needed
  - Indirection makes debugging harder
- **Why not chosen**: Over-engineering for simple use case

### Alternative 3: Cache Provider Parameter

- **Description**: Add optional `cache_provider` parameter to function:
  ```python
  async def detect_entity_type_async(
      task: Task,
      client: AsanaClient,
      parent_type: EntityType | None = None,
      allow_structure_inspection: bool = False,
      cache_provider: CacheProvider | None = None,  # NEW
  ) -> DetectionResult:
  ```
- **Pros**:
  - Explicit dependency injection
  - Easy to test with mock cache
- **Cons**:
  - Breaking API change (new parameter)
  - All callers must be updated
  - Cache is already available via client
  - Inconsistent with existing SDK patterns
- **Why not chosen**: Unnecessary API change; client already carries cache

### Alternative 4: Cache All Tier Results

- **Description**: Cache results from any tier, not just Tier 4:
  ```python
  async def detect_entity_type_async(...):
      # Check cache first for any cached result
      cached = _get_cached(task.gid)
      if cached:
          return cached

      # Run tiers, cache whatever succeeds
      result = await _run_all_tiers(task, client, ...)
      _cache_result(task.gid, result)
      return result
  ```
- **Pros**:
  - Uniform caching for all paths
  - Second call is always fast
- **Cons**:
  - Tiers 1-3 are already O(1) - no benefit from caching
  - Adds overhead to fast path
  - Cache size increases dramatically
  - Stale risk increases (registry changes, parent type changes)
- **Why not chosen**: Caching O(1) operations adds overhead with no benefit

## Consequences

### Positive

- **40x speedup on repeat Tier 4 detection**: 200ms -> <5ms
- **No fast path regression**: Tiers 1-3 unchanged (NFR-LATENCY-004)
- **Minimal code change**: ~25 lines in facade, enum member in entry.py
- **Reuses existing infrastructure**: CacheProvider, CacheEntry, EntryType
- **Graceful degradation**: Cache failures don't block detection

### Negative

- **Implicit cache coupling**: Detection facade now depends on client having cache
- **Mixed concerns**: Detection logic includes cache logic (mitigated by clear sections)
- **TTL staleness window**: 300s window where cache could be stale (mitigated by explicit invalidation)

### Neutral

- **Testing complexity**: Tests need to mock client with cache provider
- **Observability**: New log events (detection_cache_hit, detection_cache_miss)

## Compliance

How do we ensure this decision is followed?

1. **Code review**: Any changes to detection caching must follow this pattern
2. **Unit tests**: Test cache hit/miss paths with mocked cache
3. **Integration tests**: Test with real cache provider in hydration scenario
4. **Logging**: Structured logging for cache operations enables debugging
5. **Documentation**: Function docstring updated with cache behavior

## Implementation Checklist

- [ ] Add `EntryType.DETECTION` to `cache/entry.py`
- [ ] Add `_get_cached_detection()` helper in facade
- [ ] Add `_cache_detection_result()` helper in facade
- [ ] Add cache check before Tier 4 in `detect_entity_type_async()`
- [ ] Add cache store after Tier 4 success
- [ ] Add `EntryType.DETECTION` to SaveSession invalidation
- [ ] Add unit tests for cache hit/miss/error paths
- [ ] Add integration test for hydration with detection cache
- [ ] Update facade docstring with cache behavior
