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

from autom8y_log import get_logger

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
from autom8_asana.models.business.activity import (
    OFFER_CLASSIFIER,
    AccountActivity,
    extract_section_name,
)
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
# APPOINTMENTS/LEADS: upstream API supports up to 500; self-limited to 100
# for report readability (increase requires UX review).
# ASSET TABLE: capped at 150, sorted by spend desc (per WS-G spec).
DEFAULT_ROW_LIMITS: dict[str, int] = {
    "APPOINTMENTS": 100,
    "LEADS": 100,
    "ASSET TABLE": 150,
}

# Table names in section order -- derived from TABLE_SPECS (per TDD-SPRINT-C).
TABLE_NAMES = [s.table_name for s in TABLE_SPECS]

TOTAL_TABLE_COUNT = len(TABLE_NAMES)  # 12


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
            attachment_pattern=params.get(
                "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
            ),
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

        result = await super().execute_async(entities, params)

        logger.info(
            "insights_export_completed",
            total=result.total,
            succeeded=result.succeeded,
            failed=result.failed,
            skipped=result.skipped,
            total_tables_succeeded=result.metadata.get("total_tables_succeeded", 0),
            total_tables_failed=result.metadata.get("total_tables_failed", 0),
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
            o
            for o in outcomes
            if isinstance(o, _OfferOutcome) and o.preview_path is not None
        ]
        if dry_run_outcomes:
            metadata["dry_run"] = True
            metadata["preview_paths"] = {
                o.gid: o.preview_path for o in dry_run_outcomes
            }

        return metadata

    # --- Private Methods ---

    async def _enumerate_offers(self) -> list[dict[str, Any]]:
        """List ACTIVE (non-completed) Offer tasks using section-targeted fetch.

        Primary path: resolve ACTIVE section GIDs, fetch tasks per section
        in parallel (Semaphore(5)), merge and deduplicate by GID.

        Fallback: project-level fetch with client-side classification (current behavior).
        """
        from autom8_asana.automation.workflows.section_resolution import (
            resolve_section_gids,
        )

        active_section_names = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)

        # Resolve section GIDs
        try:
            resolved = await resolve_section_gids(
                self._asana_client.sections,
                OFFER_PROJECT_GID,
                active_section_names,
            )
        except Exception:  # BROAD-CATCH: boundary -- section resolution failure falls back to full enumeration
            logger.warning(
                "section_resolution_failed_fallback",
                workflow_id=self.workflow_id,
                project_gid=OFFER_PROJECT_GID,
            )
            return await self._enumerate_offers_fallback()

        if not resolved:
            logger.warning(
                "section_resolution_empty_fallback",
                workflow_id=self.workflow_id,
                project_gid=OFFER_PROJECT_GID,
            )
            return await self._enumerate_offers_fallback()

        # Parallel section fetch with bounded concurrency
        semaphore = asyncio.Semaphore(5)

        async def fetch_section(section_gid: str) -> list[Any]:
            async with semaphore:
                result: list[Any] = await self._asana_client.tasks.list_async(
                    section=section_gid,
                    opt_fields=["name", "completed", "parent", "parent.name"],
                    completed_since="now",
                ).collect()
                return result

        results = await asyncio.gather(
            *[fetch_section(gid) for gid in resolved.values()],
            return_exceptions=True,
        )

        # If any section fetch failed, fall back entirely
        if any(isinstance(r, Exception) for r in results):
            logger.warning(
                "section_fetch_partial_failure_fallback",
                workflow_id=self.workflow_id,
                project_gid=OFFER_PROJECT_GID,
                failed_count=sum(1 for r in results if isinstance(r, Exception)),
            )
            return await self._enumerate_offers_fallback()

        # Flatten, dedup by GID, build offer dicts
        seen_gids: set[str] = set()
        offers: list[dict[str, Any]] = []
        for section_tasks in results:
            assert isinstance(section_tasks, list)  # guarded by early-exit above
            for t in section_tasks:
                if t.completed or t.gid in seen_gids:
                    continue
                seen_gids.add(t.gid)
                offers.append(
                    {
                        "gid": t.gid,
                        "name": t.name,
                    }
                )

        logger.info(
            "insights_section_targeted_enumeration",
            sections_targeted=len(resolved),
            tasks_enumerated=len(offers),
        )

        return offers

    async def _enumerate_offers_fallback(self) -> list[dict[str, Any]]:
        """Fallback: project-level fetch with client-side ACTIVE classification.

        This is the pre-migration enumeration logic, preserved verbatim for
        resilience when section resolution or section-level fetch fails.
        """
        page_iterator = self._asana_client.tasks.list_async(
            project=OFFER_PROJECT_GID,
            opt_fields=[
                "name",
                "completed",
                "parent",
                "parent.name",
                "memberships.section.name",
            ],
            completed_since="now",
        )
        tasks = await page_iterator.collect()

        # Filter to non-completed tasks first
        non_completed = [t for t in tasks if not t.completed]
        total_before = len(non_completed)

        # Filter to only ACTIVE offers by section classification
        active_offers: list[dict[str, Any]] = []
        for t in non_completed:
            section_name = extract_section_name(t, OFFER_PROJECT_GID)
            if section_name is None:
                continue
            activity = OFFER_CLASSIFIER.classify(section_name)
            if activity != AccountActivity.ACTIVE:
                continue
            active_offers.append(
                {
                    "gid": t.gid,
                    "name": t.name,
                }
            )

        filtered_count = total_before - len(active_offers)
        if filtered_count > 0:
            logger.info(
                "insights_export_offers_filtered_by_activity",
                total_before=total_before,
                active_count=len(active_offers),
                filtered_count=filtered_count,
            )

        return active_offers

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
                office_phone=office_phone,
                vertical=vertical,
                table_results=table_results,
                started_at=offer_start,
                version=WORKFLOW_VERSION,
                row_limits=row_limits,
                offer_gid=offer_gid,
            )
            report_content = compose_report(report_data)

            # Step E: Upload-first attachment replacement
            sanitized_name = _sanitize_business_name(
                business_name or offer_name or "Unknown"
            )
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
                preview_dir = pathlib.Path(".wip")
                preview_dir.mkdir(exist_ok=True)
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

        except Exception as exc:  # BROAD-CATCH: boundary -- offer processing failure returns failed outcome
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
        """Fetch a single table with error isolation.

        Per FR-05: Uses match statement on spec.dispatch_type (D-04).
        Reconciliation phone filtering stays in the dispatcher (D-02).
        """
        fetch_start = time.monotonic()

        try:
            # Resolve effective limit: runtime override > spec default > None
            effective_limit = row_limits.get(spec.table_name) or spec.default_limit

            filtered_data: list[dict[str, Any]] | None = None

            match spec.dispatch_type:
                case DispatchType.APPOINTMENTS:
                    response = await self._data_client.get_appointments_async(
                        office_phone,
                        days=spec.days or 90,
                        limit=effective_limit or 100,
                    )
                case DispatchType.LEADS:
                    response = await self._data_client.get_leads_async(
                        office_phone,
                        days=spec.days or 30,
                        exclude_appointments=spec.exclude_appointments,
                        limit=effective_limit or 100,
                    )
                case DispatchType.RECONCILIATION:
                    response = await self._data_client.get_reconciliation_async(
                        office_phone,
                        vertical,
                        period=spec.period,
                        window_days=spec.window_days,
                    )
                    # Defensive phone filtering stays in dispatcher (per D-02).
                    # Uses local variable to avoid mutating response (per F-08).
                    if hasattr(response, "data") and response.data:
                        phones_in_data = {
                            r.get("office_phone")
                            for r in response.data
                            if r.get("office_phone") is not None
                        }
                        if len(phones_in_data) > 1:
                            pre_filter = len(response.data)
                            filtered_data = [
                                r
                                for r in response.data
                                if r.get("office_phone") == office_phone
                            ]
                            logger.info(
                                "insights_export_recon_filtered",
                                offer_gid=offer_gid,
                                table_name=spec.table_name,
                                pre_filter=pre_filter,
                                post_filter=len(filtered_data),
                                unique_phones=len(phones_in_data),
                            )
                case DispatchType.INSIGHTS:
                    response = await self._data_client.get_insights_async(
                        factory=spec.factory,
                        office_phone=office_phone,
                        vertical=vertical,
                        period=spec.period or "lifetime",
                        include_unused=spec.include_unused,
                    )

            elapsed_ms = (time.monotonic() - fetch_start) * 1000
            # Use filtered_data if reconciliation phone filtering was applied
            if (
                spec.dispatch_type == DispatchType.RECONCILIATION
                and filtered_data is not None
            ):
                data = filtered_data
            else:
                data = response.data if hasattr(response, "data") else []

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

        except Exception as exc:  # BROAD-CATCH: boundary -- table fetch failure returns failed TableResult
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
