"""S3 cache provider for cold tier storage with compression support."""

from __future__ import annotations

import gzip
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import TYPE_CHECKING, Any, cast

from autom8y_log import get_logger

from autom8_asana.cache.backends.base import CacheBackendBase
from autom8_asana.cache.models.entry import CacheEntry, EntryType
from autom8_asana.cache.models.errors import is_connection_error, is_s3_not_found_error
from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.models.versioning import (
    format_version,
    is_current,
    parse_version,
)
from autom8_asana.core.exceptions import S3_TRANSPORT_ERRORS, S3TransportError
from autom8_asana.protocols.cache import WarmResult

if TYPE_CHECKING:
    from types import ModuleType

    from autom8_asana.cache.models.settings import CacheSettings

logger = get_logger(__name__)


@dataclass
class S3Config:
    """S3 cache configuration.

    Attributes:
        bucket: S3 bucket name for cache storage.
        prefix: Key prefix for cache objects (default "asana-cache").
        region: AWS region (default "us-east-1").
        endpoint_url: Custom endpoint URL for LocalStack or S3-compatible storage.
        compress_threshold: Compress objects larger than this size in bytes (default 1024).
        default_ttl: Default TTL in seconds (default 604800 = 7 days).

    Note:
        Per B4 Config Consolidation audit: bucket/region/endpoint_url fields
        follow the same pattern as S3LocationConfig. The shared S3LocationConfig
        primitive is available in autom8_asana.config for new code that needs
        S3 location without backend-specific fields. S3Config retains its direct
        fields for backward compatibility with existing call sites.
    """

    bucket: str
    prefix: str = "asana-cache"
    region: str = "us-east-1"
    endpoint_url: str | None = None
    compress_threshold: int = 1024
    default_ttl: int = 604800  # 7 days


class S3CacheProvider(CacheBackendBase):
    """S3-based cache provider for cold tier storage.

    Implements the CacheProvider protocol using S3 as the backend.
    Designed for long-term, infrequently-accessed cache storage
    as part of a two-tier caching architecture (see ADR-0026).

    Key Structure:
        {prefix}/tasks/{gid}/{entry_type}.json[.gz]

    Features:
        - Gzip compression for objects exceeding compress_threshold
        - Version metadata stored in S3 object metadata
        - Graceful degradation on connection failures
        - Thread-safe through client reuse

    Thread Safety:
        Uses a single boto3 client instance with internal connection pooling.
        Client creation is protected by a lock for safe lazy initialization.

    Example:
        >>> from autom8_asana.cache.backends import S3CacheProvider, S3Config
        >>> cache = S3CacheProvider(
        ...     config=S3Config(bucket="my-cache-bucket")
        ... )
        >>> cache.is_healthy()
        True
    """

    # Metadata keys for version tracking
    META_VERSION = "x-amz-meta-version"
    META_CACHED_AT = "x-amz-meta-cached-at"
    META_ENTRY_TYPE = "x-amz-meta-entry-type"
    META_TTL = "x-amz-meta-ttl"
    META_PROJECT_GID = "x-amz-meta-project-gid"

    _transport_errors = S3_TRANSPORT_ERRORS

    def __init__(
        self,
        config: S3Config | None = None,
        settings: CacheSettings | None = None,
        *,
        connection_manager: Any | None = None,
        bucket: str | None = None,
        prefix: str | None = None,
        region: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        """Initialize S3 cache provider.

        Can be initialized with an S3Config or individual parameters.
        Uses Pydantic Settings for environment variable configuration.

        Args:
            config: S3 configuration object (preferred).
            settings: Cache settings for TTL and overflow thresholds.
            connection_manager: Optional S3ConnectionManager for lifecycle
                coordination. When provided, delegates client management
                to the manager instead of managing boto3 client internally.
                Per TDD-CONNECTION-LIFECYCLE-001 Phase 1.
            bucket: S3 bucket name (if config not provided).
            prefix: Key prefix (if config not provided).
            region: AWS region (if config not provided).
            endpoint_url: Custom endpoint URL (if config not provided).
        """
        if config is None:
            # Use Pydantic Settings for S3 configuration
            from autom8_asana.settings import get_settings

            s3_settings = get_settings().s3

            # Explicit parameters override settings from env
            resolved_bucket = bucket if bucket is not None else s3_settings.bucket
            resolved_prefix = prefix if prefix is not None else s3_settings.prefix
            resolved_region = region if region is not None else s3_settings.region
            resolved_endpoint = (
                endpoint_url if endpoint_url is not None else s3_settings.endpoint_url
            )

            if not resolved_bucket:
                logger.warning(
                    "s3_bucket_not_configured",
                    extra={
                        "message": "Set ASANA_CACHE_S3_BUCKET or pass bucket parameter"
                    },
                )

            config = S3Config(
                bucket=resolved_bucket or "",
                prefix=resolved_prefix,
                region=resolved_region,
                endpoint_url=resolved_endpoint,
            )

        self._config = config
        super().__init__(settings=settings)
        self._client: Any = None
        self._client_lock = Lock()
        self._boto3_module: ModuleType | None = None
        self._botocore_module: ModuleType | None = None

        # Connection manager delegation (per TDD-CONNECTION-LIFECYCLE-001)
        self._connection_manager = connection_manager

        # Import boto3 to make it optional dependency
        try:
            import boto3
            import botocore.exceptions

            self._boto3_module = boto3
            self._botocore_module = botocore.exceptions
            if self._connection_manager is None:
                self._initialize_client()
        except ImportError:
            logger.warning(
                "boto3_package_not_installed",
                extra={"fallback": "degraded_mode"},
            )
            self._degraded = True

    def _initialize_client(self) -> None:
        """Initialize S3 client with configuration."""
        if self._boto3_module is None:
            return

        if not self._config.bucket:
            logger.warning(
                "s3_bucket_not_configured",
                extra={"fallback": "degraded_mode"},
            )
            self._degraded = True
            return

        try:
            client_kwargs: dict[str, Any] = {
                "region_name": self._config.region,
            }
            if self._config.endpoint_url:
                client_kwargs["endpoint_url"] = self._config.endpoint_url

            self._client = self._boto3_module.client("s3", **client_kwargs)
            self._degraded = False
        except S3_TRANSPORT_ERRORS as e:
            logger.error(
                "s3_client_init_failed",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            self._degraded = True

    def _get_client(self) -> Any:
        """Get S3 client, attempting reconnection if in degraded mode.

        When a connection_manager is provided, delegates to it.
        Otherwise uses the internal client (legacy path).

        Returns:
            boto3 S3 client instance.

        Raises:
            RuntimeError: If boto3 is not available or client cannot be created.
        """
        # New path: delegate to connection manager
        if self._connection_manager is not None:
            return self._connection_manager.get_client()

        if self._boto3_module is None:
            raise RuntimeError("boto3 package not installed")

        if self._degraded:
            self._attempt_reconnect()

        if self._client is None:
            raise RuntimeError("S3 client not initialized")

        return self._client

    def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to S3 if in degraded mode."""
        if not self.should_attempt_reconnect():
            return

        with self._client_lock:
            self.record_reconnect_attempt()
            try:
                self._initialize_client()
                if self._client is not None:
                    # Test connectivity with a simple HEAD bucket
                    self._client.head_bucket(Bucket=self._config.bucket)
                    self.exit_degraded_mode()
                    logger.info("S3 connection restored")
            except S3_TRANSPORT_ERRORS as e:
                logger.warning(
                    "s3_reconnect_failed",
                    extra={"error": str(e)},
                )

    def _make_key(self, key: str, entry_type: EntryType) -> str:
        """Generate S3 object key for a cache entry.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry.

        Returns:
            Full S3 object key string.
        """
        if entry_type == EntryType.DATAFRAME:
            # Dataframe keys include project context
            return f"{self._config.prefix}/dataframe/{key}.json"
        return f"{self._config.prefix}/tasks/{key}/{entry_type.value}.json"

    def _make_simple_key(self, key: str) -> str:
        """Generate S3 object key for simple key-value storage.

        Args:
            key: Cache key.

        Returns:
            Full S3 object key string.
        """
        return f"{self._config.prefix}/simple/{key}.json"

    def _serialize_entry(self, entry: CacheEntry) -> tuple[bytes, dict[str, str], bool]:
        """Serialize CacheEntry for S3 storage.

        Args:
            entry: Cache entry to serialize.

        Returns:
            Tuple of (body bytes, metadata dict, is_compressed).
        """
        stamp_data = self._serialize_freshness_stamp(entry.freshness_stamp)

        data = {
            "data": entry.data,
            "entry_type": entry.entry_type.value,
            "version": format_version(entry.version),
            "cached_at": format_version(entry.cached_at),
            "ttl": entry.ttl,
            "project_gid": entry.project_gid,
            "metadata": entry.metadata,
            "key": entry.key,
            "freshness_stamp": stamp_data,
        }

        body = json.dumps(data).encode("utf-8")
        is_compressed = len(body) > self._config.compress_threshold

        if is_compressed:
            body = gzip.compress(body)

        metadata = {
            "version": format_version(entry.version),
            "cached-at": format_version(entry.cached_at),
            "entry-type": entry.entry_type.value,
            "compressed": str(is_compressed).lower(),
        }

        if entry.ttl is not None:
            metadata["ttl"] = str(entry.ttl)
        if entry.project_gid:
            metadata["project-gid"] = entry.project_gid

        return body, metadata, is_compressed

    def _deserialize_entry(
        self,
        body: bytes,
        metadata: dict[str, str],
        key: str,
    ) -> CacheEntry | None:
        """Deserialize S3 object to CacheEntry.

        Args:
            body: Object body bytes.
            metadata: S3 object metadata dict.
            key: Cache key.

        Returns:
            CacheEntry or None if data is invalid.
        """
        try:
            # Check if compressed
            is_compressed = metadata.get("compressed", "false").lower() == "true"
            if is_compressed:
                body = gzip.decompress(body)

            data = json.loads(body.decode("utf-8"))

            entry_type = EntryType(data.get("entry_type", "task"))
            version_str = data.get("version", "")
            cached_at_str = data.get("cached_at", "")
            ttl = data.get("ttl")
            project_gid = data.get("project_gid")
            entry_metadata = data.get("metadata", {})
            entry_data = data.get("data", {})

            version = parse_version(version_str) if version_str else datetime.now(UTC)
            cached_at = (
                parse_version(cached_at_str) if cached_at_str else datetime.now(UTC)
            )

            # Deserialize freshness stamp if present
            raw_stamp = data.get("freshness_stamp")
            freshness_stamp = self._deserialize_freshness_stamp(
                raw_stamp if isinstance(raw_stamp, dict) else None
            )

            return CacheEntry(
                key=key,
                data=entry_data,
                entry_type=entry_type,
                version=version,
                cached_at=cached_at,
                ttl=ttl,
                project_gid=project_gid,
                metadata=entry_metadata,
                freshness_stamp=freshness_stamp,
            )
        except (json.JSONDecodeError, ValueError, KeyError, gzip.BadGzipFile) as e:
            logger.warning(
                "cache_entry_deserialize_failed",
                extra={"key": key, "error": str(e)},
            )
            return None

    # === Template method hooks (simple operations) ===

    def _do_get(self, key: str) -> dict[str, Any] | None:
        """S3-specific get: fetch object, decompress if needed.

        Returns:
            Cached dict if found, None if miss.
        """
        client = self._get_client()
        s3_key = self._make_simple_key(key)

        response = client.get_object(
            Bucket=self._config.bucket,
            Key=s3_key,
        )
        body = response["Body"].read()
        metadata = response.get("Metadata", {})

        # Check compression
        is_compressed = metadata.get("compressed", "false").lower() == "true"
        if is_compressed:
            body = gzip.decompress(body)

        return cast("dict[str, Any]", json.loads(body.decode("utf-8")))

    def _do_set(self, key: str, value: dict[str, Any], ttl: int | None) -> None:
        """S3-specific set: serialize, compress, put object."""
        client = self._get_client()
        s3_key = self._make_simple_key(key)

        body = json.dumps(value).encode("utf-8")
        is_compressed = len(body) > self._config.compress_threshold

        if is_compressed:
            body = gzip.compress(body)

        metadata: dict[str, str] = {
            "compressed": str(is_compressed).lower(),
        }
        if ttl is not None:
            metadata["ttl"] = str(ttl)

        client.put_object(
            Bucket=self._config.bucket,
            Key=s3_key,
            Body=body,
            ContentType="application/json",
            Metadata=metadata,
        )

    def _do_delete(self, key: str) -> None:
        """S3-specific delete: remove object."""
        client = self._get_client()
        s3_key = self._make_simple_key(key)

        client.delete_object(
            Bucket=self._config.bucket,
            Key=s3_key,
        )

    # === Versioned methods ===

    def get_versioned(
        self,
        key: str,
        entry_type: EntryType,
        freshness: FreshnessIntent | None = None,
    ) -> CacheEntry | None:
        """Retrieve versioned cache entry with freshness control.

        Args:
            key: Cache key (task GID).
            entry_type: Type of entry for version resolution.
            freshness: STRICT validates version, EVENTUAL returns without check.

        Returns:
            CacheEntry if found and not expired, None otherwise.
        """
        if freshness is None:
            freshness = FreshnessIntent.EVENTUAL

        start = time.perf_counter()
        entry_type_str = entry_type.value

        try:
            if self._degraded:
                self._metrics.record_miss(0.0, key=key, entry_type=entry_type_str)
                return None

            client = self._get_client()
            s3_key = self._make_key(key, entry_type)

            response = client.get_object(
                Bucket=self._config.bucket,
                Key=s3_key,
            )
            body = response["Body"].read()
            metadata = response.get("Metadata", {})
            latency = (time.perf_counter() - start) * 1000

            entry = self._deserialize_entry(body, metadata, key)
            if entry is None:
                self._metrics.record_miss(latency, key=key, entry_type=entry_type_str)
                return None

            # Check TTL expiration
            if entry.is_expired():
                # Delete expired entry asynchronously (best effort)
                try:
                    client.delete_object(Bucket=self._config.bucket, Key=s3_key)
                except S3_TRANSPORT_ERRORS:
                    logger.debug(
                        "s3_expired_entry_delete_failed",
                        exc_info=True,
                        extra={"key": key, "s3_key": s3_key},
                    )
                self._metrics.record_miss(latency, key=key, entry_type=entry_type_str)
                return None

            # For STRICT freshness, caller must validate against source
            self._metrics.record_hit(latency, key=key, entry_type=entry_type_str)
            return entry

        except S3_TRANSPORT_ERRORS as e:
            latency = (time.perf_counter() - start) * 1000
            if self._is_not_found_error(e):
                self._metrics.record_miss(latency, key=key, entry_type=entry_type_str)
                return None
            self._metrics.record_error(
                key=key, entry_type=entry_type_str, error_message=str(e)
            )
            self._handle_transport_error(e, operation="get_versioned", key=key)
            return None

    def _do_set_versioned(self, key: str, entry: CacheEntry) -> None:
        """S3-specific versioned set: serialize, compress, put with metadata."""
        client = self._get_client()
        s3_key = self._make_key(key, entry.entry_type)

        body, metadata, is_compressed = self._serialize_entry(entry)

        content_encoding = "gzip" if is_compressed else None
        put_kwargs: dict[str, Any] = {
            "Bucket": self._config.bucket,
            "Key": s3_key,
            "Body": body,
            "ContentType": "application/json",
            "Metadata": metadata,
        }
        if content_encoding:
            put_kwargs["ContentEncoding"] = content_encoding

        client.put_object(**put_kwargs)

    def get_batch(
        self,
        keys: list[str],
        entry_type: EntryType,
    ) -> dict[str, CacheEntry | None]:
        """Retrieve multiple entries in single operation.

        Note: S3 does not support true batch GET. This method makes
        individual requests for each key. For high-volume batch operations,
        consider using the Redis hot tier instead.

        Args:
            keys: List of cache keys.
            entry_type: Type of entries to retrieve.

        Returns:
            Dict mapping keys to CacheEntry or None if not found.
        """
        result: dict[str, CacheEntry | None] = {}
        if not keys:
            return result

        if self._degraded:
            return {key: None for key in keys}

        # S3 doesn't have batch GET, so we make individual requests
        for key in keys:
            result[key] = self.get_versioned(key, entry_type)

        return result

    def set_batch(
        self,
        entries: dict[str, CacheEntry],
    ) -> None:
        """Store multiple entries in single operation.

        Note: S3 does not support true batch PUT. This method makes
        individual requests for each entry. For high-volume batch operations,
        consider using the Redis hot tier instead.

        Args:
            entries: Dict mapping keys to CacheEntry objects.
        """
        if not entries:
            return

        if self._degraded:
            return

        # S3 doesn't have batch PUT, so we make individual requests
        for key, entry in entries.items():
            self.set_versioned(key, entry)

    def warm(
        self,
        gids: list[str],
        entry_types: list[EntryType] | None = None,
    ) -> WarmResult:
        """Pre-populate cache for specified GIDs and entry types.

        Note: Actual warming requires API calls which are out of scope
        for this implementation. This method returns a placeholder result.

        Args:
            gids: List of task GIDs to warm.
            entry_types: Entry types to fetch and cache.

        Returns:
            WarmResult with success/failure counts.
        """
        # Warming requires integration with Asana API clients
        # which is out of scope for the cache backend
        logger.info(
            "cache_warm_requested",
            extra={"gid_count": len(gids), "status": "not_implemented"},
        )
        return WarmResult(warmed=0, failed=0, skipped=len(gids))

    def check_freshness(
        self,
        key: str,
        entry_type: EntryType,
        current_version: datetime,
    ) -> bool:
        """Check if cached version matches current version.

        Uses S3 HEAD request to check metadata without downloading body.

        Args:
            key: Cache key.
            entry_type: Type of entry.
            current_version: Known current modified_at timestamp.

        Returns:
            True if cache is fresh, False if stale or missing.
        """
        try:
            if self._degraded:
                return False

            client = self._get_client()
            s3_key = self._make_key(key, entry_type)

            response = client.head_object(
                Bucket=self._config.bucket,
                Key=s3_key,
            )
            metadata = response.get("Metadata", {})
            cached_version_str = metadata.get("version")

            if not cached_version_str:
                return False

            cached_version = parse_version(cached_version_str)
            return is_current(cached_version, current_version)

        except S3_TRANSPORT_ERRORS as e:
            if self._is_not_found_error(e):
                return False
            self._handle_transport_error(e, operation="check_freshness", key=key)
            return False

    def invalidate(
        self,
        key: str,
        entry_types: list[EntryType] | None = None,
    ) -> None:
        """Invalidate cache entries for a key.

        Args:
            key: Cache key (task GID).
            entry_types: Specific types to invalidate. If None, all types.
        """
        try:
            if self._degraded:
                return

            client = self._get_client()

            if entry_types is None:
                entry_types = list(EntryType)

            for entry_type in entry_types:
                s3_key = self._make_key(key, entry_type)
                try:
                    client.delete_object(
                        Bucket=self._config.bucket,
                        Key=s3_key,
                    )
                    self._metrics.record_eviction(key=key, entry_type=entry_type.value)
                except S3_TRANSPORT_ERRORS:
                    # Continue with other entry types even if one fails
                    logger.warning(
                        "s3_invalidate_entry_delete_failed",
                        exc_info=True,
                        extra={
                            "key": key,
                            "entry_type": entry_type.value,
                            "s3_key": s3_key,
                        },
                    )

        except S3_TRANSPORT_ERRORS as e:
            self._metrics.record_error(key=key, error_message=str(e))
            self._handle_transport_error(e, operation="invalidate", key=key)

    def is_healthy(self) -> bool:
        """Check if cache backend is operational.

        When a connection_manager is provided, delegates health check to it.

        Returns:
            True if S3 is healthy and bucket is accessible.
        """
        if self._connection_manager is not None:
            from autom8_asana.core.connections import ConnectionState

            result = self._connection_manager.health_check()
            is_healthy: bool = result.state == ConnectionState.HEALTHY
            return is_healthy

        if self._degraded or self._boto3_module is None:
            return False

        try:
            client = self._get_client()
            client.head_bucket(Bucket=self._config.bucket)
            return True
        except S3_TRANSPORT_ERRORS:
            return False

    def _is_not_found_error(self, error: Exception) -> bool:
        """Check if error indicates object not found."""
        return is_s3_not_found_error(error)

    def _handle_transport_error(
        self, error: Exception, *, operation: str = "unknown", key: str | None = None
    ) -> None:
        """Handle S3 errors and potentially enter degraded mode.

        Wraps vendor exceptions into S3TransportError for structured context.
        Does not change control flow -- degraded mode transitions remain the same.

        Args:
            error: The exception that occurred.
            operation: The S3 operation that failed (get, set, delete, etc.).
            key: The S3 key involved, if applicable.
        """
        # Wrap into domain exception for structured context
        wrapped = S3TransportError.from_boto_error(
            error, operation=operation, bucket=self._config.bucket, key=key
        )

        extra_types: tuple[type[Exception], ...] = ()

        # Check for boto3-specific errors
        if self._botocore_module is not None:
            # Common boto3/botocore exceptions
            no_credentials = getattr(
                self._botocore_module, "NoCredentialsError", Exception
            )
            partial_credentials = getattr(
                self._botocore_module, "PartialCredentialsError", Exception
            )
            client_error = getattr(self._botocore_module, "ClientError", Exception)
            endpoint_error = getattr(
                self._botocore_module, "EndpointConnectionError", Exception
            )
            connect_timeout = getattr(
                self._botocore_module, "ConnectTimeoutError", Exception
            )
            read_timeout = getattr(self._botocore_module, "ReadTimeoutError", Exception)

            extra_types = (
                no_credentials,
                partial_credentials,
                endpoint_error,
                connect_timeout,
                read_timeout,
            )

            # ClientError needs special handling - check error code
            if isinstance(error, client_error):
                error_code = error.response.get("Error", {}).get("Code", "")  # type: ignore[attr-defined]
                # Don't enter degraded mode for expected errors like 404
                if error_code in ("NoSuchKey", "404", "NotFound"):
                    return
                # Access denied or bucket not found are more serious
                if error_code in ("AccessDenied", "NoSuchBucket"):
                    self.enter_degraded_mode(str(error))
                    return

        if is_connection_error(error, extra_types=extra_types):
            self.enter_degraded_mode(str(error))
        else:
            logger.error(
                "s3_error",
                extra={
                    "error": str(error),
                    "error_type": type(error).__name__,
                    **wrapped.context,
                },
            )

    def clear_all_tasks(self) -> int:
        """Clear all task entries from S3 cache.

        Deletes all objects under the tasks/ prefix. Used for cache
        invalidation when cached data becomes stale or corrupted
        (e.g., missing required fields like memberships).

        Returns:
            Count of objects deleted.

        Raises:
            RuntimeError: If S3 client is not available.
        """
        if self._degraded:
            logger.warning("clear_all_tasks called while in degraded mode")
            return 0

        try:
            client = self._get_client()
            prefix = f"{self._config.prefix}/tasks/"
            deleted_count = 0

            # List and delete objects in batches (S3 allows up to 1000 per delete)
            paginator = client.get_paginator("list_objects_v2")

            for page in paginator.paginate(Bucket=self._config.bucket, Prefix=prefix):
                objects = page.get("Contents", [])
                if not objects:
                    continue

                # Build delete request
                delete_keys = [{"Key": obj["Key"]} for obj in objects]

                response = client.delete_objects(
                    Bucket=self._config.bucket,
                    Delete={"Objects": delete_keys, "Quiet": True},
                )

                # Count successful deletions
                deleted_count += len(delete_keys) - len(response.get("Errors", []))

                # Log any errors
                for error in response.get("Errors", []):
                    logger.warning(
                        "s3_delete_error",
                        extra={
                            "key": error.get("Key"),
                            "code": error.get("Code"),
                            "message": error.get("Message"),
                        },
                    )

            logger.info(
                "s3_clear_all_tasks_complete",
                extra={
                    "deleted_count": deleted_count,
                    "bucket": self._config.bucket,
                    "prefix": prefix,
                },
            )

            return deleted_count

        except S3_TRANSPORT_ERRORS as e:
            logger.error(
                "s3_clear_all_tasks_failed",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            self._handle_transport_error(e, operation="clear_all_tasks")
            return 0
