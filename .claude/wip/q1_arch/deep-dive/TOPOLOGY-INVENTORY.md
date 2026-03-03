# Topology Inventory: autom8y-asana

**Analysis Unit**: directory (single repo, subsystem-level boundaries)
**Repo Path**: `/Users/tomtenuta/Code/autom8y-asana`
**Source Root**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana`
**Date**: 2026-02-23
**Complexity**: DEEP-DIVE

---

## 1. Service Catalog

### 1.1 Overall Classification

**autom8y-asana** is an async-first Python SDK and API service for Asana, purpose-built for CRM/pipeline automation at business-unit scale. It operates in two deployment modes:

- **ECS Mode**: FastAPI server via uvicorn (port 8000)
- **Lambda Mode**: AWS Lambda handlers via awslambdaric

**Classification**: Platform SDK + API Service (dual-mode)
**Confidence**: High (explicit in pyproject.toml, Dockerfile, entrypoint.py)

### 1.2 Codebase Dimensions

| Metric | Value |
|--------|-------|
| Total source Python files | 402 |
| Total source LOC | ~115,743 |
| Total test Python files | 461 |
| Total test LOC | ~216,677 |
| Top-level directories | 22 |
| Root-level Python modules | 6 (client.py, config.py, entrypoint.py, exceptions.py, settings.py, __init__.py) |
| Root-level LOC | 3,476 |

### 1.3 Directory Unit Catalog

Each top-level directory under `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/` is classified below. Classification taxonomy: **subsystem**, **component**, **layer**, **module**, **utility**.

| # | Directory | Classification | Files | LOC | Sub-dirs | Confidence |
|---|-----------|---------------|-------|-----|----------|------------|
| 1 | `api/` | **Layer** (HTTP API surface) | 35 | 9,323 | `preload/`, `routes/` | High |
| 2 | `automation/` | **Subsystem** (rule-based automation) | 34 | 10,768 | `events/`, `polling/`, `workflows/` | High |
| 3 | `batch/` | **Module** (bulk API operations) | 3 | 684 | -- | High |
| 4 | `cache/` | **Subsystem** (multi-tier caching) | 53 | 16,103 | `backends/`, `dataframe/`, `integration/`, `models/`, `policies/`, `providers/` | High |
| 5 | `clients/` | **Layer** (Asana API resource clients) | 36 | 11,729 | `data/` | High |
| 6 | `core/` | **Layer** (foundational shared primitives) | 16 | 3,247 | -- | High |
| 7 | `dataframes/` | **Subsystem** (Polars DataFrame extraction) | 45 | 13,917 | `builders/`, `extractors/`, `models/`, `resolver/`, `schemas/`, `views/` | High |
| 8 | `lambda_handlers/` | **Component** (AWS Lambda entry points) | 8 | 2,249 | -- | High |
| 9 | `lifecycle/` | **Subsystem** (canonical pipeline engine) | 12 | 3,898 | -- | High |
| 10 | `metrics/` | **Module** (declarative metric computation) | 8 | 621 | `definitions/` | High |
| 11 | `models/` | **Subsystem** (Pydantic domain models) | 60 | 15,482 | `business/`, `contracts/` | High |
| 12 | `observability/` | **Utility** (correlation, logging context) | 4 | 344 | -- | High |
| 13 | `patterns/` | **Utility** (reusable design patterns) | 3 | 447 | -- | High |
| 14 | `persistence/` | **Subsystem** (SaveSession / UoW) | 20 | 8,078 | -- | High |
| 15 | `protocols/` | **Layer** (DI protocol definitions) | 6 | 727 | -- | High |
| 16 | `query/` | **Subsystem** (Query DSL v2) | 9 | 2,040 | -- | High |
| 17 | `resolution/` | **Component** (entity resolution strategies) | 8 | 1,822 | -- | High |
| 18 | `search/` | **Module** (DataFrame search interface) | 3 | 925 | -- | High |
| 19 | `services/` | **Layer** (service-layer orchestration) | 17 | 6,449 | -- | High |
| 20 | `transport/` | **Component** (HTTP transport / circuit breaker) | 6 | 1,716 | -- | High |
| 21 | `_defaults/` | **Utility** (default provider implementations) | 5 | 1,029 | -- | High |
| 22 | `auth/` | **Component** (JWT authentication) | 5 | 669 | -- | High |

---

## 2. Tech Stack Inventory

### 2.1 Languages and Runtime

| Item | Detail | Confidence |
|------|--------|------------|
| Language | Python 3.11+ (requires-python >=3.11, target 3.12) | High |
| Runtime | CPython (python:3.12-slim Docker base) | High |
| Async framework | asyncio (native, async/await throughout) | High |

### 2.2 Frameworks

| Framework | Version | Role | Confidence |
|-----------|---------|------|------------|
| FastAPI | >=0.109.0 | HTTP API framework | High |
| Pydantic | >=2.0.0 | Data validation / domain models (frozen models) | High |
| pydantic-settings | >=2.0.0 | Settings management | High |
| Polars | >=0.20.0 | DataFrame processing (not pandas) | High |
| uvicorn | >=0.27.0 (standard) | ASGI server | High |
| SlowAPI | >=0.1.9 | Rate limiting middleware | High |

### 2.3 Key Libraries

| Library | Version | Role | Confidence |
|---------|---------|------|------------|
| httpx | >=0.25.0 | HTTP client (via autom8y-http SDK) | High |
| asana | >=5.0.3 | Official Asana SDK | High |
| arrow | >=1.3.0 | Date/time manipulation | High |
| boto3 | >=1.42.19 | AWS S3 for progressive cache warming | High |
| redis / hiredis | >=5.0.0 / >=2.0.0 | Redis cache backend (optional) | High |
| awslambdaric | >=2.2.0 | AWS Lambda Runtime Interface Client | High |
| apscheduler | >=3.10.0 | Polling scheduler (dev only) | High |

### 2.4 Platform Primitives (Internal SDKs)

All sourced from private CodeArtifact registry (`autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com`).

| SDK | Version | Role | Confidence |
|-----|---------|------|------------|
| autom8y-config | >=0.4.0 | Centralized settings (Autom8yBaseSettings) | High |
| autom8y-http[otel] | >=0.5.0 | HTTP client with OpenTelemetry, circuit breaker | High |
| autom8y-cache | >=0.4.0 | HierarchyAwareResolver, schema versioning | High |
| autom8y-log | >=0.5.5 | Structured logging | High |
| autom8y-core | >=1.1.0 | Core platform primitives | High |
| autom8y-telemetry[fastapi] | >=0.3.0 | Platform observability | High |
| autom8y-auth[observability] | >=1.1.0 | JWT validation, JWKS fetching | High |

### 2.5 Build Tools and Dependency Management

| Item | Detail | Confidence |
|------|--------|------------|
| Build system | hatchling | High |
| Package manager | uv (with uv.lock lockfile) | High |
| Index strategy | first-index (PyPI default, CodeArtifact secondary) | High |
| Linter | ruff (line-length=88, target py312) | High |
| Type checker | mypy (strict=true, python_version=3.11) | High |
| Security scanner | semgrep (.semgrep.yml) | High |
| Pre-commit hooks | .pre-commit-config.yaml | High |
| Task runner | justfile | High |

### 2.6 Infrastructure

| Item | Detail | Confidence |
|------|--------|------------|
| Container | Multi-stage Docker (python:3.12-slim), dual-mode ECS/Lambda | High |
| Container orchestration | Docker Compose (docker-compose.yml + override) | High |
| CI/CD | GitHub Actions (.github/workflows/test.yml, satellite-dispatch.yml) | High |
| Cloud provider | AWS (Lambda, ECS, S3, CodeArtifact, Secrets Manager, CloudWatch) | High |
| IaC | No Terraform/CDK in repo (external) | High |
| Config files | YAML lifecycle stages (`config/lifecycle_stages.yaml`), YAML conversation-audit rules (`config/rules/conversation-audit.yaml`) | High |
| API spec | OpenAPI (`docs/api-reference/openapi.yaml`, `docs/contracts/openapi-data-service-client.yaml`) | High |

### 2.7 Testing Infrastructure

| Item | Detail | Confidence |
|------|--------|------------|
| Framework | pytest (asyncio_mode=auto, timeout=60s) | High |
| Async testing | pytest-asyncio | High |
| HTTP mocking | respx (httpx mock) | High |
| Redis mocking | fakeredis | High |
| AWS mocking | moto (S3) | High |
| Coverage | pytest-cov | High |
| Test structure | unit/ (372 files, 180K LOC), api/ (21, 9K), integration/ (40, 17K), benchmarks/ (4, 1.5K), qa/ (2, 2.5K), test_auth/ (7, 1.8K), validation/ (8, 3K), services/ (3, 0.5K) | High |

---

## 3. API Surface Map

### 3.1 HTTP API (FastAPI Routes)

All routes registered via `api/main.py` app factory.

| Router | Prefix | Tag | Endpoints | In Schema | Confidence |
|--------|--------|-----|-----------|-----------|------------|
| health | (none) | health | GET `/health`, GET `/ready`, GET `/health/deps` | Yes | High |
| users | `/api/v1/users` | users | 3 GET endpoints | Yes | High |
| workspaces | `/api/v1/workspaces` | workspaces | 2 GET endpoints | Yes | High |
| dataframes | `/api/v1/dataframes` | dataframes | 2 GET endpoints | Yes | High |
| tasks | `/api/v1/tasks` | tasks | 14 endpoints (GET/POST/PUT/DELETE) | Yes | High |
| projects | `/api/v1/projects` | projects | 8 endpoints (GET/POST/PUT/DELETE) | Yes | High |
| sections | `/api/v1/sections` | sections | 6 endpoints (GET/POST/PUT/DELETE) | Yes | High |
| section_timelines | `/api/v1/offers` | offers | 1 GET endpoint | Yes | High |
| webhooks | `/api/v1/webhooks` | webhooks | 1 POST `/inbound` | Yes | High |
| workflows | `/api/v1/workflows` | workflows | 1 POST endpoint | Yes | High |
| entity_write | `/api/v1/entity` | entity-write | 1 PATCH `/{entity_type}/{gid}` | No (hidden) | High |
| resolver | `/v1/resolve` | resolver | 1 POST `/{entity_type}` + schema sub-router | No (hidden) | High |
| query | `/v1/query` | query | 3 POST: `/{entity_type}/rows`, `/{entity_type}/aggregate`, `/{entity_type}` | No (hidden) | High |
| admin | `/v1/admin` | admin | 1 POST endpoint | No (hidden) | High |
| internal | `/api/v1/internal` | internal | (internal endpoints) | No (hidden) | High |

**Total visible endpoints**: ~42+ HTTP endpoints across 15 routers.

### 3.2 Lambda Handler Interfaces

All at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/`.

| Handler | File | Role | Bootstrap | Confidence |
|---------|------|------|-----------|------------|
| cache_warmer | `cache_warmer.py` | Cache warm-up with checkpoint resume | Explicit `_ensure_bootstrap()` | High |
| cache_invalidate | `cache_invalidate.py` | Redis key + S3 object invalidation | No (not needed) | High |
| insights_export | `insights_export.py` | Insights HTML export workflow | No (not needed) | High |
| conversation_audit | `conversation_audit.py` | Conversation audit workflow | Tier1 defensive guard | High |
| checkpoint | `checkpoint.py` | S3 checkpoint operations | N/A (utility) | High |
| workflow_handler | `workflow_handler.py` | Generic workflow factory | N/A (factory) | High |
| cloudwatch | `cloudwatch.py` | CloudWatch event handler | Medium (not in prior audit) | Medium |

### 3.3 SDK Client API (Library Exports)

Exported via `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/__init__.py`.

| Category | Key Exports | Confidence |
|----------|-------------|------------|
| Main client | `AsanaClient` | High |
| Configuration | `AsanaConfig`, `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig` | High |
| Exception hierarchy | 11 exception types (`AsanaError` base + 10 specific) | High |
| Protocols | `AuthProvider`, `CacheProvider`, `ItemLoader`, `LogProvider`, `ObservabilityHook` | High |
| Auth providers | `EnvAuthProvider`, `SecretsManagerAuthProvider` | High |
| Batch API | `BatchClient`, `BatchRequest`, `BatchResult`, `BatchSummary` | High |
| Models (Base) | `AsanaResource`, `NameGid`, `PageIterator` | High |
| Models (Tier 1) | `Task`, `Project`, `Section`, `CustomField`, `User`, `Workspace` + related | High |
| Models (Tier 2) | `Attachment`, `Goal`, `Portfolio`, `Story`, `Tag`, `Team`, `Webhook` + related | High |
| Observability | `CorrelationContext`, `error_handler`, `generate_correlation_id` | High |
| DataFrame (lazy) | 30+ exports including builders, extractors, schemas, resolvers | High |

### 3.4 External Service Integrations (Outbound)

| Service | Protocol | Module | Confidence |
|---------|----------|--------|------------|
| Asana API | HTTPS REST | `transport/asana_http.py`, `clients/*.py` | High |
| autom8-data API | HTTPS REST | `clients/data/` (5 endpoint modules) | High |
| autom8 auth API | HTTPS REST | `auth/`, `_defaults/auth.py` (JWT/JWKS) | High |
| AWS S3 | boto3 SDK | `cache/backends/s3.py`, `cache/dataframe/tiers/progressive.py` | High |
| AWS Secrets Manager | boto3 SDK | `_defaults/auth.py` | High |
| Redis | redis-py | `cache/backends/redis.py` | High |

### 3.5 Message / Event Interfaces

| Interface | Direction | Module | Confidence |
|-----------|-----------|--------|------------|
| Asana webhooks | Inbound | `api/routes/webhooks.py`, `lifecycle/webhook.py` | High |
| Automation events | Internal | `automation/events/` (emitter, envelope, transport, rules) | High |
| CloudWatch events | Inbound | `lambda_handlers/cloudwatch.py` | Medium |
| Cache mutation events | Internal | `cache/models/mutation_event.py`, `cache/integration/mutation_invalidator.py` | High |

---

## 4. Entry Point Catalog

### 4.1 Application Entry Points

| Entry Point | File | Mode | Bootstrap | Confidence |
|-------------|------|------|-----------|------------|
| Dual-mode dispatcher | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/entrypoint.py` | ECS (uvicorn) or Lambda (awslambdaric) | Explicit `bootstrap()` call in ECS mode | High |
| FastAPI app factory | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/main.py:create_app()` | ECS | Side-effect import of `models.business` at line 35 | High |
| cache_warmer handler | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_warmer.py:handler()` | Lambda | `_ensure_bootstrap()` guard | High |
| cache_invalidate handler | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cache_invalidate.py:handler()` | Lambda | No (not needed) | High |
| insights_export handler | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/insights_export.py:handler()` | Lambda | No (deferred workflow import) | High |
| conversation_audit handler | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/conversation_audit.py:handler()` | Lambda | Tier1 defensive guard (medium risk) | High |
| cloudwatch handler | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cloudwatch.py:handler()` | Lambda | Unknown | Medium |
| Polling CLI | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/polling/cli.py` | CLI (dev mode) | Unknown | Medium |

### 4.2 Initialization Flow (ECS Mode)

1. `entrypoint.py:main()` detects `AWS_LAMBDA_RUNTIME_API` absent
2. `run_ecs_mode()` calls `bootstrap()` from `models.business._bootstrap`
3. `uvicorn.run("autom8_asana.api.main:create_app", factory=True)`
4. `create_app()` creates FastAPI with lifespan context manager
5. `lifespan.py` handles startup (preload, cache warm-up) and shutdown
6. Route routers registered (15 routers)

### 4.3 Configuration Loading

| Config Source | File | Pattern | Confidence |
|---------------|------|---------|------------|
| Central Settings | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/settings.py` (886 LOC) | `Autom8yBaseSettings` subclasses, env_prefix per section | High |
| API Config | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/config.py` | `ASANA_API_` prefix | High |
| Client Config | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/config.py` (710 LOC) | `AsanaConfig` Pydantic model | High |
| Lifecycle stages | `/Users/tomtenuta/Code/autom8y-asana/config/lifecycle_stages.yaml` | YAML loaded at runtime, Pydantic-validated | High |
| Conversation audit rules | `/Users/tomtenuta/Code/autom8y-asana/config/rules/conversation-audit.yaml` | YAML rule config | High |
| Data service config | `clients/data/config.py` | `DataServiceConfig` with `AUTOM8_DATA_` prefix | High |
| Automation config | `automation/config.py` | `AutomationConfig` Pydantic model | High |
| Lifecycle config | `lifecycle/config.py` | `LifecycleConfig`, `LifecycleConfigModel` with YAML loader | High |

**Settings env prefixes**: `ASANA_`, `ASANA_CACHE_`, `ASANA_CACHE_S3_`, `ASANA_PACING_`, `ASANA_S3_`, `AUTOM8_DATA_`, `REDIS_`, `WEBHOOK_`

---

## 5. Subsystem Profiles

### 5.1 Models Subsystem (Entity Layer)

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/`
**Classification**: Subsystem
**Files**: 60 | **LOC**: 15,482
**Confidence**: High

**Sub-packages**:
- `business/` (44 files, ~9,358 LOC) -- Domain entity hierarchy: Business, Contact, Unit, Offer, Process, Location, Hours, DNA, AssetEdit, Reconciliation, Videography. Pydantic v2 frozen models with descriptor-driven auto-wiring. Includes detection/ (tiered entity type detection, 4 tiers), matching/ (entity deduplication engine with blocking/comparators/normalizers), and registry (ProjectTypeRegistry, WorkspaceProjectRegistry).
- `contracts/` (2 files) -- Phone/vertical contract models.
- Root modules (14 files, ~6,124 LOC) -- Asana API resource models: Task, Project, Section, User, CustomField, Story, etc. All `extra="ignore"` for forward compatibility.

**Key files**:
| File | LOC | Role |
|------|-----|------|
| `business/business.py` | 776 | Root Business entity with 7 holder properties, stub holders |
| `business/hydration.py` | 793 | `hydrate_from_gid_async()` -- GID-to-entity hydration pipeline |
| `business/asset_edit.py` | 745 | AssetEdit entity (39+ typed fields) |
| `business/registry.py` | 727 | ProjectTypeRegistry (SSoT), WorkspaceProjectRegistry |
| `business/descriptors.py` | 720 | Descriptor-driven custom field auto-wiring |
| `business/seeder.py` | 610 | BusinessSeeder for hierarchical entity creation |
| `business/process.py` | 510 | Process entity with ProcessType enum, ProcessSection |
| `business/unit.py` | 479 | Unit entity with nested holders and 31 typed fields |
| `business/base.py` | 416 | BusinessEntity base class, HolderMixin |
| `business/fields.py` | 376 | CascadingFieldDef, InheritedFieldDef registries |
| `business/activity.py` | 275 | SectionClassifier (frozen), AccountActivity enum |
| `business/_bootstrap.py` | 184 | `bootstrap()`, `register_all_models()` |
| `task.py` | ~400 | Task model (core Asana resource) |

**Public API surface**: 60+ exported classes and functions including 17 entity types (Business, Contact, Unit, Offer, Process, Location, Hours, DNA, AssetEdit, Reconciliation, Videography + 6 Holders), detection functions, classification utilities, hydration pipeline, resolution functions, bootstrap mechanism.

**Entity hierarchy**: Business -> {Contact, Unit, Offer, Process, Location, Hours, DNA, Reconciliation, AssetEdit, Videography} (each via typed Holder).

### 5.2 Cache Subsystem

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/`
**Classification**: Subsystem
**Files**: 53 | **LOC**: 16,103
**Confidence**: High

The largest subsystem by LOC. Multi-tier SWR (stale-while-revalidate) caching with two parallel cache systems: entity cache and DataFrame cache.

**Sub-packages**:
- `backends/` (4 files) -- Cache backend implementations: `base.py` (abstract), `memory.py` (in-memory), `redis.py` (Redis), `s3.py` (S3 cold tier).
- `dataframe/` (9 files including `tiers/`) -- DataFrame-specific caching: `build_coordinator.py`, `circuit_breaker.py`, `coalescer.py`, `decorator.py`, `factory.py`, `warmer.py`, plus `tiers/memory.py` and `tiers/progressive.py` (S3-based progressive warming).
- `integration/` (15 files) -- High-level cache integration: `autom8_adapter.py` (legacy migration), `batch.py` (bulk modification checking), `dataframe_cache.py`, `dataframes.py` (DF key management), `derived.py` (timeline cache), `factory.py` (CacheProviderFactory), `freshness_coordinator.py`, `hierarchy_warmer.py`, `loader.py` (multi-entry loading), `mutation_invalidator.py`, `schema_providers.py`, `staleness_coordinator.py`, `stories.py` (incremental story loading), `upgrader.py`.
- `models/` (12 files) -- Cache data models: `CacheEntry`, `EntryType` (14 types), `Freshness` (enum), `FreshnessState`/`FreshnessIntent` (unified), `CacheMetrics`/`CacheEvent`, `CacheSettings`, `CompletenessLevel`, `MutationEvent`, schema versioning.
- `policies/` (5 files) -- Cache policies: `coalescer.py` (RequestCoalescer), `freshness_policy.py`, `hierarchy.py` (HierarchyIndex), `lightweight_checker.py` (LightweightChecker), `staleness.py`.
- `providers/` (3 files) -- `tiered.py` (TieredCacheProvider: Redis hot + S3 cold), `unified.py` (UnifiedTaskStore).

**Public API surface**: 70+ exported symbols including CacheEntry, EntryType, Freshness, FreshnessState, CacheSettings, CompletenessLevel, TieredCacheProvider, UnifiedTaskStore, CacheProviderFactory, MutationInvalidator, plus numerous utility functions for loading, staleness checking, invalidation, and story management.

### 5.3 DataFrames Subsystem

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/`
**Classification**: Subsystem
**Files**: 45 | **LOC**: 13,917
**Confidence**: High

Schema-driven extraction of Asana task data into typed Polars DataFrames.

**Sub-packages**:
- `builders/` (10 files) -- DataFrame construction: `base.py` (DataFrameBuilder), `progressive.py` (ProgressiveProjectBuilder), `section.py` (SectionDataFrameBuilder), `parallel_fetch.py`, `freshness.py`, `fields.py`, `cascade_validator.py`, `task_cache.py`, `build_result.py`.
- `extractors/` (5 files) -- Task-to-row extraction: `base.py` (BaseExtractor), `contact.py`, `default.py`, `unit.py`, `schema.py`.
- `models/` (4 files) -- DataFrame data models: `registry.py` (SchemaRegistry), `schema.py` (DataFrameSchema, ColumnDef), `task_row.py` (TaskRow, UnitRow, ContactRow).
- `resolver/` (7 files) -- Custom field GID resolution: `protocol.py`, `default.py`, `cascading.py`, `coercer.py`, `mock.py`, `normalizer.py` (NameNormalizer).
- `schemas/` (7 files) -- Built-in schema definitions per entity type: `base.py`, `business.py`, `contact.py`, `offer.py`, `unit.py`, `asset_edit.py`, `asset_edit_holder.py`.
- `views/` (4 files) -- DataFrame view layer: `dataframe_view.py`, `cascade_view.py`, `cf_utils.py`.
- Root modules -- `cache_integration.py`, `exceptions.py`, `section_persistence.py`, `storage.py`, `watermark.py`.

**Public API surface**: 30+ exports including builders, extractors, schemas, resolver interfaces, cache integration types.

### 5.4 Persistence Subsystem (SaveSession / UoW)

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/`
**Classification**: Subsystem
**Files**: 20 | **LOC**: 8,078
**Confidence**: High

Unit of Work pattern for batched Asana API operations with 6-phase commit.

**Key files**:
| File | LOC | Role |
|------|-----|------|
| `session.py` | 1,854 | **SaveSession** -- Coordinator pattern (14 collaborators, 58 methods). UoW context manager. |
| `graph.py` | -- | Dependency graph for operation ordering |
| `cascade.py` | -- | CascadeExecutor, CascadeOperation, cascade_field |
| `action_executor.py` | -- | Action execution engine |
| `action_ordering.py` | -- | Operation ordering logic |
| `actions.py` | -- | Action type definitions |
| `pipeline.py` | -- | Persistence pipeline |
| `healing.py` | -- | HealingManager (self-healing) |
| `holder_concurrency.py` | -- | Holder-level concurrency control |
| `holder_construction.py` | -- | Holder construction logic |
| `holder_ensurer.py` | -- | Holder existence enforcement |
| `cache_invalidator.py` | -- | Post-commit cache invalidation |
| `reorder.py` | -- | Section reordering |
| `tracker.py` | -- | Entity state tracking |
| `validation.py` | -- | Pre-commit validation |
| `models.py` | -- | EntityState, OperationType, SaveResult, HealingResult |
| `exceptions.py` | -- | SaveOrchestrationError hierarchy (7 exception types) |
| `events.py` | -- | Persistence event system |
| `executor.py` | -- | Core execution engine |

**Public API surface**: SaveSession (main), EntityState, OperationType, PlannedOperation, SaveResult, CascadeExecutor, CascadeOperation, HealingManager, HealingResult, 7 exception types.

### 5.5 Clients Subsystem (Asana API + Data Service)

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/`
**Classification**: Layer
**Files**: 36 | **LOC**: 11,729
**Confidence**: High

Two distinct client layers:

**Asana Resource Clients** (root `clients/`, 22 files, ~8,705 LOC):
13 typed resource clients inheriting from `BaseClient`: Tasks, Projects, Sections, Users, Workspaces, CustomFields, Attachments, Goals, Portfolios, Stories, Tags, Teams, Webhooks. Plus `name_resolver.py`, `goal_followers.py`, `goal_relationships.py`, `task_operations.py`, `task_ttl.py`.

**Data Service Client** (`clients/data/`, 14 files, ~3,024 LOC):
`DataServiceClient` (1,276 LOC) with 5 endpoint modules:
| Module | LOC | Role |
|--------|-----|------|
| `_endpoints/simple.py` | 234 | Simple insights queries |
| `_endpoints/batch.py` | 310 | Batch insights queries |
| `_endpoints/insights.py` | 219 | Insights endpoint |
| `_endpoints/export.py` | 173 | Export endpoint |
| `_endpoints/reconciliation.py` | 133 | Reconciliation endpoint |

Plus supporting modules: `_cache.py` (194), `_response.py` (270), `_retry.py` (191), `_metrics.py` (54), `_normalize.py` (58), `_pii.py` (73 -- PII redaction contract), `config.py` (298), `models.py` (498).

### 5.6 Automation Subsystem

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/`
**Classification**: Subsystem
**Files**: 34 | **LOC**: 10,768
**Confidence**: High

Rule-based automation engine with event system, polling, and workflows.

**Sub-packages**:
- `events/` (7 files) -- Event system: `emitter.py`, `envelope.py`, `transport.py`, `rule.py`, `types.py` (EventType), `config.py`.
- `polling/` (8 files) -- Polling scheduler subsystem: `cli.py`, `polling_scheduler.py`, `trigger_evaluator.py`, `action_executor.py`, `config_loader.py`, `config_schema.py`, `structured_logger.py`.
- `workflows/` (9 files) -- Workflow implementations: `base.py`, `pipeline_transition.py`, `section_resolution.py`, `insights_export.py`, `insights_formatter.py` (1,476 LOC -- HTML insights renderer), `conversation_audit.py`, `mixins.py`, `registry.py`.
- Root modules -- `engine.py` (AutomationEngine), `pipeline.py` (970 LOC -- PipelineConversionRule, legacy creation path), `base.py` (AutomationRule protocol, TriggerCondition, Action), `config.py` (AutomationConfig, AssigneeConfig, PipelineStage), `context.py`, `seeding.py` (FieldSeeder), `templates.py` (TemplateDiscovery), `validation.py`, `waiter.py` (SubtaskWaiter).

**Public API surface**: AutomationEngine, AutomationRule, TriggerCondition, Action, AutomationContext, AutomationConfig, PipelineConversionRule (lazy-loaded), FieldSeeder, TemplateDiscovery, SubtaskWaiter, EventType.

### 5.7 Lifecycle Subsystem (Canonical Pipeline Engine)

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/`
**Classification**: Subsystem
**Files**: 12 | **LOC**: 3,898
**Confidence**: High

Data-driven lifecycle automation -- the canonical pipeline engine (vs. automation/pipeline.py legacy path).

**Key files**:
| File | LOC | Role |
|------|-----|------|
| `creation.py` | 737 | EntityCreationService -- canonical 7-step creation pipeline |
| `engine.py` | -- | LifecycleEngine -- transition orchestration |
| `dispatch.py` | -- | AutomationDispatch -- webhook routing |
| `config.py` | -- | LifecycleConfig, StageConfig, TransitionConfig (YAML-driven) |
| `seeding.py` | -- | AutoCascadeSeeder (zero-config field seeding by name matching) |
| `sections.py` | -- | CascadingSectionService |
| `completion.py` | -- | CompletionService |
| `reopen.py` | -- | ReopenService |
| `init_actions.py` | -- | Init action handlers (Comment, PlayCreation, EntityCreation, ProductsCheck, Campaign) |
| `wiring.py` | -- | DependencyWiringService |
| `webhook.py` | -- | WebhookResponse, Asana webhook payload models, FastAPI router |

**Public API surface**: LifecycleEngine, AutomationDispatch, EntityCreationService, CascadingSectionService, CompletionService, DependencyWiringService, ReopenService, AutoCascadeSeeder, LifecycleConfig (+ 10 sub-configs), 5 init action handlers, webhook router.

**Configuration**: Driven by `config/lifecycle_stages.yaml` -- 9 stages (outreach, sales, onboarding, implementation, month1, retention, reactivation, account_error, expansion) with transitions, cascading sections, seeding rules, assignee config, init actions, and dependency wiring.

### 5.8 Query Subsystem (Query DSL v2)

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/`
**Classification**: Subsystem
**Files**: 9 | **LOC**: 2,040
**Confidence**: High

Composable predicate filtering and aggregation for DataFrame cache.

**Key files**:
| File | LOC | Role |
|------|-----|------|
| `engine.py` | -- | QueryEngine -- orchestrates filtered row retrieval |
| `compiler.py` | -- | PredicateCompiler -- AST to Polars expression compilation |
| `aggregator.py` | -- | AggregationCompiler, build_post_agg_schema |
| `models.py` | -- | PredicateNode (Comparison, AndGroup, OrGroup, NotGroup), Op (10 operators), RowsRequest/Response, AggregateRequest/Response, AggSpec, AggFunction |
| `guards.py` | -- | QueryLimits, predicate_depth validation |
| `hierarchy.py` | -- | EntityRelationship, cross-entity join metadata |
| `join.py` | -- | JoinSpec, JoinResult, execute_join (depth 1) |
| `errors.py` | -- | QueryEngineError hierarchy (8 error types) |

**Public API surface**: QueryEngine, PredicateCompiler, AggregationCompiler, 4 predicate node types, 10 operators (Op enum), RowsRequest/Response, AggregateRequest/Response, QueryLimits, JoinSpec, execute_join, EntityRelationship, 8 error types.

### 5.9 API Layer

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/`
**Classification**: Layer
**Files**: 35 | **LOC**: 9,323
**Confidence**: High

FastAPI application layer with preload subsystem.

**Sub-packages**:
- `routes/` (18 files, 5,091 LOC) -- HTTP endpoint handlers (see Section 3.1).
- `preload/` (4 files) -- Cache pre-loading: `progressive.py` (S3-based progressive preload), `legacy.py` (active degraded-mode fallback per ADR-011), `constants.py`.
- Root modules -- `main.py` (app factory), `lifespan.py` (startup/shutdown), `startup.py` (initialization), `dependencies.py` (FastAPI DI), `middleware.py` (RequestID, RequestLogging), `client_pool.py`, `config.py`, `errors.py`, `health_models.py`, `metrics.py`, `models.py`, `rate_limit.py`.

### 5.10 Services Layer

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/`
**Classification**: Layer
**Files**: 17 | **LOC**: 6,449
**Confidence**: High

Service-layer orchestration bridging API routes to subsystems.

**Key files**:
| File | LOC | Role |
|------|-----|------|
| `section_timeline_service.py` | 727 | Pre-computed section timeline service |
| `resolver.py` | 718 | UniversalResolverService |
| `universal_strategy.py` | 710 | UniversalStrategy for entity resolution |
| `task_service.py` | 634 | Task CRUD service |
| `query_service.py` | 603 | Query service layer (routes queries to QueryEngine) |
| `dynamic_index.py` | 522 | Dynamic entity indexing |
| `field_write_service.py` | 363 | Entity field write service |
| `dataframe_service.py` | 360 | DataFrame service layer |
| `errors.py` | 343 | Service-layer error types |
| `gid_lookup.py` | 306 | GidLookupIndex |
| `gid_push.py` | 283 | GID push operations |
| `section_service.py` | 274 | Section CRUD service |
| `discovery.py` | 247 | Entity/project discovery |
| `entity_service.py` | 160 | Entity service |
| `entity_context.py` | 41 | Entity context provider |
| `resolution_result.py` | 147 | Resolution result models |

### 5.11 Core Layer

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/`
**Classification**: Layer
**Files**: 16 | **LOC**: 3,247
**Confidence**: High

Foundational shared primitives used across all subsystems.

**Key files**:
| File | LOC | Role |
|------|-----|------|
| `entity_registry.py` | 859 | EntityRegistry -- central type metadata registry |
| `retry.py` | 836 | Retry policy primitives |
| `exceptions.py` | 335 | Core exception hierarchy |
| `creation.py` | 256 | Shared creation primitives (template discovery, task duplication, name generation, section placement, due date, subtask waiting) |
| `project_registry.py` | 182 | Project GID -> type mapping |
| `registry_validation.py` | 170 | Registry cross-validation |
| `connections.py` | 147 | Connection pool management |
| `logging.py` | 106 | Logging configuration |
| `system_context.py` | 86 | SystemContext (global state, bootstrap reset) |
| `scope.py` | 79 | Scope definitions |
| `concurrency.py` | 68 | `gather_with_semaphore()` |
| `datetime_utils.py` | 33 | Date/time utilities |
| `entity_types.py` | 23 | Entity type enum |
| `schema.py` | 37 | Schema utilities |
| `timing.py` | 15 | Timing utilities |

### 5.12 Transport Component

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/transport/`
**Classification**: Component
**Files**: 6 | **LOC**: 1,716
**Confidence**: High

HTTP transport layer using autom8y-http platform SDK.

**Key files**: `asana_http.py` (AsanaHttpClient), `adaptive_semaphore.py` (AsyncAdaptiveSemaphore -- AIMD concurrency), `config_translator.py` (ConfigTranslator), `response_handler.py` (AsanaResponseHandler), `sync.py` (sync_wrapper utility).

**Public API**: AsanaHttpClient, AsyncAdaptiveSemaphore, ConfigTranslator, AsanaResponseHandler, sync_wrapper, CircuitState (re-exported from autom8y-http).

### 5.13 Resolution Component

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/resolution/`
**Classification**: Component
**Files**: 8 | **LOC**: 1,822
**Confidence**: High

Entity resolution primitives with strategy chain pattern.

**Key files**: `strategies.py` (4 strategies: SessionCache, NavigationRef, DependencyShortcut, HierarchyTraversal), `selection.py` (EntitySelector, predicates), `context.py` (ResolutionContext), `budget.py` (ApiBudget), `field_resolver.py`, `result.py` (ResolutionResult, ResolutionStatus), `write_registry.py`.

**Public API**: 2 predefined chains (DEFAULT_CHAIN, BUSINESS_CHAIN), 4 strategies, ApiBudget, ResolutionContext, ResolutionResult, 6 selection predicates.

### 5.14 Smaller Units

**Lambda Handlers** (8 files, 2,249 LOC) -- See Section 4.1. Includes `cloudwatch.py` (not in prior audit).

**Metrics** (8 files, 621 LOC) -- Declarative metric computation: `MetricExpr`, `Metric`, `Scope`, `MetricRegistry`, `compute_metric`, `SectionIndex`, `resolve_metric_scope`. Definitions sub-package contains `offer.py`.

**Search** (3 files, 925 LOC) -- `SearchService` for efficient GID retrieval from cached project DataFrames using Polars filter expressions.

**Batch** (3 files, 684 LOC) -- `BatchClient` for bulk operations via Asana's `/batch` endpoint.

**Auth** (5 files, 669 LOC) -- JWT authentication integration with autom8y-auth SDK.

**Protocols** (6 files, 727 LOC) -- DI protocol definitions: `AuthProvider`, `CacheProvider`, `DataFrameCacheProtocol`, `ItemLoader`, `LogProvider`, `ObservabilityHook`, `WarmResult`.

**Observability** (4 files, 344 LOC) -- `CorrelationContext`, `LogContext`, `error_handler` decorator.

**Patterns** (3 files, 447 LOC) -- Reusable patterns: `async_method` (AsyncMethodPair -- sync/async dual generation), `error_classification` (RetryableErrorMixin).

**_defaults** (5 files, 1,029 LOC) -- Default provider implementations: `EnvAuthProvider`, `SecretsManagerAuthProvider`, `NullCacheProvider`, `InMemoryCacheProvider`, `DefaultLogProvider`, `NullObservabilityHook`.

### 5.15 Root-Level Modules

**Path**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/` (root)
**Files**: 6 | **LOC**: 3,476

| File | LOC | Role |
|------|-----|------|
| `client.py` | 1,044 | `AsanaClient` -- main SDK entry point, composes all resource clients |
| `settings.py` | 886 | Centralized settings (10 settings classes, all `Autom8yBaseSettings`) |
| `config.py` | 710 | `AsanaConfig` -- client configuration model |
| `exceptions.py` | 490 | Exception hierarchy (11 types) |
| `__init__.py` | 240 | Public SDK API (lazy DataFrame exports) |
| `entrypoint.py` | 106 | Dual-mode ECS/Lambda dispatcher |

---

## 6. Directory Structure Profiles

### 6.1 Test Organization

Tests mirror source structure under `/Users/tomtenuta/Code/autom8y-asana/tests/`:

| Directory | Files | LOC | Mirrors |
|-----------|-------|-----|---------|
| `unit/api/` | 13 | 5,388 | `api/` |
| `unit/automation/` | 44 | 21,565 | `automation/` |
| `unit/cache/` | 59 | 24,344 | `cache/` |
| `unit/clients/` | 28 | 12,406 | `clients/` |
| `unit/core/` | 11 | 4,057 | `core/` |
| `unit/dataframes/` | 40 | 20,379 | `dataframes/` |
| `unit/detection/` | 2 | 596 | `models/business/detection/` |
| `unit/lambda_handlers/` | 10 | 3,869 | `lambda_handlers/` |
| `unit/lifecycle/` | 14 | 7,939 | `lifecycle/` |
| `unit/metrics/` | 8 | 1,381 | `metrics/` |
| `unit/models/` | 42 | 20,534 | `models/` |
| `unit/patterns/` | 3 | 868 | `patterns/` |
| `unit/persistence/` | 27 | 18,563 | `persistence/` |
| `unit/query/` | 12 | 8,934 | `query/` |
| `unit/resolution/` | 9 | 2,180 | `resolution/` |
| `unit/search/` | 4 | 780 | `search/` |
| `unit/services/` | 14 | 8,764 | `services/` |
| `unit/transport/` | 7 | 2,061 | `transport/` |
| `api/` (top-level) | 21 | 9,219 | API integration tests |
| `integration/` | 40 | 17,156 | Cross-subsystem integration |
| `benchmarks/` | 4 | 1,506 | Performance benchmarks |
| `qa/` | 2 | 2,549 | QA validation |
| `test_auth/` | 7 | 1,824 | Auth-specific tests |
| `validation/` | 8 | 3,046 | Data validation tests |
| `services/` (top-level) | 3 | 481 | Service integration tests |
| `_shared/` | 2 | 49 | Shared test utilities |

**Test-to-source ratio**: ~1.87:1 by LOC (216K test / 115K source).

### 6.2 Documentation Presence

| Location | Content |
|----------|---------|
| `docs/` | Architecture docs, API reference, ADRs, contracts, guides |
| `docs/architecture/` | ARCH-OPPORTUNITY-GAP-SYNTHESIS-2026-02.md |
| `docs/decisions/` | Pre-existing ADR series (ADR-00XX) |
| `docs/adr/` | Post-Q1 ADR series (ADR-0XX) |
| `docs/api-reference/` | openapi.yaml |
| `docs/contracts/` | openapi-data-service-client.yaml |
| `docs/guides/` | Canonical patterns guide |
| `docs/debt/` | Debt ledger, risk matrix, sprint plan |
| `runbooks/` | Operational runbooks |
| `README.md` | Project readme |
| `CHANGELOG.md` | Changelog |

### 6.3 Configuration File Locations

| File | Format | Role |
|------|--------|------|
| `pyproject.toml` | TOML | Build system, dependencies, tool config |
| `uv.lock` | Lock | Dependency lockfile |
| `config/lifecycle_stages.yaml` | YAML | Pipeline stage definitions (9 stages) |
| `config/rules/conversation-audit.yaml` | YAML | Conversation audit rules |
| `.pre-commit-config.yaml` | YAML | Pre-commit hooks |
| `.semgrep.yml` | YAML | Security scanning rules |
| `justfile` | Just | Task runner commands |
| `.python-version` | Text | Python version pin |
| `.envrc` | Shell | direnv configuration |
| `.gitignore` | Text | Git ignore rules |
| `.dockerignore` | Text | Docker build ignore rules |
| `Dockerfile` | Docker | Multi-stage dual-mode container |
| `Dockerfile.dev` | Docker | Development container |
| `docker-compose.yml` | YAML | Container orchestration |
| `docker-compose.override.yml` | YAML | Local dev overrides |
| `.github/workflows/test.yml` | YAML | CI test pipeline |
| `.github/workflows/satellite-dispatch.yml` | YAML | Satellite deployment dispatch |

---

## 7. Subsystem-to-Prior-Art Mapping

The 7 target subsystems from the scope description map to actual directories as follows:

| Prior Art Subsystem | Primary Directory | Secondary Directories | Notes |
|---------------------|-------------------|-----------------------|-------|
| 1. Entity | `models/` (60 files, 15.5K LOC) | `models/business/` dominates (44 files, 9.4K LOC) | Includes detection, matching, registry |
| 2. Classification | `models/business/activity.py` (275 LOC) | `models/business/sections.py` (46 LOC) | Embedded within models, not a standalone directory |
| 3. DataFrame/Query | `dataframes/` (45 files, 13.9K LOC) + `query/` (9 files, 2K LOC) + `metrics/` (8 files, 621 LOC) | `services/query_service.py`, `services/dataframe_service.py` | Three directories compose this subsystem |
| 4. Cache | `cache/` (53 files, 16.1K LOC) | `api/preload/` (4 files) | Largest single subsystem |
| 5. Persistence/SaveSession | `persistence/` (20 files, 8.1K LOC) | -- | SaveSession at 1,854 LOC is the coordinator |
| 6. DataServiceClient/API | `clients/data/` (14 files, 3K LOC) | Asana resource clients in `clients/` root (22 files, 8.7K LOC) | Two distinct client layers in one directory |
| 7. Creation Pipelines | `lifecycle/` (12 files, 3.9K LOC) + `automation/pipeline.py` (970 LOC) | `core/creation.py` (256 LOC -- shared primitives) | Dual-path: lifecycle (canonical) vs automation (legacy) |

### Additional Subsystems Discovered (Not in Prior Art)

| Subsystem | Directory | Files | LOC | Notes |
|-----------|-----------|-------|-----|-------|
| **Services Layer** | `services/` | 17 | 6,449 | Orchestration layer between API and subsystems |
| **Transport** | `transport/` | 6 | 1,716 | HTTP transport with adaptive concurrency |
| **Resolution** | `resolution/` | 8 | 1,822 | Entity resolution strategy chains |
| **Search** | `search/` | 3 | 925 | DataFrame search interface |
| **Automation Events** | `automation/events/` | 7 | ~1,200 | Event system (emitter, envelope, transport, rules) |
| **Automation Workflows** | `automation/workflows/` | 9 | ~4,000 | Workflow implementations (insights, conversation audit, pipeline transition) |
| **Automation Polling** | `automation/polling/` | 8 | ~2,200 | Dev-mode polling scheduler |
| **Business Matching** | `models/business/matching/` | 7 | ~1,500 | Entity deduplication engine |
| **Business Detection** | `models/business/detection/` | 8 | ~1,800 | 4-tier entity type detection |

---

## 8. Unknowns

### Unknown: cloudwatch.py Lambda Handler Purpose and Bootstrap Status

- **Question**: What is the `cloudwatch.py` handler's specific CloudWatch event source, and does it require entity model bootstrap?
- **Why it matters**: This handler was not included in the prior entry-point audit (U-005). If it uses entity detection or registry operations, it may need a bootstrap guard.
- **Evidence**: File exists at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lambda_handlers/cloudwatch.py` but is not mentioned in the ENTRY-POINT-AUDIT.md.
- **Suggested source**: Read the file contents; check if it imports from `models.business`.

### Unknown: Polling CLI Deployment Status

- **Question**: Is the polling CLI (`automation/polling/cli.py`) deployed in production, or is it purely a development tool?
- **Why it matters**: If deployed, it is an additional production entry point requiring bootstrap and monitoring consideration. The scheduler optional dependency (apscheduler) is marked "development mode."
- **Evidence**: Comment in pyproject.toml: "scheduler: Polling scheduler for development mode (production uses cron)".
- **Suggested source**: Deployment configuration, team knowledge.

### Unknown: Internal Router Endpoint Details

- **Question**: What endpoints does the `internal` router (`api/routes/internal.py`) expose, and what consumers use them?
- **Why it matters**: Hidden from OpenAPI schema (`include_in_schema=False`), these endpoints are part of the API surface but not externally documented.
- **Evidence**: Router registered at `/api/v1/internal` with `include_in_schema=False`.
- **Suggested source**: Read the file contents for route definitions.

### Unknown: Admin Router Full Endpoint Inventory

- **Question**: Beyond the 1 POST endpoint identified, what is the complete set of admin operations?
- **Why it matters**: Admin routes (at `/v1/admin`, hidden from schema) may include cache management, configuration reload, or other operational endpoints that affect system behavior.
- **Evidence**: `admin.py` is 475 LOC -- substantial for a single POST endpoint. Likely contains additional helper endpoints or complex logic.
- **Suggested source**: Read the file contents.

### Unknown: DataServiceClient Endpoint-to-Scaffolding Relationship Post-Decomposition

- **Question**: After the 7-module decomposition of DataServiceClient, does each endpoint module still replicate the circuit-breaker/retry/log/metric scaffolding, or has the shared execution policy been extracted?
- **Why it matters**: The prior art (ARCH-OPPORTUNITY-GAP-SYNTHESIS) identified this as the highest-leverage opportunity. The current 1,276-LOC client.py plus 5 endpoint modules (1,069 LOC combined) suggests partial decomposition.
- **Evidence**: 5 endpoint modules exist in `_endpoints/`, plus supporting modules (`_retry.py`, `_cache.py`, `_response.py`, `_metrics.py`). Total clients/data/ is 3,024 LOC vs. prior reported 2,165 LOC for monolithic DataServiceClient.
- **Suggested source**: Code inspection of endpoint modules for shared vs. duplicated scaffolding.

---

## Handoff Checklist

- [x] topology-inventory artifact exists with all required sections
- [x] Every target unit has been scanned and classified (22 directories + 6 root modules)
- [x] Confidence ratings assigned to all classifications and API surface identifications
- [x] API surfaces identified with endpoint paths, protocols, and interface detail sufficient for dependency tracing
- [x] Tech stack inventory includes dependency manager information (uv, pyproject.toml, CodeArtifact)
- [x] Unknowns section documents units that could not be fully classified
- [x] No target unit was skipped without documented reason
