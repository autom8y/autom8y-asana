"""compute_metric: execute a metric against a DataFrame.

Applies filtering, deduplication, and sorting per the metric's Scope
and MetricExpr configuration. Returns a DataFrame for caller aggregation.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import polars as pl
from autom8y_telemetry import trace_computation

if TYPE_CHECKING:
    from autom8_asana.metrics.metric import Metric


@trace_computation(
    "metric.compute", record_dataframe_shape=True, df_param="df", engine="autom8y-asana"
)
def compute_metric(
    metric: Metric,
    df: pl.DataFrame,
    *,
    verbose: bool = False,
) -> pl.DataFrame:
    """Execute a metric against a DataFrame, returning deduped/filtered rows.

    This function applies the metric's filter, deduplication, and sorting
    logic but does NOT compute the final aggregate scalar. The caller is
    responsible for aggregation (e.g., df["mrr"].sum()) so it can also
    inspect row-level data in verbose mode.

    Processing pipeline:
        1. Select relevant columns (dedup keys + metric column + "name" for display)
        2. Cast metric column to target dtype (if cast_dtype is set)
        3. Apply MetricExpr.filter_expr (row-level filter)
        4. Apply Scope.pre_filters (additional filters, ANDed)
        5. Deduplicate by Scope.dedup_keys (keep="first")
        6. Sort by dedup_keys for deterministic output

    Args:
        metric: The Metric definition to compute.
        df: Input DataFrame (typically a section parquet).
        verbose: If True, print the per-row breakdown to stdout using
            the same Polars Config as the original scripts.

    Returns:
        Filtered, deduped, sorted DataFrame containing the metric column
        and relevant context columns. Caller can then aggregate:
            total = result[metric.expr.column].sum()

    Raises:
        pl.exceptions.ColumnNotFoundError: If metric.expr.column or any
            dedup_key is missing from the DataFrame.
    """
    from opentelemetry import trace as _otel_trace

    _span = _otel_trace.get_current_span()
    _metric_start = time.perf_counter()

    expr = metric.expr
    scope = metric.scope

    # Step 0.5: Classification filter (applied before column selection)
    if scope.classification is not None:
        if "section" not in df.columns:
            raise ValueError(
                f"Classification filter requires 'section' column, "
                f"but DataFrame has columns: {df.columns}"
            )
        from autom8_asana.models.business.activity import CLASSIFIERS, AccountActivity

        classifier = CLASSIFIERS.get(scope.entity_type)
        if classifier is None:
            raise ValueError(f"No classifier for entity type '{scope.entity_type}'")
        sections = classifier.sections_for(AccountActivity(scope.classification))
        df = df.filter(pl.col("section").str.to_lowercase().is_in(list(sections)))

    # Step 1: Select relevant columns
    # Include "name" for display if present, plus dedup keys and metric column
    select_cols: list[str] = []
    if "name" in df.columns:
        select_cols.append("name")
    if scope.dedup_keys:
        select_cols.extend(scope.dedup_keys)
    select_cols.append(expr.column)

    # Deduplicate column list while preserving order
    seen: set[str] = set()
    unique_cols: list[str] = []
    for c in select_cols:
        if c not in seen:
            seen.add(c)
            unique_cols.append(c)
    result = df.select(unique_cols)

    # Step 2: Cast metric column if needed
    if expr.cast_dtype is not None:
        result = result.with_columns(
            pl.col(expr.column).cast(expr.cast_dtype, strict=False).alias(expr.column)
        )

    # Step 3: Apply MetricExpr filter
    if expr.filter_expr is not None:
        result = result.filter(expr.filter_expr)

    # Step 4: Apply Scope pre_filters
    if scope.pre_filters:
        for f in scope.pre_filters:
            result = result.filter(f)

    # Step 5: Deduplicate
    if scope.dedup_keys:
        result = result.unique(subset=scope.dedup_keys, keep="first")

    # Step 6: Sort for deterministic output
    if scope.dedup_keys:
        result = result.sort(scope.dedup_keys)

    # Verbose output (matches original script format)
    if verbose:
        with pl.Config(tbl_rows=200, tbl_cols=10, fmt_str_lengths=30):
            print(result)
        print()

    _span.set_attribute("computation.duration_ms", (time.perf_counter() - _metric_start) * 1000)
    return result
