---
domain: design-constraints
generated_at: "2026-02-27T11:21:29Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "73b6e61"
confidence: 0.8
format_version: "1.0"
---

# Codebase Design Constraints

## Tension Catalog Completeness

### TENSION-001: Circular Import Web (~915 Deferred Imports)

**Type**: Layering violation / under-engineering
**Location**: Across all packages; concentrated in `client.py`, `config.py`, `services/resolver.py`, `services/universal_strategy.py`
**Historical reason**: Organic growth from a monolithic Asana integration. Entity registry, models, services, and cache all cross-reference each other. The `from __future__ import annotations` + `TYPE_CHECKING` pattern was adopted retroactively.
**Ideal resolution**: Extract interface packages to break cycles (partially done with `protocols/`). Full resolution requires greenfield or major package restructuring.
**Resolution cost**: HIGH (weeks). 6 structural cycles remain (documented as SI-3). Prior initiative (REM-ASANA-ARCH) broke 6 of 13 bidirectional 2-cycles but declared remaining 7 as requiring major redesign.

---

### TENSION-002: Dual Exception Hierarchies (AsanaError vs ServiceError)

**Type**: Naming mismatch / dual-system pattern
**Location**: `src/autom8_asana/exceptions.py` (AsanaError tree) and `src/autom8_asana/services/errors.py` (ServiceError tree)
**Historical reason**: `AsanaError` was the original SDK exception hierarchy for HTTP API errors. `ServiceError` was added later for business logic errors to decouple services from HTTP concerns (per TDD-SERVICE-LAYER-001 / ADR-SLE-003).
**Ideal resolution**: Unify into a single hierarchy with clear domain/transport separation. ServiceError could extend AsanaError or both could extend a common base.
**Resolution cost**: MEDIUM. ~50 exception handler sites would need updating. Risk of breaking error mapping at API boundary.

---

### TENSION-003: SaveSession Coordinator Complexity (14 Collaborators)

**Type**: Over-engineering risk (perceived, not actual)
**Location**: `src/autom8_asana/persistence/session.py`
**Historical reason**: SaveSession orchestrates the full write pipeline: change tracking, action building, dependency graph ordering, execution, cache invalidation, healing, event emission. Each collaborator handles one concern.
**Ideal resolution**: This is explicitly documented as NOT a god object. It is a Coordinator pattern. Do NOT decompose.
**Resolution cost**: N/A -- frozen by design decision. Decomposition would scatter the orchestration logic and increase coupling.

---

### TENSION-004: Legacy Query Endpoint (Deprecated, Sunset 2026-06-01)

**Type**: Dual-system pattern
**Location**: `src/autom8_asana/api/routes/query.py` -- `POST /v1/query/{entity_type}` (legacy) vs `POST /v1/query/{entity_type}/rows` (current)
**Historical reason**: v1 query endpoint used flat equality filtering. v2 introduced composable predicates. Legacy retained for backward compatibility with existing consumers.
**Ideal resolution**: Remove legacy endpoint after sunset date. GATE: CloudWatch query on `deprecated_query_endpoint_used` metric (30 days of zero usage).
**Resolution cost**: LOW after gate passes. D-002/U-004 in debt ledger.

---

### TENSION-005: Legacy Preload Fallback (ADR-011)

**Type**: Dual-system pattern / resilience
**Location**: `src/autom8_asana/api/preload/legacy.py`
**Historical reason**: Progressive preload is the primary path, but legacy preload remains as a degraded-mode fallback for when progressive fails. This is documented in ADR-011 as an intentional resilience pattern.
**Ideal resolution**: Remove legacy preload when progressive is proven stable over extended period.
**Resolution cost**: LOW technically, but HIGH risk -- removing the fallback removes a safety net. Trigger: production incident in fallback path.

---

### TENSION-006: Cache Divergence (12/14 Dimensions Intentional)

**Type**: Perceived duplication (actually intentional design)
**Location**: Cache subsystem (`cache/backends/`, `cache/dataframe/`, `cache/integration/`)
**Historical reason**: Memory, S3, and Redis backends have intentionally different behavior (TTL, eviction, serialization). Documented in ADR-0067 as intentional divergence.
**Ideal resolution**: N/A -- ADR-0067 explicitly states this is by design. Do not "fix" the divergence.
**Resolution cost**: N/A -- frozen.

---

### TENSION-007: Pipeline vs Lifecycle Dual Paths

**Type**: Dual-system pattern
**Location**: `src/autom8_asana/automation/pipeline.py` (pipeline) vs `src/autom8_asana/lifecycle/` (lifecycle)
**Historical reason**: Lifecycle engine is the canonical path, absorbing most of `PipelineConversionRule` behavior. Pipeline is retained for essential differences that lifecycle does not cover.
**Ideal resolution**: D-022 (full pipeline consolidation) was CLOSED -- WS6 extracted sufficient shared surface. Remaining differences are legitimate.
**Resolution cost**: N/A -- closed as designed.

---

### TENSION-008: os.environ Direct Access (~20+ Sites)

**Type**: Under-engineering
**Location**: Scattered across `config.py`, `settings.py`, `api/config.py`, `query/__main__.py`, and others
**Historical reason**: Environment variable access was done directly via `os.environ` before `pydantic-settings` was adopted. Some sites remain from before the centralization effort.
**Ideal resolution**: Consolidate all `os.environ` access through `pydantic-settings` or the `autom8y-config` SDK.
**Resolution cost**: LOW per site, MEDIUM total. Deferred item D-011 -- address opportunistically.

---

### TENSION-009: Heavy Mock Usage (~540 Sites)

**Type**: Test infrastructure debt
**Location**: `tests/` directory, across 470 test files
**Historical reason**: Initial test development used boundary mocks (MagicMock, AsyncMock) extensively. The pattern was evaluated in WS-OVERMOCK initiative and received an ACCEPT verdict -- 75-90% are appropriate boundary mocks.
**Ideal resolution**: D-027 stays deferred. Dedicated test architecture initiative would be needed to replace mocks with fakes/stubs.
**Resolution cost**: HIGH. Trigger: dedicated test architecture initiative.

---

### TENSION-010: CascadingFieldDef allow_override Default

**Type**: API contract constraint
**Location**: `src/autom8_asana/models/business/fields.py`, `CascadingFieldDef`
**Historical reason**: Per ADR-0054, `allow_override=False` is the DEFAULT. This means parent value ALWAYS overwrites descendant value. This was a deliberate design choice for data integrity.
**Ideal resolution**: N/A -- this is a critical design constraint. Changing the default would silently break cascading field behavior across all entity types.
**Resolution cost**: N/A -- frozen by design.

## Trade-off Documentation

| Tension | Current State | Ideal State | Why Current Persists |
|---------|--------------|-------------|---------------------|
| TENSION-001 | 915 deferred imports, 6 cycles | Clean dependency graph | Cost too high; cycles in deeply coupled packages |
| TENSION-002 | Two exception trees | Unified hierarchy | Breaking 50+ handler sites; both trees work |
| TENSION-003 | 14-collaborator Coordinator | Same (by design) | Decomposition increases coupling |
| TENSION-004 | Dual query endpoints | Single modern endpoint | Waiting for sunset gate (CloudWatch metric) |
| TENSION-005 | Dual preload paths | Progressive only | Safety net for production resilience |
| TENSION-006 | 12/14 cache dimensions differ | Same (by design) | ADR-0067 explicitly documents as intentional |
| TENSION-007 | Pipeline + Lifecycle | Lifecycle only | Essential pipeline differences remain |
| TENSION-008 | os.environ scattered | Centralized settings | Low priority, address opportunistically |
| TENSION-009 | 540 mock sites | Fewer mocks, more fakes | WS-OVERMOCK ACCEPT verdict; appropriate |
| TENSION-010 | allow_override=False default | Same (by design) | Data integrity constraint per ADR-0054 |

### ADR Cross-References

- **ADR-0054**: Cascading field architecture (TENSION-010)
- **ADR-0067**: Cache divergence documentation (TENSION-006)
- **ADR-0035**: SaveSession Unit of Work pattern (TENSION-003)
- **ADR-011**: Legacy preload as active fallback (TENSION-005)
- **ADR-SLE-003**: Service layer exception hierarchy (TENSION-002)

## Abstraction Gap Mapping

### Missing Abstractions

**GAP-001: Unified DataFrameProvider for All Consumers**
- The `DataFrameProvider` protocol exists but is used only by `QueryEngine`. The `EntityQueryService` still uses `UniversalResolutionStrategy._get_dataframe()` directly.
- Files: `src/autom8_asana/protocols/dataframe_provider.py`, `src/autom8_asana/services/query_service.py`
- Impact: Adding a new DataFrame consumer requires knowledge of the cache access path.

**GAP-002: Configuration Consolidation**
- Three config systems coexist: local dataclasses (`RateLimitConfig`, `RetryConfig`), platform primitives (`PlatformRetryConfig`), and `pydantic-settings` (`settings.py`). New code uses platform primitives; old code uses local dataclasses.
- Files: `src/autom8_asana/config.py`, `src/autom8_asana/settings.py`
- Impact: Configuration drift between old and new code paths.

### Premature Abstractions

**None significant observed**. The COMPAT-PURGE initiative (2026-02-25) removed most unnecessary abstractions: `ProgressiveBuildResult`, `ProcessType.GENERIC`, `_StubReopenService`, `Freshness` alias module, and others.

## Load-Bearing Code Identification

### LB-001: EntityRegistry (Single Source of Truth)

**Location**: `src/autom8_asana/core/entity_registry.py`
**What it does**: Declares all entity metadata via `EntityDescriptor`. Four consumers are descriptor-driven.
**Dependents**: `SchemaRegistry`, extractor factory, `ENTITY_RELATIONSHIPS`, cascading field registry, `entity_types.py`, `project_registry.py`, `ENTITY_TYPES`, `DEFAULT_ENTITY_TTLS`
**Naive fix risk**: Changing descriptor shape breaks all 4 consumers plus backward-compat facades.
**Safe refactor**: Add new fields to `EntityDescriptor` (additive). Do NOT rename or remove existing fields.

### LB-002: SaveSession Pipeline

**Location**: `src/autom8_asana/persistence/session.py` + 13 collaborator modules
**What it does**: Orchestrates all Asana write operations.
**Dependents**: All API write routes, lifecycle engine, automation engine.
**Naive fix risk**: Decomposing SaveSession scatters orchestration. Reordering pipeline stages breaks commit semantics.
**Safe refactor**: Add new pipeline stages at defined extension points. Do NOT reorder existing stages.

### LB-003: SystemContext.reset_all()

**Location**: `src/autom8_asana/core/system_context.py`
**What it does**: Resets all singletons for test isolation.
**Dependents**: Every test (autouse fixture in `tests/conftest.py`).
**Naive fix risk**: Breaking reset ordering causes test pollution. Missing reset registration causes stale state.
**Safe refactor**: New singletons must call `register_reset()` at module level. Do NOT change reset ordering.

### LB-004: _bootstrap_session() Fixture

**Location**: `tests/conftest.py`
**What it does**: Runs `bootstrap()` and `model_rebuild()` for all Pydantic models once per session.
**Dependents**: Every test that uses any Pydantic model with `NameGid`.
**Naive fix risk**: Missing a model from rebuild list causes `ValidationError` in unrelated tests.
**Safe refactor**: Add new models to the rebuild list. Do NOT remove existing entries.

## Evolution Constraint Documentation

### Changeability Ratings

| Area | Rating | Evidence |
|------|--------|---------|
| `api/routes/` | **Safe** | Local changes only. New routes added without breaking existing. |
| `query/` | **Safe** | Well-encapsulated via DataFrameProvider protocol. |
| `metrics/` | **Safe** | Isolated subsystem with clear boundaries. |
| `search/` | **Safe** | Isolated service, minimal dependents. |
| `lambda_handlers/` | **Safe** | Entry points with no internal dependents. |
| `services/` | **Coordinated** | Changes may affect routes and tests. Service errors mapped to HTTP. |
| `dataframes/builders/` | **Coordinated** | Schema changes affect extractors and cache integration. |
| `cache/` | **Coordinated** | Multi-tier changes require testing Memory + S3 + Redis paths. |
| `lifecycle/` | **Coordinated** | Config-driven; changes require YAML config updates. |
| `persistence/session.py` | **Migration** | 14 collaborators; changes require full pipeline testing. |
| `core/entity_registry.py` | **Migration** | 4+ descriptor-driven consumers; additive changes only. |
| `models/business/` | **Coordinated** | Detection, matching, and cascading field logic tightly coupled. |
| `exceptions.py` | **Frozen** | Exception hierarchy consumed by all error handlers. Do not restructure. |
| `protocols/` | **Frozen** | Interface contracts consumed by all DI boundaries. Additive only. |
| `config.py` | **Coordinated** | Consumed by API, clients, services. Environment var changes are coordinated. |

### Deprecated Markers and In-Progress Migrations

| Item | Status | Gate/Trigger |
|------|--------|-------------|
| `POST /v1/query/{entity_type}` (legacy) | Deprecated, sunset 2026-06-01 | CloudWatch metric: 30d zero usage |
| Legacy preload (`api/preload/legacy.py`) | Active fallback (ADR-011) | Production incident in fallback path |
| `os.environ` direct access (20+ sites) | Opportunistic (D-011) | Address when touching the file |
| Heavy mock usage (540 sites) | ACCEPT verdict (D-027) | Dedicated test architecture initiative |
| HOLDER_KEY_MAP fallback matching | Active resilience | Per `models/business/detection/facade.py` |
| `custom_field_accessor.py` strict=False | Intentional design | Dual-purpose API (not debt) |

### External Dependency Constraints

- **Asana API rate limits**: Global rate limiter via SlowAPI + per-client adaptive semaphore
- **autom8y-data service**: DataServiceClient depends on data service API contract. Entity type mapping must match.
- **autom8y-auth SDK**: JWT validation and JWKS fetching encapsulated. Version constraints in pyproject.toml.
- **Polars DataFrame format**: Schema definitions must match Polars column types. Schema changes require migration.
- **S3 cache format**: Parquet files in S3. Format changes require cache invalidation and re-warming.

## Risk Zone Mapping

### RISK-001: Silent Fallback in Detection Facade

**Location**: `src/autom8_asana/models/business/detection/facade.py`, line ~576
**Missing guard**: Falls back to legacy `HOLDER_KEY_MAP` matching with logged warning but no metric emission.
**Evidence**: `# Fallback to legacy HOLDER_KEY_MAP matching` comment.
**Recommended guard**: Add metric emission on fallback to track how often legacy path is hit. Cross-ref: TENSION-001 (circular imports prevent cleaner detection architecture).

### RISK-002: Cache Entry Type Inference

**Location**: `src/autom8_asana/cache/models/entry.py`, line ~229
**Missing guard**: Legacy serialized data without `_type` field infers type from content, which can fail silently.
**Evidence**: `for legacy serialized data without _type` comment.
**Recommended guard**: Log warning with entry key when type inference is used (for migration tracking).

### RISK-003: Completeness UNKNOWN for Legacy Cache Entries

**Location**: `src/autom8_asana/cache/models/completeness.py`, line ~121
**Missing guard**: `UNKNOWN = 0` treated conservatively (re-fetch for STANDARD/FULL). But no alerting when UNKNOWN entries persist beyond expected migration window.
**Evidence**: `# UNKNOWN entries from legacy code need re-fetch` comment.
**Recommended guard**: Metric tracking UNKNOWN entry count per entity type.

### RISK-004: QueryEngine Predicate Depth Unlimited by Default

**Location**: `src/autom8_asana/query/guards.py`
**Missing guard**: Query complexity is bounded by `QueryLimits` but limits can be overridden. Deeply nested predicates could cause stack overflow or excessive computation.
**Recommended guard**: Hard ceiling on predicate depth regardless of limit configuration.

### RISK-005: Custom Field Accessor Non-Strict Mode

**Location**: `src/autom8_asana/models/custom_field_accessor.py`, line ~384
**Missing guard**: Non-strict mode returns input as-is, which can propagate invalid field names silently.
**Evidence**: `# Non-strict mode: return input as-is (legacy behavior)` comment.
**Recommended guard**: This is intentional dual-purpose design (documented as CLOSED in COMPAT-PURGE). No action needed, but agents should be aware of the silent pass-through.

## Knowledge Gaps

- The full import graph was not regenerated (the 915 deferred import count is from prior analysis).
- Detailed dependency counts per package for hub/leaf classification were not computed programmatically.
- The `automation/pipeline.py` vs `lifecycle/engine.py` specific behavioral differences were not traced in detail.
- RISK zones in `lambda_handlers/` were not audited.
