"""Unit tests for AsyncS3Client.

Tests the async S3 client wrapper for progressive cache warming.
Uses mocking for boto3 operations.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.dataframes.async_s3 import (
    AsyncS3Client,
    AsyncS3Config,
    S3ReadResult,
    S3WriteResult,
)


class TestAsyncS3Config:
    """Tests for AsyncS3Config dataclass."""

    def test_default_values(self) -> None:
        """Config has sensible defaults."""
        config = AsyncS3Config(bucket="test-bucket")

        assert config.bucket == "test-bucket"
        assert config.region == "us-east-1"
        assert config.endpoint_url is None
        assert config.max_retries == 3
        assert config.base_retry_delay == 0.5

    def test_custom_values(self) -> None:
        """Config accepts custom values."""
        config = AsyncS3Config(
            bucket="custom-bucket",
            region="eu-west-1",
            endpoint_url="http://localhost:4566",
            max_retries=5,
            base_retry_delay=1.0,
        )

        assert config.bucket == "custom-bucket"
        assert config.region == "eu-west-1"
        assert config.endpoint_url == "http://localhost:4566"
        assert config.max_retries == 5
        assert config.base_retry_delay == 1.0


class TestS3WriteResult:
    """Tests for S3WriteResult dataclass."""

    def test_success_result(self) -> None:
        """Successful write result calculates throughput."""
        result = S3WriteResult(
            success=True,
            key="test/key.json",
            size_bytes=1024 * 1024,  # 1 MB
            duration_ms=1000,  # 1 second
            etag="abc123",
        )

        assert result.success is True
        assert result.key == "test/key.json"
        assert result.size_bytes == 1024 * 1024
        assert result.throughput_mbps == pytest.approx(1.0, rel=0.01)
        assert result.etag == "abc123"
        assert result.error is None

    def test_failure_result(self) -> None:
        """Failed write result has error."""
        result = S3WriteResult(
            success=False,
            key="test/key.json",
            size_bytes=0,
            duration_ms=100,
            error="Access denied",
        )

        assert result.success is False
        assert result.error == "Access denied"
        assert result.throughput_mbps == 0.0

    def test_zero_duration_no_divide_by_zero(self) -> None:
        """Zero duration doesn't cause divide by zero."""
        result = S3WriteResult(
            success=True,
            key="test/key.json",
            size_bytes=1024,
            duration_ms=0,
        )

        assert result.throughput_mbps == 0.0


class TestS3ReadResult:
    """Tests for S3ReadResult dataclass."""

    def test_success_result(self) -> None:
        """Successful read result has data."""
        result = S3ReadResult(
            success=True,
            key="test/key.json",
            data=b'{"test": 1}',
            size_bytes=11,
            duration_ms=50,
        )

        assert result.success is True
        assert result.data == b'{"test": 1}'
        assert result.not_found is False
        assert result.error is None

    def test_not_found_result(self) -> None:
        """Not found result has flag set."""
        result = S3ReadResult(
            success=False,
            key="test/missing.json",
            not_found=True,
            error="Object not found",
        )

        assert result.success is False
        assert result.not_found is True
        assert result.data == b""


class TestAsyncS3ClientInit:
    """Tests for AsyncS3Client initialization."""

    def test_init_with_config(self) -> None:
        """Client initializes with config."""
        config = AsyncS3Config(bucket="test-bucket")
        client = AsyncS3Client(config=config)

        assert client._config.bucket == "test-bucket"
        assert client._initialized is False

    def test_init_with_explicit_params(self) -> None:
        """Client initializes with explicit parameters."""
        client = AsyncS3Client(
            bucket="explicit-bucket",
            region="ap-northeast-1",
        )

        assert client._config.bucket == "explicit-bucket"
        assert client._config.region == "ap-northeast-1"

    @patch("autom8_asana.settings.get_settings")
    def test_init_from_settings(self, mock_settings: MagicMock) -> None:
        """Client uses settings when no bucket provided."""
        mock_s3_settings = MagicMock()
        mock_s3_settings.bucket = "settings-bucket"
        mock_s3_settings.region = "us-west-2"
        mock_s3_settings.endpoint_url = None
        mock_settings.return_value.s3 = mock_s3_settings

        client = AsyncS3Client()

        assert client._config.bucket == "settings-bucket"
        assert client._config.region == "us-west-2"


class TestAsyncS3ClientErrors:
    """Tests for AsyncS3Client error handling."""

    def test_is_not_found_error_nosuchkey(self) -> None:
        """Recognizes NoSuchKey error."""
        client = AsyncS3Client(bucket="test")

        # Create a mock error with response
        error = Exception("NoSuchKey")
        assert client._is_not_found_error(error) is True

    def test_is_not_found_error_404(self) -> None:
        """Recognizes 404 error."""
        client = AsyncS3Client(bucket="test")

        error = Exception("404 not found")
        assert client._is_not_found_error(error) is True

    def test_is_not_found_error_generic(self) -> None:
        """Generic errors are not found errors."""
        client = AsyncS3Client(bucket="test")

        error = Exception("Connection refused")
        assert client._is_not_found_error(error) is False

    def test_is_retryable_error_timeout(self) -> None:
        """Timeout errors are retryable."""
        client = AsyncS3Client(bucket="test")

        assert client._is_retryable_error(TimeoutError()) is True
        assert client._is_retryable_error(asyncio.TimeoutError()) is True

    def test_is_retryable_error_connection(self) -> None:
        """Connection errors are retryable."""
        client = AsyncS3Client(bucket="test")

        assert client._is_retryable_error(ConnectionError()) is True

    def test_is_retryable_error_throttle(self) -> None:
        """Throttle errors are retryable."""
        client = AsyncS3Client(bucket="test")

        error = Exception("SlowDown: Please reduce your request rate")
        assert client._is_retryable_error(error) is True

    def test_is_retryable_error_access_denied(self) -> None:
        """Access denied is not retryable."""
        client = AsyncS3Client(bucket="test")

        error = Exception("AccessDenied: You don't have permission")
        assert client._is_retryable_error(error) is False


class TestAsyncS3ClientAvailability:
    """Tests for client availability checks."""

    def test_is_available_not_initialized(self) -> None:
        """Uninitialized client is not available."""
        client = AsyncS3Client(bucket="test")

        assert client.is_available is False

    def test_is_available_no_bucket(self) -> None:
        """Client without bucket is not available."""
        client = AsyncS3Client(bucket="")

        assert client.is_available is False


@pytest.mark.asyncio
class TestAsyncS3ClientOperations:
    """Integration-style tests for S3 operations (mocked)."""

    async def test_context_manager(self) -> None:
        """Client works as async context manager."""
        client = AsyncS3Client(bucket="test-bucket")

        # Mock boto3 initialization
        with patch("boto3.client") as mock_boto3:
            mock_s3 = MagicMock()
            mock_boto3.return_value = mock_s3

            async with client as c:
                assert c is client

    async def test_put_object_success(self) -> None:
        """put_object_async returns success result."""
        client = AsyncS3Client(bucket="test-bucket")

        # Mock boto3 client
        mock_s3 = MagicMock()
        mock_s3.put_object.return_value = {"ETag": '"abc123"'}

        with patch("boto3.client", return_value=mock_s3):
            with patch("botocore.config.Config"):
                await client._ensure_initialized()
                client._client = mock_s3

                result = await client.put_object_async("test/key.json", b'{"data": 1}')

                assert result.success is True
                assert result.key == "test/key.json"
                assert result.etag == "abc123"
                assert result.size_bytes == 11  # len(b'{"data": 1}')

    async def test_get_object_success(self) -> None:
        """get_object_async returns data on success."""
        client = AsyncS3Client(bucket="test-bucket")

        # Mock stream that supports read
        mock_body = MagicMock()
        mock_body.read.return_value = b'{"data": 1}'

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": mock_body}

        with patch("boto3.client", return_value=mock_s3):
            with patch("botocore.config.Config"):
                await client._ensure_initialized()
                client._client = mock_s3

                result = await client.get_object_async("test/key.json")

                assert result.success is True
                assert result.data == b'{"data": 1}'
                assert result.not_found is False

    async def test_head_object_exists(self) -> None:
        """head_object_async returns metadata when object exists."""
        client = AsyncS3Client(bucket="test-bucket")

        mock_s3 = MagicMock()
        mock_s3.head_object.return_value = {
            "ContentLength": 1024,
            "ContentType": "application/json",
            "ETag": '"xyz789"',
            "Metadata": {"project-gid": "123"},
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch("botocore.config.Config"):
                await client._ensure_initialized()
                client._client = mock_s3

                result = await client.head_object_async("test/key.json")

                assert result is not None
                assert result["content_length"] == 1024
                assert result["etag"] == "xyz789"
                assert result["metadata"]["project-gid"] == "123"

    async def test_delete_object_success(self) -> None:
        """delete_object_async returns True on success."""
        client = AsyncS3Client(bucket="test-bucket")

        mock_s3 = MagicMock()
        mock_s3.delete_object.return_value = {}

        with patch("boto3.client", return_value=mock_s3):
            with patch("botocore.config.Config"):
                await client._ensure_initialized()
                client._client = mock_s3

                result = await client.delete_object_async("test/key.json")

                assert result is True

    async def test_list_objects_success(self) -> None:
        """list_objects_async returns object list."""
        client = AsyncS3Client(bucket="test-bucket")

        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "prefix/file1.json", "Size": 100, "ETag": '"aaa"'},
                {"Key": "prefix/file2.json", "Size": 200, "ETag": '"bbb"'},
            ]
        }

        with patch("boto3.client", return_value=mock_s3):
            with patch("botocore.config.Config"):
                await client._ensure_initialized()
                client._client = mock_s3

                result = await client.list_objects_async("prefix/")

                assert len(result) == 2
                assert result[0]["key"] == "prefix/file1.json"
                assert result[1]["size"] == 200

    async def test_head_bucket_success(self) -> None:
        """head_bucket_async returns True when bucket exists."""
        client = AsyncS3Client(bucket="test-bucket")

        mock_s3 = MagicMock()
        mock_s3.head_bucket.return_value = {}

        with patch("boto3.client", return_value=mock_s3):
            with patch("botocore.config.Config"):
                await client._ensure_initialized()
                client._client = mock_s3

                result = await client.head_bucket_async()

                assert result is True

    async def test_get_object_not_found(self) -> None:
        """get_object_async handles not found."""
        client = AsyncS3Client(bucket="test-bucket")

        mock_s3 = MagicMock()
        mock_s3.get_object.side_effect = Exception(
            "NoSuchKey: The specified key does not exist"
        )

        with patch("boto3.client", return_value=mock_s3):
            with patch("botocore.config.Config"):
                await client._ensure_initialized()
                client._client = mock_s3

                result = await client.get_object_async("missing/key.json")

                assert result.success is False
                assert result.not_found is True
