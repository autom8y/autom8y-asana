---
domain: feat/index
generated_at: "2026-03-18T12:26:10Z"
expires_after: "30d"
source_scope:
  - "./src/autom8_asana/**/*.py"
  - "./docs/**/*.md"
  - "./config/**/*.yaml"
  - "./examples/*.py"
  - "./.know/*.md"
generator: theoros
source_hash: "2c604fa"
confidence: 0.93
format_version: "1.0"
---

# Feature Census

> 26 features identified across 7 categories. 23 recommended for GENERATE, 3 recommended for SKIP.

---

## data-attachment-bridge

| Field | Value |
|-------|-------|
| Name | Data Attachment Bridge (Backend-to-Asana Reporting Pipeline) |
| Category | Cross-Cutting Pattern |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/automation/workflows/conversation_audit.py`: ConversationAuditWorkflow -- SMS/conversation CSV export to ContactHolder attachments
- `src/autom8_asana/automation/workflows/insights_export.py`: InsightsExportWorkflow -- 12-table HTML ads insights report to Offer attachments
- `src/autom8_asana/automation/workflows/mixins.py`: AttachmentReplacementMixin -- shared upload-first/delete-old pattern
- `src/autom8_asana/automation/workflows/base.py`: WorkflowAction ABC -- shared contract (enumerate, execute, validate)
- `src/autom8_asana/automation/workflows/insights_formatter.py`: HTML report composition
- `src/autom8_asana/automation/workflows/insights_tables.py`: TABLE_SPECS -- 12 table definitions with DispatchType
- `src/autom8_asana/lambda_handlers/workflow_handler.py`: WorkflowHandlerConfig + create_workflow_handler() factory
- `src/autom8_asana/lambda_handlers/insights_export.py`: Lambda handler for insights workflow
- `src/autom8_asana/lambda_handlers/conversation_audit.py`: Lambda handler for conversation workflow
- `src/autom8_asana/clients/data/client.py`: DataServiceClient -- shared data source for both workflows
- `src/autom8_asana/core/scope.py`: EntityScope -- cross-cutting invocation contract

**Rationale**: This is a cross-cutting architectural pattern, not a single package. Both InsightsExportWorkflow and ConversationAuditWorkflow implement the same archetype: fetch data from autom8_data backend service, format as file (HTML/CSV), and attach to Asana entity holders. They share WorkflowAction contract, AttachmentReplacementMixin, create_workflow_handler() Lambda factory, EntityScope targeting, DataServiceClient dependency, circuit breaker + kill switch validation, and WorkflowResult reporting. Understanding this shared pattern is essential for adding future reporting bridges. GENERATE.

---

## sdk-client-facade

| Field | Value |
|-------|-------|
| Name | AsanaClient SDK Facade |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/client.py`: Primary SDK entry point, `AsanaClient` class with lazy-initialized resource clients, thread-safe via double-checked locking, sync/async support
- `src/autom8_asana/__init__.py`: Exports `AsanaClient` as top-level public API surface
- `README.md`: Featured in Quick Start — described as the primary user-facing object
- `docs/sdk-reference/client.md`: Dedicated SDK reference page

**Rationale**: The `AsanaClient` facade is the primary user-facing interface of the entire SDK. It has a dedicated SDK reference page, is featured prominently in README and guides, and is the entry point through which all resource clients are composed. Multiple modules depend on it. GENERATE is unambiguous.

---

## http-transport

| Field | Value |
|-------|-------|
| Name | Asana HTTP Transport Layer |
| Category | Core Platform |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/transport/asana_http.py`: `AsanaHttpClient` wrapping `autom8y_http`, Asana-specific response unwrapping
- `src/autom8_asana/transport/adaptive_semaphore.py`: Adaptive concurrency control
- `src/autom8_asana/transport/config_translator.py`: Translates SDK config to rate limiter / circuit breaker / retry configs
- `src/autom8_asana/transport/response_handler.py`: Response envelope unwrapping

**Rationale**: 6 transport files with cross-cutting concerns (rate limiting, circuit breaking, retry, semaphore). The transport layer is referenced in data flow documentation and the `runbooks/RUNBOOK-rate-limiting.md` exists as a standalone operational document. User-facing impact through rate limit behavior. GENERATE.

---

## resource-clients

| Field | Value |
|-------|-------|
| Name | Asana Resource Clients |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.96 |

**Source Evidence**:
- `src/autom8_asana/clients/`: 17 client files covering tasks, projects, sections, users, workspaces, webhooks, goals, portfolios, tags, stories, attachments, teams, custom_fields, batch
- `src/autom8_asana/clients/base.py`: `BaseClient` pattern shared by all 13+ resource clients
- `docs/sdk-reference/resource-clients.md`: Dedicated SDK reference page
- `docs/api-reference/endpoints/tasks.md`: REST API reference

**Rationale**: 17 client files with a shared base pattern, user-facing interface via REST API routes (`tasks_router`, `projects_router`, etc.), dedicated documentation, and multiple guide references. GENERATE.

---

## asana-models

| Field | Value |
|-------|-------|
| Name | Pydantic v2 Asana Resource Models |
| Category | Core Platform |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/models/`: 15+ model files — `task.py`, `project.py`, `section.py`, `user.py`, `webhook.py`, `goal.py`, `portfolio.py`, `custom_field.py`, `custom_field_accessor.py`, `tag.py`, `story.py`, `team.py`, `workspace.py`
- `docs/sdk-reference/models.md`: Dedicated SDK reference
- `docs/reference/REF-custom-field-catalog.md`: 108 custom fields across 5 models

**Rationale**: Extensive model coverage (15+ files), user-facing in that they are the typed return values from every SDK call. Custom field catalog reference document with 108 fields demonstrates deep decision investment. GENERATE.

---

## save-session

| Field | Value |
|-------|-------|
| Name | SaveSession Unit of Work Pattern |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.98 |

**Source Evidence**:
- `src/autom8_asana/persistence/session.py`: `SaveSession` context manager — the unit of work implementation
- `src/autom8_asana/persistence/`: 20 files — action_executor, action_ordering, actions, cascade, executor, graph, healing, holder_concurrency, holder_construction, holder_ensurer, pipeline, reorder, tracker, validation
- `docs/guides/save-session.md`: Full guide
- `docs/sdk-reference/persistence.md`: SDK reference
- `docs/reference/REF-savesession-lifecycle.md`: Lifecycle reference
- `runbooks/RUNBOOK-savesession-debugging.md`: Operational runbook

**Rationale**: 20 implementation files, a dedicated guide, SDK reference, lifecycle reference doc, and a debugging runbook. Featured in README Quick Start. Dependency ordering, healing, cascade execution — a rich self-contained subsystem. GENERATE.

---

## cache-subsystem

| Field | Value |
|-------|-------|
| Name | Multi-Tier Intelligent Cache Subsystem |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.99 |

**Source Evidence**:
- `src/autom8_asana/cache/`: 52 files across backends (memory, redis, s3), dataframe (build_coordinator, circuit_breaker, coalescer, warmer), integration (freshness_coordinator, staleness_coordinator, mutation_invalidator, hierarchy_warmer), models, policies, providers
- `docs/guides/cache-system.md`: Full guide
- `docs/reference/REF-cache-architecture.md`, `REF-cache-staleness-detection.md`, `REF-cache-ttl-strategy.md`, `REF-cache-provider-protocol.md`, `REF-cache-invalidation.md`, `REF-cache-patterns.md`: Six dedicated reference docs
- `runbooks/RUNBOOK-cache-troubleshooting.md`: Operational runbook

**Rationale**: 52 implementation files, six reference documents, one guide, one runbook. The single largest subsystem by file count. Multiple backends, tiered caching, circuit breaker, coalescer, staleness detection, mutation invalidation — all documented extensively. GENERATE.

---

## dataframe-layer

| Field | Value |
|-------|-------|
| Name | Polars DataFrame Analytics Layer |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/dataframes/`: 47 files — builders (progressive, section, base), extractors, models (registry, schema, task_row), schemas (base, unit, contact, offer, asset_edit), views, resolver
- `docs/guides/dataframes.md`: Full guide
- `docs/api-reference/endpoints/dataframes.md`: REST API reference
- `src/autom8_asana/api/routes/dataframes.py`: User-facing `dataframes_router` endpoint

**Rationale**: 47 source files, dedicated guide, API reference, user-facing REST endpoint. Polars-based with multiple extractor strategies and schema definitions for each entity type. GENERATE.

---

## query-engine

| Field | Value |
|-------|-------|
| Name | DataFrame Query Engine with Compiled Predicates |
| Category | Core Platform |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/query/`: 19 files — engine, compiler, fetcher, join, aggregator, temporal, timeline_provider, hierarchy, introspection, saved, formatters, guards, cli
- `src/autom8_asana/api/routes/query.py`: User-facing `/rows` and `/aggregate` endpoints
- `docs/guides/entity-query.md`: Full guide
- `docs/api-reference/endpoints/query.md`: API reference
- `docs/guides/search-query-builder.md` and `search-cookbook.md`: Two dedicated search guides

**Rationale**: 19 implementation files, user-facing API endpoints, 3 documentation artifacts. Includes compiled predicate trees, cross-entity joins, aggregation, temporal queries, timeline queries, CLI interface. GENERATE.

---

## business-domain-model

| Field | Value |
|-------|-------|
| Name | Business Domain Entity Model |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.98 |

**Source Evidence**:
- `src/autom8_asana/models/business/`: 60 files — business, unit, contact, offer, process, location, hours, asset_edit, videography, dna, descriptors, holder_factory, hydration, reconciliation, seeder, activity, section_timeline, fields, mixins
- `docs/guides/business-models.md`: Full guide
- `docs/sdk-reference/business-models.md`: SDK reference
- `docs/reference/REF-entity-type-table.md`, `REF-entity-lifecycle.md`: Reference docs
- `runbooks/RUNBOOK-business-model-navigation.md`: Runbook

**Rationale**: 60 source files — the largest domain model package. Multiple entity types (Business, Unit, Contact, Offer, Process, Location, Hours, AssetEdit, Videography, DNA), holder relationships, hydration, reconciliation, and seeding. Dedicated guide, SDK reference, two reference docs, and a runbook. GENERATE.

---

## entity-detection

| Field | Value |
|-------|-------|
| Name | Multi-Tier Entity Type Detection |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/models/business/detection/`: 8 files — facade, tier1, tier2, tier3, tier4, config, types
- `docs/reference/REF-detection-tiers.md`: 5-tier detection system specification
- `runbooks/RUNBOOK-detection-troubleshooting.md`: Dedicated runbook
- `scripts/diagnostic_tier1_detection.py`: Diagnostic tooling

**Rationale**: 8 implementation files with a dedicated reference spec, troubleshooting runbook, and diagnostic script. The detection system is explicitly tiered (tiers 1-4) and governs how Asana tasks are classified into business entity types — a cross-cutting concern used by dataframe extractors, lifecycle, and persistence. GENERATE.

---

## fuzzy-entity-matching

| Field | Value |
|-------|-------|
| Name | Fuzzy Matching Engine for Entity Deduplication |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/models/business/matching/`: 7 files — engine, blocking, comparators, normalizers, models, config
- `docs/reference/REF-seeder-matching-config.md`: Seeder matching configuration reference

**Rationale**: 7 implementation files with a dedicated reference document. Blocking strategy, comparators, normalizers — a standalone deduplication engine with its own config schema. Multiple modules use it (seeder, reconciliation). GENERATE.

---

## entity-resolution

| Field | Value |
|-------|-------|
| Name | Entity Resolution (Phone+Vertical to GID) |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.96 |

**Source Evidence**:
- `src/autom8_asana/resolution/`: 8 files — field_resolver, strategies, context, budget, result, selection, write_registry
- `src/autom8_asana/api/routes/resolver.py`: User-facing `POST /v1/resolve/{type}` endpoint
- `docs/guides/entity-resolution.md`: Full guide
- `docs/api-reference/endpoints/resolver.md`: API reference
- `examples/04-entity-resolution.py`: Runnable example

**Rationale**: 8 implementation files, user-facing REST endpoint, dedicated guide, API reference doc, and a runnable example. Resolves phone+vertical pairs to Asana GIDs across entity types. GENERATE.

---

## lifecycle-engine

| Field | Value |
|-------|-------|
| Name | Entity Lifecycle Pipeline (4-Phase Transition Engine) |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.98 |

**Source Evidence**:
- `src/autom8_asana/lifecycle/`: 12 files — engine, creation, completion, reopen, wiring, sections, init_actions, seeding, config, dispatch, webhook
- `config/lifecycle_stages.yaml`: Data-driven pipeline DAG configuration with 10 stages (outreach, sales, onboarding, implementation, retention, reactivation, expansion, account_error, month1)
- `docs/guides/lifecycle-engine.md`: Full guide
- `docs/reference/REF-entity-lifecycle.md`: Reference doc
- `runbooks/RUNBOOK-pipeline-automation.md`: Runbook
- `examples/07-lifecycle-transition.py`: Runnable example

**Rationale**: 12 implementation files, YAML-driven lifecycle DAG with 10 named stages, dedicated guide, reference doc, runbook, and a runnable example. The lifecycle engine is triggered by webhook events and coordinates creation, seeding, wiring, and init actions. GENERATE.

---

## automation-engine

| Field | Value |
|-------|-------|
| Name | Automation Rule Engine and Workflow Orchestration |
| Category | Automation |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.97 |

**Source Evidence**:
- `src/autom8_asana/automation/`: 35 files — engine, pipeline, context, base, config, seeding, templates, validation, waiter
- `src/autom8_asana/automation/workflows/`: pipeline_transition, insights_export, conversation_audit, section_resolution, registry
- `docs/guides/automation-pipelines.md`: Full guide
- `docs/guides/pipeline-automation-setup.md`: Setup guide
- `runbooks/RUNBOOK-pipeline-automation.md`: Operational runbook

**Rationale**: 35 implementation files, two dedicated guides, one runbook. Contains the full automation rule engine, workflow registry, and 3 concrete workflow implementations (pipeline transition, insights export, conversation audit). GENERATE.

---

## event-emission

| Field | Value |
|-------|-------|
| Name | Async Event Emission Pipeline |
| Category | Automation |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/automation/events/`: 6 files — emitter, envelope, rule, transport, types, config
- `tests/integration/events/`: Integration test coverage exists
- `docs/guides/automation-pipelines.md`: Mentions event emission within the automation context

**Rationale**: 6 implementation files with integration test coverage. The event subsystem is an independently structured sub-package within automation with its own types, envelope model, rules, and transport abstraction. Multiple modules depend on it post-save. GENERATE.

---

## polling-scheduler

| Field | Value |
|-------|-------|
| Name | Polling-Based Automation Scheduler |
| Category | Automation |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/automation/polling/`: 7 files — polling_scheduler, trigger_evaluator, action_executor, config_schema, config_loader, cli
- `config/rules/conversation-audit.yaml`: Declarative scheduling rule with cron-style `scheduler.time` and `frequency: weekly`
- `tests/integration/automation/polling/`: Integration tests exist

**Rationale**: 7 files, declarative YAML config schema, CLI interface, and integration tests. The polling scheduler is a user-facing automation surface — operators configure rules in YAML that drive scheduled workflows. GENERATE.

---

## webhooks

| Field | Value |
|-------|-------|
| Name | Asana Webhook Inbound Event Processing |
| Category | User-Facing API |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/api/routes/webhooks.py`: `webhooks_router` for inbound webhook events
- `src/autom8_asana/clients/webhooks.py`: Webhook management client
- `src/autom8_asana/lifecycle/webhook.py`: Webhook event-to-lifecycle dispatch
- `docs/guides/webhooks.md`: Full guide
- `examples/10-webhook-handler.py`: Runnable example

**Rationale**: User-facing REST endpoint, management client, lifecycle dispatch, dedicated guide, and a runnable example. Token validation and loop prevention are documented. GENERATE.

---

## entity-write-api

| Field | Value |
|-------|-------|
| Name | Entity Write API (Field Coercion and Partial Success) |
| Category | User-Facing API |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/api/routes/entity_write.py`: `entity_write_router` — `PATCH /api/v1/entity/{type}/{gid}`
- `src/autom8_asana/services/field_write_service.py`: Write orchestration
- `docs/guides/entity-write.md`: Full guide
- `docs/api-reference/endpoints/entity-write.md`: API reference
- `examples/05-entity-write.py`: Runnable example

**Rationale**: User-facing REST endpoint, dedicated write service, guide, API reference, and a runnable example. Covers field resolution, coercion, and partial success patterns. GENERATE.

---

## fastapi-server

| Field | Value |
|-------|-------|
| Name | FastAPI HTTP Server (ECS Mode) |
| Category | Infrastructure |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.96 |

**Source Evidence**:
- `src/autom8_asana/api/`: 35 files — main, lifespan, startup, dependencies, middleware, client_pool, rate_limit, health_models, metrics, errors, preload (legacy + progressive), all route modules
- `src/autom8_asana/entrypoint.py`: Dual-mode entrypoint that starts uvicorn for ECS mode
- `docker/`, `docker-compose.yml`, `Dockerfile`: Deployment artifacts

**Rationale**: 35 implementation files, 15+ registered routes, middleware stack (CORS, rate limiting, request logging, request ID, metrics), startup/lifespan handling, Docker deployment artifacts. The primary API serving mode of the system. GENERATE.

---

## lambda-handlers

| Field | Value |
|-------|-------|
| Name | AWS Lambda Function Handlers |
| Category | Infrastructure |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/lambda_handlers/`: 7 handlers — cache_warmer, cache_invalidate, cloudwatch, checkpoint, workflow_handler, insights_export, conversation_audit
- `src/autom8_asana/entrypoint.py`: Lambda mode detection via `AWS_LAMBDA_RUNTIME_API` env var
- `examples/09-cache-warming.py`: Runnable example

**Rationale**: 7 Lambda handler files, the dual-mode entrypoint selects Lambda mode at runtime, and there is a runnable cache warming example. The handlers cover cache warming, invalidation, CloudWatch metrics emission, checkpoint writes, and workflow dispatch. GENERATE.

---

## authentication

| Field | Value |
|-------|-------|
| Name | Authentication (JWT / BotPAT / DualMode / S2S) |
| Category | Infrastructure |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/auth/`: 6 files — jwt_validator, bot_pat, dual_mode, service_token, audit
- `docs/guides/authentication.md`: Full guide
- `docs/api-reference/README.md`: Auth section in API reference overview

**Rationale**: 6 implementation files, a dedicated guide, and API reference coverage. Four authentication strategies (JWT, BotPAT, DualMode, ServiceToken) plus an audit module. GENERATE.

---

## observability

| Field | Value |
|-------|-------|
| Name | Observability (Correlation IDs, Metrics, Telemetry) |
| Category | Infrastructure |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/observability/`: 4 files — context, correlation, decorators
- `src/autom8_asana/api/metrics.py`: API-level metrics
- `src/autom8_asana/protocols/observability.py`, `protocols/metrics.py`: Protocol definitions for observability hooks
- `src/autom8_asana/lambda_handlers/cloudwatch.py`: CloudWatch metrics emission Lambda handler

**Rationale**: 4 implementation files plus protocol definitions, API metrics module, and a dedicated Lambda handler for CloudWatch metrics. Correlation ID tracking is a cross-cutting concern referenced throughout the codebase. GENERATE.

---

## data-service-client

| Field | Value |
|-------|-------|
| Name | autom8_data Satellite Service Client (Ad Performance Insights) |
| Category | Infrastructure |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/clients/data/`: 14 files — client, config, models, README, endpoints (batch, export, insights, reconciliation, simple)
- `src/autom8_asana/clients/data/README.md`: Full API documentation with 14 factory types, period values, circuit breaker, retry behavior
- `src/autom8_asana/automation/workflows/insights_export.py`: Workflow consuming insights data

**Rationale**: 14 implementation files, a comprehensive README documenting 14 factory types, batch requests, circuit breaker, retry behavior, and emergency kill switch. Cross-cutting use via insights export workflow and business model integration. GENERATE.

---

## business-metrics

| Field | Value |
|-------|-------|
| Name | Business Metrics Computation (MRR, Ad Spend) |
| Category | Business Domain |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/metrics/`: 7 files — compute, registry, metric, expr, resolve, definitions/offer.py
- `src/autom8_asana/metrics/definitions/offer.py`: Defines `active_mrr` and `active_ad_spend` metrics with Polars expressions
- `scripts/calc_mrr.py`: Standalone script for MRR calculation

**Rationale**: 7 implementation files, registered metric definitions (MRR, ad spend), and a standalone diagnostic script. The registry pattern and expression DSL make this an extensible subsystem. GENERATE.

---

## entity-registry

| Field | Value |
|-------|-------|
| Name | EntityRegistry (Descriptor-Driven Entity Metadata) |
| Category | Core Platform |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.92 |

**Source Evidence**:
- `src/autom8_asana/core/entity_registry.py`: `EntityDescriptor` and `EntityRegistry` — singleton metadata store for 17 entity descriptors
- `src/autom8_asana/core/`: Multiple consumers — `ConcurrencyUtils`, `RetryUtils`, `SystemContext`
- Architecture seed notes: "The single source of truth for entity knowledge: schema paths, extractor paths, row model paths, cache TTLs, join keys, holder relationships"

**Rationale**: 1 file but imported by virtually every domain module — dataframes, cache integration, query engine, persistence, services. Described in architecture as a key design pattern. Cross-cutting concern. GENERATE.

---

## batch-api-client

| Field | Value |
|-------|-------|
| Name | Asana Batch API Client |
| Category | Core Platform |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.75 |

**Source Evidence**:
- `src/autom8_asana/batch/`: 3 files — client, models
- `docs/reference/REF-batch-operations.md`: Reference doc

**Rationale**: Only 3 implementation files. The Batch API client is a thin wrapper used internally by `SaveSession` to submit chunked operations to Asana's batch endpoint. No direct user-facing interface surface; it is an implementation detail of the persistence layer. Reference doc exists but the surface is narrow. SKIP.

---

## search-service

| Field | Value |
|-------|-------|
| Name | Search Service over Cached DataFrames |
| Category | Core Platform |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.72 |

**Source Evidence**:
- `src/autom8_asana/search/`: 3 files — service, models
- `docs/reference/REF-search-api.md`: Reference doc

**Rationale**: Only 3 files. The search service wraps the query engine for a specific access pattern — no distinct decision records, no dedicated guide. The reference doc exists, but this feature overlaps significantly with the `query-engine` feature. It is a thin service facade rather than a distinct feature. SKIP.

---

## settings-configuration

| Field | Value |
|-------|-------|
| Name | Pydantic Settings and Environment Configuration |
| Category | Infrastructure |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.80 |

**Source Evidence**:
- `src/autom8_asana/settings.py`: `Settings` singleton with 10 sub-settings groups
- `docs/reference/env-vars.md`: ~85 environment variables
- `docs/sdk-reference/configuration.md`: SDK reference

**Rationale**: While environment configuration spans ~85 variables and is well-documented, it is a pure utility/infrastructure concern with no cross-cutting behavior of its own. Settings is a dependency of every other feature, not a feature itself. SKIP.

---

## Census Gaps

1. **Business Seeder vs. Lifecycle Seeding boundary**: `models/business/seeder.py`, `automation/seeding.py`, and `lifecycle/seeding.py` all involve seeding logic. The relationship between them is partially unclear -- this may warrant a distinct `business-seeder` feature entry, but it was consolidated under `automation-engine` and `lifecycle-engine` due to ambiguity.

2. **Section Timeline feature**: `services/section_timeline_service.py` and `api/routes/section_timelines.py` form a distinct endpoint, but it appears to be a narrow query surface over the business model. No dedicated guide or ADR was found. It is covered under `resource-clients` and `dataframe-layer` but may deserve separate enumeration.

3. **Protocol/DI layer**: `protocols/` contains 8 protocol files defining the dependency injection surface. These are structural primitives, not features, and were intentionally excluded from the census.

4. **`_defaults/` standalone providers**: `EnvAuthProvider`, `SecretsManagerAuthProvider`, `NullCacheProvider` in `_defaults/` are standalone SDK usage utilities. They were subsumed under `authentication` and `cache-subsystem` but could be considered a distinct "SDK Standalone Mode" feature.

5. **ADR/TDD coverage not scanned in depth**: The `docs/decisions/` directory had no files (confirmed empty -- ADRs are listed in `docs/INDEX.md` as being in `docs/decisions/` and `docs/adr/` directories, which were not present in the filesystem scan). This represents a documentation/filesystem inconsistency.
