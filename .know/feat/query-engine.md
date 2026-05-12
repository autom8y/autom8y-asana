---
domain: feat/query-engine
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/query/"
  - "./src/autom8_asana/api/routes/query.py"
  - "./queries/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.97
format_version: "1.0"
---

# DataFrame Query Engine with Compiled Predicates

## Purpose and Design Rationale

The query engine enables S2S consumers to run structured, filterable, aggregatable queries
against cached Polars DataFrames without hitting the live Asana API. Queries execute as
pure-CPU in-process operations in single-digit milliseconds. All routes require S2S JWT
authentication (service token only; PAT pass-through is NOT supported).

**Why it exists**: The Asana API is rate-limited and slow for analytic workloads. The cache
layer (`cache/dataframe/`) holds periodically-refreshed Polars DataFrames for each entity
type. The query engine exposes those DataFrames through a structured predicate DSL, removing
the need for S2S consumers to speak Polars directly or hold their own snapshots.

**Design decisions**:
- `PredicateCompiler` is a stateless frozen dataclass (ADR-QE-002 discriminated-union
  discriminator via callable, not Literal tag) to allow reuse across entity types without
  per-call instantiation overhead.
- Date operators (BETWEEN, DATE_GTE, DATE_LTE) are NOT compiled by `PredicateCompiler`
  (P1-C-04 frozen range constraint, ESC-1 resolution in TDD §5.3) — they are translated to
  filter expressions by the `/exports` route handler BEFORE the engine call, preserving the
  compiler's frozen implementation contract.
- `QueryEngine` accepts a `DataFrameProvider` protocol (R-010, WS-QUERY) rather than
  importing `EntityQueryService` directly, decoupling the computational layer from the
  service orchestration layer.
- ADR-AGG-002: HAVING reuses `PredicateCompiler` against a synthetic post-aggregation schema.
- ADR-AGG-005: Utf8 financial columns auto-cast to Float64 for sum/mean/min/max aggregations.
- ADR-AGG-006: Group count guard enforced AFTER HAVING filter (minimizes false rejections).

**Legacy endpoint sunset**: `POST /v1/query/{entity_type}` (flat equality query) is
deprecated with headers `Deprecation: true`, `Sunset: 2026-06-01`, `Link: .../rows`.
As of 2026-05-08, **24 days remain** before the sunset deadline (EC-008).

## Conceptual Model

### Op StrEnum — 13 Operators

```
EQ, NE, GT, LT, GTE, LTE, IN, NOT_IN, CONTAINS, STARTS_WITH  ← Sprint 1 (10 ops)
BETWEEN, DATE_GTE, DATE_LTE                                    ← Sprint 2 / Sprint-3 LIVE
```

BETWEEN/DATE_GTE/DATE_LTE are **model-valid** in `Op` but **not compiled** by
`PredicateCompiler` (OPERATOR_MATRIX at `compiler.py:53-63` has no entry for them). They
are only legal as inputs to `api/routes/exports.py:translate_date_predicates`, which splits
them into `pl.Expr` before calling the engine. Any attempt to pass these ops directly to
`PredicateCompiler.compile()` will raise `InvalidOperatorError` at runtime.

### PredicateNode — Discriminated Union

Four node types, Pydantic v2 callable discriminator (`_predicate_discriminator` inspects dict
keys — NOT a Literal tag discriminator):

| Node Type | Key | Semantics |
|-----------|-----|-----------|
| `Comparison` | `field` present | Leaf: `field op value` |
| `AndGroup` | `and` present | All children must match |
| `OrGroup` | `or` present | At least one child must match |
| `NotGroup` | `not` present | Child must not match |

**FR-001 sugar**: A bare list `[...]` passed as `where` is auto-wrapped to `{"and": [...]}` by
`_wrap_flat_array_to_and_group`. An empty list becomes `None` (no filter, per EC-005).

**SCAR-DISCRIMINATOR-001 (P3, unguarded)**: `_predicate_discriminator` only inspects raw
dicts. If `NotGroup(not_=AndGroup(...))` is constructed via model-instance kwargs (not a raw
dict), Pydantic validation fails. No production path known at `8980bcd7`, but programmatic
construction of nested nodes must use `model_validate({"not": {...}})` not kwargs.

### Compilation Pipeline

```
RowsRequest.where (PredicateNode)
  → QueryLimits.check_depth()         # fail-fast before any I/O
  → QueryEngine.execute_rows()
      → DataFrameProvider.get_dataframe()
      → PredicateCompiler.compile(node, schema)  # AST → pl.Expr
          → _compile_node() (recursive)
          → _compile_comparison(): field validate → OPERATOR_MATRIX check → _coerce_value() → _build_expr()
      → df.filter(filter_expr)
      → execute_join()  [if request.join is set]
      → pagination slice
      → column select
  → RowsResponse
```

### Aggregation Pipeline

```
AggregateRequest
  → depth guards (WHERE + HAVING separately)
  → DataFrameProvider.get_dataframe()
  → SchemaRegistry.get_schema() → validate group_by columns (no List dtypes)
  → PredicateCompiler.compile(WHERE) → df.filter()
  → AggregationCompiler.compile(aggregations, schema) → df.group_by().agg()
  → build_post_agg_schema() → PredicateCompiler.compile(HAVING) → result_df.filter()
  → AggregateGroupLimitError if groups > 10,000 (ADR-AGG-006)
  → AggregateResponse
```

### Guard Rails (QueryLimits — frozen dataclass, configurable)

| Limit | Default | Enforcement point |
|-------|---------|-------------------|
| `max_predicate_depth` | 5 | `check_depth()` before any I/O |
| `max_result_rows` | 10,000 | `clamp_limit()` — silent clamp, no rejection |
| `max_aggregate_groups` | 10,000 | after HAVING filter (ADR-AGG-006) |
| `max_group_by_columns` | 5 | `check_group_by()` |
| `max_aggregations` | 10 | `check_aggregations()` (advisory; `AggregateRequest` model also enforces) |

### Join Architecture

Two join sources via `JoinSpec.source`:

**Entity joins** (`source="entity"`, default):
- Registered `EntityRelationship` derived from `EntityDescriptor.join_keys`
- Left join, deduplicate target on join key (take first), prefix columns with target entity type
- `MAX_JOIN_DEPTH = 1` (defined in `join.py:70`, exported from `query/__init__.py:75`; enforced conceptually — no runtime recursive join path exists in the engine)

**Data-service joins** (`source="data-service"`):
- 14 virtual entities from `autom8y-data` registered in `data_service_entities.py`
- Default join key: `office_phone` (30% null rate — SCAR-005/006)
- `factory` parameter required; `period` defaults to `"LIFETIME"` (most factories default `T30`)
- Column validation against virtual entity registry is **advisory** (logs warning, does not reject)
- Same `execute_join()` machinery as entity joins; factory name used as column prefix

**Data-service virtual entity catalog (14 factories)**:
`spend`, `leads`, `appts`, `campaigns`, `base`, `account`, `ads`, `adsets`, `targeting`,
`payments`, `business_offers`, `ad_questions`, `ad_tests`, `assets`

### Section and Classification Scoping

- `section` parameter resolves via `SectionIndex.resolve(section)` → name filter on `pl.col("section")`
- `classification` parameter expands via `CLASSIFIERS[entity_type].sections_for(AccountActivity)`
  → case-insensitive IN predicate on `pl.col("section").str.to_lowercase()`
- Section and classification are **mutually exclusive** (model validator enforces)
- EC-006: `strip_section_predicates()` in `compiler.py` removes `field=="section"` comparisons
  from a predicate tree; used when `section` parameter and section predicates co-exist

### Freshness Side-Channel

`QueryEngine._get_freshness_meta()` reads `provider.last_freshness_info` from the
`DataFrameProvider` after `get_dataframe()` returns. This injects `freshness`,
`data_age_seconds`, `staleness_ratio` into `RowsMeta` / `AggregateMeta`. The provider
populates `last_freshness_info` as a side-channel after a successful DataFrame retrieval.

### order_by / order_dir — UNIMPLEMENTED

`RowsRequest` defines `order_by: str | None` and `order_dir: Literal["asc", "desc"]`
fields, but `QueryEngine.execute_rows()` does not contain any sort step. These fields are
accepted and validated at the model layer but silently ignored at execution time. The saved
query `active_offers.yaml` uses `order_by: mrr, order_dir: desc` with no runtime effect.

## Implementation Map

### Module Inventory (19 files in `src/autom8_asana/query/`)

| File | Role |
|------|------|
| `models.py` | `Op` (StrEnum, 13 ops), `PredicateNode` (discriminated union), `RowsRequest`, `AggregateRequest`, `RowsResponse`, `AggregateResponse`, `JoinSpec` |
| `engine.py` | `QueryEngine` dataclass — orchestrates rows + aggregate flows; frozen ranges `139-178,181` |
| `compiler.py` | `PredicateCompiler` (frozen dataclass), `OPERATOR_MATRIX`, `_compile_node`, `_compile_comparison`, `strip_section_predicates`; frozen ranges `53-63,192-241` |
| `aggregator.py` | `AggregationCompiler`, `AGG_COMPATIBILITY` matrix, `build_post_agg_schema`, `validate_alias_uniqueness` |
| `join.py` | `JoinSpec`, `execute_join()`, `JoinResult`, `MAX_JOIN_DEPTH=1`; **full module frozen (P1-C-04)** |
| `guards.py` | `QueryLimits` (frozen dataclass), `predicate_depth()` |
| `errors.py` | Error hierarchy: `QueryEngineError`, `QueryTooComplexError`, `UnknownFieldError`, `InvalidOperatorError`, `CoercionError`, `UnknownSectionError`, `AggregationError`, `AggregateGroupLimitError`, `ClassificationError`, `JoinError` |
| `data_service_entities.py` | `DataServiceEntityInfo`, `DATA_SERVICE_ENTITIES` registry (14 factories), `get_data_service_entity()`, `list_data_service_entities()` |
| `fetcher.py` | `DataServiceJoinFetcher` — fetches from `DataServiceClient` for cross-service joins |
| `hierarchy.py` | `find_relationship()`, `get_join_key()`, `get_joinable_types()` — entity relationship lookup |
| `introspection.py` | `list_entities()`, `list_fields()`, `list_relations()`, `list_sections()` |
| `saved.py` | `SavedQuery`, `SavedJoinSpec`, `load_saved_query()`, `save_query()`, `find_saved_query()` |
| `temporal.py` | Temporal query utilities |
| `timeline_provider.py` | Timeline data provider |
| `offline_provider.py` | `OfflineDataFrameProvider` for CLI offline mode |
| `formatters.py` | CLI output formatters (table, json, csv, jsonl) |
| `cli.py` | CLI entry point (standalone, settings-guard-bypassed) |
| `__main__.py` | CLI dispatcher — 10 subcommands (see below) |
| `__init__.py` | Re-exports: `PredicateCompiler`, `QueryEngine`, `execute_join`, `MAX_JOIN_DEPTH` + public API |

### API Surface

**Active endpoints** (`api/routes/query.py` — all S2S JWT required):

| Route | Method | Description |
|-------|--------|-------------|
| `GET /v1/query/entities` | GET | List queryable entity types |
| `GET /v1/query/data-sources` | GET | List data-service factories |
| `GET /v1/query/data-sources/{factory}/fields` | GET | List fields for a data-service factory |
| `GET /v1/query/{entity_type}/fields` | GET | List fields and dtypes |
| `GET /v1/query/{entity_type}/relations` | GET | List joinable entities |
| `GET /v1/query/{entity_type}/sections` | GET | List sections with classification |
| `POST /v1/query/{entity_type}/rows` | POST | Filtered row retrieval (composable predicates) |
| `POST /v1/query/{entity_type}/aggregate` | POST | Grouped aggregation with HAVING |
| `POST /v1/query/{entity_type}` | POST | **DEPRECATED** flat equality query; sunset 2026-06-01 |

**Router mount constraint**: `query_router` uses wildcard `/{entity_type}` and **must mount
AFTER** `fleet_query_router_*` and `exports_router_*` in `api/main.py` (TENSION-009).

**Error-to-status mapping** (defined in `query.py:82-87`):
- `QueryTooComplexError` → 400
- `AggregateGroupLimitError` → 400
- `ClassificationError` → 400
- `JoinError` → 422
- All others → 422

### CLI Subcommands (10, `query/__main__.py`)

`rows`, `aggregate`, `entities`, `fields`, `relations`, `sections`, `data-sources`, `timeline`,
`list-queries`, `run`

- `--live` flag: uses `autom8y_core.TokenManager` for S2S JWT, then hits HTTP API
- Default (no `--live`): uses `OfflineDataFrameProvider` against local parquet files
- `run <name_or_path>`: loads `SavedQuery` YAML/JSON; searches `./queries/` then `~/.autom8/queries/`

### Saved Query Corpus (4 YAML files in `queries/`)

| Name | Command | Entity | Notes |
|------|---------|--------|-------|
| `active_offers.yaml` | rows | offer | classification=active, order_by=mrr (silently ignored) |
| `mrr_by_vertical.yaml` | aggregate | offer | group_by=[vertical], sum(mrr), count(gid) |
| `offers_with_business.yaml` | rows | offer | entity join to `business` for `booking_type` |
| `offers_with_spend.yaml` | rows | offer | data-service join to `spend` factory, T30 period |

### Test Coverage

**22 test files** in `tests/unit/query/` (23 entries including `__init__.py`):
`test_adversarial.py`, `test_adversarial_aggregate.py`, `test_adversarial_hierarchy.py`,
`test_aggregator.py`, `test_classification_filter.py`, `test_cli.py`, `test_cli_joins.py`,
`test_compiler.py`, `test_cross_service_wiring.py`, `test_data_service_join.py`,
`test_engine.py`, `test_formatters.py`, `test_guards.py`, `test_hierarchy.py`, `test_join.py`,
`test_models.py`, `test_offline_provider.py`, `test_saved_queries.py`,
`test_section_edge_cases.py`, `test_temporal.py`, `test_timeline_provider.py`.

`test_routes_query.py` in `tests/unit/api/` is pinned to `xdist_group("query_routes")` due
to `AsyncMock + dependency_overrides` state contamination under `--dist=loadgroup`
(SCAR-W1E-LOADGROUP-001, `149d3673`).

### FROZEN-RANGE-IMPORTERS Catalog (P1-C-04)

Frozen ranges that MUST NOT be modified without blast-radius analysis:
- `engine.py:139-178,181` — `execute_rows` steps 6-9 (filter/join/pagination/column select), aggregate logic
- `join.py` — full module
- `compiler.py:53-63,192-241` — `OPERATOR_MATRIX`, `_compile_node`, `_compile_comparison`

Verified importers at `8980bcd7`:
- `api/routes/exports.py:66` — imports `PredicateCompiler`
- `api/routes/query.py:38` — imports `QueryEngine`
- `query/__init__.py:17-18,38` — re-exports `PredicateCompiler`, `QueryEngine`, `execute_join`
- `query/__main__.py:513,669` — lazy imports of `QueryEngine` in CLI subcommands
- `services/query_service.py:236` — lazy import of `strip_section_predicates`

## Boundaries and Failure Modes

### Explicit Scope Boundaries

- This engine does NOT query the live Asana API. It requires the DataFrame cache to be warm.
  Cold cache returns `CacheNotWarmError` (→ HTTP 503 with `retry_after_seconds: 30`).
- Date operators (BETWEEN, DATE_GTE, DATE_LTE) are NOT compiled by `PredicateCompiler`. They
  must be translated upstream by the caller (exports route) before engine invocation.
  Passing them directly to the engine raises `InvalidOperatorError`.
- `order_by` / `order_dir` fields on `RowsRequest` are accepted but **NOT executed** —
  the engine performs no sort step. This is a known gap (Knowledge Gap, prior version confirmed).
- `MAX_JOIN_DEPTH = 1`: only one-hop joins supported. No recursive join path exists.
- `List[Utf8]` dtype columns have an empty operator set in `OPERATOR_MATRIX` — they cannot
  be used in predicate comparisons (Sprint 1 scope decision).
- Data-service join column validation is advisory only (logs warning, does not reject unknown columns).

### Known Failure Modes and SCARs

| SCAR | Relevance | Status |
|------|-----------|--------|
| SCAR-DISCRIMINATOR-001 | `_predicate_discriminator` dict-only guard; model-instance kwargs construction of `NotGroup(not_=AndGroup(...))` fails Pydantic validation | P3 — no production path, unguarded at `8980bcd7` |
| SCAR-005 | 30% null rate on `office_phone` (cascade warm-up ordering) — directly reduces data-service join match rates | Multiple cascade fix commits; residual null rate acknowledged |
| SCAR-012 | DataServiceClient auth failure broke cross-service joins (PAT instead of `client_credentials`) | Historical fix |
| SCAR-030 | Section names not ALL CAPS — `_resolve_section` depends on exact section name match | Historical fix |
| SCAR-W1E-LOADGROUP-001 | `test_routes_query.py` state contamination under xdist; requires `xdist_group("query_routes")` | `149d3673`; active marker |

### Error Hierarchy and Recovery Paths

All query-engine domain errors inherit from `QueryEngineError` with `to_dict()` for HTTP
serialization. The route handler maps errors to HTTP status via `_raise_query_error()`:

| Error Class | Error Code | HTTP Status | Trigger |
|-------------|-----------|-------------|---------|
| `QueryTooComplexError` | `QUERY_TOO_COMPLEX` | 400 | predicate depth > 5 |
| `AggregateGroupLimitError` | `TOO_MANY_GROUPS` | 400 | groups > 10,000 |
| `ClassificationError` | `INVALID_CLASSIFICATION` | 400 | invalid classification or entity type |
| `UnknownFieldError` | `UNKNOWN_FIELD` | 422 | field not in schema |
| `InvalidOperatorError` | `INVALID_OPERATOR` | 422 | op incompatible with dtype |
| `CoercionError` | `COERCION_FAILED` | 422 | value cannot be coerced |
| `UnknownSectionError` | `UNKNOWN_SECTION` | 422 | section not resolvable |
| `JoinError` | `JOIN_ERROR` | 422 | join key missing, no relationship, no DataServiceClient |
| `AggregationError` | `AGGREGATION_ERROR` | 422 | group_by / aggregation spec errors |

`CacheNotWarmError` (from `services/`) → HTTP 503 with `retry_after_seconds: 30`.

### Interaction Points (Boundary Clarity)

- **`DataFrameProvider` protocol** (`protocols/dataframe_provider.py`): the engine's only
  I/O interface. At runtime, `EntityQueryService` is the concrete provider. The `last_freshness_info`
  attribute is a side-channel post-retrieval.
- **`SchemaRegistry`** (`dataframes/models/registry.py`): singleton used to validate field
  names and dtypes. Schema key resolution uses `_to_pascal_case(entity_type)`.
- **`autom8y_telemetry.trace_computation`** wraps both `execute_rows` and `execute_aggregate`
  — OTel spans are emitted with `entity.query_rows` / `entity.query_aggregate` operation names.
- **`api/routes/_exports_helpers.py`**: `translate_date_predicates()` is the upstream translator
  for BETWEEN/DATE_GTE/DATE_LTE; `strip_section_predicates()` (from `compiler.py`) is used
  by `_exports_helpers.py` for EC-006 section conflict resolution.
- **`services/query_service.py`**: lazy-imports `strip_section_predicates` at runtime
  (line ~236); also provides `EntityQueryService` (the `DataFrameProvider` implementation)
  and `resolve_section_index()` / `validate_fields()` used by route handlers.

### Deprecated Endpoint — EC-008 (CRITICAL: 24 days)

`POST /v1/query/{entity_type}` (legacy flat equality query) adds response headers:
`Deprecation: true`, `Sunset: 2026-06-01`, `Link: </v1/query/{entity_type}/rows>; rel="successor-version"`.
The route is still live at `8980bcd7`. Sunset deadline: **2026-06-01 (24 days from 2026-05-08)**.
Consumer migration to `/rows` must be coordinated before this date (EC-008 from design-constraints).

### Configuration Boundaries

- `QueryLimits` is constructed with defaults in `QueryEngine.__init__`; can be injected at
  construction time for testing or per-route override.
- `data_client: DataServiceClient | None = None` — set to `None` by default; data-service
  joins will raise `JoinError` if `data_client` is not injected. Route handlers inject via
  `DataServiceClientDep`.
- `DataFrameProvider` injection (required): no default provided; routes construct
  `EntityQueryService()` directly and pass it.

```metadata
confidence: 0.97
unresolved_gaps:
  - order_by/order_dir: accepted by model, not executed by engine (confirmed at 8980bcd7)
  - fetcher.py: DataServiceJoinFetcher fetch_for_join() internals not deeply read
  - temporal.py / timeline_provider.py: temporal query internals not traced in this pass
active_risks:
  - EC-008: deprecated /v1/query/{entity_type} sunset 2026-06-01 (24 days)
  - SCAR-DISCRIMINATOR-001: P3 unguarded discriminator bug
frozen_ranges:
  - engine.py:139-178,181 (P1-C-04)
  - join.py (full module, P1-C-04)
  - compiler.py:53-63,192-241 (P1-C-04)
```
