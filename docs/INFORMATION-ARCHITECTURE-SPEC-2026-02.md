# Documentation Information Architecture Specification

**Version**: 2.0
**Date**: 2026-02-12
**Author**: Information Architect
**Supersedes**: INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md
**Audience**: Tech Writers executing Phase 3

---

## Executive Summary

This specification redesigns the consumer-facing documentation for autom8y-asana. The previous IA (2025-12-24) reorganized 613 internal design documents (PRDs, TDDs, ADRs). This specification addresses what that effort did not touch: **consumer-grade documentation that lets a new developer find, understand, and use the SDK in under 30 seconds.**

**Current state**: 613 markdown files, zero consolidated API reference, zero consumer-facing guides for cache/lifecycle/resolution/query/automation. Good source code docstrings exist but are invisible without an API reference surface.

**Target state**: Flat, navigable taxonomy with 4 entry points (learn, build, operate, decide), runnable examples, OpenAPI spec, and cross-references that eliminate dead-end searches.

**Scope**: New consumer-facing docs layer. Existing internal docs (PRDs, TDDs, ADRs, spikes) are preserved in place. This plan adds to them; it does not re-migrate them.

---

## 1. Documentation Taxonomy

### 1.1 Target Directory Structure

```
docs/
  INDEX.md                          # Master navigation hub (rewrite)
  CONVENTIONS.md                    # Existing: naming/style conventions
  CONTRIBUTION-GUIDE.md             # Existing: how to add docs

  getting-started/                  # NEW: Onboarding path (3 docs)
    overview.md                     #   System architecture overview
    installation.md                 #   Install, configure, first call
    core-concepts.md                #   Mental model (consolidation of guides/concepts.md)

  guides/                           # EXPANDED: Task-oriented how-tos
    authentication.md               #   Existing (keep)
    entity-write.md                 #   NEW: Writing fields via API + SDK
    entity-resolution.md            #   NEW: Resolving phone/vertical to GIDs
    entity-query.md                 #   NEW: Querying cached entity data
    lifecycle-engine.md             #   NEW: Lifecycle stages, transitions, creation
    cache-system.md                 #   NEW: Cache tiers, warming, invalidation
    save-session.md                 #   Existing (keep, update cross-refs)
    business-models.md              #   NEW: Entity hierarchy, holders, hydration
    dataframes.md                   #   NEW: DataFrame builders, schemas, extractors
    automation-pipelines.md         #   NEW: Pipeline, seeding, conversation audit
    webhooks.md                     #   NEW: Inbound events, dispatch
    search.md                       #   Existing search-cookbook.md (move + rename)

  api-reference/                    # NEW: REST API reference (generated + curated)
    README.md                       #   Overview, authentication, pagination, errors
    openapi.yaml                    #   OpenAPI 3.1 specification
    endpoints/                      #   Per-router endpoint docs (if needed beyond OpenAPI)
      tasks.md
      projects.md
      sections.md
      dataframes.md
      entity-write.md
      resolver.md
      query.md
      webhooks.md
      admin.md
      health.md

  sdk-reference/                    # NEW: Python SDK class reference
    client.md                       #   AsanaClient facade, initialization, providers
    resource-clients.md             #   TasksClient, ProjectsClient, etc.
    models.md                       #   Task, Project, Section, etc. (Pydantic models)
    business-models.md              #   Business, Unit, Offer, Contact, holders
    persistence.md                  #   SaveSession, actions, commit, events
    configuration.md                #   AsanaConfig, RateLimitConfig, etc.
    exceptions.md                   #   Exception hierarchy + when each is raised
    protocols.md                    #   AuthProvider, CacheProvider, LogProvider, etc.

  examples/                         # NEW: Runnable .py scripts
    README.md                       #   Index, prerequisites, how to run
    01-read-tasks.py                #   Basic: fetch and display tasks
    02-batch-update.py              #   SaveSession batch modifications
    03-create-with-subtasks.py      #   Create parent + children hierarchy
    04-entity-resolution.py         #   Resolve phone/vertical to GIDs
    05-entity-write.py              #   Write fields via FieldWriteService
    06-query-entities.py            #   Query cached DataFrame data
    07-lifecycle-transition.py      #   Trigger lifecycle stage change
    08-dataframe-export.py          #   Build DataFrames from project/section
    09-cache-warming.py             #   Warm and inspect cache state
    10-webhook-handler.py           #   Receive and process webhook events

  runbooks/                         # Existing (keep + expand)
    README.md                       #   Existing
    RUNBOOK-batch-operations.md
    RUNBOOK-business-model-navigation.md
    RUNBOOK-cache-troubleshooting.md
    RUNBOOK-detection-troubleshooting.md
    RUNBOOK-pipeline-automation.md
    RUNBOOK-savesession-debugging.md
    RUNBOOK-rate-limiting.md        #   NEW: 429 handling, backpressure

  reference/                        # Existing (keep, no changes)
    GLOSSARY.md
    REF-*.md                        #   All existing reference docs preserved

  decisions/                        # Existing (keep, no changes)
  design/                           # Existing (keep, no changes)
  requirements/                     # Existing (keep, no changes)
  adr/                              # Existing (keep, no changes)
  spikes/                           # Existing (keep, no changes)
  .archive/                         # Existing (keep, no changes)
```

### 1.2 File Naming Conventions

| Directory | Pattern | Example |
|-----------|---------|---------|
| `getting-started/` | `lowercase-kebab.md` | `core-concepts.md` |
| `guides/` | `lowercase-kebab.md` | `entity-write.md` |
| `api-reference/endpoints/` | `lowercase-kebab.md` | `entity-write.md` |
| `sdk-reference/` | `lowercase-kebab.md` | `business-models.md` |
| `examples/` | `NN-kebab-name.py` | `04-entity-resolution.py` |
| `runbooks/` | `RUNBOOK-kebab-name.md` | `RUNBOOK-rate-limiting.md` |
| `reference/` | `REF-kebab-name.md` | `REF-cache-architecture.md` |

### 1.3 Relationship to Existing Internal Docs

The new consumer-facing layer **sits alongside** the existing PRD/TDD/ADR structure. Cross-references flow in one direction:

```
Consumer docs (guides/, api-reference/, sdk-reference/)
    |
    |-- reference for deeper context -->  design/ (TDDs)
    |-- rationale links             -->  decisions/ (ADRs)
    |-- troubleshooting             -->  runbooks/
    |
    v
Internal docs (requirements/, design/, decisions/) remain unchanged
```

Consumer docs NEVER depend on internal docs being read first. Internal docs may link to consumer docs as "user-facing documentation" references.

### 1.4 Frontmatter Schema

All new documents use this frontmatter:

```yaml
---
title: "Document Title"
description: "One-line purpose statement"
audience: [sdk-consumer, api-integrator, operator, contributor]
prerequisites: ["getting-started/core-concepts.md"]
last_updated: "2026-02-12"
status: draft | active | deprecated
---
```

---

## 2. Navigation and Entry Points

### 2.1 Four Entry Points

The INDEX.md rewrites around four user journeys:

| Entry Point | Question | Landing Page | Audience |
|-------------|----------|--------------|----------|
| **Learn** | "What is this system?" | `getting-started/overview.md` | New developers, stakeholders |
| **Build** | "How do I use this?" | `guides/` directory | SDK consumers, API integrators |
| **Operate** | "Something is broken" | `runbooks/` directory | On-call engineers, operators |
| **Decide** | "Why was it built this way?" | `decisions/` directory | Architects, contributors |

### 2.2 Onboarding Path (New Developer)

Read order for a developer joining the team:

```
Step 1: getting-started/overview.md          (15 min)
   - System architecture, component map, what talks to what
   - Links to Asana API docs for background

Step 2: getting-started/installation.md      (5 min)
   - pip install, env vars, verify connectivity
   - First successful API call

Step 3: getting-started/core-concepts.md     (10 min)
   - Entity hierarchy (Business > Unit > Offer)
   - SaveSession pattern (track, modify, commit)
   - Four operation types (read, create, update, relationships)

Step 4: examples/01-read-tasks.py            (5 min)
   - Run it, see output, modify it

Step 5: Pick a guide based on your task:
   - Writing data? -> guides/entity-write.md
   - Resolving entities? -> guides/entity-resolution.md
   - Querying? -> guides/entity-query.md
```

### 2.3 Role-Based Learning Paths

**SDK Consumer** (Python developer calling the library):
1. `getting-started/` (all 3)
2. `guides/save-session.md`
3. `guides/business-models.md`
4. `sdk-reference/client.md`
5. `examples/` (relevant scripts)

**API Integrator** (service calling REST endpoints):
1. `getting-started/overview.md`
2. `api-reference/README.md` (auth, pagination, errors)
3. `api-reference/openapi.yaml` (import into Postman/Insomnia)
4. `api-reference/endpoints/` (specific endpoints)
5. `guides/entity-write.md`, `guides/entity-resolution.md`

**Entity Modeler** (defining new business entities):
1. `getting-started/core-concepts.md`
2. `guides/business-models.md`
3. `guides/lifecycle-engine.md`
4. `sdk-reference/business-models.md`
5. `reference/REF-entity-lifecycle.md`
6. `reference/REF-entity-type-table.md`

**Operator** (debugging production issues):
1. `runbooks/` (search by symptom)
2. `guides/cache-system.md`
3. `reference/REF-cache-architecture.md`

---

## 3. Migration Plan

### 3.1 Actions Per Existing Document

| Source | Action | Target | Notes |
|--------|--------|--------|-------|
| `guides/concepts.md` | **Consolidate** | `getting-started/core-concepts.md` | Preserve all content, add entity hierarchy section |
| `guides/quickstart.md` | **Consolidate** | `getting-started/installation.md` | Merge install steps, split off concepts |
| `guides/authentication.md` | **Keep** | `guides/authentication.md` | No change |
| `guides/save-session.md` | **Keep** | `guides/save-session.md` | Update cross-refs to new paths |
| `guides/workflows.md` | **Retire** | `examples/` + `guides/` | Recipes become runnable examples; prose becomes guide sections |
| `guides/patterns.md` | **Retire** | `guides/` (distribute) | Merge relevant patterns into topical guides |
| `guides/sdk-adoption.md` | **Keep** | `guides/sdk-adoption.md` | Internal migration guide, still useful |
| `guides/autom8-migration.md` | **Keep** | `guides/autom8-migration.md` | Cross-service migration, still active |
| `guides/search-cookbook.md` | **Move** | `guides/search.md` | Rename only |
| `guides/search-query-builder.md` | **Consolidate** | `guides/search.md` | Merge into single search guide |
| `guides/pipeline-automation-setup.md` | **Consolidate** | `guides/automation-pipelines.md` | Becomes section of automation guide |
| `guides/GUIDE-businessseeder-v2.md` | **Consolidate** | `guides/automation-pipelines.md` | Seeder content into automation guide |
| `reference/*` | **Keep** | `reference/*` | All 20 reference docs preserved as-is |
| `runbooks/*` | **Keep** | `runbooks/*` | All 6 runbooks preserved as-is |
| `decisions/*` | **Keep** | `decisions/*` | All 68 ADRs preserved as-is |
| `design/*` | **Keep** | `design/*` | All TDDs preserved as-is |
| `adr/*` | **Keep** | `adr/*` | All 8 new ADRs preserved as-is |
| `INDEX.md` | **Rewrite** | `INDEX.md` | New navigation hub with 4 entry points |
| All top-level `*-2025-12-24.md` | **Archive** | `.archive/2025-12-ia/` | IA artifacts from previous pass |

### 3.2 New Documents to Create

| Target Path | Source Material | Priority | Section 4 Brief ID |
|-------------|----------------|----------|---------------------|
| `getting-started/overview.md` | Source code, `architecture/DOC-ARCHITECTURE.md` | P0 | CB-001 |
| `getting-started/installation.md` | `guides/quickstart.md`, `__init__.py` | P0 | CB-002 |
| `getting-started/core-concepts.md` | `guides/concepts.md`, `REF-entity-lifecycle.md` | P0 | CB-003 |
| `guides/entity-write.md` | `routes/entity_write.py`, `TDD-entity-write-api.md` | P0 | CB-004 |
| `guides/entity-resolution.md` | `routes/resolver.py`, `services/resolver.py` | P1 | CB-005 |
| `guides/entity-query.md` | `routes/query.py`, `query/engine.py` | P1 | CB-006 |
| `guides/lifecycle-engine.md` | `lifecycle/engine.py`, `TDD-lifecycle-engine.md` | P1 | CB-007 |
| `guides/cache-system.md` | `cache/`, `REF-cache-*.md` | P1 | CB-008 |
| `guides/business-models.md` | `models/business/`, `REF-entity-lifecycle.md` | P1 | CB-009 |
| `guides/dataframes.md` | `dataframes/`, `routes/dataframes.py` | P1 | CB-010 |
| `guides/automation-pipelines.md` | `automation/`, pipeline/seeding guides | P2 | CB-011 |
| `guides/webhooks.md` | `routes/webhooks.py`, `automation/events/` | P2 | CB-012 |
| `api-reference/README.md` | `api/main.py`, route docstrings | P0 | CB-013 |
| `api-reference/openapi.yaml` | FastAPI auto-generation + curation | P0 | CB-014 |
| `sdk-reference/client.md` | `client.py` docstrings | P1 | CB-015 |
| `sdk-reference/resource-clients.md` | `clients/*.py` docstrings | P1 | CB-016 |
| `sdk-reference/models.md` | `models/*.py` | P1 | CB-017 |
| `sdk-reference/business-models.md` | `models/business/*.py` | P1 | CB-018 |
| `sdk-reference/persistence.md` | `persistence/session.py`, `persistence/actions.py` | P1 | CB-019 |
| `sdk-reference/configuration.md` | `config.py`, `settings.py` | P2 | CB-020 |
| `sdk-reference/exceptions.md` | `exceptions.py` | P2 | CB-021 |
| `sdk-reference/protocols.md` | `protocols/*.py` | P2 | CB-022 |
| `examples/README.md` | N/A | P0 | CB-023 |
| `examples/01-read-tasks.py` | `guides/quickstart.md` code | P0 | CB-024 |
| `examples/02-batch-update.py` | `guides/workflows.md` Recipe 1 | P0 | CB-025 |
| `examples/03-create-with-subtasks.py` | `guides/workflows.md` Recipe 3 | P1 | CB-026 |
| `examples/04-entity-resolution.py` | `routes/resolver.py` docstrings | P1 | CB-027 |
| `examples/05-entity-write.py` | `routes/entity_write.py` | P0 | CB-028 |
| `examples/06-query-entities.py` | `routes/query.py`, `query/engine.py` | P1 | CB-029 |
| `examples/07-lifecycle-transition.py` | `lifecycle/engine.py` | P2 | CB-030 |
| `examples/08-dataframe-export.py` | `routes/dataframes.py` | P2 | CB-031 |
| `examples/09-cache-warming.py` | `cache/`, admin routes | P2 | CB-032 |
| `examples/10-webhook-handler.py` | `routes/webhooks.py` | P2 | CB-033 |
| `runbooks/RUNBOOK-rate-limiting.md` | `transport/`, `config.py` | P2 | CB-034 |
| `INDEX.md` (rewrite) | All new docs | P0 | CB-035 |

### 3.3 Archive Actions

Move these to `.archive/2025-12-ia/`:
- `CONTENT-BRIEFS-2025-12-24.md`
- `CONTENT-INVENTORY.md`
- `DOC-AUDIT-REPORT-2025-12-24.md`
- `DOC-AUDIT-SUMMARY-2025-12-24.md`
- `IA-HANDOFF-SUMMARY-2025-12-24.md`
- `INFORMATION-ARCHITECTURE-SPEC-2025-12-24.md`
- `MIGRATION-PLAN-2025-12-24.md`
- `PHASE-7-PATTERN-EXTRACTION-VERIFICATION.md`
- `VALIDATION-REPORT-DOC-REFACTOR.md`
- `VALIDATION-REPORT-Q4-CLEANUP-2025-12-24.md`

These are artifacts from the 2025-12-24 IA pass. Their work is done and their guidance is superseded by this document.

### 3.4 Execution Sequence

```
Phase 1 (P0): Foundation                    [Est: 2 days]
  1. Create directory structure
  2. getting-started/ (3 docs)
  3. examples/README.md + 01, 02, 05
  4. api-reference/README.md
  5. api-reference/openapi.yaml (generate + curate)
  6. INDEX.md rewrite

Phase 2 (P0-P1): Entity Write + Resolution  [Est: 2 days]
  7. guides/entity-write.md
  8. guides/entity-resolution.md
  9. api-reference/endpoints/ (entity-write, resolver)
  10. examples/04-entity-resolution.py

Phase 3 (P1): Core Guides                   [Est: 3 days]
  11. guides/entity-query.md
  12. guides/lifecycle-engine.md
  13. guides/cache-system.md
  14. guides/business-models.md
  15. guides/dataframes.md
  16. sdk-reference/ (client, resource-clients, models, business-models, persistence)

Phase 4 (P1-P2): Completeness               [Est: 2 days]
  17. guides/automation-pipelines.md
  18. guides/webhooks.md
  19. sdk-reference/ (configuration, exceptions, protocols)
  20. Remaining examples (03, 06-10)
  21. runbooks/RUNBOOK-rate-limiting.md

Phase 5: Cleanup                             [Est: 1 day]
  22. Archive 2025-12-24 IA artifacts
  23. Consolidate guides/workflows.md + patterns.md into new structure
  24. Update all cross-references
  25. Verify no broken links
```

---

## 4. Content Briefs

### CB-001: Architecture Overview

- **File path**: `docs/getting-started/overview.md`
- **Title**: System Architecture Overview
- **Audience**: New developers, stakeholders, anyone asking "what is this?"
- **Purpose**: Answer "What does autom8y-asana do and how do its components fit together?"
- **Sections**:
  1. What is autom8y-asana (2-paragraph summary)
  2. Component map diagram (ASCII or Mermaid): FastAPI service, SDK client, Asana API, cache layer, lifecycle engine, resolution, automation
  3. How requests flow: External caller -> FastAPI routes -> Services -> SDK clients -> Asana HTTP -> Asana API
  4. Key subsystems (one paragraph each): Entity Resolution, Entity Write, Query Engine, Lifecycle Engine, Cache, Automation, DataFrames
  5. Repository layout: `src/autom8_asana/` directory map with one-line descriptions
  6. Related reading: links to each subsystem's guide
- **Source material**: `src/autom8_asana/__init__.py` (public API surface), `api/routes/__init__.py` (route map), `architecture/DOC-ARCHITECTURE.md`
- **Dependencies**: None (this is the root document)
- **Priority**: P0
- **Estimated scope**: Large (6+ sections)

### CB-002: Installation and Setup

- **File path**: `docs/getting-started/installation.md`
- **Title**: Installation and Setup
- **Audience**: New developers setting up their environment
- **Purpose**: Answer "How do I install this and make my first API call?"
- **Sections**:
  1. Prerequisites (Python 3.10+, Asana PAT, workspace GID)
  2. Installation (`pip install autom8y-asana`)
  3. Environment variables (ASANA_PAT, ASANA_WORKSPACE_GID, optional config vars)
  4. Verify connectivity (minimal script that fetches one task)
  5. Running the API server (uvicorn command, health check)
  6. Configuration reference (link to `sdk-reference/configuration.md`)
  7. Troubleshooting (common errors: auth failures, workspace ambiguity, rate limits)
- **Source material**: `guides/quickstart.md` (consolidate), `client.py` constructor docstrings, `config.py`
- **Dependencies**: None
- **Priority**: P0
- **Estimated scope**: Medium (5 sections)

### CB-003: Core Concepts

- **File path**: `docs/getting-started/core-concepts.md`
- **Title**: Core Concepts
- **Audience**: Anyone needing the mental model before using the SDK
- **Purpose**: Answer "What are the fundamental abstractions I need to understand?"
- **Sections**:
  1. The entity hierarchy: Business > UnitHolder > Unit > OfferHolder > Offer (with diagram)
  2. SaveSession pattern: track, modify, commit (with code snippet)
  3. Four operation types: Read, Create, Update, Relationships
  4. Sync vs async: every method has `method()` and `method_async()` variants
  5. Custom fields: descriptors, typed access, Asana field mapping
  6. Authentication modes: PAT (direct), S2S JWT (service-to-service)
  7. Glossary of key terms (GID, holder, hydration, detection, resolution)
- **Source material**: `guides/concepts.md` (consolidate), `reference/REF-entity-lifecycle.md`, `reference/REF-entity-type-table.md`
- **Dependencies**: None
- **Priority**: P0
- **Estimated scope**: Large (7 sections)

### CB-004: Entity Write Guide

- **File path**: `docs/guides/entity-write.md`
- **Title**: Writing Entity Fields
- **Audience**: API integrators, SDK consumers writing data back to Asana
- **Purpose**: Answer "How do I update entity fields through the API or SDK?"
- **Sections**:
  1. Overview: what the Entity Write API does (field resolution, type coercion, partial success)
  2. REST API usage: `PATCH /api/v1/entity/{entity_type}/{gid}` with full request/response examples
  3. SDK usage: `FieldWriteService.write_async()` direct usage
  4. Field name resolution: Python descriptor names vs Asana display names vs custom field GIDs
  5. List mode: `replace` vs `append` for multi-enum fields
  6. Error handling: per-field results, suggestions for misspelled fields
  7. Supported entity types and their writable fields
  8. Authentication: S2S JWT requirement, how to obtain service token
- **Source material**: `api/routes/entity_write.py` (full route), `services/field_write_service.py`, `resolution/field_resolver.py`, `docs/design/TDD-entity-write-api.md`
- **Dependencies**: `getting-started/core-concepts.md` (entity types), `guides/authentication.md`
- **Priority**: P0
- **Estimated scope**: Large (8 sections)

### CB-005: Entity Resolution Guide

- **File path**: `docs/guides/entity-resolution.md`
- **Title**: Entity Resolution
- **Audience**: API integrators resolving business identifiers to Asana GIDs
- **Purpose**: Answer "How do I find the Asana GID for a business entity given phone+vertical?"
- **Sections**:
  1. What is entity resolution: mapping business keys (phone, vertical) to Asana task GIDs
  2. REST API: `POST /v1/resolve/{entity_type}` with request/response examples
  3. Supported entity types and their resolution criteria
  4. Batch resolution: sending multiple criteria in one request
  5. Resolution strategies: how the system searches (index lookup, name matching, hierarchy traversal)
  6. Budget and timeouts: resolution budget concept, configuring limits
  7. Error handling: NOT_FOUND, AMBIGUOUS, resolution failures
  8. Caching behavior: how resolution results are cached
- **Source material**: `api/routes/resolver.py`, `api/routes/resolver_models.py`, `services/resolver.py`, `resolution/strategies.py`, `resolution/context.py`, `resolution/budget.py`
- **Dependencies**: `getting-started/core-concepts.md`, `guides/authentication.md`
- **Priority**: P1
- **Estimated scope**: Large (8 sections)

### CB-006: Entity Query Guide

- **File path**: `docs/guides/entity-query.md`
- **Title**: Querying Entity Data
- **Audience**: API integrators querying cached entity DataFrames
- **Purpose**: Answer "How do I query and filter entity data from the cache?"
- **Sections**:
  1. What the query system does: SQL-like filtering over cached entity DataFrames
  2. REST API v1 (legacy): `POST /v1/query/{entity_type}` flat equality filters
  3. REST API v2: `POST /v1/query-v2/{entity_type}/rows` composable predicate trees
  4. REST API v2 aggregation: `POST /v1/query-v2/{entity_type}/aggregate`
  5. Predicate syntax: operators (eq, ne, gt, lt, in, contains, regex), AND/OR composition
  6. Section filtering: filtering by Asana section
  7. Field selection: choosing which columns to return
  8. Pagination and limits
  9. Error handling: unknown fields, coercion errors, query complexity limits
- **Source material**: `api/routes/query.py`, `api/routes/query_v2.py`, `query/engine.py`, `query/compiler.py`, `query/models.py`, `services/query_service.py`
- **Dependencies**: `getting-started/core-concepts.md`, `guides/cache-system.md`
- **Priority**: P1
- **Estimated scope**: Large (9 sections)

### CB-007: Lifecycle Engine Guide

- **File path**: `docs/guides/lifecycle-engine.md`
- **Title**: Lifecycle Engine
- **Audience**: SDK consumers managing entity lifecycle transitions
- **Purpose**: Answer "How do entities move through lifecycle stages and how do I trigger transitions?"
- **Sections**:
  1. What the lifecycle engine does: manages creation, stage transitions, completion, reopening
  2. Lifecycle stages and their meanings (from `config/lifecycle_stages.yaml`)
  3. Entity creation flow: how new entities are seeded with init actions
  4. Stage transitions: which transitions are valid, what happens during transition
  5. Init action handlers: 6 handler types and what they do
  6. Configuration: `lifecycle/config.py`, stage definitions, action configuration
  7. Wiring: how the engine connects to the automation pipeline
  8. SDK usage: `LifecycleEngine` class, triggering transitions programmatically
- **Source material**: `lifecycle/engine.py`, `lifecycle/config.py`, `lifecycle/creation.py`, `lifecycle/init_actions.py`, `lifecycle/completion.py`, `lifecycle/reopen.py`, `lifecycle/wiring.py`, `docs/design/TDD-lifecycle-engine.md`
- **Dependencies**: `getting-started/core-concepts.md`, `guides/business-models.md`
- **Priority**: P1
- **Estimated scope**: Large (8 sections)

### CB-008: Cache System Guide

- **File path**: `docs/guides/cache-system.md`
- **Title**: Cache System
- **Audience**: Operators, SDK consumers needing to understand caching behavior
- **Purpose**: Answer "How does caching work, how do I warm it, and how do I troubleshoot staleness?"
- **Sections**:
  1. Cache architecture overview: tiered providers, backends
  2. Cache tiers: in-memory, Redis, S3 (when each is used)
  3. Cache warming: how to trigger, what gets cached, warm results
  4. TTL and staleness: detection, progressive TTL, LKG (last-known-good) freshness
  5. Invalidation: mutation invalidator, manual invalidation via admin API
  6. DataFrame cache: how entity DataFrames are cached and rebuilt
  7. Configuration: cache settings, provider selection, TTL tuning
  8. Admin API: `POST /v1/admin/cache/refresh` usage
  9. Troubleshooting: common staleness issues, cache miss diagnosis
- **Source material**: `cache/` module, `api/routes/admin.py`, `reference/REF-cache-architecture.md`, `reference/REF-cache-invalidation.md`, `reference/REF-cache-patterns.md`, `reference/REF-cache-staleness-detection.md`, `reference/REF-cache-ttl-strategy.md`, `runbooks/RUNBOOK-cache-troubleshooting.md`
- **Dependencies**: `getting-started/core-concepts.md`
- **Priority**: P1
- **Estimated scope**: Large (9 sections)

### CB-009: Business Models Guide

- **File path**: `docs/guides/business-models.md`
- **Title**: Business Entity Models
- **Audience**: SDK consumers working with the business domain layer
- **Purpose**: Answer "How do I work with Business, Unit, Offer, and other domain entities?"
- **Sections**:
  1. Entity hierarchy diagram: Business > ContactHolder/UnitHolder/LocationHolder > Contact/Unit > OfferHolder > Offer
  2. Holder pattern: what holders are, how they contain children
  3. Hydration: lazy loading, `hydrate_async()`, selective hydration
  4. Detection: how entity types are detected from raw Asana tasks (5-tier system)
  5. Custom field descriptors: defining typed access to Asana custom fields
  6. Navigation: traversing the hierarchy (parent, children, siblings)
  7. Seeding: `BusinessSeeder`, creating new entity hierarchies
  8. Code examples for common operations
- **Source material**: `models/business/*.py`, `models/business/detection/`, `models/business/matching/`, `reference/REF-entity-lifecycle.md`, `reference/REF-asana-hierarchy.md`
- **Dependencies**: `getting-started/core-concepts.md`
- **Priority**: P1
- **Estimated scope**: Large (8 sections)

### CB-010: DataFrames Guide

- **File path**: `docs/guides/dataframes.md`
- **Title**: DataFrame Layer
- **Audience**: SDK consumers building structured data views from Asana
- **Purpose**: Answer "How do I extract structured tabular data from Asana projects?"
- **Sections**:
  1. What DataFrames provide: Polars-based structured views of Asana task data
  2. Schemas: `DataFrameSchema`, built-in schemas (BASE, UNIT, CONTACT), custom schemas
  3. Builders: `DataFrameBuilder`, `SectionDataFrameBuilder`, `ProgressiveProjectBuilder`
  4. Extractors: `BaseExtractor`, `UnitExtractor`, `ContactExtractor`, custom extractors
  5. Custom field resolution: `DefaultCustomFieldResolver` for dynamic field extraction
  6. REST API: `GET /api/v1/dataframes/project/{gid}`, `GET /api/v1/dataframes/section/{gid}`
  7. Content negotiation: JSON vs Polars format (`Accept` header)
  8. Cache integration: `DataFrameCacheIntegration`, `CachedRow`
- **Source material**: `dataframes/` module, `api/routes/dataframes.py`, `__init__.py` DataFrame exports
- **Dependencies**: `getting-started/core-concepts.md`
- **Priority**: P1
- **Estimated scope**: Large (8 sections)

### CB-011: Automation Pipelines Guide

- **File path**: `docs/guides/automation-pipelines.md`
- **Title**: Automation Pipelines
- **Audience**: SDK consumers and operators configuring automated workflows
- **Purpose**: Answer "How do I set up automated processing of Asana entities?"
- **Sections**:
  1. Automation architecture: pipeline, engine, workflows
  2. Pipeline: `AutomationPipeline`, stages, execution flow
  3. Seeding: `AutomationSeeder`, populating new entities with defaults
  4. Built-in workflows: conversation audit, pipeline transition
  5. Configuration: automation config, template system
  6. Events: event-driven triggers, polling
  7. Integration: how automation connects to lifecycle engine and webhooks
- **Source material**: `automation/pipeline.py`, `automation/seeding.py`, `automation/engine.py`, `automation/workflows/`, `automation/events/`, `guides/pipeline-automation-setup.md`, `guides/GUIDE-businessseeder-v2.md`, `runbooks/RUNBOOK-pipeline-automation.md`
- **Dependencies**: `guides/lifecycle-engine.md`, `guides/business-models.md`
- **Priority**: P2
- **Estimated scope**: Large (7 sections)

### CB-012: Webhooks Guide

- **File path**: `docs/guides/webhooks.md`
- **Title**: Webhook Integration
- **Audience**: API integrators receiving events from Asana
- **Purpose**: Answer "How do I receive and process events from Asana via webhooks?"
- **Sections**:
  1. Overview: inbound webhook architecture
  2. Endpoint: `POST /api/v1/webhooks/inbound` with request/response
  3. Authentication: token-based query parameter
  4. V1: Asana Rules action payloads (full task JSON)
  5. V2 extension: Asana Webhooks API (handshake, HMAC)
  6. Dispatch protocol: how events route to automation engine
  7. Loop prevention: handling write-triggered webhook loops
  8. Cache invalidation: how webhook events trigger cache updates
- **Source material**: `api/routes/webhooks.py`, `automation/events/`
- **Dependencies**: `getting-started/core-concepts.md`, `guides/automation-pipelines.md`
- **Priority**: P2
- **Estimated scope**: Medium (8 sections, each small)

### CB-013: API Reference README

- **File path**: `docs/api-reference/README.md`
- **Title**: REST API Reference
- **Audience**: API integrators consuming the HTTP endpoints
- **Purpose**: Answer "How do I authenticate, paginate, and handle errors for the REST API?"
- **Sections**:
  1. Base URL and versioning (`/api/v1/` prefix, exceptions for `/v1/resolve`, `/v1/query`, `/v1/admin`)
  2. Authentication: PAT bearer token (public routes) vs S2S JWT (internal routes)
  3. Request/response format: JSON, content negotiation
  4. Pagination: limit/offset parameters, `PaginationMeta` response
  5. Error handling: HTTP status codes, error response body format
  6. Rate limiting: SlowAPI configuration, 429 response handling
  7. Health checks: `/health`, `/health/ready`, `/health/s2s`
  8. Endpoint index: table linking to each endpoint group doc
  9. OpenAPI spec: link to `openapi.yaml`, instructions for Postman/Insomnia import
- **Source material**: `api/main.py`, `api/models.py`, `api/errors.py`, `api/middleware.py`, `api/rate_limit.py`, `api/routes/health.py`
- **Dependencies**: None
- **Priority**: P0
- **Estimated scope**: Large (9 sections)

### CB-014: OpenAPI Specification

- **File path**: `docs/api-reference/openapi.yaml`
- **Title**: OpenAPI 3.1 Specification
- **Audience**: API integrators, tooling (Postman, Insomnia, code generators)
- **Purpose**: Machine-readable API contract for all REST endpoints
- **Generation strategy**: See Section 5 below
- **Priority**: P0
- **Estimated scope**: Large (generated, then curated)

### CB-015: AsanaClient Reference

- **File path**: `docs/sdk-reference/client.md`
- **Title**: AsanaClient Reference
- **Audience**: SDK consumers initializing and configuring the client
- **Purpose**: Answer "How do I create and configure an AsanaClient instance?"
- **Sections**:
  1. Constructor: all parameters with types and defaults
  2. Provider resolution order: auth, cache, log, observability
  3. Context manager usage (recommended pattern)
  4. Resource client access: `.tasks`, `.projects`, `.sections`, etc.
  5. Workspace resolution: explicit > env var > auto-detect
  6. Advanced: custom providers, observability hooks
  7. Thread safety and concurrency notes
- **Source material**: `client.py` (full class)
- **Dependencies**: `getting-started/installation.md`
- **Priority**: P1
- **Estimated scope**: Medium (7 sections, mostly extracted from docstrings)

### CB-016: Resource Clients Reference

- **File path**: `docs/sdk-reference/resource-clients.md`
- **Title**: Resource Clients Reference
- **Audience**: SDK consumers calling Asana API operations
- **Purpose**: Answer "What methods are available on each resource client?"
- **Sections**:
  1. Client pattern: sync (`method()`) and async (`method_async()`) variants
  2. TasksClient: get, list, create, update, delete, subtasks, tags, projects, sections
  3. ProjectsClient: get, list, create, update, delete, sections, members
  4. SectionsClient: get, create, update, delete, add/remove tasks, reorder
  5. UsersClient: get, list, me
  6. WorkspacesClient: get, list
  7. AttachmentsClient, CustomFieldsClient, GoalsClient, PortfoliosClient, StoriesClient, TagsClient, TeamsClient, WebhooksClient (summary table for each)
  8. Pagination: `PageIterator` pattern
  9. Error handling: per-method exceptions
- **Source material**: `clients/*.py` (14 client files)
- **Dependencies**: `sdk-reference/client.md`
- **Priority**: P1
- **Estimated scope**: Large (9 sections, repetitive structure)

### CB-017: Models Reference

- **File path**: `docs/sdk-reference/models.md`
- **Title**: Models Reference
- **Audience**: SDK consumers working with Asana data objects
- **Purpose**: Answer "What fields and methods are on each model class?"
- **Sections**:
  1. Model inheritance: `AsanaResource` > specific types
  2. Task: fields, custom field access, computed properties
  3. Project: fields, section relationship
  4. Section: fields, task membership
  5. User, Workspace, Tag, Story, Attachment, Portfolio, Goal, Team, Webhook
  6. CustomField, CustomFieldEnumOption, CustomFieldSetting
  7. Common patterns: `.gid`, `.name`, `.resource_type`, Pydantic serialization
- **Source material**: `models/*.py`
- **Dependencies**: `getting-started/core-concepts.md`
- **Priority**: P1
- **Estimated scope**: Large (7 sections)

### CB-018: Business Models Reference

- **File path**: `docs/sdk-reference/business-models.md`
- **Title**: Business Models Reference
- **Audience**: SDK consumers working with domain entities
- **Purpose**: Answer "What fields, methods, and class variables define each business model?"
- **Sections**:
  1. Class hierarchy: `Task` > `Business`, `Unit`, `Offer`, `Contact`, `AssetEdit`
  2. Base class: `BusinessEntityBase` fields and methods
  3. Business: HOLDER_KEY_MAP, custom fields, holder access
  4. Unit: holder factory, offer relationship
  5. Offer: field descriptors, parent unit access
  6. Contact: fields, business relationship
  7. Holder classes: `UnitHolder`, `OfferHolder`, `ContactHolder` -- child management
  8. Detection registration: PROJECT_GID, HOLDER_KEY_MAP, detection tiers
  9. Descriptors: how custom field descriptors provide typed property access
- **Source material**: `models/business/*.py`, `models/business/descriptors.py`, `models/business/fields.py`, `models/business/registry.py`
- **Dependencies**: `guides/business-models.md`
- **Priority**: P1
- **Estimated scope**: Large (9 sections)

### CB-019: Persistence Reference

- **File path**: `docs/sdk-reference/persistence.md`
- **Title**: Persistence (SaveSession) Reference
- **Audience**: SDK consumers performing write operations
- **Purpose**: Answer "What are all the SaveSession methods, events, and options?"
- **Sections**:
  1. SaveSession: constructor, context manager, `track()`, `commit_async()`
  2. Actions: `add_tag`, `remove_tag`, `add_to_project`, `remove_from_project`, etc.
  3. Commit result: `SaveResult`, per-entity status, partial failure handling
  4. Events: `SaveSessionEvent` types, event subscription
  5. Pipeline: action ordering, dependency graph, cascade
  6. Healing: self-healing on failed commits
  7. Exceptions: `GidValidationError`, `SaveSessionError`
- **Source material**: `persistence/session.py`, `persistence/actions.py`, `persistence/events.py`, `persistence/pipeline.py`, `persistence/healing.py`, `persistence/exceptions.py`
- **Dependencies**: `guides/save-session.md`
- **Priority**: P1
- **Estimated scope**: Large (7 sections)

### CB-020: Configuration Reference

- **File path**: `docs/sdk-reference/configuration.md`
- **Title**: Configuration Reference
- **Audience**: SDK consumers and operators tuning behavior
- **Purpose**: Answer "What configuration options exist and what are their defaults?"
- **Sections**:
  1. `AsanaConfig`: all fields with defaults
  2. `RateLimitConfig`: rate limiting parameters
  3. `RetryConfig`: retry behavior
  4. `ConcurrencyConfig`: concurrency limits
  5. `TimeoutConfig`: timeout values
  6. `ConnectionPoolConfig`: connection pool sizing
  7. Environment variables: `ASANA_PAT`, `ASANA_WORKSPACE_GID`, all settings from `settings.py`
  8. Cache configuration: provider selection, TTL, backend config
- **Source material**: `config.py`, `settings.py`, `cache/` config files
- **Dependencies**: `getting-started/installation.md`
- **Priority**: P2
- **Estimated scope**: Medium (8 sections, mostly tabular)

### CB-021: Exceptions Reference

- **File path**: `docs/sdk-reference/exceptions.md`
- **Title**: Exceptions Reference
- **Audience**: SDK consumers handling errors
- **Purpose**: Answer "What exceptions can be raised and when?"
- **Sections**:
  1. Exception hierarchy diagram
  2. Base: `AsanaError`
  3. HTTP errors: `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `RateLimitError`, `ServerError`, `GoneError`, `TimeoutError`
  4. Client errors: `ConfigurationError`, `SyncInAsyncContextError`, `HydrationError`
  5. Persistence errors: `GidValidationError`, `SaveSessionError`
  6. Service errors: `ServiceError` hierarchy from `services/errors.py`
  7. Transport error tuples: `CACHE_TRANSIENT_ERRORS`, `S3_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`
  8. When each exception is raised (table mapping exception to trigger scenario)
- **Source material**: `exceptions.py`, `persistence/exceptions.py`, `services/errors.py`, `core/exceptions.py`
- **Dependencies**: None
- **Priority**: P2
- **Estimated scope**: Medium (8 sections, mostly tabular)

### CB-022: Protocols Reference

- **File path**: `docs/sdk-reference/protocols.md`
- **Title**: Protocols Reference
- **Audience**: SDK consumers implementing custom providers
- **Purpose**: Answer "How do I implement custom auth, cache, log, or observability providers?"
- **Sections**:
  1. What protocols are: Python Protocol classes for dependency injection
  2. `AuthProvider`: `get_token()` contract, built-in implementations (EnvAuthProvider, SecretsManagerAuthProvider)
  3. `CacheProvider`: get/set/delete contract, built-in implementations
  4. `LogProvider`: logging contract
  5. `ObservabilityHook`: metrics/tracing contract
  6. `ItemLoader`: pagination contract
  7. Implementation examples for each protocol
- **Source material**: `protocols/*.py`, `_defaults/`
- **Dependencies**: `sdk-reference/client.md`
- **Priority**: P2
- **Estimated scope**: Medium (7 sections)

### CB-023: Examples README

- **File path**: `docs/examples/README.md`
- **Title**: Runnable Examples
- **Audience**: All developers
- **Purpose**: Index of examples with prerequisites and running instructions
- **Sections**:
  1. Prerequisites: Python 3.10+, installed SDK, env vars set
  2. How to run: `python docs/examples/01-read-tasks.py`
  3. Example index: table with filename, description, complexity level
  4. Conventions: each script is self-contained, uses `asyncio.run()`, includes inline comments
- **Source material**: N/A (new)
- **Dependencies**: `getting-started/installation.md`
- **Priority**: P0
- **Estimated scope**: Small (4 sections)

### CB-024 through CB-033: Example Scripts

Each example script follows this template:

```python
#!/usr/bin/env python3
"""<TITLE>

<One-paragraph description of what this example demonstrates.>

Prerequisites:
    pip install autom8y-asana
    export ASANA_PAT="your_token"
    export ASANA_WORKSPACE_GID="your_workspace_gid"

Related docs:
    - docs/guides/<relevant-guide>.md
    - docs/sdk-reference/<relevant-reference>.md
"""

import asyncio
from autom8_asana import AsanaClient

async def main():
    # ... example code with inline comments explaining each step ...
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

| Brief ID | File | Title | Source Material | Priority |
|----------|------|-------|-----------------|----------|
| CB-024 | `examples/01-read-tasks.py` | Read Tasks | `guides/quickstart.md` Step 2 | P0 |
| CB-025 | `examples/02-batch-update.py` | Batch Update with SaveSession | `guides/workflows.md` Recipe 1 | P0 |
| CB-026 | `examples/03-create-with-subtasks.py` | Create Task with Subtasks | `guides/workflows.md` Recipe 3 | P1 |
| CB-027 | `examples/04-entity-resolution.py` | Resolve Entities | `routes/resolver.py` docstrings | P1 |
| CB-028 | `examples/05-entity-write.py` | Write Entity Fields | `routes/entity_write.py` | P0 |
| CB-029 | `examples/06-query-entities.py` | Query Cached Entities | `routes/query.py` | P1 |
| CB-030 | `examples/07-lifecycle-transition.py` | Lifecycle Stage Transition | `lifecycle/engine.py` | P2 |
| CB-031 | `examples/08-dataframe-export.py` | Export DataFrames | `routes/dataframes.py` | P2 |
| CB-032 | `examples/09-cache-warming.py` | Cache Warm and Inspect | `routes/admin.py` | P2 |
| CB-033 | `examples/10-webhook-handler.py` | Webhook Event Handler | `routes/webhooks.py` | P2 |

### CB-034: Rate Limiting Runbook

- **File path**: `docs/runbooks/RUNBOOK-rate-limiting.md`
- **Title**: Rate Limiting Troubleshooting
- **Audience**: Operators debugging 429 errors
- **Purpose**: Answer "Why am I getting rate limited and how do I fix it?"
- **Sections**:
  1. Symptoms: HTTP 429, `RateLimitError` in logs
  2. Asana rate limits: per-user, per-app limits
  3. SDK rate limiter: `TokenBucketRateLimiter`, configuration
  4. API server rate limiter: SlowAPI configuration
  5. Diagnosis: checking rate limiter metrics, Asana response headers
  6. Resolution: tuning `RateLimitConfig`, adjusting concurrency, circuit breaker
  7. Hierarchy warming backpressure: large traversal rate limiting
- **Source material**: `transport/asana_http.py`, `config.py` RateLimitConfig, `api/rate_limit.py`, `spikes/SPIKE-hierarchy-warming-429-backpressure.md`
- **Dependencies**: `guides/cache-system.md`
- **Priority**: P2
- **Estimated scope**: Medium (7 sections)

### CB-035: INDEX.md Rewrite

- **File path**: `docs/INDEX.md`
- **Title**: Documentation Index
- **Audience**: Everyone
- **Purpose**: Single entry point for all documentation with 4 navigation paths
- **Sections**:
  1. "What do you need?" quick navigation (4 entry points: Learn, Build, Operate, Decide)
  2. Getting Started: links to overview, installation, core-concepts
  3. Guides: table of all guides with one-line descriptions
  4. API Reference: link to README, OpenAPI spec
  5. SDK Reference: table of all class reference docs
  6. Examples: link to examples/README.md
  7. Runbooks: table of all runbooks
  8. Internal Docs: links to PRDs, TDDs, ADRs for contributors
- **Source material**: All new docs
- **Dependencies**: All other docs (create last)
- **Priority**: P0 (but executed at end of Phase 1)
- **Estimated scope**: Medium (8 sections, all links)

---

## 5. OpenAPI Specification Plan

### 5.1 Generation Strategy

**Approach: Generate from FastAPI, then curate.**

FastAPI automatically generates an OpenAPI schema from route decorators, Pydantic models, and docstrings. The generation captures route paths, methods, request/response models, and tags. Manual curation adds descriptions, examples, and grouping polish.

**Steps:**

1. **Generate**: Run the FastAPI app in debug mode and fetch `/openapi.json`
   ```bash
   # Start the server with debug mode
   DEBUG=true uvicorn autom8_asana.api.main:create_app --factory --port 8000

   # Fetch the spec
   curl http://localhost:8000/openapi.json | python -m json.tool > docs/api-reference/openapi.json

   # Convert to YAML for readability
   python -c "import json, yaml; print(yaml.dump(json.load(open('docs/api-reference/openapi.json')), default_flow_style=False))" > docs/api-reference/openapi.yaml
   ```

2. **Curate**: Edit the generated spec to:
   - Add operation-level descriptions (from route docstrings)
   - Add request/response examples (from route test fixtures)
   - Improve tag descriptions
   - Add server URLs (local, staging, production)
   - Add security scheme definitions (PAT Bearer, S2S JWT)

3. **Validate**: Use `openapi-spec-validator` or Redocly CLI
   ```bash
   pip install openapi-spec-validator
   python -c "from openapi_spec_validator import validate; validate(open('docs/api-reference/openapi.yaml').read())"
   ```

### 5.2 File Location

- **Primary**: `docs/api-reference/openapi.yaml` (human-readable, version-controlled)
- **Generated**: `docs/api-reference/openapi.json` (machine-readable, gitignored after initial commit)

### 5.3 Tag Grouping Strategy

Group endpoints by functional domain, matching the router `tags` already defined in source:

| Tag | Routes | Auth | Description |
|-----|--------|------|-------------|
| `health` | `/health`, `/health/ready`, `/health/s2s` | None | Service health and readiness |
| `tasks` | `/api/v1/tasks/*` | PAT | Asana task CRUD operations |
| `projects` | `/api/v1/projects/*` | PAT | Asana project CRUD + sections/members |
| `sections` | `/api/v1/sections/*` | PAT | Asana section CRUD + task ordering |
| `users` | `/api/v1/users/*` | PAT | Asana user lookup |
| `workspaces` | `/api/v1/workspaces/*` | PAT | Asana workspace listing |
| `dataframes` | `/api/v1/dataframes/*` | PAT | Structured data views (project/section) |
| `webhooks` | `/api/v1/webhooks/*` | Token | Inbound event processing |
| `entity-write` | `/api/v1/entity/*` | S2S JWT | Field write operations |
| `resolver` | `/v1/resolve/*` | S2S JWT | Entity GID resolution |
| `query` | `/v1/query/*` | S2S JWT | Entity query and aggregation |
| `query-v2` | `/v1/query-v2/*` | S2S JWT | Composable predicate queries |
| `admin` | `/v1/admin/*` | S2S JWT | Cache management operations |
| `internal` | `/api/v1/internal/*` | S2S JWT | Service-to-service operations |

**Total: 14 tag groups covering approximately 47 endpoints.**

### 5.4 Authentication Schemes

Define two security schemes in the OpenAPI spec:

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      description: >
        Asana Personal Access Token (PAT). Used for public-facing
        endpoints (tasks, projects, sections, users, workspaces, dataframes).
    serviceAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: >
        Service-to-service JWT token. Used for internal endpoints
        (entity-write, resolver, query, admin). Issued by autom8 auth service.
```

### 5.5 Maintenance

The OpenAPI spec should be regenerated and curated whenever:
- New routes are added
- Request/response models change
- Authentication requirements change

Add a CI check that validates the spec file:
```yaml
# In .github/workflows/test.yml
- name: Validate OpenAPI spec
  run: |
    pip install openapi-spec-validator
    python -m openapi_spec_validator docs/api-reference/openapi.yaml
```

---

## 6. Examples Architecture

### 6.1 Location

All runnable scripts live in `docs/examples/`. This keeps examples adjacent to the docs they illustrate, rather than buried in `tests/` or a separate `examples/` directory at the repo root.

### 6.2 Naming Convention

`NN-kebab-description.py` where NN is a two-digit sequence number reflecting recommended reading order.

- `01-09`: Foundation (read, write, CRUD)
- `10-19`: (reserved for future SDK examples)
- `20-29`: (reserved for future API examples)

### 6.3 Script Conventions

Every example script follows these rules:

1. **Self-contained**: No imports from other example files
2. **Async-first**: Uses `async def main()` + `asyncio.run(main())`
3. **Env-var driven**: Reads credentials from environment, never hardcoded
4. **Documented**: Module docstring with title, description, prerequisites, related docs
5. **Commented**: Inline comments explaining each step
6. **Error-handled**: Demonstrates proper error handling (try/except with specific exceptions)
7. **Runnable**: `python docs/examples/NN-name.py` works with valid credentials
8. **Output-oriented**: Prints clear output showing what happened

### 6.4 Scenario Coverage

| # | Script | Complexity | Demonstrates |
|---|--------|-----------|--------------|
| 01 | Read tasks | Beginner | Client init, async get, model fields |
| 02 | Batch update | Beginner | SaveSession, track, modify, commit |
| 03 | Create with subtasks | Intermediate | Hierarchy creation, parent-child relationships |
| 04 | Entity resolution | Intermediate | POST /v1/resolve, batch criteria, error handling |
| 05 | Entity write | Intermediate | PATCH /api/v1/entity, field name resolution, partial results |
| 06 | Query entities | Intermediate | POST /v1/query-v2, predicate trees, pagination |
| 07 | Lifecycle transition | Advanced | LifecycleEngine, stage transitions, init actions |
| 08 | DataFrame export | Intermediate | DataFrame builders, schemas, Polars output |
| 09 | Cache warming | Advanced | Admin API, cache state inspection, TTL behavior |
| 10 | Webhook handler | Advanced | Inbound webhook, task parsing, dispatch |

### 6.5 Testing Examples

Examples should be validated in CI (not for functional correctness, but for syntax):

```yaml
- name: Validate example syntax
  run: |
    python -m py_compile docs/examples/01-read-tasks.py
    python -m py_compile docs/examples/02-batch-update.py
    # ... etc
```

---

## 7. Cross-Reference Strategy

### 7.1 Link Conventions

- **Within consumer docs**: Relative paths (`../guides/entity-write.md`)
- **To reference docs**: Relative paths (`../reference/REF-cache-architecture.md`)
- **To source code**: Backtick with module path (`` `src/autom8_asana/services/field_write_service.py` ``)
- **To internal docs**: Relative paths with note: "For design rationale, see [TDD-entity-write-api](../design/TDD-entity-write-api.md)"

### 7.2 "See Also" Sections

Every guide and reference doc ends with a "See Also" section:

```markdown
## See Also

- [Entity Resolution Guide](entity-resolution.md) - Resolving entities before writing
- [REF-entity-lifecycle](../reference/REF-entity-lifecycle.md) - Entity lifecycle pattern details
- [Example: Write Entity Fields](../examples/05-entity-write.py) - Runnable example
- [TDD-entity-write-api](../design/TDD-entity-write-api.md) - Design rationale
```

### 7.3 Bidirectional Cross-References

| From | To | Link Text |
|------|----|-----------|
| `guides/entity-write.md` | `examples/05-entity-write.py` | "See runnable example" |
| `examples/05-entity-write.py` | `guides/entity-write.md` | "Related docs" (in docstring) |
| `guides/entity-write.md` | `api-reference/endpoints/entity-write.md` | "Full API reference" |
| `api-reference/endpoints/entity-write.md` | `guides/entity-write.md` | "Usage guide" |
| `guides/entity-write.md` | `design/TDD-entity-write-api.md` | "Design rationale" |

---

## 8. Contribution Guide Update

The existing `CONTRIBUTION-GUIDE.md` should be updated to include:

1. **Where to put new docs**: Decision tree for new document placement
2. **Template links**: Templates for each document type
3. **Frontmatter requirements**: Required fields per document type
4. **Cross-reference requirements**: Every new doc must have "See Also" section
5. **Example requirements**: New features should include an example script

Decision tree for new docs:

```
Is it about how to USE the system?
  Yes -> guides/
Is it about what the API looks like?
  Yes -> api-reference/
Is it about Python class interfaces?
  Yes -> sdk-reference/
Is it about fixing a production problem?
  Yes -> runbooks/
Is it a design decision?
  Yes -> decisions/ (ADR)
Is it a design specification?
  Yes -> design/ (TDD)
Is it a product requirement?
  Yes -> requirements/ (PRD)
Everything else -> ask before creating
```

---

## Handoff Checklist

- [x] Target taxonomy and directory structure specified (Section 1)
- [x] Migration plan complete with action per existing doc (Section 3)
- [x] Consolidation specs identify source/target pairs (Section 3.1)
- [x] Content briefs written for all identified gaps (Section 4, 35 briefs)
- [x] Naming conventions and metadata requirements documented (Section 1.2, 1.4)
- [x] Priority ordering established (P0/P1/P2 per brief)
- [x] Contribution guide update specified (Section 8)
- [x] Navigation design specified with entry points (Section 2)
- [x] OpenAPI spec plan documented (Section 5)
- [x] Examples architecture documented (Section 6)
- [x] Cross-reference strategy documented (Section 7)

**This specification is ready for Tech Writer execution.**
