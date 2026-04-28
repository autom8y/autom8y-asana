---
domain: test-coverage
generated_at: "2026-04-24T00:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "acff02ab"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "1471b813f0f58342c542d2e8c9cd92aba095afec134846cda625c3fa545ec9fe"
---

# Codebase Test Coverage

## Coverage Gaps

### Package-Level Coverage Map

The test suite contains 555 Python files in `tests/` (488 named `test_*.py`, plus 15 conftest files, 62 `__init__.py` files, and shared mocks). Source tree has 478 Python files across 26 packages. 22 of 26 source packages have dedicated test directories.

**Packages with zero dedicated test files:**

| Source Package | Source Files (non-init) | Assessment |
|---|---|---|
| `src/autom8_asana/_defaults/` | 4 (`auth.py`, `cache.py`, `log.py`, `observability.py`) | Indirect coverage via client and config tests; thin adapter wrappers |
| `src/autom8_asana/batch/` | 2 (`client.py`, `models.py`) | Covered indirectly through `tests/unit/test_batch_adversarial.py` and integration tests |
| `src/autom8_asana/observability/` | 3 (`context.py`, `correlation.py`, `decorators.py`) | Covered via `tests/unit/test_observability.py` and span assertion tests |
| `src/autom8_asana/protocols/` | 8 protocol definition files | Protocol types imported/satisfied in cache, client, and persistence tests; runtime-only check |

**Single-module packages not tested directly**: `src/autom8_asana/errors.py`, `src/autom8_asana/settings.py`. `errors.py` tested indirectly via exception tests.

### Module-Level Gaps Within Covered Packages

**lifecycle** — 2 of 17 modules unmatched:
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/lifecycle/loop_detector.py` — no `test_loop_detector.py`
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/lifecycle/observation_store.py` — no `test_observation_store.py`
- All 15 other lifecycle modules have direct test counterparts

**services** — 4 of 21 service modules lack a dedicated test file:
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/services/entity_context.py` — no `test_entity_context.py`
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/services/intake_create_service.py` — tested via route tests but no direct service test
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/services/intake_resolve_service.py` — same pattern
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/src/autom8_asana/services/intake_custom_field_service.py` — same pattern
- `resolver.py` tested via `tests/unit/api/routes/test_resolver_status.py`

**lambda_handlers** — 11 of 12 handler files have dedicated tests; only `story_warmer.py` maps to `test_story_warming.py` (naming variation).

**models (top-level Asana resource models)**: `attachment.py`, `base.py`, `common.py`, `custom_field.py`, `goal.py`, `portfolio.py`, `project.py`, `section.py`, `story.py`, `tag.py`, `task.py`, `team.py`, `user.py`, `webhook.py`, `workspace.py` — no dedicated test files. Tested indirectly through all tests that instantiate them. `test_models.py` at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/unit/models/test_models.py` covers basic import/instantiation.

**models/business** — 4 modules without dedicated tests: `dna.py`, `mixins.py`, `videography.py`, `reconciliation.py`. Detection tier files (`tier1.py`–`tier4.py`) covered via `test_detection.py`.

### Prioritized Gap List (Highest-Risk First)

1. **`services/intake_create_service.py`, `intake_resolve_service.py`, `intake_custom_field_service.py`** — intake path is a critical production path (task creation, resolution) tested only through HTTP route layer; service-layer error paths and boundary conditions unverified directly.
2. **`services/entity_context.py`** — context carrier for entity operations; used across service layer with no direct unit test.
3. **`lifecycle/loop_detector.py`** — loop detection in lifecycle engine is a safety mechanism; no direct test.
4. **`lifecycle/observation_store.py`** — persistence for lifecycle observations; no direct test.
5. **`_defaults/` auth and observability** — no tests, though thin wrappers.
6. **`protocols/`** — 8 Protocol class definitions; validated only by satisfying classes elsewhere.

### Integration Test Coverage

`@pytest.mark.integration` appears on 42 marker usages across 6 files:
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/integration/test_lifecycle_smoke.py`
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/integration/test_batch_api.py`
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/integration/automation/polling/test_action_executor_integration.py`
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/integration/automation/polling/test_trigger_evaluator_integration.py`
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/integration/automation/polling/test_end_to_end.py`
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/integration/automation/polling/__init__.py`

Most `tests/integration/` files do NOT carry `@pytest.mark.integration` — integration-style tests (real wiring, no live API) but not live-API-gated.

Packages with no integration or validation tests: `auth`, `core`, `models`, `metrics`, `query`, `patterns`, `transport`, `search`, `reconciliation`.

## Testing Conventions

### Test Runner and Configuration

- **Runner**: `pytest` with `asyncio_mode = "auto"` — all `async def test_*` functions run automatically without `@pytest.mark.asyncio`
- **Test command**: `pytest` from project root (or `python -m pytest`); `testpaths = ["tests"]`
- **Parallel execution**: `pytest-xdist` with `--dist=loadfile` (keeps tests from same file on single worker; required for process-global state isolation)
- **Timeout**: 60 seconds per test; `timeout_method = "thread"`
- **Coverage**: `pytest --cov` or `pytest-cov`; `fail_under = 80`, branch coverage enabled, source `src/autom8_asana`
- **Coverage exclusions**: `pragma: no cover`, `if TYPE_CHECKING:`, `@abstractmethod`, `raise NotImplementedError`, `if __name__ == "__main__":`

### Test Naming

- Function-based tests dominant: 468 files use `def test_` or `async def test_`; 32 files use `class Test*` organization
- Naming pattern: `test_{thing_being_tested}_{condition}` — e.g., `test_cascade_validator_corrects_business_name_from_task_name`, `test_tier2_get_async_returns_model`
- Async tests: `async def test_*` used broadly (12,333 total test functions counted)
- Class-based pattern used for grouping: `class TestQueryEngineExecuteRows`, `class TestDataFrameCacheGetAsync`

### Markers

| Marker | Count | Meaning |
|---|---|---|
| `@pytest.mark.parametrize` | 131 usages | Parameterized cases; very common |
| `@pytest.mark.integration` | 42 usages | Live API tests (small subset of `tests/integration/`) |
| `@pytest.mark.usefixtures` | 38 usages | Fixture injection via decorator |
| `@pytest.mark.slow` | 23 usages | Deselectable: `-m "not slow"` |
| `@pytest.mark.skip` | 10 usages | Explicit skips (with reason strings) |
| `@pytest.mark.skipif` | 4 usages | Conditional: `not FAKEREDIS_AVAILABLE`, `not MOTO_AVAILABLE`, `not _HAS_HYPOTHESIS` |
| `@pytest.mark.benchmark` | 3 usages | Performance benchmarks |

### Mocking Conventions

- **`AsyncMock`** (stdlib `unittest.mock`): used for all async method mocking
- **`MagicMock`**: used for sync objects (services, clients, config)
- **`patch`** (`unittest.mock.patch`): used via context manager and decorator in 96+ files
- **`respx`**: httpx mocking; used in 16 files for HTTP call interception
- **`fakeredis`**: Redis mocking; conditionally available (`skipif not FAKEREDIS_AVAILABLE`)
- **`moto`**: AWS/S3 mocking; conditionally available (`skipif not MOTO_AVAILABLE`)
- SDK testing mocks: `autom8y_log.testing.MockLogger`, `autom8y_cache.testing.MockCacheProvider` — SDK-provided test doubles that capture structured log entries and cache operations

### Fixture Infrastructure

- 205 files declare `@pytest.fixture`; 15 `conftest.py` files across the tree
- Fixture scopes: `function` (default, most common), `session` (`_bootstrap_session`), `module` (API conftest `app` fixture)

**Root conftest** (`/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/conftest.py`) provides:

| Fixture | Scope | Purpose |
|---|---|---|
| `mock_http` | function | `MockHTTPClient` with `AsyncMock` for 8 HTTP methods |
| `config` | function | `AsanaConfig()` |
| `auth_provider` | function | `MockAuthProvider` returning `"test-token"` |
| `logger` | function | `MockLogger` from `autom8y_log.testing` |
| `_bootstrap_session` | session (autouse) | Bootstraps `ProjectTypeRegistry` + rebuilds all Pydantic model `NameGid` forward refs once per session |
| `reset_all_singletons` | function (autouse) | `SystemContext.reset_all()` before and after every test — complete singleton/registry isolation |

**Environment setup**: Root conftest force-sets `AUTOM8Y_ENV=test` before model imports (relaxes GID pattern validation) and `AUTH__JWKS_URL=http://localhost:8000/...` (bypasses production URL guard). Also patches `schemathesis.pytest.xdist.XdistReportingPlugin.pytest_testnodedown` to handle missing `workeroutput` on crashed xdist workers.

**Sub-package conftests** provide domain-specific fixtures:
- `tests/unit/api/conftest.py`: module-scoped `app` fixture with mocked lifespan, `EntityProjectRegistry.reset()`
- `tests/unit/clients/conftest.py`: `MockCacheProvider` extending SDK's `MockCacheProvider`, client instances
- `tests/unit/cache/conftest.py`, `tests/unit/dataframes/conftest.py`, etc.: per-domain setup

### Shared Mock Objects

- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/tests/_shared/mocks.py`: `MockTask` — plain-object mock of an Asana task with date/completion fields; used by automation/polling tests

### Test Isolation Pattern

- `SystemContext.reset_all()` via `autouse=True` `reset_all_singletons` — resets all registries, caches, singletons between every test
- Per-test singleton resets for `EntityProjectRegistry`, auth clients, bot PAT cache
- Environment variables controlled via `os.environ` in conftest (session-scoped)

### Special Test Types

- **Adversarial tests**: `test_*_adversarial.py` — failure cases, race conditions (e.g., `test_action_batch_adversarial.py`, `test_reorder_adversarial.py`)
- **Contract tests**: `test_*_contract.py` — behavioral guarantees (e.g., `test_idempotency_contracts.py`, `test_reconciliation_contract.py`)
- **Span tests**: `test_*_spans.py` — OpenTelemetry instrumentation assertions (e.g., `test_universal_strategy_spans.py`, `test_resolver_spans.py`)
- **OpenAPI fuzz**: `tests/test_openapi_fuzz.py` — schemathesis/hypothesis-based OpenAPI fuzzing (marked `fuzz`, excluded from sharded CI runs)

### No File-Based Test Data

No `fixtures/`, `testdata/`, `data/` directories exist in `tests/`. All test data constructed inline via `MockTask`, fixture functions, and builder patterns. No golden files or YAML/JSON fixture files.

## Test Structure Summary

### Directory Layout

```
tests/
  conftest.py                    # Root fixtures, env setup, schemathesis patch
  _shared/
    mocks.py                     # MockTask (used by automation/polling)
  unit/                          # 444 test_*.py files
    api/                         # 60 files: routes, middleware, preload, health, client pool
    auth/                        # 6 files: bot_pat, audit, jwt, dual_mode
    automation/                  # 47 files: events, polling, workflows, engine, templates
    cache/                       # 56 files: backends, dataframe, policies, circuit breaker
    clients/                     # 36 files: data client, name resolver, task/section/user
    core/                        # 10 files: registry, concurrency, retry
    dataframes/                  # 49 files: builders, views, schemas, extractors
    detection/                   # 1 file
    lambda_handlers/             # 16 files: warmer, checkpoint, workflow, reconciliation
    lifecycle/                   # 15 files: engine, creation, completion, webhook
    metrics/                     # 10 files: compute, registry, definitions, expr
    models/                      # 40 files: business models, matching, contracts
    patterns/                    # 2 files: async_method, error_classification
    persistence/                 # 34 files: session, cascade, executor, graph, healing
    query/                       # 21 files: engine, compiler, hierarchy, join
    reconciliation/              # 5 files: contract, executor, processor
    resolution/                  # 7 files: strategies, field_resolver, budget
    search/                      # 3 files: models, service, client integration
    services/                    # 22 files: universal_strategy, section, gid, entity
    transport/                   # 7 files: asana_http, aimd, config_translator
  integration/                   # 33 test_*.py files (not all marked @pytest.mark.integration)
    api/                         # 2 files: envelope convergence, preload manifest
    automation/polling/          # 3 files (marked @pytest.mark.integration)
    automation/workflows/        # 1 file: conversation audit e2e
    events/                      # 1 file: SQS integration
    persistence/                 # 1 file: action batch integration
    (root)                       # 25 files: cache, detection, entity resolver, hydration, etc.
  validation/
    persistence/                 # 5 files: concurrency, functional, error handling, performance
  synthetic/                     # 1 file: test_synthetic_coverage.py
  benchmarks/                    # 3 files: batch, cache, insights
```

### Test Distribution

| Suite | test_*.py Files | Total .py Files |
|---|---|---|
| unit/ | 444 | ~510 |
| integration/ | 33 | ~42 |
| validation/ | 5 | ~8 |
| synthetic/ | 1 | ~3 |
| benchmarks/ | 3 | ~5 |
| root level | 3 | ~3 |
| **Total** | **488** | **555** |

Total test functions: ~12,333

### Heavily Tested Areas (High Test Density)

1. **cache/** — 56 test files; covers circuit breaker, coalescer, backend drivers, dataframe tiers, progressive/memory tier, schema version validation
2. **api/** — 60 test files; broadest single package; routes, middleware, preload, health, fleet query adapter
3. **dataframes/** — 49 test files; cascade validator (hotspot: 6 sessions of changes), cascade view (4 sessions), builders, schemas
4. **automation/** — 47 test files; events pipeline, polling engine, workflow handlers, seeding
5. **services/** — 22 files but high complexity; `test_universal_strategy*.py` (8 sessions of changes; ~75 test functions across 4 split files) is the highest-churn hotspot

### High-Churn Hotspot Files

| File | History | Notes |
|---|---|---|
| `tests/unit/services/test_universal_strategy*.py` (4 files) | 8 sessions of changes | Core field resolution strategy; split across 4 files by concern |
| `tests/unit/dataframes/builders/test_cascade_validator.py` | 6 sessions | Cascade field validation with schema-driven correction |
| `tests/unit/dataframes/views/test_cascade_view.py` | 4 sessions | View layer over cascaded fields |
| `tests/unit/api/routes/test_resolver_status.py` | 3 sessions | HTTP status contract for resolver route |

### Test Package Style

All tests in a separate `tests/` tree (not co-located with source). Tests import source via `from autom8_asana...` (469 of 555 files). External test package style — no `autom8_asana_test` or `test_autom8_asana` package; tests do not use relative imports from source packages.

### Integration vs Unit Distinction

- **Unit tests** (`tests/unit/`): Mock all external dependencies; use `AsyncMock`, `MagicMock`, SDK testing doubles; `SystemContext.reset_all()` enforces isolation
- **Integration-style tests** (`tests/integration/`): Wire real components together with mocked I/O; most do not require live Asana API
- **Live-API integration** (`@pytest.mark.integration`): Only 6 files explicitly marked; automation/polling integration tests and lifecycle/batch smoke tests
- **Validation tests** (`tests/validation/persistence/`): Persistence-specific behavioral contracts (concurrency, ordering, error handling, performance)
- **Synthetic** (`tests/synthetic/`): Coverage synthesis tests — purpose is coverage gap detection
- **Benchmarks** (`tests/benchmarks/`): Performance benchmarks marked `@pytest.mark.benchmark`

### No TestMain Pattern

No `conftest.py` uses a `TestMain` equivalent. Bootstrap handled via `_bootstrap_session` (session-scoped autouse fixture) running once per pytest session.

## Knowledge Gaps

1. **Actual runtime coverage percentage** — `fail_under = 80` is configured and CI enforces it, but no coverage report was run during this audit. Branch coverage percentage by package unknown.
2. **`tests/synthetic/test_synthetic_coverage.py` purpose** — filename suggests synthetic coverage tracking but contents not read.
3. **CI sharding behavior** — `pytest-split` and `pytest-xdist` both present; shard-per-worker CI run behavior (coverage fragment merging) not verified.
4. **`tests/validation/persistence/` CI inclusion** — whether validation tests run in the same CI job as unit tests not visible from static analysis.
5. **Whether `@pytest.mark.integration` gating is enforced in CI** — marker defined but CI configuration file not examined.
6. **Missing `test_loop_detector.py` and `test_observation_store.py`** — may be intentional (infrastructure code not requiring direct unit test) or genuine gap.
7. **`services/intake_*_service.py` service-layer isolation** — intake services tested through route tests but direct service error path coverage unknown.
