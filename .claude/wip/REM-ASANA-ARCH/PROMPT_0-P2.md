# Phase 2 Remediation Sprint Launcher: autom8y-asana Architecture

**Source**: Phase 2 Gap Analysis completed 2026-02-24
**Health Score**: 83/100 (Phase 1 raised from 68, Phase 2 targets 92+)
**Codebase**: 115K LOC async Python, 22 subsystems, 11,123+ tests
**Phase 1 Artifacts**: `.claude/wip/REM-ASANA-ARCH/` (Phase 1 complete, archived)
**Phase 2 Artifacts**: This file + `WS-P2-{01..04}.md` seeds

---

## Phase 1 Completion Summary (68 -> 83)

Phase 1 completed 2026-02-24 in ~10 hours (original estimate 14-20 days).
7/7 workstreams done (WS-CLASS skipped). 9 clean merges, zero conflicts.

**Delivered**:
- 3 dependency cycles addressed: Cycle 5 fully clean (cache->api), Cycles 1 and 4 partially reduced
- 4 protocols on main: EndpointPolicy, InsightsProvider, MetricsEmitter, DataFrameProvider
- SystemContext registration pattern (register_reset), HOLDER_REGISTRY self-registration
- DataServiceClient 5 endpoints via EndpointPolicy (40% LOC reduction, 420 tests)
- QueryEngine decoupled via DataFrameProvider

**Corrected finding**: Original review counted "6 cycles." Spike found **13 bidirectional 2-cycles**.
Phase 1 fully cleaned 1 (Cycle 5), partially addressed 2 (Cycles 1, 4). Phase 2 targets 5 more
surgical cuts from the remaining 12. The other 7 are structural (skip).

---

## Context for This Session

The Phase 2 gap analysis produced 8 gaps scored by leverage. This sprint executes
the top 6 gaps (G-01 through G-05, G-08) across 3 required sessions, with an optional
4th session for G-07 and G-06.

**The analysis is complete. Do not re-analyze. Execute from the seeds.**
**No Phase 0 pre-flight needed. The gap analysis IS the pre-flight.**

---

## Architecture Summary (Key Facts -- Unchanged from Phase 1)

- Single query router at `api/routes/query.py` (v1/v2 merged, D-012)
- Shared creation primitives in `core/creation.py` (free functions, not classes)
- DataServiceClient decomposed into 7 focused modules in `clients/data/`
- SaveSession is a Coordinator pattern (14 collaborators) -- NOT a god object
- Lifecycle is the canonical pipeline; automation retained for essential differences
- Cache divergence is intentional (12/14 dimensions) -- ADR-0067
- Legacy preload is active degraded-mode fallback -- ADR-011
- D-022 (full pipeline consolidation) CLOSED
- Test baseline: 11,123 passed. 203 pre-existing API contract failures documented.

### Closed Items (Do NOT Reopen)

| Item | Status | Reference |
|------|--------|-----------|
| D-022 full pipeline consolidation | CLOSED | MEMORY.md, WS6 |
| ADR-0067 cache divergence | CLOSED | `docs/decisions/ADR-0067-*` |
| ADR-011 legacy preload fallback | CLOSED | `docs/decisions/ADR-011-*` |
| SaveSession decomposition | REJECTED | Coordinator pattern confirmed |
| SI-3 circular deps wholesale fix | DEFERRED | Trigger: production incident |
| D-001/D-012 query consolidation | CLOSED | Phase 1 WS-QUERY |
| Cycle count "6 -> 3" | CORRECTED | Actual: 13 total, 1 fully clean, 5 targeted in P2 |

### Guardrails (Apply to All Workstreams)

**Original 7 (from Phase 1)**:
1. Do NOT decompose SaveSession. It is a well-designed Coordinator.
2. Do NOT re-open cache divergence analysis. ADR-0067 is final.
3. Do NOT pursue full pipeline consolidation. D-022 is closed.
4. Do NOT convert deferred imports wholesale. SI-3 is deferred.
5. Do NOT modify `automation/seeding.py` field seeding strategy.
6. Run tests after every change. Green-to-green is mandatory.
7. Verify file paths before editing -- WS6 blueprint references drifted.

**Phase 2 additions**:
8. Do NOT attempt to fix all 549 deferred imports. Most are legitimate type-hint guards.
9. Do NOT attempt to eliminate all 13 2-cycles. Target only the 5 surgical ones in G-04.
10. Do NOT decompose automation/ fully. Only Scenario C (pipeline rules -> lifecycle/) if P2-04 runs.
11. Do NOT recreate existing protocols. EndpointPolicy, InsightsProvider, MetricsEmitter,
    DataFrameProvider already exist on main.

---

## Phase 2 Workstream Index

| Session | Seed | Gaps | Rite | Effort | Complexity | Points |
|---------|------|------|------|--------|------------|--------|
| P2-01 | `@.claude/wip/REM-ASANA-ARCH/WS-P2-01.md` | G-01, G-02, G-03 | hygiene | 2 hrs | PATCH | +5 |
| P2-02 | `@.claude/wip/REM-ASANA-ARCH/WS-P2-02.md` | G-04 | 10x-dev | 4-5 hrs | MODULE | +3 |
| P2-03 | `@.claude/wip/REM-ASANA-ARCH/WS-P2-03.md` | G-05, G-08 | hygiene | 2-3 hrs | PATCH | +2 |
| P2-04 (opt) | `@.claude/wip/REM-ASANA-ARCH/WS-P2-04.md` | G-07, G-06 | hygiene | 5 hrs | PATCH/MODULE | +1-2 |

---

## Dependency Graph

```
P2-01 (utility extraction) ............ independent, do first
  |
  v (soft: G-01 helps core<->dataframes cycle cut)
P2-02 (surgical cycle cuts) ........... largest session
  |
  v (hard: G-08 depends on cycles cut in P2-02)
P2-03 (protocol purity + guards) ...... after P2-02

P2-04 (test fixes + reorg) ............ independent, optional, any time
```

---

## Existing Protocols (Already on Main -- Do Not Recreate)

- `src/autom8_asana/clients/data/_policy.py` -- EndpointPolicy
- `src/autom8_asana/protocols/insights.py` -- InsightsProvider
- `src/autom8_asana/protocols/metrics.py` -- MetricsEmitter
- `src/autom8_asana/protocols/dataframe_provider.py` -- DataFrameProvider

---

## Test Commands

- **Full suite**: `AUTOM8Y_ENV=production .venv/bin/python -m pytest tests/ -x`
- **Scoped (during dev)**: `pytest tests/unit/<module>/ -x`
- Full suite runs at QA gates only (end of each session), scoped tests during development

---

## Phase 2 Closed Decisions

- Cycle count corrected from "6 remaining" to "13 total, 12 remaining." 5 targeted surgically, 7 structural (skip).
- 549 deferred imports: reduced 40% from 915 in Phase 1, but remaining are mostly legitimate. Not a target.
- automation/ full decomposition: deferred indefinitely. Only pipeline-rules extraction (Scenario C) considered.
- 160+ NameGid test failures: external API contract issues, not architecture debt.

---

## How to Use This Package

1. Start a fresh Claude Code session in a worktree
2. Reference this file: `@.claude/wip/REM-ASANA-ARCH/PROMPT_0-P2.md`
3. Load the specific session seed: `@.claude/wip/REM-ASANA-ARCH/WS-P2-{NN}.md`
4. Execute the implementation sketch in the seed file
5. Full suite at end only. Update MEMORY.md when done.

### Prior Art (Already in Repo)

- Phase 1 gap analysis: `.claude/wip/REM-ASANA-ARCH/PHASE2-GAP-ANALYSIS.md`
- Phase 1 tracker: `.claude/wip/REM-ASANA-ARCH/TRACKER.md`
- Debt ledger: `docs/debt/LEDGER-cleanup-modernization.md`
- Patterns guide: `docs/guides/patterns.md`
- Remedy report (for P2-04): `.wip/REMEDY-tests-unit-p1.md`

Load these only when the workstream seed references a specific section.
