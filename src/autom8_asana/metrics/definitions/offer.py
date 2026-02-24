"""Offer-level metric definitions.

Registered automatically when autom8_asana.metrics.definitions is imported
(triggered by MetricRegistry._ensure_initialized).

Metrics defined here:
- active_mrr: Total MRR for ACTIVE offers
- active_ad_spend: Total weekly ad spend for ACTIVE offers
"""

from __future__ import annotations

import polars as pl

from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry

# Shared scope: ACTIVE-classified offers deduped by (office_phone, vertical)
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    classification="active",
    dedup_keys=["office_phone", "vertical"],
)

ACTIVE_MRR = Metric(
    name="active_mrr",
    description=(
        "Total MRR for ACTIVE offers, deduped by phone+vertical. "
        "MRR lives at the Unit level; multiple Offers under one Unit share "
        "the same MRR value. Without dedup by (office_phone, vertical) -- "
        "the PVP that uniquely identifies a Unit -- sums are inflated "
        "proportional to the number of offers per unit."
    ),
    expr=MetricExpr(
        name="sum_mrr",
        column="mrr",
        cast_dtype=pl.Float64,
        agg="sum",
        filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
    ),
    scope=_ACTIVE_OFFER_SCOPE,
)

ACTIVE_AD_SPEND = Metric(
    name="active_ad_spend",
    description=(
        "Total weekly ad spend for ACTIVE offers, deduped by phone+vertical. "
        "Same dedup rationale as ACTIVE_MRR: ad spend is a Unit-level value "
        "shared across sibling Offers."
    ),
    expr=MetricExpr(
        name="sum_weekly_ad_spend",
        column="weekly_ad_spend",
        cast_dtype=pl.Float64,
        agg="sum",
        filter_expr=(
            pl.col("weekly_ad_spend").is_not_null() & (pl.col("weekly_ad_spend") > 0)
        ),
    ),
    scope=_ACTIVE_OFFER_SCOPE,
)

# Auto-register with singleton
_registry = MetricRegistry()
_registry.register(ACTIVE_MRR)
_registry.register(ACTIVE_AD_SPEND)
