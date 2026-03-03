# Architecture Report: autom8y-asana

**Analysis Unit**: directory (single repo, subsystem-level boundaries)
**Repo Path**: `/Users/tomtenuta/Code/autom8y-asana`
**Source Root**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana`
**Date**: 2026-02-23
**Complexity**: DEEP-DIVE
**Phase**: 4 of 4 (Remediation Planner -- terminal phase)
**Upstream Artifacts**:
- TOPOLOGY-INVENTORY.md
- DEPENDENCY-MAP.md
- ARCHITECTURE-ASSESSMENT.md
- docs/architecture/ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Answers to 7 Key Questions](#2-answers-to-7-key-questions)
3. [Consolidated Finding Summary](#3-consolidated-finding-summary)
4. [Ranked Recommendations](#4-ranked-recommendations)
5. [Phased Roadmap](#5-phased-roadmap)
6. [Migration Readiness Assessments](#6-migration-readiness-assessments)
7. [Decomposition Health Score](#7-decomposition-health-score)
8. [Cross-Rite Referrals](#8-cross-rite-referrals)
9. [Unknowns Registry](#9-unknowns-registry)
10. [Scope and Limitations](#10-scope-and-limitations)

---

## 1. Executive Summary

autom8y-asana is a 115K LOC async Python SDK and API service for Asana-based CRM/pipeline automation. It operates in two deployment modes (ECS/Lambda) across 22 subsystems, exposes 42+ HTTP endpoints, handles 7 Lambda handlers, and manages 6 external service integrations. The test suite has 10,552+ passing tests at a 1.87:1 test-to-source ratio.

**The architecture is structurally sound for its current scale.** The layered design (API -> Services -> Subsystems) holds in the common case. Domain modeling is sophisticated and well-tested. The multi-tier SWR caching system provides genuine production resilience. Six circular dependency cycles exist at the directory level but are all mitigated at runtime via deferred imports. No finding here represents an immediate production risk.

**The primary structural concerns are bounded and actionable:**

1. `core/system_context.py` imports from 5 subsystems above it, creating hidden coupling for all 12 units that depend on `core/`. This is a layering violation masquerading as a test utility.

2. Three convenience methods on domain models (`Project.build_dataframe()`, `Section.build_dataframe()`, `Task.save()`) create reverse dependencies that are the root cause of two of the six circular dependency cycles.

3. Five DataServiceClient endpoint modules each replicate an 8-step orchestration scaffolding. The retry callbacks have been extracted; the execution policy abstraction has not.

4. The dual creation pipeline (lifecycle/ canonical, automation/pipeline.py legacy) has three duplicated helper methods with identical logic that can be extracted today without philosophical debate.

5. The lifecycle engine's canonical status exists only in WIP documents, not in code-level documentation.

**What to do first:** The `conversation_audit.py` bootstrap guard verification (Risk 5, R-001) is zero-cost -- read one file and add one import if missing. After that, consolidating the three duplicated helper methods in the creation pipelines (R-002) is a two-hour change with immediate risk reduction.

**What not to do:** Do not decompose SaveSession. It is a well-designed Coordinator pattern with 14 collaborators. Do not re-open cache divergence analysis -- ADR-0067 closed this. Do not pursue full pipeline consolidation -- D-022 is closed.

**Decomposition Health Score: 68/100.** The architecture is in good shape for a codebase of this age and complexity. The identified issues are structural debts, not structural failures.

---

## 2. Answers to 7 Key Questions

### Q1: DataServiceClient Decomposition -- Residual Work Needed?

**Definitive Answer: Substantially done. One residual opportunity remains; further work is optional, not urgent.**

The prior art identified DataServiceClient as a 2,165-line god object. It has been decomposed into `client.py` (1,277 LOC) plus 5 endpoint modules (_endpoints/simple.py 234 LOC, batch.py 310 LOC, insights.py 219 LOC, export.py 173 LOC, reconciliation.py 133 LOC) plus 6 supporting modules (_retry.py 191, _cache.py 194, _response.py 270, _metrics.py 54, _pii.py 73, _normalize.py 58). Total: 3,024 LOC across 14 files.

The shared retry callback factory (`_retry.py:build_retry_callbacks()`) eliminated the highest-ROI duplication. What remains is the per-endpoint orchestration scaffolding -- the 8-step pattern (circuit breaker check -> get_client -> build callbacks -> execute_with_retry -> handle error response -> parse success response -> record success -> emit metrics) that each endpoint module replicates. Each endpoint adds approximately 50-80 LOC of structural boilerplate before endpoint-specific logic.

This is Risk 6 in the risk register (leverage score 5/10, strategic investment). It is worth addressing when adding a new endpoint (to avoid paying the scaffolding cost again) but does not need to be addressed proactively. The existing endpoints are tested and functional.

**Evidence**: ARCHITECTURE-ASSESSMENT.md AP-3, Risk 6; `clients/data/_endpoints/*.py` all follow the same pattern.

**Confidence**: High.

---

### Q2: SaveSession Coordinator Boundaries -- Any Action Needed?

**Definitive Answer: No action needed. Boundaries are clean. Accept as-is.**

SaveSession (1,854 LOC, 58 methods, 14 collaborators) is a Coordinator pattern orchestrating a 6-phase commit (validation -> ordering -> execution -> cascade -> healing -> cache invalidation). The prior art initially flagged it as a god object; subsequent analysis confirmed it is a legitimate coordinator.

The 14 collaborators are appropriately delegated to separate modules: `graph.py` (dependency ordering), `cascade.py` (field propagation), `action_executor.py` (action execution), `executor.py` (batch API calls), `healing.py` (self-healing), `holder_construction.py` (holder creation), `holder_concurrency.py` (concurrency), `holder_ensurer.py` (holder existence), `cache_invalidator.py` (post-commit), `reorder.py` (section reordering), `tracker.py` (state tracking), `validation.py` (pre-commit checks), `models.py` (types), `events.py` (event system). Each collaborator has a single responsibility.

The one boundary concern is `persistence/holder_construction.py` importing 6 specific Holder types (ContactHolder, LocationHolder, OfferHolder, ProcessHolder, UnitHolder, Business) -- this is Risk 10 (leverage score 4/10). It is real but low-severity: adding a new entity type requires updating holder_construction.py. A holder type registry (R-009) would address this, but it is not urgent.

**Evidence**: TOPOLOGY-INVENTORY.md Section 5.4; ARCHITECTURE-ASSESSMENT.md Section 3.4; MEMORY.md confirmation.

**Confidence**: High.

---

### Q3: Dual Creation Path Convergence -- Right Goal or Current State Appropriate?

**Definitive Answer: Full convergence is not the right goal. The current state is appropriate WITH two specific fixes: document canonical status in code, and extract the three duplicated helper methods.**

The essential difference between `lifecycle/creation.py` (737 LOC) and `automation/pipeline.py` (970 LOC) is at Step 7 of 7: field seeding strategy. `AutoCascadeSeeder` uses zero-config name matching. `FieldSeeder` uses explicit field lists. This is a genuine philosophical divergence between convention-over-configuration and explicit-configuration, not accidental duplication.

Additionally, `automation/pipeline.py` includes `_create_onboarding_comment_async()` (FR-COMMENT-001 through FR-COMMENT-005) and `_validate_post_transition()` that do not appear in `lifecycle/creation.py` -- suggesting the two paths handle different scenario classes.

D-022 (full pipeline consolidation) is closed. WS6 extracted sufficient shared surface (6 of 7 steps now use `core/creation.py` shared primitives).

However, three helper methods -- `_extract_user_gid()`, `_extract_first_rep()`, and `_resolve_assignee_gid()` -- are independently implemented in both paths with nearly identical logic. These are accidental duplicates extractable to `core/creation.py` without touching the seeding divergence. This is R-002 (quick win, leverage 48).

What is also missing: no code-level documentation declares lifecycle as canonical. No deprecation notice exists on `automation/pipeline.py`. This is Risk 2, Gap 6 -- addressable in one hour via module docstrings (R-003).

**Evidence**: ARCHITECTURE-ASSESSMENT.md AP-5, Risk 2; DEPENDENCY-MAP.md Section 5.1; MEMORY.md (D-022 closed).

**Confidence**: High.

---

### Q4: Cache Key Scheme Divergence -- Any Loose Ends?

**Definitive Answer: No loose ends. ADR-0067 resolved this. One minor future item exists on the DataFrameCacheProtocol.**

ADR-0067 documents the intentional 12/14-dimension divergence between the entity cache key scheme and the DataFrame cache key scheme. The two caches serve different freshness/latency profiles and are governed by separate invalidation logic.

The one remaining item noted in ADR-0067 is the `DataFrameCacheProtocol` in `protocols/cache.py` -- described as a "future extraction target" that would allow the DataFrameCache singleton to be injected rather than accessed via module-level singleton. This is AP-6 in the anti-pattern inventory (low severity, medium confidence). It is not urgent -- the current singleton works correctly and is reset appropriately via `system_context.reset_all()`.

**Evidence**: ARCHITECTURE-ASSESSMENT.md Section 5.2 (Gap 3: Fully Resolved); MEMORY.md.

**Confidence**: High.

---

### Q5: Classification Layer Configuration Surface -- Worthwhile or Premature?

**Definitive Answer: Conditionally worthwhile. The implementation path is clear, but the trigger should be a confirmed change-frequency threshold, not architectural preference.**

The `SectionClassifier` in `models/business/activity.py` (lines 183-263) hardcodes 33 Offer sections and 14 Unit sections as Python frozensets. The `from_groups()` factory method (lines 96-126) already accepts a dict format that could be loaded from YAML. The lifecycle engine already uses YAML config (`config/lifecycle_stages.yaml`) for analogous per-stage data, proving the pattern is established.

If classification rules change monthly or more: YAML externalization is a quick win with high operational leverage. A developer or operator could adjust section-to-activity mappings without a deployment cycle.

If classification rules change yearly or less: the current design is appropriate. Hardcoded Python is simpler, version-controlled, and type-checkable.

The classification rule change frequency is an unknown (see Unknowns Registry). This recommendation is classified as a conditional quick win (R-004) -- validate frequency first, then act.

**Evidence**: ARCHITECTURE-ASSESSMENT.md AP-NA (Risk 8, leverage 4/10); `models/business/activity.py` lines 183-263.

**Confidence**: High on implementation path; Medium on whether this is urgent.

---

### Q6: Query DSL Exploitation -- What Capabilities Are Underutilized?

**Definitive Answer: The aggregation and cross-entity join capabilities are structurally present but may have low consumer penetration. No code change is needed -- this is a consumer adoption question.**

The Query DSL (`query/`, 9 files, 2,040 LOC) implements:
- Composable predicate AST with 10 operators (Comparison, AndGroup, OrGroup, NotGroup, Op enum)
- Cross-entity joins at depth 1 (`query/join.py`)
- Aggregation (`query/aggregator.py`: AggregationCompiler, build_post_agg_schema, AggFunction enum)
- Three API endpoints: `/rows`, `/aggregate`, `/{entity_type}`
- Classification-based section filtering (`_resolve_classification()` calls `SectionClassifier`)

The infrastructure handles the creation pipeline via `QueryEngine.execute_rows()` and `execute_aggregate()`. The query engine directly imports `services.query_service.EntityQueryService` and `services.resolver.to_pascal_case` (Risk 9, leverage 2/10) -- a layering violation where the computation layer depends on the orchestration layer. Injecting these via constructor or protocol would be cleaner, but the impact is low.

What exploitation looks like: saved query templates, query-builder UI consumers, programmatic query composition for analytics pipelines. None of these require code changes to the DSL -- they require consumer-side investment.

The one architectural action (R-010) is refactoring `query/engine.py` to accept a `DataFrameProvider` protocol rather than importing `EntityQueryService` directly. This is a long-term item (leverage 2/10).

**Evidence**: ARCHITECTURE-ASSESSMENT.md Section 3.7, Risk 9; TOPOLOGY-INVENTORY.md Section 5.8.

**Confidence**: High on existing capabilities; Low on current consumer usage patterns.

---

### Q7: Import-Time Registration Entry Points -- Current State and Residual Risk?

**Definitive Answer: Substantially resolved. One entry point remains at Medium risk pending verification. The bootstrap mechanism is now explicit, not import-time.**

The entry-point audit (MEMORY.md: "U-005: Entry-point audit, 1 bootstrap guard added") and the code comment in `models/business/__init__.py` ("Bootstrap registration is now EXPLICIT, not import-time") indicate the bootstrap mechanism has been modernized.

Current status per the audit:
- ECS mode (`entrypoint.py`): `bootstrap()` called explicitly. **Covered.**
- Lambda `cache_warmer.py`: `_ensure_bootstrap()` guard. **Covered.**
- Lambda `cache_invalidate.py`: Does not need bootstrap (key-only operations). **N/A.**
- Lambda `insights_export.py`: Deferred workflow import pattern. **Low risk.**
- Lambda `cloudwatch.py`: Bootstrap status **unknown** (not in prior audit).
- Lambda `conversation_audit.py`: MEMORY.md suggests a guard was added, but verification is pending (Risk 5).

The `conversation_audit.py` guard is the most important verification item. MEMORY.md says "1 bootstrap guard added (conversation_audit.py)" but the ARCHITECTURE-ASSESSMENT.md flags this as unverified. Reading the file to confirm takes 5 minutes and is R-001 (leverage 80, quick win).

**Evidence**: ARCHITECTURE-ASSESSMENT.md Section 5.2 Gap 5, Risk 5; MEMORY.md; TOPOLOGY-INVENTORY.md Section 4.1.

**Confidence**: High on the overall state; Medium on conversation_audit.py specifically (unverified).

---

## 3. Consolidated Finding Summary

### Finding Themes

**Theme A: Layering Violations (Medium severity, structural)**
Three distinct violations of the layer hierarchy exist. All are mitigated at runtime but constrain refactoring freedom:
1. `core/system_context.py` imports from 5 subsystems (models, dataframes, services, metrics, automation) -- a foundation layer with upward dependencies (AP-1, Risk 1).
2. `models/project.py`, `models/section.py`, `models/task.py` contain convenience methods that import upward into dataframes/ and persistence/ -- the root cause of Cycles 1 and 2 (AP-2, Risk 3).
3. `cache/integration/dataframe_cache.py` imports `api/metrics.py` (Cycle 5) -- a cache-layer module reaching into the API layer (DEPENDENCY-MAP.md Hotspot 6).

**Theme B: Accidental Duplication (Low-Medium severity, tactical)**
Three specific instances of duplicated logic that can be extracted without philosophical debate:
1. Three helper methods (`_extract_user_gid`, `_extract_first_rep`, `_resolve_assignee_gid`) exist identically in both `lifecycle/creation.py` and `automation/pipeline.py` (AP-5 partial).
2. 8-step orchestration scaffolding repeated across 5 DataServiceClient endpoint modules (AP-3, Risk 6).
3. `models/business/business.py` TYPE_CHECKING import of `DataServiceClient` could be replaced with an `InsightsProvider` protocol (Dependency-Map Deep Dive 7.1).

**Theme C: Missing Documentation at Code Level (Low severity, high-leverage)**
Two canonical decisions exist only in WIP documents and MEMORY.md, not in code-visible locations:
1. No module docstring in `lifecycle/` declares canonical status over `automation/pipeline.py` (Risk 2, Gap 6).
2. No deprecation notice on `automation/pipeline.py` (Risk 2).

**Theme D: Singleton Management Without Registration Pattern (Low severity, ongoing risk)**
Eight module-level singletons require coordinated reset via `core/system_context.py`. Adding a new singleton requires updating the god-context. If forgotten, test isolation silently breaks (AP-6, Risk 4).

**Theme E: Bootstrap Entry Point Coverage (Medium severity, correctness)**
`lambda_handlers/conversation_audit.py` bootstrap guard status is unverified (Risk 5). `lambda_handlers/cloudwatch.py` was not in the original entry-point audit (topology unknown).

**Theme F: Accepted Trade-Offs (No action required)**
- Cache key scheme divergence: closed by ADR-0067.
- Dual creation pipeline full convergence: closed by D-022.
- SaveSession as coordinator: confirmed appropriate, no decomposition.
- Legacy preload fallback: documented by ADR-011.
- Pipeline divergence (lifecycle canonical, automation retained): intentional per MEMORY.md.

---

## 4. Ranked Recommendations

Leverage scores are inherited from the architecture-assessment risk register where available, and derived using `leverage = impact / effort` (1-100 scale) for new items. Confidence ratings propagate from upstream artifacts.

### Ranked Table

| ID | Title | Leverage | Category | Confidence | Risk if Deferred |
|----|-------|----------|----------|------------|-----------------|
| R-001 | Verify `conversation_audit.py` bootstrap guard | 80 | Quick Win | Medium | Silent correctness failure if Tier1 guard changes |
| R-002 | Extract 3 duplicated helper methods to `core/creation.py` | 48 | Quick Win | High | Drift in assignee/user resolution logic across pipelines |
| R-003 | Document lifecycle canonical status in code | 40 | Quick Win | High | New features added to wrong pipeline path |
| R-004 | Externalize classification rules to YAML (conditional) | 32 | Quick Win (conditional) | Medium | Deployment required for any section classification change |
| R-005 | Refactor `core/system_context.py` to registration pattern | 24 | Sprint-Ready | High | Singleton-add forgotten -> silent test isolation failures |
| R-006 | Extract `Project.build_dataframe()` / `Section.build_dataframe()` to DataFrameService | 18 | Sprint-Ready | High | Cycles 1 and 2 accumulate more deferred imports over time |
| R-007 | Verify and document `cloudwatch.py` Lambda bootstrap status | 16 | Quick Win | Medium | Unaudited production entry point |
| R-008 | Add DataServiceClient execution policy abstraction | 12 | Sprint-Ready | High | Linear scaffolding cost per new endpoint |
| R-009 | Add holder type registry to `persistence/holder_construction.py` | 8 | Sprint-Ready | High | New entity type silently omitted from holder auto-creation |
| R-010 | Decouple `query/engine.py` from services layer via protocol | 4 | Long-term Transformation | High | Query engine cannot be tested or extracted independently |

---

### Recommendation Detail

#### R-001: Verify `conversation_audit.py` bootstrap guard
**Leverage Score**: 80 (Impact: 8, Effort-inverse: 10 -- 5-minute read)
**Category**: Quick Win
**Confidence**: Medium (MEMORY.md says guard was added; code not verified in analysis)
**Risk if Deferred**: The `conversation_audit.py` Lambda handler performs entity detection at runtime. If the bootstrap guard is absent and the Tier1 defensive guard in `detection/tier1.py` is ever modified, entity detection returns UNKNOWN for all entities processed by this handler -- a silent correctness failure, not a crash.
**Dependencies**: None.
**Affected Subsystems**: `lambda_handlers/`, `models/business/`

**Implementation Sketch**:
1. Read `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/conversation_audit.py`.
2. Verify presence of `import autom8_asana.models.business  # noqa: F401` or equivalent bootstrap call at module top level.
3. If present: close Risk 5, update entry-point audit doc.
4. If absent: add the import guard at line 1 of the handler module body (not inside the handler function).
5. Add a unit test asserting the handler initializes correctly without prior bootstrap.

---

#### R-002: Extract 3 duplicated helper methods to `core/creation.py`
**Leverage Score**: 48 (Impact: 6, Effort-inverse: 8 -- ~2-4 hours)
**Category**: Quick Win
**Confidence**: High (identical code confirmed in ARCHITECTURE-ASSESSMENT.md AP-5)
**Risk if Deferred**: Each path evolves its helper methods independently. When business logic changes (e.g., assignee resolution cascade order), both files must be updated. The risk of divergent behavior grows with each feature change to either pipeline.
**Dependencies**: None. Does not affect the seeding divergence (intentional, closed by D-022).
**Affected Subsystems**: `lifecycle/`, `automation/`, `core/`

**Implementation Sketch**:
1. Read `lifecycle/creation.py` lines 700-719 (`_extract_user_gid`, `_extract_first_rep`) and `_resolve_assignee_gid` (lines 601-647).
2. Read the equivalent methods in `automation/pipeline.py` (lines 612-668, 730-756) to confirm they are identical or near-identical.
3. Add three module-level functions to `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py`: `extract_user_gid()`, `extract_first_rep()`, `resolve_assignee_gid()`.
4. Replace the private methods in both `lifecycle/creation.py` and `automation/pipeline.py` with calls to the shared functions.
5. Run `pytest tests/unit/lifecycle/ tests/unit/automation/` to verify no regressions.

---

#### R-003: Document lifecycle canonical status in code
**Leverage Score**: 40 (Impact: 8, Effort-inverse: 5 -- ~1 hour)
**Category**: Quick Win
**Confidence**: High
**Risk if Deferred**: A new developer adding a pipeline feature has no code-visible signal about which path to extend. Features added to `automation/pipeline.py` instead of `lifecycle/creation.py` partially unravel WS6's convergence work. The divergence grows silently.
**Dependencies**: None.
**Affected Subsystems**: `lifecycle/`, `automation/`

**Implementation Sketch**:
1. Add a module-level docstring to `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/__init__.py` declaring: "This is the canonical pipeline engine for CRM/Process lifecycle transitions. New pipeline features belong here. See automation/pipeline.py for the legacy path retained for [specific use case]."
2. Add a notice to the top of `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py`: "LEGACY: This pipeline handles [specific automation scenarios]. For new lifecycle features, use lifecycle/creation.py. See ADR-[NNN] for the dual-path decision."
3. If no ADR exists for the D-022 closure, add one (or reference the D-022 entry in the debt ledger).
4. Update `docs/guides/patterns.md` to reference the canonical status (if the guide exists and is maintained).

---

#### R-004: Externalize classification rules to YAML (conditional on change frequency)
**Leverage Score**: 32 (Impact: 8, Effort-inverse: 4 -- ~1 day if triggered)
**Category**: Quick Win (conditional)
**Confidence**: Medium (depends on unknown change frequency -- see Unknowns Registry U-002)
**Risk if Deferred**: If classification rules change frequently, every change requires a full deployment cycle. If rules are stable, deferral is appropriate.
**Dependencies**: Validate change frequency via git blame first (U-002 resolution).
**Affected Subsystems**: `models/business/`, `config/`

**Implementation Sketch** (only execute after confirming change frequency warrants it):
1. Create `/Users/tomtenuta/Code/autom8y-asana/config/classification_rules.yaml` with the 33 Offer and 14 Unit section name mappings, mirroring the structure of `lifecycle_stages.yaml`.
2. Modify `models/business/activity.py` to load `OFFER_CLASSIFIER` and `UNIT_CLASSIFIER` from YAML at module load time, using the existing `from_groups()` factory method.
3. Add Pydantic validation for the loaded YAML (type-safe classification rule objects).
4. Update tests to cover YAML-loading path and invalid YAML error handling.
5. Verify `get_classifier()` API is unchanged so all consumers are unaffected.

---

#### R-005: Refactor `core/system_context.py` to registration pattern
**Leverage Score**: 24 (Impact: 6, Effort-inverse: 4 -- ~1-2 days)
**Category**: Sprint-Ready
**Confidence**: High
**Risk if Deferred**: Each new singleton added to the codebase requires a developer to remember to update `system_context.py`. When forgotten (and it will eventually be forgotten), test isolation silently breaks. The god-context also imposes transitive upward dependencies on all 12 units that depend on `core/`.
**Dependencies**: None. Can be done independently.
**Affected Subsystems**: `core/`, `models/`, `dataframes/`, `services/`, `metrics/`, test infrastructure

**Implementation Sketch**:
1. Add a `reset_registry: list[Callable[[], None]]` to `core/system_context.py` that allows singletons to register their own reset functions: `SystemContext.register_reset(fn: Callable[[], None]) -> None`.
2. In each singleton module (SchemaRegistry, ProjectTypeRegistry, EntityProjectRegistry, DataFrameCache singleton, MetricRegistry, WatermarkRepository), call `SystemContext.register_reset(cls.reset)` at module load time.
3. Replace the explicit per-singleton calls in `reset_all()` with a loop over the registry: `for fn in _reset_registry: fn()`.
4. Remove all upward imports from `core/system_context.py` (the imports from models, dataframes, services, metrics). This eliminates Cycle 4.
5. Run full test suite to verify all singletons are properly reset. Confirm test isolation holds.

---

#### R-006: Extract `Project.build_dataframe()` / `Section.build_dataframe()` to DataFrameService
**Leverage Score**: 18 (Impact: 6, Effort-inverse: 3 -- ~1.5 days)
**Category**: Sprint-Ready
**Confidence**: High
**Risk if Deferred**: The reverse dependency (models/ -> dataframes/) prevents clean extraction of either subsystem. New developers may add non-deferred reverse imports by following the same convenience method pattern, creating runtime import errors. Cycles 1 and 2 continue to constrain the codebase.
**Dependencies**: R-005 can be done independently; this does not require R-005.
**Affected Subsystems**: `models/`, `dataframes/`, `services/`

**Implementation Sketch**:
1. Add `build_for_project(project: Project, ...) -> DataFrame` and `build_for_section(section: Section, ...) -> DataFrame` to `services/dataframe_service.py`.
2. Move the logic currently deferred-imported in `models/project.py` and `models/section.py` into these service methods.
3. Update all callers of `project.build_dataframe()` and `section.build_dataframe()` to call `dataframe_service.build_for_project(project)` instead.
4. Remove the deferred imports from `models/project.py` and `models/section.py`. This eliminates the models -> dataframes direction of Cycle 1.
5. Run `pytest tests/unit/models/ tests/unit/dataframes/ tests/unit/services/` to confirm no regressions.

Note: `Task.save()` and `Task.save_sync()` (models -> persistence Cycle 2) can be extracted similarly to `TaskService.save(task)` in a follow-on. The ARCHITECTURE-ASSESSMENT.md estimates 1 day for this extraction; it is not included here to keep scope bounded.

---

#### R-007: Verify and document `cloudwatch.py` Lambda bootstrap status
**Leverage Score**: 16 (Impact: 4, Effort-inverse: 4 -- 15-30 minutes)
**Category**: Quick Win
**Confidence**: Medium (file exists, not examined in prior audit per TOPOLOGY-INVENTORY.md Section 4.1)
**Risk if Deferred**: An unaudited production Lambda entry point. If it uses entity detection without a bootstrap guard, it is a correctness risk.
**Dependencies**: None.
**Affected Subsystems**: `lambda_handlers/`, `models/business/`

**Implementation Sketch**:
1. Read `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cloudwatch.py`.
2. Determine: (a) what CloudWatch event type it handles, (b) whether it imports from `models.business` or calls entity detection.
3. If it uses entity detection: add bootstrap guard identical to `cache_warmer.py`.
4. If it does not use entity detection: document as "no bootstrap required" in the entry-point audit.
5. Update `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/ENTRY-POINT-AUDIT.md` with findings.

---

#### R-008: Add DataServiceClient execution policy abstraction
**Leverage Score**: 12 (Impact: 6, Effort-inverse: 2 -- ~3-5 days)
**Category**: Sprint-Ready
**Confidence**: High
**Risk if Deferred**: Each new DataServiceClient endpoint costs ~50-80 LOC of structural boilerplate before endpoint logic. Without the abstraction, endpoint implementations may diverge in how they handle errors, metrics, or circuit breaker state, creating inconsistency.
**Dependencies**: None. Can be done independently.
**Affected Subsystems**: `clients/data/`

**Implementation Sketch**:
1. Define an `EndpointPolicy` abstract base (or protocol) in `clients/data/_policy.py` with the 8-step execution contract: `async def execute(self, request: T) -> R`.
2. Extract the shared 8-step orchestration from `client.py._execute_with_retry()` into a concrete `DefaultEndpointPolicy` that accepts circuit breaker state, retry config, response parser, and success recorder as constructor parameters.
3. Refactor each of the 5 endpoint modules to instantiate `DefaultEndpointPolicy` with endpoint-specific parameters and delegate the execution loop to it.
4. Each endpoint module's execute method reduces from ~50-80 LOC to ~20-30 LOC of endpoint-specific logic (path construction, request serialization, response mapping).
5. Run `pytest tests/unit/clients/` and `pytest tests/integration/` to verify behavior is unchanged.

---

#### R-009: Add holder type registry to `persistence/holder_construction.py`
**Leverage Score**: 8 (Impact: 4, Effort-inverse: 2 -- ~1.5-2 days)
**Category**: Sprint-Ready
**Confidence**: High
**Risk if Deferred**: Adding a new entity type (Holder) requires updating `holder_construction.py`. If forgotten, the new entity type's holders are never auto-created during persistence operations -- a silent behavioral gap.
**Dependencies**: Depends on understanding the full entity type registry to map Holder types correctly.
**Affected Subsystems**: `persistence/`, `models/business/`

**Implementation Sketch**:
1. Add a `HOLDER_REGISTRY: dict[str, type[Holder]]` in `persistence/holder_construction.py` mapping entity type strings to Holder classes.
2. Replace the 6 explicit Holder type imports with a registry lookup: `holder_class = HOLDER_REGISTRY[entity_type_str]`.
3. Each entity type's `_bootstrap.py` (or equivalent) registers its Holder type: `HolderRegistry.register("unit", UnitHolder)`.
4. Add a registry completeness check in tests asserting that all known entity types from `EntityRegistry` have a registered Holder.
5. Run `pytest tests/unit/persistence/` to verify holder construction behaves identically.

---

#### R-010: Decouple `query/engine.py` from services layer via protocol
**Leverage Score**: 4 (Impact: 4, Effort-inverse: 1 -- ~3 days, low urgency)
**Category**: Long-term Transformation
**Confidence**: High
**Risk if Deferred**: The query engine cannot be tested without the full services layer. As the query DSL grows (more operators, deeper joins), this coupling makes the engine harder to benchmark and extract. However, the current test suite works and the risk is low-proximity.
**Dependencies**: None, but should be done after R-006 to have clean service boundaries.
**Affected Subsystems**: `query/`, `services/`

**Implementation Sketch**:
1. Define a `DataFrameProvider` protocol in `protocols/` (or `query/protocols.py`): `async def get_dataframes(entity_type: str, ...) -> list[DataFrame]`.
2. Modify `services/universal_strategy.py` to implement `DataFrameProvider`.
3. Change `query/engine.py` to accept a `DataFrameProvider` in its constructor rather than importing `EntityQueryService` directly.
4. Remove the direct import of `services.query_service.EntityQueryService` and `services.resolver.to_pascal_case` from `query/engine.py`.
5. Update `api/routes/query.py` to inject `UniversalStrategy` as the `DataFrameProvider` via FastAPI DI.

---

### Accept-As-Is Designations

The following findings from the risk register have been reviewed and designated as accepted trade-offs requiring no action:

| Finding | Rationale |
|---------|-----------|
| AP-5: Dual creation pipeline (full convergence) | D-022 closed. Essential seeding divergence documented. Shared primitives in core/creation.py are sufficient. |
| AP-6: Module-level singletons | Idiomatic Python for this deployment model. SystemContext reset mechanism manages them deliberately. R-005 improves the pattern without eliminating singletons. |
| AP-3: DataServiceClient decomposition progress | The highest-ROI extraction (retry callbacks) is done. Current state is functional and tested. R-008 is optional, not urgent. |
| Risk 3: Circular dependencies (Cycles 3, 5, 6) | Cycles 3 (models <-> core via TYPE_CHECKING), 5 (cache -> api.metrics via try/except), and 6 (auth -> api via nosemgrep) are low-severity and locally mitigated. Not worth breaking work for. |
| SPOF-1: DataFrameCache singleton | Well-designed redundancy (memory + S3 + circuit breaker). Process-level SPOF is expected in Lambda/ECS. |
| SPOF-4: Asana API external dependency | Write fallback impossible by design. Read resilience via multi-tier cache is sufficient. |
| Paradox 1: Immutability vs. mutable cache | Architecturally coherent. Documentation would help onboarding but is not a structural issue. |
| Paradox 2: Zero-config vs. explicit critical path | Coherent split: domain = zero-config, infrastructure = explicit. |
| ADR-0067 cache divergence | Closed. Intentional, documented, analyzed. |
| ADR-011 legacy preload | Closed. Documented as active degraded-mode fallback. |

---

## 5. Phased Roadmap

### Dependency Graph

```
R-001 (verify bootstrap)      -- independent, do today
R-007 (cloudwatch audit)      -- independent, do today
R-002 (extract helpers)       -- independent, do this sprint
R-003 (document canonical)    -- independent, do this sprint
R-004 (YAML classifiers)      -- blocked on U-002 resolution
    |
    v
R-005 (system_context refactor) -- independent but enables R-006 cleanup
    |
    v
R-006 (extract build_dataframe)
    |
    v
R-008 (DataServiceClient policy) -- independent, can run parallel
R-009 (holder registry)       -- independent, can run parallel
    |
    v
R-010 (query/engine protocol) -- depends on R-006 for clean service boundaries
```

---

### Phase 0: Quick Wins (0-1 day each, no dependencies, do opportunistically)

| ID | Action | Estimated Time | Owner Signal |
|----|--------|----------------|--------------|
| R-001 | Read `conversation_audit.py`, verify or add bootstrap guard | 15-30 min | High urgency: production correctness |
| R-007 | Read `cloudwatch.py`, audit bootstrap need, update ENTRY-POINT-AUDIT.md | 15-30 min | Low urgency: completeness |
| R-003 | Add docstrings to `lifecycle/__init__.py` and `automation/pipeline.py` | 30-60 min | High urgency: developer clarity |
| R-002 | Extract 3 helper methods to `core/creation.py` | 2-4 hours | Medium urgency: drift prevention |

**Phase 0 total**: ~3-6 hours. These can all be done in a single focused session. No external dependencies. No risk of regression if each change is tested in isolation.

---

### Phase 1: Foundation (1-5 days each, prerequisite for Phase 2)

| ID | Action | Estimated Time | Precondition |
|----|--------|----------------|--------------|
| R-005 | Refactor `core/system_context.py` to registration pattern | 1-2 days | None |
| R-008 | DataServiceClient execution policy abstraction | 3-5 days | None (independent) |

**Phase 1 notes**: R-005 and R-008 can run in parallel on a 2-person team. R-005 eliminates Cycle 4 (core -> {dataframes, services, automation, metrics}). R-008 creates the extension point that makes future endpoint additions cheap. Neither is blocking for Phase 2, but both improve the codebase before the more invasive Phase 2 work.

**Phase 1 total**: 4-7 days combined, or 3-5 days if parallelized.

---

### Phase 2: Consolidation (3-10 days, builds on Phase 1)

| ID | Action | Estimated Time | Precondition |
|----|--------|----------------|--------------|
| R-006 | Extract `build_dataframe()` to DataFrameService | 1.5 days | None (but cleaner after R-005) |
| R-009 | Holder type registry in persistence | 1.5-2 days | None (can run parallel) |
| R-004 | Externalize classification rules (if U-002 triggered) | 1 day | U-002 resolved |

**Phase 2 notes**: R-006 eliminates the models -> dataframes reverse dependency, resolving Cycle 1. R-009 eliminates the fragile explicit-Holder-import pattern in persistence. Both are medium-effort with well-defined scope. Run full test suite after each.

**Phase 2 total**: 4-5 days.

---

### Phase 3: Evolution (5-10 days, long-term architectural improvement)

| ID | Action | Estimated Time | Precondition |
|----|--------|----------------|--------------|
| R-010 | Decouple `query/engine.py` from services via protocol | 3 days | R-006 complete (clean service boundaries) |
| Task.save() extraction | Extract `Task.save()`/`Task.save_sync()` to `TaskService.save()` | 1 day | Independent |
| Business -> DataServiceClient | Replace TYPE_CHECKING import with `InsightsProvider` protocol | 0.5 day | Independent |

**Phase 3 notes**: These are low-urgency improvements that pay down structural debt without addressing immediate risks. Do these opportunistically when working in the affected subsystems.

**Phase 3 total**: ~4.5 days.

---

### Timeline Summary (1-2 Engineer Team)

```
Week 1: Phase 0 (R-001, R-007, R-003, R-002)
Week 2: Phase 1 begins (R-005 parallel with R-008)
Week 3: Phase 1 completes; Phase 2 begins (R-006, R-009)
Week 4: Phase 2 completes
Week 5+: Phase 3 (opportunistic, no deadline)
```

Total estimated effort: ~14-18 engineer-days for Phases 0-2. Phase 3 is 4-5 additional days.

---

## 6. Migration Readiness Assessments

### R-005: core/system_context.py Refactor to Registration Pattern

**Current State**: `core/system_context.py` imports from 5 subsystems (models.business.registry, models.business._bootstrap, dataframes.models.registry, dataframes.watermark, services.resolver, metrics.registry) to manage 8 singletons via explicit `reset_all()`. This creates upward dependencies from the foundation layer (core/) into subsystem layers.

**Target State**: `core/system_context.py` maintains a `_reset_registry: list[Callable[[], None]]` that singletons populate at module load time. The `reset_all()` function iterates over registered callbacks. `core/` has no imports from upper layers. Cycle 4 is eliminated.

**Migration Path**:
1. Add `register_reset(fn)` and `reset_all()` to a new `ResetRegistry` class in `core/system_context.py`. Keep existing `reset_all()` working during transition.
2. In each singleton module (start with one: SchemaRegistry), add `SystemContext.register_reset(SchemaRegistry.reset)` at module load. Verify test isolation still works.
3. Migrate remaining singletons one at a time, verifying tests after each.
4. Once all 8 singletons are registered, remove the explicit imports from `system_context.py` and the old `reset_all()` body.
5. Run `pytest` with `-x` flag after each step; stop and debug before proceeding on any failure.

**Rollback Strategy**: The registration mechanism can coexist with the explicit approach during migration. The old `reset_all()` body can remain commented out until all singletons are migrated and verified.

**Green-to-Green Gates**:
- All existing `pytest tests/` pass after each singleton migration.
- `pytest -k "reset" --tb=short` shows no failures.
- No new flaky tests introduced (run the suite 3x to confirm stability).

---

### R-006: Extract `Project.build_dataframe()` / `Section.build_dataframe()` to DataFrameService

**Current State**: `models/project.py` contains `build_dataframe()` and `build_section_dataframe()` convenience methods with deferred imports of `ProgressiveProjectBuilder`, `get_schema`, `section_persistence`, `DataFrameCacheIntegration`. `models/section.py` contains `build_dataframe()` with deferred imports of `SectionDataFrameBuilder`, `get_schema`.

**Target State**: `services/dataframe_service.py` exposes `build_for_project(project: Project, ...) -> DataFrame` and `build_for_section(section: Section, ...) -> DataFrame`. `models/project.py` and `models/section.py` contain no imports from `dataframes/`. Cycle 1 (models <-> dataframes in the models -> dataframes direction) is eliminated.

**Migration Path**:
1. Add new functions to `services/dataframe_service.py` -- do not remove old methods yet.
2. Update one caller of `project.build_dataframe()` to use `dataframe_service.build_for_project(project)`. Verify tests pass.
3. Update all remaining callers (audit via grep: `\.build_dataframe\(\)` and `\.build_section_dataframe\(\)`).
4. Once all callers are updated, remove the convenience methods from `models/project.py` and `models/section.py` and remove the deferred imports.
5. Verify `from autom8_asana.models import Project; p = Project(...)` does not trigger any dataframes import.

**Rollback Strategy**: The convenience methods can be kept as thin wrappers calling the service functions during transition. If any downstream breakage appears, the wrappers can remain until the cause is identified.

**Green-to-Green Gates**:
- `pytest tests/unit/models/` passes throughout migration.
- `pytest tests/unit/dataframes/` passes throughout migration.
- `pytest tests/unit/services/` passes after new service methods are added.
- Static analysis confirms no imports of `dataframes/` remain in `models/project.py` and `models/section.py` after completion.

---

### R-008: DataServiceClient Execution Policy Abstraction

**Current State**: Five endpoint modules in `clients/data/_endpoints/` each implement the same 8-step orchestration pattern (50-80 LOC each). Supporting modules (`_retry.py`, `_cache.py`, `_response.py`, `_metrics.py`) are shared, but the orchestration flow is not.

**Target State**: A `DefaultEndpointPolicy` in `clients/data/_policy.py` owns the 8-step orchestration. Each endpoint module provides only endpoint-specific logic: path construction, request serialization, response type mapping. Per-endpoint LOC drops from ~50-80 to ~20-30.

**Migration Path**:
1. Create `clients/data/_policy.py` with `EndpointPolicy` protocol and `DefaultEndpointPolicy` concrete implementation. Do not change any endpoint modules yet.
2. Refactor one endpoint (start with `_endpoints/simple.py` -- simplest) to use `DefaultEndpointPolicy`. Verify all tests for that endpoint pass.
3. Repeat for `insights.py`, `reconciliation.py`, `export.py`, `batch.py`.
4. Once all 5 endpoints are refactored, verify `clients/data/client.py` still composes them correctly.
5. Run `pytest tests/unit/clients/data/` and integration tests.

**Rollback Strategy**: Because each endpoint module is migrated independently, any endpoint can be rolled back by restoring its pre-migration state. The `DefaultEndpointPolicy` can exist without all endpoints using it.

**Green-to-Green Gates**:
- `pytest tests/unit/clients/` passes after each endpoint migration.
- API integration tests (`pytest tests/api/`) pass after all endpoints migrated.
- Smoke test against production data service (if available) shows identical response shapes.

---

## 7. Decomposition Health Score

**Overall Score: 68 / 100**

This score reflects a codebase that is architecturally coherent and production-ready, with specific identifiable improvements available. The score is not a critique -- a score in this range is appropriate for a 115K LOC codebase at early-consolidation stage.

### Dimension Breakdown

| Dimension | Score | Justification |
|-----------|-------|---------------|
| **Modularity** | 65/100 | 22 well-classified directory units with clear responsibilities. Deducted for 6 circular dependency cycles (all mitigated), convenience method leaks in models/, and core/ upward dependencies. |
| **Coupling** | 60/100 | Clean unidirectional dependencies in the common case (API -> Services -> Subsystems). Deducted for top-3 coupling hotspots (models<->clients 72, models<->dataframes 68, models<->persistence 65), all with at least one accidental direction. |
| **Cohesion** | 75/100 | Most subsystems have clear, focused responsibilities. Deducted for `automation/` containing 3 distinct concerns (legacy pipeline, event system, workflows), `core/` containing upward-dependency violations, and `services/` being a flat bag without internal organization. |
| **Extensibility** | 65/100 | Protocol-based DI at SDK boundary is strong. YAML-driven lifecycle configuration is excellent. Deducted for DataServiceClient scaffolding cost per new endpoint, holder_construction.py explicit type coupling, and classification rules hardcoded in Python. |
| **Testability** | 80/100 | 1.87:1 test-to-source ratio. Full pytest suite. Comprehensive mocking infrastructure (respx, fakeredis, moto). Deducted for module-level singletons requiring coordinated reset and `core/system_context.py` god-context coupling. |
| **Operational Readiness** | 65/100 | Strong: multi-tier SWR caching, circuit breakers, retry with exponential backoff, checkpoint resume, structured logging, OpenTelemetry. Deducted for one unverified Lambda entry point (cloudwatch.py), one medium-risk entry point pending verification (conversation_audit.py), and pre-existing test failures noted in prior art (test_adversarial_pacing.py, test_paced_fetch.py -- status unknown). |

### Subsystem Scores (inherited from ARCHITECTURE-ASSESSMENT.md Section 7)

| Subsystem | Score | Key Strength | Key Weakness |
|-----------|-------|--------------|--------------|
| `transport/` | 96/100 | Clean protocol-based design, leaf node | None significant |
| `lifecycle/` | 92/100 | YAML-driven extensibility, clean boundary | lifecycle -> automation/seeding dependency |
| `query/` | 84/100 | Excellent internal DSL design | Direct services import in engine |
| `models/` | 80/100 | Excellent domain cohesion | Convenience method leaks |
| `persistence/` | 80/100 | Well-designed UoW coordinator | holder_construction.py hierarchy coupling |
| `api/` | 80/100 | Clean layered routing | auth <-> api cycle (low severity) |
| `dataframes/` | 76/100 | Schema-driven extraction | _clear_resolvable_cache private reach |
| `clients/` | 72/100 | 13 typed resource clients | Endpoint scaffolding duplication |
| `services/` | 72/100 | Clean orchestration boundary | Flat organization, some large files |
| `cache/` | 68/100 | Sophisticated SWR architecture | api.metrics import violation, 70+ exports |
| `core/` | 64/100 | Strong infrastructure primitives | system_context.py upward dependencies |
| `automation/` | 64/100 | Functional event system | 3 concerns in one directory |

---

## 8. Cross-Rite Referrals

### Cross-Rite Referral: XR-ARCH-001
- **Target Rite**: hygiene
- **Concern**: `automation/` directory contains 3 distinct domain concerns in a single directory: (1) legacy pipeline conversion rule (`pipeline.py`, 970 LOC), (2) event system (`events/`: emitter, transport, rules), (3) workflow implementations (`workflows/`: insights_formatter.py 1,476 LOC HTML renderer, conversation_audit, pipeline_transition), and (4) polling scheduler (`polling/`). The `insights_formatter.py` file alone is 1,476 LOC and has no functional relationship to automation rules.
- **Evidence**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/` -- 34 files, 10,768 LOC across 4 sub-packages. ARCHITECTURE-ASSESSMENT.md Risk 7, leverage 3/10.
- **Suggested Scope**: Directory reorganization: extract `automation/workflows/` to a top-level `workflows/` directory, or extract `insights_formatter.py` to a standalone renderer module. No logic changes required -- this is purely a directory structure improvement.
- **Priority**: Low (leverage 3/10). Address opportunistically when working in automation/. Do not block other work on this.

---

### Cross-Rite Referral: XR-ARCH-002
- **Target Rite**: debt-triage
- **Concern**: Query v1 endpoint has a 2026-06-01 sunset date (~3.5 months from analysis date). No consumer inventory has been found in code artifacts. If v1 consumers exist and have not migrated, the sunset requires either an extension or a forced migration.
- **Evidence**: ARCHITECTURE-ASSESSMENT.md Risk Register (Gap 7, low confidence); ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md Gap 7. No consumer list found in any analyzed artifact.
- **Suggested Scope**: Audit API access logs for v1 query endpoint traffic. Identify consumers. Notify and coordinate migration if traffic exists. If v1 has zero traffic, remove the endpoint and close the sunset tracking item.
- **Priority**: Medium-High. Sunset date is 2026-06-01 -- approximately 14 weeks from analysis date. If consumer migration is needed, this requires lead time.

---

### Cross-Rite Referral: XR-ARCH-003
- **Target Rite**: hygiene
- **Concern**: `dataframes/models/registry.py` calls `services.resolver._clear_resolvable_cache` -- a private function in a higher-level module. This is a lower-layer module reaching into a higher-layer's private API for cache coherence.
- **Evidence**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/models/registry.py` line 97: `from autom8_asana.services.resolver import _clear_resolvable_cache`. DEPENDENCY-MAP.md Unknown #4.
- **Suggested Scope**: Expose a `SchemaRegistry.on_schema_change` callback hook (or event) that `services/resolver.py` subscribes to at initialization, eliminating the cross-boundary private function call. This is a ~0.5 day refactor.
- **Priority**: Low. The current code works correctly. Address when working in dataframes/models/registry.py or services/resolver.py.

---

### Cross-Rite Referral: XR-ARCH-004
- **Target Rite**: hygiene
- **Concern**: `models/business/business.py` TYPE_CHECKING import of `DataServiceClient` and `InsightsResponse` creates a conceptual dependency from the domain model layer to the client layer. Even as TYPE_CHECKING only, it ties the Business entity definition to a specific client implementation.
- **Evidence**: `models/business/business.py` lines 35-36 (TYPE_CHECKING block): `from autom8_asana.clients.data import DataServiceClient` and `from autom8_asana.clients.data.models import InsightsResponse`. DEPENDENCY-MAP.md Deep Dive 7.1.
- **Suggested Scope**: Define an `InsightsProvider` protocol in `protocols/` with the method signatures currently type-hinted against `DataServiceClient`. Replace the TYPE_CHECKING import in `business.py` with the protocol import. Estimated effort: 0.5 day.
- **Priority**: Low. TYPE_CHECKING only -- no runtime impact. Address opportunistically.

---

### Cross-Rite Referral: XR-ARCH-005
- **Target Rite**: hygiene
- **Concern**: `cache/integration/dataframe_cache.py` imports `api/metrics.py` (line 22), protected by a `try/except` and `# nosemgrep` suppression. This creates Cycle 5 (cache <-> api) where an infrastructure layer imports from the HTTP layer for metrics emission.
- **Evidence**: DEPENDENCY-MAP.md Hotspot 6 (Score 47), Cycle 5 (Section 6.1). `cache/integration/dataframe_cache.py:22`.
- **Suggested Scope**: Extract the metrics emission contract from `api/metrics.py` into a protocol (e.g., `MetricsEmitter` in `protocols/`). Inject it into DataFrameCache rather than importing directly. This eliminates Cycle 5. Estimated effort: ~0.5-1 day.
- **Priority**: Low. The try/except guard makes this safe. Address when refactoring the cache subsystem.

---

### Cross-Rite Referral: XR-ARCH-006
- **Target Rite**: hygiene
- **Concern**: Two pre-existing test failures (`test_adversarial_pacing.py`, `test_paced_fetch.py`) are noted in the original prior art (ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md Paradox 4) as unresolved. These tests exercise the checkpoint resume system's adversarial behavior. Their current status is unknown from code artifacts.
- **Evidence**: ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md Paradox 4. Both test files referenced as pre-existing failures across all prior workstreams.
- **Suggested Scope**: Run these tests and determine: (a) are they still failing? (b) do they represent behavioral gaps or aspirational test design? If failing: prioritize fixing or removing. If passing: update the record to reflect current state.
- **Priority**: Medium. If these tests represent genuine behavioral gaps in the checkpoint resume system (the primary degraded-mode recovery mechanism), they are a reliability concern.

---

## 9. Unknowns Registry

All unknowns from all three prior phases consolidated and deduplicated, organized by impact severity.

### HIGH Impact

#### Unknown: U-001 -- Whether lifecycle/creation.py handles all automation/pipeline.py scenarios

- **Question**: Are there pipeline transition scenarios that only `automation/pipeline.py` handles and `lifecycle/creation.py` does not? Specifically: `_create_onboarding_comment_async()` (FR-COMMENT-001 through FR-COMMENT-005) and `_validate_post_transition()`.
- **Why it matters**: If yes, `automation/pipeline.py` cannot be deprecated and the dual-path architecture is permanent. If no, a deprecation timeline becomes viable. This is the highest-impact structural unknown in the codebase.
- **Evidence**: `automation/pipeline.py` contains `_create_onboarding_comment_async()` and `_validate_post_transition()` not found in `lifecycle/creation.py`. ARCHITECTURE-ASSESSMENT.md Unknown (Section 9); ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md Unknowns.
- **Suggested source**: Feature comparison of both paths; team knowledge of which pipeline handles which transitions; runtime invocation logging.

---

#### Unknown: U-002 -- Classification rule change frequency

- **Question**: How often do the 33 Offer section names and 14 Unit section names in `models/business/activity.py` (lines 183-263) change in practice?
- **Why it matters**: If monthly or more, hardcoded Python is a significant operational bottleneck and R-004 (YAML externalization) is high-value. If yearly or less, the current design is appropriate and R-004 should not be executed.
- **Evidence**: `models/business/activity.py` lines 183-263; ARCHITECTURE-ASSESSMENT.md Risk 8 (leverage 4/10, uncertainty noted).
- **Suggested source**: `git blame /Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` for the OFFER_CLASSIFIER and UNIT_CLASSIFIER definitions. Check commit frequency for these specific lines.

---

### MEDIUM Impact

#### Unknown: U-003 -- conversation_audit.py bootstrap guard verification

- **Question**: Is the bootstrap guard present in `lambda_handlers/conversation_audit.py`? MEMORY.md states "U-005: Entry-point audit, 1 bootstrap guard added (conversation_audit.py)." The ARCHITECTURE-ASSESSMENT.md flags this as unverified from code artifacts.
- **Why it matters**: If absent, `conversation_audit.py` is a MEDIUM RISK entry point relying solely on the Tier1 defensive guard. A silent correctness failure is possible if that guard is modified.
- **Evidence**: ARCHITECTURE-ASSESSMENT.md Risk 5 (leverage 8/10); TOPOLOGY-INVENTORY.md Section 4.1 (MEDIUM risk classification).
- **Suggested source**: Read `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/conversation_audit.py` -- this resolves in 5 minutes. This is R-001.

---

#### Unknown: U-004 -- Query v1 consumer inventory and migration status

- **Question**: What callers are using the v1 query API endpoint, and have they been notified of the 2026-06-01 sunset (~14 weeks from analysis date)?
- **Why it matters**: If v1 has active consumers, the sunset requires a migration plan. The 14-week window is sufficient for migration if started now, but not if discovered late.
- **Evidence**: ARCHITECTURE-ASSESSMENT.md Risk Register Gap 7; ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md Unknowns.
- **Suggested source**: API access logs, consumer onboarding documentation, or team knowledge. This is a cross-rite referral to debt-triage (XR-ARCH-002).

---

#### Unknown: U-005 -- Deferred import first-call latency in Lambda cold starts

- **Question**: With approximately 120 function-body deferred imports and 180 TYPE_CHECKING imports, what is the cumulative first-call latency impact on Lambda cold starts?
- **Why it matters**: Each deferred import incurs a one-time cost on first invocation. If many fire simultaneously during a cold start (e.g., after the cache warmer invokes `_ensure_bootstrap()`), the latency compounds. The cache warmer front-loads some of these via `_ensure_bootstrap()`, but the full profile is unquantified.
- **Evidence**: DEPENDENCY-MAP.md Unknown #3; ARCHITECTURE-ASSESSMENT.md Unknown (Section 9). `automation/pipeline.py` has 7 deferred imports, `persistence/session.py` has 5, `cache/dataframe/factory.py` has 10.
- **Suggested source**: Lambda cold-start performance profiling via CloudWatch metrics for `cache_warmer` handler initialization time; Python `importtime` profiling in a test environment.

---

#### Unknown: U-006 -- core/system_context.py design intent (organic vs. deliberate)

- **Question**: Was `core/system_context.py` designed as a permanent architectural pattern, or is it a pragmatic test utility that accumulated upward dependencies organically over time?
- **Why it matters**: If permanent, the upward dependencies should be accepted and the layering philosophy updated. If organic, R-005 (registration pattern refactor) is unambiguously correct.
- **Evidence**: Module docstring references "QW-5 (ARCH-REVIEW-1 Section 3.1)" as its origin -- suggesting it was a quality-improvement initiative response. ARCHITECTURE-ASSESSMENT.md AP-1, Risk 1.
- **Suggested source**: Original QW-5 decision-maker; ARCH-REVIEW-1 Section 3.1 document.

---

### LOW Impact

#### Unknown: U-007 -- cloudwatch.py Lambda handler purpose and bootstrap status

- **Question**: What CloudWatch event source does `lambda_handlers/cloudwatch.py` handle, and does it use entity detection (requiring bootstrap)?
- **Why it matters**: This handler was not included in the original entry-point audit (U-005). If it uses entity detection without a bootstrap guard, it is a low-severity correctness risk.
- **Evidence**: File exists at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cloudwatch.py` but is not in the original entry-point audit. TOPOLOGY-INVENTORY.md Section 3.2 (Medium confidence for bootstrap status).
- **Suggested source**: Read the file. This resolves in 10 minutes. This is R-007.

---

#### Unknown: U-008 -- Pre-existing test failures status (test_adversarial_pacing.py, test_paced_fetch.py)

- **Question**: Are `test_adversarial_pacing.py` and `test_paced_fetch.py` still failing? If so, do they represent behavioral gaps or aspirational test design?
- **Why it matters**: If these tests represent actual behavioral gaps in the checkpoint resume system, they are a reliability concern for degraded-mode recovery. If they are test design issues, they are technical debt.
- **Evidence**: ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md Paradox 4 -- described consistently as pre-existing failures across all prior workstreams.
- **Suggested source**: Run `pytest tests/ -k "adversarial_pacing or paced_fetch" --tb=short`. This resolves in under 5 minutes. Referred to hygiene rite as XR-ARCH-006.

---

#### Unknown: U-009 -- Internal router and admin router endpoint inventory

- **Question**: What endpoints does the `internal` router (`api/routes/internal.py`) expose? What are the full admin operations beyond the 1 POST identified?
- **Why it matters**: These routes are hidden from OpenAPI schema (`include_in_schema=False`). The admin router is 475 LOC -- substantial for a single POST endpoint. These may include cache management, configuration reload, or other operational endpoints.
- **Evidence**: TOPOLOGY-INVENTORY.md Unknown (Section 8): "Admin Router Full Endpoint Inventory" and "Internal Router Endpoint Details."
- **Suggested source**: Read `api/routes/internal.py` and `api/routes/admin.py`. Low-impact for architecture, but relevant for operational documentation.

---

#### Unknown: U-010 -- Polling CLI deployment status

- **Question**: Is `automation/polling/cli.py` deployed in production, or is it exclusively a development tool?
- **Why it matters**: If deployed, it is an additional production entry point requiring bootstrap and monitoring consideration.
- **Evidence**: `pyproject.toml` comment: "scheduler: Polling scheduler for development mode (production uses cron)". TOPOLOGY-INVENTORY.md Unknown (Section 8).
- **Suggested source**: Deployment configuration, infrastructure documentation, team knowledge.

---

## 10. Scope and Limitations

This analysis covers the structural architecture of the `autom8y-asana` codebase as of 2026-02-23. The following dimensions are explicitly NOT assessed and remain outside the scope of this report.

**Runtime Behavior**: Performance characteristics (latency, throughput, memory consumption under production load) are not assessed. The cache subsystem in particular has complexity visible only under load. Lambda cold-start latency profiles for the 120+ deferred imports are unquantified. These may be partially addressed by the operations rite or 10x-dev rite.

**Data Architecture**: Data flow governance between the entity cache and DataFrame cache, consistency guarantees at cache boundaries, data retention policies, and PII handling scope within `clients/data/` are not assessed beyond the structural boundary (the `_pii.py` module exists and the contract is documented). A data architecture review would be a separate engagement.

**Operational Concerns**: Deployment pipeline health, observability coverage gaps (beyond what autom8y-telemetry provides structurally), incident response playbooks, Lambda concurrency limits, and ECS scaling behavior are not assessed. The `runbooks/` directory exists but was not analyzed.

**Organizational Alignment**: Conway's Law effects on the dual creation pipeline, team ownership boundaries for the `automation/` vs. `lifecycle/` split, and cognitive load distribution across the 22 subsystems are not assessed. The canonical designation of lifecycle/ over automation/ has organizational as well as technical dimensions.

**Evolutionary Architecture**: Fitness functions, architectural runway against anticipated entity type growth beyond 17, and technical debt trajectory for the deferred items (D-002 v1 router removal 2026-06-01, D-022a/D-022b pipeline migration items) are not assessed in this report. The debt ledger at `/Users/tomtenuta/Code/autom8y-asana/docs/debt/LEDGER-cleanup-modernization.md` is the primary instrument for these.

**External Platform SDK Dependencies**: The 7 `autom8y-*` platform dependencies (autom8y-config, autom8y-http, autom8y-cache, autom8y-log, autom8y-core, autom8y-telemetry, autom8y-auth) are treated as black boxes in this analysis. Their internal architecture, versioning health, and coupling patterns are outside scope.

**Security Posture**: PII redaction in `clients/data/_pii.py` is noted structurally and the contract is documented (`XR-003` in MEMORY.md). A full security assessment is outside scope and would be routed to the security rite.

---

*Report produced by the remediation-planner agent, Phase 4 of 4 in the arch rite DEEP-DIVE workflow.*
*All file paths are absolute. All findings trace to evidence in TOPOLOGY-INVENTORY.md, DEPENDENCY-MAP.md, or ARCHITECTURE-ASSESSMENT.md.*
*Target repository was not modified during this analysis.*
