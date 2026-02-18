# Dependency Map: autom8y-asana

**Date**: 2026-02-18
**Review ID**: ARCH-REVIEW-1 (Phase 2 formalization)
**Commit**: `be4c23a` (main)
**Scope**: Intra-repo dependency graph across 27 packages (~111K LOC) + 7 external platform packages
**Complexity**: DEEP-DIVE
**Upstream Artifact**: `TOPOLOGY-AUTOM8Y-ASANA.md` (topology-inventory)

---

## 1. Dependency Graph

### 1.1 Internal Package Adjacency Table (Directed: Source -> Target)

Each row represents a package that imports from the target column. "D" = direct import (module-level), "L" = lazy/deferred import (inside function body or `__getattr__`), "T" = TYPE_CHECKING-only import.

| Source Package | Target Package | Import Type | Import Count | Confidence |
|---------------|---------------|-------------|-------------|------------|
| `__init__` | `models` | D | 15+ | High |
| `__init__` | `config` | D | 5+ | High |
| `__init__` | `persistence` | D | 2 | High |
| `__init__` | `protocols` | D | 5 | High |
| `__init__` | `batch` | D | 4 | High |
| `client` | `clients` | D | 13 | High |
| `client` | `cache` | D | 3 | High |
| `client` | `config` | D | 2 | High |
| `client` | `persistence` | D | 1 | High |
| `client` | `protocols` | D+T | 5 | High |
| `client` | `transport` | D | 1 | High |
| `client` | `core` | L | 1 | High |
| `api` | `core` | D+L | 6 | High |
| `api` | `services` | L | 8 | High |
| `api` | `cache` | D | 2 | High |
| `api` | `config` | L | 5 | High |
| `api` | `settings` | D | 2 | High |
| `api` | `models` | T | 1 | High |
| `automation` | `core` | D | 5 | High |
| `automation` | `persistence` | D | 4 | High |
| `automation` | `models` | D | 2 | High |
| `automation` | `clients` | D | 3 | High |
| `automation` | `services` | L | 1 | High |
| `batch` | `clients` | D | 1 | High |
| `batch` | `transport` | D | 1 | High |
| `cache` | `core` | D | 4 | High |
| `cache` | `protocols` | D+T | 8 | High |
| `cache` | `config` | L | 4 | High |
| `cache` | `settings` | D | 3 | High |
| `clients` | `core` | D | 6 | High |
| `clients` | `protocols` | T | 6 | High |
| `clients` | `cache` | L | 6 | High |
| `clients` | `config` | T | 1 | High |
| `clients` | `settings` | D | 3 | High |
| `clients` | `transport` | T | 1 | High |
| `config` | `core` | D | 1 | High |
| `config` | `cache` | L | 5 | High |
| `config` | `settings` | D+L | 3 | High |
| `core` | `core` (self) | D | 4 | High |
| `dataframes` | `core` | D | 5 | High |
| `dataframes` | `config` | D | 3 | High |
| `dataframes` | `settings` | L | 1 | High |
| `dataframes` | `cache` | D | 4 | High |
| `dataframes` | `protocols` | T | 2 | High |
| `dataframes` | `clients` | T | 1 | High |
| `lifecycle` | `core` | D | 4 | High |
| `lifecycle` | `persistence` | D | 1 | High |
| `lifecycle` | `resolution` | D | 1 | High |
| `lifecycle` | `models` | L | 6 | High |
| `lambda_handlers` | `services` | L | 4 | High |
| `lambda_handlers` | `clients` | L | 1 | High |
| `models` | `dataframes` | L | 5 | High |
| `models` | `core` | L | 1 | High |
| `models` | `cache` | D | 1 | High |
| `persistence` | `clients` | D | 1 | High |
| `persistence` | `transport` | D | 1 | High |
| `persistence` | `models` | T+L | 5 | High |
| `persistence` | `cache` | L | 1 | High |
| `persistence` | `core` | D | 1 | High |
| `query` | `services` | D | 2 | High |
| `query` | `dataframes` | D | 2 | High |
| `query` | `core` | L | 1 | High |
| `resolution` | `models` | D | 4 | High |
| `resolution` | `core` | L | 1 | High |
| `search` | `dataframes` | D | 2 | High |
| `services` | `cache` | D | 3 | High |
| `services` | `core` | D+L | 6 | High |
| `services` | `dataframes` | L | 12 | High |
| `services` | `models` | L | 4 | High |
| `services` | `config` | D | 1 | High |
| `services` | `settings` | D | 1 | High |
| `services` | `resolution` | D | 2 | High |
| `services` | `query` | L | 2 | High |
| `transport` | `config` | T | 2 | High |
| `transport` | `protocols` | T | 2 | High |

### 1.2 Fan-In Summary (Packages Sorted by Inbound Dependency Count)

| Target Package | Fan-In Count | Source Packages |
|---------------|-------------|-----------------|
| `core` | 14 | `api`, `automation`, `cache`, `clients`, `config`, `dataframes`, `lifecycle`, `models`, `persistence`, `query`, `resolution`, `services`, `client`, `transport` |
| `models` | 10 | `__init__`, `api`, `automation`, `lifecycle`, `persistence`, `resolution`, `services`, `client`, `dataframes` (via detection), `search` |
| `config` | 10 | `__init__`, `api`, `cache`, `clients`, `dataframes`, `services`, `transport`, `client`, `config` (self via settings), `lambda_handlers` |
| `cache` | 9 | `api`, `clients`, `config`, `dataframes`, `persistence`, `services`, `client`, `_defaults`, `protocols` |
| `protocols` | 7 | `__init__`, `cache`, `clients`, `client`, `dataframes`, `observability`, `transport` |
| `services` | 6 | `api`, `automation`, `lambda_handlers`, `query`, `core` (schema), `lifecycle` |
| `persistence` | 5 | `__init__`, `automation`, `client`, `lifecycle`, `services` (via models) |
| `clients` | 5 | `automation`, `batch`, `client`, `dataframes`, `persistence` |
| `settings` | 7 | `api`, `cache`, `clients`, `config`, `dataframes`, `services`, `_defaults` |
| `dataframes` | 5 | `models`, `query`, `search`, `services`, `lifecycle` |
| `transport` | 3 | `batch`, `client`, `persistence` |
| `resolution` | 3 | `lifecycle`, `services`, `resolution` (self) |

### 1.3 Fan-Out Summary (Packages Sorted by Outbound Dependency Count)

| Source Package | Fan-Out Count | Target Packages |
|---------------|--------------|-----------------|
| `services` | 9 | `cache`, `core`, `config`, `dataframes`, `models`, `query`, `resolution`, `settings`, `services` (self) |
| `client` | 7 | `cache`, `clients`, `config`, `core`, `persistence`, `protocols`, `transport` |
| `api` | 6 | `cache`, `config`, `core`, `models`, `services`, `settings` |
| `automation` | 5 | `clients`, `core`, `models`, `persistence`, `services` |
| `persistence` | 6 | `cache`, `clients`, `core`, `models`, `transport`, `persistence` (self) |
| `dataframes` | 5 | `cache`, `clients`, `config`, `core`, `protocols` |
| `cache` | 4 | `config`, `core`, `protocols`, `settings` |
| `lifecycle` | 5 | `core`, `models`, `persistence`, `resolution`, `lifecycle` (self) |

### 1.4 External Platform Package Dependencies

| autom8y-* Package | Internal Consumers | Import Sites | Coupling Level | Confidence |
|-------------------|-------------------|-------------|----------------|------------|
| `autom8y-log` | `core`, `services`, `cache`, `clients`, `persistence`, `lifecycle`, `automation`, `resolution`, `query`, `dataframes`, `models`, `config`, `api`, `auth`, `transport`, `lambda_handlers` | 55+ | Loose (facade only) | High |
| `autom8y-http` | `config`, `clients/data/client` | 6 | Tight (circuit breaker, retry, config types) | High |
| `autom8y-cache` | `cache/policies/hierarchy`, `cache/integration/upgrader`, `cache/integration/schema_providers`, `cache/models/freshness` | 6 | Tight (HierarchyTracker, CacheEntry, SchemaVersion, CompatibilityMode) | High |
| `autom8y-config` | `auth/bot_pat`, `services/gid_push`, `cache/dataframe/factory` | 3 | Medium (lambda secret resolution) | High |
| `autom8y-auth` | `auth/jwt_validator` | 2 | Medium (AuthClient, ServiceClaims, AuthSettings) | High |
| `autom8y-telemetry` | `api/main` | 1 | Medium (instrument_app, graceful if missing) | High |
| `autom8y-core` | (transitive via other autom8y-* packages) | 0 direct | Loose (transitive) | Medium |

---

## 2. Coupling Analysis

### 2.1 Coupling Context Methodology

Before scoring, each pair undergoes three context checks:

1. **Bounded context check**: Are the two packages within the same bounded context (domain-aligned cohesion)?
2. **Intentionality check**: Is the coupling designed (explicit contract, shared library) or incidental (duplicated types, implicit conventions)?
3. **Directionality check**: Is the dependency unidirectional (healthy) or circular (problematic)?

### 2.2 Coupling Score Table (All Significant Package Pairs)

Coupling type classification:
- **Data coupling**: Shared data models (Pydantic types, dataclasses) passed between packages
- **Stamp coupling**: Entire composite structures passed when only parts are used
- **Control coupling**: One package controls the flow of another (registry lookups, strategy selection)
- **Temporal coupling**: Packages must execute in a specific order (bootstrap, initialization)

| Package A | Package B | Score | Coupling Type | Bounded Context? | Intentional? | Direction | Confidence |
|-----------|-----------|-------|---------------|-------------------|-------------|-----------|------------|
| `cache` | `services` | **8/10** | Data + Control | No (infrastructure vs. domain) | Partially -- protocol-mediated but models leak | Bidirectional (services -> cache, cache types in services) | High |
| `services` | `dataframes` | **8/10** | Data + Control | Yes (query/resolution domain) | Yes -- designed data pipeline | Unidirectional (services -> dataframes) | High |
| `models` | `persistence` | **7/10** | Data + Stamp | Yes (entity domain) | Yes -- UoW requires entity models | Bidirectional (persistence imports model types, models.common used in session) | High |
| `models` | `resolution` | **7/10** | Data + Control | Yes (entity domain) | Yes -- resolution resolves business entities | Unidirectional (resolution -> models) | High |
| `core` | `services` | **7/10** | Control + Data | No (utility vs. domain) | Yes -- registry is shared knowledge | Unidirectional (services -> core) | High |
| `automation` | `persistence` | **7/10** | Data + Temporal | Yes (lifecycle domain) | Yes -- automation commits via SaveSession | Unidirectional (automation -> persistence) | High |
| `cache` | `config` | **6/10** | Data | No (infrastructure vs. core) | Partially -- TTL/settings models shared | Bidirectional (config -> cache models, cache -> config values) | High |
| `core` | `dataframes` | **6/10** | Control | No (utility vs. domain) | Yes -- descriptor-driven schema wiring | Bidirectional (dataframes/registry -> core/entity_registry at init time) | High |
| `services` | `cache` | **6/10** | Data + Stamp | No (domain vs. infrastructure) | Yes -- FreshnessInfo, MutationEvent contracts | Unidirectional (services -> cache models) | High |
| `clients` | `cache` | **6/10** | Data | No (integration vs. infrastructure) | Partially -- EntryType leaks to clients | Unidirectional (clients -> cache models) | High |
| `lifecycle` | `persistence` | **6/10** | Data + Control | Yes (lifecycle domain) | Yes -- lifecycle commits via SaveSession | Unidirectional (lifecycle -> persistence) | High |
| `query` | `services` | **6/10** | Data + Control | Yes (query domain) | Yes -- QueryEngine composes EntityQueryService | Unidirectional (query -> services) | High |
| `services/resolver` | `services/universal_strategy` | **8/10** | Control + Data | Yes (resolution subdomain) | Yes -- designed pair, but circular | **Circular** (deferred imports at 3 sites) | High |
| `persistence/session` | `persistence/cascade` | **5/10** | Control | Yes (persistence subdomain) | Yes -- cascade is a phase of save | **Circular** (deferred import at line 191) | High |
| `models/business/__init__` | `models/business/_bootstrap` | **5/10** | Temporal | Yes (entity registration) | Yes -- intentional registration pattern | **Circular** (import-time side effect) | High |

### 2.3 Coupling Hotspot Summary

Hotspots are pairs where coupling is incidental, circular, or crosses bounded contexts:

| Rank | Pair | Score | Hotspot Reason |
|------|------|-------|----------------|
| 1 | `services/resolver` <-> `services/universal_strategy` | 8/10 | Circular dependency requiring 3 deferred import sites |
| 2 | `cache` <-> `services` | 8/10 | Cross-context coupling; cache model types (FreshnessInfo, MutationEvent, EntryType) leak into domain layer |
| 3 | `services` -> `dataframes` | 8/10 | 12 deferred import sites; services deeply coupled to DataFrame internals (SchemaRegistry, SectionPersistence, ProgressiveProjectBuilder) |
| 4 | `models` <-> `persistence` | 7/10 | Bidirectional; persistence imports model types, models.common used in session |
| 5 | `core` -> `services` / `dataframes` -> `core` | 6/10 | EntityRegistry is a control coupling hub; 4 subsystems depend on EntityDescriptor schema |

---

## 3. Shared Model Registry

Models, types, schemas, and contracts that appear across multiple package boundaries.

### 3.1 Cross-Package Pydantic Models and Data Classes

| Model / Type | Defined In | Consumer Packages | Import Count | Sharing Mechanism | Confidence |
|-------------|-----------|-------------------|-------------|-------------------|------------|
| `BusinessEntity` (base) | `models/business/base.py` | `resolution`, `persistence`, `services`, `lifecycle`, `dataframes` | 8+ | Direct import | High |
| `Business`, `Contact`, `Offer`, `Unit`, `Process` | `models/business/*.py` | `resolution`, `lifecycle`, `persistence`, `services`, `automation`, `dataframes` | 25+ | Direct import (often deferred) | High |
| `AsanaResource` | `models/base.py` | `persistence`, `client`, `models/*` (all sub-models) | 12+ | Direct import | High |
| `NameGid` | `models/common.py` | `persistence/session`, `models/project`, `models/section`, `models/task`, etc. | 10+ | Direct import | High |
| `Task` | `models/task.py` | `persistence/cascade`, `services/dataframe_service`, `models/business/detection/tier2` | 4+ | Deferred import | High |
| `Project` | `models/project.py` | `dataframes` (via build methods), `services`, `api` | 3+ | Direct + deferred import | High |
| `EntityDescriptor` | `core/entity_registry.py` | `services/entity_context`, `dataframes/models/registry`, `config`, `services/universal_strategy` | 6+ | Via `get_registry()` | High |
| `CacheEntry`, `EntryType` | `cache/models/entry.py` | `protocols/cache`, `clients/base`, `clients/*`, `_defaults/cache`, `persistence/cache_invalidator`, `models/business/detection`, `api/routes`, `dataframes/cache_integration`, `client` | 15+ | Direct + deferred import | High |
| `Freshness` | `cache/models/freshness.py` | `config`, `protocols/cache`, `_defaults/cache`, `dataframes/cache_integration`, `cache/policies` | 6+ | Direct + deferred + defensive fallback | High |
| `FreshnessInfo` | `cache/integration/dataframe_cache.py` | `services/query_service`, `services/universal_strategy` | 3 | Direct import | High |
| `MutationEvent` / `MutationCreated` | `cache/models/mutation_event.py` | `services/task_service`, `services/field_write_service`, `services/section_service` | 3 | Direct import | High |
| `CacheMetrics` | `cache/models/metrics.py` | `protocols/cache`, `client`, `_defaults/cache` | 4 | TYPE_CHECKING + deferred | High |
| `AutomationResult` | `persistence/models.py` | `automation/pipeline`, `automation/events/rule`, `automation/engine`, `automation/polling`, `lifecycle/engine`, `persistence/session` | 8+ | Direct import | High |
| `SaveResult`, `ActionResult` | `persistence/models.py` | `persistence/pipeline`, `persistence/cache_invalidator`, `automation/context`, `automation/engine`, `persistence/events` | 6+ | Direct + TYPE_CHECKING | High |
| `ActionType`, `ActionOperation` | `persistence/models.py` | `persistence/actions`, `persistence/action_ordering`, `persistence/action_executor`, `automation/events/rule`, `automation/engine` | 7+ | Direct import | High |
| `DataFrameSchema`, `ColumnDef` | `dataframes/models/schema.py` | `query/compiler`, `query/guards`, `services/dataframe_service`, `dataframes/extractors`, `dataframes/resolver` | 6+ | Direct import | High |
| `SchemaRegistry` | `dataframes/models/registry.py` | `services/resolver`, `services/universal_strategy`, `services/query_service`, `services/dataframe_service`, `query/engine` | 6+ | Singleton via `get_schema()` | High |
| `ResolutionResult` | `services/resolution_result.py` | `services/resolver`, `services/universal_strategy`, `resolution/result` | 3 | Direct import | High |
| `EntityType` (enum) | `models/business/detection/types.py` | `models/business/_bootstrap`, `models/business/detection/*`, `core/entity_registry` (reference) | 5+ | Direct import | High |
| `WarmResult` | `protocols/cache.py` | `cache/backends/base`, `cache/backends/s3`, `cache/backends/redis`, `cache/backends/memory`, `_defaults/cache`, `client` | 7 | Direct import | High |

### 3.2 Protocol Contracts (Cross-Package Boundaries)

| Protocol | Defined In | Implementors | Consumer Packages | Confidence |
|----------|-----------|-------------|-------------------|------------|
| `CacheProvider` | `protocols/cache.py` | `cache/backends/*`, `cache/providers/*`, `_defaults/cache` | `client`, `clients/base`, `dataframes/cache_integration`, `cache/integration/*`, `search/service` | High |
| `AuthProvider` | `protocols/auth.py` | `auth/bot_pat`, `auth/jwt_validator`, `_defaults/auth` | `client`, `clients/base`, `transport/asana_http`, `clients/data/client` | High |
| `LogProvider` | `protocols/log.py` | `_defaults/log` | `client`, `clients/base`, `transport/asana_http`, `clients/data/_response`, `dataframes/cache_integration` | High |
| `ItemLoader` | `protocols/item_loader.py` | (implementations in clients) | `client` | High |
| `ObservabilityHook` | `protocols/observability.py` | `observability/decorators` | `client` | High |

---

## 4. Integration Pattern Classification

### 4.1 Internal Integration Patterns

| Source | Target | Pattern | Call Style | Mediation | Timing | Coupling Level | Confidence |
|--------|--------|---------|-----------|-----------|--------|---------------|------------|
| `services/*` | `cache/integration/dataframe_cache` | **Shared state** (DataFrame cache singleton) | Direct call | Singleton accessor | Sync + Async | Medium | High |
| `services/resolver` <-> `services/universal_strategy` | Each other | **Import-time registration** | Deferred import | None | Sync | Tight | High |
| `query/engine` | `services/query_service` | **Sync API** (composition) | Direct call | Composition | Sync + Async | Tight | High |
| `persistence/session` | `clients/*` (via `AsanaClient`) | **Sync API** (client facade) | Direct call | Facade pattern | Async | Tight | High |
| `persistence/session` | `persistence/cascade` | **Import-time registration** | Deferred import | None | Async | Medium | High |
| `persistence/session` | `cache/integration/cache_invalidator` | **Event-driven** (post-commit hook) | Direct call | Fire-and-forget | Async | Medium | High |
| `automation/pipeline` | `persistence/session` | **Sync API** (UoW pattern) | Direct call | None | Async | Tight | High |
| `automation/engine` | `automation/pipeline` | **Import-time registration** (via `__getattr__`) | Lazy import | None | Async | Medium | High |
| `lifecycle/engine` | `resolution/context` | **Sync API** (composition) | Direct call | None | Async | Tight | High |
| `lifecycle/engine` | `persistence/models` | **Shared state** (AutomationResult) | Direct import | None | Sync | Medium | High |
| `dataframes/models/registry` | `core/entity_registry` | **Import-time registration** (descriptor-driven auto-wiring) | Deferred import | Singleton | Sync | Medium | High |
| `api/dependencies` | `services/*` | **Sync API** (FastAPI DI) | Deferred import | FastAPI Depends() | Async | Medium | High |
| `api/lifespan` | `cache/integration/*` | **Temporal coupling** (startup sequence) | Direct call | Sequential init | Async | Tight | High |
| `cache/providers/unified` | `protocols/cache` | **Protocol-mediated** | Protocol impl | CacheProvider contract | Async | Loose | High |
| `clients/base` | `cache/*` (via CacheProvider) | **Protocol-mediated** | Protocol call | CacheProvider contract | Async | Loose | High |
| `config` | `cache/models/*` | **Shared state** (model re-export) | Deferred import | None | Sync | Medium | High |
| `lambda_handlers/cache_warmer` | `services/discovery` | **Temporal coupling** (cold start bootstrap) | Deferred import | None | Async | Medium | High |
| `models/business/__init__` | `models/business/_bootstrap` | **Import-time registration** (model registration side effect) | Module-level call | Idempotency guard | Sync | Tight | High |
| `models/project` | `dataframes/builders` | **Shared state** (build methods on model) | Deferred import | None | Async | Tight | High |

### 4.2 External Integration Patterns

| Source | Target | Pattern | Mediation | Confidence |
|--------|--------|---------|-----------|------------|
| `clients/*` | Asana REST API | **Sync API** (HTTP) | `transport/asana_http` -> httpx | High |
| `cache/backends/redis` | AWS ElastiCache (Redis) | **Shared state** (key-value store) | redis client library | High |
| `cache/backends/s3` + `dataframes/storage` | AWS S3 | **Shared state** (object store) | boto3 | High |
| `clients/data/client` | autom8_data insights API | **Sync API** (HTTP) | autom8y-http (circuit breaker, retry) | High |
| `auth/jwt_validator` | autom8y-auth service | **Sync API** (JWT validation) | autom8y-auth SDK | High |
| `lambda_handlers/*` | AWS EventBridge | **Event-driven** (scheduled triggers) | awslambdaric | High |

### 4.3 Pattern Distribution Summary

| Pattern Category | Count | Packages Involved |
|-----------------|-------|-------------------|
| **Sync API** (direct call / composition) | 6 | query, services, persistence, lifecycle, api, clients |
| **Protocol-mediated** (loose contract) | 3 | cache providers, clients/base, transport |
| **Shared state** (singleton / cache) | 4 | services-cache, config-cache, models-dataframes, cache-S3 |
| **Import-time registration** (side effects) | 4 | models bootstrap, dataframes registry, resolver-strategy, automation engine |
| **Event-driven** (post-commit / scheduled) | 2 | persistence invalidation, Lambda handlers |
| **Temporal coupling** (ordered init) | 2 | api lifespan, Lambda cold start |

---

## 5. Coupling Hotspot Deep Dives (Top 5)

### 5.1 Hotspot 1: `services/resolver` <-> `services/universal_strategy` (Score: 8/10)

**Coupling type**: Control + Data, Circular

**Evidence of circularity (3 deferred import sites)**:

1. `src/autom8_asana/services/universal_strategy.py:23` -- top-level import of `to_pascal_case` from `resolver`
2. `src/autom8_asana/services/universal_strategy.py:156,326` -- deferred imports of `validate_criterion_for_entity` from `resolver` inside method bodies
3. `src/autom8_asana/services/resolver.py:712` -- deferred import of `get_universal_strategy` from `universal_strategy` inside function body

**Data flow trace**:

```
API Route (POST /v1/resolve/{entity_type})
  |
  v
api/dependencies.py:491 -- deferred import of EntityProjectRegistry from resolver
  |
  v
services/resolver.py:EntityProjectRegistry.get_strategy()
  |-- Calls get_universal_strategy() [line 712, deferred import]
  |     |
  |     v
  |   services/universal_strategy.py:get_universal_strategy()
  |     |-- Constructs UniversalResolutionStrategy
  |     |-- Calls to_pascal_case() [imported from resolver, line 23]
  |     |-- Calls validate_criterion_for_entity() [deferred import from resolver, line 156]
  |     |     |
  |     |     v
  |     |   services/resolver.py:validate_criterion_for_entity()
  |     |     |-- Accesses SchemaRegistry (from dataframes/models/registry)
  |     |     |-- Returns CriterionValidationResult
  |     |     |
  |     v     v
  |   UniversalResolutionStrategy._resolve_group()
  |     |-- Uses DynamicIndex for O(1) lookups
  |     |-- Returns ResolutionResult (defined in services/resolution_result.py)
  |
  v
ResolutionResult -> serialized to API response
```

**Data transforms**:
- `entity_type` (string) -> `to_pascal_case` -> schema key for SchemaRegistry lookup
- Criterion dict -> `validate_criterion_for_entity` -> `CriterionValidationResult` (valid/invalid with reason)
- DataFrame (Polars `pl.DataFrame`) -> `DynamicIndex` build -> O(1) row lookups -> `ResolutionResult` (list of `BusinessEntity` dicts)

### 5.2 Hotspot 2: `cache` <-> `services` (Score: 8/10)

**Coupling type**: Data + Control, Cross-context

**Evidence of cross-context model leakage**:

The following cache-internal models are imported by the services domain layer:
- `FreshnessInfo` (`cache/integration/dataframe_cache.py`) -> `services/query_service.py:30`, `services/universal_strategy.py:20`
- `MutationEvent`, `MutationCreated` (`cache/models/mutation_event.py`) -> `services/task_service.py:25`, `services/field_write_service.py:27`, `services/section_service.py:22`
- `EntryType` (`cache/models/entry.py`) -> `services/field_write_service.py:200` (deferred)

**Data flow trace**:

```
services/universal_strategy.py:UniversalResolutionStrategy._get_dataframe()
  |
  |-- Checks DataFrameCache singleton (cache/integration/dataframe_cache.py)
  |     |
  |     |-- Layer 1: Memory tier (cache/dataframe/tiers/memory.py)
  |     |     |-- Hit? Return pl.DataFrame + FreshnessInfo
  |     |
  |     |-- Layer 2: S3 progressive tier (cache/dataframe/tiers/progressive.py)
  |     |     |-- Via SectionPersistence -> S3 read -> Polars deserialize
  |     |     |-- Hit? Return pl.DataFrame + FreshnessInfo
  |     |
  |     |-- Layer 3: Cache miss -> Build fresh
  |     |     |-- ProgressiveProjectBuilder (dataframes/builders/progressive.py)
  |     |     |     |-- Fetches from Asana API via clients/tasks
  |     |     |     |-- Builds per-section DataFrames
  |     |     |     |-- Writes to S3 via SectionPersistence
  |     |     |-- Returns pl.DataFrame + FreshnessInfo(status=FRESH)
  |     |
  |     v
  |   FreshnessInfo { status: FreshnessStatus, age_seconds: float, ... }
  |     |-- Carried as side-channel metadata to API response layer
  |     |-- services/query_service interprets status for cache-not-warm errors
  |
  v
services/task_service.py / services/field_write_service.py
  |-- On mutation: creates MutationEvent(entity_type, gid, operation)
  |-- Publishes to MutationInvalidator (cache/integration/mutation_invalidator.py)
  |-- MutationInvalidator removes stale entries from memory tier
```

**Data transforms**:
- `str` (entity_type) -> DataFrameCache key -> `pl.DataFrame` (full entity data) + `FreshnessInfo` (metadata)
- Entity mutation -> `MutationEvent` (type + gid + operation) -> cache invalidation (key removal from memory tier)

### 5.3 Hotspot 3: `services` -> `dataframes` (Score: 8/10)

**Coupling type**: Data + Control, 12 deferred import sites

**Evidence of deep coupling**:

`services/resolver.py` imports from `dataframes` at 4 deferred sites (lines 344, 430, 569, 659), all accessing `SchemaRegistry`.
`services/universal_strategy.py` imports from `dataframes` at 4 deferred sites (lines 183, 514, 580-581, 645-664), accessing `ProgressiveProjectBuilder`, `SectionPersistence`, `SchemaRegistry`, `DefaultCustomFieldResolver`.
`services/query_service.py` imports from `dataframes` at 3 deferred sites (lines 70-71, 122, 174), accessing `SchemaNotFoundError`, `SchemaRegistry`, `SectionPersistence`.
`services/dataframe_service.py` directly imports `SchemaRegistry`, `DataFrameSchema`, and defers 3 more imports.

**Data flow trace**:

```
services/resolver.py:_validate_entity_schema()
  |
  |-- Deferred import: SchemaRegistry from dataframes/models/registry
  |-- SchemaRegistry.get_instance().get_schema(entity_type)
  |     |
  |     v
  |   dataframes/models/registry.py:SchemaRegistry._ensure_initialized()
  |     |-- Deferred import: get_registry() from core/entity_registry
  |     |-- Iterates EntityDescriptors
  |     |-- For each: _resolve_dotted_path(desc.schema_module_path)
  |     |     |-- Imports schema module (e.g., dataframes/schemas/unit.py)
  |     |     |-- Returns DataFrameSchema instance
  |     |-- Registers in _schemas dict keyed by effective_schema_key
  |     |
  |     v
  |   DataFrameSchema { name, columns: list[ColumnDef], key_columns, ... }
  |
  v
services/universal_strategy.py:_build_or_get_dataframe()
  |
  |-- Deferred import: ProgressiveProjectBuilder from dataframes/builders
  |-- Constructs builder with AsanaClient + schema + config
  |-- builder.build_async(project_gid)
  |     |
  |     v
  |   dataframes/builders/progressive.py:ProgressiveProjectBuilder
  |     |-- Fetches sections via client.sections.list_async()
  |     |-- For each section: fetches tasks, coerces to schema, writes to S3
  |     |-- Returns BuildResult { dataframe: pl.DataFrame, sections: list[SectionResult] }
  |
  v
pl.DataFrame -> returned to UniversalResolutionStrategy for DynamicIndex construction
```

**Data transforms**:
- `entity_type` (string) -> `SchemaRegistry.get_schema()` -> `DataFrameSchema` (column definitions + constraints)
- `project_gid` (string) -> `ProgressiveProjectBuilder.build_async()` -> section task pages -> `TaskRow` dicts -> `pl.DataFrame`
- `pl.DataFrame` -> `DynamicIndex` constructor -> hash-map indexes on key columns

### 5.4 Hotspot 4: `models` <-> `persistence` (Score: 7/10)

**Coupling type**: Data + Stamp, Bidirectional

**Evidence of bidirectionality**:

Forward (persistence -> models):
- `persistence/session.py:44-45` -- TYPE_CHECKING: `AsanaResource`, `User`
- `persistence/session.py:48` -- direct import: `NameGid` from `models.common`
- `persistence/cascade.py:18-20` -- TYPE_CHECKING: `BusinessEntity`, `CascadingFieldDef`, `Task`
- `persistence/executor.py:16` -- TYPE_CHECKING: `AsanaResource`
- `persistence/holder_construction.py:42-52` -- 6 deferred imports of business entity types

Reverse (models -> persistence): Indirect but real
- `models/project.py:197-199` -- deferred imports of `ProgressiveProjectBuilder`, `get_schema`, `SectionPersistence` (which pulls in persistence-adjacent concerns)
- The `SaveSession` class itself is imported by `automation/pipeline.py:39` alongside model types, creating stamp coupling where both model and session are passed together.

**Data flow trace**:

```
User code: async with SaveSession(client) as session:
  |
  |-- session.update(entity)  [entity: AsanaResource / BusinessEntity]
  |     |
  |     v
  |   persistence/session.py:SaveSession.update()
  |     |-- ChangeTracker.track(entity) -> computes EntityState (dirty fields)
  |     |     |-- Accesses entity.__dict__ and original snapshot
  |     |     |-- Returns EntityState { gid, entity_type, dirty_fields, operation }
  |     |
  |     v
  |   session.commit_async()
  |     |
  |     v
  |   persistence/pipeline.py:SavePipeline.execute()
  |     |-- Phase 1 VALIDATE: DependencyGraph.detect_cycles()
  |     |-- Phase 2 PREPARE: BatchExecutor.build_operations(states)
  |     |     |-- For each EntityState -> PlannedOperation { gid, data, op_type }
  |     |-- Phase 3 EXECUTE: BatchExecutor.execute(operations)
  |     |     |-- Calls client.tasks.update_async() / create_async()
  |     |     |-- Returns list[SaveResult]
  |     |-- Phase 4 ACTIONS: ActionExecutor.execute(actions)
  |     |-- Phase 5 CONFIRM: Resolve temp GIDs, update entity instances
  |
  |-- Post-commit:
  |     |-- CacheInvalidator.invalidate(results)
  |     |     |-- For each SaveResult -> cache.delete_async(key)
  |     |-- AutomationEngine.fire_async(results) [if automation rules registered]
```

**Data transforms**:
- `AsanaResource` (Pydantic model) -> `ChangeTracker` -> `EntityState` (dirty field diffs)
- `EntityState` -> `BatchExecutor` -> `PlannedOperation` (API-ready payload)
- API response -> `SaveResult` (gid, success/failure, errors)
- `SaveResult` -> `CacheInvalidator` -> cache key deletion

### 5.5 Hotspot 5: `core/entity_registry` as Control Coupling Hub (Score: 6-7/10)

**Coupling type**: Control coupling, 4 subsystems depend on `EntityDescriptor`

**Evidence of hub pattern**:

`EntityDescriptor` (frozen dataclass in `core/entity_registry.py`) drives behavior in 4 subsystems:
1. `dataframes/models/registry.py:123-132` -- `SchemaRegistry._ensure_initialized()` iterates descriptors, resolves `schema_module_path`
2. `dataframes` extractor creation -- `extractor_class_path` on descriptors resolves extractor classes
3. `query/hierarchy.py:49` -- `get_registry()` used for join key discovery via `join_keys` field
4. `config.py:107` -- `get_registry()` used for `DEFAULT_ENTITY_TTLS` facade

Plus `services/universal_strategy.py:72-75` uses `get_registry().all_descriptors()` at module scope to build `DEFAULT_KEY_COLUMNS`.

**Data flow trace**:

```
Import time (cold start):
  |
  |-- models/business/_bootstrap.py:register_all_models()
  |     |-- Populates ProjectTypeRegistry (Tier 1 detection)
  |     |-- EntityType enum values associated with entity classes
  |
  |-- core/entity_registry.py: ENTITY_DESCRIPTORS tuple (static declaration)
  |     |-- Each EntityDescriptor { name, project_gid, key_columns,
  |     |     schema_module_path, extractor_class_path, ... }
  |     |
  |     v
  |   get_registry() -> EntityRegistry singleton
  |     |-- O(1) lookup by name, project GID, EntityType
  |
  v
Runtime consumers:
  |
  |-- [1] dataframes/models/registry.py: SchemaRegistry._ensure_initialized()
  |     for desc in get_registry().all_descriptors():
  |       schema = _resolve_dotted_path(desc.schema_module_path)
  |       -> DataFrameSchema instance registered
  |
  |-- [2] dataframes extractors: _create_extractor()
  |     _resolve_dotted_path(desc.extractor_class_path)
  |       -> BaseExtractor subclass instantiated
  |
  |-- [3] query/hierarchy.py: find_relationship()
  |     get_registry() -> descriptors -> join_keys
  |       -> relationship paths for cross-entity joins
  |
  |-- [4] services/universal_strategy.py (module scope):
  |     DEFAULT_KEY_COLUMNS = {d.name: list(d.key_columns) for d in registry}
  |       -> dict consumed during resolution index construction
```

**Data transforms**:
- `EntityDescriptor.schema_module_path` (string) -> `_resolve_dotted_path` -> `DataFrameSchema` class
- `EntityDescriptor.extractor_class_path` (string) -> `_resolve_dotted_path` -> `BaseExtractor` subclass
- `EntityDescriptor.key_columns` (tuple) -> `DEFAULT_KEY_COLUMNS` dict -> `DynamicIndex` column selection
- `EntityDescriptor.join_keys` (dict) -> `ENTITY_RELATIONSHIPS` dict -> query join path resolution

---

## 6. Critical Path Analysis (Top 3)

### 6.1 Critical Path 1: Entity Query (API -> QueryEngine -> DataFrame -> Cache -> API Response)

**Significance**: This is the primary read path for all S2S query and resolve endpoints. Touches 7 packages.

```
[1] api/routes/query.py: POST /v1/query/{entity_type}/rows
    |-- Receives RowsRequest (Pydantic model from query/models.py)
    |-- FastAPI Depends() injects QueryEngine from api/dependencies.py
    |
    v
[2] api/dependencies.py:get_query_engine()  [deferred import]
    |-- Creates QueryEngine(query_service=EntityQueryService())
    |
    v
[3] query/engine.py:QueryEngine.query_rows()
    |-- Validates entity_type via SchemaRegistry (dataframes/models/registry)
    |-- Compiles predicates: PredicateCompiler.compile(where, schema)
    |     |-- query/compiler.py: AST nodes -> pl.Expr via operator matrix
    |-- Calls self.query_service.get_dataframe()
    |
    v
[4] services/query_service.py:EntityQueryService.get_dataframe()
    |-- Deferred import: get_universal_strategy() from services/universal_strategy
    |-- strategy._get_dataframe(entity_type, client, project_registry)
    |
    v
[5] services/universal_strategy.py:UniversalResolutionStrategy._get_dataframe()
    |-- Checks DataFrameCacheCoalescer (prevents duplicate builds)
    |
    v
[6] cache/integration/dataframe_cache.py:DataFrameCache.get_or_build()
    |-- Memory tier check -> S3 tier check -> build on miss
    |-- On miss: ProgressiveProjectBuilder.build_async() [dataframes/builders]
    |     |-- Fetches from Asana API via clients/tasks.list_async()
    |     |-- Builds pl.DataFrame per section, writes to S3
    |-- Returns (pl.DataFrame, FreshnessInfo)
    |
    v
[7] Back in query/engine.py:
    |-- Applies compiled pl.Expr predicates to DataFrame
    |-- Applies section scoping (if section predicates present)
    |-- Applies pagination (offset, limit)
    |-- Returns RowsResponse { rows: list[dict], meta: RowsMeta }
    |
    v
[8] api/routes/query.py: Serializes RowsResponse -> HTTP 200 JSON
```

**Packages traversed**: `api` -> `query` -> `services` -> `cache` -> `dataframes` -> `clients` -> `transport`

**Key files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/engine.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/query_service.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/universal_strategy.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/dataframe_cache.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/dataframes/builders/progressive.py`

### 6.2 Critical Path 2: Entity Mutation (SaveSession -> Pipeline -> Asana API -> Cache Invalidation)

**Significance**: This is the primary write path for all entity mutations. Touches 6 packages.

```
[1] User code / automation/pipeline.py:
    |-- async with SaveSession(client) as session:
    |       session.update(entity)  # entity: BusinessEntity / AsanaResource
    |       await session.commit_async()
    |
    v
[2] persistence/session.py:SaveSession.commit_async()
    |-- ChangeTracker.compute_dirty_states() -> list[EntityState]
    |     |-- Compares current entity fields vs. tracked originals
    |     |-- persistence/tracker.py: EntityState { gid, dirty_fields, op_type }
    |-- Constructs SavePipeline
    |
    v
[3] persistence/pipeline.py:SavePipeline.execute()
    |-- Phase 1: DependencyGraph.detect_cycles() [persistence/graph.py]
    |-- Phase 2: BatchExecutor.build_operations() [persistence/executor.py]
    |     |-- EntityState -> PlannedOperation { gid, data_payload, operation_type }
    |-- Phase 3: BatchExecutor.execute() -> calls Asana API
    |     |
    |     v
[4] clients/tasks.py:TasksClient.update_async() (or create_async)
    |-- transport/asana_http.py: InstrumentedAsanaClient
    |     |-- httpx POST/PUT to Asana REST API
    |     |-- Rate limiting, retry, circuit breaker (autom8y-http)
    |-- Returns API response -> parsed into SaveResult
    |
    v
[5] Back in pipeline.py:
    |-- Phase 4: ActionExecutor.execute() [persistence/action_executor.py]
    |     |-- Tag operations, project memberships, section moves
    |     |-- Each action -> separate Asana API call
    |-- Phase 5: GID resolution, entity instance updates
    |-- Returns SaveResult { operations: list[OperationResult], errors: list[SaveError] }
    |
    v
[6] persistence/session.py (post-commit):
    |-- CacheInvalidator.invalidate(save_result) [persistence/cache_invalidator.py]
    |     |-- For each mutated entity: cache.delete_async(EntryType, gid)
    |     |-- Catches CACHE_TRANSIENT_ERRORS (fire-and-forget)
    |-- AutomationEngine.fire_async(save_result) [if registered]
    |     |-- Evaluates rule conditions against SaveResult
    |     |-- May create new SaveSession (recursive commit)
```

**Packages traversed**: `persistence` -> `clients` -> `transport` -> `cache` -> `automation` (optional)

**Key files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/session.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/pipeline.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/executor.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/persistence/cache_invalidator.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/tasks.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py`

### 6.3 Critical Path 3: Lifecycle Transition (Webhook -> Detection -> Resolution -> Creation -> Persistence)

**Significance**: This is the most complex end-to-end path, spanning 8 packages. Triggered by Asana webhook events for lifecycle transitions (e.g., Sales -> Onboarding conversion).

```
[1] api/routes/webhooks.py: POST /api/v1/webhooks/inbound
    |-- Validates Asana HMAC signature
    |-- Extracts event payload (task GID, section change)
    |
    v
[2] models/business/detection/facade.py: identify_entity_type(task)
    |-- Tier 1: ProjectTypeRegistry lookup (project GID -> EntityType)
    |-- Tier 2: Task name pattern matching (regex-based)
    |-- Tier 3: Parent-child relationship resolution
    |-- Returns EntityType enum value
    |
    v
[3] automation/engine.py: AutomationEngine.evaluate(event)
    |-- Matches event against registered rules
    |-- Finds PipelineConversionRule (automation/pipeline.py)
    |
    v
[4] automation/pipeline.py:PipelineConversionRule.execute()
    |-- Validates trigger conditions (section = CONVERTED, type = SALES)
    |-- resolution/context.py: ResolutionContext.resolve_hierarchy()
    |     |-- Resolves Unit -> Business -> Contact chain
    |     |-- Uses resolution/strategies.py: HierarchyResolutionStrategy
    |
    v
[5] core/creation.py: discover_template_async()
    |-- Finds onboarding template task in target project
    |-- duplicate_from_template_async() -> Asana API (tasks.duplicate_async)
    |-- wait_for_subtasks_async() -> polls until subtasks materialize
    |-- place_in_section_async() -> moves to target section
    |
    v
[6] automation/seeding.py:FieldSeeder.seed_fields()
    |-- Copies field values from source process to new entity
    |-- Computes due dates, assignees from hierarchy
    |
    v
[7] persistence/session.py: SaveSession
    |-- Tracks new entity + field updates
    |-- commit_async() -> SavePipeline (see Critical Path 2)
    |
    v
[8] persistence/cache_invalidator.py: post-commit
    |-- Invalidates cache for new entity + parent entities
    |-- Returns AutomationResult { success, entity_gid, warnings }
```

**Packages traversed**: `api` -> `models` (detection) -> `automation` -> `resolution` -> `core` -> `persistence` -> `clients` -> `cache`

**Key files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/webhooks.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/detection/facade.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/engine.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/automation/pipeline.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/resolution/context.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/lifecycle/engine.py`

---

## 7. Circular Dependency Map

| Cycle | Packages | Deferred Import Sites | Mechanism | Confidence |
|-------|----------|----------------------|-----------|------------|
| 1 | `services/resolver` <-> `services/universal_strategy` | 3 sites (strategy:156,326; resolver:712) | Function-body deferred imports | High |
| 2 | `models/business/__init__` <-> `models/business/_bootstrap` | 1 site (init triggers bootstrap) | Import-time registration with idempotency guard | High |
| 3 | `persistence/session` -> `persistence/cascade` | 1 site (session:191) | Deferred import within package | High |
| 4 | `automation/__init__` -> `automation/pipeline` | 1 site (`__getattr__` lazy import) | Module-level `__getattr__` | High |
| 5 | `config` <-> `cache/models` | 5 sites (config:39,40,490,504,518) | All deferred via TYPE_CHECKING or function body | High |
| 6 | `dataframes/models/registry` -> `core/entity_registry` | 1 site (registry:123) | Deferred import to avoid circular | High |

---

## 8. Unknowns

### Unknown: Lifecycle webhook router active or dead code

- **Question**: Is `src/autom8_asana/lifecycle/webhook.py` with its `APIRouter(prefix="/api/v1/webhooks")` registered with the FastAPI app, or is it dead code?
- **Why it matters**: If active, there is an additional cross-package dependency from `lifecycle` to the API layer, and a route prefix collision with `api/routes/webhooks.py`. This would add `lifecycle` -> `api` to the dependency graph (currently not present).
- **Evidence**: The router is defined in `lifecycle/webhook.py` but is not imported in `api/routes/__init__.py` or `api/main.py`. The existing `webhooks_router` from `api/routes/webhooks.py` is the only one registered.
- **Suggested source**: Code author or deployment configuration

### Unknown: Intentionality of cache model leakage into services

- **Question**: Is the coupling between `services/*` and `cache/models/*` (FreshnessInfo, MutationEvent, EntryType) an intentional API design or an incidental leakage of implementation details?
- **Why it matters**: If intentional, the coupling score context is "designed contract" and acceptable. If incidental, this represents a bounded-context violation where infrastructure types leak into the domain layer.
- **Evidence**: `FreshnessInfo` is a dataclass from `cache/integration/dataframe_cache.py` (an integration module, not a models module), imported directly by `services/query_service.py` and `services/universal_strategy.py`. `MutationEvent` is from `cache/models/mutation_event.py`, imported by 3 service modules. The fact that these live in `cache/` (infrastructure) but are consumed by `services/` (domain) suggests the boundary may not have been explicitly designed.
- **Suggested source**: Original designer of the cache integration layer

### Unknown: `autom8y-core` usage path

- **Question**: Does `autom8y-asana` use `autom8y-core` directly, or is it only a transitive dependency via other `autom8y-*` packages?
- **Why it matters**: If direct, there are import paths not captured by Grep. If transitive only, the dependency could potentially be removed from `pyproject.toml` direct dependencies.
- **Evidence**: No `from autom8y_core` import was found in the source tree. `autom8y-core>=1.1.0` is listed in `pyproject.toml`. Likely consumed transitively by `autom8y-log`, `autom8y-http`, etc.
- **Suggested source**: `pyproject.toml` dependency tree analysis via `uv pip tree`

---

## 9. Provenance

### Source Artifacts

| Source | Contribution to This Artifact |
|--------|-------------------------------|
| `ARCH-REVIEW-1-DEPENDENCIES.md` | Baseline coupling scores (Section 2), fan-in gravity wells (Section 1), integration patterns (Section 3), circular dependency chains (Section 5), abstraction leaks (Section 6) |
| `TOPOLOGY-AUTOM8Y-ASANA.md` | Package catalog (27 packages), tech stack, API surface, classification labels, deployment boundaries |

### Targeted Codebase Scans Performed

| Scan | Method | Pattern | Files Matched | Output Section |
|------|--------|---------|---------------|----------------|
| Cross-package model imports | Grep `from autom8_asana\.models` | `*.py` in `src/` | 80+ matches | Section 1.1 adjacency, Section 3 shared models |
| Cross-package core imports | Grep `from autom8_asana\.core` | `*.py` in `src/` | 60+ matches | Section 1.1 adjacency, Section 5.5 hub analysis |
| Cross-package cache imports | Grep `from autom8_asana\.cache` | `*.py` in `src/` | 60+ matches | Section 1.1, Section 3.1, Section 5.2 |
| Cross-package protocol imports | Grep `from autom8_asana\.protocols` | `*.py` in `src/` | 40+ matches | Section 3.2 protocol contracts |
| Cross-package persistence imports | Grep `from autom8_asana\.persistence` | `*.py` in `src/` | 40+ matches | Section 3.1, Section 5.4 |
| Cross-package services imports | Grep `from autom8_asana\.services` | `*.py` in `src/` | 40+ matches | Section 1.1, Section 5.1, Section 5.3 |
| Cross-package clients imports | Grep `from autom8_asana\.clients` | `*.py` in `src/` | 50+ matches | Section 1.1 adjacency |
| Cross-package config/settings imports | Grep `from autom8_asana\.config\|settings` | `*.py` in `src/` | 50+ matches | Section 1.1, Section 1.4 |
| Business model imports | Grep `from autom8_asana\.models\.business` | `*.py` in `src/` | 60+ matches | Section 3.1 shared models |
| Cache model imports | Grep `from autom8_asana\.cache\.models` | `*.py` in `src/` | 40+ matches | Section 3.1 shared models, Section 5.2 |
| Persistence model imports | Grep `from autom8_asana\.persistence\.models` | `*.py` in `src/` | 30+ matches | Section 3.1 shared models |
| Remaining cross-package imports | Grep `from autom8_asana\.(automation\|dataframes\|query\|...)` | `*.py` in `src/` | 100+ matches | Section 1.1 adjacency |
| Platform package imports | Grep `from autom8y_` | `*.py` in `src/` | 50+ matches | Section 1.4 external dependencies |
| Model class definitions | Grep `class (Business\|Contact\|...)` | `*.py` in `src/` | 40+ matches | Section 3.1 validation |
| Critical path file reads | Read of 12 key files | session.py, pipeline.py, engine.py, etc. | 12 files | Sections 5-6 |

### Handoff Readiness

- [x] Package-to-package dependency adjacency table (Section 1.1, 73 directed edges)
- [x] Fan-in and fan-out summaries (Sections 1.2, 1.3)
- [x] External platform package dependency table (Section 1.4, 7 packages)
- [x] Coupling scores with context annotations for all significant pairs (Section 2.2, 15 scored pairs)
- [x] Coupling context checks (bounded context, intentionality, directionality) performed for all pairs (Section 2.2)
- [x] Coupling hotspot summary with rankings (Section 2.3)
- [x] Shared model registry with cross-package usage counts (Section 3.1, 19 shared types)
- [x] Protocol contracts registry (Section 3.2, 5 protocols)
- [x] Integration pattern classification table (Section 4.1, 19 internal patterns)
- [x] External integration patterns (Section 4.2, 6 external patterns)
- [x] Pattern distribution summary (Section 4.3)
- [x] Top 5 coupling hotspot deep dives with data flow traces (Section 5)
- [x] 3 critical path end-to-end traces with file paths and function signatures (Section 6)
- [x] Circular dependency map (Section 7, 6 cycles)
- [x] Unknowns section (Section 8, 3 unknowns)
- [x] Confidence ratings assigned to all findings (High for all manifest/import-based evidence)
- [x] Provenance section with targeted scan inventory (Section 9)
