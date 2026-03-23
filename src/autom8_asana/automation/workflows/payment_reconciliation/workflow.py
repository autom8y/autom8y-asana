"""Payment reconciliation workflow -- weekly Excel report for Unit tasks.

Per TDD-data-attachment-bridge-platform Section 7.
Per ADR-bridge-intermediate-base-class: Third bridge built on
BridgeWorkflowAction platform (sprint-5, Workstream C validation).

Enumerates Unit tasks, resolves each to office_phone + vertical via
2-hop (Unit -> UnitHolder -> Business), fetches reconciliation data
from autom8_data, formats as multi-sheet Excel workbook, and uploads
as attachment to each Unit task.
"""

from __future__ import annotations

import io
from dataclasses import dataclass as _dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger
from autom8y_telemetry import trace_reconciliation

from autom8_asana.automation.workflows.bridge_base import (
    BridgeOutcome,
    BridgeWorkflowAction,
)
from autom8_asana.automation.workflows.payment_reconciliation.formatter import (
    compose_excel,
)
from autom8_asana.clients.utils.pii import mask_phone_number
from autom8_asana.models.business.unit import Unit
from autom8_asana.resolution.context import ResolutionContext

if TYPE_CHECKING:
    from autom8_asana.clients.attachments import AttachmentsClient
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.core.scope import EntityScope

logger = get_logger(__name__)

# Feature flag environment variable
RECONCILIATION_ENABLED_ENV_VAR = "AUTOM8_RECONCILIATION_ENABLED"

# Unit project GID (canonical source: Unit.PRIMARY_PROJECT_GID)
UNIT_PROJECT_GID: str = Unit.PRIMARY_PROJECT_GID  # type: ignore[assignment]

# Default concurrency for parallel unit processing
DEFAULT_MAX_CONCURRENCY = 5

# Default attachment pattern for cleanup
DEFAULT_ATTACHMENT_PATTERN = "reconciliation_*.xlsx"

# Default lookback window (days) for reconciliation data
DEFAULT_LOOKBACK_DAYS = 30

# Excel content type
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class PaymentReconciliationWorkflow(BridgeWorkflowAction):
    """Weekly payment reconciliation Excel report for Unit tasks.

    Per TDD-data-attachment-bridge-platform Section 7.
    Per ADR-bridge-intermediate-base-class: Inherits from
    BridgeWorkflowAction (sprint-5, built on extracted platform).

    Lifecycle:
    1. Check feature flag (AUTOM8_RECONCILIATION_ENABLED) -- inherited
    2. Check data source health -- inherited
    3. Enumerate Unit tasks in Business Units project
    4. For each Unit (with concurrency limit):
       a. Resolve Unit -> UnitHolder -> Business (2-hop)
       b. Fetch reconciliation data from DataServiceClient
       c. Format as multi-sheet Excel workbook via ExcelFormatEngine
       d. Upload new .xlsx attachment (upload-first)
       e. Delete old matching .xlsx attachments
    5. Return WorkflowResult with per-item tracking -- inherited
    """

    feature_flag_env_var = RECONCILIATION_ENABLED_ENV_VAR

    def __init__(
        self,
        asana_client: Any,
        data_client: DataServiceClient,
        attachments_client: AttachmentsClient,
    ) -> None:
        super().__init__(asana_client, data_client, attachments_client)
        # Narrow type for mypy: base class stores DataSource | None,
        # but this bridge always has a concrete DataServiceClient.
        self._data_client: DataServiceClient = data_client
        # Per-run cache: business_gid -> (office_phone, vertical, business_name) | None
        # Per Obligation 5: required, keyed by business_gid, not persisted across runs.
        self._business_cache: dict[str, tuple[str, str, str | None] | None] = {}

    @property
    def workflow_id(self) -> str:  # type: ignore[override]  # read-only property overrides base attribute
        return "payment-reconciliation"

    # --- Bridge hooks ---

    async def enumerate_entities(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Full enumeration: fetch non-completed Units from Business Units project.

        Per ADR-bridge-intermediate-base-class: Implements the abstract
        hook called by base class enumerate_async() for the full path.
        Fast-path (scope.has_entity_ids) and limit truncation handled by base.

        Args:
            scope: EntityScope (entity_ids will be empty on this path).

        Returns:
            List of unit dicts with {gid, name, parent_gid} shape.
        """
        opt_fields = ["name", "completed", "parent", "parent.gid"]

        # Forward-compatibility: if section_filter is provided, include
        # memberships for client-side filtering.
        if scope.section_filter:
            opt_fields.append("memberships.section.name")

        page_iterator = self._asana_client.tasks.list_async(
            project=UNIT_PROJECT_GID,
            opt_fields=opt_fields,
            completed_since="now",
        )
        tasks = await page_iterator.collect()

        entities: list[dict[str, Any]] = []
        for t in tasks:
            if t.completed:
                continue

            # Section filter (forward-compat accommodation, not current req)
            if scope.section_filter:
                task_sections = set()
                for m in getattr(t, "memberships", []) or []:
                    section = getattr(m, "section", None)
                    if section:
                        section_name = getattr(section, "name", None)
                        if section_name:
                            task_sections.add(section_name)
                if not task_sections & scope.section_filter:
                    continue

            entities.append(
                {
                    "gid": t.gid,
                    "name": t.name,
                    "parent_gid": t.parent.gid if t.parent else None,
                }
            )

        logger.info(
            "payment_reconciliation_enumerated",
            total_units=len(entities),
        )

        return entities

    @trace_reconciliation("payment_reconciliation.process_entity", engine="autom8y-asana")
    async def process_entity(
        self,
        entity: dict[str, Any],
        params: dict[str, Any],
    ) -> _UnitOutcome:
        """Process a single Unit: resolve, fetch, format, upload, cleanup.

        Per ADR-bridge-intermediate-base-class: Implements the abstract
        hook called by base class execute_async() for each entity.
        Per H-006: Instrumented with trace_reconciliation for standardized
        observability across bridge pipeline stages.

        Args:
            entity: Unit dict with {gid, name, parent_gid}.
            params: Configuration parameters including lookback_days,
                attachment_pattern, dry_run.

        Returns:
            _UnitOutcome with processing result.
        """
        unit_gid = entity["gid"]
        unit_name = entity.get("name")

        # Step 1: Resolve to Business (2-hop: Unit -> UnitHolder -> Business)
        resolution = await self._resolve_unit(unit_gid)
        if resolution is None:
            logger.warning(
                "payment_reconciliation_unit_skipped",
                unit_gid=unit_gid,
                unit_name=unit_name,
                reason="no_resolution",
            )
            return _UnitOutcome(
                gid=unit_gid,
                status="skipped",
                reason="no_resolution",
            )

        office_phone, vertical, business_name = resolution
        masked_phone = mask_phone_number(office_phone)

        logger.info(
            "payment_reconciliation_unit_started",
            unit_gid=unit_gid,
            office_phone=masked_phone,
            vertical=vertical,
        )

        # Step 2: Fetch reconciliation data
        lookback_days = params.get("lookback_days", DEFAULT_LOOKBACK_DAYS)
        response = await self._data_client.get_reconciliation_async(
            office_phone,
            vertical,
            period="monthly",
            window_days=lookback_days,
        )

        if not response.data:
            logger.info(
                "payment_reconciliation_unit_skipped",
                unit_gid=unit_gid,
                office_phone=masked_phone,
                reason="no_data",
            )
            return _UnitOutcome(
                gid=unit_gid,
                status="skipped",
                reason="no_data",
            )

        # Step 3: Format as Excel
        # PII contract: pass masked phone to format engine
        excel_bytes, row_count = compose_excel(
            response.data,
            office_phone=masked_phone,
            vertical=vertical,
            business_name=business_name,
        )

        # Step 4: Upload-first (skip if dry_run)
        dry_run = params.get("dry_run", False)
        filename = f"reconciliation_{datetime.now(UTC).strftime('%Y%m%d')}.xlsx"

        if not dry_run:
            await self._attachments_client.upload_async(
                parent=unit_gid,
                file=io.BytesIO(excel_bytes),
                name=filename,
                content_type=XLSX_CONTENT_TYPE,
            )

            logger.info(
                "payment_reconciliation_upload_succeeded",
                unit_gid=unit_gid,
                filename=filename,
                size_bytes=len(excel_bytes),
                excel_rows=row_count,
            )

            # Step 5: Delete old matching attachments
            attachment_pattern = params.get(
                "attachment_pattern", DEFAULT_ATTACHMENT_PATTERN
            )
            await self._delete_old_attachments(
                unit_gid, attachment_pattern, exclude_name=filename
            )
        else:
            logger.info(
                "payment_reconciliation_dry_run_skip_write",
                unit_gid=unit_gid,
                excel_rows=row_count,
            )

        # Step 6: Return outcome
        return _UnitOutcome(
            gid=unit_gid,
            status="succeeded",
            excel_rows=row_count,
        )

    async def _resolve_unit(
        self,
        unit_gid: str,
    ) -> tuple[str, str, str | None] | None:
        """Resolve Unit -> UnitHolder -> Business (2-hop) with caching.

        Per TDD Section 1: Entity resolution for the 2-hop path.

        PII contract: office_phone MUST be masked via mask_phone_number()
        before any log call. The raw phone is used only for the data
        fetch and for passing into the format engine's data dict.

        Args:
            unit_gid: Unit task GID.

        Returns:
            Tuple of (office_phone, vertical, business_name) or None.
        """
        # Fetch unit task with parent reference for traversal
        unit_task = await self._asana_client.tasks.get_async(
            unit_gid,
            opt_fields=["parent", "parent.gid"],
        )

        if not unit_task.parent or not unit_task.parent.gid:
            return None

        # Use trigger_entity so HierarchyTraversalStrategy walks the
        # parent chain (Unit -> UnitHolder -> Business, 2-hop).
        from autom8_asana.models.business.base import BusinessEntity

        unit_entity = BusinessEntity(gid=unit_gid)
        unit_entity.parent = unit_task.parent

        async with ResolutionContext(
            self._asana_client,
            trigger_entity=unit_entity,
        ) as ctx:
            business = await ctx.business_async()
            business_gid = business.gid
            office_phone = business.office_phone
            vertical = business.vertical
            business_name = business.name

        if not office_phone or not vertical:
            # Cache negative result
            self._business_cache[business_gid] = None
            return None

        result = (office_phone, vertical, business_name)

        # Cache check/populate
        if business_gid in self._business_cache:
            logger.debug(
                "payment_reconciliation_cache_hit",
                unit_gid=unit_gid,
                business_gid=business_gid,
            )
        self._business_cache[business_gid] = result

        return result

    def _build_result_metadata(
        self,
        outcomes: list[BridgeOutcome],
    ) -> dict[str, Any]:
        """Build reconciliation-specific metadata: total Excel rows.

        Args:
            outcomes: All BridgeOutcome instances from this run.

        Returns:
            Metadata dict with total_excel_rows.
        """
        total_rows = sum(
            o.excel_rows
            for o in outcomes
            if isinstance(o, _UnitOutcome) and o.excel_rows
        )
        return {"total_excel_rows": total_rows}


# --- Internal Data Structure ---


@_dataclass
class _UnitOutcome(BridgeOutcome):
    """Internal per-unit processing result.

    Extends BridgeOutcome with reconciliation-specific field for
    Excel row tracking. Per AP-5: does not duplicate core fields.
    """

    # Inherited from BridgeOutcome: gid, status, reason, error
    excel_rows: int = 0
