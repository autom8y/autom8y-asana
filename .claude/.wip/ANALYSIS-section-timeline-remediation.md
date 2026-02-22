---
type: audit
---

# Analysis Report: Section Timeline Architecture Remediation

**Agent**: logic-surgeon
**Mode**: interactive
**Complexity**: MODULE
**Date**: 2026-02-20
**Prior Artifact**: detection-report (hallucination-hunter: 0 CRITICAL, 0 HIGH, 1 MEDIUM)

---

## Summary

Analyzed 18 files (8 source, 7 test, 3 collateral) comprising the migration from
pre-computed `app.state` timeline architecture to compute-on-read-then-cache via
derived cache entries. The architecture is sound. Found 2 MEDIUM logic findings,
1 MEDIUM test quality finding, 1 LOW logic finding, 1 LOW unreviewed-output signal,
and 0 copy-paste bloat issues. No CRITICAL or HIGH findings.

---

## Logic Error Findings

### LS-001: `_computation_locks` unbounded growth (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py:47`
**Finding**: `_computation_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)`
**Evidence**: `defaultdict(asyncio.Lock)` creates a new `asyncio.Lock` for every unique
`(project_gid, classifier_name)` key that is ever accessed and **never removes them**.
In the current deployment, the key space is bounded (1 project x 2 classifiers = 2 keys),
so this is not an immediate production risk. However, if `get_or_compute_timelines` is
ever called with user-supplied or enumerated project GIDs, the dict will accumulate Lock
objects indefinitely. Each Lock is lightweight (~200 bytes), but the dict entries themselves
persist for the process lifetime.

**Expected correct behavior**: Either document the bounded key space assumption or add
a TTL/LRU eviction mechanism for the lock dict.
**Confidence**: MEDIUM -- currently benign due to constrained call sites, but the
`defaultdict` pattern is a latent accumulation risk if call sites expand.
**Severity**: MEDIUM -- no production impact today; would become LOW memory leak if
key space expands.

---

### LS-002: Race window between pre-lock cache check and lock acquisition (LOW confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py:400-415`
**Finding**: The double-check locking pattern at lines 400-415 is correctly implemented:
```python
# Step 1: Check derived cache (no lock)
cached_entry = get_cached_timelines(project_gid, classifier_name, cache)
if cached_entry is not None:
    ...return from cache...

# Step 2: Acquire lock
lock = _get_computation_lock(project_gid, classifier_name)
async with lock:
    # Re-check cache (correct double-check pattern)
    cached_entry = get_cached_timelines(project_gid, classifier_name, cache)
    if cached_entry is not None:
        ...return from cache...
    # ...compute...
```

The double-check locking is textbook correct for in-process thundering herd prevention.
The only theoretical concern: if the cache backend returns stale/expired entries
non-deterministically (e.g., Redis TTL races), the pre-lock check could see a hit while
the post-lock check sees a miss. However, the Redis and Memory backends both enforce TTL
atomically within `get_versioned`, so this is not a real issue.

**Confidence**: LOW -- the pattern is correct as implemented.
**Severity**: LOW -- informational; no fix needed.

---

### LS-003: `get_cached_timelines` silently discards base `CacheEntry` (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py:60-67`
**Finding**:
```python
entry = cache.get_versioned(key, EntryType.DERIVED_TIMELINE)
if entry is None:
    return None
if isinstance(entry, DerivedTimelineCacheEntry):
    return entry
# Fallback: base CacheEntry returned (legacy deserialization)
return None
```

If `get_versioned` returns a valid `CacheEntry` with timeline data but the entry is a
base `CacheEntry` rather than a `DerivedTimelineCacheEntry` (e.g., after a code deployment
where the registry has not been loaded, or a deserialization edge case), the function
silently discards it and returns `None`. This forces a full recomputation even though
the cached data is valid.

**Evidence**: The `_type_registry` mechanism is import-time side-effect driven. If a module
import ordering issue or test isolation problem causes `DerivedTimelineCacheEntry` to not be
registered when `from_dict` runs, the base class would be returned instead. In practice,
the registry IS populated because `entry.py` is imported before `derived.py` always. But
the silent discard is a defensive gap -- no log, no metric.

**Expected correct behavior**: Log a warning when a non-None entry is returned that is
not a `DerivedTimelineCacheEntry`, so operators can detect deserialization regressions.

**Confidence**: MEDIUM -- the silent discard is real and testable; the triggering condition
is unlikely but not impossible.
**Severity**: MEDIUM -- would cause unnecessary recomputation without any observability
signal.

---

### LS-004: `_serialize_timeline` / `_deserialize_timeline` are private but imported cross-module (LOW confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py:369-374`
**Finding**:
```python
from autom8_asana.cache.integration.derived import (
    _deserialize_timeline,
    _serialize_timeline,
    get_cached_timelines,
    store_derived_timelines,
)
```

`_serialize_timeline` and `_deserialize_timeline` are underscore-prefixed (private) in
`derived.py` but are imported by `section_timeline_service.py`. This is also noted by
hallucination-hunter in the detection-report (MEDIUM coupling fragility).

**Evidence**: The underscore prefix indicates module-private API. Cross-module import of
private symbols creates coupling fragility -- if `derived.py` refactors its serialization
internals, the service breaks. The test file `test_derived_cache.py` also imports these
private symbols (lines 21-22).

**Expected correct behavior**: Either promote to public API (remove underscore) or add
public wrappers in `derived.py` that the service and tests can use.

**Confidence**: LOW -- this is API hygiene, not a logic error.
**Severity**: LOW -- coupling fragility, not breakage.

---

## Test Quality Assessment

### TQ-001: No integration test for full compute path (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/services/test_get_or_compute_timelines.py`
**Finding**: The test suite patches `get_cached_timelines`, `read_stories_batch`, and
`store_derived_timelines` at the source module level. This is correct for unit testing but
means no test exercises the full cache-miss compute path end-to-end with real cache primitives.

Specifically, `test_enumerates_tasks_on_miss` (line 239) asserts only `len(result) >= 1`
(line 287) -- a weak assertion that does not verify the content of the result. Compare to
`test_section_timeline_service.py:TestBuildTimelineForOffer` which verifies specific
interval section names, classifications, and exited_at values.

The test for "cache miss path" does not verify that:
1. `read_stories_batch` is called with the correct task GIDs
2. Story dicts are correctly converted to `Story` models via `model_validate`
3. `_build_intervals_from_stories` receives properly filtered/sorted stories
4. `store_derived_timelines` receives correct serialized data

**Expected test quality**: At least one test should exercise the full cache-miss compute
path with a mock cache provider that actually stores and retrieves entries, verifying
the full serialize-deserialize-compute pipeline.

**Confidence**: MEDIUM -- the test gap is real and verifiable.
**Severity**: MEDIUM -- the individual components (serialization, intervals, day counts)
are well-tested independently; the integration between them in the compute path is not.

---

### TQ-002: Test quality of existing test files (GOOD)

The test files demonstrate strong behavioral testing:

- **test_derived_cache.py** (30 tests): Thorough serialization round-trips, cache hit/miss,
  type registry, JSON compatibility. Tests correctly verify None-handling edge cases.
- **test_stories_batch.py** (13 tests): Good chunking boundary tests (exact, under, over),
  mixed hit/miss, pure-read verification (no set_versioned calls).
- **test_routes_section_timelines.py** (7 tests): Covers 200/422/502 paths with proper
  DI override pattern. Verifies response envelope structure.
- **test_section_timeline_service.py** (11 tests): Good coverage of interval building,
  imputation, cross-project noise filtering.
- **test_cacheentry_hierarchy.py** (28 tests): Comprehensive hierarchy tests with
  proper registry isolation fixture.

Overall test quality: GOOD. The only weakness is the integration gap in TQ-001.

---

## Copy-Paste Bloat Scan

### No findings.

Examined for duplicated blocks between:
- `get_or_compute_timelines` cache-miss path (lines 442-521) vs `build_timeline_for_offer` (lines 266-333)

These share a similar pattern (filter stories -> build intervals -> handle imputation) but
with meaningful differences:
- `build_timeline_for_offer`: async per-offer, uses `list_for_task_cached_async` (API calls)
- `get_or_compute_timelines` cache-miss path: sync loop, uses `read_stories_batch` (cache-only)

The story filtering and interval building steps (lines 462-491 in `get_or_compute_timelines`)
do duplicate the pattern from `build_timeline_for_offer` (lines 303-326). However:
1. The input types differ (raw dicts from cache vs Story objects from API)
2. The classifier is parameterized vs hardcoded OFFER_CLASSIFIER
3. `build_timeline_for_offer` is the legacy single-offer path; `get_or_compute_timelines` is the new batch path

This is legitimate similar-but-different code for different execution paths. The shared helpers
(`_build_intervals_from_stories`, `_build_imputed_interval`, `_is_cross_project_noise`) are
already factored out. Extracting more would create unnecessary coupling.

---

## Security Anti-Pattern Scan

### No findings.

- No hardcoded secrets (project GID `1143843662099250` is a public Asana project identifier, not a secret)
- No unvalidated user input reaching cache keys (project_gid comes from a constant,
  classifier_name is validated against the CLASSIFIERS registry)
- Cache operations use versioned/typed keys preventing key collision attacks
- `period_start`/`period_end` are validated by FastAPI's `Query` type coercion and the
  explicit `period_start > period_end` check

---

## Unreviewed-Output Signal Scan

### UO-001: Over-documented with TDD/PRD references in docstrings (LOW confidence)

**Files**: All new/modified source files
**Finding**: Every function in the new code includes references like "Per TDD-SECTION-TIMELINE-REMEDIATION",
"Per AMB-3", "Per Gap 1 primitive", etc. in docstrings.

**Codebase convention evidence**: Existing code in `lifespan.py`, `strategies.py`, and
`stories.py` (pre-existing portions) uses "Per ADR-XXXX" and "Per FR-XXX" references, which
is the established pattern for tracing implementation to design documents. The new code follows
this same convention consistently.

The density of references is higher than the baseline (e.g., `derived.py` has 6 TDD references
in 187 lines vs `stories.py` pre-existing having 3 ADR references in 314 lines), but this is
proportional to the scope of the remediation and is not inconsistent with codebase norms.

**Confidence**: LOW -- follows the established pattern, just at higher density.
**Severity**: LOW -- informational; consistent with codebase conventions.

---

## Collateral Change Assessment

### strategies.py: Detection guard for Business.model_validate (CORRECT)

The change adds `detect_entity_type()` gating before `Business.model_validate()` in both
`DependencyShortcutStrategy._try_cast()` and `HierarchyTraversalStrategy._traverse_to_business_async()`.
This is a logic fix -- `Business.model_validate()` was too permissive (any Task validates as
Business), causing false-positive resolution results. The detection guard uses O(1) project
membership lookup. Tests in `test_strategies.py` cover the new behavior.

No logic errors in this change.

### asana_http.py: Multipart Content-Type header fix (CORRECT)

Removes the default `Content-Type` header before multipart POST so httpx auto-generates
the correct `multipart/form-data` boundary. Uses try/finally to restore the header.
This is a correct fix for a real bug where the boundary token was missing from the header.

No logic errors in this change.

### log.py: `_sanitize_kwargs` for non-stdlib kwargs (CORRECT)

Intercepts non-stdlib keyword arguments (e.g., `message=`) that would cause
`Logger._log()` to raise `TypeError`, and folds them into `extra`. Uses
`_LOGRECORD_RESERVED` frozenset to prefix colliding keys with `log_`.

No logic errors. The frozenset covers all standard LogRecord attributes.

---

## Findings Summary

| ID | Finding | Severity | Confidence | Type |
|----|---------|----------|------------|------|
| LS-001 | `_computation_locks` unbounded growth | MEDIUM | MEDIUM | Logic |
| LS-002 | Double-check locking race window | LOW | LOW | Logic (informational) |
| LS-003 | Silent discard of base CacheEntry in get_cached_timelines | MEDIUM | MEDIUM | Logic |
| LS-004 | Private symbols imported cross-module | LOW | LOW | API hygiene |
| TQ-001 | No integration test for full compute path | MEDIUM | MEDIUM | Test quality |
| UO-001 | High density of TDD references in docstrings | LOW | LOW | Unreviewed-output signal |

**CRITICAL**: 0
**HIGH**: 0
**MEDIUM**: 3 (LS-001, LS-003, TQ-001)
**LOW**: 3 (LS-002, LS-004, UO-001)
**Security referrals**: 0
**Cross-rite referrals**: 0

---

## Handoff Checklist

- [x] Each logic error includes flaw, evidence, expected correct behavior, confidence score
- [x] Copy-paste instances evaluated (none found; legitimate pattern)
- [x] Test degradation findings include weakness and what a proper test would verify
- [x] Security findings evaluated (none warranted)
- [x] Unreviewed-output signals include codebase-convention evidence
- [x] Severity ratings assigned to all findings

Ready for cruft-cutter.
