# WS-SLOP2: Slop-Chop Partition 2

**Scope**: tests/{integration,validation,benchmarks}
**Estimated Effort**: Full orchestrated sprint (1-2 days)
**Dependencies**: WS-HTTPX, WS-PARAM, WS-EXCEPT must be merged to main first
**Lane**: E (final, sequential)
**Rite**: slop-chop (full 6-agent quality gate)

---

## Scope

Run the complete slop-chop quality gate on the remaining test partitions that were not covered in Partition 1. Partition 1 covered `tests/unit/` (389 files, ~184K LOC, 9795 tests). Partition 2 covers:

| Directory | Files | Description |
|-----------|-------|-------------|
| `tests/integration/` | ~40 | Integration tests (API, persistence, cache, preload) |
| `tests/validation/` | ~8 | Validation/schema tests |
| `tests/benchmarks/` | ~4 | Performance benchmarks |
| `tests/_shared/` | ~2 | Shared test utilities (scan for dead code only) |

**Total**: ~54 Python files

---

## Objective

**Done when**:
- All 5 slop-chop phases complete on Partition 2
- GATE-VERDICT.md produced for Partition 2
- All DEFECT findings addressed
- SMELL findings cataloged with cross-rite referrals where appropriate
- Results merged to main

---

## Pre-Conditions

Before starting this workstream:
1. WS-HTTPX merged to main (20 httpx failures resolved)
2. WS-PARAM merged to main (16 clusters parametrized)
3. WS-EXCEPT merged to main (16 broad exceptions tightened)
4. Fresh `git pull` on worktree branch from main

This ensures Partition 2 runs against a clean baseline with all P1 deferred items resolved.

---

## Execution

This workstream runs as a full slop-chop orchestrated session with the standard 6-agent pipeline:

1. **Phase 1 (hallucination-hunter)**: Scan for phantom imports, patch targets, dead API refs
2. **Phase 2 (logic-surgeon)**: Detect tautological tests, assert-free tests, copy-paste, broad catches
3. **Phase 3 (cruft-cutter)**: Detect temporal debt, dead helpers, stale skips
4. **Phase 4 (remedy-smith)**: Produce fixes for all findings
5. **Phase 5 (gate-keeper)**: Issue verdict with before/after metrics

### Invocation

Use `/go` to start a slop-chop session. Target scope:
```
tests/integration/ tests/validation/ tests/benchmarks/
```

---

## Output Artifacts

Produced by the orchestrated session:
- `.claude/wip/SLOP-CHOP-TESTS-P2/phase1-detection/DETECTION-REPORT.md`
- `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT.md`
- `.claude/wip/SLOP-CHOP-TESTS-P2/phase3-decay/DECAY-REPORT.md`
- `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/` (patches)
- `.claude/wip/SLOP-CHOP-TESTS-P2/phase5-verdict/GATE-VERDICT.md`

---

## Constraints

- **Standard slop-chop scope rules apply**: DEFECT = fix, SMELL = defer or fix per sprint capacity
- **No production code changes**: Test-only
- **Benchmark tests are special**: Do not delete or parametrize benchmark tests. Only flag hallucinations or dead code.
- **Shared utilities**: `tests/_shared/` should be scanned for dead code only; do not restructure.

---

## Context References

- **Partition 1 verdict** (for baseline comparison): `.claude/wip/SLOP-CHOP-TESTS-P1/phase5-verdict/GATE-VERDICT.md`
- **Slop-chop rite configuration**: `.claude/ACTIVE_RITE` (current rite definition)
- **Agent prompts**: `.claude/agents/` (all 6 slop-chop agents)

---

## Verification

The slop-chop rite handles its own verification via the gate-keeper agent. The final verdict artifact contains before/after metrics and success criteria evaluation.

Post-merge verification:
```bash
# Full test suite after P2 merge
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest tests/ -n auto -q --tb=short
```
