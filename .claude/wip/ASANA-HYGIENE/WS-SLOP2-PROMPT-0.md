# WS-SLOP2 Session Prompt

## Rite & Workflow
- Rite: slop-chop
- Workflow: `/slop-chop`
- Complexity: MODULE
- Sessions: 2-3 (same scale as Partition 1 which used 5 phases across multiple sessions)

## Objective

Run the full slop-chop 5-phase quality gate on `tests/integration/`, `tests/validation/`, and `tests/benchmarks/` (Partition 2). Produce a GATE-VERDICT.md with before/after metrics. Address all DEFECT findings; catalog SMELL findings with cross-rite referrals.

## Context

Partition 1 scanned `tests/unit/` (389 files, ~184K LOC, 9795 tests) and found 28 DEFECT + 40 SMELL + 3 dead helpers. All DEFECT items were addressed. SMELL items were deferred and are being resolved by WS-PARAM, WS-EXCEPT, and WS-INTEG in this ASANA-HYGIENE initiative.

Partition 2 covers the remaining test directories. Expect lower finding density since these are fewer files (~54), but integration tests may have different quality patterns (more mock infrastructure, fewer copy-paste clusters, potentially more hallucinated API references).

- Seed doc: `.claude/wip/ASANA-HYGIENE/WS-SLOP2.md`
- Partition 1 verdict: `.claude/wip/SLOP-CHOP-TESTS-P1/phase5-verdict/GATE-VERDICT.md`
- Agent prompts: `.claude/agents/` (all 6 slop-chop agents)

### Pre-Conditions (MUST be true before starting)

- WS-HTTPX merged to main (commit `10c15db`) -- DONE
- WS-PARAM merged to main
- WS-EXCEPT merged to main
- Fresh branch from main after all merges

If any pre-condition is not met, STOP and report back to hub thread.

## Scope

### IN SCOPE

**Target directories**:
- `tests/integration/` (~40 files)
- `tests/validation/` (~8 files)
- `tests/benchmarks/` (~4 files)
- `tests/_shared/` (~2 files, scan for dead code only)

**Full 5-phase pipeline**:
1. Phase 1 (hallucination-hunter): phantom imports, patch targets, dead API refs
2. Phase 2 (logic-surgeon): tautological tests, assert-free, copy-paste, broad catches
3. Phase 3 (cruft-cutter): temporal debt, dead helpers, stale skips
4. Phase 4 (remedy-smith): produce and apply fixes for all DEFECT findings
5. Phase 5 (gate-keeper): verdict with before/after metrics, cross-rite referrals

### OUT OF SCOPE

- `tests/unit/` (already scanned in Partition 1)
- Production source code changes
- SMELL findings from Partition 1 (handled by WS-PARAM, WS-EXCEPT)
- Architecture refactoring (handled by REM-ASANA-ARCH)

## Execution Plan

This is a Pythia-coordinated orchestrated session. Use `/go` to start the slop-chop rite.

**Session 1**: Phases 1-3 (scan and detect)
- Hallucination-hunter scans `tests/integration/`, `tests/validation/`, `tests/benchmarks/`
- Logic-surgeon analyzes for all SMELL/DEFECT categories
- Cruft-cutter checks temporal debt

**Session 2**: Phase 4 (remediate)
- Remedy-smith produces fixes for all DEFECT findings from phases 1-3
- Apply AUTO patches, provide MANUAL instructions where needed

**Session 3** (if needed): Phase 5 (verdict)
- Gate-keeper evaluates before/after metrics
- Issues verdict with cross-rite referrals

### Special Handling

- **Benchmark tests**: Do NOT delete or parametrize. Only flag genuine hallucinations or dead code.
- **Shared utilities** (`tests/_shared/`): Scan for dead code only. Do not restructure.
- **Integration test mocking**: Higher mock density is expected and often appropriate in integration tests. Adjust over-mock thresholds accordingly.

## Output Artifacts

Write all phase artifacts to `.claude/wip/SLOP-CHOP-TESTS-P2/`:
- `phase1-detection/DETECTION-REPORT.md`
- `phase2-analysis/ANALYSIS-REPORT.md`
- `phase3-decay/DECAY-REPORT.md`
- `phase4-remediation/` (patches and report)
- `phase5-verdict/GATE-VERDICT.md`

## Verification

Each phase has its own verification gates (managed by the slop-chop agent pipeline).

Post-merge full-suite verification:
```bash
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/ -n auto -q --tb=short
```

## Checkpoint (between sessions)

If the session must split, write checkpoint to `.claude/wip/SLOP-CHOP-TESTS-P2/CHECKPOINT.md`:
- Phases completed
- Findings so far (count by severity)
- Files remaining to scan
- Any blockers or escalations

## Time Budget

- Session 1 (Phases 1-3): ~2-3 hours
- Session 2 (Phase 4): ~2-3 hours
- Session 3 (Phase 5): ~1 hour
- Total: ~5-7 hours across 2-3 sessions

**Risk flag (MEDIUM-HIGH)**: Unknown scope until scan completes. May generate new cross-rite referrals. If finding count exceeds 50, prioritize DEFECT items and defer SMELL to a future workstream rather than trying to address everything in one sprint.
