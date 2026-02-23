# ASANA-HYGIENE Workflow Spec

**Pattern**: sprint-parallel-worktrees (2-lane execution)
**Initiative**: Test Quality Hygiene (slop-chop P1 deferred + P2)
**Workstreams**: 5 active (WS-HTTPX DONE)
**Sessions**: 7-8 total across 4 phases
**Parallelism**: 2 concurrent worktrees max
**Rite switches**: 3 total across initiative

---

## 1. Sprint Overview

Resolve all deferred SMELL findings from slop-chop Partition 1 and run the quality gate on Partition 2. Five active workstreams across three rites (hygiene, 10x-dev, rnd) plus a final slop-chop scan. Estimated 3-5 days active work for P1 findings, plus 1-2 days for P2.

**Test baseline**: 11,123 passed, 46 skipped, 2 xfailed (post-NameGid fix)

---

## 2. Phase Sequencing

### Phase A: Parallel Hygiene (both lanes, hygiene rite)

| Lane | WS-ID | Sessions | Rite | Complexity |
|------|-------|----------|------|------------|
| 1 | WS-PARAM S1 | 1 of 2 | hygiene | MODULE |
| 2 | WS-EXCEPT | 1 of 1 | hygiene | SPOT |

**Entry criteria**: WS-HTTPX merged (DONE, commit `10c15db`)
**Exit criteria**: WS-EXCEPT merged, WS-PARAM S1 checkpoint written

**Rite state**: Both lanes hygiene. Zero switches.

### Phase B: Cross-Rite Development (continue + switch Lane 2)

| Lane | WS-ID | Sessions | Rite | Complexity |
|------|-------|----------|------|------------|
| 1 | WS-PARAM S2 | 2 of 2 | hygiene | MODULE |
| 2 | WS-INTEG | 1 of 1 | 10x-dev | SCRIPT |

**Entry criteria**: Phase A Lane 2 merged
**Exit criteria**: WS-PARAM S2 merged, WS-INTEG merged

**Rite state**: Lane 1 stays hygiene. Lane 2 switches to 10x-dev (switch 1 of 3).

### Phase B.2: Investigation Spike (Lane 2 only)

| Lane | WS-ID | Sessions | Rite | Complexity |
|------|-------|----------|------|------------|
| 1 | (idle) | -- | -- | -- |
| 2 | WS-OVERMOCK | 1 of 1 | rnd | SPIKE |

**Entry criteria**: Phase B Lane 2 merged
**Exit criteria**: WS-OVERMOCK findings document written

**Rite state**: Lane 2 switches to rnd (switch 2 of 3). Lane 1 idle.

### Phase C: Partition 2 Quality Gate (Lane 1)

| Lane | WS-ID | Sessions | Rite | Complexity |
|------|-------|----------|------|------------|
| 1 | WS-SLOP2 | 2-3 | slop-chop | MODULE |
| 2 | (idle) | -- | -- | -- |

**Entry criteria**: WS-PARAM + WS-EXCEPT both merged to main
**Exit criteria**: P2 GATE-VERDICT.md produced, all DEFECT findings addressed

**Rite state**: Lane 1 switches to slop-chop (switch 3 of 3).

---

## 3. Worktree Lifecycle Protocol

Each worktree session follows this exact sequence:

```
 1. HUB:       ari worktree create "<ws-name>"
 2. HUB:       cd <worktree-path>
 3. TERMINAL:  ari sync --rite=<rite-name>  (if rite differs from current)
 4. TERMINAL:  claude
 5. WORKTREE:  @.claude/wip/ASANA-HYGIENE/WS-{ID}-PROMPT-0.md
               <session prompt from Section 7 below>
 6. WORKTREE:  (autonomous execution per PROMPT-0)
 7. WORKTREE:  /wrap
 8. HUB:       cd /Users/tomtenuta/Code/autom8y-asana
 9. HUB:       git merge <worktree-branch>
10. HUB:       Run scoped tests (see Section 6)
11. HUB:       Update TRACKER.md + MEMORY.md
12. HUB:       ari worktree remove "<worktree-id>"
```

**Key difference from REM-ASANA-ARCH**: ASANA-HYGIENE sessions use a single @-reference (the PROMPT-0 file), which already embeds the full execution spec, verification commands, and scope boundaries. No separate PROMPT_0 guardrails file is needed because the PROMPT-0 files are self-contained.

---

## 4. Rite Switching Protocol

Rite changes require full Claude restart in the worktree:

```bash
# In the worktree BEFORE launching claude:
ari sync --rite=<rite-name>
# Then start claude fresh
claude
```

**Switch schedule**:

| Transition | When | Lane | From | To |
|-----------|------|------|------|-----|
| Switch 1 | Phase A -> Phase B | Lane 2 | hygiene | 10x-dev |
| Switch 2 | Phase B -> Phase B.2 | Lane 2 | 10x-dev | rnd |
| Switch 3 | Phase B -> Phase C | Lane 1 | hygiene | slop-chop |

**Optimization**: Lane 1 stays on hygiene through Phases A and B (WS-PARAM S1 + S2), then switches once to slop-chop for Phase C. Lane 2 is the "multi-rite lane" handling the 10x-dev and rnd work.

---

## 5. Scope Boundary Contracts

These contracts prevent file-level conflicts between parallel sessions.

| Lane 1 | Lane 2 | Overlap Risk | Resolution |
|--------|--------|-------------|------------|
| WS-PARAM S1 (8 test files in dataframes, api, clients, persistence, models) | WS-EXCEPT (8 test files in clients, models, resolution, persistence, query, cache) | **LOW** -- 1 potential overlap: `test_cascade.py` in persistence appears in both LS-014 (PARAM) and LS-026 (EXCEPT) | Verify at dispatch: LS-014 targets `test_models.py` (clients/data), not `test_cascade.py`. Zero actual overlap confirmed. |
| WS-PARAM S2 (8 test files in clients, api, automation) | WS-INTEG (1-2 files in tests/integration/api/) | **NONE** -- PARAM touches unit tests only; INTEG creates new integration test files | N/A |

---

## 6. Quality Gates

### Per-Phase Verification

**Phase A exit gate**:
```bash
# After merging WS-EXCEPT:
grep -rn "pytest.raises(Exception)" \
  tests/unit/clients/data/test_retry.py \
  tests/unit/models/test_common_models.py \
  tests/unit/resolution/test_result.py \
  tests/unit/persistence/test_cascade.py \
  tests/unit/dataframes/test_cache_integration.py \
  tests/unit/query/test_section_edge_cases.py \
  tests/unit/query/test_join.py \
  tests/unit/cache/test_edge_cases.py
# Expected: 0 matches
```

**Phase B exit gate**:
```bash
# After merging WS-PARAM S2 -- verify test count stable:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/unit/ -n auto -q --tb=short

# After merging WS-INTEG -- verify new tests pass:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/api/test_preload_manifest_check.py -v --tb=short
```

**Phase C exit gate**:
```bash
# Verify P2 gate verdict exists:
test -f .claude/wip/SLOP-CHOP-TESTS-P2/phase5-verdict/GATE-VERDICT.md

# Full suite on main:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/ -n auto -q --tb=short
```

---

## 7. Session Launch Quick Reference

### Phase A, Lane 1: WS-PARAM S1

```bash
ari worktree create "ws-param"
cd <worktree-path>
ari sync --rite=hygiene
claude
```
```
@.claude/wip/ASANA-HYGIENE/WS-PARAM-PROMPT-0.md

Execute WS-PARAM Session 1: Parametrize 8 copy-paste clusters (LS-011 to LS-016, LS-019, LS-020).
Follow the execution plan in the PROMPT-0. Capture LOC baseline before starting.
Emit checkpoint file at .claude/wip/ASANA-HYGIENE/WS-PARAM-CHECKPOINT.md when done.
```

### Phase A, Lane 2: WS-EXCEPT

```bash
ari worktree create "ws-except"
cd <worktree-path>
ari sync --rite=hygiene
claude
```
```
@.claude/wip/ASANA-HYGIENE/WS-EXCEPT-PROMPT-0.md

Execute WS-EXCEPT: Replace 16 broad pytest.raises(Exception) with specific types.
Follow the execution plan in the PROMPT-0. Work through LS-025, LS-026, LS-027 in order.
```

### Phase B, Lane 1: WS-PARAM S2

```bash
# Reuse ws-param worktree if still alive, or create new after merging S1
cd <worktree-path> && claude
```
```
@.claude/wip/ASANA-HYGIENE/WS-PARAM-PROMPT-0.md

Execute WS-PARAM Session 2: Parametrize remaining 8 clusters (LS-009, LS-010, LS-017, LS-018, LS-021 to LS-024).
See checkpoint at .claude/wip/ASANA-HYGIENE/WS-PARAM-CHECKPOINT.md for S1 results.
Run full unit test suite after all 8 clusters.
```

### Phase B, Lane 2: WS-INTEG

```bash
ari worktree create "ws-integ"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```
```
@.claude/wip/ASANA-HYGIENE/WS-INTEG-PROMPT-0.md

Execute WS-INTEG: Write integration tests for preload manifest check logic.
Follow the execution plan in the PROMPT-0.
```

### Phase B.2, Lane 2: WS-OVERMOCK

```bash
ari worktree create "ws-overmock"
cd <worktree-path>
ari sync --rite=rnd
claude
```
```
@.claude/wip/ASANA-HYGIENE/WS-OVERMOCK-PROMPT-0.md

Execute WS-OVERMOCK: Investigate high-patch tests (LS-028, LS-029). 1-hour time-box.
Write findings to .claude/wip/ASANA-HYGIENE/WS-OVERMOCK-FINDINGS.md.
```

### Phase C, Lane 1: WS-SLOP2

```bash
ari worktree create "ws-slop2"
cd <worktree-path>
ari sync --rite=slop-chop
claude
```
```
@.claude/wip/ASANA-HYGIENE/WS-SLOP2-PROMPT-0.md

Execute WS-SLOP2: Full slop-chop quality gate on tests/integration/, tests/validation/,
tests/benchmarks/. Verify pre-conditions (WS-PARAM + WS-EXCEPT merged to main) before
starting Phase 1. Use /go to activate the slop-chop rite pipeline.
```

---

## 8. Checkpoint Protocol (Multi-Session Workstreams)

Only WS-PARAM spans 2 sessions. The checkpoint file lives at:
`.claude/wip/ASANA-HYGIENE/WS-PARAM-CHECKPOINT.md`

**Written by**: WS-PARAM S1 session (at session wrap)
**Read by**: WS-PARAM S2 session (at session start via @-reference or MEMORY.md)
**Schema**:

```markdown
# WS-PARAM Session 1 Checkpoint
## Completed: [list cluster IDs with file, LOC delta, test count]
## LOC Delta: Baseline {N} -> After S1 {N} = -{N} lines
## Skipped: [cluster IDs with rationale, if any]
## Session 2 Scope: LS-009, LS-010, LS-017, LS-018, LS-021-024
## Observations: [patterns or gotchas for S2]
```

**Hub thread writes to MEMORY.md** after merging S1 branch:
```markdown
## Checkpoint WS-PARAM [date]
Completed: S1 (8 clusters: LS-011 to LS-016, LS-019, LS-020)
Remaining: S2 (8 clusters: LS-009, LS-010, LS-017, LS-018, LS-021-024)
LOC delta: -{N} lines so far
Test status: {N} passed, stable
```

WS-SLOP2 may also need checkpoints between its 2-3 sessions. These follow the same pattern, written to `.claude/wip/SLOP-CHOP-TESTS-P2/CHECKPOINT.md`.

---

## 9. Escalation Protocol

### When Worktree Sessions Should Escalate to Hub

| WS-ID | Escalation Trigger | Action |
|-------|-------------------|--------|
| WS-PARAM | Cluster has behavioral differences beyond the parameter (not a true parametrize candidate) | Skip the cluster, document in checkpoint, hub decides in review |
| WS-PARAM | Test count changes after parametrization (should be stable) | Stop, investigate, document |
| WS-EXCEPT | `pytest.raises(Exception)` is intentional (production raises truly any exception) | Use the narrowest base class available, document reasoning |
| WS-INTEG | `process_project` has side effects that prevent test isolation | Extract testable seam, document approach |
| WS-OVERMOCK | Investigation exceeds 1-hour time-box | Write what you have, recommend DEFER-TO-D027 |
| WS-SLOP2 | Finding count exceeds 50 | Prioritize DEFECT items, defer SMELL to future workstream |
| WS-SLOP2 | Pre-conditions not met (WS-PARAM or WS-EXCEPT not yet merged) | STOP immediately, report to hub |

---

## 10. Merge Protocol

### Sequential Merge Order

After each session completes:

```bash
# 1. In main project directory
cd /Users/tomtenuta/Code/autom8y-asana

# 2. Ensure main is clean
git status

# 3. Merge worktree branch
git merge <worktree-branch>

# 4. If conflicts: resolve manually (expected to be trivial per scope contracts)

# 5. Run scoped tests to verify
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/unit/ -n auto -q --tb=short

# 6. Update TRACKER.md (mark workstream status, log merge)

# 7. Update MEMORY.md (paste checkpoint/completion from session output)

# 8. Remove worktree
ari worktree remove "<worktree-id>"
```

### Parallel Merge Safety

When 2 lanes complete close together, merge sequentially:
```
Lane 1 completes -> merge Lane 1 -> run tests -> update docs
Lane 2 completes -> merge Lane 2 -> run tests -> update docs
```

Never merge two worktree branches simultaneously.

---

## 11. Hub Thread Responsibilities

The hub thread (your main terminal) is the consciousness of the initiative. It does NOT execute workstream code.

**Between dispatches**:
1. Monitor worktree git status for completion signals
2. Merge completed branches to main (Section 10)
3. Update TRACKER.md with status changes
4. Update MEMORY.md with checkpoint/completion entries
5. Evaluate phase exit criteria (Section 6)
6. Select and dispatch next phase workstreams

**Phase transitions**:
1. Verify all exit criteria for current phase
2. Switch rites in worktree if needed (Section 4)
3. Launch next phase sessions with appropriate prompts (Section 7)

**Initiative completion**:
1. All 5 workstreams merged or documented
2. P1 gate verdict upgraded to PASS (WS-HTTPX done, WS-EXCEPT done)
3. P2 gate verdict produced (WS-SLOP2)
4. MEMORY.md updated with initiative summary
5. Archive TRACKER.md final status

---

## 12. Token Budget Summary

| Session | PROMPT-0 Lines | Est. Tokens | Working Budget |
|---------|---------------|-------------|----------------|
| WS-PARAM S1 | 155 | ~700 | ~194K of 200K |
| WS-PARAM S2 | 155 + checkpoint | ~800 | ~194K |
| WS-EXCEPT | 108 | ~500 | ~195K |
| WS-INTEG | 96 | ~450 | ~195K |
| WS-OVERMOCK | 82 | ~400 | ~195K |
| WS-SLOP2 S1-S3 | 113 | ~550 | ~195K |

All sessions have ample headroom. The constraint is scope discipline, not token budget.
