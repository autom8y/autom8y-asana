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
| WS-PARAM | Parametrize copy-paste clusters | A+B | **DONE** | 1 | hygiene | S1: -298 LOC (7/8 clusters). S2: -384 LOC (8/8 clusters). Combined: **-682 LOC** from 15 active clusters. |
| WS-EXCEPT | Tighten broad exceptions | A | **DONE** | 2 | hygiene | 16/16 replaced. Gate: 0 broad exceptions remaining. |
| WS-INTEG | Preload manifest integration tests | B | **DONE** | 2 | hygiene | 3 integration tests, 353 LOC. All 3 branches covered. |
| WS-OVERMOCK | Over-mock investigation spike | B.2 | **READY** | 2 | rnd | SPIKE, 1h time-box. Phase B Lane 2 freed. |
| WS-SLOP2 | Slop-chop Partition 2 | C | **READY** | 1 | slop-chop | WS-PARAM + WS-EXCEPT both merged. Entry criteria MET. |

---

## Phase Status

| Phase | Entry Criteria | Status | Exit Criteria |
|-------|---------------|--------|---------------|
| A | WS-HTTPX merged | **COMPLETE** | WS-EXCEPT merged + WS-PARAM S1 checkpoint -- BOTH MET |
| B | Phase A Lane 2 merged | **COMPLETE** | WS-PARAM S2 merged + WS-INTEG merged -- BOTH MET |
| B.2 | Phase B Lane 2 merged | **MET** | WS-OVERMOCK findings doc written |
| C | WS-PARAM + WS-EXCEPT both on main | **MET** | P2 GATE-VERDICT.md + all DEFECT addressed |

---

## Lane Allocation (Current Phase: B.2 / C)

```
Phase A: COMPLETE
  Lane 1: WS-PARAM S1     (hygiene/MODULE)      -- MERGED
  Lane 2: WS-EXCEPT       (hygiene/SPOT)         -- DONE

Phase B: COMPLETE
  Lane 1: WS-PARAM S2     (hygiene/MODULE)      -- MERGED (9b9786b, -384 LOC)
  Lane 2: WS-INTEG        (hygiene/SPOT)         -- MERGED (634ed34, 3 tests)

Phase B.2 (CURRENT):
  Lane 2: WS-OVERMOCK     (rnd/SPIKE, rite switch)  <- READY for dispatch

Phase C (CURRENT — entry criteria MET):
  Lane 1: WS-SLOP2        (slop-chop/MODULE, rite switch)  <- READY for dispatch
```

Max concurrent: 2 worktrees
Rite switches remaining: 2 (rnd for WS-OVERMOCK, slop-chop for WS-SLOP2)

---

## Merge Log

| Date | WS-ID | Branch/Commit | Merge Commit | Tests After |
|------|-------|---------------|-------------|-------------|
| 2026-02-23 | WS-HTTPX | main | `10c15db` | 63 passed, 0 failed |
| 2026-02-24 | WS-EXCEPT | `e073de7` | fast-forward | 10,485 passed, 178 failed (pre-existing) |
| 2026-02-24 | WS-PARAM S1 | `986e95c` | merge commit | 10,485 passed, 178 failed (pre-existing) |
| 2026-02-24 | WS-PARAM S2 | `9b9786b` | `29a8982` | 10,492 passed, 178 failed (pre-existing) |
| 2026-02-24 | WS-INTEG | `634ed34` | merge commit | 10,492 passed, 178 failed; 3/3 integration tests PASS |

---

## Quality Gate Results

| Gate | Phase | Verification | Result | Date |
|------|-------|-------------|--------|------|
| Phase A exit | A | Zero broad `pytest.raises(Exception)` in target files | **PASS** | 2026-02-24 |
| Phase A exit | A | WS-PARAM S1 checkpoint written | **PASS** | 2026-02-24 |
| Phase B exit | B | Test count stable after parametrization (10,492); WS-INTEG 3/3 pass | **PASS** | 2026-02-24 |
| Phase C exit | C | P2 GATE-VERDICT.md exists; full suite green | PENDING | |

---

## Blockers

None. Phase B.2 (WS-OVERMOCK) and Phase C (WS-SLOP2) are both ready for dispatch.

---

## Session IDs (for throughline resume)

| WS-ID | Session/Agent ID | Notes |
|-------|-----------------|-------|
| WS-PARAM S1 | wt-235021-e8ee | MERGED. |
| WS-EXCEPT | wt-235408-290c | MERGED. |
| WS-PARAM S2 | wt-003956-c12d | MERGED (`9b9786b`). -384 LOC. |
| WS-INTEG | wt-004114-e156 | MERGED (`634ed34`). 3/3 integration tests. |
| Context-engineer | a62d24fa4c6c74c69 | Throughline agent |
| Consultant | a828a88ec773291b4 | Throughline agent |

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
