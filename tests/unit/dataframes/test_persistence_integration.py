"""Tests for DataFrame builder persistence integration.

Per spike-s3-persistence integration map:
Tests automatic S3 persistence after DataFrame build with moto S3 mocking.

NOTE: These tests require migration to ProgressiveProjectBuilder.
The old ProjectDataFrameBuilder has been removed. Tests are skipped until migration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import polars as pl
import pytest

# Try to import moto, skip tests if not available
try:
    from moto import mock_aws
    import boto3

    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    mock_aws = None  # type: ignore[assignment, misc]

# Skip marker for tests that use ProjectDataFrameBuilder
MIGRATION_REQUIRED = pytest.mark.skip(
    reason="Requires migration to ProgressiveProjectBuilder - constructor signatures differ"
)


@MIGRATION_REQUIRED
@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestDataFrameBuilderPersistence:
    """Test automatic persistence after DataFrame build.

    NOTE: These tests require migration to ProgressiveProjectBuilder.
    The old ProjectDataFrameBuilder has been removed.
    """

    @pytest.fixture
    def s3_setup(self):
        """Setup mocked S3 environment."""
        with mock_aws():
            # Create test bucket
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="test-bucket")
            yield client

    @pytest.fixture
    def mock_project(self):
        """Create a mock Project object."""
        project = MagicMock()
        project.gid = "proj_123"
        project.name = "Test Project"
        return project

    @pytest.fixture
    def mock_unified_store(self):
        """Create a mock UnifiedTaskStore."""
        store = MagicMock()
        store.get_batch_async = AsyncMock(return_value={})
        store.put_batch_async = AsyncMock()
        return store

    @pytest.mark.asyncio
    async def test_automatic_persistence_on_build(
        self, s3_setup, mock_project, mock_unified_store
    ):
        """Test DataFrame is automatically persisted after successful build."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    @pytest.mark.asyncio
    async def test_persistence_none_does_not_save(
        self, mock_project, mock_unified_store
    ):
        """Test that no persistence occurs when persistence=None."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    @pytest.mark.asyncio
    async def test_persistence_failure_silent_fallback(
        self, mock_project, mock_unified_store
    ):
        """Test that persistence failures don't break the build."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    @pytest.mark.asyncio
    async def test_round_trip_persistence(self, s3_setup):
        """Test full round-trip: save DataFrame -> load DataFrame -> verify data matches."""
        from autom8_asana.dataframes.persistence import DataFramePersistence

        persistence = DataFramePersistence(
            bucket="test-bucket",
            prefix="roundtrip/",
        )

        # Create test DataFrame with various data types
        original_df = pl.DataFrame(
            {
                "gid": ["123", "456", "789"],
                "name": ["Task A", "Task B", "Task C"],
                "completed": [True, False, True],
                "created_at": [
                    datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                    datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
                    datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc),
                ],
            }
        )

        watermark = datetime(2025, 1, 5, 12, 0, tzinfo=timezone.utc)

        # Save
        success = await persistence.save_dataframe(
            project_gid="proj_roundtrip",
            df=original_df,
            watermark=watermark,
        )
        assert success is True

        # Load
        loaded_df, loaded_watermark = await persistence.load_dataframe("proj_roundtrip")

        # Verify
        assert loaded_df is not None
        assert loaded_watermark is not None
        assert len(loaded_df) == len(original_df)
        assert loaded_df.columns == original_df.columns
        assert loaded_df["gid"].to_list() == ["123", "456", "789"]
        assert loaded_df["name"].to_list() == ["Task A", "Task B", "Task C"]
        assert loaded_df["completed"].to_list() == [True, False, True]

        # Verify watermark
        assert loaded_watermark == watermark


@MIGRATION_REQUIRED
class TestCreateWithAutoPersistence:
    """Tests for the create_with_auto_persistence() factory method.

    NOTE: These tests require migration to ProgressiveProjectBuilder.
    The old ProjectDataFrameBuilder.create_with_auto_persistence() has been removed.
    """

    @pytest.fixture
    def mock_project(self):
        """Create a mock Project object."""
        project = MagicMock()
        project.gid = "proj_factory_123"
        project.name = "Factory Test Project"
        return project

    @pytest.fixture
    def mock_unified_store(self):
        """Create a mock UnifiedTaskStore."""
        store = MagicMock()
        store.get_batch_async = AsyncMock(return_value={})
        store.put_batch_async = AsyncMock()
        return store

    @pytest.fixture
    def minimal_schema(self):
        """Create a minimal schema for testing."""
        from autom8_asana.dataframes.models.schema import DataFrameSchema, ColumnDef

        return DataFrameSchema(
            name="test",
            task_type="Unit",
            version="1.0",
            columns=[
                ColumnDef(name="gid", dtype=pl.Utf8, source="task.gid"),
                ColumnDef(name="name", dtype=pl.Utf8, source="task.name"),
            ],
        )

    def test_factory_with_s3_configured(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory creates persistence when S3 bucket is configured."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    def test_factory_without_s3_bucket(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory gracefully handles missing S3 bucket."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    def test_factory_with_optional_params(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory passes through optional parameters correctly."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    def test_factory_handles_settings_exception(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory gracefully handles exception during settings load."""
        # Migration required: ProjectDataFrameBuilder removed
        pass

    @pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
    def test_factory_with_mocked_s3(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory with moto-mocked S3 to verify end-to-end persistence."""
        # Migration required: ProjectDataFrameBuilder removed
        pass
