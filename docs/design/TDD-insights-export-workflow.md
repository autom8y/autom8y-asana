# TDD: InsightsExportWorkflow

**Date**: 2026-02-12
**Status**: Design Complete
**Architect**: Architect Agent
**ID**: TDD-EXPORT-001
**ADRs**: ADR-EXPORT-001, ADR-EXPORT-002, ADR-EXPORT-003
**Implements**: PRD-EXPORT-001 (InsightsExportWorkflow)
**Depends On**: WorkflowAction ABC, DataServiceClient, ResolutionContext, AttachmentsClient

---

## 1. Overview

The InsightsExportWorkflow is the second WorkflowAction implementation, following the proven ConversationAuditWorkflow pattern. It replaces the legacy `run_export` job with a modern batch workflow that:

1. Enumerates active Offer tasks from the BusinessOffers project
2. Resolves each Offer to `office_phone` and `vertical` via ResolutionContext
3. Fetches 10 tables of insights data from autom8_data via DataServiceClient
4. Composes a single markdown report per offer
5. Uploads the report as an attachment, replacing old exports

This is a second instance of a proven pattern. No new abstractions or frameworks are introduced.

### 1.1 Design Principles

1. **Follow the canonical pattern**: Mirror ConversationAuditWorkflow structure exactly
2. **Per-table error isolation**: One failed table does not poison the other nine
3. **Per-offer error isolation**: One failed offer does not affect the batch
4. **Upload-first**: New attachment is confirmed uploaded before old ones are deleted
5. **Idempotent**: Re-running produces the same end state (latest report, old ones cleaned)
6. **Shared API call optimization**: ASSET TABLE and UNUSED ASSETS derive from one API call

### 1.2 File Locations

New files:

| File | Purpose |
|------|---------|
| `src/autom8_asana/automation/workflows/insights_export.py` | InsightsExportWorkflow (WorkflowAction implementation) |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | Markdown report formatter (pipe tables, headers, footers) |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Lambda handler for EventBridge-scheduled execution |
| `tests/unit/automation/workflows/test_insights_export.py` | Workflow unit tests |
| `tests/unit/automation/workflows/test_insights_formatter.py` | Formatter unit tests |
| `tests/unit/clients/data/test_client_extensions.py` | DataServiceClient extension tests |
| `tests/unit/lambda_handlers/test_insights_export.py` | Lambda handler unit tests |

Modified files:

| File | Change |
|------|--------|
| `src/autom8_asana/clients/data/client.py` | Add `get_appointments_async()`, `get_leads_async()`; extend `_normalize_period()` |
| `src/autom8_asana/clients/data/models.py` | Extend `InsightsRequest.validate_period()` (already supports quarter/month/week -- verify only) |
| `src/autom8_asana/lambda_handlers/__init__.py` | Register `insights_export_handler` |

---

## 2. Implementation Sequencing

The work items are ordered to minimize integration risk. Each step is testable in isolation before the next depends on it.

### Phase 1: W04 -- DataServiceClient Extensions (FIRST)

**Why first**: W01 depends on these methods to fetch table data. Implementing and testing them independently ensures the data layer is solid before the workflow consumes it.

Deliverables:
- `get_appointments_async()` method
- `get_leads_async()` method
- `_normalize_period()` extension for QUARTER, MONTH, WEEK
- `InsightsRequest.validate_period()` verification (already accepts quarter/month/week per existing code)
- Unit tests in `tests/unit/clients/data/test_client_extensions.py`

### Phase 2: W03 -- Markdown Formatter (SECOND)

**Why second**: The formatter is a pure function module with no external dependencies. It takes data dicts in, produces markdown strings out. Testable with zero mocking.

Deliverables:
- `insights_formatter.py` module
- All formatting functions (header, footer, pipe tables, error markers)
- Unit tests in `tests/unit/automation/workflows/test_insights_formatter.py`

### Phase 3: W01 + W02 -- Workflow Core + Error Isolation (THIRD)

**Why third**: Depends on both W04 (data fetching) and W03 (formatting). Combines the fetch-compose-upload lifecycle with per-table error isolation.

Deliverables:
- `insights_export.py` module with InsightsExportWorkflow class
- Per-table error isolation (W02)
- Unit tests in `tests/unit/automation/workflows/test_insights_export.py`

### Phase 4: W05 -- Lambda Handler + Registration (FOURTH)

**Why fourth**: The handler is a thin wrapper around the workflow. It cannot be implemented until the workflow exists.

Deliverables:
- `lambda_handlers/insights_export.py`
- Registration in `lambda_handlers/__init__.py`
- Unit tests in `tests/unit/lambda_handlers/test_insights_export.py`

---

## 3. Module Decomposition

### 3.1 InsightsExportWorkflow (`automation/workflows/insights_export.py`)

```python
"""Insights export workflow -- daily markdown report for Offer tasks.

Per TDD-EXPORT-001: Second WorkflowAction implementation.
Enumerates active Offers, resolves each to office_phone + vertical,
fetches 10 tables from autom8_data, composes markdown report,
and uploads as attachment to each Offer task.
"""

from __future__ import annotations

import asyncio
import fnmatch
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
from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.data.client import DataServiceClient, mask_phone_number
from autom8_asana.clients.data.models import InsightsResponse
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


class InsightsExportWorkflow(WorkflowAction):
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
            errors.append(
                f"Workflow disabled via {EXPORT_ENABLED_ENV_VAR}={env_value}"
            )
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
            *[
                process_one(o["gid"], o.get("name"), o.get("parent_gid"))
                for o in offers
            ]
        )

        # Step 3: Aggregate results
        succeeded = sum(1 for r in results if r.status == "succeeded")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        errors = [r.error for r in results if r.error is not None]

        # Per-offer table counts
        per_offer_table_counts = {}
        total_tables_succeeded = 0
        total_tables_failed = 0
        for r in results:
            if r.tables_succeeded is not None:
                per_offer_table_counts[r.offer_gid] = {
                    "tables_succeeded": r.tables_succeeded,
                    "tables_failed": r.tables_failed,
                }
                total_tables_succeeded += r.tables_succeeded
                total_tables_failed += r.tables_failed

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

            tables_succeeded = sum(
                1 for t in table_results.values() if t.success
            )
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
                "SUMMARY", offer_gid, office_phone, vertical,
                frame_type="unit", period="lifetime",
            ),
            self._fetch_table(
                "APPOINTMENTS", offer_gid, office_phone, vertical,
                method="appointments", days=90,
                limit=row_limits.get("APPOINTMENTS", 100),
            ),
            self._fetch_table(
                "LEADS", offer_gid, office_phone, vertical,
                method="leads", days=30, exclude_appointments=True,
                limit=row_limits.get("LEADS", 100),
            ),
            self._fetch_table(
                "BY QUARTER", offer_gid, office_phone, vertical,
                frame_type="unit", period="quarter",
            ),
            self._fetch_table(
                "BY MONTH", offer_gid, office_phone, vertical,
                frame_type="unit", period="month",
            ),
            self._fetch_table(
                "BY WEEK", offer_gid, office_phone, vertical,
                frame_type="unit", period="week",
            ),
            self._fetch_table(
                "AD QUESTIONS", offer_gid, office_phone, vertical,
                frame_type="offer", period="lifetime",
            ),
            self._fetch_table(
                "ASSET TABLE", offer_gid, office_phone, vertical,
                frame_type="asset", period="t30",
            ),
            self._fetch_table(
                "OFFER TABLE", offer_gid, office_phone, vertical,
                frame_type="offer", period="t30",
            ),
        )

        table_map: dict[str, TableResult] = {}
        for r in results:
            table_map[r.table_name] = r

        # Derive UNUSED ASSETS from ASSET TABLE response
        asset_result = table_map.get("ASSET TABLE")
        if asset_result is not None and asset_result.success:
            unused_rows = [
                row for row in (asset_result.data or [])
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
        frame_type: str | None = None,
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
            frame_type: For POST /insights calls.
            period: For POST /insights calls.
            method: "appointments" or "leads" for detail endpoints.
            days: For appointment/lead detail endpoints.
            limit: Row limit for detail endpoints.
            exclude_appointments: For leads endpoint.

        Returns:
            TableResult with data or error information.
        """
        masked_phone = mask_phone_number(office_phone)
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
                # Standard POST /insights call
                # Map frame_type to a factory name for get_insights_async
                factory = _frame_type_to_factory(frame_type or "unit")
                response = await self._data_client.get_insights_async(
                    factory=factory,
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

    async def _delete_old_attachments(
        self,
        offer_gid: str,
        pattern: str,
        exclude_name: str,
    ) -> None:
        """Delete old export attachments matching pattern.

        Per PRD FR-W01.8: Only deletes attachments matching the
        insights_export_*.md pattern. The just-uploaded file is excluded.
        Delete failure is non-fatal.

        Args:
            offer_gid: Task GID to list attachments for.
            pattern: Glob pattern to match.
            exclude_name: Filename to exclude from deletion.
        """
        page_iter = self._attachments_client.list_for_task_async(
            offer_gid,
            opt_fields=["name"],
        )
        async for attachment in page_iter:
            att_name = attachment.name or ""
            if fnmatch.fnmatch(att_name, pattern) and att_name != exclude_name:
                try:
                    await self._attachments_client.delete_async(attachment.gid)
                    logger.debug(
                        "insights_export_old_attachment_deleted",
                        offer_gid=offer_gid,
                        attachment_gid=attachment.gid,
                        attachment_name=att_name,
                    )
                except Exception as exc:
                    logger.warning(
                        "insights_export_old_attachment_delete_failed",
                        offer_gid=offer_gid,
                        attachment_gid=attachment.gid,
                        error=str(exc),
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


def _frame_type_to_factory(frame_type: str) -> str:
    """Map frame_type to the appropriate factory name for get_insights_async.

    The DataServiceClient.get_insights_async() accepts factory names and
    maps them to frame_types internally via FACTORY_TO_FRAME_TYPE.
    We need the reverse mapping for InsightsExportWorkflow which thinks
    in terms of frame_types (per the PRD's table-to-API-call mapping).

    Args:
        frame_type: One of "unit", "offer", "asset".

    Returns:
        Factory name string.
    """
    # Reverse lookup: find a factory that maps to this frame_type.
    # Use canonical factories per the PRD's intent:
    mapping = {
        "unit": "base",       # base -> unit frame_type
        "offer": "ad_questions",  # ad_questions -> offer frame_type
        "asset": "assets",    # assets -> asset frame_type
    }
    return mapping.get(frame_type, "base")


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
```

**Key design note on `_frame_type_to_factory`**: The `get_insights_async()` method takes a `factory` parameter and maps it to a `frame_type` internally. The PRD specifies table fetches in terms of frame_type + period. The mapping above selects the correct factory for each frame_type. For the AD QUESTIONS table, the factory is `"ad_questions"` (which maps to offer frame_type). For OFFER TABLE, the factory is `"business_offers"` (which also maps to offer frame_type). This distinction is important because different factories may return different column sets even within the same frame_type.

**Correction to the above**: Looking more carefully at the FACTORY_TO_FRAME_TYPE mapping, the workflow must call `get_insights_async` with the correct factory for each table:

| Table | Factory | frame_type (derived) | Period |
|-------|---------|---------------------|--------|
| SUMMARY | `"base"` | unit | LIFETIME |
| BY QUARTER | `"base"` | unit | QUARTER |
| BY MONTH | `"base"` | unit | MONTH |
| BY WEEK | `"base"` | unit | WEEK |
| AD QUESTIONS | `"ad_questions"` | offer | LIFETIME |
| ASSET TABLE | `"assets"` | asset | T30 |
| OFFER TABLE | `"business_offers"` | offer | T30 |
| UNUSED ASSETS | (derived from ASSET TABLE) | N/A | N/A |

The `_fetch_table` method will accept a `factory` parameter directly rather than using `_frame_type_to_factory`. Updated interface:

```python
async def _fetch_table(
    self,
    table_name: str,
    offer_gid: str,
    office_phone: str,
    vertical: str,
    *,
    factory: str | None = None,   # Factory name for get_insights_async
    period: str | None = None,
    method: str | None = None,    # "appointments" or "leads"
    days: int | None = None,
    limit: int | None = None,
    exclude_appointments: bool = False,
) -> TableResult:
```

And the `_fetch_all_tables` dispatch becomes:

```python
results = await asyncio.gather(
    self._fetch_table("SUMMARY", ..., factory="base", period="lifetime"),
    self._fetch_table("APPOINTMENTS", ..., method="appointments", days=90, limit=...),
    self._fetch_table("LEADS", ..., method="leads", days=30, ...),
    self._fetch_table("BY QUARTER", ..., factory="base", period="quarter"),
    self._fetch_table("BY MONTH", ..., factory="base", period="month"),
    self._fetch_table("BY WEEK", ..., factory="base", period="week"),
    self._fetch_table("AD QUESTIONS", ..., factory="ad_questions", period="lifetime"),
    self._fetch_table("ASSET TABLE", ..., factory="assets", period="t30"),
    self._fetch_table("OFFER TABLE", ..., factory="business_offers", period="t30"),
)
```

### 3.2 Markdown Formatter (`automation/workflows/insights_formatter.py`)

This is a separate module per ADR-EXPORT-001 (see Section 10).

```python
"""Markdown report formatter for insights export.

Per TDD-EXPORT-001: Produces pipe-table markdown from table data dicts.
Pure functions with no external dependencies. All formatting logic
is concentrated here for testability.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from autom8_asana.clients.data.client import mask_phone_number


# Section order (per PRD FR-W01.6)
TABLE_ORDER: list[str] = [
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


@dataclass
class TableResult:
    """Result of fetching a single table.

    Attributes:
        table_name: Human-readable table name (e.g., "SUMMARY").
        success: Whether the fetch succeeded.
        data: List of row dicts from the API response (None if failed).
        row_count: Number of rows returned.
        error_type: Error classification string (if failed).
        error_message: Human-readable error description (if failed).
    """

    table_name: str
    success: bool
    data: list[dict[str, Any]] | None = None
    row_count: int = 0
    error_type: str | None = None
    error_message: str | None = None


@dataclass
class InsightsReportData:
    """Input data for composing a full markdown report.

    Attributes:
        business_name: Name of the Business (for header).
        office_phone: E.164 phone number (will be masked in header).
        vertical: Business vertical.
        table_results: Dict mapping table name to TableResult.
        started_at: Monotonic time when offer processing started.
        version: Workflow version identifier.
        row_limits: Per-table row limit configuration.
    """

    business_name: str
    office_phone: str
    vertical: str
    table_results: dict[str, TableResult]
    started_at: float  # time.monotonic() value
    version: str
    row_limits: dict[str, int] = field(default_factory=dict)


def compose_report(data: InsightsReportData) -> str:
    """Compose a full markdown report from table results.

    Section order: Header -> 10 tables -> Footer

    Args:
        data: InsightsReportData with all table results.

    Returns:
        Complete markdown string.
    """
    sections: list[str] = []

    # Header
    sections.append(_format_header(data))

    # Tables in fixed order
    for table_name in TABLE_ORDER:
        result = data.table_results.get(table_name)
        if result is None:
            sections.append(_format_error_section(
                table_name, "missing", "Table result not available"
            ))
        elif not result.success:
            sections.append(_format_error_section(
                table_name,
                result.error_type or "unknown",
                result.error_message or "Unknown error",
            ))
        elif not result.data:
            sections.append(_format_empty_section(table_name))
        else:
            row_limit = data.row_limits.get(table_name)
            sections.append(
                _format_table_section(table_name, result.data, row_limit)
            )

    # Footer
    elapsed = time.monotonic() - data.started_at
    tables_succeeded = sum(
        1 for r in data.table_results.values() if r.success
    )
    tables_failed = len(TABLE_ORDER) - tables_succeeded
    sections.append(
        _format_footer(elapsed, tables_succeeded, tables_failed, data.version)
    )

    return "\n\n".join(sections) + "\n"


def _format_header(data: InsightsReportData) -> str:
    """Format the report header section.

    Includes: business name, masked phone, vertical, timestamp.
    """
    masked = mask_phone_number(data.office_phone)
    timestamp = datetime.now(UTC).isoformat()
    return (
        f"# Insights Export: {data.business_name}\n\n"
        f"**Phone**: {masked}  \n"
        f"**Vertical**: {data.vertical}  \n"
        f"**Generated**: {timestamp}  \n"
        f"**Period**: Daily insights report"
    )


def _format_table_section(
    table_name: str,
    rows: list[dict[str, Any]],
    row_limit: int | None = None,
) -> str:
    """Format a table section with pipe-table markdown.

    Args:
        table_name: Table heading name.
        rows: List of row dicts.
        row_limit: Maximum rows to display. None = no limit.

    Returns:
        Markdown string with heading, pipe table, and optional truncation note.
    """
    total_rows = len(rows)
    display_rows = rows[:row_limit] if row_limit else rows
    truncated = row_limit is not None and total_rows > row_limit

    # Collect all column names (union of all rows, preserving first-seen order)
    columns: list[str] = []
    seen: set[str] = set()
    for row in display_rows:
        for key in row:
            if key not in seen:
                columns.append(key)
                seen.add(key)

    if not columns:
        return f"## {table_name}\n\n> No data available"

    # Header row (Title Case)
    header_cells = [_to_title_case(col) for col in columns]
    header_line = "| " + " | ".join(header_cells) + " |"

    # Alignment row
    align_line = "| " + " | ".join("---" for _ in columns) + " |"

    # Data rows
    data_lines: list[str] = []
    for row in display_rows:
        cells = [_format_cell(row.get(col)) for col in columns]
        data_lines.append("| " + " | ".join(cells) + " |")

    parts = [f"## {table_name}", "", header_line, align_line] + data_lines

    if truncated:
        parts.append("")
        parts.append(f"> Showing first {row_limit} of {total_rows} rows")

    return "\n".join(parts)


def _format_empty_section(table_name: str) -> str:
    """Format an empty table section.

    Per PRD FR-W03.3: Zero rows -> "No data available" note.
    Special case for UNUSED ASSETS: "No unused assets found".
    """
    if table_name == "UNUSED ASSETS":
        return f"## {table_name}\n\n> No unused assets found"
    return f"## {table_name}\n\n> No data available"


def _format_error_section(
    table_name: str,
    error_type: str,
    message: str,
) -> str:
    """Format an error marker section.

    Per PRD FR-W02.2:
    ## TABLE_NAME
    > [ERROR] {error_type}: {message}
    """
    return f"## {table_name}\n\n> [ERROR] {error_type}: {message}"


def _format_footer(
    duration_seconds: float,
    tables_succeeded: int,
    tables_failed: int,
    version: str,
) -> str:
    """Format the report footer section.

    Per PRD FR-W03.7: Duration, table count, error count, version.
    """
    total = tables_succeeded + tables_failed
    parts = [
        "---",
        "",
        f"**Duration**: {duration_seconds:.2f}s  ",
        f"**Tables**: {tables_succeeded}/{total}  ",
    ]
    if tables_failed > 0:
        parts.append(f"**Errors**: {tables_failed}  ")
    parts.append(f"**Version**: {version}")
    return "\n".join(parts)


def _to_title_case(column_name: str) -> str:
    """Convert snake_case column name to Title Case.

    Per PRD FR-W03.4: offer_cost -> Offer Cost

    Args:
        column_name: Snake-case column name from API response.

    Returns:
        Title Case display name.
    """
    return column_name.replace("_", " ").title()


def _format_cell(value: Any) -> str:
    """Format a single cell value for pipe table display.

    Per PRD FR-W03.5: Null values rendered as `---`.

    Args:
        value: Cell value (may be None).

    Returns:
        String representation for the pipe table cell.
    """
    if value is None:
        return "---"
    return str(value)
```

### 3.3 DataServiceClient Extensions (`clients/data/client.py`)

Two new async methods and an extension to `_normalize_period()`.

```python
# --- New Method: get_appointments_async ---

async def get_appointments_async(
    self,
    office_phone: str,
    *,
    days: int = 90,
    limit: int = 100,
) -> InsightsResponse:
    """Fetch appointment detail rows for a business.

    Per TDD-EXPORT-001 W04: Maps to GET /appointments on autom8_data.
    Uses the same circuit breaker, retry handler, and auth as
    get_insights_async.

    Args:
        office_phone: E.164 formatted phone number.
        days: Lookback window in days (default: 90).
        limit: Maximum rows to return (default: 100).

    Returns:
        InsightsResponse with appointment detail rows.

    Raises:
        InsightsServiceError: Upstream service failure.
        InsightsNotFoundError: No data found.
    """
    self._check_feature_enabled()

    request_id = str(uuid.uuid4())
    masked_phone = mask_phone_number(office_phone)

    logger.info(
        "appointments_request_started",
        office_phone=masked_phone,
        days=days,
        limit=limit,
        request_id=request_id,
    )

    # Circuit breaker check
    try:
        await self._circuit_breaker.check()
    except SdkCircuitBreakerOpenError as e:
        raise InsightsServiceError(
            f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
            request_id=request_id,
            reason="circuit_breaker",
        ) from e

    client = await self._get_client()
    path = "/api/v1/appointments"
    params = {
        "office_phone": office_phone,
        "days": str(days),
        "limit": str(limit),
    }

    start_time = time.monotonic()

    async def _on_timeout(e: httpx.TimeoutException, attempt: int) -> None:
        await self._circuit_breaker.record_failure(e)
        raise InsightsServiceError(
            "Appointments request timed out",
            request_id=request_id,
            reason="timeout",
        ) from e

    async def _on_http_error(e: httpx.HTTPError, attempt: int) -> None:
        await self._circuit_breaker.record_failure(e)
        raise InsightsServiceError(
            f"HTTP error during appointments fetch: {e}",
            request_id=request_id,
            reason="http_error",
        ) from e

    response, _attempt = await self._execute_with_retry(
        lambda: client.get(
            path,
            params=params,
            headers={"X-Request-Id": request_id},
        ),
        on_timeout_exhausted=_on_timeout,
        on_http_error=_on_http_error,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    if response.status_code >= 400:
        cache_key = f"appointments:{office_phone}"
        return await self._handle_error_response(
            response, request_id, cache_key, "appointments", elapsed_ms
        )

    insights_response = self._parse_success_response(response, request_id)
    await self._circuit_breaker.record_success()

    logger.info(
        "appointments_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        duration_ms=elapsed_ms,
        request_id=request_id,
    )

    return insights_response
```

```python
# --- New Method: get_leads_async ---

async def get_leads_async(
    self,
    office_phone: str,
    *,
    days: int = 30,
    exclude_appointments: bool = True,
    limit: int = 100,
) -> InsightsResponse:
    """Fetch lead detail rows for a business.

    Per TDD-EXPORT-001 W04: Maps to GET /leads on autom8_data.
    Uses the same circuit breaker, retry handler, and auth as
    get_insights_async.

    Args:
        office_phone: E.164 formatted phone number.
        days: Lookback window in days (default: 30).
        exclude_appointments: Exclude appointment leads (default: True).
        limit: Maximum rows to return (default: 100).

    Returns:
        InsightsResponse with lead detail rows.

    Raises:
        InsightsServiceError: Upstream service failure.
        InsightsNotFoundError: No data found.
    """
    self._check_feature_enabled()

    request_id = str(uuid.uuid4())
    masked_phone = mask_phone_number(office_phone)

    logger.info(
        "leads_request_started",
        office_phone=masked_phone,
        days=days,
        exclude_appointments=exclude_appointments,
        limit=limit,
        request_id=request_id,
    )

    # Circuit breaker check
    try:
        await self._circuit_breaker.check()
    except SdkCircuitBreakerOpenError as e:
        raise InsightsServiceError(
            f"Circuit breaker open. Retry in {e.time_remaining:.1f}s.",
            request_id=request_id,
            reason="circuit_breaker",
        ) from e

    client = await self._get_client()
    path = "/api/v1/leads"
    params: dict[str, str] = {
        "office_phone": office_phone,
        "days": str(days),
        "limit": str(limit),
    }
    if exclude_appointments:
        params["exclude_appointments"] = "true"

    start_time = time.monotonic()

    async def _on_timeout(e: httpx.TimeoutException, attempt: int) -> None:
        await self._circuit_breaker.record_failure(e)
        raise InsightsServiceError(
            "Leads request timed out",
            request_id=request_id,
            reason="timeout",
        ) from e

    async def _on_http_error(e: httpx.HTTPError, attempt: int) -> None:
        await self._circuit_breaker.record_failure(e)
        raise InsightsServiceError(
            f"HTTP error during leads fetch: {e}",
            request_id=request_id,
            reason="http_error",
        ) from e

    response, _attempt = await self._execute_with_retry(
        lambda: client.get(
            path,
            params=params,
            headers={"X-Request-Id": request_id},
        ),
        on_timeout_exhausted=_on_timeout,
        on_http_error=_on_http_error,
    )

    elapsed_ms = (time.monotonic() - start_time) * 1000

    if response.status_code >= 400:
        cache_key = f"leads:{office_phone}"
        return await self._handle_error_response(
            response, request_id, cache_key, "leads", elapsed_ms
        )

    insights_response = self._parse_success_response(response, request_id)
    await self._circuit_breaker.record_success()

    logger.info(
        "leads_request_completed",
        office_phone=masked_phone,
        row_count=insights_response.metadata.row_count,
        duration_ms=elapsed_ms,
        request_id=request_id,
    )

    return insights_response
```

```python
# --- Extended _normalize_period ---

def _normalize_period(self, insights_period: str | None) -> str:
    """Normalize insights_period to autom8_data's period format.

    Maps autom8_asana's period values to autom8_data's expected format:
    - "lifetime" -> "LIFETIME"
    - "t7", "l7" -> "T7"
    - "t14", "l14" -> "T14"
    - "t30", "l30" -> "T30"
    - "quarter" -> "QUARTER"   (NEW)
    - "month" -> "MONTH"       (NEW)
    - "week" -> "WEEK"         (NEW)

    Args:
        insights_period: Period value from InsightsRequest.

    Returns:
        Normalized period string for autom8_data API.
    """
    if insights_period is None:
        return "LIFETIME"

    period_lower = insights_period.lower()

    if period_lower == "lifetime":
        return "LIFETIME"
    elif period_lower in ("t7", "l7"):
        return "T7"
    elif period_lower in ("t14", "l14"):
        return "T14"
    elif period_lower in ("t30", "l30"):
        return "T30"
    elif period_lower == "quarter":
        return "QUARTER"
    elif period_lower == "month":
        return "MONTH"
    elif period_lower == "week":
        return "WEEK"

    # Default to T30 for other values (backward compatibility)
    return "T30"
```

### 3.4 Lambda Handler (`lambda_handlers/insights_export.py`)

```python
"""Lambda handler for insights export workflow.

Per TDD-EXPORT-001 Section 3.4: Entry point for scheduled Lambda execution.
Triggered by EventBridge rule on configured schedule (6:00 AM ET daily).

Environment Variables Required:
    ASANA_PAT: Asana Personal Access Token
    AUTOM8_DATA_URL: Base URL for autom8_data
    AUTOM8_DATA_API_KEY: API key for autom8_data
    AUTOM8_EXPORT_ENABLED: Feature flag (default: enabled)
"""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for insights export workflow.

    Args:
        event: EventBridge event (can contain override params).
        context: Lambda context with timeout info.

    Returns:
        Dict with execution result summary.
    """
    return asyncio.run(_handler_async(event, context))


async def _handler_async(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Async implementation of the Lambda handler."""
    try:
        return await _execute(event)
    except Exception as exc:
        logger.error(
            "lambda_insights_export_error",
            error=str(exc),
            error_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            ),
        }


async def _execute(event: dict[str, Any]) -> dict[str, Any]:
    """Execute the workflow with client initialization and cleanup."""
    from autom8_asana.automation.workflows.insights_export import (
        DEFAULT_ATTACHMENT_PATTERN,
        DEFAULT_MAX_CONCURRENCY,
        DEFAULT_ROW_LIMITS,
        InsightsExportWorkflow,
    )
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient

    logger.info("lambda_insights_export_started", lambda_event=event)

    # Build params from event or defaults
    params = {
        "workflow_id": "insights-export",
        "max_concurrency": event.get("max_concurrency", DEFAULT_MAX_CONCURRENCY),
        "attachment_pattern": event.get(
            "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
        ),
        "row_limits": event.get("row_limits", DEFAULT_ROW_LIMITS),
    }

    # Initialize clients
    asana_client = AsanaClient()
    async with DataServiceClient() as data_client:
        workflow = InsightsExportWorkflow(
            asana_client=asana_client,
            data_client=data_client,
            attachments_client=asana_client.attachments,
        )

        # Pre-flight validation
        validation_errors = await workflow.validate_async()
        if validation_errors:
            logger.error(
                "lambda_insights_export_validation_failed",
                errors=validation_errors,
            )
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "status": "skipped",
                        "reason": "validation_failed",
                        "errors": validation_errors,
                    }
                ),
            }

        # Execute workflow
        result = await workflow.execute_async(params)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "completed",
                    "workflow_id": result.workflow_id,
                    "total": result.total,
                    "succeeded": result.succeeded,
                    "failed": result.failed,
                    "skipped": result.skipped,
                    "duration_seconds": round(result.duration_seconds, 2),
                    "failure_rate": round(result.failure_rate, 4),
                    "total_tables_succeeded": result.metadata.get(
                        "total_tables_succeeded", 0
                    ),
                    "total_tables_failed": result.metadata.get(
                        "total_tables_failed", 0
                    ),
                }
            ),
        }
```

### 3.5 Registration Updates

**`lambda_handlers/__init__.py`** -- add import:

```python
from autom8_asana.lambda_handlers.insights_export import (
    handler as insights_export_handler,
)

__all__ = [
    "cache_invalidate_handler",
    "cache_warmer_handler",
    "conversation_audit_handler",
    "insights_export_handler",  # NEW
]
```

**WorkflowRegistry registration** -- In application startup (same pattern as ConversationAuditWorkflow):

```python
registry.register(
    InsightsExportWorkflow(
        asana_client=asana_client,
        data_client=data_client,
        attachments_client=attachments_client,
    )
)
```

---

## 4. Table-to-API-Call Mapping (Reference)

This is the definitive mapping from PRD Appendix 11, annotated with implementation details.

| # | Table | Client Method | Factory/Endpoint | Period | Notes |
|---|-------|--------------|------------------|--------|-------|
| 1 | SUMMARY | `get_insights_async(factory="base", period="lifetime")` | POST /insights, frame_type=unit | LIFETIME | Single aggregated row |
| 2 | APPOINTMENTS | `get_appointments_async(office_phone, days=90, limit=100)` | GET /appointments | days=90 | YELLOW: verify endpoint exists |
| 3 | LEADS | `get_leads_async(office_phone, days=30, exclude_appointments=True, limit=100)` | GET /leads | days=30 | YELLOW: verify endpoint exists |
| 4 | BY QUARTER | `get_insights_async(factory="base", period="quarter")` | POST /insights, frame_type=unit | QUARTER | Requires W04 period extension |
| 5 | BY MONTH | `get_insights_async(factory="base", period="month")` | POST /insights, frame_type=unit | MONTH | Requires W04 period extension |
| 6 | BY WEEK | `get_insights_async(factory="base", period="week")` | POST /insights, frame_type=unit | WEEK | Requires W04 period extension |
| 7 | AD QUESTIONS | `get_insights_async(factory="ad_questions", period="lifetime")` | POST /insights, frame_type=offer | LIFETIME | Question dimension on offer |
| 8 | ASSET TABLE | `get_insights_async(factory="assets", period="t30")` | POST /insights, frame_type=asset | T30 | asset_score deferred |
| 9 | OFFER TABLE | `get_insights_async(factory="business_offers", period="t30")` | POST /insights, frame_type=offer | T30 | Per-offer metrics |
| 10 | UNUSED ASSETS | (derived from #8) | N/A | N/A | Client-side filter: spend==0 AND imp==0 |

---

## 5. Error Isolation Architecture

### 5.1 Per-Table Error Isolation

Each of the 10 table fetches (technically 9 API calls + 1 derivation) is wrapped individually in `_fetch_table`. The method catches all exceptions and returns a `TableResult` with `success=False` and error details.

```
For each table:
    try:
        response = await data_client.get_insights_async(...)
        return TableResult(success=True, data=response.data)
    except Exception as exc:
        return TableResult(success=False, error_type=..., error_message=...)
```

The UNUSED ASSETS table inherits the fate of the ASSET TABLE:
- If ASSET TABLE succeeds: UNUSED ASSETS is derived (filtered) from its data
- If ASSET TABLE fails: UNUSED ASSETS also fails with a derived error message

### 5.2 Partial Report Assembly

After all 10 `TableResult` objects are collected:

1. Count `tables_succeeded` = number of results where `success=True`
2. If `tables_succeeded == 0`: mark offer as FAILED, do NOT upload (FR-W02.3)
3. If `tables_succeeded > 0`: compose markdown with error markers for failed tables, upload partial report

This means any combination of 1-10 successful tables produces a report. Only the degenerate case of 0 successful tables prevents upload.

### 5.3 Per-Offer Error Isolation

The outer `_process_offer` method wraps the entire per-offer lifecycle in a catch-all. If any unexpected exception escapes (e.g., resolution failure, upload failure), the offer is marked as FAILED but the batch continues processing other offers. This mirrors ConversationAuditWorkflow's `_process_holder` pattern.

### 5.4 Total Failure Detection

Per FR-W02.3: If all 10 tables fail for a single offer:
- `_OfferOutcome.status = "failed"`
- `_OfferOutcome.error = WorkflowItemError(error_type="all_tables_failed", ...)`
- No attachment is uploaded
- The offer is logged as failed with all error details

---

## 6. Markdown Format Specification

### 6.1 Document Structure

```markdown
# Insights Export: {BusinessName}

**Phone**: +1770***3103
**Vertical**: chiropractic
**Generated**: 2026-02-12T11:00:00+00:00
**Period**: Daily insights report

## SUMMARY

| Offer Cost | Impressions | Clicks | ... |
| --- | --- | --- | ... |
| 1500.00 | 45000 | 1200 | ... |

## APPOINTMENTS

| Date | Name | Status | Out Calls | In Calls | Time On Call |
| --- | --- | --- | --- | --- | --- |
| 2026-02-10 | John Doe | confirmed | --- | --- | --- |

## LEADS

| Date | Name | Source | Follow Up | Convo | Lead Call Time |
| --- | --- | --- | --- | --- | --- |
| 2026-02-08 | Jane Smith | web | --- | --- | --- |

## BY QUARTER
...

## BY MONTH
...

## BY WEEK
...

## AD QUESTIONS
...

## ASSET TABLE
...

## OFFER TABLE
...

## UNUSED ASSETS

> No unused assets found

---

**Duration**: 3.45s
**Tables**: 10/10
**Version**: insights-export-v1.0
```

### 6.2 Error Marker Format

When a table fails:

```markdown
## APPOINTMENTS

> [ERROR] InsightsServiceError: Request to autom8_data timed out
```

### 6.3 Empty Table Format

When a table returns zero rows:

```markdown
## BY QUARTER

> No data available
```

Special case for UNUSED ASSETS:

```markdown
## UNUSED ASSETS

> No unused assets found
```

### 6.4 Row Limit Truncation

When a table exceeds its row limit:

```markdown
## APPOINTMENTS

| Date | Name | Status | ... |
| --- | --- | --- | ... |
| ... (100 rows) ... |

> Showing first 100 of 247 rows
```

### 6.5 Column Name Rendering

All column names from the API are converted from `snake_case` to `Title Case`:
- `offer_cost` -> `Offer Cost`
- `imp` -> `Imp`
- `time_on_call` -> `Time On Call`

### 6.6 Null Handling

Null values (None in Python) are rendered as `---` in pipe table cells. This applies to:
- APPOINTMENTS: `out_calls`, `in_calls`, `time_on_call` (always null per PRD)
- LEADS: `follow_up`, `convo`, `lead_call_time` (always null per PRD)
- Any other column that happens to be null for a given row

Columns with null values are NOT omitted from the table. They are included with `---` markers.

### 6.7 File Naming

```
insights_export_{BusinessName}_{YYYYMMDD}.md
```

Where `BusinessName` is sanitized:
- Spaces replaced with underscores
- Non-alphanumeric characters (except underscore) stripped
- Example: `"Dr. Smith's Dental"` -> `Dr_Smiths_Dental`

---

## 7. YELLOW Dependency Handling

### 7.1 Appointments and Leads Endpoints (YELLOW)

The `GET /appointments` and `GET /leads` endpoints on autom8_data are assumed to exist per the PRD. If they are unavailable at implementation time:

**Degradation path**: The `_fetch_table` error isolation handles this automatically. If `get_appointments_async()` or `get_leads_async()` raises any exception (connection refused, 404, 500, etc.), the corresponding table renders with an error marker:

```markdown
## APPOINTMENTS

> [ERROR] InsightsServiceError: HTTP error during appointments fetch: ...
```

The remaining 8 tables proceed normally. No code changes are needed for this degradation -- it is a natural consequence of the per-table error isolation design.

### 7.2 Asset Score Column (YELLOW)

The `asset_score` column is computed by autom8_data's HealthScoreService and returned inline in the insights response for `frame_type=asset`. If it is not available:

**Omission strategy**: The ASSET TABLE section renders whatever columns the API returns. If `asset_score` is not present in the response data, it simply does not appear in the pipe table. No special handling is needed because the formatter dynamically builds columns from the actual data keys.

When autom8_data adds `asset_score` to the asset insights response, it will automatically appear in the next export run. No code change in autom8_asana is required.

---

## 8. Data Model

### 8.1 TableResult (dataclass)

```python
@dataclass
class TableResult:
    table_name: str                          # e.g., "SUMMARY"
    success: bool
    data: list[dict[str, Any]] | None = None # Row dicts from API
    row_count: int = 0
    error_type: str | None = None            # e.g., "InsightsServiceError"
    error_message: str | None = None
```

### 8.2 InsightsReportData (dataclass)

```python
@dataclass
class InsightsReportData:
    business_name: str
    office_phone: str                        # E.164, masked in header
    vertical: str
    table_results: dict[str, TableResult]    # Keyed by table name
    started_at: float                        # time.monotonic() value
    version: str
    row_limits: dict[str, int]               # Per-table row limits
```

### 8.3 _OfferOutcome (internal dataclass)

```python
@dataclass
class _OfferOutcome:
    offer_gid: str
    status: str                              # "succeeded", "failed", "skipped"
    reason: str | None = None                # For skipped offers
    error: WorkflowItemError | None = None
    tables_succeeded: int | None = None
    tables_failed: int | None = None
```

### 8.4 WorkflowResult.metadata Structure

```python
metadata = {
    "per_offer_table_counts": {
        "offer-gid-1": {"tables_succeeded": 9, "tables_failed": 1},
        "offer-gid-2": {"tables_succeeded": 10, "tables_failed": 0},
    },
    "total_tables_succeeded": 19,
    "total_tables_failed": 1,
}
```

---

## 9. Test Strategy

### 9.1 Test File Locations

| File | Coverage |
|------|----------|
| `tests/unit/automation/workflows/test_insights_export.py` | W01, W02 workflow tests |
| `tests/unit/automation/workflows/test_insights_formatter.py` | W03 formatter tests |
| `tests/unit/clients/data/test_client_extensions.py` | W04 client extension tests |
| `tests/unit/lambda_handlers/test_insights_export.py` | W05 handler tests |

### 9.2 Test Scenarios with AC Mapping

#### `test_insights_export.py` -- Workflow Tests

| Test Class | Scenario | ACs Covered |
|-----------|----------|-------------|
| `TestWorkflowId` | `workflow_id == "insights-export"` | AC-W01.1 |
| `TestValidateAsync` | Feature flag disabled (`"false"`, `"0"`, `"no"`) | AC-W01.2, AC-W05.5 |
| `TestValidateAsync` | Feature flag enabled (unset env var) | AC-W05.6 |
| `TestValidateAsync` | Circuit breaker open | AC-W01.3 |
| `TestEnumeration` | Only non-completed offers enumerated | AC-W01.4 |
| `TestResolution` | Successful resolution to phone + vertical | AC-W01.5 |
| `TestResolution` | Skip when phone or vertical missing | AC-W01.6 |
| `TestFetchAllTables` | All 10 table calls dispatched concurrently | AC-W01.7 |
| `TestUploadAndCleanup` | Markdown file uploaded with correct naming | AC-W01.8, AC-W03.11 |
| `TestUploadAndCleanup` | Old attachments deleted after upload | AC-W01.9 |
| `TestUploadAndCleanup` | Upload-first ordering (new before delete) | AC-W01.10 |
| `TestConcurrency` | Semaphore bounds concurrent offers | AC-W01.11 |
| `TestWorkflowResult` | Result includes total/succeeded/failed/skipped + per-offer table counts | AC-W01.12, AC-W02.4 |
| `TestPartialFailure` | 1 of 10 tables fails -> 9 rendered + 1 error marker | AC-W02.1 |
| `TestPartialFailure` | Error markers include table name, type, message | AC-W02.2 |
| `TestTotalFailure` | All 10 tables fail -> no upload, offer marked failed | AC-W02.3 |
| `TestUnusedAssetsFilter` | Correct spend==0 AND imp==0 filter | AC-W03.9 |
| `TestDeleteFailureTolerance` | Delete failure is non-fatal | (pattern from ConvAudit) |
| `TestEmptyProject` | Zero offers -> total=0, clean result | (edge case) |

#### `test_insights_formatter.py` -- Formatter Tests

| Test Class | Scenario | ACs Covered |
|-----------|----------|-------------|
| `TestPipeTable` | Valid markdown pipe table output | AC-W03.1, AC-W03.3, AC-W03.6 |
| `TestHeader` | Masked phone, business name, vertical, timestamp | AC-W03.2 |
| `TestColumnNames` | snake_case -> Title Case conversion | AC-W03.4 |
| `TestNullHandling` | Null values render as `---` | AC-W03.5 |
| `TestNullColumns` | Always-null columns present (out_calls, etc.) | AC-W03.5 |
| `TestEmptyTable` | Zero rows -> "No data available" | AC-W03.7 |
| `TestUnusedAssetsEmpty` | Zero matching -> "No unused assets found" | AC-W03.7 |
| `TestFooter` | Duration, table count, error count, version | AC-W03.8 |
| `TestRowLimit` | Truncation note when limit reached | AC-W03.10 |
| `TestErrorMarker` | Error marker format `> [ERROR] type: message` | AC-W02.2, AC-W02.5 |
| `TestComposeReport` | Full report composition with mixed results | AC-W03.1 |

#### `test_client_extensions.py` -- DataServiceClient Tests

| Test Class | Scenario | ACs Covered |
|-----------|----------|-------------|
| `TestGetAppointmentsAsync` | Returns appointment rows with PII masking | AC-W04.1, AC-W04.10 |
| `TestGetAppointmentsAsync` | Respects circuit breaker + retry | AC-W04.2 |
| `TestGetLeadsAsync` | Returns lead rows excluding appointments | AC-W04.3, AC-W04.10 |
| `TestGetLeadsAsync` | Respects circuit breaker + retry | AC-W04.4 |
| `TestNormalizePeriod` | `"quarter"` -> `"QUARTER"` | AC-W04.5 |
| `TestNormalizePeriod` | `"month"` -> `"MONTH"` | AC-W04.6 |
| `TestNormalizePeriod` | `"week"` -> `"WEEK"` | AC-W04.7 |
| `TestNormalizePeriod` | Existing periods unchanged | AC-W04.8 |
| `TestInsightsRequestValidation` | `InsightsRequest(insights_period="quarter")` passes | AC-W04.9 |

#### `test_insights_export.py` (Lambda handler) -- Handler Tests

| Test Class | Scenario | ACs Covered |
|-----------|----------|-------------|
| `TestHandlerModule` | Module exists and importable | AC-W05.1 |
| `TestHandlerPattern` | Follows asyncio.run / _handler_async / _execute pattern | AC-W05.2 |
| `TestHandlerRegistration` | Registered in `__init__.py` | AC-W05.3 |
| `TestHandlerValidation` | Returns `status: skipped` when disabled | AC-W05.5 |
| `TestHandlerExecution` | Returns structured JSON with all required fields | AC-W05.9 |
| `TestHandlerError` | Returns `statusCode: 500` on unexpected error | AC-W05.2 |

### 9.3 Key Test Patterns

The test fixtures follow the `_make_workflow()` helper pattern from ConversationAuditWorkflow tests:

```python
def _make_export_workflow(
    offers: list[MagicMock] | None = None,
    parent_tasks: dict[str, MagicMock] | None = None,
    insights_responses: dict[str, InsightsResponse] | None = None,
    insights_errors: dict[str, Exception] | None = None,
    existing_attachments: dict[str, list[MagicMock]] | None = None,
) -> tuple[InsightsExportWorkflow, MagicMock, MagicMock, MagicMock]:
    """Build an InsightsExportWorkflow with configured mocks."""
    ...
```

For the formatter tests, no mocks are needed -- the formatter is pure functions taking data in and producing strings out.

---

## 10. Architecture Decision Records

### ADR-EXPORT-001: Separate Formatter Module

**Status**: Accepted

**Context**: The markdown formatting logic (pipe tables, headers, footers, error markers, null handling, column name mapping) could live inline in the workflow module or in a separate module.

**Decision**: Create `automation/workflows/insights_formatter.py` as a separate module.

**Rationale**:
1. **Testability**: The formatter contains ~8 distinct formatting functions. Testing these as pure functions (data in, string out) with no mocking is dramatically simpler than testing them through the workflow mock harness.
2. **Separation of concerns**: The workflow module owns the fetch-compose-upload lifecycle. The formatter owns how data becomes markdown. These are independent concerns.
3. **Future reuse**: If additional markdown report workflows are added (e.g., reconciliation reports in Phase 2), the formatter patterns can be extracted to a shared utility.
4. **Size management**: The workflow module is already substantial (~400 lines). Adding ~200 lines of formatting inline would make it harder to navigate.

**Consequences**:
- One additional module to maintain
- Clear import dependency: `insights_export.py` imports from `insights_formatter.py`
- Formatter is stateless and has no side effects

### ADR-EXPORT-002: Shared Asset API Call Optimization

**Status**: Accepted

**Context**: The PRD specifies 10 tables but only 9 API calls. Table 8 (ASSET TABLE) and Table 10 (UNUSED ASSETS) both use `POST /insights` with `frame_type=asset, period=T30`. Making two identical API calls is wasteful.

**Decision**: Make a single API call for ASSET TABLE. Derive UNUSED ASSETS by client-side filtering the same response data.

**Rationale**:
1. **Efficiency**: Eliminates one HTTP round-trip per offer (saves ~200ms P50 per offer)
2. **Consistency**: Both tables always reflect the same data snapshot
3. **Simplicity**: The filter (`spend == 0 AND imp == 0`) is trivial to apply client-side
4. **PRD alignment**: PRD Appendix 11 explicitly states "Same API call as ASSET TABLE; client-side filter"

**Implementation**:
- `_fetch_all_tables()` dispatches 9 `asyncio.gather()` calls (not 10)
- After gather completes, the ASSET TABLE result is used to derive UNUSED ASSETS
- If ASSET TABLE fails, UNUSED ASSETS inherits the failure
- The `TableResult` for UNUSED ASSETS is constructed post-gather

**Consequences**:
- UNUSED ASSETS cannot fail independently from ASSET TABLE
- If ASSET TABLE returns an empty response, UNUSED ASSETS is also empty (renders "No unused assets found")
- The derivation step is synchronous and O(n) in the number of asset rows

### ADR-EXPORT-003: Configurable Row Limits via Params Dict

**Status**: Accepted

**Context**: Row limits (APPOINTMENTS: 100, LEADS: 100) need to be configurable. Three approaches were considered:
1. Module-level constants (not configurable at runtime)
2. Constructor parameters on the workflow class
3. Params dict entries (same pattern as `max_concurrency`)

**Decision**: Use the params dict with a `row_limits` key, defaulting to `DEFAULT_ROW_LIMITS`.

**Rationale**:
1. **Consistency**: `max_concurrency` and `attachment_pattern` are already passed via params. Row limits follow the same pattern.
2. **Runtime override**: Lambda event payloads can override row limits for specific runs (e.g., `{"row_limits": {"APPOINTMENTS": 50}}` for a debugging run).
3. **No code change for tuning**: Changing row limits does not require a code deployment -- just update the EventBridge event payload or Lambda environment.
4. **Backward-compatible defaults**: The `DEFAULT_ROW_LIMITS` dict provides sensible defaults when not overridden.

**Implementation**:
```python
row_limits = params.get("row_limits", DEFAULT_ROW_LIMITS)
```

The formatter receives `row_limits` and applies them per-table during `_format_table_section()`.

**Consequences**:
- Row limits are stringly-keyed (table name -> int). Typos in table names silently fall through to "no limit". This is acceptable because the default handles the common case.
- Tables without explicit limits (BY QUARTER, BY MONTH, etc.) render all rows from the API.

---

## 11. Observability

All structured logging follows the pattern established by ConversationAuditWorkflow. Log event names are prefixed with `insights_export_` for filtering.

| Log Event | When | Fields |
|-----------|------|--------|
| `insights_export_started` | Workflow begins | `total_offers`, `max_concurrency` |
| `insights_export_offer_started` | Per-offer processing begins | `offer_gid`, `office_phone` (masked), `vertical` |
| `insights_export_table_fetched` | Per-table fetch succeeds | `offer_gid`, `table_name`, `row_count`, `duration_ms` |
| `insights_export_table_failed` | Per-table fetch fails | `offer_gid`, `table_name`, `error_type`, `error_message` |
| `insights_export_offer_succeeded` | Per-offer processing succeeds | `offer_gid`, `tables_succeeded`, `tables_failed`, `duration_ms` |
| `insights_export_offer_failed` | All tables failed for offer | `offer_gid`, `error_count` |
| `insights_export_offer_skipped` | Offer skipped (no resolution) | `offer_gid`, `reason` |
| `insights_export_upload_succeeded` | Attachment uploaded | `offer_gid`, `filename`, `size_bytes` |
| `insights_export_old_attachment_deleted` | Old attachment cleaned up | `offer_gid`, `attachment_gid`, `attachment_name` |
| `insights_export_completed` | Workflow finishes | `total`, `succeeded`, `failed`, `skipped`, `total_tables_succeeded`, `total_tables_failed`, `duration_seconds` |

PII masking: `office_phone` is masked via `mask_phone_number()` in all log output. The raw phone is only passed to DataServiceClient API calls (required for lookup).

---

## 12. Security

- **PII masking**: `mask_phone_number()` from `clients/data/client.py` is used for all log output and the markdown report header. Raw phone numbers are only sent to autom8_data API calls.
- **Auth**: DataServiceClient uses existing S2S JWT / API key authentication (no changes needed).
- **No secrets in Lambda events**: Event payloads contain only override parameters (concurrency, row limits), never credentials.
- **Attachment content**: The markdown report contains business data (metrics, names) but no authentication credentials or PII beyond the masked phone number in the header.

---

## 13. Performance

| Metric | Target | Rationale |
|--------|--------|-----------|
| Single offer (10 fetches + compose + upload) | P95 < 10s | 9 parallel API calls (~2s each) + compose (~50ms) + upload (~500ms) |
| Full workflow (100 offers, concurrency=5) | P95 < 5 min | 100 offers / 5 concurrent = 20 batches * ~10s = ~200s |
| Markdown composition | < 100ms per offer | String concatenation, no I/O |
| Lambda timeout | 15 minutes (900s) | Well above P95 for typical offer counts |

The `asyncio.gather()` for per-offer table fetches ensures all 9 API calls run in parallel. The semaphore controls inter-offer concurrency (default 5).

---

## 14. Deployment Configuration

### EventBridge Rule

```json
{
  "ScheduleExpression": "cron(0 11 * * ? *)",
  "Description": "Trigger InsightsExportWorkflow at 6 AM ET daily (11:00 UTC EST / 10:00 UTC EDT)",
  "State": "ENABLED",
  "Targets": [{
    "Arn": "arn:aws:lambda:...:insights_export_handler",
    "Input": "{}"
  }]
}
```

Note: The cron uses `11:00 UTC` which is `6:00 AM EST`. During EDT, this fires at `7:00 AM ET`. If exact 6 AM ET is required year-round, the rule needs adjustment for DST. The PRD specifies 6 AM ET and the cron expression `cron(0 11 * * ? *)`.

### Lambda Configuration

| Setting | Value |
|---------|-------|
| Handler | `autom8_asana.lambda_handlers.insights_export.handler` |
| Runtime | Python 3.12 |
| Timeout | 900 seconds (15 minutes) |
| Memory | 512 MB (same as conversation_audit) |
| Feature flag | `AUTOM8_EXPORT_ENABLED` (default: enabled) |

---

## 15. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Appointments/leads endpoints unavailable | Medium | Low | Per-table error isolation renders error markers; 8/10 tables still work |
| Large offer count (>500) exceeds Lambda timeout | Low | Medium | Semaphore concurrency control; Lambda timeout is 15 min; monitor first runs |
| Asset_score column missing from API response | Expected | None | Formatter dynamically builds columns from data; column appears when available |
| Asana rate limiting during attachment upload | Low | Medium | Semaphore limits concurrent offers; Asana client has built-in retry |
| Legacy `run_export` overlap during cutover | Low | Low | Hard cutover: disable legacy rule before enabling new rule |
| Markdown rendering issues in Asana preview | Low | Medium | Asana supports standard markdown pipe tables (confirmed in PRD) |

---

## 16. Handoff Checklist

- [x] TDD covers all 5 PRD work items (W01-W05) and all 47 acceptance criteria
- [x] Component boundaries and responsibilities are clear (workflow, formatter, client, handler)
- [x] Data model defined (TableResult, InsightsReportData, _OfferOutcome, WorkflowResult.metadata)
- [x] API contracts specified (method signatures with full type annotations)
- [x] ADRs document all significant decisions (3 ADRs)
- [x] Risks identified with mitigations (6 risks)
- [x] Implementation sequencing defined with rationale
- [x] Test strategy maps every scenario to specific ACs from the PRD
- [x] YELLOW dependencies documented with degradation paths
- [x] Principal Engineer can implement directly from this document without architectural questions

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-insights-export-workflow.md` | Written 2026-02-12 |
| PRD (input) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-insights-export-workflow.md` | Read-verified |
| WorkflowAction ABC | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/base.py` | Read-verified |
| ConversationAuditWorkflow | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/conversation_audit.py` | Read-verified |
| DataServiceClient | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py` | Read-verified |
| DataServiceClient models | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/models.py` | Read-verified |
| Lambda handler pattern | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/conversation_audit.py` | Read-verified |
| Lambda __init__ | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/__init__.py` | Read-verified |
| WorkflowRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/registry.py` | Read-verified |
| Workflows __init__ | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/__init__.py` | Read-verified |
| ResolutionContext | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/resolution/context.py` | Read-verified |
| mask_phone_number | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py` (line 79) | Read-verified |
| Offer model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/offer.py` | Read-verified |
| Offer PRIMARY_PROJECT_GID | `"1143843662099250"` (confirmed in `core/project_registry.py`) | Read-verified |
| ConversationAudit tests | `/Users/tomtenuta/Code/autom8_asana/tests/unit/automation/workflows/test_conversation_audit.py` | Read-verified |
| TDD-lifecycle-engine (format reference) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-lifecycle-engine.md` | Read-verified |
