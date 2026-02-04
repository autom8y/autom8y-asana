---
sprint_id: sprint-cache-hygiene-20260204
session_id: session-20260204-004236-e7de84a6
sprint_name: "Cache Architecture Deep Hygiene — Deferred Smells"
sprint_goal: "Address 4 deferred smell findings from the prior landscape audit (SM-L005, SM-L003/L004, SM-L007, SM-L014)"
initiative: "Cache Architecture Deep Hygiene"
complexity: MODULE
active_rite: hygiene
workflow: sequential
status: pending
created_at: "2026-02-04T00:42:36Z"
schema_version: "1.0"
tasks:
  - id: task-001
    name: "SM-L005: FreshnessInfo side-channel formalization"
    description: "Replace getattr-based side-channel propagation of FreshnessInfo across DataFrameCache → EntityQueryService → QueryEngine with explicit typed return values"
    priority: HIGH
    complexity: MODULE
    status: pending
    components:
      - src/autom8_asana/cache/dataframe_cache.py
      - src/autom8_asana/services/entity_query_service.py
      - src/autom8_asana/query/engine.py
    artifacts: []
  - id: task-002
    name: "SM-L003/L004: Backend error handling extraction"
    description: "Extract duplicated degraded-mode state machine and error classification from Redis, S3, and AsyncS3 backends into shared DegradedModeHandler and error classification utilities"
    priority: MEDIUM
    complexity: FILE
    status: pending
    components:
      - src/autom8_asana/cache/backends/redis.py
      - src/autom8_asana/cache/backends/s3.py
      - src/autom8_asana/cache/backends/async_s3.py
    artifacts: []
  - id: task-003
    name: "SM-L007: build_progressive_async decomposition"
    description: "Decompose 251-line god method into focused private methods (_check_resume, _probe_freshness, _fetch_sections, _merge_and_finalize)"
    priority: HIGH
    complexity: FILE
    status: pending
    components:
      - src/autom8_asana/dataframes/builders/progressive.py
    artifacts: []
  - id: task-004
    name: "SM-L014: Structured logging migration"
    description: "Migrate ~40+ f-string log calls in tiered.py, redis.py, s3.py to structured extra={} pattern"
    priority: MEDIUM
    complexity: MODULE
    status: pending
    components:
      - src/autom8_asana/cache/backends/tiered.py
      - src/autom8_asana/cache/backends/redis.py
      - src/autom8_asana/cache/backends/s3.py
    artifacts: []
completed_tasks: 0
total_tasks: 4
---

# Sprint: Cache Architecture Deep Hygiene — Deferred Smells

## Overview

This sprint addresses 4 deferred code smell findings from the prior cache landscape audit. These smells represent architectural debt that should be resolved to improve maintainability, testability, and system clarity.

## Sprint Goal

Address 4 deferred smell findings from the prior landscape audit:
1. **SM-L005**: FreshnessInfo side-channel formalization (HIGH priority, crosses 3 components)
2. **SM-L003/L004**: Backend error handling extraction (MEDIUM priority)
3. **SM-L007**: `build_progressive_async` decomposition (HIGH priority, 251-line god method)
4. **SM-L014**: Structured logging migration (MEDIUM priority, mechanical)

## Related Artifacts

**Existing Assessment & Plans:**
- Assessment: `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/smell-report-cache-landscape.md`
- Refactoring Plan: `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/refactoring-plan-cache-landscape.md`
- Prior Audit: `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/audit-report-cache-landscape.md`

## Tasks

### Task 001: SM-L005 - FreshnessInfo Side-Channel Formalization
**Status:** pending
**Priority:** HIGH
**Complexity:** MODULE

**Description:**
Replace getattr-based side-channel propagation of FreshnessInfo across the cache→service→engine boundary with explicit typed return values.

**Components:**
- `src/autom8_asana/cache/dataframe_cache.py`
- `src/autom8_asana/services/entity_query_service.py`
- `src/autom8_asana/query/engine.py`

**Scope:**
- Define explicit return types (e.g., `tuple[DataFrame, FreshnessInfo]` or dataclass wrapper)
- Update 3 boundary signatures
- Add type hints and validation
- Update call sites
- Add integration tests for freshness propagation

**Rationale:** Current getattr side-channel is implicit, fragile, and violates explicit-over-implicit principle.

---

### Task 002: SM-L003/L004 - Backend Error Handling Extraction
**Status:** pending
**Priority:** MEDIUM
**Complexity:** FILE

**Description:**
Extract duplicated degraded-mode state machine and error classification logic from Redis, S3, and AsyncS3 backends into shared utilities.

**Components:**
- `src/autom8_asana/cache/backends/redis.py`
- `src/autom8_asana/cache/backends/s3.py`
- `src/autom8_asana/cache/backends/async_s3.py`

**Scope:**
- Create `DegradedModeHandler` class for state machine logic
- Create error classification utilities
- Refactor 3 backends to use shared logic
- Ensure test coverage for error paths
- Validate no behavioral regressions

**Rationale:** Eliminates code duplication and centralizes degraded-mode state management for consistency.

---

### Task 003: SM-L007 - build_progressive_async Decomposition
**Status:** pending
**Priority:** HIGH
**Complexity:** FILE

**Description:**
Decompose 251-line `build_progressive_async` god method into focused private methods for better readability and testability.

**Components:**
- `src/autom8_asana/dataframes/builders/progressive.py`

**Scope:**
- Extract `_check_resume()` - resume validation logic
- Extract `_probe_freshness()` - freshness checking logic
- Extract `_fetch_sections()` - section fetching loop
- Extract `_merge_and_finalize()` - DataFrame merge and metadata assembly
- Update main method to orchestrate extracted methods
- Maintain existing tests (no behavioral changes)
- Add unit tests for extracted private methods if feasible

**Rationale:** 251-line method exceeds cognitive load threshold; decomposition improves testability and maintainability.

---

### Task 004: SM-L014 - Structured Logging Migration
**Status:** pending
**Priority:** MEDIUM
**Complexity:** MODULE

**Description:**
Migrate ~40+ f-string log calls in cache backend files to structured logging pattern with `extra={}`.

**Components:**
- `src/autom8_asana/cache/backends/tiered.py`
- `src/autom8_asana/cache/backends/redis.py`
- `src/autom8_asana/cache/backends/s3.py`

**Scope:**
- Identify all f-string log calls in 3 files
- Convert to structured format: `logger.info("message", extra={"key": value})`
- Ensure log messages remain human-readable
- Validate no log format regressions
- Update any log parsing utilities if needed

**Rationale:** Structured logging enables better observability, searchability, and integration with log aggregation tools.

---

## Workflow

**Mode:** Sequential (hygiene rite default)

**Agent Flow:**
1. **orchestrator** - Coordinates sprint phases
2. **code-smeller** - Re-validates findings, provides smell context
3. **architect-enforcer** - Reviews refactoring plans, enforces architecture standards
4. **janitor** - Executes cleanup and refactoring
5. **audit-lead** - Audits results, validates no regressions

**Entry Point:** orchestrator (initiates hygiene workflow)

## Success Criteria

- All 4 tasks completed with zero regressions
- Test suite passes with no new failures
- Code coverage maintained or improved
- Architecture standards enforced (validated by architect-enforcer)
- Quality signoff from audit-lead
- All artifacts tracked in SESSION_CONTEXT.md

## Notes

- This sprint focuses on technical debt resolution, not new features
- Priority is code quality and maintainability improvements
- All changes must maintain backward compatibility
- Existing test suite must pass without modifications (except for new tests)

## Status

**Sprint Status:** pending
**Created:** 2026-02-04T00:42:36Z
**Completed Tasks:** 0 / 4
**Active Task:** None (sprint not yet started)

---

**Next Steps:**
1. Start sprint via Moirai: `start_sprint sprint_id=sprint-cache-hygiene-20260204`
2. Transition first task to `in_progress`
3. Begin with Task 001 (SM-L005, HIGH priority)
