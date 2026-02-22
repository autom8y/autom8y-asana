# Architectural Review 1: Topology

**Date**: 2026-02-18
**Scope**: 1000ft topology view of autom8y-asana
**Methodology**: 10-agent exploration swarm + synthesis
**Review ID**: ARCH-REVIEW-1

---

## 1. Overall Architecture Overview

autom8y-asana is an async-first Python SDK and application layer that mediates between the Asana REST API and downstream business automation. It provides:

- **Entity modeling**: A hierarchical business model (Business > Unit > Contact/Offer/Process/Location/Hours) with holder intermediaries
- **Caching**: Multi-tier caching (Redis hot + S3 cold for entities; Memory + S3 for DataFrames) to minimize Asana API calls
- **DataFrames**: Polars-based analytical views of entity data with section-scoped queries
- **Query engine**: A composable predicate DSL that compiles to Polars expressions
- **Automation**: Pipeline conversion rules and lifecycle management for entity state transitions
- **Detection**: 5-tier entity type detection from raw Asana task data

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Runtime | Python 3.11+, asyncio | Async-first execution |
| Models | Pydantic v2 (frozen) | Immutable entity models with validation |
| DataFrames | Polars | Columnar analytics, section-scoped queries |
| API | FastAPI | HTTP API layer |
| Cache Hot | Redis | Sub-millisecond entity reads |
| Cache Cold | S3 (Parquet) | Durable persistence, DataFrame storage |
| Deployment | Docker (ECS + Lambda) | Single image, env-driven dispatch |
| External API | Asana REST API | Primary data source |
| Platform | 7 autom8y-* packages | Shared infrastructure (cache, logging, config, auth, transport, metrics, lambda) |

### Package Map

```
src/autom8_asana/                    # Root package (~111K LOC, 383 files)
    __init__.py                      # 236 lines, re-exports, lazy DataFrame loading
    client.py                        # 1,041 lines, AsanaClient facade
    config.py                        # Configuration
    settings.py                      # Settings
    exceptions.py                    # SDK exceptions
    entrypoint.py                    # Lambda/ECS entry dispatch

    api/                  (8,880 L)  # FastAPI routes, preload, lifespan
    auth/                   (667 L)  # Authentication providers
    automation/           (9,318 L)  # Pipeline rules, seeding, events, polling, workflows
    batch/                  (687 L)  # Batch operations
    cache/               (15,658 L)  # Multi-tier caching subsystem
    clients/             (11,245 L)  # Asana API clients (tasks, tags, sections, etc.)
    core/                 (2,911 L)  # Entity registry, exceptions, timing, creation
    dataframes/          (13,728 L)  # Polars DataFrames, builders, extractors, schemas
    lambda_handlers/      (1,977 L)  # Cache warmer, scheduled handlers
    lifecycle/            (4,032 L)  # Lifecycle engine, creation, seeding
    metrics/                (616 L)  # Metrics collection
    models/              (15,356 L)  # Business entity models, detection, matching
    observability/          (343 L)  # W3C trace propagation, log-trace correlation
    patterns/               (444 L)  # Reusable patterns
    persistence/          (8,137 L)  # SaveSession, change tracking, cascade execution
    protocols/              (610 L)  # Protocol definitions (CacheProvider, AuthProvider, etc.)
    query/                (1,935 L)  # Query engine, compiler, models, guards
    resolution/           (1,799 L)  # Entity resolution
    search/                 (925 L)  # Search functionality
    services/             (5,695 L)  # Query service, resolver, universal strategy
    transport/            (1,700 L)  # HTTP transport, Asana client
```

### Deployment Model

Single Docker image, environment-driven dispatch:

```
Docker Image
    |
    +-- ECS Task (ENTRYPOINT=api)
    |     |-- FastAPI server
    |     |-- APScheduler (dev-mode cache warming)
    |     |-- Redis connection pool
    |     +-- S3 client
    |
    +-- Lambda Function (ENTRYPOINT=lambda)
          |-- cache_warmer handler
          |-- hierarchy_warmer handler
          |-- scheduled task handlers
          +-- timeout self-continuation
```

The `entrypoint.py` module dispatches based on `EXECUTION_MODE` environment variable. Lambda handlers use checkpoint-resume for large operations that exceed timeout limits.

---

## 2. Entity Model Architecture

### Entity Type Hierarchy

17 entity types organized in 4 categories:

```
BUSINESS (root)
    |
    +-- CONTACT_HOLDER    --> CONTACT (leaf)
    +-- UNIT_HOLDER        --> UNIT (composite)
    |                          |
    |                          +-- OFFER_HOLDER     --> OFFER (leaf)
    |                          +-- PROCESS_HOLDER   --> PROCESS (leaf)
    |
    +-- LOCATION_HOLDER   --> LOCATION (leaf)
    +-- DNA_HOLDER        --> (no leaf, holds DNA data)
    +-- RECONCILIATIONS_HOLDER --> (reconciliation data)
    +-- ASSET_EDIT_HOLDER --> (asset edit data)
    +-- VIDEOGRAPHY_HOLDER --> (videography data)
    +-- HOURS             --> (leaf, direct child)
```

**Source**: `src/autom8_asana/models/business/detection/types.py` -- `EntityType` enum

| Category | Count | Types |
|----------|-------|-------|
| Root | 1 | BUSINESS |
| Holders | 9 | CONTACT_HOLDER, UNIT_HOLDER, LOCATION_HOLDER, DNA_HOLDER, RECONCILIATIONS_HOLDER, ASSET_EDIT_HOLDER, VIDEOGRAPHY_HOLDER, OFFER_HOLDER, PROCESS_HOLDER |
| Composite | 1 | UNIT |
| Leaf | 5 | CONTACT, OFFER, PROCESS, LOCATION, HOURS |
| Fallback | 1 | UNKNOWN |

### Descriptor-Driven Field Definitions

Per ADR-0081 and ADR-0082, entity models use descriptors instead of explicit `@property` implementations.

**Source**: `src/autom8_asana/models/business/descriptors.py`

Three descriptor families:

| Descriptor | Purpose | Example |
|-----------|---------|---------|
| `ParentRef[T]` | Navigate to parent entity | `business = ParentRef[Business](holder_attr="_contact_holder")` |
| `HolderRef[T]` | Navigate to holder | `contact_holder = HolderRef[ContactHolder]()` |
| `CustomFieldDescriptor[T]` | Access Asana custom fields | `company_id = TextField()`, `mrr = NumberField()`, `vertical = EnumField()` |

Custom field descriptors auto-register via `__set_name__` + `__init_subclass__` two-phase pattern (ADR-0082), generating a `Fields` inner class that maps Python attribute names to Asana custom field GIDs.

This eliminates ~800 lines of duplicated `@property` implementations across entity classes.

### HolderFactory Pattern

Per TDD-PATTERNS-C, holders use `__init_subclass__` for declarative definitions.

**Source**: `src/autom8_asana/models/business/holder_factory.py`

```python
# Before: ~70 lines per holder
class DNAHolder(HolderMixin, Task):
    _children: list[Any] = PrivateAttr(default_factory=list)
    # ... 70 lines of boilerplate ...

# After: 3-5 lines
class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    '''Holder for DNA children.'''
    pass
```

9 holders defined this way, each reducing from ~70 lines to 3-5 lines.

### Entity Registration

**Source**: `src/autom8_asana/core/entity_registry.py`

`EntityRegistry` is the single source of truth (SSoT) for entity metadata:

- `EntityDescriptor`: Frozen dataclass per entity type capturing all metadata
- `ENTITY_DESCRIPTORS`: Module-level tuple of all descriptors
- O(1) lookup by name, project GID, and EntityType
- Import-time integrity validation (checks 6a-6f)
- Backward-compatible facades: `ENTITY_TYPES`, `DEFAULT_ENTITY_TTLS`, `ENTITY_ALIASES`, `DEFAULT_KEY_COLUMNS`

All 4 DataFrame layer consumers are descriptor-driven:
1. `SchemaRegistry._ensure_initialized()` -- auto-discovers schemas via `schema_module_path`
2. `_create_extractor()` -- resolves extractor classes via `extractor_class_path`
3. `ENTITY_RELATIONSHIPS` -- derived from `join_keys` on descriptors
4. `_build_cascading_field_registry()` -- discovers providers via `cascading_field_provider` flag

### Entity Detection (5 Tiers)

**Source**: `src/autom8_asana/models/business/detection/` (tier1.py through tier4.py, facade.py)

| Tier | Method | Confidence | Source |
|------|--------|-----------|--------|
| 1 | Project membership | 1.0 (deterministic) | `tier1.py` |
| 2 | Name patterns | 0.6 (unreliable) | `tier2.py` |
| 3 | Parent inference | 0.8 (reliable) | `tier3.py` |
| 4 | Structure inspection | 0.9 (structural) | `tier4.py` |
| 5 | Unknown fallback | 0.0 | Default |

Detection produces `DetectionResult` (frozen dataclass):
- `entity_type`: Detected type or `EntityType.UNKNOWN`
- `confidence`: 0.0 to 1.0
- `tier`: Which tier succeeded
- `needs_healing`: Whether project membership repair is needed
- `expected_project_gid`: For healing

---

## 3. Section Classification System

### SectionClassifier

**Source**: `src/autom8_asana/models/business/activity.py`

A frozen dataclass providing O(1) section-to-activity classification:

```python
@dataclass(frozen=True)
class SectionClassifier:
    entity_type: str           # "offer" or "unit"
    project_gid: str           # Asana project GID
    _mapping: dict[str, AccountActivity]  # lowercase name -> activity

    def classify(self, section_name: str) -> AccountActivity | None: ...
    def sections_for(self, *categories: AccountActivity) -> frozenset[str]: ...
```

### AccountActivity Enum

```python
class AccountActivity(str, Enum):
    ACTIVE = "active"
    ACTIVATING = "activating"
    INACTIVE = "inactive"
    IGNORED = "ignored"
```

Priority ordering: `ACTIVE > ACTIVATING > INACTIVE > IGNORED` (via `ACTIVITY_PRIORITY` tuple).

### Classifier Instances

| Classifier | Entity Type | Section Count | Source |
|-----------|-------------|---------------|--------|
| `OFFER_CLASSIFIER` | offer | 33 sections | `activity.py` |
| `UNIT_CLASSIFIER` | unit | 14 sections | `activity.py` |

### ProcessSection

**Source**: `src/autom8_asana/models/business/process.py` (or related module)

`ProcessSection` is a separate enum for process pipeline stages, distinct from the offer/unit section classification. Process sections represent pipeline stages (e.g., onboarding steps) rather than activity states.

### Section Name Representations

Section names exist in three parallel representations (a known inconsistency):

1. **SectionClassifier mappings** -- lowercase string keys in frozen dict
2. **OfferSection enum** (`src/autom8_asana/models/business/sections.py`) -- hardcoded GIDs
3. **Asana API responses** -- raw section names from API

---

## 4. DataFrame Subsystem

### Architecture

**Source**: `src/autom8_asana/dataframes/` (13,728 LOC, 44 files)

The DataFrame subsystem provides Polars-based analytical views of entity data.

```
DataFrames Architecture
    |
    +-- builders/           # 3 tiers of DataFrame construction
    |     +-- base.py       # DataFrameBuilder (base tier)
    |     +-- section.py    # SectionDataFrameBuilder (section-scoped)
    |     +-- task_cache.py # ProgressiveProjectBuilder (cache-integrated)
    |
    +-- extractors/         # Entity-specific row extraction
    |     +-- base.py       # BaseExtractor with source prefix pattern
    |     +-- contact.py    # ContactExtractor
    |     +-- unit.py       # UnitExtractor
    |
    +-- models/             # Data models
    |     +-- schema.py     # DataFrameSchema, ColumnDef
    |     +-- registry.py   # SchemaRegistry (singleton, lazy-init)
    |     +-- row.py        # TaskRow, UnitRow, ContactRow (frozen)
    |
    +-- schemas/            # Entity-specific schema definitions
    +-- resolver/           # Custom field resolution
    +-- views/              # CascadeView, DataFrameView
    +-- cache_integration.py  # DataFrameCacheIntegration
    +-- section_persistence.py  # SectionManifest, S3 persistence
    +-- storage.py          # S3 storage backend
    +-- watermark.py        # Incremental sync timestamps
```

### Builder Tiers

| Tier | Class | Purpose | Cache Integration |
|------|-------|---------|-------------------|
| 1 | `DataFrameBuilder` | Base builder, in-memory | None |
| 2 | `SectionDataFrameBuilder` | Section-scoped building | None |
| 3 | `ProgressiveProjectBuilder` | Full project building with cache | Memory + S3 tiered |

### Extractor Pattern

Extractors transform entity data into flat rows using source prefixes:

```
task__name          # From Asana task fields
task__gid           # From Asana task fields
cf__company_id      # From custom fields (cf_ prefix)
rel__business_name  # From related entities (rel_ prefix)
```

Each entity type has a dedicated extractor class resolved via `EntityDescriptor.extractor_class_path`.

### Schema Registry

**Source**: `src/autom8_asana/dataframes/models/registry.py`

`SchemaRegistry` is a singleton that auto-discovers schemas via `EntityDescriptor.schema_module_path`:

- Lazy initialization on first access
- Validates schema/extractor/row model triad at import time
- Thread-safe via class-level lock
- Per-entity `DataFrameSchema` with typed `ColumnDef` entries

### S3 Persistence

**Source**: `src/autom8_asana/dataframes/section_persistence.py`

`SectionManifest` provides checkpoint-resume for large DataFrame builds:

- Per-section progress tracking
- S3 Parquet storage
- Resume from last successful section on restart
- Used by Lambda warmer for operations spanning timeout boundaries

### Row Models

Frozen Pydantic models for type-safe row data:

| Model | Source | Fields |
|-------|--------|--------|
| `TaskRow` | `models/row.py` | Standard task fields |
| `UnitRow` | `models/row.py` | Unit-specific fields |
| `ContactRow` | `models/row.py` | Contact-specific fields |

---

## 5. Query DSP (Dynamic Query Service)

### Architecture

**Source**: `src/autom8_asana/query/` (1,935 LOC, 9 files)

```
Query Pipeline
    |
    +-- models.py       # Predicate AST (Comparison, AndGroup, OrGroup, NotGroup)
    +-- compiler.py     # PredicateCompiler: AST -> Polars expressions
    +-- engine.py       # QueryEngine: orchestrates execution
    +-- guards.py       # QueryLimits, depth checking
    +-- hierarchy.py    # Entity relationship navigation
    +-- join.py         # Cross-entity join execution
    +-- aggregator.py   # Aggregation support
    +-- errors.py       # Query-specific errors
```

### Predicate AST

**Source**: `src/autom8_asana/query/models.py`

Discriminated union using Pydantic v2:

```python
PredicateNode = Comparison | AndGroup | OrGroup | NotGroup

class Comparison(BaseModel):    # Leaf: field + op + value
class AndGroup(BaseModel):      # All children must match
class OrGroup(BaseModel):       # At least one child matches
class NotGroup(BaseModel):      # Negation
```

### Operator Matrix

10 operators x 8 dtypes:

| Operator | Enum | Description |
|----------|------|-------------|
| `eq` | `Op.EQ` | Equality |
| `ne` | `Op.NE` | Not equal |
| `gt` | `Op.GT` | Greater than |
| `lt` | `Op.LT` | Less than |
| `gte` | `Op.GTE` | Greater or equal |
| `lte` | `Op.LTE` | Less or equal |
| `in` | `Op.IN` | In set |
| `not_in` | `Op.NOT_IN` | Not in set |
| `contains` | `Op.CONTAINS` | String contains |
| `starts_with` | `Op.STARTS_WITH` | String starts with |

### PredicateCompiler

**Source**: `src/autom8_asana/query/compiler.py`

Stateless compiler: AST -> `pl.Expr` with operator x dtype compatibility matrix + type coercion.

- Schema passed per-call (same compiler instance serves multiple entity types)
- Explicit `OPERATOR_MATRIX` defines valid operator/dtype combinations
- Type coercion for date/datetime/number values
- Reusable across queries

### QueryEngine

**Source**: `src/autom8_asana/query/engine.py`

Orchestrates filtered row retrieval:

```python
@dataclass
class QueryEngine:
    query_service: EntityQueryService
    compiler: PredicateCompiler
    limits: QueryLimits
```

Composes: cache access -> schema validation -> predicate compilation -> section scoping -> response shaping.

### Cross-Entity Joins

`MAX_JOIN_DEPTH = 1` -- single-hop joins only (e.g., task -> unit, but not task -> unit -> business).

Join relationships derived from `EntityDescriptor.join_keys` in the EntityRegistry.

### Guards and Limits

**Source**: `src/autom8_asana/query/guards.py`

`QueryLimits` enforces:
- Maximum predicate depth
- Maximum result row count
- Aggregate group limits
- Section scoping validation

Guards are first-class concepts, not afterthoughts.

---

## 6. The Intelligence Loop

How the subsystems connect end-to-end:

```
                         Asana REST API
                              |
                    +---------+---------+
                    |                   |
              Entity Cache          DataFrame Cache
              (Redis+S3)            (Memory+S3)
                    |                   |
              Entity Models        Polars DataFrames
              (Pydantic v2)        (typed schemas)
                    |                   |
              Detection            SchemaRegistry
              (5 tiers)            (auto-discovery)
                    |                   |
              EntityRegistry       Extractors
              (SSoT)               (source prefixes)
                    |                   |
                    +-------+-----------+
                            |
                       Query Engine
                       (predicate AST)
                            |
                    +---------+---------+
                    |                   |
              API Routes           Automation
              (FastAPI)            (pipeline rules)
                    |                   |
              Downstream            SaveSession
              Consumers             (persistence)
```

The cycle:
1. **Fetch**: Asana API data fetched into entity cache
2. **Detect**: 5-tier detection classifies entity types
3. **Model**: Pydantic v2 frozen models hydrate entity data
4. **Extract**: Extractors build DataFrames from entity data
5. **Query**: Predicate engine enables filtered analytical queries
6. **Automate**: Pipeline rules and lifecycle engine drive state transitions
7. **Persist**: SaveSession commits changes back through Asana API
8. **Invalidate**: Cache invalidation triggers re-fetch cycle

---

## 7. Key Files Reference

### Entity Model

| File | Lines | Purpose |
|------|-------|---------|
| `models/business/detection/types.py` | ~110 | EntityType enum, DetectionResult, confidence constants |
| `models/business/descriptors.py` | ~400 | ParentRef, HolderRef, CustomFieldDescriptor, Fields auto-gen |
| `models/business/holder_factory.py` | ~200 | HolderFactory base class with __init_subclass__ |
| `models/business/base.py` | -- | BusinessEntity base, HolderMixin |
| `models/business/business.py` | ~810 | Business root entity |
| `models/business/unit.py` | -- | Unit composite entity |
| `models/business/contact.py` | -- | Contact leaf entity |
| `models/business/offer.py` | -- | Offer leaf entity |
| `models/business/process.py` | -- | Process leaf entity |
| `models/business/activity.py` | ~150 | SectionClassifier, AccountActivity, OFFER_CLASSIFIER, UNIT_CLASSIFIER |
| `models/business/sections.py` | ~47 | OfferSection enum (hardcoded GIDs) |
| `models/business/hydration.py` | ~780 | Entity hydration from raw Asana data |
| `models/business/registry.py` | ~240 | Class name to EntityType mapping |
| `models/business/_bootstrap.py` | ~150 | register_all_models() bootstrap |
| `core/entity_registry.py` | ~700 | EntityRegistry, EntityDescriptor, get_registry() |

### DataFrame Subsystem

| File | Lines | Purpose |
|------|-------|---------|
| `dataframes/builders/base.py` | -- | DataFrameBuilder base tier |
| `dataframes/builders/section.py` | -- | SectionDataFrameBuilder |
| `dataframes/builders/task_cache.py` | -- | ProgressiveProjectBuilder |
| `dataframes/extractors/base.py` | -- | BaseExtractor with source prefixes |
| `dataframes/models/schema.py` | -- | DataFrameSchema, ColumnDef |
| `dataframes/models/registry.py` | -- | SchemaRegistry singleton |
| `dataframes/models/row.py` | -- | TaskRow, UnitRow, ContactRow |
| `dataframes/section_persistence.py` | -- | SectionManifest, S3 persistence |
| `dataframes/watermark.py` | ~200 | WatermarkRepository, incremental sync |
| `dataframes/cache_integration.py` | -- | DataFrameCacheIntegration |

### Query Engine

| File | Lines | Purpose |
|------|-------|---------|
| `query/models.py` | ~100 | PredicateNode AST (Comparison, And/Or/Not groups) |
| `query/compiler.py` | ~200 | PredicateCompiler, OPERATOR_MATRIX |
| `query/engine.py` | ~300 | QueryEngine orchestrator |
| `query/guards.py` | ~100 | QueryLimits, predicate_depth |
| `query/hierarchy.py` | -- | Entity relationship navigation |
| `query/join.py` | -- | Cross-entity join execution, JoinSpec |
| `query/aggregator.py` | -- | Aggregation support |

### Cache Subsystem

| File | Lines | Purpose |
|------|-------|---------|
| `cache/__init__.py` | ~60 | Public API exports |
| `cache/backends/redis.py` | -- | Redis cache backend |
| `cache/backends/s3.py` | -- | S3 cache backend |
| `cache/backends/memory.py` | -- | In-memory cache backend |
| `cache/providers/tiered.py` | -- | TieredCacheProvider (Redis+S3) |
| `cache/models/entry.py` | -- | CacheEntry, EntryType, EntityCacheEntry |
| `cache/models/freshness.py` | ~36 | Freshness enum (STRICT, EVENTUAL, IMMEDIATE) |
| `cache/models/completeness.py` | -- | CompletenessLevel (4 levels) |
| `protocols/cache.py` | -- | CacheProvider protocol, WarmResult |

### Core Infrastructure

| File | Lines | Purpose |
|------|-------|---------|
| `client.py` | 1,041 | AsanaClient facade |
| `config.py` | -- | Configuration |
| `settings.py` | -- | Settings |
| `core/exceptions.py` | ~322 | Error tuples (S3_TRANSPORT_ERRORS, ASANA_API_ERRORS, etc.) |
| `core/timing.py` | ~5 | elapsed_ms() utility |
| `core/creation.py` | -- | Shared creation primitives (post-WS6) |
| `protocols/__init__.py` | ~21 | CacheProvider, AuthProvider, LogProvider, ItemLoader, ObservabilityHook |
| `persistence/session.py` | 1,853 | SaveSession UoW |
| `clients/data/client.py` | 2,165 | DataServiceClient |
