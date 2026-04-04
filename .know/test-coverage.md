---
domain: test-coverage
generated_at: "2026-04-04T12:00:00Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./app/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "55aaab5"
confidence: 0.85
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

The test suite spans 480 test files in `tests/`, covering 22 of 26 source packages. Four source packages have zero dedicated test directories:

| Source Package | Test Coverage | Notes |
|---|---|---|
| `src/autom8_asana/observability/` | Indirect | Covered via `tests/unit/test_observability.py` |
| `src/autom8_asana/protocols/` | Indirect | Protocol types imported in cache, client, and persistence tests |
| `src/autom8_asana/_defaults/` | Partial | `_defaults/cache.py` tested via client tests; auth/log/observability have no dedicated coverage |
| `src/autom8_asana/batch/` | Indirect | Covered via `tests/unit/clients/test_batch.py` and integration tests |

### Module-Level Gaps Within Covered Packages

**lifecycle** (2 source modules unmatched):
- `src/autom8_asana/lifecycle/loop_detector.py` — no `test_loop_detector.py` found
- `src/autom8_asana/lifecycle/observation_store.py` — no `test_observation_store.py` found
- All other 13 lifecycle modules have corresponding test files

**models/business** (5 source modules unmatched):
- `src/autom8_asana/models/business/dna.py` — no direct test file
- `src/autom8_asana/models/business/mixins.py` — no direct test file
- `src/autom8_asana/models/business/videography.py` — no direct test file
- `src/autom8_asana/models/business/reconciliation.py` — no direct test file
- `src/autom8_asana/models/business/detection/tier1.py` through `tier4.py` — tested via `tests/unit/models/business/test_detection.py`; no tier-specific unit test files

**models (top-level)** — Asana resource models (`attachment.py`, `base.py`, `common.py`, `custom_field.py`, `goal.py`, `portfolio.py`, `project.py`, `section.py`, `story.py`, `tag.py`, `task.py`, `team.py`, `user.py`, `webhook.py`, `workspace.py`) have no direct test files. Tested indirectly through all tests that instantiate them.

**cache** (14 source modules unmatched by direct test file):
- `base.py`, `completeness.py`, `derived.py`, `errors.py`, `factory.py`, `freshness_unified.py`, `memory.py`, `progressive.py`, `redis.py`, `s3.py`, `schema_providers.py`, `staleness_settings.py`, `upgrader.py`
- Covered through higher-level cache integration and backend tests

**clients** (24 source modules unmatched by direct test file):
- Private endpoint modules (`_cache.py`, `_metrics.py`, `_normalize.py`, `_pii.py`, `_policy.py`, `_response.py`, `_retry.py`) — `_pii.py` covered via `tests/unit/clients/utils/test_pii.py`
- Client modules (`attachments.py`, `goals.py`, `goal_followers.py`, `portfolios.py`, `projects.py`, `sections.py`, `stories.py`, `tags.py`, `task_operations.py`, `task_ttl.py`, `tasks.py`, `teams.py`, `users.py`, `webhooks.py`, `workspaces.py`) — tested through higher-level integration and service tests

**services** (2 source modules with no matching test):
- `src/autom8_asana/services/entity_context.py` — no `test_entity_context.py`
- `src/autom8_asana/services/resolver.py` — tested via `tests/unit/api/routes/test_resolver_status.py`

### Integration Test Gaps

- No integration tests for: `auth`, `clients`, `models`, `metrics`, `query`, `patterns`, `transport`, `search`, `reconciliation`
- Integration tests exist for: `automation`, `cache`, `persistence`, `lifecycle`, `detection`, `api/preload`

### Summary Coverage Counts

| Suite | Test Files | Approximate Test Functions |
|---|---|---|
| Unit (`tests/unit/`) | 439 | ~11,634 |
| Integration (`tests/integration/`) | 31 | ~568 |
| Validation (`tests/validation/`) | 5 | -- |
| Synthetic (`tests/synthetic/`) | 1 | -- |
| Benchmarks (`tests/benchmarks/`) | 3 | -- |
| **Total** | **480** | **~12,347** |

---

## Testing Conventions

### Test Framework and Configuration

- **Runner**: pytest, configured in `pyproject.toml` under `[tool.pytest.ini_options]`
- **asyncio mode**: `asyncio_mode = "auto"` — all async test functions run automatically without `@pytest.mark.asyncio`
- **Timeout**: 60 seconds per test; method: thread-based (`timeout_method = "thread"`)
- **Test paths**: `testpaths = ["tests"]`
- **Coverage target**: `fail_under = 80` in `[tool.coverage.report]`; branch coverage enabled
- **Coverage source**: `src/autom8_asana`

### Markers

| Marker | Usage Count | Meaning |
|---|---|---|
| `pytest.mark.asyncio` | 2,584 | Legacy — pre-dates `asyncio_mode = "auto"`; redundant but harmless |
| `pytest.mark.parametrize` | 109 | Parameterized test cases |
| `pytest.mark.integration` | 45 | Requires live API access |
| `pytest.mark.usefixtures` | 38 | Fixture injection |
| `pytest.mark.slow` | 23 | Slow tests (deselectable with `-m "not slow"`) |
| `pytest.mark.skip` | 10 | Explicitly skipped |
| `pytest.mark.skipif` | 8 | Conditionally skipped |
| `pytest.mark.benchmark` | 4 | Performance benchmarks |
| `pytest.mark.xfail` | 1 | Expected failures |

### Mocking Conventions

- `AsyncMock` (3,168 occurrences) — used for async methods/coroutines
- `MagicMock` (4,524 occurrences) — used for sync objects, clients, services
- `patch` imported and used in 96+ test files
- Common import: `from unittest.mock import AsyncMock, MagicMock, patch`

### Fixture Infrastructure

- **678 `@pytest.fixture` decorators** across the test suite
- **14 `conftest.py` files** at various scopes

**Root-level fixtures** in `tests/conftest.py`:

| Fixture | Scope | Purpose |
|---|---|---|
| `mock_http` | function | `MockHTTPClient` with `AsyncMock` for all 8 HTTP methods |
| `config` | function | Bare `AsanaConfig()` |
| `auth_provider` | function | `MockAuthProvider` returning `"test-token"` |
| `logger` | function | `MockLogger` from `autom8y-log` SDK |
| `mock_client_builder` | function | Returns `MockClientBuilder` class (builder pattern for `AsanaClient` mocks) |
| `_bootstrap_session` | session | Bootstraps `ProjectTypeRegistry` and rebuilds all Pydantic model forward refs once per session |
| `reset_all_singletons` | function (autouse) | Calls `SystemContext.reset_all()` before and after every test; ensures complete test isolation |

**API conftest** (`tests/unit/api/conftest.py`): Module-scoped `app` fixture creates `TestAPI` instance with mocked lifespan.

### Test Organization Patterns

1. **Mirror structure**: `tests/unit/{package}/` mirrors `src/autom8_asana/{package}/`
2. **Adversarial tests**: Dedicated files named `test_{module}_adversarial.py` — failure cases, edge conditions
3. **Contract tests**: Files named `test_{feature}_contract.py` — behavioral guarantees
4. **Span tests**: Files named `test_{feature}_spans.py` — OpenTelemetry instrumentation
5. **Validation suite** (`tests/validation/`): Separate persistence-specific validation (concurrency, functional, error handling, performance)

### Test Isolation

- `SystemContext.reset_all()` called via `autouse=True` `reset_all_singletons` fixture — resets all singletons, registries, caches between every test
- `EntityProjectRegistry.reset()` called per-test in API conftest
- Import-time singletons have explicit clear functions: `clear_bot_pat_cache()`, `reset_auth_client()`

---

## Test Structure Summary

### Directory Layout

```
tests/
  conftest.py                    # Root fixtures
  _shared/
    mocks.py                     # MockTask (used by automation/polling tests)
  unit/                          # 439 test files, ~11,634 test functions
    api/                         # 55 files: routes, middleware, preload, health
    auth/                        # 6 files: bot_pat, audit, jwt, dual_mode
    automation/                  # 43 files: events, polling, workflows, engine
    cache/                       # 56 files: backends, dataframe, policies
    clients/                     # 36 files: data client, name_resolver
    core/                        # 10 files: registry, concurrency, retry
    dataframes/                  # 49 files: builders, views, schemas
    detection/                   # 1 file
    lambda_handlers/             # 16 files: warmer, checkpoint, workflow
    lifecycle/                   # 15 files: engine, creation, completion
    metrics/                     # 10 files: compute, registry, definitions
    models/                      # 40 files: business models, matching
    patterns/                    # 2 files: async_method, error_classification
    persistence/                 # 28 files: session, cascade, executor
    query/                       # 21 files: engine, compiler, hierarchy
    reconciliation/              # 4 files: contract, executor, processor
    resolution/                  # 7 files: strategies, field_resolver
    search/                      # 3 files: models, service
    services/                    # 22 files: universal_strategy, section_service
    transport/                   # 7 files: asana_http, aimd
  integration/                   # 31 test files, ~568 test functions
  validation/
    persistence/                 # 5 files: concurrency, functional, error
  synthetic/
    test_synthetic_coverage.py
  benchmarks/                    # 3 files
```

### Hotspot Files (High-Change Frequency)

| File | Test Count | Notes |
|---|---|---|
| `tests/unit/dataframes/builders/test_cascade_validator.py` | 33 | Cascade field validation |
| `tests/unit/dataframes/views/test_cascade_view.py` | 31 | View layer over cascaded fields |
| `tests/unit/services/test_universal_strategy.py` | 41 | Core universal field resolution |
| `tests/unit/services/test_universal_strategy_status.py` | 26 | Status-specific resolution |
| `tests/unit/services/test_universal_strategy_null_slot.py` | 3 | Null slot edge cases |
| `tests/unit/services/test_universal_strategy_spans.py` | 5 | OTel span assertions |
| `tests/unit/api/routes/test_resolver_status.py` | 8 | Resolver HTTP status contract |
| `tests/unit/api/routes/test_resolver_models.py` | 36 | Resolver models |

### Test Density by Domain

| Domain | Test Files | Test Functions | Density |
|---|---|---|---|
| cache | 56 | ~1,301 | High |
| models | 40 | ~1,458 | High |
| automation | 43 | ~1,108 | High |
| dataframes | 49 | ~1,171 | High |
| api | 55 | ~982 | High |
| persistence | 28 | ~982 | High |
| query | 21 | ~907 | Medium-high |
| clients | 36 | ~880 | Medium-high |
| services | 22 | ~669 | Medium |
| lifecycle | 15 | ~362 | Medium |
| core | 10 | ~355 | Medium |
| lambda_handlers | 16 | ~263 | Medium |
| auth | 6 | ~89 | Low |
| reconciliation | 4 | ~87 | Low |
| patterns | 2 | ~67 | Low |
| search | 3 | ~51 | Low |
| detection | 1 | -- | Low |

### Fixture Architecture

The fixture hierarchy flows:
1. `tests/conftest.py` — session bootstrap + per-test singleton reset (autouse)
2. Sub-package `conftest.py` — domain-specific fixtures
3. Inline fixtures — per-file helper fixtures

`MockClientBuilder` implements builder pattern allowing explicit opt-in of mock capabilities before `build()`.

### No Test Data Directories

No `fixtures/`, `data/`, or `testdata/` directories in `tests/`. All test data constructed inline via factories and `MockClientBuilder`.

---

## Knowledge Gaps

1. **Actual coverage percentage** — `fail_under = 80` configured but no coverage report was run during this audit.
2. **Whether lifecycle `test_loop_detector.py` is missing intentionally** — may be infrastructure code not intended for direct testing.
3. **Validation suite scope** — `tests/validation/persistence/` relationship to main test suite (CI inclusion) not visible from static analysis.
4. **Synthetic test purpose** — `tests/synthetic/test_synthetic_coverage.py` purpose unclear without reading contents.
5. **`pytest.mark.asyncio` cleanup status** — 2,584 uses despite `asyncio_mode = "auto"` making them redundant.
6. **Integration test live-API dependency** — Which integration tests require a live Asana API token is unclear; `@pytest.mark.integration` marker appears inconsistently.
