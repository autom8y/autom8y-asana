"""HTML report formatter for insights export.

Implements the StructuredDataRenderer protocol (Option A+ from
SPIKE-FORMATTER-PROTOCOL-MOONSHOT) with an HtmlRenderer that produces
self-contained HTML documents with inline CSS.

Public API:
    compose_report(data: InsightsReportData) -> str
        Unchanged signature -- adapts InsightsReportData into DataSection
        list and delegates to HtmlRenderer.render_document().

    StructuredDataRenderer (Protocol)
        Reusable protocol for any surface that renders list[dict] data.

    DataSection (frozen dataclass)
        Universal input shape for a single data table/section.

    HtmlRenderer
        The sole StructuredDataRenderer implementation (v1).
"""

from __future__ import annotations

import html
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from autom8_asana.automation.workflows.insights_tables import (
    TABLE_SPECS,
    DispatchType,
)
from autom8_asana.clients.data._pii import mask_phone_number

# Preferred leading columns for period-based and reconciliation tables.
# Keys must match TABLE_ORDER names exactly.
COLUMN_ORDER: dict[str, list[str]] = {
    "BY QUARTER": ["period_label", "period_start", "period_end"],
    "BY MONTH": ["period_label", "period_start", "period_end"],
    "BY WEEK": ["period_label", "period_start", "period_end"],
    "LIFETIME RECONCILIATIONS": [
        "office_phone",
        "vertical",
        "num_invoices",
        "collected",
        "spend",
        "variance",
        "variance_pct",
    ],
    "T14 RECONCILIATIONS": [
        "period",
        "period_label",
        "period_start",
        "period_end",
        "period_len",
        "num_invoices",
        "collected",
        "spend",
        "variance",
        "variance_pct",
    ],
}

# Display-friendly column labels. Checked before title-casing.
_DISPLAY_LABELS: dict[str, str] = {
    "n_distinct_ads": "Distinct Ads",
    "cpl": "CPL",
    "cps": "CPS",
    "ecps": "Expected CPS",
    "cpc": "CPC",
    "ltv": "LTV",
    "ctr": "CTR",
    "lctr": "Lead CTR",
    "nsr_ncr": "NSR/NCR",
    "lp20m": "Leads/20K",
    "sp20m": "Shows/20K",
    "esp20m": "Exp. Shows/20K",
    "ltv20m": "LTV/20K",
    "roas": "ROAS",
    "ns_rate": "No-Show Rate",
    "nc_rate": "No-Close Rate",
    "variance_pct": "Variance %",
    "imp": "Impressions",
    "booking_rate": "Booking Rate",
    "conv_rate": "Conv. Rate",
    "sched_rate": "Sched. Rate",
    "pacing_ratio": "Pacing Ratio",
    "conversion_rate": "Conversion Rate",
    "period_label": "Period",
    "period_start": "Start",
    "period_end": "End",
    "period_len": "Days",
}

# Tooltip definitions for column headers.
_COLUMN_TOOLTIPS: dict[str, str] = {
    "cpl": "Cost Per Lead: Total spend \u00f7 total leads",
    "cps": "Cost Per Show: Total spend \u00f7 scheduled appointments",
    "booking_rate": "Booking Rate: Scheduled appointments \u00f7 total leads",
    "roas": "Return on Ad Spend: Revenue \u00f7 ad spend",
    "ctr": "Click-Through Rate: Clicks \u00f7 impressions",
    "ltv": "Lifetime Value: Estimated revenue per customer",
    "conv_rate": "Conversion Rate: Conversions \u00f7 total leads",
    "ns_rate": "No-Show Rate: No-shows \u00f7 scheduled appointments",
    "nc_rate": "No-Close Rate: No-closes \u00f7 shown appointments",
    "variance_pct": "Variance %: (Collected - Spend) \u00f7 Spend \u00d7 100",
}

# Section subtitles displayed below section headers.
_SECTION_SUBTITLES: dict[str, str] = {
    "SUMMARY": "Lifetime performance metrics across all campaigns for this business.",
    "APPOINTMENTS": "Scheduled appointments from the last 90 days.",
    "LEADS": "Incoming leads from the last 30 days, excluding those with appointments.",
    "LIFETIME RECONCILIATIONS": "Financial reconciliation across all time periods.",
    "T14 RECONCILIATIONS": "Rolling 14-day financial reconciliation windows.",
    "BY QUARTER": "Quarterly performance trends with key efficiency metrics.",
    "BY MONTH": "Monthly performance trends with key efficiency metrics.",
    "BY WEEK": "Weekly performance trends with key efficiency metrics.",
    "AD QUESTIONS": "Lead-qualifying questions and their conversion impact.",
    "ASSET TABLE": "Creative performance by individual ad asset over the last 30 days.",
    "OFFER TABLE": "Offer-level performance metrics over the last 30 days.",
    "UNUSED ASSETS": "Ad assets with zero activity (spend and leads) plus inventory-only assets, over the last 30 days.",
}


# Sections expanded by default (rest start collapsed).
_DEFAULT_EXPANDED_SECTIONS: frozenset[str] = frozenset(
    {
        "SUMMARY",
        "BY WEEK",
    }
)

# PII columns requiring phone masking in table cells.
_PII_PHONE_COLUMNS: frozenset[str] = frozenset(
    {"office_phone", "phone", "patient_phone", "contact_phone"}
)

# Conditional formatting thresholds for rate columns.
# booking_rate is ratio 0-1; conv_rate is percentage 0-100.
_CONDITIONAL_FORMAT_THRESHOLDS: dict[str, tuple[float, float]] = {
    "booking_rate": (0.40, 0.20),
    "conv_rate": (40.0, 20.0),
}


# ---------------------------------------------------------------------------
# Domain data classes (unchanged public API)
# ---------------------------------------------------------------------------


@dataclass
class TableResult:
    """Result of fetching a single table.

    Attributes:
        table_name: Human-readable table name (e.g., "SUMMARY").
        success: Whether the fetch succeeded.
        data: List of row dicts from the API response (None if failed).
        row_count: Number of rows returned.
        error_type: Error classification string (if failed).
        error_message: Human-readable error description (if failed).
    """

    table_name: str
    success: bool
    data: list[dict[str, Any]] | None = None
    row_count: int = 0
    error_type: str | None = None
    error_message: str | None = None


@dataclass
class InsightsReportData:
    """Input data for composing a full report."""

    business_name: str
    office_phone: str
    vertical: str
    table_results: dict[str, TableResult]
    started_at: float  # time.monotonic() value
    version: str
    row_limits: dict[str, int] = field(default_factory=dict)
    offer_gid: str | None = None


# ---------------------------------------------------------------------------
# StructuredDataRenderer protocol + DataSection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DataSection:
    """A named section containing tabular data or a status message."""

    name: str
    rows: list[dict[str, Any]] | None
    row_count: int = 0
    truncated: bool = False
    total_rows: int | None = None
    error: str | None = None
    empty_message: str | None = None
    full_rows: list[dict[str, Any]] | None = None


class StructuredDataRenderer(Protocol):
    """Renders tabular data sections into a formatted document.

    Protocol class (~15 lines) for any surface that needs to present
    list[dict[str, Any]] data as a human-readable document.
    """

    @property
    def content_type(self) -> str:
        """MIME type of the rendered output (e.g., 'text/html')."""
        ...

    @property
    def file_extension(self) -> str:
        """File extension without dot (e.g., 'html')."""
        ...

    def render_document(
        self,
        *,
        title: str,
        metadata: dict[str, str],
        sections: list[DataSection],
        footer: dict[str, str] | None = None,
    ) -> str:
        """Render a complete document with header, data sections, and footer."""
        ...


# ---------------------------------------------------------------------------
# HtmlRenderer -- sole StructuredDataRenderer implementation (v1)
# ---------------------------------------------------------------------------


class HtmlRenderer:
    """Renders DataSection list into a self-contained HTML document.

    All CSS is inlined. No external resources. Zero dependencies beyond
    the Python standard library.
    """

    @property
    def content_type(self) -> str:
        return "text/html"

    @property
    def file_extension(self) -> str:
        return "html"

    def render_document(
        self,
        *,
        title: str,
        metadata: dict[str, str],
        sections: list[DataSection],
        footer: dict[str, str] | None = None,
    ) -> str:
        """Render a complete self-contained HTML document.

        Args:
            title: Document title (displayed in header and <title>).
            metadata: Key-value pairs for the header info block.
            sections: Ordered list of DataSection objects.
            footer: Key-value pairs for the footer block. None omits footer.

        Returns:
            Complete HTML string.
        """
        parts: list[str] = []
        parts.append(self._render_doctype_and_head(title))
        parts.append("<body>")
        parts.append('<div class="toast" id="toast">Copied</div>')
        parts.append('<div class="layout">')
        parts.append(self._render_sidebar(sections))
        parts.append('<main class="main-content">')
        parts.append(self._render_header(title, metadata))
        parts.append(self._render_kpi_cards(sections))

        for section in sections:
            if section.error is not None:
                parts.append(self._render_error_section(section))
            elif (
                section.rows is None
                or (not section.rows and section.empty_message)
                or not section.rows
            ):
                parts.append(self._render_empty_section(section))
            else:
                parts.append(self._render_table_section(section))

        if footer is not None:
            parts.append(self._render_footer(footer))

        parts.append("</main>")
        parts.append("</div>")  # close layout
        parts.append("</body>")
        parts.append("</html>")
        return "\n".join(parts) + "\n"

    # --- Private rendering methods ---

    def _render_doctype_and_head(self, title: str) -> str:
        escaped_title = html.escape(title)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en" data-theme="light">\n'
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>{escaped_title}</title>\n"
            f"<style>\n{_CSS}\n</style>\n"
            f"<script>\n{_JS}\n</script>\n"
            "</head>"
        )

    def _render_sidebar(self, sections: list[DataSection]) -> str:
        parts: list[str] = ['<nav class="sidebar">']
        parts.append('<div class="nav-section-label">Sections</div>')
        for section in sections:
            sid = _slugify(section.name)
            row_count = section.row_count if section.rows else 0
            parts.append(
                f'<a href="#{sid}" class="nav-link">'
                f"{html.escape(section.name)}"
                f'<span class="badge">{row_count}</span></a>'
            )
        parts.append("</nav>")
        return "\n".join(parts)

    def _render_header(self, title: str, metadata: dict[str, str]) -> str:
        # Extract business name from title by splitting on ": "
        business_name = title.split(": ", 1)[1] if ": " in title else title
        escaped_business = html.escape(business_name)

        # Build metadata items
        meta_parts: list[str] = []
        for k, v in metadata.items():
            if k == "Offer":
                asana_url = f"https://app.asana.com/0/0/{html.escape(v)}"
                meta_parts.append(
                    f"<strong>{html.escape(k)}:</strong> "
                    f'<a href="{asana_url}">View in Asana</a>'
                )
            else:
                meta_parts.append(
                    f"<strong>{html.escape(k)}:</strong> {html.escape(v)}"
                )
        meta_html = " &nbsp;&bull;&nbsp; ".join(meta_parts)

        parts = [
            '<header class="report-header">',
            f'<h1 class="report-title">{escaped_business}</h1>',
            f'<div class="report-meta">{meta_html}</div>',
            '<div class="header-actions">',
            '<div class="search-wrap">',
            '<input type="text" id="global-search" placeholder="Search rows..." '
            'oninput="onSearch(this.value)">',
            '<span class="search-clear" id="search-clear" onclick="clearSearch()">&times;</span>',
            "</div>",
            '<span class="search-count" id="search-count"></span>',
            '<button class="btn" onclick="window.print()">Print</button>',
            '<button class="btn" id="theme-btn" onclick="toggleTheme()">Dark Mode</button>',
            '<button class="btn" onclick="expandAll()">Expand All</button>',
            '<button class="btn" onclick="collapseAll()">Collapse All</button>',
            "</div>",
            "</header>",
        ]
        return "\n".join(parts)

    @staticmethod
    def _extract_numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
        """Return float values for *key* from *rows*, skipping None and non-numeric."""
        return [
            float(r[key])
            for r in rows
            if r.get(key) is not None and isinstance(r.get(key), (int, float))
        ]

    def _render_kpi_cards(self, sections: list[DataSection]) -> str:
        summary_section: DataSection | None = None
        by_week_section: DataSection | None = None

        for s in sections:
            if s.name == "SUMMARY" and s.rows:
                summary_section = s
            elif s.name == "BY WEEK" and s.rows:
                by_week_section = s

        if summary_section is None and by_week_section is None:
            return ""

        cards: list[str] = []

        # Extract SUMMARY row
        summary_row: dict[str, Any] = {}
        if summary_section and summary_section.rows:
            summary_row = summary_section.rows[0]

        # Extract BY WEEK rows
        week_rows: list[dict[str, Any]] = []
        if by_week_section and by_week_section.rows:
            week_rows = by_week_section.rows

        # Card 1: CPL
        cpl_val = summary_row.get("cpl")
        if cpl_val is not None and isinstance(cpl_val, (int, float)):
            cards.append(self._kpi_card("CPL", f"${cpl_val:,.2f}", "Cost per lead"))
        else:
            cards.append(self._kpi_card("CPL", "n/a", "Awaiting data"))

        # Card 2: Booking Rate (with sparkline)
        br_val = summary_row.get("booking_rate")
        sparkline_svg = ""
        if week_rows:
            br_values = self._extract_numeric_values(week_rows, "booking_rate")
            if br_values:
                sparkline_svg = self._render_sparkline(br_values)

        if br_val is not None and isinstance(br_val, (int, float)):
            cards.append(
                self._kpi_card(
                    "Booking Rate",
                    f"{br_val * 100:.2f}%",
                    "Leads &rarr; scheduled",
                    sparkline=sparkline_svg,
                )
            )
        else:
            cards.append(self._kpi_card("Booking Rate", "n/a", "Awaiting data"))

        # Card 3: CPS
        cps_val = summary_row.get("cps")
        if cps_val is not None and isinstance(cps_val, (int, float)):
            cards.append(self._kpi_card("CPS", f"${cps_val:,.2f}", "Cost per show"))
        else:
            cards.append(self._kpi_card("CPS", "n/a", "Awaiting data"))

        # Card 4: ROAS
        roas_val = summary_row.get("roas")
        if roas_val is not None and isinstance(roas_val, (int, float)):
            cards.append(
                self._kpi_card("ROAS", f"{roas_val:.2f}x", "Return on ad spend")
            )
        else:
            cards.append(self._kpi_card("ROAS", "n/a", "Awaiting data"))

        # Card 5: Best Week
        if week_rows:
            br_pairs: list[tuple[float, str]] = [
                (float(r["booking_rate"]), str(r.get("period_label", "")))
                for r in week_rows
                if r.get("booking_rate") is not None
                and isinstance(r.get("booking_rate"), (int, float))
            ]
            if br_pairs:
                best_val, best_label = max(br_pairs, key=lambda p: p[0])
                cards.append(
                    self._kpi_card(
                        "Best Week",
                        f"{best_val * 100:.2f}%",
                        html.escape(str(best_label)),
                    )
                )
            else:
                cards.append(self._kpi_card("Best Week", "n/a", "Awaiting data"))
        else:
            cards.append(self._kpi_card("Best Week", "n/a", "Awaiting data"))

        # Card 6: Spend Trend
        if week_rows:
            spend_values = self._extract_numeric_values(week_rows, "spend")
            if len(spend_values) >= 2:
                recent = spend_values[-12:] if len(spend_values) > 12 else spend_values
                prior_start = max(0, len(spend_values) - 24)
                prior_end = max(0, len(spend_values) - 12)
                prior = (
                    spend_values[prior_start:prior_end]
                    if prior_end > prior_start
                    else []
                )
                recent_sum = sum(recent)
                prior_sum = sum(prior) if prior else 0

                if prior_sum > 0:
                    pct_change = (recent_sum - prior_sum) / prior_sum
                    if pct_change > 0.05:
                        arrow = "&uarr;"
                        css_class = "trend-up"
                    elif pct_change < -0.05:
                        arrow = "&darr;"
                        css_class = "trend-down"
                    else:
                        arrow = "&rarr;"
                        css_class = ""
                    cards.append(
                        self._kpi_card(
                            "Spend Trend",
                            f'<span class="{css_class}">{arrow}</span>',
                            "vs prior 12 weeks",
                        )
                    )
                else:
                    cards.append(self._kpi_card("Spend Trend", "n/a", "Awaiting data"))
            else:
                cards.append(self._kpi_card("Spend Trend", "n/a", "Awaiting data"))
        else:
            cards.append(self._kpi_card("Spend Trend", "n/a", "Awaiting data"))

        return '<div class="kpi-grid">\n' + "\n".join(cards) + "\n</div>"

    def _kpi_card(
        self,
        label: str,
        value: str,
        subtitle: str,
        sparkline: str = "",
    ) -> str:
        parts = [
            '<div class="kpi-card">',
            f'<div class="kpi-label">{html.escape(label)}</div>',
            f'<div class="kpi-value">{value}</div>',
            f'<div class="kpi-sub">{subtitle}</div>',
        ]
        if sparkline:
            parts.append(f'<div class="kpi-sparkline">{sparkline}</div>')
        parts.append("</div>")
        return "\n".join(parts)

    def _render_sparkline(self, values: list[float]) -> str:
        if not values:
            return ""
        width = 140
        height = 36
        padding = 2
        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val if max_val != min_val else 1.0

        points: list[str] = []
        n = len(values)
        for i, v in enumerate(values):
            x = padding + (i / max(n - 1, 1)) * (width - 2 * padding)
            y = height - padding - ((v - min_val) / val_range) * (height - 2 * padding)
            points.append(f"{x:.1f},{y:.1f}")

        polyline_points = " ".join(points)
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<polyline points="{polyline_points}" fill="none" '
            f'stroke="var(--accent)" stroke-width="1.5" />'
            f"</svg>"
        )

    def _render_table_section(self, section: DataSection) -> str:
        rows = section.rows or []
        columns = _discover_columns(rows)
        columns = _reorder_columns(columns, COLUMN_ORDER.get(section.name))

        if not columns:
            return self._render_empty_section(section)

        # Pre-compute alignment class per column (O(columns) instead of O(rows*columns))
        align_by_col = {col: _column_align_class(rows, col) for col in columns}

        sid = _slugify(section.name)
        is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
        collapsed_class = "" if is_expanded else " collapsed"

        # Build header cells with sort, tooltips, and alignment
        header_cells: list[str] = []
        for col_idx, col in enumerate(columns):
            align_cls = align_by_col[col]
            tooltip = _COLUMN_TOOLTIPS.get(col)
            title_attr = f' title="{html.escape(tooltip)}"' if tooltip else ""
            display_label = html.escape(_to_title_case(col))
            cls = align_cls
            header_cells.append(
                f"<th onclick=\"sortTable('{sid}',{col_idx})\""
                f"{title_attr}"
                f' class="{cls}">'
                f"{display_label}"
                f'<span class="sort-icon"></span></th>'
            )

        # Build body rows with alignment + conditional formatting
        body_rows: list[str] = []
        for row in rows:
            cells: list[str] = []
            for col in columns:
                value = row.get(col)
                align_cls = align_by_col[col]
                cond_cls = _conditional_format_class(value, col)
                # Date columns
                date_cls = ""
                if "period_start" in col or "period_end" in col:
                    date_cls = " date-cell"
                td_class = f"{align_cls} {cond_cls}{date_cls}".strip()
                cell_html = _format_cell_html(value, col)
                cells.append(f'<td class="{td_class}">{cell_html}</td>')
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        # Subtitle
        subtitle = _SECTION_SUBTITLES.get(section.name, "")
        subtitle_html = (
            f'<div class="section-subtitle">{html.escape(subtitle)}</div>'
            if subtitle
            else ""
        )

        # Embedded JSON for Copy TSV (with PII masking)
        json_rows = (
            section.full_rows if section.full_rows is not None else (section.rows or [])
        )
        json_data = json.dumps(_mask_pii_rows(json_rows), default=str)

        parts = [
            f'<section id="{sid}" class="table-section">',
            f'<div class="section-header" onclick="toggleSection(\'{sid}\')">',
            f"<h2>{html.escape(section.name)} "
            f'<span class="badge">{section.row_count}</span></h2>',
            '<div class="section-controls">',
            f'<button class="copy-btn" onclick="event.stopPropagation();copyTable(\'{sid}\')">Copy TSV</button>',
            f'<span class="toggle-icon{collapsed_class}" id="toggle-{sid}">\u25bc</span>',
            "</div>",
            "</div>",
            f'<div class="section-body{collapsed_class}" id="body-{sid}">',
            subtitle_html,
            '<div class="table-scroll">',
            f'<table class="data-table" id="tbl-{sid}">',
            f"<thead><tr>{''.join(header_cells)}</tr></thead>",
            "<tbody>",
            "\n".join(body_rows),
            "</tbody>",
            "</table>",
            "</div>",
        ]

        if section.truncated and section.total_rows is not None:
            parts.append(
                f'<p class="truncation-note">Showing {section.row_count} '
                f"of {section.total_rows} rows</p>"
            )

        # Embedded JSON data script
        parts.append(
            f'<script type="application/json" id="data-{sid}">{json_data}</script>'
        )
        parts.append("</div>")
        parts.append("</section>")
        return "\n".join(parts)

    def _render_section_with_body(self, section: DataSection, body_content: str) -> str:
        """Render a section scaffold with the given body_content string."""
        sid = _slugify(section.name)
        is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
        collapsed_class = "" if is_expanded else " collapsed"
        subtitle = _SECTION_SUBTITLES.get(section.name, "")
        subtitle_html = (
            f'<div class="section-subtitle">{html.escape(subtitle)}</div>'
            if subtitle
            else ""
        )
        return (
            f'<section id="{sid}" class="table-section">\n'
            f'<div class="section-header" onclick="toggleSection(\'{sid}\')">\n'
            f"<h2>{html.escape(section.name)}</h2>\n"
            f'<div class="section-controls">'
            f'<span class="toggle-icon{collapsed_class}" id="toggle-{sid}">\u25bc</span>'
            f"</div>\n"
            "</div>\n"
            f'<div class="section-body{collapsed_class}" id="body-{sid}">\n'
            f"{subtitle_html}\n"
            f"{body_content}\n"
            "</div>\n"
            "</section>"
        )

    def _render_empty_section(self, section: DataSection) -> str:
        message = section.empty_message or "No data available"
        body = f'<p class="empty">{html.escape(message)}</p>'
        return self._render_section_with_body(section, body)

    def _render_error_section(self, section: DataSection) -> str:
        error_text = section.error or "Unknown error"
        body = f'<div class="error-box">{html.escape(error_text)}</div>'
        return self._render_section_with_body(section, body)

    def _render_footer(self, footer: dict[str, str]) -> str:
        items = " &nbsp;&bull;&nbsp; ".join(
            f'<span class="footer-item"><strong>{html.escape(k)}:</strong> {html.escape(v)}</span>'
            for k, v in footer.items()
        )
        return f'<footer class="report-footer">\n{items}\n</footer>'


# ---------------------------------------------------------------------------
# compose_report -- public API (unchanged signature)
# ---------------------------------------------------------------------------

_renderer = HtmlRenderer()


def compose_report(data: InsightsReportData) -> str:
    """Compose a full HTML report from table results.

    Per FR-06: Iterates TABLE_SPECS and applies spec-driven transforms.
    No table-name branching in the main loop body (per D-07).
    """
    masked = mask_phone_number(data.office_phone)
    timestamp = datetime.now(UTC).isoformat()
    metadata: dict[str, str] = {
        "Phone": masked,
        "Vertical": data.vertical,
        "Generated": timestamp,
        "Period": "Daily insights report",
    }
    if data.offer_gid:
        metadata["Offer"] = data.offer_gid

    sections: list[DataSection] = []

    for spec in TABLE_SPECS:
        result = data.table_results.get(spec.table_name)

        # --- Step 1: Validate result (missing / error / empty) ---
        if result is None:
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=None,
                    error="[ERROR] missing: Table result not available",
                )
            )
            continue

        if not result.success:
            error_type = result.error_type or "unknown"
            error_msg = result.error_message or "Unknown error"
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=None,
                    error=f"[ERROR] {error_type}: {error_msg}",
                )
            )
            continue

        if not result.data:
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=[],
                    empty_message=spec.empty_message,
                )
            )
            continue

        # --- Step 2: Reconciliation pending detection (per FR-11) ---
        if (
            spec.dispatch_type == DispatchType.RECONCILIATION
            and _is_payment_data_pending(result.data)
        ):
            sections.append(
                DataSection(
                    name=spec.table_name,
                    rows=[],
                    empty_message=_RECONCILIATION_PENDING_MESSAGE,
                )
            )
            continue

        # --- Step 3: Start with full data; display_rows diverges ---
        all_rows = result.data
        display_rows = list(all_rows)

        # --- Step 4: Sort (spec.sort_key) ---
        if spec.sort_key is not None:
            _sort_key: str = spec.sort_key
            display_rows = sorted(
                display_rows,
                key=lambda r: r.get(_sort_key) or 0,
                reverse=spec.sort_desc,
            )

        # --- Step 5: Row limit (runtime override > spec default) ---
        row_limit = data.row_limits.get(spec.table_name) or spec.default_limit
        total_rows = len(display_rows)
        if row_limit:
            display_rows = display_rows[:row_limit]
        truncated = row_limit is not None and total_rows > row_limit

        # --- Step 6: Exclude columns (spec.exclude_columns) ---
        if spec.exclude_columns is not None:
            display_rows = [
                {k: v for k, v in row.items() if k not in spec.exclude_columns}
                for row in display_rows
            ]

        # --- Step 7: Display columns whitelist (spec.display_columns) ---
        if spec.display_columns is not None:
            available = [
                c for c in spec.display_columns if any(c in r for r in display_rows)
            ]
            display_rows = [
                {k: v for k, v in row.items() if k in available} for row in display_rows
            ]

        # --- Step 8: Emit DataSection ---
        sections.append(
            DataSection(
                name=spec.table_name,
                rows=display_rows,
                row_count=len(display_rows),
                truncated=truncated,
                total_rows=total_rows if truncated else None,
                full_rows=all_rows,
            )
        )

    # Build footer (unchanged)
    elapsed = time.monotonic() - data.started_at
    tables_succeeded = sum(1 for r in data.table_results.values() if r.success)
    tables_failed = len(TABLE_SPECS) - tables_succeeded
    total_tables = tables_succeeded + tables_failed

    footer: dict[str, str] = {
        "Duration": f"{elapsed:.2f}s",
        "Tables": f"{tables_succeeded}/{total_tables}",
    }
    if tables_failed > 0:
        footer["Errors"] = str(tables_failed)
    footer["Version"] = data.version

    title = f"Insights Export: {data.business_name}"

    return _renderer.render_document(
        title=title,
        metadata=metadata,
        sections=sections,
        footer=footer,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Payment indicator columns for reconciliation tables.
# When ALL of these are null across all rows, payment data is pending.
_PAYMENT_INDICATOR_COLUMNS = frozenset(
    {
        "collected",
        "num_invoices",
        "variance",
        "expected_collection",
        "expected_variance",
    }
)

_RECONCILIATION_PENDING_MESSAGE = (
    "Payment reconciliation data is pending Stripe integration. "
    "Spend and budget data is available below."
)


def _is_payment_data_pending(rows: list[dict[str, Any]]) -> bool:
    """Check if all payment indicator columns are null across all rows.

    Returns True when every value for every payment indicator column
    is None (or the column is absent) in every row. This signals that
    Stripe REC-8 has not shipped and payment data is unavailable.
    """
    if not rows:
        return False
    for row in rows:
        for col in _PAYMENT_INDICATOR_COLUMNS:
            if row.get(col) is not None:
                return False
    return True


def _to_title_case(column_name: str) -> str:
    """Convert snake_case column name to display label.

    Checks _DISPLAY_LABELS first for known abbreviations/acronyms,
    then falls back to title-casing.
    """
    label = _DISPLAY_LABELS.get(column_name)
    if label:
        return label
    return column_name.replace("_", " ").title()


# ---------------------------------------------------------------------------
# Field format categories for type-aware cell rendering.
# Maps column names to display format: currency ($12,847.50), rate (3.42%),
# percentage (42.50%), ratio (3.50x), per20k (12.50).
# Fields not listed fall through to comma-grouped int/float defaults.
# Source of truth: autom8y-data InsightsService._PRECISION_RULES + EntityMetrics.
# ---------------------------------------------------------------------------
_FIELD_FORMAT: dict[str, str] = {
    # CURRENCY — $12,847.50
    "spend": "currency",
    "cpl": "currency",
    "cps": "currency",
    "ecps": "currency",
    "cpc": "currency",
    "ltv": "currency",
    "avg_conv": "currency",
    "collected": "currency",
    "variance": "currency",
    "expected_collection": "currency",
    "expected_variance": "currency",
    "offer_cost": "currency",
    "budget": "currency",
    "expected_spend": "currency",
    "projected_spend": "currency",
    "budget_variance": "currency",
    # RATE — stored as decimal ratio 0-1, display as ×100 percent (0.0342 → 3.42%)
    # Aligned with upstream _PRECISION_RULES RATE category (2026-02-22).
    "booking_rate": "rate",
    "sched_rate": "rate",
    # PERCENTAGE — already in percent units (18.36 → 18.36%), do NOT multiply
    # Upstream PercentageFormula outputs 0-100 directly for these fields.
    "ctr": "percentage",
    "lctr": "percentage",
    "conversion_rate": "percentage",
    "ns_rate": "percentage",
    "nc_rate": "percentage",
    "conv_rate": "percentage",
    "nsr_ncr": "percentage",
    "variance_pct": "percentage",
    # RATIO — multiplier notation (3.5 → 3.50x), unbounded
    "roas": "ratio",
    "pacing_ratio": "ratio",
    # PER_20K — comma-grouped decimal, no symbol
    "lp20m": "per20k",
    "sp20m": "per20k",
    "esp20m": "per20k",
    "ltv20m": "per20k",
}


def _format_cell_html(value: Any, column: str = "") -> str:
    """Format a single cell value for HTML table display.

    Applies type-aware formatting based on column name:
    - Currency fields: $12,847.50
    - Rate fields (stored as decimal): 3.42%
    - Percentage fields (already in %): 42.50%
    - Ratio fields: 3.50x
    - Per-20k fields: 12.50
    - Other integers: comma-grouped (45,000)
    - Other floats: comma-grouped 2dp (123.46)

    None values render as a styled dash indicator.
    All output is HTML-escaped to prevent XSS.

    Args:
        value: Cell value (may be None).
        column: Column name for format lookup (default "" for backward compat).

    Returns:
        HTML-safe string for table cell content.
    """
    if value is None:
        return '<span class="dash">\u2014</span>'

    # PII: mask phone columns before any other formatting
    if column in _PII_PHONE_COLUMNS and isinstance(value, str):
        return html.escape(mask_phone_number(value))

    fmt = _FIELD_FORMAT.get(column, "")

    if isinstance(value, (int, float)):
        if fmt == "currency":
            return html.escape(f"${value:,.2f}")
        if fmt == "rate":
            return html.escape(f"{value * 100:.2f}%")
        if fmt == "percentage":
            return html.escape(f"{value:.2f}%")
        if fmt == "ratio":
            return html.escape(f"{value:.2f}x")
        if fmt == "per20k":
            return html.escape(f"{value:,.2f}")
        # Fallback: comma-grouped int or 2dp float
        if isinstance(value, int):
            return html.escape(f"{value:,}")
        return html.escape(f"{value:,.2f}")

    return html.escape(str(value))


def _mask_pii_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a shallow copy of *rows* with PII phone columns masked."""
    if not rows:
        return rows
    # Fast path: check if any PII columns are present in the first row
    pii_cols = _PII_PHONE_COLUMNS & rows[0].keys()
    if not pii_cols:
        return rows
    masked: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        for col in pii_cols:
            val = r.get(col)
            if isinstance(val, str):
                r[col] = mask_phone_number(val)
        masked.append(r)
    return masked


def _discover_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Discover all column names from rows, preserving first-seen order.

    Handles heterogeneous rows where different rows may have different
    key sets. Returns the union of all keys.
    """
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                columns.append(key)
                seen.add(key)
    return columns


def _reorder_columns(
    columns: list[str],
    preferred_leading: list[str] | None = None,
) -> list[str]:
    """Reorder *columns* so that *preferred_leading* entries come first.

    Preferred columns that do not appear in *columns* are silently
    skipped.  The relative order of remaining columns is preserved.

    Args:
        columns: Column names in their current order.
        preferred_leading: Columns to move to the front (if present).

    Returns:
        New list with leading columns first, then the rest.
    """
    if not preferred_leading:
        return columns
    leading = [c for c in preferred_leading if c in columns]
    remaining = [c for c in columns if c not in preferred_leading]
    return leading + remaining


def _slugify(name: str) -> str:
    """Convert a section name to a URL-safe ID slug.

    E.g., "BY QUARTER" -> "by-quarter", "ASSET TABLE" -> "asset-table"
    """
    return name.lower().replace(" ", "-")


def _column_align_class(rows: list[dict[str, Any]], column: str) -> str:
    """Determine CSS alignment class for a column based on value types.

    Numeric columns (int/float) get right alignment; text columns get left.
    Checks the first non-None value in the column to determine type.
    """
    for row in rows:
        val = row.get(column)
        if val is not None:
            if isinstance(val, (int, float)):
                return "num"
            return ""
    return ""


def _conditional_format_class(value: Any, column: str) -> str:
    """Return CSS class for conditional formatting based on threshold rules.

    Returns 'br-green', 'br-yellow', 'br-red', or '' (no formatting).
    """
    thresholds = _CONDITIONAL_FORMAT_THRESHOLDS.get(column)
    if thresholds is None or not isinstance(value, (int, float)):
        return ""
    green_threshold, yellow_threshold = thresholds
    if value >= green_threshold:
        return "br-green"
    if value >= yellow_threshold:
        return "br-yellow"
    return "br-red"


# ---------------------------------------------------------------------------
# Static assets -- loaded once at import time, inlined into generated HTML
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / "static"
_CSS = (_STATIC_DIR / "insights_report.css").read_text(encoding="utf-8").rstrip("\n")
_JS = (_STATIC_DIR / "insights_report.js").read_text(encoding="utf-8").rstrip("\n")
