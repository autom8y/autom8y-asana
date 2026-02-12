# autom8_asana Documentation

> Python SDK and REST API for Asana task management, entity resolution, and business automation.

---

## What Do You Need?

| Goal | Start Here |
|------|------------|
| **Learn** the system | [Getting Started](getting-started/overview.md) |
| **Build** an integration | [API Reference](api-reference/README.md) / [Examples](examples/README.md) |
| **Operate** a deployment | [Runbooks](runbooks/README.md) |
| **Decide** on architecture | [ADRs](decisions/) / [Reference Data](reference/README.md) |

---

## Getting Started

New to autom8_asana? Start here.

| Guide | Description |
|-------|-------------|
| [System Overview](getting-started/overview.md) | Architecture, component map, request flow |
| [Installation](getting-started/installation.md) | Prerequisites, setup, first API call |
| [Core Concepts](getting-started/core-concepts.md) | Entity hierarchy, custom fields, sync/async, caching |

---

## Guides

Topical guides for common tasks and patterns.

| Guide | Description |
|-------|-------------|
| [Quick Start](guides/quickstart.md) | Get started in 5 minutes |
| [Core Concepts](guides/concepts.md) | SDK mental model and key abstractions |
| [Authentication](guides/authentication.md) | PAT and S2S JWT authentication modes |
| [Entity Write](guides/entity-write.md) | Write fields via API: resolution, coercion, partial success |
| [Entity Resolution](guides/entity-resolution.md) | Resolve phone+vertical to Asana GIDs |
| [Common Workflows](guides/workflows.md) | Task recipes: create, update, query, batch |
| [SaveSession](guides/save-session.md) | Unit-of-work pattern for batch writes |
| [Best Practices](guides/patterns.md) | Error handling, caching, performance |
| [Search & Query](guides/search-query-builder.md) | Building search queries against Asana |
| [Search Cookbook](guides/search-cookbook.md) | Ready-to-use search query examples |
| [Pipeline Automation](guides/pipeline-automation-setup.md) | Setting up automated pipeline workflows |
| [BusinessSeeder v2](guides/GUIDE-businessseeder-v2.md) | Seeding business entities from templates |
| [SDK Adoption](guides/sdk-adoption.md) | Migrating from legacy patterns |
| [Entity Query](guides/entity-query.md) | Composable queries: predicates, joins, aggregation |
| [Business Models](guides/business-models.md) | Entity hierarchy, descriptors, holders, detection |
| [Lifecycle Engine](guides/lifecycle-engine.md) | Pipeline stages, transitions, webhooks |
| [Cache System](guides/cache-system.md) | Multi-tier cache, TTL strategy, staleness, warming |
| [DataFrame Layer](guides/dataframes.md) | Polars DataFrames, schemas, content negotiation |
| [Automation Pipelines](guides/automation-pipelines.md) | Pipeline, seeding, conversation audit, workflows |
| [Webhooks](guides/webhooks.md) | Inbound events, dispatch, loop prevention |
| [Cache Migration](guides/autom8-migration.md) | S3 to Redis cache migration |

---

## API Reference

REST API documentation for service integrators.

| Resource | Description |
|----------|-------------|
| [API Reference Overview](api-reference/README.md) | Auth, pagination, errors, route groups |
| [OpenAPI Spec](api-reference/openapi.yaml) | Machine-readable specification (37 paths, 49 schemas) |
| [Entity Write Endpoint](api-reference/endpoints/entity-write.md) | PATCH /api/v1/entity/{type}/{gid} reference |
| [Resolver Endpoint](api-reference/endpoints/resolver.md) | POST /v1/resolve/{type} reference |

Interactive docs available at `/docs` (Swagger) and `/redoc` when `DEBUG=true`.

---

## SDK Reference

Class and module reference for Python developers.

| Module | Description |
|--------|-------------|
| [Client](sdk-reference/client.md) | AsanaClient configuration, authentication, connection pooling |
| [Resource Clients](sdk-reference/resource-clients.md) | Tasks, Projects, Sections, Custom Fields, Users, Tags |
| [Models](sdk-reference/models.md) | AsanaResource, Task, Project, Section, CustomField |
| [Business Models](sdk-reference/business-models.md) | Business, Unit, Offer, Contact, descriptors, holders |
| [Persistence](sdk-reference/persistence.md) | SaveSession, change tracking, batch commit, actions |
| [Configuration](sdk-reference/configuration.md) | AsanaConfig, rate limits, timeouts, connection pools |
| [Exceptions](sdk-reference/exceptions.md) | Exception hierarchy, HTTP errors, transport errors |
| [Protocols](sdk-reference/protocols.md) | AuthProvider, CacheProvider, LogProvider interfaces |

---

## Examples

Runnable Python scripts demonstrating common patterns.

| Example | Description |
|---------|-------------|
| [Examples Index](examples/README.md) | Full list of all examples with descriptions |
| [01 - Read Tasks](examples/01-read-tasks.py) | Client setup, user info, task listing |
| [02 - Batch Update](examples/02-batch-update.py) | Bulk custom field updates across tasks |
| [04 - Entity Resolution](examples/04-entity-resolution.py) | Resolve phone+vertical to GIDs via REST API |
| [03 - Create with Subtasks](examples/03-create-with-subtasks.py) | SaveSession parent + children hierarchy |
| [05 - Entity Write](examples/05-entity-write.py) | Write all field types: text, number, enum, multi-enum |
| [06 - Query Entities](examples/06-query-entities.py) | Query cached entity data with filters |
| [07 - Lifecycle Transition](examples/07-lifecycle-transition.py) | Trigger lifecycle stage changes |
| [08 - DataFrame Export](examples/08-dataframe-export.py) | Build DataFrames from project/section data |
| [09 - Cache Warming](examples/09-cache-warming.py) | Warm and inspect cache state |
| [10 - Webhook Handler](examples/10-webhook-handler.py) | Receive and process webhook events |

---

## Runbooks

Operational troubleshooting guides.

| Runbook | Description |
|---------|-------------|
| [Runbook Index](runbooks/README.md) | Overview and usage guide |
| [Cache Troubleshooting](runbooks/RUNBOOK-cache-troubleshooting.md) | Cache misses, stale data, performance |
| [SaveSession Debugging](runbooks/RUNBOOK-savesession-debugging.md) | Dependency cycles, partial failures, healing |
| [Detection Troubleshooting](runbooks/RUNBOOK-detection-troubleshooting.md) | Wrong types, tier fallback, missing entities |
| [Batch Operations](runbooks/RUNBOOK-batch-operations.md) | Chunking, parallelism, error recovery |
| [Business Model Navigation](runbooks/RUNBOOK-business-model-navigation.md) | Entity traversal and relationship debugging |
| [Pipeline Automation](runbooks/RUNBOOK-pipeline-automation.md) | Pipeline triggers, state transitions, failures |
| [Rate Limiting](runbooks/RUNBOOK-rate-limiting.md) | 429 handling, backpressure, token bucket tuning |

---

## Reference Data

Specifications and lookup tables.

### Entity Model

| Reference | Description |
|-----------|-------------|
| [Entity Lifecycle](reference/REF-entity-lifecycle.md) | Define, Detect, Populate, Navigate, Persist |
| [Entity Type Table](reference/REF-entity-type-table.md) | Business model entity hierarchy |
| [Asana Hierarchy](reference/REF-asana-hierarchy.md) | Workspace, Project, Section, Task, Subtask |
| [Detection Tiers](reference/REF-detection-tiers.md) | 5-tier detection system specification |
| [Custom Field Catalog](reference/REF-custom-field-catalog.md) | 108 custom fields across 5 models |
| [SDK Stability](reference/REF-sdk-stability.md) | API stability guarantees and versioning |

### Cache Architecture

| Reference | Description |
|-----------|-------------|
| [Cache Architecture](reference/REF-cache-architecture.md) | Provider protocol, backend selection |
| [Cache Staleness](reference/REF-cache-staleness-detection.md) | Detection algorithms, modified-since, coalescing |
| [Cache TTL Strategy](reference/REF-cache-ttl-strategy.md) | Progressive TTL, watermarks, max TTL |
| [Cache Provider Protocol](reference/REF-cache-provider-protocol.md) | CacheProvider interface spec |
| [Cache Invalidation](reference/REF-cache-invalidation.md) | Invalidation strategies and hooks |
| [Cache Patterns](reference/REF-cache-patterns.md) | Common usage patterns and best practices |

### Persistence and Workflow

| Reference | Description |
|-----------|-------------|
| [SaveSession Lifecycle](reference/REF-savesession-lifecycle.md) | Track, Modify, Commit, Validate |
| [Batch Operations](reference/REF-batch-operations.md) | Chunking, parallelization, error handling |
| [Search API](reference/REF-search-api.md) | Search API specification |
| [Seeder Config](reference/REF-seeder-matching-config.md) | BusinessSeeder matching configuration |

### Meta

| Reference | Description |
|-----------|-------------|
| [Glossary](reference/GLOSSARY.md) | 200+ terms |
| [Reference Index](reference/README.md) | Complete reference documentation guide |

---

## Internal Documentation

Project planning and architecture decision records for contributors.

### PRDs (Requirements)

31 Product Requirements Documents in [requirements/](requirements/).

Key PRDs: [Foundation Architecture](requirements/PRD-01-foundation-architecture.md) | [Data Layer](requirements/PRD-02-data-layer.md) | [Batch Save](requirements/PRD-03-batch-save-operations.md) | [Business Domain](requirements/PRD-06-business-domain.md) | [Navigation Hydration](requirements/PRD-05-navigation-hydration.md) | [Custom Fields](requirements/PRD-04-custom-fields.md) | [Entity Write API](requirements/PRD-entity-write-api.md)

### TDDs (Design)

57 Technical Design Documents in [design/](design/).

Key TDDs: [Foundation Architecture](design/TDD-01-foundation-architecture.md) | [Data Layer](design/TDD-02-data-layer.md) | [Batch Save](design/TDD-04-batch-save-operations.md) | [Business Domain](design/TDD-08-business-domain.md) | [Navigation Hydration](design/TDD-07-navigation-hydration.md) | [Entity Write API](design/TDD-entity-write-api.md)

### ADRs (Decisions)

77 Architecture Decision Records in [decisions/](decisions/) and [adr/](adr/).

Browse by topic: SDK Architecture (0001-0005) | Caching (0016-0026, 0115-0134) | Save Orchestration (0035-0040) | Business Model (0050-0054) | Hydration/Resolution (0068-0073) | Process Pipeline (0096-0106) | Detection (0135-0144)

### Test Plans

10 test plans in [testing/](testing/). 6 validation reports in [validation/](validation/).

See [CONVENTIONS.md](CONVENTIONS.md) for naming guidance.
