---
type: audit
---
# SLOP-CHOP-DEEP Analysis Report

**Phase**: 2 -- Analysis
**Specialist**: logic-surgeon
**Date**: 2026-02-25
**Scope**: `src/autom8_asana/` + `tests/`

---

## Executive Summary

| Severity | Count | Confidence Distribution |
|----------|-------|-------------------------|
| HIGH     | 2     | 1 HIGH, 1 MEDIUM        |
| MEDIUM   | 6     | 3 HIGH, 2 MEDIUM, 1 LOW |
| LOW      | 3     | 2 MEDIUM, 1 LOW         |
| **Total**| **11**|                         |

**Verdict**: Codebase is in strong shape after four major initiatives. No CRITICAL findings. Two HIGH findings relate to behavioral logic issues (metrics dollar-sign formatting assumption and empty-DataFrame crash). Six MEDIUM findings cover test degradation (broad exception catches, copy-paste clusters still present), code duplication, and latent data quality. Three LOW findings are advisory. RS-021 confirmed as a genuine cache miss in the external `autom8y_cache` library, not a bug in this repo.

---

## Findings

### LS-DEEP-001: Metrics CLI hardcodes dollar-sign formatting for all aggregations

- **Severity**: HIGH
- **Confidence**: HIGH
- **Category**: logic-error
- **File**: `src/autom8_asana/metrics/__main__.py:102`
- **Evidence**:
  ```python
  print(f"\n  {metric.name}: ${total:,.2f}")
  ```
  The `$` prefix and `,.2f` formatting are unconditionally applied regardless of the metric's aggregation function or column semantics. `MetricExpr.agg` supports `sum`, `count`, `mean`, `min`, `max` -- and the `count` aggregation produces an integer count of rows, not a dollar amount. Similarly, `mean` on a non-financial column or any future metric that counts entities will display as e.g. `$42.00` when it should display `42`.

  Current metric definitions (`active_mrr`, `active_ad_spend`) happen to be financial sums, so this bug is masked in production. But the CLI is designed as a generic metric runner (`MetricRegistry` accepts arbitrary metrics), and the formatting assumption will silently produce misleading output the moment a non-financial metric is registered.
- **Impact**: Incorrect output formatting for any non-financial metric. `count` metrics display as `$N.00`. No data corruption, but user-facing incorrectness.
- **Interview**: NO

---

### LS-DEEP-002: Empty DataFrame crash in metrics CLI with `mean`/`min`/`max` aggregation

- **Severity**: HIGH
- **Confidence**: MEDIUM
- **Category**: logic-error
- **File**: `src/autom8_asana/metrics/__main__.py:95-102`
- **Evidence**:
  ```python
  agg_fn = getattr(result[metric.expr.column], metric.expr.agg)
  total = agg_fn()
  ...
  print(f"\n  {metric.name}: ${total:,.2f}")
  ```
  This uses `getattr` to dynamically call a Polars Series method based on `metric.expr.agg` (a string like `"sum"`, `"count"`, `"mean"`, etc.). While `MetricExpr.__post_init__` validates that `agg` is in `SUPPORTED_AGGS` (`frozenset({"sum", "count", "mean", "min", "max"})`), there is an edge case with empty DataFrames:

  If `compute_metric` returns an empty DataFrame (all rows filtered out), `result[col].sum()` returns `0` (correct for sum), and `result[col].count()` returns `0`. However, `result[col].mean()` returns `None`, and `result[col].min()` / `result[col].max()` also return `None`. The subsequent `print(f"\n  {metric.name}: ${total:,.2f}")` will then fail with `TypeError: unsupported format character` because `None` cannot be formatted as `,.2f`.

  Current production metrics use `agg="sum"` which returns `0` on empty, masking this issue. But the metrics framework explicitly supports `mean`, `min`, `max` -- and all three return `None` on empty DataFrames.
- **Impact**: `TypeError` crash when a metric with `agg="mean"` (or `min`/`max`) runs against a DataFrame where all rows are filtered out. Crash is unhandled -- no try/except around this code path.
- **Interview**: NO

---

### LS-DEEP-003: `execute_live_rows` / `execute_live_aggregate` are near-identical copy-paste

- **Severity**: MEDIUM
- **Confidence**: HIGH
- **Category**: copy-paste-bloat
- **File**: `src/autom8_asana/query/__main__.py:273-372`
- **Evidence**: `execute_live_rows` (lines 273-321) and `execute_live_aggregate` (lines 324-372) differ only in:
  1. URL path suffix (`/rows` vs `/aggregate`)
  2. Response model (`RowsResponse` vs `AggregateResponse`)

  The 48-line function bodies are otherwise identical: same `import httpx`, same `_get_live_config()` call, same `httpx.post()` with timeout=30.0, same three `except` branches with identical error messages (only URL differs due to f-string), same `resp.raise_for_status()`, same `model_validate(resp.json())`.

  Variation delta: 4 tokens differ out of ~150 tokens per function body. This is classic extractable duplication -- a single `_execute_live(entity_type, path_suffix, request_data, response_model)` helper would eliminate ~45 LOC.
- **Impact**: Maintenance burden. A change to error handling, timeout, or auth logic requires parallel edits in both functions.
- **Interview**: NO

---

### LS-DEEP-004: Broad `pytest.raises(Exception)` in new test modules (6 occurrences)

- **Severity**: MEDIUM
- **Confidence**: HIGH
- **Category**: test-degradation
- **Files**:
  - `tests/unit/metrics/test_adversarial.py:183` -- comment says `ColumnNotFoundError or SchemaError`
  - `tests/unit/metrics/test_adversarial.py:190` -- no comment, should be `ColumnNotFoundError`
  - `tests/unit/query/test_saved_queries.py:188` -- comment says `pydantic ValidationError`
  - `tests/unit/query/test_saved_queries.py:201` -- comment says `pydantic ValidationError`
  - `tests/unit/query/test_adversarial_hierarchy.py:248` -- comment says `polars.exceptions.SchemaError`
  - `tests/unit/query/test_adversarial.py:1135` -- should be `ColumnNotFoundError`
- **Evidence**: All 6 occurrences use `pytest.raises(Exception)` instead of the specific exception type. The comments (where present) even document what the correct type should be: `ColumnNotFoundError`, `SchemaError`, `pydantic.ValidationError`. These are new test files introduced during AUTOM8_QUERY / metrics initiatives, not carry-forward from P1.

  These tests would pass even if the code raised `RuntimeError("database connection lost")` instead of the intended domain error. They verify that *something* fails, not that the *correct thing* fails.
- **Impact**: Tests do not verify error contract. A refactoring that changes which exception is raised would not be caught by these tests.
- **Interview**: NO

---

### LS-DEEP-005: RS-021 resolved -- cache miss is in `autom8y_cache.HierarchyAwareResolver`, not this repo

- **Severity**: MEDIUM
- **Confidence**: HIGH
- **Category**: logic-error (external)
- **File**: `tests/integration/test_platform_performance.py:208-241`
- **Evidence**: The skipped test `test_resolve_batch_caches_results` creates a `HierarchyAwareResolver` (imported from `autom8y_cache`), calls `resolve_batch` twice with the same keys, and expects `fetch_count` to remain at 2 on the second call. Instead, `fetch_count` reaches 4 -- the resolver re-fetches all items.

  Analysis of `CascadingFieldResolver._fetch_parent_async` in `src/autom8_asana/dataframes/resolver/cascading.py:487-550` shows:
  1. The local `_parent_cache` (dict) correctly caches results from `resolve_batch` (line 543: `self._parent_cache[parent_gid] = fetched_parent`).
  2. However, the `HierarchyAwareResolver` instance (from `autom8y_cache`) has its *own* internal cache, and `resolve_batch` is a method on that external class. The re-fetch happens *inside* `HierarchyAwareResolver.resolve_batch`, not in this repo's code.

  The test's assumption that `HierarchyAwareResolver.resolve_batch` caches internally is either: (a) a missing feature in `autom8y_cache`, or (b) the cache has different keying semantics than the test expects.

  This is NOT a bug in `autom8_asana`. The correct resolution is either:
  - File an issue on `autom8y-cache` to add internal result caching to `resolve_batch`
  - Or adjust the test expectation to match the actual `resolve_batch` contract

  The skip annotation with reason string is appropriate.
- **Impact**: Extra API calls (2x) when `resolve_batch` is called repeatedly with the same keys. Performance concern only, not correctness. The `CascadingFieldResolver` local cache mitigates this in the common path (via `_fetch_parent_async`).
- **Interview**: YES -- needs decision on whether to fix upstream in `autom8y-cache` or accept the performance characteristic.

---

### LS-DEEP-006: D-015 confirmed -- UnitExtractor stubs always return None, handled defensively

- **Severity**: MEDIUM
- **Confidence**: MEDIUM
- **Category**: logic-error (latent)
- **File**: `src/autom8_asana/dataframes/extractors/unit.py:71-118`
- **Evidence**: `_extract_vertical_id` and `_extract_max_pipeline_stage` unconditionally return `None`. These are derived fields with `source=None` in the unit schema (`src/autom8_asana/dataframes/schemas/unit.py:66-85`), so the base extractor dispatches to these methods via `f"_extract_{col.name}"` dynamic lookup.

  Downstream handling: Both columns are declared `nullable=True` in the schema and `str | None = None` in the `UnitRow` model (`src/autom8_asana/dataframes/models/task_row.py:106-108`). The `None` values flow through to Polars DataFrames as null columns, which are handled correctly by the query engine (null-safe comparisons, no crashes).

  **However**: The columns `vertical_id` and `max_pipeline_stage` are present in query results and exported data. Users querying `--select vertical_id` will always see `null`. This is documented ("stub implementation") but creates a silent data quality gap -- the schema advertises the field, the CLI shows it as available via `fields unit`, but the data is always null.

  The `contact` schema also references `vertical_id` (`src/autom8_asana/dataframes/schemas/contact.py:89`), suggesting the same stub pattern may exist there.
- **Impact**: Data quality -- always-null columns in exported DataFrames. No crash, but misleading schema advertisement.
- **Interview**: YES -- needs product decision on whether to implement the lookups, remove the columns from the schema, or document them as "planned" in the schema description.

---

### LS-DEEP-007: Saved query path loading lacks symlink/traversal guard

- **Severity**: MEDIUM
- **Confidence**: LOW
- **Category**: security-anti-pattern
- **File**: `src/autom8_asana/query/saved.py:94-114` and `src/autom8_asana/query/__main__.py:1052-1064`
- **Evidence**: The `run` subcommand in the CLI accepts a file path argument:
  ```python
  query_path = Path(query_arg)
  if query_path.exists():
      saved = load_saved_query(query_path)
  ```
  `load_saved_query` reads `path.read_text()` and then parses with `yaml.safe_load` or `json.loads`, followed by Pydantic validation. There is no check that the path is within expected directories (`./queries/` or `~/.autom8/queries/`).

  For a CLI tool used by the developer on their own machine, this is low risk -- the user explicitly provides the path. However, if the `run` subcommand is ever exposed through a web interface or API endpoint (e.g., `--live` mode extension), the lack of path containment becomes a file-read vulnerability.

  `yaml.safe_load` mitigates YAML deserialization attacks (no arbitrary Python execution). The Pydantic validation rejects extraneous fields. The risk is limited to reading arbitrary files and getting parse errors.
- **Impact**: LOW in current CLI context. Would become HIGH if the saved-query path is ever accepted from untrusted input.
- **Interview**: NO -- flag for security rite referral.

---

### LS-DEEP-008: File handle leak pattern in `_get_output_stream`

- **Severity**: LOW
- **Confidence**: MEDIUM
- **Category**: logic-error
- **File**: `src/autom8_asana/query/__main__.py:477-482`
- **Evidence**:
  ```python
  def _get_output_stream(args: argparse.Namespace) -> IO[str]:
      output_path = getattr(args, "output", None)
      if output_path:
          return open(output_path, "w")  # noqa: SIM115
      return sys.stdout
  ```
  When `--output` is provided, a file handle is opened and returned. Callers use a `try/finally` pattern to close it:
  ```python
  out = _get_output_stream(args)
  try:
      formatter.format_rows(result, out)
      print_metadata(result.meta)
  finally:
      if out is not sys.stdout:
          out.close()
  ```
  Currently, all callers open the stream right before the `try` block, so the `finally` properly closes it. The `noqa: SIM115` suppression acknowledges the bare `open()` without context manager. This is a latent bug pattern -- if a future handler calls `_get_output_stream` earlier (before query execution, for example), an exception in the intervening code would leak the handle.

  In CLI context this is low risk (process exit cleans up), but it violates the codebase's general pattern of defensive resource management.
- **Impact**: Latent file handle leak risk when `--output` is specified. Minor in CLI context.
- **Interview**: NO

---

### LS-DEEP-009: `handle_error` catches `PermissionError` redundantly after `OSError`

- **Severity**: LOW
- **Confidence**: MEDIUM
- **Category**: logic-error (minor)
- **File**: `src/autom8_asana/query/__main__.py:452`
- **Evidence**:
  ```python
  if isinstance(error, (OSError, PermissionError)):
      print(f"ERROR: {error}", file=sys.stderr)
      return 2
  ```
  `PermissionError` is a subclass of `OSError` in Python 3. The `isinstance(error, (OSError, PermissionError))` check is equivalent to `isinstance(error, OSError)` -- the `PermissionError` branch is dead code within the tuple. The behavior is correct (both map to exit code 2), so this is cosmetic, but it signals potential confusion about the exception hierarchy.
- **Impact**: None -- behavior is correct. Cosmetic redundancy.
- **Interview**: NO

---

### LS-DEEP-010: `list-queries` silently swallows all exceptions during query discovery

- **Severity**: LOW
- **Confidence**: LOW
- **Category**: logic-error
- **File**: `src/autom8_asana/query/__main__.py:994-1008`
- **Evidence**:
  ```python
  try:
      saved = load_saved_query(p)
      rows.append(...)
  except Exception:
      # Skip malformed query files silently
      continue
  ```
  The bare `except Exception` swallows ALL errors during query file discovery, including permission errors, encoding errors, disk I/O errors, and even programming errors in the Pydantic model. The comment acknowledges this is intentional ("skip malformed query files"), but the scope is overly broad. A user with a YAML syntax error in their query file would get no indication that the file was skipped.

  A better pattern would catch `(yaml.YAMLError, json.JSONDecodeError, pydantic.ValidationError)` and log/warn for other exceptions.
- **Impact**: Silent data loss in discovery output. User cannot diagnose why their saved query doesn't appear in `list-queries`.
- **Interview**: NO

---

## Carry-Forward Assessment

### LS-009 through LS-024 (Copy-paste clusters): STILL PRESENT

The 16 copy-paste cluster findings from P1 remain in the codebase. These were classified as SMELL (not DEFECT) and deferred to a hygiene rite. Representative examples:

- `test_unit_schema.py` (LS-011): 10 nearly identical column-existence tests that differ only in column name and dtype.
- `test_normalizers.py` (LS-016): 9 phone/domain normalization tests with identical structure, differing only in input/output values.
- `test_pii.py` (LS-021): 5 phone format masking tests with identical assertion patterns.

**Total estimated LOC reduction from parametrization**: ~600-800 lines (unchanged from P1 estimate).

**Recommendation**: Remains SMELL severity. These tests are functionally correct -- they just have unnecessary verbosity. Parametrization would improve maintainability without changing coverage.

### LS-025 through LS-027 (Broad exception assertions): PARTIALLY RESOLVED

- **LS-025** (`test_retry.py`, 7 occurrences of `pytest.raises(Exception)` catching `ClientError`): **RESOLVED** -- no `pytest.raises(Exception)` found in any retry test file. The REM-HYGIENE initiative tightened these.
- **LS-026** (`test_common_models.py`, `test_result.py`, `test_cascade.py`, `test_cache_integration.py`, 5 occurrences catching `ValidationError`/`FrozenInstanceError`): **RESOLVED** -- no `pytest.raises(Exception)` found in these files.
- **LS-027** (`test_section_edge_cases.py`, `test_join.py`, `test_edge_cases.py`, 4 occurrences catching `SchemaError`/`ColumnNotFoundError`): **RESOLVED** for the P1 files. However, 6 NEW occurrences were introduced in new test files (see LS-DEEP-004 above).

**Net status**: P1 occurrences resolved. 6 new occurrences introduced in AUTOM8_QUERY / metrics test modules.

---

## Clean Areas

The following areas were analyzed and showed no behavioral issues:

### `src/autom8_asana/query/` -- Query Engine Module (CLEAN with noted exceptions)

- **`query/engine.py`**: Clean orchestration pattern. Proper error hierarchy with domain-specific exceptions. Predicate depth guard (`QueryLimits`) prevents query bomb attacks.
- **`query/compiler.py`**: Type-safe predicate compilation against schema dtypes. No injection risk -- Polars expressions are constructed programmatically, not from string concatenation.
- **`query/models.py`**: Pydantic models with proper validation. `RowsRequest.limit` bounded to 1000 max.
- **`query/errors.py`**: Clean error hierarchy following canonical `to_dict()` pattern. All 8 error types map correctly to HTTP status codes.
- **`query/temporal.py`**: Clean date parsing with explicit validation. `parse_date_or_relative` handles both ISO dates and relative durations without ambiguity. No injection risk in regex pattern.
- **`query/offline_provider.py`**: Clean protocol implementation. `NullClient` sentinel pattern properly prevents accidental API calls in offline mode. In-process caching is correct.
- **`query/formatters.py`**: Output formatters handle empty DataFrames gracefully.

### `src/autom8_asana/metrics/` -- Metrics Computation Module (CLEAN with noted exceptions)

- **`metrics/compute.py`**: Correct 6-step pipeline. Classification filter at Step 0.5 is clean. `unique(subset=..., keep="first")` dedup is deterministic after sort.
- **`metrics/expr.py`**: `__post_init__` validates `agg` against `SUPPORTED_AGGS`. `to_polars_expr()` constructs expressions safely.
- **`metrics/registry.py`**: Singleton pattern with `reset()` for testing. No concurrency concerns (CLI is single-threaded).

### `src/autom8_asana/dataframes/offline.py` -- S3 Offline Loader (CLEAN)

- Paginated listing handles empty pages correctly (`.get("Contents", [])`).
- `LastModified` metadata propagation is correct.
- `diagonal_relaxed` concatenation handles schema variations across section parquets.
- Bucket configuration falls back to env var correctly.

### `src/autom8_asana/dataframes/resolver/cascading.py` -- Cascading Field Resolver (CLEAN)

- Circular reference detection via `visited` set is correct.
- Root fallback for Business entity type is appropriate.
- `_fetch_parent_async` cache-first pattern is correct.
- `S3_TRANSPORT_ERRORS` catch is appropriate for network errors.

### Test Quality -- Strong Areas

- **`tests/unit/metrics/test_compute.py`**: Excellent parity tests that reproduce old script logic and assert equivalence. Classification tests cover case-insensitivity, unknown entity types, missing columns.
- **`tests/unit/query/test_temporal.py`**: Pure-data fixtures with no mocks. Tests cover empty filters, date boundary conditions, relative date parsing.
- **`tests/unit/dataframes/test_offline.py`**: Thorough S3 loader tests including pagination, non-parquet filtering, env var fallback, LastModified propagation.
- **`tests/unit/query/test_saved_queries.py`**: Good coverage of YAML/JSON loading, search directory precedence, override semantics.

### Security Assessment -- CLI Input Surface (CLEAN)

- **No Polars expression injection**: CLI `--where` input is parsed into structured `Comparison` dicts via `parse_where_flag`, then validated through `Op` enum and Pydantic. No raw string interpolation into Polars expressions.
- **`--where-json` is validated**: Parsed as JSON, then validated via Pydantic discriminated union. Invalid structures rejected before reaching the query engine.
- **`yaml.safe_load` used everywhere**: No `yaml.load` (unsafe) calls. YAML deserialization attacks are mitigated.
- **Argparse validation**: `--format`, `--order-dir`, `--join-source` all use `choices=` restriction. Invalid values rejected at parse time.

### Unreviewed-Output Signal Check (CLEAN)

Compared new modules against established codebase conventions documented in `docs/guides/patterns.md`:

- **Error handling**: `query/errors.py` follows the canonical dict-mapping pattern from `api/routes/query.py`. `QueryEngineError` subclasses all implement `to_dict()`.
- **DI patterns**: Offline modules correctly avoid DI (they are CLI-context, not FastAPI). The `NullClient` sentinel replaces the need for `Optional` parameters.
- **Logging**: Uses `autom8y_log.get_logger(__name__)` consistently where logging is present.
- **No inconsistent idioms detected** between new modules and established conventions.

---

## Interview Escalation Items

### LS-DEEP-005: RS-021 -- HierarchyAwareResolver cache miss (upstream decision needed)

The cache miss (`fetch_count=4` when expected `2`) is confirmed to be in the `autom8y_cache` library's `HierarchyAwareResolver.resolve_batch` method, not in this repo's code. Two options:
1. File issue on `autom8y-cache` to add internal result caching to `resolve_batch`
2. Accept the performance characteristic and update the test expectation to `fetch_count=4`

### LS-DEEP-006: D-015 -- Always-null derived columns (`vertical_id`, `max_pipeline_stage`)

Product decision needed:
1. Implement the lookups (requires Vertical model and UnitHolder model access)
2. Remove the columns from the schema (breaking change for consumers)
3. Add "planned" or "stub" annotation to schema description so CLI `fields unit` output is honest

---

## Cross-Rite Referrals

| Finding | Target Rite | Reason |
|---------|------------|--------|
| LS-DEEP-007 (path loading) | security | Path traversal guard for potential future exposure |
| LS-009 through LS-024 (copy-paste) | hygiene | Parametrization cleanup, ~600-800 LOC reduction |

---

## Handoff Checklist

- [x] Each logic error includes flaw, evidence, expected correct behavior, confidence score
- [x] Copy-paste instances include duplicated blocks and variation delta
- [x] Test degradation findings include weakness and what a proper test would verify
- [x] Security findings flagged for cross-rite referral where warranted
- [x] Unreviewed-output signals include codebase-convention evidence
- [x] Severity ratings assigned to all findings
- [x] RS-021 analysis complete with behavioral root cause
- [x] D-015 analysis complete with downstream impact assessment
- [x] P1 carry-forward items (LS-009..LS-027) status verified

**Ready for cruft-cutter.**
