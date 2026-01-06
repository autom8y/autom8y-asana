"""Unit tests for SectionPersistence.

Tests section-level S3 persistence for progressive cache warming.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.async_s3 import S3ReadResult, S3WriteResult
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionPersistence,
    SectionPersistenceConfig,
    SectionStatus,
)


class TestSectionStatus:
    """Tests for SectionStatus enum."""

    def test_values(self) -> None:
        """Status enum has expected values."""
        assert SectionStatus.PENDING == "pending"
        assert SectionStatus.IN_PROGRESS == "in_progress"
        assert SectionStatus.COMPLETE == "complete"
        assert SectionStatus.FAILED == "failed"


class TestSectionInfo:
    """Tests for SectionInfo model."""

    def test_default_values(self) -> None:
        """SectionInfo has sensible defaults."""
        info = SectionInfo()

        assert info.status == SectionStatus.PENDING
        assert info.rows == 0
        assert info.written_at is None
        assert info.error is None

    def test_complete_info(self) -> None:
        """Complete section has written_at and rows."""
        now = datetime.now(timezone.utc)
        info = SectionInfo(
            status=SectionStatus.COMPLETE,
            rows=450,
            written_at=now,
        )

        assert info.status == SectionStatus.COMPLETE
        assert info.rows == 450
        assert info.written_at == now

    def test_failed_info(self) -> None:
        """Failed section has error message."""
        info = SectionInfo(
            status=SectionStatus.FAILED,
            error="Connection timeout",
        )

        assert info.status == SectionStatus.FAILED
        assert info.error == "Connection timeout"


class TestSectionManifest:
    """Tests for SectionManifest model."""

    def test_create_manifest(self) -> None:
        """Manifest can be created with sections."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=3,
            sections={
                "sec_1": SectionInfo(),
                "sec_2": SectionInfo(),
                "sec_3": SectionInfo(),
            },
        )

        assert manifest.project_gid == "123"
        assert manifest.entity_type == "offer"
        assert manifest.total_sections == 3
        assert manifest.completed_sections == 0
        assert len(manifest.sections) == 3

    def test_get_incomplete_section_gids(self) -> None:
        """get_incomplete_section_gids returns pending/failed sections."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=4,
            sections={
                "sec_1": SectionInfo(status=SectionStatus.COMPLETE, rows=100),
                "sec_2": SectionInfo(status=SectionStatus.PENDING),
                "sec_3": SectionInfo(status=SectionStatus.FAILED, error="timeout"),
                "sec_4": SectionInfo(status=SectionStatus.IN_PROGRESS),
            },
        )

        incomplete = manifest.get_incomplete_section_gids()

        assert "sec_1" not in incomplete
        assert "sec_2" in incomplete
        assert "sec_3" in incomplete
        assert "sec_4" not in incomplete  # in_progress is not incomplete

    def test_get_complete_section_gids(self) -> None:
        """get_complete_section_gids returns only complete sections."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=3,
            sections={
                "sec_1": SectionInfo(status=SectionStatus.COMPLETE, rows=100),
                "sec_2": SectionInfo(status=SectionStatus.COMPLETE, rows=200),
                "sec_3": SectionInfo(status=SectionStatus.PENDING),
            },
        )

        complete = manifest.get_complete_section_gids()

        assert "sec_1" in complete
        assert "sec_2" in complete
        assert "sec_3" not in complete

    def test_mark_section_complete(self) -> None:
        """mark_section_complete updates status and counts."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=2,
            sections={
                "sec_1": SectionInfo(),
                "sec_2": SectionInfo(),
            },
        )

        manifest.mark_section_complete("sec_1", rows=450)

        assert manifest.sections["sec_1"].status == SectionStatus.COMPLETE
        assert manifest.sections["sec_1"].rows == 450
        assert manifest.sections["sec_1"].written_at is not None
        assert manifest.completed_sections == 1

    def test_mark_section_failed(self) -> None:
        """mark_section_failed updates status with error."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=2,
            sections={
                "sec_1": SectionInfo(),
                "sec_2": SectionInfo(),
            },
        )

        manifest.mark_section_failed("sec_1", "API rate limited")

        assert manifest.sections["sec_1"].status == SectionStatus.FAILED
        assert manifest.sections["sec_1"].error == "API rate limited"

    def test_mark_section_in_progress(self) -> None:
        """mark_section_in_progress updates status."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=2,
            sections={
                "sec_1": SectionInfo(),
                "sec_2": SectionInfo(),
            },
        )

        manifest.mark_section_in_progress("sec_1")

        assert manifest.sections["sec_1"].status == SectionStatus.IN_PROGRESS

    def test_is_complete(self) -> None:
        """is_complete returns True when all sections done."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=2,
            completed_sections=0,
            sections={
                "sec_1": SectionInfo(),
                "sec_2": SectionInfo(),
            },
        )

        assert manifest.is_complete() is False

        manifest.mark_section_complete("sec_1", 100)
        assert manifest.is_complete() is False

        manifest.mark_section_complete("sec_2", 200)
        assert manifest.is_complete() is True

    def test_serialization(self) -> None:
        """Manifest can be serialized to JSON."""
        manifest = SectionManifest(
            project_gid="123",
            entity_type="offer",
            total_sections=2,
            sections={
                "sec_1": SectionInfo(status=SectionStatus.COMPLETE, rows=100),
                "sec_2": SectionInfo(status=SectionStatus.PENDING),
            },
        )
        manifest.completed_sections = 1

        json_str = manifest.model_dump_json()
        data = json.loads(json_str)

        assert data["project_gid"] == "123"
        assert data["entity_type"] == "offer"
        assert data["total_sections"] == 2
        assert data["completed_sections"] == 1
        assert data["sections"]["sec_1"]["status"] == "complete"
        assert data["sections"]["sec_1"]["rows"] == 100

    def test_deserialization(self) -> None:
        """Manifest can be deserialized from JSON."""
        data = {
            "project_gid": "456",
            "entity_type": "contact",
            "started_at": "2026-01-06T20:00:00Z",
            "total_sections": 3,
            "completed_sections": 2,
            "sections": {
                "sec_1": {"status": "complete", "rows": 150},
                "sec_2": {"status": "complete", "rows": 250},
                "sec_3": {"status": "pending", "rows": 0},
            },
            "version": 1,
        }

        manifest = SectionManifest.model_validate(data)

        assert manifest.project_gid == "456"
        assert manifest.entity_type == "contact"
        assert manifest.total_sections == 3
        assert manifest.sections["sec_1"].status == SectionStatus.COMPLETE
        assert manifest.sections["sec_1"].rows == 150


class TestSectionPersistenceConfig:
    """Tests for SectionPersistenceConfig."""

    def test_default_values(self) -> None:
        """Config has sensible defaults."""
        config = SectionPersistenceConfig(bucket="test-bucket")

        assert config.bucket == "test-bucket"
        assert config.prefix == "dataframes/"
        assert config.region == "us-east-1"
        assert config.endpoint_url is None


class TestSectionPersistenceKeys:
    """Tests for S3 key generation."""

    def test_manifest_key(self) -> None:
        """Manifest key follows expected pattern."""
        config = SectionPersistenceConfig(bucket="test", prefix="cache/")
        persistence = SectionPersistence(config=config)

        key = persistence._make_manifest_key("proj_123")

        assert key == "cache/proj_123/manifest.json"

    def test_section_key(self) -> None:
        """Section key follows expected pattern."""
        config = SectionPersistenceConfig(bucket="test", prefix="dataframes/")
        persistence = SectionPersistence(config=config)

        key = persistence._make_section_key("proj_123", "sec_456")

        assert key == "dataframes/proj_123/sections/sec_456.parquet"

    def test_dataframe_key(self) -> None:
        """DataFrame key follows expected pattern."""
        config = SectionPersistenceConfig(bucket="test", prefix="dataframes/")
        persistence = SectionPersistence(config=config)

        key = persistence._make_dataframe_key("proj_123")

        assert key == "dataframes/proj_123/dataframe.parquet"

    def test_watermark_key(self) -> None:
        """Watermark key follows expected pattern."""
        config = SectionPersistenceConfig(bucket="test", prefix="dataframes/")
        persistence = SectionPersistence(config=config)

        key = persistence._make_watermark_key("proj_123")

        assert key == "dataframes/proj_123/watermark.json"


@pytest.mark.asyncio
class TestSectionPersistenceOperations:
    """Tests for SectionPersistence async operations."""

    async def test_create_manifest(self) -> None:
        """create_manifest_async creates and saves manifest."""
        config = SectionPersistenceConfig(bucket="test")
        persistence = SectionPersistence(config=config)

        # Mock S3 client
        mock_result = S3WriteResult(success=True, key="manifest.json")
        persistence._s3_client = MagicMock()
        persistence._s3_client.put_object_async = AsyncMock(return_value=mock_result)

        manifest = await persistence.create_manifest_async(
            "proj_123",
            "offer",
            ["sec_1", "sec_2", "sec_3"],
        )

        assert manifest.project_gid == "proj_123"
        assert manifest.entity_type == "offer"
        assert manifest.total_sections == 3
        assert len(manifest.sections) == 3
        assert all(
            info.status == SectionStatus.PENDING for info in manifest.sections.values()
        )

    async def test_get_manifest_success(self) -> None:
        """get_manifest_async returns manifest when it exists."""
        config = SectionPersistenceConfig(bucket="test")
        persistence = SectionPersistence(config=config)

        manifest_data = {
            "project_gid": "proj_123",
            "entity_type": "offer",
            "started_at": "2026-01-06T20:00:00Z",
            "total_sections": 2,
            "completed_sections": 1,
            "sections": {
                "sec_1": {"status": "complete", "rows": 100},
                "sec_2": {"status": "pending", "rows": 0},
            },
            "version": 1,
        }

        mock_result = S3ReadResult(
            success=True,
            key="manifest.json",
            data=json.dumps(manifest_data).encode(),
        )
        persistence._s3_client = MagicMock()
        persistence._s3_client.get_object_async = AsyncMock(return_value=mock_result)

        manifest = await persistence.get_manifest_async("proj_123")

        assert manifest is not None
        assert manifest.project_gid == "proj_123"
        assert manifest.completed_sections == 1
        assert manifest.sections["sec_1"].status == SectionStatus.COMPLETE

    async def test_get_manifest_not_found(self) -> None:
        """get_manifest_async returns None when not found."""
        config = SectionPersistenceConfig(bucket="test")
        persistence = SectionPersistence(config=config)

        mock_result = S3ReadResult(
            success=False,
            key="manifest.json",
            not_found=True,
        )
        persistence._s3_client = MagicMock()
        persistence._s3_client.get_object_async = AsyncMock(return_value=mock_result)

        manifest = await persistence.get_manifest_async("proj_123")

        assert manifest is None

    async def test_get_incomplete_sections(self) -> None:
        """get_incomplete_sections returns pending/failed sections."""
        config = SectionPersistenceConfig(bucket="test")
        persistence = SectionPersistence(config=config)

        manifest_data = {
            "project_gid": "proj_123",
            "entity_type": "offer",
            "started_at": "2026-01-06T20:00:00Z",
            "total_sections": 3,
            "completed_sections": 1,
            "sections": {
                "sec_1": {"status": "complete", "rows": 100},
                "sec_2": {"status": "pending", "rows": 0},
                "sec_3": {"status": "failed", "error": "timeout"},
            },
            "version": 1,
        }

        mock_result = S3ReadResult(
            success=True,
            key="manifest.json",
            data=json.dumps(manifest_data).encode(),
        )
        persistence._s3_client = MagicMock()
        persistence._s3_client.get_object_async = AsyncMock(return_value=mock_result)

        incomplete = await persistence.get_incomplete_sections("proj_123")

        assert "sec_2" in incomplete
        assert "sec_3" in incomplete
        assert "sec_1" not in incomplete

    async def test_write_section(self) -> None:
        """write_section_async writes DataFrame and updates manifest."""
        config = SectionPersistenceConfig(bucket="test")
        persistence = SectionPersistence(config=config)
        persistence._polars_module = pl

        # Create test DataFrame
        df = pl.DataFrame({"gid": ["1", "2"], "name": ["Task 1", "Task 2"]})

        # Mock S3 operations
        mock_write_result = S3WriteResult(
            success=True,
            key="sections/sec_1.parquet",
            size_bytes=1024,
            duration_ms=50,
        )

        manifest_data = {
            "project_gid": "proj_123",
            "entity_type": "offer",
            "started_at": "2026-01-06T20:00:00Z",
            "total_sections": 2,
            "completed_sections": 0,
            "sections": {
                "sec_1": {"status": "in_progress", "rows": 0},
                "sec_2": {"status": "pending", "rows": 0},
            },
            "version": 1,
        }
        mock_read_result = S3ReadResult(
            success=True,
            key="manifest.json",
            data=json.dumps(manifest_data).encode(),
        )

        persistence._s3_client = MagicMock()
        persistence._s3_client.put_object_async = AsyncMock(return_value=mock_write_result)
        persistence._s3_client.get_object_async = AsyncMock(return_value=mock_read_result)

        success = await persistence.write_section_async("proj_123", "sec_1", df)

        assert success is True
        # Verify put_object was called for section parquet
        persistence._s3_client.put_object_async.assert_called()

    async def test_read_section(self) -> None:
        """read_section_async reads DataFrame from S3."""
        config = SectionPersistenceConfig(bucket="test")
        persistence = SectionPersistence(config=config)
        persistence._polars_module = pl

        # Create test parquet bytes
        df = pl.DataFrame({"gid": ["1", "2"], "name": ["Task 1", "Task 2"]})
        import io

        buffer = io.BytesIO()
        df.write_parquet(buffer)
        buffer.seek(0)
        parquet_bytes = buffer.read()

        mock_result = S3ReadResult(
            success=True,
            key="sections/sec_1.parquet",
            data=parquet_bytes,
            size_bytes=len(parquet_bytes),
        )
        persistence._s3_client = MagicMock()
        persistence._s3_client.get_object_async = AsyncMock(return_value=mock_result)

        result_df = await persistence.read_section_async("proj_123", "sec_1")

        assert result_df is not None
        assert len(result_df) == 2
        assert result_df["gid"].to_list() == ["1", "2"]

    async def test_merge_sections(self) -> None:
        """merge_sections_to_dataframe_async merges all complete sections."""
        config = SectionPersistenceConfig(bucket="test")
        persistence = SectionPersistence(config=config)
        persistence._polars_module = pl

        # Create test parquet bytes for two sections
        df1 = pl.DataFrame({"gid": ["1", "2"], "name": ["Task 1", "Task 2"]})
        df2 = pl.DataFrame({"gid": ["3", "4"], "name": ["Task 3", "Task 4"]})

        import io

        buffer1 = io.BytesIO()
        df1.write_parquet(buffer1)
        buffer1.seek(0)
        parquet1 = buffer1.read()

        buffer2 = io.BytesIO()
        df2.write_parquet(buffer2)
        buffer2.seek(0)
        parquet2 = buffer2.read()

        manifest_data = {
            "project_gid": "proj_123",
            "entity_type": "offer",
            "started_at": "2026-01-06T20:00:00Z",
            "total_sections": 2,
            "completed_sections": 2,
            "sections": {
                "sec_1": {"status": "complete", "rows": 2},
                "sec_2": {"status": "complete", "rows": 2},
            },
            "version": 1,
        }

        # Mock to return different data based on key
        async def mock_get_object(key: str) -> S3ReadResult:
            if "manifest.json" in key:
                return S3ReadResult(
                    success=True,
                    key=key,
                    data=json.dumps(manifest_data).encode(),
                )
            elif "sec_1" in key:
                return S3ReadResult(success=True, key=key, data=parquet1)
            elif "sec_2" in key:
                return S3ReadResult(success=True, key=key, data=parquet2)
            return S3ReadResult(success=False, key=key, not_found=True)

        persistence._s3_client = MagicMock()
        persistence._s3_client.get_object_async = AsyncMock(side_effect=mock_get_object)

        merged = await persistence.merge_sections_to_dataframe_async("proj_123")

        assert merged is not None
        assert len(merged) == 4
        assert set(merged["gid"].to_list()) == {"1", "2", "3", "4"}
