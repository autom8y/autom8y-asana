---
schema_version: "2.0"
sprint_id: "sprint-materialization-002"
sprint_number: 2
sprint_name: "Core Implementation"
session_id: "session-20251231-134242-00b4d145"
status: "completed"
created_at: "2026-01-01T22:00:00Z"
started_at: "2026-01-01T23:00:00Z"
completed_at: "2026-01-02T01:30:00Z"
timebox_days: 2
depends_on: "sprint-materialization-001"
goal: "Implement WatermarkRepository, incremental sync, S3 persistence, and startup preloading"
tasks:
  - id: "task-001"
    name: "Implement WatermarkRepository"
    status: "completed"
    assigned_to: "principal-engineer"
    complexity: "FEATURE"
    estimated_hours: 4
    started_at: "2026-01-01T23:00:00Z"
    completed_at: "2026-01-01T23:45:00Z"
    artifacts:
      - type: "CODE"
        path: "src/autom8_asana/dataframes/watermark.py"
        status: "completed"
  - id: "task-002"
    name: "Implement incremental refresh in ProjectDataFrameBuilder"
    status: "completed"
    assigned_to: "principal-engineer"
    complexity: "FEATURE"
    estimated_hours: 6
    started_at: "2026-01-01T23:45:00Z"
    completed_at: "2026-01-01T23:55:00Z"
    depends_on: ["task-001"]
    artifacts:
      - type: "CODE"
        path: "src/autom8_asana/dataframes/builders/project.py"
        status: "completed"
  - id: "task-003"
    name: "Implement S3 persistence for GidLookupIndex"
    status: "completed"
    assigned_to: "principal-engineer"
    complexity: "FEATURE"
    estimated_hours: 4
    started_at: "2026-01-01T23:55:00Z"
    completed_at: "2026-01-02T00:15:00Z"
    depends_on: ["task-002"]
    artifacts:
      - type: "CODE"
        path: "src/autom8_asana/dataframes/persistence.py"
        status: "completed"
  - id: "task-004"
    name: "Integrate with resolver and startup preload"
    status: "completed"
    assigned_to: "principal-engineer"
    complexity: "FEATURE"
    estimated_hours: 6
    started_at: "2026-01-02T00:15:00Z"
    completed_at: "2026-01-02T00:45:00Z"
    depends_on: ["task-001", "task-002", "task-003"]
    artifacts:
      - type: "CODE"
        path: "src/autom8_asana/services/resolver.py"
        status: "completed"
      - type: "CODE"
        path: "src/autom8_asana/api/main.py"
        status: "completed"
      - type: "CODE"
        path: "src/autom8_asana/api/routes/health.py"
        status: "completed"
  - id: "task-005"
    name: "Unit tests for new components"
    status: "completed"
    assigned_to: "principal-engineer"
    complexity: "FEATURE"
    estimated_hours: 4
    started_at: "2026-01-02T00:45:00Z"
    completed_at: "2026-01-02T01:30:00Z"
    depends_on: ["task-004"]
    artifacts:
      - type: "TEST"
        path: "tests/unit/test_watermark.py"
        status: "completed"
      - type: "TEST"
        path: "tests/unit/test_incremental_refresh.py"
        status: "completed"
      - type: "TEST"
        path: "tests/unit/test_persistence.py"
        status: "completed"
      - type: "TEST"
        path: "tests/api/test_health.py"
        status: "completed"
        note: "Cache readiness tests added"
completed_tasks: 5
total_tasks: 5
---

# Sprint 2: Core Implementation

## Sprint Overview

**Sprint**: 2 of 3
**Goal**: Implement the core materialization layer components for DataFrame caching
**Duration**: 2 days
**Status**: Pending

This sprint transforms the approved architecture into production code by implementing the centralized watermark repository, incremental DataFrame refresh logic, S3 persistence layer, and startup preloading infrastructure.

## Input Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| PRD | docs/requirements/PRD-materialization-layer.md | Approved |
| TDD | docs/architecture/TDD-materialization-layer.md | Approved |

## Tasks

### T1: Implement WatermarkRepository
**Owner**: principal-engineer
**Estimated Effort**: 4 hours
**Status**: pending

**Description**: Create thread-safe singleton WatermarkRepository class for centralized per-project timestamp tracking.

**Acceptance Criteria**:
- [ ] Create `src/autom8_asana/dataframes/watermark.py`
- [ ] Implement `WatermarkRepository` class per TDD FR-001 specification
- [ ] Thread-safe singleton pattern with `threading.Lock`
- [ ] Methods: `get_watermark()`, `set_watermark()`, `get_all_watermarks()`, `clear_watermark()`
- [ ] Timezone-aware datetime enforcement
- [ ] Module-level `get_watermark_repo()` accessor function

**Output Artifact**: `src/autom8_asana/dataframes/watermark.py`

**Dependencies**: None

---

### T2: Implement Incremental Refresh
**Owner**: principal-engineer
**Estimated Effort**: 6 hours
**Status**: pending

**Description**: Add incremental refresh logic to ProjectDataFrameBuilder with `modified_since` parameter usage and delta merge.

**Acceptance Criteria**:
- [ ] Add `refresh_incremental()` method to `ProjectDataFrameBuilder`
- [ ] Implement `_fetch_modified_tasks()` using `modified_since` API parameter
- [ ] Implement `_merge_deltas()` for DataFrame delta merge logic
- [ ] Handle first sync (watermark=None) vs incremental sync
- [ ] Fallback to full fetch on incremental failure
- [ ] Structured logging for all sync operations

**Output Artifact**: Modified `src/autom8_asana/dataframes/builders/project.py`

**Dependencies**: T1 (needs WatermarkRepository)

---

### T3: Implement S3 Persistence
**Owner**: principal-engineer
**Estimated Effort**: 4 hours
**Status**: pending

**Description**: Create S3 persistence layer for GidLookupIndex baseline storage and watermark recovery.

**Acceptance Criteria**:
- [ ] Create `src/autom8_asana/dataframes/persistence.py`
- [ ] Implement `S3BaselinePersistence` class per TDD FR-007
- [ ] Methods: `save_baseline()`, `load_baseline()`
- [ ] Store DataFrame + watermark as parquet + metadata
- [ ] Error handling for S3 access failures
- [ ] Configuration via environment variables

**Output Artifact**: `src/autom8_asana/dataframes/persistence.py`

**Dependencies**: T2 (needs DataFrame refresh logic)

---

### T4: Integration and Startup Preload
**Owner**: principal-engineer
**Estimated Effort**: 6 hours
**Status**: pending

**Description**: Wire incremental refresh into resolver, add startup cache preloading, and update health check.

**Acceptance Criteria**:
- [ ] Modify `UnitResolutionStrategy._get_or_build_index()` to use `refresh_incremental()`
- [ ] Add `_preload_dataframe_cache()` to `api/main.py` lifespan
- [ ] Set `app.state.cache_ready = True` after preload complete
- [ ] Update health check to return 503 during warming
- [ ] Add `/health/detailed` endpoint with cache status
- [ ] Parallel entity preloading via `asyncio.gather()`

**Output Artifacts**:
- Modified `src/autom8_asana/services/resolver.py`
- Modified `src/autom8_asana/api/main.py`
- Modified `src/autom8_asana/api/routes/health.py`

**Dependencies**: T1, T2, T3 (needs all core components)

---

### T5: Unit Tests for New Components
**Owner**: principal-engineer
**Estimated Effort**: 4 hours
**Status**: pending

**Description**: Create comprehensive unit tests for WatermarkRepository, incremental refresh, and persistence layer.

**Acceptance Criteria**:
- [ ] Unit tests for `WatermarkRepository` (thread safety, timezone validation, singleton)
- [ ] Unit tests for `refresh_incremental()` (full fetch, incremental, fallback)
- [ ] Unit tests for `_merge_deltas()` (create, update, edge cases)
- [ ] Unit tests for `S3BaselinePersistence` (save, load, error handling)
- [ ] Test coverage >90% for new components
- [ ] All existing tests still pass

**Output Artifact**: `tests/unit/test_watermark.py`, `tests/unit/test_incremental_refresh.py`, `tests/unit/test_persistence.py`

**Dependencies**: T4 (needs implementation complete)

---

## Task Dependency Graph

```
T1 (WatermarkRepository)
 |
 v
T2 (Incremental Refresh)
 |
 v
T3 (S3 Persistence)
 |
 v
T4 (Integration)
 |
 v
T5 (Unit Tests)
```

**Sequential Dependencies**:
- T2 depends on T1 (incremental refresh needs watermark tracking)
- T3 depends on T2 (persistence needs DataFrame refresh logic)
- T4 depends on T1, T2, T3 (integration needs all components)
- T5 depends on T4 (tests need complete implementation)

## Success Criteria

### Implementation Complete
- [ ] All 5 tasks marked complete
- [ ] All new files created and integrated
- [ ] No regressions in existing functionality

### Performance Targets
- [ ] Startup preload completes in <60 seconds
- [ ] First request after healthy status <500ms
- [ ] Incremental refresh completes in <5 seconds

### Quality Gates
- [ ] All unit tests pass with >90% coverage
- [ ] No linting or type checking errors
- [ ] Code review approved

## Blockers

None currently identified.

## Notes

This sprint implements the core infrastructure for the materialization layer. The next sprint (Sprint 3) will focus on integration testing, performance validation, and production readiness.

**Key Implementation Notes**:
- Follow TDD specifications exactly (FR-001 through FR-007)
- Maintain backward compatibility with existing resolver
- Use structured logging for all operations (observability)
- Implement graceful fallback for all error cases

## Sprint Handoff

**From**: Sprint 1 (Requirements & Architecture)
**To**: Sprint 3 (Integration Testing & Production Readiness)

**Handoff Artifacts**:
- Completed implementation of all core components
- Unit tests with >90% coverage
- Integration-ready codebase for end-to-end testing
