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
from autom8_asana.models.business.sections import OfferSection

# Shared scope: ACTIVE offers deduped by (office_phone, vertical)
_ACTIVE_OFFER_SCOPE = Scope(
    entity_type="offer",
    section=OfferSection.ACTIVE.value,
    dedup_keys=["office_phone", "vertical"],
)

ACTIVE_MRR = Metric(
    name="active_mrr",
    description="Total MRR for ACTIVE offers, deduped by phone+vertical",
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
    description="Total weekly ad spend for ACTIVE offers, deduped by phone+vertical",
    expr=MetricExpr(
        name="sum_weekly_ad_spend",
        column="weekly_ad_spend",
        cast_dtype=pl.Float64,
        agg="sum",
        filter_expr=(
            pl.col("weekly_ad_spend").is_not_null()
            & (pl.col("weekly_ad_spend") > 0)
        ),
    ),
    scope=_ACTIVE_OFFER_SCOPE,
)

# Auto-register with singleton
_registry = MetricRegistry()
_registry.register(ACTIVE_MRR)
_registry.register(ACTIVE_AD_SPEND)
