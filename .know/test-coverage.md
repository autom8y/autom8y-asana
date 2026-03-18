---
domain: test-coverage
generated_at: "2026-03-18T11:50:56Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "d234795"
confidence: 0.85
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Test Coverage

## Coverage Gaps

### Source Package Coverage Map

The following table maps each source package to its test coverage status. "Direct" means a dedicated test directory exists. "Indirect" means the package is exercised via imports in other test files. "None" means no observed test coverage.

| Source Package | Src Files | Test Status | Test Location |
|---|---|---|---|
| `_defaults` | 4 | Indirect | `tests/unit/clients/`, `tests/unit/cache/` |
| `api` | 12 | Direct | `tests/unit/api/` (32 test files) |
| `api/preload` | 3 | Direct | `tests/unit/api/preload/` |
| `api/routes` | 17 | Direct | `tests/unit/api/routes/` (6 test files) |
| `auth` | 5 | Direct | `tests/unit/auth/` (6 test files) |
| `automation/events` | 6 | Direct | `tests/unit/automation/events/` (9 test files) |
| `automation/polling` | 7 | Direct | `tests/unit/automation/polling/`, integration |
| `automation/workflows` | 9 | Direct | `tests/unit/automation/workflows/` (7 test files) |
| `batch` | 2 | Indirect | `tests/integration/test_batch_api.py`, `tests/integration/persistence/test_action_batch_integration.py` |
| `cache/backends` | 4 | Indirect | `tests/unit/cache/test_memory_backend.py`, `test_redis_backend.py`, `test_s3_backend.py` |
| `cache/dataframe` | 6 | Direct | `tests/unit/cache/dataframe/` (10 test files) |
| `cache/integration` | 14 | Indirect | Multiple via `autom8_adapter`, `mutation_invalidator`, etc. |
| `cache/models` | 11 | Indirect | `tests/unit/cache/test_entry.py`, `test_events.py`, `test_metrics.py`, `test_mutation_event.py`, `test_versioning.py`, etc. |
| `cache/policies` | 5 | Indirect | `tests/unit/cache/test_coalescer.py`, `test_freshness_policy.py`, `test_staleness.py`, `test_lightweight_checker.py` |
| `cache/providers` | 2 | Direct | `tests/unit/cache/providers/` (1 test file) |
| `clients` | 19 | Direct | `tests/unit/clients/` (17 test files) |
| `clients/data` | 10 | Direct | `tests/unit/clients/data/` (17 test files) |
| `core` | 18 | Direct | `tests/unit/core/` (10 test files) |
| `dataframes` | 7 | Direct | `tests/unit/dataframes/` (30+ test files) |
| `dataframes/builders` | 9 | Direct | `tests/unit/dataframes/builders/` (8 test files) |
| `dataframes/extractors` | 5 | Indirect | `tests/unit/dataframes/test_extractors.py` |
| `dataframes/models` | 3 | Indirect | `tests/unit/dataframes/test_base_schema.py`, `test_cascade_registry_audit.py` |
| `dataframes/resolver` | 6 | Indirect | `tests/unit/dataframes/test_cascading_resolver.py`, `tests/integration/test_cascading_field_resolution.py` |
| `dataframes/schemas` | 7 | Indirect | 67 test imports; `tests/unit/dataframes/test_contact_schema.py`, `tests/integration/test_schema_contract.py` |
| `dataframes/views` | 3 | Direct | `tests/unit/dataframes/views/` (3 test files) |
| `lambda_handlers` | 7 | Direct | `tests/unit/lambda_handlers/` (9 test files) |
| `lifecycle` | 11 | Direct | `tests/unit/lifecycle/` (12 test files) |
| `metrics` | 6 | Direct | `tests/unit/metrics/` (9 test files) |
| `metrics/definitions` | 1 | None identified | No direct or indirect imports in tests found |
| `models` | 16 | Partial | `tests/unit/models/` (5 test files) -- top-level models partially covered |
| `models/business` | 25 | Direct | `tests/unit/models/business/` (30 test files) |
| `models/business/detection` | 7 | Indirect | `tests/unit/models/business/test_detection.py`, `tests/unit/detection/`, `tests/integration/test_detection.py` |
| `models/business/matching` | 6 | Direct | `tests/unit/models/business/matching/` (4 test files) |
| `models/contracts` | 1 | Direct | `tests/unit/models/contracts/` (1 test file) |
| `observability` | 3 | None identified | No test imports of `autom8_asana.observability` found |
| `patterns` | 2 | Direct | `tests/unit/patterns/` (2 test files) |
| `persistence` | 19 | Direct | `tests/unit/persistence/` (28 test files), `tests/validation/persistence/` (5 files) |
| `protocols` | 8 | Indirect | 10 test imports; used via WarmResult, CacheProvider, etc. |
| `query` | 18 | Direct | `tests/unit/query/` (21 test files) |
| `resolution` | 7 | Direct | `tests/unit/resolution/` (7 test files) |
| `search` | 2 | Direct | `tests/unit/search/` (3 test files) |
| `services` | 16 | Direct | `tests/unit/services/` (15 test files) |
| `transport` | 5 | Direct | `tests/unit/transport/` (7 test files) |

### Untested and Undertested Packages (Prioritized by Risk)

**Priority 1 -- No direct test directory, high complexity:**

- **`cache/integration/`** (14 source files): `autom8_adapter.py`, `dataframe_cache.py`, `mutation_invalidator.py`, `staleness_coordinator.py`, `freshness_coordinator.py`, `hierarchy_warmer.py`, `factory.py`, `loader.py`, and others. These are integration glue components that wire cache policies to business objects. They are exercised indirectly through many cache unit tests (via the `tests/unit/cache/` suite -- 56 test files import these modules), but have no dedicated test subdirectory. Risk is moderate: the suite tests behavior but not the integration components in isolation.

- **`dataframes/resolver/`** (6 source files): `cascading.py`, `coercer.py`, `default.py`, `normalizer.py`. Exercised indirectly through `tests/unit/dataframes/test_cascading_resolver.py` and `tests/integration/test_cascading_field_resolution.py`, `tests/integration/test_unit_cascade_resolution.py`. Critical path: dataframe resolution is central to query results.

**Priority 2 -- No observed test coverage:**

- **`observability/`** (3 files: `context.py`, `correlation.py`, `decorators.py`): No test imports identified. Given the role of `@trace_computation` decorators (documented in `tests/test_computation_spans.py`), the decorators themselves may be covered via `autom8y_telemetry.testing` patterns, but `context.py` and `correlation.py` have no direct coverage. Medium risk.

- **`metrics/definitions/`** (1 file: `offer.py`): No test imports found. Low risk given it is likely a static constant/model definition. Risk is low unless metric definitions drive business logic.

**Priority 3 -- Indirect-only with meaningful complexity:**

- **`models/business/detection/`** (7 files): Indirect coverage via `tests/unit/models/business/test_detection.py` and `tests/integration/test_detection.py`. The detection facade and tier1-4 tier logic are exercised through integration but not in isolated unit tests. Risk is medium: tier logic has branching complexity.

- **`dataframes/extractors/`** (5 files): Covered indirectly via `tests/unit/dataframes/test_extractors.py`. No dedicated subdirectory.

- **`_defaults/`** (4 files): `NullCacheProvider` and `InMemoryCacheProvider` are heavily exercised indirectly -- 280 test references found across `tests/unit/clients/` and `tests/unit/cache/`. `DefaultLogProvider` is used in `tests/unit/cache/test_events.py`. Low gap risk.

- **`protocols/`** (8 files): Protocol interfaces -- 10 test imports. Protocols are structural typing contracts, so the absence of direct tests is expected and low risk. Behavioral contracts are verified through implementor tests.

- **`batch/`** (2 files: `client.py`, `models.py`): Exercised through integration tests. Risk is low given the integration coverage.

### Critical Path Coverage Assessment

| Critical Path | Coverage Assessment |
|---|---|
| Query execution (`query/engine.py`, `query/compiler.py`) | Well covered: 21 unit test files, adversarial tests |
| Persistence / SaveSession (`persistence/session.py`) | Well covered: 28 unit test files + 5 validation files + integration |
| Cache layer (`cache/backends`, `cache/models`, `cache/policies`) | Well covered indirectly: 56 unit test files in `tests/unit/cache/` |
| Dataframe building (`dataframes/builders/`) | Well covered: 8 unit test files + adversarial pacing test |
| Authentication (`auth/`) | Well covered: 6 unit test files covering audit, bot_pat, dual_mode, integration |
| API routes (`api/routes/`) | Partially covered: 6 test files for 17 source files -- gap exists |
| Services layer (`services/`) | Well covered: 15 unit test files |
| Business models (`models/business/`) | Well covered: 30 unit test files |
| Observability decorators | Gap: no direct tests for `observability/` package |
| Lambda handlers | Well covered: 9 unit test files for 7 source files |

### Negative/Error Path Coverage

`pytest.raises` appears in 1,163 locations across the test suite. This is a strong indicator that error paths and negative tests are a first-class concern. Key patterns observed:

- `tests/unit/query/test_compiler.py`: `InvalidOperatorError`, `UnknownFieldError`, `CoercionError` all tested
- `tests/unit/persistence/test_session.py`: `SessionClosedError`, `PositioningConflictError`, `UnsupportedOperationError`
- Adversarial test files (`test_adversarial.py`, `test_adversarial_aggregate.py`, `test_hardening_a.py`) specifically target edge cases and error paths in query, cache, metrics, and persistence

**Blind spot**: The `observability/` package (`context.py`, `correlation.py`) has no observed negative test coverage.

### Prioritized Gap List

1. **Lambda handlers edge cases** -- Entry points are tested but error paths and retry behavior have limited coverage
2. **Observability hooks** -- Limited dedicated tests for metric emission and trace correlation
3. **Transport layer** -- Adaptive semaphore and sync wrapper edge cases
4. **CLI edge cases** -- `--live` mode HTTP client, saved query resolution error paths
5. **Automation workflow templates** -- Template rendering and validation edge cases

## Testing Conventions

### Test File Naming

All test files follow `test_{module_name}.py` convention. Mirror the source tree under `tests/unit/` and `tests/integration/`. Adversarial/hardening variants append `_adversarial`, `_hardening_a`, or `_e2e` suffixes. Examples:
- `tests/unit/query/test_compiler.py` mirrors `src/autom8_asana/query/compiler.py`
- `tests/unit/cache/test_adversarial_pacing_backpressure.py` -- adversarial variant
- `tests/integration/test_e2e_offer_write_proof.py` -- e2e variant

### Test Function Naming

Two patterns coexist:

1. **Class-based** (majority): `class TestXxx:` containing `def test_{verb}_{scenario}(self, ...)`. 8,052 class-method test functions found (vs 2,593 module-level).
   ```python
   class TestCompilerUtf8:
       def test_eq(self, compiler, test_schema): ...
       def test_ne(self, compiler, test_schema): ...
   ```

2. **Module-level**: `def test_{verb}_{scenario}(...)`. Used for simpler, standalone tests.

### Async Tests

3,130 async test functions (`async def test_...`). All use `pytest-asyncio` with `asyncio_mode = "auto"` (set in `pyproject.toml`), meaning no `@pytest.mark.asyncio` decorator is needed.

### Subtest/Parametrize Patterns

`pytest.mark.parametrize` appears in 83 locations. Used for matrix tests (e.g., operator x dtype in query compiler). Example pattern:
```python
@pytest.mark.parametrize("op,expected", [(Op.EQ, ...), (Op.NE, ...)])
def test_operator_matrix(self, op, expected): ...
```

### Assertion Patterns

- Direct `assert` statements (no assertion library)
- `pytest.raises` context manager for exception testing (1,163 uses)
- `logger.assert_logged(level, event)` via `autom8y_log.testing.MockLogger` for log assertions

### Mock Patterns

- **`unittest.mock.MagicMock`**: 2,848 uses -- primary synchronous mock
- **`unittest.mock.AsyncMock`**: 2,296 uses -- primary async mock
- **`respx`**: 203 uses for httpx request mocking (HTTP client layer)
- **`fakeredis`**: 12 uses for Redis backend tests (`test_redis_backend.py`, `test_redis_stamp_serialization.py`)
- **`moto` / `mock_aws`**: 3 uses for S3 backend tests (`test_s3_backend.py`)
- **`autom8y_cache.testing`**: 9 uses for SDK cache testing subpackage
- **`autom8y_log.testing.MockLogger`**: 1 use (in top-level `conftest.py`) -- provides `MockLogger` fixture globally

### Test Fixture Patterns

**Global conftest** (`tests/conftest.py`):
- `mock_http` -- `MockHTTPClient` with all 8 HTTP methods mocked
- `config` -- `AsanaConfig()` instance
- `auth_provider` -- `MockAuthProvider` returning `"test-token"`
- `logger` -- `MockLogger` from `autom8y_log.testing`
- `mock_client_builder` -- returns `MockClientBuilder` class (builder pattern for `AsanaClient` mocks)
- `_bootstrap_session` (session-scoped, autouse) -- bootstraps `ProjectTypeRegistry` and rebuilds Pydantic models with `NameGid` forward refs
- `reset_all_singletons` (function-scoped, autouse) -- calls `SystemContext.reset_all()` before and after every test for isolation

**Local conftest** files exist at: `tests/unit/api/conftest.py`, `tests/unit/automation/polling/conftest.py`, `tests/unit/automation/workflows/conftest.py`, `tests/unit/cache/conftest.py`, `tests/unit/clients/conftest.py`, `tests/unit/clients/data/conftest.py`, `tests/unit/dataframes/conftest.py`, `tests/unit/lifecycle/conftest.py`, `tests/unit/resolution/conftest.py`, `tests/validation/persistence/conftest.py`.

**Shared mocks** (`tests/_shared/mocks.py`): `MockTask` -- mimics Asana task with date fields for `TriggerEvaluator` tests.

**Builder pattern**: `MockClientBuilder` in root `conftest.py` -- fluent builder for mock `AsanaClient` construction:
```python
client = MockClientBuilder().with_batch(results=[...]).with_http().build()
```

### Skip Patterns

- `@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, ...)` -- conditional skip when optional dependency absent
- `@pytest.mark.skipif(not ASANA_PAT, reason="ASANA_PAT not set")` -- guards live-API tests
- `@pytest.mark.skip(...)` -- used for known-broken tests in `test_workspace_switching.py` (7 skips) and `test_platform_performance.py` (1 skip)

### Test Data

No fixture data directories (`fixtures/`, `testdata/`, `__fixtures__/`) were found in the test tree. All test data is constructed inline in test functions or via fixtures. YAML configs exist in `config/` and `queries/` but these are production fixtures, not test fixtures.

## Test Structure Summary

### Overall Distribution

| Tier | Test Files | Notes |
|---|---|---|
| `tests/unit/` | 380 files | Primary test tier; organized by source package |
| `tests/integration/` | 31 files | Require live Asana API or substantial setup |
| `tests/validation/` | 5 files | Persistence layer functional/performance validation |
| `tests/benchmarks/` | 4 files | Performance benchmarks (`bench_batch_operations.py`, `bench_cache_operations.py`) |
| `tests/` (top-level) | 1 file | `test_computation_spans.py` -- OTel span verification |

**Total test functions**: ~8,109 (estimated from function-level grep; includes both `def test_` at module level and within classes).

**Async test functions**: 3,130 of ~8,109 (38.6%) -- consistent with the async-first codebase.

### Most Heavily Tested Areas (by file count)

1. `cache` -- 56 unit test files (largest single area)
2. `automation` -- 38 unit test files
3. `dataframes` -- 41 unit test files
4. `clients` -- 34 unit test files
5. `api` -- 32 unit test files
6. `models` -- 40 unit test files (business + base)
7. `persistence` -- 28 unit test files

### Test Package Naming Pattern

Test packages mirror the source package tree exactly under `tests/unit/` and `tests/integration/`. All directories contain `__init__.py`, making them proper packages. There is no separate `test_` prefix on directory names -- the structure is `tests/unit/{package}/test_{module}.py`.

### Integration Test vs Unit Test Distinction

Integration tests are in `tests/integration/` and distinguished in two ways:
1. **Physical location**: `tests/integration/` directory
2. **Marker**: `@pytest.mark.integration` (45 occurrences) -- used when tests are embedded outside the `integration/` directory or need explicit marking for CI filtering

CI runs unit tests only on pull requests (`test_markers_exclude: 'not integration and not benchmark'`) and adds integration tests on push to `main` (`run_integration: ${{ github.event_name == 'push' }}`).

### Test Invocation Commands

```bash
# Standard test run (from justfile)
uv run pytest

# Fast tests only (no slow, integration, benchmarks)
uv run pytest tests/ -m "not slow and not integration and not benchmark"

# Integration tests (requires ASANA_PAT env var)
uv run pytest tests/ -m "integration"

# With coverage
uv run pytest --cov=autom8_asana --cov-report=html --cov-report=term

# Slow tests only
uv run pytest tests/ -m "slow"

# Benchmarks
uv run pytest tests/ -m "benchmark"
```

**Coverage threshold**: 80% (configured in `.github/workflows/test.yml` via `coverage_threshold: 80`).

**pytest configuration** (`pyproject.toml`):
- `asyncio_mode = "auto"` -- all async tests run automatically
- `timeout = 60` -- 60-second timeout per test (thread method)
- `testpaths = ["tests"]`
- Markers: `slow`, `integration`, `benchmark`

### Singleton Isolation Pattern

A critical testing constraint: every test resets all singletons via `SystemContext.reset_all()` (autouse fixture `reset_all_singletons` in root `conftest.py`). This prevents cross-test state leakage from registries, caches, and settings. Any new code using `SystemContext` singletons will automatically benefit from this isolation.

## Knowledge Gaps

- **Coverage percentages**: No `.coverage` database or `htmlcov/` report was present in the repository at observation time. The documented CI threshold is 80%, but current measured coverage against source is unknown. The `just test-cov` command must be run to obtain current percentages.
- **`observability/` package tests**: No test imports of `autom8_asana.observability` were found. Whether `context.py` and `correlation.py` are exercised indirectly through the telemetry SDK cannot be confirmed from static analysis.
- **`cache/integration/` isolation**: The 14-file `cache/integration/` package is tested indirectly via many cache unit tests, but the specific coverage of each file (e.g., `hierarchy_warmer.py`, `schema_providers.py`, `upgrader.py`) was not traced individually.
- **Validation tests scope**: The `tests/validation/persistence/` files (`test_concurrency.py`, `test_dependency_ordering.py`, `test_error_handling.py`, `test_functional.py`, `test_performance.py`) appear to be a separate validation harness, but their relationship to CI execution was not confirmed.
- **`tests/integration/events/test_sqs_integration.py`**: Exists but not analyzed for skip/live API requirements.
