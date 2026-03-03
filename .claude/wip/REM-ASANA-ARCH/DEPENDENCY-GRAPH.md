# Workstream Dependency Graph

## Phased Execution Order

```
PHASE 0 (Week 1)
================
  WS-QW  [R-001, R-002, R-003, R-007]
    |      3-6 hours, PATCH, no dependencies
    |      Resolves: U-003, U-007
    |
    +-- All subsequent phases benefit from Quick Wins being done first
        (documented canonical status, shared helpers, verified entry points)

PHASE 1 (Week 2-3) -- Parallelizable
=====================================
  WS-SYSCTX  [R-005]                    WS-DSC  [R-008]
    |  1-2 days, MODULE                    |  3-5 days, MODULE
    |  Eliminates Cycle 4                  |  Reduces endpoint boilerplate
    |  No dependencies                     |  No dependencies
    |                                      |
    +---------- can run in parallel -------+

PHASE 2 (Week 3-4)
===================
  WS-DFEX  [R-006, R-009]               WS-CLASS  [R-004]
    |  3-3.5 days, MODULE                  |  1 day, PATCH
    |  Cleaner after WS-SYSCTX            |  BLOCKED on U-002 resolution
    |  (not hard-blocked)                  |  (git blame activity.py)
    |  Eliminates Cycle 1                  |
    |  (models->dataframes direction)      |
    |                                      |
    v                                      |
PHASE 3 (Week 5+, opportunistic)          |
=================================          |
  WS-QUERY  [R-010]                        |
    |  3 days, MODULE                      |
    |  Best after WS-DFEX                  |
    |  (clean service boundaries)          |
    |  Decouples query engine              |
    |                                      |
    +--------------------------------------+

CROSS-RITE (Any Phase, Independent)
====================================
  WS-HYGIENE  [XR-001..006]             WS-DEBT  [XR-002, D-002]
    |  3-4 days, PATCH/MODULE              |  1-2 days, PATCH
    |  hygiene rite                         |  debt-triage rite
    |  No dependencies                     |  No dependencies
    |  6 referrals, ordered by priority    |  v1 sunset audit
```

## Dependency Table

| Workstream | Depends On | Blocks | Parallel With |
|------------|------------|--------|---------------|
| WS-QW | (none) | (none, but do first) | -- |
| WS-SYSCTX | (none) | WS-DFEX (soft) | WS-DSC, WS-HYGIENE, WS-DEBT |
| WS-DSC | (none) | (none) | WS-SYSCTX, WS-HYGIENE, WS-DEBT |
| WS-DFEX | WS-SYSCTX (soft) | WS-QUERY | WS-DSC, WS-CLASS |
| WS-CLASS | U-002 resolution | (none) | WS-DFEX |
| WS-QUERY | WS-DFEX (soft) | (none) | WS-HYGIENE, WS-DEBT |
| WS-HYGIENE | (none) | (none) | Any |
| WS-DEBT | (none) | (none) | Any |

**Soft dependency** = cleaner/easier after the dependency is done, but not blocked.
All workstreams are technically independent -- dependencies are quality-of-execution,
not correctness.

## Critical Path

The longest dependency chain is:

```
WS-QW (0.5 day) -> WS-SYSCTX (2 days) -> WS-DFEX (3.5 days) -> WS-QUERY (3 days)
                                                                  = ~9 days
```

With parallelization (WS-DSC during WS-SYSCTX, WS-CLASS during WS-DFEX):

```
Week 1:   WS-QW
Week 2:   WS-SYSCTX || WS-DSC
Week 3:   WS-DSC (cont) || WS-DFEX starts
Week 4:   WS-DFEX (cont) || WS-CLASS
Week 5+:  WS-QUERY (opportunistic)
```

Cross-rite work (WS-HYGIENE, WS-DEBT) slots into any gaps.

## Unknown Resolution Gates

| Unknown | Must Resolve Before | Resolution Time |
|---------|--------------------|--------------------|
| U-002 | WS-CLASS | 5 min (git blame) |
| U-003 | WS-QW R-001 | 5 min (read file) |
| U-006 | WS-SYSCTX | 10 min (read ARCH-REVIEW-1) |
| U-007 | WS-QW R-007 | 5 min (read file) |
| U-008 | WS-HYGIENE XR-006 | 5 min (run 2 tests) |
