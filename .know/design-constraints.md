---
domain: design-constraints
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
confidence: 0.87
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "ccac1bdf21a076abac37f960cd0d2210bee78a023d780c7374cb6d5c087c9c5b"
---

# Codebase Design Constraints

## Tension Catalog Completeness

### Confirmed Accurate Tensions

**TENSION-001: Dual Config System — Domain Dataclasses vs Platform Primitives**
Location: `src/autom8_asana/config.py:22-65`, `src/autom8_asana/transport/config_translator.py`. The `ConfigTranslator` class translates between domain dataclasses (`RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `CircuitBreakerConfig`) and platform equivalents. Do not consolidate without phased migration; 200+ callers depend on domain dataclasses.

**TENSION-002: Services Layer Imports from API Layer (Intentional Violation)**
Location: `src/autom8_asana/services/intake_create_service.py:23`, `matching_service.py:21`, `intake_resolve_service.py:18`, `intake_custom_field_service.py:16`. Confirmed at runtime (bare imports, no TYPE_CHECKING guard, no nosemgrep annotation on the actual import lines — these four services import directly from `api/routes/*_models.py` without suppression annotations).

**TENSION-003: Models Layer Importing from Persistence Layer**
Location: `src/autom8_asana/models/task.py:406-409`, `models/custom_field_accessor.py:421`. Confirmed TYPE_CHECKING-guarded imports with `nosemgrep: autom8y.no-models-import-upper`. Load-bearing for SaveSession pattern.

**TENSION-004: Lambda Handlers as Service-Layer Overflow**
Location: `src/autom8_asana/lambda_handlers/pipeline_stage_aggregator.py:15`, `reconciliation_runner.py:11`. Both docstrings confirm placement in `lambda_handlers/` specifically to avoid circular dependencies.

**TENSION-005: Entity Classes Duplicate Project GIDs from Registry**
Location: `src/autom8_asana/core/project_registry.py`, `src/autom8_asana/models/business/*.py`. 15+ entity classes with hardcoded `PRIMARY_PROJECT_GID`. Parity enforced by `tests/unit/core/test_project_registry.py:313`.

**TENSION-006: autom8y_interop Protocol Gap — DataServiceClient Coverage Only 30%**
Location: `src/autom8_asana/automation/workflows/protocols.py:32-61`, `bridge_base.py:29-38`. Confirmed: `get_reconciliation_async()` at `clients/data/client.py:1209` and `get_export_csv_async()` at `clients/data/client.py:1145` have no interop analogues. Both are explicitly documented as bridge-specific gaps requiring upstream PRs.

**TENSION-007: Polars-Primary DataFrame Layer with Pandas Backward-Compat Bridge**
Location: `src/autom8_asana/clients/data/models.py`. `.to_pandas()` backward-compat bridge documented.

### TENSION-008 (Newly Identified): Auth Layer Importing from API Layer at Runtime

**Location**: `src/autom8_asana/auth/dual_mode.py:24`

`auth/dual_mode.py` imports `ApiAuthError` directly from `api/exception_types.py` at module load time — not TYPE_CHECKING-guarded, no nosemgrep suppression. `cache/dataframe/decorator.py:147,184,204,223` contains four inline function-body imports from `api/exception_types`. Both `auth/` and `cache/` layers have undocumented runtime dependencies on the `api/` layer.

**Constraint**: `api/exception_types.py` has become a cross-cutting exception registry accessed by lower layers. Moving `ApiAuthError` to the public exception hierarchy in `exceptions.py` is the clean resolution path, but the auth layer's dependency on FastAPI-specific error shapes may resist this.

**Resolution cost**: Medium. Requires creating a shared exception type in `core/exceptions.py` or `exceptions.py`, updating all callers in `api/`, `auth/`, and `cache/`, and verifying FastAPI exception handlers still catch the correct types.

## Trade-off Documentation

### Confirmed Trade-offs (TRADE-001 through TRADE-006)

- **TRADE-001**: `raw=True` dual-return type on all 12 `*Client` classes. Confirmed: 115 occurrences of `raw: bool` or `raw=True` across `src/autom8_asana/clients/`.
- **TRADE-002**: `CircuitBreakerConfig.enabled = False` opt-in. Confirmed at `src/autom8_asana/config.py:291-297`.
- **TRADE-003**: `ConcurrencyConfig.aimd_cooldown_duration_seconds` unused; adaptive semaphore logs `"cooldown_not_active_in_v1"`. Confirmed at `src/autom8_asana/transport/adaptive_semaphore.py:60,339`.
- **TRADE-004**: Broad-except sites in lambda handlers annotated `# BROAD-CATCH`. Current count: 22 BROAD-CATCH annotations in `lambda_handlers/` (prior `.know/` had stale count of 14). 152 total BROAD-CATCH marker occurrences codebase-wide.
- **TRADE-005**: ADR-0025 big-bang S3 cutover, no fallback. Referenced but ADR-0025 not in `.ledge/decisions/` (only ADR-0001–0003 present).
- **TRADE-006**: `DataServiceConfig.max_batch_size >= 500` constraint documented in `src/autom8_asana/query/fetcher.py:8-10`. Current code at `src/autom8_asana/clients/data/config.py:256-263` validates `max_batch_size >= 1` and `<= 1000`. The 500-threshold concern is real but code validation is at `>= 1`, not `>= 500`.

### Additional Trade-offs

**TRADE-007: Idempotency Middleware DynamoDB Silent Degradation**

Location: `src/autom8_asana/api/middleware/idempotency.py` and `src/autom8_asana/api/main.py:325`

`DynamoDBIdempotencyStore` degrades silently to passthrough on DynamoDB connectivity failures (read failure at line 277, claim failure at 339, finalize failure at 384, delete failure at 404). On degradation, `api/main.py:325` emits `idempotency_store_degraded` metric. The finalize failure case (SCAR-IDEM-001 at line 719) is most dangerous: DynamoDB failure during finalize means the idempotency key is not persisted and a client retry will re-execute the mutation. Code annotation states this is only acceptable for human callers or idempotent systems; S2S callers with strict-once semantics are at risk. `ADR-omniscience-idempotency Section 3.7` referenced but lives in agent memory (`.claude/agent-memory/`), not in `.ledge/decisions/`.

**Trade-off**: Availability over strict-once guarantee. DynamoDB outage converts idempotency layer to pass-through rather than rejecting requests — keeps API available at the cost of at-least-once semantics during DynamoDB unavailability.

**TRADE-008: Deprecated Query Endpoint Kept Until Sunset Date**

Location: `src/autom8_asana/api/routes/query.py:7,541,561,669`

`POST /v1/query/{entity_type}` is documented as deprecated with sunset `2026-06-01`. Legacy model classes preserved in the same file (`# Legacy models (for deprecated POST /{entity_type} endpoint)` at line 104). The metric `deprecated_query_endpoint_used` (line 669) tracks live usage. Legacy callers continue working past the architectural obsolescence of the flat-equality filter model, at the cost of maintaining dual code paths in `query.py`.

**Cost**: Coordinated removal cannot happen before `2026-06-01`. Any agent touching `query.py` must not remove the deprecated endpoint or its legacy model classes before that date.

## Abstraction Gap Mapping

### Confirmed Gaps

- **GAP-001**: Missing `CONSULTATION` variant in `ProcessType` enum. Confirmed at `src/autom8_asana/services/intake_create_service.py:46-48`.
- **GAP-002**: Reconciliation section GIDs are unverified placeholders. Confirmed at `src/autom8_asana/reconciliation/section_registry.py:57,79,94,128` with `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations.
- **GAP-003**: `TieredCacheProvider` S3 cold tier is Phase 3 — not implemented. Redis-only in factory.
- **GAP-004**: `DataServiceClient` / `autom8y_interop` protocol gaps for reconciliation and export. Confirmed at `src/autom8_asana/automation/workflows/protocols.py:32-61`.
- **GAP-005**: Metrics layer Phase 1, section scoping for "offer" only. Confirmed at `src/autom8_asana/metrics/metric.py:28-30`.
- **GAP-006**: `EntityDescriptor` frozen dataclass mutated at module load via `object.__setattr__()`. Confirmed at `src/autom8_asana/core/entity_registry.py:851-890`.
- **GAP-007**: `EntityDescriptor.entity_type` typed as `Any = None` to break `core -> models` circular import. Confirmed at `src/autom8_asana/core/entity_registry.py:140,851-853`.

### GAP-008: api/exception_types.py Used as Cross-Cutting Exception Registry

Location: `src/autom8_asana/api/exception_types.py`; callers: `auth/dual_mode.py:24`, `cache/dataframe/decorator.py:147,184,204,223`, `api/dependencies.py:37`, `api/routes/internal.py:20`

`exception_types.py` was placed in `api/` but has become a shared exception contract accessed by `auth/` and `cache/` layers at runtime. There is no shared `core/exceptions.py` or additions to `exceptions.py` for these types. Any rename or restructuring of `api/exception_types.py` requires coordinated updates across four files in three packages.

**Maintenance burden**: If FastAPI is replaced or `api/exception_types.py` is moved, all cross-layer callers silently break.

## Load-Bearing Code Identification

### Confirmed Load-Bearing Code

- **LBC-001**: `EntityRegistry` singleton built at import time with 7 integrity checks. Import failure = startup failure.
- **LBC-002**: `ENTITY_DESCRIPTORS` tuple — all entity metadata in one declaration; all backward-compat facades delegate to it.
- **LBC-003**: `DEFAULT_ENTITY_TTLS` in `config.py` — backward-compat import shim for legacy code.
- **LBC-004**: `EXCLUDED_SECTION_NAMES` at `src/autom8_asana/reconciliation/section_registry.py:109-120` — "DO NOT use `UNIT_CLASSIFIER.ignored`" warning still present.
- **LBC-005**: `SWR_GRACE_MULTIPLIER = 3.0` and `LKG_MAX_STALENESS_MULTIPLIER = 0.0` at `src/autom8_asana/config.py:93-102`.
- **LBC-006**: `DataServiceConfig.max_batch_size >= 500` for join fetcher (documented in `query/fetcher.py:8-10`).
- **LBC-007**: `cascade_warm_phases()` topological ordering at `src/autom8_asana/api/lifespan.py:242`.
- **LBC-008**: BROAD-CATCH isolation pattern in lambda handlers. Currently 22 annotated BROAD-CATCH sites.

### LBC-009: DynamoDBIdempotencyStore Degradation-to-Passthrough Pattern

Location: `src/autom8_asana/api/middleware/idempotency.py:277,339,384,404`

The four `except Exception` blocks in `DynamoDBIdempotencyStore` are load-bearing in the LBC-008 sense — removing or narrowing any of them could cause DynamoDB connectivity failures to propagate as HTTP 500s. The passthrough degradation is an intentional availability trade-off. The exception at line 384 (finalize) is flagged SCAR-IDEM-001 and carries the double-execution risk.

**Naive-fix failure mode**: Narrowing to `botocore.exceptions.ClientError` would break on connection timeout exceptions (different class hierarchy). Narrowing to `Exception` subclasses excluding `asyncio.CancelledError` would be correct but requires careful testing.

**Safe refactor**: Requires mapping all `botocore`/`aiobotocore` exception types and confirming `asyncio.CancelledError` propagates correctly.

## Evolution Constraint Documentation

### Confirmed Constraints

- **EC-001**: TDD-PRIMITIVE-MIGRATION-001 Phase 3 (config consolidation) not started.
- **EC-002**: Project GID migration (entity classes to registry) documented but not started.
- **EC-003**: Cache architecture Phase 1 (Redis hot tier only); Phase 3 (S3 cold tier) planned.
- **EC-004**: Consultation ProcessType blocked model landing.
- **EC-005**: `autom8y_interop` partial migration blocked on upstream PRs.
- **EC-006**: Exception narrowing in preload (I6 backlog) not yet run.
- **EC-007**: Reconciliation section GIDs require production API verification before deployment.

### EC-008: Deprecated Query Endpoint Frozen Until 2026-06-01

Location: `src/autom8_asana/api/routes/query.py:7,541`

`POST /v1/query/{entity_type}` is deprecated with explicit sunset `2026-06-01`. The endpoint and its legacy model classes must not be removed before that date. Callers are tracked via `deprecated_query_endpoint_used` metric. Today's date (2026-04-24) leaves approximately 38 days before removal is permitted.

**Changeability rating for `api/routes/query.py`**: coordinated — removing the deprecated endpoint requires verifying zero caller traffic via metric.

### EC-009: ADR-0001 secretspec Profile Split — Implemented

`.ledge/decisions/` contains ADR-0001 (secretspec profile split), ADR-0002 (bucket naming), ADR-0003 (bucket disposition). ADR-0001 implemented: `src/autom8_asana/metrics/__main__.py:19-49` references `[profiles.cli]` in `secretspec.toml` and implements the preflight check pattern.

**Changeability rating for `secretspec.toml`**: migration — changing `[profiles.cli]` required vars requires updating the inline fallback list in `metrics/__main__.py` and the `tests/unit/metrics/test_main.py::TestPreflightParity::test_inline_and_secretspec_enforce_same_required_vars` test simultaneously.

### EC-010: Python Version Constraint — No Upper Bound

Location: `pyproject.toml:10`

`requires-python = ">=3.12"` (upper bound `<3.14` was removed in commit `770c9cd6`). Linter config (`pyproject.toml:226-227`) still suppresses UP046/UP047 (PEP 695 type params) with stale comment "requires-python still >=3.11".

**Changeability rating for `pyproject.toml` requires-python**: safe — changing the lower bound is coordinated; adding an upper bound is safe.

## Risk Zone Mapping

### Confirmed Risk Zones

- **RISK-001**: Reconciliation placeholder GIDs (SCAR-REG-001) — confirmed 4 VERIFY-BEFORE-PROD annotations at `section_registry.py:57,79,94,128`. Severity: High.
- **RISK-002**: Phantom exclusion rate in reconciliation (TC-4). Severity: Medium.
- **RISK-003**: Circular import structure — 3 misplaced `lambda_handlers/` modules + TYPE_CHECKING-guarded lazy imports. Severity: Medium.
- **RISK-004**: `config.py` module-level computation at import time. Severity: Medium.
- **RISK-005**: `DataServiceConfig.max_batch_size` has no 500-minimum enforcement (only `>= 1` validated). Severity: Low-Medium.
- **RISK-006**: `object.__setattr__()` on frozen `EntityDescriptors` is order-dependent. Severity: Low.
- **RISK-007**: ~10 broad-except sites in preload (`legacy.py: 5`, `progressive.py: 5`). Severity: Low.

### RISK-008: SCAR-IDEM-001 — Idempotency Finalize Failure Causes Double-Execution for S2S Callers

Location: `src/autom8_asana/api/middleware/idempotency.py:719`

SCAR-IDEM-001: if `DynamoDBIdempotencyStore.finalize()` raises, the idempotency key is not persisted. A client retry will re-execute the mutation. The annotation states this is acceptable only for human callers or idempotent systems; S2S callers with strict-once semantics are at double-execution risk.

**Missing guard**: no metric specifically for finalize failure (the broader `idempotency_store_degraded` at `api/main.py:325` covers initialization failure, not finalize failure).

**Recommended guard**: add `metrics.increment("idempotency_finalize_failure")` at the finalize except block and promote exception logging level from implicit (caught silently) to explicit warning.

**Cross-reference**: relates to TENSION-008 and TRADE-007.

### RISK-009: Cache Backends — STRICT Freshness Caller-Responsibility Assumption

Location: `src/autom8_asana/cache/backends/redis.py:432`, `src/autom8_asana/cache/backends/s3.py:505`

Both Redis and S3 backends document: "For STRICT freshness, caller must validate against source." No enforcement of this contract — callers can request `STRICT` freshness and receive data without the backend verifying the caller has validated freshness. Silent responsibility handoff.

**Recommended guard**: consider adding a validation callback to the cache read path for `STRICT` freshness policy consumers, or document accepted callers explicitly.

**Cross-reference**: relates to RISK-002 — if reconciliation uses STRICT freshness without proper source validation, phantom exclusions can result from stale data.

## Knowledge Gaps

1. **Lifecycle YAML files**: Still not found. YAML-based automation config schema unlocated in repository.
2. **autom8y_http and autom8y_log internal contracts**: External packages. Not observable from this audit.
3. **INTEGRATE-ecosystem-dispatch Section 1.4**: Not found in repository.
4. **Actual section GID values**: Still require live Asana API verification via `GET /projects/1201081073731555/sections`.
5. **ADR documents partial**: `.ledge/decisions/` contains ADR-0001, ADR-0002, ADR-0003. ADR-0025 (S3 cutover), ADR-I6-001, ADR-omniscience-idempotency, ADR-S2S-001/002 referenced in code but not present in `.ledge/decisions/` — may live in `.claude/agent-memory/`.
6. **DataServiceClient endpoint depth**: Partially resolved via TENSION-006 and GAP-004.
7. **TENSION-002 nosemgrep annotation absence**: The four services-layer imports from API layer lack nosemgrep suppression — semgrep likely flags these as violations in CI.
8. **ADR-omniscience-idempotency in agent memory, not .ledge/decisions/**: `idempotency.py:3` references it as canonical; its Section 3.7 describes SCAR-IDEM-001 risk zone. Agents cannot follow the link without searching `.claude/agent-memory/`.
