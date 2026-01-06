"""Section-level S3 persistence for progressive DataFrame cache warming.

Provides granular persistence at the section level, enabling:
- Progressive writes as sections complete (not waiting for full project)
- Resume capability from manifest on restart
- Section-targeted queries without loading full DataFrame

S3 Key Structure:
    dataframes/
    └── {project_gid}/
        ├── manifest.json          # Tracks section completion state
        ├── sections/
        │   ├── {section_gid_1}.parquet
        │   ├── {section_gid_2}.parquet
        │   └── ...
        ├── dataframe.parquet      # Final merged DataFrame
        ├── watermark.json
        └── gid_lookup_index.json

Thread Safety:
    Uses async operations throughout. Manifest updates are atomic per-section.

Example:
    >>> from autom8_asana.dataframes.section_persistence import SectionPersistence
    >>> import polars as pl
    >>>
    >>> persistence = SectionPersistence(bucket="my-bucket")
    >>> async with persistence:
    ...     # Start a new project build
    ...     await persistence.create_manifest_async("proj_123", "offer", ["sec_1", "sec_2"])
    ...
    ...     # Write sections as they complete
    ...     df = pl.DataFrame({"gid": ["123"], "name": ["Task"]})
    ...     await persistence.write_section_async("proj_123", "sec_1", df)
    ...
    ...     # Resume after restart
    ...     incomplete = await persistence.get_incomplete_sections("proj_123")
    ...     print(f"Need to fetch: {incomplete}")
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import TracebackType
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from autom8_asana.dataframes.async_s3 import AsyncS3Client, AsyncS3Config

if TYPE_CHECKING:
    import polars as pl

__all__ = [
    "SectionPersistence",
    "SectionManifest",
    "SectionStatus",
    "SectionInfo",
]

logger = logging.getLogger(__name__)


class SectionStatus(str, Enum):
    """Status of a section in the manifest."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class SectionInfo(BaseModel):
    """Information about a single section."""

    status: SectionStatus = SectionStatus.PENDING
    rows: int = 0
    written_at: datetime | None = None
    error: str | None = None

    model_config = {"use_enum_values": True}


class SectionManifest(BaseModel):
    """Manifest tracking section completion state for a project.

    Persisted to S3 at: dataframes/{project_gid}/manifest.json
    """

    project_gid: str
    entity_type: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sections: dict[str, SectionInfo] = Field(default_factory=dict)
    total_sections: int = 0
    completed_sections: int = 0
    version: int = 1

    model_config = {"use_enum_values": True}

    def get_incomplete_section_gids(self) -> list[str]:
        """Get list of section GIDs that need to be fetched."""
        return [
            gid
            for gid, info in self.sections.items()
            if info.status in (SectionStatus.PENDING, SectionStatus.FAILED)
        ]

    def get_complete_section_gids(self) -> list[str]:
        """Get list of section GIDs that are complete."""
        return [
            gid
            for gid, info in self.sections.items()
            if info.status == SectionStatus.COMPLETE
        ]

    def mark_section_complete(
        self,
        section_gid: str,
        rows: int,
    ) -> None:
        """Mark a section as complete."""
        self.sections[section_gid] = SectionInfo(
            status=SectionStatus.COMPLETE,
            rows=rows,
            written_at=datetime.now(timezone.utc),
        )
        self.completed_sections = len(self.get_complete_section_gids())

    def mark_section_failed(
        self,
        section_gid: str,
        error: str,
    ) -> None:
        """Mark a section as failed."""
        self.sections[section_gid] = SectionInfo(
            status=SectionStatus.FAILED,
            error=error,
        )

    def mark_section_in_progress(self, section_gid: str) -> None:
        """Mark a section as in progress."""
        if section_gid in self.sections:
            self.sections[section_gid].status = SectionStatus.IN_PROGRESS
        else:
            self.sections[section_gid] = SectionInfo(status=SectionStatus.IN_PROGRESS)

    def is_complete(self) -> bool:
        """Check if all sections are complete."""
        return self.completed_sections == self.total_sections


@dataclass
class SectionPersistenceConfig:
    """Configuration for section persistence.

    Attributes:
        bucket: S3 bucket name.
        prefix: Key prefix for persisted objects (default "dataframes/").
        region: AWS region (default "us-east-1").
        endpoint_url: Custom endpoint URL for LocalStack or S3-compatible storage.
    """

    bucket: str
    prefix: str = "dataframes/"
    region: str = "us-east-1"
    endpoint_url: str | None = None


class SectionPersistence:
    """Section-level S3 persistence for progressive DataFrame cache warming.

    Provides granular persistence at the section level with manifest tracking
    for resume capability.

    Example:
        >>> config = SectionPersistenceConfig(bucket="my-bucket")
        >>> persistence = SectionPersistence(config=config)
        >>> async with persistence:
        ...     manifest = await persistence.get_manifest_async("proj_123")
        ...     if manifest:
        ...         incomplete = manifest.get_incomplete_section_gids()
    """

    def __init__(
        self,
        config: SectionPersistenceConfig | None = None,
        *,
        bucket: str | None = None,
        prefix: str = "dataframes/",
        region: str | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        """Initialize section persistence.

        Args:
            config: Persistence configuration object (preferred).
            bucket: S3 bucket name (if config not provided).
            prefix: Key prefix (if config not provided).
            region: AWS region (if config not provided).
            endpoint_url: Custom endpoint URL (if config not provided).
        """
        if config is None:
            from autom8_asana.settings import get_settings

            s3_settings = get_settings().s3

            resolved_bucket = bucket if bucket is not None else s3_settings.bucket
            resolved_region = region if region is not None else s3_settings.region
            resolved_endpoint = (
                endpoint_url if endpoint_url is not None else s3_settings.endpoint_url
            )

            config = SectionPersistenceConfig(
                bucket=resolved_bucket or "",
                prefix=prefix,
                region=resolved_region,
                endpoint_url=resolved_endpoint,
            )

        self._config = config
        self._s3_client = AsyncS3Client(
            config=AsyncS3Config(
                bucket=config.bucket,
                region=config.region,
                endpoint_url=config.endpoint_url,
            )
        )
        # Initialize polars eagerly for is_available check
        self._polars_module: Any = None
        self._initialize_polars()

    async def __aenter__(self) -> "SectionPersistence":
        """Async context manager entry."""
        await self._s3_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self._s3_client.__aexit__(exc_type, exc_val, exc_tb)

    def _initialize_polars(self) -> None:
        """Initialize polars module."""
        try:
            import polars

            self._polars_module = polars
        except ImportError:
            logger.warning("polars not available for SectionPersistence")

    @property
    def is_available(self) -> bool:
        """Check if persistence can potentially be available.

        Uses can_be_available for pre-initialization check (bucket configured).
        Full availability (initialized, not degraded) checked at operation time.
        """
        return self._s3_client.can_be_available and self._polars_module is not None

    def _make_manifest_key(self, project_gid: str) -> str:
        """Generate S3 key for manifest."""
        return f"{self._config.prefix}{project_gid}/manifest.json"

    def _make_section_key(self, project_gid: str, section_gid: str) -> str:
        """Generate S3 key for section parquet."""
        return f"{self._config.prefix}{project_gid}/sections/{section_gid}.parquet"

    def _make_dataframe_key(self, project_gid: str) -> str:
        """Generate S3 key for final merged DataFrame."""
        return f"{self._config.prefix}{project_gid}/dataframe.parquet"

    def _make_watermark_key(self, project_gid: str) -> str:
        """Generate S3 key for watermark."""
        return f"{self._config.prefix}{project_gid}/watermark.json"

    def _make_index_key(self, project_gid: str) -> str:
        """Generate S3 key for GID lookup index."""
        return f"{self._config.prefix}{project_gid}/gid_lookup_index.json"

    # ========== Manifest Operations ==========

    async def create_manifest_async(
        self,
        project_gid: str,
        entity_type: str,
        section_gids: list[str],
    ) -> SectionManifest:
        """Create a new manifest for a project build.

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type (e.g., "offer", "contact").
            section_gids: List of section GIDs to track.

        Returns:
            Created SectionManifest.
        """
        manifest = SectionManifest(
            project_gid=project_gid,
            entity_type=entity_type,
            total_sections=len(section_gids),
            sections={gid: SectionInfo() for gid in section_gids},
        )

        await self._save_manifest_async(manifest)

        logger.info(
            "section_manifest_created",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "total_sections": len(section_gids),
            },
        )

        return manifest

    async def get_manifest_async(self, project_gid: str) -> SectionManifest | None:
        """Get manifest for a project.

        Args:
            project_gid: Asana project GID.

        Returns:
            SectionManifest if exists, None otherwise.
        """
        key = self._make_manifest_key(project_gid)
        result = await self._s3_client.get_object_async(key)

        if not result.success:
            if result.not_found:
                return None
            logger.warning(
                "Failed to get manifest for %s: %s",
                project_gid,
                result.error,
            )
            return None

        try:
            data = json.loads(result.data.decode("utf-8"))
            return SectionManifest.model_validate(data)
        except Exception as e:
            logger.error("Failed to parse manifest for %s: %s", project_gid, e)
            return None

    async def _save_manifest_async(self, manifest: SectionManifest) -> bool:
        """Save manifest to S3."""
        key = self._make_manifest_key(manifest.project_gid)
        data = manifest.model_dump_json(indent=2).encode("utf-8")

        result = await self._s3_client.put_object_async(
            key=key,
            body=data,
            content_type="application/json",
        )

        if not result.success:
            logger.error(
                "Failed to save manifest for %s: %s",
                manifest.project_gid,
                result.error,
            )
        return result.success

    async def update_manifest_section_async(
        self,
        project_gid: str,
        section_gid: str,
        status: SectionStatus,
        rows: int = 0,
        error: str | None = None,
    ) -> SectionManifest | None:
        """Update a section's status in the manifest.

        Args:
            project_gid: Asana project GID.
            section_gid: Section GID to update.
            status: New status for the section.
            rows: Row count (for complete status).
            error: Error message (for failed status).

        Returns:
            Updated manifest, or None on error.
        """
        manifest = await self.get_manifest_async(project_gid)
        if manifest is None:
            logger.warning("No manifest found for %s", project_gid)
            return None

        if status == SectionStatus.COMPLETE:
            manifest.mark_section_complete(section_gid, rows)
        elif status == SectionStatus.FAILED:
            manifest.mark_section_failed(section_gid, error or "Unknown error")
        elif status == SectionStatus.IN_PROGRESS:
            manifest.mark_section_in_progress(section_gid)
        else:
            manifest.sections[section_gid] = SectionInfo(status=status)

        await self._save_manifest_async(manifest)

        logger.info(
            "section_status_updated",
            extra={
                "project_gid": project_gid,
                "section_gid": section_gid,
                "status": status.value,
                "rows": rows,
                "completed": f"{manifest.completed_sections}/{manifest.total_sections}",
            },
        )

        return manifest

    async def get_incomplete_sections(self, project_gid: str) -> list[str]:
        """Get list of incomplete section GIDs for resume capability.

        Args:
            project_gid: Asana project GID.

        Returns:
            List of section GIDs that need to be fetched.
        """
        manifest = await self.get_manifest_async(project_gid)
        if manifest is None:
            return []
        return manifest.get_incomplete_section_gids()

    # ========== Section DataFrame Operations ==========

    async def write_section_async(
        self,
        project_gid: str,
        section_gid: str,
        df: "pl.DataFrame",
    ) -> bool:
        """Write a section DataFrame to S3.

        Args:
            project_gid: Asana project GID.
            section_gid: Section GID.
            df: Polars DataFrame for this section.

        Returns:
            True if written successfully.
        """
        if self._polars_module is None:
            logger.warning("polars not available, cannot write section")
            return False

        # Serialize to parquet
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        buffer.seek(0)
        parquet_bytes = buffer.read()

        key = self._make_section_key(project_gid, section_gid)
        result = await self._s3_client.put_object_async(
            key=key,
            body=parquet_bytes,
            content_type="application/octet-stream",
            metadata={
                "project-gid": project_gid,
                "section-gid": section_gid,
                "row-count": str(len(df)),
            },
        )

        if result.success:
            logger.info(
                "section_s3_write_completed",
                extra={
                    "project_gid": project_gid,
                    "section_gid": section_gid,
                    "s3_key": key,
                    "size_bytes": result.size_bytes,
                    "write_time_ms": round(result.duration_ms, 2),
                    "throughput_mbps": round(result.throughput_mbps, 2),
                    "row_count": len(df),
                },
            )

            # Update manifest
            await self.update_manifest_section_async(
                project_gid,
                section_gid,
                SectionStatus.COMPLETE,
                rows=len(df),
            )
        else:
            logger.error(
                "section_s3_write_failed",
                extra={
                    "project_gid": project_gid,
                    "section_gid": section_gid,
                    "error": result.error,
                },
            )

            # Mark as failed in manifest
            await self.update_manifest_section_async(
                project_gid,
                section_gid,
                SectionStatus.FAILED,
                error=result.error,
            )

        return result.success

    async def read_section_async(
        self,
        project_gid: str,
        section_gid: str,
    ) -> "pl.DataFrame | None":
        """Read a section DataFrame from S3.

        Args:
            project_gid: Asana project GID.
            section_gid: Section GID.

        Returns:
            Polars DataFrame if found, None otherwise.
        """
        if self._polars_module is None:
            logger.warning("polars not available, cannot read section")
            return None

        key = self._make_section_key(project_gid, section_gid)
        result = await self._s3_client.get_object_async(key)

        if not result.success:
            if result.not_found:
                return None
            logger.warning(
                "Failed to read section %s/%s: %s",
                project_gid,
                section_gid,
                result.error,
            )
            return None

        try:
            buffer = io.BytesIO(result.data)
            return self._polars_module.read_parquet(buffer)
        except Exception as e:
            logger.error(
                "Failed to parse section parquet %s/%s: %s",
                project_gid,
                section_gid,
                e,
            )
            return None

    async def read_all_sections_async(
        self,
        project_gid: str,
    ) -> list["pl.DataFrame"]:
        """Read all complete section DataFrames for a project.

        Args:
            project_gid: Asana project GID.

        Returns:
            List of section DataFrames (empty if none complete).
        """
        manifest = await self.get_manifest_async(project_gid)
        if manifest is None:
            return []

        complete_sections = manifest.get_complete_section_gids()
        if not complete_sections:
            return []

        dfs = []
        for section_gid in complete_sections:
            df = await self.read_section_async(project_gid, section_gid)
            if df is not None:
                dfs.append(df)

        logger.info(
            "read_all_sections_completed",
            extra={
                "project_gid": project_gid,
                "sections_read": len(dfs),
                "total_complete": len(complete_sections),
            },
        )

        return dfs

    # ========== Merge Operations ==========

    async def merge_sections_to_dataframe_async(
        self,
        project_gid: str,
    ) -> "pl.DataFrame | None":
        """Merge all complete sections into a single DataFrame.

        Used after all sections are complete to create the final merged
        DataFrame for the project.

        Args:
            project_gid: Asana project GID.

        Returns:
            Merged DataFrame, or None if no sections or error.
        """
        if self._polars_module is None:
            logger.warning("polars not available, cannot merge sections")
            return None

        section_dfs = await self.read_all_sections_async(project_gid)
        if not section_dfs:
            logger.warning("No sections to merge for %s", project_gid)
            return None

        try:
            # Use how="diagonal_relaxed" to handle type mismatches between sections
            # (e.g., Null vs String when one section has empty values for a column)
            merged = self._polars_module.concat(section_dfs, how="diagonal_relaxed")

            logger.info(
                "sections_merged",
                extra={
                    "project_gid": project_gid,
                    "sections_merged": len(section_dfs),
                    "total_rows": len(merged),
                },
            )

            return merged
        except Exception as e:
            logger.error("Failed to merge sections for %s: %s", project_gid, e)
            return None

    # ========== Final Atomic Write Operations ==========

    async def write_final_artifacts_async(
        self,
        project_gid: str,
        df: "pl.DataFrame",
        watermark: datetime,
        index_data: dict[str, Any] | None = None,
    ) -> bool:
        """Write final artifacts atomically (DataFrame + watermark + optional index).

        Called after all sections are complete and merged.

        Args:
            project_gid: Asana project GID.
            df: Final merged DataFrame.
            watermark: Watermark timestamp.
            index_data: Optional serialized GidLookupIndex data.

        Returns:
            True if all artifacts written successfully.
        """
        if self._polars_module is None:
            logger.warning("polars not available, cannot write final artifacts")
            return False

        success = True

        # 1. Write DataFrame
        buffer = io.BytesIO()
        df.write_parquet(buffer)
        buffer.seek(0)
        parquet_bytes = buffer.read()

        df_key = self._make_dataframe_key(project_gid)
        df_result = await self._s3_client.put_object_async(
            key=df_key,
            body=parquet_bytes,
            content_type="application/octet-stream",
            metadata={
                "project-gid": project_gid,
                "row-count": str(len(df)),
                "watermark": watermark.isoformat(),
            },
        )
        success = success and df_result.success

        # 2. Write watermark
        watermark_data = {
            "project_gid": project_gid,
            "watermark": watermark.isoformat(),
            "row_count": len(df),
            "columns": df.columns,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        wm_key = self._make_watermark_key(project_gid)
        wm_result = await self._s3_client.put_object_async(
            key=wm_key,
            body=json.dumps(watermark_data).encode("utf-8"),
            content_type="application/json",
        )
        success = success and wm_result.success

        # 3. Write index if provided
        if index_data is not None:
            idx_key = self._make_index_key(project_gid)
            idx_result = await self._s3_client.put_object_async(
                key=idx_key,
                body=json.dumps(index_data).encode("utf-8"),
                content_type="application/json",
            )
            success = success and idx_result.success

        if success:
            logger.info(
                "final_artifacts_written",
                extra={
                    "project_gid": project_gid,
                    "dataframe_key": df_key,
                    "watermark_key": wm_key,
                    "row_count": len(df),
                    "watermark": watermark.isoformat(),
                    "index_written": index_data is not None,
                },
            )
        else:
            logger.error(
                "final_artifacts_write_failed",
                extra={
                    "project_gid": project_gid,
                    "df_success": df_result.success,
                    "wm_success": wm_result.success,
                },
            )

        return success

    # ========== Cleanup Operations ==========

    async def delete_section_files_async(self, project_gid: str) -> bool:
        """Delete all section files for a project.

        Optionally called after final merge if section files are no longer needed.
        Based on plan decision: Keep section files forever for targeted queries.

        Args:
            project_gid: Asana project GID.

        Returns:
            True if all deletions succeeded or no sections to delete.
        """
        manifest = await self.get_manifest_async(project_gid)
        if manifest is None:
            return True

        success = True
        for section_gid in manifest.sections:
            key = self._make_section_key(project_gid, section_gid)
            if not await self._s3_client.delete_object_async(key):
                success = False

        logger.info(
            "section_files_deleted",
            extra={
                "project_gid": project_gid,
                "sections_deleted": len(manifest.sections),
                "success": success,
            },
        )

        return success

    async def delete_manifest_async(self, project_gid: str) -> bool:
        """Delete manifest for a project.

        Args:
            project_gid: Asana project GID.

        Returns:
            True if deleted or didn't exist.
        """
        key = self._make_manifest_key(project_gid)
        return await self._s3_client.delete_object_async(key)
