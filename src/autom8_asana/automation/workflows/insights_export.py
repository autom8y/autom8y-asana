"""Insights export workflow -- daily markdown report for Offer tasks.

Per TDD-EXPORT-001: Second WorkflowAction implementation.
Enumerates active Offers, resolves each to office_phone + vertical,
fetches 10 tables from autom8_data, composes markdown report,
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
from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)

# Feature flag environment variable
EXPORT_ENABLED_ENV_VAR = "AUTOM8_EXPORT_ENABLED"

# Offer project GID (canonical source: Offer.PRIMARY_PROJECT_GID)
OFFER_PROJECT_GID = "1143843662099250"

# Default concurrency for parallel offer processing
DEFAULT_MAX_CONCURRENCY = 5

# Default attachment pattern for cleanup
DEFAULT_ATTACHMENT_PATTERN = "insights_export_*.md"

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
       d. Upload new .md attachment (upload-first)
       e. Delete old matching .md attachments
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

    @property
    def workflow_id(self) -> str:
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
        except Exception:
            pass  # Non-circuit-breaker errors are not pre-flight failures

        return errors

    async def execute_async(
        self,
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the full insights export cycle.

        Args:
            params: Configurable parameters:
                - max_concurrency (int): Parallel offer limit, default 5
                - row_limits (dict): Per-table row limits override
                - attachment_pattern (str): Glob for old attachment cleanup

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

        # Step 1: Enumerate active Offers
        offers = await self._enumerate_offers()

        logger.info(
            "insights_export_started",
            total_offers=len(offers),
            max_concurrency=max_concurrency,
        )

        # Step 2: Process each offer with concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[_OfferOutcome] = []

        async def process_one(
            offer_gid: str,
            offer_name: str | None,
            parent_gid: str | None,
        ) -> None:
            async with semaphore:
                outcome = await self._process_offer(
                    offer_gid=offer_gid,
                    offer_name=offer_name,
                    parent_gid=parent_gid,
                    attachment_pattern=attachment_pattern,
                    row_limits=row_limits,
                )
                results.append(outcome)

        await asyncio.gather(
            *[process_one(o["gid"], o.get("name"), o.get("parent_gid")) for o in offers]
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

        workflow_result = WorkflowResult(
            workflow_id=self.workflow_id,
            started_at=started_at,
            completed_at=completed_at,
            total=len(offers),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            metadata={
                "per_offer_table_counts": per_offer_table_counts,
                "total_tables_succeeded": total_tables_succeeded,
                "total_tables_failed": total_tables_failed,
            },
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
        """List all active (non-completed) Offer tasks in BusinessOffers project.

        Uses paginated task listing with completed_since=now filter.

        Returns:
            List of dicts with {gid, name, parent_gid} fields.
        """
        page_iterator = self._asana_client.tasks.list_for_project_async(
            OFFER_PROJECT_GID,
            opt_fields=["name", "completed", "parent", "parent.name"],
            completed_since="now",
        )
        tasks = await page_iterator.collect()
        return [
            {
                "gid": t.gid,
                "name": t.name,
                "parent_gid": t.parent.gid if t.parent else None,
            }
            for t in tasks
            if not t.completed
        ]

    async def _process_offer(
        self,
        offer_gid: str,
        offer_name: str | None,
        parent_gid: str | None,
        attachment_pattern: str,
        row_limits: dict[str, int],
    ) -> _OfferOutcome:
        """Process a single Offer: resolve, fetch tables, compose, upload.

        Args:
            offer_gid: Offer task GID.
            offer_name: Offer task name (for logging / filename).
            parent_gid: Parent (Business) GID if known from enumeration.
            attachment_pattern: Glob for old attachment cleanup.
            row_limits: Per-table row limits.

        Returns:
            _OfferOutcome with status and per-table tracking.
        """
        offer_start = time.monotonic()

        try:
            # Step A: Resolve office_phone + vertical via parent Business
            resolution = await self._resolve_offer(offer_gid, parent_gid)
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

            # Step D: Compose markdown report
            report_data = InsightsReportData(
                business_name=business_name or offer_name or "Unknown",
                office_phone=office_phone,
                vertical=vertical,
                table_results=table_results,
                started_at=offer_start,
                version=WORKFLOW_VERSION,
                row_limits=row_limits,
            )
            markdown_content = compose_report(report_data)

            # Step E: Upload-first attachment replacement
            sanitized_name = _sanitize_business_name(
                business_name or offer_name or "Unknown"
            )
            date_str = datetime.now(UTC).strftime("%Y%m%d")
            filename = f"insights_export_{sanitized_name}_{date_str}.md"

            await self._attachments_client.upload_async(
                parent=offer_gid,
                file=markdown_content.encode("utf-8"),
                name=filename,
                content_type="text/markdown",
            )

            logger.info(
                "insights_export_upload_succeeded",
                offer_gid=offer_gid,
                filename=filename,
                size_bytes=len(markdown_content.encode("utf-8")),
            )

            # Step F: Delete old matching attachments
            await self._delete_old_attachments(
                offer_gid, attachment_pattern, exclude_name=filename
            )

            elapsed_ms = (time.monotonic() - offer_start) * 1000
            logger.info(
                "insights_export_offer_succeeded",
                offer_gid=offer_gid,
                tables_succeeded=tables_succeeded,
                tables_failed=tables_failed,
                duration_ms=elapsed_ms,
            )

            return _OfferOutcome(
                offer_gid=offer_gid,
                status="succeeded",
                tables_succeeded=tables_succeeded,
                tables_failed=tables_failed,
            )

        except Exception as exc:
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
        parent_gid: str | None,
    ) -> tuple[str, str, str | None] | None:
        """Resolve Offer -> parent Business -> office_phone + vertical.

        The resolution path is:
        1. Offer task -> parent reference (from enumeration or task fetch)
        2. Parent Business -> office_phone descriptor + vertical descriptor

        Args:
            offer_gid: Offer task GID.
            parent_gid: Parent Business GID if known from enumeration.

        Returns:
            Tuple of (office_phone, vertical, business_name) or None.
        """
        # If parent_gid not available from enumeration, fetch the task
        if not parent_gid:
            offer_task = await self._asana_client.tasks.get_async(
                offer_gid,
                opt_fields=["parent", "parent.gid"],
            )
            if not offer_task.parent or not offer_task.parent.gid:
                return None
            parent_gid = offer_task.parent.gid

        # Use ResolutionContext to resolve Business
        async with ResolutionContext(
            self._asana_client,
            business_gid=parent_gid,
        ) as ctx:
            business = await ctx.business_async()
            office_phone = business.office_phone
            vertical = business.vertical
            business_name = business.name

        if not office_phone or not vertical:
            return None

        return (office_phone, vertical, business_name)

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

        except Exception as exc:
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
