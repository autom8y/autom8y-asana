# Architectural Review 1: Dependency and Coupling Topology

**Date**: 2026-02-18
**Scope**: Dependency analysis across all 27 packages (~111K LOC)
**Methodology**: Dependency analyst agents (steel-man + straw-man) with fan-in/fan-out measurement
**Review ID**: ARCH-REVIEW-1

---

## 1. Fan-In Gravity Wells

Fan-in measures how many modules depend on a given module. High fan-in modules are gravity wells -- changes to them ripple widely.

| Module | Fan-In | Description |
|--------|--------|-------------|
| `models/` | 20+ | Business entity models imported by nearly every package |
| `config.py` + `settings.py` | 34+ | Configuration consumed everywhere |
| `protocols/` | 16+ | Protocol definitions (CacheProvider, AuthProvider, LogProvider, ItemLoader, ObservabilityHook) |
| `core/` | 14+ | Entity registry, exceptions, timing, creation utilities |
| `cache/` | 12+ | Cache providers, models, policies |
| `exceptions.py` | 10+ | SDK exception types |
| `client.py` | 8+ | AsanaClient facade |
| `transport/` | 6+ | HTTP transport layer |

### Gravity Well Analysis

**models/ (fan-in 20+)**: The business model package is the most depended-upon module. Every package that works with entities imports from `models.business`. This is structurally correct -- models should be at the bottom of the dependency graph. However, the `__init__.py` import-time side effect (`register_all_models()`) means every importer pays the registration cost.

**config.py + settings.py (fan-in 34+)**: Configuration is the highest fan-in when counted as individual import sites. This is expected for centralized configuration but creates a vulnerability: a breaking change to config schema affects 34+ consumers.

**protocols/ (fan-in 16+)**: Protocol definitions are widely imported for type annotations and dependency injection. This is the intended use pattern -- protocols define boundaries.

**core/ (fan-in 14+)**: The core package (entity registry, exceptions, timing) serves as a shared utility layer. After WS5-WS7 refactoring, `core/timing.py`, `core/creation.py`, and `core/exceptions.py` were added, increasing fan-in intentionally.

---

## 2. Coupling Hotspot Analysis

Coupling score combines fan-in, fan-out, and the nature of dependencies (structural vs behavioral, tight vs loose).

| Package | Coupling Score | Fan-In | Fan-Out | Coupling Type | Risk |
|---------|---------------|--------|---------|---------------|------|
| `models/` | 7/10 | 20+ | 3 | Structural (types) | Changes to model fields ripple to all consumers |
| `cache/` | 8/10 | 12 | 8 | Behavioral (state) | Cache behavior changes affect all cached paths |
| `config.py` | 6/10 | 34+ | 0 | Data (values) | Schema changes require coordinated consumer updates |
| `core/entity_registry.py` | 7/10 | 14+ | 5 | Structural + behavioral | Registry changes affect detection, schema, caching |
| `persistence/session.py` | 6/10 | 5 | 12 | Behavioral (orchestration) | High fan-out; orchestrates 8 collaborators |
| `clients/data/client.py` | 5/10 | 3 | 6 | Behavioral (I/O) | Sole HTTP gateway; changes affect all data access |
| `services/resolver.py` | 5/10 | 4 | 5 | Behavioral + structural | Bidirectional dependency with universal_strategy.py |

### Score Rationale

**cache/ (8/10)**: Highest coupling score because it has both significant fan-in (12 consumers) and high fan-out (8 dependencies including Redis, S3, metrics, protocols, models, policies). Cache behavior changes have both immediate (consumer-facing) and indirect (backend-facing) ripple effects. The two separate cache systems (entity vs DataFrame) compound the coupling.

**models/ (7/10)**: High fan-in but low fan-out (models depend on little). Score elevated because import-time side effects mean importing models has behavioral consequences beyond type access.

**core/entity_registry.py (7/10)**: Central to 4 subsystems (detection, schema, caching, services). The EntityDescriptor frozen dataclass is the schema for entity metadata -- changes to its fields affect all 4 consumers.

---

## 3. Integration Pattern Classification

| Integration Point | Call Style | Mediation | Timing | Coupling | Pattern |
|-------------------|-----------|-----------|---------|----------|---------|
| Entity models -> Cache | Direct call | Protocol (`CacheProvider`) | Sync + Async | Loose | Cache-aside with protocol boundary |
| Detection -> EntityRegistry | Direct call | None | Sync | Tight | Module-level constant lookup |
| SaveSession -> Asana API | Direct call | Client facade | Async | Tight | Sequential phase execution |
| SaveSession -> CacheInvalidator | Direct call | None | Async (fire-and-forget) | Medium | Post-commit hook |
| Query Engine -> SchemaRegistry | Direct call | Singleton | Sync | Medium | Lazy-init singleton access |
| Query Engine -> DataFrames | Direct call | None | Sync | Tight | Direct Polars operations |
| DataFrame Builder -> Extractors | Direct call | None | Sync | Tight | Strategy pattern via registry |
| Lambda Warmer -> Cache | Direct call | Protocol | Async | Loose | Priority-ordered warming |
| API Routes -> Query Engine | Direct call | None | Async | Medium | Dependency injection via FastAPI |
| Automation Rules -> SaveSession | Direct call | None | Async | Tight | Post-commit automation firing |
| Configuration -> All consumers | Import | Module attribute | Sync | Loose (data) | Centralized config, scattered consumption |
| Client facade -> Sub-clients | Composition | None | Both | Tight | Facade delegates to 13 sub-clients |

### Pattern Summary

| Pattern | Count | Coupling Level |
|---------|-------|---------------|
| Protocol-mediated (loose) | 3 | Loose -- changes to implementation do not affect consumers |
| Direct call with DI (medium) | 4 | Medium -- interface is stable but implementation can vary |
| Direct call, tight coupling | 5 | Tight -- both sides must change together |

The codebase uses protocols for cache boundaries (`CacheProvider`) and auth (`AuthProvider`) but relies on direct coupling for most internal integrations. The protocol boundary stops at the cache layer -- query engine, DataFrame builders, and automation rules use direct imports.

---

## 4. Cohesion Assessment

| Package | Cohesion | Rating | Rationale |
|---------|----------|--------|-----------|
| `query/` | High | Excellent | 8 modules, all focused on query compilation and execution |
| `models/business/detection/` | High | Excellent | 5 tiers + types, single responsibility per file |
| `core/` | High | Good | Shared utilities with clear boundaries (after WS5-WS7) |
| `dataframes/` | High | Good | Builders, extractors, schemas, storage -- all DataFrame-related |
| `protocols/` | High | Good | Pure protocol definitions, no implementation |
| `transport/` | High | Good | HTTP transport only |
| `automation/` | Medium | Adequate | Pipeline rules, seeding, events, polling, workflows -- related but diverse |
| `lifecycle/` | Medium | Adequate | Engine, creation, seeding -- lifecycle management cohesion |
| `cache/` | Medium | Adequate | Models, backends, providers, policies, integration -- cache-related but broad |
| `clients/` | Medium | Adequate | 13 sub-clients sharing patterns but each for a different Asana resource |
| `services/` | Low | Needs attention | Resolver, universal strategy, query service, discovery -- diverse responsibilities |
| `persistence/` | Low | Needs attention | SaveSession (1,853L) + change tracking + cascade + healing -- mixed concerns |
| `models/business/` | Low | Needs attention | 8 sub-domains in one package (business, contact, offer, unit, process, location, hours, detection) |
| `api/` | Low | Needs attention | Routes, preload, lifespan, middleware -- API framework + cache warming |

### Cohesion Concerns

**services/ (Low)**: Contains `resolver.py` (entity resolution), `universal_strategy.py` (resolution strategy), `query_service.py` (query data access), and `discovery.py` (entity discovery). These are related by "services" label but serve different subsystems. The bidirectional dependency between `resolver.py` and `universal_strategy.py` (requiring deferred imports) is a cohesion smell.

**persistence/ (Low)**: `SaveSession` at 1,853 lines dominates the package. It mixes entity tracking, dirty detection, dependency ordering, CRUD execution, cascade execution, healing, automation, and cache invalidation. Although it delegates to collaborators, the orchestration itself is a mixed concern.

**models/business/ (Low)**: One package containing 8 entity-specific sub-domains (`business.py`, `contact.py`, `offer.py`, `unit.py`, `process.py`, `location.py`, `hours.py`, `reconciliation.py`) plus shared infrastructure (`base.py`, `descriptors.py`, `holder_factory.py`, `hydration.py`, `registry.py`, `activity.py`, `sections.py`, `detection/`). The 85-export `__init__.py` is a symptom.

---

## 5. Circular Dependency Surface

### Active Circular Chains

4 active circular dependency chains, all managed via lazy imports:

| Chain | Mechanism | Risk |
|-------|-----------|------|
| `services/universal_strategy.py` <-> `services/resolver.py` | Deferred imports at lines 156, 326 (strategy) and 712 (resolver) | Bidirectional; refactoring either file requires care |
| `models/business/__init__.py` -> `_bootstrap.py` -> entity classes -> `__init__.py` | Import-time registration with idempotency guard | Fragile; new entity classes must follow registration pattern |
| `persistence/session.py` -> `persistence/cascade.py` | Deferred import at line 191 | Contained within package; low external risk |
| `automation/__init__.py` -> `automation/pipeline.py` | `__getattr__` lazy import | Intentional; prevents loading automation on basic import |

### Lazy Import Inventory

| Type | Count | Description |
|------|-------|-------------|
| `__getattr__` module-level | 6+ | Lazy loading of heavy submodules |
| Function-body imports | 20+ | Deferred imports inside function bodies |
| `TYPE_CHECKING` imports | 35+ | Type-only imports (correct pattern, not a smell) |
| `# noqa: E402` | 5 | Import-order suppression for post-registration imports |

### Risk Assessment

The circular dependencies are individually manageable but collectively fragile. Adding a new dependency between any two packages in the circular chains could create a new cycle that existing lazy imports do not handle.

---

## 6. Five Abstraction Leaks

### Leak 1: `_get_field_attr` and `_normalize_custom_fields` Cross-Package

**Before WS6**: `lifecycle/seeding.py` imported private functions (`_get_field_attr`, `_normalize_custom_fields`) from `automation/seeding.py`.

**After WS6 (RF-006)**: Functions promoted to public API (`get_field_attr`, `normalize_custom_fields`). The abstraction leak is resolved by making it an intentional public API.

**Status**: RESOLVED (post WS6)

### Leak 2: Direct Asana API Calls from Multiple Packages

Both `automation/pipeline.py` and `lifecycle/creation.py` make direct Asana API calls (`tasks.duplicate_async`, `tasks.add_to_project_async`, `tasks.update_async`) for entity creation operations.

**After WS6 (RF-005)**: Shared creation helpers in `core/creation.py` reduce duplication but both modules still make direct API calls through the shared helpers.

**Status**: PARTIALLY RESOLVED

### Leak 3: EntityDescriptor Internals in DataFrame Layer

`dataframes/models/registry.py` accesses `EntityDescriptor.schema_module_path` and `EntityDescriptor.extractor_class_path` to resolve classes via dotted path import. The DataFrame layer has knowledge of the EntityRegistry's internal resolution mechanism.

**Status**: OPEN -- the descriptor-driven pattern intentionally exposes these paths

### Leak 4: Cache EntryType Knowledge in Clients

`clients/data/client.py` and other client modules reference specific `EntryType` values when caching responses. The client layer has knowledge of cache entry type taxonomy.

**Status**: OPEN -- considered acceptable because clients know what they are caching

### Leak 5: Configuration Schema in Consumer Modules

Multiple modules access configuration attributes directly (`config.cache_ttl`, `config.s3_enabled`, etc.) rather than through a configuration service or dependency injection. Configuration schema is leaked to 34+ consumer sites.

**Status**: OPEN -- standard Python pattern; DI for configuration is not idiomatic

---

## 7. Configuration Coupling Analysis

### Centralized Definition, Scattered Consumption

Configuration is defined centrally in `config.py` + `settings.py` but consumed across 34+ modules:

```
config.py / settings.py
    |
    +-- cache/ (TTL values, S3 flags, Redis settings)
    +-- clients/ (timeout values, retry counts)
    +-- api/ (server settings, CORS, middleware)
    +-- automation/ (rule configurations, polling intervals)
    +-- lifecycle/ (stage configurations)
    +-- lambda_handlers/ (timeout limits, checkpoint settings)
    +-- dataframes/ (storage paths, memory limits)
    +-- services/ (query limits, resolution settings)
    +-- transport/ (HTTP settings, connection pools)
    ...
```

### Impact of Configuration Changes

A change to configuration schema requires:
1. Update `config.py` or `settings.py`
2. Update all consuming modules that reference the changed attribute
3. Update environment variable documentation
4. Update deployment configuration (ECS task definition, Lambda environment)
5. Test with both old and new configuration values

### No Configuration Validation at Startup

While Pydantic models in `settings.py` validate individual values, there is no cross-field validation at startup (e.g., verifying that `cache_ttl` values are consistent with `freshness_mode` settings).

---

## 8. Platform Dependency Fan-Out

### 7 autom8y-* Packages

| Package | Purpose | Coupling Level |
|---------|---------|---------------|
| `autom8y-cache` | Cache provider SDK, Freshness enum | Tight -- protocols and enums imported directly |
| `autom8y-log` | Structured logging (`get_logger`) | Loose -- logger facade only |
| `autom8y-config` | Configuration management | Medium -- config loading at startup |
| `autom8y-auth` | Authentication providers | Medium -- AuthProvider protocol |
| `autom8y-transport` | HTTP transport, rate limiting | Tight -- used for all Asana API calls |
| `autom8y-metrics` | Metrics collection | Loose -- optional emission |
| `autom8y-lambda` | Lambda handler framework | Medium -- Lambda entry point |

### Coupling Analysis

**Tight coupling (2/7)**: `autom8y-cache` and `autom8y-transport` are deeply integrated. Breaking changes in either would require coordinated updates across autom8y-asana.

**Medium coupling (3/7)**: `autom8y-config`, `autom8y-auth`, and `autom8y-lambda` are used at specific integration points (startup, authentication, Lambda entry). Changes are contained.

**Loose coupling (2/7)**: `autom8y-log` and `autom8y-metrics` are used through stable facades (`get_logger`, metrics emission). These could be swapped with minimal effort.

### Version Sensitivity

The `Freshness` enum is defined in `autom8y-cache` and re-exported with a defensive fallback:

```python
# cache/models/freshness.py
try:
    from autom8y_cache import Freshness
except ImportError:
    class Freshness(str, Enum):  # Fallback
        STRICT = "strict"
        EVENTUAL = "eventual"
        IMMEDIATE = "immediate"
```

This defensive import pattern exists because Lambda deployment may have version mismatches between `autom8y-cache` and `autom8y-asana`. It is a real-world resilience pattern, not paranoia.

---

## 9. Dependency Graph Visualization

```
                    config.py + settings.py
                         |  (34+ consumers)
                         v
    +--------+------+--------+------+--------+
    |        |      |        |      |        |
    v        v      v        v      v        v
protocols/ core/ models/  cache/ clients/ transport/
    |        |      |        |      |        |
    |        |      v        v      v        |
    |        +-> entity_  cache   data     asana
    |        |   registry  models  client   http
    |        |      |        |      |        |
    |        v      v        v      v        v
    +------> persistence/  dataframes/   automation/
                  |              |             |
                  v              v             v
              SaveSession   DataFrame    Pipeline
              (1,853 L)     Builders     Rules
                  |              |             |
                  +-------+------+------+-----+
                          |
                          v
                     services/
                     (resolver, query_service,
                      universal_strategy)
                          |
                          v
                      query/
                      (engine, compiler)
                          |
                          v
                       api/
                       (routes, preload)
                          |
                          v
                  lambda_handlers/
                  (warmer, scheduler)
```

### Key Observations

1. **models/ and config/ are at the bottom**: Correctly positioned as low-dependency foundations
2. **cache/ is mid-stack**: Depends on models and protocols, depended on by services and api
3. **services/ is a funnel**: Multiple subsystems converge through resolver and query_service
4. **api/ and lambda_handlers/ are at the top**: Correctly positioned as application entry points
5. **persistence/ has high fan-out**: SaveSession reaches into 8 collaborator modules
