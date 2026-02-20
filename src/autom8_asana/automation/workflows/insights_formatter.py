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
    """Input data for composing a full report.

    Attributes:
        business_name: Name of the Business (for header).
        office_phone: E.164 phone number (will be masked in header).
        vertical: Business vertical.
        table_results: Dict mapping table name to TableResult.
        started_at: Monotonic time when offer processing started.
        version: Workflow version identifier.
        row_limits: Per-table row limit configuration.
    """

    business_name: str
    office_phone: str
    vertical: str
    table_results: dict[str, TableResult]
    started_at: float  # time.monotonic() value
    version: str
    row_limits: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# StructuredDataRenderer protocol + DataSection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DataSection:
    """A named section containing tabular data or a status message.

    Universal input shape for StructuredDataRenderer -- not coupled to
    any specific workflow or data source.
    """

    name: str
    rows: list[dict[str, Any]] | None
    row_count: int = 0
    truncated: bool = False
    total_rows: int | None = None
    error: str | None = None
    empty_message: str | None = None


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
        parts.append('<div class="container">')
        parts.append(self._render_header(title, metadata))

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

        parts.append("</div>")
        parts.append("</body>")
        parts.append("</html>")
        return "\n".join(parts) + "\n"

    # --- Private rendering methods ---

    def _render_doctype_and_head(self, title: str) -> str:
        escaped_title = html.escape(title)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>{escaped_title}</title>\n"
            f"<style>\n{_CSS}\n</style>\n"
            "</head>"
        )

    def _render_header(self, title: str, metadata: dict[str, str]) -> str:
        escaped_title = html.escape(title)
        meta_items = "\n".join(
            f'<span class="meta-item"><strong>{html.escape(k)}:</strong> {html.escape(v)}</span>'
            for k, v in metadata.items()
        )
        return (
            '<header class="report-header">\n'
            f'<h1 class="report-title">{escaped_title}</h1>\n'
            f'<div class="report-meta">{meta_items}</div>\n'
            "</header>"
        )

    def _render_table_section(self, section: DataSection) -> str:
        rows = section.rows or []
        columns = _discover_columns(rows)
        columns = _reorder_columns(columns, COLUMN_ORDER.get(section.name))

        if not columns:
            return self._render_empty_section(section)

        section_id = _slugify(section.name)
        header_cells = "".join(
            f'<th class="{_column_align_class(rows, col)}">'
            f"{html.escape(_to_title_case(col))}</th>"
            for col in columns
        )

        body_rows: list[str] = []
        for row in rows:
            cells = "".join(
                f'<td class="{_column_align_class(rows, col)}">'
                f"{_format_cell_html(row.get(col))}</td>"
                for col in columns
            )
            body_rows.append(f"<tr>{cells}</tr>")

        parts = [
            f'<section id="{section_id}" class="table-section">',
            '<div class="section-header">',
            f"<h2>{html.escape(section.name)} "
            f'<span class="badge">{section.row_count}</span></h2>',
            "</div>",
            '<div class="section-body">',
            '<div class="table-scroll">',
            "<table>",
            f"<thead><tr>{header_cells}</tr></thead>",
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

        parts.append("</div>")
        parts.append("</section>")
        return "\n".join(parts)

    def _render_empty_section(self, section: DataSection) -> str:
        section_id = _slugify(section.name)
        message = section.empty_message or "No data available"
        return (
            f'<section id="{section_id}" class="table-section">\n'
            f'<div class="section-header">\n'
            f"<h2>{html.escape(section.name)}</h2>\n"
            "</div>\n"
            '<div class="section-body">\n'
            f'<p class="empty-message">{html.escape(message)}</p>\n'
            "</div>\n"
            "</section>"
        )

    def _render_error_section(self, section: DataSection) -> str:
        section_id = _slugify(section.name)
        error_text = section.error or "Unknown error"
        return (
            f'<section id="{section_id}" class="table-section">\n'
            f'<div class="section-header">\n'
            f"<h2>{html.escape(section.name)}</h2>\n"
            "</div>\n"
            '<div class="section-body">\n'
            f'<div class="error-box">{html.escape(error_text)}</div>\n'
            "</div>\n"
            "</section>"
        )

    def _render_footer(self, footer: dict[str, str]) -> str:
        items = "\n".join(
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

    Thin adapter: unpacks InsightsReportData into DataSection list
    and delegates to HtmlRenderer.render_document().

    Args:
        data: InsightsReportData with all table results.

    Returns:
        Complete HTML string.
    """
    # Build metadata
    masked = mask_phone_number(data.office_phone)
    timestamp = datetime.now(UTC).isoformat()
    metadata: dict[str, str] = {
        "Phone": masked,
        "Vertical": data.vertical,
        "Generated": timestamp,
        "Period": "Daily insights report",
    }

    # Build sections in fixed order
    sections: list[DataSection] = []
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
            row_limit = data.row_limits.get(table_name)
            total_rows = len(result.data)
            display_rows = result.data[:row_limit] if row_limit else result.data
            truncated = row_limit is not None and total_rows > row_limit
            sections.append(
                DataSection(
                    name=table_name,
                    rows=display_rows,
                    row_count=len(display_rows),
                    truncated=truncated,
                    total_rows=total_rows if truncated else None,
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


def _to_title_case(column_name: str) -> str:
    """Convert snake_case column name to Title Case.

    Per PRD FR-W03.4: offer_cost -> Offer Cost

    Args:
        column_name: Snake-case column name from API response.

    Returns:
        Title Case display name.
    """
    return column_name.replace("_", " ").title()


def _format_cell_html(value: Any) -> str:
    """Format a single cell value for HTML table display.

    None values render as a styled dash indicator.
    All string values are HTML-escaped to prevent XSS.

    Args:
        value: Cell value (may be None).

    Returns:
        HTML-safe string for table cell content.
    """
    if value is None:
        return '<span class="null-value">---</span>'
    return html.escape(str(value))


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


# ---------------------------------------------------------------------------
# Inline CSS (self-contained, no external resources)
# ---------------------------------------------------------------------------

_CSS = """\
/* Reset & Base */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 14px; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #fafafa;
  color: #1a1a1a;
  line-height: 1.5;
  padding: 0;
  margin: 0;
}

/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px;
}

/* Header */
.report-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e0e0e0;
}
.report-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #1a1a1a;
}
.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #666;
}
.meta-item strong {
  color: #333;
}

/* Table Sections */
.table-section {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  margin-bottom: 16px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.section-header {
  padding: 10px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}
.section-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge {
  font-size: 11px;
  background: #e0e0e0;
  color: #666;
  border-radius: 10px;
  padding: 1px 8px;
  font-weight: 500;
}
.section-body {
  overflow: hidden;
}

/* Tables */
.table-scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
thead tr {
  background: #f9f9f9;
  border-bottom: 2px solid #e0e0e0;
}
th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  white-space: nowrap;
}
th.num {
  text-align: right;
}
td {
  padding: 6px 12px;
  border-bottom: 1px solid #f0f0f0;
  color: #1a1a1a;
}
td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
tbody tr:nth-child(even) {
  background: #f9f9f9;
}
tbody tr:hover {
  background: #f0f4ff;
}

/* Null value indicator */
.null-value {
  color: #bbb;
}

/* Empty message */
.empty-message {
  padding: 20px 16px;
  color: #888;
  font-style: italic;
  text-align: center;
}

/* Error box */
.error-box {
  padding: 12px 16px;
  margin: 12px 16px;
  background: #fdeaea;
  border: 1px solid #f5c6c6;
  border-radius: 4px;
  color: #9a1f1f;
  font-size: 13px;
}

/* Truncation note */
.truncation-note {
  padding: 8px 16px;
  font-size: 12px;
  color: #888;
  font-style: italic;
  border-top: 1px solid #f0f0f0;
}

/* Footer */
.report-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 2px solid #e0e0e0;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: 13px;
  color: #666;
}
.footer-item strong {
  color: #333;
}

/* Print styles */
@media print {
  body { background: #fff; }
  .container { max-width: none; padding: 0; }
  .table-section { box-shadow: none; break-inside: avoid; }
  .report-footer { break-before: avoid; }
}

/* Responsive */
@media (max-width: 768px) {
  .container { padding: 12px; }
  table { font-size: 12px; }
  th, td { padding: 4px 8px; }
}"""
