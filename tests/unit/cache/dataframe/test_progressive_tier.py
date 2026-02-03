"""Unit tests for ProgressiveTier.

Per TDD-UNIFIED-PROGRESSIVE-CACHE-001: Tests for reading/writing via
SectionPersistence storage location, key parsing, error handling,
and statistics tracking.
"""

import io
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
from autom8_asana.cache.dataframe_cache import CacheEntry
from autom8_asana.dataframes.async_s3 import S3ReadResult


def make_entry(project_gid: str = "proj-1") -> CacheEntry:
    """Create a test CacheEntry."""
    df = pl.DataFrame(
        {
            "gid": ["gid-1", "gid-2"],
            "name": ["A", "B"],
            "value": [1, 2],
        }
    )

    return CacheEntry(
        project_gid=project_gid,
        entity_type="unit",
        dataframe=df,
        watermark=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        created_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
        schema_version="1.0.0",
    )


def make_parquet_bytes(df: pl.DataFrame | None = None) -> bytes:
    """Create parquet bytes from a DataFrame."""
    if df is None:
        df = pl.DataFrame({"gid": ["gid-1", "gid-2"], "name": ["A", "B"]})
    buffer = io.BytesIO()
    df.write_parquet(buffer)
    return buffer.getvalue()


def make_watermark_json(watermark: str = "2024-01-15T12:00:00+00:00") -> bytes:
    """Create watermark JSON bytes."""
    return json.dumps(
        {
            "project_gid": "proj-1",
            "watermark": watermark,
            "row_count": 2,
            "columns": ["gid", "name"],
            "saved_at": "2024-01-15T12:00:00+00:00",
            "schema_version": "1.0.0",
        }
    ).encode("utf-8")


def make_mock_persistence(
    s3_client: AsyncMock | None = None,
    prefix: str = "dataframes/",
) -> MagicMock:
    """Create a mock SectionPersistence with configured S3 client."""
    persistence = MagicMock()
    persistence._config = MagicMock()
    persistence._config.prefix = prefix
    persistence._s3_client = s3_client if s3_client else AsyncMock()
    persistence.write_final_artifacts_async = AsyncMock(return_value=True)
    return persistence


class TestProgressiveTierKeyParsing:
    """Tests for key parsing logic."""

    def test_parse_key_valid(self) -> None:
        """Valid key formats are parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entity_type, project_gid = tier._parse_key("unit:1234567890")
        assert entity_type == "unit"
        assert project_gid == "1234567890"

    def test_parse_key_with_underscore_entity(self) -> None:
        """Entity types with underscores are parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entity_type, project_gid = tier._parse_key("asset_edit:5555555555")
        assert entity_type == "asset_edit"
        assert project_gid == "5555555555"

    def test_parse_key_invalid_no_colon(self) -> None:
        """Key without colon raises ValueError."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        with pytest.raises(ValueError, match="Invalid cache key format"):
            tier._parse_key("invalid-key")

    def test_parse_key_invalid_empty_entity(self) -> None:
        """Key with empty entity type raises ValueError."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        with pytest.raises(ValueError, match="Invalid cache key format"):
            tier._parse_key(":1234567890")

    def test_parse_key_invalid_empty_project(self) -> None:
        """Key with empty project_gid raises ValueError."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        with pytest.raises(ValueError, match="Invalid cache key format"):
            tier._parse_key("unit:")


class TestProgressiveTierGet:
    """Tests for get_async method."""

    @pytest.mark.asyncio
    async def test_get_async_reads_from_correct_location(self) -> None:
        """Get reads dataframe.parquet from correct project directory."""
        s3_client = AsyncMock()

        # Mock successful DataFrame read
        parquet_bytes = make_parquet_bytes()
        s3_client.get_object_async.side_effect = [
            # First call: dataframe.parquet
            S3ReadResult(
                success=True,
                key="dataframes/proj-123/dataframe.parquet",
                data=parquet_bytes,
                size_bytes=len(parquet_bytes),
            ),
            # Second call: watermark.json
            S3ReadResult(
                success=True,
                key="dataframes/proj-123/watermark.json",
                data=make_watermark_json(),
                size_bytes=100,
            ),
        ]

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is not None
        assert result.project_gid == "proj-123"
        assert result.entity_type == "unit"
        assert result.row_count == 2

        # Verify correct S3 key was used
        calls = s3_client.get_object_async.call_args_list
        assert calls[0][0][0] == "dataframes/proj-123/dataframe.parquet"
        assert calls[1][0][0] == "dataframes/proj-123/watermark.json"

    @pytest.mark.asyncio
    async def test_get_async_returns_none_on_missing(self) -> None:
        """Get returns None when dataframe.parquet doesn't exist."""
        s3_client = AsyncMock()
        s3_client.get_object_async.return_value = S3ReadResult(
            success=False,
            key="dataframes/proj-123/dataframe.parquet",
            not_found=True,
            error="Object not found",
        )

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is None

        stats = tier.get_stats()
        assert stats["not_found"] == 1
        assert stats["reads"] == 1

    @pytest.mark.asyncio
    async def test_get_async_handles_missing_watermark(self) -> None:
        """Get uses fallback watermark when watermark.json is missing."""
        s3_client = AsyncMock()
        parquet_bytes = make_parquet_bytes()

        s3_client.get_object_async.side_effect = [
            # DataFrame read succeeds
            S3ReadResult(
                success=True,
                key="dataframes/proj-123/dataframe.parquet",
                data=parquet_bytes,
                size_bytes=len(parquet_bytes),
            ),
            # Watermark read fails (not found)
            S3ReadResult(
                success=False,
                key="dataframes/proj-123/watermark.json",
                not_found=True,
                error="Object not found",
            ),
        ]

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is not None
        assert result.project_gid == "proj-123"
        # Watermark should be recent (fallback to current time)
        assert result.watermark.tzinfo is not None
        assert result.schema_version == "unknown"

    @pytest.mark.asyncio
    async def test_get_async_handles_corrupted_parquet(self) -> None:
        """Get returns None when parquet parsing fails."""
        s3_client = AsyncMock()
        s3_client.get_object_async.return_value = S3ReadResult(
            success=True,
            key="dataframes/proj-123/dataframe.parquet",
            data=b"not valid parquet data",
            size_bytes=22,
        )

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is None

        stats = tier.get_stats()
        assert stats["read_errors"] == 1

    @pytest.mark.asyncio
    async def test_get_async_handles_s3_error(self) -> None:
        """Get returns None on S3 read error."""
        s3_client = AsyncMock()
        s3_client.get_object_async.return_value = S3ReadResult(
            success=False,
            key="dataframes/proj-123/dataframe.parquet",
            error="Connection timeout",
        )

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("unit:proj-123")

        assert result is None

        stats = tier.get_stats()
        assert stats["read_errors"] == 1

    @pytest.mark.asyncio
    async def test_get_async_invalid_key_returns_none(self) -> None:
        """Get returns None for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.get_async("invalid-key")

        assert result is None

        stats = tier.get_stats()
        assert stats["read_errors"] == 1


class TestProgressiveTierPut:
    """Tests for put_async method."""

    @pytest.mark.asyncio
    async def test_put_async_delegates_to_persistence(self) -> None:
        """Put calls write_final_artifacts_async correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is True
        persistence.write_final_artifacts_async.assert_called_once_with(
            project_gid="proj-1",
            df=entry.dataframe,
            watermark=entry.watermark,
            index_data=None,
            entity_type="unit",
        )

        stats = tier.get_stats()
        assert stats["writes"] == 1
        assert stats["bytes_written"] > 0

    @pytest.mark.asyncio
    async def test_put_async_returns_false_on_error(self) -> None:
        """Put returns False when SectionPersistence write fails."""
        persistence = make_mock_persistence()
        persistence.write_final_artifacts_async.return_value = False

        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is False

        stats = tier.get_stats()
        assert stats["write_errors"] == 1

    @pytest.mark.asyncio
    async def test_put_async_handles_exception(self) -> None:
        """Put returns False on exception."""
        persistence = make_mock_persistence()
        persistence.write_final_artifacts_async.side_effect = Exception("S3 error")

        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is False

        stats = tier.get_stats()
        assert stats["write_errors"] == 1

    @pytest.mark.asyncio
    async def test_put_async_invalid_key_returns_false(self) -> None:
        """Put returns False for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        entry = make_entry()
        result = await tier.put_async("invalid-key", entry)

        assert result is False

        stats = tier.get_stats()
        assert stats["write_errors"] == 1


class TestProgressiveTierExists:
    """Tests for exists_async method."""

    @pytest.mark.asyncio
    async def test_exists_async_checks_dataframe_file(self) -> None:
        """Exists checks for dataframe.parquet presence."""
        s3_client = AsyncMock()
        s3_client.head_object_async.return_value = {
            "content_length": 1234,
            "etag": "abc123",
        }

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.exists_async("unit:proj-123")

        assert result is True
        s3_client.head_object_async.assert_called_once_with(
            "dataframes/proj-123/dataframe.parquet"
        )

    @pytest.mark.asyncio
    async def test_exists_async_returns_false_when_missing(self) -> None:
        """Exists returns False when file doesn't exist."""
        s3_client = AsyncMock()
        s3_client.head_object_async.return_value = None

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.exists_async("unit:proj-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_async_invalid_key_returns_false(self) -> None:
        """Exists returns False for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.exists_async("invalid-key")

        assert result is False


class TestProgressiveTierDelete:
    """Tests for delete_async method."""

    @pytest.mark.asyncio
    async def test_delete_async_removes_artifacts(self) -> None:
        """Delete removes dataframe and watermark files."""
        s3_client = AsyncMock()
        s3_client.delete_object_async.return_value = True

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.delete_async("unit:proj-123")

        assert result is True

        # Should delete both dataframe and watermark
        calls = s3_client.delete_object_async.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "dataframes/proj-123/dataframe.parquet"
        assert calls[1][0][0] == "dataframes/proj-123/watermark.json"

    @pytest.mark.asyncio
    async def test_delete_async_returns_false_on_partial_failure(self) -> None:
        """Delete returns False if any deletion fails."""
        s3_client = AsyncMock()
        s3_client.delete_object_async.side_effect = [True, False]

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.delete_async("unit:proj-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_async_invalid_key_returns_false(self) -> None:
        """Delete returns False for invalid key format."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = await tier.delete_async("invalid-key")

        assert result is False


class TestProgressiveTierStats:
    """Tests for statistics tracking."""

    def test_stats_initial_values(self) -> None:
        """Stats are initialized to zero."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        stats = tier.get_stats()

        assert stats["reads"] == 0
        assert stats["writes"] == 0
        assert stats["read_errors"] == 0
        assert stats["write_errors"] == 0
        assert stats["bytes_read"] == 0
        assert stats["bytes_written"] == 0
        assert stats["not_found"] == 0

    @pytest.mark.asyncio
    async def test_stats_tracking(self) -> None:
        """Stats correctly track reads, writes, errors."""
        s3_client = AsyncMock()
        parquet_bytes = make_parquet_bytes()

        # Set up successful read
        s3_client.get_object_async.side_effect = [
            S3ReadResult(
                success=True,
                key="dataframes/proj-1/dataframe.parquet",
                data=parquet_bytes,
                size_bytes=len(parquet_bytes),
            ),
            S3ReadResult(
                success=True,
                key="dataframes/proj-1/watermark.json",
                data=make_watermark_json(),
                size_bytes=100,
            ),
        ]

        persistence = make_mock_persistence(s3_client=s3_client)
        tier = ProgressiveTier(persistence=persistence)

        # Perform read
        await tier.get_async("unit:proj-1")

        stats = tier.get_stats()
        assert stats["reads"] == 1
        assert stats["bytes_read"] == len(parquet_bytes)

        # Perform write
        entry = make_entry()
        await tier.put_async("unit:proj-1", entry)

        stats = tier.get_stats()
        assert stats["writes"] == 1
        assert stats["bytes_written"] > 0


class TestProgressiveTierDatetimeParsing:
    """Tests for datetime parsing helper."""

    def test_parse_datetime_valid_iso(self) -> None:
        """Valid ISO datetime is parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime("2024-01-15T12:00:00+00:00")

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.tzinfo is not None

    def test_parse_datetime_z_suffix(self) -> None:
        """Datetime with Z suffix is parsed correctly."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime("2024-01-15T12:00:00Z")

        assert result.year == 2024
        assert result.tzinfo is not None

    def test_parse_datetime_none(self) -> None:
        """None value returns current time."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime(None)

        assert result.tzinfo is not None
        # Should be recent
        now = datetime.now(UTC)
        assert abs((now - result).total_seconds()) < 5

    def test_parse_datetime_invalid(self) -> None:
        """Invalid value returns current time."""
        persistence = make_mock_persistence()
        tier = ProgressiveTier(persistence=persistence)

        result = tier._parse_datetime("not-a-date")

        assert result.tzinfo is not None
        # Should be recent
        now = datetime.now(UTC)
        assert abs((now - result).total_seconds()) < 5
