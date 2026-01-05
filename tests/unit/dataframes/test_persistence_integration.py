"""Tests for DataFrame builder persistence integration.

Per spike-s3-persistence integration map:
Tests automatic S3 persistence after DataFrame build with moto S3 mocking.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

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


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestDataFrameBuilderPersistence:
    """Test automatic persistence after DataFrame build."""

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
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.models.schema import DataFrameSchema, ColumnDef
        from autom8_asana.dataframes.persistence import DataFramePersistence

        # Setup persistence with mocked S3
        persistence = DataFramePersistence(
            bucket="test-bucket",
            prefix="test/",
        )

        # Create minimal schema
        schema = DataFrameSchema(
            name="test",
            task_type="Unit",
            version="1.0",
            columns=[
                ColumnDef(name="gid", dtype=pl.Utf8, source="task.gid"),
                ColumnDef(name="name", dtype=pl.Utf8, source="task.name"),
            ],
        )

        # Create builder with persistence
        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="Unit",
            schema=schema,
            unified_store=mock_unified_store,
            persistence=persistence,
        )

        # Mock the view plugin to return a test DataFrame
        test_df = pl.DataFrame(
            {
                "gid": ["123", "456"],
                "name": ["Task 1", "Task 2"],
            }
        )

        # We need to mock the internal build process
        # Since we can't easily mock the entire unified path, let's test the
        # persistence method directly
        watermark = datetime.now(timezone.utc)
        await builder._persist_dataframe_async(
            project_gid="proj_123",
            df=test_df,
            watermark=watermark,
        )

        # Verify DataFrame was saved to S3
        loaded_df, loaded_watermark = await persistence.load_dataframe("proj_123")

        assert loaded_df is not None
        assert len(loaded_df) == 2
        assert loaded_df["gid"].to_list() == ["123", "456"]
        assert loaded_df["name"].to_list() == ["Task 1", "Task 2"]
        assert loaded_watermark is not None

    @pytest.mark.asyncio
    async def test_persistence_none_does_not_save(
        self, mock_project, mock_unified_store
    ):
        """Test that no persistence occurs when persistence=None."""
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.models.schema import DataFrameSchema, ColumnDef

        schema = DataFrameSchema(
            name="test",
            task_type="Unit",
            version="1.0",
            columns=[
                ColumnDef(name="gid", dtype=pl.Utf8, source="task.gid"),
            ],
        )

        # Create builder WITHOUT persistence
        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="Unit",
            schema=schema,
            unified_store=mock_unified_store,
            persistence=None,
        )

        # Test DataFrame
        test_df = pl.DataFrame({"gid": ["123"]})
        watermark = datetime.now(timezone.utc)

        # Should not raise, should be no-op
        await builder._persist_dataframe_async(
            project_gid="proj_123",
            df=test_df,
            watermark=watermark,
        )

    @pytest.mark.asyncio
    async def test_persistence_failure_silent_fallback(
        self, mock_project, mock_unified_store
    ):
        """Test that persistence failures don't break the build."""
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.dataframes.models.schema import DataFrameSchema, ColumnDef
        from autom8_asana.dataframes.persistence import DataFramePersistence

        # Create persistence with invalid bucket (will fail)
        persistence = DataFramePersistence(
            bucket="nonexistent-bucket-12345",
            prefix="test/",
        )

        schema = DataFrameSchema(
            name="test",
            task_type="Unit",
            version="1.0",
            columns=[
                ColumnDef(name="gid", dtype=pl.Utf8, source="task.gid"),
            ],
        )

        builder = ProjectDataFrameBuilder(
            project=mock_project,
            task_type="Unit",
            schema=schema,
            unified_store=mock_unified_store,
            persistence=persistence,
        )

        test_df = pl.DataFrame({"gid": ["123"]})
        watermark = datetime.now(timezone.utc)

        # Should not raise even though S3 is unavailable
        await builder._persist_dataframe_async(
            project_gid="proj_123",
            df=test_df,
            watermark=watermark,
        )

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


class TestCreateWithAutoPersistence:
    """Tests for the create_with_auto_persistence() factory method."""

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
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.settings import reset_settings

        # Set S3 environment variables
        with patch.dict(
            os.environ,
            {
                "ASANA_CACHE_S3_BUCKET": "test-auto-bucket",
                "ASANA_CACHE_S3_PREFIX": "auto-prefix/",
            },
            clear=False,
        ):
            reset_settings()

            try:
                builder = ProjectDataFrameBuilder.create_with_auto_persistence(
                    project=mock_project,
                    task_type="Unit",
                    schema=minimal_schema,
                    unified_store=mock_unified_store,
                )

                # Verify builder was created
                assert builder is not None
                assert builder.project == mock_project
                assert builder.task_type == "Unit"

                # Verify persistence was configured
                assert builder._persistence is not None
                assert builder._persistence._config.bucket == "test-auto-bucket"
                assert builder._persistence._config.prefix == "auto-prefix/"
            finally:
                reset_settings()

    def test_factory_without_s3_bucket(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory gracefully handles missing S3 bucket."""
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.settings import reset_settings

        # Ensure no S3 bucket is set
        env_without_bucket = {
            k: v for k, v in os.environ.items() if k != "ASANA_CACHE_S3_BUCKET"
        }

        with patch.dict(os.environ, env_without_bucket, clear=True):
            reset_settings()

            try:
                builder = ProjectDataFrameBuilder.create_with_auto_persistence(
                    project=mock_project,
                    task_type="Unit",
                    schema=minimal_schema,
                    unified_store=mock_unified_store,
                )

                # Verify builder was created
                assert builder is not None
                assert builder.project == mock_project

                # Verify persistence is None (graceful fallback)
                assert builder._persistence is None
            finally:
                reset_settings()

    def test_factory_with_optional_params(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory passes through optional parameters correctly."""
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.settings import reset_settings

        mock_resolver = MagicMock()
        mock_cache_integration = MagicMock()
        mock_client = MagicMock()

        # Ensure no S3 bucket (we're testing param passthrough, not S3)
        env_without_bucket = {
            k: v for k, v in os.environ.items() if k != "ASANA_CACHE_S3_BUCKET"
        }

        with patch.dict(os.environ, env_without_bucket, clear=True):
            reset_settings()

            try:
                builder = ProjectDataFrameBuilder.create_with_auto_persistence(
                    project=mock_project,
                    task_type="Contact",
                    schema=minimal_schema,
                    unified_store=mock_unified_store,
                    sections=["Active", "Pending"],
                    resolver=mock_resolver,
                    lazy_threshold=500,
                    cache_integration=mock_cache_integration,
                    client=mock_client,
                )

                # Verify all parameters were passed through
                assert builder.task_type == "Contact"
                assert builder.sections == ["Active", "Pending"]
                assert builder._resolver == mock_resolver
                assert builder._lazy_threshold == 500
                assert builder._cache_integration == mock_cache_integration
                assert builder._client == mock_client
            finally:
                reset_settings()

    def test_factory_handles_settings_exception(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory gracefully handles exception during settings load."""
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder

        # Patch at the source module where get_settings is defined
        with patch(
            "autom8_asana.settings.get_settings",
            side_effect=RuntimeError("Settings load failed"),
        ):
            # Should not raise - should return builder with persistence=None
            builder = ProjectDataFrameBuilder.create_with_auto_persistence(
                project=mock_project,
                task_type="Unit",
                schema=minimal_schema,
                unified_store=mock_unified_store,
            )

            assert builder is not None
            assert builder._persistence is None

    @pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
    def test_factory_with_mocked_s3(
        self, mock_project, mock_unified_store, minimal_schema
    ):
        """Test factory with moto-mocked S3 to verify end-to-end persistence."""
        from autom8_asana.dataframes.builders.project import ProjectDataFrameBuilder
        from autom8_asana.settings import reset_settings

        with mock_aws():
            # Create test bucket
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="moto-test-bucket")

            with patch.dict(
                os.environ,
                {
                    "ASANA_CACHE_S3_BUCKET": "moto-test-bucket",
                    "ASANA_CACHE_S3_PREFIX": "test-prefix/",
                    "ASANA_CACHE_S3_REGION": "us-east-1",
                },
                clear=False,
            ):
                reset_settings()

                try:
                    builder = ProjectDataFrameBuilder.create_with_auto_persistence(
                        project=mock_project,
                        task_type="Unit",
                        schema=minimal_schema,
                        unified_store=mock_unified_store,
                    )

                    # Verify persistence is configured and available
                    assert builder._persistence is not None
                    assert builder._persistence._config.bucket == "moto-test-bucket"
                    # Persistence availability depends on boto3 client init
                    # With moto, the bucket exists so this should pass
                    assert builder._persistence.is_available is True
                finally:
                    reset_settings()
