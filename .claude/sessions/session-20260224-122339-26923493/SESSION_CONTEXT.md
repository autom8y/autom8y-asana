---
schema_version: "2.1"
session_id: session-20260224-122339-26923493
status: PARKED
created_at: "2026-02-24T11:23:39Z"
initiative: 'ASANA_DATA: Wire metrics infrastructure for CLI-driven business metric computation'
complexity: MODULE
active_rite: hygiene
rite: hygiene
current_phase: implementation
parked_at: "2026-02-24T11:24:59Z"
parked_reason: auto-parked on Stop
---


# Session: ASANA_DATA: Wire metrics infrastructure for CLI-driven business metric computation

## Overview

Cross-Cutting session (direct execution, no rite orchestration). Execution-ready: PROMPT_0, REMEDIATION-PLAN, and REMEDIATION-TRACKER already exist.

Oracle: `scripts/calc_mrr.py` -> $96,126. Estimated effort: 1.75 days.

## Workstreams

| WS | Name | Dependency | Status |
|----|------|------------|--------|
| WS-1 | Offline loader | None | pending |
| WS-2 | Classification scope | None | pending |
| WS-3 | Metric definitions | WS-1, WS-2 | pending |
| WS-4 | CLI entry point | WS-3 | pending |

Dependency graph: WS-1 || WS-2 -> WS-3 -> WS-4

## Execution Plan

- Phase 1 (parallel): WS-1 + WS-2
- Phase 2 (sequential): WS-3
- Phase 3 (sequential): WS-4

## Artifacts

- PROMPT_0: `.claude/wip/ASANA_DATA/PROMPT_0.md` (approved)
- REMEDIATION-PLAN: `.claude/wip/ASANA_DATA/REMEDIATION-PLAN.md` (approved)
- REMEDIATION-TRACKER: `.claude/wip/ASANA_DATA/REMEDIATION-TRACKER.md` (active)

## Blockers

None.

## Next Steps

1. Execute WS-1 (offline loader) and WS-2 (classification scope) in parallel
2. Execute WS-3 (metric definitions) after WS-1 and WS-2 complete
3. Execute WS-4 (CLI entry point) after WS-3 completes
4. Validate oracle: `scripts/calc_mrr.py` -> $96,126
