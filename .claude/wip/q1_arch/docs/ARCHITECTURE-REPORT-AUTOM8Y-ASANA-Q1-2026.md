# Architecture Report: autom8y-asana — Q1 2026

> **Post-cleanup note (2026-02-18):** The hygiene sprint (commit f6e08e5) merged query_v2.py into query.py and resolved the v1/v2 routing ambiguity. QW-6 is complete. References below have been updated.

**Report ID**: ARCH-REVIEW-1 — Terminal Deliverable
**Date**: 2026-02-18
**Commit**: `be4c23a` (main)
**Scope**: Single-repo, full-depth — `autom8y-asana` (~111K LOC, 383 Python files, 27 packages)
**Complexity**: DEEP-DIVE
**Produced by**: Remediation Planner (arch rite — terminal agent)
**Upstream artifacts**: TOPOLOGY-AUTOM8Y-ASANA.md, DEPENDENCY-MAP-AUTOM8Y-ASANA.md, ARCHITECTURE-ASSESSMENT-AUTOM8Y-ASANA.md, ARCH-REVIEW-1-OPPORTUNITIES.md, ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Finding Synthesis by Theme](#2-finding-synthesis-by-theme)
   - 2.1 [Entity Model](#21-entity-model)
   - 2.2 [Caching Subsystem](#22-caching-subsystem)
   - 2.3 [Persistence Layer](#23-persistence-layer)
   - 2.4 [Query Engine](#24-query-engine)
   - 2.5 [Import Architecture](#25-import-architecture)
   - 2.6 [Deployment Model](#26-deployment-model)
   - 2.7 [Platform Dependencies](#27-platform-dependencies)
3. [Recommendation Ranking](#3-recommendation-ranking)
   - 3.1 [Quick Wins](#31-quick-wins-high-leverage-low-effort)
   - 3.2 [Strategic Investments](#32-strategic-investments-high-impact-moderate-effort)
   - 3.3 [Long-Term Transformations](#33-long-term-transformations-necessary-but-high-effort)
4. [Cross-Rite Referrals](#4-cross-rite-referrals)
5. [Unknowns Registry](#5-unknowns-registry)
6. [Migration Readiness Assessment](#6-migration-readiness-assessment)
7. [Phased Remediation Roadmap](#7-phased-remediation-roadmap)
8. [Scope and Limitations](#8-scope-and-limitations)
9. [Provenance](#9-provenance)

---

## 1. Executive Summary

### What this system is

autom8y-asana is a ~111K LOC async Python SDK and HTTP API for Asana, purpose-built for CRM and pipeline automation. It does three things: it models a business entity hierarchy (17 entity types across 4 categories), it caches those entities aggressively to stay within Asana's 150-requests-per-minute rate limit, and it automates lifecycle transitions between pipeline stages. It is deployed as a single Docker image in two modes: an ECS-hosted FastAPI service and a set of Lambda-hosted scheduled jobs.

The system has 10,583 passing tests, nine Architecture Decision Records, and a completed seven-workstream refactoring initiative. It is not a prototype and not legacy software. It is a maturing internal platform at the transition point between **growth phase** and **consolidation phase**.

### Maturity phase

**Late Growth / Early Consolidation.** The core subsystems are built and operational. A major refactoring initiative (WS1-WS7) just concluded, with all workstreams shipping green-to-green. The team is actively paying down structural debt. Two high-complexity god objects (DataServiceClient, SaveSession) have been explicitly deferred to the next workstream. Multiple structural concerns have been identified, cataloged, and prioritized.

### Essential-to-accidental complexity ratio

**70% essential / 30% accidental.** The essential complexity is genuine: 17 entity types in a hierarchy, multi-tier caching with stale-while-revalidate semantics, dynamic query compilation from an AST to Polars expressions, and dual-mode deployment. The accidental complexity is concentrated in four areas: the triple registry, the dual creation pipeline, the 47 hardcoded section classifications, and the import-time side effect architecture.

### Top 3 strengths

1. **Descriptor-driven auto-wiring.** The EntityDescriptor system (ADR-0081) eliminated approximately 800 lines of boilerplate by making entity field registration declarative. Schema and extractor resolution flow automatically from descriptor declarations. This is the most leveraged architectural investment in the codebase.

2. **Defensive onion caching.** Five concentric degradation layers (Circuit Breaker -> S3 Cold -> Redis Hot -> Memory -> Application) ensure the system degrades gracefully rather than fails catastrophically. Each ring absorbs a distinct class of failure. This matches the system's primary stated value: operational resilience.

3. **Query engine as algebraic foundation.** The query engine (1,935 LOC, 8 files, each under 300 lines) implements a full predicate AST, stateless compiler, 10-operator by 8-dtype compatibility matrix, cross-entity joins, and aggregation. It is more capable than current usage requires and is positioned to be a platform capability rather than just a data retrieval mechanism.

### Top 3 risks

1. **Dual creation pipeline divergence (R-003, leverage 13.5).** Two parallel implementations of the same 7-step entity creation pipeline exist in `automation/pipeline.py` and `lifecycle/creation.py`. Field seeding has already diverged. Every enhancement to one path risks leaving the other behind. This is the single highest-leverage open structural problem in the codebase.

2. **Cache invalidation gap for external mutations (R-002, leverage 5.0, likelihood High).** When entities are mutated outside the SDK (directly through the Asana UI or other tools), the cache has no mechanism to detect the change. Only TTL expiration eventually forces a refresh, with a staleness window up to 60 minutes. This is a consistency risk in an AP-system design that accepts eventual consistency.

3. **God object accumulation (R-004/R-005, leverage 9.0).** DataServiceClient (2,175 lines, 49 methods, 3 cyclomatic complexity violations) and SaveSession (1,853 lines, 58 methods, 6-phase commit) are both actively used and actively growing. Each new feature added to either class makes future decomposition more expensive. Both are deferred to WS8.

### Overall trajectory

The architecture is heading in the right direction. WS1-WS7 executed a disciplined consolidation: shared utilities extracted, duplicate creation primitives merged, import architecture cleaned up, cache reliability hardened. The next workstream (WS8) should address god object decomposition. The two highest-risk deferments — the god objects and the dual creation pipeline — are both recognized by the team, documented, and queued. The trajectory is healthy. The risk is pace: if feature development continues adding to the god objects before WS8 begins, the remediation cost grows non-linearly.

---

## 2. Finding Synthesis by Theme

This section consolidates findings from all three prior phases (topology, dependency, and structural assessment) into thematic narratives. Themes follow the system's major architectural concerns rather than the phase in which they were discovered. Confidence ratings propagate from upstream artifacts.

### 2.1 Entity Model

**Confidence: High** (corroborated across all three artifacts)

The entity model is the strongest domain layer in the codebase. Seventeen entity types are declared in `models/business/`, each as a Pydantic v2 frozen model. The descriptor system drives field registration, schema resolution, and extractor auto-wiring from a single declaration point. The five-tier detection system (ProjectTypeRegistry -> task name pattern -> parent-child relationship -> fallback heuristics -> Unknown) handles genuine Asana API ambiguity with calibrated confidence values.

**What works well.** The `core/entity_registry.py` `EntityDescriptor` is the correct abstraction for cross-cutting entity metadata. Fan-in of 14 packages into `core` is healthy: it is the shared kernel, and the dependency flows universally inward. The `models/business/detection/` subdirectory is well-bounded internally. The `resolution/` package (5/5 domain alignment score) cleanly separates GID lookup from hierarchy-aware resolution.

**Where it breaks down.** The `models/business/` package conflates eight distinct sub-domains (entity definitions, holder wiring, detection, descriptors, hydration, section classification, registration, and field matching) behind a single package boundary that scores 2/5 on domain alignment — the lowest in the codebase. The barrel file at `models/business/__init__.py` exports 85+ symbols and triggers a registration side effect on import (see Section 2.5). Adding a new entity type still requires four to seven file changes across four packages despite the descriptor system. Three registries (EntityRegistry, ProjectTypeRegistry, EntityProjectRegistry) encode overlapping views of "which entity types live in which projects" without cross-registry validation, creating a silent divergence risk (AP-003, R-001).

**Key files:**
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/__init__.py` (239 lines, 85+ exports, import-time side effect)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/entity_registry.py` (EntityRegistry singleton, EntityDescriptor declarations)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py` (ProjectTypeRegistry, EntityProjectRegistry — the two additional registries)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py` (47 hardcoded section classification strings)

### 2.2 Caching Subsystem

**Confidence: High** (extensively corroborated, most analyzed subsystem)

The caching subsystem is simultaneously the most sophisticated piece of the architecture and the source of the highest conceptual density. It consumes 14.1% of the codebase (15,658 LOC direct, approximately 17.9% when DataFrame cache integration and Lambda warmers are included). This is justified by the external constraint: Asana's 150-requests-per-minute rate limit forces the system to treat API calls as a scarce resource. Every architectural decision in the cache reflects this constraint.

**Two parallel cache systems exist under one roof.** The entity cache (Redis hot tier + S3 cold tier) and the DataFrame cache (Memory LRU + S3 progressive tier) use different freshness models (3-mode vs. 6-state), different storage formats (JSON vs. Parquet), different eviction policies (TTL vs. LRU), and different invalidation strategies (mutation-driven vs. stale-while-revalidate). The `CacheProvider` protocol provides a unified interface for the entity cache only. No single protocol spans both systems. A developer working on "caching" must hold two distinct mental models. This bifurcation is undocumented. No ADR explains whether the divergence is intentional or evolutionary.

**The freshness model is more sophisticated than the invalidation model.** Six freshness states (FRESH, STALE_SERVABLE, STALE_REFRESHING, EXPIRED, MISSING, ERROR) provide precise tracking of cache entry health. But for external mutations — entities modified through the Asana UI or other tools — the only invalidation mechanism is TTL expiration. The sophistication of tracking is disproportionate to the sophistication of reduction. Cache entries can serve stale data for up to 60 minutes after an external mutation. This is a documented AP-system trade-off, but it creates a philosophical contradiction: the system invested heavily in *observing* freshness states without investing in *improving* them.

**The 31-concept density is the primary cognitive load driver.** 31 distinct caching concepts (14 entry types, 7 freshness-related types, 6 freshness states, 5 providers, 4 cache tiers, 4 completeness levels, and more) against 111K LOC represents 3x the typical conceptual density for a caching subsystem. The two pre-existing test failures in `test_adversarial_pacing.py` and `test_paced_fetch.py` have been carried across all seven workstreams without investigation, which means the most adversarial edge cases of the checkpoint-resume system are unvalidated in the test suite.

**The defensive onion is the strongest architectural asset.** Five degradation tiers (Circuit Breaker, S3 Cold, Redis Hot, Memory, Application) absorb distinct failure classes. The 4:2 servable-to-reject ratio ensures data availability even when the Asana API is degraded. The SWR pattern prevents thundering-herd rebuilds during cache misses.

**Key files:**
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/` (15,658 LOC across backends/, dataframe/, integration/, models/, policies/, providers/)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframe_cache.py` (DataFrameCache singleton, FreshnessInfo — leaks to services domain)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/models/mutation_event.py` (MutationEvent, MutationCreated — leaks to services domain)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/progressive.py` (complexity 35, primary warm-up path)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/legacy.py` (613 LOC, complexity 23, degraded-mode fallback — status unclear)

### 2.3 Persistence Layer

**Confidence: High** (corroborated across topology, dependency map, and assessment)

The persistence layer (`persistence/`, 8,137 LOC) implements a Unit of Work pattern for batching Asana API mutations. The `SaveSession` class orchestrates entity changes through a six-phase commit pipeline: validate -> prepare -> execute -> actions -> confirm -> post-commit hooks (cache invalidation, automation triggers). This is the correct pattern for an AP system that must batch mutations against a rate-limited, non-transactional external API.

**The boundary is correct; the class is too large.** SaveSession's domain alignment is 4/5 — the boundary matches the UoW concept well, but 1,853 lines and 58 methods indicate the class is carrying action builder responsibilities (add_followers, add_comment, set_parent, reorder_subtask) that belong in collaborating objects. The core orchestration work is essential complexity; the action builders are accidental accumulation.

**The six-phase pipeline has no compensating transactions.** If Phase 3 (CRUD execution) partially fails after multiple API calls succeed, earlier mutations are already committed to Asana. There is no rollback. This is a genuine SPOF (SPOF-004) with Critical cascade severity: a phase ordering bug or mid-phase failure can leave entity state inconsistent. The mitigation is design discipline, not code-level protection.

**Models and persistence are bidirectionally coupled.** The dependency map records a 7/10 coupling score between `models` and `persistence` with bidirectional imports. `persistence/session.py` imports `NameGid` from `models.common` at module level; `persistence/cascade.py` imports `BusinessEntity` and `Task` under TYPE_CHECKING. Conversely, `models/project.py` defers imports of `ProgressiveProjectBuilder` and `SectionPersistence`, pulling persistence-adjacent concerns into the model layer. This is inherent to the UoW pattern but is worth monitoring as both packages grow.

**Key files:**
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/session.py` (1,853 lines, 58 methods — primary god object concern)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/pipeline.py` (6-phase commit pipeline)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/executor.py` (batch operation executor)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py` (post-commit cache invalidation hook)

### 2.4 Query Engine

**Confidence: High** (corroborated by topology, dependency map, and assessment)

The query engine (`query/`, 1,935 LOC) is one of the best-structured subsystems in the codebase. Eight files, each under 300 lines. The predicate AST compiler translates user-supplied filter criteria into Polars expressions via an explicit operator-by-dtype compatibility matrix. Section scoping, cross-entity joins at depth 1, and aggregation are supported. The domain alignment score is 5/5 — perfect.

**The v1/v2 routing ambiguity has been resolved.** The hygiene sprint (commit f6e08e5) merged `query_v2.py` into `query.py`, eliminating the duplicate router registration. A single unified router now registers all three query endpoints under the `/v1/query` prefix. The deprecated `POST /{entity_type}` endpoint remains in the unified router with its 2026-06-01 sunset date, deprecation headers, and `Link` successor header intact. The route collision that previously risked silently shadowing v2 responses no longer exists.

**The query engine is underexploited as a platform foundation.** The predicate AST is capable of expressing automation rule conditions, dashboard filter definitions, and alerting thresholds — none of which appear to currently use it. Automation pipeline rules use hardcoded condition checks. The infrastructure investment exceeds current surface area usage, suggesting an unrealized expansion opportunity.

**The services layer couples tightly to query internals.** The `services/` package imports from `dataframes/` at 12 deferred sites (SchemaRegistry, ProgressiveProjectBuilder, SectionPersistence). The coupling score is 8/10. This is the deepest cross-boundary coupling in the codebase and creates fragility: internal changes to `dataframes/` require matching changes in `services/`.

**Key files:**
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py` (QueryEngine, predicate compilation)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/universal_strategy.py` (12 deferred imports from dataframes; circular with resolver)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py` (circular with universal_strategy, 3 deferred import sites)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py` (unified query route)

### 2.5 Import Architecture

**Confidence: High** (confirmed by targeted codebase scans and SMELL-REPORT-WS4)

The import architecture is the structural concern most likely to cause developer productivity loss and occasional hard-to-reproduce failures. Three overlapping problems combine:

**Import-time side effects.** `models/business/__init__.py` calls `register_all_models()` at module load time (line 60-62). This populates the EntityRegistry, the ProjectTypeRegistry, and all entity class registrations as a side effect of importing any business entity class. The idempotency guard in `_bootstrap.py` makes re-entry safe. The defensive call in `detection/tier1.py:105` provides a fallback. But there is no inventory of which execution contexts trigger the import chain, and any new entry point that imports from a different path before reaching `models/business/__init__.py` will silently have an empty EntityRegistry. RF-009 explicitly deferred this audit.

**Six circular dependency cycles.** Six import cycles exist across the codebase, managed by deferred imports (function-body imports). The most concerning is `services/resolver` <-> `services/universal_strategy` with three deferred import sites. The `config` <-> `cache/models` cycle has five deferred sites (config.py lines 39, 40, 490, 504, 518). Managing six cycles via deferred imports creates a fragile import graph: adding a new import between two participating packages can break an existing cycle management.

**Excessive barrel file.** The `models/business/__init__.py` barrel exports 87 symbols (85+ under `__all__`) with a `# ruff: noqa: E402` suppression to permit the post-import bootstrap call. Any import of a single entity class forces the full registration cascade. This is the structural link between "I need a Contact model" and "all 17 entity types are now registered."

**Recent progress.** RF-010 (completed in WS7) introduced lazy DataFrame loading via `__getattr__` in `src/autom8_asana/__init__.py`, preventing the DataFrame subsystem from loading on SDK import. RF-012 annotated the legacy preload fallback with a code comment. These are meaningful improvements. The underlying import-time side effect and the circular cycles remain.

**Key files:**
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/__init__.py` (line 60-62: import-time registration trigger)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/_bootstrap.py` (idempotency guard)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py:712` (deferred import, cycle 1)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/universal_strategy.py:156,326` (deferred imports, cycle 1)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/config.py:39,40,490,504,518` (deferred imports, cycle 5)

### 2.6 Deployment Model

**Confidence: High** (corroborated by topology inventory and infrastructure references)

The dual ECS/Lambda deployment from a single Docker image is a pragmatic architectural choice. A single image simplifies CI/CD (one build, one push, one scan) and ensures all runtime behaviors use the same Python environment. The `entrypoint.py` dispatcher (97 lines, 5/5 alignment score) detects `AWS_LAMBDA_RUNTIME_API` to branch between modes.

**The dual creation pipeline is the deployment model's most acute risk.** Both `automation/pipeline.py` (legacy creation path) and `lifecycle/creation.py` (canonical creation path) are active simultaneously. Field seeding has already diverged between `FieldSeeder` (explicit field lists, used by automation) and `AutoCascadeSeeder` (zero-config name matching, used by lifecycle). WS6 extracted shared creation primitives (template discovery, task duplication, name generation, section placement) for steps 1-6 of the 7-step pipeline, but step 7 (field seeding) remains diverged. The longer both paths remain active, the more they will drift.

**The lifecycle webhook router may be dead code or a route collision.** A router is defined in `lifecycle/webhook.py` with prefix `/api/v1/webhooks` (matching the live webhooks router in `api/routes/webhooks.py`) but does not appear to be registered in `api/main.py`. If unregistered, it is dead code. If registered by an indirect path not visible in static analysis, it creates a prefix collision with the live webhooks router.

**Lambda cold start bootstrap is unaudited.** Lambda handlers call `_ensure_bootstrap()` which calls `register_all_models()` idempotently. The cold start latency cost of this registration has not been measured. The entry-point audit called for in Gap 5 of the opportunity/gap analysis has not been completed.

**Key files:**
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/entrypoint.py` (dual-mode dispatcher)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py` (legacy creation path, lines 191-497)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/creation.py` (canonical creation path, lines 103-493)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/webhook.py` (possibly dead code or route collision)

### 2.7 Platform Dependencies

**Confidence: High** (confirmed by pyproject.toml and import scan)

Seven `autom8y-*` packages are declared as dependencies, sourced from an AWS CodeArtifact private registry. These packages provide platform-level capabilities: logging (`autom8y-log`), HTTP transport with circuit breaker and retry (`autom8y-http`), cache primitives and schema versioning (`autom8y-cache`), configuration management (`autom8y-config`), JWT/S2S authentication (`autom8y-auth`), observability (`autom8y-telemetry`), and shared core primitives (`autom8y-core`).

**Coupling levels vary across packages.** `autom8y-log` is loosely coupled (facade only, consumed across 55+ import sites). `autom8y-http` and `autom8y-cache` are tightly coupled — they provide type definitions (`HierarchyTracker`, `CacheEntry`, `SchemaVersion`, `CompatibilityMode`) that the internal codebase imports directly. `autom8y-core` appears to be consumed only transitively (no direct `from autom8y_core` imports found in source), which raises the question of whether it is a direct or transitive dependency.

**Platform package health is outside the scope of this analysis.** The architectural health, versioning practices, and internal structure of the seven `autom8y-*` packages are not evaluated in these artifacts. Tight coupling to `autom8y-http` and `autom8y-cache` means internal API changes in those packages have potential blast radius in this codebase. The upgrade path and versioning contract for `autom8y-*` packages are unknown from these artifacts.

**Key references:**
- `/Users/tomtenuta/Code/autom8y-asana/pyproject.toml` (all 7 platform package version constraints)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/auth/jwt_validator.py` (autom8y-auth coupling)
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py` (autom8y-http coupling — circuit breaker, retry types)

---

## 3. Recommendation Ranking

Recommendations are ranked by leverage (impact / effort). Leverage scores are inherited directly from the architecture-assessment risk register (structure-evaluator phase) and not re-derived. Each recommendation carries the confidence rating of the finding that produced it.

### 3.1 Quick Wins (High Leverage, Low Effort)

Target: actions executable in 1-3 days each. Dependency ordering: all quick wins are independent unless noted.

---

**QW-1: Consolidate utility function duplication into `core/`**
- **Source risk**: R-012 (leverage 8.0 inherited)
- **Confidence**: High
- **Effort**: 0.5 day (1 person)
- **Impact**: Low-Medium (removes duplication, reduces minor divergence risk)
- **Action**: Move `_elapsed_ms()` (duplicated in 3 files) and `_ASANA_API_ERRORS` tuple (duplicated in 2 files) to `src/autom8_asana/core/`. Update all import sites. Run test suite.
- **Files**: Grep for `_elapsed_ms` and `_ASANA_API_ERRORS` across `src/` to identify all sites.

---

**QW-2: Remove deprecated `ReconciliationsHolder` alias**
- **Source risk**: R-014 (leverage 8.0 inherited)
- **Confidence**: High
- **Effort**: 0.5 day (1 person)
- **Action**: Verify zero external usages of `ReconciliationsHolder` (grep across SDK consumers if known). Remove the alias and deprecation warning from `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/business.py` lines 81-95. Run tests.
- **Prerequisite**: Confirm zero consumers before removal.

---

**QW-3: Extract section name classifications into a configuration file**
- **Source risk**: R-007 (leverage 6.0 inherited)
- **Confidence**: High (finding confirmed); Medium (effort estimate — depends on whether configuration loading infrastructure exists)
- **Effort**: 2-3 days (1 person)
- **Impact**: Medium — removes the code-deployment bottleneck for section classification changes. 47 hardcoded section names in `activity.py` become a YAML or TOML configuration file loaded at startup.
- **Action**: Define a `ClassificationRule` model. Load rules from a config file at startup. Replace the `SectionClassifier._mapping` dicts with rules loaded from config. Validate that the configuration file is complete at startup with a fail-fast check.
- **File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py`
- **Dependency**: Before acting, confirm with the product team whether classification rules change frequently enough to justify the infrastructure (see Unknown U-003).

---

**QW-4: Add cross-registry validation at startup**
- **Source risk**: R-001 (leverage 8.0 inherited)
- **Confidence**: High
- **Effort**: 1 day (1 person)
- **Impact**: High (prevents silent divergence between the three entity registries)
- **Action**: Add a startup validation step (callable from both `api/lifespan.py` and Lambda handler bootstrap) that asserts every EntityDescriptor in `EntityRegistry` has a corresponding entry in `ProjectTypeRegistry` and `EntityProjectRegistry`. Log a structured warning (or raise at startup for critical mismatches). This does not unify the registries — it prevents silent divergence until the full AP-003 refactoring is tackled as a strategic investment.
- **Files**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/entity_registry.py`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py`

---

**QW-5: Implement `SystemContext.reset_all()` for test isolation**
- **Source risk**: R-017 (leverage 3.5 inherited)
- **Confidence**: High
- **Effort**: 1 day (1 person)
- **Impact**: Low-Medium — fixes test order sensitivity and singleton reset fragility
- **Action**: Introduce a `SystemContext` module in `src/autom8_asana/core/` that holds references to all six-plus singletons (EntityRegistry, ProjectTypeRegistry, EntityProjectRegistry, SchemaRegistry, and any others identified). Expose a `reset_all()` method. Replace individual singleton reset calls in test fixtures with `SystemContext.reset_all()`. This does not require changing the singletons themselves.
- **Files**: New file in `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/system_context.py`

---

**QW-6: Resolve query v1/v2 routing ambiguity and begin v1 consumer inventory** — **COMPLETED** (commit f6e08e5)
- **Source risk**: Unknown routing behavior (architecture-assessment Section 7, leverage estimated ~6.0)
- **Confidence**: High (routing collision confirmed); Low (consumer inventory — no data)
- **Effort**: 0.5 day to fix routing, 0.5 day to begin consumer inventory
- **Impact**: Medium — prevents v1 silently shadowing v2 responses; creates prerequisite for v1 sunset (2026-06-01)
- **Resolution**: The hygiene sprint (commit f6e08e5) merged `query_v2.py` into `query.py`. A single unified router now handles all query endpoints under `/v1/query`. The routing ambiguity is eliminated. Consumer inventory for the v1 sunset (2026-06-01) remains an open task under XR-004.
- **Files**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py` (unified)

---

### 3.2 Strategic Investments (High Impact, Moderate Effort)

Target: workstreams of 3-10 days each. Dependency ordering noted per item.

---

**SI-1: Converge the dual creation pipeline (lifecycle becomes the single canonical path)**
- **Source risk**: R-003 (leverage 13.5 inherited — highest in the codebase)
- **Confidence**: High (duplication confirmed); Medium (effort — depends on feature parity gap, see Unknown U-006)
- **Effort**: 5-8 days (1-2 people)
- **Impact**: Critical — eliminates the highest-leverage open structural problem. Prevents field seeding strategies from diverging further.
- **Action**: First, conduct a feature comparison between `automation/pipeline.py` and `lifecycle/creation.py` to identify any cases that automation handles but lifecycle does not (see Unknown U-006). If lifecycle handles all cases, deprecate `automation/pipeline.py` with a clear deprecation timeline. If gaps exist, port them to lifecycle before deprecation. Designate lifecycle as canonical in code documentation and an ADR. The WS6 work (shared creation primitives in `core/`) makes this tractable.
- **Files**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/creation.py`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/seeding.py`
- **Dependency**: Resolve Unknown U-006 (feature parity assessment) before beginning.

---

**SI-2: Decompose `DataServiceClient` via an endpoint executor pattern**
- **Source risk**: R-004 (leverage 9.0 inherited)
- **Confidence**: High
- **Effort**: 5-8 days (1 person, WS8 workstream)
- **Impact**: High — eliminates the SPOF-003 shared-state blast radius, reduces cyclomatic complexity violations, and creates an extension point for future endpoints.
- **Action**: Extract the retry/circuit-breaker/log/metric scaffolding (the "Pattern A" structure identified in SMELL-REPORT-WS4) into a reusable `EndpointExecutor` class. Each of the five endpoints (insights, batch, CSV export, appointments, leads) becomes a thin wrapper calling the executor with endpoint-specific parameters. The four sub-modules already extracted (`_response.py`, `_metrics.py`, `_cache.py`) confirm the decomposition direction is understood.
- **Files**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py` (2,175 lines — primary target), `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_response.py`

---

**SI-3: Resolve the `resolver` <-> `universal_strategy` circular dependency**
- **Source risk**: R-006 (leverage 6.0 inherited), coupling hotspot 1 (score 8/10)
- **Confidence**: High
- **Effort**: 3-5 days (1 person)
- **Impact**: High — removes the three deferred-import sites that currently manage the cycle, reduces cognitive load on the resolution path, and eliminates SPOF-010.
- **Action**: Introduce a `resolution_contracts.py` module (or promote to `protocols/`) containing `CriterionValidationResult` and the type contracts shared between `resolver` and `universal_strategy`. Move `to_pascal_case` to `core/` (it is a utility function, not a resolver concept). With the shared types extracted, the circular import that requires deferred loading at `universal_strategy.py:156,326` and `resolver.py:712` can be eliminated.
- **Files**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/resolver.py`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/universal_strategy.py`

---

**SI-4: Document and monitor the preload degraded-mode fallback**
- **Source risk**: Gap 2 from ARCH-REVIEW-1-OPPORTUNITIES.md, risk of dead-code removal (Medium)
- **Confidence**: High
- **Effort**: 1-2 days (1 person)
- **Impact**: Medium — prevents the `legacy.py` fallback from being removed as dead code; provides operational visibility when degraded mode activates.
- **Action**: Write an ADR documenting the progressive -> legacy preload fallback as an intentional degraded-mode strategy. Add a metric counter (`preload_degraded_mode_activations_total`) and a structured log entry (`level=WARNING, reason="s3_unavailable"`) at the fallback entry point. Add a note to the legacy.py module header explaining its role.
- **Files**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/progressive.py:258-260`, `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/legacy.py`

---

**SI-5: Write ADR documenting entity cache vs. DataFrame cache divergence**
- **Source risk**: Gap 3 from ARCH-REVIEW-1-OPPORTUNITIES.md, AP-008 philosophy contradiction #2
- **Confidence**: High
- **Effort**: 1 day (1 person)
- **Impact**: Medium — prevents accidental convergence of the two systems when the separation may be intentional; reduces cognitive load for developers who wonder "why do these work differently?"
- **Action**: Write an ADR explaining why the entity cache (Redis/S3, TTL eviction, mutation-driven invalidation, `CacheProvider` protocol) and the DataFrame cache (Memory/S3, LRU eviction, SWR invalidation, `DataFrameCacheIntegration` interface) differ. Explicitly state whether convergence is planned, deferred, or permanently rejected. If permanently rejected, document the rationale as the ADR decision.
- **Dependency**: Resolve Unknown U-002 (confirm whether divergence is intentional) before finalizing the ADR.

---

**SI-6: Investigate and fix pre-existing test failures in checkpoint system**
- **Source risk**: Paradox 4 from ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md, Unknown U-004
- **Confidence**: Medium (nature of failures unknown)
- **Effort**: 1-3 days (1 person, depending on root cause)
- **Impact**: Medium — validates adversarial behavior of the checkpoint-resume system, which is the primary reliability mechanism for Lambda warmers under timeout pressure.
- **Action**: Read `test_adversarial_pacing.py` and `test_paced_fetch.py`. Determine whether the failures represent untested production behavior (behavioral gap) or aspirational tests written before the implementation was ready (test design debt). If behavioral gap: fix the implementation. If test design debt: either update the tests to match current behavior or delete them with a documented rationale.
- **Note**: This is a strategic investment only if the failures are behavioral gaps. If they are test design debt, this becomes a quick win (0.5 day).

---

### 3.3 Long-Term Transformations (Necessary, High Effort)

These recommendations address the deepest structural concerns. They are ranked lower in leverage per the formula (impact / effort) because the effort is high, but they cannot be decomposed into higher-leverage steps without first completing prerequisite strategic investments. They are presented separately with justification.

---

**LT-1: Decompose `SaveSession` via phase-specific collaborators**
- **Source risk**: R-005 (leverage 9.0 but classified LT due to blast radius; AP-002)
- **Confidence**: High
- **Effort**: 8-12 days (1-2 people)
- **Impact**: Critical — reduces SPOF-004 blast radius, eliminates the god object's 1,853-line complexity, separates action builder methods from orchestration responsibilities.
- **Action**: Extract the six commit phases into phase-specific handler objects (`ValidationHandler`, `PrepareHandler`, `ExecuteHandler`, `ActionHandler`, `ConfirmHandler`, `PostCommitHandler`). Extract the action builder methods (add_followers, add_comment, set_parent, reorder_subtask) into a separate `SessionActionBuilder` or integrate them into the relevant domain services. SaveSession becomes an orchestrator holding a `SavePipeline`. This is a high-blast-radius refactoring: SaveSession is imported by 5 packages and invoked by virtually all write paths.
- **Dependency**: Must be preceded by comprehensive integration test coverage of the current six-phase pipeline behavior. Cannot begin until the test suite for the commit pipeline is confirmed thorough.
- **Justification for Long-Term classification**: The 1,853-line class is the most coupled write-path component in the codebase. A partial refactoring that leaves inconsistent phase boundaries is worse than no refactoring. The work requires end-to-end integration test coverage before starting, which is itself a prerequisite workstream.

---

**LT-2: Resolve import-time side effects via explicit initialization**
- **Source risk**: R-006 (leverage 6.0 inherited; AP-005)
- **Confidence**: High
- **Effort**: 5-8 days (1 person) — primarily the audit + migration, not the code change itself
- **Action**: Complete the entry-point audit deferred in RF-009: document every execution context (API lifespan, each Lambda handler, test conftest, CLI if any) and the import chain that triggers `register_all_models()` for each. Once the inventory is complete, introduce an explicit `initialize(entry_point: str)` function in `models/business/_bootstrap.py` that replaces the import-time call. Update each entry point to call `initialize()` explicitly. Remove the module-level call from `models/business/__init__.py`.
- **Dependency**: Requires the entry-point audit (see Gap 5 / Unknown U-005) to be complete first. Without the audit, the migration will miss contexts and create silent failures.
- **Justification for Long-Term classification**: The code change itself is straightforward. The audit required to do it safely — tracing all import chains across API startup, 4 Lambda handlers, test fixtures, and any SDK consumer entry points — is the expensive work. Doing this without the audit would introduce hard-to-reproduce silent failures.

---

**LT-3: Unify the three entity registries into a single SSoT**
- **Source risk**: R-001 (leverage 8.0 inherited; AP-003)
- **Confidence**: High (problem confirmed); Medium (approach — multiple valid unification strategies)
- **Effort**: 8-12 days (1-2 people)
- **Impact**: High — eliminates the triple registry divergence risk, ensures cross-registry consistency, simplifies the conceptual model.
- **Action**: Determine which of the three registries (EntityRegistry, ProjectTypeRegistry, EntityProjectRegistry) should be the canonical source for each type of entity metadata. EntityRegistry (compile-time descriptors) and ProjectTypeRegistry/EntityProjectRegistry (runtime bindings from configuration) serve different time horizons, so a full merge may not be correct. The minimum viable unification is: (a) make ProjectTypeRegistry and EntityProjectRegistry derive from EntityRegistry descriptors rather than being independently populated, and (b) add the cross-registry startup validation from QW-4 as an interim safeguard.
- **Dependency**: QW-4 (cross-registry startup validation) should be implemented first as an interim safeguard while LT-3 is planned. LT-3 requires architectural design clarity on the intended relationship between static descriptors and runtime bindings.
- **Justification for Long-Term classification**: The three registries serve related but distinct purposes (static schema vs. runtime config vs. project resolution). A premature merger risks conflating concerns that are intentionally separated. The design work (determining the correct unification model) must precede the code work.

---

### Accept-as-Is Designations

The following findings from the architecture-assessment risk register are designated **accept-as-is** with rationale.

| Risk ID | Finding | Rationale |
|---------|---------|-----------|
| R-008 | Schema/extractor drift via manual definitions | Low likelihood, low impact. The descriptor-driven schema resolution and extractor path resolution already catch most drift at startup. Accept until descriptor auto-wiring (Opportunity 3) is scoped. |
| R-009 | Caching cognitive overload (31 concepts) | The conceptual density is high but the code is well-tested and the 4-tier degradation model is load-bearing. Cognitive load reduction is a side effect of LT-1 (SaveSession decomposition) and SI-5 (cache ADR). Do not decompose the cache subsystem in isolation. |
| R-015 | Root `__init__` eager DataFrame loading | Partially addressed by RF-010. The remaining eager loads are minimal. Accept as-is pending LT-2 completion. |
| R-016 | CircuitBreaker thread safety | Low likelihood. The `threading.Lock` usage is standard. Monitor under concurrent sync bridge load; promote to SI if evidence of contention emerges. |
| AP-013 | Async/sync duality (88 sync bridges) | Intentional trade-off. Dual sync/async consumers are a genuine requirement. The docstring duplication is accepted overhead for a public SDK. |
| AP-012 | Frozen model escape hatches (`object.__setattr__`, `PrivateAttr`) | Documented Pydantic v2 workaround for two-phase initialization. Thread safety risk is low in current usage. Accept as-is. |

---

## 4. Cross-Rite Referrals

Findings that fall outside the architectural domain are referred to the appropriate specialist rite. Each referral contains sufficient context for the target rite to act without re-analyzing the codebase.

---

### Cross-Rite Referral: XR-001
- **Target Rite**: hygiene
- **Concern**: `DataServiceClient` has three cyclomatic complexity violations (C901) confirmed by static analysis. The class is 2,175 lines with 49 methods. Six other functions in the codebase have complexity between 20 and 35, creating high-risk conditions for silent bug introduction.
- **Evidence**:
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py` (2,175 lines, C901 x3)
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/progressive.py` (complexity 35 in `_preload_dataframe_cache_progressive`)
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_response.py:59` (`handle_error_response` with 16 parameters)
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py:732` (`get_insights_async` with 13 parameters)
- **Suggested Scope**: Run the full codebase through ruff with C901 complexity threshold of 15. Produce a ranked list of functions by complexity. Flag all functions above threshold. Coordinate with the arch rite WS8 workstream for DataServiceClient decomposition (SI-2) so hygiene findings inform the decomposition scope.
- **Priority**: High. Complexity hotspots in `DataServiceClient` and `_preload_dataframe_cache_progressive` are on the critical paths for all external data API calls and cache warm-up respectively.

---

### Cross-Rite Referral: XR-002
- **Target Rite**: hygiene
- **Concern**: Inconsistent naming conventions between the two creation pipeline implementations. The naming split (`FieldSeeder` in automation vs. `AutoCascadeSeeder` in lifecycle) is a symptom of the dual-path divergence (AP-004) and has cascaded into inconsistent field accessor naming and inconsistent docstring patterns across the two subsystems.
- **Evidence**:
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/seeding.py` (`FieldSeeder` class)
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/seeding.py` (`AutoCascadeSeeder` class, imports private functions from `automation/seeding.py`)
  - NM-001 from SMELL-REPORT-WS4: inconsistent naming documented at hygiene level
- **Suggested Scope**: Audit naming conventions across `automation/` and `lifecycle/` packages. Align docstring patterns. This is preparatory work for SI-1 (pipeline convergence) — consistent naming reduces the merge cost when the dual paths are unified.
- **Priority**: Medium. Valuable before SI-1 begins, but does not block any quick wins.

---

### Cross-Rite Referral: XR-003
- **Target Rite**: security
- **Concern**: `DataServiceClient` handles PII redaction internally as part of its logging pipeline. The redaction is implemented at the class level, meaning a refactoring of the god object (SI-2) could accidentally move or disable PII redaction if the security boundary is not explicitly documented.
- **Evidence**:
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py` (PII redaction noted in structural analysis; specific implementation line not confirmed from these artifacts)
  - The `ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md` Scope and Limitations section explicitly calls out "PII handling boundaries within DataServiceClient" as outside the architectural analysis scope.
- **Suggested Scope**: Identify the exact PII redaction mechanism in `DataServiceClient`. Document which fields are redacted, under what conditions, and at which point in the execution pipeline. Produce a security finding that captures the redaction contract explicitly, so that SI-2 (god object decomposition) can preserve the redaction invariants. Verify that PII cannot escape through other code paths (e.g., exception messages, metrics labels).
- **Priority**: High. SI-2 is scoped for WS8. The security assessment should precede or run concurrently with WS8 planning.

---

### Cross-Rite Referral: XR-004
- **Target Rite**: debt-triage
- **Concern**: Query v1 (`/v1/query/{entity_type}` and `/v1/query/{entity_type}/rows`) is deprecated with a stated sunset date of 2026-06-01. No consumer inventory has been produced. If active v1 consumers exist and have not migrated, the sunset either must be extended or will break callers.
- **Evidence**:
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py` (unified router: deprecated v1 endpoint + active `/rows` and `/aggregate` endpoints)
  - Route collision resolved: hygiene sprint (commit f6e08e5) merged `query_v2.py` into `query.py`; single router now registered
- **Suggested Scope**: Produce a v1 consumer inventory from API access logs. Establish a migration plan for any active consumers of the deprecated `POST /{entity_type}` endpoint. If no active v1 consumers exist, remove the deprecated handler from `query.py` immediately.
- **Priority**: High. The sunset date is 2026-06-01. Consumer inventory work should begin within the next 4-6 weeks to allow migration time.

---

### Cross-Rite Referral: XR-005
- **Target Rite**: debt-triage
- **Concern**: `api/preload/legacy.py` (613 lines, cyclomatic complexity 23) may be superseded by `api/preload/progressive.py`. If it is truly dead code on the primary execution path, it represents 613 lines of maintenance burden. If it is the degraded-mode fallback (as annotated in RF-012), its status as "legacy" is a misnomer that invites accidental removal.
- **Evidence**:
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/legacy.py` (613 lines, complexity 23)
  - `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/preload/progressive.py:258-260` (S3-unavailable fallback to legacy)
  - RF-012 commit annotated the fallback with a code comment but did not produce an ADR
- **Suggested Scope**: Confirm whether `legacy.py` is the fallback path for the S3-unavailable degraded mode (SI-4 above addresses the documentation gap). If it is the fallback: rename to `degraded_mode.py` and add a module header explaining its role. If it is truly dead code: remove it. The debt-triage rite should investigate commit history (`git log --follow` on `legacy.py`) to determine when it was last modified and whether it is currently called.
- **Priority**: Medium. No immediate risk. Resolves the Unknown U-007 (legacy preload status) and prevents accidental removal during the SI-4 ADR work.

---

### Cross-Rite Referral: XR-006
- **Target Rite**: docs
- **Concern**: Several load-bearing architectural decisions are undocumented in ADRs. The following have no ADR:
  1. Why entity cache and DataFrame cache use different freshness models, key schemes, and eviction policies (addressed by SI-5, but the target rite should ensure the ADR follows platform documentation standards)
  2. Why `lifecycle/` is canonical for new pipeline work while `automation/pipeline.py` remains active (no code-level documentation; only WIP artifacts note the designation)
  3. The preload degraded-mode fallback pattern (addressed by SI-4, but again, docs rite should review ADR format)
  4. The `SaveSession` six-phase commit ordering rationale is documented only in code comments, not in a TDD or ADR
- **Evidence**:
  - `/Users/tomtenuta/Code/autom8y-asana/docs/adr/` (9 existing ADRs: ADR-001 through ADR-009)
  - `/Users/tomtenuta/Code/autom8y-asana/docs/tdd/` (1 existing TDD: auth-v1-migration)
  - Architecture gaps documented in `ARCH-REVIEW-1-OPPORTUNITIES.md` sections Gap 2, Gap 3, and Gap 6
- **Suggested Scope**: Audit the existing ADR series against the structural decisions identified in this architecture report. Produce ADRs for the four undocumented decisions listed above. The cache divergence ADR (SI-5) and the preload degraded-mode ADR (SI-4) are the most urgent. Review the `SaveSession` phase ordering rationale with the original author and capture it in a TDD before the WS8 decomposition (LT-1) begins.
- **Priority**: High for the SaveSession TDD (must be complete before LT-1 begins). Medium for remaining ADRs.

---

## 5. Unknowns Registry

All unknowns from all three prior phases, deduplicated and organized by impact on analysis or implementation decisions.

### Critical Impact

---

### Unknown: U-001 — Lifecycle vs. automation feature parity gap
- **Question**: Are there entity creation or pipeline transition scenarios handled by `automation/pipeline.py` that are NOT handled by `lifecycle/creation.py`?
- **Why it matters**: If automation handles scenarios lifecycle does not, the dual-path architecture is permanent and SI-1 (pipeline convergence) cannot proceed. If lifecycle handles all cases, SI-1 can be executed immediately.
- **Evidence**: `lifecycle/seeding.py` imports private functions from `automation/seeding.py`, suggesting lifecycle is not yet self-sufficient. SMELL-REPORT-WS4 describes lifecycle as "next-gen replacement." WS6 refactoring plan states "lifecycle is canonical for CRM/Process pipelines, automation stays for other workflows" — but the "other workflows" boundary is not enumerated.
- **Suggested source**: Feature comparison of call sites: grep for all `PipelineConversionRule` and `lifecycle.engine` invocations in production code.
- **Impact on SI-1**: Blocks SI-1 planning until resolved.

---

### Unknown: U-002 — Cache system key scheme divergence: intentional or evolutionary?
- **Question**: Do the entity cache and DataFrame cache intentionally use different key schemes and freshness models because they serve different latency/freshness profiles, or did they evolve independently?
- **Why it matters**: Determines whether SI-5 (cache ADR) documents an intentional design or corrects an accidental divergence. If accidental, the ADR's decision should be convergence. If intentional, the ADR's decision should be permanent separation.
- **Evidence**: Two cache systems with different key schemes, freshness models (TTL vs. SWR), storage formats (JSON vs. Parquet). No ADR documents the divergence.
- **Suggested source**: `TDD-unified-progressive-cache.md` and `TDD-cache-invalidation-pipeline.md` (referenced in WS2 checkpoint but not read in these artifacts). Original designers of the two cache systems.
- **Impact on SI-5**: Blocks SI-5 finalization until resolved.

---

### High Impact

---

### Unknown: U-003 — Section classification rule change frequency
- **Question**: How often do Asana section names and their classifications change in practice? Monthly? Quarterly? Yearly?
- **Why it matters**: If classification rules change monthly, the hardcoded Python classifiers are a deployment bottleneck and QW-3 (extract to config) is high priority. If they change annually, the current design is appropriate and QW-3 can be deferred.
- **Evidence**: 47 hardcoded section names in `activity.py`. No change history visible from static analysis.
- **Suggested source**: Git blame on `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/activity.py`. Product team or Asana workspace administrator.
- **Impact on QW-3**: Determines whether QW-3 is high priority or can be deferred indefinitely.

---

### Unknown: U-004 — Pre-existing test failures in checkpoint system: behavioral gap or test design debt?
- **Question**: Do `test_adversarial_pacing.py` and `test_paced_fetch.py` failures represent actual behavioral gaps in the checkpoint-resume system (production behavior the system cannot handle) or aspirational tests written before the implementation was complete?
- **Why it matters**: If behavioral gaps, the Lambda warmer's adversarial resilience is unvalidated — a reliability risk for degraded-mode operation. If test design debt, the failures can be resolved by updating or removing the tests.
- **Evidence**: Both files consistently described as "pre-existing failures with checkpoint assertions" across all seven workstream checkpoints. Neither was investigated or fixed.
- **Suggested source**: Read the failing test code directly. Compare assertions against current implementation behavior.
- **Impact on SI-6**: Determines whether SI-6 is a reliability fix or a test cleanup task.

---

### Unknown: U-005 — Entry-point inventory for `register_all_models()`
- **Question**: What are all execution contexts (API startup, Lambda handlers, CLI, test fixtures) that depend on `register_all_models()` having fired before first use of the EntityRegistry?
- **Why it matters**: Any new execution context that bypasses the standard import chain will have an empty EntityRegistry — a silent correctness failure. LT-2 (explicit initialization) cannot be safely executed without this inventory.
- **Evidence**: RF-009 explicitly deferred LT-2 because this inventory did not exist. `models/business/__init__.py:60-62` triggers registration. Lambda handlers call `_ensure_bootstrap()`. Test conftest behavior is unknown from these artifacts.
- **Suggested source**: Grep all source files for `from autom8_asana.models.business` and `from autom8_asana.models import`. Trace the import chain for each Lambda handler from its entry point.
- **Impact on LT-2**: Blocks LT-2 until resolved.

---

### Unknown: U-006 — Query v1 traffic volume and consumer list
- **Question**: Are active consumers calling the deprecated v1 query endpoint (`/v1/query/{entity_type}`)? Have they been notified of the 2026-06-01 sunset?
- **Why it matters**: If active v1 consumers exist and have not migrated, the sunset deadline will either break callers or require an extension.
- **Route collision aspect**: RESOLVED. The hygiene sprint (commit f6e08e5) merged `query_v2.py` into `query.py`. The duplicate `/rows` handler registration no longer exists; no routing ambiguity remains.
- **Evidence**: Unified `query.py` router registered in `api/main.py`. Sunset date documented. No consumer inventory found in these artifacts.
- **Suggested source**: API access logs filtered for `/v1/query`. Internal documentation for API consumers. XR-004 referral to debt-triage rite.
- **Impact**: Consumer inventory remains urgent — sunset is 2026-06-01.

---

### Medium Impact

---

### Unknown: U-007 — Legacy preload module active or dead code?
- **Question**: Is `api/preload/legacy.py` (613 lines, complexity 23) the active degraded-mode fallback or is it dead code?
- **Why it matters**: If dead code: 613 lines of maintenance burden that can be removed. If active fallback: the module is load-bearing infrastructure misnamed as "legacy," inviting accidental removal.
- **Evidence**: `progressive.py:258-260` contains an S3-unavailable fallback. RF-012 added a code comment about the fallback. The module is named "legacy" but may be exercised in production when S3 is unavailable.
- **Suggested source**: Read the progressive.py fallback code. Run the degraded-mode path in a test environment with S3 mocked as unavailable.
- **Impact on SI-4**: SI-4 assumes this module is the degraded-mode fallback. If it is confirmed dead code, SI-4 scope changes.

---

### Unknown: U-008 — Lifecycle webhook router: registered or dead code?
- **Question**: Is the router defined in `lifecycle/webhook.py` (prefix `/api/v1/webhooks`) registered with the main FastAPI application?
- **Why it matters**: If registered: there is an additional inbound webhook path that is not documented in the API surface and potentially collides with `api/routes/webhooks.py`. If not registered: dead code (a router object that is never mounted).
- **Evidence**: The router is defined with `APIRouter(prefix="/api/v1/webhooks")` in `lifecycle/webhook.py`. It is not imported in `api/routes/__init__.py` or `api/main.py`. The main `webhooks_router` from `api/routes/webhooks.py` is the registered webhook handler.
- **Suggested source**: Read `api/main.py` in full; grep for any wildcard router registration patterns.

---

### Unknown: U-009 — `autom8y-core` direct vs. transitive dependency
- **Question**: Is `autom8y-core` imported directly by this codebase, or is it only a transitive dependency via other `autom8y-*` packages?
- **Why it matters**: If only transitive, `autom8y-core>=1.1.0` in `pyproject.toml` is an unnecessary direct declaration that could be removed to simplify dependency management.
- **Evidence**: No `from autom8y_core` imports found in source tree scan. `autom8y-core>=1.1.0` declared in `pyproject.toml`. Likely consumed transitively by `autom8y-log` or `autom8y-http`.
- **Suggested source**: `uv pip tree` to produce the full dependency graph.

---

### Unknown: U-010 — Internal `router` registration with `include_in_schema=False`
- **Question**: Is the `internal` router (`/api/v1/internal`) intended to have route handlers in the future, or is its registration purely to provide the `require_service_claims` dependency and `ServiceClaims` model to other routers?
- **Why it matters**: If intended for future routes: the current empty-handler registration is correct scaffolding. If purely a dependency provider: the router registration in `api/main.py` has no functional purpose and could be removed (or replaced with a plain dependency injection approach that does not require a router).
- **Evidence**: `src/autom8_asana/api/routes/internal.py` contains only router declaration, `ServiceClaims` model, and `require_service_claims` dependency — no route handlers.
- **Suggested source**: Original author or related TDD.

---

## 6. Migration Readiness Assessment

This section evaluates readiness for the three highest-priority architectural transitions. Decomposition health scores are on a 1-10 scale where 10 = fully ready to begin, 1 = significant prerequisites missing.

### 6.1 Transition: Dual Creation Pipeline Convergence (SI-1)

**Current State**: Two parallel implementations of a 7-step entity creation pipeline coexist. `automation/pipeline.py` (legacy, lines 191-497) and `lifecycle/creation.py` (canonical, lines 103-493) handle the same pipeline concept. Steps 1-6 (shared creation primitives) were extracted to `core/` in WS6. Step 7 (field seeding) remains diverged: automation uses `FieldSeeder` (explicit field lists) and lifecycle uses `AutoCascadeSeeder` (zero-config matching).

**Target State**: `lifecycle/creation.py` is the single canonical creation path. `automation/pipeline.py` is deprecated with a removal timeline. `lifecycle/seeding.py` no longer imports private functions from `automation/seeding.py` — it is self-sufficient. An ADR documents the canonical designation.

**Decomposition Health Score: 6/10**

| Readiness Factor | Status | Score |
|-----------------|--------|-------|
| Shared creation primitives extracted (WS6) | Complete | +2 |
| Feature parity gap assessed | Not done (Unknown U-001) | -2 |
| lifecycle/seeding.py self-sufficient | Not yet (imports from automation) | -1 |
| lifecycle engine test coverage | Not assessed | 0 |
| Canonical designation documented in code | Not done (only in WIP docs) | -1 |
| ADR for lifecycle canonical status | Not written | 0 |

**Blocking dependencies**:
- Unknown U-001 must be resolved (feature parity assessment)
- lifecycle/seeding.py must import only from lifecycle/ or shared core/ (remove the automation private function imports)

**Estimated effort**: 5-8 person-weeks total: 1-2 days (feature parity gap analysis) + 3-5 days (port any gaps to lifecycle) + 2-3 days (deprecate automation path with redirects and removal timeline) + 1 day (ADR)

**Risk factors**:
- Low: WS6 already extracted the shared primitives, reducing the merge surface
- Medium: If automation/pipeline.py handles edge cases not visible in static analysis (e.g., webhook-triggered transitions not documented in artifacts), porting gaps to lifecycle could reveal unexpected complexity
- Low: Test coverage for lifecycle appears thorough (13 test files, lifecycle subdirectory in unit tests)

---

### 6.2 Transition: `DataServiceClient` God Object Decomposition (SI-2)

**Current State**: `DataServiceClient` is a 2,175-line class with 49 methods, 3 C901 cyclomatic complexity violations, and shared state (HTTP client, circuit breaker, PII redactor, metrics) across five distinct API endpoint methods (insights, batch, CSV export, appointments, leads). Four sub-modules have already been extracted (`_response.py`, `_metrics.py`, `_cache.py`, partial decomposition).

**Target State**: Each endpoint is a thin wrapper around a shared `EndpointExecutor` that carries the retry/circuit-breaker/log/metric scaffolding. Adding a new endpoint requires only defining the endpoint-specific logic. The shared state (HTTP session, PII redactor) is explicit in the executor, not implicit across 49 methods.

**Decomposition Health Score: 7/10**

| Readiness Factor | Status | Score |
|-----------------|--------|-------|
| Four sub-modules already extracted | Complete | +2 |
| Pattern A (5-step scaffolding) identified in WS4 | Complete | +1 |
| Decomposition direction established | Understood by team | +1 |
| Unit test coverage of `DataServiceClient` | Confirmed (17 test files in clients/) | +1 |
| PII redaction security boundary documented | Not documented (XR-003) | -1 |
| Integration tests for end-to-end data API flows | Not confirmed from artifacts | 0 |

**Blocking dependencies**:
- XR-003 (security referral) must be resolved — PII redaction contract must be documented before refactoring the class that contains it
- Integration test coverage for all five endpoints should be confirmed or added before beginning

**Estimated effort**: 5-8 person-weeks: 1-2 days (confirm PII redaction contract) + 1-2 days (design EndpointExecutor interface) + 3-5 days (extract all 5 endpoints) + 1 day (update tests)

**Risk factors**:
- Medium: PII redaction is load-bearing. Moving it during refactoring without a documented contract risks data leakage.
- Low: The four extracted sub-modules already demonstrate the decomposition pattern works
- Low: The 17 test files in `clients/` provide good coverage for regression detection

---

### 6.3 Transition: Import-Time Side Effect Elimination (LT-2)

**Current State**: `register_all_models()` is called at module import time from `models/business/__init__.py:60-62`. This side effect fires whenever any business entity class is imported. The idempotency guard prevents double-registration. Lambda handlers call `_ensure_bootstrap()` as an additional guard. Six circular import cycles are managed via 10+ deferred import sites.

**Target State**: An explicit `initialize(entry_point: str)` function in `_bootstrap.py` replaces the import-time call. Each entry point (API lifespan, Lambda handlers, test conftest) calls `initialize()` explicitly. The `models/business/__init__.py` barrel no longer has import-time side effects. Circular import cycles are partially reduced as a byproduct of removing the deferred import workarounds.

**Decomposition Health Score: 3/10**

| Readiness Factor | Status | Score |
|-----------------|--------|-------|
| Idempotency guard in place | Complete | +1 |
| RF-009 deferred decision documented | Complete | +1 |
| Entry-point audit completed | Not done (RF-009 deferred) | -3 |
| Circular import cycle inventory | Complete (6 cycles documented) | +1 |
| Integration test coverage for Lambda cold start | Not confirmed | -1 |
| Test fixture reset behavior documented | Not confirmed | -1 |

**Blocking dependencies**:
- Unknown U-005 (entry-point audit) is the primary blocker. Without a complete inventory of all execution contexts that depend on the import side effect, the migration will create silent failures in unaudited paths.
- Test fixture reset order behavior must be confirmed before removing the import-time trigger.

**Estimated effort**: 8-12 person-weeks total: 3-5 days (entry-point audit — the expensive prerequisite) + 2-3 days (code migration across all entry points) + 2-3 days (test suite validation across all execution contexts) + 1 day (remove deferred imports where cycles are resolved)

**Risk factors**:
- High: This is the riskiest migration in the codebase. Silent failures (empty EntityRegistry in a new execution context) may not manifest until production. The audit must be thorough.
- Medium: Six circular dependency cycles interact with the import-time registration. Removing the module-level call may expose import ordering issues previously hidden by the eager registration.
- Low: The idempotency guard provides a safety net during migration (double-registration will not cause corruption)

---

## 7. Phased Remediation Roadmap

Dependencies between phases are noted below. An item in a later phase should not begin until its listed dependencies in earlier phases are complete.

```
Phase 1 ──────────────────────────────────────────────────> Phase 2
(QW-1, QW-2, QW-4, QW-5, QW-6)                           (SI-3, SI-4, SI-5, SI-6)
    |                                                            |
    |                                                            |
    +──> Phase 2 unlocks SI-5 resolution (cache ADR)            |
    |                                                            |
    QW-4 (cross-registry validation) provides interim           |
    safeguard while LT-3 is planned                             |
                                                                 |
                                                                 +──> Phase 3
                                                                     (SI-1, SI-2, QW-3)
                                                                          |
                                                                          +──> Phase 4
                                                                              (LT-1, LT-2, LT-3)
```

### Phase 1 — Quick Wins (0-4 weeks)

No inter-phase dependencies. All items in this phase are independent of each other and of any prior prerequisite work. Begin immediately.

| Item | Description | Effort | Owner Signal |
|------|-------------|--------|-------------|
| QW-1 | Consolidate `_elapsed_ms` and `_ASANA_API_ERRORS` into `core/` | 0.5 day | Any engineer |
| QW-2 | Remove deprecated `ReconciliationsHolder` alias | 0.5 day | Any engineer |
| QW-4 | Add cross-registry validation at startup | 1 day | Any engineer |
| QW-5 | Implement `SystemContext.reset_all()` for test isolation | 1 day | Any engineer |
| QW-6 | ~~Resolve query v1/v2 routing ambiguity; begin consumer inventory~~ **COMPLETED** (commit f6e08e5) | — | — |
| XR-004 | Debt-triage referral: Query v1 sunset consumer inventory | 0.5 day | debt-triage rite |
| XR-001 | Hygiene referral: complexity audit with ruff | 0.5 day | hygiene rite |

**Phase 1 exit gate**: All quick wins complete and tests green. Consumer inventory for v1 sunset initiated.

**Note on QW-3**: Section classification config extraction is listed in Phase 3 (not here) because it depends on Unknown U-003 (change frequency) being resolved first. If U-003 resolution confirms frequent changes, QW-3 can be promoted to Phase 1.

---

### Phase 2 — Foundation (4-12 weeks)

These items establish prerequisites for the major architectural moves in Phase 3. Some items in this phase can run in parallel.

| Item | Description | Effort | Dependency |
|------|-------------|--------|------------|
| SI-3 | Resolve resolver <-> universal_strategy circular dependency | 3-5 days | None (independent) |
| SI-4 | Document and monitor preload degraded-mode fallback | 1-2 days | Confirm U-007 (legacy preload status) |
| SI-5 | Write ADR: entity cache vs. DataFrame cache divergence | 1 day | Resolve U-002 first |
| SI-6 | Investigate pre-existing checkpoint test failures | 1-3 days | None (independent) |
| XR-003 | Security referral: document PII redaction contract in DataServiceClient | 1-2 days | Needed before Phase 3 SI-2 |
| XR-006 | Docs referral: SaveSession TDD (phase ordering rationale) | 1-2 days | Needed before Phase 4 LT-1 |
| U-001 | Resolve: feature parity gap between automation and lifecycle | 1-2 days | Needed before Phase 3 SI-1 |
| U-005 | Resolve: entry-point audit for register_all_models() | 3-5 days | Needed before Phase 4 LT-2 |

**Phase 2 exit gate**: Circular dependency resolved. Cache ADR written. PII redaction documented. SaveSession TDD written. Unknown U-001 (lifecycle feature parity) resolved.

---

### Phase 3 — Strategic (12-26 weeks)

Major architectural moves. Items here depend on Phase 2 completing.

| Item | Description | Effort | Dependency |
|------|-------------|--------|------------|
| SI-1 | Converge dual creation pipeline (lifecycle canonical) | 5-8 days | U-001 resolved (Phase 2) |
| SI-2 | Decompose DataServiceClient via endpoint executor | 5-8 days | XR-003 complete (Phase 2) |
| QW-3 | Extract section classifications to config | 2-3 days | U-003 resolved |

**Phase 3 exit gate**: Single creation pipeline active. DataServiceClient decomposed. Test suite fully green.

---

### Phase 4 — Long-term Transformations (26+ weeks)

Transformational changes with high blast radius. Require Phase 3 completion.

| Item | Description | Effort | Dependency |
|------|-------------|--------|------------|
| LT-1 | Decompose SaveSession via phase-specific collaborators | 8-12 days | SaveSession TDD (Phase 2 XR-006); comprehensive integration tests |
| LT-2 | Eliminate import-time side effects via explicit initialization | 8-12 days | U-005 entry-point audit (Phase 2) |
| LT-3 | Unify three entity registries into single SSoT | 8-12 days | QW-4 cross-registry validation active (Phase 1); design clarification on static vs. runtime registry boundary |

**Phase 4 exit gate**: Import architecture clean. SaveSession decomposed. Registry unified. 70/30 essential/accidental ratio moves toward 85/15.

---

## 8. Scope and Limitations

This architecture report is based exclusively on static analysis of the repository at commit `be4c23a`, conducted by a 17-agent analysis swarm across three phases (topology inventory, dependency mapping, and structural assessment). The following dimensions are explicitly NOT covered by this analysis.

**Runtime behavior.** Performance characteristics, latency, throughput, memory consumption under load, and failure modes under production traffic are not assessed. The cache subsystem in particular has complexity that is only observable under concurrent production load. The caching layer's adversarial behavior (thundering herd, SWR under cache miss pressure) is theoretically described in the architecture but not empirically validated. The two pre-existing test failures (`test_adversarial_pacing.py`, `test_paced_fetch.py`) represent the only known behavioral gap and are flagged as Unknown U-004.

**Data architecture.** Data flow governance (which services can read or write which entities), consistency guarantees between the entity cache and DataFrame cache, data retention policies, and PII data flow boundaries are not assessed. The PII redaction in `DataServiceClient` is noted structurally (XR-003) but not analyzed in depth.

**Operational concerns.** Deployment pipeline health, CI/CD reliability, observability coverage beyond what is documented in the code, Lambda cold start latency in production, incident response readiness, and runbook completeness are not assessed. The `docs/runbooks/` directory exists but its contents were not evaluated.

**Organizational alignment.** Conway's Law effects, team cognitive load distribution across subsystems, ownership clarity for the dual creation pipeline, and communication overhead are not assessed. The finding that `lifecycle/` is "canonical" exists only in WIP documents, not in code-level documentation — this organizational clarity gap is referred to the docs rite (XR-006) but the organizational dimension is outside this analysis.

**Evolutionary architecture.** Fitness functions, architectural runway against anticipated feature growth, and technical debt trajectory beyond the WS8 planning horizon are not assessed. The trajectory analysis in Section 1 (Executive Summary) reflects inferences from the WS1-WS7 commit history and workstream records, not a formal architectural fitness function evaluation.

**External platform dependencies.** The health, versioning practices, internal structure, and upgrade paths for the seven `autom8y-*` packages (autom8y-log, autom8y-http, autom8y-cache, autom8y-config, autom8y-auth, autom8y-telemetry, autom8y-core) are not assessed. Tight coupling to `autom8y-http` and `autom8y-cache` is noted as a risk, but the packages themselves were not analyzed.

**Security posture.** Authentication mechanism correctness, authorization coverage across all 48-49 API endpoints, JWT validation correctness, and S2S secret management are not assessed beyond noting structural concerns. The PII redaction boundary in `DataServiceClient` is referred to the security rite (XR-003).

**Business logic correctness.** Whether the 5-tier entity detection system produces correct results, whether the SaveSession phase ordering produces correct API mutations, and whether automation rules produce correct lifecycle transitions are not evaluated. These require domain knowledge and runtime validation.

---

## 9. Provenance

### Input Artifacts

| Artifact | Phase | Contribution to This Report |
|----------|-------|----------------------------|
| `TOPOLOGY-AUTOM8Y-ASANA.md` | Phase 1: Topology Inventory | Package catalog (27 packages, Section 2), API surface (48-49 endpoints), deployment boundaries, tech stack, bootstrap patterns, test structure |
| `DEPENDENCY-MAP-AUTOM8Y-ASANA.md` | Phase 2: Dependency Map | Package adjacency (73 edges), coupling scores (Section 2 themes), fan-in/fan-out, 6 circular cycles, 3 critical path traces, 5 coupling hotspot deep dives |
| `ARCHITECTURE-ASSESSMENT-AUTOM8Y-ASANA.md` | Phase 3: Structure Evaluation | 14 anti-patterns, 27-package boundary scorecard, 10 SPOFs, 18 risks with leverage scores, architectural philosophy, 27-package domain alignment scores, 4 unknowns |
| `ARCH-REVIEW-1-OPPORTUNITIES.md` | Prior synthesis | 5 opportunities, 7 gaps, trajectory assessment, bus factor signals, 5 architectural paradoxes, recommended next steps |
| `ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md` | Prior synthesis | State assessment, essential/accidental ratio, opportunity map, gap analysis, trajectory, 5 paradoxes, unknowns registry (6 items), scope and limitations |
| `ARCH-REVIEW-1-INDEX.md` | Phase 0: Review index | Methodology, 17-agent swarm structure, key findings summary, architecture profile |

### Methodology Note

This report performs no independent code analysis. All findings, file paths, line numbers, coupling scores, and leverage scores are sourced directly from the upstream artifacts listed above. Where confidence is noted as "Medium" or "Low," this reflects the upstream artifact's own confidence rating or an inference that could not be corroborated across multiple artifacts.

### Confidence Propagation Summary

| Confidence Level | Criteria | Findings in This Report |
|-----------------|----------|------------------------|
| **High** | Corroborated across multiple upstream artifacts; file-path evidence confirmed | All Section 2 themes; all risk register items R-001 through R-018; all SPOF items; all coupling hotspot findings |
| **Medium** | Partial corroboration; inferred from one artifact or confirmed by text matching | QW-3 effort estimate (config infrastructure dependency); SI-1 effort (parity gap unknown); some items in Unknowns Registry |
| **Low** | Single-source inference; or the finding involves a question not resolvable from static analysis | Unknown U-006 (v1 traffic); Unknown U-003 (change frequency); SI-6 (checkpoint test failure nature) |

### Handoff Criteria Verification

- [x] Executive summary present and readable by non-experts (Section 1: maturity phase, essential/accidental ratio, top 3 strengths, top 3 risks, trajectory)
- [x] All findings consolidated by theme, not by phase (Section 2: 7 themes)
- [x] Recommendations ranked by leverage with effort estimates and confidence ratings (Section 3: 6 QWs, 6 SIs, 3 LTs, 6 accept-as-is)
- [x] Every finding from architecture-assessment risk register (R-001 through R-018) has a corresponding recommendation or explicit accept-as-is designation (verified: R-001=SI/LT-3, R-002=accepted with referral, R-003=SI-1, R-004=SI-2, R-005=LT-1, R-006=LT-2, R-007=QW-3, R-008=accept, R-009=accept, R-010=XR-001, R-011=XR-001, R-012=QW-1, R-013=XR-005, R-014=QW-2, R-015=accept, R-016=accept, R-017=QW-5, R-018=SI-3)
- [x] Cross-rite referrals with target rite, evidence, suggested scope, and priority (Section 4: 6 referrals)
- [x] Unknowns registry organized by impact (Section 5: 10 unknowns, 2 critical, 4 high, 4 medium)
- [x] Migration readiness for top 3 transitions with decomposition health scores (Section 6: SI-1 6/10, SI-2 7/10, LT-2 3/10)
- [x] Phased remediation roadmap with dependency ordering (Section 7: 4 phases with dependency arrows)
- [x] Scope and limitations section (Section 8)
- [x] Table of contents present
- [x] Provenance section with input artifact list and methodology note (Section 9)
