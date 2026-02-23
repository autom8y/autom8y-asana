# ASANA-HYGIENE Tracker

**Initiative**: Test Quality Hygiene (slop-chop P1 deferred + P2)
**Started**: 2026-02-23
**Hub**: This thread is the consciousness hub
**Workflow spec**: `.claude/wip/ASANA-HYGIENE/WORKFLOW-SPEC.md`

---

## Workstream Status

| WS-ID | Name | Phase | Status | Lane | Rite | Notes |
|-------|------|-------|--------|------|------|-------|
| WS-HTTPX | Fix phantom httpx patches | -- | **DONE** | -- | -- | Commit `10c15db`, 20 tests fixed, gate -> PASS |
| WS-PARAM | Parametrize copy-paste clusters | A | READY | 1 | hygiene | MODULE, 2 sessions (S1: LS-011-016,019,020; S2: LS-009,010,017,018,021-024) |
| WS-EXCEPT | Tighten broad exceptions | A | READY | 2 | hygiene | SPOT, 1 session, 16 sites across 8 files |
| WS-INTEG | Preload manifest integration tests | B | BLOCKED | 2 | 10x-dev | SCRIPT, 1 session (after Phase A Lane 2 frees) |
| WS-OVERMOCK | Over-mock investigation spike | B.2 | BLOCKED | 2 | rnd | SPIKE, 1h time-box (after Phase B Lane 2 frees) |
| WS-SLOP2 | Slop-chop Partition 2 | C | BLOCKED | 1 | slop-chop | MODULE, 2-3 sessions (after WS-PARAM + WS-EXCEPT merge) |

---

## Phase Status

| Phase | Entry Criteria | Status | Exit Criteria |
|-------|---------------|--------|---------------|
| A | WS-HTTPX merged | **MET** (commit `10c15db`) | WS-EXCEPT merged + WS-PARAM S1 checkpoint |
| B | Phase A Lane 2 merged | PENDING | WS-PARAM S2 merged + WS-INTEG merged |
| B.2 | Phase B Lane 2 merged | PENDING | WS-OVERMOCK findings doc written |
| C | WS-PARAM + WS-EXCEPT both on main | PENDING | P2 GATE-VERDICT.md + all DEFECT addressed |

---

## Lane Allocation (Current Phase: A)

```
Phase A (CURRENT):
  Lane 1: WS-PARAM S1     (hygiene/MODULE)      <- READY for dispatch
  Lane 2: WS-EXCEPT       (hygiene/SPOT)         <- READY for dispatch

Phase B (after Phase A Lane 2 frees):
  Lane 1: WS-PARAM S2     (hygiene/MODULE, continued)
  Lane 2: WS-INTEG        (10x-dev/SCRIPT, rite switch)

Phase B.2 (after Phase B Lane 2 frees):
  Lane 1: (done)
  Lane 2: WS-OVERMOCK     (rnd/SPIKE, rite switch)

Phase C (after WS-PARAM + WS-EXCEPT merged):
  Lane 1: WS-SLOP2        (slop-chop/MODULE, rite switch)
```

Max concurrent: 2 worktrees
Rite switches remaining: 3

---

## Active Worktrees

| Worktree | WS-ID | Lane | Rite | Created | Status |
|----------|-------|------|------|---------|--------|
| -- | -- | -- | -- | -- | No active worktrees yet |

---

## Merge Log

| Date | WS-ID | Branch | Commit | Tests After |
|------|-------|--------|--------|-------------|
| 2026-02-23 | WS-HTTPX | main | `10c15db` | 63 passed, 0 failed |

---

## Quality Gate Results

| Gate | Phase | Verification | Result | Date |
|------|-------|-------------|--------|------|
| Phase A exit | A | Zero broad `pytest.raises(Exception)` in target files | PENDING | |
| Phase B exit | B | Test count stable after parametrization; WS-INTEG tests pass | PENDING | |
| Phase C exit | C | P2 GATE-VERDICT.md exists; full suite green | PENDING | |

---

## Blockers

None currently. Phase A is ready for dispatch.

---

## Session IDs (for throughline resume)

| WS-ID | Session/Agent ID | Notes |
|-------|-----------------|-------|
| -- | -- | Populated when sessions are dispatched |

---

## Phase Legend

| Status | Meaning |
|--------|---------|
| READY | Prompt written, entry criteria met, ready for dispatch |
| BLOCKED | Waiting on prior phase completion |
| DISPATCHED | Worktree session launched |
| IN PROGRESS | Session executing |
| REVIEW | Changes complete, pending hub review |
| MERGED | Branch merged to main, tests verified |
| DONE | Verified on main, MEMORY.md updated |
