# ADR: Test Fixture Optimization — Mock Discovery in Shared App Fixture

**Status**: Accepted
**Date**: 2026-02-03
**Deciders**: Architecture team
**Context**: Sprint 3 of Dynamic Query Service initiative

## Context

The fast test suite (`pytest -m "not slow and not integration and not benchmark"`) takes **183 seconds wall-clock** but only **20.1 seconds** (11%) is actual test execution. Profiling reveals that fixture overhead accounts for 89% of total time:

| Phase | Duration | % of Total |
|-------|----------|------------|
| Fixture setup | 87.9s | 48% |
| Test call | 20.1s | 11% |
| Fixture teardown | 68.3s | 37% |
| Collection/import | 7.0s | 4% |

**Root cause**: The shared `app` fixture in `tests/api/conftest.py` calls `create_app()` with function scope. Each invocation triggers the full FastAPI lifespan, including `_discover_entity_projects()` which makes real Asana API calls. At ~400ms setup and ~300ms teardown per test across 165 API tests, this produces ~115 seconds of pure network overhead in what should be a fast, offline test suite.

## Decision

**Strategy A: Mock discovery in the shared `app` fixture** (lowest risk, proven pattern).

Replace the shared `app` fixture in `tests/api/conftest.py` with a version that patches `_discover_entity_projects` using `AsyncMock`. The mock populates `EntityProjectRegistry` with known test data (4 entity types: offer, unit, contact, business) identically to the pattern already proven in `tests/api/test_routes_query.py` (lines 44-78), which has been stable across 82 tests in CI.

Additionally, deduplicate the identical local `app` fixtures in three test files (`test_routes_query.py`, `test_routes_resolver.py`, `test_routes_query_rows.py`) that will now be covered by the shared fixture.

## Alternatives Considered

### Strategy B: Module-scoped app fixture
- **Approach**: Change fixture scope from `function` to `module`, sharing one `create_app()` call across all tests in a module.
- **Rejected because**: Requires auditing all 165 tests for shared state leakage. Higher isolation risk. Real API calls still happen (once per module), so the fixture still depends on network availability.

### Strategy C: Session-scoped app fixture
- **Approach**: Single `create_app()` call for the entire test session.
- **Rejected because**: Maximum isolation risk. Any test that modifies app state affects all subsequent tests. Requires comprehensive state-reset mechanisms. Diminishing returns compared to Strategy A.

### Strategy D: pytest-xdist parallel execution
- **Approach**: Distribute tests across CPU cores to divide wall-clock time.
- **Deferred, not rejected**: This is complementary to Strategy A and can be layered on later. Strategy A eliminates the dominant cost first; parallelization would then divide the remaining ~70-85s by core count.

## Consequences

### Positive
- **~60% wall-clock reduction**: Projected drop from 183s to ~70-85s by eliminating ~100s of network overhead
- **Offline-capable**: Fast suite no longer requires network access or valid Asana credentials
- **Deterministic**: Mock data eliminates flaky failures from API rate limits or network timeouts
- **DRY**: Removes ~120 lines of duplicated fixture code across 3 files
- **Zero isolation risk**: Function-scoped fixtures maintained; each test gets a fresh app instance

### Negative
- **Reduced integration coverage in fast suite**: The shared fixture no longer exercises the real `_discover_entity_projects` code path. This is acceptable because:
  - Discovery is tested by integration tests (`-m integration`), not the fast suite
  - The mock pattern has been stable across 82 tests with no false positives
  - Real discovery behavior is a deployment concern, not a unit test concern

### Neutral
- **Test count unchanged**: No tests added or removed (~7570 total)
- **No production code changes**: Only test infrastructure is modified

## Rollback

Single-commit revert restores original `app` fixture. Partial rollback possible by re-adding local fixtures to individual test files.

## Future Work

If further optimization is needed after measuring Phase 1 results, `pytest-xdist -n auto` (parallel execution across CPU cores) would divide the ~70-85s by core count (4 cores → ~18-21s). This would be a separate ADR.
