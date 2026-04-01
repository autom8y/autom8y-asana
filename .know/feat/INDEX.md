---
domain: feat/index
generated_at: "2026-04-01T14:30:00Z"
expires_after: "30d"
source_scope:
  - "./src/autom8_asana/**/*.py"
  - "./docs/**/*.md"
  - "./config/**/*.yaml"
  - "./.know/*.md"
generator: theoros
source_hash: "c213958"
confidence: 0.91
format_version: "1.0"
---

# Feature Census

> 32 features identified across 8 categories. 28 recommended for GENERATE, 4 recommended for SKIP.

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
- `README.md`: Featured in Quick Start as the primary user-facing object
- `docs/sdk-reference/client.md`: Dedicated SDK reference page

**Rationale**: The `AsanaClient` facade is the primary user-facing interface of the entire SDK. It has a dedicated SDK reference page, is featured in README Quick Start, and is the entry point through which all resource clients are composed. Multiple modules import it directly. All three GENERATE heuristics are met: user-facing interface, 10+ dependent files, multiple module dependencies. GENERATE.

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
- `src/autom8_asana/clients/`: 18 client files -- tasks, projects, sections, users, workspaces, webhooks, goals, portfolios, tags, stories, attachments, teams, custom_fields, batch, name_resolver, task_operations, task_ttl, goal_followers, goal_relationships
- `src/autom8_asana/clients/base.py`: `BaseClient` pattern shared by all resource clients
- `docs/sdk-reference/resource-clients.md`: Dedicated SDK reference page
- `docs/api-reference/endpoints/tasks.md`: REST API reference

**Rationale**: 18 client files with a shared base pattern, user-facing interface via REST API routes (tasks_router, projects_router, etc.), dedicated documentation. Multiple REST endpoints depend on these. GENERATE.

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
- `src/autom8_asana/transport/adaptive_semaphore.py`: AIMD adaptive concurrency control (halves concurrency on 429, increments on success)
- `src/autom8_asana/transport/config_translator.py`: Translates SDK config to rate limiter / circuit breaker / retry configs
- `src/autom8_asana/transport/response_handler.py`: Response envelope unwrapping
- `docs/runbooks/RUNBOOK-rate-limiting.md`: Dedicated operational runbook

**Rationale**: 6 transport files with cross-cutting concerns (rate limiting, circuit breaking, retry, AIMD semaphore). Dedicated runbook. Used by every resource client. GENERATE.

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
- `src/autom8_asana/models/`: 12+ model files -- task.py, project.py, section.py, user.py, webhook.py, goal.py, portfolio.py, custom_field.py, tag.py, story.py, team.py, workspace.py
- `docs/sdk-reference/models.md`: Dedicated SDK reference
- `docs/sdk-reference/exceptions.md`: SDK reference for exception hierarchy

**Rationale**: 12+ files, user-facing typed return values from every SDK call, dedicated SDK reference. The base `AsanaResource` class is imported by all domain models. GENERATE.

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
- `src/autom8_asana/persistence/session.py`: `SaveSession` context manager -- the unit of work implementation
- `src/autom8_asana/persistence/`: 20 files -- action_executor, action_ordering, actions, cascade, executor, graph, healing, holder_concurrency, holder_construction, holder_ensurer, pipeline, reorder, tracker, validation
- `docs/guides/save-session.md`: Full guide
- `docs/sdk-reference/persistence.md`: SDK reference
- `docs/runbooks/RUNBOOK-savesession-debugging.md`: Operational runbook
- `README.md`: Featured in Quick Start

**Rationale**: 20 implementation files, a dedicated guide, SDK reference, debugging runbook, and README Quick Start entry. Dependency ordering, healing, cascade execution -- a rich self-contained subsystem. GENERATE.

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
- `src/autom8_asana/cache/`: 52+ files across backends (memory, redis, s3), dataframe (build_coordinator, circuit_breaker, coalescer, warmer), integration (freshness_coordinator, staleness_coordinator, mutation_invalidator, hierarchy_warmer, schema_providers, stories, upgrader), models, policies, providers
- `docs/guides/cache-system.md`: Full guide
- `docs/runbooks/RUNBOOK-cache-troubleshooting.md`: Operational runbook

**Rationale**: 52+ implementation files, the single largest subsystem. Multiple backends (memory, Redis, S3), tiered caching, circuit breaker, coalescer, staleness detection, mutation invalidation. Dedicated guide and runbook. GENERATE.

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
- `src/autom8_asana/dataframes/`: builders (progressive, section, base), extractors, models (registry, schema, task_row), schemas (base, unit, contact, offer, asset_edit), views, resolver, cache_integration
- `docs/guides/dataframes.md`: Full guide
- `docs/api-reference/endpoints/dataframes.md`: REST API reference
- `src/autom8_asana/api/routes/dataframes.py`: User-facing `dataframes_router` endpoint

**Rationale**: 47+ source files, dedicated guide, API reference, user-facing REST endpoint. Polars-based with multiple extractor strategies and schema definitions per entity type. GENERATE.

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
- `src/autom8_asana/query/`: 18 files -- engine, compiler, fetcher, join, aggregator, temporal, timeline_provider, hierarchy, introspection, saved, formatters, guards, cli, models, offline_provider, data_service_entities
- `src/autom8_asana/api/routes/query.py`: User-facing `/rows` and `/aggregate` endpoints
- `docs/guides/entity-query.md`: Full guide
- `docs/api-reference/endpoints/query.md`: API reference
- `docs/guides/search-query-builder.md` and `search-cookbook.md`: Two dedicated search guides

**Rationale**: 18 implementation files, user-facing API endpoints, 3 documentation artifacts. Compiled predicate trees, cross-entity joins, aggregation, temporal queries, timeline queries, CLI interface. GENERATE.

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
- `src/autom8_asana/core/entity_registry.py`: `EntityDescriptor` and `EntityRegistry` -- singleton metadata store for 17+ entity descriptors
- `src/autom8_asana/core/project_registry.py`: Project GID registry
- `src/autom8_asana/core/registry_validation.py`: Cross-registry consistency validation

**Rationale**: 3 registry files but imported by virtually every domain module -- dataframes, cache integration, query engine, persistence, services. Described in architecture seed as "the single source of truth for entity configuration." Cross-cutting concern. GENERATE.

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
- `src/autom8_asana/models/business/`: 60+ files -- business, unit, contact, offer, process, location, hours, asset_edit, dna, descriptors, holder_factory, hydration, fields, mixins, activity, patterns
- `docs/guides/business-models.md`: Full guide
- `docs/sdk-reference/business-models.md`: SDK reference
- `docs/runbooks/RUNBOOK-business-model-navigation.md`: Runbook

**Rationale**: 60+ source files -- the largest domain model package. Multiple entity types (Business, Unit, Contact, Offer, Process, Location, Hours, AssetEdit, DNA), holder relationships, hydration. Dedicated guide, SDK reference, and runbook. GENERATE.

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
- `src/autom8_asana/models/business/detection/`: 8 files -- facade, tier1, tier2, tier3, tier4, config, types
- `docs/runbooks/RUNBOOK-detection-troubleshooting.md`: Dedicated runbook

**Rationale**: 8 implementation files with a tiered detection system (tiers 1-4) and dedicated troubleshooting runbook. Governs how Asana tasks are classified into business entity types -- a cross-cutting concern used by dataframe extractors, lifecycle, and persistence. GENERATE.

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
- `src/autom8_asana/models/business/matching/`: 6 files -- engine, blocking, comparators, normalizers, models, config
- `src/autom8_asana/api/routes/matching.py`: Hidden user-facing `POST /v1/matching/query` endpoint
- `src/autom8_asana/services/matching_service.py`: Matching service orchestration

**Rationale**: 6 implementation files plus a user-facing (hidden) REST endpoint and dedicated service. Blocking strategy, comparators, normalizers -- a standalone deduplication engine. Multiple modules use it (seeder, reconciliation, resolution). GENERATE.

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
- `src/autom8_asana/resolution/`: 8 files -- field_resolver, strategies, context, budget, result, selection, write_registry
- `src/autom8_asana/api/routes/resolver.py`: User-facing `POST /v1/resolve/{type}` endpoint
- `docs/guides/entity-resolution.md`: Full guide
- `docs/api-reference/endpoints/resolver.md`: API reference

**Rationale**: 8 implementation files, user-facing REST endpoint (resolver_router), dedicated guide, and API reference. Resolves phone+vertical pairs to Asana GIDs across entity types. GENERATE.

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
- `src/autom8_asana/lifecycle/`: 16 files -- engine, creation, completion, reopen, wiring, sections, init_actions, seeding, config, dispatch, webhook, webhook_dispatcher, observation, observation_store, loop_detector, startup
- `config/lifecycle_stages.yaml`: Data-driven pipeline DAG configuration with 10 stages
- `docs/guides/lifecycle-engine.md`: Full guide
- `docs/runbooks/RUNBOOK-pipeline-automation.md`: Runbook

**Rationale**: 16 implementation files (expanded from 12 in prior census), YAML-driven lifecycle DAG with 10 named stages, dedicated guide and runbook. Adds observation/observation_store, loop_detector, and webhook_dispatcher since prior census. GENERATE.

---

## intake-pipeline

| Field | Value |
|-------|-------|
| Name | Intake Business Creation Pipeline |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/api/routes/intake_create.py`: S2S JWT `POST /v1/intake/business` and `POST /v1/intake/process` endpoints
- `src/autom8_asana/api/routes/intake_resolve.py`: S2S JWT intake resolution routes
- `src/autom8_asana/api/routes/intake_custom_fields.py`: S2S JWT intake custom field write routes
- `src/autom8_asana/services/intake_create_service.py`: Business creation orchestration
- `src/autom8_asana/services/intake_resolve_service.py`: Intake resolution service
- `src/autom8_asana/services/intake_custom_field_service.py`: Custom field write service

**Rationale**: 20+ files across 3 dedicated routes, 3 dedicated services, and matching model files. User-facing S2S REST endpoints for business creation and process routing. The intake pipeline has its own distinct service layer, auth model (S2S JWT), and business logic for creating entities. GENERATE.

---

## payment-reconciliation

| Field | Value |
|-------|-------|
| Name | Payment Reconciliation Processing (Excel Output) |
| Category | Business Domain |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.88 |

**Source Evidence**:
- `src/autom8_asana/reconciliation/`: 6 files -- engine, executor, processor, report, section_registry
- `src/autom8_asana/lambda_handlers/payment_reconciliation.py`: Lambda handler for reconciliation workflow
- `src/autom8_asana/lambda_handlers/reconciliation_runner.py`: Reconciliation runner Lambda
- `src/autom8_asana/models/business/reconciliation.py`: Reconciliation domain model
- `src/autom8_asana/automation/workflows/payment_reconciliation/`: Dedicated automation workflow (formatter + workflow)

**Rationale**: 6 standalone reconciliation package files plus Lambda handler, runner, business model, and dedicated automation workflow. The `openpyxl` dependency in `pyproject.toml` exists specifically for Excel output in this feature. 11 total files across multiple packages. GENERATE.

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
- `src/autom8_asana/automation/`: 10 files -- engine, pipeline, context, base, config, seeding, templates, validation, waiter, events
- `src/autom8_asana/automation/workflows/`: pipeline_transition, section_resolution, bridge_base, mixins, registry, protocols
- `docs/guides/automation-pipelines.md`: Full guide
- `docs/guides/pipeline-automation-setup.md`: Setup guide
- `docs/runbooks/RUNBOOK-pipeline-automation.md`: Operational runbook

**Rationale**: 35+ implementation files total, two dedicated guides, one runbook. Contains the full automation rule engine, workflow registry, and concrete workflow implementations. GENERATE.

---

## data-attachment-bridge

| Field | Value |
|-------|-------|
| Name | Data Attachment Bridge (Backend-to-Asana Reporting Pipeline) |
| Category | Automation |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/automation/workflows/insights/workflow.py`: InsightsExportWorkflow -- 12-table HTML ads insights report to Offer attachments
- `src/autom8_asana/automation/workflows/conversation_audit/workflow.py`: ConversationAuditWorkflow -- SMS/conversation CSV export to ContactHolder attachments
- `src/autom8_asana/automation/workflows/mixins.py`: `AttachmentReplacementMixin` -- shared upload-first/delete-old pattern
- `src/autom8_asana/lambda_handlers/insights_export.py`: Lambda handler
- `src/autom8_asana/lambda_handlers/conversation_audit.py`: Lambda handler

**Rationale**: Cross-cutting architectural pattern: both InsightsExportWorkflow and ConversationAuditWorkflow share the same archetype (fetch from data backend, format as file, attach to Asana entity). Shared contract, shared mixin, shared Lambda factory. Understanding this pattern is essential for future reporting bridges. GENERATE.

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
- `src/autom8_asana/automation/events/`: 6 files -- emitter, envelope, rule, transport, types, config
- `pyproject.toml`: `events = ["autom8y-events>=0.1.0"]` optional dependency group

**Rationale**: 6 implementation files with its own types, envelope model, rules, and transport abstraction. The `autom8y-events` optional dependency exists specifically for this. Multiple modules use it post-save. GENERATE.

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
- `src/autom8_asana/automation/polling/`: 6 files -- scheduler, trigger_evaluator, action_executor, config_schema, config_loader, cli
- `config/rules/conversation-audit.yaml`: Declarative scheduling rule with cron-style scheduler and frequency
- `pyproject.toml`: `scheduler = ["apscheduler>=3.10.0"]` optional dependency

**Rationale**: 6 files, declarative YAML config schema, CLI interface, and dedicated optional dependency group. Operators configure rules in YAML that drive scheduled workflows. GENERATE.

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
- `src/autom8_asana/lifecycle/webhook_dispatcher.py`: Webhook dispatcher (new since prior census)
- `docs/guides/webhooks.md`: Full guide

**Rationale**: User-facing REST endpoint, management client, lifecycle dispatch + dispatcher, and dedicated guide. Token validation and loop prevention are documented. GENERATE.

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
- `src/autom8_asana/api/routes/entity_write.py`: `entity_write_router` -- `PATCH /api/v1/entity/{type}/{gid}`
- `src/autom8_asana/services/field_write_service.py`: Write orchestration
- `docs/guides/entity-write.md`: Full guide
- `docs/api-reference/endpoints/entity-write.md`: API reference

**Rationale**: User-facing REST endpoint, dedicated write service, guide, and API reference. Covers field resolution, coercion, and partial success patterns. GENERATE.

---

## business-metrics

| Field | Value |
|-------|-------|
| Name | Business Metrics Computation (MRR, Ad Spend) |
| Category | User-Facing API |
| Complexity | MEDIUM |
| Recommendation | **GENERATE** |
| Confidence | 0.90 |

**Source Evidence**:
- `src/autom8_asana/metrics/`: 7 files -- compute, registry, metric, expr, resolve, definitions/
- `src/autom8_asana/metrics/definitions/`: metric definitions (offer.py defining `active_mrr` and `active_ad_spend`)
- `src/autom8_asana/metrics/__main__.py`: CLI compute entry point

**Rationale**: 7 implementation files, registered metric definitions (MRR, ad spend), expression DSL, and a standalone CLI compute entry point. The registry pattern makes this an extensible subsystem. GENERATE.

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
- `src/autom8_asana/api/`: 35+ files -- main, lifespan, startup, dependencies, middleware (idempotency, core), client_pool, rate_limit, health_models, metrics, errors, preload (legacy + progressive), all route modules
- `src/autom8_asana/entrypoint.py`: Dual-mode entrypoint that starts uvicorn for ECS mode
- `docker-compose.yml`: Docker deployment artifact
- `Dockerfile`: Container build artifact
- `pyproject.toml`: `api = ["fastapi>=0.115.0", "autom8y-api-schemas>=1.5.0", "uvicorn[standard]>=0.27.0", "slowapi>=0.1.9"]` optional dependency group

**Rationale**: 35+ implementation files, 19 registered routers, middleware stack (CORS, rate limiting, idempotency, request logging, request ID), startup/lifespan handling, Docker deployment artifacts. GENERATE.

---

## lambda-handlers

| Field | Value |
|-------|-------|
| Name | AWS Lambda Function Handlers |
| Category | Infrastructure |
| Complexity | HIGH |
| Recommendation | **GENERATE** |
| Confidence | 0.95 |

**Source Evidence**:
- `src/autom8_asana/lambda_handlers/`: 13 handler files -- cache_warmer, cache_invalidate, cloudwatch, checkpoint, workflow_handler, insights_export, conversation_audit, payment_reconciliation, pipeline_stage_aggregator, push_orchestrator, reconciliation_runner, story_warmer, timeout
- `src/autom8_asana/entrypoint.py`: Lambda mode detection via `AWS_LAMBDA_RUNTIME_API` env var
- `pyproject.toml`: `lambda = ["awslambdaric>=2.2.0"]` optional dependency group

**Rationale**: 13 Lambda handler files (up from 7 in prior census), dual-mode entrypoint selects Lambda mode at runtime, dedicated optional dependency group. Handlers cover cache warming, invalidation, CloudWatch metrics, checkpoint writes, workflow dispatch, pipeline stage aggregation, GID push, and story warming. GENERATE.

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
- `src/autom8_asana/auth/`: 5 files -- jwt_validator, bot_pat, dual_mode, service_token, audit
- `docs/guides/authentication.md`: Full guide
- `pyproject.toml`: `auth = ["autom8y-auth[observability]>=2.0.0"]` optional dependency group

**Rationale**: 5 implementation files, dedicated guide, and dedicated optional dependency group. Four authentication strategies (JWT, BotPAT, DualMode, ServiceToken) plus an audit module. GENERATE.

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
- `src/autom8_asana/observability/`: 3 files -- context, correlation, decorators
- `src/autom8_asana/api/metrics.py`: API-level Prometheus metrics
- `src/autom8_asana/protocols/observability.py`: Protocol definition for observability hooks
- `src/autom8_asana/lambda_handlers/cloudwatch.py`: CloudWatch metrics emission Lambda
- `pyproject.toml`: `autom8y-telemetry[aws,fastapi,otlp]>=0.6.0` and `autom8y-events` dependencies

**Rationale**: 3 implementation files plus protocol definitions, API metrics module, and dedicated CloudWatch Lambda handler. Correlation ID tracking is a cross-cutting concern. GENERATE.

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
- `src/autom8_asana/clients/data/`: 14 files -- client, config, models, README, endpoints (batch, export, insights, reconciliation, simple)
- `docs/contracts/openapi-data-service-client.yaml`: OpenAPI contract for data service
- `src/autom8_asana/automation/workflows/insights/workflow.py`: Workflow consuming insights data

**Rationale**: 14 implementation files, cross-service client with its own OpenAPI contract, batch requests, circuit breaker, retry behavior, emergency kill switch. Consumed by insights export workflow and business model integration. GENERATE.

---

## query-cli

| Field | Value |
|-------|-------|
| Name | autom8-query CLI Tool |
| Category | Tooling |
| Complexity | LOW |
| Recommendation | **GENERATE** |
| Confidence | 0.85 |

**Source Evidence**:
- `src/autom8_query_cli.py`: CLI entry point
- `pyproject.toml`: `[project.scripts] autom8-query = "autom8_query_cli:main"` entry point registration
- `src/autom8_asana/query/cli.py`: CLI implementation within query package

**Rationale**: Registered CLI entry point in `pyproject.toml`, user-facing command. Though only a few files, this is the project's explicitly registered command-line tool and qualifies by the user-facing interface heuristic. GENERATE.

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
- `src/autom8_asana/batch/`: 2 files -- client, models (plus __init__.py)

**Rationale**: Only 2 implementation files. The Batch API client is a thin wrapper used internally by `SaveSession` to submit chunked operations to Asana's batch endpoint. No direct user-facing interface surface; it is an implementation detail of the persistence layer. Fewer than 5 files, no decision records, pure utility. SKIP.

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
- `src/autom8_asana/search/`: 2 files -- service, models

**Rationale**: Only 2 implementation files. The search service wraps the query engine for a specific access pattern. Overlaps significantly with the `query-engine` feature. It is a thin service facade with no dedicated guide or decision records. SKIP.

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
- `docs/sdk-reference/configuration.md`: SDK reference
- `README.md`: Environment variable table

**Rationale**: Single file. While environment configuration spans ~85 variables and is well-documented, it is a pure utility/infrastructure concern with no cross-cutting behavior of its own. Settings is a dependency of every feature, not a feature itself. SKIP.

---

## protocol-di-layer

| Field | Value |
|-------|-------|
| Name | Protocol / Dependency Injection Layer |
| Category | Core Platform |
| Complexity | LOW |
| Recommendation | **SKIP** |
| Confidence | 0.85 |

**Source Evidence**:
- `src/autom8_asana/protocols/`: 8 files -- auth, cache, dataframe_provider, insights, item_loader, log, metrics, observability
- `docs/sdk-reference/protocols.md`: SDK reference

**Rationale**: 8 files defining PEP 544 Protocol structural interfaces with no executable logic. These are structural primitives (DI boundary definitions), not features themselves. The test-coverage knowledge file explicitly notes "absence of tests is expected and correct." SKIP.

---

## Census Gaps

1. **Business Seeder boundary**: `models/business/` does not have a standalone `seeder.py` visible at this scan, but `automation/seeding.py` and `lifecycle/seeding.py` both handle seeding logic. The relationship between them is partially unclear -- may warrant a distinct `business-seeder` feature if seeding has its own knowledge surface.

2. **Section Timeline feature**: `services/section_timeline_service.py` and `api/routes/section_timelines.py` form a distinct endpoint group (`/api/v1/offers` prefix, PAT auth). This is small (2-3 files) and was subsumed under `resource-clients` and `dataframe-layer`, but the offer timeline pattern may warrant separation if it grows.

3. **New Lambda handlers not in prior census**: 6 new handlers (pipeline_stage_aggregator, push_orchestrator, reconciliation_runner, story_warmer, timeout, checkpoint) were subsumed under `lambda-handlers`. The pipeline_stage_aggregator and push_orchestrator appear to be related to a GID push / pipeline counting subsystem that may be its own distinct feature as the codebase evolves.

4. **`patterns/` package**: Only 2 files observed. Contents confirm `async_method.py` and `error_classification.py` -- shared behavioral patterns. Subsumed under `save-session` and general conventions; too thin for a standalone feature entry.

5. **`_defaults/` standalone providers**: `EnvAuthProvider`, `NullCacheProvider`, `DefaultLogProvider`, `NullObservabilityHook` in `_defaults/` are subsumed under `authentication` and `cache-subsystem` respectively. These could form a distinct "SDK Standalone Mode" feature if the protocol/DI surface is documented separately.

6. **No ADRs found**: The `docs/` directory has no `decisions/` or `adr/` subdirectory at filesystem level. Feature decisions are embedded in runbooks and guide documents rather than formal ADR files. This criterion source category is confirmed absent (not a scan gap).
