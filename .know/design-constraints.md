---
domain: design-constraints
generated_at: "2026-05-04T00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./pyproject.toml"
  - "./.github/workflows/*.yml"
  - "./.ci/semantic-baseline.json"
generator: theoros
source_hash: "20ef7952"
confidence: 0.93
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Design Constraints

> Regenerated 2026-05-04 (FULL mode). Source hash: `20ef7952`. Prior source hash: `6b303485`.
> All prior TENSIONs, LBCs, ECs, and RISKs preserved with post-diff anchor verification.
>
> **KEY UPDATES vs `6b303485`**:
> - M-02 confirmed PASSING (0.5266, pass: true) — RISK-012 status updated to prospective-only
> - M-07_constraint_coverage is now the active failing metric (0.5714, floor: 0.6, pass: false)
> - `SystemContext._reset_registry` is now a per-xdist-worker dict (was a flat list) — **new LBC-012**
> - `ExportsSuccessResponse` added to `api/models.py` — **new load-bearing schema surface** (LBC-013)
> - Gitleaks workflow gained concurrency control (group: `gitleaks-${{ github.ref }}`, cancel-in-progress: true) — new CI operational constraint
> - UP046/UP047 ruff suppression comments at `pyproject.toml:227-228` remain stale (`requires-python = ">=3.12"` not `>=3.11`)
> - New ADRs landed: ADR-008 through ADR-013 (runner sizing, xdist, shard expansion, post-merge coverage, path-b scaffold, hadolint)
> - SCAR test cluster expanded: 35 tests bear `@pytest.mark.scar` (was documented as 33)

## Tension Catalog

**TENSION-001: Dual Config System — Domain Dataclasses vs Platform Primitives**
Location: `src/autom8_asana/config.py:22-65`, `src/autom8_asana/transport/config_translator.py`.
The `ConfigTranslator` translates between domain dataclasses (`RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `CircuitBreakerConfig`) and platform equivalents. Do not consolidate without phased migration; 200+ callers depend on domain dataclasses.
Trade-off: Current state persists because the platform primitives predate the domain model — migrating all callers is an initiative-scale effort (EC-001 TDD-PRIMITIVE-MIGRATION-001 Phase 3 not started). Resolution cost: High.

**TENSION-002: Services Layer Imports from API Layer (Intentional Violation)**
Location: `src/autom8_asana/services/intake_create_service.py:23`, `matching_service.py:21`, `intake_resolve_service.py:18`, `intake_custom_field_service.py:16`. Confirmed at runtime (bare imports, no TYPE_CHECKING guard, no nosemgrep annotation on the actual import lines). Semgrep likely flags these 4 files on every CI run. Models are co-located in `api/routes/` because they were initially handler-local; extraction requires a coordinated models migration.
Trade-off: Model extraction would require touching multiple service and route files simultaneously. No planned migration. Resolution cost: Medium.

**TENSION-003: Models Layer Importing from Persistence Layer**
Location: `src/autom8_asana/models/task.py:406-409`, `models/custom_field_accessor.py:421`. Confirmed TYPE_CHECKING-guarded imports with `nosemgrep: autom8y.no-models-import-upper`. Load-bearing for SaveSession pattern.
Trade-off: SaveSession requires both model and persistence types at the call site; the TYPE_CHECKING guard avoids runtime circularity while satisfying mypy. Resolution cost: Medium (requires redesigning SaveSession signature).

**TENSION-004: Lambda Handlers as Service-Layer Overflow**
Location: `src/autom8_asana/lambda_handlers/pipeline_stage_aggregator.py:15`, `reconciliation_runner.py:11`. Both docstrings confirm placement to avoid circular dependencies.
Trade-off: Lambda handlers import from services and models layers; placing them in `lambda_handlers/` breaks the circular dependency that would arise if they lived in `services/`. Resolution cost: Low to medium (requires clear service boundary definition).

**TENSION-005: Entity Classes Duplicate Project GIDs from Registry**
Location: `src/autom8_asana/core/project_registry.py`, `src/autom8_asana/models/business/*.py`. 15+ entity classes with hardcoded `PRIMARY_PROJECT_GID`. Parity enforced by `tests/unit/core/test_project_registry.py:313`.
Trade-off: Duplication is acknowledged but removal would break backward-compat facades. Test guard prevents divergence but does not eliminate the dual-source-of-truth. Resolution cost: Medium (EC-002 documented but not started).

**TENSION-006: autom8y_interop Protocol Gap — DataServiceClient Coverage Only 30%**
Location: `src/autom8_asana/automation/workflows/protocols.py:32-61`, `bridge_base.py:29-38`. `get_reconciliation_async()` at `clients/data/client.py:1209` and `get_export_csv_async()` at `clients/data/client.py:1145` have no interop analogues. Both documented as bridge-specific gaps requiring upstream PRs.
Trade-off: `autom8y_interop` is an external dependency; adding methods requires upstream PRs in another repository. Current state persists because upstream prioritization is external. Resolution cost: High (cross-repo coordination, EC-005).

**TENSION-007: Polars-Primary DataFrame Layer with Pandas Backward-Compat Bridge**
Location: `src/autom8_asana/clients/data/models.py`. `.to_pandas()` backward-compat bridge documented.
Trade-off: Migration to Polars was intentional for performance. Bridge exists for callers that predate the migration. Resolution cost: Low (bridge can be removed when all callers migrate).

**TENSION-008: Auth Layer Importing from API Layer at Runtime**
Location: `src/autom8_asana/auth/dual_mode.py:24`. Imports `ApiAuthError` directly from `api/exception_types.py` at module load time — not TYPE_CHECKING-guarded, no nosemgrep suppression. `cache/dataframe/decorator.py:147,184,204,223` contains four inline function-body imports from `api/exception_types`. Both `auth/` and `cache/` layers have undocumented runtime dependencies on the `api/` layer.
Resolution path: Move `ApiAuthError` to public exception hierarchy in `core/exceptions.py` or root `exceptions.py`. Resolution cost: Medium. Cross-reference: GAP-008.

**TENSION-009: Exports Route Mount-Order Load-Bearing Constraint**
Location: `src/autom8_asana/api/main.py:431-441`. `exports_router_v1` and `exports_router_api_v1` MUST mount BEFORE `query_router` in FastAPI router registration order. `query_router` uses wildcard `/v1/query/{entity_type}` that would match `/v1/exports` if mounted later. The constraint mirrors the same ordering for `fleet_query_router_v1` / `fleet_query_router_api_v1`. Post-diff verification at `20ef7952`: ordering confirmed at lines 431-441 with comment `"Mount BEFORE query_router"`.
Resolution cost: Low (comment documents discipline). Forgetting the order is silent-failure risk; not structurally enforced.

**TENSION-010: ExportOptions extra="allow" — Phase 2 Forward-Binding Contract Lock**
Location: `src/autom8_asana/api/routes/exports.py:141`. `ExportOptions.model_config = ConfigDict(extra="allow")` is explicitly marked P1-C-02 BINDING. Must NOT be changed to `extra="forbid"` — would foreclose Phase 2 `predicate_join_semantics` field per LEFT-PRESERVATION GUARD ADR (mechanism (b) escape valve at `ADR-engine-left-preservation-guard.md §4.1`). Documented in code comments and confirmed at `exports.py:141` at `20ef7952`.
Resolution cost: Nil for Phase 1. Phase 2: promote `predicate_join_semantics` to typed `Literal` field, tension dissolves.

**TENSION-011: ExportsSuccessResponse extra="ignore" vs Fleet SuccessResponse Convention** [NEW at `20ef7952`]
Location: `src/autom8_asana/api/models.py:121`. `ExportsSuccessResponse` overrides `SuccessResponse` with `extra="ignore"` rather than the fleet default. This is intentional (schema-only typing over wire payload) but deviates from the parent class's open policy.
Trade-off: The override prevents mypy/Pydantic complaints when the exports handler wraps a `list[dict]` in the standard envelope. Tightening or relaxing the parent `SuccessResponse` would require re-examining this subclass. Resolution cost: Low.

**TENSION-012: UP046/UP047 Ruff Suppression Comments Stale**
Location: `pyproject.toml:227-228`. Comments say `"requires-python still >=3.11"` but `pyproject.toml:10` now reads `requires-python = ">=3.12"`. The suppressions are harmless but misleading — they cite a Python version constraint that no longer exists.
Resolution cost: Trivial (comment update only).

## Operational Constraints (process and platform)

These constraints are out-of-tree (rite-platform) or CI-enforced, not code-anchored. They govern process behavior affecting codebase integrity.

**HYG-001: Pre-S4 Hygiene Gate Must Verify Untracked Test Files**
Type: Operational constraint (rite-platform)
Anchor: Incident-of-record: Sprint-3 hygiene rite issued APPROVED on PR-38 branch when 5 test files (`tests/unit/api/test_exports_*.py`) were untracked. Post-PR38, 6 files are committed. The hygiene rite audit-lead rendered APPROVED against a substrate-blind ground truth.
Constraint: Hygiene S4 audit-lead pre-gate MUST run `git ls-files --others --exclude-standard tests/` and if non-empty halt with `RITE-SUBSTRATE-REFUSED: untracked test files present` before issuing APPROVED verdict.
Owner-rite: knossos platform / hygiene-pass-2
Severity: P1 (recurrence risk confirmed)
Cross-reference: RITE-SUBSTRATE-INTEGRITY-001

**RITE-SUBSTRATE-INTEGRITY-001: Pre-S0 Dirty-Tree Halt for ari sync**
Type: Meta-constraint (rite-platform)
Anchor: IC SEV-2 incident 2026-04-28. `ari sync --rite X` on a dirty working tree permitted multi-rite verdicts to render against substrate-blind ground truth.
Constraint: `ari sync` pre-flight MUST run `git status --porcelain` and emit `RITE-SUBSTRATE-REFUSED: working tree dirty` + halt when dirty.
Owner-rite: knossos platform / forge eval-specialist
Severity: P1
Operational consequence: Any `ari sync` verdict issued against a dirty tree is unreliable and must be treated as invalid.

**M02-MONITOR-001: M-02 Score CI Tripwire — DISCHARGED 2026-04-29**
Type: Observability constraint (CI)
Status: **DISCHARGED via HYG-T1 commit `7dd9aa5d`** (2026-04-29). Empirical recompute at `20ef7952`: M-02 = 99/188 = 0.5266 (above 0.5 floor, pass: true). Confirmed in `.ci/semantic-baseline.json:12-19`.
Residual concern (carry-forward): `aegis-check.py` does NOT enforce `examples=` count. Future PRs removing `examples=` declarations will not be caught until a manual baseline refresh.
Severity: P3 (was P1 — downgraded; no active breach)
Deadline: Sprint-4 (advisory)

**M07-MONITOR-001: M-07 Constraint Coverage CI Tripwire — ACTIVE BREACH** [NEW at `20ef7952`]
Type: Observability constraint (CI)
Anchor: `.ci/semantic-baseline.json:52-59`
Status: **FAILING**. M-07 score = 0.5714 (numerator: 4/7, floor: 0.6, pass: false). `regression_safe: true` flag set — the baseline marks this as a known floor violation but not a regression blocker.
Evidence: `floor_violations: ["M-07_constraint_coverage"]`. `aegis-check.py` reports this but CI is set `regression_safe: true` (does not block PRs). The 3 uncovered constraint slots are unknown without re-running `aegis-check.py` against the spec.
Severity: P2 (active floor violation; CI not blocking due to `regression_safe: true`)
Deadline: Sprint-4 (before re-baselining)
Cross-reference: RISK-013 (new RISK entry below)

**WORKTREE-001: Parallel-Worktree Contamination Protocol Absent**
Type: Operational constraint (development hygiene)
Anchor: `.worktrees/` directory (gitignored). Uncommitted Sprint-3 wiring on a hygiene branch contributed to the IC SEV-2 dirty-tree incident.
Constraint: Apply `parallel-wave-close-consolidation-protocol` at each session-wrap; audit `.worktrees/` for stale checkouts older than 7 days.
Owner-rite: naxos / Sprint-4 cleanup
Severity: P2
Cross-reference: RITE-SUBSTRATE-INTEGRITY-001

**FROZEN-RANGE-IMPORTERS-001: Frozen-Range Importer Catalog**
Type: Structural constraint (blast-radius mapping)
Frozen modules (P1-C-04 per `api/routes/exports.py:14`):
- `src/autom8_asana/query/engine.py:139-178,181` (execute_rows steps 6-9, aggregate logic)
- `src/autom8_asana/query/join.py` (full module)
- `src/autom8_asana/query/compiler.py:53-63,192-241` (OPERATOR_MATRIX + _compile_node + _compile_comparison)

Importer catalog (verified at `20ef7952`):
- `src/autom8_asana/api/routes/exports.py:66` — imports `PredicateCompiler` from `query.compiler`
- `src/autom8_asana/api/routes/query.py:38` — imports `QueryEngine` from `query.engine`
- `src/autom8_asana/query/__init__.py:17-18,38` — re-exports `PredicateCompiler`, `QueryEngine`, `execute_join`
- `src/autom8_asana/query/__main__.py:513,669,1025` — lazy-imports `QueryEngine` in CLI subcommands (3 sites)
- `src/autom8_asana/services/query_service.py:238` — lazy-imports `strip_section_predicates` from `query.compiler`

Constraint: Any modification to P1-C-04 frozen ranges must be cross-referenced against this importer list to assess blast radius.
Severity: Structural — permanent design constraint
Cross-reference: EC-011, SCAR-DISCRIMINATOR-001

**FLEET-SHA-SKEW-001: autom8y-workflows Security SHA Skew Across Fleet**
Type: Operational constraint (fleet security posture)
Anchor: `.github/workflows/gitleaks.yml`, `trufflehog-scan.yml`, `dependency-review.yml`, `zizmor.yml` in autom8y-asana — all four pin `autom8y/autom8y-workflows/...@44b771e516a49a0d964782e4bbd0f0e39b2f97a1`. Scorecard workflow pins `c77acb0cf9e48b17f08180d54e24086016706856`.
Skew surface: 4-of-5 security workflows trail the fleet SHA.
Constraint: Fleet should converge on a single autom8y-workflows SHA. SHA bump must be atomic across affected repos.
Severity: P2 (security workflow versions diverge; no CI enforcement)
Owner-rite: /arch (cadence) or /sre (direct execution)

**DEFER-WATCH-REGISTRY-001: Active Defer-Watch Entries — Cross-Reference**
Type: Informational constraint (deferred-scope registry)
See `.know/architecture.md` §Defer-Watch Active Entries for canonical cross-reference.
Active entries as of 2026-04-29 close (2 total, both KEEP-OPEN per EUN-005 audit):
- `DEFER-WS4-T3-2026-04-29`: autom8y_log SDK stdlib interface gap; watch_trigger 2026-05-29; escalation: rnd-rite
- `lockfile-propagator-prod-ci-confirmation`: Notify-Satellite-Repos green pending; watch_trigger 2026-05-29; deadline 2026-07-29; escalation: 10x-dev rite

**CI-CONCURRENCY-001: Gitleaks Workflow Concurrency Control** [NEW at `20ef7952`]
Type: Operational constraint (CI)
Anchor: `.github/workflows/gitleaks.yml:3-5`.
`concurrency: group: gitleaks-${{ github.ref }}, cancel-in-progress: true` added by commit `20ef7952`. Only `gitleaks.yml` has this control among the 4 security workflows. `trufflehog-scan.yml`, `dependency-review.yml`, and `zizmor.yml` lack equivalent concurrency guards.
Constraint: Gitleaks is now safe from concurrent runs on the same branch. The other 3 security workflows can still queue multiple simultaneous runs. Inconsistent concurrency posture across fleet security workflows.
Severity: P3 (informational; no active incident)
Cross-reference: FLEET-SHA-SKEW-001

## Trade-off Documentation

- **TRADE-001**: `raw=True` dual-return type on all 12 `*Client` classes. 115 occurrences of `raw: bool` or `raw=True` across `src/autom8_asana/clients/`. Current state: convenience API that returns either raw JSON or domain objects. Ideal: separate methods. Why current persists: legacy callers throughout automation layer. ADR: none.
- **TRADE-002**: `CircuitBreakerConfig.enabled = False` opt-in. Confirmed at `config.py:291-297`. Current state: circuit breaker off by default. Ideal: default-on resilience. Why: avoiding circuit breaker complexity during build-out phase.
- **TRADE-003**: `ConcurrencyConfig.aimd_cooldown_duration_seconds` unused; adaptive semaphore logs `"cooldown_not_active_in_v1"`. Confirmed at `transport/adaptive_semaphore.py:60,339`. Why: Phase 1 of adaptive semaphore doesn't implement full AIMD cooling.
- **TRADE-004**: Broad-except sites in lambda handlers annotated `# BROAD-CATCH`. Current count: 22 BROAD-CATCH annotations in `lambda_handlers/`; 158 total codebase-wide (up from 152). Why: Lambda handlers serve as blast-radius isolation; broad catches prevent unhandled exceptions from crashing the handler host.
- **TRADE-005**: ADR-0025 big-bang S3 cutover, no fallback. Referenced but ADR-0025 not in `.ledge/decisions/` (21 ADRs present, none numbered ADR-0025). May live in `.claude/agent-memory/`.
- **TRADE-006**: `DataServiceConfig.max_batch_size >= 500` constraint documented in `query/fetcher.py:8-10`. Current code at `clients/data/config.py:256-263` validates `>=1` and `<=1000`. The 500-threshold concern is real but code validation is at `>= 1`.
- **TRADE-007**: `DynamoDBIdempotencyStore` degrades silently to passthrough on connectivity failures. `api/main.py:339-344` emits `idempotency_store_degraded` warning and falls back to `NoopIdempotencyStore`.
- **TRADE-008: Deprecated Query Endpoint Kept Until Sunset Date.** `api/routes/query.py:7,541,561,669`. `POST /v1/query/{entity_type}` deprecated with sunset `2026-06-01`. Today (2026-05-04) leaves ~28 days. Metric `deprecated_query_endpoint_used` (line 669) tracks usage. Legacy model classes preserved until sunset.
- **TRADE-009: LEFT-PRESERVATION GUARD as NO-OP Structural Seam in Phase 1.** `api/routes/exports.py:236-284` (`_engine_call_with_left_preservation_guard`). Phase 1 ships single-entity exports — no LEFT JOIN fires, the GUARD is a structural NO-OP. Seam exists for Sprint 4 qa-adversary verification + Phase 2 architect inheritance. Per `ADR-engine-left-preservation-guard.md §4`.
- **TRADE-010: ESC-1 Date Predicates Under OR/NOT Unsupported in Phase 1.** `api/routes/_exports_helpers.py:369-417`. Date operators (`BETWEEN`, `DATE_GTE`, `DATE_LTE`) inside `OrGroup` or `NotGroup` rejected with `ValueError` in Phase 1. Restriction: extracting date Comparisons from OR/NOT semantics would alter boolean meaning.
- **TRADE-011: ExportsSuccessResponse Typed Schema Over Wire Envelope.** [NEW at `20ef7952`] `api/models.py:98-127`. The `ExportsSuccessResponse` subclass of `SuccessResponse[list[dict[str, Any]]]` exists purely to inject `examples=` for the M-02 semantic score metric. It uses `extra="ignore"` to avoid Pydantic validation failures when the wire response includes untyped dict fields. No runtime behavior change — schema-generation only. The `_exports_schema_extra` callable patches the `meta` property in the generated JSON schema. Why: M-02 score recovery after typed schema introduction in BLOCKING-1 amendment.

## Abstraction Gap Mapping

- **GAP-001**: Missing `CONSULTATION` variant in `ProcessType` enum. `services/intake_create_service.py:46-48`. Blocks Consultation flow until enum extended.
- **GAP-002**: Reconciliation section GIDs are unverified placeholders. `reconciliation/section_registry.py:57,79,94,128` with `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations. 4 locations confirmed.
- **GAP-003**: `TieredCacheProvider` S3 cold tier is Phase 3 — not implemented. Redis-only in factory. EC-003.
- **GAP-004**: `DataServiceClient` / `autom8y_interop` protocol gaps for reconciliation and export. `automation/workflows/protocols.py:32-61`. TENSION-006.
- **GAP-005**: Metrics layer Phase 1, section scoping for "offer" only. `metrics/metric.py:28-30`.
- **GAP-006**: `EntityDescriptor` frozen dataclass mutated at module load via `object.__setattr__()`. `core/entity_registry.py:851-890`. Order-dependent; test relies on stable import order.
- **GAP-007**: `EntityDescriptor.entity_type` typed as `Any = None` to break `core → models` circular import. `core/entity_registry.py:140,851-853`.
- **GAP-008: api/exception_types.py Used as Cross-Cutting Exception Registry.** Callers: `auth/dual_mode.py:24`, `cache/dataframe/decorator.py:147,184,204,223`, `api/dependencies.py:37`, `api/routes/internal.py:20`. Renaming requires coordinated updates across four files in three packages. Cross-reference TENSION-008.
- **GAP-009: Op Enum Has Date Operators Not Supported by PredicateCompiler.** `query/models.py:52-56` (`Op.BETWEEN`, `Op.DATE_GTE`, `Op.DATE_LTE`) exist in AST vocabulary but `PredicateCompiler` (P1-C-04 FORBIDDEN at `compiler.py:53-63,192-241`) does not handle them. The `/exports` handler explicitly strips date ops before calling `PredicateCompiler`.
- **GAP-010: SystemContext._reset_registry Per-Worker Isolation Carries Invisible State Risk.** [NEW at `20ef7952`] `core/system_context.py:33`. The registry is now a `dict[str, list[Callable]]` keyed by xdist worker ID. Outside xdist, all registrations go to key `"main"`. In xdist, each worker gets its own list. If a module is imported in the main process before workers fork, its `register_reset` call lands on `"main"` but workers won't inherit it (they run fresh). Registration-before-fork creates a silent gap. No test currently exercises this boundary.

## Load-Bearing Code Identification

- **LBC-001**: `EntityRegistry` singleton built at import time with 7 integrity checks. Import failure = startup failure. Dependents: all entity-typed routes, all dataframe strategies.
- **LBC-002**: `ENTITY_DESCRIPTORS` tuple — all entity metadata in one declaration; all backward-compat facades delegate to it. Safe refactor requires: replacing with registry factory + migration of all descriptor references.
- **LBC-003**: `DEFAULT_ENTITY_TTLS` in `config.py` — backward-compat import shim. Dependents: any caller using the old import path.
- **LBC-004**: `EXCLUDED_SECTION_NAMES` at `reconciliation/section_registry.py:109-120` — "DO NOT use `UNIT_CLASSIFIER.ignored`" warning. Naive "fix" to use classifier directly changes reconciliation logic.
- **LBC-005**: `SWR_GRACE_MULTIPLIER = 3.0` and `LKG_MAX_STALENESS_MULTIPLIER = 0.0` at `config.py:93-102`. Cache behavior semantics depend on these exact values; changing them is a behavioral regression risk.
- **LBC-006**: `DataServiceConfig.max_batch_size >= 500` for join fetcher. `query/fetcher.py:8-10`. Values below 500 cause join fetch failures; enforcement is only in docstring, not validation.
- **LBC-007**: `cascade_warm_phases()` topological ordering at `api/lifespan.py:242`. Wrong ordering causes cache warming failures at startup.
- **LBC-008**: BROAD-CATCH isolation pattern in lambda handlers. 22 annotated in `lambda_handlers/`; 158 total codebase-wide. Naive narrowing breaks handler isolation.
- **LBC-009: DynamoDBIdempotencyStore Degradation-to-Passthrough.** `api/middleware/idempotency.py:277,339,384,404`. Four `except Exception` blocks load-bearing. SCAR-IDEM-001 carries double-execution risk at line 384 (finalize). Naive narrowing to `botocore.exceptions.ClientError` would break on connection timeout exceptions.
- **LBC-010: ExportOptions extra="allow" Contract Lock.** `api/routes/exports.py:141`. Tightening to `"forbid"`/`"ignore"` would silently break Phase 2 callers passing `predicate_join_semantics` as untyped extra. Dependents: `ADR-engine-left-preservation-guard.md §4`, `exports.py:292-304`.
- **LBC-011: Router Registration Order in api/main.py.** `api/main.py:431-441`. `fleet_query_router_v1`, `fleet_query_router_api_v1`, `exports_router_v1`, `exports_router_api_v1` MUST register BEFORE `query_router`. Failure mode is silent at startup (no error), only manifests on first request to affected path. Confirmed at `20ef7952`.
- **LBC-012: SystemContext._reset_registry is now Per-Worker Dict.** [NEW at `20ef7952`] `core/system_context.py:33`. Changed from `list[Callable]` to `dict[str, list[Callable]]`. Callers invoking `SystemContext.reset_all()` outside xdist continue to work (key `"main"` is used). Any code that previously held a reference to the list or read `_reset_registry` directly is now broken. No known external callers access `_reset_registry` directly (private name), but this is load-bearing for test isolation across the full suite. Safe-refactor requirement: maintain `_worker_key()` contract if xdist environment detection logic changes.
- **LBC-013: ExportsSuccessResponse as Typed Schema Surface.** [NEW at `20ef7952`] `api/models.py:98-127`. `ExportsSuccessResponse` is now the `response_model=` for both `/v1/exports` and `/api/v1/exports` mounts (confirmed at `exports.py:515,547`). Changing the `data` field type or the `json_schema_extra` callable affects the generated OpenAPI spec and M-02 semantic score baseline. Dependents: `exports.py:515`, `exports.py:547`, `aegis-synthetic-coverage.yml`, `.ci/semantic-baseline.json`.

## Evolution Constraints

- **EC-001**: TDD-PRIMITIVE-MIGRATION-001 Phase 3 (config consolidation) not started.
- **EC-002**: Project GID migration (entity classes to registry) documented but not started.
- **EC-003**: Cache architecture Phase 1 (Redis hot tier only); Phase 3 (S3 cold tier) planned.
- **EC-004**: Consultation ProcessType blocked model landing.
- **EC-005**: `autom8y_interop` partial migration blocked on upstream PRs.
- **EC-006**: Exception narrowing in preload (I6 backlog) not yet run.
- **EC-007**: Reconciliation section GIDs require production API verification before deployment.
- **EC-008: Deprecated Query Endpoint Frozen Until 2026-06-01.** `api/routes/query.py:7,541`. Today (2026-05-04) leaves ~28 days. Callers tracked via `deprecated_query_endpoint_used` metric.
- **EC-009: ADR-0001 secretspec Profile Split — Implemented.** `metrics/__main__.py:19-49` references `[profiles.cli]`. Test `tests/unit/metrics/test_main.py::TestPreflightParity::test_inline_and_secretspec_enforce_same_required_vars` enforces parity.
- **EC-010: Python Version Constraint — No Upper Bound.** `pyproject.toml:10`: `requires-python = ">=3.12"` (upper bound `<3.14` removed earlier). Linter config suppresses UP046/UP047 with stale comments citing `>=3.11`.
- **EC-011: query/engine.py:139-178,:181 and query/join.py — P1-C-04 Frozen.** `query/engine.py:139-178,181`, `query/join.py`, `query/compiler.py:53-63,192-241`. Explicitly P1-C-04 FORBIDDEN per `api/routes/exports.py:14` docstring. Phase 2 may modify under LEFT-PRESERVATION GUARD ADR architecture. See FROZEN-RANGE-IMPORTERS-001.
- **EC-012: ExportOptions extra="allow" — Do Not Tighten Until Phase 2.** `api/routes/exports.py:141`. Bound by `ADR-engine-left-preservation-guard.md §4.1`.
- **EC-013: project-asana-pipeline-extraction Telos Deadline.** Phase 0/1 carries `telos_deadline: 2026-05-11`. Today (2026-05-04) leaves 7 days. Primary deliverable is Phase 1 exports route. Agents must not restructure the exports surface without confirming sprint scope. [KNOW-CANDIDATE] Telos deadline imminent — all exports constraints are at peak criticality.
- **EC-014: SCAR Test Cluster Now pytest.mark.scar Tagged.** [NEW at `20ef7952`] 35 tests across 11 files bear `@pytest.mark.scar` (HYG-001 sprint, commit `36eaec6c`). These tests are inviolable regression guards. The `scar` marker is registered in `pyproject.toml` (via `7cd7ffd6`). Running `pytest -m scar` isolates this cluster. Do not modify or delete `@pytest.mark.scar` tests without an ADR.
- **EC-015: Post-Merge Coverage CI Job Added.** [NEW at `20ef7952`] `.github/workflows/post-merge-coverage.yml` introduced (SRE-004, commit `29fdaad1`). `cancel-in-progress: false` — post-merge gates must run to completion. This is a new persistent CI surface; any refactor that changes test pass/fail distribution will affect post-merge coverage reporting.
- **EC-016: Hadolint Dockerfile Lint Gate Added.** [NEW at `20ef7952`] `.github/workflows/dockerfile-lint.yml` introduced (SRE-005, per ADR-013). Any Dockerfile changes must pass hadolint with config `.hadolint.yaml`. The gate is authoritative per ADR-013-sre-005-hadolint-2026-04-30.md.

## Risk Zone Mapping

- **RISK-001**: Reconciliation placeholder GIDs (SCAR-REG-001). 4 VERIFY-BEFORE-PROD annotations at `section_registry.py:57,79,94,128`. Severity: High.
- **RISK-002**: Phantom exclusion rate in reconciliation (TC-4). Severity: Medium.
- **RISK-003**: Circular import structure — 3 misplaced `lambda_handlers/` modules + TYPE_CHECKING-guarded lazy imports. Severity: Medium.
- **RISK-004**: `config.py` module-level computation at import time. Severity: Medium.
- **RISK-005**: `DataServiceConfig.max_batch_size` has no 500-minimum enforcement (only `>= 1`). Severity: Low-Medium.
- **RISK-006**: `object.__setattr__()` on frozen `EntityDescriptors` is order-dependent. Severity: Low.
- **RISK-007**: ~10 broad-except sites in preload (`legacy.py: 5`, `progressive.py: 5`). Severity: Low.
- **RISK-008: SCAR-IDEM-001 — Idempotency Finalize Failure Causes Double-Execution.** `api/middleware/idempotency.py:719`. If `finalize()` raises, idempotency key not persisted; client retry re-executes mutation. No metric specifically for finalize failure. Recommended guard: add `metrics.increment("idempotency_finalize_failure")` and promote logging level to explicit warning.
- **RISK-009: Cache Backends — STRICT Freshness Caller-Responsibility Assumption.** `cache/backends/redis.py:432`, `cache/backends/s3.py:505`. Both document "For STRICT freshness, caller must validate against source." No enforcement. Silent responsibility handoff. Cross-references RISK-002.
- **RISK-010: Op Enum Date Operators Not Compilable.** `query/models.py:52-56`, `compiler.py:53-63,192-241`. Date operators exist in `Op` StrEnum but not handled by `PredicateCompiler`. Failure mode is implicit. Only valid consumer is `/exports` handler (strips date ops before compile).
- **RISK-011: LEFT-PRESERVATION GUARD Seam Not Test-Covered in Phase 1.** `api/routes/exports.py:236-284`. NO-OP in Phase 1; correctness in Phase 2 depends on architect's mechanism (a) per `ADR §4.1`. Phase 2 MUST include integration test exercising C5-PATH LEFT request.
- **RISK-012: M-02 Score Floor — RESOLVED, PROSPECTIVE RISK REMAINS.** `.ci/semantic-baseline.json:12-18`. M-02 score = 0.5266 (floor: 0.50) at `20ef7952` — now PASSING. Original breach (0.4743) was discharged via HYG-T1. Prospective risk: `aegis-check.py` does not enforce `examples=` count; a future PR removing `examples=` from Pydantic source will not be caught until a manual baseline refresh. Severity: P3 (downgraded from P1 — no active breach).
- **RISK-013: M-07 Constraint Coverage Floor Actively Breached.** [NEW at `20ef7952`] `.ci/semantic-baseline.json:52-59`. M-07 score = 0.5714 (floor: 0.6, pass: false). `regression_safe: true` prevents CI blocking. The 3 missing constraint coverage slots are unknown without re-running `aegis-check.py` against the spec. Every PR that adds endpoints without `x-constraint` annotations widens the gap. Cross-reference: M07-MONITOR-001. Recommended guard: add constraint-annotation discipline to PR review checklist.
- **RISK-014: SystemContext Per-Worker Registration Gap Under xdist.** [NEW at `20ef7952`] `core/system_context.py:33,48-51`. If a module registers its reset function in the main process before xdist forks workers, that registration lands on key `"main"` — which workers never consult. Singletons imported only in the main process would not reset between worker tests. No test currently covers this boundary. Cross-reference: LBC-012, GAP-010.

## Experiential Observations (from session history)

The 18-session corpus surfaces frozen/sacred areas:
- **SCAR test cluster**: 35 tests now formally tagged `@pytest.mark.scar` (HYG-001). These are inviolable regression guards. Prior documentation cited 33 — actual count at `20ef7952` is 35.
- **Coverage floor**: `>=80%` non-negotiable per project-crucible sprint-6
- **Cascade-spike sessions** (session-20260303-173218, 134822): explicit "do not unpark or interfere" constraint from project-asana-pipeline-extraction
- **Telos deadline pressure**: project-asana-pipeline-extraction Phase 1 telos_deadline is 2026-05-11. Today (2026-05-04) leaves 7 days — highest-urgency active constraint in the codebase.

Recurring tensions documented across sessions:
- CascadingFieldResolver null rates (~30% on units, 30-40% on Offer office) manifested in 3 distinct sessions
- Cascade-contract bypass on fast-paths (S3 fast-path + Offer source=None)
- Test-suite scale/speed (13,072→12,320 reduction, xdist disabled then re-enabled, CI <60s target)
- autom8y-asana identified as fleet's binding CI constraint (consumer-gate timeout 900s→2400s)

Architecture review for Data Attachment Bridge (session-20260318) parked at requirements with no follow-up — load-bearing risk that hasn't been addressed.

## Knowledge Gaps

1. Lifecycle YAML files: not found. YAML-based automation config schema unlocated.
2. autom8y_http and autom8y_log internal contracts: external packages, not observable.
3. INTEGRATE-ecosystem-dispatch Section 1.4: not found in repository.
4. Actual section GID values: require live Asana API verification via `GET /projects/1201081073731555/sections`.
5. ADRs partial: `.ledge/decisions/` contains 21 ADRs (ADR-001–013, plus domain-specific ADRs). ADR-0025 (S3 cutover), ADR-I6-001, ADR-omniscience-idempotency, ADR-S2S-001/002 referenced in code but not in `.ledge/decisions/` — may live in `.claude/agent-memory/`.
6. TENSION-002 nosemgrep annotation absence: four services-layer imports from API layer lack suppression — semgrep likely flags in CI.
7. M-07 gap detail: the 3 uncovered constraint slots are not determinable without running `aegis-check.py` against the live spec.
8. Phase 2 exports implementation scope: `ADR §4.1` describes mechanism (a) territory but no Phase 2 TDD or architectural spec filed yet.
9. `query/engine.py` P1-C-04 boundary exact scope: lines 139-178 and 181 frozen but full module structure / what changes are permitted in Phase 1 not independently documented outside exports route docstring.
10. HYG-001 and RITE-SUBSTRATE-INTEGRITY-001 gate logic: out-of-tree (knossos/ari platform), not expressible as code anchor.
11. RISK-014 (xdist per-worker registration gap): no test exercises main-process-vs-worker singleton registration boundary; actual exposure unquantified.

```metadata
confidence: 0.93
generated_at: "2026-05-04T00:00Z"
source_hash: "20ef7952"
criteria_grades:
  tension_catalog: "A"
  trade_off_documentation: "A"
  abstraction_gap_mapping: "B"
  load_bearing_code: "A"
  evolution_constraints: "A"
  risk_zone_mapping: "A"
overall_grade: "A"
notes: >
  FULL refresh. All prior entries verified at 20ef7952.
  12 new entries added (TENSION-011, TENSION-012, M07-MONITOR-001,
  CI-CONCURRENCY-001, TRADE-011, GAP-010, LBC-012, LBC-013,
  EC-013 updated urgency, EC-014..EC-016, RISK-013..RISK-014).
  RISK-012 downgraded from P1 to P3 (breach discharged).
  SCAR cluster count corrected: 35 not 33.
  Telos deadline: 7 days remaining at generation time.
```
