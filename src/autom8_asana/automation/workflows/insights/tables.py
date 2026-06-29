"""Declarative table specifications for the insights export.

Per TDD-SPRINT-C Section 1: centralizes the table configuration for both fetch
dispatch (F-03) and display preparation (F-04).

GAP-1 PR-A (TDD-gap1-asana-operator-rewire-v2): the cross-tenant agency-BI export
is realized at TRUE Option-1 scope -- the DE-IDENTIFIED AGGREGATE tables only, served
via the operator plane (mint ``OperatorClaims`` -> ``POST /api/v1/insights/operator/
execute-batch``, bounded to the owned set ``O``). This file now declares ONLY the
4 CLEAN-1:1 tables (SUMMARY, OFFER TABLE, AD QUESTIONS, ASSET TABLE), each dispatched
via :data:`DispatchType.OPERATOR_INSIGHTS`.

DROPPED (M4) -- the 4 per-patient/financial PII tables are removed from the
cross-tenant view and are NOT kept on the SA fleet-read (keeping them re-asserts
DATA-VAL-003, the telos antithesis): APPOINTMENTS, LEADS, LIFETIME RECONCILIATIONS,
T14 RECONCILIATIONS.

DEFERRED (FF) -- the BY-period series (BY QUARTER / MONTH / WEEK; OQ-3 bounded-lookback
ruling) and UNUSED ASSETS (OQ-4b Category-B, data-plane-only) need an affordance over
the batch route and ship in the fast-follow (PR-FF), NOT here.

Public API:
    DispatchType (Enum) -- routing discriminator for _fetch_table dispatch.
    TableSpec (frozen dataclass) -- declarative specification for a single table.
    TABLE_SPECS (list[TableSpec]) -- ordered list of the 4 clean table specifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "DispatchType",
    "TableSpec",
    "TABLE_SPECS",
]


class DispatchType(Enum):
    """Discriminator for _fetch_table dispatch routing.

    Each value maps to a distinct fetch path. Used in a match statement inside
    _fetch_table to eliminate the if/elif chain (per D-04).
    """

    OPERATOR_INSIGHTS = "operator_insights"
    """Operator-plane de-identified aggregate read (GAP-1 PR-A).
    Served from the pre-fetched batch-over-O cache keyed by the spec's
    ``insight_name``; distributed per-office. Bounded to the owned set O via a
    minted OperatorClaims token (NEVER the SA fleet-read)."""

    INSIGHTS = "insights"
    """Standard POST /insights call via get_insights_async.
    Parameterized by factory, period, include_unused. Retained for the deferred
    BY-period / UNUSED ASSETS tables (PR-FF); NOT used by the clean subset."""

    APPOINTMENTS = "appointments"
    """GET /appointments via get_appointments_async.
    DROPPED from the cross-tenant export (M4, PII); enum retained for other
    consumers / the formatter's spec-driven loop."""

    LEADS = "leads"
    """GET /leads via get_leads_async.
    DROPPED from the cross-tenant export (M4, PII); enum retained."""

    RECONCILIATION = "reconciliation"
    """GET /reconciliation via get_reconciliation_async.
    DROPPED from the cross-tenant export (M4, financial PII); enum retained
    because the formatter references it in its pending-detection branch."""


@dataclass(frozen=True)
class TableSpec:
    """Declarative specification for a single insights table.

    Unifies fetch dispatch configuration (F-03) and display preparation rules
    (F-04) on a single frozen dataclass (per D-05).

    Fields are divided into groups:
    - Identity: table_name
    - Fetch: dispatch_type, insight_name, factory, period, days, limit,
             exclude_appointments, window_days, include_unused, activity_filter
    - Limits: default_limit
    - Display: sort_key, sort_desc, exclude_columns, display_columns, empty_message
    """

    # --- Identity ---
    table_name: str
    """Human-readable table name. Must match TABLE_ORDER names exactly."""

    # --- Fetch configuration ---
    dispatch_type: DispatchType
    """Routing discriminator for _fetch_table (per D-04)."""

    insight_name: str | None = None
    """Registered de-identified aggregate insight name. Only used when
    dispatch_type is OPERATOR_INSIGHTS (the operator-plane allowlisted name)."""

    factory: str = "base"
    """Factory parameter for get_insights_async. Only used when dispatch_type
    is INSIGHTS (the deferred BY-period / UNUSED ASSETS path)."""

    period: str | None = None
    """Period parameter. For OPERATOR_INSIGHTS / INSIGHTS: the time-period preset.
    None means omit."""

    days: int | None = None
    """Lookback window in days. Used by APPOINTMENTS and LEADS (dropped)."""

    exclude_appointments: bool = False
    """Exclude appointment leads. Used by LEADS dispatch only (dropped)."""

    window_days: int | None = None
    """Rolling window size in days for RECONCILIATION dispatch (dropped)."""

    include_unused: bool = False
    """Include zero-activity assets. Used by INSIGHTS dispatch with
    factory='assets' (deferred UNUSED ASSETS)."""

    activity_filter: bool = False
    """OQ-4a: drop zero-activity rows (keep ``spend > 0 OR leads > 0``) asana-side
    after the operator fetch. Set for ASSET TABLE + AD QUESTIONS (the operator
    batch route does not apply the factory-frame path's activity filter)."""

    # --- Limits ---
    default_limit: int | None = None
    """Default row limit for this table (applied client-side during compose_report
    display preparation). Runtime row_limits dict overrides this value."""

    # --- Display configuration ---
    sort_key: str | None = None
    """Column name to sort display rows by. None = no sort."""

    sort_desc: bool = True
    """Sort direction. True = descending. Only meaningful when sort_key is set."""

    exclude_columns: frozenset[str] | None = None
    """Columns to exclude from display rows. None = no exclusion.
    Applied after sort and limit. Copy TSV (full_rows) is NOT affected."""

    display_columns: list[str] | None = None
    """Whitelist of columns to show in display. None = show all.
    Applied after exclude_columns. Copy TSV (full_rows) is NOT affected.
    Columns not present in any row are silently omitted."""

    empty_message: str = "No data available"
    """Message shown when the table has zero rows."""


# The 4 CLEAN-1:1 de-identified aggregate tables served via the operator plane.
# (TDD-gap1 §7: SUMMARY, OFFER TABLE, AD QUESTIONS, ASSET TABLE.) OFFER TABLE +
# AD QUESTIONS additionally require PR-D1's +2 allowlist names
# (offer_level_stats / question_level_stats) on the data plane.
TABLE_SPECS: list[TableSpec] = [
    # --- SUMMARY -> account_level_stats (lifetime) ---
    TableSpec(
        table_name="SUMMARY",
        dispatch_type=DispatchType.OPERATOR_INSIGHTS,
        insight_name="account_level_stats",
        period="lifetime",
    ),
    # --- AD QUESTIONS -> question_level_stats (lifetime, activity-filtered) ---
    TableSpec(
        table_name="AD QUESTIONS",
        dispatch_type=DispatchType.OPERATOR_INSIGHTS,
        insight_name="question_level_stats",
        period="lifetime",
        activity_filter=True,
    ),
    # --- ASSET TABLE -> asset_level_stats (t30, activity-filtered, top-spend) ---
    TableSpec(
        table_name="ASSET TABLE",
        dispatch_type=DispatchType.OPERATOR_INSIGHTS,
        insight_name="asset_level_stats",
        period="t30",
        activity_filter=True,
        default_limit=150,
        sort_key="spend",
        sort_desc=True,
        exclude_columns=frozenset(
            {
                "offer_id",
                "office_phone",
                "vertical",
                "transcript",
                "is_raw",
                "is_generic",
                "platform_id",
                "disabled",
            }
        ),
    ),
    # --- OFFER TABLE -> offer_level_stats (t30) ---
    TableSpec(
        table_name="OFFER TABLE",
        dispatch_type=DispatchType.OPERATOR_INSIGHTS,
        insight_name="offer_level_stats",
        period="t30",
    ),
]
