---
domain: feat/exports-route
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/exports.py"
  - "./src/autom8_asana/api/routes/_exports_helpers.py"
  - "./tests/unit/api/test_exports_*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.96
format_version: "1.0"
---

# Feature Knowledge: Polars-backed /exports Route with Predicate-Tree Compilation

## 1. Purpose and Design Rationale

### Why This Feature Exists

The `/exports` route provides a **bulk, account-grain data export surface** for BI tooling (Vince's BI path) and internal pipeline consumers. Unlike `/api/v1/dataframes/{schema}` which returns raw schema-projected rows, the exports route delivers:

- Deterministic account-grain deduplication (one row per `office_phone × vertical` pair)
- An explicit `identity_complete` boolean column on every output row (SCAR-005/006 transparency — surfaces null-key rows rather than silently dropping them)
- Multi-format negotiation: JSON (default), CSV (BI-tool path), Parquet (analytics binary)
- Section scoping with an ACTIVE-only default (callers who forget to filter do not accidentally export inactive/dead records)
- Date-range predicates (`BETWEEN`, `DATE_GTE`, `DATE_LTE`) over the existing query AST without modifying the core `PredicateCompiler`

This is Phase 1 of `project-asana-pipeline-extraction`. The telos deadline is **2026-05-11** (Phase 1 DELIVERED; 3 days remain as of 2026-05-08).

### Problem Statement

Prior to this route, BI consumers had no single-call export path that:
1. Normalized to account grain (deduplicated across multi-project stacks)
2. Made identity completeness observable (consumers were silently missing rows with null phone/vertical)
3. Supported date-range filtering without requiring consumers to implement client-side temporal slicing

### Design Decisions and Rationale

**P1-C-01 — Single-entity hard-lock**: Phase 1 intentionally ships with no cross-entity join capability. The `ExportRequest` contract uses `extra="forbid"` at the top level to surface caller mistakes (e.g., passing a `join` field produces a 422, not silent ignore). Phase 2 LEFT JOIN semantics are reserved but not enabled.

**P1-C-02 — `ExportOptions.extra="allow"` (LOAD-BEARING, MUST NOT CHANGE)**: The inner `options` substructure uses `ConfigDict(extra="allow")` to reserve the `predicate_join_semantics` field for Phase 2. Changing this to `extra="forbid"` would be a breaking API change and would foreclose the LEFT-PRESERVATION GUARD ADR (mechanism (b) escape valve). This is a frozen constraint — see TENSION-010.

**P1-C-04 — Engine frozen**: The route deliberately does NOT modify `query/engine.py:139-178,181`, `query/join.py`, or `query/compiler.py:53-63,192-241`. All predicate processing for the exports surface happens in route-handler space, not inside the engine. This allows the engine to evolve independently and prevents blast-radius contamination. The frozen-range importer catalog is documented as FROZEN-RANGE-IMPORTERS-001.

**ESC-1 — Date operator translation before engine call**: `BETWEEN`, `DATE_GTE`, `DATE_LTE` are Sprint 2 additive operators. Rather than teaching the frozen `PredicateCompiler` about Polars temporal expressions, the route handler splits date-op `Comparison` nodes out of the AST before calling the compiler, translates them to `pl.Expr`, and AND-merges the result with the base filter post-engine-call. This is `translate_date_predicates()` in `_exports_helpers.py`. Trade-off: date predicates under `OR` or `NOT` semantics are rejected (TRADE-010) — callers must restructure to AND-level date bounds.

**ESC-2 — True dual-AUTH**: Both `/api/v1/exports` (PAT, user-facing) and `/v1/exports` (S2S, internal) call the SAME `export_handler` callable. Auth-scope verification is delegated to existing PAT/S2S middleware; the handler itself is auth-agnostic.

**ESC-3 — Row-count/size measurement at format seam**: Row count and serialized size are logged at `_format_dataframe_response`, preserving the measurement point across all three format paths (JSON, CSV, Parquet) without duplicating it.

**ACTIVE-only default (DEFER-WATCH-3 disposition "RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE")**: When the caller omits a `section` predicate entirely, the handler injects an ACTIVE-only filter (`Op.IN`, `ACTIVE_SECTIONS`) before the engine call. This is the "fail safe" default — callers who are unaware of section semantics do not accidentally export dead/inactive accounts. The flag `default_section_applied` is logged in the response meta for transparency.

**LEFT-PRESERVATION GUARD wrapper (Phase 1 NO-OP)**: An async wrapper `_engine_call_with_left_preservation_guard` sits between the handler and the engine's `_get_dataframe` call. In Phase 1, no joins ship so the guard is a structural NO-OP that logs its invocation. Its purpose is to demonstrate the seam for Sprint 4 qa-adversary verification and to ensure Phase 2 architect can slot the `.explain()` assertion body without restructuring the call graph. Mechanism (b) (caller opt-in via `predicate_join_semantics`) is wired through even in Phase 1.

**`PHASE_1_DEFAULT_COLUMNS`**: The exported column set is deliberately minimal (7 columns: `gid`, `name`, `section`, `office_phone`, `vertical`, `pipeline_type`, `modified_at`) per PRD §5.2 DEFER-WATCH-2. The `identity_complete` column is always appended if present in the frame. Extending this set is a Phase 4/5 concern.

---

## 2. Conceptual Model

### Key Entities and Types

| Type | Module | Role |
|------|--------|------|
| `ExportRequest` | `api/routes/exports.py:160` | Top-level request contract. `extra="forbid"` to catch caller typos. Fields: `entity_type`, `project_gids`, `predicate`, `format`, `options`. |
| `ExportOptions` | `api/routes/exports.py:122` | Inner open-extension substructure. `extra="allow"` (P1-C-02 BINDING). Named Phase 1 fields: `include_incomplete_identity` (bool, default `True`), `dedupe_key` (list[str], default `["office_phone", "vertical"]`). Phase 2 reserved: `predicate_join_semantics`. |
| `ExportsSuccessResponse` | `api/models.py:121` | Typed `SuccessResponse[list[dict[str, Any]]]` variant with `extra="ignore"` (TENSION-011). Used as `response_model` in the route registration for OpenAPI schema generation. The actual response is a Polars-serialized `Response` object (JSON/CSV/Parquet) — the `response_model` is declarative only. |
| `PredicateNode` | `query/models.py` | Discriminated union: `Comparison | AndGroup | OrGroup | NotGroup`. The `predicate` field in `ExportRequest` accepts this union. `Op` StrEnum includes 13 operators: standard comparison ops + `BETWEEN`, `DATE_GTE`, `DATE_LTE`, `IN`, `NOT_IN`. |
| `DateTranslationResult` | `_exports_helpers.py:335` | Output of `translate_date_predicates()`. Two fields: `cleaned_predicate` (AST with date-op nodes stripped) and `date_filter_expr` (composed `pl.Expr | None`). |
| `InvalidSectionError(ValueError)` | `_exports_helpers.py:91` | Raised when a caller's `section` predicate value is not in `PROCESS_PIPELINE_SECTIONS`. Surfaces as HTTP 400 `error.code: "unknown_section_value"`. |

### Invariants

1. **Identity completeness invariant**: Every output row has an `identity_complete` column. `True` iff both `office_phone IS NOT NULL` and `vertical IS NOT NULL`. This is the SINGLE source-of-truth (P1-C-05). It is NOT computed in `cascade_resolver.py` or `cascade_validator.py`.

2. **ACTIVE-default invariant**: If the caller predicate does not reference the `section` field at all, the handler injects `section IN ACTIVE_SECTIONS` before the engine call. Callers who explicitly include a `section` Comparison in their predicate (even `Op.IN` with active-only values) bypass injection.

3. **Mount-order invariant**: `exports_router_v1` and `exports_router_api_v1` MUST register before `query_router` in `api/main.py` because `query_router` uses wildcard `/v1/query/{entity_type}` that would shadow `/v1/exports`. Silent failure if ordering is violated — TENSION-009.

4. **Dual-mount fidelity invariant**: Both `/v1/exports` (S2S) and `/api/v1/exports` (PAT) call the identical `export_handler` callable. Any divergence between the two paths is structurally impossible.

5. **Eager-only invariant (P1-C-06)**: All transforms in `_exports_helpers.py` operate on `pl.DataFrame` (eager). No `pl.LazyFrame` consumer surface exists in Phase 1.

6. **Frozen-engine invariant (P1-C-04)**: The handler NEVER modifies `query/engine.py:139-178,181`, `query/join.py`, or `query/compiler.py:53-63,192-241`.

### Section Vocabulary

`VALID_SECTIONS` and `ACTIVE_SECTIONS` are computed at module load from `PROCESS_PIPELINE_SECTIONS` (sourced from `models/business/activity.py:282`). `ACTIVE_SECTIONS` is the subset used for the default inject. Section vocabulary validation happens at step 2 of the handler pipeline (before ACTIVE-default injection) so invalid caller values fail loudly.

### State / Request Flow

```
POST /v?/exports
  │
  ├─ 1. entity_service.validate_entity_type(entity_type)    [400 on UnknownEntityError]
  ├─ 2. validate_section_values(predicate)                   [400 InvalidSectionError]
  ├─ 3. apply_active_default_section_predicate(predicate)    [injects ACTIVE filter if no section]
  ├─ 4. translate_date_predicates(effective_predicate)       [400 ValueError on date under OR/NOT]
  ├─ 5. PredicateCompiler().compile(cleaned_predicate, schema)  [400 on UnknownField/InvalidOp/Coercion]
  ├─ 6. for each project_gid:
  │     ├─ _engine_call_with_left_preservation_guard(...)    [503 CacheNotWarmError]
  │     └─ df.filter(combined_filter_expr)
  ├─ 7. pl.concat(frames, how="diagonal_relaxed")
  ├─ 8. attach_identity_complete(df)                         [P1-C-05 single source-of-truth]
  ├─ 9. filter_incomplete_identity(df, include=...)          [optional null-key suppression]
  ├─ 10. dedupe_by_key(df, keys=[...])                       [most-recent-by-modified_at policy]
  ├─ 11. column projection → PHASE_1_DEFAULT_COLUMNS
  └─ 12. _format_dataframe_response(df, format=request.format)   [JSON/CSV/Parquet]
```

---

## 3. Implementation Map

### File Responsibilities

| File | Responsibility |
|------|---------------|
| `src/autom8_asana/api/routes/exports.py` | Route registration (`exports_router_v1`, `exports_router_api_v1`), Pydantic contract (`ExportRequest`, `ExportOptions`), LEFT-PRESERVATION GUARD wrapper, `export_handler` orchestration logic, `PHASE_1_DEFAULT_COLUMNS`. |
| `src/autom8_asana/api/routes/_exports_helpers.py` | Pure DataFrame transforms and predicate helpers: `attach_identity_complete`, `filter_incomplete_identity`, `dedupe_by_key`, `apply_active_default_section_predicate`, `validate_section_values`, `translate_date_predicates`, `_walk_predicate` generic visitor, `DateTranslationResult`, `InvalidSectionError`. |
| `src/autom8_asana/api/models.py` | `ExportsSuccessResponse` — typed OpenAPI `response_model` declaration. |
| `src/autom8_asana/api/routes/_security.py` | `pat_router(prefix, tags)` and `s2s_router(prefix, tags)` factories used at `exports.py:221-228`. |
| `src/autom8_asana/api/main.py:431-441` | Mount-order-critical router registration (exports before query wildcard). |
| `src/autom8_asana/services/universal_strategy.py` | `get_universal_strategy(entity_type)` — returns strategy instance; `strategy._get_dataframe(project_gid, client)` is the actual DataFrame fetch path. |
| `src/autom8_asana/query/compiler.py` | `PredicateCompiler.compile(node, schema)` — compiles non-date predicates to `pl.Expr`. FROZEN per P1-C-04 (lines 53-63, 192-241). |
| `src/autom8_asana/query/models.py` | `PredicateNode`, `Comparison`, `AndGroup`, `OrGroup`, `NotGroup`, `Op` StrEnum (includes BETWEEN/DATE_GTE/DATE_LTE). |
| `src/autom8_asana/query/temporal.py` | `parse_date_or_relative(s)` — used by `_coerce_date_value` in `_exports_helpers.py` to parse ISO date strings and relative durations. |
| `src/autom8_asana/models/business/activity.py:282` | `PROCESS_PIPELINE_SECTIONS` — canonical section vocabulary source. |
| `src/autom8_asana/dataframes/models/registry.py` | `SchemaRegistry.get_instance().get_schema(pascal_entity_type)` — fetches schema for PredicateCompiler. |
| `src/autom8_asana/api/routes/dataframes.py` | `_format_dataframe_response(df, ...)` — shared format-negotiation function; called at step 12 with explicit `format=` kwarg. |
| `src/autom8_asana/services/errors.py` | `CacheNotWarmError` — raised when cache is cold; handler surfaces as 503. `UnknownEntityError` — raised when entity_type unknown; handler surfaces as 400. |

### Key Entry Points

**Route handlers** (thin wrappers into shared logic):
- `post_export_v1` at `exports.py:521` — S2S path (`/v1/exports`)
- `post_export_api_v1` at `exports.py:553` — PAT path (`/api/v1/exports`)

Both delegates unconditionally into `export_handler` at `exports.py:307`.

**Shared handler**:
- `export_handler(*, request_body, request_id, auth, entity_service, client)` at `exports.py:307` — 11-step orchestration pipeline.

**LEFT-PRESERVATION GUARD wrapper**:
- `_engine_call_with_left_preservation_guard(...)` at `exports.py:236` — wraps `strategy._get_dataframe()`.

**Predicate helpers** (all in `_exports_helpers.py`):
- `translate_date_predicates(predicate)` → `DateTranslationResult` — entry point for ESC-1.
- `_walk_predicate(node, *, on_comparison, default, combine)` at `_exports_helpers.py:209` — generic recursive visitor. Used by `predicate_references_field`, `_contains_date_op`, `validate_section_values`. NOT used by `_split_date_predicates` (requires structural mutation).
- `apply_active_default_section_predicate(predicate)` → `(new_predicate, default_applied: bool)`.

### Test Coverage

6 test files, 1488 total lines:

| Test File | What It Covers |
|-----------|----------------|
| `test_exports_contract.py` (243 lines) | `ExportRequest`/`ExportOptions` Pydantic contract: AC-12 no join/target_entity fields, AC-13 `extra="allow"` admits `predicate_join_semantics`, AC-15 no LazyFrame surface, AC-16 both routers exported, `PHASE_1_DEFAULT_COLUMNS` shape |
| `test_exports_handler.py` (298 lines) | End-to-end handler logic: LEFT-PRESERVATION GUARD wrapper invocation + log payload, mechanism (b) `predicate_join_semantics` forwarding, entity validation → ACTIVE-default → identity_complete → dedupe → CSV emission, dual-mount AP-3 guard |
| `test_exports_helpers.py` (359 lines) | Pure helper unit tests: `attach_identity_complete` (null-key AP-6 guard, missing columns), `filter_incomplete_identity`, `dedupe_by_key` (most-recent policy), `apply_active_default_section_predicate` (inject/bypass), `validate_section_values` (InvalidSectionError), `translate_date_predicates` (BETWEEN/DATE_GTE/DATE_LTE, OR/NOT rejection) |
| `test_exports_helpers_walk_predicate_property.py` (280 lines) | Property-based tests for `_walk_predicate` visitor correctness |
| `test_exports_format_negotiation.py` (206 lines) | Format negotiation: JSON/CSV/Parquet output, Accept header behavior, ESC-3 size measurement seam |
| `test_exports_auth_exclusion.py` (102 lines) | SCAR-WS8 regression: `/api/v1/exports/*` present in `jwt_auth_config.exclude_paths`; live middleware stack introspection |

---

## 4. Boundaries and Failure Modes

### What Is IN Scope (Phase 1)

- Single-entity exports only (`ExportRequest` has no `join` field — `extra="forbid"` at top level)
- Entities: any registered entity admissible; Phase 1 inception anchor is `"process"`
- Date operators: `BETWEEN`, `DATE_GTE`, `DATE_LTE` via ESC-1 translation (AND-level only)
- Standard predicate operators: all `PredicateCompiler`-supported ops (EQ, NEQ, GT, GTE, LT, LTE, IN, NOT_IN, CONTAINS, STARTS_WITH, ENDS_WITH, IS_NULL, IS_NOT_NULL)
- Output formats: `json` (default), `csv`, `parquet`
- Multi-project stacking: multiple `project_gids` are fetched, filtered independently, and `pl.concat`-ed with `diagonal_relaxed`
- Section vocabulary validation and ACTIVE-only default injection

### What Is OUT of Scope (Phase 1 → Phase 2)

- **LEFT JOINs**: `query/join.py` is frozen. The LEFT-PRESERVATION GUARD wrapper is a NO-OP in Phase 1. Cross-entity join exports are reserved for Phase 2 via `predicate_join_semantics: "allow-inner-rewrite"` mechanism.
- **`OR`/`NOT` date predicates (TRADE-010)**: Date operators (`BETWEEN`, `DATE_GTE`, `DATE_LTE`) under `OrGroup` or `NotGroup` raise `ValueError` (HTTP 400) at step 4. Restructure to top-level AND or remove. Rationale: AND-merging semantics cannot be preserved across OR/NOT boundaries without altering boolean logic.
- **LazyFrame consumer surface (P1-C-06)**: All transforms are eager `pl.DataFrame`. No LazyFrame pipeline is built or exposed.
- **Column projection extension**: The 7-column default set is intentionally minimal (DEFER-WATCH-2). Callers cannot currently request additional columns; Phase 4/5 concern.
- **`predicate_join_semantics` typed field**: Phase 2 reserved. In Phase 1 it is accessed via `model_extra` dict (`options.model_extra.get("predicate_join_semantics", "preserve-outer")`).

### Known Gaps

**OBS-EXPORTS-001 (OPEN, deadline 2026-06-15)**: The `/exports` route has **zero observability instrumentation** beyond log correlation:
- 0 metric counters/histograms (no `request_duration_seconds`, no `predicate_split_outcome`, no `format_negotiation_fallback_total`, no `identity_suppressed_count`)
- 0 explicit tracer spans (only auto-instrumentation via OTel FastAPI middleware)
- 0 SLO targets
- 0 alert rules

A regression in `_walk_predicate` or `translate_date_predicates` would only surface as 500s in production. Detection is 100% reactive. Owner-rite: SRE. Required signals documented in `.know/obs.md §OBS-EXPORTS-001`.

**SCAR-DISCRIMINATOR-001 (P3, no production path)**: `_predicate_discriminator` dict-only guard — `NotGroup(not_=AndGroup(...))` fails Pydantic validation when constructed via model-instance kwargs (not from dicts). No production code path triggers this. No fix at `8980bcd7`.

### Failure Scenarios

**ESC-1 (ValueError under OR/NOT date predicates)**
- Trigger: Caller passes `predicate: {"or": [{"field": "modified_at", "op": "DATE_GTE", "value": "2026-01-01"}, ...]}`.
- Path: `translate_date_predicates` → `_split_date_predicates` → detects date op under `OrGroup` → raises `ValueError`.
- Handler catch: `except ValueError as e: raise_api_error(request_id, 400, "malformed_predicate", str(e))`.
- User sees: HTTP 400 `error.code: "malformed_predicate"` with message explaining OR/NOT restriction.

**Mount-order silent failure (TENSION-009)**
- Trigger: `exports_router_v1` or `exports_router_api_v1` registered AFTER `query_router` in `api/main.py`.
- Symptom: Requests to `/v1/exports` silently match `query_router`'s wildcard `/v1/query/{entity_type}` with `entity_type="exports"` — returns unexpected `UnknownEntityError` or 400 instead of 404.
- No runtime assertion guards this. The constraint is enforced by comment only.

**Cache not warm (CacheNotWarmError → HTTP 503)**
- Trigger: DataFrame cache is cold for requested `entity_type` + `project_gid`.
- Path: `_engine_call_with_left_preservation_guard` → `strategy._get_dataframe()` returns `None` → raises `CacheNotWarmError`.
- Handler response: HTTP 503 `error.code: "CACHE_NOT_WARMED"` with `retry_after_seconds: 30`.

**Unknown entity type (HTTP 400)**
- Trigger: `entity_type` not registered in `EntityRegistry`.
- Path: `entity_service.validate_entity_type(entity_type)` → raises `UnknownEntityError`.
- Handler response: HTTP 400 `error.code: "unknown_entity_type"` with `available_entities`.

**Unknown section value (HTTP 400)**
- Trigger: Caller predicate references a `section` value not in `PROCESS_PIPELINE_SECTIONS`.
- Path: `validate_section_values(predicate)` → raises `InvalidSectionError`.
- Handler response: HTTP 400 `error.code: "unknown_section_value"` with the offending value.

**SCAR-WS8 / DEF-08 (now guarded by regression test)**
- Historical defect: `/api/v1/exports` was absent from `jwt_auth_config.exclude_paths`. JWT middleware rejected PAT-authenticated requests with 401 before the PAT handler fired.
- Fix: `api/main.py:381-388` — `/api/v1/exports/*` added to PAT-tag route-tree exclusion list.
- Guard: `test_exports_auth_exclusion.py` introspects live middleware stack to prevent regression.

~~**Idempotency finalize exception (SCAR-IDEM-001)**~~
~~- The route is annotated `x-fleet-idempotency: {idempotent: true, key_source: null}`. The `IdempotencyMiddleware` at `api/middleware/idempotency.py:719` has a known `finalize()` exception-swallow risk for any route it wraps. This is not exports-specific but applies to the exports surface.~~ **RESOLVED** `f795d7dc` #149 (W-IDEM, 2026-06-24): finalize bool now read; S2S callers get hard 500 at `idempotency.py:803-830` (R-IDEM-2). Stale anchor `:719` was replay-header code at tip.

### Interaction Points and Boundary Clarity

- **`query/compiler.py` (PredicateCompiler)**: Exports consumes the compiler READ-ONLY. The compiler's `OPERATOR_MATRIX` at lines 53-63 does NOT include `BETWEEN`/`DATE_GTE`/`DATE_LTE` — those are handled pre-compiler by `translate_date_predicates`. Any attempt to pass date-op nodes to the compiler will raise `InvalidOperatorError`.
- **`services/universal_strategy.py`**: `get_universal_strategy(entity_type)._get_dataframe(project_gid, client)` is the sole engine call path. This path returns an eager `pl.DataFrame`. The exports handler applies all post-load transforms (filter, identity_complete, dedupe, format) without touching the strategy internals.
- **`api/routes/dataframes.py`**: `_format_dataframe_response` is a shared utility imported by exports. The exports handler passes `format=request_body.format` explicitly (overriding Accept header negotiation); this is the ESC-3 measurement seam (row count and serialized size logged here).
- **`models/business/activity.py`**: `PROCESS_PIPELINE_SECTIONS` is the canonical section vocabulary. `_exports_helpers.py` derives `VALID_SECTIONS` and `ACTIVE_SECTIONS` from it at module load — if the vocabulary changes, the derived frozensets update automatically.

---

```metadata
confidence: 0.96
dimension_grades:
  purpose_and_design_rationale: A
  conceptual_model: A
  implementation_map: A
  boundaries_and_failure_modes: A
overall_grade: A
notes: >
  All four dimensions at A (95%+ completeness). Purpose grounded in TDD/PRD citations,
  rejected alternatives documented, tradeoffs explicit. Conceptual model covers all key
  types, invariants, and request-flow state machine. Implementation map anchors every
  step to file:line with test coverage mapping. Boundaries document both Phase 1 vs
  Phase 2 scope and all known failure paths (ESC-1, TENSION-009, CacheNotWarmError,
  OBS-EXPORTS-001, SCAR-WS8, SCAR-IDEM-001). One observable gap: OBS-EXPORTS-001
  (zero observability instrumentation) is documented as a known gap, not a knowledge gap.
```
