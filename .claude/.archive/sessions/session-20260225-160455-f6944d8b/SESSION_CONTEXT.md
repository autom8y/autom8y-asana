---
schema_version: "2.1"
session_id: session-20260225-160455-f6944d8b
status: ARCHIVED
created_at: "2026-02-25T15:04:55Z"
initiative: COMPAT-PURGE — Backward-Compatibility Shim & Legacy Accommodation Elimination
complexity: INITIATIVE
active_rite: hygiene
rite: hygiene
current_phase: requirements
parked_at: "2026-02-25T15:21:48Z"
parked_reason: auto-parked on Stop
archived_at: "2026-02-25T17:34:55Z"
---



# Session: COMPAT-PURGE — Backward-Compatibility Shim & Legacy Accommodation Elimination

## Overview

Orchestrated hygiene initiative targeting backward-compatibility shims, legacy-caller accommodations, orphaned migration paths, and hardcoded bespoke logic across ~115K LOC async Python/FastAPI codebase with 10,500+ tests.

Rite: `hygiene` (code-smeller -> architect-enforcer -> janitor -> audit-lead)

Execution mode: **Orchestrated** — Pythia coordinates; specialists execute via Task tool.

## Phases

| Phase | Agent | Goal | Status |
|-------|-------|------|--------|
| Phase 0 | Pythia | Pre-flight: inventory targets, scope constraints, risk calibration | pending |
| Code-Smeller | code-smeller | Detect and catalog all compat shims, legacy accommodations, migration paths, bespoke hardcoding | pending |
| Architect-Enforcer | architect-enforcer | Classify findings by risk/impact, define elimination order and guard contracts | pending |
| Janitor | janitor | Execute elimination workstreams (multi-worktree parallel where safe) | pending |
| Audit-Lead | audit-lead | Validate eliminations, confirm no regressions, close the initiative | pending |

## Target Categories

| Category | Description |
|----------|-------------|
| Backward-compat shims | Adapters, wrapper layers, dual-code-paths retained for old callers |
| Legacy-caller accommodations | Logic paths that exist solely to support deprecated external call patterns |
| Orphaned migration paths | Migration code where both source and destination now coexist; source is dead |
| Hardcoded bespoke logic | One-off special-case handling embedded in otherwise generic paths |

## Scope Constraints

- Codebase: ~115K LOC async Python / FastAPI
- Test baseline: 10,500+ tests (no regression tolerance)
- Parallel worktree execution allowed for independent workstreams
- Each workstream must have explicit file-scope contracts to avoid merge conflicts
- Deferred items require explicit ADR or debt ledger entry

## Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| PRD | `.claude/wip/COMPAT-PURGE/PRD.md` | pending |
| Smeller Report | `.claude/wip/COMPAT-PURGE/SMELLER-REPORT.md` | pending |
| Elimination Plan | `.claude/wip/COMPAT-PURGE/ELIMINATION-PLAN.md` | pending |
| Workstream Tracker | `.claude/wip/COMPAT-PURGE/TRACKER.md` | pending |
| Audit Report | `.claude/wip/COMPAT-PURGE/AUDIT-REPORT.md` | pending |

## Workstreams

To be defined after Code-Smeller phase completes. Expected shape: multiple parallel workstreams, one per target category or subsystem, each with explicit file-scope contracts.

## Blockers

None.

## Next Steps

1. Run Phase 0 (Pre-flight): inventory shim surface, calibrate risk, confirm agent pantheon readiness
2. Invoke Code-Smeller to scan codebase and produce SMELLER-REPORT
3. Invoke Architect-Enforcer to classify findings and produce ELIMINATION-PLAN
4. Dispatch Janitor workstreams (parallel where dependencies allow)
5. Invoke Audit-Lead for post-execution validation and initiative close
