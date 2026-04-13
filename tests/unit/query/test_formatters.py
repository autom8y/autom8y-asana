"""Tests for query/formatters.py: Output format correctness."""

from __future__ import annotations

import io
import json

import pytest

from autom8_asana.query.formatters import (
    CsvFormatter,
    JsonFormatter,
    JsonlFormatter,
    TableFormatter,
)
from autom8_asana.query.models import (
    AggregateMeta,
    AggregateResponse,
    RowsMeta,
    RowsResponse,
)


@pytest.fixture
def sample_rows_response() -> RowsResponse:
    """RowsResponse with 3 rows for formatter testing."""
    return RowsResponse(
        data=[
            {"gid": "1", "name": "Alpha", "section": "Active", "mrr": "100"},
            {"gid": "2", "name": "Beta", "section": "Won", "mrr": "200"},
            {"gid": "3", "name": "Gamma", "section": "Active", "mrr": "300"},
        ],
        meta=RowsMeta(
            total_count=3,
            returned_count=3,
            limit=100,
            offset=0,
            entity_type="offer",
            project_gid="123",
            query_ms=42.5,
        ),
    )


@pytest.fixture
def sample_aggregate_response() -> AggregateResponse:
    """AggregateResponse with 2 groups for formatter testing."""
    return AggregateResponse(
        data=[
            {"section": "Active", "sum_mrr": 400},
            {"section": "Won", "sum_mrr": 200},
        ],
        meta=AggregateMeta(
            group_count=2,
            aggregation_count=1,
            group_by=["section"],
            entity_type="offer",
            project_gid="123",
            query_ms=15.3,
        ),
    )


@pytest.fixture
def sample_discovery_rows() -> list[dict[str, object]]:
    """Discovery rows for entities/fields/relations formatters."""
    return [
        {"entity_type": "offer", "display_name": "Offer", "project_gid": "123"},
        {"entity_type": "unit", "display_name": "Business Units", "project_gid": "456"},
    ]


@pytest.fixture
def empty_rows_response() -> RowsResponse:
    """RowsResponse with no data for empty-result testing."""
    return RowsResponse(
        data=[],
        meta=RowsMeta(
            total_count=0,
            returned_count=0,
            limit=100,
            offset=0,
            entity_type="offer",
            project_gid="123",
            query_ms=1.0,
        ),
    )


class TestJsonFormatter:
    """JSON array output correctness."""

    def test_format_rows_valid_json(self, sample_rows_response: RowsResponse) -> None:
        """Output must be valid JSON."""
        buf = io.StringIO()
        JsonFormatter().format_rows(sample_rows_response, buf)
        data = json.loads(buf.getvalue())
        assert isinstance(data, list)
        assert len(data) == 3

    def test_format_rows_field_count(self, sample_rows_response: RowsResponse) -> None:
        """Each row must have the correct number of fields."""
        buf = io.StringIO()
        JsonFormatter().format_rows(sample_rows_response, buf)
        data = json.loads(buf.getvalue())
        for row in data:
            assert len(row) == 4  # gid, name, section, mrr

    def test_format_rows_values(self, sample_rows_response: RowsResponse) -> None:
        """Values must match input data."""
        buf = io.StringIO()
        JsonFormatter().format_rows(sample_rows_response, buf)
        data = json.loads(buf.getvalue())
        assert data[0]["gid"] == "1"
        assert data[0]["name"] == "Alpha"
        assert data[2]["mrr"] == "300"

    def test_format_aggregate_valid_json(
        self, sample_aggregate_response: AggregateResponse
    ) -> None:
        """Aggregate output must be valid JSON."""
        buf = io.StringIO()
        JsonFormatter().format_aggregate(sample_aggregate_response, buf)
        data = json.loads(buf.getvalue())
        assert isinstance(data, list)
        assert len(data) == 2

    def test_format_discovery_valid_json(
        self, sample_discovery_rows: list[dict[str, object]]
    ) -> None:
        """Discovery output must be valid JSON."""
        buf = io.StringIO()
        JsonFormatter().format_discovery(sample_discovery_rows, buf)
        data = json.loads(buf.getvalue())
        assert isinstance(data, list)
        assert len(data) == 2

    def test_format_empty_rows(self, empty_rows_response: RowsResponse) -> None:
        """Empty result produces empty JSON array."""
        buf = io.StringIO()
        JsonFormatter().format_rows(empty_rows_response, buf)
        data = json.loads(buf.getvalue())
        assert data == []


class TestCsvFormatter:
    """CSV output correctness."""

    def test_format_rows_has_header(self, sample_rows_response: RowsResponse) -> None:
        """CSV output must have a header row."""
        buf = io.StringIO()
        CsvFormatter().format_rows(sample_rows_response, buf)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 4  # header + 3 data rows
        header = lines[0]
        assert "gid" in header
        assert "name" in header

    def test_format_rows_data_values(self, sample_rows_response: RowsResponse) -> None:
        """CSV data rows contain expected values."""
        buf = io.StringIO()
        CsvFormatter().format_rows(sample_rows_response, buf)
        content = buf.getvalue()
        assert "Alpha" in content
        assert "Beta" in content
        assert "300" in content

    def test_format_aggregate_csv(self, sample_aggregate_response: AggregateResponse) -> None:
        """Aggregate CSV output has correct structure."""
        buf = io.StringIO()
        CsvFormatter().format_aggregate(sample_aggregate_response, buf)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 3  # header + 2 groups

    def test_format_empty_rows(self, empty_rows_response: RowsResponse) -> None:
        """Empty result produces no output (no header)."""
        buf = io.StringIO()
        CsvFormatter().format_rows(empty_rows_response, buf)
        assert buf.getvalue() == ""


class TestTableFormatter:
    """Table output correctness."""

    def test_format_rows_contains_headers(self, sample_rows_response: RowsResponse) -> None:
        """Table output must contain column headers."""
        buf = io.StringIO()
        TableFormatter().format_rows(sample_rows_response, buf)
        output = buf.getvalue()
        assert "gid" in output
        assert "name" in output
        assert "section" in output

    def test_format_rows_contains_values(self, sample_rows_response: RowsResponse) -> None:
        """Table output must contain data values."""
        buf = io.StringIO()
        TableFormatter().format_rows(sample_rows_response, buf)
        output = buf.getvalue()
        assert "Alpha" in output
        assert "Beta" in output

    def test_format_empty_rows(self, empty_rows_response: RowsResponse) -> None:
        """Empty result shows placeholder message."""
        buf = io.StringIO()
        TableFormatter().format_rows(empty_rows_response, buf)
        assert "empty result set" in buf.getvalue()

    def test_format_discovery(self, sample_discovery_rows: list[dict[str, object]]) -> None:
        """Discovery table contains entity type names."""
        buf = io.StringIO()
        TableFormatter().format_discovery(sample_discovery_rows, buf)
        output = buf.getvalue()
        assert "offer" in output
        assert "unit" in output

    def test_format_discovery_empty(self) -> None:
        """Empty discovery shows placeholder."""
        buf = io.StringIO()
        TableFormatter().format_discovery([], buf)
        assert "no results" in buf.getvalue()


class TestJsonlFormatter:
    """JSONL output correctness."""

    def test_format_rows_one_per_line(self, sample_rows_response: RowsResponse) -> None:
        """Each line must be a valid JSON object."""
        buf = io.StringIO()
        JsonlFormatter().format_rows(sample_rows_response, buf)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            obj = json.loads(line)
            assert isinstance(obj, dict)

    def test_format_rows_values(self, sample_rows_response: RowsResponse) -> None:
        """JSONL values match input data."""
        buf = io.StringIO()
        JsonlFormatter().format_rows(sample_rows_response, buf)
        lines = buf.getvalue().strip().split("\n")
        first = json.loads(lines[0])
        assert first["gid"] == "1"
        assert first["name"] == "Alpha"

    def test_format_empty_rows(self, empty_rows_response: RowsResponse) -> None:
        """Empty result produces no output."""
        buf = io.StringIO()
        JsonlFormatter().format_rows(empty_rows_response, buf)
        assert buf.getvalue() == ""

    def test_format_discovery(self, sample_discovery_rows: list[dict[str, object]]) -> None:
        """Discovery JSONL has one line per entry."""
        buf = io.StringIO()
        JsonlFormatter().format_discovery(sample_discovery_rows, buf)
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 2
