# Smell Verification Report: mypy --strict CI Compliance (Sprint 7)

**Date**: 2026-02-03
**Commit**: 1d6c80c (main)
**Verification Mode**: Post-fix confirmation
**VERIFICATION_STATUS**: CLEAN

---

## CI Gate Results

| Gate | Result |
|------|--------|
| `uv run mypy src/autom8_asana --strict` | **Success: no issues found in 289 source files** |
| `uv run ruff check .` | **All checks passed!** |

---

## Per-File Verification

### 1. `src/autom8_asana/auth/__init__.py` -- CLEAN

**Changes verified**: Lines 40-42. Stale `misc` error code removed from `detect_token_type` (line 41) and `get_auth_mode` (line 42) assignments. Retained `[misc,assignment]` on `AuthMode` (line 40) because `AuthMode = None` genuinely triggers both `misc` (incompatible types in conditional) and `assignment`.

**Type annotation quality**: Correct. The conditional import pattern for optional FastAPI dependency is a standard idiom. Error codes are specific and accurate.

**Smells introduced**: None.

### 2. `src/autom8_asana/query/compiler.py` -- CLEAN

**Changes verified**: Line 287 -- `_to_raw()` return type annotated as `dict[str, Any]`. Lines 127-137 -- six `# type: ignore[no-any-return]` comments on Polars comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`).

**Type annotation quality**: Correct. Polars comparison operators return `pl.Expr` at runtime but mypy sees `Any` due to Polars stub limitations. The `no-any-return` suppression is the standard approach. The `_to_raw()` return type accurately reflects the dict structure used for `model_validate` round-trips.

**Smells introduced**: None. The `Any` in the return type is necessary because `value` in `Comparison` is `Any`.

### 3. `src/autom8_asana/dataframes/builders/freshness.py` -- CLEAN

**Changes verified**: Line 130 -- `verdicts: dict[str, int] = {}` explicit type annotation.

**Type annotation quality**: Correct. The dict accumulates verdict string keys mapped to integer counts. The annotation matches the usage pattern at line 132 (`verdicts.get(..., 0) + 1`).

**Smells introduced**: None.

### 4. `src/autom8_asana/metrics/expr.py` -- CLEAN

**Changes verified**: Line 47 -- `cast_dtype: type[pl.DataType] | pl.DataType | None = None`. Line 80 -- `agg_fn: Callable[[], pl.Expr] = getattr(e, self.agg)`.

**Type annotation quality**: Good. The `cast_dtype` widening to accept both `type[pl.DataType]` (class-level, e.g., `pl.Float64`) and `pl.DataType` (instance-level) is correct because `pl.Expr.cast()` accepts both. The `getattr` typing as `Callable[[], pl.Expr]` is accurate for Polars aggregation methods (`.sum()`, `.mean()`, etc.) which take no arguments and return `pl.Expr`.

**Smells introduced**: Minor -- the `getattr` call at line 80 could theoretically receive a non-callable attribute if `self.agg` were invalid, but the `__post_init__` validation against `SUPPORTED_AGGS` prevents this. No action needed.

### 5. `src/autom8_asana/dataframes/builders/progressive.py` -- CLEAN

**Changes verified**: Lines 273-275 -- `section_names: dict[str, str]` annotation with `isinstance(s.name, str)` guard in dict comprehension.

**Type annotation quality**: Correct. The `Section.name` field is typed as `str | None` per the Asana API model. The `isinstance` guard filters out `None` names, ensuring the dict only contains `str -> str` mappings. This is more precise than a bare cast.

**Smells introduced**: None.

### 6. `src/autom8_asana/query/engine.py` -- CLEAN

**Changes verified**: Lines 199-203 -- `join_key is None` guard raising `JoinError`. Line 268 -- `# type: ignore[arg-type]` on `**join_meta`.

**Type annotation quality**: Correct. The `join_meta` dict has `dict[str, object]` type but `RowsMeta.__init__` expects specific keyword types; the `[arg-type]` suppression is appropriate for `**kwargs` unpacking of extra metadata. The error code is specific.

**Behavioral impact assessment** (see Section below).

**Smells introduced**: None.

### 7. `src/autom8_asana/api/routes/query.py` -- CLEAN

**Changes verified**: Line 189 -- return type changed from `QueryResponse` to `JSONResponse`. Line 473 -- `query_rows` return type remains `RowsResponse`.

**Type annotation quality**: Correct. The `query_entities` endpoint (line 189) constructs a `QueryResponse` but then wraps it in `JSONResponse` (line 394) to add deprecation headers. The return type `JSONResponse` accurately reflects what the function actually returns. FastAPI handles both `JSONResponse` and Pydantic model returns, so the `response_model=QueryResponse` decorator still governs the OpenAPI schema.

**Smells introduced**: None. The `response_model` parameter on the decorator and the function return type now tell a consistent story: the response_model documents the schema, the return type documents the implementation.

### 8. `src/autom8_asana/cache/dataframe_cache.py` -- CLEAN

**Changes verified**: Lines 184-186 -- `_build_callback: Callable[[str, str], Awaitable[None]] | None`. Lines 527-529 -- `set_build_callback` accepts `Callable[[str, str], Awaitable[None]]`.

**Type annotation quality**: Correct. The callback signature `(project_gid: str, entity_type: str) -> Awaitable[None]` matches all call sites (line 657: `await self._build_callback(project_gid, entity_type)`). The `set_build_callback` method correctly accepts a non-optional callback (you wouldn't call it to set None), while the field itself is `| None` with `default=None`.

**Smells introduced**: None.

### 9. `src/autom8_asana/api/main.py` -- CLEAN

**Changes verified**: Lines 1127-1133 -- `s3_watermark is not None` guards before `watermark_repo.set_watermark()` and `dataframe_cache.put_async()`.

**Type annotation quality**: Correct. Both `set_watermark` and `put_async` require `datetime` (not `datetime | None`). The guard prevents passing `None` to these typed APIs.

**Behavioral impact assessment** (see Section below).

**Smells introduced**: None.

---

## Bare type: ignore Audit

**Result**: Zero bare `type: ignore` comments found in `src/autom8_asana/`. Every suppression includes a specific error code (e.g., `[no-any-return]`, `[arg-type]`, `[misc,assignment]`, `[attr-defined]`).

---

## Dead type: ignore Check

All `type: ignore` comments in the 9 verified files are active (mypy would report errors without them). Confirmed by the clean mypy --strict pass: mypy reports unused type-ignore comments as errors under strict mode, and 0 errors were found.

---

## Behavioral Impact Assessment

### engine.py join_key None guard (lines 199-203)

```python
if join_key is None:
    raise JoinError(
        f"No join key found between {entity_type} "
        f"and {request.join.entity_type}"
    )
```

**Assessment: SAFE**

- `get_join_key()` returns `str | None`. Before this fix, passing `None` to `execute_join()` would have caused a runtime error deeper in the join logic (Polars `join` with `None` as the `on` column).
- The new guard fails fast with a descriptive `JoinError`, which is the established error type for join failures (used consistently at lines 153, 189, and in `query/join.py`).
- The HTTP layer in `query.py` does not explicitly catch `JoinError`, but the centralized exception handlers in `api/errors.py` handle `QueryEngineError` subclasses. `JoinError` is a `QueryEngineError` subclass, so it will be caught and returned as a structured error response.
- **No behavioral regression**: Previously this path would crash with an opaque error; now it raises a clean domain error.

### main.py s3_watermark None guard (lines 1127-1133)

```python
if s3_watermark is not None:
    watermark_repo.set_watermark(project_gid, s3_watermark)
if dataframe_cache is not None and s3_watermark is not None:
    await dataframe_cache.put_async(...)
```

**Assessment: SAFE**

- `load_dataframe()` returns `tuple[pl.DataFrame | None, datetime | None]`. When a DataFrame exists in S3 but lacks watermark metadata, `s3_watermark` is `None`.
- Skipping `set_watermark` when watermark is None is correct: setting a `None` watermark would be meaningless and the typed API rejects it.
- Skipping `put_async` when watermark is None is also correct: the cache entry requires a valid `datetime` watermark for freshness tracking. A cache entry without a watermark would be immediately expired on next freshness check.
- The DataFrame is still loaded and logged (line 1114-1126), so the only effect is that it won't be cached in the in-memory tier -- which is appropriate since we lack freshness metadata.
- **No behavioral regression**: This codepath only applies when S3 has a parquet file but no watermark, which is an edge case (Lambda writes both). The guard prevents a type error while maintaining correct cache semantics.

---

## New Smells Introduced by Fixes

**None identified.** All 9 fixes are minimal and precise:

- No `Any` leakage introduced
- No overly broad casts
- No behavioral changes beyond fail-fast guards
- No dead code introduced
- Type-ignore comments all have specific error codes
- Annotations match actual runtime types

---

## Overall Assessment

The codebase is fully compliant with `mypy --strict`. All 289 source files pass without errors. The 9 targeted fixes are clean, minimal, and introduce no new smells. The two logic-adjacent changes (engine.py join_key guard and main.py watermark guard) are both safe and improve error handling by failing fast with typed domain errors rather than allowing `None` propagation into downstream APIs.

---

## Attestation Table

| File | Read | Verified |
|------|------|----------|
| `src/autom8_asana/auth/__init__.py` | Yes | Clean |
| `src/autom8_asana/query/compiler.py` | Yes | Clean |
| `src/autom8_asana/dataframes/builders/freshness.py` | Yes | Clean |
| `src/autom8_asana/metrics/expr.py` | Yes | Clean |
| `src/autom8_asana/dataframes/builders/progressive.py` | Yes | Clean |
| `src/autom8_asana/query/engine.py` | Yes | Clean |
| `src/autom8_asana/api/routes/query.py` | Yes | Clean |
| `src/autom8_asana/cache/dataframe_cache.py` | Yes | Clean |
| `src/autom8_asana/api/main.py` | Yes | Clean |
