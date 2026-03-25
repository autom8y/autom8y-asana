---
domain: test-coverage
generated_at: "2026-03-25T01:56:07Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "c6bcef6"
confidence: 0.88
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
---

# Codebase Test Coverage

**Language**: Python 3.12
**Test runner**: `pytest` with `pytest-asyncio` (auto mode), `pytest-cov`, `pytest-xdist` (parallel)
**Coverage threshold**: 80% (enforced in CI via reusable workflow)
**Test command (CI)**: `pytest -m "not integration and not benchmark"` (unit only on PRs; integration added on push to main)
**Total test files**: 443 (405 unit, 31 integration, 5 validation, 1 computation spans, 1 benchmark)
**Total test functions**: ~11,590 (2,690 top-level + class-method tests)
**Source files**: 392 Python source files across 22 top-level packages

---

## Coverage Gaps

### Packages with Zero Direct Test Coverage

Two packages have no test files:

**`_defaults/` (4 source files) -- Medium criticality**
- `src/autom8_asana/_defaults/auth.py`
- `src/autom8_asana/_defaults/cache.py`
- `src/autom8_asana/_defaults/log.py`
- `src/autom8_asana/_defaults/observability.py`

These are platform SDK default wiring modules. They assemble SDK primitives for the main application. No dedicated test exists. Coverage likely comes passively via integration paths, but default wiring failures (wrong config keys, mismatched SDK versions) would be silent.

**`protocols/` (8 source files) -- Low criticality (intentional)**
- All 8 files define `Protocol` (PEP 544) structural interfaces with no executable logic
- Pure interface definitions; absence of tests is expected and correct

### Lightly Covered Packages

| Package | Test Files | Source Files | Notes |
|---|---|---|---|
| `observability/` | 1 (root-level `test_observability.py`) | 3 | Minimal direct coverage |
| `search/` | 3 | 2 | Adequate per source count |
| `patterns/` | 2 | 2 | Adequate per source count |

### Services Coverage Blind Spots

The `services/` package is large (19 source modules). Several modules have no dedicated test file but are tested via route tests:

- `intake_create_service.py` -- covered via `tests/unit/api/routes/test_intake_create.py`
- `intake_resolve_service.py` -- covered via `tests/unit/api/routes/test_intake_resolve.py`
- `intake_custom_field_service.py` -- covered via `tests/unit/api/routes/test_intake_custom_fields.py`
- `entity_context.py` -- no dedicated test file; covered indirectly through resolver and service tests
- `resolver.py` (the main resolver service) -- covered via multiple test files in `tests/unit/api/routes/test_resolver_*.py` and `tests/unit/api/test_routes_resolver.py`

### Lambda Handlers Gap

`src/autom8_asana/lambda_handlers/cloudwatch.py` has no dedicated test file. All other lambda handlers are tested (checkpoint, payment_reconciliation, insights_export, conversation_audit, workflow_handler, cache_invalidate, cache_warmer -- 9 test files for 8 source files).

### Skipped Tests (Active Blind Spots)

10 tests marked `@pytest.mark.skip`:
- `tests/unit/dataframes/test_cascading_resolver.py`: `test_clear_cache_empties_the_cache` -- marked `xfail` with reason "clear_cache method removed - test needs update" (stale test)
- `tests/integration/test_workspace_switching.py`: 5 skipped tests -- all skipped for known deferred bugs
- `tests/integration/test_platform_performance.py`: 1 skipped -- RS-021 cache miss regression
- `tests/integration/test_lifecycle_smoke.py`: 1 `xfail` -- D-LC-001 known defect in pipeline_stage deduplication

### Integration Test Coverage (Live API)

31 integration test files under `tests/integration/`. All tests requiring a live Asana API use `@pytest.mark.skipif(not ASANA_PAT, ...)` guards. Integration tests run only on push to `main` branch in CI (not on PRs).

### Prioritized Gap List

1. **HIGH**: `cloudwatch.py` lambda handler -- no test coverage, production monitoring path
2. **MEDIUM**: `_defaults/` package -- platform wiring tested only implicitly; a regression in SDK argument names would be silent
3. **MEDIUM**: `entity_context.py` service -- no dedicated test file; used in critical resolution paths
4. **LOW**: 5 skipped `workspace_switching` integration tests -- represent deferred known defects
5. **LOW**: 1 xfail `clear_cache` test in `test_cascading_resolver.py` -- stale test pointing at removed method

---

## Testing Conventions

### Test Function Naming

All test functions follow the `test_{what_is_being_tested}` convention:
- Descriptive snake_case: `test_create_task_event`, `test_frozen_immutability`, `test_extract_from_projects_array`
- Error-case naming uses suffix patterns: `test_rejects_zero_timeout`, `test_raises_on_invalid_...`, `test_handles_malformed_...`
- Method-under-test prefixes common: `test_execute_rows`, `test_build_progressive_async`

### Test Organization

Predominantly **class-based** structure (2,690 test classes vs 190 standalone functions):
```python
class TestMutationEvent:
    def test_create_task_event(self) -> None: ...
    def test_frozen_immutability(self) -> None: ...
```
Classes group related tests for a single class or behavior cluster. No `TestCase` (unittest-style); pure pytest class syntax.

### Async Tests

2,496 tests use `@pytest.mark.asyncio`. The `asyncio_mode = "auto"` setting in `pyproject.toml` means `async def test_*` functions run as coroutines automatically without needing the decorator explicitly, but the decorator is still used widely for explicitness.

### Parametrize Pattern

93 uses of `@pytest.mark.parametrize`. Standard pytest syntax:
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
- **Exception testing**: `pytest.raises` (1,170 occurrences) -- always as context manager: `with pytest.raises(SomeError):`
- **Mock verification**: `assert_called` variants (706 occurrences); `assert_awaited` for async mocks (48 occurrences)
- **Numeric tolerance**: `pytest.approx` (35 occurrences) for float comparisons

### Fixture Patterns

**Root conftest** (`tests/conftest.py`):
- `mock_http` -- `MockHTTPClient` with 8 `AsyncMock` methods
- `config` -- `AsanaConfig()` with defaults
- `auth_provider` -- `MockAuthProvider` returning `"test-token"`
- `logger` -- SDK `MockLogger` for log assertion
- `mock_client_builder` -- `MockClientBuilder` class with fluent builder API
- `_bootstrap_session` (autouse, scope=session) -- calls `bootstrap()` + model rebuilds on session start

**Sub-package conftest examples**:
- `tests/unit/cache/conftest.py`: `mock_batch_client` fixture
- `tests/unit/resolution/conftest.py`: domain entity fixtures (Business, Unit, Contact, Process) + `make_mock_task()` and `make_business_entity()` helpers
- `tests/unit/lifecycle/conftest.py`: `lifecycle_config` loaded from YAML at `config/lifecycle_stages.yaml`

**12 conftest.py files total** (1 root + 11 scoped).

### Builder/Factory Patterns for Test Data

- `MockClientBuilder` in root conftest: fluent builder with `with_batch()`, `with_http()`, `with_cache()`, `with_tasks()`, `with_projects_list()` chaining
- 143 factory functions (`make_*`, `build_*`, `create_*`) in test files; 9 in conftest files
- Polars DataFrame construction is heavy (789 occurrences of `pl.DataFrame(...)`) -- test data is built inline as dict-of-lists
- `MockTask` in `tests/_shared/mocks.py` -- shared mock with explicit attribute control for automation tests

### Mocking Strategy

- `unittest.mock.AsyncMock` and `MagicMock` are the primary mocks (not `respx` for most tests)
- `respx` used in 294 tests -- primarily HTTP-level route mocking for client tests
- `fakeredis` for Redis backend tests (guarded with `@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, ...)`)
- `moto` for S3 backend tests (guarded with `@pytest.mark.skipif(not MOTO_AVAILABLE, ...)`)
- OTel `InMemorySpanExporter` + `TracerProvider` for span/tracing tests (introduced in newer tests for instrumentation coverage)

### Skip Patterns

- `@pytest.mark.skip(reason="...")` -- 10 instances; reasons are either known deferred bugs or regression tickets (e.g., RS-021)
- `@pytest.mark.skipif(not ASANA_PAT, ...)` -- integration tests requiring live API
- `@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, ...)` and `@pytest.mark.skipif(not MOTO_AVAILABLE, ...)` -- optional-dependency guards
- `@pytest.mark.xfail(reason="...")` -- 1 instance in `test_cascading_resolver.py` (stale, method removed)

### Test Environment Management

- `asyncio_mode = "auto"` in `pyproject.toml` (no per-test decorator required)
- `timeout = 60` seconds per test, enforced by `pytest-timeout` with `thread` method
- Global `_bootstrap_session` autouse fixture initializes the `ProjectTypeRegistry` and Pydantic model forward references once per session
- CI excludes `integration` and `benchmark` markers on PRs; includes them on push to `main`

---

## Test Structure Summary

### Distribution Overview

| Category | Test Files | Approximate Tests |
|---|---|---|
| `tests/unit/` | 405 files | ~11,000 |
| `tests/integration/` | 31 files | ~350 |
| `tests/validation/` | 5 files (persistence only) | ~50 |
| `tests/` root | 1 file (computation spans) | ~10 |
| `tests/benchmarks/` | 1 file | ~5 |

### Most Heavily Tested Areas (Unit)

By file count:
1. `cache/` -- 56 files (largest test package)
2. `automation/` -- 47 files (events + polling + workflows)
3. `dataframes/` -- 43 files (builders, extractors, schemas, resolver)
4. `api/` -- 41 files (routes, preload, dependencies, health)
5. `models/` -- 40 files (business entities, contracts, detection, matching)
6. `clients/` -- 36 files (data clients, utilities, endpoint wrappers)
7. `persistence/` -- 28 files (session, change tracking, ordering)

### Integration vs Unit Distinction

**Unit tests** (`tests/unit/`):
- Mock all external I/O (Asana API, Redis, S3, SQS)
- Use `AsyncMock`/`MagicMock` for HTTP, cache, and client boundaries
- Run on every PR; no live credentials required

**Integration tests** (`tests/integration/`):
- Mix of two types:
  1. **Live API tests**: Guarded with `@pytest.mark.skipif(not ASANA_PAT, ...)` -- require `ASANA_WORKSPACE_GID` env var; run only on push to `main`
  2. **In-process integration tests**: Wire multiple real components together without external I/O (e.g., `test_unit_cascade_resolution.py`, `test_cascading_field_resolution.py`)
- Marker: `@pytest.mark.integration` (41 usages)

**Validation tests** (`tests/validation/persistence/`):
- Functional, concurrency, dependency ordering, error handling, and performance tests for the persistence layer
- Separate category for depth-testing one critical subsystem

**Computation spans test** (`tests/test_computation_spans.py`):
- Top-level, standalone test file
- Validates OTel span emission for 10 instrumented functions on the entity query/join critical path

**Benchmark tests** (`tests/benchmarks/`):
- `bench_batch_operations.py`, `bench_cache_operations.py`, `test_insights_benchmark.py`
- Excluded from standard CI run (`-m "not benchmark"`)

### Test Package Naming Patterns

- Unit tests mirror source structure: `tests/unit/{package}/test_{module}.py`
- Integration tests use descriptive names: `test_cascading_field_resolution.py`, `test_hydration_cache_integration.py`
- Adversarial tests use explicit naming: `test_tier1_adversarial.py`, `test_tier2_adversarial.py`, `test_batch_adversarial.py`
- Span/instrumentation tests use `_spans` suffix: `test_resolver_spans.py`, `test_universal_strategy_spans.py`, `tests/test_computation_spans.py`

### How Tests Are Run

```bash
# Unit tests only (PR gate)
pytest -m "not integration and not benchmark" --cov=autom8_asana --cov-fail-under=80

# With parallel execution (CI uses pytest-xdist)
pytest -n auto -m "not integration and not benchmark"

# Integration tests (main branch only)
pytest -m integration --timeout=60
```

---

## Knowledge Gaps

1. **Actual coverage percentages per module**: No coverage report artifact was present in the repo at observation time. The 80% threshold is enforced in CI but the per-module breakdown is not locally visible.
2. **`_defaults/` package criticality**: The exact behavior of default wiring modules (whether they are exercised by any test via import side effects) cannot be determined without running the test suite with coverage instrumentation.
3. **Validation test scope**: The `tests/validation/persistence/` tests appear to validate a specific persistence abstraction; it is not clear whether this maps to `src/autom8_asana/persistence/` or to an external SDK being validated locally.
4. **`entity_context.py` indirect coverage**: This service module appears in no test file name; its coverage via other tests cannot be confirmed without a coverage report.
