---
type: review
status: draft
---

# Scan Findings: project-asana-pipeline-extraction Phase 1

## Telos Pulse (verbatim)

"A coworker's ad-hoc request to extract actionable account lists from Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana service: there is no first-class BI export surface, and any response today would be a one-off script with zero reusability. This initiative transitions from observation (Iris snapshot) to repeatable, account-grain, CSV-capable data extraction codified in the service's dataframe layer."

## Inception Anchor

`.ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md:1-332` — primary inception anchor; §3 source-code inventory, §4.1 SS-Q1..Q5, §5 carry-forward gap inventory, §7 anti-pattern guards.

## Scope

- Target: Phase 1 created + modified files (8 source files, 4 test files)
- Complexity: FULL
- Date: 2026-04-28

## Files Under Scan

| File | LOC | Role |
|------|-----|------|
| `src/autom8_asana/api/routes/exports.py` | 569 | Created — main route module |
| `src/autom8_asana/api/routes/_exports_helpers.py` | 454 | Created — helpers |
| `tests/unit/api/test_exports_helpers.py` | 360 | Created — 38 tests |
| `tests/unit/api/test_exports_contract.py` | 244 | Created — 25 tests |
| `tests/unit/api/test_exports_format_negotiation.py` | 208 | Created — 13 tests |
| `tests/unit/api/test_exports_handler.py` | 294 | Created — 11 tests |
| `src/autom8_asana/query/models.py` | +19 modified | Op enum extension |
| `src/autom8_asana/api/routes/dataframes.py` | +108 modified | format kwarg |
| `src/autom8_asana/api/routes/__init__.py` | +6 modified | router exports |
| `src/autom8_asana/api/main.py` | +24 modified | dual-mount registration |

## Overview

- Files: 10 files touched across 3 directories
- Languages: Python (all)
- Tests: 4 test files, 87 tests total; test-to-new-source ratio approximately 1.1 (1106 test LOC : 1023 source LOC — above the 0.3 threshold)
- Dependencies: no new external dependencies introduced; reuses existing polars, fastapi, pydantic, autom8y_log

---

## Raw Signals

### SS-Q1: Structural Concerns in exports.py

**Direct answer**: exports.py at 569 LOC triggers the >500-line file heuristic. The complexity is structurally justified (module-level docstring 36 LOC, two Pydantic model classes, two router objects, three helper functions, one async guard wrapper, one shared handler, two route registrations), but the size signal is real and warrants tracking. No directory nesting beyond 4 levels. No mixed-concern indicators: Pydantic models, routers, and handler all live in this one module. The `export_handler` function itself spans lines 307–495 (approximately 188 LOC), making it the largest single function in the Phase 1 surface.

**Supporting signals**:

#### [COMPLEXITY] File size exceeds threshold
- **Location**: `src/autom8_asana/api/routes/exports.py`
- **Signal**: 569 LOC — exceeds the 500-line threshold
- **Evidence**: `wc -l` returns 569. The `export_handler` function body (lines 307–495, ~188 LOC) is the largest contributor. The function is a linear 11-step pipeline with inline error handling at each step; there is no branching complexity beyond what the pipeline dictates.
- **Confidence**: HIGH (threshold exceeded; structural justification present reduces severity concern but does not eliminate the signal)
- **Category**: Complexity

#### [COMPLEXITY] export_handler function length
- **Location**: `src/autom8_asana/api/routes/exports.py:307-495`
- **Signal**: Single async function spans ~188 LOC handling 11 distinct pipeline steps
- **Evidence**: Function body reads from line 307 (`async def export_handler`) through line 495 (return statement). The 11 steps are enumerated in the docstring at lines 317–334.
- **Confidence**: MEDIUM (188-LOC function is not a complexity red flag by itself given the linear pipeline structure; decomposition would increase indirection without obvious gain, but it is a signal for reviewers)
- **Category**: Complexity

#### [COMPLEXITY] Deferred dependency: lazy import of polars inside handler
- **Location**: `src/autom8_asana/api/routes/exports.py:336`, `_exports_helpers.py:125,159,181,201,343`
- **Signal**: `import polars as pl` executed inside function bodies rather than at module top
- **Evidence**: `exports.py:336` has `import polars as pl` as first line of `export_handler`. `_exports_helpers.py:125` has the same inside `attach_identity_complete`. This is consistent with the P1-C-06 design (polars is TYPE_CHECKING-only at import time to avoid circular-import issues in the test harness), but produces a per-call import cost that disappears after first call due to sys.modules caching.
- **Confidence**: LOW (common fastapi/polars integration pattern; sys.modules caching means no repeated I/O; noise unless test isolation causes repeated cold imports)
- **Category**: Hygiene

### SS-Q2: Structural Smells in _exports_helpers.py re: SCAR-005/006

**Direct answer**: No structural smell amplifying SCAR-005/006. The `attach_identity_complete` function correctly handles missing-column edge cases by marking all rows `False` rather than raising or silently dropping rows. The `filter_incomplete_identity` function has a defensive guard for the missing-column case. One signal worth flagging: the "missing columns" fallback in `attach_identity_complete` silently succeeds (returns df with all-False identity_complete), which means a schema drift where neither `office_phone` nor `vertical` is present would produce an all-False column without any error that would surface to the caller. This is a SCAR-005/006 adjacent risk: transparent but not fail-loud.

**Supporting signals**:

#### [STRUCTURE] attach_identity_complete silent all-False fallback
- **Location**: `src/autom8_asana/api/routes/_exports_helpers.py:130-139`
- **Signal**: When `office_phone` or `vertical` columns are absent, the function logs a WARNING and returns `identity_complete=False` for every row without raising an exception. A caller receiving the response would see 0 complete identities without understanding why.
- **Evidence**: Lines 130-139: `if not has_phone or not has_vertical: logger.warning(...); return df.with_columns(identity_complete=pl.lit(False))`. The warning is logged to the structlog logger but not surfaced as a 4xx/5xx in the handler (the handler calls `attach_identity_complete(result_df)` at line 454 with no exception path from this function).
- **Confidence**: MEDIUM (documented behavior per TDD AC-5; the design intent is "surface null-key rows, not fail"; scar-tissue context is that SCAR-005/006 risk is cascade-pipeline; this helper is post-pipeline — the risk profile is schema-mismatch rather than cascade ordering)
- **Category**: Structure

#### [HYGIENE] filter_incomplete_identity missing-column defensive path
- **Location**: `src/autom8_asana/api/routes/_exports_helpers.py:162-170`
- **Signal**: If `attach_identity_complete` was skipped upstream (programmer error), `filter_incomplete_identity` with `include=False` logs a warning and returns all rows unchanged — silently allowing incomplete-identity rows through when suppression was requested.
- **Evidence**: Lines 162-170: `if "identity_complete" not in df.columns: logger.warning(...); return df`. The guard exists and is tested (`test_exports_helpers.py:115-121`), but the test asserts only that `out.height == 1` — it does not assert the log warning was emitted. So the test confirms the "no silent drop" behavior but does not confirm the observability signal fires.
- **Confidence**: MEDIUM
- **Category**: Hygiene

No cascade-null amplification risk found. The `attach_identity_complete` computation is a boolean AND of two IS-NOT-NULL checks (line 142-143); it does not traverse the cascade chain. SCAR-005/006's risk domain (cascade ordering, source="cascade:..." enforcement) is separate from this surface.

### SS-Q3: Op Enum Extension — Silent Contract Risk

**Direct answer**: The BETWEEN/DATE_GTE/DATE_LTE additions to `Op` carry a bounded but real silent-failure risk in `compiler.py`'s `_build_expr` function. The match statement at `compiler.py:125-145` has no case arm for the three new values and falls through to `raise ValueError(f"Unknown operator: {op}")` at line 148 (marked `pragma: no cover`). The critical question is whether the ESC-1 guarantee — that date ops are stripped BEFORE `PredicateCompiler.compile` is called — holds in all code paths. In the exports handler it does (lines 369-376 in `exports.py`). However, the `Op` enum is shared across all callers of `PredicateCompiler`, and any caller that constructs a `Comparison` with `Op.BETWEEN/DATE_GTE/DATE_LTE` and routes it through `PredicateCompiler.compile` without the ESC-1 pre-translation step will get a `ValueError` at runtime, not a caught validation error. `fleet_query_adapter.py` does NOT reference `Op` directly (confirmed: zero grep hits for `Op.`, `Comparison`, `BETWEEN`, `DATE_GTE`, `DATE_LTE` in that file) — the adapter accepts raw dicts in `FleetQuery.filters` and passes through to `EntityQueryService.query`. The `OPERATOR_MATRIX` in `compiler.py` (lines 53-63) does not include BETWEEN/DATE_GTE/DATE_LTE as allowed ops for any dtype, so the `_compile_comparison` validation step at lines 228-234 would also surface `InvalidOperatorError` before reaching `_build_expr`, providing a second defense layer.

**Supporting signals**:

#### [STRUCTURE] Op match statement has no fallthrough arm for date ops
- **Location**: `src/autom8_asana/query/compiler.py:125-148`
- **Signal**: The `match op:` statement covers EQ/NE/GT/LT/GTE/LTE/IN/NOT_IN/CONTAINS/STARTS_WITH (10 arms) with no arm for BETWEEN/DATE_GTE/DATE_LTE. The fallback is `raise ValueError(f"Unknown operator: {op}")` marked `pragma: no cover`.
- **Evidence**: `grep -n "BETWEEN\|DATE_GTE\|DATE_LTE" compiler.py` returns zero results. The match statement ends at line 145 (`case Op.STARTS_WITH:`) with no `case _:` arm and no date-op arms. The `pragma: no cover` at line 148 documents that this path is not exercised in the test suite — which is intentional given the ESC-1 design, but means the runtime failure mode is untested.
- **Confidence**: HIGH (confirmed by file read; the gap exists; the ESC-1 design intent makes it a controlled gap rather than an oversight, but it is still a gap)
- **Category**: Structure

#### [STRUCTURE] OPERATOR_MATRIX excludes date ops — InvalidOperatorError fires before _build_expr
- **Location**: `src/autom8_asana/query/compiler.py:53-63` and `compiler.py:228-234`
- **Signal**: BETWEEN/DATE_GTE/DATE_LTE are absent from `OPERATOR_MATRIX`, so any caller routing a date-op Comparison through `PredicateCompiler.compile` will receive `InvalidOperatorError` at operator validation (line 230), not a silent failure or a crash at expression build time. This provides a defense-in-depth layer for the `_build_expr` gap above.
- **Evidence**: Lines 53-63 show only `_ORDERABLE_OPS | _UNIVERSAL_OPS | _STRING_OPS` per dtype; none include the date op members. The `Op.BETWEEN` / `Op.DATE_GTE` / `Op.DATE_LTE` string values (`"between"`, `"date_gte"`, `"date_lte"`) do not appear in the matrix.
- **Confidence**: HIGH
- **Category**: Structure

**Forward/backward compat grade**: CONTAINED. The new Op members are additive (StrEnum extension does not break existing Op consumers). The compiler's `OPERATOR_MATRIX` exclusion ensures any accidental routing of date ops into `PredicateCompiler` surfaces as `InvalidOperatorError` rather than a silent wrong-result. `fleet_query_adapter.py` does not consume `Op` directly. The sole risk is a new caller constructing a date-op `Comparison` and calling `PredicateCompiler.compile` without the ESC-1 pre-translation — which would produce a caught `InvalidOperatorError` (400 to the caller), not a silent data corruption.

### SS-Q4: Dual-Mount Registration — Ordering and Shadowing Risk

**Direct answer**: No shadowing risk observed. The exports routers are mounted at lines 438-439 of `main.py`, between the fleet_query routers (lines 430-432) and the legacy `query_router` (line 440). The relevant collision candidate is the legacy `/v1/query/{entity_type}` wildcard in `query_router`. The route `/v1/exports` does NOT match the `{entity_type}` pattern because it would require a match for the literal token `exports` as an entity type, but the path prefix `/v1/exports` is registered before `/v1/query/{entity_type}` in the router list, and exports uses a distinct prefix (`/v1/exports`, not `/v1/query/exports`). No path collision exists.

The `jwt_auth_config.exclude_paths` list (main.py:375-389) does NOT include `/api/v1/exports/*` or `/v1/exports/*`. This is the correct behavior for the S2S mount (`/v1/exports` uses JWT auth via `s2s_router`) but is structurally asymmetric with the PAT mount: `/api/v1/dataframes/*` is excluded (line 387) because PAT routes are handled by the dual-mode `get_auth_context` DI, but `/api/v1/exports/*` is NOT excluded.

**Supporting signals**:

#### [STRUCTURE] /api/v1/exports missing from jwt_auth_config exclude_paths
- **Location**: `src/autom8_asana/api/main.py:374-395`
- **Signal**: The `jwt_auth_config.exclude_paths` list excludes `/api/v1/dataframes/*`, `/api/v1/tasks/*`, and other PAT-mounted routes, but does NOT exclude `/api/v1/exports/*`. The exports PAT mount (`exports_router_api_v1`) uses `pat_router` which applies dual-mode `get_auth_context`. If the JWT middleware processes PAT requests to `/api/v1/exports` before the DI layer, PAT tokens (non-JWT Bearer) may be rejected by the JWT middleware before reaching the handler.
- **Evidence**: Lines 381-388 list the excluded PAT paths; `/api/v1/exports` is absent. `dataframes_router` is excluded at line 387; `exports_router_api_v1` is not. This is the same pattern as the existing PAT routes. The risk mirrors the SCAR-WS8 route-ordering constraint documented in `.know/scar-tissue.md:148`.
- **Confidence**: MEDIUM (the behavior depends on `JWTAuthConfig` middleware semantics and whether `pat_router` factory explicitly bypasses the JWT middleware — this cannot be confirmed from source read alone without inspecting `_security.py` or `autom8y_api_middleware`; flagged for pattern-profiler to confirm)
- **Category**: Structure

#### [STRUCTURE] Route registration order: exports after fleet_query, before query_router
- **Location**: `src/autom8_asana/api/main.py:430-440`
- **Signal**: Exports routers mount at lines 438-439; `query_router` (containing `/v1/query/{entity_type}`) mounts at line 440. The comment at lines 432-437 explicitly acknowledges the FastAPI registration-order constraint and states exports follows the same discipline as fleet_query.
- **Evidence**: Lines 432-437 contain the inline comment: "Mount BEFORE query_router so /v1/exports is not shadowed by the legacy /v1/query/{wildcard} path matcher." Routing order is correct per this documented discipline.
- **Confidence**: HIGH (no shadowing; order is correct; inline comment is the canonical evidence)
- **Category**: Structure

### SS-Q5: LEFT-PRESERVATION GUARD Wrapper Coverage

**Direct answer**: The NO-OP shim IS tested. Two tests exercise it: (1) `test_wrapper_invokes_strategy_get_dataframe` (test_exports_handler.py:53-73) confirms the wrapper calls `strategy._get_dataframe` and returns the DataFrame; (2) `test_wrapper_logs_phase_and_join_semantics` (test_exports_handler.py:75-109) patches the logger and asserts the `exports_left_preservation_guard_noop` log signal is emitted with `phase=1`, `join_active=False`, and the caller's `predicate_join_semantics` value. The second test is the observability test: it confirms the seam is wired and the Phase 1 metadata is logged. What is NOT tested: the case where `strategy._get_dataframe` returns `None` (the `CacheNotWarmError` raise path at exports.py:264-268). That branch exists but has no dedicated unit test for the guard wrapper itself (it is tested at the handler level via the end-to-end pipeline mock).

**Supporting signals**:

#### [TESTING] LEFT-PRESERVATION GUARD wrapper: NO-OP behavior is tested; CacheNotWarmError path not tested at wrapper level
- **Location**: `tests/unit/api/test_exports_handler.py:43-109` (tested); `src/autom8_asana/api/routes/exports.py:264-268` (untested at wrapper level)
- **Signal**: The two wrapper tests confirm: (a) the seam exists and fires, and (b) the log signal carries the correct Phase 1 metadata. The `df is None → CacheNotWarmError` path at `exports.py:264-268` has no dedicated wrapper test.
- **Evidence**: `test_exports_handler.py:53-73` asserts `out is fake_df`; `test_exports_handler.py:75-109` asserts `guard_calls` is non-empty and `extra["phase"] == 1`. The `None` return case is untested at the wrapper level — the `fake_df` fixture always returns a real DataFrame.
- **Confidence**: HIGH for tested path; MEDIUM for untested path (the CacheNotWarmError path is a structural gap but not a logical gap — the handler-level test at test_exports_handler.py:177-193 exercises the 400/503 error paths, though not via the null-return guard wrapper path specifically)
- **Category**: Testing

---

## AP-R-3 Sample Spot-Check Evidence Block

### (a) identity_complete null-key surfacing test — behavioral assertion check

**File:line read**: `tests/unit/api/test_exports_helpers.py:65-76`

Test `test_null_key_rows_NOT_silently_dropped` constructs a DataFrame with one null-phone/null-vertical row and calls `attach_identity_complete`. The assertion at line 75 checks `out.height == 2` (row count preserved — NOT silently dropped) and line 76 asserts `out["identity_complete"].to_list() == [True, False]`. This is a behavioral assertion about the documented SCAR-005/006 transparency invariant: the test specifically names "AP-6 guard" in its docstring and asserts the null-key row surfaces with `identity_complete=False`, not absent. The test does NOT merely assert absence of exception — it asserts the specific column values on the output frame.

**AP-R-3(a) verdict**: CORROBORATES the 10x-dev self-attestation. The test is behavioral (not just "no exception"), correctly names the AP-6 invariant, and asserts the exact output shape.

### (b) Dual-mount route test — both /v1 and /api/v1 paths exercised

**File:line read**: `tests/unit/api/test_exports_contract.py:154-165`

Tests `test_v1_router_uses_v1_prefix` (line 160) and `test_api_v1_router_uses_api_v1_prefix` (line 163) assert the router `.prefix` attributes directly. `test_v1_router_security_scheme_is_service_jwt` (line 168-177) inspects the security scheme on the S2S router. `test_api_v1_router_security_scheme_is_pat` (line 180-186) inspects the PAT router. The end-to-end handler test at `test_exports_handler.py:137-158` additionally confirms via source inspection that both route callables invoke `export_handler`.

Both `/v1/exports` and `/api/v1/exports` prefixes are exercised by distinct tests that assert prefix values and security scheme identity. This satisfies the AC-2/AC-3 dual-mount verification requirement.

**AP-R-3(b) verdict**: CORROBORATES. Both paths are exercised at the contract level. The tests assert prefix string values (not just "routers exist") and security-scheme identity.

### (c) LEFT-PRESERVATION GUARD wrapper — NO-OP shim observable coverage

**File:line read**: `tests/unit/api/test_exports_handler.py:75-109`

Test `test_wrapper_logs_phase_and_join_semantics` patches `autom8_asana.api.routes.exports.logger`, invokes `_engine_call_with_left_preservation_guard` with `predicate_join_semantics="allow-inner-rewrite"`, and then asserts the log was emitted with `extra["predicate_join_semantics"] == "allow-inner-rewrite"`, `extra["phase"] == 1`, and `extra["join_active"] is False`. The test also confirms `extra["entity_type"] == "process"`, `extra["project_gid"] == "123"`, `extra["request_id"] == "req-2"`.

The shim IS observably tested. The test asserts the NO-OP log signal fires with the correct Phase 1 metadata. The test confirms the mechanism (b) escape-valve value flows through to the log payload.

**AP-R-3(c) verdict**: CORROBORATES with a caveat. The NO-OP shim is observably tested. The gap is the `strategy._get_dataframe → None → CacheNotWarmError` branch, which exists at `exports.py:264-268` but has no wrapper-level unit test. This is a coverage gap, not a behavioral gap in the tested path.

**Overall AP-R-3 verdict**: The three spot-checks CORROBORATE the 10x-dev self-attestation. All three tested behaviors assert documented invariants (AP-6, dual-mount prefix, Phase 1 NO-OP metadata) with explicit assertion statements — not just absence-of-exception. One real gap identified: the `CacheNotWarmError` path inside the guard wrapper is not unit-tested at the wrapper level.

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Total files scanned | 10 |
| Signals identified | 9 |
| By category | Complexity: 3, Testing: 1, Dependencies: 0, Structure: 4, Hygiene: 1 |
| Test-to-source LOC ratio | 1106:1023 (~1.08) — above 0.3 threshold |
| Files exceeding 500 LOC | 1 (exports.py: 569) |
| New direct dependencies introduced | 0 |
| Op enum new members | 3 (BETWEEN, DATE_GTE, DATE_LTE) |

---

## Cross-Rite Routing Hints

- SS-Q2 `attach_identity_complete` all-False silent fallback and `filter_incomplete_identity` unlogged warning path → 10x-dev test-add (add assertion that log warning fires in the missing-column case)
- SS-Q3 `_build_expr` match statement missing date-op arms (`pragma: no cover`) → 10x-dev test-add (add a regression test that calls `PredicateCompiler.compile` with a date-op Comparison and confirms `InvalidOperatorError` fires before `_build_expr`)
- SS-Q4 `/api/v1/exports` missing from `jwt_auth_config.exclude_paths` → arch coupling review (confirm `pat_router` factory bypasses JWT middleware independently; if not, PAT callers to `/api/v1/exports` may receive 401 from JWT middleware before handler)
- SS-Q5 `CacheNotWarmError` branch in guard wrapper untested at wrapper level → 10x-dev test-add (optional; already covered at handler level but wrapper-level coverage would be cleaner)

---

## Out-of-Scope Phase 2 Callouts (AP-R-2)

No AP-R-2 trips fired. All signals are bounded to Phase 1 artifacts. The `predicate_join_semantics` field, `LEFT-PRESERVATION GUARD` wrapper, and `ExportOptions(extra="allow")` are Phase 1 structural forward-compatibility surfaces — observed and noted, not escalated as Phase 1 blockers. Phase 2 (join engine, boundary_predicate behavior, cross-entity work) not entered.
