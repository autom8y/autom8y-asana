---
domain: test-coverage
generated_at: "2026-05-08T00:00Z"
expires_after: "7d"
source_scope:
  - "./tests/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.92
format_version: "1.0"
update_mode: "incremental"
incremental_cycle: 1
max_incremental_cycles: 3
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "9db9c6f33d48f5c2fce398de7d3359fef30a0a0bd809044f7259f792ee6c4b9e"
---

# Codebase Test Coverage

## Coverage Gaps

### Package-Level Coverage Map

The test suite contains 502 `test_*.py` files under `tests/` (505 in `tests/unit/` alone as of prior cycle; revised per current count). Source tree has 24 top-level packages under `src/autom8_asana/`. 22 of 24 source packages have dedicated test directories or direct flat test files.

**Packages with zero dedicated test directories** (partial indirect coverage):

| Source Package | Source Files | Assessment |
|---|---|---|
| `_defaults/` | 4 | Indirect coverage via client/config tests; thin adapter wrappers |
| `batch/` | 2 | Covered indirectly via `tests/unit/test_batch_adversarial.py`, `tests/unit/clients/test_batch.py` |
| `observability/` | 3 | Covered via `tests/unit/test_observability.py` and span assertion tests in services |
| `protocols/` | 9 | Protocol types validated only by satisfying-class tests |

**Single-module source files with no dedicated tests**: `errors.py` (tested indirectly), `settings.py` (covered in `tests/unit/test_settings.py`).

### Module-Level Gaps Within Covered Packages

**lifecycle** — 2 of 17 modules unmatched:
- `lifecycle/loop_detector.py` — no `test_loop_detector.py`; safety mechanism for lifecycle engine; highest-risk gap (unguarded safety path)
- `lifecycle/observation_store.py` — no `test_observation_store.py`; persistence for lifecycle observations

**services** — intake services lack direct unit tests:
- `services/intake_create_service.py` — tested only through route layer
- `services/intake_resolve_service.py` — same pattern
- `services/intake_custom_field_service.py` — same pattern
- `services/entity_context.py` — context carrier used across service layer; no direct unit test

**models (top-level)**: 15 Asana resource model files (`task.py`, `project.py`, etc.) have no dedicated test files. Covered indirectly through all tests that instantiate them; `tests/unit/models/test_models.py` covers basic import/instantiation.

**models/business** — 4 modules without dedicated tests: `dna.py`, `mixins.py`, `videography.py`, `reconciliation.py`. Detection tier files (`tier1`–`tier4`) covered via detection_cache and adversarial tests.

### Schemathesis / OpenAPI Fuzz

`tests/test_openapi_fuzz.py` has 47 pre-existing xfail markers (`xfail(strict=False)`) representing known schemathesis violations. These are pending triage — they represent known OpenAPI contract gaps that have not been resolved.

### Exports Feature Test Cluster (post-PR #38, commit `80256049`)

Six committed test files in `tests/unit/api/` cover `api/routes/exports.py` and `api/routes/_exports_helpers.py`:

| File | Focus |
|---|---|
| `test_exports_contract.py` | `ExportRequest`/`ExportOptions` Pydantic contract (AC-12, AC-13, AC-15, AC-16) |
| `test_exports_auth_exclusion.py` | JWT middleware PAT-exclusion regression (DEF-08 SCAR-WS8) |
| `test_exports_format_negotiation.py` | Content-type format negotiation behavior |
| `test_exports_handler.py` | `export_handler` function behavior |
| `test_exports_helpers.py` | `_exports_helpers.py` date-predicate translation (ESC-1) |
| `test_exports_helpers_walk_predicate_property.py` | Behavior-preservation class-based tests for `_walk_predicate` refactor (T-04a, commit `f4fd18f6`) |

**CHANGE-001** (commit `321909c1`): Removed 2 silent test-method overwrites in `test_exports_helpers_walk_predicate_property.py` — post-CHANGE-001: 36 effective test functions, 0 silent overwrites. Closes FLAG-1 and FLAG-3.

### Prioritized Gap List (Highest-Risk First)

1. **`services/intake_*_service.py` (3 modules)** — critical production path. Tested only through HTTP route layer; service-layer error paths and boundary conditions unverified in isolation.
2. **`lifecycle/loop_detector.py`** — loop detection in lifecycle engine is a safety mechanism; no direct test. [KNOW-CANDIDATE] Unguarded safety path — regression risk not previously flagged at highest priority.
3. **`lifecycle/observation_store.py`** — persistence for lifecycle observations; no direct test.
4. **`services/entity_context.py`** — context carrier used across service layer with no direct unit test.
5. **`_defaults/` auth and observability** — thin adapter wrappers; indirect coverage exists but no dedicated test.
6. **`protocols/`** — 9 Protocol class definitions; no explicit protocol-conformance tests.
7. **Schemathesis 47 xfails** — pre-existing OpenAPI contract violations pending triage.

### Integration Test Coverage

`@pytest.mark.integration` appears across 6 files in `tests/integration/`:
- `tests/integration/automation/polling/test_end_to_end.py` (7 marks)
- `tests/integration/automation/polling/test_action_executor_integration.py`
- `tests/integration/automation/polling/test_trigger_evaluator_integration.py`
- `tests/integration/test_composite_verification.py`
- `tests/integration/test_e2e_offer_write_proof.py`
- `tests/integration/test_batch_api.py`

Most `tests/integration/` files (25 of 33) do NOT carry `@pytest.mark.integration` — they use real component wiring with mocked I/O but do not require live Asana API.

Packages with no integration or validation tests: `auth`, `core`, `models`, `metrics`, `query`, `patterns`, `transport`, `search`, `reconciliation`.

### Coverage Infrastructure

- `fail_under = 80` in `pyproject.toml` (`[tool.coverage.report]`); branch coverage enabled (`branch = true`); source scoped to `src/autom8_asana`
- Coverage exclusion lines: `pragma: no cover`, `if TYPE_CHECKING:`, `@abstractmethod`, `raise NotImplementedError`, `if __name__ == "__main__":`
- **Coverage gate (SRE-004 / ADR-011 — ENFORCED post-merge)**: `pyproject.toml:127` declares `fail_under = 80`. `.github/workflows/test.yml` sets `coverage_threshold: 0` for the 4-shard PR matrix job (per-shard coverage is meaningless with `test_splits=4`; each shard covers ~25%). Aggregate coverage gate runs at `.github/workflows/post-merge-coverage.yml` (single-shard `pytest --cov-fail-under=80` on push to main), enforcing the declared 80% floor post-merge. Project-crucible achieved 87.59% coverage baseline.

## Testing Conventions

### Test Runner and Configuration

- **Runner**: `pytest` with `asyncio_mode = "auto"` (all `async def test_*` execute without `@pytest.mark.asyncio`)
- **Test command**: `pytest` from project root; `testpaths = ["tests"]`
- **Parallel execution**: `pytest-xdist` with `--dist=loadgroup` (current `addopts` in `pyproject.toml`, commit `149d3673`). The `loadgroup` strategy ACTIVATES `xdist_group` markers — all tests carrying the same `xdist_group` value are pinned to the same worker. Prior doc drift (comment describing `--dist=loadfile` / R5-FIX rationale) is now resolved; `pyproject.toml:103-105` carries a forward-pointer to the substantive rationale in `test_workflow_handler.py` and `test_openapi_fuzz.py`.
- **Timeout**: 60 seconds per test; `timeout_method = "thread"`
- **Coverage**: `pytest --cov`; `fail_under = 80`, branch coverage, source `src/autom8_asana`

**xdist history**: disabled → re-enabled (commit `affbf5a5`) → `--dist=load` → `--dist=loadfile` (commit `8fd0aefb`) → `--dist=load` (commit `8f99a801`) → `--dist=loadgroup` (commit `149d3673`; current).

**xdist_group markers inventory** (3 active groups):

| Group | File | Purpose |
|---|---|---|
| `xdist_group("fuzz")` | `tests/test_openapi_fuzz.py` | Pins schemathesis/hypothesis fuzz tests to a single worker; prevents cross-worker state corruption |
| `xdist_group("workflow_handler")` | `tests/unit/lambda_handlers/test_workflow_handler.py` | Pins tests sharing `AsyncMock(spec=DataServiceClient)` teardown patterns executed inside `asyncio.run` event loops; was FORWARD-COMPATIBLE no-op under `--dist=load`, now ACTIVE under `--dist=loadgroup` (commit `149d3673`) |
| `xdist_group("query_routes")` | `tests/unit/api/test_routes_query.py` | Pins tests with heavy `AsyncMock` + `dependency_overrides` isolation that produced contention under `--dist=loadgroup` without co-location (DW-W1E-LOADGROUP-FALLOUT-001) |

### Test Naming

- Function-based tests dominant; subset use `class Test*` organization (e.g., `test_exports_contract.py` uses `class TestExportRequestForbiddenFields`, `test_exports_helpers_walk_predicate_property.py` uses 4 `class Test*` groups)
- Naming pattern: `test_{thing_being_tested}_{condition}` — e.g., `test_cascade_validator_corrects_business_name_from_task_name`, `test_tier2_get_async_returns_model`
- Async tests: `async def test_*` used broadly
- Class-based pattern used for grouping related contract assertions and behavior-preservation clusters

#### Async-native migration pattern (B7 Sprint-1, 2026-06-01)

Canonical mechanical transform for `def test_X(self) -> None: asyncio.run(coro)` sites whose production target is `async def`:

1. `def test_X(self, ...) -> None:` -> `async def test_X(self, ...) -> None:`
2. `asyncio.run(<expr>)` -> `await <expr>`
3. `with pytest.raises(...): asyncio.run(coro)` -> `with pytest.raises(...): await coro`
4. Drop orphaned `import asyncio` to satisfy ruff F401.
5. Do NOT add `@pytest.mark.asyncio` — auto-mode (`pyproject.toml:99`) is the standard.
6. Production source MUST remain untouched; any `src/` diff signals scope drift.

First landed at `tests/unit/lifecycle/test_observation.py:235` and `tests/unit/lifecycle/test_observation.py:244` (TestStageTransitionEmitter); production target `src/autom8_asana/lifecycle/observation.py:160` (`async def emit`) is unchanged. Exit-gate evidence: test ID parity (18 collected pre/post), `git diff main..HEAD -- src/` = 0 bytes, ruff/mypy clean.

Intentional `asyncio.run` pins (DO NOT MIGRATE — they exercise specific guard behavior or sit in docstrings):

- `tests/unit/lifecycle/test_freshness_verification_recency.py:736-760`
- `tests/unit/patterns/test_async_method.py:92` (`test_sync_in_async_context_raises` — deliberately invokes sync API inside a running loop)
- `tests/unit/dataframes/test_public_api.py:278` (docstring reference only)

### Markers

| Marker | Count | Meaning |
|---|---|---|
| `@pytest.mark.parametrize` | 148 call-sites (63 files) | Parameterized test cases; 12.4% parametrize rate |
| `@pytest.mark.integration` | ~42 usages | Live API tests |
| `@pytest.mark.usefixtures` | ~38 usages | Fixture injection via decorator |
| `@pytest.mark.slow` | ~23 usages | Deselectable: `-m "not slow"` |
| `@pytest.mark.scar` | 35 usages (11 files) | SCAR regression tests (HYG-001); selectable via `pytest -m scar`; registered in `pyproject.toml` |
| `@pytest.mark.skip` | ~10 usages | Explicit skips with reason strings |
| `@pytest.mark.skipif` | ~4 usages | Conditional: `not FAKEREDIS_AVAILABLE`, `not MOTO_AVAILABLE`, `not _HAS_HYPOTHESIS` |
| `@pytest.mark.benchmark` | ~3 usages | Performance benchmarks |
| `@pytest.mark.fuzz` | 1 module | OpenAPI hypothesis fuzz |
| `@pytest.mark.xfail` | 1 module (`test_openapi_fuzz.py`) | 47 pre-existing schemathesis violations |

**Parametrize adoption (HYG-004)**: 148 call-sites across 63 files (verified at HEAD `8980bcd7`). Unchanged from prior cycle. Rate: 12.4%.

**SCAR marker (HYG-001)**: `@pytest.mark.scar` registered in `pyproject.toml` with 35 invocations across 11 test files (verified at HEAD `8980bcd7`; unchanged from prior cycle). Enables `pytest -m scar` selection of the inviolable regression cluster.

### Property Tests (Hypothesis)

Only **1 `@hypothesis.given` decorator** in `tests/unit/` — `tests/unit/persistence/test_reorder.py:288` (`test_property_moves_produce_desired_order`), stabilized by TRIAGE-005 (commit `ec7c7f10`): `@settings(max_examples=100, deadline=None, derandomize=True)`.

`tests/test_openapi_fuzz.py` is the other hypothesis consumer: schemathesis-driven OpenAPI fuzz with `max_examples` capped and `derandomize=True` (FR-10). Hypothesis DB write channel disabled in CI.

Note: `test_exports_helpers_walk_predicate_property.py` uses "property" in its name but is a class-based pytest test — it does NOT use `@hypothesis.given`.

### Mocking Conventions

- **`AsyncMock`** (stdlib `unittest.mock`): all async method mocking; dominant pattern
- **`MagicMock`**: sync objects (services, clients, config)
- **`MagicMock(spec=)`** (HYG-002): 136 call-sites across 33 files — interface-enforcing mocks that fail fast on attribute typos. This is the canonical spec-enforcing mock pattern adopted post-HYG-002 campaign. Count verified at HEAD `8980bcd7`.
- **`patch`** (`unittest.mock.patch`): context manager and decorator in 96+ files
- **`respx`**: httpx mocking; ~16 files for HTTP call interception
- **`fakeredis`**: Redis mocking; conditionally available
- **`moto`**: AWS/S3 mocking; conditionally available
- **SDK testing doubles**: `autom8y_log.testing.MockLogger`, `autom8y_cache.testing.MockCacheProvider`
- **`schemathesis` + `hypothesis`**: OpenAPI property-based fuzzing

### MockTask Canonicalization (HYG-003 — COMPLETE)

`MockTask` is fully canonicalized: **1 definition** in `tests/_shared/mocks.py`, **0 bespoke** class-level redefinitions remaining (verified at HEAD `8980bcd7`; `grep -rn "class MockTask" tests/` returns only the canonical definition). `MockTasksClient` (2 remaining occurrences in `tests/unit/automation/test_waiter.py` and `tests/integration/test_unit_cascade_resolution.py`) is a distinct class, not a `MockTask` variant.

**Convention**: New tests that require a `MockTask` MUST import from `tests/_shared/mocks`. Bespoke redefinitions are prohibited.

**SDK testing doubles utilization**: `autom8y_log.testing`/`autom8y_cache.testing` imported in 5 of 502 non-conftest test files (~1% adoption). Doubles are funneled through root conftest fixtures (`MockLogger`, `MockCacheProvider`); direct per-test imports are rare.

## Fixture Patterns

### Fixture Infrastructure

- 687 `@pytest.fixture` definitions; 15 `conftest.py` files
- Fixture scopes: `function` (default), `session` (`_bootstrap_session`), `module` (API conftest `app` fixture)

### Root Conftest (`tests/conftest.py`)

| Fixture | Scope | Purpose |
|---|---|---|
| `mock_http` | function | `MockHTTPClient` with `AsyncMock` for 8 HTTP methods |
| `config` | function | `AsanaConfig()` |
| `auth_provider` | function | `MockAuthProvider` returning `"test-token"` |
| `logger` | function | `MockLogger` from `autom8y_log.testing` |
| `_bootstrap_session` | session (autouse) | Bootstraps `ProjectTypeRegistry` + rebuilds Pydantic `NameGid` forward refs once per session |
| `reset_all_singletons` | function (autouse) | `SystemContext.reset_all()` before/after every test — complete isolation |

**Environment setup**: Root conftest force-sets `AUTOM8Y_ENV=test` (relaxes GID pattern) and `AUTH__JWKS_URL=http://localhost:8000/...`. Patches `schemathesis.pytest.xdist.XdistReportingPlugin.pytest_testnodedown` at class-method level inside `pytest_configure` (R4-FIX-002).

### Canonical Shared Mocks (`tests/_shared/mocks.py`)

The `_shared/mocks.py` module is the canonical source for `MockTask` (automation/polling). Any test requiring `MockTask` must import from here. `MagicMock(spec=)` adoption (HYG-002 — 136 call-sites across 33 files) complements this by enforcing interface contracts on inline mock objects.

### Sub-Package Conftests

Domain-specific fixtures provided by: `api/`, `clients/`, `clients/data/`, `cache/`, `dataframes/`, `automation/polling/`, `automation/workflows/`, `lifecycle/`, `persistence/`, `resolution/`, `reconciliation/`.

### Test Isolation Pattern

- `SystemContext.reset_all()` via autouse fixture resets all registries, caches, singletons between every test
- Per-test resets for `EntityProjectRegistry`, `reset_auth_client`, `clear_bot_pat_cache`
- Environment variables controlled via `os.environ` in conftest (session-scoped)

### No File-Based Test Data

No `fixtures/`, `testdata/`, or `data/` directories in `tests/`. All test data inline via `MockTask`, fixture functions, builder/helper patterns. No golden files or YAML/JSON fixture files.

**Test data factory patterns**: 160 helper functions named `make_*`/`create_*`/`build_*`.

## CI Test Topology

### xdist Configuration

- **Runtime**: `--dist=loadgroup` (current `addopts`, commit `149d3673`). Under `loadgroup`, `xdist_group` markers are ACTIVE — tests in the same group are routed to the same worker.
- **xdist_group markers**: 3 active groups (`fuzz`, `workflow_handler`, `query_routes`) — see Markers table above.
- **Resolved doc drift**: Prior knowledge noted a stale `--dist=loadfile` comment in `pyproject.toml`. That drift is fully resolved at `8980bcd7`: `pyproject.toml:103-105` now carries a minimal forward-pointer comment ("--dist=loadgroup activates xdist_group markers; substantive rationale lives at tests/unit/lambda_handlers/test_workflow_handler.py:25-46 + tests/test_openapi_fuzz.py:64-72") with no stale R5-FIX text.
- **Hypothesis DB**: Write channel disabled in CI to prevent cross-worker database corruption

### PR Sharding

- 4-shard matrix using `pytest-split` with `coverage_threshold: 0` per shard (per-shard coverage meaningless at 25% each)
- `tests/unit/lambda_handlers/test_workflow_handler.py` and `tests/test_openapi_fuzz.py` historically caused worker crashes (commits `d0a6335b` context); `xdist_group` + `--dist=loadgroup` is the current mitigation
- **`.test_durations` refresh** (commit `e7698907`): retrained from trailing main n>=10. Affects pytest-split shard balance across the 4-shard PR matrix. Automated weekly refresh via `.github/workflows/durations-refresh.yml` (weekly cron; opens a `chore/durations-refresh-{run_id}` PR when durations change).

### Post-Merge Coverage Gate

- `.github/workflows/post-merge-coverage.yml` enforces `pytest --cov-fail-under=80` on push to main (SRE-004 / ADR-011)
- Project-crucible 6-sprint run achieved 87.59% coverage baseline (36+ commits, 13,072→12,320 tests post-dedup campaigns)
- Consumer-gate poll timeout raised 900s→2400s due to autom8y-asana wall-clock constraints

### Performance Budgets

- `TestAC006PerformanceTolerance` (`tests/unit/persistence/test_session_concurrency.py`):
  - `test_lock_overhead_track`: < 1ms per operation
  - `test_lock_overhead_state_read`: < 100µs (well under 1ms)
  - `test_lock_overhead_under_contention`: < 2ms (widened from 1ms, commit `f37802f2` / B-3 — accommodates scheduler jitter under contention without false failures)

### Assertion Density

- 23,881 `assert` statements across ~11,922 unit test functions: ~2.00 asserts per test
- 1,249 `pytest.raises` usages: strong negative-test culture (10%+ of test functions exercise error paths explicitly)

## Test Structure Summary

### Directory Layout

```
tests/
  conftest.py                    # Root fixtures, env setup, schemathesis xdist patch
  _shared/
    mocks.py                     # MockTask canonical (automation/polling) — HYG-003 complete
  unit/                          # ~490 test_*.py files
    api/                         # ~51 files: routes, middleware, preload, health, exports (6 committed post-PR38)
    auth/                        # ~6: bot_pat, audit, jwt, dual_mode
    automation/                  # ~47: events, polling, workflows, engine
    cache/                       # ~56: backends, dataframe, policies, circuit breaker
    clients/                     # ~36: data client, name resolver, task/section/user
    core/                        # ~10: registry, concurrency, retry
    dataframes/                  # ~49: builders, views, schemas, extractors
    detection/                   # 1: detection_cache
    lambda_handlers/             # ~16: warmer, checkpoint, workflow, reconciliation
    lifecycle/                   # ~15: engine, creation, completion, webhook
    metrics/                     # ~10: compute, registry, definitions, expr
    models/                      # ~40: business models, matching, contracts
    patterns/                    # 2
    persistence/                 # ~34: session, cascade, executor, graph, healing
    query/                       # ~21: engine, compiler, hierarchy, join
    reconciliation/              # ~5
    resolution/                  # ~7: strategies, field_resolver, budget
    search/                      # ~3
    services/                    # 22: universal_strategy split (4 files)
    transport/                   # ~7
    (flat)                       # 9: auth_providers, batch_adversarial, settings, etc.
  integration/                   # 33 test_*.py files
  validation/persistence/        # 5: concurrency, functional, error handling, performance
  synthetic/                     # 1: test_synthetic_coverage.py
  benchmarks/                    # 1: insights benchmark
  test_openapi_endpoint.py       # OpenAPI smoke
  test_openapi_fuzz.py           # Schemathesis property-based fuzz; xdist_group("fuzz")
  test_computation_spans.py      # Computation span assertions
```

### Test Distribution

| Suite | Files | Test Functions |
|---|---|---|
| unit/ | ~490 | ~11,922 |
| integration/ | 33 | ~500 |
| validation/ | 5 | ~80 |
| synthetic/ | 1 | ~10 |
| benchmarks/ | 1 | ~10 |
| root level | 3 | ~320 |
| **Total** | **~502** | **~12,842** |

Total assert statements: 23,881+. Total `pytest.raises`: 1,249.

### Heavily Tested Areas (High Test Density)

1. **cache/** — ~56 test files; circuit breaker, coalescer, backend drivers, dataframe tiers
2. **api/** — ~51 test files (including 6 committed exports cluster post-PR #38)
3. **dataframes/** — ~49 test files; cascade validator (highest-churn: 6 sessions)
4. **automation/** — ~47 test files; events pipeline, polling engine, workflow handlers
5. **services/** — 22 files; `test_universal_strategy*.py` (split across 4 files) is highest-churn hotspot (8 sessions)

### High-Churn Hotspot Files

| File | History |
|---|---|
| `tests/unit/services/test_universal_strategy.py` (+ 3 split files) | 8 sessions |
| `tests/unit/dataframes/builders/test_cascade_validator.py` | 6 sessions |
| `tests/unit/dataframes/views/test_cascade_view.py` | 4 sessions |
| `tests/unit/api/routes/test_resolver_status.py` | 3 sessions |
| `tests/test_openapi_fuzz.py` | 2 sessions; pass rate 5%→66%, now stabilized at xfail |

### Test Package Style

External tree style (separate `tests/` directory, not co-located with source). Tests import via `from autom8_asana...`. No `autom8_asana_test` package.

### Integration vs Unit Distinction

- **Unit tests**: Mock all external dependencies; `AsyncMock`, `MagicMock(spec=)` (HYG-002), SDK testing doubles; `SystemContext.reset_all()` enforces isolation
- **Integration-style** (most of `tests/integration/`): Wire real components together with mocked I/O
- **Live-API integration** (`@pytest.mark.integration`): Only 6 files marked
- **Validation tests** (`tests/validation/persistence/`): Persistence behavioral contracts (concurrency, ordering, error handling, performance)
- **Synthetic** (`tests/synthetic/`): Coverage gap detection
- **Benchmarks** (`tests/benchmarks/`): Performance benchmarks marked `@pytest.mark.benchmark`

### Special Test Types

- **Adversarial tests**: `test_*_adversarial.py` — failure cases, race conditions, boundary violations
- **Contract tests**: `test_*_contract.py` — behavioral guarantees (e.g., `test_idempotency_contracts.py`, `test_exports_contract.py`)
- **Span tests**: `test_*_spans.py` — OpenTelemetry instrumentation assertions
- **OpenAPI fuzz**: `tests/test_openapi_fuzz.py` — schemathesis/hypothesis (marked `fuzz`, `xfail(strict=False)`)
- **SCAR regression tests**: 35 invocations across 11 files (HYG-001), selectable via `pytest -m scar`; registered marker. Inviolable regression cluster: SCAR-001/005/006/010/010b/020/026/027, SCAR-WS8, S3-LOOP, TENSION-001.
- **Behavior-preservation tests**: `test_*_walk_predicate_property.py` — class-based tests anchoring behavior before/after refactors (T-04 pattern)

### SCAR Test Cluster

35 `@pytest.mark.scar` invocations across 11 test files (HYG-001 — verified at HEAD `8980bcd7`). The `scar` marker is registered in `pyproject.toml` and enables `pytest -m scar` selection. Files include `tests/unit/api/test_exports_auth_exclusion.py` (SCAR-WS8), `tests/unit/api/middleware/test_idempotency_finalize_scar.py`, `tests/unit/reconciliation/test_section_registry.py`.

## Knowledge Gaps

1. **Actual runtime coverage percentage** — `fail_under = 80` configured and enforced; project-crucible baseline was 87.59%, but no coverage report run during this audit cycle to confirm current state
2. **`tests/validation/persistence/` CI inclusion** — unknown whether this suite runs in the 4-shard PR matrix or only post-merge
3. **Whether `@pytest.mark.integration` gating is enforced in CI** — marker defined; CI config not examined for deselection enforcement
4. **`tests/synthetic/test_synthetic_coverage.py` purpose** — contents not read; filename suggests coverage gap detection
5. **`services/intake_*_service.py` service-layer isolation** — tested only through route tests; direct service error path coverage unknown
6. **Schemathesis 47 xfails pending triage** — pre-existing OpenAPI contract violations in `test_openapi_fuzz.py` that have not been resolved or categorized

```metadata
criteria_grades:
  coverage_gaps:
    grade: A
    pct: 92
    weight: 0.40
    notes: >
      All untested packages identified with criticality assessment. Critical paths assessed.
      Prioritized gap list produced. Lifecycle safety gap (loop_detector) flagged at #2.
      Incremental cycle: no new gaps introduced; all prior gaps unchanged at HEAD 8980bcd7.
  testing_conventions:
    grade: A
    pct: 93
    weight: 0.30
    notes: >
      xdist topology fully documented including new --dist=loadgroup switch and 3 xdist_group
      markers. MockTask HYG-003 complete verified. MagicMock(spec=) count confirmed 136.
      Performance budget widening (2ms contention) documented. Stale doc drift resolved.
  test_structure_summary:
    grade: A
    pct: 92
    weight: 0.30
    notes: >
      Distribution summary, heavily tested areas, directory layout, integration vs unit
      distinction all current. .test_durations refresh cadence documented under CI topology.
overall_grade: A
overall_pct: 92.3
confidence: 0.92
source_hash: "8980bcd7"
incremental_notes: >
  Major change: xdist topology switched from --dist=load to --dist=loadgroup (commit 149d3673).
  xdist_group markers inventory expanded from 1 to 3 groups (added workflow_handler, query_routes).
  Prior doc-drift (stale loadfile comment) confirmed resolved in pyproject.toml.
  .test_durations refresh cadence documented via durations-refresh.yml weekly cron.
  Performance budget: TestAC006 contention budget widened 1ms->2ms (commit f37802f2).
  Marker counts (parametrize=148, scar=35, MagicMock(spec=)=136) verified at HEAD.
  Import-order ruff fixes across 4 test files: no semantic test changes.
  Knowledge gap #7 (stale loadfile comment) removed — resolved.
```
