# TDD: Query Engine Foundation (Sprint 1 -- /rows Endpoint)

## Metadata

| Field | Value |
|-------|-------|
| **TDD ID** | TDD-query-engine-foundation |
| **PRD** | PRD-dynamic-query-service |
| **Sprint** | S1-002 |
| **Status** | Draft |
| **Created** | 2026-02-03 |
| **Author** | Architect |

---

## 1. Overview

This document specifies the technical design for the query engine foundation that powers Sprint 1's `POST /v1/query/{entity_type}/rows` endpoint. The design introduces a composable predicate compilation engine (AST to `pl.Expr`) that future `/aggregate` and `/metric` endpoints will reuse without modification.

### 1.1 Design Goals

1. **Composable predicate engine**: The compiler transforms a recursive PredicateNode AST into a single `pl.Expr`, independent of how that expression is consumed.
2. **Schema-aware validation**: Every leaf node is validated against `SchemaRegistry` column definitions before compilation -- fail fast, fail clearly.
3. **Composition over inheritance**: `QueryEngine` composes `EntityQueryService` (cache access), `PredicateCompiler` (AST to expr), `SchemaRegistry` (field validation), and `SectionIndex` (section resolution) rather than subclassing any of them.
4. **Additive change**: The existing `/v1/query/{entity_type}` route is untouched. The new route lives in a separate module. No existing tests break.

### 1.2 Key Decisions Summary

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Package location | `src/autom8_asana/query/` | Separate from `services/` to signal new capability boundary | ADR-QE-001 |
| Discriminated union strategy | Pydantic v2 `Discriminator` with callable | Only approach that handles leaf vs group without a shared discriminator key | ADR-QE-002 |
| Section column semantics | Match by **name** (not GID) | DataFrame `section` column stores names per EC-010; SectionIndex resolves param name for comparison | ADR-QE-003 |
| EntityQueryService extension | New `get_dataframe()` public method | Wraps `strategy._get_dataframe()` to avoid downstream callers touching private API | ADR-QE-004 |

---

## 2. Module Structure

```
src/autom8_asana/query/
    __init__.py       # Public API: QueryEngine, PredicateCompiler, models, errors
    models.py         # Pydantic v2 models: PredicateNode, Comparison, PredicateGroup, RowsRequest, RowsResponse
    compiler.py       # PredicateCompiler: AST -> pl.Expr with operator x dtype matrix + coercion
    engine.py         # QueryEngine: composes data loading + scope resolution + compilation + response
    guards.py         # QueryLimits config dataclass + depth/rows enforcement
    errors.py         # QueryEngineError hierarchy with error codes

src/autom8_asana/api/routes/query_v2.py   # /v1/query/{entity_type}/rows route handler

tests/unit/query/
    __init__.py
    test_models.py     # PredicateNode parsing, sugar, depth, validation
    test_compiler.py   # Operator x dtype matrix, coercion, expression assembly
    test_engine.py     # QueryEngine integration with mocked services
    test_guards.py     # Depth + row limit enforcement
    test_errors.py     # Error hierarchy serialization

tests/integration/api/
    test_query_v2.py   # End-to-end /rows tests via TestClient
```

### 2.1 Rationale

The `query/` package is a **new top-level domain** under `src/autom8_asana/` rather than a sub-module of `services/` because:

- It owns models, compilation logic, and orchestration -- not just a service wrapper.
- Sprint 2/3 will add aggregate and metric engines here without polluting `services/`.
- The existing `services/query_service.py` (`EntityQueryService`) remains the cache-access primitive. `QueryEngine` composes it.

---

## 3. PredicateNode Discriminated Union (Pydantic v2)

### 3.1 Type Hierarchy

```
PredicateNode (union)
  |
  +-- Comparison        {"field": str, "op": Op, "value": Any}
  +-- AndGroup          {"and": list[PredicateNode]}
  +-- OrGroup           {"or": list[PredicateNode]}
  +-- NotGroup          {"not": PredicateNode}
```

### 3.2 Models

```python
"""query/models.py -- Pydantic v2 predicate models."""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, field_validator


class Op(str, Enum):
    """Supported comparison operators."""
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"


class Comparison(BaseModel):
    """Leaf predicate node: single field comparison."""
    model_config = ConfigDict(extra="forbid")

    field: str
    op: Op
    value: Any


class AndGroup(BaseModel):
    """AND group node: all children must match."""
    model_config = ConfigDict(extra="forbid")

    and_: list[PredicateNode] = Field(alias="and")


class OrGroup(BaseModel):
    """OR group node: at least one child must match."""
    model_config = ConfigDict(extra="forbid")

    or_: list[PredicateNode] = Field(alias="or")


class NotGroup(BaseModel):
    """NOT group node: child must not match."""
    model_config = ConfigDict(extra="forbid")

    not_: PredicateNode = Field(alias="not")


def _predicate_discriminator(v: Any) -> str:
    """Callable discriminator for PredicateNode union.

    Inspects the raw dict to determine which variant to parse.
    """
    if isinstance(v, dict):
        if "and" in v:
            return "and"
        if "or" in v:
            return "or"
        if "not" in v:
            return "not"
        if "field" in v:
            return "comparison"
    # Pydantic will raise a validation error for unrecognized shapes
    return "comparison"


PredicateNode = Annotated[
    Union[
        Annotated[Comparison, Tag("comparison")],
        Annotated[AndGroup, Tag("and")],
        Annotated[OrGroup, Tag("or")],
        Annotated[NotGroup, Tag("not")],
    ],
    Discriminator(_predicate_discriminator),
]

# Rebuild forward refs after PredicateNode is defined
AndGroup.model_rebuild()
OrGroup.model_rebuild()
NotGroup.model_rebuild()
```

### 3.3 Flat-Array Sugar

The `RowsRequest` model handles the sugar transformation in a `field_validator`:

```python
class RowsRequest(BaseModel):
    """POST /v1/query/{entity_type}/rows request body."""
    model_config = ConfigDict(extra="forbid")

    where: PredicateNode | None = None
    section: str | None = None
    select: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    order_by: str | None = None
    order_dir: Literal["asc", "desc"] = "asc"

    @field_validator("where", mode="before")
    @classmethod
    def wrap_flat_array(cls, v: Any) -> Any:
        """Auto-wrap bare list to AND group (FR-001 sugar)."""
        if isinstance(v, list):
            if len(v) == 0:
                return None  # Empty array = no filter (EC-005)
            return {"and": v}
        return v
```

### 3.4 Depth Tracking

Depth is computed as a standalone function, not embedded in models, because it is a guard concern:

```python
# query/guards.py
def predicate_depth(node: PredicateNode) -> int:
    """Compute max nesting depth of a predicate tree.

    - Comparison leaf = 1
    - Group node = 1 + max(children depth)
    """
    if isinstance(node, Comparison):
        return 1
    if isinstance(node, (AndGroup, OrGroup)):
        children = node.and_ if isinstance(node, AndGroup) else node.or_
        if not children:
            return 1
        return 1 + max(predicate_depth(c) for c in children)
    if isinstance(node, NotGroup):
        return 1 + predicate_depth(node.not_)
    return 1  # unreachable
```

---

## 4. Operator x Dtype Validation Matrix

### 4.1 Matrix Definition

The matrix is defined as a `frozenset` lookup for O(1) validation:

```python
# query/compiler.py

# Operator groups
_ORDERABLE_OPS = frozenset({Op.GT, Op.LT, Op.GTE, Op.LTE})
_STRING_OPS = frozenset({Op.CONTAINS, Op.STARTS_WITH})
_UNIVERSAL_OPS = frozenset({Op.EQ, Op.NE, Op.IN, Op.NOT_IN})

# Dtypes that support ordering
_ORDERABLE_DTYPES = frozenset({
    "Utf8", "Int64", "Int32", "Float64", "Date", "Datetime", "Decimal",
})

# Complete compatibility matrix: dtype -> frozenset of allowed ops
OPERATOR_MATRIX: dict[str, frozenset[Op]] = {
    "Utf8":       _UNIVERSAL_OPS | _ORDERABLE_OPS | _STRING_OPS,
    "Int64":      _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Int32":      _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Float64":    _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Boolean":    _UNIVERSAL_OPS,
    "Date":       _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Datetime":   _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "Decimal":    _UNIVERSAL_OPS | _ORDERABLE_OPS,
    "List[Utf8]": frozenset(),  # No operators in Sprint 1
}
```

### 4.2 Validation Matrix (Table Form)

| Dtype | eq | ne | gt | lt | gte | lte | in | not_in | contains | starts_with |
|-------|:--:|:--:|:--:|:--:|:---:|:---:|:--:|:------:|:--------:|:-----------:|
| **Utf8** | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| **Int64** | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| **Int32** | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| **Float64** | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| **Boolean** | Y | Y | N | N | N | N | Y | Y | N | N |
| **Date** | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| **Datetime** | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| **Decimal** | Y | Y | Y | Y | Y | Y | Y | Y | N | N |
| **List[Utf8]** | N | N | N | N | N | N | N | N | N | N |

### 4.3 Validation Flow

```
Comparison leaf received
    |
    +-- 1. Field exists in schema? (SchemaRegistry)
    |       NO -> UNKNOWN_FIELD (422)
    |
    +-- 2. Get dtype from ColumnDef
    |
    +-- 3. Op in OPERATOR_MATRIX[dtype]?
    |       NO -> INVALID_OPERATOR (422)
    |
    +-- 4. Coerce value to dtype
    |       FAIL -> COERCION_FAILED (422)
    |
    +-- 5. Build pl.Expr
```

---

## 5. Value Coercion Rules

The compiler coerces JSON values to the column's Polars dtype before building expressions. Coercion is fail-fast: the first error aborts compilation.

### 5.1 Coercion Table

| Source JSON Type | Target Dtype | Coercion Logic | Example |
|------------------|-------------|----------------|---------|
| string | Utf8 | Passthrough | `"dental"` -> `"dental"` |
| number (int/float) | Utf8 | `str(value)` | `123` -> `"123"` (permissive per EC-007) |
| number (int) | Int64 | `int(value)` | `1000` -> `1000` |
| number (int) | Int32 | `int(value)`, range check | `1000` -> `1000` |
| number (int/float) | Float64 | `float(value)` | `99.5` -> `99.5` |
| string | Float64 | `float(value)` | `"99.5"` -> `99.5` |
| string | Int64 | `int(value)` | `"1000"` -> `1000` |
| boolean | Boolean | Passthrough | `true` -> `True` |
| string | Date | `date.fromisoformat(value)` | `"2026-01-15"` -> `date(2026, 1, 15)` |
| string | Datetime | `datetime.fromisoformat(value)` | `"2026-01-15T10:30:00Z"` -> `datetime(...)` |
| number | Decimal | `float(value)` | `99.5` -> `99.5` (stored as Float64) |
| list | (for in/not_in) | Coerce each element per dtype | `[1, 2, 3]` -> `[1, 2, 3]` |

### 5.2 Coercion Implementation

```python
# query/compiler.py

from datetime import date, datetime


def _coerce_value(value: Any, dtype: str, field_name: str, op: Op) -> Any:
    """Coerce a JSON value to the target Polars dtype.

    For in/not_in operators, coerces each element in the list.

    Raises:
        CoercionError: If value cannot be coerced.
    """
    if op in (Op.IN, Op.NOT_IN):
        if not isinstance(value, list):
            raise CoercionError(field_name, dtype, value, "value must be a list for in/not_in")
        return [_coerce_scalar(v, dtype, field_name) for v in value if v is not None]

    return _coerce_scalar(value, dtype, field_name)


def _coerce_scalar(value: Any, dtype: str, field_name: str) -> Any:
    """Coerce a single scalar value."""
    try:
        if dtype == "Utf8":
            return str(value)
        if dtype in ("Int64", "Int32"):
            return int(value)
        if dtype in ("Float64", "Decimal"):
            return float(value)
        if dtype == "Boolean":
            if not isinstance(value, bool):
                raise ValueError("expected boolean")
            return value
        if dtype == "Date":
            if isinstance(value, str):
                return date.fromisoformat(value)
            raise ValueError("expected ISO 8601 date string")
        if dtype == "Datetime":
            if isinstance(value, str):
                # Handle trailing Z (common in JSON)
                normalized = value.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized)
            raise ValueError("expected ISO 8601 datetime string")
    except (ValueError, TypeError, OverflowError) as e:
        raise CoercionError(field_name, dtype, value, str(e)) from e

    raise CoercionError(field_name, dtype, value, f"unsupported dtype: {dtype}")
```

---

## 6. PredicateCompiler

### 6.1 Interface

```python
# query/compiler.py

@dataclass(frozen=True)
class PredicateCompiler:
    """Compiles a PredicateNode AST into a pl.Expr.

    Stateless, reusable. Schema is passed per-call so the same compiler
    instance can serve multiple entity types.
    """

    def compile(
        self,
        node: PredicateNode,
        schema: DataFrameSchema,
    ) -> pl.Expr:
        """Compile a predicate tree to a Polars expression.

        Args:
            node: Root of the predicate tree.
            schema: Entity schema for field/dtype validation.

        Returns:
            A single pl.Expr that can be passed to df.filter().

        Raises:
            UnknownFieldError: Field not in schema.
            InvalidOperatorError: Op incompatible with field dtype.
            CoercionError: Value cannot be coerced to field dtype.
        """
        ...

    def _compile_comparison(
        self,
        node: Comparison,
        schema: DataFrameSchema,
    ) -> pl.Expr:
        """Compile a leaf comparison to pl.Expr.

        Validation order: field -> operator -> coercion -> expression.
        """
        # 1. Validate field
        col_def = schema.get_column(node.field)
        if col_def is None:
            raise UnknownFieldError(
                field=node.field,
                available=schema.column_names(),
            )

        # 2. Validate operator
        allowed_ops = OPERATOR_MATRIX.get(col_def.dtype, frozenset())
        if node.op not in allowed_ops:
            raise InvalidOperatorError(
                field=node.field,
                dtype=col_def.dtype,
                op=node.op,
                allowed=sorted(o.value for o in allowed_ops),
            )

        # 3. Coerce value
        coerced = _coerce_value(node.value, col_def.dtype, node.field, node.op)

        # 4. Build expression
        return _build_expr(node.field, node.op, coerced)

    def _compile_group(
        self,
        node: AndGroup | OrGroup | NotGroup,
        schema: DataFrameSchema,
    ) -> pl.Expr:
        """Compile a group node by recursing into children."""
        ...
```

### 6.2 Expression Building

```python
# query/compiler.py

def _build_expr(field: str, op: Op, value: Any) -> pl.Expr:
    """Build a pl.Expr from a validated comparison."""
    col = pl.col(field)

    match op:
        case Op.EQ:
            return col == value
        case Op.NE:
            return col != value
        case Op.GT:
            return col > value
        case Op.LT:
            return col < value
        case Op.GTE:
            return col >= value
        case Op.LTE:
            return col <= value
        case Op.IN:
            return col.is_in(value)
        case Op.NOT_IN:
            return ~col.is_in(value)
        case Op.CONTAINS:
            return col.str.contains(value, literal=True)
        case Op.STARTS_WITH:
            return col.str.starts_with(value)
```

### 6.3 Group Compilation

```python
def _compile_node(self, node: PredicateNode, schema: DataFrameSchema) -> pl.Expr:
    if isinstance(node, Comparison):
        return self._compile_comparison(node, schema)
    if isinstance(node, AndGroup):
        exprs = [self._compile_node(c, schema) for c in node.and_]
        if not exprs:
            return pl.lit(True)  # Identity element of AND (EC-005)
        return reduce(lambda a, b: a & b, exprs)
    if isinstance(node, OrGroup):
        exprs = [self._compile_node(c, schema) for c in node.or_]
        if not exprs:
            return pl.lit(False)  # Identity element of OR
        return reduce(lambda a, b: a | b, exprs)
    if isinstance(node, NotGroup):
        return ~self._compile_node(node.not_, schema)
    raise ValueError(f"Unknown node type: {type(node)}")
```

---

## 7. QueryEngine

### 7.1 Responsibilities

`QueryEngine` is the orchestrator for a single query request. It composes:

| Component | Source | Responsibility |
|-----------|--------|----------------|
| `EntityQueryService` | `services/query_service.py` | DataFrame retrieval via cache lifecycle |
| `PredicateCompiler` | `query/compiler.py` | AST to `pl.Expr` |
| `SchemaRegistry` | `dataframes/models/registry.py` | Field + dtype validation |
| `SectionIndex` | `metrics/resolve.py` | Section name resolution |
| `QueryLimits` | `query/guards.py` | Depth + row guards |

### 7.2 EntityQueryService Extension

The existing `EntityQueryService` exposes DataFrame retrieval only through the `query()` method. `QueryEngine` needs raw DataFrame access. Rather than calling `strategy._get_dataframe()` directly (private API), we add a public method:

```python
# Addition to services/query_service.py

async def get_dataframe(
    self,
    entity_type: str,
    project_gid: str,
    client: AsanaClient,
) -> pl.DataFrame:
    """Get the raw DataFrame for an entity type.

    Provides the same cache lifecycle as query() but returns the
    raw DataFrame for custom processing.

    Args:
        entity_type: Entity type (e.g., "offer").
        project_gid: Project GID for cache key.
        client: AsanaClient for build operations if cache miss.

    Returns:
        Polars DataFrame.

    Raises:
        CacheNotWarmError: DataFrame unavailable after self-refresh.
    """
    assert self.strategy_factory is not None
    strategy = self.strategy_factory(entity_type)
    df = await strategy._get_dataframe(project_gid, client)
    if df is None:
        raise CacheNotWarmError(
            f"DataFrame unavailable for {entity_type}."
        )
    return df
```

### 7.3 QueryEngine Interface

```python
# query/engine.py

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.metrics.resolve import SectionIndex
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.errors import QueryEngineError, UnknownSectionError
from autom8_asana.query.guards import QueryLimits, predicate_depth
from autom8_asana.query.models import (
    PredicateNode,
    RowsMeta,
    RowsRequest,
    RowsResponse,
)
from autom8_asana.services.query_service import EntityQueryService
from autom8_asana.services.resolver import to_pascal_case

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

logger = get_logger(__name__)


@dataclass
class QueryEngine:
    """Orchestrates filtered row retrieval.

    Composes cache access, schema validation, predicate compilation,
    section scoping, and response shaping.
    """

    query_service: EntityQueryService = field(default_factory=EntityQueryService)
    compiler: PredicateCompiler = field(default_factory=PredicateCompiler)
    limits: QueryLimits = field(default_factory=QueryLimits)

    async def execute_rows(
        self,
        entity_type: str,
        project_gid: str,
        client: AsanaClient,
        request: RowsRequest,
        section_index: SectionIndex | None = None,
    ) -> RowsResponse:
        """Execute a /rows query.

        Flow:
        1. Validate predicate depth (fail-fast guard).
        2. Resolve section parameter to name filter.
        3. Load DataFrame via EntityQueryService.get_dataframe().
        4. Compile predicate AST to pl.Expr.
        5. Apply section filter + predicate filter.
        6. Apply pagination (offset/limit clamped to MAX_RESULT_ROWS).
        7. Select columns (gid always included).
        8. Build response with metadata.

        Args:
            entity_type: Entity type to query.
            project_gid: Project GID for cache lookup.
            client: AsanaClient for potential cache build.
            request: Validated RowsRequest.
            section_index: Pre-built section index (optional, built if needed).

        Returns:
            RowsResponse with data and metadata.

        Raises:
            QueryEngineError subclass for all domain errors.
            CacheNotWarmError if DataFrame unavailable.
        """
        start = time.monotonic()

        # 1. Depth guard (before any I/O)
        if request.where is not None:
            depth = predicate_depth(request.where)
            self.limits.check_depth(depth)

        # 2. Resolve section
        section_name_filter: str | None = None
        if request.section is not None:
            if section_index is None:
                # Caller should provide; fallback to enum
                section_index = SectionIndex.from_enum_fallback(entity_type)
            resolved_gid = section_index.resolve(request.section)
            if resolved_gid is None:
                raise UnknownSectionError(section=request.section)
            # EC-010: DataFrame section column stores NAMES, not GIDs.
            # We filter by the parameter name directly.
            section_name_filter = request.section

        # 3. Load DataFrame
        df = await self.query_service.get_dataframe(
            entity_type, project_gid, client,
        )

        # 4. Get schema for validation
        registry = SchemaRegistry.get_instance()
        schema = registry.get_schema(to_pascal_case(entity_type))

        # 5. Build filter expression
        filter_expr: pl.Expr | None = None
        if request.where is not None:
            filter_expr = self.compiler.compile(request.where, schema)

        # 6. Apply section filter (ANDed with predicate)
        if section_name_filter is not None:
            section_expr = pl.col("section") == section_name_filter
            if filter_expr is not None:
                # EC-006: Log warning if user also filtered on section in predicates
                filter_expr = section_expr & filter_expr
            else:
                filter_expr = section_expr

        # 7. Apply filter
        if filter_expr is not None:
            df = df.filter(filter_expr)

        # 8. Total count (before pagination)
        total_count = len(df)

        # 9. Clamp limit to MAX_RESULT_ROWS
        effective_limit = min(request.limit, self.limits.max_result_rows)

        # 10. Pagination
        df = df.slice(request.offset, effective_limit)

        # 11. Select columns (gid always included per PRD)
        select_fields = request.select or ["gid", "name", "section"]
        columns = list(dict.fromkeys(["gid"] + select_fields))  # dedupe, preserve order
        available = set(df.columns)
        valid_columns = [c for c in columns if c in available]

        # Validate select fields against schema
        for col_name in select_fields:
            if schema.get_column(col_name) is None:
                from autom8_asana.query.errors import UnknownFieldError
                raise UnknownFieldError(
                    field=col_name,
                    available=schema.column_names(),
                )

        df = df.select(valid_columns)

        # 12. Build response
        elapsed_ms = (time.monotonic() - start) * 1000
        data = df.to_dicts()

        return RowsResponse(
            data=data,
            meta=RowsMeta(
                total_count=total_count,
                returned_count=len(data),
                limit=effective_limit,
                offset=request.offset,
                entity_type=entity_type,
                project_gid=project_gid,
                query_ms=round(elapsed_ms, 2),
            ),
        )
```

### 7.4 Section Resolution -- EC-010 Clarification

The DataFrame `section` column stores **section names** (e.g., `"Active"`), not GIDs.

Resolution flow:
1. User passes `section: "Active"` in request.
2. `SectionIndex.resolve("Active")` returns GID `"1143843662099256"` -- this confirms the name is valid.
3. The filter applied to the DataFrame is `pl.col("section") == "Active"` -- matching by **name**.

This is a validation-then-match-by-name pattern. The SectionIndex exists to validate the name is legitimate, then we filter on the name itself.

---

## 8. Query Guards

```python
# query/guards.py

from dataclasses import dataclass

from autom8_asana.query.errors import QueryTooComplexError


@dataclass(frozen=True)
class QueryLimits:
    """Configurable query limits per FR-008."""

    max_predicate_depth: int = 5
    max_result_rows: int = 10_000

    def check_depth(self, depth: int) -> None:
        """Reject predicates exceeding max depth.

        Raises:
            QueryTooComplexError: If depth exceeds limit.
        """
        if depth > self.max_predicate_depth:
            raise QueryTooComplexError(
                depth=depth,
                max_depth=self.max_predicate_depth,
            )
```

---

## 9. Error Hierarchy

```python
# query/errors.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QueryEngineError(Exception):
    """Base error for all query engine domain errors.

    Subclasses define the error_code and HTTP status mapping.
    """
    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict for HTTP response."""
        raise NotImplementedError


@dataclass
class QueryTooComplexError(QueryEngineError):
    """Predicate tree exceeds max depth."""
    depth: int
    max_depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "QUERY_TOO_COMPLEX",
            "message": f"Predicate tree depth {self.depth} exceeds maximum of {self.max_depth}",
            "max_depth": self.max_depth,
        }


@dataclass
class UnknownFieldError(QueryEngineError):
    """Referenced field not in entity schema."""
    field: str
    available: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "UNKNOWN_FIELD",
            "message": f"Unknown field: {self.field}",
            "available_fields": sorted(self.available),
        }


@dataclass
class InvalidOperatorError(QueryEngineError):
    """Operator incompatible with field dtype."""
    field: str
    dtype: str
    op: str
    allowed: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "INVALID_OPERATOR",
            "message": f"Operator '{self.op}' not supported for {self.dtype} field '{self.field}'",
            "field": self.field,
            "field_dtype": self.dtype,
            "operator": self.op,
            "supported_operators": self.allowed,
        }


@dataclass
class CoercionError(QueryEngineError):
    """Value cannot be coerced to field dtype."""
    field: str
    dtype: str
    value: Any
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "COERCION_FAILED",
            "message": f"Cannot coerce {self.value!r} to {self.dtype} for field '{self.field}'",
            "field": self.field,
            "field_dtype": self.dtype,
            "value": self.value,
        }


@dataclass
class UnknownSectionError(QueryEngineError):
    """Section name cannot be resolved."""
    section: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "UNKNOWN_SECTION",
            "message": f"Unknown section: '{self.section}'",
            "section": self.section,
        }
```

### 9.1 Error to HTTP Status Mapping

| Error Class | HTTP Status | Error Code |
|-------------|:-----------:|------------|
| `QueryTooComplexError` | 400 | `QUERY_TOO_COMPLEX` |
| `UnknownFieldError` | 422 | `UNKNOWN_FIELD` |
| `InvalidOperatorError` | 422 | `INVALID_OPERATOR` |
| `CoercionError` | 422 | `COERCION_FAILED` |
| `UnknownSectionError` | 422 | `UNKNOWN_SECTION` |
| `CacheNotWarmError` | 503 | `CACHE_NOT_WARMED` |

---

## 10. Route Handler Design

### 10.1 Route Module

```python
# api/routes/query_v2.py

"""Query v2 routes: /rows (Sprint 1), /aggregate (Sprint 2), /metric (Sprint 3).

POST /v1/query/{entity_type}/rows -- Filtered row retrieval with composable predicates.
"""

from __future__ import annotations

from typing import Annotated

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from autom8_asana.api.routes.internal import ServiceClaims, require_service_claims
from autom8_asana.client import AsanaClient
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import QueryEngineError, QueryTooComplexError
from autom8_asana.query.models import RowsRequest, RowsResponse
from autom8_asana.services.query_service import CacheNotWarmError
from autom8_asana.services.resolver import EntityProjectRegistry, get_resolvable_entities

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/query", tags=["query-v2"])


# Error-to-status mapping
_ERROR_STATUS: dict[type[QueryEngineError], int] = {
    QueryTooComplexError: 400,
}
_DEFAULT_ERROR_STATUS = 422


def _error_to_response(error: QueryEngineError) -> HTTPException:
    """Map QueryEngineError to HTTPException."""
    status = _ERROR_STATUS.get(type(error), _DEFAULT_ERROR_STATUS)
    return HTTPException(status_code=status, detail=error.to_dict())


@router.post("/{entity_type}/rows", response_model=RowsResponse)
async def query_rows(
    entity_type: str,
    request_body: RowsRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> RowsResponse:
    """Query entity rows with composable predicate filtering.

    See PRD-dynamic-query-service FR-004.
    """
    # Validate entity type
    queryable = get_resolvable_entities()
    if entity_type not in queryable:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UNKNOWN_ENTITY_TYPE",
                "message": f"Unknown entity type: {entity_type}",
                "available_types": sorted(queryable),
            },
        )

    # Get project GID
    registry: EntityProjectRegistry | None = getattr(
        request.app.state, "entity_project_registry", None,
    )
    if registry is None or not registry.is_ready():
        raise HTTPException(status_code=503, detail={
            "error": "PROJECT_NOT_CONFIGURED",
            "message": "Entity project registry not initialized.",
        })

    project_gid = registry.get_project_gid(entity_type)
    if project_gid is None:
        raise HTTPException(status_code=503, detail={
            "error": "PROJECT_NOT_CONFIGURED",
            "message": f"No project configured for entity type: {entity_type}",
        })

    # Get bot PAT for cache operations
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

    try:
        bot_pat = get_bot_pat()
    except BotPATError:
        raise HTTPException(status_code=503, detail={
            "error": "SERVICE_NOT_CONFIGURED",
            "message": "Bot PAT not configured for cache operations.",
        })

    # Build section index (manifest-first, enum fallback)
    section_index = None
    if request_body.section is not None:
        from autom8_asana.dataframes.section_persistence import SectionPersistence
        from autom8_asana.metrics.resolve import SectionIndex

        persistence = SectionPersistence()
        section_index = await SectionIndex.from_manifest_async(persistence, project_gid)
        # Check if manifest had results; if not, fall back to enum
        if section_index.resolve(request_body.section) is None:
            section_index = SectionIndex.from_enum_fallback(entity_type)

    # Execute query
    engine = QueryEngine()
    try:
        async with AsanaClient(token=bot_pat) as client:
            result = await engine.execute_rows(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
                request=request_body,
                section_index=section_index,
            )
    except QueryEngineError as e:
        raise _error_to_response(e)
    except CacheNotWarmError as e:
        raise HTTPException(status_code=503, detail={
            "error": "CACHE_NOT_WARMED",
            "message": str(e),
            "retry_after_seconds": 30,
        })

    # Log query completion
    logger.info(
        "query_v2_rows_complete",
        extra={
            "entity_type": entity_type,
            "total_count": result.meta.total_count,
            "returned_count": result.meta.returned_count,
            "query_ms": result.meta.query_ms,
            "caller_service": claims.service_name,
            "predicate_depth": (
                predicate_depth(request_body.where) if request_body.where else 0
            ),
            "section": request_body.section,
        },
    )

    return result
```

### 10.2 Router Registration

Add to `src/autom8_asana/api/main.py` alongside existing routers:

```python
from autom8_asana.api.routes.query_v2 import router as query_v2_router

# In create_app(), after query_router:
app.include_router(query_v2_router)
```

### 10.3 Deprecation Headers on Existing Endpoint

Add deprecation headers to the existing `query_entities` response in `api/routes/query.py`:

```python
# After building response, before return:
response_headers = {
    "Deprecation": "true",
    "Sunset": "2026-06-01",
    "Link": '</v1/query/{entity_type}/rows>; rel="successor-version"',
}
# Apply via Response parameter in endpoint signature
```

---

## 11. Response Models

```python
# query/models.py (additions to section 3.2)

class RowsMeta(BaseModel):
    """Response metadata for /rows endpoint."""
    model_config = ConfigDict(extra="forbid")

    total_count: int
    returned_count: int
    limit: int
    offset: int
    entity_type: str
    project_gid: str
    query_ms: float


class RowsResponse(BaseModel):
    """Response body for /rows endpoint."""
    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]
    meta: RowsMeta
```

---

## 12. Sequence Diagram: /rows Request Flow

```
Client                Route Handler           QueryEngine           Compiler           EntityQueryService
  |                       |                       |                    |                      |
  |-- POST /rows -------->|                       |                    |                      |
  |                       |-- validate entity --->|                    |                      |
  |                       |-- resolve section --->|                    |                      |
  |                       |                       |                    |                      |
  |                       |-- execute_rows ------>|                    |                      |
  |                       |                       |-- check_depth ---->|                      |
  |                       |                       |                    |                      |
  |                       |                       |-- get_dataframe ---|--------------------->|
  |                       |                       |<-- DataFrame ------|--------------------<-|
  |                       |                       |                    |                      |
  |                       |                       |-- compile -------->|                      |
  |                       |                       |                    |-- validate fields    |
  |                       |                       |                    |-- validate ops       |
  |                       |                       |                    |-- coerce values      |
  |                       |                       |                    |-- build pl.Expr      |
  |                       |                       |<-- pl.Expr -----<-|                      |
  |                       |                       |                    |                      |
  |                       |                       |-- df.filter(expr)  |                      |
  |                       |                       |-- df.slice(o, l)   |                      |
  |                       |                       |-- df.select(cols)  |                      |
  |                       |                       |-- df.to_dicts()    |                      |
  |                       |                       |                    |                      |
  |                       |<-- RowsResponse ------|                    |                      |
  |<-- 200 JSON ----------|                       |                    |                      |
```

---

## 13. Test Strategy

### 13.1 Test Matrix

| Test File | Scope | Estimated Cases |
|-----------|-------|:---------------:|
| `test_models.py` | PredicateNode parsing, sugar, depth validation, extra="forbid" | ~18 |
| `test_compiler.py` | Operator x dtype matrix (80 cells), coercion (12 rules), expression assembly | ~35 |
| `test_engine.py` | QueryEngine with mocked EntityQueryService, section resolution, pagination | ~15 |
| `test_guards.py` | Depth enforcement, row limit clamping | ~6 |
| `test_errors.py` | Error serialization, to_dict() output | ~6 |
| `test_query_v2.py` | End-to-end /rows via TestClient (happy + error paths) | ~12 |
| **Total** | | **~92** |

### 13.2 Key Test Categories

**Model parsing tests** (`test_models.py`):
- Comparison leaf parses correctly
- AND/OR/NOT group nodes parse with nested children
- Flat-array sugar wraps to AND
- Empty array becomes None (no filter)
- Extra fields rejected (extra="forbid")
- Depth calculation for various tree shapes

**Compiler matrix tests** (`test_compiler.py`):
- For each dtype: test all 10 operators, expecting success or `InvalidOperatorError`
- Value coercion: string->Date, string->Datetime, number->Int64, bool->Boolean, list coercion
- Coercion failure: "abc"->Int64, non-ISO date string, etc.
- Expression assembly: AND combines with `&`, OR with `|`, NOT with `~`
- Empty AND/OR return identity expressions

**Engine integration tests** (`test_engine.py`):
- Section resolution with name-based filtering
- Section parameter + predicate section conflict (warning logged)
- Pagination with offset/limit
- MAX_RESULT_ROWS clamping
- Select field validation
- gid always included in response

### 13.3 Example Test Case

```python
# tests/unit/query/test_compiler.py

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.compiler import PredicateCompiler
from autom8_asana.query.errors import InvalidOperatorError
from autom8_asana.query.models import Comparison, Op


@pytest.fixture
def offer_schema() -> DataFrameSchema:
    """Minimal schema for compiler tests."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("mrr", "Utf8", nullable=True),
            ColumnDef("is_completed", "Boolean", nullable=False),
            ColumnDef("date", "Date", nullable=True),
        ],
    )


class TestCompilerComparison:
    """Test Comparison leaf -> pl.Expr compilation."""

    def test_eq_utf8(self, offer_schema: DataFrameSchema) -> None:
        """eq on Utf8 field produces equality expression."""
        compiler = PredicateCompiler()
        node = Comparison(field="name", op=Op.EQ, value="Acme")
        expr = compiler.compile(node, offer_schema)

        df = pl.DataFrame({"name": ["Acme", "Beta", "Acme"]})
        result = df.filter(expr)
        assert len(result) == 2
        assert result["name"].to_list() == ["Acme", "Acme"]

    def test_gt_on_boolean_raises(self, offer_schema: DataFrameSchema) -> None:
        """gt on Boolean field raises InvalidOperatorError."""
        compiler = PredicateCompiler()
        node = Comparison(field="is_completed", op=Op.GT, value=True)

        with pytest.raises(InvalidOperatorError) as exc_info:
            compiler.compile(node, offer_schema)

        assert exc_info.value.field == "is_completed"
        assert exc_info.value.dtype == "Boolean"
        assert exc_info.value.op == "gt"

    def test_contains_on_utf8(self, offer_schema: DataFrameSchema) -> None:
        """contains on Utf8 field produces str.contains expression."""
        compiler = PredicateCompiler()
        node = Comparison(field="name", op=Op.CONTAINS, value="cm")
        expr = compiler.compile(node, offer_schema)

        df = pl.DataFrame({"name": ["Acme", "Beta", "Acme Dental"]})
        result = df.filter(expr)
        assert len(result) == 2
```

---

## 14. Performance Considerations

### 14.1 Target Latency (Sprint 1)

Per NFR-001, `/rows` targets:
- p50 < 50ms (cache hit, < 1000 rows, depth <= 3)
- p99 < 200ms (cache hit)

### 14.2 Hot Path Analysis

| Step | Expected Cost | Notes |
|------|:------------:|-------|
| Depth check | < 0.01ms | Tree walk, max 5 levels |
| Section resolution | < 0.1ms | In-memory dict lookup |
| `get_dataframe()` | 0ms (cache hit) | Already materialized in memory |
| Predicate compilation | < 0.5ms | Tree walk + expr construction |
| `df.filter()` | 1-20ms | Polars vectorized, depends on DataFrame size |
| `df.slice()` | < 0.1ms | Offset pointer, no copy |
| `df.select()` | < 0.1ms | Column projection |
| `df.to_dicts()` | 1-10ms | Serialization, depends on row count |
| **Total** | **3-30ms** | Well within p50 target |

### 14.3 What We Are NOT Doing

- **Lazy evaluation**: DataFrames are already materialized in cache. Lazy adds overhead for small frames.
- **Expression caching**: Predicate trees are cheap to compile. Caching adds complexity for minimal gain.
- **Parallel compilation**: Tree depth is max 5. Sequential compilation is faster than parallelization overhead.

---

## 15. Architecture Decision Records

### ADR-QE-001: Package Location

**Context**: The query engine needs a home. Options: (A) extend `services/query_service.py`, (B) new `services/query_engine.py`, (C) new top-level `query/` package.

**Decision**: (C) New `src/autom8_asana/query/` package.

**Rationale**: The query engine owns models, compilation, orchestration, guards, and errors -- too much for a single service file. A dedicated package provides clear module boundaries. Sprint 2/3 will add `aggregate.py` and `metric_bridge.py` here without polluting the services layer.

**Consequences**: New import path `autom8_asana.query.*`. One more package to maintain, but clear ownership.

### ADR-QE-002: Pydantic v2 Discriminated Union Strategy

**Context**: PredicateNode is a union of 4 types (Comparison, AndGroup, OrGroup, NotGroup) with no shared discriminator field. Options: (A) `Union[...]` with Pydantic trying each type, (B) wrapper model with explicit `type` field, (C) `Discriminator` with callable.

**Decision**: (C) `Discriminator` with a callable that inspects dict keys.

**Rationale**: (A) relies on try/except ordering and is fragile with `extra="forbid"`. (B) requires callers to add a `type` field, breaking the clean PRD schema. (C) inspects `{"and": ...}`, `{"or": ...}`, `{"not": ...}`, or `{"field": ...}` deterministically in O(1) and matches the PRD JSON format exactly.

**Consequences**: The discriminator function must be maintained if new node types are added (Sprint 2+ may add `is_null`).

### ADR-QE-003: Section Column Semantics

**Context**: EC-010 clarifies that the DataFrame `section` column stores **names** (e.g., "Active"), not GIDs. The `section` request parameter needs to filter this column.

**Decision**: Use SectionIndex for **validation only** (confirm name is legitimate), then filter by `pl.col("section") == section_name`.

**Rationale**: Since the column stores names, filtering by GID would never match. The SectionIndex validates that the user-provided name corresponds to a known section, preventing typos. The actual filter uses the name directly.

**Consequences**: If the DataFrame column ever changes to store GIDs (unlikely given Asana's membership structure), the filter logic would need updating. This is documented as a known coupling.

### ADR-QE-004: EntityQueryService Public DataFrame Method

**Context**: `QueryEngine` needs the raw DataFrame, but `EntityQueryService` only exposes it through `query()` which applies its own filters. Calling `strategy._get_dataframe()` directly violates encapsulation.

**Decision**: Add `EntityQueryService.get_dataframe()` as a public method wrapping `strategy._get_dataframe()`.

**Rationale**: This is a minimal, backward-compatible change. The existing `query()` method continues to work. New consumers get a clean public API. The private `_get_dataframe()` call is encapsulated in one place.

**Consequences**: `EntityQueryService` gains a second public method. This is acceptable given its role as the cache-access primitive.

---

## 16. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Pydantic v2 discriminator edge cases | Medium | Medium | Extensive test_models.py coverage (~18 cases); fallback to try/except union if issues arise |
| mrr column dtype mismatch | High | Low | Offer schema declares `mrr` as `Utf8` (not numeric). Coercion handles string comparisons correctly. Document that numeric comparison on mrr requires Utf8 ordering. |
| Section name case sensitivity | Medium | Low | `SectionIndex.resolve()` is case-insensitive. Filter on DataFrame column is case-sensitive. Document: section param must match DataFrame casing exactly (e.g., "Active" not "active"). |
| Large DataFrame serialization | Low | Medium | `to_dicts()` on 10k rows is ~50ms worst case. Acceptable for Sprint 1. Lazy eval in Sprint 2 if needed. |
| Circular import risk | Low | Low | `query/` imports from `services/`, `dataframes/`, `metrics/` -- all downstream. No back-imports needed. |

---

## 17. Open Questions (Resolved)

| # | Question | Resolution |
|---|----------|------------|
| 1 | Does `section` column store names or GIDs? | **Names** (per EC-010 clarification). Filter by name match. |
| 2 | Should `order_by`/`order_dir` be in Sprint 1? | **No** (PRD Sprint 1 scope explicitly defers this). RowsRequest includes the fields but engine ignores them in Sprint 1. |
| 3 | How to handle `mrr` being Utf8 but used for numeric queries? | Coerce to Utf8 for comparison. Ordering on Utf8 is lexicographic. Document this limitation. Numeric dtype migration is a separate initiative. |
| 4 | Should the compiler be stateless or carry schema context? | **Stateless**. Schema passed per-call allows one compiler instance to serve all entity types. |

---

## 18. Handoff Checklist

- [x] Module structure finalized with rationale (Section 2, ADR-QE-001)
- [x] PredicateNode schema with Pydantic v2 discriminator example code (Section 3)
- [x] Operator x dtype matrix explicitly defined (Section 4)
- [x] Coercion rules per dtype with examples (Section 5)
- [x] QueryEngine interface complete (Section 7)
- [x] Route handler design (Section 10)
- [x] Test strategy with count estimates (~92 cases) (Section 13)
- [x] Sample test case included (Section 13.3)
- [x] No blocking open questions (Section 17)
- [x] ADRs for all significant decisions (Section 15)
- [x] Risks identified with mitigations (Section 16)
- [x] Sequence diagram for /rows flow (Section 12)
- [x] Error hierarchy with HTTP mapping (Section 9)

---

## Attestation Table

| File | Absolute Path | Read |
|------|---------------|:----:|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-query-service.md` | Yes |
| Query Service | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Yes |
| Query Route | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/query.py` | Yes |
| Schema Registry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Yes |
| Schema Model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Yes |
| Section Resolve | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/resolve.py` | Yes |
| OfferSection | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/sections.py` | Yes |
| Auth (internal) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/internal.py` | Yes |
| Router Registration | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` (lines 1340-1380) | Yes |
| Base Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/base.py` | Yes |
| Offer Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/offer.py` | Yes |
| Resolver | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes |
