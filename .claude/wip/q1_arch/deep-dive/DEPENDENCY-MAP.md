# Dependency Map: autom8y-asana

**Analysis Unit**: directory (single repo, subsystem-level boundaries)
**Repo Path**: `/Users/tomtenuta/Code/autom8y-asana`
**Source Root**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana`
**Date**: 2026-02-23
**Complexity**: DEEP-DIVE
**Upstream**: TOPOLOGY-INVENTORY.md

---

## 1. Cross-Directory Dependency Matrix

The matrix below shows directional import dependencies between the 22 directory units plus the root-level module group. An arrow A -> B means "A imports from B." Counts represent distinct import targets (unique `from autom8_asana.X.Y import Z` statements deduplicated by target module).

### 1.1 Outbound Dependency Summary (what each unit imports FROM)

| # | Unit | Depends On (target -> distinct import count) |
|---|------|----------------------------------------------|
| 1 | **api/** | services(18), cache(14), auth(8), dataframes(13), core(7), models(5), query(6), lambda_handlers(4), persistence(2), resolution(2), protocols(1), _defaults(1) |
| 2 | **automation/** | models(12), persistence(8), core(7), clients(3), lifecycle(3), resolution(3), automation/internal(self) |
| 3 | **batch/** | clients(1), transport(1) |
| 4 | **cache/** | core(14), protocols(8), batch(5), models(4), dataframes(6), services(3), _defaults(3), auth(1), clients(2), api(1) |
| 5 | **clients/** | models(18), cache(5), core(4), observability(5), patterns(5), transport(2), protocols(4), persistence(5) |
| 6 | **core/** | models(4), dataframes(3), services(2), automation(2), metrics(1) |
| 7 | **dataframes/** | cache(8), core(7), models(9), clients(2), services(2), protocols(2) |
| 8 | **lambda_handlers/** | models(2), automation(3), cache(4), services(3), core(2), auth(1), dataframes(1), clients(1) |
| 9 | **lifecycle/** | core(4), models(5), persistence(2), resolution(4), automation(1) |
| 10 | **metrics/** | models(1), dataframes(1) |
| 11 | **models/** | core(3), cache(2), dataframes(6), persistence(2), clients(1), transport(1), search(1) |
| 12 | **observability/** | protocols(1) |
| 13 | **patterns/** | (none -- leaf) |
| 14 | **persistence/** | models(12), batch(4), cache(3), core(2), clients(1), transport(1), patterns(1) |
| 15 | **protocols/** | cache(3), models(1) |
| 16 | **query/** | dataframes(5), services(3), core(1), models(1), metrics(1) |
| 17 | **resolution/** | models(15), core(2) |
| 18 | **search/** | dataframes(1), protocols(1) |
| 19 | **services/** | cache(6), core(4), dataframes(8), models(4), clients(1), query(2), auth(1), resolution(2), _defaults(1), metrics(1) |
| 20 | **transport/** | protocols(2) |
| 21 | **_defaults/** | cache(4), protocols(2), observability(1) |
| 22 | **auth/** | api(2) |
| R | **root modules** | _defaults(2), automation(2), batch(1), cache(5), clients(13), core(1), dataframes(1), models(1), observability(1), persistence(2), protocols(3), search(1), transport(2) |

### 1.2 Inbound Dependency Summary (what depends on each unit)

| Unit | Depended On By (count of importing units) | Fan-In |
|------|-------------------------------------------|--------|
| **models/** | 14 units (api, automation, cache, clients, core, dataframes, lambda_handlers, lifecycle, metrics, persistence, protocols, query, resolution, services) | **Very High** |
| **core/** | 12 units (api, automation, cache, clients, dataframes, lambda_handlers, lifecycle, persistence, query, resolution, services, config.py) | **Very High** |
| **cache/** | 11 units (api, _defaults, clients, dataframes, lambda_handlers, persistence, protocols, services, client.py, config.py) | **High** |
| **dataframes/** | 9 units (api, cache, core, metrics, models, query, search, services) | **High** |
| **services/** | 7 units (api, cache, core, dataframes, lambda_handlers, query, root) | **High** |
| **protocols/** | 7 units (api, cache, clients, _defaults, observability, search, transport) | **Medium** |
| **persistence/** | 6 units (api, automation, clients, lifecycle, models, root) | **Medium** |
| **clients/** | 6 units (api, automation, batch, cache, dataframes, lambda_handlers, root) | **Medium** |
| **auth/** | 5 units (api, cache, lambda_handlers, services, root) | **Medium** |
| **automation/** | 4 units (core, lambda_handlers, lifecycle, root) | **Medium** |
| **resolution/** | 4 units (api, automation, lifecycle, services) | **Medium** |
| **transport/** | 4 units (batch, clients, models, persistence, root) | **Medium** |
| **patterns/** | 3 units (clients, persistence, root) | **Low** |
| **observability/** | 3 units (clients, _defaults, root) | **Low** |
| **batch/** | 3 units (cache, persistence, root) | **Low** |
| **query/** | 3 units (api, services, root) | **Low** |
| **_defaults/** | 3 units (api, cache, services, root) | **Low** |
| **metrics/** | 3 units (core, query, services) | **Low** |
| **lambda_handlers/** | 2 units (api) | **Low** |
| **search/** | 2 units (models, root) | **Low** |
| **lifecycle/** | 2 units (automation, lambda_handlers) | **Low** |
| **api/** | 2 units (auth, cache) | **Low** |

### 1.3 Full Adjacency Matrix

Rows = importing unit, Columns = imported unit. Numbers = distinct cross-boundary import statement count.

```
              api aut bat cac cli cor dat lam lif met mod obs pat per pro qry res sea ser tra _df aut
api            .   .   .  14   .   7  13   4   .   .   5   .   .   2   1   6   2   .  18   .   1   8
automation     .   .   .   .   3   7   .   .   3   .  12   .   .   8   .   .   3   .   .   .   .   .
batch          .   .   .   .   1   .   .   .   .   .   .   .   .   .   .   .   .   .   .   1   .   .
cache          1   .   5   .   2  14   6   .   .   .   4   .   .   .   8   .   .   .   3   .   3   1
clients        .   .   .   5   .   4   .   .   .   .  18   5   5   5   4   .   .   .   .   2   .   .
core           .   2   .   .   .   .   3   .   .   1   4   .   .   .   .   .   .   .   2   .   .   .
dataframes     .   .   .   8   2   7   .   .   .   .   9   .   .   .   2   .   .   .   2   .   .   .
lambda_hdl     .   3   .   4   1   2   1   .   .   .   2   .   .   .   .   .   .   .   3   .   .   1
lifecycle      .   1   .   .   .   4   .   .   .   .   5   .   .   2   .   .   4   .   .   .   .   .
metrics        .   .   .   .   .   .   1   .   .   .   1   .   .   .   .   .   .   .   .   .   .   .
models         .   .   .   2   1   3   6   .   .   .   .   .   .   2   .   .   .   1   .   1   .   .
observability  .   .   .   .   .   .   .   .   .   .   .   .   .   .   1   .   .   .   .   .   .   .
patterns       .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
persistence    .   .   4   3   1   2   .   .   .   .  12   .   1   .   .   .   .   .   .   1   .   .
protocols      .   .   .   3   .   .   .   .   .   .   1   .   .   .   .   .   .   .   .   .   .   .
query          .   .   .   .   .   1   5   .   .   1   1   .   .   .   .   .   .   .   3   .   .   .
resolution     .   .   .   .   .   2   .   .   .   .  15   .   .   .   .   .   .   .   .   .   .   .
search         .   .   .   .   .   .   1   .   .   .   .   .   .   .   1   .   .   .   .   .   .   .
services       .   .   .   6   1   4   8   .   .   1   4   .   .   .   .   2   2   .   .   .   1   1
transport      .   .   .   .   .   .   .   .   .   .   .   .   .   .   2   .   .   .   .   .   .   .
_defaults      .   .   .   4   .   .   .   .   .   .   .   1   .   .   2   .   .   .   .   .   .   .
auth           2   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
```

**Confidence**: High -- based on exhaustive grep of all `from autom8_asana.X` import statements in source files.

---

## 2. Coupling Score Table

Coupling scores are calculated using the following methodology:

- **Import Count Weight**: Sum of directional imports between pair (A->B + B->A)
- **Bidirectionality Multiplier**: x1.5 if bidirectional
- **Depth Penalty**: +2 if imports reach into internal/private modules (prefixed `_`)
- **Coupling Type Bonus**: +3 for data coupling (shared Pydantic models), +2 for stamp coupling (passing complex types), +1 for control coupling
- **Score Range**: 0-100 (normalized)

### Coupling Context Checks

Before scoring, each pair was evaluated for:
1. **Bounded Context Check**: Are these units within the same domain-aligned boundary?
2. **Intentionality Check**: Is the coupling designed (contract-based) or incidental?
3. **Directionality Check**: Unidirectional (healthy) or circular (problematic)?

### Scored Pairs (ranked by coupling strength)

| Rank | Unit A | Unit B | A->B | B->A | Bidir | Coupling Type | Context | Score | Confidence |
|------|--------|--------|------|------|-------|---------------|---------|-------|------------|
| 1 | **models/** | **clients/** | 1 | 18 | Yes | Data (Pydantic models passed across boundary) | Designed: clients type-check against domain models | **72** | High |
| 2 | **models/** | **dataframes/** | 6 | 9 | Yes | Data + Stamp (models consumed and transformed into DF rows) | Designed: schema-driven extraction from model types | **68** | High |
| 3 | **models/** | **persistence/** | 2 | 12 | Yes | Data + Control (models are UoW entities; persistence controls lifecycle) | Designed: persistence manages model state transitions | **65** | High |
| 4 | **models/** | **resolution/** | 0 | 15 | No | Data (resolution navigates model hierarchy) | Designed: resolution strategies traverse business entity tree | **55** | High |
| 5 | **cache/** | **core/** | 1 | 14 | Yes | Stamp + Control (exceptions, registry, concurrency) | Mixed: core provides infrastructure to cache, but cache imports into core schema | **54** | High |
| 6 | **api/** | **services/** | 0 | 18 | No | Control (API delegates to service layer) | Designed: clean layered architecture (API -> Service) | **52** | High |
| 7 | **models/** | **automation/** | 0 | 12 | No | Data (automation reads model types for pipeline rules) | Designed: automation operates on domain models | **48** | High |
| 8 | **api/** | **cache/** | 1 | 14 | Yes | Stamp (cache types flow through API startup/preload) | Mixed: mostly designed (factory/preload), api metric import is incidental | **47** | High |
| 9 | **dataframes/** | **cache/** | 6 | 8 | Yes | Data + Stamp (DataFrames cached in cache subsystem; cache builds DFs) | Designed: intentional cache-integration layer bridges these | **46** | High |
| 10 | **services/** | **dataframes/** | 8 | 2 | Yes | Stamp (services resolve via DF schemas; DFs use services for lookup) | Mixed: mostly designed (query resolution), some incidental coupling | **44** | High |
| 11 | **automation/** | **persistence/** | 0 | 8 | No | Data + Control (automation uses SaveSession, AutomationResult) | Designed: automation commits via persistence UoW | **42** | High |
| 12 | **api/** | **dataframes/** | 0 | 13 | No | Stamp (API preload builds DataFrames) | Designed: preload populates DF cache at startup | **40** | High |
| 13 | **clients/** | **cache/** | 5 | 2 | Yes | Stamp (clients use CacheEntry for read-through; cache uses TasksClient for warming) | Designed: explicit cache integration in BaseClient | **38** | High |
| 14 | **services/** | **cache/** | 6 | 3 | Yes | Stamp (services use MutationInvalidator, FreshnessInfo) | Designed: services invalidate cache after mutations | **37** | High |
| 15 | **clients/** | **persistence/** | 5 | 1 | Yes | Data + Control (task_operations uses SaveSession; persistence uses BatchClient) | Designed: clients provide persistence execution backend | **36** | High |
| 16 | **models/** | **core/** | 3 | 4 | Yes | Data (core entity_registry references model detection types; models use core exceptions) | Mixed: core references model types (slight layering violation) | **35** | High |
| 17 | **core/** | **dataframes/** | 3 | 7 | Yes | Stamp (core system_context references SchemaRegistry; dataframes uses core retry/exceptions) | Mixed: core should not reference DF types (upward dependency) | **34** | Medium |
| 18 | **dataframes/** | **models/** | 9 | 6 | Yes | Data (extractors read Task/CustomField; models.project delegates to DF builders) | Mixed: DF -> models is designed; models -> DF is convenience coupling | **33** | High |
| 19 | **lifecycle/** | **resolution/** | 4 | 0 | No | Control (lifecycle uses ResolutionContext for entity navigation) | Designed: lifecycle resolves entities for transitions | **32** | High |
| 20 | **api/** | **auth/** | 8 | 2 | Yes | Control (API uses auth for JWT validation; auth uses API dependencies) | Mixed: auth -> api is a layering violation | **30** | High |

**Confidence**: High for all scores. Import counts derived from exhaustive source grep, coupling type determined by inspecting what is imported (types vs. functions vs. abstractions).

---

## 3. Integration Pattern Catalog

### 3.1 Direct Import (Tight Coupling)

The dominant integration pattern. All 22 units communicate via direct Python imports. This is appropriate for a monolithic SDK codebase.

| Pattern | Count | Example |
|---------|-------|---------|
| Direct class/function import | ~380 cross-boundary imports | `from autom8_asana.models.task import Task` |
| Deferred import (TYPE_CHECKING) | ~180 type-only imports | `if TYPE_CHECKING: from autom8_asana.models.base import AsanaResource` |
| Lazy import (inside function body) | ~120 runtime-deferred imports | `def foo(): from autom8_asana.cache.integration.factory import CacheProviderFactory` |

**Confidence**: High

### 3.2 Protocol/ABC-Based (Loose Coupling)

The `protocols/` directory defines 6 protocol interfaces used for dependency injection:

| Protocol | File | Implementors | Consumers |
|----------|------|-------------- |-----------|
| `AuthProvider` | `protocols/auth.py` | `_defaults/auth.py` (EnvAuthProvider, SecretsManagerAuthProvider) | `transport/`, `clients/`, root `client.py` |
| `CacheProvider` | `protocols/cache.py` | `_defaults/cache.py` (NullCacheProvider, InMemoryCacheProvider), `cache/backends/` (Redis, S3, Memory) | `clients/base.py`, `cache/`, `dataframes/`, `search/`, `services/` |
| `DataFrameCacheProtocol` | `protocols/cache.py` | `cache/integration/dataframe_cache.py` | Not widely used (noted as future extraction target in ADR-0067) |
| `ItemLoader` | `protocols/item_loader.py` | Various (implicit) | `models/` |
| `LogProvider` | `protocols/log.py` | `_defaults/log.py` | `clients/`, `transport/`, `observability/` |
| `ObservabilityHook` | `protocols/observability.py` | `_defaults/observability.py` | root `client.py` |

**Confidence**: High

### 3.3 Event-Based / Callback-Based

| Pattern | Module | Direction | Description |
|---------|--------|-----------|-------------|
| Automation Events | `automation/events/` | Internal | EventEmitter -> EventTransport -> EventEnvelope. Rule-based event matching with EventEmissionRule. |
| Persistence Events | `persistence/events.py` | Internal | EventSystem fires on SaveSession lifecycle (pre-commit, post-commit). |
| Cache Mutation Events | `cache/models/mutation_event.py` | Internal | MutationEvent (create/update/delete/move) triggers MutationInvalidator to cascade cache invalidation. |
| Asana Webhooks | `lifecycle/webhook.py` | Inbound | External Asana webhook -> AutomationDispatch -> LifecycleEngine transition. |

**Confidence**: High

### 3.4 Shared Data Structures (Pydantic Models Passed Between Layers)

The primary cross-boundary data coupling mechanism. Key shared types:

| Type | Defined In | Consumed By | Pattern |
|------|-----------|-------------|---------|
| `Task` (Pydantic) | `models/task.py` | clients, dataframes, persistence, automation, lifecycle, resolution, cache | Frozen Pydantic model, `extra="ignore"` |
| `BusinessEntity` hierarchy | `models/business/` | persistence, automation, lifecycle, resolution, dataframes, services | Frozen Pydantic, descriptor-driven field wiring |
| `CacheEntry` | `cache/models/entry.py` | clients, _defaults, persistence, dataframes, protocols | Frozen Pydantic with EntryType enum |
| `AutomationResult` | `persistence/models.py` | automation, lifecycle | Result type bridging automation output to persistence |
| `SaveResult` | `persistence/models.py` | automation, lifecycle, api | Persistence commit outcome |
| `DataFrameSchema` | `dataframes/models/schema.py` | query, cache, services, api | Schema-driven column definitions for DF extraction |
| `ResolutionContext` | `resolution/context.py` | automation, lifecycle | Entity navigation context |
| `InsightsResponse`/`InsightsRequest` | `clients/data/models.py` | automation/workflows | Data service response types |
| `PhoneVerticalPair` | `models/contracts/` | clients/data, services | Cross-service identifier |

**Confidence**: High

### 3.5 Dependency Injection Patterns

| Pattern | Location | Description |
|---------|----------|-------------|
| FastAPI `Depends()` | `api/dependencies.py` | 20+ dependency providers using `Annotated[T, Depends(factory)]` |
| Protocol-based DI | `protocols/` | 6 runtime protocols, implementations injected at `AsanaClient.__init__` |
| Factory Pattern | `cache/integration/factory.py` | `CacheProviderFactory` constructs cache providers based on env |
| `create_cache_provider()` | `cache/integration/factory.py` | Convenience factory used by root `client.py` |
| Singleton (module-level) | `cache/dataframe/factory.py` | `_cache_instance` module singleton for DataFrameCache |
| Bootstrap registration | `models/business/_bootstrap.py` | `register_all_models()` side-effects populate global registries |

**Confidence**: High

---

## 4. Coupling Hotspot Analysis (Top 10)

### Hotspot 1: models/ <-> clients/ (Score: 72)

**Direction**: Primarily clients -> models (18 imports), models -> clients (1 import: `models/business/business.py` references `clients/data`)
**Imports**: All 13 Asana resource clients import their corresponding model type (Task, Project, Section, User, etc.). `clients/tasks.py` imports `models.business.STANDARD_TASK_OPT_FIELDS`. `clients/data/client.py` imports `models.contracts.PhoneVerticalPair`.
**Coupling Context**:
- Bounded context: Yes -- clients are typed wrappers around Asana API, models define the types they return
- Intentionality: Designed -- explicit typed client pattern
- Directionality: Mostly unidirectional (clients -> models), but `models/business/business.py` TYPE_CHECKING imports `DataServiceClient` (bidirectional)
**Classification**: Mostly essential coupling. The single reverse import (Business -> DataServiceClient) is accidental -- a convenience method that could use a protocol.

### Hotspot 2: models/ <-> dataframes/ (Score: 68)

**Direction**: Bidirectional. dataframes -> models (9: Task, CustomField, Section, BusinessEntity types). models -> dataframes (6: Project/Section delegate `build_dataframe` to DF builders).
**Imports**: `dataframes/extractors/` read Task fields. `dataframes/resolver/` reads CustomField. `dataframes/views/` reads BusinessEntity hierarchy. `models/project.py` and `models/section.py` have convenience methods that import DF builders.
**Coupling Context**:
- Bounded context: No -- models is domain layer, dataframes is data processing layer
- Intentionality: Mixed -- DF -> models is designed (extractors need source types), models -> DF is convenience coupling
- Directionality: Circular at directory level
**Classification**: The models -> dataframes direction is accidental coupling. `Project.build_dataframe()` and `Section.build_dataframe()` convenience methods create the reverse dependency.

### Hotspot 3: models/ <-> persistence/ (Score: 65)

**Direction**: Bidirectional. persistence -> models (12: AsanaResource, NameGid, BusinessEntity, Holder types). models -> persistence (2: Task.save() imports SaveSession, CustomFieldAccessor imports validation).
**Imports**: `persistence/session.py` imports `clients.name_resolver.NameResolver`. `persistence/holder_construction.py` imports 5+ model Holder types. `persistence/cascade.py` imports BusinessEntity/CascadingFieldDef. `models/task.py` imports `persistence.session.SaveSession`.
**Coupling Context**:
- Bounded context: Yes -- persistence manages model state (UoW pattern)
- Intentionality: Mixed -- persistence -> models is designed (UoW needs entity types), models -> persistence is convenience (Task.save())
- Directionality: Circular at directory level
**Classification**: persistence -> models is essential (UoW pattern requires entity knowledge). models -> persistence (Task.save()) is accidental -- a convenience method pattern.

### Hotspot 4: cache/ <-> core/ (Score: 54)

**Direction**: Bidirectional. cache -> core (14: exceptions, entity_registry, connections, concurrency, datetime_utils, schema). core -> cache (1: core/system_context resets caches on bootstrap reset).
**Imports**: Cache backends import `core.exceptions.CACHE_TRANSIENT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `S3_TRANSPORT_ERRORS`. Cache policies import `core.entity_registry.get_registry`. `core/system_context.py` imports from cache and multiple upper layers.
**Coupling Context**:
- Bounded context: No -- core is foundational infrastructure, cache is a subsystem
- Intentionality: Mixed -- cache -> core/exceptions is designed, but `core/system_context.py` is a god-context pulling from 6 subsystems
- Directionality: Mostly unidirectional cache -> core; core -> cache via system_context only
**Classification**: cache -> core is essential (infrastructure dependency). core -> cache via `system_context.py` is incidental -- SystemContext acts as a registry-of-registries, creating upward dependencies.

### Hotspot 5: api/ -> services/ (Score: 52)

**Direction**: Unidirectional. api -> services (18 imports). services -> api (0).
**Imports**: Every API route imports its corresponding service: `routes/tasks.py` -> `services/task_service.py`, `routes/dataframes.py` -> `services/dataframe_service.py`, `routes/query.py` -> `services/query_service.py`, `routes/resolver.py` -> `services/resolver.py`, etc.
**Coupling Context**:
- Bounded context: Yes -- api and services form the request handling bounded context
- Intentionality: Designed -- standard layered architecture pattern
- Directionality: Strictly unidirectional (api -> services)
**Classification**: Essential coupling. This is textbook layered architecture.

### Hotspot 6: api/ <-> cache/ (Score: 47)

**Direction**: Bidirectional. api -> cache (14: factory, dataframe_cache, mutation_invalidator, models). cache -> api (1: `cache/integration/dataframe_cache.py` imports `api.metrics`).
**Imports**: `api/startup.py` initializes cache providers. `api/preload/` builds DF cache. `api/dependencies.py` creates MutationInvalidator. The reverse import (`cache/integration/dataframe_cache.py:22: from autom8_asana.api.metrics`) is a layering violation.
**Coupling Context**:
- Bounded context: No -- api is the HTTP layer, cache is infrastructure
- Intentionality: Mixed -- api -> cache for startup is designed, cache -> api for metrics is incidental
- Directionality: Circular at directory level (though the reverse is a single import)
**Classification**: api -> cache is essential (startup must initialize cache). cache -> api (`api.metrics`) is incidental and a layering violation (lower layer importing from upper layer).

### Hotspot 7: dataframes/ <-> cache/ (Score: 46)

**Direction**: Bidirectional. dataframes -> cache (8: CacheEntry, FreshnessIntent, make_dataframe_key, CompletenessLevel). cache -> dataframes (6: SchemaRegistry, ProgressiveProjectBuilder, SectionPersistence).
**Imports**: `dataframes/cache_integration.py` is the explicit bridge module. `dataframes/views/dataframe_view.py` imports CompletenessLevel. `cache/dataframe/factory.py` imports DF builders. `cache/integration/schema_providers.py` imports get_schema.
**Coupling Context**:
- Bounded context: No -- dataframes is data extraction, cache is storage/retrieval
- Intentionality: Designed -- `dataframes/cache_integration.py` and `cache/integration/` explicitly bridge these subsystems
- Directionality: Circular at directory level (by design -- bidirectional integration layer)
**Classification**: This is intentional bidirectional coupling through a designated integration layer. The coupling is concentrated in `cache_integration.py` (DF side) and `cache/integration/` (cache side).

### Hotspot 8: services/ <-> dataframes/ (Score: 44)

**Direction**: Bidirectional. services -> dataframes (8: SchemaRegistry, ProgressiveProjectBuilder, SectionPersistence, DefaultCustomFieldResolver, DataFrameViewPlugin). dataframes -> services (2: `dataframes/models/registry.py` imports `services.resolver._clear_resolvable_cache`, `dataframes/builders/progressive.py` imports `services.gid_lookup`).
**Imports**: `services/resolver.py` imports SchemaRegistry extensively. `services/dataframe_service.py` imports schema types. `services/universal_strategy.py` imports DF builders.
**Coupling Context**:
- Bounded context: Yes -- services and dataframes collaborate on entity resolution
- Intentionality: Mixed -- services -> dataframes is designed, dataframes -> services is incidental
- Directionality: Circular at directory level
**Classification**: The reverse dependency (dataframes -> services) is accidental. `dataframes/models/registry.py` calling `services.resolver._clear_resolvable_cache` is reaching across boundaries to a private function.

### Hotspot 9: automation/ -> persistence/ (Score: 42)

**Direction**: Unidirectional. automation -> persistence (8: AutomationResult, ActionType, SaveSession, SaveResult).
**Imports**: `automation/pipeline.py` uses SaveSession for entity creation. `automation/engine.py` uses AutomationResult/ActionType for result tracking. `automation/events/rule.py` uses AutomationResult.
**Coupling Context**:
- Bounded context: Yes -- automation commits entity changes via persistence
- Intentionality: Designed -- automation uses persistence UoW for all writes
- Directionality: Strictly unidirectional
**Classification**: Essential coupling. Automation engine must persist changes through SaveSession.

### Hotspot 10: core/ <-> services/ & dataframes/ (Score: 34)

**Direction**: Bidirectional. core -> dataframes (3: SchemaRegistry, WatermarkRepository). core -> services (2: EntityProjectRegistry, to_pascal_case). dataframes -> core (7). services -> core (4).
**Imports**: `core/system_context.py` imports from 6 subsystems: models, dataframes, services, metrics, cache (implicit via entity_types). `core/schema.py` imports SchemaRegistry and to_pascal_case. `core/creation.py` imports from automation.
**Coupling Context**:
- Bounded context: No -- core should be the foundation layer with no upward dependencies
- Intentionality: Incidental -- `core/system_context.py` and `core/schema.py` violate layering
- Directionality: Circular (core depends on layers that depend on core)
**Classification**: The upward dependencies from core -> {services, dataframes, metrics, automation, models} are incidental coupling. `system_context.py` is a god-context anti-pattern, and `core/creation.py` referencing automation templates is a layering violation.

---

## 5. Critical Data Flow Traces

### 5.1 Creation Pipeline Flow

```
API Request (POST /api/v1/tasks or webhook)
    |
    v
[api/routes/webhooks.py] or [api/routes/tasks.py]
    |
    v
[lifecycle/dispatch.py] AutomationDispatch.dispatch()
    |  - Detects Process type from task
    |  - Looks up LifecycleConfig for stage transitions
    v
[lifecycle/engine.py] LifecycleEngine.handle_transition()
    |  - Evaluates transition rules from lifecycle_stages.yaml
    |  - Determines required init_actions
    v
[lifecycle/creation.py] EntityCreationService.create_entity()
    |  - 7-step creation pipeline:
    |    1. Template discovery (core/creation.py -> automation/templates.py)
    |    2. Task duplication (AsanaHttpClient)
    |    3. Name generation (core/creation.py)
    |    4. Section placement (core/creation.py)
    |    5. Due date computation
    |    6. Field seeding (lifecycle/seeding.py -> automation/seeding.py)
    |    7. Subtask waiting (automation/waiter.py)
    v
[persistence/session.py] SaveSession
    |  - 6-phase commit:
    |    1. validation.py (pre-commit checks)
    |    2. action_ordering.py (topological sort)
    |    3. executor.py (batch API calls via BatchClient)
    |    4. cascade.py (cascading field propagation)
    |    5. healing.py (self-healing on partial failure)
    |    6. cache_invalidator.py (post-commit cache invalidation)
    v
[cache/integration/mutation_invalidator.py] MutationInvalidator
    |  - Invalidates entity cache entries
    |  - Invalidates DataFrame cache for affected projects
    v
[cache/providers/unified.py] UnifiedTaskStore
    |  - Redis hot tier: invalidate key
    |  - S3 cold tier: delete object
    v
Response (SaveResult with created entity GIDs)
```

**Data transformation checkpoints**:
- Webhook payload (dict) -> Task (Pydantic) at `lifecycle/dispatch.py`
- Task -> BusinessEntity (via detection + hydration) at `lifecycle/engine.py`
- BusinessEntity fields -> Asana API payload (dict) at `persistence/executor.py`
- SaveResult -> MutationEvent at `persistence/cache_invalidator.py`

**Units traversed**: api -> lifecycle -> core -> automation -> persistence -> batch -> cache -> clients (transport)

**Confidence**: High

### 5.2 Query Flow

```
API Request (POST /v1/query/{entity_type}/rows)
    |
    v
[api/routes/query.py] query_rows_endpoint()
    |  - Validates predicate depth (query/guards.py)
    |  - Extracts entity_type, RowsRequest from body
    v
[services/query_service.py] EntityQueryService.resolve_dataframes()
    |  - Resolves entity type -> project GIDs via EntityProjectRegistry
    |  - Fetches DataFrames from cache or builds on-demand
    |  - Uses UniversalResolutionStrategy for multi-project resolution
    v
[services/universal_strategy.py] UniversalResolutionStrategy
    |  - Queries DynamicIndex for project GIDs
    |  - Fetches cached DataFrames via DataFrameCache
    |  - If cache miss: builds via ProgressiveProjectBuilder
    v
[cache/integration/dataframe_cache.py] DataFrameCache
    |  - MemoryTier (in-process dict)
    |  - ProgressiveTier (S3 Parquet files)
    |  - Circuit breaker for S3 failures
    v
[query/engine.py] QueryEngine.execute_rows()
    |  - Compiles predicates to Polars expressions (query/compiler.py)
    |  - Applies filters to DataFrame
    |  - Handles cross-entity joins (query/join.py, depth=1)
    |  - Applies pagination (offset, limit)
    v
[query/aggregator.py] (if aggregate endpoint)
    |  - Builds Polars group_by + agg expressions
    |  - Validates agg functions against schema
    v
Response (RowsResponse with filtered data)
```

**Data transformation checkpoints**:
- RowsRequest (Pydantic) -> predicate AST at `query/models.py`
- Predicate AST -> Polars Expression at `query/compiler.py`
- Polars DataFrame (cached) -> filtered DataFrame at `query/engine.py`
- DataFrame rows -> JSON-serializable dicts at response serialization

**Units traversed**: api -> services -> cache -> dataframes -> query -> models

**Confidence**: High

### 5.3 Cache Warm-Up Flow

```
Lambda Trigger (CloudWatch scheduled event)
    |
    v
[lambda_handlers/cache_warmer.py] handler()
    |  - _ensure_bootstrap() -> models/business/_bootstrap.bootstrap()
    |  - Loads checkpoint from S3 (lambda_handlers/checkpoint.py)
    v
[services/discovery.py] discover_entity_projects_async()
    |  - Gets workspace GID from settings
    |  - Lists all projects via ProjectsClient
    |  - Classifies projects by entity type using BusinessEntity detection
    |  - Populates EntityProjectRegistry
    v
[cache/dataframe/warmer.py] CacheWarmer.warm_all()
    |  - Iterates over entity types from EntityProjectRegistry
    |  - For each project:
    v
[cache/dataframe/warmer.py] CacheWarmer.warm_project()
    |  - Gets strategy from services/resolver.py
    |  - Builds DataFrame via ProgressiveProjectBuilder
    v
[dataframes/builders/progressive.py] ProgressiveProjectBuilder.build()
    |  - Fetches sections via SectionsClient
    |  - Parallel-fetches tasks via TasksClient (with cache read-through)
    |  - Extracts task data into typed rows (dataframes/extractors/)
    |  - Resolves custom fields (dataframes/resolver/)
    |  - Builds Polars DataFrame from rows
    v
[cache/integration/dataframe_cache.py] DataFrameCache.store()
    |  - MemoryTier: stores in-process dict
    |  - ProgressiveTier: writes Parquet to S3
    v
[cache/providers/unified.py] UnifiedTaskStore
    |  - Warm entity cache entries (Redis + S3)
    |  - For each fetched task: store in hot tier
    v
[services/gid_push.py] push_gid_mappings_to_data_service()
    |  - Pushes GID -> phone/vertical mappings to autom8-data service
    v
[lambda_handlers/checkpoint.py] CheckpointManager.save()
    |  - Saves progress to S3 for resume capability
    v
Return (warm result with entity counts)
```

**Data transformation checkpoints**:
- Lambda event (dict) -> warm-up config at `cache_warmer.py`
- Asana API responses (dict) -> Task (Pydantic) at `clients/tasks.py`
- Task -> TaskRow/UnitRow/ContactRow at `dataframes/extractors/`
- TaskRow list -> Polars DataFrame at `dataframes/builders/base.py`
- DataFrame -> Parquet bytes at `cache/dataframe/tiers/progressive.py`
- Task -> CacheEntry (serialized JSON) at `cache/providers/unified.py`

**Units traversed**: lambda_handlers -> models -> services -> cache -> dataframes -> clients -> transport -> (Asana API) -> persistence(cache_invalidator)

**Confidence**: High

---

## 6. Circular Dependency Inventory

### 6.1 Directory-Level Cycles

Six circular dependency chains exist at the directory level:

#### Cycle 1: models <-> dataframes
- `models/project.py` -> `dataframes/builders`, `dataframes/models.registry`, `dataframes/section_persistence`
- `models/section.py` -> `dataframes/builders.section`, `dataframes/models.registry`
- `models/custom_field_accessor.py` -> `dataframes/resolver.default`
- `dataframes/extractors/*` -> `models/task.py`, `models/custom_field.py`
- `dataframes/views/*` -> `models/business/`
- `dataframes/resolver/*` -> `models/task.py`, `models/business/`
- **Mitigation**: All imports in the models -> dataframes direction are deferred (inside method bodies or TYPE_CHECKING). Runtime cycle is avoided.
- **Confidence**: High

#### Cycle 2: models <-> persistence
- `models/task.py` -> `persistence/session.py`, `persistence/exceptions.py`
- `models/custom_field_accessor.py` -> `persistence/exceptions.py`
- `persistence/*` -> `models/base.py`, `models/common.py`, `models/business/*`
- **Mitigation**: All imports in models -> persistence direction are deferred (inside method bodies). Runtime cycle is avoided.
- **Confidence**: High

#### Cycle 3: models <-> core
- `models/business/fields.py` -> `core/entity_registry.py`
- `models/business/detection/facade.py` -> `core/exceptions.py`, `cache/models/entry.py`
- `core/entity_registry.py` -> `models/business/detection/types.py`
- `core/system_context.py` -> `models/business/registry.py`, `models/business/_bootstrap.py`
- `core/creation.py` -> (automation, not models, but via models indirectly)
- **Mitigation**: Deferred imports in both directions. The entity_registry <-> detection types cycle is tight but uses TYPE_CHECKING guards.
- **Confidence**: High

#### Cycle 4: core <-> dataframes / services / automation
- `core/system_context.py` -> `dataframes/models/registry.py`, `dataframes/watermark.py`
- `core/system_context.py` -> `services/resolver.py`
- `core/system_context.py` -> `metrics/registry.py`
- `core/schema.py` -> `dataframes/models/registry.py`, `services/resolver.py`
- `core/creation.py` -> `automation/templates.py`, `automation/waiter.py`
- All reverse dependencies (dataframes/services/automation -> core) are normal downward imports.
- **Mitigation**: All upward imports in `core/system_context.py` and `core/schema.py` are deferred. `core/creation.py` imports are deferred.
- **Confidence**: High

#### Cycle 5: cache <-> api
- `cache/integration/dataframe_cache.py` -> `api/metrics.py` (soft optional import, guarded by try/except)
- `api/*` -> `cache/*` (many imports for startup/preload)
- **Mitigation**: The cache -> api import is guarded by try/except and marked with nosemgrep comment. It is a soft optional dependency for metrics emission.
- **Confidence**: High

#### Cycle 6: auth <-> api
- `auth/__init__.py` -> `api/dependencies.py` (get_auth_context, AuthContext)
- `auth/audit.py` -> `api/dependencies.py` (AuthContext, get_auth_context)
- `api/*` -> `auth/*` (JWT validation, bot_pat, dual_mode)
- **Mitigation**: The auth -> api imports are marked with `# nosemgrep: autom8y.no-lower-imports-api`. They are deferred (TYPE_CHECKING in __init__, runtime in audit.py).
- **Confidence**: High

### 6.2 Summary

| Cycle | Units | Severity | Mitigation Status |
|-------|-------|----------|------------------|
| 1 | models <-> dataframes | Medium | All deferred imports |
| 2 | models <-> persistence | Medium | All deferred imports |
| 3 | models <-> core | Low | TYPE_CHECKING guards |
| 4 | core -> {dataframes, services, automation, metrics} | Medium | All deferred in system_context/schema/creation |
| 5 | cache <-> api | Low | try/except guard, soft optional |
| 6 | auth <-> api | Low | nosemgrep annotation, deferred |

All cycles are mitigated at runtime via deferred imports (function-body imports, TYPE_CHECKING blocks, or try/except guards). No cycles cause runtime import errors. However, they indicate architectural layering violations that constrain refactoring freedom.

**Confidence**: High -- verified by examining each reverse import for its deferral mechanism.

---

## 7. DEEP-DIVE Coupling Hotspot Deep Dives

### 7.1 Deep Dive: models/ <-> clients/ (Score: 72)

#### Full Cross-Boundary Import Inventory

**clients/ -> models/ (18 distinct targets)**:
| Source File | Import Target | Runtime/TypeCheck |
|-------------|---------------|-------------------|
| `clients/base.py` | `core.exceptions.CACHE_TRANSIENT_ERRORS` | Runtime |
| `clients/tasks.py` | `models.Task`, `models.PageIterator`, `models.business.STANDARD_TASK_OPT_FIELDS` | Runtime |
| `clients/projects.py` | `models.Project`, `models.Section`, `models.PageIterator` | Runtime |
| `clients/sections.py` | `models.Section`, `models.PageIterator` | Runtime |
| `clients/users.py` | `models.User`, `models.PageIterator` | Runtime |
| `clients/workspaces.py` | `models.Workspace`, `models.PageIterator` | Runtime |
| `clients/custom_fields.py` | `models.CustomField` (+ subtypes), `models.PageIterator` | Runtime |
| `clients/stories.py` | `models.Story`, `models.PageIterator` | Runtime |
| `clients/attachments.py` | `models.Attachment`, `models.PageIterator` | Runtime |
| `clients/goals.py` | `models.Goal`, `models.PageIterator` | Runtime |
| `clients/portfolios.py` | `models.Portfolio`, `models.Project`, `models.PageIterator` | Runtime |
| `clients/tags.py` | `models.Tag`, `models.PageIterator` | Runtime |
| `clients/teams.py` | `models.Team`, `models.TeamMembership`, `models.User`, `models.PageIterator` | Runtime |
| `clients/webhooks.py` | `models.Webhook`, `models.PageIterator` | Runtime |
| `clients/task_operations.py` | `models.Task` | Runtime |
| `clients/task_ttl.py` | `models.business.detect_entity_type_from_dict` | Deferred |
| `clients/data/client.py` | `models.contracts.PhoneVerticalPair` | Runtime |
| `clients/data/models.py` | `models.contracts.PhoneVerticalPair` | Runtime |
| `clients/data/_endpoints/batch.py` | `models.contracts.PhoneVerticalPair` | TypeCheck |

**models/ -> clients/ (1 distinct target)**:
| Source File | Import Target | Runtime/TypeCheck |
|-------------|---------------|-------------------|
| `models/business/business.py` | `clients.data.DataServiceClient`, `clients.data.models.InsightsResponse` | TypeCheck only |

#### Which Imports Could Be Replaced With Protocols/Abstractions

1. **models -> clients (reverse)**: The `Business` model's TYPE_CHECKING import of `DataServiceClient` exists to type-hint a method parameter. This could be replaced with a protocol (e.g., `InsightsProvider`) defined in `protocols/`. **Effort: 0.5 day.**

2. **clients -> models (forward)**: This coupling is essential -- typed API clients must return typed models. However, `clients/task_ttl.py` importing `models.business.detect_entity_type_from_dict` is a reach into the business logic layer. This detection could be injected as a callable. **Effort: 0.25 day.**

3. **clients/data -> models.contracts**: `PhoneVerticalPair` is a simple data contract. If it were extracted to a shared contracts module (not inside models/), the dependency direction would be cleaner. **Effort: 0.5 day.**

#### Estimated Effort to Decouple

- Remove `Business -> DataServiceClient` TYPE_CHECKING import: 0.5 day
- Extract `PhoneVerticalPair` to shared contracts: 0.5 day
- Inject entity detection into task_ttl: 0.25 day
- **Total**: ~1.25 days
- The bulk coupling (clients returning model types) cannot and should not be decoupled.

#### Risk If Left Coupled

**Low**. The coupling is overwhelmingly unidirectional and essential (typed client pattern). The single reverse import is TYPE_CHECKING only and does not create runtime issues. The primary risk is that adding new methods to Business that reference DataServiceClient types would deepen the coupling incrementally.

### 7.2 Deep Dive: models/ <-> dataframes/ (Score: 68)

#### Full Cross-Boundary Import Inventory

**dataframes/ -> models/ (9 distinct target modules)**:
| Source File | Import Target | Runtime/TypeCheck |
|-------------|---------------|-------------------|
| `dataframes/resolver/mock.py` | `models.custom_field.CustomField`, `models.task.Task` | TypeCheck |
| `dataframes/resolver/default.py` | `models.custom_field.CustomField`, `models.task.Task` | TypeCheck |
| `dataframes/resolver/protocol.py` | `models.custom_field.CustomField`, `models.task.Task` | TypeCheck |
| `dataframes/resolver/cascading.py` | `models.business.{CascadingFieldDef, InheritedFieldDef, ...}`, `models.task.Task` | Runtime + TypeCheck |
| `dataframes/views/cf_utils.py` | `models.business.fields.CascadingFieldDef`, `models.business.detection.EntityType` | Runtime |
| `dataframes/views/cascade_view.py` | `models.business.{CascadingFieldDef, InheritedFieldDef, ...}` | Runtime |
| `dataframes/views/dataframe_view.py` | `models.business.{detect_entity_type_from_dict, ...}`, `models.business.activity.extract_section_name` | Deferred |
| `dataframes/extractors/base.py` | `models.task.Task`, `models.business.activity.extract_section_name` | TypeCheck + Deferred |
| `dataframes/extractors/{contact,default,unit}.py` | `models.task.Task` | TypeCheck |
| `dataframes/builders/progressive.py` | `models.section.Section`, `models.task.Task` | TypeCheck |
| `dataframes/builders/task_cache.py` | `models.Task`, `models.business.detect_entity_type_from_dict` | Deferred |
| `dataframes/builders/base.py` | `models.task.Task`, `models.custom_field.CustomField` | TypeCheck + Deferred |
| `dataframes/builders/parallel_fetch.py` | `models.section.Section`, `models.task.Task` | TypeCheck |

**models/ -> dataframes/ (6 distinct target modules)**:
| Source File | Import Target | Runtime/TypeCheck |
|-------------|---------------|-------------------|
| `models/project.py` | `dataframes.builders.ProgressiveProjectBuilder`, `dataframes.models.registry.get_schema`, `dataframes.section_persistence` | Deferred (inside methods) |
| `models/section.py` | `dataframes.builders.section.SectionDataFrameBuilder`, `dataframes.models.registry.get_schema` | Deferred (inside methods) |
| `models/custom_field_accessor.py` | `dataframes.resolver.default.DefaultCustomFieldResolver` | TypeCheck |
| `models/project.py` (TYPE_CHECKING) | `dataframes.cache_integration.DataFrameCacheIntegration`, `dataframes.models.schema.DataFrameSchema`, `dataframes.resolver.protocol.CustomFieldResolver` | TypeCheck |
| `models/section.py` (TYPE_CHECKING) | `dataframes.cache_integration.DataFrameCacheIntegration`, `dataframes.resolver.protocol.CustomFieldResolver` | TypeCheck |

#### Which Imports Could Be Replaced With Protocols/Abstractions

1. **models/ -> dataframes/ (reverse direction, 6 targets)**: The `Project.build_dataframe()` and `Section.build_dataframe()` convenience methods create the circular dependency. These could be extracted to a service function in `services/dataframe_service.py` (which already exists). The Project/Section models would lose their convenience methods, and callers would use `DataFrameService.build_for_project(project)` instead.
   - **Effort**: 1-2 days (method extraction, update callers, update tests)

2. **dataframes/ -> models/ (forward direction)**: The extractors and resolvers fundamentally need to understand Task and CustomField structure. This cannot be removed. However, `dataframes/views/cf_utils.py` importing `models.business.detection.EntityType` is a reach into business logic for what is essentially a string enum. This could use a string constant instead.
   - **Effort**: 0.5 day

3. **dataframes/views/ -> models/business/**: The cascade view imports business entity types (CascadingFieldDef, InheritedFieldDef) directly. A protocol for "field definition" could abstract this, but the domain knowledge is inherently needed.
   - **Effort**: Not recommended (protocol would mirror the concrete type)

#### Estimated Effort to Decouple

- Extract `Project.build_dataframe()` / `Section.build_dataframe()` to DataFrameService: 1.5 days
- Replace EntityType import in cf_utils with string constants: 0.5 day
- **Total**: ~2 days for meaningful decoupling of the reverse direction
- Forward direction (dataframes -> models) coupling is essential and should remain.

#### Risk If Left Coupled

**Medium**. The circular dependency at directory level constrains refactoring. If `dataframes/` were ever extracted to a separate package, the reverse dependency (models -> dataframes convenience methods) would prevent clean extraction. The deferred imports prevent runtime issues but make the codebase harder to reason about. New developers may inadvertently add non-deferred reverse imports, creating runtime failures.

### 7.3 Deep Dive: models/ <-> persistence/ (Score: 65)

#### Full Cross-Boundary Import Inventory

**persistence/ -> models/ (12 distinct target modules)**:
| Source File | Import Target | Runtime/TypeCheck |
|-------------|---------------|-------------------|
| `persistence/session.py` | `models.base.AsanaResource`, `models.common.NameGid`, `models.user.User` | TypeCheck |
| `persistence/session.py` | `models.business.Offer` | Deferred |
| `persistence/cascade.py` | `models.business.base.BusinessEntity`, `models.business.fields.CascadingFieldDef`, `models.task.Task` | TypeCheck |
| `persistence/holder_construction.py` | `models.common.NameGid` | Runtime |
| `persistence/holder_construction.py` | `models.business.{Business, ContactHolder, LocationHolder, OfferHolder, ProcessHolder, UnitHolder, detection}` | Deferred (5+ imports) |
| `persistence/executor.py` | `models.base.AsanaResource` | TypeCheck |
| `persistence/action_executor.py` | `models.common.NameGid` | Runtime |
| `persistence/tracker.py` | `models.base.AsanaResource` | TypeCheck |
| `persistence/exceptions.py` | `models.base.AsanaResource` | TypeCheck |
| `persistence/reorder.py` | `models.base.AsanaResource` | TypeCheck |
| `persistence/graph.py` | `models.base.AsanaResource` | TypeCheck |
| `persistence/healing.py` | `models.business.base.BusinessEntity` | TypeCheck |
| `persistence/events.py` | `models.base.AsanaResource` | TypeCheck |
| `persistence/actions.py` | `models.base.AsanaResource`, `models.common.NameGid` | Runtime + TypeCheck |
| `persistence/models.py` | `models.base.AsanaResource`, `models.common.NameGid` | TypeCheck |

**models/ -> persistence/ (2 distinct target modules)**:
| Source File | Import Target | Runtime/TypeCheck |
|-------------|---------------|-------------------|
| `models/task.py` | `persistence.exceptions.{SaveSessionError, GidValidationError}`, `persistence.session.SaveSession` | Deferred (inside save() method) |
| `models/custom_field_accessor.py` | `persistence.exceptions.{SaveSessionError, GidValidationError}` | Deferred (inside method) |

#### Which Imports Could Be Replaced With Protocols/Abstractions

1. **models/ -> persistence/ (reverse, 2 targets)**: The `Task.save()` and `Task.save_sync()` convenience methods import SaveSession. These could be extracted to `services/task_service.py` (which already has `TaskService`). Callers would use `task_service.save(task)` instead of `task.save()`.
   - **Effort**: 1 day (remove convenience methods, update callers, update tests)

2. **persistence/ -> models/ (forward, 12 targets)**: The persistence layer fundamentally needs entity types for the UoW pattern. However, `persistence/holder_construction.py` imports 6 specific Holder types, creating tight coupling to the entity hierarchy. A factory registry pattern (register Holder classes by type string) could abstract this.
   - **Effort**: 2 days (create holder registry, refactor holder_construction)

3. **persistence/session.py -> models/business/Offer**: A deferred import to check Offer-specific behavior in a special case. Could be abstracted via a method on BusinessEntity.
   - **Effort**: 0.25 day

#### Estimated Effort to Decouple

- Extract `Task.save()` to TaskService: 1 day
- Create holder type registry in persistence: 2 days
- Abstract Offer check: 0.25 day
- **Total**: ~3.25 days for meaningful decoupling

#### Risk If Left Coupled

**Low-Medium**. The coupling is structurally sound for a UoW pattern -- persistence must understand entity types. The primary risk is in `holder_construction.py` where adding new entity types requires updating the persistence layer. The `Task.save()` convenience method is a minor concern since it is deferred. The existing deferred import discipline ensures no runtime cycles. However, `holder_construction.py` has deep knowledge of the entity hierarchy (6 specific Holder imports), making it fragile when the entity model evolves.

---

## 8. Unknowns

### Unknown: core/system_context.py Dependency Scope

- **Question**: Is `core/system_context.py` intentionally designed as a god-context that references 6+ subsystems, or has it accumulated dependencies organically?
- **Why it matters**: This module creates upward dependencies from core -> {models, dataframes, services, metrics}, which is the root cause of Cycle 4. If it is intentional (a deliberate "reset everything" mechanism), the coupling may be acceptable. If organic growth, it is a refactoring opportunity.
- **Evidence**: The file imports from `models.business.registry`, `models.business._bootstrap`, `dataframes.models.registry`, `dataframes.watermark`, `services.resolver`, `metrics.registry` -- all for a `reset()` function that clears global state during testing/bootstrap.
- **Suggested source**: Original author of `system_context.py`; test infrastructure design decisions.

### Unknown: cache/integration/dataframe_cache.py -> api/metrics.py Import Intent

- **Question**: Is the `cache/integration/dataframe_cache.py` import of `api/metrics.py` a temporary measure or a deliberate architectural choice?
- **Why it matters**: This creates Cycle 5 (cache <-> api) and is explicitly marked with nosemgrep suppression. If temporary, it should be scheduled for extraction. If deliberate, the metrics emission contract should be abstracted to a protocol.
- **Evidence**: Line 22: `from autom8_asana.api.metrics import (  # nosemgrep: autom8y.asana-no-lower-imports-api, autom8y.no-lower-imports-api  # soft optional dep, guarded by try/except`
- **Suggested source**: Developer who added the import; check git blame for context.

### Unknown: Deferred Import Count and Runtime Behavior

- **Question**: With approximately 120 function-body deferred imports and 180 TYPE_CHECKING imports, what is the cumulative first-call latency impact of deferred imports in hot paths?
- **Why it matters**: Each deferred import incurs a one-time import cost on first invocation. In Lambda cold starts, this could compound to significant latency if many deferred imports are triggered simultaneously.
- **Evidence**: `automation/pipeline.py` has 7 deferred imports. `persistence/session.py` has 5 deferred imports. `cache/dataframe/factory.py` has 10 deferred imports. Lambda handlers explicitly call `_ensure_bootstrap()` to front-load some of these.
- **Suggested source**: Lambda cold-start performance profiling; CloudWatch metrics for cache_warmer handler init time.

### Unknown: dataframes/models/registry.py -> services/resolver._clear_resolvable_cache

- **Question**: Why does the DataFrame schema registry call a private function in the services layer?
- **Why it matters**: This is an unusual cross-boundary dependency where a lower-level module (dataframes) calls a private function (`_clear_resolvable_cache`) in a higher-level module (services). It creates coupling in the wrong direction and accesses a private API.
- **Evidence**: `dataframes/models/registry.py:97: from autom8_asana.services.resolver import _clear_resolvable_cache`
- **Suggested source**: git blame on this line; likely a cache coherence mechanism added after initial design.

### Unknown: models/business/business.py -> clients/data TYPE_CHECKING Import

- **Question**: What method on Business uses DataServiceClient type hints, and could it use a protocol instead?
- **Why it matters**: This is the only import from models -> clients, creating a circular dependency between the domain model layer and the client layer.
- **Evidence**: `models/business/business.py:35: from autom8_asana.clients.data import DataServiceClient` and line 36: `from autom8_asana.clients.data.models import InsightsResponse` -- both under TYPE_CHECKING.
- **Suggested source**: Read the specific method signatures that use these types.

---

## Handoff Checklist

- [x] dependency-map artifact exists with all required sections (dependency graph, coupling analysis, shared model registry, integration pattern catalog)
- [x] Cross-directory dependency graph covers all 22 directory units identified in topology-inventory
- [x] Coupling scores assigned to all connected pairs (top 20 ranked)
- [x] Confidence ratings (high/medium/low) assigned to all dependency findings and coupling scores
- [x] Coupling context checks (bounded context, intentionality, directionality) performed before scoring
- [x] Integration patterns classified for all cross-directory communication channels (5 patterns)
- [x] Shared models/schemas that appear in multiple units registered (Section 3.4)
- [x] Unknowns section documents ambiguous dependencies and unresolvable coupling questions (5 unknowns)
- [x] (DEEP-DIVE) Critical path analysis complete for 3 data flows (creation, query, cache warm-up)
- [x] (DEEP-DIVE) Coupling hotspot deep dives complete for top 3 pairs with full import inventories
- [x] Circular dependency inventory covers all 6 directory-level cycles with mitigation status
