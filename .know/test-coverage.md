---
domain: test-coverage
generated_at: "2026-04-29T12:30Z"
expires_after: "7d"
source_scope:
  - "./tests/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "6b303485"
confidence: 0.93
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

The test suite contains 570 `test_*.py` files under `tests/` (505 in `tests/unit/` alone). Source tree has 24 top-level packages under `src/autom8_asana/`. 22 of 24 source packages have dedicated test directories or direct flat test files.

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
- `lifecycle/loop_detector.py` — no `test_loop_detector.py`; safety mechanism for lifecycle engine
- `lifecycle/observation_store.py` — no `test_observation_store.py`; persistence for lifecycle observations

**services** — 4 of ~22 service modules lack dedicated test files:
- `services/entity_context.py` — no direct test
- `services/intake_create_service.py` — tested only through route layer
- `services/intake_resolve_service.py` — same pattern
- `services/intake_custom_field_service.py` — same pattern

**models (top-level)**: 15 Asana resource model files (`task.py`, `project.py`, etc.) have no dedicated test files. Covered indirectly through all tests that instantiate them; `tests/unit/models/test_models.py` covers basic import/instantiation.

**models/business** — 4 modules without dedicated tests: `dna.py`, `mixins.py`, `videography.py`, `reconciliation.py`. Detection tier files (`tier1`–`tier4`) covered via detection_cache and adversarial tests.

### Exports Feature Test Cluster (as of 2026-04-29, post-PR #38)

Six committed test files in `tests/unit/api/` cover `api/routes/exports.py` and `api/routes/_exports_helpers.py`. All 6 files are tracked post-PR #38 merge (commit `80256049`).

| File | Focus |
|---|---|
| `test_exports_contract.py` | `ExportRequest`/`ExportOptions` Pydantic contract (AC-12, AC-13, AC-15, AC-16) |
| `test_exports_auth_exclusion.py` | JWT middleware PAT-exclusion regression (DEF-08 SCAR-WS8) |
| `test_exports_format_negotiation.py` | Content-type format negotiation behavior |
| `test_exports_handler.py` | `export_handler` function behavior |
| `test_exports_helpers.py` | `_exports_helpers.py` date-predicate translation (ESC-1) |
| `test_exports_helpers_walk_predicate_property.py` | Behavior-preservation class-based tests for `_walk_predicate` refactor (T-04a, commit `f4fd18f6`) |

**Note on inventory history**: The prior knowledge entry (source_hash `8c58f930`) cited "5 untracked test files." The 6th file `test_exports_helpers_walk_predicate_property.py` was committed at `f4fd18f6` but absent from that inventory (HYG-001 detection gap — pre-S4 gate did not enforce untracked-file audit). Post-PR #38, all 6 are committed. Source files (`exports.py`, `_exports_helpers.py`) are also committed.

**CHANGE-001 — duplicate test removal** (commit `321909c1`): The property preservation test file had 2 silent test-method overwrites:
- Removed lines 115-118: duplicate `test_not_group_of_comparison_match` in `TestPredicateReferencesFieldBehavior`
- Removed lines 215-218: duplicate `test_not_group_with_date_returns_true` in `TestContainsDateOpBehavior`

Both duplicates carried comments asserting "NotGroup.not_ only accepts Comparison (Pydantic validated model constraint)" — a claim that is EMPIRICALLY FALSE per SCAR-DISCRIMINATOR-001 (see scar-tissue.md). Removing them closed FLAG-1 and FLAG-3. Post-CHANGE-001: 36 effective test functions, 0 silent overwrites. (The file name contains "property" but uses class-based pytest fixtures, NOT `@hypothesis.given`.)

### Prioritized Gap List (Highest-Risk First)

1. **`services/intake_*_service.py` (3 modules)** — critical production path. Tested only through HTTP route layer; service-layer error paths and boundary conditions unverified in isolation.
2. **`services/entity_context.py`** — context carrier used across service layer with no direct unit test.
3. **`lifecycle/loop_detector.py`** — loop detection in lifecycle engine is a safety mechanism; no direct test.
4. **`lifecycle/observation_store.py`** — persistence for lifecycle observations; no direct test.
5. **`_defaults/` auth and observability** — thin adapter wrappers; indirect coverage exists but no dedicated test.
6. **`protocols/`** — 9 Protocol class definitions; no explicit protocol-conformance tests.

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
- The 80% floor is a CI hard gate.

## Testing Conventions

### Test Runner and Configuration

- **Runner**: `pytest` with `asyncio_mode = "auto"` (all `async def test_*` execute without `@pytest.mark.asyncio`)
- **Test command**: `pytest` from project root; `testpaths = ["tests"]`
- **Parallel execution**: `pytest-xdist` with `--dist=loadfile` (keeps tests from same file on single worker — required for process-global state isolation in `tests/unit/lambda_handlers/test_workflow_handler.py` and `tests/test_openapi_fuzz.py`)
- **Timeout**: 60 seconds per test; `timeout_method = "thread"`
- **Coverage**: `pytest --cov`; `fail_under = 80`, branch coverage, source `src/autom8_asana`

xdist was re-enabled by commit `affbf5a5`; commit `8fd0aefb` switched `--dist=load` to `--dist=loadfile`.

### Test Naming

- Function-based tests dominant; subset use `class Test*` organization (e.g., `test_exports_contract.py` uses `class TestExportRequestForbiddenFields`, `test_exports_helpers_walk_predicate_property.py` uses 4 `class Test*` groups)
- Naming pattern: `test_{thing_being_tested}_{condition}` — e.g., `test_cascade_validator_corrects_business_name_from_task_name`, `test_tier2_get_async_returns_model`
- Async tests: `async def test_*` used broadly; ~11,922 total test function definitions in unit/
- Class-based pattern used for grouping related contract assertions and behavior-preservation clusters

### Markers

| Marker | Count | Meaning |
|---|---|---|
| `@pytest.mark.parametrize` | 132 call-sites (57 files) | Parameterized test cases; 11.6% of test files |
| `@pytest.mark.integration` | ~42 usages | Live API tests |
| `@pytest.mark.usefixtures` | ~38 usages | Fixture injection via decorator |
| `@pytest.mark.slow` | ~23 usages | Deselectable: `-m "not slow"` |
| `@pytest.mark.skip` | ~10 usages | Explicit skips with reason strings |
| `@pytest.mark.skipif` | ~4 usages | Conditional: `not FAKEREDIS_AVAILABLE`, `not MOTO_AVAILABLE`, `not _HAS_HYPOTHESIS` |
| `@pytest.mark.benchmark` | ~3 usages | Performance benchmarks |
| `@pytest.mark.fuzz` | 1 module | OpenAPI hypothesis fuzz |
| `@pytest.mark.xfail` | 1 module (`test_openapi_fuzz.py`) | 46 pre-existing schemathesis violations |

Parametrize adoption: 11.6% of test files; 132 call-sites. Low parametrize adoption relative to total test count is a known anti-pattern (project-crucible sprint-6: 687 `@pytest.fixture` definitions vs 132 `@pytest.mark.parametrize` usages).

### Property Tests (Hypothesis)

Only **1 `@hypothesis.given` decorator** found in `tests/unit/` — `tests/unit/persistence/test_reorder.py:288`. The test `test_property_moves_produce_desired_order` was stabilized by TRIAGE-005 (commit `ec7c7f10`):

- **Before**: `@settings(max_examples=200)` (default deadline, random seed)
- **After**: `@settings(max_examples=100, deadline=None, derandomize=True)`
- **Rationale**: Under accumulated full-suite memory pressure (~284s elapsed), hypothesis examples exceeded the 200ms default deadline. Deterministic seed eliminates flake; `deadline=None` removes per-example pressure; halved example count retains robust property coverage.

`tests/test_openapi_fuzz.py` is the other hypothesis consumer: schemathesis-driven OpenAPI fuzz with `max_examples` capped and `derandomize=True` (FR-10).

Note: `test_exports_helpers_walk_predicate_property.py` uses the word "property" in its name but is a class-based pytest test file — it does NOT use `@hypothesis.given`. The 4 test classes exercise `PredicateNode` walker behavior preservation across all node shapes (Comparison, AndGroup, OrGroup, NotGroup).

### Mocking Conventions

- **`AsyncMock`** (stdlib `unittest.mock`): all async method mocking; dominant pattern
- **`MagicMock`**: sync objects (services, clients, config)
- **`patch`** (`unittest.mock.patch`): context manager and decorator in 96+ files
- **`respx`**: httpx mocking; ~16 files for HTTP call interception
- **`fakeredis`**: Redis mocking; conditionally available
- **`moto`**: AWS/S3 mocking; conditionally available
- **SDK testing doubles**: `autom8y_log.testing.MockLogger`, `autom8y_cache.testing.MockCacheProvider`
- **`schemathesis` + `hypothesis`**: OpenAPI property-based fuzzing

### Fixture Infrastructure

- 687 `@pytest.fixture` definitions; 15 `conftest.py` files
- Fixture scopes: `function` (default), `session` (`_bootstrap_session`), `module` (API conftest `app` fixture)

**Root conftest** (`tests/conftest.py`):

| Fixture | Scope | Purpose |
|---|---|---|
| `mock_http` | function | `MockHTTPClient` with `AsyncMock` for 8 HTTP methods |
| `config` | function | `AsanaConfig()` |
| `auth_provider` | function | `MockAuthProvider` returning `"test-token"` |
| `logger` | function | `MockLogger` from `autom8y_log.testing` |
| `_bootstrap_session` | session (autouse) | Bootstraps `ProjectTypeRegistry` + rebuilds Pydantic `NameGid` forward refs once per session |
| `reset_all_singletons` | function (autouse) | `SystemContext.reset_all()` before/after every test — complete isolation |

**Environment setup**: Root conftest force-sets `AUTOM8Y_ENV=test` (relaxes GID pattern) and `AUTH__JWKS_URL=http://localhost:8000/...`. Patches `schemathesis.pytest.xdist.XdistReportingPlugin.pytest_testnodedown` at class-method level inside `pytest_configure` (R4-FIX-002).

**Sub-package conftests** provide domain-specific fixtures: api/, clients/, clients/data/, cache/, dataframes/, automation/polling/, automation/workflows/, lifecycle/, persistence/, resolution/, reconciliation/.

### Test Isolation Pattern

- `SystemContext.reset_all()` via autouse fixture resets all registries, caches, singletons between every test
- Per-test resets for `EntityProjectRegistry`, `reset_auth_client`, `clear_bot_pat_cache`
- Environment variables controlled via `os.environ` in conftest (session-scoped)

### Assertion Density

- 23,881 `assert` statements across ~11,922 unit test functions: ~2.00 asserts per test
- 1,249 `pytest.raises` usages: strong negative-test culture (10%+ of test functions exercise error paths explicitly)
- 160 helper functions named `make_*`/`create_*`/`build_*` — test data factory patterns

### Special Test Types

- **Adversarial tests**: `test_*_adversarial.py` — failure cases, race conditions, boundary violations
- **Contract tests**: `test_*_contract.py` — behavioral guarantees (e.g., `test_idempotency_contracts.py`, `test_exports_contract.py`)
- **Span tests**: `test_*_spans.py` — OpenTelemetry instrumentation assertions
- **OpenAPI fuzz**: `tests/test_openapi_fuzz.py` — schemathesis/hypothesis (marked `fuzz`, `xfail(strict=False)`)
- **SCAR regression tests**: 33+ inviolable regression tests (SCAR-001/005/006/010/010b/020/026/027, SCAR-WS8, S3-LOOP, TENSION-001) flagged as sacred constraints
- **Behavior-preservation tests**: `test_*_walk_predicate_property.py` — class-based tests anchoring behavior before/after refactors (T-04 pattern)

### No File-Based Test Data

No `fixtures/`, `testdata/`, or `data/` directories in `tests/`. All test data inline via `MockTask`, fixture functions, builder/helper patterns. No golden files or YAML/JSON fixture files.

## Test Structure Summary

### Directory Layout

```
tests/
  conftest.py                    # Root fixtures, env setup, schemathesis xdist patch
  _shared/
    mocks.py                     # MockTask (automation/polling)
  unit/                          # 505 test_*.py files
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
  test_openapi_fuzz.py           # Schemathesis property-based fuzz
  test_computation_spans.py      # Computation span assertions
```

### Test Distribution

| Suite | Files | Test Functions |
|---|---|---|
| unit/ | 505 | ~11,922 |
| integration/ | 33 | ~500 |
| validation/ | 5 | ~80 |
| synthetic/ | 1 | ~10 |
| benchmarks/ | 1 | ~10 |
| root level | 3 | ~320 |
| **Total** | **570** | **~12,842** |

Total assert statements: 23,881+. Total `pytest.raises`: 1,249.

### Heavily Tested Areas (High Test Density)

1. **cache/** — ~56 test files; circuit breaker, coalescer, backend drivers, dataframe tiers
2. **api/** — ~51 test files (including 6 committed exports cluster post-PR #38)
3. **dataframes/** — ~49 test files; cascade validator (highest-churn: 6 sessions)
4. **automation/** — ~47 test files; events pipeline, polling engine, workflow handlers
5. **services/** — 22 files; `test_universal_strategy*.py` (split across 4 files: core, null_slot, spans, status) is highest-churn hotspot (8 sessions)

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

- **Unit tests**: Mock all external dependencies; `AsyncMock`, `MagicMock`, SDK testing doubles; `SystemContext.reset_all()` enforces isolation
- **Integration-style** (most of `tests/integration/`): Wire real components together with mocked I/O
- **Live-API integration** (`@pytest.mark.integration`): Only 6 files marked
- **Validation tests** (`tests/validation/persistence/`): Persistence behavioral contracts (concurrency, ordering, error handling, performance)
- **Synthetic** (`tests/synthetic/`): Coverage gap detection
- **Benchmarks** (`tests/benchmarks/`): Performance benchmarks marked `@pytest.mark.benchmark`

### SCAR Test Cluster

33+ inviolable regression tests preserved as sacred constraints. Files include `tests/unit/api/test_exports_auth_exclusion.py` (SCAR-WS8, committed post-PR #38), `tests/unit/api/middleware/test_idempotency_finalize_scar.py`, `tests/unit/reconciliation/test_section_registry.py`.

`test_exports_auth_exclusion.py` (SCAR-WS8) was previously untracked at source_hash `8c58f930`; it is now committed and part of the SCAR regression cluster.

## Knowledge Gaps

1. **Actual runtime coverage percentage** — `fail_under = 80` configured and enforced, but no coverage report run during this audit
2. **CI sharding behavior** — `pytest-split` and `pytest-xdist` both present; shard-per-worker coverage fragment merging not verified
3. **`tests/validation/persistence/` CI inclusion** unknown
4. **Whether `@pytest.mark.integration` gating is enforced in CI** — marker defined but CI config not examined
5. **`tests/synthetic/test_synthetic_coverage.py` purpose** — contents not read; filename suggests coverage gap detection
6. **`services/intake_*_service.py` service-layer isolation** — tested only through route tests; direct service error path coverage unknown
7. **Exports fixture topology** — `tests/unit/api/conftest.py` provides shared fixtures; whether exports test cluster consumes conftest fixtures without duplication not fully verified (INVESTIGATE: glint-exports-helpers-fixture-topology)

## Incremental Update Log

### Cycle 1 — 2026-04-29 (post-PR #38 merge, source_hash `6b303485`)

**Corrections applied:**
- Lines 58-68 (stale): "Five new untracked test files" → "Six committed test files (all tracked post-PR #38)". Added 6th file `test_exports_helpers_walk_predicate_property.py` (T-04a, commit `f4fd18f6`). Noted HYG-001 detection gap.
- Line 68 (stale): "These files are untracked. Source files also untracked." → removed; both source and test files are committed post-PR #38.
- Line 199/246 (stale): "5 untracked" → "6 committed post-PR38"
- Line 281 (stale): "5 untracked exports test files" → removed from knowledge gaps; now item 7 is exports fixture topology (INVESTIGATE status)
- Total file counts updated: 493 → 570 total, 449 → 505 unit/

**New entries added:**
- CHANGE-001 (commit `321909c1`): removal of 2 silent test-method overwrites in `test_exports_helpers_walk_predicate_property.py` → 36 effective test functions. Closes FLAG-1/FLAG-3.
- TRIAGE-005 (commit `ec7c7f10`): `test_reorder.py:288` hypothesis settings stabilized from `@settings(max_examples=200)` to `@settings(max_examples=100, deadline=None, derandomize=True)`.
- Hypothesis inventory: 1 `@given` decorator in unit tests (`test_reorder.py`); clarified that `test_exports_helpers_walk_predicate_property.py` is NOT a hypothesis test despite its name.
- Property tests section added to Testing Conventions.
- Behavior-preservation test type added to Special Test Types.
- SCAR-WS8 confirmation: `test_exports_auth_exclusion.py` now committed and part of SCAR cluster.
