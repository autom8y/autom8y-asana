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
import io
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.config import (
    CHECKPOINT_EVERY_N_PAGES,
    PACE_DELAY_SECONDS,
    PACE_PAGES_PER_PAUSE,
)
from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.fields import (
    BASE_OPT_FIELDS,
    coerce_rows_to_schema,
)
from autom8_asana.dataframes.section_persistence import (
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task

logger = get_logger(__name__)


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
        sections_probed: Number of sections checked for freshness.
        sections_delta_updated: Number of sections updated via delta merge.
    """

    df: pl.DataFrame
    watermark: datetime
    total_rows: int
    sections_fetched: int
    sections_resumed: int
    fetch_time_ms: float
    total_time_ms: float
    sections_probed: int = 0
    sections_delta_updated: int = 0


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
        self._section_dfs: dict[str, pl.DataFrame] = {}
        self._manifest: SectionManifest | None = None

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
        sections_probed = 0
        sections_delta_updated = 0

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

                    # Step 2b: Probe COMPLETE sections for freshness
                    if (
                        manifest.is_complete()
                        and os.environ.get("SECTION_FRESHNESS_PROBE", "1") != "0"
                    ):
                        try:
                            from autom8_asana.dataframes.builders.freshness import (
                                ProbeVerdict,
                                SectionFreshnessProber,
                            )

                            prober = SectionFreshnessProber(
                                client=self._client,
                                persistence=self._persistence,
                                project_gid=self._project_gid,
                                manifest=manifest,
                                schema=self._schema,
                                dataframe_view=self._dataframe_view,
                            )
                            probe_results = await prober.probe_all_async()
                            sections_probed = len(probe_results)

                            stale = [
                                r
                                for r in probe_results
                                if r.verdict
                                not in (ProbeVerdict.CLEAN, ProbeVerdict.PROBE_FAILED)
                            ]
                            if stale:
                                sections_delta_updated = (
                                    await prober.apply_deltas_async(
                                        stale,
                                        dataframe_view=self._dataframe_view,
                                    )
                                )

                                logger.info(
                                    "progressive_build_freshness_applied",
                                    extra={
                                        "project_gid": self._project_gid,
                                        "sections_probed": sections_probed,
                                        "sections_stale": len(stale),
                                        "sections_delta_updated": sections_delta_updated,
                                    },
                                )
                        except Exception as e:
                            logger.warning(
                                "progressive_build_freshness_probe_failed",
                                extra={
                                    "project_gid": self._project_gid,
                                    "error": str(e),
                                    "error_type": type(e).__name__,
                                },
                            )

        # Step 3: Create/update manifest
        if manifest is None:
            section_names: dict[str, str] = {
                s.gid: s.name for s in sections if isinstance(s.name, str)
            }
            manifest = await self._persistence.create_manifest_async(
                self._project_gid,
                self._entity_type,
                section_gids,
                schema_version=current_schema_version,
                section_names=section_names or None,
            )

        # Store manifest for section-level access (resume/checkpoint)
        self._manifest = manifest

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

        # Step 5: Merge all sections from S3, with in-memory fallback
        merged_df = await self._persistence.merge_sections_to_dataframe_async(
            self._project_gid
        )

        if merged_df is None and self._section_dfs:
            merged_df = pl.concat(
                list(self._section_dfs.values()), how="diagonal_relaxed"
            )
            logger.warning(
                "progressive_build_s3_fallback",
                extra={
                    "project_gid": self._project_gid,
                    "sections_in_memory": len(self._section_dfs),
                    "total_rows": len(merged_df),
                },
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
                entity_type=self._entity_type,
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
                "sections_probed": sections_probed,
                "sections_delta_updated": sections_delta_updated,
                "fetch_time_ms": round(fetch_time, 2),
                "total_time_ms": round(total_time, 2),
            },
        )

        # Release in-memory section DataFrames
        self._section_dfs.clear()

        return ProgressiveBuildResult(
            df=merged_df,
            watermark=watermark,
            total_rows=total_rows,
            sections_fetched=sections_fetched,
            sections_resumed=sections_resumed,
            fetch_time_ms=fetch_time,
            total_time_ms=total_time,
            sections_probed=sections_probed,
            sections_delta_updated=sections_delta_updated,
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

        For large sections (100+ tasks on first page), uses paced iteration
        with periodic checkpoint writes to avoid Asana cost-based 429s.
        Per TDD-large-section-resilience.

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

            # --- Resume detection (per TDD section 3.5) ---
            section_info = None
            if self._manifest is not None:
                section_info = self._manifest.sections.get(section_gid)

            checkpoint_df: pl.DataFrame | None = None
            resume_offset = 0

            if (
                section_info is not None
                and section_info.status == SectionStatus.IN_PROGRESS
                and section_info.rows_fetched > 0
            ):
                try:
                    checkpoint_df = await self._persistence.read_section_async(
                        self._project_gid, section_gid
                    )
                    if checkpoint_df is not None:
                        resume_offset = section_info.last_fetched_offset
                        logger.info(
                            "section_checkpoint_resumed",
                            extra={
                                "section_gid": section_gid,
                                "resumed_offset": resume_offset,
                                "resumed_rows": section_info.rows_fetched,
                                "checkpoint_rows": len(checkpoint_df),
                            },
                        )
                except Exception as e:
                    logger.warning(
                        "section_checkpoint_resume_failed",
                        extra={
                            "section_gid": section_gid,
                            "error": str(e),
                            "fallback": "full_refetch",
                        },
                    )
                    checkpoint_df = None
                    resume_offset = 0

            # --- Create PageIterator ---
            iterator = self._client.tasks.list_async(
                section=section_gid,
                opt_fields=BASE_OPT_FIELDS,
            )

            # --- Skip past already-fetched pages on resume ---
            if resume_offset > 0:
                skip_count = 0
                skip_task_count = 0
                async for task in iterator:
                    skip_task_count += 1
                    if skip_task_count >= 100:
                        skip_count += 1
                        skip_task_count = 0
                        if skip_count >= resume_offset:
                            break

                logger.info(
                    "section_resume_pages_skipped",
                    extra={
                        "section_gid": section_gid,
                        "pages_skipped": skip_count,
                        "target_offset": resume_offset,
                    },
                )

            # --- Fetch first page to determine section size ---
            first_page_tasks: list[Task] = []
            async for task in iterator:
                first_page_tasks.append(task)
                if len(first_page_tasks) >= 100:
                    break

            is_large_section = len(first_page_tasks) == 100

            logger.info(
                "large_section_detected",
                extra={
                    "section_gid": section_gid,
                    "first_page_count": len(first_page_tasks),
                    "pacing_enabled": is_large_section,
                },
            )

            if not first_page_tasks:
                # Empty section - mark as complete with 0 rows
                from autom8_asana.dataframes.builders.freshness import (
                    compute_gid_hash,
                )

                await self._persistence.update_manifest_section_async(
                    self._project_gid,
                    section_gid,
                    SectionStatus.COMPLETE,
                    rows=0,
                    gid_hash=compute_gid_hash([]),
                )
                return True

            if not is_large_section:
                # --- Small section: process immediately (existing path) ---
                tasks = first_page_tasks
            else:
                # --- Large section: paced iteration with checkpoints ---
                all_tasks: list[Task] = list(first_page_tasks)
                pages_fetched = 1
                current_page_task_count = 0

                async for task in iterator:
                    all_tasks.append(task)
                    current_page_task_count += 1

                    if current_page_task_count >= 100:
                        pages_fetched += 1
                        current_page_task_count = 0

                        # Pacing: pause every N pages
                        if pages_fetched % PACE_PAGES_PER_PAUSE == 0:
                            logger.info(
                                "section_pace_pause",
                                extra={
                                    "section_gid": section_gid,
                                    "pages_fetched": pages_fetched,
                                    "rows_so_far": len(all_tasks),
                                    "pause_seconds": PACE_DELAY_SECONDS,
                                },
                            )
                            await asyncio.sleep(PACE_DELAY_SECONDS)

                        # Checkpoint: persist every N pages
                        if pages_fetched % CHECKPOINT_EVERY_N_PAGES == 0:
                            await self._write_checkpoint(
                                section_gid, all_tasks, pages_fetched
                            )

                # Account for final partial page
                if current_page_task_count > 0:
                    pages_fetched += 1

                tasks = all_tasks

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

            # Convert tasks to DataFrame rows
            task_dicts = [self._task_to_dict(task) for task in tasks]
            rows = await self._extract_rows(task_dicts)

            # Coerce row values to match schema types (handles "0%" -> 0.0, etc.)
            coerced_rows = coerce_rows_to_schema(rows, self._schema)

            # Build section DataFrame with explicit schema to avoid type inference issues
            section_df = pl.DataFrame(
                coerced_rows, schema=self._schema.to_polars_schema()
            )

            # Compute freshness metadata for section probing
            from autom8_asana.dataframes.builders.freshness import compute_gid_hash

            section_gid_hash = compute_gid_hash([t.gid for t in tasks])
            section_watermark: datetime | None = None
            if "last_modified" in section_df.columns and len(section_df) > 0:
                max_val = section_df["last_modified"].max()
                if max_val is not None and isinstance(max_val, datetime):
                    section_watermark = max_val

            # Store in memory before S3 write (fallback if S3 unavailable)
            self._section_dfs[section_gid] = section_df

            # Write to S3 (this also updates manifest to COMPLETE)
            success = await self._persistence.write_section_async(
                self._project_gid,
                section_gid,
                section_df,
                watermark=section_watermark,
                gid_hash=section_gid_hash,
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

    async def _write_checkpoint(
        self,
        section_gid: str,
        tasks: list[Task],
        pages_fetched: int,
    ) -> bool:
        """Write accumulated tasks as a checkpoint parquet to S3.

        Converts accumulated tasks to a DataFrame and writes to the
        section's existing S3 key (atomic overwrite via PutObject).
        Updates manifest with checkpoint metadata.

        Per TDD-large-section-resilience section 3.2 / ADR-LSR-002.

        Args:
            section_gid: Section GID being fetched.
            tasks: All accumulated tasks so far.
            pages_fetched: Number of pages consumed so far.

        Returns:
            True if checkpoint written successfully.
        """
        try:
            task_dicts = [self._task_to_dict(task) for task in tasks]
            rows = await self._extract_rows(task_dicts)
            coerced_rows = coerce_rows_to_schema(rows, self._schema)
            checkpoint_df = pl.DataFrame(
                coerced_rows, schema=self._schema.to_polars_schema()
            )

            # Write to S3 at the section's key (atomic overwrite).
            # We call the underlying S3 write directly, NOT
            # write_section_async(), because that method marks
            # the section COMPLETE. For checkpoints we need the
            # section to remain IN_PROGRESS.
            key = self._persistence._make_section_key(self._project_gid, section_gid)
            buffer = io.BytesIO()
            checkpoint_df.write_parquet(buffer)
            buffer.seek(0)
            parquet_bytes = buffer.read()

            result = await self._persistence._s3_client.put_object_async(
                key=key,
                body=parquet_bytes,
                content_type="application/octet-stream",
                metadata={
                    "project-gid": self._project_gid,
                    "section-gid": section_gid,
                    "row-count": str(len(checkpoint_df)),
                    "checkpoint": "true",
                    "pages-fetched": str(pages_fetched),
                },
            )

            if result.success:
                await self._update_checkpoint_metadata(
                    section_gid, pages_fetched, len(checkpoint_df)
                )
                logger.info(
                    "section_checkpoint_written",
                    extra={
                        "section_gid": section_gid,
                        "pages_fetched": pages_fetched,
                        "rows_checkpointed": len(checkpoint_df),
                        "s3_key": key,
                    },
                )
                # Store in memory for fallback
                self._section_dfs[section_gid] = checkpoint_df
            else:
                logger.warning(
                    "section_checkpoint_write_failed",
                    extra={
                        "section_gid": section_gid,
                        "error": result.error,
                    },
                )

            return result.success

        except Exception as e:
            logger.warning(
                "section_checkpoint_failed",
                extra={
                    "section_gid": section_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return False

    async def _update_checkpoint_metadata(
        self,
        section_gid: str,
        pages_fetched: int,
        rows_fetched: int,
    ) -> None:
        """Update manifest SectionInfo with checkpoint progress.

        Uses the per-project manifest lock to safely update checkpoint
        fields without race conditions.

        Per TDD-large-section-resilience section 3.3.

        Args:
            section_gid: Section GID being checkpointed.
            pages_fetched: Total pages fetched so far.
            rows_fetched: Total rows accumulated so far.
        """
        lock = self._persistence._get_manifest_lock(self._project_gid)
        async with lock:
            manifest = await self._persistence.get_manifest_async(self._project_gid)
            if manifest is None:
                return

            section_info = manifest.sections.get(section_gid)
            if section_info is None:
                return

            section_info.last_fetched_offset = pages_fetched
            section_info.rows_fetched = rows_fetched
            section_info.chunks_checkpointed += 1

            self._persistence._manifest_cache[self._project_gid] = manifest
            await self._persistence._save_manifest_async(manifest)

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
            from autom8_asana.services.universal_strategy import DEFAULT_KEY_COLUMNS

            key_columns = DEFAULT_KEY_COLUMNS.get(self._entity_type, ["gid"])
            index = GidLookupIndex.from_dataframe(df, key_columns=key_columns)
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
