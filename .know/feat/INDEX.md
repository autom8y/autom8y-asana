---
domain: feat/index
generated_at: "2026-05-08T00:00Z"
expires_after: "30d"
source_scope:
  - "./.know/architecture.md"
  - "./.know/api.md"
  - "./src/autom8_asana/**/*.py"
generator: theoros
source_hash: "8980bcd7"
prior_source_hash: "6b303485"
confidence: 0.93
format_version: "1.0"
update_mode: "incremental"
incremental_cycle: 2
max_incremental_cycles: 3
---

# Feature Census — autom8y-asana @ HEAD `8980bcd7`

**Census Date**: 2026-05-08
**Source Hash**: `8980bcd7`
**Prior Index Hash**: `6b303485` (2026-04-29)
**Commits Since Prior Index**: 20 commits (2026-04-29 → 2026-05-08; CI, tests, style, deps, docs — no new source files added to `src/autom8_asana/`)

**Summary Counts**: 41 features across 7 categories. 37 GENERATE, 4 SKIP.
- **Per category**: Core Platform 12 (9G/3S), Business Domain 10 (10G), Automation 5 (5G), User-Facing API 4 (4G), Infrastructure 7 (6G/1S), Services 1 (1G), Tooling 2 (2G)
- **Prior census**: 33 features (29 GENERATE, 4 SKIP)
- **Net new features**: +8 (gid-data-sync-pipeline, business-seeder, section-timeline, vertical-backfill, admin-cache-control, workflow-invoke-api, plus 2 from finer Core Platform decomposition)
- **Removed**: 0
- **Boundary corrections**: 1 (custom-field-descriptor-dsl subsumed into business-domain-model)

---

## Category: Core Platform

### sdk-client-facade

| Field | Value |
|-------|-------|
| Slug | `sdk-client-facade` |
| Name | AsanaClient SDK Facade |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/client.py` — `AsanaClient` class, primary SDK entry point
- `src/autom8_asana/__init__.py` — top-level public export
- `README.md` — Quick Start entry

**Rationale**: Primary user-facing SDK interface; 10+ dependent modules; multiple cross-cutting imports. Boundary verified unchanged. GENERATE.

---

### resource-clients

| Field | Value |
|-------|-------|
| Slug | `resource-clients` |
| Name | Asana Resource Clients |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.96 |

**Source Evidence**:
- `src/autom8_asana/clients/` — 18+ client files (tasks, projects, sections, users, workspaces, webhooks, goals, portfolios, tags, stories, attachments, teams, custom_fields, batch, name_resolver, task_operations, task_ttl, goal_followers, goal_relationships)
- `src/autom8_asana/clients/base.py` — `BaseClient` shared pattern

**Rationale**: 18 client files, user-facing REST API routes, shared base pattern. Boundary unchanged. GENERATE.

---

### http-transport

| Field | Value |
|-------|-------|
| Slug | `http-transport` |
| Name | Asana HTTP Transport Layer |
| Category | Core Platform |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/transport/asana_http.py` — `AsanaHttpClient`
- `src/autom8_asana/transport/adaptive_semaphore.py` — AIMD adaptive concurrency
- `src/autom8_asana/transport/config_translator.py`, `response_handler.py`, `sync.py`

**Rationale**: 5+ transport files, cross-cutting rate-limit/circuit-breaker/retry/AIMD semaphore; used by every resource client. GENERATE.

---

### asana-models

| Field | Value |
|-------|-------|
| Slug | `asana-models` |
| Name | Pydantic v2 Asana Resource Models |
| Category | Core Platform |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/models/` — 12+ model files (task.py, project.py, section.py, user.py, webhook.py, goal.py, portfolio.py, custom_field.py, tag.py, story.py, team.py, workspace.py)

**Rationale**: 12+ files, user-facing typed return values from every SDK call, shared `AsanaResource` base. GENERATE.

---

### save-session

| Field | Value |
|-------|-------|
| Slug | `save-session` |
| Name | SaveSession Unit of Work Pattern |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.98 |

**Source Evidence**:
- `src/autom8_asana/persistence/session.py` — `SaveSession` context manager
- `src/autom8_asana/persistence/` — 20 files

**Rationale**: 20 implementation files, 4/5-phase `SavePipeline` (Validate→Prepare→Execute→Actions→Confirm). GENERATE.

---

### cache-subsystem

| Field | Value |
|-------|-------|
| Slug | `cache-subsystem` |
| Name | Multi-Tier Intelligent Cache Subsystem |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.99 |

**Source Evidence**:
- `src/autom8_asana/cache/` — 52+ files across backends (memory, redis, s3), dataframe (build_coordinator, circuit_breaker, coalescer, warmer), integration (freshness_coordinator, staleness_coordinator, mutation_invalidator, hierarchy_warmer, autom8_adapter, upgrader), models, policies, providers

**Rationale**: 52+ files, largest single subsystem. Multiple backends, tiered caching, circuit breaker, coalescer, staleness detection, mutation invalidation. Note: `cache/integration/autom8_adapter.py` (466 LOC) + `upgrader.py` (211 LOC) = 677 LOC migration path subsumed here. GENERATE.

---

### dataframe-layer

| Field | Value |
|-------|-------|
| Slug | `dataframe-layer` |
| Name | Polars DataFrame Analytics Layer |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/dataframes/` — 45+ files across builders, schemas, extractors, models, resolver, views
- `src/autom8_asana/api/routes/dataframes.py` — user-facing `dataframes_router` endpoint

**Rationale**: 45+ source files, user-facing REST endpoint, Polars-based with multiple extractor strategies. GENERATE.

---

### query-engine

| Field | Value |
|-------|-------|
| Slug | `query-engine` |
| Name | DataFrame Query Engine with Compiled Predicates |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/query/` — 18 files (engine, compiler, fetcher, join, aggregator, temporal, timeline_provider, hierarchy, introspection, saved, formatters, guards, models, offline_provider, data_service_entities, errors, `__main__`)
- `src/autom8_asana/api/routes/query.py` — user-facing `/rows`, `/aggregate`, `/sections` endpoints
- `queries/` — 4 saved named queries (active_offers, mrr_by_vertical, offers_with_business, offers_with_spend)
- `query/models.py:54-56` — BETWEEN, DATE_GTE, DATE_LTE LIVE since Sprint-3

**Rationale**: 18 implementation files, S2S REST endpoints, compiled predicate trees, temporal queries, timeline queries, saved queries corpus, CLI interface. GENERATE.

---

### entity-registry

| Field | Value |
|-------|-------|
| Slug | `entity-registry` |
| Name | EntityRegistry (Descriptor-Driven Entity Metadata) |
| Category | Core Platform |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.92 |

**Source Evidence**:
- `src/autom8_asana/core/entity_registry.py` — `EntityDescriptor`, `EntityRegistry` singleton
- `src/autom8_asana/core/project_registry.py` — Project GID constants (9 pipeline projects)
- `src/autom8_asana/core/registry_validation.py` — cross-registry consistency validation

**Rationale**: 3 files imported by virtually every domain module. Singleton source of truth for entity configuration. GENERATE.

---

### batch-api-client

| Field | Value |
|-------|-------|
| Slug | `batch-api-client` |
| Name | Asana Batch API Client |
| Category | Core Platform |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.75 |

**Source Evidence**:
- `src/autom8_asana/batch/` — 2 files (client, models)

**Rationale**: 2 files, internal implementation detail of persistence layer, no direct user-facing surface. SKIP.

---

### search-service

| Field | Value |
|-------|-------|
| Slug | `search-service` |
| Name | Search Service over Cached DataFrames |
| Category | Core Platform |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.72 |

**Source Evidence**:
- `src/autom8_asana/search/` — 2 files (service, models)

**Rationale**: Thin service facade over query-engine. 2 files, no dedicated guide or ADR. SKIP.

---

### protocol-di-layer

| Field | Value |
|-------|-------|
| Slug | `protocol-di-layer` |
| Name | Protocol / Dependency Injection Layer |
| Category | Core Platform |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.85 |

**Source Evidence**:
- `src/autom8_asana/protocols/` — 8 files (auth, cache, dataframe_provider, insights, item_loader, log, metrics, observability)

**Rationale**: PEP 544 Protocol structural interfaces with no executable logic. Structural primitives, not a feature. SKIP.

---

## Category: Business Domain

### business-domain-model

| Field | Value |
|-------|-------|
| Slug | `business-domain-model` |
| Name | Business Domain Entity Model |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.98 |

**Source Evidence**:
- `src/autom8_asana/models/business/` — 60+ files (business, unit, contact, offer, process, location, hours, asset_edit, dna, descriptors, holder_factory, hydration, fields, mixins, activity, patterns, reconciliation, registry, resolution, seeder, section_timeline, matching/*, detection/*, contracts/)
- `src/autom8_asana/models/business/descriptors.py` — 740 LOC, 8 typed descriptor classes (`CustomFieldDescriptor[T]`, TextField, PhoneTextField, EnumField, MultiEnumField, NumberField, IntField, PeopleField, DateField) with `ParentRef[T]`, `HolderRef[T]`

**Rationale**: 60+ source files, the largest domain model package. Descriptor DSL (740 LOC) is subsumed here — it is the primary typed access layer for custom fields across all entity types. GENERATE.

[KNOW-CANDIDATE] Custom field descriptor DSL (740 LOC, `descriptors.py`) is not documented in existing `business-domain-model.md` — high-value addition to the per-feature knowledge file.

---

### entity-detection

| Field | Value |
|-------|-------|
| Slug | `entity-detection` |
| Name | Multi-Tier Entity Type Detection |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/models/business/detection/` — 8 files (facade, tier1, tier2, tier3, tier4, config, types + adversarial tests)

**Rationale**: 8 files, tiered detection system (tiers 1-4), cross-cutting concern. Boundary unchanged. GENERATE.

---

### fuzzy-entity-matching

| Field | Value |
|-------|-------|
| Slug | `fuzzy-entity-matching` |
| Name | Fuzzy Matching Engine for Entity Deduplication |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/models/business/matching/` — 6 files (engine, blocking, comparators, normalizers, models, config)
- `src/autom8_asana/api/routes/matching.py` — hidden `POST /v1/matching/query` endpoint
- `src/autom8_asana/services/matching_service.py` — orchestration service

**Rationale**: 6 implementation files + user-facing (hidden) REST endpoint + service. Blocking strategy, comparators, normalizers. GENERATE.

---

### entity-resolution

| Field | Value |
|-------|-------|
| Slug | `entity-resolution` |
| Name | Entity Resolution (Phone+Vertical to GID) |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.96 |

**Source Evidence**:
- `src/autom8_asana/resolution/` — 7 files (field_resolver, strategies, context, budget, result, selection, write_registry)
- `src/autom8_asana/api/routes/resolver.py` — `POST /v1/resolve/{type}` endpoint
- `src/autom8_asana/services/universal_strategy.py` — `UniversalResolutionStrategy` (`DynamicIndex`-backed)

**Rationale**: 8+ files, user-facing REST endpoint. Resolves phone+vertical pairs to Asana GIDs. GENERATE.

---

### lifecycle-engine

| Field | Value |
|-------|-------|
| Slug | `lifecycle-engine` |
| Name | Entity Lifecycle Pipeline (4-Phase Transition Engine) |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.98 |

**Source Evidence**:
- `src/autom8_asana/lifecycle/` — 17 files: engine, completion, creation, dispatch, init_actions, loop_detector, observation, observation_store, reopen, sections, seeding, webhook, webhook_dispatcher, wiring, config, `__init__`
- `config/lifecycle_stages.yaml` — pipeline DAG configuration

**Rationale**: 17 implementation files (current count; prior said 16), YAML-driven lifecycle DAG, 4-phase engine (Create→Configure→Actions→Wire). GENERATE.

---

### intake-pipeline

| Field | Value |
|-------|-------|
| Slug | `intake-pipeline` |
| Name | Intake Business Creation Pipeline |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/api/routes/intake_create.py` — `POST /v1/intake/business`, `POST /v1/intake/process`
- `src/autom8_asana/api/routes/intake_resolve.py` — intake resolution routes
- `src/autom8_asana/api/routes/intake_custom_fields.py` — custom field write routes
- `src/autom8_asana/services/intake_create_service.py`, `intake_resolve_service.py`, `intake_custom_field_service.py` — services

**Rationale**: 20+ files across 3 dedicated routes + 3 dedicated services. S2S JWT auth. GENERATE.

---

### payment-reconciliation

| Field | Value |
|-------|-------|
| Slug | `payment-reconciliation` |
| Name | Payment Reconciliation Processing (Excel Output) |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/reconciliation/` — 5 files (engine, executor, processor, report, section_registry)
- `src/autom8_asana/lambda_handlers/payment_reconciliation.py`, `reconciliation_runner.py`
- `src/autom8_asana/models/business/reconciliation.py`
- `src/autom8_asana/automation/workflows/payment_reconciliation/` — dedicated workflow

**Rationale**: 6 standalone reconciliation package files + Lambda handlers + business model + automation workflow. `openpyxl` dep exists specifically for Excel output. 11+ total files. GENERATE.

---

### section-timeline

| Field | Value |
|-------|-------|
| Slug | `section-timeline` |
| Name | Section Timeline Service (Offer Lifecycle History) |
| Category | Business Domain |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/api/routes/section_timelines.py` — 200 LOC, `GET /api/v1/offers`, PAT auth
- `src/autom8_asana/services/section_timeline_service.py` — 738 LOC, `SectionTimeline` computation
- `src/autom8_asana/models/business/section_timeline.py` — 226 LOC, `SectionInterval`, `SectionTimeline`, `OfferTimelineEntry` domain types
- Tests: `tests/unit/api/test_section_timelines.py`, `tests/unit/services/test_section_timeline_service.py`, `tests/unit/models/test_section_timeline.py`

**Rationale**: 4 files / 1,164 LOC (route + service + model + tests), user-facing PAT endpoint at `/api/v1/offers`, own domain types. Prior census gap item 2 underestimated at "2-3 files" — actual is 4 files and substantially more complex. GENERATE.

[KNOW-CANDIDATE] New feature entry, not in prior INDEX — distinct from `dataframe-layer` and `resource-clients`.

---

### vertical-backfill

| Field | Value |
|-------|-------|
| Slug | `vertical-backfill` |
| Name | Vertical Backfill Service (Entity Enrichment from Notes) |
| Category | Business Domain |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.87 |

**Source Evidence**:
- `src/autom8_asana/services/vertical_backfill.py` — 290 LOC, `VerticalBackfillService`, `BackfillResult`, `parse_vertical_from_notes()`
- `tests/unit/services/test_vertical_backfill.py` — dedicated unit test

**Rationale**: Standalone service with `BackfillResult` dataclass and notes-field parser; conceptually distinct from entity-resolution and entity-write-api. 290 LOC with own test cluster. GENERATE.

[KNOW-CANDIDATE] New feature entry, not in prior INDEX.

---

### business-seeder

| Field | Value |
|-------|-------|
| Slug | `business-seeder` |
| Name | Business Entity Seeder (Field Population Across Lifecycle) |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/models/business/seeder.py` — 617 LOC, `BusinessSeeder` domain class
- `src/autom8_asana/automation/seeding.py` — 816 LOC, `FieldSeeder` with `WriteResult`
- `src/autom8_asana/lifecycle/seeding.py` — 302 LOC, lifecycle bridge
- Tests: `tests/unit/models/business/test_seeder.py`, `tests/unit/automation/test_seeding.py`, `tests/unit/automation/test_seeding_write.py`, `tests/unit/lifecycle/test_seeding.py`

**Rationale**: 3 production files / 1,735 LOC spanning 3 packages (models/business, automation, lifecycle), 4 test files. Prior census gap item 1 noted "boundary unclear" — now resolved: `BusinessSeeder` (domain class) + `FieldSeeder` (automation write path) + lifecycle bridge form a coherent feature. GENERATE.

[KNOW-CANDIDATE] New feature entry, not in prior INDEX — prior census gap item 1 ("Business Seeder boundary") resolved.

---

## Category: Automation

### automation-engine

| Field | Value |
|-------|-------|
| Slug | `automation-engine` |
| Name | Automation Rule Engine and Workflow Orchestration |
| Category | Automation |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/automation/` — engine, pipeline, context, base, config, seeding, templates, validation, waiter, events
- `src/autom8_asana/automation/workflows/` — pipeline_transition, section_resolution, bridge_base, mixins, registry, protocols + concrete workflow implementations

**Rationale**: 35+ implementation files. Full automation rule engine, workflow registry, concrete implementations. GENERATE.

---

### data-attachment-bridge

| Field | Value |
|-------|-------|
| Slug | `data-attachment-bridge` |
| Name | Data Attachment Bridge (Backend-to-Asana Reporting Pipeline) |
| Category | Automation |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/automation/workflows/insights/workflow.py` — InsightsExportWorkflow
- `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` — ConversationAuditWorkflow
- `src/autom8_asana/automation/workflows/mixins.py` — `AttachmentReplacementMixin`
- `src/autom8_asana/lambda_handlers/insights_export.py`, `conversation_audit.py`

**Rationale**: Cross-cutting architectural pattern (fetch→format→attach), shared mixin, two concrete workflows. GENERATE.

---

### event-emission

| Field | Value |
|-------|-------|
| Slug | `event-emission` |
| Name | Async Event Emission Pipeline |
| Category | Automation |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/automation/events/` — 6 files (emitter, envelope, rule, transport, types, config)
- `pyproject.toml` — `events = ["autom8y-events>=1.2.0,<2.0.0"]` optional dependency

**Rationale**: 6 files, own types and envelope model, optional dependency group. GENERATE.

---

### polling-scheduler

| Field | Value |
|-------|-------|
| Slug | `polling-scheduler` |
| Name | Polling-Based Automation Scheduler |
| Category | Automation |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/automation/polling/` — 7 files: polling_scheduler, trigger_evaluator, action_executor, config_schema, config_loader, cli, **structured_logger** (new — not in prior census)
- `config/rules/conversation-audit.yaml` — declarative scheduling rule
- `pyproject.toml` — `scheduler = ["apscheduler>=3.10.0"]` optional dependency

**Rationale**: 7 files (1 more than prior census documented; `structured_logger.py` added), YAML config schema, CLI interface, dedicated optional dependency group. GENERATE.

---

### workflow-invoke-api

| Field | Value |
|-------|-------|
| Slug | `workflow-invoke-api` |
| Name | Workflow Invocation API (HTTP-facing Workflow Dispatch Surface) |
| Category | Automation |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/api/routes/workflows.py` — 461 LOC, `WorkflowInvokeRequest`, `WorkflowInvokeResponse`, `WorkflowEntry`, `register_workflow_config()`
- `src/autom8_asana/lambda_handlers/workflow_handler.py` — `WorkflowHandlerConfig` registry
- `src/autom8_asana/api/lifespan.py` — `register_workflow_config()` called ×2 on startup

**Rationale**: 461 LOC route + `WorkflowHandlerConfig` registry + HTTP-facing invocation surface with `WorkflowEntry` listing endpoint, 202-Accepted async execution, Lambda-vs-HTTP dispatch mode. Conceptually distinct from `automation-engine` (which covers the execution engine). User-facing endpoint with S2S JWT auth. GENERATE.

[KNOW-CANDIDATE] New feature entry — HTTP-facing workflow invocation surface distinct from automation-engine execution side.

---

## Category: User-Facing API

### webhooks

| Field | Value |
|-------|-------|
| Slug | `webhooks` |
| Name | Asana Webhook Inbound Event Processing |
| Category | User-Facing API |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/api/routes/webhooks.py` — `webhooks_router`, inbound event processing
- `src/autom8_asana/clients/webhooks.py` — webhook management client
- `src/autom8_asana/lifecycle/webhook.py`, `lifecycle/webhook_dispatcher.py` — lifecycle dispatch

**Rationale**: User-facing REST endpoint, management client, lifecycle dispatch + dispatcher. Token validation and loop prevention documented. GENERATE.

---

### entity-write-api

| Field | Value |
|-------|-------|
| Slug | `entity-write-api` |
| Name | Entity Write API (Field Coercion and Partial Success) |
| Category | User-Facing API |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/api/routes/entity_write.py` — `PATCH /api/v1/entity/{type}/{gid}`
- `src/autom8_asana/services/field_write_service.py` — write orchestration

**Rationale**: User-facing REST endpoint, dedicated write service, field resolution/coercion, partial success patterns. GENERATE.

---

### business-metrics

| Field | Value |
|-------|-------|
| Slug | `business-metrics` |
| Name | Business Metrics Computation (MRR, Ad Spend) |
| Category | User-Facing API |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/metrics/` — 7 files (compute, registry, metric, expr, resolve, sla_profile, cloudwatch_emit, freshness, definitions/)
- `src/autom8_asana/metrics/__main__.py` — CLI compute entry point
- `src/autom8_asana/metrics/definitions/` — `offer.py` (active_mrr, active_ad_spend), `lifecycle.py`

**Rationale**: 7+ files, registered metric definitions, expression DSL, standalone CLI compute entry point, registry pattern. GENERATE.

---

### exports-route

| Field | Value |
|-------|-------|
| Slug | `exports-route` |
| Name | Polars-backed /exports Route with Predicate-Tree Compilation |
| Category | User-Facing API |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |
| Status | **LIVE** |
| live_since | 2026-04-29 |
| telos_deadline | 2026-05-11 (Phase 1 — DELIVERED) |
| obs_status | F (OBS-EXPORTS-001 OPEN — zero metrics/SLOs/alerts, deadline 2026-06-15) |

**Source Evidence**:
- `src/autom8_asana/api/routes/exports.py` — primary route handler, dual-mount `/api/v1/exports` + `/v1/exports`
- `src/autom8_asana/api/routes/_exports_helpers.py` — predicate compilation helpers, `_walk_predicate` visitor
- Tests: 6 committed test files (`test_exports_auth_exclusion.py`, `test_exports_contract.py`, `test_exports_format_negotiation.py`, `test_exports_handler.py`, `test_exports_helpers.py`, `test_exports_helpers_walk_predicate_property.py`)
- Commits since prior INDEX: 5 commits modifying `exports.py` / `_exports_helpers.py`

**Rationale**: User-facing live REST endpoint, 6 test files, `_walk_predicate` visitor architectural pattern, imports from frozen-range compiler. **Missing per-feature knowledge file `.know/feat/exports-route.md` (highest-priority gap per Myron glint).** GENERATE.

---

## Category: Infrastructure

### fastapi-server

| Field | Value |
|-------|-------|
| Slug | `fastapi-server` |
| Name | FastAPI HTTP Server (ECS Mode) |
| Category | Infrastructure |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.96 |

**Source Evidence**:
- `src/autom8_asana/api/` — 35+ files (main, lifespan, dependencies, middleware/, preload/, client_pool, fleet_query_adapter, models, routes/)
- `src/autom8_asana/entrypoint.py` — dual-mode entry point
- `Dockerfile`, `docker-compose.yml`

**Rationale**: 35+ files, 22 registered routers (4 dual-mounted), 13-step startup sequence, middleware stack. GENERATE.

---

### lambda-handlers

| Field | Value |
|-------|-------|
| Slug | `lambda-handlers` |
| Name | AWS Lambda Function Handlers |
| Category | Infrastructure |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/lambda_handlers/` — 13 files: cache_warmer, cache_invalidate, cloudwatch, checkpoint, workflow_handler, insights_export, conversation_audit, payment_reconciliation, pipeline_stage_aggregator, push_orchestrator, reconciliation_runner, story_warmer, timeout
- `src/autom8_asana/entrypoint.py` — Lambda mode detection via `AWS_LAMBDA_RUNTIME_API`
- `pyproject.toml` — `lambda = ["awslambdaric>=2.2.0"]` optional dependency

**Rationale**: 13 Lambda handler files, dual-mode entrypoint. GENERATE.

---

### admin-cache-control

| Field | Value |
|-------|-------|
| Slug | `admin-cache-control` |
| Name | Admin Cache Control API (Force-Rebuild / Incremental-Rebuild) |
| Category | Infrastructure |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.85 |

**Source Evidence**:
- `src/autom8_asana/api/routes/admin.py` — 522 LOC, `POST /v1/admin/cache/refresh`, `include_in_schema=False`
- References: ADR (TDD-cache-freshness-remediation Fix 4), security constraint (Bedrock W4C-P3 / SEC-DT-10 / D-017), super-admin gate (`admin:access` permission)
- `src/autom8_asana/api/routes/internal.py` — `require_service_claims` used by admin route (load-bearing dependency, 11 routes import it)

**Rationale**: 522 LOC operational endpoint, S2S JWT + super-admin permission gate, force-full-rebuild vs incremental modes, Lambda invocation side path, hidden from OpenAPI but real production surface. GENERATE.

[KNOW-CANDIDATE] New feature entry — not in prior INDEX.

---

### authentication

| Field | Value |
|-------|-------|
| Slug | `authentication` |
| Name | Authentication (JWT / BotPAT / DualMode / S2S / ServiceClaims) |
| Category | Infrastructure |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/auth/` — 5 files (jwt_validator, bot_pat, dual_mode, service_token, audit)
- `src/autom8_asana/api/routes/internal.py` — 172 LOC, `ServiceClaims`, `require_service_claims` dependency (imported by 11 route files)
- `pyproject.toml` — `auth = ["autom8y-auth[observability]>=3.3.0"]` optional dependency

**Rationale**: 5 auth files + load-bearing `internal.py` dependency. Four auth strategies + ServiceClaims claim-extraction pattern. `internal.py` subsumed here. GENERATE.

---

### observability

| Field | Value |
|-------|-------|
| Slug | `observability` |
| Name | Observability (Correlation IDs, Metrics, Telemetry) |
| Category | Infrastructure |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/observability/` — 3 files (context, correlation, decorators)
- `src/autom8_asana/api/metrics.py` — Prometheus metrics
- `src/autom8_asana/protocols/observability.py` — protocol definition
- `src/autom8_asana/lambda_handlers/cloudwatch.py` — CloudWatch metrics emission Lambda

**Rationale**: Cross-cutting correlation ID tracking, Prometheus metrics, CloudWatch Lambda, OTel telemetry. OBS-EXPORTS-001 open gap. GENERATE.

---

### data-service-client

| Field | Value |
|-------|-------|
| Slug | `data-service-client` |
| Name | autom8_data Satellite Service Client (Ad Performance Insights) |
| Category | Infrastructure |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/clients/data/` — 14+ files (client, config, models, _cache, _metrics, _normalize, _pii, _policy, _response, _retry, endpoints/batch, endpoints/export, endpoints/insights, endpoints/reconciliation, endpoints/simple)

**Rationale**: 14 implementation files, cross-service client, own PII handling, circuit breaker, retry behavior, emergency kill switch. GENERATE.

---

### settings-configuration

| Field | Value |
|-------|-------|
| Slug | `settings-configuration` |
| Name | Pydantic Settings and Environment Configuration |
| Category | Infrastructure |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.80 |

**Source Evidence**:
- `src/autom8_asana/settings.py` — `Settings` singleton, 50+ env vars

**Rationale**: Single file, pure infrastructure concern, no cross-cutting behavior of its own. Settings is a dependency of every feature, not a feature itself. SKIP.

---

## Category: Services

### gid-data-sync-pipeline

| Field | Value |
|-------|-------|
| Slug | `gid-data-sync-pipeline` |
| Name | GID Data Sync Pipeline (GID Mapping + Account Status Push) |
| Category | Services |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.93 |

**Source Evidence**:
- `src/autom8_asana/services/gid_push.py` — 536 LOC, `GidPushResponse`, `AccountStatusPushResponse`, exports GID mappings and account status to autom8_data post-cache-warm
- `src/autom8_asana/services/gid_lookup.py` — 318 LOC, `GidLookupIndex`, `build_gid_index_data`
- `src/autom8_asana/lambda_handlers/push_orchestrator.py` — 207 LOC, sequences post-warm side-effects; documents FLAG-1 (stays in lambda_handlers to avoid circular deps)
- `src/autom8_asana/lambda_handlers/pipeline_stage_aggregator.py` — 217 LOC, ephemeral pipeline stage summaries per ADR (Option C)
- Tests: `tests/unit/services/test_gid_push.py`, `tests/unit/services/test_gid_lookup.py`, `tests/unit/lambda_handlers/test_push_orchestrator.py`, `tests/unit/lambda_handlers/test_pipeline_stage_aggregator.py`
- Importers: `cache/dataframe/factory.py`, `core/registry_validation.py`, `api/preload/progressive.py`, `api/preload/legacy.py`, `services/universal_strategy.py`, `services/dataframe_service.py`, `api/routes/admin.py`

**Rationale**: 4 production files / 1,278 LOC, 4 test files, explicit architectural constraint (FLAG-1), ADR reference, cross-service push pattern. Imported by 7+ modules. GENERATE.

[KNOW-CANDIDATE] New feature entry — prior census gap item 3 noted as "may be its own distinct feature"; now confirmed.

---

## Category: Tooling

### query-cli

| Field | Value |
|-------|-------|
| Slug | `query-cli` |
| Name | autom8-query CLI Tool |
| Category | Tooling |
| Complexity | LOW |
| Recommendation | **GENERATE** |
| Confidence | 0.85 |

**Source Evidence**:
- `src/autom8_query_cli.py` — standalone CLI entry point (TID251-exempt, uses direct httpx)
- `pyproject.toml` — `[project.scripts] autom8-query = "autom8_query_cli:main"` registered entry point
- `src/autom8_asana/query/__main__.py` — 10 subcommands

**Rationale**: Registered CLI entry point in `pyproject.toml`, user-facing command. GENERATE.

---

### lockfile-propagator

| Field | Value |
|-------|-------|
| Slug | `lockfile-propagator` |
| Name | Lockfile-Propagator In-Tool Source Stubbing |
| Category | Tooling |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |
| Status | **proposed** (pending prod-CI green; defer-watch `lockfile-propagator-prod-ci-confirmation`) |
| Source Repo | autom8y monorepo (not autom8y-asana source) |

**Source Evidence**:
- `autom8y/tools/lockfile-propagator/src/lockfile_propagator/source_stub.py` — 327 LOC, `stub_editable_path_sources()`
- `.ledge/specs/lockfile-propagator-source-stubbing.tdd.md` — TDD spec
- `.ledge/decisions/ADR-lockfile-propagator-source-stubbing.md` — ADR (Option A, 8 alternatives evaluated)

**Rationale**: ADR + TDD spec + 780+ LOC. Boundary note: source lives in autom8y monorepo, not autom8y-asana. **Missing per-feature knowledge file `.know/feat/lockfile-propagator.md`.** GENERATE.

---

## Census Gaps

### 1. Boundary-ambiguity decisions

- **gid-data-sync-pipeline vs lambda-handlers**: `push_orchestrator.py` and `pipeline_stage_aggregator.py` could be subsumed under `lambda-handlers` (prior census) OR promoted to standalone (this census promotes them: 1,278 LOC, FLAG-1 architectural constraint, ADR reference, own test cluster, 7+ importers). Dual reference in evidence — not a conflict.
- **workflow-invoke-api vs automation-engine**: `workflows.py` route (461 LOC) split out because it is the HTTP invocation surface with own request/response contract and registry hook.
- **custom-field-descriptor-dsl vs business-domain-model**: 740 LOC subsumed under `business-domain-model` (descriptor DSL is integral typed access layer for custom fields, not independently consumable). KNOW-CANDIDATE marker on `business-domain-model` ensures the knowledge file documents this subsystem.

### 2. Glints NOT promoted to standalone features

| Glint | Decision | Reason |
|-------|----------|--------|
| `glint-feat-cache-migration-adapter` | Subsumed into `cache-subsystem` | 677 LOC migration path is a dimension of cache operations |
| `glint-feat-queries-saved-corpus` | Subsumed into `query-engine` | YAML corpus is user-facing dimension of query engine |
| `glint-feat-custom-field-descriptor-dsl` | Subsumed into `business-domain-model` | Integral to business model layer |
| `glint-feat-internal-service-auth` | Subsumed into `authentication` | 11 importers — shared infrastructure, not a feature |
| `glint-polling-structured-logger-undocumented` | Architecture doc gap only | Filing for architecture.md update |
| `glint-feat-lockfile-propagator-knowledge-gap` | Knowledge gap only | Feature already in INDEX; missing `.know/feat/` file is GENERATE queue item |
| `glint-feat-exports-route-knowledge-gap` | Knowledge gap only | Highest-priority GENERATE queue item |
| `glint-prototypes-telemetry-poc` | DISMISS | Prototype directory, not production code |
| `glint-feat-search-service-skip-confirmed` | DISMISS | Already SKIP in INDEX, confirmed correct |

### 3. Orphan check — `.know/feat/{slug}.md` files on disk vs new census

All 32 existing `.know/feat/` knowledge files (excluding INDEX.md) correspond to features in the new census. Zero orphans detected.

**Missing knowledge files for GENERATE features (require GENERATE queue action)**:
- `.know/feat/exports-route.md` — **MISSING** (highest priority, telos-adjacent)
- `.know/feat/lockfile-propagator.md` — **MISSING** (lower priority, proposed status)
- `.know/feat/section-timeline.md` — **NEW FEATURE**
- `.know/feat/vertical-backfill.md` — **NEW FEATURE**
- `.know/feat/business-seeder.md` — **NEW FEATURE**
- `.know/feat/gid-data-sync-pipeline.md` — **NEW FEATURE**
- `.know/feat/admin-cache-control.md` — **NEW FEATURE**
- `.know/feat/workflow-invoke-api.md` — **NEW FEATURE**

### 4. Telos-aware urgency markers (deadline 2026-05-11, 3 days remaining)

Features under `project-asana-pipeline-extraction` telos:
- `exports-route` — Phase 1 DELIVERED. OBS-EXPORTS-001 open (deadline 2026-06-15). Missing knowledge file is the remaining gap.
- `gid-data-sync-pipeline` — Under-documented; relevant to pipeline extraction telos as the post-warm data push component.

### 5. Source categories scanned

| Source Category | Status | Count |
|---|---|---|
| Module/package directories (`src/autom8_asana/**/*.py`) | Scanned via architecture seed + targeted file checks | 33 sub-packages |
| Entry points (`entrypoint.py`, `api/main.py`, `lambda_handlers/`, `query/__main__.py`) | Scanned | 4 entry points |
| Decision records (`docs/decisions/`, `.ledge/decisions/`) | Confirmed | ADR-lockfile-propagator referenced |
| User-facing interface definitions (routes, CLI) | Scanned via architecture seed (22 routers) + targeted source reads | 22 routers + 2 CLI scripts |
| Project documentation (`README.md`, `docs/`) | Consulted via architecture seed references | Used for rationale validation |
| Existing codebase knowledge (`.know/*.md`) | Read: architecture.md (fresh), prior INDEX.md | Used as structural map |
| Configuration and workflow definitions (`config/`, `pyproject.toml`, `.github/`) | Consulted via architecture seed | pyproject.toml optional deps confirmed |

