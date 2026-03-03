# Architecture Assessment: autom8y-asana

**Analysis Unit**: directory (single repo, subsystem-level boundaries)
**Repo Path**: `/Users/tomtenuta/Code/autom8y-asana`
**Source Root**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana`
**Date**: 2026-02-23
**Complexity**: DEEP-DIVE
**Upstream**: TOPOLOGY-INVENTORY.md, DEPENDENCY-MAP.md, ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md

---

## 1. Executive Summary

autom8y-asana is a 115K LOC async Python SDK at the boundary between late growth and early consolidation. The architecture is structurally sound for its current scale, with clean layered patterns (API -> Services -> Subsystems) in the common case and sophisticated domain modeling (17 entity types, descriptor-driven wiring, multi-tier SWR caching). Six circular dependency cycles exist at the directory level, all mitigated at runtime via deferred imports. The primary structural risks are: (1) `core/system_context.py` acting as a god-context with upward dependencies into 6 subsystems, creating the root cause of the largest dependency cycle; (2) the dual creation pipeline (lifecycle/ canonical vs. automation/pipeline.py legacy) where convergence is blocked by a genuine philosophical divergence in field seeding strategy; (3) residual scaffolding duplication in DataServiceClient endpoint modules that has been substantially reduced but not eliminated. The codebase benefits from strong test coverage (1.87:1 test-to-source ratio), explicit ADR documentation for intentional trade-offs, and a proven consolidation trajectory. The implicit architectural philosophy is "modular monolith with protocol-based seams" -- a coherent foundation that the code mostly follows, with notable exceptions in the models/ and core/ layers where convenience methods create reverse dependencies.

---

## 2. Anti-Pattern Inventory

### AP-1: God Context -- `core/system_context.py`

**Classification**: God Module (centralized knowledge of 8 singletons across 6 subsystems)
**Severity**: Medium
**Confidence**: High

**Evidence**:
- File: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/system_context.py` (87 LOC)
- Imports from: `models.business.registry`, `models.business._bootstrap`, `dataframes.models.registry`, `dataframes.watermark`, `services.resolver`, `metrics.registry`, `settings`
- Fan-out: 7 imports into 5 distinct subsystems from what should be the foundational layer

**Why this is an anti-pattern**: `core/` is classified as a Layer (foundational shared primitives) with Very High fan-in (12 units depend on it). By importing from models, dataframes, services, and metrics, `system_context.py` creates upward dependencies from the foundation layer into subsystem layers. This is the root cause of Cycle 4 (core -> {dataframes, services, automation, metrics}). Every unit that depends on `core/` transitively depends on these subsystems at the type level.

**False-positive check**: The module's docstring explicitly states it exists "Per QW-5 (ARCH-REVIEW-1 Section 3.1)" to provide a single `reset_all()` for test isolation. This is an intentional design decision for test ergonomics. However, the upward dependency direction is architecturally incorrect regardless of intent -- a registry-of-registries should be in a neutral location (e.g., a `testing/` module) or use a registration pattern where subsystems register their reset functions with core, rather than core importing from subsystems.

**Accepted trade-off assessment**: Partially. The convenience for test fixtures is real, but the layering violation constrains refactoring freedom for all 12 units that depend on core/.

---

### AP-2: Convenience Method Coupling (models/ -> dataframes/, models/ -> persistence/)

**Classification**: Feature Envy / Layering Violation
**Severity**: Medium
**Confidence**: High

**Evidence**:
- `models/project.py` imports `dataframes.builders.ProgressiveProjectBuilder`, `dataframes.models.registry.get_schema`, `dataframes.section_persistence` (all deferred inside method bodies)
- `models/section.py` imports `dataframes.builders.section.SectionDataFrameBuilder`, `dataframes.models.registry.get_schema` (all deferred)
- `models/task.py` imports `persistence.session.SaveSession`, `persistence.exceptions` (deferred inside `save()` and `save_sync()`)
- Dependency-map coupling scores: models <-> dataframes = 68, models <-> persistence = 65

**Why this is an anti-pattern**: Domain model objects (Project, Section, Task) contain convenience methods (`build_dataframe()`, `save()`) that reach upward into service/infrastructure layers. This creates bidirectional dependencies at the directory level (Cycles 1 and 2), which are the two highest-severity cycles identified by the dependency-analyst. The convenience methods make the model layer depend on its consumers rather than the other way around.

**False-positive check**: The convenience method pattern (e.g., `task.save()` a la Django ORM) is a well-known API design pattern. The deferred imports prevent runtime cycle failures. The question is whether the API ergonomics justify the architectural cost.

**Accepted trade-off assessment**: This appears to be an intentional API design choice (Django-style convenience), but it constrains future extraction of models/ or dataframes/ as independent packages.

---

### AP-3: Residual Scaffolding Duplication in DataServiceClient Endpoints

**Classification**: Duplicate Structure
**Severity**: Low (reduced from original finding)
**Confidence**: High

**Evidence**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/insights.py` (219 LOC): circuit breaker check, get_client, build_retry_callbacks, _execute_with_retry, handle_error_response, parse_success_response, record_success, cache_response
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/simple.py` (234 LOC): Same pattern x2 (appointments + leads): circuit breaker check, get_client, build_retry_callbacks, _execute_with_retry, handle_error_response, parse_success_response, record_success
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/batch.py` (310 LOC): Same scaffolding
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/reconciliation.py` (133 LOC): Same scaffolding
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/export.py` (173 LOC): Same scaffolding

**Status vs. Prior Art**: The prior art identified DataServiceClient as a 2,165-line god object. It has since been decomposed into 7 modules (client.py 1,277 LOC + 5 endpoint modules + supporting modules). The shared retry callbacks have been extracted to `_retry.py:build_retry_callbacks()`, which eliminated ~196 LOC of boilerplate. The `_execute_with_retry()` method on the client provides a common retry loop. However, each endpoint module still replicates the orchestration scaffolding: circuit breaker check -> get_client -> build callbacks -> execute_with_retry -> error handling -> success parsing -> circuit breaker record_success.

**Why this remains an anti-pattern**: Each new endpoint requires ~50-80 lines of structural scaffolding before endpoint-specific logic. The retry/callback infrastructure was extracted, but the higher-level execution policy (the 8-step orchestration) was not. An execution policy abstraction would reduce each endpoint to only its unique logic (path, params, request body, response mapping).

**False-positive check**: The duplication is real but has been significantly reduced from the original finding. The current state is functional and tested. The remaining duplication is primarily orchestration flow, not logic.

---

### AP-4: Circular Dependencies (6 Cycles)

**Classification**: Architectural Cycle
**Severity**: Medium (mitigated at runtime)
**Confidence**: High

**Evidence**: Full inventory in DEPENDENCY-MAP.md Section 6. Summary:

| Cycle | Units | Runtime Mitigated | Structural Impact |
|-------|-------|-------------------|-------------------|
| 1 | models <-> dataframes | Yes (deferred) | Prevents clean extraction of either |
| 2 | models <-> persistence | Yes (deferred) | Prevents clean extraction of either |
| 3 | models <-> core | Yes (TYPE_CHECKING) | Tight entity_registry <-> detection types coupling |
| 4 | core -> {df, svc, auto, metrics} | Yes (deferred in system_context) | Root cause: god-context AP-1 |
| 5 | cache <-> api | Yes (try/except guard) | Single import: cache -> api.metrics |
| 6 | auth <-> api | Yes (nosemgrep) | Auth imports API dependencies |

**Why this is an anti-pattern**: While all 6 cycles are mitigated at runtime (no import errors occur), they represent structural layering violations that: (a) constrain refactoring freedom, (b) create risk that new developers will add non-deferred reverse imports, (c) make the dependency graph harder to reason about, and (d) accumulate ~120 function-body deferred imports whose first-call latency cost is unquantified.

**False-positive check**: Some of these cycles are arguably intentional (e.g., the models <-> dataframes cycle exists because `Project.build_dataframe()` is a convenience method that the team chose to keep). Cycles 5 and 6 are low-severity and localized (single imports each).

---

### AP-5: Dual Creation Pipeline (Lifecycle vs. Automation)

**Classification**: Parallel Implementation
**Severity**: Medium
**Confidence**: High

**Evidence**:
- Lifecycle (canonical): `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/creation.py` (737 LOC) -- 7-step pipeline with AutoCascadeSeeder
- Automation (legacy): `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py` (970 LOC) -- 7-step pipeline with FieldSeeder
- Shared primitives in `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py` (256 LOC): `discover_template_async`, `duplicate_from_template_async`, `generate_entity_name`, `place_in_section_async`, `compute_due_date`, `wait_for_subtasks_async`

**Specific duplication found**:
- `PipelineConversionRule._extract_user_gid()` (lines 730-742) mirrors `EntityCreationService._extract_user_gid()` (lines 700-706) -- identical logic
- `PipelineConversionRule._extract_first_rep()` (lines 744-756) mirrors `EntityCreationService._extract_first_rep()` (lines 712-719) -- identical logic
- `PipelineConversionRule._resolve_assignee_gid()` (lines 612-668) mirrors `EntityCreationService._resolve_assignee_gid()` (lines 601-647) -- nearly identical 4-step cascade
- Both pipelines use the same 7-step flow: resolve context -> duplicate check -> template discovery -> create -> configure (section, due date, subtasks, fields, hierarchy, assignee)

**What blocks full convergence**: The essential difference is at Step 7 (field seeding):
- `FieldSeeder` (automation): Explicit field lists configured per-pipeline (`DEFAULT_BUSINESS_CASCADE_FIELDS`, `DEFAULT_UNIT_CASCADE_FIELDS`, `DEFAULT_PROCESS_CARRY_THROUGH_FIELDS`)
- `AutoCascadeSeeder` (lifecycle): Zero-config name matching -- any field with the same name on source and target cascades automatically, with YAML-driven exclude lists

This is a genuine philosophical divergence (explicit vs. convention-over-configuration), not accidental duplication.

**False-positive check**: The MEMORY.md notes "Pipeline divergence: lifecycle is canonical path, automation retained for essential differences" and "D-022 (full pipeline consolidation) CLOSED -- WS6 extracted sufficient shared surface." This is an acknowledged, intentional coexistence. The 6 shared primitives in `core/creation.py` demonstrate deliberate convergence effort.

---

### AP-6: Module-Level Singleton Pattern (DataFrameCache, SchemaRegistry, ProjectTypeRegistry)

**Classification**: Hidden Global State
**Severity**: Low
**Confidence**: Medium

**Evidence**:
- `cache/dataframe/factory.py`: `_cache_instance` module singleton for DataFrameCache
- `dataframes/models/registry.py`: `SchemaRegistry` singleton via `get_instance()` class method
- `models/business/registry.py`: `ProjectTypeRegistry` singleton via `get_registry()` module function
- `services/resolver.py`: `EntityProjectRegistry` singleton via `get_instance()` class method
- `core/system_context.py`: `reset_all()` resets all 8 singletons (demonstrating the scope of global state)

**Why this is a pattern to note**: Eight module-level singletons require coordinated reset for test isolation. The `SystemContext.reset_all()` god-context (AP-1) exists specifically because of this. Each singleton is individually reasonable; the aggregate creates test fragility and makes the application's initialization order load-bearing.

**False-positive check**: Module-level singletons are idiomatic Python and appropriate for this codebase's deployment model (single-process ECS/Lambda). The `SystemContext.reset_all()` pattern demonstrates the team is managing this deliberately.

---

## 3. Boundary Alignment Assessment

### 3.1 models/ (Entity Layer)

**Domain alignment**: Strong. The 17 entity types (Business -> Contact, Unit, Offer, Process, Location, Hours, DNA, AssetEdit, Reconciliation, Videography + 7 Holders) map directly to the CRM/pipeline domain.

**Boundary issues**:
- `models/project.py` and `models/section.py` contain `build_dataframe()` convenience methods that cross into the dataframes subsystem (Cycle 1)
- `models/task.py` contains `save()` and `save_sync()` that cross into persistence (Cycle 2)
- `models/business/business.py` TYPE_CHECKING import of `DataServiceClient` creates a conceptual dependency on the client layer

**Public API surface**: 60+ exported classes and functions -- wide but appropriate for a domain model layer

**Assessment**: Cohesive domain boundary with 3 specific convenience-method leaks. The leaks are localized and deferred. Score: 4/5 alignment.

---

### 3.2 cache/ (Multi-Tier Caching)

**Domain alignment**: Strong. 53 files, 16,103 LOC dedicated to multi-tier SWR caching -- the largest subsystem, reflecting the caching subsystem's genuine complexity.

**Boundary issues**:
- `cache/integration/dataframe_cache.py` imports `api/metrics.py` (Cycle 5) -- a layering violation where the cache layer reaches up to the API layer for metrics emission
- `cache/integration/schema_providers.py` imports `dataframes/` schema types (bidirectional coupling with dataframes, Score 46)
- `cache/integration/` acts as an explicit bridge module for cross-subsystem integration, which is architecturally intentional

**Public API surface**: 70+ exported symbols -- very wide, reflecting the subsystem's internal complexity

**Assessment**: Well-bounded subsystem with one clear layering violation (cache -> api.metrics). The bridge modules in `cache/integration/` are an appropriate pattern for managing the cache-dataframes bidirectional relationship. Score: 3.5/5 alignment.

---

### 3.3 dataframes/ (DataFrame Extraction)

**Domain alignment**: Strong. Schema-driven extraction of Asana task data into typed Polars DataFrames.

**Boundary issues**:
- Bidirectional coupling with models/ (Score 68) -- extractors inherently need model types, but models/ convenience methods reach back
- `dataframes/models/registry.py` imports `services.resolver._clear_resolvable_cache` -- reaches across boundaries to a private function in a higher layer
- Bidirectional coupling with cache/ (Score 46) -- intentional via bridge modules

**Public API surface**: 30+ exports -- appropriately sized

**Assessment**: Solid domain boundary with one notable private-API reach (`_clear_resolvable_cache`). The bidirectional coupling with models/ and cache/ is partially intentional (bridge modules) and partially accidental (convenience methods). Score: 3.5/5 alignment.

---

### 3.4 persistence/ (SaveSession / UoW)

**Domain alignment**: Strong. Unit of Work pattern for batched Asana API operations.

**Boundary issues**:
- `persistence/holder_construction.py` has deep knowledge of 6 specific Holder types (ContactHolder, LocationHolder, OfferHolder, ProcessHolder, UnitHolder, Business), creating tight coupling to the entity hierarchy
- Models -> persistence reverse dependency via `Task.save()` convenience method

**Public API surface**: SaveSession (main), EntityState, OperationType, PlannedOperation, SaveResult, plus CascadeExecutor and HealingManager -- focused

**Assessment**: The SaveSession coordinator pattern (1,854 LOC, 58 methods, 14 collaborators) is appropriate for the UoW pattern per prior analysis. The boundary is clean except for the holder_construction.py deep hierarchy knowledge and the Task.save() reverse dependency. Score: 4/5 alignment.

---

### 3.5 lifecycle/ (Canonical Pipeline Engine)

**Domain alignment**: Strong. YAML-driven lifecycle automation with 9 stages.

**Boundary issues**:
- Depends on `core/creation.py` for 6 shared primitives (appropriate -- core provides to lifecycle)
- Depends on `automation/seeding.py` via `lifecycle/seeding.py` (AutoCascadeSeeder reuses FieldSeeder infrastructure)
- Clean unidirectional dependencies on models/ and resolution/

**Public API surface**: LifecycleEngine, AutomationDispatch, EntityCreationService, plus YAML config types -- appropriately sized

**Assessment**: Clean boundary with appropriate dependency directions. The lifecycle -> automation/seeding dependency is a pragmatic code reuse choice. Score: 4.5/5 alignment.

---

### 3.6 clients/ (Asana API + Data Service)

**Domain alignment**: Strong. Two distinct client layers coexist in one directory.

**Boundary issues**:
- Asana resource clients (22 files, 8,705 LOC) -> models/ is essential and unidirectional
- DataServiceClient (14 files, 3,024 LOC) has been decomposed from a god object into focused modules
- `clients/task_ttl.py` imports `models.business.detect_entity_type_from_dict` -- reaching into business logic
- `clients/data/client.py` manages its own circuit breaker and retry separately from the platform SDK -- intentional per docstring (avoids double-applying)

**Public API surface**: 13 Asana resource clients + DataServiceClient + supporting types

**Assessment**: The Asana clients have clean boundaries. DataServiceClient decomposition has improved significantly but retains endpoint scaffolding duplication (AP-3). The two client layers (Asana vs. Data Service) could be in separate directories for clarity. Score: 3.5/5 alignment.

---

### 3.7 query/ (Query DSL v2)

**Domain alignment**: Strong. Composable predicate filtering and aggregation for DataFrame cache.

**Boundary issues**:
- `query/engine.py` imports `services.query_service.EntityQueryService` and `services.resolver.to_pascal_case` directly -- mixing layers (query engine depends on services layer)
- `query/engine.py` imports `dataframes.models.registry.SchemaRegistry` directly

**Public API surface**: QueryEngine, PredicateCompiler, AggregationCompiler, predicate types, RowsRequest/Response -- well-scoped

**Assessment**: Clean internal design (compiler, engine, models separation), but the QueryEngine directly reaches into services/ and dataframes/ rather than having these injected. The engine conflates orchestration (getting DataFrames via service) with computation (compiling and executing predicates). Score: 3.5/5 alignment.

---

## 4. SPOF Register

### SPOF-1: DataFrameCache Singleton

**Component**: `cache/dataframe/factory.py` (`_cache_instance` module singleton)
**Fan-in**: All query operations, cache warming, section timeline service
**Cascade path**: DataFrameCache failure -> all query endpoints return 503 -> all DataFrame-dependent features unavailable
**Redundancy**: Memory tier + S3 tier + circuit breaker. If memory is lost (process restart), S3 provides fallback. If S3 is unavailable, circuit breaker prevents thundering herd.
**Assessment**: Well-designed redundancy via tiered architecture. The singleton is a process-level SPOF (expected in Lambda/ECS), not a system-level SPOF. **Risk: Low.**

### SPOF-2: ProjectTypeRegistry (Bootstrap Dependency)

**Component**: `models/business/registry.py` (ProjectTypeRegistry singleton)
**Fan-in**: All entity detection, all hydration, all lifecycle operations
**Cascade path**: If bootstrap fails or hasn't run -> empty registry -> all entity detection returns UNKNOWN -> incorrect entity processing throughout system
**Redundancy**: Tier1 defensive guard in `detection/tier1.py` (lines 91-105) provides last-resort safety net. Entry-point audit (U-005) confirmed 2 covered, 1 medium risk, 2 low risk.
**Assessment**: The bootstrap dependency is a structural SPOF mitigated by defensive guards. The `conversation_audit.py` Lambda handler remains the one entry point with MEDIUM RISK (per entry-point audit). **Risk: Medium.**

### SPOF-3: `core/system_context.py` as Test Infrastructure SPOF

**Component**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/system_context.py`
**Fan-in**: All test fixtures that need state reset
**Cascade path**: If `reset_all()` misses a singleton or the reset order is wrong -> stale state leaks between tests -> flaky test failures
**Redundancy**: None -- this is the single point for all singleton resets
**Assessment**: Adding any new singleton requires updating this file. If forgotten, test isolation silently breaks. **Risk: Low-Medium** (test infrastructure, not production).

### SPOF-4: Asana API (External Dependency)

**Component**: All operations via `transport/asana_http.py`
**Fan-in**: All 13 Asana resource clients, cache warming, entity creation, persistence
**Cascade path**: Asana API outage -> all write operations fail, cache warming fails, new entity creation fails. Read operations served from cache remain available.
**Redundancy**: Multi-tier SWR cache (Redis hot + S3 cold) provides read resilience. Checkpoint resume in cache warmer provides warming resilience. No write resilience (expected -- can't write to Asana if Asana is down).
**Assessment**: Well-mitigated for reads via cache architecture. Writes have no fallback by design. **Risk: Inherent, well-mitigated.**

### SPOF-5: autom8-data API (External Dependency for Insights)

**Component**: `clients/data/client.py` (DataServiceClient)
**Fan-in**: Insights export, conversation audit, reconciliation, appointments, leads
**Cascade path**: autom8-data outage -> insights endpoints fail, cache fallback (ADR-INS-004) provides stale data -> if no stale data cached, full outage for insights features
**Redundancy**: Circuit breaker, retry with exponential backoff, client-side cache fallback (stale-while-revalidate)
**Assessment**: Good resilience infrastructure. Cache fallback provides graceful degradation. **Risk: Low-Medium.**

---

## 5. Prior Art Validation

### 5.1 Opportunities

#### Opportunity 1: DataServiceClient as an Execution Policy Layer

**Status**: Partially Resolved
**Code Evidence**:
- Client decomposed from 2,165 LOC monolith to 1,277 LOC client.py + 5 endpoint modules (1,069 LOC combined) + 5 supporting modules (_retry.py 191 LOC, _cache.py 194 LOC, _response.py 270 LOC, _metrics.py 54 LOC, _pii.py 73 LOC, _normalize.py 58 LOC)
- `_retry.py:build_retry_callbacks()` extracts the retry callback factory (eliminates ~196 LOC of boilerplate per the module docstring)
- `client.py:_execute_with_retry()` provides a shared retry loop
- Each endpoint module delegates to these shared facilities

**Updated Assessment**: The highest-ROI extraction (retry callbacks) has been done. The remaining opportunity is the higher-level execution policy (the ~50-80 LOC scaffolding pattern per endpoint). Severity reduced from High to Medium. The original characterization of DataServiceClient as a "2,165-line god object" is no longer accurate.

#### Opportunity 2: Classification Layer as a Configuration Surface

**Status**: Confirmed (unchanged)
**Code Evidence**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` lines 183-263: 33 Offer sections and 14 Unit sections hardcoded as Python frozensets in `OFFER_CLASSIFIER` and `UNIT_CLASSIFIER` module-level instances
- The `SectionClassifier.from_groups()` factory method already accepts a dict format that could trivially be loaded from YAML/TOML
- Lifecycle stages already use YAML config (`config/lifecycle_stages.yaml`) for analogous per-stage data

**Updated Assessment**: The opportunity is real and the implementation path is clear (load from YAML instead of Python dict literals). Severity depends on classification rule change frequency, which remains an unknown.

#### Opportunity 3: Query DSL as an Unexploited Foundation

**Status**: Confirmed (unchanged)
**Code Evidence**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py`: Full `execute_rows()` (37 steps) and `execute_aggregate()` (12 steps) implementation
- 10 operators via `Op` enum, composable predicate AST (Comparison, AndGroup, OrGroup, NotGroup), cross-entity joins at depth 1
- Classification-based section filtering integrated (`_resolve_classification()` calls `SectionClassifier`)
- 3 API endpoints: `/rows`, `/aggregate`, `/{entity_type}` (v2)

**Updated Assessment**: The query infrastructure is substantially more capable than minimum requirements. The classification integration (Opportunity 2 + Opportunity 3 together) shows the subsystems are well-composed. Whether the query surface is "unexploited" depends on consumer usage patterns (an unknown).

#### Opportunity 4: Descriptor-Driven Auto-Wiring as a Pattern

**Status**: Confirmed (unchanged)
**Code Evidence**:
- `models/business/descriptors.py` (720 LOC): Descriptor-driven custom field auto-wiring
- `models/business/fields.py` (376 LOC): CascadingFieldDef, InheritedFieldDef registries
- `lifecycle/seeding.py:AutoCascadeSeeder` (306 LOC): Extends the convention-over-configuration pattern to field seeding

**Updated Assessment**: The descriptor pattern has been applied beyond its original scope (entity fields) into lifecycle seeding. The pattern could extend to classification rules (Opportunity 2) and potentially DataFrame schema definitions.

#### Opportunity 5: Lambda Warmer as a Reliability Indicator

**Status**: Confirmed (unchanged)
**Code Evidence**:
- `lambda_handlers/cache_warmer.py`: Checkpoint resume via `lambda_handlers/checkpoint.py` (S3-based)
- Cache warm-up flow documented in DEPENDENCY-MAP.md Section 5.3

**Updated Assessment**: The checkpoint resume pattern is well-implemented. No new findings.

### 5.2 Gaps

#### Gap 1: No Explicit Extension Points for DataServiceClient Endpoints

**Status**: Partially Resolved
**Code Evidence**:
- `_retry.py:build_retry_callbacks()` provides a parameterized callback factory with 7 variation axes (documented in docstring lines 51-59)
- `client.py:_execute_with_retry()` provides the shared retry loop
- Each endpoint module follows a consistent pattern but without a formal protocol/abstract base

**Updated Assessment**: The retry/callback infrastructure is now shared. What's missing is a higher-level "endpoint execution policy" protocol that would make the remaining scaffolding pattern (circuit breaker check -> get_client -> build callbacks -> execute -> handle response -> record success) declarative. Severity reduced from High to Medium.

#### Gap 2: Preload Degraded-Mode Is Undocumented as Architecture

**Status**: Fully Resolved
**Code Evidence**:
- ADR-011 documents the preload fallback as active degraded-mode per MEMORY.md ("SI-4: ADR-011 preload fallback + metric counter")
- `api/preload/legacy.py` is documented as active fallback

**Updated Assessment**: This gap is closed. ADR-011 provides the architectural documentation.

#### Gap 3: No Unified Key Scheme Across Cache Systems

**Status**: Fully Resolved
**Code Evidence**:
- ADR-0067 documents the intentional 12/14-dimension divergence between entity cache and DataFrame cache
- Per MEMORY.md: "Cache divergence is intentional (12/14 dimensions) per ADR-0067"

**Updated Assessment**: This gap is closed. The divergence is intentional, documented, and analyzed.

#### Gap 4: No Abstraction Boundary Between Classification Rules and Classification Engine

**Status**: Confirmed (unchanged)
**Code Evidence**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` lines 48-126: `SectionClassifier` class (engine) and lines 183-263: hardcoded `OFFER_CLASSIFIER` and `UNIT_CLASSIFIER` (rules) are in the same file
- The `from_groups()` factory method (lines 96-126) accepts a dict format, showing the engine/rules separation is architecturally present but not physically separated
- `get_classifier()` function (line 266) provides a lookup API

**Updated Assessment**: The gap persists. The `SectionClassifier` class is the engine; the module-level instances are the rules. They are in the same file with no configuration-loading path.

#### Gap 5: Import-Time Side Effects Without Entry Point Inventory

**Status**: Partially Resolved
**Code Evidence**:
- Entry-point audit completed at `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/ENTRY-POINT-AUDIT.md`
- `models/business/__init__.py` line 63 now explicitly documents: "ARCHITECTURE: Bootstrap registration is now EXPLICIT, not import-time." The module imports `bootstrap` and `register_all_models` from `_bootstrap.py`, but the comment clarifies the intent
- `_bootstrap.py` has explicit `bootstrap()` function (lines 134-165) as the public API, with `is_bootstrap_complete()` guard
- `conversation_audit.py` identified as MEDIUM RISK -- recommended to add bootstrap guard

**Updated Assessment**: The audit exists, the bootstrap mechanism is now explicit (not import-time per the updated `__init__.py` comments), and 2 of 3 relevant entry points are covered. The `conversation_audit.py` guard was recommended but whether it was implemented is not verified from these artifacts.

#### Gap 6: Lifecycle Module Has No Explicit Status as Canonical

**Status**: Confirmed (unchanged)
**Code Evidence**:
- No ADR or module-level docstring in `lifecycle/` declares canonical status
- The `lifecycle/creation.py` docstring (line 1-24) describes the creation flow but does not mention canonical status vs. automation
- `automation/pipeline.py` docstring (lines 1-13) does not mention deprecation or non-canonical status

**Updated Assessment**: The canonical status exists only in WIP documents and MEMORY.md, not in code-level documentation that a new developer would find.

#### Gap 7: Query v1 Sunset Without Migration Path Validation

**Status**: Confirmed (unchanged, low confidence)
**Code Evidence**: No v1 consumer inventory found in the artifacts examined. Sunset date 2026-06-01 (approximately 3.5 months away).

**Updated Assessment**: Cannot evaluate from code artifacts alone. Requires operational data.

### 5.3 Paradoxes

#### Paradox 1: "Immutability vs. Mutable Cache"

**Status**: Confirmed
**Evidence**: Frozen Pydantic models throughout `models/`, mutable CacheEntry with EntryType enum (14 types) and FreshnessState in `cache/models/`
**Updated Assessment**: Architecturally coherent tension (value semantics vs. coordination layer) that is not resolved in documentation. No code change needed, but design documentation would help onboarding.

#### Paradox 2: "Zero-Config vs. Explicit Critical Path"

**Status**: Confirmed
**Evidence**: `AutoCascadeSeeder` (zero-config name matching) vs. `DataServiceClient` (explicit circuit breaker/retry/callback configuration). `lifecycle/creation.py` benefits from shared primitives; `clients/data/` requires explicit parameterization.
**Updated Assessment**: This is a coherent split: domain modeling is zero-config, infrastructure execution is explicit. The tension is real but architecturally appropriate.

#### Paradox 3: "Eliminated Duplication but Seeding Strategies Diverged"

**Status**: Confirmed with additional evidence
**Evidence**:
- 6 of 7 creation steps are shared via `core/creation.py`
- Step 7 divergence is documented: `FieldSeeder` (explicit, `automation/seeding.py`) vs. `AutoCascadeSeeder` (convention, `lifecycle/seeding.py`)
- `AutoCascadeSeeder` reuses `FieldSeeder` infrastructure for enum resolution and API write (line 188: `field_seeder = FieldSeeder(self._client)`)
- Additional duplication found: `_extract_user_gid()`, `_extract_first_rep()`, and `_resolve_assignee_gid()` are independently implemented in both `pipeline.py` and `creation.py` with nearly identical logic (see AP-5)

**Updated Assessment**: The seeding divergence is intentional and well-documented. The helper method duplication (`_extract_user_gid`, `_extract_first_rep`, `_resolve_assignee_gid`) is accidental and extractable to shared utilities in `core/creation.py`.

#### Paradox 4: "Sophisticated Cache but Ignored Test Failures"

**Status**: Unable to verify from current artifacts
**Updated Assessment**: The two pre-existing test failures (`test_adversarial_pacing.py`, `test_paced_fetch.py`) are referenced in prior art but not examined in this analysis. Cannot confirm or refute current status.

#### Paradox 5: "SSoT via Import-Time Registration"

**Status**: Partially Resolved
**Evidence**:
- `_bootstrap.py` now provides explicit `bootstrap()` function (not import-time)
- `models/business/__init__.py` comments clarify: "Bootstrap registration is now EXPLICIT, not import-time"
- `ProjectTypeRegistry._ensure_bootstrapped()` provides lazy bootstrap on first access

**Updated Assessment**: The paradox has been substantially addressed. Bootstrap is now explicit rather than import-time side-effect. The `_ensure_bootstrapped()` lazy guard + explicit `bootstrap()` at entry points resolves the "SSoT with an asterisk" concern for covered entry points.

---

## 6. Architectural Philosophy (DEEP-DIVE)

### 6.1 Implicit Design Philosophy: Modular Monolith with Protocol-Based Seams

The codebase exhibits a consistent architectural philosophy that can be articulated as:

**"A modular monolith organized as layered subsystems with protocol-based extension points at the SDK boundary and direct coupling at the internal boundary."**

Evidence:
1. **Modular monolith**: Single deployment unit (ECS/Lambda) with clear directory-level module boundaries (22 directories, each classified in topology-inventory). No microservice aspirations.

2. **Protocol-based seams at SDK boundary**: `protocols/` directory defines 6 runtime protocols (AuthProvider, CacheProvider, DataFrameCacheProtocol, ItemLoader, LogProvider, ObservabilityHook). `_defaults/` provides default implementations. This is a clean dependency inversion pattern at the public SDK API level.

3. **Direct coupling internally**: Within the codebase, subsystems communicate via direct import rather than protocols. The ~380 cross-boundary imports are almost entirely concrete class references, not protocol implementations. This is appropriate for a monolith -- protocol indirection within a single deployment unit adds overhead without benefit.

4. **Frozen models as value semantics**: Pydantic v2 frozen models throughout `models/` enforce value semantics. Models are created, never mutated. State changes go through persistence/ (SaveSession UoW pattern).

5. **Convention-over-configuration for domain, explicit for infrastructure**: The descriptor-driven auto-wiring and AutoCascadeSeeder follow convention-over-configuration. The transport/client layers use explicit configuration.

### 6.2 Where Practice Diverges from Philosophy

1. **Convenience methods violate modularity**: `Project.build_dataframe()`, `Section.build_dataframe()`, and `Task.save()` create reverse dependencies that violate the layered architecture. The philosophy says "subsystems are independent modules"; the convenience methods say "models know about their consumers."

2. **core/ violates its own foundation role**: `system_context.py` imports from 5 subsystems above it. `core/creation.py` imports from `automation/templates.py` and `automation/waiter.py`. `core/schema.py` imports from `dataframes/models/registry.py`. The philosophy says "core is the foundation"; these imports say "core is also a coordinator."

3. **Protocol-based seams stop at the SDK boundary**: Internally, there are almost no protocols between subsystems. The query engine directly instantiates `EntityQueryService`. The cache warming flow directly calls concrete classes throughout. The philosophy supports protocol-based decoupling; the practice limits it to the public API.

4. **Dual creation paths contradict single-canonical-path philosophy**: The lifecycle/ subsystem is described as canonical, but `automation/pipeline.py` is equally functional and independently maintained. The philosophy says "one canonical path"; the codebase has two.

### 6.3 Emergent Architecture vs. Designed Architecture

**Designed elements** (consistent, deliberate):
- Entity hierarchy (Business -> 10 entity types via Holders)
- Multi-tier SWR caching (Redis hot + S3 cold + memory in-process)
- Query DSL with composable predicate AST
- Lifecycle engine with YAML-driven configuration
- SaveSession UoW pattern with 6-phase commit
- Protocol-based DI at SDK boundary

**Emergent elements** (accumulated, not fully unified):
- `core/system_context.py` grew to manage 8 singletons as they were added
- The `cache/integration/` bridge layer emerged to manage the bidirectional cache-dataframes relationship
- The dual creation pipeline emerged from separate development timelines (automation first, lifecycle later)
- The 120 deferred imports emerged as workarounds for circular dependencies rather than as a designed pattern

### 6.4 North Star Architecture

Based on the strongest patterns in the codebase, a "north star" architecture would:

1. **Extract convenience methods to services**: `DataFrameService.build_for_project()` instead of `Project.build_dataframe()`. `TaskService.save()` instead of `Task.save()`. This eliminates Cycles 1 and 2.

2. **Move SystemContext to a test utilities module**: `tests/_shared/system_context.py` rather than `core/system_context.py`. Subsystems register their reset functions via a registration API rather than core importing from them.

3. **Consolidate creation helper methods**: Move `_extract_user_gid()`, `_extract_first_rep()`, `_resolve_assignee_gid()` to `core/creation.py` as shared utilities.

4. **Add an execution policy abstraction to DataServiceClient**: A base class or protocol that each endpoint implements, reducing per-endpoint scaffolding from ~80 LOC to ~20 LOC.

5. **Document lifecycle canonical status in code**: Module-level docstring in `lifecycle/__init__.py` and deprecation notice in `automation/pipeline.py`.

---

## 7. Module-to-Domain Alignment Scores (DEEP-DIVE)

| Subsystem | Cohesion | Coupling | API Clarity | Testability | Extensibility | Overall |
|-----------|----------|----------|-------------|-------------|---------------|---------|
| **models/** | 5 | 3 | 4 | 4 | 4 | 4.0 |
| **cache/** | 4 | 3 | 3 | 4 | 3 | 3.4 |
| **dataframes/** | 4 | 3 | 4 | 4 | 4 | 3.8 |
| **persistence/** | 5 | 4 | 4 | 4 | 3 | 4.0 |
| **lifecycle/** | 5 | 4 | 5 | 4 | 5 | 4.6 |
| **clients/** | 4 | 3 | 4 | 4 | 3 | 3.6 |
| **query/** | 5 | 3 | 5 | 4 | 4 | 4.2 |
| **automation/** | 3 | 3 | 3 | 4 | 3 | 3.2 |
| **services/** | 4 | 3 | 3 | 4 | 4 | 3.6 |
| **core/** | 3 | 2 | 4 | 4 | 3 | 3.2 |
| **api/** | 4 | 4 | 4 | 4 | 4 | 4.0 |
| **transport/** | 5 | 5 | 5 | 5 | 4 | 4.8 |

**Score Rationale**:

- **models/ (4.0)**: Excellent cohesion (all entity types in one place) but coupling issues from convenience methods. Wide API surface is appropriate for the domain.
- **cache/ (3.4)**: Cohesive internally but large (16K LOC, 53 files). The 70+ export surface is wide. The api.metrics import is a coupling violation.
- **dataframes/ (3.8)**: Clean internal organization (builders, extractors, models, resolver, schemas, views). The `_clear_resolvable_cache` cross-boundary reach lowers coupling score.
- **persistence/ (4.0)**: SaveSession is a well-designed coordinator. `holder_construction.py` deep entity hierarchy knowledge is the main coupling concern.
- **lifecycle/ (4.6)**: Highest-scoring subsystem. Clean boundary, YAML-driven extensibility, clear public API. Only docked for the `automation/seeding.py` dependency.
- **clients/ (3.6)**: Two distinct client layers in one directory. DataServiceClient endpoint scaffolding duplication lowers extensibility.
- **query/ (4.2)**: Excellent internal design (compiler, engine, models). Docked for direct service/dataframe imports in engine.
- **automation/ (3.2)**: Lowest-scoring functional subsystem. Contains the legacy pipeline, workflows (including the 1,476 LOC insights_formatter), and polling scheduler -- three distinct concerns in one directory.
- **services/ (3.6)**: Orchestration layer doing its job. Some services are very large (section_timeline 727 LOC, resolver 718 LOC). The layer boundary is clear but the internal organization is a flat bag of services.
- **core/ (3.2)**: Foundation layer with upward dependency violations. `entity_registry.py` (859 LOC) and `retry.py` (836 LOC) are appropriate; `system_context.py`, `schema.py`, and `creation.py` violate layering.
- **transport/ (4.8)**: Highest score. 6 files, 1,716 LOC, clean protocol-based design, no upward dependencies, leaf node in the dependency graph.

---

## 8. Risk Register

### Risk 1: core/system_context.py Layering Violation Creates Hidden Coupling

**Severity**: Medium | **Likelihood**: Medium | **Proximity**: Ongoing
**Category**: Structural
**Classification**: Strategic Investment (high impact, medium effort)
**Leverage Score**: 6/10

**Description**: The god-context pattern (AP-1) creates a hidden dependency where all 12 units that depend on `core/` transitively depend on models, dataframes, services, and metrics through `system_context.py`. Any change to singleton management in those subsystems can break core/, and adding new singletons requires updating core/.

**Evidence**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/system_context.py` imports from 5 subsystems.

**Impact if realized**: Increased cognitive load for developers, fragile test isolation if reset order changes, constraint on future subsystem extraction.

---

### Risk 2: Dual Creation Pipeline Drift

**Severity**: Medium | **Likelihood**: Medium | **Proximity**: 3-6 months
**Category**: Structural
**Classification**: Long-term Transformation
**Leverage Score**: 5/10

**Description**: `lifecycle/creation.py` and `automation/pipeline.py` implement the same 7-step creation flow with duplicated helper methods and diverged seeding strategies. Without clear canonical status documentation in code, new features may be added to either path, causing drift and increasing the cost of future consolidation.

**Evidence**: 3 duplicated helper methods (`_extract_user_gid`, `_extract_first_rep`, `_resolve_assignee_gid`), identical in logic, independently maintained. No code-level deprecation notice on `automation/pipeline.py`.

**Impact if realized**: Feature parity divergence, doubled maintenance burden, confusion for new developers about which path to extend.

---

### Risk 3: Circular Dependencies Constrain Future Extraction

**Severity**: Low-Medium | **Likelihood**: Low | **Proximity**: Long-term
**Category**: Structural
**Classification**: Long-term Transformation
**Leverage Score**: 3/10

**Description**: 6 directory-level circular dependencies, all mitigated at runtime via deferred imports, prevent clean extraction of subsystems as independent packages. The ~120 deferred imports accumulate first-call latency costs that are unquantified.

**Evidence**: DEPENDENCY-MAP.md Section 6, Cycles 1-6. All mitigated but all architecturally real.

**Impact if realized**: Lambda cold-start latency degradation, refactoring constraints, increasing deferred-import count as the codebase grows.

---

### Risk 4: Singleton Proliferation Without Registration Pattern

**Severity**: Low-Medium | **Likelihood**: Medium | **Proximity**: Ongoing
**Category**: Structural
**Classification**: Quick Win (high leverage, low effort)
**Leverage Score**: 7/10

**Description**: 8 module-level singletons require coordinated reset for test isolation. Adding a new singleton requires updating `core/system_context.py`. If forgotten, test isolation silently breaks. A registration pattern (singletons register their reset functions) would make this self-maintaining.

**Evidence**: `core/system_context.py` lines 38-86: explicit import and reset of 8 singletons from 5 subsystems.

**Impact if realized**: Flaky tests due to leaked state, developer frustration from debugging test isolation failures.

---

### Risk 5: conversation_audit.py Bootstrap Gap

**Severity**: Medium | **Likelihood**: Low | **Proximity**: Immediate
**Category**: Correctness
**Classification**: Quick Win
**Leverage Score**: 8/10

**Description**: The `conversation_audit.py` Lambda handler uses entity detection at runtime but lacks an explicit bootstrap guard. It relies on the Tier1 defensive guard in `detection/tier1.py` as a safety net.

**Evidence**: Entry-point audit (`/Users/tomtenuta/Code/autom8y-asana/.claude/wip/ENTRY-POINT-AUDIT.md`) classifies this as MEDIUM RISK. Recommendation: add `import autom8_asana.models.business  # noqa: F401` bootstrap guard.

**Impact if realized**: Silent correctness failure if the Tier1 guard is ever modified or the import chain changes.

---

### Risk 6: DataServiceClient Endpoint Scaffolding Duplication

**Severity**: Low | **Likelihood**: Medium | **Proximity**: Next endpoint addition
**Category**: Accidental Complexity
**Classification**: Strategic Investment
**Leverage Score**: 5/10

**Description**: Each new DataServiceClient endpoint requires ~50-80 LOC of structural scaffolding (circuit breaker check, get_client, build callbacks, execute_with_retry, handle error, parse success, record success, emit metrics). The retry callbacks have been extracted but the orchestration flow has not.

**Evidence**: 5 endpoint modules in `clients/data/_endpoints/` each implement the same 8-step orchestration.

**Impact if realized**: Linear cost growth per new endpoint, risk of inconsistency between endpoint implementations.

---

### Risk 7: automation/ Directory Contains 3 Distinct Concerns

**Severity**: Low | **Likelihood**: Low | **Proximity**: Long-term
**Category**: Boundary Misalignment
**Classification**: Long-term Transformation
**Leverage Score**: 3/10

**Description**: The `automation/` directory (34 files, 10,768 LOC) contains: (1) the legacy pipeline conversion rule, (2) the event system (emitter, transport, rules), (3) the workflow implementations (insights export, conversation audit, pipeline transition), and (4) the polling scheduler. These are three distinct domain concerns sharing a directory.

**Evidence**: Topology-inventory Section 5.6: 4 sub-packages (`events/`, `polling/`, `workflows/`, root) plus `pipeline.py`. The `workflows/insights_formatter.py` alone is 1,476 LOC -- an HTML renderer that has no relationship to automation rules.

**Impact if realized**: Developer confusion about where new automation features belong, increasing directory size without clear organization.

---

### Risk 8: Classification Rules Hardcoded in Python

**Severity**: Low | **Likelihood**: Low-Medium | **Proximity**: Unknown (depends on change frequency)
**Category**: Operational Flexibility
**Classification**: Quick Win (if change frequency warrants)
**Leverage Score**: 4/10 (uncertain -- depends on unknown change frequency)

**Description**: 33 Offer sections and 14 Unit sections are hardcoded as Python frozensets. Any classification change requires a code change, PR, CI, and deployment.

**Evidence**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` lines 183-263.

**Impact if realized**: Operational bottleneck if classification rules change frequently. Appropriate if rules are stable.

---

### Risk 9: QueryEngine Direct Dependency on Services Layer

**Severity**: Low | **Likelihood**: Low | **Proximity**: Long-term
**Category**: Layering Violation
**Classification**: Long-term Transformation
**Leverage Score**: 2/10

**Description**: `query/engine.py` directly imports `services.query_service.EntityQueryService` and `services.resolver.to_pascal_case`. This means the query engine (a computational subsystem) depends on the services layer (an orchestration layer), inverting the expected dependency direction.

**Evidence**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py` lines 40-41.

**Impact if realized**: Query engine cannot be tested without the full services layer. Extracting the query subsystem as an independent library would require decoupling.

---

### Risk 10: holder_construction.py Deep Entity Hierarchy Knowledge

**Severity**: Low | **Likelihood**: Medium | **Proximity**: Next entity type addition
**Category**: Fragile Coupling
**Classification**: Strategic Investment
**Leverage Score**: 4/10

**Description**: `persistence/holder_construction.py` imports 6 specific Holder types (ContactHolder, LocationHolder, OfferHolder, ProcessHolder, UnitHolder, Business), creating tight coupling to the entity hierarchy. Adding a new entity type requires updating the persistence layer.

**Evidence**: Dependency-map Section 7.3: "persistence/holder_construction.py imports 6 specific Holder types."

**Impact if realized**: Forgetting to update holder_construction.py when adding a new entity type leads to silent failure in holder auto-creation.

---

## 9. Unknowns

### Unknown: core/system_context.py Design Intent

- **Question**: Was `core/system_context.py` designed as a permanent architectural pattern, or is it a pragmatic test utility that should eventually move to a non-core location?
- **Why it matters**: If permanent, the upward dependencies should be accepted and the layering philosophy adjusted. If pragmatic, it should be refactored to use a registration pattern or moved out of core/.
- **Evidence**: The module's docstring references "QW-5 (ARCH-REVIEW-1 Section 3.1)" as its origin, suggesting it was a quality-improvement initiative response rather than a designed architectural feature.
- **Suggested source**: Original QW-5 decision-maker; the architecture review that spawned it.

### Unknown: Classification Rule Change Frequency

- **Question**: How often do the 33 Offer section names and 14 Unit section names change in practice?
- **Why it matters**: If monthly or more, hardcoded Python is a significant operational bottleneck. If yearly or less, the current design is appropriate and Risk 8 is a non-issue.
- **Evidence**: 33 + 14 = 47 section names in `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py`. No change history visible from code artifacts.
- **Suggested source**: Git blame on the classifier definitions; product team.

### Unknown: conversation_audit.py Bootstrap Guard Status

- **Question**: Was the recommended bootstrap guard added to `conversation_audit.py` after the entry-point audit?
- **Why it matters**: If not added, this remains a MEDIUM RISK entry point relying on a defensive safety net rather than an explicit guard.
- **Evidence**: Entry-point audit recommended the change. MEMORY.md lists "U-005: Entry-point audit, 1 bootstrap guard added (conversation_audit.py)" -- suggesting it WAS added. But the code was not verified in this analysis.
- **Suggested source**: Read `lambda_handlers/conversation_audit.py` to verify.

### Unknown: Deferred Import Latency Impact

- **Question**: What is the cumulative first-call latency cost of ~120 function-body deferred imports on Lambda cold starts?
- **Why it matters**: Each deferred import incurs a one-time import cost on first invocation. In Lambda cold starts, if many deferred imports fire simultaneously, the latency could compound.
- **Evidence**: DEPENDENCY-MAP.md Unknown #3: "approximately 120 function-body deferred imports." Cache warmer Lambda explicitly calls `_ensure_bootstrap()` to front-load some of these.
- **Suggested source**: Lambda cold-start performance profiling (CloudWatch metrics).

### Unknown: Query v1 Consumer Inventory

- **Question**: What callers use the v1 query API, and have they been notified of the 2026-06-01 sunset?
- **Why it matters**: The sunset date is ~3.5 months away. If v1 has active consumers, migration must be planned.
- **Evidence**: v1 deprecated endpoint exists in API layer; sunset date documented; no consumer list found in code artifacts.
- **Suggested source**: API access logs, consumer onboarding documentation.

### Unknown: Whether lifecycle/creation.py Handles All automation/pipeline.py Scenarios

- **Question**: Are there pipeline transition scenarios that only `automation/pipeline.py` handles (e.g., onboarding comment creation, post-transition validation)?
- **Why it matters**: If automation/pipeline.py has unique capabilities, it cannot be deprecated -- the dual-path architecture is permanent.
- **Evidence**: `automation/pipeline.py` includes `_create_onboarding_comment_async()` (FR-COMMENT-001 through FR-COMMENT-005) and post-transition validation (`_validate_post_transition()`) that do not appear in `lifecycle/creation.py`. However, these may be lifecycle-specific features not needed by the lifecycle engine's different workflow.
- **Suggested source**: Feature comparison of the two paths; team knowledge of which pipeline handles which transitions.

---

## Handoff Checklist

- [x] architecture-assessment artifact exists with all required sections (anti-pattern findings, boundary assessments, SPOF register, risk register)
- [x] Each anti-pattern finding includes evidence (file paths, code references) and affected subsystems
- [x] Risk register entries have leverage scores and impact/effort classifications (quick win, strategic investment, long-term transformation)
- [x] Confidence ratings (high/medium/low) assigned to all findings
- [x] False-positive context check performed for all anti-pattern findings
- [x] SPOF register identifies cascade paths
- [x] Boundary assessments reference both topology-inventory service classifications and dependency-map coupling data
- [x] Unknowns section documents structural decisions requiring human context
- [x] (DEEP-DIVE) Architectural philosophy extraction and module-to-domain alignment scoring are complete
- [x] Prior art validation covers all 5 Opportunities, 7 Gaps, and 5 Paradoxes with status and code evidence
