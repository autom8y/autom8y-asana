"""Progressive tier for DataFrame cache using SectionPersistence storage.

Per TDD-UNIFIED-PROGRESSIVE-CACHE-001: Replaces S3Tier to read from the same
storage location as ProgressiveProjectBuilder, eliminating the dual-location bug.

Key format translation:
    "{entity_type}:{project_gid}" -> "dataframes/{project_gid}/"

Read path:
    1. Parse cache key to extract project_gid
    2. Read dataframes/{project_gid}/dataframe.parquet
    3. Read dataframes/{project_gid}/watermark.json for metadata
    4. Construct CacheEntry with DataFrame and metadata

Write path:
    1. Delegate to SectionPersistence.write_final_artifacts_async()
    2. Ensures consistency with ProgressiveProjectBuilder writes
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import polars as pl
from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.dataframe_cache import CacheEntry
    from autom8_asana.dataframes.section_persistence import SectionPersistence

__all__ = ["ProgressiveTier"]

logger = get_logger(__name__)


@dataclass
class ProgressiveTier:
    """S3 tier using SectionPersistence storage structure.

    Replaces S3Tier to use the same storage location as
    ProgressiveProjectBuilder, eliminating the dual-location bug.

    Key format translation:
        "{entity_type}:{project_gid}" -> "dataframes/{project_gid}/"

    Read path:
        1. Parse cache key to extract project_gid
        2. Read dataframes/{project_gid}/dataframe.parquet
        3. Read dataframes/{project_gid}/watermark.json for metadata
        4. Construct CacheEntry with DataFrame and metadata

    Write path:
        1. Delegate to SectionPersistence.write_final_artifacts_async()
        2. Ensures consistency with ProgressiveProjectBuilder writes

    Attributes:
        persistence: SectionPersistence instance for S3 operations.
        _stats: Operation statistics (reads, writes, errors, etc.).

    Example:
        >>> from autom8_asana.dataframes.section_persistence import SectionPersistence
        >>> persistence = SectionPersistence(bucket="my-bucket")
        >>> tier = ProgressiveTier(persistence=persistence)
        >>> async with persistence:
        ...     entry = await tier.get_async("unit:proj-123")
    """

    persistence: "SectionPersistence"
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize statistics."""
        self._stats = {
            "reads": 0,
            "writes": 0,
            "read_errors": 0,
            "write_errors": 0,
            "bytes_read": 0,
            "bytes_written": 0,
            "not_found": 0,
        }

    def _parse_key(self, key: str) -> tuple[str, str]:
        """Parse cache key into entity_type and project_gid.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            Tuple of (entity_type, project_gid).

        Raises:
            ValueError: If key format is invalid.

        Examples:
            "unit:1234567890" -> ("unit", "1234567890")
            "offer:9876543210" -> ("offer", "9876543210")
            "asset_edit:5555555555" -> ("asset_edit", "5555555555")
        """
        parts = key.split(":", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid cache key format: {key}")
        return parts[0], parts[1]

    async def get_async(self, key: str) -> "CacheEntry | None":
        """Get entry from progressive storage location.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            CacheEntry if found and readable, None otherwise.

        Algorithm:
            1. Parse key: "unit:1234567890" -> project_gid="1234567890"
            2. Read dataframe: dataframes/1234567890/dataframe.parquet
            3. Read watermark: dataframes/1234567890/watermark.json
            4. Construct CacheEntry with metadata from watermark
            5. Return None on any error (graceful degradation)
        """
        from autom8_asana.cache.dataframe_cache import CacheEntry

        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError as e:
            logger.warning(
                "progressive_tier_invalid_key",
                extra={"key": key, "error": str(e)},
            )
            self._stats["read_errors"] += 1
            return None

        self._stats["reads"] += 1

        # Read DataFrame parquet via SectionPersistence's internal S3 client
        df_key = f"{self.persistence._config.prefix}{project_gid}/dataframe.parquet"
        df_result = await self.persistence._s3_client.get_object_async(df_key)

        if not df_result.success:
            if df_result.not_found:
                self._stats["not_found"] += 1
                logger.debug(
                    "progressive_tier_not_found",
                    extra={"key": key, "s3_key": df_key},
                )
                return None
            self._stats["read_errors"] += 1
            logger.warning(
                "progressive_tier_read_error",
                extra={"key": key, "s3_key": df_key, "error": df_result.error},
            )
            return None

        # Parse DataFrame from parquet bytes
        try:
            df = pl.read_parquet(io.BytesIO(df_result.data))
            self._stats["bytes_read"] += len(df_result.data)
        except Exception as e:
            self._stats["read_errors"] += 1
            logger.warning(
                "progressive_tier_parse_error",
                extra={"key": key, "error": str(e)},
            )
            return None

        # Read watermark metadata
        wm_key = f"{self.persistence._config.prefix}{project_gid}/watermark.json"
        wm_result = await self.persistence._s3_client.get_object_async(wm_key)

        if wm_result.success:
            try:
                watermark_data = json.loads(wm_result.data.decode("utf-8"))
                watermark = self._parse_datetime(watermark_data.get("watermark"))
                schema_version = watermark_data.get("schema_version", "unknown")
            except Exception:
                # Fallback to current time if watermark parsing fails
                watermark = datetime.now(timezone.utc)
                schema_version = "unknown"
        else:
            # No watermark file - use current time
            watermark = datetime.now(timezone.utc)
            schema_version = "unknown"

        entry = CacheEntry(
            project_gid=project_gid,
            entity_type=entity_type,
            dataframe=df,
            watermark=watermark,
            created_at=watermark,  # Use watermark as created_at for consistency
            schema_version=schema_version,
        )

        logger.debug(
            "progressive_tier_read_success",
            extra={
                "key": key,
                "row_count": entry.row_count,
                "bytes_read": len(df_result.data),
                "duration_ms": df_result.duration_ms,
            },
        )

        return entry

    async def put_async(self, key: str, entry: "CacheEntry") -> bool:
        """Store entry to progressive storage location.

        Delegates to SectionPersistence.write_final_artifacts_async() to ensure
        consistency with ProgressiveProjectBuilder writes.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".
            entry: CacheEntry containing DataFrame and metadata.

        Returns:
            True if written successfully, False on error.
        """
        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError as e:
            logger.warning(
                "progressive_tier_put_invalid_key",
                extra={"key": key, "error": str(e)},
            )
            self._stats["write_errors"] += 1
            return False

        self._stats["writes"] += 1

        try:
            # Delegate to SectionPersistence for consistent writes
            success = await self.persistence.write_final_artifacts_async(
                project_gid=project_gid,
                df=entry.dataframe,
                watermark=entry.watermark,
                index_data=None,  # Index is built lazily, not stored with cache
            )

            if success:
                # Estimate bytes written from DataFrame size
                buffer = io.BytesIO()
                entry.dataframe.write_parquet(buffer)
                self._stats["bytes_written"] += len(buffer.getvalue())

                logger.info(
                    "progressive_tier_put_success",
                    extra={
                        "key": key,
                        "row_count": entry.row_count,
                        "watermark": entry.watermark.isoformat(),
                    },
                )
            else:
                self._stats["write_errors"] += 1
                logger.error(
                    "progressive_tier_put_error",
                    extra={"key": key, "project_gid": project_gid},
                )

            return success

        except Exception as e:
            self._stats["write_errors"] += 1
            logger.error(
                "progressive_tier_put_exception",
                extra={"key": key, "error": str(e), "error_type": type(e).__name__},
            )
            return False

    async def exists_async(self, key: str) -> bool:
        """Check if entry exists.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            True if dataframe.parquet exists for project.
        """
        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError:
            return False

        df_key = f"{self.persistence._config.prefix}{project_gid}/dataframe.parquet"
        result = await self.persistence._s3_client.head_object_async(df_key)
        return result is not None

    async def delete_async(self, key: str) -> bool:
        """Delete entry (dataframe + watermark files).

        Does not delete section files or manifest to preserve resume capability.

        Args:
            key: Cache key in format "{entity_type}:{project_gid}".

        Returns:
            True if deleted or didn't exist.
        """
        try:
            entity_type, project_gid = self._parse_key(key)
        except ValueError as e:
            logger.warning(
                "progressive_tier_delete_invalid_key",
                extra={"key": key, "error": str(e)},
            )
            return False

        success = True

        # Delete dataframe.parquet
        df_key = f"{self.persistence._config.prefix}{project_gid}/dataframe.parquet"
        if not await self.persistence._s3_client.delete_object_async(df_key):
            success = False

        # Delete watermark.json
        wm_key = f"{self.persistence._config.prefix}{project_gid}/watermark.json"
        if not await self.persistence._s3_client.delete_object_async(wm_key):
            success = False

        if success:
            logger.info(
                "progressive_tier_delete_success",
                extra={"key": key, "project_gid": project_gid},
            )
        else:
            logger.warning(
                "progressive_tier_delete_partial",
                extra={"key": key, "project_gid": project_gid},
            )

        return success

    def get_stats(self) -> dict[str, int]:
        """Get tier statistics.

        Returns:
            Dict with keys: reads, writes, read_errors, write_errors,
            bytes_read, bytes_written, not_found.
        """
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
