# QA Report: --live auth fix (ASANA_SERVICE_KEY -> SERVICE_API_KEY + TokenManager)

```yaml
commit: df33fb8
tester: qa-adversary
date: 2026-02-24
build: 95 CLI tests pass, 10928 full-suite pass
```

## Results Summary

| Phase | Category | Result |
|-------|----------|--------|
| 1 | Completeness Audit | PASS |
| 2 | Code Review: _get_live_config() | PASS (1 LOW defect) |
| 3 | Code Review: smoke scripts | PASS |
| 4 | Test Coverage Analysis | PASS |
| 5 | Test Execution | PASS (95/95 CLI, 10928/10930 suite) |
| 6 | Lint + Type Check | PASS (1 LOW defect in smoke script) |
| 7 | Edge Case Analysis | PASS |
| 8 | Security Review | PASS (2 PRE-EXISTING findings) |

---

## Phase 1: Completeness Audit -- PASS

**Objective**: Zero references to `ASANA_SERVICE_KEY` in src/, tests/, scripts/, run_smoke_test.py, docs/.

**Result**: ZERO hits across all target directories.

**Verified**:
- `src/` -- 0 hits. All 5 references are correctly `SERVICE_API_KEY`.
- `tests/` -- 0 hits.
- `scripts/smoke_test_api.py` -- 0 hits. Uses `SERVICE_API_KEY` via Config/TokenManager.
- `scripts/demo_dynamic_api.sh` -- 0 hits. All 6 refs renamed to `SERVICE_API_KEY`.
- `run_smoke_test.py` -- 0 hits. Uses `SERVICE_API_KEY` via Config/TokenManager.
- `docs/design/TDD-entity-scope-invocation.md` -- 0 hits for `ASANA_SERVICE_KEY`. Already uses `SERVICE_API_KEY`.

**Stale references in untracked files**: 9 hits in `.claude/wip/` working documents (DEPLOY_QA.md, AUTOM8_QUERY/PRD.md, AUTOM8_QUERY/TDD.md, INSIGHTS_EXPORT-SMOKETEST). These are untracked documentation artifacts written before the rename. Non-blocking.

---

## Phase 2: Code Review -- _get_live_config() -- PASS

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/query/__main__.py` lines 231-269

### Verified Behaviors

| Check | Status | Notes |
|-------|--------|-------|
| Config.from_env() ValueError -> CLIError exit_code=2 | PASS | Line 252-257 |
| TokenAcquisitionError -> CLIError exit_code=2 | PASS | Line 262-263 |
| InvalidServiceKeyError caught | PASS | Subclass of TokenAcquisitionError |
| RetryExhaustedError caught | PASS | Subclass of TokenAcquisitionError |
| Default base_url is production | PASS | `https://data.api.autom8y.io` (line 249) |
| AUTOM8_DATA_URL override respected | PASS | os.environ.get with fallback |
| manager.close() called on success | PASS | Line 261 |
| Empty SERVICE_API_KEY handled | PASS | Config.__post_init__ raises ValueError |
| Whitespace-only SERVICE_API_KEY | PASS | Config accepts it; TokenManager fails with TokenAcquisitionError, caught |
| Headers format correct | PASS | Bearer + Content-Type (lines 265-268) |

### DEF-001: TokenManager resource leak on error path (LOW)

**Severity**: LOW
**Impact**: httpx.Client not closed when get_token() raises TokenAcquisitionError.
**Reproduction**: Set SERVICE_API_KEY to an invalid key, run `python -m autom8_asana.query rows offer --live`.
**Expected**: manager.close() called in finally block.
**Actual**: manager.close() skipped on exception path.
**Risk**: Minimal. CLI process exits immediately after the error. OS reclaims all resources. The httpx.Client is lazy-initialized, so it only holds a TCP connection to the auth service. No data corruption or functional impact.
**Fix**: Wrap lines 258-263 in try/finally to ensure manager.close().

```python
manager = TokenManager(config)
try:
    token = manager.get_token()
finally:
    manager.close()
```

---

## Phase 3: Code Review -- Smoke Scripts -- PASS

### scripts/smoke_test_api.py

**File**: `/Users/tomtenuta/Code/autom8y-asana/scripts/smoke_test_api.py` lines 126-150

- `_acquire_jwt()` uses `Config(service_key=key, ...)` (direct construction, not from_env).
- Handles empty key: returns None (line 135-136).
- Handles exchange failure: catches Exception, prints message, returns None (lines 148-150).
- `manager.close()` called on success (line 145).
- Same resource leak pattern as _get_live_config on failure (minor, process exits).
- JWT length printed, not content (line 146). Safe.

### run_smoke_test.py

**File**: `/Users/tomtenuta/Code/autom8y-asana/run_smoke_test.py` lines 45-76

- `_ensure_data_api_token()` uses `Config(service_key=key, ...)` (direct construction).
- Empty key: raises RuntimeError with actionable message (line 61-64). Correct.
- `manager.close()` called on success (line 73). Same minor leak on error.
- Token length printed, not content (line 76). Safe.

### scripts/demo_dynamic_api.sh

**File**: `/Users/tomtenuta/Code/autom8y-asana/scripts/demo_dynamic_api.sh`

- All 6 `ASANA_SERVICE_KEY` references renamed to `SERVICE_API_KEY`. Verified:
  - Line 21: comment
  - Line 63: check
  - Line 64: error message
  - Line 65: example hint
  - Line 70: prefix print (first 15 chars)
  - Line 75: X-API-Key header
- Shell script uses manual curl-based JWT exchange (not TokenManager). This is acceptable -- shell scripts cannot use Python TokenManager.
- Note: Line 70 prints first 15 chars of key. Pre-existing pattern; not introduced by this commit.

---

## Phase 4: Test Coverage Analysis -- PASS

**File**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/query/test_cli.py`

### TestGetLiveConfig (5 tests)

| Test | Scenario | Verdict |
|------|----------|---------|
| test_missing_service_key_raises | SERVICE_API_KEY unset -> CLIError | PASS |
| test_returns_url_and_jwt_headers | Happy path: key set, URL override, JWT returned | PASS |
| test_default_url_is_production | AUTOM8_DATA_URL unset -> production URL | PASS |
| test_exit_code_is_2 | Missing key -> exit_code=2 | PASS |
| test_token_acquisition_error | TokenAcquisitionError -> CLIError "Auth failed" | PASS |

### TestExecuteLiveRows (4 tests)

| Test | Scenario | Verdict |
|------|----------|---------|
| test_successful_request | 200 OK -> RowsResponse | PASS |
| test_connect_error | ConnectError -> CLIError exit_code=2 | PASS |
| test_http_status_error | 503 HTTPStatusError -> CLIError exit_code=1 | PASS |
| test_timeout_error | TimeoutException -> CLIError exit_code=2 | PASS |

### TestExecuteLiveAggregate (2 tests)

| Test | Scenario | Verdict |
|------|----------|---------|
| test_successful_request | 200 OK -> AggregateResponse | PASS |
| test_connect_error | ConnectError -> CLIError | PASS |

### TestLiveCLIIntegration (3 tests)

| Test | Scenario | Verdict |
|------|----------|---------|
| test_rows_live_mode | E2E: rows offer --live --format json | PASS |
| test_aggregate_live_mode | E2E: aggregate offer --live --format json | PASS |
| test_live_without_service_key_exits_2 | E2E: --live without key exits 2, stderr mentions SERVICE_API_KEY | PASS |

### Mock Target Verification

All tests correctly patch:
- `autom8y_core.Config.from_env` -- patches at the source module, not the import site
- `autom8y_core.TokenManager` -- patches at the source module
- `autom8_asana.query.__main__._get_live_config` -- patches the function for integration tests

This is correct because `_get_live_config()` imports from `autom8y_core` directly (deferred import), so patching at the source module intercepts correctly.

### Coverage Gaps (non-blocking)

- No test for aggregate live timeout/HTTP error (only rows tested). LOW risk -- code mirrors rows path exactly.
- No test for `autom8y_core` not installed. Not needed -- it is a hard dependency in pyproject.toml.

---

## Phase 5: Test Execution -- PASS

### CLI Tests

```
95 passed in 0.74s
```

All 95 tests pass including all 14 live-mode tests.

### Full Unit Suite

```
10928 passed, 2 skipped, 1 xfailed, 543 warnings in 218.98s
```

Zero regressions from baseline (10,928 vs 10,928 expected range). 2 skipped tests are pre-existing.

---

## Phase 6: Lint + Type Check -- PASS (1 LOW defect)

### ruff

- `src/autom8_asana/query/__main__.py` -- 0 errors
- `run_smoke_test.py` -- 0 errors
- `scripts/smoke_test_api.py` -- 1 error: F401 unused import `pathlib` (line 30)

### DEF-002: Unused import in smoke_test_api.py (LOW)

**Severity**: LOW
**File**: `/Users/tomtenuta/Code/autom8y-asana/scripts/smoke_test_api.py` line 30
**Issue**: `import pathlib` is unused.
**Fix**: Remove the import.

### mypy --strict

```
Success: no issues found in 1 source file
```

`src/autom8_asana/query/__main__.py` passes mypy strict with zero errors.

---

## Phase 7: Edge Case Analysis -- PASS

| Edge Case | Behavior | Status |
|-----------|----------|--------|
| autom8y_core not installed | ModuleNotFoundError (ugly traceback) | ACCEPT -- hard dependency in pyproject.toml |
| SERVICE_API_KEY empty string | Config.__post_init__ raises ValueError -> CLIError | PASS |
| SERVICE_API_KEY whitespace-only | Config accepts; TokenManager fails -> CLIError "Auth failed" | PASS |
| SERVICE_API_KEY with trailing whitespace | Sent to auth service as-is; auth service rejects | PASS (user error) |
| Auth service down | TokenAcquisitionError (timeout/connection) -> CLIError | PASS |
| Token expires mid-session | Only relevant if --live is called twice in same process; _get_live_config() creates new TokenManager each call | ACCEPT |
| Concurrent --live calls | Not applicable -- CLI is single-threaded | N/A |
| --live on subcommands that don't support it | Only rows and aggregate have --live flag; other subcommands ignore | PASS |
| --live help text | "requires SERVICE_API_KEY" -- correct and consistent | PASS |

---

## Phase 8: Security Review -- PASS

### Current Commit

| Check | Status |
|-------|--------|
| Service key never logged or printed in __main__.py | PASS |
| JWT never logged or printed in __main__.py | PASS |
| Error messages do not leak key material | PASS -- messages say "SERVICE_API_KEY" (name), not value |
| TokenAcquisitionError messages from autom8y_core | PASS -- generic messages, no key content |
| Headers not logged before transmission | PASS |
| .env/production not tracked by git | PASS |

### PRE-EXISTING Findings (not introduced by this commit)

**SEC-PRE-001: Hardcoded production service key in tracked files (HIGH)**

Three tracked files contain production service keys:
- `docs/design/TDD-entity-scope-invocation.md` line 1131: `sk_prod_c5PNK7aViFlAulrMPB2m6XQAbmxP1JfV`
- `tmp/qa_individual_tests.py` line 12: `sk_prod_Md9G1vsXgHZxBZhEn2YABLjQcvgod5Cn`
- `tmp/qa_stability_check.py` line 10: `sk_prod_Md9G1vsXgHZxBZhEn2YABLjQcvgod5Cn`

**Recommendation**: Rotate these keys immediately. Remove the hardcoded values from tracked files. Add `tmp/` to `.gitignore`.

**SEC-PRE-002: Shell script prints first 15 chars of service key (LOW)**

`scripts/demo_dynamic_api.sh` line 70: `echo "Using key: ${SERVICE_API_KEY:0:15}..."` -- prints the key prefix to stdout. Pre-existing pattern.

---

## Defect Summary

| ID | Severity | Phase | Description | Blocking? |
|----|----------|-------|-------------|-----------|
| DEF-001 | LOW | 2 | TokenManager not closed on error path in _get_live_config() | No |
| DEF-002 | LOW | 6 | Unused `import pathlib` in smoke_test_api.py (ruff F401) | No |
| SEC-PRE-001 | HIGH | 8 | Hardcoded production service keys in tracked files (PRE-EXISTING) | No (pre-existing) |
| SEC-PRE-002 | LOW | 8 | Shell script prints key prefix (PRE-EXISTING) | No (pre-existing) |

---

## Release Recommendation

**CONDITIONAL -- APPROVE with advisory**

### GO Criteria Met

- All acceptance criteria verified: ASANA_SERVICE_KEY fully eliminated from src/tests/scripts/docs
- SERVICE_API_KEY + TokenManager correctly integrated in all 3 files
- 95/95 CLI tests pass, 10928/10930 full suite pass
- mypy --strict clean, ruff clean on main module
- No credential leakage in error messages
- No critical or high severity defects introduced by this commit

### Conditions

1. **DEF-001** (LOW): Consider adding try/finally around TokenManager in `_get_live_config()`. Non-blocking -- CLI exits immediately after error.
2. **DEF-002** (LOW): Remove unused `import pathlib` from `scripts/smoke_test_api.py`. Trivial fix.

### Advisory (pre-existing, not blocking this commit)

3. **SEC-PRE-001** (HIGH): Rotate production service keys exposed in `docs/design/TDD-entity-scope-invocation.md`, `tmp/qa_individual_tests.py`, `tmp/qa_stability_check.py`. These are tracked by git and contain real `sk_prod_*` keys.
4. **SEC-PRE-002** (LOW): Review key prefix printing in `demo_dynamic_api.sh`.
5. Stale `ASANA_SERVICE_KEY` references remain in 9 untracked `.claude/wip/` documentation files. No functional impact.

---

## Not Tested

- Live integration against production auth service (requires real SERVICE_API_KEY; covered by existing smoke_test_api.py in deploy pipeline)
- `autom8y_core` package absence (hard dependency, not a realistic scenario)
- Network partition / DNS failure during TokenManager exchange (covered by autom8y_core internal tests)
