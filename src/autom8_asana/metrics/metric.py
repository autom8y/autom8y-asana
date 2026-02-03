"""Scope and Metric: data scope and named metric definitions.

Scope controls which data is loaded and how rows are deduplicated.
Metric combines a MetricExpr with a Scope under a registry-friendly name.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import polars as pl

from autom8_asana.metrics.expr import MetricExpr


@dataclass(frozen=True)
class Scope:
    """Defines where and how a metric applies.

    Scope controls which data is loaded (entity_type + section) and
    how rows are deduplicated before aggregation.

    Attributes:
        entity_type: The entity type whose project contains the data.
            Maps to a project GID via OfferSection or future section enums.
            Phase 1 supports "offer" only.
        section: Section GID string (e.g., "1143843662099256" for ACTIVE).
            None means "all sections" (not implemented in Phase 1).
        dedup_keys: Column names for row uniqueness. Rows are deduplicated
            using these columns with keep="first" after sorting.
            None means no deduplication.
        pre_filters: Additional Polars filter expressions applied before
            deduplication. These are ANDed together with MetricExpr.filter_expr.

    Example:
        >>> scope = Scope(
        ...     entity_type="offer",
        ...     section="1143843662099256",
        ...     dedup_keys=["office_phone", "vertical"],
        ... )
    """

    entity_type: str
    section: str | None = None
    section_name: str | None = None
    dedup_keys: list[str] | None = field(default=None)
    pre_filters: list[pl.Expr] | None = field(default=None)

    def with_resolved_section(self, gid: str) -> Scope:
        """Return a new Scope with section set to *gid*."""
        return replace(self, section=gid)


@dataclass(frozen=True)
class Metric:
    """A named, scoped metric definition.

    Combines a MetricExpr (what to compute) with a Scope (where to compute it)
    under a registry-friendly name.

    Attributes:
        name: Registry key, used as CLI argument (e.g., "active_mrr").
            Must be unique within the MetricRegistry. Convention: snake_case.
        description: Human-readable description shown in --list output
            and error messages.
        expr: The MetricExpr defining the column, cast, filter, and aggregation.
        scope: The Scope defining entity type, section, dedup, and pre-filters.

    Example:
        >>> metric = Metric(
        ...     name="active_mrr",
        ...     description="Total MRR for ACTIVE offers, deduped by phone+vertical",
        ...     expr=MetricExpr(
        ...         name="sum_mrr", column="mrr",
        ...         cast_dtype=pl.Float64, agg="sum",
        ...         filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0),
        ...     ),
        ...     scope=Scope(
        ...         entity_type="offer",
        ...         section="1143843662099256",
        ...         dedup_keys=["office_phone", "vertical"],
        ...     ),
        ... )
    """

    name: str
    description: str
    expr: MetricExpr
    scope: Scope
