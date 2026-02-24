# REM-HYGIENE Initiative Manifest

**Objective**: Resolve the 13 blocking DEFECT findings from the SLOP-CHOP-TESTS-P2 quality gate, upgrading the verdict from CONDITIONAL-PASS to PASS. Apply the 5 AUTO patches, implement the 8 MANUAL behavioral fixes, and address high-value P2/P3 advisory items.

**Source**: `.claude/wip/SLOP-CHOP-TESTS-P2/phase5-verdict/GATE-VERDICT.md`

---

## Success Criteria

1. All 13 P1 DEFECT findings resolved (5 AUTO + 8 MANUAL)
2. Re-run of P2 quality gate produces PASS verdict (exit code 0)
3. Zero regressions: test pass count stable or improved from baseline (10,492 passed, 178 pre-existing failures)
4. P2/P3 advisory items addressed where time permits (Phase D)
5. All changes merged to main via sequential merge protocol

---

## Workstream Decomposition

### Phase A -- Blocking (P1 DEFECT, required for merge)

| WS-ID | Name | RS-IDs | Files | Est. Effort | Rite (recommended) | Complexity |
|-------|------|--------|-------|-------------|---------------------|------------|
| WS-AUTO | Apply 5 AUTO patches | RS-008, RS-010, RS-019, RS-021, RS-024 | 5 | 30 min | hygiene (confirm at dispatch) | SPOT |
| WS-CFVAL | Assert-free validation tests | RS-001 | 1 | 3h | 10x-dev (confirm at dispatch) | MODULE |
| WS-WSISO | Workspace switching tests | RS-012, RS-013 | 1 | 3h | 10x-dev (confirm at dispatch) | MODULE |
| WS-SSEDGE | SaveSession edge + partial failures | RS-015, RS-016, RS-017 | 2 | 4h | 10x-dev (confirm at dispatch) | MODULE |
| WS-HYDRA | Dead traversal test | RS-002 | 1 | 1h | 10x-dev (confirm at dispatch) | SPOT |
| WS-LIVEAPI | Dead string-literal test suite | RS-020 | 1 | 2h | 10x-dev (confirm at dispatch) | MODULE |

### Phase D -- Advisory (P2/P3, non-blocking, if time permits)

| WS-ID | Name | RS-IDs | Files | Est. Effort | Rite (recommended) | Complexity |
|-------|------|--------|-------|-------------|---------------------|------------|
| WS-ADVISORY | P2+P3 grouped by file | RS-003, RS-004, RS-006, RS-009, RS-014, RS-018, RS-026, RS-027, RS-031, RS-033 to RS-048 | ~15 | 4-6h | hygiene (confirm at dispatch) | MODULE |

**Total P1 effort**: ~13.5 hours active work across 6 workstreams.

---

## Workstream Merging Rationale

Per the user request to reduce dispatch overhead for small workstreams:

- **WS-SSEDGE** combines RS-015 + RS-016 (test_savesession_edge_cases.py) and RS-017 (test_savesession_partial_failures.py). Both files exercise SaveSession semantics and share mock patterns. Zero file overlap with other workstreams.
- **WS-HYDRA** (RS-002, 1 dead test) and **WS-LIVEAPI** (RS-020, 1 dead suite) remain separate because they touch unrelated code domains (hydration vs. persistence live-API) and different production APIs.

---

## Rite Alignment

All rite assignments are **recommended until dispatch** -- the consultant may adjust at session start.

| WS-ID | Recommended Rite | Rationale |
|-------|-----------------|-----------|
| WS-AUTO | hygiene/SPOT | Mechanically safe patches, no behavioral judgment |
| WS-CFVAL | 10x-dev/MODULE | 26 tests need behavioral get-back assertions; requires reading CustomFieldAccessor source |
| WS-WSISO | 10x-dev/MODULE | Workspace isolation contract implementation; requires understanding workspace/client architecture |
| WS-SSEDGE | 10x-dev/MODULE | SaveSession.preview() and commit_async() behavioral testing; requires reading persistence source |
| WS-HYDRA | 10x-dev/SPOT | Single test needs act+assert phase added; requires reading _traverse_upward_async |
| WS-LIVEAPI | 10x-dev/MODULE | Decision: promote dead string-literal to live tests OR delete after coverage verification |
| WS-ADVISORY | hygiene/MODULE | Mixed P2/P3 items: dead helpers, stale skips, ephemeral comments, copy-paste consolidation |

---

## Parallelism Strategy

**Concurrency**: 2 lanes max (proven pattern from ASANA-HYGIENE and REM-ASANA-ARCH).

**Phase sequencing**:

```
Phase A (parallel, 2 lanes):
  Lane 1: WS-AUTO (30 min) --> WS-CFVAL (3h)
  Lane 2: WS-WSISO (3h)

Phase B (parallel, 2 lanes):
  Lane 1: WS-SSEDGE (4h)
  Lane 2: WS-HYDRA (1h) --> WS-LIVEAPI (2h)

Phase C (quality gate):
  Re-run P2 quality gate on main after all P1 merges

Phase D (advisory, optional, parallel):
  Lane 1: WS-ADVISORY batch 1 (grouped by file)
  Lane 2: WS-ADVISORY batch 2 (grouped by file)
```

**File overlap analysis**: Verified zero file overlap across all parallel pairs. Each workstream targets a distinct test file (or file set) with no shared scope.

| Lane 1 | Lane 2 | Overlap |
|--------|--------|---------|
| WS-AUTO (5 files) | -- (solo) | N/A |
| WS-CFVAL (test_custom_field_type_validation.py) | WS-WSISO (test_workspace_switching.py) | NONE |
| WS-SSEDGE (test_savesession_edge_cases.py, test_savesession_partial_failures.py) | WS-HYDRA (test_hydration.py) + WS-LIVEAPI (test_live_api.py) | NONE |

---

## Scope Boundary

**IN SCOPE**: Resolve all 13 P1 DEFECT findings from SLOP-CHOP-TESTS-P2 gate verdict. Address P2/P3 advisory items in Phase D if time permits.

**OUT OF SCOPE** (do NOT touch):
- Production source code (all changes are test-only, except reading source to understand expected behavior)
- Other debt items (D-001 through D-035, architecture/code debt)
- REM-ASANA-ARCH workstreams (WS-SYSCTX, WS-DSC, WS-DFEX, etc.)
- ASANA-HYGIENE P1 workstreams (all completed)
- Unit test files in tests/unit/ (P1 scope, already addressed)

---

## Artifact References

### Source Reports (read-only context for workstream sessions)
- Gate verdict: `.claude/wip/SLOP-CHOP-TESTS-P2/phase5-verdict/GATE-VERDICT.md`
- Remedy plan: `.claude/wip/SLOP-CHOP-TESTS-P2/phase4-remediation/REMEDY-PLAN.md`
- Analysis (batch 1): `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-integ-batch1.md`
- Analysis (batch 2): `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-integ-batch2.md`
- Analysis (val/bench): `.claude/wip/SLOP-CHOP-TESTS-P2/phase2-analysis/ANALYSIS-REPORT-val-bench.md`
- Decay report: `.claude/wip/SLOP-CHOP-TESTS-P2/phase3-decay/DECAY-REPORT.md`

### Initiative Artifacts
- Manifest: `.claude/wip/REM-HYGIENE/MANIFEST.md` (this file)
- Workflow spec: `.claude/wip/REM-HYGIENE/WORKFLOW-SPEC.md`
- Tracker: `.claude/wip/REM-HYGIENE/TRACKER.md`
- Seed docs: `.claude/wip/REM-HYGIENE/WS-{ID}.md`
- Dispatch prompts: `.claude/wip/REM-HYGIENE/WS-{ID}-PROMPT-0.md`

### Proven Templates (replicated patterns)
- Sprint manifest: `.claude/wip/REM-ASANA-ARCH/SPRINT-MANIFEST.md`
- PROMPT-0 examples: `.claude/wip/ASANA-HYGIENE/WS-PARAM-PROMPT-0.md`
- Workflow spec: `.claude/wip/ASANA-HYGIENE/WORKFLOW-SPEC.md`
