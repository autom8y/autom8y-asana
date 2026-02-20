"""Insights export workflow -- daily HTML report for Offer tasks.

Per TDD-EXPORT-001: Second WorkflowAction implementation.
Enumerates active Offers, resolves each to office_phone + vertical,
fetches 10 tables from autom8_data, composes HTML report,
and uploads as attachment to each Offer task.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import dataclass as _dataclass
from datetime import UTC, datetime
from typing import Any

from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.insights_formatter import (
    InsightsReportData,
    TableResult,
    compose_report,
)
from autom8_asana.automation.workflows.mixins import AttachmentReplacementMixin
from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.data.client import DataServiceClient, mask_phone_number
from autom8_asana.core.scope import EntityScope
from autom8_asana.models.business.activity import (
    OFFER_CLASSIFIER,
    AccountActivity,
    extract_section_name,
)
from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)

# Feature flag environment variable
EXPORT_ENABLED_ENV_VAR = "AUTOM8_EXPORT_ENABLED"

# Offer project GID (canonical source: Offer.PRIMARY_PROJECT_GID)
OFFER_PROJECT_GID = "1143843662099250"

# Default concurrency for parallel offer processing
DEFAULT_MAX_CONCURRENCY = 5

# Default attachment patterns for cleanup
# Primary pattern matches current HTML format; legacy pattern cleans up
# old .md files from pre-migration deployments (transitional, one cycle).
DEFAULT_ATTACHMENT_PATTERN = "insights_export_*.html"
LEGACY_ATTACHMENT_PATTERN = "insights_export_*.md"

# Workflow version identifier (for footer)
WORKFLOW_VERSION = "insights-export-v1.0"

# Default row limits per table type
DEFAULT_ROW_LIMITS: dict[str, int] = {
    "APPOINTMENTS": 100,
    "LEADS": 100,
}

# Table names in section order (per PRD FR-W01.6)
TABLE_NAMES: list[str] = [
    "SUMMARY",
    "APPOINTMENTS",
    "LEADS",
    "BY QUARTER",
    "BY MONTH",
    "BY WEEK",
    "AD QUESTIONS",
    "ASSET TABLE",
    "OFFER TABLE",
    "UNUSED ASSETS",
]

TOTAL_TABLE_COUNT = len(TABLE_NAMES)  # 10


class InsightsExportWorkflow(AttachmentReplacementMixin, WorkflowAction):
    """Daily insights export markdown report for Offer tasks.

    Per PRD-EXPORT-001: Second WorkflowAction implementation.

    Lifecycle:
    1. Check feature flag (AUTOM8_EXPORT_ENABLED)
    2. Enumerate active Offer tasks in BusinessOffers project
    3. For each Offer (with concurrency limit):
       a. Resolve parent Business -> office_phone + vertical
       b. Fetch 10 tables concurrently from DataServiceClient
       c. Compose markdown report via insights_formatter
       d. Upload new .html attachment (upload-first)
       e. Delete old matching .html/.md attachments
    4. Return WorkflowResult with per-item and per-table tracking

    Args:
        asana_client: AsanaClient for Asana API operations.
        data_client: DataServiceClient for autom8_data insights fetch.
        attachments_client: AttachmentsClient for upload/delete operations.
    """

    def __init__(
        self,
        asana_client: Any,  # AsanaClient (TYPE_CHECKING avoids circular)
        data_client: DataServiceClient,
        attachments_client: AttachmentsClient,
    ) -> None:
        self._asana_client = asana_client
        self._data_client = data_client
        self._attachments_client = attachments_client
        # Dedup cache: offer_gid -> (office_phone, vertical, business_name)
        # Per AT3-001: eliminates redundant Business fetches across offers.
        self._business_cache: dict[str, tuple[str, str, str | None] | None] = {}

    @property
    def workflow_id(self) -> str:  # type: ignore[override]  # read-only property overrides base attribute
        return "insights-export"

    async def validate_async(self) -> list[str]:
        """Pre-flight validation.

        Checks:
        1. Feature flag is enabled (AUTOM8_EXPORT_ENABLED).
        2. DataServiceClient circuit breaker is not open.

        Returns:
            List of validation error strings (empty = ready).
        """
        errors: list[str] = []

        # Check feature flag
        env_value = os.environ.get(EXPORT_ENABLED_ENV_VAR, "").lower()
        if env_value in {"false", "0", "no"}:
            errors.append(f"Workflow disabled via {EXPORT_ENABLED_ENV_VAR}={env_value}")
            return errors  # Short-circuit

        # Check DataServiceClient circuit breaker
        try:
            from autom8y_http import CircuitBreakerOpenError as SdkCBOpen

            await self._data_client._circuit_breaker.check()
        except SdkCBOpen:
            errors.append(
                "DataServiceClient circuit breaker is open. "
                "autom8_data may be degraded."
            )
        except (ConnectionError, TimeoutError, OSError):
            pass  # Non-circuit-breaker errors are not pre-flight failures

        return errors

    async def enumerate_async(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Enumerate Offer entities based on scope.

        Per TDD-ENTITY-SCOPE-001 Section 2.4.1:
        When scope.has_entity_ids: return synthetic offer dicts for each GID.
        When scope is empty: perform full section-targeted enumeration.

        Args:
            scope: EntityScope controlling targeting, filtering, and limits.

        Returns:
            List of offer dicts with {gid, name} shape.
        """
        if scope.has_entity_ids:
            offers = [{"gid": gid, "name": None} for gid in scope.entity_ids]
            logger.info(
                "insights_export_targeted",
                entity_ids=scope.entity_ids,
                dry_run=scope.dry_run,
            )
            return offers

        # Full enumeration (existing _enumerate_offers logic)
        offers = await self._enumerate_offers()

        # Apply limit if provided
        if scope.limit is not None and len(offers) > scope.limit:
            offers = offers[: scope.limit]

        return offers

    async def execute_async(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the insights export for the given entities.

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
        started_at = datetime.now(UTC)

        max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        attachment_pattern = params.get(
            "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
        )
        row_limits = params.get("row_limits", DEFAULT_ROW_LIMITS)
        dry_run = params.get("dry_run", False)

        offers = entities  # Named alias for clarity

        logger.info(
            "insights_export_started",
            total_offers=len(offers),
            max_concurrency=max_concurrency,
            dry_run=dry_run,
        )

        # Process each offer with concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[_OfferOutcome] = []

        async def process_one(
            offer_gid: str,
            offer_name: str | None,
        ) -> None:
            async with semaphore:
                outcome = await self._process_offer(
                    offer_gid=offer_gid,
                    offer_name=offer_name,
                    attachment_pattern=attachment_pattern,
                    row_limits=row_limits,
                    dry_run=dry_run,
                )
                results.append(outcome)

        await asyncio.gather(*[process_one(o["gid"], o.get("name")) for o in offers])

        # Log Business cache summary for observability (per AT3-001)
        logger.info(
            "insights_business_cache_summary",
            extra={
                "total_offers": len(offers),
                "unique_businesses": len(self._business_cache),
                "cache_hits": len(offers) - len(self._business_cache),
                "api_calls_saved": len(offers) - len(self._business_cache),
            },
        )

        # Step 3: Aggregate results
        succeeded = sum(1 for r in results if r.status == "succeeded")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        errors = [r.error for r in results if r.error is not None]

        # Per-offer table counts
        per_offer_table_counts: dict[str, dict[str, int | None]] = {}
        total_tables_succeeded = 0
        total_tables_failed = 0
        for r in results:
            if r.tables_succeeded is not None:
                per_offer_table_counts[r.offer_gid] = {
                    "tables_succeeded": r.tables_succeeded,
                    "tables_failed": r.tables_failed,
                }
                total_tables_succeeded += r.tables_succeeded
                total_tables_failed += r.tables_failed or 0

        completed_at = datetime.now(UTC)

        metadata: dict[str, Any] = {
            "per_offer_table_counts": per_offer_table_counts,
            "total_tables_succeeded": total_tables_succeeded,
            "total_tables_failed": total_tables_failed,
        }
        if dry_run:
            metadata["dry_run"] = True
            previews = {
                r.offer_gid: r.report_preview
                for r in results
                if r.report_preview is not None
            }
            if previews:
                metadata["report_preview"] = previews

        workflow_result = WorkflowResult(
            workflow_id=self.workflow_id,
            started_at=started_at,
            completed_at=completed_at,
            total=len(offers),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            metadata=metadata,
        )

        logger.info(
            "insights_export_completed",
            total=workflow_result.total,
            succeeded=workflow_result.succeeded,
            failed=workflow_result.failed,
            skipped=workflow_result.skipped,
            total_tables_succeeded=total_tables_succeeded,
            total_tables_failed=total_tables_failed,
            duration_seconds=round(workflow_result.duration_seconds, 2),
        )

        return workflow_result

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
                    offer_gid=offer_gid,
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

            # Step B: Fetch all 10 tables concurrently
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
                    offer_gid=offer_gid,
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
            )
            report_content = compose_report(report_data)

            # Step E: Upload-first attachment replacement
            sanitized_name = _sanitize_business_name(
                business_name or offer_name or "Unknown"
            )
            date_str = datetime.now(UTC).strftime("%Y%m%d")
            filename = f"insights_export_{sanitized_name}_{date_str}.html"

            if not dry_run:
                await self._attachments_client.upload_async(
                    parent=offer_gid,
                    file=report_content.encode("utf-8"),
                    name=filename,
                    content_type="text/html",
                )

                logger.info(
                    "insights_export_upload_succeeded",
                    offer_gid=offer_gid,
                    filename=filename,
                    size_bytes=len(report_content.encode("utf-8")),
                )

                # Step F: Delete old matching attachments (current + legacy patterns)
                await self._delete_old_attachments(
                    offer_gid, attachment_pattern, exclude_name=filename
                )
                # Transitional: clean up legacy .md files from pre-migration
                if attachment_pattern != LEGACY_ATTACHMENT_PATTERN:
                    await self._delete_old_attachments(
                        offer_gid, LEGACY_ATTACHMENT_PATTERN, exclude_name=filename
                    )
            else:
                logger.info(
                    "insights_export_dry_run_skip_write",
                    offer_gid=offer_gid,
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
                offer_gid=offer_gid,
                status="succeeded",
                tables_succeeded=tables_succeeded,
                tables_failed=tables_failed,
                report_preview=report_content[:2000] if dry_run else None,
            )

        except Exception as exc:  # BROAD-CATCH: boundary -- offer processing failure returns failed outcome
            logger.error(
                "insights_export_offer_error",
                offer_gid=offer_gid,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return _OfferOutcome(
                offer_gid=offer_gid,
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

        Args:
            offer_gid: Offer task GID.

        Returns:
            Tuple of (office_phone, vertical, business_name) or None.
        """
        # Check dedup cache first (per AT3-001: same pattern as
        # conversation_audit._activity_map). Keyed by offer_gid.
        if offer_gid in self._business_cache:
            logger.debug(
                "insights_business_cache_hit",
                offer_gid=offer_gid,
            )
            return self._business_cache[offer_gid]

        # Fetch offer task with parent reference for traversal
        offer_task = await self._asana_client.tasks.get_async(
            offer_gid,
            opt_fields=["parent", "parent.gid"],
        )
        if not offer_task.parent or not offer_task.parent.gid:
            self._business_cache[offer_gid] = None
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
            office_phone = business.office_phone
            vertical = business.vertical
            business_name = business.name

        if not office_phone or not vertical:
            result = None
        else:
            result = (office_phone, vertical, business_name)

        # Populate dedup cache keyed by offer_gid
        self._business_cache[offer_gid] = result

        return result

    async def _fetch_all_tables(
        self,
        office_phone: str,
        vertical: str,
        row_limits: dict[str, int],
        offer_gid: str,
    ) -> dict[str, TableResult]:
        """Fetch all 10 tables concurrently for a single offer.

        Per PRD FR-W01.5: All 10 calls dispatched concurrently via
        asyncio.gather(). ASSET TABLE and UNUSED ASSETS share a single
        API call (ADR-EXPORT-002).

        Args:
            office_phone: E.164 phone number.
            vertical: Business vertical string.
            row_limits: Per-table row limits.
            offer_gid: Offer GID for logging.

        Returns:
            Dict mapping table name to TableResult.
        """
        # Fetch the 9 independent API calls concurrently
        # Note: UNUSED ASSETS is derived from ASSET TABLE response
        # so we dispatch 9 API calls and derive the 10th
        results = await asyncio.gather(
            self._fetch_table(
                "SUMMARY",
                offer_gid,
                office_phone,
                vertical,
                factory="base",
                period="lifetime",
            ),
            self._fetch_table(
                "APPOINTMENTS",
                offer_gid,
                office_phone,
                vertical,
                method="appointments",
                days=90,
                limit=row_limits.get("APPOINTMENTS", 100),
            ),
            self._fetch_table(
                "LEADS",
                offer_gid,
                office_phone,
                vertical,
                method="leads",
                days=30,
                exclude_appointments=True,
                limit=row_limits.get("LEADS", 100),
            ),
            self._fetch_table(
                "BY QUARTER",
                offer_gid,
                office_phone,
                vertical,
                factory="base",
                period="quarter",
            ),
            self._fetch_table(
                "BY MONTH",
                offer_gid,
                office_phone,
                vertical,
                factory="base",
                period="month",
            ),
            self._fetch_table(
                "BY WEEK",
                offer_gid,
                office_phone,
                vertical,
                factory="base",
                period="week",
            ),
            self._fetch_table(
                "AD QUESTIONS",
                offer_gid,
                office_phone,
                vertical,
                factory="ad_questions",
                period="lifetime",
            ),
            self._fetch_table(
                "ASSET TABLE",
                offer_gid,
                office_phone,
                vertical,
                factory="assets",
                period="t30",
            ),
            self._fetch_table(
                "OFFER TABLE",
                offer_gid,
                office_phone,
                vertical,
                factory="business_offers",
                period="t30",
            ),
        )

        table_map: dict[str, TableResult] = {}
        for r in results:
            table_map[r.table_name] = r

        # Derive UNUSED ASSETS from ASSET TABLE response
        asset_result = table_map.get("ASSET TABLE")
        if asset_result is not None and asset_result.success:
            unused_rows = [
                row
                for row in (asset_result.data or [])
                if row.get("spend", -1) == 0 and row.get("imp", -1) == 0
            ]
            table_map["UNUSED ASSETS"] = TableResult(
                table_name="UNUSED ASSETS",
                success=True,
                data=unused_rows,
                row_count=len(unused_rows),
            )
        elif asset_result is not None and not asset_result.success:
            # If ASSET TABLE failed, UNUSED ASSETS also fails
            table_map["UNUSED ASSETS"] = TableResult(
                table_name="UNUSED ASSETS",
                success=False,
                error_type=asset_result.error_type,
                error_message=(
                    f"Derived from ASSET TABLE which failed: "
                    f"{asset_result.error_message}"
                ),
            )
        else:
            table_map["UNUSED ASSETS"] = TableResult(
                table_name="UNUSED ASSETS",
                success=False,
                error_type="missing_dependency",
                error_message="ASSET TABLE result not available",
            )

        return table_map

    async def _fetch_table(
        self,
        table_name: str,
        offer_gid: str,
        office_phone: str,
        vertical: str,
        *,
        factory: str | None = None,
        period: str | None = None,
        method: str | None = None,
        days: int | None = None,
        limit: int | None = None,
        exclude_appointments: bool = False,
    ) -> TableResult:
        """Fetch a single table with error isolation.

        Per PRD FR-W02.1: Each table fetch is individually wrapped
        in error handling. A failed table produces a TableResult
        with success=False.

        Args:
            table_name: Human-readable table name for the report.
            offer_gid: Offer GID for logging.
            office_phone: E.164 phone number.
            vertical: Business vertical.
            factory: Factory name for get_insights_async.
            period: For POST /insights calls.
            method: "appointments" or "leads" for detail endpoints.
            days: For appointment/lead detail endpoints.
            limit: Row limit for detail endpoints.
            exclude_appointments: For leads endpoint.

        Returns:
            TableResult with data or error information.
        """
        fetch_start = time.monotonic()

        try:
            if method == "appointments":
                response = await self._data_client.get_appointments_async(
                    office_phone, days=days or 90, limit=limit or 100
                )
            elif method == "leads":
                response = await self._data_client.get_leads_async(
                    office_phone,
                    days=days or 30,
                    exclude_appointments=exclude_appointments,
                    limit=limit or 100,
                )
            else:
                # Standard POST /insights call with factory parameter
                response = await self._data_client.get_insights_async(
                    factory=factory or "base",
                    office_phone=office_phone,
                    vertical=vertical,
                    period=period or "lifetime",
                )

            elapsed_ms = (time.monotonic() - fetch_start) * 1000
            data = response.data if hasattr(response, "data") else []

            logger.info(
                "insights_export_table_fetched",
                offer_gid=offer_gid,
                table_name=table_name,
                row_count=len(data),
                duration_ms=elapsed_ms,
            )

            return TableResult(
                table_name=table_name,
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
                table_name=table_name,
                error_type=error_type,
                error_message=str(exc),
                duration_ms=elapsed_ms,
            )

            return TableResult(
                table_name=table_name,
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
    return sanitized


# --- Internal Data Structures ---


@_dataclass
class _OfferOutcome:
    """Internal per-offer processing result."""

    offer_gid: str
    status: str  # "succeeded", "failed", "skipped"
    reason: str | None = None
    error: WorkflowItemError | None = None
    tables_succeeded: int | None = None
    tables_failed: int | None = None
    report_preview: str | None = None
