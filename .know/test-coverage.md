---
domain: test-coverage
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
  - ".sos/land/workflow-patterns.md"
land_hash: "1471b813f0f58342c542d2e8c9cd92aba095afec134846cda625c3fa545ec9fe"
---

# Codebase Test Coverage

**Language**: Python 3.12
**Test runner**: `pytest` with `pytest-asyncio` (auto mode), `pytest-cov`, `pytest-xdist` (parallel)
**Coverage threshold**: 80% (enforced in CI via `[tool.coverage.report] fail_under = 80`)
**Test command (CI)**: `pytest -m "not integration and not benchmark"` (unit only on PRs; integration added on push to main)
**Total test files**: 460 (421 unit, 32 integration, 5 validation, 1 computation spans, 1 benchmark)
**Total test functions**: ~11,986 (215 top-level + 11,771 class-method tests across 2,838 test classes)
**Source files**: 411 non-`__init__` Python source files across 22 top-level packages

---

## Coverage Gaps

### Packages with Zero Direct Test Coverage

**`_defaults/` (4 source files) -- Medium criticality**
- `src/autom8_asana/_defaults/auth.py`
- `src/autom8_asana/_defaults/cache.py`
- `src/autom8_asana/_defaults/log.py`
- `src/autom8_asana/_defaults/observability.py`

Platform SDK default wiring modules. No dedicated test directory or test files exist. Coverage likely comes passively via integration paths, but default wiring failures (wrong config keys, mismatched SDK versions) would be silent.

**`protocols/` (8 source files) -- Low criticality (intentional)**
- All 8 files define `Protocol` (PEP 544) structural interfaces with no executable logic
- Pure interface definitions; absence of tests is expected and correct

**`batch/` (2 source files: `client.py`, `models.py`) -- Low criticality (indirect coverage)**
- No dedicated `tests/unit/batch/` directory
- `batch.models.BatchResult` imported in 20+ test files across `cache/`, `persistence/`, `clients/` tests
- `batch.client` tested indirectly via `test_batch_adversarial.py` and `clients/test_batch.py`

**`observability/` (3 source files: `context.py`, `correlation.py`, `decorators.py`) -- Medium criticality**
- Single root-level test file `tests/unit/test_observability.py` covers basics
- No dedicated `tests/unit/observability/` directory
- `decorators.py` instrumentation exercised transitively via span tests (`test_computation_spans.py`, `*_spans.py` tests)

### Lightly Covered Packages

| Package | Test Files | Source Files | Notes |
|---|---|---|---|
| `observability/` | 1 (root-level) | 3 | Minimal direct coverage |
| `search/` | 3 | 2 | Adequate |
| `patterns/` | 2 | 2 | Adequate |
| `reconciliation/` | 0 | 0 (empty pkg, only `__pycache__/`) | Placeholder directory, no source to test |

### Services Coverage Blind Spots

The `services/` package has 20 source modules. Several modules have no dedicated test file but are tested via route tests:

- `intake_create_service.py` -- covered via `tests/unit/api/routes/test_intake_create.py`
- `intake_resolve_service.py` -- covered via `tests/unit/api/routes/test_intake_resolve.py`
- `intake_custom_field_service.py` -- covered via `tests/unit/api/routes/test_intake_custom_fields.py`
- `entity_context.py` -- no dedicated test file; used only in `tests/unit/services/test_entity_service.py` transitively
- `resolver.py` (the main resolver service) -- covered via `tests/unit/api/routes/test_resolver_*.py` (5 files) and `tests/unit/api/test_routes_resolver.py`
- `errors.py` -- covered via `tests/unit/services/test_service_errors.py`

### Lambda Handlers Gaps

3 of 11 lambda handlers have no dedicated test file:

| Handler | Criticality | Notes |
|---|---|---|
| `cloudwatch.py` | **HIGH** | Production monitoring/alerting path; no test coverage found |
| `push_orchestrator.py` | **MEDIUM** | Orchestrates cache push; related to `test_cache_warmer_gid_push.py` but no direct test |
| `timeout.py` | **LOW** | Likely a thin utility; no dedicated test |

All other 8 lambda handlers have dedicated test files (11 test files for 8 source files, including multi-aspect tests for `cache_warmer`).

### Core Package Utility Gaps

8 of 18 core source files have no dedicated test file:
- `datetime_utils.py`, `entity_types.py`, `field_utils.py`, `logging.py`, `registry.py`, `string_utils.py`, `timing.py`, `types.py`

These are utility/constant modules likely tested transitively. `registry.py` is tested via `test_entity_registry.py` and `test_project_registry.py`. The others define types, constants, or thin wrappers.

### Skipped Tests (Active Blind Spots)

10+ tests marked `@pytest.mark.skip` or `xfail`:
- `tests/unit/dataframes/test_cascading_resolver.py`: `test_clear_cache_empties_the_cache` -- marked `xfail` ("clear_cache method removed - test needs update")
- `tests/integration/test_workspace_switching.py`: 5 skipped tests -- known deferred bugs
- `tests/integration/test_platform_performance.py`: 1 skipped -- RS-021 cache miss regression
- `tests/integration/test_lifecycle_smoke.py`: 1 `xfail` -- D-LC-001 known defect
- `tests/test_computation_spans.py`: 1 skipped test

Optional-dependency guards:
- `@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, ...)` in `tests/unit/cache/test_redis_backend.py`
- `@pytest.mark.skipif(not MOTO_AVAILABLE, ...)` in `tests/unit/cache/test_s3_backend.py`
- `@pytest.mark.skipif(not _HAS_HYPOTHESIS, ...)` in `tests/unit/persistence/test_reorder.py`

### Integration Test Coverage (Live API)

32 integration test files under `tests/integration/`. Tests requiring a live Asana API use `@pytest.mark.skipif(not ASANA_PAT, ...)` guards. Integration tests run only on push to `main` branch in CI (not on PRs).

### Prioritized Gap List

1. **HIGH**: `cloudwatch.py` lambda handler -- no test coverage, production monitoring path
2. **MEDIUM**: `push_orchestrator.py` lambda handler -- no dedicated test, orchestration logic
3. **MEDIUM**: `_defaults/` package (4 files) -- platform wiring tested only implicitly
4. **MEDIUM**: `entity_context.py` service -- no dedicated test file; used in critical resolution paths
5. **LOW**: `timeout.py` lambda handler -- thin utility, low risk
6. **LOW**: Core utility modules (8 files) -- types/constants, transitively covered
7. **LOW**: 5 skipped `workspace_switching` integration tests -- deferred known defects
8. **LOW**: 1 xfail `clear_cache` test -- stale test pointing at removed method

---

## Testing Conventions

### Test Function Naming

All test functions follow `test_{what_is_being_tested}` convention:
- Descriptive snake_case: `test_create_task_event`, `test_frozen_immutability`, `test_extract_from_projects_array`
- Error-case naming uses suffix patterns: `test_rejects_zero_timeout`, `test_raises_on_invalid_...`, `test_handles_malformed_...`
- Method-under-test prefixes common: `test_execute_rows`, `test_build_progressive_async`

### Test Organization

Predominantly **class-based** structure (2,838 test classes vs 215 standalone functions):
```python
class TestMutationEvent:
    def test_create_task_event(self) -> None: ...
    def test_frozen_immutability(self) -> None: ...
```
Classes group related tests for a single class, behavior cluster, or scenario. No `TestCase` (unittest-style); pure pytest class syntax. Many test files contain 10-20+ classes (e.g., `test_insights_export.py` has 20 test classes).

### Async Tests

2,505 tests use `@pytest.mark.asyncio`. The `asyncio_mode = "auto"` setting in `pyproject.toml` means `async def test_*` functions run as coroutines automatically, but the decorator is still used widely for explicitness.

### Parametrize Pattern

103 uses of `@pytest.mark.parametrize` across 45 files. Standard pytest syntax:
```python
@pytest.mark.parametrize("field", ["connect", "read", "write", "pool"])
def test_rejects_zero_timeout(self, field: str) -> None: ...
```
Parameter tuples used for multi-variable cases:
```python
@pytest.mark.parametrize("input_val,expected", [...])
```

### Assertion Patterns

- **Primary**: `assert` statements with plain Python equality
- **Exception testing**: `pytest.raises` (1,181 occurrences across 211 files) -- always as context manager: `with pytest.raises(SomeError):`
- **Mock verification**: `assert_called`/`assert_awaited`/`assert_not_called` variants (1,052 occurrences across 190 files)
- **Numeric tolerance**: `pytest.approx` (43 occurrences across 14 files) for float comparisons
- **DataFrame assertions**: Polars `pl.DataFrame` constructed in 190+ test files; equality checked via `frame_equal()` or column-level `assert`

### Fixture Patterns

**Root conftest** (`tests/conftest.py`):
- `mock_http` -- `MockHTTPClient` with 8 `AsyncMock` methods (get, post, put, delete, request, get_paginated, post_multipart, get_stream_url)
- `config` -- `AsanaConfig()` with defaults
- `auth_provider` -- `MockAuthProvider` returning `"test-token"`
- `logger` -- SDK `MockLogger` (from `autom8y_log.testing`) for structured log assertion via `logger.assert_logged(level, event)`
- `mock_client_builder` -- `MockClientBuilder` class with fluent builder API (`with_batch()`, `with_http()`, `with_cache()`, `with_tasks()`, `with_projects_list()`)
- `_bootstrap_session` (autouse, scope=session) -- calls `bootstrap()` + Pydantic `model_rebuild()` for NameGid forward references on 16 model classes
- `reset_all_singletons` (autouse, scope=function) -- calls `SystemContext.reset_all()` before and after each test for full singleton isolation

**Sub-package conftest files** (12 total: 1 root + 11 scoped):
- `tests/unit/cache/conftest.py`: `mock_batch_client` fixture
- `tests/unit/dataframes/conftest.py`: `make_mock_task()` factory + `_TestBuilder` concrete builder for extractor tests
- `tests/unit/resolution/conftest.py`: Domain entity fixtures (Business, Unit, Contact, Process) + `make_mock_task()` and `make_business_entity()` helpers
- `tests/unit/lifecycle/conftest.py`: `lifecycle_config` loaded from YAML at `config/lifecycle_stages.yaml`
- `tests/unit/automation/workflows/conftest.py`: `mock_resolution_context` with reconfigurable `set_business()` and `lifecycle_config` from YAML
- `tests/integration/automation/polling/conftest.py`: Integration-level polling fixtures
- `tests/unit/clients/conftest.py`, `tests/unit/clients/data/conftest.py`: Client-level fixtures
- `tests/unit/api/conftest.py`: API test fixtures
- `tests/validation/persistence/conftest.py`: Validation-specific persistence fixtures

### Builder/Factory Patterns for Test Data

- `MockClientBuilder` in root conftest: fluent builder with chaining
- Factory functions (`make_*`, `_make_*`, `build_*`) defined locally in test files (common pattern: `make_task()`, `make_unit_dataframe()`, `_make_mock_store()`)
- Polars DataFrame construction is heavy -- test data built inline as dict-of-lists pattern
- `MockTask` in `tests/_shared/mocks.py` -- shared mock with explicit attribute control for automation tests

### Mocking Strategy

- `unittest.mock.AsyncMock` and `MagicMock` are the primary mocks (not `respx` for most tests)
- `unittest.mock.patch` used in 1,583 occurrences across 142 files -- both as decorator and context manager
- `respx` used in 90 import occurrences across 12 files -- primarily HTTP-level route mocking for `clients/data/` tests
- `fakeredis` for Redis backend tests (guarded with `@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, ...)`)
- `moto` for S3 backend tests (guarded with `@pytest.mark.skipif(not MOTO_AVAILABLE, ...)`)
- OTel `InMemorySpanExporter` + `TracerProvider` for span/tracing tests

### Skip Patterns

- `@pytest.mark.skip(reason="...")` -- 10 instances; reasons are deferred bugs or regression tickets (e.g., RS-021)
- `@pytest.mark.skipif(not ASANA_PAT, ...)` -- integration tests requiring live API
- `@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, ...)` and `@pytest.mark.skipif(not MOTO_AVAILABLE, ...)` -- optional-dependency guards
- `@pytest.mark.skipif(not _HAS_HYPOTHESIS, ...)` -- property-based testing guard
- `@pytest.mark.xfail(reason="...")` -- 2 instances (stale method reference, known defect)

### Test Environment Management

- `asyncio_mode = "auto"` in `pyproject.toml`
- `timeout = 60` seconds per test, enforced by `pytest-timeout` with `thread` method
- Global `_bootstrap_session` autouse fixture initializes `ProjectTypeRegistry` and Pydantic model forward references once per session
- Global `reset_all_singletons` autouse fixture ensures `SystemContext.reset_all()` before/after each test
- CI excludes `integration` and `benchmark` markers on PRs; includes them on push to `main`
- Custom markers: `slow`, `integration`, `benchmark`

---

## Test Structure Summary

### Distribution Overview

| Category | Test Files | Approximate Tests |
|---|---|---|
| `tests/unit/` | 421 files | ~11,270 |
| `tests/integration/` | 32 files | ~572 |
| `tests/validation/` | 5 files (persistence only) | ~121 |
| `tests/` root | 1 file (computation spans) | ~15 |
| `tests/benchmarks/` | 1 file (insights) | ~8 |

### Most Heavily Tested Areas (Unit)

By file count:
1. `cache/` -- 56 test files (largest test package; covers backends, dataframe cache, providers, policies, integration layer)
2. `dataframes/` -- 48 test files (builders 9, views 3, models, extractors, schemas, resolver)
3. `api/` -- 47 test files (routes 19, preload 2, middleware 2, dependencies, health, lifespan)
4. `automation/` -- 43 test files (events 8, polling 7, workflows 12, engine/pipeline/config)
5. `models/` -- 40 test files (business entities 16, contracts 3, detection, matching, hydration)
6. `clients/` -- 36 test files (data clients 18, utilities 2, name resolver, stories cache)
7. `persistence/` -- 28 test files (session 8, action executor, pipeline, healing, cascade)
8. `services/` -- 21 test files (universal strategy 4, dataframe service, query service, section service)
9. `lifecycle/` -- 15 test files (creation, engine, sections, dispatch, integration, webhooks)
10. `query/` -- 14 test files (engine, adversarial 3, compiler, CLI, aggregator, joins)

### File Change Hotspots (from session history)

Most frequently changed test files (high-churn indicates active development/refinement):
- `tests/unit/dataframes/builders/test_cascade_validator.py` (6 changes)
- `tests/unit/services/test_universal_strategy*.py` (8 changes across 4 files)
- `tests/unit/dataframes/views/test_cascade_view.py` (4 changes)
- `tests/unit/api/routes/test_resolver_status.py` (3 changes)

### Integration vs Unit Distinction

**Unit tests** (`tests/unit/`):
- Mock all external I/O (Asana API, Redis, S3, SQS)
- Use `AsyncMock`/`MagicMock` for HTTP, cache, and client boundaries
- Run on every PR; no live credentials required

**Integration tests** (`tests/integration/`):
- Mix of two types:
  1. **Live API tests**: Guarded with `@pytest.mark.skipif(not ASANA_PAT, ...)` -- require `ASANA_WORKSPACE_GID` env var; run only on push to `main`
  2. **In-process integration tests**: Wire multiple real components together without external I/O (e.g., `test_unit_cascade_resolution.py`, `test_cascading_field_resolution.py`)
- Sub-directories: `api/` (1), `automation/polling/` (3), `automation/workflows/` (1), `events/` (1), `persistence/` (1)

**Validation tests** (`tests/validation/persistence/`):
- Functional, concurrency, dependency ordering, error handling, and performance tests for the persistence layer
- Separate category for depth-testing one critical subsystem

**Computation spans test** (`tests/test_computation_spans.py`):
- Top-level standalone test file
- Validates OTel span emission for instrumented functions on the entity query/join critical path

**Benchmark tests** (`tests/benchmarks/`):
- `bench_batch_operations.py`, `bench_cache_operations.py`, `test_insights_benchmark.py`
- Excluded from standard CI run (`-m "not benchmark"`)

### Test Package Naming Patterns

- Unit tests mirror source structure: `tests/unit/{package}/test_{module}.py`
- Integration tests use descriptive names: `test_cascading_field_resolution.py`, `test_hydration_cache_integration.py`
- Adversarial tests use explicit naming: `test_tier1_adversarial.py`, `test_tier2_adversarial.py`, `test_batch_adversarial.py`, `test_schema_extractor_adversarial.py`
- Span/instrumentation tests use `_spans` suffix: `test_resolver_spans.py`, `test_universal_strategy_spans.py`, `test_cascade_validator_spans.py`
- Edge case tests use `_edge_cases` suffix: `test_paced_fetch_edge_cases.py`, `test_gid_validation_edge_cases.py`

### How Tests Are Run

```bash
# Unit tests only (PR gate)
pytest -m "not integration and not benchmark" --cov=autom8_asana --cov-fail-under=80

# With parallel execution (CI uses pytest-xdist)
pytest -n auto -m "not integration and not benchmark"

# Integration tests (main branch only)
pytest -m integration --timeout=60

# Full suite
pytest --timeout=60
```

---

## Knowledge Gaps

1. **Actual coverage percentages per module**: No coverage report artifact was present in the repo at observation time. The 80% threshold is enforced in CI but the per-module breakdown is not locally visible.
2. **`_defaults/` package criticality**: Whether default wiring modules are exercised by any test via import side effects cannot be determined without running the test suite with coverage instrumentation.
3. **`cloudwatch.py` handler**: Referenced only in 3 test files (for story warming and cache warming), never directly tested. Actual coverage impact unknown without instrumented run.
4. **`entity_context.py` indirect coverage**: Appears in only 1 test file by import (`test_entity_service.py`); its actual line coverage via other tests cannot be confirmed without a coverage report.
5. **Core utility modules**: 8 of 18 core files lack dedicated tests. These define types, constants, and thin utilities that are likely covered transitively, but no confirmation without coverage data.

```metadata
overall_grade: A
overall_percentage: 92.0%
confidence: 0.92
criteria_grades:
  coverage_gaps: A
  testing_conventions: A
  test_structure_summary: A
```
