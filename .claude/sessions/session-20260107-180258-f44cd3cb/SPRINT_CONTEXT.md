---
sprint_id: sprint-dataframe-builder-consolidation
session_id: session-20260107-180258-f44cd3cb
name: DataFrame Builder Consolidation
goal: Consolidate ProjectDataFrameBuilder and ProgressiveProjectBuilder into unified builder with parallel fetch + incremental resume
status: COMPLETE
created_at: 2026-01-07T19:51:00Z
started_at: 2026-01-07T19:51:00Z
completed_at: 2026-01-07T19:40:00Z
complexity: MODULE
---

# Sprint: DataFrame Builder Consolidation

## Objective
Eliminate code smell by consolidating two DataFrame builders into one unified builder that combines:
- Parallel fetch capability (from ProjectDataFrameBuilder)
- Incremental resume with S3 persistence (from ProgressiveProjectBuilder)
- Watermark-based task filtering for efficient rebuilds

## Task Breakdown

| ID | Phase | Description | Agent | Status | Depends On |
|----|-------|-------------|-------|--------|------------|
| T1.0 | 1 | Watermark filtering design (TDD) | architect | in_progress | - |
| T1.1 | 1 | `build_with_parallel_fetch_async()` | principal-engineer | pending | T1.0 |
| T1.2 | 1 | Watermark-based task filtering impl | principal-engineer | pending | T1.0 |
| T1.3 | 1 | Create `fields.py` with BASE_OPT_FIELDS | principal-engineer | pending | T1.0 |
| T2.0 | 2 | Factory function + compatibility shim | principal-engineer | pending | T1.1, T1.2, T1.3 |
| T2.1 | 2 | Integration test: old interface → new | qa-adversary | pending | T2.0 |
| T3.1 | 3 | Migrate UnitResolutionStrategy | principal-engineer | pending | T2.1 |
| T3.2 | 3 | Migrate OfferResolutionStrategy | principal-engineer | pending | T2.1 |
| T3.3 | 3 | Migrate ContactResolutionStrategy | principal-engineer | pending | T2.1 |
| T3.4 | 3 | Resolution strategy integration test | qa-adversary | pending | T3.1, T3.2, T3.3 |
| T4.0 | 4 | Migrate decorator.py, dataframe_cache.py | principal-engineer | pending | T3.4 |
| T4.1 | 4 | Migrate extractors | principal-engineer | pending | T3.4 |
| T5.0 | 5 | Delete project.py, rename progressive.py | principal-engineer | pending | T4.0, T4.1 |
| T5.1 | 5 | Import path verification | qa-adversary | pending | T5.0 |
| T6.0 | 6 | Update 68 tests across 4 files | principal-engineer | pending | T5.1 |
| T6.1 | 6 | Full test suite validation | qa-adversary | pending | T6.0 |
| T7.0 | 7 | Dead code removal, doc updates | principal-engineer | pending | T6.1 |

## QA Checkpoints

| Gate | After | Focus |
|------|-------|-------|
| QA-1 | T2.0 | Compatibility shim: old callers work unchanged |
| QA-2 | T3.4 | Resolution strategies: identical output |
| QA-3 | T5.0 | Import audit: no dangling references |
| QA-4 | T6.1 | Full regression: all tests pass |

## Critical Path

```
T1.0 → T1.1/T1.2/T1.3 (parallel) → T2.0 → T2.1 → T3.x → T3.4 → T4.x → T5.0 → T5.1 → T6.x → T7.0
```

## Progress Log

### 2026-01-07T19:51:00Z
- Sprint created
- T1.0 started: Architect consultation for watermark design

## Completion Criteria

- [ ] `ProjectDataFrameBuilder` class removed entirely
- [ ] `ProgressiveProjectBuilder` renamed to `ProjectDataFrameBuilder`
- [ ] All 13+ files migrated
- [ ] All 3 resolution strategies use unified builder
- [ ] Tests pass (68 tests)
- [ ] `_BASE_OPT_FIELDS` deduplicated
- [ ] Parallel fetch + resume capability both work
