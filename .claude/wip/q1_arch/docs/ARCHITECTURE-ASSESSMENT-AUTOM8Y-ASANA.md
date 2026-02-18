# Architecture Assessment: autom8y-asana

**Date**: 2026-02-18
**Review ID**: ARCH-REVIEW-1 (Phase 3 -- Structure Evaluation)
**Commit**: `be4c23a` (main)
**Scope**: Single-repo assessment -- `autom8y-asana` (~111K LOC, 383 Python files, 27 packages)
**Complexity**: DEEP-DIVE
**Upstream Artifacts**: `TOPOLOGY-AUTOM8Y-ASANA.md`, `DEPENDENCY-MAP-AUTOM8Y-ASANA.md`, `ARCH-REVIEW-1-*` series, `SMELL-REPORT-WS4.md`

---

## Table of Contents

1. [Anti-Pattern Inventory](#1-anti-pattern-inventory)
2. [Boundary Assessment](#2-boundary-assessment)
3. [SPOF Register](#3-spof-register)
4. [Risk Register](#4-risk-register)
5. [Architectural Philosophy Extraction (DEEP-DIVE)](#5-architectural-philosophy-extraction)
6. [Module-to-Domain Alignment Scoring (DEEP-DIVE)](#6-module-to-domain-alignment-scoring)
7. [Unknowns](#7-unknowns)
8. [Provenance](#8-provenance)

---

## 1. Anti-Pattern Inventory

### 1.1 Anti-Pattern Table

Each anti-pattern includes a false-positive context check (intentional trade-off? context-aware coupling? evidence sufficient?).

| ID | Pattern Name | Severity | Affected Packages | Evidence (File Paths) | Confidence | Leverage Score | Context Check |
|----|-------------|----------|-------------------|----------------------|------------|----------------|---------------|
| AP-001 | God Object: DataServiceClient | Critical | `clients` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py` (2,175 lines, 49 methods, 3 C901 violations) | High | 9.0 | Not intentional -- decomposition already started (extracted `_response.py`, `_metrics.py`, `_cache.py`) but class remains monolithic. Mixes HTTP transport, retry, circuit breaker, caching, PII redaction, metrics, response parsing, 5 API endpoints. |
| AP-002 | God Object: SaveSession | Critical | `persistence` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/session.py` (1,853 lines, 58 methods, 6-phase commit) | High | 9.0 | Partially intentional -- UoW pattern legitimately requires orchestration of 8 collaborators across 6 phases over a non-transactional API. However, the class also contains action builder methods (`add_followers`, `add_comment`, `set_parent`, `reorder_subtask`) that could be extracted. Accepted trade-off for orchestration; anti-pattern for action builders. |
| AP-003 | Triple Registry | High | `core`, `services` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/entity_registry.py` (EntityRegistry), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py` (ProjectTypeRegistry + EntityProjectRegistry) | High | 8.0 | Not intentional. Three registries encode overlapping views of "which entity types live in which projects." Populated independently with no cross-registry validation. Silent divergence goes undetected. |
| AP-004 | Parallel Hierarchy: Dual Creation Pipeline | High | `automation`, `lifecycle` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py` (lines 191-497), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/creation.py` (lines 103-493) | High | 13.5 | Partially intentional -- lifecycle engine is the "next-gen" replacement, but both paths remain active simultaneously. Field seeding already diverged (FieldSeeder vs AutoCascadeSeeder). Highest-ROI smell per WS4 report (DRY-001). |
| AP-005 | Import-Time Side Effects | High | `models` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/__init__.py` (line 60-62: `register_all_models()` at import), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/_bootstrap.py` | High | 6.0 | Partially intentional -- registration must occur before any business model is used. However, import-time execution creates fragile import ordering, impacts test isolation, and adds Lambda cold start latency. The idempotency guard in `_bootstrap.py` and the defensive call in `detection/tier1.py:105` confirm this is a known fragility point. |
| AP-006 | Excessive Barrel File | High | `models` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/__init__.py` (239 lines, 87 `__all__` entries, `# ruff: noqa: E402` suppression) | High | 4.5 | Not intentional. 85+ symbols from 8 sub-domains re-exported through a single barrel that triggers registration side effects. Any import of a single entity class forces full registration cascade. |
| AP-007 | Circular Dependencies (6 cycles) | Medium | `services`, `models`, `persistence`, `automation`, `config`, `cache`, `dataframes`, `core` | See cycle table below | High | 4.0 | Partially intentional -- each cycle is individually managed via deferred imports. The aggregate (6 cycles, 10+ deferred import sites) creates a fragile import graph. The `resolver` <-> `universal_strategy` cycle (3 deferred sites) is the most concerning. |
| AP-008 | Caching Concept Overload (31 concepts) | Medium | `cache`, `dataframes` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/` (15,658 LOC, 3 freshness modes, 6 freshness states, 4 tiers, 5 providers, 14 entry types, 4 completeness levels) | High | 5.0 | Partially intentional -- Asana API rate limits (150 req/min) justify sophisticated caching. However, 31 concepts / 111K LOC = 3x typical concept density. Two separate cache systems (entity vs DataFrame) with different mental models amplify cognitive load. The freshness model sophistication is disproportionate to the invalidation model simplicity. |
| AP-009 | Singleton Constellation (6+ uncoordinated) | Medium | `core`, `services`, `dataframes`, `models` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/entity_registry.py` (EntityRegistry._instance), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py` (ProjectTypeRegistry._instance, EntityProjectRegistry._instance), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/models/registry.py` (SchemaRegistry._instance) | High | 3.5 | Partially intentional -- singletons are appropriate for registries. The anti-pattern is the absence of a lifecycle coordinator. No `SystemContext.initialize()` or `SystemContext.reset()` ensures consistent state. Test reset order-sensitivity causes flaky tests. |
| AP-010 | Shotgun Surgery: New Entity Type | Medium | `models`, `core`, `dataframes`, `services` | `detection/types.py` (EntityType enum), `core/entity_registry.py` (EntityDescriptor), `models/business/` (entity class), `_bootstrap.py` (registration), `dataframes/schemas/` (schema), `dataframes/extractors/` (extractor), `activity.py` (section classifier) | Medium | 5.0 | Partially intentional -- the descriptor system and EntityRegistry SSoT reduce the surface. Schema and extractor resolution is descriptor-driven. But new entity types still require 4-7 file changes across 4 packages. |
| AP-011 | Hardcoded Configuration: 47 Section Names | Medium | `models` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` (47 hardcoded string keys in SectionClassifier._mapping) | Medium | 6.0 | Not intentional. Creates a deployment-required code change for any new Asana section. No runtime section discovery. Unknown sections produce `None` that propagates through the system. |
| AP-012 | Frozen Model Escape Hatches | Low | `models` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/descriptors.py` (`object.__setattr__()`), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/hydration.py` (`PrivateAttr` mutation) | Medium | 2.0 | Partially intentional -- Pydantic v2's `frozen=True` constraint requires escape hatches for two-phase initialization. `PrivateAttr` is the documented workaround. The concern is thread safety when cached frozen models have mutable private state. |
| AP-013 | Async/Sync Duality (88 sync bridges) | Low | `clients`, `persistence`, `cache`, `services` | Codebase-wide: 88 `_run_sync()` / `asyncio.run()` / `loop.run_until_complete()` occurrences, 14 `threading.Lock` instances | Medium | 2.0 | Intentional trade-off -- dual sync/async consumers are a genuine requirement. The pattern (async-first with sync wrappers) is the standard approach. However, 88 sync bridge sites and full docstring duplication in `DataServiceClient` represent maintainability cost. Classified as accepted trade-off. |
| AP-014 | Cross-Context Model Leakage: cache -> services | Medium | `cache`, `services` | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/query_service.py:30` (imports FreshnessInfo), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/task_service.py:25` (imports MutationEvent) | High | 4.0 | Unknown intentionality -- cache infrastructure types (`FreshnessInfo`, `MutationEvent`, `EntryType`) leak into the domain services layer. Coupling score 8/10 per dependency-map. See Unknown section for escalation. |

### 1.2 Circular Dependency Detail

| Cycle # | Package A | Package B | Deferred Import Sites | Mechanism | Severity |
|---------|-----------|-----------|----------------------|-----------|----------|
| 1 | `services/resolver` | `services/universal_strategy` | 3 (strategy:156,326; resolver:712) | Function-body deferred imports | High |
| 2 | `models/business/__init__` | `models/business/_bootstrap` | 1 (init triggers bootstrap) | Import-time registration + idempotency guard | Medium |
| 3 | `persistence/session` | `persistence/cascade` | 1 (session:191) | Deferred import within package | Low |
| 4 | `automation/__init__` | `automation/pipeline` | 1 (`__getattr__` lazy import) | Module-level `__getattr__` | Low |
| 5 | `config` | `cache/models` | 5 (config:39,40,490,504,518) | Deferred via TYPE_CHECKING or function body | Medium |
| 6 | `dataframes/models/registry` | `core/entity_registry` | 1 (registry:123) | Deferred import to avoid circular | Low |

### 1.3 Cross-Reference: SMELL-REPORT-WS4 Findings Integration

The 25 findings from SMELL-REPORT-WS4 (3 critical, 9 high, 11 medium, 2 low) map to anti-patterns as follows:

| Smell ID | Category | Anti-Pattern ID | Status |
|----------|----------|-----------------|--------|
| CX-001 (DataServiceClient god object) | CX-GOD | AP-001 | Incorporated |
| CX-002 (SaveSession god object) | CX-GOD | AP-002 | Incorporated |
| CX-003 (_preload complexity 35) | CX-CYCLO | Risk R-010 | Incorporated into risk register |
| CX-004 (_execute_batch_request complexity 29) | CX-CYCLO | Subsumed by AP-001 | Subsumed |
| CX-005 (PipelineConversionRule complexity 20) | CX-CYCLO | Subsumed by AP-004 | Subsumed |
| CX-006 (Multiple C901 violations) | CX-CYCLO | Risk R-010 | Incorporated |
| CX-007 (High parameter counts) | CX-PARAM | Risk R-011 | Incorporated |
| CX-008 (Deep nesting) | CX-NEST | Informational | Low severity, not anti-pattern |
| DRY-001 (Pipeline creation duplication) | DRY-PARA | AP-004 | Incorporated |
| DRY-002 (Retry callback boilerplate) | DRY-COPY | Subsumed by AP-001 | Subsumed |
| DRY-003 (_elapsed_ms duplication) | DRY-COPY | Risk R-012 | Quick win |
| DRY-004 (_ASANA_API_ERRORS duplication) | DRY-CONST | Risk R-012 | Quick win |
| DRY-005 (Sync/async docstring duplication) | DRY-COPY | AP-013 | Incorporated |
| DRY-006 (Client CRUD overloads) | DRY-PARA | Accepted trade-off | Intentional for type safety |
| DRY-007 (Name generation regex) | DRY-COPY | Subsumed by AP-004 | Subsumed |
| AR-001 (Barrel __init__.py logic) | AR-LAYER | AP-005, AP-006 | Incorporated |
| AR-002 (Dual-path automation) | AR-COUPLE | AP-004 | Incorporated |
| AR-003 (AsanaClient cross-module coupling) | AR-COUPLE | Informational | Intentional facade pattern |
| AR-004 (E402 circular avoidance) | AR-CIRC | Subsumed by AP-007 | Subsumed |
| DC-001 (Legacy preload module) | DC-MOD | Risk R-013 | Needs domain review |
| DC-002 (Deprecated ReconciliationsHolder) | DC-BRANCH | Risk R-014 | Low priority |
| IM-001 (models/business barrel) | IM-BARREL | AP-006 | Incorporated |
| IM-002 (Root __init__ dataframes import) | IM-BARREL | Risk R-015 | Partially addressed (lazy loading via RF-010) |
| IM-003 (Inline deferred imports) | IM-CIRC | AP-007 | Incorporated |
| NM-001 (Inconsistent naming) | NM-CONV | Subsumed by AP-004 | Subsumed |

---

## 2. Boundary Assessment

### 2.1 Boundary Alignment Scorecard

Each major package boundary is evaluated against domain alignment using:
- **Topology-inventory** classification (core / domain / infrastructure / integration / API)
- **Dependency-map** coupling scores and fan-in/fan-out data
- **Domain-health** boundary tension analysis

Scoring:
- **Aligned**: Package boundary matches a coherent domain concept. Low incidental coupling. Clean API surface.
- **Partially Aligned**: Package captures a domain concept but leaks abstractions or contains mixed responsibilities.
- **Misaligned**: Package boundary does not match any single domain concept, or coupling patterns indicate the boundary is in the wrong place.

| Package | Classification | Domain Concept | Alignment | Coupling Evidence | Justification |
|---------|---------------|----------------|-----------|-------------------|---------------|
| `core` | core | Shared kernel (entity registry, timing, creation primitives) | **Aligned** | Fan-in: 14 (highest). All incoming. Unidirectional. | High fan-in is expected for a shared kernel. No fan-out to domain packages. `EntityDescriptor` is the correct location for cross-cutting entity metadata. |
| `protocols` | core | Integration contracts (CacheProvider, AuthProvider, LogProvider) | **Aligned** | Fan-in: 7. All TYPE_CHECKING or protocol mediation. | Protocols define boundaries between subsystems. No implementation leakage. Clean DI contracts. |
| `models` | domain | Entity model definitions + detection + hydration + matching | **Partially Aligned** | Fan-in: 10. Fan-out: 3 (lazy). Contains 8 sub-domains in `business/`. | The `models/business/` package conflates 8 sub-domains (entities, holders, detection, descriptors, hydration, section classification, registration, matching). The `detection/` subdirectory is well-bounded internally but trapped inside the over-broad `business/` boundary. Barrel file exports 85+ symbols with import-time side effects. |
| `persistence` | domain | Unit of Work, change tracking, cascade execution | **Aligned** | Fan-in: 5. Fan-out: 6. Bidirectional with `models` (7/10 coupling). | SaveSession legitimately orchestrates entity persistence. The bidirectional coupling with `models` is inherent to the UoW pattern. The 1,853-line god object is a complexity concern (AP-002) but the boundary itself is correct. |
| `cache` | infrastructure | Multi-tier caching (Redis+S3 entity, Memory+S3 DataFrame) | **Partially Aligned** | Fan-in: 9. Fan-out: 4. Cross-context leakage to `services` (8/10 coupling). | Cache models (`FreshnessInfo`, `MutationEvent`, `EntryType`) leak into domain `services` layer (AP-014). Two separate cache systems (entity and DataFrame) under one package boundary but with different mental models. The boundary would be better if cache *models* consumed by services were promoted to a shared contract. |
| `services` | domain | Query orchestration, entity resolution, field writes | **Partially Aligned** | Fan-in: 6. Fan-out: 9 (highest). Circular with self (resolver <-> universal_strategy). | Services is a composition layer that bridges many packages. Fan-out of 9 is the highest in the codebase. Contains the `resolver` <-> `universal_strategy` circular dependency (AP-007 Cycle 1). The 12 deferred import sites from `dataframes` (coupling score 8/10) indicate deep coupling to DataFrame internals. |
| `dataframes` | domain | Polars DataFrame analytics (builders, extractors, schemas, storage) | **Aligned** | Fan-in: 5. Fan-out: 5. | Clean domain boundary for analytical data transformation. Schema-driven via EntityDescriptor. Internal decomposition (builders, extractors, schemas, storage, cache) is well-organized. The 12 deferred imports from `services` are all inbound (services depends on dataframes), not outbound leakage. |
| `query` | domain | Algebraic query engine (AST, compiler, guards, joins) | **Aligned** | Fan-in: implicit (via `services`). Fan-out: 3. | Clean decomposition: 8 files, each < 300 lines. Stateless compiler. Explicit operator/dtype matrix. Single responsibility: translate predicate AST to Polars expressions. |
| `automation` | domain | Pipeline rules, seeding, events, polling, workflows | **Partially Aligned** | Fan-in: implicit. Fan-out: 5. Parallel with `lifecycle`. | Contains the legacy pipeline conversion path (AP-004). Overlaps with `lifecycle` for entity creation. Internal structure is complex (events/, polling/, workflows/ subdirectories) but each serves a distinct automation concern. The boundary issue is not internal -- it is the existence of a parallel `lifecycle` package that does overlapping work. |
| `lifecycle` | domain | Lifecycle engine, creation, seeding, webhook handler | **Partially Aligned** | Fan-out: 5. Imports from `automation/seeding.py` (private functions). | Intended as the "next-gen" replacement for automation pipeline creation. However, the boundary leaks: `lifecycle/seeding.py` imports private functions from `automation/seeding.py` (BOUNDARY-001 in smell report). The package is not yet self-sufficient. |
| `clients` | integration | Asana API clients (tasks, tags, sections, projects, etc.) | **Aligned** | Fan-in: 5. Fan-out: 5 (to core, protocols, cache, config, transport). | Each client file (`tasks.py`, `sections.py`, etc.) maps to an Asana API resource. Clean internal structure. The fan-out to `cache` (EntryType leakage) is the only concern, and it is mediated via deferred imports. |
| `transport` | integration | HTTP transport, instrumented Asana client | **Aligned** | Fan-in: 3. Fan-out: 2 (config, protocols via TYPE_CHECKING). | Thin layer between `clients` and Asana API. Clean boundary. |
| `api` | API | FastAPI routes, middleware, lifespan, preload | **Aligned** | Fan-in: 0 (entry point). Fan-out: 6. | Entry point package. Routes are organized by resource. The preload subsystem (`progressive.py` complexity 35) is a concern but contained within the `api/preload/` subdirectory. |
| `auth` | infrastructure | Authentication providers (PAT, JWT/S2S) | **Aligned** | Fan-in: implicit. Fan-out: 1 (autom8y-auth). | Small, focused package. Clean boundary. |
| `lambda_handlers` | infrastructure | Cache warmer, invalidate, insights export, conversation audit | **Aligned** | Fan-in: 0 (entry points). Fan-out: 3 (services, clients via deferred). | Each handler is a self-contained Lambda entry point. Temporal coupling to cold-start bootstrap is inherent. |
| `resolution` | domain | Entity resolution (GID lookup, hierarchy-aware) | **Aligned** | Fan-in: 3. Fan-out: 2 (models, core). | Clean domain concept. 7 files with clear decomposition (context, strategies, field resolver, selection, budget, write registry, result). |
| `config` | core | Configuration loading (env vars, settings) | **Partially Aligned** | Fan-in: 10. Bidirectional with `cache/models` (5 deferred sites). | Config has high fan-in (expected) but also imports from `cache/models` for TTL defaults and freshness enums. This bidirectional relationship (AP-007 Cycle 5) blurs the boundary between configuration and cache implementation. |
| `search` | domain | Search functionality | **Aligned** | Fan-in: 0. Fan-out: 1 (dataframes). | Small, focused. Clean boundary. |
| `batch` | domain | Batch operations against Asana API | **Aligned** | Fan-in: 1. Fan-out: 2 (clients, transport). | Small, focused. Clean boundary. |
| `metrics` | infrastructure | Prometheus metrics collection | **Aligned** | Fan-in: implicit. Fan-out: 0. | Small, focused. Clean boundary. |
| `observability` | infrastructure | W3C trace propagation, log-trace correlation | **Aligned** | Fan-in: implicit. Fan-out: 0. | Small, focused. Clean boundary. |
| `entrypoint` | infrastructure | Dual-mode dispatcher (ECS/Lambda) | **Aligned** | Fan-in: 0 (system entry). Fan-out: 1 (api). | 97 lines. Minimal. Clean boundary. |
| `patterns` | core | Reusable patterns (shared base classes) | **Aligned** | Fan-in: implicit. Fan-out: 0. | Small, utility package. Clean boundary. |
| `settings` | core | Pydantic Settings model | **Aligned** | Fan-in: 7. Fan-out: 0. | Pure data model. No behavioral coupling. |
| `exceptions` | core | SDK exception hierarchy | **Aligned** | Fan-in: implicit. Fan-out: 0. | Pure definitions. No coupling concerns. |
| `_defaults` | core | Default implementations (auth, cache, log, observability) | **Aligned** | Fan-in: 1 (client.py). Fan-out: 3 (protocols, cache, auth). | Provides sensible defaults for protocol implementations. Clean pattern. |

### 2.2 Boundary Alignment Summary

| Rating | Count | Packages |
|--------|-------|----------|
| **Aligned** | 20 | `core`, `protocols`, `persistence`, `dataframes`, `query`, `clients`, `transport`, `api`, `auth`, `lambda_handlers`, `resolution`, `search`, `batch`, `metrics`, `observability`, `entrypoint`, `patterns`, `settings`, `exceptions`, `_defaults` |
| **Partially Aligned** | 7 | `models`, `cache`, `services`, `automation`, `lifecycle`, `config` |
| **Misaligned** | 0 | (none) |

**Assessment**: No package boundaries are fundamentally misaligned. The 7 partially-aligned packages share a common theme: they are the largest and most complex packages in the codebase, where organic growth has introduced mixed responsibilities or cross-context coupling. The `models/business/` package (8 sub-domains in one boundary) and the `automation`/`lifecycle` parallel hierarchy are the most significant boundary concerns.

---

## 3. SPOF Register

Single Points of Failure -- components whose failure cascades to multiple subsystems.

### 3.1 SPOF Table

| ID | SPOF Component | Criticality | Dependents | Failure Mode | Cascade Path | Mitigation Exists? | Cascade Severity |
|----|---------------|-------------|------------|-------------|--------------|---------------------|------------------|
| SPOF-001 | `register_all_models()` | **Critical** | All entity class instantiation, detection, schema resolution, DataFrame extraction | If not called: entity classes lack registered metadata; detection returns Unknown for all entities; schema registry cannot initialize | `models/business/__init__.py` import -> `_bootstrap.py` -> all entity classes -> all detection tiers -> all DataFrames -> all query results | Yes: idempotency guard + defensive call in `tier1.py:105`. But no explicit health check validates completion. | **Critical** -- app is non-functional |
| SPOF-002 | `EntityRegistry` validation | **Critical** | Detection, schema resolution, caching keys, DataFrame extraction, query joins | If validation fails: import-time error, app does not start | Import-time error in `core/entity_registry.py` -> `_validate_registry_integrity()` -> all packages importing core -> app crash | Yes: fail-fast at import; integrity tests (checks 6a-6f). But validation does not check cross-registry consistency with ProjectTypeRegistry. | **Critical** -- app does not start |
| SPOF-003 | `DataServiceClient` | **High** | All external data API calls (insights, batch, CSV export, appointments, leads) | God object: failure in shared state (circuit breaker, HTTP session) could affect all 5 endpoint methods | Any endpoint method failure -> shared circuit breaker state -> potential false-positive circuit open for other endpoints | Partial: per-endpoint error handling. But shared class state (HTTP client, PII redactor, metrics) creates coupling. | **High** -- all external data API unavailable |
| SPOF-004 | `SaveSession` | **High** | All entity mutations (create, update, delete, cascade, heal, automate) | Orchestrator failure: bug in phase ordering or action execution corrupts data or leaves partial state | Phase 1 (ensure_holders) failure -> children cannot be created. Phase 3 (CRUD) partial failure -> inconsistent entity state. Phase 5 (automation) failure -> downstream automations do not fire. | Partial: phase isolation means later phase failure does not roll back earlier phases. But no compensating transaction for partial CRUD. | **High** -- entity mutations fail or corrupt |
| SPOF-005 | `SchemaRegistry` lazy init | **High** | All DataFrame operations (builders, extractors, queries, resolution) | If init fails: DataFrame queries return errors; resolution returns empty results | First access -> `_ensure_initialized()` -> iterates EntityDescriptors -> resolves schema modules. Failure at any descriptor -> entire registry init fails. | Partial: lazy init with retry on next access. But first-failure is visible to the user. | **High** -- all analytical queries fail |
| SPOF-006 | `ProjectTypeRegistry` population | **High** | All entity resolution via `services/resolver.py`, Tier 1 detection | If not populated: all entity queries return Unknown; Tier 1 detection produces 0 results | Config-driven population at startup -> `_discover_entity_projects()` in `api/lifespan.py` -> fail-fast if config missing. | Yes: fail-fast at startup. But if runtime config changes (Asana project GID rotation), registry serves stale mappings until restart. | **High** -- entity resolution broken |
| SPOF-007 | Redis connection | **Medium** | All hot-tier cache reads for entity data | If down: fall back to S3 cold tier or direct API | Redis unavailable -> `TieredCacheProvider` skips hot tier -> S3 read (higher latency) -> if S3 also down -> direct API (rate limit risk) | Yes: graceful degradation via `TieredCacheProvider`. Circuit breaker prevents connection storm. | **Medium** -- degraded performance, not outage |
| SPOF-008 | S3 access | **Medium** | Cold tier cache, DataFrame persistence, watermarks, Lambda warmer checkpoints | If down: hot tier only, no cold-start resilience, DataFrame builds cannot persist | S3 unavailable -> circuit breaker opens -> Redis-only operation (no cold-tier durability) -> Lambda warmers cannot checkpoint -> next cold start requires full API refresh. | Yes: circuit breaker + graceful degradation. But prolonged S3 outage degrades cache warming and cold-start resilience. | **Medium** -- degraded resilience |
| SPOF-009 | Asana API | **Medium** | All data fetching (entities, tasks, projects, sections) | If rate-limited or down: stale cache data served | API rate-limited -> cache serves stale (4:2 servable ratio) -> extended outage -> cache TTLs expire -> EXPIRED state -> errors. | Yes: 4:2 servable-to-reject ratio ensures data availability from cache. Cache warming pre-populates. But extended outage (> max TTL) causes data loss. | **Medium** -- degraded freshness, eventual failure |
| SPOF-010 | `resolver` <-> `universal_strategy` cycle | **Low** | Entity resolution API endpoints (`POST /v1/resolve/{entity_type}`) | Import-time failure if circular dependency breaks | Deferred imports at 3 sites. If any import path changes, resolution endpoint fails with `ImportError` or `AttributeError`. | Partial: deferred imports work today. But adding new imports between these two modules risks breaking the cycle management. | **Low** -- resolution endpoint fails |

### 3.2 Cascade Severity Summary

| Severity | Count | SPOF IDs |
|----------|-------|----------|
| **Critical** (app non-functional) | 2 | SPOF-001, SPOF-002 |
| **High** (major feature broken) | 4 | SPOF-003, SPOF-004, SPOF-005, SPOF-006 |
| **Medium** (degraded operation) | 3 | SPOF-007, SPOF-008, SPOF-009 |
| **Low** (single endpoint affected) | 1 | SPOF-010 |

---

## 4. Risk Register

### 4.1 Consolidated Risk Table

Severity, Likelihood, Impact rated: Critical / High / Medium / Low.
Leverage = Impact-to-Effort ratio (1.0-10.0 scale, higher = more improvement per unit effort).
Classification: QW = Quick Win, SI = Strategic Investment, LT = Long-Term Transformation.

| ID | Risk | Severity | Likelihood | Impact | Leverage | Classification | Source Anti-Pattern / SPOF | Evidence |
|----|------|----------|-----------|--------|----------|----------------|---------------------------|----------|
| R-001 | **Triple registry divergence**: New entity type added to one registry but not others; silent misclassification | High | Medium | High | 8.0 | **SI** | AP-003 | Three registries populated independently with no cross-validation. `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/entity_registry.py`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py` |
| R-002 | **Cache invalidation gap**: External Asana mutations invisible; stale data served for up to TTL window | High | High | High | 5.0 | **SI** | AP-008 | No webhook integration. TTL-only invalidation for external mutations. Business entity staleness up to 60 minutes. |
| R-003 | **Dual creation pipeline divergence**: Behavior diverges as one path is updated without the other | High | High | High | 13.5 | **SI** | AP-004 | Field seeding already diverged (FieldSeeder vs AutoCascadeSeeder). `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/creation.py` |
| R-004 | **DataServiceClient single-class failure**: Bug or resource leak in shared state affects all 5 API endpoints | High | Low | High | 9.0 | **SI** | AP-001, SPOF-003 | 2,175-line monolith with shared HTTP client, circuit breaker, PII redactor. `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py` |
| R-005 | **SaveSession phase ordering bug**: Data inconsistency from incorrect phase execution order | High | Low | Critical | 9.0 | **LT** | AP-002, SPOF-004 | 6-phase UoW with no compensating transactions. Phase 3 partial failure leaves inconsistent state. `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/session.py` |
| R-006 | **Import-time failure cascade**: Circular import or registration failure prevents app startup | High | Low | Critical | 6.0 | **SI** | AP-005, SPOF-001 | `register_all_models()` at import time. 6 circular dependency cycles. 10+ deferred import sites. `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/__init__.py:60-62` |
| R-007 | **Section name drift**: New Asana section not in hardcoded classifier; entities unclassified | Medium | Medium | Medium | 6.0 | **QW** | AP-011 | 47 hardcoded section name strings. No runtime section discovery. `None` propagation on unknown sections. `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` |
| R-008 | **Schema/extractor drift**: Manual schema/extractor definitions diverge from descriptor declarations | Medium | Low | Medium | 5.0 | **QW** | AP-010 | Column names use `cf__` prefix convention but defined manually. Extractor uses string field name matching. Rename requires multi-file update. |
| R-009 | **Caching cognitive overload**: New developer productivity impacted by 31 caching concepts | Medium | High | Medium | 3.0 | **LT** | AP-008 | 31 concepts / 111K LOC = 3x typical density. Two separate cache systems with different mental models. Estimated 2-3 day onboarding impact. |
| R-010 | **Extreme cyclomatic complexity**: Functions with complexity 20-35 are high-risk for bugs | Medium | Medium | Medium | 4.0 | **SI** | CX-003, CX-005, CX-006 | `_preload_dataframe_cache_progressive` (35), `_execute_batch_request` (29), `_validate_registry_integrity` (25), `_warm_cache_async` (24), `_preload_dataframe_cache` (23), `PipelineConversionRule.execute_async` (20) |
| R-011 | **High parameter count methods**: Methods with 12-16 parameters indicate missing abstractions | Low | Medium | Low | 6.0 | **QW** | CX-007 | `handle_error_response` (16), `get_insights_async` (13), `get_section_dataframe` (12). `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_response.py:59`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py:732` |
| R-012 | **Utility function duplication**: Small utility functions duplicated across modules | Low | Low | Low | 8.0 | **QW** | DRY-003, DRY-004 | `_elapsed_ms()` in 3 files, `_ASANA_API_ERRORS` tuple in 2 files. Quick consolidation into `core/`. |
| R-013 | **Dead code: legacy preload module**: `api/preload/legacy.py` (613 lines, complexity 23) may be superseded | Low | Medium | Low | 4.0 | **QW** | DC-001 | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/legacy.py`. Needs domain review to confirm if `progressive.py` fully replaces it. |
| R-014 | **Deprecated alias still exported**: `ReconciliationsHolder` alias with deprecation warning | Low | Low | Low | 8.0 | **QW** | DC-002 | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/business.py:81-95`. Removal is a trivial change once usage is confirmed zero. |
| R-015 | **Root __init__ eager DataFrame loading**: `import autom8_asana` loads entire DataFrame subsystem | Low | Low | Low | 2.0 | **QW** | IM-002 | Partially addressed by RF-010 (lazy loading via `__getattr__`). Verify completion. `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/__init__.py` |
| R-016 | **CircuitBreaker thread safety**: Per-project circuit breakers may race under concurrent sync bridge access | Medium | Low | Medium | 3.0 | **SI** | Philosophy contradiction | `threading.Lock` may contend when sync bridges create threads. State machine transition (CLOSED -> OPEN -> HALF_OPEN) is not atomic. Two concurrent requests in HALF_OPEN could both attempt probe. |
| R-017 | **Singleton reset order sensitivity**: Test fixtures must reset 6+ singletons in specific order | Low | Medium | Low | 3.5 | **QW** | AP-009 | No lifecycle coordinator. Reset order changes cause flaky tests. Could be addressed with a `SystemContext.reset_all()` utility. |
| R-018 | **Cross-context model leakage**: Cache infrastructure types in domain services | Medium | Medium | Medium | 4.0 | **SI** | AP-014 | `FreshnessInfo`, `MutationEvent`, `EntryType` imported from `cache/` into `services/`. Coupling score 8/10. |

### 4.2 Risk Classification Summary

| Classification | Count | Risk IDs | Description |
|----------------|-------|----------|-------------|
| **Quick Win** (QW) | 7 | R-007, R-008, R-011, R-012, R-013, R-014, R-015, R-017 | High leverage, low effort. Can be addressed in 1-2 day increments. |
| **Strategic Investment** (SI) | 8 | R-001, R-002, R-003, R-004, R-006, R-010, R-016, R-018 | High impact, moderate effort. Multi-day workstreams. |
| **Long-Term Transformation** (LT) | 2 | R-005, R-009 | High impact, high effort. Requires architectural evolution across multiple workstreams. |

### 4.3 Risk Heat Map

```
             Low Likelihood    Medium Likelihood    High Likelihood
            +------------------+--------------------+------------------+
Critical    |  R-005, R-006    |                    |                  |
Impact      |                  |                    |                  |
            +------------------+--------------------+------------------+
High        |  R-004           |  R-001             |  R-002, R-003    |
Impact      |                  |                    |                  |
            +------------------+--------------------+------------------+
Medium      |  R-016           |  R-007, R-008,     |  R-009           |
Impact      |                  |  R-010, R-018      |                  |
            +------------------+--------------------+------------------+
Low         |  R-012, R-014,   |  R-011, R-013,     |                  |
Impact      |  R-015           |  R-017             |                  |
            +------------------+--------------------+------------------+
```

---

## 5. Architectural Philosophy Extraction (DEEP-DIVE)

### 5.1 Primary Values

The codebase's architectural decisions consistently optimize for two primary values, in this priority order:

| Rank | Value | Evidence Count | Description |
|------|-------|---------------|-------------|
| 1 | **Operational Resilience** | 7 architectural decisions | The system is designed to degrade gracefully rather than fail catastrophically. Every major infrastructure decision (tiered cache, circuit breakers, SWR, checkpoint-resume, degraded mode mixins, defensive imports) prioritizes continued operation under adverse conditions. |
| 2 | **API Call Minimization** | 6 mechanisms | Asana API rate limits (150 req/min per PAT) are treated as the binding external constraint. The architecture treats API calls as a scarce resource: entity cache, DataFrame cache, LIS-optimized reordering, watermark incremental sync, cache warming, batch API support. |

**Supporting values** (consistent but secondary):
- **Type safety**: Pydantic v2 frozen models, algebraic predicate AST, `@overload` patterns, explicit operator/dtype matrix
- **Backward compatibility**: Deprecated aliases with warnings, backward-compatible facades, `extra="ignore"`, defensive imports with fallback
- **Defense-in-depth**: Multiple overlapping protection mechanisms (7 protection layers documented in philosophy analysis)

### 5.2 Consistent Trade-Offs

The codebase repeatedly makes the same trade-off choices:

| Trade-Off | Chosen Side | Sacrificed Side | Example |
|-----------|-------------|-----------------|---------|
| Complexity vs. Simplicity | Complexity | Simplicity | 5-tier detection, 6 freshness states, 6-phase UoW, descriptor system |
| Availability vs. Consistency | Availability (AP) | Consistency | 4:2 servable-to-reject ratio, stale-while-revalidate, graceful degradation |
| Correctness guarantees vs. Runtime flexibility | Correctness | Flexibility | Frozen models, phase-ordered commits, typed query predicates |
| Abstraction investment vs. Direct implementation | Abstraction | Directness | Descriptor system (400 lines infrastructure -> 800 lines eliminated), HolderFactory (14x reduction), protocol-based DI |

### 5.3 Dominant Metaphor: The Defensive Onion

The caching architecture operates as concentric rings of defense, each absorbing a class of failure:

```
Ring 5 (outermost): Asana API
    |-- Absorbs: Nothing (source of truth)
    v
Ring 4: Circuit Breaker + Retry + Rate Limit
    |-- Absorbs: API outages and rate limits
    v
Ring 3: S3 Cold Tier
    |-- Absorbs: Redis failures and cold starts
    v
Ring 2: Redis Hot Tier
    |-- Absorbs: API latency
    v
Ring 1: Memory Cache (DataFrame)
    |-- Absorbs: Redis latency for analytical queries
    v
Ring 0 (core): Application Logic
    -- Always receives data, possibly stale
```

The system degrades by losing outer rings while inner rings continue operating. This is a consistent architectural metaphor applied throughout the caching subsystem.

### 5.4 Philosophy Contradictions

Three philosophical contradictions were identified where practice diverges from the dominant philosophy:

| # | Contradiction | Aspiration | Reality | Diagnosis |
|---|--------------|------------|---------|-----------|
| 1 | **Freshness as First-Class vs. Invalidation as Best-Effort** | 3 freshness modes, 6 freshness states, SWR semantics -- freshness is a first-class concern | External mutations rely solely on TTL expiration. No webhooks, no polling, no event-driven invalidation. | The freshness model describes *observable states* but does not improve *transition rates*. The sophistication of tracking is disproportionate to the simplicity of invalidation. For an AP system that accepts eventual consistency, the 6-state model may be over-engineered. |
| 2 | **Unified Aspiration vs. Bifurcated Reality** | A unified caching layer handling all data types consistently | Two separate cache systems with different freshness models (3-mode vs 6-state), storage formats (JSON vs Parquet), eviction policies (TTL vs LRU), invalidation strategies (mutation-driven vs SWR) | The `CacheProvider` protocol provides a unified interface for entity cache only. DataFrame cache does not use it. No unified protocol spans both systems. A developer working on "caching" must learn two mental models. |
| 3 | **Immutability Aspiration vs. Mutable Singletons** | Entity models are `frozen=True`. Immutability is a stated principle. | 6+ mutable singletons hold global state. `PrivateAttr` mutation and `object.__setattr__()` bypass frozen checks. | Immutability stops at the model boundary. The *models* are frozen, but the *registries that manage them* are mutable singletons accessible from any code path. |

### 5.5 Complexity Budget Analysis

| Component | LOC | % of Codebase (111K) | Assessment |
|-----------|-----|----------------------|------------|
| `cache/` (direct) | 15,658 | 14.1% | Justified at the edge. 5 distinct strategies + invalidation + warming + completeness + metrics. |
| `cache/` + DataFrame cache integration + Lambda warmers | ~19,835 | ~17.9% | High for any single concern. Rate limit constraint justifies significant investment. |
| Caching concepts | 31 | 1 per ~3,600 LOC | 3x typical density (typical: 1 per ~10,000 LOC). Significant cognitive load. |
| Two cache systems | 2 | -- | Each requires a separate mental model. |

**Verdict**: The 14.1% direct cache allocation is proportionate to the Asana API rate limit constraint (150 req/min). However, the *conceptual density* (31 concepts) is over-budget. The complexity is in the number of abstractions, not the amount of code. Reducing concept count by unifying the two cache systems' terminology and consolidating overlapping abstractions would reduce cognitive load without reducing resilience.

### 5.6 Cognitive Load Assessment

| Developer Task | Concepts Required | Estimated Learning Curve | Benchmark |
|---------------|-------------------|-------------------------|-----------|
| Modify entity cache behavior | 10 (Tier 1: must-know) | 1 day | Typical: 0.5 day |
| Modify DataFrame cache behavior | 12 (Tier 2: should-know) | 1.5 days | Typical: 0.5 day |
| Understand full caching subsystem | 31 (all tiers) | 2-3 days | Typical: 0.5-1 day |
| Add new entity type | 4-7 file changes across 4 packages | 0.5 day | Typical: 1-2 files |
| Understand pipeline creation flow | 2 parallel implementations + 2 seeding strategies | 1 day | Typical: 1 implementation |
| Debug import-time failure | 6 circular cycles, 10+ deferred sites, import-time side effects | 0.5-1 day per incident | Typical: minutes |

### 5.7 Architectural Classification

**Primary classification**: Modular Monolith

The codebase is a single deployable unit (Docker image) with internal package boundaries that map to domain concepts. It is not a microservices architecture (single repo, single deployment) nor a traditional monolith (clear internal boundaries, protocol-based DI, clean fan-in/fan-out patterns).

**Where practice diverges from classification**:
- The dual ECS/Lambda deployment model introduces some distributed system concerns (cache consistency, cold starts) that are atypical for a monolith
- The 6+ uncoordinated singletons and import-time side effects are monolith-style patterns that would not exist in a properly bounded microservices architecture
- The cache subsystem's sophistication (tiered, per-project circuit breakers, SWR) is more typical of a distributed system than a monolith

---

## 6. Module-to-Domain Alignment Scoring (DEEP-DIVE)

Each of the 27 packages is scored on how well its boundary aligns with a coherent domain concept.

**Scoring rubric**:
- **5**: Package boundary perfectly matches a single, coherent domain concept. Clean API surface. Minimal incidental coupling.
- **4**: Package boundary matches a domain concept with minor leakage or mixed responsibilities.
- **3**: Package boundary captures related concerns but contains 2-3 distinct sub-domains or has significant coupling issues.
- **2**: Package boundary is poorly defined, containing unrelated concerns or exhibiting high incidental coupling.
- **1**: Package boundary actively works against domain understanding.

| # | Package | Domain Concept | Score | Justification |
|---|---------|---------------|-------|---------------|
| 1 | `__init__` | SDK public API surface | 3 | Re-exports from 8 subpackages (187 non-import lines). Lazy DataFrame loading is good (RF-010), but root barrel still exposes too much surface. |
| 2 | `client` | SDK facade (primary entry point) | 4 | Correct facade pattern. Minor concern: contains business logic (cache warming, workspace auto-detection) that could be delegated. |
| 3 | `config` | Configuration management | 3 | Bidirectional coupling with `cache/models` (5 deferred sites). Config should depend on nothing; instead it imports cache types for TTL defaults. |
| 4 | `settings` | Pydantic Settings model | 5 | Pure data model. No behavioral coupling. Perfect alignment. |
| 5 | `exceptions` | SDK exception hierarchy | 5 | Pure definitions. No coupling concerns. Perfect alignment. |
| 6 | `entrypoint` | Dual-mode dispatcher | 5 | 97 lines. Single responsibility. Clean. |
| 7 | `api` | HTTP API layer (routes, middleware, lifespan) | 4 | Well-organized routes by resource. Preload subsystem (complexity 35) is a minor concern but contained in subdirectory. |
| 8 | `auth` | Authentication providers | 5 | Small, focused. Two clean strategies (PAT, JWT/S2S). Clean boundary. |
| 9 | `automation` | Pipeline rules, seeding, events, workflows | 3 | Complex internal structure (events/, polling/, workflows/). Overlaps with `lifecycle` for entity creation (AP-004). Contains legacy creation path. |
| 10 | `batch` | Batch Asana API operations | 5 | Small (687 LOC), focused, clean boundary. Single domain concept. |
| 11 | `cache` | Multi-tier caching subsystem | 3 | Well-organized internally (backends/, dataframe/, integration/, models/, policies/, providers/). But two separate cache systems (entity vs DataFrame) with different mental models under one roof. Model types leak to `services`. |
| 12 | `clients` | Asana API clients | 4 | Each client maps to an Asana API resource. The `data/client.py` god object (AP-001) is a quality issue, not a boundary issue. Minor `EntryType` leakage from cache. |
| 13 | `core` | Shared kernel | 4 | Entity registry + timing + creation primitives. High fan-in (14) is expected. Minor concern: `creation.py` contains domain logic (template discovery, duplication) that might belong in `lifecycle`. |
| 14 | `dataframes` | Polars DataFrame analytics | 4 | Clean decomposition (builders, extractors, schemas, storage). Internal cohesion is high. Minor concern: DataFrame cache lives here AND in `cache/dataframe/`. |
| 15 | `lambda_handlers` | Lambda entry points | 4 | Each handler is self-contained. Temporal coupling to bootstrap is inherent, not avoidable. |
| 16 | `lifecycle` | Lifecycle engine + creation | 3 | Intended as next-gen replacement for `automation` pipeline creation. Not yet self-sufficient (imports private functions from `automation/seeding.py`). Boundary leak. |
| 17 | `metrics` | Prometheus metrics | 5 | Small (616 LOC), focused. Single concern. |
| 18 | `models` | Entity model definitions | 2 | The `models/business/` sub-package conflates 8 distinct sub-domains (entities, holders, detection, descriptors, hydration, section classification, registration, matching). 85+ symbol barrel with import-time side effects. This is the most significant boundary problem in the codebase. |
| 19 | `observability` | Trace propagation + log correlation | 5 | Small (343 LOC), focused. Clean boundary. |
| 20 | `patterns` | Reusable base classes | 4 | Small (444 LOC). Clean utility package. Minor: the name "patterns" is generic. |
| 21 | `persistence` | Unit of Work + change tracking | 4 | Correct domain boundary for entity persistence. SaveSession god object is a quality issue (AP-002), not a boundary issue. |
| 22 | `protocols` | Integration contracts | 5 | Pure protocol definitions. Clean DI boundaries. |
| 23 | `query` | Algebraic query engine | 5 | Excellent decomposition: 8 files, each < 300 lines. AST, compiler, guards, joins, aggregation. Clean domain concept. |
| 24 | `resolution` | Entity resolution | 5 | Clean domain concept. 7 files with clear decomposition (context, strategies, field resolver, selection, budget, write registry, result). |
| 25 | `search` | Search functionality | 4 | Small (925 LOC). Clean boundary. Minor: only depends on `dataframes`, suggesting it might be a thin wrapper. |
| 26 | `services` | Query orchestration + resolution + field writes | 3 | Composition layer with fan-out of 9 (highest). Internal circular dependency (resolver <-> universal_strategy). 12 deferred imports from `dataframes`. Contains mixed responsibilities: resolution strategy, query service, field writes, discovery, GID lookup. |
| 27 | `transport` | HTTP transport layer | 5 | Thin, focused. Clean boundary between `clients` and Asana API. |

### 6.1 Alignment Score Distribution

| Score | Count | Packages |
|-------|-------|----------|
| **5** (perfect) | 11 | `settings`, `exceptions`, `entrypoint`, `auth`, `batch`, `metrics`, `observability`, `protocols`, `query`, `resolution`, `transport` |
| **4** (good) | 9 | `client`, `api`, `clients`, `core`, `dataframes`, `lambda_handlers`, `patterns`, `persistence`, `search` |
| **3** (mixed) | 6 | `__init__`, `config`, `automation`, `cache`, `lifecycle`, `services` |
| **2** (poor) | 1 | `models` |
| **1** (harmful) | 0 | (none) |

### 6.2 Alignment Statistics

- **Mean score**: 4.0 / 5.0
- **Median score**: 4.0 / 5.0
- **Packages scoring 4+**: 20 / 27 (74%)
- **Packages scoring 3 or below**: 7 / 27 (26%)

**Assessment**: The majority of packages (74%) have good-to-perfect domain alignment. The 7 packages scoring 3 or below are concentrated in the largest, most complex areas of the codebase: `models` (the worst at 2/5), `services`, `automation`, `lifecycle`, `cache`, `config`, and `__init__`. These are the areas where organic growth has outpaced boundary maintenance.

---

## 7. Unknowns

### Unknown: Cache model leakage intentionality

- **Question**: Is the coupling between `services/*` and `cache/models/*` (FreshnessInfo, MutationEvent, EntryType) an intentional API design or an incidental leakage of implementation details?
- **Why it matters**: Determines whether AP-014 (coupling score 8/10) is a bounded-context violation or an accepted contract. If intentional, these types should be promoted to a shared protocol package. If incidental, the services layer should not depend on cache internals.
- **Evidence**: `FreshnessInfo` is a dataclass from `cache/integration/dataframe_cache.py` (an integration module, not a models module), imported by `services/query_service.py:30` and `services/universal_strategy.py:20`. `MutationEvent` from `cache/models/mutation_event.py` imported by 3 service modules.
- **Suggested source**: Original designer of the cache integration layer

### Unknown: Lifecycle as automation replacement timeline

- **Question**: Is `lifecycle/` intended to fully replace `automation/pipeline.py`, or do both paths serve distinct use cases long-term?
- **Why it matters**: Determines whether AP-004 (dual creation pipeline) should be resolved by deprecating `automation/pipeline.py` or by establishing clear boundaries between the two systems. This is the highest-leverage risk (R-003, leverage 13.5).
- **Evidence**: `lifecycle/creation.py` reimplements the same 7-step creation pipeline as `automation/pipeline.py`. `lifecycle/seeding.py` imports private functions from `automation/seeding.py`. The lifecycle engine supports multi-stage transitions and YAML-driven config, while automation supports only single sales-to-onboarding conversion.
- **Suggested source**: Product roadmap or original author of lifecycle engine

### Unknown: Legacy preload module status

- **Question**: Is `api/preload/legacy.py` (613 lines, complexity 23) still active, or has it been fully superseded by `api/preload/progressive.py` (508 lines, complexity 35)?
- **Why it matters**: If superseded, `legacy.py` is 613 lines of dead code contributing to maintenance burden and complexity metrics.
- **Evidence**: Both implementations exist side-by-side. The naming convention ("legacy" vs "progressive") suggests succession, but the `legacy.py` module still has a fallback reference annotated per RF-012 (`refactor(preload,business): annotate legacy fallback and import-time registration`).
- **Suggested source**: Commit history for `api/preload/` or deployment configuration

### ~~Unknown: Query v1 vs v2 route collision~~ — RESOLVED (commit f6e08e5)

- **Resolution**: The hygiene sprint (commit f6e08e5) merged `query_v2.py` into `query.py`. A single unified router now handles all query endpoints. The duplicate `POST /{entity_type}/rows` registration no longer exists; no routing ambiguity remains. The deprecated `POST /{entity_type}` endpoint is retained in the unified router with its 2026-06-01 sunset headers intact.

---

## 8. Provenance

### Source Artifacts

| Source Artifact | Contribution to This Assessment |
|----------------|-------------------------------|
| `ARCH-REVIEW-1-STRAW-MAN.md` | Anti-pattern identification (9 structural weaknesses), severity ratings, philosophy contradictions |
| `ARCH-REVIEW-1-STEEL-MAN.md` | Proportionality verdicts (8 design decisions defended), context for accepted trade-offs |
| `ARCH-REVIEW-1-DOMAIN-HEALTH.md` | Boundary assessment (aligned/divergent), essential vs accidental complexity verdicts, SPOF register, risk register |
| `ARCH-REVIEW-1-PHILOSOPHY.md` | Primary values, consistent trade-offs, architectural metaphor, philosophy contradictions, complexity budget, cognitive load analysis, consistency model |
| `TOPOLOGY-AUTOM8Y-ASANA.md` | 27-package catalog with classifications, deployment boundaries, API surface (48-49 endpoints), tech stack |
| `DEPENDENCY-MAP-AUTOM8Y-ASANA.md` | Package adjacency (73 edges), coupling scores (15 scored pairs, top score 8/10), fan-in/fan-out, 6 circular dependency cycles, 3 critical path traces, 5 hotspot deep dives |
| `SMELL-REPORT-WS4.md` | 25 code-level findings (3 critical, 9 high, 11 medium, 2 low), ROI scores, module health matrix, boundary violation flags |

### Targeted Codebase Verifications

| Verification | Method | Result |
|-------------|--------|--------|
| DataServiceClient line count | `wc -l clients/data/client.py` | 2,175 lines (confirmed) |
| SaveSession line count | `wc -l persistence/session.py` | 1,853 lines (confirmed) |
| Barrel file line count | `wc -l models/business/__init__.py` | 239 lines (confirmed) |
| Top-level package list | `ls src/autom8_asana/` | 27 packages + `__pycache__` (confirmed) |
| models/business/ structure | `ls src/autom8_asana/models/business/` | 27 items including 2 subdirectories (detection/, matching/) (confirmed) |
| services/ file list | `ls src/autom8_asana/services/` | 16 files (confirmed) |
| cache/ structure | `ls src/autom8_asana/cache/` | 6 subdirectories (backends, dataframe, integration, models, policies, providers) (confirmed) |

### Handoff Readiness Checklist

- [x] Anti-pattern table with severity, evidence (file paths), and leverage scores (Section 1, 14 anti-patterns)
- [x] Boundary alignment scorecard for all 27 packages (Section 2, 20 aligned / 7 partially aligned / 0 misaligned)
- [x] SPOF register with cascade paths (Section 3, 10 SPOFs with cascade severity)
- [x] Risk register with severity/likelihood/impact/leverage ratings (Section 4, 18 risks)
- [x] Risk classification (7 quick wins, 8 strategic investments, 2 long-term transformations)
- [x] Confidence ratings assigned to all findings (High for code-verified, Medium for inferred)
- [x] False-positive context check performed for all anti-patterns (Column: Context Check)
- [x] Cross-reference: SMELL-REPORT-WS4 findings mapped to anti-patterns (Section 1.3, 25 findings)
- [x] DEEP-DIVE: Architectural philosophy extraction (Section 5, primary values, trade-offs, metaphor, contradictions)
- [x] DEEP-DIVE: Complexity budget analysis (Section 5.5, cache = 14.1% / 17.9% of LOC)
- [x] DEEP-DIVE: Cognitive load assessment (Section 5.6, per-task learning curves)
- [x] DEEP-DIVE: Module-to-domain alignment scoring (Section 6, all 27 packages, mean 4.0/5.0)
- [x] Unknowns section (Section 7, 4 unknowns requiring human context)
- [x] Provenance section (Section 8, source artifacts + targeted verifications)

### Acid Test

*Can the remediation-planner rank and prioritize recommendations using only this architecture-assessment and the prior artifacts, without needing to independently evaluate any structural concern?*

**Yes.** Every risk register entry (R-001 through R-018) includes severity, likelihood, impact, leverage score, classification (QW/SI/LT), source anti-pattern or SPOF reference, and file-path evidence. The remediation-planner can sort by leverage score, filter by classification, and produce a prioritized roadmap without re-analyzing any code.
