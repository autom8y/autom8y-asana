---
domain: feat/entity-resolution
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/resolution/"
  - "./src/autom8_asana/api/routes/resolver.py"
  - "./src/autom8_asana/services/universal_strategy.py"
  - "./src/autom8_asana/services/resolution_result.py"
  - "./src/autom8_asana/services/resolver.py"
  - "./src/autom8_asana/services/dynamic_index.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# Entity Resolution

## Purpose and Design Rationale

Entity resolution is the feature by which autom8y-asana translates business
identifiers (phone number + vertical, offer_id, etc.) into Asana task GIDs.
Every cross-service operation — intake, reconciliation, automation — must resolve
a GID before acting on an entity. Without this translation layer, cross-service
callers would need to understand the Asana project/task graph directly.

**O(1) lookup via DynamicIndex** (TDD-DYNAMIC-RESOLVER-001 / FR-003): The primary
path skips live Asana API calls entirely. Polars DataFrames pre-warmed into memory at
startup are indexed into `DynamicIndex` instances keyed on criterion column tuples.
Each lookup is a dict key probe — `O(1)` regardless of project size.

**Schema-driven, entity-agnostic** (TDD-DYNAMIC-RESOLVER-001 / FR-005): A single
`UniversalResolutionStrategy` class replaces four per-entity strategies
(`UnitResolutionStrategy`, `BusinessResolutionStrategy`, `OfferResolutionStrategy`,
`ContactResolutionStrategy`). New entity types become resolvable automatically when
they have a `DataFrameSchema` in `SchemaRegistry` and a project in
`EntityProjectRegistry`.

**Two independent sub-systems** share the `resolution/` package name but serve
different callers:
- **Sub-system A (HTTP API)**: `POST /v1/resolve/{entity_type}` — S2S JWT only,
  fully DataFrame-backed, no live API calls at request time.
- **Sub-system B (programmatic)**: `ResolutionContext` — strategy chain for
  intra-process automation workflows that traverse the entity hierarchy via live
  API calls.

**Status-aware filtering** (TDD-STATUS-AWARE-RESOLUTION): `active_only=True`
(default) filters post-lookup GIDs to `AccountActivity.ACTIVE` and
`AccountActivity.ACTIVATING` via `SectionClassifier`. `total_match_count` preserves
the pre-filter count for diagnostic metadata (FR-11).

**Design decisions and rejected alternatives**:
- Per-entity strategy classes were retired (TDD-DYNAMIC-RESOLVER-001) — each
  required bespoke maintenance as new entity types were added. The unified strategy
  derives its behavior from `EntityDescriptor.key_columns` at startup.
- The `DynamicIndex` cache uses an LRU eviction policy (max 5 entries per entity
  type) with a configurable TTL (`ASANA_CACHE_TTL_DYNAMIC_INDEX`).
- `total_match_count` was added after callers reported confusion when
  `active_only=True` returned NOT_FOUND despite the entity existing in an inactive
  section (FR-11).
- ADR-0060 documented the decision to discover project GIDs at startup rather than
  per-request to avoid cold-path Asana API latency.

---

## Conceptual Model

### Two Sub-systems

**Sub-system A — HTTP API resolution** (`api/routes/resolver.py` + `services/universal_strategy.py`):

```
POST /v1/resolve/{entity_type}
  ↓ validate entity_type (EntityProjectRegistry + SchemaRegistry)
  ↓ normalize criteria (5-step alias chain: "phone" → "office_phone")
  ↓ group by key_column tuple
  ↓ DynamicIndexCache.get() or build from DataFrameCache (never triggers build on miss)
  ↓ O(1) DynamicIndex.lookup(criterion)
  ↓ SectionClassifier.classify(section) per GID → AccountActivity
  ↓ filter active_only → sort by ACTIVITY_PRIORITY
  ↓ ResolutionResult(gids, status_annotations, total_match_count)
```

**Sub-system B — programmatic resolution** (`resolution/context.py` + `resolution/strategies.py`):

```
async with ResolutionContext(client, trigger_entity=process) as ctx:
  entity = await ctx.business_async()
  # Internally dispatches: SessionCacheStrategy → NavigationRefStrategy
  #                      → DependencyShortcutStrategy → HierarchyTraversalStrategy
  # Budget ceiling: ApiBudget(max_calls=8)
```

### Key Terminology

| Term | Definition |
|------|------------|
| `DynamicIndex` | In-memory dict indexed on a frozen tuple of column values; O(1) lookup |
| `DynamicIndexCache` | LRU cache of `DynamicIndex` instances keyed by `(entity_type, key_columns)` |
| `DynamicIndexKey` | Versioned composite cache key: `"idx1:col1=val1:col2=val2"` |
| `UniversalResolutionStrategy` | Schema-driven strategy; single class for all entity types |
| `EntityProjectRegistry` | Singleton; maps `entity_type` → Asana project GID; populated at startup |
| `ResolutionResult` (services) | Frozen dataclass: `gids`, `match_count`, `status_annotations`, `total_match_count` |
| `ResolutionResult` (resolution/) | Different type: generic `ResolutionResult[T]` for strategy-chain results (entity object, not GIDs) |
| `ResolutionContext` | Session-scoped async context manager for strategy-chain resolution with API budget |
| `ApiBudget` | Call-count tracker with `max_calls=8` default; `consume()` raises `BudgetExhaustedError` |
| `AccountActivity` | StrEnum: `ACTIVE`, `ACTIVATING`, `INACTIVE`, `IGNORED` |
| `ACTIVITY_PRIORITY` | Canonical sort order: `(ACTIVE, ACTIVATING, INACTIVE, IGNORED)` |
| `SectionClassifier` | Maps Asana section names → `AccountActivity` values for an entity type |
| `EntityWriteRegistry` | Auto-discovers writable entity types by scanning model classes for `CustomFieldDescriptor` |
| `FieldResolver` | Stateless per-request class; resolves snake_case field names → Asana API payloads |
| `SelectionPredicate` | Abstract predicate for choosing among holder children (`FieldPredicate`, `CompoundPredicate`, `NewestActivePredicate`) |

### Resolution Status Lifecycle (Sub-system A)

```
criteria list
  → INVALID_CRITERIA (schema validation fail)
  → INDEX_UNAVAILABLE (DataFrame cache miss or build failure)
  → O(1) lookup
    ├─ empty gids → NOT_FOUND
    ├─ all inactive after filter → NOT_FOUND (total_match_count > 0)
    ├─ single gid → is_unique=True
    └─ multiple gids → is_ambiguous=True (all returned; caller handles)
```

### Strategy Chain Order (Sub-system B)

`DEFAULT_CHAIN`: SessionCacheStrategy → NavigationRefStrategy → DependencyShortcutStrategy → HierarchyTraversalStrategy

`BUSINESS_CHAIN` (when resolving a `Business`): SessionCacheStrategy → NavigationRefStrategy → HierarchyTraversalStrategy (skips `DependencyShortcutStrategy` — dependencies are entity-to-entity links, not hierarchy links)

### Inter-feature Relationships

**Consumes**:
- `dataframes/` — `DataFrameCache` provides Polars DataFrames; `DynamicIndex` built from them
- `dataframes/builders/cascade_validator.py` — `check_cascade_health()` gate (>20% null → 503)
- `models/business/activity.py` — `SectionClassifier`, `AccountActivity`, `ACTIVITY_PRIORITY`
- `core/entity_registry.py` — `EntityDescriptor.key_columns` drives schema-driven lookups
- `dataframes/models/registry.py` — `SchemaRegistry` for criterion validation and field enrichment

**Provides to**:
- `api/routes/resolver.py` — HTTP resolution endpoint
- `automation/` workflows — `ResolutionContext` for entity traversal
- `api/routes/intake_*.py` — intake pipeline uses `intake_resolve_service.py` (which wraps the strategy)
- `services/entity_write` path — `EntityWriteRegistry` + `FieldResolver` enable the entity-write API

---

## Implementation Map

### `resolution/` package — Sub-system B primitives (7 files)

| File | Purpose | Key Types |
|------|---------|-----------|
| `budget.py` | API call budget enforcement | `ApiBudget` (max_calls=8), `BudgetExhaustedError` |
| `context.py` | Session-scoped resolution manager | `ResolutionContext` (async ctx mgr, session cache, holder hydration), `ResolutionError` |
| `result.py` | Generic strategy result (entity object) | `ResolutionResult[T]` (frozen, `status`, `entity`, `api_calls_used`), `ResolutionStatus` StrEnum |
| `strategies.py` | Strategy chain ABC + 4 concrete strategies | `ResolutionStrategy` ABC, `SessionCacheStrategy`, `NavigationRefStrategy`, `DependencyShortcutStrategy`, `HierarchyTraversalStrategy`, `DEFAULT_CHAIN`, `BUSINESS_CHAIN` |
| `selection.py` | Entity selection within holder children | `SelectionPredicate` ABC, `FieldPredicate`, `CompoundPredicate`, `NewestActivePredicate`, `EntitySelector`, `ProcessSelector` |
| `write_registry.py` | Auto-discovers writable entity types at startup | `EntityWriteRegistry`, `WritableEntityInfo` (frozen, slots) |
| `field_resolver.py` | Resolves field names to Asana API payloads | `FieldResolver` (per-request, stateless), `ResolvedField` |

**Note**: `resolution/result.py` and `services/resolution_result.py` are DIFFERENT types with the SAME name. The former is a generic `ResolutionResult[T]` carrying an entity object (strategy-chain internal). The latter is an API-facing `ResolutionResult` carrying `gids` and `status_annotations`. This naming collision is a documented maintenance trap.

### `services/` layer — Sub-system A (3 files)

| File | Purpose | Key Types |
|------|---------|-----------|
| `universal_strategy.py` | Schema-driven O(1) batch resolution | `UniversalResolutionStrategy` (@dataclass), `get_universal_strategy()` factory, `get_shared_index_cache()`, `DYNAMIC_INDEX_CACHE_TTL`, `RESOLVE_MAX_CONCURRENT=10` |
| `resolution_result.py` | API-facing result (GIDs + status) | `ResolutionResult` (frozen, `gids`, `match_count`, `status_annotations`, `total_match_count`), factories: `not_found()`, `from_gids()`, `from_gids_with_status()`, `error_result()` |
| `resolver.py` | Registry + validation utilities | `EntityProjectRegistry`, `EntityProjectConfig`, `CriterionValidationResult`, `get_strategy()`, `validate_criterion_for_entity()`, `filter_result_fields()`, `get_resolvable_entities()` |
| `dynamic_index.py` | O(1) index data structure | `DynamicIndex`, `DynamicIndexCache` (LRU, max 5/entity, configurable TTL), `DynamicIndexKey` |

### Route: `api/routes/resolver.py`

- Auth: S2S JWT only (`s2s_router`). PAT path explicitly blocked.
- Endpoint: `POST /v1/resolve/{entity_type}` — wildcard route, MUST mount after
  `fleet_query_router` and `exports_router` (mount order constraint, architecture.md CRITICAL note).
- OTel-instrumented: spans on `resolver.entities.resolve` and `strategy.resolution.resolve`.
- Error tier taxonomy: Tier 1 (ServiceError) → `raise_service_error()`; Tier 2 (AsanaError) → re-raise to global handlers; Tier 3 (unexpected) → 500 RESOLUTION_ERROR.
- Includes `schema_router` sub-router for `GET /v1/resolve/{entity_type}/schema`.

### Request/Response Models: `api/routes/resolver_models.py`

`ResolutionRequest` (criteria list, optional `fields`, `active_only`), `ResolutionResponse` (results + meta), `ResolutionResultModel` (gid, gids, match_count, error, data, status, total_match_count), `ResolutionMeta` (resolved_count, unresolved_count, entity_type, project_gid, available_fields, criteria_schema).

**Note**: These models live in `api/routes/resolver_models.py` — a TENSION-002 violation pattern (services layer imports from api/routes).

### Data Flow (Sub-system A, happy path)

```
POST /v1/resolve/{entity_type}  [S2S JWT required]
  → get_supported_entity_types() [EntityProjectRegistry + SchemaRegistry discovery]
  → validate entity_type → 404 UNKNOWN_ENTITY_TYPE
  → EntityProjectRegistry.get_project_gid(entity_type) → 503 PROJECT_NOT_CONFIGURED
  → get_strategy(entity_type) → UniversalResolutionStrategy
  → strategy.validate_criterion() per criterion
  → strategy.resolve(criteria, project_gid, client, active_only)
    → Phase 1: validate + normalize + group by key_columns
    → Phase 2: gather_with_limit(max_concurrent=10)
      per group:
        → DynamicIndexCache.get() or _get_or_build_index()
        → _check_cascade_health() [>20% null → CascadeNotReadyError → 503]
        → DynamicIndex.lookup(criterion) [O(1)]
        → _classify_gids() [SectionClassifier per GID]
        → filter active_only + sort by ACTIVITY_PRIORITY
        → ResolutionResult.from_gids_with_status()
    → Phase 3: finalize list (null slot guard → RESOLUTION_NULL_SLOT)
  → ResolutionResultModel mapping (gid, gids, status, total_match_count)
  → ResolutionMeta (resolved_count, available_fields, criteria_schema)
```

### Test Coverage

| Test File | Scope | Test Count |
|-----------|-------|-----------|
| `tests/unit/resolution/test_budget.py` | ApiBudget | 9 |
| `tests/unit/resolution/test_result.py` | resolution/result.py | 9 |
| `tests/unit/resolution/test_selection.py` | SelectionPredicate, EntitySelector | 22 |
| `tests/unit/resolution/test_context.py` | ResolutionContext | 22 |
| `tests/unit/resolution/test_strategies.py` | Strategy chain | 14 |
| `tests/unit/resolution/test_write_registry.py` | EntityWriteRegistry | 9 |
| `tests/unit/resolution/test_field_resolver.py` | FieldResolver | 21 |
| `tests/unit/services/test_universal_strategy.py` | UniversalResolutionStrategy | 41 |
| `tests/unit/services/test_universal_strategy_status.py` | status-aware resolution | 26 |
| `tests/unit/services/test_universal_strategy_null_slot.py` | null slot guard | 3 |
| `tests/unit/services/test_universal_strategy_spans.py` | OTel spans | 5 |
| `tests/unit/services/test_resolution_result_status.py` | services/resolution_result | 13 |
| `tests/unit/api/test_routes_resolver.py` | HTTP route | 32 |
| `tests/unit/api/routes/test_resolver_spans.py` | route OTel spans | 6 |
| `tests/integration/test_entity_resolver_e2e.py` | E2E resolution | 8 |

---

## Boundaries and Failure Modes

### Hard Boundaries — What This Feature Does NOT Do

- **No PAT path**: `POST /v1/resolve/{entity_type}` requires S2S JWT; callers cannot use PAT tokens.
- **No on-demand DataFrame builds**: `_get_dataframe()` does NOT trigger a DataFrame build on cache miss. It returns `None`, yielding `INDEX_UNAVAILABLE`. DataFrame warm-up is a startup concern, not a request-time one.
- **No cascade health bypass**: If a cascade-sourced key column exceeds 20% null rate (`check_cascade_health()`), the endpoint returns 503 CascadeNotReadyError rather than serving degraded results.
- **No batch limit override**: `ResolutionRequest.criteria` is validated for a 1000-item maximum (implied by Pydantic model constraints).
- **No sub-system mixing**: The strategy chain (`DEFAULT_CHAIN` / `BUSINESS_CHAIN`) is for intra-process automation workflows only. HTTP API resolution does NOT use it.
- **No live Asana API calls on the HTTP path**: All resolution is DataFrame-backed.

### Failure Mode Catalog

| Failure | Result | HTTP Status |
|---------|--------|-------------|
| Discovery not complete | 503 DISCOVERY_INCOMPLETE | 503 |
| Project not configured | 503 PROJECT_NOT_CONFIGURED | 503 |
| Unknown entity type | 404 UNKNOWN_ENTITY_TYPE | 404 |
| Strategy not found | 501 STRATEGY_NOT_IMPLEMENTED | 501 |
| Missing required criterion field | 422 MISSING_REQUIRED_FIELD | 422 |
| Invalid field name in `fields` | 422 INVALID_FIELD | 422 |
| DataFrame cache miss on lookup | INDEX_UNAVAILABLE per-criterion | 200 (per-result error) |
| Index build failure | INDEX_UNAVAILABLE (group-level) | 200 (per-result error) |
| Cascade >20% null rate | CascadeNotReadyError → 503 | 503 |
| All matches filtered inactive | NOT_FOUND (total_match_count > 0) | 200 |
| Multi-match | All GIDs returned; caller handles | 200 |
| Null slot in results list | RESOLUTION_NULL_SLOT (defensive guard) | 200 |
| Per-criterion lookup exception | LOOKUP_ERROR (isolated, logged) | 200 |
| ServiceError from strategy | raise_service_error() | varies |

### Known SCARs Intersecting This Feature

| SCAR | Description | Relevance |
|------|-------------|-----------|
| SCAR-001 | Entity/holder class missing `PRIMARY_PROJECT_GID` — silent resolution collision | EntityWriteRegistry guards against this at discovery |
| SCAR-005 | CascadingFieldResolver 30% null rate on units — cascade warm-up ordering | `_check_cascade_health()` raises 503 if repeated; SCAR-005/006 refs in `_classify_gids()` for null-section handling |
| SCAR-006 | Cascade hierarchy warming gaps — parent GID not stored | Same cascade health gate mitigates |
| SCAR-020 | `PhoneNormalizer` wired only into matching engine, not read path — reconciliation blindness | E.164 phone normalization bypassed before DynamicIndex build; criterion misses E.164-normalized rows |

### Configuration Boundaries

| Setting | Effect | Invalid Values |
|---------|--------|----------------|
| `ASANA_CACHE_TTL_DYNAMIC_INDEX` | DynamicIndex cache TTL (default from settings) | 0 or negative would disable effective caching |
| `RESOLVE_MAX_CONCURRENT` | Max parallel group index builds (hardcoded=10) | Cannot be overridden via env |
| `ApiBudget.max_calls` | Sub-system B max API calls (default=8) | Callers can pass custom value to `ResolutionContext` |

### Interaction Points Where Boundaries Blur

- **`intake_resolve_service.py`** wraps `UniversalResolutionStrategy` for intake-specific resolution — shares the same DataFrame-backed path but adds intake-specific error handling and criterion pre-processing. Callers of the generic resolver should NOT assume intake behavior.
- **`EntityWriteRegistry`** lives in `resolution/write_registry.py` but serves the entity-write API route (`/v1/entity-write`), not the resolution route. Co-location is historical/organizational, not functional.
- **`FieldResolver`** is extracted from `automation/seeding.py` per ADR-EW-003 and serves the entity-write API path, not the resolve path.
- **TENSION-002 (layer boundary violation)**: `services/resolver.py` uses `api/routes/resolver_models.py` Pydantic models. Changes to resolver_models.py affect both the HTTP contract and the service internals.

---

```metadata
{
  "feature": "entity-resolution",
  "category": "Business Domain",
  "complexity": "HIGH",
  "confidence": 0.95,
  "sub_systems": 2,
  "source_files_read": 14,
  "test_functions_counted": 240,
  "known_naming_collision": "resolution/result.py vs services/resolution_result.py",
  "active_scars": ["SCAR-020"],
  "tdds_referenced": ["TDD-DYNAMIC-RESOLVER-001", "TDD-STATUS-AWARE-RESOLUTION", "TDD-FIELDS-ENRICHMENT-001", "TDD-entity-resolver"],
  "adrs_referenced": ["ADR-0060", "ADR-EW-002", "ADR-EW-003", "ADR-error-taxonomy-resolution"],
  "layer_tension": "TENSION-002 (services imports from api/routes)"
}
```
