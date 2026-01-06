"""S3 tier for DataFrame cold storage with Parquet format.

Per TDD-DATAFRAME-CACHE-001: S3 as source of truth with Parquet serialization.
Schema evolution: superset OK (new columns acceptable).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

    from autom8_asana.cache.dataframe_cache import CacheEntry

logger = get_logger(__name__)


@dataclass
class S3Tier:
    """S3 tier with Parquet serialization.

    Per TDD-DATAFRAME-CACHE-001:
    - Parquet format for efficient columnar storage
    - Schema evolution: new columns acceptable (superset OK)
    - Strict startup: fail if S3 read fails

    Key format: {prefix}{entity_type}:{project_gid}.parquet

    Metadata stored in S3 object metadata:
    - project_gid: Asana project GID
    - entity_type: Entity type identifier
    - watermark: ISO datetime freshness watermark
    - created_at: ISO datetime cache entry creation
    - schema_version: Schema version for invalidation
    - row_count: Number of rows (for observability)

    Attributes:
        bucket: S3 bucket name.
        prefix: Key prefix for DataFrame storage.
        s3_client: boto3 S3 client (injected for testing).

    Example:
        >>> tier = S3Tier(
        ...     bucket="autom8-cache",
        ...     prefix="dataframes/v1/",
        ...     s3_client=boto3.client("s3"),
        ... )
        >>> await tier.put_async("unit:proj-123", entry)
        >>> entry = await tier.get_async("unit:proj-123")
    """

    bucket: str
    prefix: str = "dataframes/"
    s3_client: "S3Client | None" = None

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)
    _initialized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Initialize statistics and optionally create S3 client."""
        self._stats = {
            "reads": 0,
            "writes": 0,
            "read_errors": 0,
            "write_errors": 0,
            "bytes_read": 0,
            "bytes_written": 0,
            "not_found": 0,
        }
        self._initialized = False

    def _ensure_client(self) -> "S3Client":
        """Lazily initialize S3 client if not provided.

        Returns:
            Initialized S3 client.
        """
        if self.s3_client is None:
            import boto3

            self.s3_client = boto3.client("s3")
            self._initialized = True
        return self.s3_client

    async def get_async(self, key: str) -> "CacheEntry | None":
        """Get entry from S3.

        Note: This method is async for interface consistency but uses
        synchronous boto3 calls. Future optimization could use aioboto3.

        Args:
            key: Cache key (entity_type:project_gid).

        Returns:
            CacheEntry if found, None on error or not found.
        """
        from autom8_asana.cache.dataframe_cache import CacheEntry

        s3_key = f"{self.prefix}{key}.parquet"
        client = self._ensure_client()

        try:
            self._stats["reads"] += 1

            response = client.get_object(
                Bucket=self.bucket,
                Key=s3_key,
            )

            # Read Parquet bytes
            body = response["Body"].read()
            self._stats["bytes_read"] += len(body)

            # Parse DataFrame
            df = pl.read_parquet(io.BytesIO(body))

            # Extract metadata from S3 object metadata
            metadata = response.get("Metadata", {})

            # Parse timestamps with fallbacks
            watermark_str = metadata.get("watermark")
            created_at_str = metadata.get("created_at")

            watermark = self._parse_datetime(watermark_str)
            created_at = self._parse_datetime(created_at_str)

            # Parse key to get project_gid and entity_type if not in metadata
            key_parts = key.split(":")
            default_entity_type = key_parts[0] if len(key_parts) > 0 else "unknown"
            default_project_gid = key_parts[1] if len(key_parts) > 1 else "unknown"

            entry = CacheEntry(
                project_gid=metadata.get("project_gid", default_project_gid),
                entity_type=metadata.get("entity_type", default_entity_type),
                dataframe=df,
                watermark=watermark,
                created_at=created_at,
                schema_version=metadata.get("schema_version", "unknown"),
            )

            logger.debug(
                "s3_tier_get_success",
                extra={
                    "key": key,
                    "row_count": entry.row_count,
                    "bytes": len(body),
                },
            )

            return entry

        except client.exceptions.NoSuchKey:
            self._stats["not_found"] += 1
            logger.debug("s3_tier_not_found", extra={"key": key})
            return None

        except Exception as e:
            self._stats["read_errors"] += 1
            logger.warning(
                "s3_tier_get_error",
                extra={"key": key, "error": str(e), "error_type": type(e).__name__},
            )
            return None

    async def put_async(
        self,
        key: str,
        entry: "CacheEntry",
    ) -> bool:
        """Store entry in S3.

        Note: This method is async for interface consistency but uses
        synchronous boto3 calls. Future optimization could use aioboto3.

        Args:
            key: Cache key (entity_type:project_gid).
            entry: CacheEntry to store.

        Returns:
            True on success, False on failure.
        """
        s3_key = f"{self.prefix}{key}.parquet"
        client = self._ensure_client()

        try:
            self._stats["writes"] += 1

            # Serialize DataFrame to Parquet bytes
            buffer = io.BytesIO()
            entry.dataframe.write_parquet(buffer)
            body = buffer.getvalue()

            self._stats["bytes_written"] += len(body)

            # Store with metadata
            # Note: S3 metadata values must be strings
            client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=body,
                ContentType="application/x-parquet",
                Metadata={
                    "project_gid": entry.project_gid,
                    "entity_type": entry.entity_type,
                    "watermark": entry.watermark.isoformat(),
                    "created_at": entry.created_at.isoformat(),
                    "schema_version": entry.schema_version,
                    "row_count": str(entry.row_count),
                },
            )

            logger.info(
                "s3_tier_put_success",
                extra={
                    "key": key,
                    "row_count": entry.row_count,
                    "bytes": len(body),
                },
            )

            return True

        except Exception as e:
            self._stats["write_errors"] += 1
            logger.error(
                "s3_tier_put_error",
                extra={"key": key, "error": str(e), "error_type": type(e).__name__},
            )
            return False

    async def exists_async(self, key: str) -> bool:
        """Check if entry exists in S3.

        Args:
            key: Cache key (entity_type:project_gid).

        Returns:
            True if entry exists, False otherwise.
        """
        s3_key = f"{self.prefix}{key}.parquet"
        client = self._ensure_client()

        try:
            client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except Exception:
            return False

    async def delete_async(self, key: str) -> bool:
        """Delete entry from S3.

        Args:
            key: Cache key (entity_type:project_gid).

        Returns:
            True on success, False on failure.
        """
        s3_key = f"{self.prefix}{key}.parquet"
        client = self._ensure_client()

        try:
            client.delete_object(Bucket=self.bucket, Key=s3_key)
            return True
        except Exception as e:
            logger.warning(
                "s3_tier_delete_error",
                extra={"key": key, "error": str(e)},
            )
            return False

    def get_stats(self) -> dict[str, int]:
        """Get tier statistics."""
        return dict(self._stats)

    def _parse_datetime(self, value: str | None) -> datetime:
        """Parse ISO datetime string or return current time.

        Args:
            value: ISO format datetime string or None.

        Returns:
            Parsed datetime, or current UTC time if parsing fails.
        """
        if not value:
            return datetime.now(timezone.utc)

        try:
            # Handle Z suffix
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"

            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return datetime.now(timezone.utc)
