# Deferred Work Roadmap

**Session**: session-20260204-195700-0f38ebf6
**Initiative**: Platform Maturity: Deferred Work Execution
**Complexity**: MIGRATION
**Source**: Deep Hygiene Sprint session-20260204-170818-5363b6da
**Date**: 2026-02-04

---

## Executive Summary

This roadmap coordinates execution of all deferred work from the Deep Hygiene Sprint, organized as 7 initiatives across 4 waves. The work resolves 14 refactor items (R01-R14) and 207 deferred items (D01-D45) from the hygiene triage manifest, plus completes Phase 2 wiring of orphaned architectural modules.

**Estimated Duration**: 10-14 sprints across 4 waves
**Estimated LOC Impact**: -2,500 lines (net reduction)
**Test Regression Tolerance**: Zero

---

## Wave Structure

```
Wave 1 (parallel)
├── I1: Quick Wins Sweep (hygiene, 1 sprint)
└── I4-S1: Exception Narrowing Sprint 1 (hygiene, 1 sprint)

Wave 2 (sequential after Wave 1)
├── I2: Service Layer Wiring (10x-dev, 2 sprints)
└── I4-S2/S3: Exception Narrowing Sprints 2-3 (hygiene, 1-2 sprints)

Wave 3 (sequential after Wave 2)
├── I3: Storage + Connection Wiring (10x-dev, 2 sprints)
└── I5-S1: API Main Decomposition Sprint 1 (10x-dev, 1 sprint)

Wave 4 (sequential after Wave 3)
├── I5-S2/S3: API Main Decomposition Completion (10x-dev, 1-2 sprints)
├── I6: API Error Unification (10x-dev, 1 sprint)
└── I7: Mechanical Cleanup Sweep (hygiene, 1 sprint)
```

---

## Wave 1: Foundation & Quick Wins

### I1: Quick Wins Sweep (hygiene, 1 sprint)

**Objective**: Execute low-hanging fruit from hygiene triage manifest that can be completed quickly and safely.

**Scope**:
- B01: Force-fix critical runtime & observability (3 sites)
  - DOC-001: Fix broken TieredCacheProvider() call in cache_invalidate.py
  - SW-001: Add logging to detection/facade.py:167 swallowed exception
  - SW-002: Add logging to mutation_invalidator.py:309 swallowed exception

- B08: Clean unused test imports (66 imports across 41 files)

- B09: Fix swallowed exceptions non-read-only (13 sites)
  - Add logging to 13 silent exception handlers

- B10: Fix logging inconsistency (4 new modules)
  - Replace stdlib logging with autom8y_log in services/ and core/

- B11: Extract magic numbers to named constants (5 sites)
  - TTL values in clients/custom_fields.py, clients/users.py, etc.

- B12: Add docstrings to public SDK methods (12 methods in clients/sections.py)

**Success Criteria**:
- [ ] All 3 force-fix items resolved
- [ ] 66 unused imports removed, tests pass
- [ ] 13 swallowed exceptions now log properly
- [ ] 4 modules using autom8y_log consistently
- [ ] 5 magic numbers extracted to named constants
- [ ] 12 public methods have docstrings
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-quick-wins-sweep.md`
- Implementation commits: 7 atomic commits (one per batch)

**Dependencies**: None (can start immediately)

**Estimated Duration**: 1 sprint (3-5 days)

---

### I4-S1: Exception Narrowing Sprint 1 - Mechanical Fixes (hygiene, 1 sprint)

**Objective**: Replace `except Exception:` with specific exception types for ~40 sites with clear mechanical patterns.

**Scope**:
- Focus on sites where exception type is obvious from context:
  - Cache operations → CacheError, CacheReadError, CacheWriteError
  - Network calls → NetworkError, ConnectionError, TimeoutError
  - Validation → ValidationError, SchemaError
  - Serialization → SerializationError, JSONDecodeError

- Target sites: ~40 of the 158 bare-except sites (D01-D13)

**Success Criteria**:
- [ ] 40 bare-except sites replaced with specific types
- [ ] All replaced sites have proper error context propagation
- [ ] Error messages include actionable context
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-exception-narrowing-s1.md`
- Exception type inventory (new exceptions needed)
- Implementation commits: 4-6 commits grouped by exception domain

**Dependencies**: None (can run in parallel with I1)

**Estimated Duration**: 1 sprint (3-5 days)

---

## Wave 2: Service Layer & Exception Completion

### I2: Service Layer Wiring (10x-dev, 2 sprints)

**Objective**: Wire EntityService, TaskService, SectionService to API routes, eliminate route-level duplication.

**Scope**:
- Wire orphaned service modules (R07: OM-001 to OM-005)
  - `services/entity_service.py`
  - `services/task_service.py`
  - `services/section_service.py`
  - `core/entity_registry.py`

- Migrate API routes to use service layer:
  - `api/routes/tasks.py` (reduce ~45%)
  - `api/routes/sections.py` (reduce ~45%)
  - `api/routes/dataframes.py` (reduce ~30%)

- Extract shared logic from routes into services:
  - Entity resolution
  - Cache coordination
  - Error handling patterns

**Success Criteria**:
- [ ] All 3 service modules fully wired to routes
- [ ] Route code reduced 45% for tasks.py and sections.py
- [ ] Route code reduced 30% for dataframes.py
- [ ] ServiceNotConfiguredError (UE-006) properly raised/handled or removed
- [ ] Zero test regressions
- [ ] All route endpoints maintain backward compatibility

**Artifacts**:
- PRD: `.claude/artifacts/PRD-service-layer-wiring.md`
- TDD: `docs/design/TDD-service-layer-extraction.md` (existing)
- Service integration tests
- Implementation commits: 8-10 commits (one per route migration)

**Dependencies**: Wave 1 complete (to ensure clean baseline)

**Estimated Duration**: 2 sprints (6-10 days)

---

### I4-S2/S3: Exception Narrowing Sprints 2-3 - Case-by-Case (hygiene, 1-2 sprints)

**Objective**: Handle remaining ~118 bare-except sites requiring case-by-case analysis and potential exception hierarchy expansion.

**Scope**:
- Analyze remaining bare-except sites from D01-D13:
  - api/main.py (11 sites - read-only lifted by I5)
  - api/routes/ (10 sites)
  - services/universal_strategy.py (6 sites)
  - clients/data/client.py (7 sites)
  - cache/ subsystem (21 sites)
  - persistence/ (10 sites)
  - dataframes/ (21 sites)
  - automation/ (19 sites)
  - models/ (20 sites)
  - other files (11 sites)

- For each site, determine:
  - Can use existing exception type?
  - Need new exception type? (extend hierarchy)
  - Is bare Exception actually appropriate? (document why)

- Wire unused exception types (R10, R11):
  - AutomationError, RuleExecutionError, SeedingError, PipelineActionError
  - CacheReadError, CacheWriteError

**Success Criteria**:
- [ ] All 118 remaining bare-except sites analyzed and addressed
- [ ] Exception hierarchy documented (map of what to raise when)
- [ ] All new exception types have clear docstrings and usage examples
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-exception-narrowing-s2.md`
- PRD: `.claude/artifacts/PRD-exception-narrowing-s3.md` (if split into 2 sprints)
- TDD: `docs/design/TDD-exception-hierarchy.md` (existing)
- Exception hierarchy diagram
- Implementation commits: 10-15 commits grouped by module

**Dependencies**: I2 complete (service layer may simplify some error handling)

**Estimated Duration**: 1-2 sprints (4-8 days depending on complexity)

---

## Wave 3: Storage & Decomposition Foundation

### I3: Storage + Connection Wiring (10x-dev, 2 sprints)

**Objective**: Complete Phase 2 of storage and connection lifecycle TDDs, eliminate S3 persistence duplication.

**Scope**:

**Part 1: Storage Protocol Wiring (R09)**
- Wire `dataframes/storage.py` (currently orphaned)
- Migrate consumers to use `DataFrameStorage` protocol
- References: TDD-unified-dataframe-persistence.md

**Part 2: Connection Lifecycle Wiring (R08)**
- Wire `cache/connections/` subpackage (RedisConnectionManager, S3ConnectionManager, ConnectionRegistry)
- Integrate into cache backends (currently backends manage own connections)
- References: TDD-connection-lifecycle-management.md

**Part 3: S3 Persistence Consolidation (R14)**
- Consolidate 3 overlapping S3 implementations:
  - DataFramePersistence (dataframes/persistence.py)
  - S3DataFrameStorage (dataframes/storage.py)
  - AsyncS3Client (dataframes/async_s3.py)
- Target: ~2,000 LOC reduction

**Success Criteria**:
- [ ] `dataframes/storage.py` fully wired, protocol adopted by all consumers
- [ ] `cache/connections/` integrated into all cache backends
- [ ] 3 S3 implementations reduced to 1 canonical implementation
- [ ] ~2,000 LOC eliminated
- [ ] All connection lifecycle tests pass
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-storage-connection-wiring.md`
- TDD: `docs/design/TDD-unified-dataframe-persistence.md` (existing)
- TDD: `docs/design/TDD-connection-lifecycle-management.md` (existing)
- Migration guide for storage protocol adopters
- Implementation commits: 12-15 commits (grouped by subsystem)

**Dependencies**: I2 complete (service layer may be consumers of storage)

**Estimated Duration**: 2 sprints (6-10 days)

---

### I5-S1: API Main Decomposition Sprint 1 (10x-dev, 1 sprint)

**Objective**: Extract first batch of endpoint groups from api/main.py god module (1466 lines).

**Scope**:
- Extract endpoint groups from api/main.py:
  - Dataframe catchup endpoints → `api/routes/catchup.py`
  - Dataframe rebuild endpoints → `api/routes/rebuild.py`
  - Cache warming endpoints → `api/routes/cache_warming.py`

- Address related deferred items now unblocked:
  - D14: api/main.py god module refactoring
  - D15: ProgressiveProjectBuilder duplication (R01 factory extraction)
  - R01: Extract 7-step instantiation ceremony into factory

- Target: main.py from 1466 lines to <1000 lines

**Success Criteria**:
- [ ] 3 new route modules created with extracted endpoints
- [ ] api/main.py reduced to <1000 lines
- [ ] ProgressiveProjectBuilder factory function extracted (R01)
- [ ] All extracted endpoints maintain backward compatibility
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-api-main-decomposition-s1.md`
- TDD: For ProgressiveProjectBuilder factory (R01)
- Implementation commits: 4-5 commits (one per extraction)

**Dependencies**: I3 complete (storage wiring may affect catchup/rebuild endpoints)

**Estimated Duration**: 1 sprint (3-5 days)

---

## Wave 4: Completion & Polish

### I5-S2/S3: API Main Decomposition Completion (10x-dev, 1-2 sprints)

**Objective**: Complete extraction of remaining endpoint groups, reduce main.py to routing shell only (<250 lines).

**Scope**:
- Extract remaining endpoint groups:
  - Project management endpoints → `api/routes/projects.py` (if not already separate)
  - Workspace/settings endpoints → `api/routes/settings.py`
  - Health/admin endpoints → `api/routes/health.py` (if not already separate)
  - Any remaining inline utilities → appropriate modules

- Address remaining main.py deferred items:
  - D16: Import migration (shims no longer needed after extraction)
  - HYG-005-17: Update to canonical import paths

- Eliminate 4 retained backward-compat shims (now safe after main.py refactor):
  - The 4 shims retained in B07 for read-only zone constraint

- Target: main.py under 250 lines (routing shell + middleware setup only)

**Success Criteria**:
- [ ] All endpoint groups extracted to dedicated route modules
- [ ] api/main.py under 250 lines
- [ ] 4 retained shims deleted (B07 completion)
- [ ] All imports using canonical paths (no shims)
- [ ] All extracted endpoints maintain backward compatibility
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-api-main-decomposition-s2.md`
- PRD: `.claude/artifacts/PRD-api-main-decomposition-s3.md` (if split)
- Final api/main.py architecture diagram
- Implementation commits: 8-10 commits

**Dependencies**: I5-S1 complete

**Estimated Duration**: 1-2 sprints (4-8 days)

---

### I6: API Error Unification (10x-dev, 1 sprint)

**Objective**: Unify mixed HTTPException vs centralized error handler patterns across API layer.

**Scope**:
- Address R13: API error handling pattern unification
  - HYG-005-06: Inconsistent error handling in routes
  - HYG-005-07: Mixed HTTPException vs centralized handlers

- Establish documented convention:
  - When to raise HTTPException directly
  - When to use centralized error handlers
  - How to propagate error context
  - Error response format standardization

- Migrate all route modules to follow convention:
  - api/routes/tasks.py
  - api/routes/sections.py
  - api/routes/dataframes.py
  - api/routes/query.py
  - api/routes/admin.py
  - All new route modules from I5

**Success Criteria**:
- [ ] Error handling convention documented (ADR or guide)
- [ ] All route modules follow consistent pattern
- [ ] HTTPException usage rationalized and justified
- [ ] Error responses have consistent format
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-api-error-unification.md`
- ADR: Error handling convention for API layer
- Migration guide for future route modules
- Implementation commits: 6-8 commits (one per route module)

**Dependencies**: I5-S2/S3 complete (all route modules extracted)

**Estimated Duration**: 1 sprint (3-5 days)

---

### I7: Mechanical Cleanup Sweep (hygiene, 1 sprint)

**Objective**: Final cleanup pass for low-ROI deferred items now addressable, remove temporary scaffolding.

**Scope**:

**From triage manifest deferred items (D20-D45)**:
- D20-D23: Minor missing docstrings (47 items - business model properties, internal helpers)
- D27: Minor magic numbers (2 sites)
- D29-D33: Low-severity DRY violations now addressable:
  - CACHE_TRANSIENT_ERRORS pattern (14 sites)
  - MutationEvent fire-and-forget boilerplate (14 sites)
  - Cache-check-before-HTTP pattern (3+ clients)
  - list_subtasks/list_dependents duplication
  - ISP violation: warm() no-op stubs
- D36: CancelledError guard additions (2 sites)
- D37: Broad try block decomposition (pipeline.py)
- D38: Redundant exception catch hierarchy

**Remaining refactor items**:
- R02: FreshnessStamp serialization consolidation (if not done in I3)
- R03: S3 config dataclass consolidation (if not done in I3)
- R04: Schema lookup ceremony extraction (15+ sites)
- R05: Workspace GID retrieval consolidation (5+ sites)
- R06: Duplicate CircuitBreakerOpenError consolidation
- R12: Bot PAT acquisition boilerplate consolidation (12 sites)

**Temporary scaffolding cleanup**:
- Remove any TODO markers added during earlier waves
- Clean up any temporary adapter code
- Verify all orphaned modules are now wired or explicitly documented as unused

**Success Criteria**:
- [ ] All addressable minor docstrings added
- [ ] All minor DRY violations resolved or documented as acceptable
- [ ] All remaining refactor items (R02-R06, R12) completed
- [ ] Zero temporary TODO markers
- [ ] Zero truly orphaned modules (all wired or documented)
- [ ] Final hygiene audit shows clean bill of health
- [ ] Zero test regressions

**Artifacts**:
- PRD: `.claude/artifacts/PRD-mechanical-cleanup-sweep.md`
- Final hygiene audit report (equivalent to hygiene-audit-report.md)
- Implementation commits: 8-10 commits grouped by theme

**Dependencies**: All of Wave 1-4 complete (lifts read-only constraints, provides final context)

**Estimated Duration**: 1 sprint (3-5 days)

---

## Success Metrics Summary

| Metric | Baseline (post-hygiene sprint) | Target (post-roadmap) |
|--------|-------------------------------|----------------------|
| Refactor items (R01-R14) | 14 unresolved | 0 (all resolved or superseded) |
| Deferred items (D01-D45) | 207 deferred | 0 (all resolved, wired, or documented as acceptable) |
| Bare-except sites | 158 | 0 (all narrowed or justified) |
| api/main.py lines | 1466 | <250 |
| Backward-compat shims | 4 retained | 0 |
| Route code reduction | Baseline | -45% (tasks.py, sections.py) |
| LOC reduction (total) | Baseline | -2,500 (net) |
| Test regressions | 0 new (hygiene sprint baseline: 6 pre-existing) | 0 new |
| Orphaned modules | 7 (OM-001 to OM-007) | 0 (all wired or removed) |
| Unused exception types | 6 (UE-001 to UE-006) | 0 (all wired or removed) |

---

## Risk Mitigation

### High-Risk Areas

1. **api/main.py decomposition (I5)**
   - Risk: Breaking backward compatibility for existing API consumers
   - Mitigation: Comprehensive integration tests, feature flags for gradual rollout, maintain API contract tests

2. **Exception narrowing (I4)**
   - Risk: Catching too narrow an exception, allowing unexpected failures
   - Mitigation: Comprehensive error case testing, staged rollout, monitoring for new error types in production

3. **S3 persistence consolidation (I3)**
   - Risk: Data loss or corruption during migration
   - Mitigation: Extensive testing with production-like data, rollback plan, phased migration

4. **Service layer wiring (I2)**
   - Risk: Performance regression from additional abstraction layer
   - Mitigation: Benchmark before/after, optimize hot paths, async patterns maintained

### Dependency Risks

- **Wave dependencies**: Later waves depend on earlier waves lifting read-only constraints
  - Mitigation: Strict wave ordering, checkpoint validation between waves

- **Test regression budget**: Zero tolerance means any regression blocks progress
  - Mitigation: Comprehensive pre-wave baseline, automated regression detection, quick rollback capability

---

## Execution Guidelines

### Rite Switching

This session will switch rites multiple times:

| Initiative | Rite | Reason |
|-----------|------|--------|
| I1 | hygiene | Cleanup/fix-now items |
| I4-S1/S2/S3 | hygiene | Exception handling is hygiene concern |
| I2 | 10x-dev | Service layer is new architectural wiring |
| I3 | 10x-dev | Storage/connection is architectural wiring |
| I5 | 10x-dev | API decomposition is architectural refactor |
| I6 | 10x-dev | Error unification is architectural decision |
| I7 | hygiene | Final cleanup sweep |

### Commit Strategy

- **Wave 1-2**: Atomic commits per batch/module
- **Wave 3-4**: Feature-flagged commits for high-risk changes
- **Throughout**: Continuous integration, test on every commit

### Checkpoint Gates

After each wave:
1. Run full test suite (must pass)
2. Run hygiene scans (trend improving or stable)
3. Generate WHITE_SAILS confidence signal
4. User approval to proceed to next wave (if GRAY or BLACK sails)

---

## Timeline Estimate

| Wave | Initiatives | Sprints | Days (estimated) |
|------|------------|---------|-----------------|
| Wave 1 | I1, I4-S1 | 2 (parallel) | 3-5 |
| Wave 2 | I2, I4-S2/S3 | 3-4 | 7-12 |
| Wave 3 | I3, I5-S1 | 3 | 9-15 |
| Wave 4 | I5-S2/S3, I6, I7 | 3-4 | 8-13 |
| **Total** | 7 initiatives | 11-13 sprints | 27-45 days |

**Calendar estimate**: 6-9 weeks (assuming 5-day sprints with 1-2 day gaps for reviews)

---

## Appendix: Mapping to Triage Manifest

### Refactor Items (R01-R14) to Initiatives

| Refactor Item | Description | Initiative | Notes |
|--------------|-------------|-----------|-------|
| R01 | ProgressiveProjectBuilder factory | I5-S1 | Extracted during main.py decomposition |
| R02 | FreshnessStamp serialization | I7 | Low-risk consolidation in final sweep |
| R03 | S3 config dataclass consolidation | I3 | Part of storage wiring |
| R04 | Schema lookup ceremony extraction | I7 | Mechanical extraction in final sweep |
| R05 | Workspace GID retrieval consolidation | I7 | Config access pattern |
| R06 | Duplicate CircuitBreakerOpenError consolidation | I7 | Exception hierarchy cleanup |
| R07 | Orphaned services layer | I2 | Core of service layer wiring initiative |
| R08 | Orphaned cache/connections | I3 | Core of connection wiring |
| R09 | Orphaned dataframes/storage.py | I3 | Core of storage wiring |
| R10 | Unused automation exceptions | I4-S2/S3 | Wired during exception narrowing |
| R11 | Unused cache semantic errors | I4-S2/S3 | Wired during exception narrowing |
| R12 | Bot PAT boilerplate consolidation | I7 | DRY violation in final sweep |
| R13 | API error handling unification | I6 | Dedicated initiative |
| R14 | Three S3 persistence implementations | I3 | Core of storage consolidation |

### Deferred Items (D01-D45) to Initiatives

| Deferred Range | Description | Initiative | Notes |
|---------------|-------------|-----------|-------|
| D01-D13 | Bare-except sites (by module) | I4-S1/S2/S3 | Exception narrowing sprints |
| D14 | api/main.py god module | I5-S1/S2/S3 | API decomposition |
| D15 | api/main.py ProgressiveProjectBuilder duplication | I5-S1 | With R01 factory extraction |
| D16 | api/main.py import migration | I5-S2/S3 | After decomposition complete |
| D17-D19 | Read-only zone items (metrics/, lambda_handlers/) | I7 | May remain deferred if zones stay read-only |
| D20-D23 | Minor missing docstrings | I7 | Final sweep |
| D24-D28 | Minor comments/magic numbers | I7 | Final sweep |
| D29-D35 | Low-severity DRY violations | I7 | Final sweep |
| D36-D39 | Defensive improvements | I7 | Final sweep |
| D40-D45 | Config/architecture inconsistencies | I7 or I2/I3 | Depending on scope |

---

## Appendix: Key Artifacts Cross-Reference

### From Deep Hygiene Sprint (session-20260204-170818-5363b6da)

- Triage manifest: `.claude/artifacts/hygiene-triage-manifest.md`
- Triage rules: `.claude/sessions/session-20260204-170818-5363b6da/hygiene-triage-rules.yaml`
- Discovery findings (5 scans):
  - `.claude/artifacts/hygiene-findings-dead-code.md` (103 findings)
  - `.claude/artifacts/hygiene-findings-error-handling.md` (134 findings)
  - `.claude/artifacts/hygiene-findings-doc-debt.md` (82 findings)
  - `.claude/artifacts/hygiene-findings-solid-dry.md` (22 findings)
  - `.claude/artifacts/hygiene-findings-architecture.md` (18 findings)
- Final audit report: `.claude/artifacts/hygiene-audit-report.md`

### TDD References (12 existing)

All in `docs/design/`:
- TDD-cache-invalidation-pipeline.md
- TDD-cache-module-reorganization.md
- TDD-connection-lifecycle-management.md
- TDD-cross-tier-freshness.md
- TDD-dataframe-build-coalescing.md
- TDD-entity-knowledge-registry.md
- TDD-exception-hierarchy.md
- TDD-partial-failure-signaling.md
- TDD-service-layer-extraction.md
- TDD-unified-cacheentry-hierarchy.md
- TDD-unified-dataframe-persistence.md
- TDD-unified-retry-orchestrator.md

### This Session Artifacts (to be created)

Per-initiative PRDs:
- `.claude/artifacts/PRD-quick-wins-sweep.md` (I1)
- `.claude/artifacts/PRD-exception-narrowing-s1.md` (I4-S1)
- `.claude/artifacts/PRD-exception-narrowing-s2.md` (I4-S2)
- `.claude/artifacts/PRD-exception-narrowing-s3.md` (I4-S3, if needed)
- `.claude/artifacts/PRD-service-layer-wiring.md` (I2)
- `.claude/artifacts/PRD-storage-connection-wiring.md` (I3)
- `.claude/artifacts/PRD-api-main-decomposition-s1.md` (I5-S1)
- `.claude/artifacts/PRD-api-main-decomposition-s2.md` (I5-S2)
- `.claude/artifacts/PRD-api-main-decomposition-s3.md` (I5-S3, if needed)
- `.claude/artifacts/PRD-api-error-unification.md` (I6)
- `.claude/artifacts/PRD-mechanical-cleanup-sweep.md` (I7)

Per-sprint contexts (created as sprints start):
- `.claude/sessions/session-20260204-195700-0f38ebf6/SPRINT_CONTEXT_I1.md`
- `.claude/sessions/session-20260204-195700-0f38ebf6/SPRINT_CONTEXT_I4S1.md`
- ... (and so on)

---

**END OF ROADMAP**
