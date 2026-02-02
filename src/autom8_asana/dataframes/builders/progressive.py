"""Progressive project builder with section-level S3 persistence.

Per progressive cache warming architecture:
- Writes section DataFrames to S3 as they complete (not waiting for all)
- Uses manifest tracking for resume capability on restart
- Supports parallel project processing with bounded concurrency

This builder enables:
- Resume from partial builds after container restart
- Per-section visibility during long preload operations
- Section-targeted queries without loading full DataFrame
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.delta_merger import DeltaMerger
from autom8_asana.dataframes.builders.fields import (
    BASE_OPT_FIELDS,
    WATERMARK_COLUMN_NAME,
    coerce_rows_to_schema,
)
from autom8_asana.dataframes.builders.incremental_filter import IncrementalFilter
from autom8_asana.dataframes.section_persistence import (
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task

logger = get_logger(__name__)


@dataclass
class BuildProgress:
    """Progress information for incremental build callback.

    Per TDD-DATAFRAME-BUILDER-WATERMARK-001: Progress reporting for
    long-running build operations.

    Attributes:
        phase: Current build phase name.
        sections_total: Total sections to process.
        sections_complete: Sections completed so far.
        tasks_processed: Total tasks processed.
        tasks_skipped: Tasks skipped due to cache.
        elapsed_ms: Time elapsed since build start.
    """

    phase: str
    sections_total: int
    sections_complete: int
    tasks_processed: int
    tasks_skipped: int
    elapsed_ms: float


@dataclass
class ProgressiveBuildResult:
    """Result of progressive project build.

    Attributes:
        df: Final merged DataFrame.
        watermark: Build timestamp.
        total_rows: Total rows across all sections.
        sections_fetched: Number of sections fetched from API.
        sections_resumed: Number of sections loaded from S3 (resumed).
        fetch_time_ms: Time spent fetching from API.
        total_time_ms: Total build time including S3 writes.
    """

    df: pl.DataFrame
    watermark: datetime
    total_rows: int
    sections_fetched: int
    sections_resumed: int
    fetch_time_ms: float
    total_time_ms: float


class ProgressiveProjectBuilder:
    """Builder that writes section DataFrames progressively to S3.

    Integrates with SectionPersistence for:
    - Creating manifest at start of build
    - Writing section parquets as they complete
    - Resume capability (skip sections already in S3)
    - Final merge and artifact writes

    Example:
        >>> builder = ProgressiveProjectBuilder(
        ...     client=client,
        ...     project_gid="123",
        ...     entity_type="offer",
        ...     schema=schema,
        ...     persistence=persistence,
        ... )
        >>> result = await builder.build_progressive_async()
        >>> print(f"Built {result.total_rows} rows, resumed {result.sections_resumed}")
    """

    def __init__(
        self,
        client: AsanaClient,
        project_gid: str,
        entity_type: str,
        schema: DataFrameSchema,
        persistence: SectionPersistence,
        *,
        resolver: CustomFieldResolver | None = None,
        store: Any | None = None,
        max_concurrent_sections: int = 8,
    ) -> None:
        """Initialize progressive builder.

        Args:
            client: AsanaClient for API calls.
            project_gid: Asana project GID.
            entity_type: Entity type (e.g., "offer", "contact").
            schema: DataFrame schema for extraction.
            persistence: SectionPersistence for S3 operations.
            resolver: Optional custom field resolver.
            store: Optional UnifiedStore for cascade field resolution.
            max_concurrent_sections: Max parallel section fetches.
        """
        self._client = client
        self._project_gid = project_gid
        self._entity_type = entity_type
        self._schema = schema
        self._persistence = persistence
        self._resolver = resolver
        self._store = store
        self._max_concurrent = max_concurrent_sections
        self._dataframe_view: DataFrameViewPlugin | None = None

    async def build_progressive_async(
        self,
        resume: bool = True,
    ) -> ProgressiveBuildResult:
        """Build DataFrame with progressive section writes to S3.

        Args:
            resume: If True, check manifest and skip completed sections.

        Returns:
            ProgressiveBuildResult with merged DataFrame and metrics.
        """
        start_time = time.perf_counter()
        fetch_time = 0.0
        sections_fetched = 0
        sections_resumed = 0

        # Initialize DataFrameView for task-to-row extraction
        await self._ensure_dataframe_view()

        # Step 1: Get section list
        sections = await self._list_sections()
        section_gids = [s.gid for s in sections]

        if not sections:
            logger.warning(
                "progressive_build_no_sections",
                extra={"project_gid": self._project_gid},
            )
            return ProgressiveBuildResult(
                df=pl.DataFrame(schema=self._schema.to_polars_schema()),
                watermark=datetime.now(UTC),
                total_rows=0,
                sections_fetched=0,
                sections_resumed=0,
                fetch_time_ms=0.0,
                total_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Step 2: Check for existing manifest (resume capability)
        manifest: SectionManifest | None = None
        sections_to_fetch: list[str] = section_gids
        current_schema_version = self._schema.version

        if resume:
            manifest = await self._persistence.get_manifest_async(self._project_gid)
            if manifest is not None:
                # Check manifest age (staleness detection)
                # Per TDD-cache-freshness-remediation Fix 1: Delete stale
                # COMPLETE manifests to force a full rebuild. Incomplete
                # manifests are preserved for transient failure resume.
                try:
                    manifest_ttl_hours = int(
                        os.environ.get("MANIFEST_TTL_HOURS", "6")
                    )
                except (ValueError, TypeError):
                    manifest_ttl_hours = 6

                manifest_age_hours = (
                    datetime.now(UTC) - manifest.started_at
                ).total_seconds() / 3600

                if manifest_age_hours > manifest_ttl_hours and manifest.is_complete():
                    logger.warning(
                        "progressive_build_manifest_stale",
                        extra={
                            "project_gid": self._project_gid,
                            "manifest_age_hours": round(manifest_age_hours, 2),
                            "ttl_hours": manifest_ttl_hours,
                            "started_at": manifest.started_at.isoformat(),
                        },
                    )
                    try:
                        await self._persistence.delete_manifest_async(
                            self._project_gid
                        )
                    except Exception as e:
                        logger.error(
                            "progressive_build_manifest_delete_failed",
                            extra={
                                "project_gid": self._project_gid,
                                "error": str(e),
                            },
                        )
                        # Continue with stale manifest (graceful degradation)
                    else:
                        manifest = None  # Force fresh build

                # Check schema compatibility before resuming
                if manifest is not None and not manifest.is_schema_compatible(
                    current_schema_version
                ):
                    logger.warning(
                        "progressive_build_schema_mismatch",
                        extra={
                            "project_gid": self._project_gid,
                            "cached_version": manifest.schema_version,
                            "current_version": current_schema_version,
                        },
                    )
                    await self._persistence.delete_manifest_async(self._project_gid)
                    manifest = None  # Force fresh build
                elif manifest is not None:
                    # Resume: only fetch incomplete sections
                    sections_to_fetch = manifest.get_incomplete_section_gids()
                    sections_resumed = manifest.completed_sections

                    logger.info(
                        "progressive_build_resuming",
                        extra={
                            "project_gid": self._project_gid,
                            "total_sections": len(section_gids),
                            "completed_sections": sections_resumed,
                            "sections_to_fetch": len(sections_to_fetch),
                        },
                    )

        # Step 3: Create/update manifest
        if manifest is None:
            manifest = await self._persistence.create_manifest_async(
                self._project_gid,
                self._entity_type,
                section_gids,
                schema_version=current_schema_version,
            )

        logger.info(
            "preload_project_started",
            extra={
                "project_gid": self._project_gid,
                "entity_type": self._entity_type,
                "total_sections": len(section_gids),
                "resume_from_section": sections_resumed,
            },
        )

        # Step 4: Fetch and persist incomplete sections
        if sections_to_fetch:
            fetch_start = time.perf_counter()

            # Use as_completed for streaming results
            section_map = {s.gid: s for s in sections}
            fetch_tasks = [
                self._fetch_and_persist_section(
                    section_gid,
                    section_map.get(section_gid),
                    idx,
                    len(sections_to_fetch),
                )
                for idx, section_gid in enumerate(sections_to_fetch)
            ]

            # Process sections with bounded concurrency
            results = await gather_with_limit(
                fetch_tasks,
                max_concurrent=self._max_concurrent,
            )

            sections_fetched = sum(1 for r in results if r)
            fetch_time = (time.perf_counter() - fetch_start) * 1000

        # Step 5: Merge all sections from S3
        merged_df = await self._persistence.merge_sections_to_dataframe_async(
            self._project_gid
        )

        if merged_df is None:
            merged_df = pl.DataFrame(schema=self._schema.to_polars_schema())

        total_rows = len(merged_df)
        watermark = datetime.now(UTC)

        # Step 6: Write final artifacts
        if total_rows > 0:
            # Build GidLookupIndex from merged DataFrame
            index_data = self._build_index_data(merged_df)

            await self._persistence.write_final_artifacts_async(
                self._project_gid,
                merged_df,
                watermark,
                index_data=index_data,
            )

        total_time = (time.perf_counter() - start_time) * 1000

        logger.info(
            "progressive_build_complete",
            extra={
                "project_gid": self._project_gid,
                "entity_type": self._entity_type,
                "total_rows": total_rows,
                "sections_fetched": sections_fetched,
                "sections_resumed": sections_resumed,
                "fetch_time_ms": round(fetch_time, 2),
                "total_time_ms": round(total_time, 2),
            },
        )

        return ProgressiveBuildResult(
            df=merged_df,
            watermark=watermark,
            total_rows=total_rows,
            sections_fetched=sections_fetched,
            sections_resumed=sections_resumed,
            fetch_time_ms=fetch_time,
            total_time_ms=total_time,
        )

    async def _ensure_dataframe_view(self) -> None:
        """Initialize DataFrameView for row extraction."""
        if self._dataframe_view is not None:
            return

        from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin

        self._dataframe_view = DataFrameViewPlugin(
            schema=self._schema,
            store=self._store,
            resolver=self._resolver,
        )

    async def _list_sections(self) -> list[Section]:
        """List sections for the project."""
        sections: list[Section] = await self._client.sections.list_for_project_async(
            self._project_gid
        ).collect()
        return sections

    async def _fetch_and_persist_section(
        self,
        section_gid: str,
        section: Section | None,
        section_index: int,
        total_sections: int,
    ) -> bool:
        """Fetch tasks for a section, build DataFrame, and persist to S3.

        Args:
            section_gid: Section GID to fetch.
            section: Section object (may be None if not in map).
            section_index: Index for progress logging.
            total_sections: Total sections being fetched.

        Returns:
            True if successful, False on error.
        """
        section_start = time.perf_counter()

        try:
            # Mark section as in progress
            await self._persistence.update_manifest_section_async(
                self._project_gid,
                section_gid,
                SectionStatus.IN_PROGRESS,
            )

            # Fetch tasks for section
            tasks: list[Task] = await self._client.tasks.list_async(
                section=section_gid,
                opt_fields=BASE_OPT_FIELDS,
            ).collect()

            # Populate UnifiedStore with fetched tasks for cascade resolution
            if self._store is not None and tasks:
                await self._populate_store_with_tasks(tasks)

            fetch_time = (time.perf_counter() - section_start) * 1000

            logger.info(
                "section_fetch_completed",
                extra={
                    "project_gid": self._project_gid,
                    "section_gid": section_gid,
                    "section_index": section_index,
                    "total_sections": total_sections,
                    "task_count": len(tasks),
                    "fetch_time_ms": round(fetch_time, 2),
                },
            )

            if not tasks:
                # Empty section - mark as complete with 0 rows
                await self._persistence.update_manifest_section_async(
                    self._project_gid,
                    section_gid,
                    SectionStatus.COMPLETE,
                    rows=0,
                )
                return True

            # Convert tasks to DataFrame rows
            task_dicts = [self._task_to_dict(task) for task in tasks]
            rows = await self._extract_rows(task_dicts)

            # Coerce row values to match schema types (handles "0%" → 0.0, etc.)
            coerced_rows = coerce_rows_to_schema(rows, self._schema)

            # Build section DataFrame with explicit schema to avoid type inference issues
            # Per TDD: polars schema must match extraction schema for date/datetime types
            section_df = pl.DataFrame(
                coerced_rows, schema=self._schema.to_polars_schema()
            )

            # Write to S3 (this also updates manifest to COMPLETE)
            success = await self._persistence.write_section_async(
                self._project_gid,
                section_gid,
                section_df,
            )

            return success

        except Exception as e:
            logger.error(
                "section_fetch_failed",
                extra={
                    "project_gid": self._project_gid,
                    "section_gid": section_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            # Mark as failed in manifest
            await self._persistence.update_manifest_section_async(
                self._project_gid,
                section_gid,
                SectionStatus.FAILED,
                error=str(e),
            )

            return False

    def _task_to_dict(self, task: Task) -> dict[str, Any]:
        """Convert Task model to dict for DataFrameView extraction."""
        # Use task's model_dump if available, otherwise manual conversion
        if hasattr(task, "model_dump"):
            return task.model_dump()

        # Manual fallback - must convert nested models to dicts
        parent = getattr(task, "parent", None)
        if parent is not None and hasattr(parent, "model_dump"):
            parent = parent.model_dump()
        elif parent is not None and hasattr(parent, "gid"):
            # Convert parent model to dict with gid for hierarchy registration
            parent = {"gid": parent.gid}

        return {
            "gid": task.gid,
            "name": task.name,
            "resource_subtype": getattr(task, "resource_subtype", None),
            "completed": getattr(task, "completed", None),
            "completed_at": getattr(task, "completed_at", None),
            "created_at": getattr(task, "created_at", None),
            "modified_at": getattr(task, "modified_at", None),
            "due_on": getattr(task, "due_on", None),
            "tags": getattr(task, "tags", []),
            "memberships": getattr(task, "memberships", []),
            "parent": parent,
            "custom_fields": getattr(task, "custom_fields", []),
        }

    async def _extract_rows(
        self,
        task_dicts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract DataFrame rows from task dicts using DataFrameViewPlugin."""
        if self._dataframe_view is None:
            await self._ensure_dataframe_view()

        assert self._dataframe_view is not None

        rows = await self._dataframe_view._extract_rows_async(
            task_dicts,
            project_gid=self._project_gid,
        )
        return rows

    async def _populate_store_with_tasks(self, tasks: list[Task]) -> None:
        """Populate UnifiedStore with fetched tasks for cascade resolution.

        Per ADR-cascade-field-resolution: Uses put_batch_async with warm_hierarchy=True
        to recursively fetch and cache parent tasks. This ensures fields like
        office_phone and vertical that cascade from Business are properly resolved.

        The hierarchy warming:
        - Fetches immediate parents not already in cache
        - Recursively warms ancestors up to max_depth=5
        - Includes custom_fields for cascade field extraction
        """
        if not tasks or self._store is None:
            return

        try:
            # Convert Task models to dicts for batch storage
            task_dicts = [self._task_to_dict(task) for task in tasks]

            logger.info(
                "store_populate_batch_starting",
                extra={
                    "task_count": len(task_dicts),
                    "entity_type": self._entity_type,
                    "project_gid": self._project_gid,
                    "warm_hierarchy": True,
                },
            )

            # Use put_batch_async with hierarchy warming - same pattern as project.py
            # This recursively fetches and caches parent chains for cascade resolution
            await self._store.put_batch_async(
                task_dicts,
                opt_fields=BASE_OPT_FIELDS,
                tasks_client=self._client.tasks,
                warm_hierarchy=True,
            )

        except Exception as e:
            # Don't fail build if store population fails
            logger.warning(
                "store_populate_batch_failed",
                extra={
                    "task_count": len(tasks),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "entity_type": self._entity_type,
                },
            )

    def _build_index_data(self, df: pl.DataFrame) -> dict[str, Any] | None:
        """Build GidLookupIndex serialized data from DataFrame."""
        try:
            from autom8_asana.services.gid_lookup import GidLookupIndex

            index = GidLookupIndex.from_dataframe(df)
            return index.serialize()
        except Exception as e:
            logger.warning(
                "progressive_build_index_failed",
                extra={
                    "project_gid": self._project_gid,
                    "error": str(e),
                },
            )
            return None

    # =========================================================================
    # Incremental Build with Watermark Filtering (TDD-DATAFRAME-BUILDER-WATERMARK-001)
    # =========================================================================

    async def build_with_parallel_fetch_async(
        self,
        project_gid: str,
        schema: DataFrameSchema,
        *,
        resume: bool = True,
        incremental: bool = True,
        max_concurrent_sections: int = 5,
        on_progress: Callable[[BuildProgress], None] | None = None,
    ) -> pl.DataFrame:
        """Build DataFrame with parallel section fetch and incremental filtering.

        Per TDD-DATAFRAME-BUILDER-WATERMARK-001: Implements watermark-based
        incremental processing with parallel section fetch.

        Flow:
        1. Load existing DataFrame from S3 (if exists and resume=True)
        2. Build IncrementalFilter from existing DataFrame watermarks
        3. Fetch sections in parallel with bounded concurrency
        4. For each section: filter tasks against watermarks
        5. Extract rows only for changed/new tasks
        6. Use DeltaMerger to combine results
        7. Persist merged DataFrame to S3
        8. Return merged DataFrame

        Args:
            project_gid: Asana project GID.
            schema: DataFrame schema for extraction.
            resume: If True, load existing DataFrame from S3 and merge.
            incremental: If True, use watermark filtering to skip unchanged tasks.
            max_concurrent_sections: Max concurrent section fetches (default 5).
            on_progress: Optional callback for progress reporting.

        Returns:
            Merged Polars DataFrame with all tasks.

        Example:
            >>> builder = ProgressiveProjectBuilder(
            ...     client=client,
            ...     project_gid=project_gid,
            ...     entity_type="offer",
            ...     schema=schema,
            ...     persistence=persistence,
            ... )
            >>> df = await builder.build_with_parallel_fetch_async(
            ...     project_gid=project_gid,
            ...     schema=schema,
            ...     incremental=True,
            ... )
        """
        start_time = time.perf_counter()

        # Initialize DataFrameView for row extraction
        await self._ensure_dataframe_view()

        # Step 1: Load existing DataFrame from S3 (if resume enabled)
        existing_df: pl.DataFrame | None = None
        if resume:
            existing_df = await self._load_existing_dataframe_async(project_gid)
            if existing_df is not None:
                logger.info(
                    "incremental_build_existing_loaded",
                    extra={
                        "project_gid": project_gid,
                        "existing_rows": len(existing_df),
                        "has_watermark_column": WATERMARK_COLUMN_NAME
                        in existing_df.columns,
                    },
                )

        # Step 2: Build incremental filter from existing DataFrame
        incremental_filter: IncrementalFilter | None = None
        if incremental and existing_df is not None:
            incremental_filter = IncrementalFilter.from_dataframe(existing_df)
            logger.info(
                "incremental_filter_built",
                extra={
                    "project_gid": project_gid,
                    "cache_size": incremental_filter.cache_size,
                },
            )

        # Step 3: Fetch sections for project
        sections = await self._list_sections()
        if not sections:
            logger.warning(
                "incremental_build_no_sections",
                extra={"project_gid": project_gid},
            )
            return self._build_empty_dataframe(schema)

        total_sections = len(sections)

        # Report initial progress
        if on_progress:
            on_progress(
                BuildProgress(
                    phase="fetching_sections",
                    sections_total=total_sections,
                    sections_complete=0,
                    tasks_processed=0,
                    tasks_skipped=0,
                    elapsed_ms=(time.perf_counter() - start_time) * 1000,
                )
            )

        # Step 4: Fetch and filter tasks from all sections in parallel
        semaphore = asyncio.Semaphore(max_concurrent_sections)
        all_new_rows: list[dict[str, Any]] = []
        all_skipped_gids: list[str] = []
        all_fetched_gids: set[str] = set()
        sections_complete = 0

        async def process_section(
            section: Section,
        ) -> tuple[list[dict[str, Any]], list[str], set[str]]:
            """Process a single section: fetch, filter, extract."""
            async with semaphore:
                # Fetch tasks for section
                tasks: list[Task] = await self._client.tasks.list_async(
                    section=section.gid,
                    opt_fields=BASE_OPT_FIELDS,
                ).collect()

                # Convert to dicts for filtering
                task_dicts = [self._task_to_dict(task) for task in tasks]
                fetched_gids = {t.get("gid") for t in task_dicts if t.get("gid")}

                # Apply incremental filter
                if incremental_filter is not None:
                    filter_result = incremental_filter.filter(task_dicts)
                    to_process = filter_result.to_process
                    skipped = filter_result.to_skip
                else:
                    # No filter - process all
                    to_process = task_dicts
                    skipped = []

                # Extract rows for tasks to process
                rows: list[dict[str, Any]] = []
                if to_process:
                    # Populate store for cascade resolution
                    if self._store is not None:
                        await self._store.put_batch_async(
                            to_process,
                            opt_fields=BASE_OPT_FIELDS,
                            tasks_client=self._client.tasks,
                            warm_hierarchy=True,
                        )

                    # Extract rows
                    rows = await self._extract_rows(to_process)

                    # Add _modified_at column to each row
                    for i, task_dict in enumerate(to_process):
                        if i < len(rows):
                            modified_at = task_dict.get("modified_at")
                            if modified_at:
                                rows[i][WATERMARK_COLUMN_NAME] = self._parse_datetime(
                                    modified_at
                                )

                logger.debug(
                    "section_processed",
                    extra={
                        "section_gid": section.gid,
                        "fetched": len(task_dicts),
                        "processed": len(to_process),
                        "skipped": len(skipped),
                    },
                )

                return rows, skipped, fetched_gids  # type: ignore[return-value]

        # Process all sections in parallel
        results = await asyncio.gather(
            *[process_section(section) for section in sections],
            return_exceptions=True,
        )

        # Aggregate results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "section_processing_failed",
                    extra={
                        "section_gid": sections[i].gid,
                        "error": str(result),
                        "error_type": type(result).__name__,
                    },
                )
                continue

            rows, skipped, fetched_gids = result  # type: ignore[misc]
            all_new_rows.extend(rows)
            all_skipped_gids.extend(skipped)
            all_fetched_gids.update(fetched_gids)
            sections_complete += 1

            # Report progress
            if on_progress:
                on_progress(
                    BuildProgress(
                        phase="processing_sections",
                        sections_total=total_sections,
                        sections_complete=sections_complete,
                        tasks_processed=len(all_new_rows),
                        tasks_skipped=len(all_skipped_gids),
                        elapsed_ms=(time.perf_counter() - start_time) * 1000,
                    )
                )

        # Step 5: Compute deleted GIDs (in cache but not in any fetch)
        deleted_gids: list[str] = []
        if incremental_filter is not None:
            cached_gids = incremental_filter.cached_gids
            deleted_gids = list(cached_gids - all_fetched_gids)

        logger.info(
            "incremental_aggregation_complete",
            extra={
                "project_gid": project_gid,
                "new_rows": len(all_new_rows),
                "skipped_gids": len(all_skipped_gids),
                "deleted_gids": len(deleted_gids),
                "fetched_gids": len(all_fetched_gids),
            },
        )

        # Step 6: Merge using DeltaMerger
        if existing_df is not None and incremental:
            merger = DeltaMerger()
            merged_df = merger.merge(
                existing_df=existing_df,
                new_rows=all_new_rows,
                skipped_gids=all_skipped_gids,
                deleted_gids=deleted_gids,
                schema=schema,
            )
        else:
            # No existing DataFrame - build from scratch
            if all_new_rows:
                coerced_rows = coerce_rows_to_schema(all_new_rows, schema)
                merged_df = pl.DataFrame(coerced_rows, schema=schema.to_polars_schema())
            else:
                merged_df = self._build_empty_dataframe(schema)

        # Step 7: Persist merged DataFrame to S3
        if len(merged_df) > 0:
            watermark = datetime.now(UTC)
            index_data = self._build_index_data(merged_df)
            await self._persistence.write_final_artifacts_async(
                project_gid=project_gid,
                df=merged_df,
                watermark=watermark,
                index_data=index_data,
            )

        total_time = (time.perf_counter() - start_time) * 1000

        # Final progress report
        if on_progress:
            on_progress(
                BuildProgress(
                    phase="complete",
                    sections_total=total_sections,
                    sections_complete=sections_complete,
                    tasks_processed=len(all_new_rows),
                    tasks_skipped=len(all_skipped_gids),
                    elapsed_ms=total_time,
                )
            )

        logger.info(
            "incremental_build_complete",
            extra={
                "project_gid": project_gid,
                "total_rows": len(merged_df),
                "new_rows": len(all_new_rows),
                "skipped": len(all_skipped_gids),
                "deleted": len(deleted_gids),
                "sections": total_sections,
                "total_time_ms": round(total_time, 2),
            },
        )

        return merged_df

    async def _load_existing_dataframe_async(
        self,
        project_gid: str,
    ) -> pl.DataFrame | None:
        """Load existing DataFrame from S3.

        Args:
            project_gid: Asana project GID.

        Returns:
            Existing DataFrame if found, None otherwise.
        """
        try:
            # Try to load merged DataFrame first
            merged_df = await self._persistence.merge_sections_to_dataframe_async(
                project_gid
            )
            return merged_df
        except Exception as e:
            logger.warning(
                "load_existing_dataframe_failed",
                extra={
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None

    def _build_empty_dataframe(self, schema: DataFrameSchema) -> pl.DataFrame:
        """Build empty DataFrame with schema columns.

        Args:
            schema: DataFrame schema.

        Returns:
            Empty Polars DataFrame with correct schema.
        """
        return pl.DataFrame(schema=schema.to_polars_schema())

    def _parse_datetime(self, value: str | datetime | None) -> datetime | None:
        """Parse datetime value to timezone-aware datetime.

        Args:
            value: Raw datetime value (string or datetime).

        Returns:
            Timezone-aware datetime in UTC, or None if unparseable.
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value

        if not isinstance(value, str):
            return None

        # Handle Z suffix
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            return None


async def build_project_progressive_async(
    client: AsanaClient,
    project_gid: str,
    entity_type: str,
    schema: DataFrameSchema,
    persistence: SectionPersistence,
    *,
    resolver: CustomFieldResolver | None = None,
    store: Any | None = None,
    resume: bool = True,
) -> ProgressiveBuildResult:
    """Convenience function for progressive project build.

    Args:
        client: AsanaClient for API calls.
        project_gid: Asana project GID.
        entity_type: Entity type (e.g., "offer").
        schema: DataFrame schema.
        persistence: SectionPersistence for S3 operations.
        resolver: Optional custom field resolver.
        store: Optional UnifiedStore for cascade field resolution.
        resume: If True, resume from existing manifest.

    Returns:
        ProgressiveBuildResult with DataFrame and metrics.
    """
    builder = ProgressiveProjectBuilder(
        client=client,
        project_gid=project_gid,
        entity_type=entity_type,
        schema=schema,
        persistence=persistence,
        resolver=resolver,
        store=store,
    )
    return await builder.build_progressive_async(resume=resume)
