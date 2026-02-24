# WS-OVERMOCK Findings: High-Patch-Count Test Investigation

**Date**: 2026-02-24
**Findings**: LS-028, LS-029
**Verdict**: **ACCEPT**
**Session**: session-20260224-011048-7c4c66fb

---

## Executive Summary

The high mock-patch counts in these test files are **predominantly structural** -- they mock genuine external boundaries (Asana API, S3, CloudWatch, auth). The core business logic IS exercised. The real issue is **boilerplate repetition**, not test brittleness. Existing conftest fixtures could reduce visual noise but aren't leveraged by these files.

**No code changes recommended.** The mock density is the cost of testing functions with many real external dependencies.

---

## LS-028: test_cache_warmer.py

### Patch Census

| Test Class | Tests | Patches | Max per Test |
|---|---|---|---|
| TestWarmCacheAsync | 5 | 18 | 4 |
| TestHandler | 5 | 5 | 1 |
| TestHandlerAsync | 3 | 3 | 1 |
| TestShouldExitEarly | 8 | 0 | 0 |
| TestEmitMetric | 3 | 4 | 2 |
| **TestCheckpointIntegration** | **4** | **24** | **9** |
| TestHandlerContextPassing | 3 | 3 | 1 |
| TestWarmResponseExtended | 3 | 0 | 0 |
| **Total** | **34** | **57** | **9** |

The "24 patches" flagged in LS-028 maps to `TestCheckpointIntegration` (4 tests, 24 patches). The worst single test is `test_clears_checkpoint_on_success` with 9 patches.

### Patch Categorization (TestCheckpointIntegration, 24 patches)

| Category | Count | % | Examples |
|---|---|---|---|
| **Boundary** (external I/O) | 9 | 37% | `AsanaClient`, `emit_metric`, `get_bot_pat` |
| **Factory/singleton** (wraps boundary) | 9 | 37% | `get_dataframe_cache`, `EntityProjectRegistry.get_instance`, `CheckpointManager` |
| **Configuration** | 4 | 17% | `os.environ` (patch.dict) |
| **Internal implementation** | 2 | 8% | `CacheWarmer`, `WarmResult` |

### Root Cause

`_warm_cache_async()` is a ~430-line orchestrator function that creates ALL dependencies internally via imports and factory calls:

```
_warm_cache_async()
  -> get_dataframe_cache()          # S3 cache factory
  -> EntityProjectRegistry.get_instance()  # singleton
  -> CheckpointManager(bucket=...)  # S3-backed checkpoint
  -> get_bot_pat()                  # credential retrieval
  -> resolve_secret_from_env(...)   # env config
  -> AsanaClient(token=...)         # external API
  -> CacheWarmer(cache=...)         # internal warmer
  -> emit_metric(...)               # CloudWatch
```

8 dependencies, all created inline. No constructor injection. Tests must patch each one at the module level.

### Assessment

The patches are **structurally necessary**. The "factory/singleton" category (37%) mocks things like `get_dataframe_cache` and `CheckpointManager` that wrap S3 -- these are boundary-adjacent, not internal implementation detail.

**Could DI reduce patches?** Yes -- if `_warm_cache_async` accepted its dependencies as parameters, tests could inject mocks directly instead of patching module-level lookups. But this would be a significant refactor of a 430-line function that currently works correctly.

**Could a fixture factory help?** Modestly. The 5-patch common core (env vars, cache, registry, bot_pat, client) repeats across `TestCheckpointIntegration` tests. A fixture could reduce each test from ~8 patches to ~3-4. But with only 4 tests in the class, the ROI is low.

---

## LS-029: test_routes_query.py + test_routes_query_rows.py

### Patch Census

| File | Tests | Patches | Max per Test |
|---|---|---|---|
| test_routes_query.py | 24 | 57 | 4 |
| test_routes_query_rows.py | 21 | 75 | 5 |
| **Total** | **45** | **132** | **5** |

### The Dominant Pattern

15 of 21 tests in `test_routes_query_rows.py` and 10 of 24 in `test_routes_query.py` follow the exact same 4-patch pattern:

```python
with (
    patch("...validate_service_token", _mock_jwt_validation()),    # auth boundary
    patch("...get_bot_pat", return_value="test_bot_pat"),           # credential boundary
    patch("...AsanaClient") as mock_client_class,                  # external API boundary
    patch("..._get_dataframe", new_callable=AsyncMock, ...),       # cache/strategy
):
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)   # boilerplate
    mock_client.__aexit__ = AsyncMock(return_value=None)           # boilerplate
    mock_client_class.return_value = mock_client                   # boilerplate
```

That's 4 patches + 3 boilerplate lines, repeated ~25 times across two files.

### Patch Categorization (4-patch pattern)

| Category | Count | % | Notes |
|---|---|---|---|
| **Boundary** (auth) | 1 | 25% | `validate_service_token` -- JWT validation |
| **Boundary** (credential) | 1 | 25% | `get_bot_pat` -- bot PAT retrieval |
| **Boundary** (external API) | 1 | 25% | `AsanaClient` -- Asana API client |
| **Internal** (strategy) | 1 | 25% | `_get_dataframe` -- cache data source |

3 of 4 patches target genuine external boundaries. The 4th (`_get_dataframe`) is debatable -- it's an internal method on `UniversalResolutionStrategy`, but it wraps S3 cache access.

### Root Cause

The route handlers create `AsanaClient` directly inside the endpoint function:

```python
# query.py:169
async with AsanaClient(token=ctx.bot_pat) as client:
    result = await engine.execute_rows(...)
```

This forces tests to patch the class constructor. If the route used FastAPI's `Depends()` to receive the client, the existing `authed_client` conftest fixture would work.

### Existing Infrastructure NOT Leveraged

The conftest at `tests/unit/api/conftest.py` already provides:
- `mock_asana_client` fixture (line 271) -- fully mocked AsanaClient with async context manager
- `authed_client` fixture (line 312) -- authenticated client with dependency overrides
- `auth_header` fixture (line 302)

**None of these are used by the query test files.** Each query test manually constructs its own mock client and patch context.

### Assessment

The repetition is the problem, not the mocking itself. The 4-patch pattern is appropriate for isolating a route handler from external dependencies. But copy-pasting it 25 times across two files is a test ergonomics issue.

**Could a fixture factory reduce patch count?** Yes -- a `query_client` fixture wrapping the 4 patches + 3 boilerplate lines would reduce each test from 7 setup lines to a single fixture parameter. This is a pure test-infrastructure change.

**Would production DI changes help?** If `query_rows` and `query_entities` received `AsanaClient` via `Depends()`, the existing `authed_client` conftest fixture would work directly. But this changes production code for test convenience -- not recommended as a standalone change.

---

## query_v2.py

The file `src/autom8_asana/api/routes/query_v2.py` referenced in the PROMPT-0 scope **does not exist**. The "v2" equivalent is the `/rows` endpoint in `query.py` itself (line 143: `@router.post("/{entity_type}/rows")`). The legacy `POST /{entity_type}` endpoint is deprecated (sunset 2026-06-01) with the `/rows` endpoint as its successor. Both use the same test patterns with identical mock density.

---

## Answers to Investigation Questions

### 1. What percentage of patches mock external boundaries vs internal implementation?

| Finding | Boundary | Factory/Singleton (wraps boundary) | Config | Internal |
|---|---|---|---|---|
| LS-028 (57 patches) | 37% | 37% | 17% | 8% |
| LS-029 (132 patches) | 75% | -- | -- | 25% |

**~75-90% of patches target external boundaries or their immediate wrappers.** True internal-only mocks are <10% of total.

### 2. Would a conftest fixture factory reduce patch count without losing coverage?

**For LS-029: Yes**, significantly. A query-specific fixture could encapsulate the 4-patch + 3-boilerplate pattern, reducing ~25 tests from 7 setup lines to 1 fixture parameter each. Coverage would be preserved.

**For LS-028: Marginally.** The 5-patch common core could become a fixture, but with only 4 tests in `TestCheckpointIntegration`, the payoff is small.

### 3. Is there a structural production-code change (DI, factory) that would reduce patches?

**For cache_warmer**: Yes -- `_warm_cache_async` could accept dependencies as parameters. But this is a major refactor of a 430-line function. Not justified for test ergonomics alone.

**For query routes**: Yes -- injecting `AsanaClient` via `Depends()` instead of constructing it inline. The conftest already supports this pattern. But changing production code purely for test convenience is low priority.

### 4. Recommendation

## **ACCEPT**

**Rationale:**
1. The mock density is **structural**, not pathological -- most patches target real external boundaries
2. The core logic (checkpoint state machines, Polars filtering, pagination, error handling) **IS exercised**
3. The repetition in LS-029 is a **cosmetic/ergonomics issue**, not a correctness or brittleness issue
4. Existing conftest infrastructure already supports better patterns but isn't leveraged -- this is a test authoring habit, not a missing capability
5. No production code changes are needed

**Optional follow-up** (D-027 scope, not urgent):
- Add a `query_test_client` fixture to `tests/unit/api/conftest.py` that encapsulates the 4-patch pattern
- Update query test files to use existing `mock_asana_client` fixture
- Estimated effort: 1-2 hours, zero production risk

---

## Appendix: File Statistics

| File | Lines | Tests | Total Patches | Patches/Test |
|---|---|---|---|---|
| test_cache_warmer.py | 913 | 34 | 57 | 1.7 |
| test_routes_query.py | 965 | 24 | 57 | 2.4 |
| test_routes_query_rows.py | 870 | 21 | 75 | 3.6 |
| **Total** | **2748** | **79** | **189** | **2.4** |
