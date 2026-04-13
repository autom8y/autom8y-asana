"""Conversation audit workflow -- weekly CSV refresh for ContactHolders.

Per TDD-CONV-AUDIT-001 Section 3.8: First WorkflowAction implementation.
Enumerates active ContactHolders, resolves each to a Business office_phone,
fetches 30-day conversation CSV from autom8_data, and replaces the
attachment on each ContactHolder task.

Per ADR-bridge-intermediate-base-class: Rebased onto
BridgeWorkflowAction in sprint-4.
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass as _dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autom8_asana.clients.attachments import AttachmentsClient
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.core.scope import EntityScope
    from autom8_asana.models.business.activity import AccountActivity

from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import (
    WorkflowItemError,
    WorkflowResult,
)
from autom8_asana.automation.workflows.bridge_base import (
    BridgeOutcome,
    BridgeWorkflowAction,
)
from autom8_asana.clients.utils.pii import mask_phone_number
from autom8_asana.errors import ExportError
from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.models.business.contact import ContactHolder
from autom8_asana.models.business.hydration import hydrate_from_gid_async
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


class ConversationAuditWorkflow(BridgeWorkflowAction):
    """Weekly conversation audit CSV refresh for ContactHolders.

    Per PRD REQ-F18: First concrete WorkflowAction implementation.
    Per ADR-bridge-intermediate-base-class: Inherits from
    BridgeWorkflowAction (sprint-4 migration).

    Lifecycle:
    1. Check feature flag (AUTOM8_AUDIT_ENABLED) -- inherited
    2. Check data source health -- inherited
    3. Enumerate active ContactHolder tasks in PRIMARY_PROJECT_GID
    4. For each ContactHolder (with concurrency limit):
       a. Check parent Business activity (skip if not ACTIVE)
       b. Resolve parent Business -> office_phone
       c. Fetch CSV from DataServiceClient.get_export_csv_async()
       d. Upload new CSV attachment (upload-first)
       e. Delete old matching CSV attachments
    5. Return WorkflowResult with per-item tracking

    Args:
        asana_client: AsanaClient for Asana API operations.
        data_client: DataServiceClient for autom8_data CSV export.
        attachments_client: AttachmentsClient for upload/delete operations.
    """

    feature_flag_env_var = AUDIT_ENABLED_ENV_VAR

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
        self._activity_map: dict[str, AccountActivity | None] = {}

    @property
    def workflow_id(self) -> str:  # type: ignore[override]  # read-only property overrides base attribute
        return "conversation-audit"

    # --- Bridge hooks ---

    async def enumerate_async(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Enumerate ContactHolder entities based on scope.

        Per TDD-ENTITY-SCOPE-001 Section 2.5.1:
        When scope.has_entity_ids: return synthetic holder dicts for each GID.
            Skips bulk pre-resolution (single entity does not benefit).
        When scope is empty: perform full enumeration + bulk pre-resolution
            + pre-filter by business activity.

        Overrides base to add targeted logging, custom dict shape with
        parent_gid/parent fields, and activity pre-filtering.

        Args:
            scope: EntityScope controlling targeting, filtering, and limits.

        Returns:
            List of holder dicts with {gid, name, parent_gid, parent} shape.
        """
        if scope.has_entity_ids:
            holders = [
                {"gid": gid, "name": None, "parent_gid": None, "parent": None}
                for gid in scope.entity_ids
            ]
            logger.info(
                "conversation_audit_targeted",
                entity_ids=scope.entity_ids,
                dry_run=scope.dry_run,
            )
            return holders

        # Full enumeration
        holders = await self._enumerate_contact_holders()

        # Bulk pre-resolve Business activities
        await self._pre_resolve_business_activities(holders)

        # Pre-filter holders with inactive parent Businesses
        active_holders: list[dict[str, Any]] = []
        for h in holders:
            parent_gid = h.get("parent_gid")
            if parent_gid:
                activity = self._activity_map.get(parent_gid)
                if activity != AccountActivity.ACTIVE:
                    continue
            active_holders.append(h)

        logger.info(
            "conversation_audit_enumerated",
            total_holders=len(holders),
            active_holders=len(active_holders),
            skipped_inactive=len(holders) - len(active_holders),
        )

        # Apply limit if provided
        if scope.limit is not None and len(active_holders) > scope.limit:
            active_holders = active_holders[: scope.limit]

        return active_holders

    async def enumerate_entities(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Full enumeration path (not used -- enumerate_async overridden).

        This bridge overrides enumerate_async() directly to handle the
        custom dict shape and activity pre-filtering. This method exists
        only to satisfy the abstract contract.

        Per ADR-bridge-intermediate-base-class: Subclasses that override
        enumerate_async() may implement this as a no-op.
        """
        return await self._enumerate_contact_holders()

    async def process_entity(
        self,
        entity: dict[str, Any],
        params: dict[str, Any],
    ) -> _HolderOutcome:
        """Dispatch to _process_holder with params extraction.

        Per ADR-bridge-intermediate-base-class: Implements the abstract
        hook called by base class execute_async() for each entity.
        """
        date_range_days = params.get("date_range_days", DEFAULT_DATE_RANGE_DAYS)
        end_date = date.today()
        start_date = end_date - timedelta(days=date_range_days)

        return await self._process_holder(
            holder_gid=entity["gid"],
            holder_name=entity.get("name"),
            parent_gid=entity.get("parent_gid"),
            attachment_pattern=params.get(
                "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
            ),
            start_date=start_date,
            end_date=end_date,
            dry_run=params.get("dry_run", False),
        )

    async def execute_async(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> WorkflowResult:
        """Execute the conversation audit for the given entities.

        Overrides base to add start/completion logging that preserves
        existing observability events.

        Args:
            entities: Holder dicts from enumerate_async.
                Shape: [{gid, name, parent_gid, parent}, ...]
            params: Configuration parameters:
                - date_range_days (int): Export window, default 30
                - attachment_pattern (str): Glob for old attachment cleanup
                - max_concurrency (int): Parallel processing limit, default 5
                - dry_run (bool): Skip write operations

        Returns:
            WorkflowResult with total/succeeded/failed/skipped counts.
        """
        max_concurrency = params.get("max_concurrency", DEFAULT_MAX_CONCURRENCY)
        dry_run = params.get("dry_run", False)

        logger.info(
            "conversation_audit_started",
            total_holders=len(entities),
            max_concurrency=max_concurrency,
            dry_run=dry_run,
        )

        result = await super().execute_async(entities, params)

        # Inject dry_run flag into metadata (matches pre-migration behavior)
        if dry_run:
            result.metadata["dry_run"] = True
        else:
            # csv_row_count is only included in metadata during dry_run
            result.metadata.pop("csv_row_count", None)

        logger.info(
            "conversation_audit_completed",
            total=result.total,
            succeeded=result.succeeded,
            failed=result.failed,
            skipped=result.skipped,
            truncated=result.metadata.get("truncated_count", 0),
            activity_skipped=result.metadata.get("activity_skipped_count", 0),
            duration_seconds=round(result.duration_seconds, 2),
        )

        return result

    def _build_result_metadata(
        self,
        outcomes: list[BridgeOutcome],
    ) -> dict[str, Any]:
        """Build audit-specific metadata: truncation + activity skip counts.

        Also includes dry-run CSV row counts when applicable.
        """
        truncated_count = sum(
            1 for o in outcomes if isinstance(o, _HolderOutcome) and o.truncated
        )
        activity_skipped = sum(
            1
            for o in outcomes
            if o.status == "skipped"
            and o.reason in ("business_not_active", "activity_unknown")
        )

        metadata: dict[str, Any] = {
            "truncated_count": truncated_count,
            "activity_skipped_count": activity_skipped,
        }

        # Check if any outcome has dry_run info (csv_row_count populated)
        row_counts = {
            o.gid: o.csv_row_count
            for o in outcomes
            if isinstance(o, _HolderOutcome) and o.csv_row_count is not None
        }
        if row_counts:
            metadata["csv_row_count"] = row_counts

        return metadata

    # --- Private Methods ---

    async def _enumerate_contact_holders(self) -> list[dict[str, Any]]:
        """List all active (non-completed) tasks in the ContactHolder project.

        Uses paginated task listing with completed_since=now filter to
        exclude completed/archived ContactHolders.

        Returns:
            List of task dicts with {gid, name, parent_gid} fields.
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
        parent_gid: str | None = None,
        attachment_pattern: str = DEFAULT_ATTACHMENT_PATTERN,
        start_date: date | None = None,
        end_date: date | None = None,
        dry_run: bool = False,
    ) -> _HolderOutcome:
        """Process a single ContactHolder: resolve phone, fetch CSV, replace attachment.

        Per PRD REQ-F07: Errors are captured per-item; batch continues.

        Args:
            holder_gid: ContactHolder task GID.
            holder_name: ContactHolder task name (for logging).
            parent_gid: Parent Business GID if known from enumeration.
            attachment_pattern: Glob pattern for old attachment cleanup.
            start_date: Export date range start.
            end_date: Export date range end.
            dry_run: If True, skip upload and delete operations.

        Returns:
            _HolderOutcome with status and optional error.
        """
        try:
            # Step 0: Activity gate -- skip if parent Business is not ACTIVE
            if parent_gid:
                activity = await self._resolve_business_activity(parent_gid)
                if activity != AccountActivity.ACTIVE:
                    reason = (
                        "activity_unknown"
                        if activity is None
                        else "business_not_active"
                    )
                    logger.info(
                        "holder_skipped_inactive_business",
                        holder_gid=holder_gid,
                        holder_name=holder_name,
                        business_gid=parent_gid,
                        activity=activity.value if activity else None,
                    )
                    return _HolderOutcome(
                        gid=holder_gid,
                        status="skipped",
                        reason=reason,
                    )

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
                    gid=holder_gid,
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
                    gid=holder_gid,
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
                    gid=holder_gid,
                    status="skipped",
                    reason="zero_rows",
                )

            # Step D: Upload-first attachment replacement (REQ-F04)
            if not dry_run:
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
            else:
                logger.info(
                    "conversation_audit_dry_run_skip_write",
                    holder_gid=holder_gid,
                )

            logger.info(
                "holder_succeeded",
                holder_gid=holder_gid,
                office_phone=masked,
                row_count=export.row_count,
                truncated=export.truncated,
                dry_run=dry_run,
            )

            return _HolderOutcome(
                gid=holder_gid,
                status="succeeded",
                truncated=export.truncated,
                csv_row_count=export.row_count,
            )

        except Exception as exc:  # BROAD-CATCH: boundary -- holder processing failure returns failed outcome
            logger.error(
                "holder_processing_error",
                holder_gid=holder_gid,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return _HolderOutcome(
                gid=holder_gid,
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
class _HolderOutcome(BridgeOutcome):
    """Internal per-holder processing result.

    Extends BridgeOutcome with audit-specific fields for truncation
    tracking and CSV row counts.
    """

    # Inherited from BridgeOutcome: gid, status, reason, error
    truncated: bool = False
    csv_row_count: int | None = None

    @property
    def holder_gid(self) -> str:
        """Alias for gid -- backward compatibility with log/metadata consumers."""
        return self.gid
