---
domain: feat/query-engine
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/query/**/*.py"
  - "./src/autom8_asana/api/routes/query.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# DataFrame Query Engine with Compiled Predicates

## Purpose and Design Rationale

The query engine enables S2S consumers to run structured, filterable, aggregatable queries against cached Polars DataFrames without hitting the live Asana API. Queries execute as pure-CPU in-process operations in single-digit milliseconds. All routes are S2S JWT authenticated.

## Conceptual Model

### Predicate AST

Four node types: `Comparison` (leaf: field, op, value), `AndGroup`, `OrGroup`, `NotGroup`. 10 operators: eq, ne, gt, lt, gte, lte, in, not_in, contains, starts_with. Bare list of comparisons auto-wraps to `AndGroup` (FR-001 sugar).

### Compilation Pipeline

Request -> Pydantic validation -> `PredicateCompiler.compile()` -> `pl.Expr` -> `df.filter(expr)`. The compiler is stateless (frozen dataclass). Value coercion handles datetime, numeric, and string types.

### Aggregation

Six functions: sum, count, mean, min, max, count_distinct. HAVING support reuses `PredicateCompiler` against a synthetic post-aggregation schema (ADR-AGG-002). Utf8 financial columns auto-cast to Float64 (ADR-AGG-005).

### Guard Rails

`QueryLimits`: max_predicate_depth=5, max_result_rows=10000, max_aggregate_groups=10000, max_group_by_columns=5, max_aggregations=10.

### Join Architecture

**Entity joins**: Registered `EntityRelationship` derived from `EntityDescriptor.join_keys`. Left join, dedup, prefix columns.
**Data-service joins**: 14 virtual entities from `autom8y-data` via `DataServiceJoinFetcher`. Join key: `office_phone`.

## Implementation Map

18 files in `src/autom8_asana/query/`: engine.py, models.py, compiler.py, aggregator.py, guards.py, errors.py, join.py, hierarchy.py, fetcher.py, data_service_entities.py, introspection.py, saved.py, temporal.py, formatters.py, offline_provider.py, timeline_provider.py, cli.py. Plus `api/routes/query.py`.

### API Surface

| Route | Method | Description |
|-------|--------|-------------|
| `/v1/query/entities` | GET | List queryable entity types |
| `/v1/query/{entity_type}/fields` | GET | List fields and dtypes |
| `/v1/query/{entity_type}/rows` | POST | Filtered row retrieval |
| `/v1/query/{entity_type}/aggregate` | POST | Grouped aggregation |

**22 test files** in `tests/unit/query/`.

## Boundaries and Failure Modes

- **SCAR-012**: DataServiceClient auth failure broke cross-service joins
- **SCAR-030**: Classifier section names invented, fixed to ALL CAPS
- **SCAR-005/006**: 30% null rate in office_phone affects join match rates

## Knowledge Gaps

1. `order_by`/`order_dir` execution path may be unimplemented.
2. `MAX_JOIN_DEPTH=1` enforcement not found at runtime.
3. Legacy `/v1/query/{entity_type}` deprecated endpoint (sunset 2026-06-01) not read.
