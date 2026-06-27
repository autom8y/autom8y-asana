"""Onboarding walkthrough workflow -- personalized deck attach (3rd bridge sibling).

Per PRD/TDD/ADR (seam A2 x B1): for an onboarding task whose ``Calendar Provider``
enum value is in the positive trigger set, this workflow:

1. GATE   -- ``calendar_provider`` is a triggering value (G-DENOM positive gate).
2. MAP    -- look up the deck template (None -> no-op skip).
3. PHONE  -- ``office_phone`` present, else fail-closed skip.
4. RESOLVE -- the gated ``{guid}@appointments.contenteapp.com`` address via the
   in-process autom8y-core SDK ``resolve_routing_address_by_phone_async`` (B1,
   sole address source; injected as ``self._resolver``).
5. FREEZE -- render-then-freeze the personalized deck via the Node >=22 producer
   subprocess (A2, sole freezer; ``producer.freeze_walkthrough_deck``).
6/7. UPLOAD-then-DELETE -- attach the frozen HTML, then delete the prior
   walkthrough deck (upload-first replacement; no half-replaced state).
8. CLEANUP -- best-effort remove the producer temp file.

Every external leg fails closed. Zero reimplementation of the freeze mechanism
(G-PROPAGATE P2) and zero hand-built gated addresses (G-PROPAGATE P3).

Per ADR-bridge-intermediate-base-class: extends ``BridgeWorkflowAction`` (reuses
``AttachmentReplacementMixin`` + ``upload_async``); no new bridge is introduced.
"""

from __future__ import annotations

import io
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from autom8y_core.errors import DataServiceUnavailableError
from autom8y_log import get_logger

from autom8_asana.automation.workflows.base import WorkflowItemError
from autom8_asana.automation.workflows.bridge_base import (
    BridgeOutcome,
    BridgeWorkflowAction,
)
from autom8_asana.automation.workflows.onboarding_walkthrough import constants
from autom8_asana.automation.workflows.onboarding_walkthrough import producer as _producer
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    ProducerFreezeError,
)
from autom8_asana.clients.utils.pii import mask_phone_number

if TYPE_CHECKING:
    from autom8_asana.clients.attachments import AttachmentsClient
    from autom8_asana.core.scope import EntityScope

logger = get_logger(__name__)


@runtime_checkable
class RoutingAddressResolver(Protocol):
    """Structural type for the sole address source (autom8y-core SDK).

    The autom8y-core ``DataServiceClient`` (>=4.9.0) satisfies this protocol via
    ``resolve_routing_address_by_phone_async``. Injected so the workflow never
    hand-builds an address and tests can mock the resolve leg (no live call).
    """

    async def resolve_routing_address_by_phone_async(self, office_phone: str) -> str | None: ...


class OnboardingWalkthroughWorkflow(BridgeWorkflowAction):
    """Attach a personalized, gated walkthrough deck to an onboarding task.

    Args:
        asana_client: AsanaClient for Asana API operations.
        resolver: The autom8y-core SDK ``DataServiceClient`` (B1 sole address
            source). Injected (ADR-WALK-B4) -- a distinct dependency from any
            asana-local data client.
        attachments_client: AttachmentsClient for upload/delete.
        producer_dir: Directory containing the Node producer (CONFIG; sourced
            from ``AUTOM8_WALKTHROUGH_PRODUCER_DIR`` by the handler, never
            hardcoded to a worktree path).
        onboarding_project_gid: Asana onboarding project GID (defaults to the
            N0-probed constant).
        data_client: Optional asana-local DataSource (unused by this workflow;
            passed through so the base health-check is a no-op when None).
    """

    feature_flag_env_var = constants.WALKTHROUGH_ENABLED_ENV_VAR

    def __init__(
        self,
        asana_client: Any,
        resolver: RoutingAddressResolver,
        attachments_client: AttachmentsClient,
        *,
        producer_dir: Path | str,
        onboarding_project_gid: str = constants.ONBOARDING_PROJECT_GID,
        data_client: Any | None = None,
    ) -> None:
        super().__init__(asana_client, data_client, attachments_client)
        self._resolver = resolver
        self._producer_dir = Path(producer_dir)
        self._onboarding_project_gid = onboarding_project_gid

    @property
    def workflow_id(self) -> str:  # type: ignore[override]  # read-only property overrides base attr
        return "onboarding-walkthrough"

    async def validate_async(self) -> list[str]:
        """Opt-IN safe-default kill-switch (MC-2 #725 broad-rollout containment).

        The sibling bridges (InsightsExport / ConversationAudit) are opt-OUT --
        enabled unless ``=false/0/no``. This not-yet-piloted automation INVERTS
        that: it stays DISABLED unless the operator EXPLICITLY enables it, so
        wiring up dispatch can never make it fire by default. The rest of
        pre-flight (data-source health) is delegated to the base unchanged.
        """
        env_value = os.environ.get(self.feature_flag_env_var, "").lower()
        if env_value not in {"true", "1", "yes", "on"}:
            return [
                f"Workflow disabled (opt-in): set {self.feature_flag_env_var}=true "
                "to enable (MC-2 #725: stays off until the operator enables it)"
            ]
        return await super().validate_async()

    # --- Bridge hooks ---

    async def enumerate_async(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Enumerate onboarding entities, enriched with the gate inputs.

        Both the targeted (``entity_ids``) and full paths produce entity dicts
        carrying ``calendar_provider`` + ``office_phone`` read off each task's
        own custom fields, so ``process_entity`` can gate without re-fetching.
        """
        if scope.has_entity_ids:
            entities: list[dict[str, Any]] = []
            for gid in scope.entity_ids:
                task = await self._asana_client.tasks.get_async(
                    gid,
                    opt_fields=["name", "custom_fields"],
                )
                entities.append(self._task_to_entity(task))
            logger.info(
                "onboarding_walkthrough_targeted",
                entity_ids=scope.entity_ids,
                dry_run=scope.dry_run,
            )
            return entities

        return await super().enumerate_async(scope)

    async def enumerate_entities(
        self,
        scope: EntityScope,
    ) -> list[dict[str, Any]]:
        """Full enumeration: active onboarding-project tasks, gate inputs read.

        Implements the abstract hook called by the base ``enumerate_async`` for
        the full (non-targeted) path.
        """
        page_iterator = self._asana_client.tasks.list_async(
            project=self._onboarding_project_gid,
            opt_fields=["name", "completed", "custom_fields"],
            completed_since="now",
        )
        tasks = await page_iterator.collect()
        return [
            self._task_to_entity(task) for task in tasks if not getattr(task, "completed", False)
        ]

    async def process_entity(
        self,
        entity: dict[str, Any],
        params: dict[str, Any],
    ) -> BridgeOutcome:
        """Gate -> map -> phone -> resolve -> freeze -> upload -> delete -> cleanup.

        Every external leg fails closed. Reads the gate inputs directly off the
        entity dict produced by ``enumerate_async``.
        """
        gid = entity.get("gid", "unknown")
        provider = entity.get("calendar_provider")
        dry_run = bool(params.get("dry_run", False))

        # 1. GATE -- positive necessity rule (G-DENOM). Unknown / absent / None
        #    values fall through to a no-op skip by construction.
        if provider is None or provider not in constants.WALKTHROUGH_DECK_MAP:
            logger.info(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="provider_not_triggering",
                provider=provider,
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="provider_not_triggering")

        # 2. MAP -- a known provider whose deck is PROBE-GATED (None) -> no-op skip.
        deck_template = constants.WALKTHROUGH_DECK_MAP[provider]
        if deck_template is None:
            logger.info(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="provider_unmapped",
                provider=provider,
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="provider_unmapped")

        # 3. PHONE -- fail-closed skip when office_phone is absent/empty.
        office_phone = entity.get("office_phone")
        if not office_phone:
            logger.warning(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="missing_office_phone",
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="missing_office_phone")

        masked = mask_phone_number(office_phone)

        # 4. RESOLVE -- sole address source (B1). Never hand-built.
        try:
            gated_address = await self._resolver.resolve_routing_address_by_phone_async(
                office_phone=office_phone
            )
        except DataServiceUnavailableError as exc:
            logger.error(
                "onboarding_walkthrough_resolve_unavailable",
                task_gid=gid,
                office_phone=masked,
                error=str(exc),
            )
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="resolve_unavailable",
                    message=str(exc),
                    recoverable=True,
                ),
            )

        if not gated_address:
            logger.warning(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                office_phone=masked,
                reason="address_unresolved",
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="address_unresolved")

        client_name = entity.get("client_name") or entity.get("name") or "Clinic"
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        out_filename = f"walkthrough_{gid}_{ts}.html"

        # 5. FREEZE -- sole freezer (A2). Native async subprocess (no thread
        # offload): producer.freeze_walkthrough_deck uses
        # asyncio.create_subprocess_exec, so the concurrency-guard fitness
        # function stays green by elimination, not by allowlisting a to_thread.
        try:
            frozen_bytes = await _producer.freeze_walkthrough_deck(
                producer_dir=self._producer_dir,
                deck_template=deck_template,
                gated_address=gated_address,
                client_name=client_name,
                out_filename=out_filename,
            )
        except ProducerFreezeError as exc:
            logger.error(
                "onboarding_walkthrough_freeze_failed",
                task_gid=gid,
                deck_template=deck_template,
                error=str(exc),
            )
            # Producer writes no file on non-zero exit -> nothing to clean.
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="producer_freeze_failed",
                    message=str(exc),
                    recoverable=True,
                ),
            )

        if dry_run:
            self._cleanup_export(out_filename)
            logger.info(
                "onboarding_walkthrough_dry_run_skip_write",
                task_gid=gid,
                deck_template=deck_template,
                size_bytes=len(frozen_bytes),
            )
            return BridgeOutcome(gid=gid, status="succeeded", reason="dry_run")

        # 6/7. UPLOAD-first, then DELETE-old. Cleanup runs on every exit path.
        try:
            try:
                await self._attachments_client.upload_async(
                    parent=gid,
                    file=io.BytesIO(frozen_bytes),
                    name=out_filename,
                    content_type="text/html",
                )
            except Exception as exc:  # noqa: BLE001 -- boundary: upload failure preserves prior state
                logger.error(
                    "onboarding_walkthrough_upload_failed",
                    task_gid=gid,
                    filename=out_filename,
                    error=str(exc),
                )
                # Do NOT delete old: prior attachment must survive (no half-replace).
                return BridgeOutcome(
                    gid=gid,
                    status="failed",
                    error=WorkflowItemError(
                        item_id=gid,
                        error_type="upload_failed",
                        message=str(exc),
                        recoverable=True,
                    ),
                )

            logger.info(
                "onboarding_walkthrough_upload_succeeded",
                task_gid=gid,
                filename=out_filename,
                size_bytes=len(frozen_bytes),
            )

            await self._delete_old_attachments(
                gid,
                constants.ATTACHMENT_GLOB,
                exclude_name=out_filename,
            )
            return BridgeOutcome(gid=gid, status="succeeded")
        finally:
            self._cleanup_export(out_filename)

    # --- Helpers ---

    def _task_to_entity(self, task: Any) -> dict[str, Any]:
        """Build an entity dict from an Asana task, reading the gate inputs.

        Reads ``calendar_provider`` (EnumField) and ``office_phone``
        (PhoneTextField) off the task's own custom fields via the Business
        descriptors. Honors N0 (fields live on the onboarding task) while using
        the TDD-specified Business descriptor binding.
        """
        # Lazy import: business.py is heavy and risks an import cycle at module load.
        from autom8_asana.models.business.business import Business

        business = Business.model_validate(task, from_attributes=True)
        return {
            "gid": task.gid,
            "name": task.name,
            "calendar_provider": business.calendar_provider,
            "office_phone": business.office_phone,
            "client_name": task.name,
        }

    def _cleanup_export(self, out_filename: str) -> None:
        """Best-effort removal of the producer temp file (FR-8)."""
        try:
            (self._producer_dir / "export" / out_filename).unlink(missing_ok=True)
        except OSError as exc:  # best-effort; a leftover temp file is non-fatal
            logger.debug(
                "onboarding_walkthrough_cleanup_failed",
                filename=out_filename,
                error=str(exc),
            )
