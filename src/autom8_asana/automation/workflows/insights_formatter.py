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
from typing import Any, Protocol

from autom8_asana.clients.data.client import mask_phone_number

# Section order (per PRD FR-W01.6, extended per TDD-WS5)
TABLE_ORDER: list[str] = [
    "SUMMARY",
    "APPOINTMENTS",
    "LEADS",
    "LIFETIME RECONCILIATIONS",
    "T14 RECONCILIATIONS",
    "BY QUARTER",
    "BY MONTH",
    "BY WEEK",
    "AD QUESTIONS",
    "ASSET TABLE",
    "OFFER TABLE",
    "UNUSED ASSETS",
]

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
    "UNUSED ASSETS": "Ad assets with zero spend and zero impressions in the last 30 days.",
}

# ASSET TABLE columns to exclude from display.
_ASSET_EXCLUDE_COLUMNS: frozenset[str] = frozenset(
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
)

# Period table columns to show (display only; Copy TSV exports all columns).
_PERIOD_DISPLAY_COLUMNS: list[str] = [
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
]

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
            elif section.rows is None or (not section.rows and section.empty_message):
                parts.append(self._render_empty_section(section))
            elif not section.rows:
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
        if ": " in title:
            business_name = title.split(": ", 1)[1]
        else:
            business_name = title
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

        sid = _slugify(section.name)
        is_expanded = section.name in _DEFAULT_EXPANDED_SECTIONS
        collapsed_class = "" if is_expanded else " collapsed"

        # Build header cells with sort, tooltips, and alignment
        header_cells: list[str] = []
        for col_idx, col in enumerate(columns):
            align_cls = _column_align_class(rows, col)
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
                align_cls = _column_align_class(rows, col)
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
        json_rows = section.full_rows if section.full_rows is not None else section.rows
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
    """Compose a full HTML report from table results."""
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
    _period_tables = frozenset({"BY QUARTER", "BY MONTH", "BY WEEK"})

    for table_name in TABLE_ORDER:
        result = data.table_results.get(table_name)
        if result is None:
            sections.append(
                DataSection(
                    name=table_name,
                    rows=None,
                    error="[ERROR] missing: Table result not available",
                )
            )
        elif not result.success:
            error_type = result.error_type or "unknown"
            error_msg = result.error_message or "Unknown error"
            sections.append(
                DataSection(
                    name=table_name,
                    rows=None,
                    error=f"[ERROR] {error_type}: {error_msg}",
                )
            )
        elif not result.data:
            empty_msg = (
                "No unused assets found"
                if table_name == "UNUSED ASSETS"
                else "No data available"
            )
            sections.append(
                DataSection(
                    name=table_name,
                    rows=[],
                    empty_message=empty_msg,
                )
            )
        else:
            # Reconciliation tables: show pending message when payment
            # data is unavailable (Stripe REC-8 not shipped)
            if table_name in _RECONCILIATION_TABLES and _is_payment_data_pending(
                result.data
            ):
                sections.append(
                    DataSection(
                        name=table_name,
                        rows=[],
                        empty_message=_RECONCILIATION_PENDING_MESSAGE,
                    )
                )
                continue

            all_rows = result.data
            display_rows = all_rows

            # ASSET TABLE: sort by spend desc, exclude metadata columns
            if table_name == "ASSET TABLE":
                display_rows = sorted(
                    display_rows,
                    key=lambda r: r.get("spend") or 0,
                    reverse=True,
                )

            # Apply row limit
            row_limit = data.row_limits.get(table_name)
            total_rows = len(display_rows)
            if row_limit:
                display_rows = display_rows[:row_limit]
            truncated = row_limit is not None and total_rows > row_limit

            # ASSET TABLE: filter out excluded columns for display
            if table_name == "ASSET TABLE":
                display_rows = [
                    {k: v for k, v in row.items() if k not in _ASSET_EXCLUDE_COLUMNS}
                    for row in display_rows
                ]

            # Period tables: filter display columns (Copy TSV gets full data)
            if table_name in _period_tables:
                available = [
                    c
                    for c in _PERIOD_DISPLAY_COLUMNS
                    if any(c in r for r in display_rows)
                ]
                display_rows = [
                    {k: v for k, v in row.items() if k in available}
                    for row in display_rows
                ]

            sections.append(
                DataSection(
                    name=table_name,
                    rows=display_rows,
                    row_count=len(display_rows),
                    truncated=truncated,
                    total_rows=total_rows if truncated else None,
                    full_rows=all_rows,
                )
            )

    # Build footer
    elapsed = time.monotonic() - data.started_at
    tables_succeeded = sum(1 for r in data.table_results.values() if r.success)
    tables_failed = len(TABLE_ORDER) - tables_succeeded
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

# Reconciliation table names that should show pending message
_RECONCILIATION_TABLES = frozenset(
    {
        "LIFETIME RECONCILIATIONS",
        "T14 RECONCILIATIONS",
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
# Inline CSS — theme-aware design system (light/dark via CSS custom properties)
# ---------------------------------------------------------------------------

_CSS = """\
/* ===== CSS Custom Properties (Theme) ===== */
:root {
  --bg: #fafafa;
  --surface: #ffffff;
  --border: #e0e0e0;
  --border-light: #f0f0f0;
  --text: #1a1a1a;
  --text-muted: #888;
  --text-dim: #bbb;
  --accent: #4a7bb5;
  --accent-hover: #3568a0;
  --header-bg: #f4f4f4;
  --zebra: #f9f9f9;
  --green: #1e7a44;
  --green-bg: #e6f4ed;
  --yellow: #7a5c00;
  --yellow-bg: #fff8e0;
  --red: #9a1f1f;
  --red-bg: #fdeaea;
  --nav-bg: #ffffff;
  --nav-border: #e8e8e8;
  --shadow: 0 1px 2px rgba(0,0,0,0.08);
  --kpi-border: #e0e0e0;
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --mono: 'SF Mono', 'Consolas', 'Menlo', monospace;
}
[data-theme="dark"] {
  --bg: #1a1a1a;
  --surface: #242424;
  --border: #383838;
  --border-light: #2e2e2e;
  --text: #e8e8e8;
  --text-muted: #888;
  --text-dim: #555;
  --accent: #6fa0d4;
  --accent-hover: #85b3e0;
  --header-bg: #2a2a2a;
  --zebra: #212121;
  --green: #4ade80;
  --green-bg: #0f2e1a;
  --yellow: #fbbf24;
  --yellow-bg: #2a2000;
  --red: #f87171;
  --red-bg: #2e0f0f;
  --nav-bg: #1e1e1e;
  --nav-border: #333;
  --shadow: 0 1px 3px rgba(0,0,0,0.4);
  --kpi-border: #383838;
}

/* ===== Reset & Base ===== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 13px; scroll-behavior: smooth; }
body { font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.4; }

/* ===== Layout ===== */
.layout { display: flex; min-height: 100vh; }
.sidebar { width: 200px; min-width: 200px; background: var(--nav-bg); border-right: 1px solid var(--nav-border); position: sticky; top: 0; height: 100vh; overflow-y: auto; padding: 12px 0; flex-shrink: 0; }
.main-content { flex: 1; min-width: 0; padding: 16px 20px; max-width: 100%; }
@media (max-width: 768px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; height: auto; position: static; overflow-x: auto; display: flex; flex-wrap: wrap; padding: 8px; border-right: none; border-bottom: 1px solid var(--nav-border); }
  .sidebar .nav-section-label { display: none; }
  .nav-link { white-space: nowrap; }
}

/* ===== Sidebar Navigation ===== */
.nav-section-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); padding: 6px 14px 4px; margin-top: 4px; }
.nav-link { display: flex; justify-content: space-between; align-items: center; padding: 5px 14px; color: var(--text); text-decoration: none; font-size: 12px; border-left: 3px solid transparent; transition: background 0.1s, border-color 0.1s; }
.nav-link:hover { background: var(--border-light); border-left-color: var(--accent); color: var(--accent); }
.nav-link.active { border-left-color: var(--accent); color: var(--accent); background: var(--border-light); }
.badge { font-size: 10px; background: var(--border); color: var(--text-muted); border-radius: 3px; padding: 1px 5px; font-weight: 500; flex-shrink: 0; }

/* ===== Header ===== */
.report-header { margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.report-title { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
.report-meta { font-size: 11px; color: var(--text-muted); }
.report-meta a { color: var(--accent); text-decoration: none; }
.report-meta a:hover { text-decoration: underline; }
.header-actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; align-items: center; }
.btn { padding: 5px 12px; font-size: 12px; border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; border-radius: 3px; font-family: var(--font); transition: background 0.1s; }
.btn:hover { background: var(--header-bg); border-color: var(--accent); color: var(--accent); }
.search-wrap { flex: 1; max-width: 300px; position: relative; }
.search-wrap input { width: 100%; padding: 5px 10px; font-size: 12px; border: 1px solid var(--border); background: var(--surface); color: var(--text); border-radius: 3px; font-family: var(--font); outline: none; }
.search-wrap input:focus { border-color: var(--accent); }
.search-clear { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); cursor: pointer; color: var(--text-muted); font-size: 14px; line-height: 1; display: none; }
.search-count { font-size: 11px; color: var(--text-muted); margin-left: 8px; white-space: nowrap; }

/* ===== KPI Cards ===== */
.kpi-grid { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }
.kpi-card { flex: 1; min-width: 140px; max-width: 240px; border: 1px solid var(--kpi-border); background: var(--surface); border-radius: 4px; padding: 10px 14px; box-shadow: var(--shadow); }
.kpi-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 4px; }
.kpi-value { font-size: 20px; font-weight: 700; color: var(--text); line-height: 1.2; }
.kpi-sub { font-size: 10px; color: var(--text-muted); margin-top: 2px; }
.kpi-sparkline { margin-top: 6px; }
.trend-up { color: var(--green); }
.trend-down { color: var(--red); }

/* ===== Table Sections ===== */
.table-section { background: var(--surface); border: 1px solid var(--border); border-radius: 4px; margin-bottom: 12px; box-shadow: var(--shadow); overflow: hidden; }
.section-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 14px; background: var(--header-bg); border-bottom: 1px solid var(--border); cursor: pointer; user-select: none; }
.section-header h2 { font-size: 13px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 8px; }
.section-header h2 .badge { font-size: 10px; }
.section-controls { display: flex; gap: 6px; align-items: center; }
.toggle-icon { font-size: 10px; color: var(--text-muted); transition: transform 0.15s; }
.toggle-icon.collapsed { transform: rotate(-90deg); }
.section-body { overflow: hidden; }
.section-body.collapsed { display: none; }
.section-subtitle { padding: 6px 14px 0; font-size: 11px; color: var(--text-muted); font-style: italic; }

/* ===== Data Table ===== */
.table-scroll { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 11.5px; white-space: nowrap; }
.data-table thead th { background: var(--header-bg); border-bottom: 1px solid var(--border); padding: 5px 10px; text-align: left; font-weight: 600; font-size: 11px; color: var(--text); cursor: pointer; position: sticky; top: 0; user-select: none; }
.data-table thead th:hover { color: var(--accent); }
.sort-icon::after { content: ''; margin-left: 4px; }
th.sort-asc .sort-icon::after { content: '\25B2'; }
th.sort-desc .sort-icon::after { content: '\25BC'; }
.data-table tbody tr { border-bottom: 1px solid var(--border-light); }
.data-table tbody tr:nth-child(even) { background: var(--zebra); }
.data-table tbody tr:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); }
.data-table td { padding: 3px 10px; vertical-align: middle; max-width: 300px; overflow: hidden; text-overflow: ellipsis; }

/* Conditional formatting */
.br-green { background: var(--green-bg) !important; color: var(--green); font-weight: 600; }
.br-yellow { background: var(--yellow-bg) !important; color: var(--yellow); font-weight: 600; }
.br-red { background: var(--red-bg) !important; color: var(--red); font-weight: 600; }
.muted { color: var(--text-dim); }
.dash { color: var(--text-dim); }
.num { text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); font-size: 11px; }
.date-cell { text-align: center; font-family: var(--mono); font-size: 11px; color: var(--text-muted); }

/* Search highlight */
mark.search-hl { background: #ffe066; color: #1a1a1a; border-radius: 2px; padding: 0 1px; }
[data-theme="dark"] mark.search-hl { background: #7a6000; color: #ffe066; }
tr.search-hidden { display: none; }

/* Copy button */
.copy-btn { font-size: 10px; padding: 3px 8px; border: 1px solid var(--border); background: var(--surface); color: var(--text-muted); cursor: pointer; border-radius: 3px; font-family: var(--font); transition: background 0.1s; }
.copy-btn:hover { border-color: var(--accent); color: var(--accent); }
.copy-btn.copied { color: var(--green); border-color: var(--green); }

/* Toast */
.toast { position: fixed; bottom: 20px; right: 20px; background: #333; color: #fff; padding: 8px 16px; border-radius: 4px; font-size: 12px; opacity: 0; transition: opacity 0.2s; pointer-events: none; z-index: 1000; }
.toast.show { opacity: 1; }

/* Empty state */
.empty { padding: 20px; color: var(--text-muted); font-size: 12px; text-align: center; }

/* Truncation note */
.truncation-note { padding: 6px 14px; font-size: 11px; color: var(--text-muted); font-style: italic; border-top: 1px solid var(--border-light); }

/* Error box */
.error-box { padding: 12px 14px; margin: 8px 14px; background: var(--red-bg); border: 1px solid var(--red); border-radius: 4px; color: var(--red); font-size: 12px; }

/* Footer */
.report-footer { margin-top: 20px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 16px; font-size: 11px; color: var(--text-muted); }
.footer-item strong { color: var(--text); }

/* ===== Print Styles ===== */
@media print {
  .sidebar, .header-actions, .section-controls, .copy-btn { display: none !important; }
  .layout { display: block; }
  .main-content { padding: 0; }
  .section-body.collapsed { display: block !important; }
  .table-section { box-shadow: none; border: 1px solid #ccc; page-break-inside: avoid; margin-bottom: 20px; }
  .data-table { font-size: 9px; }
  .kpi-sparkline { display: none; }
  body { color: #000; background: #fff; }
  .data-table tbody tr:nth-child(even) { background: #f5f5f5; }
}"""

# ---------------------------------------------------------------------------
# Inline JavaScript — interactive features (sort, search, collapse, copy, theme)
# ---------------------------------------------------------------------------

_JS = """\
// ===== Sort =====
var sortState = {};

function sortTable(sid, colIdx) {
  var tbl = document.getElementById('tbl-' + sid);
  if (!tbl) return;
  var th = tbl.querySelectorAll('thead th');
  var key = sid + '-' + colIdx;
  var asc = sortState[key] !== 'asc';
  sortState[key] = asc ? 'asc' : 'desc';
  th.forEach(function(h, i) {
    h.classList.remove('sort-asc', 'sort-desc');
    if (i === colIdx) h.classList.add(asc ? 'sort-asc' : 'sort-desc');
  });
  var tbody = tbl.querySelector('tbody');
  var rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort(function(a, b) {
    var aCell = (a.cells[colIdx] && a.cells[colIdx].textContent || '').trim();
    var bCell = (b.cells[colIdx] && b.cells[colIdx].textContent || '').trim();
    var aNum = parseFloat(aCell.replace(/[^0-9.\\-]/g, ''));
    var bNum = parseFloat(bCell.replace(/[^0-9.\\-]/g, ''));
    var cmp = 0;
    if (!isNaN(aNum) && !isNaN(bNum)) { cmp = aNum - bNum; }
    else { cmp = aCell.localeCompare(bCell, undefined, {numeric: true}); }
    return asc ? cmp : -cmp;
  });
  rows.forEach(function(r) { tbody.appendChild(r); });
}

// ===== Search =====
var searchTimeout = null;

function onSearch(val) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(function() { doSearch(val); }, 80);
  var clear = document.getElementById('search-clear');
  if (clear) clear.style.display = val ? 'block' : 'none';
}

function clearSearch() {
  var inp = document.getElementById('global-search');
  if (inp) { inp.value = ''; doSearch(''); }
  var clear = document.getElementById('search-clear');
  if (clear) clear.style.display = 'none';
}

function doSearch(query) {
  var q = query.trim().toLowerCase();
  var countEl = document.getElementById('search-count');
  if (!q) {
    document.querySelectorAll('mark.search-hl').forEach(function(m) { m.outerHTML = m.innerHTML; });
    document.querySelectorAll('tr.search-hidden').forEach(function(r) { r.classList.remove('search-hidden'); });
    if (countEl) countEl.textContent = '';
    return;
  }
  var totalMatch = 0;
  document.querySelectorAll('.data-table tbody tr').forEach(function(row) {
    var text = row.textContent.toLowerCase();
    if (text.includes(q)) { row.classList.remove('search-hidden'); totalMatch++; }
    else { row.classList.add('search-hidden'); }
  });
  document.querySelectorAll('mark.search-hl').forEach(function(m) { m.outerHTML = m.innerHTML; });
  var re = new RegExp('(' + q.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
  document.querySelectorAll('.data-table tbody tr:not(.search-hidden) td').forEach(function(td) {
    if (td.querySelector('span[title]')) return;
    td.innerHTML = td.innerHTML.replace(re, '<mark class="search-hl">$1</mark>');
  });
  if (countEl) countEl.textContent = totalMatch + ' row' + (totalMatch !== 1 ? 's' : '') + ' matched';
}

// ===== Collapse/Expand =====
function toggleSection(sid) {
  var body = document.getElementById('body-' + sid);
  var icon = document.getElementById('toggle-' + sid);
  if (!body) return;
  var collapsed = body.classList.toggle('collapsed');
  if (icon) icon.classList.toggle('collapsed', collapsed);
}

function expandAll() {
  document.querySelectorAll('.section-body').forEach(function(b) { b.classList.remove('collapsed'); });
  document.querySelectorAll('.toggle-icon').forEach(function(i) { i.classList.remove('collapsed'); });
}

function collapseAll() {
  document.querySelectorAll('.section-body').forEach(function(b) { b.classList.add('collapsed'); });
  document.querySelectorAll('.toggle-icon').forEach(function(i) { i.classList.add('collapsed'); });
}

// ===== Copy TSV =====
function copyTable(sid) {
  var dataEl = document.getElementById('data-' + sid);
  if (!dataEl) return;
  try {
    var rows = JSON.parse(dataEl.textContent);
    if (!rows.length) return;
    var headers = Object.keys(rows[0]);
    var tsv = [headers.join('\\t')]
      .concat(rows.map(function(r) { return headers.map(function(h) { return String(r[h] != null ? r[h] : ''); }).join('\\t'); }))
      .join('\\n');
    navigator.clipboard.writeText(tsv).then(function() {
      showToast('Table copied as TSV (' + rows.length + ' rows, ' + headers.length + ' columns)');
      var btn = document.querySelector('[onclick=\"copyTable(\\'' + sid + '\\')\"');
      if (btn) { btn.textContent = 'Copied!'; btn.classList.add('copied'); setTimeout(function() { btn.textContent = 'Copy TSV'; btn.classList.remove('copied'); }, 1500); }
    }).catch(function() { showToast('Copy failed'); });
  } catch(e) { showToast('Copy failed'); }
}

function showToast(msg) {
  var t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function() { t.classList.remove('show'); }, 2000);
}

// ===== Theme Toggle =====
function toggleTheme() {
  var html = document.documentElement;
  var current = html.getAttribute('data-theme');
  var next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  var btn = document.getElementById('theme-btn');
  if (btn) btn.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
  try { localStorage.setItem('theme', next); } catch(e) {}
}

// ===== Active Nav (Scroll Spy) =====
function updateActiveNav() {
  var sections = document.querySelectorAll('.table-section');
  var navLinks = document.querySelectorAll('.nav-link');
  var current = '';
  sections.forEach(function(sec) {
    var top = sec.getBoundingClientRect().top;
    if (top < 200) current = sec.id;
  });
  navLinks.forEach(function(link) {
    link.classList.toggle('active', link.getAttribute('href') === '#' + current);
  });
}

// ===== Init =====
(function() {
  var saved = typeof localStorage !== 'undefined' ? localStorage.getItem('theme') : null;
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
  var btn = document.getElementById('theme-btn');
  var theme = document.documentElement.getAttribute('data-theme');
  if (btn) btn.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
  window.addEventListener('scroll', updateActiveNav, {passive: true});
  updateActiveNav();
})();"""
