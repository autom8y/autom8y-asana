# Remediation Sprint Launcher: autom8y-asana Architecture

**Source**: DEEP-DIVE architecture analysis completed 2026-02-23
**Health Score**: 68/100 (structurally sound, specific improvements available)
**Codebase**: 115K LOC async Python, 22 subsystems, 10,552+ tests (1.87:1 ratio)
**Artifacts**: `.claude/wip/q1_arch/deep-dive/` (4 files, ~3,100 lines total)

---

## Context for This Session

A 4-phase architecture analysis produced 10 ranked recommendations, 6 cross-rite
referrals, and 10 unknowns. This document decomposes that output into executable
workstreams. Each workstream has a standalone seed file loadable via `@` reference.

**The analysis is complete. Do not re-analyze. Execute from the seeds.**

---

## Architecture Summary (Key Facts)

- Single query router at `api/routes/query.py` (v1/v2 merged, D-012)
- Shared creation primitives in `core/creation.py` (free functions, not classes)
- DataServiceClient decomposed into 7 focused modules in `clients/data/`
- SaveSession is a Coordinator pattern (14 collaborators) -- NOT a god object
- Lifecycle is the canonical pipeline; automation retained for essential differences
- Cache divergence is intentional (12/14 dimensions) -- ADR-0067
- Legacy preload is active degraded-mode fallback -- ADR-011
- D-022 (full pipeline consolidation) CLOSED
- Test baseline: 10,552 passed, 46 skipped, 2 xfailed

### Closed Items (Do NOT Reopen)

| Item | Status | Reference |
|------|--------|-----------|
| D-022 full pipeline consolidation | CLOSED | MEMORY.md, WS6 |
| ADR-0067 cache divergence | CLOSED | `docs/decisions/ADR-0067-*` |
| ADR-011 legacy preload fallback | CLOSED | `docs/decisions/ADR-011-*` |
| SaveSession decomposition | REJECTED | Coordinator pattern confirmed |
| SI-3 circular deps wholesale fix | DEFERRED | Trigger: production incident |

### Guardrails (Apply to All Workstreams)

1. Do NOT decompose SaveSession. It is a well-designed Coordinator.
2. Do NOT re-open cache divergence analysis. ADR-0067 is final.
3. Do NOT pursue full pipeline consolidation. D-022 is closed.
4. Do NOT convert deferred imports wholesale. SI-3 is deferred.
5. Do NOT modify `automation/seeding.py` field seeding strategy. The
   FieldSeeder vs AutoCascadeSeeder divergence is intentional.
6. Run tests after every change. Green-to-green is mandatory.
7. Verify file paths before editing -- WS6 blueprint references drifted.

---

## Workstream Index

### Phase 0: Quick Wins (3-6 hours total)

| WS | Seed | Recs | Rite | Effort | Complexity |
|----|------|------|------|--------|------------|
| WS-QW | `@.claude/wip/REM-ASANA-ARCH/WS-QW.md` | R-001, R-002, R-003, R-007 | hygiene | 3-6 hrs | PATCH |

### Phase 1: Foundation (4-7 days total, parallelizable)

| WS | Seed | Recs | Rite | Effort | Complexity |
|----|------|------|------|--------|------------|
| WS-SYSCTX | `@.claude/wip/REM-ASANA-ARCH/WS-SYSCTX.md` | R-005 | hygiene | 1-2 days | MODULE |
| WS-DSC | `@.claude/wip/REM-ASANA-ARCH/WS-DSC.md` | R-008 | 10x-dev | 3-5 days | MODULE |

### Phase 2: Consolidation (4-5 days total)

| WS | Seed | Recs | Rite | Effort | Complexity |
|----|------|------|------|--------|------------|
| WS-DFEX | `@.claude/wip/REM-ASANA-ARCH/WS-DFEX.md` | R-006, R-009 | hygiene | 3-3.5 days | MODULE |
| WS-CLASS | `@.claude/wip/REM-ASANA-ARCH/WS-CLASS.md` | R-004 | hygiene | 1 day | PATCH |

### Phase 3: Evolution (4.5 days, opportunistic)

| WS | Seed | Recs | Rite | Effort | Complexity |
|----|------|------|------|--------|------------|
| WS-QUERY | `@.claude/wip/REM-ASANA-ARCH/WS-QUERY.md` | R-010 | 10x-dev | 3 days | MODULE |

### Cross-Rite Referrals (Independent)

| WS | Seed | Items | Rite | Effort | Complexity |
|----|------|-------|------|--------|------------|
| WS-HYGIENE | `@.claude/wip/REM-ASANA-ARCH/WS-HYGIENE.md` | XR-001..006 | hygiene | 3-4 days | PATCH/MODULE |
| WS-DEBT | `@.claude/wip/REM-ASANA-ARCH/WS-DEBT.md` | XR-002, D-002 | debt-triage | 1-2 days | PATCH |

---

## Dependency Graph (Summary)

```
Phase 0: WS-QW .................. (independent, do first)

Phase 1: WS-SYSCTX ─┐
         WS-DSC ────┤ (parallel, no dependencies)
                    │
Phase 2: WS-DFEX ──┤ (cleaner after WS-SYSCTX, not blocked)
         WS-CLASS ──┤ (blocked on U-002 resolution)
                    │
Phase 3: WS-QUERY ──┘ (after WS-DFEX for clean service boundaries)

Cross-Rite: WS-HYGIENE, WS-DEBT (independent, any phase)
```

Full graph: `@.claude/wip/REM-ASANA-ARCH/DEPENDENCY-GRAPH.md`

---

## Unknowns (Resolve Before or During Sprints)

10 unknowns documented in the analysis. Most resolve in under 5 minutes.

Quick-resolution guide: `@.claude/wip/REM-ASANA-ARCH/UNKNOWNS-RESOLUTION.md`

| ID | Summary | Resolves Via | Blocks |
|----|---------|--------------|--------|
| U-001 | Does lifecycle handle all automation scenarios? | Feature comparison | Long-term planning |
| U-002 | Classification rule change frequency | `git blame activity.py` | WS-CLASS |
| U-003 | conversation_audit.py bootstrap guard status | Read one file | WS-QW (R-001) |
| U-004 | Query v1 consumer inventory | API access logs | WS-DEBT |
| U-005 | Deferred import cold-start latency | CloudWatch profiling | Nothing immediate |
| U-006 | system_context.py design intent | ARCH-REVIEW-1 S3.1 | WS-SYSCTX |
| U-007 | cloudwatch.py bootstrap status | Read one file | WS-QW (R-007) |
| U-008 | Pre-existing test failures status | Run 2 tests | WS-HYGIENE |
| U-009 | Internal/admin router inventory | Read 2 files | Nothing |
| U-010 | Polling CLI deployment status | Check infra config | Nothing |

---

## How to Use This Package

### Starting a Workstream

1. Start a fresh Claude Code session
2. Reference this file: `@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md`
3. Load the specific workstream seed: `@.claude/wip/REM-ASANA-ARCH/WS-QW.md`
4. Start the sprint: `/start "WS-QW: Quick Wins" --complexity=PATCH`
5. Execute the implementation sketch in the seed file

### Resolving Unknowns

Load `@.claude/wip/REM-ASANA-ARCH/UNKNOWNS-RESOLUTION.md` and execute the
one-liner commands. Update this file and MEMORY.md with results.

### Referencing Analysis Detail

When a workstream seed says "See ARCHITECTURE-REPORT.md Section 4, R-005",
load: `@.claude/wip/q1_arch/deep-dive/ARCHITECTURE-REPORT.md`

The four analysis artifacts are:
- `TOPOLOGY-INVENTORY.md` -- subsystem map, API surfaces, entry points
- `DEPENDENCY-MAP.md` -- coupling scores, circular deps, data flows
- `ARCHITECTURE-ASSESSMENT.md` -- anti-patterns, boundary alignment, risk register
- `ARCHITECTURE-REPORT.md` -- ranked recommendations, phased roadmap, migration readiness

Load these only when the workstream seed references a specific section.

### Prior Art (Already in Repo)

- Debt ledger: `docs/debt/LEDGER-cleanup-modernization.md`
- Risk matrix: `docs/debt/RISK-MATRIX-cleanup-modernization.md`
- Patterns guide: `docs/guides/patterns.md`
- Entry-point audit: `.claude/wip/ENTRY-POINT-AUDIT.md`
- Pipeline parity: `.claude/wip/PIPELINE-PARITY-ANALYSIS.md`
- PII contract: `.claude/wip/SECURITY-PII-REDACTION-CONTRACT.md`
- Gap synthesis: `docs/architecture/ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md`

---

## Session Lifecycle Notes

- MEMORY.md already contains key architecture facts. Fresh sessions inherit this.
- Each workstream is sized for 1 session (WS-QW, WS-CLASS, WS-DEBT) or 2-3
  sessions (WS-SYSCTX, WS-DSC, WS-DFEX, WS-QUERY, WS-HYGIENE).
- For multi-session workstreams, emit a checkpoint at the end of each session:
  ```
  ## Checkpoint [WS-ID] [date]
  Completed: [list]
  Remaining: [list]
  Decisions: [list with rationale]
  Test status: [pass/fail count]
  ```
- After completing a workstream, update MEMORY.md with the outcome.

---

## Total Estimated Effort

| Phase | Effort | Workstreams |
|-------|--------|-------------|
| Phase 0 | 3-6 hours | WS-QW |
| Phase 1 | 4-7 days | WS-SYSCTX, WS-DSC |
| Phase 2 | 4-5 days | WS-DFEX, WS-CLASS |
| Phase 3 | 3 days | WS-QUERY |
| Cross-Rite | 4-6 days | WS-HYGIENE, WS-DEBT |
| **Total** | **~15-22 engineer-days** | 8 workstreams |

Phase 3 and cross-rite work is opportunistic. Phases 0-2 are the core investment.
