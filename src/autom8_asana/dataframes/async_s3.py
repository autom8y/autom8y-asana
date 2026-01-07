"""Async S3 client wrapper using boto3 with asyncio.to_thread().

Provides async S3 operations for section-level DataFrame persistence.
Uses boto3 with asyncio.to_thread() for non-blocking I/O during parallel
project processing. This approach:
- Matches AWS best practices (used by awswrangler, Lambda Powertools)
- Has 30-40% better performance at 10-30 concurrent operations vs aioboto3
- Has zero dependency conflicts (works with any boto3 version)

Features:
- Async interface via asyncio.to_thread() (thread pool executor)
- Retry logic with exponential backoff
- Graceful degradation on S3 errors
- Metrics collection (write time, bytes, throughput)
- Thread-safe boto3 client reuse

Thread Safety:
    boto3 clients are thread-safe for S3 operations. A single client
    is shared across all async operations via the thread pool.

Example:
    >>> from autom8_asana.dataframes.async_s3 import AsyncS3Client
    >>>
    >>> client = AsyncS3Client(bucket="my-bucket")
    >>> async with client:
    ...     result = await client.put_object_async("key", b"data")
    ...     print(f"Written {result.size_bytes} bytes in {result.duration_ms}ms")
"""

from __future__ import annotations

import asyncio
from autom8y_log import get_logger
import time
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

__all__ = ["AsyncS3Client", "S3WriteResult", "S3ReadResult", "AsyncS3Config"]

logger = get_logger(__name__)


@dataclass
class AsyncS3Config:
    """Configuration for async S3 client.

    Attributes:
        bucket: S3 bucket name.
        region: AWS region (default "us-east-1").
        endpoint_url: Custom endpoint URL for LocalStack or S3-compatible storage.
        max_retries: Maximum retry attempts for transient errors (default 3).
        base_retry_delay: Base delay in seconds for exponential backoff (default 0.5).
        connect_timeout: Connection timeout in seconds (default 10).
        read_timeout: Read timeout in seconds (default 30).
    """

    bucket: str
    region: str = "us-east-1"
    endpoint_url: str | None = None
    max_retries: int = 3
    base_retry_delay: float = 0.5
    connect_timeout: int = 10
    read_timeout: int = 30


@dataclass
class S3WriteResult:
    """Result of an S3 write operation.

    Attributes:
        success: Whether the write succeeded.
        key: S3 object key that was written.
        size_bytes: Size of data written in bytes.
        duration_ms: Time taken for the write operation in milliseconds.
        throughput_mbps: Write throughput in MB/s.
        etag: S3 ETag of the written object (if successful).
        error: Error message if write failed.
    """

    success: bool
    key: str
    size_bytes: int = 0
    duration_ms: float = 0.0
    throughput_mbps: float = 0.0
    etag: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        """Calculate throughput after initialization."""
        if self.success and self.duration_ms > 0:
            # Convert bytes to MB and ms to s
            mb = self.size_bytes / (1024 * 1024)
            seconds = self.duration_ms / 1000
            self.throughput_mbps = mb / seconds if seconds > 0 else 0.0


@dataclass
class S3ReadResult:
    """Result of an S3 read operation.

    Attributes:
        success: Whether the read succeeded.
        key: S3 object key that was read.
        data: Raw bytes read from S3 (if successful).
        size_bytes: Size of data read in bytes.
        duration_ms: Time taken for the read operation in milliseconds.
        error: Error message if read failed.
        not_found: True if the object doesn't exist.
    """

    success: bool
    key: str
    data: bytes = field(default_factory=bytes)
    size_bytes: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    not_found: bool = False


class AsyncS3Client:
    """Async S3 client wrapper using boto3 with asyncio.to_thread().

    Provides async S3 operations with retry logic, graceful degradation,
    and comprehensive metrics collection. Uses thread pool for non-blocking
    I/O which matches AWS best practices.

    Example:
        >>> config = AsyncS3Config(bucket="my-bucket")
        >>> client = AsyncS3Client(config=config)
        >>> async with client:
        ...     result = await client.put_object_async("test/key.json", b'{"data": 1}')
        ...     if result.success:
        ...         print(f"Written in {result.duration_ms:.1f}ms")
    """

    def __init__(
        self,
        config: AsyncS3Config | None = None,
        *,
        bucket: str | None = None,
        region: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        """Initialize async S3 client.

        Can be initialized with an AsyncS3Config or individual parameters.
        Uses Pydantic Settings for environment variable configuration when
        no explicit bucket is provided.

        Args:
            config: S3 configuration object (preferred).
            bucket: S3 bucket name (if config not provided).
            region: AWS region (if config not provided).
            endpoint_url: Custom endpoint URL (if config not provided).
        """
        if config is None:
            # Use Pydantic Settings for S3 configuration
            from autom8_asana.settings import get_settings

            s3_settings = get_settings().s3

            resolved_bucket = bucket if bucket is not None else s3_settings.bucket
            resolved_region = region if region is not None else s3_settings.region
            resolved_endpoint = (
                endpoint_url if endpoint_url is not None else s3_settings.endpoint_url
            )

            if not resolved_bucket:
                logger.warning(
                    "No S3 bucket configured for AsyncS3Client. "
                    "Set ASANA_CACHE_S3_BUCKET or pass bucket parameter."
                )

            config = AsyncS3Config(
                bucket=resolved_bucket or "",
                region=resolved_region,
                endpoint_url=resolved_endpoint,
            )

        self._config = config
        self._client: "S3Client | None" = None
        self._degraded = False
        self._last_error_time: float = 0.0
        self._degraded_backoff = 60.0  # seconds before retry in degraded mode
        self._initialized = False

    async def __aenter__(self) -> "AsyncS3Client":
        """Async context manager entry."""
        await self._ensure_initialized()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_initialized(self) -> None:
        """Lazily initialize boto3 client."""
        if self._initialized:
            return

        if not self._config.bucket:
            logger.warning("No S3 bucket configured, entering degraded mode")
            self._degraded = True
            return

        try:
            import boto3
            from botocore.config import Config

            # Configure boto3 client with timeouts
            boto_config = Config(
                connect_timeout=self._config.connect_timeout,
                read_timeout=self._config.read_timeout,
                retries={"max_attempts": 0},  # We handle retries ourselves
            )

            client_kwargs: dict[str, Any] = {
                "region_name": self._config.region,
                "config": boto_config,
            }
            if self._config.endpoint_url:
                client_kwargs["endpoint_url"] = self._config.endpoint_url

            # Create client in thread to avoid blocking event loop
            self._client = await asyncio.to_thread(
                boto3.client, "s3", **client_kwargs
            )
            self._initialized = True
            logger.debug(
                "AsyncS3Client initialized: bucket=%s region=%s",
                self._config.bucket,
                self._config.region,
            )
        except Exception as e:
            logger.error("Failed to create boto3 S3 client: %s", e)
            self._degraded = True

    def _get_client(self) -> "S3Client":
        """Get the boto3 S3 client.

        Returns:
            The boto3 S3 client.

        Raises:
            RuntimeError: If client not initialized or in degraded mode.
        """
        if self._client is None:
            raise RuntimeError("boto3 S3 client not initialized")

        if self._degraded:
            # Check if we should retry
            if time.time() - self._last_error_time > self._degraded_backoff:
                self._degraded = False
            else:
                raise RuntimeError("AsyncS3Client in degraded mode")

        return self._client

    async def close(self) -> None:
        """Close the client and release resources."""
        if self._client is not None:
            # boto3 clients don't need explicit closing, but we reset state
            self._client = None
        self._initialized = False
        logger.debug("AsyncS3Client closed")

    @property
    def is_available(self) -> bool:
        """Check if the client is available (not in degraded mode)."""
        return self._initialized and not self._degraded and bool(self._config.bucket)

    @property
    def can_be_available(self) -> bool:
        """Check if client can potentially be available (has valid config).

        Use this for pre-initialization checks before entering async context.
        Unlike is_available, this doesn't require async initialization.
        """
        return bool(self._config.bucket)

    async def put_object_async(
        self,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> S3WriteResult:
        """Write an object to S3 asynchronously.

        Args:
            key: S3 object key.
            body: Raw bytes to write.
            content_type: MIME content type.
            metadata: Optional S3 object metadata.

        Returns:
            S3WriteResult with success status and metrics.
        """
        await self._ensure_initialized()
        start_time = time.monotonic()
        size_bytes = len(body)

        for attempt in range(self._config.max_retries):
            try:
                client = self._get_client()

                put_kwargs: dict[str, Any] = {
                    "Bucket": self._config.bucket,
                    "Key": key,
                    "Body": body,
                    "ContentType": content_type,
                }
                if metadata:
                    put_kwargs["Metadata"] = metadata

                # Run S3 operation in thread pool
                response = await asyncio.to_thread(
                    client.put_object, **put_kwargs
                )

                duration_ms = (time.monotonic() - start_time) * 1000
                etag = response.get("ETag", "").strip('"')

                result = S3WriteResult(
                    success=True,
                    key=key,
                    size_bytes=size_bytes,
                    duration_ms=duration_ms,
                    etag=etag,
                )

                logger.debug(
                    "s3_write_completed",
                    extra={
                        "key": key,
                        "size_bytes": size_bytes,
                        "duration_ms": round(duration_ms, 2),
                        "throughput_mbps": round(result.throughput_mbps, 2),
                    },
                )
                return result

            except Exception as e:
                if self._is_retryable_error(e) and attempt < self._config.max_retries - 1:
                    delay = self._config.base_retry_delay * (2**attempt)
                    logger.warning(
                        "S3 put_object retry %d/%d for key %s: %s (delay %.1fs)",
                        attempt + 1,
                        self._config.max_retries,
                        key,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    duration_ms = (time.monotonic() - start_time) * 1000
                    self._handle_error(e, "put_object", key)
                    return S3WriteResult(
                        success=False,
                        key=key,
                        size_bytes=size_bytes,
                        duration_ms=duration_ms,
                        error=str(e),
                    )

        # Should not reach here, but handle edge case
        duration_ms = (time.monotonic() - start_time) * 1000
        return S3WriteResult(
            success=False,
            key=key,
            size_bytes=size_bytes,
            duration_ms=duration_ms,
            error="Max retries exceeded",
        )

    async def get_object_async(self, key: str) -> S3ReadResult:
        """Read an object from S3 asynchronously.

        Args:
            key: S3 object key.

        Returns:
            S3ReadResult with data and metrics.
        """
        await self._ensure_initialized()
        start_time = time.monotonic()

        for attempt in range(self._config.max_retries):
            try:
                client = self._get_client()

                # Run S3 operation in thread pool
                response = await asyncio.to_thread(
                    client.get_object,
                    Bucket=self._config.bucket,
                    Key=key,
                )

                # Read body in thread pool
                data = await asyncio.to_thread(
                    response["Body"].read
                )

                duration_ms = (time.monotonic() - start_time) * 1000

                logger.debug(
                    "s3_read_completed",
                    extra={
                        "key": key,
                        "size_bytes": len(data),
                        "duration_ms": round(duration_ms, 2),
                    },
                )

                return S3ReadResult(
                    success=True,
                    key=key,
                    data=data,
                    size_bytes=len(data),
                    duration_ms=duration_ms,
                )

            except Exception as e:
                if self._is_not_found_error(e):
                    duration_ms = (time.monotonic() - start_time) * 1000
                    return S3ReadResult(
                        success=False,
                        key=key,
                        duration_ms=duration_ms,
                        not_found=True,
                        error="Object not found",
                    )

                if self._is_retryable_error(e) and attempt < self._config.max_retries - 1:
                    delay = self._config.base_retry_delay * (2**attempt)
                    logger.warning(
                        "S3 get_object retry %d/%d for key %s: %s (delay %.1fs)",
                        attempt + 1,
                        self._config.max_retries,
                        key,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    duration_ms = (time.monotonic() - start_time) * 1000
                    self._handle_error(e, "get_object", key)
                    return S3ReadResult(
                        success=False,
                        key=key,
                        duration_ms=duration_ms,
                        error=str(e),
                    )

        duration_ms = (time.monotonic() - start_time) * 1000
        return S3ReadResult(
            success=False,
            key=key,
            duration_ms=duration_ms,
            error="Max retries exceeded",
        )

    async def head_object_async(self, key: str) -> dict[str, Any] | None:
        """Check if an object exists and get its metadata.

        Args:
            key: S3 object key.

        Returns:
            Object metadata dict if exists, None if not found or error.
        """
        await self._ensure_initialized()
        try:
            client = self._get_client()

            response = await asyncio.to_thread(
                client.head_object,
                Bucket=self._config.bucket,
                Key=key,
            )
            return {
                "content_length": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", ""),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag", "").strip('"'),
                "metadata": response.get("Metadata", {}),
            }
        except Exception as e:
            if self._is_not_found_error(e):
                return None
            self._handle_error(e, "head_object", key)
            return None

    async def delete_object_async(self, key: str) -> bool:
        """Delete an object from S3.

        Args:
            key: S3 object key.

        Returns:
            True if deleted or didn't exist, False on error.
        """
        await self._ensure_initialized()
        try:
            client = self._get_client()

            await asyncio.to_thread(
                client.delete_object,
                Bucket=self._config.bucket,
                Key=key,
            )
            logger.debug("s3_delete_completed", extra={"key": key})
            return True
        except Exception as e:
            if self._is_not_found_error(e):
                return True  # Already doesn't exist
            self._handle_error(e, "delete_object", key)
            return False

    async def list_objects_async(
        self,
        prefix: str,
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """List objects under a prefix.

        Args:
            prefix: S3 key prefix to list.
            max_keys: Maximum number of keys to return.

        Returns:
            List of object info dicts with key, size, last_modified.
        """
        await self._ensure_initialized()
        try:
            client = self._get_client()

            response = await asyncio.to_thread(
                client.list_objects_v2,
                Bucket=self._config.bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            objects = []
            for obj in response.get("Contents", []):
                objects.append(
                    {
                        "key": obj.get("Key", ""),
                        "size": obj.get("Size", 0),
                        "last_modified": obj.get("LastModified"),
                        "etag": obj.get("ETag", "").strip('"'),
                    }
                )

            return objects
        except Exception as e:
            self._handle_error(e, "list_objects", prefix)
            return []

    async def head_bucket_async(self) -> bool:
        """Check if the configured bucket exists and is accessible.

        Returns:
            True if bucket is accessible, False otherwise.
        """
        await self._ensure_initialized()
        try:
            client = self._get_client()

            await asyncio.to_thread(
                client.head_bucket,
                Bucket=self._config.bucket,
            )
            return True
        except Exception as e:
            self._handle_error(e, "head_bucket", self._config.bucket)
            return False

    def _is_not_found_error(self, error: Exception) -> bool:
        """Check if error indicates object not found."""
        error_str = str(error).lower()
        error_class = type(error).__name__

        # Check common patterns
        if "nosuchkey" in error_str or "not found" in error_str:
            return True
        if "404" in error_str:
            return True
        if error_class in ("NoSuchKey", "NotFound"):
            return True

        # Check botocore ClientError
        if hasattr(error, "response"):
            error_code = error.response.get("Error", {}).get("Code", "")  # type: ignore[attr-defined]
            return error_code in ("NoSuchKey", "404", "NotFound")

        return False

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if error is transient and should be retried."""
        error_str = str(error).lower()

        # Network errors are retryable
        retryable_patterns = [
            "timeout",
            "connection",
            "throttl",
            "slowdown",
            "503",
            "500",
            "serviceunav",
        ]
        for pattern in retryable_patterns:
            if pattern in error_str:
                return True

        # Specific exception types
        retryable_types = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            OSError,
        )
        if isinstance(error, retryable_types):
            return True

        # Check botocore error codes
        if hasattr(error, "response"):
            error_code = error.response.get("Error", {}).get("Code", "")  # type: ignore[attr-defined]
            return error_code in (
                "SlowDown",
                "ServiceUnavailable",
                "InternalError",
                "RequestTimeout",
            )

        return False

    def _handle_error(self, error: Exception, operation: str, key: str) -> None:
        """Handle S3 errors and potentially enter degraded mode."""
        # Check for access denied or bucket not found
        if hasattr(error, "response"):
            error_code = error.response.get("Error", {}).get("Code", "")  # type: ignore[attr-defined]
            if error_code in ("AccessDenied", "NoSuchBucket"):
                if not self._degraded:
                    logger.warning(
                        "S3 access error during %s for %s, entering degraded mode: %s",
                        operation,
                        key,
                        error,
                    )
                    self._degraded = True
                    self._last_error_time = time.time()
                return

        # Network/connection errors trigger degraded mode
        if isinstance(error, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
            if not self._degraded:
                logger.warning(
                    "S3 connectivity error during %s for %s, entering degraded mode: %s",
                    operation,
                    key,
                    error,
                )
                self._degraded = True
                self._last_error_time = time.time()
        else:
            logger.error(
                "S3 error during %s for %s: %s",
                operation,
                key,
                error,
            )
