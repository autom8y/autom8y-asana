---
type: triage
---

# Remedy Plan: Section Timeline Architecture Remediation

**Agent**: remedy-smith
**Mode**: interactive
**Complexity**: MODULE
**Date**: 2026-02-20
**Upstream artifacts**:
- detection-report: `.wip/DETECTION-section-timeline-remediation-2026-02-20.md`
- analysis-report: `.claude/.wip/ANALYSIS-section-timeline-remediation.md`
- decay-report: `.wip/DECAY-section-timeline-remediation-2026-02-20.md`

**Note on application**: remedy-smith write access is sandboxed to `.wip/`. AUTO patches below are
provided as exact text replacements for a human or CI step to apply. The test command to verify
after applying all AUTO patches is at the bottom of this document.

---

## Finding Inventory

| Finding ID | Source | Severity | Classification | Effort | Status |
|-----------|--------|----------|----------------|--------|--------|
| HH-001 | detection-report | MEDIUM | MANUAL | small | Pending |
| LS-001 | analysis-report | MEDIUM | MANUAL | small | Pending |
| LS-002 | analysis-report | LOW | No fix needed | -- | Informational only |
| LS-003 | analysis-report | MEDIUM | AUTO | trivial | Pending application |
| LS-004 | analysis-report | LOW | MANUAL | small | Pending (same root as HH-001) |
| TQ-001 | analysis-report | MEDIUM | MANUAL | medium | Pending |
| UO-001 | analysis-report | LOW | No fix needed | -- | Follows codebase convention |
| CC-001 | decay-report | TEMPORAL | AUTO | trivial | Pending application |
| CC-002 | decay-report | TEMPORAL | AUTO | trivial | Pending application |
| CC-003 | decay-report | TEMPORAL | AUTO | trivial | Pending application |
| CC-004 | decay-report | TEMPORAL | AUTO | trivial | Pending application |

---

## AUTO Fixes

All five AUTO fixes are comments/docstrings and one logging addition. No logic changes.
Apply them in any order; they do not interact.

---

### RS-001: Add warning log for base CacheEntry discard in get_cached_timelines (AUTO)

**Source**: LS-003 (analysis-report)
**Finding**: `get_cached_timelines` in `derived.py` silently returns `None` when `get_versioned`
returns a valid but non-`DerivedTimelineCacheEntry` object. No log is emitted, so deserialization
regressions are invisible to operators.
**Classification**: AUTO -- adding a warning log is mechanically safe. Control flow is unchanged;
only observability is added.
**Risk**: Negligible. Uses the module-level logger pattern already standard in the codebase.

**File**: `src/autom8_asana/cache/integration/derived.py`

**Change 1 of 2** -- add logger import and instance after the existing imports (after line 23,
before the blank line that precedes `_DERIVED_TIMELINE_TTL`):

```
# BEFORE (lines 8-25 of derived.py):
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8_asana.cache.models.entry import (
    DerivedTimelineCacheEntry,
    EntryType,
)
from autom8_asana.models.business.section_timeline import (
    SectionInterval,
    SectionTimeline,
)

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider


# AFTER:
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.cache.models.entry import (
    DerivedTimelineCacheEntry,
    EntryType,
)
from autom8_asana.models.business.section_timeline import (
    SectionInterval,
    SectionTimeline,
)

if TYPE_CHECKING:
    from autom8_asana.protocols.cache import CacheProvider

logger = get_logger(__name__)
```

**Change 2 of 2** -- replace the silent fallback `return None` at lines 66-67:

```
# BEFORE (lines 63-67 of derived.py):
    # Ensure we return the typed subclass
    if isinstance(entry, DerivedTimelineCacheEntry):
        return entry
    # Fallback: base CacheEntry returned (legacy deserialization)
    return None

# AFTER:
    # Ensure we return the typed subclass
    if isinstance(entry, DerivedTimelineCacheEntry):
        return entry
    # Fallback: base CacheEntry returned (deserialization did not produce typed subclass).
    # This indicates a registry miss or forward-compatibility edge case. Log for observability.
    logger.warning(
        "derived_timeline_cache_type_mismatch",
        extra={
            "key": key,
            "entry_type": type(entry).__name__,
            "expected": "DerivedTimelineCacheEntry",
        },
    )
    return None
```

**Effort**: trivial

---

### RS-002: Fix stale Yields docstring in lifespan.py (AUTO)

**Source**: CC-001 (decay-report)
**Finding**: `lifespan.py:63` Yields clause states "no persistent state stored on app.state for SDK"
but the function body assigns four keys to `app.state`. Directly contradicted in the same function.
**Classification**: AUTO -- provably stale. The replacement text is unambiguous from the existing
function body. No logic change.
**Risk**: Zero. Docstring only.

**File**: `src/autom8_asana/api/lifespan.py`

```
# BEFORE (line 63):
        None (no persistent state stored on app.state for SDK).

# AFTER:
        None (control returned to request handlers; startup state on app.state
        includes cache_provider, client_pool, entity_write_registry,
        cache_warming_task).
```

**Effort**: trivial

---

### RS-003: Fix stale warm-up task reference in lifespan.py comment (AUTO)

**Source**: CC-002 (decay-report)
**Finding**: `lifespan.py:119-120` comment credits `cache_provider` sharing to "the timeline
warm-up task", which was deleted in commit `8b5813e`. The sharing rationale is still correct;
only the stated beneficiary is a ghost.
**Classification**: AUTO -- provably stale (warm-up task confirmed absent by exhaustive grep).
**Risk**: Zero. Comment only.

**File**: `src/autom8_asana/api/lifespan.py`

```
# BEFORE (lines 119-120):
    # DEF-005: pass shared cache_provider so pooled clients share the same
    # cache backend as the timeline warm-up task.

# AFTER:
    # DEF-005: pass shared cache_provider so pooled clients share the same
    # cache backend as the shared request-handler pool.
```

**Effort**: trivial

---

### RS-004: Fix stale warm-up rationale comment in build_timeline_for_offer (AUTO)

**Source**: CC-003 (decay-report)
**Finding**: `section_timeline_service.py:291-295` comment justifies `max_cache_age_seconds=7200`
in terms of the deleted warm-up pipeline ("populated during warm-up (runs every ~12 min on ECS
restart)"). The 7200s value itself is correct; only the warm-up rationale is stale.
**Classification**: AUTO -- warm-up pipeline is provably deleted. Replacing with staleness-tolerance
framing requires no judgment about whether 7200s is the right value.
**Risk**: Low. Comment only. The `max_cache_age_seconds=7200` argument is untouched.

**File**: `src/autom8_asana/services/section_timeline_service.py`

```
# BEFORE (lines 291-295):
    # FR-1: Fetch stories via cached client.
    # max_cache_age_seconds=7200: If the story cache was populated during
    # warm-up (runs every ~12 min on ECS restart), skip the Asana API
    # refresh entirely.  Stories fetched within the last 2 hours are current
    # enough for historical day-counting.

# AFTER:
    # Fetch stories via cached client.
    # max_cache_age_seconds=7200: Stories cached within the last 2 hours are
    # current enough for historical day-counting. Skips the Asana API refresh
    # for recently-cached entries.
```

**Effort**: trivial

---

### RS-005: Strip inline requirement tags (FR-N, AC-N, EC-N, NFR-N) from source (AUTO)

**Source**: CC-004 (decay-report)
**Finding**: Initiative-era acceptance-criteria tags appear as inline comments in two source files.
The feature has shipped; tags reference ephemeral `.claude/wip/` planning documents. Code is
self-documenting without them.
**Classification**: AUTO -- ephemeral comment stripping. All substantive text after the tag prefix
is preserved. No logic change.
**Risk**: Negligible. Comments only.

**File 1**: `src/autom8_asana/services/section_timeline_service.py`

```
# BEFORE (lines 276-278, inside build_timeline_for_offer docstring):
    Per FR-1: Fetch and filter stories.
    Per FR-2: Walk chronologically to produce intervals.
    Per FR-3: Handle never-moved tasks via imputation.

# AFTER:
    Fetch and filter stories.
    Walk chronologically to produce intervals.
    Handle never-moved tasks via imputation.
```

```
# BEFORE (line 302):
    # AC-1.2: Filter to section_changed only

# AFTER:
    # Filter to section_changed only
```

```
# BEFORE (line 305):
    # AC-1.3, AC-1.4: Filter cross-project noise

# AFTER:
    # Filter cross-project noise
```

```
# BEFORE (line 310):
    # Sort by created_at ascending (AC-2.5)

# AFTER:
    # Sort by created_at ascending
```

```
# BEFORE (line 313):
    # FR-2: Build intervals from filtered stories

# AFTER:
    # Build intervals from filtered stories
```

```
# BEFORE (line 318):
    # FR-3: Handle never-moved task

# AFTER:
    # Handle never-moved task
```

```
# BEFORE (line 504):
                # EC-6: Entity with zero cached stories.

# AFTER:
                # Entity with zero cached stories.
```

**File 2**: `src/autom8_asana/api/routes/section_timelines.py`

```
# BEFORE (line 91):
    # AC-6.5: Validate period_start <= period_end

# AFTER:
    # Validate period_start <= period_end
```

```
# BEFORE (line 125):
    # NFR-2: Structured logging for endpoint completion

# AFTER:
    # Structured logging for endpoint completion
```

**Effort**: trivial

---

## MANUAL Fixes

### RS-006: Resolve private symbol imports across module boundary (MANUAL)

**Source**: HH-001 (detection-report), LS-004 (analysis-report)
**Finding**: `_serialize_timeline`, `_deserialize_timeline`, and `_DERIVED_TIMELINE_TTL` are
underscore-prefixed (module-private) in `src/autom8_asana/cache/integration/derived.py` but are
imported by two callers:
- `src/autom8_asana/services/section_timeline_service.py` -- imports `_serialize_timeline` and `_deserialize_timeline`
- `tests/unit/cache/test_derived_cache.py` -- imports all three

If `derived.py` refactors its serialization internals, both callers break silently at import time.

**Recommended fix -- choose one option**:

**Option A: Promote to public API (remove underscore prefix)**

Rename in `derived.py`:
- `_serialize_timeline` -> `serialize_timeline`
- `_deserialize_timeline` -> `deserialize_timeline`
- `_DERIVED_TIMELINE_TTL` -> `DERIVED_TIMELINE_TTL`

Update all imports in `section_timeline_service.py` and `test_derived_cache.py`. Export the public
names from `cache/integration/__init__.py` and `cache/__init__.py` if needed.

Choose this if the serialization contract is stable and callers are expected to use it long-term.

**Option B: Add public wrapper functions**

Keep the underscore-prefixed implementations private. Add thin public wrappers in `derived.py`:
```python
def serialize_timeline(timeline: SectionTimeline) -> dict[str, Any]:
    """Public API: serialize a SectionTimeline."""
    return _serialize_timeline(timeline)

def deserialize_timeline(data: dict[str, Any]) -> SectionTimeline:
    """Public API: deserialize a SectionTimeline."""
    return _deserialize_timeline(data)
```
Expose `DERIVED_TIMELINE_TTL = _DERIVED_TIMELINE_TTL` as a public alias if tests need the value.

Choose this if the internal implementation is expected to change while the external contract stays stable.

**Verification steps**:
1. After the change: `grep -r "_serialize_timeline\|_deserialize_timeline\|_DERIVED_TIMELINE_TTL" src/ tests/` -- zero results outside `derived.py` itself.
2. Run the full test suite.

**Effort**: small (~30 minutes of mechanical edits)
**Classification**: MANUAL -- requires a decision about the public API contract for these helpers.

---

### RS-007: Document or bound `_computation_locks` key space (MANUAL)

**Source**: LS-001 (analysis-report)
**Finding**: `_computation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)` in
`section_timeline_service.py:47` accumulates Lock objects indefinitely. Today this is benign
(key space = 1 project x 2 classifiers = 2 entries). If `get_or_compute_timelines` is ever called
with arbitrary project GIDs, the dict becomes a latent memory leak.

**Option A: Document the bounded assumption (trivial)**

Replace the comment block at lines 43-47 with an explicit bounded-space statement:
```python
# Computation lock for thundering-herd prevention (AMB-3).
# Key format: "{project_gid}:{classifier_name}".
# Key space is bounded in production: 1 project x 2 classifiers = 2 entries.
# If call sites expand to arbitrary project GIDs, replace with a TTL-bounded
# structure (e.g., cachetools.TTLCache) to prevent unbounded accumulation.
_computation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
```

**Option B: Use a bounded LRU cache (small)**

Replace the `defaultdict` with a thread-safe bounded structure (verify `cachetools` is in the
dependency tree before using):
```python
from cachetools import LRUCache
import threading

_computation_locks: LRUCache[str, asyncio.Lock] = LRUCache(maxsize=128)
_computation_locks_mu = threading.Lock()

def _get_computation_lock(project_gid: str, classifier_name: str) -> asyncio.Lock:
    key = f"{project_gid}:{classifier_name}"
    with _computation_locks_mu:
        lock = _computation_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _computation_locks[key] = lock
        return lock
```

Note: `asyncio.Lock` objects must not cross event loops. Safe for FastAPI + uvicorn (single loop).

**Verification steps**:
1. Option A: audit all call sites -- `grep -r "get_or_compute_timelines" src/` -- confirm each uses `BUSINESS_OFFERS_PROJECT_GID` and a bounded classifier set.
2. Option B: `pip show cachetools` to confirm availability; run test suite after change.

**Effort**: trivial (Option A) / small (Option B)
**Classification**: MANUAL -- requires a decision about production call site constraints vs. defensive bounding.

---

### RS-008: Add integration test for compute-on-read path (MANUAL)

**Source**: TQ-001 (analysis-report)
**Finding**: `tests/unit/services/test_get_or_compute_timelines.py` patches all cache primitives,
meaning no test exercises the full cache-miss compute path with real cache primitives. The
`test_enumerates_tasks_on_miss` test asserts only `len(result) >= 1` -- it does not verify timeline
content, task GID propagation, or story filtering correctness.

**What a proper integration test should verify**:
1. `read_stories_batch` is called with the correct task GIDs (those returned by task enumeration)
2. Story dicts are correctly converted to `Story` models via `model_validate`
3. The resulting timeline has correct intervals derived from the fixture stories
4. `store_derived_timelines` is called and the derived cache is subsequently populated
5. The returned `OfferTimelineEntry` list has correct `offer_gid`, `active_section_days`, and `billable_section_days` values

**Example test structure** (seed a `MockCacheProvider` with story data; do not patch `read_stories_batch`):
```python
@pytest.mark.asyncio
async def test_computes_correct_intervals_on_cache_miss():
    """Full cache-miss compute path produces correctly structured OfferTimelineEntry."""
    task_gid = "task-001"
    story_dicts = [
        {
            "gid": "s1",
            "resource_subtype": "section_changed",
            "created_at": "2026-01-10T00:00:00Z",
            "new_section": {"name": "Active"},
            "old_section": {"name": "New Leads"},
            "memberships": [{"project": {"gid": BUSINESS_OFFERS_PROJECT_GID}}],
        }
    ]
    cache = build_seeded_mock_cache(task_gid, story_dicts)
    client = build_mock_client(cache=cache, tasks=[make_task(gid=task_gid, section="Active")])

    result = await get_or_compute_timelines(
        client=client,
        project_gid=BUSINESS_OFFERS_PROJECT_GID,
        classifier_name="offer",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
    )

    assert len(result) == 1
    entry = result[0]
    assert entry.offer_gid == task_gid
    assert isinstance(entry.active_section_days, int)
    assert isinstance(entry.billable_section_days, int)

    # Assert the derived cache was populated
    derived = get_cached_timelines(BUSINESS_OFFERS_PROJECT_GID, "offer", cache)
    assert derived is not None
    assert derived.source_entity_count == 1
    assert derived.source_cache_hits == 1
    assert derived.source_cache_misses == 0
```

**Also**: Replace `assert len(result) >= 1` in `test_enumerates_tasks_on_miss` with assertions on `offer_gid` membership and field types.

**Effort**: medium (design fixture data, wire up semi-real cache provider, verify day-count arithmetic)
**Classification**: MANUAL -- test restructuring requires judgment about fixture design, seeding approach, and expected output values.

---

## No-Fix Items

### LS-002: Double-check locking race window (LOW)
**Disposition**: No fix needed.
**Rationale**: Logic-surgeon confirmed the double-check locking pattern is textbook correct. The theoretical race does not apply to Redis or InMemory backends, which enforce TTL atomically within `get_versioned`. No code change warranted.

---

### UO-001: TDD reference density in docstrings (LOW)
**Disposition**: No fix needed.
**Rationale**: Logic-surgeon confirmed this follows the established codebase convention for
"Per TDD-..." and "Per ADR-..." references in docstrings. The decay-report explicitly cleared
"Per TDD-SECTION-TIMELINE-REMEDIATION" docstring citations as non-temporal debt. No change warranted.

---

## Remediation Roadmap (Priority Order)

| Priority | Finding | RS-ID | Classification | Effort | Applied? |
|----------|---------|-------|----------------|--------|----------|
| 1 | CC-001 | RS-002 | AUTO | trivial | No -- patch text above |
| 2 | CC-002 | RS-003 | AUTO | trivial | No -- patch text above |
| 3 | CC-003 | RS-004 | AUTO | trivial | No -- patch text above |
| 4 | CC-004 | RS-005 | AUTO | trivial | No -- patch text above |
| 5 | LS-003 | RS-001 | AUTO | trivial | No -- patch text above |
| 6 | HH-001 / LS-004 | RS-006 | MANUAL | small | No |
| 7 | LS-001 | RS-007 | MANUAL | trivial-small | No |
| 8 | TQ-001 | RS-008 | MANUAL | medium | No |

---

## Verification Command

After applying all AUTO patches (RS-001 through RS-005), run:

```bash
uv run python -m pytest tests/unit/services/test_section_timeline_service.py tests/unit/cache/test_derived_cache.py tests/unit/cache/test_stories_batch.py tests/unit/services/test_get_or_compute_timelines.py tests/unit/api/test_routes_section_timelines.py tests/unit/cache/test_cacheentry_hierarchy.py -x -q --timeout=30
```

---

## Handoff Checklist

- [x] Every finding from all prior reports has a remedy or explicit "no fix needed" disposition
- [x] AUTO patches include exact before/after text -- ready for human or CI application
- [x] MANUAL fixes include rationale and expected correct behavior
- [x] Temporal debt cleanup plans include verification steps for MANUAL items
- [x] Effort estimates for all fixes
- [x] Safe/unsafe classification justified for each fix
- [x] LS-002 and UO-001 explicitly dispositioned as no-fix-needed with rationale

**Ready for gate-keeper.**
