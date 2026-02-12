"""Conversation audit workflow -- weekly CSV refresh for ContactHolders.

Per TDD-CONV-AUDIT-001 Section 3.8: First WorkflowAction implementation.
Enumerates active ContactHolders, resolves each to a Business office_phone,
fetches 30-day conversation CSV from autom8_data, and replaces the
attachment on each ContactHolder task.
"""

from __future__ import annotations

import asyncio
import io
import os
from dataclasses import dataclass as _dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.mixins import AttachmentReplacementMixin
from autom8_asana.clients.attachments import AttachmentsClient
from autom8_asana.clients.data.client import DataServiceClient, mask_phone_number
from autom8_asana.exceptions import ExportError
from autom8_asana.models.business.contact import ContactHolder
from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)

# Feature flag environment variable
AUDIT_ENABLED_ENV_VAR = "AUTOM8_AUDIT_ENABLED"

# ContactHolder project GID (canonical source: ContactHolder.PRIMARY_PROJECT_GID)
CONTACT_HOLDER_PROJECT_GID = ContactHolder.PRIMARY_PROJECT_GID

# Default concurrency for parallel processing
DEFAULT_MAX_CONCURRENCY = 5

# Default attachment pattern for cleanup
DEFAULT_ATTACHMENT_PATTERN = "conversations_*.csv"

# Default date range for export (days)
DEFAULT_DATE_RANGE_DAYS = 30


class ConversationAuditWorkflow(AttachmentReplacementMixin, WorkflowAction):
    """Weekly conversation audit CSV refresh for ContactHolders.

    Per PRD REQ-F18: First concrete WorkflowAction implementation.

    Lifecycle:
    1. Check feature flag (AUTOM8_AUDIT_ENABLED)
    2. Enumerate active ContactHolder tasks in PRIMARY_PROJECT_GID
    3. For each ContactHolder (with concurrency limit):
       a. Resolve parent Business -> office_phone
       b. Fetch CSV from DataServiceClient.get_export_csv_async()
       c. Upload new CSV attachment (upload-first)
       d. Delete old matching CSV attachments
    4. Return WorkflowResult with per-item tracking

    Args:
        asana_client: AsanaClient for Asana API operations.
        data_client: DataServiceClient for autom8_data CSV export.
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
        return "conversation-audit"

    async def validate_async(self) -> list[str]:
        """Pre-flight validation.

        Checks:
        1. Feature flag is enabled.
        2. DataServiceClient is reachable (circuit breaker not open).

        Returns:
            List of validation error strings (empty = ready).
        """
        errors: list[str] = []

        # Check feature flag
        env_value = os.environ.get(AUDIT_ENABLED_ENV_VAR, "").lower()
        if env_value in {"false", "0", "no"}:
            errors.append(f"Workflow disabled via {AUDIT_ENABLED_ENV_VAR}={env_value}")
            return errors  # Short-circuit; no point checking other things

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
        """Execute the full conversation audit cycle.

        Args:
            params: YAML-configured parameters:
                - workflow_id (str): "conversation-audit"
                - date_range_days (int): Export window, default 30
                - attachment_pattern (str): Glob for old attachment cleanup
                - max_concurrency (int): Parallel processing limit, default 5

        Returns:
            WorkflowResult with total/succeeded/failed/skipped counts.
        """
        started_at = datetime.now(UTC)

        max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        attachment_pattern = params.get(
            "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
        )
        date_range_days = params.get("date_range_days", DEFAULT_DATE_RANGE_DAYS)

        # Compute export date window from date_range_days
        end_date = date.today()
        start_date = end_date - timedelta(days=date_range_days)

        # Step 1: Enumerate active ContactHolders
        holders = await self._enumerate_contact_holders()

        logger.info(
            "conversation_audit_started",
            total_holders=len(holders),
            max_concurrency=max_concurrency,
        )

        # Step 2: Process each holder with concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[_HolderOutcome] = []

        async def process_one(holder_gid: str, holder_name: str | None) -> None:
            async with semaphore:
                outcome = await self._process_holder(
                    holder_gid=holder_gid,
                    holder_name=holder_name,
                    attachment_pattern=attachment_pattern,
                    start_date=start_date,
                    end_date=end_date,
                )
                results.append(outcome)

        await asyncio.gather(*[process_one(h["gid"], h.get("name")) for h in holders])

        # Step 3: Aggregate results
        succeeded = sum(1 for r in results if r.status == "succeeded")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        truncated_count = sum(1 for r in results if r.truncated)
        errors = [r.error for r in results if r.error is not None]

        completed_at = datetime.now(UTC)

        workflow_result = WorkflowResult(
            workflow_id=self.workflow_id,
            started_at=started_at,
            completed_at=completed_at,
            total=len(holders),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
            metadata={"truncated_count": truncated_count},
        )

        logger.info(
            "conversation_audit_completed",
            total=workflow_result.total,
            succeeded=workflow_result.succeeded,
            failed=workflow_result.failed,
            skipped=workflow_result.skipped,
            truncated=truncated_count,
            duration_seconds=round(workflow_result.duration_seconds, 2),
        )

        return workflow_result

    # --- Private Methods ---

    async def _enumerate_contact_holders(self) -> list[dict[str, Any]]:
        """List all active (non-completed) tasks in the ContactHolder project.

        Uses paginated task listing with completed_since=now filter to
        exclude completed/archived ContactHolders.

        Returns:
            List of task dicts with at least {gid, name, parent} fields.
        """
        page_iterator = self._asana_client.tasks.list_for_project_async(
            CONTACT_HOLDER_PROJECT_GID,
            opt_fields=["name", "completed", "parent", "parent.name"],
            completed_since="now",
        )
        tasks = await page_iterator.collect()
        return [
            {"gid": t.gid, "name": t.name, "parent": t.parent}
            for t in tasks
            if not t.completed
        ]

    async def _process_holder(
        self,
        holder_gid: str,
        holder_name: str | None,
        attachment_pattern: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> _HolderOutcome:
        """Process a single ContactHolder: resolve phone, fetch CSV, replace attachment.

        Per PRD REQ-F07: Errors are captured per-item; batch continues.

        Args:
            holder_gid: ContactHolder task GID.
            holder_name: ContactHolder task name (for logging).
            attachment_pattern: Glob pattern for old attachment cleanup.

        Returns:
            _HolderOutcome with status and optional error.
        """
        try:
            # Step A: Resolve office_phone via parent Business
            office_phone = await self._resolve_office_phone(holder_gid)
            if not office_phone:
                logger.warning(
                    "holder_skipped_no_phone",
                    holder_gid=holder_gid,
                    holder_name=holder_name,
                )
                return _HolderOutcome(
                    holder_gid=holder_gid,
                    status="skipped",
                    reason="no_office_phone",
                )

            # Step B: Fetch CSV export
            masked = mask_phone_number(office_phone)
            try:
                export = await self._data_client.get_export_csv_async(
                    office_phone,
                    start_date=start_date,
                    end_date=end_date,
                )
            except ExportError as e:
                logger.error(
                    "holder_export_failed",
                    holder_gid=holder_gid,
                    office_phone=masked,
                    error=str(e),
                    reason=e.reason,
                )
                return _HolderOutcome(
                    holder_gid=holder_gid,
                    status="failed",
                    error=WorkflowItemError(
                        item_id=holder_gid,
                        error_type=f"export_{e.reason}",
                        message=str(e),
                        recoverable=e.reason != "client_error",
                    ),
                )

            # Step C: Skip if zero data rows (REQ-F06)
            if export.row_count == 0:
                logger.info(
                    "holder_skipped_zero_rows",
                    holder_gid=holder_gid,
                    office_phone=masked,
                )
                return _HolderOutcome(
                    holder_gid=holder_gid,
                    status="skipped",
                    reason="zero_rows",
                )

            # Step D: Upload-first attachment replacement (REQ-F04)
            csv_file = io.BytesIO(export.csv_content)
            await self._attachments_client.upload_async(
                parent=holder_gid,
                file=csv_file,
                name=export.filename,
                content_type="text/csv",
            )

            # Step E: Delete old matching attachments
            await self._delete_old_attachments(
                holder_gid, attachment_pattern, exclude_name=export.filename
            )

            logger.info(
                "holder_succeeded",
                holder_gid=holder_gid,
                office_phone=masked,
                row_count=export.row_count,
                truncated=export.truncated,
            )

            return _HolderOutcome(
                holder_gid=holder_gid,
                status="succeeded",
                truncated=export.truncated,
            )

        except Exception as exc:
            logger.error(
                "holder_processing_error",
                holder_gid=holder_gid,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return _HolderOutcome(
                holder_gid=holder_gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=holder_gid,
                    error_type="unexpected",
                    message=str(exc),
                    recoverable=True,
                ),
            )

    async def _resolve_office_phone(self, holder_gid: str) -> str | None:
        """Resolve ContactHolder -> parent Business -> office_phone.

        Per TDD-CONV-AUDIT-001 Section 4: Uses the Asana parent task
        relationship. ContactHolder is a subtask of Business in the
        holder pattern. Uses ResolutionContext for standardized resolution.

        Args:
            holder_gid: ContactHolder task GID.

        Returns:
            E.164 phone string, or None if parent has no office_phone.
        """
        # Fetch the ContactHolder task to get its parent reference
        holder_task = await self._asana_client.tasks.get_async(
            holder_gid,
            opt_fields=["parent", "parent.gid"],
        )

        if not holder_task.parent or not holder_task.parent.gid:
            return None

        # Use ResolutionContext to resolve Business and extract office_phone
        async with ResolutionContext(
            self._asana_client,
            business_gid=holder_task.parent.gid,
        ) as ctx:
            business = await ctx.business_async()
            return business.office_phone  # Descriptor access


# --- Internal Data Structure ---


@_dataclass
class _HolderOutcome:
    """Internal per-holder processing result."""

    holder_gid: str
    status: str  # "succeeded", "failed", "skipped"
    reason: str | None = None
    error: WorkflowItemError | None = None
    truncated: bool = False
