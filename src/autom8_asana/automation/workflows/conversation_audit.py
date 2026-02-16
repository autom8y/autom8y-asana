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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.models.business.activity import AccountActivity

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
        self._activity_map: dict[str, AccountActivity | None] = {}

    @property
    def workflow_id(self) -> str:  # type: ignore[override]  # read-only property overrides base attribute
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
        except (ConnectionError, TimeoutError, OSError):
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

        # Step 1.5: Bulk pre-resolve Business activities
        await self._pre_resolve_business_activities(holders)

        # Step 1.6: Pre-filter holders with inactive parent Businesses
        from autom8_asana.models.business.activity import AccountActivity

        active_holders: list[dict[str, Any]] = []
        prefiltered: list[_HolderOutcome] = []
        for h in holders:
            parent_gid = h.get("parent_gid")
            if parent_gid:
                activity = self._activity_map.get(parent_gid)
                if activity != AccountActivity.ACTIVE:
                    prefiltered.append(
                        _HolderOutcome(
                            holder_gid=h["gid"],
                            status="skipped",
                            reason="inactive_business",
                        )
                    )
                    continue
            active_holders.append(h)

        logger.info(
            "conversation_audit_started",
            total_holders=len(holders),
            active_holders=len(active_holders),
            skipped_inactive=len(prefiltered),
            max_concurrency=max_concurrency,
        )

        # Step 2: Process each ACTIVE holder with concurrency control
        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[_HolderOutcome] = list(prefiltered)

        async def process_one(
            holder_gid: str,
            holder_name: str | None,
            parent_gid: str | None,
        ) -> None:
            async with semaphore:
                outcome = await self._process_holder(
                    holder_gid=holder_gid,
                    holder_name=holder_name,
                    attachment_pattern=attachment_pattern,
                    start_date=start_date,
                    end_date=end_date,
                    parent_gid=parent_gid,
                )
                results.append(outcome)

        await asyncio.gather(
            *[
                process_one(h["gid"], h.get("name"), h.get("parent_gid"))
                for h in active_holders
            ]
        )

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
        page_iterator = self._asana_client.tasks.list_async(
            project=CONTACT_HOLDER_PROJECT_GID,
            opt_fields=["name", "completed", "parent", "parent.name"],
            completed_since="now",
        )
        tasks = await page_iterator.collect()
        return [
            {
                "gid": t.gid,
                "name": t.name,
                "parent": t.parent,
                "parent_gid": t.parent.gid if t.parent else None,
            }
            for t in tasks
            if not t.completed
        ]

    async def _pre_resolve_business_activities(
        self,
        holders: list[dict[str, Any]],
    ) -> None:
        """Bulk-resolve parent Business activities into _activity_map.

        Extracts unique parent_gids, hydrates each Business to depth=2 in
        parallel (Semaphore(8)), and populates self._activity_map. After
        this call, _resolve_business_activity() is a cache hit for all GIDs.

        Args:
            holders: List of holder dicts with "parent_gid" key.
        """
        unique_gids = {
            h["parent_gid"]
            for h in holders
            if h.get("parent_gid") and h["parent_gid"] not in self._activity_map
        }

        if not unique_gids:
            return

        semaphore = asyncio.Semaphore(8)

        async def resolve_one(gid: str) -> None:
            async with semaphore:
                await self._resolve_business_activity(gid)

        await asyncio.gather(
            *[resolve_one(gid) for gid in unique_gids],
            return_exceptions=True,
        )

    async def _resolve_business_activity(
        self,
        business_gid: str,
    ) -> AccountActivity | None:
        """Resolve the max unit activity for a Business, with dedup caching.

        Fetches the Business task, hydrates its Unit children, and returns
        the highest activity level across all Units. Caches results by
        business_gid to avoid redundant API calls across ContactHolders
        sharing the same parent Business.

        Returns:
            AccountActivity or None if resolution fails.
        """
        if business_gid in self._activity_map:
            return self._activity_map[business_gid]

        try:
            from autom8_asana.models.business.hydration import hydrate_from_gid_async

            result = await hydrate_from_gid_async(
                self._asana_client,
                business_gid,
                hydrate_full=True,  # Business -> UnitHolder -> Units
            )
            if result.business is not None:
                activity = getattr(result.business, "max_unit_activity", None)
            else:
                activity = None
        except Exception:  # BROAD-CATCH: boundary -- activity resolution failure returns None (soft-fail)
            logger.warning(
                "conversation_audit_activity_resolution_failed",
                business_gid=business_gid,
            )
            activity = None

        self._activity_map[business_gid] = activity
        return activity

    async def _process_holder(
        self,
        holder_gid: str,
        holder_name: str | None,
        attachment_pattern: str,
        start_date: date | None = None,
        end_date: date | None = None,
        parent_gid: str | None = None,
    ) -> _HolderOutcome:
        """Process a single ContactHolder: resolve phone, fetch CSV, replace attachment.

        Per PRD REQ-F07: Errors are captured per-item; batch continues.

        Args:
            holder_gid: ContactHolder task GID.
            holder_name: ContactHolder task name (for logging).
            attachment_pattern: Glob pattern for old attachment cleanup.
            parent_gid: Parent Business GID for activity gating.

        Returns:
            _HolderOutcome with status and optional error.
        """
        # Step 0: Activity gate -- skip if parent Business is not ACTIVE
        if parent_gid:
            from autom8_asana.models.business.activity import AccountActivity

            business_activity = await self._resolve_business_activity(parent_gid)
            if business_activity != AccountActivity.ACTIVE:
                logger.debug(
                    "conversation_audit_holder_skipped_inactive",
                    holder_gid=holder_gid,
                    business_gid=parent_gid,
                    activity=str(business_activity) if business_activity else "unknown",
                )
                return _HolderOutcome(
                    holder_gid=holder_gid,
                    status="skipped",
                    reason="inactive_business",
                )

        try:
            # Step A: Resolve office_phone via parent Business
            office_phone = await self._resolve_office_phone(
                holder_gid, parent_gid=parent_gid
            )
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

        except Exception as exc:  # BROAD-CATCH: boundary -- holder processing failure returns failed outcome
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

    async def _resolve_office_phone(
        self,
        holder_gid: str,
        parent_gid: str | None = None,
    ) -> str | None:
        """Resolve ContactHolder -> parent Business -> office_phone.

        Per TDD-CONV-AUDIT-001 Section 4: Uses the Asana parent task
        relationship. ContactHolder is a subtask of Business in the
        holder pattern. Uses ResolutionContext for standardized resolution.

        Args:
            holder_gid: ContactHolder task GID.
            parent_gid: Pre-resolved parent Business GID. When provided,
                skips the holder task fetch (saves 1 API call per holder).

        Returns:
            E.164 phone string, or None if parent has no office_phone.
        """
        business_gid = parent_gid

        if business_gid is None:
            # Fall back to fetching the holder task for its parent reference
            holder_task = await self._asana_client.tasks.get_async(
                holder_gid,
                opt_fields=["parent", "parent.gid"],
            )

            if not holder_task.parent or not holder_task.parent.gid:
                return None

            business_gid = holder_task.parent.gid

        # Use ResolutionContext to resolve Business and extract office_phone
        async with ResolutionContext(
            self._asana_client,
            business_gid=business_gid,
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
