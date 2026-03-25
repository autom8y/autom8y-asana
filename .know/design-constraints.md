---
domain: design-constraints
generated_at: "2026-03-25T01:56:07Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "c6bcef6"
confidence: 0.91
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Design Constraints

## Tension Catalog

### TENSION-001: Circular Import Web (~44 Deferred Import Sites, 6 Remaining Structural Cycles)

**Type**: Layering violation / under-engineering
**Location**: All packages; concentrated in `src/autom8_asana/client.py`, `src/autom8_asana/config.py`, `src/autom8_asana/services/resolver.py`, `src/autom8_asana/services/universal_strategy.py`, `src/autom8_asana/models/business/`
**Historical reason**: Organic growth from a monolithic Asana integration. Entity registry, models, services, and cache all cross-reference each other. `from __future__ import annotations` + `TYPE_CHECKING` guard was adopted retroactively. The `protocols/` package was extracted to break cycles, but 6 structural cycles remain.
**Evidence**: 44 `# noqa: E402` deferred module-level imports directly measured (Grep: "noqa.*E402"). Key sites: `src/autom8_asana/core/entity_registry.py:895`, `src/autom8_asana/models/business/business.py:781`, `src/autom8_asana/models/business/unit.py:483`. Additionally, ~50 "Import here to avoid circular import" inline deferred imports within function bodies.
**Ideal resolution**: Extract interface packages. Full resolution requires major package restructuring.
**Resolution cost**: HIGH (weeks). 6 structural cycles remain.

---

### TENSION-002: Dual Exception Hierarchies (AsanaError vs ServiceError)

**Type**: Naming mismatch / dual-system pattern
**Location**: `src/autom8_asana/exceptions.py` (AsanaError tree) and `src/autom8_asana/services/errors.py` (ServiceError tree, per ADR-SLE-003)
**Historical reason**: `AsanaError` was the original SDK exception hierarchy for HTTP API errors. `ServiceError` was added for business logic errors to decouple services from HTTP concerns.
**Ideal resolution**: Unify into a single hierarchy with clear domain/transport separation.
**Resolution cost**: MEDIUM. ~50 exception handler sites would need updating. Risk of breaking error mapping at API boundary.

---

### TENSION-003: SaveSession Coordinator Complexity (14 Collaborators)

**Type**: Over-engineering risk (perceived, not actual — Coordinator pattern)
**Location**: `src/autom8_asana/persistence/session.py` + 13 collaborator modules (per TDD-GAP-01, TDD-0011, TDD-GAP-05)
**Historical reason**: SaveSession orchestrates the full write pipeline: change tracking, action building, dependency graph ordering, execution, cache invalidation, healing, event emission. Each collaborator handles one concern.
**Ideal resolution**: This is explicitly documented as NOT a god object. Do NOT decompose.
**Resolution cost**: N/A — frozen by design decision per ADR-0035.

---

### TENSION-004: Legacy Query Endpoint (Deprecated, Sunset 2026-06-01)

**Type**: Dual-system pattern
**Location**: `src/autom8_asana/api/routes/query.py` — `POST /v1/query/{entity_type}` (deprecated) vs `POST /v1/query/{entity_type}/rows` (current)
**Historical reason**: v1 query endpoint used flat equality filtering. v2 introduced composable predicates. Legacy retained for backward compatibility with existing consumers.
**Ideal resolution**: Remove legacy endpoint after sunset date. GATE: CloudWatch query on `deprecated_query_endpoint_used` metric (30 days of zero usage).
**Resolution cost**: LOW after gate passes. D-002/U-004 in debt ledger.

---

### TENSION-005: Legacy Preload Fallback (ADR-011) with 12 Bare-Except Sites

**Type**: Dual-system pattern / resilience + unguarded exception handling
**Location**: `src/autom8_asana/api/preload/legacy.py` (activated at `progressive.py:328-340` on progressive failure). Also `src/autom8_asana/api/lifespan.py` and `src/autom8_asana/api/preload/progressive.py`.
**Historical reason**: Progressive preload is the primary path, but legacy preload remains as a degraded-mode fallback. ADR-011 documents this as an intentional resilience pattern. The 12 bare-except sites were preserved from `main.py` during decomposition (TDD-I5) and tagged for narrowing in I6 (Exception Narrowing). I6 has NOT been executed.
**Ideal resolution**: Remove legacy preload when progressive is proven stable. Narrow the 12 bare-except sites as part of I6 initiative.
**Resolution cost**: LOW technically for preload removal, HIGH risk. I6 exception narrowing: LOW per site, MEDIUM total.

---

### TENSION-006: Cache Divergence (12/14 Dimensions Intentional)

**Type**: Perceived duplication (actually intentional design per ADR-0067)
**Location**: `src/autom8_asana/cache/backends/memory.py`, `src/autom8_asana/cache/backends/s3.py`, `src/autom8_asana/cache/backends/redis.py`
**Historical reason**: Memory, S3, and Redis backends have intentionally different behavior (TTL, eviction, serialization). ADR-0067 explicitly states this is by design.
**Resolution cost**: N/A — frozen.

---

### TENSION-007: Pipeline vs Lifecycle Dual Paths (CLOSED)

**Type**: Dual-system pattern (closed)
**Location**: `src/autom8_asana/automation/pipeline.py` vs `src/autom8_asana/lifecycle/` (engine, config, wiring, sections, reopen)
**Historical reason**: Lifecycle engine absorbed most PipelineConversionRule behavior. D-022 CLOSED — WS6 extracted sufficient shared surface.
**Resolution cost**: N/A — closed as designed.

---

### TENSION-008: os.environ Direct Access (28+ Sites)

**Type**: Under-engineering
**Location**: Scattered: `src/autom8_asana/config.py`, `src/autom8_asana/settings.py`, `src/autom8_asana/api/routes/health.py`, `src/autom8_asana/api/routes/admin.py`, `src/autom8_asana/api/preload/progressive.py`, `src/autom8_asana/automation/events/config.py`, `src/autom8_asana/auth/service_token.py`, `src/autom8_asana/entrypoint.py`, `src/autom8_asana/services/gid_push.py`, `src/autom8_asana/dataframes/offline.py`, and others.
**Historical reason**: Direct `os.environ` access predates `pydantic-settings` adoption. The env var standardization (commit c9273d8, 2026-03-14) applied ADR-ENV-NAMING-CONVENTION for canonical `AUTOM8Y_DATA_*`, `ASANA_CW_*`, `ASANA_RUNTIME_*` names but did not sweep all os.environ sites.
**Resolution cost**: LOW per site, MEDIUM total. Deferred item D-011 — address opportunistically.

---

### TENSION-009: Heavy Mock Usage (~540 Sites)

**Type**: Test infrastructure debt (ACCEPT verdict)
**Location**: `tests/` directory, ~470 test files
**Historical reason**: WS-OVERMOCK initiative evaluated mocks, received ACCEPT verdict — 75-90% are appropriate boundary mocks.
**Resolution cost**: HIGH. D-027 deferred.

---

### TENSION-010: CascadingFieldDef allow_override Default

**Type**: API contract constraint (frozen)
**Location**: `src/autom8_asana/models/business/fields.py`, `CascadingFieldDef`
**Historical reason**: Per ADR-0054, `allow_override=False` is the DEFAULT. Parent value ALWAYS overwrites descendant value. Changing this default would silently break cascading field behavior across all entity types.
**Resolution cost**: N/A — frozen by design.

---

### TENSION-011: @async_method Descriptor Type System Friction (269 type:ignore Suppressions)

**Type**: Over-engineering risk / mypy strict incompatibility
**Location**: `src/autom8_asana/patterns/async_method.py`, and all 11 client files using `@async_method`
**Historical reason**: `@async_method` generates both `get_async()` and `get()` variants dynamically via `__set_name__`, eliminating code duplication (~65% reduction). mypy cannot track dynamic method injection — requiring `# type: ignore[arg-type, operator, misc]` at every call site.
**Ideal resolution**: Protocol stubs or a mypy plugin for AsyncMethodPair. No clean resolution under mypy strict mode.
**Resolution cost**: HIGH. Structural constraint of the descriptor pattern.

---

### TENSION-012: Lifecycle Config Forward-Compat Contract (D-LC-002)

**Type**: API contract constraint (frozen)
**Location**: `src/autom8_asana/lifecycle/config.py` — 11 Pydantic config models (`SelfLoopConfig`, `InitActionConfig`, `ValidationRuleConfig`, `ValidationConfig`, `CascadingSectionConfig`, `TransitionConfig`, `SeedingConfig`, `AssigneeConfig`, `StageConfig`, `WiringRuleConfig`, `LifecycleConfigModel`)
**Historical reason**: Lifecycle YAML files may evolve ahead of code. New fields added to YAML configs by config authors before Pydantic models are updated must not break older code. These 11 models MUST use `extra="ignore"` (not `extra="forbid"`). Surfaced when SM-003 attempted to add `extra="forbid"` — immediately reverted (commit 5a24194).
**Ideal resolution**: N/A — intentional forward-compat contract.
**Resolution cost**: N/A — frozen by design. Constraint is named D-LC-002.

---

### TENSION-013: Triple Registry Duplication for Entity-Project Mapping

**Type**: Naming mismatch / over-engineering / layering violation
**Location**:
- `src/autom8_asana/core/entity_registry.py` — `EntityRegistry` / `ENTITY_DESCRIPTORS` (canonical metadata)
- `src/autom8_asana/core/project_registry.py` — `ProjectRegistry` (logical-name → GID constants)
- `src/autom8_asana/models/business/registry.py` — `ProjectTypeRegistry` (runtime GID → EntityType lookup)
- `src/autom8_asana/services/resolver.py` — `EntityProjectRegistry` (discovery-time GID → entity config)
**Historical reason**: `ProjectTypeRegistry` pre-dates `EntityRegistry`. `EntityProjectRegistry` was added for API startup discovery. `project_registry.py` was added for lifecycle YAML resolution. All four encode entity-to-project-GID mappings in different forms.
**Evidence**: `src/autom8_asana/core/registry_validation.py` was written specifically to cross-validate the three independent registries at startup (per QW-4, ARCH-REVIEW-1 Section 3.1). The migration comment in `src/autom8_asana/core/project_registry.py:7` reads: "Entity classes retain their own PRIMARY_PROJECT_GID for now. Parity tests verify that entity class values match registry values. Future sprints will migrate entity classes to reference the registry directly." This migration has not been executed.
**Ideal resolution**: Collapse ProjectTypeRegistry and EntityProjectRegistry into facades over EntityRegistry.
**Resolution cost**: HIGH. Cross-registry validation at startup is a workaround for this gap.

---

### TENSION-014: Frozen Dataclass Mutation via object.__setattr__ (Load-Bearing Pattern)

**Type**: Load-bearing jank (anti-pattern that cannot be removed)
**Location**: `src/autom8_asana/core/entity_registry.py:674-710` (`_bind_entity_types`), `src/autom8_asana/persistence/holder_construction.py:166-191`, `src/autom8_asana/persistence/action_executor.py:421`, `src/autom8_asana/persistence/pipeline.py:240`, `src/autom8_asana/services/resolution_result.py:72-74`, `src/autom8_asana/config.py:491-525`
**Historical reason**: `EntityDescriptor` is frozen to enable hashability and thread safety, but `entity_type` cannot be set at declaration time (circular import: `core.types` cannot be imported at `entity_registry` definition). `_bind_entity_types()` uses `object.__setattr__` to mutate after-the-fact. Similar pattern exists in persistence to patch GIDs onto newly-created entities.
**Pattern**: 32 `object.__setattr__` call sites across src (Grep: "object\.__setattr__"). Per ADR-001: "Safe because this runs exactly once before any consumer reads the descriptors."
**Ideal resolution**: Breaking the circular import would allow normal `entity_type` assignment. Requires moving `EntityType` to a leaf module with no dependencies.
**Resolution cost**: MEDIUM. Core plumbing change that touches 17 entity bindings.

---

### TENSION-015: reconciliation_holder vs RECONCILIATIONS_HOLDER Naming Mismatch

**Type**: Naming mismatch
**Location**:
- `src/autom8_asana/core/entity_registry.py:590` — descriptor name: `"reconciliation_holder"` (singular)
- `src/autom8_asana/core/types.py:38` — `EntityType.RECONCILIATIONS_HOLDER` (plural)
- `src/autom8_asana/core/entity_registry.py:699` — binding: `"reconciliation_holder": EntityType.RECONCILIATIONS_HOLDER`
**Historical reason**: The descriptor was named with consistent singular pattern (`contact_holder`, `unit_holder`). The EntityType enum used plural (`RECONCILIATIONS_HOLDER`) matching the Asana project name "Reconciliations". Divergence was never resolved.
**Evidence**: No test guards this naming pair. It compiles because `_bind_entity_types()` uses a hardcoded `_TYPE_MAP` dict.
**Ideal resolution**: Rename `EntityType.RECONCILIATIONS_HOLDER` to `EntityType.RECONCILIATION_HOLDER` (singular) for consistency.
**Resolution cost**: LOW (rename + sed). Risk: any code using the old enum name breaks at runtime (not compile time for string-based references).

---

### TENSION-016: Hardcoded Custom Field Resolver Allowlist

**Type**: Under-engineering / naming mismatch
**Location**: `src/autom8_asana/services/universal_strategy.py:935`
**Pattern**: `if self.entity_type in ("unit", "business", "offer"):` — three entity types are hardcoded to receive `DefaultCustomFieldResolver`. All other entity types receive `None`.
**Historical reason**: Custom field resolution was implemented for the original three entities. When `asset_edit`, `contact`, and holder entities were added, the allowlist was never updated via the `EntityDescriptor`.
**Evidence**: `EntityDescriptor` has a `cascading_field_provider` flag for descriptor-driven behavior, but no equivalent `uses_custom_field_resolver` flag. The allowlist is undocumented.
**Ideal resolution**: Add `custom_field_resolver_class_path` to `EntityDescriptor`, or a boolean flag. Drive resolver lookup from the registry, not a hardcoded list.
**Resolution cost**: LOW (additive descriptor field + allowlist expansion).

---

## Trade-off Documentation

| Tension | Current State | Ideal State | Why Current Persists |
|---------|--------------|-------------|---------------------|
| TENSION-001 | 44 E402 sites, ~50 deferred function imports, 6 cycles | Clean dependency graph | Cost too high; deeply coupled packages |
| TENSION-002 | Two exception trees | Unified hierarchy | Breaking 50+ handler sites; both trees work |
| TENSION-003 | 14-collaborator Coordinator | Same (by design) | Decomposition increases coupling |
| TENSION-004 | Dual query endpoints | Single modern endpoint | Waiting for sunset gate (CloudWatch metric) |
| TENSION-005 | Dual preload paths + 12 bare-except sites | Progressive only + narrowed exceptions | Safety net needed; I6 initiative not started |
| TENSION-006 | 12/14 cache dimensions differ | Same (by design) | ADR-0067 explicitly documents as intentional |
| TENSION-007 | Pipeline + Lifecycle | Lifecycle only | Essential pipeline differences remain (CLOSED) |
| TENSION-008 | os.environ scattered (28+) | Centralized settings | Low priority, D-011 |
| TENSION-009 | 540 mock sites | Fewer mocks, more fakes | WS-OVERMOCK ACCEPT verdict; appropriate |
| TENSION-010 | allow_override=False default | Same (by design) | Data integrity constraint per ADR-0054 |
| TENSION-011 | 269 type:ignore suppressions | Protocol stubs / mypy plugin | Structural constraint of descriptor pattern |
| TENSION-012 | 11 lifecycle models must be extra="ignore" | Same (by design) | D-LC-002 forward-compat contract |
| TENSION-013 | 4 registries encoding entity-GID mapping | Collapsed to 1 | ProjectTypeRegistry and EntityProjectRegistry predate EntityRegistry; migration not executed |
| TENSION-014 | object.__setattr__ on frozen dataclasses (32 sites) | Normal assignment | Circular import prevents frozen-safe initialization |
| TENSION-015 | reconciliation_holder vs RECONCILIATIONS_HOLDER naming mismatch | Consistent singular naming | Never renamed; works at runtime via hardcoded dict |
| TENSION-016 | Hardcoded allowlist for custom field resolver | Descriptor-driven | No EntityDescriptor field for resolver; added opportunistically |

### ADR Cross-References

- **ADR-0054**: Cascading field architecture (TENSION-010)
- **ADR-0067**: Cache divergence documentation (TENSION-006)
- **ADR-0035**: SaveSession Unit of Work pattern (TENSION-003)
- **ADR-011**: Legacy preload as active fallback (TENSION-005)
- **ADR-SLE-003**: Service layer exception hierarchy (TENSION-002)
- **ADR-0002**: Sync-in-async context fail-fast (informs TENSION-011)
- **ADR-ENV-NAMING-CONVENTION**: Env var standardization (informing TENSION-008 resolution progress)
- **D-LC-002**: Lifecycle config forward-compat contract (TENSION-012)
- **ADR-001**: Frozen dataclass mutation policy (TENSION-014)
- **ADR-S4-001**: Schema-extractor-row triad (informs TENSION-016)
- **QW-4 / ARCH-REVIEW-1 Section 3.1**: Triple-registry cross-validation (TENSION-013)

## Abstraction Gap Mapping

### Missing Abstractions

**GAP-001: Unified DataFrameProvider for All Consumers**
- The `DataFrameProvider` protocol exists (`src/autom8_asana/protocols/dataframe_provider.py`) and is used by `QueryEngine` (`src/autom8_asana/query/engine.py`). However, `EntityQueryService` still uses `UniversalResolutionStrategy._get_dataframe()` directly — not the protocol. This is documented in `src/autom8_asana/services/query_service.py:5-13` as intentional (bypassing the protocol gives access to the full cache lifecycle including build lock, coalescing, and circuit breaker).
- Files: `src/autom8_asana/protocols/dataframe_provider.py`, `src/autom8_asana/services/query_service.py`, `src/autom8_asana/services/universal_strategy.py`
- Impact: Adding a new DataFrame consumer with full cache lifecycle semantics requires understanding the private `_get_dataframe()` call chain, not just the protocol.

**GAP-002: Configuration Consolidation**
- Three config systems coexist: local dataclasses (`RateLimitConfig`, `RetryConfig`, `CircuitBreakerConfig` in `src/autom8_asana/config.py`), platform primitives (`PlatformRetryConfig`, `PlatformCircuitBreakerConfig` from autom8y-http), and pydantic-settings (`src/autom8_asana/settings.py`). `DataServiceClient` (`src/autom8_asana/clients/data/config.py`) has its own `CircuitBreakerConfig` with identical field structure (noted at line 168: "Shares field structure with autom8_asana.config.CircuitBreakerConfig"). Migration to platform primitives is in progress (TDD-PRIMITIVE-MIGRATION-001).
- Files: `src/autom8_asana/config.py`, `src/autom8_asana/clients/data/config.py`
- Impact: Configuration drift between old and new code paths.

**GAP-003: Custom Field Resolver Not Descriptor-Driven**
- `UniversalResolutionStrategy._get_custom_field_resolver()` (line 929-939 of `src/autom8_asana/services/universal_strategy.py`) uses a hardcoded `("unit", "business", "offer")` list. There is no corresponding field on `EntityDescriptor` to declare whether an entity needs custom field resolution. New entity types added to `ENTITY_DESCRIPTORS` must also be manually added to this list.
- Files: `src/autom8_asana/services/universal_strategy.py:935`, `src/autom8_asana/core/entity_registry.py`
- Impact: Silent omission — new entities will not receive custom field resolution without updating the allowlist.

### Premature Abstractions

None significant observed. The COMPAT-PURGE initiative (2026-02-25) removed most unnecessary abstractions. `src/autom8_asana/models/business/base.py` uses `extra="allow"` (intentional — supports dynamic attribute attachment via `_children_cache` and similar private patterns in holder types).

### Schema-Extractor-Row Triad Partial Wiring

Several entities have schemas without extractors. Per `src/autom8_asana/core/entity_registry.py:827-841`, this triggers a WARNING (`schema_without_extractor`) unless `strict_triad_validation=True` (which is `False` by default, per ADR-S4-001). Entities with partial wiring at time of audit:
- `business` — has `schema_module_path`, `cascading_field_provider=True`, but no `extractor_class_path` or `row_model_class_path`
- `offer` — has `schema_module_path`, but no `extractor_class_path` or `row_model_class_path`
- `asset_edit` — has `schema_module_path`, but no `extractor_class_path` or `row_model_class_path`
- `asset_edit_holder` — has `schema_module_path`, but no `extractor_class_path` or `row_model_class_path`

The `unit` and `contact` entities have full triads. `strict_triad_validation=False` is load-bearing while partial wiring persists.

## Load-Bearing Code Identification

### LB-001: EntityRegistry (Single Source of Truth)

**Location**: `src/autom8_asana/core/entity_registry.py`
**What it does**: Declares all entity metadata via `EntityDescriptor`. Four consumers are descriptor-driven: `SchemaRegistry._ensure_initialized()` (auto-discovers schemas via `schema_module_path`), extractor factory (`extractor_class_path`), `ENTITY_RELATIONSHIPS` (derived from `join_keys`), `_build_cascading_field_registry()` (via `cascading_field_provider` flag).
**Dependents**: `src/autom8_asana/dataframes/models/registry.py`, `src/autom8_asana/dataframes/extractors/`, `src/autom8_asana/core/types.py`, `src/autom8_asana/models/business/registry.py`, `src/autom8_asana/cache/models/entry.py`, `src/autom8_asana/config.py` (FACADE), `src/autom8_asana/services/universal_strategy.py` (FACADE)
**Naive fix risk**: Changing descriptor shape breaks all 4 descriptor-driven consumers plus backward-compat facades.
**Safe refactor**: Add new fields to `EntityDescriptor` (additive). Do NOT rename or remove existing fields. Note: `entity_registry.py:895` has a deferred `# noqa: E402` import to `system_context` — do not move to top-level.
**Hot path**: Every DataFrameCache warmup and every resolution call reads this registry.

### LB-002: SaveSession Pipeline

**Location**: `src/autom8_asana/persistence/session.py` + 13 collaborator modules
**What it does**: Orchestrates all Asana write operations — ENSURE_HOLDERS phase (TDD-GAP-01), action executor (TDD-0011), batch support (TDD-GAP-05).
**Dependents**: All API write routes, lifecycle engine, automation engine.
**Naive fix risk**: Decomposing SaveSession scatters orchestration. Reordering pipeline stages breaks commit semantics.
**Safe refactor**: Add new pipeline stages at defined extension points. Do NOT reorder existing stages. Adding holder auto-creation behavior requires understanding `auto_create_holders` flag semantics (session.py lines 150-169).

### LB-003: SystemContext.reset_all()

**Location**: `src/autom8_asana/core/system_context.py`
**What it does**: Resets all singletons for test isolation. 12+ files call `register_reset()` at module level.
**Dependents**: Every test (autouse fixture in `tests/conftest.py`).
**Naive fix risk**: Breaking reset ordering causes test pollution. Missing reset registration causes stale state between tests.
**Safe refactor**: New singletons must call `register_reset()` at module level. Do NOT change reset ordering.

### LB-004: _bootstrap_session() Fixture

**Location**: `tests/conftest.py`
**What it does**: Runs `bootstrap()` and `model_rebuild()` for all Pydantic models once per session.
**Dependents**: Every test that uses any Pydantic model with `NameGid`.
**Naive fix risk**: Missing a model from rebuild list causes `ValidationError` in unrelated tests.
**Safe refactor**: Add new models to the rebuild list. Do NOT remove existing entries.

### LB-005: @async_method Decorator (Descriptor Pattern)

**Location**: `src/autom8_asana/patterns/async_method.py`
**What it does**: Generates `{name}_async()` and `{name}()` pairs via `AsyncMethodPair.__set_name__`. Used by all 11 specialized client files in `src/autom8_asana/clients/`.
**Dependents**: All clients using `@async_method` with overloads and `# type: ignore[arg-type, operator, misc]` annotations.
**Naive fix risk**: Changing `__set_name__` injection logic silently breaks all method pairs. `SyncInAsyncContextError` raise behavior (ADR-0002 fail-fast) must not be weakened.
**Safe refactor**: Do NOT change `sync_name` or `async_name` derivation logic.

### LB-006: Lifecycle Config Models (D-LC-002)

**Location**: `src/autom8_asana/lifecycle/config.py` — 11 models
**What it does**: YAML-deserializable config for lifecycle rules. Must tolerate unknown fields.
**Dependents**: All lifecycle YAML config files (runtime-loaded).
**Naive fix risk**: Adding `extra="forbid"` to these models breaks forward-compatibility.
**Safe refactor**: These 11 models must NOT get `extra="forbid"`. All other models CAN.

### LB-007: _bind_entity_types() + object.__setattr__ Mutation (TENSION-014)

**Location**: `src/autom8_asana/core/entity_registry.py:678-710`
**What it does**: Mutates frozen `EntityDescriptor` instances after module load to inject `entity_type` values, bypassing the `frozen=True` constraint via `object.__setattr__`. This runs exactly once before any consumer reads the descriptors.
**Dependents**: All 17 entity descriptors in `ENTITY_DESCRIPTORS`. The binding is required for `registry.get_by_type()` to work.
**Naive fix risk**: Adding any code that reads `entity_type` before `_bind_entity_types()` completes will get `None`. Calling `_bind_entity_types()` a second time (outside of `_reset_entity_registry`) has no effect (idempotent by design — second call produces no error but also no change if types already set).
**Safe refactor**: The deferred binding is safe as-is. Resolution requires eliminating the circular import between `core.entity_registry` and `core.types`.

### LB-008: Cross-Registry Startup Validation

**Location**: `src/autom8_asana/core/registry_validation.py`
**What it does**: Validates consistency across `EntityRegistry`, `ProjectTypeRegistry`, and `EntityProjectRegistry` at startup. Called from both `api/lifespan.py` and Lambda handler bootstrap.
**Dependents**: All three registries. Failures here mean entity-to-project mapping is broken.
**Naive fix risk**: Disabling or skipping this validation removes the only guard against silent registry divergence (TENSION-013).
**Safe refactor**: Always call with `check_project_type_registry=True`. `check_entity_project_registry` can be `False` for Lambda bootstrap where EntityProjectRegistry is unpopulated.

## Evolution Constraint Documentation

### Changeability Ratings

| Area | Rating | Evidence |
|------|--------|---------|
| `src/autom8_asana/api/routes/` | **Safe** | Local changes only. New routes added without breaking existing. |
| `src/autom8_asana/query/` | **Safe** | Well-encapsulated via DataFrameProvider protocol. |
| `src/autom8_asana/metrics/` | **Safe** | Isolated subsystem with clear boundaries. |
| `src/autom8_asana/search/` | **Safe** | Isolated service, minimal dependents. |
| `src/autom8_asana/lambda_handlers/` | **Safe** | Entry points with no internal dependents. |
| `src/autom8_asana/observability/` | **Safe** | Decorator pattern, no cross-coupling. |
| `src/autom8_asana/services/` | **Coordinated** | Changes may affect routes and tests. Service errors mapped to HTTP. |
| `src/autom8_asana/dataframes/builders/` | **Coordinated** | Schema changes affect extractors and cache integration. Cascade validator is post-build. |
| `src/autom8_asana/cache/` | **Coordinated** | Multi-tier changes require testing Memory + S3 + Redis paths. Freshness enum consolidation in progress (4 legacy enums → 2 via `freshness_unified.py`). |
| `src/autom8_asana/lifecycle/` | **Coordinated** | Config-driven; changes require YAML config updates AND respect D-LC-002. |
| `src/autom8_asana/automation/` | **Coordinated** | Event transport uses boto3 via asyncio.to_thread; polling scheduler is APScheduler-based. |
| `src/autom8_asana/persistence/session.py` | **Migration** | 14 collaborators; changes require full pipeline testing. |
| `src/autom8_asana/core/entity_registry.py` | **Migration** | 4+ descriptor-driven consumers; additive changes only. Adding entity = 1 descriptor entry + schema file. |
| `src/autom8_asana/models/business/` | **Coordinated** | Detection (5 tiers), matching, cascading field logic tightly coupled. `_bootstrap.py` must stay synchronized with `EntityRegistry`. |
| `src/autom8_asana/lifecycle/config.py` | **Frozen** | D-LC-002 forward-compat contract. 11 models must keep `extra="ignore"`. |
| `src/autom8_asana/exceptions.py` | **Frozen** | Exception hierarchy consumed by all error handlers. Do not restructure. |
| `src/autom8_asana/protocols/` | **Frozen** | Interface contracts consumed by all DI boundaries. Additive only. |
| `src/autom8_asana/config.py` | **Coordinated** | Consumed by API, clients, services. Post-standardization: AUTOM8Y_DATA_*, ASANA_CW_*, ASANA_RUNTIME_* naming must be respected. |
| `src/autom8_asana/patterns/async_method.py` | **Frozen** | Method injection logic. Changing `__set_name__` breaks all 11 client method pairs. |
| `src/autom8_asana/core/project_registry.py` | **Migration** | Migration comment says entity classes should eventually reference registry directly; not yet executed. Changing GID values here without updating entity class `PRIMARY_PROJECT_GID` breaks parity tests. |

### Deprecated Markers and In-Progress Migrations

| Item | Status | Gate/Trigger |
|------|--------|-------------|
| `POST /v1/query/{entity_type}` (legacy) | Deprecated, sunset 2026-06-01 | CloudWatch metric: 30d zero usage |
| Legacy preload (`src/autom8_asana/api/preload/legacy.py`) | Active fallback (ADR-011) | Production incident in fallback path |
| 12 bare-except sites in preload/lifespan | Tagged for I6 narrowing | I6 initiative not started |
| `os.environ` direct access (28+ sites) | Opportunistic (D-011) | Address when touching the file |
| Heavy mock usage (540 sites) | ACCEPT verdict (D-027) | Dedicated test architecture initiative |
| `HOLDER_KEY_MAP` fallback matching | Active resilience | Per `src/autom8_asana/models/business/detection/facade.py:576` |
| `custom_field_accessor.py` strict=False | Intentional design | Dual-purpose API (not debt) |
| `AUTOM8_DATA_*` prefix in `run_smoke_test.py` | Stale (outside src) | Superseded by c9273d8; scripts not updated |
| Cache freshness enum consolidation | In progress | `freshness_unified.py` consolidates 4 → 2 enums; old locations maintain type aliases |
| `service/section_service.py` route wiring | Phase 3/4 deferred | Route handlers still directly implemented; service extraction done, wiring not |
| `ProjectTypeRegistry` → `EntityRegistry` migration | Stated intent | comment in `project_registry.py:7`; no sprint assigned |
| Partial schema-extractor-row triads (4 entities) | Unresolved warnings | `strict_triad_validation=False` preserves backward compat until all triads complete |

### External Dependency Constraints

- **Asana API rate limits**: Global rate limiter via SlowAPI + per-client adaptive semaphore (TDD-GAP-04/ADR-GAP04-001 AIMD control)
- **autom8y-data service**: DataServiceClient depends on data service API contract. Entity type mapping must match. Emergency kill switch: `AUTOM8Y_DATA_INSIGHTS_ENABLED`.
- **autom8y-auth SDK**: JWT validation and JWKS fetching encapsulated. Version `>=1.1.0` required for observability extras.
- **Polars DataFrame format**: Schema definitions must match Polars column types. Schema changes require migration.
- **S3 cache format**: Parquet files in S3. Format changes require cache invalidation and re-warming. `asyncio.to_thread()` wraps all boto3 calls (thread-safe S3 client per `src/autom8_asana/dataframes/storage.py`).
- **autom8y-telemetry**: `glass-S9: 0.6.0+` required for `trace_computation` decorator (per pyproject.toml comment).
- **Lambda context timeout**: `cache_warmer.py:162` notes that `context.get_remaining_time_in_millis()` returns `None` if context is `None` — no timeout enforcement in test/local mode.
- **Warm priority ordering constraint**: Cascade source entities must warm before cascade consumers (documented in `EntityRegistry.warmable_entities()` docstring). Current ordering: `business (1) → unit (2) → offer (3) → contact (4) → asset_edit (5) → asset_edit_holder (6)`. Violating this order reproduces SCAR-005/006 conditions.

## Risk Zone Mapping

### RISK-001: Silent Fallback in Detection Facade

**Location**: `src/autom8_asana/models/business/detection/facade.py:576-584`
**Missing guard**: Falls back to legacy `HOLDER_KEY_MAP` matching with logged warning and `detection_fallback_holder_key_map` log event but NO metric emission.
**Evidence**: Lines 580-584 call `log.warning("detection_fallback_holder_key_map", fallback="HOLDER_KEY_MAP")` — observable only in logs, not CloudWatch.
**Cross-ref**: TENSION-001 (circular imports prevent cleaner detection architecture).
**Recommended guard**: Add metric emission on fallback to track frequency.

### RISK-002: Cache Entry Type Inference for Legacy Data

**Location**: `src/autom8_asana/cache/models/entry.py:229-247`
**Missing guard**: Legacy serialized data without `_type` field infers type from content. Can fail silently.
**Evidence**: `# Base CacheEntry construction (legacy path)` comment at line 247. Comment at line 297: "Used for legacy data without `_type` or when no subclass is matched."
**Recommended guard**: Log warning with entry key when type inference is used (for migration tracking).

### RISK-003: Completeness UNKNOWN for Legacy Cache Entries

**Location**: `src/autom8_asana/cache/models/completeness.py:238-272`
**Missing guard**: `UNKNOWN = 0` treated conservatively (re-fetch for STANDARD/FULL). No alerting when UNKNOWN entries persist beyond expected migration window.
**Evidence**: `# UNKNOWN entries from legacy code need re-fetch` comment at line 272.
**Recommended guard**: Metric tracking UNKNOWN entry count per entity type.

### RISK-004: QueryEngine Predicate Depth Unlimited by Default

**Location**: `src/autom8_asana/query/guards.py`
**Missing guard**: Query complexity is bounded by `QueryLimits` but limits can be overridden. Deeply nested predicates could cause stack overflow or excessive computation.
**Recommended guard**: Hard ceiling on predicate depth regardless of limit configuration.

### RISK-005: Custom Field Accessor Non-Strict Mode (ACCEPTED)

**Location**: `src/autom8_asana/models/custom_field_accessor.py:384-387`
**Missing guard**: Non-strict mode returns input as-is, propagating invalid field names silently.
**Evidence**: `# Non-strict mode: return input as-is (legacy behavior)` comment.
**Status**: CLOSED in COMPAT-PURGE — intentional dual-purpose design. Agents should be aware of silent pass-through.

### RISK-006: Sync-in-Async Context Detection Gap in DataServiceClient

**Location**: `src/autom8_asana/clients/data/client.py`
**Missing guard**: The `_run_sync()` method checks for a running loop and raises `SyncInAsyncContextError` — correct. However, the sync `fetch_insights()` path uses `run_in_executor()` to a thread pool. If a caller passes an executor without a running loop (test context), the detection can pass but the thread-pool call may silently deadlock.
**Recommended guard**: Integration test covering sync call from thread-pool context.

### RISK-007: Lambda Handler Timeout Bypass When context=None

**Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:162`
**Missing guard**: `context.get_remaining_time_in_millis()` returns `None` when context is `None` (no Lambda context object — local/test mode). The timeout guard is disabled in this case.
**Evidence**: Line 162 comment: "Returns False if context is None (no timeout enforcement)."
**Recommended guard**: Integration test should verify timeout behavior with mock context object, not `None`.

### RISK-008: Bare-Except Sites in Preload/Lifespan (12 Known)

**Location**: `src/autom8_asana/api/preload/legacy.py` (12 sites), `src/autom8_asana/api/lifespan.py` (some), `src/autom8_asana/api/preload/progressive.py` (some)
**Missing guard**: Bare `except` catches all exceptions including `KeyboardInterrupt`, `SystemExit`, and programming errors, silently continuing. Tagged for I6 (Exception Narrowing) but I6 has not been executed.
**Evidence**: Module docstrings in all three files explicitly note: "Note: bare-except sites are preserved as-is from main.py. They are tagged for narrowing in I6 (Exception Narrowing)."
**Recommended guard**: Execute I6 initiative. Minimum: convert to `except Exception:` to exclude system signals.

### RISK-009: 4-Entity Partial Schema-Extractor-Row Triad

**Location**: `src/autom8_asana/core/entity_registry.py:828-850` (validation warnings); entities: `business`, `offer`, `asset_edit`, `asset_edit_holder`
**Missing guard**: `strict_triad_validation=False` (the production default) means these entities log a WARNING at startup but do not fail-fast. If an extractor is accidentally registered without a schema for these entities, it would pass check 6f (extractor without schema = ERROR) but the inverse (schema without extractor) is only a warning.
**Cross-ref**: ADR-S4-001.
**Recommended guard**: Advance `strict_triad_validation=True` as triads complete. Document current partial entities as explicitly accepted gaps.

## Knowledge Gaps

- The full static import graph was not regenerated from source. The deferred import count of 44 E402 sites is directly measured (Grep: `# noqa: E402`); the ~50 inline deferred imports within function bodies is an estimate.
- `automation/pipeline.py` vs `lifecycle/engine.py` specific behavioral differences were not traced in detail. The "essential pipeline differences" referenced in TENSION-007 are not enumerated.
- `src/autom8_asana/resolution/` package was not fully audited — it contains `strategies.py`, `selection.py`, `field_resolver.py`, `write_registry.py` which may have overlap with `services/universal_strategy.py`.
- Lambda handler full event-payload shape validation gaps in `cache_invalidate.py` and `workflow_handler.py` were not traced.
- The 269 `# type: ignore` count includes test files; production-only count was not isolated.
- Cache migration completeness for freshness enum consolidation (`freshness_unified.py` replacing 4 legacy enums) was not traced to completion.
- `services/section_service.py` and `services/task_service.py` both note route wiring as Phase 3/4 deferred work; neither the route handlers nor the service entry points were read in detail.
