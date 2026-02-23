# WS-HTTPX: Fix Phantom httpx Patch Targets

**Finding IDs**: H-001, H-002
**Severity**: HALLUCINATION (conditional-pass blocker)
**Estimated Effort**: 3-4 hours
**Dependencies**: None (independent)
**Lane**: A

---

## Scope

Fix 20 failing tests across 2 files that patch `httpx.AsyncClient` on modules that no longer import `httpx`. Production code migrated to `autom8y_http.Autom8yHttpClient` but test mock targets were not updated.

### Files to Edit

1. **`tests/unit/clients/data/test_client.py`** (H-001)
   - 10 patch sites at lines: 217, 245, 270, 289, 306, 320, 334, 352, 363, 489
   - 11 test failures in `TestDataServiceClientGetClient` + `TestDataServiceClientConcurrency`
   - 3 additional close/context-manager bugs (lines 120, 167, 193): `aclose` should be `close`

2. **`tests/unit/services/test_gid_push.py`** (H-002)
   - 8 patch sites at lines: 226, 276, 306, 327, 350, 373, 399, 448
   - 9 test failures in `TestPushGidMappingsToDataService` + `TestPiiMaskingInLogs`

### Production Files to Read (do NOT modify)

- `src/autom8_asana/clients/data/client.py` -- uses `autom8y_http.Autom8yHttpClient` with `HttpClientConfig`
- `src/autom8_asana/services/gid_push.py` -- uses `Autom8yHttpClient` with nested `client.raw()` context manager
- Check `autom8y_http` package API: `Autom8yHttpClient`, `HttpClientConfig`, `TimeoutException`

---

## Objective

**Done when**:
- All 20 currently-failing tests pass
- Zero regressions in passing tests for both files
- No `httpx` patch targets remain in either file (import of `httpx` for Response construction is OK)
- Gate verdict condition H-001+H-002 is resolved

---

## Fix Patterns (from Remediation Report)

### H-001: test_client.py `_get_client` tests

Replace:
```python
with patch("autom8_asana.clients.data.client.httpx.AsyncClient") as mock_client_cls:
```

With:
```python
with patch("autom8_asana.clients.data.client.Autom8yHttpClient") as mock_class:
    mock_instance = AsyncMock()
    mock_instance.close = AsyncMock()
    mock_class.return_value = mock_instance
```

Assert on `HttpClientConfig` fields (`.base_url`, `.connect_timeout`, `.read_timeout`, etc.) instead of `httpx.AsyncClient` constructor kwargs.

### H-001: test_client.py close tests (lines 120, 167, 193)

Change `mock_http.aclose` to `mock_http.close` (production calls `await self._client.close()`, not `aclose`).

### H-002: test_gid_push.py

Production uses two-layer context manager:
```python
async with Autom8yHttpClient(_PUSH_CONFIG) as client:
    async with client.raw() as raw_client:
        response = await raw_client.post(url, json=payload, headers=headers)
```

Replace:
```python
with patch("autom8_asana.services.gid_push.httpx.AsyncClient") as mock_client_cls:
```

With nested mock chain:
```python
with patch("autom8_asana.services.gid_push.Autom8yHttpClient") as mock_http_cls:
    mock_raw_client = AsyncMock()
    mock_raw_client.post.return_value = mock_response

    mock_raw_cm = AsyncMock()
    mock_raw_cm.__aenter__ = AsyncMock(return_value=mock_raw_client)
    mock_raw_cm.__aexit__ = AsyncMock(return_value=None)

    mock_outer_client = AsyncMock()
    mock_outer_client.raw.return_value = mock_raw_cm

    mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_outer_client)
    mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=None)
```

Update assertions from `mock_client.post` to `mock_raw_client.post`.

For timeout test (line 327): change `httpx.ReadTimeout` to `autom8y_http.TimeoutException`.

---

## Context References

- **Detailed fix instructions**: `.wip/REMEDY-tests-unit-p1.md` (Batch 1: RS-001, RS-002)
- **Detection evidence**: `.claude/wip/SLOP-CHOP-TESTS-P1/phase1-detection/DETECTION-REPORT.md`
- **Production client API**: Read `src/autom8_asana/clients/data/client.py` lines 1-50 for imports
- **Production gid_push API**: Read `src/autom8_asana/services/gid_push.py` lines 1-30 for imports

---

## Constraints

- **Test-only changes**: Do NOT modify any production source files
- **Preserve test intent**: Each test's behavioral assertion must be preserved or strengthened
- **httpx import OK for test side**: `import httpx` for constructing `httpx.Response` mock objects is valid
- **Do NOT expand scope**: Only fix the 20 identified tests. Do not refactor surrounding test code.

---

## Verification

```bash
# Verify all 20 previously-failing tests now pass
source .venv/bin/activate && AUTOM8Y_ENV=test AUTOM8_DATA_URL=http://localhost:5200 \
  python -m pytest \
  tests/unit/clients/data/test_client.py \
  tests/unit/services/test_gid_push.py \
  -n auto -q --tb=short

# Expected: 0 failures (was 20 failures before fix)
# Total tests: ~63 (43 passing + 20 fixed)
```

```bash
# Verify no httpx patch targets remain
grep -rn "httpx.AsyncClient" tests/unit/clients/data/test_client.py tests/unit/services/test_gid_push.py
# Expected: 0 matches
```
