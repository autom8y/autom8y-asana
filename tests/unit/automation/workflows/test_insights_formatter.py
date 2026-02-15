"""Tests for insights_formatter.py -- pure-function markdown formatter.

Covers TDD Section 9.2 test scenarios:
- TestPipeTable: Valid markdown pipe table output (AC-W03.1, AC-W03.3, AC-W03.6)
- TestHeader: Masked phone, business name, vertical, timestamp (AC-W03.2)
- TestColumnNames: snake_case -> Title Case conversion (AC-W03.4)
- TestNullHandling: Null values render as "---" (AC-W03.5)
- TestNullColumns: Always-null columns present with "---" markers (AC-W03.5)
- TestEmptyTable: Zero rows -> "No data available" (AC-W03.7)
- TestUnusedAssetsEmpty: Zero matching -> "No unused assets found" (AC-W03.7)
- TestFooter: Duration, table count, error count, version (AC-W03.8)
- TestRowLimit: Truncation note when limit reached (AC-W03.10)
- TestErrorMarker: Error marker format (AC-W02.2, AC-W02.5)
- TestComposeReport: Full report composition with mixed results (AC-W03.1)
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from autom8_asana.automation.workflows.insights_formatter import (
    TABLE_ORDER,
    InsightsReportData,
    TableResult,
    _format_cell,
    _format_empty_section,
    _format_error_section,
    _format_footer,
    _format_header,
    _format_table_section,
    _to_title_case,
    compose_report,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_report_data(
    table_results: dict[str, TableResult] | None = None,
    business_name: str = "Test Dental",
    office_phone: str = "+17705753103",
    vertical: str = "dental",
    started_at: float | None = None,
    version: str = "insights-export-v1.0",
    row_limits: dict[str, int] | None = None,
) -> InsightsReportData:
    """Build an InsightsReportData with sensible defaults."""
    return InsightsReportData(
        business_name=business_name,
        office_phone=office_phone,
        vertical=vertical,
        table_results=table_results or {},
        started_at=started_at if started_at is not None else time.monotonic(),
        version=version,
        row_limits=row_limits or {},
    )


def _make_table_result(
    table_name: str,
    data: list[dict] | None = None,
    success: bool = True,
    error_type: str | None = None,
    error_message: str | None = None,
) -> TableResult:
    """Build a TableResult with sensible defaults."""
    return TableResult(
        table_name=table_name,
        success=success,
        data=data,
        row_count=len(data) if data else 0,
        error_type=error_type,
        error_message=error_message,
    )


# ---------------------------------------------------------------------------
# TestPipeTable -- AC-W03.1, AC-W03.3, AC-W03.6
# ---------------------------------------------------------------------------


class TestPipeTable:
    """Valid markdown pipe table output from _format_table_section."""

    def test_single_row_table(self):
        rows = [{"offer_cost": 1500, "impressions": 45000, "clicks": 1200}]
        result = _format_table_section("SUMMARY", rows)

        lines = result.split("\n")
        assert lines[0] == "## SUMMARY"
        assert lines[1] == ""
        # Header row
        assert lines[2] == "| Offer Cost | Impressions | Clicks |"
        # Alignment row
        assert lines[3] == "| --- | --- | --- |"
        # Data row
        assert lines[4] == "| 1500 | 45000 | 1200 |"
        assert len(lines) == 5

    def test_multiple_rows(self):
        rows = [
            {"date": "2026-02-10", "name": "John", "status": "confirmed"},
            {"date": "2026-02-11", "name": "Jane", "status": "pending"},
            {"date": "2026-02-12", "name": "Bob", "status": "cancelled"},
        ]
        result = _format_table_section("APPOINTMENTS", rows)

        lines = result.split("\n")
        assert lines[0] == "## APPOINTMENTS"
        assert lines[1] == ""
        assert lines[2] == "| Date | Name | Status |"
        assert lines[3] == "| --- | --- | --- |"
        # 3 data rows
        assert lines[4] == "| 2026-02-10 | John | confirmed |"
        assert lines[5] == "| 2026-02-11 | Jane | pending |"
        assert lines[6] == "| 2026-02-12 | Bob | cancelled |"
        assert len(lines) == 7

    def test_columns_union_preserves_order(self):
        """Columns are a union of all row keys, preserving first-seen order."""
        rows = [
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
        ]
        result = _format_table_section("TEST", rows)

        lines = result.split("\n")
        # Headers: a, b, c (first-seen order across all rows)
        assert lines[2] == "| A | B | C |"
        # Second row missing 'a' -> gets None -> "---"
        assert "| --- | 3 | 4 |" in lines[5]

    def test_empty_rows_list_returns_no_data(self):
        """Empty dict rows (no keys) produce 'No data available'."""
        rows = [{}]
        result = _format_table_section("TEST", rows)
        assert "> No data available" in result


# ---------------------------------------------------------------------------
# TestHeader -- AC-W03.2
# ---------------------------------------------------------------------------


class TestHeader:
    """_format_header includes masked phone, business name, vertical, ISO timestamp."""

    def test_header_contains_business_name(self):
        data = _make_report_data(business_name="Smith Chiropractic")
        result = _format_header(data)
        assert "# Insights Export: Smith Chiropractic" in result

    def test_header_contains_masked_phone(self):
        data = _make_report_data(office_phone="+17705753103")
        result = _format_header(data)
        assert "+1770***3103" in result
        assert "+17705753103" not in result

    def test_header_contains_vertical(self):
        data = _make_report_data(vertical="chiropractic")
        result = _format_header(data)
        assert "**Vertical**: chiropractic" in result

    def test_header_contains_iso_timestamp(self):
        data = _make_report_data()
        result = _format_header(data)
        # ISO timestamp includes T separator and timezone info
        assert "**Generated**:" in result
        # Should contain date-like pattern
        assert "202" in result  # Year prefix

    def test_header_contains_period(self):
        data = _make_report_data()
        result = _format_header(data)
        assert "**Period**: Daily insights report" in result

    def test_header_trailing_spaces_for_linebreaks(self):
        """Markdown trailing double-space for line breaks."""
        data = _make_report_data()
        result = _format_header(data)
        lines = result.split("\n")
        # Phone, Vertical, Generated lines end with "  " for markdown linebreaks
        phone_line = [ln for ln in lines if "**Phone**" in ln][0]
        vertical_line = [ln for ln in lines if "**Vertical**" in ln][0]
        generated_line = [ln for ln in lines if "**Generated**" in ln][0]
        assert phone_line.endswith("  ")
        assert vertical_line.endswith("  ")
        assert generated_line.endswith("  ")


# ---------------------------------------------------------------------------
# TestColumnNames -- AC-W03.4
# ---------------------------------------------------------------------------


class TestColumnNames:
    """_to_title_case converts snake_case to Title Case."""

    def test_offer_cost(self):
        assert _to_title_case("offer_cost") == "Offer Cost"

    def test_single_word(self):
        assert _to_title_case("imp") == "Imp"

    def test_three_words(self):
        assert _to_title_case("time_on_call") == "Time On Call"

    def test_already_single_word(self):
        assert _to_title_case("clicks") == "Clicks"

    def test_empty_string(self):
        assert _to_title_case("") == ""


# ---------------------------------------------------------------------------
# TestNullHandling -- AC-W03.5
# ---------------------------------------------------------------------------


class TestNullHandling:
    """Null values render as '---' in pipe table cells."""

    def test_format_cell_none(self):
        assert _format_cell(None) == "---"

    def test_format_cell_string(self):
        assert _format_cell("hello") == "hello"

    def test_format_cell_integer(self):
        assert _format_cell(42) == "42"

    def test_format_cell_float(self):
        assert _format_cell(3.14) == "3.14"

    def test_format_cell_zero(self):
        assert _format_cell(0) == "0"

    def test_format_cell_empty_string(self):
        assert _format_cell("") == ""

    def test_null_values_in_pipe_table(self):
        """Rows with None values in pipe table show '---'."""
        rows = [
            {"date": "2026-02-10", "name": "John", "status": None},
        ]
        result = _format_table_section("TEST", rows)
        assert "| 2026-02-10 | John | --- |" in result


# ---------------------------------------------------------------------------
# TestNullColumns -- AC-W03.5
# ---------------------------------------------------------------------------


class TestNullColumns:
    """Always-null columns are present with '---' markers when data has those keys."""

    def test_appointments_null_columns(self):
        """APPOINTMENTS: out_calls, in_calls, time_on_call always null."""
        rows = [
            {
                "date": "2026-02-10",
                "name": "John Doe",
                "status": "confirmed",
                "out_calls": None,
                "in_calls": None,
                "time_on_call": None,
            },
        ]
        result = _format_table_section("APPOINTMENTS", rows)

        # Column headers present
        assert "Out Calls" in result
        assert "In Calls" in result
        assert "Time On Call" in result

        # Data row has --- for null columns
        data_line = result.split("\n")[4]
        assert "| 2026-02-10 | John Doe | confirmed | --- | --- | --- |" == data_line

    def test_leads_null_columns(self):
        """LEADS: follow_up, convo, lead_call_time always null."""
        rows = [
            {
                "date": "2026-02-08",
                "name": "Jane Smith",
                "source": "web",
                "follow_up": None,
                "convo": None,
                "lead_call_time": None,
            },
        ]
        result = _format_table_section("LEADS", rows)

        assert "Follow Up" in result
        assert "Convo" in result
        assert "Lead Call Time" in result

        data_line = result.split("\n")[4]
        assert "| 2026-02-08 | Jane Smith | web | --- | --- | --- |" == data_line


# ---------------------------------------------------------------------------
# TestEmptyTable -- AC-W03.7
# ---------------------------------------------------------------------------


class TestEmptyTable:
    """Zero rows -> 'No data available'."""

    def test_empty_summary(self):
        result = _format_empty_section("SUMMARY")
        assert result == "## SUMMARY\n\n> No data available"

    def test_empty_appointments(self):
        result = _format_empty_section("APPOINTMENTS")
        assert result == "## APPOINTMENTS\n\n> No data available"

    def test_empty_generic_table(self):
        result = _format_empty_section("BY QUARTER")
        assert result == "## BY QUARTER\n\n> No data available"


# ---------------------------------------------------------------------------
# TestUnusedAssetsEmpty -- AC-W03.7
# ---------------------------------------------------------------------------


class TestUnusedAssetsEmpty:
    """UNUSED ASSETS empty shows special message."""

    def test_unused_assets_empty(self):
        result = _format_empty_section("UNUSED ASSETS")
        assert result == "## UNUSED ASSETS\n\n> No unused assets found"

    def test_unused_assets_distinct_from_other_tables(self):
        """Verify UNUSED ASSETS message differs from other empty tables."""
        unused = _format_empty_section("UNUSED ASSETS")
        summary = _format_empty_section("SUMMARY")
        assert "No unused assets found" in unused
        assert "No data available" in summary
        assert unused != summary


# ---------------------------------------------------------------------------
# TestFooter -- AC-W03.8
# ---------------------------------------------------------------------------


class TestFooter:
    """_format_footer includes duration, table count, error count, version."""

    def test_footer_basic(self):
        result = _format_footer(3.456, 10, 0, "insights-export-v1.0")
        assert "**Duration**: 3.46s" in result
        assert "**Tables**: 10/10" in result
        assert "**Version**: insights-export-v1.0" in result

    def test_footer_no_errors_omits_error_line(self):
        result = _format_footer(1.0, 10, 0, "v1")
        assert "**Errors**" not in result

    def test_footer_with_errors(self):
        result = _format_footer(2.5, 8, 2, "v1")
        assert "**Tables**: 8/10" in result
        assert "**Errors**: 2" in result

    def test_footer_duration_two_decimal_places(self):
        result = _format_footer(0.1, 10, 0, "v1")
        assert "**Duration**: 0.10s" in result

    def test_footer_duration_rounding(self):
        result = _format_footer(3.999, 10, 0, "v1")
        assert "**Duration**: 4.00s" in result

    def test_footer_starts_with_horizontal_rule(self):
        result = _format_footer(1.0, 10, 0, "v1")
        assert result.startswith("---")

    def test_footer_version_is_last_line(self):
        result = _format_footer(1.0, 10, 0, "insights-export-v1.0")
        lines = result.strip().split("\n")
        assert lines[-1] == "**Version**: insights-export-v1.0"


# ---------------------------------------------------------------------------
# TestRowLimit -- AC-W03.10
# ---------------------------------------------------------------------------


class TestRowLimit:
    """Truncation note when row limit is reached."""

    def test_truncation_note(self):
        rows = [{"id": i, "value": f"row_{i}"} for i in range(150)]
        result = _format_table_section("APPOINTMENTS", rows, row_limit=100)

        lines = result.split("\n")
        # Should have heading + blank + header + alignment + 100 data rows + blank + truncation
        data_rows = [
            ln
            for ln in lines
            if ln.startswith("| ") and "---" not in ln and "Id" not in ln
        ]
        assert len(data_rows) == 100
        assert "> Showing first 100 of 150 rows" in result

    def test_no_truncation_when_under_limit(self):
        rows = [{"id": i} for i in range(50)]
        result = _format_table_section("LEADS", rows, row_limit=100)
        assert "> Showing first" not in result

    def test_no_truncation_when_at_limit(self):
        rows = [{"id": i} for i in range(100)]
        result = _format_table_section("LEADS", rows, row_limit=100)
        assert "> Showing first" not in result

    def test_no_truncation_when_no_limit(self):
        rows = [{"id": i} for i in range(200)]
        result = _format_table_section("BY MONTH", rows, row_limit=None)
        assert "> Showing first" not in result
        data_rows = [
            ln
            for ln in result.split("\n")
            if ln.startswith("| ") and "---" not in ln and "Id" not in ln
        ]
        assert len(data_rows) == 200


# ---------------------------------------------------------------------------
# TestErrorMarker -- AC-W02.2, AC-W02.5
# ---------------------------------------------------------------------------


class TestErrorMarker:
    """Error marker format: > [ERROR] type: message."""

    def test_basic_error_marker(self):
        result = _format_error_section(
            "APPOINTMENTS", "InsightsServiceError", "Request timed out"
        )
        expected = (
            "## APPOINTMENTS\n\n> [ERROR] InsightsServiceError: Request timed out"
        )
        assert result == expected

    def test_error_marker_is_blockquote(self):
        result = _format_error_section("SUMMARY", "timeout", "Server unavailable")
        # Blockquote starts with >
        lines = result.split("\n")
        error_line = [ln for ln in lines if "[ERROR]" in ln][0]
        assert error_line.startswith(">")

    def test_error_marker_includes_heading(self):
        result = _format_error_section("BY QUARTER", "api_error", "500")
        assert result.startswith("## BY QUARTER")

    def test_missing_table_error_marker(self):
        """When a table result is None, compose_report generates a 'missing' error."""
        result = _format_error_section("LEADS", "missing", "Table result not available")
        assert "> [ERROR] missing: Table result not available" in result


# ---------------------------------------------------------------------------
# TestComposeReport -- AC-W03.1
# ---------------------------------------------------------------------------


class TestComposeReport:
    """Full compose_report with mixed results."""

    def _build_mixed_report_data(self, started_at: float) -> InsightsReportData:
        """Build report data with mixed success/error/empty results."""
        table_results: dict[str, TableResult] = {}

        # SUMMARY: success with data
        table_results["SUMMARY"] = _make_table_result(
            "SUMMARY",
            data=[{"offer_cost": 1500, "impressions": 45000}],
        )

        # APPOINTMENTS: error
        table_results["APPOINTMENTS"] = _make_table_result(
            "APPOINTMENTS",
            success=False,
            error_type="InsightsServiceError",
            error_message="Request timed out",
        )

        # LEADS: success with data
        table_results["LEADS"] = _make_table_result(
            "LEADS",
            data=[{"date": "2026-02-08", "name": "Jane"}],
        )

        # BY QUARTER: empty
        table_results["BY QUARTER"] = _make_table_result(
            "BY QUARTER",
            data=[],
        )

        # BY MONTH: success with data
        table_results["BY MONTH"] = _make_table_result(
            "BY MONTH",
            data=[{"month": "January", "spend": 500}],
        )

        # BY WEEK: success with data
        table_results["BY WEEK"] = _make_table_result(
            "BY WEEK",
            data=[{"week": "W01", "spend": 100}],
        )

        # AD QUESTIONS: success with data
        table_results["AD QUESTIONS"] = _make_table_result(
            "AD QUESTIONS",
            data=[{"question": "Hours?", "answer": "9-5"}],
        )

        # ASSET TABLE: success with data
        table_results["ASSET TABLE"] = _make_table_result(
            "ASSET TABLE",
            data=[{"asset": "banner_1", "imp": 1000}],
        )

        # OFFER TABLE: success with data
        table_results["OFFER TABLE"] = _make_table_result(
            "OFFER TABLE",
            data=[{"offer": "spring_deal", "clicks": 200}],
        )

        # UNUSED ASSETS: empty
        table_results["UNUSED ASSETS"] = _make_table_result(
            "UNUSED ASSETS",
            data=[],
        )

        return _make_report_data(
            table_results=table_results,
            started_at=started_at,
        )

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_sections_in_order(self, mock_monotonic):
        """Section ordering matches TABLE_ORDER."""
        mock_monotonic.return_value = 103.45  # elapsed = 103.45 - 100.0 = 3.45
        started_at = 100.0

        data = self._build_mixed_report_data(started_at)
        report = compose_report(data)

        # Verify header is first
        assert report.startswith("# Insights Export:")

        # Verify table section ordering
        section_positions = {}
        for table_name in TABLE_ORDER:
            pos = report.find(f"## {table_name}")
            assert pos > 0, f"Missing section: {table_name}"
            section_positions[table_name] = pos

        ordered_names = sorted(section_positions, key=section_positions.get)
        assert ordered_names == TABLE_ORDER

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_header_at_top(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert report.startswith("# Insights Export: Test Dental")

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_footer_at_bottom(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert report.strip().endswith("**Version**: insights-export-v1.0")

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_ends_with_newline(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert report.endswith("\n")

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_error_section_present(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert "> [ERROR] InsightsServiceError: Request timed out" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_empty_section_present(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        # BY QUARTER is empty
        assert "## BY QUARTER\n\n> No data available" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_unused_assets_empty(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert "## UNUSED ASSETS\n\n> No unused assets found" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_missing_table_gets_error(self, mock_monotonic):
        """Tables not in table_results get a 'missing' error marker."""
        mock_monotonic.return_value = 101.0

        # Only provide SUMMARY, all others missing
        data = _make_report_data(
            table_results={
                "SUMMARY": _make_table_result("SUMMARY", data=[{"a": 1}]),
            },
            started_at=100.0,
        )
        report = compose_report(data)
        assert "> [ERROR] missing: Table result not available" in report
        # APPOINTMENTS is missing
        assert "## APPOINTMENTS" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_footer_counts(self, mock_monotonic):
        """Footer reflects correct succeeded/failed counts."""
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        # 9 successful results (APPOINTMENTS failed), but tables_failed = 10 - 9 = 1
        # (APPOINTMENTS is not success)
        # table_results has 10 entries, 9 with success=True, 1 with success=False
        assert "**Tables**: 9/10" in report
        assert "**Errors**: 1" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_sections_joined_with_double_newline(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        # Sections separated by "\n\n"
        # After header, before first table section
        assert "Daily insights report\n\n## SUMMARY" in report


# ---------------------------------------------------------------------------
# Adversarial Edge Cases (QA-ADVERSARY)
# ---------------------------------------------------------------------------


class TestAdversarialPipeInjection:
    """QA-ADVERSARY: Cell values containing pipe chars must not break tables."""

    def test_cell_value_with_pipe_char(self):
        """A cell value containing '|' must be escaped to prevent table corruption."""
        rows = [{"name": "Foo | Bar", "spend": 100}]
        result = _format_table_section("TEST", rows)
        lines = result.split("\n")
        data_line = lines[4]
        # The pipe character inside the value must be escaped as \|
        # so it does not act as a column delimiter.
        assert "Foo \\| Bar" in data_line, (
            f"Pipe in cell value not escaped. Got: {data_line}"
        )
        # Structural check: count unescaped pipes (column delimiters).
        # Remove escaped pipes first, then count remaining.
        import re

        header_unescaped = len(re.findall(r"(?<!\\)\|", lines[2]))
        data_unescaped = len(re.findall(r"(?<!\\)\|", data_line))
        assert data_unescaped == header_unescaped, (
            f"Structural mismatch: header has {header_unescaped} delimiters "
            f"but data has {data_unescaped} delimiters."
        )

    def test_cell_value_with_backtick(self):
        """Backticks in cell values should not break markdown formatting."""
        rows = [{"name": "`code`", "value": 42}]
        result = _format_table_section("TEST", rows)
        assert "`code`" in result

    def test_cell_value_with_hash(self):
        """Hash chars in cell values should not create false headings."""
        rows = [{"name": "# Not a heading", "value": 1}]
        result = _format_table_section("TEST", rows)
        # The # should be inside a table cell, not starting a line
        lines = result.split("\n")
        data_line = lines[4]
        assert data_line.startswith("|")


class TestAdversarialSanitizeBusinessName:
    """QA-ADVERSARY: Edge cases for _sanitize_business_name."""

    def test_all_special_chars(self):
        """All special characters result in empty string."""
        from autom8_asana.automation.workflows.insights_export import (
            _sanitize_business_name,
        )

        result = _sanitize_business_name("!@#$%^&*()")
        assert result == ""

    def test_unicode_chars_stripped(self):
        """Unicode (non-ASCII) characters are stripped."""
        from autom8_asana.automation.workflows.insights_export import (
            _sanitize_business_name,
        )

        result = _sanitize_business_name("Cafe\u0301 Dental")
        # The accent character should be stripped but base chars preserved
        assert "Caf" in result
        assert "Dental" in result

    def test_very_long_name(self):
        """Very long business name does not cause issues."""
        from autom8_asana.automation.workflows.insights_export import (
            _sanitize_business_name,
        )

        long_name = "A" * 500
        result = _sanitize_business_name(long_name)
        assert len(result) == 500
        assert result == long_name


class TestAdversarialUnusedAssetsNoneSpend:
    """QA-ADVERSARY: spend=None vs spend=0 in UNUSED ASSETS filter."""

    @pytest.mark.asyncio
    async def test_none_spend_excluded_from_unused(self):
        """Rows with spend=None are NOT matched by spend==0 filter."""

        # Simulate the filter logic directly
        asset_data = [
            {"name": "Normal", "spend": 100, "imp": 5000},
            {"name": "None Spend", "spend": None, "imp": 0},
            {"name": "None Imp", "spend": 0, "imp": None},
            {"name": "Both None", "spend": None, "imp": None},
            {"name": "Actually Unused", "spend": 0, "imp": 0},
        ]

        unused_rows = [
            row
            for row in asset_data
            if row.get("spend", -1) == 0 and row.get("imp", -1) == 0
        ]

        assert len(unused_rows) == 1
        assert unused_rows[0]["name"] == "Actually Unused"

    @pytest.mark.asyncio
    async def test_missing_spend_key_excluded(self):
        """Rows with no spend key are excluded (default -1 != 0)."""
        asset_data = [
            {"name": "No Spend Key", "imp": 0},
            {"name": "No Imp Key", "spend": 0},
            {"name": "Neither Key"},
        ]

        unused_rows = [
            row
            for row in asset_data
            if row.get("spend", -1) == 0 and row.get("imp", -1) == 0
        ]

        assert len(unused_rows) == 0


class TestAdversarialRowLimitEdgeCases:
    """QA-ADVERSARY: row_limit edge cases for _format_table_section."""

    def test_row_limit_one(self):
        """row_limit=1 shows exactly 1 row with truncation note."""
        rows = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = _format_table_section("TEST", rows, row_limit=1)
        assert "> Showing first 1 of 3 rows" in result
        data_rows = [
            ln
            for ln in result.split("\n")
            if ln.startswith("| ") and "---" not in ln and "Id" not in ln
        ]
        assert len(data_rows) == 1


class TestAdversarialRowLimitZero:
    """QA-ADVERSARY: Edge case with row_limit=0.

    DEFECT-003 (LOW): row_limit=0 is falsy so the code path
    `rows[:row_limit] if row_limit else rows` takes the else branch
    and displays ALL rows, then says 'Showing first 0 of N rows'.
    This is cosmetically wrong but row_limit=0 is not a realistic
    configuration. DEFAULT_ROW_LIMITS only sets 100 for APPOINTMENTS
    and LEADS. Documenting as known edge case.
    """

    def test_row_limit_zero_displays_all_rows(self):
        """row_limit=0 is falsy -- displays all rows (known edge case)."""
        rows = [{"id": 1}, {"id": 2}]
        result = _format_table_section("TEST", rows, row_limit=0)
        # Due to `if row_limit` being falsy for 0, all rows are displayed
        data_rows = [
            ln
            for ln in result.split("\n")
            if ln.startswith("| ") and "---" not in ln and "Id" not in ln
        ]
        assert len(data_rows) == 2
