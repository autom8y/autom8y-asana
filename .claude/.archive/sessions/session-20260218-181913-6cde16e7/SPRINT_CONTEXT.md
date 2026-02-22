---
sprint_id: sprint-20260218-stabilization-tail
session_id: session-20260218-181913-6cde16e7
sprint_name: "Stabilization Tail"
sprint_goal: "Execute 3 pre-planned hygiene items: D-022a (pipeline hierarchy placement migration), D-022b (pipeline assignee resolution migration), and Cache Protocol + DI convergence (DataFrameCacheProtocol + singleton removal)"
initiative: "Stabilization Tail — hygiene pipeline + cache DI"
complexity: SPOT
active_rite: hygiene
workflow: sequential
status: ACTIVE
created_at: "2026-02-18T17:19:13Z"
schema_version: "1.0"
tasks:
  - id: task-001
    name: "D-022a: Migrate pipeline.py hierarchy placement to resolve_holder_async"
    description: "Migrate _place_in_hierarchy_async in pipeline.py to use resolve_holder_async. Pre-planned from PIPELINE-PARITY-ANALYSIS.md D-022a."
    priority: HIGH
    complexity: SPOT
    status: pending
    components:
      - src/autom8_asana/pipeline.py
    artifacts: []
  - id: task-002
    name: "D-022b: Migrate pipeline.py assignee resolution to AssigneeConfig"
    description: "Migrate _set_assignee_from_rep_async in pipeline.py to use the AssigneeConfig pattern. Pre-planned from PIPELINE-PARITY-ANALYSIS.md D-022b."
    priority: HIGH
    complexity: SPOT
    status: pending
    components:
      - src/autom8_asana/pipeline.py
    artifacts: []
  - id: task-003
    name: "Cache DI: Introduce DataFrameCacheProtocol and replace module-level singleton with injection"
    description: "Define DataFrameCacheProtocol, wire it via dependency injection, and remove the module-level singleton. Converges Cache Protocol and DI work identified in the architecture review."
    priority: HIGH
    complexity: SPOT
    status: pending
    components:
      - src/autom8_asana/cache/dataframe_cache.py
    artifacts: []
completed_tasks: 0
total_tasks: 3
---

# Sprint: Stabilization Tail

## Overview

This sprint executes 3 pre-planned hygiene items that were scoped, designed, and deferred for a clean execution pass. No assessment or planning phase is needed — tasks are pre-defined with known scope and approach. Sprint enters directly at execution phase.

## Sprint Goal

Execute 3 pre-planned hygiene items:

1. **D-022a** — Migrate `pipeline.py` hierarchy placement to `resolve_holder_async`
2. **D-022b** — Migrate `pipeline.py` assignee resolution to `AssigneeConfig` pattern
3. **Cache DI** — Introduce `DataFrameCacheProtocol` and replace module-level singleton with injection

## Phase

**Entry phase**: execution (assessment + planning skipped — tasks are pre-planned)

## Tasks

### Task 001: D-022a — Hierarchy Placement Migration
**Status:** pending
**Priority:** HIGH
**Complexity:** SPOT

**Description:**
Migrate `_place_in_hierarchy_async` in `pipeline.py` to use `ctx.resolve_holder_async`. This replaces direct inline hierarchy placement logic with the canonical resolver pattern already established in the codebase.

**Components:**
- `src/autom8_asana/pipeline.py` (lines ~510–598 per PIPELINE-PARITY-ANALYSIS.md)

**Acceptance Criteria:**
- `_place_in_hierarchy_async` delegates to `resolve_holder_async`
- No behavioral regression in hierarchy placement
- Existing tests pass; new test for delegation path if feasible
- Zero regressions in full test suite

---

### Task 002: D-022b — Assignee Resolution Migration
**Status:** pending
**Priority:** HIGH
**Complexity:** SPOT

**Description:**
Migrate `_set_assignee_from_rep_async` in `pipeline.py` to use the `AssigneeConfig` pattern. Aligns pipeline assignee resolution with the canonical config-driven approach used elsewhere in the codebase.

**Components:**
- `src/autom8_asana/pipeline.py` (lines ~600–682 per PIPELINE-PARITY-ANALYSIS.md)

**Acceptance Criteria:**
- `_set_assignee_from_rep_async` uses `AssigneeConfig`
- No behavioral regression in assignee resolution
- Existing tests pass
- Zero regressions in full test suite

---

### Task 003: Cache DI — DataFrameCacheProtocol + Singleton Removal
**Status:** pending
**Priority:** HIGH
**Complexity:** SPOT

**Description:**
Introduce `DataFrameCacheProtocol` as a formal interface for the DataFrame cache, then replace the module-level singleton with dependency injection. This converges two related deferred items from the architecture review.

**Components:**
- `src/autom8_asana/cache/dataframe_cache.py`
- Call sites that currently reference the module-level singleton

**Acceptance Criteria:**
- `DataFrameCacheProtocol` defined with correct interface
- Module-level singleton removed; consumers receive cache via injection
- DI wiring in place (startup/factory layer)
- All existing cache tests pass
- Zero regressions in full test suite

---

## Workflow

**Mode:** Sequential (hygiene rite)
**Entry point:** janitor (execution-first, no assessment/planning phase)

**Agent Flow (abbreviated — SPOT complexity):**
1. **janitor** — Executes tasks 001, 002, 003 in sequence
2. **audit-lead** — Audits results, validates no regressions, provides signoff

## Success Criteria

- All 3 tasks completed with zero regressions
- Full test suite passes after each task
- `pipeline.py` hierarchy and assignee paths use canonical patterns
- `DataFrameCacheProtocol` in place, module-level singleton eliminated
- Audit-lead signoff

## Reference Artifacts

- Pipeline parity analysis: `.claude/wip/PIPELINE-PARITY-ANALYSIS.md` (D-022a, D-022b scope)
- Architecture review opportunities: `.claude/wip/q1_arch/ARCH-REVIEW-1-OPPORTUNITIES.md`

## Status

**Sprint Status:** ACTIVE
**Created:** 2026-02-18T17:19:13Z
**Completed Tasks:** 0 / 3
**Active Task:** None (sprint ready for execution)

---

**Next Steps:**
1. Dispatch janitor for task-001 (D-022a — hierarchy placement migration)
2. Validate with full test suite after each task
3. After task-003, dispatch audit-lead for signoff
