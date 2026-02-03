# TDD: /aggregate Endpoint + AggSpec (Sprint 2, Cycle 2)

## Metadata

| Field | Value |
|-------|-------|
| **TDD ID** | TDD-aggregate-endpoint |
| **PRD** | PRD-dynamic-query-service (FR-005) |
| **Status** | Draft |
| **Created** | 2026-02-03 |
| **Author** | Architect |
| **Sprint** | 2, Cycle 2 |
| **Scope** | `/aggregate` endpoint, AggSpec model, HAVING clause, engine integration |
| **Depends On** | TDD-dynamic-query-service (Sprint 1, COMPLETE), TDD-hierarchy-index (Sprint 2 Cycle 1, COMPLETE) |

---

## 1. System Context

### 1.1 What We Are Building

A grouped aggregation endpoint `POST /v1/query/{entity_type}/aggregate` that computes aggregated values over cached DataFrames. The endpoint supports:

- **AggSpec**: A `{column, function, alias}` model that defines a single aggregation.
- **GROUP BY**: Group results by 1-5 columns before aggregation.
- **WHERE**: Pre-aggregation row filtering using the same `PredicateNode` tree from Sprint 1.
- **HAVING**: Post-aggregation group filtering using `PredicateNode` that references alias names.
- **Section scoping**: Same section-parameter-to-name-filter behavior as `/rows`.

### 1.2 Architectural Position

```
                 +-----------------+
                 |   API Gateway   |
                 |  (S2S JWT Auth) |
                 +--------+--------+
                          |
           +--------------+--------------+
           |              |              |
  POST /rows      POST /aggregate     POST /metric
  (Sprint 1)      (THIS SPRINT)       (Sprint 3)
           |              |
           v              v
  +------------------+  +-------------------+
  | QueryEngine      |  | QueryEngine       |
  | .execute_rows()  |  | .execute_aggregate|
  |   |              |  |   |               |
  |   +-- Compiler   |  |   +-- Compiler    |
  |   +-- SectionIdx |  |   +-- SectionIdx  |
  |   +-- Join       |  |   +-- AggCompiler |
  +--------+---------+  +--------+----------+
           |                      |
           +-------+--------------+
                   |
                   v
        +---------------------+
        | EntityQueryService   |
        | .get_dataframe()     |
        +---------------------+
```

### 1.3 Key Design Constraint: Financial Columns Are Utf8

The Offer schema stores `mrr`, `cost`, and `weekly_ad_spend` as `Utf8` dtype (string-encoded numbers). The existing `MetricExpr` handles this by casting to `Float64` before aggregation via `col.cast(pl.Float64, strict=False)`. The `/aggregate` endpoint must follow the same pattern: when a consumer requests `sum` or `mean` on a Utf8 column, the aggregation compiler casts to `Float64` before applying the aggregation function.

This is not optional. Without the cast, `sum("mrr")` would attempt string concatenation or raise a Polars type error. The `strict=False` parameter ensures non-numeric strings become null rather than raising, consistent with MetricExpr behavior.

---

## 2. Architecture Decisions

### ADR-AGG-001: Aggregation Compilation Module -- New `query/aggregator.py`

**Context**: Aggregation expression building could live in `compiler.py` (alongside predicates) or in a new `aggregator.py`.

**Decision**: New `query/aggregator.py` module.

**Rationale**: Predicate compilation and aggregation compilation are distinct concerns. `compiler.py` transforms a recursive AST into filter expressions; `aggregator.py` transforms a flat list of AggSpec into aggregation expressions. Combining them would bloat `compiler.py` and confuse the single-responsibility boundary. A separate module also makes it clear where to add future aggregation features (windowed aggregations, percentiles, etc.).

**Consequences**: One additional file in the `query/` package. Imports are straightforward. No circular dependency risk since `aggregator.py` imports from `models.py` and `errors.py` (no back-imports).

### ADR-AGG-002: HAVING Reuses PredicateCompiler via Synthetic Schema

**Context**: HAVING filters operate on aggregated output columns (aliases), not the original entity columns. The PredicateCompiler validates fields against a `DataFrameSchema`. Options: (A) Add a "skip validation" mode to PredicateCompiler, (B) Build a synthetic schema from the aggregation output and pass it to the compiler, (C) Write a separate HAVING compiler.

**Decision**: (B) Build a synthetic `DataFrameSchema` from `build_post_agg_schema()` and pass it to the existing `PredicateCompiler.compile()`.

**Rationale**: The PredicateCompiler already handles all the operator validation, coercion, and expression building we need. The only issue is that it validates field names against a schema -- and for HAVING, the "schema" is the aggregated output. By constructing a `DataFrameSchema` whose columns are the group_by keys and aggregation aliases (with inferred dtypes), we get full validation for free. Option (A) would remove safety. Option (C) duplicates code.

**Consequences**: `build_post_agg_schema()` must correctly infer output dtypes for each aggregation function. This is straightforward (count->Int64, mean->Float64, sum/min/max->same as input, with Utf8 becoming Float64 after cast). If dtype inference is wrong, HAVING filters may produce coercion errors -- but this is caught in unit testing.

### ADR-AGG-003: count_distinct Extension Beyond PRD

**Context**: The PRD FR-005 lists supported agg values as `sum, count, mean, min, max`. The task specification adds `count_distinct`.

**Decision**: Include `count_distinct` in `AggFunction` enum.

**Rationale**: `count_distinct` is one of the most common analytical aggregation functions. It maps trivially to Polars `n_unique()`. Omitting it would force consumers to fetch all rows and deduplicate client-side, negating the purpose of the aggregation endpoint. The implementation cost is a single enum value and one `match` arm.

**Consequences**: The `AggFunction` enum has 6 values instead of the PRD's 5. The PRD should be annotated with a reference to this decision.

### ADR-AGG-004: AggSpec Field Name -- `function` Not `agg`

**Context**: The PRD uses `"agg"` as the AggSpec field name. The existing `MetricExpr` also uses `agg`. However, `agg` is overloaded with Polars' `.agg()` method and less self-documenting for API consumers.

**Decision**: Use `function` as the field name in AggSpec.

**Rationale**: `function` is immediately self-documenting: "what aggregation function to apply." `agg` is ambiguous -- it could mean the aggregation operation, the aggregation result, or the Polars method. The API schema documentation will be the source of truth, not the PRD field name suggestion.

**Consequences**: API consumers use `"function": "sum"` instead of `"agg": "sum"`. Internal code uses the `AggFunction` enum for type safety.

### ADR-AGG-005: Utf8 Columns Permitted for Numeric Aggregations (With Cast)

**Context**: Financial columns (`mrr`, `cost`, `weekly_ad_spend`) are stored as Utf8 in the schema. Should `sum(mrr)` be rejected or should we cast transparently?

**Options Considered**:
1. **Reject Utf8 for sum/mean**: Fail-fast, but useless for the primary aggregation use case.
2. **Cast Utf8 to Float64 transparently**: Follows MetricExpr precedent, enables the primary use case.
3. **Require explicit cast parameter**: Adds API complexity for a universal need.

**Decision**: Option 2 -- Cast Utf8 to Float64 transparently for sum/mean/min/max.

**Rationale**: The entire purpose of `/aggregate` on the Offer entity is to `sum(mrr) group by vertical`. If we reject this, the endpoint is useless for its primary audience. `MetricExpr.to_polars_expr()` already does `col.cast(pl.Float64, strict=False)` before aggregation. We follow the same pattern. Non-numeric strings become null; Polars aggregations ignore nulls by default.

**Consequences**:
- The AGG_FUNCTION_MATRIX allows Utf8 for sum/mean/min/max.
- The aggregation compiler inserts `.cast(pl.Float64, strict=False)` for Utf8 columns with numeric aggregations.
- Output dtype for Utf8 aggregations is Float64 (used in HAVING schema).
- `count` and `count_distinct` on Utf8 do NOT cast (they count values, not compute numerics).

### ADR-AGG-006: No Pagination, Group Count Guard

**Context**: The PRD states "Full result returned (no pagination)." Should we add a guard for maximum groups?

**Decision**: No pagination. Add a `max_aggregate_groups = 10_000` guard that rejects queries producing more groups than the limit.

**Rationale**: GROUP BY on high-cardinality columns (e.g., `gid`) could produce as many groups as rows. Returning 10,000+ group rows in a single response is a misuse of the aggregation endpoint. The 10,000 limit matches `max_result_rows` from the rows endpoint. The check happens after grouping but before serialization, so we can count groups cheaply.

**Consequences**: A new `AggregateGroupLimitError` if groups exceed the limit. The response always returns all groups (up to the limit).

---

## 3. Module Structure

### 3.1 New Files

```
src/autom8_asana/query/
    aggregator.py        # AggregationCompiler, AGG_FUNCTION_MATRIX, build_post_agg_schema

tests/unit/query/
    test_aggregator.py   # Aggregation compilation, dtype validation, HAVING schema
    test_aggregate.py    # QueryEngine.execute_aggregate() with mocked services

tests/api/
    test_routes_query_aggregate.py   # End-to-end /aggregate via TestClient
```

### 3.2 Modified Files

```
src/autom8_asana/query/
    models.py         # + AggFunction, AggSpec, AggregateRequest, AggregateMeta, AggregateResponse
    engine.py         # + QueryEngine.execute_aggregate()
    guards.py         # + max_aggregate_groups, check_group_by, check_aggregations
    errors.py         # + AggregationError, AggregateGroupLimitError
    __init__.py       # + export new public API

src/autom8_asana/api/routes/
    query_v2.py       # + POST /{entity_type}/aggregate route handler
```

### 3.3 Unmodified Files

| File | Reason |
|------|--------|
| `query/compiler.py` | Reused as-is for WHERE and HAVING compilation |
| `query/hierarchy.py` | Not relevant for aggregate |
| `query/join.py` | Not relevant for aggregate |
| `services/query_service.py` | `get_dataframe()` already provides what we need |

---

## 4. Pydantic Model Definitions

### 4.1 AggFunction Enum (`query/models.py`)

```python
class AggFunction(str, Enum):
    """Supported aggregation functions for /aggregate endpoint."""

    SUM = "sum"
    COUNT = "count"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    COUNT_DISTINCT = "count_distinct"
```

### 4.2 AggSpec Model (`query/models.py`)

```python
class AggSpec(BaseModel):
    """Single aggregation specification.

    Defines what column to aggregate, which function to apply,
    and what to name the output.

    Example: {"column": "mrr", "function": "sum", "alias": "total_mrr"}
    """

    model_config = ConfigDict(extra="forbid")

    column: str
    function: AggFunction
    alias: str | None = None

    @property
    def resolved_alias(self) -> str:
        """Return alias, or generate default from function + column."""
        if self.alias is not None:
            return self.alias
        return f"{self.function.value}_{self.column}"
```

### 4.3 AggregateRequest Model (`query/models.py`)

```python
class AggregateRequest(BaseModel):
    """POST /v1/query/{entity_type}/aggregate request body."""

    model_config = ConfigDict(extra="forbid")

    where: PredicateNode | None = None
    section: str | None = None
    group_by: list[str] = Field(min_length=1, max_length=5)
    aggregations: list[AggSpec] = Field(min_length=1, max_length=10)
    having: PredicateNode | None = None

    @field_validator("where", mode="before")
    @classmethod
    def wrap_flat_array(cls, v: Any) -> Any:
        """Auto-wrap bare list to AND group (reuse FR-001 sugar)."""
        if isinstance(v, list):
            if len(v) == 0:
                return None
            return {"and": v}
        return v

    @field_validator("having", mode="before")
    @classmethod
    def wrap_having_flat_array(cls, v: Any) -> Any:
        """Auto-wrap bare list HAVING to AND group."""
        if isinstance(v, list):
            if len(v) == 0:
                return None
            return {"and": v}
        return v
```

### 4.4 Response Models (`query/models.py`)

```python
class AggregateMeta(BaseModel):
    """Response metadata for /aggregate endpoint."""

    model_config = ConfigDict(extra="forbid")

    group_count: int
    aggregation_count: int
    group_by: list[str]
    entity_type: str
    project_gid: str
    query_ms: float


class AggregateResponse(BaseModel):
    """Response body for /aggregate endpoint."""

    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]
    meta: AggregateMeta
```

---

## 5. Aggregation Function/Dtype Validation Matrix

### 5.1 The Matrix

| Dtype | sum | count | mean | min | max | count_distinct |
|-------|:---:|:-----:|:----:|:---:|:---:|:--------------:|
| **Utf8** | Y* | Y | Y* | Y* | Y* | Y |
| **Int64** | Y | Y | Y | Y | Y | Y |
| **Int32** | Y | Y | Y | Y | Y | Y |
| **Float64** | Y | Y | Y | Y | Y | Y |
| **Boolean** | N | Y | N | N | N | Y |
| **Date** | N | Y | N | Y | Y | Y |
| **Datetime** | N | Y | N | Y | Y | Y |
| **Decimal** | Y | Y | Y | Y | Y | Y |
| **List[Utf8]** | N | N | N | N | N | N |

**Y***: Utf8 columns are cast to `Float64` before applying the aggregation function. This handles string-encoded financial columns (`mrr`, `cost`, `weekly_ad_spend`). Non-numeric strings become null; Polars ignores nulls in aggregations.

### 5.2 Implementation

```python
# query/aggregator.py

_NUMERIC_AGGS = frozenset({AggFunction.SUM, AggFunction.MEAN})
_ORDERABLE_AGGS = frozenset({AggFunction.MIN, AggFunction.MAX})
_UNIVERSAL_AGGS = frozenset({AggFunction.COUNT, AggFunction.COUNT_DISTINCT})
_ALL_NON_LIST = _NUMERIC_AGGS | _ORDERABLE_AGGS | _UNIVERSAL_AGGS

AGG_FUNCTION_MATRIX: dict[str, frozenset[AggFunction]] = {
    "Utf8":       _ALL_NON_LIST,  # sum/mean/min/max cast to Float64 first
    "Int64":      _ALL_NON_LIST,
    "Int32":      _ALL_NON_LIST,
    "Float64":    _ALL_NON_LIST,
    "Boolean":    _UNIVERSAL_AGGS,
    "Date":       _ORDERABLE_AGGS | _UNIVERSAL_AGGS,
    "Datetime":   _ORDERABLE_AGGS | _UNIVERSAL_AGGS,
    "Decimal":    _ALL_NON_LIST,
    "List[Utf8]": frozenset(),
}
```

### 5.3 Inferred Output Dtypes (for HAVING Schema)

| Function | Input Dtype | Output Dtype |
|----------|------------|-------------|
| sum | Int64/Int32 | Int64 |
| sum | Float64/Decimal | Float64 |
| sum | Utf8 (cast) | Float64 |
| count | Any | Int64 |
| count_distinct | Any | Int64 |
| mean | Any numeric/Utf8 | Float64 |
| min/max | Numeric | Same as input |
| min/max | Date/Datetime | Same as input |
| min/max | Utf8 (cast) | Float64 |

---

## 6. Aggregation Compiler Design (`query/aggregator.py`)

### 6.1 AggregationCompiler Class

```python
@dataclass(frozen=True)
class AggregationCompiler:
    """Compiles AggSpec list into Polars aggregation expressions.

    Stateless, reusable. Schema is passed per-call so the same compiler
    instance can serve multiple entity types.
    """

    def compile(
        self,
        specs: list[AggSpec],
        schema: DataFrameSchema,
    ) -> list[pl.Expr]:
        """Compile aggregation specifications to Polars expressions.

        Args:
            specs: List of AggSpec models to compile.
            schema: Entity schema for column/dtype validation.

        Returns:
            List of pl.Expr suitable for df.group_by(...).agg(...).

        Raises:
            AggregationError: If column does not exist, or function
                is incompatible with column dtype.
            UnknownFieldError: If column not in schema.
        """
        return [self._compile_one(spec, schema) for spec in specs]

    def _compile_one(self, spec: AggSpec, schema: DataFrameSchema) -> pl.Expr:
        """Compile a single AggSpec to a pl.Expr."""
        # 1. Validate column exists
        col_def = schema.get_column(spec.column)
        if col_def is None:
            from autom8_asana.query.errors import UnknownFieldError
            raise UnknownFieldError(
                field=spec.column,
                available=schema.column_names(),
            )

        # 2. Validate function/dtype compatibility
        allowed = AGG_FUNCTION_MATRIX.get(col_def.dtype, frozenset())
        if spec.function not in allowed:
            raise AggregationError(
                f"Function '{spec.function.value}' not supported for "
                f"{col_def.dtype} column '{spec.column}'. "
                f"Supported: {sorted(a.value for a in allowed)}"
            )

        # 3. Build expression with optional Utf8 cast
        return _build_agg_expr(spec.column, spec.function, col_def.dtype, spec.resolved_alias)
```

### 6.2 Expression Building

```python
def _build_agg_expr(
    column: str, function: AggFunction, dtype: str, alias: str
) -> pl.Expr:
    """Build a single Polars aggregation expression.

    For Utf8 columns with numeric aggregations (sum, mean, min, max),
    casts to Float64 first. This handles string-encoded financial columns.
    """
    col = pl.col(column)

    # Cast Utf8 to Float64 for numeric aggregations
    needs_cast = dtype == "Utf8" and function in (
        AggFunction.SUM, AggFunction.MEAN, AggFunction.MIN, AggFunction.MAX,
    )
    if needs_cast:
        col = col.cast(pl.Float64, strict=False)

    match function:
        case AggFunction.SUM:
            return col.sum().alias(alias)
        case AggFunction.COUNT:
            return col.count().alias(alias)
        case AggFunction.MEAN:
            return col.mean().alias(alias)
        case AggFunction.MIN:
            return col.min().alias(alias)
        case AggFunction.MAX:
            return col.max().alias(alias)
        case AggFunction.COUNT_DISTINCT:
            return col.n_unique().alias(alias)

    raise ValueError(f"Unknown aggregation function: {function}")  # pragma: no cover
```

### 6.3 HAVING Schema Builder

```python
def build_post_agg_schema(
    group_by_columns: list[str],
    agg_specs: list[AggSpec],
    source_schema: DataFrameSchema,
) -> DataFrameSchema:
    """Build a synthetic schema representing the aggregated output.

    This schema is used to validate HAVING predicates against the
    post-aggregation column names and their inferred dtypes.

    Columns in the output schema:
    - group_by columns: retain their source dtype.
    - aggregation aliases: inferred from function + input dtype.
    """
    from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema

    columns: list[ColumnDef] = []

    # group_by columns retain their source dtype
    for col_name in group_by_columns:
        source_col = source_schema.get_column(col_name)
        if source_col is not None:
            columns.append(ColumnDef(
                name=col_name,
                dtype=source_col.dtype,
                nullable=source_col.nullable,
            ))

    # Aggregation output columns with inferred dtypes
    for spec in agg_specs:
        output_dtype = _infer_agg_output_dtype(spec, source_schema)
        columns.append(ColumnDef(
            name=spec.resolved_alias,
            dtype=output_dtype,
            nullable=True,
        ))

    return DataFrameSchema(
        name="__aggregate_output__",
        task_type="*",
        columns=columns,
    )


def _infer_agg_output_dtype(spec: AggSpec, schema: DataFrameSchema) -> str:
    """Infer the output dtype of an aggregation expression."""
    source_col = schema.get_column(spec.column)
    source_dtype = source_col.dtype if source_col else "Float64"

    match spec.function:
        case AggFunction.COUNT | AggFunction.COUNT_DISTINCT:
            return "Int64"
        case AggFunction.MEAN:
            return "Float64"
        case AggFunction.SUM:
            if source_dtype in ("Float64", "Decimal", "Utf8"):
                return "Float64"
            return "Int64"  # Int64/Int32 sum stays Int64
        case AggFunction.MIN | AggFunction.MAX:
            if source_dtype == "Utf8":
                return "Float64"  # Cast happens before aggregation
            return source_dtype

    return "Float64"  # pragma: no cover
```

### 6.4 Alias Uniqueness Validation

```python
def validate_alias_uniqueness(
    agg_specs: list[AggSpec],
    group_by: list[str],
) -> None:
    """Ensure all resolved alias names are unique and do not collide with group_by columns.

    Raises:
        AggregationError: If duplicate aliases or alias/group_by collision found.
    """
    seen: set[str] = set()
    for spec in agg_specs:
        alias = spec.resolved_alias
        if alias in seen:
            raise AggregationError(f"Duplicate alias: '{alias}'")
        if alias in group_by:
            raise AggregationError(
                f"Alias '{alias}' collides with group_by column"
            )
        seen.add(alias)
```

---

## 7. Engine Integration

### 7.1 `QueryEngine.execute_aggregate()` Method

```python
async def execute_aggregate(
    self,
    entity_type: str,
    project_gid: str,
    client: AsanaClient,
    request: AggregateRequest,
    section_index: SectionIndex | None = None,
) -> AggregateResponse:
    """Execute a /aggregate query.

    Flow:
    1. Validate predicate depth for WHERE (fail-fast guard).
    2. Validate predicate depth for HAVING (fail-fast guard).
    3. Resolve section parameter to name filter.
    4. Load DataFrame via EntityQueryService.get_dataframe().
    5. Get schema, validate group_by columns, validate alias uniqueness.
    6. Build filter expression from WHERE predicate.
    7. Apply section filter + WHERE filter.
    8. Compile aggregation expressions.
    9. Execute group_by().agg().
    10. Build HAVING virtual schema and compile HAVING predicate.
    11. Apply HAVING filter to grouped result.
    12. Check group count against max_aggregate_groups.
    13. Build response with metadata.
    """
    start = time.monotonic()

    # 1-2. Depth guards
    if request.where is not None:
        depth = predicate_depth(request.where)
        self.limits.check_depth(depth)
    if request.having is not None:
        depth = predicate_depth(request.having)
        self.limits.check_depth(depth)

    # 3. Resolve section (identical to execute_rows)
    section_name_filter: str | None = None
    if request.section is not None:
        if section_index is None:
            from autom8_asana.metrics.resolve import SectionIndex as _SectionIndex
            section_index = _SectionIndex.from_enum_fallback(entity_type)
        resolved_gid = section_index.resolve(request.section)
        if resolved_gid is None:
            raise UnknownSectionError(section=request.section)
        section_name_filter = request.section

    # 4. Load DataFrame
    df = await self.query_service.get_dataframe(
        entity_type, project_gid, client,
    )

    # 5. Get schema, validate group_by, validate aliases
    registry = SchemaRegistry.get_instance()
    schema = registry.get_schema(to_pascal_case(entity_type))
    self.limits.check_group_by(request.group_by, schema)
    validate_alias_uniqueness(request.aggregations, request.group_by)

    # 6-7. Build and apply WHERE + section filter
    filter_expr: pl.Expr | None = None
    if request.where is not None:
        filter_expr = self.compiler.compile(request.where, schema)
    if section_name_filter is not None:
        section_expr = pl.col("section") == section_name_filter
        filter_expr = (section_expr & filter_expr) if filter_expr else section_expr
    if filter_expr is not None:
        df = df.filter(filter_expr)

    # 8. Compile aggregation expressions
    from autom8_asana.query.aggregator import (
        AggregationCompiler,
        build_post_agg_schema,
    )
    agg_compiler = AggregationCompiler()
    agg_exprs = agg_compiler.compile(request.aggregations, schema)

    # 9. Execute GROUP BY + AGG
    result_df = df.group_by(request.group_by).agg(agg_exprs)

    # 10-11. HAVING filter
    if request.having is not None:
        post_agg_schema = build_post_agg_schema(
            group_by_columns=request.group_by,
            agg_specs=request.aggregations,
            source_schema=schema,
        )
        having_expr = self.compiler.compile(request.having, post_agg_schema)
        result_df = result_df.filter(having_expr)

    # 12. Check group count guard
    group_count = len(result_df)
    if group_count > self.limits.max_aggregate_groups:
        raise AggregateGroupLimitError(
            group_count=group_count,
            max_groups=self.limits.max_aggregate_groups,
        )

    # 13. Build response
    elapsed_ms = (time.monotonic() - start) * 1000
    data = result_df.to_dicts()

    return AggregateResponse(
        data=data,
        meta=AggregateMeta(
            group_count=group_count,
            aggregation_count=len(request.aggregations),
            group_by=request.group_by,
            entity_type=entity_type,
            project_gid=project_gid,
            query_ms=round(elapsed_ms, 2),
        ),
    )
```

### 7.2 Sequence Diagram

```
Client              Route Handler         QueryEngine          AggCompiler       PredicateCompiler     EQS
  |                     |                     |                    |                   |                |
  |-- POST /aggregate ->|                     |                    |                   |                |
  |                     |-- execute_aggregate->|                    |                   |                |
  |                     |                     |                    |                   |                |
  |                     |                check_depth(WHERE)        |                   |                |
  |                     |                check_depth(HAVING)       |                   |                |
  |                     |                resolve section           |                   |                |
  |                     |                     |                    |                   |                |
  |                     |                     |-- get_dataframe ---|---|---|---|------->|                |
  |                     |                     |<-- DataFrame ------|---|---|---|--------|                |
  |                     |                     |                    |                   |                |
  |                     |                validate group_by (schema)|                   |                |
  |                     |                validate alias uniqueness |                   |                |
  |                     |                     |                    |                   |                |
  |                     |                     | compile WHERE -----|---|---|---|------->|                |
  |                     |                     |<-- pl.Expr --------|---|---|---|--------|                |
  |                     |                     |                    |                   |                |
  |                     |                df.filter(section + WHERE)|                   |                |
  |                     |                     |                    |                   |                |
  |                     |                     | compile aggs ----->|                   |                |
  |                     |                     |   (validate dtypes)|                   |                |
  |                     |                     |<-- [pl.Expr] ------|                   |                |
  |                     |                     |                    |                   |                |
  |                     |                df.group_by().agg()       |                   |                |
  |                     |                     |                    |                   |                |
  |                     |                build_post_agg_schema     |                   |                |
  |                     |                     | compile HAVING ----|---|---|---|------->|                |
  |                     |                     |<-- pl.Expr --------|---|---|---|--------|                |
  |                     |                     |                    |                   |                |
  |                     |                result_df.filter(having)  |                   |                |
  |                     |                check group count guard   |                   |                |
  |                     |                     |                    |                   |                |
  |                     |<-- AggregateResponse|                    |                   |                |
  |<-- 200 JSON --------|                     |                    |                   |                |
```

---

## 8. Error Types

### 8.1 New Error Classes (`query/errors.py`)

```python
@dataclass
class AggregationError(QueryEngineError):
    """Aggregation-specific error (dtype mismatch, invalid group_by, alias collision)."""

    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "AGGREGATION_ERROR",
            "message": self.message,
        }


@dataclass
class AggregateGroupLimitError(QueryEngineError):
    """Aggregation produced too many groups."""

    group_count: int
    max_groups: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "TOO_MANY_GROUPS",
            "message": (
                f"Aggregation produced {self.group_count} groups, "
                f"exceeding maximum of {self.max_groups}"
            ),
            "group_count": self.group_count,
            "max_groups": self.max_groups,
        }
```

### 8.2 Error to HTTP Status Mapping

| Error Class | HTTP Status | Error Code |
|-------------|:-----------:|------------|
| `AggregationError` | 422 | `AGGREGATION_ERROR` |
| `AggregateGroupLimitError` | 400 | `TOO_MANY_GROUPS` |
| `QueryTooComplexError` | 400 | `QUERY_TOO_COMPLEX` |
| `UnknownFieldError` | 422 | `UNKNOWN_FIELD` |
| `InvalidOperatorError` | 422 | `INVALID_OPERATOR` |
| `CoercionError` | 422 | `COERCION_FAILED` |
| `UnknownSectionError` | 422 | `UNKNOWN_SECTION` |
| `CacheNotWarmError` | 503 | `CACHE_NOT_WARMED` |

The `_ERROR_STATUS` mapping in `query_v2.py` is extended:

```python
_ERROR_STATUS: dict[type[QueryEngineError], int] = {
    QueryTooComplexError: 400,
    AggregateGroupLimitError: 400,  # NEW
}
```

---

## 9. Guards Extension (`query/guards.py`)

### 9.1 QueryLimits Extension

```python
@dataclass(frozen=True)
class QueryLimits:
    """Configurable query limits per FR-008."""

    max_predicate_depth: int = 5
    max_result_rows: int = 10_000
    max_aggregate_groups: int = 10_000  # NEW

    # ... existing check_depth and clamp_limit methods ...

    def check_group_by(
        self,
        columns: list[str],
        schema: DataFrameSchema,
    ) -> None:
        """Validate group_by columns exist and are not List dtype.

        Raises:
            UnknownFieldError: If column not in schema.
            AggregationError: If column has List dtype.
        """
        for col_name in columns:
            col_def = schema.get_column(col_name)
            if col_def is None:
                raise UnknownFieldError(
                    field=col_name,
                    available=schema.column_names(),
                )
            if col_def.dtype.startswith("List"):
                raise AggregationError(
                    f"Cannot group by List-dtype column '{col_name}' "
                    f"(dtype: {col_def.dtype}). Use a scalar column."
                )
```

### 9.2 Guard Summary

| Guard | Limit | Applied To |
|-------|:-----:|------------|
| `max_predicate_depth` | 5 | WHERE and HAVING predicate trees |
| `max_aggregate_groups` | 10,000 | Post-aggregation result count |
| `group_by max_length` | 5 | Pydantic field constraint |
| `aggregations max_length` | 10 | Pydantic field constraint |
| group_by List dtype | Reject | group_by column validation |

---

## 10. Route Handler Design (`api/routes/query_v2.py`)

### 10.1 New Endpoint

```python
@router.post("/{entity_type}/aggregate", response_model=AggregateResponse)
async def query_aggregate(
    entity_type: str,
    request_body: AggregateRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> AggregateResponse:
    """Aggregate entity data with grouping and optional HAVING filter.

    See PRD-dynamic-query-service FR-005.
    """
```

The handler follows the identical pattern as `query_rows`:
1. Validate entity type against `get_resolvable_entities()`.
2. Get `EntityProjectRegistry` from `request.app.state`.
3. Get `project_gid` from registry.
4. Get bot PAT via `get_bot_pat()`.
5. Build section index if `request_body.section` is provided.
6. Instantiate `QueryEngine` and call `execute_aggregate()`.
7. Catch `QueryEngineError` -> `_error_to_response()`.
8. Catch `CacheNotWarmError` -> 503.
9. Log completion metrics.

### 10.2 Import Additions

```python
from autom8_asana.query.errors import AggregateGroupLimitError
from autom8_asana.query.models import AggregateRequest, AggregateResponse
```

---

## 11. Example Request/Response

### 11.1 Basic Aggregation

**Request**:
```json
POST /v1/query/offer/aggregate
{
    "section": "Active",
    "group_by": ["vertical"],
    "aggregations": [
        {"column": "mrr", "function": "sum", "alias": "total_mrr"},
        {"column": "gid", "function": "count", "alias": "offer_count"}
    ]
}
```

**Response**:
```json
{
    "data": [
        {"vertical": "dental", "total_mrr": 15000.0, "offer_count": 12},
        {"vertical": "medical", "total_mrr": 22000.0, "offer_count": 8}
    ],
    "meta": {
        "group_count": 2,
        "aggregation_count": 2,
        "group_by": ["vertical"],
        "entity_type": "offer",
        "project_gid": "1143843662099250",
        "query_ms": 8.3
    }
}
```

### 11.2 With WHERE and HAVING

**Request**:
```json
POST /v1/query/offer/aggregate
{
    "where": {"field": "is_completed", "op": "eq", "value": false},
    "group_by": ["vertical"],
    "aggregations": [
        {"column": "mrr", "function": "sum", "alias": "total_mrr"},
        {"column": "gid", "function": "count", "alias": "offer_count"}
    ],
    "having": {"field": "total_mrr", "op": "gt", "value": 10000}
}
```

**Response** (only groups where total_mrr > 10000):
```json
{
    "data": [
        {"vertical": "dental", "total_mrr": 15000.0, "offer_count": 12},
        {"vertical": "medical", "total_mrr": 22000.0, "offer_count": 8}
    ],
    "meta": {
        "group_count": 2,
        "aggregation_count": 2,
        "group_by": ["vertical"],
        "entity_type": "offer",
        "project_gid": "1143843662099250",
        "query_ms": 11.2
    }
}
```

### 11.3 count_distinct with Default Alias

**Request**:
```json
POST /v1/query/offer/aggregate
{
    "group_by": ["section"],
    "aggregations": [
        {"column": "vertical", "function": "count_distinct"},
        {"column": "gid", "function": "count"}
    ]
}
```

Note: No explicit aliases provided. Defaults to `count_distinct_vertical` and `count_gid`.

---

## 12. Test Plan

### 12.1 Unit Tests: AggSpec Model Validation (`tests/unit/query/test_models.py` additions)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-AS001 | Valid AggSpec with explicit alias | Parses successfully |
| TC-AS002 | Valid AggSpec without alias | `resolved_alias` returns `"{function}_{column}"` |
| TC-AS003 | AggSpec with invalid function | Pydantic validation error |
| TC-AS004 | AggSpec with extra fields | Rejected (extra="forbid") |
| TC-AS005 | AggregateRequest empty group_by | Pydantic min_length error |
| TC-AS006 | AggregateRequest >5 group_by | Pydantic max_length error |
| TC-AS007 | AggregateRequest empty aggregations | Pydantic min_length error |
| TC-AS008 | AggregateRequest >10 aggregations | Pydantic max_length error |
| TC-AS009 | AggregateRequest WHERE flat array sugar | Wrapped to AND group |
| TC-AS010 | AggregateRequest HAVING flat array sugar | Wrapped to AND group |

### 12.2 Unit Tests: AggregationCompiler (`tests/unit/query/test_aggregator.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-AC001 | sum on Float64 column | Valid expression, correct sum |
| TC-AC002 | sum on Int64 column | Valid expression, correct sum |
| TC-AC003 | sum on Utf8 column (mrr) | Valid expression with Float64 cast, correct sum |
| TC-AC004 | sum on Boolean column | `AggregationError` raised |
| TC-AC005 | sum on Date column | `AggregationError` raised |
| TC-AC006 | count on Utf8 column | Valid expression, counts non-null |
| TC-AC007 | count_distinct on Utf8 column | Valid expression via n_unique() |
| TC-AC008 | count on Boolean column | Valid expression |
| TC-AC009 | mean on Float64 column | Valid expression, Float64 output |
| TC-AC010 | mean on Boolean column | `AggregationError` raised |
| TC-AC011 | min on Date column | Valid expression |
| TC-AC012 | max on Datetime column | Valid expression |
| TC-AC013 | min/max on Utf8 column | Valid expression with Float64 cast |
| TC-AC014 | Any function on List[Utf8] column | `AggregationError` raised |
| TC-AC015 | Unknown column | `UnknownFieldError` raised |
| TC-AC016 | Alias applied correctly | Output column name matches alias |
| TC-AC017 | Default alias pattern | Output column name is `{function}_{column}` |
| TC-AC018 | Multiple agg specs compiled | Returns list of correct length |

### 12.3 Unit Tests: HAVING Schema Builder (`tests/unit/query/test_aggregator.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-HS001 | group_by columns retain source dtype | `vertical` -> Utf8 |
| TC-HS002 | sum alias on Float64 -> Float64 | `total_amount` -> Float64 |
| TC-HS003 | sum alias on Int64 -> Int64 | `total_quantity` -> Int64 |
| TC-HS004 | sum alias on Utf8 (cast) -> Float64 | `total_mrr` -> Float64 |
| TC-HS005 | count alias -> Int64 | `offer_count` -> Int64 |
| TC-HS006 | count_distinct alias -> Int64 | `unique_verticals` -> Int64 |
| TC-HS007 | mean alias -> Float64 | `avg_cost` -> Float64 |
| TC-HS008 | min/max on Date -> Date | `min_date` -> Date |

### 12.4 Unit Tests: Alias Validation (`tests/unit/query/test_aggregator.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-AV001 | All unique aliases | No error |
| TC-AV002 | Duplicate resolved aliases | `AggregationError` |
| TC-AV003 | Alias collides with group_by column | `AggregationError` |
| TC-AV004 | Default aliases are unique (different functions) | No error |
| TC-AV005 | Default aliases collide (same function, same column) | `AggregationError` |

### 12.5 Unit Tests: QueryEngine.execute_aggregate (`tests/unit/query/test_engine.py` additions)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-EA001 | Basic group_by + sum | Correct grouped sums |
| TC-EA002 | group_by + multiple aggregations | All agg columns present |
| TC-EA003 | WHERE filter applied before grouping | Correct filter-then-group |
| TC-EA004 | Section filter applied before grouping | Correct section-then-group |
| TC-EA005 | HAVING filter applied after grouping | Groups filtered correctly |
| TC-EA006 | WHERE + section + HAVING combined | Full pipeline |
| TC-EA007 | group_by on non-existent column | `UnknownFieldError` |
| TC-EA008 | group_by on List[Utf8] column | `AggregationError` |
| TC-EA009 | Utf8 column sum via Float64 cast | Correct numeric sum |
| TC-EA010 | Empty DataFrame after WHERE filter | `data: [], group_count: 0` |
| TC-EA011 | HAVING filters all groups | `data: [], group_count: 0` |
| TC-EA012 | count vs count_distinct | Different results when duplicates exist |
| TC-EA013 | Depth guard on WHERE | `QueryTooComplexError` |
| TC-EA014 | Depth guard on HAVING | `QueryTooComplexError` |
| TC-EA015 | HAVING references non-existent alias | `UnknownFieldError` |
| TC-EA016 | HAVING on group_by column | Works correctly |
| TC-EA017 | Group count exceeds max_aggregate_groups | `AggregateGroupLimitError` |
| TC-EA018 | AggregateMeta populated correctly | group_count, aggregation_count, group_by, query_ms |
| TC-EA019 | Alias collision | `AggregationError` |
| TC-EA020 | Multiple group_by columns | Compound grouping works |

### 12.6 Integration Tests: /aggregate Route (`tests/api/test_routes_query_aggregate.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-RA001 | Valid aggregate request | 200, correct response shape |
| TC-RA002 | Unknown entity type | 404 UNKNOWN_ENTITY_TYPE |
| TC-RA003 | sum on Boolean column | 422 AGGREGATION_ERROR |
| TC-RA004 | group_by on List column | 422 AGGREGATION_ERROR |
| TC-RA005 | HAVING with unknown alias | 422 UNKNOWN_FIELD |
| TC-RA006 | WHERE predicate too deep | 400 QUERY_TOO_COMPLEX |
| TC-RA007 | Cache not warm | 503 CACHE_NOT_WARMED |
| TC-RA008 | Empty result | 200, data=[], group_count=0 |
| TC-RA009 | Missing S2S auth | 401 |
| TC-RA010 | With section filter | 200, section applied before grouping |
| TC-RA011 | count_distinct in response | 200, correct unique counts |
| TC-RA012 | Request with extra fields | 422 Pydantic validation error |
| TC-RA013 | Utf8 column sum (mrr) | 200, correct Float64 sum |
| TC-RA014 | HAVING flat array sugar | 200, treated as AND |
| TC-RA015 | Duplicate alias error | 422 AGGREGATION_ERROR |
| TC-RA016 | Too many groups | 400 TOO_MANY_GROUPS |

---

## 13. Implementation Task Breakdown (Ordered)

### Phase 1: Models and Compilation (No Route Changes)

| # | Task | File(s) | Depends On | Est. LOC |
|---|------|---------|-----------|----------|
| 1 | Add AggFunction, AggSpec to models | `query/models.py` | -- | 30 |
| 2 | Add AggregateRequest, AggregateMeta, AggregateResponse to models | `query/models.py` | 1 | 40 |
| 3 | Add AggregationError, AggregateGroupLimitError to errors | `query/errors.py` | -- | 30 |
| 4 | Create `aggregator.py`: AggregationCompiler, AGG_FUNCTION_MATRIX, build_post_agg_schema, validate_alias_uniqueness | `query/aggregator.py` | 1,3 | 180 |
| 5 | Add max_aggregate_groups + check_group_by to guards | `query/guards.py` | 3 | 25 |
| 6 | Unit tests for AggSpec/AggregateRequest models | `tests/unit/query/test_models.py` | 1,2 | 80 |
| 7 | Unit tests for AggregationCompiler + HAVING schema | `tests/unit/query/test_aggregator.py` | 4 | 200 |

### Phase 2: Engine Integration

| # | Task | File(s) | Depends On | Est. LOC |
|---|------|---------|-----------|----------|
| 8 | Add execute_aggregate() to QueryEngine | `query/engine.py` | 4,5 | 80 |
| 9 | Unit tests for execute_aggregate() | `tests/unit/query/test_aggregate.py` | 8 | 250 |

### Phase 3: Route Integration

| # | Task | File(s) | Depends On | Est. LOC |
|---|------|---------|-----------|----------|
| 10 | Add POST /{entity_type}/aggregate handler | `api/routes/query_v2.py` | 8 | 70 |
| 11 | Update __init__.py exports | `query/__init__.py` | 1,2,3,4 | 20 |
| 12 | Integration tests for /aggregate route | `tests/api/test_routes_query_aggregate.py` | 10 | 200 |

**Total estimated LOC**: ~1,205 (implementation + tests)

---

## 14. Performance Considerations

### 14.1 Target Latency (NFR-001: p50 < 30ms, p99 < 150ms)

| Step | Expected Time | Notes |
|------|:------------:|-------|
| Auth validation | ~1ms | JWT validation cached |
| WHERE compilation | ~0.1ms | Pure Python dict traversal |
| Section validation | ~0.1ms | In-memory dict lookup |
| DataFrame retrieval | ~0.5ms | Memory-tier cache hit |
| Polars filter (WHERE) | ~3ms | In-memory columnar |
| Polars group_by + agg | ~2ms | Vectorized, <50 groups typical |
| HAVING compilation | ~0.1ms | Small virtual schema |
| Polars filter (HAVING) | ~0.1ms | Tiny result set |
| Serialization | ~1ms | <50 groups = <50 dicts |
| **Total** | **~8ms** | Well under 30ms target |

### 14.2 Utf8 Cast Overhead

Casting Utf8 columns to Float64 adds ~1ms for 1000+ rows. This is negligible and unavoidable given the schema. `strict=False` ensures non-numeric strings become null rather than raising, consistent with `MetricExpr.to_polars_expr()`.

### 14.3 What We Are NOT Doing

- **Lazy evaluation**: DataFrames are materialized in cache. Eager group_by is efficient.
- **Pre-computed aggregation caching**: Cheap to compute, not worth staleness risk.
- **Streaming**: Full DataFrame fits in memory.

---

## 15. Security Considerations

- **No injection vectors**: Columns, functions, and aliases are validated against schema and enum. No string interpolation.
- **S2S JWT required**: Same auth as existing endpoints via `require_service_claims()`.
- **extra="forbid"** on all new Pydantic models.
- **MAX_AGGREGATE_GROUPS guard**: Prevents resource exhaustion from high-cardinality GROUP BY.
- **MAX_PREDICATE_DEPTH**: Applied to both WHERE and HAVING predicates.

---

## 16. Observability

Each `/aggregate` request logs:

```python
logger.info(
    "query_v2_aggregate_complete",
    extra={
        "entity_type": entity_type,
        "group_count": result.meta.group_count,
        "aggregation_count": result.meta.aggregation_count,
        "group_by": result.meta.group_by,
        "query_ms": result.meta.query_ms,
        "caller_service": claims.service_name,
        "predicate_depth": (
            predicate_depth(request_body.where) if request_body.where else 0
        ),
        "having_depth": (
            predicate_depth(request_body.having) if request_body.having else 0
        ),
        "section": request_body.section,
    },
)
```

---

## 17. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| **Utf8 cast produces all nulls for non-numeric strings** | Medium | Low | sum/mean of nulls returns null. The cast only fails silently for non-numeric content. Financial columns (mrr, cost) are reliably numeric strings. Non-financial Utf8 columns (name, vertical) would produce null aggregates, which is visible in the response. |
| **HAVING dtype inference mismatch** | Low | Medium | `_infer_agg_output_dtype()` unit-tested per function. If a new function is added without updating inference, the test will catch it. |
| **Non-deterministic group order** | Medium | Low | Polars group_by uses hash-based grouping. Consumers should sort client-side if ordering matters. Document in API docs. |
| **Null values in group_by columns** | Medium | Low | Polars creates a group for null values. This is correct SQL semantics. Document that null is a valid group key. |
| **High-cardinality group_by** | Low | Medium | max_aggregate_groups=10,000 guard catches this. group_by max_length=5 limits combinatorial explosion. |
| **Alias collision with Polars internal names** | Very Low | Low | Aliases are user-controlled and validated for uniqueness. Polars does not reserve column names. |

---

## 18. Design Constraints and Known Limitations

1. **Additive to Sprint 1+2 code**: No modifications to existing models, engine methods, compiler, or guards (except extending `QueryLimits` with one new field and one new method).
2. **Reuse PredicateCompiler for WHERE and HAVING**: Compiler is not modified; HAVING uses a synthetic schema.
3. **Reuse section resolution from /rows**: Identical pattern.
4. **No pagination on aggregate results**: All groups returned (up to max_aggregate_groups).
5. **HAVING references alias names, not raw column names**: Enforced by the synthetic schema.
6. **No ORDER BY on aggregated results**: Results in Polars natural group order. Future enhancement.
7. **No nested aggregation**: Single-level group_by only.
8. **count_distinct counts nulls**: Polars `n_unique()` treats null as a distinct value.

---

## Attestation Table

| File | Absolute Path | Read |
|------|---------------|:----:|
| PRD FR-005 | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-query-service.md` | Yes |
| Sprint 1 TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-dynamic-query-service.md` | Yes |
| Sprint 2 Cycle 1 TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-hierarchy-index.md` | Yes |
| Query __init__ | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/__init__.py` | Yes |
| Query models | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py` | Yes |
| Query compiler | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/compiler.py` | Yes |
| Query engine | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py` | Yes |
| Query guards | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/guards.py` | Yes |
| Query errors | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | Yes |
| Query join | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/join.py` | Yes |
| MetricExpr | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/expr.py` | Yes |
| DataFrameSchema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Yes |
| Base Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/base.py` | Yes |
| Offer Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/offer.py` | Yes |
| Route handler (query_v2) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query_v2.py` | Yes |
