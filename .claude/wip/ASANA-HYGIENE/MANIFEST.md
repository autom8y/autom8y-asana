# ASANA-HYGIENE Initiative Manifest

**Objective**: Resolve all deferred SMELL findings from slop-chop Partition 1, fix the conditional-pass hallucination items, and run slop-chop on remaining test partitions.

**Success Criteria**:
- ~~Gate verdict upgrades from CONDITIONAL-PASS to PASS (20 httpx failures resolved)~~ **DONE** (commit `10c15db`)
- 600-800 LOC reduction from copy-paste parametrization (16 clusters)
- 16 broad `pytest.raises(Exception)` replaced with specific exception types
- Preload manifest check has proper integration test coverage
- Slop-chop Partition 2 scanned and findings addressed
- Zero regressions: test pass count stable or improved

---

## Workstream Decomposition

| WS-ID | Name | Scope | Files | Est. Effort | Phase |
|-------|------|-------|-------|-------------|-------|
| ~~WS-HTTPX~~ | ~~Fix phantom httpx patches~~ | ~~H-001, H-002 (20 tests)~~ | ~~2~~ | **DONE** | -- |
| WS-PARAM | Parametrize copy-paste clusters | LS-009 to LS-024 (16 clusters) | 16 | 4-6h | A+B |
| WS-EXCEPT | Tighten broad exceptions | LS-025 to LS-027 (16 sites) | 8 | 2-3h | A |
| WS-INTEG | Preload manifest integration tests | LS-008 referral | 2 | 2-3h | B |
| WS-OVERMOCK | Over-mock investigation spike | LS-028, LS-029 | 3 | 1h (spike) | B.2 |
| WS-SLOP2 | Slop-chop Partition 2 | tests/{integration,validation,benchmarks} | ~52 | Full sprint | C |

**Total estimated effort**: ~15-20h active work (excluding WS-SLOP2 which is a full orchestrated sprint)

---

## Workflow Spec

The complete parallel worktree sprint specification is at:
**`.claude/wip/ASANA-HYGIENE/WORKFLOW-SPEC.md`**

Covers: phase sequencing, lane allocation, worktree lifecycle, rite switching protocol, merge protocol, checkpoint protocol, escalation protocol, quality gates, hub responsibilities, token budget.

**Pattern**: sprint-parallel-worktrees (2-lane execution), adapted from the proven REM-ASANA-ARCH pattern.

### Execution Schedule (Visual)

```
Phase A:  Lane 1: [WS-PARAM S1] -----> Lane 2: [WS-EXCEPT]
Phase B:  Lane 1: [WS-PARAM S2] -----> Lane 2: [WS-INTEG]       (10x-dev switch)
Phase B2: Lane 1: (idle)         -----> Lane 2: [WS-OVERMOCK]    (rnd switch)
Phase C:  Lane 1: [WS-SLOP2 S1..S3]                              (slop-chop switch)
```

---

## Rite Alignment (Consultant Advisory)

| WS-ID | Rite | Workflow | Complexity | Sessions | Agent Routing |
|-------|------|----------|------------|----------|---------------|
| WS-HTTPX | ~~hygiene~~ | ~~SPOT~~ | ~~SPOT~~ | **DONE** | Completed as hotfix, commit `10c15db` |
| WS-PARAM | **hygiene** | `/task` | MODULE | 2 (8+8 clusters) | architect-enforcer (plan) -> janitor (execute) -> audit-lead (verify) |
| WS-EXCEPT | **hygiene** | `/task` | SPOT | 1 | janitor (direct apply) -> audit-lead (verify) |
| WS-INTEG | **10x-dev** | `/task` | SCRIPT | 1 | principal-engineer (write tests) -> qa-adversary (validate) |
| WS-OVERMOCK | **rnd** | `/spike` | SPIKE | 1 | technology-scout (investigate) -> decision doc |
| WS-SLOP2 | **slop-chop** | `/slop-chop` | MODULE | 2-3 | Full 5-phase pipeline (pythia-coordinated) |

---

## Parallelism Strategy

**Concurrency**: 2 lanes max. Lane 1 is the "hygiene lane" (stays on hygiene through Phases A-B). Lane 2 is the "multi-rite lane" (hygiene -> 10x-dev -> rnd).

**File overlap analysis**: Verified zero overlap between all parallel lane pairs. See WORKFLOW-SPEC.md Section 5 for full scope boundary contracts.

**WS-SLOP2 dependency**: Must wait until WS-PARAM and WS-EXCEPT are complete and merged to main, so Partition 2 runs against clean baseline.

**Rite switches**: 3 total (all on Lane 2 except the final Phase C switch on Lane 1). Each costs ~1-2 minutes (`ari sync --rite=<name>` + Claude restart).

---

## Session Architecture

```
Hub Thread (consciousness hub -- never executes workstream code)
  |
  |-- Phase A (parallel)
  |     |-- Lane 1: WS-PARAM S1 worktree (hygiene)
  |     |-- Lane 2: WS-EXCEPT worktree (hygiene)
  |
  |-- Phase B (parallel, Lane 2 rite switch)
  |     |-- Lane 1: WS-PARAM S2 worktree (hygiene)
  |     |-- Lane 2: WS-INTEG worktree (10x-dev)
  |
  |-- Phase B.2 (Lane 2 only, rite switch)
  |     |-- Lane 2: WS-OVERMOCK worktree (rnd)
  |
  |-- Phase C (Lane 1 only, rite switch)
        |-- Lane 1: WS-SLOP2 worktree (slop-chop, 2-3 sessions)
```

Each worktree session receives a single @-reference: its `WS-{ID}-PROMPT-0.md` file, which is self-contained (execution spec + verification commands + scope boundaries). CLAUDE.md and MEMORY.md are auto-injected. No cross-session communication during execution.

---

## Artifact References

### Source Reports (read-only context)
- Gate verdict: `.claude/wip/SLOP-CHOP-TESTS-P1/phase5-verdict/GATE-VERDICT.md`
- Analysis report: `.claude/wip/SLOP-CHOP-TESTS-P1/phase2-analysis/ANALYSIS-REPORT.md`
- Decay report: `.claude/wip/SLOP-CHOP-TESTS-P1/phase3-decay/DECAY-REPORT.md`
- Detection report: `.claude/wip/SLOP-CHOP-TESTS-P1/phase1-detection/DETECTION-REPORT.md`
- Remediation report: `.wip/REMEDY-tests-unit-p1.md`

### Project References
- Debt ledger: `docs/debt/LEDGER-cleanup-modernization.md`
- Existing arch hygiene WS: `.claude/wip/REM-ASANA-ARCH/WS-HYGIENE.md` (separate initiative, do NOT overlap)

### Initiative Artifacts
- Workflow spec: `.claude/wip/ASANA-HYGIENE/WORKFLOW-SPEC.md`
- Tracker: `.claude/wip/ASANA-HYGIENE/TRACKER.md`
- Seed docs: `.claude/wip/ASANA-HYGIENE/WS-{ID}.md`
- Dispatch prompts: `.claude/wip/ASANA-HYGIENE/WS-{ID}-PROMPT-0.md`

---

## Scope Boundary

**IN SCOPE**: Test quality improvements from slop-chop P1 findings, Partition 2 scan.

**OUT OF SCOPE** (do NOT touch):
- REM-ASANA-ARCH workstreams (WS-SYSCTX, WS-DEBT, WS-DSC, WS-DFEX, WS-QUERY, etc.)
- Production source code changes (except WS-INTEG which may add integration test infrastructure)
- Debt ledger items D-001 through D-035 (architecture/code debt -- separate initiative)
- WS-HYGIENE from REM-ASANA-ARCH (XR-ARCH-001 through XR-ARCH-006 -- separate initiative)
