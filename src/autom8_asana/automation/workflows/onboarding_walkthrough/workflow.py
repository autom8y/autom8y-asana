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

import fnmatch
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
from autom8_asana.automation.workflows.onboarding_walkthrough import constants, identity_guard
from autom8_asana.automation.workflows.onboarding_walkthrough import producer as _producer
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    ProducerFreezeError,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TenantBindingError,
    assert_exclusive_tenant_binding,
    harvest_routing_addresses,
)
from autom8_asana.clients.utils.pii import mask_phone_number
from autom8_asana.resolution.gfr.errors import GfrError

if TYPE_CHECKING:
    from autom8_asana.clients.attachments import AttachmentsClient
    from autom8_asana.core.scope import EntityScope
    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.resolution.gfr.truth_source import ByGuidVerifier

logger = get_logger(__name__)


@runtime_checkable
class RoutingAddressResolver(Protocol):
    """Structural type for the sole address source (autom8y-core SDK).

    The autom8y-core ``DataServiceClient`` (>=4.9.0) satisfies this protocol via
    ``resolve_routing_address_by_phone_async``. Injected so the workflow never
    hand-builds an address and tests can mock the resolve leg (no live call).
    """

    async def resolve_routing_address_by_phone_async(self, office_phone: str) -> str | None: ...


class CompanyIdAnchor(Protocol):
    """Structural type for the W1 Source-B anchor (the parent-chain company_id).

    The production default is ``identity_guard.anchor_company_id`` (which calls
    ``gfr.resolve_async`` -- the SOLE by-GUID substrate, G-PROPAGATE). Injected as a
    seam (DIP) so the W1 guard depends on this abstraction, not a hard module call:
    the guard is then trivially testable with a stub anchor, while production wires
    the real GFR-backed default. Raises a ``GfrError`` subclass when GFR cannot
    independently anchor the tenant (the workflow catches the base and fail-closes).
    """

    async def __call__(
        self,
        *,
        task_gid: str,
        client: Any,
        query_engine: QueryEngine,
        verifier: ByGuidVerifier | None,
    ) -> str: ...


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
        query_engine: The substrate ``QueryEngine`` the W1 GFR by-GUID identity
            guard consumes (GATE-1). Keyword-only; defaults to ``None`` so a
            caller that has not wired the substrate fail-CLOSES the guard
            (``anchor_unresolved`` skip) rather than crashing -- the guard's safe
            degrade (Pythia Fork-1: an un-anchorable task must never attach).
        verifier: Optional tier-2 by-GUID verifier for the W1 guard; ``None``
            uses the tier-1 cache anchor (the gid-exact Business row).
        company_id_anchor: The W1 Source-B anchor function (DIP seam). Defaults to
            ``identity_guard.anchor_company_id`` (the real GFR-backed anchor);
            injectable so the guard is testable with a stub.
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
        query_engine: QueryEngine | None = None,
        verifier: ByGuidVerifier | None = None,
        company_id_anchor: CompanyIdAnchor | None = None,
        onboarding_project_gid: str = constants.ONBOARDING_PROJECT_GID,
        data_client: Any | None = None,
    ) -> None:
        super().__init__(asana_client, data_client, attachments_client)
        self._resolver = resolver
        self._producer_dir = Path(producer_dir)
        self._query_engine = query_engine
        self._verifier = verifier
        self._company_id_anchor: CompanyIdAnchor = (
            company_id_anchor if company_id_anchor is not None else identity_guard.anchor_company_id
        )
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

        # 0a. PRESENCE-GATE phase 1 (W2, GATE-3) -- harvest prior walkthrough decks
        #     by EMBEDDED GUID (date-FREE idempotency key; NOT the date-stamped name,
        #     NOT the task gid). Name-agnostic: matches the glob, reads the embedded
        #     routing-address guid from the BYTES, so a LEGACY date-stamped deck
        #     (walkthrough_{gid}_{ts}.html minted before any guid-in-name convention)
        #     is recognized by its embedded address (the migration arm). The full
        #     skip/dedupe/replace decision is phase 2 (0b), AFTER resolve makes the
        #     target guid known; this phase only pays a cheap list+harvest so an
        #     empty-prior task falls straight through to mint exactly one.
        existing_by_guid = await self._existing_walkthrough_guids(gid)

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

        # 4b. GFR-BY-GUID IDENTITY GUARD (W1, GATE-1) -- resolve-CORRECTNESS, UPSTREAM.
        #     Source A (address-embedded guid, from the PHONE resolve) vs Source B
        #     (parent-chain-anchored company_id, from GFR). The two are INDEPENDENTLY
        #     derived (Pythia Fork-1): a phone collision that resolves the WRONG
        #     tenant's address produces a guid that does NOT equal the parent-chain
        #     anchor, and this guard catches it BEFORE any freeze/upload. G-PROPAGATE:
        #     calls gfr.resolve_async (the SOLE by-GUID substrate); no reimplementation.
        address_guid = identity_guard.extract_address_guid(gated_address)
        if self._query_engine is None:
            # FAIL-CLOSED: no substrate wired => GFR cannot independently anchor the
            # tenant => the guard cannot certify correctness => refuse to attach. A
            # misconfiguration must skip, never attach on the phone resolve alone.
            logger.error(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="anchor_unresolved",
                detail="query_engine not wired",
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="anchor_unresolved")
        try:
            anchored_company_id = await self._company_id_anchor(
                task_gid=gid,
                client=self._asana_client,
                query_engine=self._query_engine,
                verifier=self._verifier,
            )
        except GfrError as exc:
            # FAIL-CLOSED: GFR cannot INDEPENDENTLY anchor this task's tenant
            # (no parent chain to a Business root, anchored row absent, identity-path
            # purity drift, or a non-single-row result) -> refuse to attach. Catching
            # the GfrError base covers UnresolvedError / GuardViolationError /
            # AmbiguousCardinalityError uniformly -- any GFR failure is a safe skip.
            logger.warning(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="anchor_unresolved",
                error=str(exc),
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="anchor_unresolved")

        if address_guid != anchored_company_id:
            # The phone-resolved address points at a DIFFERENT tenant than the
            # parent-chain anchor: the cross-tenant leak class. FAIL-CLOSED -- NO
            # freeze, NO upload (the guard precedes FREEZE, so no producer subprocess
            # runs and no temp file is written). The fan-out continues for other
            # tasks (per-entity isolation). Guids are MASKED, never spilled in full.
            logger.error(
                "onboarding_walkthrough_guid_anchor_mismatch",
                task_gid=gid,
                address_guid=identity_guard.mask_guid(address_guid),
                anchored_company_id=identity_guard.mask_guid(anchored_company_id),
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="guid_anchor_mismatch")
        # else: address-embedded guid == parent-chain-anchored company_id -> PROCEED.

        # 0b. PRESENCE-GATE phase 2 (W2, GATE-3) -- the target guid is now known
        #     (== the W1-certified address guid). Decide skip / dedupe-down / replace
        #     against the priors harvested in 0a. The {ts} in any prior name is NEVER
        #     consulted -- the EMBEDDED guid is the whole key.
        target_guid = address_guid
        priors_for_target = existing_by_guid.get(target_guid, [])
        if priors_for_target:
            if len(priors_for_target) > 1:
                # >1 prior for THIS tenant (e.g. a delete-FAILURE residue from a
                # prior run): dedupe-DOWN -- keep the newest, delete the rest -- then
                # SKIP the re-mint. The presence-gate makes the residue NON-COMPOUNDING:
                # a persistent delete failure leaves at most a finite residue set this
                # arm reaps, never unbounded duplicate decks.
                await self._dedupe_down(gid, priors_for_target)
                logger.info(
                    "onboarding_walkthrough_skipped",
                    task_gid=gid,
                    reason="already_attached_deduped",
                    target_guid=identity_guard.mask_guid(target_guid),
                    prior_count=len(priors_for_target),
                )
                return BridgeOutcome(gid=gid, status="skipped", reason="already_attached_deduped")
            # Exactly one prior for THIS tenant -> already done. SKIP: no freeze,
            # no upload. (Recognizes LEGACY date-stamped decks via the byte-harvest
            # in 0a -- the migration arm.)
            logger.info(
                "onboarding_walkthrough_skipped",
                task_gid=gid,
                reason="already_attached",
                target_guid=identity_guard.mask_guid(target_guid),
            )
            return BridgeOutcome(gid=gid, status="skipped", reason="already_attached")
        # No prior for the target guid (the task may still carry decks for a DIFFERENT
        # guid -- the tenant changed). PROCEED to freeze->upload->delete-old: the
        # upload-first replacement reaps the foreign-guid prior via the glob delete.

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

        # 5b. TENANT-BINDING ASSERT (T7) -- the runtime analogue of the byte-exact
        # oracle. The frozen deck MUST carry EXACTLY the resolved routing address:
        # present (the producer's substring check) AND exclusive (no OTHER canonical
        # routing address). A producer-side injection drift or a template-static
        # foreign address is a wrong-tenant leak in the artifact the client receives.
        # Runs before the dry_run return so a dry_run exercises the full
        # resolve->freeze->assert path. Fail-closed: refuse to attach, surface
        # loudly, clean up the producer temp file (non-recoverable -- a retry on a
        # drifted producer / contaminated template would only reproduce it).
        try:
            assert_exclusive_tenant_binding(frozen=frozen_bytes, gated_address=gated_address)
        except TenantBindingError as exc:
            logger.error(
                "onboarding_walkthrough_tenant_binding_violation",
                task_gid=gid,
                office_phone=masked,
                error=str(exc),
            )
            self._cleanup_export(out_filename)
            return BridgeOutcome(
                gid=gid,
                status="failed",
                error=WorkflowItemError(
                    item_id=gid,
                    error_type="tenant_binding_violation",
                    message=str(exc),
                    recoverable=False,
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

    # --- W2 idempotency helpers ---

    async def _existing_walkthrough_guids(self, task_gid: str) -> dict[str, list[Any]]:
        """Map embedded-guid -> prior walkthrough attachments (date-FREE, name-agnostic).

        The W2 idempotency substrate (GATE-3): lists every ``walkthrough_*.html``
        on the task, downloads each one's bytes, and harvests the EMBEDDED canonical
        routing-address guid via the SAME ``harvest_routing_addresses`` oracle T7
        uses (one source of truth for what counts as a routing address). Keying on
        the embedded guid -- not the display name -- is what recognizes a LEGACY
        date-stamped deck (the migration arm): the guid is read from the bytes, so a
        ``walkthrough_{gid}_{ts}.html`` minted before any guid-in-name convention is
        matched by its address, not its name.

        Args:
            task_gid: the task whose prior walkthrough decks to harvest.

        Returns:
            ``{embedded_guid -> [attachment, ...]}`` for all prior walkthrough decks.
            Empty when the task carries no ``walkthrough_*.html`` (the no-prior arm).
        """
        out: dict[str, list[Any]] = {}
        page_iter = self._attachments_client.list_for_task_async(
            task_gid,
            opt_fields=["name", "created_at"],
        )
        async for att in page_iter:
            name = getattr(att, "name", None) or ""
            if not fnmatch.fnmatch(name, constants.ATTACHMENT_GLOB):
                continue
            raw = await self._download_attachment_bytes(att.gid)
            for routing_addr in harvest_routing_addresses(raw):
                guid = routing_addr.split("@", 1)[0].lower()
                out.setdefault(guid, []).append(att)
        return out

    async def _download_attachment_bytes(self, attachment_gid: str) -> bytes:
        """Fetch a prior attachment's bytes for the W2 embedded-guid harvest.

        The AttachmentsClient download surface writes to a ``destination`` BinaryIO
        and returns a path/None (it does NOT return bytes), so this thin wrapper
        streams into an in-memory buffer and returns the bytes (UV-P-W2 discharge --
        the byte-download surface exists; it is destination-based, not bytes-returning).

        Args:
            attachment_gid: the prior attachment's gid.

        Returns:
            The raw deck bytes (for ``harvest_routing_addresses``).
        """
        buffer = io.BytesIO()
        await self._attachments_client.download_async(attachment_gid, destination=buffer)
        return buffer.getvalue()

    async def _dedupe_down(self, task_gid: str, priors: list[Any]) -> None:
        """Reap all but the NEWEST of a same-guid prior set (>1 prior arm).

        Keeps the newest (by ``created_at`` when present, else by name -- the
        ``{ts}`` segment makes a newer same-task name sort later) and soft-fail
        deletes the rest, mirroring ``_delete_old_attachments`` per-item swallow so
        one stuck delete never aborts the reap. Combined with the presence-gate's
        re-mint short-circuit, a persistent delete failure can leave at most a
        finite residue set this arm reaps -- never unbounded duplicate decks.

        Args:
            task_gid: the task being processed (for structured logging).
            priors: the >1 prior attachments harvested for the target guid.
        """

        def _sort_key(att: Any) -> tuple[str, str]:
            return (getattr(att, "created_at", None) or "", getattr(att, "name", None) or "")

        ordered = sorted(priors, key=_sort_key)
        # Keep ordered[-1] (newest); delete the rest.
        for att in ordered[:-1]:
            try:
                await self._attachments_client.delete_async(att.gid)
                logger.debug(
                    "onboarding_walkthrough_dedupe_deleted",
                    task_gid=task_gid,
                    attachment_gid=att.gid,
                    attachment_name=getattr(att, "name", None),
                )
            except Exception as exc:  # noqa: BLE001 -- boundary: dedupe delete soft-fails per item
                logger.warning(
                    "onboarding_walkthrough_dedupe_delete_failed",
                    task_gid=task_gid,
                    attachment_gid=att.gid,
                    error=str(exc),
                )

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
