---
domain: test-coverage
generated_at: "2026-04-01T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "24d8e44"
confidence: 0.93
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
**Test runner**: pytest with pytest-asyncio (auto mode), pytest-cov, pytest-xdist (parallel)
**Coverage threshold**: 80% (enforced in CI via `[tool.coverage.report] fail_under = 80`)
**Total test files**: 470 (430 unit, 32 integration, 5 validation, 1 computation spans, 1 benchmarks, 1 root)
**Total test classes**: 2,843
**Source files**: 477 Python source files across 23 top-level packages

## Coverage Gaps

### Packages with Zero Direct Test Coverage

**`_defaults/` (4 source files) -- Medium criticality**
- `src/autom8_asana/_defaults/auth.py`
- `src/autom8_asana/_defaults/cache.py`
- `src/autom8_asana/_defaults/log.py`
- `src/autom8_asana/_defaults/observability.py`

Platform SDK default wiring modules. No dedicated test directory. Default wiring failures would be silent.

**`protocols/` (8 source files) -- Low criticality (intentional)**
All 8 files define PEP 544 Protocol structural interfaces with no executable logic. Absence of tests is expected and correct.

**`batch/` (2 source files) -- Low criticality (indirect coverage)**
No `tests/unit/batch/`. `batch.models.BatchResult` imported in 20+ test files. `batch.client` tested indirectly.

**`observability/` (3 source files) -- Medium criticality**
Single root-level test file `tests/unit/test_observability.py`. No dedicated `tests/unit/observability/` directory. `decorators.py` exercised transitively via span tests.

### Lambda Handlers Coverage Gaps

3 of 11 lambda handler source files have no dedicated test file:

| Handler | Criticality | Notes |
|---|---|---|
| `lambda_handlers/cloudwatch.py` | HIGH | Production monitoring path; never directly tested |
| `lambda_handlers/push_orchestrator.py` | MEDIUM | Cache push orchestration; no direct test |
| `lambda_handlers/timeout.py` | LOW | Thin utility handler |

### Services Package Blind Spots

Three service modules have no dedicated test file but are covered via API route tests: `intake_create_service.py`, `intake_resolve_service.py`, `intake_custom_field_service.py`. `entity_context.py` has no dedicated test file and appears in only 1 test via transitive import.

### Reconciliation Package Gaps

5 source files in `reconciliation/`; only 3 test files. `reconciliation/report.py` and `reconciliation/executor.py` have no visible direct tests. `engine.py` only tested by patching in lambda handler tests.

### Core Utility Gaps

8 of 18 core source files have no dedicated test: `datetime_utils.py`, `entity_types.py`, `field_utils.py`, `logging.py`, `registry.py`, `string_utils.py`, `timing.py`, `types.py`.

### Skipped Tests (Active Blind Spots)

- 5 skipped tests in `tests/integration/test_workspace_switching.py` -- deferred known bugs
- 1 skip in `tests/integration/test_platform_performance.py` -- RS-021 regression
- 1 xfail in `tests/integration/test_lifecycle_smoke.py` -- D-LC-001 known defect
- 1 xfail in `tests/unit/dataframes/test_cascading_resolver.py` -- stale method reference

### Prioritized Gap List

1. **HIGH**: `cloudwatch.py` lambda handler -- production monitoring, no coverage
2. **MEDIUM**: `push_orchestrator.py` lambda handler -- no dedicated test
3. **MEDIUM**: `_defaults/` package (4 files) -- implicit only
4. **MEDIUM**: `entity_context.py` service -- no dedicated test; critical resolution path
5. **MEDIUM**: `reconciliation/report.py`, `reconciliation/executor.py` -- no visible direct tests
6. **LOW**: `timeout.py` lambda handler
7. **LOW**: Core utility modules (8 files) -- transitively covered
8. **LOW**: 5 skipped workspace_switching tests
9. **LOW**: Stale xfail test pointing at removed method

## Testing Conventions

### Test Function Naming

All test functions follow `test_{what_is_being_tested}` convention in snake_case. Error-case suffixes: `test_rejects_*`, `test_raises_on_*`, `test_handles_malformed_*`. Specialized suffixes: `_adversarial`, `_spans`, `_edge_cases`.

### Test Organization

Predominantly class-based structure (2,843 test classes vs ~215 standalone functions). Pure pytest class syntax, no `unittest.TestCase`.

### Async Tests

`asyncio_mode = "auto"` in `pyproject.toml`. `@pytest.mark.asyncio` used explicitly on many classes for documentation purposes but not required.

### Parametrize Pattern

109 uses of `@pytest.mark.parametrize` across the test suite.

### Assertion Patterns

- Primary: `assert` statements (~22,000 occurrences)
- Exception testing: `pytest.raises` (1,327 occurrences) as context manager
- Mock verification: `assert_called`/`assert_awaited`/`assert_not_called`
- Numeric: `pytest.approx` for float comparisons
- Polars DataFrame: `frame_equal()` or column-level `assert`

### Fixture Patterns

Root conftest (`tests/conftest.py`) provides: `mock_http`, `config`, `auth_provider`, `logger` (SDK `MockLogger`), `mock_client_builder`, `_bootstrap_session` (autouse session), `reset_all_singletons` (autouse function). 11 sub-package conftest files with domain-specific fixtures.

### Builder/Factory Patterns

`MockClientBuilder` in root conftest with fluent API. Factory functions (`make_*`, `_make_*`, `build_*`) in test files. `tests/_shared/mocks.py` houses `MockTask` for polling/automation tests.

### Mocking Strategy

`unittest.mock.AsyncMock` and `MagicMock` are primary (390 import occurrences). `respx` used in ~12 files for HTTP-level route mocking. `fakeredis` and `moto` for backend testing with `@pytest.mark.skipif` guards.

### Test Environment Management

`asyncio_mode = "auto"`, 60-second timeout per test via `pytest-timeout` (thread method). Global `_bootstrap_session` and `reset_all_singletons` autouse fixtures ensure isolation. API conftest uses module-scoped `TestClient` with function-scoped singleton resets.

## Test Structure Summary

### Distribution Overview

| Category | Test Files | Approximate Tests |
|---|---|---|
| `tests/unit/` | 430 files | ~11,770 |
| `tests/integration/` | 32 files | ~570 |
| `tests/validation/persistence/` | 5 files | ~121 |
| `tests/` root | 1 file | ~15 |
| `tests/benchmarks/` | 1 file | ~8 |

### Most Heavily Tested Areas (by file count)

1. `cache/` -- 56 test files
2. `api/` -- 53 test files
3. `dataframes/` -- 49 test files
4. `automation/` -- 43 test files
5. `models/` -- 40 test files

### Integration vs Unit Distinction

Unit tests mock all external I/O. Integration tests split between live-API tests (guarded by `ASANA_PAT`) and in-process tests (wire real components, no network). Validation tests provide depth-testing for the persistence layer specifically.

### How Tests Are Run

```bash
# Unit tests (PR gate)
pytest -m "not integration and not benchmark" --cov=autom8_asana --cov-fail-under=80

# Parallel (CI)
pytest -n auto -m "not integration and not benchmark"

# Integration (main branch only)
pytest -m integration --timeout=60
```

## Knowledge Gaps

1. **Actual per-module coverage percentages** -- not locally visible without running `pytest --cov`
2. **`_defaults/` runtime coverage** -- cannot confirm import-side-effect coverage without instrumented run
3. **`cloudwatch.py` actual line coverage** -- transitively referenced but not measured
4. **`entity_context.py` indirect coverage** -- only confirmed in 1 test file import
5. **Core utility transitive coverage** -- likely covered as dependencies, not confirmed
