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
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger
from autom8y_telemetry import trace_computation

from autom8_asana.core.errors import S3_TRANSPORT_ERRORS
from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.build_result import (
    BuildResult,
    BuildStatus,
    SectionOutcome,
    SectionResult,
)
from autom8_asana.dataframes.builders.fields import (
    BASE_OPT_FIELDS,
    safe_dataframe_construct,
)
from autom8_asana.dataframes.builders.hierarchy_warmer import HierarchyWarmer
from autom8_asana.dataframes.section_persistence import (
    SectionManifest,
    SectionPersistence,
    SectionStatus,
)
from autom8_asana.models.business.activity import get_classifier
from autom8_asana.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin
    from autom8_asana.models.section import Section
    from autom8_asana.models.task import Task

logger = get_logger(__name__)

# Asana API maximum items per page. Used as page-boundary sentinel
# for pacing and checkpoint logic.
ASANA_PAGE_SIZE: int = 100


@dataclass
class _ResumeResult:
    """Internal result from resume check."""

    manifest: SectionManifest | None
    sections_to_fetch: list[str]
    sections_resumed: int
    sections_probed: int
    sections_delta_updated: int


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
        index_builder: Callable[[pl.DataFrame, str], dict[str, Any] | None]
        | None = None,
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
            index_builder: Optional callback ``(df, entity_type) -> dict | None``
                that builds a serialized GidLookupIndex. When *None*, index
                building is skipped.
        """
        self._client = client
        self._project_gid = project_gid
        self._entity_type = entity_type
        self._schema = schema
        self._persistence = persistence
        self._resolver = resolver
        self._store = store
        self._max_concurrent = max_concurrent_sections
        self._index_builder = index_builder
        self._dataframe_view: DataFrameViewPlugin | None = None
        self._section_dfs: dict[str, pl.DataFrame] = {}
        self._manifest: SectionManifest | None = None
        # Delta checkpoint state -- reset per section (R5)
        self._checkpoint_df: pl.DataFrame | None = None
        self._checkpoint_task_count: int = 0
        # Hierarchy warming delegate (None when store is None)
        self._hierarchy_warmer: HierarchyWarmer | None = (
            HierarchyWarmer(
                store=store,
                client=client,
                project_gid=project_gid,
                entity_type=entity_type,
                max_concurrent=max_concurrent_sections,
                task_to_dict=self._task_to_dict,
            )
            if store is not None
            else None
        )

    def _check_cascade_provider_data(self) -> None:
        """L3 pre-build assertion: verify cascade provider data is available.

        For entities that consume cascade fields, checks that the store
        contains data from the provider entity types. If the store does
        not support this probe, logs a warning and returns (does not block).

        This is L3 of the three-layer defense-in-depth for the cascade
        warm-up ordering invariant (SCAR-005/006).
        """
        from autom8_asana.dataframes.cascade_utils import get_cascade_providers

        providers = get_cascade_providers(self._entity_type)
        if not providers:
            return  # Not a cascade consumer — nothing to check

        if self._store is None:
            logger.warning(
                "cascade_l3_check_skipped_no_store",
                extra={
                    "entity_type": self._entity_type,
                    "project_gid": self._project_gid,
                    "providers": sorted(providers),
                    "reason": "no store available for cascade probe",
                },
            )
            return

        # Probe the store's hierarchy index for registered tasks.
        # If the hierarchy is empty, cascade providers haven't populated
        # the store yet — which means ordering was violated.
        try:
            hierarchy = self._store.get_hierarchy_index()
            if hierarchy is not None:
                hierarchy_len = len(hierarchy)
                if hierarchy_len == 0:
                    logger.warning(
                        "cascade_l3_check_empty_hierarchy",
                        extra={
                            "entity_type": self._entity_type,
                            "project_gid": self._project_gid,
                            "providers": sorted(providers),
                            "reason": (
                                "hierarchy index is empty — cascade providers "
                                "may not have warmed yet"
                            ),
                        },
                    )
                else:
                    logger.debug(
                        "cascade_l3_check_passed",
                        extra={
                            "entity_type": self._entity_type,
                            "project_gid": self._project_gid,
                            "providers": sorted(providers),
                            "hierarchy_size": hierarchy_len,
                        },
                    )
        except Exception as e:
            # Probe failed — log but don't block the build.
            # L1 and L2 are the hard guards; L3 is advisory.
            logger.warning(
                "cascade_l3_check_probe_failed",
                extra={
                    "entity_type": self._entity_type,
                    "project_gid": self._project_gid,
                    "providers": sorted(providers),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    async def _check_resume_and_probe(
        self,
        section_gids: list[str],
        resume: bool,
    ) -> _ResumeResult:
        """Check for existing manifest and probe freshness.

        Handles:
        - Manifest retrieval and schema compatibility check
        - Resume detection (skip completed sections)
        - Freshness probing and delta application for complete manifests

        Args:
            section_gids: All section GIDs in the project.
            resume: Whether to attempt resume from existing manifest.

        Returns:
            _ResumeResult with manifest, sections to fetch, and metrics.
        """
        sections_to_fetch = section_gids
        sections_resumed = 0
        sections_probed = 0
        sections_delta_updated = 0
        manifest: SectionManifest | None = None
        current_schema_version = self._schema.version

        if not resume:
            return _ResumeResult(
                manifest=manifest,
                sections_to_fetch=sections_to_fetch,
                sections_resumed=sections_resumed,
                sections_probed=sections_probed,
                sections_delta_updated=sections_delta_updated,
            )

        manifest = await self._persistence.get_manifest_async(self._project_gid)
        if manifest is None:
            return _ResumeResult(
                manifest=manifest,
                sections_to_fetch=sections_to_fetch,
                sections_resumed=sections_resumed,
                sections_probed=sections_probed,
                sections_delta_updated=sections_delta_updated,
            )

        # Check schema compatibility before resuming
        if not manifest.is_schema_compatible(current_schema_version):
            logger.warning(
                "progressive_build_schema_mismatch",
                extra={
                    "project_gid": self._project_gid,
                    "cached_version": manifest.schema_version,
                    "current_version": current_schema_version,
                },
            )
            await self._persistence.delete_manifest_async(self._project_gid)
            return _ResumeResult(
                manifest=None,
                sections_to_fetch=sections_to_fetch,
                sections_resumed=sections_resumed,
                sections_probed=sections_probed,
                sections_delta_updated=sections_delta_updated,
            )

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

        # Probe COMPLETE sections for freshness
        probed, delta_updated = await self._probe_freshness(manifest)
        sections_probed = probed
        sections_delta_updated = delta_updated

        return _ResumeResult(
            manifest=manifest,
            sections_to_fetch=sections_to_fetch,
            sections_resumed=sections_resumed,
            sections_probed=sections_probed,
            sections_delta_updated=sections_delta_updated,
        )

    async def _probe_freshness(
        self,
        manifest: SectionManifest,
    ) -> tuple[int, int]:
        """Probe completed sections for freshness and apply deltas.

        Only runs when manifest is fully complete and probe is enabled.

        Args:
            manifest: Complete manifest to probe.

        Returns:
            Tuple of (sections_probed, sections_delta_updated).
        """
        if not manifest.is_complete():
            return 0, 0

        from autom8_asana.settings import get_settings

        if get_settings().runtime.section_freshness_probe == "0":
            return 0, 0

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
            sections_delta_updated = 0

            stale = [
                r
                for r in probe_results
                if r.verdict not in (ProbeVerdict.CLEAN, ProbeVerdict.PROBE_FAILED)
            ]
            if stale:
                sections_delta_updated = await prober.apply_deltas_async(
                    stale,
                    dataframe_view=self._dataframe_view,
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

            return sections_probed, sections_delta_updated

        except Exception as e:  # BROAD-CATCH: degrade
            logger.warning(
                "progressive_build_freshness_probe_failed",
                extra={
                    "project_gid": self._project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return 0, 0

    async def _ensure_manifest(
        self,
        manifest: SectionManifest | None,
        sections: list[Section],
        section_gids: list[str],
    ) -> SectionManifest:
        """Create manifest if none exists, or return existing.

        Args:
            manifest: Existing manifest from resume check, or None.
            sections: Section objects for name extraction.
            section_gids: All section GIDs.

        Returns:
            SectionManifest (created or existing).
        """
        if manifest is None:
            section_names: dict[str, str] = {
                s.gid: s.name for s in sections if isinstance(s.name, str)
            }
            manifest = await self._persistence.create_manifest_async(
                self._project_gid,
                self._entity_type,
                section_gids,
                schema_version=self._schema.version,
                section_names=section_names or None,
            )

        self._manifest = manifest
        return manifest

    async def _merge_section_dataframes(self) -> pl.DataFrame:
        """Merge all sections from S3, with in-memory fallback.

        Returns:
            Merged DataFrame (may be empty if no sections produced data).
        """
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

        return merged_df

    @trace_computation("progressive.build", engine="autom8y-asana")
    async def build_progressive_async(
        self,
        resume: bool = True,
    ) -> BuildResult:
        """Build DataFrame with progressive section writes to S3.

        Per TDD-PARTIAL-FAILURE-SIGNALING-001: Returns BuildResult with
        per-section outcomes and aggregate status classification.

        Args:
            resume: If True, check manifest and skip completed sections.

        Returns:
            BuildResult with classified status and per-section detail.
        """
        start_time = time.perf_counter()

        # L3 (WS-4a): Pre-build assertion — verify cascade provider data
        # is available in the store before building a consumer entity.
        # This is the innermost layer of defense-in-depth for the
        # cascade warm-up ordering invariant (SCAR-005/006).
        self._check_cascade_provider_data()

        await self._ensure_dataframe_view()

        # Step 1: Get section list
        sections = await self._list_sections()
        section_gids = [s.gid for s in sections]

        # Step 1.5: Warn about section names the classifier cannot map (N4)
        self._warn_unclassified_sections(sections)

        if not sections:
            logger.warning(
                "progressive_build_no_sections",
                extra={"project_gid": self._project_gid},
            )
            return BuildResult(
                status=BuildStatus.SUCCESS,
                sections=(),
                dataframe=pl.DataFrame(schema=self._schema.to_polars_schema()),
                watermark=datetime.now(UTC),
                project_gid=self._project_gid,
                entity_type=self._entity_type,
                total_time_ms=(time.perf_counter() - start_time) * 1000,
                fetch_time_ms=0.0,
            )

        # Step 2: Check resume and probe freshness
        resume_result = await self._check_resume_and_probe(section_gids, resume)

        # Step 3: Ensure manifest exists
        await self._ensure_manifest(
            resume_result.manifest,
            sections,
            section_gids,
        )

        logger.info(
            "preload_project_started",
            extra={
                "project_gid": self._project_gid,
                "entity_type": self._entity_type,
                "total_sections": len(section_gids),
                "resume_from_section": resume_result.sections_resumed,
            },
        )

        # Collect SectionResults for resumed sections
        section_results: list[SectionResult] = []
        for gid in section_gids:
            if gid not in resume_result.sections_to_fetch:
                section_results.append(
                    SectionResult(
                        section_gid=gid,
                        outcome=SectionOutcome.SKIPPED,
                        resumed=True,
                    )
                )

        # Step 4: Fetch and persist incomplete sections
        fetch_time = 0.0
        if resume_result.sections_to_fetch:
            fetch_start = time.perf_counter()

            section_map = {s.gid: s for s in sections}
            fetch_tasks = [
                self._fetch_and_persist_section_with_result(
                    section_gid,
                    section_map.get(section_gid),
                    idx,
                    len(resume_result.sections_to_fetch),
                )
                for idx, section_gid in enumerate(resume_result.sections_to_fetch)
            ]

            # Process sections with bounded concurrency
            fetch_results = await gather_with_limit(
                fetch_tasks,
                max_concurrent=self._max_concurrent,
            )
            section_results.extend(fetch_results)
            fetch_time = (time.perf_counter() - fetch_start) * 1000

        # Step 5: Merge sections
        merged_df = await self._merge_section_dataframes()
        total_rows = len(merged_df)
        watermark = datetime.now(UTC)

        # Step 5.25: Reconstruct hierarchy from resumed sections
        # Per TDD-CASCADE-RESUME-FIX: Resumed sections loaded from parquet
        # don't register in HierarchyIndex. Reconstruct from parent_gid column
        # so Step 5.5 cascade validation can resolve parent chains.
        if total_rows > 0 and self._hierarchy_warmer is not None:
            reconstructed = self._hierarchy_warmer.reconstruct_hierarchy_from_dataframe(
                merged_df
            )
            if reconstructed > 0:
                # Step 5.3: Warm hierarchy gaps (e.g. unit_holder → business links)
                warmed = await self._hierarchy_warmer.warm_hierarchy_gaps_async(
                    merged_df
                )
                logger.info(
                    "hierarchy_gaps_warmed",
                    extra={
                        "project_gid": self._project_gid,
                        "entity_type": self._entity_type,
                        "reconstructed": reconstructed,
                        "gaps_warmed": warmed,
                    },
                )

        # Steps 5.5 and 5.6: Post-build cascade validation and audit
        # Per TDD-CASCADE-FAILURE-FIXES-001 Fix 3 and ADR-cascade-contract-policy.
        if total_rows > 0 and self._store is not None:
            from autom8_asana.dataframes.builders.post_build_validation import (
                post_build_validate_and_audit,
            )

            merged_df, total_rows = await post_build_validate_and_audit(
                merged_df=merged_df,
                store=self._store,
                dataframe_view=self._dataframe_view,
                schema=self._schema,
                entity_type=self._entity_type,
                project_gid=self._project_gid,
            )

        # Step 6: Write final artifacts
        if total_rows > 0:
            index_data = self._build_index_data(merged_df)

            await self._persistence.write_final_artifacts_async(
                self._project_gid,
                merged_df,
                watermark,
                index_data=index_data,
                entity_type=self._entity_type,
            )

        total_time = (time.perf_counter() - start_time) * 1000

        # Classify and log build result
        build_result = BuildResult.from_section_results(
            section_results=section_results,
            dataframe=merged_df,
            watermark=watermark,
            project_gid=self._project_gid,
            entity_type=self._entity_type,
            total_time_ms=total_time,
            fetch_time_ms=fetch_time,
            sections_probed=resume_result.sections_probed,
            sections_delta_updated=resume_result.sections_delta_updated,
        )

        logger.info(
            "build_result_classified",
            extra={
                "project_gid": self._project_gid,
                "entity_type": self._entity_type,
                "status": build_result.status.value,
                "sections_succeeded": build_result.sections_succeeded,
                "sections_failed": build_result.sections_failed,
                "total_rows": build_result.total_rows,
                "fetched_rows": build_result.fetched_rows,
                "sections_probed": resume_result.sections_probed,
                "sections_delta_updated": resume_result.sections_delta_updated,
                "fetch_time_ms": round(fetch_time, 2),
                "total_time_ms": round(total_time, 2),
            },
        )

        if build_result.status == BuildStatus.PARTIAL:
            logger.warning(
                "build_partial_failure",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "failed_section_gids": build_result.failed_section_gids,
                    "error_summary": build_result.error_summary,
                },
            )
        elif build_result.status == BuildStatus.FAILURE:
            logger.error(
                "build_total_failure",
                extra={
                    "project_gid": self._project_gid,
                    "entity_type": self._entity_type,
                    "error_summary": build_result.error_summary,
                },
            )

        # Release in-memory section DataFrames
        self._section_dfs.clear()

        from opentelemetry import trace as _otel_trace

        _span = _otel_trace.get_current_span()
        _span.set_attribute("computation.duration_ms", build_result.total_time_ms)
        _span.set_attribute(
            "computation.materialize.sections_built", build_result.sections_succeeded
        )
        _span.set_attribute(
            "computation.materialize.total_rows", build_result.total_rows
        )

        return build_result

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

    def _warn_unclassified_sections(self, sections: list[Section]) -> None:
        """Log warnings for section names not recognized by the entity classifier.

        Iterates over sections and checks each name against the classifier
        registered for ``self._entity_type``.  If no classifier is registered
        (e.g. for entity types without an activity model), the method returns
        immediately without warnings.

        This is purely observational -- it never modifies state or raises.

        Args:
            sections: Section objects returned from the Asana API.
        """
        classifier = get_classifier(self._entity_type)
        if classifier is None:
            return

        for section in sections:
            if section.name is None:
                continue
            if classifier.classify(section.name) is None:
                logger.warning(
                    "unclassified_section_name",
                    extra={
                        "project_gid": self._project_gid,
                        "entity_type": self._entity_type,
                        "section_gid": section.gid,
                        "section_name": section.name,
                        "unclassified_section": section.name,
                    },
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

        Orchestrates 5 phases: checkpoint loading, first-page fetch,
        large-section paced iteration, DataFrame construction, and
        S3 persistence. For large sections (100+ tasks on first page),
        uses paced iteration with periodic checkpoints.

        Args:
            section_gid: Section GID to fetch.
            section: Section object (may be None if not in map).
            section_index: Index for progress logging.
            total_sections: Total sections being fetched.

        Returns:
            True if successful, False on error.
        """
        section_start = time.perf_counter()

        # Reset delta checkpoint state per section (R5: prevent cross-section leakage)
        self._checkpoint_df = None
        self._checkpoint_task_count = 0

        try:
            await self._persistence.update_manifest_section_async(
                self._project_gid,
                section_gid,
                SectionStatus.IN_PROGRESS,
            )

            # Phase 1: Resume detection
            resume_offset = await self._load_checkpoint(section_gid)

            # Phase 2: Create iterator and fetch first page
            iterator = self._client.tasks.list_async(
                section=section_gid,
                opt_fields=BASE_OPT_FIELDS,
            )
            first_page_tasks, resume_offset = await self._fetch_first_page(
                section_gid, iterator, resume_offset
            )

            if not first_page_tasks:
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

            # Phase 3: Collect all tasks (paced for large sections)
            if len(first_page_tasks) < ASANA_PAGE_SIZE:
                tasks = first_page_tasks
            else:
                tasks = await self._fetch_large_section(
                    section_gid, iterator, first_page_tasks
                )

            if self._hierarchy_warmer is not None and tasks:
                await self._hierarchy_warmer.populate_store_with_tasks(tasks)

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

            # Phase 4: Build DataFrame
            section_df, gid_hash, watermark = await self._build_section_dataframe(tasks)

            # Phase 5: Persist to S3
            return await self._persist_section(
                section_gid, section_df, gid_hash, watermark
            )

        except Exception as e:  # BROAD-CATCH: isolation
            logger.error(
                "section_fetch_failed",
                extra={
                    "project_gid": self._project_gid,
                    "section_gid": section_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            await self._persistence.update_manifest_section_async(
                self._project_gid,
                section_gid,
                SectionStatus.FAILED,
                error=str(e),
            )

            return False

    async def _fetch_and_persist_section_with_result(
        self,
        section_gid: str,
        section: Section | None,
        section_index: int,
        total_sections: int,
    ) -> SectionResult:
        """Fetch, build, and persist a section, returning a SectionResult.

        Per ADR-C2-003: Wrapper around _fetch_and_persist_section that
        captures the outcome as a structured SectionResult instead of
        a boolean. The underlying method is unchanged.

        Args:
            section_gid: Section GID to fetch.
            section: Section object (may be None).
            section_index: Index for progress logging.
            total_sections: Total sections being fetched.

        Returns:
            SectionResult with outcome, row count, timing, and error detail.
        """
        section_start = time.perf_counter()

        try:
            success = await self._fetch_and_persist_section(
                section_gid, section, section_index, total_sections
            )

            fetch_time_ms = (time.perf_counter() - section_start) * 1000

            if success:
                # Get row count from in-memory section DF
                row_count = 0
                section_df = self._section_dfs.get(section_gid)
                if section_df is not None:
                    row_count = len(section_df)

                # Get watermark from manifest
                watermark = None
                if self._manifest is not None:
                    info = self._manifest.sections.get(section_gid)
                    if info is not None:
                        watermark = info.watermark

                return SectionResult(
                    section_gid=section_gid,
                    outcome=SectionOutcome.SUCCESS,
                    row_count=row_count,
                    fetch_time_ms=fetch_time_ms,
                    watermark=watermark,
                )
            else:
                # _fetch_and_persist_section returned False
                # Error was logged and manifest updated inside the method
                error_msg = None
                if self._manifest is not None:
                    info = self._manifest.sections.get(section_gid)
                    if info is not None and info.error:
                        error_msg = info.error

                return SectionResult(
                    section_gid=section_gid,
                    outcome=SectionOutcome.ERROR,
                    fetch_time_ms=fetch_time_ms,
                    error_message=error_msg or "Section fetch returned False",
                    error_type="UnknownError",
                )

        except Exception as e:  # BROAD-CATCH: isolation
            fetch_time_ms = (time.perf_counter() - section_start) * 1000
            return SectionResult(
                section_gid=section_gid,
                outcome=SectionOutcome.ERROR,
                fetch_time_ms=fetch_time_ms,
                error_message=str(e),
                error_type=type(e).__name__,
            )

    async def _load_checkpoint(self, section_gid: str) -> int:
        """Attempt to load a checkpoint for resume and return the page offset.

        Per TDD section 3.5: if the manifest shows an in-progress section
        with rows already fetched, try to read the checkpoint parquet from
        S3 and return the offset to resume from.

        Args:
            section_gid: Section GID to check for checkpoint.

        Returns:
            Page offset to resume from (0 if no checkpoint available).
        """
        section_info = None
        if self._manifest is not None:
            section_info = self._manifest.sections.get(section_gid)

        if (
            section_info is None
            or section_info.status != SectionStatus.IN_PROGRESS
            or section_info.rows_fetched <= 0
        ):
            return 0

        try:
            checkpoint_df = await self._persistence.read_section_async(
                self._project_gid, section_gid
            )
            if checkpoint_df is not None:
                logger.info(
                    "section_checkpoint_resumed",
                    extra={
                        "section_gid": section_gid,
                        "resumed_offset": section_info.last_fetched_offset,
                        "resumed_rows": section_info.rows_fetched,
                        "checkpoint_rows": len(checkpoint_df),
                    },
                )
                return section_info.last_fetched_offset
        except Exception as e:  # BROAD-CATCH: degrade
            logger.warning(
                "section_checkpoint_resume_failed",
                extra={
                    "section_gid": section_gid,
                    "error": str(e),
                    "fallback": "full_refetch",
                },
            )

        return 0

    async def _fetch_first_page(
        self,
        section_gid: str,
        iterator: Any,
        resume_offset: int,
    ) -> tuple[list[Task], int]:
        """Skip past resumed pages and fetch the first page of tasks.

        Args:
            section_gid: Section GID for logging.
            iterator: Async task iterator from API client.
            resume_offset: Number of pages to skip (0 for fresh fetch).

        Returns:
            Tuple of (first_page_tasks, resume_offset). Empty list if
            the section has no tasks.
        """
        # Skip past already-fetched pages on resume
        if resume_offset > 0:
            skip_count = 0
            skip_task_count = 0
            async for task in iterator:
                skip_task_count += 1
                if skip_task_count >= ASANA_PAGE_SIZE:
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

        # Fetch first page to determine section size
        first_page_tasks: list[Task] = []
        async for task in iterator:
            first_page_tasks.append(task)
            if len(first_page_tasks) >= ASANA_PAGE_SIZE:
                break

        logger.info(
            "large_section_detected",
            extra={
                "section_gid": section_gid,
                "first_page_count": len(first_page_tasks),
                "pacing_enabled": len(first_page_tasks) == ASANA_PAGE_SIZE,
            },
        )

        return first_page_tasks, resume_offset

    async def _fetch_large_section(
        self,
        section_gid: str,
        iterator: Any,
        first_page_tasks: list[Task],
    ) -> list[Task]:
        """Fetch remaining pages for a large section with pacing and checkpoints.

        Per TDD-large-section-resilience: pauses every N pages to avoid
        Asana cost-based 429s, and writes checkpoints every N pages.

        Args:
            section_gid: Section GID for logging and checkpoints.
            iterator: Async task iterator positioned after first page.
            first_page_tasks: Tasks from the first page.

        Returns:
            All tasks including first page.
        """
        _pacing = get_settings().pacing
        pace_pages_per_pause = _pacing.pages_per_pause
        pace_delay_seconds = _pacing.delay_seconds
        checkpoint_every_n_pages = _pacing.checkpoint_every_n_pages

        all_tasks: list[Task] = list(first_page_tasks)
        pages_fetched = 1
        current_page_task_count = 0

        async for task in iterator:
            all_tasks.append(task)
            current_page_task_count += 1

            if current_page_task_count >= ASANA_PAGE_SIZE:
                pages_fetched += 1
                current_page_task_count = 0

                # Pacing: pause every N pages
                if pages_fetched % pace_pages_per_pause == 0:
                    logger.info(
                        "section_pace_pause",
                        extra={
                            "section_gid": section_gid,
                            "pages_fetched": pages_fetched,
                            "rows_so_far": len(all_tasks),
                            "pause_seconds": pace_delay_seconds,
                        },
                    )
                    await asyncio.sleep(pace_delay_seconds)

                # Checkpoint: persist every N pages
                if pages_fetched % checkpoint_every_n_pages == 0:
                    await self._write_checkpoint(section_gid, all_tasks, pages_fetched)

        # Account for final partial page
        if current_page_task_count > 0:
            pages_fetched += 1

        return all_tasks

    async def _build_section_dataframe(
        self,
        tasks: list[Task],
    ) -> tuple[pl.DataFrame, str, datetime | None]:
        """Convert tasks to a DataFrame with freshness metadata.

        Uses delta approach (IMP-22) to avoid re-extracting tasks already
        processed during checkpoints. Three branches:
        (a) Checkpoint exists AND more tasks remain: extract delta, concatenate
        (b) Checkpoint exists AND no new tasks: use checkpoint directly
        (c) No checkpoint: full extraction (original behavior)

        Args:
            tasks: Fetched tasks for this section.

        Returns:
            Tuple of (section_df, gid_hash, watermark).
        """
        if self._checkpoint_df is not None:
            # Branch (a) or (b): checkpoint exists
            remaining_tasks = tasks[self._checkpoint_task_count :]
            if remaining_tasks:
                # Branch (a): extract only new tasks since last checkpoint
                task_dicts = [self._task_to_dict(task) for task in remaining_tasks]
                rows = await self._extract_rows(task_dicts)
                delta_df = safe_dataframe_construct(rows, self._schema)
                section_df = pl.concat(
                    [self._checkpoint_df, delta_df], how="diagonal_relaxed"
                )
            else:
                # Branch (b): all tasks were already checkpointed
                section_df = self._checkpoint_df
        else:
            # Branch (c): no checkpoint, full extraction
            task_dicts = [self._task_to_dict(task) for task in tasks]
            rows = await self._extract_rows(task_dicts)
            section_df = safe_dataframe_construct(rows, self._schema)

        from autom8_asana.dataframes.builders.freshness import compute_gid_hash

        gid_hash = compute_gid_hash([t.gid for t in tasks])
        watermark: datetime | None = None
        if "last_modified" in section_df.columns and len(section_df) > 0:
            max_val = section_df["last_modified"].max()
            if max_val is not None and isinstance(max_val, datetime):
                watermark = max_val

        return section_df, gid_hash, watermark

    async def _persist_section(
        self,
        section_gid: str,
        section_df: pl.DataFrame,
        gid_hash: str,
        watermark: datetime | None,
    ) -> bool:
        """Store section DataFrame in memory and persist to S3.

        Args:
            section_gid: Section GID.
            section_df: Built DataFrame for this section.
            gid_hash: SHA256 hash of sorted task GIDs.
            watermark: Max modified_at timestamp, if available.

        Returns:
            True if S3 write succeeded.
        """
        # Store in memory before S3 write (fallback if S3 unavailable)
        self._section_dfs[section_gid] = section_df

        # Write to S3 (this also updates manifest to COMPLETE)
        return await self._persistence.write_section_async(
            self._project_gid,
            section_gid,
            section_df,
            watermark=watermark,
            gid_hash=gid_hash,
        )

    async def _write_checkpoint(
        self,
        section_gid: str,
        tasks: list[Task],
        pages_fetched: int,
    ) -> bool:
        """Write accumulated tasks as a checkpoint parquet to S3.

        Uses delta extraction (IMP-22): only converts tasks added since the
        last checkpoint, then concatenates with the previous checkpoint
        DataFrame. This eliminates O(N*checkpoints) re-extraction amplification.

        Per TDD-large-section-resilience section 3.2 / ADR-LSR-002.

        Args:
            section_gid: Section GID being fetched.
            tasks: All accumulated tasks so far.
            pages_fetched: Number of pages consumed so far.

        Returns:
            True if checkpoint written successfully.
        """
        try:
            # Delta extraction: only process tasks since last checkpoint
            new_tasks = tasks[self._checkpoint_task_count :]
            task_dicts = [self._task_to_dict(task) for task in new_tasks]
            rows = await self._extract_rows(task_dicts)
            delta_df = safe_dataframe_construct(rows, self._schema)

            # Concatenate with previous checkpoint if it exists
            if self._checkpoint_df is not None:
                checkpoint_df = pl.concat(
                    [self._checkpoint_df, delta_df], how="diagonal_relaxed"
                )
            else:
                checkpoint_df = delta_df

            # Update delta state for next checkpoint
            self._checkpoint_df = checkpoint_df
            self._checkpoint_task_count = len(tasks)

            success = await self._persistence.write_checkpoint_async(
                self._project_gid,
                section_gid,
                checkpoint_df,
                pages_fetched=pages_fetched,
                rows_fetched=len(checkpoint_df),
            )

            if success:
                logger.info(
                    "section_checkpoint_written",
                    extra={
                        "section_gid": section_gid,
                        "pages_fetched": pages_fetched,
                        "rows_checkpointed": len(checkpoint_df),
                        "delta_rows": len(delta_df),
                    },
                )
                # Store in memory for fallback
                self._section_dfs[section_gid] = checkpoint_df
            else:
                logger.warning(
                    "section_checkpoint_write_failed",
                    extra={
                        "section_gid": section_gid,
                    },
                )

            return success

        except S3_TRANSPORT_ERRORS as e:
            logger.warning(
                "section_checkpoint_failed",
                extra={
                    "section_gid": section_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
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

    def _build_index_data(self, df: pl.DataFrame) -> dict[str, Any] | None:
        """Build GidLookupIndex serialized data from DataFrame.

        Delegates to the ``index_builder`` callback provided at construction.
        Returns *None* when no builder was supplied.
        """
        if self._index_builder is None:
            return None
        try:
            return self._index_builder(df, self._entity_type)
        except Exception as e:  # BROAD-CATCH: enrichment
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
        from autom8_asana.core.datetime_utils import parse_iso_datetime

        if value is None:
            return None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value

        if not isinstance(value, str):
            return None

        return parse_iso_datetime(value, default_now=False)


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
    index_builder: Callable[[pl.DataFrame, str], dict[str, Any] | None] | None = None,
) -> BuildResult:
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
        index_builder: Optional callback for building GidLookupIndex data.

    Returns:
        BuildResult with classified status and per-section detail.
    """
    builder = ProgressiveProjectBuilder(
        client=client,
        project_gid=project_gid,
        entity_type=entity_type,
        schema=schema,
        persistence=persistence,
        resolver=resolver,
        store=store,
        index_builder=index_builder,
    )
    result: BuildResult = await builder.build_progressive_async(resume=resume)
    return result
