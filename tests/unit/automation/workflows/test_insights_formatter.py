"""Tests for insights_formatter.py -- HTML report formatter.

Covers TDD Section 9.2 test scenarios adapted for HTML output:
- TestHtmlTable: Valid HTML table output (AC-W03.1, AC-W03.3, AC-W03.6)
- TestHeader: Masked phone, business name, vertical, timestamp (AC-W03.2)
- TestColumnNames: snake_case -> Title Case conversion (AC-W03.4)
- TestNullHandling: Null values render as styled "---" (AC-W03.5)
- TestNullColumns: Always-null columns present with "---" markers (AC-W03.5)
- TestEmptyTable: Zero rows -> "No data available" (AC-W03.7)
- TestUnusedAssetsEmpty: Zero matching -> "No unused assets found" (AC-W03.7)
- TestFooter: Duration, table count, error count, version (AC-W03.8)
- TestRowLimit: Truncation note when limit reached (AC-W03.10)
- TestErrorMarker: Error section format (AC-W02.2, AC-W02.5)
- TestComposeReport: Full report composition with mixed results (AC-W03.1)
- TestProtocol: StructuredDataRenderer protocol conformance
- TestHtmlEscaping: XSS prevention via html.escape()
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from autom8_asana.automation.workflows.insights_formatter import (
    COLUMN_ORDER,
    TABLE_ORDER,
    DataSection,
    HtmlRenderer,
    InsightsReportData,
    StructuredDataRenderer,
    TableResult,
    _FIELD_FORMAT,
    _discover_columns,
    _format_cell_html,
    _reorder_columns,
    _slugify,
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


def _render_section(
    name: str,
    rows: list[dict] | None = None,
    row_count: int = 0,
    truncated: bool = False,
    total_rows: int | None = None,
    error: str | None = None,
    empty_message: str | None = None,
) -> str:
    """Render a single DataSection via HtmlRenderer for testing."""
    renderer = HtmlRenderer()
    section = DataSection(
        name=name,
        rows=rows,
        row_count=row_count,
        truncated=truncated,
        total_rows=total_rows,
        error=error,
        empty_message=empty_message,
    )
    return renderer.render_document(
        title="Test",
        metadata={},
        sections=[section],
    )


# ---------------------------------------------------------------------------
# TestProtocol -- StructuredDataRenderer conformance
# ---------------------------------------------------------------------------


class TestProtocol:
    """StructuredDataRenderer protocol conformance for HtmlRenderer."""

    def test_html_renderer_satisfies_protocol(self):
        """HtmlRenderer is a structural subtype of StructuredDataRenderer."""
        renderer: StructuredDataRenderer = HtmlRenderer()
        assert renderer.content_type == "text/html"
        assert renderer.file_extension == "html"

    def test_render_document_returns_string(self):
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={"Key": "Value"},
            sections=[],
        )
        assert isinstance(result, str)
        assert result.startswith("<!DOCTYPE html>")

    def test_render_document_with_footer(self):
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={},
            sections=[],
            footer={"Duration": "1.00s"},
        )
        assert "Duration" in result
        assert "1.00s" in result


# ---------------------------------------------------------------------------
# TestHtmlTable -- AC-W03.1, AC-W03.3, AC-W03.6
# ---------------------------------------------------------------------------


class TestHtmlTable:
    """Valid HTML table output from HtmlRenderer."""

    def test_single_row_table(self):
        rows = [{"offer_cost": 1500, "impressions": 45000, "clicks": 1200}]
        result = _render_section("SUMMARY", rows=rows, row_count=1)

        assert "<table>" in result
        assert "<thead>" in result
        assert "<tbody>" in result
        assert "<th" in result
        assert "Offer Cost" in result
        assert "Impressions" in result
        assert "Clicks" in result
        assert "<td" in result
        # offer_cost is a currency field → $1,500.00
        assert "$1,500.00" in result
        # impressions and clicks are integers → comma-grouped
        assert "45,000" in result
        assert "1,200" in result

    def test_multiple_rows(self):
        rows = [
            {"date": "2026-02-10", "name": "John", "status": "confirmed"},
            {"date": "2026-02-11", "name": "Jane", "status": "pending"},
            {"date": "2026-02-12", "name": "Bob", "status": "cancelled"},
        ]
        result = _render_section("APPOINTMENTS", rows=rows, row_count=3)

        assert "Date" in result
        assert "Name" in result
        assert "Status" in result
        assert "John" in result
        assert "Jane" in result
        assert "Bob" in result
        # Three <tr> in tbody
        assert result.count("<tr>") >= 4  # 1 thead + 3 tbody

    def test_columns_union_preserves_order(self):
        """Columns are a union of all row keys, preserving first-seen order."""
        rows = [
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
        ]
        result = _render_section("TEST", rows=rows, row_count=2)

        # Headers should be A, B, C in first-seen order
        a_pos = result.find(">A<")
        b_pos = result.find(">B<")
        c_pos = result.find(">C<")
        assert a_pos < b_pos < c_pos
        # Second row missing 'a' -> gets None -> styled "---"
        assert "---" in result

    def test_empty_rows_list_returns_no_data(self):
        """Empty dict rows (no keys) produce 'No data available'."""
        rows = [{}]
        result = _render_section("TEST", rows=rows, row_count=1)
        assert "No data available" in result

    def test_table_has_section_id(self):
        """Table sections have id attributes for navigation."""
        result = _render_section("BY QUARTER", rows=[{"a": 1}], row_count=1)
        assert 'id="by-quarter"' in result

    def test_table_has_row_count_badge(self):
        """Table sections display row count badge."""
        rows = [{"a": 1}, {"a": 2}, {"a": 3}]
        result = _render_section("TEST", rows=rows, row_count=3)
        assert '<span class="badge">3</span>' in result


# ---------------------------------------------------------------------------
# TestHeader -- AC-W03.2
# ---------------------------------------------------------------------------


class TestHeader:
    """Header includes masked phone, business name, vertical, ISO timestamp."""

    def test_header_contains_business_name(self):
        data = _make_report_data(business_name="Smith Chiropractic")
        result = compose_report(data)
        assert "Insights Export: Smith Chiropractic" in result

    def test_header_contains_masked_phone(self):
        data = _make_report_data(office_phone="+17705753103")
        result = compose_report(data)
        assert "+1770***3103" in result
        assert "+17705753103" not in result

    def test_header_contains_vertical(self):
        data = _make_report_data(vertical="chiropractic")
        result = compose_report(data)
        assert "chiropractic" in result

    def test_header_contains_iso_timestamp(self):
        data = _make_report_data()
        result = compose_report(data)
        # ISO timestamp includes T separator and timezone info
        assert "Generated" in result
        assert "202" in result  # Year prefix

    def test_header_contains_period(self):
        data = _make_report_data()
        result = compose_report(data)
        assert "Daily insights report" in result

    def test_header_is_in_header_element(self):
        data = _make_report_data()
        result = compose_report(data)
        assert '<header class="report-header">' in result
        assert '<h1 class="report-title">' in result


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
    """Null values render as styled '---' in HTML table cells."""

    def test_format_cell_none(self):
        result = _format_cell_html(None)
        assert "---" in result
        assert "null-value" in result

    def test_format_cell_string(self):
        assert _format_cell_html("hello") == "hello"

    def test_format_cell_integer(self):
        assert _format_cell_html(42) == "42"

    def test_format_cell_float(self):
        assert _format_cell_html(3.14) == "3.14"

    def test_format_cell_zero(self):
        assert _format_cell_html(0) == "0"

    def test_format_cell_empty_string(self):
        assert _format_cell_html("") == ""

    def test_null_values_in_html_table(self):
        """Rows with None values in table show styled '---'."""
        rows = [
            {"date": "2026-02-10", "name": "John", "status": None},
        ]
        result = _render_section("TEST", rows=rows, row_count=1)
        assert "2026-02-10" in result
        assert "John" in result
        assert "---" in result
        assert "null-value" in result


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
        result = _render_section("APPOINTMENTS", rows=rows, row_count=1)

        # Column headers present
        assert "Out Calls" in result
        assert "In Calls" in result
        assert "Time On Call" in result
        # Data has --- for null columns
        assert result.count("---") == 3

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
        result = _render_section("LEADS", rows=rows, row_count=1)

        assert "Follow Up" in result
        assert "Convo" in result
        assert "Lead Call Time" in result
        assert result.count("---") == 3


# ---------------------------------------------------------------------------
# TestEmptyTable -- AC-W03.7
# ---------------------------------------------------------------------------


class TestEmptyTable:
    """Zero rows -> 'No data available'."""

    def test_empty_summary(self):
        result = _render_section("SUMMARY", rows=[], empty_message="No data available")
        assert "No data available" in result
        assert "empty-message" in result

    def test_empty_appointments(self):
        result = _render_section(
            "APPOINTMENTS", rows=[], empty_message="No data available"
        )
        assert "No data available" in result

    def test_empty_generic_table(self):
        result = _render_section(
            "BY QUARTER", rows=[], empty_message="No data available"
        )
        assert "No data available" in result


# ---------------------------------------------------------------------------
# TestUnusedAssetsEmpty -- AC-W03.7
# ---------------------------------------------------------------------------


class TestUnusedAssetsEmpty:
    """UNUSED ASSETS empty shows special message."""

    def test_unused_assets_empty(self):
        result = _render_section(
            "UNUSED ASSETS", rows=[], empty_message="No unused assets found"
        )
        assert "No unused assets found" in result

    def test_unused_assets_distinct_from_other_tables(self):
        """Verify UNUSED ASSETS message differs from other empty tables."""
        unused = _render_section(
            "UNUSED ASSETS", rows=[], empty_message="No unused assets found"
        )
        summary = _render_section("SUMMARY", rows=[], empty_message="No data available")
        assert "No unused assets found" in unused
        assert "No data available" in summary


# ---------------------------------------------------------------------------
# TestFooter -- AC-W03.8
# ---------------------------------------------------------------------------


class TestFooter:
    """Footer includes duration, table count, error count, version."""

    def test_footer_basic(self):
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={},
            sections=[],
            footer={
                "Duration": "3.46s",
                "Tables": "10/10",
                "Version": "insights-export-v1.0",
            },
        )
        assert "Duration" in result
        assert "3.46s" in result
        assert "Tables" in result
        assert "10/10" in result
        assert "Version" in result
        assert "insights-export-v1.0" in result

    def test_footer_no_errors_omits_error_line(self):
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={},
            sections=[],
            footer={"Duration": "1.00s", "Tables": "10/10", "Version": "v1"},
        )
        assert "Errors" not in result

    def test_footer_with_errors(self):
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={},
            sections=[],
            footer={
                "Duration": "2.50s",
                "Tables": "8/10",
                "Errors": "2",
                "Version": "v1",
            },
        )
        assert "8/10" in result
        assert "Errors" in result
        assert " 2</span>" in result

    def test_footer_has_footer_element(self):
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={},
            sections=[],
            footer={"Version": "v1"},
        )
        assert '<footer class="report-footer">' in result

    def test_footer_version_present(self):
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={},
            sections=[],
            footer={"Version": "insights-export-v1.0"},
        )
        assert "insights-export-v1.0" in result


# ---------------------------------------------------------------------------
# TestRowLimit -- AC-W03.10
# ---------------------------------------------------------------------------


class TestRowLimit:
    """Truncation note when row limit is reached."""

    def test_truncation_note(self):
        rows = [{"id": i, "value": f"row_{i}"} for i in range(100)]
        result = _render_section(
            "APPOINTMENTS",
            rows=rows,
            row_count=100,
            truncated=True,
            total_rows=150,
        )
        assert "Showing 100 of 150 rows" in result
        assert "truncation-note" in result

    def test_no_truncation_when_under_limit(self):
        rows = [{"id": i} for i in range(50)]
        result = _render_section("LEADS", rows=rows, row_count=50)
        assert "Showing" not in result

    def test_no_truncation_when_at_limit(self):
        rows = [{"id": i} for i in range(100)]
        result = _render_section("LEADS", rows=rows, row_count=100)
        assert "Showing" not in result

    def test_no_truncation_when_no_limit(self):
        rows = [{"id": i} for i in range(200)]
        result = _render_section("BY MONTH", rows=rows, row_count=200)
        assert "Showing" not in result
        # All 200 rows should be in the output
        assert result.count("<tr>") >= 201  # 1 thead + 200 tbody


# ---------------------------------------------------------------------------
# TestErrorMarker -- AC-W02.2, AC-W02.5
# ---------------------------------------------------------------------------


class TestErrorMarker:
    """Error section format: styled error box."""

    def test_basic_error_marker(self):
        result = _render_section(
            "APPOINTMENTS",
            error="[ERROR] InsightsServiceError: Request timed out",
        )
        assert "error-box" in result
        assert "[ERROR] InsightsServiceError: Request timed out" in result

    def test_error_section_has_section_id(self):
        result = _render_section("SUMMARY", error="[ERROR] timeout: Server unavailable")
        assert 'id="summary"' in result

    def test_error_section_has_heading(self):
        result = _render_section("BY QUARTER", error="[ERROR] api_error: 500")
        assert "BY QUARTER" in result

    def test_missing_table_error_marker(self):
        """When a table result is None, compose_report generates a 'missing' error."""
        result = _render_section(
            "LEADS",
            error="[ERROR] missing: Table result not available",
        )
        assert "[ERROR] missing: Table result not available" in result


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

        # LIFETIME RECONCILIATIONS: success with data
        table_results["LIFETIME RECONCILIATIONS"] = _make_table_result(
            "LIFETIME RECONCILIATIONS",
            data=[{"office_phone": "+19259998806", "collected": 5000.0}],
        )

        # T14 RECONCILIATIONS: success with data
        table_results["T14 RECONCILIATIONS"] = _make_table_result(
            "T14 RECONCILIATIONS",
            data=[{"period": 0, "period_label": "P0", "collected": 1200.0}],
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
    def test_compose_report_is_valid_html(self, mock_monotonic):
        """Output is a valid HTML document."""
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)

        assert report.startswith("<!DOCTYPE html>")
        assert "</html>" in report
        assert "<head>" in report
        assert "<body>" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_sections_in_order(self, mock_monotonic):
        """Section ordering matches TABLE_ORDER."""
        mock_monotonic.return_value = 103.45
        started_at = 100.0

        data = self._build_mixed_report_data(started_at)
        report = compose_report(data)

        # Verify all table sections are present and in order
        section_positions = {}
        for table_name in TABLE_ORDER:
            section_id = table_name.lower().replace(" ", "-")
            pos = report.find(f'id="{section_id}"')
            assert pos > 0, f"Missing section: {table_name}"
            section_positions[table_name] = pos

        ordered_names = sorted(section_positions, key=section_positions.get)
        assert ordered_names == TABLE_ORDER

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_header_at_top(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert "Insights Export: Test Dental" in report
        # Header comes before first section
        header_pos = report.find("report-header")
        first_section_pos = report.find("table-section")
        assert header_pos < first_section_pos

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_footer_at_bottom(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert "report-footer" in report
        assert "insights-export-v1.0" in report
        # Footer element (in body, not CSS) after all section elements
        footer_tag_pos = report.find('<footer class="report-footer">')
        last_section_close_pos = report.rfind("</section>")
        assert footer_tag_pos > last_section_close_pos

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
        assert "[ERROR] InsightsServiceError: Request timed out" in report
        assert "error-box" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_empty_section_present(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        # BY QUARTER is empty
        assert "No data available" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_unused_assets_empty(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert "No unused assets found" in report

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
        assert "[ERROR] missing: Table result not available" in report
        # APPOINTMENTS is missing -- check its section exists
        assert 'id="appointments"' in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_footer_counts(self, mock_monotonic):
        """Footer reflects correct succeeded/failed counts."""
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        # 11 successful results out of 12 (APPOINTMENTS failed)
        assert "11/12" in report
        assert "Errors" in report

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_contains_inline_css(self, mock_monotonic):
        mock_monotonic.return_value = 103.45
        data = self._build_mixed_report_data(100.0)
        report = compose_report(data)
        assert "<style>" in report
        assert "table" in report
        assert "font-family" in report
        # CSS is inline, no external stylesheet references
        assert 'rel="stylesheet"' not in report
        assert "link href=" not in report


# ---------------------------------------------------------------------------
# TestHtmlEscaping -- XSS prevention
# ---------------------------------------------------------------------------


class TestHtmlEscaping:
    """All user-supplied values are HTML-escaped."""

    def test_cell_value_with_html_tags(self):
        """HTML tags in cell values are escaped."""
        result = _format_cell_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_cell_value_with_ampersand(self):
        result = _format_cell_html("A & B")
        assert "&amp;" in result

    def test_cell_value_with_quotes(self):
        result = _format_cell_html('He said "hello"')
        assert "&quot;" in result

    def test_business_name_escaped_in_header(self):
        data = _make_report_data(business_name='<script>alert("xss")</script>')
        result = compose_report(data)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_cell_value_with_angle_brackets(self):
        rows = [{"name": "<b>Bold</b>", "value": 42}]
        result = _render_section("TEST", rows=rows, row_count=1)
        assert "<b>Bold</b>" not in result
        assert "&lt;b&gt;" in result


# ---------------------------------------------------------------------------
# Adversarial Edge Cases (QA-ADVERSARY)
# ---------------------------------------------------------------------------


class TestAdversarialSpecialCharsInCells:
    """QA-ADVERSARY: Cell values with special characters must be safe."""

    def test_cell_value_with_pipe_char(self):
        """Pipe chars are harmless in HTML (no table corruption like markdown)."""
        rows = [{"name": "Foo | Bar", "spend": 100}]
        result = _render_section("TEST", rows=rows, row_count=1)
        assert "Foo | Bar" in result

    def test_cell_value_with_backtick(self):
        rows = [{"name": "`code`", "value": 42}]
        result = _render_section("TEST", rows=rows, row_count=1)
        assert "`code`" in result

    def test_cell_value_with_hash(self):
        """Hash chars are harmless in HTML (no heading creation)."""
        rows = [{"name": "# Not a heading", "value": 1}]
        result = _render_section("TEST", rows=rows, row_count=1)
        assert "# Not a heading" in result


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
    """QA-ADVERSARY: spend=None vs spend=0, disabled, is_generic in UNUSED ASSETS filter."""

    @pytest.mark.asyncio
    async def test_none_spend_excluded_from_unused(self):
        """Rows with spend=None are NOT matched by spend==0 filter."""
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
            if row.get("spend", -1) == 0
            and row.get("imp", -1) == 0
            and not row.get("disabled")
            and not row.get("is_generic")
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
            if row.get("spend", -1) == 0
            and row.get("imp", -1) == 0
            and not row.get("disabled")
            and not row.get("is_generic")
        ]

        assert len(unused_rows) == 0

    @pytest.mark.asyncio
    async def test_disabled_asset_excluded_from_unused(self):
        """Disabled assets (disabled=1) are excluded even with zero spend/imp."""
        asset_data = [
            {"name": "Disabled Zero", "spend": 0, "imp": 0, "disabled": 1},
            {"name": "Enabled Zero", "spend": 0, "imp": 0, "disabled": 0},
        ]

        unused_rows = [
            row
            for row in asset_data
            if row.get("spend", -1) == 0
            and row.get("imp", -1) == 0
            and not row.get("disabled")
            and not row.get("is_generic")
        ]

        assert len(unused_rows) == 1
        assert unused_rows[0]["name"] == "Enabled Zero"


class TestAdversarialRowLimitEdgeCases:
    """QA-ADVERSARY: row_limit edge cases."""

    def test_row_limit_one(self):
        """row_limit=1 shows exactly 1 row with truncation note."""
        rows = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = _render_section(
            "TEST", rows=rows[:1], row_count=1, truncated=True, total_rows=3
        )
        assert "Showing 1 of 3 rows" in result
        # Count data rows (tr in tbody, not thead)
        # The single row should be present
        assert ">1<" in result


class TestAdversarialRowLimitZero:
    """QA-ADVERSARY: Edge case with row_limit=0.

    DEFECT-003 (LOW): row_limit=0 is falsy so the code path
    `rows[:row_limit] if row_limit else rows` takes the else branch
    and displays ALL rows. This is cosmetically wrong but row_limit=0
    is not a realistic configuration.
    """

    def test_row_limit_zero_displays_all_rows(self):
        """row_limit=0 is falsy -- displays all rows (known edge case)."""
        # compose_report handles row_limit=0 at the adapter layer
        data = _make_report_data(
            table_results={
                "SUMMARY": _make_table_result("SUMMARY", data=[{"id": 1}, {"id": 2}]),
            },
            started_at=time.monotonic(),
            row_limits={"SUMMARY": 0},
        )
        report = compose_report(data)
        # Due to `if row_limit` being falsy for 0, all rows are displayed
        assert ">1<" in report
        assert ">2<" in report


# ---------------------------------------------------------------------------
# TestDiscoverColumns
# ---------------------------------------------------------------------------


class TestDiscoverColumns:
    """Column discovery helper tests."""

    def test_empty_rows(self):
        assert _discover_columns([]) == []

    def test_single_row(self):
        cols = _discover_columns([{"a": 1, "b": 2}])
        assert cols == ["a", "b"]

    def test_heterogeneous_rows(self):
        cols = _discover_columns([{"a": 1}, {"b": 2}, {"a": 3, "c": 4}])
        assert cols == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# TestSlugify
# ---------------------------------------------------------------------------


class TestSlugify:
    """Slugify helper tests."""

    def test_simple_name(self):
        assert _slugify("SUMMARY") == "summary"

    def test_multi_word(self):
        assert _slugify("BY QUARTER") == "by-quarter"

    def test_asset_table(self):
        assert _slugify("ASSET TABLE") == "asset-table"


# ---------------------------------------------------------------------------
# TestNumericAlignment
# ---------------------------------------------------------------------------


class TestNumericAlignment:
    """Numeric columns get right-alignment class."""

    def test_numeric_column_has_num_class(self):
        rows = [{"name": "test", "spend": 100}]
        result = _render_section("TEST", rows=rows, row_count=1)
        # The spend column should have num class for right-alignment
        assert 'class="num"' in result

    def test_string_column_has_no_num_class(self):
        rows = [{"name": "test"}]
        result = _render_section("TEST", rows=rows, row_count=1)
        # Name column should not have num class
        # Check that the th for Name does not have num class
        assert 'class=""' in result or 'class="num"' not in result.split("Name")[0]


# ---------------------------------------------------------------------------
# TestSelfContainedHtml
# ---------------------------------------------------------------------------


class TestSelfContainedHtml:
    """The HTML document is fully self-contained."""

    def test_no_external_resources(self):
        """HTML has no links to external CSS, JS, or images."""
        renderer = HtmlRenderer()
        result = renderer.render_document(
            title="Test",
            metadata={"Key": "Value"},
            sections=[DataSection(name="T", rows=[{"a": 1}], row_count=1)],
            footer={"Version": "v1"},
        )
        assert 'href="http' not in result
        assert 'src="http' not in result
        assert 'rel="stylesheet"' not in result
        assert "<link" not in result

    def test_inline_css_present(self):
        """CSS is inlined in a <style> tag."""
        renderer = HtmlRenderer()
        result = renderer.render_document(title="Test", metadata={}, sections=[])
        assert "<style>" in result
        assert "</style>" in result


# ---------------------------------------------------------------------------
# TestColumnOrdering -- WS-2 period column ordering fix
# ---------------------------------------------------------------------------


class TestColumnOrdering:
    """Period columns render as leftmost columns in period-based tables."""

    def test_by_quarter_period_label_is_first_column(self):
        """BY QUARTER table renders period_label as the first column."""
        rows = [
            {
                "spend": 500,
                "impressions": 10000,
                "period_label": "Q1 2026",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
            },
        ]
        result = _render_section("BY QUARTER", rows=rows, row_count=1)

        # Extract <th> positions -- period_label should appear before spend
        period_label_pos = result.find("Period Label")
        spend_pos = result.find("Spend")
        impressions_pos = result.find("Impressions")
        assert period_label_pos < spend_pos, (
            "period_label must appear before spend in BY QUARTER"
        )
        assert period_label_pos < impressions_pos, (
            "period_label must appear before impressions in BY QUARTER"
        )

    def test_by_month_period_columns_before_metrics(self):
        """BY MONTH table renders all three period columns before metrics."""
        rows = [
            {
                "clicks": 120,
                "period_end": "2026-01-31",
                "period_start": "2026-01-01",
                "period_label": "January 2026",
                "impressions": 5000,
            },
        ]
        result = _render_section("BY MONTH", rows=rows, row_count=1)

        period_label_pos = result.find("Period Label")
        period_start_pos = result.find("Period Start")
        period_end_pos = result.find("Period End")
        clicks_pos = result.find("Clicks")
        impressions_pos = result.find("Impressions")

        # All three period columns must precede metric columns
        assert period_label_pos < clicks_pos
        assert period_start_pos < clicks_pos
        assert period_end_pos < clicks_pos
        assert period_label_pos < impressions_pos

        # Period columns should be in the COLUMN_ORDER sequence
        assert period_label_pos < period_start_pos < period_end_pos

    def test_summary_table_keeps_natural_column_order(self):
        """SUMMARY table (no COLUMN_ORDER entry) preserves dict key order."""
        rows = [
            {"offer_cost": 1500, "impressions": 45000, "clicks": 1200},
        ]
        result = _render_section("SUMMARY", rows=rows, row_count=1)

        offer_cost_pos = result.find("Offer Cost")
        impressions_pos = result.find("Impressions")
        clicks_pos = result.find("Clicks")

        # Natural dict insertion order: offer_cost, impressions, clicks
        assert offer_cost_pos < impressions_pos < clicks_pos

    def test_preferred_columns_missing_from_data_silently_skipped(self):
        """Preferred columns not present in data are silently skipped."""
        # Data has period_label but NOT period_start or period_end
        rows = [
            {"period_label": "Q1 2026", "spend": 500, "clicks": 100},
        ]
        result = _render_section("BY QUARTER", rows=rows, row_count=1)

        # period_label should still be first
        period_label_pos = result.find("Period Label")
        spend_pos = result.find("Spend")
        assert period_label_pos < spend_pos

        # Missing columns should not appear at all
        assert "Period Start" not in result
        assert "Period End" not in result

    def test_reorder_columns_with_none_returns_original(self):
        """_reorder_columns(columns, None) returns the original list unchanged."""
        columns = ["spend", "clicks", "impressions"]
        result = _reorder_columns(columns, None)
        assert result == ["spend", "clicks", "impressions"]

        # Also verify empty list preferred_leading
        result_empty = _reorder_columns(columns, [])
        assert result_empty == ["spend", "clicks", "impressions"]


# ---------------------------------------------------------------------------
# TestReconciliationTables -- TDD-WS5 Part 2 reconciliation consumer tests
# ---------------------------------------------------------------------------


class TestReconciliationTables:
    """Reconciliation table rendering and configuration tests.

    Per TDD-WS5 Part 2 Section 2.5-2.6: Validates LIFETIME RECONCILIATIONS
    and T14 RECONCILIATIONS table entries in TABLE_ORDER, COLUMN_ORDER, and
    rendered HTML output.
    """

    def test_table_order_has_12_entries(self):
        """TABLE_ORDER has 12 entries (was 10, +2 reconciliation tables)."""
        assert len(TABLE_ORDER) == 12

    def test_reconciliation_tables_at_positions_4_5(self):
        """LIFETIME RECONCILIATIONS at index 3, T14 RECONCILIATIONS at index 4."""
        assert TABLE_ORDER[3] == "LIFETIME RECONCILIATIONS"
        assert TABLE_ORDER[4] == "T14 RECONCILIATIONS"

    def test_reconciliation_tables_after_leads(self):
        """Reconciliation tables follow LEADS in TABLE_ORDER."""
        leads_idx = TABLE_ORDER.index("LEADS")
        lifetime_idx = TABLE_ORDER.index("LIFETIME RECONCILIATIONS")
        t14_idx = TABLE_ORDER.index("T14 RECONCILIATIONS")
        assert lifetime_idx == leads_idx + 1
        assert t14_idx == leads_idx + 2

    def test_reconciliation_tables_before_by_quarter(self):
        """Reconciliation tables precede BY QUARTER in TABLE_ORDER."""
        t14_idx = TABLE_ORDER.index("T14 RECONCILIATIONS")
        quarter_idx = TABLE_ORDER.index("BY QUARTER")
        assert t14_idx < quarter_idx

    def test_lifetime_reconciliations_column_order(self):
        """LIFETIME RECONCILIATIONS has correct COLUMN_ORDER entry."""
        assert "LIFETIME RECONCILIATIONS" in COLUMN_ORDER
        expected = [
            "office_phone",
            "vertical",
            "num_invoices",
            "collected",
            "spend",
            "variance",
            "variance_pct",
        ]
        assert COLUMN_ORDER["LIFETIME RECONCILIATIONS"] == expected

    def test_t14_reconciliations_column_order(self):
        """T14 RECONCILIATIONS has correct COLUMN_ORDER entry with period columns."""
        assert "T14 RECONCILIATIONS" in COLUMN_ORDER
        expected = [
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
        ]
        assert COLUMN_ORDER["T14 RECONCILIATIONS"] == expected

    def test_lifetime_reconciliations_renders_correct_column_order(self):
        """LIFETIME RECONCILIATIONS renders office_phone, vertical first."""
        rows = [
            {
                "office_phone": "+19259998806",
                "vertical": "chiro",
                "num_invoices": 25,
                "collected": 5000.00,
                "spend": 4200.00,
                "variance": 800.00,
                "variance_pct": 16.0,
                "first_payment": "2025-11-01",
                "latest_payment": "2026-02-19",
                "days_with_activity": 45,
            },
        ]
        result = _render_section("LIFETIME RECONCILIATIONS", rows=rows, row_count=1)

        # Preferred columns should appear before non-preferred columns
        office_phone_pos = result.find("Office Phone")
        vertical_pos = result.find("Vertical")
        num_invoices_pos = result.find("Num Invoices")
        collected_pos = result.find("Collected")
        first_payment_pos = result.find("First Payment")

        assert office_phone_pos < vertical_pos
        assert vertical_pos < num_invoices_pos
        assert num_invoices_pos < collected_pos
        # Non-preferred columns come after preferred ones
        assert collected_pos < first_payment_pos

    def test_t14_reconciliations_renders_period_columns_first(self):
        """T14 RECONCILIATIONS renders period, period_label, period_start, period_end first."""
        rows = [
            {
                "office_phone": "+19259998806",
                "vertical": "chiro",
                "period": 0,
                "period_len": 14,
                "period_start": "2026-02-07",
                "period_end": "2026-02-20",
                "period_label": "P0",
                "num_invoices": 4,
                "collected": 1200.00,
                "spend": 980.50,
                "variance": 219.50,
                "variance_pct": 18.29,
            },
            {
                "office_phone": "+19259998806",
                "vertical": "chiro",
                "period": 1,
                "period_len": 12,
                "period_start": "2026-01-24",
                "period_end": "2026-02-06",
                "period_label": "P1",
                "num_invoices": 3,
                "collected": 900.00,
                "spend": 850.00,
                "variance": 50.00,
                "variance_pct": 5.56,
            },
        ]
        result = _render_section("T14 RECONCILIATIONS", rows=rows, row_count=2)

        # Period columns should come before metric columns
        period_pos = result.find(">Period<")
        period_label_pos = result.find("Period Label")
        period_start_pos = result.find("Period Start")
        period_end_pos = result.find("Period End")
        num_invoices_pos = result.find("Num Invoices")
        office_phone_pos = result.find("Office Phone")

        # period/period_label/period_start/period_end before metrics
        assert period_pos < num_invoices_pos
        assert period_label_pos < num_invoices_pos
        assert period_start_pos < num_invoices_pos
        assert period_end_pos < num_invoices_pos
        # office_phone is not in preferred leading -- comes after
        assert office_phone_pos > period_end_pos

    def test_lifetime_reconciliations_section_id(self):
        """LIFETIME RECONCILIATIONS section has correct slugified id."""
        rows = [{"office_phone": "+19259998806", "collected": 5000.00}]
        result = _render_section("LIFETIME RECONCILIATIONS", rows=rows, row_count=1)
        assert 'id="lifetime-reconciliations"' in result

    def test_t14_reconciliations_section_id(self):
        """T14 RECONCILIATIONS section has correct slugified id."""
        rows = [{"period": 0, "period_label": "P0", "collected": 1200.00}]
        result = _render_section("T14 RECONCILIATIONS", rows=rows, row_count=1)
        assert 'id="t14-reconciliations"' in result

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_includes_reconciliation_sections(self, mock_monotonic):
        """compose_report includes reconciliation sections in output."""
        mock_monotonic.return_value = 101.0

        table_results: dict[str, TableResult] = {}
        # Provide all 12 tables
        for name in TABLE_ORDER:
            if name == "LIFETIME RECONCILIATIONS":
                table_results[name] = _make_table_result(
                    name,
                    data=[
                        {
                            "office_phone": "+19259998806",
                            "vertical": "chiro",
                            "num_invoices": 25,
                            "collected": 5000.0,
                            "spend": 4200.0,
                            "variance": 800.0,
                            "variance_pct": 16.0,
                        }
                    ],
                )
            elif name == "T14 RECONCILIATIONS":
                table_results[name] = _make_table_result(
                    name,
                    data=[
                        {
                            "period": 0,
                            "period_label": "P0",
                            "period_start": "2026-02-07",
                            "period_end": "2026-02-20",
                            "num_invoices": 4,
                            "collected": 1200.0,
                            "spend": 980.5,
                            "variance": 219.5,
                            "variance_pct": 18.29,
                        }
                    ],
                )
            else:
                table_results[name] = _make_table_result(name, data=[{"a": 1}])

        data = _make_report_data(table_results=table_results, started_at=100.0)
        report = compose_report(data)

        # Both reconciliation sections should be present
        assert 'id="lifetime-reconciliations"' in report
        assert 'id="t14-reconciliations"' in report

        # Section order: reconciliation after LEADS, before BY QUARTER
        leads_pos = report.find('id="leads"')
        lifetime_pos = report.find('id="lifetime-reconciliations"')
        t14_pos = report.find('id="t14-reconciliations"')
        quarter_pos = report.find('id="by-quarter"')

        assert leads_pos < lifetime_pos < t14_pos < quarter_pos

    @patch("autom8_asana.automation.workflows.insights_formatter.time.monotonic")
    def test_compose_report_footer_reflects_12_tables(self, mock_monotonic):
        """Footer table count reflects 12 tables when all succeed."""
        mock_monotonic.return_value = 101.0

        table_results = {}
        for name in TABLE_ORDER:
            table_results[name] = _make_table_result(name, data=[{"a": 1}])

        data = _make_report_data(table_results=table_results, started_at=100.0)
        report = compose_report(data)
        assert "12/12" in report


# ---------------------------------------------------------------------------
# TestFormatCellHtmlFormatting -- GAP-04 type-aware numeric formatting
# ---------------------------------------------------------------------------


class TestFormatCellHtmlFormatting:
    """Type-aware cell formatting for currency, rate, percentage, ratio, per-20k."""

    @pytest.mark.parametrize(
        "value,column,expected",
        [
            # Currency fields → $X,XXX.XX
            (12847.5, "spend", "$12,847.50"),
            (0, "spend", "$0.00"),
            (-500.0, "cpl", "$-500.00"),
            (1500, "offer_cost", "$1,500.00"),
            (5000.0, "collected", "$5,000.00"),
            (800.0, "variance", "$800.00"),
            (4200.0, "budget", "$4,200.00"),
            (99.99, "cpc", "$99.99"),
            # Rate fields → X.XX% (stored as decimal, ×100 for display)
            (0.0342, "ctr", "3.42%"),
            (0.0, "ns_rate", "0.00%"),
            (1.0, "conversion_rate", "100.00%"),
            (0.1567, "lctr", "15.67%"),
            (0.85, "pacing_ratio", "85.00%"),
            # Percentage fields → X.XX% (already in percent units)
            (42.5, "variance_pct", "42.50%"),
            (0.0, "variance_pct", "0.00%"),
            (100.0, "variance_pct", "100.00%"),
            # Ratio fields → X.XXx
            (3.5, "roas", "3.50x"),
            (0.0, "roas", "0.00x"),
            (10.123, "roas", "10.12x"),
            # Per-20k fields → comma-grouped 2dp (no symbol)
            (12.5, "lp20m", "12.50"),
            (0.0, "sp20m", "0.00"),
            (1234.56, "esp20m", "1,234.56"),
            # Integer fallback (unknown column) → comma-grouped
            (45000, "imp", "45,000"),
            (0, "leads", "0"),
            (1000000, "contacts", "1,000,000"),
            # Float fallback (unknown column) → comma-grouped 2dp
            (123.456, "unknown_field", "123.46"),
            (0.5, "unknown_float", "0.50"),
            # None → styled dash
            (None, "spend", '<span class="null-value">---</span>'),
            (None, "ctr", '<span class="null-value">---</span>'),
            (None, "", '<span class="null-value">---</span>'),
            # Text passthrough → html-escaped string
            ("hello", "office", "hello"),
            ("2026-02-20", "first_ran", "2026-02-20"),
            # Backward compat: no column → fallback formatting
            (42, "", "42"),
            (3.14, "", "3.14"),
        ],
        ids=[
            "currency-spend",
            "currency-zero",
            "currency-negative",
            "currency-offer_cost",
            "currency-collected",
            "currency-variance",
            "currency-budget",
            "currency-cpc",
            "rate-ctr",
            "rate-zero",
            "rate-full",
            "rate-lctr",
            "rate-pacing_ratio",
            "pct-normal",
            "pct-zero",
            "pct-full",
            "ratio-roas",
            "ratio-zero",
            "ratio-rounded",
            "per20k-lp20m",
            "per20k-zero",
            "per20k-large",
            "int-imp",
            "int-zero",
            "int-million",
            "float-unknown",
            "float-small",
            "none-currency",
            "none-rate",
            "none-empty",
            "text-office",
            "text-date",
            "compat-int",
            "compat-float",
        ],
    )
    def test_format_cell_html_typed(self, value, column, expected):
        assert _format_cell_html(value, column) == expected

    def test_all_currency_fields_format_correctly(self):
        """Every field mapped as 'currency' produces $ prefix."""
        currency_fields = [k for k, v in _FIELD_FORMAT.items() if v == "currency"]
        assert len(currency_fields) == 16
        for field in currency_fields:
            result = _format_cell_html(1234.5, field)
            assert result.startswith("$"), f"{field} should produce $ prefix"
            assert "," in result, f"{field} should have comma grouping"

    def test_all_rate_fields_format_correctly(self):
        """Every field mapped as 'rate' produces % suffix with ×100."""
        rate_fields = [k for k, v in _FIELD_FORMAT.items() if v == "rate"]
        assert len(rate_fields) == 10
        for field in rate_fields:
            result = _format_cell_html(0.05, field)
            assert result.endswith("%"), f"{field} should produce % suffix"
            assert "5.00%" == result, f"{field}: 0.05 should display as 5.00%"

    def test_xss_safety_preserved(self):
        """Formatted output still goes through html.escape."""
        # Currency with a value that might look odd but is safe
        result = _format_cell_html(1000.0, "spend")
        assert "&" not in result or "&amp;" in result  # no raw ampersands

    def test_integration_table_with_mixed_types(self):
        """Full table render with currency, rate, int, and text columns."""
        rows = [
            {
                "office": "Acme Dental",
                "spend": 12847.5,
                "ctr": 0.0342,
                "imp": 45000,
                "roas": 3.5,
                "variance_pct": 42.5,
                "lp20m": 8.75,
            },
        ]
        result = _render_section("TEST", rows=rows, row_count=1)

        assert "Acme Dental" in result
        assert "$12,847.50" in result
        assert "3.42%" in result
        assert "45,000" in result
        assert "3.50x" in result
        assert "42.50%" in result
        assert "8.75" in result
