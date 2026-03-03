---
type: audit
---
# SLOP-CHOP-DEEP Remedy Plan

**Phase**: 4 — Remediation
**Specialist**: remedy-smith
**Date**: 2026-02-25
**Scope**: `src/autom8_asana/` + `tests/` + `src/autom8_query_cli.py`
**Initiative Context**: Post ASANA-HYGIENE + REM-ASANA-ARCH + REM-HYGIENE + COMPAT-PURGE
**Note**: Written to `.wip/REMEDY-PLAN-slop-chop-deep.md` — agent-guard restricts remedy-smith writes to `.wip/`.

---

## Executive Summary

| Category | Count |
|----------|-------|
| AUTO workstreams | 3 (WS-DEPS, WS-TEMPORAL, WS-TEST-QUALITY) |
| MANUAL workstreams | 4 (WS-METRICS, WS-QUERY, WS-HEALTH-MOCK, deferred D-015) |
| Total findings remediated | 19 (HH-DEEP-001..002, LS-DEEP-001..010, CC-DEEP-001..006, carry-forward referrals) |
| Blocking workstreams | 2 (WS-DEPS, WS-HEALTH-MOCK) |
| Advisory workstreams | 5 |
| Deferred items | 2 (RS-021/LS-DEEP-005, D-015/LS-DEEP-006) |
| Cross-rite referrals | 2 (security, hygiene) |

**Total effort estimate**: ~3–5 days across all MANUAL workstreams. AUTO workstreams are trivial to small.

**Prioritized execution order**:
1. WS-DEPS (AUTO, trivial) — unblocks clean-environment testing
2. WS-TEMPORAL (AUTO, small) — pure removal, zero risk
3. WS-TEST-QUALITY (AUTO, small) — tightens exception contracts
4. WS-HEALTH-MOCK (MANUAL, small) — HIGH-severity mock correctness
5. WS-METRICS (MANUAL, small) — HIGH-severity output correctness
6. WS-QUERY (MANUAL, medium) — advisory, improves robustness

---

## Workstream: WS-DEPS — Declare PyYAML Production Dependency

**Classification**: AUTO
**Source finding**: HH-DEEP-002
**Blocking**: YES (MEDIUM severity with production import-failure impact)
**Effort**: trivial (5 minutes)

### File-Scope Contract

| File | Operation | Scope |
|------|-----------|-------|
| `pyproject.toml` | INSERT one line into `[project.dependencies]` | After the `boto3` line (currently line 27) |

### Patch Instructions

In `pyproject.toml`, insert `"pyyaml>=6.0.0",` into the `[project.dependencies]` list. The current last dependency entry is:

```toml
    "boto3>=1.42.19",                    # S3 for progressive cache warming (asyncio.to_thread)
```

Insert after this line:

```toml
    "boto3>=1.42.19",                    # S3 for progressive cache warming (asyncio.to_thread)
    "pyyaml>=6.0.0",                     # YAML config parsing (lifecycle, automation, query/saved)
```

After editing, run:

```bash
uv lock
```

to regenerate `uv.lock` with PyYAML as a declared direct production dependency. Verify `uv lock` shows `pyyaml` under the `autom8y-asana` package's direct dependencies rather than only under `moto`.

**Classification rationale**: AUTO — single-line manifest addition, zero behavioral change, no ambiguity about the correct package name or version. PyYAML 6.x is the current stable series; `pyyaml 6.0.3` is already resolved in the lockfile as a transitive dep from `moto`, confirming compatibility.

---

## Workstream: WS-TEMPORAL — Remove Initiative Tags and Dead Freshness Aliases

**Classification**: AUTO
**Source findings**: CC-DEEP-001, CC-DEEP-002, CC-DEEP-003, CC-DEEP-004, CC-DEEP-005, CC-DEEP-006
**Blocking**: NO (TEMPORAL severity — advisory)
**Effort**: small (1–2 hours including verification)

This workstream batches all 6 temporal debt findings. All are pure deletions: comment line removals or alias definition + re-export removals. No logic changes, no behavioral changes.

### File-Scope Contract

| File | Operation | Scope |
|------|-----------|-------|
| `src/autom8_asana/services/dataframe_service.py` | DELETE comment lines | Lines 325–326 and 387–388 (`Per R-006 (REM-ASANA-ARCH WS-DFEX):` lines in docstrings) |
| `src/autom8_asana/persistence/holder_construction.py` | DELETE comment lines | Lines 21–22 (module docstring `Per R-009 ...` block) |
| `src/autom8_asana/core/registry.py` | DELETE comment lines | Lines 6–7 (module docstring `Per R-009 ...` block) |
| `tests/unit/dataframes/test_public_api.py` | DELETE comment line | Line 3 (`Per TDD-0009 Phase 5 / R-006 (REM-ASANA-ARCH WS-DFEX):`) |
| `tests/unit/persistence/test_holder_construction.py` | DELETE comment lines | Lines 71–72 (class docstring `Per R-009 ...` block) |
| `src/autom8_asana/models/business/detection/__init__.py` | DELETE comment line | Line 3 |
| `src/autom8_asana/models/business/detection/tier1.py` | DELETE comment line | Line 3 |
| `src/autom8_asana/models/business/detection/tier2.py` | DELETE comment line | Line 3 |
| `src/autom8_asana/models/business/detection/tier3.py` | DELETE comment line | Line 3 |
| `src/autom8_asana/models/business/detection/tier4.py` | DELETE comment line | Line 3 |
| `src/autom8_asana/models/business/detection/types.py` | DELETE comment line | Line 3 |
| `src/autom8_asana/models/business/detection/config.py` | DELETE comment line | Line 3 |
| `src/autom8_asana/models/business/detection/facade.py` | DELETE comment line | Line 3 only (`Per TDD-SPRINT-3-DETECTION-DECOMPOSITION:` — keep line 4, the `Per PRD-CACHE-PERF-DETECTION:` reference is a live PRD citation) |
| `src/autom8_asana/cache/models/freshness_stamp.py` | DELETE 2 lines | Lines 20–21 (alias comment + `FreshnessClassification = FreshnessState`) |
| `src/autom8_asana/cache/models/__init__.py` | DELETE one import entry | Remove `FreshnessClassification,` from the `freshness_stamp` import block (line 48) |
| `src/autom8_asana/cache/integration/dataframe_cache.py` | DELETE 2 lines | Lines 18–19 (alias comment + `FreshnessStatus = FreshnessState`) |
| `src/autom8_asana/cache/integration/freshness_coordinator.py` | DELETE 2 lines | Lines 20–21 (alias comment + `FreshnessMode = FreshnessIntent`) |
| `src/autom8_asana/cache/integration/__init__.py` | DELETE import line + `__all__` entry | Line 13 (import) and `"FreshnessMode",` from `__all__` (line 26) |
| `src/autom8_asana/cache/__init__.py` | DELETE import line + `__all__` entry | Line 107 (import) and `"FreshnessMode",` from `__all__` (line 269) |
| `tests/unit/services/test_gid_push.py` | DELETE 2 comment lines | Lines 3–4 (`Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: ...`) |
| `tests/unit/lambda_handlers/test_cache_warmer_gid_push.py` | DELETE 3 comment lines | Lines 3–5 (`Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: ...` — 3-line sentence) |

### Patch Instructions

**CC-DEEP-001 — REM-ASANA-ARCH WS-DFEX tags**

`src/autom8_asana/services/dataframe_service.py` — Delete lines 325–326 (within the `build_for_project` docstring):
```
Per R-006 (REM-ASANA-ARCH WS-DFEX): Service function replacing model
convenience methods.
```
Repeat for lines 387–388 (within the `build_for_section` docstring). Keep all surrounding docstring content.

`src/autom8_asana/persistence/holder_construction.py` — Delete lines 21–22 from the module docstring:
```
Per R-009 (REM-ASANA-ARCH WS-DFEX): Each Holder module self-registers via
register_holder() at module level, following the register_reset() pattern.
```

`src/autom8_asana/core/registry.py` — Delete lines 6–7 from the module docstring (identical pattern).

`tests/unit/dataframes/test_public_api.py` — Delete line 3:
```
Per TDD-0009 Phase 5 / R-006 (REM-ASANA-ARCH WS-DFEX):
```
Keep the next line (`Validates the service functions...`) and the bullet list.

`tests/unit/persistence/test_holder_construction.py` — Delete lines 71–72 from the `TestHolderRegistryCompleteness` class docstring:
```
    Per R-009 (REM-ASANA-ARCH WS-DFEX): Completeness gate ensuring no Holder
    class is missing from the registry when EntityRegistry adds a new one.
```

**CC-DEEP-002 — TDD-SPRINT-3-DETECTION-DECOMPOSITION tags**

For each of the 8 detection package files, delete line 3 which is the `Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: ...` line. All other docstring content remains.

Special case for `facade.py`: line 3 is `Per TDD-SPRINT-3-DETECTION-DECOMPOSITION: Central orchestration for tiered detection.` — delete this line only. Line 4 (`Per PRD-CACHE-PERF-DETECTION: Caches Tier 4 detection results for performance.`) is a live PRD reference, keep it.

**CC-DEEP-003 — Remove `FreshnessClassification` alias**

`src/autom8_asana/cache/models/freshness_stamp.py` — Delete lines 20–21:
```python
# Backward-compatible alias. New code should use FreshnessState directly.
FreshnessClassification = FreshnessState
```

`src/autom8_asana/cache/models/__init__.py` — The import block at lines 47–51 currently reads:
```python
from autom8_asana.cache.models.freshness_stamp import (
    FreshnessClassification,
    FreshnessStamp,
    VerificationSource,
)
```
Remove the `    FreshnessClassification,` line. Result:
```python
from autom8_asana.cache.models.freshness_stamp import (
    FreshnessStamp,
    VerificationSource,
)
```

**CC-DEEP-004 — Remove `FreshnessStatus` alias**

`src/autom8_asana/cache/integration/dataframe_cache.py` — Delete lines 18–19:
```python
# Backward-compatible alias. New code should use FreshnessState directly.
FreshnessStatus = FreshnessState
```

**CC-DEEP-005 — Remove `FreshnessMode` alias (3 files)**

Interview resolution: REMOVE — zero callers confirmed, superseded by `FreshnessIntent`.

`src/autom8_asana/cache/integration/freshness_coordinator.py` — Delete lines 20–21:
```python
# Backward-compatible alias. New code should use FreshnessIntent directly.
FreshnessMode = FreshnessIntent
```

`src/autom8_asana/cache/integration/__init__.py` — Delete line 13:
```python
from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode
```
And remove `"FreshnessMode",` from `__all__` (line 26). Keep `"FreshnessIntent"` in `__all__`.

`src/autom8_asana/cache/__init__.py` — Delete line 107:
```python
from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode
```
And remove `"FreshnessMode",` from `__all__` (line 269).

**CC-DEEP-006 — Remove SPIKE-BREAK-CIRCULAR-DEP tags**

`tests/unit/services/test_gid_push.py` — Delete lines 3–4 from the module docstring:
```
Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: Tests for the push function that
sends GID mappings to autom8_data after cache warmer rebuilds.
```

`tests/unit/lambda_handlers/test_cache_warmer_gid_push.py` — Delete lines 3–5 from the module docstring (3-line sentence):
```
Per SPIKE-BREAK-CIRCULAR-DEP Phase 3: Tests that the cache warmer
calls the GID push function after successfully warming entities, and
that push failures do not affect the warmer's success status.
```

### Verification Steps

After applying all WS-TEMPORAL changes:
1. `grep -r "REM-ASANA-ARCH WS-DFEX" src/ tests/` — expect 0 matches
2. `grep -r "TDD-SPRINT-3-DETECTION-DECOMPOSITION" src/ tests/` — expect 0 matches
3. `grep -r "SPIKE-BREAK-CIRCULAR-DEP" src/ tests/` — expect 0 matches
4. `grep -r "FreshnessClassification\|FreshnessStatus\|FreshnessMode" src/ tests/` — expect 0 import-site matches (the `TestFreshnessMode` class name in `test_freshness_coordinator.py` is a test class name, not an import — it is not a finding)
5. `pytest tests/unit/cache/ -x -q` — all cache unit tests must pass
6. `python -c "from autom8_asana.cache import FreshnessIntent, FreshnessState; print('OK')"` — must succeed
7. `python -c "from autom8_asana.cache import FreshnessMode"` — must raise `ImportError` (confirms removal)

**Classification rationale**: AUTO — all changes are pure deletions: comment lines with zero runtime effect, or alias assignments with zero active callers confirmed by the detection scan. The interview resolution for CC-DEEP-005 explicitly authorizes removal. No logic paths, no behavioral changes.

---

## Workstream: WS-TEST-QUALITY — Narrow Broad Exception Assertions

**Classification**: AUTO
**Source findings**: LS-DEEP-004, LS-DEEP-009
**Blocking**: NO (MEDIUM/LOW severity — advisory)
**Effort**: small (30 minutes)

### File-Scope Contract

| File | Operation | Scope |
|------|-----------|-------|
| `tests/unit/metrics/test_adversarial.py` | REPLACE `pytest.raises(Exception)` with specific types | Lines 183, 190 |
| `tests/unit/query/test_saved_queries.py` | REPLACE `pytest.raises(Exception)` with specific types | Lines 188, 201 |
| `tests/unit/query/test_adversarial_hierarchy.py` | REPLACE `pytest.raises(Exception)` with specific type | Line 248 |
| `tests/unit/query/test_adversarial.py` | REPLACE `pytest.raises(Exception)` with specific type | Line 1135 |
| `src/autom8_asana/query/__main__.py` | REPLACE redundant `PermissionError` in isinstance tuple | Line 452 |

### Patch Instructions

**LS-DEEP-004 — Narrow `pytest.raises(Exception)` (6 occurrences)**

All 6 substitutions are mechanical. The comments in the test files document the correct types; they become redundant after the fix and should be removed.

`tests/unit/metrics/test_adversarial.py:183`:
```python
# Before:
with pytest.raises(Exception):  # ColumnNotFoundError or SchemaError
# After:
with pytest.raises((pl.exceptions.ColumnNotFoundError, pl.exceptions.SchemaError)):
```

`tests/unit/metrics/test_adversarial.py:190`:
```python
# Before:
with pytest.raises(Exception):
# After:
with pytest.raises(pl.exceptions.ColumnNotFoundError):
```
Confirm `import polars as pl` is at the top of `test_adversarial.py`. The test description (`test_missing_dedup_key_column_raises`) confirms a missing column error is expected.

`tests/unit/query/test_saved_queries.py:188`:
```python
# Before:
with pytest.raises(Exception):  # pydantic ValidationError
# After:
with pytest.raises(ValidationError):
```
Add `from pydantic import ValidationError` to the import section at the top of the file (not inline). Apply this same import and fix to line 201.

`tests/unit/query/test_saved_queries.py:201`:
```python
# Before:
with pytest.raises(Exception):  # pydantic ValidationError
# After:
with pytest.raises(ValidationError):
```

`tests/unit/query/test_adversarial_hierarchy.py:248`:
```python
# Before:
with pytest.raises(Exception):  # polars.exceptions.SchemaError
# After:
with pytest.raises(pl.exceptions.SchemaError):
```
Confirm `import polars as pl` is at the top of this test file.

`tests/unit/query/test_adversarial.py:1135`:
```python
# Before:
# Polars raises ColumnNotFoundError when filtering by missing column
with pytest.raises(Exception):
# After:
# Polars raises ColumnNotFoundError when filtering by missing column
with pytest.raises(pl.exceptions.ColumnNotFoundError):
```

**LS-DEEP-009 — Remove redundant `PermissionError` from `isinstance` check**

`src/autom8_asana/query/__main__.py:452`:
```python
# Before:
if isinstance(error, (OSError, PermissionError)):
# After:
if isinstance(error, OSError):
```
`PermissionError` is a Python stdlib subclass of `OSError` — removing it from the tuple is a provable no-op. The `FileNotFoundError` case (also a subclass of `OSError`) is handled separately on line 445 via its own `isinstance` check before this line, so the ordering is correct.

### Verification Steps

```bash
pytest tests/unit/metrics/test_adversarial.py \
       tests/unit/query/test_saved_queries.py \
       tests/unit/query/test_adversarial_hierarchy.py \
       tests/unit/query/test_adversarial.py \
       -x -q
```
All targeted tests must pass.

**Classification rationale**: AUTO — the test comments explicitly document the correct exception types, making this mechanical substitution with zero ambiguity. `LS-DEEP-009` is dead-code removal with provable no-op behavior.

---

## Workstream: WS-HEALTH-MOCK — Fix Fragile Patch Target in Health Check Tests

**Classification**: MANUAL
**Source finding**: HH-DEEP-001
**Blocking**: YES (HIGH severity — mock bypasses abstraction boundary)
**Effort**: small (2–4 hours including test validation)

### File-Scope Contract

| File | Operation | Scope |
|------|-----------|-------|
| `tests/unit/api/test_health.py` | REWORK mock setup for 6 test methods | Lines 274, 289, 304, 319, 328, 342 (patch target strings + mock configuration) |

### Flaw Description

Six tests in `TestDepsEndpoint` patch `"httpx.AsyncClient.get"` at the httpx class level. The production code in `health.py` wraps all JWKS HTTP calls through `Autom8yHttpClient`:

```python
async with Autom8yHttpClient(_jwks_config) as client:
    async with client.raw() as raw_client:
        response = await raw_client.get(jwks_url)
```

The class-level patch works today because `raw()` returns a plain `httpx.AsyncClient`, but it bypasses `Autom8yHttpClient` entirely, creating two hidden fragility vectors:

1. If `autom8y_http` ever wraps its exceptions in custom types (rather than re-exporting httpx exceptions directly), the `side_effect = httpx.TimeoutException(...)` lines stop exercising the intended `except TimeoutException` branches — silently.
2. If `raw()` ever returns a subclass or proxy instead of a plain `httpx.AsyncClient`, the class-level patch no longer intercepts the method.

The canonical pattern (established by H-001/H-002 fixes in REM-HYGIENE) is to patch `Autom8yHttpClient` at the module import site.

### Recommended Fix Approach

Replace all 6 `patch("httpx.AsyncClient.get")` calls with `patch("autom8_asana.api.routes.health.Autom8yHttpClient")`. The mock must mirror the three-level async context manager chain:

```
Autom8yHttpClient(config)   -> __aenter__ returns http_client mock
  http_client.raw()         -> async context manager; __aenter__ returns raw_client mock
    raw_client.get(url)     -> the actual HTTP call being controlled
```

**Template for success-case tests** (lines 274, 319, 342):
```python
with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
    mock_http_client = AsyncMock()
    mock_raw_client = AsyncMock()
    mock_raw_client.get = AsyncMock(return_value=mock_response)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)
    mock_http_client.raw.return_value.__aenter__ = AsyncMock(return_value=mock_raw_client)
    mock_http_client.raw.return_value.__aexit__ = AsyncMock(return_value=None)
    mock_cls.return_value = mock_http_client
    response = client.get("/health/deps")
```

**Template for exception-case tests** (lines 289, 304, 328):
```python
with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
    mock_http_client = AsyncMock()
    mock_raw_client = AsyncMock()
    mock_raw_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    # (same __aenter__/__aexit__ wiring as above)
    mock_cls.return_value = mock_http_client
    response = client.get("/health/deps")
```

Use `tests/unit/clients/data/test_client.py` as a reference — it contains the established pattern for mocking `Autom8yHttpClient` at the module import site, applied across 10+ test sites during the H-001 fix in REM-HYGIENE.

The test assertions themselves (response status codes, JSON keys, `latency_ms` presence) do not change — only the mock wiring changes.

After applying: `pytest tests/unit/api/test_health.py -v` — all tests must pass.

**Classification rationale**: MANUAL — requires understanding of async context manager mock chaining across three levels. While the target patch string is unambiguous (`autom8_asana.api.routes.health.Autom8yHttpClient`), the correct mock structure for the three-level async context manager chain requires judgment. Incorrect wiring produces `AttributeError` or silently passes tests that are not actually testing the intended path.

---

## Workstream: WS-METRICS — Fix Metrics CLI Output Formatting

**Classification**: MANUAL
**Source findings**: LS-DEEP-001, LS-DEEP-002
**Blocking**: YES (2x HIGH severity — behavioral incorrectness and crash risk)
**Effort**: small (4–6 hours including tests)

### File-Scope Contract

| File | Operation | Scope |
|------|-----------|-------|
| `src/autom8_asana/metrics/__main__.py` | REPLACE hardcoded `$` format + ADD `None` guard | Lines 95–102 |
| `tests/unit/metrics/` | ADD tests for non-financial formatting and empty-DataFrame handling | New test cases in existing adversarial test file |

### Flaw Description

**LS-DEEP-001** — Line 102 unconditionally formats all aggregation results as dollar amounts:
```python
print(f"\n  {metric.name}: ${total:,.2f}")
```
A `count` metric produces `$42.00` when it should produce `42`. Any future `mean`/`min`/`max` on a non-financial column will also display incorrectly.

**LS-DEEP-002** — `result[col].mean()`, `.min()`, `.max()` return `None` on an empty DataFrame. The `f"${total:,.2f}"` format string raises `TypeError: unsupported format character` when `total is None`. Current production metrics use `agg="sum"` which returns `0` on empty, masking this crash.

### Recommended Fix Approach

Replace lines 95–102 in `src/autom8_asana/metrics/__main__.py`.

**Option A — Infer format from `MetricExpr.agg`** (preferred, no model change required):

```python
agg_fn = getattr(result[metric.expr.column], metric.expr.agg)
total = agg_fn()

# Guard None: mean/min/max on empty DataFrame returns None
if total is None:
    formatted = "N/A (no data)"
elif metric.expr.agg == "count":
    formatted = f"{int(total):,}"
else:
    # sum, mean, min, max on financial columns
    formatted = f"${total:,.2f}"

if metric.scope.dedup_keys:
    dedup_desc = ", ".join(metric.scope.dedup_keys)
    print(f"Unique ({dedup_desc}) combos: {len(result)}")

print(f"\n  {metric.name}: {formatted}")
```

**Option B — Add `format: str` field to `MetricExpr`** (more explicit, requires model change):
Add `format: Literal["currency", "integer", "float"] = "currency"` to `MetricExpr` in `metrics/expr.py`. Existing metric definitions default to `"currency"`. This is more extensible but requires migrating metric definitions and updating tests.

**Recommendation**: Option A handles the immediate correctness problem with no model changes. Option B is appropriate if the metrics system is expected to grow significantly. Discuss with the team before implementing.

**None guard semantics**: Use `"N/A (no data)"` — not `0.0`. An empty result means the classification filter excluded all rows. Displaying `$0.00` would misrepresent "no qualifying data" as "the metric is genuinely zero."

**Tests to add**:
- `test_count_metric_formats_as_integer` — register a `count` metric, run it against a non-empty DataFrame, assert output contains `42` not `$42.00`
- `test_empty_dataframe_mean_returns_no_data` — run a `mean` metric against an empty DataFrame, assert output contains `"N/A (no data)"` without raising `TypeError`

**Classification rationale**: MANUAL — the correct formatting behavior requires a product decision (Option A vs. Option B), and the `None` sentinel semantics (`0.0` vs `"N/A"` vs omit the line) require understanding of what the metrics CLI communicates to users. The current hardcoded `$` format is definitively wrong, but the replacement requires judgment.

---

## Workstream: WS-QUERY — Query CLI Robustness Improvements

**Classification**: MANUAL
**Source findings**: LS-DEEP-003, LS-DEEP-008, LS-DEEP-010
**Blocking**: NO (MEDIUM/LOW severity — advisory)
**Effort**: medium (2–3 days for all three; LS-DEEP-003 alone is small ~4 hours)

### File-Scope Contract

| File | Operation | Scope |
|------|-----------|-------|
| `src/autom8_asana/query/__main__.py` | EXTRACT shared `_execute_live` helper | Lines 273–372 (replacing `execute_live_rows` and `execute_live_aggregate`) |
| `src/autom8_asana/query/__main__.py` | REFACTOR or DOCUMENT `_get_output_stream` | Lines 477–482 |
| `src/autom8_asana/query/__main__.py` | NARROW bare `except Exception` in `list-queries` | Lines 1006–1008 |

### LS-DEEP-003: Extract `_execute_live` helper (MEDIUM — advisory)

**Flaw**: `execute_live_rows` (lines 273–321) and `execute_live_aggregate` (lines 324–372) share ~45 LOC of identical logic. They differ only in URL path suffix (`rows` vs `aggregate`) and response model (`RowsResponse` vs `AggregateResponse`).

**Recommended fix**: Extract a private `_execute_live` function:

```python
def _execute_live(
    entity_type: str,
    path_suffix: str,
    request_data: dict[str, Any],
    response_model: type[Any],
) -> Any:
    """Shared implementation for live HTTP query execution."""
    import httpx

    base_url, headers = _get_live_config()
    url = f"{base_url}/v1/query/{entity_type}/{path_suffix}"

    try:
        resp = httpx.post(url, json=request_data, headers=headers, timeout=30.0)
        resp.raise_for_status()
    except httpx.ConnectError:
        raise CLIError(
            f"Cannot connect to {base_url}. "
            "Is the data service running? Start with 'just dev-up data'.",
            exit_code=2,
        )
    except httpx.HTTPStatusError as e:
        raise CLIError(
            f"API error ({e.response.status_code}): {e.response.text}",
            exit_code=1,
        )
    except httpx.TimeoutException:
        raise CLIError(
            f"Request to {url} timed out after 30s.",
            exit_code=2,
        )

    return response_model.model_validate(resp.json())


def execute_live_rows(entity_type: str, request_data: dict[str, Any]) -> Any:
    """Execute a rows query via the live HTTP API."""
    from autom8_asana.query.models import RowsResponse
    return _execute_live(entity_type, "rows", request_data, RowsResponse)


def execute_live_aggregate(entity_type: str, request_data: dict[str, Any]) -> Any:
    """Execute an aggregate query via the live HTTP API."""
    from autom8_asana.query.models import AggregateResponse
    return _execute_live(entity_type, "aggregate", request_data, AggregateResponse)
```

Verify: the timeout error message in `_execute_live` uses `url` (which incorporates the path suffix), so the message is still specific — `"Request to https://host/v1/query/offer/rows timed out after 30s."` This is semantically equivalent to the current per-function messages. Confirm existing `execute_live_rows` and `execute_live_aggregate` tests pass unchanged.

**Classification rationale**: MANUAL — the extracted function must be verified semantically equivalent. The timeout error message uses a locally-constructed `url` variable; verify it produces the same output as the current per-function f-strings before replacing both.

---

### LS-DEEP-008: Fix `_get_output_stream` file handle pattern (LOW — advisory)

**Flaw**: `_get_output_stream` opens and returns a file handle without being a context manager. All current callers use `try/finally`, but the pattern is fragile for future callers.

**Option A — Convert to context manager** (recommended):

```python
from contextlib import contextmanager
from collections.abc import Generator

@contextmanager
def _output_stream(args: argparse.Namespace) -> Generator[IO[str], None, None]:
    """Context manager for output stream: file or stdout."""
    output_path = getattr(args, "output", None)
    if output_path:
        with open(output_path, "w") as f:
            yield f
    else:
        yield sys.stdout
```

Update all caller sites from `out = _get_output_stream(args)` + `try/finally` to `with _output_stream(args) as out:`. Rename the function during the refactor to distinguish from the current `_get_output_stream`.

**Option B — Document caller contract** (lower effort):
Keep `_get_output_stream` as-is, update the `noqa: SIM115` suppression comment to document the caller contract:
```python
return open(output_path, "w")  # noqa: SIM115 -- caller owns close() via try/finally
```

**Recommendation**: Option A eliminates the latent bug pattern and aligns with Python resource management conventions. Option B is acceptable given the CLI context (process exit is final cleanup) and the discipline of current callers.

**Classification rationale**: MANUAL — requires deciding between two valid approaches based on team preference for the CLI's resource management convention.

---

### LS-DEEP-010: Narrow bare `except Exception` in `list-queries` (LOW — advisory)

**Flaw**: The `list-queries` discovery loop at lines 1006–1008 swallows all exceptions silently. A user whose saved query file has a YAML syntax error receives no diagnostic output.

**Recommended fix**:

```python
import logging  # or: from autom8y_log import get_logger

# In the discovery loop (replace lines 1006-1008):
try:
    saved = load_saved_query(p)
    rows.append({...})
except (yaml.YAMLError, json.JSONDecodeError, pydantic.ValidationError) as e:
    logger.warning("Skipping malformed query file %s: %s", p, e)
    continue
except Exception:
    logger.warning("Skipping query file %s due to unexpected error", p, exc_info=True)
    continue
```

Add the logger at module level using `autom8y_log.get_logger(__name__)` (the codebase's established pattern). The `yaml` module is available via `from autom8_asana.query.saved import load_saved_query`'s dependencies; add `import yaml`, `import json`, and `import pydantic` at the top of the function or file as needed.

The warning is only emitted when a file is actually skipped — nominal discovery produces no extra output.

**Classification rationale**: MANUAL — requires deciding the logging strategy (logger vs. stderr print), the exception type granularity in the first branch, and whether warnings are appropriate in the CLI UX context.

---

## Deferred Items

### LS-DEEP-005 / RS-021 — HierarchyAwareResolver Cache Miss (upstream)

**Interview resolution**: Decision A — file upstream issue on `autom8y-cache`, keep skip annotation, update with link.

**Action**: Once the upstream issue is filed at `autom8y-cache`, update the skip reason in `tests/integration/test_platform_performance.py:208-211`:

Current:
```python
reason="RS-021: resolve_batch cache miss — fetch_count=4 on second call, "
"needs architect-enforcer investigation per B-001"
```

Target (fill in `NNN` with the actual issue number):
```python
reason=(
    "RS-021: resolve_batch cache miss in autom8y-cache HierarchyAwareResolver. "
    "fetch_count=4 on second call (expected 2). "
    "Upstream: https://github.com/autom8y/autom8y-cache/issues/NNN"
)
```

No other code change to this repo.

**Trigger**: File upstream issue, then update skip reason with URL.
**Classification**: MANUAL-DEFERRED

---

### LS-DEEP-006 / D-015 — Always-Null Derived Columns (`vertical_id`, `max_pipeline_stage`)

**Interview resolution**: Decision A — implement the lookups as a separate task requiring Vertical model + UnitHolder model access.

**What needs to be implemented** (when models are accessible):

`src/autom8_asana/dataframes/extractors/unit.py:71–95` — `_extract_vertical_id`:
- Input: `task.custom_fields` value for the `vertical` key (the raw custom field string, e.g., `"dental"`)
- Required: lookup from vertical key to Vertical model database ID
- Output: `str` (database ID) or `None` if key not found

`src/autom8_asana/dataframes/extractors/unit.py:97–118` — `_extract_max_pipeline_stage`:
- Input: Unit's associated UnitHolder(s)
- Required: UnitHolder model with pipeline stage tracking
- Output: `str` (stage name/identifier) or `None` if no holder data

**Interim action** (do now, no model access required): Update schema descriptions for `vertical_id` and `max_pipeline_stage` in `src/autom8_asana/dataframes/schemas/unit.py:66-85` to say `"Planned: stub returns None pending Vertical/UnitHolder model access"` so the `fields unit` CLI output is honest about stub status.

**Trigger**: Vertical model and UnitHolder model become accessible from the extractor context.
**Classification**: MANUAL-DEFERRED (interim schema description update is AUTO-eligible but low priority)

---

## Cross-Rite Referrals

| Finding | Target Rite | Action |
|---------|-------------|--------|
| LS-DEEP-007 (path traversal in `query/saved.py:94-114`) | **security** | Evaluate whether `run` subcommand path loading needs containment to `./queries/` and `~/.autom8/queries/`. Low risk in current CLI-only context; HIGH risk if the `run` subcommand is ever exposed via API or web interface. `yaml.safe_load` and Pydantic validation mitigate deserialization attacks but not file-read scope. |
| LS-009 through LS-024 (copy-paste clusters in test files) | **hygiene** | Parametrize test clusters: `test_unit_schema.py` (10 column-existence tests), `test_normalizers.py` (9 normalization tests), `test_pii.py` (5 phone masking tests). Estimated ~600–800 LOC reduction. Tests are functionally correct; improvement is maintainability only. |

---

## Finding Coverage Verification

Every finding from all three prior reports is accounted for:

| Finding | Source Report | Remedy | Workstream |
|---------|--------------|--------|------------|
| HH-DEEP-001 | detection-report | MANUAL fix | WS-HEALTH-MOCK |
| HH-DEEP-002 | detection-report | AUTO patch | WS-DEPS |
| LS-DEEP-001 | analysis-report | MANUAL fix | WS-METRICS |
| LS-DEEP-002 | analysis-report | MANUAL fix | WS-METRICS |
| LS-DEEP-003 | analysis-report | MANUAL fix | WS-QUERY |
| LS-DEEP-004 | analysis-report | AUTO patch | WS-TEST-QUALITY |
| LS-DEEP-005 | analysis-report | MANUAL-DEFERRED (upstream issue + skip update) | Deferred |
| LS-DEEP-006 | analysis-report | MANUAL-DEFERRED (interim schema description update) | Deferred |
| LS-DEEP-007 | analysis-report | Cross-rite referral to security | Referral |
| LS-DEEP-008 | analysis-report | MANUAL fix | WS-QUERY |
| LS-DEEP-009 | analysis-report | AUTO patch | WS-TEST-QUALITY |
| LS-DEEP-010 | analysis-report | MANUAL fix | WS-QUERY |
| LS-009..LS-024 (carry-forward) | analysis-report | Cross-rite referral to hygiene | Referral |
| CC-DEEP-001 | decay-report | AUTO patch | WS-TEMPORAL |
| CC-DEEP-002 | decay-report | AUTO patch | WS-TEMPORAL |
| CC-DEEP-003 | decay-report | AUTO patch | WS-TEMPORAL |
| CC-DEEP-004 | decay-report | AUTO patch | WS-TEMPORAL |
| CC-DEEP-005 | decay-report | AUTO patch | WS-TEMPORAL |
| CC-DEEP-006 | decay-report | AUTO patch | WS-TEMPORAL |

**Orphaned findings**: None. All 19 findings have a remedy, deferral, or referral.

---

## Handoff Checklist

- [x] Every finding from all prior reports has a remedy, explicit deferral, or cross-rite referral
- [x] AUTO patches labeled AUTO with classification rationale
- [x] MANUAL fixes include flaw description, expected correct behavior, and recommended fix approach
- [x] Temporal debt cleanup plans (WS-TEMPORAL) include explicit verification steps
- [x] Effort estimates for all MANUAL fixes
- [x] Safe/unsafe classification justified for each fix
- [x] Deferred items include trigger conditions
- [x] Cross-rite referrals include target rite and action description
- [x] Finding coverage table confirms zero orphaned findings

**Ready for gate-keeper.**
