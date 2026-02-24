# REM-HYGIENE Workflow Spec

**Pattern**: sprint-parallel-worktrees (2-lane execution)
**Initiative**: Resolve SLOP-CHOP-TESTS-P2 Blocking Findings
**Workstreams**: 7 (6 P1 blocking + 1 P2/P3 advisory)
**Sessions**: 7-9 total across 4 phases
**Parallelism**: 2 concurrent worktrees max
**Rite switches**: 1 total (hygiene -> 10x-dev for Lane 2 in Phase A)

---

## 1. Sprint Overview

Resolve all 13 P1 blocking DEFECT findings from the SLOP-CHOP-TESTS-P2 quality gate. Five AUTO patches applied mechanically, eight MANUAL items implemented with behavioral assertions. Phase D addresses P2/P3 advisory items opportunistically.

**Test baseline**: 10,492 passed, 178 failed (all pre-existing), 46 skipped

---

## 2. Phase Sequencing

### Phase A: AUTO Patches + First P1 Batch (2 lanes)

| Lane | WS-ID | Sessions | Rite | Complexity | Est. Time |
|------|-------|----------|------|------------|-----------|
| 1 | WS-AUTO, then WS-CFVAL | 1+1 | hygiene, then 10x-dev | SPOT, then MODULE | 30m + 3h |
| 2 | WS-WSISO | 1 | 10x-dev | MODULE | 3h |

**Entry criteria**: Initiative start
**Exit criteria**: WS-AUTO + WS-CFVAL + WS-WSISO all merged to main

Lane 1 starts with WS-AUTO (30 min, hygiene SPOT), then immediately switches to WS-CFVAL (10x-dev MODULE). Lane 2 dispatches WS-WSISO (10x-dev MODULE) in parallel with WS-AUTO.

### Phase B: Second P1 Batch (2 lanes)

| Lane | WS-ID | Sessions | Rite | Complexity | Est. Time |
|------|-------|----------|------|------------|-----------|
| 1 | WS-SSEDGE | 1 | 10x-dev | MODULE | 4h |
| 2 | WS-HYDRA, then WS-LIVEAPI | 1+1 | 10x-dev | SPOT, then MODULE | 1h + 2h |

**Entry criteria**: Phase A merged
**Exit criteria**: WS-SSEDGE + WS-HYDRA + WS-LIVEAPI all merged to main

### Phase C: Quality Gate Re-Run (hub only)

**Entry criteria**: All 13 P1 items merged to main
**Exit criteria**: P2 quality gate re-run produces PASS (exit code 0, 0 blocking findings)

Hub thread re-runs the P2 quality gate on main. If PASS: initiative P1 objective met. If CONDITIONAL-PASS: diagnose and fix remaining items in a spot session.

### Phase D: Advisory Cleanup (optional, 2 lanes)

| Lane | WS-ID | Sessions | Rite | Complexity | Est. Time |
|------|-------|----------|------|------------|-----------|
| 1 | WS-ADVISORY batch 1 | 1 | hygiene | MODULE | 2-3h |
| 2 | WS-ADVISORY batch 2 | 1 | hygiene | MODULE | 2-3h |

**Entry criteria**: Phase C PASS
**Exit criteria**: Advisory items addressed or documented as deferred

---

## 3. Worktree Lifecycle Protocol

Each worktree session follows this exact sequence:

```
 1. HUB:       ari worktree create "<ws-name>"
 2. HUB:       cd <worktree-path>
 3. TERMINAL:  ari sync --rite=<rite-name>  (if rite differs from current)
 4. TERMINAL:  claude
 5. WORKTREE:  @.claude/wip/REM-HYGIENE/WS-{ID}-PROMPT-0.md
               <session prompt from Section 7 below>
 6. WORKTREE:  (autonomous execution per PROMPT-0)
 7. WORKTREE:  /wrap
 8. HUB:       cd /Users/tomtenuta/Code/autom8y-asana
 9. HUB:       git merge <worktree-branch>
10. HUB:       Run scoped tests (see Section 6)
11. HUB:       Update TRACKER.md + MEMORY.md
12. HUB:       safe-wt-remove (see below)
```

### Safe Worktree Removal Protocol

**CRITICAL**: NEVER force-remove worktrees without checking for uncommitted changes. Data was lost on 2026-02-24 from force-removing worktrees with active uncommitted work.

```bash
# Step 1: Check for uncommitted changes
git -C <worktree-path> status --porcelain -- src/ tests/

# Step 2: If output is EMPTY, safe to remove:
ari worktree remove "<worktree-id>"

# Step 3: If output is NON-EMPTY, DO NOT REMOVE. Instead:
#   a. Commit or stash the changes in the worktree
#   b. Merge or cherry-pick to main
#   c. THEN remove the worktree
```

This protocol is mandatory for every worktree removal. No subagent recommendation overrides this rule.

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
| Switch 1 | Phase A, after WS-AUTO | Lane 1 | hygiene | 10x-dev |

**Optimization**: WS-AUTO is the only hygiene SPOT session. All remaining P1 workstreams use 10x-dev. Lane 2 starts directly in 10x-dev. Lane 1 switches once after WS-AUTO completes.

---

## 5. Scope Boundary Contracts

These contracts prevent file-level conflicts between parallel sessions.

### Phase A Scope Boundaries

| WS-AUTO (Lane 1, first 30 min) | Files |
|------|-------|
| RS-008 | `tests/integration/test_custom_field_type_validation.py` (lines 493-501 ONLY) |
| RS-010 | `tests/integration/test_entity_write_smoke.py` (line 995) |
| RS-019 | `tests/integration/test_unified_cache_integration.py` (lines 594, 624) |
| RS-021 | `tests/integration/test_platform_performance.py` (line 236) |
| RS-024 | `tests/validation/persistence/test_concurrency.py` (line 212) |

**Note**: WS-AUTO touches test_custom_field_type_validation.py lines 493-501. WS-CFVAL touches lines 14-519 (the remaining 26 functions). Zero overlap because WS-AUTO completes and merges BEFORE WS-CFVAL dispatches.

| Lane 1: WS-CFVAL | Lane 2: WS-WSISO | Overlap |
|------------------|------------------|---------|
| `tests/integration/test_custom_field_type_validation.py` | `tests/integration/test_workspace_switching.py` | **NONE** |

### Phase B Scope Boundaries

| Lane 1: WS-SSEDGE | Lane 2: WS-HYDRA + WS-LIVEAPI | Overlap |
|------------------|-------------------------------|---------|
| `tests/integration/test_savesession_edge_cases.py`, `tests/integration/test_savesession_partial_failures.py` | `tests/integration/test_hydration.py`, `tests/integration/persistence/test_live_api.py` | **NONE** |

---

## 6. Quality Gates

### Per-Workstream Verification

Each workstream session runs scoped verification before /wrap. Commands are embedded in the PROMPT-0 files.

### Phase Gate Verification (hub thread)

**Phase A exit gate** (after all 3 merges):
```bash
# Verify WS-AUTO patches applied:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/integration/test_custom_field_type_validation.py::TestValidationEdgeCases::test_boolean_accepted_as_number \
  tests/integration/test_entity_write_smoke.py::test_process_has_descriptors \
  tests/integration/test_unified_cache_integration.py::TestPerformanceTiming \
  tests/integration/test_platform_performance.py::TestHierarchyAwareResolver::test_resolve_batch_caches_results \
  "tests/validation/persistence/test_concurrency.py" -k "test_concurrent_graph" \
  -v --tb=short

# Verify WS-CFVAL assertions exist:
grep -c "assert" tests/integration/test_custom_field_type_validation.py
# Expected: >> 26 (was ~1 before)

# Verify WS-WSISO is no longer pass-only:
grep -c "pass$" tests/integration/test_workspace_switching.py
# Expected: 0 (was 4 before)
```

**Phase B exit gate** (after all 3 merges):
```bash
# Full integration test suite:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/integration/ tests/validation/ -n auto -q --tb=short
```

**Phase C quality gate** (re-run):
```bash
# Full suite on main:
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/ -n auto -q --tb=short
```

---

## 7. Session Launch Quick Reference

### Phase A, Lane 1 (first): WS-AUTO

```bash
ari worktree create "ws-auto"
cd <worktree-path>
ari sync --rite=hygiene
claude
```
```
@.claude/wip/REM-HYGIENE/WS-AUTO-PROMPT-0.md

Execute WS-AUTO: Apply 5 diff-ready AUTO patches (RS-008, RS-010, RS-019, RS-021, RS-024).
Follow the PROMPT-0. Verify each patch with the specified test command.
```

### Phase A, Lane 1 (second, after WS-AUTO merge): WS-CFVAL

```bash
ari worktree create "ws-cfval"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```
```
@.claude/wip/REM-HYGIENE/WS-CFVAL-PROMPT-0.md

Execute WS-CFVAL: Add behavioral get-back assertions to 26 assert-free test functions
in test_custom_field_type_validation.py. Follow the PROMPT-0.
```

### Phase A, Lane 2: WS-WSISO

```bash
ari worktree create "ws-wsiso"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```
```
@.claude/wip/REM-HYGIENE/WS-WSISO-PROMPT-0.md

Execute WS-WSISO: Implement behavioral tests or named skips for 8 workspace switching tests.
Follow the PROMPT-0.
```

### Phase B, Lane 1: WS-SSEDGE

```bash
ari worktree create "ws-ssedge"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```
```
@.claude/wip/REM-HYGIENE/WS-SSEDGE-PROMPT-0.md

Execute WS-SSEDGE: Implement behavioral SaveSession assertions for 10 tests
across test_savesession_edge_cases.py and test_savesession_partial_failures.py.
Follow the PROMPT-0.
```

### Phase B, Lane 2 (first): WS-HYDRA

```bash
ari worktree create "ws-hydra"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```
```
@.claude/wip/REM-HYGIENE/WS-HYDRA-PROMPT-0.md

Execute WS-HYDRA: Fix the dead traversal test in test_hydration.py.
Follow the PROMPT-0.
```

### Phase B, Lane 2 (second, after WS-HYDRA merge): WS-LIVEAPI

```bash
ari worktree create "ws-liveapi"
cd <worktree-path>
ari sync --rite=10x-dev
claude
```
```
@.claude/wip/REM-HYGIENE/WS-LIVEAPI-PROMPT-0.md

Execute WS-LIVEAPI: Promote or delete the dead string-literal test suite in test_live_api.py.
Follow the PROMPT-0.
```

### Phase D (optional): WS-ADVISORY

```bash
ari worktree create "ws-advisory"
cd <worktree-path>
ari sync --rite=hygiene
claude
```
```
@.claude/wip/REM-HYGIENE/WS-ADVISORY-PROMPT-0.md

Execute WS-ADVISORY: Address P2/P3 advisory items grouped by file.
Follow the PROMPT-0. Work through items in priority order.
```

---

## 8. Checkpoint Protocol

Most workstreams are single-session (SPOT or short MODULE). Only WS-SSEDGE and WS-ADVISORY might need checkpoints if they span sessions.

**Schema** (for any multi-session workstream):

```markdown
# WS-{ID} Checkpoint

## Completed
- [list RS-IDs with file, test count, status]

## LOC Delta
- Before: {N} lines
- After: {N} lines

## Skipped (if any)
- RS-{ID}: [reason]

## Remaining Scope
- [list RS-IDs still to address]

## Observations
- [patterns or gotchas for next session]
```

---

## 9. Escalation Protocol

| WS-ID | Escalation Trigger | Action |
|-------|-------------------|--------|
| WS-CFVAL | CustomFieldAccessor.get() does not return the stored value (different representation) | Read source to determine correct assertion form; document decision |
| WS-WSISO | Workspace isolation logic does not exist in production code | Convert stubs to named `pytest.mark.skip(reason=...)` with explicit description |
| WS-SSEDGE | SaveSession.preview() return type is opaque or undocumented | Read session.py source to determine assertion targets |
| WS-SSEDGE | commit_async() does not raise SaveSessionError on configured mock failures | Read error propagation path in session.py; document correct mock setup |
| WS-HYDRA | _traverse_upward_async is not callable from test scope | Add necessary import; document the import path |
| WS-LIVEAPI | Coverage verification shows test_action_batch_integration.py does NOT cover the same scenarios | Choose Option A (promote); guard with skipif for credentials |
| WS-ADVISORY | Item count exceeds session budget | Prioritize P2 items, defer P3 to future workstream, document |

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
  python -m pytest tests/integration/ tests/validation/ -n auto -q --tb=short

# 6. Update TRACKER.md (mark workstream status, log merge commit)

# 7. Update MEMORY.md (paste checkpoint/completion from session output)

# 8. Safe worktree removal (Section 3)
git -C <worktree-path> status --porcelain -- src/ tests/
# If empty: ari worktree remove "<worktree-id>"
# If non-empty: DO NOT REMOVE until changes are committed/merged
```

### Parallel Merge Safety

When 2 lanes complete close together, merge sequentially:
```
Lane 1 completes -> merge Lane 1 -> run tests -> update docs
Lane 2 completes -> merge Lane 2 -> run tests -> update docs
```

Never merge two worktree branches simultaneously.

### Merge even for CONDITIONAL-PASS results

If a workstream resolves most but not all of its items (e.g., one test needs a different approach), merge what is complete and create a follow-up SPOT session for the remainder. Do not hold entire workstream branches for single unresolved items.

---

## 11. Hub Thread Responsibilities

The hub thread (main terminal) is the consciousness of the initiative. It does NOT execute workstream code.

**Between dispatches**:
1. Monitor worktree git status for completion signals
2. Merge completed branches to main (Section 10)
3. Update TRACKER.md within 5 minutes of any status change
4. Update MEMORY.md with checkpoint/completion entries
5. Evaluate phase exit criteria (Section 6)
6. Select and dispatch next phase workstreams

**Phase transitions**:
1. Verify all exit criteria for current phase
2. Switch rites in worktree if needed (Section 4)
3. Launch next phase sessions with appropriate prompts (Section 7)

**Initiative completion**:
1. All 13 P1 items resolved and merged
2. P2 quality gate re-run produces PASS verdict
3. MEMORY.md updated with initiative summary
4. TRACKER.md archived with final status

---

## 12. Token Budget Summary

| Session | PROMPT-0 Lines | Est. Tokens | Working Budget |
|---------|---------------|-------------|----------------|
| WS-AUTO | ~80 | ~400 | ~195K of 200K |
| WS-CFVAL | ~120 | ~550 | ~195K |
| WS-WSISO | ~120 | ~550 | ~195K |
| WS-SSEDGE | ~150 | ~700 | ~194K |
| WS-HYDRA | ~80 | ~400 | ~195K |
| WS-LIVEAPI | ~100 | ~450 | ~195K |
| WS-ADVISORY | ~130 | ~600 | ~195K |

All sessions have ample headroom. The constraint is scope discipline, not token budget.
