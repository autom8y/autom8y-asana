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
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import polars as pl

from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.parallel_fetch import ParallelSectionFetcher
from autom8_asana.dataframes.section_persistence import (
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.dataframes.views.dataframe_view import DataFrameView
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task
    from autom8_asana.services.gid_lookup import GidLookupIndex

logger = logging.getLogger(__name__)


# Base opt_fields required for DataFrame extraction
# Duplicated from project.py to avoid circular imports
_BASE_OPT_FIELDS: list[str] = [
    "gid",
    "name",
    "resource_subtype",
    "completed",
    "completed_at",
    "created_at",
    "modified_at",
    "due_on",
    "tags",
    "tags.name",
    "memberships.section.name",
    "memberships.project.gid",
    "parent",
    "parent.gid",
    "custom_fields",
    "custom_fields.gid",
    "custom_fields.name",
    "custom_fields.resource_subtype",
    "custom_fields.display_value",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.number_value",
    "custom_fields.text_value",
]


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
        client: "AsanaClient",
        project_gid: str,
        entity_type: str,
        schema: "DataFrameSchema",
        persistence: SectionPersistence,
        *,
        resolver: "CustomFieldResolver | None" = None,
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
            max_concurrent_sections: Max parallel section fetches.
        """
        self._client = client
        self._project_gid = project_gid
        self._entity_type = entity_type
        self._schema = schema
        self._persistence = persistence
        self._resolver = resolver
        self._max_concurrent = max_concurrent_sections
        self._dataframe_view: "DataFrameView | None" = None

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
                df=pl.DataFrame(),
                watermark=datetime.now(timezone.utc),
                total_rows=0,
                sections_fetched=0,
                sections_resumed=0,
                fetch_time_ms=0.0,
                total_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Step 2: Check for existing manifest (resume capability)
        manifest: SectionManifest | None = None
        sections_to_fetch: list[str] = section_gids

        if resume:
            manifest = await self._persistence.get_manifest_async(self._project_gid)
            if manifest is not None:
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
            merged_df = pl.DataFrame()

        total_rows = len(merged_df)
        watermark = datetime.now(timezone.utc)

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

        from autom8_asana.dataframes.views.dataframe_view import DataFrameView

        self._dataframe_view = DataFrameView(
            schema=self._schema,
            resolver=self._resolver,
        )

    async def _list_sections(self) -> list["Section"]:
        """List sections for the project."""
        sections: list["Section"] = await self._client.sections.list_for_project_async(
            self._project_gid
        ).collect()
        return sections

    async def _fetch_and_persist_section(
        self,
        section_gid: str,
        section: "Section | None",
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
            tasks: list["Task"] = await self._client.tasks.list_async(
                section=section_gid,
                opt_fields=_BASE_OPT_FIELDS,
            ).collect()

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

            # Build section DataFrame
            section_df = pl.DataFrame(rows)

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

    def _task_to_dict(self, task: "Task") -> dict[str, Any]:
        """Convert Task model to dict for DataFrameView extraction."""
        # Use task's model_dump if available, otherwise manual conversion
        if hasattr(task, "model_dump"):
            return task.model_dump()
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
            "parent": getattr(task, "parent", None),
            "custom_fields": getattr(task, "custom_fields", []),
        }

    async def _extract_rows(
        self,
        task_dicts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract DataFrame rows from task dicts using DataFrameView."""
        if self._dataframe_view is None:
            await self._ensure_dataframe_view()

        assert self._dataframe_view is not None

        rows = await self._dataframe_view._extract_rows_async(
            task_dicts,
            project_gid=self._project_gid,
        )
        return rows

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


async def build_project_progressive_async(
    client: "AsanaClient",
    project_gid: str,
    entity_type: str,
    schema: "DataFrameSchema",
    persistence: SectionPersistence,
    *,
    resolver: "CustomFieldResolver | None" = None,
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
    )
    return await builder.build_progressive_async(resume=resume)
