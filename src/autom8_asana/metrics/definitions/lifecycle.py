"""Lifecycle pipeline metric definitions.

Per ADR-omniscience-lifecycle-observation Decision 2:
Registered automatically when autom8_asana.metrics.definitions is imported
(triggered by MetricRegistry._ensure_initialized).

Metrics defined here:
- outreach_to_sales_conversion: Count of converted transitions outreach -> sales
- sales_to_onboarding_conversion: Count of converted transitions sales -> onboarding
- onboarding_to_implementation_conversion: Count of converted transitions onboarding -> impl
- stage_duration_median: Median days spent in a stage (completed intervals only)
- stage_duration_p95: 95th percentile days in a stage (completed intervals only)
- stalled_entities: Count of entities stuck in current stage beyond threshold
- weekly_transitions: Total weekly pipeline throughput

All metrics operate on the stage_transition entity type (parquet-backed).
Conversion rate (numerator/denominator) is computed by the caller, not embedded
in a single MetricExpr, because MetricExpr produces a single scalar aggregation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl

from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry

# Shared scope for stage_transition entity type
_STAGE_TRANSITION_SCOPE = Scope(
    entity_type="stage_transition",
)

_STAGE_TRANSITION_DEDUP_SCOPE = Scope(
    entity_type="stage_transition",
    dedup_keys=["entity_gid"],
)


# ---------------------------------------------------------------------------
# Conversion metrics (one per stage pair)
# ---------------------------------------------------------------------------

OUTREACH_TO_SALES_CONVERSION = Metric(
    name="outreach_to_sales_conversion",
    description="Count of businesses converting from outreach to sales",
    expr=MetricExpr(
        name="count_converted",
        column="entity_gid",
        agg="count",
        filter_expr=(
            (pl.col("from_stage") == "outreach")
            & (pl.col("to_stage") == "sales")
            & (pl.col("transition_type") == "converted")
        ),
    ),
    scope=_STAGE_TRANSITION_DEDUP_SCOPE,
)

SALES_TO_ONBOARDING_CONVERSION = Metric(
    name="sales_to_onboarding_conversion",
    description="Count of businesses converting from sales to onboarding",
    expr=MetricExpr(
        name="count_converted",
        column="entity_gid",
        agg="count",
        filter_expr=(
            (pl.col("from_stage") == "sales")
            & (pl.col("to_stage") == "onboarding")
            & (pl.col("transition_type") == "converted")
        ),
    ),
    scope=_STAGE_TRANSITION_DEDUP_SCOPE,
)

ONBOARDING_TO_IMPLEMENTATION_CONVERSION = Metric(
    name="onboarding_to_implementation_conversion",
    description="Count of businesses converting from onboarding to implementation",
    expr=MetricExpr(
        name="count_converted",
        column="entity_gid",
        agg="count",
        filter_expr=(
            (pl.col("from_stage") == "onboarding")
            & (pl.col("to_stage") == "implementation")
            & (pl.col("transition_type") == "converted")
        ),
    ),
    scope=_STAGE_TRANSITION_DEDUP_SCOPE,
)


# ---------------------------------------------------------------------------
# Duration metrics
# ---------------------------------------------------------------------------

STAGE_DURATION_MEDIAN = Metric(
    name="stage_duration_median",
    description="Median days spent in a stage (configurable via filter)",
    expr=MetricExpr(
        name="median_duration_days",
        column="duration_days",
        cast_dtype=pl.Float64,
        agg="median",
        filter_expr=pl.col("exited_at").is_not_null(),
    ),
    scope=_STAGE_TRANSITION_SCOPE,
)

STAGE_DURATION_P95 = Metric(
    name="stage_duration_p95",
    description="95th percentile days spent in a stage",
    expr=MetricExpr(
        name="p95_duration_days",
        column="duration_days",
        cast_dtype=pl.Float64,
        agg="quantile",
        quantile_value=0.95,
        filter_expr=pl.col("exited_at").is_not_null(),
    ),
    scope=_STAGE_TRANSITION_SCOPE,
)


# ---------------------------------------------------------------------------
# Stall detection
# ---------------------------------------------------------------------------


def _stall_filter(threshold_days: int = 30) -> pl.Expr:
    """Build a filter expression for stall detection.

    Selects entities with:
    - exited_at IS NULL (still in stage)
    - entered_at older than threshold_days ago

    Args:
        threshold_days: Number of days before an entity is considered stalled.

    Returns:
        Polars filter expression.
    """
    cutoff = datetime.now(UTC) - timedelta(days=threshold_days)
    return pl.col("exited_at").is_null() & (pl.col("entered_at") < cutoff)


STALLED_ENTITIES = Metric(
    name="stalled_entities",
    description="Count of entities stuck in current stage beyond 30-day threshold",
    expr=MetricExpr(
        name="stalled_count",
        column="entity_gid",
        agg="count",
        filter_expr=_stall_filter(30),
    ),
    scope=_STAGE_TRANSITION_DEDUP_SCOPE,
)


# ---------------------------------------------------------------------------
# Throughput metric
# ---------------------------------------------------------------------------

WEEKLY_TRANSITIONS = Metric(
    name="weekly_transitions",
    description="Count of stage transitions (total pipeline throughput)",
    expr=MetricExpr(
        name="transition_count",
        column="entity_gid",
        agg="count",
    ),
    scope=_STAGE_TRANSITION_SCOPE,
)


# ---------------------------------------------------------------------------
# Auto-register with singleton
# ---------------------------------------------------------------------------

_registry = MetricRegistry()
_registry.register(OUTREACH_TO_SALES_CONVERSION)
_registry.register(SALES_TO_ONBOARDING_CONVERSION)
_registry.register(ONBOARDING_TO_IMPLEMENTATION_CONVERSION)
_registry.register(STAGE_DURATION_MEDIAN)
_registry.register(STAGE_DURATION_P95)
_registry.register(STALLED_ENTITIES)
_registry.register(WEEKLY_TRANSITIONS)
