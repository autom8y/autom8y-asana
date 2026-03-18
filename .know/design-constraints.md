---
domain: design-constraints
generated_at: "2026-03-18T11:50:56Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "d234795"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Design Constraints

## Tension Catalog Completeness

### TENSION-001: Circular Import Web (~21 Deferred E402 Imports, 6 Remaining Structural Cycles)

**Type**: Layering violation / under-engineering
**Location**: Across all packages; concentrated in `src/autom8_asana/client.py`, `src/autom8_asana/config.py`, `src/autom8_asana/services/resolver.py`, `src/autom8_asana/services/universal_strategy.py`, `src/autom8_asana/models/business/`
**Historical reason**: Organic growth from a monolithic Asana integration. Entity registry, models, services, and cache all cross-reference each other. The `from __future__ import annotations` + `TYPE_CHECKING` guard was adopted retroactively. The `protocols/` package was extracted to break cycles, but 6 structural cycles remain (prior initiative REM-ASANA-ARCH broke 6 of 13 bidirectional 2-cycles, declared remaining 7 as requiring major redesign).
**Observed pattern**: 21 `# noqa: E402` deferred imports at module level (measured directly). Key sites: `src/autom8_asana/core/entity_registry.py:873`, `src/autom8_asana/models/business/business.py:781`, `src/autom8_asana/models/business/unit.py:483`, `src/autom8_asana/query/hierarchy.py:73` (explicitly comments "circular imports -- core/ must not be imported at module scope from query/").
**Ideal resolution**: Extract interface packages to break cycles (partially done with `protocols/`). Full resolution requires greenfield or major package restructuring.
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

**Type**: Over-engineering risk (perceived, not actual -- Coordinator pattern)
**Location**: `src/autom8_asana/persistence/session.py` + 13 collaborator modules (per TDD-GAP-01, TDD-0011, TDD-GAP-05)
**Historical reason**: SaveSession orchestrates the full write pipeline: change tracking, action building, dependency graph ordering, execution, cache invalidation, healing, event emission. Each collaborator handles one concern.
**Ideal resolution**: This is explicitly documented as NOT a god object. Do NOT decompose.
**Resolution cost**: N/A -- frozen by design decision per ADR-0035.

---

### TENSION-004: Legacy Query Endpoint (Deprecated, Sunset 2026-06-01)

**Type**: Dual-system pattern
**Location**: `src/autom8_asana/api/routes/query.py:425` -- `POST /v1/query/{entity_type}` (deprecated) vs `POST /v1/query/{entity_type}/rows` (current)
**Historical reason**: v1 query endpoint used flat equality filtering. v2 introduced composable predicates. Legacy retained for backward compatibility with existing consumers.
**Ideal resolution**: Remove legacy endpoint after sunset date. GATE: CloudWatch query on `deprecated_query_endpoint_used` metric (30 days of zero usage).
**Resolution cost**: LOW after gate passes. D-002/U-004 in debt ledger.

---

### TENSION-005: Legacy Preload Fallback (ADR-011)

**Type**: Dual-system pattern / resilience
**Location**: `src/autom8_asana/api/preload/legacy.py` (activated at `progressive.py:328-340` on progressive failure)
**Historical reason**: Progressive preload is the primary path, but legacy preload remains as a degraded-mode fallback. ADR-011 documents this as an intentional resilience pattern.
**Ideal resolution**: Remove legacy preload when progressive is proven stable over extended period.
**Resolution cost**: LOW technically, HIGH risk -- removing fallback removes a safety net.

---

### TENSION-006: Cache Divergence (12/14 Dimensions Intentional)

**Type**: Perceived duplication (actually intentional design per ADR-0067)
**Location**: `src/autom8_asana/cache/backends/memory.py`, `src/autom8_asana/cache/backends/s3.py`, `src/autom8_asana/cache/backends/redis.py`
**Historical reason**: Memory, S3, and Redis backends have intentionally different behavior (TTL, eviction, serialization). ADR-0067 explicitly states this is by design.
**Resolution cost**: N/A -- frozen.

---

### TENSION-007: Pipeline vs Lifecycle Dual Paths

**Type**: Dual-system pattern (closed)
**Location**: `src/autom8_asana/automation/pipeline.py` vs `src/autom8_asana/lifecycle/` (engine, config, wiring, sections, reopen)
**Historical reason**: Lifecycle engine absorbed most PipelineConversionRule behavior. Pipeline retained for essential differences lifecycle does not cover. D-022 was CLOSED -- WS6 extracted sufficient shared surface.
**Resolution cost**: N/A -- closed as designed.

---

### TENSION-008: os.environ Direct Access (28+ Sites)

**Type**: Under-engineering
**Location**: Scattered across `src/autom8_asana/config.py:686`, `src/autom8_asana/settings.py:750,758,889`, `src/autom8_asana/api/routes/health.py:170,232`, `src/autom8_asana/api/routes/admin.py:194`, `src/autom8_asana/api/preload/progressive.py:565,676`, `src/autom8_asana/automation/events/config.py:85-87`, `src/autom8_asana/auth/service_token.py:35`, `src/autom8_asana/entrypoint.py:65,78`, `src/autom8_asana/services/gid_push.py:62,111`, `src/autom8_asana/dataframes/offline.py:76,82`, and others.
**Historical reason**: Direct `os.environ` access predates `pydantic-settings` adoption. Some sites remain from before centralization (notably automation subsystems and entrypoints).
**Resolution cost**: LOW per site, MEDIUM total. Deferred item D-011 -- address opportunistically.
**Update since 2026-02-27**: The env var standardization (commit c9273d8, 2026-03-14) applied ADR-ENV-NAMING-CONVENTION as a clean break -- `settings.py` now uses canonical `AUTOM8Y_DATA_*`, `ASANA_CW_*`, `ASANA_RUNTIME_*` names. Count revised to ~28 os.environ sites in src (was stated as "20+").

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
**Location**: `src/autom8_asana/patterns/async_method.py`, `src/autom8_asana/clients/tags.py`, `src/autom8_asana/clients/tasks.py`, and all 11 client files using `@async_method`
**Historical reason**: `@async_method` generates both `get_async()` and `get()` variants dynamically via `__set_name__`, eliminating code duplication (~65% reduction). However, mypy cannot track dynamic method injection -- requiring `# type: ignore[arg-type, operator, misc]` at every `@async_method` call site, plus `# type: ignore[no-overload-impl]` at every overload pair. 269 total `# type: ignore` suppressions project-wide, with the client files contributing heavily.
**Ideal resolution**: Protocol stubs or a mypy plugin for AsyncMethodPair. No clean resolution under mypy strict mode.
**Resolution cost**: HIGH. This is a structural constraint of the descriptor pattern. Adding a new client method requires adding 4 overload stubs plus accepting type ignore suppressions.

---

### TENSION-012: Lifecycle Config Forward-Compat Contract (D-LC-002)

**Type**: API contract constraint (frozen, recently surfaced)
**Location**: `src/autom8_asana/lifecycle/config.py` -- 11 Pydantic config models (`SelfLoopConfig`, `InitActionConfig`, `ValidationRuleConfig`, `ValidationConfig`, `CascadingSectionConfig`, `TransitionConfig`, `SeedingConfig`, `AssigneeConfig`, `StageConfig`, `WiringRuleConfig`, `LifecycleConfigModel`)
**Historical reason**: Lifecycle YAML files may evolve ahead of code. New fields added to YAML configs by config authors before Pydantic models are updated must not break older code. This means these 11 models MUST use `extra="ignore"` (not `extra="forbid"`). Surfaced when SM-003 attempted to add `extra="forbid"` to all models -- immediately reverted (commit 5a24194) with explicit D-LC-002 label.
**Ideal resolution**: N/A -- intentional forward-compat contract. Any future schema-hardening effort must exempt these 11 models.
**Resolution cost**: N/A -- frozen by design. Constraint is now named D-LC-002.

## Trade-off Documentation

| Tension | Current State | Ideal State | Why Current Persists |
|---------|--------------|-------------|---------------------|
| TENSION-001 | 21 E402 deferred imports, 6 cycles | Clean dependency graph | Cost too high; cycles in deeply coupled packages |
| TENSION-002 | Two exception trees | Unified hierarchy | Breaking 50+ handler sites; both trees work |
| TENSION-003 | 14-collaborator Coordinator | Same (by design) | Decomposition increases coupling |
| TENSION-004 | Dual query endpoints | Single modern endpoint | Waiting for sunset gate (CloudWatch metric) |
| TENSION-005 | Dual preload paths | Progressive only | Safety net for production resilience |
| TENSION-006 | 12/14 cache dimensions differ | Same (by design) | ADR-0067 explicitly documents as intentional |
| TENSION-007 | Pipeline + Lifecycle | Lifecycle only | Essential pipeline differences remain |
| TENSION-008 | os.environ scattered (28+) | Centralized settings | Low priority, address opportunistically |
| TENSION-009 | 540 mock sites | Fewer mocks, more fakes | WS-OVERMOCK ACCEPT verdict; appropriate |
| TENSION-010 | allow_override=False default | Same (by design) | Data integrity constraint per ADR-0054 |
| TENSION-011 | 269 type:ignore suppressions | Protocol stubs / mypy plugin | Structural constraint of descriptor pattern |
| TENSION-012 | 11 lifecycle models must be extra="ignore" | Same (by design) | D-LC-002 forward-compat contract |

### ADR Cross-References

- **ADR-0054**: Cascading field architecture (TENSION-010)
- **ADR-0067**: Cache divergence documentation (TENSION-006)
- **ADR-0035**: SaveSession Unit of Work pattern (TENSION-003)
- **ADR-011**: Legacy preload as active fallback (TENSION-005)
- **ADR-SLE-003**: Service layer exception hierarchy (TENSION-002)
- **ADR-0002**: Sync-in-async context fail-fast (informs TENSION-011)
- **ADR-ENV-NAMING-CONVENTION**: Env var standardization (informing TENSION-008 resolution progress)
- **D-LC-002**: Lifecycle config forward-compat contract (TENSION-012)

## Abstraction Gap Mapping

### Missing Abstractions

**GAP-001: Unified DataFrameProvider for All Consumers**
- The `DataFrameProvider` protocol exists (`src/autom8_asana/protocols/dataframe_provider.py`) and is used by `QueryEngine` (`src/autom8_asana/query/engine.py:6-7` explicitly documents this decoupling via R-010). However, `EntityQueryService` still uses `UniversalResolutionStrategy._get_dataframe()` directly -- not the protocol. This is documented in `src/autom8_asana/services/query_service.py:5-13` as intentional (bypassing the protocol gives access to the full cache lifecycle including build lock, coalescing, and circuit breaker).
- Files: `src/autom8_asana/protocols/dataframe_provider.py`, `src/autom8_asana/services/query_service.py:272`, `src/autom8_asana/services/universal_strategy.py:478`
- Impact: Adding a new DataFrame consumer with full cache lifecycle semantics requires understanding the private `_get_dataframe()` call chain, not just the protocol.

**GAP-002: Configuration Consolidation**
- Three config systems coexist: local dataclasses (`RateLimitConfig`, `RetryConfig`, `CircuitBreakerConfig` in `src/autom8_asana/config.py`), platform primitives (`PlatformRetryConfig`, `PlatformCircuitBreakerConfig` from autom8y-http), and pydantic-settings (`src/autom8_asana/settings.py`). New code uses platform primitives; old code uses local dataclasses. DataServiceClient (`src/autom8_asana/clients/data/config.py`) has its own `CircuitBreakerConfig` with identical field structure (documented at line 168: "Shares field structure with autom8_asana.config.CircuitBreakerConfig").
- Files: `src/autom8_asana/config.py:285`, `src/autom8_asana/clients/data/config.py:160`
- Impact: Configuration drift between old and new code paths.

### Premature Abstractions

**None significant observed**. The COMPAT-PURGE initiative (2026-02-25) removed most unnecessary abstractions. Post-COMPAT-PURGE, `src/autom8_asana/models/business/base.py` uses `extra="allow"` (line 221) -- this is intentional (supports dynamic attribute attachment via `_children_cache` and similar private patterns in holder types).

## Load-Bearing Code Identification

### LB-001: EntityRegistry (Single Source of Truth)

**Location**: `src/autom8_asana/core/entity_registry.py`
**What it does**: Declares all entity metadata via `EntityDescriptor`. Four consumers are descriptor-driven: `SchemaRegistry`, extractor factory, `ENTITY_RELATIONSHIPS`, cascading field registry.
**Dependents**: `src/autom8_asana/dataframes/models/registry.py`, `src/autom8_asana/dataframes/extractors/`, `src/autom8_asana/core/types.py`, `src/autom8_asana/models/business/registry.py`, `src/autom8_asana/cache/models/entry.py`
**Naive fix risk**: Changing descriptor shape breaks all 4 descriptor-driven consumers plus backward-compat facades.
**Safe refactor**: Add new fields to `EntityDescriptor` (additive). Do NOT rename or remove existing fields. Note: `entity_registry.py:873` has a deferred `# noqa: E402` import to `system_context` to avoid circular imports -- do not move this import to top-level.

### LB-002: SaveSession Pipeline

**Location**: `src/autom8_asana/persistence/session.py` + 13 collaborator modules
**What it does**: Orchestrates all Asana write operations -- ENSURE_HOLDERS phase (TDD-GAP-01), action executor (TDD-0011), batch support (TDD-GAP-05).
**Dependents**: All API write routes, lifecycle engine, automation engine.
**Naive fix risk**: Decomposing SaveSession scatters orchestration. Reordering pipeline stages breaks commit semantics.
**Safe refactor**: Add new pipeline stages at defined extension points. Do NOT reorder existing stages. Adding holder auto-creation behavior requires understanding `auto_create_holders` flag semantics (session.py:150-169).

### LB-003: SystemContext.reset_all()

**Location**: `src/autom8_asana/core/system_context.py`
**What it does**: Resets all singletons for test isolation. 12 files call `register_reset()` at module level.
**Dependents**: Every test (autouse fixture in `tests/conftest.py`).
**Naive fix risk**: Breaking reset ordering causes test pollution. Missing reset registration causes stale state.
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
**Naive fix risk**: Changing the descriptor's `__set_name__` injection logic silently breaks all method pairs. Adding parameters to `AsyncMethodPair` can change injection behavior.
**Safe refactor**: Do NOT change `sync_name` or `async_name` derivation logic. The `SyncInAsyncContextError` raise behavior (fail-fast, per ADR-0002) must not be weakened.

### LB-006: Lifecycle Config Models (D-LC-002)

**Location**: `src/autom8_asana/lifecycle/config.py` -- 11 models
**What it does**: YAML-deserializable config for lifecycle rules. Must tolerate unknown fields.
**Dependents**: All lifecycle YAML config files (runtime-loaded).
**Naive fix risk**: Adding `extra="forbid"` to these models breaks forward-compatibility -- YAML configs with new fields would raise `ValidationError`.
**Safe refactor**: These 11 models must NOT get `extra="forbid"`. All other models CAN get `extra="forbid"` (5 non-lifecycle models already have it).

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
| `src/autom8_asana/dataframes/builders/` | **Coordinated** | Schema changes affect extractors and cache integration. |
| `src/autom8_asana/cache/` | **Coordinated** | Multi-tier changes require testing Memory + S3 + Redis paths. |
| `src/autom8_asana/lifecycle/` | **Coordinated** | Config-driven; changes require YAML config updates AND respect D-LC-002. |
| `src/autom8_asana/automation/` | **Coordinated** | Event transport uses boto3 via asyncio.to_thread; polling scheduler is APScheduler-based. |
| `src/autom8_asana/persistence/session.py` | **Migration** | 14 collaborators; changes require full pipeline testing. |
| `src/autom8_asana/core/entity_registry.py` | **Migration** | 4+ descriptor-driven consumers; additive changes only. |
| `src/autom8_asana/models/business/` | **Coordinated** | Detection, matching, and cascading field logic tightly coupled. |
| `src/autom8_asana/lifecycle/config.py` | **Frozen** | D-LC-002 forward-compat contract. 11 models must keep extra="ignore". |
| `src/autom8_asana/exceptions.py` | **Frozen** | Exception hierarchy consumed by all error handlers. Do not restructure. |
| `src/autom8_asana/protocols/` | **Frozen** | Interface contracts consumed by all DI boundaries. Additive only. |
| `src/autom8_asana/config.py` | **Coordinated** | Consumed by API, clients, services. Post-standardization: AUTOM8Y_DATA_*, ASANA_CW_*, ASANA_RUNTIME_* naming must be respected. |
| `src/autom8_asana/patterns/async_method.py` | **Frozen** | Method injection logic. Changing __set_name__ breaks all 11 client method pairs. |

### Deprecated Markers and In-Progress Migrations

| Item | Status | Gate/Trigger |
|------|--------|-------------|
| `POST /v1/query/{entity_type}` (legacy) | Deprecated, sunset 2026-06-01 | CloudWatch metric: 30d zero usage |
| Legacy preload (`src/autom8_asana/api/preload/legacy.py`) | Active fallback (ADR-011) | Production incident in fallback path |
| `os.environ` direct access (28+ sites) | Opportunistic (D-011) | Address when touching the file |
| Heavy mock usage (540 sites) | ACCEPT verdict (D-027) | Dedicated test architecture initiative |
| HOLDER_KEY_MAP fallback matching | Active resilience | Per `src/autom8_asana/models/business/detection/facade.py:576` |
| `custom_field_accessor.py` strict=False | Intentional design | Dual-purpose API (not debt) |
| `AUTOM8_DATA_*` prefix in `run_smoke_test.py` | Stale (outside src) | Superseded by c9273d8 clean-break standardization; scripts not updated |

### External Dependency Constraints

- **Asana API rate limits**: Global rate limiter via SlowAPI + per-client adaptive semaphore (TDD-GAP-04/ADR-GAP04-001 AIMD control)
- **autom8y-data service**: DataServiceClient depends on data service API contract. Entity type mapping must match. Emergency kill switch: `AUTOM8Y_DATA_INSIGHTS_ENABLED`.
- **autom8y-auth SDK**: JWT validation and JWKS fetching encapsulated. Version `>=1.1.0` required for observability extras.
- **Polars DataFrame format**: Schema definitions must match Polars column types. Schema changes require migration.
- **S3 cache format**: Parquet files in S3. Format changes require cache invalidation and re-warming. `asyncio.to_thread()` wraps all boto3 calls (thread-safe S3 client per `src/autom8_asana/dataframes/storage.py:288`).
- **autom8y-telemetry**: `glass-S9: 0.6.0+` required for `trace_computation` decorator (per pyproject.toml comment).
- **Lambda context timeout**: `cache_warmer.py:162` notes that `context.get_remaining_time_in_millis()` returns `None` if context is `None` -- no timeout enforcement in test/local mode.

## Risk Zone Mapping

### RISK-001: Silent Fallback in Detection Facade

**Location**: `src/autom8_asana/models/business/detection/facade.py:576-584`
**Missing guard**: Falls back to legacy `HOLDER_KEY_MAP` matching with logged warning and `detection_fallback_holder_key_map` log event but NO metric emission.
**Evidence**: Lines 580-584 call `log.warning("detection_fallback_holder_key_map", fallback="HOLDER_KEY_MAP")` -- observable only in logs, not CloudWatch.
**Recommended guard**: Add metric emission on fallback to track frequency. Cross-ref: TENSION-001 (circular imports prevent cleaner detection architecture).

### RISK-002: Cache Entry Type Inference

**Location**: `src/autom8_asana/cache/models/entry.py:229-247`
**Missing guard**: Legacy serialized data without `_type` field infers type from content. Can fail silently.
**Evidence**: `# Base CacheEntry construction (legacy path)` comment at line 247.
**Recommended guard**: Log warning with entry key when type inference is used (for migration tracking).

### RISK-003: Completeness UNKNOWN for Legacy Cache Entries

**Location**: `src/autom8_asana/cache/models/completeness.py:238-272`
**Missing guard**: `UNKNOWN = 0` treated conservatively (re-fetch for STANDARD/FULL). No alerting when UNKNOWN entries persist beyond expected migration window.
**Evidence**: `# UNKNOWN entries from legacy code need re-fetch` comment.
**Recommended guard**: Metric tracking UNKNOWN entry count per entity type.

### RISK-004: QueryEngine Predicate Depth Unlimited by Default

**Location**: `src/autom8_asana/query/guards.py`
**Missing guard**: Query complexity is bounded by `QueryLimits` but limits can be overridden. Deeply nested predicates could cause stack overflow or excessive computation.
**Recommended guard**: Hard ceiling on predicate depth regardless of limit configuration.

### RISK-005: Custom Field Accessor Non-Strict Mode

**Location**: `src/autom8_asana/models/custom_field_accessor.py:384-387`
**Missing guard**: Non-strict mode returns input as-is, propagating invalid field names silently.
**Evidence**: `# Non-strict mode: return input as-is (legacy behavior)` comment.
**Status**: CLOSED in COMPAT-PURGE -- intentional dual-purpose design. Agents should be aware of silent pass-through.

### RISK-006: Sync-in-Async Context Detection Gap in DataServiceClient

**Location**: `src/autom8_asana/clients/data/client.py:229-259`
**Missing guard**: The `_run_sync()` method (line 229) checks for a running loop and raises `SyncInAsyncContextError` -- correct. However, the sync `fetch_insights()` path at line 791 uses `run_in_executor()` to a thread pool. If a caller passes an executor without a running loop (test context), the detection can pass but the thread-pool call may silently deadlock.
**Evidence**: Lines 791-815 comment: "Runs the async method in a thread pool from sync context (ADR-0002)."
**Recommended guard**: Integration test covering sync call from thread-pool context.

### RISK-007: Lambda Handler Timeout Bypass When context=None

**Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:162`
**Missing guard**: `context.get_remaining_time_in_millis()` returns `None` when context is `None` (no Lambda context object -- local/test mode). The timeout guard is disabled in this case.
**Evidence**: Line 162 comment: "Returns False if context is None (no timeout enforcement)."
**Recommended guard**: Integration test should verify timeout behavior with mock context object, not `None`.

## Knowledge Gaps

- The full static import graph was not regenerated from source (the deferred import count of 21 E402 sites is directly measured; prior "915" figure from old analysis was likely counting all deferred-style imports including TYPE_CHECKING blocks, not just E402 violations).
- `automation/pipeline.py` vs `lifecycle/engine.py` specific behavioral differences were not traced in detail. The "essential pipeline differences" referenced in TENSION-007 are not enumerated.
- The `src/autom8_asana/resolution/` package was not audited for tension patterns -- it contains `strategies.py` that may have overlap with `services/universal_strategy.py`.
- Lambda handler RISK zones were partially audited; full event-payload shape validation gaps in `cache_invalidate.py` and `workflow_handler.py` were not traced.
- The 269 `# type: ignore` count includes test files; production-only count was not isolated.
