---
domain: test-coverage
generated_at: "2026-02-27T11:21:29Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "73b6e61"
confidence: 0.85
format_version: "1.0"
---

# Codebase Test Coverage

## Coverage Gaps

### Overall Coverage Landscape

The project has 470 test files totaling ~225K lines, with 11,121 tests passing at last baseline count. The test-to-source ratio is approximately 1.1:1 by file count (470 test files vs 421 source files) and 1.9:1 by LOC (225K test vs 120K source).

### Test Distribution by Package

| Source Package | Test Directory | Has Tests | Coverage Level |
|---------------|----------------|-----------|---------------|
| `api/` | `tests/unit/api/` | Yes | High -- routes, middleware, dependencies, errors |
| `api/routes/` | `tests/unit/api/routes/` | Yes | High -- all 15 route modules |
| `auth/` | `tests/unit/auth/` | Yes | Moderate |
| `automation/` | `tests/unit/automation/` | Yes | Moderate -- engine, config, events |
| `automation/polling/` | `tests/unit/automation/polling/` + integration | Yes | Moderate |
| `automation/workflows/` | `tests/unit/automation/workflows/` | Yes | Moderate |
| `batch/` | Tests in `tests/unit/` | Yes | Present |
| `cache/` | `tests/unit/cache/` | Yes | High -- backends, dataframe, providers |
| `clients/` | `tests/unit/clients/` | Yes | High -- Asana resource clients |
| `clients/data/` | `tests/unit/clients/data/` | Yes | High -- DataServiceClient modules |
| `core/` | `tests/unit/core/` | Yes | Moderate |
| `dataframes/` | `tests/unit/dataframes/` | Yes | High -- builders, extractors, models, views |
| `lambda_handlers/` | `tests/unit/lambda_handlers/` | Yes | Present |
| `lifecycle/` | `tests/unit/lifecycle/` | Yes | High -- engine, config, services |
| `metrics/` | `tests/unit/metrics/` | Yes | Present |
| `models/` | `tests/unit/models/` | Yes | High -- Pydantic models, business entities |
| `models/business/` | `tests/unit/models/business/` | Yes | High |
| `observability/` | (inline) | Partial | Minimal dedicated tests |
| `patterns/` | `tests/unit/patterns/` | Yes | Present |
| `persistence/` | `tests/unit/persistence/` | Yes | High -- SaveSession, actions, graph |
| `protocols/` | (no dedicated) | No | Protocols are tested implicitly via implementors |
| `query/` | `tests/unit/query/` | Yes | High -- engine, compiler, models, CLI |
| `resolution/` | `tests/unit/resolution/` | Yes | Moderate |
| `search/` | `tests/unit/search/` | Yes | Present |
| `services/` | `tests/unit/services/` | Yes | High -- query, entity, resolver |
| `transport/` | `tests/unit/transport/` | Yes | Moderate |

### Packages Without Dedicated Tests

- `protocols/` -- By design, protocols define interfaces. They are tested implicitly through their implementing classes. No coverage gap.
- `_defaults/` -- Default provider implementations tested indirectly through client construction tests. Minimal gap.
- `observability/` -- Limited dedicated tests. Tested partially through integration with API layer.

### Critical Path Coverage Assessment

| Critical Path | Coverage | Gap Assessment |
|--------------|----------|----------------|
| API request lifecycle | High | Routes, middleware, auth, errors all tested |
| DataFrame cache warming | High | S3, memory, progressive preload tested |
| QueryEngine row retrieval | High | Predicate compilation, section scoping, joins |
| SaveSession commit | High | Action execution, dependency graph, healing |
| Lifecycle transitions | High | Engine, cascading, seeding, wiring |
| DataServiceClient calls | High | Endpoints, PII, retry, cache |
| Entity detection/matching | High | Business model detection and matching |
| Webhook dispatch | Moderate | Basic dispatch flow tested |
| Lambda handlers | Moderate | Handler entry points tested, less edge-case coverage |
| CLI (query, metrics) | Moderate | Core functionality tested, fewer edge cases |

### Known Test Failures (Pre-Existing)

At last baseline (11,121 passed), approximately 178 pre-existing test failures exist in untouched files. These are tracked but not blocking. Recent initiatives (REM-HYGIENE) resolved 629 test issues without regressions.

### Prioritized Gap List

1. **Lambda handlers edge cases** -- Entry points are tested but error paths and retry behavior have limited coverage
2. **Observability hooks** -- Limited dedicated tests for metric emission and trace correlation
3. **Transport layer** -- Adaptive semaphore and sync wrapper edge cases
4. **CLI edge cases** -- `--live` mode HTTP client, saved query resolution error paths
5. **Automation workflow templates** -- Template rendering and validation edge cases

## Testing Conventions

### Test Function Naming

Tests follow `test_<behavior_description>` convention:
```python
def test_query_engine_filters_by_section():
def test_save_session_raises_on_closed():
def test_entity_registry_lookup_by_gid():
async def test_data_service_client_retry_on_timeout():
```

Class-based grouping is used for related tests:
```python
class TestQueryEngine:
    def test_rows_basic(self):
    def test_rows_with_join(self):
    async def test_aggregate_count(self):
```

### Assertion Patterns

- Standard `assert` statements (not `assertEqual` style)
- `pytest.raises(SpecificException)` for exception testing (narrowed from generic `Exception` per recent fix)
- `pytest.approx()` for floating-point comparisons
- SDK `MockLogger` for log assertions: `logger.assert_logged(level, event)` or `logger.get_events(level)`
- Pydantic model validation via `model_validate()` and `model_dump()`
- Polars DataFrame assertions via `df.shape`, `df.columns`, `df.to_dicts()`

### Test Helper Patterns

**MockClientBuilder** (`tests/conftest.py`):
Builder pattern for mock `AsanaClient` with explicit opt-in per capability:
```python
client = (MockClientBuilder()
    .with_workspace_gid("123")
    .with_batch(results=[...])
    .with_http()
    .build())
```

**MockHTTPClient** (`tests/conftest.py`):
8-method superset mock HTTP client with `AsyncMock` for each method:
- `get`, `post`, `put`, `delete`, `request`, `get_paginated`, `post_multipart`, `get_stream_url`

**SDK Testing Helpers**:
- `autom8y_log.testing.MockLogger` for structured log assertions
- `respx` for httpx response mocking
- `fakeredis` for Redis mocking
- `moto` for AWS/S3 mocking

### Fixture Patterns

**Root conftest** (`tests/conftest.py`):
- `mock_http` -- MockHTTPClient instance
- `config` -- AsanaConfig for testing
- `auth_provider` -- MockAuthProvider
- `logger` -- SDK MockLogger
- `mock_client_builder` -- MockClientBuilder class reference
- `_bootstrap_session` (autouse, session-scoped) -- Runs `bootstrap()` and `model_rebuild()` for all Pydantic models
- `reset_all_singletons` (autouse) -- `SystemContext.reset_all()` before and after each test

**Package-scoped conftest files** (12 total):
- `tests/unit/api/conftest.py` -- FastAPI TestClient fixtures
- `tests/unit/cache/conftest.py` -- Cache backend fixtures
- `tests/unit/clients/conftest.py` -- Client mock fixtures
- `tests/unit/clients/data/conftest.py` -- DataServiceClient fixtures
- `tests/unit/dataframes/conftest.py` -- DataFrame builder fixtures
- `tests/unit/lifecycle/conftest.py` -- Lifecycle engine fixtures
- `tests/unit/resolution/conftest.py` -- Resolution strategy fixtures
- Plus integration and validation conftest files

### Test Skip Patterns

- `@pytest.mark.slow` -- For slow tests (deselect with `-m "not slow"`)
- `@pytest.mark.integration` -- Integration tests requiring live API
- `@pytest.mark.benchmark` -- Performance benchmarks
- Named skips with `pytest.skip("reason")` -- Used for workspace isolation tests (8 tests feature-gated)
- `pytest.importorskip("module")` -- For optional dependencies

### Test Environment Management

- `monkeypatch` for environment variables (never direct `os.environ` mutation)
- `SystemContext.reset_all()` autouse fixture for singleton cleanup
- `_bootstrap_session` session-scoped fixture for one-time Pydantic model setup
- `pytest-timeout` with 60s default (configurable via `timeout` in pyproject.toml)

### Test Data and Fixtures

- No `testdata/` directories -- test data is constructed inline or via fixtures
- Pydantic model factories: tests construct model instances directly
- Mock response dicts: JSON-like dicts mimicking Asana API responses
- Polars DataFrame fixtures: constructed inline with `pl.DataFrame()`

## Test Structure Summary

### Overall Distribution

- **470 total test files** across 4 categories
- **416 unit test files** (~89%) -- Primary testing approach
- **38 integration test files** (~8%) -- API, automation, persistence, events
- **8 validation test files** (~2%) -- Persistence validation
- **4 benchmark files** (~1%) -- Performance measurement

### Most Heavily Tested Areas

1. **Persistence/SaveSession** (`tests/unit/persistence/`) -- Extensive coverage of Unit of Work, action execution, dependency graph, cascade, healing
2. **Cache subsystem** (`tests/unit/cache/`) -- Backends, dataframe tiers, providers, integration, staleness
3. **DataFrames** (`tests/unit/dataframes/`) -- Builders, extractors, models, views, schemas, resolver
4. **Services** (`tests/unit/services/`) -- Query service, entity service, resolution strategies
5. **API routes** (`tests/unit/api/routes/`) -- All route modules with request/response assertions
6. **Models/business** (`tests/unit/models/business/`) -- Business entity detection, matching, fields
7. **Lifecycle** (`tests/unit/lifecycle/`) -- Engine, config, creation, cascading, seeding, wiring

### Test Package Naming

Tests use external test packages (separate from source):
```
tests/unit/services/test_query_service.py    # tests src/autom8_asana/services/query_service.py
tests/unit/api/routes/test_query.py          # tests src/autom8_asana/api/routes/query.py
```

### Integration Test Patterns

Integration tests in `tests/integration/` use:
- FastAPI TestClient for API endpoint testing
- Real (mocked) Redis/S3 backends via `fakeredis` and `moto`
- Multi-component interaction testing (cache + service + API)
- `@pytest.mark.integration` marker for selective execution

### Test Invocation

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Specific package
pytest tests/unit/services/

# Skip slow tests
pytest -m "not slow"

# With coverage
pytest --cov=src/autom8_asana --cov-report=html
```

Configuration in `pyproject.toml`:
- `asyncio_mode = "auto"` (pytest-asyncio)
- `testpaths = ["tests"]`
- `timeout = 60` seconds per test
- `timeout_method = "thread"`

## Knowledge Gaps

- Exact per-package line coverage percentages were not computed (would require running `pytest --cov`).
- The content of adversarial test files (e.g., `test_adversarial_pacing.py`, `test_tier1_adversarial.py`) was not read in detail.
- Benchmark test specifics (what metrics are measured, what thresholds are used) were not examined.
- The `_shared/` test utility module contents were not read.
