"""Declarative table specifications for insights export.

Per TDD-SPRINT-C Section 1: A new module that centralizes the 12-table
configuration for both fetch dispatch (F-03) and display preparation (F-04).

Public API:
    DispatchType (Enum) -- routing discriminator for _fetch_table dispatch.
    TableSpec (frozen dataclass) -- declarative specification for a single table.
    TABLE_SPECS (list[TableSpec]) -- ordered list of all 12 table specifications.
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

    Each value maps to a distinct DataServiceClient method call.
    Used in a match statement inside _fetch_table to eliminate
    the if/elif chain (per D-04).
    """

    INSIGHTS = "insights"
    """Standard POST /insights call via get_insights_async.
    Parameterized by factory, period, include_unused."""

    APPOINTMENTS = "appointments"
    """GET /appointments via get_appointments_async.
    Parameterized by days, limit."""

    LEADS = "leads"
    """GET /leads via get_leads_async.
    Parameterized by days, limit, exclude_appointments."""

    RECONCILIATION = "reconciliation"
    """GET /reconciliation via get_reconciliation_async.
    Parameterized by period, window_days. Phone filtering
    stays in the dispatcher (per D-02)."""


@dataclass(frozen=True)
class TableSpec:
    """Declarative specification for a single insights table.

    Unifies fetch dispatch configuration (F-03) and display
    preparation rules (F-04) on a single frozen dataclass (per D-05).
    The D-08 stakeholder override explicitly couples fetch and display
    on one type.

    Fields are divided into four groups:
    - Identity: table_name
    - Fetch: dispatch_type, factory, period, days, limit, exclude_appointments,
             window_days, include_unused
    - Limits: default_limit
    - Display: sort_key, sort_desc, exclude_columns, display_columns, empty_message
    """

    # --- Identity ---
    table_name: str
    """Human-readable table name. Must match TABLE_ORDER names exactly."""

    # --- Fetch configuration ---
    dispatch_type: DispatchType
    """Routing discriminator for _fetch_table (per D-04)."""

    factory: str = "base"
    """Factory parameter for get_insights_async. Only used when
    dispatch_type is INSIGHTS."""

    period: str | None = None
    """Period parameter. For INSIGHTS: passed to get_insights_async.
    For RECONCILIATION: passed to get_reconciliation_async.
    None means omit (APPOINTMENTS, LEADS do not use period)."""

    days: int | None = None
    """Lookback window in days. Used by APPOINTMENTS and LEADS."""

    exclude_appointments: bool = False
    """Exclude appointment leads. Used by LEADS dispatch only."""

    window_days: int | None = None
    """Rolling window size in days for RECONCILIATION dispatch."""

    include_unused: bool = False
    """Include zero-activity assets. Used by INSIGHTS dispatch with
    factory='assets'."""

    # --- Limits ---
    default_limit: int | None = None
    """Default row limit for this table.
    - APPOINTMENTS/LEADS: applied server-side via the limit parameter (per D-03).
    - All others: applied client-side during compose_report display preparation.
    - Runtime row_limits dict overrides this value when provided."""

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


TABLE_SPECS: list[TableSpec] = [
    # --- 1. SUMMARY ---
    TableSpec(
        table_name="SUMMARY",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="lifetime",
    ),
    # --- 2. APPOINTMENTS ---
    TableSpec(
        table_name="APPOINTMENTS",
        dispatch_type=DispatchType.APPOINTMENTS,
        days=90,
        default_limit=100,
    ),
    # --- 3. LEADS ---
    TableSpec(
        table_name="LEADS",
        dispatch_type=DispatchType.LEADS,
        days=30,
        exclude_appointments=True,
        default_limit=100,
    ),
    # --- 4. LIFETIME RECONCILIATIONS ---
    TableSpec(
        table_name="LIFETIME RECONCILIATIONS",
        dispatch_type=DispatchType.RECONCILIATION,
    ),
    # --- 5. T14 RECONCILIATIONS ---
    TableSpec(
        table_name="T14 RECONCILIATIONS",
        dispatch_type=DispatchType.RECONCILIATION,
        window_days=14,
    ),
    # --- 6. BY QUARTER ---
    TableSpec(
        table_name="BY QUARTER",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="quarter",
        display_columns=[
            "period_label",
            "period_start",
            "period_end",
            "spend",
            "leads",
            "cpl",
            "scheds",
            "booking_rate",
            "cps",
            "conv_rate",
            "ctr",
            "ltv",
        ],
    ),
    # --- 7. BY MONTH ---
    TableSpec(
        table_name="BY MONTH",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="month",
        display_columns=[
            "period_label",
            "period_start",
            "period_end",
            "spend",
            "leads",
            "cpl",
            "scheds",
            "booking_rate",
            "cps",
            "conv_rate",
            "ctr",
            "ltv",
        ],
    ),
    # --- 8. BY WEEK ---
    TableSpec(
        table_name="BY WEEK",
        dispatch_type=DispatchType.INSIGHTS,
        factory="base",
        period="week",
        display_columns=[
            "period_label",
            "period_start",
            "period_end",
            "spend",
            "leads",
            "cpl",
            "scheds",
            "booking_rate",
            "cps",
            "conv_rate",
            "ctr",
            "ltv",
        ],
    ),
    # --- 9. AD QUESTIONS ---
    TableSpec(
        table_name="AD QUESTIONS",
        dispatch_type=DispatchType.INSIGHTS,
        factory="ad_questions",
        period="lifetime",
    ),
    # --- 10. ASSET TABLE ---
    TableSpec(
        table_name="ASSET TABLE",
        dispatch_type=DispatchType.INSIGHTS,
        factory="assets",
        period="t30",
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
    # --- 11. OFFER TABLE ---
    TableSpec(
        table_name="OFFER TABLE",
        dispatch_type=DispatchType.INSIGHTS,
        factory="business_offers",
        period="t30",
    ),
    # --- 12. UNUSED ASSETS ---
    TableSpec(
        table_name="UNUSED ASSETS",
        dispatch_type=DispatchType.INSIGHTS,
        factory="assets",
        period="t30",
        include_unused=True,
        empty_message="No unused assets found",
    ),
]
