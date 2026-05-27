"""Section-level freshness probing and delta merge for progressive cache.

Detects stale sections via lightweight API calls (GID hash + modified_since)
and applies delta merges for changed sections without full rebuilds.

Two-step probe design per POC findings:
1. GID hash comparison detects structural changes (adds/removes)
2. modified_since check detects in-place edits (only if hash matches)

API budget: 1-2 calls per section (~300-550ms each), ~34 sections at 8 concurrent = ~2-3s.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import polars as pl
from autom8y_log import get_logger

from autom8_asana.dataframes.builders.base import gather_with_limit
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS

if TYPE_CHECKING:
    from collections.abc import Mapping

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


def _parse_dt(value: Any) -> datetime | None:
    """Best-effort parse of an Asana ``modified_at`` value into an aware UTC datetime.

    Asana returns ISO-8601 strings (e.g. ``"2026-05-26T18:42:00.123Z"``);
    SDK shapes may also surface a ``datetime`` directly. Return ``None``
    on anything we cannot interpret -- the caller treats ``None`` as
    "cannot prove a strict-after edit" and falls through to CLEAN.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        # Normalize naive datetimes to UTC -- comparisons against the
        # stored watermark (aware) would otherwise raise TypeError.
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if isinstance(value, str):
        try:
            # ``fromisoformat`` accepts the "+00:00" form natively;
            # Asana's "Z" suffix needs a small substitution on Python
            # versions where fromisoformat is strict about that.
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _any_modified_after(tasks: list[Any], watermark: datetime) -> bool:
    """Return True iff any task in ``tasks`` has ``modified_at`` strictly > watermark.

    The watermark-task-identity test that closes the QA D3 / spike
    line-72-73 false-CLEAN blind spot for watermark-bearing sections
    (ADR-006 §Revision-2-correction / TDD §2.5).

    A single returned task whose ``modified_at`` is the inclusive
    boundary (``== watermark``) stays CLEAN -- this is what protects
    against the false-positive storm on the steady-state boundary
    task. An edit to the watermark task itself or to a single-task
    section produces ``modified_at > watermark`` and is caught.
    """
    if not tasks:
        return False
    for t in tasks:
        t_modified = _parse_dt(getattr(t, "modified_at", None))
        if t_modified is not None and t_modified > watermark:
            return True
    return False


class ProbeVerdict(StrEnum):
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
        section_names: Mapping[str, str | None] | None = None,
    ) -> None:
        self._client = client
        self._persistence = persistence
        self._project_gid = project_gid
        self._manifest = manifest
        self._schema = schema
        self._dataframe_view = dataframe_view
        self._max_concurrent = max_concurrent
        # ``section_names``: ``{gid: name}`` map sourced from the warm-entry
        # ``_list_sections()`` call (threaded through
        # ``progressive._probe_freshness``). Same source the stamp + re-seed
        # pass uses -- single source of truth for names across the warm.
        #
        # D11 (QA-gate-2): without this, the prober's delta-apply path calls
        # ``write_section_async`` without ``name=``, so a section renamed or
        # deleted in Asana mid-warm (absent from ``_list_sections()`` but
        # present in the manifest) gets re-completed with ``prior.name``
        # carry-forward only. If ``prior.name`` is ``None`` (existing prod
        # steady state) and the GID is NOT in ``names_map`` (because the
        # section was renamed/deleted mid-warm), the row lands with
        # ``name=None`` + ``last_verified_at=now`` -> permanent ERROR-tier
        # ``section_name_contract_violation`` because ``any_stamped=True``.
        # Passing ``section_names`` here lets the delta path supply the
        # carried-forward name to ``write_section_async``, matching the
        # re-seed pass in ``progressive._probe_freshness``.
        self._section_names: Mapping[str, str | None] = section_names or {}

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
        verdicts: dict[str, int] = {}
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
            #
            # Watermark-task-identity test per ADR-006 §Decision-5b / TDD §2.5.
            # The old `len(modified_tasks) > 1` gate missed:
            #   - any edit to a single-task section, and
            #   - an edit to the exact watermark task itself
            # because ``modified_since`` is inclusive (``>=``), so the
            # boundary task is always returned even when unchanged. We
            # now fetch ``modified_at`` alongside ``gid`` and flag
            # CONTENT_CHANGED when ANY returned task has
            # ``modified_at > watermark`` (strict). An unchanged boundary
            # task has ``modified_at == watermark`` -> CLEAN.
            #
            # Residual (documented, NOT a regression): null-watermark
            # sections (~21/34 offer, ~4/17 unit per QA 2026-05-27)
            # bypass this branch entirely and retain the pre-existing
            # hash-only detection. ADR-006 §Revision-2-correction (D8).
            if section_info.watermark is not None:
                watermark = section_info.watermark
                watermark_iso = watermark.isoformat()
                modified_tasks = await self._client.tasks.list_async(
                    section=section_gid,
                    modified_since=watermark_iso,
                    opt_fields=["gid", "modified_at"],
                    limit=2,
                ).collect()

                if _any_modified_after(modified_tasks, watermark):
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

        except Exception as e:  # BROAD-CATCH: api-boundary -- probe calls Asana API which can throw diverse HTTP errors  # noqa: BLE001
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
    ) -> tuple[int, frozenset[str]]:
        """Apply delta merges for stale sections in parallel.

        Per IMP-08: Each delta application is independent (different sections,
        different S3 keys), so they can run concurrently with bounded parallelism.

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
            Tuple of (updated_count, applied_gids), where applied_gids is a
            frozenset of section GIDs whose delta-apply SUCCEEDED. The stamp
            block in ``progressive._probe_freshness`` consumes applied_gids
            to gate ``last_verified_at`` on per-section reconciliation
            success (ADR-006 §Decision-5c / TDD §2.2 D4) — a delta verdict
            whose apply FAILED is NOT stamp-eligible.
        """
        from autom8_asana.core.concurrency import gather_with_semaphore

        view = dataframe_view or self._dataframe_view

        if not stale_results:
            return 0, frozenset()

        results = await gather_with_semaphore(
            (self._apply_section_delta(result, view) for result in stale_results),
            concurrency=5,
            label="apply_deltas",
        )

        updated_count = 0
        applied_gids: set[str] = set()
        for i, outcome in enumerate(results):
            if isinstance(outcome, BaseException):
                logger.error(
                    "freshness_delta_section_failed",
                    extra={
                        "project_gid": self._project_gid,
                        "section_gid": stale_results[i].section_gid,
                        "verdict": stale_results[i].verdict.value,
                        "error": str(outcome),
                        "error_type": type(outcome).__name__,
                    },
                )
            elif outcome:
                updated_count += 1
                applied_gids.add(stale_results[i].section_gid)

        logger.info(
            "freshness_delta_complete",
            extra={
                "project_gid": self._project_gid,
                "stale_sections": len(stale_results),
                "updated_sections": updated_count,
            },
        )

        return updated_count, frozenset(applied_gids)

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
        existing_df = await self._persistence.read_section_async(self._project_gid, section_gid)

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

        # Fetch added tasks in parallel (may not appear in modified_since)
        fetched_gids = {t.gid for t in delta_tasks}
        unfetched_added = [gid for gid in added_gids if gid not in fetched_gids]

        if unfetched_added:
            sem = asyncio.Semaphore(8)

            async def _fetch_one(gid: str) -> tuple[str, Any]:
                """Fetch a single added GID with bounded concurrency."""
                async with sem:
                    return gid, await self._client.tasks.get_async(gid, opt_fields=BASE_OPT_FIELDS)

            fetch_results = await asyncio.gather(
                *[_fetch_one(g) for g in unfetched_added],
                return_exceptions=True,
            )

            succeeded = 0
            failed = 0
            for i, fetch_result in enumerate(fetch_results):
                if isinstance(fetch_result, BaseException):
                    failed += 1
                    logger.warning(
                        "freshness_delta_fetch_added_failed",
                        extra={
                            "section_gid": section_gid,
                            "task_gid": unfetched_added[i],
                            "error": str(fetch_result),
                            "error_type": type(fetch_result).__name__,
                        },
                    )
                else:
                    _gid, task = fetch_result
                    delta_tasks.append(task)
                    succeeded += 1

            if unfetched_added:
                logger.info(
                    "freshness_delta_parallel_fetch_summary",
                    extra={
                        "section_gid": section_gid,
                        "total_added": len(unfetched_added),
                        "succeeded": succeeded,
                        "failed": failed,
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

            rows = await view._extract_rows_async(task_dicts, project_gid=self._project_gid)

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
        if "last_modified" in merged_df.columns and len(merged_df) > 0:
            max_val = merged_df["last_modified"].max()
            if max_val is not None:
                new_watermark = max_val if isinstance(max_val, datetime) else None

        # Persist updated section.
        #
        # D11 (QA-gate-2): thread the warm-entry section name so the
        # delta-apply path supplies ``name=`` to
        # ``write_section_async`` -> ``update_manifest_section_async`` ->
        # ``mark_section_complete``. Without this, ``mark_section_complete``
        # would only see the ``prior.name`` carry-forward; on existing prod
        # manifests where ``prior.name is None``, that propagates ``None``
        # indefinitely on the delta path. The same ``self._section_names``
        # is what ``progressive._probe_freshness`` uses to drive the
        # stamp+re-seed pass -- single source of truth.
        await self._persistence.write_section_async(
            self._project_gid,
            section_gid,
            merged_df,
            watermark=new_watermark,
            gid_hash=new_gid_hash,
            name=self._section_names.get(section_gid),
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

            # D11: empty-section completion also runs through
            # mark_section_complete -- thread the same name so it does
            # NOT propagate ``prior.name=None`` for sections absent from
            # the warm-entry list.
            await self._persistence.update_manifest_section_async(
                self._project_gid,
                section_gid,
                SectionStatus.COMPLETE,
                rows=0,
                watermark=None,
                gid_hash=compute_gid_hash([]),
                name=self._section_names.get(section_gid),
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

        rows = await view._extract_rows_async(task_dicts, project_gid=self._project_gid)

        from autom8_asana.dataframes.builders.fields import coerce_rows_to_schema

        coerced = coerce_rows_to_schema(rows, self._schema)
        section_df = pl.DataFrame(coerced, schema=self._schema.to_polars_schema())

        # Compute freshness metadata
        gid_hash = compute_gid_hash([t.gid for t in tasks])
        watermark: datetime | None = None
        if "last_modified" in section_df.columns and len(section_df) > 0:
            max_val = section_df["last_modified"].max()
            if max_val is not None:
                watermark = max_val if isinstance(max_val, datetime) else None

        # D11: full re-fetch also persists with name= so the delta path
        # is symmetric with the §2.2.1 fix in
        # _fetch_and_persist_section (progressive.py:1325).
        await self._persistence.write_section_async(
            self._project_gid,
            section_gid,
            section_df,
            watermark=watermark,
            gid_hash=gid_hash,
            name=self._section_names.get(section_gid),
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
