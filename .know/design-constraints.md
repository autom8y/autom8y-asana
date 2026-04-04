---
domain: design-constraints
generated_at: "2026-04-04T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "55aaab5"
confidence: 0.82
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

### TENSION-001: Dual Config System -- Domain Dataclasses vs Platform Primitives

**Location**: `src/autom8_asana/config.py` (lines 22-65), `src/autom8_asana/transport/config_translator.py`

The codebase maintains two parallel configuration hierarchies for the same transport concerns. `config.py` declares `RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, and `CircuitBreakerConfig` as domain dataclasses. Simultaneously, `autom8y_http` exports platform equivalents.

The `ConfigTranslator` class exists solely to translate between the two.

**Constraint**: Do not consolidate these configs without a phased migration. Callers across 200+ files depend on the domain dataclasses. Platform configs are for new code only (TDD-PRIMITIVE-MIGRATION-001 Phase 2).

---

### TENSION-002: Services Layer Imports from API Layer (Intentional Violation)

**Location**: `src/autom8_asana/services/intake_create_service.py:23`, `src/autom8_asana/services/matching_service.py:20`, `src/autom8_asana/services/intake_resolve_service.py:17`, `src/autom8_asana/services/intake_custom_field_service.py:16`

Services import request/response models from the API routes layer, inverting the expected dependency direction. Marked with custom semgrep rule suppression `nosemgrep: autom8y.no-lower-imports-api`.

**Constraint**: Extracting service contracts to a shared `models/contracts/` location would break API layer callers. Accepted violation locked in by API-first schema design.

---

### TENSION-003: Models Layer Importing from Persistence Layer

**Location**: `src/autom8_asana/models/task.py:413-416`, `src/autom8_asana/models/custom_field_accessor.py:423`

`Task` and `CustomFieldAccessor` use deferred `TYPE_CHECKING`-guarded imports from `persistence.session` and `persistence.exceptions`, suppressed with `nosemgrep: autom8y.no-models-import-upper`.

**Constraint**: These lazy imports are load-bearing for the SaveSession pattern (`ADR-0050`). Removing them requires refactoring the session-commit protocol.

---

### TENSION-004: Lambda Handlers as Service-Layer Overflow

**Location**: `src/autom8_asana/lambda_handlers/pipeline_stage_aggregator.py:14-16`, `src/autom8_asana/lambda_handlers/reconciliation_runner.py:11-12`, `src/autom8_asana/lambda_handlers/push_orchestrator.py:8-9`

Three modules that logically belong in `services/` live in `lambda_handlers/` because moving them creates circular dependencies. Each module's docstring explains.

**Constraint**: Circular import structure prevents proper module placement. Resolving requires either inversion of control or introduction of an intermediate abstraction.

---

### TENSION-005: Entity Classes Duplicate Project GIDs from Registry

**Location**: `src/autom8_asana/core/project_registry.py`, `src/autom8_asana/models/business/*.py`

`core/project_registry.py` is the declared "single source of truth" for Asana project GIDs, yet 15+ entity classes maintain their own hardcoded `PRIMARY_PROJECT_GID` class attributes with raw GID strings.

**Constraint**: Migration blocked by test and call site count. Parity enforced via `tests/unit/core/test_project_registry.py:313`. Any GID change requires updating both locations.

---

### TENSION-006: autom8y_interop Protocol Gap -- DataServiceClient Coverage Only 30%

**Location**: `src/autom8_asana/automation/workflows/protocols.py:41-44`, `src/autom8_asana/automation/workflows/bridge_base.py:29-38`

`autom8y_interop` SDK protocols cover ~30% of `DataServiceClient` surface. No interop reconciliation protocol, no interop export protocol.

**Constraint**: Full migration blocked until upstream `autom8y_interop` adds `DataReconciliationProtocol` and export protocols.

---

### TENSION-007: Polars-Primary DataFrame Layer with Pandas Backward-Compat Bridge

**Location**: `src/autom8_asana/clients/data/models.py:283-292`

The data layer is Polars-native, but `InsightsResponse.to_pandas()` provides backward-compatibility for pre-Polars consumers. Marked "Per TDD-INSIGHTS-001 FR-005.5."

**Constraint**: Removing `to_pandas()` would break external consumers. Must persist until all callers are Polars-compatible.

---

## Trade-off Documentation

### TRADE-001: raw=True Dual-Return Type on All Asana Clients

All 12 `*Client` classes implement `raw: bool = False` on read methods. When `raw=True`, methods return raw `dict` instead of typed Pydantic models. Maintains backward compatibility with pre-typing callers.

**Cost**: Every read method carries dual return-type complexity. Removing requires auditing all callers of 12 client classes.

---

### TRADE-002: Circuit Breaker Disabled by Default

`CircuitBreakerConfig.enabled = False` (opt-in). `src/autom8_asana/config.py:291-297`: "default False for backward compat."

**Cost**: New deployments do not get circuit breaker protection unless they explicitly opt in.

---

### TRADE-003: AIMD Adaptive Semaphore with Unused Cooldown Parameter

`ConcurrencyConfig.aimd_cooldown_duration_seconds` exists but the adaptive semaphore logs `"cooldown_not_active_in_v1"`. Reserved for future AIMD v2.

**Location**: `src/autom8_asana/config.py:207`, `src/autom8_asana/transport/adaptive_semaphore.py:60,339`

---

### TRADE-004: Broad Except Catches Annotated as Intentional (BROAD-CATCH)

213 `except Exception` / `except:` sites exist. Lambda handlers annotated with `# BROAD-CATCH: {rationale}`. 12 bare-except sites in preload tagged for `I6` narrowing.

**Cost**: Static analysis cannot distinguish intentional from accidental broad catches.

---

### TRADE-005: ADR-0025 Big-Bang S3 Cutover -- No Fallback

The migration from legacy S3-based caching to Redis uses a big-bang cutover strategy with no S3 fallback. Initial cache miss spike of 100% at T+0. Requires cache warming to recover.

---

### TRADE-006: max_batch_size >= 500 Constraint Coupling

`DataServiceConfig.max_batch_size = 500` has a hard minimum enforced only by comment. `DataServiceJoinFetcher` depends on this being >= 500 to avoid extra chunking rounds.

**Location**: `src/autom8_asana/clients/data/config.py:252-256`

---

## Abstraction Gap Mapping

### GAP-001: Missing Consultation ProcessType Model

**Location**: `src/autom8_asana/services/intake_create_service.py:46-48`, `src/autom8_asana/models/business/process.py:51`

`VALID_PROCESS_TYPES` contains `{"sales", "retention", "implementation"}` with TODO for "consultation". `ProcessType` enum lacks `CONSULTATION` variant. Intake route cannot route consultation processes.

---

### GAP-002: Reconciliation Section GIDs Are Unverified Placeholders

**Location**: `src/autom8_asana/reconciliation/section_registry.py:94-143`

`EXCLUDED_SECTION_GIDS` and `UNIT_SECTION_GIDS` are `VERIFY-BEFORE-PROD (SCAR-REG-001)` — sequential placeholder values not verified against the live Asana API. Self-detection logic (`_looks_like_placeholder_gids()`) logs warnings.

---

### GAP-003: TieredCacheProvider S3 Cold Tier Is Phase 3 (Not Implemented)

**Location**: `src/autom8_asana/cache/integration/factory.py:208,216-217`, `src/autom8_asana/cache/providers/tiered.py:66-73`

`TieredCacheProvider` architecturally supports Redis (hot) + S3 (cold), but the factory only wires Redis: "For Phase 1, tiered maps to Redis (S3 cold tier is Phase 3)."

---

### GAP-004: DataServiceClient / autom8y_interop Protocol Gaps

**Location**: `src/autom8_asana/automation/workflows/protocols.py:34-44`

Two bridge-specific capabilities have no interop analogue: `get_reconciliation_async()` and `get_export_csv_async()`. Requires upstream PRs.

---

### GAP-005: Metrics Layer Phase 1 -- Section Scoping Not Fully Implemented

**Location**: `src/autom8_asana/metrics/metric.py:28-30`

`Metric.scope.section_name` supports "offer" only in Phase 1. `None` means "all sections" (not implemented).

---

### GAP-006: EntityType Binding Uses object.__setattr__ on Frozen Dataclasses

**Location**: `src/autom8_asana/core/entity_registry.py:851-890`

`EntityDescriptor` instances are `@dataclass(frozen=True)`, but `_bind_entity_types()` mutates them at module load via `object.__setattr__()`. Documented as intentional per ADR-001. `entity_type` typed as `Any = None` to avoid circular import.

---

### GAP-007: Deferred EntityType Binding to Break core -> models Circular Import

**Location**: `src/autom8_asana/core/entity_registry.py:140,851-853`

`EntityDescriptor.entity_type` typed as `Any = None` (not `EntityType | None`) to avoid `core -> models` circular imports. Binding deferred to module load.

---

## Load-Bearing Code Identification

### LBC-001: EntityRegistry Singleton -- Import-Time Validation Gate

**Location**: `src/autom8_asana/core/entity_registry.py:896-1062`

Built at module import time via `_validate_registry_integrity()`. 7 integrity checks. Failure raises `ValueError` at import time, preventing startup.

**Load-bearing for**: All DataFrame layer consumers, cache warming, API startup.

---

### LBC-002: ENTITY_DESCRIPTORS Tuple -- Single Declaration Per Entity

**Location**: `src/autom8_asana/core/entity_registry.py`

All entity metadata declared once. Backward-compatible facades (`ENTITY_TYPES`, `DEFAULT_ENTITY_TTLS`, `ENTITY_ALIASES`, `DEFAULT_KEY_COLUMNS`) delegate to this. Adding a new entity requires one entry; removing breaks all facades.

---

### LBC-003: DEFAULT_ENTITY_TTLS in config.py -- Backward-Compatible Facade

**Location**: `src/autom8_asana/config.py:104-112`

Module-level computed constant delegating to `EntityRegistry`. Import shim for legacy code. Removing breaks any code importing from `autom8_asana.config`.

---

### LBC-004: EXCLUDED_SECTION_NAMES -- Reconciliation Firewall

**Location**: `src/autom8_asana/reconciliation/section_registry.py:109-120`

"DO NOT use `UNIT_CLASSIFIER.ignored` as the exclusion source." `EXCLUDED_SECTION_NAMES` with all 4 values prevents reconciliation from processing units in `Templates`, `Next Steps`, `Account Review`, `Account Error`. Replacing with `UNIT_CLASSIFIER.ignored` would silently pass 3/4 excluded sections.

---

### LBC-005: SWR_GRACE_MULTIPLIER and LKG_MAX_STALENESS_MULTIPLIER

**Location**: `src/autom8_asana/config.py:93-102`

`SWR_GRACE_MULTIPLIER = 3.0` (3x entity TTL for stale serving). `LKG_MAX_STALENESS_MULTIPLIER = 0.0` (unlimited Last-Known-Good fallback). Module-level constants affecting all cache staleness decisions.

---

### LBC-006: DataServiceConfig max_batch_size >= 500 Dependency

**Location**: `src/autom8_asana/clients/data/config.py:252-256`, `src/autom8_asana/query/fetcher.py:8`

No hard validation prevents reducing below 500, which silently breaks join fetcher batching.

---

### LBC-007: Cascade Warm-Up Ordering Validated at API Startup

**Location**: `src/autom8_asana/api/lifespan.py:242`, `src/autom8_asana/dataframes/cascade_utils.py:134-228`

`cascade_warm_phases()` computes topological ordering. If cascade provider ordering is incorrect, downstream field resolution fails silently.

---

### LBC-008: BROAD-CATCH in Lambda Handlers -- Isolation Invariant

**Location**: `src/autom8_asana/lambda_handlers/` (14 annotated sites)

The Lambda handler isolation pattern — every per-entity step catches `Exception` — is load-bearing. Removing causes single-entity failures to abort entire cache warming runs.

---

## Evolution Constraint Documentation

### EC-001: TDD-PRIMITIVE-MIGRATION-001 -- Transport Primitive Migration

Phase 2 (import platform configs for new code) is complete. Phase 3 (consolidate domain configs) has not started. New transport code should use platform configs; existing callers must not be changed without a migration sprint.

---

### EC-002: Project GID Migration -- Entity Classes to Project Registry

15+ entity classes hold hardcoded GID strings duplicating `project_registry.py`. Parity enforced by tests. Migration to have entity classes reference the registry directly is documented but not started.

---

### EC-003: Cache Architecture Phase Roadmap

- **Phase 1** (current): Redis hot tier only
- **Phase 3** (planned): S3 cold tier wired into `TieredCacheProvider`

---

### EC-004: Consultation ProcessType -- Blocked Model Landing

`VALID_PROCESS_TYPES` artificially restricted. Requires `CONSULTATION` variant in `ProcessType` enum and intake flow extension.

---

### EC-005: autom8y_interop Partial Migration -- Blocked on Upstream PRs

`DataServiceClient` cannot be migrated to interop protocols until upstream adds `DataReconciliationProtocol` and export protocol.

---

### EC-006: Exception Narrowing in Preload (I6 Backlog)

12 bare-except sites in preload code tagged for `I6 (Exception Narrowing)` sprint item, which has not run.

---

### EC-007: Reconciliation Section GIDs -- Production Verification Required

All section GIDs are sequential placeholders. Production deployment requires API verification via `GET /projects/1201081073731555/sections`.

---

## Risk Zone Mapping

### RISK-001: Reconciliation Uses Unverified Section GIDs (SCAR-REG-001)

**Severity**: High. Placeholder GIDs for section exclusion and targeting. Misfire risk in production.

**Location**: `src/autom8_asana/reconciliation/section_registry.py:94-143`

**Mitigation**: `_looks_like_placeholder_gids()` emits warning with `"action_required": "verify_gids_against_asana_api_before_production"`.

---

### RISK-002: Phantom Exclusion Rate in Reconciliation (TC-4)

**Severity**: Medium. Production smoke test produced 756 phantom exclusions (~100% exclusion rate). Warning threshold: 50%.

---

### RISK-003: Circular Import Structure -- Hidden Coupling Debt

**Severity**: Medium. Three `lambda_handlers/` modules misplaced due to circular imports. Multiple `TYPE_CHECKING`-guarded lazy imports across layers. Each represents frozen coupling blocking clean evolution.

---

### RISK-004: config.py Module-Level Computation at Import Time

**Severity**: Medium. `DEFAULT_ENTITY_TTLS` computed at module-level via `_get_entity_registry()`. If `EntityRegistry` initialization fails, importing `autom8_asana.config` fails with `ValueError`.

**Location**: `src/autom8_asana/config.py:106-112`

---

### RISK-005: DataServiceConfig max_batch_size Has No Minimum Enforcement

**Severity**: Low-Medium. The >= 500 constraint for `DataServiceJoinFetcher` is enforced only by comment.

**Location**: `src/autom8_asana/clients/data/config.py:252-256`

---

### RISK-006: object.__setattr__ on Frozen EntityDescriptors Is Order-Dependent

**Severity**: Low. Mutation must complete before any consumer reads. Guaranteed by module-level execution order.

---

### RISK-007: 12 Bare-Except Sites in Preload -- Exception Signal Loss

**Severity**: Low. Preload exceptions silently swallowed. Service reports `cache_ready=True` even when preload has failed silently.

---

## Knowledge Gaps

1. **Lifecycle YAML files**: Automation config references lifecycle stage YAML but no YAML schema was found in the repository.
2. **autom8y_http and autom8y_log internal contracts**: External packages used by 212+ files. Internal constraints not observable.
3. **INTEGRATE-ecosystem-dispatch Section 1.4**: Referenced in `protocols.py` but document not found in repository.
4. **Actual section GID values**: Real GIDs must be retrieved from live Asana API.
5. **ADR documents**: Numerous ADR references in code but no ADR directory found during this audit.
6. **DataServiceClient endpoint depth**: `clients/data/` package not fully read. Endpoint-level constraints partially captured.
