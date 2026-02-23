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
| WS-PARAM | Parametrize copy-paste clusters | A->B | **S1 MERGED** | 1 | hygiene | S1: 7/8 clusters done (LS-014 N/A), -298 LOC. S2 ready. |
| WS-EXCEPT | Tighten broad exceptions | A | **DONE** | 2 | hygiene | 16/16 replaced. Gate: 0 broad exceptions remaining. |
| WS-INTEG | Preload manifest integration tests | B | **READY** | 2 | hygiene | SPOT, 1 session. Phase A Lane 2 freed. Rite changed from 10x-dev (saves 1 switch). |
| WS-OVERMOCK | Over-mock investigation spike | B.2 | BLOCKED | 2 | rnd | SPIKE, 1h time-box (after Phase B Lane 2 frees) |
| WS-SLOP2 | Slop-chop Partition 2 | C | **READY** | 1 | slop-chop | WS-PARAM + WS-EXCEPT both merged. Entry criteria MET. |

---

## Phase Status

| Phase | Entry Criteria | Status | Exit Criteria |
|-------|---------------|--------|---------------|
| A | WS-HTTPX merged | **COMPLETE** | WS-EXCEPT merged + WS-PARAM S1 checkpoint -- BOTH MET |
| B | Phase A Lane 2 merged | **MET** | WS-PARAM S2 merged + WS-INTEG merged |
| B.2 | Phase B Lane 2 merged | PENDING | WS-OVERMOCK findings doc written |
| C | WS-PARAM + WS-EXCEPT both on main | **MET** (entry only) | P2 GATE-VERDICT.md + all DEFECT addressed |

---

## Lane Allocation (Current Phase: B)

```
Phase A: COMPLETE
  Lane 1: WS-PARAM S1     (hygiene/MODULE)      -- MERGED
  Lane 2: WS-EXCEPT       (hygiene/SPOT)         -- DONE

Phase B (CURRENT):
  Lane 1: WS-PARAM S2     (hygiene/MODULE)      <- READY for dispatch
  Lane 2: WS-INTEG        (hygiene/SPOT)         <- READY for dispatch

Phase B.2 (after Phase B Lane 2 frees):
  Lane 1: (done)
  Lane 2: WS-OVERMOCK     (rnd/SPIKE, rite switch)

Phase C (entry criteria MET, but blocked on WS-PARAM S2 merge):
  Lane 1: WS-SLOP2        (slop-chop/MODULE, rite switch)
```

Max concurrent: 2 worktrees
Rite switches remaining: 2 (rnd for WS-OVERMOCK, slop-chop for WS-SLOP2)

---

## Active Worktrees

| Worktree | WS-ID | Lane | Rite | Created | Status |
|----------|-------|------|------|---------|--------|
| -- | -- | -- | -- | -- | Phase A worktrees merged and available for cleanup |

Stale worktrees to clean up:
- `wt-20260223-235021-e8ee` (WS-PARAM S1, merged as `986e95c`)
- `wt-20260223-235408-290c` (WS-EXCEPT, merged as `e073de7`)
- Other detached worktrees from prior sessions

---

## Merge Log

| Date | WS-ID | Branch/Commit | Merge Commit | Tests After |
|------|-------|---------------|-------------|-------------|
| 2026-02-23 | WS-HTTPX | main | `10c15db` | 63 passed, 0 failed |
| 2026-02-24 | WS-EXCEPT | `e073de7` | fast-forward to `e073de7` | 10,485 passed, 178 failed (pre-existing) |
| 2026-02-24 | WS-PARAM S1 | `986e95c` | merge commit | 10,485 passed, 178 failed (pre-existing) |

---

## Quality Gate Results

| Gate | Phase | Verification | Result | Date |
|------|-------|-------------|--------|------|
| Phase A exit | A | Zero broad `pytest.raises(Exception)` in target files | **PASS** | 2026-02-24 |
| Phase A exit | A | WS-PARAM S1 checkpoint written | **PASS** | 2026-02-24 |
| Phase B exit | B | Test count stable after parametrization; WS-INTEG tests pass | PENDING | |
| Phase C exit | C | P2 GATE-VERDICT.md exists; full suite green | PENDING | |

---

## Blockers

None. Phase B is ready for dispatch. Phase C entry criteria also met (but WS-PARAM S2 should complete first for clean P2 baseline).

---

## Session IDs (for throughline resume)

| WS-ID | Session/Agent ID | Notes |
|-------|-----------------|-------|
| WS-PARAM S1 | wt-235021-e8ee | MERGED. Checkpoint at WS-PARAM-CHECKPOINT.md |
| WS-EXCEPT | wt-235408-290c | MERGED. 16/16 replaced. |

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
