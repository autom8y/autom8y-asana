---
domain: design-constraints
generated_at: "2026-03-29T18:30:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "905fe4b"
confidence: 0.92
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "ccac1bdf21a076abac37f960cd0d2210bee78a023d780c7374cb6d5c087c9c5b"
---

# Codebase Design Constraints

## Tension Catalog

### TENSION-001: Circular Import Web (~44 Deferred Import Sites, 6 Remaining Structural Cycles)

**Type**: Layering violation / under-engineering
**Location**: All packages; concentrated in `src/autom8_asana/client.py`, `src/autom8_asana/config.py`, `src/autom8_asana/services/resolver.py`, `src/autom8_asana/services/universal_strategy.py`, `src/autom8_asana/models/business/`
**Historical reason**: Organic growth from a monolithic Asana integration. Entity registry, models, services, and cache all cross-reference each other. `from __future__ import annotations` + `TYPE_CHECKING` guard was adopted retroactively (502 TYPE_CHECKING occurrences across 250 files). The `protocols/` package was extracted to break cycles, but 6 structural cycles remain.
**Evidence**: 44 `# noqa: E402` deferred module-level imports directly measured. Key sites: `src/autom8_asana/core/entity_registry.py:895`, `src/autom8_asana/models/business/business.py:781`, `src/autom8_asana/models/business/unit.py:483`. Additionally, ~50 "Import here to avoid circular import" inline deferred imports within function bodies. The `_bind_entity_types()` function at `src/autom8_asana/core/entity_registry.py:712` exists solely to break the `core.entity_registry` <-> `core.types` circular dependency using `object.__setattr__` on frozen dataclasses.
**Ideal resolution**: Extract interface packages. Full resolution requires major package restructuring.
**Resolution cost**: HIGH (weeks). 6 structural cycles remain.

---

### TENSION-002: Dual Exception Hierarchies (AsanaError vs ServiceError) + 3 Rogue Exceptions

**Type**: Naming mismatch / dual-system pattern
**Location**: `src/autom8_asana/exceptions.py` (AsanaError tree, 16 exception classes) and `src/autom8_asana/services/errors.py` (ServiceError tree, per ADR-SLE-003). Additionally, 4 exception hierarchies total: AsanaError, Autom8Error (`src/autom8_asana/core/exceptions.py`), ServiceError, QueryEngineError (`src/autom8_asana/query/errors.py`), DataFrameError (`src/autom8_asana/dataframes/exceptions.py`).
**Rogue exceptions**: Three exceptions bypass all hierarchies:
- `CacheNotWarmError(Exception)` at `src/autom8_asana/services/query_service.py:240` -- module-local, used by 3 route handlers
- `MissingConfigurationError(Exception)` at `src/autom8_asana/cache/integration/autom8_adapter.py:57` -- not in any hierarchy
- `ResolutionError(Exception)` at `src/autom8_asana/resolution/context.py:440` -- duplicates `src/autom8_asana/exceptions.py:321` (two classes with the same name, different inheritance)
**Historical reason**: `AsanaError` was the original SDK exception hierarchy for HTTP API errors. `ServiceError` was added for business logic errors to decouple services from HTTP concerns.
**Ideal resolution**: Unify into a single hierarchy with clear domain/transport separation. Promote rogue exceptions into appropriate trees.
**Resolution cost**: MEDIUM. ~50 exception handler sites would need updating. Risk of breaking error mapping at API boundary.

---

### TENSION-003: SaveSession Coordinator Complexity (14 Collaborators)

**Type**: Over-engineering risk (perceived, not actual -- Coordinator pattern)
**Location**: `src/autom8_asana/persistence/session.py` (1,849 lines) + 13 collaborator modules (per TDD-GAP-01, TDD-0011, TDD-GAP-05). Imports from: `action_executor`, `actions`, `cache_invalidator`, `events`, `graph`, `healing`, `models`, `pipeline`, `tracker`, `exceptions`, `cascade`, `reorder`, `holder_construction`.
**Historical reason**: SaveSession orchestrates the full write pipeline: change tracking, action building, dependency graph ordering, execution, cache invalidation, healing, event emission. Each collaborator handles one concern.
**Ideal resolution**: This is explicitly documented as NOT a god object. Do NOT decompose.
**Resolution cost**: N/A -- frozen by design decision per ADR-0035.

---

### TENSION-004: Legacy Query Endpoint (Deprecated, Sunset 2026-06-01)

**Type**: Dual-system pattern
**Location**: `src/autom8_asana/api/routes/query.py` -- `POST /v1/query/{entity_type}` (deprecated) vs `POST /v1/query/{entity_type}/rows` (current)
**Historical reason**: v1 query endpoint used flat equality filtering. v2 introduced composable predicates. Legacy retained for backward compatibility with existing consumers.
**Evidence**: `src/autom8_asana/api/routes/query.py:491` "Deprecated endpoint (sunset 2026-06-01)". `src/autom8_asana/api/routes/query.py:611` emits `deprecated_query_endpoint_used` structured log event.
**Ideal resolution**: Remove legacy endpoint after sunset date. GATE: CloudWatch query on `deprecated_query_endpoint_used` metric (30 days of zero usage).
**Resolution cost**: LOW after gate passes.

---

### TENSION-005: Legacy Preload Fallback (ADR-011) with BROAD-CATCH Sites

**Type**: Dual-system pattern / resilience + unguarded exception handling
**Location**: `src/autom8_asana/api/preload/legacy.py` (activated at `progressive.py:328-340` on progressive failure). 30+ BROAD-CATCH sites across the codebase, each tagged with isolation rationale (e.g., `# BROAD-CATCH: isolation -- push failure must never fail cache warmer`).
**Historical reason**: Progressive preload is the primary path, but legacy preload remains as a degraded-mode fallback. ADR-011 documents this as an intentional resilience pattern. BROAD-CATCH sites were preserved from `main.py` during decomposition (TDD-I5) and tagged for narrowing in I6 (Exception Narrowing). I6 has NOT been executed.
**Evidence**: Grep for `BROAD-CATCH` yields 30+ sites in `src/autom8_asana/` with structured comments explaining isolation rationale.
**Ideal resolution**: Remove legacy preload when progressive is proven stable. Narrow the BROAD-CATCH sites as part of I6 initiative.
**Resolution cost**: LOW technically for preload removal, HIGH risk. I6 exception narrowing: LOW per site, MEDIUM total.

---

### TENSION-006: Cache Backend Divergence (Intentional by Design)

**Type**: Perceived duplication (actually intentional design per ADR-0067)
**Location**: `src/autom8_asana/cache/backends/memory.py`, `src/autom8_asana/cache/backends/s3.py`, `src/autom8_asana/cache/backends/redis.py`
**Historical reason**: Memory, S3, and Redis backends have intentionally different behavior (TTL, eviction, serialization). ADR-0067 explicitly states this is by design.
**Resolution cost**: N/A -- frozen.

---

### TENSION-007: Pipeline vs Lifecycle Dual Paths (CLOSED)

**Type**: Dual-system pattern (closed)
**Location**: `src/autom8_asana/automation/pipeline.py` vs `src/autom8_asana/lifecycle/` (engine, config, wiring, sections, reopen)
**Historical reason**: Lifecycle engine absorbed most PipelineConversionRule behavior. D-022 CLOSED -- WS6 extracted sufficient shared surface.
**Resolution cost**: N/A -- closed as designed.

---

### TENSION-008: os.environ Direct Access (28+ Sites)

**Type**: Under-engineering
**Location**: Scattered: `src/autom8_asana/config.py`, `src/autom8_asana/settings.py`, `src/autom8_asana/api/routes/health.py`, `src/autom8_asana/api/routes/admin.py`, `src/autom8_asana/api/preload/progressive.py`, `src/autom8_asana/automation/events/config.py`, `src/autom8_asana/auth/service_token.py`, `src/autom8_asana/entrypoint.py`, `src/autom8_asana/services/gid_push.py`, `src/autom8_asana/dataframes/offline.py`, `src/autom8_asana/api/main.py` (IDEMPOTENCY_STORE_BACKEND, IDEMPOTENCY_TABLE_NAME, IDEMPOTENCY_TABLE_REGION).
**Historical reason**: Direct `os.environ` access predates `pydantic-settings` adoption. The env var standardization (commit c9273d8, 2026-03-14) applied ADR-ENV-NAMING-CONVENTION for canonical `AUTOM8Y_DATA_*`, `ASANA_CW_*`, `ASANA_RUNTIME_*` names but did not sweep all os.environ sites.
**Evidence**: `src/autom8_asana/api/main.py:319` reads `IDEMPOTENCY_STORE_BACKEND` directly rather than via settings.
**Resolution cost**: LOW per site, MEDIUM total. Deferred item D-011 -- address opportunistically.

---

### TENSION-009: Heavy Mock Usage (~540 Sites)

**Type**: Test infrastructure debt (ACCEPT verdict)
**Location**: `tests/` directory, ~470 test files
**Historical reason**: WS-OVERMOCK initiative evaluated mocks, received ACCEPT verdict -- 75-90% are appropriate boundary mocks.
**Resolution cost**: HIGH. D-027 deferred.

---

### TENSION-010: CascadingFieldDef allow_override Default

**Type**: API contract constraint (frozen)
**Location**: `src/autom8_asana/models/business/fields.py`, `CascadingFieldDef`
**Historical reason**: Per ADR-0054, `allow_override=False` is the DEFAULT. Parent value ALWAYS overwrites descendant value. Changing this default would silently break cascading field behavior across all entity types.
**Resolution cost**: N/A -- frozen by design.

---

### TENSION-011: @async_method Descriptor Type System Friction (269 type:ignore Suppressions)

**Type**: Over-engineering risk / mypy strict incompatibility
**Location**: `src/autom8_asana/patterns/async_method.py`, and all 11 client files using `@async_method`
**Historical reason**: `@async_method` generates both `get_async()` and `get()` variants dynamically via `__set_name__`, eliminating code duplication (~65% reduction). mypy cannot track dynamic method injection -- requiring `# type: ignore[arg-type, operator, misc]` at every call site.
**Ideal resolution**: Protocol stubs or a mypy plugin for AsyncMethodPair. No clean resolution under mypy strict mode.
**Resolution cost**: HIGH. Structural constraint of the descriptor pattern.

---

### TENSION-012: Lifecycle Config Forward-Compat Contract (D-LC-002)

**Type**: API contract constraint (frozen)
**Location**: `src/autom8_asana/lifecycle/config.py` -- 11 Pydantic config models (`SelfLoopConfig`, `InitActionConfig`, `ValidationRuleConfig`, `ValidationConfig`, `CascadingSectionConfig`, `TransitionConfig`, `SeedingConfig`, `AssigneeConfig`, `StageConfig`, `WiringRuleConfig`, `LifecycleConfigModel`)
**Historical reason**: Lifecycle YAML files may evolve ahead of code. New fields added to YAML configs by config authors before Pydantic models are updated must not break older code. These 11 models MUST use `extra="ignore"` (not `extra="forbid"`). Surfaced when SM-003 attempted to add `extra="forbid"` -- immediately reverted (commit 5a24194, SCAR-014).
**Ideal resolution**: N/A -- intentional forward-compat contract.
**Resolution cost**: N/A -- frozen by design. Constraint is named D-LC-002.

---

### TENSION-013: Triple Registry Duplication for Entity-Project Mapping

**Type**: Naming mismatch / over-engineering / layering violation
**Location**:
- `src/autom8_asana/core/entity_registry.py` -- `EntityRegistry` / `ENTITY_DESCRIPTORS` (canonical metadata)
- `src/autom8_asana/core/project_registry.py` -- `ProjectRegistry` (logical-name -> GID constants)
- `src/autom8_asana/models/business/registry.py` -- `ProjectTypeRegistry` (runtime GID -> EntityType lookup)
- `src/autom8_asana/services/resolver.py` -- `EntityProjectRegistry` (discovery-time GID -> entity config)
**Historical reason**: `ProjectTypeRegistry` pre-dates `EntityRegistry`. `EntityProjectRegistry` was added for API startup discovery. `project_registry.py` was added for lifecycle YAML resolution. All four encode entity-to-project-GID mappings in different forms.
**Evidence**: `src/autom8_asana/core/registry_validation.py` was written specifically to cross-validate the three independent registries at startup (per QW-4, ARCH-REVIEW-1 Section 3.1). The migration comment in `src/autom8_asana/core/project_registry.py:7` reads: "Entity classes retain their own PRIMARY_PROJECT_GID for now... Future sprints will migrate entity classes to reference the registry directly." This migration has not been executed.
**Ideal resolution**: Collapse ProjectTypeRegistry and EntityProjectRegistry into facades over EntityRegistry.
**Resolution cost**: HIGH. Cross-registry validation at startup is a workaround for this gap.

---

### TENSION-014: Frozen Dataclass Mutation via object.__setattr__ (Load-Bearing Pattern)

**Type**: Load-bearing jank (anti-pattern that cannot be removed)
**Location**: `src/autom8_asana/core/entity_registry.py:674-710` (`_bind_entity_types`), `src/autom8_asana/persistence/holder_construction.py:166-191`, `src/autom8_asana/persistence/action_executor.py:421`, `src/autom8_asana/persistence/pipeline.py:240`, `src/autom8_asana/services/resolution_result.py:72-74`, `src/autom8_asana/config.py:491-525`
**Historical reason**: `EntityDescriptor` is frozen to enable hashability and thread safety, but `entity_type` cannot be set at declaration time (circular import: `core.types` cannot be imported at `entity_registry` definition). `_bind_entity_types()` uses `object.__setattr__` to mutate after-the-fact. Similar pattern exists in persistence to patch GIDs onto newly-created entities.
**Pattern**: 32 `object.__setattr__` call sites across src. Per ADR-001: "Safe because this runs exactly once before any consumer reads the descriptors."
**Ideal resolution**: Breaking the circular import would allow normal `entity_type` assignment. Requires moving `EntityType` to a leaf module with no dependencies.
**Resolution cost**: MEDIUM. Core plumbing change that touches 17 entity bindings.

---

### TENSION-015: reconciliation_holder vs RECONCILIATIONS_HOLDER Naming Mismatch

**Type**: Naming mismatch
**Location**:
- `src/autom8_asana/core/entity_registry.py:590` -- descriptor name: `"reconciliation_holder"` (singular)
- `src/autom8_asana/core/types.py:38` -- `EntityType.RECONCILIATIONS_HOLDER` (plural)
- `src/autom8_asana/core/entity_registry.py:699` -- binding: `"reconciliation_holder": EntityType.RECONCILIATIONS_HOLDER`
**Historical reason**: The descriptor was named with consistent singular pattern (`contact_holder`, `unit_holder`). The EntityType enum used plural (`RECONCILIATIONS_HOLDER`) matching the Asana project name "Reconciliations". Divergence was never resolved.
**Evidence**: No test guards this naming pair. It compiles because `_bind_entity_types()` uses a hardcoded `_TYPE_MAP` dict.
**Ideal resolution**: Rename `EntityType.RECONCILIATIONS_HOLDER` to `EntityType.RECONCILIATION_HOLDER` (singular) for consistency.
**Resolution cost**: LOW (rename + sed). Risk: any code using the old enum name breaks at runtime.

---

### TENSION-016: Hardcoded Custom Field Resolver Allowlist

**Type**: Under-engineering / naming mismatch
**Location**: `src/autom8_asana/services/universal_strategy.py:935`
**Pattern**: `if self.entity_type in ("unit", "business", "offer"):` -- three entity types are hardcoded to receive `DefaultCustomFieldResolver`. All other entity types receive `None`.
**Historical reason**: Custom field resolution was implemented for the original three entities. When `asset_edit`, `contact`, and holder entities were added, the allowlist was never updated.
**Evidence**: `EntityDescriptor` now has a `custom_field_resolver_class_path` field (added since prior generation) enabling descriptor-driven resolver lookup. However, `UniversalResolutionStrategy._get_custom_field_resolver()` has not yet been updated to use it.
**Ideal resolution**: Drive resolver lookup from the `EntityDescriptor.custom_field_resolver_class_path` field, not a hardcoded list.
**Resolution cost**: LOW (use existing descriptor field).

---

### TENSION-017: 9 mypy ignore_errors Module Overrides

**Type**: Under-engineering / type safety erosion
**Location**: `pyproject.toml` [[tool.mypy.overrides]] sections with `ignore_errors = true` for:
- `autom8_asana.cache.integration.dataframe_cache`
- `autom8_asana.services.universal_strategy`
- `autom8_asana.dataframes.builders.progressive`
- `autom8_asana.services.dataframe_service`
- `autom8_asana.query.__main__`
- `autom8_asana.api.routes.query`
- `autom8_asana.services.intake_resolve_service`
- `autom8_asana.services.intake_create_service`
- `autom8_asana.services.intake_custom_field_service`
**Historical reason**: Pre-existing mypy strict violations in Polars/dataframe code (no-any-return) and new intake service files use dynamic SDK APIs not yet typed. Annotated as "Pre-existing mypy strict violations" in pyproject.toml.
**Evidence**: 9 modules exempt from mypy strict mode. Several are core business logic files (universal_strategy.py at 997 lines, progressive.py at 1,339 lines).
**Ideal resolution**: Add proper type annotations and remove ignore_errors overrides incrementally.
**Resolution cost**: MEDIUM. Polars API typing is the primary blocker.

---

### TENSION-018: autom8y-api-schemas Editable Path Dependency

**Type**: Build/deployment constraint
**Location**: `pyproject.toml:316` -- `autom8y-api-schemas = { path = "../autom8y-api-schemas", editable = true }`
**Historical reason**: `autom8y-api-schemas` is a sibling monorepo package used in development. The editable path dependency works locally and in CI but is stripped at Docker build time by `--no-sources` (SCAR-022/DEF-009).
**Evidence**: Dockerfile must use `uv sync --no-sources --no-dev` to resolve from CodeArtifact registry instead of local path. The `--no-sources` flag is the sole mechanism preventing the editable path from breaking the container build.
**Ideal resolution**: This pattern is intentional for the monorepo development workflow. No action needed.
**Resolution cost**: N/A -- constrained by monorepo structure.

---

### TENSION-019: SecureRouter Migration In-Progress

**Type**: Migration / dual-system pattern
**Location**: `src/autom8_asana/api/routes/_security.py` (new factories), `src/autom8_asana/api/main.py` (custom_openapi security annotation)
**Historical reason**: Recent commits (9513f52, 2c899ca) migrated routers to fleet SDK `SecureRouter` and `E164PhoneField`. The custom_openapi() function in `src/autom8_asana/api/main.py` still manually injects security schemes and strips authorization parameters -- a 200-line function that partially overlaps with `SecureRouter`'s declarative security.
**Evidence**: `_security.py` defines `pat_router()` and `s2s_router()` factory functions wrapping `SecureRouter`. `custom_openapi()` continues to post-process the spec with tag-based classification (`_PAT_TAGS`, `_S2S_TAGS`, `_TOKEN_TAGS`, `_NO_AUTH_TAGS`).
**Ideal resolution**: Once all routers use `SecureRouter`, the manual security annotation in `custom_openapi()` can be simplified or removed.
**Resolution cost**: LOW to MEDIUM. Requires verifying all security annotations are handled by SecureRouter.

---

## Trade-off Documentation

| Tension | Current State | Ideal State | Why Current Persists |
|---------|--------------|-------------|---------------------|
| TENSION-001 | 44 E402 sites, ~50 deferred function imports, 6 cycles | Clean dependency graph | Cost too high; deeply coupled packages |
| TENSION-002 | Two exception trees + 3 rogue exceptions | Unified hierarchy | Breaking 50+ handler sites; both trees work |
| TENSION-003 | 14-collaborator Coordinator | Same (by design) | Decomposition increases coupling |
| TENSION-004 | Dual query endpoints | Single modern endpoint | Waiting for sunset gate (CloudWatch metric) |
| TENSION-005 | Dual preload paths + 30+ BROAD-CATCH sites | Progressive only + narrowed exceptions | Safety net needed; I6 initiative not started |
| TENSION-006 | Cache dimensions differ | Same (by design) | ADR-0067 explicitly documents as intentional |
| TENSION-007 | Pipeline + Lifecycle | Lifecycle only | Essential pipeline differences remain (CLOSED) |
| TENSION-008 | os.environ scattered (28+) | Centralized settings | Low priority, D-011 |
| TENSION-009 | 540 mock sites | Fewer mocks, more fakes | WS-OVERMOCK ACCEPT verdict; appropriate |
| TENSION-010 | allow_override=False default | Same (by design) | Data integrity constraint per ADR-0054 |
| TENSION-011 | 269 type:ignore suppressions | Protocol stubs / mypy plugin | Structural constraint of descriptor pattern |
| TENSION-012 | 11 lifecycle models must be extra="ignore" | Same (by design) | D-LC-002 forward-compat contract |
| TENSION-013 | 4 registries encoding entity-GID mapping | Collapsed to 1 | ProjectTypeRegistry and EntityProjectRegistry predate EntityRegistry; migration not executed |
| TENSION-014 | object.__setattr__ on frozen dataclasses (32 sites) | Normal assignment | Circular import prevents frozen-safe initialization |
| TENSION-015 | reconciliation_holder vs RECONCILIATIONS_HOLDER | Consistent singular naming | Never renamed; works at runtime via hardcoded dict |
| TENSION-016 | Hardcoded allowlist for custom field resolver | Descriptor-driven (field exists, not wired) | UniversalResolutionStrategy not updated to use descriptor field |
| TENSION-017 | 9 modules exempt from mypy strict | Full mypy strict coverage | Polars API typing is the primary blocker |
| TENSION-018 | Editable path dep for autom8y-api-schemas | Same (by design) | Monorepo development workflow |
| TENSION-019 | SecureRouter + manual custom_openapi security | SecureRouter only | Migration in-progress |

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
- **ADR-cascade-contract-policy**: Cascade null rate monitoring (informs RISK-010)
- **ADR-cascade-null-resolution**: S3 resume hierarchy warming fix (SCAR-005/006)
- **ADR-schema-extractor-triad-policy**: Partial triad rationale (TENSION-016, RISK-009)
- **ADR-status-aware-resolution**: active_only=True breaking change (evolution constraint)
- **ADR-SPRINT1-001**: Tag-based security classification (TENSION-019)
- **SCAR-022/DEF-009**: uv --no-sources constraint (TENSION-018)

## Abstraction Gap Mapping

### Missing Abstractions

**GAP-001: Unified DataFrameProvider for All Consumers**
- The `DataFrameProvider` protocol exists (`src/autom8_asana/protocols/dataframe_provider.py`) and is used by `QueryEngine` (`src/autom8_asana/query/engine.py`). However, `EntityQueryService` still uses `UniversalResolutionStrategy._get_dataframe()` directly -- not the protocol. This is documented in `src/autom8_asana/services/query_service.py:5-13` as intentional (bypassing the protocol gives access to the full cache lifecycle including build lock, coalescing, and circuit breaker).
- Files: `src/autom8_asana/protocols/dataframe_provider.py`, `src/autom8_asana/services/query_service.py`, `src/autom8_asana/services/universal_strategy.py`
- Impact: Adding a new DataFrame consumer with full cache lifecycle semantics requires understanding the private `_get_dataframe()` call chain, not just the protocol.

**GAP-002: Configuration Consolidation**
- Three config systems coexist: local dataclasses (`RateLimitConfig`, `RetryConfig`, `CircuitBreakerConfig` in `src/autom8_asana/config.py`), platform primitives (`PlatformRetryConfig`, `PlatformCircuitBreakerConfig` from autom8y-http), and pydantic-settings (`src/autom8_asana/settings.py`). `DataServiceClient` (`src/autom8_asana/clients/data/config.py`) has its own `CircuitBreakerConfig` with identical field structure. Migration to platform primitives is in progress (TDD-PRIMITIVE-MIGRATION-001).
- Files: `src/autom8_asana/config.py`, `src/autom8_asana/clients/data/config.py`
- Impact: Configuration drift between old and new code paths.

**GAP-003: Custom Field Resolver Not Fully Descriptor-Driven**
- `UniversalResolutionStrategy._get_custom_field_resolver()` at `src/autom8_asana/services/universal_strategy.py:935` uses a hardcoded `("unit", "business", "offer")` list. The `EntityDescriptor` now has `custom_field_resolver_class_path` (observed on the `business` descriptor: `"autom8_asana.dataframes.resolver.DefaultCustomFieldResolver"`), but `UniversalResolutionStrategy` has not been updated to use it.
- Files: `src/autom8_asana/services/universal_strategy.py:935`, `src/autom8_asana/core/entity_registry.py`
- Impact: Silent omission -- new entities will not receive custom field resolution without updating the allowlist.

**GAP-004: Webhook Dispatch Seam (GAP-03 Partially Filled)**
- `src/autom8_asana/api/routes/webhooks.py` defines `WebhookDispatcher` protocol with `NoOpDispatcher` default. `src/autom8_asana/lifecycle/webhook_dispatcher.py` provides a real implementation replacing the no-op at the GAP-03 seam. However, the WARNING in webhooks.py about loop risk ("our outbound writes to Asana may trigger Asana Rules that POST back to this endpoint") notes that "Loop prevention is GAP-03 scope." The loop prevention mechanism is not documented as implemented.
- Files: `src/autom8_asana/api/routes/webhooks.py:56-59`, `src/autom8_asana/lifecycle/webhook_dispatcher.py`
- Impact: Potential webhook loop risk between outbound Asana writes and inbound webhook endpoint.

### Premature Abstractions

None significant observed. The COMPAT-PURGE initiative (2026-02-25) removed most unnecessary abstractions. `src/autom8_asana/models/business/base.py` uses `extra="allow"` (intentional -- supports dynamic attribute attachment via `_children_cache` and similar private patterns in holder types).

### Schema-Extractor-Row Triad Partial Wiring

4 entities have partial triads (schema without extractor): `business`, `offer`, `asset_edit`, `asset_edit_holder`. This is intentional per ADR-schema-extractor-triad-policy -- the generic `SchemaExtractor` handles all extraction for these entities. `strict_triad_validation` is set to `True` at the registry level (line 920: `_REGISTRY = EntityRegistry(ENTITY_DESCRIPTORS, strict_triad_validation=True)`), but check 6d for schema-without-extractor only emits a WARNING, not an ERROR, regardless of the flag.

### Zombie Abstractions

**ZOMBIE-001: reconciliation package** -- `src/autom8_asana/reconciliation/` exists as a package directory containing only `__pycache__/` (no `__init__.py`). The reconciliation domain models live at `src/autom8_asana/models/business/reconciliation.py` and the workflow at `src/autom8_asana/automation/workflows/payment_reconciliation/`. The empty package directory appears to be vestigial.

## Load-Bearing Code Identification

### LB-001: EntityRegistry (Single Source of Truth)

**Location**: `src/autom8_asana/core/entity_registry.py` (946 lines)
**What it does**: Declares all entity metadata via `EntityDescriptor`. Four consumers are descriptor-driven: `SchemaRegistry._ensure_initialized()` (auto-discovers schemas via `schema_module_path`), extractor factory (`extractor_class_path`), `ENTITY_RELATIONSHIPS` (derived from `join_keys`), `_build_cascading_field_registry()` (via `cascading_field_provider` flag).
**Dependents**: `src/autom8_asana/dataframes/models/registry.py`, `src/autom8_asana/dataframes/extractors/`, `src/autom8_asana/core/types.py`, `src/autom8_asana/models/business/registry.py`, `src/autom8_asana/cache/models/entry.py`, `src/autom8_asana/config.py` (FACADE), `src/autom8_asana/services/universal_strategy.py` (FACADE)
**Naive fix risk**: Changing descriptor shape breaks all 4 descriptor-driven consumers plus backward-compat facades. Renaming or removing fields causes silent runtime failures.
**Safe refactor**: Add new fields to `EntityDescriptor` (additive). Do NOT rename or remove existing fields. Note: deferred `# noqa: E402` import to `system_context` at module bottom -- do not move to top-level.
**Hot path**: Every DataFrameCache warmup and every resolution call reads this registry.

### LB-002: SaveSession Pipeline

**Location**: `src/autom8_asana/persistence/session.py` (1,849 lines) + 13 collaborator modules
**What it does**: Orchestrates all Asana write operations -- ENSURE_HOLDERS phase (TDD-GAP-01), action executor (TDD-0011), batch support (TDD-GAP-05). 5-phase pipeline: VALIDATE -> PREPARE -> EXECUTE -> ACTIONS -> CONFIRM.
**Dependents**: All API write routes, lifecycle engine, automation engine.
**Naive fix risk**: Decomposing SaveSession scatters orchestration. Reordering pipeline stages breaks commit semantics. DEF-001 (SCAR-008): cleanup ordering (clear accessor BEFORE snapshot) is safety-critical.
**Safe refactor**: Add new pipeline stages at defined extension points. Do NOT reorder existing stages. Adding holder auto-creation behavior requires understanding `auto_create_holders` flag semantics (session.py lines 150-169). Thread safety via `RLock` -- all state access through `_state_lock()`.

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

**Location**: `src/autom8_asana/lifecycle/config.py` -- 11 models
**What it does**: YAML-deserializable config for lifecycle rules. Must tolerate unknown fields.
**Dependents**: All lifecycle YAML config files (runtime-loaded).
**Naive fix risk**: Adding `extra="forbid"` to these models breaks forward-compatibility (SCAR-014).
**Safe refactor**: These 11 models must NOT get `extra="forbid"`. All other Pydantic models (API request/response, query models) CAN and DO use `extra="forbid"`.

### LB-007: _bind_entity_types() + object.__setattr__ Mutation (TENSION-014)

**Location**: `src/autom8_asana/core/entity_registry.py:712`
**What it does**: Mutates frozen `EntityDescriptor` instances after module load to inject `entity_type` values, bypassing the `frozen=True` constraint via `object.__setattr__`. Runs exactly once at module load before the singleton registry is built.
**Dependents**: All 17 entity descriptors in `ENTITY_DESCRIPTORS`. The binding is required for `registry.get_by_type()` to work.
**Naive fix risk**: Adding any code that reads `entity_type` before `_bind_entity_types()` completes will get `None`. Calling `_bind_entity_types()` a second time (outside of `_reset_entity_registry`) is safe (idempotent).
**Safe refactor**: The deferred binding is safe as-is. Resolution requires eliminating the circular import between `core.entity_registry` and `core.types`.

### LB-008: Cross-Registry Startup Validation

**Location**: `src/autom8_asana/core/registry_validation.py`
**What it does**: Validates consistency across `EntityRegistry`, `ProjectTypeRegistry`, and `EntityProjectRegistry` at startup. Called from both `api/lifespan.py` and Lambda handler bootstrap.
**Dependents**: All three registries. Failures here mean entity-to-project mapping is broken.
**Naive fix risk**: Disabling or skipping this validation removes the only guard against silent registry divergence (TENSION-013).
**Safe refactor**: Always call with `check_project_type_registry=True`. `check_entity_project_registry` can be `False` for Lambda bootstrap where EntityProjectRegistry is unpopulated.

### LB-009: Warm Priority Ordering (Cascade Invariant)

**Location**: `src/autom8_asana/core/entity_registry.py`, `warmable_entities()` method and `warm_priority` field on each descriptor
**What it does**: Ensures cascade source entities warm before cascade consumers. Current ordering: `business (1) -> unit (2) -> offer (3) -> contact (4) -> asset_edit (5) -> asset_edit_holder (6)`.
**Dependents**: All DataFrame builders, Lambda cache warmer, API startup preload.
**Naive fix risk**: Changing warm_priority ordering reproduces SCAR-005/006 conditions (30% cascade field null rate). The docstring explicitly references SCAR-005/006.
**Safe refactor**: New warmable entities must have `warm_priority` > all their cascade sources. Per ADR-cascade-contract-policy.

### LB-010: _bootstrap.py Model Registration

**Location**: `src/autom8_asana/models/business/_bootstrap.py`
**What it does**: Explicit, deterministic model registration via `register_all_models()`. Imports all entity model classes inside the function to avoid circular imports at module load time. Called from `api/lifespan.py` and `entrypoint.py`.
**Dependents**: All detection, resolution, and lifecycle subsystems.
**Naive fix risk**: Adding a new entity model class without adding it to `_bootstrap.py` means the model is never registered with `ProjectRegistry`, causing Tier 1 detection to miss it.
**Safe refactor**: New entity models must be added to the import list inside `register_all_models()`.

## Evolution Constraint Documentation

### Changeability Ratings

| Area | Rating | Evidence |
|------|--------|---------|
| `src/autom8_asana/api/routes/` | **Safe** | Local changes only. New routes added without breaking existing. SecureRouter migration simplifies new route creation via `pat_router()` and `s2s_router()` factories. |
| `src/autom8_asana/query/` | **Safe** | Well-encapsulated via DataFrameProvider protocol. |
| `src/autom8_asana/metrics/` | **Safe** | Isolated subsystem with clear boundaries. |
| `src/autom8_asana/search/` | **Safe** | Isolated service, minimal dependents. |
| `src/autom8_asana/lambda_handlers/` | **Safe** | Entry points with no internal dependents. Recent RF-001 through RF-006 refactoring extracted concerns (story_warmer, push_orchestrator, timeout, post_build_validation, hierarchy_warmer) into dedicated modules. |
| `src/autom8_asana/observability/` | **Safe** | Decorator pattern, no cross-coupling. |
| `src/autom8_asana/services/` | **Coordinated** | Changes may affect routes and tests. Service errors mapped to HTTP. |
| `src/autom8_asana/dataframes/builders/` | **Coordinated** | Schema changes affect extractors and cache integration. Cascade validator is post-build. Recent RF-004/RF-005 extracted HierarchyWarmer and PostBuildValidation. |
| `src/autom8_asana/cache/` | **Coordinated** | Multi-tier changes require testing Memory + S3 + Redis paths. Schema versioning behind `_SCHEMA_VERSIONING_AVAILABLE` feature flag. |
| `src/autom8_asana/lifecycle/` | **Coordinated** | Config-driven; changes require YAML config updates AND respect D-LC-002. |
| `src/autom8_asana/automation/` | **Coordinated** | Event transport uses boto3 via asyncio.to_thread; polling scheduler is APScheduler-based. |
| `src/autom8_asana/persistence/session.py` | **Migration** | 14 collaborators; changes require full pipeline testing. |
| `src/autom8_asana/core/entity_registry.py` | **Migration** | 4+ descriptor-driven consumers; additive changes only. Adding entity = 1 descriptor entry + schema file. |
| `src/autom8_asana/models/business/` | **Coordinated** | Detection (4 tiers + facade), matching, cascading field logic tightly coupled. `_bootstrap.py` must stay synchronized with `EntityRegistry`. SectionClassifier instances (OFFER_CLASSIFIER, UNIT_CLASSIFIER, etc.) define per-entity section classification -- section names must match live Asana project values (recent fix: 905fe4b, 7f35ea7). |
| `src/autom8_asana/lifecycle/config.py` | **Frozen** | D-LC-002 forward-compat contract. 11 models must keep `extra="ignore"`. |
| `src/autom8_asana/exceptions.py` | **Frozen** | Exception hierarchy consumed by all error handlers. Do not restructure. |
| `src/autom8_asana/protocols/` | **Frozen** | Interface contracts consumed by all DI boundaries. Additive only. |
| `src/autom8_asana/config.py` | **Coordinated** | Consumed by API, clients, services. Post-standardization: AUTOM8Y_DATA_*, ASANA_CW_*, ASANA_RUNTIME_* naming must be respected. |
| `src/autom8_asana/patterns/async_method.py` | **Frozen** | Method injection logic. Changing `__set_name__` breaks all 11 client method pairs. |
| `src/autom8_asana/core/project_registry.py` | **Migration** | Migration comment says entity classes should eventually reference registry directly; not yet executed. Changing GID values here without updating entity class `PRIMARY_PROJECT_GID` breaks parity tests. |
| `src/autom8_asana/api/main.py` | **Coordinated** | 663-line app factory with 20 router inclusions, custom_openapi() post-processing, middleware stack. Router inclusion order matters (intake_resolve_router BEFORE resolver_router for path precedence). |
| `src/autom8_asana/models/business/activity.py` | **Coordinated** | SectionClassifier instances frozen with Asana section name literals. Section names must be verified against live Asana projects before modification. Recent truth audit (905fe4b) corrected provisional values. |

### Deprecated Markers and In-Progress Migrations

| Item | Status | Gate/Trigger |
|------|--------|-------------|
| `POST /v1/query/{entity_type}` (legacy) | Deprecated, sunset 2026-06-01 | CloudWatch metric: 30d zero usage |
| Legacy preload (`src/autom8_asana/api/preload/legacy.py`) | Active fallback (ADR-011) | Production incident in fallback path |
| BROAD-CATCH sites (30+ in src) | Tagged for I6 narrowing | I6 initiative not started |
| `os.environ` direct access (28+ sites) | Opportunistic (D-011) | Address when touching the file |
| Heavy mock usage (540 sites) | ACCEPT verdict (D-027) | Dedicated test architecture initiative |
| `HOLDER_KEY_MAP` fallback matching | Active resilience | Per `src/autom8_asana/models/business/detection/facade.py:576` |
| `custom_field_accessor.py` strict=False | Intentional design | Dual-purpose API (not debt) |
| Cache freshness enum consolidation | In progress | `freshness_unified.py` consolidates 4 -> 2 enums; old locations maintain type aliases |
| `ProjectTypeRegistry` -> `EntityRegistry` migration | Stated intent | comment in `project_registry.py:7`; no sprint assigned |
| Partial schema-extractor-row triads (4 entities) | Accepted per ADR | `strict_triad_validation=True` at registry level; check 6d is WARNING only |
| SecureRouter migration | In-progress | custom_openapi() security annotation overlap with SecureRouter |
| SectionClassifier truth audit | Applied (905fe4b) | Section names verified against live Asana; provisional values replaced |
| QUERY HTTP method adoption | HOLD | Blocked by httptools parser, FastAPI decorator, and tooling support |

### External Dependency Constraints

- **Asana API rate limits**: Global rate limiter via SlowAPI + per-client adaptive semaphore (TDD-GAP-04/ADR-GAP04-001 AIMD control)
- **autom8y-data service**: DataServiceClient depends on data service API contract. Entity type mapping must match. Emergency kill switch: `AUTOM8Y_DATA_INSIGHTS_ENABLED`.
- **autom8y-auth SDK**: JWT validation and JWKS fetching encapsulated. Version `>=1.1.0` required for observability extras.
- **autom8y-api-schemas**: Editable path dependency (`../autom8y-api-schemas`). Provides `SecureRouter` and `E164PhoneField`. Version `>=1.1.0` required.
- **Polars DataFrame format**: Schema definitions must match Polars column types. Schema changes require migration.
- **S3 cache format**: Parquet files in S3. Format changes require cache invalidation and re-warming. `asyncio.to_thread()` wraps all boto3 calls.
- **autom8y-telemetry**: `glass-S9: 0.6.0+` required for `trace_computation` decorator.
- **Lambda context timeout**: `cache_warmer.py:162` notes that `context.get_remaining_time_in_millis()` returns `None` if context is `None` -- no timeout enforcement in test/local mode.
- **Warm priority ordering constraint**: Cascade source entities must warm before cascade consumers. Current ordering: `business (1) -> unit (2) -> offer (3) -> contact (4) -> asset_edit (5) -> asset_edit_holder (6)`. Violating this order reproduces SCAR-005/006 conditions.
- **ALB 60-second timeout**: Per SCAR-015, request handlers must not perform per-request I/O exceeding 60 seconds. All heavy I/O must be pre-computed at warm-up time.
- **uv >=0.15.4**: `--frozen` and `--no-sources` are mutually exclusive (SCAR-022). Dockerfile uses `--no-sources --no-dev` only.

## Risk Zone Mapping

### RISK-001: Silent Fallback in Detection Facade

**Location**: `src/autom8_asana/models/business/detection/facade.py:576-584`
**Missing guard**: Falls back to legacy `HOLDER_KEY_MAP` matching with logged warning and `detection_fallback_holder_key_map` log event but NO metric emission.
**Evidence**: Lines 580-584 call `log.warning("detection_fallback_holder_key_map", fallback="HOLDER_KEY_MAP")` -- observable only in logs, not CloudWatch.
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
**Status**: CLOSED in COMPAT-PURGE -- intentional dual-purpose design. Agents should be aware of silent pass-through.

### RISK-006: Sync-in-Async Context Detection Gap in DataServiceClient

**Location**: `src/autom8_asana/clients/data/client.py`
**Missing guard**: The `_run_sync()` method checks for a running loop and raises `SyncInAsyncContextError` -- correct. However, the sync `fetch_insights()` path uses `run_in_executor()` to a thread pool. If a caller passes an executor without a running loop (test context), the detection can pass but the thread-pool call may silently deadlock.
**Recommended guard**: Integration test covering sync call from thread-pool context.

### RISK-007: Lambda Handler Timeout Bypass When context=None

**Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:162`
**Missing guard**: `context.get_remaining_time_in_millis()` returns `None` when context is `None` (no Lambda context object -- local/test mode). The timeout guard is disabled in this case.
**Evidence**: Line 162 comment: "Returns False if context is None (no timeout enforcement)."
**Recommended guard**: Integration test should verify timeout behavior with mock context object, not `None`.

### RISK-008: BROAD-CATCH Sites in Lambda Handlers and Preload (30+ Known)

**Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py` (5 sites), `src/autom8_asana/lambda_handlers/cache_invalidate.py` (2), `src/autom8_asana/lambda_handlers/workflow_handler.py` (2), `src/autom8_asana/lambda_handlers/story_warmer.py` (3), `src/autom8_asana/lambda_handlers/checkpoint.py` (3), `src/autom8_asana/lambda_handlers/push_orchestrator.py` (2), `src/autom8_asana/models/business/hydration.py` (4), and others.
**Missing guard**: Catches `Exception` broadly. While each site has a documented isolation rationale (e.g., "push failure must never fail cache warmer"), they also catch programming errors (`TypeError`, `AttributeError`, `KeyError`) that should propagate.
**Evidence**: All tagged with `# BROAD-CATCH:` annotation. Module docstrings note they are "tagged for narrowing in I6 (Exception Narrowing)."
**Cross-ref**: TENSION-005.
**Recommended guard**: Execute I6 initiative. Minimum: narrow to expected exception types per site.

### RISK-009: 4-Entity Partial Schema-Extractor-Row Triad

**Location**: `src/autom8_asana/core/entity_registry.py:828-850` (validation warnings); entities: `business`, `offer`, `asset_edit`, `asset_edit_holder`
**Missing guard**: `strict_triad_validation=True` (set at line 920) but check 6d (schema_without_extractor) only emits a WARNING regardless of strict mode. If an entity accidentally needs custom extraction that SchemaExtractor cannot provide, the WARNING is the only signal.
**Cross-ref**: ADR-schema-extractor-triad-policy.
**Recommended guard**: Monitor startup warnings. Promote check 6d to ERROR when all triads are complete.

### RISK-010: Cascade Field Null Rate Without Continuous Monitoring

**Location**: `src/autom8_asana/dataframes/builders/cascade_validator.py`, `src/autom8_asana/dataframes/builders/progressive.py`
**Missing guard**: Post-build cascade null rate audit runs and logs structured events (`cascade_key_null_audit`), but there is no CloudWatch alarm or metric emission. Detection depends on log analysis.
**Cross-ref**: ADR-cascade-contract-policy. SCAR-005/006 (30% null rate production incident).
**Recommended guard**: Emit CloudWatch metric for cascade null rates. Alert on >5% threshold.

### RISK-011: Webhook Loop Prevention Not Implemented

**Location**: `src/autom8_asana/api/routes/webhooks.py:56-59`
**Missing guard**: The WARNING comment states: "Implementations must be aware of loop risk -- our outbound writes to Asana may trigger Asana Rules that POST back to this endpoint. Loop prevention is GAP-03 scope." The lifecycle webhook dispatcher (`src/autom8_asana/lifecycle/webhook_dispatcher.py`) replaces the no-op but no explicit loop detection mechanism (e.g., idempotency check, write-origin tracking) is visible.
**Cross-ref**: GAP-004 (Abstraction Gap Mapping).
**Recommended guard**: Implement write-origin tracking or idempotency check on the webhook inbound path.

### RISK-012: SectionClassifier Hardcoded Section Names

**Location**: `src/autom8_asana/models/business/activity.py` (OFFER_CLASSIFIER, UNIT_CLASSIFIER, PROCESS_CLASSIFIER)
**Missing guard**: Section names are string literals frozen into `SectionClassifier.from_groups()` calls. If Asana section names change in the project, classifiers silently return UNKNOWN for all tasks in renamed sections. Recent truth audit (commit 905fe4b) corrected provisional values, indicating this has happened before.
**Evidence**: Commits 905fe4b and 7f35ea7 both fix classifier section names based on live Asana verification.
**Recommended guard**: Add a startup or periodic check that validates classifier section names against live Asana project sections.

## Knowledge Gaps

1. **`src/autom8_asana/query/` package** (15 files): The query engine (compiler, aggregator, join, temporal, hierarchy) was not read in detail. Known to have its own error hierarchy (`QueryEngineError`) and complexity guards (`QueryLimits`).
2. **`src/autom8_asana/metrics/` package**: Domain metrics computation (expr engine, metric registry) not deeply read. Appears to compute business metrics from DataFrames.
3. **`src/autom8_asana/lifecycle/` full state machine**: The exact state machine triggers and guard conditions for creation/completion/sections/wiring were not fully traced.
4. **`src/autom8_asana/models/business/detection/` tier details**: Tier 1-4 detection logic not read at implementation level. Known to exist as a 4-tier cascade with a facade.
5. **`src/autom8_asana/automation/polling/`**: Polling scheduler and YAML config schema not read in detail. Known to have APScheduler-based scheduling.
6. **Recent RF-001 through RF-006 refactoring**: Extraction of story_warmer, push_orchestrator, timeout, post_build_validation, hierarchy_warmer modules was observed in commit log but files not read in detail. These are recent decompositions of `cache_warmer.py` and `progressive.py`.
7. **`src/autom8_asana/api/middleware/idempotency.py`**: DynamoDB-backed idempotency middleware observed in `main.py` but not read in detail. Includes `InMemoryIdempotencyStore` and `NoopIdempotencyStore` for graceful degradation.
8. **SCAR-004 (DEF-005) isolated-cache regression test**: No dedicated test confirms warm-up data is visible to request handlers when `InMemoryCacheProvider` is auto-detected.
9. **SCAR-008 (DEF-001) regression test**: No isolated regression test for the snapshot-ordering bug.
10. **SCAR-013 import-fallback unit test**: No unit test exercises the `_SCHEMA_VERSIONING_AVAILABLE = False` path.

```metadata
overall_grade: A
overall_percentage: 91.5%
confidence: 0.92
criteria_grades:
  tension_catalog_completeness: A
  trade_off_documentation: A
  abstraction_gap_mapping: A
  load_bearing_code_identification: A
  evolution_constraint_documentation: A
  risk_zone_mapping: A
```
