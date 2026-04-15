"""Tests for InsightsResponse models.

Per TDD-INSIGHTS-001 Section 4.2-4.4: Unit tests for model parsing,
DataFrame conversion, and staleness fields.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import polars as pl
import pytest
from pydantic import ValidationError

from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)

# -----------------------------------------------------------------------------
# InsightsRequest Tests
# -----------------------------------------------------------------------------


class TestInsightsRequest:
    """Tests for InsightsRequest model."""

    def test_minimal_request(self) -> None:
        """Create request with only required fields."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        assert request.office_phone == "+17705753103"
        assert request.vertical == "chiropractic"
        assert request.insights_period == "lifetime"
        assert request.refresh is False
        assert request.filters == {}

    def test_full_request(self) -> None:
        """Create request with all fields."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
            insights_period="t30",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            metrics=["spend", "impressions"],
            dimensions=["date"],
            groups=["campaign_id"],
            break_down=["ad_type"],
            refresh=True,
            filters={"status": "active"},
        )
        assert request.insights_period == "t30"
        assert request.start_date == date(2025, 1, 1)
        assert request.end_date == date(2025, 1, 31)
        assert request.metrics == ["spend", "impressions"]
        assert request.dimensions == ["date"]
        assert request.groups == ["campaign_id"]
        assert request.break_down == ["ad_type"]
        assert request.refresh is True
        assert request.filters == {"status": "active"}


class TestInsightsRequestPeriodValidation:
    """Tests for insights_period validation."""

    @pytest.mark.parametrize(
        "period",
        [
            "lifetime",
            "date",
            "day",
            "week",
            "month",
            "quarter",
            "year",
        ],
    )
    def test_valid_standard_periods(self, period: str) -> None:
        """Standard period values are accepted."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
            insights_period=period,
        )
        assert request.insights_period == period.lower()

    @pytest.mark.parametrize(
        "period",
        ["t1", "t3", "t7", "t10", "t14", "t30", "t90", "t180", "t365"],
    )
    def test_valid_trailing_periods(self, period: str) -> None:
        """Trailing period values (t{N}) are accepted."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
            insights_period=period,
        )
        assert request.insights_period == period.lower()

    @pytest.mark.parametrize(
        "period",
        ["l1", "l3", "l7", "l10", "l14", "l30", "l90", "l180", "l365", "l24h"],
    )
    def test_valid_last_periods(self, period: str) -> None:
        """Last period values (l{N} or l{N}h) are accepted."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
            insights_period=period,
        )
        assert request.insights_period == period.lower()

    def test_period_case_insensitive(self) -> None:
        """Period validation is case-insensitive."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
            insights_period="LIFETIME",
        )
        assert request.insights_period == "lifetime"

    def test_period_none_allowed(self) -> None:
        """None period value is allowed."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
            insights_period=None,
        )
        assert request.insights_period is None

    @pytest.mark.parametrize(
        "invalid_period",
        [
            "invalid",
            "t",
            "l",
            "t-30",
            "last30",
            "30days",
            "monthly",
        ],
    )
    def test_invalid_period_raises(self, invalid_period: str) -> None:
        """Invalid period values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InsightsRequest(
                office_phone="+17705753103",
                vertical="chiropractic",
                insights_period=invalid_period,
            )
        assert "Invalid period format" in str(exc_info.value)


class TestInsightsRequestSerialization:
    """Tests for InsightsRequest serialization."""

    def test_model_dump_excludes_none(self) -> None:
        """model_dump(exclude_none=True) excludes None fields."""
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
        )
        data = request.model_dump(exclude_none=True)

        assert "office_phone" in data
        assert "vertical" in data
        assert "insights_period" in data  # has default value
        assert "start_date" not in data  # None excluded
        assert "end_date" not in data  # None excluded
        assert "metrics" not in data  # None excluded


# -----------------------------------------------------------------------------
# ColumnInfo Tests
# -----------------------------------------------------------------------------


class TestColumnInfo:
    """Tests for ColumnInfo model."""

    def test_basic_column(self) -> None:
        """Create column info with basic fields."""
        col = ColumnInfo(name="spend", dtype="float64")
        assert col.name == "spend"
        assert col.dtype == "float64"
        assert col.nullable is True  # default

    def test_non_nullable_column(self) -> None:
        """Create non-nullable column."""
        col = ColumnInfo(name="id", dtype="int64", nullable=False)
        assert col.nullable is False


# -----------------------------------------------------------------------------
# InsightsMetadata Tests
# -----------------------------------------------------------------------------


class TestInsightsMetadata:
    """Tests for InsightsMetadata model."""

    def test_minimal_metadata(self) -> None:
        """Create metadata with required fields only."""
        metadata = InsightsMetadata(
            factory="account",
            row_count=10,
            column_count=5,
            columns=[
                ColumnInfo(name="spend", dtype="float64"),
            ],
            cache_hit=False,
            duration_ms=50.0,
        )
        assert metadata.factory == "account"
        assert metadata.row_count == 10
        assert metadata.column_count == 5
        assert len(metadata.columns) == 1
        assert metadata.cache_hit is False
        assert metadata.duration_ms == 50.0

        # Defaults
        assert metadata.frame_type is None
        assert metadata.insights_period is None
        assert metadata.sort_history is None
        assert metadata.is_stale is False
        assert metadata.cached_at is None

    def test_full_metadata(self) -> None:
        """Create metadata with all fields."""
        cached_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        metadata = InsightsMetadata(
            factory="account",
            frame_type="AccountInsights",
            insights_period="t30",
            row_count=100,
            column_count=10,
            columns=[
                ColumnInfo(name="spend", dtype="float64"),
                ColumnInfo(name="impressions", dtype="int64"),
            ],
            cache_hit=True,
            duration_ms=25.0,
            sort_history=["date", "spend"],
            is_stale=True,
            cached_at=cached_at,
        )
        assert metadata.frame_type == "AccountInsights"
        assert metadata.insights_period == "t30"
        assert metadata.sort_history == ["date", "spend"]
        assert metadata.is_stale is True
        assert metadata.cached_at == cached_at


class TestInsightsMetadataStaleness:
    """Tests for staleness fields (per ADR-INS-004 revision)."""

    def test_is_stale_default_false(self) -> None:
        """is_stale defaults to False."""
        metadata = InsightsMetadata(
            factory="account",
            row_count=0,
            column_count=0,
            columns=[],
            cache_hit=False,
            duration_ms=0.0,
        )
        assert metadata.is_stale is False

    def test_cached_at_default_none(self) -> None:
        """cached_at defaults to None."""
        metadata = InsightsMetadata(
            factory="account",
            row_count=0,
            column_count=0,
            columns=[],
            cache_hit=False,
            duration_ms=0.0,
        )
        assert metadata.cached_at is None

    def test_stale_response_indicators(self) -> None:
        """Stale response has is_stale=True and cached_at set."""
        cached_at = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        metadata = InsightsMetadata(
            factory="account",
            row_count=5,
            column_count=2,
            columns=[ColumnInfo(name="spend", dtype="float64")],
            cache_hit=False,
            duration_ms=0.0,
            is_stale=True,
            cached_at=cached_at,
        )
        assert metadata.is_stale is True
        assert metadata.cached_at == cached_at


# -----------------------------------------------------------------------------
# InsightsResponse Tests
# -----------------------------------------------------------------------------


class TestInsightsResponse:
    """Tests for InsightsResponse model."""

    def test_minimal_response(self) -> None:
        """Create response with minimal data."""
        response = InsightsResponse(
            data=[],
            metadata=InsightsMetadata(
                factory="account",
                row_count=0,
                column_count=0,
                columns=[],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-123",
        )
        assert response.data == []
        assert response.metadata.factory == "account"
        assert response.request_id == "test-123"
        assert response.warnings == []  # default

    def test_response_with_data(self) -> None:
        """Create response with actual data rows."""
        response = InsightsResponse(
            data=[
                {"spend": 100.0, "impressions": 5000},
                {"spend": 150.0, "impressions": 7500},
            ],
            metadata=InsightsMetadata(
                factory="account",
                row_count=2,
                column_count=2,
                columns=[
                    ColumnInfo(name="spend", dtype="float64"),
                    ColumnInfo(name="impressions", dtype="int64"),
                ],
                cache_hit=True,
                duration_ms=45.0,
            ),
            request_id="test-456",
            warnings=["Some data may be delayed"],
        )
        assert len(response.data) == 2
        assert response.warnings == ["Some data may be delayed"]


class TestInsightsResponseToDataFrame:
    """Tests for to_dataframe() method."""

    def test_empty_data_returns_empty_dataframe_with_schema(self) -> None:
        """Empty data returns DataFrame with schema from metadata."""
        response = InsightsResponse(
            data=[],
            metadata=InsightsMetadata(
                factory="account",
                row_count=0,
                column_count=2,
                columns=[
                    ColumnInfo(name="spend", dtype="float64"),
                    ColumnInfo(name="impressions", dtype="int64"),
                ],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-123",
        )

        df = response.to_dataframe()

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0
        assert df.schema == {"spend": pl.Float64, "impressions": pl.Int64}

    def test_data_converted_to_polars_dataframe(self) -> None:
        """Data is converted to Polars DataFrame."""
        response = InsightsResponse(
            data=[
                {"spend": 100.0, "impressions": 5000},
                {"spend": 150.0, "impressions": 7500},
            ],
            metadata=InsightsMetadata(
                factory="account",
                row_count=2,
                column_count=2,
                columns=[
                    ColumnInfo(name="spend", dtype="float64"),
                    ColumnInfo(name="impressions", dtype="int64"),
                ],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-123",
        )

        df = response.to_dataframe()

        assert isinstance(df, pl.DataFrame)
        assert len(df) == 2
        assert df["spend"].to_list() == [100.0, 150.0]
        assert df["impressions"].to_list() == [5000, 7500]

    def test_dtypes_cast_from_metadata(self) -> None:
        """Column dtypes are cast according to metadata."""
        response = InsightsResponse(
            data=[
                {"id": 1, "name": "Test", "active": True},
            ],
            metadata=InsightsMetadata(
                factory="account",
                row_count=1,
                column_count=3,
                columns=[
                    ColumnInfo(name="id", dtype="int64"),
                    ColumnInfo(name="name", dtype="string"),
                    ColumnInfo(name="active", dtype="bool"),
                ],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-123",
        )

        df = response.to_dataframe()

        assert df.schema["id"] == pl.Int64
        assert df.schema["name"] == pl.Utf8
        assert df.schema["active"] == pl.Boolean

    def test_unknown_dtype_preserves_original(self) -> None:
        """Unknown dtype in metadata preserves original column dtype."""
        response = InsightsResponse(
            data=[{"value": "test"}],
            metadata=InsightsMetadata(
                factory="account",
                row_count=1,
                column_count=1,
                columns=[
                    ColumnInfo(name="value", dtype="unknown_type"),
                ],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-123",
        )

        df = response.to_dataframe()

        # Column exists but wasn't cast (original dtype preserved)
        assert "value" in df.columns
        assert df["value"].to_list() == ["test"]

    def test_missing_column_in_data_ignored(self) -> None:
        """Columns in metadata but not in data are ignored during casting."""
        response = InsightsResponse(
            data=[{"existing": 100}],
            metadata=InsightsMetadata(
                factory="account",
                row_count=1,
                column_count=2,
                columns=[
                    ColumnInfo(name="existing", dtype="int64"),
                    ColumnInfo(name="missing", dtype="float64"),
                ],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-123",
        )

        df = response.to_dataframe()

        assert "existing" in df.columns
        assert "missing" not in df.columns


class TestInsightsResponseToPandas:
    """Tests for to_pandas() method."""

    def test_converts_to_pandas_dataframe(self) -> None:
        """to_pandas() returns pandas DataFrame."""
        pd = pytest.importorskip("pandas")

        response = InsightsResponse(
            data=[
                {"spend": 100.0, "impressions": 5000},
            ],
            metadata=InsightsMetadata(
                factory="account",
                row_count=1,
                column_count=2,
                columns=[
                    ColumnInfo(name="spend", dtype="float64"),
                    ColumnInfo(name="impressions", dtype="int64"),
                ],
                cache_hit=False,
                duration_ms=0.0,
            ),
            request_id="test-123",
        )

        pdf = response.to_pandas()

        assert isinstance(pdf, pd.DataFrame)
        assert len(pdf) == 1
        assert pdf["spend"].iloc[0] == 100.0
        assert pdf["impressions"].iloc[0] == 5000


class TestInsightsResponseDtypeMapping:
    """Tests for _polars_dtype() static method."""

    @pytest.mark.parametrize(
        ("dtype_str", "expected"),
        [
            ("int64", pl.Int64),
            ("int32", pl.Int32),
            ("int16", pl.Int16),
            ("int8", pl.Int8),
            ("uint64", pl.UInt64),
            ("uint32", pl.UInt32),
            ("uint16", pl.UInt16),
            ("uint8", pl.UInt8),
            ("float64", pl.Float64),
            ("float32", pl.Float32),
            ("bool", pl.Boolean),
            ("boolean", pl.Boolean),
            ("object", pl.Utf8),
            ("string", pl.Utf8),
            ("str", pl.Utf8),
            ("datetime64[ns]", pl.Datetime),
            ("datetime", pl.Datetime),
            ("date", pl.Date),
        ],
    )
    def test_dtype_mapping(self, dtype_str: str, expected: pl.DataType) -> None:
        """Each dtype string maps to correct Polars type."""
        result = InsightsResponse._polars_dtype(dtype_str)
        assert result == expected

    def test_dtype_mapping_case_insensitive(self) -> None:
        """Dtype mapping is case-insensitive."""
        assert InsightsResponse._polars_dtype("INT64") == pl.Int64
        assert InsightsResponse._polars_dtype("Float64") == pl.Float64
        assert InsightsResponse._polars_dtype("STRING") == pl.Utf8

    def test_unknown_dtype_returns_none(self) -> None:
        """Unknown dtype returns None."""
        assert InsightsResponse._polars_dtype("unknown") is None
        assert InsightsResponse._polars_dtype("complex128") is None


class TestInsightsResponseParsing:
    """Tests for parsing InsightsResponse from JSON-like data."""

    def test_parse_from_dict(self) -> None:
        """Parse InsightsResponse from dictionary (simulating API response)."""
        api_response: dict[str, Any] = {
            "data": [
                {"spend": 100.0, "impressions": 5000},
            ],
            "metadata": {
                "factory": "account",
                "frame_type": "AccountInsights",
                "row_count": 1,
                "column_count": 2,
                "columns": [
                    {"name": "spend", "dtype": "float64", "nullable": True},
                    {"name": "impressions", "dtype": "int64", "nullable": True},
                ],
                "cache_hit": False,
                "duration_ms": 45.5,
            },
            "request_id": "api-request-123",
            "warnings": [],
        }

        response = InsightsResponse(**api_response)

        assert response.metadata.factory == "account"
        assert response.metadata.frame_type == "AccountInsights"
        assert len(response.metadata.columns) == 2
        assert response.metadata.columns[0].name == "spend"
        assert response.request_id == "api-request-123"

    def test_parse_with_staleness_info(self) -> None:
        """Parse response with staleness indicators."""
        api_response: dict[str, Any] = {
            "data": [{"value": 42}],
            "metadata": {
                "factory": "account",
                "row_count": 1,
                "column_count": 1,
                "columns": [{"name": "value", "dtype": "int64"}],
                "cache_hit": False,
                "duration_ms": 0.0,
                "is_stale": True,
                "cached_at": "2025-01-01T12:00:00+00:00",
            },
            "request_id": "stale-123",
        }

        response = InsightsResponse(**api_response)

        assert response.metadata.is_stale is True
        assert response.metadata.cached_at == datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)


# -----------------------------------------------------------------------------
# Integration-style Tests
# -----------------------------------------------------------------------------


class TestInsightsResponseRoundTrip:
    """Tests for full round-trip: create -> serialize -> parse -> convert."""

    def test_request_to_response_roundtrip(self) -> None:
        """Full workflow from request creation to DataFrame."""
        # Create a request
        request = InsightsRequest(
            office_phone="+17705753103",
            vertical="chiropractic",
            insights_period="t30",
            metrics=["spend", "impressions"],
        )

        # Simulate API response based on request
        response = InsightsResponse(
            data=[
                {"spend": 100.0, "impressions": 5000},
                {"spend": 200.0, "impressions": 10000},
            ],
            metadata=InsightsMetadata(
                factory="account",
                insights_period=request.insights_period,
                row_count=2,
                column_count=2,
                columns=[
                    ColumnInfo(name="spend", dtype="float64"),
                    ColumnInfo(name="impressions", dtype="int64"),
                ],
                cache_hit=False,
                duration_ms=50.0,
            ),
            request_id="roundtrip-123",
        )

        # Convert to DataFrame
        df = response.to_dataframe()

        # Verify data integrity
        assert len(df) == 2
        assert df["spend"].sum() == 300.0
        assert df["impressions"].sum() == 15000
        assert df.schema == {"spend": pl.Float64, "impressions": pl.Int64}
