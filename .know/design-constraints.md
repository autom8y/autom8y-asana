---
domain: design-constraints
generated_at: "2026-04-29T00:09Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "6b303485"
confidence: 0.92
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Design Constraints

> Regenerated 2026-04-29 (FULL mode, Wave B). Source hash: `6b303485` (HEAD at time of audit,
> two commits past PR38 merge `80256049`). 5 new entries added (HYG-001, RITE-SUBSTRATE-INTEGRITY-001,
> M02-MONITOR-001, WORKTREE-001, FROZEN-RANGE-IMPORTERS-001). All prior TENSIONs, LBCs, ECs, and
> RISKs preserved with post-merge anchor verification.
>
> **EMPIRICAL CORRECTION**: M-02 score in `.ci/semantic-baseline.json` is currently **0.4743**
> (numerator: 83/175) — already FAILING below the 0.5 floor. The glint cited 0.5266; that figure
> may have reflected an in-progress state or a stale read. M02-MONITOR-001 is classified P1 (not P2).

## Tension Catalog

**TENSION-001: Dual Config System — Domain Dataclasses vs Platform Primitives**
Location: `src/autom8_asana/config.py:22-65`, `src/autom8_asana/transport/config_translator.py`. The `ConfigTranslator` translates between domain dataclasses (`RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `CircuitBreakerConfig`) and platform equivalents. Do not consolidate without phased migration; 200+ callers depend on domain dataclasses.

**TENSION-002: Services Layer Imports from API Layer (Intentional Violation)**
Location: `src/autom8_asana/services/intake_create_service.py:23`, `matching_service.py:21`, `intake_resolve_service.py:18`, `intake_custom_field_service.py:16`. Confirmed at runtime (bare imports, no TYPE_CHECKING guard, no nosemgrep annotation on the actual import lines).

**TENSION-003: Models Layer Importing from Persistence Layer**
Location: `src/autom8_asana/models/task.py:406-409`, `models/custom_field_accessor.py:421`. Confirmed TYPE_CHECKING-guarded imports with `nosemgrep: autom8y.no-models-import-upper`. Load-bearing for SaveSession pattern.

**TENSION-004: Lambda Handlers as Service-Layer Overflow**
Location: `src/autom8_asana/lambda_handlers/pipeline_stage_aggregator.py:15`, `reconciliation_runner.py:11`. Both docstrings confirm placement to avoid circular dependencies.

**TENSION-005: Entity Classes Duplicate Project GIDs from Registry**
Location: `src/autom8_asana/core/project_registry.py`, `src/autom8_asana/models/business/*.py`. 15+ entity classes with hardcoded `PRIMARY_PROJECT_GID`. Parity enforced by `tests/unit/core/test_project_registry.py:313`.

**TENSION-006: autom8y_interop Protocol Gap — DataServiceClient Coverage Only 30%**
Location: `src/autom8_asana/automation/workflows/protocols.py:32-61`, `bridge_base.py:29-38`. `get_reconciliation_async()` at `clients/data/client.py:1209` and `get_export_csv_async()` at `clients/data/client.py:1145` have no interop analogues. Both documented as bridge-specific gaps requiring upstream PRs.

**TENSION-007: Polars-Primary DataFrame Layer with Pandas Backward-Compat Bridge**
Location: `src/autom8_asana/clients/data/models.py`. `.to_pandas()` backward-compat bridge documented.

**TENSION-008: Auth Layer Importing from API Layer at Runtime**
Location: `src/autom8_asana/auth/dual_mode.py:24`. Imports `ApiAuthError` directly from `api/exception_types.py` at module load time — not TYPE_CHECKING-guarded, no nosemgrep suppression. `cache/dataframe/decorator.py:147,184,204,223` contains four inline function-body imports from `api/exception_types`. Both `auth/` and `cache/` layers have undocumented runtime dependencies on the `api/` layer.

**Resolution path**: Move `ApiAuthError` to public exception hierarchy in `core/exceptions.py` or root `exceptions.py`. Resolution cost: Medium.

**TENSION-009: Exports Route Mount-Order Load-Bearing Constraint**
Location: `src/autom8_asana/api/main.py:431-441`. `exports_router_v1` and `exports_router_api_v1` MUST mount BEFORE `query_router` in FastAPI router registration order. `query_router` uses wildcard `/v1/query/{entity_type}` that would match `/v1/exports` if mounted later. The constraint mirrors the same ordering for `fleet_query_router_v1` / `fleet_query_router_api_v1`. Post-merge verification at `6b303485`: ordering confirmed at lines 431-441 with comment `"Mount BEFORE query_router"`.

**Resolution cost**: Low (comment documents discipline). Forgetting the order is silent-failure risk; not structurally enforced.

**TENSION-010: ExportOptions extra="allow" — Phase 2 Forward-Binding Contract Lock**
Location: `src/autom8_asana/api/routes/exports.py:140`. `ExportOptions.model_config = ConfigDict(extra="allow")` is explicitly marked P1-C-02 BINDING. Must NOT be changed to `extra="forbid"` — would foreclose Phase 2 `predicate_join_semantics` field per LEFT-PRESERVATION GUARD ADR (mechanism (b) escape valve at `ADR-engine-left-preservation-guard.md §4.1`). Documented in code comments but not enforced by a test. Post-merge line confirmed at `exports.py:140`.

**Resolution cost**: Nil for Phase 1. Phase 2: promote `predicate_join_semantics` to typed `Literal` field, tension dissolves.

## Operational Constraints (new section — process and platform)

These constraints are out-of-tree (rite-platform) or CI-enforced, not code-anchored. They govern process behavior affecting codebase integrity.

**HYG-001: Pre-S4 Hygiene Gate Must Verify Untracked Test Files**
Type: Operational constraint (rite-platform)
Anchor: Incident-of-record: Sprint-3 hygiene rite issued APPROVED on PR-38 branch when 5 test files (`tests/unit/api/test_exports_*.py`) were untracked. Post-PR38, 6 files are committed (`git ls-files tests/unit/api/test_exports*.py` returns 6 paths at `6b303485`). The hygiene rite audit-lead rendered APPROVED against a substrate-blind ground truth.
Constraint: Hygiene S4 audit-lead pre-gate MUST run `git ls-files --others --exclude-standard tests/` and if non-empty halt with `RITE-SUBSTRATE-REFUSED: untracked test files present` before issuing APPROVED verdict. Failure mode: rite approves a PR that omits committed test coverage.
Owner-rite: knossos platform / hygiene-pass-2
Deadline: 2026-05-06
Severity: P1 (recurrence risk — Sprint-3 occurrence confirmed)
Cross-reference: RITE-SUBSTRATE-INTEGRITY-001 (root meta-constraint)

**RITE-SUBSTRATE-INTEGRITY-001: Pre-S0 Dirty-Tree Halt for ari sync**
Type: Meta-constraint (rite-platform)
Anchor: IC SEV-2 incident 2026-04-28. `ari sync --rite X` on a dirty working tree permitted multi-rite verdicts to render against substrate-blind ground truth. Simultaneous symptom: HYG-001 untracked test files, and WORKTREE-001 worktree contamination.
Constraint: `ari sync` pre-flight MUST run `git status --porcelain` and emit `RITE-SUBSTRATE-REFUSED: working tree dirty` + halt when dirty. No rite may produce a verdict on an unclean substrate.
Owner-rite: knossos platform / forge eval-specialist
Deadline: 2026-05-06
Severity: P1 (every dirty `ari sync` reproduces the failure mode)
Operational consequence: Any `ari sync` verdict issued against a dirty tree is unreliable and must be treated as invalid.

**M02-MONITOR-001: M-02 Score CI Tripwire Absent — Floor Already Breached**
Type: Observability constraint (CI)
Anchor: `scripts/aegis-check.py:48-86`, `.ci/semantic-baseline.json:12`
Current state (empirically verified at `6b303485`): `semantic-baseline.json` M-02 score = **0.4743** (numerator: 83/175, floor: 0.5). Floor is CURRENTLY BREACHED. `aegis-check.py` checks endpoint-level memory/coverage — does NOT check `examples=` field presence or count at the Pydantic source level.
Constraint: Add proxy metric `count(fields_with_examples) / count(total_fields)` to `aegis-check.py` as a CI gate with floor threshold 0.50 (matching `semantic-baseline.json` floor). Current score 0.4743 means 92 of 175 fields currently lack `examples=`. Breach is active — not prospective.
Severity: P1 (floor currently breached; CI does not surface this; PR-merge will not block on M-02 regression)
Deadline: 2026-05-06 (Sprint-4 priority)
Cross-reference: CSI-001 DISCHARGED (scar-tissue.md) — CSI-001 fixed the spec-gen gap; M02-MONITOR-001 is the missing CI enforcement that would prevent regression.

**WORKTREE-001: Parallel-Worktree Contamination Protocol Absent**
Type: Operational constraint (development hygiene)
Anchor: `.worktrees/` directory — 10 entries confirmed at `6b303485`: `anchor-r1v3-change-005`, `autom8y`, `autom8y-api-schemas`, `batch-d-observation`, `cache-freshness-impl`, `hotfix-coalescer-moto`, `hotfix-config-2.0.1`, `hygiene-cleanup`, `lazy-load-detection-cache-ttl`, `lockfile-bump-config-201`, `lockfile-bump-config-202`, `thermia-cache-procession` (12 entries observed; glint reported 10 — actual count may vary).
Why: `.worktrees/` is `.gitignore`d (not committed). Uncommitted Sprint-3 wiring on a hygiene branch was identified as a proximate contributor to the IC SEV-2 dirty-tree incident. A stale worktree can pollute `git status` in the main tree, and `ari sync` running against a dirty tree produces substrate-blind verdicts.
Constraint: Apply `parallel-wave-close-consolidation-protocol` at each session-wrap; audit `.worktrees/` for stale checkouts older than 7 days; document and enforce worktree-discipline rules in `.knossos/`.
Owner-rite: naxos / Sprint-4 cleanup
Severity: P2 (no current production impact; risk is rite-verdict reliability)
Cross-reference: RITE-SUBSTRATE-INTEGRITY-001

**FROZEN-RANGE-IMPORTERS-001: Frozen-Range Importer Catalog**
Type: Structural constraint (blast-radius mapping)
Frozen modules (P1-C-04 per `api/routes/exports.py:14`):
- `src/autom8_asana/query/engine.py:139-178,181` (execute_rows steps 6-9, aggregate logic)
- `src/autom8_asana/query/join.py` (full module)
- `src/autom8_asana/query/compiler.py:53-63,192-241` (OPERATOR_MATRIX + _compile_node + _compile_comparison)

Importer catalog (verified at `6b303485`):
- `src/autom8_asana/api/routes/exports.py:65` — imports `PredicateCompiler` from `query.compiler` (NEW post-PR38 T-09 addition)
- `src/autom8_asana/api/routes/query.py:38` — imports `QueryEngine` from `query.engine`
- `src/autom8_asana/query/__init__.py:17-18,38` — re-exports `PredicateCompiler`, `QueryEngine`, `execute_join`
- `src/autom8_asana/query/__main__.py:513,669` — lazy-imports `QueryEngine` in CLI subcommands
- `src/autom8_asana/services/query_service.py:236` — lazy-imports `strip_section_predicates` from `query.compiler`

Constraint: Any modification to P1-C-04 frozen ranges must be cross-referenced against this importer list to assess blast radius. `exports.py:65` is the newest importer (added by T-09, commit `d9abbc1f`); it was undocumented at prior source_hash `8c58f930`.
Severity: Structural — no temporal deadline; permanent design constraint
Cross-reference: EC-011, SCAR-DISCRIMINATOR-001 (adjacent to but NOT in P1-C-04 frozen — discriminator lives at `query/models.py:97-112`)

## Trade-off Documentation

- **TRADE-001**: `raw=True` dual-return type on all 12 `*Client` classes. 115 occurrences of `raw: bool` or `raw=True` across `src/autom8_asana/clients/`.
- **TRADE-002**: `CircuitBreakerConfig.enabled = False` opt-in. Confirmed at `config.py:291-297`.
- **TRADE-003**: `ConcurrencyConfig.aimd_cooldown_duration_seconds` unused; adaptive semaphore logs `"cooldown_not_active_in_v1"`. Confirmed at `transport/adaptive_semaphore.py:60,339`.
- **TRADE-004**: Broad-except sites in lambda handlers annotated `# BROAD-CATCH`. Current count: 22 BROAD-CATCH annotations in `lambda_handlers/`; 152 total codebase-wide.
- **TRADE-005**: ADR-0025 big-bang S3 cutover, no fallback. Referenced but ADR-0025 not in `.ledge/decisions/` (only ADR-0001–0003, ADR-bucket-naming, ADR-0003-bucket-disposition, ADR-env-secret-profile-split, ADR-engine-left-preservation-guard present).
- **TRADE-006**: `DataServiceConfig.max_batch_size >= 500` constraint documented in `query/fetcher.py:8-10`. Current code at `clients/data/config.py:256-263` validates `>=1` and `<=1000`. The 500-threshold concern is real but code validation is at `>= 1`.
- **TRADE-007**: `DynamoDBIdempotencyStore` degrades silently to passthrough on connectivity failures. `api/main.py:339-344` emits `idempotency_store_degraded` warning and falls back to `NoopIdempotencyStore`.
- **TRADE-008: Deprecated Query Endpoint Kept Until Sunset Date.** `api/routes/query.py:7,541,561,669`. `POST /v1/query/{entity_type}` deprecated with sunset `2026-06-01`. Legacy model classes preserved. Metric `deprecated_query_endpoint_used` (line 669) tracks usage.
- **TRADE-009: LEFT-PRESERVATION GUARD as NO-OP Structural Seam in Phase 1.** `api/routes/exports.py:236-284` (`_engine_call_with_left_preservation_guard`). Phase 1 ships single-entity exports — no LEFT JOIN fires, the GUARD is a structural NO-OP. Seam exists for Sprint 4 qa-adversary verification + Phase 2 architect inheritance. Per `ADR-engine-left-preservation-guard.md §4`.
- **TRADE-010: ESC-1 Date Predicates Under OR/NOT Unsupported in Phase 1.** `api/routes/_exports_helpers.py:369-417`. Date operators (`BETWEEN`, `DATE_GTE`, `DATE_LTE`) inside `OrGroup` or `NotGroup` rejected with `ValueError` in Phase 1. Restriction: extracting date Comparisons from OR/NOT semantics would alter boolean meaning.

## Abstraction Gap Mapping

- **GAP-001**: Missing `CONSULTATION` variant in `ProcessType` enum. `services/intake_create_service.py:46-48`.
- **GAP-002**: Reconciliation section GIDs are unverified placeholders. `reconciliation/section_registry.py:57,79,94,128` with `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations.
- **GAP-003**: `TieredCacheProvider` S3 cold tier is Phase 3 — not implemented. Redis-only in factory.
- **GAP-004**: `DataServiceClient` / `autom8y_interop` protocol gaps for reconciliation and export. `automation/workflows/protocols.py:32-61`.
- **GAP-005**: Metrics layer Phase 1, section scoping for "offer" only. `metrics/metric.py:28-30`.
- **GAP-006**: `EntityDescriptor` frozen dataclass mutated at module load via `object.__setattr__()`. `core/entity_registry.py:851-890`.
- **GAP-007**: `EntityDescriptor.entity_type` typed as `Any = None` to break `core → models` circular import. `core/entity_registry.py:140,851-853`.
- **GAP-008: api/exception_types.py Used as Cross-Cutting Exception Registry.** Callers: `auth/dual_mode.py:24`, `cache/dataframe/decorator.py:147,184,204,223`, `api/dependencies.py:37`, `api/routes/internal.py:20`. Renaming requires coordinated updates across four files in three packages.
- **GAP-009: Op Enum Has Date Operators Not Supported by PredicateCompiler.** `query/models.py:52-56` (`Op.BETWEEN`, `Op.DATE_GTE`, `Op.DATE_LTE`) exist in AST vocabulary but `PredicateCompiler` (P1-C-04 FORBIDDEN at `compiler.py:53-63,192-241`) does not handle them. The `/exports` handler explicitly strips date ops before calling `PredicateCompiler`.

## Load-Bearing Code Identification

- **LBC-001**: `EntityRegistry` singleton built at import time with 7 integrity checks. Import failure = startup failure.
- **LBC-002**: `ENTITY_DESCRIPTORS` tuple — all entity metadata in one declaration; all backward-compat facades delegate to it.
- **LBC-003**: `DEFAULT_ENTITY_TTLS` in `config.py` — backward-compat import shim.
- **LBC-004**: `EXCLUDED_SECTION_NAMES` at `reconciliation/section_registry.py:109-120` — "DO NOT use `UNIT_CLASSIFIER.ignored`" warning.
- **LBC-005**: `SWR_GRACE_MULTIPLIER = 3.0` and `LKG_MAX_STALENESS_MULTIPLIER = 0.0` at `config.py:93-102`.
- **LBC-006**: `DataServiceConfig.max_batch_size >= 500` for join fetcher. `query/fetcher.py:8-10`.
- **LBC-007**: `cascade_warm_phases()` topological ordering at `api/lifespan.py:242`.
- **LBC-008**: BROAD-CATCH isolation pattern in lambda handlers. 22 annotated in `lambda_handlers/`; 152 total codebase-wide.
- **LBC-009: DynamoDBIdempotencyStore Degradation-to-Passthrough.** `api/middleware/idempotency.py:277,339,384,404`. Four `except Exception` blocks load-bearing. SCAR-IDEM-001 carries double-execution risk at line 384 (finalize). Naive narrowing to `botocore.exceptions.ClientError` would break on connection timeout exceptions.
- **LBC-010: ExportOptions extra="allow" Contract Lock.** `api/routes/exports.py:140`. Tightening to `"forbid"`/`"ignore"` would silently break Phase 2 callers passing `predicate_join_semantics` as untyped extra. Dependents: `ADR-engine-left-preservation-guard.md §4`, `exports.py:292-304`. Post-merge anchor confirmed at line 140.
- **LBC-011: Router Registration Order in api/main.py.** `api/main.py:431-441`. `fleet_query_router_v1`, `fleet_query_router_api_v1`, `exports_router_v1`, `exports_router_api_v1` MUST register BEFORE `query_router`. Failure mode is silent at startup (no error), only manifests on first request to affected path. Post-merge anchor confirmed at lines 431-441.

## Evolution Constraints

- **EC-001**: TDD-PRIMITIVE-MIGRATION-001 Phase 3 (config consolidation) not started.
- **EC-002**: Project GID migration (entity classes to registry) documented but not started.
- **EC-003**: Cache architecture Phase 1 (Redis hot tier only); Phase 3 (S3 cold tier) planned.
- **EC-004**: Consultation ProcessType blocked model landing.
- **EC-005**: `autom8y_interop` partial migration blocked on upstream PRs.
- **EC-006**: Exception narrowing in preload (I6 backlog) not yet run.
- **EC-007**: Reconciliation section GIDs require production API verification before deployment.
- **EC-008: Deprecated Query Endpoint Frozen Until 2026-06-01.** `api/routes/query.py:7,541`. Today (2026-04-29) leaves ~33 days. Callers tracked via `deprecated_query_endpoint_used` metric.
- **EC-009: ADR-0001 secretspec Profile Split — Implemented.** `metrics/__main__.py:19-49` references `[profiles.cli]`. Test `tests/unit/metrics/test_main.py::TestPreflightParity::test_inline_and_secretspec_enforce_same_required_vars` enforces parity.
- **EC-010: Python Version Constraint — No Upper Bound.** `pyproject.toml:10`: `requires-python = ">=3.12"` (upper bound `<3.14` removed in commit `770c9cd6`). Linter config still suppresses UP046/UP047 with stale comment.
- **EC-011: query/engine.py:139-178,:181 and query/join.py — P1-C-04 Frozen.** `query/engine.py:139-178,181`, `query/join.py`, `query/compiler.py:53-63,192-241`. Explicitly P1-C-04 FORBIDDEN per `api/routes/exports.py:14` docstring. Phase 2 may modify under LEFT-PRESERVATION GUARD ADR architecture. See FROZEN-RANGE-IMPORTERS-001 for full importer blast-radius catalog.
- **EC-012: ExportOptions extra="allow" — Do Not Tighten Until Phase 2.** `api/routes/exports.py:140`. Bound by `ADR-engine-left-preservation-guard.md §4.1`.
- **EC-013: project-asana-pipeline-extraction Telos Deadline.** Phase 0/1 carries `telos_deadline: 2026-05-11`. Phase 1 exports route is primary deliverable. Today (2026-04-29) leaves 12 days. Active sprint scope — agents should not restructure exports surface without confirming.

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
- **RISK-010: Op Enum Date Operators Not Compilable.** `query/models.py:52-56`, `compiler.py:53-63,192-241`. Date operators exist in `Op` StrEnum but not handled by `PredicateCompiler`. Failure mode is implicit (falls through to default case or AttributeError/KeyError). Only valid consumer is `/exports` handler (strips date ops before compile).
- **RISK-011: LEFT-PRESERVATION GUARD Seam Not Test-Covered in Phase 1.** `api/routes/exports.py:236-284`. NO-OP in Phase 1; correctness in Phase 2 depends on architect's mechanism (a) per `ADR §4.1`. If guard implemented incorrectly in Phase 2, silent LEFT→INNER rewrite defect re-emerges. Phase 2 MUST include integration test exercising C5-PATH LEFT request.
- **RISK-012: M-02 Score Floor Currently Breached — No CI Enforcement.** `.ci/semantic-baseline.json:12`. M-02 score = 0.4743 (floor: 0.50) at `6b303485`. 92 of 175 fields lack `examples=`. `aegis-check.py` does not check this metric. Every PR that adds Pydantic fields without `examples=` silently widens the gap. [KNOW-CANDIDATE] Active breach with no CI guard — theoros-audited discrepancy vs glint estimate.
- **RISK-013: _predicate_discriminator Dict-Only Guard — SCAR-DISCRIMINATOR-001.** `src/autom8_asana/query/models.py:97-112`. Model-instance inputs to `NotGroup(not_=AndGroup(...))` fall through to `return "comparison"`, triggering Pydantic validation failure. No production caller currently reaches this path; P3 severity. Adjacent to but outside P1-C-04 frozen range. See `scar-tissue.md` SCAR-DISCRIMINATOR-001.

## Experiential Observations (from session history)

The 18-session corpus surfaces frozen/sacred areas:
- **SCAR test cluster**: 33 inviolable regression tests (SCAR-001/005/006/010/010b/020/026/027/S3-LOOP, TENSION-001) — explicit "do not modify" constraint from project-crucible
- **Coverage floor**: `>=80%` non-negotiable per project-crucible sprint-6
- **Cascade-spike sessions** (session-20260303-173218, 134822): explicit "do not unpark or interfere" constraint from project-asana-pipeline-extraction

Recurring tensions documented across sessions:
- CascadingFieldResolver null rates (~30% on units, 30-40% on Offer office) manifested in 3 distinct sessions
- Cascade-contract bypass on fast-paths (S3 fast-path + Offer source=None)
- Test-suite scale/speed (13,072→12,320 reduction, xdist disabled then re-enabled, CI <60s target)
- autom8y-asana identified as fleet's binding CI constraint (consumer-gate timeout 900s→2400s)

Architecture review for Data Attachment Bridge (session-20260318) parked at requirements with no follow-up — possibly indicates load-bearing risk that hasn't been addressed.

Telos discipline emerging: project-asana-pipeline-extraction Phase 0/1 carries telos_deadline 2026-05-11 — first telos data point in corpus. 12 days remaining as of 2026-04-29.

## Knowledge Gaps

1. Lifecycle YAML files: not found. YAML-based automation config schema unlocated.
2. autom8y_http and autom8y_log internal contracts: external packages, not observable.
3. INTEGRATE-ecosystem-dispatch Section 1.4: not found in repository.
4. Actual section GID values: require live Asana API verification via `GET /projects/1201081073731555/sections`.
5. ADRs partial: `.ledge/decisions/` contains ADR-0001/0002/0003, ADR-env-secret-profile-split, ADR-engine-left-preservation-guard. ADR-0025 (S3 cutover), ADR-I6-001, ADR-omniscience-idempotency, ADR-S2S-001/002 referenced in code but not in `.ledge/decisions/` — may live in `.claude/agent-memory/`.
6. TENSION-002 nosemgrep annotation absence: four services-layer imports from API layer lack suppression — semgrep likely flags in CI.
7. ADR-omniscience-idempotency in agent memory, not `.ledge/decisions/`.
8. Phase 2 exports implementation scope: `ADR §4.1` describes mechanism (a) territory but no Phase 2 TDD or architectural spec filed yet.
9. `query/engine.py` P1-C-04 boundary exact scope: lines 139-178 and 181 frozen but full module structure / what changes are permitted in Phase 1 not independently documented outside exports route docstring.
10. HYG-001 and RITE-SUBSTRATE-INTEGRITY-001 gate logic: out-of-tree (knossos/ari platform), not expressible as code anchor. Constraint documented but enforcement must be implemented in knossos platform (forge eval-specialist).
11. M-02 score discrepancy: glint report cited 0.5266; empirical read of `semantic-baseline.json` at `6b303485` shows 0.4743. Source of glint figure unresolved — may be stale or from a different aegis-report.json artifact.
