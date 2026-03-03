# Phase 1: Detection Report — Hallucination Scan

**Scope**: tests/unit/ (389 files, ~184K LOC, 9795 tests)
**Agent**: hallucination-hunter (supplemented by hub thread verification)
**Date**: 2026-02-23

## Summary

| Category | Confirmed | False Positive | Total Sites |
|----------|-----------|----------------|-------------|
| Phantom patch targets | 2 clusters | 1 cluster | 18+20 sites |
| Phantom imports | 0 | 0 | 0 |
| Orphaned fixtures | 0 found | — | — |
| Dead API references | 0 found | — | — |

**Confirmed failures caused by hallucinations: 20 tests**

---

## Confirmed Findings

### [H-001] Phantom patch target: `autom8_asana.clients.data.client.httpx.AsyncClient`
- **Files**: `tests/unit/clients/data/test_client.py` (10 sites)
- **Lines**: 217, 245, 270, 289, 306, 320, 334, 352, 363, 489
- **Evidence**: Tests patch `autom8_asana.clients.data.client.httpx.AsyncClient` but `client.py` does NOT import `httpx` — the module has zero httpx imports. Production code uses `autom8y_http.Autom8yHttpClient`.
- **Verification**: `grep -n "httpx" src/autom8_asana/clients/data/client.py` → only docstring references. `python -c "import autom8_asana.clients.data.client; print(hasattr(autom8_asana.clients.data.client, 'httpx'))"` → `False`
- **Severity**: HALLUCINATION (confirmed non-existent)
- **Impact**: 11 test failures (AttributeError at runtime)
- **Root cause**: Tests were written against pre-decomposition code that imported `httpx` directly. After DataServiceClient was split into 7 focused modules and migrated to `autom8y_http`, the `httpx` import was removed but tests were not updated.
- **Fix**: Correct patch targets to mock `autom8y_http.Autom8yHttpClient` where the production code actually uses it, OR refactor tests to mock at the method level instead of the client constructor.

### [H-002] Phantom patch target: `autom8_asana.services.gid_push.httpx.AsyncClient`
- **Files**: `tests/unit/services/test_gid_push.py` (8 sites)
- **Lines**: 226, 276, 306, 327, 350, 373, 399, 448
- **Evidence**: Tests patch `autom8_asana.services.gid_push.httpx.AsyncClient` but `gid_push.py` does NOT import `httpx`. Production uses `from autom8y_http import Autom8yHttpClient, HttpClientConfig, TimeoutException` (line 16).
- **Verification**: `grep "httpx" src/autom8_asana/services/gid_push.py` → no matches. Module imports `autom8y_http.Autom8yHttpClient`.
- **Severity**: HALLUCINATION (confirmed non-existent)
- **Impact**: 9 test failures (AttributeError at runtime)
- **Root cause**: Same migration-era drift as H-001. `gid_push.py` was migrated from `httpx` to `autom8y_http` but tests retained the old patch target.
- **Fix**: Correct patch targets to `autom8y_http.Autom8yHttpClient` or mock at the method/instance level.

---

## Investigated and Dismissed (False Positives)

### [H-FP-001] `autom8_asana.cache.dataframe_cache` patch targets
- **Files**: `tests/unit/cache/dataframe/test_dataframe_cache.py` (18 sites), `test_schema_version_validation.py` (2 sites)
- **Evidence**: Tests patch `autom8_asana.cache.dataframe_cache.asyncio.create_task` — the module `autom8_asana.cache.dataframe_cache` doesn't exist as a file (actual location: `cache/integration/dataframe_cache.py`)
- **Why dismissed**: `cache/__init__.py:295` has a `__getattr__` lazy loader that returns `autom8_asana.cache.integration.dataframe_cache` when `dataframe_cache` is accessed. `unittest.mock.patch()` uses attribute traversal (not module import), so it triggers `__getattr__` and resolves correctly.
- **Verification**: `pytest tests/unit/cache/dataframe/test_dataframe_cache.py` → **61 passed, 0 failed**
- **Status**: NOT A HALLUCINATION — works via lazy loading

---

## Global httpx Verification

`httpx` is not imported as a module (`import httpx`) anywhere in the production codebase:
```
grep -r "^import httpx\|^from httpx" src/autom8_asana/ → 0 results
```
The project migrated from `httpx` to `autom8y_http` (internal HTTP client library). All `httpx` references in test patch targets are post-migration phantoms.

## Recommendations for Phase 4 (Remediation)

1. **H-001 + H-002**: These 20 failing tests need patch target correction. The correct target is `autom8y_http.Autom8yHttpClient` as used in the production modules. This will require reading the test logic to determine whether to patch at constructor or method level.
2. Consider a sweep for any other `httpx` patch targets outside the two files identified.
