# ADR-0023: Detection Package Structure and Caching

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: SDK Team
- **Consolidated From**: ADR-0142, ADR-0143
- **Related**: [reference/DETECTION.md](reference/DETECTION.md), ADR-0020, TDD-SPRINT-3-DETECTION-DECOMPOSITION

## Context

The detection system originally existed as a single `detection.py` file that grew to **1125 lines** containing 4 distinct concerns:

1. Type definitions (EntityType enum, DetectionResult dataclass) - ~170 lines
2. Configuration data (ENTITY_TYPE_INFO, NAME_PATTERNS, mappings) - ~230 lines
3. Detection logic across 5 tiers (22 functions) - ~600 lines
4. Helper utilities - ~125 lines

This violated the Single Responsibility Principle and created maintenance challenges:
- **Cognitive load**: Engineers must navigate 1100+ lines to modify tier-specific logic
- **Merge conflicts**: Multiple engineers touching the same file
- **Test coupling**: 2300+ lines of tests import from one monolith module
- **Onboarding friction**: New team members must understand entire file to modify any part

The SDK has a **250-line soft limit** per module. `detection.py` exceeded this by 4.5x.

Additionally, Tier 4 structure inspection adds **~200ms latency** per detection and compounds during hydration operations that traverse multiple hierarchy levels. Repeated detection for the same task wastes this expensive operation.

## Decision

We will convert `detection.py` from a single file to a **package directory** with **7 focused modules** and integrate **inline caching** for Tier 4 results.

### Package Structure

```
src/autom8_asana/models/business/
    detection/                    # Package (replaces detection.py)
        __init__.py               # Re-exports for backward compatibility (~50 lines)
        types.py                  # Types and constants (~170 lines)
        config.py                 # Configuration data (~230 lines)
        tier1.py                  # Project membership detection (~180 lines)
        tier2.py                  # Name pattern detection (~150 lines)
        tier3.py                  # Parent inference detection (~60 lines)
        tier4.py                  # Structure inspection detection (~80 lines)
        facade.py                 # Unified detection orchestration (~200 lines)
```

### Module Dependency Graph (Strict Layering)

```
                ┌───────────┐
                │  types.py │  (no dependencies - pure types)
                └─────┬─────┘
                      │
                ┌─────┴─────┐
                │ config.py │  (imports types.py only)
                └─────┬─────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
┌─────┴─────┐   ┌────┴────┐   ┌─────┴─────┐
│  tier1.py │   │tier2.py │   │  tier3.py │
└─────┬─────┘   └────┬────┘   └─────┬─────┘
      │              │              │
      │         ┌────┴────┐         │
      │         │tier4.py │         │
      │         └────┬────┘         │
      │              │              │
      └──────────────┼──────────────┘
                     │
               ┌─────┴─────┐
               │ facade.py │  (imports all tiers)
               └─────┬─────┘
                     │
               ┌─────┴─────┐
               │__init__.py│  (re-exports all public symbols)
               └───────────┘
```

### Module Responsibilities

**types.py** (~170 lines):
- `EntityType` enum (all entity type values)
- `DetectionResult` dataclass (frozen, with __bool__)
- Confidence constants (CONFIDENCE_TIER_1 through CONFIDENCE_TIER_5)
- No dependencies - pure type definitions

**config.py** (~230 lines):
- `ENTITY_TYPE_INFO` master dictionary
- `NAME_PATTERNS` for Tier 2 matching
- `HOLDER_NAME_MAP` for holder detection
- `PARENT_CHILD_MAP` for Tier 3 inference
- Derived maps and configuration
- Imports: `types.py` only

**tier1.py** (~180 lines):
- `_detect_by_project()` - sync project membership detection
- `_detect_tier1_project_membership_async()` - async variant with discovery
- `ProjectTypeRegistry` integration
- `WorkspaceProjectRegistry` lazy discovery
- Imports: `types`, `config`

**tier2.py** (~150 lines):
- `_detect_by_name_pattern()` - name pattern matching
- `_compile_pattern()` - cached regex compilation
- `_matches_pattern()` - word boundary matching
- `_strip_decorations()` - decoration removal
- `PatternSpec` configuration handling
- Imports: `types`, `config`

**tier3.py** (~60 lines):
- `_detect_by_parent()` - parent-child inference
- `_disambiguate_by_name()` - name-based disambiguation
- `PARENT_CHILD_MAP` usage
- Imports: `types`, `config`

**tier4.py** (~80 lines):
- `detect_by_structure_inspection()` - async structure inspection
- Subtask fetching and analysis
- Business/Unit indicator detection
- Imports: `types`, `config`, `AsanaClient`

**facade.py** (~200 lines):
- `detect_entity_type()` - synchronous orchestration (Tiers 1-3)
- `detect_entity_type_async()` - async orchestration (Tiers 1-5)
- Cache integration (inline before Tier 4)
- Tier coordination and result aggregation
- Imports: All tier modules

**__init__.py** (~50 lines):
- Re-exports all public symbols from modules
- Maintains backward compatibility
- Preserves `__all__` from original module

### Re-export Strategy

```python
# detection/__init__.py
from autom8_asana.models.business.detection.types import (
    EntityType,
    DetectionResult,
    CONFIDENCE_TIER_1,
    CONFIDENCE_TIER_2,
    CONFIDENCE_TIER_3,
    CONFIDENCE_TIER_4,
    CONFIDENCE_TIER_5,
)
from autom8_asana.models.business.detection.config import (
    ENTITY_TYPE_INFO,
    NAME_PATTERNS,
    HOLDER_NAME_MAP,
    PARENT_CHILD_MAP,
    get_holder_attr,
    entity_type_to_holder_attr,
)
from autom8_asana.models.business.detection.facade import (
    detect_entity_type,
    detect_entity_type_async,
)
# ... remaining imports ...

__all__ = [
    # All 22 original exports + 5 private functions for test compatibility
]
```

**Backward compatibility guarantee**:
- `from autom8_asana.models.business.detection import EntityType` continues to work
- No changes required to any import statements in the codebase
- Python's package import system handles file-to-directory migration transparently

### Detection Result Caching

Integrate caching **inline** within `detect_entity_type_async()`:

**Cache check placement**: AFTER Tiers 1-3, BEFORE Tier 4 execution (no fast-path overhead)

**Cache access**: Extract `cache_provider` from the `client` parameter (no new parameters)

**Serialization**: Use `dataclasses.asdict()` with enum string conversion

```python
# In facade.py
async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Async detection with Tier 4 caching.

    Per ADR-0023: Cache integrated inline before Tier 4.
    """
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
                    logger.debug(
                        "detection_cache_hit",
                        task_gid=task.gid,
                        entity_type=cached.entity_type.value,
                    )
                    return cached
            except Exception as exc:
                logger.warning(
                    "detection_cache_check_failed",
                    task_gid=task.gid,
                    error=str(exc),
                )

        tier4_result = await detect_by_structure_inspection(task, client)
        if tier4_result:
            # Cache successful Tier 4 result
            if cache:
                try:
                    _cache_detection_result(task, tier4_result, cache)
                    logger.debug(
                        "detection_cache_store",
                        task_gid=task.gid,
                        entity_type=tier4_result.entity_type.value,
                    )
                except Exception as exc:
                    logger.warning(
                        "detection_cache_store_failed",
                        task_gid=task.gid,
                        error=str(exc),
                    )
            return tier4_result

    # Tier 5: Unknown fallback
    return _make_unknown_result(task)
```

### Cache Helpers

```python
def _get_cached_detection(task_gid: str, cache: CacheProvider) -> DetectionResult | None:
    """Retrieve cached detection result."""
    entry = cache.get(task_gid, entry_type=EntryType.DETECTION)
    if entry is None:
        return None

    # Deserialize from dict
    data = entry.data
    return DetectionResult(
        entity_type=EntityType(data["entity_type"]),
        confidence=data["confidence"],
        tier_used=data["tier_used"],
        needs_healing=data["needs_healing"],
        expected_project_gid=data["expected_project_gid"],
    )


def _cache_detection_result(
    task: Task,
    result: DetectionResult,
    cache: CacheProvider,
) -> None:
    """Store detection result in cache."""
    # Serialize to dict
    data = {
        "entity_type": result.entity_type.value,  # Enum -> string
        "confidence": result.confidence,
        "tier_used": result.tier_used,
        "needs_healing": result.needs_healing,
        "expected_project_gid": result.expected_project_gid,
    }

    cache.set(
        task.gid,
        data,
        entry_type=EntryType.DETECTION,
        ttl=300,  # 5 minutes
        metadata={"task_name": task.name},
    )
```

### Cache Invalidation

Detection cache is invalidated when entity structure may have changed:

```python
# In SaveSession after commit
if auto_heal and result.healed_entities:
    # Invalidate detection cache for healed entities
    for entity_gid in result.healed_entities:
        cache.invalidate(entity_gid, entry_type=EntryType.DETECTION)
```

## Rationale

### Why Package Over Single File?

| Criterion | Single File | Package |
|-----------|-------------|---------|
| Cognitive load | Must read 1100+ lines | Open only relevant module (60-230 lines) |
| Merge conflicts | High probability | Low - separate files per concern |
| Testing isolation | All tests touch one module | Tier-specific tests possible |
| Navigation | Scroll to find functions | File name = function category |
| Maintenance | Any change touches 1 file | Changes scoped to concern |
| SRP compliance | Violated (4 concerns) | Each module single responsibility |

### Why These Module Boundaries?

Boundaries follow natural structure already present in code:

1. **Types have zero dependencies** - pure definitions belong together
2. **Configuration depends only on types** - natural second layer
3. **Each tier is logically independent** - distinct responsibilities:
   - Tier 1: Registry lookup (sync + async variants)
   - Tier 2: String pattern matching (word boundaries, stripping)
   - Tier 3: Parent-child inference (PARENT_CHILD_MAP)
   - Tier 4: Async structure inspection (API call)
4. **Facade orchestrates tiers** - natural aggregation point

### Why Cache Check AFTER Tiers 1-3?

```
Current Flow (No Cache):
  detect_entity_type_async()
    → Tier 1: Project membership (O(1))
    → Tier 2-3: Name patterns, parent inference (O(1))
    → Tier 4: Subtask fetch (~200ms)
    → Tier 5: UNKNOWN

With Cache Check at Entry:
  detect_entity_type_async()
    → Cache check (~1ms) <-- ADDED OVERHEAD
    → Tier 1-3: (O(1))
    → Tier 4: (only if cache miss)

With Cache Check Before Tier 4:
  detect_entity_type_async()
    → Tier 1-3: (O(1)) <-- NO OVERHEAD
    → Cache check (~1ms) <-- Only when Tier 4 needed
    → Tier 4: (only if cache miss)
```

**Cache check before Tier 4 is optimal** because:
- Tiers 1-3 succeed for most tasks (registered projects, holder names)
- Adding cache overhead to fast path would regress performance
- Cache is only valuable for Tier 4 (the expensive operation)
- Zero overhead for 80%+ of detection calls

### Why Extract Cache from Client (Not New Parameter)?

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

### Why `asdict()` for Serialization?

| Approach | Pros | Cons |
|----------|------|------|
| **`asdict()`** | Built-in; handles all fields; reversible | Enum becomes string |
| `__dict__` | Simple | Frozen dataclass has no `__dict__` |
| Custom `to_dict()` | Full control | More code to maintain |
| pickle | Preserves types | Binary; security concerns |

**`asdict()`** wins because:
- `DetectionResult` has 5 simple fields
- All field types are JSON-compatible
- Reconstruction is straightforward with enum lookup

### Why Inline Logic (No DetectionCacheCoordinator)?

| Approach | Pros | Cons |
|----------|------|------|
| **Inline in facade** | Simple; contained; ~25 lines | Logic mixed with detection |
| `DetectionCacheCoordinator` | Separation of concerns | Over-engineering for ~25 lines |
| Decorator pattern | Clean separation | Adds indirection; harder to debug |

**Inline logic** wins because:
- Total code is ~25 lines (check + store + try/except)
- Detection caching is simple: single key lookup, single key store
- Coordinator would add boilerplate without meaningful abstraction
- P1 BatchCacheCoordinator justified by complex two-phase operations; detection is simpler

## Alternatives Considered

### Alternative A: Keep Single File with Regions

Add comment regions (`# region Tier 1`) for navigation.

**Why not chosen**:
- Still violates SRP
- Merge conflicts persist
- Cognitive load unchanged
- Doesn't address root cause

### Alternative B: Extract Types Only

Create `detection_types.py`, keep logic in `detection.py`.

**Why not chosen**:
- Main file still 950+ lines
- SRP still violated
- Would need follow-up refactoring

### Alternative C: One File Per Function

Create 22 files, one per function.

**Why not chosen**:
- Over-engineering
- Navigation overhead
- Excessive files
- Tier-based grouping more intuitive

### Alternative D: Cache at Function Entry

Check cache before any tier.

**Why not chosen**:
- Adds ~1ms overhead to every detection call
- Most calls succeed at Tier 1-3 (cache check is wasted)
- Violates performance requirements

### Alternative E: DetectionCacheCoordinator Class

Create dedicated class mirroring P1's BatchCacheCoordinator.

**Why not chosen**:
- Adds ~50 lines for ~25 lines of logic
- Detection is single-key, no batching needed
- Over-engineering for simple use case

## Consequences

### Positive

**Package structure**:
- **Improved maintainability**: Each module has single responsibility
- **Reduced cognitive load**: Engineers work with 60-230 line files, not 1125
- **Better code review**: Changes scoped to concern-specific files
- **Easier onboarding**: Module names indicate purpose
- **Test isolation**: Can test tiers independently
- **Merge conflict reduction**: Parallel work on different tiers possible
- **SRP compliance**: Each module under 250-line soft limit

**Caching**:
- **40x speedup on repeat Tier 4 detection**: 200ms → <5ms
- **No fast-path regression**: Tiers 1-3 unchanged (zero overhead)
- **Minimal code change**: ~25 lines in facade, enum member in entry.py
- **Reuses existing infrastructure**: CacheProvider, CacheEntry, EntryType
- **Graceful degradation**: Cache failures don't block detection

### Negative

**Package structure**:
- **More files**: 7 files instead of 1 (acceptable trade-off for clarity)
- **One-time migration effort**: Must extract carefully to preserve behavior
- **Slightly longer import chains**: Internal imports span files (mitigated by re-exports)

**Caching**:
- **Implicit cache coupling**: Detection facade depends on client having cache
- **Mixed concerns**: Detection logic includes cache logic (mitigated by clear sections)
- **TTL staleness window**: 300s window where cache could be stale (mitigated by invalidation)

### Neutral

- No API changes: all existing imports continue to work
- No behavior changes: pure structural refactoring
- Test updates optional: tests can use new paths in follow-up work
- Testing complexity: tests need to mock client with cache provider
- Observability: new log events (detection_cache_hit, detection_cache_miss)

## Compliance

How do we ensure this decision is followed?

**Package structure**:
1. **All tests must pass after each phase** - CI verification
2. **Import validation succeeds**: `from autom8_asana.models.business.detection import *`
3. **Line count check**: All modules <250 lines (`wc -l detection/*.py`)
4. **Type checking passes**: `mypy src/autom8_asana/models/business/detection/`
5. **No circular imports**: Module imports without error on fresh Python session

**Caching**:
1. **Cache check before Tier 4 only** - verified by code review
2. **Unit tests for cache hit/miss/error paths** - test suite coverage
3. **Integration tests for hydration with cache** - end-to-end verification
4. **Logging for cache operations** - observability requirement
5. **Function docstring updated** - documentation requirement

## Implementation Notes

**Adding new tier logic**:

```python
# Add new tier module: detection/tier6.py
def _detect_by_new_strategy(task: Task) -> DetectionResult | None:
    """Tier 6: New detection strategy."""
    # Implementation
    pass

# Update facade.py to call new tier
result = _detect_by_new_strategy(task)
if result:
    return result
```

**Testing tier in isolation**:

```python
# Test tier2 without facade
from autom8_asana.models.business.detection.tier2 import _detect_by_name_pattern

def test_tier2_word_boundary():
    task = Task(name="Community Center", gid="123")
    result = _detect_by_name_pattern(task)
    assert result is None  # Should NOT match "unit"
```

**Cache performance monitoring**:

```python
# Log cache hit rate
cache_hits = sum(1 for log in logs if log["event"] == "detection_cache_hit")
cache_misses = sum(1 for log in logs if log["event"] == "tier4_executed")
hit_rate = cache_hits / (cache_hits + cache_misses)

# Alert if hit rate < 60% (indicates cache not effective)
```

**Migration checklist**:

- [ ] Create `detection/` package directory
- [ ] Extract `types.py` with all type definitions
- [ ] Extract `config.py` with all configuration data
- [ ] Extract tier modules (tier1.py through tier4.py)
- [ ] Create `facade.py` with orchestration logic
- [ ] Add cache integration to facade
- [ ] Create `__init__.py` with re-exports
- [ ] Add `EntryType.DETECTION` to cache/entry.py
- [ ] Update SaveSession to invalidate detection cache
- [ ] Verify all tests pass unchanged
- [ ] Run mypy and verify no type errors
- [ ] Update documentation references
