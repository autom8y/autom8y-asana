---
schema_version: "1.0"
sprint_id: S6
sprint_name: "SWR Production Wiring + Dead Code Cleanup"
session_id: session-20260203-124709-9df8e766
status: COMPLETE
created_at: "2026-02-03T16:48:01Z"
completed_at: "2026-02-03T16:56:04Z"
complexity: SCRIPT
entry_point: principal-engineer
phases:
  - implementation
  - validation
current_phase: validation
---

# Sprint 6: SWR Production Wiring + Dead Code Cleanup

## Goal

Wire the SWR build callback in factory.py so background refreshes work, and remove ttl_hours dead code from DataFrameCache and tests.

## Context

Following the completion of the stale-while-revalidate (SWR) spike (SPIKE-stale-while-revalidate-freshness.md), Sprint 6 focuses on production wiring of the SWR build callback and cleanup of the now-obsolete ttl_hours parameter.

**Key Design Decisions from Spike:**
- SWR callback wired in factory.py's `create_cache()` function
- `ttl_hours` parameter is dead code (never used in actual cache operations)
- Build callback enables background refresh without blocking reads
- Cleanup includes DataFrameCache dataclass and test helpers

## Tasks

### S6-001: Wire SWR Build Callback + Remove ttl_hours Dead Code
**Phase**: implementation
**Agent**: principal-engineer
**Status**: completed
**Completed**: 2026-02-03T17:30:00Z

**Scope:**
1. Wire SWR build callback in `src/autom8_asana/cache/factory.py`
   - Pass `build_callback` to DataFrameCache constructor
   - Ensure callback signature matches spike design
2. Remove `ttl_hours` dead code:
   - Remove from DataFrameCache dataclass in `src/autom8_asana/cache/dataframe_cache.py`
   - Remove from test helpers in `tests/unit/cache/dataframe/test_dataframe_cache.py`
   - Remove any other references found via grep

**Artifacts**:
- src/autom8_asana/cache/factory.py (wired _swr_build callback with resume=True, removed ttl_hours=12)
- src/autom8_asana/cache/dataframe_cache.py (removed ttl_hours field from dataclass)
- tests/unit/cache/dataframe/test_dataframe_cache.py (removed ttl_hours from make_cache(), added TestSWRCallbackWiring test class)
- tests/unit/cache/dataframe/test_schema_version_validation.py (removed ttl_hours from make_cache())
- tests/unit/cache/dataframe/test_dataframe_cache_stats.py (removed ttl_hours from _make_cache())

**Test Results**: 158 dataframe cache tests passed, 942 cache tests passed, zero ttl_hours references in src/

**Design Reference**: docs/spikes/SPIKE-stale-while-revalidate-freshness.md

---

### S6-002: Adversarial Testing - SWR Wiring + Dead Code Removal
**Phase**: validation
**Agent**: qa-adversary
**Status**: completed
**Completed**: 2026-02-03T16:56:04Z

**Scope:**
1. Verify SWR build callback is properly wired in factory.py
2. Confirm ttl_hours fully removed from:
   - DataFrameCache dataclass
   - Test helpers
   - Any other references
3. Regression testing:
   - Existing cache tests still pass
   - No broken references to ttl_hours
   - SWR callback can be invoked without error

**Artifact**: /Users/tomtenuta/Code/autom8_asana/tests/unit/cache/dataframe/test_adversarial_swr_wiring.py

**Test Summary**: 158 dataframe cache tests, 942 cache tests, 6822 unit tests — all passing, zero failures

**Defects**: Zero

**Key Validations**:
- ttl_hours fully dead in src/ and tests/
- SWR callback correctly wired (closure, ordering, resume=True, early returns, guarded puts)
- All adversarial edge cases assessed safe

**Verdict**: GO - Zero defects, zero regressions, SWR production-ready

---

## Dependencies

**Upstream**: SPIKE-stale-while-revalidate-freshness.md (completed)
**Downstream**: None (cleanup sprint)

## Entry Point

principal-engineer (skip PRD/TDD — spike serves as design artifact)

## Success Criteria

1. SWR build callback wired in factory.py
2. ttl_hours dead code fully removed from codebase
3. All existing cache tests pass (zero regressions)
4. QA adversarial validation passes
5. No broken references to ttl_hours remain

## Notes

- This is a cleanup sprint following spike validation
- No PRD/TDD required (spike document serves as design)
- Entry point is principal-engineer for direct implementation
- Low complexity (SCRIPT level)
- Should be quick turnaround (1-2 tasks only)
