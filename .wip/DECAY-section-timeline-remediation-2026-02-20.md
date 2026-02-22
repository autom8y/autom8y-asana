---
type: audit
---
# Decay Report: Section Timeline Architecture Remediation

**Agent**: cruft-cutter
**Mode**: interactive
**Complexity**: MODULE
**Scope**: Section timeline migration from pre-computed app.state to compute-on-read-then-cache
**Report Date**: 2026-02-20
**Git Baseline**: HEAD = `8b5813e` (2026-02-19 23:19:27)

---

## Executive Summary

The remediation is clean. The warm-up pipeline was fully excised -- no orphaned symbols, no residual `app.state.timeline*` keys, no dead conditional guards in the production path. Four temporal findings were identified, all at TEMPORAL severity. Two are **provably stale** (architecture ghost comments referencing deleted systems). Two are **probably stale** (inline requirement tags and a warm-up era rationale comment).

---

## Findings

---

### CC-001: Stale docstring claim: "No persistent state stored on app.state for SDK" (provably stale)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py:63`
**Finding**:
```python
    Yields:
        None (no persistent state stored on app.state for SDK).
```
**Evidence**: The Yields clause states no persistent state is stored on `app.state` for the SDK. This was accurate before DEF-005 (commit `557a44c`, 2026-02-19 18:31). The current function body stores four keys on `app.state` at startup:
- `app.state.cache_provider` (line 110)
- `app.state.client_pool` (line 121)
- `app.state.entity_write_registry` (line 186)
- `app.state.cache_warming_task` (line 243)

The Yields line was not updated when these were added. The TDD-SECTION-TIMELINE-REMEDIATION comment block immediately below (lines 250-253) explicitly says "No app.state keys for timeline data" -- a true statement scoped to timelines -- but the Yields clause above still claims no `app.state` keys at all.

`git log --format="%ai" src/autom8_asana/api/lifespan.py` confirms `8b5813e` as the latest touch.

**Type**: Architecture ghost comment -- describes a system state that no longer exists.
**Tier**: Provably stale -- four `app.state.*` assignments exist in the same function body, directly contradicting the Yields claim.
**Severity**: TEMPORAL (advisory, never blocking)

---

### CC-002: Stale cross-reference in ClientPool comment: "cache backend as the timeline warm-up task" (provably stale)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py:119-120`
**Finding**:
```python
    # DEF-005: pass shared cache_provider so pooled clients share the same
    # cache backend as the timeline warm-up task.
```
**Evidence**: "timeline warm-up task" refers to the pre-computed architecture (`warm_story_caches`, `build_all_timelines`) that was removed in commit `8b5813e` (2026-02-19 23:19). Comprehensive grep across `src/` and `tests/` for all warm-up era symbols returns zero results:

```
warm_story_caches         -> 0 results
build_all_timelines       -> 0 results
_WARM_TIMEOUT_SECONDS     -> 0 results
app.state.offer_timelines -> 0 results
timeline_warm_count       -> 0 results
```

The shared `cache_provider` itself is still correct and necessary. Only the stated beneficiary (the warm-up task) is a ghost.

**Type**: Architecture ghost comment -- the referenced component (timeline warm-up task) was deleted in `8b5813e`.
**Tier**: Provably stale -- warm-up task confirmed absent by comprehensive grep.
**Severity**: TEMPORAL (advisory, never blocking)

---

### CC-003: `build_timeline_for_offer` carries warm-up era comment explaining `max_cache_age_seconds=7200` in terms of the removed warm-up pipeline (probably stale)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py:292-295`
**Finding**:
```python
    # FR-1: Fetch stories via cached client.
    # max_cache_age_seconds=7200: If the story cache was populated during
    # warm-up (runs every ~12 min on ECS restart), skip the Asana API
    # refresh entirely.  Stories fetched within the last 2 hours are current
    # enough for historical day-counting.
```
**Evidence**: The comment justifies `max_cache_age_seconds=7200` in terms of the removed warm-up pipeline ("populated during warm-up (runs every ~12 min on ECS restart)"). The warm-up pipeline no longer runs. Under the remediated architecture, story caches are populated by `_preload_dataframe_cache_progressive` (the DataFrame cache preload background task), not by a dedicated timeline warm-up. The 7200-second threshold may still be appropriate, but the stated rationale is now inaccurate.

**Additional context**: `build_timeline_for_offer` has no callers in production source (`src/`). It is only called from `tests/unit/services/test_section_timeline_service.py:290,322`. The production path (`get_or_compute_timelines`) uses `read_stories_batch` (pure-read from cache, no API calls) and never calls `build_timeline_for_offer`. Whether the function itself is dead production code is a logic/hygiene question outside cruft-cutter jurisdiction. The comment archaeology finding here is scoped to the stale warm-up rationale.

`git log --format="%ai"` on `section_timeline_service.py`: latest commit `8b5813e` (2026-02-19 23:19).

**Type**: Architecture ghost comment -- rationale references a system that no longer exists.
**Tier**: Probably stale -- warm-up pipeline confirmed deleted; however, the 7200s value may have independent validity not documented in this file, and there is no explicit "keep until" marker.
**Severity**: TEMPORAL (advisory, never blocking)

---

### CC-004: Inline requirement tags (FR-*, AC-*, EC-*, NFR-*) in production source (probably stale)

**Files and lines**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py`: 276-278 (docstring), 291, 302, 305, 310, 313, 318, 504
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py`: 91, 125

**Finding** (representative):
```python
    # FR-1: Fetch stories via cached client.
    # AC-1.2: Filter to section_changed only
    # AC-1.3, AC-1.4: Filter cross-project noise
    # Sort by created_at ascending (AC-2.5)
    # FR-2: Build intervals from filtered stories
    # FR-3: Handle never-moved task
    # EC-6: Entity with zero cached stories.
    # AC-6.5: Validate period_start <= period_end
    # NFR-2: Structured logging for endpoint completion
```
**Evidence**: These are TDD-era acceptance criteria tags (FR = Functional Requirement, AC = Acceptance Criteria, EC = Edge Case, NFR = Non-Functional Requirement) from the TDD-SECTION-TIMELINE-001 and TDD-SECTION-TIMELINE-REMEDIATION specification documents. They cross-reference internal planning documents located in `.claude/wip/` -- an ephemeral working directory, not stable documentation. No URLs are provided. The tags first appeared in `574b16f` (2026-02-19 14:36) and survived through `8b5813e` (2026-02-19 23:19). The referenced feature has shipped.

These tags are the initiative-tag anti-pattern: they track traceability to a now-completed specification phase. The information belongs in commit messages (where several FR/AC/EC tags already appear) or test docstrings, not inline in the step-by-step logic of production functions.

**Type**: Ephemeral comment artifact -- initiative tags referencing a completed specification.
**Tier**: Probably stale -- no resolution signal confirming the TDD docs are formally closed; however, the feature shipped and the specification lifecycle is complete.
**Severity**: TEMPORAL (advisory, never blocking)

---

## Non-Findings (Items Investigated and Cleared)

The following were explicitly investigated and found clean.

**Warm-up pipeline removal -- fully complete.** Grep for `warm_story_caches`, `build_all_timelines`, `_WARM_TIMEOUT_SECONDS`, `app.state.offer_timelines`, `app.state.timeline_warm_count`, `app.state.timeline_total`, `app.state.timeline_warm_failed`, `app.state.timeline_build_count`, `app.state.timeline_build_total` across `src/` and `tests/` returns zero results. The pre-compute architecture introduced in commit `8b5813e` was fully replaced within the same commit.

**`get_or_compute_timelines` -- no dead code path.** Imported in `section_timelines.py:26-29`, called at line 101. No conditional flag guards between old and new approaches. The new architecture is the only production path.

**`_computation_locks` module-level state.** Actively used by `_get_computation_lock()` at `section_timeline_service.py:50-61`, which is called inside `get_or_compute_timelines()`. Not dead.

**Derived cache primitives -- all exported and used.** `make_derived_timeline_key`, `get_cached_timelines`, `store_derived_timelines` are exported from `cache/__init__.py:99-102` and `cache/integration/__init__.py:8-12`, and are called from `get_or_compute_timelines()` at lines 369-374. Not dead.

**`read_cached_stories` and `read_stories_batch` -- both active.** `read_stories_batch` is called at `section_timeline_service.py:439`. `read_cached_stories` is exported and tested; its non-use in the current service hot path is architectural (the batch variant is used for the bulk case) rather than temporal.

**`DerivedTimelineCacheEntry` "Fallback: base CacheEntry returned (legacy deserialization)" comment** (`derived.py:66`). This is a permanent defensive pattern in the serialization layer, not a migration stub. The `from_dict()` dispatch mechanism in `entry.py` is designed to handle base-class fallback for forward compatibility with any future data that arrives without a `_type` discriminator. Not temporal debt.

**ADR references in comments.** All ADR references in in-scope files (`ADR-ASANA-007`, `ADR-0020`, `ADR-0021`, `ADR-0023`, `ADR-0025`, `ADR-0026`, `ADR-0060`, `ADR-0067`, `ADR-0131`, `ADR-INS-004`) reference permanent architectural decisions. No inline `ADR-0146`, `ADR-0147`, or `ADR-0148` references appear in source code -- those ADRs live only in `docs/decisions/`. Clean.

**`HOTFIX:` comment in `cache/__init__.py:177`.** Tags a defensive `try/except ImportError` for Lambda compatibility predating this migration (introduced 2026-02-05, commit `680ef63`). Outside the scope of this remediation.

**`Per TDD-SECTION-TIMELINE-REMEDIATION` docstring citations.** These name the design document in module and function docstrings. This pattern is used consistently across the codebase for multiple TDDs and serves as stable design provenance, consistent with how ADR references are used elsewhere. Not flagged.

---

## Staleness Scores

| ID | File | Line(s) | Type | Tier | Evidence Quality |
|----|------|---------|------|------|-----------------|
| CC-001 | `api/lifespan.py` | 63 | Architecture ghost | **Provably stale** | Direct contradiction by 4 `app.state.*` assignments in same function body |
| CC-002 | `api/lifespan.py` | 119-120 | Architecture ghost | **Provably stale** | Referenced component (warm-up task) confirmed deleted by exhaustive grep |
| CC-003 | `services/section_timeline_service.py` | 292-295 | Architecture ghost | Probably stale | Warm-up pipeline deleted; 7200s value may retain independent validity |
| CC-004 | `services/section_timeline_service.py`, `api/routes/section_timelines.py` | Multiple | Initiative tag | Probably stale | Feature shipped; spec lifecycle complete; no stable external reference |

**Staleness methodology**: "Provably stale" requires a positive resolution signal (confirmed deletion, direct contradiction in the same file). "Probably stale" uses the 90-day default heuristic, reduced to same-sprint inference for initiative tags from a completed feature. Age for all findings: ~1 day (HEAD = `8b5813e`, 2026-02-19).

---

## Handoff Notes for Remedy-Smith

- **CC-001** (`lifespan.py:63`): One-line docstring fix. Replace the inaccurate Yields clause. Suggested replacement: `None (control returned to request handlers; startup state on app.state includes cache_provider, client_pool, entity_write_registry, cache_warming_task).`
- **CC-002** (`lifespan.py:119-120`): Update the DEF-005 comment. The cache_provider sharing rationale is sound; only "timeline warm-up task" needs updating. Suggested: replace "timeline warm-up task" with "pooled request handlers" or similar.
- **CC-003** (`section_timeline_service.py:292-295`): Update the `max_cache_age_seconds=7200` comment to reflect the actual cache population source. Replace the warm-up reference with a description of how story caches are populated in the current architecture (DataFrameCache preload via `_preload_dataframe_cache_progressive`), or simplify to state the staleness tolerance directly without referencing the old pipeline.
- **CC-004** (`section_timeline_service.py` multiple lines, `section_timelines.py:91,125`): Strip the inline `# FR-N:`, `# AC-N.N:`, `# EC-N:`, `# NFR-N:` prefix tags. The algorithmic steps are self-documenting; requirement traceability belongs in commit messages.

All findings are TEMPORAL severity. None block merge.
