---
domain: feat/index
generated_at: "2026-07-24T00:00Z"
expires_after: "30d"
source_scope:
  - "./.know/architecture.md"
  - "./.know/api.md"
  - "./src/autom8_asana/**/*.py"
  - "./mcp/asana_mcp/tools/**/*.py"      # MCP island — the 10 tool modules (FL-3 scope widening)
  - "./mcp/asana_mcp/**/*.py"            # MCP sidecar supporting modules
  - "./mcp/serve_stdio.py"
  - "./mcp/pyproject.toml"
  - "./mcp/README.md"
  - "./.ledge/decisions/ADR-ws7-actor-attribution-seam.md"   # delegation arc (WS-7 actor-attribution seam)
generator: theoros (mechanical — FL-3 lane; theoros hero unseated, executed by fleet-delegation-phase2 WAVE-1)
source_hash: "53755669"
prior_source_hash: "8980bcd7"
confidence: 0.9
format_version: "1.0"
update_mode: "incremental"
incremental_cycle: 3
max_incremental_cycles: 3
---

# Feature Census — autom8y-asana @ HEAD `53755669`

**Census Date**: 2026-07-24
**Source Hash**: `53755669` (widened scope: `src/autom8_asana/**` + `mcp/asana_mcp/**` + delegation-arc ADR)
**Prior Index Hash**: `8980bcd7` (2026-05-08)
**HEAD commit**: `dfdb84a3`
**Commits Since Prior Index**: 210 commits (2026-05-08 → 2026-07-24). The dominant NEW source region is the **`mcp/` MCP-sidecar island** (7 feature-bearing commits, #239 → #268) plus the **fleet-delegation arc** (WS-5b whole-surface disclosure, RB-1 confirm-gate, WS-7 actor-attribution seam).

**FL-3 SCOPE CORRECTION (load-bearing)**: the prior census `source_scope` **structurally excluded `mcp/`** — its 41-feature census predates the entire MCP island. A naive `/know --scope=feature` re-run against the un-widened scope would SILENTLY re-exclude the island and reproduce the blind spot. This regeneration **widens `source_scope`** to include `mcp/asana_mcp/tools/**` (the 10 tool modules), the MCP sidecar supporting modules, and the delegation-arc ADR, then censuses that region. The `src/autom8_asana/**` region is **carried forward verbatim from 2026-05-08 (NOT re-audited this cycle)**; a full re-census of `src/` is queued (Census Gaps §6). `incremental_cycle` is at its 3/3 cap — the next `/know --scope=feature` run should be a FULL re-census.

**Summary Counts**: **52 features across 8 categories.** 46 GENERATE, 6 SKIP.
- **NEW this cycle — Category: MCP Sidecar (asana-mcp-v1)**: 11 features (9 GENERATE / 2 SKIP) covering the FastMCP sidecar island + the fleet-delegation arc (mcp-report-workflow-disclosure / `list_report_workflows`, mcp-confirm-gate, mcp-composite-write, and the delegation keystone mcp-actor-attribution-seam).
- **Carried forward (src/autom8_asana census, 2026-05-08)**: 41 features across 7 categories — Core Platform 12 (9G/3S), Business Domain 10 (10G), Automation 5 (5G), User-Facing API 4 (4G), Infrastructure 7 (6G/1S), Services 1 (1G), Tooling 2 (2G).
- **Prior census**: 41 features (37 GENERATE, 4 SKIP)
- **Net new features**: +11 (all in the new MCP Sidecar category / delegation arc)
- **Removed**: 0
- **Boundary corrections**: 0 this cycle (src/ carried forward)

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

## Category: MCP Sidecar (asana-mcp-v1)

> **NEW region this cycle — previously excluded from `source_scope`.** The `mcp/` island is a **FastMCP 3.4.4 sidecar** (`mcp/asana_mcp/`) that re-exposes the autom8y-asana REST **S2S** surface as MCP tools for agent consumption. It is the **code realization of the fleet-delegation arc**: an agent answers real business questions (read tier) and performs a gated business mutation (write tier) *on behalf of a human operator*, with a confirm-before-firing human gate (R5 / RB-1), whole-surface disclosure (WS-5b), and two-family honest failure classification (C3).
>
> **Posture (frozen, not incidental):** REFERENCE / THROWAWAY POC (charter §5.3 / MCP-REFERENCE-POSTURE-001) — NOT production code; reimplement against production contracts at tech-transfer. **Load-bearing fence (constraint 5):** the island NEVER imports the `autom8_asana` domain SDK and makes ZERO direct Asana calls — it speaks HTTP only to the satellite REST surface via `ctx.http`; auth JOINS the fleet bridge `autom8y_core.TokenManager` (SVR-8), the sole sanctioned `autom8y_core` touch-point (lazy import). Proven by `mcp/tests/test_import_safety.py` (AST scan + clean-subprocess).
>
> **Grounding:** charters `DECISION-fleet-mcp-program-alignment-2026-07-17.md`, `DECISION-asana-mcp-v1-rulings-B1-B5-W5.md`; delegation keystone `ADR-ws7-actor-attribution-seam.md`. 7 feature-bearing commits (#239 s2 read-surface → #238 s3 composite-write → #242 s6 assembly → #249 dual-key tag → #264 401-fail-clean → #263 RB-1 confirm-gate → #268 report-workflow disclosure). Test corpus: 25 files in `mcp/tests/`.

### mcp-sidecar-server

| Field | Value |
|-------|-------|
| Slug | `mcp-sidecar-server` |
| Name | asana_mcp FastMCP Sidecar (Server Factory + Assembly + Stdio Mount) |
| Category | MCP Sidecar |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.92 |
| Posture | REFERENCE / THROWAWAY POC (charter §5.3) |

**Source Evidence**:
- `mcp/asana_mcp/server.py` — `create_server(settings) -> FastMCP` (FROZEN signature; call-time-only config/import — C9a), registers read tools 1-5
- `mcp/asana_mcp/assembly.py` — `build_instrumented_server()` (mount-seam item 4: create → register write → instrument)
- `mcp/asana_mcp/context.py` — `SidecarContext` (frozen seam: `http` / `settings` / `readiness`), `build_context()`
- `mcp/asana_mcp/settings.py` — `Settings` (env prefix `ASANA_MCP_*`; `readiness_fail_open`, budget extension point)
- `mcp/asana_mcp/timeouts.py` — single timeout source-of-truth (C4 / R2)
- `mcp/serve_stdio.py` — stdio launcher (the Claude Code witness mount entrypoint; `--smoke` inventory mode)
- `mcp/pyproject.toml` — `asana-mcp` package (fastmcp `>=3.4.4,<3.5.0`, httpx, pydantic, otel, autom8y-core)
- `mcp/asana_mcp/tools/__init__.py`, `mcp/README.md`

**Rationale**: The island's structural core — the FROZEN mount-seam (`create_server` → `register(mcp, ctx)` per tool → `instrument`), the SidecarContext substrate every tool consumes, settings/timeouts source-of-truth, and the stdio mount entrypoint. Import-safety fence (`import asana_mcp` does zero IO, pulls neither `autom8_asana` nor `autom8y_core`) is verified in `test_import_safety.py` / `test_assembly_floor.py`. GENERATE.

[KNOW-CANDIDATE] Entire MCP island absent from prior INDEX — `source_scope` structurally excluded `mcp/`.

---

### mcp-auth-bridge

| Field | Value |
|-------|-------|
| Slug | `mcp-auth-bridge` |
| Name | S2S-JWT Bridge (TokenManager Join + 401-Fail-Clean Mint Classification) |
| Category | MCP Sidecar |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `mcp/asana_mcp/bridge.py` — `build_http_client()` (per-request `Authorization: Bearer <jwt>` event-hook), `_default_token_provider()` (lazy `autom8y_core.TokenManager.from_env()`, SVR-8), `_classify_mint_failure()`, `make_readiness_probe()` (proxies satellite `/ready`, fail-closed default)
- `mcp/tests/test_bridge_401_fail_clean.py`, `test_readiness_gate.py`, `test_postures.py`
- Commit #264 `fix(mcp): fail clean on S2S mint 401`

**Rationale**: The auth seam — joins the fleet `TokenManager` (zero new mint code) and enforces the 401-fail-clean discipline (operator ruling R21 Lane 1): a revoked/invalid `sa_*` credential presents CLEANLY as auth-shaped/non-retryable (`InvalidServiceKeyError` → 401 `S2S_MINT_CREDENTIALS_INVALID`) while auth-infra trouble presents as retryable 503 (`S2S_MINT_UNAVAILABLE`) — the two families never cross-dress. Classification is by exception-class name across the MRO (no `autom8y_core` import — C9a). GENERATE.

---

### mcp-discovery-tools

| Field | Value |
|-------|-------|
| Slug | `mcp-discovery-tools` |
| Name | MCP Discovery Tier (list_entity_types + describe_entity) |
| Category | MCP Sidecar |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `mcp/asana_mcp/tools/discovery.py` — `list_entity_types` (`GET /v1/query/entities`) + `describe_entity` (composes `/fields` + `/relations` + best-effort `/sections`)
- `mcp/tests/test_discovery_tools.py`

**Rationale**: The thin, FleetQuery-shaped discovery tier (two-tier grain ruling C1) — limb-(a) steps 1-2 that let an agent GROUND on the schema before building predicates. Kept deliberately thin/fleet-shaped; the rich per-satellite power lives in `mcp-query-tools`. GENERATE.

---

### mcp-query-tools

| Field | Value |
|-------|-------|
| Slug | `mcp-query-tools` |
| Name | MCP Execution Tier (query_rows / query_aggregate / resolve_entity + Honesty Passthrough) |
| Category | MCP Sidecar |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.91 |

**Source Evidence**:
- `mcp/asana_mcp/tools/query.py` — `query_rows` (`POST /v1/query/{t}/rows`) + `query_aggregate` (`POST /v1/query/{t}/aggregate`)
- `mcp/asana_mcp/tools/resolve.py` — `resolve_entity` (`POST /v1/resolve/{t}`, identifier → GID batch)
- `mcp/asana_mcp/schemas.py` — hand-authored `RowsArgs` / `AggregateArgs` / `ResolveArgs` (C2 / R6; native execution router is `include_in_schema=False` — SVR-2) + WS-2-EP pin-and-canary anchor (`test_schema_canary.py`)
- `mcp/asana_mcp/envelopes.py` — `unwrap_outer` / `extract_honesty`; `mcp/asana_mcp/tools/_common.py` — `ensure_ready`, `get_json`/`post_json`, `shape_execution_result`
- `mcp/asana_mcp/errors.py` — `McpToolError` taxonomy + `map_http_error` (C3 disjoint auth/warming/server families; cross-cutting, also consumed by bridge/tag_resolve/composite_write)
- `mcp/tests/test_query_tools.py`, `test_resolve_tool.py`, `test_honesty_passthrough.py`, `test_errors_c3.py`, `test_errors_passthrough.py`, `test_schema_canary.py`, `test_cold_frame_mapping.py`

**Rationale**: The rich native read/execution tier (limb-(a) steps 3-5). Hand-authored schemas from native `RowsRequest`/`AggregateRequest`/`ResolutionRequest`, guarded by a content-hash drift canary. The honesty attestations (`stale_served` / `honest_empty` / `contract_complete` — C6 / SVR-5) are lifted UNWRAPPED-and-VISIBLE to the top level so the LLM sees them plainly. C3 fence: a cold-frame 503 maps to retryable/warming, NEVER auth-shaped. GENERATE.

---

### mcp-composite-write

| Field | Value |
|-------|-------|
| Slug | `mcp-composite-write` |
| Name | Composite Write Tool (asana_complete_tagged_task — add_tag → push → mark_complete) |
| Category | MCP Sidecar |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.92 |
| Status | **EXPOSURE-GATED** (`ASANA_MCP_ENABLE_WRITE_SURFACE`, default OFF; W-5 / GATE-BW) |

**Source Evidence**:
- `mcp/asana_mcp/tools/composite_write.py` — 521 LOC; `execute_composite_write()` (server-side all-or-nothing sequencer), `execute_tagged_write()` (dual-key WS-B2 orchestrator), `CompositeWriteResult`/`StepOutcome` honest receipts, `write_surface_enabled()` exposure gate, tool `asana_complete_tagged_task`
- Backing REST verbs (SVR-7): `POST /api/v1/tasks/{gid}/tags`, `PUT /api/v1/tasks/{gid}` (push + mark_complete)
- Depends on `mcp-confirm-gate` (RB-1) and `mcp-tag-resolve` (WS-B2)
- `mcp/tests/test_composite_write_s3.py`, `test_tag_dual_key_wsb2.py`
- Commits #238 (s3 POC), #249 (dual-key)

**Rationale**: The write tier — the ratified add_tag → push(PUT-save) → mark_complete chain shipped as ONE workflow-shaped tool, sequenced server-side, all-or-nothing HONESTLY (the backing API has no transaction, so committed steps are not rolled back; every verb is idempotent so a safe re-run converges — W-2/W-3/W-4). Dual-key selector (exactly one of `tag_gid`|`tag_name`), read-back confirmation (PLAY-3), and a documented CONSUMED-TRIGGER hazard (re-applying a play tag RE-FIRES a live automation). EXPOSURE-GATED default OFF — build ≠ expose. GENERATE.

[KNOW-CANDIDATE] The all-or-nothing-honestly (non-ACID convergence-on-re-run) contract is a distinct pattern worth a dedicated per-feature knowledge file.

---

### mcp-confirm-gate

| Field | Value |
|-------|-------|
| Slug | `mcp-confirm-gate` |
| Name | RB-1 Confirm-Before-Firing Gate (Two-Phase Human-Yes Token) |
| Category | MCP Sidecar |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `mcp/asana_mcp/tools/confirm_gate.py` — `ConfirmationGate` (single-use, TTL-bounded, intent-bound pending store), `intent_fingerprint()` (sha256 of task+tag+save-fields tuple), `build_confirmation_envelope()` (zero-writes `confirmation_required` envelope), redemption outcomes (ok/unknown/expired/intent_mismatch)
- `mcp/tests/test_confirm_gate_rb1.py`
- Commit #263 `feat(mcp): RB-1 confirm-before-firing gate (R5/R21)`

**Rationale**: The delegation-arc human gate (operator ruling R5): actions known to fire business automations "pause for a human yes". Two-phase — phase 1 (no token) writes NOTHING and returns a single-use expiring token bound by fingerprint to the exact write intent + a human-approval instruction; phase 2 executes only with the SAME arguments + token. A reused/expired/argument-drifted token is refused (zero writes) and burned. V1 trigger posture: ALL tags treated trigger-capable (the classification list's owner is deliberately unassigned — the boundary cannot silently drift ahead of its owner). GENERATE.

---

### mcp-tag-resolve

| Field | Value |
|-------|-------|
| Slug | `mcp-tag-resolve` |
| Name | Tag Name → GID Resolution (WS-B2, Page-Cap Honesty, Read-Back Confirmation) |
| Category | MCP Sidecar |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.89 |

**Source Evidence**:
- `mcp/asana_mcp/tools/tag_resolve.py` — 430 LOC; `resolve_tag_name()` (429-aware exponential backoff), `TagNameCache` (TTL-bounded, positive-only), `TagResolution` (resolved/not_found/ambiguous/truncated_scan), `validate_tag_selector()` (dual-key), `read_back_tag_state()` (PLAY-3 soft-fail confirmation)
- Backing satellite read surface: `GET /api/v1/tags?name=` (#246; sidecar half of the dual-key fix)
- `mcp/tests/test_tag_dual_key_wsb2.py`

**Rationale**: The sidecar half of the WS-B2 dual-key fix — resolves an EXACT (case-sensitive, byte-for-byte) tag name to its GID READ-ONLY (adds no write verb; the only write remains add_tag — HARD FENCE). Owns three honesty properties: page-cap honesty (a name miss is bounded at the satellite's 100-page scan cap and never claims proven absence; a forward-compatible `truncated_scan` status is emitted only when the satellite positively signals truncation), TTL-bounded resolution cost, and upstream error passthrough. GENERATE.

---

### mcp-report-workflow-disclosure

| Field | Value |
|-------|-------|
| Slug | `mcp-report-workflow-disclosure` |
| Name | Report-Workflow Disclosure (list_report_workflows — WS-5b Whole-Surface Disclosure) |
| Category | MCP Sidecar |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `mcp/asana_mcp/tools/workflows.py` — `list_report_workflows` tool + `list_report_workflows_handler()`; reads the live oracle `GET /api/v1/workflows` (backed by `_WORKFLOW_CONFIGS` registry populated at startup by `api/lifespan.py`)
- `mcp/tests/test_workflows_disclosure.py`
- Commit #268 `feat(mcp): disclose registered report workflows`

**Rationale**: The WS-5b whole-surface disclosure tier — a PURE READ that discloses the REGISTERED report-workflow surface (insights-export, conversation-audit, ...) with the honesty vocabulary (`honest_empty` / `contract_complete`) surfaced top-level. Explicit boundary: it NEVER invokes (R7 / §5 HALT) — invocation is a separate declared write-verb (`POST /api/v1/workflows/{id}/invoke`, `x-fleet-side-effects: asana_api/task`) that uploads/deletes Asana attachments and can RE-FIRE a consuming listener; that verb is deliberately NOT disclosed here. Carries the delegation-arc consumption posture (CAPABILITY-NOW / consumption-post-KEYSTONE — see `mcp-actor-attribution-seam`). GENERATE.

---

### mcp-observability

| Field | Value |
|-------|-------|
| Slug | `mcp-observability` |
| Name | MCP Observability + Guardrails Overlay (instrument() — span / traceparent / timeout / rate-cap) |
| Category | MCP Sidecar |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `mcp/asana_mcp/observability.py` — 815 LOC; `instrument(mcp, settings) -> FastMCP` (idempotent; mount-seam item 3): per-tool-execution `gen_ai.*` span + `com.autom8y.mcp.*` attrs, W3C traceparent propagation onto `ctx.http`, outermost timeout guard (values from `asana_mcp.timeouts`), honesty-field passthrough assertion, MCP-side rate cap (`MCP_RATE_BUDGET_EXHAUSTED`, bounded — never unbounded queueing)
- `mcp/tests/test_instrument_seam.py`, `test_span_and_traceparent.py`, `test_budget_partition_and_rate_cap.py`, `test_timeout_cascade_invariant.py`, `test_import_safety_obs.py`, `test_seam_conformance.py`
- Consumes seam contract `asana-mcp-v1.s4-seam-contract.md`

**Rationale**: The sprint-4 observability + guardrails wrap applied at sprint-6 assembly. Import-safe (lazy OTel, call-time env reads — guards the 2026-04-28 config incident), zero domain-SDK coupling. Owns the declared failure postures: typed cold-frame 503 mapping (never auth-shaped), `/ready` fail-closed refusal, MCP-side budget partition + rate cap. GENERATE.

---

### mcp-match-business-stub

| Field | Value |
|-------|-------|
| Slug | `mcp-match-business-stub` |
| Name | match_business Tool (Tool 6 — Surface-Not-POC Stub) |
| Category | MCP Sidecar |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.85 |

**Source Evidence**:
- `mcp/asana_mcp/tools/_match_business_stub.py` — 26 LOC; intentionally NOT registered by `create_server`; `register()` raises `NotImplementedError(STUB_NOTE)`

**Rationale**: The 6th curated tool (`match_business`, backing `POST /v1/matching/query`) is part of the read SURFACE but explicitly NOT part of the POC (shape §0). The module is a deliberate scope-boundary marker in code — no implementation to document. Its BACKING capability is already censused as `fuzzy-entity-matching` (Business Domain). SKIP.

---

### mcp-actor-attribution-seam

| Field | Value |
|-------|-------|
| Slug | `mcp-actor-attribution-seam` |
| Name | Actor-Attribution Seam (Delegation Keystone — acting_agent + delegating_user) |
| Category | MCP Sidecar |
| Complexity | HIGH |
| Recommendation | **SKIP** |
| Confidence | 0.88 |
| Status | **PLANNING / built-unconsumed** (ADR `proposed`; design-only, NO production code; cross-repo Phase-2) |

**Source Evidence**:
- `.ledge/decisions/ADR-ws7-actor-attribution-seam.md` — `status: proposed`, `phase: design-only (VISIONARY / Phase-2 precondition) — NO production code`; the Phase-2 consumption/audit schema MUST carry BOTH `sub=human` (delegating_user) and `act=agent` (acting_agent) for request- AND event-triggered actions
- `mcp/asana_mcp/tools/workflows.py:24-31,59-64` — the ONLY code reference: disclosed verbs run on the SHARED BOT PAT (S2S-JWT → bot PAT via `api/dependencies.get_auth_context`) "until the identity keystone (acting_agent + delegating_user) lands in a cross-repo Phase-2"
- Grounding: fleet-delegation-portfolio (WS-7 reactive-delegation axis); RFC-8693 token audit fields ASSERTED present-but-unread

**Rationale**: The north-star keystone of the fleet-delegation arc — audit-names-the-human on BOTH the request axis and the reactive (event-woken) axis. Recorded here for arc coverage, but **NOT code-realized in autom8y-asana**: it is an ADR-stage seam whose audit-of-record row is written CROSS-REPO in the auth service `audit_log` (autom8y-asana has no persistence layer), and it must NOT lock until an actor-modeling claims contract exists SDK-side. The MCP island today ships SURFACE (CAPABILITY-NOW), not audit-names-the-human (consumption-post-KEYSTONE) — the built-unconsumed honest floor. **SKIP** (no in-repo code to generate a per-feature knowledge file against); re-evaluate when the Phase-2 seam lands.

[KNOW-CANDIDATE] The delegation arc's built-unconsumed floor (capability shipped, identity keystone deferred cross-repo) is a governance pattern the corpus does not yet name.

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
| **MCP island (`mcp/asana_mcp/**`, `mcp/serve_stdio.py`, `mcp/pyproject.toml`, `mcp/README.md`)** | **Scanned directly (FL-3 scope widening) — full-text reads of all 10 tool modules + supporting modules** | **10 tool modules + 11 supporting modules + 25 test files** |
| **Delegation-arc decisions (`.ledge/decisions/ADR-ws7-…`, `DECISION-asana-mcp-v1-rulings-…`)** | **Read for WS-7 keystone + B1-B5/W5 rulings** | ADR-ws7 (`proposed`) + charter rulings |

---

## FL-3 additions (this cycle) — MCP island + delegation arc

### 6. src/autom8_asana full re-census QUEUED (carry-forward disclosure)

This cycle **widened scope to census the `mcp/` island and delegation arc**; the 41 `src/autom8_asana/**` feature entries above are **carried forward verbatim from the 2026-05-08 census (source_hash `8980bcd7`) and were NOT re-audited**. Sanity spot-check confirmed representative source paths still present (`client.py`, `cache/`, `api/routes/exports.py`, `services/gid_push.py`). Because `incremental_cycle` is now at its 3/3 cap AND 210 commits have landed since the src/ census, **the next `/know --scope=feature` run should be a FULL re-census** (reset the incremental lineage) covering both regions. Do not treat the src/ entries' timestamps as fresh.

### 7. Delegation arc (fleet-delegation north star) — how it is covered

The "delegation arc" is not a single module; it is the through-line the MCP island serves. Coverage map:

| Arc element | Census home | Realization state |
|-------------|-------------|-------------------|
| Agent performs business READS on behalf of a human | `mcp-discovery-tools`, `mcp-query-tools` | CODE-REALIZED (POC) |
| Agent performs a GATED business WRITE on behalf of a human | `mcp-composite-write` | CODE-REALIZED, EXPOSURE-GATED default OFF |
| "Pause for a human yes" before a trigger-capable action (R5) | `mcp-confirm-gate` | CODE-REALIZED (POC) |
| Whole-surface disclosure of the invocable surface (WS-5b) | `mcp-report-workflow-disclosure` | CODE-REALIZED (POC), read-only |
| **Audit-names-the-human (acting_agent + delegating_user)** | `mcp-actor-attribution-seam` | **PLANNING / built-unconsumed** — ADR `proposed`, cross-repo Phase-2, NO in-repo code |

Honest floor: the island ships **CAPABILITY (SURFACE) NOW**; identity **CONSUMPTION** (audit-names-the-human) is deferred to a cross-repo Phase-2 keystone. The disclosed/gated verbs still run on the SHARED bot PAT. This built-unconsumed state is named in `workflows.py` and governed by `ADR-ws7-actor-attribution-seam.md` — never reported as mission-complete.

### 8. MCP per-feature knowledge files — GENERATE queue (this census produced the INDEX only)

Per the feat-knowledge methodology, the census (this INDEX) precedes per-feature capture. NONE of the 9 GENERATE-recommended MCP features has a `.know/feat/{slug}.md` file yet — all are new GENERATE-queue items:
- `.know/feat/mcp-sidecar-server.md` — **MISSING / NEW**
- `.know/feat/mcp-auth-bridge.md` — **MISSING / NEW**
- `.know/feat/mcp-discovery-tools.md` — **MISSING / NEW**
- `.know/feat/mcp-query-tools.md` — **MISSING / NEW**
- `.know/feat/mcp-composite-write.md` — **MISSING / NEW** (highest priority — the write tier + all-or-nothing-honestly contract)
- `.know/feat/mcp-confirm-gate.md` — **MISSING / NEW**
- `.know/feat/mcp-tag-resolve.md` — **MISSING / NEW**
- `.know/feat/mcp-report-workflow-disclosure.md` — **MISSING / NEW**
- `.know/feat/mcp-observability.md` — **MISSING / NEW**

`mcp-match-business-stub` and `mcp-actor-attribution-seam` are SKIP — no per-feature file (no in-repo code to document).

