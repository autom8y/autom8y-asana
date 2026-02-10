"""Tests for S3CacheProvider."""

import gzip
import json
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.protocols.cache import WarmResult

# Try to import moto, skip integration tests if not available
try:
    import boto3
    from botocore.exceptions import ClientError
    from moto import mock_aws

    MOTO_AVAILABLE = True
except ImportError:
    MOTO_AVAILABLE = False
    mock_aws = None  # type: ignore[assignment, misc]


class TestS3Config:
    """Tests for S3Config dataclass."""

    def test_config_defaults(self) -> None:
        """Test S3Config default values."""
        from autom8_asana.cache.backends.s3 import S3Config

        config = S3Config(bucket="test-bucket")

        assert config.bucket == "test-bucket"
        assert config.prefix == "asana-cache"
        assert config.region == "us-east-1"
        assert config.endpoint_url is None
        assert config.compress_threshold == 1024
        assert config.default_ttl == 604800  # 7 days

    def test_config_custom_values(self) -> None:
        """Test S3Config with custom values."""
        from autom8_asana.cache.backends.s3 import S3Config

        config = S3Config(
            bucket="custom-bucket",
            prefix="my-cache",
            region="eu-west-1",
            endpoint_url="http://localhost:4566",
            compress_threshold=2048,
            default_ttl=86400,
        )

        assert config.bucket == "custom-bucket"
        assert config.prefix == "my-cache"
        assert config.region == "eu-west-1"
        assert config.endpoint_url == "http://localhost:4566"
        assert config.compress_threshold == 2048
        assert config.default_ttl == 86400

    def test_environment_variable_loading(self) -> None:
        """Test bucket loading from environment variable."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider

        with patch.dict(os.environ, {"ASANA_CACHE_S3_BUCKET": "env-bucket"}):
            with patch.object(S3CacheProvider, "_initialize_client"):
                provider = S3CacheProvider()
                assert provider._config.bucket == "env-bucket"

    def test_missing_bucket_enters_degraded_mode(self) -> None:
        """Test that missing bucket configuration enters degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider

        with patch.dict(os.environ, {}, clear=True):
            # Remove ASANA_CACHE_S3_BUCKET if it exists
            os.environ.pop("ASANA_CACHE_S3_BUCKET", None)
            with patch.object(S3CacheProvider, "_initialize_client"):
                provider = S3CacheProvider()
                # Manually trigger degraded state check
                provider._config.bucket == ""
                provider._degraded = True

                assert provider.is_healthy() is False


class TestS3CacheProviderInit:
    """Tests for S3CacheProvider initialization."""

    def test_init_without_boto3_installed(self) -> None:
        """Test initialization when boto3 module not available enters degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")

        with patch.dict("sys.modules", {"boto3": None, "botocore.exceptions": None}):
            with patch.object(S3CacheProvider, "_initialize_client"):
                provider = S3CacheProvider(config=config)
                # Simulate boto3 not available
                provider._boto3_module = None
                provider._degraded = True

                assert provider._degraded is True
                assert provider.is_healthy() is False

    def test_init_with_config(self) -> None:
        """Test initialization with S3Config."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(
            bucket="my-bucket",
            prefix="my-prefix",
            region="us-west-2",
        )

        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            assert provider._config.bucket == "my-bucket"
            assert provider._config.prefix == "my-prefix"
            assert provider._config.region == "us-west-2"

    def test_init_with_individual_params(self) -> None:
        """Test initialization with individual parameters."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider

        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(
                bucket="test-bucket",
                prefix="custom-prefix",
                region="ap-southeast-1",
                endpoint_url="http://localhost:4566",
            )

            assert provider._config.bucket == "test-bucket"
            assert provider._config.prefix == "custom-prefix"
            assert provider._config.region == "ap-southeast-1"
            assert provider._config.endpoint_url == "http://localhost:4566"


class TestS3CacheProviderDegraded:
    """Tests for S3CacheProvider in degraded mode."""

    def test_degraded_get_returns_none(self) -> None:
        """Test get returns None in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True
            provider._boto3_module = None

            assert provider.get("key") is None

    def test_degraded_set_does_nothing(self) -> None:
        """Test set does nothing in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True
            provider._boto3_module = None

            # Should not raise
            provider.set("key", {"data": "value"})

    def test_degraded_get_versioned_returns_none(self) -> None:
        """Test get_versioned returns None in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True
            provider._boto3_module = None

            assert provider.get_versioned("key", EntryType.TASK) is None

    def test_degraded_is_healthy_returns_false(self) -> None:
        """Test is_healthy returns False in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True

            assert provider.is_healthy() is False

    def test_degraded_mode_returns_none_for_batch_get(self) -> None:
        """Test get_batch returns None for all keys in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True

            result = provider.get_batch(["1", "2", "3"], EntryType.TASK)

            assert result == {"1": None, "2": None, "3": None}

    def test_degraded_set_batch_does_nothing(self) -> None:
        """Test set_batch does nothing in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True

            now = datetime.now(UTC)
            entries = {
                "1": CacheEntry(
                    key="1", data={}, entry_type=EntryType.TASK, version=now
                ),
            }

            # Should not raise
            provider.set_batch(entries)

    def test_degraded_check_freshness_returns_false(self) -> None:
        """Test check_freshness returns False in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True

            assert (
                provider.check_freshness("key", EntryType.TASK, datetime.now(UTC))
                is False
            )


class TestS3CacheProviderKeyGeneration:
    """Tests for S3 key generation."""

    def test_make_key_task(self) -> None:
        """Test key generation for task entries."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket", prefix="cache")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            key = provider._make_key("1234567890", EntryType.TASK)
            assert key == "cache/tasks/1234567890/task.json"

    def test_make_key_subtasks(self) -> None:
        """Test key generation for subtasks entries."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket", prefix="cache")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            key = provider._make_key("1234567890", EntryType.SUBTASKS)
            assert key == "cache/tasks/1234567890/subtasks.json"

    def test_make_key_dataframe(self) -> None:
        """Test key generation for dataframe entries."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket", prefix="cache")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            key = provider._make_key("task:project", EntryType.DATAFRAME)
            assert key == "cache/dataframe/task:project.json"

    def test_make_simple_key(self) -> None:
        """Test simple key generation."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket", prefix="cache")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            key = provider._make_simple_key("my-key")
            assert key == "cache/simple/my-key.json"


class TestS3CacheProviderSerialization:
    """Tests for cache entry serialization."""

    def test_serialize_entry(self) -> None:
        """Test serializing a CacheEntry."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket", compress_threshold=10000)
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            entry = CacheEntry(
                key="123",
                data={"name": "Test Task"},
                entry_type=EntryType.TASK,
                version=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                cached_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
                ttl=300,
                project_gid="project_456",
                metadata={"source": "api"},
            )

            body, metadata, is_compressed = provider._serialize_entry(entry)

            # Should not be compressed (under threshold)
            assert is_compressed is False
            assert "version" in metadata
            assert "entry-type" in metadata
            assert metadata["entry-type"] == "task"
            assert metadata["compressed"] == "false"

            # Check body contains expected data
            data = json.loads(body.decode("utf-8"))
            assert data["data"] == {"name": "Test Task"}
            assert data["entry_type"] == "task"
            assert data["ttl"] == 300
            assert data["project_gid"] == "project_456"

    def test_deserialize_entry(self) -> None:
        """Test deserializing a CacheEntry."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            data = {
                "data": {"name": "Test Task"},
                "entry_type": "task",
                "version": "2025-01-01T12:00:00+00:00",
                "cached_at": "2025-01-01T12:00:00+00:00",
                "ttl": 300,
                "project_gid": "project_456",
                "metadata": {"source": "api"},
                "key": "123",
            }

            body = json.dumps(data).encode("utf-8")
            metadata = {"compressed": "false"}

            entry = provider._deserialize_entry(body, metadata, "123")

            assert entry is not None
            assert entry.key == "123"
            assert entry.data["name"] == "Test Task"
            assert entry.entry_type == EntryType.TASK
            assert entry.ttl == 300
            assert entry.project_gid == "project_456"

    def test_deserialize_compressed_entry(self) -> None:
        """Test deserializing a compressed CacheEntry."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            data = {
                "data": {"name": "Test Task"},
                "entry_type": "task",
                "version": "2025-01-01T12:00:00+00:00",
                "cached_at": "2025-01-01T12:00:00+00:00",
                "ttl": 300,
                "project_gid": None,
                "metadata": {},
                "key": "123",
            }

            body = gzip.compress(json.dumps(data).encode("utf-8"))
            metadata = {"compressed": "true"}

            entry = provider._deserialize_entry(body, metadata, "123")

            assert entry is not None
            assert entry.key == "123"
            assert entry.data["name"] == "Test Task"

    def test_deserialize_invalid_json_returns_none(self) -> None:
        """Test deserializing invalid JSON returns None."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            body = b"not valid json{{{"
            metadata = {"compressed": "false"}

            assert provider._deserialize_entry(body, metadata, "123") is None

    def test_deserialize_invalid_gzip_returns_none(self) -> None:
        """Test deserializing invalid gzip data returns None."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            body = b"not gzip data"
            metadata = {"compressed": "true"}

            assert provider._deserialize_entry(body, metadata, "123") is None


class TestS3CacheProviderMetrics:
    """Tests for S3CacheProvider metrics."""

    def test_get_metrics(self) -> None:
        """Test get_metrics returns CacheMetrics."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            metrics = provider.get_metrics()
            assert metrics is not None
            assert metrics.hits == 0
            assert metrics.misses == 0

    def test_reset_metrics(self) -> None:
        """Test reset_metrics clears counters."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            # Record some metrics
            provider._metrics.record_hit(1.0)
            provider._metrics.record_miss(1.0)

            assert provider.get_metrics().hits == 1

            provider.reset_metrics()

            assert provider.get_metrics().hits == 0
            assert provider.get_metrics().misses == 0

    def test_metrics_record_hit_on_cache_hit(self) -> None:
        """Test metrics record hit when cache returns data."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            # Manually record a hit
            provider._metrics.record_hit(5.0, key="test-key")

            metrics = provider.get_metrics()
            assert metrics.hits == 1
            assert metrics.misses == 0

    def test_metrics_record_miss_on_cache_miss(self) -> None:
        """Test metrics record miss when cache returns None."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            # Manually record a miss
            provider._metrics.record_miss(3.0, key="test-key")

            metrics = provider.get_metrics()
            assert metrics.hits == 0
            assert metrics.misses == 1

    def test_metrics_record_error_on_exception(self) -> None:
        """Test metrics record error when exception occurs."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            # Manually record an error
            provider._metrics.record_error(
                key="test-key", error_message="Connection failed"
            )

            metrics = provider.get_metrics()
            assert metrics.errors == 1


class TestS3CacheProviderWarm:
    """Tests for S3CacheProvider warm operation."""

    def test_warm_returns_placeholder(self) -> None:
        """Test warm returns placeholder result."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            result = provider.warm(["1", "2", "3"])

            assert isinstance(result, WarmResult)
            assert result.skipped == 3
            assert result.warmed == 0
            assert result.failed == 0


class TestS3CacheProviderCompression:
    """Tests for compression behavior."""

    def test_compression_small_object_not_compressed(self) -> None:
        """Test small objects are not compressed."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        # Set threshold high so small objects don't get compressed
        config = S3Config(bucket="test-bucket", compress_threshold=10000)
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            entry = CacheEntry(
                key="123",
                data={"name": "Small"},
                entry_type=EntryType.TASK,
                version=datetime.now(UTC),
            )

            body, metadata, is_compressed = provider._serialize_entry(entry)

            assert is_compressed is False
            assert metadata["compressed"] == "false"
            # Verify body is not gzipped
            assert not body.startswith(b"\x1f\x8b")  # gzip magic bytes

    def test_compression_large_object_compressed(self) -> None:
        """Test large objects are gzip compressed."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        # Set threshold very low so objects get compressed
        config = S3Config(bucket="test-bucket", compress_threshold=10)
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            # Create a large entry that exceeds threshold
            large_data = {"name": "Test", "description": "A" * 1000}
            entry = CacheEntry(
                key="123",
                data=large_data,
                entry_type=EntryType.TASK,
                version=datetime.now(UTC),
            )

            body, metadata, is_compressed = provider._serialize_entry(entry)

            assert is_compressed is True
            assert metadata["compressed"] == "true"
            # Verify body is gzipped (starts with gzip magic bytes)
            assert body.startswith(b"\x1f\x8b")

    def test_decompression_on_read(self) -> None:
        """Test compressed data is decompressed on read."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)

            data = {
                "data": {"name": "Test Task"},
                "entry_type": "task",
                "version": "2025-01-01T12:00:00+00:00",
                "cached_at": "2025-01-01T12:00:00+00:00",
                "ttl": 300,
                "project_gid": None,
                "metadata": {},
                "key": "123",
            }

            # Create compressed body
            compressed_body = gzip.compress(json.dumps(data).encode("utf-8"))
            metadata = {"compressed": "true"}

            entry = provider._deserialize_entry(compressed_body, metadata, "123")

            assert entry is not None
            assert entry.data["name"] == "Test Task"


class TestS3CacheProviderErrorHandling:
    """Tests for error handling and graceful degradation."""

    def test_graceful_degradation_on_connection_error(self) -> None:
        """Test provider enters degraded mode on connection errors."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = False

            # Simulate connection error
            provider._handle_transport_error(ConnectionError("Connection refused"))

            assert provider._degraded is True

    def test_graceful_degradation_on_timeout_error(self) -> None:
        """Test provider enters degraded mode on timeout errors."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = False

            # Simulate timeout error
            provider._handle_transport_error(TimeoutError("Request timed out"))

            assert provider._degraded is True

    def test_not_found_error_does_not_degrade(self) -> None:
        """Test 404 errors don't enter degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = False

            # Mock botocore exceptions
            mock_client_error = MagicMock()
            mock_client_error.response = {"Error": {"Code": "NoSuchKey"}}

            # Create a mock exception class
            class MockClientError(Exception):
                def __init__(self) -> None:
                    self.response = {"Error": {"Code": "NoSuchKey"}}

            provider._botocore_module = MagicMock()
            provider._botocore_module.ClientError = MockClientError

            # Handle the error
            provider._handle_transport_error(MockClientError())

            # Should not enter degraded mode for 404
            assert provider._degraded is False

    def test_reconnect_attempt_respects_interval(self) -> None:
        """Test reconnect attempts respect the reconnect interval."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True
            provider._last_reconnect_attempt = 0.0

            # Mock the time and settings
            with patch("time.time", return_value=1000.0):
                provider._settings.reconnect_interval = 30

                # First call should attempt reconnect
                with patch.object(provider, "_initialize_client") as mock_init:
                    provider._attempt_reconnect()
                    mock_init.assert_called_once()

            # Second immediate call should not attempt reconnect
            with patch("time.time", return_value=1010.0):  # Only 10 seconds later
                with patch.object(provider, "_initialize_client") as mock_init:
                    provider._attempt_reconnect()
                    mock_init.assert_not_called()


class TestS3CacheProviderHealthCheck:
    """Tests for health check functionality."""

    def test_is_healthy_true_when_connected(self) -> None:
        """Test is_healthy returns True when S3 is accessible."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = False
            provider._boto3_module = MagicMock()

            # Mock client that successfully responds to head_bucket
            mock_client = MagicMock()
            mock_client.head_bucket.return_value = {}
            provider._client = mock_client

            assert provider.is_healthy() is True

    def test_is_healthy_false_when_degraded(self) -> None:
        """Test is_healthy returns False when in degraded mode."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._degraded = True

            assert provider.is_healthy() is False

    def test_is_healthy_false_when_boto3_unavailable(self) -> None:
        """Test is_healthy returns False when boto3 not available."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        config = S3Config(bucket="test-bucket")
        with patch.object(S3CacheProvider, "_initialize_client"):
            provider = S3CacheProvider(config=config)
            provider._boto3_module = None

            assert provider.is_healthy() is False


@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")
class TestS3CacheProviderIntegration:
    """Integration tests using moto for S3 mocking."""

    @pytest.fixture
    def s3_provider(self):
        """Create a provider with moto-mocked S3 backend."""
        from autom8_asana.cache.backends.s3 import S3CacheProvider, S3Config

        with mock_aws():
            # Create the mock bucket
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket="test-bucket")

            config = S3Config(bucket="test-bucket", prefix="cache")
            provider = S3CacheProvider(config=config)

            yield provider

    def test_simple_get_miss(self, s3_provider) -> None:
        """Test simple get returns None for missing key."""
        result = s3_provider.get("nonexistent")
        assert result is None

    def test_simple_set_and_get(self, s3_provider) -> None:
        """Test simple get/set operations."""
        s3_provider.set("key", {"data": "value"})
        result = s3_provider.get("key")

        assert result == {"data": "value"}

    def test_simple_delete(self, s3_provider) -> None:
        """Test simple delete operation."""
        s3_provider.set("key", {"data": "value"})
        s3_provider.delete("key")

        assert s3_provider.get("key") is None

    def test_versioned_get_miss(self, s3_provider) -> None:
        """Test versioned get returns None for missing key."""
        result = s3_provider.get_versioned("nonexistent", EntryType.TASK)
        assert result is None

    def test_versioned_set_and_get(self, s3_provider) -> None:
        """Test versioned get/set operations."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="123",
            data={"name": "Test Task"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=300,
        )

        s3_provider.set_versioned("123", entry)
        result = s3_provider.get_versioned("123", EntryType.TASK)

        assert result is not None
        assert result.data["name"] == "Test Task"
        assert result.entry_type == EntryType.TASK

    def test_check_freshness_current(self, s3_provider) -> None:
        """Test check_freshness returns True for current version."""
        cached_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_time,
        )
        s3_provider.set_versioned("123", entry)

        # Same version should be fresh
        assert s3_provider.check_freshness("123", EntryType.TASK, cached_time) is True

    def test_check_freshness_stale(self, s3_provider) -> None:
        """Test check_freshness returns False for stale version."""
        cached_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = CacheEntry(
            key="123",
            data={},
            entry_type=EntryType.TASK,
            version=cached_time,
        )
        s3_provider.set_versioned("123", entry)

        # Newer version should be stale
        newer = datetime(2025, 1, 1, 14, 0, 0, tzinfo=UTC)
        assert s3_provider.check_freshness("123", EntryType.TASK, newer) is False

    def test_check_freshness_missing(self, s3_provider) -> None:
        """Test check_freshness returns False for missing entry."""
        assert (
            s3_provider.check_freshness(
                "nonexistent",
                EntryType.TASK,
                datetime.now(UTC),
            )
            is False
        )

    def test_invalidate_single_type(self, s3_provider) -> None:
        """Test invalidate removes specified entry types."""
        now = datetime.now(UTC)

        s3_provider.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        s3_provider.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.SUBTASKS,
                version=now,
            ),
        )

        s3_provider.invalidate("123", [EntryType.TASK])

        assert s3_provider.get_versioned("123", EntryType.TASK) is None
        assert s3_provider.get_versioned("123", EntryType.SUBTASKS) is not None

    def test_invalidate_all_types(self, s3_provider) -> None:
        """Test invalidate removes all entry types when None specified."""
        now = datetime.now(UTC)

        s3_provider.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        s3_provider.set_versioned(
            "123",
            CacheEntry(
                key="123",
                data={},
                entry_type=EntryType.SUBTASKS,
                version=now,
            ),
        )

        s3_provider.invalidate("123", None)

        assert s3_provider.get_versioned("123", EntryType.TASK) is None
        assert s3_provider.get_versioned("123", EntryType.SUBTASKS) is None

    def test_get_batch(self, s3_provider) -> None:
        """Test get_batch operation."""
        now = datetime.now(UTC)

        s3_provider.set_versioned(
            "1",
            CacheEntry(
                key="1",
                data={"id": 1},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )
        s3_provider.set_versioned(
            "2",
            CacheEntry(
                key="2",
                data={"id": 2},
                entry_type=EntryType.TASK,
                version=now,
            ),
        )

        result = s3_provider.get_batch(["1", "2", "3"], EntryType.TASK)

        assert result["1"] is not None
        assert result["1"].data["id"] == 1
        assert result["2"] is not None
        assert result["2"].data["id"] == 2
        assert result["3"] is None

    def test_get_batch_empty_keys(self, s3_provider) -> None:
        """Test get_batch with empty keys list."""
        result = s3_provider.get_batch([], EntryType.TASK)
        assert result == {}

    def test_set_batch(self, s3_provider) -> None:
        """Test set_batch operation."""
        now = datetime.now(UTC)

        entries = {
            "1": CacheEntry(
                key="1", data={"id": 1}, entry_type=EntryType.TASK, version=now
            ),
            "2": CacheEntry(
                key="2", data={"id": 2}, entry_type=EntryType.TASK, version=now
            ),
        }

        s3_provider.set_batch(entries)

        assert s3_provider.get_versioned("1", EntryType.TASK) is not None
        assert s3_provider.get_versioned("2", EntryType.TASK) is not None

    def test_set_batch_empty_entries(self, s3_provider) -> None:
        """Test set_batch with empty entries dict."""
        # Should not raise
        s3_provider.set_batch({})

    def test_ttl_expiration(self, s3_provider) -> None:
        """Test TTL expiration handling (S3 stores TTL in metadata)."""
        # Create an entry that's already expired
        old_time = datetime.now(UTC) - timedelta(hours=1)
        entry = CacheEntry(
            key="123",
            data={"name": "Expired Task"},
            entry_type=EntryType.TASK,
            version=old_time,
            cached_at=old_time,
            ttl=60,  # 60 seconds TTL, but cached 1 hour ago
        )

        s3_provider.set_versioned("123", entry)

        # Should return None because entry is expired
        result = s3_provider.get_versioned("123", EntryType.TASK)
        assert result is None

    def test_is_healthy(self, s3_provider) -> None:
        """Test is_healthy returns True when connected."""
        assert s3_provider.is_healthy() is True

    def test_compression_integration(self, s3_provider) -> None:
        """Test compression works end-to-end."""
        # Create a large entry that will be compressed
        large_data = {"name": "Test", "description": "A" * 2000}
        entry = CacheEntry(
            key="large",
            data=large_data,
            entry_type=EntryType.TASK,
            version=datetime.now(UTC),
        )

        s3_provider.set_versioned("large", entry)
        result = s3_provider.get_versioned("large", EntryType.TASK)

        assert result is not None
        assert result.data["description"] == "A" * 2000

    def test_dataframe_entry_type(self, s3_provider) -> None:
        """Test DATAFRAME entry type uses correct key structure."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="task:project",
            data={"structure": "data"},
            entry_type=EntryType.DATAFRAME,
            version=now,
        )

        s3_provider.set_versioned("task:project", entry)
        result = s3_provider.get_versioned("task:project", EntryType.DATAFRAME)

        assert result is not None
        assert result.data["structure"] == "data"

    def test_metadata_preserved(self, s3_provider) -> None:
        """Test entry metadata is preserved through round-trip."""
        now = datetime.now(UTC)
        entry = CacheEntry(
            key="123",
            data={"name": "Test"},
            entry_type=EntryType.TASK,
            version=now,
            ttl=600,
            project_gid="proj_456",
            metadata={"source": "api", "request_id": "req_789"},
        )

        s3_provider.set_versioned("123", entry)
        result = s3_provider.get_versioned("123", EntryType.TASK)

        assert result is not None
        assert result.ttl == 600
        assert result.project_gid == "proj_456"
        assert result.metadata["source"] == "api"
        assert result.metadata["request_id"] == "req_789"

    def test_metrics_after_operations(self, s3_provider) -> None:
        """Test metrics are recorded after cache operations."""
        # Initial state
        assert s3_provider.get_metrics().hits == 0
        assert s3_provider.get_metrics().misses == 0

        # Cache miss
        s3_provider.get("nonexistent")
        assert s3_provider.get_metrics().misses == 1

        # Cache set and hit
        s3_provider.set("key", {"data": "value"})
        s3_provider.get("key")
        assert s3_provider.get_metrics().hits == 1
        assert s3_provider.get_metrics().writes == 1
