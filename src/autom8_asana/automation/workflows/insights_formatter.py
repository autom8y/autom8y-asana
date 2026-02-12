"""Markdown report formatter for insights export.

Per TDD-EXPORT-001: Produces pipe-table markdown from table data dicts.
Pure functions with no external dependencies. All formatting logic
is concentrated here for testability.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from autom8_asana.clients.data.client import mask_phone_number


# Section order (per PRD FR-W01.6)
TABLE_ORDER: list[str] = [
    "SUMMARY",
    "APPOINTMENTS",
    "LEADS",
    "BY QUARTER",
    "BY MONTH",
    "BY WEEK",
    "AD QUESTIONS",
    "ASSET TABLE",
    "OFFER TABLE",
    "UNUSED ASSETS",
]


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
    """Input data for composing a full markdown report.

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


def compose_report(data: InsightsReportData) -> str:
    """Compose a full markdown report from table results.

    Section order: Header -> 10 tables -> Footer

    Args:
        data: InsightsReportData with all table results.

    Returns:
        Complete markdown string.
    """
    sections: list[str] = []

    # Header
    sections.append(_format_header(data))

    # Tables in fixed order
    for table_name in TABLE_ORDER:
        result = data.table_results.get(table_name)
        if result is None:
            sections.append(
                _format_error_section(
                    table_name, "missing", "Table result not available"
                )
            )
        elif not result.success:
            sections.append(
                _format_error_section(
                    table_name,
                    result.error_type or "unknown",
                    result.error_message or "Unknown error",
                )
            )
        elif not result.data:
            sections.append(_format_empty_section(table_name))
        else:
            row_limit = data.row_limits.get(table_name)
            sections.append(_format_table_section(table_name, result.data, row_limit))

    # Footer
    elapsed = time.monotonic() - data.started_at
    tables_succeeded = sum(1 for r in data.table_results.values() if r.success)
    tables_failed = len(TABLE_ORDER) - tables_succeeded
    sections.append(
        _format_footer(elapsed, tables_succeeded, tables_failed, data.version)
    )

    return "\n\n".join(sections) + "\n"


def _format_header(data: InsightsReportData) -> str:
    """Format the report header section.

    Includes: business name, masked phone, vertical, timestamp.
    """
    masked = mask_phone_number(data.office_phone)
    timestamp = datetime.now(UTC).isoformat()
    return (
        f"# Insights Export: {data.business_name}\n\n"
        f"**Phone**: {masked}  \n"
        f"**Vertical**: {data.vertical}  \n"
        f"**Generated**: {timestamp}  \n"
        f"**Period**: Daily insights report"
    )


def _format_table_section(
    table_name: str,
    rows: list[dict[str, Any]],
    row_limit: int | None = None,
) -> str:
    """Format a table section with pipe-table markdown.

    Args:
        table_name: Table heading name.
        rows: List of row dicts.
        row_limit: Maximum rows to display. None = no limit.

    Returns:
        Markdown string with heading, pipe table, and optional truncation note.
    """
    total_rows = len(rows)
    display_rows = rows[:row_limit] if row_limit else rows
    truncated = row_limit is not None and total_rows > row_limit

    # Collect all column names (union of all rows, preserving first-seen order)
    columns: list[str] = []
    seen: set[str] = set()
    for row in display_rows:
        for key in row:
            if key not in seen:
                columns.append(key)
                seen.add(key)

    if not columns:
        return f"## {table_name}\n\n> No data available"

    # Header row (Title Case)
    header_cells = [_to_title_case(col) for col in columns]
    header_line = "| " + " | ".join(header_cells) + " |"

    # Alignment row
    align_line = "| " + " | ".join("---" for _ in columns) + " |"

    # Data rows
    data_lines: list[str] = []
    for row in display_rows:
        cells = [_format_cell(row.get(col)) for col in columns]
        data_lines.append("| " + " | ".join(cells) + " |")

    parts = [f"## {table_name}", "", header_line, align_line] + data_lines

    if truncated:
        parts.append("")
        parts.append(f"> Showing first {row_limit} of {total_rows} rows")

    return "\n".join(parts)


def _format_empty_section(table_name: str) -> str:
    """Format an empty table section.

    Per PRD FR-W03.3: Zero rows -> "No data available" note.
    Special case for UNUSED ASSETS: "No unused assets found".
    """
    if table_name == "UNUSED ASSETS":
        return f"## {table_name}\n\n> No unused assets found"
    return f"## {table_name}\n\n> No data available"


def _format_error_section(
    table_name: str,
    error_type: str,
    message: str,
) -> str:
    """Format an error marker section.

    Per PRD FR-W02.2:
    ## TABLE_NAME
    > [ERROR] {error_type}: {message}
    """
    return f"## {table_name}\n\n> [ERROR] {error_type}: {message}"


def _format_footer(
    duration_seconds: float,
    tables_succeeded: int,
    tables_failed: int,
    version: str,
) -> str:
    """Format the report footer section.

    Per PRD FR-W03.7: Duration, table count, error count, version.
    """
    total = tables_succeeded + tables_failed
    parts = [
        "---",
        "",
        f"**Duration**: {duration_seconds:.2f}s  ",
        f"**Tables**: {tables_succeeded}/{total}  ",
    ]
    if tables_failed > 0:
        parts.append(f"**Errors**: {tables_failed}  ")
    parts.append(f"**Version**: {version}")
    return "\n".join(parts)


def _to_title_case(column_name: str) -> str:
    """Convert snake_case column name to Title Case.

    Per PRD FR-W03.4: offer_cost -> Offer Cost

    Args:
        column_name: Snake-case column name from API response.

    Returns:
        Title Case display name.
    """
    return column_name.replace("_", " ").title()


def _format_cell(value: Any) -> str:
    """Format a single cell value for pipe table display.

    Per PRD FR-W03.5: Null values rendered as `---`.
    Pipe characters in values are escaped to prevent markdown table corruption.

    Args:
        value: Cell value (may be None).

    Returns:
        String representation for the pipe table cell.
    """
    if value is None:
        return "---"
    text = str(value)
    # Escape pipe characters to prevent corrupting pipe-table column structure
    return text.replace("|", "\\|")
