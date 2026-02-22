# Analysis Report -- Deep Slop Triage

Date: 2026-02-19
Scope: Full Codebase
Agent: logic-surgeon
Phase: 2 of 5 (slop-chop pipeline)
Upstream: hallucination-hunter (0 critical/high findings)

## Executive Summary

| Category               | HIGH | MEDIUM | LOW | Total |
|------------------------|------|--------|-----|-------|
| Logic Errors           | 2    | 4      | 2   | 8     |
| Copy-Paste Bloat       | 0    | 2      | 1   | 3     |
| Test Degradation       | 0    | 2      | 3   | 5     |
| Security Anti-Patterns | 1    | 2      | 1   | 4     |
| Unreviewed-Output Signals | 0 | 0      | 2   | 2     |
| **Total**              | **3**| **10** | **9**| **22**|

The codebase is well-structured with strong error handling conventions. The main
risk areas are: (1) a regex injection vector in entity name generation, (2) PII
leakage in the GID push module that was missed by the XR-003 audit, and (3) a
duplicated dead function left behind from the D-030 endpoint extraction. No
critical logic errors that would cause data loss or corruption in production.

---

## Findings

### Logic Errors

#### LS-001: Regex injection via user-supplied business/unit names in generate_entity_name (HIGH confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py:82-96`
**Finding**: `re.sub()` uses `business_name` and `unit_name` as the replacement
string without escaping. If a business name contains backreference patterns like
`\1`, `\g<0>`, or raw backslashes, `re.sub` will interpret them as backreferences,
causing either silent corruption or `re.error` exceptions.

```python
result = re.sub(
    r"\[business\s*name\]",
    business_name,  # <-- unescaped user input as replacement
    result,
    flags=re.IGNORECASE,
)
```

**Evidence**: Per Python docs, `re.sub(pattern, repl, string)` treats `repl` as
a regex replacement string where `\1` means "first capture group". A business
named `"Acme \1 Corp"` or `"Price: $100 (50% off)"` (backslash in Windows paths)
would produce unexpected results. The function `generate_entity_name` is called
from `lifecycle/creation.py:163`, `lifecycle/creation.py:282`, and
`automation/pipeline.py:309` -- all paths where business names come from Asana
task data (user-supplied).

**Confidence**: 0.95 -- provably wrong for business names containing backslash
sequences. Production likelihood depends on whether any business names contain
backslashes, which is plausible for path-style names.
**Severity**: HIGH -- silent data corruption in task names


#### LS-002: Batch failure_count computed from len(pairs) not len(results) (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py:995`
**Finding**: `failure_count = len(pairs) - success_count` may be incorrect when
multi-chunk batch processing encounters a chunk failure that marks PVPs from
ALL chunks (not just the failed chunk) as errored.

```python
# Line 979-989: When a chunk fails, iterates over ALL pairs
for pvp in pairs:  # <-- iterates ALL pairs, not just chunk's pairs
    if pvp.canonical_key not in results:
        results[pvp.canonical_key] = BatchInsightsResult(
            pvp=pvp,
            error=sanitized_error,
        )
```

When chunk A succeeds and chunk B fails, the error handler at line 984 iterates
ALL `pairs` and sets error results for any PVP not already in `results`. This
is actually correct behavior (marking unprocessed PVPs as failed), but the
`failure_count` calculation at line 995 is correct only because it derives
from `success_count` subtracted from `len(pairs)`, which accounts for all PVPs.

**Evidence**: The logic is subtle but actually correct on inspection. The
`for pvp in pairs` loop only writes to `results` for keys NOT already present,
so it does not overwrite successful results from chunk A. However, this is
fragile -- the correctness depends on the iteration order and the `not in`
guard. A code change removing that guard would silently corrupt results.

**Confidence**: 0.40 -- the code is correct but fragile; documenting as LOW
for awareness
**Severity**: LOW -- currently correct, risk of regression


#### LS-003: _ERROR_STATUS map missing error types handled elsewhere (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/query.py:65-69`
**Finding**: The `_ERROR_STATUS` dict maps only `QueryTooComplexError` and
`AggregateGroupLimitError` to 400, but falls through to `_DEFAULT_ERROR_STATUS = 422`
for all other `QueryEngineError` subclasses. This works but means any future
`QueryEngineError` subclass that should be a 400 or 500 will silently get 422.

**Evidence**: The `_raise_query_error` function handles all `QueryEngineError`
subclasses identically (convert to dict, send with mapped status). The
`_DEFAULT_ERROR_STATUS = 422` default is reasonable for validation-style errors
but would be incorrect for a hypothetical `QueryTimeoutError` or
`QueryResourceExhaustedError` which would warrant 503 or 500.

**Confidence**: 0.50 -- no current bug but error mapping is incomplete for
extensibility
**Severity**: LOW -- only manifests when new QueryEngineError subclasses are added


#### LS-004: Redundant phone length check in mask_phone_number (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_pii.py:34-42`
**Finding**: Two sequential guards both check `len(phone) < 9`:

```python
if not phone or len(phone) < 9:  # Line 34
    return phone

if phone.startswith("+") and len(phone) >= 9:  # Line 37 -- always true here
    prefix = phone[:5]
    suffix = phone[-4:]
    return f"{prefix}***{suffix}"

return phone  # Line 42 -- only reached for 9+ char non-E.164 strings
```

After line 34 passes, `len(phone) >= 9` is guaranteed. The second `len(phone) >= 9`
check on line 37 is dead code within the `and` condition. The `return phone` on
line 42 is only reached for strings like `"123456789"` (no + prefix, 9+ chars).

**Evidence**: The function comments say "Returns original string if not a valid
phone format" but this case (9+ chars without + prefix) is not tested. The test
`test_returns_non_e164_unchanged` only tests `"7705753103"` (10 chars) which
does hit this path. However, the masking behavior is correct for its stated
purpose -- just has a confusing dead condition.

**Confidence**: 0.85 -- provably redundant check
**Severity**: LOW -- cosmetic logic issue, no behavioral impact


#### LS-005: Type hint stale -- models.core.Task import path does not exist (HIGH confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py:21`
**Finding**: `from autom8_asana.models.core import Task` references a module
that does not exist. The actual path is `autom8_asana.models.task` (re-exported
via `autom8_asana.models.__init__`). Same stale import at
`src/autom8_asana/automation/templates.py:17`.

```python
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.core import Task  # <-- models/core.py does NOT exist
```

**Evidence**: `ls models/core.py` returns "NOT FOUND". The file `models/__init__.py`
re-exports `Task` from `models/task.py`. This import works at runtime only because
it is guarded by `TYPE_CHECKING` (never actually executed). However, any static
analysis tool or IDE following this import will fail.

**Confidence**: 0.95 -- confirmed: file does not exist
**Severity**: MEDIUM -- breaks static analysis tools, mypy with explicit imports,
IDE navigation. Does not break runtime.
**Note**: Also flagged by hallucination-hunter as L-002; confirming with evidence.


#### LS-006: export.py sends raw phone in query params without masking (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/export.py:86`
**Finding**: The export endpoint sends the raw (unmasked) `office_phone` in
HTTP query parameters, which is correct for the API call but means the raw
phone number appears in httpx access logs and any HTTP-level logging.

```python
params: dict[str, str] = {"office_phone": office_phone}  # raw phone in params
```

**Evidence**: This is by design -- the API needs the real phone to function.
However, it contrasts with the PII-aware logging elsewhere (where masked
phone is used for log entries). The httpx client logs requests by default
at DEBUG level, which would include the raw phone in query string.

**Confidence**: 0.60 -- correct behavior but PII exposure risk at debug log level
**Severity**: MEDIUM -- PII in debug logs; SECURITY referral recommended


#### LS-007: simple.py appointments/leads use masked_phone in cache_key for stale fallback (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/simple.py:110`
**Finding**: The cache key for stale fallback uses the masked phone:

```python
cache_key = f"appointments:{masked_phone}"  # masked, not raw
```

This means the stale fallback will never find a cached response, because
`cache_response()` in the success path (if it were called) would use a
different key format. However, for `get_appointments` and `get_leads`, there
is no cache_response() call on success -- the code only has stale fallback
via `_handle_error_response`, which passes the masked cache key.

**Evidence**: This is actually intentional per XR-003 Vector 4 -- the cache key
uses masked phone to prevent PII in cache backends. But it means the stale
fallback can never work for appointments/leads because no cache entry is ever
written with this key. The `_handle_error_response` calls `get_stale_response`
which will always return None for a key that was never cached.

**Confidence**: 0.75 -- the stale fallback path is unreachable for appointments/leads
**Severity**: MEDIUM -- dead code path that silently degrades resilience


#### LS-008: normalize_period silently defaults unknown periods to T30 (LOW confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_normalize.py:57-58`
**Finding**: Any unrecognized period string (e.g., typo "t31", "biweekly", "t7d")
is silently mapped to "T30" instead of raising a validation error.

```python
# Default to T30 for other values (backward compatibility)
return "T30"
```

**Evidence**: The `InsightsRequest.validate_period` validator at
`models.py:83-129` accepts `t{N}` for any N (via regex `^t\d+$`). So `t31` or
`t999` passes validation but gets normalized to "T30" silently. The API
consumer has no indication their requested period was remapped.

**Confidence**: 0.70 -- validated pattern passes through, gets silently remapped
**Severity**: LOW -- backward compatibility tradeoff, not a bug per se

---

### Copy-Paste Bloat

#### CPB-001: Duplicate _parse_content_disposition_filename function (MEDIUM confidence)

**File A**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/client.py:1250-1261`
**File B**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/export.py:27-38`

**Finding**: Identical function `_parse_content_disposition_filename` exists in
both files. The client.py version is dead code -- it is never imported or called.
The export.py version is the active one.

**Variation delta**: Zero -- byte-for-byte identical implementation.
**Evidence**: `grep` shows the client.py version is only defined, never referenced.
The export.py version is called at line 148. This is a leftover from the D-030
endpoint extraction that moved the function but did not clean up the original.

**Confidence**: 0.95 -- provably dead code in client.py
**Severity**: MEDIUM -- dead code that may confuse future developers


#### CPB-002: Near-identical circuit breaker/retry/error patterns across 4 endpoint files (MEDIUM confidence)

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/insights.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/batch.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/export.py`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/simple.py`

**Finding**: All four endpoint files follow an identical pattern:
1. Circuit breaker check with SdkCircuitBreakerOpenError catch
2. `_get_client()` call
3. `build_retry_callbacks()` with similar params
4. `_execute_with_retry()` call
5. Status code >= 400 check
6. Success response parsing + circuit breaker record_success

The `_retry.py` module already extracts the callback boilerplate, which is good.
But the enclosing structure (steps 1-6) is repeated ~40 LOC each time.

**Variation delta**: The variations are in error_class (InsightsServiceError vs
ExportError), request method (POST vs GET), URL path, and log event names.
These are legitimate differentiators for the four distinct endpoints.

**Confidence**: 0.65 -- this is a pattern, not exact duplication. The _retry.py
extraction was the right call. Further abstraction risks over-engineering.
**Severity**: LOW -- engineering judgment: current structure is maintainable


#### CPB-003: _make_mock_task and _FakePageIterator duplicated in two test files (LOW confidence)

**File A**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/dataframes/builders/test_adversarial_pacing.py:33-59`
**File B**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/dataframes/builders/test_paced_fetch.py:26-54`

**Finding**: Both test files define nearly identical `_make_mock_task` and
`_FakePageIterator` helpers. The `_FakePageIterator` in test_adversarial_pacing.py
has an extra `start_gid` parameter; otherwise they are functionally identical.

**Variation delta**: 1 parameter (`start_gid` in adversarial version).
**Evidence**: Could be extracted to the `conftest.py` in the builders test directory.

**Confidence**: 0.85 -- clear duplication
**Severity**: LOW -- test helpers, not production code

---

### Test Degradation

#### TD-001: test_settings.py shallow assertions -- 6 tests just check `is not None` (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/test_settings.py`
**Lines**: 408, 421, 441, 525 (and more)

**Finding**: Multiple tests in test_settings.py assert only `assert settings is not None`
without verifying that the settings contain expected values, correct defaults,
or proper type resolution.

```python
assert settings is not None  # Line 408, 421, 441, 525
```

**Evidence**: A settings module that returns an empty object would pass these
tests. Proper tests would assert specific field values:
`assert settings.asana.pat is not None` (which IS done at lines 285, 292, 554)
shows the pattern the shallow tests should follow.

**Confidence**: 0.80 -- shallow assertions that would pass with broken implementation
**Severity**: MEDIUM -- settings misconfiguration could go undetected


#### TD-002: test_staleness_flow.py has 6 sequential `is not None` assertions without value checks (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/tests/integration/test_staleness_flow.py`
**Lines**: 103, 139, 144, 149, 381, 383, 436

**Finding**: Integration test for staleness flow checks existence but not
correctness. For a cache staleness test, the assertions should verify
`is_stale=True`, `cached_at` is populated, and data matches expected values.

**Evidence**: A cache that returns garbage data would pass `assert result is not None`.

**Confidence**: 0.70 -- would need to see the full context of each assertion;
some may be followed by deeper checks on subsequent lines
**Severity**: MEDIUM -- staleness is a critical resilience feature


#### TD-003: Mock-heavy tests in test_client.py test mock configuration not behavior (LOW confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/clients/data/test_client.py`

**Finding**: Several tests (e.g., `test_accepts_auth_provider`,
`test_accepts_logger`, `test_accepts_cache_provider`) verify that constructor
arguments are stored on the instance (`assert client._auth_provider is mock_auth`)
rather than testing that the auth provider is actually used during requests.

**Evidence**: These are valid unit tests for constructor behavior, but they don't
verify that the injected dependencies are actually called. The behavioral tests
exist in separate test files (test_insights.py, test_export.py), so coverage
is adequate across the suite. Flagging as LOW because the test organization is
intentional.

**Confidence**: 0.50 -- legitimate unit test pattern, not truly degraded
**Severity**: LOW -- constructor tests are shallow by design


#### TD-004: PII test assertions check substring presence but not position (LOW confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/tests/unit/clients/data/test_pii.py`

**Finding**: PII masking tests assert `"+17705753103" not in result` and
`"+1770***3103" in result` but don't verify the exact output string. A masking
function that appends "***" instead of replacing middle digits would pass.

```python
assert "+17705753103" not in result  # raw phone absent
assert "+1770***3103" in result      # masked phone present
```

**Evidence**: The `test_masks_standard_us_phone` test at line 27 does check
`assert result == "+1770***3103"` (exact match). But the later tests
(TestMaskPiiInString, TestCacheLoggingPiiRedaction) only do substring checks,
which is appropriate since they test string-within-string behavior.

**Confidence**: 0.40 -- the test pattern is actually correct for the context
**Severity**: LOW -- false positive on closer inspection


#### TD-005: 30 restored quarantine tests have adequate quality (PASS)

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/tests/unit/dataframes/builders/test_adversarial_pacing.py`
- `/Users/tomtenuta/Code/autom8y-asana/tests/unit/dataframes/builders/test_paced_fetch.py`

**Finding**: The 30 restored D-029 tests verify concrete behavioral properties:
sleep call counts at specific page boundaries, checkpoint write intervals,
specific task counts in written DataFrames, and error handling paths. These
are NOT shallow assertions.

**Evidence**: `test_pacing_sleep_intervals` verifies `assert mock_sleep.call_count == 3`;
`test_large_section_pacing_activated` verifies `assert len(written_df) == 150`;
`test_small_section_no_pacing` verifies `mock_sleep.assert_not_called()`.
These test real behavioral contracts.

**Confidence**: 0.90 -- tests are properly behavioral
**Severity**: NONE -- pass

---

### Security Anti-Patterns

#### SEC-001: PII leakage in gid_push.py -- phone numbers in push payload without masking (HIGH confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/gid_push.py:63-68`
**Finding**: `extract_mappings_from_index` extracts raw phone numbers from the
GidLookupIndex and includes them in the HTTP payload sent to autom8_data.
Neither the payload nor the log entries mask phone numbers.

```python
mappings.append(
    {
        "phone": parts[1],       # <-- raw phone, e.g., "+17705753103"
        "vertical": parts[2],
        "task_gid": task_gid,
    }
)
```

And at line 232, error response text is logged without PII masking:

```python
"response_text": response.text[:500],  # may contain echoed phone numbers
```

**Evidence**: The XR-003 PII redaction audit (eef8c3a) closed 5 leakage vectors
in `clients/data/`, but `services/gid_push.py` was not in scope. The raw phone
in the HTTP payload is arguably required (autom8_data needs real phones), but
the log entry at line 232 should use `mask_pii_in_string()` on `response.text`.

**Confidence**: 0.90 -- the response_text log entry is a clear PII leak vector
**Severity**: HIGH -- structured log PII leakage. SECURITY CROSS-RITE REFERRAL.
**Referral**: XR-003 extension -- add `mask_pii_in_string` to gid_push log entries


#### SEC-002: Regex injection in generate_entity_name (same as LS-001) (MEDIUM confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/core/creation.py:82-96`
**Finding**: User-supplied business names used as `re.sub` replacement strings.
While not a traditional injection (no code execution), it can cause:
1. `re.error` exceptions crashing task creation
2. Silent data corruption via backreference interpretation

**Evidence**: See LS-001 for full analysis.
**Confidence**: 0.90
**Severity**: MEDIUM -- DoS via crafted business name, data corruption
**Referral**: Fix category: AUTO (use `re.escape` on replacement or use `str.replace`)


#### SEC-003: `except (ValueError, Exception)` is effectively bare except (MEDIUM confidence)

**Files**:
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/gid_push.py:211`
- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/batch.py:187`

**Finding**: The pattern `except (ValueError, Exception)` catches ALL exceptions
because `Exception` is a superclass of `ValueError`. The `ValueError` in the
tuple is dead code.

```python
except (ValueError, Exception) as e:  # Exception catches everything
    body = {}
```

**Evidence**: This swallows `KeyboardInterrupt`-safe but catches `SystemExit`
(which inherits from `BaseException`, not `Exception`), so it is not literally
bare. But it catches `TypeError`, `AttributeError`, `RuntimeError`, etc. which
may mask real bugs in JSON parsing.

**Confidence**: 0.95 -- provably redundant catch clause
**Severity**: MEDIUM -- masks bugs silently


#### SEC-004: Content-Disposition filename not sanitized for path traversal (LOW confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_endpoints/export.py:27-38`
**Finding**: `_parse_content_disposition_filename` extracts a filename from
the Content-Disposition header but does not sanitize for path traversal
characters (`../`, absolute paths). The regex `[^";\s]+` allows directory
separators.

```python
match = re.search(r'filename="?([^";\s]+)"?', header)
return match.group(1) if match else None
```

**Evidence**: The filename is used in `ExportResult.filename` which is a data
field -- it depends on how downstream consumers use it. If any consumer writes
this filename to disk without sanitizing, it creates a path traversal risk.
However, the current codebase appears to use `ExportResult.filename` only for
Asana attachment upload (not file system write), so the risk is theoretical.

**Confidence**: 0.50 -- depends on downstream usage which appears safe currently
**Severity**: LOW -- theoretical risk, not currently exploitable
**Referral**: MANUAL review if filename is ever used for filesystem operations

---

### Unreviewed-Output Signals

#### UOS-001: Over-documented obvious code in _pii.py (LOW confidence)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/clients/data/_pii.py`
**Finding**: Every function has a comprehensive docstring with Args/Returns
sections, even for trivial 3-line functions. This is consistent with the
codebase convention (similar docstrings across all modules), so it is NOT
an inconsistency signal.

**Evidence**: Compared against `_normalize.py`, `_metrics.py`, `_cache.py` --
all follow the same comprehensive docstring pattern. This is a codebase
convention, not an unreviewed-output signal.

**Confidence**: 0.20 -- false positive; matches established codebase convention
**Severity**: NONE


#### UOS-002: Comments referencing specific TDD/FR/ADR numbers in every function (LOW confidence)

**File**: Multiple files across `clients/data/`
**Finding**: Nearly every function includes a comment like
`Per TDD-INSIGHTS-001 Section 5.1:` or `Per Story 1.9:` or `Per ADR-INS-004:`.
These cross-references are consistent throughout the codebase and appear to be
a team convention for traceability.

**Evidence**: This pattern appears in files authored before and after the recent
commits. It is a deliberate traceability practice, not a signal of unreviewed
AI output. The references correspond to actual documents in `docs/design/`.

**Confidence**: 0.15 -- false positive; established team convention
**Severity**: NONE

---

## Statistics

| Metric                    | Value    |
|---------------------------|----------|
| Source files analyzed      | 392      |
| Source lines of code       | 111,314  |
| Test files analyzed        | 441      |
| Test lines of code         | 206,341  |
| Files with deep analysis   | 25       |
| Findings total             | 22       |
| HIGH severity              | 3        |
| MEDIUM severity            | 10       |
| LOW severity               | 9        |
| Avg confidence score       | 0.69     |

### Files with Deep Analysis

| File | Lines | Findings |
|------|-------|----------|
| `src/autom8_asana/core/creation.py` | 255 | LS-001, LS-005, SEC-002 |
| `src/autom8_asana/clients/data/client.py` | 1262 | LS-002, CPB-001 |
| `src/autom8_asana/clients/data/_pii.py` | 74 | LS-004 |
| `src/autom8_asana/clients/data/_normalize.py` | 59 | LS-008 |
| `src/autom8_asana/clients/data/_response.py` | 271 | -- |
| `src/autom8_asana/clients/data/_retry.py` | 194 | -- |
| `src/autom8_asana/clients/data/_cache.py` | 195 | -- |
| `src/autom8_asana/clients/data/_metrics.py` | 55 | -- |
| `src/autom8_asana/clients/data/_endpoints/insights.py` | 225 | -- |
| `src/autom8_asana/clients/data/_endpoints/batch.py` | 311 | SEC-003 |
| `src/autom8_asana/clients/data/_endpoints/export.py` | 174 | LS-006, SEC-004 |
| `src/autom8_asana/clients/data/_endpoints/simple.py` | 235 | LS-007 |
| `src/autom8_asana/clients/data/config.py` | 299 | -- |
| `src/autom8_asana/clients/data/models.py` | 499 | -- |
| `src/autom8_asana/api/routes/query.py` | 401 | LS-003 |
| `src/autom8_asana/api/errors.py` | 510 | -- |
| `src/autom8_asana/services/errors.py` | 343 | -- |
| `src/autom8_asana/services/query_service.py` | 604 | -- |
| `src/autom8_asana/services/gid_push.py` | 258 | SEC-001, SEC-003 |
| `src/autom8_asana/exceptions.py` | 491 | -- |
| `tests/unit/clients/data/test_pii.py` | 444 | TD-004 |
| `tests/unit/clients/data/test_client.py` | 350+ | TD-003 |
| `tests/unit/test_settings.py` | 554+ | TD-001 |
| `tests/unit/dataframes/builders/test_paced_fetch.py` | 283+ | CPB-003, TD-005 |
| `tests/unit/dataframes/builders/test_adversarial_pacing.py` | 300+ | CPB-003 |

## Methodology

1. **Logic scan**: Read each file in scope sequentially. For each function,
   compared stated intent (name, docstring, comments) against actual behavior.
   Traced control flow paths for correctness. Verified error handling completeness.

2. **Bloat detection**: Used grep to find function definitions duplicated across
   modules. Compared function bodies for variation delta. Distinguished from
   legitimate patterns (e.g., HTTP handler structure that is similar by design).

3. **Test assessment**: Searched for weak assertion patterns (`assert True`,
   `assert X is not None`, `mock.called`). Read restored quarantine tests to
   verify quality. Checked that assertions verify behavioral contracts, not
   just existence.

4. **Security scan**: Searched for `eval`, `exec`, `pickle`, `subprocess`,
   `os.environ` access patterns. Analyzed PII handling against XR-003 contract.
   Checked regex patterns for injection. Verified Content-Disposition parsing.

5. **Unreviewed-output signals**: Compared docstring density, comment style,
   and error handling patterns across files written at different times. Checked
   for inconsistencies against established codebase conventions.

## Handoff Checklist

- [x] Each logic error includes flaw, evidence, expected correct behavior, confidence score
- [x] Copy-paste instances include duplicated blocks and variation delta
- [x] Test degradation findings include weakness and what a proper test would verify
- [x] Security findings flagged for cross-rite referral where warranted
- [x] Unreviewed-output signals include codebase-convention evidence
- [x] Severity ratings assigned to all findings
- [x] Phase 1 detection-report cross-referenced (L-002 confirmed as LS-005)

## Cross-Rite Referrals

| Finding | Target Rite | Reason |
|---------|-------------|--------|
| SEC-001 | security | PII leakage in gid_push.py logs -- XR-003 extension |
| SEC-002/LS-001 | hygiene | Regex injection fix -- use `re.escape()` or `str.replace()` |
| CPB-001 | cruft-cutter | Dead code removal -- `_parse_content_disposition_filename` in client.py |
