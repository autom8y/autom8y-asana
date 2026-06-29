"""Insights export workflow -- daily HTML report for Offer tasks.

Per TDD-EXPORT-001: Second WorkflowAction implementation.
Enumerates active Offers, resolves each to office_phone + vertical,
fetches 12 tables from autom8_data, composes HTML report,
and uploads as attachment to each Offer task.

Per ADR-bridge-intermediate-base-class: Rebased onto
BridgeWorkflowAction in sprint-3.
"""

from __future__ import annotations

import asyncio
import pathlib
import re
import time
from dataclasses import dataclass as _dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_api_schemas import OfficePhone
from autom8y_log import get_logger

from autom8_asana.automation.workflows.active_offer_enumeration import (
    enumerate_active_offers,
)
from autom8_asana.automation.workflows.base import (
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.bridge_base import (
    BridgeOutcome,
    BridgeWorkflowAction,
)
from autom8_asana.automation.workflows.insights.formatter import (
    InsightsReportData,
    TableResult,
    compose_report,
)
from autom8_asana.automation.workflows.insights.tables import (
    TABLE_SPECS,
    DispatchType,
    TableSpec,
)
from autom8_asana.clients.utils.pii import mask_phone_number
from autom8_asana.errors import OperatorAccessDeniedError, OperatorMintRefusedError
from autom8_asana.models.business.offer import Offer
from autom8_asana.resolution.context import ResolutionContext

if TYPE_CHECKING:
    from autom8_asana.clients.attachments import AttachmentsClient
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.core.scope import EntityScope

logger = get_logger(__name__)

# Feature flag environment variable
EXPORT_ENABLED_ENV_VAR = "AUTOM8_EXPORT_ENABLED"

# Offer project GID (canonical source: Offer.PRIMARY_PROJECT_GID)
OFFER_PROJECT_GID: str = Offer.PRIMARY_PROJECT_GID  # type: ignore[assignment]

# Default concurrency for parallel offer processing
DEFAULT_MAX_CONCURRENCY = 5

# Default attachment pattern for cleanup
DEFAULT_ATTACHMENT_PATTERN = "insights_export_*.html"

# Workflow version identifier (for footer)
WORKFLOW_VERSION = "insights-export-v1.0"

# Default row limits per table type.
# ASSET TABLE: capped at 150, sorted by spend desc (per WS-G spec), applied at
# display time. (GAP-1 PR-A: APPOINTMENTS/LEADS were dropped from the cross-tenant
# export as PII; their limits are gone with them.)
DEFAULT_ROW_LIMITS: dict[str, int] = {
    "ASSET TABLE": 150,
}

# Table names in section order -- derived from TABLE_SPECS (per TDD-SPRINT-C).
TABLE_NAMES = [s.table_name for s in TABLE_SPECS]

# GAP-1 PR-A: the cross-tenant export now serves the 4 CLEAN de-identified
# aggregate tables only (the 4 PII tables are dropped; BY-period + UNUSED ASSETS
# are deferred to PR-FF). See tables.py.
TOTAL_TABLE_COUNT = len(TABLE_NAMES)  # 4


class InsightsExportWorkflow(BridgeWorkflowAction):
    """Daily insights export HTML report for Offer tasks.

    Per PRD-EXPORT-001: Second WorkflowAction implementation.
    Per ADR-bridge-intermediate-base-class: Inherits from
    BridgeWorkflowAction (sprint-3 migration).

    Lifecycle:
    1. Check feature flag (AUTOM8_EXPORT_ENABLED) -- inherited
    2. Enumerate active Offer tasks in BusinessOffers project
    3. For each Offer (with concurrency limit):
       a. Resolve parent Business -> office_phone + vertical
       b. Fetch 12 tables concurrently from DataServiceClient
       c. Compose HTML report via insights_formatter
       d. Upload new .html attachment (upload-first)
       e. Delete old matching .html/.md attachments
    4. Return WorkflowResult with per-item and per-table tracking

    Args:
        asana_client: AsanaClient for Asana API operations.
        data_client: DataServiceClient for autom8_data insights fetch.
        attachments_client: AttachmentsClient for upload/delete operations.
    """

    feature_flag_env_var = EXPORT_ENABLED_ENV_VAR

    def __init__(
        self,
        asana_client: Any,  # AsanaClient (TYPE_CHECKING avoids circular)
        data_client: DataServiceClient,
        attachments_client: AttachmentsClient,
        preview_dir: pathlib.Path | str | None = None,
    ) -> None:
        super().__init__(asana_client, data_client, attachments_client)
        # Narrow type for mypy: base class stores DataSource | None,
        # but this bridge always has a concrete DataServiceClient.
        self._data_client: DataServiceClient = data_client
        # Dedup cache: business_gid -> (office_phone, vertical, business_name)
        # Per AT3-001: eliminates redundant Business fetches across offers.
        self._business_cache: dict[str, tuple[str, str, str | None] | None] = {}
        # Tracks offer_gid -> business_gid for cache lookups
        self._offer_to_business: dict[str, str | None] = {}
        # Actual cache hit counter (per F-13: replaces derived formula)
        self._cache_hits: int = 0
        # GAP-1 PR-A: pre-fetched operator-plane batch cache, populated once per run
        # in execute_async (batch-over-O). Shape: {table_name: {office_phone: rows}}.
        # A per-insight route denial leaves THAT table absent here -> its office
        # decks render empty gracefully (no crash, no SA fleet-read fallback). A
        # whole-plane mint refusal is handled separately via the INERT no-op guard
        # below (the run skips publish entirely rather than rendering empty decks).
        self._operator_batch: dict[str, dict[str, list[dict[str, Any]]]] = {}
        # GAP-1 PR-A INERT no-op guard: True when the operator-plane mint was
        # REFUSED (the empty OPERATOR_ARN_ALLOWLIST 403, or no ambient AWS
        # credentials to sign sts:GetCallerIdentity). This is the deploy-INERT
        # signal. It is DISTINCT from a successful-but-empty live result: only a
        # mint REFUSAL makes the run a TRUE no-op (execute_async skips the whole
        # publish step -- no empty deck is built/uploaded and NO prior attachment
        # is deleted), so a pre-FLIP schedule firing cannot overwrite any Offer's
        # last-good deck with an empty one. Reset at the top of every prefetch.
        self._operator_plane_refused: bool = False
        # WS-2 partial-run protection: offices the operator batch could NOT serve
        # this run because the run budget / throttle stopped the bisection before
        # reaching them (NON-definitive). _process_offer SKIPS the publish for these
        # (no empty deck uploaded, NO prior attachment deleted) -- the per-office
        # mirror of the INERT no-op guard, so a budget-capped partial run never
        # overwrites an unreached office's last-good deck (RISK-4). Reset per run.
        # Distinct from drift/denied offices (definitive answer -> publish empty).
        self._operator_unreached_offices: set[str] = set()
        # Dry-run preview output directory. Injectable so concurrent dry-runs
        # (and xdist-parallel tests) target distinct, non-colliding directories
        # instead of one shared cwd-relative path whose deterministic filename
        # (insights_export_{business}_{date}.html) races write_text/read under
        # -n auto. Defaults to cwd-relative .wip for the operator-local preview.
        self._preview_dir: pathlib.Path = (
            pathlib.Path(preview_dir) if preview_dir is not None else pathlib.Path(".wip")
        )

    @property
    def workflow_id(self) -> str:  # type: ignore[override]  # read-only property overrides base attribute
        return "insights-export"

    # --- Bridge hooks ---

    async def enumerate_async(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Enumerate Offer entities based on scope.

        Per TDD-ENTITY-SCOPE-001 Section 2.4.1:
        When scope.has_entity_ids: return synthetic offer dicts for each GID.
        When scope is empty: perform full section-targeted enumeration.

        Overrides base to add targeted logging before delegating to
        super() for fast-path and limit handling.

        Args:
            scope: EntityScope controlling targeting, filtering, and limits.

        Returns:
            List of offer dicts with {gid, name} shape.
        """
        if scope.has_entity_ids:
            logger.info(
                "insights_export_targeted",
                entity_ids=scope.entity_ids,
                dry_run=scope.dry_run,
            )
        return await super().enumerate_async(scope)

    async def enumerate_entities(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Full enumeration: section-targeted fetch of ACTIVE offers.

        Per ADR-bridge-intermediate-base-class: Implements the abstract
        hook called by base class enumerate_async() for the full path.
        """
        return await self._enumerate_offers()

    async def process_entity(
        self,
        entity: dict[str, Any],
        params: dict[str, Any],
    ) -> _OfferOutcome:
        """Dispatch to _process_offer with params extraction.

        Per ADR-bridge-intermediate-base-class: Implements the abstract
        hook called by base class execute_async() for each entity.
        """
        return await self._process_offer(
            offer_gid=entity["gid"],
            offer_name=entity.get("name"),
            attachment_pattern=params.get("attachment_pattern", DEFAULT_ATTACHMENT_PATTERN),
            row_limits=params.get("row_limits", DEFAULT_ROW_LIMITS),
            dry_run=params.get("dry_run", False),
        )

    async def execute_async(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the insights export for the given entities.

        Overrides base to add start/completion logging that preserves
        existing observability events.

        Args:
            entities: Offer dicts from enumerate_async.
                Shape: [{gid, name}, ...]
            params: Configuration parameters:
                - max_concurrency (int): Parallel offer limit, default 5
                - row_limits (dict): Per-table row limits override
                - attachment_pattern (str): Glob for old attachment cleanup
                - dry_run (bool): Skip write operations

        Returns:
            WorkflowResult with total/succeeded/failed/skipped counts
            and per-offer table tracking in metadata.
        """
        max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        dry_run = params.get("dry_run", False)

        logger.info(
            "insights_export_started",
            total_offers=len(entities),
            max_concurrency=max_concurrency,
            dry_run=dry_run,
        )

        # GAP-1 PR-A: mint once + fetch the clean tables batch-over-O BEFORE the
        # per-offer fan-out. The per-offer pass reads the resulting cache (it does
        # NOT make per-office operator calls -- that would blow the 10/min route
        # budget). A whole-plane mint refusal sets self._operator_plane_refused;
        # the INERT no-op guard below then skips the publish step entirely (a
        # per-insight denial instead leaves only that table empty and still
        # publishes).
        await self._prefetch_operator_tables(entities, params)

        # GAP-1 PR-A INERT no-op guard: if the operator-plane mint was REFUSED
        # (the empty OPERATOR_ARN_ALLOWLIST 403, or no ambient AWS credentials),
        # the whole operator plane is dark. SKIP the publish step ENTIRELY at the
        # earliest INERT detection -- do NOT build or upload an empty deck, and do
        # NOT delete prior attachments. This makes deploy-INERT a TRUE no-op by
        # construction (not by a fragile schedule-disable gate): a pre-FLIP
        # schedule firing leaves every Offer's last-good deck intact, with no
        # empty-deck overwrite. The completion counter stays RED
        # (insights_export_completed is NOT emitted) and there is NO SA fleet-read
        # fallback (G-NO-FALLBACK). NOTE: this fires ONLY on mint REFUSAL; a
        # successful-but-empty live result still follows the normal publish path.
        if self._operator_plane_refused:
            logger.warning(
                "insights_export_skipped_operator_plane_inert",
                total_offers=len(entities),
                dry_run=dry_run,
            )
            now = datetime.now(UTC)
            return WorkflowResult(
                workflow_id=self.workflow_id,
                started_at=now,
                completed_at=now,
                total=len(entities),
                succeeded=0,
                failed=0,
                skipped=len(entities),
                metadata={"operator_plane_inert": True},
            )

        result = await super().execute_async(entities, params)

        # WS-2: flag the run partial iff the operator batch left owned offices
        # unreached this run (budget/throttle-capped). Their prior decks were
        # preserved (RISK-4); the operator can re-drive next window or land Lever 1.
        if self._operator_unreached_offices:
            result.metadata["operator_run_partial"] = True
            result.metadata["operator_unreached_office_count"] = len(
                self._operator_unreached_offices
            )

        logger.info(
            "insights_export_completed",
            total=result.total,
            succeeded=result.succeeded,
            failed=result.failed,
            skipped=result.skipped,
            total_tables_succeeded=result.metadata.get("total_tables_succeeded", 0),
            total_tables_failed=result.metadata.get("total_tables_failed", 0),
            operator_run_partial=result.metadata.get("operator_run_partial", False),
            duration_seconds=round(result.duration_seconds, 2),
        )

        return result

    def _build_result_metadata(
        self,
        outcomes: list[BridgeOutcome],
    ) -> dict[str, Any]:
        """Build insights-specific metadata: table counts + preview paths.

        Also emits cache summary log (per AT3-001).
        """
        # Cache summary log (moved from execute_async)
        logger.info(
            "insights_business_cache_summary",
            extra={
                "total_offers": len(outcomes),
                "unique_businesses": len(self._business_cache),
                "cache_hits": self._cache_hits,
                "api_calls_saved": self._cache_hits,
            },
        )

        # Per-offer table counts
        per_offer_table_counts: dict[str, dict[str, int | None]] = {}
        total_tables_succeeded = 0
        total_tables_failed = 0
        for o in outcomes:
            if isinstance(o, _OfferOutcome) and o.tables_succeeded is not None:
                per_offer_table_counts[o.gid] = {
                    "tables_succeeded": o.tables_succeeded,
                    "tables_failed": o.tables_failed,
                }
                total_tables_succeeded += o.tables_succeeded
                total_tables_failed += o.tables_failed or 0

        metadata: dict[str, Any] = {
            "per_offer_table_counts": per_offer_table_counts,
            "total_tables_succeeded": total_tables_succeeded,
            "total_tables_failed": total_tables_failed,
        }

        # Dry-run preview paths
        dry_run_outcomes = [
            o for o in outcomes if isinstance(o, _OfferOutcome) and o.preview_path is not None
        ]
        if dry_run_outcomes:
            metadata["dry_run"] = True
            metadata["preview_paths"] = {o.gid: o.preview_path for o in dry_run_outcomes}

        return metadata

    # --- Private Methods ---

    async def _enumerate_offers(self) -> list[dict[str, Any]]:
        """List ACTIVE (non-completed) Offer tasks using section-targeted fetch.

        Delegates to the shared ``enumerate_active_offers`` helper so the
        insights export and the grain-bridge leads consumer share ONE
        active-set definition (no second classifier). Behavior (section-targeted
        primary + project-level fallback) is unchanged.
        """
        return await enumerate_active_offers(
            self._asana_client,
            logger=logger,
            workflow_id=self.workflow_id,
        )

    async def _process_offer(
        self,
        offer_gid: str,
        offer_name: str | None,
        attachment_pattern: str,
        row_limits: dict[str, int],
        dry_run: bool = False,
    ) -> _OfferOutcome:
        """Process a single Offer: resolve, fetch tables, compose, upload.

        Args:
            offer_gid: Offer task GID.
            offer_name: Offer task name (for logging / filename).
            attachment_pattern: Glob for old attachment cleanup.
            row_limits: Per-table row limits.
            dry_run: If True, skip upload and delete operations.

        Returns:
            _OfferOutcome with status and per-table tracking.
        """
        offer_start = time.monotonic()

        try:
            # Step A: Resolve office_phone + vertical via parent Business
            resolution = await self._resolve_offer(offer_gid)
            if resolution is None:
                logger.warning(
                    "insights_export_offer_skipped",
                    offer_gid=offer_gid,
                    offer_name=offer_name,
                    reason="no_resolution",
                )
                return _OfferOutcome(
                    gid=offer_gid,
                    status="skipped",
                    reason="no_resolution",
                )

            office_phone, vertical, business_name = resolution
            masked_phone = mask_phone_number(office_phone)

            # WS-2 RISK-4: if the operator batch could NOT serve this office this run
            # (the run budget / throttle stopped the bisection before reaching it --
            # a NON-definitive miss), SKIP the publish ENTIRELY: do NOT build/upload
            # an empty deck and do NOT delete the prior attachment. This mirrors the
            # whole-plane INERT no-op guard at per-office granularity so a budget-
            # capped partial run leaves this office's last-good deck intact. Distinct
            # from a served-empty or drift office (definitive answer -> publishes
            # empty per the normal path).
            if office_phone in self._operator_unreached_offices:
                logger.warning(
                    "insights_export_offer_skipped_budget_unreached",
                    offer_gid=offer_gid,
                    office_phone=masked_phone,
                )
                return _OfferOutcome(
                    gid=offer_gid,
                    status="skipped",
                    reason="operator_budget_unreached",
                )

            logger.info(
                "insights_export_offer_started",
                offer_gid=offer_gid,
                office_phone=masked_phone,
                vertical=vertical,
            )

            # Step B: Fetch all 12 tables concurrently
            table_results = await self._fetch_all_tables(
                office_phone=office_phone,
                vertical=vertical,
                row_limits=row_limits,
                offer_gid=offer_gid,
            )

            tables_succeeded = sum(1 for t in table_results.values() if t.success)
            tables_failed = TOTAL_TABLE_COUNT - tables_succeeded

            # Step C: Check for total failure
            if tables_succeeded == 0:
                logger.error(
                    "insights_export_offer_failed",
                    offer_gid=offer_gid,
                    error_count=tables_failed,
                )
                return _OfferOutcome(
                    gid=offer_gid,
                    status="failed",
                    tables_succeeded=0,
                    tables_failed=tables_failed,
                    error=WorkflowItemError(
                        item_id=offer_gid,
                        error_type="all_tables_failed",
                        message=f"All {TOTAL_TABLE_COUNT} tables failed",
                        recoverable=True,
                    ),
                )

            # Step D: Compose HTML report
            report_data = InsightsReportData(
                business_name=business_name or offer_name or "Unknown",
                office_phone=OfficePhone(office_phone),
                vertical=vertical,
                table_results=table_results,
                started_at=offer_start,
                version=WORKFLOW_VERSION,
                row_limits=row_limits,
                offer_gid=offer_gid,
            )
            report_content = compose_report(report_data)

            # Step E: Upload-first attachment replacement
            sanitized_name = _sanitize_business_name(business_name or offer_name or "Unknown")
            date_str = datetime.now(UTC).strftime("%Y%m%d")
            filename = f"insights_export_{sanitized_name}_{date_str}.html"
            preview_path: str | None = None

            report_bytes = report_content.encode("utf-8")

            if not dry_run:
                await self._attachments_client.upload_async(
                    parent=offer_gid,
                    file=report_bytes,
                    name=filename,
                    content_type="text/html",
                )

                logger.info(
                    "insights_export_upload_succeeded",
                    offer_gid=offer_gid,
                    filename=filename,
                    size_bytes=len(report_bytes),
                )

                # Step F: Delete old matching attachments
                await self._delete_old_attachments(
                    offer_gid, attachment_pattern, exclude_name=filename
                )
            else:
                # Write full HTML to local preview file for validation
                preview_dir = self._preview_dir
                preview_dir.mkdir(parents=True, exist_ok=True)
                local_path = preview_dir / filename
                local_path.write_text(report_content, encoding="utf-8")
                preview_path = str(local_path)

                logger.info(
                    "insights_export_dry_run_preview",
                    offer_gid=offer_gid,
                    preview_path=str(preview_path),
                    size_bytes=len(report_bytes),
                )

            elapsed_ms = (time.monotonic() - offer_start) * 1000
            logger.info(
                "insights_export_offer_succeeded",
                offer_gid=offer_gid,
                tables_succeeded=tables_succeeded,
                tables_failed=tables_failed,
                duration_ms=elapsed_ms,
                dry_run=dry_run,
            )

            return _OfferOutcome(
                gid=offer_gid,
                status="succeeded",
                tables_succeeded=tables_succeeded,
                tables_failed=tables_failed,
                report_preview=report_content if dry_run else None,
                preview_path=str(preview_path) if dry_run else None,
            )

        except (
            Exception  # noqa: BLE001
        ) as exc:  # BROAD-CATCH: boundary -- offer processing failure returns failed outcome
            logger.error(
                "insights_export_offer_error",
                offer_gid=offer_gid,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return _OfferOutcome(
                gid=offer_gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=offer_gid,
                    error_type="unexpected",
                    message=str(exc),
                    recoverable=True,
                ),
            )

    async def _resolve_offer(
        self,
        offer_gid: str,
    ) -> tuple[str, str, str | None] | None:
        """Resolve Offer -> parent Business -> office_phone + vertical.

        Traverses the full entity hierarchy via ResolutionContext:
            Offer -> OfferHolder -> Unit -> UnitHolder -> Business

        Note: Offer.parent is OfferHolder (NOT Business). The resolution
        chain handles the multi-level traversal correctly.

        Cache is keyed by business_gid (per F-02) so sibling offers
        sharing the same parent Business hit the cache and avoid
        redundant API calls.

        Args:
            offer_gid: Offer task GID.

        Returns:
            Tuple of (office_phone, vertical, business_name) or None.
        """
        # Check if this offer has already been resolved to a business_gid
        if offer_gid in self._offer_to_business:
            biz_gid = self._offer_to_business[offer_gid]
            self._cache_hits += 1
            logger.debug(
                "insights_business_cache_hit",
                offer_gid=offer_gid,
                business_gid=biz_gid,
            )
            if biz_gid is None:
                return None
            return self._business_cache.get(biz_gid)

        # Fetch offer task with parent reference for traversal
        offer_task = await self._asana_client.tasks.get_async(
            offer_gid,
            opt_fields=["parent", "parent.gid"],
        )
        if not offer_task.parent or not offer_task.parent.gid:
            self._offer_to_business[offer_gid] = None
            return None

        # Use trigger_entity so HierarchyTraversalStrategy walks the
        # full parent chain (Offer -> OfferHolder -> Unit -> UnitHolder -> Business).
        # Do NOT use business_gid= fast-path: Offer.parent is OfferHolder, not Business.
        from autom8_asana.models.business.base import BusinessEntity

        offer_entity = BusinessEntity(gid=offer_gid)
        offer_entity.parent = offer_task.parent

        async with ResolutionContext(
            self._asana_client,
            trigger_entity=offer_entity,
        ) as ctx:
            business = await ctx.business_async()
            business_gid = business.gid
            office_phone = business.office_phone
            vertical = business.vertical
            business_name = business.name

        if not office_phone or not vertical:
            result = None
        else:
            result = (office_phone, vertical, business_name)

        # Check if another offer already resolved this business
        if business_gid in self._business_cache:
            self._cache_hits += 1
            logger.debug(
                "insights_business_cache_hit_sibling",
                offer_gid=offer_gid,
                business_gid=business_gid,
            )

        # Populate caches: business_gid -> result, offer_gid -> business_gid
        self._business_cache[business_gid] = result
        self._offer_to_business[offer_gid] = business_gid

        return result

    async def _prefetch_operator_tables(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> None:
        """Mint once and fetch the clean tables batch-over-O (GAP-1 PR-A).

        Resolves the intended owned office set ``O`` (warming the per-offer
        resolution cache), then for EACH operator-plane table issues ONE
        ``get_operator_insights_batch_async(phones=O)`` call (reusing one minted
        token). The per-office results are cached in ``self._operator_batch`` for
        the per-offer pass to read.

        Fails GRACEFULLY closed:

        - A whole-plane mint REFUSAL (``OperatorMintRefusedError`` -- the INERT
          empty-allowlist 403, or no ambient AWS credentials) is logged WARNING
          once and sets ``self._operator_plane_refused``. execute_async then makes
          the run a TRUE no-op: it skips the publish step entirely (no empty deck
          uploaded, NO prior attachment deleted -- prior decks stay intact).
        - A per-insight route denial (``OperatorAccessDeniedError``) leaves only
          THAT table empty and continues; the offer still publishes (clean decks
          render empty for the denied table).

        NEVER falls back to the SA fleet-read (G-NO-FALLBACK); the cross-tenant
        counter simply stays RED.
        """
        self._operator_batch = {}
        self._operator_plane_refused = False
        self._operator_unreached_offices = set()

        office_set = await self._resolve_owned_office_set(entities, params)
        if not office_set:
            logger.info("insights_export_no_owned_offices", total_offers=len(entities))
            return

        phones = sorted(office_set)
        operator_specs = [
            s for s in TABLE_SPECS if s.dispatch_type is DispatchType.OPERATOR_INSIGHTS
        ]

        # ONE run-scoped budget governor threaded across ALL operator insights AND
        # the bisection recursion, so the AGGREGATE wire count is capped by a SINGLE
        # shared counter (B_run, default 9 < 10) -- per-RUN, not per-insight. This
        # holds INV-1 (the 10/min DoS guard): the export self-limits strictly below
        # it, so the guard stays armed and fires at the 11th for anything else (TDD
        # §5.3 / ADR-003 / RISK-5).
        pacer = self._data_client.new_operator_pacer()

        fetched = 0
        for spec in operator_specs:
            # operator specs always carry insight_name (asserted in tables.py)
            insight_name = spec.insight_name
            assert insight_name is not None  # noqa: S101 -- spec invariant
            try:
                per_office = await self._data_client.get_operator_insights_batch_async(
                    insight_name=insight_name,
                    phones=phones,
                    period=spec.period,
                    pacer=pacer,
                )
            except OperatorMintRefusedError as exc:
                # The mint is dark (INERT empty-allowlist 403, or no credentials):
                # the WHOLE operator plane is unreachable. Flag the run as INERT so
                # execute_async skips the publish step ENTIRELY (TRUE no-op: no empty
                # deck uploaded, NO prior attachment deleted -- prior decks intact).
                # Graceful, no crash, NO SA fleet-read fallback. The counter stays
                # RED with zero regression.
                self._operator_batch = {}
                self._operator_plane_refused = True
                logger.warning(
                    "insights_export_operator_plane_unavailable",
                    reason=getattr(exc, "reason", None),
                    error=str(exc),
                )
                return
            except OperatorAccessDeniedError as exc:
                # THIS insight is denied (e.g. not yet on the data-plane allowlist,
                # or all its offices drifted out of O): leave this table empty and
                # continue with the others. NO SA fleet-read fallback.
                logger.warning(
                    "insights_export_operator_table_denied",
                    table=spec.table_name,
                    reason=getattr(exc, "reason", None),
                    error=str(exc),
                )
                continue
            except (
                Exception  # noqa: BLE001
            ) as exc:  # BROAD-CATCH: an unexpected operator error must not crash the daily run
                logger.warning(
                    "insights_export_operator_table_error",
                    table=spec.table_name,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                continue
            self._operator_batch[spec.table_name] = per_office
            fetched += 1

        # Offices the run budget / throttle could not reach this run (NON-definitive
        # -- the bisection stopped before serving them). The per-offer pass PROTECTS
        # their prior decks (skips publish), distinct from drift/denied offices which
        # got a definitive answer and publish empty (RISK-4 / TDD §5.3).
        self._operator_unreached_offices = set(pacer.unreached)

        logger.info(
            "insights_export_operator_batch_fetched",
            tables=fetched,
            requested=len(operator_specs),
            offices=len(phones),
            wire_calls=pacer.spent,
            partial=pacer.partial,
            unreached_offices=len(self._operator_unreached_offices),
        )

    async def _resolve_owned_office_set(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> set[str]:
        """Resolve every offer to its office_phone; return the deduped owned set.

        This is the ``phones=O`` the batch-over-O calls send (asana's INTENDED
        set; the data plane intersects it with the server-resolved owned set,
        all-or-nothing). It warms ``self._business_cache`` / ``self._offer_to_business``
        so the subsequent per-offer pass hits the cache (no double Asana fetch). A
        single offer's resolution failure is isolated (it just drops out of O).
        """
        max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _resolve_one(entity: dict[str, Any]) -> tuple[str, str, str | None] | None:
            async with semaphore:
                try:
                    return await self._resolve_offer(entity["gid"])
                except (
                    Exception  # noqa: BLE001
                ):  # BROAD-CATCH: one offer's resolution failure must not abort the prefetch
                    return None

        resolutions = await asyncio.gather(*(_resolve_one(e) for e in entities))
        return {r[0] for r in resolutions if r is not None and r[0]}

    async def _fetch_all_tables(
        self,
        office_phone: str,
        vertical: str,
        row_limits: dict[str, int],
        offer_gid: str,
    ) -> dict[str, TableResult]:
        """Fetch all tables concurrently using TABLE_SPECS.

        Per FR-04: Iterates TABLE_SPECS and dispatches via asyncio.gather().
        Signature unchanged (per NFR-05: concurrent fetch preserved).
        """
        results = await asyncio.gather(
            *(
                self._fetch_table(
                    spec=spec,
                    offer_gid=offer_gid,
                    office_phone=office_phone,
                    vertical=vertical,
                    row_limits=row_limits,
                )
                for spec in TABLE_SPECS
            )
        )
        return {r.table_name: r for r in results}

    async def _fetch_table(
        self,
        spec: TableSpec,
        offer_gid: str,
        office_phone: str,
        vertical: str,
        row_limits: dict[str, int],
    ) -> TableResult:
        """Resolve one table for one office from the pre-fetched operator batch.

        GAP-1 PR-A: the cross-tenant export serves ONLY the operator-plane clean
        tables. This reads the per-office rows from ``self._operator_batch`` (filled
        once in ``_prefetch_operator_tables`` via batch-over-O) -- it does NOT make a
        per-office wire call (that would blow the 10/min route budget) and it NEVER
        calls the SA fleet-read methods (get_appointments/leads/reconciliation/
        get_insights) on the cross-tenant path (M3 / G-NO-FALLBACK). OQ-4a: the
        asana-side activity filter is applied here for the tables that need it (the
        operator batch route does not apply the factory-frame activity filter).
        """
        fetch_start = time.monotonic()

        try:
            if spec.dispatch_type is not DispatchType.OPERATOR_INSIGHTS:
                # Defensive: the cross-tenant export carries ONLY operator specs.
                raise ValueError(
                    f"unsupported dispatch_type {spec.dispatch_type!r} on the "
                    f"cross-tenant export (only OPERATOR_INSIGHTS is served)"
                )

            rows = self._operator_batch.get(spec.table_name, {}).get(office_phone, [])

            # OQ-4a: asana-side activity filter (keep spend>0 OR leads>0). Applied
            # only to the tables that need it (ASSET TABLE, AD QUESTIONS); it only
            # removes rows, preserving de-identification.
            data = _apply_activity_filter(rows) if spec.activity_filter else list(rows)

            elapsed_ms = (time.monotonic() - fetch_start) * 1000

            logger.info(
                "insights_export_table_fetched",
                offer_gid=offer_gid,
                table_name=spec.table_name,
                row_count=len(data),
                duration_ms=elapsed_ms,
            )

            return TableResult(
                table_name=spec.table_name,
                success=True,
                data=data,
                row_count=len(data),
            )

        except (
            Exception  # noqa: BLE001
        ) as exc:  # BROAD-CATCH: boundary -- table fetch failure returns failed TableResult
            elapsed_ms = (time.monotonic() - fetch_start) * 1000
            error_type = type(exc).__name__

            logger.warning(
                "insights_export_table_failed",
                offer_gid=offer_gid,
                table_name=spec.table_name,
                error_type=error_type,
                error_message=str(exc),
                duration_ms=elapsed_ms,
            )

            return TableResult(
                table_name=spec.table_name,
                success=False,
                error_type=error_type,
                error_message=str(exc),
            )


# --- Helper Functions ---


def _apply_activity_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OQ-4a: keep rows with ``spend > 0 OR leads > 0`` (drop zero-activity rows).

    Mirrors the data plane's factory-frame activity filter (autom8y-data
    ``_insights_helpers.apply_activity_filter``), which the operator batch route
    does NOT apply. Both ``spend`` and ``leads`` are present on the rewired
    asset/question rows; a missing/null metric is treated as 0. This only REMOVES
    rows, so it preserves de-identification.
    """

    def _is_active(row: dict[str, Any]) -> bool:
        spend = row.get("spend") or 0
        leads = row.get("leads") or 0
        return spend > 0 or leads > 0

    return [row for row in rows if _is_active(row)]


def _sanitize_business_name(name: str) -> str:
    """Sanitize business name for filename use.

    Per PRD FR-W01.7: Spaces -> underscores, non-alphanumeric stripped.

    Args:
        name: Raw business name.

    Returns:
        Filename-safe string.
    """
    sanitized = name.replace(" ", "_")
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", sanitized)
    return sanitized or "unknown"


# --- Internal Data Structures ---


@_dataclass
class _OfferOutcome(BridgeOutcome):
    """Internal per-offer processing result.

    Extends BridgeOutcome with insights-specific fields for table
    tracking and dry-run preview.
    """

    # Inherited from BridgeOutcome: gid, status, reason, error
    tables_succeeded: int | None = None
    tables_failed: int | None = None
    report_preview: str | None = None
    preview_path: str | None = None
