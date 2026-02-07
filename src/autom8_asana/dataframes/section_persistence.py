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
    Uses per-project asyncio.Lock to serialize manifest read-modify-write cycles.
    An in-memory cache eliminates redundant S3 reads within the same event loop.

Example:
    >>> from autom8_asana.dataframes.storage import S3DataFrameStorage
    >>> from autom8_asana.config import S3LocationConfig
    >>> from autom8_asana.dataframes.section_persistence import SectionPersistence
    >>> import polars as pl
    >>>
    >>> location = S3LocationConfig(bucket="my-bucket")
    >>> storage = S3DataFrameStorage(location=location)
    >>> persistence = SectionPersistence(storage=storage)
    >>> # Start a new project build
    >>> await persistence.create_manifest_async("proj_123", "offer", ["sec_1", "sec_2"])
    >>> # Write sections as they complete
    >>> df = pl.DataFrame({"gid": ["123"], "name": ["Task"]})
    >>> await persistence.write_section_async("proj_123", "sec_1", df)
    >>> # Resume after restart
    >>> incomplete = await persistence.get_incomplete_sections("proj_123")
    >>> print(f"Need to fetch: {incomplete}")
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import polars as pl

from autom8_asana.dataframes.storage import DataFrameStorage

__all__ = [
    "SectionPersistence",
    "SectionManifest",
    "SectionStatus",
    "SectionInfo",
    "create_section_persistence",
]

logger = get_logger(__name__)


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
    watermark: datetime | None = None
    gid_hash: str | None = None
    name: str | None = None
    in_progress_since: datetime | None = None

    # Checkpoint tracking fields (per TDD-large-section-resilience D3)
    last_fetched_offset: int = 0
    rows_fetched: int = 0
    chunks_checkpointed: int = 0

    model_config = {"use_enum_values": True}


class SectionManifest(BaseModel):
    """Manifest tracking section completion state for a project.

    Persisted to S3 at: dataframes/{project_gid}/manifest.json
    """

    project_gid: str
    entity_type: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sections: dict[str, SectionInfo] = Field(default_factory=dict)
    total_sections: int = 0
    completed_sections: int = 0
    version: int = 1
    schema_version: str = ""

    model_config = {"use_enum_values": True}

    def is_schema_compatible(self, current_schema_version: str) -> bool:
        """Check if manifest schema is compatible with current version.

        Returns False for legacy manifests (empty schema_version) to force rebuild.

        Args:
            current_schema_version: The current schema version to compare against.

        Returns:
            True if compatible, False if rebuild needed.
        """
        if not self.schema_version:
            return False  # Legacy manifest - force rebuild
        return self.schema_version == current_schema_version

    def get_incomplete_section_gids(
        self, *, stale_timeout_seconds: int = 300
    ) -> list[str]:
        """Get list of section GIDs that need to be fetched.

        Includes PENDING, FAILED, and IN_PROGRESS sections that have been
        stuck longer than stale_timeout_seconds (default 5 minutes).
        Per ADR-HOTFIX-001: prevents permanent deadlock from orphaned
        IN_PROGRESS sections after process death.

        Args:
            stale_timeout_seconds: Seconds after which an IN_PROGRESS
                section is considered stuck and retryable. Default 300 (5 min).
        """
        now = datetime.now(UTC)
        result: list[str] = []
        for gid, info in self.sections.items():
            if info.status in (SectionStatus.PENDING, SectionStatus.FAILED):
                result.append(gid)
            elif info.status == SectionStatus.IN_PROGRESS:
                # Treat as stuck if no timestamp (legacy) or older than threshold
                if info.in_progress_since is None:
                    result.append(gid)
                elif (now - info.in_progress_since).total_seconds() > stale_timeout_seconds:
                    result.append(gid)
        return result

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
        *,
        watermark: datetime | None = None,
        gid_hash: str | None = None,
    ) -> None:
        """Mark a section as complete."""
        self.sections[section_gid] = SectionInfo(
            status=SectionStatus.COMPLETE,
            rows=rows,
            written_at=datetime.now(UTC),
            watermark=watermark,
            gid_hash=gid_hash,
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
        now = datetime.now(UTC)
        if section_gid in self.sections:
            self.sections[section_gid].status = SectionStatus.IN_PROGRESS
            self.sections[section_gid].in_progress_since = now
        else:
            self.sections[section_gid] = SectionInfo(
                status=SectionStatus.IN_PROGRESS,
                in_progress_since=now,
            )

    def is_complete(self) -> bool:
        """Check if all sections are complete."""
        return self.completed_sections == self.total_sections

    def get_section_name_index(self) -> dict[str, str]:
        """Return a ``{name.lower(): gid}`` mapping for sections with names."""
        return {
            info.name.lower(): gid for gid, info in self.sections.items() if info.name
        }


class SectionPersistence:
    """Section-level S3 persistence for progressive DataFrame cache warming.

    Provides granular persistence at the section level with manifest tracking
    for resume capability. All S3 I/O is delegated to a DataFrameStorage
    implementation (per TDD-I11, ADR-I11-001).

    Example:
        >>> from autom8_asana.dataframes.storage import S3DataFrameStorage
        >>> from autom8_asana.config import S3LocationConfig
        >>> location = S3LocationConfig(bucket="my-bucket")
        >>> storage = S3DataFrameStorage(location=location)
        >>> persistence = SectionPersistence(storage=storage)
        >>> manifest = await persistence.get_manifest_async("proj_123")
        >>> if manifest:
        ...     incomplete = manifest.get_incomplete_section_gids()
    """

    def __init__(
        self,
        storage: DataFrameStorage,
        *,
        prefix: str = "dataframes/",
    ) -> None:
        """Initialize section persistence.

        Args:
            storage: DataFrameStorage protocol implementation for S3 I/O.
                All S3 operations are delegated to this storage backend.
            prefix: Key prefix for S3 objects (default "dataframes/").
        """
        self._storage: DataFrameStorage = storage
        self._prefix = prefix

        # In-memory manifest cache + per-project locks to prevent
        # read-modify-write races during concurrent section updates.
        self._manifest_cache: dict[str, SectionManifest] = {}
        self._manifest_locks: dict[str, asyncio.Lock] = {}
        # Initialize polars eagerly for is_available check
        self._polars_module: Any = None
        self._initialize_polars()

    @property
    def storage(self) -> DataFrameStorage:
        """Public access to the underlying DataFrameStorage.

        Per ADR-I11-003: Exposes storage for consumers that need direct
        S3 I/O (e.g., ProgressiveTier read path).
        """
        return self._storage

    async def __aenter__(self) -> SectionPersistence:
        """Async context manager entry (no-op, storage manages its own lifecycle)."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Async context manager exit (no-op)."""

    def _initialize_polars(self) -> None:
        """Initialize polars module."""
        try:
            import polars

            self._polars_module = polars
        except ImportError:
            logger.warning("polars not available for SectionPersistence")

    def _get_manifest_lock(self, project_gid: str) -> asyncio.Lock:
        """Get or create a per-project asyncio.Lock for manifest updates.

        Safe without additional synchronization because dict access between
        check and assignment has no `await` (atomic in single event loop).
        """
        if project_gid not in self._manifest_locks:
            self._manifest_locks[project_gid] = asyncio.Lock()
        return self._manifest_locks[project_gid]

    @property
    def is_available(self) -> bool:
        """Check if persistence can potentially be available.

        Delegates to storage.is_available and checks polars availability.
        """
        return self._storage.is_available and self._polars_module is not None

    def _make_manifest_key(self, project_gid: str) -> str:
        """Generate S3 key for manifest."""
        return f"{self._prefix}{project_gid}/manifest.json"

    def _make_section_key(self, project_gid: str, section_gid: str) -> str:
        """Generate S3 key for section parquet."""
        return f"{self._prefix}{project_gid}/sections/{section_gid}.parquet"

    def _make_dataframe_key(self, project_gid: str) -> str:
        """Generate S3 key for final merged DataFrame."""
        return f"{self._prefix}{project_gid}/dataframe.parquet"

    def _make_watermark_key(self, project_gid: str) -> str:
        """Generate S3 key for watermark."""
        return f"{self._prefix}{project_gid}/watermark.json"

    def _make_index_key(self, project_gid: str) -> str:
        """Generate S3 key for GID lookup index."""
        return f"{self._prefix}{project_gid}/gid_lookup_index.json"

    # ========== Manifest Operations ==========

    async def create_manifest_async(
        self,
        project_gid: str,
        entity_type: str,
        section_gids: list[str],
        schema_version: str = "",
        section_names: dict[str, str] | None = None,
    ) -> SectionManifest:
        """Create a new manifest for a project build.

        Args:
            project_gid: Asana project GID.
            entity_type: Entity type (e.g., "offer", "contact").
            section_gids: List of section GIDs to track.
            schema_version: Schema version for cache compatibility.
            section_names: Optional ``{gid: name}`` mapping for sections.

        Returns:
            Created SectionManifest.
        """
        names = section_names or {}
        manifest = SectionManifest(
            project_gid=project_gid,
            entity_type=entity_type,
            total_sections=len(section_gids),
            sections={gid: SectionInfo(name=names.get(gid)) for gid in section_gids},
            schema_version=schema_version,
        )

        await self._save_manifest_async(manifest)
        self._manifest_cache[project_gid] = manifest

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

        Returns cached manifest if available, otherwise reads from S3
        and populates the cache.

        Args:
            project_gid: Asana project GID.

        Returns:
            SectionManifest if exists, None otherwise.
        """
        if project_gid in self._manifest_cache:
            return self._manifest_cache[project_gid]

        key = self._make_manifest_key(project_gid)

        raw_bytes = await self._storage.load_json(key)
        if raw_bytes is None:
            return None
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
            manifest = SectionManifest.model_validate(data)
            self._manifest_cache[project_gid] = manifest
            return manifest
        except Exception as e:  # BROAD-CATCH: vendor-polymorphic
            logger.error("manifest_parse_failed", project_gid=project_gid, error=str(e))
            return None

    async def _save_manifest_async(self, manifest: SectionManifest) -> bool:
        """Save manifest to S3."""
        key = self._make_manifest_key(manifest.project_gid)
        data = manifest.model_dump_json(indent=2).encode("utf-8")

        success = await self._storage.save_json(key, data)
        if not success:
            logger.error(
                "manifest_save_failed",
                project_gid=manifest.project_gid,
            )
        return success

    async def update_manifest_section_async(
        self,
        project_gid: str,
        section_gid: str,
        status: SectionStatus,
        rows: int = 0,
        error: str | None = None,
        *,
        watermark: datetime | None = None,
        gid_hash: str | None = None,
    ) -> SectionManifest | None:
        """Update a section's status in the manifest.

        Uses a per-project asyncio.Lock to serialize read-modify-write cycles,
        preventing concurrent updates from overwriting each other.

        Args:
            project_gid: Asana project GID.
            section_gid: Section GID to update.
            status: New status for the section.
            rows: Row count (for complete status).
            error: Error message (for failed status).
            watermark: Max modified_at timestamp (for complete status).
            gid_hash: SHA256 hash of sorted GIDs (for complete status).

        Returns:
            Updated manifest, or None on error.
        """
        lock = self._get_manifest_lock(project_gid)

        async with lock:
            manifest = await self.get_manifest_async(project_gid)
            if manifest is None:
                logger.warning("manifest_not_found", project_gid=project_gid)
                return None

            if status == SectionStatus.COMPLETE:
                manifest.mark_section_complete(
                    section_gid, rows, watermark=watermark, gid_hash=gid_hash
                )
            elif status == SectionStatus.FAILED:
                manifest.mark_section_failed(section_gid, error or "Unknown error")
            elif status == SectionStatus.IN_PROGRESS:
                manifest.mark_section_in_progress(section_gid)
            else:
                manifest.sections[section_gid] = SectionInfo(status=status)

            self._manifest_cache[project_gid] = manifest
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
        df: pl.DataFrame,
        *,
        watermark: datetime | None = None,
        gid_hash: str | None = None,
    ) -> bool:
        """Write a section DataFrame to S3.

        Args:
            project_gid: Asana project GID.
            section_gid: Section GID.
            df: Polars DataFrame for this section.
            watermark: Max modified_at timestamp for freshness probing.
            gid_hash: SHA256 hash of sorted task GIDs for structural change detection.

        Returns:
            True if written successfully.
        """
        if self._polars_module is None:
            logger.warning("polars not available, cannot write section")
            return False

        success = await self._storage.save_section(
            project_gid,
            section_gid,
            df,
            metadata={
                "project-gid": project_gid,
                "section-gid": section_gid,
                "row-count": str(len(df)),
            },
        )

        if success:
            logger.info(
                "section_s3_write_completed",
                extra={
                    "project_gid": project_gid,
                    "section_gid": section_gid,
                    "row_count": len(df),
                },
            )
            await self.update_manifest_section_async(
                project_gid,
                section_gid,
                SectionStatus.COMPLETE,
                rows=len(df),
                watermark=watermark,
                gid_hash=gid_hash,
            )
        else:
            logger.error(
                "section_s3_write_failed",
                extra={
                    "project_gid": project_gid,
                    "section_gid": section_gid,
                },
            )
            await self.update_manifest_section_async(
                project_gid,
                section_gid,
                SectionStatus.FAILED,
                error="storage_write_failed",
            )
        return success

    async def read_section_async(
        self,
        project_gid: str,
        section_gid: str,
    ) -> pl.DataFrame | None:
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

        return await self._storage.load_section(project_gid, section_gid)

    async def read_all_sections_async(
        self,
        project_gid: str,
    ) -> list[pl.DataFrame]:
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
    ) -> pl.DataFrame | None:
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
            logger.warning("no_sections_to_merge", project_gid=project_gid)
            return None

        try:
            # Use how="diagonal_relaxed" to handle type mismatches between sections
            # (e.g., Null vs String when one section has empty values for a column)
            merged: pl.DataFrame = self._polars_module.concat(
                section_dfs, how="diagonal_relaxed"
            )

            logger.info(
                "sections_merged",
                extra={
                    "project_gid": project_gid,
                    "sections_merged": len(section_dfs),
                    "total_rows": len(merged),
                },
            )

            return merged
        except Exception as e:  # BROAD-CATCH: vendor-polymorphic
            logger.error("sections_merge_failed", project_gid=project_gid, error=str(e))
            return None

    # ========== Final Atomic Write Operations ==========

    async def write_final_artifacts_async(
        self,
        project_gid: str,
        df: pl.DataFrame,
        watermark: datetime,
        index_data: dict[str, Any] | None = None,
        entity_type: str | None = None,
    ) -> bool:
        """Write final artifacts atomically (DataFrame + watermark + optional index).

        Called after all sections are complete and merged.

        Args:
            project_gid: Asana project GID.
            df: Final merged DataFrame.
            watermark: Watermark timestamp.
            index_data: Optional serialized GidLookupIndex data.
            entity_type: Optional entity type for schema_version resolution.

        Returns:
            True if all artifacts written successfully.
        """
        if self._polars_module is None:
            logger.warning("polars not available, cannot write final artifacts")
            return False

        # Ensure watermark is timezone-aware for save_dataframe
        if watermark.tzinfo is None:
            watermark = watermark.replace(tzinfo=UTC)

        df_ok = await self._storage.save_dataframe(
            project_gid, df, watermark, entity_type=entity_type
        )

        idx_ok = True
        if index_data is not None:
            idx_ok = await self._storage.save_index(project_gid, index_data)

        success = df_ok and idx_ok
        if success:
            logger.info(
                "final_artifacts_written",
                extra={
                    "project_gid": project_gid,
                    "row_count": len(df),
                    "watermark": watermark.isoformat(),
                    "index_written": index_data is not None,
                    "entity_type": entity_type,
                },
            )
        else:
            logger.error(
                "final_artifacts_write_failed",
                extra={
                    "project_gid": project_gid,
                    "df_success": df_ok,
                    "idx_success": idx_ok,
                },
            )
        return success

    # ========== Checkpoint Operations ==========

    async def write_checkpoint_async(
        self,
        project_gid: str,
        section_gid: str,
        df: pl.DataFrame,
        *,
        pages_fetched: int,
        rows_fetched: int,
    ) -> bool:
        """Write a mid-fetch checkpoint parquet to S3 without marking complete.

        Used during paced iteration of large sections to persist progress.
        The section remains IN_PROGRESS so that resume can continue from
        the checkpoint offset. Updates manifest with checkpoint metadata.

        Args:
            project_gid: Asana project GID.
            section_gid: Section GID being fetched.
            df: Checkpoint DataFrame with accumulated rows so far.
            pages_fetched: Number of API pages consumed so far.
            rows_fetched: Total rows accumulated so far.

        Returns:
            True if checkpoint written successfully.
        """
        if self._polars_module is None:
            logger.warning("polars not available, cannot write checkpoint")
            return False

        success = await self._storage.save_section(
            project_gid,
            section_gid,
            df,
            metadata={
                "project-gid": project_gid,
                "section-gid": section_gid,
                "row-count": str(len(df)),
                "checkpoint": "true",
                "pages-fetched": str(pages_fetched),
            },
        )

        if success:
            await self.update_checkpoint_metadata_async(
                project_gid, section_gid, pages_fetched, rows_fetched
            )
        else:
            logger.warning(
                "checkpoint_write_failed",
                extra={
                    "project_gid": project_gid,
                    "section_gid": section_gid,
                },
            )
        return success

    async def update_checkpoint_metadata_async(
        self,
        project_gid: str,
        section_gid: str,
        pages_fetched: int,
        rows_fetched: int,
    ) -> None:
        """Update manifest SectionInfo with checkpoint progress.

        Uses the per-project manifest lock to safely update checkpoint
        fields without race conditions.

        Args:
            project_gid: Asana project GID.
            section_gid: Section GID being checkpointed.
            pages_fetched: Total pages fetched so far.
            rows_fetched: Total rows accumulated so far.
        """
        lock = self._get_manifest_lock(project_gid)
        async with lock:
            manifest = await self.get_manifest_async(project_gid)
            if manifest is None:
                return

            section_info = manifest.sections.get(section_gid)
            if section_info is None:
                return

            section_info.last_fetched_offset = pages_fetched
            section_info.rows_fetched = rows_fetched
            section_info.chunks_checkpointed += 1

            self._manifest_cache[project_gid] = manifest
            await self._save_manifest_async(manifest)

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
            if not await self._storage.delete_section(project_gid, section_gid):
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
        self._manifest_cache.pop(project_gid, None)
        key = self._make_manifest_key(project_gid)
        return await self._storage.delete_object(key)


def create_section_persistence(
    *,
    storage: DataFrameStorage | None = None,
    prefix: str = "dataframes/",
) -> SectionPersistence:
    """Factory to create a SectionPersistence with default S3DataFrameStorage.

    Constructs an S3DataFrameStorage from application settings when no
    storage is explicitly provided. This replaces the old pattern of
    calling ``SectionPersistence()`` with no arguments.

    Args:
        storage: Optional DataFrameStorage instance. If None, creates
            an S3DataFrameStorage from ``get_settings().s3``.
        prefix: S3 key prefix (default "dataframes/").

    Returns:
        Configured SectionPersistence instance.
    """
    if storage is None:
        from autom8_asana.config import S3LocationConfig
        from autom8_asana.dataframes.storage import S3DataFrameStorage
        from autom8_asana.settings import get_settings

        s3_settings = get_settings().s3
        location = S3LocationConfig(
            bucket=s3_settings.bucket or "",
            region=s3_settings.region,
            endpoint_url=s3_settings.endpoint_url,
        )
        storage = S3DataFrameStorage(location=location)

    return SectionPersistence(storage=storage, prefix=prefix)
