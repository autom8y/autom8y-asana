---
schema_version: "2.1"
session_id: session-20260203-124709-9df8e766
status: ACTIVE
created_at: "2026-02-03T11:47:09Z"
initiative: Dynamic Query Service
complexity: SERVICE
active_rite: rnd
current_phase: validation
---


# Session: Dynamic Query Service

## Sprint 2: Hierarchy Index + /aggregate Endpoint

**Status: COMPLETE**

**Goal**: Build HierarchyIndex for cross-entity joins and implement the /aggregate endpoint with GROUP BY/HAVING support.

**Entry Point**: design phase (architect) - PRD skipped per sprint plan

**Completion Date**: 2026-02-04T00:45:00Z

## Sprint 3: Test Fixture Optimization

**Status: COMPLETE**

**Goal**: Eliminate 89% fixture overhead in test suite by mocking shared app fixture and deduplicating test files.

**Entry Point**: architect (ADR) then principal-engineer (implementation)

**Sprint Context**: /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20260203-124709-9df8e766/SPRINT_CONTEXT.md

**Completion Date**: 2026-02-03T22:30:00Z

## Sprint 4: Large Section Resilience

**Status: COMPLETE**

**Goal**: Enable progressive builder to handle sections with 10,000+ tasks by introducing paced pagination, checkpoint persistence, and resumable fetch.

**Entry Point**: requirements (requirements-analyst)

**Sprint Context**: /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20260203-124709-9df8e766/SPRINT_CONTEXT_S4.md

**Completion Date**: 2026-02-03T23:59:00Z

## Sprint 5: Hierarchy Warming Backpressure Hardening

**Status: COMPLETE**

**Goal**: Eliminate 145 HTTP 429s during hierarchy warming via batched dispatch pacing.

**Entry Point**: design (architect - ADR phase)

**Sprint Context**: /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20260203-124709-9df8e766/SPRINT_CONTEXT_S5.md

**Created**: 2026-02-03T19:47:09Z

**Completion Date**: 2026-02-04T02:00:00Z

## Artifacts
- ADR: /Users/tomtenuta/Code/autom8_asana/docs/design/ADR-hierarchy-backpressure-hardening.md
- ADR: /Users/tomtenuta/Code/autom8_asana/docs/design/ADR-test-fixture-optimization.md
- PRD: /Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-large-section-resilience.md
- TDD: /Users/tomtenuta/Code/autom8_asana/docs/design/TDD-lkg-cache-freshness.md

## Tasks
### Completed
- **S1-001** (requirements): PRD for Dynamic Query Service
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-query-service.md
  - Completed: 2026-02-03T11:55:08Z
  - Agent: requirements-analyst

- **S1-002** (design): TDD: Query Engine Foundation
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/design/TDD-query-engine-foundation.md
  - Completed: 2026-02-03T12:00:00Z
  - Agent: architect

- **S1-003** (implementation): Query Module + /rows Route
  - Artifacts:
    - src/autom8_asana/query/ (module: errors.py, models.py, compiler.py, guards.py, engine.py, __init__.py)
    - src/autom8_asana/api/routes/query_v2.py (route handler)
    - tests/unit/query/ (83 tests, all passing)
  - Completed: 2026-02-03T12:47:30Z
  - Agent: principal-engineer

- **S1-004** (qa): Adversarial Validation
  - Artifact: /Users/tomtenuta/Code/autom8_asana/tests/unit/query/test_adversarial.py
  - Test Summary: 200 adversarial tests, all passing, 0 bugs found
  - Test Counts: 283 query tests passing, 1472 full suite passing (1 pre-existing unrelated failure)
  - Completed: 2026-02-03T19:45:00Z
  - Agent: qa-adversary
  - Verdict: GO for production - Zero bugs found, zero regressions

- **S2-001** (design): TDD: HierarchyIndex + Cross-Entity Joins
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/design/TDD-hierarchy-index.md
  - Completed: 2026-02-03T20:30:00Z
  - Agent: architect
  - Key Decisions: Shared column left-joins (not GID-based), static relationship registry, query/hierarchy.py + query/join.py

- **S2-002** (implementation): Implement: HierarchyIndex + Joins
  - Artifacts:
    - src/autom8_asana/query/hierarchy.py (HierarchyIndex implementation)
    - src/autom8_asana/query/join.py (JoinResolver implementation)
    - src/autom8_asana/query/errors.py (JoinError added)
    - src/autom8_asana/query/models.py (JoinSpec model)
    - src/autom8_asana/query/engine.py (join support integration)
    - src/autom8_asana/query/__init__.py (exports updated)
    - src/autom8_asana/api/routes/query_v2.py (join route integration)
    - tests/unit/query/test_hierarchy.py (9 tests)
    - tests/unit/query/test_join.py (16 tests)
    - tests/unit/query/test_engine.py (9 additional join tests)
  - Test Summary: 34 new tests, all passing (317 query tests total)
  - Test Counts: 317 query tests passing, 1506 full suite passing (1 pre-existing unrelated failure)
  - Completed: 2026-02-03T21:15:00Z
  - Agent: principal-engineer
  - Note: Zero regressions, all Sprint 1 tests remain passing

- **S2-003** (qa): QA: Hierarchy + Joins
  - Artifact: /Users/tomtenuta/Code/autom8_asana/tests/unit/query/test_adversarial_hierarchy.py
  - Test Summary: 53 adversarial tests (hierarchy + joins), all passing
  - Test Counts: 370 query tests passing, 7532/7757 full suite passing (6 pre-existing failures)
  - Defects: 1 LOW severity (DEF-001: synthetic DataFrame dtype mismatch in test fixtures, not production-relevant)
  - Completed: 2026-02-03T22:00:00Z
  - Agent: qa-adversary
  - Verdict: GO - Hierarchy and join subsystems validated, zero production-blocking defects, zero regressions

- **S2-004** (design): TDD: /aggregate + AggSpec
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/design/TDD-aggregate-endpoint.md
  - Completed: 2026-02-03T23:30:00Z
  - Agent: architect
  - Key Decisions: New query/aggregator.py module, HAVING via synthetic schema, count_distinct support, Utf8 cast for financial columns

### Sprint 2 Tasks

#### Completed

- **S2-005** (implementation): Implement: /aggregate + GROUP BY/HAVING
  - Artifacts:
    - src/autom8_asana/query/aggregator.py (GroupByAggregator implementation)
    - src/autom8_asana/query/engine.py (execute_aggregate method)
    - src/autom8_asana/api/routes/query_v2.py (/aggregate route)
    - tests/unit/query/test_aggregator.py (unit tests)
    - tests/unit/query/test_engine.py (aggregate integration tests)
    - tests/api/test_routes_query_aggregate.py (API tests)
  - Test Summary: 80+ new tests (unit + integration + API), all passing
  - Test Counts: 7737 passed, 219 skipped, 1 xfailed, zero failures
  - Completed: 2026-02-04T00:15:00Z
  - Agent: principal-engineer
  - Note: Full regression clean, zero regressions

- **S2-006** (qa): QA: /aggregate
  - Artifact: /Users/tomtenuta/Code/autom8_asana/tests/unit/query/test_adversarial_aggregate.py
  - Test Summary: 65 adversarial tests (aggregation + HAVING), all passing
  - Test Counts: 7737 passed, 219 skipped, 1 xfailed, zero failures
  - Defects: Zero bugs found
  - Completed: 2026-02-04T00:45:00Z
  - Agent: qa-adversary
  - Verdict: GO - Aggregate subsystem validated, zero defects, zero regressions

### Sprint 3 Tasks

#### Completed

- **S3-001** (design): ADR: Test Fixture Optimization
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/design/ADR-test-fixture-optimization.md
  - Completed: 2026-02-03T22:30:00Z
  - Agent: architect

- **S3-002** (implementation): Modify shared app fixture to mock discovery
  - File: tests/api/conftest.py
  - Changes: Replaced app fixture with mocked discovery, added reset_singletons autouse fixture
  - Completed: 2026-02-03T22:30:00Z
  - Agent: principal-engineer

- **S3-003** (implementation): Deduplicate local app fixtures in 3 test files
  - Files: tests/api/test_routes_query.py, tests/api/test_routes_resolver.py, tests/api/test_routes_query_rows.py
  - Changes: Removed redundant local app, client, reset_singletons fixtures and unused imports
  - Test Results: All 82 tests across 3 files passing
  - Completed: 2026-02-03T22:30:00Z
  - Agent: principal-engineer

- **S3-004** (qa): Validate correctness, performance, isolation
  - QA Verdict: GO
  - Test Results: 7,463 passed, 6 failed (pre-existing, unrelated), 188 skipped
  - Performance: ~30-36% wall-clock reduction (183s -> ~118-130s)
  - Note: 6 pre-existing failures are schema version mismatches from prior commit ba6050b, NOT from Sprint 3 changes
  - Completed: 2026-02-03T22:30:00Z
  - Agent: qa-adversary

### Sprint 4 Tasks

#### Completed

- **S4-001** (requirements): PRD for Large Section Resilience
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-large-section-resilience.md
  - Completed: 2026-02-03T23:00:00Z
  - Agent: requirements-analyst
  - Description: PRD with 5 user stories, 6 functional requirements, 4 NFRs, 8 edge cases

- **S4-002** (design): TDD for Large Section Resilience
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/design/TDD-large-section-resilience.md
  - Completed: 2026-02-03T23:15:00Z
  - Agent: architect
  - Description: TDD with 4 ADRs (LSR-001 through LSR-004), detailed pseudocode, performance analysis

- **S4-003** (implementation): Implement paced pagination + checkpoints
  - Artifacts:
    - src/autom8_asana/dataframes/builders/progressive.py (~200 LOC changes)
    - src/autom8_asana/persistence/section_persistence.py (~4 LOC changes)
    - src/autom8_asana/config.py (~15 LOC config additions)
    - tests/unit/dataframes/builders/test_paced_fetch.py (8 unit tests)
    - tests/unit/dataframes/builders/test_checkpoint_resume.py (4 integration tests)
    - tests/unit/dataframes/builders/test_section_info_compat.py (6 compatibility tests)
  - Test Summary: 18 new feature tests, all passing, zero regressions
  - Completed: 2026-02-03T23:45:00Z
  - Agent: principal-engineer

- **S4-004** (qa): Adversarial testing
  - Artifact: /Users/tomtenuta/Code/autom8_asana/tests/unit/dataframes/builders/test_adversarial_pacing.py
  - Test Summary: 22 adversarial tests (stress tests, edge cases, concurrency), all passing
  - Test Counts: 40 total feature tests passing, 7634 full suite passing
  - Defects: Zero bugs found
  - Completed: 2026-02-03T23:59:00Z
  - Agent: qa-adversary
  - Verdict: GO - Zero defects, zero regressions, large section handling validated

### Sprint 5 Tasks

#### Completed

- **S5-001** (design): ADR: Hierarchy Warming Backpressure Hardening
  - Artifact: /Users/tomtenuta/Code/autom8_asana/docs/design/ADR-hierarchy-backpressure-hardening.md
  - Completed: 2026-02-03T20:15:00Z
  - Agent: architect
  - Description: ADR documenting batched dispatch pacing, structured 429 logging, and dead code removal

- **S5-002** (implementation): Implement batch pacing, dead code removal, structured 429 logging
  - Artifacts:
    - src/autom8_asana/config.py (3 pacing constants: HIERARCHY_BATCH_SIZE=50, HIERARCHY_BATCH_DELAY_MS=100, HIERARCHY_BATCH_JITTER_MS=20)
    - src/autom8_asana/cache/unified.py (batched dispatch with lazy import)
    - src/autom8_asana/cache/hierarchy_warmer.py (dead code removed)
    - src/autom8_asana/transport/asana_http.py (structured 429 log with logger guard)
    - tests/unit/cache/test_hierarchy_pacing.py (12 tests)
    - tests/unit/cache/test_hierarchy_warmer.py (verified passing)
  - Test Summary: 12 new tests, all passing
  - Test Counts: 930/930 cache tests passing
  - Completed: 2026-02-04T01:30:00Z
  - Agent: principal-engineer
  - Note: All 6 changes implemented, batched dispatch operational

- **S5-003** (qa): Adversarial testing of pacing behavior and regression
  - Artifact: /Users/tomtenuta/Code/autom8_asana/tests/unit/cache/test_adversarial_pacing_backpressure.py
  - Test Summary: 26 adversarial tests (batch pacing, 429 handling, concurrency, regression), all passing
  - Test Counts: 930/930 cache tests passing, 6810/6810 unit tests passing, 0 failures
  - Defects: 1 defect found (DEF-001: missing logger guard on 429 log) - FIXED
  - Completed: 2026-02-04T02:00:00Z
  - Agent: qa-adversary
  - Verdict: GO - Batch pacing validated, 429 handling confirmed, zero regressions

## Sprint 6: SWR Production Wiring + Dead Code Cleanup

**Status: COMPLETE**

**Goal**: Wire the SWR build callback in factory.py so background refreshes work, and remove ttl_hours dead code from DataFrameCache and tests.

**Entry Point**: principal-engineer (skip PRD/TDD — spike serves as design artifact)

**Sprint Context**: /Users/tomtenuta/Code/autom8_asana/.claude/sessions/session-20260203-124709-9df8e766/SPRINT_CONTEXT_S6.md

**Created**: 2026-02-03T16:48:01Z

**Completion Date**: 2026-02-03T16:56:04Z

## Blockers
None.

## Sprint 1 Summary

**Status: COMPLETE**

All 4 tasks completed successfully:
1. **S1-001**: Requirements (PRD) - docs/requirements/PRD-dynamic-query-service.md (678 lines)
2. **S1-002**: Design (TDD) - docs/design/TDD-dynamic-query-service.md (1,039 lines)
3. **S1-003**: Implementation - src/autom8_asana/query/ module + route handler (662 tests passing)
4. **S1-004**: QA (Adversarial) - tests/unit/query/test_adversarial.py (200 adversarial tests)

**Total Test Coverage**: 283 query tests passing, 1472 full suite passing (1 pre-existing unrelated failure)

**Quality Gates**:
- Zero bugs found in adversarial testing
- Zero regressions introduced
- All code paths validated
- Route integration verified
- QA Verdict: GO for production

**Completion Date**: 2026-02-03T19:45:00Z

**Next Phase**: Sprint 2 ready to begin (session remains ACTIVE)

## Sprint 3 Summary

**Status: COMPLETE**

All 4 tasks completed successfully:
1. **S3-001**: ADR: Test Fixture Optimization - docs/design/ADR-test-fixture-optimization.md
2. **S3-002**: Modify shared app fixture - tests/api/conftest.py (mocked discovery, added reset_singletons)
3. **S3-003**: Deduplicate local fixtures - 3 test files cleaned (82 tests passing)
4. **S3-004**: QA validation - GO verdict, zero regressions, ~30-36% performance improvement

**Total Test Coverage**: 7,463 passing (unchanged), 6 pre-existing failures (unrelated to Sprint 3)

**Performance Improvement**: ~30-36% wall-clock reduction (183s -> ~118-130s)

**Quality Gates**:
- Zero regressions introduced
- All test isolation preserved
- Fixture correctness validated
- Performance target exceeded
- QA Verdict: GO

**Completion Date**: 2026-02-03T22:30:00Z

**Next Phase**: Sprint 2 (S2-004) and Sprint 4 work can continue

## Sprint 4 Summary

**Status: COMPLETE**

All 4 tasks completed successfully:
1. **S4-001**: Requirements (PRD) - docs/requirements/PRD-large-section-resilience.md (5 user stories, 6 FRs, 4 NFRs, 8 edge cases)
2. **S4-002**: Design (TDD) - docs/design/TDD-large-section-resilience.md (4 ADRs, detailed pseudocode, performance analysis)
3. **S4-003**: Implementation - progressive.py (~200 LOC), section_persistence.py (~4 LOC), config.py (~15 LOC), 18 new tests
4. **S4-004**: QA (Adversarial) - tests/unit/dataframes/builders/test_adversarial_pacing.py (22 adversarial tests)

**Total Test Coverage**: 40 feature tests passing (18 unit + 4 integration + 6 compatibility + 12 pre-existing + 22 adversarial), 7634 full suite passing

**Quality Gates**:
- Zero bugs found in adversarial testing
- Zero regressions introduced
- Large section handling validated (10,000+ tasks)
- Paced pagination implemented with configurable limits
- Checkpoint persistence enables crash recovery
- Resumable fetch validated through adversarial tests
- QA Verdict: GO

**Completion Date**: 2026-02-03T23:59:00Z

**Next Phase**: Sprint 2 complete, session ready for wrap

## Sprint 2 Summary

**Status: COMPLETE**

All 6 tasks completed successfully:
1. **S2-001**: Design (TDD: HierarchyIndex) - docs/design/TDD-hierarchy-index.md (920 lines)
2. **S2-002**: Implementation (HierarchyIndex + Joins) - query/hierarchy.py, query/join.py, +34 tests
3. **S2-003**: QA (Hierarchy + Joins) - test_adversarial_hierarchy.py (53 tests, 1 LOW defect, GO verdict)
4. **S2-004**: Design (TDD: /aggregate) - docs/design/TDD-aggregate-endpoint.md (1329 lines)
5. **S2-005**: Implementation (/aggregate + GROUP BY/HAVING) - query/aggregator.py, /aggregate route, +80 tests
6. **S2-006**: QA (/aggregate) - test_adversarial_aggregate.py (65 tests, zero defects, GO verdict)

**Total Test Coverage**: 230+ new tests across two cycles
- **Cycle 1**: 87 new tests (hierarchy + joins)
- **Cycle 2**: 145+ new tests (aggregation + HAVING)
- **Full Regression**: 7737 passed, 219 skipped, 1 xfailed, 0 failures

**Quality Gates**:
- Zero production-blocking defects (1 LOW synthetic DataFrame defect in test fixtures only)
- Zero regressions introduced across both cycles
- Both cycles received GO verdicts from QA
- Complete test coverage for HierarchyIndex, JoinResolver, and GroupByAggregator

**Key Deliverables**:
- **HierarchyIndex**: EntityRelationship registry with bidirectional parent/child lookup
- **JoinResolver**: Shared-column left-join enrichment on /rows endpoint
- **/aggregate endpoint**: GROUP BY with count/sum/avg/min/max/count_distinct, HAVING support via PredicateCompiler
- **Integration**: Project registry threaded through query_v2 routes for proper context

**New/Modified Files**:
- New modules: query/hierarchy.py, query/join.py, query/aggregator.py
- Modified: query/errors.py, query/models.py, query/engine.py, query/guards.py, query/__init__.py
- Route: api/routes/query_v2.py (join + aggregate routes)
- Tests: 9 new test files, 230+ new test cases

**Completion Date**: 2026-02-04T00:45:00Z

## Sprint 5 Summary

**Status: COMPLETE**

All 3 tasks completed successfully:
1. **S5-001**: Design (ADR) - docs/design/ADR-hierarchy-backpressure-hardening.md
2. **S5-002**: Implementation - 6 files modified (config.py, cache/unified.py, cache/hierarchy_warmer.py, transport/asana_http.py, 2 test files with 12 tests)
3. **S5-003**: QA (Adversarial) - tests/unit/cache/test_adversarial_pacing_backpressure.py (26 tests)

**Total Test Coverage**: 930/930 cache tests passing, 6810/6810 unit tests passing, 0 failures

**Quality Gates**:
- 1 defect found (DEF-001: missing logger guard on 429 log) - FIXED immediately
- Zero regressions introduced
- Batch pacing validated (50 project batch, 100ms delay, 20ms jitter)
- Structured 429 logging confirmed functional
- Dead code removed from hierarchy_warmer.py
- QA Verdict: GO

**Key Deliverables**:
- **Batched Dispatch**: Hierarchy warming now processes projects in batches of 50 with 100ms delay + 20ms jitter
- **Structured 429 Logging**: HTTP 429 errors now logged with structured format including rate limit headers
- **Dead Code Removal**: Obsolete code paths removed from hierarchy_warmer.py
- **Logger Guard**: Added check to prevent log errors when logger not available

**Implementation Changes**:
- config.py: Added 3 pacing constants (HIERARCHY_BATCH_SIZE, HIERARCHY_BATCH_DELAY_MS, HIERARCHY_BATCH_JITTER_MS)
- cache/unified.py: Implemented batched dispatch logic with lazy import
- cache/hierarchy_warmer.py: Removed dead code
- transport/asana_http.py: Added structured 429 logging with logger guard
- tests/unit/cache/test_hierarchy_pacing.py: 12 unit tests for pacing behavior
- tests/unit/cache/test_adversarial_pacing_backpressure.py: 26 adversarial tests

**Completion Date**: 2026-02-04T02:00:00Z

**Next Phase**: Session ready for wrap

## Sprint 6 Summary

**Status: COMPLETE**

All 2 tasks completed successfully:
1. **S6-001**: Implementation - Wire SWR build callback + remove ttl_hours dead code (5 files modified)
2. **S6-002**: QA (Adversarial) - tests/unit/cache/dataframe/test_adversarial_swr_wiring.py (validation)

**Total Test Coverage**: 158 dataframe cache tests, 942 cache tests, 6822 unit tests — all passing, 0 failures

**Quality Gates**:
- Zero defects found in adversarial testing
- Zero regressions introduced
- ttl_hours fully removed from src/ and tests/
- SWR callback correctly wired with proper closure, ordering, and resume=True
- All adversarial edge cases validated safe
- QA Verdict: GO - SWR production-ready

**Key Deliverables**:
- **SWR Build Callback**: factory.py now wires _swr_build callback for background refresh
- **Dead Code Removal**: ttl_hours parameter fully eliminated from DataFrameCache and test helpers
- **Production Ready**: SWR background refresh operational with proper error handling and early returns

**Implementation Changes**:
- src/autom8_asana/cache/factory.py: Wired _swr_build callback with resume=True, removed ttl_hours=12
- src/autom8_asana/cache/dataframe_cache.py: Removed ttl_hours field from dataclass
- tests/unit/cache/dataframe/test_dataframe_cache.py: Removed ttl_hours from make_cache(), added TestSWRCallbackWiring
- tests/unit/cache/dataframe/test_schema_version_validation.py: Removed ttl_hours from make_cache()
- tests/unit/cache/dataframe/test_dataframe_cache_stats.py: Removed ttl_hours from _make_cache()
- tests/unit/cache/dataframe/test_adversarial_swr_wiring.py: Adversarial validation tests

**Completion Date**: 2026-02-03T16:56:04Z

**Next Phase**: Session ready for wrap

### Sprint 6 Tasks

#### Completed

- **S6-001** (implementation): Wire SWR build callback + remove ttl_hours dead code
  - Agent: principal-engineer
  - Status: completed
  - Completed: 2026-02-03T17:30:00Z
  - Artifacts:
    - src/autom8_asana/cache/factory.py (wired _swr_build callback with resume=True, removed ttl_hours=12)
    - src/autom8_asana/cache/dataframe_cache.py (removed ttl_hours field from dataclass)
    - tests/unit/cache/dataframe/test_dataframe_cache.py (removed ttl_hours from make_cache(), added TestSWRCallbackWiring test class)
    - tests/unit/cache/dataframe/test_schema_version_validation.py (removed ttl_hours from make_cache())
    - tests/unit/cache/dataframe/test_dataframe_cache_stats.py (removed ttl_hours from _make_cache())
  - Test Results: 158 dataframe cache tests passed, 942 cache tests passed, zero ttl_hours references in src/

- **S6-002** (validation): Adversarial testing of SWR wiring + dead code removal
  - Agent: qa-adversary
  - Status: completed
  - Completed: 2026-02-03T16:56:04Z
  - Artifact: /Users/tomtenuta/Code/autom8_asana/tests/unit/cache/dataframe/test_adversarial_swr_wiring.py
  - Test Summary: 158 dataframe cache tests, 942 cache tests, 6822 unit tests — all passing, zero failures
  - Defects: Zero
  - Key Validations:
    - ttl_hours fully dead in src/ and tests/
    - SWR callback correctly wired (closure, ordering, resume=True, early returns, guarded puts)
    - All adversarial edge cases assessed safe
  - Verdict: GO - Zero defects, zero regressions, SWR production-ready