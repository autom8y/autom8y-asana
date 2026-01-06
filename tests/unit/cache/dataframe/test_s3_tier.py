"""Unit tests for S3Tier.

Per TDD-DATAFRAME-CACHE-001: Tests for Parquet serialization,
metadata handling, and error cases.
"""

import io
from datetime import datetime, timezone
from unittest.mock import MagicMock

import polars as pl
import pytest

from autom8_asana.cache.dataframe_cache import CacheEntry
from autom8_asana.cache.dataframe.tiers.s3 import S3Tier


def make_entry(project_gid: str = "proj-1") -> CacheEntry:
    """Create a test CacheEntry."""
    df = pl.DataFrame({
        "gid": ["gid-1", "gid-2"],
        "name": ["A", "B"],
        "value": [1, 2],
    })

    return CacheEntry(
        project_gid=project_gid,
        entity_type="unit",
        dataframe=df,
        watermark=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
        schema_version="1.0.0",
    )


class TestS3Tier:
    """Tests for S3Tier."""

    @pytest.mark.asyncio
    async def test_put_serializes_to_parquet(self) -> None:
        """Put serializes DataFrame to Parquet format."""
        mock_client = MagicMock()
        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is True
        mock_client.put_object.assert_called_once()

        call_kwargs = mock_client.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "df/unit:proj-1.parquet"
        assert call_kwargs["ContentType"] == "application/x-parquet"

        # Verify body is valid Parquet
        body = call_kwargs["Body"]
        df = pl.read_parquet(io.BytesIO(body))
        assert len(df) == 2

    @pytest.mark.asyncio
    async def test_put_includes_metadata(self) -> None:
        """Put includes metadata in S3 object."""
        mock_client = MagicMock()
        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        entry = make_entry()
        await tier.put_async("unit:proj-1", entry)

        call_kwargs = mock_client.put_object.call_args.kwargs
        metadata = call_kwargs["Metadata"]

        assert metadata["project_gid"] == "proj-1"
        assert metadata["entity_type"] == "unit"
        assert metadata["schema_version"] == "1.0.0"
        assert metadata["row_count"] == "2"
        assert "watermark" in metadata
        assert "created_at" in metadata

    @pytest.mark.asyncio
    async def test_put_handles_exception(self) -> None:
        """Put returns False on exception."""
        mock_client = MagicMock()
        mock_client.put_object.side_effect = Exception("S3 error")

        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        entry = make_entry()
        result = await tier.put_async("unit:proj-1", entry)

        assert result is False

        stats = tier.get_stats()
        assert stats["write_errors"] == 1

    @pytest.mark.asyncio
    async def test_get_deserializes_parquet(self) -> None:
        """Get deserializes Parquet to DataFrame."""
        # Create a Parquet buffer
        df = pl.DataFrame({"gid": ["1", "2"], "name": ["A", "B"]})
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        parquet_bytes = buffer.getvalue()

        # Mock S3 response
        mock_body = MagicMock()
        mock_body.read.return_value = parquet_bytes

        mock_client = MagicMock()
        mock_client.get_object.return_value = {
            "Body": mock_body,
            "Metadata": {
                "project_gid": "proj-1",
                "entity_type": "unit",
                "watermark": "2024-01-15T12:00:00+00:00",
                "created_at": "2024-01-15T11:00:00+00:00",
                "schema_version": "1.0.0",
            },
        }

        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.get_async("unit:proj-1")

        assert result is not None
        assert result.project_gid == "proj-1"
        assert result.entity_type == "unit"
        assert result.row_count == 2
        assert result.schema_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_returns_none_on_not_found(self) -> None:
        """Get returns None when key not found."""
        mock_client = MagicMock()

        # Create mock exception class
        class NoSuchKey(Exception):
            pass

        mock_client.exceptions.NoSuchKey = NoSuchKey
        mock_client.get_object.side_effect = NoSuchKey()

        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.get_async("unit:proj-1")

        assert result is None

        stats = tier.get_stats()
        assert stats["not_found"] == 1

    @pytest.mark.asyncio
    async def test_get_returns_none_on_error(self) -> None:
        """Get returns None on general error."""
        mock_client = MagicMock()

        # Create mock exception class that won't match NoSuchKey
        class NoSuchKey(Exception):
            pass

        mock_client.exceptions.NoSuchKey = NoSuchKey
        mock_client.get_object.side_effect = Exception("Connection error")

        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.get_async("unit:proj-1")

        assert result is None

        stats = tier.get_stats()
        assert stats["read_errors"] == 1

    @pytest.mark.asyncio
    async def test_get_parses_key_for_defaults(self) -> None:
        """Get extracts project_gid and entity_type from key if not in metadata."""
        df = pl.DataFrame({"gid": ["1"]})
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        parquet_bytes = buffer.getvalue()

        mock_body = MagicMock()
        mock_body.read.return_value = parquet_bytes

        mock_client = MagicMock()
        mock_client.get_object.return_value = {
            "Body": mock_body,
            "Metadata": {},  # No metadata
        }

        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.get_async("offer:proj-123")

        assert result is not None
        assert result.entity_type == "offer"
        assert result.project_gid == "proj-123"

    @pytest.mark.asyncio
    async def test_exists(self) -> None:
        """Exists checks S3 for key."""
        mock_client = MagicMock()
        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.exists_async("unit:proj-1")

        assert result is True
        mock_client.head_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_returns_false_on_error(self) -> None:
        """Exists returns False on error."""
        mock_client = MagicMock()
        mock_client.head_object.side_effect = Exception("Not found")

        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.exists_async("unit:proj-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Delete removes key from S3."""
        mock_client = MagicMock()
        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.delete_async("unit:proj-1")

        assert result is True
        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="df/unit:proj-1.parquet",
        )

    @pytest.mark.asyncio
    async def test_delete_handles_error(self) -> None:
        """Delete returns False on error."""
        mock_client = MagicMock()
        mock_client.delete_object.side_effect = Exception("Error")

        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        result = await tier.delete_async("unit:proj-1")

        assert result is False

    def test_stats(self) -> None:
        """Stats track operations correctly."""
        mock_client = MagicMock()
        tier = S3Tier(bucket="test-bucket", prefix="df/", s3_client=mock_client)

        stats = tier.get_stats()

        assert "reads" in stats
        assert "writes" in stats
        assert "read_errors" in stats
        assert "write_errors" in stats
        assert "bytes_read" in stats
        assert "bytes_written" in stats

    def test_key_format(self) -> None:
        """S3 key uses correct format."""
        mock_client = MagicMock()
        tier = S3Tier(bucket="test-bucket", prefix="cache/v1/", s3_client=mock_client)

        # Put to check key format
        entry = make_entry()

        # Use synchronous call to avoid async complexity
        import asyncio

        asyncio.run(tier.put_async("unit:proj-123", entry))

        call_kwargs = mock_client.put_object.call_args.kwargs
        assert call_kwargs["Key"] == "cache/v1/unit:proj-123.parquet"
