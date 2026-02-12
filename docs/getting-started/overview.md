# System Architecture Overview

## What is autom8_asana

autom8_asana is a Python SDK that wraps the Asana API with business-domain layers for a marketing/healthcare automation platform. It bridges the gap between Asana's generic task management primitives (tasks, projects, custom fields) and a domain-specific model where tasks represent business entities like Offers, Units, and Businesses, each with typed fields and lifecycle stages.

The SDK provides both a REST API service (FastAPI) and a Python client library. Services can call the REST API for entity resolution, field writes, and queries, while internal automation uses the Python SDK directly to orchestrate workflows, manage caches, and enforce lifecycle rules. The system handles entity resolution (mapping business identifiers like phone numbers to Asana task GIDs), field validation and writes (with automatic enum resolution), multi-tier caching (in-memory, Redis, S3), and lifecycle automation (stage transitions, auto-completion, dependency wiring).

## Component Map

```
┌────────────────────────────────────────────────────────────────────┐
│                       External Callers                             │
│  (autom8_data, autom8_workflow, internal automation scripts)       │
└───────────────┬────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     FastAPI Routes                                │
│  /api/v1/tasks, /api/v1/entity, /v1/resolve, /v1/query           │
│  /api/v1/dataframes, /api/v1/internal, /health                   │
└───────────────┬───────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                        Services                                   │
│  FieldWriteService, QueryService, EntityService, TaskService     │
└───────────────┬───────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                    SDK Clients Layer                              │
│  AsanaClient: TasksClient, ProjectsClient, SectionsClient,       │
│               UsersClient, WorkspacesClient, BatchClient          │
└───────────────┬───────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                   HTTP Transport Layer                            │
│  AsanaHTTPClient (rate limiting, circuit breaker, retries)       │
└───────────────┬───────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                      Asana REST API                               │
│  https://app.asana.com/api/1.0                                   │
└───────────────────────────────────────────────────────────────────┘

Side Components (accessed via Services/Clients):

┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Cache Layer  │  │ Entity Resolution│  │ Lifecycle Engine │
│ (3-tier)     │  │ (5 strategies)   │  │ (4 phases)       │
└──────────────┘  └──────────────────┘  └──────────────────┘

┌──────────────┐  ┌──────────────────┐
│ Automation   │  │ DataFrame        │
│ Pipelines    │  │ Builders         │
└──────────────┘  └──────────────────┘
```

## Request Flow

### Read Path: GET /api/v1/tasks/{gid}

```
1. Client → FastAPI route handler
   GET /api/v1/tasks/123456789

2. Route handler → TaskService
   Passes gid, opt_fields, check_cache=True

3. TaskService → Cache check
   Look up in InMemory → Redis → S3 tiers

4. Cache miss → TasksClient.get_async()
   Build Asana API URL with opt_fields query params

5. TasksClient → AsanaHTTPClient
   HTTP GET with rate limiting, circuit breaker

6. AsanaHTTPClient → Asana API
   GET https://app.asana.com/api/1.0/tasks/123456789?opt_fields=...

7. Asana API → Response
   JSON with task data, custom_fields, memberships

8. TasksClient → Deserialize
   Pydantic Task model (or BusinessEntity subclass if detected)

9. Task → Cache write
   Store in all applicable cache tiers with TTL

10. TaskService → Route handler
    Return Task model

11. Route handler → Client
    HTTP 200 with JSON response
```

### Write Path: PATCH /api/v1/entity/offer/{gid}

```
1. Client → FastAPI route handler
   PATCH /api/v1/entity/offer/123456789
   Body: {"fields": {"weekly_ad_spend": 500, "status": "Active"}}

2. Route handler → FieldWriteService.write_fields_async()
   Passes entity_type="offer", gid, fields dict

3. FieldWriteService → EntityWriteRegistry lookup
   Get WritableEntityInfo (project_gid, allowed_fields)

4. FieldWriteService → TasksClient.get_async()
   Fetch task with custom_fields, enum_options, memberships
   Verify task is in the entity's project

5. FieldWriteService → FieldResolver construction
   Build resolver from task's custom field metadata

6. FieldResolver → Resolve each field
   - Core fields (name, notes, assignee): pass through
   - Custom fields: lookup gid by descriptor name
   - Enum fields: resolve display value to enum_option gid
   - Type validation: number/text/date formats

7. FieldWriteService → Build API payload
   {"custom_fields": {"cf_gid_1": 500, "cf_gid_2": "enum_gid_xyz"}}

8. FieldWriteService → TasksClient.update_async()
   Single PATCH call to Asana API

9. TasksClient → AsanaHTTPClient → Asana API
   PATCH https://app.asana.com/api/1.0/tasks/123456789

10. FieldWriteService → Emit MutationEvent
    Notify cache system: (TASK, gid, UPDATE, [project_gids])

11. MutationInvalidator → Invalidate cache tiers
    Clear InMemory + Redis entries for this task and related queries

12. FieldWriteService → Optional re-fetch
    Get updated task to return fresh field values

13. FieldWriteService → Route handler
    Return WriteFieldsResult with per-field outcomes

14. Route handler → Client
    HTTP 200 with field resolution details
```

## Key Subsystems

### Entity Resolution

Resolves business identifiers (phone number, vertical) to Asana task GIDs. Uses a chain of five strategies: CachedResolution (check session cache) → DirectResolution (GID provided directly) → SiblingResolution (traverse from related entity) → SearchResolution (Asana search API) → RecursiveResolution (fetch parent entities and search children). Each strategy returns a ResolutionResult or passes to the next strategy. Tracks API budget to prevent expensive recursive searches. Used by entity write API, query engine, and automation workflows to translate business keys into Asana task references.

### Entity Write API

Writes fields to entities with automatic resolution and validation. Accepts descriptor names (human-readable field names like "weekly_ad_spend") and display values (enum strings like "Active"). FieldResolver maps descriptors to custom field GIDs and resolves enum display values to enum_option GIDs. Validates field types (number, text, enum, multi_enum, date) against Asana metadata. Single atomic PATCH call per write. Emits MutationEvent for cache invalidation. Returns per-field results with success/failure/resolution details. Route: PATCH /api/v1/entity/{entity_type}/{gid}.

### Query Engine

Query cached entity data with composable predicate trees. Supports field equality, inequality, contains, and aggregation (count, sum, avg). Predicate classes: FieldEquals, FieldContains, And, Or, Not. Query execution against cached dataframes (Polars format) for fast filtering. Route: POST /v1/query with JSON predicate tree. Returns matching entity GIDs with optional field projections. Used by autom8_data for business intelligence queries and by internal automation for conditional triggers.

### Lifecycle Engine

Manages stage transitions with a 4-phase pipeline. Phase 1 (Create): Creates new entities with DNC routing (create_new, reopen, deferred based on stage config). Phase 2 (Configure): Cascades section updates, auto-completes source processes. Phase 3 (Actions): Executes init actions (create child entities, set fields). Phase 4 (Wire): Wires dependencies between entities. Fail-forward design: hard failure only on Phase 1 creation errors, all other phases degrade gracefully with warnings. Routes: Internal use via LifecycleEngine.handle_transition_async(). Accumulates results into AutomationResult with per-phase diagnostics.

### Cache System

Multi-tier caching with InMemory (LRU), Redis (shared across instances), and S3 (archival) providers. TTL management with freshness coordination: short TTLs for volatile data, long TTLs for stable references. Batch warming: preload task batches into cache on startup. Mutation invalidation: MutationEvent triggers selective cache clearing (task-level, project-level, query-level). CacheProvider protocol allows pluggable backends. TieredCacheCoordinator orchestrates tier reads/writes. Cache keys use structured format: "task:123456789", "project:tasks:987654321". Configured via CacheConfig with per-tier TTL and size limits.

### Automation

Pipeline automation for recurring workflows: seeding (create entities from external data sources), conversation audit (sync message threads from Asana comments), pipeline transition (trigger lifecycle stages based on field changes). Workflows defined in `automation/workflows/` with execute() entry point. SeederService constructs entity hierarchies (Business → UnitHolder → Unit → OfferHolder → Offer). SaveSession accumulates mutations and executes as batch. Integration with lifecycle engine for stage transitions. Scheduled via webhook triggers or cron jobs.

### DataFrames

Polars-based dataframe builders with content negotiation. Clients request data via POST /api/v1/dataframes with frame_type (offer, unit, business, asset) and format (json, polars_wire). DataFrame builders fetch entities from cache, extract fields with type coercion, construct Polars DataFrame with schema validation. JSON format returns standard REST response, polars_wire returns binary-serialized DataFrame for efficient cross-service transfer. Schema providers define column names, types, and extractors. Used by autom8_data for analytics and reporting.

## Repository Layout

```
src/autom8_asana/
├── api/                   FastAPI application, routes, middleware
│   ├── main.py            App factory, CORS, rate limiting, observability
│   ├── routes/            Route handlers (tasks, entity, resolver, query)
│   ├── lifespan.py        Startup/shutdown lifecycle (preload, warmup)
│   ├── middleware.py      Request ID, logging, metrics
│   └── errors.py          Exception handlers (SDK errors → HTTP responses)
│
├── clients/               Asana API client wrappers
│   ├── tasks.py           TasksClient (get, create, update, delete)
│   ├── projects.py        ProjectsClient (get, list tasks)
│   ├── sections.py        SectionsClient (get, add task, list tasks)
│   ├── users.py           UsersClient (get, search)
│   ├── workspaces.py      WorkspacesClient (get, list users)
│   └── data/              DataServiceClient (autom8_data integration)
│
├── models/                Pydantic models
│   ├── task.py            Core Task model (Asana API resource)
│   ├── project.py         Project, Section models
│   ├── user.py            User, Workspace models
│   └── business/          Business entity hierarchy
│       ├── base.py        BusinessEntity base class
│       ├── business.py    Business (top-level entity)
│       ├── unit.py        Unit, UnitHolder
│       └── offer.py       Offer, OfferHolder
│
├── resolution/            Entity resolution strategies and field resolver
│   ├── strategies.py      ResolutionStrategy ABC, 5 concrete strategies
│   ├── universal.py       UniversalResolutionStrategy (strategy chain)
│   ├── field_resolver.py  FieldResolver (descriptor → GID, enum resolution)
│   ├── context.py         ResolutionContext (client, session cache)
│   └── write_registry.py  EntityWriteRegistry (writable entity metadata)
│
├── lifecycle/             Stage transition engine
│   ├── engine.py          LifecycleEngine (4-phase pipeline orchestrator)
│   ├── services/          Phase services (creation, cascade, actions, wiring)
│   ├── config.py          LifecycleConfig, StageConfig YAML schema
│   └── loader.py          Config loader from YAML files
│
├── services/              Business logic services
│   ├── field_write_service.py  FieldWriteService (entity write orchestration)
│   ├── entity_service.py       EntityService (entity CRUD operations)
│   ├── query_service.py        QueryService (predicate-based queries)
│   └── errors.py               Service-layer exceptions
│
├── cache/                 Multi-tier cache system
│   ├── providers/         CacheProvider implementations (InMemory, Redis, S3)
│   ├── integration/       TieredCacheCoordinator, MutationInvalidator
│   ├── policies/          TTL policies, freshness coordination
│   ├── models/            CacheKey, CacheEntry, MutationEvent
│   └── connections/       Redis/S3 connection managers
│
├── automation/            Pipeline automation
│   ├── pipeline.py        Pipeline orchestrator
│   ├── seeding.py         SeederService (entity creation from external data)
│   └── workflows/         Workflow implementations (conversation_audit, etc)
│
├── dataframes/            DataFrame builders
│   ├── builders.py        Frame builders (OfferFrameBuilder, UnitFrameBuilder)
│   ├── schemas.py         Column schemas and type definitions
│   ├── extractors.py      Field extractors with type coercion
│   └── decorator.py       Content negotiation (JSON vs Polars wire format)
│
├── transport/             HTTP client layer
│   ├── asana_http.py      AsanaHTTPClient (rate limiting, circuit breaker)
│   └── rate_limiter.py    Token bucket rate limiter
│
├── persistence/           SaveSession and holder construction
│   ├── save_session.py    SaveSession (mutation accumulator, batch executor)
│   ├── holder_construction.py  Holder builder (construct entity hierarchies)
│   └── models.py          AutomationResult, ValidationMessage
│
├── batch/                 Batch API client
│   └── batch_client.py    BatchClient (batch task fetches)
│
├── core/                  Core registries and exceptions
│   ├── entity_registry.py EntityProjectRegistry (entity type detection)
│   ├── project_registry.py ProjectTypeRegistry, WorkspaceProjectRegistry
│   └── exceptions.py      Error tuples (CACHE_TRANSIENT_ERRORS, etc)
│
├── client.py              AsanaClient (main SDK entry point)
├── config.py              AsanaConfig (SDK configuration)
├── exceptions.py          SDK exceptions (NotFoundError, RateLimitError)
└── settings.py            Application settings (env var loading)
```

## Related Reading

- Getting Started Guides: `docs/getting-started/` (client setup, authentication, basic operations)
- API Routes Reference: `docs/api/` (endpoint specifications, request/response schemas)
- Entity Model Guide: `docs/models/` (entity hierarchy, field descriptors, navigation)
- Resolution System: `docs/resolution/` (strategy chain, field resolver, write registry)
- Lifecycle Engine: `docs/lifecycle/` (stage config, DNC routing, phase execution)
- Cache Architecture: `docs/cache/` (tier providers, TTL policies, invalidation)
- Automation Workflows: `docs/automation/` (pipeline patterns, seeding, workflows)
