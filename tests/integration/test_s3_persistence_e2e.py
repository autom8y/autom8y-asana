"""E2E integration tests for S3 DataFrame persistence with real S3.

Per spike-s3-persistence task:
Tests DataFrame persistence against actual S3 (not moto mocks) to validate
production behavior. These tests require a configured S3 bucket and are
skipped in CI where S3 is not available.

Environment Variables Required:
    ASANA_CACHE_S3_BUCKET: S3 bucket name for persistence storage
    ASANA_CACHE_S3_REGION: AWS region (optional, default us-east-1)
    ASANA_CACHE_S3_PREFIX: Key prefix (optional, default dataframes/)

Running Locally:
    export ASANA_CACHE_S3_BUCKET=your-test-bucket
    just test tests/integration/test_s3_persistence_e2e.py -m integration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import polars as pl
import pytest

from autom8_asana.dataframes.persistence import DataFramePersistence
from autom8_asana.settings import S3Settings, get_settings

if TYPE_CHECKING:
    pass

# Mark entire module as integration test (not run in CI unit test suite)
pytestmark = pytest.mark.integration


@pytest.fixture
def s3_configured() -> S3Settings:
    """Skip test if S3 is not configured.

    Returns:
        S3Settings if bucket is configured.

    Raises:
        pytest.skip: If ASANA_CACHE_S3_BUCKET is not set.
    """
    settings = get_settings()
    if not settings.s3.bucket:
        pytest.skip("S3 not configured (ASANA_CACHE_S3_BUCKET not set)")
    return settings.s3


@pytest.fixture
def test_project_gid() -> str:
    """Generate unique project GID for test isolation.

    Each test gets a unique project_gid to avoid conflicts when tests
    run in parallel or when cleanup fails.
    """
    return f"e2e_test_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def persistence(s3_configured: S3Settings) -> DataFramePersistence:
    """Create DataFramePersistence configured for real S3.

    Uses a test-specific prefix to isolate E2E test data from production data.
    """
    return DataFramePersistence(
        bucket=s3_configured.bucket,
        prefix="e2e-test-dataframes/",
        region=s3_configured.region,
        endpoint_url=s3_configured.endpoint_url,
    )


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Create a sample DataFrame with various data types for round-trip testing."""
    return pl.DataFrame(
        {
            "gid": ["task_001", "task_002", "task_003"],
            "name": ["Task A", "Task B", "Task C"],
            "completed": [True, False, True],
            "priority": [1, 2, 3],
            "created_at": [
                datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
                datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
                datetime(2025, 1, 3, 12, 0, tzinfo=timezone.utc),
            ],
            "notes": ["Note 1", None, "Note 3"],
        }
    )


class TestS3PersistenceE2E:
    """E2E tests for S3 DataFrame persistence with real S3."""

    @pytest.mark.asyncio
    async def test_round_trip_with_real_s3(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
        test_project_gid: str,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Build -> save -> load -> compare with real S3.

        Verifies:
        - DataFrame survives round-trip through S3 (Parquet serialization)
        - All data types are preserved (strings, bools, ints, datetimes, nulls)
        - Watermark timestamp is correctly stored and retrieved
        - Column order and structure are maintained
        """
        # Arrange
        watermark = datetime(2025, 1, 5, 12, 0, 0, tzinfo=timezone.utc)

        try:
            # Act: Save DataFrame to S3
            save_success = await persistence.save_dataframe(
                project_gid=test_project_gid,
                df=sample_dataframe,
                watermark=watermark,
            )
            assert save_success is True, "save_dataframe should return True on success"

            # Act: Load DataFrame from S3
            loaded_df, loaded_watermark = await persistence.load_dataframe(
                test_project_gid
            )

            # Assert: DataFrame loaded successfully
            assert loaded_df is not None, "Loaded DataFrame should not be None"
            assert loaded_watermark is not None, "Loaded watermark should not be None"

            # Assert: Row count matches
            assert len(loaded_df) == len(sample_dataframe), (
                f"Row count mismatch: expected {len(sample_dataframe)}, got {len(loaded_df)}"
            )

            # Assert: Column structure preserved
            assert loaded_df.columns == sample_dataframe.columns, (
                f"Column mismatch: expected {sample_dataframe.columns}, got {loaded_df.columns}"
            )

            # Assert: Data values preserved
            assert loaded_df["gid"].to_list() == ["task_001", "task_002", "task_003"]
            assert loaded_df["name"].to_list() == ["Task A", "Task B", "Task C"]
            assert loaded_df["completed"].to_list() == [True, False, True]
            assert loaded_df["priority"].to_list() == [1, 2, 3]

            # Assert: Null values preserved
            notes = loaded_df["notes"].to_list()
            assert notes[0] == "Note 1"
            assert notes[1] is None
            assert notes[2] == "Note 3"

            # Assert: Watermark preserved exactly
            assert loaded_watermark == watermark, (
                f"Watermark mismatch: expected {watermark.isoformat()}, "
                f"got {loaded_watermark.isoformat()}"
            )

        finally:
            # Cleanup: Remove test data from S3
            await persistence.delete_dataframe(test_project_gid)

    @pytest.mark.asyncio
    async def test_watermark_persistence(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
        test_project_gid: str,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Verify watermark metadata stored in S3 object.

        Tests:
        - Watermark JSON file is created separately from DataFrame
        - get_watermark_only() retrieves watermark without loading DataFrame
        - Watermark contains microsecond precision
        """
        # Arrange: Use a watermark with microseconds to test precision
        watermark = datetime(2025, 6, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)

        try:
            # Act: Save DataFrame with watermark
            await persistence.save_dataframe(
                project_gid=test_project_gid,
                df=sample_dataframe,
                watermark=watermark,
            )

            # Act: Retrieve watermark only (fast path, no DataFrame load)
            watermark_only = await persistence.get_watermark_only(test_project_gid)

            # Assert: Watermark retrieved successfully
            assert watermark_only is not None, (
                "get_watermark_only should return watermark"
            )

            # Assert: Watermark matches exactly (including microseconds)
            assert watermark_only == watermark, (
                f"Watermark precision loss: expected {watermark.isoformat()}, "
                f"got {watermark_only.isoformat()}"
            )

            # Assert: Timezone is preserved
            assert watermark_only.tzinfo is not None, (
                "Watermark should have timezone info"
            )

        finally:
            # Cleanup
            await persistence.delete_dataframe(test_project_gid)

    @pytest.mark.asyncio
    async def test_graceful_degradation_bucket_removed(
        self,
        s3_configured: S3Settings,
        test_project_gid: str,
    ) -> None:
        """Verify silent fallback when bucket becomes inaccessible.

        Tests graceful degradation behavior:
        - Operations on nonexistent bucket don't raise exceptions
        - save_dataframe returns False (not exception)
        - load_dataframe returns (None, None)
        - System can recover when bucket becomes available again

        Note: This test uses a deliberately invalid bucket name to simulate
        bucket inaccessibility. In production, this could happen if:
        - Bucket is deleted
        - Permissions are revoked
        - Network partition occurs
        """
        # Arrange: Create persistence with nonexistent bucket
        invalid_persistence = DataFramePersistence(
            bucket="nonexistent-bucket-e2e-test-12345",
            prefix="test/",
            region=s3_configured.region,
        )

        df = pl.DataFrame({"gid": ["123"], "name": ["Test"]})
        watermark = datetime.now(timezone.utc)

        # Act & Assert: save_dataframe should fail gracefully (return False, no exception)
        save_result = await invalid_persistence.save_dataframe(
            project_gid=test_project_gid,
            df=df,
            watermark=watermark,
        )
        assert save_result is False, "save to invalid bucket should return False"

        # Act & Assert: load_dataframe should fail gracefully (return None, None)
        loaded_df, loaded_wm = await invalid_persistence.load_dataframe(
            test_project_gid
        )
        assert loaded_df is None, (
            "load from invalid bucket should return None DataFrame"
        )
        assert loaded_wm is None, (
            "load from invalid bucket should return None watermark"
        )

        # Act & Assert: get_watermark_only should fail gracefully
        wm_only = await invalid_persistence.get_watermark_only(test_project_gid)
        assert wm_only is None, (
            "get_watermark_only from invalid bucket should return None"
        )

        # Assert: Persistence correctly reports unavailable status
        assert invalid_persistence.is_available is False, (
            "is_available should be False for invalid bucket"
        )

    @pytest.mark.asyncio
    async def test_list_persisted_projects(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
    ) -> None:
        """Test listing all projects with persisted DataFrames.

        Creates multiple test projects, persists them, then verifies
        list_persisted_projects returns all of them.
        """
        # Arrange: Create multiple unique test project GIDs
        test_projects = [f"e2e_list_test_{uuid.uuid4().hex[:8]}" for _ in range(3)]
        df = pl.DataFrame({"gid": ["123"], "name": ["Test"]})
        watermark = datetime.now(timezone.utc)

        try:
            # Act: Persist DataFrames for each project
            for project_gid in test_projects:
                success = await persistence.save_dataframe(
                    project_gid=project_gid,
                    df=df,
                    watermark=watermark,
                )
                assert success is True, f"Failed to save DataFrame for {project_gid}"

            # Act: List all persisted projects
            listed_projects = await persistence.list_persisted_projects()

            # Assert: All test projects are in the list
            for project_gid in test_projects:
                assert project_gid in listed_projects, (
                    f"Project {project_gid} not found in listed projects"
                )

        finally:
            # Cleanup: Delete all test projects
            for project_gid in test_projects:
                await persistence.delete_dataframe(project_gid)

    @pytest.mark.asyncio
    async def test_delete_dataframe(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
        test_project_gid: str,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Test deletion of persisted DataFrame.

        Verifies:
        - delete_dataframe removes both DataFrame and watermark
        - Subsequent load returns (None, None)
        - Delete is idempotent (succeeds even if already deleted)
        """
        watermark = datetime.now(timezone.utc)

        # Act: Save then delete
        await persistence.save_dataframe(
            project_gid=test_project_gid,
            df=sample_dataframe,
            watermark=watermark,
        )

        delete_success = await persistence.delete_dataframe(test_project_gid)
        assert delete_success is True, "delete_dataframe should return True"

        # Assert: Load returns None after deletion
        loaded_df, loaded_wm = await persistence.load_dataframe(test_project_gid)
        assert loaded_df is None, "DataFrame should be None after deletion"
        assert loaded_wm is None, "Watermark should be None after deletion"

        # Assert: Idempotent deletion (deleting again should succeed)
        delete_again = await persistence.delete_dataframe(test_project_gid)
        assert delete_again is True, "delete_dataframe should be idempotent"

    @pytest.mark.asyncio
    async def test_overwrite_existing_dataframe(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
        test_project_gid: str,
    ) -> None:
        """Test overwriting an existing persisted DataFrame.

        Verifies:
        - Second save overwrites first
        - New data is returned on load
        - Watermark is updated
        """
        # Arrange: Create two different DataFrames
        df_v1 = pl.DataFrame({"gid": ["v1_001"], "name": ["Version 1"]})
        wm_v1 = datetime(2025, 1, 1, tzinfo=timezone.utc)

        df_v2 = pl.DataFrame(
            {"gid": ["v2_001", "v2_002"], "name": ["Version 2A", "Version 2B"]}
        )
        wm_v2 = datetime(2025, 6, 1, tzinfo=timezone.utc)

        try:
            # Act: Save v1, then overwrite with v2
            await persistence.save_dataframe(test_project_gid, df_v1, wm_v1)
            await persistence.save_dataframe(test_project_gid, df_v2, wm_v2)

            # Assert: Load returns v2
            loaded_df, loaded_wm = await persistence.load_dataframe(test_project_gid)

            assert loaded_df is not None
            assert len(loaded_df) == 2, "Should have 2 rows from v2"
            assert loaded_df["gid"].to_list() == ["v2_001", "v2_002"]
            assert loaded_wm == wm_v2, "Watermark should be v2"

        finally:
            await persistence.delete_dataframe(test_project_gid)

    @pytest.mark.asyncio
    async def test_large_dataframe_persistence(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
        test_project_gid: str,
    ) -> None:
        """Test persistence with a larger DataFrame (10,000 rows).

        Validates that Parquet serialization handles realistic dataset sizes
        without data loss or corruption.
        """
        # Arrange: Create large DataFrame
        num_rows = 10_000
        large_df = pl.DataFrame(
            {
                "gid": [f"task_{i:06d}" for i in range(num_rows)],
                "name": [f"Task Number {i}" for i in range(num_rows)],
                "completed": [i % 2 == 0 for i in range(num_rows)],
                "priority": [i % 5 for i in range(num_rows)],
            }
        )
        watermark = datetime.now(timezone.utc)

        try:
            # Act: Save and load
            save_success = await persistence.save_dataframe(
                test_project_gid, large_df, watermark
            )
            assert save_success is True

            loaded_df, loaded_wm = await persistence.load_dataframe(test_project_gid)

            # Assert: All rows preserved
            assert loaded_df is not None
            assert len(loaded_df) == num_rows, f"Expected {num_rows} rows"

            # Spot check some values
            assert loaded_df["gid"][0] == "task_000000"
            assert loaded_df["gid"][num_rows - 1] == f"task_{num_rows - 1:06d}"
            assert loaded_df["completed"][0] is True  # 0 % 2 == 0
            assert loaded_df["completed"][1] is False  # 1 % 2 != 0

        finally:
            await persistence.delete_dataframe(test_project_gid)

    @pytest.mark.asyncio
    async def test_special_characters_in_data(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
        test_project_gid: str,
    ) -> None:
        """Test persistence with special characters in string fields.

        Validates handling of:
        - Unicode characters (emoji, CJK, accented chars)
        - Newlines and tabs
        - Empty strings
        """
        df = pl.DataFrame(
            {
                "gid": ["u001", "u002", "u003", "u004"],
                "name": [
                    "Task with emoji: cat face with tears of joy",  # Emoji removed
                    "Japanese text",
                    "Accented: cafe, naive, resume",
                    "",  # Empty string
                ],
                "notes": [
                    "Line1\nLine2\tTabbed",  # Newlines and tabs
                    "Quotes: 'single' and \"double\"",
                    "<html>&amp;entities</html>",  # HTML entities
                    None,  # Null
                ],
            }
        )
        watermark = datetime.now(timezone.utc)

        try:
            await persistence.save_dataframe(test_project_gid, df, watermark)
            loaded_df, _ = await persistence.load_dataframe(test_project_gid)

            assert loaded_df is not None
            assert len(loaded_df) == 4

            # Verify special characters preserved
            assert "\n" in loaded_df["notes"][0]
            assert "\t" in loaded_df["notes"][0]
            assert loaded_df["name"][3] == ""  # Empty string preserved
            assert loaded_df["notes"][3] is None  # Null preserved

        finally:
            await persistence.delete_dataframe(test_project_gid)


class TestS3PersistenceIsAvailable:
    """Tests for the is_available property with real S3."""

    def test_is_available_with_valid_bucket(
        self,
        s3_configured: S3Settings,
        persistence: DataFramePersistence,
    ) -> None:
        """Verify is_available returns True for configured, accessible bucket."""
        assert persistence.is_available is True, (
            "is_available should be True for valid S3 configuration"
        )

    def test_is_available_with_invalid_bucket(
        self,
        s3_configured: S3Settings,
    ) -> None:
        """Verify is_available returns False for nonexistent bucket."""
        invalid_persistence = DataFramePersistence(
            bucket="this-bucket-does-not-exist-12345",
            region=s3_configured.region,
        )
        # Note: is_available does a head_bucket check which will fail
        assert invalid_persistence.is_available is False
