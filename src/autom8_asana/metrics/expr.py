"""MetricExpr: a single column aggregation expression.

Encapsulates column selection, optional type cast, optional row filter,
and aggregation function needed to compute one scalar from a DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


# Supported aggregation functions
SUPPORTED_AGGS: frozenset[str] = frozenset({"sum", "count", "mean", "min", "max"})


@dataclass(frozen=True)
class MetricExpr:
    """A single column aggregation expression.

    Encapsulates the column selection, optional type cast, optional row filter,
    and aggregation function needed to compute one scalar from a DataFrame.

    Attributes:
        name: Expression identifier used in output (e.g., "sum_mrr").
        column: Source column name in the DataFrame (e.g., "mrr").
        cast_dtype: If set, cast column to this Polars dtype before aggregation.
            Use pl.Float64 for financial columns to handle string-encoded numbers.
        agg: Aggregation function name. Must be one of SUPPORTED_AGGS.
        filter_expr: Optional Polars expression applied as row filter BEFORE
            aggregation. Rows where this evaluates to False are excluded.

    Example:
        >>> expr = MetricExpr(
        ...     name="sum_mrr",
        ...     column="mrr",
        ...     cast_dtype=pl.Float64,
        ...     agg="sum",
        ...     filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
        ... )
        >>> polars_expr = expr.to_polars_expr()
    """

    name: str
    column: str
    cast_dtype: pl.DataType | None = None
    agg: str = "sum"
    filter_expr: pl.Expr | None = None

    def __post_init__(self) -> None:
        """Validate agg is a supported aggregation."""
        if self.agg not in SUPPORTED_AGGS:
            raise ValueError(
                f"Unsupported aggregation '{self.agg}'. "
                f"Must be one of: {', '.join(sorted(SUPPORTED_AGGS))}"
            )

    def to_polars_expr(self) -> pl.Expr:
        """Build a Polars aggregation expression.

        Constructs a chained Polars expression that:
        1. Selects self.column
        2. Casts to self.cast_dtype (if set)
        3. Applies the aggregation function named by self.agg

        NOTE: filter_expr is NOT applied here. Filtering happens in
        compute_metric() at the DataFrame level, because deduplication
        must occur between filtering and aggregation.

        Returns:
            Polars expression ready for use in .select() or .agg().
        """
        e = pl.col(self.column)

        if self.cast_dtype is not None:
            e = e.cast(self.cast_dtype, strict=False)

        # Apply aggregation
        e = getattr(e, self.agg)()

        return e.alias(self.name)
