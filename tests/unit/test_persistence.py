"""Tests for DataFramePersistence S3 operations.

Tests cover:
- save_dataframe stores parquet + watermark
- load_dataframe retrieves data
- load_dataframe returns (None, None) when not found
- delete_dataframe removes files
- Graceful handling of S3 errors
- Degraded mode behavior

Per sprint-materialization-002 Task T3:
DataFramePersistence provides restart resilience by persisting DataFrame
state and watermarks to S3.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.persistence import (
    DataFramePersistence,
    PersistenceConfig,
)


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Create a sample DataFrame for testing."""
    return pl.DataFrame(
        {
            "gid": ["task-1", "task-2", "task-3"],
            "name": ["Task 1", "Task 2", "Task 3"],
            "completed": [False, True, False],
        }
    )


@pytest.fixture
def sample_watermark() -> datetime:
    """Create a sample watermark for testing."""
    return datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)


class TestPersistenceConfig:
    """Tests for PersistenceConfig dataclass."""

    def test_config_with_defaults(self) -> None:
        """Config with only bucket uses sensible defaults."""
        config = PersistenceConfig(bucket="my-bucket")

        assert config.bucket == "my-bucket"
        assert config.prefix == "dataframes/"
        assert config.region == "us-east-1"
        assert config.endpoint_url is None
        assert config.enabled is True

    def test_config_with_all_params(self) -> None:
        """Config accepts all parameters."""
        config = PersistenceConfig(
            bucket="custom-bucket",
            prefix="custom-prefix/",
            region="eu-west-1",
            endpoint_url="http://localhost:4566",
            enabled=False,
        )

        assert config.bucket == "custom-bucket"
        assert config.prefix == "custom-prefix/"
        assert config.region == "eu-west-1"
        assert config.endpoint_url == "http://localhost:4566"
        assert config.enabled is False


class TestKeyGeneration:
    """Tests for S3 key generation methods."""

    def test_make_dataframe_key(self) -> None:
        """DataFrame key follows expected format."""
        config = PersistenceConfig(bucket="bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)

        key = persistence._make_dataframe_key("project-123")

        assert key == "dataframes/project-123/dataframe.parquet"

    def test_make_watermark_key(self) -> None:
        """Watermark key follows expected format."""
        config = PersistenceConfig(bucket="bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)

        key = persistence._make_watermark_key("project-123")

        assert key == "dataframes/project-123/watermark.json"

    def test_custom_prefix(self) -> None:
        """Custom prefix is respected in key generation."""
        config = PersistenceConfig(bucket="bucket", prefix="custom/path/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)

        df_key = persistence._make_dataframe_key("proj")
        wm_key = persistence._make_watermark_key("proj")

        assert df_key == "custom/path/proj/dataframe.parquet"
        assert wm_key == "custom/path/proj/watermark.json"


class TestSaveDataframe:
    """Tests for save_dataframe method."""

    @pytest.mark.asyncio
    async def test_save_dataframe_rejects_naive_datetime(
        self,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """save_dataframe raises ValueError for naive datetime."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._polars_module = pl

        naive_dt = datetime(2024, 6, 15)  # No tzinfo

        with pytest.raises(ValueError, match="timezone-aware"):
            await persistence.save_dataframe("project-123", sample_dataframe, naive_dt)

    @pytest.mark.asyncio
    async def test_save_dataframe_returns_false_when_degraded(
        self,
        sample_dataframe: pl.DataFrame,
        sample_watermark: datetime,
    ) -> None:
        """save_dataframe returns False when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        result = await persistence.save_dataframe(
            "project-123",
            sample_dataframe,
            sample_watermark,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_save_dataframe_returns_false_when_polars_unavailable(
        self,
        sample_dataframe: pl.DataFrame,
        sample_watermark: datetime,
    ) -> None:
        """save_dataframe returns False when polars is unavailable."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._polars_module = None

        result = await persistence.save_dataframe(
            "project-123",
            sample_dataframe,
            sample_watermark,
        )

        assert result is False


class TestLoadDataframe:
    """Tests for load_dataframe method."""

    @pytest.mark.asyncio
    async def test_load_dataframe_returns_none_when_degraded(self) -> None:
        """load_dataframe returns (None, None) when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        df, watermark = await persistence.load_dataframe("project-123")

        assert df is None
        assert watermark is None

    @pytest.mark.asyncio
    async def test_load_dataframe_returns_none_when_polars_unavailable(self) -> None:
        """load_dataframe returns (None, None) when polars is unavailable."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._polars_module = None

        df, watermark = await persistence.load_dataframe("project-123")

        assert df is None
        assert watermark is None


class TestDeleteDataframe:
    """Tests for delete_dataframe method."""

    @pytest.mark.asyncio
    async def test_delete_dataframe_returns_false_when_degraded(self) -> None:
        """delete_dataframe returns False when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        result = await persistence.delete_dataframe("project-123")

        assert result is False


class TestIsAvailable:
    """Tests for is_available property."""

    def test_is_available_false_when_degraded(self) -> None:
        """is_available returns False when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        assert persistence.is_available is False

    def test_is_available_false_when_boto3_unavailable(self) -> None:
        """is_available returns False when boto3 is unavailable."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = None

        assert persistence.is_available is False

    def test_is_available_false_when_polars_unavailable(self) -> None:
        """is_available returns False when polars is unavailable."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()
            persistence._polars_module = None

        assert persistence.is_available is False

    def test_is_available_false_when_disabled(self) -> None:
        """is_available returns False when persistence is disabled."""
        config = PersistenceConfig(bucket="test-bucket", enabled=False)

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()
            persistence._polars_module = MagicMock()

        # Even with mocked modules, is_available checks config.enabled
        assert persistence.is_available is False


class TestGetWatermarkOnly:
    """Tests for get_watermark_only method."""

    @pytest.mark.asyncio
    async def test_get_watermark_only_returns_none_when_degraded(self) -> None:
        """get_watermark_only returns None when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        watermark = await persistence.get_watermark_only("project-123")

        assert watermark is None


class TestListPersistedProjects:
    """Tests for list_persisted_projects method."""

    @pytest.mark.asyncio
    async def test_list_persisted_projects_returns_empty_when_degraded(self) -> None:
        """list_persisted_projects returns empty list when degraded."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        projects = await persistence.list_persisted_projects()

        assert projects == []


class TestDegradedModeRecovery:
    """Tests for degraded mode and recovery behavior."""

    def test_reconnect_interval_respected(self) -> None:
        """Reconnection attempts are rate-limited."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True
            persistence._boto3_module = MagicMock()
            persistence._last_reconnect_attempt = 0

            # First attempt should trigger reconnection
            with patch.object(persistence, "_initialize_client") as mock_init:
                persistence._attempt_reconnect()
                mock_init.assert_called_once()

                # Immediate retry should not trigger reconnection
                persistence._attempt_reconnect()
                mock_init.assert_called_once()  # Still only once


class TestErrorHandling:
    """Tests for S3 error handling."""

    def test_is_not_found_error_returns_false_without_botocore(self) -> None:
        """_is_not_found_error returns False when botocore unavailable."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._botocore_module = None

        result = persistence._is_not_found_error(RuntimeError("test"))

        assert result is False

    def test_handle_s3_error_enters_degraded_for_connection_errors(self) -> None:
        """Connection errors trigger degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._botocore_module = None

        persistence._handle_s3_error(
            ConnectionError("Connection refused"),
            "save",
            "project-123",
        )

        assert persistence._degraded is True

    def test_handle_s3_error_enters_degraded_for_timeout(self) -> None:
        """Timeout errors trigger degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._botocore_module = None

        persistence._handle_s3_error(
            TimeoutError("Operation timed out"),
            "load",
            "project-123",
        )

        assert persistence._degraded is True


class TestInitialization:
    """Tests for DataFramePersistence initialization."""

    def test_init_with_config(self) -> None:
        """Initialization with PersistenceConfig works."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)

        assert persistence._config == config

    def test_config_stored_correctly(self) -> None:
        """Configuration parameters are stored correctly."""
        config = PersistenceConfig(
            bucket="my-bucket",
            prefix="my-prefix/",
            region="eu-west-1",
            endpoint_url="http://localhost:4566",
            enabled=True,
        )

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)

        assert persistence._config.bucket == "my-bucket"
        assert persistence._config.prefix == "my-prefix/"
        assert persistence._config.region == "eu-west-1"
        assert persistence._config.endpoint_url == "http://localhost:4566"
        assert persistence._config.enabled is True


class TestDegradedModeOperations:
    """Tests for operations in degraded mode."""

    @pytest.mark.asyncio
    async def test_operations_graceful_in_degraded_mode(
        self,
        sample_dataframe: pl.DataFrame,
        sample_watermark: datetime,
    ) -> None:
        """All operations return appropriate values in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        # save returns False
        save_result = await persistence.save_dataframe(
            "project-123",
            sample_dataframe,
            sample_watermark,
        )
        assert save_result is False

        # load returns (None, None)
        df, wm = await persistence.load_dataframe("project-123")
        assert df is None
        assert wm is None

        # delete returns False
        delete_result = await persistence.delete_dataframe("project-123")
        assert delete_result is False

        # get_watermark_only returns None
        wm_only = await persistence.get_watermark_only("project-123")
        assert wm_only is None

        # list returns empty list
        projects = await persistence.list_persisted_projects()
        assert projects == []

        # is_available returns False
        assert persistence.is_available is False


class TestIndexKeyGeneration:
    """Tests for index S3 key generation."""

    def test_make_index_key(self) -> None:
        """Index key follows expected format."""
        config = PersistenceConfig(bucket="bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)

        key = persistence._make_index_key("project-123")

        assert key == "dataframes/project-123/gid_lookup_index.json"

    def test_index_key_with_custom_prefix(self) -> None:
        """Custom prefix is respected in index key generation."""
        config = PersistenceConfig(bucket="bucket", prefix="custom/path/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)

        key = persistence._make_index_key("proj")

        assert key == "custom/path/proj/gid_lookup_index.json"


class TestSaveIndex:
    """Tests for save_index method."""

    @pytest.mark.asyncio
    async def test_save_index_returns_false_when_degraded(self) -> None:
        """save_index returns False when in degraded mode."""
        from datetime import datetime, timezone

        from autom8_asana.services.gid_lookup import GidLookupIndex

        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        # Create a minimal index
        index = GidLookupIndex(
            lookup_dict={"pv1:+17705551234:dental": "123456"},
            created_at=datetime.now(timezone.utc),
        )

        result = await persistence.save_index("project-123", index)

        assert result is False

    @pytest.mark.asyncio
    async def test_save_index_success(self) -> None:
        """save_index uploads JSON to S3 with correct key and content."""
        from datetime import datetime, timezone

        from autom8_asana.services.gid_lookup import GidLookupIndex

        config = PersistenceConfig(bucket="test-bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()

        # Create a minimal index
        created_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        index = GidLookupIndex(
            lookup_dict={"pv1:+17705551234:dental": "123456"},
            created_at=created_at,
        )

        # Mock S3 client
        mock_client = MagicMock()
        persistence._client = mock_client

        result = await persistence.save_index("project-123", index)

        assert result is True
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "dataframes/project-123/gid_lookup_index.json"
        assert call_kwargs["ContentType"] == "application/json"
        assert call_kwargs["Metadata"]["project-gid"] == "project-123"
        assert call_kwargs["Metadata"]["entry-count"] == "1"

    @pytest.mark.asyncio
    async def test_save_index_handles_s3_error(self) -> None:
        """save_index returns False and enters degraded mode on S3 error."""
        from datetime import datetime, timezone

        from autom8_asana.services.gid_lookup import GidLookupIndex

        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()
            persistence._botocore_module = None

        # Create a minimal index
        index = GidLookupIndex(
            lookup_dict={"pv1:+17705551234:dental": "123456"},
            created_at=datetime.now(timezone.utc),
        )

        # Mock S3 client that raises ConnectionError
        mock_client = MagicMock()
        mock_client.put_object.side_effect = ConnectionError("Connection refused")
        persistence._client = mock_client

        result = await persistence.save_index("project-123", index)

        assert result is False
        assert persistence._degraded is True


class TestLoadIndex:
    """Tests for load_index method."""

    @pytest.mark.asyncio
    async def test_load_index_returns_none_when_degraded(self) -> None:
        """load_index returns None when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        index = await persistence.load_index("project-123")

        assert index is None

    @pytest.mark.asyncio
    async def test_load_index_returns_none_when_not_found(self) -> None:
        """load_index returns None when index doesn't exist in S3."""
        import botocore.exceptions

        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._botocore_module = botocore.exceptions

        # Mock S3 client that returns NoSuchKey
        mock_client = MagicMock()
        error_response = {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}
        mock_client.get_object.side_effect = botocore.exceptions.ClientError(
            error_response, "GetObject"
        )
        persistence._client = mock_client

        index = await persistence.load_index("project-123")

        assert index is None

    @pytest.mark.asyncio
    async def test_load_index_success(self) -> None:
        """load_index reconstructs GidLookupIndex from S3 JSON."""
        import json
        from datetime import datetime, timezone

        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()

        # Create serialized index data
        created_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        index_data = {
            "version": "1.0",
            "created_at": created_at.isoformat(),
            "entry_count": 2,
            "lookup": {
                "pv1:+17705551234:dental": "123456",
                "pv1:+17705559999:chiropractic": "789012",
            },
        }

        # Mock S3 client response
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(index_data).encode("utf-8")
        mock_client = MagicMock()
        mock_client.get_object.return_value = {"Body": mock_body}
        persistence._client = mock_client

        index = await persistence.load_index("project-123")

        assert index is not None
        assert len(index) == 2
        assert index.created_at == created_at

    @pytest.mark.asyncio
    async def test_load_index_handles_s3_error(self) -> None:
        """load_index returns None and enters degraded mode on S3 error."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()
            persistence._botocore_module = None

        # Mock S3 client that raises ConnectionError
        mock_client = MagicMock()
        mock_client.get_object.side_effect = ConnectionError("Connection refused")
        persistence._client = mock_client

        index = await persistence.load_index("project-123")

        assert index is None
        assert persistence._degraded is True

    @pytest.mark.asyncio
    async def test_load_index_handles_invalid_json(self) -> None:
        """load_index returns None on invalid JSON data."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()
            persistence._botocore_module = None

        # Mock S3 client with invalid JSON
        mock_body = MagicMock()
        mock_body.read.return_value = b"not valid json"
        mock_client = MagicMock()
        mock_client.get_object.return_value = {"Body": mock_body}
        persistence._client = mock_client

        index = await persistence.load_index("project-123")

        assert index is None


class TestDeleteIndex:
    """Tests for delete_index method."""

    @pytest.mark.asyncio
    async def test_delete_index_returns_false_when_degraded(self) -> None:
        """delete_index returns False when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        result = await persistence.delete_index("project-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_index_success(self) -> None:
        """delete_index removes index from S3."""
        config = PersistenceConfig(bucket="test-bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()

        # Mock S3 client
        mock_client = MagicMock()
        persistence._client = mock_client

        result = await persistence.delete_index("project-123")

        assert result is True
        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="dataframes/project-123/gid_lookup_index.json",
        )

    @pytest.mark.asyncio
    async def test_delete_index_handles_s3_error(self) -> None:
        """delete_index returns False and enters degraded mode on S3 error."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()
            persistence._botocore_module = None

        # Mock S3 client that raises ConnectionError
        mock_client = MagicMock()
        mock_client.delete_object.side_effect = ConnectionError("Connection refused")
        persistence._client = mock_client

        result = await persistence.delete_index("project-123")

        assert result is False
        assert persistence._degraded is True


class TestIndexRoundTrip:
    """Tests for save/load round-trip functionality."""

    @pytest.mark.asyncio
    async def test_save_and_load_preserves_data(self) -> None:
        """Round-trip through save/load preserves all index data."""
        from datetime import datetime, timezone

        from autom8_asana.services.gid_lookup import GidLookupIndex

        config = PersistenceConfig(bucket="test-bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()  # Required for _get_client()

        # Create index with multiple entries
        created_at = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        original_index = GidLookupIndex(
            lookup_dict={
                "pv1:+17705551234:dental": "123456",
                "pv1:+17705559999:chiropractic": "789012",
                "pv1:+14045551111:orthodontics": "345678",
            },
            created_at=created_at,
        )

        # Capture what would be written to S3
        captured_body: bytes | None = None

        def capture_put(**kwargs):  # noqa: ANN003, ANN202
            nonlocal captured_body
            captured_body = kwargs["Body"]

        mock_client = MagicMock()
        mock_client.put_object.side_effect = capture_put
        persistence._client = mock_client

        # Save
        result = await persistence.save_index("project-123", original_index)
        assert result is True
        assert captured_body is not None

        # Mock load to return what was saved
        mock_body = MagicMock()
        mock_body.read.return_value = captured_body
        mock_client.get_object.return_value = {"Body": mock_body}

        # Load
        loaded_index = await persistence.load_index("project-123")

        # Verify round-trip
        assert loaded_index is not None
        assert len(loaded_index) == len(original_index)
        assert loaded_index.created_at == original_index.created_at
        assert loaded_index == original_index


class TestIndexDegradedModeOperations:
    """Tests for index operations in degraded mode."""

    @pytest.mark.asyncio
    async def test_all_index_operations_graceful_in_degraded_mode(self) -> None:
        """All index operations return appropriate values in degraded mode."""
        from datetime import datetime, timezone

        from autom8_asana.services.gid_lookup import GidLookupIndex

        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        # Create a minimal index for save test
        index = GidLookupIndex(
            lookup_dict={"pv1:+17705551234:dental": "123456"},
            created_at=datetime.now(timezone.utc),
        )

        # save_index returns False
        save_result = await persistence.save_index("project-123", index)
        assert save_result is False

        # load_index returns None
        loaded = await persistence.load_index("project-123")
        assert loaded is None

        # delete_index returns False
        delete_result = await persistence.delete_index("project-123")
        assert delete_result is False


class TestSaveWatermark:
    """Tests for save_watermark method."""

    @pytest.mark.asyncio
    async def test_save_watermark_rejects_naive_datetime(self) -> None:
        """save_watermark raises ValueError for naive datetime."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False

        naive_dt = datetime(2024, 6, 15)  # No tzinfo

        with pytest.raises(ValueError, match="timezone-aware"):
            await persistence.save_watermark("project-123", naive_dt)

    @pytest.mark.asyncio
    async def test_save_watermark_returns_false_when_degraded(
        self,
        sample_watermark: datetime,
    ) -> None:
        """save_watermark returns False when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        result = await persistence.save_watermark("project-123", sample_watermark)

        assert result is False

    @pytest.mark.asyncio
    async def test_save_watermark_success(
        self,
        sample_watermark: datetime,
    ) -> None:
        """save_watermark uploads JSON to S3 with correct key and content."""
        import json

        config = PersistenceConfig(bucket="test-bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()

        # Mock S3 client
        mock_client = MagicMock()
        persistence._client = mock_client

        result = await persistence.save_watermark("project-123", sample_watermark)

        assert result is True
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "dataframes/project-123/watermark.json"
        assert call_kwargs["ContentType"] == "application/json"

        # Verify JSON content
        body = json.loads(call_kwargs["Body"].decode("utf-8"))
        assert body["project_gid"] == "project-123"
        assert body["watermark"] == sample_watermark.isoformat()
        assert "saved_at" in body

    @pytest.mark.asyncio
    async def test_save_watermark_handles_s3_error(
        self,
        sample_watermark: datetime,
    ) -> None:
        """save_watermark returns False on S3 error."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()
            persistence._botocore_module = None

        # Mock S3 client that raises ConnectionError
        mock_client = MagicMock()
        mock_client.put_object.side_effect = ConnectionError("Connection refused")
        persistence._client = mock_client

        result = await persistence.save_watermark("project-123", sample_watermark)

        assert result is False
        assert persistence._degraded is True


class TestLoadAllWatermarks:
    """Tests for load_all_watermarks method."""

    @pytest.mark.asyncio
    async def test_load_all_watermarks_returns_empty_when_degraded(self) -> None:
        """load_all_watermarks returns empty dict when in degraded mode."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        result = await persistence.load_all_watermarks()

        assert result == {}

    @pytest.mark.asyncio
    async def test_load_all_watermarks_returns_empty_when_no_projects(self) -> None:
        """load_all_watermarks returns empty dict when no persisted projects."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()

        # Mock S3 client with empty list
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"CommonPrefixes": []}]
        mock_client.get_paginator.return_value = mock_paginator
        persistence._client = mock_client

        result = await persistence.load_all_watermarks()

        assert result == {}

    @pytest.mark.asyncio
    async def test_load_all_watermarks_loads_multiple_projects(self) -> None:
        """load_all_watermarks loads watermarks from all persisted projects."""
        import json

        config = PersistenceConfig(bucket="test-bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()

        # Mock watermarks
        wm1 = datetime(2024, 1, 15, tzinfo=timezone.utc)
        wm2 = datetime(2024, 6, 20, tzinfo=timezone.utc)

        watermark_responses = {
            "dataframes/proj-1/watermark.json": {
                "watermark": wm1.isoformat(),
                "project_gid": "proj-1",
            },
            "dataframes/proj-2/watermark.json": {
                "watermark": wm2.isoformat(),
                "project_gid": "proj-2",
            },
        }

        def mock_get_object(Bucket, Key):  # noqa: N803
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps(watermark_responses[Key]).encode(
                "utf-8"
            )
            return {"Body": mock_body}

        # Mock S3 client
        mock_client = MagicMock()

        # Mock list_persisted_projects to return projects
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "CommonPrefixes": [
                    {"Prefix": "dataframes/proj-1/"},
                    {"Prefix": "dataframes/proj-2/"},
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_client.get_object.side_effect = mock_get_object
        persistence._client = mock_client

        result = await persistence.load_all_watermarks()

        assert len(result) == 2
        assert result["proj-1"] == wm1
        assert result["proj-2"] == wm2

    @pytest.mark.asyncio
    async def test_load_all_watermarks_handles_missing_watermark(self) -> None:
        """load_all_watermarks skips projects with missing watermark files."""
        import botocore.exceptions
        import json

        config = PersistenceConfig(bucket="test-bucket", prefix="dataframes/")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()
            persistence._botocore_module = botocore.exceptions

        # Mock watermarks - one exists, one doesn't
        wm1 = datetime(2024, 1, 15, tzinfo=timezone.utc)

        def mock_get_object(Bucket, Key):  # noqa: N803
            if Key == "dataframes/proj-1/watermark.json":
                mock_body = MagicMock()
                mock_body.read.return_value = json.dumps(
                    {
                        "watermark": wm1.isoformat(),
                        "project_gid": "proj-1",
                    }
                ).encode("utf-8")
                return {"Body": mock_body}
            else:
                error_response = {
                    "Error": {"Code": "NoSuchKey", "Message": "Not found"}
                }
                raise botocore.exceptions.ClientError(error_response, "GetObject")

        # Mock S3 client
        mock_client = MagicMock()

        # Mock list_persisted_projects to return projects
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "CommonPrefixes": [
                    {"Prefix": "dataframes/proj-1/"},
                    {"Prefix": "dataframes/proj-missing/"},
                ]
            }
        ]
        mock_client.get_paginator.return_value = mock_paginator
        mock_client.get_object.side_effect = mock_get_object
        persistence._client = mock_client

        result = await persistence.load_all_watermarks()

        # Should only have the project with a valid watermark
        assert len(result) == 1
        assert result["proj-1"] == wm1

    @pytest.mark.asyncio
    async def test_load_all_watermarks_handles_error_gracefully(self) -> None:
        """load_all_watermarks returns empty dict on S3 error."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = False
            persistence._boto3_module = MagicMock()
            persistence._botocore_module = None

        # Mock S3 client that raises ConnectionError
        mock_client = MagicMock()
        mock_client.get_paginator.side_effect = ConnectionError("Connection refused")
        persistence._client = mock_client

        result = await persistence.load_all_watermarks()

        assert result == {}


class TestWatermarkPersistenceDegradedMode:
    """Tests for watermark persistence in degraded mode."""

    @pytest.mark.asyncio
    async def test_all_watermark_operations_graceful_in_degraded_mode(
        self,
        sample_watermark: datetime,
    ) -> None:
        """All watermark persistence operations return appropriate values."""
        config = PersistenceConfig(bucket="test-bucket")

        with patch.object(DataFramePersistence, "_initialize_modules"):
            persistence = DataFramePersistence(config=config)
            persistence._degraded = True

        # save_watermark returns False
        save_result = await persistence.save_watermark("project-123", sample_watermark)
        assert save_result is False

        # load_all_watermarks returns empty dict
        watermarks = await persistence.load_all_watermarks()
        assert watermarks == {}
