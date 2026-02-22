# Architectural Review 1: Domain Boundary and Modeling Health

**Date**: 2026-02-18
**Scope**: Domain boundary alignment, modeling health, anti-patterns, risk assessment
**Methodology**: Structure evaluator agents (steel-man + straw-man) with boundary tension analysis
**Review ID**: ARCH-REVIEW-1

---

## 1. Where Package Boundaries Align with Domain

### Well-Aligned Boundaries

**detection/** -- Clean domain boundary around entity type detection.

| Property | Assessment |
|----------|-----------|
| Single responsibility | Each tier file (tier1-tier4) handles one detection strategy |
| Internal cohesion | All files serve detection; no unrelated code |
| External coupling | Depends only on `types.py` (EntityType, DetectionResult) and entity registry |
| API surface | Clean facade via `facade.py` |
| Testability | Each tier independently testable |

**Source**: `src/autom8_asana/models/business/detection/` (6 files: `__init__.py`, `config.py`, `facade.py`, `tier1.py`, `tier2.py`, `tier3.py`, `tier4.py`, `types.py`)

**entity_registry** -- SSoT for entity metadata with clean protocol.

| Property | Assessment |
|----------|-----------|
| Single responsibility | EntityDescriptor + registry lookups |
| Internal cohesion | All code serves entity metadata resolution |
| External coupling | Depended upon by many (intentional -- it is SSoT) |
| API surface | `get_registry()` -> `registry.get()`, `registry.get_by_gid()`, `registry.warmable_entities()` |
| Testability | Singleton with explicit `reset()` for test isolation |

**Source**: `src/autom8_asana/core/entity_registry.py`

**descriptors.py** -- Declarative field system with clear scope.

| Property | Assessment |
|----------|-----------|
| Single responsibility | Descriptor definitions for navigation and custom fields |
| Internal cohesion | ParentRef, HolderRef, CustomFieldDescriptor all serve field access |
| External coupling | Depends on Pydantic internals (`PrivateAttr`, `__set_name__`) |
| API surface | Descriptor classes + `_pending_fields` registration |
| Testability | Descriptors testable via model instantiation |

**Source**: `src/autom8_asana/models/business/descriptors.py`

**query/** -- Algebraic query engine with clean decomposition.

| Property | Assessment |
|----------|-----------|
| Single responsibility | 8 files, each <300 lines, each serving one query aspect |
| Internal cohesion | Models, compiler, engine, guards, joins, aggregation -- all query-related |
| External coupling | Depends on Polars and SchemaRegistry; minimal outward leakage |
| API surface | `QueryEngine`, `RowsRequest`, `RowsResponse`, `AggregateRequest`, `AggregateResponse` |
| Testability | Stateless compiler enables isolated testing |

**Source**: `src/autom8_asana/query/` (8 files, 1,935 LOC)

---

## 2. Where Package Boundaries Diverge from Domain

### models/business/ -- 8 Sub-Domains in One Package

**Source**: `src/autom8_asana/models/business/` (15,356 LOC across models/, 59 files)

The `models/business/` package contains at least 8 distinct sub-domains:

| Sub-Domain | Files | Concern |
|-----------|-------|---------|
| Entity definitions | `business.py`, `unit.py`, `contact.py`, `offer.py`, `process.py`, `location.py`, `hours.py`, `reconciliation.py`, `videography.py`, `asset_edit.py`, `dna.py` | Entity classes |
| Holder infrastructure | `holder_factory.py`, `base.py` (HolderMixin) | Holder pattern |
| Detection | `detection/` (7 files) | Entity type detection |
| Descriptors | `descriptors.py` | Field descriptor system |
| Hydration | `hydration.py` (~780 lines) | Raw data -> entity conversion |
| Section classification | `activity.py`, `sections.py` | Section-to-activity mapping |
| Registration | `_bootstrap.py`, `registry.py` | Entity registration |
| Matching | `matching/` | Entity matching logic |

The `__init__.py` exports 85+ symbols from these 8 sub-domains. A developer working on detection should not need to understand hydration; a developer working on descriptors should not need to understand section classification.

### 85-Export Barrel

`models/business/__init__.py` re-exports 85+ symbols in `__all__`. This barrel file:
- Calls `register_all_models()` at import time (side effect)
- Uses `# ruff: noqa: E402` for post-registration imports
- Makes it impossible to import a single entity class without triggering full registration

### Dual Registry in services/

`services/resolver.py` contains both `ProjectTypeRegistry` and `EntityProjectRegistry` alongside resolution logic. These registries overlap with `core/entity_registry.py`'s `EntityRegistry`, creating the triple-registry problem documented in the STRAW-MAN analysis.

---

## 3. Section Classification Inconsistency

### Three Incompatible Representations

| # | Representation | Source | Format |
|---|---------------|--------|--------|
| 1 | SectionClassifier mapping | `activity.py` | `dict[str, AccountActivity]` with 47 lowercase string keys |
| 2 | OfferSection enum | `sections.py` | `Enum` members with GID string values |
| 3 | ProcessSection | `process.py` or related | `Enum` for pipeline stages |

### The Inconsistency

- **SectionClassifier** operates on section *names* (lowercase strings)
- **OfferSection** maps to section *GIDs* (Asana identifiers)
- There is no mapping between SectionClassifier names and OfferSection GIDs
- ProcessSection represents pipeline stages, which is a different domain concept than activity classification

A section named "active" in SectionClassifier maps to `AccountActivity.ACTIVE`, while `OfferSection.ACTIVE` maps to GID `"1143843662099256"`. These two "active" representations are disconnected.

### Consequence

Adding a new section requires changes in up to 3 places, and the developer must know which representation(s) to update. There is no single "section definition" that generates all three representations.

---

## 4. Field Definition Inconsistency

### Four Representations of the Same Domain Truth

The concept "an entity has a custom field called X" is represented 4 ways:

| # | Representation | Where | Example |
|---|---------------|-------|---------|
| 1 | Descriptor declaration | Entity class body | `company_id = TextField()` |
| 2 | EntityDescriptor metadata | `core/entity_registry.py` | `custom_fields=["company_id", ...]` in descriptor tuple |
| 3 | Schema column definition | `dataframes/schemas/` | `ColumnDef("cf__company_id", pl.Utf8)` |
| 4 | Extractor field mapping | `dataframes/extractors/` | `self._extract_custom_field("company_id")` |

Representations 2-4 are auto-derived from representation 1 via the descriptor registration system (ADR-0081, ADR-0082). However, the auto-derivation chain has manual intervention points where inconsistency can enter.

### Where Auto-Derivation Works

- Descriptor `__set_name__` registers field -> EntityDescriptor gets it via `_pending_fields`
- EntityDescriptor `schema_module_path` resolves to the correct schema
- EntityDescriptor `extractor_class_path` resolves to the correct extractor

### Where It Does Not

- Column names in schema definitions use the `cf__` prefix convention but are defined manually in schema files
- Extractor field access uses `self._extract_custom_field()` with a string name that must match the descriptor name

A rename of a custom field descriptor requires updates in the schema file and extractor, not just the entity class.

---

## 5. Holder Pattern: Essential Core with Accidental Overhead

### The Essential Part

Asana's task hierarchy requires "holder" intermediary tasks to contain children. A Unit does not directly contain Offers -- it contains an OfferHolder task, which contains Offer tasks. This is a genuine Asana API constraint that the holder pattern faithfully models.

```
Unit Task (Asana)
    |
    +-- Offer Holder Task (Asana container)
    |     +-- Offer Task 1
    |     +-- Offer Task 2
    |
    +-- Process Holder Task (Asana container)
          +-- Process Task 1
```

The `HolderFactory` pattern (3-5 lines per holder) is proportionate to this essential complexity.

### The Accidental Overhead

The overhead emerges from holder management:

1. **ensure_holders** phase in SaveSession -- before creating child entities, holders must exist
2. **HolderMixin** on every holder class -- shared behavior for child management
3. **Holder detection** -- Tiers 1-4 must detect holder types separately from leaf types
4. **Holder caching** -- 9 holder types with their own TTLs and cache entries
5. **Holder hydration** -- `hydration.py` maps each holder type separately

These 5 concerns exist because of the Asana API's intermediary pattern, not because of the SDK's design choice. The overhead is accidental in the sense that it would not exist if Asana used direct parent-child relationships.

---

## 6. Anti-Pattern Surface

### Parallel Hierarchy

**Pattern**: Two class hierarchies that mirror each other and must be kept in sync.

**Evidence**:
- `automation/pipeline.py` and `lifecycle/creation.py` -- parallel creation pipelines (addressed in WS6 via shared creation helpers)
- `automation/seeding.py` (`FieldSeeder`) and `lifecycle/seeding.py` (`AutoCascadeSeeder`) -- parallel seeding strategies

**Status**: Partially addressed. WS6 extracted shared helpers to `core/creation.py`. Seeding strategies intentionally diverge (explicit vs zero-config).

### Shotgun Surgery Risk

**Pattern**: A single conceptual change requires edits in many scattered files.

**Evidence**:
- Adding a new entity type requires changes in: `detection/types.py` (EntityType enum), `core/entity_registry.py` (EntityDescriptor), `models/business/` (entity class), `_bootstrap.py` (registration), `dataframes/schemas/` (schema), `dataframes/extractors/` (extractor), `activity.py` (section classifier if applicable)
- Adding a new section requires: `activity.py` (classifier mapping), potentially `sections.py` (enum), potentially API route configuration

**Mitigation**: The descriptor system and EntityRegistry SSoT reduce the surface. Schema and extractor resolution is descriptor-driven. But new entity types still require 4-7 file changes.

### Feature Envy

**Pattern**: A class that uses another class's internals more than its own.

**Evidence**:
- `lifecycle/seeding.py` imports functions from `automation/seeding.py` (resolved in WS6 by promoting to public API)
- `persistence/session.py` constructs action objects that know details about Asana API payloads

**Status**: Low severity. Most inter-module access goes through public APIs.

### God Module

**Pattern**: A single module with too many responsibilities.

**Evidence**:
- `clients/data/client.py` (2,165 lines, 49 methods) -- DataServiceClient mixes HTTP transport, retry logic, circuit breaker, caching, PII redaction, metrics, response parsing, 5 API endpoints
- `persistence/session.py` (1,853 lines, 58 methods) -- SaveSession mixes entity tracking, dirty detection, dependency ordering, CRUD, cascade, healing, automation, event hooks, action builders, cache invalidation

**Status**: Identified in WS4 smell report as CX-001 and CX-002. Deferred to WS8.

---

## 7. Boundary Tension Points

### DataFrame / Entity Boundary

The DataFrame subsystem builds analytical views from entity data, creating a boundary between the entity model (Pydantic v2, individual objects) and DataFrame layer (Polars, columnar analytics).

**Tension**: DataFrames need to access entity custom fields, which are defined via descriptors on Pydantic models. The extraction path (`Extractor.extract()`) must flatten Pydantic model data into Polars-compatible columns. This flattening loses the type safety of the Pydantic model.

**Evidence**: Extractors use string-based field access (`self._extract_custom_field("company_id")`) rather than typed descriptor access. A descriptor rename is not caught at compile time in the extractor.

### Query / Multi-Subsystem Boundary

The query engine bridges DataFrames, caching, schema validation, and section scoping.

**Tension**: `QueryEngine` imports from `dataframes.models.registry`, `query.compiler`, `query.guards`, `query.hierarchy`, `query.join`, `query.models`, and `services.query_service`. It is a composition root that touches 7 modules.

**Evidence**: `query/engine.py` has 11 import statements from 7 different packages. Adding a new query capability requires understanding the interaction between all 7.

### Detection / Registry Dual Registration

Entity detection depends on the EntityRegistry, and the EntityRegistry depends on entity class definitions that are registered at import time via `_bootstrap.py`.

**Tension**: Detection cannot run until registration completes, but registration is triggered by importing `models.business`. If detection code is imported before `models.business`, it sees an empty registry.

**Evidence**: `detection/tier1.py:105` explicitly calls `register_all_models()` as a guard. This is a defensive workaround for the import-time registration dependency.

---

## 8. Essential vs. Accidental Complexity Verdicts

| Domain | Complexity | Verdict | Rationale |
|--------|-----------|---------|-----------|
| Entity type hierarchy (17 types) | Essential | Proportionate | Asana's task model genuinely has this many entity types |
| 5-tier detection | Essential | Proportionate | Ambiguity is genuine; 5 strategies for 4 certainty levels |
| Holder intermediaries (9 holders) | Essential | Proportionate | Asana API requires container tasks |
| Descriptor system | Essential | Proportionate | ~800 lines boilerplate -> ~400 lines infrastructure |
| Two-tier entity cache | Essential | Proportionate | API rate limits + cold start resilience |
| DataFrame subsystem | Essential | Proportionate | Analytical queries over entity data |
| Query predicate AST | Essential | Proportionate | Composable queries with type safety |
| SaveSession 6-phase UoW | Essential | Proportionate | Non-transactional API requires orchestration |
| Triple registry | Accidental | Over-complex | Should be derivable from single source |
| 47 hardcoded section names | Accidental | Brittle | Should be configuration or dynamic discovery |
| Two separate cache systems | Accidental | Over-complex | Could share more infrastructure |
| 31 caching concepts | Accidental | Over-complex | Conceptual density exceeds domain requirements |
| Import-time side effects | Accidental | Fragile | Registration should be explicit |
| 85-export barrel | Accidental | Maintenance burden | Package should be split or exports reduced |
| Parallel creation pipelines | Accidental | Duplication | Addressed in WS6 but seeding still diverges |
| Async/sync duality | Mixed | Inherent but costly | Dual consumer requirement, but 88 sync bridges is high |

### Ratio Estimate

**Essential complexity**: ~70% of total system complexity
**Accidental complexity**: ~30% of total system complexity

The 70/30 ratio indicates a codebase that is fundamentally well-architected for its problem domain but has accumulated structural debt in configuration management, import architecture, and caching abstractions.

---

## 9. SPOF Register

Single Points of Failure -- components whose failure would cascade to multiple subsystems.

| SPOF | What Depends On It | Failure Mode | Mitigation |
|------|-------------------|-------------|------------|
| `ProjectTypeRegistry` population | All entity resolution via `services/resolver.py` | If not populated: all entity queries return Unknown | Config-driven; fails at startup if config missing |
| `EntityRegistry` validation | Detection, schema resolution, caching, DataFrame extraction | If validation fails: import-time error, app does not start | Fail-fast at import; checked by integrity tests |
| `SchemaRegistry` lazy init | All DataFrame operations (builders, extractors, queries) | If init fails: DataFrame queries return errors | Lazy with retry; first-access failure is visible |
| `register_all_models()` | All entity class instantiation | If not called: entity classes lack registered metadata | Idempotency guard; called at import time and in detection |
| Redis connection | All hot-tier cache reads | If down: fall back to S3 cold tier or API direct | Graceful degradation via TieredCacheProvider |
| S3 access | Cold tier, DataFrame persistence, watermarks | If down: hot tier only, no cold-start resilience | Circuit breaker + graceful degradation |
| Asana API | All data fetching | If rate-limited or down: stale cache data served | 4:2 servable ratio ensures data availability from cache |

---

## 10. Risk Register

| Risk | Severity | Likelihood | Leverage | Description |
|------|----------|-----------|----------|-------------|
| Triple registry divergence | HIGH | MEDIUM | HIGH | New entity type added to one registry but not others; silent misclassification |
| Cache invalidation gap | HIGH | HIGH | MEDIUM | External Asana mutations invisible; stale data served for up to TTL window |
| Section name drift | MEDIUM | MEDIUM | HIGH | New Asana section added; not in hardcoded classifier; entities unclassified |
| Import-time failure cascade | HIGH | LOW | MEDIUM | Circular import or registration failure prevents app startup |
| DataServiceClient outage | HIGH | LOW | LOW | God object; failure in one endpoint method could affect others via shared state |
| SaveSession phase ordering | HIGH | LOW | LOW | Bug in phase ordering could cause data inconsistency (holders before children) |
| Singleton reset in tests | LOW | MEDIUM | LOW | Reset order sensitivity causes flaky tests |
| Schema/extractor drift | MEDIUM | LOW | HIGH | Manual schema/extractor definitions drift from descriptor declarations |
| CircuitBreaker thread safety | MEDIUM | LOW | MEDIUM | Per-project circuit breakers use state that may race under concurrent access |
| Lambda timeout mid-operation | MEDIUM | MEDIUM | HIGH | Cache warming interrupted; checkpoint-resume mitigates but partial state possible |

### Risk Legend

- **Severity**: Impact if the risk materializes (HIGH/MEDIUM/LOW)
- **Likelihood**: Probability of occurrence (HIGH/MEDIUM/LOW)
- **Leverage**: How much architectural improvement would reduce the risk (HIGH = high leverage for remediation, LOW = inherent risk)
