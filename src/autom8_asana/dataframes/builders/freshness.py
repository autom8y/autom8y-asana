"""Section-level freshness probing and delta merge for progressive cache.

Detects stale sections via lightweight API calls (GID hash + modified_since)
and applies delta merges for changed sections without full rebuilds.

Two-step probe design per POC findings:
1. GID hash comparison detects structural changes (adds/removes)
2. modified_since check detects in-place edits (only if hash matches)

API budget: 1-2 calls per section (~300-550ms each), ~34 sections at 8 concurrent = ~2-3s.
"""

from __future__ import annotations

import hashlib
import io
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.models.schema import DataFrameSchema
    from autom8_asana.dataframes.section_persistence import (
        SectionManifest,
        SectionPersistence,
    )
    from autom8_asana.dataframes.views.dataframe_view import DataFrameViewPlugin

__all__ = [
    "ProbeVerdict",
    "SectionProbeResult",
    "SectionFreshnessProber",
    "compute_gid_hash",
]

logger = get_logger(__name__)


def compute_gid_hash(gids: list[str]) -> str:
    """Compute a stable hash of sorted GIDs for structural change detection.

    Args:
        gids: List of task GIDs.

    Returns:
        Truncated SHA256 hex digest (16 chars).
    """
    return hashlib.sha256("|".join(sorted(gids)).encode()).hexdigest()[:16]


class ProbeVerdict(str, Enum):
    """Result of probing a single section for freshness."""

    CLEAN = "clean"
    STRUCTURE_CHANGED = "structure_changed"
    CONTENT_CHANGED = "content_changed"
    NO_BASELINE = "no_baseline"
    PROBE_FAILED = "probe_failed"


class SectionProbeResult:
    """Result of probing a single section."""

    __slots__ = ("section_gid", "verdict", "current_gids", "current_gid_hash")

    def __init__(
        self,
        section_gid: str,
        verdict: ProbeVerdict,
        current_gids: list[str] | None = None,
        current_gid_hash: str | None = None,
    ) -> None:
        self.section_gid = section_gid
        self.verdict = verdict
        self.current_gids = current_gids
        self.current_gid_hash = current_gid_hash


class SectionFreshnessProber:
    """Probes COMPLETE manifest sections for staleness via lightweight API calls.

    Uses a two-step algorithm per POC findings:
    1. Fetch GIDs only (~300-550ms) and compare hash → detects structural changes
    2. If hash matches, use modified_since with limit=1 → detects content edits

    Deletions are invisible to modified_since, so the GID hash step is essential.
    """

    def __init__(
        self,
        client: AsanaClient,
        persistence: SectionPersistence,
        project_gid: str,
        manifest: SectionManifest,
        schema: DataFrameSchema,
        *,
        dataframe_view: DataFrameViewPlugin | None = None,
        max_concurrent: int = 8,
    ) -> None:
        self._client = client
        self._persistence = persistence
        self._project_gid = project_gid
        self._manifest = manifest
        self._schema = schema
        self._dataframe_view = dataframe_view
        self._max_concurrent = max_concurrent

    async def probe_all_async(self) -> list[SectionProbeResult]:
        """Probe all COMPLETE sections for freshness with bounded concurrency.

        Returns:
            List of SectionProbeResult for each probed section.
        """
        complete_gids = self._manifest.get_complete_section_gids()
        if not complete_gids:
            return []

        results = await gather_with_limit(
            [self._probe_section(gid) for gid in complete_gids],
            max_concurrent=self._max_concurrent,
        )

        # Log summary
        verdicts = {}
        for r in results:
            verdicts[r.verdict.value] = verdicts.get(r.verdict.value, 0) + 1

        logger.info(
            "freshness_probe_complete",
            extra={
                "project_gid": self._project_gid,
                "sections_probed": len(results),
                "verdicts": verdicts,
            },
        )

        return results

    async def _probe_section(self, section_gid: str) -> SectionProbeResult:
        """Probe a single section for freshness.

        Algorithm:
        1. Fetch GIDs only → compute hash
        2. If stored gid_hash is None → NO_BASELINE
        3. If hash differs → STRUCTURE_CHANGED
        4. If hash matches → modified_since check
           - Per POC: modified_since is inclusive (>=), so boundary task always returned
           - >1 result → CONTENT_CHANGED (real changes beyond false-positive)
           - <=1 result → CLEAN
        5. API errors → PROBE_FAILED (treated as clean)
        """
        section_info = self._manifest.sections.get(section_gid)
        if section_info is None:
            return SectionProbeResult(section_gid, ProbeVerdict.PROBE_FAILED)

        try:
            # Step 1: Fetch GIDs only
            tasks = await self._client.tasks.list_async(
                section=section_gid,
                opt_fields=["gid"],
            ).collect()

            current_gids = [t.gid for t in tasks]
            current_hash = compute_gid_hash(current_gids)

            # Step 2: Check baseline
            if section_info.gid_hash is None:
                return SectionProbeResult(
                    section_gid,
                    ProbeVerdict.NO_BASELINE,
                    current_gids=current_gids,
                    current_gid_hash=current_hash,
                )

            # Step 3: Hash comparison
            if current_hash != section_info.gid_hash:
                return SectionProbeResult(
                    section_gid,
                    ProbeVerdict.STRUCTURE_CHANGED,
                    current_gids=current_gids,
                    current_gid_hash=current_hash,
                )

            # Step 4: modified_since check (only if hash matches)
            if section_info.watermark is not None:
                watermark_iso = section_info.watermark.isoformat()
                modified_tasks = await self._client.tasks.list_async(
                    section=section_gid,
                    modified_since=watermark_iso,
                    opt_fields=["gid"],
                    limit=2,
                ).collect()

                # Per POC: modified_since is inclusive (>=), so the task at
                # exactly the watermark is always returned (1 false-positive).
                # >1 means real changes exist.
                if len(modified_tasks) > 1:
                    return SectionProbeResult(
                        section_gid,
                        ProbeVerdict.CONTENT_CHANGED,
                        current_gids=current_gids,
                        current_gid_hash=current_hash,
                    )

            return SectionProbeResult(
                section_gid,
                ProbeVerdict.CLEAN,
                current_gids=current_gids,
                current_gid_hash=current_hash,
            )

        except Exception as e:
            logger.warning(
                "freshness_probe_section_failed",
                extra={
                    "project_gid": self._project_gid,
                    "section_gid": section_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return SectionProbeResult(section_gid, ProbeVerdict.PROBE_FAILED)

    async def apply_deltas_async(
        self,
        stale_results: list[SectionProbeResult],
        dataframe_view: DataFrameViewPlugin | None = None,
    ) -> int:
        """Apply delta merges for stale sections.

        For each stale section:
        1. Read existing parquet from S3
        2. Compute added/removed GIDs
        3. Fetch modified + added tasks with full opt_fields
        4. Upsert into existing DataFrame
        5. Persist updated section parquet
        6. Update manifest with new watermark/gid_hash

        Args:
            stale_results: Probe results with non-CLEAN verdicts.
            dataframe_view: Optional DataFrameViewPlugin for row extraction.

        Returns:
            Number of sections successfully delta-updated.
        """
        view = dataframe_view or self._dataframe_view
        updated_count = 0

        for result in stale_results:
            try:
                success = await self._apply_section_delta(result, view)
                if success:
                    updated_count += 1
            except Exception as e:
                logger.error(
                    "freshness_delta_section_failed",
                    extra={
                        "project_gid": self._project_gid,
                        "section_gid": result.section_gid,
                        "verdict": result.verdict.value,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        logger.info(
            "freshness_delta_complete",
            extra={
                "project_gid": self._project_gid,
                "stale_sections": len(stale_results),
                "updated_sections": updated_count,
            },
        )

        return updated_count

    async def _apply_section_delta(
        self,
        result: SectionProbeResult,
        view: DataFrameViewPlugin | None,
    ) -> bool:
        """Apply delta merge for a single stale section.

        Falls back to full section re-fetch if:
        - Existing parquet is missing
        - NO_BASELINE verdict (no stored gid_hash)

        Returns:
            True if section was successfully updated.
        """
        section_gid = result.section_gid
        section_info = self._manifest.sections.get(section_gid)

        # For NO_BASELINE or missing parquet, do a full re-fetch
        existing_df = await self._persistence.read_section_async(
            self._project_gid, section_gid
        )

        if existing_df is None or result.verdict == ProbeVerdict.NO_BASELINE:
            return await self._full_section_refetch(section_gid, result, view)

        # Delta merge path
        current_gids = set(result.current_gids or [])

        # Extract stored GIDs from parquet
        if "gid" in existing_df.columns:
            stored_gids = set(existing_df["gid"].to_list())
        else:
            # No gid column — fall back to full re-fetch
            return await self._full_section_refetch(section_gid, result, view)

        added_gids = current_gids - stored_gids
        removed_gids = stored_gids - current_gids

        # Start with existing DF, remove deleted tasks
        if removed_gids:
            existing_df = existing_df.filter(~pl.col("gid").is_in(list(removed_gids)))

        # Fetch modified tasks (since watermark)
        delta_tasks = []
        if section_info and section_info.watermark is not None:
            watermark_iso = section_info.watermark.isoformat()
            modified_raw = await self._client.tasks.list_async(
                section=section_gid,
                modified_since=watermark_iso,
                opt_fields=BASE_OPT_FIELDS,
            ).collect()
            delta_tasks.extend(modified_raw)

        # Fetch added tasks individually (may not appear in modified_since)
        fetched_gids = {t.gid for t in delta_tasks}
        for gid in added_gids:
            if gid not in fetched_gids:
                try:
                    task = await self._client.tasks.get_async(
                        gid, opt_fields=BASE_OPT_FIELDS
                    )
                    delta_tasks.append(task)
                except Exception as e:
                    logger.warning(
                        "freshness_delta_fetch_added_failed",
                        extra={
                            "section_gid": section_gid,
                            "task_gid": gid,
                            "error": str(e),
                        },
                    )

        if delta_tasks and view is not None:
            # Convert tasks to rows using the view
            task_dicts = []
            for t in delta_tasks:
                if hasattr(t, "model_dump"):
                    task_dicts.append(t.model_dump())
                else:
                    task_dicts.append({"gid": t.gid, "name": getattr(t, "name", "")})

            rows = await view._extract_rows_async(
                task_dicts, project_gid=self._project_gid
            )

            from autom8_asana.dataframes.builders.fields import coerce_rows_to_schema

            coerced = coerce_rows_to_schema(rows, self._schema)
            delta_df = pl.DataFrame(coerced, schema=self._schema.to_polars_schema())

            # Upsert: remove old versions of delta GIDs, then concat
            delta_gids = set(delta_df["gid"].to_list())
            existing_df = existing_df.filter(~pl.col("gid").is_in(list(delta_gids)))
            merged_df = pl.concat([existing_df, delta_df], how="diagonal_relaxed")
        elif removed_gids:
            # Only removals, no additions/modifications
            merged_df = existing_df
        else:
            # Nothing to change
            merged_df = existing_df

        # Compute new watermark and gid_hash
        new_gid_hash = compute_gid_hash(list(current_gids))
        new_watermark: datetime | None = None
        if "_modified_at" in merged_df.columns and len(merged_df) > 0:
            max_val = merged_df["_modified_at"].max()
            if max_val is not None:
                new_watermark = max_val if isinstance(max_val, datetime) else None

        # Persist updated section
        await self._persistence.write_section_async(
            self._project_gid,
            section_gid,
            merged_df,
            watermark=new_watermark,
            gid_hash=new_gid_hash,
        )

        logger.info(
            "freshness_delta_section_updated",
            extra={
                "project_gid": self._project_gid,
                "section_gid": section_gid,
                "verdict": result.verdict.value,
                "added": len(added_gids),
                "removed": len(removed_gids),
                "delta_tasks": len(delta_tasks),
                "final_rows": len(merged_df),
            },
        )

        return True

    async def _full_section_refetch(
        self,
        section_gid: str,
        result: SectionProbeResult,
        view: DataFrameViewPlugin | None,
    ) -> bool:
        """Full re-fetch for a section (fallback when delta merge not possible).

        Args:
            section_gid: Section GID.
            result: Probe result with current GIDs.
            view: DataFrameViewPlugin for row extraction.

        Returns:
            True if section was successfully re-fetched and persisted.
        """
        tasks = await self._client.tasks.list_async(
            section=section_gid,
            opt_fields=BASE_OPT_FIELDS,
        ).collect()

        if not tasks:
            from autom8_asana.dataframes.section_persistence import SectionStatus

            await self._persistence.update_manifest_section_async(
                self._project_gid,
                section_gid,
                SectionStatus.COMPLETE,
                rows=0,
                watermark=None,
                gid_hash=compute_gid_hash([]),
            )
            return True

        if view is None:
            logger.warning(
                "freshness_full_refetch_no_view",
                extra={
                    "project_gid": self._project_gid,
                    "section_gid": section_gid,
                },
            )
            return False

        task_dicts = []
        for t in tasks:
            if hasattr(t, "model_dump"):
                task_dicts.append(t.model_dump())
            else:
                task_dicts.append({"gid": t.gid, "name": getattr(t, "name", "")})

        rows = await view._extract_rows_async(
            task_dicts, project_gid=self._project_gid
        )

        from autom8_asana.dataframes.builders.fields import coerce_rows_to_schema

        coerced = coerce_rows_to_schema(rows, self._schema)
        section_df = pl.DataFrame(coerced, schema=self._schema.to_polars_schema())

        # Compute freshness metadata
        gid_hash = compute_gid_hash([t.gid for t in tasks])
        watermark: datetime | None = None
        if "_modified_at" in section_df.columns and len(section_df) > 0:
            max_val = section_df["_modified_at"].max()
            if max_val is not None:
                watermark = max_val if isinstance(max_val, datetime) else None

        await self._persistence.write_section_async(
            self._project_gid,
            section_gid,
            section_df,
            watermark=watermark,
            gid_hash=gid_hash,
        )

        logger.info(
            "freshness_full_refetch_complete",
            extra={
                "project_gid": self._project_gid,
                "section_gid": section_gid,
                "rows": len(section_df),
            },
        )

        return True
