"""Aggregation expression compilation: AggSpec list -> pl.Expr list.

Translates AggSpec models into Polars aggregation expressions for use
with DataFrame.group_by().agg(). Validates dtype compatibility before
building expressions.

ADR-AGG-001: Separate module from compiler.py (predicate vs aggregation concerns).
ADR-AGG-005: Utf8 columns cast to Float64 for sum/mean/min/max (financial columns).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from autom8_asana.query.errors import AggregationError
from autom8_asana.query.models import AggFunction, AggSpec

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema

__all__ = [
    "AGG_COMPATIBILITY",
    "AggregationCompiler",
    "build_post_agg_schema",
    "validate_alias_uniqueness",
]

# ---------------------------------------------------------------------------
# Aggregation function x dtype compatibility matrix (TDD Section 5)
# ---------------------------------------------------------------------------

_NUMERIC_AGGS = frozenset({AggFunction.SUM, AggFunction.MEAN})
_ORDERABLE_AGGS = frozenset({AggFunction.MIN, AggFunction.MAX})
_UNIVERSAL_AGGS = frozenset({AggFunction.COUNT, AggFunction.COUNT_DISTINCT})
_ALL_NON_LIST = _NUMERIC_AGGS | _ORDERABLE_AGGS | _UNIVERSAL_AGGS

# ADR-AGG-005: Utf8 permitted for all non-list aggs; sum/mean/min/max cast
# to Float64 before aggregation (handles string-encoded financial columns).
AGG_COMPATIBILITY: dict[str, frozenset[AggFunction]] = {
    "Utf8": _ALL_NON_LIST,
    "Int64": _ALL_NON_LIST,
    "Int32": _ALL_NON_LIST,
    "Float64": _ALL_NON_LIST,
    "Boolean": _UNIVERSAL_AGGS,
    "Date": _ORDERABLE_AGGS | _UNIVERSAL_AGGS,
    "Datetime": _ORDERABLE_AGGS | _UNIVERSAL_AGGS,
    "Decimal": _ALL_NON_LIST,
    "List[Utf8]": frozenset(),
}

# Agg functions that require Utf8 -> Float64 cast before application
_UTF8_CAST_AGGS = frozenset(
    {
        AggFunction.SUM,
        AggFunction.MEAN,
        AggFunction.MIN,
        AggFunction.MAX,
    }
)


# ---------------------------------------------------------------------------
# AggregationCompiler
# ---------------------------------------------------------------------------


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
            AggregationError: If column does not exist, or agg function
                is incompatible with column dtype.
        """
        return [self._compile_one(spec, schema) for spec in specs]

    def _compile_one(
        self,
        spec: AggSpec,
        schema: DataFrameSchema,
    ) -> pl.Expr:
        """Compile a single AggSpec to a pl.Expr."""
        # 1. Validate column exists
        col_def = schema.get_column(spec.column)
        if col_def is None:
            raise AggregationError(
                f"Unknown column '{spec.column}' for aggregation. "
                f"Available: {sorted(schema.column_names())}"
            )

        # 2. Validate agg function compatibility with dtype
        allowed_aggs = AGG_COMPATIBILITY.get(col_def.dtype, frozenset())
        if spec.agg not in allowed_aggs:
            raise AggregationError(
                f"Aggregation function '{spec.agg.value}' not supported "
                f"for {col_def.dtype} column '{spec.column}'. "
                f"Supported: {sorted(a.value for a in allowed_aggs)}"
            )

        # 3. Build expression with optional Utf8 cast
        return _build_agg_expr(
            spec.column,
            spec.agg,
            col_def.dtype,
            spec.resolved_alias,
        )


def _build_agg_expr(
    column: str,
    agg: AggFunction,
    dtype: str,
    alias: str,
) -> pl.Expr:
    """Build a single Polars aggregation expression.

    For Utf8 columns with numeric aggregations (sum, mean, min, max),
    casts to Float64 first. This handles string-encoded financial columns
    like mrr, cost, weekly_ad_spend.

    ADR-AGG-005: strict=False ensures non-numeric strings become null
    rather than raising, consistent with MetricExpr.to_polars_expr().
    """
    col = pl.col(column)

    # Cast Utf8 to Float64 for numeric/orderable aggregations
    if dtype == "Utf8" and agg in _UTF8_CAST_AGGS:
        col = col.cast(pl.Float64, strict=False)

    match agg:
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

    raise ValueError(f"Unknown aggregation function: {agg}")  # pragma: no cover


# ---------------------------------------------------------------------------
# Alias uniqueness validation (TDD Section 6.4)
# ---------------------------------------------------------------------------


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
            raise AggregationError(f"Alias '{alias}' collides with group_by column")
        seen.add(alias)


# ---------------------------------------------------------------------------
# HAVING support: synthetic post-aggregation schema (TDD Section 6.3)
# ---------------------------------------------------------------------------


def build_post_agg_schema(
    group_by_columns: list[str],
    agg_specs: list[AggSpec],
    source_schema: DataFrameSchema,
) -> DataFrameSchema:
    """Build a synthetic schema representing the aggregated output.

    This schema is used to validate HAVING predicates against the
    post-aggregation column names and their inferred dtypes.

    ADR-AGG-002: Reuses PredicateCompiler via this synthetic schema
    rather than building a separate HAVING compiler.

    Args:
        group_by_columns: Columns used in group_by (retain source dtype).
        agg_specs: Aggregation specifications (determine output column dtypes).
        source_schema: Original entity schema for dtype lookup.

    Returns:
        DataFrameSchema with columns representing the aggregated output.
    """
    from autom8_asana.dataframes.models.schema import (
        ColumnDef,
    )
    from autom8_asana.dataframes.models.schema import (
        DataFrameSchema as DFSchema,
    )

    columns: list[ColumnDef] = []

    # group_by columns retain their source dtype
    for col_name in group_by_columns:
        source_col = source_schema.get_column(col_name)
        if source_col is not None:
            columns.append(
                ColumnDef(
                    name=col_name,
                    dtype=source_col.dtype,
                    nullable=source_col.nullable,
                )
            )

    # Aggregation output columns with inferred dtypes
    for spec in agg_specs:
        alias = spec.resolved_alias
        output_dtype = _infer_agg_output_dtype(spec, source_schema)
        columns.append(
            ColumnDef(
                name=alias,
                dtype=output_dtype,
                nullable=True,
            )
        )

    return DFSchema(
        name="__aggregate_output__",
        task_type="*",
        columns=columns,
    )


def _infer_agg_output_dtype(spec: AggSpec, schema: DataFrameSchema) -> str:
    """Infer the output dtype of an aggregation expression.

    Follows TDD Section 5.3:
    - count/count_distinct -> Int64
    - mean -> Float64
    - sum on Float64/Decimal/Utf8 -> Float64; on Int64/Int32 -> Int64
    - min/max on Utf8 (cast) -> Float64; otherwise same as input
    """
    source_col = schema.get_column(spec.column)
    source_dtype = source_col.dtype if source_col else "Float64"

    match spec.agg:
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
